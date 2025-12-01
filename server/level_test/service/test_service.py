from langchain_openai import ChatOpenAI
from server.level_test.repository.log_repository import (
    get_user_by_login_id, get_last_log,
    get_recent_logs, get_all_logs_by_level,
    save_level_test_log
)
from server.level_test.repository.summary_repository import (
    get_summaries_by_level, get_last_summary, save_summary
)
from datetime import datetime
import httpx
import os

test_llm = ChatOpenAI(model="qwen:4b", base_url="http://127.0.0.1:11434/v1", api_key="none")
summary_llm = ChatOpenAI(model="gpt-4o-mini")
result_llm = ChatOpenAI(model="gpt-4o")

# Spring Boot API URL
SPRING_BOOT_URL = os.getenv("SPRING_BOOT_URL", "https://semiconical-shela-loftily.ngrok-free.dev")


async def evaluate_level(db, user_id: int, level_test_num: int, current_level: str = "Beginner") -> str:
    """최근 10개 대화를 기반으로 CEFR 레벨 평가 (사용자 응답만 평가)"""
    last_ten = get_recent_logs(db, user_id, level_test_num, 10)

    if not last_ten:
        print("⚠️ 평가할 대화 내용이 없습니다. 현재 레벨 유지")
        return current_level

    if len(last_ten) < 10:
        print(f"⚠️ 대화가 10개 미만입니다 (현재: {len(last_ten)}개)")

    # ✅ 개선 1: 사용자 응답만 추출 (AI 응답 제외)
    user_responses = [f"{i+1}. {log.user_question}" for i, log in enumerate(last_ten)]
    user_responses_text = "\n".join(user_responses)

    # ✅ 개선 2: Few-shot 예시 추가
    prompt = f"""Analyze the following {len(last_ten)} user responses and determine their English proficiency level according to CEFR standards.

IMPORTANT: Only evaluate the USER's responses. Do NOT consider any AI responses.

Evaluation criteria with examples:

**Beginner** (Very basic, many errors):
Example: "I go school. Like study English. Teacher is good."
- Very simple vocabulary, frequent grammar errors, incomplete sentences

**A1** (Basic phrases):
Example: "Hello, my name is John. I am 20 years old. I like music and sports."
- Simple present tense, basic vocabulary, short sentences

**A2** (Elementary, familiar topics):
Example: "Yesterday I went to the park with my friends. We played soccer and had fun. The weather was nice."
- Simple past tense, can describe daily activities, basic connectors

**B1** (Intermediate, travel situations):
Example: "I've been studying English for two years. I'm planning to travel to London next month because I want to improve my speaking skills."
- Present perfect, future plans, because/when clauses, longer sentences

**B2** (Upper-intermediate, fluent interaction):
Example: "I've always been interested in learning languages because I believe it opens up new perspectives. Although it's challenging, I find it rewarding when I can communicate with people from different cultures."
- Complex sentences, subordinate clauses, varied vocabulary, natural flow

**C1** (Advanced, fluent expression):
Example: "Having studied linguistics for several years, I've come to appreciate the intricate relationship between language and culture. What fascinates me most is how subtle nuances in word choice can convey entirely different meanings."
- Sophisticated structures, rich vocabulary, abstract concepts, native-like fluency

**C2** (Proficient, near-native):
Example: "The interplay between sociolinguistic factors and language acquisition has long been a subject of scholarly debate. Notwithstanding the myriad challenges inherent in cross-cultural communication, I contend that linguistic competence transcends mere grammatical accuracy."
- Academic/professional level, complex vocabulary, idiomatic expressions, perfect grammar

Now analyze these user responses:
{user_responses_text}

Consider:
- Vocabulary range and sophistication
- Grammar accuracy and complexity
- Sentence structure variety
- Naturalness and fluency

Respond with ONLY ONE of these exact words: Beginner, A1, A2, B1, B2, C1, or C2.
No explanation, just the level."""

    try:
        print("🤖 GPT-4o-mini에게 레벨 평가 요청 중...")
        response = summary_llm.invoke(prompt)
        level = response.content.strip()
        print(f"🤖 GPT 원본 응답: '{level}'")

        valid_levels = ["Beginner", "A1", "A2", "B1", "B2", "C1", "C2"]
        if level not in valid_levels:
            for valid_level in valid_levels:
                if valid_level in level:
                    level = valid_level
                    break
            else:
                # ✅ 개선 3: 파싱 실패 시 현재 레벨 유지 (Beginner 강제 X)
                print(f"⚠️ 유효하지 않은 응답: '{level}', 현재 레벨 유지")
                level = current_level

        return level
    except Exception as e:
        # ✅ 개선 4: 예외 발생 시 현재 레벨 유지
        print(f"❌ 레벨 평가 중 오류 발생: {e}, 현재 레벨 유지")
        return current_level


async def update_user_rank_in_spring(user_id: int, rank_title: str, token: str) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{SPRING_BOOT_URL}/api/v1/users/{user_id}/rank",
                json={"rankTitle": rank_title},
                headers={"Authorization": f"Bearer {token}"},   # ⭐ 추가!!!
                timeout=10.0
            )
            if response.status_code == 200:
                print(f"✅ User {user_id} rank updated to {rank_title}")
                return True
            else:
                print(f"❌ Failed to update rank: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        print(f"⚠️ Error updating rank in Spring Boot: {e}")
        return False



async def process_test_message(db, login_id: str, message: str, token: str):

    user = get_user_by_login_id(db, login_id)
    if not user:
        raise ValueError("User not found")

    user_id = user.id
    last_log = get_last_log(db, user_id)

    # 대화 번호 계산
    if not last_log:
        level_test_num, dialog_num = 1, 1
    else:
        if last_log.diolog_num >= 100:
            level_test_num, dialog_num = last_log.level_test_num + 1, 1
        else:
            level_test_num, dialog_num = last_log.level_test_num, last_log.diolog_num + 1

    # summary + recent logs 불러오기
    summaries = get_summaries_by_level(db, user_id, level_test_num)
    summary_context = "\n".join([s.summary_text for s in summaries])

    remainder = (dialog_num - 1) % 10
    recent_logs = get_recent_logs(db, user_id, level_test_num, remainder)
    dialogue_context = "\n".join(
        [f"User: {l.user_question}\nAI: {l.ai_response}" for l in recent_logs]
    )

    # 대화 context 생성
    context = f"""
    Summary of previous conversation:
    {summary_context}

    Recent exchanges:
    {dialogue_context}

    User now says: {message}
    Respond naturally, in 1-2 sentences, friendly and conversational.
    When you answer, you don't need to provide information, but simply answer briefly just for socializing.
    Answer by empathizing or asking about the condition of the user
    """

    # 대답 생성
    response = test_llm.invoke(context)
    ai_reply = response.content.strip()

    # 로그 저장
    save_level_test_log(db, user_id, message, ai_reply, level_test_num, dialog_num)

    current_level = user.ranks.title if user.ranks else "Beginner"
    level_changed = False
    evaluated_level = ""   # ⭐ 기본값: 빈 문자열

    # 10번째마다 요약 + 레벨 평가
    if dialog_num % 10 == 0:

        last_ten = get_recent_logs(db, user_id, level_test_num, 10)
        text = "\n".join([f"User: {x.user_question}\nAI: {x.ai_response}" for x in last_ten])
        prompt = f"Summarize the following 10 exchanges concisely:\n{text}"
        summary_text = summary_llm.invoke(prompt).content.strip()

        last_summary = get_last_summary(db, user_id, level_test_num)
        next_summary_num = (last_summary.summary_num + 1) if last_summary else 1
        save_summary(db, user_id, level_test_num, next_summary_num, summary_text)

        # ⭐ 10개 단위 레벨 평가 (현재 레벨 전달)
        previous_level = user.ranks.title if user.ranks else "Beginner"
        evaluated_level = await evaluate_level(db, user_id, level_test_num, previous_level)

        if evaluated_level != previous_level:
            success = await update_user_rank_in_spring(user.id, evaluated_level, token)
            if success:
                current_level = evaluated_level
                level_changed = True
                db.refresh(user)

    # 100번째일 때도 evaluated_level 보내기
    if dialog_num % 100 == 0:

        # ⭐ 100번째 시점 간이 레벨 평가 (최근 10개 기준)
        previous_level = user.ranks.title if user.ranks else "Beginner"
        evaluated_level = await evaluate_level(db, user_id, level_test_num, previous_level)

        # 전체 100개 분석 로직 실행
        await analyze_test_result(db=db, login_id=login_id, level_test_num=level_test_num)

    return {
        "user_message": message,
        "llm_reply": ai_reply,
        "level_test_num": level_test_num,
        "dialog_num": dialog_num,
        "current_level": current_level,
        "level_changed": level_changed,
        "evaluated_level": evaluated_level   # ⭐ 여기 추가됨
    }


async def analyze_test_result(db, login_id: str, level_test_num: int):
    user = get_user_by_login_id(db, login_id)

    logs = get_all_logs_by_level(db, user.id, level_test_num)
    history_text = "\n".join(
        [f"User: {x.user_question}\nAI: {x.ai_response}" for x in logs]
    )

    prompt = f"""
    다음은 user가 어휘력 테스트 중 남긴 100개의 대화 내용입니다.
    이를 종합하여 user는 CEFR 기준(A1~C2) 중 어느 수준의 어휘력을 보이는지 분석해주세요.
    history:
    {history_text}
    """

    result = result_llm.invoke(prompt)
    return {"level_analysis": result.content.strip()}

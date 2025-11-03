# # server/test/service/test_service.py
# from langchain_openai import ChatOpenAI
# from server.level_test.repository.test_repository import save_level_test_log

# # ✅ 임시 저장소 (실제 서비스면 Redis나 DB로 교체 가능)
# test_state = {
#     "cnt": 0,
#     "history": [],
#     "history_summary" : []
# }

# # ✅ 테스트용 LLM (Ollama Qwen)
# test_llm = ChatOpenAI(
#     model="qwen:4b",
#     base_url="http://127.0.0.1:11434/v1",
#     api_key="none"
# )

# # ✅ 결과 분석용 LLM (GPT-4o)
# result_llm = ChatOpenAI(model="gpt-4o")
# summary_llm = ChatOpenAI(model="gpt-4o-mini")

# # ===============================
# # 1️⃣ 어휘 테스트 수행 (/test)
# # ===============================
# async def process_test_message(db, login_id: str, message: str):
#     # 1️⃣ 카운트 증가
#     #test_state["cnt"] += 1

#     # 2️⃣ 대화 context 구성: summary + 최근 메시지
#     context = f"""
#     Summary of previous conversation:
#     {test_state['history_summary']}

#     Last messages:
#     {test_state['history'][-1]['user'] if test_state['history'] else ''}
#     {test_state['history'][-1]['ai'] if test_state['history'] else ''}

#     User now says: {message}
#     Respond naturally, in 1-2 sentences, friendly and conversational.
#     When you answer, you don't need to provide information, but simply answer briefly just for socializing.
#     Answer by empathizing or asking about the condition of the user
#     """

#     # 3️⃣ AI 응답 생성
#     response = test_llm.invoke(context)

#     # 4️⃣ 대화 기록 저장
#     test_state["history"].append({
#         "user": message,
#         "ai": response.content
#     })

#     save_level_test_log(
#         db=db,
#         login_id=login_id,
#         user_question=message,
#         ai_response=response.content,
#     )

#     # 5️⃣ Summary 업데이트 (요약 LLM에게 전달)
#     summary_prompt = f"""
#     Update this conversation summary based on the new exchange.

#     Old summary:
#     {test_state['history_summary']}

#     New message:
#     User: {message}
#     AI: {response.content}

#     Provide an updated concise summary that keeps the important topics and tone.
#     """
#     summary_response = summary_llm.invoke(summary_prompt)
#     test_state["history_summary"] = summary_response.content.strip()

#     # 6️⃣ 결과 반환
#     return {
#         "cnt": test_state["cnt"],
#         "user_message": message,
#         "llm_reply": response.content,
#         "summary": test_state["history_summary"]
#     }


# # ===============================
# # 2️⃣ 결과 분석 (/test-result)
# # ===============================
# async def analyze_test_result():
#     # if test_state["cnt"] < 100:
#     #     return {"error": "테스트가 아직 완료되지 않았어요.", "current_cnt": test_state["cnt"]}

#     # 어휘력 평가 프롬프트
#     prompt = f"""
#     다음은 user가 어휘력 테스트 중 남긴 100개의 대화 내용입니다.
#     이를 종합하여 user는 CEFR 기준(A1~C2) 중 어느 수준의 어휘력을 보이는지 분석해주세요.
#     history:
#     {test_state["history"]}
#     """

#     # ✅ 분석 완료 후 상태 초기화
#     test_state["cnt"] = 0
#     test_state["history"] = []

#     result = result_llm.invoke(prompt)


#     return {
#         "level_analysis": result.content,
#         "total_messages": len(test_state["history"])
#     }


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
SPRING_BOOT_URL = os.getenv("SPRING_BOOT_URL", "http://localhost:8080")


async def evaluate_level(db, user_id: int, level_test_num: int) -> str:
    """최근 10개 대화를 기반으로 CEFR 레벨 평가"""
    last_ten = get_recent_logs(db, user_id, level_test_num, 10)

    if not last_ten:
        print("⚠️ 평가할 대화 내용이 없습니다. Beginner 반환")
        return "Beginner"

    if len(last_ten) < 10:
        print(f"⚠️ 대화가 10개 미만입니다 (현재: {len(last_ten)}개)")

    dialogue_text = "\n".join([f"User: {x.user_question}\nAI: {x.ai_response}" for x in last_ten])

    prompt = f"""Analyze the following {len(last_ten)} exchanges and determine the user's English proficiency level (CEFR: A1, A2, B1, B2, C1, C2).
Consider vocabulary richness, grammar complexity, sentence structure, and fluency.

Evaluation criteria:
- Beginner: Very basic English, simple words, many errors
- A1: Basic phrases, simple vocabulary
- A2: Elementary level, can describe familiar matters
- B1: Intermediate level, can handle most travel situations
- B2: Upper-intermediate, can interact with fluency
- C1: Advanced, can express ideas fluently
- C2: Proficient, near-native level

Dialogue:
{dialogue_text}

Respond with ONLY ONE of these exact words: Beginner, A1, A2, B1, B2, C1, or C2.
No other text, just the level."""

    try:
        print("🤖 GPT-4o-mini에게 레벨 평가 요청 중...")
        response = summary_llm.invoke(prompt)  # gpt-4o-mini
        level = response.content.strip()
        print(f"🤖 GPT 원본 응답: '{level}'")

        # 유효한 레벨인지 확인
        valid_levels = ["Beginner", "A1", "A2", "B1", "B2", "C1", "C2"]
        if level not in valid_levels:
            print(f"⚠️ 유효하지 않은 레벨 응답, 텍스트에서 추출 시도...")
            # 레벨이 유효하지 않으면 텍스트에서 추출 시도
            for valid_level in valid_levels:
                if valid_level in level:
                    level = valid_level
                    print(f"✅ 추출 성공: {level}")
                    break
            else:
                print(f"❌ 추출 실패, Beginner로 설정")
                level = "Beginner"  # 기본값

        return level
    except Exception as e:
        print(f"❌ 레벨 평가 중 오류 발생: {e}")
        return "Beginner"


async def update_user_rank_in_spring(user_id: int, rank_title: str) -> bool:
    """Spring Boot API를 호출하여 User의 rank 업데이트"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{SPRING_BOOT_URL}/api/v1/users/{user_id}/rank",
                json={"rankTitle": rank_title},
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


async def process_test_message(db, login_id: str, message: str):

    # 몇번째 대화인지 확인하기
    # 1️⃣ 사용자 및 최근 로그
    user = get_user_by_login_id(db, login_id)
    if not user:
        raise ValueError("User not found")

    user_id = user.id
    last_log = get_last_log(db, user_id)

    # 2️⃣ level_test_num, dialog_num 계산
    if not last_log:
        level_test_num, dialog_num = 1, 1
    else:
        if last_log.diolog_num >= 100:
            level_test_num, dialog_num = last_log.level_test_num + 1, 1
        else:
            level_test_num, dialog_num = last_log.level_test_num, last_log.diolog_num + 1




    
    # 10개 단위 요약 + 낱개 요약 안된 대화 불러와서 컨텍스트 생성
    # 3️⃣ 요약 불러오기 (모든 summary)
    summaries = get_summaries_by_level(db, user_id, level_test_num)
    summary_context = "\n".join([s.summary_text for s in summaries])

    # 4️⃣ 최근 n%10 대화 기록
    remainder = (dialog_num - 1) % 10
    recent_logs = get_recent_logs(db, user_id, level_test_num, remainder)
    dialogue_context = "\n".join(
        [f"User: {l.user_question}\nAI: {l.ai_response}" for l in recent_logs]
    )

    # 5️⃣ context 생성
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





    # invoke 하기
    # 6️⃣ AI 응답 생성
    response = test_llm.invoke(context)
    ai_reply = response.content.strip()





    # 7️⃣ 로그 저장
    new_log = save_level_test_log(db, user_id, message, ai_reply, level_test_num, dialog_num)

    # 🆕 현재 레벨 정보 (기본값)
    current_level = user.ranks.title if user.ranks else "Beginner"
    level_changed = False

    # 8️⃣ 요약 저장 (10의 배수일때만)
    if dialog_num % 10 == 0:
        print(f"\n{'='*60}")
        print(f"🔟 10번째 대화 도달! (대화 번호: {dialog_num})")
        print(f"{'='*60}\n")

        # 10개 대화 요약
        last_ten = get_recent_logs(db, user_id, level_test_num, 10)
        text = "\n".join([f"User: {x.user_question}\nAI: {x.ai_response}" for x in last_ten])
        prompt = f"Summarize the following 10 exchanges concisely:\n{text}"
        summary_text = summary_llm.invoke(prompt).content.strip()

        last_summary = get_last_summary(db, user_id, level_test_num)
        next_summary_num = (last_summary.summary_num + 1) if last_summary else 1
        save_summary(db, user_id, level_test_num, next_summary_num, summary_text)
        print(f"✅ 요약 저장 완료 (요약 번호: {next_summary_num})")

        # 🆕 레벨 평가 수행
        previous_level = user.ranks.title if user.ranks else "Beginner"
        print(f"📊 레벨 평가 시작...")
        print(f"   - 현재 레벨: {previous_level}")
        print(f"   - 평가 대상: 최근 10개 대화")

        evaluated_level = await evaluate_level(db, user_id, level_test_num)
        print(f"   - 평가 결과: {evaluated_level}")

        # 레벨이 변경되었으면 Spring Boot로 업데이트
        if evaluated_level != previous_level:
            print(f"🔄 레벨 변경 감지! {previous_level} → {evaluated_level}")
            success = await update_user_rank_in_spring(user.id, evaluated_level)
            if success:
                current_level = evaluated_level
                level_changed = True
                # DB에서 user의 rank 정보 업데이트 (캐시 동기화)
                db.refresh(user)
                print(f"🎉 레벨 업데이트 성공! 새 레벨: {evaluated_level}")
            else:
                print(f"❌ Spring Boot 업데이트 실패")
                current_level = previous_level
        else:
            print(f"✅ 레벨 유지: {previous_level}")
            current_level = previous_level

        print(f"\n{'='*60}\n")

    # 9️⃣ 100회 도달 시 결과 분석
    if dialog_num == 100:
        await analyze_test_result(db, login_id, level_test_num)

    return {
        "user_message": message,
        "llm_reply": ai_reply,
        "level_test_num": level_test_num,
        "dialog_num": dialog_num,
        "current_level": current_level,
        "level_changed": level_changed
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

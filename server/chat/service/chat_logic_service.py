from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session
from langchain_core.messages import SystemMessage, HumanMessage
from server.database import SessionLocal
from server.models import ChatOrder, ChatLog, ChatSummary, ChatAnalysis
import json


def handle_chat_flow(state, chat_llm, summary_llm, analysis_llm):
    """
    유저별 세션(chat_order) 관리 + 대화 저장 + 요약/분석 트리거 통합
    """
    db: Session = SessionLocal()
    try:
        user_id = int(state.get("userId", 0))
        initial_chat = bool(state.get("initialChat", False))

        # --------------------------------------------------
        # 1️⃣ ChatOrder 결정 (유저별 마지막 chat_order + 1)
        # --------------------------------------------------
        if initial_chat:
            last_order_num = (
                db.query(func.max(ChatOrder.chat_order))
                .filter(ChatOrder.user_id == user_id)
                .scalar()
            )
            next_chat_order_num = 1 if last_order_num is None else last_order_num + 1

            new_order = ChatOrder(chat_order=next_chat_order_num, user_id=user_id)
            db.add(new_order)
            db.commit()
            db.refresh(new_order)

            chat_order_id = new_order.id
            chat_order_num = new_order.chat_order  # ✅ 유저별 세션 번호
            next_chat_num = 1

            print(f"🆕 [New Session] user_id={user_id}, chat_order={chat_order_num}, id={chat_order_id}")
        else:
            # ✅ 유저별 최신 세션 가져오기
            last_order = (
                db.query(ChatOrder)
                .filter(ChatOrder.user_id == user_id)
                .order_by(ChatOrder.chat_order.desc())
                .first()
            )

            if last_order is None:
                new_order = ChatOrder(chat_order=1, user_id=user_id)
                db.add(new_order)
                db.commit()
                db.refresh(new_order)
                chat_order_id = new_order.id
                chat_order_num = new_order.chat_order
                next_chat_num = 1
                print(f"🆕 [Fallback New Session] user_id={user_id}, chat_order=1, id={chat_order_id}")
            else:
                chat_order_id = last_order.id
                chat_order_num = last_order.chat_order  # ✅ 여기!
                last_log = (
                    db.query(ChatLog)
                    .filter(ChatLog.chat_order_id == chat_order_id)
                    .order_by(ChatLog.chatNum.desc())
                    .first()
                )
                next_chat_num = 1 if last_log is None else last_log.chatNum + 1
                print(f"💬 [Continue Chat] user_id={user_id}, chat_order={chat_order_num}, chatNum={next_chat_num}")

        # --------------------------------------------------
        # 2️⃣ 히스토리 & 요약 로드
        # --------------------------------------------------
        summaries = (
            db.query(ChatSummary)
            .filter(ChatSummary.chat_order_id == chat_order_id)
            .order_by(ChatSummary.id.desc())
            .limit(10)
            .all()
        )
        summary_text = "\n".join(s.detail for s in reversed(summaries)) if summaries else ""

        take_n = next_chat_num % 10 if next_chat_num > 1 else 0
        logs = (
            db.query(ChatLog)
            .filter(ChatLog.chat_order_id == chat_order_id)
            .order_by(ChatLog.id.desc())
            .limit(take_n)
            .all()
        )
        history_text = "\n".join(
            f"User: {l.userChat}\nAI: {l.aiChat}" for l in reversed(logs)
        ) if logs else ""

        # --------------------------------------------------
        # 3️⃣ LLM 응답 생성
        # --------------------------------------------------
        messages = [
            SystemMessage(f"""You are a friendly and intelligent friend.
            You respond empathetically, briefly (3 sentences max), and naturally.
            Use the provided summaries and recent chats as context.

            - The user's CEFR level is provided in state["cefr_level"].
            - Respond using vocabulary, grammar, and sentence complexity appropriate for that CEFR level.
            - If the CEFR level is very low (A1–A2), use simpler words and shorter sentences.
            - If the CEFR level is high (B2–C2), use more natural and complex English expressions.
            """),
            HumanMessage(
                f"[Summaries(last 10)]\n{summary_text}\n\n"
                f"[Recent chats(last {take_n})]\n{history_text}\n\n"
                f"[User]\n{state.get('user_input','')}"
                f"[CEFR Level]\n{state.get('cefr_level', 'UNKNOWN')}"
            ),
        ]
        ai_text = chat_llm.invoke(messages).content

        # --------------------------------------------------
        # 4️⃣ 로그 저장
        # --------------------------------------------------
        db.add(ChatLog(
            chat_order_id=chat_order_id,
            chatNum=next_chat_num,
            userChat=state.get("user_input", ""),
            aiChat=ai_text,
            createdAt=datetime.utcnow()
        ))

        # --------------------------------------------------
        # 5️⃣ 요약 / 분석 트리거
        # --------------------------------------------------
        if next_chat_num % 10 == 0:
            s_detail = _summarize_recent_chats(db, chat_order_id, summary_llm, limit=10)
            db.add(ChatSummary(chat_order_id=chat_order_id, summary_num=next_chat_num // 10, detail=s_detail))
            print(f"🧠 Summary created for chat_order={chat_order_num}")

        if next_chat_num % 20 == 0:
            _analyze_interests(db, chat_order_id, analysis_llm, limit=20)
            print(f"🔍 Analysis created for chat_order={chat_order_num}")

        db.commit()

        # ✅ 응답 시 chat_order_id 대신 chat_order_num 반환
        return {
            "output": ai_text,
            "chatNum": next_chat_num,
            "chatOrder": chat_order_num,  # ✅ 세션 번호
        }

    finally:
        db.close()


# --------------------------------------------------
# 🧠 Helper: 요약 생성
# --------------------------------------------------
def _summarize_recent_chats(db: Session, chat_order_id: int, llm, limit: int = 10) -> str:
    logs = (
        db.query(ChatLog)
        .filter(ChatLog.chat_order_id == chat_order_id)
        .order_by(ChatLog.id.desc())
        .limit(limit)
        .all()
    )
    text = "\n".join(f"User: {l.userChat}\nAI: {l.aiChat}" for l in reversed(logs)) if logs else ""
    if not text:
        return "No content to summarize."
    msg = [
        SystemMessage("Summarize the following conversation into concise bullet points (max 10)."),
        HumanMessage(text)
    ]
    return llm.invoke(msg).content


# --------------------------------------------------
# 🔍 Helper: 관심사 분석
# --------------------------------------------------
def _analyze_interests(db: Session, chat_order_id: int, llm, limit: int = 20):
    logs = (
        db.query(ChatLog)
        .filter(ChatLog.chat_order_id == chat_order_id)
        .order_by(ChatLog.id.desc())
        .limit(limit)
        .all()
    )

    text = "\n".join(
        f"User: {l.userChat}\nAI: {l.aiChat}"
        for l in reversed(logs)
    ) if logs else ""

    if not text:
        return "No content to analyze."

    # ------------------------
    # 1) LLM 호출
    # ------------------------
    msg = [
        SystemMessage(
            "From the dialogue, extract user's interests as a JSON:\n"
            '{"interests": [...]}'
        ),
        HumanMessage(text)
    ]

    result = llm.invoke(msg).content

    # ------------------------
    # 2) JSON 파싱
    # ------------------------
    try:
        data = json.loads(result)
    except:
        # 실패했으면 원본 통째로 하나만 저장
        db.add(ChatAnalysis(
            chat_order_id=chat_order_id,
            detail=result,
            createdAt=datetime.utcnow(),
        ))
        db.commit()
        return result

    # ------------------------
    # 3) 오직 interests[]만 저장
    # ------------------------
    interests = data.get("interests", [])

    # interests가 없으면 저장 안 함
    if not interests:
        return result

    for item in interests:
        db.add(ChatAnalysis(
            chat_order_id=chat_order_id,
            detail=item,     # 🔥 여기! "AI", "다이어트", "FastAPI", "Flutter"만 저장됨
            createdAt=datetime.utcnow()
        ))

    db.commit()

    return result

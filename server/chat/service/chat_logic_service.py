from datetime import datetime
from sqlalchemy.orm import Session
from langchain_core.messages import SystemMessage, HumanMessage
from server.database import SessionLocal
from server.models import ChatOrder, ChatLog, ChatSummary, ChatAnalysis

def handle_chat_flow(state, chat_llm, summary_llm, analysis_llm):
    """
    chat 분기 메인 플로우 (chatNum은 서버가 계산)
    """
    db: Session = SessionLocal()
    try:
        user_id = int(state.get("userId", 0))
        initial_chat = bool(state.get("initialChat", False))

        # ✅ 1. chatOrder / chatNum 결정
        if initial_chat:
            # 새로운 chatOrder 생성
            last_order = (
                db.query(ChatOrder)
                .filter(ChatOrder.user_id == user_id)
                .order_by(ChatOrder.chat_order.desc())
                .first()
            )
            new_order_id = 1 if last_order is None else int(last_order.chat_order) + 1
            new_order = ChatOrder(chat_order=new_order_id, user_id=user_id, detail=None)
            db.add(new_order)
            db.commit()
            db.refresh(new_order)
            next_chat_num = 1  # 첫 대화
        else:
            # 기존 chatOrder 유지
            last_order = (
                db.query(ChatOrder)
                .filter(ChatOrder.user_id == user_id)
                .order_by(ChatOrder.chat_order.desc())
                .first()
            )
            if last_order is None:
                # 방어적 처리
                new_order_id = 1
                new_order = ChatOrder(chat_order=new_order_id, user_id=user_id, detail=None)
                db.add(new_order)
                db.commit()
                db.refresh(new_order)
                next_chat_num = 1
            else:
                new_order_id = int(last_order.chat_order)
                # ✅ 마지막 chatNum 불러오기
                last_log = (
                    db.query(ChatLog)
                    .filter(ChatLog.chat_order == new_order_id)
                    .order_by(ChatLog.chatNum.desc())
                    .first()
                )
                next_chat_num = 1 if last_log is None else int(last_log.chatNum) + 1

        # 2. 요약 + 최근 로그로 히스토리 구성
        try:
            summaries = (
                db.query(ChatSummary)
                .filter(ChatSummary.chat_order == new_order_id)
                .order_by(ChatSummary.id.desc())
                .limit(10)
                .all()
            )
            summary_text = "\n".join(s.detail for s in reversed(summaries)) if summaries else ""
        except Exception as e:
            print(f"Warning: Failed to load summaries: {e}")
            summary_text = ""

        take_n = next_chat_num % 10 if next_chat_num > 1 else 0
        try:
            logs = (
                db.query(ChatLog)
                .filter(ChatLog.chat_order == new_order_id)
                .order_by(ChatLog.id.desc())
                .limit(take_n)
                .all()
            )
            history_text = "\n".join(
                f"User: {l.userChat}\nAI: {l.aiChat}" for l in reversed(logs)
            ) if logs else ""
        except Exception as e:
            print(f"Warning: Failed to load chat logs: {e}")
            history_text = ""

        # 3. LLM 응답 생성 (프롬프트 그대로 유지)
        messages = [
            SystemMessage("""You are a friendly and intelligent friend. 
             You talk in an empathetic manner, and you don't need to pass too long information.
             Provide useful answers. Use the given history & summaries for context.
             Answer in no more than three sentences
             """),
            HumanMessage(
                f"[Summaries(last 10)]\n{summary_text}\n\n"
                f"[Recent chats(last {take_n})]\n{history_text}\n\n"
                f"[User]\n{state.get('user_input','')}"
            ),
        ]
        ai_text = chat_llm.invoke(messages).content

        # 4. 대화 저장
        db.add(ChatLog(
            chat_order=new_order_id,
            chatNum=next_chat_num,
            userChat=state.get("user_input",""),
            aiChat=ai_text,
            createdAt=datetime.utcnow()
        ))

        # 5. 요약/분석 트리거
        if next_chat_num % 10 == 0:
            s_detail = _summarize_recent_chats(db, new_order_id, summary_llm, limit=10)
            db.add(ChatSummary(chat_order=new_order_id, summary_num=next_chat_num // 10, detail=s_detail))

        if next_chat_num % 20 == 0:
            a_detail = _analyze_interests(db, new_order_id, analysis_llm, limit=20)
            db.add(ChatAnalysis(chat_order=new_order_id, detail=a_detail, createdAt=datetime.utcnow()))

        db.commit()

        return {
            "output": ai_text,
            "chatNum": next_chat_num,
            "chatOrder": new_order_id
        }

    finally:
        db.close()

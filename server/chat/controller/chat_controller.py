from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from server.chat.service.chat_service import process_chat_message
from server.auth_manager import get_current_user
from server.models import User
import server.chat.service.supervisor_graph as supervisor_graph
import server.chat.service.groq_subgraph as groq_subgraph
from server.chat.service.tts_service import generate_tts_audio
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    initialChat: Optional[bool] = False  # ✅ 첫 대화 여부만 전달

class PodcastRequest(BaseModel):
    conversationHistory: str  # 대화 내용 전체 또는 요약


@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    사용자 메시지를 받아 LangGraph로 처리
    - initialChat=True → 새로운 chatOrder 생성
    - initialChat=False → 기존 chatOrder의 마지막 chatNum 불러와서 +1
    """
    result = await process_chat_message(
        message=request.message,
        user_id=current_user.id,
        initial_chat=request.initialChat
    )

    return {
        "response": result.get("output"),
        "audio": result.get("audio_base64"),
        "chatNum": result.get("chatNum"),
        "chatOrder": result.get("chatOrder"),
    }


# 디버그용 (JWT 없이)
@router.post("/chat/debug")
async def chat_debug_endpoint(request: ChatRequest):
    try:
        result = await process_chat_message(
            message=request.message,
            user_id=1,
            initial_chat=request.initialChat
        )

        return {
            "user_message": request.message,
            "ai_response": result.get("output"),
            "audio_base64": result.get("audio_base64"),
            "chatNum": result.get("chatNum"),
            "chatOrder": result.get("chatOrder"),
        }
    except Exception as e:
        import traceback
        print(f"ERROR in chat_debug_endpoint: {str(e)}")
        print(traceback.format_exc())
        return {
            "user_message": request.message,
            "ai_response": f"Error: {str(e)}",
            "audio_base64": None,
            "chatNum": 0,
            "chatOrder": 0,
        }


# 간단한 챗/팟캐스트 엔드포인트 (데이터베이스 없음)
@router.post("/chat/simple")
async def simple_chat_endpoint(request: ChatRequest):
    """간단한 챗/팟캐스트 엔드포인트 - 데이터베이스 없이 작동"""
    try:
        # 팟캐스트 키워드 감지
        podcast_keywords = ["podcast", "listening", "radio", "audio show"]
        is_podcast = any(keyword in request.message.lower() for keyword in podcast_keywords)

        if is_podcast:
            # 팟캐스트 생성
            podcast_app = groq_subgraph.build_podcast_graph()
            result = podcast_app.invoke({
                "user_input": request.message,
                "history": "",
                "history_summary": "Radio show is started. You need to speak",
                "turn_count": 0
            })
            script = result.get("history", "")
            audio = generate_tts_audio(script)

            return {
                "user_message": request.message,
                "ai_response": script,
                "audio_base64": audio,
                "chatNum": 1,
                "chatOrder": 1,
            }
        else:
            # 일반 챗
            llm = ChatOpenAI(model="gpt-4o")
            messages = [
                SystemMessage("""You are a friendly and intelligent friend.
                 You talk in an empathetic manner, and you don't need to pass too long information.
                 Provide useful answers. Answer in no more than three sentences"""),
                HumanMessage(request.message)
            ]
            ai_text = llm.invoke(messages).content

            return {
                "user_message": request.message,
                "ai_response": ai_text,
                "audio_base64": None,
                "chatNum": 1,
                "chatOrder": 1,
            }
    except Exception as e:
        import traceback
        print(f"ERROR in simple_chat_endpoint: {str(e)}")
        print(traceback.format_exc())
        return {
            "user_message": request.message,
            "ai_response": f"Error: {str(e)}",
            "audio_base64": None,
            "chatNum": 0,
            "chatOrder": 0,
        }


# 대화 내용 기반 팟캐스트 생성 전용 엔드포인트
@router.post("/podcast/generate")
async def generate_podcast_from_conversation(request: PodcastRequest):
    """
    최근 대화 내용을 기반으로 팟캐스트 생성
    - conversationHistory: 사용자와 AI의 최근 대화 내용
    """
    try:
        # 1. 대화 내용을 요약하여 팟캐스트 주제 추출
        llm = ChatOpenAI(model="gpt-4o-mini")
        summary_messages = [
            SystemMessage("""Analyze the conversation history and extract the main topic.
            Provide a concise topic description (1-2 sentences) suitable for a podcast/radio show.
            Focus on the core subject being discussed."""),
            HumanMessage(f"Conversation:\n{request.conversationHistory}")
        ]
        topic = llm.invoke(summary_messages).content

        # 2. 추출된 주제로 팟캐스트 생성
        podcast_app = groq_subgraph.build_podcast_graph()
        result = podcast_app.invoke({
            "user_input": topic,
            "history": "",
            "history_summary": "Radio show is started. You need to speak about the conversation topic.",
            "turn_count": 0
        })

        # 3. 스크립트 및 오디오 생성
        script = result.get("history", "")
        audio = generate_tts_audio(script)

        return {
            "topic": topic,
            "ai_response": script,
            "audio_base64": audio,
            "chatNum": 1,
            "chatOrder": 1,
        }

    except Exception as e:
        import traceback
        print(f"ERROR in generate_podcast_from_conversation: {str(e)}")
        print(traceback.format_exc())
        return {
            "topic": "",
            "ai_response": f"Error: {str(e)}",
            "audio_base64": None,
            "chatNum": 0,
            "chatOrder": 0,
        }

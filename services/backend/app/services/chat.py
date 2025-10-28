from uuid import uuid4

from app.schemas.chat import ChatRequest, ChatResponse, ChatMessage


class ChatService:
    """Proxy for chat orchestration with Azure OpenAI and AWS Bedrock (stubbed)."""

    async def process_turn(self, payload: ChatRequest) -> ChatResponse:
        session_id = payload.session_id or f"sess_{uuid4().hex}"

        # Placeholder response until LLM orchestration is integrated.
        reply = ChatMessage(
            role="assistant",
            content="这是一条占位回复，用于演示聊天服务的接口。",
        )

        return ChatResponse(
            session_id=session_id,
            reply=reply,
            recommended_therapist_ids=[],
        )

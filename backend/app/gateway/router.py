from typing import Dict, Any
from sqlalchemy.orm import Session
from agents.query_agent import QueryAgent
from agents.action_agent import ActionAgent

class GatewayRouter:
    """
    API Gateway Router (Production):
    Tiếp nhận yêu cầu duy nhất từ Web Frontend tại `/api/v1/ai/chat`,
    Phân loại ý định (Intent Classification) và điều hướng sang Query Agent hoặc Action Agent.
    """

    @staticmethod
    def classify_intent(prompt: str) -> str:
        prompt_lower = prompt.lower()
        action_keywords = [
            "tạo", "thêm", "lập", "xóa", "hủy", "delete", "sửa", "chỉnh sửa", "cập nhật",
            "phân công", "giao việc", "duyệt", "approve", "hoàn thành", "update", "báo cáo sự cố", "create"
        ]
        for kw in action_keywords:
            if kw in prompt_lower:
                return "ACTION"
        return "QUERY"

    @classmethod
    def process_request(cls, prompt: str, db: Session, is_confirmed: bool = False, draft_data: Dict[str, Any] = None) -> Dict[str, Any]:
        if is_confirmed and draft_data:
            result = ActionAgent.execute_draft(draft_data, db)
            target_api = "/api/agent/action"
            intent = "ACTION (CONFIRMED)"
        else:
            intent = cls.classify_intent(prompt)
            if intent == "ACTION":
                result = ActionAgent.process(prompt, db)
                target_api = "/api/agent/action"
            else:
                result = QueryAgent.process(prompt, db)
                target_api = "/api/agent/query"

        return {
            "status": "success",
            "gateway_info": {
                "entrypoint": "/api/v1/ai/chat",
                "detected_intent": intent,
                "routed_api": target_api,
                "executing_agent": result.get("agent", "AI Agent")
            },
            "response": {
                "reply": result.get("reply", ""),
                "data": result.get("data", None),
                "mutation": result.get("mutation", None),
                "is_draft": result.get("is_draft", False),
                "draft_data": result.get("draft_data", None)
            }
        }

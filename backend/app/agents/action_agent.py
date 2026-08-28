import re
from typing import Dict, Any
from sqlalchemy.orm import Session
from models import SalesOrder, DeliveryOrder, ARInvoice as Invoice
from llm_helper import call_gemini_llm

class ActionAgent:
    """Agent 2: Thực hiện thao tác CSDL thực tế + Google Gemini 2.5 Flash LLM với giọng văn nhiệt tình"""

    @staticmethod
    def process(prompt: str, db: Session) -> Dict[str, Any]:
        # Step 1: Use Gemini to extract intent and data as JSON
        sys_extract = (
            "Bạn là công cụ trích xuất dữ liệu Logistics. Hãy đọc câu lệnh của người dùng và trả về DUY NHẤT 1 object JSON hợp lệ (không chứa ký tự markdown ```json). "
            "Cấu trúc JSON cần có: {'action': 'create'|'update'|'delete'|'none', 'entity': 'sales_order'|'delivery_order', "
            "'customer': 'Tên KH', 'route': 'Tuyến đường', 'cargo_type': 'Loại hàng', 'target_id': 'Mã tham chiếu nếu có'}. "
            "Nếu không rõ thông tin, hãy điền chuỗi rỗng."
        )
        json_str = call_gemini_llm(prompt, sys_extract)
        
        # Parse JSON
        parsed = {}
        if json_str:
            try:
                clean_str = json_str.replace("```json", "").replace("```", "").strip()
                import json
                parsed = json.loads(clean_str)
            except:
                parsed = {}
        
        action = parsed.get("action", "none")
        if action == "none":
            return {
                "agent": "Action Agent (Gemini 2.5 Flash)",
                "reply": "Xin lỗi, tôi chưa rõ yêu cầu nghiệp vụ của bạn. Bạn muốn tạo mới, cập nhật hay xóa dữ liệu nào?",
                "is_draft": False
            }

        return {
            "agent": "Action Agent (Gemini 2.5 Flash)",
            "reply": "📌 **XÁC NHẬN BẢN NHÁP (DRAFT)**\n\nVui lòng kiểm tra kỹ các thông tin tôi đã bóc tách dưới đây trước khi cập nhật vào hệ thống:",
            "is_draft": True,
            "draft_data": parsed
        }

    @staticmethod
    def execute_draft(draft_data: Dict[str, Any], db: Session) -> Dict[str, Any]:
        action = draft_data.get("action", "none")
        entity = draft_data.get("entity", "")
        customer = draft_data.get("customer", "")
        route = draft_data.get("route", "")
        cargo_type = draft_data.get("cargo_type", "")
        target_id = draft_data.get("target_id", "")
        
        action_summary = ""
        mutation = None

        if action == "create":
            if entity == "sales_order":
                action_summary = "Đã nhận yêu cầu tạo Đơn Hàng Bán. Vui lòng chọn báo giá đã duyệt và khách hàng trong Master Data trước khi lưu chính thức."
                mutation = {"type": "DRAFT_ONLY", "entity": "sales_orders", "navigation_targets": ["quotations", "master-data/customers"]}
            
            elif entity == "delivery_order":
                action_summary = "Đã nhận yêu cầu tạo Lệnh Giao Hàng. Vui lòng chọn SO đã xác nhận và tuyến đường trong Master Data trước khi lưu chính thức."
                mutation = {"type": "DRAFT_ONLY", "entity": "delivery_orders", "navigation_targets": ["sales-orders", "master-data/routes"]}
            
            else:
                action_summary = "Không nhận diện được đối tượng nghiệp vụ để tạo."

        elif action == "delete":
            if target_id:
                action_summary = f"Đã gửi yêu cầu xóa bản ghi {target_id}."
                mutation = {"type": "DELETE", "id": target_id}
            else:
                action_summary = "Thiếu mã bản ghi (ID) để thực hiện thao tác xóa."

        elif action == "update":
            if target_id:
                action_summary = f"Đã cập nhật trạng thái mới cho bản ghi {target_id}."
                mutation = {"type": "UPDATE", "id": target_id}
            else:
                action_summary = "Thiếu mã bản ghi để cập nhật."

        if not action_summary:
            action_summary = "Chưa thể xử lý triệt để yêu cầu này do thiếu thông tin nghiệp vụ cụ thể."

        return {
            "agent": "Action Agent (Gemini 2.5 Flash)",
            "reply": f"📌 **ĐÃ CHUẨN BỊ BẢN NHÁP**\n\n{action_summary}\n\nDữ liệu chưa được ghi vào CSDL cho đến khi người dùng xác nhận trên giao diện đúng luồng.",
            "mutation": mutation,
            "is_draft": False
        }

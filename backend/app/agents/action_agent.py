import re
from typing import Dict, Any
from sqlalchemy.orm import Session
from models import DeliveryOrder
from llm_helper import call_gemini_llm

class ActionAgent:
    """Agent 2: Thực hiện thao tác CSDL thực tế + Google Gemini 2.5 Flash LLM với giọng văn nhiệt tình"""

    @staticmethod
    def process(prompt: str, db: Session) -> Dict[str, Any]:
        # Step 1: Use Gemini to extract intent and data as JSON
        sys_extract = (
            "Bạn là công cụ trích xuất dữ liệu Logistics. Hãy đọc câu lệnh của người dùng và trả về DUY NHẤT 1 object JSON hợp lệ (không chứa ký tự markdown ```json). "
            "Cấu trúc JSON cần có: {'action': 'create'|'update'|'delete'|'none', 'entity': 'delivery_order', "
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
        """Diễn giải bản nháp thành hướng dẫn thao tác. KHÔNG ghi vào CSDL.

        Agent này cố tình không tự ghi dữ liệu: nội dung bản nháp do mô hình
        ngôn ngữ bóc tách nên không thể tin cậy để dùng thẳng làm lệnh ghi.
        Mọi thay đổi phải đi qua đúng endpoint nghiệp vụ, nơi có kiểm tra ràng
        buộc, quyền hạn và nhật ký kiểm toán.

        Trước đây hàm này trả về những câu ở thì quá khứ — "Đã cập nhật trạng
        thái mới cho bản ghi X", "Đã gửi yêu cầu xóa bản ghi X" — kèm một object
        ``mutation`` khiến giao diện tải lại toàn bộ dữ liệu. Người dùng thấy
        hệ thống báo thành công và bảng dữ liệu làm mới, nên tin rằng thao tác
        đã xong, trong khi tham số ``db`` không hề được dùng và không có gì
        được ghi. Câu chữ ở đây phải nói đúng những gì thực sự xảy ra.
        """
        action = draft_data.get("action", "none")
        entity = draft_data.get("entity", "")
        target_id = draft_data.get("target_id", "")

        action_summary = ""
        navigation_targets = []

        if action == "create":
            if entity == "delivery_order":
                action_summary = (
                    "Lệnh giao hàng sinh tự động khi khách chấp nhận báo giá. Hãy mở màn "
                    "Báo giá cước, ghi nhận khách chấp nhận — hệ thống sẽ tạo lệnh."
                )
                navigation_targets = ["quotations", "master-data/routes"]
            else:
                action_summary = "Không nhận diện được đối tượng nghiệp vụ để tạo."

        elif action == "delete":
            if target_id:
                action_summary = (
                    f"Cần xóa bản ghi {target_id}. Hãy mở màn hình tương ứng và thực "
                    f"hiện thao tác xóa tại đó — thao tác xóa cần kiểm tra ràng buộc "
                    f"dữ liệu nên không thể thực hiện từ khung trò chuyện."
                )
                navigation_targets = ["delivery-orders"]
            else:
                action_summary = "Thiếu mã bản ghi (ID) để thực hiện thao tác xóa."

        elif action == "update":
            if target_id:
                action_summary = (
                    f"Cần cập nhật bản ghi {target_id}. Hãy mở màn hình tương ứng và "
                    f"chuyển trạng thái tại đó — thao tác này cần kiểm tra quyền và "
                    f"ghi nhật ký kiểm toán nên không thể thực hiện từ khung trò chuyện."
                )
                navigation_targets = ["delivery-orders"]
            else:
                action_summary = "Thiếu mã bản ghi để cập nhật."

        if not action_summary:
            action_summary = "Chưa thể xử lý yêu cầu này do thiếu thông tin nghiệp vụ cụ thể."

        return {
            "agent": "Action Agent (Gemini 2.5 Flash)",
            "reply": (
                "📋 **HƯỚNG DẪN THAO TÁC — CHƯA GHI VÀO HỆ THỐNG**\n\n"
                f"{action_summary}\n\n"
                "⚠️ Trợ lý không tự ghi dữ liệu. Chưa có thay đổi nào được lưu."
            ),
            # Không có thay đổi nào xảy ra, nên không trả về ``mutation``: giao
            # diện dùng trường đó để tải lại dữ liệu, khiến người dùng tưởng
            # thao tác đã hoàn tất.
            "mutation": None,
            "applied": False,
            "navigation_targets": navigation_targets,
            "is_draft": False
        }

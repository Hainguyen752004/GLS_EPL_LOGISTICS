import re
from typing import Dict, Any
from sqlalchemy.orm import Session
from models import DeliveryOrder, ARInvoice as Invoice, Vehicle, Driver
from llm_helper import call_gemini_llm

class QueryAgent:
    """Agent 1: Tra cứu CSDL kết hợp Google Gemini 2.0/2.5 Flash LLM với giọng văn nhiệt tình, đẹp mắt"""

    @staticmethod
    def process(prompt: str, db: Session) -> Dict[str, Any]:
        # Comprehensive System Snapshot
        dos = db.query(DeliveryOrder).all()
        invs = db.query(Invoice).all()
        vehicles = db.query(Vehicle).all()
        drivers = db.query(Driver).all()

        total_rev = sum(i.total for i in invs if i.total)

        context_data = "BÁO CÁO TOÀN DIỆN HỆ THỐNG LOGISTICS EPL:\n\n"
        context_data += f"- DOANH THU & TÀI CHÍNH: Tổng doanh thu hóa đơn: {total_rev:,.0f} VNĐ.\n"
        context_data += f"- TỔNG QUAN SỐ LƯỢNG: {len(dos)} Lệnh Giao Hàng DO, {len(invs)} Hóa đơn.\n"
        context_data += f"- ĐỘI XE & TÀI XẾ: Tổng {len(vehicles)} Xe, {len(drivers)} Tài xế.\n"
        
        # Chi tiết Xe
        if vehicles:
            context_data += "  + Tình trạng xe: " + ", ".join([f"{v.id} ({v.type}) - {v.status}" for v in vehicles]) + "\n"

        # Chi tiết Lệnh giao hàng đang chạy
        active_dos = [d for d in dos if d.status == "In Transit"]
        if active_dos:
            context_data += f"- ĐƠN HÀNG ĐANG CHẠY (In Transit): {len(active_dos)} chuyến.\n"
            for d in active_dos:
                context_data += f"  + {d.id}: {d.customer_id} đi tuyến {d.route_id} (Xe: {d.vehicle_id}, Lái xe: {d.driver_id})\n"

        system_instruction = (
            "Bạn là Chuyên viên Trợ lý AI cao cấp của Hệ thống Logistics EPL (Lào Enterprise System). "
            "Hãy đọc yêu cầu của sếp/người dùng và sử dụng BẢN BÁO CÁO HỆ THỐNG TOÀN DIỆN DƯỚI ĐÂY để trả lời. "
            "KHÔNG ĐƯỢC BỊA THÔNG TIN. Hãy trả lời cực kỳ chuyên nghiệp, sinh động, dùng Markdown (in đậm, danh sách).\n\n"
            f"{context_data}"
        )

        llm_reply = call_gemini_llm(prompt, system_instruction)
        
        if not llm_reply:
            llm_reply = "Xin lỗi, hiện tại hệ thống kết nối AI đang bị gián đoạn. Vui lòng thử lại sau."

        return {
            "agent": "Query Agent (Gemini 2.5 Flash)",
            "reply": llm_reply,
            "data": {"total_revenue": total_rev}
        }

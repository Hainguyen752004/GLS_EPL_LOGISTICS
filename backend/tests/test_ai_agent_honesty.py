"""Trợ lý AI không được báo thành công cho việc nó không làm.

Người dùng báo lỗi: bấm nút xác nhận trên khung trò chuyện thì hệ thống nói
"Đã cập nhật trạng thái mới cho bản ghi X", giao diện tải lại toàn bộ dữ liệu,
nhưng không có gì được ghi. Nguyên nhân: execute_draft nhận tham số ``db`` rồi
không dùng, trả về câu ở thì quá khứ, kèm một object ``mutation`` khiến giao
diện làm mới bảng — ba tín hiệu đều nói "đã xong" trong khi không có lệnh ghi.
"""

import importlib

import pytest


@pytest.fixture
def agents():
    action = importlib.import_module("agents.action_agent")
    gateway = importlib.import_module("gateway.router")
    return action.ActionAgent, gateway.GatewayRouter


PAST_TENSE_CLAIMS = ("Đã cập nhật", "Đã xóa", "Đã lưu", "Đã ghi", "Đã tạo", "Đã gửi yêu cầu xóa")


@pytest.mark.parametrize("draft", [
    {"action": "update", "target_id": "SO-001"},
    {"action": "delete", "target_id": "SO-001"},
    {"action": "create", "entity": "delivery_order"},
])
def test_execute_draft_never_claims_work_it_did_not_do(agents, draft):
    ActionAgent, _ = agents

    result = ActionAgent.execute_draft(draft, db=None)

    reply = result["reply"]
    for claim in PAST_TENSE_CLAIMS:
        assert claim not in reply, (
            f"phản hồi nói '{claim}' trong khi không có lệnh ghi nào chạy: {reply}"
        )
    assert result["applied"] is False
    assert result["mutation"] is None, (
        "mutation khác None khiến giao diện tải lại dữ liệu và người dùng "
        "tưởng thao tác đã hoàn tất"
    )
    assert "CHƯA GHI" in reply or "không tự ghi" in reply


def test_execute_draft_works_without_a_database_session(agents):
    """Bằng chứng hàm này không hề chạm CSDL: truyền None vẫn chạy.

    Đây là điều test khẳng định chứ không phải chỗ hở — thiết kế cố ý không cho
    agent tự ghi, vì nội dung bản nháp do mô hình ngôn ngữ bóc tách nên không
    đủ tin cậy để dùng thẳng làm lệnh ghi. Vấn đề trước đây chỉ là câu chữ nói
    ngược lại sự thật.
    """
    ActionAgent, _ = agents

    result = ActionAgent.execute_draft({"action": "update", "target_id": "X"}, db=None)

    assert result["applied"] is False


def test_gateway_does_not_hardcode_success(agents):
    """status trước đây luôn là "success", kể cả khi không có gì xảy ra."""
    _, GatewayRouter = agents

    payload = GatewayRouter.process_request(
        "CONFIRM", db=None, is_confirmed=True,
        draft_data={"action": "update", "target_id": "SO-001"},
    )

    assert payload["status"] != "success"
    assert payload["response"]["applied"] is False
    assert payload["response"]["mutation"] is None


def test_gateway_exposes_navigation_targets_so_the_user_can_finish_the_task(agents):
    """Đã không làm thay được thì phải chỉ rõ người dùng cần đi đâu."""
    _, GatewayRouter = agents

    payload = GatewayRouter.process_request(
        "CONFIRM", db=None, is_confirmed=True,
        draft_data={"action": "create", "entity": "delivery_order"},
    )

    assert payload["response"]["navigation_targets"], (
        "phải chỉ ra màn hình cần mở để hoàn tất thao tác"
    )

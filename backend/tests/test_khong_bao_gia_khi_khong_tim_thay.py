"""Xoa/sua mot ban ghi KHONG TON TAI thi khong duoc bao thanh cong.

Day la mot loi da tim thay bang tay o `delete_driver`: khong tim thay tai xe
thi ham van tra ve `{"message": "Đã xóa nhân sự"}`. Nguoi dung go nham mot ma,
bam Xoa, va nhan mot loi khang dinh SAI — trong khi khong co gi bi xoa ca.

Doc than route de doan thi khong du: rat nhieu endpoint uy quyen cho service,
va service moi la cho nem DomainError 404. Nen bai kiem nay GOI THAT tung
endpoint voi mot ma khong ton tai, roi doc ma trang thai.

Quy tac: 200/201 kem chu "Đã ..." cho mot ban ghi khong ton tai la NOI SAI.
Cho phep 404 (dung nhat), 401/403 (chan quyen truoc), 409 (dang bi rang buoc),
422 (than yeu cau khong hop le — voi PUT thi day la binh thuong vi bai kiem
gui than rong).
"""
import pytest

MA_GIA = "KHONG-TON-TAI-XYZ-123"

#: Cac duong XOA co the goi khong can than yeu cau.
DUONG_XOA = [
    "/api/customers/" + MA_GIA,
    "/api/routes/" + MA_GIA,
    "/api/vehicles/" + MA_GIA,
    "/api/vehicle-types/" + MA_GIA,
    "/api/drivers/" + MA_GIA,
    "/api/quotations/" + MA_GIA,
    "/api/delivery-orders/" + MA_GIA,
    "/api/tms/scheduling/driver-shifts/" + MA_GIA,
]

#: Cac duong SUA/CHUYEN TRANG THAI. Than rong la du: neu endpoint tu choi vi
#: than khong hop le (422) thi cung khong phai loi khang dinh sai.
DUONG_SUA = [
    ("/api/quotations/" + MA_GIA, {}),
    ("/api/quotations/" + MA_GIA + "/status", {"status": "Đã duyệt"}),
    ("/api/delivery-orders/" + MA_GIA + "/status", {"status": "Đang vận chuyển"}),
    ("/api/master-data/tax-codes/" + MA_GIA, {}),
    ("/api/master-data/accounting-periods/" + MA_GIA, {}),
    ("/api/master-data/account-mappings/" + MA_GIA, {}),
]

CHAP_NHAN = (400, 401, 403, 404, 409, 422)


def _mo_ta(r):
    return "%d %s" % (r.status_code, r.text[:160])


@pytest.mark.parametrize("duong", DUONG_XOA)
def test_xoa_ban_ghi_khong_ton_tai_khong_duoc_bao_da_xoa(app_client, duong):
    client, _, _ = app_client
    r = client.delete(duong)
    assert r.status_code in CHAP_NHAN, _mo_ta(r)
    # Va tuyet doi khong duoc noi "Đã xóa".
    assert "Đã xóa" not in r.text, "nói đã xóa trong khi không có gì bị xóa: " + _mo_ta(r)
    assert "Da xoa" not in r.text, _mo_ta(r)


@pytest.mark.parametrize("duong,than", DUONG_SUA)
def test_sua_ban_ghi_khong_ton_tai_khong_duoc_bao_da_cap_nhat(app_client, duong, than):
    client, _, _ = app_client
    r = client.put(duong, json=than)
    assert r.status_code in CHAP_NHAN, _mo_ta(r)
    for chu in ("Đã cập nhật", "Đã duyệt", "Đã lưu", "Đã xác nhận", "thành công"):
        assert chu not in r.text, (
            "nói %r cho một bản ghi không tồn tại: %s" % (chu, _mo_ta(r)))


def test_khong_duoc_500_o_bat_ky_duong_nao(app_client):
    """500 nghia la loi khong ai bat. Nguoi dung khong sua duoc gi tu mot
    'Internal Server Error', va nguoi van hanh cung khong biet chuyen gi."""
    client, _, _ = app_client
    xau = []
    for duong in DUONG_XOA:
        r = client.delete(duong)
        if r.status_code >= 500:
            xau.append(("DELETE", duong, r.status_code, r.text[:120]))
    for duong, than in DUONG_SUA:
        r = client.put(duong, json=than)
        if r.status_code >= 500:
            xau.append(("PUT", duong, r.status_code, r.text[:120]))
    assert xau == [], xau

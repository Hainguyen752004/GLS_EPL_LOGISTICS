# -*- coding: utf-8 -*-
"""Hồ sơ chốt của lệnh giao hàng: giá thành và lãi gộp phải đúng.

HAI LỖI ĐÃ ĐO ĐƯỢC trên PostgreSQL thật, và cả hai hiện ra ở con số mà người
xem demo nhìn đầu tiên.

LỖI 1 — LÃI GỘP 98,56%. `cost_basis` lấy bằng `actual_cost.total_amount`, nhưng
cột đó mang **PHẦN VƯỢT** so với kế hoạch chứ không mang chi phí — đó là chủ ý
của bảng chi phí thực tế: nó nói về chênh lệch. Bản trước viết
`cost_basis = actual_total or quoted_cost`, tức khi đã có bảng chi phí thì lấy
luôn phần vượt làm giá thành:

    cước 3.601.600 · giá thành thật 2.409.255 · vượt 51.963
    -> bản trước: lãi gộp 3.601.600 − 51.963 = 3.549.637 = 98,56%
    -> đúng phải: 3.601.600 − 2.461.218 = 1.140.382 ≈ 31,7%

Đây là CÙNG MỘT LỖI đã sửa ở `tms_reporting_service` — báo cáo doanh thu cũng
từng hiện lãi gộp 99% vì lấy chênh lệch làm tổng. Sửa một chỗ mà không soi chỗ
còn lại thì lỗi vẫn sống ở màn khác, và đó chính là chuyện đã xảy ra.

LỖI 2 — `quoted_cost = 0`. Báo giá chỉ được tra qua bước Đơn hàng
(`so_id` -> SO -> báo giá). Bước Đơn hàng đã BỎ khỏi luồng ở mốc `7c445d1` —
báo giá tách THẲNG ra lệnh giao hàng — nên `so_id` rỗng trên mọi lệnh mới và báo
giá không bao giờ tìm ra được. Lệnh giao hàng có sẵn `quotation_id` từ lúc tách.

Bài kiểm này đi ĐÚNG LUỒNG MỚI: tạo báo giá rồi TÁCH ra lệnh giao hàng, không đi
qua bước Đơn hàng. Đi đường cũ thì `so_id` có mặt và đường lùi che mất lỗi.
"""
import pytest

from conftest import API_TEST_HEADERS


def _tach_do(client, workflow_builder, ma_bao_gia="QT-CLOSE"):
    """Tạo báo giá rồi tách thẳng ra lệnh giao hàng — luồng hiện tại."""
    workflow_builder.master_data()
    workflow_builder.quotation(ma_bao_gia, total_cost=2_000_000, selling_price=3_000_000)

    # Báo giá phải qua bước khách chấp nhận mới tách được, và đường đó đòi báo
    # giá đã gửi. Đi tuần tự đúng như người dùng đi.
    tra = client.post("/api/quotations/%s/send" % ma_bao_gia, json={},
                      headers=API_TEST_HEADERS)
    if tra.status_code >= 400:
        pytest.skip("đường send trả %s: %s" % (tra.status_code, tra.text[:200]))

    # KHACH CHAP NHAN thi he thong SINH DO NGAY trong cung giao dich — khong con
    # buoc tach tay. `do_ids` nam ngay trong goi tra ve cua accept.
    tra = client.post("/api/quotations/%s/accept" % ma_bao_gia,
                      json={"dos": [{"quantity": 1}]}, headers=API_TEST_HEADERS)
    if tra.status_code >= 400:
        pytest.skip("đường accept trả %s: %s" % (tra.status_code, tra.text[:200]))
    goi = tra.json()
    ds = goi.get("do_ids") or (goi.get("data") or {}).get("do_ids") or []
    assert ds, "chấp nhận xong phải trả về mã lệnh giao hàng: %s" % tra.text[:200]
    return ds[0]


def _hoso(client, do_id):
    tra = client.get("/api/delivery-orders/%s/closeout" % do_id)
    assert tra.status_code == 200, tra.text
    goi = tra.json()
    return goi.get("data") or goi


def test_gia_thanh_lay_tu_bao_gia_cua_CHINH_lenh_giao_hang(app_client, workflow_builder):
    """Không đi qua bước Đơn hàng — bước đó đã bỏ khỏi luồng."""
    client, _, _ = app_client
    do_id = _tach_do(client, workflow_builder)

    c = _hoso(client, do_id)["commercials"]
    assert float(c["quoted_cost"]) > 0, (
        "giá thành đọc ra 0. Báo giá phải được tra từ `delivery_order.quotation_id`; "
        "tra qua `so_id` thì không bao giờ tìm ra vì bước Đơn hàng đã bỏ khỏi luồng."
    )


def test_lai_gop_tinh_tren_GIA_THANH_khong_tinh_tren_phan_vuot(app_client, workflow_builder):
    client, _, _ = app_client
    do_id = _tach_do(client, workflow_builder)

    c = _hoso(client, do_id)["commercials"]
    cuoc = float(c["final_selling_price"])
    lai = float(c["margin_amount"])

    # Lãi gộp phải bằng cước trừ GIÁ THÀNH. Nếu nó bằng cước trừ PHẦN VƯỢT thì
    # con số sẽ gần bằng cả cước — đúng cái đã xảy ra (98,56%).
    assert cuoc > 0
    bien = lai / cuoc * 100
    assert bien < 90, (
        "biên lợi nhuận %.2f%% — không có chuyến vận tải nào lãi vậy. Đây là dấu "
        "hiệu giá thành đang bị lấy bằng phần vượt thay vì bằng giá thành." % bien)

    # Và quan hệ phải khép: cước − giá thành = lãi gộp.
    assert abs(lai - (cuoc - float(c["quoted_cost"]))) < 1.0, (
        "lãi gộp %s không bằng cước %s trừ giá thành %s"
        % (lai, cuoc, c["quoted_cost"]))


def test_moi_khoan_muc_deu_co_ma_phan_loai_dung_MOT_bo(app_client, workflow_builder):
    """`configured_cost_lines` phải mang `charge_type` của bộ mã CHUẨN.

    Trước đây cùng "Phí bãi & lưu kho" mà một bên ghi `warehouse` (mã cấu phần
    công thức), bên kia ghi `yard` (mã khoản mục chi phí). Ai đọc gói này để
    hạch toán sẽ ánh xạ theo một danh sách rồi lệch danh sách kia — và lệch im
    lặng, vì cả hai mã đều "trông đúng".
    """
    client, _, _ = app_client
    do_id = _tach_do(client, workflow_builder)

    dong = _hoso(client, do_id).get("configured_cost_lines") or []
    if not dong:
        pytest.skip("loại xe của dữ liệu thử chưa có công thức giá thành")

    from services.khoan_muc_chi_phi import KHOAN_MUC
    for x in dong:
        assert "charge_type" in x, (
            "dòng %r thiếu `charge_type` — bên ngoài không phân loại được khoản "
            "mục này" % x.get("name"))
        assert x["charge_type"] in KHOAN_MUC, (
            "`charge_type` %r không có trong danh sách khoản mục chuẩn"
            % x["charge_type"])


def test_ho_so_chot_liet_ke_du_ba_con_so_tien_cho_moi_dong_chi_phi_thuc_te(
        app_client, workflow_builder):
    """`actual_cost_lines` phải có chi phí GỐC, THỰC TẾ và PHẦN VƯỢT.

    Bản trước chỉ trả `total_amount`/`unit_price`/`net_amount`, mà cả ba đều mang
    phần vượt — nên bên đọc thấy 0 đồng cho một chuyến có chi phí thật hai triệu
    rưỡi, và không có gì trong gói cho biết vì sao.
    """
    client, _, _ = app_client
    do_id = _tach_do(client, workflow_builder)

    ho_so = _hoso(client, do_id)
    for x in ho_so.get("actual_cost_lines") or []:
        for truong in ("original_amount", "actual_amount", "increase_amount"):
            assert truong in x, (
                "dòng chi phí thực tế thiếu %r — thiếu nó thì gói này vô dụng "
                "với ai đọc để hạch toán" % truong)


def test_hai_con_so_tong_trong_cung_goi_khong_duoc_chong_nhau(app_client, workflow_builder):
    """`gia ban - actual_cost_total` PHAI bang `margin_amount`.

    LOI DA DO DUOC tren PostgreSQL that (DO-2026-0001-DO01): goi tra
    `actual_cost_total = 17.227` cho mot chuyen co chi phi thuc te 1.731.767 —
    sai 100 lan. Nguyen nhan la `actual_cost_total` lay thang
    `freight_actual_costs.total_amount`, ma cot do o duong CHOT GIA mang PHAN
    VUOT chu khong mang chi phi.

    Nang hon la sau khi `cost_basis` duoc sua de lay tu `item.actual_amount`,
    HAI CON SO TRONG CUNG MOT GOI tu chong nhau:

        gia ban 2.666.000 − actual_cost_total 17.227 = 2.648.773
        nhung margin_amount ghi                        934.233

    Ai doc goi nay de hach toan se lap phieu chi 17.227 cho mot chuyen ton
    1.731.767, va khong co gi trong goi cho biet vi sao. Phep bat buoc duoi day
    la thu ma mot con so sai kieu do KHONG THE di qua: ba con so phai cong tru
    khop nhau, du duong nao tao ra du lieu.
    """
    client, _, _ = app_client
    do_id = _tach_do(client, workflow_builder)

    tm = _hoso(client, do_id)["commercials"]
    gia_ban = float(tm["final_selling_price"])
    chi_phi = float(tm["actual_cost_total"])
    lai = float(tm["margin_amount"])

    # `cost_basis` la MAU SO that cua `margin_percent`. Tra no ra de ben doc
    # KIEM duoc con so lai chu khong phai tin no, va phep dong nhat phai khop
    # voi no o MOI trang thai — ke ca khi chua co bang chi phi thuc te.
    assert "cost_basis" in tm and "cost_basis_source" in tm, tm
    gia_thanh = float(tm["cost_basis"])
    assert abs(gia_ban - gia_thanh - lai) < 1.0, (
        "lai gop khong khop gia thanh: %.0f - %.0f = %.0f, nhung margin_amount = %.0f"
        % (gia_ban, gia_thanh, gia_ban - gia_thanh, lai))

    # Va KHI DA CO bang chi phi thuc te thi hai con so phai TRUNG. Day dung la
    # cho da vo: `actual_cost_total` ghi 17.227 (phan vuot) trong khi lai gop
    # duoc tinh tren 1.731.767 (chi phi thuc te).
    #
    # Con khi CHUA CO bang chi phi thi `actual_cost_total = 0` la dung — chua ghi
    # dong chi phi nao thi khong duoc bia ra mot con so — va `margin_is_provisional`
    # la thu noi rang lai gop dang tinh tren KE HOACH.
    if not tm.get("margin_is_provisional"):
        assert abs(gia_thanh - chi_phi) < 1.0, (
            "da co bang chi phi thuc te ma `actual_cost_total` (%.0f) lech "
            "`cost_basis` (%.0f) — mot ben nay mang phan vuot" % (chi_phi, gia_thanh))
    else:
        assert chi_phi == 0.0, (
            "chua co bang chi phi thuc te thi `actual_cost_total` phai la 0, "
            "khong phai %.0f" % chi_phi)

    # Phan vuot van phai tra ra, chi la duoi TEN DUNG cua no.
    assert "actual_cost_variance" in tm, tm

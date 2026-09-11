# -*- coding: utf-8 -*-
"""`GET /api/handover/delivery-orders/{id}` — header + detail của DO đã hoàn tất cho bên công nợ.

Anh Khang: *"truyền ID header DO thì lấy luôn cả header và detail của nó"*. Khoá:
1. DO không có → 404; DO chưa hoàn tất → 409 `DO_NOT_COMPLETED` (không nhả số chưa chốt).
2. Hàm dựng gói: header mang mã DO/khách/báo giá/chuyến/xe/tổng tiền; details là
   từng dòng thu/chi có `acc_code` — cùng nguồn với khối Hồ sơ đã hoàn tất.
"""
from conftest import API_TEST_HEADERS
from routes.handover_routes import dong_goi_ban_giao


def test_khong_co_hoac_chua_hoan_tat_thi_khong_nha(app_client, workflow_builder):
    client, _, _ = app_client
    r = client.get("/api/handover/delivery-orders/DO-KHONG-CO", headers=API_TEST_HEADERS)
    assert r.status_code == 404
    workflow_builder.master_data()
    workflow_builder.quotation("QT-BG1", approve=True)
    workflow_builder.delivery_order("DO-BG1", "QT-BG1", approve=True)
    r = client.get("/api/handover/delivery-orders/DO-BG1", headers=API_TEST_HEADERS)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "DO_NOT_COMPLETED"


def test_dong_goi_header_va_details_tu_closeout():
    closeout = {
        "do_id": "DO-1", "status": "delivered", "currency": "VND", "customer_id": "CUS-1", "quotation_id": "QT-1",
        "delivery_order": {"id": "DO-1", "origin": "Kho A", "destination": "Cảng B", "weight_kg": 19000,
                           "delivery_window_end": "2026-09-10T06:29:00+07:00", "vehicle_id": "V1", "driver_id": "D1"},
        "route": {"id": "RT-1", "name": "A → B", "distance_km": 96.5},
        "trip": {"id": "TRIP-1", "status": "completed", "vehicle_id": "V1", "driver_id": "D1",
                 "actual_arrival_at": "2026-09-09T23:09:00+07:00"},
        "pod_records": [{"delivery_time": "2026-09-09T23:09:00+07:00", "receiver_name": "Anh Tư"}],
        "commercials": {"base_selling_price": 2556000.0, "customer_surcharge_total": 180000.0,
                        "final_selling_price": 2736000.0, "quoted_cost": 1750650.0, "actual_cost_total": 1781182.0,
                        "margin_amount": 954818.0, "margin_percent": 34.9},
        "ledger_totals": {"chi": 1781182.0, "thu": 2736000.0},
        "cost_formula": {"id": "CT-20", "name": "Đầu kéo 20'", "currency": "VND"},
        "ledger_lines": [
            {"kind": "chi", "cost_index": "6421", "acc_code": "6421", "charge_type": "fuel", "name": "Chi phí xăng dầu /km",
             "planned_amount": 745752.0, "actual_amount": 641182.0, "variance": -104570.0, "customer_extra": 0.0,
             "source": "vehicle", "calculation": "96.5 km × 7.728 VND", "actual_cost_line_id": "L1"},
            {"kind": "thu", "cost_index": "", "acc_code": "", "charge_type": "freight", "name": "Cước báo khách",
             "planned_amount": 2556000.0, "actual_amount": 2556000.0, "variance": 0.0, "customer_extra": 0.0,
             "source": "quotation", "calculation": ""},
        ],
    }
    g = dong_goi_ban_giao(closeout)
    h, d = g["header"], g["details"]
    assert h["do_id"] == "DO-1" and h["customer_id"] == "CUS-1" and h["quotation_id"] == "QT-1"
    assert h["trip_id"] == "TRIP-1" and h["vehicle_id"] == "V1" and h["route"]["distance_km"] == 96.5
    assert h["pod_count"] == 1 and h["pod_receiver"] == "Anh Tư"
    assert h["final_selling_price"] == 2736000.0 and h["actual_cost_total"] == 1781182.0
    assert len(d) == 2
    # Mỗi dòng mang `currency` của chính nó (thêm 11/09): dòng chi theo phiếu chi phí, dòng
    # thu theo báo giá — trước đây mảng này trộn hai đơn vị mà không có nhãn nào.
    assert d[0] == {"line_no": 1, "kind": "chi", "acc_code": "6421", "missing_acc_code": False, "charge_type": "fuel", "currency": "VND",
                    "name": "Chi phí xăng dầu /km", "planned_amount": 745752.0, "actual_amount": 641182.0,
                    "customer_extra": 0.0, "variance": -104570.0, "source": "vehicle",
                    "calculation": "96.5 km × 7.728 VND", "ref_id": "L1"}
    assert d[1]["kind"] == "thu" and d[1]["missing_acc_code"] is True

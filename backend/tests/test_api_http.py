"""Gọi thật các điểm cuối HTTP qua TestClient, không cần bật máy chủ riêng."""

import os
import sys
import uuid

GOC_APP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app"))
sys.path.insert(0, GOC_APP)

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402

_loi = []


def kiem(dieu_kien, nhan):
    if dieu_kien:
        print(f"  OK   {nhan}")
    else:
        print(f"  FAIL {nhan}")
        _loi.append(nhan)


def chay():
    client = TestClient(main.app)

    print("\n[A] Máy chủ sống và có đủ điểm cuối")
    r = client.get("/health")
    kiem(r.status_code == 200 and r.json().get("status") == "ok", "/health trả ok")
    # Hỏi THẲNG từng điểm cuối thay vì soi app.routes: bản Starlette này gói
    # router con lại nên danh sách route ở ngoài không nhìn thấy chúng, và soi
    # kiểu đó báo hỏng trong khi API vẫn chạy đúng.
    for dd in ("/api/sales-orders", "/api/packing-lists", "/api/deliveries",
               "/api/customers", "/api/vehicles", "/api/drivers",
               "/api/packing-lists/stats", "/api/deliveries/stats"):
        kiem(client.get(dd).status_code == 200, f"điểm cuối {dd} trả 200")

    print("\n[B] Trang và tệp tĩnh")
    kiem(client.get("/").status_code == 200, "trang chủ mở được")
    for tep in [
        "/static/lang.json",
        "/static/css/khung.css",
        "/static/js/khung.js",
        "/static/modules/don-hang/don-hang.html",
        "/static/modules/don-hang/don-hang.js",
        "/static/modules/don-hang/don-hang.css",
        "/static/modules/packing-list/packing-list.html",
        "/static/modules/packing-list/packing-list.js",
        "/static/modules/packing-list/packing-list.css",
        "/static/modules/giao-hang/giao-hang.html",
        "/static/modules/giao-hang/giao-hang.js",
        "/static/modules/giao-hang/giao-hang.css",
        "/static/modules/quet-tem/quet-tem.html",
        "/static/modules/quet-tem/quet-tem.js",
        "/static/modules/quet-tem/quet-tem.css",
    ]:
        kiem(client.get(tep).status_code == 200, f"tải được {tep}")

    print("\n[C] Bốn thứ tiếng phải đủ khoá")
    tu_dien = client.get("/static/lang.json").json()
    thieu = [
        k
        for k, v in tu_dien.items()
        if not isinstance(v, dict) or not v.get("vi") or not v.get("en") or not v.get("lo")
    ]
    kiem(not thieu, f"mọi khoá đều có vi/en/lo ({len(tu_dien)} khoá)" + (f" — thiếu: {thieu[:5]}" if thieu else ""))

    print("\n[D] Luồng qua API")
    po = "HTTP-" + uuid.uuid4().hex[:6].upper()
    r = client.post(
        "/api/sales-orders",
        json={
            "po_number": po,
            "ship_to_name": "PTTLAO DONEKOY",
            "currency": "LAK",
            "lines": [
                {"line_no": 1, "description": "BISKIO DINO 15g", "barcode": "885", "case_qty": 8, "piece_qty": 96, "unit_price": 343000, "amount": 686000, "weight_kg": 6.5},
            ],
        },
    )
    kiem(r.status_code == 200, f"tạo đơn qua API (HTTP {r.status_code})")
    don = r.json()["data"]
    dong_id = don["lines"][0]["id"]

    r = client.post(
        f"/api/sales-orders/{don['id']}/packing-lists",
        json={"items": [{"so_line_id": dong_id, "case_qty": 3}], "box_count": 3},
    )
    kiem(r.status_code == 200, f"tạo Packing List qua API (HTTP {r.status_code})")
    pl = r.json()["data"]
    kiem(len(pl["labels"]) == 3, "sinh 3 tem QR")
    kiem(pl["items"][0]["so_line_id"] == dong_id, "dòng hàng gắn đúng dòng của đơn")

    token = pl["labels"][0]["qr_token"]
    r = client.get(f"/api/labels/{token}/qr.svg")
    kiem(r.status_code == 200 and b"<svg" in r.content, "sinh được ảnh QR cho tem")

    r = client.post("/api/labels/scan", json={"token": token})
    kiem(r.status_code == 200, "quét tem qua API")
    kq = r.json()["data"]
    kiem(kq["sales_order"]["id"] == don["id"], "quét ra đúng đơn hàng")
    kiem(kq["packing_list"]["id"] == pl["id"], "quét ra đúng Packing List")

    print("\n[E] Lỗi nghiệp vụ trả về MÃ ổn định để giao diện dịch được")
    r = client.post(
        f"/api/sales-orders/{don['id']}/packing-lists",
        json={"items": [{"so_line_id": dong_id, "case_qty": 999}]},
    )
    ct = r.json().get("detail") or {}
    kiem(r.status_code == 409 and ct.get("code") == "PL_OVER_ORDERED", f"đóng vượt bị chặn bằng mã ({ct.get('code')})")
    kiem(bool((ct.get("detail") or {}).get("lines")), "lỗi nói rõ dòng nào vượt")

    r = client.post("/api/labels/scan", json={"token": "SAI"})
    kiem(
        r.status_code == 404 and (r.json().get("detail") or {}).get("code") == "LABEL_NOT_FOUND",
        "quét tem lạ trả mã LABEL_NOT_FOUND",
    )

    print("\n[F] Mã lỗi nào cũng phải có bản dịch")
    ma_can = ["PL_OVER_ORDERED", "LABEL_NOT_FOUND", "PL_NO_POD", "DL_MISSING_POD", "POD_NO_RECEIVER"]
    thieu_dich = [m for m in ma_can if ("err_" + m) not in tu_dien]
    kiem(not thieu_dich, f"lang.json có bản dịch cho các mã lỗi hay gặp" + (f" — thiếu {thieu_dich}" if thieu_dich else ""))

    print("\n" + "=" * 60)
    if _loi:
        print(f"CÓ {len(_loi)} MỤC HỎNG:")
        for x in _loi:
            print("  -", x)
        sys.exit(1)
    print("API VÀ GIAO DIỆN TĨNH: ĐỦ VÀ ĐÚNG")
    sys.exit(0)


if __name__ == "__main__":
    chay()

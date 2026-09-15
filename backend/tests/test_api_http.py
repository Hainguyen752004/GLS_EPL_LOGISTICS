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
        "/static/modules/khach-hang/khach-hang.html",
        "/static/modules/khach-hang/khach-hang.js",
        "/static/modules/khach-hang/khach-hang.css",
        "/static/modules/theo-doi/theo-doi.html",
        "/static/modules/theo-doi/theo-doi.js",
        "/static/modules/theo-doi/theo-doi.css",
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
    khach = [c for c in client.get("/api/customers").json()["data"] if c["kind"] == "customer"]
    kiem(bool(khach), "danh mục có khách nhận hàng để chọn")
    ncc = [c for c in client.get("/api/customers?kind=vendor").json()["data"]]
    r = client.post("/api/sales-orders", json={"po_number": "HTTP-KHONG-KHACH", "lines": [{"description": "x", "case_qty": 1}]})
    kiem(
        r.status_code == 400 and (r.json().get("detail") or {}).get("code") == "SO_NO_CUSTOMER",
        "đơn không chọn khách từ danh mục bị chặn (SO_NO_CUSTOMER)",
    )
    po = "HTTP-" + uuid.uuid4().hex[:6].upper()
    r = client.post(
        "/api/sales-orders",
        json={
            "po_number": po,
            "customer_id": khach[0]["id"],
            "vendor_id": ncc[0]["id"] if ncc else None,
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

    kiem(don["ship_to_name"] == khach[0]["name"], "tên khách trên đơn lấy từ danh mục, không từ ô gõ tay")

    print("\n[D2] Danh mục khách hàng")
    ma = "KH-" + uuid.uuid4().hex[:5].upper()
    r = client.post("/api/customers", json={"code": ma, "name": "Khách kiểm", "kind": "customer", "lat": 17.9, "lng": 102.6})
    kiem(r.status_code == 200, "tạo khách hàng")
    kh_id = r.json()["data"]["id"]
    r = client.post("/api/customers", json={"code": ma, "name": "Trùng", "kind": "customer"})
    kiem(r.status_code == 409 and r.json()["detail"]["code"] == "CUST_CODE_DUPLICATE", "mã trùng bị chặn")
    r = client.post("/api/customers", json={"code": ma + "X", "name": "Nửa toạ độ", "lat": 17.9})
    kiem(r.status_code == 400 and r.json()["detail"]["code"] == "CUST_COORD_HALF", "toạ độ thiếu một nửa bị chặn")
    r = client.put(f"/api/customers/{kh_id}", json={"code": ma, "name": "Khách kiểm 2", "kind": "customer"})
    kiem(r.status_code == 200 and r.json()["data"]["name"] == "Khách kiểm 2", "sửa khách hàng")
    kiem(client.delete(f"/api/customers/{kh_id}").status_code == 200, "xoá khách chưa dùng")
    r = client.delete(f"/api/customers/{khach[0]['id']}")
    kiem(r.status_code == 409 and r.json()["detail"]["code"] == "CUST_IN_USE", "khách đang có đơn thì không xoá được")

    print("\n[D3] Theo dõi xe")
    r = client.get("/api/tracking")
    kiem(r.status_code == 200 and isinstance(r.json()["data"], list), "danh sách chuyến đang theo dõi")
    ds_gh = client.get("/api/deliveries?status=arrived").json()["data"]["items"] or client.get("/api/deliveries?status=in_transit").json()["data"]["items"]
    if ds_gh:
        gh_id = ds_gh[0]["id"]
        r = client.post(f"/api/tracking/{gh_id}/position", json={"lat": 17.95, "lng": 102.62, "speed_kmh": 40, "source": "gps"})
        kiem(r.status_code == 200 and r.json()["data"]["position"]["lat"] == 17.95, "thiết bị gửi vị trí GPS lên được")
        r = client.get(f"/api/tracking/{gh_id}")
        kiem(r.status_code == 200 and len(r.json()["data"]["trail"]) >= 1, "đọc được vệt đường của chuyến")
        r = client.post(f"/api/tracking/{gh_id}/position", json={"lat": 999, "lng": 0})
        kiem(r.status_code == 400 and r.json()["detail"]["code"] == "TRK_BAD_COORD", "toạ độ ngoài phạm vi bị chặn")
    else:
        print("  (bỏ qua: không có chuyến đang chạy để thử vị trí)")

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

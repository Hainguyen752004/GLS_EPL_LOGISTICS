# -*- coding: utf-8 -*-
"""Thử phần máy chủ của màn Khách hàng mới (30/09): mã khách (= mã bên kế toán), loại khách, công nợ mọi khách, mã khách
trong gói bàn giao DO.

    python kiem/thu_khach_hang_moi.py [http://127.0.0.1:8011]

CHỈ chạy trên máy thử (bản sao DB): bài ghi mã khách thử rồi TRẢ LẠI mã cũ, và tạo lại khoá bàn giao của máy đang gọi.
"""
import json
import sys
import urllib.error
import urllib.request

GOC = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"
if GOC.rstrip("/").endswith((":8020", ":8010")):
    sys.exit("Không chạy bài này trên máy thật.")
TK, LOI = {}, []


def goi(duong, body=None, u=None, method=None, khoa=None):
    dau = {"Content-Type": "application/json"}
    if u:
        dau["Authorization"] = "Bearer " + TK[u]
    if khoa:
        dau["Authorization"] = "Bearer " + khoa
    r = urllib.request.Request(GOC + duong, data=json.dumps(body).encode() if body is not None else None,
                               method=method or ("POST" if body is not None else "GET"), headers=dau)
    try:
        with urllib.request.urlopen(r, timeout=120) as t:
            return t.status, json.loads(t.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except ValueError:
            return e.code, {}


def dung(dk, buoc):
    print("  %s %s" % ("✓" if dk else "SAI", buoc))
    sys.stdout.flush()
    if not dk:
        LOI.append(buoc)


def ma_loi(g):
    return ((g or {}).get("detail") or {}).get("ma")


def main():
    for u in ("admin", "ketoan", "thabok", "tx01"):
        TK[u] = goi("/api/dang-nhap", {"username": u, "password": "1234"})[1]["token"]
    s, ds = goi("/api/customers", u="admin")
    dung(s == 200 and len(ds) >= 2 and all("code" in k and "cust_type" in k for k in ds), "danh sách khách có ô code, cust_type (%d khách)" % len(ds))
    a, b = ds[0], ds[1]
    cu = {k["id"]: (k.get("code"), k.get("cust_type")) for k in ds}
    try:
        print("1. Mã khách và loại khách")
        s, g = goi("/api/customers/" + a["id"], {"code": "KIEM-KH-01", "cust_type": "company"}, u="thabok", method="PUT")
        dung(s == 200 and g["code"] == "KIEM-KH-01" and g["cust_type"] == "company", "Bãi (được sửa khách) ghi mã KIEM-KH-01, loại công ty")
        s, g = goi("/api/customers/" + b["id"], {"code": "kiem-kh-01"}, u="admin", method="PUT")
        dung(s == 409 and ma_loi(g) == "MA_KHACH_TRUNG", "mã trùng (khác hoa thường) → 409 MA_KHACH_TRUNG")
        s, g = goi("/api/customers/" + b["id"], {"code": "ຄຳ 01"}, u="admin", method="PUT")
        dung(s == 422 and ma_loi(g) == "MA_KHACH_SAI", "mã có chữ Lào / dấu cách → 422 MA_KHACH_SAI")
        s, g = goi("/api/customers/" + b["id"], {"code": "X" * 51}, u="admin", method="PUT")
        dung(s == 422 and ma_loi(g) == "MA_KHACH_SAI", "mã dài hơn 50 ký tự → 422")
        s, g = goi("/api/customers/" + b["id"], {"cust_type": "shop"}, u="admin", method="PUT")
        dung(s == 422 and ma_loi(g) == "LOAI_KHACH_SAI", "loại khách lạ → 422 LOAI_KHACH_SAI")
        s, g = goi("/api/customers/" + a["id"], {"code": "KIEM-KH-01"}, u="admin", method="PUT")
        dung(s == 200, "ghi lại đúng mã của chính khách đó → 200 (không tự báo trùng với mình)")
        s, g = goi("/api/customers/" + a["id"], {"code": "", "cust_type": ""}, u="admin", method="PUT")
        dung(s == 200 and g["code"] is None and g["cust_type"] is None, "xoá trống mã, loại → null")
        goi("/api/customers/" + a["id"], {"code": "KIEM-KH-01"}, u="admin", method="PUT")

        print("2. Công nợ mọi khách")
        s, g = goi("/api/customers-cong-no", u="ketoan")
        dung(s == 200 and isinstance(g, dict), "kế toán → 200, %d khách có tờ" % len(g or {}))
        if g:
            cid, x = next(iter(g.items()))
            s1, mot = goi("/api/customers/%s/cong-no" % cid, u="ketoan")
            khop = s1 == 200 and all(mot[k] == x[k] for k in ("so_to", "so_to_no", "tong_lak", "da_thu_lak", "con_no_lak", "tong_tien", "con_no_tien"))
            dung(khop, "số của một khách ở danh sách = số ở hồ sơ khách đó (%s: còn nợ %s LAK)" % (cid, x.get("con_no_lak")))
        dung(goi("/api/customers-cong-no", u="thabok")[0] == 403, "Bãi → 403 (không thấy tiền bán)")
        dung(goi("/api/customers-cong-no", u="tx01")[0] == 403, "tài xế → 403")
        dung(goi("/api/customers-cong-no")[0] == 401, "không đăng nhập → 401")

        print("3. Mã khách trong gói bàn giao DO")
        khoa = goi("/api/handover/tao-khoa", method="POST", u="admin")[1]["token_nhan_qlsx"]
        s, g = goi("/api/handover/delivery-orders?page_size=200", khoa=khoa)
        items = g["data"]["items"]
        cua_a = [x for x in items if x["customer_id"] == a["id"]]
        dung(all(x.get("customer_code") == "KIEM-KH-01" for x in cua_a), "dòng danh sách của khách có customer_code (%d DO)" % len(cua_a))
        if cua_a:
            s, g2 = goi("/api/handover/delivery-orders?page_size=200&customer_id=KIEM-KH-01", khoa=khoa)
            dung(s == 200 and g2["data"]["total"] == len(cua_a), "lọc theo mã khách bên kế toán → đúng %d DO" % len(cua_a))
            s, g3 = goi(cua_a[0]["detail_url"], khoa=khoa)
            dung(s == 200 and g3["data"]["header"]["customer_code"] == "KIEM-KH-01", "header chi tiết có customer_code")
    finally:
        for cid, (m, l) in cu.items():
            goi("/api/customers/" + cid, {"code": m or "", "cust_type": l or ""}, u="admin", method="PUT")
        print("  · đã trả lại mã, loại khách như cũ")
    print("\n%s" % ("ĐẠT hết" if not LOI else "SAI %d chỗ:\n  - " % len(LOI) + "\n  - ".join(LOI)))
    sys.exit(1 if LOI else 0)


if __name__ == "__main__":
    main()

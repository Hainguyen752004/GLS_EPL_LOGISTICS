# -*- coding: utf-8 -*-
"""Thử GỬI SO THẬT (đề nghị thu → SO + công nợ khách) qua API GLS CHẠY Ở MÁY EM (01/10).

    python kiem/thu_tao_so_that.py [http://127.0.0.1:8011] [http://127.0.0.1:5090]

CHỈ chạy trên máy thử 8011 nối 5090 (DB demo Lào anh Tune đã sao lưu). Lấy một DO đã khoá có khách CHƯA có mã bên kế toán:
xem trước báo sẽ tạo khách EPLKH-<id> → KT Thu/Chi bấm gửi → khách có bên kế toán, mã ghi vào danh mục khách bên em →
SO tạo được, hoặc bên đó từ chối với câu rõ (ví dụ tiền cước USD chưa có trong danh mục tiền tệ bên đó) và lần gửi được ghi lại.
"""
import json
import os
import sys
import urllib.error
import urllib.request

GOC = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011").rstrip("/")
KT = (sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:5090").rstrip("/")
if GOC.endswith((":8020", ":8010")):
    sys.exit("Không chạy bài này trên máy thật.")
TK, LOI = {}, []
TOKEN_KT = next(d.split("=", 1)[1].strip().strip('"').strip("'") for d in open(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".env"), encoding="utf-8") if d.strip().startswith("EPL_ACC_CODE_TOKEN="))


def _http(url, body=None, dau=None, method=None):
    r = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                               method=method or ("POST" if body is not None else "GET"), headers={"Content-Type": "application/json", **(dau or {})})
    try:
        with urllib.request.urlopen(r, timeout=120) as t:
            return t.status, json.loads(t.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except ValueError:
            return e.code, {}


def goi(duong, body=None, vai=None, method=None):
    return _http(GOC + duong, body, {"Authorization": "Bearer " + TK[vai]} if vai else None, method)


def dung(dk, buoc, them=""):
    print("  %s %s %s" % ("✓" if dk else "SAI", buoc, them))
    sys.stdout.flush()
    if not dk:
        LOI.append(buoc)


def main():
    for u in ("ketoan", "admin"):
        TK[u] = goi("/api/dang-nhap", {"username": u, "password": "1234"})[1]["token"]
    s, khs = goi("/api/customers", vai="ketoan")
    chua = {k["id"] for k in khs if not k.get("code")}
    import datetime as dt
    hang, t = [], dt.date.today().replace(day=1)
    for _ in range(4):                                            # tháng này rồi lùi dần — DO đã khoá có thể ở tháng trước
        s, ds = goi("/api/de-nghi-thu?thang=%s" % t.strftime("%Y-%m"), vai="ketoan")
        hang += (ds.get("ds") if isinstance(ds, dict) else ds) or []
        t = (t - dt.timedelta(days=1)).replace(day=1)
    do = None
    for x in hang:
        # 01/10 bỏ trang kế toán tạm: mọi DO đã khoá gửi SO từ đầu — chỉ bỏ qua DO đã có SO hoặc chưa khoá
        if (x.get("so_ke_toan") or {}).get("da_tao_so") or x.get("da_tao_so") or not x.get("locked"):
            continue
        cid = (goi("/api/trips/%s" % x["trip_id"], vai="admin")[1] or {}).get("customer_id")
        if cid in chua:
            do = x
            break
    cid = (goi("/api/trips/%s" % do["trip_id"], vai="admin")[1] or {}).get("customer_id") if do else None
    if do is None:
        print("  · không còn DO đã khoá nào có khách chưa có mã — bỏ qua")
        return ket_thuc()
    tid = do["trip_id"]
    print("  · DO %s · khách %s" % (do["doc_no"], do["customer_name"]))
    s, v = goi("/api/trips/%s/tao-so" % tid, vai="ketoan")
    tt = v.get("tom_tat") or {}
    dung(s == 200 and tt.get("tao_khach") == "EPLKH-" + cid, "xem trước: sẽ tạo khách bên kế toán", tt.get("tao_khach"))
    s, g = goi("/api/trips/%s/tao-so" % tid, {}, "ketoan")
    k = next((x for x in goi("/api/customers", vai="ketoan")[1] if x["id"] == cid), {})
    dung(k.get("code") == "EPLKH-" + cid, "khách đã có mã bên kế toán trong danh mục bên em", k.get("code"))
    s3, kq = _http(KT + "/api/v1/master-data/customers/list", {"PageIndex": 1, "ObjKey": "EPLKH-" + cid}, {"Authorization": "Bearer " + TOKEN_KT})
    co = [x for x in (((kq or {}).get("Result") or {}).get("Data") or []) if x.get("ObjectNo") == "EPLKH-" + cid]
    dung(len(co) == 1, "khách có trong danh mục khách bên kế toán", co[0].get("Name") if co else "")
    if s == 200:
        tr = g.get("trang_thai") or {}
        dung(tr.get("da_tao_so") and tr.get("order_code"), "SO tạo được bên kế toán", "%s · %s %s" % (tr.get("order_code"), tr.get("total_amount"), tr.get("currency")))
    else:
        d = (g or {}).get("detail") or {}
        dung(bool(d.get("loi")) and d.get("ma") != "LOGISTICS_52905", "bên kế toán từ chối nhưng KHÔNG còn vì thiếu khách (52905) — câu lỗi rõ",
             "%s · %s" % (d.get("ma"), (d.get("loi") or "")[:120]))
    ket_thuc()


def ket_thuc():
    print("\nGỬI SO THẬT: %s" % ("ĐẠT" if not LOI else "SAI %d — %s" % (len(LOI), "; ".join(LOI))))
    sys.exit(1 if LOI else 0)


if __name__ == "__main__":
    main()

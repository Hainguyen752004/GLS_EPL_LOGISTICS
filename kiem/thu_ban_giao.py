# -*- coding: utf-8 -*-
"""Thử API BÀN GIAO DO cho hệ kế toán anh Tune (30/09) — đúng khuôn EPL_System, khoá máy riêng, mặc định chỉ phiếu đã khoá
(06/10: `scope=all` có cả DO đang chạy, B2 trả DO chưa xong với status thật — mục 5).

    python kiem/thu_ban_giao.py [http://127.0.0.1:8011]
    python kiem/thu_ban_giao_trong_gd.py      (cùng bài, chạy trong tiến trình trên bản sao _d7, cuối ROLLBACK — thử mã mới
                                               mà không phải khởi động lại máy 8011)

CHỈ chạy trên máy thử (bản sao DB): bài này TẠO LẠI khoá `token_nhan_qlsx` của máy đang gọi. Ngoài khoá đó không đổi dữ
liệu. Không in khoá ra màn hình.

Đặt `KHOA_BAN_GIAO_TEP=<tệp chứa khoá đang dùng>` thì bài dùng khoá đó, KHÔNG tạo lại — để chạy được trên một máy
thử dùng chung DB với máy khác mà không làm hỏng khoá bên kia đang cầm.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

GOC = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"
if GOC.rstrip("/").endswith((":8020", ":8010")):
    sys.exit("Không chạy bài này trên máy thật — nó tạo lại khoá bàn giao.")
TK = {}
LOI = []
DANH_MUC = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app", "services",
                                       "danh_muc_tai_khoan_lao.json"), encoding="utf-8"))


def goi(duong, body=None, u=None, method=None, khoa=None):
    du = json.dumps(body).encode() if body is not None else None
    dau = {"Content-Type": "application/json"}
    if u:
        dau["Authorization"] = "Bearer " + TK[u]
    if khoa is not None:
        dau["Authorization"] = "Bearer " + khoa
    r = urllib.request.Request(GOC + duong, data=du, method=method or ("POST" if du is not None else "GET"), headers=dau)
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


def ma_that(ma):
    """Mỗi vế của 'no/co' phải là mã có trong danh mục Lào — hoặc một trong ba mã con chờ anh Tune mở."""
    ds = {x["code"] for x in DANH_MUC["tai_khoan"]}
    return all(v in ds or v in ("1371", "4021", "4022") for v in (ma or "").split("/") if v)


def main():
    for u in ("admin", "ketoan", "thabok", "tx01"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"})
        TK[u] = g["token"]

    print("1. Quyền các đường quản trị")
    dung(goi("/api/handover/trang-thai", u="admin")[0] == 200, "Sếp xem trạng thái bàn giao → 200")
    dung(goi("/api/handover/trang-thai", u="ketoan")[0] == 403, "kế toán xem trạng thái → 403")
    dung(goi("/api/handover/trang-thai")[0] == 401, "không đăng nhập → 401")
    dung(goi("/api/handover/tao-khoa", method="POST", u="ketoan")[0] == 403, "kế toán tạo khoá → 403")
    tep_khoa = os.getenv("KHOA_BAN_GIAO_TEP")
    if tep_khoa:
        khoa = open(tep_khoa, encoding="utf-8").read().strip()
        print("     dùng khoá có sẵn trong %s (dài %d ký tự, không in) — không tạo lại" % (os.path.basename(tep_khoa), len(khoa)))
    else:
        s, g = goi("/api/handover/tao-khoa", method="POST", u="admin")
        khoa = (g or {}).get("token_nhan_qlsx") or ""
        dung(s == 200 and len(khoa) >= 40, "Sếp tạo khoá → 200, khoá dài %d ký tự (không in)" % len(khoa))
    s, g = goi("/api/handover/trang-thai", u="admin")
    dung(g.get("co_khoa") is True and "token_nhan_qlsx" not in json.dumps(g), "trạng thái chỉ báo 'đã có khoá', không lộ khoá")
    tong_khoa = g.get("so_do_ban_giao_duoc")

    print("2. Khoá máy")
    dung(goi("/api/handover/delivery-orders")[0] == 401, "không khoá → 401")
    dung(goi("/api/handover/delivery-orders", khoa="sai-" + khoa[:8])[0] == 401, "khoá sai → 401")
    dung(goi("/api/handover/delivery-orders", u="admin")[0] == 401, "phiên đăng nhập của Sếp KHÔNG thay được khoá máy → 401")

    print("3. Danh sách")
    s, g = goi("/api/handover/delivery-orders?page_size=200", khoa=khoa)
    d = (g or {}).get("data") or {}
    items = d.get("items") or []
    dung(s == 200 and d.get("total") == tong_khoa, "200, total %s = số phiếu đã về và đã khoá %s" % (d.get("total"), tong_khoa))
    dung(all(x["do_id"].startswith("EPLLAO-") and x["status"] == "delivered" for x in items), "mọi dòng mã EPLLAO-…, delivered")
    can = {"do_id", "status", "customer_id", "quotation_id", "route_id", "vehicle_id", "driver_id", "selling_price",
           "customer_surcharge_total", "final_selling_price", "currency", "completed_at", "completed_by", "detail_url"}
    dung(all(can <= set(x) for x in items), "mỗi dòng có đủ 14 khoá của EPL_System (hệ anh Tune đọc Summary từ đây)")
    dung(all(x["completed_at"] is None or x["completed_at"].endswith("+00:00") for x in items), "giờ khoá ghi rõ +00:00")
    tien = sorted({x["currency"] for x in items})
    print("     %d DO · tiền cước: %s" % (len(items), ", ".join(tien)))
    ngay = [x["completed_at"] for x in items if x["completed_at"]]
    dung(ngay == sorted(ngay, reverse=True), "mới khoá trước")
    s2, g2 = goi("/api/handover/delivery-orders?page=1&page_size=2", khoa=khoa)
    dung(len(g2["data"]["items"]) == min(2, len(items)) and g2["data"]["total"] == d.get("total"), "phân trang: trang 2 dòng, total giữ nguyên")
    if items:
        kh = items[0]["customer_ref"]
        s3, g3 = goi("/api/handover/delivery-orders?page_size=200&customer_id=%s" % kh, khoa=khoa)
        dung(all(x["customer_ref"] == kh for x in g3["data"]["items"]) and g3["data"]["total"] >= 1, "lọc theo mã khách bên em")
    dung(all(x["customer_id"] == x["customer_code"] for x in items), "customer_id = mã khách bên kế toán (null khi chưa gán)")
    s4, g4 = goi("/api/handover/delivery-orders?completed_from=2099-01-01", khoa=khoa)
    dung(s4 == 200 and g4["data"]["total"] == 0, "lọc từ ngày tương lai → 0")
    dung(goi("/api/handover/delivery-orders?completed_to=30-09-2026", khoa=khoa)[0] == 422, "ngày sai dạng → 422")

    print("3b. Tìm theo chữ q (màn Vụ việc bên anh Tune tìm trên toàn bộ DO)")
    o_tim = ("do_id", "doc_no", "customer_id", "customer_name", "truck_no", "plate_head")

    def tim(chu, co=200, trang=1):
        s, g = goi("/api/handover/delivery-orders?page=%d&page_size=%d&q=%s" % (trang, co, urllib.parse.quote(chu)), khoa=khoa)
        return s, (g or {}).get("data") or {}

    def khop(x, chu):
        return any(chu.lower() in str(x.get(o) or "").lower() for o in o_tim)

    if items:
        x0 = items[-1]
        for o, chu in (("số phiếu", x0["doc_no"]), ("mã DO", x0["do_id"][-6:].upper()), ("số xe", x0["truck_no"]),
                       ("biển đầu kéo", x0["plate_head"]), ("tên khách", (x0["customer_name"] or "")[:5]),
                       ("mã khách bên kế toán", next((x["customer_id"] for x in items if x["customer_id"]), None))):
            if not chu:
                print("     bỏ qua %s: không có dữ liệu mẫu" % o)
                continue
            s, d = tim(chu)
            mong = [x["do_id"] for x in items if khop(x, chu)]
            dung(s == 200 and d.get("q") == chu.strip() and [x["do_id"] for x in d.get("items") or []] == mong
                 and d.get("total") == len(mong),
                 "q theo %s %r → %d DO, đúng các dòng chứa chữ đó, total = số sau lọc" % (o, chu, len(mong)))
        chu = x0["doc_no"][:2]
        s, d = tim(chu)
        tong_loc = d.get("total") or 0
        s1, d1 = tim(chu, co=1, trang=1)
        s2, d2 = tim(chu, co=1, trang=max(1, tong_loc))
        dung(d1.get("total") == d2.get("total") == tong_loc and len(d1.get("items") or []) == min(1, tong_loc)
             and (tong_loc < 2 or d1["items"][0]["do_id"] != d2["items"][0]["do_id"]),
             "phân trang khi tìm: trang 1 cỡ 1 và trang cuối khác nhau, total giữ = %d" % tong_loc)
    s, d = tim("khong-co-phieu-nay-%_")
    dung(s == 200 and d.get("total") == 0 and d.get("items") == [], "chữ không có → 0 dòng, total 0")
    s, d = tim("%")
    dung(s == 200 and d.get("total") == 0, "'%' là chữ thường, không phải ký tự đại diện → 0")
    s, d = tim("   ")
    dung(s == 200 and d.get("q") is None and d.get("total") == tong_khoa, "q toàn dấu cách = không lọc")
    dung(goi("/api/handover/delivery-orders?q=" + "a" * 201, khoa=khoa)[0] == 422, "q dài hơn 200 ký tự → 422")

    print("4. Chi tiết")
    thieu_ma, sai_ma, lech = [], [], []
    lk = 0
    for x in items:
        s, g = goi(x["detail_url"], khoa=khoa)
        if s != 200:
            LOI.append("chi tiết %s → %s" % (x["do_id"], s))
            continue
        h, ds = g["data"]["header"], g["data"]["details"]
        thu = [dg for dg in ds if dg["kind"] == "thu"]
        if not (h["do_id"] == x["do_id"] and len(thu) == 1 and thu[0]["actual_amount"] == h["final_selling_price"] == x["final_selling_price"]
                and thu[0]["currency"] == h["currency"] == x["currency"] and thu[0]["acc_code"] == "1211/708"):
            LOI.append("dòng thu / header lệch ở %s" % x["do_id"])
        chi = [dg for dg in ds if dg["kind"] == "chi"]
        epl = [dg for dg in chi if dg["paid_by"] == "epl"]
        thieu_ma += [(h["doc_no"], dg["name"]) for dg in epl if not dg["acc_code"]]
        sai_ma += [(h["doc_no"], dg["acc_code"]) for dg in epl if dg["acc_code"] and not ma_that(dg["acc_code"])]
        if any(dg["acc_code"] for dg in chi if dg["paid_by"] == "chu_xe"):
            LOI.append("dòng chủ xe tự trả mà có định khoản ở %s" % x["do_id"])
        # Σ từng dòng (làm tròn từng dòng) ≈ tổng theo mục (làm tròn từng mục) — lệch tối đa 1 Kíp mỗi dòng
        if abs(sum(dg["amount_lak"] for dg in epl) - h["actual_cost_total_lak"]) > len(epl):
            lech.append((h["doc_no"], sum(dg["amount_lak"] for dg in epl), h["actual_cost_total_lak"]))
        # khoá màn "Vụ việc" bên anh Tune đọc (GLS-QLSX-Web cm-source-reference-modal.js)
        if not (h["trip_status"] == "completed" and h["actual_cost_total"] == h["actual_cost_total_lak"]
                and h["margin_amount"] == h["margin"] and (h["fx_rate"] is None) == (h["currency"] == "LAK")
                and all(dg.get("calculation") for dg in ds) and h["customer_id"] == h["customer_code"]):
            LOI.append("khoá màn Vụ việc bên kế toán thiếu / lệch ở %s" % x["do_id"])
        if h["company"] == "joint":
            lk += 1
            if not (h.get("hire") and h["hire"]["acc_code"] == "621/4022" and "amount" in h["hire"]):
                LOI.append("xe thuê %s thiếu khối hire" % x["do_id"])
        elif h.get("hire"):
            LOI.append("xe nhà %s lại có khối hire" % x["do_id"])
    dung(not [e for e in LOI if e.startswith(("chi tiết", "dòng thu"))], "mọi DO: 200, một dòng thu 1211/708 bằng đúng cước và tiền của header")
    dung(not [e for e in LOI if e.startswith("khoá màn Vụ việc")],
         "mọi DO có khoá màn Vụ việc bên kế toán đọc: trip_status, actual_cost_total, margin_amount, fx_rate, calculation")
    dung(not thieu_ma, "mọi dòng EPL chi đều có định khoản%s" % ("" if not thieu_ma else " — thiếu: %s" % thieu_ma[:5]))
    dung(not sai_ma, "mọi định khoản là mã thật trong danh mục Lào (hoặc 1371/4021/4022 chờ mở)%s" % ("" if not sai_ma else ": %s" % sai_ma[:5]))
    dung(not lech, "Σ dòng chi EPL khớp tổng chi phiếu%s" % ("" if not lech else ": %s" % lech[:5]))
    dung(not [e for e in LOI if "hire" in e or "chủ xe tự trả" in e], "xe thuê có khối hire (%d phiếu), không có dòng thuê tự đặt mã" % lk)

    print("5. Phiếu chưa khoá, mã sai, xem trước")
    s, ds = goi("/api/trips?co=80", u="admin")
    mo = next((p for p in ds if not p.get("locked")), None)
    if mo:
        # 06/10: DO chưa xong cũng bàn giao (Vụ việc cho phiếu chi tạm ứng / mục V–VI) — status nói thật, Web cũ chỉ nhận
        # "delivered" nên vẫn không lập được gì trên DO này; trước 06/10 là 409 DO_CHUA_KHOA
        s, g = goi("/api/handover/delivery-orders/EPLLAO-" + mo["id"], khoa=khoa)
        h = ((g or {}).get("data") or {}).get("header") or {}
        dung(s == 200 and h.get("status") in ("in_transit", "arrived") and h.get("trip_status") == "in_progress"
             and isinstance(h.get("payment_status"), dict),
             "phiếu chưa khoá %s → 200, status %s (không giả delivered), có payment_status" % (mo.get("doc_no"), h.get("status")))
        s, g = goi("/api/handover/delivery-orders?scope=all&page_size=200", khoa=khoa)
        dung(s == 200 and "EPLLAO-" + mo["id"] in {x["do_id"] for x in g["data"]["items"]}, "scope=all có phiếu chưa khoá")
        dung(goi("/api/handover/xem-truoc/" + mo["id"], u="ketoan")[0] == 200, "xem trước phiếu chưa khoá → 200")
    dung(goi("/api/handover/delivery-orders/EPLLAO-khongco", khoa=khoa)[0] == 404, "mã không có → 404")
    dung(goi("/api/handover/delivery-orders/T4-0428-08", khoa=khoa)[0] == 404, "số phiếu thay cho mã DO → 404")
    if items:
        tid = items[0]["do_id"][len("EPLLAO-"):]
        s, g = goi("/api/handover/xem-truoc/" + tid, u="ketoan")
        s0, g0 = goi(items[0]["detail_url"], khoa=khoa)
        dung(s == 200 and g["data"] == g0["data"], "kế toán xem trước = đúng gói bên kia nhận")
        dung(goi("/api/handover/xem-truoc/" + tid, u="thabok")[0] == 403, "Bãi Thà Bốc xem trước → 403 (Bãi không thấy tiền)")
        dung(goi("/api/handover/xem-truoc/" + tid, u="tx01")[0] == 403, "tài xế xem trước → 403")
        print("     mẫu %s: %s" % (items[0]["doc_no"], json.dumps(g0["data"]["details"][:2], ensure_ascii=False)[:400]))

    print("\n%s" % ("ĐẠT hết" if not LOI else "SAI %d chỗ:\n  - " % len(LOI) + "\n  - ".join(LOI)))
    sys.exit(1 if LOI else 0)


if __name__ == "__main__":
    main()

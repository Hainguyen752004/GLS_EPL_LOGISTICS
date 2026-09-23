# -*- coding: utf-8 -*-
"""Thử HAI VAI MỚI ở Thà Bốc (C1.2) và ĐỔI XE GIỮA ĐƯỜNG (C2.2).

    python kiem/thu_vai_va_doi_xe.py [http://127.0.0.1:8010]

Anh Khampla trả lời 22/09:
  · C1.2 — kho phụ tùng và tổ sửa chữa ở Thà Bốc là **người riêng**, không phải Admin Bãi. Nên
    mục V (sửa chữa) rút khỏi Bãi, kho phụ tùng rút khỏi Bãi và kế toán; tổ sửa chữa là người duyệt
    báo hỏng của tài xế và quyết lấy phụ tùng từ kho hay mang ra gara.
  · C2.2 — xe hỏng nặng giữa đường thì **đổi xe khác chở tiếp**, dù mục I đã kiểm xong. Việc này
    làm trên chính tờ phiếu đang chạy: hàng, khách, tuyến và tiền đã chi vẫn là của chuyến đó.

Kịch bản: tài xế báo hỏng → Bãi duyệt bị chặn, tổ sửa chữa duyệt được, dòng chi vào mục V →
Bãi nhập/xuất kho phụ tùng bị chặn, thủ kho phụ tùng làm được → đổi xe giữa đường: chặn vai khác,
chặn thiếu lý do, chặn trùng xe; đổi xong phiếu mang xe mới, có dòng diễn biến, mục I về "đã nhập".
"""
import json
import sys
import urllib.error
import urllib.request

GOC = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010").rstrip("/")
TOKEN = {}
SO_PHIEU = "VAI-DOIXE-01/EPL"


def goi(duong, du_lieu=None, vai=None, method=None):
    dau = {"Content-Type": "application/json"}
    if vai:
        dau["Authorization"] = "Bearer " + TOKEN[vai]
    than = json.dumps(du_lieu).encode() if du_lieu is not None else None
    r = urllib.request.Request(GOC + duong, data=than, headers=dau,
                               method=method or ("POST" if than is not None else "GET"))
    try:
        with urllib.request.urlopen(r, timeout=60) as t:
            return t.status, json.loads(t.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except ValueError:
            return e.code, {}


def phai(s, mong, buoc, g=None):
    dt_ = (g or {}).get("detail") if isinstance(g, dict) else None
    ma = dt_.get("ma", "") if isinstance(dt_, dict) else ""
    print("%s %-60s %s %s" % ("  ✓" if s == mong else "  SAI", buoc, s, ma))
    if s != mong:
        raise SystemExit("DỪNG: %s trả %s, mong %s — %s" % (buoc, s, mong, g))


def don():
    s, ds = goi("/api/trips", vai="admin")
    for p in [x for x in ds if x["doc_no"] == SO_PHIEU]:
        goi("/api/trips/%s/mo-khoa" % p["id"], {}, vai="admin")
        goi("/api/trips/%s" % p["id"], vai="admin", method="DELETE")


def chi_tam_ung(pid, phai):
    """Quy trình: tài xế cầm tiền đi đường (mục IV "đã chi") rồi mới xuất phát / báo xe tới — từ 23/09 máy chặn
    cả hai cửa. Bộ kiểm đi đủ 4 bước như người thật thay vì bấm thẳng "Xe đã tới"."""
    for hd, v in (("send", "thabok"), ("verify", "ketoancp"), ("book", "ketoancp"), ("pay", "quytb")):
        s, g = goi("/api/trips/%s/sections/travel/%s" % (pid, hd), {}, vai=v)
        if s == 409 and isinstance(g, dict) and (g.get("detail") or {}).get("ma") in ("MUC_TRONG", "SAI_BUOC"):
            return          # mục IV trống, hoặc đã đi qua bước này rồi
        phai(s, 200, "mục IV: %s (%s)" % (hd, v), g)


def main():
    for u in ("thabok", "ketoan", "ketoancp", "khonl", "quytb", "totsua", "khopt", "tx01", "admin"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"})
        if s != 200:
            raise SystemExit("Không đăng nhập được %s: %s" % (u, g))
        TOKEN[u] = g["token"]
    print("✓ đăng nhập 9 vai (có thủ kho phụ tùng và tổ sửa chữa)")
    don()

    s, kh = goi("/api/customers", vai="ketoan")
    s, tuyen = goi("/api/routes", vai="ketoan")
    s, xe = goi("/api/vehicles", vai="thabok")
    s, tx = goi("/api/drivers", vai="thabok")
    # Tài xế của phiếu phải đúng người đang đăng nhập bằng tx01, nếu không màn tài xế từ chối.
    s, toi = goi("/api/toi", vai="tx01")
    tx = sorted(tx, key=lambda d: 0 if d["name"] == toi["full_name"] else 1)
    xe_nha = [x for x in xe if x.get("owner_type") != "joint" and x.get("active") is not False]
    if len(xe_nha) < 2:
        raise SystemExit("DỪNG: cần ít nhất hai xe nhà để thử đổi xe — chạy lại seed.py --dung-lai")

    # ---------------------------------------------------------------- 1. lập phiếu, kiểm mục I
    s, P = goi("/api/trips", {
        "doc_no": SO_PHIEU, "kind": "gom", "doc_date": "2026-09-21", "out_date": "2026-09-21",
        "vehicle_id": xe_nha[0]["id"], "driver_id": tx[0]["id"], "customer_id": kh[0]["id"],
        "route_id": tuyen[0]["id"], "goods_type": "iron_ore", "weight_origin": 35,
        "hang": [{"goods_name": "ແຮ່ເຫຼັກ (quặng sắt)", "qty_t": 35}],
        "expenses": [{"section": "fuel", "item_key": "diesel", "qty": 80, "unit_price": 30000, "currency": "LAK", "place": "fp_yard"}],
    }, vai="thabok")
    phai(s, 200, "Bãi lập phiếu %s với xe %s" % (SO_PHIEU, xe_nha[0]["truck_no"]), P)
    pid = P["id"]
    s, g = goi("/api/trips/%s/sections/info/send" % pid, {}, vai="thabok"); phai(s, 200, "Bãi gửi kiểm mục I", g)
    s, g = goi("/api/trips/%s/sections/info/verify" % pid, {}, vai="ketoan"); phai(s, 200, "Kế toán kiểm mục I", g)

    # ---------------------------------------------------------------- 2. C1.2 — mục V là của tổ sửa chữa
    s, g = goi("/api/trips/%s/events" % pid, {"kind": "arrive_stop", "stop_seq": 1, "note": "vào mỏ"}, vai="thabok")
    phai(s, 200, "Bãi vẫn ghi diễn biến bình thường", g)
    s, parts = goi("/api/parts", vai="totsua")
    pt = next(x for x in parts if x["qty"] >= 1); ton = pt["qty"]
    than_sua = {"kind": "repair", "incident_type": "breakdown", "note": "thử: hỏng bơm",
                "repair": {"source": "kho", "part_id": pt["id"], "qty": 1}}
    s, g = goi("/api/trips/%s/events" % pid, than_sua, vai="thabok")
    phai(s, 403, "Bãi khai khoản sửa chữa → bị chặn (C1.2)", g)
    s, g = goi("/api/trips/%s/events" % pid, than_sua, vai="ketoancp")
    phai(s, 403, "Kế toán chi phí khai khoản sửa chữa → bị chặn", g)
    s, g = goi("/api/trips/%s/events" % pid, than_sua, vai="totsua")
    phai(s, 200, "Tổ sửa chữa khai sửa xe, lấy phụ tùng từ kho", g)
    dong = [e for e in g["expenses"] if e["section"] == "repair"]
    assert dong and dong[-1]["source"] == "kho", "phải sinh dòng mục V nguồn kho: %s" % dong
    assert g["sections"]["repair"] == "entered", "mục V phải về 'đã nhập': %s" % g["sections"]["repair"]
    s, parts2 = goi("/api/parts", vai="totsua")
    assert next(x for x in parts2 if x["id"] == pt["id"])["qty"] == ton - 1, "tồn phụ tùng phải giảm 1"
    print("  ✓ %-60s %s → %s" % ("Tồn phụ tùng giảm đúng 1", ton, ton - 1))

    s, g = goi("/api/parts/%s/moves" % pt["id"], {"kind": "in", "qty": 1, "note": "thử trả kho"}, vai="thabok")
    phai(s, 403, "Bãi nhập kho phụ tùng → bị chặn (C1.2)", g)
    s, g = goi("/api/parts/%s/moves" % pt["id"], {"kind": "in", "qty": 1, "note": "thử trả kho"}, vai="ketoan")
    phai(s, 403, "Kế toán nhập kho phụ tùng → bị chặn", g)
    s, g = goi("/api/parts/%s/moves" % pt["id"], {"kind": "in", "qty": 1, "note": "thử trả kho"}, vai="khopt")
    phai(s, 200, "Thủ kho phụ tùng nhập kho được", g)

    # tài xế báo hỏng → tổ sửa chữa duyệt
    s, g = goi("/api/trips/%s/bao-hong" % pid, {"note": "thử: kêu lạ ở cầu sau", "reported_cost": 250000}, vai="tx01")
    phai(s, 200, "Tài xế báo hỏng", g)
    ev = [e for e in g["events"] if e["status"] == "reported"][-1]
    s, g = goi("/api/trips/%s/events/%s/duyet" % (pid, ev["id"]),
               {"source": "mua", "item_name": "thử: thay bạc đạn", "qty": 1, "unit_price": 250000}, vai="thabok")
    phai(s, 403, "Bãi duyệt báo hỏng → bị chặn (việc tổ sửa chữa)", g)
    s, g = goi("/api/trips/%s/events/%s/duyet" % (pid, ev["id"]),
               {"source": "mua", "item_name": "thử: thay bạc đạn", "qty": 1, "unit_price": 250000}, vai="totsua")
    phai(s, 200, "Tổ sửa chữa duyệt báo hỏng → thành dòng mục V", g)
    assert len([e for e in g["expenses"] if e["section"] == "repair"]) == 2, "phải có hai dòng mục V"

    s, g = goi("/api/trips/%s/sections/repair/send" % pid, {}, vai="thabok")
    phai(s, 403, "Bãi gửi kiểm mục V → bị chặn", g)
    s, g = goi("/api/trips/%s/sections/repair/verify" % pid, {}, vai="ketoancp")
    phai(s, 200, "KT Chi phí kiểm mục V (tổ sửa chữa không tự kiểm)", g)
    s, g = goi("/api/trips/%s/sections/repair/verify" % pid, {}, vai="totsua")
    phai(s, 403, "Tổ sửa chữa tự kiểm mục V → bị chặn (KT Chi phí kiểm)", g)

    # TIỀN BÁN: hai vai mới xếp cùng nhóm Bãi — không xem lãi chuyến, không xem công nợ chủ xe.
    s, ds_chu = goi("/api/owners", vai="totsua")
    assert all("fee_pct" not in o for o in ds_chu), "tổ sửa chữa không được thấy phí chủ xe: %s" % ds_chu[:1]
    s, g = goi("/api/bao-cao/xe-lien-ket", vai="khopt")
    phai(s, 403, "Thủ kho phụ tùng xem báo cáo xe liên kết (lãi) → bị chặn", g)
    s, g = goi("/api/hoa-don-gop", vai="totsua")
    phai(s, 403, "Tổ sửa chữa xem hoá đơn → bị chặn (tiền bán)", g)

    # ---------------------------------------------------------------- 3. C2.2 — đổi xe giữa đường
    s, g = goi("/api/trips/%s/doi-xe" % pid, {"vehicle_id": xe_nha[1]["id"], "ly_do": "thử"}, vai="ketoan")
    phai(s, 403, "Kế toán đổi xe → bị chặn (Bãi điều xe)", g)
    s, g = goi("/api/trips/%s/doi-xe" % pid, {"vehicle_id": xe_nha[1]["id"]}, vai="thabok")
    phai(s, 422, "Đổi xe không ghi lý do → bị từ chối", g)
    s, g = goi("/api/trips/%s/doi-xe" % pid, {"vehicle_id": xe_nha[0]["id"], "ly_do": "thử"}, vai="thabok")
    phai(s, 409, "Đổi sang chính xe đang chạy → bị từ chối", g)
    xe_lk = next((x for x in xe if x.get("owner_type") == "joint" and x.get("active") is not False), None)
    if xe_lk:
        s, g = goi("/api/trips/%s/doi-xe" % pid, {"vehicle_id": xe_lk["id"], "ly_do": "thử chéo"}, vai="thabok")
        phai(s, 409, "Đổi chéo xe nhà → xe liên kết → bị từ chối (chứng từ mang mã loại cũ)", g)

    s, g = goi("/api/trips/%s/doi-xe" % pid,
               {"vehicle_id": xe_nha[1]["id"], "driver_id": tx[1]["id"], "ly_do": "thử: gãy nhíp giữa đường",
                "xe_cu_hong": True}, vai="thabok")
    phai(s, 200, "Bãi đổi sang xe %s giữa đường" % xe_nha[1]["truck_no"], g)
    assert g["truck_no"] == xe_nha[1]["truck_no"] and g["plate_head"] == xe_nha[1]["plate_head"], \
        "phiếu phải mang xe mới: %s" % g["truck_no"]
    assert g["driver_name"] == tx[1]["name"], "phiếu phải mang tài xế mới: %s" % g["driver_name"]
    assert g["sections"]["info"] == "entered", "mục I phải quay về 'đã nhập' để kiểm lại: %s" % g["sections"]["info"]
    dx = [e for e in g["events"] if e["kind"] == "change_truck"]
    assert dx and xe_nha[0]["truck_no"] in dx[-1]["note"] and xe_nha[1]["truck_no"] in dx[-1]["note"], \
        "diễn biến phải ghi rõ đổi từ xe nào sang xe nào: %s" % dx
    print("  ✓ %-60s %s" % ("Diễn biến giữ lại xe cũ", dx[-1]["note"][:52]))
    assert len(g["expenses"]) >= 3, "dòng chi của chuyến phải còn nguyên sau khi đổi xe"
    print("  ✓ %-60s %d dòng" % ("Tiền đã chi của chuyến còn nguyên trên phiếu", len(g["expenses"])))

    s, xe2 = goi("/api/vehicles", vai="thabok")
    cu = next(x for x in xe2 if x["id"] == xe_nha[0]["id"]); moi = next(x for x in xe2 if x["id"] == xe_nha[1]["id"])
    assert cu["status"] == "maintenance", "xe cũ phải vào xưởng: %s" % cu["status"]
    assert moi["status"] == "on_trip", "xe mới phải là đang chạy: %s" % moi["status"]
    print("  ✓ %-60s %s · %s" % ("Trạng thái hai xe đổi theo", cu["status"], moi["status"]))

    s, g = goi("/api/trips/%s/sections/info/verify" % pid, {}, vai="ketoan")
    phai(s, 200, "Kế toán kiểm lại mục I sau khi đổi xe", g)

    chi_tam_ung(pid, phai)
    s, g = goi("/api/trips/%s/transport-status" % pid, {"status": "arrived", "weight_dest": 35, "odo_back": 100}, vai="thabok")
    phai(s, 200, "Xe (mới) báo tới nơi", g)
    s, g = goi("/api/trips/%s/doi-xe" % pid, {"vehicle_id": xe_nha[0]["id"], "ly_do": "thử"}, vai="thabok")
    phai(s, 409, "Đổi xe khi đã tới nơi → bị từ chối", g)

    # ---------------------------------------------------------------- 4. dọn
    s, g = goi("/api/parts/%s/moves" % pt["id"], {"kind": "in", "qty": 1, "note": "hoàn trả sau bộ kiểm"}, vai="khopt")
    phai(s, 200, "Trả lại phụ tùng đã xuất (dọn)", g)
    s, g = goi("/api/trips/%s" % pid, vai="admin", method="DELETE"); phai(s, 200, "Xoá phiếu thử (dọn)", g)
    for x, tt in ((xe_nha[0]["id"], "available"), (xe_nha[1]["id"], "available")):
        goi("/api/vehicles/%s" % x, {"status": tt}, vai="thabok", method="PUT")
    print("\n✅ HAI VAI MỚI & ĐỔI XE: mục V và kho phụ tùng đã rút khỏi Bãi, tổ sửa chữa duyệt báo hỏng,")
    print("   đổi xe giữa đường giữ nguyên chuyến và bắt kiểm lại mục I.")


if __name__ == "__main__":
    main()

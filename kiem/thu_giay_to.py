# -*- coding: utf-8 -*-
"""Thử CỬA CHẶN GIẤY TỜ khi xếp xe vào phiếu (20/10 — anh Hải chọn bổ sung theo EPL_System «điều phối chặn tài xế không đủ bằng lái»).

    python kiem/thu_giay_to.py [http://127.0.0.1:8011]

Phải thấy (luật: backend/app/services/giay_to.py):
  · GET /api/kiem-giay-to: tài xế hết hạn bằng → «chan»; tài xế còn hạn → không chặn;
  · Bãi lập phiếu với tài xế hết hạn bằng → 422 GIAY_TO_CHUA_DU; gửi kèm «bo_qua_giay_to» cũng vẫn bị chặn (chỉ Sếp cho qua);
  · Sếp lập phiếu đó kèm lý do → lưu được, nhật ký phiếu có dòng «gt_bo_qua:<lý do>»; Sếp không ghi lý do → vẫn chặn;
  · phiếu đã lưu: sửa mục khác (không đổi tài xế) → không vướng; đổi sang tài xế hết hạn → chặn;
  · xe hết hạn đăng kiểm (đặt tạm trên bản sao) → chặn; trả lại hạn cũ cuối bài.
Bài tự lập phiếu thử và tự xoá; hạn đăng kiểm xe thử trả về như cũ.
"""
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request

GOC = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"
TK = {}
SAI = []


def goi(duong, body=None, vai=None, method=None):
    du = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(GOC + duong, data=du, method=method or ("POST" if du is not None else "GET"),
                               headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + TK[vai]} if vai else {})})
    try:
        with urllib.request.urlopen(r, timeout=120) as t:
            return t.status, json.loads(t.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except ValueError:
            return e.code, {}


def ma(g):
    return (g or {}).get("detail", {}).get("ma") if isinstance((g or {}).get("detail"), dict) else None


def dung(dk, buoc, them=""):
    print("  %s %s %s" % ("✓" if dk else "SAI", buoc, "" if dk else them))
    if not dk:
        SAI.append(buoc)


def main():
    mk = os.environ.get("PW_8011") or "1234"                # máy thử: mật khẩu chung của bản demo
    for v in ("thabok", "admin", "ketoan"):
        s, d = goi("/api/dang-nhap", {"username": v, "password": mk})
        assert s == 200, (v, s, d)
        TK[v] = d["token"]
    hom_nay = dt.date.today().isoformat()
    s, tx = goi("/api/drivers", vai="admin")
    s, xe = goi("/api/vehicles", vai="admin")
    s, kh = goi("/api/customers", vai="admin")
    het = next((d for d in tx if d.get("active", True) and d.get("license_no") and d.get("license_valid_to")
                and d["license_valid_to"] < hom_nay and (d.get("license_status") or "active") == "active"), None)
    tot = next((d for d in tx if d.get("active", True) and d.get("license_no") and (d.get("license_valid_to") or "9999") > hom_nay
                and (d.get("license_status") or "active") == "active"
                and not (d.get("license_class_hr") and d.get("license_type") and d["license_class_hr"] != d["license_type"])), None)
    xe_tot = next((x for x in xe if x["owner_type"] == "EPL" and x.get("active", True)
                   and all((x.get(k) or "9999") > hom_nay for k in ("inspection_exp", "insurance_exp", "road_permit_exp"))), None)
    assert het and tot and xe_tot, "bản sao thiếu tài xế hết hạn / tài xế còn hạn / xe còn hạn để thử"
    print("Tài xế hết hạn: %s (%s) · tài xế còn hạn: %s · xe: %s" % (het["name"], het["license_valid_to"], tot["name"], xe_tot["truck_no"]))

    s, k = goi("/api/kiem-giay-to?driver_id=%s&ngay=%s" % (het["id"], hom_nay), vai="thabok")
    dung(s == 200 and any(m["ly_do"] == "het_han" and m["doi_tuong"] == "tai_xe" for m in k["chan"]), "Xem trước: tài xế hết hạn bằng → chặn", k)
    s, k = goi("/api/kiem-giay-to?driver_id=%s&vehicle_id=%s&ngay=%s" % (tot["id"], xe_tot["id"], hom_nay), vai="thabok")
    dung(s == 200 and not k["chan"], "Xem trước: tài xế + xe còn hạn → không chặn", k)

    than = {"doc_no": "THU-GT-%s/EPL" % time.strftime("%H%M%S"), "kind": "giao", "vehicle_id": xe_tot["id"], "driver_id": het["id"],
            "customer_id": kh[0]["id"], "doc_date": hom_nay, "expenses": []}
    s, g = goi("/api/trips", than, "thabok")
    dung(s == 422 and ma(g) == "GIAY_TO_CHUA_DU", "Bãi lập phiếu với tài xế hết hạn bằng → chặn", (s, g))
    s, g = goi("/api/trips", dict(than, bo_qua_giay_to="Bãi xin cho qua"), "thabok")
    dung(s == 422 and ma(g) == "GIAY_TO_CHUA_DU", "Bãi gửi kèm lý do vẫn bị chặn (chỉ Sếp cho qua)", (s, g))
    s, g = goi("/api/trips", dict(than, bo_qua_giay_to="   "), "admin")
    dung(s == 422 and ma(g) == "GIAY_TO_CHUA_DU", "Sếp không ghi lý do → vẫn chặn", (s, g))
    pid = None
    xe_cu = None
    try:
        s, p = goi("/api/trips", dict(than, bo_qua_giay_to="Tài xế đang chờ cấp bằng mới — chạy chuyến gần (thử)"), "admin")
        dung(s == 200, "Sếp lập phiếu kèm lý do → lưu được", (s, p))
        pid = p.get("id")
        s, pk = goi("/api/trips/%s" % pid, vai="admin")
        dung(any(str(l.get("action", "")).startswith("gt_bo_qua:") for l in pk.get("logs", [])), "Nhật ký phiếu có dòng Sếp cho qua kèm lý do",
             pk.get("logs"))
        s, g = goi("/api/trips/%s" % pid, {"note": "sửa ghi chú thử"}, "admin", "PUT")
        dung(s == 200, "Sửa mục khác (không đổi tài xế) → không vướng giấy tờ", (s, g))
        s, g = goi("/api/trips/%s" % pid, {"driver_id": tot["id"]}, "thabok", "PUT")
        dung(s == 200, "Bãi đổi sang tài xế còn hạn → lưu được", (s, g))
        s, g = goi("/api/trips/%s" % pid, {"driver_id": het["id"]}, "thabok", "PUT")
        dung(s == 422 and ma(g) == "GIAY_TO_CHUA_DU", "Bãi đổi lại sang tài xế hết hạn → chặn", (s, g))
        # xe hết hạn đăng kiểm (đặt tạm trên bản sao)
        xe_cu = xe_tot.get("inspection_exp")
        s, g = goi("/api/vehicles/%s" % xe_tot["id"], {"inspection_exp": (dt.date.today() - dt.timedelta(days=3)).isoformat()}, "admin", "PUT")
        s, k = goi("/api/kiem-giay-to?vehicle_id=%s&ngay=%s" % (xe_tot["id"], hom_nay), vai="thabok")
        dung(any(m["giay"] == "dang_kiem" and m["doi_tuong"] == "dau_keo" for m in k["chan"]), "Xe hết hạn đăng kiểm → chặn", k)
        s, g = goi("/api/trips", dict(than, doc_no=than["doc_no"] + "B", driver_id=tot["id"]), "thabok")
        dung(s == 422 and ma(g) == "GIAY_TO_CHUA_DU", "Bãi lập phiếu với xe hết hạn đăng kiểm → chặn", (s, g))
    finally:
        if xe_cu is not None or "xe_tot" in dir():
            s, _ = goi("/api/vehicles/%s" % xe_tot["id"], {"inspection_exp": xe_cu}, "admin", "PUT")
            print("  · trả hạn đăng kiểm xe %s về như cũ: %s" % (xe_tot["truck_no"], s))
        if pid:
            s, _ = goi("/api/trips/%s" % pid, vai="admin", method="DELETE"); print("  · phiếu thử %s" % ("đã xoá" if s == 200 else "ở lại (%s)" % s))
    print("\nTHỬ GIẤY TỜ: %s" % ("ĐẠT" if not SAI else "SAI %d bước: %s" % (len(SAI), "; ".join(SAI))))
    sys.exit(1 if SAI else 0)


if __name__ == "__main__":
    main()

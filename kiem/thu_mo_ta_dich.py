# -*- coding: utf-8 -*-
"""Thử 10/10: CHỮ MÁY TỰ SINH lưu trong dữ liệu có bản Lào / Anh lúc hiện (anh Hải: chọn tiếng Lào vẫn thấy "Tài xế báo đã về · km …",
"Lĩnh … lít tại …", "Phiếu xuất xe …", "Đề nghị thu cước phiếu …") — services/mo_ta_dich.json + loi_dich.dich_mo_ta / gan_ban_dich.

    python kiem/thu_mo_ta_dich.py

A. Danh mục: mọi mẫu có đủ lo / en, chỗ chèn khớp, bản dịch không còn chữ Việt; câu mẫu dựng ĐÚNG như mã máy chủ ghép (chép chuỗi định
   dạng từ mã) → dịch được; mỗi chuỗi định dạng mo_ta= / note= máy tự ghi trong mã đều có mẫu (thêm câu mới mà quên mẫu → SAI).
B. Ghi chú người dùng tự gõ / câu lỗi không bị dịch theo mẫu này.
C. API (TestClient, _d7, ROLLBACK): tài xế báo về → sự kiện mang note tiếng Việt như cũ trong DB, API kèm note_lo / note_en; sổ chứng
   từ của phiếu: mô tả DO kèm mo_ta_lo / mo_ta_en; ghi chú tự gõ → không có bản dịch.
"""
import json
import os
import re
import sys

import _khung_tien_trinh as K                           # đặt DATABASE_URL = _d7, chặn mạng — trước mọi mã máy chủ

dung, phai = K.dung, K.phai
GOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
VIET = re.compile(r"[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỷỹỵ]", re.I)


def phan_a():
    print("== A. danh mục mẫu")
    from services import loi_dich as LD
    dm = json.load(open(os.path.join(GOC, "backend", "app", "services", "mo_ta_dich.json"), encoding="utf-8"))
    hong = []
    for vi, d in dm.items():
        cho = sorted(re.findall(r"\{\d+\}", vi))
        for lang in ("lo", "en"):
            t = d.get(lang) or ""
            if not t or sorted(re.findall(r"\{\d+\}", t)) != cho or VIET.search(re.sub(r"\{\d+\}", "", t)):
                hong.append((vi, lang, t))
    dung(not hong, "%d mẫu: đủ Lào / Anh, chỗ chèn khớp, không còn chữ Việt" % len(dm), hong[:3])
    # câu mẫu ghép đúng như mã (chuỗi định dạng chép từ routes / services)
    mau = [
        "Tài xế báo đã về · km %s" % 9824,
        "Báo cân tại mỏ %s t%s%s%s" % ("40.5", "", "", ""),
        "Báo cân tại mỏ %s t%s%s%s" % ("40.5", " (trước %s t)" % "41", " · %d ảnh" % 2, " · " + "cân lại"),
        "Báo cân tại mỏ %s t%s%s%s" % ("40.5", "", " · %d ảnh" % 1, ""),
        "Đổi xe %s%s → %s%s · %s%s" % ("341", " (ບອ 3262)", "342", " (ບອ 3311)", "hỏng máy", ""),
        "Đổi xe %s%s → %s%s · %s%s" % ("341", "", "342", "", "hỏng máy", " · đổi tài xế sang %s" % "ທ້າວ ບຸນມີ"),
        "Phiếu xuất xe %s · %s → %s" % ("T4-0001-10/EPL", "ກາສີ", "ທ່າບົກ"),
        "Đề nghị thu cước phiếu %s · %s → %s" % ("T4-0001-10/EPL", "ກາສີ", "ທ່າບົກ"),
        "Lĩnh %s lít tại %s" % (100.0, "Kho dầu Thà Bốc"),
        "Cấp %s lít dầu theo %s" % (100.0, "PL-0001"),
        "Đề nghị tạm ứng phiếu %s" % "T4-0001-10/EPL",
        "Chi theo đề nghị tạm ứng %s" % "TU-0001",
        "Chi mục IV đi đường phiếu %s" % "T4-0001-10/EPL",
        "Chi mục %s phiếu %s" % ({"repair": "V sửa chữa", "other": "VI khác"}["repair"], "T4-0001-10/EPL"),
        "Chi mục %s phiếu %s" % ({"repair": "V sửa chữa", "other": "VI khác"}["other"], "T4-0001-10/EPL"),
        "Xuất %s %s sửa xe %s" % (2, "ຢາງລົດ", "341"),
        "Nhập kho hàng từ %s · %s tấn" % ("G4-0001-10/EPL", 42.3),
        "Xuất kho hàng đi giao %s · %s tấn" % ("T4-0001-10/EPL", 30.0),
        "Điều chỉnh kho lô %s: %s%s tấn — %s" % ("G4-0001-10/EPL", "+", 0.5, "cân lại"),
    ]
    sai = [(c, LD.dich_mo_ta(c, "lo"), LD.dich_mo_ta(c, "en")) for c in mau if not (LD.dich_mo_ta(c, "lo") and LD.dich_mo_ta(c, "en"))]
    dung(not sai, "%d câu ghép đúng như mã máy chủ → đều có bản Lào và Anh" % len(mau), sai[:3])
    vd = LD.dich_mo_ta("Lĩnh 100.0 lít tại Kho dầu Thà Bốc", "lo")
    dung(vd == "ເບີກນໍ້າມັນ 100.0 ລິດ ທີ່ Kho dầu Thà Bốc", "giá trị chèn (tên kho trong dữ liệu) giữ nguyên chữ", vd)
    vd = LD.dich_mo_ta("Báo cân tại mỏ 40.5 t (trước 41 t) · 2 ảnh · cân lại", "en")
    dung(vd == "Mine weight reported: 40.5 t (was 41 t) · 2 photo(s) · cân lại", "mẫu cụ thể nhất thắng; ghi chú tự gõ giữ nguyên", vd)
    # mỗi chuỗi định dạng mo_ta= / note= máy tự ghi (chứng từ, sự kiện) trong mã đều có mẫu
    nguon = {"routes/phieu.py": [r'mo_ta="(Phiếu xuất xe[^"]*)"', r'note="(Tài xế báo đã về[^"]*)"', r'mo_ta="(Chi mục IV[^"]*)"',
                                 r'mo_ta="(Xuất %s %s sửa xe[^"]*)"'],
             "routes/phieu_linh.py": [r'mo_ta="(Lĩnh[^"]*)"', r'mo_ta="(Cấp %s lít[^"]*)"', r'mo_ta="(Đề nghị tạm ứng[^"]*)"',
                                      r'mo_ta="(Chi theo đề nghị[^"]*)"'],
             "services/de_nghi_thu.py": [r'mo_ta = "(Đề nghị thu cước[^"]*)"'],
             "services/kho_hang_dia.py": [r'mo_ta="(Nhập kho hàng từ[^"]*)"', r'mo_ta = "(Xuất kho hàng đi giao[^"]*)"']}
    thieu = []
    for tep, ds in nguon.items():
        van = open(os.path.join(GOC, "backend", "app", tep), encoding="utf-8").read()
        for rx in ds:
            for m in re.findall(rx, van):
                i = iter(range(1, 20))
                mau_ = re.sub(r"%[sd]", lambda _: "{%d}" % next(i), m)
                if mau_ not in dm:
                    thieu.append((tep, m))
    dung(not thieu, "chuỗi định dạng máy tự ghi trong mã đều có mẫu dịch", thieu)


def phan_b():
    print("== B. không dịch nhầm")
    from services import loi_dich as LD
    for c in ("xe bị hỏng lốp ở km 120", "Phiếu đã khoá.", "Đã nhận", "Tài xế báo hỏng xe", "Lĩnh dầu"):
        dung(LD.dich_mo_ta(c, "lo") is None, "«%s» không khớp mẫu → không có bản dịch (màn hiện nguyên chữ)" % c)
    dung(LD.dich("Không có chủ xe này.", "lo") == "ບໍ່ມີເຈົ້າຂອງລົດຄົນນີ້.", "dịch câu lỗi (danh mục cũ) vẫn chạy như trước")


def phan_c():
    print("== C. API")
    with K.Khung() as m:
        goi, M = m.goi, m.M
        tx = m.tai_xe("ທ້າວ ທົດລອງ ມໍຕາ", tai_khoan=True)
        kh = m.khach("ລູກຄ້າ ທົດລອງ ມໍຕາ")
        xe = m.xe("THU-MT-01")
        m.commit()
        ngay = m.ngay(10).isoformat()
        s, p = goi("/api/trips", {"doc_no": "THU-MT-A/EPL", "kind": "giao", "vehicle_id": xe.id, "driver_id": tx.id, "customer_id": kh.id,
                                  "doc_date": ngay, "out_date": ngay, "weight_origin": 40, "odo_out": 100, "price": 40, "price_ccy": "USD"},
                   vai="admin")
        phai(s, 200, "Sếp lập phiếu thử", p)
        s, g = goi("/api/trips/%s/events" % p["id"], {"kind": "note", "note": "xe chờ cân ở cổng"}, vai="admin")
        phai(s, 200, "ghi chú tự gõ", g)
        T = m.db.get(M.Trip, p["id"])
        m.db.add(M.TripEvent(trip_id=T.id, kind="arrive_stop", by_user="thu", note="Tài xế báo đã về · km %s" % 9824))
        m.commit()
        s, P = goi("/api/trips/" + p["id"], vai="admin")
        ev = {e["note"]: e for e in P.get("events") or []}
        e1, e2 = ev.get("Tài xế báo đã về · km 9824"), ev.get("xe chờ cân ở cổng")
        dung(e1 and e1.get("note_lo") == "ໂຊເຟີແຈ້ງວ່າກັບຮອດແລ້ວ · km 9824" and e1.get("note_en") == "Driver reported back · km 9824",
             "sự kiện máy tự ghi: note giữ tiếng Việt, kèm note_lo / note_en", e1)
        dung(e2 and "note_lo" not in e2 and "note_en" not in e2, "ghi chú tự gõ: không có bản dịch", e2)
        luu = m.db.query(M.TripEvent.note).filter(M.TripEvent.trip_id == T.id, M.TripEvent.kind == "arrive_stop").scalar()
        dung(luu == "Tài xế báo đã về · km 9824", "câu lưu trong DB không đổi", luu)
        s, ct = goi("/api/chung-tu?trip_id=" + p["id"], vai="admin")
        do = next((c for c in (ct or {}).get("ds") or [] if c.get("loai") == "DO"), None)
        dung(do and do["mo_ta"].startswith("Phiếu xuất xe THU-MT-A/EPL") and do.get("mo_ta_lo", "").startswith("ໃບເບີກລົດ THU-MT-A/EPL")
             and do.get("mo_ta_en", "").startswith("Dispatch slip THU-MT-A/EPL"), "sổ chứng từ: mô tả DO kèm mo_ta_lo / mo_ta_en",
             do and (do["mo_ta"], do.get("mo_ta_lo"), do.get("mo_ta_en")))


if __name__ == "__main__":
    try:
        phan_a(); phan_b(); phan_c()
    except RuntimeError as e:
        print(e)
    K.ket_thuc("THỬ CHỮ MÁY TỰ SINH CÓ BẢN DỊCH")

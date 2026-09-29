# -*- coding: utf-8 -*-
"""THÊM XE · RƠ-MOÓC · TÀI XẾ MẪU cho bản demo (29/09) — đi qua API của trang điều xe, đúng như người dùng bấm ở màn Xe,
Tài xế: máy chủ kiểm từng ô như lúc nhập tay, không ghi thẳng DB.

    python tools/them_xe_tai_xe.py [địa chỉ=http://127.0.0.1:8020]          chạy thử: kể ra sẽ thêm gì, KHÔNG ghi
    python tools/them_xe_tai_xe.py [địa chỉ] that                           thêm thật

Thêm (cái nào đã có — cùng số xe, cùng biển rơ-moóc, cùng mã tài xế — thì bỏ qua, chạy lại bao nhiêu lần cũng không trùng):
  · 12 đầu kéo xe nhà 343–354 (HOWO, SHACMAN, SITRAK, FAW), biển đầu kéo ບອ · ນວ · ກຂ, giấy tờ, công-tơ-mét;
  · 2 xe liên kết ຮ່ວມ-08, ຮ່ວມ-09 của chủ xe đã có trong danh mục;
  · 18 rơ-moóc — lắp vào 14 đầu kéo mới, 4 cái để rời (1 đang sửa) để thử "hư cái này thì lấy cái kia lắp vào";
  · 14 tài xế DRV-03 … DRV-14 (xe nhà) và DRV-LK-02, DRV-LK-03 (xe liên kết), có bằng lái, xe thường lái.
Vài giấy tờ, bằng lái cố ý sắp hết hạn / đã hết hạn để thử cờ cảnh báo trên màn Xe, Tài xế.
Không tạo tài khoản đăng nhập cho tài xế mới (tài khoản làm ở Hệ thống → Tài khoản).
"""
import json
import sys
import urllib.error
import urllib.request

GOC = next((a for a in sys.argv[1:] if a.startswith("http")), "http://127.0.0.1:8020").rstrip("/")
THAT = "that" in sys.argv[1:]

# ---------------------------------------------------------------- dữ liệu
# đầu kéo: số xe, hãng, năm, biển đầu kéo, tải (t), định mức L/100km, dung tích máy, hạn bảo hiểm, hạn đăng kiểm, km
DAU_KEO = [
    ("343", "HOWO-430", 2020, "ບອ 3345", 42, 40, "9,7 L / 430 HP", "2027-04-01", "2027-01-20", 61200),
    ("344", "HOWO-430", 2020, "ບອ 3346", 42, 40, "9,7 L / 430 HP", "2027-04-01", "2026-10-12", 58800),   # đăng kiểm sắp hết
    ("345", "HOWO-371", 2018, "ບອ 3171", 40, 38, "9,7 L / 371 HP", "2026-11-30", "2027-02-28", 132500),
    ("346", "HOWO-371", 2018, "ບອ 3172", 40, 38, "9,7 L / 371 HP", "2026-09-20", "2027-02-28", 128900),   # bảo hiểm đã hết
    ("347", "SHACMAN X3000", 2021, "ນວ 5501", 45, 42, "11,6 L / 460 HP", "2027-06-15", "2027-05-10", 44300),
    ("348", "SHACMAN X3000", 2021, "ນວ 5502", 45, 42, "11,6 L / 460 HP", "2027-06-15", "2027-05-10", 41900),
    ("349", "SITRAK C7H", 2022, "ນວ 5613", 45, 41, "12,4 L / 480 HP", "2027-08-01", "2027-07-01", 26700),
    ("350", "SITRAK C7H", 2022, "ນວ 5614", 45, 41, "12,4 L / 480 HP", "2027-08-01", "2027-07-01", 24100),
    ("351", "FAW J6P", 2019, "ກຂ 7702", 42, 39, "11 L / 420 HP", "2027-01-10", "2026-12-05", 97800),
    ("352", "FAW J6P", 2019, "ກຂ 7703", 42, 39, "11 L / 420 HP", "2027-01-10", "2026-12-05", 95400),
    ("353", "HOWO-430", 2023, "ບອ 3490", 42, 40, "9,7 L / 430 HP", "2028-02-01", "2027-11-15", 12800),
    ("354", "HOWO-430", 2023, "ບອ 3491", 42, 40, "9,7 L / 430 HP", "2028-02-01", "2027-11-15", 11500),
]
LIEN_KET = [   # xe liên kết của chủ xe đã có trong danh mục
    ("ຮ່ວມ-08", "SHACMAN", 2018, "ກຂ 8820", 40, 40, "10 L / 380 HP", 102300),
    ("ຮ່ວມ-09", "HOWO-371", 2017, "ກຂ 8831", 40, 38, "9,7 L / 371 HP", 141600),
]
THUNG_BEN = "ຕ້ວນຖັງ (thùng ben)"
# rơ-moóc: biển, loại, tải, năm, hạn bảo hiểm, hạn đăng kiểm, trạng thái — 14 cái đầu lắp theo thứ tự xe ở trên
RO_MOOC = [
    ("ບອ 3347", THUNG_BEN, 42, 2020, "2027-04-01", "2027-01-20", "available"),
    ("ບອ 3348", THUNG_BEN, 42, 2020, "2027-04-01", "2027-01-20", "available"),
    ("ບອ 3173", THUNG_BEN, 40, 2018, "2026-11-30", "2027-02-28", "available"),
    ("ບອ 3174", THUNG_BEN, 40, 2018, "2026-11-30", "2027-02-28", "available"),
    ("ນວ 5503", THUNG_BEN, 45, 2021, "2027-06-15", "2027-05-10", "available"),
    ("ນວ 5504", THUNG_BEN, 45, 2021, "2027-06-15", "2027-05-10", "available"),
    ("ນວ 5615", "container 40'", 40, 2022, "2027-08-01", "2027-07-01", "available"),
    ("ນວ 5616", "container 40'", 40, 2022, "2027-08-01", "2027-07-01", "available"),
    ("ກຂ 7704", THUNG_BEN, 42, 2019, "2027-01-10", "2026-12-05", "available"),
    ("ກຂ 7705", THUNG_BEN, 42, 2019, "2027-01-10", "2026-10-08", "available"),        # đăng kiểm sắp hết
    ("ບອ 3492", THUNG_BEN, 42, 2023, "2028-02-01", "2027-11-15", "available"),
    ("ບອ 3493", THUNG_BEN, 42, 2023, "2028-02-01", "2027-11-15", "available"),
    ("ກຂ 8821", THUNG_BEN, 40, 2018, "2027-03-01", "2027-01-01", "available"),        # lắp xe liên kết ຮ່ວມ-08
    ("ກຂ 8832", THUNG_BEN, 40, 2017, "2027-03-01", "2027-01-01", "available"),        # lắp xe liên kết ຮ່ວມ-09
    ("ບອ 3501", THUNG_BEN, 42, 2021, "2027-05-01", "2027-04-01", "available"),        # để rời — lắp thay khi cái khác hư
    ("ບອ 3502", THUNG_BEN, 42, 2021, "2027-05-01", "2027-04-01", "available"),        # để rời
    ("ນວ 5620", "container 40'", 40, 2020, "2027-02-01", "2026-12-20", "available"),  # để rời
    ("ບອ 3503", THUNG_BEN, 40, 2016, "2026-12-01", "2026-11-01", "maintenance"),      # đang sửa — không lắp được
]
# tài xế: mã, tên, tên Latin, điện thoại, ngày sinh, ngày vào làm, số bằng, hạng, bằng từ, bằng tới, xe thường lái
TAI_XE = [
    ("DRV-03", "ທ້າວ ສົມສັກ", "Somsak", "020 5510 3303", "1985-02-14", "2019-03-01", "LA-2410533", "C", "2021-03-01", "2029-03-01", "343"),
    ("DRV-04", "ທ້າວ ບຸນເຫຼືອ", "Bounleua", "020 5510 3304", "1987-07-22", "2019-06-15", "LA-2410544", "C", "2021-06-15", "2029-06-15", "344"),
    ("DRV-05", "ທ້າວ ພອນສະຫວັນ", "Phonsavanh", "020 5510 3305", "1990-11-03", "2020-01-10", "LA-2410555", "C", "2022-01-10", "2030-01-10", "345"),
    ("DRV-06", "ທ້າວ ຄຳແພງ", "Khamphaeng", "020 5510 3306", "1983-05-30", "2018-09-01", "LA-2410566", "C", "2020-09-01", "2026-10-20", "346"),   # bằng sắp hết
    ("DRV-07", "ທ້າວ ສີສຸພັນ", "Sisouphan", "020 5510 3307", "1992-01-18", "2021-02-01", "LA-2410577", "C", "2023-02-01", "2031-02-01", "347"),
    ("DRV-08", "ທ້າວ ວິໄລ", "Vilay", "020 5510 3308", "1989-08-09", "2020-05-20", "LA-2410588", "C", "2022-05-20", "2030-05-20", "348"),
    ("DRV-09", "ທ້າວ ບົວພັນ", "Bouaphanh", "020 5510 3309", "1986-12-25", "2019-11-11", "LA-2410599", "C", "2021-11-11", "2026-09-15", "349"),  # bằng đã hết
    ("DRV-10", "ທ້າວ ແສງທອງ", "Saengthong", "020 5510 3310", "1994-04-04", "2022-03-01", "LA-2410600", "C", "2024-03-01", "2032-03-01", "350"),
    ("DRV-11", "ທ້າວ ອຸດົມ", "Oudom", "020 5510 3311", "1988-06-16", "2020-08-08", "LA-2410611", "C", "2022-08-08", "2030-08-08", "351"),
    ("DRV-12", "ທ້າວ ສຸລິຍາ", "Souliya", "020 5510 3312", "1991-09-29", "2021-07-01", "LA-2410622", "C", "2023-07-01", "2031-07-01", "352"),
    ("DRV-13", "ທ້າວ ທອງໃສ", "Thongsay", "020 5510 3313", "1984-03-12", "2018-04-01", "LA-2410633", "C", "2020-04-01", "2028-04-01", "353"),
    ("DRV-14", "ທ້າວ ວັນໄຊ", "Vanxay", "020 5510 3314", "1993-10-07", "2023-01-15", "LA-2410644", "C", "2025-01-15", "2033-01-15", "354"),
    ("DRV-LK-02", "ທ້າວ ຄຳສີ", "Khamsy", "020 5520 4402", "1982-02-02", "2020-02-01", "LA-1907731", "C", "2020-02-01", "2028-02-01", "ຮ່ວມ-08"),
    ("DRV-LK-03", "ທ້າວ ພູວົງ", "Phouvong", "020 5520 4403", "1987-05-05", "2021-05-01", "LA-1907742", "C", "2021-05-01", "2029-05-01", "ຮ່ວມ-09"),
]
NOI_CAP = "ກົມຂົນສົ່ງ ວຽງຈັນ"       # đúng nơi cấp của các bằng đang có


def goi(duong, than=None, tk=None, cach=None):
    du = json.dumps(than).encode("utf-8") if than is not None else None
    r = urllib.request.Request(GOC + duong, data=du, method=cach or ("POST" if du is not None else "GET"),
                               headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + tk} if tk else {})})
    try:
        with urllib.request.urlopen(r, timeout=60) as t:
            return t.status, json.loads(t.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def phai(s, g, viec):
    if s != 200:
        raise SystemExit("DỪNG — %s: %s %s" % (viec, s, json.dumps(g, ensure_ascii=False)[:300]))
    return g


def main():
    s, g = goi("/api/dang-nhap", {"username": "admin", "password": "1234"})
    tk = phai(s, g, "đăng nhập admin")["token"]
    xe = {v["truck_no"]: v for v in phai(*goi("/api/vehicles", tk=tk), "đọc danh mục xe")}
    rm = {t["plate"]: t for t in phai(*goi("/api/trailers", tk=tk), "đọc danh mục rơ-moóc")}
    tx = {d["driver_code"]: d for d in phai(*goi("/api/drivers", tk=tk), "đọc danh mục tài xế")}
    chu = phai(*goi("/api/owners", tk=tk), "đọc danh mục chủ xe")
    print("Trang điều xe %s — đang có: %d xe · %d rơ-moóc · %d tài xế · %d chủ xe" % (GOC, len(xe), len(rm), len(tx), len(chu)))
    if not chu:
        raise SystemExit("DỪNG: chưa có chủ xe liên kết nào trong danh mục — xe liên kết cần chủ xe.")
    chu_xe = chu[0]
    moi_xe = [x for x in DAU_KEO if x[0] not in xe] + [x for x in LIEN_KET if x[0] not in xe]
    moi_rm = [r for r in RO_MOOC if r[0] not in rm]
    moi_tx = [d for d in TAI_XE if d[0] not in tx]
    print("%s: %d đầu kéo · %d rơ-moóc · %d tài xế (bỏ qua cái đã có)" % ("SẼ THÊM" if not THAT else "THÊM", len(moi_xe), len(moi_rm), len(moi_tx)))
    if not THAT:
        for x in moi_xe:
            print("   xe  %-9s %-14s %s" % (x[0], x[1], x[3]))
        for r in moi_rm:
            print("   rơ-moóc %-10s %s%s" % (r[0], r[1], " · đang sửa" if r[6] == "maintenance" else ""))
        for d in moi_tx:
            print("   tài xế %-10s %-18s %s · bằng tới %s · xe %s" % (d[0], d[1], d[2], d[9], d[10]))
        print("\n(chạy thử — chưa ghi gì; thêm tham số 'that' để thêm thật)")
        return
    # 1. đầu kéo
    for x in DAU_KEO:
        if x[0] in xe:
            continue
        so, hang, nam, bien, tai, dm, may, bh, dk, km = x
        xe[so] = phai(*goi("/api/vehicles", {"truck_no": so, "brand_model": hang, "year": nam, "plate_head": bien, "owner_type": "EPL",
                                             "capacity_t": tai, "fuel_norm": dm, "engine_cap": may, "tyre": "12R22.5",
                                             "insurance_exp": bh, "inspection_exp": dk, "odometer_km": km, "depot": "ທ່າບົກ"}, tk=tk), "thêm xe " + so)
        print("  ✓ xe %s · %s · %s" % (so, hang, bien))
    for x in LIEN_KET:
        if x[0] in xe:
            continue
        so, hang, nam, bien, tai, dm, may, km = x
        xe[so] = phai(*goi("/api/vehicles", {"truck_no": so, "brand_model": hang, "year": nam, "plate_head": bien, "owner_type": "joint",
                                             "owner_id": chu_xe["id"], "capacity_t": tai, "fuel_norm": dm, "engine_cap": may,
                                             "odometer_km": km, "depot": "ທ່າບົກ"}, tk=tk), "thêm xe liên kết " + so)
        print("  ✓ xe liên kết %s · chủ xe %s · %s" % (so, chu_xe["name"], bien))
    # 2. rơ-moóc, rồi lắp 14 cái đầu vào đúng xe
    lap_vao = [x[0] for x in DAU_KEO] + [x[0] for x in LIEN_KET]
    for i, r in enumerate(RO_MOOC):
        bien, loai, tai, nam, bh, dk, tt = r
        if bien not in rm:
            rm[bien] = phai(*goi("/api/trailers", {"plate": bien, "trailer_type": loai, "capacity_t": tai, "year": nam,
                                                   "owner_type": "joint" if bien.startswith("ກຂ 88") else "EPL",
                                                   "owner_name": chu_xe["name"] if bien.startswith("ກຂ 88") else None,
                                                   "insurance_exp": bh, "inspection_exp": dk, "status": tt, "depot": "ທ່າບົກ"}, tk=tk),
                            "thêm rơ-moóc " + bien)
            print("  ✓ rơ-moóc %s · %s%s" % (bien, loai, " · đang sửa" if tt == "maintenance" else ""))
        if i < len(lap_vao):
            v = xe[lap_vao[i]]
            if not v.get("trailer_id"):
                phai(*goi("/api/vehicles/%s/trailer" % v["id"], {"trailer_id": rm[bien]["id"], "reason": "lắp lúc nhập xe mới"}, tk=tk),
                     "lắp rơ-moóc %s vào xe %s" % (bien, v["truck_no"]))
                print("    ↳ lắp vào đầu kéo %s" % v["truck_no"])
    # 3. tài xế + bằng lái (bằng hiện hành ghi luôn một dòng lịch sử; ghi thêm nơi cấp)
    for d in TAI_XE:
        if d[0] in tx:
            continue
        ma, ten, latin, dt, sinh, vao, so_bang, hang, tu, toi, so_xe = d
        g = phai(*goi("/api/drivers", {"driver_code": ma, "name": ten, "name_latin": latin, "phone": dt, "dob": sinh, "hire_date": vao,
                                       "role": "main", "default_vehicle_id": xe[so_xe]["id"] if so_xe in xe else None}, tk=tk),
                 "thêm tài xế " + ma)
        phai(*goi("/api/drivers/%s/licenses" % g["id"], {"license_no": so_bang, "license_type": hang, "valid_from": tu, "valid_to": toi,
                                                         "issued_by": NOI_CAP}, tk=tk), "ghi bằng lái " + ma)
        print("  ✓ tài xế %s · %s (%s) · bằng %s tới %s · xe %s" % (ma, ten, latin, so_bang, toi, so_xe))
    s, xe2 = goi("/api/vehicles", tk=tk); s, rm2 = goi("/api/trailers", tk=tk); s, tx2 = goi("/api/drivers", tk=tk)
    print("\nXONG — nay có %d xe · %d rơ-moóc · %d tài xế." % (len(xe2), len(rm2), len(tx2)))


if __name__ == "__main__":
    main()

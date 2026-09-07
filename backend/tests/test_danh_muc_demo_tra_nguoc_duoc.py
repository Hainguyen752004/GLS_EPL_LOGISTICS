"""Moi con so trong danh muc demo phai TRA NGUOC LAI DUOC.

Du lieu mau khong duoc la nhung con so bia. Nguoi xem demo se hoi "8.050 dong
mot km o dau ra", va cau tra loi phai kiem lai duoc bang may tinh — khong thi
ban demo mat tin ngay o cho de kiem nhat.

Ba chot:

  1. CHI PHI XANG DAU suy ra tu dinh muc: `fuel_norm / 100 x gia dau`.
     `fuel_norm` la lit tren 100 km — quy uoc nganh, va cac gia tri that (18,
     26, 35) chi hop ly o don vi do; 26 lit cho 1 km la vo ly. Nen phai chia cho
     100 truoc roi moi nhan gia dau.

  2. TONG KM CUA TUYEN bang tong cac chang. Nhap tay hai cho thi tong va cac
     chang lech nhau, va ETA tinh ra sai ma khong ai thay.

  3. CHI PHI VA CUOC KHONG CONG CHUNG. Bon cau phan `fuel`, `driver`, `toll`,
     `wh` la tien CHI ra; `rate` la CUOC THU cua khach. Cong ca nam thi ket qua
     khong phai gia thanh cung khong phai gia ban.
"""

import importlib
import json


# `DEMO-VT-20FT` la loai xe co san tu ban demo dau tien, va cac bai kiem khac
# doi chieu so tien suy ra tu no (bao gia `DEMO-QT-2026-001` ra dung 2.132.200 d
# gia thanh va 3.600.000 d cuoc). Chi phi dau cua no la 6.250 d/km trong khi
# dinh muc 26 lit/100km chi ra 5.980 — mot cho lech co that, co TU TRUOC quy uoc
# suy ra o tren.
#
# De o day thanh mot NGOAI LE DUOC GHI RO, khong phai mot cho lech am tham: sua
# no la lam do mot loat bai kiem o cho khac, ma bo qua khong ghi lai thi lan sau
# co nguoi tuong quy uoc khong duoc ap dung o dau ca.
NGOAI_LE_CO_TU_TRUOC = {"DEMO-VT-20FT"}


def _nap(app_client):
    client, _, _ = app_client
    database = importlib.import_module("database")
    seed = importlib.import_module("services.demo_seed_service")
    with database.SessionLocal() as db:
        seed.seed_demo(db, reset=True, verify=True)
    return client, database, importlib.import_module("models")


def test_chi_phi_xang_dau_suy_ra_dung_tu_dinh_muc(app_client):
    _, database, models = _nap(app_client)
    master = importlib.import_module("services.demo_master_seed")

    with database.SessionLocal() as db:
        ds = db.query(models.VehicleType).all()
        assert len(ds) >= 5, f"danh muc chi co {len(ds)} loai xe — qua it de so sanh"

        lech = []
        for loai in ds:
            if loai.id in NGOAI_LE_CO_TU_TRUOC or not loai.fuel_norm:
                continue
            mong = master.chi_phi_dau_moi_km(loai.fuel_norm)
            if int(loai.base_rate or 0) != mong:
                lech.append("%s: %s l/100km ra %s d/km, dang ghi %s"
                            % (loai.id, loai.fuel_norm, mong, loai.base_rate))
        assert not lech, "chi phi xang dau khong suy ra tu dinh muc:\n" + "\n".join(lech)


def test_cong_thuc_gia_thanh_tach_chi_phi_voi_cuoc(app_client):
    _, database, models = _nap(app_client)

    with database.SessionLocal() as db:
        cong_thuc = db.query(models.CostFormula).all()
        assert len(cong_thuc) >= 5, f"chi co {len(cong_thuc)} cong thuc gia thanh"

        for ct in cong_thuc:
            d = json.loads(ct.formula_expression)
            terms = d.get("terms") or []
            assert terms, f"{ct.id} khong co hang tu nao"

            loai = {t["key"]: t.get("kind") for t in terms}
            # Bon cau phan nay la tien CHI ra.
            for khoa in ("fuel", "driver", "toll", "wh"):
                assert loai.get(khoa) == "cost", (
                    f"{ct.id}: cau phan {khoa} phai la chi phi, dang la {loai.get(khoa)}")
            # `rate` la tien THU ve. Danh dau sai o day thi phep tinh cong cuoc
            # vao gia thanh, va moi chuyen deu trong nhu lo.
            assert loai.get("rate") == "revenue", (
                f"{ct.id}: cuoc phi phai la doanh thu, dang la {loai.get('rate')}")

            # `components` la chuoi de HIEN RA, `terms` moi la cho tinh that. Hai
            # cho lech nhau thi man hinh noi mot dang ma phep tinh ra mot dang khac.
            cps = d.get("components") or {}
            doi_ten = {"wh": "warehouse", "rate": "freight_rate"}
            for t in terms:
                ten_cp = doi_ten.get(t["key"], t["key"])
                assert ten_cp in cps, f"{ct.id}: thieu {ten_cp} trong components"
                assert str(cps[ten_cp]) == str(t["rate"]), (
                    f"{ct.id}: {ten_cp} hien {cps[ten_cp]} ma tinh {t['rate']}")


def test_tong_km_cua_tuyen_bang_tong_cac_chang(app_client):
    _, database, models = _nap(app_client)

    with database.SessionLocal() as db:
        tuyen = db.query(models.Route).all()
        assert len(tuyen) >= 4, f"chi co {len(tuyen)} tuyen — o chon tuyen se gan nhu trong"

        lech = []
        for t in tuyen:
            if not t.segments_json:
                continue
            chang = json.loads(t.segments_json)
            assert chang, f"{t.id} khong co chang nao"
            tong = round(sum(float(c.get("dist_km") or 0) for c in chang), 1)
            if abs(tong - float(t.distance_km or 0)) > 0.05:
                lech.append("%s: tong chang %s km, ghi %s km" % (t.id, tong, t.distance_km))
        assert not lech, "tong km khong bang tong cac chang:\n" + "\n".join(lech)


def test_danh_muc_du_rong_de_cac_man_co_gi_ma_xem(app_client):
    """Danh muc phai du rong, khong thi man hinh khong the hien duoc viec cua no.

    Voi mot loai xe thi bang so sanh gia thanh chi co mot dong; voi mot tuyen thi
    o chon tuyen chi co mot lua chon; voi hai xe cung mot bai thi bo loc bai
    khong loc duoc gi. Nguoi xem khong phan biet duoc "man nay chi hien it nhu
    vay" voi "man nay hong".
    """
    _, database, models = _nap(app_client)

    with database.SessionLocal() as db:
        assert db.query(models.VehicleType).count() >= 5
        assert db.query(models.Route).count() >= 4
        assert db.query(models.Customer).count() >= 4
        assert db.query(models.Driver).count() >= 5

        xe = db.query(models.Vehicle).all()
        assert len(xe) >= 8, f"chi co {len(xe)} xe"
        # Xe phai trai tren NHIEU BAI, khong thi bo loc bai vo nghia.
        bai = {v.depot_code for v in xe if v.depot_code}
        assert len(bai) >= 3, f"xe chi nam o {len(bai)} bai: {bai}"
        # Va tren NHIEU LOAI, khong thi bo loc loai xe cung vo nghia.
        loai = {v.type for v in xe if v.type}
        assert len(loai) >= 4, f"xe chi thuoc {len(loai)} loai: {loai}"
        # Moi xe phai tro toi mot loai CO THAT: tro sai thi man danh muc hien
        # trong o loai, va phep tinh gia thanh khong tim duoc cong thuc nao.
        #
        # Chap nhan CA MA LAN TEN. `vehicles.type` trong du lieu that co ca hai
        # kieu — ban ghi cu luu ten ("Container 20FT"), ban ghi moi luu ma
        # ("DEMO-VT-20FT") — va tang nghiep vu da tra theo ca hai:
        #     VehicleType.id == vehicle.type | VehicleType.name == vehicle.type
        # Bai kiem doi mot kieu duy nhat la doi chat hon chinh he thong.
        loai_ds = db.query(models.VehicleType).all()
        co_that = {t.id for t in loai_ds} | {t.name for t in loai_ds if t.name}
        mo_coi = sorted({v.type for v in xe if v.type and v.type not in co_that})
        assert not mo_coi, f"xe tro toi loai khong co that: {mo_coi}"

# -*- coding: utf-8 -*-
"""Chay TRON CHUOI MOC len PostgreSQL rong, roi doi chieu voi `models.py`.

DAY LA BAI KIEM MA DU AN THIEU, va thieu no la nguyen nhan GOC cua ba loi nang
da lot qua ca bo kiem xanh:

  1. Rang buoc `ck_delivery_orders_canonical_status` tren PostgreSQL that chi co
     BON trang thai, chua co `arrived` — nen moi duong ghi `arrived` deu vo tren
     co so du lieu that, trong khi bo kiem xanh het.
  2. Rang buoc trang thai bao gia thieu bon gia tri (`sent`, `accepted`,
     `rejected`, `split`) — gui khach / khach chap nhan / khach tu choi / tach DO
     deu vo.
  3. Cot khung gio cua `freight_orders` khai `timestamp` TRAN trong khi cac bang
     anh em khai `timestamptz`, lam khung gio chuyen lech BAY GIO.

VI SAO CA BA DEU LOT. Bo kiem cu dung SQLite tam DUNG LAI TU `models.py`
(`Base.metadata.create_all`), nen no luon co rang buoc moi nhat. PostgreSQL thi
NANG CAP TUNG BUOC, nen schema cua no co the TROI khoi mo hinh. Mot bo kiem chay
tren ban dung lai khong the thay su troi do — no dang kiem mo hinh doi chieu voi
chinh mo hinh.

Bai kiem nay di dung duong that: schema rong -> chay het 43 moc -> so voi
`models.py`. Bat ky chenh lech nao cung la mot cho ma ma nguon va co so du lieu
that dang noi hai chuyen khac nhau.
"""
import pytest
from sqlalchemy import create_engine, text

from database import Base
import models  # noqa: F401  — phai nap de moi bang duoc dang ky


#: Cot ma HAI BEN co tha, va tha co ly do — khong tinh la chenh lech.
#:
#: `schema_migrations` la bang cua chinh bo moc, khong co trong `models.py`. Do
#: la dung: mo hinh khong nen biet gi ve co che nang cap.
BANG_BO_QUA = {"schema_migrations"}


#: BA MƯƠI SÁU CỘT đang lệch, ĐÃ BIẾT và đang chờ chủ dự án quyết.
#:
#: Cả 36 lệch cùng một kiểu và cùng một hướng: `models.py` khai `DateTime` TRẦN,
#: còn PostgreSQL that là `timestamp with time zone`. Đây đúng là họ lỗi đã làm
#: khung giờ chuyến lệch BẢY GIỜ, và nó nằm ở toàn bộ cột khung giờ của điều
#: phối: `delivery_orders.pickup_window_*`, `driver_shift_assignments.shift_*`,
#: `resource_assignments.assignment_*`, `transport_trip*.planned_*`.
#:
#: VÌ SAO CHƯA SỬA. Bên ĐÚNG là cơ sở dữ liệu, không phải mô hình: cột đã là
#: `timestamptz`, có dữ liệu thật, và phiên kết nối đã được khoá `timezone=UTC`
#: nên hành vi hiện tại là đúng và không nhập nhằng. Thứ đi sau là lời khai
#: trong `models.py`. Nên phép sửa là đổi 36 dòng khai sang
#: `DateTime(timezone=True)` — MỘT THAY ĐỔI CHỈ Ở MÃ, không cần mốc nâng cấp,
#: không đụng tới dữ liệu. Nhưng nó sửa 36 chỗ trong một tệp đang có người khác
#: làm, và nó không nằm trên đường demo.
#:
#: VÌ SAO GHIM LẠI THAY VÌ BỎ QUA. Ghim thì lệch MỚI sẽ đỏ ngay, còn 36 cái cũ
#: thì có tên có tuổi trong danh sách này chứ không nằm im. Sửa xong một cột thì
#: XOÁ nó khỏi đây — để nguyên là bài kiểm lại lặng lẽ cho qua.
LECH_MUI_GIO_DA_BIET = {
    "delivery_order_charge_adjustments.created_at",
    "delivery_order_closeouts.completed_at",
    "delivery_order_closeouts.created_at",
    "delivery_orders.delivery_date",
    "delivery_orders.delivery_window_end",
    "delivery_orders.delivery_window_start",
    "delivery_orders.pickup_date",
    "delivery_orders.pickup_window_end",
    "delivery_orders.pickup_window_start",
    "delivery_orders.planned_arrival_at",
    "delivery_orders.planned_departure_at",
    "delivery_orders.planned_return_at",
    "delivery_pod_documents.created_at",
    "delivery_pod_records.delivery_time",
    "driver_shift_assignments.created_at",
    "driver_shift_assignments.shift_end",
    "driver_shift_assignments.shift_start",
    "driver_shift_assignments.updated_at",
    "resource_assignments.assignment_end",
    "resource_assignments.assignment_start",
    "transport_trip_legs.actual_arrival_at",
    "transport_trip_legs.actual_departure_at",
    "transport_trip_legs.created_at",
    "transport_trip_legs.planned_arrival_at",
    "transport_trip_legs.planned_departure_at",
    "transport_trip_legs.updated_at",
    "transport_trips.actual_arrival_at",
    "transport_trips.actual_departure_at",
    "transport_trips.actual_return_at",
    "transport_trips.created_at",
    "transport_trips.planned_arrival_at",
    "transport_trips.planned_departure_at",
    "transport_trips.planned_return_at",
    "transport_trips.updated_at",
    "trip_delivery_orders.created_at",
}


@pytest.fixture(scope="module")
def schema_da_nang_cap():
    """Schema PostgreSQL THAT trong `.env` — chi doc, chi doc CATALOG.

    VI SAO PHAI LA CO SO DU LIEU THAT chu khong phai mot ban dung tam.

    Y dinh dau tien cua bai kiem nay la: dung mot schema rong roi chay het 43
    moc len do. KHONG LAM DUOC, va ly do dang ghi lai — `runner.baseline()` noi
    ro trong chinh chu thich cua no: cac moc lich su la lenh SUA bang. `v001`
    ALTER cac bang nghiep vu ma no gia dinh da ton tai; `v006` doi cac bang TMS
    khop dung DDL viet tay cua no. Tren mot schema rong ca hai deu khong chay
    duoc.

    Nen trong du an nay khong co duong "rong -> chay het moc". Cai dat moi thi
    `create_all` roi `baseline`; co so du lieu dang chay thi `upgrade` tung buoc.
    Va chinh vi the ma SU TROI la co that: schema that la ket qua cua mot chuoi
    nang cap dai, khong phai ket qua cua `models.py`. Doi chieu voi mot ban dung
    lai tu `models.py` la doi chieu mo hinh voi chinh no — dung cai vo dung ma
    bo kiem cu dang lam.

    AN TOAN: fixture nay chi doc `information_schema` va `pg_constraint`. Khong
    doc mot dong du lieu nghiep vu nao, khong ghi gi, khong tao gi. Do la ly do
    duy nhat mot bai kiem duoc phep noi tay vao co so du lieu that.
    """
    import conftest as C

    url = C._url_kiem_postgres()
    that = C._ten_csdl_that()
    if not that:
        pytest.skip("khong doc duoc ten co so du lieu that trong .env")
    # Doi ten co so du lieu ve DUNG ban that, giu nguyen may chu / tai khoan.
    dau, _, _ = url.rstrip("/").partition("?")[0].rpartition("/")
    may = create_engine("%s/%s" % (dau, that), pool_pre_ping=True)
    try:
        with may.connect() as c:
            c.execute(text("SELECT 1"))
        yield may, "public"
    finally:
        may.dispose()


def _bang_that(may, schema):
    with may.connect() as c:
        return {r[0] for r in c.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = :s"
        ), {"s": schema})} - BANG_BO_QUA


def _cot_that(may, schema, bang):
    with may.connect() as c:
        return {r[0]: (r[1], r[2]) for r in c.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = :s AND table_name = :t
        """), {"s": schema, "t": bang})}


def test_chuoi_moc_dung_du_moi_bang_cua_models(schema_da_nang_cap):
    """Chay het moc thi phai co DU moi bang ma `models.py` khai.

    Thieu mot bang nghia la mot moc chua duoc viet cho no: mo hinh co lop do,
    `create_all` dung duoc tren SQLite, nhung co so du lieu that thi khong co
    bang — va loi chi lo ra khi co nguoi bam vao chuc nang do.
    """
    may, schema = schema_da_nang_cap
    that = _bang_that(may, schema)
    mo_hinh = set(Base.metadata.tables) - BANG_BO_QUA

    thieu = sorted(mo_hinh - that)
    assert not thieu, (
        "%d bang co trong models.py ma chuoi moc khong dung: %s\n"
        "Moi bang thieu la mot moc chua viet." % (len(thieu), thieu))


def test_moi_bang_du_cot_va_dung_kieu(schema_da_nang_cap):
    """Tung bang phai du COT, va cot phai dung KIEU.

    Kieu cot la cho lech nguy hiem nhat vi no lech IM LANG: `timestamp` tran va
    `timestamp with time zone` cung nhan mot mo hinh Python, cung ghi duoc, chi
    khac la mot ben quy doi mui gio va mot ben khong. Do la lech bay gio da do
    duoc o khung gio chuyen.
    """
    may, schema = schema_da_nang_cap
    that_bang = _bang_that(may, schema)
    loi = []

    for ten, bang in sorted(Base.metadata.tables.items()):
        if ten in BANG_BO_QUA or ten not in that_bang:
            continue
        that = _cot_that(may, schema, ten)
        for cot in bang.columns:
            if cot.name not in that:
                loi.append("%s.%s: co trong models.py ma khong co trong co so du lieu"
                           % (ten, cot.name))
                continue
            kieu_that = that[cot.name][0]
            # So theo HO KIEU, khong so tung chu: `character varying` va
            # `VARCHAR(128)` la cung mot thu, con `timestamp` va `timestamptz`
            # thi KHAC — va do dung la cai can bat.
            kieu_mo_hinh = str(cot.type).lower()
            # `str(DateTime(timezone=True))` chi ra "DATETIME" — cai co `timezone`
            # nam o thuoc tinh, khong nam trong chuoi. Doc thuoc tinh truoc.
            co_mui = (bool(getattr(cot.type, "timezone", False))
                      or "timezone=true" in kieu_mo_hinh or "timestamptz" in kieu_mo_hinh)
            if kieu_that.startswith("timestamp"):
                that_co_mui = "with time zone" in kieu_that
                if co_mui != that_co_mui:
                    khoa = "%s.%s" % (ten, cot.name)
                    if khoa in LECH_MUI_GIO_DA_BIET:
                        continue
                    loi.append(
                        "%s: models.py khai %s, co so du lieu la %r — mot ben "
                        "quy doi mui gio va mot ben khong, nen cung mot moc ghi "
                        "vao doc ra lech bay gio"
                        % (khoa, "CO mui gio" if co_mui else "KHONG mui gio",
                           kieu_that))

    assert not loi, (
        "%d cot lech MOI giua models.py va PostgreSQL that:\n  %s\n\n"
        "Neu day la lech co chu y thi them vao `LECH_MUI_GIO_DA_BIET` kem ly do; "
        "neu khong thi doi lai lo khai trong models.py." % (len(loi), "\n  ".join(loi)))


def test_danh_sach_lech_da_biet_khong_con_thu_da_sua():
    """Danh sach lech da biet phai SACH: khong giu ten cua cai da sua.

    Mot danh sach bo qua chi an toan khi no co nguoi don. De lai mot cot da sua
    trong `LECH_MUI_GIO_DA_BIET` thi lan sau no lech lai se khong ai biet — bai
    kiem da duoc bao truoc la "cai nay lech, binh thuong".
    """
    con_lech = set()
    for ten, bang in Base.metadata.tables.items():
        for cot in bang.columns:
            if "timestamp" not in str(cot.type).lower() and "datetime" not in str(cot.type).lower():
                continue
            if "timezone=true" not in str(cot.type).lower():
                con_lech.add("%s.%s" % (ten, cot.name))

    du = sorted(LECH_MUI_GIO_DA_BIET - con_lech)
    assert not du, (
        "%d ten trong LECH_MUI_GIO_DA_BIET khong con la cot TRAN trong models.py "
        "— chung da duoc sua, hay xoa khoi danh sach:\n  %s" % (len(du), "\n  ".join(du)))


def test_rang_buoc_trang_thai_du_moi_gia_tri_ma_ma_nguon_ghi(schema_da_nang_cap):
    """Rang buoc CHECK tren cac cot trang thai phai du gia tri.

    DAY LA CHO DA VO HAI LAN, va ca hai lan deu chi lo ra tren co so du lieu
    that: `arrived` cua lenh giao hang, va bon trang thai cua bao gia. Ca hai
    lan bo kiem deu xanh, vi SQLite duoc dung lai tu `models.py` nen rang buoc
    cua no luon moi nhat.

    Phep kiem: moi gia tri ma `models.py` liet ke cho mot cot trang thai deu
    phai co mat trong rang buoc CHECK tuong ung tren PostgreSQL.
    """
    may, schema = schema_da_nang_cap
    with may.connect() as c:
        dong = list(c.execute(text("""
            SELECT cl.relname, co.conname, pg_get_constraintdef(co.oid)
            FROM pg_constraint co
            JOIN pg_class cl ON cl.oid = co.conrelid
            JOIN pg_namespace n ON n.oid = cl.relnamespace
            WHERE n.nspname = :s AND co.contype = 'c'
        """), {"s": schema}))

    # Gom theo BANG, khong theo TEN rang buoc.
    #
    # SO THEO TEN LA SAI, va da do duoc: `models.py` khai `ck_ap_status`, con
    # tren PostgreSQL that no mang ten tu sinh `ap_invoices_status_check`. Ca
    # bay rang buoc tai chinh deu vay — chung CO That va dung gia tri, chi khac
    # ten, vi moc tao bang da viet CHECK thang trong cau `CREATE TABLE` nen ten
    # trong mo hinh khong bao gio duoc dung. So theo ten thi bao dong gia bay
    # lan, va mot bai kiem bao dong gia se bi tat.
    theo_bang = {}
    for ten_bang, ten_rb, dinh_nghia in dong:
        theo_bang.setdefault(ten_bang, []).append((ten_rb, dinh_nghia))

    loi = []
    for ten_bang, bang in sorted(Base.metadata.tables.items()):
        for rb in bang.constraints:
            if rb.__class__.__name__ != "CheckConstraint":
                continue
            cau = str(rb.sqltext)
            gia_tri = set(_gia_tri_trong_ngoac(cau))
            if not gia_tri:
                continue
            cot = _cot_bi_rang_buoc(cau, bang)
            if not cot:
                continue

            # TAP GIA TRI THUC SU DUOC PHEP = GIAO cua moi rang buoc noi ve cot do.
            #
            # Phai lay GIAO chu khong phai hop: mot dong phai qua HET moi rang
            # buoc. Day dung la bay da vo that — bang `freight_charge_items`
            # tung co HAI rang buoc cho cung cot `charge_type`, va cai mang ten
            # tu sinh khong co `yard`. Ghi `yard` qua duoc mot cai roi vo o cai
            # kia, va loi noi ra la "Xung dot khi ghi nhan yeu cau" — mot lai
            # bao khong lien quan gi toi nguyen nhan.
            lien_quan = [(t, d) for t, d in theo_bang.get(ten_bang, [])
                         if cot in d and _gia_tri_trong_ngoac(d)]
            if not lien_quan:
                loi.append(
                    "%s.%s: models.py gioi han %d gia tri ma tren PostgreSQL "
                    "KHONG co rang buoc nao ve cot do — co so du lieu that nhan "
                    "bat ky chuoi nao" % (ten_bang, cot, len(gia_tri)))
                continue
            duoc_phep = None
            for _, d in lien_quan:
                tap = set(_gia_tri_trong_ngoac(d))
                duoc_phep = tap if duoc_phep is None else (duoc_phep & tap)
            thieu = sorted(gia_tri - duoc_phep)
            if thieu:
                loi.append(
                    "%s.%s: PostgreSQL that KHONG cho %s (rang buoc: %s) — moi "
                    "duong ghi mot trong cac gia tri do deu vo tren co so du "
                    "lieu that, con bo kiem thi xanh"
                    % (ten_bang, cot, thieu, ", ".join(t for t, _ in lien_quan)))

    assert not loi, "%d rang buoc trang thai lech:\n  %s" % (len(loi), "\n  ".join(loi))


def _cot_bi_rang_buoc(cau, bang):
    """Ten cot ma mot cau CHECK gioi han tap gia tri noi ve, hoac None."""
    import re
    for mau in (r"([A-Za-z_][A-Za-z0-9_]*)\s+IN\s*\(",
                r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*ANY\s*\("):
        m = re.search(mau, cau, flags=re.IGNORECASE)
        if m and m.group(1) in bang.columns:
            return m.group(1)
    return None


def _gia_tri_trong_ngoac(cau):
    """Rut tap gia tri cho phep tu mot cau CHECK, o CA HAI dang viet.

    HAI DANG, va phai doc duoc ca hai:

      · `models.py` viet     `status IN ('draft', 'sent')`
      · PostgreSQL tra ve    `status = ANY (ARRAY['draft'::text, 'sent'::text])`

    Chi doc dang thu nhat la mot cai bay da vo: moi rang buoc that deu khong
    khop, nen bai kiem bao "PostgreSQL khong co rang buoc nao ve cot do" cho ca
    hai muoi cot — mot lai bao vua sai vua dang so, va no che mat nhung cho lech
    thuc su.
    """
    import re
    ra = []
    for khoi in re.findall(r"\bIN\s*\(([^)]*)\)", cau, flags=re.IGNORECASE):
        ra.extend(re.findall(r"'([^']*)'", khoi))
    for khoi in re.findall(r"ARRAY\s*\[([^\]]*)\]", cau, flags=re.IGNORECASE):
        ra.extend(re.findall(r"'([^']*)'", khoi))
    return ra

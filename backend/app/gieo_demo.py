"""Dọn dữ liệu rác của bài kiểm rồi gieo một bộ demo đi được trọn luồng.

Sau khi chạy, mở trang lên là đã có sẵn:
  · một đơn CHƯA đóng gì   → để bấm thử đóng gói từ đầu;
  · một đơn ĐANG đóng dở   → để thấy cột "còn lại" hoạt động;
  · một đơn ĐÃ lên chuyến và đang trên đường → để thử quét tem và ký nhận.
"""

import io
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, tao_luoc_do
from models import (
    Customer,
    Delivery,
    InboundOrder,
    DeliveryEvent,
    Driver,
    PackingEvent,
    PackingLabel,
    PackingList,
    PackingListItem,
    PackingListPOD,
    Route,
    SalesOrder,
    SalesOrderLine,
    Vehicle,
)
from services import don_hang_service, giao_hang_service, packing_service, theo_doi_service
import seed

NGUOI = "demo"

HANG = [
    ("8858954206236", "4111396", "BISKIO ໄຂ່ໄດໂນປິສກິດຊັອກໂກແລັດ 15g_ຟ12",
     "BISKIO DINO EGG SURPRISE Biscuit Chocolate 15g_P12", 6.5, 0.035),
    ("8858954214934", "4111398", "BISKIO ໄຂ່ຄູໂຣມິປິສກິດຊັອກໂກແລັດ 30g_ຟ12",
     "BISKIO KUROMI EGG SURPRISE Biscuit Choco 30g_P12", 9.2, 0.042),
    ("8858954213524", "4111400", "BISKIO ໄຂ່ແຄຣແບປິສກິດຊັອກໂກແລັດ 30g_ຟ12",
     "BISKIO CAR BEARS EGG SURPRISE Biscuit Choco 30g_P12", 9.2, 0.042),
    ("8850987123456", "4222100", "ນ້ຳດື່ມ ຂວດ 600ml_ຟ24",
     "Drinking water 600ml bottle_P24", 14.4, 0.028),
]


def _dong(i, thung):
    ma_vach, ma_hang, mo_ta, mo_ta_en, kg, m3 = HANG[i]
    return {
        "line_no": i + 1,
        "barcode": ma_vach,
        "product_code": ma_hang,
        "description": mo_ta,
        "description_en": mo_ta_en,
        "vat_kind": "EXC",
        "vat_percent": 10,
        "pack_size": 12,
        "unit_quantity": "2CT",
        "case_qty": thung,
        "piece_qty": thung * 12,
        "uom": "CT",
        "unit_price": 343000,
        "discount": 0,
        "amount": 343000 * thung,
        "weight_kg": kg,
        "cube_m3": m3,
    }


def don_sach(db):
    """Xoá dữ liệu do bài kiểm sinh ra. Chỉ đụng vào PO có tiền tố của bài kiểm."""
    # Phiếu trong hộp chờ duyệt do bài kiểm nhận đơn tải lên. Xoá trước đơn hàng
    # vì phiếu đã duyệt trỏ tới đơn; xoá đơn trước là vướng khoá ngoại.
    so_phieu = (
        db.query(InboundOrder)
        .filter(InboundOrder.file_name.like("PO_6003990311%") | InboundOrder.subject.like("KIEM-%"))
        .delete(synchronize_session=False)
    )
    if so_phieu:
        print("Đã xoá %d phiếu nhận của bài kiểm." % so_phieu)
    db.flush()

    xoa = (
        db.query(SalesOrder)
        .filter(
            SalesOrder.po_number.like("KIEM-%")
            | SalesOrder.po_number.like("HTTP-%")
            | SalesOrder.po_number.like("6003990311%")
        )
        .all()
    )
    for don in xoa:
        for pl in db.query(PackingList).filter(PackingList.so_id == don.id).all():
            db.query(PackingListPOD).filter(PackingListPOD.packing_list_id == pl.id).delete()
            db.query(PackingEvent).filter(PackingEvent.packing_list_id == pl.id).delete()
            db.query(PackingLabel).filter(PackingLabel.packing_list_id == pl.id).delete()
            db.query(PackingListItem).filter(PackingListItem.packing_list_id == pl.id).delete()
            gh_id = pl.delivery_id
            db.delete(pl)
            if gh_id:
                db.flush()
                con = db.query(PackingList).filter(PackingList.delivery_id == gh_id).count()
                if con == 0:
                    db.query(DeliveryEvent).filter(DeliveryEvent.delivery_id == gh_id).delete()
                    gh = db.query(Delivery).filter(Delivery.id == gh_id).first()
                    if gh:
                        db.delete(gh)
        db.query(InboundOrder).filter(InboundOrder.so_id == don.id).delete(
            synchronize_session=False
        )
        db.query(SalesOrderLine).filter(SalesOrderLine.so_id == don.id).delete()
        db.delete(don)
    db.commit()
    return len(xoa)


def _tuyen(db, ma):
    r = db.query(Route).filter(Route.code == ma).first()
    return r.id if r else None


def _dung_chang_cho_tuyen_cu(db):
    """Tuyến gieo từ trước khi có bảng chặng thì chưa có chặng nào — dựng lại từ
    bảng TUYEN trong seed, để bản đồ vẽ được lộ trình và tổng km có nguồn."""
    from models import RouteSegment

    for ma_t, ten_t, ds_chang in seed.TUYEN:
        r = db.query(Route).filter(Route.code == ma_t).first()
        if not r:
            continue
        if db.query(RouteSegment).filter(RouteSegment.route_id == r.id).count():
            continue
        for i, (ma_di, ma_den, km) in enumerate(ds_chang, start=1):
            di = db.query(Customer).filter(Customer.code == ma_di).first()
            den = db.query(Customer).filter(Customer.code == ma_den).first()
            db.add(RouteSegment(
                route_id=r.id, seq=i,
                from_id=di.id if di else None, to_id=den.id if den else None,
                from_name=di.name if di else ma_di,
                to_name=den.name if den else ma_den,
                distance_km=km,
            ))
        r.distance_km = round(sum(x[2] for x in ds_chang), 2)
        print(f"  Đã dựng {len(ds_chang)} chặng cho tuyến {ma_t}")
    db.commit()


def _gan_tuyen_cho_phieu_cu(db):
    """Phiếu gieo trước khi có danh mục tuyến thì route_id rỗng — gắn lại theo
    điểm giao của đơn, để màn Theo dõi vẽ được đường."""
    for pl in db.query(PackingList).filter(PackingList.route_id.is_(None)).all():
        don = db.query(SalesOrder).filter(SalesOrder.id == pl.so_id).first()
        if not don:
            continue
        # Dò theo CHÍNH khách của đơn, không dò theo mã điểm giao: mã đó có thể
        # là số cũ ("60039") chứ không phải mã trong danh mục.
        from models import RouteSegment
        kh_id = don.customer_id
        if not kh_id and don.ship_to_code:
            kh = db.query(Customer).filter(Customer.code == don.ship_to_code).first()
            kh_id = kh.id if kh else None
        r = None
        if kh_id:
            # Tuyến có CHẶNG CUỐI dừng ở khách của đơn.
            chang = (
                db.query(RouteSegment)
                .filter(RouteSegment.to_id == kh_id)
                .order_by(RouteSegment.seq.desc())
                .first()
            )
            if chang:
                r = db.query(Route).filter(Route.id == chang.route_id).first()
        if r:
            pl.route_id = r.id
            pl.route_name = r.name
    db.commit()


def _tao_don(db, po, ship_to, ship_code, dong):
    co = db.query(SalesOrder).filter(SalesOrder.po_number == po).first()
    if co:
        return co
    khach = db.query(Customer).filter(Customer.code == ship_code).first()
    ncc = db.query(Customer).filter(Customer.code == "KPA-TRADE").first()
    return don_hang_service.tao(
        db,
        {
            "po_number": po,
            "order_date": "2026-09-14",
            "shipping_date": "2026-09-17",
            "customer_id": khach.id if khach else None,
            "vendor_id": ncc.id if ncc else None,
            "tax_number": "083753885-0-00",
            "currency": "LAK",
            "zone": "L0",
            "lines": dong,
        },
        NGUOI,
    )


def _ma_po_moi(db):
    """Sinh số PO chưa dùng, theo dãy 600399xxxx của phiếu mẫu."""
    n = 200
    while db.query(SalesOrder).filter(SalesOrder.po_number == "60039902%02d" % n).first():
        n += 1
    return "60039902%02d" % n


def _phieu_po_mau():
    """Dựng một phiếu PURCHASE ORDER dạng PDF để bấm thử màn Nhận đơn.

    Không có reportlab thì trả về None và bước gieo này bỏ qua — một bản demo
    thiếu phiếu mẫu vẫn chạy được, còn cài thêm thư viện cho máy người dùng thì
    không phải việc của lệnh gieo dữ liệu.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        return None, None

    hang_hoa = [
        ("8850002001234", "LA-100231", "LAY POTATO CHIP ORIGINAL 48G", 12, 24, 10000),
        ("8850002005678", "LA-100232", "TASTO BBQ FLAVOUR 62G", 12, 18, 12000),
        ("8851959132111", "LA-100233", "MAMA INSTANT NOODLE PORK 60G", 30, 40, 4500),
        ("8858891302222", "LA-100234", "BEER LAO LAGER CAN 330ML", 24, 60, 8500),
    ]
    po = "6003990%03d" % (300 + (uuid.uuid4().int % 90))

    bo_nho = io.BytesIO()
    kieu = getSampleStyleSheet()
    tai_lieu = SimpleDocTemplate(bo_nho, pagesize=A4, topMargin=15 * mm, bottomMargin=15 * mm,
                                 leftMargin=12 * mm, rightMargin=12 * mm)
    dau = [
        ["PO NUMBER:", po, "ORDER DATE:", "2026-09-14"],
        ["VENDOR:", "SENVANG TRADING CO., LTD", "SHIPPING DATE:", "2026-09-20"],
        ["TAX NUMBER:", "0105556098765", "CURRENCY:", "LAK"],
        ["SHIP TO CODE:", "PTTLAO-DONEKOY", "", ""],
        ["SHIP TO:", "PTTLAO DONEKOY", "", ""],
        ["ADDRESS:", "Donekoy Village, Sisattanak, Vientiane", "", ""],
    ]
    b1 = Table(dau, colWidths=[30 * mm, 75 * mm, 30 * mm, 45 * mm])
    b1.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
    ]))

    bang = [["NO", "BARCODE", "ITEM ID", "ITEM DESCRIPTION", "PACK\nSIZE",
             "UNIT QUANTITY\n(UNIT/PACK/CASE)", "UNIT PRICE", "AMOUNT"]]
    tong = 0
    for i, (bc, ma, ten, quy, thung, gia) in enumerate(hang_hoa, start=1):
        tien = quy * thung * gia
        tong += tien
        bang.append([str(i), bc, ma, ten, str(quy), "%dCT" % thung,
                     "{:,.2f}".format(gia), "{:,.2f}".format(tien)])
    bang.append(["", "", "", "TOTAL", "", "", "", "{:,.2f}".format(tong)])
    b2 = Table(bang, colWidths=[9 * mm, 28 * mm, 22 * mm, 58 * mm, 13 * mm,
                                26 * mm, 20 * mm, 24 * mm], repeatRows=1)
    b2.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (4, 1), (-1, -1), "RIGHT"),
    ]))
    tai_lieu.build([Paragraph("<b>PURCHASE ORDER</b>", kieu["Title"]), Spacer(1, 4 * mm),
                    b1, Spacer(1, 5 * mm), b2])
    return bo_nho.getvalue(), po


def them_phieu_cho_duyet(db):
    """LUÔN có một phiếu nằm trong hộp chờ duyệt của màn Nhận đơn.

    Để mở trang lên là bấm duyệt thử được ngay, không cần hộp thư đã cấp quyền.
    Phiếu này do AI đọc thật, nên con số hiện trên màn đúng là thứ máy đọc ra.
    """
    from services import doc_don_ai, nhan_don_service

    co = (
        db.query(InboundOrder)
        .filter(InboundOrder.status.in_(["new", "parsed", "failed"]))
        .count()
    )
    if co:
        print("Đang có %d phiếu chờ duyệt — không gieo thêm." % co)
        return None
    if not doc_don_ai.san_sang():
        print("Chưa cấu hình GEMINI_API_KEY_GT — bỏ qua phiếu chờ duyệt.")
        return None

    du_lieu, po = _phieu_po_mau()
    if du_lieu is None:
        print("Máy chưa có reportlab — bỏ qua phiếu chờ duyệt mẫu.")
        return None

    ib = nhan_don_service.them_tu_tep(
        db, "PO_%s.pdf" % po, "application/pdf", du_lieu, "khach@demo.la",
        "Phiếu mẫu để bấm thử màn Nhận đơn",
    )
    db.commit()
    try:
        ib = nhan_don_service.doc_bang_ai(db, ib.id)
        db.commit()
        print("Phiếu CHỜ DUYỆT mới: %s / PO %s — AI đọc %d%%, %d dòng hàng"
              % (ib.id, po, ib.ai_confidence, len(json.loads(ib.draft or "{}").get("lines") or [])))
    except Exception as loi:  # noqa: BLE001
        db.rollback()
        print("Đã nhận phiếu %s nhưng AI chưa đọc được: %s" % (ib.id, loi))
    return ib


def them_don_chua_dong(db):
    """LUÔN có một đơn CHƯA đóng gì, để bấm thử màn Packing List từ đầu.

    Chủ dự án bấm hết kịch bản thì mọi đơn đều đã đóng đủ; mở lại mà không còn
    đơn trắng nào thì màn đóng gói không có gì để gõ.
    """
    co = db.query(SalesOrder).filter(SalesOrder.status == "new").count()
    if co:
        print(f"Đang có {co} đơn chưa đóng — không gieo thêm.")
        return None
    po = _ma_po_moi(db)
    don = _tao_don(db, po, "PTTLAO DONEKOY", "PTTLAO-DONEKOY", [_dong(0, 24), _dong(1, 24), _dong(2, 24)])
    db.commit()
    print(f"Đơn CHƯA ĐÓNG mới: {don.id} / PO {po} — 3 dòng hàng, 72 thùng")
    return don


def them_don_dong_do(db):
    """LUÔN có một đơn ĐANG ĐÓNG DỞ, để thấy cột 'Còn lại' hoạt động."""
    co = db.query(SalesOrder).filter(SalesOrder.status == "packing").count()
    if co:
        print(f"Đang có {co} đơn đóng dở — không gieo thêm.")
        return None
    po = _ma_po_moi(db)
    don = _tao_don(db, po, "PTTLAO SIKHAY", "PTTLAO-SIKHAY", [_dong(0, 20), _dong(1, 12), _dong(3, 30)])
    db.commit()

    don = don_hang_service.nap(db, don.id)
    pl = packing_service.tao(
        db, don.id,
        {
            "items": [
                {"so_line_id": don.lines[0].id, "case_qty": 8, "piece_qty": 96},
                {"so_line_id": don.lines[2].id, "case_qty": 10, "piece_qty": 120},
            ],
            "box_count": 18,
            "route_id": _tuyen(db, "RT-VTE-SIKHAY"),
            "wave": "W1",
            "gate": "B",
        },
        NGUOI,
    )
    db.commit()
    print(f"Đơn ĐÓNG DỞ mới: {don.id} / PO {po} — đã đóng {pl.id}, còn 44 thùng")
    return don


def them_don_dang_giao(db):
    """Sinh thêm một đơn đã đóng đủ, đã lên chuyến, đang ở trạng thái ĐÃ TỚI NƠI
    với một Packing List CHƯA ký nhận — để lúc nào mở lên cũng có cái để bấm.

    Chỉ sinh khi KHÔNG còn chuyến nào đang chạy. Chạy lại nhiều lần không đẻ ra
    một đống chuyến rác.
    """
    dang_chay = (
        db.query(Delivery)
        .filter(Delivery.status.in_(["planned", "loading", "in_transit", "arrived"]))
        .count()
    )
    if dang_chay:
        print(f"Đang có {dang_chay} chuyến chưa đóng — không gieo thêm.")
        return None

    dem = db.query(SalesOrder).filter(SalesOrder.po_number.like("600399019%")).count()
    po = "600399019%d" % (dem + 4)
    while db.query(SalesOrder).filter(SalesOrder.po_number == po).first():
        dem += 1
        po = "600399019%d" % (dem + 4)

    don = _tao_don(db, po, "PTTLAO SIKHAY", "PTTLAO-SIKHAY", [_dong(0, 8), _dong(3, 12)])
    db.commit()

    packing_service.tao_tu_dong(db, don.id, 2, NGUOI)
    db.commit()

    ds = db.query(PackingList).filter(PackingList.so_id == don.id).all()
    rid = _tuyen(db, "RT-VTE-SIKHAY")
    for pl in ds:
        pl.route_id = rid
    db.commit()
    xe = db.query(Vehicle).filter(Vehicle.internal_no == "342").first() or db.query(Vehicle).first()
    tx = db.query(Driver).filter(Driver.code == "DRV-002").first() or db.query(Driver).first()
    gh = giao_hang_service.tao(
        db,
        {
            "packing_list_ids": [p.id for p in ds],
            "vehicle_id": xe.id if xe else None,
            "driver_id": tx.id if tx else None,
            "route_name": "Kho Vientiane → PTTLAO SIKHAY",
        },
        NGUOI,
    )
    db.commit()
    for buoc in ("loading", "in_transit", "arrived"):
        giao_hang_service.doi_trang_thai(db, gh.id, buoc, NGUOI)
        db.commit()

    # Ký nhận MỘT phiếu, chừa phiếu còn lại cho người xem tự bấm.
    giao_hang_service.ghi_pod(
        db, ds[0].id,
        {"received_by": "Bounma", "result": "full", "goods_condition": "Nguyên kiện"},
        NGUOI,
    )
    db.commit()
    print(f"Đơn ĐANG GIAO mới: {don.id} / PO {po} / chuyến {gh.code} "
          f"— còn {ds[1].id} chưa ký nhận")
    return gh


def gieo():
    tao_luoc_do()
    seed.gieo()

    db = SessionLocal()
    try:
        bo = don_sach(db)
        if bo:
            print(f"Đã dọn {bo} đơn rác của bài kiểm.")

        # Đơn gieo từ trước khi có danh mục thì chưa gắn customer_id. Gắn lại theo
        # mã hoặc tên điểm giao, để màn Theo dõi biết điểm đến của chuyến.
        for don in db.query(SalesOrder).filter(SalesOrder.customer_id.is_(None)).all():
            kh = (
                db.query(Customer).filter(Customer.code == (don.ship_to_code or "")).first()
                or db.query(Customer).filter(Customer.name == (don.ship_to_name or "")).first()
                or db.query(Customer).filter(Customer.tax_number == (don.ship_to_code or "")).first()
            )
            if kh:
                don.customer_id = kh.id
                don.ship_to_code = kh.code
                don.ship_to_address = don.ship_to_address or kh.address
        db.commit()

        # 1) Đơn chưa đóng gì — chính là phiếu PO thật đã gieo ở seed.py
        print("Đơn 1 (chưa đóng): SO-2026-0001 / PO 6003990191")

        # 2) Đơn đang đóng dở
        d2 = _tao_don(db, "6003990192", "PTTLAO SIKHAY", "PTTLAO-SIKHAY",
                      [_dong(0, 20), _dong(1, 12), _dong(3, 30)])
        db.commit()
        if not db.query(PackingList).filter(PackingList.so_id == d2.id).count():
            d2 = don_hang_service.nap(db, d2.id)
            packing_service.tao(
                db, d2.id,
                {
                    "items": [
                        {"so_line_id": d2.lines[0].id, "case_qty": 8, "piece_qty": 96},
                        {"so_line_id": d2.lines[2].id, "case_qty": 10, "piece_qty": 120},
                    ],
                    "box_count": 18,
                    "route_id": _tuyen(db, "RT-VTE-SIKHAY"),
                    "wave": "W1",
                    "gate": "B",
                },
                NGUOI,
            )
            db.commit()
        print(f"Đơn 2 (đóng dở): {d2.id} / PO 6003990192")

        # 3) Đơn đã đóng đủ, đã lên chuyến và đang trên đường
        d3 = _tao_don(db, "6003990193", "PTTLAO DONEKOY", "PTTLAO-DONEKOY",
                      [_dong(1, 10), _dong(2, 10)])
        db.commit()
        if not db.query(PackingList).filter(PackingList.so_id == d3.id).count():
            packing_service.tao_tu_dong(db, d3.id, 2, NGUOI)
            db.commit()

            ds = db.query(PackingList).filter(PackingList.so_id == d3.id).all()
            xe = db.query(Vehicle).first()
            tx = db.query(Driver).first()
            gh = giao_hang_service.tao(
                db,
                {
                    "packing_list_ids": [p.id for p in ds],
                    "vehicle_id": xe.id if xe else None,
                    "driver_id": tx.id if tx else None,
                    "route_name": "Vientiane → Donekoy",
                },
                NGUOI,
            )
            db.commit()
            giao_hang_service.doi_trang_thai(db, gh.id, "loading", NGUOI)
            db.commit()
            giao_hang_service.doi_trang_thai(db, gh.id, "in_transit", NGUOI)
            db.commit()
            giao_hang_service.doi_trang_thai(db, gh.id, "arrived", NGUOI)
            db.commit()
            # Ký nhận MỘT phiếu thôi, để còn một phiếu cho người xem tự bấm thử.
            giao_hang_service.ghi_pod(
                db, ds[0].id,
                {"received_by": "Somchai", "result": "full", "goods_condition": "Nguyên kiện"},
                NGUOI,
            )
            db.commit()
            print(f"Đơn 3 (đang giao): {d3.id} / chuyến {gh.code}")
        else:
            print(f"Đơn 3 (đang giao): {d3.id} — đã có sẵn")

        _dung_chang_cho_tuyen_cu(db)
        _gan_tuyen_cho_phieu_cu(db)

        # 4) LUÔN đủ BA trạng thái để bấm thử. Chủ dự án bấm hết kịch bản rồi
        # thì mọi đơn đều đã đóng đủ và mọi chuyến đều đã đóng; gieo lại mà
        # không có ba bước này là mở lên không còn gì để thao tác.
        them_phieu_cho_duyet(db)
        them_don_chua_dong(db)
        them_don_dong_do(db)
        them_don_dang_giao(db)

        # Vệt GPS mô phỏng cho mọi chuyến đang chạy mà chưa có mốc nào
        from models import VehiclePosition
        for gh in db.query(Delivery).filter(Delivery.status.in_(["in_transit", "arrived"])).all():
            if db.query(VehiclePosition).filter(VehiclePosition.delivery_id == gh.id).count():
                continue
            gh = giao_hang_service.nap(db, gh.id)
            try:
                for _ in range(4):
                    theo_doi_service.mo_phong_chay_tiep(db, gh.id, 0.2, NGUOI)
                db.commit()
                print(f"  Đã gieo vệt GPS mô phỏng cho {gh.code}")
            except Exception as loi:  # noqa: BLE001
                db.rollback()
                print(f"  Bỏ qua vệt GPS cho {gh.code}: {loi}")

        print("\nXong. Chạy: python chay.py  →  http://127.0.0.1:8042")
    finally:
        db.close()


if __name__ == "__main__":
    gieo()

"""Chạy trọn luồng của bản demo trên cơ sở dữ liệu thật.

    Đơn hàng -> Packing List -> chuyến giao hàng -> quét tem -> ký nhận -> đã giao

Bài này cố tình đi cả những lối SAI (đóng vượt số đặt, nhảy cóc trạng thái, ký
nhận khi chưa rời bãi) vì đó mới là chỗ bản demo dễ vỡ.
"""

import os
import sys
import uuid

GOC_APP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app"))
sys.path.insert(0, GOC_APP)

from database import SessionLocal, tao_luoc_do  # noqa: E402
from models import Customer, Driver, Vehicle  # noqa: E402
from services import don_hang_service, giao_hang_service, packing_service  # noqa: E402
from services.loi import LoiNghiepVu  # noqa: E402

NGUOI = "kiem-tra"
_loi = []


def kiem(dieu_kien, nhan):
    if dieu_kien:
        print(f"  OK   {nhan}")
    else:
        print(f"  FAIL {nhan}")
        _loi.append(nhan)


def phai_nem(ma_mong_doi, ham, nhan):
    try:
        ham()
    except LoiNghiepVu as loi:
        kiem(loi.ma == ma_mong_doi, f"{nhan} (chặn bằng {loi.ma})")
        return
    kiem(False, f"{nhan} — KHÔNG bị chặn, đây là lỗ hổng")


def chay():
    tao_luoc_do()
    db = SessionLocal()
    try:
        hau_to = uuid.uuid4().hex[:6].upper()

        print("\n[1] Tạo đơn hàng khách")
        from models import Customer
        kh = db.query(Customer).filter(Customer.kind == "customer").first()
        kiem(kh is not None, "danh mục có khách hàng để chọn")
        don = don_hang_service.tao(
            db,
            {
                "po_number": f"KIEM-{hau_to}",
                "customer_id": kh.id if kh else None,
                "order_date": "2026-09-14",
                "shipping_date": "2026-09-17",
                "ship_to_code": "60039",
                "ship_to_name": "PTTLAO DONEKOY",
                "vendor_name": "KPA Trade",
                "currency": "LAK",
                "lines": [
                    {
                        "line_no": 1,
                        "barcode": "8858954206236",
                        "product_code": "4111396",
                        "description": "BISKIO DINO 15g",
                        "case_qty": 10,
                        "piece_qty": 120,
                        "uom": "CT",
                        "unit_price": 343000,
                        "amount": 686000,
                        "weight_kg": 6.5,
                        "cube_m3": 0.035,
                    },
                    {
                        "line_no": 2,
                        "barcode": "8858954214934",
                        "product_code": "4111398",
                        "description": "BISKIO KUROMI 30g",
                        "case_qty": 6,
                        "piece_qty": 72,
                        "uom": "CT",
                        "unit_price": 343000,
                        "amount": 686000,
                        "weight_kg": 9.2,
                        "cube_m3": 0.042,
                    },
                ],
            },
            NGUOI,
        )
        db.commit()
        db.refresh(don)
        d1, d2 = don.lines[0].id, don.lines[1].id
        kiem(don.status == "new", "đơn mới tạo ở trạng thái new")

        print("\n[2] Đóng gói không được vượt số đã đặt")
        phai_nem(
            "PL_OVER_ORDERED",
            lambda: packing_service.tao(
                db, don.id, {"items": [{"so_line_id": d1, "case_qty": 99, "piece_qty": 0}]}, NGUOI
            ),
            "đóng 99 thùng khi đơn chỉ đặt 10",
        )
        db.rollback()
        phai_nem(
            "PL_ITEM_NO_SO_LINE",
            lambda: packing_service.tao(db, don.id, {"items": [{"case_qty": 1}]}, NGUOI),
            "dòng hàng không chỉ rõ thuộc dòng nào của đơn",
        )
        db.rollback()

        print("\n[3] Tạo Packing List thứ nhất")
        pl1 = packing_service.tao(
            db,
            don.id,
            {
                "items": [
                    {"so_line_id": d1, "case_qty": 4, "piece_qty": 48},
                    {"so_line_id": d2, "case_qty": 2, "piece_qty": 24},
                ],
                "box_count": 6,
                "route_name": "Kho Vientiane -> PTTLAO DONEKOY",
            },
            NGUOI,
        )
        db.commit()
        kiem(pl1.total_cases == 6, "tổng thùng của phiếu = 6")
        kiem(len(pl1.labels) == 6, "sinh đủ 6 tem QR")
        kiem(all(it.so_line_id for it in pl1.items), "mọi dòng hàng đều gắn dòng của đơn")
        kiem(
            abs(pl1.total_weight_kg - (6.5 * 4 + 9.2 * 2)) < 0.001,
            "trọng lượng tính theo số thùng thật",
        )

        don = don_hang_service.nap(db, don.id)
        kiem(don.status == "packing", "đơn chuyển sang đang đóng gói")

        print("\n[4] Phần còn lại của đơn phải trừ đi phần đã đóng")
        ra = don_hang_service.ra_dict(db, don)
        con_d1 = next(x for x in ra["lines"] if x["id"] == d1)
        kiem(con_d1["remaining_case_qty"] == 6, "dòng 1 còn lại 6 thùng")
        kiem(ra["fully_packed"] is False, "đơn chưa đóng đủ")

        print("\n[5] Chia tự động phần còn lại thành 2 phiếu")
        them = packing_service.tao_tu_dong(db, don.id, 2, NGUOI)
        db.commit()
        kiem(len(them) == 2, "chia ra đúng 2 phiếu")
        ra = don_hang_service.ra_dict(db, don_hang_service.nap(db, don.id))
        kiem(ra["remaining_case_qty"] == 0, "chia xong thì đơn hết hàng chưa đóng")
        kiem(ra["fully_packed"] is True, "đơn đã đóng đủ")
        kiem(
            don_hang_service.nap(db, don.id).status == "packed",
            "đơn chuyển sang đã đóng đủ",
        )

        print("\n[6] Không được đóng thêm khi đơn đã đủ")
        phai_nem(
            "PL_NOTHING_LEFT",
            lambda: packing_service.tao_tu_dong(db, don.id, 1, NGUOI),
            "chia tiếp khi không còn gì",
        )
        db.rollback()

        print("\n[7] Trạng thái Packing List phải đi lần lượt")
        phai_nem(
            "PL_STATUS_SKIP",
            lambda: packing_service.doi_trang_thai(db, pl1.id, "loaded", NGUOI),
            "nhảy từ ready thẳng sang loaded",
        )
        db.rollback()
        packing_service.doi_trang_thai(db, pl1.id, "parked", NGUOI)
        db.commit()
        phai_nem(
            "PL_STATUS_BACKWARD",
            lambda: packing_service.doi_trang_thai(db, pl1.id, "ready", NGUOI),
            "lùi trạng thái",
        )
        db.rollback()

        print("\n[8] Quét tem trả về đủ dây truy ngược")
        pl1 = packing_service.nap(db, pl1.id)
        tem = pl1.labels[0]
        ket_qua = packing_service.quet_tem(db, tem.qr_token, NGUOI)
        db.commit()
        kiem(ket_qua["packing_list"]["id"] == pl1.id, "quét ra đúng Packing List")
        kiem(ket_qua["sales_order"]["id"] == don.id, "quét ra đúng đơn hàng")
        kiem(
            all(it["so_line_id"] for it in ket_qua["packing_list"]["items"]),
            "từng dòng hàng chỉ rõ thuộc dòng nào của đơn",
        )
        lan_hai = packing_service.quet_tem(db, tem.qr_token, NGUOI)
        db.commit()
        kiem(lan_hai["label"]["first_scan"] is False, "quét lặp không tính thành kiện mới")
        kiem(lan_hai["label"]["scanned_count"] == 1, "vẫn chỉ đếm 1 kiện đã quét")
        phai_nem(
            "LABEL_NOT_FOUND",
            lambda: packing_service.quet_tem(db, "KHONG-CO-TEM-NAY", NGUOI),
            "quét tem lạ",
        )
        db.rollback()

        print("\n[9] Lập chuyến giao hàng")
        xe = db.query(Vehicle).first()
        tx = db.query(Driver).first()
        gh = giao_hang_service.tao(
            db,
            {
                "packing_list_ids": [pl1.id, them[0].id],
                "vehicle_id": xe.id if xe else None,
                "driver_id": tx.id if tx else None,
                "route_name": "Vientiane -> Donekoy",
            },
            NGUOI,
        )
        db.commit()
        kiem(gh.status == "planned", "chuyến mới ở trạng thái đã lên kế hoạch")
        kiem(len(gh.packing_lists) == 2, "chuyến chở 2 Packing List")

        print("\n[10] Một Packing List không nằm trên hai chuyến")
        phai_nem(
            "PL_ON_OTHER_DELIVERY",
            lambda: giao_hang_service.tao(db, {"packing_list_ids": [pl1.id]}, NGUOI),
            "xếp lại phiếu đang ở chuyến khác",
        )
        db.rollback()

        print("\n[11] Chưa rời bãi thì chưa ký nhận được")
        phai_nem(
            "PL_NOT_DISPATCHED",
            lambda: giao_hang_service.ghi_pod(db, pl1.id, {"received_by": "Ông A"}, NGUOI),
            "ký nhận khi hàng còn trong bãi",
        )
        db.rollback()

        print("\n[12] Cho chuyến xuất phát")
        giao_hang_service.doi_trang_thai(db, gh.id, "loading", NGUOI)
        db.commit()
        giao_hang_service.doi_trang_thai(db, gh.id, "in_transit", NGUOI)
        db.commit()
        gh = giao_hang_service.nap(db, gh.id)
        kiem(
            all(pl.status == "dispatched" for pl in gh.packing_lists),
            "mọi Packing List trên xe đều thành đã xuất bãi",
        )
        kiem(gh.departed_at is not None, "có mốc giờ xuất phát")
        kiem(
            don_hang_service.nap(db, don.id).status == "delivering",
            "đơn chuyển sang đang giao",
        )

        print("\n[13] Ký nhận theo từng Packing List")
        phai_nem(
            "POD_NO_RECEIVER",
            lambda: giao_hang_service.ghi_pod(db, pl1.id, {}, NGUOI),
            "ký nhận mà không ghi tên người nhận",
        )
        db.rollback()
        giao_hang_service.doi_trang_thai(db, gh.id, "arrived", NGUOI)
        db.commit()
        giao_hang_service.ghi_pod(
            db,
            pl1.id,
            {"received_by": "Somchai", "result": "full", "goods_condition": "Nguyên kiện"},
            NGUOI,
        )
        db.commit()
        kiem(
            packing_service.nap(db, pl1.id).status == "delivered",
            "ký nhận xong thì phiếu thành đã giao",
        )

        print("\n[14] Chuyến chưa đủ POD thì chưa đóng được")
        phai_nem(
            "DL_MISSING_POD",
            lambda: giao_hang_service.doi_trang_thai(db, gh.id, "delivered", NGUOI),
            "đóng chuyến khi còn phiếu chưa ký nhận",
        )
        db.rollback()
        giao_hang_service.ghi_pod(db, them[0].id, {"received_by": "Somchai"}, NGUOI)
        db.commit()
        giao_hang_service.doi_trang_thai(db, gh.id, "delivered", NGUOI)
        db.commit()
        kiem(giao_hang_service.nap(db, gh.id).status == "delivered", "chuyến đã giao xong")

        print("\n[15] Huỷ Packing List thì trả hàng về cho đơn")
        con_lai_truoc = don_hang_service.ra_dict(db, don_hang_service.nap(db, don.id))[
            "remaining_case_qty"
        ]
        packing_service.huy(db, them[1].id, "Kiểm thử huỷ", NGUOI)
        db.commit()
        con_lai_sau = don_hang_service.ra_dict(db, don_hang_service.nap(db, don.id))[
            "remaining_case_qty"
        ]
        kiem(
            con_lai_sau > con_lai_truoc,
            "huỷ phiếu xong thì số hàng chưa đóng của đơn tăng lại",
        )

        print("\n[16] Phiếu đã rời bãi thì không huỷ được")
        phai_nem(
            "PL_ALREADY_OUT",
            lambda: packing_service.huy(db, pl1.id, "thử", NGUOI),
            "huỷ phiếu đã giao",
        )
        db.rollback()

    finally:
        db.close()

    print("\n" + "=" * 60)
    if _loi:
        print(f"CÓ {len(_loi)} MỤC HỎNG:")
        for x in _loi:
            print("  -", x)
        sys.exit(1)
    print("TOÀN BỘ LUỒNG A-Z CHẠY ĐÚNG")
    sys.exit(0)


if __name__ == "__main__":
    chay()

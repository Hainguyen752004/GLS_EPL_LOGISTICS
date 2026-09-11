# -*- coding: utf-8 -*-
"""Ba việc chốt ngày 11/09/2026: chặn hàng chiều về, nhãn xe đang quay về, công thức ngoại tệ.

Ba thứ rời nhau nhưng cùng một gốc: hệ thống IM LẶNG ở chỗ đáng lẽ phải nói.

1. **Chặn hàng chiều về.** Chuyến chở hàng chiều về là một ngõ cụt làm mất doanh thu — DO
   chiều về chỉ có chặng `backhaul`, mà bước hoàn tất chỉ nhận POD cho chặng `delivery`, nên
   nó không ký nhận được; kéo theo `complete_return` luôn trả `409 OPEN_DELIVERY_ORDER`, xe
   bị giữ mãi, và lô hàng về không có hồ sơ quyết toán để sang bên công nợ. Trước đây người
   điều phối chỉ phát hiện ở bước cuối, lúc hàng đã chở xong.

2. **Xe đang quay về.** Xe đã giao xong, chỉ còn chặng về bãi, nhưng màn hình vẫn nói trống
   không là "đang chạy" — người điều độ không biết mấy giờ nó rảnh để xếp chuyến kế.

3. **Công thức ngoại tệ.** Công thức giá thành đánh mã kèm đơn vị tiền, nên báo giá USD tra
   không ra công thức USD và hồ sơ quyết toán trả danh sách khoản mục RỖNG — 8 trong 29 lệnh
   đã hoàn tất trên dữ liệu thật rơi vào cảnh đó.
"""
import datetime as dt
import importlib

import pytest

from conftest import API_TEST_HEADERS


# ----------------------------------------------------------------- 1. chặn hàng chiều về

def test_tao_chuyen_cho_hang_chieu_ve_bi_chan_ngay_o_dau_vao():
    """`backhaul` và `returned_goods` phải bị từ chối NGAY, không để đi tới ngõ cụt."""
    trip_service = importlib.import_module("services.tms_trip_service")
    from services.errors import DomainError

    for muc_dich in ("backhaul", "returned_goods"):
        with pytest.raises(DomainError) as loi:
            trip_service._chan_hang_chieu_ve(muc_dich)
        assert loi.value.code == "TRIP_HANG_CHIEU_VE_CHUA_HO_TRO"
        assert loi.value.status_code == 422
        # Lời báo phải NÓI ĐƯỜNG ĐI TIẾP, không chỉ nói "không được".
        assert "rỗng" in loi.value.message.lower(), loi.value.message

    # Xe về RỖNG không bị chặn — nhánh đó chạy đúng trọn luồng, chặn nhầm là phá luồng đang tốt.
    assert trip_service._chan_hang_chieu_ve("empty_return") is None
    assert trip_service._chan_hang_chieu_ve("none") is None


def test_ca_hai_duong_vao_deu_bi_chan_khong_bo_ngo_cua_sau():
    """Chặn ở `create_trip_from_delivery_orders` mà bỏ ngỏ `add_leg` thì coi như không chặn.

    `add_leg` nhận thẳng `leg_type="backhaul"`, không đi qua chỗ kiểm `return_purpose`. Bài
    này đọc mã nguồn vì đó là điều kiện về CẤU TRÚC: cửa gác phải được gọi ở cả hai đường.
    """
    import inspect

    trip_service = importlib.import_module("services.tms_trip_service")
    for ham in (trip_service.create_trip_from_delivery_orders, trip_service.add_leg):
        than = inspect.getsource(ham)
        assert "_chan_hang_chieu_ve" in than, (
            "%s chưa gọi cửa gác hàng chiều về" % ham.__name__)


# ----------------------------------------------------------------- 2. xe đang quay về

def _bo_chang(db, models, trip_id, cac_chang):
    for i, (loai, trang_thai) in enumerate(cac_chang, start=1):
        db.add(models.TransportTripLeg(
            id="%s-LEG-%03d" % (trip_id, i), trip_id=trip_id, sequence_no=i,
            leg_type=loai, status=trang_thai, origin="A", destination="B",
            distance_km=10, avg_speed_kmh=40, dwell_minutes=0))


@pytest.fixture
def chuyen_quay_ve(app_client):
    """Ba chiếc xe, ba tình huống: đang giao, đang quay về, đã về tới bãi."""
    client, _, _ = app_client
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    bay_gio = dt.datetime.now(dt.timezone.utc)
    ve_luc = bay_gio + dt.timedelta(hours=3)
    with database.SessionLocal() as db:
        for ma in ("XE-QV-DANGGIAO", "XE-QV-VE", "XE-QV-XONG"):
            db.add(models.Vehicle(id=ma, type="Xe tải 10 tấn", weight_capacity=10000,
                                  operational_status="available",
                                  inspection_exp="2027-12-31", insurance_date="2027-12-31",
                                  maintenance_date="2027-12-31"))
        db.flush()
        db.add(models.Driver(id="TX-QV", name="Tài xế QV", license_type="FC"))
        db.add(models.Location(id="LOC-QV-A", name="A"))
        db.add(models.Location(id="LOC-QV-B", name="B"))
        db.flush()
        bo = [
            # còn chặng giao chưa đóng → CHƯA phải đang quay về
            ("TRIP-QV-1", "XE-QV-DANGGIAO", [("delivery", "planned"), ("empty_return", "planned")]),
            # giao xong, chặng về chưa đi → ĐANG quay về
            ("TRIP-QV-2", "XE-QV-VE", [("delivery", "completed"), ("empty_return", "planned")]),
            # chặng về cũng đã đóng → xe đã tới bãi, không còn "đang quay về"
            ("TRIP-QV-3", "XE-QV-XONG", [("delivery", "completed"), ("empty_return", "completed")]),
        ]
        for trip_id, xe, chang in bo:
            # `transport_trips.freight_order_id` là NOT NULL: một chuyến luôn thực hiện một
            # lệnh vận chuyển, không có chuyến trôi nổi.
            fo = "FO-" + trip_id
            db.add(models.FreightOrder(
                id=fo, pickup_location_id="LOC-QV-A", delivery_location_id="LOC-QV-B",
                pickup_window_start=bay_gio - dt.timedelta(hours=6),
                pickup_window_end=bay_gio - dt.timedelta(hours=4),
                delivery_window_start=bay_gio - dt.timedelta(hours=3),
                delivery_window_end=bay_gio + dt.timedelta(hours=6),
                max_weight_kg=10000, max_volume_m3=30, max_pallet_count=20))
            db.flush()
            db.add(models.TransportTrip(id=trip_id, freight_order_id=fo, status="in_transit",
                                        planned_return_at=ve_luc))
            db.flush()
            _bo_chang(db, models, trip_id, chang)
            db.add(models.ResourceAssignment(
                freight_order_id=fo, trip_id=trip_id, vehicle_id=xe, driver_id="TX-QV",
                status="active",
                assignment_start=bay_gio - dt.timedelta(hours=5),
                assignment_end=bay_gio + dt.timedelta(hours=5)))
        db.commit()
    return client, ve_luc


def test_xe_giao_xong_con_chang_ve_thi_bao_dang_quay_ve(chuyen_quay_ve):
    database = importlib.import_module("database")
    from services.lich_xe import xe_dang_quay_ve

    with database.SessionLocal() as db:
        assert xe_dang_quay_ve(db, "XE-QV-DANGGIAO")[0] is False, "còn hàng trên xe mà đã báo quay về"
        assert xe_dang_quay_ve(db, "XE-QV-XONG")[0] is False, "xe đã về tới bãi thì hết 'đang quay về'"
        quay_ve, ve_luc = xe_dang_quay_ve(db, "XE-QV-VE")
        assert quay_ve is True
        assert ve_luc is not None, "phải trả giờ dự kiến về để người điều độ xếp chuyến kế"
        # Xe không có chuyến nào giữ: trả lời gọn, không nổ.
        assert xe_dang_quay_ve(db, "XE-KHONG-CO") == (False, None)
        assert xe_dang_quay_ve(db, None) == (False, None)


def test_api_vehicles_gan_nhan_ranh_luc_may_gio_va_KHONG_doi_ma_trang_thai(chuyen_quay_ve):
    """Nhãn đổi, MÃ giữ nguyên `on_trip`.

    Đây là điều kiện an toàn của cả việc này: thêm một mã trạng thái mới thì mọi chỗ hỏi
    `== "available"` đều phải rà lại, sót một chỗ là xe đang trên đường về bị coi là rảnh rồi
    bị xếp chồng chuyến. Ở đội ~500 xe đó là lỗi tốn tiền.
    """
    client, _ = chuyen_quay_ve
    r = client.get("/api/vehicles?paginated=true&page_size=200", headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    theo_ma = {x["id"]: x for x in r.json()["items"]}

    ve = theo_ma["XE-QV-VE"]
    assert ve["operational_status"] == "on_trip", "KHÔNG được đẻ thêm mã trạng thái mới"
    assert ve["dang_quay_ve"] is True
    assert ve["san_sang_luc"], "thiếu giờ dự kiến rảnh"
    assert "Đang quay về" in ve["operational_status_label"]
    assert "rảnh lúc" in ve["operational_status_label"], ve["operational_status_label"]

    for ma in ("XE-QV-DANGGIAO", "XE-QV-XONG"):
        assert theo_ma[ma]["dang_quay_ve"] is False
        assert "Đang quay về" not in (theo_ma[ma]["operational_status_label"] or "")


# ----------------------------------------------------------------- 3. công thức ngoại tệ

def test_bao_gia_ngoai_te_lui_ve_cong_thuc_vnd_va_NOI_RA(app_client):
    """Không có công thức USD thì dùng công thức VND, nhưng phải dán nhãn rõ.

    Trả danh sách rỗng như bản trước là màn hình im lặng: người ký nhận thấy "Chưa có khoản
    mục nào từ công thức" mà không hiểu vì sao, và không khai được khoản khách trả thêm.

    Nhưng cũng KHÔNG được lặng lẽ đưa công thức VND vào như thể nó là công thức của báo giá
    USD: màn hình sẽ đặt con số VND cạnh con số USD rồi cộng lại — đúng con bug lãi gộp
    −630.270% đã diệt. Nên `currency_fallback` phải bật, và mỗi dòng giữ tiền của chính nó.
    """
    client, _, _ = app_client
    delivery_routes = importlib.import_module("routes.delivery_routes")

    assert delivery_routes.TIEN_CHUC_NANG == "VND"
    # Hằng số phải ở MỨC MODULE: hàm chọn công thức dự phòng nằm ngoài hàm dựng hồ sơ, hai
    # bản sao của cùng một hằng là hai chỗ để lệch nhau.
    assert "TIEN_CHUC_NANG" in dir(delivery_routes)

    import inspect
    than = inspect.getsource(delivery_routes._cong_thuc_theo_tien_chuc_nang)
    assert "TIEN_CHUC_NANG" in than

    # Chỗ gọi phải bật cờ và nói lý do, chứ không lặng lẽ đổi công thức.
    ho_so = inspect.getsource(delivery_routes)
    for khoa in ("currency_fallback", "fallback_reason", "quote_currency"):
        assert khoa in ho_so, "hồ sơ quyết toán thiếu %s" % khoa


def test_lui_ve_cong_thuc_vnd_phai_chay_TRUOC_cua_chan_cong_thuc():
    """Thứ tự trong hàm là điều kiện sống còn của việc này, không phải chi tiết trình bày.

    ĐÃ HỎNG THẬT một lần. Bản sửa đầu đặt khối lùi-về-công-thức-VND SAU cửa chặn
    `COST_FORMULA_REQUIRED`. Cửa đó chỉ bỏ qua lệnh ĐÃ CHỐT (`con_phai_tinh` là False), nên
    lệnh đang chạy hay đã đến nơi vẫn ăn 409 trước khi chạm tới khối kia. Kết quả đo trên bộ
    dữ liệu demo Lào: màn "Hoàn tất giao hàng" hiện "Chưa tải được giá" ở 10 trong 13 dòng —
    đúng 10 dòng ngoại tệ, chỉ 3 dòng VND còn đọc được giá.

    Bài này đọc mã nguồn vì thứ cần khoá là THỨ TỰ, và một bài chạy thật trên lệnh đã giao
    sẽ xanh kể cả khi thứ tự bị đảo — đó chính là cách lỗi trên lọt qua.
    """
    import inspect

    delivery_routes = importlib.import_module("routes.delivery_routes")
    than = inspect.getsource(delivery_routes.get_delivery_order_closeout)

    vi_tri_lui = than.find("_cong_thuc_theo_tien_chuc_nang")
    # Tìm CHỖ NÉM LỖI, không phải chữ `COST_FORMULA_REQUIRED` nói chung: chính chú thích giải
    # thích bài này cũng nhắc tên mã đó, và tìm theo tên trần sẽ khớp vào câu chú thích rồi
    # kết luận ngược. Đã mắc đúng bẫy ấy một lần.
    vi_tri_chan = than.find('"code": "COST_FORMULA_REQUIRED"')
    assert vi_tri_lui > 0, "hàm dựng hồ sơ quyết toán không còn gọi công thức dự phòng"
    assert vi_tri_chan > 0, "không thấy chỗ ném lỗi COST_FORMULA_REQUIRED"
    assert vi_tri_lui < vi_tri_chan, (
        "khối lùi về công thức VND phải nằm TRƯỚC cửa chặn COST_FORMULA_REQUIRED; "
        "đặt sau thì mọi lệnh ngoại tệ chưa giao xong đều trả 409 và màn Hoàn tất "
        "giao hàng hiện 'Chưa tải được giá'")

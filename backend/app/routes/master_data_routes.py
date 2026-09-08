"""Dữ liệu gốc: khách hàng và tuyến đường.

Tách ra khỏi main.py vì cả 7 endpoint này từng KHÔNG kiểm quyền một dòng nào,
trong khi chúng nuôi trực tiếp phần tính tiền:

- Xóa khách hàng: `curl -X DELETE /api/customers/CUS-001` không cần credential,
  và không có kiểm tra đang-sử-dụng nào — khác với delete_vehicle vốn kiểm rất
  cẩn thận tham chiếu DO/Trip/Tracking.
- POST /api/routes với id đã tồn tại thì ghi đè distance_km và segments_json của
  một tuyến đang chạy, mà hai trường đó nuôi tính ETA và giá cước.

Router mang dependency xác thực ở TẦNG ROUTER nên endpoint thêm vào đây được
bảo vệ mặc định, không phụ thuộc việc người viết có nhớ gọi hàm kiểm tra hay
không — đó chính là cách 95 trên 105 endpoint ghi dữ liệu đã lọt ra ngoài.
"""

import json
from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Customer, DeliveryOrder, Quotation, Route, SalesOrder
from routes.finance_master_routes import require_authenticated_principal
from schemas.workflow import RouteCreateRequest
from services import duong_bo
from services import toa_do_diem


router = APIRouter(dependencies=[Depends(require_authenticated_principal)])


@router.get("/api/customers")
async def list_customers(db: Session = Depends(get_db)):
    return db.query(Customer).all()

@router.post("/api/customers")
async def create_customer(data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    cid = data.get("id")
    if not cid:
        raise HTTPException(status_code=400, detail="Thiếu Mã khách hàng")
    # Ma da ton tai thi noi ro. Truoc day cho nay di thang xuong db.add ->
    # db.commit(), va khoa chinh trung lam SQLAlchemy nem IntegrityError -> 500
    # Internal Server Error. Nguoi dung thay "loi may chu" cho mot viec ho tu
    # sua duoc trong ba giay: doi ma khac.
    if db.get(Customer, cid):
        raise HTTPException(
            status_code=409,
            detail="Mã khách hàng %s đã tồn tại. Hãy dùng mã khác." % cid,
        )
    cus = Customer(
        id=cid,
        name=data.get("name", "Khách hàng Mới"),
        type=data.get("type", "Account"),
        contact_person=data.get("contact_person", ""),
        phone=data.get("phone", ""),
        address=data.get("address", "")
    )
    db.add(cus)
    db.commit()
    db.refresh(cus)
    return {"message": "Tạo khách hàng thành công", "data": cus}

@router.put("/api/customers/{customer_id}")
async def update_customer(customer_id: str, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    cus = db.query(Customer).filter(Customer.id == customer_id).first()
    if not cus:
        raise HTTPException(status_code=404, detail="Không tìm thấy Khách hàng")
    if "name" in data: cus.name = data["name"]
    if "type" in data: cus.type = data["type"]
    if "contact_person" in data: cus.contact_person = data["contact_person"]
    if "phone" in data: cus.phone = data["phone"]
    if "address" in data: cus.address = data["address"]
    db.commit()
    db.refresh(cus)
    return {"message": "Cập nhật khách hàng thành công", "data": cus}

@router.delete("/api/customers/{customer_id}")
async def delete_customer(customer_id: str, db: Session = Depends(get_db)):
    """Xoa mot khach hang khoi Master Data.

    Chu thich o dau tep nay da ghi tu truoc rang cho nay "khong co kiem tra
    dang-su-dung nao — khac voi delete_vehicle von kiem rat can than", nhung
    no van chua duoc sua. Nay sua.

    Ba bang tro vao `customers.id`: bao gia, don van chuyen, lenh giao hang.
    Xoa mot khach dang co chung tu thi hoac vo o tang khoa ngoai (500), hoac
    de lai `customer_id` mo coi — luc do man bao cao doanh thu theo khach
    khong con biet dong tien do thuoc ve ai.
    """
    cus = db.query(Customer).filter(Customer.id == customer_id).first()
    if not cus:
        raise HTTPException(status_code=404, detail="Không tìm thấy Khách hàng")

    dang_dung = {
        "báo giá": db.query(Quotation.id).filter(Quotation.customer_id == customer_id).first(),
        "đơn vận chuyển": db.query(SalesOrder.id).filter(SalesOrder.customer_id == customer_id).first(),
        "lệnh giao hàng": db.query(DeliveryOrder.id).filter(DeliveryOrder.customer_id == customer_id).first(),
    }
    vuong = [ten for ten, co in dang_dung.items() if co]
    if vuong:
        raise HTTPException(status_code=409, detail={
            "code": "LOCKED_RECORD",
            "message": (
                "Khách hàng %s đang có %s, không được xóa."
                " Xóa đi thì báo cáo doanh thu theo khách mất nguồn."
                % (customer_id, ", ".join(vuong))
            ),
            "navigation_targets": ["crm-sales", "operations", "master-data/customers"],
        })

    db.delete(cus)
    db.commit()
    return {"message": f"Đã xóa khách hàng {customer_id}"}

# 5. Routes API
def _tuyen_kem_toa_do(row, db=None, cho_phep_ngoai=False):
    """Mot tuyen, kem toa do cua tung chang.

    VI SAO PHAI GAN O DAY. So do lo trinh cua man Tuyen duong truoc day di hoi
    `nominatim.openstreetmap.org` cho tung diem — mot loi goi ra Internet tu
    trinh duyet nguoi dung. Khong co mang, mang bi chan, hoac bi dich vu do tu
    choi thi ban do TRANG TRON va man hinh chi bao "Khong xac dinh duoc toa do
    tuyen duong". Do duoc tren may that.

    Ma he thong DA BIET toa do cua dung nhung diem do — man "Theo doi va kiem
    soat" ve duoc tuyen bang chinh bang `toa_do_diem`. Hai man noi hai dieu
    trai nguoc ve cung mot tuyen.

    Tra ve mot khoa RIENG `segments_geo` chu khong sua `segments_json` cua ban
    ghi khi ĐỌC. Toa do duoc ghi vao `segments_json` o DUONG LUU (`create_route`)
    — dung mot lan, luc nguoi dung vua go ten diem va con sua duoc; con duong
    doc thi chi bo sung cho nhung tuyen luu tu truoc khi co viec nay.

    Chang nao khong tra duoc toa do thi KHONG co khoa — giao dien phan biet
    "chua biet toa do diem nay" voi mot cap (0, 0), va bao ten diem do ra qua
    `diem_thieu_toa_do`.
    """
    try:
        chang = json.loads(row.segments_json or "[]")
    except (ValueError, TypeError):
        chang = []
    if not isinstance(chang, list):
        chang = []
    # `cho_phep_ngoai=False` khi tra ca danh sach: mot tuyen co ba chang la sau
    # diem, va sau loi goi ra Internet moi lan mo man Du lieu goc thi man do mo
    # mat vai chuc giay. Danh sach dung hai tang trong may; tang thu ba chi chay
    # khi nguoi dung MO dung mot tuyen, hoac khi luu tuyen.
    if db is not None:
        chang_geo, thieu = toa_do_diem.gan_toa_do_cho_chang_db(db, chang, cho_phep_ngoai)
    else:
        chang_geo, thieu = toa_do_diem.gan_toa_do_cho_chang(chang), []
    # Danh sach diem theo THU TU DI. Bo cac chang chua co toa do chu khong dung
    # lai: mot tuyen ba chang ma thieu toa do chang giua thi hai chang con lai
    # van ve duoc, va ve duoc mot phan van hon khong ve gi.
    moc = []
    for c in chang_geo:
        for lat, lng in ((c.get("from_lat"), c.get("from_lng")),
                         (c.get("to_lat"), c.get("to_lng"))):
            if lat is None or lng is None:
                continue
            if not moc or moc[-1] != (lat, lng):
                moc.append((lat, lng))
    hinh = ({"diem": None, "km": None, "nguon": None} if db is None
            else duong_bo.duong_bo_cua_tuyen(db, row, moc, cho_phep_ngoai))
    return {
        "id": row.id,
        "name": row.name,
        "distance_km": row.distance_km,
        # PHI BOT CUA TUYEN. Man Bao gia phai noi duoc "31,2 km · 1 chang · BOT
        # uoc 120.000 d" NGAY khi nguoi dung chon tuyen — truoc khi chon loai
        # xe, nen chua goi duoc bang cau phan gia thanh. BOT thuoc DUONG chu
        # khong thuoc xe, nen no o day moi dung cho.
        "bot_fee": row.bot_fee,
        "segments_json": row.segments_json,
        "segments_geo": chang_geo,
        # HINH DUONG BO THAT. `nguon=None` nghia la khong co — giao dien PHAI
        # noi ra dieu do chu khong duoc ve mot duong thang roi de nguoi xem
        # tuong day la tuyen di.
        "duong_bo": hinh["diem"],
        "km_duong_bo": hinh["km"],
        "nguon_duong_bo": hinh["nguon"],
        # NOI RA diem nao chua biet toa do. Bao "khong ve duoc ban do" ma khong
        # noi diem nao thi nguoi dung khong biet phai sua gi.
        "diem_thieu_toa_do": thieu,
    }


@router.get("/api/routes")
async def list_routes(
    paginated: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Route).order_by(Route.id.asc())
    if not paginated:
        return [_tuyen_kem_toa_do(row, db) for row in query.limit(100).all()]
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [_tuyen_kem_toa_do(row, db) for row in items],
            "total": total, "page": page, "page_size": page_size}

@router.post("/api/routes")
async def create_route(payload: RouteCreateRequest, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_unset=True)
    route_id = data.get("id")
    if not route_id:
        count = db.query(Route).count() + 1
        route_id = f"RT-{count:03d}"
    # XÁC ĐỊNH TOẠ ĐỘ NGAY LÚC LƯU, và ghi vào chính `segments_json`.
    #
    # Đây là chỗ đúng để làm việc đó. Người dùng vừa gõ tên điểm đi và điểm đến,
    # nên nếu có điểm nào hệ thống không biết thì phải nói ra NGAY — lúc họ còn
    # đang ở form và sửa được — chứ không phải để họ mở lại tuyến ba ngày sau và
    # thấy một ô bản đồ trắng không rõ vì sao.
    #
    # Ghi vào dữ liệu tuyến thì mọi lần vẽ sau đó không cần tra lại, kể cả khi
    # máy mất mạng. Toạ độ người dùng đã khai tay không bị ghi đè.
    chang_vao = data.get("segments_json")
    thieu_toa_do = []
    if chang_vao is not None:
        try:
            chang = json.loads(chang_vao) if isinstance(chang_vao, str) else chang_vao
        except (ValueError, TypeError):
            chang = []
        if isinstance(chang, list) and chang and isinstance(chang[0], dict):
            chang_geo, thieu_toa_do = toa_do_diem.gan_toa_do_cho_chang_db(db, chang, True)
            chang_vao = json.dumps(chang_geo, ensure_ascii=False)

    existing = db.query(Route).filter(Route.id == route_id).first()
    if existing:
        existing.name = data.get("name", existing.name or "Tuyến mới")
        existing.distance_km = float(data.get("distance_km") or 0)
        existing.segments_json = chang_vao if chang_vao is not None else (existing.segments_json or "[]")
        route = existing
    else:
        route = Route(
            id=route_id,
            name=data.get("name", "Tuyến mới"),
            distance_km=float(data.get("distance_km") or 0),
            segments_json=chang_vao if chang_vao is not None else "[]"
        )
        db.add(route)
    db.commit()
    db.refresh(route)
    thong_bao = f"Đã lưu tuyến đường {route_id} thành công"
    if thieu_toa_do:
        thong_bao += (". Chưa xác định được toạ độ của: " + ", ".join(thieu_toa_do)
                      + " — sơ đồ lộ trình sẽ thiếu các điểm này cho tới khi khai toạ độ.")
    return {
        "message": thong_bao,
        "data": route,
        "diem_thieu_toa_do": thieu_toa_do,
    }

@router.get("/api/routes/{route_id}/geo")
async def route_geo(route_id: str, db: Session = Depends(get_db)):
    """Mot tuyen kem toa do, CO PHEP tra ra dich vu ngoai.

    Tach khoi `GET /api/routes` vi hai duong nay co gia khac nhau: danh sach
    chay trong may (nhanh, dung cho man Du lieu goc mo len), con duong nay co
    the mat vai giay cho mot dia diem chua ai biet toa do — va nguoi dung dang
    doi mot ban do nen vai giay do la chap nhan duoc.

    Toa do tra duoc se duoc GHI vao bang `locations`, nen lan sau duong danh
    sach cung tra ra ngay ma khong can mang.
    """
    row = db.query(Route).filter(Route.id == route_id).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Khong tim thay tuyen {route_id}")
    ket_qua = _tuyen_kem_toa_do(row, db, cho_phep_ngoai=True)
    db.commit()
    return {"message": "Da xac dinh toa do tuyen duong.", "data": ket_qua}


@router.put("/api/locations/{location_id}/coordinates")
async def set_location_coordinates(
    location_id: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    """Khai TAY toa do cua mot dia diem.

    Day la duong cuoi, va no phai co. Mot dich vu tra toa do ngoai co the khong
    biet mot bai noi bo, hoac tra ve sai cho — va khong co duong nay thi nguoi
    dung khong con cach nao sua ngoai viec sua ma nguon. Toa do khai tay khong
    bao gio bi may ghi de: `gan_toa_do_cho_chang_db` bo qua chang da co toa do.
    """
    from models import Location
    row = db.query(Location).filter(Location.id == location_id).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Khong tim thay dia diem {location_id}")
    la = set(payload) - {"latitude", "longitude"}
    if la:
        raise HTTPException(status_code=422, detail="Truong khong hop le: " + ", ".join(sorted(la)))
    try:
        lat = float(payload.get("latitude"))
        lng = float(payload.get("longitude"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Toa do phai la hai so.")
    # Chan toa do ngoai Viet Nam: mot con so nhap sai dau (106 thanh 10.6) se
    # dat kho ra giua bien, va tren ban do thi khong ai doc ra la do nhap sai.
    a, b, c, d = toa_do_diem.HOP_VIET_NAM
    if not (a <= lat <= b and c <= lng <= d):
        raise HTTPException(
            status_code=422,
            detail=f"Toa do ({lat}, {lng}) nam ngoai Viet Nam. Vi tri hop le: "
                   f"vi do {a}-{b}, kinh do {c}-{d}.",
        )
    row.latitude, row.longitude = lat, lng
    db.commit()
    return {"message": f"Da luu toa do cho {row.name or location_id}",
            "data": {"id": row.id, "name": row.name, "latitude": lat, "longitude": lng}}


@router.get("/api/locations/coordinates")
async def list_location_coordinates(db: Session = Depends(get_db)):
    """Danh sach dia diem kem toa do, va nhung dia diem CON THIEU toa do.

    Man Du lieu goc dung danh sach thieu nay de noi ra viec can lam: mot dia
    diem khong co toa do la mot tuyen khong ve duoc ban do.
    """
    from models import Location
    ds = db.query(Location).order_by(Location.name.asc()).all()
    return {
        "message": "Da tai toa do dia diem.",
        "data": {
            "dia_diem": [
                {"id": x.id, "name": x.name, "type": x.type,
                 "latitude": x.latitude, "longitude": x.longitude}
                for x in ds
            ],
            "thieu_toa_do": [
                {"id": x.id, "name": x.name}
                for x in ds if x.latitude is None or x.longitude is None
            ],
        },
    }


@router.delete("/api/routes/{route_id}")
async def delete_route(route_id: str, db: Session = Depends(get_db)):
    """Xoa mot tuyen duong khoi Master Data.

    Truoc day ham nay KHONG kiem dang-su-dung, khac han `delete_vehicle` va
    `delete_driver`. Ba bang tro vao `routes.id`: bao gia, don van chuyen va
    lenh giao hang. Xoa mot tuyen dang duoc tham chieu thi hoac vo o tang
    khoa ngoai (500 Internal Server Error, nguoi dung khong sua duoc gi),
    hoac de lai `route_id` mo coi — va `distance_km` cua tuyen chinh la thu
    nuoi phep tinh gia cuoc lan ETA, nen mat no la moi con so tien tren
    nhung don do mat nguon ma khong mot loi bao nao.
    """
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tuyến đường {route_id}")

    dang_dung = {
        "báo giá": db.query(Quotation.id).filter(Quotation.route_id == route_id).first(),
        "đơn vận chuyển": db.query(SalesOrder.id).filter(SalesOrder.route_id == route_id).first(),
        "lệnh giao hàng": db.query(DeliveryOrder.id).filter(DeliveryOrder.route_id == route_id).first(),
    }
    vuong = [ten for ten, co in dang_dung.items() if co]
    if vuong:
        raise HTTPException(status_code=409, detail={
            "code": "LOCKED_RECORD",
            "message": (
                "Tuyến %s đang được %s tham chiếu, không được xóa."
                " Quãng đường của tuyến nuôi phép tính giá cước và ETA của"
                " những chứng từ đó." % (route_id, ", ".join(vuong))
            ),
            "navigation_targets": ["crm-sales", "operations", "master-data/routes"],
        })

    db.delete(route)
    db.commit()
    return {"message": f"Đã xóa tuyến đường {route_id} thành công"}

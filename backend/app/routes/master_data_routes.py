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

from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Customer, DeliveryOrder, Quotation, Route, SalesOrder
from routes.finance_master_routes import require_authenticated_principal
from schemas.workflow import RouteCreateRequest


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
@router.get("/api/routes")
async def list_routes(
    paginated: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Route).order_by(Route.id.asc())
    if not paginated:
        return query.limit(100).all()
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}

@router.post("/api/routes")
async def create_route(payload: RouteCreateRequest, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_unset=True)
    route_id = data.get("id")
    if not route_id:
        count = db.query(Route).count() + 1
        route_id = f"RT-{count:03d}"
    existing = db.query(Route).filter(Route.id == route_id).first()
    if existing:
        existing.name = data.get("name", existing.name or "Tuyến mới")
        existing.distance_km = float(data.get("distance_km") or 0)
        existing.segments_json = data.get("segments_json", existing.segments_json or "[]")
        route = existing
    else:
        route = Route(
            id=route_id,
            name=data.get("name", "Tuyến mới"),
            distance_km=float(data.get("distance_km") or 0),
            segments_json=data.get("segments_json", "[]")
        )
        db.add(route)
    db.commit()
    db.refresh(route)
    return {"message": f"Đã lưu tuyến đường {route_id} thành công", "data": route}

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

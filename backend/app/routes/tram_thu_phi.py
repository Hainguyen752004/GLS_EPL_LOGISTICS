# -*- coding: utf-8 -*-
"""Trạm thu phí — ດ່ານເກັບຄ່າທາງ (16/10). Danh mục trạm (giá một lượt cho xe EPL) + tìm trạm dọc đường xe đi của một tuyến.

Ai sửa: Bãi, kế toán (như tuyến đường) và KT Chi phí — người kiểm mục IV. Bãi KHÔNG thấy và không đặt GIÁ (anh Khampla A2): giá Bãi gửi
lên bị bỏ, giá đang có giữ nguyên. Luật tính lượt, dòng phiếu: services/tram_thu_phi.py.
"""
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import RouteToll, TollStation, TripExpense
from services import tram_thu_phi as TP
from services.bao_mat import can_vai, nguoi_hien_tai
from services.phan_quyen import thay_tien_chi

router = APIRouter()
SUA = can_vai("yard", "acct", "expacct")       # KT Chi phí kiểm mục IV — giá trạm là việc của họ


def _so_tuyen(db):
    return dict(db.query(RouteToll.station_id, func.count(RouteToll.id)).group_by(RouteToll.station_id).all())


def _toa_do(v, nho, lon, ten):
    if v in (None, ""):
        return None
    try:
        x = float(str(v).replace(",", ""))
    except ValueError:
        raise HTTPException(422, {"ma": "TOA_DO_SAI", "loi": "%s phải là số." % ten})
    if not (nho <= x <= lon):
        raise HTTPException(422, {"ma": "TOA_DO_SAI", "loi": "%s phải từ %s đến %s." % (ten, nho, lon)})
    return x


def _ghi(db, st, data, user):
    if "name" in data:
        ten = str(data.get("name") or "").strip()
        if not ten:
            raise HTTPException(422, {"ma": "THIEU_TEN", "loi": "Trạm thu phí phải có tên."})
        st.name = ten[:200]
    if "country" in data:
        nuoc = str(data.get("country") or "").upper()
        if nuoc not in TP.NUOC:
            raise HTTPException(422, {"ma": "NUOC_SAI", "loi": "Nước của trạm phải là LA, VN hoặc TH."})
        st.country = nuoc
    if "lat" in data:
        st.lat = _toa_do(data.get("lat"), -90, 90, "Vĩ độ")
    if "lng" in data:
        st.lng = _toa_do(data.get("lng"), -180, 180, "Kinh độ")
    if "one_way" in data:
        st.one_way = bool(data.get("one_way"))
    if "note" in data:
        st.note = (str(data.get("note") or "").strip() or None)
    if "active" in data:
        st.active = bool(data.get("active"))
    if data.get("osm_ref"):                                   # trạm thêm từ gợi ý «gần đường» — nhớ điểm OSM, lần dò sau khỏi thêm trùng
        st.osm_ref = str(data["osm_ref"])[:500]
    # giá và tiền tệ: chỉ vai được thấy tiền chi (Bãi gửi lên thì bỏ, giữ giá kế toán đã đặt)
    if thay_tien_chi(user.role):
        if "currency" in data:
            tt = str(data.get("currency") or "").upper()
            if tt not in ("LAK", "VND", "THB", "USD", "CNY"):
                raise HTTPException(422, {"ma": "TIEN_TE_SAI", "loi": "Tiền tệ của trạm phải là LAK, VND, THB, USD hoặc CNY."})
            st.currency = tt
        if "fee" in data:
            v = data.get("fee")
            if v in (None, ""):
                st.fee = None
            else:
                try:
                    g = float(str(v).replace(",", ""))
                except ValueError:
                    raise HTTPException(422, {"ma": "SO_SAI", "loi": "Giá qua trạm phải là số."})
                if g < 0:
                    raise HTTPException(422, {"ma": "SO_AM", "loi": "Giá qua trạm không được âm."})
                st.fee = g
    if not st.currency:
        st.currency = TP.TIEN_TE_NUOC.get(st.country or "LA", "LAK")


@router.get("/api/toll-stations")
def ds(db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    dem, thay = _so_tuyen(db), thay_tien_chi(user.role)
    return [TP.xuat_tram(s, thay, dem.get(s.id, 0))
            for s in db.query(TollStation).order_by(TollStation.active.desc(), TollStation.country, TollStation.name).all()]


@router.post("/api/toll-stations")
def them(data: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA)):
    st = TollStation(name="", country=str(data.get("country") or "LA").upper(), active=True, one_way=False)
    _ghi(db, st, {"name": data.get("name"), **data}, user)
    db.add(st); db.commit()
    return TP.xuat_tram(st, thay_tien_chi(user.role), 0)


@router.put("/api/toll-stations/{sid}")
def sua(sid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA)):
    st = db.get(TollStation, sid)
    if not st:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có trạm thu phí này."})
    _ghi(db, st, data, user)
    db.commit()
    return TP.xuat_tram(st, thay_tien_chi(user.role), _so_tuyen(db).get(st.id, 0))


@router.delete("/api/toll-stations/{sid}")
def xoa(sid: str, db: Session = Depends(get_db), user=Depends(SUA)):
    """Xoá trạm thêm nhầm. Chỉ xoá được trạm CHƯA tuyến nào gắn và CHƯA dòng phiếu nào mang — đang dùng thì ngưng dùng thay vì xoá
    (phiếu cũ còn tra được trạm)."""
    st = db.get(TollStation, sid)
    if not st:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có trạm thu phí này."})
    if db.query(RouteToll).filter(RouteToll.station_id == sid).count() or \
            db.query(TripExpense).filter(TripExpense.toll_station_id == sid).count():
        raise HTTPException(409, {"ma": "TRAM_DANG_DUNG", "loi": "Trạm đang gắn với tuyến hoặc đã có trên phiếu — chỉ ngưng dùng được, không xoá."})
    db.delete(st); db.commit()
    return {"ok": True}


@router.post("/api/toll-stations/doc-tuyen")
def doc_tuyen(data: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA)):
    """Tìm trạm trên đường xe đi. Thân: `duong` = [[lat, lng], …] (đường xe tải màn Tuyến đường đã vẽ, theo chiều đi), `ten_tuyen`.
    Dò cả trạm trong danh mục lẫn trạm OSM đóng gói; trạm OSM chưa có trong danh mục thì THÊM vào danh mục (chưa có giá).
    → {"tren": [{…trạm, km}] theo thứ tự xe đi qua, "gan": [{ref | id, name, lat, lng, country, km, cach_m}] — trạm cách đường ≤ 1,5 km,
    CHƯA thêm vào tuyến / danh mục: máy chỉ đường có khi chọn đường tắt khác đường xe hay chạy, người dùng tự quyết}."""
    duong = data.get("duong")
    if not isinstance(duong, list) or len(duong) < 2:
        raise HTTPException(422, {"ma": "THIEU_DUONG", "loi": "Chưa có đường xe đi để dò trạm — chấm vị trí ít nhất hai điểm của tuyến."})
    if len(duong) > 60000:
        raise HTTPException(422, {"ma": "DUONG_QUA_DAI", "loi": "Đường gửi lên quá dài để dò trạm."})
    # trạm đã có trong danh mục (kể cả người dùng tự chấm) + trạm OSM — trạm OSM trùng trạm đã có thì ghep() gộp lại
    co = [{"ref": s.osm_ref, "name": s.name, "lat": s.lat, "lng": s.lng, "country": s.country, "_id": s.id}
          for s in db.query(TollStation).filter(TollStation.active.is_(True)).all() if s.lat is not None]
    tat = TP.doc_tuyen(duong, co + TP.ds_osm(), TP.GAN_M)
    tren = [x for x in tat if x[2] <= TP.NGUONG_M]
    ket = TP.ghep(db, tren, str(data.get("ten_tuyen") or "").strip()[:60])
    db.commit()
    dem, thay = _so_tuyen(db), thay_tien_chi(user.role)
    da = {st.id for st, _ in ket}
    da_ref = set().union(*[TP._ref(st.osm_ref) for st, _ in ket]) if ket else set()
    gan, thay_gan = [], set()
    for u, km, d in tat:
        if d <= TP.NGUONG_M or (u.get("_id") and u["_id"] in da) or (TP._ref(u.get("ref")) & da_ref):
            continue
        khoa = u.get("_id") or u.get("ref")
        if khoa in thay_gan:
            continue
        thay_gan.add(khoa)
        gan.append({"id": u.get("_id"), "ref": u.get("ref"), "name": u.get("name"), "lat": u["lat"], "lng": u["lng"],
                    "country": u.get("country") or "LA", "km": round(km, 1), "cach_m": round(d)})
    return {"tren": [dict(TP.xuat_tram(st, thay, dem.get(st.id, 0)), km=round(km, 1)) for st, km in ket], "gan": gan[:30]}

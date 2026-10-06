# -*- coding: utf-8 -*-
"""Thử 06/10 — tài xế & tất toán (chủ dự án chốt: "KT Chi phí chỉnh chi thật mục IV", "làm hàng đợi mất mạng luôn") trên bản
sao _d7. MỌI THỨ trong một giao dịch ngoài (phiên chạy savepoint), cuối ROLLBACK: không ghi gì vào d7. Gọi qua FastAPI TestClient
bằng phiên đăng nhập thật của người dùng có sẵn trong d7, không chạy sự kiện khởi động, KHÔNG gọi mạng (urlopen bị chặn và đếm —
lời gọi hệ kế toán anh Tune thành lỗi mạng, đúng đường "gửi hỏng, ghi lỗi lên bản ghi").

    python kiem/thu_tai_xe_tat_toan.py

DO thử lập mới trong giao dịch (Sếp lập, xe nhà, tài xế của tx01; dòng chi / trạng thái mục đặt thẳng trong giao dịch):
  G7  vị trí GPS: điểm sống mang giờ máy · giờ tương lai → giờ máy chủ · gửi bù theo lô (giờ máy, gửi lại không trùng, điểm dày /
      giờ vô lý / toạ độ sai bị bỏ có đếm, quá 500 điểm → 422) · phiếu đã tới nhận điểm trước lúc tới · quyền.
      thao tác hàng đợi: Xuất phát / báo hỏng / khai dầu mang ma_gui + luc → ghi theo giờ máy, gửi lại không trùng, xuất phát gửi
      muộn không kéo phiếu đã tới về; báo hỏng giờ thật trước lúc tới vẫn nhận; giờ máy tương lai vẫn nhận (giờ máy chủ).
  G5  kiểm lại / khoá DO: khai báo tài xế chưa duyệt → cảnh báo KHAI_BAO_CHO_DUYET liệt kê từng lần, không lộ tiền; khoá không xác
      nhận → 409 CO_CANH_BAO; duyệt / từ chối xong thì hết cảnh báo.
  G11 ghi sổ mục III chỉ lấy kho → tự "đã chi" (nhật ký pay_auto); có dòng mua tiền mặt / ghi nợ trạm → vẫn chờ thủ quỹ chi; dọn tồn
      (chỉ Sếp, gọi lại không đổi gì).
  G4  chốt tất toán còn DO chưa khoá · khai báo chưa duyệt · dòng tiền mặt giá 0 → 409 CHUA_DU_DE_CHOT liệt kê từng DO (ba tiếng),
      xem trước (chan_chot) cùng kết quả; sửa xong thì chốt được; bỏ chốt khi phiếu chênh đã ghi sổ / QT_TU đã gửi → 409 nói vì sao.
  G6  chi thật mục IV: chỉ KT Chi phí / Sếp · chỉ khi mục IV đã chi · chỉ dòng tiền mặt xe nhà · số âm 422 · nhật ký cũ → mới · tờ
      tạm ứng và chứng từ tạm ứng không đổi · số "đã chi thật" của tất toán theo số mới · kỳ đã chốt → khoá.
"""
import datetime as dt
import os
import sys
import urllib.request

GOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
URL = open(os.path.join(GOC, ".may_thu", "url_epl_lao_d7.txt"), encoding="utf-8").read().strip()
if "_d7" not in URL.rsplit("/", 1)[-1]:
    sys.exit("Chuỗi nối không trỏ bản sao _d7 — bài chỉ chạy trên bản sao.")
os.environ["DATABASE_URL"] = URL
os.environ["KHO_NGUON"] = "qlsx"
for k in ("QLSX_WEB_URL", "QLSX_GUI_BUT_TOAN", "EPL_CHI_TAM_UNG"):
    os.environ.pop(k, None)
sys.path.insert(0, os.path.join(GOC, "backend", "app"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

MANG = []


def _cam_mang(yc, *a, **k):
    MANG.append(getattr(yc, "full_url", str(yc)))
    raise OSError("bài thử chặn mạng")


urllib.request.urlopen = _cam_mang

from fastapi.testclient import TestClient               # noqa: E402
from sqlalchemy import create_engine, text              # noqa: E402
from sqlalchemy.orm import Session                      # noqa: E402

import models as M                                      # noqa: E402
from database import get_db                             # noqa: E402
from main import app                                    # noqa: E402
from routes import vi_tri as VT                         # noqa: E402
from services import goi_ke_toan as KT                  # noqa: E402
from services.bao_mat import ky_phien                   # noqa: E402
from services.phan_quyen import viec_dang_cho           # noqa: E402

KQ = []


def dung(dk, ten, ct=""):
    KQ.append(bool(dk))
    print(("  ✓ " if dk else "  SAI ") + ten + ((" — " + str(ct)[:300]) if ct != "" else ""))


def _cam_kho_tam(*a, **k):
    raise AssertionError("KHO_NGUON=qlsx mà vẫn gọi kho tạm")


KT.goi = _cam_kho_tam


def ma(r):
    try:
        d = r.json().get("detail")
    except ValueError:
        return None
    return d.get("ma") if isinstance(d, dict) else d


def ct(r):
    try:
        return r.json().get("detail")
    except ValueError:
        return r.text[:200]


def iso(t):
    """datetime UTC không múi → chuỗi kiểu toISOString của điện thoại (phần nghìn giây, Z)."""
    return t.strftime("%Y-%m-%dT%H:%M:%S.") + "%03dZ" % (t.microsecond // 1000)


def main():
    eng = create_engine(URL, connect_args={"options": "-c timezone=UTC"})
    conn = eng.connect()
    ngoai = conn.begin()
    conn.execute(text("SET LOCAL lock_timeout = '10s'"))   # máy thử chạy song song: chờ khoá quá 10 giây thì hỏng, không treo
    for t in ("gui_so_nhien_lieu_tune", "can_tru_tune", "dieu_chinh_hang"):
        if t in M.Base.metadata.tables:
            M.Base.metadata.tables[t].create(bind=conn, checkfirst=True)
    db = Session(bind=conn, join_transaction_mode="create_savepoint", autoflush=False)

    def _db():
        try:
            yield db
        finally:
            db.rollback()
    app.dependency_overrides[get_db] = _db
    c = TestClient(app, raise_server_exceptions=False)
    try:
        H = {}
        for u in ("thabok", "ketoan", "ketoancp", "khonl", "quyvc", "admin", "tx01", "tx02"):
            x = db.query(M.User).filter(M.User.username == u).first()
            assert x is not None, "d7 thiếu người dùng %s" % u
            H[u] = {"Authorization": "Bearer " + ky_phien(u)}
        tx01 = db.query(M.User).filter(M.User.username == "tx01").one()
        tai_xe = db.get(M.Driver, tx01.driver_id)
        assert tai_xe is not None, "tx01 chưa gắn tài xế"
        xe = db.query(M.Vehicle).filter(M.Vehicle.owner_type == "EPL", M.Vehicle.active.is_(True)).order_by(M.Vehicle.truck_no).all()
        kh = db.query(M.Customer).order_by(M.Customer.id).first()
        kho = db.query(M.FuelPlace).filter(M.FuelPlace.owner_type == "epl").first()
        tram = db.query(M.FuelPlace).filter(M.FuelPlace.owner_type != "epl").first()
        assert len(xe) >= 2 and kh is not None and kho is not None and tram is not None, "d7 thiếu xe / khách / kho / trạm"
        bay_gio = dt.datetime.utcnow()

        def lap(i, ngay, kind="giao", **them):
            d = {"kind": kind, "vehicle_id": xe[i % len(xe)].id, "driver_id": tai_xe.id, "customer_id": kh.id,
                 "doc_date": ngay.isoformat(), "out_date": ngay.isoformat(), "goods_type": "iron_ore", "weight_origin": 30}
            d.update(them)
            r = c.post("/api/trips", json=d, headers=H["admin"])
            assert r.status_code == 200, ("lập DO thử", r.status_code, ct(r))
            return db.get(M.Trip, r.json()["id"])

        def dong(p, sec, i, **k):
            e = M.TripExpense(trip_id=p.id, section=sec, line_no=i, qty=k.pop("qty", 1), unit_price=k.pop("unit_price", 0),
                              currency=k.pop("currency", "LAK"), paid_by_epl=k.pop("paid_by_epl", True), **k)
            db.add(e); db.flush()
            return e

        def muc(p, **tt):
            for s in db.query(M.TripSection).filter(M.TripSection.trip_id == p.id, M.TripSection.section.in_(list(tt))):
                s.status = tt[s.section]
            db.commit()

        def tt_muc(p, m):
            db.expire_all()
            return db.query(M.TripSection.status).filter(M.TripSection.trip_id == p.id, M.TripSection.section == m).scalar()

        hom_nay = dt.date.today()
        # ============================================================ G7 — GPS gửi bù có giờ máy
        print("== G7a. Vị trí GPS: giờ máy, gửi bù theo lô, không trùng")
        T1 = lap(0, hom_nay)
        T1.transport_status = "transit"; db.commit()
        u1 = "/api/trips/%s/vi-tri" % T1.id
        t_song = bay_gio - dt.timedelta(seconds=40)
        r = c.post(u1, json={"lat": 18.1, "lng": 103.1, "ts": iso(t_song)}, headers=H["tx01"])
        v = db.query(M.VehiclePosition).filter(M.VehiclePosition.trip_id == T1.id).order_by(M.VehiclePosition.ts.desc()).first()
        dung(r.status_code == 200 and r.json()["ghi"] and v is not None and abs((v.ts - t_song).total_seconds()) < 0.002,
             "điểm sống mang giờ máy → ghi đúng giờ máy (không phải giờ máy chủ)", (r.status_code, v and v.ts, t_song))
        r = c.post(u1, json={"lat": 18.2, "lng": 103.2, "ts": iso(bay_gio + dt.timedelta(hours=2))}, headers=H["tx01"])
        v = db.query(M.VehiclePosition).filter(M.VehiclePosition.trip_id == T1.id).order_by(M.VehiclePosition.ts.desc()).first()
        dung(r.status_code == 200 and r.json()["ghi"] and v.ts < bay_gio + dt.timedelta(minutes=5),
             "giờ máy ở tương lai 2 giờ → ghi theo giờ máy chủ", (r.status_code, v.ts))
        lo = "/api/trips/%s/vi-tri/lo" % T1.id
        goc = bay_gio - dt.timedelta(hours=3)
        diem = [{"lat": 18.0 + i / 100, "lng": 103.0 + i / 100, "ts": iso(goc + dt.timedelta(seconds=30 * i)), "speed_kmh": 40 + i}
                for i in range(5)]
        r = c.post(lo, json={"diem": diem}, headers=H["tx01"])
        dung(r.status_code == 200 and r.json() == {"nhan": 5, "ghi": 5, "bo": {}}, "gửi bù 5 điểm mất sóng 3 giờ trước → ghi 5", r.json())
        ts = sorted(t for (t,) in db.query(M.VehiclePosition.ts).filter(M.VehiclePosition.trip_id == T1.id,
                                                                       M.VehiclePosition.ts < bay_gio - dt.timedelta(hours=1)))
        dung(len(ts) == 5 and all(abs((ts[i] - (goc + dt.timedelta(seconds=30 * i))).total_seconds()) < 0.002 for i in range(5)),
             "mỗi điểm mang đúng giờ máy lúc lấy (không dồn về lúc gửi)", ts[:2])
        r = c.post(lo, json={"diem": diem}, headers=H["tx01"])
        dung(r.status_code == 200 and r.json()["ghi"] == 0 and r.json()["bo"] == {"trung": 5},
             "gửi lại đúng lô đó (mất phản hồi) → không ghi trùng", r.json())
        xau = [{"lat": 18.5, "lng": 103.5, "ts": iso(goc + dt.timedelta(seconds=10))},                    # cách điểm đã có 10 giây
               {"lat": 18.5, "lng": 103.5, "ts": iso(bay_gio + dt.timedelta(hours=1))},                   # tương lai
               {"lat": 18.5, "lng": 103.5, "ts": iso(bay_gio - dt.timedelta(days=8))},                    # quá 7 ngày
               {"lat": 18.5, "lng": 103.5},                                                              # không giờ
               {"lat": 999, "lng": 103.5, "ts": iso(goc + dt.timedelta(minutes=10))},                     # toạ độ sai
               {"lat": 18.6, "lng": 103.6, "ts": iso(goc + dt.timedelta(minutes=20))}]                    # tốt
        r = c.post(lo, json={"diem": xau}, headers=H["tx01"])
        dung(r.status_code == 200 and r.json() == {"nhan": 6, "ghi": 1, "bo": {"qua_day": 1, "gio_sai": 3, "toa_do_sai": 1}},
             "lô lẫn điểm xấu: bỏ có đếm (quá dày, giờ vô lý, toạ độ sai), điểm tốt vẫn ghi", r.json())
        moi = VT.vi_tri_moi_nhat(db, [T1.id])[T1.id]
        dung(moi.ts > bay_gio - dt.timedelta(minutes=5), "điểm gửi bù (cũ) không thành 'vị trí mới nhất' trên bản đồ", moi.ts)
        r = c.post(lo, json={"diem": diem}, headers=H["tx02"])
        dung(r.status_code == 403, "tài xế khác gửi bù → 403", r.status_code)
        r = c.post(lo, json={"diem": diem}, headers=H["ketoan"])
        dung(r.status_code == 403, "kế toán gửi bù → 403", r.status_code)
        r = c.post(lo, json={"diem": [diem[0]] * 501}, headers=H["tx01"])
        dung(r.status_code == 422 and ma(r) == "LO_QUA_LON", "lô 501 điểm → 422 LO_QUA_LON", ma(r))
        r = c.post(lo, json={"diem": "x"}, headers=H["tx01"])
        dung(r.status_code == 422 and ma(r) == "THIEU_DIEM", "không có danh sách điểm → 422", ma(r))
        # phiếu đã tới: điểm trước lúc tới vẫn là vệt của chuyến; sau lúc tới thì bỏ; điểm sống bị chặn như cũ
        T1.transport_status = "arrived"
        db.add(M.TripLog(trip_id=T1.id, user_name="Thử", role="yard", action="st_arrived", ts=bay_gio - dt.timedelta(minutes=10)))
        db.commit()
        r = c.post(lo, json={"diem": [{"lat": 18.7, "lng": 103.7, "ts": iso(bay_gio - dt.timedelta(minutes=30))},
                                      {"lat": 18.8, "lng": 103.8, "ts": iso(bay_gio - dt.timedelta(minutes=2))}]}, headers=H["tx01"])
        dung(r.status_code == 200 and r.json() == {"nhan": 2, "ghi": 1, "bo": {"sau_khi_toi": 1}},
             "phiếu đã tới: điểm trước lúc tới ghi, sau lúc tới bỏ", r.json())
        r = c.post(u1, json={"lat": 18.9, "lng": 103.9}, headers=H["tx01"])
        dung(r.status_code == 409 and ma(r) == "PHIEU_DA_TOI", "điểm sống cho phiếu đã tới → 409 như cũ", ma(r))

        # ============================================================ G7 — thao tác chờ gửi (ma_gui + luc)
        print("== G7b. Xuất phát / báo hỏng / khai dầu từ hàng đợi mất mạng")
        T2 = lap(1, hom_nay)
        luc_di = bay_gio - dt.timedelta(hours=2)
        dd = {"status": "transit", "ma_gui": "g-di-1", "luc": iso(luc_di)}
        r = c.post("/api/trips/%s/transport-status" % T2.id, json=dd, headers=H["tx01"])
        db.expire_all()
        nk = db.query(M.TripLog).filter(M.TripLog.trip_id == T2.id, M.TripLog.action == "st_transit").all()
        dung(r.status_code == 200 and db.get(M.Trip, T2.id).transport_status == "transit" and len(nk) == 1
             and abs((nk[0].ts - luc_di).total_seconds()) < 0.002, "xuất phát gửi muộn → đang chạy, nhật ký theo giờ bấm thật",
             (r.status_code, ct(r) if r.status_code != 200 else [x.ts for x in nk]))
        r = c.post("/api/trips/%s/transport-status" % T2.id, json=dd, headers=H["tx01"])
        dung(r.status_code == 200 and db.query(M.TripLog).filter(M.TripLog.trip_id == T2.id, M.TripLog.action == "st_transit").count() == 1,
             "gửi lại xuất phát → không ghi thêm", r.status_code)
        luc_h = bay_gio - dt.timedelta(minutes=90)
        bh = {"incident_type": "tire", "note": "Nổ lốp sau", "reported_cost": 300000, "currency": "LAK", "paid_by_driver": True,
              "can_run": True, "ma_gui": "g-bh-1", "luc": iso(luc_h)}
        r = c.post("/api/trips/%s/bao-hong" % T2.id, json=bh, headers=H["tx01"])
        r2 = c.post("/api/trips/%s/bao-hong" % T2.id, json=bh, headers=H["tx01"])
        ev = db.query(M.TripEvent).filter(M.TripEvent.trip_id == T2.id, M.TripEvent.kind == "incident").all()
        dung(r.status_code == 200 and r2.status_code == 200 and len(ev) == 1 and abs((ev[0].ts - luc_h).total_seconds()) < 0.002,
             "báo hỏng: giờ = giờ máy lúc báo; gửi lại → vẫn một lần báo", (r.status_code, r2.status_code, len(ev)))
        r = c.post("/api/trips/%s/bao-hong" % T2.id, json=dict(bh, ma_gui="g-bh-2", luc=iso(luc_h + dt.timedelta(minutes=5)),
                                                                note="Nổ lốp trước"), headers=H["tx01"])
        dung(r.status_code == 200 and db.query(M.TripEvent).filter(M.TripEvent.trip_id == T2.id, M.TripEvent.kind == "incident").count() == 2,
             "lần báo khác (giờ khác) → thêm một lần", r.status_code)
        kd = {"qty_l": 120, "place_id": tram.id, "currency": "VND", "note": "đổ ở VN", "ma_gui": "g-kd-1",
              "luc": iso(bay_gio - dt.timedelta(minutes=60))}
        r = c.post("/api/trips/%s/bao-nhien-lieu" % T2.id, json=kd, headers=H["tx01"])
        r2 = c.post("/api/trips/%s/bao-nhien-lieu" % T2.id, json=kd, headers=H["tx01"])
        ev = db.query(M.TripEvent).filter(M.TripEvent.trip_id == T2.id, M.TripEvent.kind == "refuel").all()
        dung(r.status_code == 200 and r2.status_code == 200 and len(ev) == 1 and ev[0].qty_l == 120
             and abs((ev[0].ts - (bay_gio - dt.timedelta(minutes=60))).total_seconds()) < 0.002,
             "khai đổ dầu: giờ máy; gửi lại → không trùng", (r.status_code, r2.status_code, len(ev)))
        r = c.post("/api/trips/%s/bao-nhien-lieu" % T2.id, json=dict(kd, ma_gui="g-kd-2", luc=iso(bay_gio + dt.timedelta(hours=3))),
                   headers=H["tx01"])
        ev = db.query(M.TripEvent).filter(M.TripEvent.trip_id == T2.id, M.TripEvent.kind == "refuel").order_by(M.TripEvent.ts.desc()).all()
        dung(r.status_code == 200 and len(ev) == 2 and ev[0].ts < bay_gio + dt.timedelta(minutes=5),
             "đồng hồ máy chạy nhanh 3 giờ → vẫn nhận (giờ máy chủ), không mất lần khai", (r.status_code, ev[0].ts if ev else None))
        # xe được ghi tới nơi; lần báo giờ thật TRƯỚC lúc tới vẫn nhận, sau thì không; xuất phát gửi muộn không kéo phiếu về
        T2.transport_status = "arrived"
        db.add(M.TripLog(trip_id=T2.id, user_name="Thử", role="yard", action="st_arrived", ts=bay_gio - dt.timedelta(minutes=20)))
        db.commit()
        r = c.post("/api/trips/%s/bao-hong" % T2.id, json=dict(bh, ma_gui="g-bh-3", luc=iso(bay_gio - dt.timedelta(minutes=40)),
                                                                note="Kẹt đường", incident_type="delay"), headers=H["tx01"])
        dung(r.status_code == 200, "báo hỏng gửi muộn, giờ thật trước lúc xe tới → nhận", (r.status_code, ma(r)))
        r = c.post("/api/trips/%s/bao-hong" % T2.id, json=dict(bh, ma_gui="g-bh-4", luc=iso(bay_gio - dt.timedelta(minutes=5))),
                   headers=H["tx01"])
        dung(r.status_code == 409 and ma(r) == "PHIEU_DA_XONG", "giờ thật sau lúc xe tới → 409 PHIEU_DA_XONG", ma(r))
        r = c.post("/api/trips/%s/bao-hong" % T2.id, json={"incident_type": "other", "note": "x"}, headers=H["tx01"])
        dung(r.status_code == 409 and ma(r) == "PHIEU_DA_XONG", "báo thường (không hàng đợi) cho phiếu đã tới → 409 như cũ", ma(r))
        r = c.post("/api/trips/%s/transport-status" % T2.id, json=dict(dd, ma_gui="g-di-2"), headers=H["tx01"])
        db.expire_all()
        dung(r.status_code == 200 and db.get(M.Trip, T2.id).transport_status == "arrived",
             "xuất phát gửi muộn sau khi xe đã tới → trả nguyên, phiếu vẫn 'đã tới'", (r.status_code, db.get(M.Trip, T2.id).transport_status))

        # ============================================================ G5 — khoá DO cảnh báo khai báo chưa duyệt
        print("== G5. Khoá DO: khai báo tài xế chưa duyệt")
        r = c.get("/api/trips/%s/kiem-lai" % T2.id, headers=H["ketoan"])
        cb = [x for x in r.json().get("canh_bao", []) if x["ma"] == "KHAI_BAO_CHO_DUYET"]
        dung(r.status_code == 200 and len(cb) == 1 and cb[0]["so"] == 5 and cb[0]["loi"].count("khai đổ dầu") == 2
             and cb[0]["loi"].count("báo sự cố") == 3 and cb[0].get("loi_lo") and cb[0].get("loi_en"),
             "kiểm lại: một cảnh báo liệt kê 5 khai báo chưa duyệt (2 khai dầu, 3 sự cố), đủ ba tiếng", cb[0]["loi"] if cb else r.json())
        dung(cb and "300" not in cb[0]["loi"] and "LAK" not in cb[0]["loi"], "câu cảnh báo không mang số tiền (Bãi cũng xem kiểm lại)")
        r = c.post("/api/trips/%s/khoa" % T2.id, json={}, headers=H["ketoan"])
        dung(r.status_code == 409 and ma(r) == "CO_CANH_BAO" and any(x["ma"] == "KHAI_BAO_CHO_DUYET" for x in ct(r).get("canh_bao", [])),
             "khoá không xác nhận → 409 CO_CANH_BAO kèm khai báo chờ duyệt", ma(r))
        for e in db.query(M.TripEvent).filter(M.TripEvent.trip_id == T2.id, M.TripEvent.status == "reported").all():
            e.status = "rejected"
        db.commit()
        r = c.get("/api/trips/%s/kiem-lai" % T2.id, headers=H["thabok"])
        dung(r.status_code == 200 and not any(x["ma"] == "KHAI_BAO_CHO_DUYET" for x in r.json()["canh_bao"]),
             "duyệt / từ chối hết → hết cảnh báo", [x["ma"] for x in r.json()["canh_bao"]])

        # ============================================================ G11 — mục III chỉ lấy kho tự qua bước Chi
        print("== G11. Ghi sổ mục III chỉ lấy kho → tự đã chi")
        T3 = lap(0, hom_nay)
        dong(T3, "fuel", 1, qty=100, unit_price=26500, source="kho", place_id=kho.id, stock_move_id="qlsx:THU-0610-1")
        muc(T3, fuel="verified")
        r = c.post("/api/trips/%s/sections/fuel/book" % T3.id, headers=H["khonl"])
        nk = [a for (a,) in db.query(M.TripLog.action).filter(M.TripLog.trip_id == T3.id, M.TripLog.action.like("sec_fuel:%"))]
        dung(r.status_code == 200 and tt_muc(T3, "fuel") == "paid" and r.json()["sections"]["fuel"] == "paid"
             and "sec_fuel:book" in nk and "sec_fuel:pay_auto" in nk, "chỉ dầu kho đã cấp: ghi sổ → 'đã chi' ngay, nhật ký pay_auto",
             (r.status_code, ma(r), tt_muc(T3, "fuel"), nk))
        dung(not viec_dang_cho("treasury", "fuel", "paid"), "không còn là việc chờ của thủ quỹ VC")
        T4 = lap(1, hom_nay)
        dong(T4, "fuel", 1, qty=100, unit_price=26500, source="kho", place_id=kho.id, stock_move_id="qlsx:THU-0610-2")
        dong(T4, "fuel", 2, qty=50, unit_price=25000, source="mua", place_id=tram.id)
        muc(T4, fuel="verified")
        r = c.post("/api/trips/%s/sections/fuel/book" % T4.id, headers=H["khonl"])
        dung(r.status_code == 200 and tt_muc(T4, "fuel") == "booked" and viec_dang_cho("treasury", "fuel", "booked"),
             "có dòng mua trạm ngoài (tiền mặt) → vẫn 'đã ghi sổ', chờ thủ quỹ chi", (r.status_code, tt_muc(T4, "fuel")))
        r = c.post("/api/trips/%s/sections/fuel/pay" % T4.id, headers=H["quyvc"])
        dung(r.status_code == 200 and tt_muc(T4, "fuel") == "paid", "thủ quỹ VC chi như cũ", (r.status_code, ma(r)))
        T5 = lap(0, hom_nay)
        dong(T5, "fuel", 1, qty=80, unit_price=25000, source="mua", place_id=tram.id, ghi_no=True)
        muc(T5, fuel="verified")
        r = c.post("/api/trips/%s/sections/fuel/book" % T5.id, headers=H["khonl"])
        dung(r.status_code == 200 and tt_muc(T5, "fuel") == "booked", "ghi nợ trạm → giữ như cũ (chờ chi)", (r.status_code, tt_muc(T5, "fuel")))
        # ============================================================ mục IV chỉ "trả cùng lương" (điều phối 06/10, ví dụ G4-0006)
        print("== IV-lương. Ghi sổ mục IV không có tạm ứng tiền mặt → tự qua bước Chi")
        L1 = lap(0, hom_nay)
        dong(L1, "travel", 1, qty=1, unit_price=150000, item_key="x_trip")                         # mặc định cùng lương
        dong(L1, "travel", 2, qty=1, unit_price=20000, item_key="x_water")                         # mặc định cùng lương
        dong(L1, "fuel", 1, qty=100, unit_price=26500, source="kho", place_id=kho.id, stock_move_id="qlsx:THU-0610-L1")
        muc(L1, travel="verified")
        MANG.clear()
        r = c.post("/api/trips/%s/sections/travel/book" % L1.id, headers=H["ketoancp"])
        nk = [a for (a,) in db.query(M.TripLog.action).filter(M.TripLog.trip_id == L1.id, M.TripLog.action.like("sec_travel:%"))]
        dung(r.status_code == 200 and tt_muc(L1, "travel") == "paid" and "sec_travel:book" in nk and "sec_travel:pay_luong" in nk
             and not db.query(M.Voucher).filter(M.Voucher.trip_id == L1.id, M.Voucher.kind == "advance").count() and not MANG,
             "mục IV chỉ cùng lương: ghi sổ → 'đã chi' ngay (nhật ký pay_luong), không tờ tạm ứng, không gọi hệ kế toán",
             (r.status_code, ma(r), tt_muc(L1, "travel"), nk, MANG[:1]))
        dung(not viec_dang_cho("cash", "travel", "paid"), "không còn là việc chờ chi của quỹ tiền mặt")
        L2 = lap(1, hom_nay)
        dong(L2, "travel", 1, qty=1, unit_price=150000, item_key="x_trip")                         # cùng lương
        dong(L2, "other", 1, qty=1, unit_price=50000, item_key="x_misc")                           # VI tiền mặt → có tờ tạm ứng
        muc(L2, travel="verified")
        r = c.post("/api/trips/%s/sections/travel/book" % L2.id, headers=H["ketoancp"])
        dung(r.status_code == 200 and tt_muc(L2, "travel") == "booked",
             "mục IV cùng lương nhưng phiếu còn tiền mặt (mục VI) → giữ 'đã ghi sổ', chờ phiếu chi tạm ứng như cũ", (r.status_code, tt_muc(L2, "travel")))
        # ============================================================ dọn tồn (mục III chỉ lấy kho · mục IV không tiền mặt đã ghi sổ trước luật mới)
        T6 = lap(1, hom_nay)
        dong(T6, "fuel", 1, qty=60, unit_price=26500, source="kho", place_id=kho.id, stock_move_id="qlsx:THU-0610-3")
        muc(T6, fuel="booked")
        L3 = lap(0, hom_nay)
        dong(L3, "travel", 1, qty=1, unit_price=150000, item_key="x_trip")
        muc(L3, travel="booked")
        r = c.post("/api/muc/qua-chi-ton", headers=H["khonl"])
        dung(r.status_code == 403, "dọn tồn: không phải Sếp → 403", r.status_code)
        r = c.post("/api/muc/qua-chi-ton", headers=H["admin"])
        x = r.json() if r.status_code == 200 else {}
        dung(r.status_code == 200 and T6.doc_no in x["do"] and T5.doc_no not in x["do"] and tt_muc(T6, "fuel") == "paid"
             and tt_muc(T5, "fuel") == "booked", "dọn tồn III: chỉ lấy kho → đã chi; còn ghi nợ trạm thì giữ", x)
        dung(r.status_code == 200 and L3.doc_no in x["do_iv"] and L2.doc_no not in x["do_iv"] and tt_muc(L3, "travel") == "paid"
             and tt_muc(L2, "travel") == "booked", "dọn tồn IV: cùng lương, không tiền mặt → đã chi; phiếu có tạm ứng thì giữ", x.get("do_iv"))
        r = c.post("/api/muc/qua-chi-ton", headers=H["admin"])
        dung(r.status_code == 200 and r.json()["so_do"] == 0, "gọi lại → không đổi gì", r.json())

        # ============================================================ G4 + G6 — tất toán tài xế, chi thật mục IV
        ky = "2026-07"
        ngay_ky = dt.date(2026, 7, 10)
        dung(not db.query(M.DriverSettlement).filter(M.DriverSettlement.driver_id == tai_xe.id, M.DriverSettlement.period == ky).count()
             and not db.query(M.Trip).filter(M.Trip.driver_id == tai_xe.id, M.Trip.out_date >= dt.date(2026, 7, 1),
                                             M.Trip.out_date <= dt.date(2026, 7, 31)).count(),
             "kỳ thử %s của %s chưa chốt, chưa có DO nào" % (ky, tai_xe.name))
        print("== G6. Chi thật mục IV (trước khi chốt kỳ)")
        A = lap(0, ngay_ky)
        B = lap(1, ngay_ky)
        an = dong(A, "travel", 1, qty=2, unit_price=50000, item_key="x_food")                 # tiền mặt
        ap = dong(A, "travel", 2, qty=1, unit_price=0, item_key="x_phone")                    # tiền mặt, chưa có giá
        al = dong(A, "travel", 3, qty=1, unit_price=70000, item_key="x_trip", pay_channel="luong")   # trả cùng lương — không phải tiền mặt
        dong(B, "travel", 1, qty=1, unit_price=30000, item_key="x_water", pay_channel="tien_mat")
        B.locked = True
        db.add(M.Voucher(trip_id=A.id, kind="advance", doc_no="PTU-" + A.doc_no, doc_date=ngay_ky, driver_id=tai_xe.id,
                         amount_lak=100000, status="da_cap", token="thu-0610-" + A.id))
        db.commit()
        cta = "/api/trips/%s/chi-that" % A.id
        r = c.post(cta, json={"dong": [{"id": an.id, "chi_that": 80000}]}, headers=H["ketoancp"])
        dung(r.status_code == 409 and ma(r) == "CHUA_CHI" and ct(r).get("loi_lo"), "mục IV chưa chi → 409 CHUA_CHI (ba tiếng)", ma(r))
        muc(A, travel="paid"); muc(B, travel="paid")
        for u, http in (("ketoan", 403), ("thabok", 403), ("quyvc", 403), ("tx01", 403)):
            r = c.post(cta, json={"dong": [{"id": an.id, "chi_that": 80000}]}, headers=H[u])
            dung(r.status_code == http, "%s sửa chi thật → %d" % (u, http), (r.status_code, ma(r)))
        r = c.post(cta, json={"dong": [{"id": al.id, "chi_that": 1}]}, headers=H["ketoancp"])
        dung(r.status_code == 409 and ma(r) == "KHONG_PHAI_TIEN_MAT", "dòng trả cùng lương → 409 KHONG_PHAI_TIEN_MAT", ma(r))
        r = c.post(cta, json={"dong": [{"id": an.id, "chi_that": -5}]}, headers=H["ketoancp"])
        dung(r.status_code == 422 and ma(r) == "SO_SAI", "số âm → 422", ma(r))
        ct_truoc = db.query(M.ChungTu).filter(M.ChungTu.trip_id == A.id).count()
        r = c.post(cta, json={"dong": [{"id": an.id, "chi_that": "80,000"}, {"id": ap.id, "chi_that": 20000}], "ghi_chu": "tài xế nộp hoá đơn"},
                   headers=H["ketoancp"])
        db.expire_all()
        x = r.json() if r.status_code == 200 else {}
        dung(r.status_code == 200 and abs(db.get(M.TripExpense, an.id).unit_price - 40000) < 1e-6 and db.get(M.TripExpense, an.id).qty == 2
             and abs(db.get(M.TripExpense, ap.id).unit_price - 20000) < 1e-6,
             "KT Chi phí sửa: 2 × 50.000 → chi thật 80.000 (giữ SL, đơn giá 40.000); dòng giá 0 → 20.000", (r.status_code, ct(r)))
        nk = x.get("nhat_ky") or []
        dung(len(nk) == 2 and {(z["cu"], z["moi"]) for z in nk} == {(100000, 80000), (0, 20000)} and all(z["user"] and z["ts"] for z in nk)
             and nk[0]["ghi_chu"] == "tài xế nộp hoá đơn", "nhật ký từng dòng: cũ → mới, ai, lúc nào, ghi chú", nk)
        dung(len(x.get("dong") or []) == 2 and x.get("duoc_sua") and not any(z["id"] == al.id for z in x["dong"]),
             "màn chi thật chỉ liệt kê dòng tiền mặt; còn sửa được", [z["item_key"] for z in x.get("dong") or []])
        v = db.query(M.Voucher).filter(M.Voucher.trip_id == A.id, M.Voucher.kind == "advance").one()
        dung(v.amount_lak == 100000 and v.status == "da_cap" and db.query(M.ChungTu).filter(M.ChungTu.trip_id == A.id).count() == ct_truoc,
             "tờ tạm ứng (đã cấp 100.000) và chứng từ không đổi", (v.amount_lak, ct_truoc))
        r = c.post(cta, json={"dong": [{"id": an.id, "chi_that": 80000}]}, headers=H["ketoancp"])
        dung(r.status_code == 200 and len(r.json()["nhat_ky"]) == 2, "gửi lại cùng số → không ghi thêm nhật ký", len(r.json().get("nhat_ky", [])))
        r = c.get("/api/tat-toan/%s?ky=%s" % (tai_xe.id, ky), headers=H["ketoancp"])
        pa = next((p for p in r.json().get("phieu", []) if p["trip_id"] == A.id), {})
        dung(r.status_code == 200 and pa.get("da_chi_that_lak") == 100000 and pa.get("da_ung_lak") == 100000,
             "tất toán: đã chi thật theo số mới (80.000 + 20.000), đã ứng giữ 100.000", (pa.get("da_chi_that_lak"), pa.get("da_ung_lak")))
        r = c.get(cta, headers=H["thabok"])
        dung(r.status_code == 403, "Bãi xem chi thật → 403", r.status_code)
        J = lap(1, ngay_ky)
        J.company = "joint"; db.commit()
        muc(J, travel="paid")
        r = c.post("/api/trips/%s/chi-that" % J.id, json={"dong": []}, headers=H["ketoancp"])
        dung(r.status_code == 409 and ma(r) == "XE_THUE", "phiếu xe thuê → 409 XE_THUE", ma(r))
        db.delete(J); db.commit()

        print("== G4. Chốt tất toán: chặn khi còn DO dở")
        dong(A, "travel", 4, qty=1, unit_price=0, item_key="x_parking")                      # tiền mặt giá 0
        db.add(M.TripEvent(trip_id=A.id, kind="refuel", status="reported", qty_l=60, place_id=tram.id, by_user=tai_xe.name))
        db.commit()
        r = c.get("/api/tat-toan/%s?ky=%s" % (tai_xe.id, ky), headers=H["ketoancp"])
        xem = r.json().get("chan_chot") or []
        dung(r.status_code == 200 and [z["doc_no"] for z in xem] == [A.doc_no] and xem[0]["ly_do"] == ["CHUA_KHOA", "KHAI_BAO_CHO", "GIA_0"],
             "xem trước: A chưa khoá · 1 khai dầu chờ duyệt · dòng tiền mặt giá 0; B đã khoá đủ thì không có", xem)
        r = c.post("/api/tat-toan", json={"driver_id": tai_xe.id, "period": ky}, headers=H["ketoancp"])
        d = ct(r) or {}
        dung(r.status_code == 409 and d.get("ma") == "CHUA_DU_DE_CHOT" and A.doc_no in d.get("loi", "") and "IV 4" in d.get("loi", "")
             and d.get("loi_lo") and d.get("loi_en") and [z["doc_no"] for z in d.get("phieu", [])] == [A.doc_no],
             "chốt → 409 CHUA_DU_DE_CHOT liệt kê từng DO, đủ ba tiếng", d.get("loi"))
        dung(not db.query(M.DriverSettlement).filter(M.DriverSettlement.driver_id == tai_xe.id, M.DriverSettlement.period == ky).count(),
             "bị chặn: không có bản chốt")
        # sửa từng chỗ: giá dòng 4 (chi thật), từ chối khai dầu, khoá A
        c.post(cta, json={"dong": [{"id": db.query(M.TripExpense).filter(M.TripExpense.trip_id == A.id, M.TripExpense.line_no == 4).one().id,
                                    "chi_that": 10000}]}, headers=H["ketoancp"])
        for e in db.query(M.TripEvent).filter(M.TripEvent.trip_id == A.id, M.TripEvent.status == "reported"):
            e.status = "rejected"
        db.commit()
        r = c.post("/api/tat-toan", json={"driver_id": tai_xe.id, "period": ky}, headers=H["ketoancp"])
        dung(r.status_code == 409 and [z["ly_do"] for z in ct(r).get("phieu", [])] == [["CHUA_KHOA"]], "còn đúng một việc: A chưa khoá",
             ct(r).get("loi") if isinstance(ct(r), dict) else ct(r))
        db.get(M.Trip, A.id).locked = True; db.commit()
        MANG.clear()
        r = c.post("/api/tat-toan", json={"driver_id": tai_xe.id, "period": ky, "note": "thử 06/10"}, headers=H["ketoancp"])
        x = r.json() if r.status_code == 200 else {}
        tt = x.get("tat_toan") or {}
        dung(r.status_code == 200 and tt.get("tong_chi_lak") == 140000 and tt.get("tong_ung_lak") == 100000 and tt.get("chenh_lech_lak") == 40000
             and x.get("chan_chot") == [], "đủ điều kiện → chốt: đã chi thật 80.000 + 20.000 + 10.000 + 30.000 = 140.000, ứng 100.000, chênh 40.000",
             (r.status_code, ct(r) if r.status_code != 200 else {k: tt.get(k) for k in ("tong_chi_lak", "tong_ung_lak", "chenh_lech_lak")}))
        dung((tt.get("phieu_ke_toan") or {}).get("status") == "loi", "phiếu chi bù sang kế toán: mạng bị chặn → ghi lỗi trên bản ghi (gửi lại sau)",
             (tt.get("phieu_ke_toan") or {}).get("error_code"))
        r = c.post(cta, json={"dong": [{"id": an.id, "chi_that": 60000}]}, headers=H["ketoancp"])
        dung(r.status_code == 409 and ma(r) == "KY_DA_CHOT" and ct(r).get("loi_lo") and ct(r).get("loi_en"),
             "kỳ đã chốt → sửa chi thật 409 KY_DA_CHOT (ba tiếng)", ct(r).get("loi") if isinstance(ct(r), dict) else ct(r))
        r = c.get(cta, headers=H["ketoancp"])
        dung(r.status_code == 200 and not r.json()["duoc_sua"] and r.json()["ly_do"]["ma"] == "KY_DA_CHOT" and r.json()["tat_toan"],
             "màn chi thật: khoá, nói rõ kỳ đã chốt", r.json().get("ly_do"))
        print("== G4. Bỏ chốt")
        x = db.query(M.DriverSettlement).filter(M.DriverSettlement.driver_id == tai_xe.id, M.DriverSettlement.period == ky).one()
        from services import chi_tat_toan_tune as TTT
        rec, bt = TTT._phieu_tt(db, x), TTT._but_toan_tt(db, x)
        rec.status, rec.document_no, rec.post_by, rec.post_at = "da_chi", "CMP-THU-0610", "Thủ quỹ thử", dt.datetime(2026, 10, 6, 9, 0)
        db.commit()
        r = c.get("/api/tat-toan/%s?ky=%s" % (tai_xe.id, ky), headers=H["ketoancp"])
        dung(r.status_code == 200 and (r.json().get("bo_chot_chan") or {}).get("ma") == "DA_CHI_O_KE_TOAN",
             "xem: phiếu chênh đã ghi sổ → bo_chot_chan nói vì sao", (r.json().get("bo_chot_chan") or {}).get("loi"))
        r = c.delete("/api/tat-toan/%s?ky=%s" % (tai_xe.id, ky), headers=H["ketoancp"])
        d = ct(r) or {}
        dung(r.status_code == 409 and d.get("ma") == "DA_CHI_O_KE_TOAN" and "CMP-THU-0610" in d.get("loi", "") and "lệch" in d.get("loi", "")
             and d.get("loi_lo") and d.get("loi_en"), "bỏ chốt khi phiếu chênh đã ghi sổ → 409 nói rõ không bỏ được và vì sao", d.get("loi"))
        rec.status, rec.obj_id = "loi", None          # lần gửi chưa tới được hệ kế toán (không có gì bên đó để tìm / rút)
        if bt is not None:
            bt.status, bt.so_ben_ke_toan = "da_gui", "GL-THU-0610"
        db.commit()
        if bt is not None:
            r = c.delete("/api/tat-toan/%s?ky=%s" % (tai_xe.id, ky), headers=H["ketoancp"])
            dung(r.status_code == 409 and ma(r) == "BUT_TOAN_DA_GUI" and "QT_TU" in ct(r).get("loi", ""),
                 "QT_TU đã gửi → 409 nói rõ", ct(r).get("loi") if isinstance(ct(r), dict) else ct(r))
            bt.status = "cho_gui"; db.commit()
        r = c.delete("/api/tat-toan/%s?ky=%s" % (tai_xe.id, ky), headers=H["ketoancp"])
        dung(r.status_code == 200, "chưa ghi sổ, QT_TU chưa gửi → bỏ chốt được như cũ", (r.status_code, ct(r) if r.status_code != 200 else ""))
        r = c.post(cta, json={"dong": [{"id": an.id, "chi_that": 60000}]}, headers=H["ketoancp"])
        dung(r.status_code == 200, "bỏ chốt rồi → sửa chi thật lại được", (r.status_code, ma(r)))
        dung(not any("5090" in u or "accounting" in u for u in MANG if "cmpayment" not in u and "master-data" not in u),
             "không gọi mạng nào ngoài hệ kế toán (bị chặn có chủ ý)", MANG[:3])

        # ============================================================ hỏi lại phiếu tất toán bên kế toán: 5xx / mất mạng không phải "mất"
        print("== dong_bo. Hỏi lại phiếu chênh: lỗi 5xx / mất mạng giữ trạng thái, chỉ 4xx thật mới là PHIEU_CHI_MAT")
        import io
        import urllib.error
        from fastapi import HTTPException
        from services import chi_tat_toan_tune as TTT2
        rec = M.PhieuTienTune(nguon="tat_toan", ma_nguon="thu-0610:dong-bo", loai="TT_CHI", voucher_type="CMP", doi_tuong_loai="tai_xe",
                              doi_tuong_id=tai_xe.id, currency="LAK", amount=1000, amount_lak=1000, ref_no="TTX-THU-0610", no="1601",
                              co="1011", status="da_gui", real_id=987654, document_no="CMP-THU-0610")
        db.add(rec); db.commit()

        def tra_http(ma, than):
            def _f(yc, *a, **k):
                MANG.append(getattr(yc, "full_url", str(yc)))
                raise urllib.error.HTTPError(getattr(yc, "full_url", ""), ma, "thu", {}, io.BytesIO(than.encode("utf-8")))
            return _f
        for ten, f, giu in (("HTTP 500 bên kế toán", tra_http(500, '{"Success": false, "Message": "loi may chu"}'), True),
                            ("HTTP 503 bên kế toán", tra_http(503, "Service Unavailable"), True),
                            ("mất mạng", _cam_mang, True),
                            ("HTTP 404 (từ chối thật)", tra_http(404, '{"Success": false, "Message": "khong co phieu"}'), False)):
            rec.status, rec.error_code, rec.error_message = "da_gui", None, None
            db.commit()
            urllib.request.urlopen = f
            try:
                TTT2.dong_bo(db, rec)
                loi = None
            except HTTPException as e:
                loi = (e.status_code, (e.detail or {}).get("ma"))
            finally:
                urllib.request.urlopen = _cam_mang
            db.expire_all()
            r2 = db.get(M.PhieuTienTune, rec.id)
            if giu:
                dung(loi is not None and r2.status == "da_gui" and r2.error_code is None,
                     "%s → ném lỗi, phiếu vẫn 'đã gửi · chờ chi' (lượt sau hỏi lại)" % ten, (loi, r2.status, r2.error_code))
            else:
                dung(loi is not None and r2.status == "loi" and r2.error_code == "PHIEU_CHI_MAT",
                     "%s → PHIEU_CHI_MAT như cũ" % ten, (loi, r2.status, r2.error_code))
    finally:
        app.dependency_overrides.clear()
        db.close()
        ngoai.rollback()
        conn.close()
    print("đã ROLLBACK — bản sao d7 không đổi")
    print("TỔNG: %d/%d đạt" % (sum(KQ), len(KQ)))
    sys.exit(0 if all(KQ) else 1)


if __name__ == "__main__":
    main()

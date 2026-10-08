# -*- coding: utf-8 -*-
"""TỰ ĐỒNG BỘ NỀN trạng thái chứng từ đã gửi sang hệ kế toán anh Tune (06/10/2026).

Vì sao: trang điều xe chưa ra Internet nên hệ anh Tune không gọi sang báo "đã chi / đã thu" — bên em phải HỎI LẠI. Trước 06/10
chỉ hỏi khi người dùng mở tờ, bấm Xuất phát hay bấm Cập nhật, nên trạng thái bên em đứng yên dù bên kia đã xong (rà 06/10: SO 169
đã thu đủ mà trang điều xe vẫn "chưa thu"; viên trạng thái chi của bàn giao DO đọc đúng các bản ghi này). Luồng nền này cứ N phút
hỏi lại MỘT LƯỢT các bản ghi còn chờ — CHỈ GỌI các hàm đọc lại sẵn có, không viết lại luật nào:

    tam_ung     phiếu chi "Chi trước" (chi_tune · ChiTune da_gui)            → chi_tune.dong_bo        (mục IV "đã chi", PTU "đã cấp")
    chi_muc     phiếu chi "Chi khác" mục V–VI (ChiMucTune da_gui)            → chi_muc_tune.dong_bo    (mục "đã chi" khi đủ)
    tra_chu_xe  đề nghị trả chủ xe (ChiChuXeTune da_gui)                     → chi_tune.dong_bo_chu_xe (phiếu "đã trả", chốt hàng quầy)
    phieu_tien  tất toán tháng tài xế · trả nhà cung cấp (PhieuTienTune da_gui) → chi_tat_toan_tune.dong_bo
    so_cuoc     thu tiền SO cước (GuiSoTune synced, chưa thu đủ)             → de_nghi_thu.doc_thu_tune (thu_*, trips.finance_status)
    so_nl       thu tiền SO nhiên liệu (GuiSoNhienLieuTune synced, chưa thu đủ) → so_nhien_lieu.doc_thu
    chi_luong   trả cùng lương (06/10): dòng cùng lương của DO đã ghi sổ mục IV mà chưa "đã trả" → chi_luong_tune.dong_bo
                (phiếu chi lương lập trên Web theo DO, hỏi theo khoá dòng, lô 500) — CHỈ khi EPL_DONG_BO_CHI_LUONG=1
    khach_gls   thông tin chung khách đã liên kết Đối tượng GLS (customers.obj_id, Việc 9 08/10) chép quá 60 phút → khach_gls.dong_bo
                (tên · điện thoại · địa chỉ · mã) — CHỈ khi EPL_KHACH_GLS=1
    ncc_gls     như trên cho nhà cung cấp + chủ xe liên kết (Việc 10) → doi_tuong_gls.dong_bo — CHỈ khi EPL_NCC_GLS=1

Mỗi lượt mỗi loại tối đa `gioi_han()` bản ghi, bản ghi hỏi lâu nhất trước (checked_at / thu_doc_luc); bản ghi đã xong (đã chi, đã
thu đủ, lỗi) không hỏi. Lỗi máy chủ / mạng bên kia (HTTP ≥ 500, không gọi được, chưa có token) → ghi log, DỪNG lượt, lượt sau thử
lại; bên kia từ chối một bản ghi (4xx) → bỏ qua bản ghi đó, làm tiếp. Không chạy chồng: khoá trong tiến trình + khoá Postgres
(pg_try_advisory_lock) — nhiều worker uvicorn thì chỉ một worker chạy một lượt, và lượt bị bỏ nếu máy khác vừa chạy chưa đủ N phút
(mốc lượt gần nhất ghi trong bảng cau_hinh, khoá `dong_bo_nen`). Màn quản trị đọc tình trạng ở GET /api/dong-bo-nen (Sếp).

Cấu hình (.env): EPL_DONG_BO_NEN_PHUT (mặc định 5; 0 = tắt) · EPL_DONG_BO_NEN_GIOI_HAN (mặc định 50 bản ghi mỗi loại mỗi lượt;
chi_luong hỏi tối đa max(giới hạn, 500) dòng — một lô 500 khoá là một lần gọi) · EPL_DONG_BO_CHI_LUONG (1 = hỏi trả cùng lương;
mặc định tắt tới khi API anh Tune đang chạy có đường line-vouchers — bản cũ trả 404).
Nhật ký: logs/dong_bo_nen.log. Bài kiểm: kiem/thu_dong_bo_nen.py (một lượt trong giao dịch ROLLBACK, lời gọi mạng giả lập).
"""
import datetime as dt
import json
import logging
import os
import threading
import time

from fastapi import HTTPException
from sqlalchemy import or_, text

_nk = logging.getLogger("epl_lao.dong_bo_nen")
KHOA_PG = 610_2026                  # khoá tư vấn Postgres của luồng này (số bất kỳ, cố định)
KHOA_CAU_HINH = "dong_bo_nen"       # cau_hinh.khoa — JSON tình trạng lượt gần nhất (dùng chung giữa các worker)
TRE_DAU = 60                        # giây chờ sau khi máy chủ bật (để lam_nong tính sẵn báo cáo trước)
_KHOA = threading.Lock()            # không chạy chồng lượt trong một tiến trình
_LUONG = {"t": None}


def phut():
    """Chu kỳ (phút). 0 / số âm / chữ = tắt."""
    v = (os.getenv("EPL_DONG_BO_NEN_PHUT") or "5").strip()
    try:
        return max(0.0, float(v))
    except ValueError:
        return 0.0


def gioi_han():
    v = (os.getenv("EPL_DONG_BO_NEN_GIOI_HAN") or "").strip()
    return int(v) if v.isdigit() and int(v) > 0 else 50


def _ghi_log():
    if not _nk.handlers:
        from database import GOC_DU_AN
        os.makedirs(os.path.join(GOC_DU_AN, "logs"), exist_ok=True)
        h = logging.FileHandler(os.path.join(GOC_DU_AN, "logs", "dong_bo_nen.log"), encoding="utf-8")
        h.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        _nk.addHandler(h); _nk.setLevel(logging.INFO); _nk.propagate = False


def _gio(t=None):
    return (t or dt.datetime.utcnow()).replace(microsecond=0).isoformat() + "+00:00"


def _cau_loi(e):
    if isinstance(e, HTTPException):
        d = e.detail if isinstance(e.detail, dict) else {}
        return "%s %s" % (d.get("ma") or e.status_code, (d.get("loi") or str(e.detail))[:300])
    return ("%s: %s" % (type(e).__name__, e))[:300]


def _dung_luot(e):
    """Lỗi này có phải lỗi máy chủ / mạng bên kia (dừng cả lượt) không — bên kia từ chối MỘT bản ghi (4xx) thì không."""
    return not isinstance(e, HTTPException) or e.status_code >= 500


class _DungLuot(Exception):
    pass


# ================================================================ từng loại bản ghi
def _phieu_chi(db, Bang, ham, n, ket, ten):
    """Một loại phiếu chi / thu bên kế toán (bản ghi có status · real_id · checked_at): hỏi lại các bản ghi `da_gui`."""
    ds = (db.query(Bang).filter(Bang.status == "da_gui", Bang.real_id.isnot(None))
          .order_by(Bang.checked_at.asc().nullsfirst()).limit(n).all())
    for rec in ds:
        truoc = (rec.status, rec.error_code, rec.error_message, rec.checked_at)
        try:
            ham(db, rec)
        except Exception as e:                                     # noqa: BLE001
            db.rollback()
            if _dung_luot(e):
                # chi_tune.doc_phieu (06/10) đánh PHIEU_CHI_MAT cả khi bên kia trả 5xx — lỗi máy chủ không phải phiếu bị xoá:
                # trả bản ghi về như trước khi hỏi (người dùng không phải "gửi lại" một phiếu vẫn còn bên đó)
                db.refresh(rec)
                if rec.status == "loi" and truoc[0] == "da_gui":
                    rec.status, rec.error_code, rec.error_message, rec.checked_at = truoc
                    db.commit()
                raise _DungLuot("%s %s: %s" % (ten, getattr(rec, "document_no", None) or rec.real_id, _cau_loi(e)))
            ket["loi_ban_ghi"].append("%s %s: %s" % (ten, getattr(rec, "document_no", None) or rec.real_id, _cau_loi(e)))
            continue
        ket["da_hoi"][ten] = ket["da_hoi"].get(ten, 0) + 1
        if rec.status != truoc[0]:
            ket["cap_nhat"][ten] = ket["cap_nhat"].get(ten, 0) + 1


def _so(db, Bang, ham, n, ket, ten):
    """Thu tiền SO (cước / nhiên liệu): hỏi lại SO đã tạo mà chưa thu đủ — hàm đọc lại tự gom theo khách / đối tác."""
    ds = (db.query(Bang).filter(Bang.status == "synced", Bang.order_code.isnot(None),
                                or_(Bang.thu_trang_thai.is_(None), Bang.thu_trang_thai != "da_thu"))
          .order_by(Bang.thu_doc_luc.asc().nullsfirst()).limit(n).all())
    if not ds:
        return
    truoc = {b.do_id: (b.thu_trang_thai, b.thu_da_thu, b.thu_con_no) for b in ds}
    try:
        kq = ham(db, ds) or {}
        db.commit()                                                 # hai hàm đọc lại không tự commit
    except Exception as e:                                          # noqa: BLE001
        db.rollback()
        raise _DungLuot("%s: %s" % (ten, _cau_loi(e)))
    ket["da_hoi"][ten] = ket["da_hoi"].get(ten, 0) + int(kq.get("da_doc") or 0)
    doi = sum(1 for b in ds if (b.thu_trang_thai, b.thu_da_thu, b.thu_con_no) != truoc[b.do_id])
    if doi:
        ket["cap_nhat"][ten] = ket["cap_nhat"].get(ten, 0) + doi
    if kq.get("loi"):
        # hàm đọc lại đã dừng ở khách / đối tác hỏng và ghi lỗi lên SO đó (thu_loi) — coi như lỗi bên kia, lượt sau thử lại
        raise _DungLuot("%s: %s" % (ten, kq["loi"]))


def _chi_luong(db, n, ket, ten):
    """Trả cùng lương (06/10): hỏi phiếu chi lương lập trên Web theo khoá dòng (chi_luong_tune.dong_bo, lô 500 khoá một lần gọi).
    Lỗi máy chủ / mạng bên kia → dừng lượt; bên kia từ chối cả lô (4xx — ví dụ chưa có đường, tài khoản chưa được gọi) → ghi
    loi_ban_ghi, lượt chạy tiếp. Lô đã ghi trước lỗi vẫn giữ (dong_bo commit từng lô)."""
    from services import chi_luong_tune as CL
    try:
        kq = CL.dong_bo(db, n)
    except Exception as e:                                          # noqa: BLE001
        db.rollback()
        if _dung_luot(e):
            raise _DungLuot("%s: %s" % (ten, _cau_loi(e)))
        ket["loi_ban_ghi"].append("%s: %s" % (ten, _cau_loi(e)))
        return
    if kq["da_hoi"]:
        ket["da_hoi"][ten] = ket["da_hoi"].get(ten, 0) + kq["da_hoi"]
    if kq["cap_nhat"]:
        ket["cap_nhat"][ten] = ket["cap_nhat"].get(ten, 0) + kq["cap_nhat"]


def _khach_gls(db, n, ket, ten):
    """Khách là đối tượng GLS (Việc 9): chép lại thông tin chung các khách chép quá 60 phút, lâu nhất trước. Đối tượng không còn
    bên GLS → ghi loi_ban_ghi (khách vẫn dùng bản chép cũ)."""
    from services import khach_gls as KG
    try:
        kq = KG.dong_bo(db, n, cu_hon_phut=60)
        db.commit()
    except Exception as e:                                          # noqa: BLE001
        db.rollback()
        if _dung_luot(e):
            raise _DungLuot("%s: %s" % (ten, _cau_loi(e)))
        ket["loi_ban_ghi"].append("%s: %s" % (ten, _cau_loi(e)))
        return
    if kq["da_hoi"]:
        ket["da_hoi"][ten] = ket["da_hoi"].get(ten, 0) + kq["da_hoi"]
    if kq["cap_nhat"]:
        ket["cap_nhat"][ten] = ket["cap_nhat"].get(ten, 0) + kq["cap_nhat"]
    for m in kq["mat"]:
        ket["loi_ban_ghi"].append("%s %s: đối tượng GLS %s không còn" % (ten, m["name"], m["obj_id"]))


def _ncc_gls(db, n, ket, ten):
    """Nhà cung cấp + chủ xe liên kết (Việc 10): như _khach_gls, mỗi loại tối đa `n` hồ sơ chép quá 60 phút."""
    from services import doi_tuong_gls as DT
    for loai in ("ncc", "chu_xe"):
        try:
            kq = DT.dong_bo(db, loai, n, cu_hon_phut=60)
            db.commit()
        except Exception as e:                                      # noqa: BLE001
            db.rollback()
            if _dung_luot(e):
                raise _DungLuot("%s: %s" % (ten, _cau_loi(e)))
            ket["loi_ban_ghi"].append("%s %s: %s" % (ten, loai, _cau_loi(e)))
            continue
        if kq["da_hoi"]:
            ket["da_hoi"][ten] = ket["da_hoi"].get(ten, 0) + kq["da_hoi"]
        if kq["cap_nhat"]:
            ket["cap_nhat"][ten] = ket["cap_nhat"].get(ten, 0) + kq["cap_nhat"]
        for m in kq["mat"]:
            ket["loi_ban_ghi"].append("%s %s %s: đối tượng %s không còn" % (ten, loai, m["name"], m["obj_id"]))


def _kho_web(db, n, ket, ten):
    """Điểm đổ kho dầu EPL ↔ danh mục kho trên Web (08/10): chép lại tên / địa chỉ / trạng thái, tối đa mỗi giờ một lần."""
    from services import diem_do_web as DDW
    if not DDW.can_dong_bo(db):
        return
    try:
        kq = DDW.dong_bo(db)
        db.commit()
    except Exception as e:                                          # noqa: BLE001
        db.rollback()
        if _dung_luot(e):
            raise _DungLuot("%s: %s" % (ten, _cau_loi(e)))
        ket["loi_ban_ghi"].append("%s: %s" % (ten, _cau_loi(e)))
        return
    ket["da_hoi"][ten] = ket["da_hoi"].get(ten, 0) + 1
    if kq["cap_nhat"]:
        ket["cap_nhat"][ten] = ket["cap_nhat"].get(ten, 0) + kq["cap_nhat"]
    for m in kq["mat"]:
        ket["loi_ban_ghi"].append("%s %s: không còn trong danh mục kho trên Web" % (ten, m))


def _viec():
    from models import ChiChuXeTune, ChiMucTune, ChiTune, GuiSoNhienLieuTune, GuiSoTune, PhieuTienTune
    from services import chi_luong_tune as CL
    from services import chi_muc_tune as CMT
    from services import chi_tat_toan_tune as CTT
    from services import chi_tune as CHI
    from services import de_nghi_thu as DNT
    from services import so_nhien_lieu as NL
    viec = [
        ("tam_ung", lambda db, n, k: _phieu_chi(db, ChiTune, CHI.dong_bo, n, k, "tam_ung")),
        ("chi_muc", lambda db, n, k: _phieu_chi(db, ChiMucTune, CMT.dong_bo, n, k, "chi_muc")),
        ("tra_chu_xe", lambda db, n, k: _phieu_chi(db, ChiChuXeTune, CHI.dong_bo_chu_xe, n, k, "tra_chu_xe")),
        ("phieu_tien", lambda db, n, k: _phieu_chi(db, PhieuTienTune, CTT.dong_bo, n, k, "phieu_tien")),
        ("so_cuoc", lambda db, n, k: _so(db, GuiSoTune, lambda d, ds: DNT.doc_thu_tune(d, ds, ep=True), n, k, "so_cuoc")),
        ("so_nl", lambda db, n, k: _so(db, GuiSoNhienLieuTune, NL.doc_thu, n, k, "so_nl")),
    ]
    if CL.bat():                                                    # cuối lượt: lỗi của nó không chặn các loại trên
        viec.append(("chi_luong", lambda db, n, k: _chi_luong(db, n, k, "chi_luong")))
    from services import khach_gls as KG
    if KG.bat():                                                    # thông tin chung khách — sau cùng, không chặn tiền
        viec.append(("khach_gls", lambda db, n, k: _khach_gls(db, n, k, "khach_gls")))
    from services import doi_tuong_gls as DT
    if DT.bat("ncc"):                                               # nhà cung cấp + chủ xe (Việc 10)
        viec.append(("ncc_gls", lambda db, n, k: _ncc_gls(db, n, k, "ncc_gls")))
    from services import kho_qlsx as KQ
    if KQ.bat():                                                    # kho dầu EPL ↔ danh mục kho Web (08/10)
        viec.append(("kho_web", lambda db, n, k: _kho_web(db, n, k, "kho_web")))
    return viec


def mot_luot(db, n=None):
    """MỘT lượt trên phiên `db` có sẵn — không khoá, không ghi tình trạng (bài kiểm gọi thẳng trong giao dịch ROLLBACK).
    → {"da_hoi": {loại: n}, "cap_nhat": {loại: n}, "loi": câu lỗi dừng lượt | None, "loi_ban_ghi": [...]}."""
    n = n or gioi_han()
    ket = {"da_hoi": {}, "cap_nhat": {}, "loi": None, "loi_ban_ghi": []}
    for ten, ham in _viec():
        try:
            ham(db, n, ket)
        except _DungLuot as e:
            ket["loi"] = str(e)
            break
    return ket


# ================================================================ lượt của luồng nền: khoá, tình trạng
def _co_cau_hinh():
    from services import gui_tune as GT
    return bool(GT.cau_hinh(dang_nhap=False)[1])


def doc_tinh_trang(db):
    from models import CauHinh
    r = db.get(CauHinh, KHOA_CAU_HINH)
    try:
        return json.loads(r.gia_tri) if r is not None and r.gia_tri else {}
    except ValueError:
        return {}


def _ghi_tinh_trang(db, tt):
    from services import day_ke_toan as DK
    DK.dat_cau_hinh(db, KHOA_CAU_HINH, json.dumps(tt, ensure_ascii=False))
    db.commit()


def _vua_chay(tt, giay):
    try:
        bd = dt.datetime.fromisoformat(tt.get("bat_dau", "")[:19])
    except ValueError:
        return False
    return (dt.datetime.utcnow() - bd).total_seconds() < giay


def chay_luot(tao_phien=None, ep=False):
    """Một lượt của luồng nền. Bỏ (trả lý do) khi: lượt khác đang chạy trong tiến trình / ở worker khác (khoá Postgres), máy khác
    vừa chạy chưa đủ chu kỳ (trừ `ep`), chưa cấu hình hệ kế toán. Ghi tình trạng vào cau_hinh."""
    from database import SessionLocal, engine
    tao_phien = tao_phien or SessionLocal
    if not _KHOA.acquire(blocking=False):
        return {"bo_qua": "đang chạy một lượt khác trong tiến trình này"}
    c = None
    try:
        c = engine.connect()
        if not c.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": KHOA_PG}).scalar():
            return {"bo_qua": "worker khác đang chạy một lượt"}
        db = tao_phien()
        try:
            tt = doc_tinh_trang(db)
            if not ep and _vua_chay(tt, max(0.0, phut() * 60 - 30)):
                return {"bo_qua": "máy khác vừa chạy lúc %s" % tt.get("bat_dau")}
            if not _co_cau_hinh():
                tt.update({"bat_dau": _gio(), "xong": _gio(), "bo_qua": "chưa có địa chỉ / token hệ kế toán (QLSX_*)"})
                _ghi_tinh_trang(db, tt)
                return {"bo_qua": tt["bo_qua"]}
            t0, bd = time.time(), _gio()
            tt.update({"bat_dau": bd, "xong": None, "bo_qua": None, "may": "%s pid %s" % (os.getenv("COMPUTERNAME") or "", os.getpid())})
            _ghi_tinh_trang(db, tt)                                 # mốc bắt đầu: worker khác thấy ngay, không chạy chồng
            try:
                ket = mot_luot(db)
            except Exception as e:                                  # noqa: BLE001 — lỗi lạ: ghi lại, luồng vẫn sống
                db.rollback()
                ket = {"da_hoi": {}, "cap_nhat": {}, "loi": _cau_loi(e), "loi_ban_ghi": []}
            tt = doc_tinh_trang(db)
            tt.update({"bat_dau": bd, "xong": _gio(), "giay": round(time.time() - t0, 1), "da_hoi": ket["da_hoi"],
                       "cap_nhat": ket["cap_nhat"], "loi": ket["loi"], "loi_ban_ghi": ket["loi_ban_ghi"][:10],
                       "so_luot": int(tt.get("so_luot") or 0) + 1})
            if ket["loi"] or ket["loi_ban_ghi"]:
                tt["loi_gan_nhat"] = {"luc": _gio(), "loi": ket["loi"] or ket["loi_ban_ghi"][0]}
            _ghi_tinh_trang(db, tt)
            _nk.info("%s lượt %.1f s · hỏi %s · cập nhật %s%s", "✗" if ket["loi"] else "✓", time.time() - t0,
                     json.dumps(ket["da_hoi"]), json.dumps(ket["cap_nhat"]), (" · " + ket["loi"]) if ket["loi"] else "")
            return tt
        finally:
            db.close()
    finally:
        if c is not None:
            try:
                c.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": KHOA_PG})
                c.rollback()
                c.close()
            except Exception:                                       # noqa: BLE001 — không nhả được: bỏ hẳn kết nối, khoá tự nhả
                c.invalidate()
        _KHOA.release()


def _vong():
    time.sleep(TRE_DAU)
    while True:
        p = phut()
        if p <= 0:
            return
        try:
            kq = chay_luot()
            if kq.get("bo_qua"):
                _nk.info("· bỏ lượt: %s", kq["bo_qua"])
        except Exception as e:                                      # noqa: BLE001 — DB tạm mất: lượt sau thử lại
            _nk.info("✗ lượt hỏng: %s", _cau_loi(e))
        time.sleep(p * 60)


def bat_dau():
    """Gọi lúc máy chủ khởi động (main.py): một luồng nền mỗi tiến trình, tắt khi EPL_DONG_BO_NEN_PHUT=0."""
    if phut() <= 0 or (_LUONG["t"] is not None and _LUONG["t"].is_alive()):
        return
    _ghi_log()
    _LUONG["t"] = threading.Thread(target=_vong, name="dong-bo-nen", daemon=True)
    _LUONG["t"].start()


def tinh_trang(db):
    """Cho GET /api/dong-bo-nen: cấu hình + lượt gần nhất (dùng chung mọi worker, đọc từ cau_hinh)."""
    from services import chi_luong_tune as CL
    return {"bat": phut() > 0, "phut": phut(), "gioi_han": gioi_han(), "co_cau_hinh_ke_toan": _co_cau_hinh(), "chi_luong": CL.bat(),
            "luong_song": bool(_LUONG["t"] is not None and _LUONG["t"].is_alive()), "dang_chay_luot": _KHOA.locked(),
            "lan_gan_nhat": doc_tinh_trang(db) or None}

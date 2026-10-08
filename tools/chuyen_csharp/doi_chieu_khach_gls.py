# -*- coding: utf-8 -*-
"""Việc 9 / 10 (chuyển trang điều xe sang module Vận tải C#, 08/10): ĐỐI CHIẾU khách · nhà cung cấp · chủ xe liên kết hiện có với
danh mục Đối tượng chung → ghi `obj_id` (OBJ_AUTOID), rồi mới bật cờ (EPL_KHACH_GLS cho khách, EPL_NCC_GLS cho nhà cung cấp + chủ xe).

    python -X utf8 tools/chuyen_csharp/doi_chieu_khach_gls.py                      # khách, CHỈ XEM — không ghi gì
    python -X utf8 tools/chuyen_csharp/doi_chieu_khach_gls.py --loai ncc           # nhà cung cấp (chu_xe · tat_ca tương tự)
    python -X utf8 tools/chuyen_csharp/doi_chieu_khach_gls.py --loai tat_ca --ghi  # ghi obj_id + chép tên/điện thoại/địa chỉ/mã (DB EPL)
    python -X utf8 tools/chuyen_csharp/doi_chieu_khach_gls.py --ghi --tao          # chưa có trong danh mục chung: TẠO rồi ghi

DB EPL lấy DATABASE_URL (.env hoặc biến môi trường); danh mục chung lấy QLSX_BASE_URL + token như trang điều xe (services/chi_tune).
`--tao` là GHI vào danh mục Đối tượng chung — chỉ chạy khi chủ dự án đồng ý. Tài xế (EPLTX-) không đối chiếu ở đây.

Thứ tự tìm đối tượng của một hồ sơ (dừng ở cách đầu tiên ra kết quả):
  1. obj_id đã ghi → kiểm còn trong danh mục.
  2. bảng nhớ đối tượng bên kế toán (doi_tuong_tune) — hồ sơ đã từng gửi chứng từ.
  3. mã (cột code) = OBJ_OBJECTNO, đúng cả mã.
  4. không có → «chưa có» (`--tao`: tạo mã = mã đang có, trống thì EPLKH- / EPLNCC- / EPLCX-<id> như chi_tune.doi_tuong).
"""
import os
import sys

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(GOC, "backend", "app"))

import database  # noqa: E402 — nạp .env, mở DB
from fastapi import HTTPException  # noqa: E402
from models import DoiTuongTune, Trip  # noqa: E402
from services import doi_tuong_gls as DT  # noqa: E402

BANG = {"khach": "customers", "ncc": "suppliers", "chu_xe": "owners"}


def _tim(db, loai, k):
    """→ (dòng danh mục chung gọn | None, cách tìm)."""
    if k.obj_id:
        return DT.mot(loai, k.obj_id), "obj_id"
    r = db.get(DoiTuongTune, (loai, k.id))
    if r is not None:
        g = DT.mot(loai, r.obj_id)
        if g is not None:
            return g, "đã gửi kế toán"
    if (k.code or "").strip():
        ma = k.code.strip().lower()
        g = next((x for x in DT.tim(loai, k.code.strip(), nho=False)["items"] if (x["code"] or "").lower() == ma), None)
        if g is not None:
            return g, "mã"
    return None, "—"


def _so_phieu(db, loai, k):
    if loai == "khach":
        return db.query(Trip).filter(Trip.customer_id == k.id).count()
    if loai == "chu_xe":
        return db.query(Trip).filter(Trip.owner_id == k.id).count()
    return 0


def doi_chieu(db, loai, ghi, tao):
    from sqlalchemy import inspect
    if "obj_id" not in {c["name"] for c in inspect(database.engine).get_columns(BANG[loai])}:
        sys.exit("Cột %s.obj_id chưa có — khởi động trang điều xe bản mới một lần (máy chủ tự thêm cột) rồi chạy lại." % BANG[loai])
    bang = DT.LOAI[loai]["bang"]
    dem = {"khop": 0, "chua_co": 0, "da_tao": 0, "trung": 0}
    dung = {}                                           # obj_id → hồ sơ đã nhận (một đối tượng chỉ một hồ sơ)
    ds = db.query(bang).order_by(bang.name).all()
    print("== %s: %d hồ sơ — %s" % (loai, len(ds), "GHI" + (" + TẠO trong danh mục chung" if tao else "") if ghi else "chỉ xem"))
    for k in ds:
        so_do = _so_phieu(db, loai, k)
        g, cach = _tim(db, loai, k)
        if g is None and tao:
            ma = (k.code or "").strip() or (DT.LOAI[loai]["tien_to"] + k.id)
            g = DT.mot(loai, DT.tao(loai, {"name": k.name, "phone": getattr(k, "phone", None), "address": getattr(k, "address", None),
                                           "cust_type": getattr(k, "cust_type", None)}, ma))
            cach = "TẠO MỚI"
            dem["da_tao"] += 1
        if g is None:
            dem["chua_co"] += 1
            print("  CHƯA CÓ  %-14s %-34s mã=%-22s phiếu=%d" % (k.id, (k.name or "")[:34], k.code, so_do))
            continue
        if g["obj_id"] in dung:
            dem["trung"] += 1
            print("  TRÙNG    %-14s %-34s → ObjId %s đã nhận cho %s — gộp tay rồi chạy lại"
                  % (k.id, (k.name or "")[:34], g["obj_id"], dung[g["obj_id"]]))
            continue
        dung[g["obj_id"]] = k.id
        dem["khop"] += 1
        doi = [o for o, v in (("name", g["name"]), ("phone", g["phone"]), ("address", g["address"]), ("code", g["code"]))
               if v and (getattr(k, o) or None) != v]
        print("  KHỚP     %-14s %-34s → ObjId %-6s %-22s (%s)%s phiếu=%d" % (
            k.id, (k.name or "")[:34], g["obj_id"], g["code"], cach, (" · khác: " + ", ".join(doi)) if doi else "", so_do))
        if ghi:
            k.obj_id = g["obj_id"]
            _doi, ten_cu = DT._chep(loai, k, g)
            db.flush()
            DT._theo_ten_chu_xe(db, loai, k, ten_cu)
            DT._nho_doi_tuong(db, loai, k)
    print("   Khớp %(khop)d · chưa có %(chua_co)d · tạo mới %(da_tao)d · trùng đối tượng %(trung)d" % dem
          + ("" if ghi else "  (chưa ghi — chạy lại với --ghi)"))


CACH_DUNG = "Cách dùng: doi_chieu_khach_gls.py [--loai khach|ncc|chu_xe|tat_ca] [--ghi [--tao]]"


def main():
    # tham số lạ / gõ thiếu (ví dụ "--lo") thì dừng — không lặng lẽ chạy loại mặc định
    thua = [a for i, a in enumerate(sys.argv[1:], 1) if a not in ("--ghi", "--tao", "--loai") and sys.argv[i - 1] != "--loai"]
    if thua or (sys.argv[-1] == "--loai"):
        sys.exit("Tham số không hiểu: %s\n%s" % (" ".join(thua) or "--loai (thiếu loại)", CACH_DUNG))
    ghi, tao = "--ghi" in sys.argv, "--tao" in sys.argv
    if tao and not ghi:
        sys.exit("--tao phải đi cùng --ghi.")
    loai = sys.argv[sys.argv.index("--loai") + 1] if "--loai" in sys.argv else "khach"
    cac = list(BANG) if loai == "tat_ca" else [loai]
    if any(x not in BANG for x in cac):
        sys.exit("--loai phải là khach · ncc · chu_xe · tat_ca.")
    db = database.SessionLocal()
    try:
        for x in cac:
            doi_chieu(db, x, ghi, tao)
            if ghi:
                db.commit()
    except HTTPException as e:
        db.rollback()
        sys.exit("Dừng — danh mục chung báo: %s" % (e.detail.get("loi") if isinstance(e.detail, dict) else e.detail))
    finally:
        db.close()


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""TÍNH SẴN BÁO CÁO KHI MÁY CHỦ KHỞI ĐỘNG (chủ dự án 24/09: "báo cáo mà chờ tận 1 phút cho 1 lần xem là quá lâu").

Báo cáo tháng ghép từ phần tính sẵn của từng NGÀY (services/dem_bao_cao). Phần của một ngày chỉ tính một lần rồi giữ
trong DB — nhưng lần ĐẦU TIÊN (vừa triển khai, hay bộ đệm bị xoá) thì phải tính cả 180 ngày của màn Tổng quan: trên dữ
liệu 4 năm mất gần một phút. Để không người dùng nào phải chờ lần đó, máy chủ vừa bật xong là tự tính trước — tháng
này và tháng trước của mọi báo cáo, sáu tháng của Tổng quan, nợ nhà cung cấp — trong một luồng riêng, không chặn yêu cầu
nào. Phần nào đã có trong DB thì lấy lại ngay (vài chục mili giây), nên khởi động lại máy chủ gần như không tốn gì.

Tắt bằng biến môi trường EPL_LAO_LAM_NONG=0 (ví dụ máy dev, bộ kiểm). Kết quả ghi vào logs/lam_nong.log.
"""
import datetime as dt
import logging
import os
import threading
import time

_nk = logging.getLogger("epl_lao.lam_nong")


class _Vai:
    """Vai Sếp: thấy mọi khoá — phần tính sẵn của từng ngày dùng chung cho mọi vai, vai chỉ bỏ khoá lúc trả về."""
    role, driver_id, full_name, place_id = "admin", None, "lam_nong", None


def _viec():
    import routes.bao_cao as B
    import routes.nha_cung_cap as N
    import routes.tat_toan as TT
    h = dt.date.today()
    nay = h.strftime("%Y-%m")
    truoc = (h.replace(day=1) - dt.timedelta(days=1)).strftime("%Y-%m")
    v = _Vai()
    ra = []
    for th in (nay, truoc):
        ra += [("tổng quan " + th, lambda db, th=th: B.tong_quan(thang=th, db=db, user=v)),
               ("xu hướng " + th, lambda db, th=th: B.xu_huong(thang=th, db=db, user=v)),
               ("tiền chuyến tài xế " + th, lambda db, th=th: B.tien_tai_xe(thang=th, db=db, user=v)),
               ("cấn trừ " + th, lambda db, th=th: B.can_tru(thang=th, db=db, user=v)),
               ("dòng tổng theo dõi " + th, lambda db, th=th: B.theo_doi_tong(thang=th, q=None, transport_status=None,
                                                                          finance_status=None, company=None, quy=None, db=db, user=v)),
               ("tất toán " + th, lambda db, th=th: TT.bang_ky(ky=th, chi_tiet=0, db=db, user=v))]
    ra.append(("nợ nhà cung cấp (mọi ngày)", lambda db: N.ds(db=db, user=v)))
    return ra


def lam_nong():
    from database import GOC_DU_AN, SessionLocal
    if not _nk.handlers:
        os.makedirs(os.path.join(GOC_DU_AN, "logs"), exist_ok=True)
        h = logging.FileHandler(os.path.join(GOC_DU_AN, "logs", "lam_nong.log"), encoding="utf-8")
        h.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        _nk.addHandler(h); _nk.setLevel(logging.INFO); _nk.propagate = False
    t_tong = time.time()
    for ten, f in _viec():
        db = SessionLocal()
        t0 = time.time()
        try:
            f(db)
            _nk.info("✓ %-32s %6.1f s", ten, time.time() - t0)
        except Exception as e:  # noqa: BLE001 — tính sẵn hỏng thì thôi, người dùng mở báo cáo sẽ tự tính như thường
            _nk.info("✗ %-32s %s", ten, str(e).splitlines()[0][:200])
        finally:
            db.rollback(); db.close()
    _nk.info("xong tính sẵn · %.1f s", time.time() - t_tong)


def bat_dau():
    """Gọi lúc máy chủ khởi động: tính sẵn trong một luồng riêng (không chặn khởi động, không chặn yêu cầu nào)."""
    if os.getenv("EPL_LAO_LAM_NONG", "1") == "0":
        return
    threading.Thread(target=lambda: (time.sleep(3), lam_nong()), name="lam-nong-bao-cao", daemon=True).start()


if __name__ == "__main__":        # chạy tay: python -m services.lam_nong  (trong backend/app)
    lam_nong()
    for dong in open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs", "lam_nong.log"),
                     encoding="utf-8").read().splitlines()[-15:]:
        print(dong)

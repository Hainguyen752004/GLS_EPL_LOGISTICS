# -*- coding: utf-8 -*-
"""Bộ giám sát: nhìn API EPL định kỳ, phát thông báo khi có gì MỚI xảy ra.

Bốn loại việc người quản lý muốn được báo ngay:
  · bao_gia_moi   — xuất hiện một báo giá mới
  · do_moi        — xuất hiện một lệnh giao hàng mới (khách vừa chấp nhận báo giá)
  · xe_xuat_phat  — một chuyến chuyển sang đang chạy (xe đã lăn bánh)
  · xe_hoan_tat   — một chuyến chuyển sang hoàn tất (xe đã báo xong), hoặc DO vừa được giao

Cách làm: cứ `CHU_KY` giây đọc lại ba danh sách (báo giá, DO, chuyến), so với lần trước
theo mã và trạng thái, phần chênh là thông báo. Lần đọc đầu chỉ chụp ảnh — không đổ cả lịch
sử ra thành thông báo lúc khởi động.

Kết quả đọc được đặt luôn vào bộ đệm của `cong_cu`, nên công cụ của tác tử gần như không
phải chờ API: bộ giám sát đã làm nóng sẵn.

Thông báo là DỮ LIỆU CÓ CẤU TRÚC (loại, mã, xe, khách…), không phải câu chữ — trình duyệt
tự ghép câu theo ngôn ngữ người xem đang chọn.
"""
import datetime as dt
import sys
import threading
import time
from collections import deque

import cong_cu

CHU_KY = 15
GIU_TOI_DA = 300

_su_kien = deque(maxlen=GIU_TOI_DA)
_khoa = threading.Lock()
_bo_dem_id = 0
_anh_truoc = None          # (bao_gia: {id: status}, do: {id: status}, chuyen: {id: status})
_lan_doc_cuoi = None
_loi_cuoi = None


def _bay_gio():
    return dt.datetime.now(cong_cu.VN).isoformat(timespec="seconds")


def _them(loai, **du_lieu):
    global _bo_dem_id
    with _khoa:
        _bo_dem_id += 1
        _su_kien.append({"id": _bo_dem_id, "luc": _bay_gio(), "loai": loai, **du_lieu})


def chup_anh():
    """Đọc ba danh sách, trả (ảnh trạng thái, dữ liệu thô) — và làm nóng bộ đệm công cụ."""
    bao_gia = cong_cu._lay_het("/api/quotations")
    do = cong_cu._lay_het("/api/delivery-orders")
    chuyen = cong_cu._lay_het("/api/tms/trips")
    with cong_cu._khoa_dem:
        t = time.time()
        cong_cu._dem["bao_gia"] = (t, bao_gia)
        cong_cu._dem["do"] = (t, do)
        cong_cu._dem["chuyen"] = (t, chuyen)
    anh = ({q.get("id"): (q.get("canonical_status") or "") for q in bao_gia},
           {d.get("id"): (d.get("canonical_status") or "") for d in do},
           {t.get("id"): (t.get("status") or "") for t in chuyen})
    return anh, (bao_gia, do, chuyen)


def so_sanh(truoc, sau, tho):
    """Trả danh sách thông báo từ hai ảnh. Tách riêng để kiểm được không cần API."""
    bg_truoc, do_truoc, ch_truoc = truoc
    bg_sau, do_sau, ch_sau = sau
    bao_gia, do, chuyen = tho
    ra = []
    theo_ma_bg = {q.get("id"): q for q in bao_gia}
    theo_ma_do = {d.get("id"): d for d in do}
    try:
        ten_khach = cong_cu._khach_hang_ten()
    except cong_cu.LoiAPI:
        ten_khach = {}

    for ma in bg_sau:
        if ma not in bg_truoc:
            q = theo_ma_bg.get(ma, {})
            ra.append(dict(loai="bao_gia_moi", ma=ma, khach=ten_khach.get(q.get("customer_id"), q.get("customer_id")),
                           tuyen=q.get("origin") or q.get("route_id"), gia=q.get("selling_price"),
                           tien_te=q.get("currency_code"), trang_thai=q.get("canonical_status")))
    for ma in do_sau:
        if ma not in do_truoc:
            d = theo_ma_do.get(ma, {})
            ra.append(dict(loai="do_moi", ma=ma, khach=ten_khach.get(d.get("customer_id"), d.get("customer_id")),
                           tuyen=d.get("origin") or d.get("route_id"), bao_gia=d.get("quotation_id"),
                           han_giao=d.get("delivery_window_end")))
        elif do_truoc[ma] != do_sau[ma] and do_sau[ma] == "delivered":
            d = theo_ma_do.get(ma, {})
            ra.append(dict(loai="do_giao_xong", ma=ma, khach=ten_khach.get(d.get("customer_id"), d.get("customer_id")),
                           xe=d.get("vehicle_id"), tai_xe=d.get("driver_id")))
    for t in chuyen:
        ma = t.get("id")
        cu, moi = ch_truoc.get(ma), ch_sau.get(ma)
        if cu is None or cu == moi:
            continue
        chung = dict(ma=ma, xe=t.get("vehicle_id"), tai_xe=t.get("driver_id"),
                     do_ids=t.get("delivery_order_ids") or [],
                     khach=", ".join(sorted({ten_khach.get(theo_ma_do.get(x, {}).get("customer_id"), "") or ""
                                             for x in (t.get("delivery_order_ids") or [])} - {""})))
        if moi == "in_transit":
            ra.append(dict(loai="xe_xuat_phat", **chung))
        elif moi == "completed":
            ra.append(dict(loai="xe_hoan_tat", **chung))
    return ra


def _vong():
    global _anh_truoc, _lan_doc_cuoi, _loi_cuoi
    while True:
        try:
            anh, tho = chup_anh()
            if _anh_truoc is not None:
                for sk in so_sanh(_anh_truoc, anh, tho):
                    _them(**sk)
                    sys.stdout.write("  ! %s %s\n" % (sk["loai"], sk.get("ma")))
            _anh_truoc = anh
            _lan_doc_cuoi = _bay_gio()
            _loi_cuoi = None
        except Exception as loi:                       # mất API một lúc thì thử lại, không chết
            _loi_cuoi = str(loi)[:200]
            sys.stdout.write("  ! giám sát lỗi: %s\n" % _loi_cuoi)
        sys.stdout.flush()
        time.sleep(CHU_KY)


def bat_dau():
    threading.Thread(target=_vong, name="canh-bao", daemon=True).start()


def lay(sau_id=0, toi_da=50):
    with _khoa:
        ds = [s for s in _su_kien if s["id"] > int(sau_id or 0)][-toi_da:]
        moi_nhat = _bo_dem_id
    return {"su_kien": ds, "moi_nhat": moi_nhat, "lan_doc_cuoi": _lan_doc_cuoi, "loi": _loi_cuoi,
            "chu_ky_giay": CHU_KY}

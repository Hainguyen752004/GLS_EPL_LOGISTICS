# -*- coding: utf-8 -*-
"""CHUYỂN TỒN ĐẦU từ KHO TẠM (EPL_KETOAN, bản sao epl_ketoan_d<số> — CHỈ ĐỌC) sang KHO QLSX anh Tune — chủ dự án duyệt 05/10.

    python tools/may_thu/chuyen_ton_dau_qlsx.py                       = --chi-in: liệt kê tồn + giá vốn từng kho × mặt hàng, KHÔNG gọi gì
    python tools/may_thu/chuyen_ton_dau_qlsx.py --that                gọi stock-receipts (DocTypeId 53) cho mỗi dòng tồn > 0
    python tools/may_thu/chuyen_ton_dau_qlsx.py --hang-khach          liệt kê sổ HÀNG KHÁCH GỬI ở bãi (quặng, không phải tài sản kho EPL)
    python tools/may_thu/chuyen_ton_dau_qlsx.py --hang-khach --that   chép sổ đó về goods_moves của trang điều xe (bản sao epl_lao_d<số>)

Tham số: --ngay YYYY-MM-DD (ngày chứng từ + hậu tố SourceRef, mặc định hôm nay) · --api URL (gốc API anh Tune, mặc định QLSX_BASE_URL
hoặc http://127.0.0.1:5090) · --url-kt / --url-lao (tệp chứa chuỗi nối, mặc định .may_thu/url_epl_ketoan_d7.txt · url_epl_lao_d7.txt).

  · Dầu: tồn từng kho EPL (fuel_places.owner_type = epl) và giá vốn BÌNH QUÂN di động — chép đúng thuật toán kho tạm
    (EPL_KETOAN services/gia_von_dau.py: theo ngày, giờ tạo, mã; dòng không ghi kho thuộc KHO-TB). Mã hàng EPLNL-diesel, mã kho = code.
  · Phụ tùng: parts.qty × parts.unit_price (bình quân kho tạm) → mã EPLPT-<parts.id>, kho KHO-PT (KHO_PT_MA).
  · Mỗi dòng một phiếu nhập: SourceRef = Idempotency-Key = EPLTD-<kho>-<mã hàng>-<yyyymmdd>. Gọi lại an toàn — bên kia trả bản cũ (replayed).
  · Hàng khách gửi: mọi dòng goods_moves bên kho tạm của các DO có ở trang điều xe; DO nào trang điều xe đã có dòng sổ thì bỏ qua (gọi lại
    không chép trùng).
Chỉ chạy khi chuỗi nối trỏ bản sao (tên DB …_d<số>). Dừng ngay ở dòng hỏng, in rõ dòng + lỗi.
"""
import argparse
import datetime as dt
import os
import re
import sys

GOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass


def _url(tep):
    u = open(tep, encoding="utf-8").read().strip()
    if not re.search(r"_d\d+$", u.rsplit("/", 1)[-1].split("?")[0]):
        sys.exit("Chuỗi nối trong %s không trỏ bản sao (…_d<số>) — dừng." % tep)
    return u


def _chay(ds):
    """(lít, giá bình quân LAK/lít) — y hệt gia_von_dau._chay của kho tạm."""
    lit, gia_tri, gia = 0.0, 0.0, 0.0
    for m in ds:
        n = m["qty_l"] or 0
        if m["kind"] == "in":
            g = m["unit_cost_lak"] if m["unit_cost_lak"] is not None else ((m["unit_price"] or 0) if (m["currency"] or "LAK").upper() == "LAK" else 0.0)
            lit += n; gia_tri += n * g
            gia = gia_tri / lit if lit > 0 else g
        else:
            lit -= n; gia_tri -= n * gia
            if lit <= 0.0001:
                gia_tri = 0.0
    return round(lit, 3), round(gia, 2)


def ton_kho_tam(c, kho_pt):
    from sqlalchemy import text
    kho = {r.id: r for r in c.execute(text("select id, code, name from fuel_places where owner_type = 'epl' order by code"))}
    goc = next((k for k, r in kho.items() if r.code == "KHO-TB"), next(iter(kho), None))
    nhom = {}
    for m in c.execute(text("select kind, qty_l, unit_price, currency, unit_cost_lak, place_id from fuel_moves "
                            "order by move_date, created_at asc nulls first, id")).mappings():
        nhom.setdefault(m["place_id"] or goc, []).append(m)
    ra = []
    for pid, ds in nhom.items():
        lit, gia = _chay(ds)
        if pid in kho and lit > 0.0005:
            ra.append({"kho": kho[pid].code, "hang": "EPLNL-diesel", "ten": "Dầu diesel · " + kho[pid].name, "sl": lit, "gia": gia})
    for p in c.execute(text("select id, name, qty, unit_price from parts where coalesce(qty, 0) > 0 order by name")):
        ra.append({"kho": kho_pt, "hang": "EPLPT-" + p.id, "ten": p.name, "sl": round(float(p.qty), 3), "gia": round(float(p.unit_price or 0), 2)})
    return sorted(ra, key=lambda x: (x["kho"], x["hang"]))


def hang_khach(c_kt, c_lao):
    from sqlalchemy import text
    co = {r[0] for r in c_lao.execute(text("select id from trips"))}
    da = {r[0] for r in c_lao.execute(text("select distinct trip_id from goods_moves where trip_id is not null"))}
    ra, bo = [], set()
    for m in c_kt.execute(text("select * from goods_moves order by move_date, created_at, id")).mappings():
        if m["trip_id"] not in co or (m["lo_trip_id"] and m["lo_trip_id"] not in co):
            bo.add(m["trip_doc_no"]); continue
        if m["trip_id"] in da:
            continue
        ra.append(dict(m))
    return ra, sorted(x for x in bo if x)


def main():
    ap = argparse.ArgumentParser(description="Chuyển tồn đầu kho tạm → kho QLSX anh Tune (mặc định chỉ liệt kê).")
    ap.add_argument("--chi-in", action="store_true", help="chỉ liệt kê (mặc định)")
    ap.add_argument("--that", action="store_true", help="ghi thật")
    ap.add_argument("--hang-khach", action="store_true", help="sổ hàng khách gửi ở bãi thay vì tồn kho EPL")
    ap.add_argument("--ngay", default=dt.date.today().isoformat())
    ap.add_argument("--api", default=os.getenv("QLSX_BASE_URL") or "http://127.0.0.1:5090")
    ap.add_argument("--url-kt", default=os.path.join(GOC, ".may_thu", "url_epl_ketoan_d7.txt"))
    ap.add_argument("--url-lao", default=os.path.join(GOC, ".may_thu", "url_epl_lao_d7.txt"))
    a = ap.parse_args()
    that = a.that and not a.chi_in
    ngay = dt.date.fromisoformat(a.ngay)
    from sqlalchemy import create_engine, text
    kt = create_engine(_url(a.url_kt), connect_args={"options": "-c default_transaction_read_only=on"})

    if a.hang_khach:
        lao = create_engine(_url(a.url_lao))
        with kt.connect() as ck, lao.connect() as cl:
            ds, bo = hang_khach(ck, cl)
            print("SỔ HÀNG KHÁCH GỬI kho tạm → goods_moves trang điều xe: %d dòng%s" % (len(ds), " (GHI THẬT)" if that else " (chỉ liệt kê)"))
            for m in ds:
                print("  %s  %-4s %-16s lô %-12s %8.3f t  %s" % (m["move_date"], m["kind"], m["trip_doc_no"] or "", m["lo_trip_id"] or "",
                                                               m["qty_t"], m["goods_name"]))
            if bo:
                print("  bỏ qua (DO không có ở trang điều xe): %s" % ", ".join(bo))
            if that and ds:
                # kết nối đã tự mở giao dịch lúc đọc (autobegin) — ghi trong chính giao dịch đó rồi commit một lần
                for m in ds:
                    cl.execute(text("insert into goods_moves (id, move_date, kind, goods_name, qty_t, trip_id, trip_doc_no, lo_trip_id, depot, "
                                    "note, by_user, created_at) values (:id, :move_date, :kind, :goods_name, :qty_t, :trip_id, :trip_doc_no, "
                                    ":lo_trip_id, :depot, :note, :by_user, :created_at) on conflict (id) do nothing"),
                               {k: m.get(k) for k in ("id", "move_date", "kind", "goods_name", "qty_t", "trip_id", "trip_doc_no", "lo_trip_id",
                                                      "depot", "note", "by_user", "created_at")})
                cl.commit()
                print("ĐÃ CHÉP %d dòng." % len(ds))
        return

    kho_pt = (os.getenv("KHO_PT_MA") or "KHO-PT").strip()
    with kt.connect() as ck:
        ds = ton_kho_tam(ck, kho_pt)
    print("TỒN ĐẦU kho tạm → kho QLSX (DocTypeId 53, ngày %s)%s" % (ngay, " — GHI THẬT vào %s" % a.api if that else " — chỉ liệt kê"))
    print("  %-10s %-24s %12s %14s %16s  %s" % ("Kho", "Mã hàng", "Số lượng", "Giá vốn BQ", "Thành tiền LAK", "SourceRef"))
    for x in ds:
        x["sr"] = "EPLTD-%s-%s-%s" % (x["kho"], x["hang"], ngay.strftime("%Y%m%d"))
        print("  %-10s %-24s %12s %14s %16s  %s · %s" % (x["kho"], x["hang"], "{:,.3f}".format(x["sl"]), "{:,.2f}".format(x["gia"]),
                                                    "{:,.0f}".format(x["sl"] * x["gia"]), x["sr"], x["ten"]))
    print("  Tổng giá trị: %s LAK · %d dòng" % ("{:,.0f}".format(sum(x["sl"] * x["gia"] for x in ds)), len(ds)))
    if not that:
        return
    os.environ["QLSX_BASE_URL"] = a.api
    os.environ.setdefault("EPL_ACC_CODE_API", a.api)
    os.environ["DATABASE_URL"] = _url(a.url_lao)            # module trang điều xe cần chuỗi nối khi nạp; công cụ không ghi DB này
    sys.path.insert(0, os.path.join(GOC, "backend", "app"))
    import database  # noqa: F401  (nạp .env: tài khoản tích hợp QLSX)
    os.environ["QLSX_BASE_URL"] = a.api
    from fastapi import HTTPException
    from services import kho_qlsx as KQ
    for x in ds:
        try:
            r = KQ.nhap(x["sr"], [{"ItemCode": x["hang"], "WarehouseCode": x["kho"], "Qty": x["sl"], "UnitCost": x["gia"]}], loai=53, ngay=ngay,
                        mo_ta="Tồn đầu chuyển từ kho tạm EPL · %s" % x["ten"])
        except HTTPException as e:
            sys.exit("DỪNG ở %s / %s: %s" % (x["kho"], x["hang"], e.detail))
        print("  ✓ %s → %s%s" % (x["sr"], (r or {}).get("documentNo"), " (đã có — trả bản cũ)" if (r or {}).get("replayed") else ""))
    print("XONG — %d phiếu nhập tồn đầu." % len(ds))


if __name__ == "__main__":
    main()

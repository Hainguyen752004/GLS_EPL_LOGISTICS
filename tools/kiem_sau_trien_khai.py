# -*- coding: utf-8 -*-
"""KIỂM SAU TRIỂN KHAI — hệ kế toán anh Tune (GLS-QLSX API) ↔ trang điều xe EPL Lào. CHỈ ĐỌC.

    python -X utf8 tools/kiem_sau_trien_khai.py <API anh Tune> <trang điều xe>
    python -X utf8 tools/kiem_sau_trien_khai.py https://demo-lao-api.goldensme.com https://<trang điều xe>
    python -X utf8 tools/kiem_sau_trien_khai.py http://127.0.0.1:5090 http://127.0.0.1:8011        # máy thử

Chỉ gửi GET. Hai lệnh POST duy nhất là ĐĂNG NHẬP, không tạo gì:
  * `POST /api/v1/auth/login` bên anh Tune — chỉ khi có QLSX_USERNAME / QLSX_PASSWORD (kiểm tài khoản tích hợp);
  * `POST /api/dang-nhap` bên trang điều xe — chỉ khi có KIEM_SEP_TEN / KIEM_SEP_MAT_KHAU.
Không tạo phiếu, không gửi SO, không sửa danh mục, không tạo khoá.

Biến môi trường, hoặc dòng KEY=giá_trị trong `.env` của EPL_LAO_REAL (đổi tệp bằng --env). KHÔNG in giá trị nào:
  QLSX_ACCESS_TOKEN                          token API anh Tune đặt tay (ưu tiên 1 — cùng thứ tự với trang điều xe)
  QLSX_USERNAME / QLSX_PASSWORD / QLSX_ORG_ID  tài khoản tích hợp (ưu tiên 2; có thì kiểm đăng nhập)
  EPL_ACC_CODE_TOKEN                         token đang mượn (ưu tiên 3)
  QLSX_TIEN_USD                              mã tiền USD đặt tay khi USD đang tắt bên kế toán
  QLSX_DOTY_CHI_TAM_UNG, QLSX_DOTY_CHI_KHAC, QLSX_DOTY_THU_KHAC   mã loại chứng từ nếu DB host khác 59 / 60 / 17
  KIEM_SEP_TEN / KIEM_SEP_MAT_KHAU           (tuỳ chọn) tài khoản Sếp trang điều xe → trạng thái bàn giao, máy đang gửi sang
  KIEM_PHIEN_SEP                             (tuỳ chọn) phiên Sếp có sẵn, thay cho tên + mật khẩu
  KIEM_KHOA_BAN_GIAO                         (tuỳ chọn) khoá bàn giao (= LogisticsSource:ApiKey) → đọc thẳng danh sách DO

Tham số --dot-1: đợt 1, CHƯA đặt LogisticsSource — API (từ commit ce95b3c) trả 503 "chưa cấu hình nguồn Logistics" cho DO là
ĐÚNG; các dòng cần DO thì bỏ qua.

Không theo chuyển hướng, giống API anh Tune (`AllowAutoRedirect = false`): địa chỉ chuyển hướng là báo SAI.
Thoát mã 0 khi không có dòng SAI, 1 khi có. Hướng dẫn: DOCS/md/HUONG_DAN_TRIEN_KHAI_ANH_TUNE.md, mục 8.
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from urllib.parse import urlsplit

GOC_DU_AN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIEN_TO_DO = "EPLLAO-"                     # services/ban_giao.py — DO của trang điều xe Lào
MA_CON = ("1371", "4021", "4022")          # ba mã con anh Khampla, mở 01/10 (hợp đồng 12.12.1)
MA_TONG_HOP = ("137", "402")               # cha của ba mã con: phải là tài khoản tổng hợp
# mã bên em dùng: phiếu chi / thu (tiền 1011 · 1012 · 1021 · 1022, tạm ứng 1601, chủ xe 4022, NCC 4021, mục V 614, mục VI 625)
# + bút toán chờ gửi (thuê xe 621/4022, ghi nợ NCC 625 · 614/4021, quyết toán tạm ứng 625/1601)
MA_PHIEU_CHI = ("1011", "1012", "1021", "1022", "1601", "4021", "4022", "614", "621", "625")
CHO_GIAY = 20
TU_KHOA_KHONG_CO = "kiem-khong-co-zq9"     # tìm chữ này phải ra 0 dòng: Total đúng sau lọc

DONG = []                                  # (kết quả, việc kiểm, chi tiết, hướng sửa)


# ---------------------------------------------------------------- cấu hình
def doc_env(tep):
    kq = {}
    if tep and os.path.isfile(tep):
        for d in open(tep, encoding="utf-8-sig"):
            d = d.strip()
            if not d or d.startswith("#") or "=" not in d:
                continue
            k, v = d.split("=", 1)
            kq[k.strip()] = v.strip().strip('"').strip("'")
    return kq


class CauHinh:
    def __init__(self, tep):
        self._tep = doc_env(tep)

    def __call__(self, ten, giu_nguyen=False):
        v = os.getenv(ten)
        if v is None:
            v = self._tep.get(ten)
        v = v or ""
        return v if giu_nguyen else v.strip()

    def so(self, ten, mac_dinh):
        v = self(ten)
        return int(v) if v.isdigit() else mac_dinh


# ---------------------------------------------------------------- HTTP (không theo chuyển hướng)
class _KhongChuyenHuong(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None                        # 30x về thẳng thành HTTPError


_MO = urllib.request.build_opener(_KhongChuyenHuong)


def goi(method, url, token=None, body=None):
    """→ (http | None, thân json | None, giây, lỗi mạng | None, Location khi 30x). Không ném lỗi."""
    dau = {"Accept": "application/json", "User-Agent": "EPL-LAO-kiem-sau-trien-khai/1.0"}
    du = None
    if body is not None:
        du = json.dumps(body, ensure_ascii=False).encode("utf-8")
        dau["Content-Type"] = "application/json"
    if token:
        dau["Authorization"] = "Bearer " + token
    t0 = time.time()
    try:
        with _MO.open(urllib.request.Request(url, data=du, method=method, headers=dau), timeout=CHO_GIAY) as r:
            ma, tho, toi = r.status, r.read(), None
    except urllib.error.HTTPError as e:
        ma, tho, toi = e.code, e.read() or b"", e.headers.get("Location")
    except Exception as e:                                          # noqa: BLE001 — mất mạng, DNS, SSL, hết giờ
        return None, None, time.time() - t0, "%s: %s" % (type(e).__name__, str(e)[:160]), None
    try:
        than = json.loads(tho.decode("utf-8", "replace")) if tho.strip() else None
    except ValueError:
        than = None
    return ma, than, time.time() - t0, None, toi


def doc_tune(api, duong, token):
    """GET một đường bên anh Tune, bóc phong bì {Success, Result}. → (Result | None, câu lỗi | None, http)."""
    ma, than, _, loi, toi = goi("GET", api + duong, token)
    if loi:
        return None, "không gọi được: " + loi, None
    if ma in (301, 302, 303, 307, 308):
        return None, "HTTP %s chuyển hướng tới %s" % (ma, toi), ma
    if ma == 401:
        return None, "HTTP 401 — token sai hoặc đã hết hạn", ma
    if isinstance(than, dict) and than.get("Success") is True:
        return than.get("Result"), None, ma
    cau = than.get("Message") if isinstance(than, dict) else ""
    return None, "HTTP %s%s" % (ma, (" — " + str(cau)[:160]) if cau else ""), ma


def ghi(kq, viec, chi_tiet="", sua=""):
    DONG.append((kq, viec, chi_tiet, sua))


def so(n):
    return "{:,}".format(n).replace(",", ".")


# ---------------------------------------------------------------- phía trang điều xe: đọc trước (dùng cho câu sửa)
def do_dieu_xe(dx):
    """Trang điều xe có trả lời không, có đường bàn giao + tham số q không (openapi). Ghi dòng ở phần B."""
    ra = {"song": False, "co_q": None}
    ma, than, giay, loi, toi = goi("GET", dx + "/api/suc-khoe")
    if loi:
        ra["loi_song"] = ("SAI", "không gọi được: " + loi,
                          "Trang điều xe tắt hoặc sai địa chỉ / cổng. Bên em kiểm tiến trình trang điều xe.")
    elif ma in (301, 302, 303, 307, 308):
        ra["loi_song"] = ("SAI", "HTTP %s chuyển hướng tới %s" % (ma, toi),
                          "API anh Tune không theo chuyển hướng. LogisticsSource:BaseUrl phải là địa chỉ CUỐI (thường là "
                          "https://…/api/).")
    elif ma == 200 and isinstance(than, dict):
        ra["song"] = True
        ra["loi_song"] = ("✓" if than.get("ok") else "SAI",
                          "HTTP 200, %s giây, DB %s %s" % (("%.2f" % giay).replace(".", ","), than.get("db") or "?", "trả lời" if than.get("ok") else "KHÔNG trả lời"),
                          "" if than.get("ok") else "Trang điều xe chạy nhưng không nối được PostgreSQL — bên em kiểm DATABASE_URL.")
    else:
        ra["loi_song"] = ("SAI", "HTTP %s" % ma, "Địa chỉ này không phải trang điều xe EPL Lào (không có /api/suc-khoe).")
    if ra["song"]:
        ma, than, _, loi, _ = goi("GET", dx + "/openapi.json")
        if ma == 200 and isinstance(than, dict) and isinstance(than.get("paths"), dict):
            p = than["paths"]
            ds = (p.get("/api/handover/delivery-orders") or {}).get("get")
            ra["co_ban_giao"] = bool(ds) and "/api/handover/delivery-orders/{do_id}" in p
            ra["co_q"] = bool(ds) and "q" in [x.get("name") for x in ds.get("parameters", []) if isinstance(x, dict)]
    return ra


# ---------------------------------------------------------------- A. API anh Tune
def _bo_dong_do(ctx, ly_do):
    """Hai dòng cần danh sách DO của trang điều xe Lào: bỏ qua, giữ số thứ tự dòng như lần chạy đủ."""
    for v in ("Vụ việc: đọc DO từ trang điều xe", "Tìm DO theo từ khoá → SearchScope ALL"):
        ghi("--", v, ly_do, "")
    return ctx


def kiem_api(api, cfg, dx_info, tu_khoa, dot_1=False):
    ctx = {}
    # A1 — API sống: GetAllCurrency không đòi token
    ma, than, giay, loi, toi = goi("GET", api + "/api/v1/common/GetAllCurrency")
    if loi:
        ghi("SAI", "API anh Tune trả lời", "không gọi được: " + loi,
            "Site IIS DemoLao_API chưa chạy, sai địa chỉ hoặc chứng chỉ https. IIS Manager → Sites → Start; Application "
            "Pools → Recycle; xem log stdout / Event Viewer (mục 9).")
        return ctx
    if ma in (301, 302, 303, 307, 308):
        ghi("SAI", "API anh Tune trả lời", "HTTP %s chuyển hướng tới %s" % (ma, toi),
            "Dùng đúng địa chỉ cuối của API (https://…), không qua chuyển hướng.")
        return ctx
    if not (isinstance(than, dict) and than.get("Success") is True):
        ghi("SAI", "API anh Tune trả lời", "HTTP %s, thân không đúng phong bì {Success, Result}" % ma,
            "Địa chỉ này không phải API GLS-QLSX, hoặc site lỗi khởi động (500.30). Xem log site.")
        return ctx
    ghi("✓", "API anh Tune trả lời", "HTTP 200, %s giây" % ("%.2f" % giay).replace(".", ","))
    tien = than.get("Result") or []

    # A2 — token / tài khoản tích hợp (cùng thứ tự với trang điều xe: tay → tích hợp → mượn)
    tay = cfg("QLSX_ACCESS_TOKEN")
    ten, mk = cfg("QLSX_USERNAME"), cfg("QLSX_PASSWORD", giu_nguyen=True)
    tk_tich_hop = None
    if ten and mk:
        org = cfg.so("QLSX_ORG_ID", 1368)
        ma, than, _, loi, _ = goi("POST", api + "/api/v1/auth/login", body={"Username": ten, "Password": mk, "OrgID": org})
        kq = than.get("Result") if isinstance(than, dict) and than.get("Success") is True else None
        if isinstance(kq, str) and kq:
            tk_tich_hop = kq
            ghi("✓", "Đăng nhập tài khoản tích hợp", "tài khoản %s, chi nhánh %d — đăng nhập được" % (ten, org))
        else:
            cau = loi or (than.get("Message") if isinstance(than, dict) else "HTTP %s" % ma)
            ghi("SAI", "Đăng nhập tài khoản tích hợp", "tài khoản %s: %s" % (ten, str(cau)[:120]),
                "Sai tên / mật khẩu / OrgID, hoặc tài khoản chưa có trên DB host (mục 6). Kiểm QLSX_USERNAME, QLSX_PASSWORD, "
                "QLSX_ORG_ID trong .env trang điều xe.")
    token = tay or tk_tich_hop or cfg("EPL_ACC_CODE_TOKEN")
    ctx["nguon_token"] = ("QLSX_ACCESS_TOKEN" if tay else "tài khoản tích hợp %s" % ten if tk_tich_hop
                          else "EPL_ACC_CODE_TOKEN" if token else "không có")
    if not (ten and mk):
        ghi("--", "Đăng nhập tài khoản tích hợp", "chưa đặt QLSX_USERNAME / QLSX_PASSWORD — đang dùng %s" % ctx["nguon_token"],
            "Tạo tài khoản tích hợp theo mục 6, đặt hai biến vào .env trang điều xe trước 10/10 (token cá nhân hết hạn).")
    if not token:
        ghi("SAI", "Có token gọi API anh Tune", "không có QLSX_ACCESS_TOKEN, tài khoản tích hợp hay EPL_ACC_CODE_TOKEN",
            "Đặt một trong ba cách lấy token (biến môi trường hoặc .env) rồi chạy lại.")
        return ctx

    # A3 — danh mục quốc gia 11 (cùng đường trang điều xe đọc, EPL_ACC_CODE_API)
    r, loi, ma = doc_tune(api, "/api/v1/common/country-accounts?tryAutoId=11&onlyActive=true", token)
    if r is None:
        sua = ("Token %s sai hoặc hết hạn: lấy token mới / dùng tài khoản tích hợp (mục 6)." % ctx["nguon_token"]
               if ma == 401 else "Xem log API; đường common/country-accounts phải có trên bản host.")
        ghi("SAI", "Danh mục tài khoản quốc gia 11", loi, sua)
        if ma == 401:
            return ctx
    else:
        d = {str(x.get("AccCode") or "").strip(): x for x in r if isinstance(x, dict)}
        thieu = [m for m in MA_CON if m not in d]
        khong_la = [m for m in MA_CON if m in d and not d[m].get("AccAccountWrite")]
        van_la = [m for m in MA_TONG_HOP if m in d and d[m].get("AccAccountWrite")]
        chi = "%d mã; 1371 · 4021 · 4022 %s; 137 · 402 %s" % (
            len(d), "có" if not thieu else "THIẾU " + ", ".join(thieu),
            "là tổng hợp" if not van_la else "VẪN hạch toán: " + ", ".join(van_la))
        if thieu:
            ghi("SAI", "Danh mục tài khoản quốc gia 11", chi,
                "DB host chưa có ba mã con (494 mã là DB khác bản ở máy). Chạy: python tools/mo_ma_con_tune.py %s "
                "(mục 5) — lệnh GHI, cần chủ dự án cho phép." % api)
        elif khong_la or van_la:
            ghi("SAI", "Danh mục tài khoản quốc gia 11", chi + ("; mã con không hạch toán: " + ", ".join(khong_la) if khong_la else ""),
                "Cây mã chưa đúng: 137 / 402 phải Posting=false, 1371 / 4021 / 4022 Posting=true (mục 5).")
        else:
            ghi("✓", "Danh mục tài khoản quốc gia 11", chi)

    # A4 — danh mục hạch toán phiếu thu chi (đường kiểm tài khoản lúc lưu phiếu)
    r, loi, ma = doc_tune(api, "/api/v1/accounting/cmpayment-receipt/country-accounts?countryId=11", token)
    if r is None:
        ghi("SAI", "Mã hạch toán được trên phiếu chi", loi, "Xem log API (cmpayment-receipt/country-accounts).")
    else:
        co = {str(x.get("AccCode") or x.get("ACC_CODE") or "").strip() for x in r if isinstance(x, dict)}
        thieu = [m for m in MA_PHIEU_CHI if m not in co]
        ghi("SAI" if thieu else "✓", "Mã hạch toán được trên phiếu chi",
            "%d mã hạch toán; %s" % (len(co), ("thiếu " + ", ".join(thieu)) if thieu else "đủ " + " · ".join(MA_PHIEU_CHI)),
            ("Phiếu chi dùng các mã này sẽ bị từ chối \"tài khoản không hợp lệ theo quốc gia\". Mở mã thiếu (mục 5)."
             if thieu else ""))

    # A5 — loại chứng từ: 58 chi công nợ (WEB), 59 Chi trước (tạm ứng), 60 Chi khác (trả chủ xe, mục V–VI, NCC, tất toán chi bù),
    # 17 Thu khác (tất toán: tài xế nộp lại). 58 / 59 / 60 phải là loại CHI (CMP), 17 là loại THU (CMR).
    r, loi, ma = doc_tune(api, "/api/v1/accounting/cmpayment-receipt/document-types?voucherType=ALL", token)
    chi_khac = cfg.so("QLSX_DOTY_CHI_KHAC", cfg.so("QLSX_DOTY_TRA_CHU_XE", 60))
    can = [(58, "DOTY_ISCMP"), (cfg.so("QLSX_DOTY_CHI_TAM_UNG", 59), "DOTY_ISCMP"), (chi_khac, "DOTY_ISCMP"),
           (cfg.so("QLSX_DOTY_THU_KHAC", 17), "DOTY_ISCMR")]
    viec = "Loại chứng từ %s" % " / ".join(str(k) for k, _ in can)
    if r is None:
        ghi("SAI", viec, loi, "Xem log API (document-types).")
    else:
        by = {}
        for x in r if isinstance(r, list) else []:
            try:
                by[int(x.get("DOTY_AUTOID"))] = x
            except (TypeError, ValueError):
                pass
        sai = [k for k, co in can if k not in by or not by[k].get(co)]
        ghi("SAI" if sai else "✓", viec,
            " · ".join("%d %s" % (k, by[k].get("DOTY_NAME") if k in by else "KHÔNG CÓ") for k, _ in can),
            ("DB host đánh số loại chứng từ khác (hoặc sai loại thu / chi). Báo bên em mã đúng để đặt QLSX_DOTY_CHI_TAM_UNG / "
             "QLSX_DOTY_CHI_KHAC / QLSX_DOTY_THU_KHAC; WEB phân loại theo 58 / 60 và 15 / 17 (mục 8.4)." if sai else ""))

    # A6 — tiền: LAK bật, USD bật hoặc đặt tay
    ten_tien = {str(c.get("CUR_NAME") or "").upper(): c for c in tien if isinstance(c, dict)}
    # Trang điều xe tra mã tiền theo tên ở GetAllCurrency (chỉ trả tiền ĐANG BẬT); tiền đang tắt thì đặt tay QLSX_TIEN_<MÃ>.
    phan, thieu = [], []
    for ma_tien in ("LAK", "USD"):
        c, tay = ten_tien.get(ma_tien), cfg("QLSX_TIEN_%s" % ma_tien)
        if c:
            phan.append("%s mã %s đang bật" % (ma_tien, c.get("CUR_AUTOID")))
        elif tay.isdigit():
            phan.append("%s đang TẮT, trang điều xe dùng tạm QLSX_TIEN_%s=%s" % (ma_tien, ma_tien, tay))
        else:
            phan.append("%s KHÔNG có trong tiền đang bật" % ma_tien)
            thieu.append(ma_tien)
    ghi("SAI" if thieu else "✓", "Tiền tệ LAK / USD", "; ".join(phan) + ("" if not thieu else " (đang bật: %s)" % (", ".join(ten_tien) or "—")),
        "" if not thieu else ("Bật %s trong danh mục tiền tệ bên hệ kế toán (LAK: phiếu chi tạm ứng, trả chủ xe; USD: cước USD), "
                              "hoặc bên em đặt tạm QLSX_TIEN_<MÃ>=<CUR_AUTOID> trong .env trang điều xe (mục 4.3)." % " và ".join(thieu)))
    lak = ten_tien.get("LAK")
    ctx["lak"] = lak.get("CUR_AUTOID") if lak else (cfg.so("QLSX_TIEN_LAK", 0) or None)

    # A7 — tài khoản tiền mặc định (WEB tự điền; tiền mặt và chuyển khoản)
    hai = []
    for nhan, tham in (("tiền mặt", "isCash=true&isLocal=true"), ("chuyển khoản", "isCash=false&isLocal=true")):
        duong = "/api/v1/accounting/cmpayment-receipt/default-money-account?countryId=11&" + tham
        if ctx.get("lak"):
            duong += "&currencyId=%s" % ctx["lak"]
        r, loi, ma = doc_tune(api, duong, token)
        hai.append((nhan, (r or {}).get("AccountCode") if isinstance(r, dict) else None, loi))
    tm, loi_tm = hai[0][1], hai[0][2]
    ghi("✓" if tm else "SAI", "Tài khoản tiền mặc định (LAK)",
        " · ".join("%s %s" % (n, a or ("lỗi: " + l[:70] if l else "KHÔNG CÓ")) for n, a, l in hai),
        "" if tm else (("API báo lỗi: %s Tra log API theo mã tra cứu đó. Thường do DB host thiếu bảng / thủ tục tài khoản tiền "
                        "theo quốc gia (script 20260910_cash_voucher_country_account_phase1, mục 13 tài liệu của anh)." % loi_tm
                        if loi_tm else
                        "Chưa cấu hình tài khoản tiền mặc định quốc gia 11 (CMACCOUNTCONFIGCOUNTRY, vai CASH_LOCAL).")
                       + " WEB sẽ không tự điền tài khoản tiền."))

    # A8 — kỳ tài chính chứa hôm nay, còn mở (phiếu chi cần FiciAutoId)
    r, loi, ma = doc_tune(api, "/api/v1/common/GetFinancyCicle", token)
    hom_nay = dt.date.today().isoformat()
    if r is None:
        ghi("SAI", "Kỳ tài chính hôm nay", loi, "Xem log API (GetFinancyCicle).")
    else:
        ky = [k for k in r if isinstance(k, dict) and str(k.get("FICI_DATEFROM") or "")[:10] <= hom_nay <= str(k.get("FICI_DATETO") or "")[:10]
              and k.get("FICI_ISACTIVE") is not False]
        if not ky:
            ghi("SAI", "Kỳ tài chính hôm nay", "không có kỳ chứa %s" % hom_nay, "Tạo kỳ tháng này bên hệ kế toán — thiếu kỳ thì không lập được phiếu chi.")
        elif ky[0].get("FICI_ISCLOSE"):
            ghi("SAI", "Kỳ tài chính hôm nay", "kỳ %s đã ĐÓNG" % ky[0].get("FICI_NAME"), "Mở lại kỳ, hoặc tạo kỳ mới.")
        else:
            ghi("✓", "Kỳ tài chính hôm nay", "kỳ %s (mã %s) đang mở" % (ky[0].get("FICI_NAME"), ky[0].get("FICI_AUTOID")))

    # A9 — nguồn DO đã cấu hình chưa. Từ commit ce95b3c: thiếu LogisticsSource:BaseUrl → 503 "Chưa cấu hình nguồn Logistics"
    # (bỏ mặc định ngầm EPL_System 1506). Bản cũ hơn không có 503: thiếu BaseUrl thì đọc 1506 (DO mã DO-…).
    r, loi, ma = doc_tune(api, "/api/v1/accounting/cash-voucher-references?type=DO&page=1&pageSize=5", token)
    cau = loi or ""
    viec = "Nguồn DO: LogisticsSource:BaseUrl"
    rows = ((r or {}).get("Rows") or []) if isinstance(r, dict) else []
    khac = [x.get("SourceId") for x in rows if not str(x.get("SourceId") or "").startswith(TIEN_TO_DO)]
    if ma == 503 and "Chưa cấu hình nguồn Logistics" in cau:
        if dot_1:
            ghi("✓", viec, "HTTP 503 \"chưa cấu hình\" — đúng cho đợt 1 (chưa đặt LogisticsSource)")
        else:
            ghi("SAI", viec, "HTTP 503 — chưa cấu hình nguồn Logistics (LogisticsSource:BaseUrl)",
                "Chưa đặt LogisticsSource:BaseUrl + ApiKey trong appsettings.<Env>.json của host (mục 4.2). Đang ở đợt 1 thì "
                "chạy lại với --dot-1.")
        return _bo_dong_do(ctx, "chưa đặt nguồn DO")
    if ma == 503 and "không hợp lệ" in cau:
        ghi("SAI", viec, "HTTP 503 — BaseUrl sai dạng", "LogisticsSource:BaseUrl phải là địa chỉ tuyệt đối http(s)://…/api/ (mục 4.2).")
        return _bo_dong_do(ctx, "BaseUrl sai dạng")
    if r is not None and khac:
        ghi("SAI", viec, "HTTP 200 nhưng DO không phải của trang điều xe Lào (mã %s)" % khac[0],
            "API đang đọc EPL_System 1506: bản API chưa có ce95b3c (thiếu BaseUrl thì tự trỏ 1506) và chưa đặt BaseUrl, hoặc "
            "BaseUrl trỏ 1506. Publish đủ nhánh (mục 1.4, 3), đặt LogisticsSource (mục 4.2).")
        return _bo_dong_do(ctx, "API chưa đọc trang điều xe Lào")
    if dot_1:
        ghi("SAI" if r is not None else "--", viec, "đã đặt (HTTP %s), dù chạy với --dot-1" % ma,
            "Bỏ --dot-1 nếu đã sang đợt 2." if r is not None else "")
    else:
        ghi("✓", viec, "đã đặt — API không báo 503 (HTTP %s)" % ma)

    # A10 — màn Vụ việc đọc DO từ trang điều xe (API anh → LogisticsSource → /api/handover/…)
    viec = "Vụ việc: đọc DO từ trang điều xe"
    if r is None:
        if "từ chối khoá" in cau:
            sua = "LogisticsSource:ApiKey sai hoặc Sếp đã tạo lại khoá. Dán khoá đang dùng vào cấu hình host (mục 4.2)."
        elif ma == 504 or "quá thời gian" in cau:
            sua = "Trang điều xe trả lời quá 15 giây. Kiểm mạng từ máy host tới LogisticsSource:BaseUrl."
        elif "không hợp lệ" in cau:
            sua = "LogisticsSource:BaseUrl không trỏ vào /api/ của trang điều xe (trả HTML hoặc khuôn khác). Sửa địa chỉ (mục 4.2)."
        else:
            sua = ("Máy host không gọi được LogisticsSource:BaseUrl: sai địa chỉ, chuyển hướng http→https, trang điều xe tắt, "
                   "hoặc trang điều xe chưa tạo khoá (503). Thử lệnh ở mục 9 từ chính máy host.")
        ghi("SAI", viec, cau, sua)
        ghi("--", "Tìm DO theo từ khoá → SearchScope ALL", "không đọc được danh sách DO", "")
        return ctx
    total = (r or {}).get("Total") or 0
    ctx["do_total"] = total
    if not rows:
        ghi("✓", viec, "đọc được, nhưng trang điều xe chưa có DO đã khoá (Total %s)" % total, "")
        ghi("--", "Tìm DO theo từ khoá → SearchScope ALL", "chưa có DO để tìm", "")
        return ctx
    dau = rows[0]
    ctx["do_mau"] = dau
    so_phieu_ok = all(x.get("SourceCode") and x.get("SourceCode") != x.get("SourceId") for x in rows)
    ghi("✓" if so_phieu_ok else "SAI", viec,
        "%s DO; dòng đầu %s, số phiếu %s" % (total, dau.get("SourceId"), dau.get("SourceCode")),
        "" if so_phieu_ok else "Màn Vụ việc hiện mã DO thay số phiếu: host chưa có commit 465748b (SourceCode = doc_no).")

    # A11 — tìm theo keyword: SearchScope = ALL, Total đúng sau lọc
    kw = tu_khoa or dau.get("SourceCode") or ""
    viec = "Tìm DO theo từ khoá → SearchScope ALL"
    r, loi, ma = doc_tune(api, "/api/v1/accounting/cash-voucher-references?type=DO&page=1&pageSize=5&keyword=" + urllib.parse.quote(kw), token)
    if r is None:
        ghi("SAI", viec, "từ khoá %r: %s" % (kw, loi), "Xem log API.")
        return ctx
    pham_vi, ids = r.get("SearchScope"), [x.get("SourceId") for x in r.get("Rows") or []]
    r0, _, _ = doc_tune(api, "/api/v1/accounting/cash-voucher-references?type=DO&page=1&pageSize=5&keyword=" + TU_KHOA_KHONG_CO, token)
    t0 = (r0 or {}).get("Total")
    chi = "từ khoá %r → %s, Total %s%s; chữ không có → Total %s" % (
        kw, pham_vi, r.get("Total"), "" if tu_khoa else (" (có DO đầu)" if dau.get("SourceId") in ids else " (THIẾU DO đầu)"), t0)
    if pham_vi == "ALL" and (tu_khoa or dau.get("SourceId") in ids) and t0 == 0:
        ghi("✓", viec, chi)
    else:
        if pham_vi != "ALL" and dx_info.get("co_q") is False:
            sua = ("Trang điều xe đang chạy bản CŨ (chưa có tham số q, sửa 01/10 14:07). Bên em khởi động lại trang điều xe để "
                   "nạp code mới.")
        elif pham_vi != "ALL":
            sua = ("API chưa chạy bản có commit 64ce7a4 (gửi q sang trang điều xe), hoặc LogisticsSource:BaseUrl trỏ vào một trang "
                   "điều xe khác bản cũ. Merge + publish lại đúng nhánh (mục 1.4, 3).")
        else:
            sua = "Total sau lọc chưa đúng — gửi kết quả này cho bên em."
        ghi("SAI", viec, chi, sua)
    return ctx


# ---------------------------------------------------------------- B. trang điều xe
def kiem_dieu_xe(dx, api, cfg, dx_info, ctx, dot_1=False):
    kq, chi, sua = dx_info["loi_song"]
    ghi(kq, "Trang điều xe trả lời", chi, sua)
    if not dx_info["song"]:
        return
    if dx_info.get("co_q") is None:
        ghi("--", "Trang điều xe có đường bàn giao + q", "không đọc được /openapi.json", "")
    elif not dx_info.get("co_ban_giao"):
        ghi("SAI", "Trang điều xe có đường bàn giao + q", "không có /api/handover/delivery-orders",
            "Trang điều xe chạy bản trước 30/09. Bên em cập nhật code trang điều xe.")
    else:
        ghi("✓" if dx_info["co_q"] else "SAI", "Trang điều xe có đường bàn giao + q",
            "có hai đường bàn giao; tham số q %s" % ("có" if dx_info["co_q"] else "CHƯA CÓ (bản cũ)"),
            "" if dx_info["co_q"] else "Bên em khởi động lại trang điều xe để nạp bản có q (01/10 14:07).")

    # khoá bàn giao (nếu có): đọc thẳng như API anh đọc
    khoa = cfg("KIEM_KHOA_BAN_GIAO")
    if khoa:
        ma, than, giay, loi, toi = goi("GET", dx + "/api/handover/delivery-orders?page=1&page_size=1", khoa)
        if ma == 200 and isinstance(than, dict):
            t = ((than.get("data") or {}).get("total"))
            dong = (than.get("data") or {}).get("items") or []
            if dong and isinstance(dong[0], dict):
                ctx["do_id_dx"] = dong[0].get("do_id")             # DO mẫu cho dòng "gửi sang đúng API" khi API chưa đọc DO
            khop = ctx.get("do_total") is None or t == ctx.get("do_total")
            ghi("✓" if khop else "SAI", "Khoá bàn giao đọc được danh sách DO",
                "HTTP 200, %s DO%s" % (t, "" if ctx.get("do_total") is None else ("; API anh thấy %s" % ctx["do_total"])),
                "" if khop else "API anh đang đọc một trang điều xe khác (LogisticsSource:BaseUrl), không phải địa chỉ này.")
        else:
            cau = loi or ((than or {}).get("detail") or {}).get("loi") if isinstance(than, dict) else loi
            ghi("SAI", "Khoá bàn giao đọc được danh sách DO", "HTTP %s %s" % (ma, cau or ""),
                "401: khoá KIEM_KHOA_BAN_GIAO không khớp khoá trang điều xe đang giữ — Sếp đã tạo lại? 503: chưa tạo khoá.")
    else:
        ghi("--", "Khoá bàn giao đọc được danh sách DO", "chưa đặt KIEM_KHOA_BAN_GIAO", "")

    # phiên Sếp (nếu có): trạng thái bàn giao, máy đang gửi sang, danh mục tài khoản
    phien = cfg("KIEM_PHIEN_SEP")
    ten, mk = cfg("KIEM_SEP_TEN"), cfg("KIEM_SEP_MAT_KHAU", giu_nguyen=True)
    if not phien and ten and mk:
        ma, than, _, loi, _ = goi("POST", dx + "/api/dang-nhap", body={"username": ten, "password": mk})
        phien = (than or {}).get("token") if ma == 200 and isinstance(than, dict) else None
        if not phien:
            ghi("SAI", "Đăng nhập Sếp trang điều xe", "HTTP %s %s" % (ma, loi or ""), "Sai KIEM_SEP_TEN / KIEM_SEP_MAT_KHAU.")
    if not phien:
        for viec in ("Trạng thái bàn giao (Sếp)", "Trang điều xe gửi sang đúng API", "Trang điều xe đọc danh mục tài khoản"):
            ghi("--", viec, "chưa đặt KIEM_SEP_TEN / KIEM_SEP_MAT_KHAU (hoặc KIEM_PHIEN_SEP)", "")
        return

    ma, than, _, loi, _ = goi("GET", dx + "/api/handover/trang-thai", phien)
    if ma == 200 and isinstance(than, dict):
        n, co = than.get("so_do_ban_giao_duoc"), than.get("co_khoa")
        khop = ctx.get("do_total") is None or n == ctx.get("do_total")
        ok = (bool(co) or dot_1) and khop
        ghi("✓" if ok else "SAI", "Trạng thái bàn giao (Sếp)",
            "khoá %s; %s DO bàn giao được%s" % ("đã tạo" if co else ("chưa tạo (đợt 1: chưa cần)" if dot_1 else "CHƯA TẠO"), n,
                                               "" if ctx.get("do_total") is None else "; API anh thấy %s" % ctx["do_total"]),
            "" if ok else ("Sếp chưa tạo khoá bàn giao: POST /api/handover/tao-khoa (mục 4.2)." if not co else
                           "Số DO hai bên lệch: API anh đang đọc một trang điều xe khác (LogisticsSource:BaseUrl)."))
    else:
        ghi("SAI", "Trạng thái bàn giao (Sếp)", "HTTP %s %s" % (ma, loi or ""), "Phiên Sếp sai / hết hạn, hoặc tài khoản không phải vai admin.")

    # máy trang điều xe đang gửi SO / phiếu chi sang (xem trước gói SO — không gọi mạng, không ghi)
    mau = str((ctx.get("do_mau") or {}).get("SourceId") or ctx.get("do_id_dx") or "")
    if mau.startswith(TIEN_TO_DO):
        tid = mau[len(TIEN_TO_DO):]
        ma, than, _, loi, _ = goi("GET", dx + "/api/trips/%s/tao-so" % urllib.parse.quote(tid), phien)
        if ma == 200 and isinstance(than, dict):
            may, co_tk = than.get("may"), than.get("co_token")
            dung = (may or "").lower() == urlsplit(api).netloc.lower()
            ghi("✓" if dung and co_tk else "SAI", "Trang điều xe gửi sang đúng API",
                "gửi SO / phiếu chi sang %s; token %s" % (may, "có" if co_tk else "KHÔNG CÓ"),
                "" if dung and co_tk else ("Trang điều xe còn trỏ %s. Bên em sửa QLSX_BASE_URL / EPL_ACC_CODE_API trong .env "
                                           "rồi khởi động lại (mục 7)." % may if not dung else
                                           "Trang điều xe chưa có token: đặt tài khoản tích hợp (mục 6)."))
        else:
            ghi("SAI", "Trang điều xe gửi sang đúng API", "HTTP %s %s" % (ma, loi or ""), "Gửi kết quả này cho bên em.")
    else:
        ghi("--", "Trang điều xe gửi sang đúng API", "không có DO mẫu (API anh chưa đọc DO, chưa đặt KIEM_KHOA_BAN_GIAO)", "")

    ma, than, _, loi, _ = goi("GET", dx + "/api/acc-codes", phien)
    if ma == 200 and isinstance(than, dict):
        src = than.get("source")
        ok = src in ("remote", "cached")
        ghi("✓" if ok else "SAI", "Trang điều xe đọc danh mục tài khoản", "%s — %s" % (src, str(than.get("message") or "")[:90]),
            "" if ok else "Trang điều xe không đọc được EPL_ACC_CODE_API: sai địa chỉ hoặc EPL_ACC_CODE_TOKEN hết hạn (mục 7).")
    else:
        ghi("SAI", "Trang điều xe đọc danh mục tài khoản", "HTTP %s %s" % (ma, loi or ""), "Gửi kết quả này cho bên em.")


# ---------------------------------------------------------------- in bảng
def in_bang(api, dx, ctx):
    print()
    print("KIỂM SAU TRIỂN KHAI — %s" % dt.datetime.now().strftime("%d/%m/%Y %H:%M"))
    print("  API anh Tune : %s" % api)
    print("  Trang điều xe: %s" % dx)
    print("  Token API    : %s (không in)" % ctx.get("nguon_token", "—"))
    print()
    rong = max(len(v) for _, v, _, _ in DONG) + 2
    print(" %-3s %-4s %-*s %s" % ("#", "KQ", rong, "Kiểm", "Chi tiết"))
    print(" " + "-" * (rong + 60))
    for i, (kq, viec, chi, _) in enumerate(DONG, 1):
        print(" %-3d %-4s %-*s %s" % (i, kq, rong, viec, chi))
    sai = [(i, v, s) for i, (kq, v, _, s) in enumerate(DONG, 1) if kq == "SAI"]
    bo = [(i, v, s) for i, (kq, v, _, s) in enumerate(DONG, 1) if kq == "--" and s]
    if sai:
        print()
        print("Hướng sửa:")
        for i, v, s in sai:
            print(" %-3d %s: %s" % (i, v, s or "gửi kết quả này cho bên em."))
    if bo:
        print()
        print("Bỏ qua (chưa đủ dữ liệu để kiểm):")
        for i, v, s in bo:
            print(" %-3d %s: %s" % (i, v, s))
    print()
    print("Tổng: %d ✓ · %d SAI · %d bỏ qua" % (sum(1 for d in DONG if d[0] == "✓"), len(sai), sum(1 for d in DONG if d[0] == "--")))
    return 1 if sai else 0


def main():
    ap = argparse.ArgumentParser(description="Kiểm sau triển khai (chỉ đọc): API anh Tune ↔ trang điều xe EPL Lào.")
    ap.add_argument("api", help="địa chỉ gốc API anh Tune, ví dụ https://demo-lao-api.goldensme.com")
    ap.add_argument("dieu_xe", help="địa chỉ gốc trang điều xe, ví dụ http://127.0.0.1:8011")
    ap.add_argument("--env", default=os.path.join(GOC_DU_AN, ".env"), help="tệp KEY=giá_trị đọc thêm (mặc định .env của EPL_LAO_REAL)")
    ap.add_argument("--tu-khoa", default="", help="từ khoá thử tìm DO (mặc định: số phiếu của DO đầu tiên)")
    ap.add_argument("--dot-1", action="store_true",
                    help="đợt 1: chưa đặt LogisticsSource — DO trả 503 \"chưa cấu hình\" là đúng")
    a = ap.parse_args()
    api, dx = a.api.rstrip("/"), a.dieu_xe.rstrip("/")
    if dx.endswith("/api"):
        dx = dx[:-4]
    cfg = CauHinh(a.env)
    dx_info = do_dieu_xe(dx)
    ctx = kiem_api(api, cfg, dx_info, a.tu_khoa.strip(), a.dot_1)
    kiem_dieu_xe(dx, api, cfg, dx_info, ctx, a.dot_1)
    sys.exit(in_bang(api, dx, ctx))


if __name__ == "__main__":
    main()

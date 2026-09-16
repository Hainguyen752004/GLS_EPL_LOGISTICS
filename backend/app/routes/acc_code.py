# -*- coding: utf-8 -*-
"""Danh mục Acc code (mã tài khoản kế toán) từ API bên công nợ — anh Khang, Golden SME.

Cùng cách nối với EPL_System (routes/fleet_routes.py): ba biến môi trường EPL_ACC_CODE_API,
EPL_ACC_CODE_TOKEN, EPL_ACC_CODE_COUNTRY (Lào = 11); giữ bộ nhớ 10 phút vì danh mục ~500 dòng
và hiếm đổi. Token nằm phía máy chủ, không bao giờ ra trình duyệt.

Mã trên phiếu của bên Lào là CẶP định khoản kiểu "625/402" (Nợ / Có). Danh mục của anh Khang
là từng tài khoản đơn. Nên màn hình ghép cặp từ hai ô chọn Nợ và Có lấy từ danh mục này; nửa
nào không có trong danh mục (ví dụ 371, 4022 họ ghi trong Excel) thì hiện cảnh báo, KHÔNG tự
bịa mã thay thế — chủ dự án chốt: mã do bên kia cấp.

`source` phân biệt: remote · cached · unconfigured · error · fallback. Không nối được thì trả
danh sách rút gọn từ Excel của họ kèm source=fallback để màn hình nói thật là đang dùng bản tạm.
"""
import json
import os
import time
import urllib.error
import urllib.request

from fastapi import APIRouter, Depends

from services.bao_mat import nguoi_hien_tai

router = APIRouter()
DUONG_COUNTRY_ACCOUNTS = "/api/v1/common/country-accounts"
_BO_NHO = {"khoa": None, "luc": 0.0, "goi": None}
CACHE_GIAY = 600

# Bản tạm khi chưa nối được — các tài khoản xuất hiện trong Excel và quy trình của họ.
DU_PHONG = [
    {"code": "625", "name": "ຄ່າເດີນທາງ", "description": "Chi phí đi đường, công tác phí"},
    {"code": "614", "name": "ຄ່າບົວລະບັດ, ສ້ອມແປງ", "description": "Chi phí bảo trì và sửa chữa"},
    {"code": "402", "name": "ໜີ້ຕ້ອງສົ່ງ ຜູ້ສະໜອງ - ບໍລິການ", "description": "Phải trả nhà cung cấp dịch vụ"},
    {"code": "371", "name": "ສາງ (ຕາມ Excel)", "description": "Kho — theo Excel của họ, chưa có trong danh mục"},
    {"code": "4022", "name": "ຈ່າຍແທນລົດຮ່ວມ (ຕາມ Excel)", "description": "Chi hộ nhà thầu phụ — theo quy trình, chưa có trong danh mục"},
    {"code": "1211", "name": "ລູກຄ້າ-ຄ່າສິນຄ້າ", "description": "Khách hàng - Hàng hoá"},
    {"code": "70", "name": "ຂາຍສິນຄ້າ, ບໍລິການ", "description": "Bán sản phẩm, hàng hoá, dịch vụ"},
]


def _url():
    goc = (os.getenv("EPL_ACC_CODE_API") or "").strip()
    if not goc:
        return ""
    url = goc if "country-accounts" in goc else goc.rstrip("/") + DUONG_COUNTRY_ACCOUNTS
    quoc_gia = (os.getenv("EPL_ACC_CODE_COUNTRY") or "11").strip()
    if "tryAutoId=" not in url:
        url += ("&" if "?" in url else "?") + "tryAutoId=%s" % quoc_gia
    if "onlyActive=" not in url:
        url += "&onlyActive=true"
    return url


def _chuan_hoa(goi):
    if isinstance(goi, dict) and isinstance(goi.get("Result"), list):
        ket = []
        for x in goi["Result"]:
            if not isinstance(x, dict):
                continue
            ma = str(x.get("AccCode") or "").strip()
            if not ma:
                continue
            ket.append({"code": ma, "name": str(x.get("AccName") or "").strip() or ma,
                        "description": str(x.get("AccDescription") or "").strip(),
                        "parent": (str(x.get("AccParentId")).strip() if x.get("AccParentId") not in (None, "") else None),
                        "postable": bool(x.get("AccAccountWrite")), "active": bool(x.get("AccIsActive", True))})
        return ket
    ds = goi.get("data") if isinstance(goi, dict) else goi
    return [{"code": str(x.get("code") or "").strip(), "name": str(x.get("name") or x.get("code") or ""),
             "description": str(x.get("description") or "")} for x in (ds if isinstance(ds, list) else []) if isinstance(x, dict) and x.get("code")]


def lay_danh_muc(refresh=False):
    """Trả (danh sách, source, message). Dùng chung cho endpoint và cho bước kiểm mã khi lưu phiếu."""
    url = _url()
    if not url:
        return DU_PHONG, "unconfigured", "Chưa nối API mã tài khoản của bên công nợ (đặt EPL_ACC_CODE_API) — đang dùng bản tạm từ Excel."
    bo = _BO_NHO
    if not refresh and bo["goi"] is not None and bo["khoa"] == url and time.time() - bo["luc"] < CACHE_GIAY:
        return bo["goi"], "cached", "Danh mục %d mã (bộ nhớ, tối đa 10 phút)." % len(bo["goi"])
    try:
        dau = {"Accept": "application/json"}
        token = (os.getenv("EPL_ACC_CODE_TOKEN") or "").strip()
        if token:
            dau["Authorization"] = "Bearer " + token
        with urllib.request.urlopen(urllib.request.Request(url, headers=dau), timeout=20) as tra:
            goi = json.loads(tra.read().decode("utf-8", "replace"))
    except Exception as loi:  # noqa: BLE001 — mọi lỗi mạng/định dạng đều là "không đọc được"
        if bo["goi"] is not None:
            return bo["goi"], "cached", "Không nối được API bên công nợ, dùng bản trong bộ nhớ."
        return DU_PHONG, "error", "Không đọc được danh mục Acc code từ API bên công nợ: %s — đang dùng bản tạm." % str(loi)[:120]
    if isinstance(goi, dict) and goi.get("Success") is False:
        return DU_PHONG, "error", "API bên công nợ từ chối: %s" % str(goi.get("Message") or goi.get("Code"))[:120]
    ket = _chuan_hoa(goi)
    bo["khoa"], bo["luc"], bo["goi"] = url, time.time(), ket
    return ket, "remote", "Đã tải %d mã từ API bên công nợ." % len(ket)


@router.get("/api/acc-codes")
def danh_muc_acc_code(refresh: bool = False, _=Depends(nguoi_hien_tai)):
    ds, source, msg = lay_danh_muc(refresh)
    return {"data": ds, "source": source, "count": len(ds), "message": msg}

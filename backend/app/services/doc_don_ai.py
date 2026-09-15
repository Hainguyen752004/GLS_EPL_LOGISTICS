"""Đọc phiếu đặt hàng của khách bằng Gemini, ra bản nháp đơn hàng.

Gọi THẲNG REST API chứ không dùng SDK `google-generativeai`: trên máy chủ dự án
SDK đó kéo theo aiohttp, và aiohttp vỡ ngay lúc nạp vì đọc kho chứng chỉ của
Windows (`ssl.SSLError: NOT_ENOUGH_DATA`). REST chỉ cần `requests`, không có
chuỗi phụ thuộc đó, và vẫn gửi được PDF/ảnh dưới dạng inline_data.

Gemini đọc thẳng PDF và ảnh, nên không cần thư viện bóc chữ riêng.
"""

import base64
import json
import logging
import os
import re

import requests

logger = logging.getLogger(__name__)

KHOA = os.getenv("GEMINI_API_KEY_GT", "").strip()
MO_HINH = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
URL = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={k}"

# Kiểu tệp Gemini nhận thẳng. Excel thì mình đọc ra chữ trước rồi mới gửi.
MIME_GUI_THANG = (
    "application/pdf",
    "image/png", "image/jpeg", "image/jpg", "image/webp", "image/heic", "image/heif",
    "text/plain", "text/csv",
)

HUONG_DAN = """\
Bạn đọc phiếu đặt hàng (Purchase Order) của khách trong ngành vận tải - kho vận
ở Lào, Thái Lan và Việt Nam. Trả về ĐÚNG một JSON, không thêm chữ nào ngoài JSON.

Schema:
{
  "po_number": "số PO trên phiếu, hoặc null",
  "order_date": "ngày đặt dạng YYYY-MM-DD, hoặc null",
  "shipping_date": "ngày giao dự kiến dạng YYYY-MM-DD, hoặc null",
  "ship_to_code": "mã điểm giao / mã cửa hàng, hoặc null",
  "ship_to_name": "tên nơi nhận hàng, hoặc null",
  "ship_to_address": "địa chỉ giao, hoặc null",
  "vendor_name": "tên nhà cung cấp / bên bán, hoặc null",
  "tax_number": "mã số thuế, hoặc null",
  "currency": "LAK | THB | USD | VND, hoặc null",
  "lines": [
    {
      "barcode": "mã vạch, hoặc null",
      "product_code": "mã hàng, hoặc null",
      "description": "tên hàng đúng như trên phiếu",
      "description_en": "tên hàng bản tiếng Anh nếu phiếu có in, hoặc null",
      "pack_size": số cái trong một thùng (số nguyên) hoặc null,
      "case_qty": số THÙNG đặt (số nguyên),
      "piece_qty": số CÁI đặt (số nguyên) hoặc null,
      "unit_price": đơn giá (số) hoặc null,
      "amount": thành tiền (số) hoặc null
    }
  ],
  "confidence": số từ 0 đến 100 cho biết bạn chắc chắn tới đâu,
  "warnings": ["những chỗ bạn không chắc"]
}

Quy tắc bắt buộc:
- KHÔNG BỊA. Không thấy thì để null và ghi vào warnings.
- Số lượng phải là số nguyên thuần, bỏ dấu phân cách ngàn.
- Cột kiểu "UNIT QUANTITY (UNIT/PACK/CASE)" ghi "2CT" nghĩa là 2 CASE (2 thùng)
  — đưa 2 vào case_qty, KHÔNG đưa vào piece_qty.
- Có PACK SIZE (ví dụ 12) thì piece_qty = case_qty × pack_size, trừ khi phiếu
  ghi rõ số cái khác.
- Tiền: bỏ dấu phân cách, giữ phần thập phân nếu có.
- Phiếu có cả tiếng Lào và tiếng Anh thì `description` lấy bản tiếng Lào,
  `description_en` lấy bản tiếng Anh.
- warnings phải nêu rõ dòng nào, cột nào bạn đọc không chắc. Đây là thứ người
  duyệt nhìn vào để soát lại, nên nói cụ thể.
"""


class LoiAI(Exception):
    pass


def san_sang():
    return bool(KHOA)


def _goi_gemini(cac_phan, timeout=90):
    if not KHOA:
        raise LoiAI("Chưa cấu hình GEMINI_API_KEY_GT trong .env")
    try:
        r = requests.post(
            URL.format(m=MO_HINH, k=KHOA),
            json={
                "contents": [{"parts": cac_phan}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0},
            },
            timeout=timeout,
        )
    except requests.RequestException as loi:
        raise LoiAI(f"Không gọi được Gemini: {loi}")
    if not r.ok:
        raise LoiAI(f"Gemini trả lỗi HTTP {r.status_code}")
    try:
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, ValueError):
        raise LoiAI("Gemini trả về dữ liệu không đọc được")


def _doc_json(chu):
    """Gỡ JSON ra khỏi câu trả lời của Gemini.

    Đã gặp thật: có lần Gemini trả JSON kèm dấu phẩy thừa trước dấu đóng ngoặc,
    và `json.loads` ném thẳng ValueError ra ngoài module này. Ở đây phải nuốt
    mọi kiểu trả lời lệch chuẩn và, nếu vẫn không đọc được, ném LoiAI — để phía
    trên luôn biến nó thành một mã lỗi có bản dịch, chứ không phải một vệt lỗi
    Python bay lên màn hình nghiệp vụ.
    """
    chu = (chu or "").strip()
    if chu.startswith("```"):
        chu = re.sub(r"^```[a-zA-Z]*\s*", "", chu)
        chu = re.sub(r"\s*```$", "", chu)

    ung_vien = [chu]
    m = re.search(r"\{[\s\S]*\}", chu)
    if m and m.group(0) != chu:
        ung_vien.append(m.group(0))
    ung_vien += [re.sub(r",(\s*[}\]])", r"", x) for x in list(ung_vien)]

    for x in ung_vien:
        try:
            return json.loads(x)
        except ValueError:
            continue
    raise LoiAI("Gemini trả về JSON không đọc được")


def _goi_va_doc(cac_phan):
    """Gọi Gemini rồi đọc JSON; hỏng thì thử LẠI MỘT LẦN.

    Câu trả lời lệch chuẩn gần như luôn tự hết ở lần gọi thứ hai, và gọi lại một
    lần rẻ hơn nhiều so với bắt người duyệt gõ tay lại cả phiếu.
    """
    try:
        return _doc_json(_goi_gemini(cac_phan))
    except LoiAI as loi:
        logger.warning("Lan doc dau hong (%s) - goi lai mot lan", loi)
        return _doc_json(_goi_gemini(cac_phan))


def _so_nguyen(x):
    if x in (None, "", False):
        return 0
    if isinstance(x, (int, float)):
        return int(x)
    chu = re.sub(r"[^\d\-]", "", str(x))
    return int(chu) if chu else 0


def _so_thuc(x):
    if x in (None, "", False):
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    chu = str(x).replace(" ", "")
    # "686,000.00" và "686.000,00" đều gặp trong phiếu của Lào/Thái.
    if "," in chu and "." in chu:
        chu = chu.replace(",", "") if chu.rfind(".") > chu.rfind(",") else chu.replace(".", "").replace(",", ".")
    elif "," in chu:
        chu = chu.replace(",", "") if len(chu.split(",")[-1]) == 3 else chu.replace(",", ".")
    chu = re.sub(r"[^\d.\-]", "", chu)
    try:
        return float(chu) if chu else 0.0
    except ValueError:
        return 0.0


def _chuan_hoa(d):
    """Ép dữ liệu AI về đúng hình dạng bản nháp đơn hàng của mình."""
    canh_bao = list(d.get("warnings") or [])
    dong = []
    for i, x in enumerate(d.get("lines") or [], start=1):
        mo_ta = (x.get("description") or "").strip()
        if not mo_ta:
            canh_bao.append(f"Dòng {i} không đọc được tên hàng")
            continue
        thung = _so_nguyen(x.get("case_qty"))
        quy_cach = _so_nguyen(x.get("pack_size"))
        cai = _so_nguyen(x.get("piece_qty"))
        if not cai and thung and quy_cach:
            cai = thung * quy_cach
        if thung <= 0 and cai <= 0:
            canh_bao.append(f"Dòng {i} ({mo_ta}) không đọc được số lượng")
        gia = _so_thuc(x.get("unit_price"))
        dong.append({
            "line_no": i,
            "barcode": (x.get("barcode") or "").strip() or None,
            "product_code": (x.get("product_code") or "").strip() or None,
            "description": mo_ta,
            "description_en": (x.get("description_en") or "").strip() or None,
            "pack_size": quy_cach or 1,
            "case_qty": thung,
            "piece_qty": cai,
            "unit_price": gia,
            "amount": _so_thuc(x.get("amount")) or round(gia * thung, 2),
        })

    tin_cay = d.get("confidence")
    try:
        tin_cay = max(0, min(100, int(float(tin_cay))))
    except (TypeError, ValueError):
        tin_cay = 0

    if not dong:
        canh_bao.append("Không đọc được dòng hàng nào từ tệp này")

    return {
        "po_number": (d.get("po_number") or "").strip() or None,
        "order_date": (d.get("order_date") or "").strip() or None,
        "shipping_date": (d.get("shipping_date") or "").strip() or None,
        "ship_to_code": (d.get("ship_to_code") or "").strip() or None,
        "ship_to_name": (d.get("ship_to_name") or "").strip() or None,
        "ship_to_address": (d.get("ship_to_address") or "").strip() or None,
        "vendor_name": (d.get("vendor_name") or "").strip() or None,
        "tax_number": (d.get("tax_number") or "").strip() or None,
        "currency": ((d.get("currency") or "").strip().upper() or None),
        "lines": dong,
        "confidence": tin_cay,
        "warnings": canh_bao,
    }


def _chu_tu_excel(du_lieu, ten):
    """Excel: bóc ra chữ rồi mới gửi, vì Gemini không nhận thẳng .xlsx."""
    try:
        import io

        import openpyxl
    except ImportError:
        raise LoiAI("Máy chủ chưa có openpyxl để đọc tệp Excel")
    wb = openpyxl.load_workbook(io.BytesIO(du_lieu), data_only=True)
    ra = [f"Tệp: {ten}"]
    for sheet in wb.worksheets:
        ra.append(f"--- Sheet: {sheet.title} ---")
        for hang in sheet.iter_rows(values_only=True):
            o = [str(x) for x in hang if x not in (None, "")]
            if o:
                ra.append(" | ".join(o))
    return "\n".join(ra[:2000])


def doc_tep(du_lieu, mime, ten_tep="", chu_kem=""):
    """Đọc một tệp đính kèm ra bản nháp đơn hàng."""
    mime = (mime or "").lower().split(";")[0].strip()
    boi_canh = HUONG_DAN
    if chu_kem:
        boi_canh += "\n\nNội dung email kèm theo (dùng để bổ sung, phiếu vẫn là chính):\n" + chu_kem[:4000]

    if mime in MIME_GUI_THANG:
        phan = [
            {"text": boi_canh},
            {"inline_data": {"mime_type": mime, "data": base64.b64encode(du_lieu).decode("ascii")}},
        ]
    elif ten_tep.lower().endswith((".xlsx", ".xlsm", ".xls")) or "spreadsheet" in mime or "excel" in mime:
        phan = [{"text": boi_canh + "\n\nNội dung bảng tính:\n" + _chu_tu_excel(du_lieu, ten_tep)}]
    else:
        # Kiểu lạ: thử đọc như chữ thuần, hỏng thì báo rõ chứ không đoán bừa.
        try:
            chu = du_lieu.decode("utf-8", errors="ignore")
        except Exception:
            raise LoiAI(f"Không đọc được tệp kiểu {mime}")
        if not chu.strip():
            raise LoiAI(f"Không đọc được tệp kiểu {mime}")
        phan = [{"text": boi_canh + "\n\nNội dung tệp:\n" + chu[:20000]}]

    return _chuan_hoa(_goi_va_doc(phan))


def doc_chu(chu):
    """Đọc đơn hàng viết thẳng trong thân email, khi không có tệp đính kèm."""
    if not (chu or "").strip():
        raise LoiAI("Email không có nội dung để đọc")
    return _chuan_hoa(_goi_va_doc([{"text": HUONG_DAN + "\n\nNội dung email:\n" + chu[:20000]}]))

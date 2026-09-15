"""Đọc hộp thư đặt hàng của khách qua Gmail API.

Cắt gọn từ bản đang chạy ở dự án CHATBOT & QUAN TRI CRM: bản demo này CHỈ ĐỌC
thư và đánh dấu đã đọc, không gửi thư trả lời. Ít quyền hơn thì ít rủi ro hơn.

Mọi hàm ở đây ném `LoiNghiepVu` với mã ổn định thay vì để lỗi thư viện bay lên
màn hình, vì màn nghiệp vụ không được hiện chữ kỹ thuật.
"""

import base64
import datetime
import logging
import os

from services.loi import LoiNghiepVu

logger = logging.getLogger(__name__)

PHAM_VI = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _duong_dan(bien, mac_dinh):
    """Đường dẫn trong .env có thể là tương đối; quy về gốc dự án cho chắc."""
    d = os.getenv(bien, mac_dinh).strip().strip('"')
    return d if os.path.isabs(d) else os.path.normpath(os.path.join(GOC, d))


def duong_dan_token():
    return _duong_dan("GMAIL_TOKEN_PATH", "services/token.json")


def duong_dan_khoa():
    return _duong_dan("GMAIL_CREDENTIALS_PATH", "services/OAuth2.json")


def san_sang():
    """Đã nối được hộp thư chưa — dùng để bật/tắt nút Quét hộp thư trên giao diện."""
    try:
        import googleapiclient  # noqa: F401
    except ImportError:
        return False
    return os.path.exists(duong_dan_token())


def _dich_vu():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        raise LoiNghiepVu(
            "GM_NO_LIB", "Máy chủ chưa cài thư viện Gmail (google-api-python-client)", 503
        )

    tok = duong_dan_token()
    if not os.path.exists(tok):
        raise LoiNghiepVu("GM_NO_TOKEN", f"Chưa cấp quyền hộp thư (thiếu {tok})", 503)

    creds = Credentials.from_authorized_user_file(tok, PHAM_VI)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(tok, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
        else:
            raise LoiNghiepVu("GM_TOKEN_EXPIRED", "Quyền đọc hộp thư đã hết hạn, cần cấp lại", 503)
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def dia_chi_hop_thu():
    """Địa chỉ hộp thư đang nối, để hiện cho người dùng biết đang quét thư của ai."""
    try:
        return _dich_vu().users().getProfile(userId="me").execute().get("emailAddress")
    except LoiNghiepVu:
        raise
    except Exception as loi:
        logger.warning("Khong doc duoc ho so hop thu: %s", loi)
        return None


def kiem_tra():
    """Gọi thật một lần để biết hộp thư CÓ DÙNG ĐƯỢC không, chứ không chỉ có tệp.

    Có `token.json` nằm đó không có nghĩa là còn dùng được: token hết hạn mà khoá
    OAuth đã bị thu hồi thì Google từ chối làm mới. Nếu chỉ nhìn thấy tệp rồi bật
    nút "Quét hộp thư", người dùng bấm vào và nhận một lỗi khó hiểu. Thà nói ngay
    là chưa nối, kèm lý do, và chỉ đúng lệnh cần chạy.
    """
    if not san_sang():
        return {
            "ok": False,
            "reason": "GM_NO_TOKEN" if _co_thu_vien() else "GM_NO_LIB",
            "mailbox": None,
        }
    try:
        dia_chi = _dich_vu().users().getProfile(userId="me").execute().get("emailAddress")
        return {"ok": True, "reason": None, "mailbox": dia_chi}
    except LoiNghiepVu as loi:
        return {"ok": False, "reason": loi.ma, "mailbox": None}
    except Exception as loi:
        logger.warning("Hop thu khong dung duoc: %s", loi)
        return {"ok": False, "reason": "GM_TOKEN_EXPIRED", "mailbox": None}


def _co_thu_vien():
    try:
        import googleapiclient  # noqa: F401
        return True
    except ImportError:
        return False


def _gio(ms):
    try:
        return datetime.datetime.utcfromtimestamp(int(ms) / 1000)
    except (TypeError, ValueError):
        return datetime.datetime.utcnow()


def _bo_phan(phan, gom):
    """Đi hết cây MIME, gom thân thư và tệp đính kèm."""
    for p in phan or []:
        ten = p.get("filename") or ""
        than = p.get("body") or {}
        kieu = (p.get("mimeType") or "").lower()
        if p.get("parts"):
            _bo_phan(p["parts"], gom)
        elif ten:
            gom["files"].append(
                {
                    "name": ten,
                    "mime": kieu,
                    "size": int(than.get("size") or 0),
                    "attachment_id": than.get("attachmentId"),
                }
            )
        elif kieu == "text/plain" and than.get("data"):
            gom["text"] += base64.urlsafe_b64decode(than["data"]).decode("utf-8", "ignore")


def danh_sach_thu_chua_doc(gioi_han=10, loc=None):
    """Thư CHƯA ĐỌC trong hộp đến. Đọc rồi thì lần quét sau không lấy lại."""
    dv = _dich_vu()
    truy_van = loc or "is:unread in:inbox"
    try:
        kq = (
            dv.users()
            .messages()
            .list(userId="me", q=truy_van, maxResults=max(1, min(int(gioi_han), 50)))
            .execute()
        )
    except Exception as loi:
        logger.warning("Không đọc được danh sách thư: %s", loi)
        raise LoiNghiepVu("GM_LIST_FAILED", "Không đọc được danh sách thư trong hộp thư", 502)
    return [m["id"] for m in kq.get("messages", [])]


def chi_tiet_thu(msg_id):
    """Một lá thư: người gửi, tiêu đề, thân thư, và các tệp đính kèm đã tải sẵn."""
    dv = _dich_vu()
    try:
        thu = dv.users().messages().get(userId="me", id=msg_id, format="full").execute()
    except Exception as loi:
        logger.warning("Không đọc được thư %s: %s", msg_id, loi)
        raise LoiNghiepVu("GM_GET_FAILED", "Không đọc được nội dung thư", 502)

    dau = {h["name"].lower(): h["value"] for h in thu.get("payload", {}).get("headers", [])}
    gom = {"text": "", "files": []}
    than = thu.get("payload") or {}
    if than.get("parts"):
        _bo_phan(than["parts"], gom)
    elif (than.get("body") or {}).get("data"):
        gom["text"] = base64.urlsafe_b64decode(than["body"]["data"]).decode("utf-8", "ignore")

    for t in gom["files"]:
        t["data"] = b""
        if not t.get("attachment_id"):
            continue
        try:
            a = (
                dv.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=msg_id, id=t["attachment_id"])
                .execute()
            )
            t["data"] = base64.urlsafe_b64decode(a["data"])
        except Exception as loi:
            logger.warning("Không tải được tệp %s: %s", t.get("name"), loi)

    return {
        "message_id": msg_id,
        "from_email": dau.get("from", ""),
        "subject": dau.get("subject", "(không tiêu đề)"),
        "received_at": _gio(thu.get("internalDate")),
        "text": gom["text"].strip(),
        "files": [t for t in gom["files"] if t.get("data")],
    }


def danh_dau_da_doc(msg_id):
    try:
        _dich_vu().users().messages().modify(
            userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
        ).execute()
        return True
    except Exception as loi:
        logger.warning("Không đánh dấu đã đọc %s: %s", msg_id, loi)
        return False

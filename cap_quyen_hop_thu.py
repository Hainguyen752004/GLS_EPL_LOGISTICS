# -*- coding: utf-8 -*-
"""Cấp quyền cho bản demo đọc hộp thư đặt hàng.

    python cap_quyen_hop_thu.py

Chạy lệnh này khi màn Nhận đơn báo "Hộp thư: chưa nối". Nó mở trình duyệt để
đăng nhập Google, rồi ghi tệp quyền vào `secrets/token.json`. Sau đó khởi động
lại máy chủ là nút "Quét hộp thư" bật lên.

Bản demo chỉ xin quyền ĐỌC thư và đánh dấu đã đọc, không xin quyền gửi thư.

Cần gì trước khi chạy: `secrets/OAuth2.json` phải là tệp khoá OAuth còn hiệu lực
tải từ Google Cloud Console (mục APIs & Services -> Credentials -> OAuth client
ID kiểu Desktop app). Nếu khoá cũ đã bị thu hồi hay xoá thì tạo khoá mới, tải về
và thay tệp đó — token cũ không cứu được, Google từ chối với lỗi
"invalid_client".
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "app"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from services import gmail_service  # noqa: E402


def main():
    khoa = gmail_service.duong_dan_khoa()
    tok = gmail_service.duong_dan_token()

    if not os.path.exists(khoa):
        print("Không thấy tệp khoá OAuth: %s" % khoa)
        print("Tải OAuth client ID (Desktop app) từ Google Cloud Console rồi lưu vào đó.")
        return 1

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Thiếu thư viện. Chạy: pip install google-auth-oauthlib google-api-python-client")
        return 1

    print("Đang mở trình duyệt để đăng nhập Google...")
    luong = InstalledAppFlow.from_client_secrets_file(khoa, gmail_service.PHAM_VI)
    creds = luong.run_local_server(port=0)

    os.makedirs(os.path.dirname(tok), exist_ok=True)
    with open(tok, "w", encoding="utf-8") as f:
        f.write(creds.to_json())
    print("Đã ghi quyền vào: %s" % tok)

    dia_chi = gmail_service.dia_chi_hop_thu()
    print("Hộp thư đang nối: %s" % (dia_chi or "(không đọc được địa chỉ)"))
    print("Khởi động lại máy chủ rồi vào màn Nhận đơn, nút Quét hộp thư sẽ bật.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

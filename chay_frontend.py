# -*- coding: utf-8 -*-
"""Chạy RIÊNG giao diện EPL, không cần chạy chung tiến trình với backend.

    python chay_frontend.py                                   # trang :8080, API về :8001
    python chay_frontend.py --api http://senvangsolutions.com:1506
    python chay_frontend.py --cong 9000 --api http://192.168.1.50:8001

VÌ SAO CẦN TỆP NÀY. Mọi đường dẫn trong `frontend/index.html` đều bắt đầu bằng `/static/`
(44 tệp CSS và JS), nhưng trong thư mục `frontend/` KHÔNG có thư mục nào tên `static` — nó
do backend tạo ra lúc chạy:

    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

Nên bê nguyên thư mục `frontend/` lên một máy chủ tĩnh (nginx trỏ thẳng, `python -m
http.server`, hosting tĩnh, hay mở thẳng tệp) là mọi đường `/static/...` trả 404: trang hiện
ra trơ trụi, không CSS không JS. Tệp này dựng lại đúng phép ánh xạ đó.

BA PHÉP ÁNH XẠ, không hơn:
  /static/<đường>  →  frontend/<đường>          (bỏ tiền tố, đây là chỗ hay hỏng)
  /api/...         →  chuyển tiếp sang backend   (kèm token nếu có)
  /uploads/...     →  chuyển tiếp sang backend   (ảnh xe, ảnh tài xế, ảnh POD)
  còn lại          →  frontend/index.html

KHÔNG dùng cho môi trường thật có nhiều người dùng: đây là máy chủ của thư viện chuẩn, dựng
để demo và để chạy giao diện tách khỏi backend. Chạy thật thì để nginx làm, xem README.
"""
import argparse
import http.server
import os
import socketserver
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit

GOC = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(GOC, "frontend")
API_MAC_DINH = "http://127.0.0.1:8001"

#: Header thuộc về từng kết nối, không thuộc nội dung — chuyển tiếp là hỏng.
BO_HEADER = {"host", "connection", "keep-alive", "transfer-encoding", "upgrade",
             "proxy-authorization", "proxy-authenticate", "te", "trailer",
             "content-length", "content-encoding", "accept-encoding"}
#: Đường nào đi thẳng sang backend chứ không phải tệp tĩnh.
DUONG_API = ("/api/", "/uploads/")


def doc_token(duong_env):
    if duong_env and os.path.exists(duong_env):
        for dong in open(duong_env, encoding="utf-8"):
            if dong.strip().startswith("EPL_TMS_API_TOKEN="):
                return dong.split("=", 1)[1].strip().strip('"').strip("'")
    return os.getenv("EPL_TMS_API_TOKEN", "")


class Tay(http.server.SimpleHTTPRequestHandler):
    api_goc = API_MAC_DINH
    token = ""

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=WEB, **kw)

    def log_message(self, dang, *doi):
        sys.stdout.write("  %s\n" % (dang % doi))
        sys.stdout.flush()

    def translate_path(self, path):
        """ĐÂY LÀ CHỖ SỬA. `/static/js/app.js` phải đọc `frontend/js/app.js`.

        Bỏ tiền tố `/static` rồi mới giao cho bộ xử lý tệp tĩnh của thư viện chuẩn — nó vốn
        đã lo phần chống đi ngược thư mục (`..`), nên không tự ghép đường dẫn ở đây.
        """
        duong = urlsplit(path).path
        if duong == "/static" or duong.startswith("/static/"):
            path = duong[len("/static"):] or "/"
        return super().translate_path(path)

    def do_GET(self):
        if self.path.startswith(DUONG_API):
            return self._chuyen_tiep("GET")
        return self._tinh("GET")

    def do_HEAD(self):
        if self.path.startswith(DUONG_API):
            return self._chuyen_tiep("HEAD")
        return self._tinh("HEAD")

    def do_POST(self):
        return self._chuyen_tiep("POST")

    def do_PUT(self):
        return self._chuyen_tiep("PUT")

    def do_PATCH(self):
        return self._chuyen_tiep("PATCH")

    def do_DELETE(self):
        return self._chuyen_tiep("DELETE")

    def _tinh(self, phuong_thuc):
        """Tệp tĩnh. Đường không phải tệp thì trả index.html — giao diện tự định tuyến
        bằng `#mã-màn`, nên tải lại giữa chừng không được rơi vào 404."""
        duong = urlsplit(self.path).path
        that = self.translate_path(self.path)
        if duong != "/" and not os.path.isfile(that):
            self.path = "/index.html"
        if phuong_thuc == "HEAD":
            return super().do_HEAD()
        return super().do_GET()

    def _chuyen_tiep(self, phuong_thuc):
        dai = int(self.headers.get("Content-Length") or 0)
        than = self.rfile.read(dai) if dai else None
        yeu_cau = urllib.request.Request(self.api_goc + self.path, data=than, method=phuong_thuc)
        for ten, gia_tri in self.headers.items():
            if ten.lower() not in BO_HEADER:
                yeu_cau.add_header(ten, gia_tri)
        if self.token and not self.headers.get("Authorization"):
            yeu_cau.add_header("Authorization", "Bearer " + self.token)
        try:
            with urllib.request.urlopen(yeu_cau, timeout=180) as tra:
                noi_dung, ma, dau_ra = tra.read(), tra.status, tra.headers
        except urllib.error.HTTPError as loi:
            # LỖI NGHIỆP VỤ PHẢI ĐI QUA NGUYÊN VẸN: giao diện đọc `error.code` và `message`
            # để nói cho người dùng biết thiếu gì (sai thứ tự mốc, thiếu POD, hết hạn khung
            # giờ…). Thay bằng một lỗi chung là bịt mắt người đang đứng trước màn hình.
            noi_dung, ma, dau_ra = loi.read(), loi.code, loi.headers
        except Exception as loi:
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(('{"error":{"code":"KHONG_GOI_DUOC_API","message":'
                              '"Khong goi duoc %s: %s"}}' % (self.api_goc, loi)).encode("utf-8"))
            return
        self.send_response(ma)
        for ten, gia_tri in (dau_ra or {}).items():
            if ten.lower() not in BO_HEADER:
                self.send_header(ten, gia_tri)
        self.send_header("Content-Length", str(len(noi_dung)))
        self.end_headers()
        if phuong_thuc != "HEAD":
            self.wfile.write(noi_dung)

    def end_headers(self):
        # Tệp tĩnh không cache: sửa CSS xong tải lại là thấy, khỏi Ctrl+F5.
        if not self.path.startswith(DUONG_API):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()


class MayChu(socketserver.ThreadingTCPServer):
    """Nhiều luồng: một lời gọi API đi xa vài giây không được chặn cả trang."""
    allow_reuse_address = True
    daemon_threads = True


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--cong", type=int, default=int(os.getenv("PORT", "8080")))
    p.add_argument("--api", default=os.getenv("EPL_API_BASE", API_MAC_DINH),
                   help="gốc backend EPL, ví dụ http://senvangsolutions.com:1506")
    p.add_argument("--env", default=os.path.join(GOC, ".env"),
                   help="tệp .env để lấy EPL_TMS_API_TOKEN")
    a = p.parse_args()

    if not os.path.isdir(WEB):
        sys.exit("Không thấy thư mục frontend tại %s" % WEB)
    if not os.path.isfile(os.path.join(WEB, "index.html")):
        sys.exit("Không thấy frontend/index.html — chạy tệp này từ thư mục gốc EPL_System.")

    Tay.api_goc = a.api.rstrip("/")
    Tay.token = doc_token(a.env)

    print("EPL — giao diện chạy riêng")
    print("  Trang      : http://localhost:%d" % a.cong)
    print("  Tệp tĩnh   : %s   (/static/... → thư mục này)" % WEB)
    print("  API về     : %s   (%s)" % (Tay.api_goc, "có token" if Tay.token else "không có token"))
    print("  Dừng: Ctrl+C\n")
    sys.stdout.flush()
    with MayChu(("0.0.0.0", a.cong), Tay) as mc:
        try:
            mc.serve_forever()
        except KeyboardInterrupt:
            print("\nĐã dừng.")


if __name__ == "__main__":
    main()

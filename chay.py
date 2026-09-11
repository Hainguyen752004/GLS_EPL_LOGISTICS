# -*- coding: utf-8 -*-
"""Máy chủ nhỏ cho TRANG TÀI XẾ: phục vụ `web/` và chuyển tiếp `/api/...` sang máy chủ EPL.

    python chay.py                 # mở http://localhost:8080
    python chay.py --cong 9000     # đổi cổng
    python chay.py --api http://127.0.0.1:8001

VÌ SAO CẦN PROXY, không gọi thẳng API từ trình duyệt: máy chủ EPL chỉ cho phép CORS từ chính
nó (`EPL_CORS_ORIGINS`, mặc định `localhost:8001`). Một trang đặt ở địa chỉ khác gọi thẳng sẽ
bị trình duyệt chặn ở bước tiền kiểm — đo được: `OPTIONS /api/drivers` với `Origin` lạ trả
`400 Bad Request`. Chuyển tiếp qua chính máy chủ này thì trình duyệt thấy MỘT địa chỉ duy nhất,
không có CORS nào để vướng, và KHÔNG phải sửa cấu hình máy chủ EPL đang chạy thật.

TOKEN. Máy chủ EPL đang host mở (gọi không token vẫn 200) nên mặc định không gửi gì. Khi nào
bật token thì đặt biến môi trường `EPL_TMS_API_TOKEN` (hoặc `--token`) — nó được gắn Ở ĐÂY, phía
máy chủ, nên token KHÔNG nằm trong điện thoại tài xế.

GIỚI HẠN CỦA BẢN DEMO, nói rõ để không ai hiểu nhầm: trang này lọc chuyến theo tài xế ở phần
TRÌNH BÀY. Ai mở trang cũng chọn được tên người khác. Muốn thành thật thì đăng nhập và lọc ở
máy chủ — việc đó thuộc hệ thống cha, xem README.
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
WEB = os.path.join(GOC, "web")
API_MAC_DINH = "http://senvangsolutions.com:1506"
#: Header không được chuyển tiếp: chúng thuộc về từng kết nối, không thuộc về nội dung.
BO_HEADER = {"host", "connection", "keep-alive", "transfer-encoding", "upgrade",
             "proxy-authorization", "proxy-authenticate", "te", "trailer",
             "content-length", "content-encoding", "accept-encoding"}


class Tay(http.server.SimpleHTTPRequestHandler):
    api_goc = API_MAC_DINH
    token = ""

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=WEB, **kw)

    # --- ghi log gọn: một dòng một yêu cầu, không kèm chữ HTML dài ---
    def log_message(self, dang, *doi):
        sys.stdout.write("  %s\n" % (dang % doi))
        sys.stdout.flush()

    def do_GET(self):
        if self.path.startswith("/api/"):
            return self._chuyen_tiep("GET")
        return super().do_GET()

    def do_HEAD(self):
        if self.path.startswith("/api/"):
            return self._chuyen_tiep("HEAD")
        return super().do_HEAD()

    def do_POST(self):
        return self._chuyen_tiep("POST")

    def do_PUT(self):
        return self._chuyen_tiep("PUT")

    def do_PATCH(self):
        return self._chuyen_tiep("PATCH")

    def do_DELETE(self):
        return self._chuyen_tiep("DELETE")

    def _chuyen_tiep(self, phuong_thuc):
        if not self.path.startswith("/api/"):
            self.send_error(404, "Chi chuyen tiep duong /api/")
            return
        dai = int(self.headers.get("Content-Length") or 0)
        than = self.rfile.read(dai) if dai else None
        dich = self.api_goc + self.path
        yeu_cau = urllib.request.Request(dich, data=than, method=phuong_thuc)
        for ten, gia_tri in self.headers.items():
            if ten.lower() not in BO_HEADER:
                yeu_cau.add_header(ten, gia_tri)
        if self.token and not self.headers.get("Authorization"):
            yeu_cau.add_header("Authorization", "Bearer " + self.token)
        try:
            with urllib.request.urlopen(yeu_cau, timeout=120) as tra:
                noi_dung, ma, dau_ra = tra.read(), tra.status, tra.headers
        except urllib.error.HTTPError as loi:
            # LỖI NGHIỆP VỤ PHẢI ĐI QUA NGUYÊN VẸN. Trang tài xế đọc `detail.code` và
            # `message` để nói cho người dùng biết phải làm gì (sai thứ tự mốc, thiếu POD…);
            # thay nó bằng một lỗi chung là bịt mắt người đang đứng ở cổng cảng.
            noi_dung, ma, dau_ra = loi.read(), loi.code, loi.headers
        except Exception as loi:                                  # mất mạng, DNS, hết giờ
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(('{"detail":{"code":"KHONG_GOI_DUOC_API","message":'
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
        # Trang tĩnh không được cache: sửa xong tải lại là thấy, khỏi phải Ctrl+F5.
        if not self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()


class MayChu(socketserver.ThreadingTCPServer):
    """Nhiều luồng: một yêu cầu API đi xa vài giây không được chặn cả trang."""
    allow_reuse_address = True
    daemon_threads = True


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--cong", type=int, default=int(os.getenv("PORT", "8080")))
    p.add_argument("--api", default=os.getenv("EPL_API_BASE", API_MAC_DINH),
                   help="gốc máy chủ EPL, ví dụ http://senvangsolutions.com:1506")
    p.add_argument("--token", default=os.getenv("EPL_TMS_API_TOKEN", ""),
                   help="token API, gắn ở phía máy chủ này nên không lọt vào điện thoại")
    a = p.parse_args()
    Tay.api_goc = a.api.rstrip("/")
    Tay.token = a.token.strip()
    if not os.path.isdir(WEB):
        sys.exit("Khong thay thu muc web/ canh %s" % __file__)
    print("Trang tai xe : http://localhost:%d" % a.cong)
    print("API chuyen ve : %s%s" % (Tay.api_goc, "  (co token)" if Tay.token else "  (khong token)"))
    print("Dung: Ctrl+C\n")
    with MayChu(("0.0.0.0", a.cong), Tay) as may:
        try:
            may.serve_forever()
        except KeyboardInterrupt:
            print("\nDa dung.")


if __name__ == "__main__":
    main()

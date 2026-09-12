# -*- coding: utf-8 -*-
"""EPL Trợ lý — máy chủ nhỏ phục vụ trang chat, chạy tác tử và bộ giám sát thông báo.

    python chay.py                      # trang: http://localhost:8090 · API EPL: http://127.0.0.1:8001
    python chay.py --api http://senvangsolutions.com:1506 --cong 8090

Đọc `GEMINI_API_KEY_GT` và `EPL_TMS_API_TOKEN` từ `.env` của EPL_System (hoặc biến môi trường).
Hai khóa này nằm Ở ĐÂY, phía máy chủ; trình duyệt chỉ gửi câu hỏi lên `POST /hoi`.

Đường:
  POST /hoi        {cau_hoi, lich_su, ngon_ngu}  → STREAM text/event-stream:
                     event: cong_cu | cong_cu_xong | chu | xong | loi   (data: JSON)
  GET  /thong-bao?sau=ID                          → thông báo mới hơn ID (bộ giám sát)
  GET  /suc-khoe                                  → có khóa Gemini chưa, nối EPL được chưa

Không dùng khung web nào: chỉ thư viện chuẩn, để anh copy thư mục sang máy khác chạy được ngay.
"""
import argparse
import http.server
import json
import os
import socketserver
import sys
import time
import traceback
from urllib.parse import parse_qs, urlsplit

import canh_bao
import cong_cu
import tac_tu

GOC = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(GOC, "web")
ENV_MAC_DINH = os.path.normpath(os.path.join(GOC, "..", "EPL_System", ".env"))


def doc_env(duong):
    ra = {}
    if duong and os.path.exists(duong):
        for dong in open(duong, encoding="utf-8"):
            dong = dong.strip()
            if dong and not dong.startswith("#") and "=" in dong:
                k, v = dong.split("=", 1)
                ra[k.strip()] = v.strip().strip('"').strip("'")
    return ra


class Tay(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=WEB, **kw)

    def log_message(self, dang, *doi):
        chu = dang % doi
        if "/thong-bao" in chu:                    # trình duyệt hỏi mỗi 10 giây — không rải log
            return
        sys.stdout.write("  %s\n" % chu)
        sys.stdout.flush()

    def _json(self, ma, du_lieu):
        than = json.dumps(du_lieu, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(ma)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(than)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(than)

    def do_GET(self):
        duong = urlsplit(self.path)
        if duong.path == "/suc-khoe":
            return self._suc_khoe()
        if duong.path == "/thong-bao":
            sau = (parse_qs(duong.query).get("sau") or ["0"])[0]
            try:
                sau = int(sau)
            except ValueError:
                sau = 0
            return self._json(200, canh_bao.lay(sau))
        if duong.path == "/hoi":
            return self._json(405, {"loi": "Dùng POST /hoi với JSON {cau_hoi, lich_su, ngon_ngu}."})
        return super().do_GET()

    def do_POST(self):
        if urlsplit(self.path).path != "/hoi":
            return self._json(404, {"loi": "Không có đường này."})
        dai = int(self.headers.get("Content-Length") or 0)
        if dai > 600_000:
            return self._json(413, {"loi": "Nội dung gửi lên quá lớn."})
        try:
            than = json.loads(self.rfile.read(dai).decode("utf-8") or "{}")
        except Exception:
            return self._json(400, {"loi": "JSON không hợp lệ."})
        cau_hoi = (than.get("cau_hoi") or "").strip()
        if not cau_hoi:
            return self._json(400, {"loi": "Thiếu câu hỏi."})
        if len(cau_hoi) > 4000:
            return self._json(400, {"loi": "Câu hỏi quá dài (tối đa 4000 ký tự)."})
        lich_su = than.get("lich_su") or []
        if not isinstance(lich_su, list):
            lich_su = []
        lich_su = lich_su[-20:]                      # 10 lượt hỏi-đáp gần nhất là đủ ngữ cảnh
        ngon_ngu = than.get("ngon_ngu") or "vi"

        # --- stream SSE ---
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Connection", "close")
        self.end_headers()
        bat_dau = time.time()
        sys.stdout.write("\n? [%s] %s\n" % (ngon_ngu, cau_hoi[:120].replace("\n", " ")))
        sys.stdout.flush()

        def phat(su_kien, du_lieu):
            try:
                self.wfile.write(("event: %s\ndata: %s\n\n" % (
                    su_kien, json.dumps(du_lieu, ensure_ascii=False, default=str))).encode("utf-8"))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass                                 # người dùng đóng tab giữa chừng: cứ chạy nốt

        try:
            ket = tac_tu.tra_loi(cau_hoi, lich_su, ngon_ngu,
                                 ghi_log=lambda s: (sys.stdout.write(s + "\n"), sys.stdout.flush()),
                                 phat=phat)
        except Exception as loi:                     # không được để một câu hỏi làm sập máy chủ
            traceback.print_exc()
            ket = {"loi": "Máy chủ trợ lý gặp lỗi: %s" % loi}
        ket["giay"] = round(time.time() - bat_dau, 1)
        phat("loi" if ket.get("loi") else "xong", ket)
        sys.stdout.write("= %s trong %.1fs, %d công cụ\n" % (
            "lỗi" if ket.get("loi") else "xong", ket["giay"], len(ket.get("cong_cu_da_dung") or [])))
        sys.stdout.flush()

    def _suc_khoe(self):
        ket = {"gemini_co_khoa": bool(tac_tu.KHOA), "mo_hinh": tac_tu.MO_HINH,
               "epl_api": cong_cu.GOC_API, "epl_ok": False, "so_cong_cu": len(cong_cu.CONG_CU),
               "giam_sat": canh_bao.lay(10**12)}
        try:
            cong_cu.goi_api("/api/currencies", timeout=8)
            ket["epl_ok"] = True
        except cong_cu.LoiAPI as loi:
            ket["epl_loi"] = str(loi)[:200]
        return self._json(200, ket)

    def end_headers(self):
        if not self.path.startswith(("/hoi", "/suc-khoe", "/thong-bao")):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()


class MayChu(socketserver.ThreadingTCPServer):
    """Nhiều luồng: một câu hỏi chạy 5–30 giây không được chặn người khác."""
    allow_reuse_address = True
    daemon_threads = True


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--cong", type=int, default=int(os.getenv("PORT", "8090")))
    p.add_argument("--api", default=os.getenv("EPL_API_BASE", "http://127.0.0.1:8001"),
                   help="gốc máy chủ EPL")
    p.add_argument("--env", default=os.getenv("EPL_ENV_FILE", ENV_MAC_DINH),
                   help="tệp .env chứa GEMINI_API_KEY_GT và EPL_TMS_API_TOKEN")
    p.add_argument("--mo-hinh", default=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    p.add_argument("--khong-giam-sat", action="store_true", help="không chạy bộ giám sát thông báo")
    a = p.parse_args()

    env = doc_env(a.env)
    khoa = os.getenv("GEMINI_API_KEY_GT") or env.get("GEMINI_API_KEY_GT") or ""
    token = os.getenv("EPL_TMS_API_TOKEN") or env.get("EPL_TMS_API_TOKEN") or ""
    cong_cu.cau_hinh(a.api, token)
    tac_tu.cau_hinh(khoa, a.mo_hinh)

    print("EPL Trợ lý")
    print("  Trang        : http://localhost:%d" % a.cong)
    print("  API EPL      : %s  (%s)" % (a.api, "có token" if token else "KHÔNG có token"))
    print("  Gemini       : %s  (%s, suy nghĩ %d)" % (
        a.mo_hinh, "có khóa" if khoa else "THIẾU GEMINI_API_KEY_GT — chat sẽ báo lỗi", tac_tu.NGAN_SACH_SUY_NGHI))
    print("  Công cụ      : %d" % len(cong_cu.CONG_CU))
    print("  Giám sát     : %s" % ("tắt" if a.khong_giam_sat else "mỗi %d giây (báo giá mới, DO mới, xe xuất phát, xe hoàn tất)" % canh_bao.CHU_KY))
    print("  Dừng: Ctrl+C\n")
    sys.stdout.flush()
    if not a.khong_giam_sat:
        canh_bao.bat_dau()
    with MayChu(("0.0.0.0", a.cong), Tay) as mc:
        try:
            mc.serve_forever()
        except KeyboardInterrupt:
            print("\nĐã dừng.")


if __name__ == "__main__":
    main()

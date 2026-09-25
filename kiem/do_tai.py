# -*- coding: utf-8 -*-
"""ĐO TẢI — gọi từng API danh sách trên DB thử 1 năm (tools/gieo_tai_thu.py) và in thời gian · dung lượng · số dòng.

    python kiem/do_tai.py [nhan] [tu-den]          ví dụ: python kiem/do_tai.py truoc 1-12

Bộ đo TỰ BẬT máy chủ thử cổng 8012 trỏ vào epl_lao_tai (không đụng 8020 / 8001 / epl_lao). Mỗi API gọi 2 lần (lần đầu
làm nóng), in lần thứ hai. Quá 60 s thì ghi QUÁ GIỜ, TẮT máy chủ thử rồi bật lại — một yêu cầu treo không được giữ kết
nối DB làm sai số đo các API sau. `tu-den` chỉ đo một đoạn danh sách (mỗi lượt chạy dưới 10 phút). `nhan` (ví dụ
`truoc`, `sau`) ghi kết quả vào kiem/do_tai_<nhan>.json để so. Mục tiêu chủ dự án chốt: mọi màn dưới 1–2 giây.
"""
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

GOC = "http://127.0.0.1:8012"
NHAN = sys.argv[1] if len(sys.argv) > 1 else ""
DOAN = sys.argv[2] if len(sys.argv) > 2 else ""
GIOI_HAN = 60
THU_MUC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = r"C:\Users\zinnn\miniconda3\python.exe"
TK = {}
MAY = {}

# (vai, đường, màn dùng nó)
DS = [
    ("admin", "/api/trips", "Phiếu xuất xe · danh sách"),
    ("admin", "/api/trips?q=341", "Phiếu xuất xe · tìm"),
    ("admin", "/api/trips?transport_status=transit", "Phiếu xuất xe · đang chạy"),
    ("thabok", "/api/trips", "Bãi · danh sách phiếu"),
    ("ketoan", "/api/trips?finance_status=unpaid", "Kế toán · chưa thu"),
    ("tx01", "/api/trips", "Tài xế · phiếu của tôi"),
    ("admin", "/api/theo-doi", "Theo dõi (tracking)"),
    ("admin", "/api/theo-doi/su-co", "Theo dõi · sự cố"),
    ("admin", "/api/bao-cao/tong-quan", "Báo cáo tổng quan"),
    ("admin", "/api/bao-cao/xu-huong", "Báo cáo xu hướng"),
    ("admin", "/api/bao-cao/theo-doi?trang=1&co=100", "Báo cáo theo dõi · 1 trang"),
    ("admin", "/api/bao-cao/theo-doi/tong", "Báo cáo theo dõi · dòng tổng"),
    ("admin", "/api/bao-cao/can-tru", "Cấn trừ"),
    ("admin", "/api/bao-cao/xe-lien-ket", "Báo cáo xe liên kết"),
    ("admin", "/api/bao-cao/tien-tai-xe", "Tiền chuyến tài xế"),
    ("admin", "/api/dem-viec", "Đếm việc (thanh menu)"),
    ("ketoan", "/api/chung-tu", "Chứng từ"),
    ("ketoan", "/api/ke-toan/trang-thai", "Kế toán · trạng thái đẩy"),
    ("ketoan", "/api/hoa-don-gop", "Hoá đơn gộp"),
    ("ketoan", "/api/hoa-don-gop/cho-gop", "Hoá đơn · chờ gộp"),
    ("ketoan", "/api/tat-toan?chi_tiet=0", "Tất toán"),
    ("admin", "/api/vouchers", "Phiếu lĩnh"),
    ("admin", "/api/fuel-moves", "Kho nhiên liệu · nhập xuất"),
    ("admin", "/api/kho-hang", "Kho hàng"),
    ("admin", "/api/vehicles", "Xe"),
    ("admin", "/api/drivers", "Tài xế"),
    ("admin", "/api/trailers", "Rơ-moóc"),
    ("admin", "/api/customers", "Khách hàng"),
    ("admin", "/api/owners", "Chủ xe liên kết"),
    ("admin", "/api/suppliers", "Nhà cung cấp"),
    ("admin", "/api/hop-dong", "Hợp đồng"),
    ("admin", "/api/lenh-sua-chua", "Lệnh sửa chữa"),
    ("admin", "/api/the-cao-toc", "Thẻ cao tốc"),
    ("admin", "/api/ban-hang", "Bán hàng"),
    ("admin", "/api/routes", "Tuyến đường"),
]


def dang_nhap(u):
    r = urllib.request.Request(GOC + "/api/dang-nhap", data=json.dumps({"username": u, "password": "1234"}).encode(),
                               headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=60).read())["token"]


def tat_may():
    if MAY.get("p"):
        MAY["p"].kill(); MAY["p"].wait(); MAY.pop("p")


def bat_may():
    tat_may()
    env_goc = open(os.path.join(THU_MUC, ".env"), encoding="utf-8").read()
    u = re.search(r"^DATABASE_URL\s*=\s*(\S+)", env_goc, re.M).group(1).strip("\"'")
    env = dict(os.environ, DATABASE_URL=u.rsplit("/", 1)[0] + "/epl_lao_tai", PYTHONUNBUFFERED="1", EPL_LAO_LAM_NONG="0")   # đo "lần đầu" thật: tắt tính sẵn
    log = open(os.path.join(os.environ.get("TEMP", "."), "epl_lao_8012.log"), "a", encoding="utf-8")
    MAY["p"] = subprocess.Popen([PY, "-X", "utf8", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8012"],
                                cwd=os.path.join(THU_MUC, "backend"), env=env, stdout=log, stderr=log)
    for _ in range(80):
        try:
            urllib.request.urlopen(GOC + "/api/tai-khoan-mau", timeout=2)
            break
        except Exception:  # noqa: BLE001
            time.sleep(0.5)
    TK.clear()
    for v in {v for v, _, _ in DS}:
        TK[v] = dang_nhap(v)
    print("  (bật máy chủ thử 8012 · PID %d)" % MAY["p"].pid, flush=True)


def goi(vai, duong):
    r = urllib.request.Request(GOC + duong, headers={"Authorization": "Bearer " + TK[vai]})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(r, timeout=GIOI_HAN) as t:
            du = t.read()
            ms = (time.perf_counter() - t0) * 1000
            tong = t.headers.get("X-Tong")
    except urllib.error.HTTPError as e:
        return {"loi": "HTTP %d" % e.code, "ms": (time.perf_counter() - t0) * 1000}
    except (socket.timeout, TimeoutError, urllib.error.URLError):
        return {"loi": "QUÁ GIỜ > %d s" % GIOI_HAN, "ms": GIOI_HAN * 1000}
    g = json.loads(du or b"null")
    dong = len(g) if isinstance(g, list) else (len(g.get("ds") or g.get("data") or g.get("items") or []) if isinstance(g, dict) else 0)
    return {"ms": ms, "kb": len(du) / 1024, "dong": dong, "tong": tong}


def xoa_dem():
    """Xoá bản báo cáo đã tính (bảng bao_cao_dem của DB THỬ) — "lần đầu" phải là tính thật, không phải lấy lại."""
    from sqlalchemy import create_engine, text
    u = re.search(r"^DATABASE_URL\s*=\s*(\S+)", open(os.path.join(THU_MUC, ".env"), encoding="utf-8").read(), re.M).group(1).strip("\"'")
    e = create_engine(u.rsplit("/", 1)[0] + "/epl_lao_tai")
    with e.begin() as c:
        c.execute(text("CREATE TABLE IF NOT EXISTS bao_cao_dem (khoa varchar PRIMARY KEY, pb varchar NOT NULL, du_lieu text NOT NULL, luc timestamp NOT NULL DEFAULT now())"))
        c.execute(text("DELETE FROM bao_cao_dem"))


def main():
    ds = DS
    xoa_dem()
    if DOAN:
        a, b = (int(x) for x in DOAN.split("-"))
        ds = DS[a - 1:b]
    bat_may()
    print("Đo trên %s · DB epl_lao_tai%s\n" % (GOC, (" · nhãn " + NHAN) if NHAN else ""), flush=True)
    print("%-34s %-44s %9s %9s %9s %8s" % ("Màn", "API", "lần đầu", "lần sau", "KB", "dòng"), flush=True)
    ra = {}
    try:
        for vai, duong, man in ds:
            k1 = goi(vai, duong)              # lần đầu: bộ đệm báo cáo đã xoá → tính thật
            k = k1
            if k1.get("loi", "").startswith("QUÁ GIỜ"):
                bat_may()                     # yêu cầu treo vẫn giữ kết nối DB → tắt hẳn, bật lại
            elif k1["ms"] < 60000:
                k = goi(vai, duong)           # lần sau: như người thứ hai mở cùng màn
            ra["%s %s" % (vai, duong)] = dict(k, man=man, ms_dau=k1["ms"])
            if k.get("loi"):
                print("%-34s %-44s %9.0f %9s  %s" % (man, duong, k1["ms"], "", k["loi"]), flush=True)
            else:
                print("%-34s %-44s %9.0f %9.0f %9.0f %8s%s%s" % (man, duong, k1["ms"], k["ms"], k["kb"], k["dong"],
                                                               (" / " + k["tong"]) if k.get("tong") else "",
                                                               "  ⚠ chậm" if k["ms"] > 2000 else ""), flush=True)
    finally:
        tat_may()
    cham = [k for k in ra.values() if k.get("loi") or k["ms"] > 2000]
    print("\n%d / %d API chậm hơn 2 giây hoặc lỗi" % (len(cham), len(ra)), flush=True)
    if NHAN:
        tep = os.path.join(os.path.dirname(os.path.abspath(__file__)), "do_tai_%s.json" % NHAN)
        cu = json.load(open(tep, encoding="utf-8")) if os.path.exists(tep) else {}
        cu.update(ra)
        with open(tep, "w", encoding="utf-8") as f:
            json.dump(cu, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()

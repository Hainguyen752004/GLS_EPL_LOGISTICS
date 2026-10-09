# -*- coding: utf-8 -*-
"""Thử bản tiếng Lào / tiếng Anh của câu lỗi API (09/10/2026) — services/loi_dich.py + backend/app/services/loi_dich.json.

    python kiem/thu_loi_dich.py

1. Danh mục đủ: mọi câu lỗi trong mã có bản lo + en, {n} khớp (tools/sinh_loi_dich.py --kiem) — thêm câu mới mà quên dịch là bài này
   SAI; câu bên hệ kế toán (tools/sinh_loi_dich_ke_toan.py --kiem) cũng vậy.
2. Từng mẫu: điền giá trị thử vào chỗ {n} của câu vi → dich() ra đúng mẫu lo / en với cùng giá trị (không mẫu nào bị mẫu khác "nuốt").
3. Câu ghép: giá trị chèn là cụm có bản dịch ("chưa xuất phát") → câu Lào / Anh không còn chữ Việt.
4. Qua API (giao dịch trên bản sao _d7, cuối ROLLBACK): 404 KHONG_THAY, 409 XE_CHUA_VE (giá trị chèn đúng chỗ), bảng rà khoá phiếu
   (canh_bao), câu đã dịch sẵn trong mã (_loi3) giữ nguyên bản dịch của mã.
"""
import json
import os
import re
import subprocess
import sys

GOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
URL = open(os.path.join(GOC, ".may_thu", "url_epl_lao_d7.txt"), encoding="utf-8").read().strip()
if "_d7" not in URL.rsplit("/", 1)[-1]:
    sys.exit("Chuỗi nối không trỏ bản sao _d7 — bài chỉ chạy trên bản sao.")
os.environ["DATABASE_URL"] = URL
os.environ["EPL_DANG_NHAP_GLS"] = "0"
sys.path.insert(0, os.path.join(GOC, "backend", "app"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

from fastapi.testclient import TestClient               # noqa: E402
from sqlalchemy import create_engine, text              # noqa: E402
from sqlalchemy.orm import Session                      # noqa: E402

from database import get_db                             # noqa: E402
from main import app                                    # noqa: E402
from services import loi_dich as LD                     # noqa: E402

KQ = []
DANG_CHAY = "ab65dc282091"
LAO = re.compile(r"[຀-໿]")
# chữ Việt có dấu không có trong tiếng Anh / Lào — còn sót là câu lai
VIET = re.compile(r"[ăâđêôơưĂÂĐÊÔƠƯàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ]")


def dung(dk, ten, ct=""):
    KQ.append(bool(dk))
    print(("  ✓ " if dk else "  SAI ") + ten + ((" — " + str(ct)[:300]) if ct != "" else ""))


def main():
    print("== 1. danh mục đủ bản dịch")
    r = subprocess.run([sys.executable, "-X", "utf8", os.path.join(GOC, "tools", "sinh_loi_dich.py"), "--kiem"], capture_output=True,
                       text=True, encoding="utf-8")
    dung(r.returncode == 0, "mọi câu lỗi trong mã có bản Lào + Anh, {n} khớp", (r.stdout or r.stderr).strip()[:300])
    r = subprocess.run([sys.executable, "-X", "utf8", os.path.join(GOC, "tools", "sinh_loi_dich_ke_toan.py"), "--kiem"], capture_output=True,
                       text=True, encoding="utf-8")
    dung(r.returncode == 0, "câu lỗi bên hệ kế toán (loi_dich_ke_toan.json) có bản Lào + Anh, {n} khớp", (r.stdout or r.stderr).strip()[:300])

    print("== 2. từng mẫu: giá trị chèn vào đúng chỗ")
    dm = json.load(open(LD.TEP, encoding="utf-8"))
    dm.update({k: v for k, v in json.load(open(LD.TEP_KE_TOAN, encoding="utf-8")).items() if k not in dm})
    sai, lai_vi, thieu_lao = [], [], []
    for vi, d in dm.items():
        if not d.get("lo") or not d.get("en"):
            continue
        thu = re.sub(r"\{(\d+)\}", lambda m: "Q%sQ" % m.group(1), vi)
        for lang in ("lo", "en"):
            mong = re.sub(r"\{(\d+)\}", lambda m: "Q%sQ" % m.group(1), d[lang])
            ra = LD.dich(thu, lang)
            if ra != mong:
                sai.append((vi[:80], lang, (ra or "")[:80]))
            if ra and VIET.search(ra):
                lai_vi.append((vi[:60], lang, ra[:80]))
        if not LAO.search(d["lo"]):
            thieu_lao.append(vi[:80])
    dung(not sai, "%d mẫu × 2 tiếng: dịch đúng mẫu, giá trị chèn đúng chỗ" % len(dm), sai[:3])
    dung(not lai_vi, "bản Lào / Anh không còn chữ Việt có dấu", lai_vi[:3])
    dung(not thieu_lao, "bản lo viết bằng chữ Lào", thieu_lao[:3])

    print("== 3. câu ghép từ cụm có bản dịch")
    cau = "Chưa chi tiền tạm ứng (mục IV chưa 'đã chi') — tài xế chưa nhận tiền thì chưa xuất phát."
    lo, en = LD.dich(cau, "lo"), LD.dich(cau, "en")
    dung(lo and en and not VIET.search(lo) and not VIET.search(en), "«… thì chưa xuất phát»: cụm chèn cũng được dịch", (lo, en))
    dung(LD.dich("Câu này không có trong danh mục.", "lo") is None, "câu ngoài danh mục: không gắn bản dịch (giữ tiếng Việt)")
    kt = json.load(open(LD.TEP_KE_TOAN, encoding="utf-8"))
    cau_kt = next(k for k in sorted(kt) if not re.search(r"\{\d+\}", k) and k.endswith("."))
    boc = "Hệ kế toán từ chối: " + cau_kt
    lo, en = LD.dich(boc, "lo"), LD.dich(boc, "en")
    dung(lo and en and LAO.search(lo) and not VIET.search(lo) and not VIET.search(en) and kt[cau_kt]["en"] in en,
         "«Hệ kế toán từ chối: <câu bên kế toán>»: dịch cả lớp EPL lẫn câu bên kế toán", (cau_kt, lo, en))
    x = LD.them_dich({"ma": "A", "loi": "Không có phiếu này.", "ds": [{"ma": "B", "loi": "Không có phiếu này."}]})
    dung(LAO.search(x.get("loi_lo") or "") and x["ds"][0].get("loi_en"), "them_dich gắn cả {ma, loi} lồng trong danh sách", x)

    print("== 4. qua API (rollback)")
    eng = create_engine(URL, connect_args={"options": "-c timezone=UTC"})
    conn = eng.connect()
    ngoai = conn.begin()
    db = Session(bind=conn, join_transaction_mode="create_savepoint", autoflush=False)

    def _db():
        try:
            yield db
        finally:
            db.rollback()
    app.dependency_overrides[get_db] = _db
    c = TestClient(app, raise_server_exceptions=False)
    try:
        tk = {u: c.post("/api/dang-nhap", json={"username": u, "password": "1234"}).json()["token"] for u in ("ketoan", "ketoancp")}
        h = lambda u: {"Authorization": "Bearer " + tk[u]}            # noqa: E731
        r = c.get("/api/trips/khong-co-phieu", headers=h("ketoan"))
        d = r.json().get("detail") or {}
        dung(r.status_code == 404 and LAO.search(d.get("loi_lo") or "") and d.get("loi_en"), "404 KHONG_THAY: có loi_lo + loi_en", d)
        r = c.post("/api/trips/%s/khoa" % DANG_CHAY, json={"xac_nhan": True}, headers=h("ketoan"))
        d = r.json().get("detail") or {}
        dung(r.status_code == 409 and d.get("ma") == "XE_CHUA_VE" and "dispatched" in (d.get("loi_lo") or "")
             and "dispatched" in (d.get("loi_en") or ""), "409 XE_CHUA_VE: giá trị chèn (trạng thái) nằm trong bản Lào / Anh", d)
        r = c.get("/api/trips/%s/kiem-lai" % DANG_CHAY, headers=h("ketoan"))
        cb = r.json().get("canh_bao") or []
        dung(r.status_code == 200 and cb and all(x.get("loi_lo") and x.get("loi_en") for x in cb),
             "bảng rà khoá phiếu: mọi điểm cần xem có bản Lào / Anh", [(x.get("ma"), (x.get("loi_lo") or "")[:40]) for x in cb])
        r = c.post("/api/trips/%s/chi-that" % DANG_CHAY, json={"dong": [{"id": "khong-co", "chi_that": 1}]}, headers=h("ketoancp"))
        d = r.json().get("detail") or {}
        dung(r.status_code in (403, 409) and d.get("loi_lo"), "câu đã dịch sẵn trong mã (_loi3) vẫn mang bản dịch", d)
        r = c.post("/api/dang-nhap", json={"username": "ketoan", "password": "sai-mat-khau"})
        d = r.json().get("detail") or {}
        dung(r.status_code == 401 and LAO.search(d.get("loi_lo") or ""), "sai mật khẩu: câu báo có bản Lào", d)
    finally:
        db.close()
        ngoai.rollback()
        conn.close()
        app.dependency_overrides.clear()
    print("\n%d/%d đúng" % (sum(KQ), len(KQ)))
    sys.exit(0 if all(KQ) else 1)


if __name__ == "__main__":
    main()

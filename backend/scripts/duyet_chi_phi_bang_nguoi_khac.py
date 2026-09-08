# -*- coding: utf-8 -*-
"""Duyệt chi phí thực của các chuyến đã trình, DƯỚI DANH TÍNH MỘT NGƯỜI KHÁC.

VÌ SAO CẦN MỘT TỆP RIÊNG. Bảng chi phí thực đi qua hai tay: người vận hành
TRÌNH, trưởng phòng tài chính DUYỆT. Máy chủ chặn người tạo tự duyệt chính
bảng của mình — quy tắc bốn mắt, và nó là một chốt kiểm soát thật chứ không
phải thủ tục giấy tờ: người nhập con số không được là người xác nhận con số đó
đúng.

Hệ quả là `don_va_gieo_10_case_demo.py` chỉ TRÌNH được, vì nó chạy dưới một
danh tính duy nhất. Tệp này bổ khuyết đúng phần đó: nó dựng một máy chủ TẠM
mang danh tính trưởng phòng tài chính, gọi duyệt qua đường API bình thường, rồi
tắt máy chủ đó đi.

VÌ SAO KHÔNG SỬA THẲNG BẢNG. Một câu `UPDATE ... SET status='approved'` cho ra
đúng con số trên báo cáo, nhưng nó không đi qua chốt kiểm nào, không ghi ai đã
duyệt, và không có dòng nhật ký kiểm toán. Sau đó không ai trả lời được câu
"ai duyệt khoản này" — mà đó chính là câu mà cả quy tắc bốn mắt tồn tại để trả
lời được.

CÁCH CHẠY (máy chủ chính đang chạy ở cổng 8011):

    python scripts/duyet_chi_phi_bang_nguoi_khac.py

Đổi người duyệt bằng `EPL_NGUOI_DUYET`, cổng tạm bằng `EPL_CONG_TAM`.
"""

import io
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

GOC = os.environ.get("EPL_GOC", "http://127.0.0.1:8011")
CONG_TAM = int(os.environ.get("EPL_CONG_TAM", "8019"))
GOC_TAM = "http://127.0.0.1:%d" % CONG_TAM
NGUOI_DUYET = os.environ.get("EPL_NGUOI_DUYET", "truong-phong-tai-chinh")
THU_MUC_APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")


def goi(goc, duong, than=None, cach="GET", dau=None):
    tieu_de = {"Content-Type": "application/json"}
    if dau:
        tieu_de["Idempotency-Key"] = dau
    yc = urllib.request.Request(
        goc + duong,
        data=json.dumps(than, ensure_ascii=False).encode("utf-8") if than is not None else None,
        method=cach, headers=tieu_de)
    try:
        with urllib.request.urlopen(yc, timeout=90) as tra:
            return tra.status, json.loads(tra.read().decode("utf-8", "replace") or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw or "{}")
        except ValueError:
            return e.code, {"detail": raw[:300]}
    except Exception as e:                                        # noqa: BLE001
        return 0, {"detail": "%s: %s" % (type(e).__name__, e)}


def chu(g):
    if not isinstance(g, dict):
        return str(g)[:200]
    for lay in (lambda: g["message"], lambda: g["error"]["message"],
                lambda: g["detail"]["message"], lambda: g["detail"]):
        try:
            v = lay()
            if isinstance(v, str) and v.strip():
                return v.strip()[:200]
        except (KeyError, TypeError):
            continue
    return json.dumps(g, ensure_ascii=False)[:200]


def du_lieu(g):
    if isinstance(g, list):
        return g
    return (g or {}).get("data", g) or {}


def main():
    print("Người duyệt:", NGUOI_DUYET, "· cổng tạm:", CONG_TAM)

    ma, g = goi(GOC, "/api/tms/finance/costs")
    ds = du_lieu(g)
    ds = ds if isinstance(ds, list) else (ds.get("items") or [])
    cho_duyet = [x for x in ds if str(x.get("status") or "") == "submitted"]
    print("Bảng chi phí đang chờ duyệt:", len(cho_duyet))
    if not cho_duyet:
        print("Không có gì để duyệt.")
        return 0

    moi_truong = dict(os.environ)
    moi_truong["EPL_TMS_API_PRINCIPAL"] = NGUOI_DUYET
    moi_truong.setdefault("EPL_ENV_FILE",
                          os.path.join(os.path.dirname(THU_MUC_APP), "..", ".env.sqlite"))
    moi_truong["PYTHONUNBUFFERED"] = "1"
    tien_trinh = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "127.0.0.1", "--port", str(CONG_TAM)],
        cwd=THU_MUC_APP, env=moi_truong,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        # Chờ máy chủ tạm trả lời, tối đa 40 giây.
        for _ in range(40):
            ma, _ = goi(GOC_TAM, "/api/health")
            if ma == 200:
                break
            time.sleep(1)
        else:
            print("Máy chủ tạm không lên được — không duyệt được.")
            return 1

        xong = 0
        for x in cho_duyet:
            ma_cp = x.get("id")
            pb = int(x.get("version") or 1)
            ma, g = goi(GOC_TAM, "/api/tms/finance/costs/%s/approve" % ma_cp,
                        {"expected_version": pb}, "POST",
                        dau="duyet-%s" % ma_cp)
            ok = ma == 200
            xong += 1 if ok else 0
            print("   %-40s -> %s %s" % (ma_cp, ma, chu(g)[:110]))
        print("Đã duyệt %d/%d bảng chi phí." % (xong, len(cho_duyet)))
    finally:
        tien_trinh.terminate()
        try:
            tien_trinh.wait(timeout=15)
        except subprocess.TimeoutExpired:
            tien_trinh.kill()
        print("Đã tắt máy chủ tạm.")

    ma, g = goi(GOC, "/api/tms/reporting/transport-revenue")
    d = du_lieu(g)
    tong = (d.get("summary") or {}) if isinstance(d, dict) else {}
    print("Báo cáo doanh thu sau khi duyệt:", json.dumps(tong, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

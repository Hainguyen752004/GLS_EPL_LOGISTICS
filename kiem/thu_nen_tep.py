# -*- coding: utf-8 -*-
"""Thử NÉN TỆP trước khi tải lên + giới hạn ở máy chủ (chủ dự án chốt 24/09: nghìn chuyến / ngày).

    <python có playwright + Pillow> kiem/thu_nen_tep.py [http://127.0.0.1:8011]

· Trình duyệt thật: ảnh điện thoại 4000×3000 (nhiều chi tiết như ảnh phiếu cân) qua EPL.nenTep còn ≤ 200 KB, vẫn là JPEG,
  cạnh dài ≤ 1600 px; PDF 3 MB bị chặn ngay trên máy với câu dễ hiểu; PDF nhỏ giữ nguyên.
· Máy chủ: ảnh chưa nén 1,5 MB → 422; PDF 2,5 MB → 422; ảnh đã nén → 200. Bài tự lập phiếu thử và tự xoá.
"""
import base64
import io
import json
import random
import sys
import time
import urllib.error
import urllib.request
import uuid

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

GOC = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"
TK = {}


def goi(duong, body=None, vai=None, method=None):
    du = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(GOC + duong, data=du, method=method or ("POST" if du is not None else "GET"),
                               headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + TK[vai]} if vai else {})})
    with urllib.request.urlopen(r, timeout=60) as t:
        return json.loads(t.read() or b"null")


def tai_len(tid, ten, kieu, du):
    b = uuid.uuid4().hex
    than = (b"--%s\r\nContent-Disposition: form-data; name=\"kind\"\r\n\r\npod\r\n" % b.encode()
            + b"--%s\r\nContent-Disposition: form-data; name=\"tep\"; filename=\"%s\"\r\nContent-Type: %s\r\n\r\n" % (b.encode(), ten.encode(), kieu.encode())
            + du + b"\r\n--%s--\r\n" % b.encode())
    r = urllib.request.Request(GOC + "/api/trips/%s/tep" % tid, data=than, method="POST",
                               headers={"Content-Type": "multipart/form-data; boundary=" + b, "Authorization": "Bearer " + TK["thabok"]})
    try:
        with urllib.request.urlopen(r, timeout=60) as t:
            return t.status, json.loads(t.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def anh_dien_thoai():
    """4000×3000, nhiễu + chữ — giống ảnh chụp phiếu cân, khó nén."""
    random.seed(7)
    im = Image.effect_noise((4000, 3000), 40).convert("RGB")
    d = ImageDraw.Draw(im)
    for i in range(60):
        d.text((100 + (i % 6) * 640, 80 + (i // 6) * 280), "PHIEU CAN 40.25 t · T4-0445-09", fill=(10, 10, 10))
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=95)
    return buf.getvalue()


def main():
    for u in ("thabok", "admin"):
        TK[u] = goi("/api/dang-nhap", {"username": u, "password": "1234"})["token"]
    goc = anh_dien_thoai()
    print("✓ ảnh thử: 4000×3000 · %.1f MB" % (len(goc) / 1048576))
    with sync_playwright() as pw:
        b = pw.chromium.launch(); pg = b.new_page()
        pg.goto(GOC + "/", wait_until="networkidle")
        kq = pg.evaluate("""async (b64) => {
          const bin = atob(b64), u8 = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
          const f = new File([u8], 'IMG_2026.jpg', { type: 'image/jpeg' });
          const t0 = performance.now(); const n = await EPL.nenTep(f); const ms = performance.now() - t0;
          const img = await new Promise(r => { const i = new Image(); i.onload = () => r(i); i.src = URL.createObjectURL(n); });
          let pdfLoi = ''; try { await EPL.nenTep(new File([new Uint8Array(3 * 1048576)], 'hop-dong.pdf', { type: 'application/pdf' })); } catch (e) { pdfLoi = e.message; }
          const nho = new File([new Uint8Array(5000)], 'nho.pdf', { type: 'application/pdf' });
          const giu = await EPL.nenTep(nho);
          return { size: n.size, type: n.type, w: img.naturalWidth, h: img.naturalHeight, ms, pdfLoi, giuNguyen: giu === nho };
        }""", base64.b64encode(goc).decode())
        b.close()
    assert kq["size"] <= 200 * 1024 and kq["type"] == "image/jpeg" and max(kq["w"], kq["h"]) <= 1600, kq
    print("✓ trình duyệt nén: %.1f MB → %d KB · %d×%d · %.0f ms" % (len(goc) / 1048576, kq["size"] // 1024, kq["w"], kq["h"], kq["ms"]))
    assert kq["pdfLoi"] and "2 MB" in kq["pdfLoi"], kq["pdfLoi"]
    print("✓ PDF 3 MB bị chặn ngay trên máy: «%s»" % kq["pdfLoi"])
    assert kq["giuNguyen"], "PDF nhỏ phải giữ nguyên"
    print("✓ PDF nhỏ giữ nguyên")

    xe = goi("/api/vehicles", vai="thabok"); kh = goi("/api/customers", vai="thabok"); tx = goi("/api/drivers", vai="thabok")
    p = goi("/api/trips", {"doc_no": "THU-NEN-%s/EPL" % time.strftime("%H%M%S"), "company": "EPL",
                           "vehicle_id": next(x for x in xe if x["owner_type"] != "joint")["id"], "driver_id": tx[0]["id"], "customer_id": kh[0]["id"],
                           "doc_date": time.strftime("%Y-%m-%d"), "note": "thử nén tệp"}, "thabok")
    try:
        im = Image.effect_noise((2600, 2000), 60).convert("RGB"); buf = io.BytesIO(); im.save(buf, "JPEG", quality=97)
        lon = buf.getvalue()
        s, g = tai_len(p["id"], "chua-nen.jpg", "image/jpeg", lon)
        assert s == 422 and g["detail"]["ma"] == "TEP_QUA_LON", (s, g); print("✓ máy chủ chặn ảnh chưa nén %.1f MB: «%s»" % (len(lon) / 1048576, g["detail"]["loi"]))
        s, g = tai_len(p["id"], "to.pdf", "application/pdf", b"%PDF-1.4\n" + b"0" * int(2.5 * 1048576))
        assert s == 422, (s, g); print("✓ máy chủ chặn PDF 2,5 MB: «%s»" % g["detail"]["loi"])
        s, g = tai_len(p["id"], "da-nen.jpg", "image/jpeg", b"\xff\xd8\xff\xe0" + b"1" * 150000 + b"\xff\xd9")
        assert s == 200, (s, g); print("✓ máy chủ nhận ảnh đã nén 150 KB")
    finally:
        goi("/api/trips/%s" % p["id"], vai="admin", method="DELETE"); print("  dọn phiếu thử")
    print("\n✅ NÉN TỆP: ảnh điện thoại còn ≤ 200 KB trên máy · PDF > 2 MB chặn · máy chủ chặn ảnh > 1 MB, PDF > 2 MB, mỗi lần > 10 MB")


if __name__ == "__main__":
    main()

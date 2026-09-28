# -*- coding: utf-8 -*-
"""Thử KÝ NHẬN GIAO HÀNG trên màn ĐIỆN THOẠI tài xế — Chromium thật (Playwright), cỡ 390×844, cảm ứng.

    <python có playwright> kiem/thu_ky_nhan_dien_thoai.py [http://127.0.0.1:8011]

1. Còn mạng: mở "Giao hàng hoàn tất", người nhận VẼ chữ ký bằng tay, thêm ảnh, gửi → phiếu có chữ ký, khối POD đầy.
2. MẤT MẠNG: ký phiếu thứ hai → vào hàng đợi, thẻ hiện "chờ gửi".
3. CÓ MẠNG LẠI: hàng đợi tự gửi, máy chủ có chữ ký của phiếu thứ hai.
4. "Xem biên bản" mở tờ in có chữ ký.
Bài tự lập hai phiếu thử (tài xế tx01) và tự xoá.
"""
import json
import os
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright

GOC = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"
RA = os.path.join(tempfile.gettempdir(), "epl_thu_ky_nhan")
os.makedirs(RA, exist_ok=True)
TK = {}


def goi(duong, body=None, vai=None, method=None):
    du = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(GOC + duong, data=du, method=method or ("POST" if du is not None else "GET"),
                               headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + TK[vai]} if vai else {})})
    with urllib.request.urlopen(r, timeout=60) as t:
        return json.loads(t.read() or b"null")


def main():
    for u in ("thabok", "admin", "tx01"):
        g = goi("/api/dang-nhap", {"username": u, "password": "1234"}); TK[u] = g["token"]
        if u == "tx01": tx = g["user"]
    xe = goi("/api/vehicles", vai="thabok"); kh = goi("/api/customers", vai="thabok"); tuyen = goi("/api/routes", vai="thabok")
    nha = next(x for x in xe if x["owner_type"] != "joint")
    ids = []
    for i in (1, 2):
        p = goi("/api/trips", {"doc_no": "THU-KYDT-%s-%d/EPL" % (time.strftime("%H%M%S"), i), "company": "EPL", "vehicle_id": nha["id"],
                               "driver_id": tx["driver_id"], "customer_id": kh[0]["id"], "route_id": tuyen[0]["id"],
                               "doc_date": time.strftime("%Y-%m-%d"), "weight_origin": 40, "note": "thử ký điện thoại"}, "thabok")
        goi("/api/trips/%s/transport-status" % p["id"], {"status": "transit"}, "admin")
        ids.append(p)
    loi = []
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
                                locale="vi-VN", geolocation={"latitude": 17.9757, "longitude": 102.6331}, permissions=["geolocation"])
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: loi.append("JS: %s" % e))
            pg.goto(GOC + "/", wait_until="networkidle")
            pg.fill("#lgU", "tx01"); pg.fill("#lgP", "1234"); pg.click("#lgBtn")
            pg.wait_for_selector("#app:not([hidden])"); pg.wait_for_timeout(800)
            if pg.eval_on_selector("#langApp .ln-nut", "b => b.title") != "Tiếng Việt":
                pg.click("#langApp .ln-nut"); pg.wait_for_timeout(250); pg.click('#langApp .ln-muc[data-lang="vi"]'); pg.wait_for_timeout(400)
            pg.wait_for_selector('[data-gh="%s"]' % ids[0]["id"], timeout=15000)

            def ky(pid, ten):
                pg.click('[data-gh="%s"]' % pid); pg.wait_for_selector("#pct-gh[open]"); pg.wait_for_timeout(700)
                pg.fill("#pct-gh-ten", ten); pg.fill("#pct-gh-sdt", "020 5555 1234")
                hop = pg.query_selector("#pct-gh-canvas").bounding_box()
                pg.mouse.move(hop["x"] + 30, hop["y"] + 120); pg.mouse.down()
                for k in range(1, 30):
                    pg.mouse.move(hop["x"] + 30 + k * 10, hop["y"] + 120 - (40 if k % 6 < 3 else -10) + k)
                pg.mouse.up()
                pg.set_input_files("#pct-gh-anh", files=[{"name": "bien-ban.png", "mimeType": "image/png",
                                                          "buffer": bytes.fromhex("89504e470d0a1a0a0000000d49484452000000020000000208060000007"
                                                                                  "2b60d240000001649444154789c63f8ffffff7f0606060606000011fe04fd8d8b3f370000000049454e44ae426082")}])
                pg.wait_for_timeout(600)
                pg.screenshot(path=os.path.join(RA, "hop_ky_%s.png" % ten.replace(" ", "_")), full_page=False)
                pg.click("#pct-gh-gui"); pg.wait_for_timeout(1800)

            # 1. còn mạng
            ky(ids[0]["id"], "ນາງ ຮັບສິນຄ້າ")
            p1 = goi("/api/trips/%s" % ids[0]["id"], vai="admin")
            assert p1["pod_signed"] and p1["pod_files"] == 1 and p1["pod_lat"], (p1["pod_signed"], p1["pod_files"], p1["pod_lat"])
            print("✓ còn mạng: ký bằng tay + 1 ảnh + GPS → máy chủ có chữ ký · %s · %s" % (p1["pod_no"], p1["pod_at"]))
            # chờ thẻ vẽ lại sau khi gửi (máy chủ bận thì lâu hơn 1,8 giây chờ cứng ở trên) — tối đa 10 giây
            pg.wait_for_selector('[data-bb="%s"]' % ids[0]["id"], state="visible", timeout=10000)
            assert pg.is_visible('[data-bb="%s"]' % ids[0]["id"]), "thẻ phải có nút Xem biên bản"
            # 2. mất mạng
            ctx.set_offline(True)
            ky(ids[1]["id"], "ທ້າວ ອອບລາຍ")
            hd = pg.evaluate("() => JSON.parse(localStorage.getItem('epl_lao_giao_nhan_' + EPL.AUTH.user.id) || '[]').length")
            assert hd == 1, "mất mạng phải vào hàng đợi, có %s" % hd
            assert "Chờ gửi" in pg.inner_text("#pct-ds"), "thẻ phải hiện chờ gửi"
            p2 = goi("/api/trips/%s" % ids[1]["id"], vai="admin"); assert not p2["pod_signed"]
            print("✓ mất mạng: ký xong vào hàng đợi (1), thẻ hiện 'Chờ gửi', máy chủ chưa có gì")
            # 3. có mạng lại
            ctx.set_offline(False); pg.evaluate("() => window.dispatchEvent(new Event('online'))"); pg.wait_for_timeout(3500)
            hd = pg.evaluate("() => JSON.parse(localStorage.getItem('epl_lao_giao_nhan_' + EPL.AUTH.user.id) || '[]').length")
            p2 = goi("/api/trips/%s" % ids[1]["id"], vai="admin")
            assert hd == 0 and p2["pod_signed"] and p2["pod_receiver"] == "ທ້າວ ອອບລາຍ", (hd, p2["pod_signed"], p2["pod_receiver"])
            print("✓ có mạng lại: hàng đợi tự gửi, máy chủ có chữ ký phiếu thứ hai (%s)" % p2["pod_receiver"])
            # 4. biên bản in
            with ctx.expect_page() as moi:
                pg.click('[data-bb="%s"]' % ids[0]["id"])
            bb = moi.value; bb.wait_for_load_state("networkidle"); bb.wait_for_timeout(600)
            co_ky = bb.evaluate("() => [...document.images].some(i => i.src.includes('/api/tep/') && i.naturalWidth > 0)")
            bb.screenshot(path=os.path.join(RA, "bien_ban.png"), full_page=True)
            txt = bb.inner_text("body")
            assert co_ky and "ນາງ ຮັບສິນຄ້າ" in txt and p1["pod_no"] in txt, (co_ky, txt[:200])
            print("✓ biên bản in: có chữ ký, tên người nhận, số POD")
            b.close()
    finally:
        for p in ids:
            goi("/api/trips/%s" % p["id"], vai="admin", method="DELETE")
        print("  dọn 2 phiếu thử · ảnh chụp ở", RA)
    if loi:
        print("HỎNG — lỗi JS:", loi); sys.exit(1)
    print("\n✅ KÝ NHẬN TRÊN ĐIỆN THOẠI: vẽ chữ ký · ảnh · GPS · mất mạng vào hàng đợi · có mạng tự gửi · in biên bản")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Thử KÝ NHẬN GIAO HÀNG trên màn ĐIỆN THOẠI tài xế — Chromium thật (Playwright), cỡ 390×844, cảm ứng.

    <python có playwright> kiem/thu_ky_nhan_dien_thoai.py [http://127.0.0.1:8011]

1. Còn mạng: mở "Giao hàng hoàn tất", người nhận VẼ chữ ký bằng tay, thêm ảnh, gửi → phiếu có chữ ký, khối POD đầy.
2. MẤT MẠNG: ký phiếu thứ hai → vào hàng đợi, thẻ hiện "chờ gửi".
3. CÓ MẠNG LẠI: hàng đợi tự gửi, máy chủ có chữ ký của phiếu thứ hai.
4. "Xem biên bản" mở tờ in có chữ ký.
Bài tự lập hai phiếu thử (tài xế tx01) và tự xoá.

Màn Phiếu của tôi làm lại theo bản mẫu (30/09): mỗi lần một thẻ chuyến (#tx-p-trip, số phiếu ở .trip-id .code), chuyển
phiếu bằng nút [data-chon] (quá 5 phiếu mở thì ô chọn #tx-chon). "Giao hàng hoàn tất" là NÚT LỚN Bước tiếp theo
(.btn-go[data-act="gh"]) — không còn ô bấm lặp lại bên dưới (rà 01/10); hộp ký #tx-d-gh; ký xong có ô [data-act="bb"] Xem
biên bản. Máy chủ lưu chữ ký là tệp pod_sign, ảnh là pod.
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
                               "doc_date": time.strftime("%Y-%m-%d"), "weight_origin": 40, "note": "thử ký điện thoại", "kind": "giao"}, "thabok")
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
            pg.wait_for_selector("#tx-p-trip .trip-id .code", timeout=15000)

            def dang_xem():
                return (pg.text_content("#tx-p-trip .trip-id .code") or "").strip()

            def chon(p):
                """Đưa thẻ chuyến về đúng phiếu p (nút [data-chon] hoặc ô chọn #tx-chon khi quá 5 phiếu mở)."""
                if dang_xem() != p["doc_no"]:
                    if pg.query_selector('#tx-p-trip [data-chon="%s"]' % p["id"]):
                        pg.click('#tx-p-trip [data-chon="%s"]' % p["id"])
                    else:
                        pg.select_option("#tx-chon", p["id"])
                pg.wait_for_function("so => ((document.querySelector('#tx-p-trip .trip-id .code') || {}).textContent || '').trim() === so",
                                     arg=p["doc_no"], timeout=10000)
                pg.wait_for_timeout(300)

            def ky(p, ten):
                chon(p)
                nut = '#tx-p-trip .btn-go[data-act="gh"]'
                assert pg.is_visible(nut), "phiếu giao đang chạy: nút lớn Bước tiếp theo phải là Giao hàng hoàn tất"
                n_gh = len(pg.query_selector_all('#tx-p-trip [data-act="gh"]:not(.link-btn)'))
                assert n_gh == 1, "chỉ MỘT nút Giao hàng hoàn tất (ô bấm lặp dưới nút lớn đã bỏ 01/10), có %d" % n_gh
                pg.click(nut); pg.wait_for_selector("#tx-d-gh[open]"); pg.wait_for_timeout(700)
                pg.fill("#tx-gh-ten", ten); pg.fill("#tx-gh-sdt", "020 5555 1234")
                hop = pg.query_selector("#tx-gh-canvas").bounding_box()
                pg.mouse.move(hop["x"] + 30, hop["y"] + hop["height"] / 2); pg.mouse.down()
                for k in range(1, 30):
                    pg.mouse.move(hop["x"] + 30 + k * 9, hop["y"] + hop["height"] / 2 - (25 if k % 6 < 3 else -10) + k / 2)
                pg.mouse.up()
                pg.set_input_files("#tx-gh-anh", files=[{"name": "bien-ban.png", "mimeType": "image/png",
                                                         "buffer": bytes.fromhex("89504e470d0a1a0a0000000d49484452000000020000000208060000007"
                                                                                 "2b60d240000001649444154789c63f8ffffff7f0606060606000011fe04fd8d8b3f370000000049454e44ae426082")}])
                pg.wait_for_timeout(800)
                pg.screenshot(path=os.path.join(RA, "hop_ky_%s.png" % ten.replace(" ", "_")), full_page=False)
                pg.click('#tx-d-gh [type="submit"]')
                pg.wait_for_selector("#tx-d-gh:not([open])", state="attached", timeout=15000); pg.wait_for_timeout(1500)

            # 1. còn mạng
            ky(ids[0], "ນາງ ຮັບສິນຄ້າ")
            p1 = goi("/api/trips/%s" % ids[0]["id"], vai="admin")
            assert p1["pod_signed"] and p1["pod_files"] == 1 and p1["pod_lat"], (p1["pod_signed"], p1["pod_files"], p1["pod_lat"])
            tep = goi("/api/trips/%s/tep" % ids[0]["id"], vai="admin")
            loai = sorted(x.get("kind") for x in tep)
            assert loai.count("pod_sign") == 1 and loai.count("pod") == 1, "máy chủ phải có 1 chữ ký pod_sign + 1 ảnh pod: %s" % loai
            print("✓ còn mạng: nút lớn Giao hàng hoàn tất → ký bằng tay + 1 ảnh + GPS → máy chủ có pod_sign + ảnh pod · %s · %s"
                  % (p1["pod_no"], p1["pod_at"]))
            # thẻ vẽ lại sau khi gửi: nút lớn sang việc kế tiếp, có ô Xem biên bản — tối đa 10 giây
            chon(ids[0])
            pg.wait_for_selector('#tx-p-trip [data-act="bb"]', state="visible", timeout=10000)
            assert not pg.query_selector('#tx-p-trip .btn-go[data-act="gh"]'), "đã ký thì nút lớn không còn là Giao hàng hoàn tất"
            print("✓ thẻ đã ký: có ô Xem biên bản, nút lớn chuyển sang việc kế tiếp")
            # 2. mất mạng
            ctx.set_offline(True)
            ky(ids[1], "ທ້າວ ອອບລາຍ")
            hd = pg.evaluate("() => JSON.parse(localStorage.getItem('epl_lao_giao_nhan_' + EPL.AUTH.user.id) || '[]').length")
            assert hd == 1, "mất mạng phải vào hàng đợi, có %s" % hd
            assert "Chờ gửi" in pg.inner_text("#tx-p-trip"), "thẻ phải hiện chờ gửi"
            p2 = goi("/api/trips/%s" % ids[1]["id"], vai="admin"); assert not p2["pod_signed"]
            print("✓ mất mạng: ký xong vào hàng đợi (1), thẻ hiện 'Chờ gửi', máy chủ chưa có gì")
            # 3. có mạng lại
            ctx.set_offline(False); pg.evaluate("() => window.dispatchEvent(new Event('online'))"); pg.wait_for_timeout(3500)
            hd = pg.evaluate("() => JSON.parse(localStorage.getItem('epl_lao_giao_nhan_' + EPL.AUTH.user.id) || '[]').length")
            p2 = goi("/api/trips/%s" % ids[1]["id"], vai="admin")
            assert hd == 0 and p2["pod_signed"] and p2["pod_receiver"] == "ທ້າວ ອອບລາຍ", (hd, p2["pod_signed"], p2["pod_receiver"])
            print("✓ có mạng lại: hàng đợi tự gửi, máy chủ có chữ ký phiếu thứ hai (%s)" % p2["pod_receiver"])
            # 4. biên bản in
            chon(ids[0])
            with ctx.expect_page() as moi:
                pg.click('#tx-p-trip [data-act="bb"]')
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

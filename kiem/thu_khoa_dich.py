# -*- coding: utf-8 -*-
"""Mọi khoá dịch giao diện đang dùng phải có trong từ điển (frontend/js/ngon_ngu.js).

    python kiem/thu_khoa_dich.py

Rà giao diện 23/09 thấy nút "view" (HĐ gộp) và "refresh" (Xe, Tài xế) hiện nguyên chữ tiếng Anh: khoá thiếu trong
từ điển, và bộ kiểm "lộ khoá" trên jsdom không bắt được vì tên khoá trông như chữ thường. Bài này đọc thẳng mã nguồn.
Khoá ghép động ('r_' + vai, 'sec' + số…) được bỏ qua — chúng kết thúc bằng '_' hoặc là tiền tố đã biết.
"""
import glob
import io
import json
import os
import re
import sys

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIEN_TO = {"sec"}          # NN.t('sec' + n)


def main():
    s = io.open(os.path.join(GOC, "frontend", "js", "ngon_ngu.js"), encoding="utf-8").read()
    tu = json.loads(s[s.index("{"):s.rindex("}") + 1])
    dung = {}
    for f in glob.glob(os.path.join(GOC, "frontend", "**", "*.js"), recursive=True) + glob.glob(os.path.join(GOC, "frontend", "**", "*.html"), recursive=True):
        if "ngon_ngu" in f or "node_modules" in f or "Index (2)" in f:
            continue
        t = io.open(f, encoding="utf-8", errors="ignore").read()
        for k in (re.findall(r'data-i18n="([a-zA-Z0-9_]+)"', t) + re.findall(r"NN\.[th]\('([a-zA-Z0-9_]+)'", t)
                  + re.findall(r"label: '([a-z0-9_]+)'", t) + re.findall(r"nav(?:_s)?: '([a-z0-9_]+)'", t)):
            if k.endswith("_") or k in TIEN_TO:
                continue
            dung.setdefault(k, set()).add(os.path.relpath(f, GOC))
    thieu = {k: v for k, v in dung.items() if k not in tu}
    for k, v in sorted(thieu.items()):
        print("  THIẾU %-24s ← %s" % (k, ", ".join(sorted(v))))
    if thieu:
        print("\nHỎNG — %d khoá dùng mà từ điển chưa có (thêm vào tools/sinh_ngon_ngu.py rồi chạy lại)." % len(thieu)); sys.exit(1)
    print("✅ KHOÁ DỊCH: %d khoá đang dùng, đều có đủ trong từ điển (%d khoá)." % (len(dung), len(tu)))


if __name__ == "__main__":
    main()

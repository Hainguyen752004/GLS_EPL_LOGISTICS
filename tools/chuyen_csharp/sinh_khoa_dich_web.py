# -*- coding: utf-8 -*-
"""Việc 8 (chuyển trang điều xe sang module Vận tải C#, 08/10): sinh từ điển riêng của module Vận tải cho Web GLS —
GLS-QLSX-Web/Backend/Base/Localization/logistics.{vi,lo,en}.json — từ frontend/js/ngon_ngu.js của trang điều xe.

    python -X utf8 tools/chuyen_csharp/sinh_khoa_dich_web.py

Quy ước (anh Hải chốt 08/10 — tệp riêng, không gộp vào vi/lo/en.json chung):
  * khoá Web = "LOG_" + khoá trang điều xe viết HOA (ký tự khác chữ / số → "_"): nav_dash → LOG_NAV_DASH, tk_gls → LOG_TK_GLS.
  * thiếu bản lo / en thì lấy bản vi (giống AppLocalizer.Translate).
  * chỗ thay số giữ nguyên dạng {tên} — Web dùng cùng dạng (AppI18n.format, Helper.Trans).
  * AppLocalizer đọc thêm tệp này (khoá phải bắt đầu LOG_, không đè khoá chung); _Layout chỉ đẩy khoá LOG_ xuống trình duyệt ở
    trang /Logistics — các trang Web khác không nặng thêm. Razor dịch bằng Helper.Trans("LOG_…") như mọi khoá.
  * chế độ song ngữ «VI + ລາວ» của trang điều xe KHÔNG mang sang (Web chỉ có vi / lo / en).
Chạy lại khi từ điển trang điều xe đổi — tệp ghi đè toàn bộ, xếp theo khoá.

Việc 9 (08/10): câu CHỈ màn Web có (nút gắn Đối tượng GLS…) viết ở tools/chuyen_csharp/khoa_dich_web_rieng.json — khoá đã có
tiền tố LOG_W_, mỗi khoá {vi, lo, en}; bộ sinh gộp vào cùng tệp, trùng khoá với từ điển trang điều xe thì dừng.
"""
import json, os, re, sys
from collections import Counter

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RA = r"D:\Demo_Lao\GLS-QLSX-Web\Backend\Base\Localization"

t = open(os.path.join(GOC, "frontend", "js", "ngon_ngu.js"), encoding="utf-8").read()
tu = json.loads(t[t.index("{"):t.rstrip().rindex("}") + 1])
khoa_web = lambda k: "LOG_" + re.sub(r"[^A-Za-z0-9]", "_", k).upper()

trung = [k for k, n in Counter(khoa_web(k) for k in tu).items() if n > 1]
if trung:
    sys.exit("TRÙNG khoá sau khi đổi tên: %s" % trung[:10])
rieng = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "khoa_dich_web_rieng.json"), encoding="utf-8"))
sai = [k for k in rieng if not k.startswith("LOG_W_") or k in {khoa_web(x) for x in tu}]
if sai:
    sys.exit("Khoá riêng của Web phải bắt đầu LOG_W_ và không trùng từ điển trang điều xe: %s" % sai[:10])

for ng in ("vi", "lo", "en"):
    d = {khoa_web(k): (v.get(ng) or v.get("vi") or "") for k, v in tu.items()}
    d.update({k: (v.get(ng) or v.get("vi") or "") for k, v in rieng.items()})
    p = os.path.join(RA, "logistics.%s.json" % ng)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(dict(sorted(d.items())), f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("%s: %d khoá → %s" % (ng, len(d), p))

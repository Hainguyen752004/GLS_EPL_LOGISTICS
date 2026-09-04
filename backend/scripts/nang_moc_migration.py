"""Nâng mốc migration head trong bộ test, phân biệt đúng các loại chỗ xuất hiện.

Việc này đã làm sai ba lần với đúng hai cái bẫy, vì một lệnh tìm/thay hàng loạt
không phân biệt được bốn loại chỗ mà tên phiên bản xuất hiện:

  1. MỐC HEAD      `required_migration_head() == "025_..."`   -> ĐỔI sang bản mới
  2. DANH SÁCH     `"024_...", "025_..."` hoặc `..., "025_..."]` -> NỐI THÊM
  3. TUPLE MỘT PHẦN TỬ  `.fetchone() == ("025_...",)`         -> ĐỔI, không nối
                   (nối vào đây biến nó thành tuple hai phần tử và test sai)
  4. TÊN MODULE    `from migrations import v025_... as v025`   -> GIỮ NGUYÊN
                   (đổi ở đây làm hỏng import)

Cách dùng:
    python scripts/nang_moc_migration.py 025_vehicle_depot 026_sales_order_lines
"""
import io
import os
import re
import sys


def bump(old, new, root="tests"):
    append_rules = [
        ('"%s",' % old, '"%s", "%s",' % (old, new)),
        ('"%s"]' % old, '"%s", "%s"]' % (old, new)),
    ]
    # Tuple mot phan tu: dau hieu la dau phay ngay truoc dau dong ngoac.
    single_tuple = re.compile(r'\("%s",\s*\)' % re.escape(old))
    changed = []

    for folder, _dirs, files in os.walk(root):
        if "__pycache__" in folder:
            continue
        for name in sorted(files):
            if not name.endswith(".py"):
                continue
            path = os.path.join(folder, name)
            text = io.open(path, encoding="utf-8").read()
            if old not in text:
                continue

            out, touched = [], 0
            for line in text.split(chr(10)):
                if old not in line:
                    out.append(line)
                    continue
                # (4) Ten module — giu nguyen.
                if "import" in line:
                    out.append(line)
                    continue
                before = line
                # (3) Tuple mot phan tu — doi thang, KHONG noi them.
                if single_tuple.search(line):
                    line = single_tuple.sub('("%s",)' % new, line)
                else:
                    # (2) Danh sach — noi them.
                    for needle, repl in append_rules:
                        if needle in line:
                            line = line.replace(needle, repl)
                    # (1) Moc head — doi thang.
                    if line == before:
                        line = line.replace(old, new)
                if line != before:
                    touched += 1
                out.append(line)

            if touched:
                io.open(path, "w", encoding="utf-8").write(chr(10).join(out))
                changed.append((path, touched))
    return changed


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    old, new = sys.argv[1], sys.argv[2]
    changed = bump(old, new)
    for path, count in changed:
        print("%3d dòng  %s" % (count, path))
    print("tổng: %d dòng trong %d tệp" % (sum(c for _p, c in changed), len(changed)))
    print()
    print("Nhớ chạy lại bộ test migration ngay sau đó — vẫn còn hai chỗ script")
    print("không đoán được: danh sách kết thúc bằng biến HEAD_VERSION, và test")
    print("`test_vNNN_is_the_registered_head` của chính bản vừa bị thay thế.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

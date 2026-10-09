# -*- coding: utf-8 -*-
"""Danh mục câu lỗi / cảnh báo của API để dịch sang tiếng Lào, tiếng Anh (09/10/2026).

Vì sao: API báo lỗi bằng {"ma": …, "loi": "<câu tiếng Việt>"}; màn cũ (chung.js chuLoi) và Web (LogisticsApiClient) đã chọn
`loi_lo` / `loi_en` khi có, nhưng chỉ ~26 / ~460 câu có bản dịch → người dùng tiếng Lào vẫn đọc tiếng Việt. Thay vì sửa tay từng chỗ
raise, bộ này đọc mã nguồn (ast), lấy mọi dict có khoá "ma" + "loi" (lỗi HTTPException, cảnh báo khoá phiếu, hằng lỗi dùng chung) và
viết mẫu câu vào backend/app/services/loi_dich.json. services/loi_dich.py lúc chạy so câu tiếng Việt với mẫu, lấy các giá trị chèn
(số phiếu, số tấn…) và ghép vào mẫu Lào / Anh.

Mẫu: phần chèn của câu (%s · %.1f · {bien} trong f-string · biến nối bằng +) ghi là {1}, {2}… theo thứ tự trong câu tiếng Việt; bản
dịch dùng cùng các {n} (đổi chỗ được). Dấu % trong câu là chữ thường.

Chạy:  python tools/sinh_loi_dich.py          → cập nhật loi_dich.json (giữ bản dịch đã có, thêm câu mới với lo / en trống, đánh dấu
                                                câu không còn trong mã), in thống kê + câu chưa dịch
       python tools/sinh_loi_dich.py --kiem   → chỉ kiểm, không ghi; mã thoát 1 nếu có câu chưa dịch hoặc mẫu dịch sai {n}
"""
import ast
import json
import os
import re
import sys

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(GOC, "backend", "app")
TEP = os.path.join(APP, "services", "loi_dich.json")
PRINTF = re.compile(r"%(?:\([^)]*\))?[-+ #0]*(?:\d+|\*)?(?:\.(?:\d+|\*))?[sdifrxXeEgGc%]")


def _chu(text):
    return [("chu", text)] if text else []


def _printf(text):
    """'Xe %s chở %.1f t (100%%)' → [chu 'Xe ', cho, chu ' chở ', cho, chu ' t (100%)']."""
    ra, i = [], 0
    for m in PRINTF.finditer(text):
        ra += _chu(text[i:m.start()])
        ra += [("chu", "%")] if m.group() == "%%" else [("cho",)]
        i = m.end()
    return ra + _chu(text[i:])


def _gop(tok):
    """Gộp các mảnh chữ liền nhau ("%" + "s" sau lớp % thứ nhất thành "%s") để đọc lớp % thứ hai."""
    ra = []
    for t in tok:
        if t[0] == "chu" and ra and ra[-1][0] == "chu":
            ra[-1] = ("chu", ra[-1][1] + t[1])
        else:
            ra.append(t)
    return ra


def _mau(node):
    """Các dạng câu của một biểu thức "loi" → list các chuỗi token; None nếu cả câu chỉ là biến (không dịch được)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [_chu(node.value)]
    if isinstance(node, ast.JoinedStr):
        tok = []
        for v in node.values:
            tok += _chu(v.value) if isinstance(v, ast.Constant) else [("cho",)]
        return [tok]
    if isinstance(node, ast.IfExp):
        a, b = _mau(node.body), _mau(node.orelse)
        return (a or []) + (b or []) or None
    if isinstance(node, ast.BoolOp):                    # loi_co_tep(...) or "Ảnh quá lớn." — nhánh nào là câu thì lấy
        return [c for v in node.values for c in (_mau(v) or [])] or None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
        trai = _mau(node.left)
        if not trai:
            return None
        # "Hệ kế toán trả HTTP %s: %%s" % ma rồi % cau: chỗ chèn của lớp trong giữ nguyên, chữ còn lại đọc tiếp như printf
        return [[x for t in _gop(c) for x in (_printf(t[1]) if t[0] == "chu" else [t])] for c in trai]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        a, b = _mau(node.left) or [[("cho",)]], _mau(node.right) or [[("cho",)]]
        return [x + y for x in a for y in b]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format" \
            and isinstance(node.func.value, ast.Constant) and isinstance(node.func.value.value, str):
        tok, i, s = [], 0, node.func.value.value
        for m in re.finditer(r"\{[^{}]*\}", s):
            tok += _chu(s[i:m.start()]) + [("cho",)]
            i = m.end()
        return [tok + _chu(s[i:])]
    return None


CUM_CHEN = {}            # chữ cố định máy điền vào chỗ chèn ("xe" · "tài xế" · "xuất kho"…) → chỗ — dịch như một cụm


def _chu_chen(node):
    """Chuỗi cố định có thể thành giá trị chèn: hằng chuỗi, hai nhánh `a if … else b`, `x or "mặc định"`, phần tử tuple đối số."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.IfExp):
        return _chu_chen(node.body) + _chu_chen(node.orelse)
    if isinstance(node, ast.BoolOp):
        return [x for v in node.values for x in _chu_chen(v)]
    if isinstance(node, ast.Tuple):
        return [x for v in node.elts for x in _chu_chen(v)]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get"             and isinstance(node.func.value, ast.Dict):             # {"huy": "huỷ đề nghị …", …}.get(viec, …)
        return [x for v in node.func.value.values for x in _chu_chen(v)]
    return []


def _gom_chu_chen(node, cho):
    """Trong biểu thức "loi": đối số của `"…" % (…)` và giá trị trong f-string — giữ chuỗi có chữ thường, không có "_" (bỏ mã)."""
    for n in ast.walk(node):
        nguon = []
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mod):
            nguon = _chu_chen(n.right)
        elif isinstance(n, ast.FormattedValue):
            nguon = _chu_chen(n.value)
        for s in nguon:
            s = s.strip()
            if len(s) >= 2 and "_" not in s and re.search(r"[a-zà-ỹ]", s) and not PRINTF.search(s):
                CUM_CHEN.setdefault(s, cho)


def _hien(tok):
    """token → câu hiển thị với {1}, {2}…; gộp chữ liền nhau."""
    ra, n = [], 0
    for t in tok:
        if t[0] == "cho":
            n += 1
            ra.append("{%d}" % n)
        else:
            ra.append(t[1])
    return "".join(ra), n


def _ham_phu(cac_cay):
    """Hàm dựng lỗi nhận câu qua tham số: dict {"ma": …, "loi": <tham số>} trong thân hàm → {tên: (vị trí loi, tên loi, vị trí ma)}."""
    ra = {}
    for _, cay in cac_cay:
        for f in ast.walk(cay):
            if not isinstance(f, ast.FunctionDef):
                continue
            ts = [a.arg for a in f.args.args]
            for d in ast.walk(f):
                if not isinstance(d, ast.Dict):
                    continue
                khoa = {k.value: v for k, v in zip(d.keys, d.values) if isinstance(k, ast.Constant)}
                v = khoa.get("loi")
                if isinstance(v, ast.Name) and v.id in ts and "loi_lo" not in khoa:
                    m = khoa.get("ma")
                    ra[f.name] = (ts.index(v.id), v.id, ts.index(m.id) if isinstance(m, ast.Name) and m.id in ts else None)
    return ra


def _tham_so_chen(cac_cay):
    """Hàm chèn tham số của nó vào câu lỗi ("Vai %s không được %s." % (vai, viec) · _ket(…, viec) → "Bên kế toán từ chối %s: …")
    → {tên hàm: {vị trí tham số}} — chữ cố định truyền vào đó ở nơi gọi ("xem công nợ nhà cung cấp", "đọc tồn") là cụm cần dịch."""
    ra = {}
    for _, cay in cac_cay:
        for f in ast.walk(cay):
            if not isinstance(f, ast.FunctionDef):
                continue
            ts = [a.arg for a in f.args.args]
            for n in ast.walk(f):
                dung = []
                if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mod) and isinstance(n.left, ast.Constant)                         and isinstance(n.left.value, str) and VIET_CHU.search(n.left.value):
                    dung = [x for x in ast.walk(n.right) if isinstance(x, ast.Name)]
                elif isinstance(n, ast.JoinedStr) and any(isinstance(v, ast.Constant) and VIET_CHU.search(v.value) for v in n.values):
                    dung = [x for v in n.values if isinstance(v, ast.FormattedValue) for x in ast.walk(v.value) if isinstance(x, ast.Name)]
                for x in dung:
                    if x.id in ts:
                        ra.setdefault(f.name, set()).add(ts.index(x.id))
    return ra


VIET_CHU = re.compile(r"[ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵĂÂĐÊÔƠƯ]")


def quet():
    """→ ({mẫu vi: {"ma": set, "o": set(chỗ)}}, [chỗ không dịch được])."""
    mau, bo = {}, []
    cac_cay = []
    for goc, _, tep in os.walk(APP):
        if "__pycache__" in goc:
            continue
        for t in tep:
            if t.endswith(".py"):
                duong = os.path.join(goc, t)
                cac_cay.append((os.path.relpath(duong, GOC).replace("\\", "/"), ast.parse(open(duong, encoding="utf-8").read(), duong)))
    phu = _ham_phu(cac_cay)
    chen = _tham_so_chen(cac_cay)

    def ghi_mau(cac, ma, cho, so_chu_toi_thieu=0):
        for tok in cac or []:
            vi, so = _hien(tok)
            if not vi.strip() or vi.strip() == "{1}" or not any(t[0] == "chu" and len(t[1].strip()) > so_chu_toi_thieu for t in tok):
                continue
            e = mau.setdefault(vi, {"ma": set(), "o": set(), "so_cho": so})
            e["ma"].add(ma)
            e["o"].add(cho)

    for tuong_doi, cay in cac_cay:
        if True:
            for node in ast.walk(cay):
                # chữ cố định truyền vào tham số được chèn vào câu lỗi: chan_vai(user, …, "xem công nợ nhà cung cấp")
                if isinstance(node, ast.Call):
                    ten = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
                    for i in chen.get(ten, ()):
                        a = node.args[i] if len(node.args) > i else None
                        for chu_ in (_chu_chen(a) if a is not None else []):
                            chu_ = chu_.strip()
                            if VIET_CHU.search(chu_) and "_" not in chu_:
                                CUM_CHEN.setdefault(chu_, "%s:%d" % (tuong_doi, node.lineno))
                        if a is not None and isinstance(a, ast.BinOp):          # "%s đề nghị trả nhà cung cấp" % viec
                            ghi_mau(_mau(a), "*chen", "%s:%d" % (tuong_doi, node.lineno), 3)
                # nơi gọi hàm phụ: _loi("MA", "câu …" % x) · _chan(p, "MA", "câu …")
                if isinstance(node, ast.Call):
                    ten = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
                    if ten in phu:
                        i_loi, ten_loi, i_ma = phu[ten]
                        v = node.args[i_loi] if len(node.args) > i_loi else next((k.value for k in node.keywords if k.arg == ten_loi), None)
                        a_ma = node.args[i_ma] if i_ma is not None and len(node.args) > i_ma else None
                        ma = a_ma.value if isinstance(a_ma, ast.Constant) else "*"
                        if v is not None:
                            _gom_chu_chen(v, "%s:%d" % (tuong_doi, node.lineno))
                            cac = _mau(v)
                            if cac:
                                ghi_mau(cac, ma, "%s:%d" % (tuong_doi, node.lineno))
                            else:
                                bo.append("%s:%d (%s)" % (tuong_doi, node.lineno, ma))
                # d["loi"] = "SO cước %s. Chưa tạo SO nhiên liệu: %s" % (…) — sửa câu của một lỗi đã bắt rồi ném lại
                if isinstance(node, ast.Assign) and any(isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant)
                                                        and t.slice.value == "loi" for t in node.targets):
                    ghi_mau(_mau(node.value), "*gan", "%s:%d" % (tuong_doi, node.lineno), 3)
                # ValueError("câu …") — câu đi thẳng vào "loi" qua str(e) (routes/de_nghi LOC_SAI…)
                if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "ValueError" and node.args:
                    ghi_mau(_mau(node.args[0]), "*ValueError", "%s:%d" % (tuong_doi, node.lineno), 3)
                # return (None, "MA_LOI", "câu …") — hàm đọc kết quả bên kế toán trả (mã, câu) cho nơi gọi _loi(ma, cau)
                # · hằng (MÃ, câu) dùng làm {"ma": X[0], "loi": X[1]}
                bo_doi = node.value if isinstance(node, (ast.Return, ast.Assign)) and isinstance(node.value, ast.Tuple) else None
                if bo_doi is not None and any(isinstance(x, ast.Constant) and isinstance(x.value, str)
                                              and re.fullmatch(r"[A-Z][A-Z0-9_]{3,}", x.value) for x in bo_doi.elts):
                    for x in bo_doi.elts:
                        if not (isinstance(x, ast.Constant) and isinstance(x.value, str) and re.fullmatch(r"[A-Z0-9_]+", x.value)):
                            ghi_mau(_mau(x), "*bo", "%s:%d" % (tuong_doi, node.lineno), 3)
                # câu nối thêm: cau += " — phiếu dùng tài khoản %s; …" % tk  → mẫu "{1} — phiếu dùng tài khoản {2}; …"
                if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add) and isinstance(node.target, ast.Name)                         and node.target.id in ("cau", "loi", "chu", "ly_do"):
                    ghi_mau([[("cho",)] + c for c in (_mau(node.value) or [])], "*noi", "%s:%d" % (tuong_doi, node.lineno), 3)
                # câu lỗi dựng trong hàm riêng rồi đưa vào "loi" (CHI.cau_chan_chi, _cau_chua_tam_ung, loi_co_tep, loi_ma_khach…)
                if isinstance(node, ast.FunctionDef) and re.match(r"_?(cau|loi)_", node.name):
                    for r in ast.walk(node):
                        if isinstance(r, ast.Return) and r.value is not None:
                            _gom_chu_chen(r.value, "%s:%d" % (tuong_doi, r.lineno))
                            for tok in _mau(r.value) or []:
                                vi, so = _hien(tok)
                                if vi.strip() and vi.strip() != "{1}" and any(t[0] == "chu" and len(t[1].strip()) > 3 for t in tok):
                                    e = mau.setdefault(vi, {"ma": set(), "o": set(), "so_cho": so})
                                    e["ma"].add("*")
                                    e["o"].add("%s:%d" % (tuong_doi, r.lineno))
                    continue
                # cụm chữ truyền vào hàm dựng câu (_cau_chua_tam_ung(db, p, "chưa xuất phát")) — lúc chạy, giá trị chèn trùng cụm
                # có bản dịch thì dịch luôn, không để câu Lào / Anh chen một cụm tiếng Việt
                if isinstance(node, ast.Call):
                    ten = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
                    if re.match(r"_?cau_", ten or ""):
                        for a in node.args:
                            if isinstance(a, ast.Constant) and isinstance(a.value, str) and " " in a.value.strip():
                                e = mau.setdefault(a.value, {"ma": set(), "o": set(), "so_cho": 0})
                                e["ma"].add("*cum")
                                e["o"].add("%s:%d" % (tuong_doi, node.lineno))
                if not isinstance(node, ast.Dict):
                    continue
                khoa = {k.value: v for k, v in zip(node.keys, node.values) if isinstance(k, ast.Constant)}
                if "loi" not in khoa or "ma" not in khoa or "loi_lo" in khoa:
                    continue
                ma = khoa["ma"].value if isinstance(khoa["ma"], ast.Constant) else "*"
                _gom_chu_chen(khoa["loi"], "%s:%d" % (tuong_doi, node.lineno))
                cac = _mau(khoa["loi"])
                if not cac:
                    if not (isinstance(khoa["loi"], ast.Name) and any(i[1] == khoa["loi"].id for i in phu.values())):
                        bo.append("%s:%d (%s)" % (tuong_doi, node.lineno, ma))
                    continue
                for tok in cac:
                    vi, so = _hien(tok)
                    if not vi.strip() or vi.strip() == "{1}":
                        continue
                    e = mau.setdefault(vi, {"ma": set(), "o": set(), "so_cho": so})
                    e["ma"].add(ma)
                    e["o"].add("%s:%d" % (tuong_doi, node.lineno))
    # tên loại ảnh chèn vào "Không có {1} này." (routes/anh.py: Loai(…, ten_chu="xe" · "tài xế")) — tham số dựng lớp, ngoài câu lỗi
    CUM_CHEN.setdefault("xe", "backend/app/routes/anh.py:44")
    CUM_CHEN.setdefault("tài xế", "backend/app/routes/anh.py:45")
    for s, cho in CUM_CHEN.items():
        if s not in mau:
            mau[s] = {"ma": {"*chen"}, "o": {cho}, "so_cho": 0}
    return mau, bo


def cho_cua(text):
    return sorted(set(re.findall(r"\{(\d+)\}", text or "")), key=int)


def main():
    kiem = "--kiem" in sys.argv
    mau, bo = quet()
    cu = json.load(open(TEP, encoding="utf-8")) if os.path.exists(TEP) else {}
    moi = {}
    for vi in sorted(mau):
        e = mau[vi]
        d = cu.get(vi, {})
        moi[vi] = {"ma": sorted(e["ma"]), "lo": d.get("lo", ""), "en": d.get("en", ""), "o": sorted(e["o"])[:3]}
    thieu = [vi for vi, d in moi.items() if not d["lo"] or not d["en"]]
    sai = [vi for vi, d in moi.items() if d["lo"] and d["en"]
           and not (cho_cua(d["lo"]) == cho_cua(vi) == cho_cua(d["en"]))]
    bo_cu = [vi for vi in cu if vi not in moi]
    print("mẫu câu: %d · chưa dịch: %d · {n} lệch: %d · câu cũ không còn trong mã: %d · chỗ không dịch được (cả câu là biến): %d"
          % (len(moi), len(thieu), len(sai), len(bo_cu), len(bo)))
    for vi in sai[:20]:
        print("  {n} lệch:", vi[:120])
    if kiem:
        for vi in thieu[:20]:
            print("  chưa dịch:", vi[:120])
        sys.exit(1 if thieu or sai else 0)
    with open(TEP, "w", encoding="utf-8") as f:
        json.dump(moi, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    print("đã ghi", os.path.relpath(TEP, GOC))
    if bo:
        print("chỗ không dịch được:", ", ".join(bo[:30]))


if __name__ == "__main__":
    main()

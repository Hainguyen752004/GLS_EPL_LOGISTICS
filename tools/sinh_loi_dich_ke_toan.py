# -*- coding: utf-8 -*-
"""Danh mục câu lỗi của HỆ KẾ TOÁN (GLS-QLSX-APIs) mà EPL chuyển tiếp — để dịch sang tiếng Lào, tiếng Anh (09/10/2026).

Vì sao: khi bên kế toán từ chối (lập phiếu chi, SO, xuất kho, đối tượng…), API trả "Message" tiếng Việt cứng (bên đó chưa có đa ngôn
ngữ); EPL bọc vào câu của mình ("Hệ kế toán từ chối: {1}") → người dùng tiếng Lào vẫn đọc tiếng Việt. Bộ này đọc mã nguồn bên đó
CHỈ trên đường EPL gọi (controller → service → repository → thủ tục SQL) và ghi mẫu câu vào
backend/app/services/loi_dich_ke_toan.json; services/loi_dich.py nạp cùng danh mục chính, giá trị chèn trùng câu bên kế toán thì
dịch luôn. Tệp riêng (không gộp loi_dich.json) vì mã nguồn bên kế toán chỉ có ở máy dev — tools/sinh_loi_dich.py chạy ở máy khác không
làm mất các câu này.

Chạy (máy có D:\\Demo_Lao\\GLS-QLSX-APIs, hoặc đặt GLS_API_DIR):
    python tools/sinh_loi_dich_ke_toan.py          → cập nhật loi_dich_ke_toan.json (giữ bản dịch đã có), in câu chưa dịch
    python tools/sinh_loi_dich_ke_toan.py --kiem   → chỉ kiểm tệp (không cần mã nguồn bên kế toán): mã thoát 1 nếu còn câu chưa dịch
"""
import json
import os
import re
import sys

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEP = os.path.join(GOC, "backend", "app", "services", "loi_dich_ke_toan.json")
API = os.getenv("GLS_API_DIR", os.path.join(os.path.dirname(GOC), "GLS-QLSX-APIs", "Backend.API"))
# controller EPL gọi (services/chi_tune · gui_tune · kho_qlsx · gui_but_toan_tune · doi_tuong_gls · khach_gls · dang_nhap_gls …)
CTRL = ["Finance/Accounting/Api/V1/CMPaymentReceiptController.cs", "Finance/Accounting/Api/V1/LaoAccountsController.cs",
        "Finance/Accounting/Api/V1/LogisticsJournalEntryController.cs", "Finance/Accounting/Api/V1/LogisticsLineVoucherController.cs",
        "Sales/Sales/Api/V1/DebtCollectionController.cs", "Sales/Sales/Api/V1/DebtCollectionOffsetController.cs",
        "Sales/Sales/Api/V1/LogisticsFuelSalesOrderController.cs", "Sales/Sales/Api/V1/LogisticsPushController.cs",
        "SupplyChain/Warehouse/Api/V1/LogisticsFuelVoucherController.cs", "SupplyChain/Warehouse/Api/V1/LogisticsStockController.cs",
        "SupplyChain/Warehouse/Api/V1/LogisticsStockDocumentController.cs", "SupplyChain/Warehouse/Api/V1/WarehouseController.cs",
        "Shared/MasterData/Api/V1/CommonController.cs", "Shared/ObjectManagement/Api/V1/CustomerController.cs",
        "Shared/ObjectManagement/Api/V1/SupplierController.cs", "Shared/ObjectManagement/Api/V1/StaffController.cs",
        "Shared/ObjectManagement/Api/V1/ObjectManagementController.cs", "Security/Auth/Api/V1/AuthController.cs"]
# lớp dùng chung mà đường EPL không chạm (danh mục hàng, công thức, vé) — bỏ
BO_MODULE = re.compile(r"\\Modules\\(Catalog|Formula|Sales\\Resticket)\\")
VIET = re.compile(r"[ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵĂÂĐÊÔƠƯ]")
CS_STR = re.compile(r'(\$?)@?"((?:[^"\\]|\\.)*)"')
BO_DONG = re.compile(r"_logger|Log(Information|Warning|Error|Debug|Critical)\(|Summary\s*=|Description\s*=|///|^\s*//|\[Display|\[Swagger")
SQL_STR = re.compile(r"N'((?:[^']|'')*)'")
PRINTF = re.compile(r"%(?:\d+\$)?[-+ #0]*\d*(?:\.\d+)?[sdiuxX]")


def _cs(noi_suy, s):
    """Chuỗi C# → mẫu {1}, {2}…: $"…{x}…" (nội suy) hoặc "…{0}…" (string.Format); bỏ thoát \\" \\n."""
    s = s.replace('\\"', '"').replace("\\n", " ").replace("\\t", " ").replace("\\\\", "\\")
    if noi_suy:
        s = s.replace("{{", "\x01").replace("}}", "\x02")
        n = iter(range(1, 100))
        s = re.sub(r"\{[^{}]*\}", lambda m: "{%d}" % next(n), s)
        return s.replace("\x01", "{").replace("\x02", "}")
    return re.sub(r"\{(\d+)(?:[,:][^}]*)?\}", lambda m: "{%d}" % (int(m.group(1)) + 1), s)


def _sql(s):
    n = iter(range(1, 100))
    return PRINTF.sub(lambda m: "{%d}" % next(n), s.replace("''", "'")).replace("%%", "%")


def la_cau(s):
    return VIET.search(s) and " " in s.strip() and len(s.strip()) >= 8 and not re.search(r"\b(SELECT|INSERT|UPDATE|DELETE)\b", s)


def quet():
    tat_ca = {}
    for goc, _, tep in os.walk(os.path.join(API, "Modules")):
        if "\\bin" in goc or "\\obj" in goc:
            continue
        for t in tep:
            if t.endswith(".cs"):
                tat_ca[os.path.join(goc, t)] = None
    hien_thuc = {}
    for duong in tat_ca:
        if BO_MODULE.search(duong):
            continue
        noi = open(duong, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"class\s+(\w+)[^{]*?:\s*([^{]+)\{", noi):
            for i in re.findall(r"\bI[A-Z]\w+", m.group(2)):
                hien_thuc.setdefault(i, set()).add(duong)
    xet, hang = set(), [os.path.join(API, "Modules", c.replace("/", "\\")) for c in CTRL]
    for _ in range(3):                                   # controller → service → repository
        moi = []
        for duong in hang:
            if duong in xet or not os.path.exists(duong):
                continue
            xet.add(duong)
            noi = open(duong, encoding="utf-8", errors="replace").read()
            for i in set(re.findall(r"\b(I[A-Z]\w+(?:Service|Repository|Repo|Store|Provider|Handler|Client))\b", noi)):
                moi += list(hien_thuc.get(i, ()))
        hang = moi
    mau, proc = {}, set()
    for duong in sorted(xet):
        ten = os.path.relpath(duong, API).replace("\\", "/")
        for i, dong in enumerate(open(duong, encoding="utf-8", errors="replace")):
            proc.update(x.lower() for x in re.findall(r"\b(?:dbo\.)?(proc_[A-Za-z0-9_]+|sp_[A-Za-z0-9_]+)", dong))
            if BO_DONG.search(dong):
                continue
            for noi_suy, s in CS_STR.findall(dong):
                vi = _cs(noi_suy, s).strip()
                if la_cau(vi) and vi.strip(" {}0123456789") :
                    mau.setdefault(vi, "%s:%d" % (ten, i + 1))
    thu_muc = os.path.join(API, "Database", "Scripts")
    for t in sorted(os.listdir(thu_muc)):
        if not t.endswith(".sql"):
            continue
        noi = open(os.path.join(thu_muc, t), encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"CREATE\s+(?:OR\s+ALTER\s+)?PROC(?:EDURE)?\s+(?:\[?dbo\]?\.)?\[?([A-Za-z0-9_]+)\]?(.*?)(?=\n\s*GO\b|\Z)",
                             noi, re.S | re.I):
            if m.group(1).lower() not in proc:
                continue
            for s in SQL_STR.findall(m.group(2)):
                vi = _sql(s).strip()
                if la_cau(vi):
                    mau[vi] = "Database/Scripts/%s (%s)" % (t, m.group(1))     # bản thủ tục mới nhất thắng
    return mau


def cho_cua(text):
    return sorted(set(re.findall(r"\{(\d+)\}", text or "")), key=int)


def main():
    cu = json.load(open(TEP, encoding="utf-8")) if os.path.exists(TEP) else {}
    if "--kiem" in sys.argv:
        thieu = [vi for vi, d in cu.items() if not d.get("lo") or not d.get("en")]
        sai = [vi for vi, d in cu.items() if d.get("lo") and not (cho_cua(d["lo"]) == cho_cua(vi) == cho_cua(d.get("en")))]
        print("câu bên kế toán: %d · chưa dịch: %d · {n} lệch: %d" % (len(cu), len(thieu), len(sai)))
        sys.exit(1 if thieu or sai else 0)
    if not os.path.isdir(API):
        sys.exit("Không thấy mã nguồn bên kế toán ở %s (đặt GLS_API_DIR)." % API)
    mau = quet()
    moi = {vi: {"lo": cu.get(vi, {}).get("lo", ""), "en": cu.get(vi, {}).get("en", ""), "o": o} for vi, o in sorted(mau.items())}
    with open(TEP, "w", encoding="utf-8") as f:
        json.dump(moi, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    thieu = [vi for vi, d in moi.items() if not d["lo"] or not d["en"]]
    print("câu bên kế toán: %d · chưa dịch: %d · câu cũ không còn: %d · ký tự chưa dịch: %d"
          % (len(moi), len(thieu), len([v for v in cu if v not in moi]), sum(map(len, thieu))))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Việc 7 (chuyển trang điều xe sang module Vận tải C#, 08/10): sinh script menu «Vận tải» + mã quyền trang + gán quyền theo vai,
và khoá dịch MENU_* / MENU_*_DESC cho Web — từ đúng MODULES / quy tắc thayDuoc() của trang điều xe (frontend/js/chung.js) và
nhãn trong frontend/js/ngon_ngu.js.

Bố cục (anh Hải 08/10: «giống menu Quản lý kho»): cấp 2 của Vận tải là bảng 2 cột — màn dùng nhiều để thẳng, còn lại gom nhóm
(như «Báo cáo kho»); mỗi mục một biểu tượng riêng + một dòng mô tả ngắn (vi · lo · en).
    python -X utf8 tools/chuyen_csharp/sinh_menu_van_tai.py
"""
import json, re

EPL = r"D:\Demo_Lao\EPL_LAO_REAL"
SQL_RA = r"D:\Demo_Lao\GLS-QLSX-APIs\Backend.API\Database\Scripts\20261008_logistics_menu.sql"
WEB_LOC = r"D:\Demo_Lao\GLS-QLSX-Web\Backend\Base\Localization"

src = open(EPL + r"\frontend\js\chung.js", encoding="utf-8").read()
khoi = src[src.index("const MODULES = EPL.MODULES = ["):src.index("];", src.index("const MODULES = EPL.MODULES = ["))]
MODS = {}
for m in re.finditer(r"\{ id: '([^']+)',\s*nhom: '([^']+)',\s*nav: '([^']+)'(.*?)\},?\s*(?=\n\s*(?://|\{|$))", khoi, re.S):
    vai = re.search(r"vai: \[([^\]]*)\]", m.group(4))
    MODS[m.group(1)] = {"id": m.group(1), "nav": m.group(3),
                        "vai": [x.strip().strip("'") for x in vai.group(1).split(",")] if vai else None}
assert len(MODS) == 24, list(MODS)

t = open(EPL + r"\frontend\js\ngon_ngu.js", encoding="utf-8").read()
TD = json.loads(t[t.index("{"):t.rstrip().rindex("}") + 1])
nhan = lambda k, ng: (TD.get(k) or {}).get(ng) or (TD.get(k) or {}).get("vi") or k

VAI = ["admin", "acct", "expacct", "rev", "treasury", "cash", "fuel", "yard", "repair", "parts", "depot", "driver"]
MAN_CUA_VAI = {"parts": ["xe", "kho-xem"], "repair": ["theo-doi-tuyen", "phieu-xuat-xe", "xe", "kho-xem"]}


def thay_duoc(vai, m):          # y hệt thayDuoc() trong chung.js
    if vai == "driver": return bool(m["vai"] and "driver" in m["vai"])
    if vai == "depot": return bool(m["vai"] and "depot" in m["vai"])
    if vai in MAN_CUA_VAI: return m["id"] in MAN_CUA_VAI[vai]
    if m["vai"]: return vai == "admin" or vai in m["vai"]
    return True


# màn: biểu tượng + mô tả ngắn (vi · lo · en)
MAN = {
    "tong-quan": ("fa-solid fa-gauge-high", "Số liệu tháng, việc chờ, xe trên đường", "ຕົວເລກປະຈຳເດືອນ, ວຽກລໍຖ້າ, ລົດກຳລັງແລ່ນ", "Monthly figures, pending work, trucks on the road"),
    "phieu-xuat-xe": ("fa-solid fa-truck-ramp-box", "Lập DO, chi phí chuyến, khoá phiếu", "ອອກ DO, ຄ່າໃຊ້ຈ່າຍຖ້ຽວ, ລັອກໃບ", "Create DOs, trip costs, lock slips"),
    "phieu-cua-toi": ("fa-solid fa-mobile-screen-button", "App tài xế: chuyến của mình", "ແອັບໂຊເຟີ: ຖ້ຽວຂອງຕົນ", "Driver app: my trips"),
    "kho-xem": ("fa-solid fa-warehouse", "Tồn dầu, phụ tùng, hàng gửi bãi", "ສາງນໍ້າມັນ, ອາໄຫຼ່, ສິນຄ້າຝາກເດີ່ນ", "Fuel, parts and yard cargo stock"),
    "theo-doi": ("fa-solid fa-table-list", "Bảng theo dõi phiếu như Excel", "ຕາຕະລາງຕິດຕາມໃບຄືກັບ Excel", "Trip tracking table, as in Excel"),
    "theo-doi-tuyen": ("fa-solid fa-map-location-dot", "Xe trên đường, bản đồ, mốc chặng", "ລົດຢູ່ເທິງທາງ, ແຜນທີ່, ຈຸດຜ່ານ", "Trucks on the road, map, checkpoints"),
    "de-nghi-chi": ("fa-solid fa-money-bill-transfer", "Tạm ứng, nhiên liệu gửi kế toán chi", "ເບີກລ່ວງໜ້າ, ນໍ້າມັນ ສົ່ງບັນຊີຈ່າຍ", "Advances and fuel for accounting to pay"),
    "de-nghi-xuat-kho": ("fa-solid fa-gas-pump", "Xuất dầu, phụ tùng cho xe", "ເບີກນໍ້າມັນ, ອາໄຫຼ່ ໃຫ້ລົດ", "Issue fuel and parts to trucks"),
    "de-nghi-thu": ("fa-solid fa-hand-holding-dollar", "DO xong, đề nghị thu tiền khách", "DO ສຳເລັດ, ສະເໜີເກັບເງິນລູກຄ້າ", "Completed DOs, request customer payment"),
    "chung-tu": ("fa-solid fa-folder-open", "Hồ sơ chứng từ từng DO", "ເອກະສານຂອງແຕ່ລະ DO", "Documents of each DO"),
    "but-toan-cho": ("fa-solid fa-book", "Khoản chờ gửi bút toán kế toán", "ລາຍການລໍຖ້າສົ່ງບັນທຶກບັນຊີ", "Items waiting for journal entries"),
    "tat-toan": ("fa-solid fa-user-check", "Tạm ứng, hoàn ứng, chốt kỳ tài xế", "ເບີກ, ສົ່ງຄືນ, ປິດງວດໂຊເຟີ", "Driver advances, refunds, period close"),
    "tien-tai-xe": ("fa-solid fa-wallet", "Tiền chuyến, tiền nước theo tài xế", "ເງິນຖ້ຽວ, ເງິນເຕີມນ້ຳ ຕາມໂຊເຟີ", "Trip and water money per driver"),
    "tat-toan-doi-tac": ("fa-solid fa-handshake", "Trả đối tác xe thuê từng chuyến", "ຈ່າຍຄູ່ຮ່ວມລົດເຊົ່າ ແຕ່ລະຖ້ຽວ", "Pay hired-truck partners per trip"),
    "xe-lien-ket": ("fa-solid fa-truck-moving", "Xe thuê, chủ xe, lãi xe liên kết", "ລົດເຊົ່າ, ເຈົ້າຂອງລົດ, ກຳໄລລົດຮ່ວມ", "Hired trucks, owners, partner margin"),
    "nha-cung-cap": ("fa-solid fa-store", "Công nợ trạm dầu, lốp, phí đường", "ໜີ້ປໍ້ານໍ້າມັນ, ຢາງ, ຄ່າທາງ", "Payables: fuel stations, tyres, tolls"),
    "khach-hang": ("fa-solid fa-users", "Khách, bảng giá cước, hợp đồng", "ລູກຄ້າ, ລາຄາຄ່າຂົນສົ່ງ, ສັນຍາ", "Customers, freight rates, contracts"),
    "xe": ("fa-solid fa-truck", "Hồ sơ xe, rơ-moóc, lịch tuần", "ຂໍ້ມູນລົດ, ຫາງລາກ, ຕາຕະລາງອາທິດ", "Truck files, trailers, weekly schedule"),
    "tai-xe": ("fa-solid fa-id-card", "Hồ sơ tài xế, bằng lái", "ຂໍ້ມູນໂຊເຟີ, ໃບຂັບຂີ່", "Driver files, licences"),
    "the-cao-toc": ("fa-solid fa-credit-card", "Thẻ cao tốc, nạp tiền, công nợ", "ບັດທາງດ່ວນ, ເຕີມເງິນ, ໜີ້", "Toll cards, top-ups, payables"),
    "ty-gia": ("fa-solid fa-coins", "Tỷ giá quy đổi về LAK", "ອັດຕາແລກປ່ຽນເປັນ LAK", "Exchange rates to LAK"),
    "tuyen-duong": ("fa-solid fa-road", "Tuyến, chặng, km, gợi ý chi phí", "ເສັ້ນທາງ, ຈຸດຜ່ານ, ກມ, ຄ່າໃຊ້ຈ່າຍແນະນຳ", "Routes, legs, km, cost suggestions"),
    "quy-trinh": ("fa-solid fa-diagram-project", "Công đoạn và ai làm gì", "ຂັ້ນຕອນ ແລະ ໃຜເຮັດຫຍັງ", "Workflow and who does what"),
    "tai-khoan": ("fa-solid fa-user-gear", "Người dùng, vai, gắn tài khoản đăng nhập Web", "ຜູ້ໃຊ້, ບົດບາດ, ເຊື່ອມບັນຊີເຂົ້າລະບົບເວັບ", "Users, roles, Web login link"),
}
assert set(MAN) == set(MODS), set(MODS) ^ set(MAN)

# nhóm cấp 2 (như «Báo cáo kho»): mã, tên (vi · lo · en), biểu tượng, mô tả (vi · lo · en), các màn
NHOM = {
    "TRACKING": (("Theo dõi", "ຕິດຕາມ", "Tracking"), "fa-solid fa-route",
                 ("Phiếu vận chuyển, xe trên đường", "ໃບຂົນສົ່ງ, ລົດເທິງທາງ", "Trips and trucks on the road"),
                 ["theo-doi", "theo-doi-tuyen"]),
    "REQUEST": (("Đề nghị gửi kế toán", "ໃບສະເໜີສົ່ງບັນຊີ", "Requests to accounting"), "fa-solid fa-file-signature",
                ("Chi, xuất kho, thu, hồ sơ DO", "ຈ່າຍ, ເບີກສາງ, ເກັບເງິນ, ເອກະສານ DO", "Payments, stock issues, receipts, DO files"),
                ["de-nghi-chi", "de-nghi-xuat-kho", "de-nghi-thu", "chung-tu", "but-toan-cho"]),
    "SETTLE": (("Tất toán", "ສະສາງ", "Settlement"), "fa-solid fa-scale-balanced",
               ("Tài xế, đối tác, nhà cung cấp", "ໂຊເຟີ, ຄູ່ຮ່ວມ, ຜູ້ສະໜອງ", "Drivers, partners, suppliers"),
               ["tat-toan", "tien-tai-xe", "tat-toan-doi-tac", "xe-lien-ket", "nha-cung-cap"]),
    "MASTER": (("Danh mục", "ຂໍ້ມູນພື້ນຖານ", "Master data"), "fa-solid fa-list",
               ("Khách hàng, xe, tài xế, tuyến…", "ລູກຄ້າ, ລົດ, ໂຊເຟີ, ເສັ້ນທາງ…", "Customers, trucks, drivers, routes…"),
               ["khach-hang", "xe", "tai-xe", "the-cao-toc", "ty-gia", "tuyen-duong"]),
    "SYSTEM": (("Hệ thống", "ລະບົບ", "System"), "fa-solid fa-gears",
               ("Quy trình, tài khoản", "ຂັ້ນຕອນ, ບັນຊີຜູ້ໃຊ້", "Workflow, accounts"),
               ["quy-trinh", "tai-khoan"]),
}
# thứ tự ô cấp 2 (bảng 2 cột, đọc theo hàng): ("man", id) hoặc ("nhom", mã)
CAP2 = [("man", "tong-quan"), ("man", "phieu-xuat-xe"), ("man", "phieu-cua-toi"), ("nhom", "TRACKING"), ("nhom", "REQUEST"),
        ("nhom", "SETTLE"), ("man", "kho-xem"), ("nhom", "MASTER"), ("nhom", "SYSTEM")]
da_xep = [x for _, x in CAP2 if _ == "man"] + [m for k in NHOM for m in NHOM[k][3]]
assert sorted(da_xep) == sorted(MODS), set(MODS) ^ set(da_xep)

pascal = lambda s: "".join(p.capitalize() for p in s.split("-"))
ma_menu = lambda s: "LOGISTICS_" + s.upper().replace("-", "_")
q = lambda s: s.replace("'", "''")

dong_nhom, dong_man, dong_quyen, dem = [], [], [], {}
for i, (loai, x) in enumerate(CAP2, 1):
    if loai == "nhom":
        ten, ic, mo, _ = NHOM[x]
        dong_nhom.append("    ('LOGISTICS_GRP_%s', N'%s', N'%s', %d, N'%s')" % (x, q(ten[0]), q(mo[0]), i * 10, ic))
for i, (loai, x) in enumerate(CAP2, 1):
    cac = [(x, None, i * 10)] if loai == "man" else [(m, "LOGISTICS_GRP_" + x, j * 10) for j, m in enumerate(NHOM[x][3], 1)]
    for m, cha, thu_tu in cac:
        ic, mo = MAN[m][0], MAN[m][1]
        dong_man.append("    ('%s', %s, N'%s', N'%s', '%s', 'Logistics.%s', %d, N'%s', %d)" % (
            ma_menu(m), "'%s'" % cha if cha else "NULL", q(nhan(MODS[m]["nav"], "vi")), q(mo), m, pascal(m), thu_tu, ic, 3 if cha else 2))
        for v in VAI:
            if thay_duoc(v, MODS[m]):
                dong_quyen.append("    ('%s', 'Logistics.%s')" % (v, pascal(m)))
                dem[v] = dem.get(v, 0) + 1

sql = """/*==================================================================================================
Author      : EPL Logistics
Created date: 2026-10-08
Description : Module Vận tải — việc 7: menu «Vận tải» trên Web GLS + 24 mã quyền trang Logistics.<Màn> + gán quyền trang cho 12 vai
              LOGISTICS_* theo đúng quy tắc vai nào thấy màn nào của trang điều xe (frontend/js/chung.js thayDuoc).
              Bố cục giống menu Quản lý kho: cấp 2 là bảng 2 cột — 4 màn để thẳng (Tổng quan, Phiếu xuất xe, Phiếu của tôi,
              Xem kho) + 5 nhóm (Theo dõi, Đề nghị gửi kế toán, Tất toán, Danh mục, Hệ thống) như «Báo cáo kho»; mỗi mục một
              biểu tượng + một dòng mô tả (khoá MENU_<mã>_DESC ở Web).
              Mục màn là trang Web GLS (PAGE / SELF), đường cố định /Logistics/<màn>: màn đã chuyển sang C# → trang thật; chưa
              chuyển → trang chờ trong Web (LogisticsPageController). Trang điều xe chỉ còn là API.
              SINH TỰ ĐỘNG (bộ sinh EPL_LAO_REAL/tools/chuyen_csharp/sinh_menu_van_tai.py). Cần chạy
              20261008_logistics_role_permissions.sql trước. Chạy lại an toàn (sửa cả bố cục đã tạo trước). sqlcmd -f 65001.
Database    : DB QLSX (DB demo Lào / host).
==================================================================================================*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @ModuleId INT = (SELECT ModuleId FROM dbo.Sys_Module WHERE ModuleCode = 'LOGISTICS');
IF @ModuleId IS NULL OR NOT EXISTS (SELECT 1 FROM dbo.Sys_Role WHERE RoleCode = 'LOGISTICS_ADMIN')
BEGIN
    RAISERROR(N'Chưa chạy 20261008_logistics_role_permissions.sql (module LOGISTICS / vai LOGISTICS_*) — dừng.', 16, 1);
    RETURN;
END;

DECLARE @Nhom TABLE (MenuCode VARCHAR(50) NOT NULL, Ten NVARCHAR(150) NOT NULL, MoTa NVARCHAR(250) NOT NULL, ThuTu INT NOT NULL,
                     Icon NVARCHAR(80) NOT NULL);
INSERT INTO @Nhom VALUES
%s;

-- Cha NULL = ô thẳng ở cấp 2 (dưới LOGISTICS_ROOT)
DECLARE @Man TABLE (MenuCode VARCHAR(50) NOT NULL, Cha VARCHAR(50) NULL, Ten NVARCHAR(150) NOT NULL, MoTa NVARCHAR(250) NOT NULL,
                    Man VARCHAR(50) NOT NULL, MaQuyen VARCHAR(100) NOT NULL, ThuTu INT NOT NULL, Icon NVARCHAR(80) NOT NULL, Cap INT NOT NULL);
INSERT INTO @Man VALUES
%s;

DECLARE @VaiQuyen TABLE (Vai VARCHAR(20) NOT NULL, MaQuyen VARCHAR(100) NOT NULL);
INSERT INTO @VaiQuyen VALUES
%s;

BEGIN TRAN;

-- cấp 1: «Vận tải» (sau Quản lý kho = 40)
IF NOT EXISTS (SELECT 1 FROM dbo.Sys_Menu WHERE MenuCode = 'LOGISTICS_ROOT')
    INSERT INTO dbo.Sys_Menu (ParentId, ModuleId, MenuCode, MenuName, MenuDesc, Url, IconClass, MenuType, OpenMode, SortOrder, LevelNo,
                              IsVisible, IsActive, IsSystem, RequiredPermissionCode, CreatedBy)
    VALUES (NULL, @ModuleId, 'LOGISTICS_ROOT', N'Vận tải', N'Điều xe, phiếu xuất xe (DO), chi phí chuyến, tất toán', NULL,
            N'fa-solid fa-truck', 'GROUP', 'SELF', 45, 1, 1, 1, 0, NULL, 1);
DECLARE @Goc INT = (SELECT MenuId FROM dbo.Sys_Menu WHERE MenuCode = 'LOGISTICS_ROOT');

-- cấp 2: nhóm
MERGE dbo.Sys_Menu AS d
USING (SELECT * FROM @Nhom) AS n ON d.MenuCode = n.MenuCode
WHEN MATCHED THEN UPDATE SET ParentId = @Goc, MenuName = n.Ten, MenuDesc = n.MoTa, SortOrder = n.ThuTu, IconClass = n.Icon,
                             MenuType = 'GROUP', OpenMode = 'SELF', LevelNo = 2, IsVisible = 1, IsActive = 1,
                             UpdatedDate = SYSDATETIME(), UpdatedBy = 1
WHEN NOT MATCHED THEN INSERT (ParentId, ModuleId, MenuCode, MenuName, MenuDesc, IconClass, MenuType, OpenMode, SortOrder, LevelNo,
                              IsVisible, IsActive, IsSystem, CreatedBy)
     VALUES (@Goc, @ModuleId, n.MenuCode, n.Ten, n.MoTa, n.Icon, 'GROUP', 'SELF', n.ThuTu, 2, 1, 1, 0, 1);

-- màn: cấp 2 (ô thẳng) hoặc cấp 3 (trong nhóm) — trang Web /Logistics/<màn>
MERGE dbo.Sys_Menu AS d
USING (SELECT m.*, ISNULL(g.MenuId, @Goc) AS ChaId FROM @Man m LEFT JOIN dbo.Sys_Menu g ON g.MenuCode = m.Cha) AS n
    ON d.MenuCode = n.MenuCode
WHEN MATCHED THEN UPDATE SET ParentId = n.ChaId, MenuName = n.Ten, MenuDesc = n.MoTa, SortOrder = n.ThuTu, LevelNo = n.Cap,
                             RequiredPermissionCode = n.MaQuyen, Url = N'/Logistics/' + n.Man, MenuType = 'PAGE', OpenMode = 'SELF',
                             IconClass = n.Icon, IsVisible = 1, IsActive = 1, UpdatedDate = SYSDATETIME(), UpdatedBy = 1
WHEN NOT MATCHED THEN INSERT (ParentId, ModuleId, MenuCode, MenuName, MenuDesc, Url, IconClass, MenuType, OpenMode, SortOrder, LevelNo,
                              IsVisible, IsActive, IsSystem, RequiredPermissionCode, CreatedBy)
     VALUES (n.ChaId, @ModuleId, n.MenuCode, n.Ten, n.MoTa, N'/Logistics/' + n.Man, n.Icon, 'PAGE', 'SELF', n.ThuTu, n.Cap,
             1, 1, 0, n.MaQuyen, 1);

-- nhóm cũ của bố cục trước (Điều xe / Kho / Danh mục / Hệ thống theo thanh bên) không còn dùng: tắt nếu đã tạo
UPDATE dbo.Sys_Menu SET IsVisible = 0, IsActive = 0, UpdatedDate = SYSDATETIME(), UpdatedBy = 1
WHERE MenuCode IN ('LOGISTICS_GRP_TRANSPORT', 'LOGISTICS_GRP_WAREHOUSE')
  AND NOT EXISTS (SELECT 1 FROM dbo.Sys_Menu c WHERE c.ParentId = dbo.Sys_Menu.MenuId AND c.IsActive = 1);

-- 24 mã quyền trang (PAGE), gắn mục menu
MERGE dbo.Sys_Permission AS d
USING (SELECT m.MaQuyen, m.Ten, m.MenuCode, mm.MenuId FROM @Man m JOIN dbo.Sys_Menu mm ON mm.MenuCode = m.MenuCode) AS n
    ON d.PermissionCode = n.MaQuyen
WHEN MATCHED THEN UPDATE SET PermissionName = N'Vận tải — ' + n.Ten, PermissionScope = 'PAGE', ModuleId = @ModuleId, MenuId = n.MenuId,
                             TargetCode = n.MenuCode, IsActive = 1, UpdatedDate = SYSDATETIME(), UpdatedBy = 1
WHEN NOT MATCHED THEN INSERT (PermissionCode, PermissionName, PermissionScope, ModuleId, MenuId, TargetCode, Description, IsActive, IsSystem, CreatedBy)
     VALUES (n.MaQuyen, N'Vận tải — ' + n.Ten, 'PAGE', @ModuleId, n.MenuId, n.MenuCode, N'Màn trang điều xe EPL (module Vận tải)', 1, 0, 1);

-- vai LOGISTICS_* → quyền trang theo quy tắc trang điều xe (chỉ thêm, không gỡ quyền admin GLS đã chỉnh tay)
INSERT INTO dbo.Sys_RolePermission (RoleId, PermissionId, Effect, IsActive, CreatedBy)
SELECT r.RoleId, p.PermissionId, 'ALLOW', 1, 1
FROM @VaiQuyen v
JOIN dbo.Sys_Role r ON r.RoleCode = 'LOGISTICS_' + UPPER(v.Vai)
JOIN dbo.Sys_Permission p ON p.PermissionCode = v.MaQuyen
WHERE NOT EXISTS (SELECT 1 FROM dbo.Sys_RolePermission x WHERE x.RoleId = r.RoleId AND x.PermissionId = p.PermissionId);

COMMIT;

-- bộ nhớ đệm ui-shell làm mới ngay (như proc_SysMenu_AdminUpsert / proc_SysRolePermission_Save)
EXEC dbo.proc_SysAppVersion_Touch @VersionKey = 'MENU_VERSION', @Silent = 1;
EXEC dbo.proc_SysAppVersion_Touch @VersionKey = 'PERMISSION_VERSION', @Silent = 1;

SELECT r.RoleCode, COUNT(*) AS SoManDuocVao
FROM dbo.Sys_RolePermission rp
JOIN dbo.Sys_Role r ON r.RoleId = rp.RoleId AND r.RoleCode LIKE 'LOGISTICS[_]%%'
JOIN dbo.Sys_Permission p ON p.PermissionId = rp.PermissionId AND p.PermissionScope = 'PAGE' AND p.PermissionCode LIKE 'Logistics.%%'
WHERE rp.IsActive = 1
GROUP BY r.RoleCode ORDER BY r.RoleCode;
PRINT N'Xong: menu Vận tải (4 màn thẳng + 5 nhóm, 24 màn), 24 mã quyền trang, quyền trang cho 12 vai LOGISTICS_*.';
""" % (",\n".join(dong_nhom), ",\n".join(dong_man), ",\n".join(dong_quyen))
open(SQL_RA, "w", encoding="utf-8").write(sql)
print("SQL:", SQL_RA, "| so man", len(dong_man), "| quyen vai:", dict(sorted(dem.items())))

# ---- khoá dịch MENU_* và MENU_*_DESC cho Web (vi / lo / en); khoá đã có thì cập nhật giá trị
khoa = {"MENU_LOGISTICS_ROOT": {"vi": "Vận tải", "lo": "ຂົນສົ່ງ", "en": "Transport"}}
for ma, (ten, _, mo, _) in NHOM.items():
    khoa["MENU_LOGISTICS_GRP_" + ma] = dict(zip(("vi", "lo", "en"), ten))
    khoa["MENU_LOGISTICS_GRP_" + ma + "_DESC"] = dict(zip(("vi", "lo", "en"), mo))
for m in MODS:
    khoa["MENU_" + ma_menu(m)] = {ng: nhan(MODS[m]["nav"], ng) for ng in ("vi", "lo", "en")}
    khoa["MENU_" + ma_menu(m) + "_DESC"] = dict(zip(("vi", "lo", "en"), MAN[m][1:]))
for ng in ("vi", "lo", "en"):
    p = WEB_LOC + "\\%s.json" % ng
    b = open(p, "rb").read(); bom = b.startswith(b"\xef\xbb\xbf"); tx = b.decode("utf-8-sig")
    nl = "\r\n" if "\r\n" in tx else "\n"
    co = json.loads(tx)
    sua = 0
    for k, v in khoa.items():
        if k in co and co[k] != v[ng]:
            cu_dong = '  %s: %s,' % (json.dumps(k), json.dumps(co[k], ensure_ascii=False))
            if cu_dong in tx:
                tx = tx.replace(cu_dong, '  %s: %s,' % (json.dumps(k), json.dumps(v[ng], ensure_ascii=False))); sua += 1
    co = json.loads(tx)
    moi = [(k, v[ng]) for k, v in khoa.items() if k not in co]
    if moi:
        moc = '  "MENU_LOGISTICS_JOURNAL_ENTRY_DESC": '
        i = tx.index(moc); j = tx.index(nl, i) + len(nl)
        tx = tx[:j] + "".join('  %s: %s,%s' % (json.dumps(k), json.dumps(v, ensure_ascii=False), nl) for k, v in moi) + tx[j:]
    json.loads(tx)
    open(p, "wb").write((b"\xef\xbb\xbf" if bom else b"") + tx.encode("utf-8"))
    print(ng, "them", len(moi), "| sua", sua)

# -*- coding: utf-8 -*-
"""Mở 1371, 4021, 4022 trong danh mục tài khoản Lào bên anh Tune — qua API `accounting/lao-accounts`, không sửa thẳng DB.

    python tools/mo_ma_con_tune.py                    # API chạy ở máy (127.0.0.1:5090) — đã chạy 01/10
    python tools/mo_ma_con_tune.py https://<API host> # khi bản mới đã lên host mà danh mục host còn thiếu ba mã

Đúng cây anh Khampla: 137 và 402 chuyển thành tài khoản tổng hợp, ba mã con là tài khoản lá. Chạy lại không sao (mã đã có thì
bỏ qua). Token đọc từ EPL_ACC_CODE_TOKEN trong .env, không in ra. Hợp đồng anh Tune mục 12.12.1."""
import json, urllib.request, urllib.error

import sys
# Mặc định API ở máy (5090). Khi bản mới đã lên host mà danh mục host còn thiếu ba mã: python tools/mo_ma_con_tune.py https://<host API>
GOC = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5090").rstrip("/")
G = GOC + "/api/v1/accounting/lao-accounts"
tk = next(d.split("=", 1)[1].strip().strip('"').strip("'") for d in open(__import__("os").path.join(__import__("os").path.dirname(__file__), "..", ".env"), encoding="utf-8")
          if d.strip().startswith("EPL_ACC_CODE_TOKEN="))


def goi(method, url, body=None):
    r = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode() if body is not None else None, method=method,
                               headers={"Authorization": "Bearer " + tk, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=60) as t:
            return t.status, json.loads(t.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def ds():
    return {str(r["ACC_CODE"]): r for r in goi("GET", G)[1]["Result"]["Rows"]}


MOI = [("1371", "137", "13", "ສາງສິນຄ້າ, ວັດຖຸ", "Kho hàng, vật tư (EPL) — mã con anh Khampla", 1),
       ("4021", "402", "40", "ໜີ້ຕ້ອງສົ່ງ ຜູ້ສະໜອງ", "Phải trả nhà cung cấp (EPL)", 2),
       ("4022", "402", "40", "ເຈົ້າໜີ້ເຈົ້າຂອງລົດຮ່ວມ", "Phải trả chủ xe liên kết (EPL)", 2)]

d = ds()
for ma, cha, ong, ten, mo_ta, du in MOI:
    if ma in d:
        print("%s đã có (cha %s)" % (ma, d[ma].get("ACC_PARENTID")))
        continue
    c = d.get(cha)
    if c and c.get("ACC_ACCOUNTWRITE"):
        s, g = goi("POST", G + "/update", {"Code": cha, "ParentCode": c.get("ACC_PARENTID"), "Name": c["ACC_NAME"],
                                           "Description": c.get("ACC_DESCRIPTION"), "Active": True, "Posting": False,
                                           "ForeignCurrency": bool(c.get("ACC_ISMONEYCURENTCY")), "Balance": c["ACC_BALANCE"],
                                           "GroupId": c.get("ACCG_AUTOID"), "TypeId": c.get("ACCT_AUTOID"), "Structure": 0, "Version": c["Version"]})
        print("chuyển %s thành tài khoản tổng hợp → %s %s" % (cha, s, (g or {}).get("Message")))
        d = ds()
    goc = cha if not d[cha].get("ACC_ACCOUNTWRITE") else ong
    s, g = goi("POST", G, {"Code": ma, "ParentCode": goc, "Name": ten, "Description": mo_ta, "Active": True, "Posting": True,
                           "ForeignCurrency": False, "Balance": du, "Structure": 1})
    print("tạo %s dưới %s → %s %s" % (ma, goc, s, (g or {}).get("Message")))
    d = ds()

s, g = goi("GET", GOC + "/api/v1/accounting/cmpayment-receipt/country-accounts?countryId=11")
co = {str(a.get("AccCode") or a.get("ACC_CODE")) for a in (g.get("Result") or [])}
print("có ở danh mục hạch toán quốc gia 11:", {m: m in co for m in ("1371", "4021", "4022", "137", "402")})

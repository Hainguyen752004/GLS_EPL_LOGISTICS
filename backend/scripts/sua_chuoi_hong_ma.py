# -*- coding: utf-8 -*-
"""Sua nhung chuoi tieng Viet bi MA HOA HAI LAN trong ma nguon backend.

VAN DE. Nam tep trong `app/` co chuoi tieng Viet bi ghi nham: byte UTF-8 cua
tieng Viet bi doc lai nhu cp1252 roi ghi ra UTF-8 mot lan nua. Ket qua la thay
vi "Chi DO dang van chuyen moi duoc hoan tat giao." thi ma nguon chua
"Chá»‰ DO Ä‘ang váº­n chuyá»ƒn má»›i Ä‘Æ°á»£c hoÃ n táº¥t giao."

Day KHONG phai loi hien thi cua may ai do: chuoi trong TEP da sai, nen bat ke
nguoi dung mo bang gi thi ho cung doc ra dung chuoi rac do. Va cho no xuat hien
la nhung THONG BAO LOI — dung luc nguoi dung dang be tac va can doc de biet
phai lam gi.

CACH SUA, va vi sao no an toan. Khong the giai ma ca tep mot lan: cac tep nay
con chua tieng Viet ghi DUNG (chu thich moi viet), va giai ma ca tep se lam vo
phan dung do. Nen sua theo TUNG CUM ky tu ngoai ASCII:

  · Cum bi ma hoa hai lan thi MOI ky tu cua no deu nam trong cp1252 — do la
    cach no sinh ra. Nen `cum.encode('cp1252')` chay duoc.
  · Tieng Viet ghi DUNG thi phan lon ky tu nam NGOAI cp1252 (`đ`, `ơ`, `ư`,
    `ế`, `ộ`...), nen `encode('cp1252')` nem loi va cum do duoc de nguyen.
  · Truong hop con lai — mot ky tu Latin-1 don le nhu `á` — encode duoc nhung
    mot byte le khong phai UTF-8 hop le, nen `decode('utf-8')` nem loi va cum
    do cung duoc de nguyen.

Ba lop do cong lai nghia la phep sua chi cham vao cum THUC SU bi hong. Them mot
chot cuoi: chi thay khi ket qua co it nhat mot ky tu rieng cua tieng Viet.

Chay thu truoc (mac dinh), `--that` moi ghi.
"""

import io
import os
import re
import sys


# Ky tu rieng cua tieng Viet — de xac nhan ket qua giai ma la tieng Viet that
# chu khong phai mot chuoi byte tinh co giai ma duoc.
CHU_VIET = set(
    "ăâđêôơưĂÂĐÊÔƠƯ"
    "áàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩị"
    "óòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
    "ÁÀẢÃẠẮẰẲẴẶẤẦẨẪẬÉÈẺẼẸẾỀỂỄỆÍÌỈĨỊ"
    "ÓÒỎÕỌỐỒỔỖỘỚỜỞỠỢÚÙỦŨỤỨỪỬỮỰÝỲỶỸỴ"
)

# Cum lien tiep cac ky tu NGOAI ASCII.
CUM = re.compile(r"[^\x00-\x7f]+")


#: Thu cp1252 TRUOC roi moi latin-1.
#:
#: Vi sao can ca hai. Cum bi hong duoc sinh ra bang cach doc byte UTF-8 nhu mot
#: bang ma mot-byte, va bang do khong dong nhat: `Ã¡` doc duoc bang cp1252, con
#: `ề` (E1 BB 81) chua byte 0x81 — vi tri KHONG co trong cp1252 — nen chi
#: latin-1 dua no ve dung byte cu. Chi thu cp1252 thi mot phan chuoi duoc sua
#: va mot phan khong: ket qua la "số tiá»n" — nua dung nua sai, doc ra con te
#: hon de nguyen ca cum sai.
BANG_MA = ("cp1252", "latin-1")


def sua_cum(cum):
    """Cum da sua, hoac chinh no khi khong phai chuoi bi ma hoa hai lan."""
    if len(cum) < 2:
        return cum
    for bang in BANG_MA:
        try:
            ra = cum.encode(bang).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if ra != cum and any(ch in CHU_VIET for ch in ra):
            return ra
    return cum


def sua_tep(duong):
    """Tra ve `(noi_dung_moi, so_cum_da_sua, vi_du)`."""
    tho = open(duong, "rb").read()
    co_bom = tho[:3] == b"\xef\xbb\xbf"
    s = tho.decode("utf-8-sig")
    dem = []

    def thay(m):
        cu = m.group(0)
        moi = sua_cum(cu)
        if moi != cu:
            dem.append((cu, moi))
        return moi

    moi = CUM.sub(thay, s)
    return moi, len(dem), dem[:3], co_bom


def main():
    that = "--that" in sys.argv
    tong = 0
    for goc, _, tep in os.walk("app"):
        if "__pycache__" in goc:
            continue
        for t in sorted(tep):
            if not t.endswith(".py"):
                continue
            p = os.path.join(goc, t)
            noi_dung, so, vi_du, co_bom = sua_tep(p)
            if not so:
                continue
            tong += so
            print("%-56s %3d cum" % (p, so))
            for cu, m in vi_du:
                print("      %-34s -> %s" % (cu[:32], m[:44]))
            if that:
                # GIU BOM neu tep von co: bo BOM di la mot thay doi khong ai
                # yeu cau, va no lam moi cong cu so sanh bao ca tep da doi.
                with open(p, "wb") as f:
                    if co_bom:
                        f.write(b"\xef\xbb\xbf")
                    f.write(noi_dung.encode("utf-8"))
    print()
    print("TONG:", tong, "cum", "(DA GHI)" if that else "(chay thu — them --that de ghi)")


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    main()

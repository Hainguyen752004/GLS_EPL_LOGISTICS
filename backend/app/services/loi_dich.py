# -*- coding: utf-8 -*-
"""Bản tiếng Lào / tiếng Anh cho câu lỗi và cảnh báo của API (09/10/2026).

API báo lỗi bằng {"ma": …, "loi": "<câu tiếng Việt>"}; màn cũ (frontend/js/chung.js chuLoi) và Web (LogisticsApiClient) hiện
`loi_lo` / `loi_en` khi có. Trước 09/10 chỉ ~26 / ~460 câu có bản dịch. Câu trong mã vẫn viết tiếng Việt như cũ; danh mục mẫu câu
(loi_dich.json, sinh bằng tools/sinh_loi_dich.py) mang bản Lào / Anh — `them_dich` gắn vào lúc trả về:

    "Xe chưa về (trạng thái {1}) thì chưa khoá phiếu."  → so khớp câu thật, lấy {1} = "dispatched", ghép vào mẫu lo / en.

Giá trị chèn nào tự nó là một câu / cụm có trong danh mục (câu ghép từ câu khác, cụm "chưa xuất phát"…) thì dịch luôn — câu Lào / Anh
không chen cụm tiếng Việt. Câu không khớp mẫu nào (câu bên kế toán ngoài danh mục, câu từ máy khác…) giữ nguyên tiếng Việt,
không gắn bản dịch.
Gọi ở: main.py (mọi HTTPException trả ra) · routes/phieu.kiem_lai, khoa_phieu (cảnh báo khoá phiếu, chỗ chặn khoá) · các chỗ trả lỗi
theo đường thường: routes/lien_thong.thu, routes/de_nghi (SO nhiên liệu), services/gui_but_toan_tune.gui_het (chi_tiet_loi).
Câu lỗi bên hệ kế toán (loi_dich_ke_toan.json) nạp cùng — câu EPL bọc câu bên đó được dịch cả hai lớp.

CHỮ MÁY TỰ SINH LƯU TRONG DỮ LIỆU (10/10, anh Hải: chọn tiếng Lào mà màn vẫn hiện "Tài xế báo đã về · km …", "Lĩnh … lít tại …"):
mô tả chứng từ (chung_tu.mo_ta) và ghi chú sự kiện máy tự ghi (TripEvent.note) — danh mục RIÊNG mo_ta_dich.json (viết tay, không do
tools/sinh_loi_dich.py sinh), dịch lúc trả ra (`gan_ban_dich`: thêm <trường>_lo / <trường>_en). Câu lưu trong DB GIỮ NGUYÊN (gửi sang
kế toán, tìm kiếm, dữ liệu cũ đều như trước). Tách khỏi danh mục câu lỗi để ghi chú người dùng tự gõ không bị dịch nhầm theo mẫu
câu lỗi; ghi chú tự gõ không khớp mẫu nào → không có bản dịch, màn hiện nguyên chữ."""
import json
import os
import re
from functools import lru_cache

TEP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "loi_dich.json")
# câu lỗi của HỆ KẾ TOÁN mà EPL chuyển tiếp ("Hệ kế toán từ chối: {1}" — {1} là câu bên đó), sinh bằng tools/sinh_loi_dich_ke_toan.py
TEP_KE_TOAN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "loi_dich_ke_toan.json")
TEP_MO_TA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mo_ta_dich.json")
CHO = re.compile(r"\{(\d+)\}")
SAU_TOI_DA = 3            # độ sâu dịch giá trị chèn (câu EPL bọc câu bên kế toán, câu đó lại ghép câu khác)

_TRON = {}                # câu không có chỗ chèn: vi → {lo, en}
_MAU = []                 # (regex, số chỗ, {lo, en}) — mẫu cụ thể (nhiều chữ cố định) thử trước
_TRON_MT, _MAU_MT = {}, []   # như trên, cho chữ máy tự sinh lưu trong dữ liệu (mo_ta_dich.json)


def _dung(tat_ca, tron, mau_ds):
    """Danh mục {câu Việt: {lo, en}} → câu trọn (tron) + mẫu có chỗ chèn (mau_ds, cụ thể trước)."""
    tron.clear()
    mau_ds.clear()
    for vi, d in tat_ca.items():
        if not d.get("lo") or not d.get("en"):
            continue
        ban = {"lo": d["lo"], "en": d["en"]}
        if not CHO.search(vi):
            tron[vi] = ban
            continue
        manh = CHO.split(vi)                # [chữ, số, chữ, số, …, chữ]
        mau = "".join(re.escape(m) if i % 2 == 0 else "(?P<c%s>.*?)" % m for i, m in enumerate(manh))
        try:
            rx = re.compile(r"\A" + mau + r"\Z", re.S)
        except re.error:                    # một số {n} lặp lại trong câu — bỏ mẫu đó (giữ tiếng Việt)
            continue
        mau_ds.append((rx, len(re.sub(CHO, "", vi)), ban))
    mau_ds.sort(key=lambda x: -x[1])


def _doc(*tep_ds):
    tat_ca = {}
    for tep in tep_ds:                             # tệp sau thắng khi trùng câu
        if os.path.exists(tep):
            tat_ca.update(json.load(open(tep, encoding="utf-8")))
    return tat_ca


def _nap():
    _dung(_doc(TEP_KE_TOAN, TEP), _TRON, _MAU)     # câu EPL sau — trùng câu thì bản EPL thắng
    _dung(_doc(TEP_MO_TA), _TRON_MT, _MAU_MT)
    dich.cache_clear()
    dich_mo_ta.cache_clear()


def _khop(vi, lang, sau, tron, mau_ds, de_quy):
    if not vi or lang not in ("lo", "en"):
        return None
    goc, vi = vi, vi.strip()
    if vi in tron:
        return tron[vi][lang]
    for rx, _, ban in mau_ds:
        # thử câu đã cắt khoảng trắng hai đầu, rồi câu nguyên: chỗ chèn cuối câu rỗng ("Phiếu xuất xe X ·  → " — phiếu chưa có tuyến)
        m = rx.match(vi) or (rx.match(goc) if goc != vi else None)
        if not m:
            continue
        gia = {k[1:]: v for k, v in m.groupdict().items()}
        if sau < SAU_TOI_DA:
            gia = {k: (de_quy(v, lang, sau + 1) or v) for k, v in gia.items()}
        return CHO.sub(lambda c: gia.get(c.group(1), c.group(0)), ban[lang])
    return None


@lru_cache(maxsize=2048)
def dich(vi, lang, sau=0):
    """Câu tiếng Việt `vi` → bản `lang` (lo · en); không có mẫu khớp → None."""
    return _khop(vi, lang, sau, _TRON, _MAU, dich)


@lru_cache(maxsize=4096)
def dich_mo_ta(vi, lang, sau=0):
    """Như `dich`, cho chữ máy tự sinh lưu trong dữ liệu (mô tả chứng từ, ghi chú sự kiện) — chỉ theo mo_ta_dich.json."""
    return _khop(vi, lang, sau, _TRON_MT, _MAU_MT, dich_mo_ta)


def gan_ban_dich(x, truong):
    """dict `x`: thêm `<truong>_lo` / `<truong>_en` khi x[truong] khớp mẫu chữ máy tự sinh. Trả lại `x`."""
    vi = x.get(truong)
    if isinstance(vi, str) and vi:
        for lang in ("lo", "en"):
            ban = dich_mo_ta(vi, lang)
            if ban:
                x[truong + "_" + lang] = ban
    return x


def them_dich(x):
    """Gắn loi_lo / loi_en vào mọi {ma, loi} trong `x` (dict · list lồng nhau) chưa có bản dịch. Trả lại chính `x`."""
    if isinstance(x, dict):
        if isinstance(x.get("loi"), str) and "ma" in x:
            for lang in ("lo", "en"):
                if not x.get("loi_" + lang):
                    ban = dich(x["loi"], lang)
                    if ban:
                        x["loi_" + lang] = ban
        for v in x.values():
            if isinstance(v, (dict, list)):
                them_dich(v)
    elif isinstance(x, list):
        for v in x:
            them_dich(v)
    return x


_nap()

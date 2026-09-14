# -*- coding: utf-8 -*-
"""Bắn cả bộ câu hỏi kiểm thử lên tác tử THẬT (Gemini + API EPL) và ghi kết quả từng câu.

    python kiem/chay_bo_cau_hoi.py                  # cả bộ, tiếng Việt, + 6 gợi ý màn hình × 3 ngôn ngữ
    python kiem/chay_bo_cau_hoi.py --nhom A,B,C     # chỉ vài nhóm (chữ đầu của mã câu)
    python kiem/chay_bo_cau_hoi.py --goi-y          # chỉ 18 câu gợi ý trên màn hình

Không phải bộ kiểm đơn vị — nó tốn tiền gọi mô hình và mất 5–15 giây mỗi câu. Dùng để soát
trước buổi demo: câu nào lỗi, câu nào không gọi công cụ mong đợi, câu ranh giới nào không
từ chối. Kết quả ghi vào kiem/ket_qua_bo_cau_hoi.md để đọc lại.
"""
import argparse
import io
import os
import sys
import time

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC)
sys.path.insert(0, os.path.join(GOC, "docs"))

import bo_cau_hoi  # noqa: E402
import cong_cu     # noqa: E402
import tac_tu      # noqa: E402

GOI_Y_MAN_HINH = {
    "vi": ['Hôm nay có gì cần lo không?', 'Có sự cố nào đang mở không?',
           'Bao nhiêu lệnh giao hàng đang chạy, cái nào sắp trễ?', 'Báo giá nào sắp hết hạn trong 7 ngày?',
           'Xe và tài xế nào đang rảnh?', 'Giấy tờ xe hay bằng lái nào sắp hết hạn?'],
    "en": ['Anything I should worry about today?', 'Any open incidents?',
           'How many orders are in transit, which are about to be late?', 'Which quotations expire within 7 days?',
           'Which vehicles and drivers are free?', 'Any vehicle papers or licences expiring soon?'],
    "lo": ['ມື້ນີ້ມີຫຍັງຕ້ອງກັງວົນບໍ?', 'ມີເຫດການໃດຍັງເປີດຢູ່ບໍ?',
           'ມີ DO ຈັກໃບກຳລັງຂົນສົ່ງ, ໃບໃດໃກ້ຊ້າ?', 'ໃບສະເໜີລາຄາໃດຈະໝົດອາຍຸໃນ 7 ມື້?',
           'ລົດ ແລະ ຄົນຂັບຄັນໃດຫວ່າງ?', 'ເອກະສານລົດ ຫຼື ໃບຂັບຂີ່ໃດໃກ້ໝົດອາຍຸ?'],
}
# Câu "hỏi tiếp" cần câu trước đó trong lịch sử: mã câu → mã câu phải hỏi trước.
CAU_TRUOC = {"J1": "A1", "J2": "J1", "J3": "C4", "J4": "E5", "J5": "F5"}
# Câu đổi ngôn ngữ: mã → (mã câu gốc, ngôn ngữ)
DOI_NGON_NGU = {"L1": ("A1", "lo"), "L2": ("E5", "en")}
TU_TU_CHOI = ("không thể", "không làm", "chỉ đọc", "không hỗ trợ", "không được", "màn", "chưa hỗ trợ",
              "cannot", "can't", "read-only", "not able", "ບໍ່ສາມາດ", "ບໍ່ໄດ້")


def doc_env():
    ra = {}
    duong = os.path.normpath(os.path.join(GOC, "..", "EPL_System", ".env"))
    for dong in io.open(duong, encoding="utf-8"):
        dong = dong.strip()
        if dong and not dong.startswith("#") and "=" in dong:
            k, v = dong.split("=", 1)
            ra[k.strip()] = v.strip().strip('"').strip("'")
    return ra


def hoi(cau, lich_su, ngon_ngu):
    goi = []
    bat_dau = time.time()
    ket = tac_tu.tra_loi(cau, lich_su, ngon_ngu,
                         phat=lambda sk, dl: goi.append(dl.get("ten")) if sk == "cong_cu" else None)
    giay = time.time() - bat_dau
    return ket, goi, giay


def in_ngay(chu):
    sys.stdout.write(chu + "\n")
    sys.stdout.flush()


def bo_ngoac(cau):
    """'[Hỏi ngay sau A1] Cái sự cố đó…' → 'Cái sự cố đó…'."""
    return cau.split("]", 1)[1].strip() if cau.startswith("[") and "]" in cau else cau


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--nhom", default="", help="chữ đầu mã câu, ví dụ A,B,K")
    p.add_argument("--goi-y", action="store_true", help="chỉ chạy 18 câu gợi ý trên màn hình")
    p.add_argument("--nghi", type=float, default=2.0, help="giây nghỉ giữa hai câu, tránh chạm giới hạn tần suất")
    a = p.parse_args()

    env = doc_env()
    cong_cu.cau_hinh(cong_cu.GOC_API, env.get("EPL_TMS_API_TOKEN", ""))
    tac_tu.cau_hinh(env.get("GEMINI_API_KEY_GT", ""), "gemini-2.5-flash")
    in_ngay("API EPL: %s · mô hình: %s · python: %s" % (cong_cu.GOC_API, tac_tu.MO_HINH, sys.executable))

    bang = {c[0]: c for c in bo_cau_hoi.CAU_HOI}
    viec = []                                   # (nhãn, mã, ngôn ngữ, câu, công cụ mong đợi, cần thấy)
    if not a.goi_y:
        nhom = {x.strip().upper() for x in a.nhom.split(",") if x.strip()}
        for c in bo_cau_hoi.CAU_HOI:
            if nhom and c[0][0] not in nhom:
                continue
            viec.append(("KB", c[0], "vi", c[3], c[2], c[6]))
    if a.goi_y or not a.nhom:
        for ng, ds in GOI_Y_MAN_HINH.items():
            for i, cau in enumerate(ds):
                viec.append(("MH", "G%d" % (i + 1), ng, cau, "", "Gợi ý trên màn hình"))

    ket_qua = []
    cache_tra_loi = {}                          # mã câu đã hỏi (vi) → (câu, ket) để làm lịch sử cho câu tiếp
    tong = len(viec)
    for so, (nhan, ma, ng, cau, mong_doi, can_thay) in enumerate(viec, 1):
        lich_su = []
        cau_thuc = bo_ngoac(cau)
        if ma in DOI_NGON_NGU:
            ma_goc, ng = DOI_NGON_NGU[ma]
            goc = bang[ma_goc]
            cau_thuc = goc[4] if ng == "en" else goc[5]
        elif ma in CAU_TRUOC:
            # dựng lịch sử: hỏi (hoặc lấy lại) chuỗi câu trước
            chuoi, m = [], ma
            while m in CAU_TRUOC:
                m = CAU_TRUOC[m]
                chuoi.insert(0, m)
            for m in chuoi:
                if m not in cache_tra_loi:
                    cau0 = bo_ngoac(bang[m][3])
                    k0, _, _ = hoi(cau0, list(lich_su), "vi")
                    cache_tra_loi[m] = (cau0, k0)
                    time.sleep(a.nghi)
                cau0, k0 = cache_tra_loi[m]
                lich_su.append({"vai": "user", "noi_dung": cau0})
                lich_su.append({"vai": "model", "noi_dung": k0.get("tra_loi") or k0.get("loi") or "",
                                "ngu_canh": k0.get("ngu_canh") or ""})

        try:
            ket, goi, giay = hoi(cau_thuc, lich_su, ng)
        except Exception as loi:                        # noqa: BLE001 — muốn thấy MỌI lỗi, không dừng cả bộ
            ket, goi, giay = {"loi": "%s: %s" % (type(loi).__name__, loi)}, [], 0.0
        if nhan == "KB" and ng == "vi" and ma not in cache_tra_loi and "loi" not in ket:
            cache_tra_loi[ma] = (cau_thuc, ket)

        tra_loi = (ket.get("tra_loi") or "").strip()
        loi = ket.get("loi")
        # Đánh giá tự động — chỉ những gì máy đo được; phần "cần thấy gì" vẫn do người đọc soát.
        danh_gia = []
        if loi:
            danh_gia.append("LỖI")
        elif not tra_loi:
            danh_gia.append("RỖNG")
        if ma.startswith("K") and ma != "K6":
            if goi:
                danh_gia.append("GỌI CÔNG CỤ DÙ PHẢI TỪ CHỐI: " + ",".join(goi))
            if not any(t in tra_loi.lower() for t in TU_TU_CHOI):
                danh_gia.append("KHÔNG THẤY LỜI TỪ CHỐI")
        if mong_doi and not mong_doi.startswith("(") and not loi:
            can = [x.strip() for x in mong_doi.split("·")]
            if not any(x in goi for x in can):
                danh_gia.append("không gọi công cụ mong đợi (%s), đã gọi: %s" % (mong_doi, ",".join(goi) or "—"))
        if ng == "lo" and not loi and not any("຀" <= ch <= "໿" for ch in tra_loi):
            danh_gia.append("TRẢ LỜI KHÔNG CÓ CHỮ LÀO")
        if ng == "en" and not loi and any("຀" <= ch <= "໿" for ch in tra_loi):
            danh_gia.append("TIẾNG ANH LẪN CHỮ LÀO")

        trang_thai = "OK" if not danh_gia else " · ".join(danh_gia)
        in_ngay("[%2d/%d] %-3s %-2s %5.1fs  %-28s %s" % (
            so, tong, ma, ng, giay, ",".join(goi)[:28] or "—", trang_thai[:90]))
        ket_qua.append((nhan, ma, ng, cau_thuc, goi, giay, trang_thai,
                        tra_loi if not loi else str(loi), can_thay))
        time.sleep(a.nghi)

    # ---- ghi báo cáo
    duong = os.path.join(GOC, "kiem", "ket_qua_bo_cau_hoi.md")
    so_ok = sum(1 for r in ket_qua if r[6] == "OK")
    with io.open(duong, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Kết quả bắn bộ câu hỏi lên tác tử thật\n\n")
        f.write("Chạy lúc %s · API EPL %s · mô hình %s · %d/%d câu OK theo máy đo\n\n"
                % (time.strftime("%d/%m/%Y %H:%M"), cong_cu.GOC_API, tac_tu.MO_HINH, so_ok, len(ket_qua)))
        f.write("| # | Mã | NN | Câu | Công cụ đã gọi | Giây | Máy đo |\n|---|---|---|---|---|---:|---|\n")
        for i, r in enumerate(ket_qua, 1):
            f.write("| %d | %s | %s | %s | %s | %.1f | %s |\n" % (
                i, r[1], r[2], r[3].replace("|", "/"), ", ".join(r[4]) or "—", r[5], r[6]))
        f.write("\n## Câu trả lời đầy đủ\n")
        for i, r in enumerate(ket_qua, 1):
            f.write("\n### %d. %s [%s] — %s\n\n" % (i, r[1], r[2], r[3]))
            f.write("*Cần thấy:* %s\n\n*Máy đo:* %s\n\n" % (r[8], r[6]))
            f.write(r[7].strip() + "\n")
    in_ngay("\nXong: %d/%d câu OK theo máy đo. Báo cáo: %s" % (so_ok, len(ket_qua), duong))


if __name__ == "__main__":
    main()

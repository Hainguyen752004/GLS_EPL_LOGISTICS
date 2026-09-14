# -*- coding: utf-8 -*-
"""Tác tử: vòng lặp Gemini 2.5 Flash gọi công cụ cho tới khi có câu trả lời — có STREAM.

Không có kịch bản cứng. Mô hình đọc mô tả các công cụ trong `cong_cu.py`, tự chọn cần đọc
gì, đọc xong mới trả lời. Một câu hỏi có thể kéo nhiều vòng: "hôm nay có gì gấp" → tổng
quan → thấy 2 lệnh quá hạn → gọi theo dõi từng lệnh → trả lời. Tối đa `VONG_TOI_DA` vòng
để một mô hình lạc đường không quay mãi.

Ba việc làm cho nhanh (đo ngày 12/09: một vòng Gemini ~1,3 s, một câu 2–3 vòng, API EPL
chỉ 0,2–1 s — nên thời gian nằm ở Gemini, không ở EPL):
  · Dùng `streamGenerateContent`: chữ trả lời chảy về trình duyệt ngay khi mô hình bắt đầu
    viết, và từng công cụ được báo ngay khi gọi — người đọc thấy việc đang chạy thay vì
    nhìn ba dấu chấm 6 giây.
  · Mô hình gọi nhiều công cụ trong một vòng thì chạy SONG SONG, không xếp hàng.
  · Giữ một kết nối HTTPS tới Gemini cho mỗi luồng, khỏi bắt tay TLS lại mỗi vòng.

Trí nhớ: ngoài lời hỏi-đáp, mỗi lượt trả về `ngu_canh` — bản rút gọn của dữ liệu đã tra.
Trình duyệt gửi lại nó ở lượt sau, nên hỏi tiếp "cái đó giá bao nhiêu" là mô hình có sẵn
số, không phải tra lại và không lạc sang bản ghi khác.

Khóa Gemini chỉ nằm ở đây, phía máy chủ. Trình duyệt không bao giờ thấy nó.
"""
import datetime as dt
import http.client
import json
import os
import ssl
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import cong_cu

MO_HINH = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
# 0 là nhanh nhất nhưng đã đo thấy mô hình đoán tên khách thay vì gọi công cụ; 256 thêm ~0,2 s
# mỗi vòng và bớt hồ đồ. Đổi bằng biến môi trường GEMINI_THINKING nếu cần.
NGAN_SACH_SUY_NGHI = int(os.getenv("GEMINI_THINKING", "256"))
VONG_TOI_DA = 8
KHOA = ""
MAY_CHU_GEMINI = "generativelanguage.googleapis.com"
_noi = threading.local()


def cau_hinh(khoa, mo_hinh=None):
    global KHOA, MO_HINH
    KHOA = khoa or ""
    if mo_hinh:
        MO_HINH = mo_hinh


TEN_NGON_NGU = {"vi": "tiếng Việt", "en": "English", "lo": "ພາສາລາວ (Lao)"}

LOI_DAN = """Bạn là trợ lý vận hành của EPL Logistics — hệ thống quản lý vận tải (TMS) chạy ở Việt Nam và Lào.
Người hỏi là người quản lý: điều độ, kinh doanh, giám đốc. Họ cần con số đúng và câu trả lời ngắn.

BẮT BUỘC:
1. Mọi con số, mã lệnh, tên khách, trạng thái đều phải lấy từ công cụ hoặc từ khối [DỮ LIỆU HỆ THỐNG ĐÃ TRA TRONG
   HỘI THOẠI] kèm theo câu hỏi. KHÔNG bịa, KHÔNG suy diễn từ trí nhớ chung. Công cụ trả rỗng thì nói rõ "không có".
   Câu hỏi nối tiếp ("cái đó", "xe ấy", "khách này") thì đọc khối dữ liệu đó trước. Nếu khối đó KHÔNG có đúng
   trường đang được hỏi (ví dụ có mã lệnh nhưng không có tên khách, có xe nhưng không có tài xế) thì BẮT BUỘC gọi
   công cụ để lấy — tuyệt đối không điền tên khách, tên tài xế, biển số, giá tiền từ trí nhớ hay từ chỗ khác.
   Một tên công ty hay một con số không có trong dữ liệu công cụ là một lời nói dối với người quản lý.
   Khối dữ liệu đó là TRÍCH ĐOẠN đã cắt gọn (mỗi nhóm chỉ vài mục đầu). Câu hỏi ĐẾM hay TỔNG HỢP ("bao nhiêu",
   "tổng cộng", "tất cả", "danh sách đầy đủ") thì BẮT BUỘC gọi công cụ với bộ lọc phù hợp, không đếm trên trích đoạn.
   Cần tra thì CỨ GỌI CÔNG CỤ NGAY rồi trả lời — không hỏi xin phép, không hỏi "anh/chị có muốn em tra không".
   Câu hỏi nhắc tới một MÃ CỤ THỂ (DO-…, QT-…, TRIP-…, CLOSEOUT-…, biển số xe, mã tài xế) hay một TÊN KHÁCH mà
   hội thoại CHƯA CÓ khối [DỮ LIỆU HỆ THỐNG…] nào chứa nó thì BẮT BUỘC gọi công cụ TRƯỚC khi mở miệng. Không có
   khối dữ liệu nghĩa là không có gì để nhớ — trả lời thẳng lúc đó là bịa, dù câu trả lời nghe hợp lý.
   Đại từ nối tiếp ("khách đó", "xe ấy", "lệnh này", "tài xế đó") trỏ về thực thể ĐƯỢC NÊU TÊN TRONG CÂU TRẢ LỜI
   GẦN NHẤT CỦA CHÍNH BẠN ở trên — không phải một mục bất kỳ trong khối dữ liệu. Tra lại theo đúng tên/mã đó.
   Câu trả lời là VĂN XUÔI cho người đọc: KHÔNG BAO GIỜ in lại khối dữ liệu, JSON hay tên hàm ra câu trả lời.
2. Câu hỏi chung ("hôm nay thế nào", "có gì cần lo") → gọi tong_quan_hom_nay trước, rồi đào sâu chỗ có vấn đề.
   Cần nhiều công cụ thì gọi CÙNG LÚC trong một lượt, đừng gọi lần lượt.
3. Tiền: luôn ghi kèm mã tiền tệ CỦA CHÍNH BẢN GHI (trường currency_code): VNĐ, USD, THB, LAK.
   Viết "VNĐ", không viết "đ" hay "₫". Không tự quy đổi. Không thấy currency_code thì nói "chưa rõ tiền tệ".
4. Trả lời NGẮN, đi thẳng vào việc: kết luận trước, chi tiết sau. Dùng gạch đầu dòng hoặc bảng Markdown khi có
   từ 3 dòng dữ liệu. Danh sách dài thì tóm số lượng và nêu 5–10 mục đáng chú ý nhất. Luôn nêu MÃ (DO-…, QT-…,
   biển số) để người đọc tra lại được.
5. Nói ngôn ngữ nghiệp vụ, không lộ tên trường kỹ thuật (không viết canonical_status, do_id…). Dịch trạng thái:
   pending = chờ điều phối · in_transit = đang vận chuyển · delivered = đã giao · split = khách đã chấp nhận,
   đã tách lệnh · sent = đã gửi khách · pending_approval = chờ duyệt nội bộ · available = rảnh · on_trip = đang chạy.
6. Bạn CHỈ ĐỌC. Không tạo, sửa, xoá, điều phối gì được. Nếu được nhờ làm việc đó, nói rõ không làm được ở đây và
   chỉ ĐÚNG màn hình để làm — chỉ sai màn còn tệ hơn không chỉ:
   · Điều phối — gán xe và tài xế, chốt điều phối, xuất bến.
   · Lệnh giao hàng — xem lệnh, sửa khung giờ lấy/giao, huỷ hoặc xoá lệnh, lập chuyến.
   · Báo giá — lập, sửa, gửi khách, duyệt nội bộ, ghi khách chấp nhận hoặc từ chối.
   · Khách hàng và cơ hội — thêm cơ hội, đổi giai đoạn, ghi lý do mất.
   · Hoàn tất giao hàng — ký nhận POD, thêm phụ phí, chốt giá, ghi sổ kinh doanh.
   · Theo dõi — báo sự cố, cập nhật GPS và mốc.
   · Dữ liệu gốc — xe, tài xế, bằng lái, lịch ca, tuyến, công thức giá thành, tỷ giá, khách hàng.
7. Mô hình ba tầng: Báo giá (QT) là thoả thuận giá → khách chấp nhận sinh Lệnh giao hàng (DO) → Chuyến (Trip) là
   xe thật chở DO. Một chuyến có thể chở nhiều DO. Không có cách tạo DO bằng tay.
8. Khi công cụ trả về lỗi (trường "loi"), nói lại nguyên nhân bằng lời thường, không kèm mã kỹ thuật thô,
   không nhắc tới "giới hạn dòng", "page size", "API" hay tên công cụ.
9. Tỉ lệ (biên lợi nhuận, tỉ lệ chốt, tiến độ) viết dạng phần trăm có một chữ số lẻ: 0.34 → 34%, 0.913 → 91,3%.
   Ngày giờ viết theo kiểu người đọc: 12/09/2026 16:59, không để nguyên chuỗi ISO có chữ T và múi giờ.
10. Xưng hô: tiếng Việt thì tự xưng "em", gọi người hỏi là "anh/chị" (ví dụ "Em thấy có 5 sự cố đang mở, anh/chị
   lưu ý…"). Không xưng "tôi". Tiếng Anh và tiếng Lào dùng cách xưng hô lịch sự thông thường.

Hôm nay: {hom_nay} (giờ Việt Nam, UTC+7). Dùng mốc này để tính "hôm nay", "tuần này", "sắp hết hạn".

NGÔN NGỮ TRẢ LỜI: {ngon_ngu}. Toàn bộ câu trả lời phải bằng ngôn ngữ đó, kể cả tiêu đề bảng và nhãn.
Mã bản ghi (DO-2026-…, QT-…, biển số xe) và mã tiền tệ giữ nguyên. Tên riêng người và công ty giữ nguyên.
{cach_viet_so}
"""

CACH_VIET_SO = {
    "vi": "Cách viết số tiền trong tiếng Việt: 1.406.000 VNĐ · 1.728.118 LAK · 2.500 USD (chấm ngăn nghìn, mã tiền sau số).",
    "en": "Number format in English: 1,406,000 VND · 1,728,118 LAK · 2,500 USD (comma thousands separator, write VND not VNĐ).",
    "lo": "ຮູບແບບຕົວເລກໃນພາສາລາວ: 1.406.000 VNĐ · 1.728.118 LAK · 2.500 USD (ຈຸດແຍກຫຼັກພັນ, ລະຫັດເງິນຕາຫຼັງຕົວເລກ).",
}


class LoiGemini(Exception):
    pass


# ------------------------------------------------------------------ kết nối giữ lâu
def _boi_canh_ssl():
    """Bối cảnh TLS dựng từ bộ chứng chỉ của `certifi`, KHÔNG từ kho chứng chỉ Windows.

    VÌ SAO. `ssl.create_default_context()` trên Windows đi nạp toàn bộ kho chứng chỉ của
    hệ điều hành. Chỉ cần MỘT chứng chỉ trong kho đó hỏng là cả lời gọi bật lỗi

        ssl.SSLError: [ASN1: NOT_ENOUGH_DATA] not enough data (_ssl.c:4192)

    và mọi câu hỏi gửi lên Gemini chết ngay ở bước dựng kết nối, trước khi ra tới mạng.
    Đo được ngày 13/09/2026: cùng một máy, môi trường `vungcam_2026` bật lỗi này còn môi
    trường gốc thì không — nên nó phụ thuộc phiên bản OpenSSL đi kèm từng môi trường, chứ
    không phải lỗi của mã này. Người dùng không có cách nào tự đoán ra.

    `certifi` là bộ chứng chỉ gốc của Mozilla, đi kèm sẵn, không dính gì tới kho Windows —
    dùng nó thì môi trường nào cũng chạy. Đây KHÔNG phải tắt kiểm chứng chỉ: vẫn kiểm đủ
    tên miền và chuỗi tin cậy, chỉ đổi nguồn danh sách gốc.
    """
    boi_canh = getattr(_noi, "ssl_ctx", None)
    if boi_canh is None:
        try:
            import certifi
            boi_canh = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            # Không có certifi thì quay về kho hệ điều hành — máy nào lành vẫn chạy được.
            boi_canh = ssl.create_default_context()
        _noi.ssl_ctx = boi_canh
    return boi_canh


def _ket_noi(lam_moi=False):
    kn = getattr(_noi, "kn", None)
    if kn is None or lam_moi:
        if kn is not None:
            try:
                kn.close()
            except Exception:
                pass
        kn = http.client.HTTPSConnection(MAY_CHU_GEMINI, timeout=90,
                                         context=_boi_canh_ssl())
        _noi.kn = kn
    return kn


def _goi_gemini_stream(than, nhan_chu=None):
    """Gọi `streamGenerateContent` (SSE). Trả danh sách `parts` đã gom của lượt trả lời;
    mỗi mẩu chữ đến được đẩy ngay qua `nhan_chu(chu)`.

    Thử lại hai lần khi bị giới hạn tần suất hoặc Google lỗi tạm — chỉ khi CHƯA nhận được
    gì; đã nhận nửa câu mà nối lại là chữ bị lặp."""
    if not KHOA:
        raise LoiGemini("Chưa cấu hình GEMINI_API_KEY_GT.")
    duong = "/v1beta/models/%s:streamGenerateContent?alt=sse&key=%s" % (MO_HINH, KHOA)
    du_lieu = json.dumps(than).encode("utf-8")
    cho = 1.5
    for lan in range(3):
        kn = _ket_noi(lam_moi=lan > 0)
        try:
            kn.request("POST", duong, body=du_lieu, headers={"Content-Type": "application/json",
                                                            "Accept": "text/event-stream"})
            tra = kn.getresponse()
        except (http.client.HTTPException, OSError) as loi:
            if lan < 2:
                time.sleep(cho)
                cho *= 2
                continue
            raise LoiGemini("Không gọi được Gemini: %s" % loi)
        if tra.status != 200:
            than_loi = tra.read().decode("utf-8", "replace")[:600]
            if tra.status in (429, 500, 502, 503, 504) and lan < 2:
                time.sleep(cho)
                cho *= 2
                continue
            raise LoiGemini("Gemini trả %s: %s" % (tra.status, than_loi))
        return _doc_sse(tra, nhan_chu)
    raise LoiGemini("Gemini không phản hồi.")


def _doc_sse(tra, nhan_chu):
    """Gom các mẩu SSE thành một danh sách parts: chữ nối lại, functionCall giữ nguyên."""
    phan, chu_dang_gom, ly_do = [], [], None
    for dong in tra:
        dong = dong.decode("utf-8", "replace").strip()
        if not dong.startswith("data:"):
            continue
        goi = dong[5:].strip()
        if not goi or goi == "[DONE]":
            continue
        try:
            manh = json.loads(goi)
        except ValueError:
            continue
        ung = (manh.get("candidates") or [{}])[0]
        ly_do = ung.get("finishReason") or ly_do or (manh.get("promptFeedback") or {}).get("blockReason")
        for p in (ung.get("content") or {}).get("parts") or []:
            if p.get("thought"):
                continue
            if "functionCall" in p:
                phan.append(p)
            elif p.get("text"):
                chu_dang_gom.append(p["text"])
                if nhan_chu:
                    nhan_chu(p["text"])
    if chu_dang_gom:
        phan.insert(0, {"text": "".join(chu_dang_gom)})
    if not phan and ly_do:
        phan.append({"_ly_do": ly_do})
    return phan


# ------------------------------------------------------------------ lịch sử và ngữ cảnh
NHAN_NGU_CANH = "[DỮ LIỆU HỆ THỐNG ĐÃ TRA TRONG HỘI THOẠI"


def _noi_dung_tu_lich_su(lich_su):
    """Lịch sử từ trình duyệt: [{vai, noi_dung, ngu_canh?}] → (contents của Gemini, ngữ cảnh
    gần nhất).

    `ngu_canh` là dữ liệu đã tra ở lượt đó (rút gọn). KHÔNG gắn nó vào lượt của mô hình:
    đã đo (12/09) mô hình bắt chước — kết câu trả lời bằng một khối dữ liệu tự chế, có tên
    tài xế và giá tiền không tồn tại. Thay vào đó trả ngữ cảnh gần nhất ra ngoài để
    `tra_loi` đưa vào lượt NGƯỜI DÙNG hiện tại như một ghi chú hệ thống."""
    ra, ngu_canh = [], ""
    # Khối dữ liệu gắn vào LƯỢT HỎI đã sinh ra nó (câu hỏi "hôm nay thế nào" → dữ liệu tổng
    # quan), KHÔNG gắn cạnh câu hỏi hiện tại. Đã đo (12/09): đặt khối ngay trước câu hỏi mới
    # thì "khách đó" bị hút về cái tên gần nhất trong khối thay vì câu trả lời ngay phía trên.
    # Chỉ hai khối gần nhất, và không lặp: nhiều lượt không tra gì cùng mang một khối.
    mo_hinh_co_ngu_canh = [i for i, m in enumerate(lich_su or [])
                           if m.get("vai") in ("model", "assistant", "tro_ly") and m.get("ngu_canh")]
    da_gan = set()
    for i, m in enumerate(lich_su or []):
        vai = "model" if m.get("vai") in ("model", "assistant", "tro_ly") else "user"
        chu = (m.get("noi_dung") or "").strip()
        if vai == "model" and m.get("ngu_canh"):
            ngu_canh = str(m["ngu_canh"])
            khoi = ngu_canh[:6000]
            if i in mo_hinh_co_ngu_canh[-2:] and khoi not in da_gan and ra and ra[-1]["role"] == "user":
                da_gan.add(khoi)
                ra[-1]["parts"].append({"text": "%s cho câu hỏi trên — TRÍCH ĐOẠN đã cắt gọn; KHÔNG in lại "
                                                "khối này, KHÔNG bịa thêm trường nào]\n%s" % (NHAN_NGU_CANH, khoi)})
        if not chu:
            continue
        if ra and ra[-1]["role"] == vai:            # Gemini đòi xen kẽ user/model
            ra[-1]["parts"][0]["text"] += "\n\n" + chu
        else:
            ra.append({"role": vai, "parts": [{"text": chu}]})
    return ra, ngu_canh[:6000]


def _cat_khoi_du_lieu(chu):
    """Phòng hờ: mô hình vẫn in một khối dữ liệu thô ở cuối thì cắt bỏ, không cho ra màn."""
    for moc in (NHAN_NGU_CANH, "[DỮ LIỆU ĐÃ TRA]", "[DỮ LIỆU"):
        i = chu.find(moc)
        if i > 0:
            return chu[:i].rstrip()
    return chu


def _gon_cho_mo_hinh(ket_qua, toi_da=14000):
    """Kết quả công cụ đưa vào functionResponse; chặn cứng kích thước để không vượt ngữ cảnh."""
    chu = json.dumps(ket_qua, ensure_ascii=False, default=str)
    if len(chu) <= toi_da:
        return ket_qua
    return {"ghi_chu": "Kết quả quá dài, đã cắt còn %d ký tự — hãy lọc hẹp hơn (tim/trang_thai/gioi_han)."
                       % toi_da, "mot_phan": chu[:toi_da]}


def _ngu_canh(ket_qua_cac_cong_cu, toi_da=6000):
    """Rút gọn toàn bộ dữ liệu đã tra trong lượt này thành một chuỗi để lượt sau dùng lại."""
    chu = json.dumps(ket_qua_cac_cong_cu, ensure_ascii=False, default=str, separators=(",", ":"))
    return chu if len(chu) <= toi_da else chu[:toi_da] + "…"


# ------------------------------------------------------------------ vòng lặp
def tra_loi(cau_hoi, lich_su=None, ngon_ngu="vi", ghi_log=None, phat=None):
    """Chạy tác tử. `phat(su_kien, du_lieu)` nếu có sẽ nhận stream:
         ("cong_cu", {ten, nhan, doi_so})      — vừa bắt đầu gọi
         ("cong_cu_xong", {ten, giay, loi})    — vừa xong
         ("chu", "…")                          — một mẩu chữ trả lời
    Trả `{tra_loi, cong_cu_da_dung, so_vong, mo_hinh, ngu_canh}` hoặc `{loi}`."""
    ngon_ngu = ngon_ngu if ngon_ngu in TEN_NGON_NGU else "vi"
    phat = phat or (lambda *_: None)
    hom_nay = dt.datetime.now(cong_cu.VN).strftime("%A %d/%m/%Y %H:%M")
    loi_dan = LOI_DAN.format(hom_nay=hom_nay, ngon_ngu=TEN_NGON_NGU[ngon_ngu],
                             cach_viet_so=CACH_VIET_SO[ngon_ngu])
    noi_dung, ngu_canh_truoc = _noi_dung_tu_lich_su(lich_su)
    noi_dung.append({"role": "user", "parts": [{"text": cau_hoi}]})
    than = {
        "systemInstruction": {"parts": [{"text": loi_dan}]},
        "contents": noi_dung,
        "tools": [{"functionDeclarations": cong_cu.khai_bao_gemini()}],
        "toolConfig": {"functionCallingConfig": {"mode": "AUTO"}},
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4096,
                             "thinkingConfig": {"thinkingBudget": NGAN_SACH_SUY_NGHI}},
    }
    da_dung, du_lieu_da_tra = [], {}
    for vong in range(1, VONG_TOI_DA + 1):
        chu_stream = []

        def nhan_chu(mau):
            # Phát NGAY từng mẩu chữ — đó là toàn bộ cái lợi của stream. Vòng vừa có chữ
            # vừa có gọi hàm rất hiếm; gặp thì phát `chu_xoa` để trình duyệt bỏ chữ tạm.
            chu_stream.append(mau)
            phat("chu_them", mau)

        try:
            phan = _goi_gemini_stream(than, nhan_chu)
        except LoiGemini as loi:
            return {"loi": str(loi), "cong_cu_da_dung": da_dung, "so_vong": vong}
        goi_ham = [p["functionCall"] for p in phan if "functionCall" in p]
        if not goi_ham:
            chu = _cat_khoi_du_lieu("".join(chu_stream).strip())
            if not chu:
                ly_do = next((p["_ly_do"] for p in phan if "_ly_do" in p), "không rõ")
                return {"loi": "Mô hình không trả lời (%s)." % ly_do, "cong_cu_da_dung": da_dung, "so_vong": vong}
            # Lượt này không tra gì (trả lời từ ngữ cảnh) thì giữ ngữ cảnh cũ cho lượt sau.
            return {"tra_loi": chu, "cong_cu_da_dung": da_dung, "so_vong": vong, "mo_hinh": MO_HINH,
                    "ngu_canh": _ngu_canh(du_lieu_da_tra) if du_lieu_da_tra else ngu_canh_truoc}
        if chu_stream:
            phat("chu_xoa", "")

        than["contents"].append({"role": "model", "parts": [p for p in phan if "_ly_do" not in p]})
        for g in goi_ham:
            phat("cong_cu", {"ten": g.get("name"), "doi_so": g.get("args") or {},
                             "nhan": cong_cu.NHAN.get(g.get("name"), {}).get(ngon_ngu, g.get("name"))})

        def chay_mot(g):
            ten, doi_so = g.get("name"), g.get("args") or {}
            bat_dau = time.time()
            ket = cong_cu.chay_cong_cu(ten, doi_so)
            return ten, doi_so, ket, time.time() - bat_dau

        # Nhiều công cụ một vòng → chạy song song; thứ tự phản hồi giữ theo thứ tự gọi.
        if len(goi_ham) > 1:
            with ThreadPoolExecutor(max_workers=min(6, len(goi_ham))) as bo:
                ket_qua = list(bo.map(chay_mot, goi_ham))
        else:
            ket_qua = [chay_mot(goi_ham[0])]

        phan_hoi = []
        for ten, doi_so, ket, mat in ket_qua:
            loi = ket.get("loi") if isinstance(ket, dict) else None
            da_dung.append({"ten": ten, "doi_so": doi_so, "giay": round(mat, 2), "loi": loi,
                            "nhan": cong_cu.NHAN.get(ten, {}).get(ngon_ngu, ten)})
            phat("cong_cu_xong", {"ten": ten, "giay": round(mat, 2), "loi": loi})
            if ghi_log:
                ghi_log("  [%d] %s(%s) %.1fs%s" % (vong, ten, json.dumps(doi_so, ensure_ascii=False),
                                                   mat, " LOI" if loi else ""))
            if not loi:
                du_lieu_da_tra["%s(%s)" % (ten, json.dumps(doi_so, ensure_ascii=False))] = ket
            phan_hoi.append({"functionResponse": {"name": ten, "response": _gon_cho_mo_hinh(ket)}})
        than["contents"].append({"role": "user", "parts": phan_hoi})

    return {"loi": "Đã hỏi dữ liệu %d vòng mà chưa chốt được câu trả lời — hãy hỏi hẹp hơn." % VONG_TOI_DA,
            "cong_cu_da_dung": da_dung, "so_vong": VONG_TOI_DA}

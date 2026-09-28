/* Quy trình & trách nhiệm — mỗi công đoạn ai làm, làm gì, máy chặn gì, IN RA PHIẾU gì, SINH CHỨNG TỪ gì.
 *
 * Hai phần dữ liệu:
 *   · Viết tay ở đây (CHUYEN, NGOAI): công đoạn, người làm, màn, việc làm, máy tự làm, máy chặn. Soạn theo đúng
 *     mã đang chạy ngày 23/09/2026 (câu trả lời của anh Khampla) — sửa luồng thì sửa ở đây.
 *   · Lấy từ máy chủ (/api/quy-trinh): ma trận quyền, vai nào thấy / nhập tiền, và ĐỊNH KHOẢN từng loại chứng từ
 *     tính bằng chính hàm ghi sổ — nên Nợ / Có trên màn không bao giờ lệch với cái máy thật sự ghi.
 */
(function () {
  const { API, NN, esc } = EPL;
  let root, D = null, xem = 'chuyen';
  const q = (s) => root.querySelector(s);

  /* ================================================================ một chuyến, theo giai đoạn */
  // vai: mã vai · man: id màn · lam: người làm gì · may: máy tự làm · chan: máy chặn · giay: phiếu in / tờ giấy
  // ct: mã chứng từ sinh ra (định khoản lấy từ máy chủ) · ct_khi: ghi chú lúc nào sinh · sau: trạng thái sau bước
  const CHUYEN = [
    { gd: 'Lập phiếu tại bãi Thà Bốc', buoc: [
      { so: 1, vai: ['yard'], man: 'phieu-xuat-xe', ten: 'Mở phiếu xuất xe — mục I (xe) và mục II (chuyến)',
        lam: ['Chọn loại phiếu: GIAO (chở tới cảng / khách) hay GOM (mỏ → bãi)', 'Chọn xe — xe của chủ xe liên kết thì phiếu tự thành phiếu xe liên kết',
          'Chọn tài xế, khách hàng, tuyến; ngày lập, ngày đi; km lúc đi', 'Cân đầu (tấn) theo phiếu quặng của khách',
          'Phiếu giao lấy hàng ở bãi: chọn lô (phiếu gom) và số tấn lấy'],
        may: ['Số phiếu gợi ý: T4-xxxx-MM/EPL (giao) · G4-xxxx-MM/EPL (gom)', 'Điểm đi / đến theo tuyến; km về ước tính = km đi + km tuyến',
          'Giá cước điền theo bảng giá khách × tuyến; phí 2 %, ngưỡng tấn theo hồ sơ chủ xe — Bãi KHÔNG thấy', 'Tỷ giá USD · THB · VND · CNY khoá vào phiếu lúc lập'],
        chan: ['Bãi không nhập được giá cước, giá thuê, phí, ngưỡng tấn (A2 · C4.1)', 'Số phiếu quặng: chỉ kế toán nhập (C3.7)', 'Phiếu giao có dòng hàng mà không chỉ rõ lô → chặn',
          'Lấy quá số tấn còn trong lô → chặn'],
        giay: ['Phiếu xuất xe (in từ nút In)'], ct: ['DO'], ct_khi: { DO: 'sinh ngay lúc lập phiếu' }, sau: 'Phiếu: Đã xuất xe · mục I, II: Chờ' },
      { so: 2, vai: ['yard'], man: 'phieu-xuat-xe', ten: 'Mục III — nhiên liệu: số lít và nơi đổ',
        lam: ['Mỗi dòng: số lít + nơi đổ', 'Xe liên kết: chọn EPL ứng hay chủ xe tự trả', 'Đổ ở trạm Việt Nam mà trạm ghi nợ: đánh dấu "ghi nợ tại trạm"'],
        may: ['Nơi đổ là KHO của EPL → nguồn kho, giá = giá BÌNH QUÂN của đúng kho đó (C5.3), không ai gõ', 'Nơi đổ là trạm ngoài → nguồn mua, gắn nhà cung cấp của trạm',
          'Định khoản gợi ý: 625/1371 (kho) · 625/4021 (mua) · 4022/… (xe liên kết)'],
        chan: ['Bãi không thấy và không nhập đơn giá dầu, thành tiền, mã tài khoản'],
        giay: ['Phiếu lĩnh nhiên liệu có mã QR — mỗi kho một tờ, tài xế cầm tới kho'], ct: ['PLNL'], ct_khi: { PLNL: 'khi bấm "Phiếu lĩnh nhiên liệu"' }, sau: 'Phiếu lĩnh: Chờ cấp' },
      { so: 3, vai: ['yard'], man: 'phieu-xuat-xe', ten: 'Mục IV — đi đường, mục VI — chi khác',
        lam: ['Khoản mục + số lượng: tiền ăn, tiền nước, chi phí sang Việt Nam, điện thoại, chipping…', 'Phí cao tốc: chọn trả tiền mặt hay trừ THẺ cao tốc'],
        may: ['Tuyến có BOT thì tự thêm dòng phí cao tốc, giá theo tuyến', 'Gom mọi khoản tiền mặt EPL ứng (IV, VI, dầu mua ngoài) thành số tạm ứng'],
        chan: ['Bãi không nhập đơn giá — người kiểm mục nhập ở công đoạn 6'],
        giay: ['Phiếu tạm ứng đi đường có mã QR — tài xế cầm tới quỹ'], ct: ['PTU'], ct_khi: { PTU: 'khi bấm "Phiếu chi tạm ứng"' }, sau: 'Mục IV: Chờ' },
      { so: 4, vai: ['yard'], man: 'phieu-xuat-xe', ten: 'Gửi kiểm từng mục',
        lam: ['Bấm "Gửi kiểm" ở mục I, II, III, IV, VI (mục V là của tổ sửa chữa)'],
        may: ['Mục chuyển "Đã nhập" — Bãi vẫn sửa được tới khi kế toán kiểm'], chan: ['Mục trống không gửi được'], sau: 'Các mục: Đã nhập · chờ kiểm' },
    ] },
    { gd: 'Viêng Chăn kiểm và nhập giá', buoc: [
      { so: 5, vai: ['acct'], man: 'phieu-xuat-xe', ten: 'KT Thu/Chi VC — kiểm mục I, II',
        lam: ['Đối chiếu xe, tài xế, cân đầu với phiếu quặng', 'Nhập SỐ PHIẾU QUẶNG + ngày (gõ tay được, không bắt ảnh)', 'Sửa giá cước nếu khác hợp đồng; nhập giá thuê xe liên kết, phí, ngưỡng tấn',
          'Bấm Kiểm (hoặc Trả lại cho Bãi)'],
        chan: ['Mục đã kiểm là khoá — muốn sửa phải Trả lại', 'KT Thu/Chi không kiểm mục III–VI'], sau: 'Mục I, II: Đã kiểm' },
      { so: 6, vai: ['fuel', 'expacct'], man: 'phieu-xuat-xe', ten: 'Người kiểm mục nhập đơn giá rồi kiểm · ghi sổ',
        lam: ['KT kho xăng dầu: nhập đơn giá dầu MUA NGOÀI (VND, tỷ giá trên phiếu) → Kiểm → Ghi sổ mục III',
          'KT Chi phí: nhập đơn giá mục IV, VI → Kiểm → Ghi sổ', 'Bấm Kiểm là máy lưu giá trước rồi mới kiểm'],
        may: ['Ghi sổ mục III: dòng dầu KHO chưa cấp theo phiếu lĩnh thì xuất kho luôn, theo giá bình quân lúc xuất', 'Ghi sổ mục IV: dòng trả bằng thẻ cao tốc trừ số dư thẻ đúng một lần'],
        chan: ['Dòng EPL trả mà đơn giá 0 → không kiểm được (THIEU_DON_GIA)', 'Kế toán chỉ nhập giá, không thêm / xoá dòng (CHI_SUA_GIA)', 'Dòng lấy từ kho: giá là bình quân, gõ tay bị bỏ qua'],
        ct: ['PXK_NL'], ct_khi: { PXK_NL: 'lúc ghi sổ mục III — với dòng dầu kho chưa cấp theo phiếu lĩnh' }, sau: 'Mục III, IV, VI: Đã ghi sổ · chờ chi' },
    ] },
    { gd: 'Cấp dầu và tạm ứng', buoc: [
      { so: 7, vai: ['depot'], man: 'cap-phat', o_ke_toan: true, ten: 'Thủ kho quét QR phiếu lĩnh, cấp dầu',
        lam: ['Quét mã, đối chiếu đúng xe, đúng tài xế', 'Nhập số lít cấp thật → Cấp'],
        may: ['Trừ tồn đúng kho ngay; dòng dầu trên phiếu mang giá bình quân của kho lúc cấp', 'Mất mạng vẫn cấp được, máy gửi lại khi có mạng'],
        chan: ['Thủ kho kho khác không cấp được', 'Cấp lệch số duyệt mà không ghi lý do → chặn', 'Cấp hai lần → chặn'],
        ct: ['PXK_NL'], ct_khi: { PXK_NL: 'lúc cấp — mỗi dòng dầu kho chỉ xuất một lần (hoặc ở đây, hoặc lúc ghi sổ mục III)' }, sau: 'Phiếu lĩnh: Đã cấp' },
      { so: 8, vai: ['cash'], man: 'cap-phat', o_ke_toan: true, ten: 'Quỹ tiền mặt cảng cạn chi tạm ứng',
        lam: ['Quét QR phiếu tạm ứng rồi Chi tiền — hoặc bấm Chi mục IV trên phiếu'],
        may: ['Hai đường chi tự loại nhau: đã chi đường này thì đường kia là sai bước, không ra hai tờ', 'Dòng trả bằng thẻ cao tốc không tính vào tiền mặt'],
        chan: ['Mục IV chưa ghi sổ → không chi được', 'Tài xế tự chi cho mình → chặn'],
        giay: ['Tài xế ký nhận tiền trên phiếu tạm ứng'], ct: ['PC_TU'], ct_khi: { PC_TU: 'lúc quỹ chi' }, sau: 'Mục IV: Đã chi' },
    ] },
    { gd: 'Trên đường', buoc: [
      { so: 9, vai: ['driver', 'yard'], man: 'phieu-cua-toi', ten: 'Xuất phát · báo mốc · chia sẻ vị trí',
        lam: ['Tài xế bấm Xuất phát, bật chia sẻ vị trí (GPS)', 'Bãi hoặc tài xế báo tới từng mốc trên tuyến'],
        chan: ['Mục IV chưa "Đã chi" (tài xế chưa cầm tiền) → không xuất phát được (CHUA_NHAN_TAM_UNG)'], sau: 'Đang vận chuyển' },
      { so: 10, vai: ['driver', 'fuel'], man: 'phieu-cua-toi', ten: 'Đổ dầu dọc đường (Việt Nam)',
        lam: ['Tài xế khai SỐ LÍT và trạm (C5.1 — không nhập giá)', 'KT kho xăng dầu (hoặc Bãi) duyệt → thành dòng mục III nguồn mua; KT kho nhập giá khi kiểm'],
        may: ['Trạm ghi nợ: cuối tháng EPL trả trạm hoặc cấn trừ vào cước của khách đứng ra với trạm'], chan: ['Khai đổ ở KHO của EPL → bảo dùng phiếu lĩnh'], sau: 'Mục III mở lại · Đã nhập' },
      { so: 11, vai: ['driver', 'repair'], man: 'theo-doi-tuyen', ten: 'Xe hỏng: báo hỏng → tổ sửa chữa duyệt (mục V)',
        lam: ['Tài xế báo hỏng: hỏng gì, số tiền dự kiến', 'Tổ sửa chữa Thà Bốc duyệt: lấy phụ tùng KHO hay MUA ngoài (gara)'],
        may: ['Lấy kho: trừ tồn phụ tùng ngay, giá bình quân của phụ tùng', 'Mục V tự mở lại "Đã nhập"; hỏng nặng thì xe chuyển "đang sửa"'],
        chan: ['Chỉ tổ sửa chữa duyệt báo hỏng (C1.2)', 'Kho không đủ phụ tùng → chặn'],
        ct: ['PXK_PT'], ct_khi: { PXK_PT: 'khi lấy phụ tùng từ kho' }, sau: 'Mục V: Đã nhập · chờ kiểm' },
      { so: 12, vai: ['yard'], man: 'phieu-xuat-xe', ten: 'Đổi xe giữa đường (xe hỏng nặng — C2.2)',
        lam: ['Bấm "Đổi xe", chọn xe thay'], may: ['Giữ nguyên chuyến, dòng chi, hàng; mục I phải kiểm lại'], chan: ['Phiếu đã tới nơi → không đổi xe'], sau: 'Mục I: Đã nhập · chờ kiểm lại' },
      { so: 13, vai: ['yard', 'driver'], man: 'theo-doi-tuyen', ten: 'Xe tới nơi',
        lam: ['Nhập cân cuối (tấn), km về thật, ngày về'],
        may: ['Phiếu GIAO: tính hao hụt, ghi dòng hao hụt; hàng lấy từ lô được xuất khỏi kho bãi', 'Phiếu GOM: hàng vào kho bãi thành một LÔ chờ phiếu giao lấy'],
        chan: ['Chưa nhận tạm ứng → không báo tới được (như cửa Xuất phát)'],
        ct: ['PXK_HH', 'PNK_HH'], ct_khi: { PXK_HH: 'phiếu giao lấy hàng từ kho bãi', PNK_HH: 'phiếu gom — hàng vào kho bãi' }, sau: 'Đã giao hàng' },
    ] },
    { gd: 'Về tới và khoá phiếu', buoc: [
      { so: 14, vai: ['expacct', 'cash'], man: 'phieu-xuat-xe', ten: 'Mục V, VI: KT Chi phí kiểm · ghi sổ → quỹ chi',
        lam: ['KT Chi phí kiểm, ghi sổ sửa chữa và chi khác', 'Quỹ tiền mặt cảng cạn chi phần MUA ngoài'],
        may: ['Một tờ chi cho cả mục; dòng lấy kho không tính (đã có phiếu xuất kho phụ tùng)'], ct: ['PC_SC'], ct_khi: { PC_SC: 'lúc quỹ chi mục V / VI' }, sau: 'Mục V, VI: Đã chi' },
      { so: 15, vai: ['acct'], man: 'phieu-xuat-xe', ten: 'KT Thu/Chi VC: Kiểm lại toàn phiếu → Khoá',
        lam: ['Bấm "Kiểm lại", đọc bảng cảnh báo, xác nhận khoá', 'Mở khoá nếu cần sửa (khi chưa xuất hoá đơn)'],
        may: ['Rà: km về lệch ước tính > 10 %, hao hụt > 1,5 %, thiếu cân cuối, thiếu km về, thiếu phiếu quặng (không có cả ảnh lẫn số phiếu), mục có chi mà chưa kiểm'],
        chan: ['Còn cảnh báo mà chưa xác nhận → không khoá', 'Khoá rồi Bãi, tài xế không ghi thêm; đã có hoá đơn thì không mở khoá'], sau: 'Phiếu: Đã khoá 🔒' },
    ] },
    { gd: 'Doanh thu', buoc: [
      { so: 16, vai: ['rev'], man: 'hoa-don', ten: 'KT Doanh thu lập hoá đơn vận chuyển',
        lam: ['Khách theo phiếu (không hợp đồng): mỗi phiếu một hoá đơn', 'Khách hợp đồng: gộp các phiếu trong tháng thành một hoá đơn (màn HĐ gộp)'],
        may: ['Tiền = cân (tấn tới hoặc trọn chuyến) × đơn giá, theo tiền tệ của hợp đồng'], chan: ['Phiếu chưa khoá → chưa lập hoá đơn'],
        giay: ['Hoá đơn vận chuyển (in)'], ct: ['HD'], ct_khi: { HD: 'lúc lập hoá đơn (lẻ hoặc gộp tháng)' }, sau: 'Đã xuất hoá đơn · Chưa thanh toán' },
      { so: 17, vai: ['rev'], man: 'hoa-don', ten: 'Ghi thu tiền khách (nhiều lần, nhiều tiền) · cấn trừ cuối tháng',
        lam: ['Ghi từng lần thu: số tiền, tiền tệ, tỷ giá, tiền mặt / chuyển khoản', 'Cuối tháng: ghi cấn trừ phần khách đã trả hộ (thẻ cao tốc của khách, trạm dầu Việt Nam ghi nợ)'],
        may: ['Trạng thái tự suy: chưa thu · thu một phần · đã thu'], chan: ['Thu dư → chặn', 'Lần thu đã đẩy sang sổ kế toán → không xoá được'],
        giay: ['Biên nhận thu tiền'], ct: ['PT'], ct_khi: { PT: 'mỗi lần thu; cấn trừ ghi PT cách thu "cấn trừ"' }, sau: 'Đã thanh toán' },
    ] },
    { gd: 'Xe liên kết và cuối kỳ', buoc: [
      { so: 18, vai: ['cash', 'treasury'], man: 'xe-lien-ket', ten: 'Trả chủ xe liên kết (lẻ · gộp tháng · theo đợt)',
        lam: ['Chọn các phiếu đã khoá của một chủ xe → Trả'],
        may: ['Phải trả = tiền thuê − phí % − trừ vượt tấn − mọi khoản EPL đã ứng (dầu kho, đi đường…) — chủ xe tự trả thì không trừ',
          'TỰ TRỪ tiếp hàng chủ xe mua ở quầy (xăng, phụ tùng) chưa trừ — ví dụ deal 1tr6, mua 3 trăm → trả 1tr3', 'Phiếu chi ghi số THỰC CHI sau khi trừ'],
        chan: ['Phiếu chưa khoá → chưa trả', 'Trả hai lần → chặn', 'Các phiếu khác tiền thuê → tách đợt'],
        giay: ['Chủ xe ký nhận trên phiếu chi'], ct: ['PC_CX'], ct_khi: { PC_CX: 'lúc quỹ trả (một tờ cho cả đợt)' }, sau: 'Chủ xe: Đã trả' },
      { so: 19, vai: ['expacct', 'cash', 'treasury'], man: 'tat-toan', ten: 'Tất toán tài xế theo tháng',
        lam: ['Đối: đã ứng bao nhiêu, chi thật bao nhiêu → Chốt'], may: ['Chi thật > ứng: công ty chi bù · ngược lại: tài xế nộp lại'],
        chan: ['Chốt hai lần một kỳ → chặn'], ct: ['TT_CHI', 'TT_THU'], ct_khi: { TT_CHI: 'khi công ty chi bù', TT_THU: 'khi tài xế nộp lại' }, sau: 'Kỳ: Đã tất toán' },
      { so: 20, vai: ['acct', 'admin'], man: 'chung-tu', ten: 'Đẩy chứng từ sang sổ kế toán',
        lam: ['Bấm "Đẩy tất cả" ở màn Chứng từ'], may: ['Mỗi tờ đẩy đúng một lần; hỏng thì giữ tờ, ghi lỗi lên tờ để đẩy lại'],
        chan: ['Chưa cấu hình địa chỉ sổ kế toán → báo rõ'], sau: 'Tờ: Đã đẩy' },
    ] },
  ];

  /* ================================================================ ngoài chuyến */
  const NGOAI = [
    { gd: 'Kho nhiên liệu (7 kho + kho xe) — giá vốn bình quân', buoc: [
      { so: 'K1', vai: ['fuel', 'acct'], man: 'kho-nhien-lieu', o_ke_toan: true, ten: 'Nhập dầu vào một kho',
        lam: ['Chọn kho, nhà cung cấp, số đơn mua, số lít, đơn giá, tiền tệ, tỷ giá lúc nhập'],
        may: ['Giá nhập quy LAK theo tỷ giá LÚC NHẬP; giá bình quân của kho tính lại'], chan: ['Bãi chỉ xem số lít, không ghi sổ kho, không thấy giá (A2)'],
        giay: ['Phiếu nhập kho'], ct: ['PNK_NL'] },
      { so: 'K2', vai: ['fuel', 'acct'], man: 'kho-nhien-lieu', o_ke_toan: true, ten: 'Mua dầu ở Việt Nam qua KHO XE (A3)',
        lam: ['Nhập 1.000 L vào "Kho xe · dầu mua Việt Nam" (VND)', 'Phiếu xuất xe lấy 600 L với nơi đổ = kho xe', 'Chuyển 400 L còn lại về Thà Bốc hay một kho hiện trường'],
        may: ['Dầu ra khỏi kho xe mang giá bình quân của kho xe'], ct: ['PNK_NL', 'PXK_NL', 'CK_NL'] },
      { so: 'K3', vai: ['fuel', 'acct'], man: 'kho-nhien-lieu', o_ke_toan: true, ten: 'Chuyển kho',
        lam: ['Chọn kho đi, kho nhận, số lít'], may: ['Hai dòng sổ kho cùng một số CK-YYMM-###; mang giá bình quân của kho đi'],
        chan: ['Chuyển quá tồn → chặn', 'Kho đi = kho nhận → chặn'], giay: ['Phiếu chuyển kho'], ct: ['CK_NL'] },
      { so: 'K4', vai: ['fuel', 'acct'], man: 'kho-nhien-lieu', o_ke_toan: true, ten: 'Xuất tay cho xe (ngoài phiếu)',
        lam: ['Chọn kho, số xe, số lít'], may: ['Giá = bình quân kho'], chan: ['Xuất quá tồn của đúng kho → chặn'] },
    ] },
    { gd: 'Kho phụ tùng và sửa xe khi không chạy', buoc: [
      { so: 'P1', vai: ['parts'], man: 'kho-phu-tung', o_ke_toan: true, ten: 'Thủ kho phụ tùng nhập · xuất',
        lam: ['Nhập: số lượng + đơn giá (giá bình quân tính lại)', 'Xuất tay cho xe'], chan: ['Bãi, kế toán không nhập xuất phụ tùng (C1.2)', 'Xuất quá tồn → chặn'],
        ct: ['PNK_PT', 'PXK_PT'] },
      { so: 'P2', vai: ['repair', 'expacct', 'cash'], man: 'sua-chua', ten: 'Lệnh sửa chữa riêng — bảo dưỡng, xe nằm xưởng (C7.3)',
        lam: ['Tổ sửa chữa lập lệnh: xe, km, gara; dòng lấy KHO hoặc MUA', 'KT Chi phí kiểm → ghi sổ', 'Quỹ tiền mặt cảng cạn chi phần mua ngoài'],
        may: ['Dòng lấy kho trừ tồn NGAY LÚC KHAI'], chan: ['Không gắn phiếu xuất xe nào'], ct: ['PXK_PT', 'PC_SC'] },
    ] },
    { gd: 'Bán hàng (phụ tùng · xăng dầu)', buoc: [
      { so: 'B1', vai: ['acct', 'rev', 'fuel'], man: 'ban-hang', ten: 'Bán cho khách',
        lam: ['Chọn khách (hoặc gõ tên), thêm dòng phụ tùng / dầu kho, đơn giá bán'], may: ['Xuất kho theo giá vốn bình quân (Nợ 607)', 'Hoá đơn bán sinh cùng lúc'],
        chan: ['Bán quá tồn của đúng kho → chặn'], giay: ['Hoá đơn bán hàng'], ct: ['PXK_BAN', 'HD_BAN'] },
      { so: 'B2', vai: ['rev', 'cash', 'treasury'], man: 'ban-hang', ten: 'Thu tiền bán hàng', lam: ['Bấm Đã thu'], chan: ['Thu hai lần → chặn'], ct: ['PT_BAN'] },
      { so: 'B3', vai: ['acct', 'rev', 'fuel', 'cash', 'treasury'], man: 'ban-hang', ten: 'Chủ xe liên kết mua ở quầy — trừ vào tiền trả',
        lam: ['Người mua = "Chủ xe liên kết — trừ vào tiền trả", chọn chủ xe'], may: ['Không thu tiền mặt; đợt trả chủ xe kế tiếp tự trừ (công đoạn 18)'],
        chan: ['Thu tiền mặt phiếu này → chặn (TRU_CHU_XE)', 'Đã trừ vào một đợt → không bỏ phiếu được'], ct: ['PXK_BAN', 'HD_BAN'] },
    ] },
    { gd: 'Tách chặng: mỏ → bãi → cảng (B1–B4)', buoc: [
      { so: 'T1', vai: ['yard'], man: 'phieu-xuat-xe', ten: 'Phiếu GOM (xe A) mỏ → bãi', lam: ['Lập phiếu loại GOM, số G4-…'],
        may: ['Xe về: hàng vào kho bãi thành một lô'], ct: ['DO', 'PNK_HH'] },
      { so: 'T2', vai: ['yard'], man: 'kho-hang', o_ke_toan: true, ten: 'Hàng nằm bãi nhiều ngày', lam: ['Xem tồn từng lô ở màn Kho hàng', 'Kế toán điều chỉnh có lý do (cân lại, hao)'], ct: ['DC_HH'] },
      { so: 'T3', vai: ['yard'], man: 'phieu-xuat-xe', ten: 'Phiếu GIAO (xe B) bãi → cảng lấy từ lô', lam: ['Chọn lô và số tấn'],
        may: ['Xe tới: hàng xuất khỏi kho bãi, hao hụt tính theo phiếu'], chan: ['Lấy quá tồn lô → chặn', 'Xoá phiếu gom đã có người lấy hàng → chặn'], ct: ['DO', 'PXK_HH'] },
      { so: 'T4', vai: ['rev'], man: 'hoa-don-gop', ten: 'Cước riêng từng chặng · hoá đơn gộp tháng', lam: ['Phiếu gom có cước riêng thì lập hoá đơn như phiếu giao', 'Khách hợp đồng: gộp tháng'], ct: ['HD', 'PT'] },
    ] },
    { gd: 'Thẻ cao tốc · trạm dầu Việt Nam · nhà cung cấp', buoc: [
      { so: 'C1', vai: ['acct', 'cash', 'treasury'], man: 'the-cao-toc', ten: 'Thẻ cao tốc (C6.1)',
        lam: ['KT Thu/Chi lập thẻ (của khách hay của EPL)', 'Quỹ / kế toán nạp tiền'], may: ['Trừ thẻ đúng một lần lúc ghi sổ mục IV', 'Thẻ của khách: cuối tháng cấn trừ vào cước của khách đó'],
        chan: ['Điều chỉnh số dư phải có lý do'] },
      { so: 'C2', vai: ['expacct'], man: 'nha-cung-cap', ten: 'Trạm dầu Việt Nam ghi nợ (C5.1)',
        lam: ['Gắn trạm với khách được cấn trừ', 'Cuối tháng: trả trạm, hoặc cấn trừ vào cước khách (công đoạn 17)'] },
      { so: 'C3', vai: ['expacct', 'cash', 'treasury'], man: 'nha-cung-cap', ten: 'Trả nhà cung cấp theo đợt', lam: ['Chọn nhà cung cấp, số tiền, cách chi'], ct: ['PC_NCC'] },
    ] },
  ];

  /* ================================================================ ngoài phiếu: ai được làm gì (theo mã) */
  const VIEC = [
    ['Lập phiếu xuất xe, đổi xe, báo mốc', ['yard']],
    ['Nhập số phiếu quặng, giá cước, giá thuê xe, phí, ngưỡng tấn', ['acct']],
    ['Duyệt báo hỏng (mục V)', ['repair']],
    ['Duyệt khai đổ dầu dọc đường', ['yard', 'fuel']],
    ['Cấp dầu theo phiếu lĩnh', ['depot', 'fuel']],
    ['Khoá / mở khoá phiếu', ['acct']],
    ['Lập hoá đơn, ghi thu, cấn trừ', ['rev']],
    ['Trả chủ xe liên kết', ['cash', 'treasury']],
    ['Điều khoản chủ xe (phí, ngưỡng, cách trả)', ['acct']],
    ['Nhập · xuất · chuyển kho dầu', ['fuel', 'acct']],
    ['Nhập · xuất kho phụ tùng', ['parts']],
    ['Lập phiếu bán hàng', ['acct', 'rev', 'fuel']],
    ['Thu tiền bán hàng', ['rev', 'cash', 'treasury']],
    ['Lệnh sửa chữa: lập · kiểm/ghi sổ · chi', ['repair', 'expacct', 'cash']],
    ['Tất toán tài xế', ['expacct', 'cash', 'treasury']],
    ['Trả nhà cung cấp', ['expacct', 'cash', 'treasury']],
    ['Thẻ cao tốc: lập thẻ · nạp tiền', ['acct', 'cash', 'treasury']],
    ['Bảng giá khách × tuyến, tỷ giá', ['acct', 'rev']],
    ['Điều chỉnh kho hàng bãi', ['acct']],
    ['Đẩy chứng từ sang sổ kế toán', ['acct']],
  ];

  /* ================================================================ vẽ */
  const tenVai = (v) => NN.h('r_' + v);
  const ctCua = (ma) => (D && D.chung_tu.find(c => c.ma === ma)) || null;
  // "Nợ 625 · 4022 / Có 1371" — gom các biến thể cho gọn; chi tiết đủ ở tab Danh mục chứng từ
  function dkGon(c) {
    if (!c || !c.dinh_khoan) return 'không định khoản';
    const u = (a) => [...new Set(a.filter(Boolean))];
    const no = u(c.bien_the.map(b => b.no)), co = u(c.bien_the.map(b => b.co));
    if (!no.length && !co.length) return 'ngoài bảng · mã do kế toán cấp';
    return `Nợ ${no.join(' · ') || '—'} / Có ${co.join(' · ') || '—'}`;
  }
  const ds = (arr, cls) => arr && arr.length ? `<ul class="${cls || ''}">${arr.map(x => `<li>${esc(x)}</li>`).join('')}</ul>` : '';

  function theBuoc(b) {
    const ct = (b.ct || []).map(ma => {
      const c = ctCua(ma);
      return `<button class="qt-ct-chip" data-ct="${ma}" title="Xem đủ các trường hợp định khoản">
        <b>${ma}</b> <span>${esc(c ? c.ten : ma)}</span><small>${esc(dkGon(c))}</small>${b.ct_khi && b.ct_khi[ma] ? `<i>${esc(b.ct_khi[ma])}</i>` : ''}</button>`;
    }).join('');
    return `<article class="qt-buoc">
      <div class="qt-b-dau"><span class="so">${esc(String(b.so))}</span>
        <div class="grow"><h4>${esc(b.ten)}</h4>
          <div class="qt-b-vai">${b.vai.map(v => `<span class="qt-vai">${tenVai(v)}</span>`).join('')}
            ${b.o_ke_toan ? '<span class="qt-man qt-man-kt">ở trang kế toán</span>'   // màn đã dời sang EPL_KETOAN (28/09)
              : `<button class="qt-man" data-man="${b.man}">màn ${NN.h(((EPL.MODULES || []).find(m => m.id === b.man) || {}).nav || b.man)} ↗</button>`}</div></div>
        ${b.sau ? `<span class="qt-sau">${esc(b.sau)}</span>` : ''}</div>
      <div class="qt-b-than">
        <div class="qt-b-cot"><div class="l">Làm gì</div>${ds(b.lam)}
          ${b.may && b.may.length ? `<div class="l">Máy tự làm</div>${ds(b.may, 'may')}` : ''}
          ${b.chan && b.chan.length ? `<div class="l">Máy chặn</div>${ds(b.chan, 'chan')}` : ''}</div>
        <div class="qt-b-cot qt-b-ra">
          <div class="l">Phiếu in ra</div>${b.giay && b.giay.length ? b.giay.map(g => `<div class="qt-giay">${esc(g)}</div>`).join('') : '<div class="muted small">—</div>'}
          <div class="l">Chứng từ sinh ra</div>${ct || '<div class="muted small">— không sinh chứng từ</div>'}</div>
      </div></article>`;
  }
  function veLuong(dsGd, dich) {
    q(dich).innerHTML = dsGd.map((g, i) => `<section class="qt-gd"><h3><span>${i + 1}</span>${esc(g.gd)}</h3>${g.buoc.map(theBuoc).join('')}</section>`).join('');
  }

  // mã chứng từ → các công đoạn sinh ra nó (cho tab Danh mục)
  function noiSinh(ma) {
    const ra = [];
    [...CHUYEN, ...NGOAI].forEach(g => g.buoc.forEach(b => { if ((b.ct || []).includes(ma)) ra.push(`${b.so}. ${b.ten}`); }));
    return ra;
  }
  function veChungTu() {
    q('#qt-ct-than').innerHTML = D.chung_tu.map(c => {
      const bt = c.dinh_khoan && c.bien_the.length ? c.bien_the : [{ khi: '', no: null, co: null }];
      const sinh = noiSinh(c.ma);
      return bt.map((b, i) => `<tr id="qt-ct-${c.ma}" class="${i ? 'tiep' : 'dau'}">
        ${i ? '' : `<td rowspan="${bt.length}" class="mono"><b>${c.ma}</b></td><td rowspan="${bt.length}"><b>${esc(c.ten)}</b><div class="small muted" lang="lo">${esc(c.ten_lo)}</div></td>
          <td rowspan="${bt.length}" class="small">${sinh.length ? sinh.map(esc).join('<br>') : '<span class="muted">—</span>'}</td>`}
        <td class="small">${esc(b.khi || (c.dinh_khoan ? 'mọi trường hợp' : 'chỉ lưu, không bút toán'))}</td>
        <td>${b.no ? `<span class="acct">${esc(b.no)}</span> <span class="small muted">${esc(b.no_ten || '')}</span>` : (c.dinh_khoan ? '<span class="muted small">ngoài bảng / kế toán cấp mã</span>' : '—')}</td>
        <td>${b.co ? `<span class="acct">${esc(b.co)}</span> <span class="small muted">${esc(b.co_ten || '')}</span>` : '—'}</td></tr>`).join('');
    }).join('');
  }

  // "Được nhập đơn giá" THẬT: luật cho phép (nhap_gia) VÀ vai đó nhập hoặc kiểm ít nhất một mục chi III–VI
  const nhapGiaThat = (v) => D.tien[v].nhap_gia && ['fuel', 'travel', 'repair', 'other'].some(m => D.quyen[v].edit.includes(m) || D.quyen[v].verify.includes(m));
  function veMaTran() {
    const vai = D.vai.filter(v => v !== 'admin');
    q('#qt-mt-dau').innerHTML = `<tr><th>Mục của phiếu</th>${vai.map(v => `<th>${tenVai(v)}</th>`).join('')}</tr>`;
    const MUC = [['info', 'I. Xe'], ['trans', 'II. Chuyến · khách · cân'], ['fuel', 'III. Nhiên liệu'], ['travel', 'IV. Đi đường'], ['repair', 'V. Sửa chữa'], ['other', 'VI. Chi khác']];
    const o = (v, m) => { const p = D.quyen[v]; const ch = [['edit', 'N'], ['verify', 'K'], ['book', 'G'], ['pay', 'C']].filter(([k]) => p[k].includes(m)).map(x => x[1]).join(' ');
      return `<td class="qt-o ${!ch ? 'trong' : ch.startsWith('N') ? 'nhap' : ch.startsWith('C') ? 'chi' : 'kiem'}">${ch || '—'}</td>`; };
    const co = (b) => `<td class="qt-o ${b ? 'nhap' : 'trong'}">${b ? '✓' : '✗'}</td>`;
    q('#qt-mt-than').innerHTML = MUC.map(([m, ten]) => `<tr><td><b>${ten}</b></td>${vai.map(v => o(v, m)).join('')}</tr>`).join('')
      + `<tr class="qt-mt-nhom"><td colspan="${vai.length + 1}">Tiền trên phiếu</td></tr>`
      + [['thay_tien_ban', 'Thấy tiền BÁN (giá cước, doanh thu, giá thuê xe, lãi)'], ['thay_tien_chi', 'Thấy tiền CHI (đơn giá, thành tiền, tỷ giá)'], ['nhap_gia', 'Được nhập đơn giá dòng chi']]
        .map(([k, ten]) => `<tr><td>${ten}</td>${vai.map(v => co(k === 'nhap_gia' ? nhapGiaThat(v) : D.tien[v][k])).join('')}</tr>`).join('');
    q('#qt-mt2-dau').innerHTML = q('#qt-mt-dau').innerHTML.replace('Mục của phiếu', 'Việc');
    q('#qt-mt2-than').innerHTML = VIEC.map(([ten, ai]) => `<tr><td>${esc(ten)}</td>${vai.map(v => co(ai.includes(v))).join('')}</tr>`).join('');
  }

  function doiXem(x) {
    xem = x;
    root.querySelectorAll('.qt-tab button').forEach(b => b.classList.toggle('active', b.dataset.xem === x));
    ['chuyen', 'ngoai', 'ma-tran', 'chung-tu'].forEach(k => { q('#qt-' + k).hidden = k !== x; });
  }
  function noiNut() {
    root.querySelectorAll('[data-man]').forEach(b => b.addEventListener('click', () => EPL.di(b.dataset.man)));
    root.querySelectorAll('[data-ct]').forEach(b => b.addEventListener('click', () => {
      doiXem('chung-tu');
      const tr = q('#qt-ct-' + b.dataset.ct);
      if (tr) { root.querySelectorAll('.qt-ctb tr.soi').forEach(x => x.classList.remove('soi')); root.querySelectorAll('#qt-ct-' + b.dataset.ct).forEach(x => x.classList.add('soi')); tr.scrollIntoView({ block: 'center' }); }
    }));
  }
  function veHet() { veLuong(CHUYEN, '#qt-chuyen-ds'); veLuong(NGOAI, '#qt-ngoai-ds'); veMaTran(); veChungTu(); noiNut(); }

  EPL.modules['quy-trinh'] = {
    async init(r) {
      root = r;
      root.querySelectorAll('.qt-tab button').forEach(b => b.addEventListener('click', () => doiXem(b.dataset.xem)));
      q('#qt-mo-so').addEventListener('click', () => EPL.di('chung-tu', { tab: 'so' }));
      D = await API.get('/api/quy-trinh');
      veHet(); doiXem('chuyen');
    },
    onLang() { if (root && D) veHet(); },
    // cho màn Tài khoản dùng lại: vai này sinh những chứng từ nào, làm những công đoạn nào
    buocCuaVai(v) { return [...CHUYEN, ...NGOAI].flatMap(g => g.buoc).filter(b => b.vai.includes(v)); },
  };
  EPL.QUY_TRINH = { CHUYEN, NGOAI, VIEC };
})();

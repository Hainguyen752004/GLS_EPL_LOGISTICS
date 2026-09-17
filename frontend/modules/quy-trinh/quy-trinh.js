/* Sơ đồ luồng nghiệp vụ — trang tham chiếu và thảo luận: ai làm bước nào, nhập gì, ẩn gì, sinh chứng
 * từ nào, định khoản ra sao.
 *
 * Toàn bộ nội dung nằm trong hai bảng dữ liệu bên dưới (LAN và BUOC). Sửa luồng thì sửa ở đây, màn
 * vẽ lại theo. Mỗi bước có `tt`:
 *   'co'      đang chạy thật trong hệ (có màn, có API, có bộ kiểm)
 *   'de_nghi' em đề nghị theo mô tả của anh, CHƯA làm, chờ anh chốt
 * Một bước có thể "đang có" nhưng bên trong có vài ô là đề nghị — ghi trong `de_nghi` của bước.
 */
(function () {
  const { NN, esc } = EPL;
  let root, chon = null, xem = 'so-do';
  const q = (s) => root.querySelector(s);

  /* ---------------------------------------------------------------- các làn (vai) */
  const LAN = [
    { id: 'yard',   khoa: 'r_yard',   av: 'TB', ghi: 'Điều độ tại bãi · người mở phiếu' },
    { id: 'acct',   khoa: 'r_acct',   av: 'KT', ghi: 'Kiểm, sửa, nhập các ô kế toán, khoá phiếu' },
    { id: 'fuel',   khoa: 'r_fuel',   av: 'KN', ghi: 'Kiểm và ghi sổ nhiên liệu' },
    { id: 'depot',  khoa: 'r_depot',  av: 'KH', ghi: 'Cấp dầu tại kho theo phiếu lĩnh' },
    { id: 'cash',   khoa: 'r_cash',   av: 'QU', ghi: 'Quỹ Viêng Chăn và tiền mặt lẻ Thà Bốc' },
    { id: 'driver', khoa: 'r_driver', av: 'TX', ghi: 'Nhận tiền, chạy, báo hỏng, khai dầu' },
    { id: 'rev',    khoa: 'r_rev',    av: 'DT', ghi: 'Hoá đơn và thu tiền khách' },
  ];

  /* ---------------------------------------------------------------- các bước, theo thứ tự thời gian */
  const BUOC = [
    { so: 1, vai: 'yard', tt: 'co', ten: 'Mở phiếu xuất xe (DO)', muc: 'sec1', man: 'phieu-xuat-xe',
      mo_ta: 'Bãi mở phiếu mới. Chọn loại xe: xe nhà hay xe thuê (xe liên kết). Đây là điều xe bằng tay, hạn chế nhưng hợp với bên Lào lúc này; sau nối module điều xe của EPL_System.',
      nhap: ['Loại xe: EPL hay liên kết', 'Số xe, biển đầu kéo, biển rơ-moóc', 'Tài xế', 'Ngày lập, ngày xe đi', 'Km lúc đi', 'Km về ước tính: máy tự tính = km đi + km tuyến (chỉ đọc). Km về thật nhập ở bước 13.'],
      chung_tu: ['Phiếu xuất xe · DO'], trang_thai: 'Mới → Đã xuất xe' },

    { so: 2, vai: 'yard', tt: 'co', ten: 'Mục II: tuyến, khách, hàng', muc: 'sec2', man: 'phieu-xuat-xe',
      mo_ta: 'Bãi chọn tuyến (điểm đi, điểm đến tự điền), khách hàng, loại hàng, số phiếu quặng và CÂN ĐẦU. Em chốt Bãi nhập cân vì tờ phiếu quặng nằm ở bãi lúc bốc hàng, kế toán ở Viêng Chăn không cầm tờ đó; kế toán chỉ kiểm lại con số. Tiền (đơn giá, thành tiền, quy đổi, khấu trừ) Bãi không thấy.',
      nhap: ['Tuyến đường', 'Khách hàng', 'Loại hàng', 'Số phiếu quặng, ngày', 'Đính kèm ảnh hoặc PDF phiếu quặng của khách', 'Điểm đi, điểm đến (tự theo tuyến)', 'Cân đầu (tấn) từ phiếu quặng'],
      an: ['Đơn giá USD/tấn', 'Thành tiền USD', 'Quy đổi LAK', 'Khấu trừ xe liên kết', 'Tổng kết doanh thu · chi · lãi'],
      chung_tu: [], trang_thai: 'Mục II: Chưa gửi → Đã nhập' },

    { so: 3, vai: 'yard', tt: 'co', ten: 'Mục III: nhiên liệu', muc: 'sec3', man: 'phieu-xuat-xe',
      mo_ta: 'Bãi khai số lít và nơi đổ. Nơi đổ là kho dầu của EPL thì ra phiếu lĩnh có mã QR cho tài xế cầm tới kho. Giá dầu là giá vốn, chỉ thủ kho và kế toán thấy.',
      nhap: ['Số lít', 'Nơi đổ (kho EPL)'],
      an: ['Đơn giá', 'Tiền tệ', 'Thành tiền', 'Mã kế toán'],
      chung_tu: ['Phiếu lĩnh nhiên liệu (QR) · PLNL'], trang_thai: 'Phiếu lĩnh: Chờ cấp' },

    { so: 4, vai: 'yard', tt: 'co', ten: 'Mục IV: chi phí đi đường', muc: 'sec4', man: 'phieu-xuat-xe',
      mo_ta: 'Bãi khai các khoản tiền mặt tài xế cần cầm đi: tiền nước, chi phí sang Việt Nam, điện thoại, chipping, cao tốc. Ra phiếu tạm ứng có mã QR.',
      nhap: ['Khoản mục', 'Số lượng', 'Đơn giá'],
      chung_tu: ['Phiếu tạm ứng đi đường (QR) · PTU'], trang_thai: 'Mục IV: Đã nhập · chờ kiểm' },

    { so: 5, vai: 'acct', tt: 'co', ten: 'Kiểm mục I, II, IV · nhập ô kế toán', muc: 'sec2', man: 'phieu-xuat-xe',
      mo_ta: 'Kế toán Viêng Chăn mở phiếu, kiểm những gì Bãi nhập, sửa nếu sai hoặc trả lại cho Bãi. Nhập các ô đã ẩn với Bãi.',
      nhap: ['Đơn giá USD/tấn theo hợp đồng', 'Xe liên kết: giá thuê, phí 2%, ngưỡng tấn', 'Đơn giá dầu, tiền tệ, mã TK ở mục III nếu kho nhiên liệu chưa điền'],
      kiem: ['Mục I', 'Mục II (cân đầu Bãi nhập so với phiếu quặng)', 'Mục IV'],
      chung_tu: [], trang_thai: 'I, II: Đã kiểm · IV: Đã kiểm' },

    { so: 6, vai: 'fuel', tt: 'co', ten: 'Kiểm và ghi sổ mục III', muc: 'sec3', man: 'phieu-xuat-xe',
      mo_ta: 'Kế toán kho nhiên liệu kiểm số lít, ghi sổ. Dầu lĩnh kho định khoản 625/371, dầu mua ngoài 625/402, xe liên kết 4022/…',
      kiem: ['Mục III'], dinh_khoan: '625/371 (kho) · 625/402 (mua) · 4022/… (xe liên kết)',
      chung_tu: [], trang_thai: 'Mục III: Đã kiểm → Đã ghi sổ' },

    { so: 7, vai: 'depot', tt: 'co', ten: 'Quét QR, cấp dầu', muc: 'sec3', man: 'cap-phat',
      mo_ta: 'Xe tới kho, tài xế đưa phiếu lĩnh. Thủ kho quét mã, đối chiếu đúng xe đúng tài xế, nhập số lít cấp thật rồi bấm Cấp. Cấp lệch số duyệt thì bắt ghi lý do. Mất mạng vẫn cấp được, gửi lại sau.',
      nhap: ['Số lít cấp thật', 'Lý do nếu lệch'],
      chung_tu: ['Phiếu xuất kho nhiên liệu · PXK_NL'], dinh_khoan: '625/371', trang_thai: 'Phiếu lĩnh: Đã cấp · Tồn kho trừ ngay' },

    { so: 8, vai: 'acct', tt: 'co', ten: 'Ghi sổ mục IV', muc: 'sec4', man: 'phieu-xuat-xe',
      mo_ta: 'Kế toán ghi sổ khoản đi đường sau khi kiểm. Ghi sổ xong quỹ mới được chi.',
      dinh_khoan: '625/402', chung_tu: [], trang_thai: 'Mục IV: Đã ghi sổ · chờ chi' },

    { so: 9, vai: 'cash', tt: 'co', ten: 'Chi tạm ứng theo QR', muc: 'sec4', man: 'cap-phat',
      mo_ta: 'Tài xế cầm phiếu tạm ứng tới quỹ. Quỹ quét mã, đối chiếu, bấm Chi tiền. Mục IV chưa ghi sổ thì máy chặn.',
      chung_tu: ['Phiếu chi tạm ứng · PC_TU'], dinh_khoan: '625/… · Có: tiền mặt (mã bên kế toán cấp)',
      trang_thai: 'Mục IV: Đã chi · Phiếu lĩnh: Đã cấp' },

    { so: 10, vai: 'driver', tt: 'co', ten: 'Xuất phát · chia sẻ vị trí', muc: 'sec1', man: 'phieu-cua-toi',
      mo_ta: 'Tài xế thấy tiền tạm ứng đã chi thì bấm Xuất phát. Chưa nhận tiền mà bấm thì máy chặn. Bật chia sẻ vị trí để văn phòng thấy xe trên bản đồ.',
      nhap: ['Bấm Xuất phát', 'Bật chia sẻ vị trí'], chung_tu: [], trang_thai: 'Đã xuất xe → Đang vận chuyển' },

    { so: 11, vai: 'driver', tt: 'co', ten: 'Trên đường: báo hỏng, khai đổ dầu', muc: 'sec5', man: 'phieu-cua-toi',
      mo_ta: 'Xe hỏng thì báo hỏng kèm số tiền dự kiến. Chiều về từ Việt Nam phải mua dầu: khai số lít, trạm nào của nhà cung cấp nào, đơn giá VND. Máy tự quy đổi về LAK theo tỷ giá ghi trên phiếu.',
      nhap: ['Báo hỏng: hỏng gì, bao nhiêu tiền', 'Khai đổ dầu: lít, trạm, nhà cung cấp, đơn giá, tiền tệ'],
      chung_tu: [], trang_thai: 'Báo hỏng: Chờ duyệt · Khai dầu: Chờ duyệt' },

    { so: 12, vai: 'yard', tt: 'co', ten: 'Duyệt báo hỏng → mục V, VI', muc: 'sec5', man: 'theo-doi-tuyen',
      mo_ta: 'Bãi duyệt báo hỏng của tài xế. Có phụ tùng trong kho thì xuất kho (trừ tồn ngay); không có thì chi mua ngoài. Phiếu tự mở lại mục V. Khai đổ dầu do kế toán hoặc kho nhiên liệu duyệt, rơi vào mục III nguồn mua.',
      nhap: ['Duyệt hoặc từ chối', 'Nguồn: kho hay mua', 'Phụ tùng nếu lấy kho', 'Số tiền duyệt'],
      chung_tu: ['Phiếu xuất kho phụ tùng (nếu lấy kho) · PXK_PT'], dinh_khoan: '614/371 (kho) · 614/402 (mua)',
      trang_thai: 'Mục V: Đã nhập · chờ kiểm' },

    { so: 13, vai: 'yard', tt: 'co', ten: 'Xe tới nơi', muc: 'sec2', man: 'theo-doi-tuyen',
      mo_ta: 'Bãi bấm mốc cuối trên màn Theo dõi. Máy hỏi cân cuối, km về thật, ngày về.',
      nhap: ['Cân cuối (tấn)', 'Km về thật', 'Ngày về'], chung_tu: [], trang_thai: 'Đang vận chuyển → Đã giao hàng' },

    { so: 14, vai: 'acct', tt: 'co', ten: 'Kiểm lại toàn phiếu, khoá', muc: 'sec2', man: 'phieu-xuat-xe',
      mo_ta: 'Xe về rồi, kế toán bấm Khoá phiếu. Máy rà một lượt và liệt kê điểm lệch: km về thật so với ước tính (lệch quá 10%), hao hụt quá 1,5%, thiếu cân cuối, thiếu km về, chưa đính kèm phiếu quặng, mục có chi mà chưa kiểm. Kế toán đọc rồi xác nhận khoá. Khoá rồi Bãi và tài xế không ghi gì thêm; kế toán, quỹ, kho vẫn kiểm và chi tiếp. Chỉ phiếu đã khoá mới xuất hoá đơn và mới trả chủ xe liên kết.',
      kiem: ['Km ước tính so với km thật', 'Cân đầu so với cân cuối, hao hụt quá 1,5%', 'Phiếu quặng đã đính kèm chưa', 'Mục V, VI có chi mà chưa kiểm'],
      nhap: ['Bấm Khoá phiếu, đọc cảnh báo, xác nhận', 'Mở khoá nếu cần sửa (chưa xuất hoá đơn)'],
      chung_tu: [], trang_thai: 'Phiếu: Đã khoá 🔒' },

    { so: 15, vai: 'acct', tt: 'co', ten: 'Kiểm và ghi sổ mục V, VI', muc: 'sec5', man: 'phieu-xuat-xe',
      mo_ta: 'Kế toán kiểm và ghi sổ sửa chữa và chi khác phát sinh trên đường.',
      kiem: ['Mục V', 'Mục VI'], dinh_khoan: '614/… · 625/402', chung_tu: [], trang_thai: 'V, VI: Đã ghi sổ · chờ chi' },

    { so: 16, vai: 'cash', tt: 'co', ten: 'Chi mục V, VI', muc: 'sec5', man: 'phieu-xuat-xe',
      mo_ta: 'Tiền mặt lẻ Thà Bốc chi các khoản sửa chữa mua ngoài và chi khác.',
      chung_tu: ['Phiếu chi sửa chữa · chi khác · PC_SC'], dinh_khoan: '614/… · 625/… · Có: tiền mặt', trang_thai: 'V, VI: Đã chi' },

    { so: 17, vai: 'rev', tt: 'co', ten: 'Lập hoá đơn, thu tiền khách', muc: 'sec2', man: 'hoa-don',
      mo_ta: 'Kế toán doanh thu đối chiếu số phiếu, cân cuối, đơn giá hợp đồng rồi lập hoá đơn vận chuyển và ghi thu.',
      nhap: ['Lập hoá đơn', 'Ghi đã thu'], chung_tu: ['Hoá đơn vận chuyển · HD', 'Phiếu thu tiền khách · PT'], dinh_khoan: '1211/70 (hoá đơn) · tiền mặt/1211 (thu)',
      trang_thai: 'Chưa thanh toán → Đã thanh toán' },

    { so: 18, vai: 'cash', tt: 'co', ten: 'Xe liên kết: trả chủ xe', muc: 'sec2', man: 'xe-lien-ket',
      mo_ta: 'Với xe thuê ngoài: tiền trả chủ xe = giá thuê × tấn, trừ 2% mỗi phiếu, trừ 1 USD mỗi tấn vượt 40 t, trừ các khoản EPL đã ứng thay.',
      chung_tu: ['Phiếu chi trả chủ xe · PC_CX'], dinh_khoan: '4022/tiền mặt',
      nhap: ['Quỹ bấm Trả chủ xe (ở màn Xe liên kết hoặc trên phiếu) — phiếu phải đã khoá, mỗi phiếu trả một lần'],
      trang_thai: 'Chủ xe: Chưa trả → Đã trả' },

    { so: 19, vai: 'cash', tt: 'co', ten: 'Tất toán tài xế theo tháng', muc: 'sec4', man: 'tat-toan',
      mo_ta: 'Cuối tháng đối: đã ứng bao nhiêu, đã chi thật bao nhiêu. Dương thì công ty chi bù, âm thì tài xế nộp lại. Không tính khoản công ty trả nhà cung cấp theo đợt.',
      chung_tu: ['Phiếu chi bù · TT_CHI', 'hoặc Phiếu thu hoàn · TT_THU'], trang_thai: 'Kỳ: Đã tất toán · khoá' },

    { so: 20, vai: 'acct', tt: 'co', ten: 'Bán phụ tùng · xăng dầu', muc: 'sec_ban', man: 'ban-hang',
      mo_ta: 'Ngoài chuyến: EPL bán phụ tùng, dầu cho bên ngoài. Kế toán hoặc kho lập phiếu bán: chọn khách, thêm dòng phụ tùng (trừ tồn ngay) hoặc dầu kho, đơn giá bán, tiền tệ. Lập xong là có xuất kho và hoá đơn bán; kế toán doanh thu hoặc quỹ bấm Đã thu. Chưa thu thì còn bỏ được, hàng về kho.',
      nhap: ['Khách, ngày, tiền tệ', 'Dòng: phụ tùng hoặc dầu, số lượng, đơn giá bán', 'Ghi đã thu'],
      chung_tu: ['Phiếu xuất kho bán hàng · PXK_BAN', 'Hoá đơn bán hàng · HD_BAN', 'Phiếu thu bán hàng · PT_BAN'], dinh_khoan: 'giá vốn/371 · 1211/70 · tiền mặt/1211',
      trang_thai: 'Phiếu bán: Đã lập → Đã thu' },
  ];

  /* ---------------------------------------------------------------- ma trận vai × mục (đề nghị) */
  // Ô: chữ cái · có dấu * là ĐỀ NGHỊ thay đổi so với hiện tại
  const MUC = [
    { khoa: 'sec1', ten: 'I. Xe' },
    { khoa: 'sec2', ten: 'II. Tuyến · khách · cân đầu · cân cuối' },
    { khoa: 'sec2b', ten: 'II. Đơn giá · thành tiền · khấu trừ' },
    { khoa: 'sec3', ten: 'III. Nhiên liệu (lít, nơi đổ)' },
    { khoa: 'sec3b', ten: 'III. Đơn giá dầu · mã TK' },
    { khoa: 'sec4', ten: 'IV. Đi đường' },
    { khoa: 'sec5', ten: 'V. Sửa chữa' },
    { khoa: 'sec6', ten: 'VI. Khác' },
    { khoa: 'hd', ten: 'Hoá đơn · thu tiền' },
  ];
  const MT = {
    //         yard    acct    fuel   depot   cash   driver  rev
    sec1:  ['N',    'K',    'X',   '—',    'X',   'X',    'X'],
    sec2:  ['N',    'K',    'X',   '—',    'X',   'X',    'X'],
    sec2b: ['Ẩ',    'N K',  'X',   '—',    'X',   '—',    'X'],
    sec3:  ['N',    'X',    'K G', 'X',    'X',   'X',    'X'],
    sec3b: ['Ẩ',    'N K',  'K G', 'N',    'X',   '—',    'X'],
    sec4:  ['N',    'K G',  '—',   '—',    'C',   'X',    'X'],
    sec5:  ['N K',  'K G',  '—',   '—',    'C',   'N',    'X'],
    sec6:  ['N K',  'K G',  '—',   '—',    'C',   'X',    'X'],
    hd:    ['X',    'X',    '—',   '—',    'X',   '—',    'N K'],
  };

  /* ---------------------------------------------------------------- chứng từ */
  // [tên · MÃ trong Sổ chứng từ, bước, ai lập, định khoản gợi ý, tình trạng, ghi chú]
  // "Đang chạy" = bước đó đã ghi một tờ vào Sổ chứng từ (/api/chung-tu), bên anh Khang kéo về được.
  const CHUNG_TU = [
    ['Phiếu xuất xe · DO', '1', 'Bãi lập · cả hệ dùng', '—', 'co', 'Hồ sơ của cả chuyến, mọi chứng từ khác treo vào đây.'],
    ['Phiếu lĩnh nhiên liệu (QR) · PLNL', '3', 'Bãi in · tài xế cầm · thủ kho cấp', '—', 'co', 'Mỗi điểm đổ một tờ. Chưa định khoản: là cam kết, chưa ra hàng.'],
    ['Phiếu tạm ứng đi đường (QR) · PTU', '4', 'Bãi in · tài xế cầm · quỹ chi', '—', 'co', 'Gom mục IV, VI và dầu mua ngoài. Chưa định khoản: chưa ra tiền.'],
    ['Phiếu xuất kho nhiên liệu · PXK_NL', '6 · 7', 'Thủ kho khi cấp · kế toán kho khi ghi sổ', '625/371 · 4022/371', 'co', 'Sinh tự động, trừ tồn ngay.'],
    ['Phiếu chi tạm ứng · PC_TU', '9', 'Quỹ', '625/tiền mặt · 4022/tiền mặt', 'co', 'Có số riêng PC_TU/YYMM/0001. Vế Có để bên kế toán cấp mã tiền mặt.'],
    ['Phiếu xuất kho phụ tùng · PXK_PT', '12', 'Bãi khi duyệt sửa xe lấy kho', '614/371', 'co', 'Sinh tự động, trừ tồn ngay.'],
    ['Phiếu chi sửa chữa · chi khác · PC_SC', '16', 'Tiền mặt lẻ Thà Bốc', '614/tiền mặt · 625/tiền mặt', 'co', 'Một tờ cho cả mục, kèm từng dòng trong payload. Dòng lấy kho không tính (đã có PXK_PT).'],
    ['Hoá đơn vận chuyển · HD', '17', 'Kế toán doanh thu', '1211/70', 'co', 'Một chuyến một hoá đơn.'],
    ['Phiếu thu tiền khách · PT', '17', 'Kế toán doanh thu', 'tiền mặt/1211', 'co', 'Khi đổi trạng thái sang Đã thanh toán.'],
    ['Phiếu chi trả chủ xe liên kết · PC_CX', '18', 'Quỹ', '4022/tiền mặt', 'co', 'Nút Trả chủ xe ở màn Xe liên kết; phiếu phải đã khoá; mỗi phiếu một lần.'],
    ['Tất toán tài xế · TT_CHI hoặc TT_THU', '19', 'Kế toán · quỹ', '625/tiền mặt hoặc tiền mặt/625', 'co', 'Chi bù khi chi thật > ứng; thu hoàn khi ngược lại.'],
    ['Phiếu nhập kho nhiên liệu · PNK_NL', 'Ngoài chuyến', 'Kế toán kho', '371/402', 'co', 'Màn Kho nhiên liệu, nhập dầu.'],
    ['Phiếu nhập · xuất kho phụ tùng · PNK_PT · PXK_PT', 'Ngoài chuyến', 'Kế toán kho', '371/402 · 614/371', 'co', 'Màn Kho phụ tùng, nhập xuất tay.'],
    ['Phiếu chi trả nhà cung cấp · PC_NCC', 'Ngoài chuyến', 'Kế toán · quỹ', '402/tiền mặt', 'co', 'Màn Nhà cung cấp, trả theo đợt.'],
    ['Phiếu xuất kho bán hàng · PXK_BAN', '20', 'Kế toán · kho', 'giá vốn/371', 'co', 'Bán phụ tùng, dầu cho bên ngoài. Vế Nợ để bên kế toán cấp mã giá vốn.'],
    ['Hoá đơn bán hàng · HD_BAN', '20', 'Kế toán', '1211/70', 'co', 'Sinh cùng lúc lập phiếu bán.'],
    ['Phiếu thu bán hàng · PT_BAN', '20', 'Doanh thu · quỹ', 'tiền mặt/1211', 'co', 'Khi bấm Đã thu.'],
  ];

  /* ---------------------------------------------------------------- vẽ */
  const nhanTT = (tt) => tt === 'co' ? '<span class="qt-tt co">Đang chạy</span>' : '<span class="qt-tt de-nghi">Đề nghị</span>';
  const tenVai = (id) => NN.h((LAN.find(l => l.id === id) || {}).khoa || id);

  function veSoDo() {
    const soCot = BUOC.length;
    q('#qt-lan-ds').innerHTML = LAN.map(l => {
      const o = BUOC.map(b => b.vai === l.id
        ? `<button class="qt-nut ${b.tt} ${chon === b.so ? 'chon' : ''}" data-so="${b.so}">
             <span class="so">${b.so}</span><span class="ten">${esc(b.ten)}</span>
             ${b.chung_tu && b.chung_tu.length ? `<span class="ct">${esc(b.chung_tu[0])}${b.chung_tu.length > 1 ? ' +' + (b.chung_tu.length - 1) : ''}</span>` : ''}
           </button>`
        : '<span class="qt-o-trong"></span>').join('');
      return `<div class="qt-lan">
        <div class="qt-lan-nhan"><span class="av">${l.av}</span><div><b>${tenVai(l.id)}</b><small>${esc(l.ghi)}</small></div></div>
        <div class="qt-lan-o" style="--n:${soCot}">${o}</div></div>`;
    }).join('');
    q('#qt-lan-ds').querySelectorAll('[data-so]').forEach(b => b.addEventListener('click', () => { chon = +b.dataset.so; veSoDo(); vePanel(); }));
  }

  function vePanel() {
    const b = BUOC.find(x => x.so === chon);
    if (!b) return;
    q('#qt-p-ten').textContent = b.so + '. ' + b.ten;
    q('#qt-p-tt').innerHTML = nhanTT(b.tt);
    const ds = (tieu, arr, cls) => arr && arr.length
      ? `<div class="qt-p-khoi ${cls || ''}"><div class="l">${tieu}</div><ul>${arr.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>` : '';
    q('#qt-p-than').innerHTML = `
      <div class="qt-p-vai">${tenVai(b.vai)} · ${b.muc === 'sec_ban' ? NN.h('nav_sales') : NN.h(b.muc)}</div>
      <p>${esc(b.mo_ta)}</p>
      ${ds('Nhập', b.nhap)}
      ${ds('Kiểm', b.kiem)}
      ${ds('Ẩn với vai này', b.an, 'an')}
      ${ds('Chứng từ sinh ra', b.chung_tu, 'ct')}
      ${b.dinh_khoan ? `<div class="qt-p-khoi"><div class="l">Định khoản</div><div>${b.dinh_khoan.split(' · ').map(x => `<span class="acct">${esc(x)}</span>`).join(' ')}</div></div>` : ''}
      ${b.trang_thai ? `<div class="qt-p-khoi"><div class="l">Trạng thái</div><div>${esc(b.trang_thai)}</div></div>` : ''}
      ${ds('Đề nghị · chờ anh chốt', b.de_nghi, 'de-nghi')}
      <div class="qt-p-nut"><button class="btn sm" id="qt-mo">${NN.h('open_slip').replace(/phiếu/i, 'màn')}</button></div>`;
    const nut = q('#qt-mo'); if (nut) nut.addEventListener('click', () => EPL.di(b.man));
  }

  function veMaTran() {
    q('#qt-mt-dau').innerHTML = `<tr><th>Mục của phiếu</th>${LAN.map(l => `<th>${tenVai(l.id)}</th>`).join('')}</tr>`;
    q('#qt-mt-than').innerHTML = MUC.map(m => `<tr><td><b>${esc(m.ten)}</b></td>${(MT[m.khoa] || []).map(o => {
      const deNghi = o.includes('*'); const chu = o.replace(/\*/g, '');
      const cls = chu === '—' ? 'trong' : chu.startsWith('N') ? 'nhap' : chu.startsWith('K') || chu.startsWith('G') ? 'kiem' : chu.startsWith('C') ? 'chi' : chu.startsWith('Ẩ') ? 'an' : 'xem';
      return `<td class="qt-o ${cls} ${deNghi ? 'de-nghi' : ''}">${esc(chu)}</td>`; }).join('')}</tr>`).join('');
  }

  function veChungTu() {
    q('#qt-ct-than').innerHTML = CHUNG_TU.map(([ten, buoc, ai, tk, tt, ghi]) => `<tr>
      <td><b>${esc(ten)}</b></td><td class="num">${esc(buoc)}</td><td>${esc(ai)}</td>
      <td>${tk === '—' ? '—' : tk.split(' · ').map(x => `<span class="acct">${esc(x)}</span>`).join(' ')}</td>
      <td>${nhanTT(tt)}</td><td class="small muted">${esc(ghi)}</td></tr>`).join('');
  }

  function doiXem(x) {
    xem = x;
    root.querySelectorAll('.qt-tab button').forEach(b => b.classList.toggle('active', b.dataset.xem === x));
    q('#qt-so-do').hidden = x !== 'so-do';
    q('#qt-ma-tran').hidden = x !== 'ma-tran';
    q('#qt-chung-tu').hidden = x !== 'chung-tu';
    q('#qt-panel').hidden = x !== 'so-do';
  }

  EPL.modules['quy-trinh'] = {
    async init(r) {
      root = r;
      root.querySelectorAll('.qt-tab button').forEach(b => b.addEventListener('click', () => doiXem(b.dataset.xem)));
      veSoDo(); veMaTran(); veChungTu();
      const moSo = q('#qt-mo-so'); if (moSo) moSo.addEventListener('click', () => EPL.di('chung-tu', { tab: 'so' }));
      chon = 1; veSoDo(); vePanel(); doiXem('so-do');
    },
    onLang() { if (root) { veSoDo(); veMaTran(); veChungTu(); vePanel(); } },
  };
})();

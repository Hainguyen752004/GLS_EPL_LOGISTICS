/* eslint-env browser */
/**
 * Trang tài xế — ba ngôn ngữ: Tiếng Việt · English · ພາສາລາວ.
 *
 * Vì sao trang này cần: tài xế chạy tuyến Viêng Chăn → Cảng Cửa Lò là người Lào. Bắt họ đọc
 * "Chốt điều phối & xuất bến" bằng tiếng Việt trong lúc đứng ở cổng cảng là bắt họ đoán.
 *
 * MỖI CÂU DỊCH TRỌN hoặc để nguyên — không có câu lai hai thứ tiếng. Mã bản ghi (DO-…,
 * TRIP-…, biển số) và mã tiền tệ giữ nguyên ở mọi ngôn ngữ.
 *
 * Cách dùng:
 *   T('nut_ghi_moc')                 → chuỗi theo ngôn ngữ đang chọn
 *   T('da_ky_va_chot', {ma, gia})    → chuỗi có chỗ thay, viết {ten_cho}
 *   datNgonNgu('lo')                 → đổi ngôn ngữ, lưu lại, và vẽ lại toàn trang
 *
 * Chỗ dễ sai: đổi ngôn ngữ phải vẽ LẠI cả phần do JS sinh ra (thẻ chuyến, mốc, hộp ký nhận),
 * không chỉ thay nhãn tĩnh — nếu không thì nửa trang đổi, nửa kia vẫn tiếng Việt.
 */
(function () {
  'use strict';

  var LUU = 'EPL_TAIXE_NGON_NGU';

  var CHU = {
    // ---------------------------------------------------------------- vi
    vi: {
      ten_ngon_ngu: 'Tiếng Việt',
      ung_dung: 'Ứng dụng tài xế',
      khach_hang: 'Khách hàng',
      ma_chuyen: 'Mã chuyến',
      han_giao: 'Hạn giao',
      xe: 'Xe',
      to_lai: 'Tổ lái',
      chang_cua_chuyen: 'Chặng của chuyến',
      chang_da_xong: 'đã xong',
      chang_da_huy: 'đã huỷ',
      chang_chua_di: 'chưa đi',
      den_thuc_te: 'Đến thực tế: {gio}',
      ke_hoach: 'Kế hoạch: {gio}',
      nut_ghi_moc_la: '📍 Ghi mốc: {ten}',
      nut_hoan_tat_giao: '✍ Hoàn tất giao',
      goi_y_ghi_moc_truoc: 'Ghi mốc <b>{ten}</b> trước, rồi mới ký nhận được.',
      goi_y_da_ky_du: 'Đã ký nhận đủ các điểm giao của lệnh này.',
      cap_nhat: 'Cập nhật',
      toi_la_ai: 'Tôi là tài xế nào',
      chon_ten: 'Chọn tên của bạn',
      cham_de_chon: 'Chạm để chọn',
      dang_tai_tai_xe: 'Đang tải danh sách tài xế…',
      chuyen_cua_toi: 'Chuyến của tôi',
      cham_vao_ten: 'Chạm vào tên bạn ở trên để xem chuyến.',
      chua_co_chuyen: 'Hôm nay bạn chưa được xếp chuyến nào đang chạy.',
      quay_lai: 'Quay lại',
      canh_qua_han: '<b>Lệnh này đã quá hạn giao.</b> Nếu còn đang trên đường, hãy báo sự cố để điều độ biết lý do.',
      canh_su_co: '<b>{so} sự cố chưa đóng</b> trên chuyến này.',
      canh_gps_mo_phong: 'Vị trí trên bản đồ đang là <b>mô phỏng theo tuyến</b>, không phải GPS của máy bạn. Ghi mốc ở dưới để cập nhật vị trí thật.',
      chang_delivery: 'Chặng giao',
      chang_outbound: 'Đi ngang',
      chang_pickup: 'Đi lấy hàng',
      chang_empty_return: 'Về rỗng',
      chang_backhaul: 'Hàng về',
      chang_warehouse_transfer: 'Chuyển kho',
      ban_do_hong: 'Không tải được thư viện bản đồ.<br>Vẫn ghi mốc và ký nhận bình thường được.',
      dong: 'Đóng',

      // mốc
      moc_check_in: 'Vào bãi',
      moc_pickup: 'Lấy hàng',
      moc_departure: 'Xuất bến',
      moc_arrival: 'Đến điểm giao',
      moc_unloading: 'Dỡ hàng',
      moc_delivered: 'Giao xong',

      // trạng thái chuyến
      tt_dispatched: 'Đã điều phối · chờ xuất bến',
      tt_pending: 'Chờ điều phối',
      tt_departed: 'Đã xuất bến',
      tt_completed: 'Đã hoàn tất',
      tt_in_transit: 'Đang trên đường',
      tt_arrived: 'Đã đến · chờ ký nhận',
      tt_delivered: 'Đã giao · chờ xe về bãi',
      chua_ro: 'Chưa rõ',

      // bốn ô số
      da_di: 'Đã đi',
      con_lai: 'Còn lại',
      toc_do: 'Tốc độ',
      den_luc: 'Đến lúc',

      // thẻ nội dung
      lenh_giao_hang: 'Lệnh giao hàng',
      khach: 'Khách',
      tuyen: 'Tuyến',

      // ghi mốc
      chua_co_lenh: 'Chuyến này chưa có lệnh vận chuyển nên chưa ghi được mốc.',
      hoi_ghi_moc: 'Ghi mốc "{ten}"?',
      hoi_ghi_moc_noi: 'Ghi cho {ma} vào lúc này. Mốc vào lịch sử chuyến và cập nhật vị trí xe '
                     + 'trên màn điều độ. Không hoàn lại được.',
      nut_ghi_moc: 'Ghi mốc',
      nut_chua_ghi: 'Chưa ghi',
      da_ghi_moc: 'Đã ghi mốc "{ten}".',
      ghi_chu_moc: 'Tài xế ghi mốc "{ten}" trên trang tài xế',

      // sự cố
      bao_su_co: '⚠ Báo sự cố',
      loai_su_co: 'Loại sự cố',
      sc_ket_xe: 'Kẹt xe',
      sc_hong_hoc: 'Hỏng hóc',
      sc_thoi_tiet: 'Thời tiết',
      sc_giay_to: 'Giấy tờ',
      sc_tai_nan: 'Tai nạn',
      sc_hang_hu: 'Hàng hoá hư hỏng',
      sc_khac: 'Khác',
      muc_do: 'Mức độ',
      md_thap: 'Thấp — vẫn chạy được',
      md_trung: 'Trung bình — sẽ chậm giờ',
      md_cao: 'Cao — không chạy tiếp được',
      dang_o_dau: 'Đang ở đâu',
      vi_du_vi_tri: 'Ví dụ: QL51 đoạn Long Thành',
      chuyen_gi_xay_ra: 'Chuyện gì xảy ra',
      vi_du_su_co: 'Nổ lốp sau bên phải, đã gọi cứu hộ.',
      gui_bao_cao: 'Gửi báo cáo',

      // hoàn tất giao hàng
      hoan_tat_giao_hang: '✍ Hoàn tất giao hàng',
      buoc_1_pod: '1 · Bằng chứng giao hàng',
      buoc_2_gia: '2 · Chốt giá cuối',
      nut_hoan_tat: '✔ Hoàn tất',
      dang_doc_gia: 'Đang đọc hồ sơ giá…',
      khong_con_chang: 'Lệnh này không còn chặng giao nào cần ký.',
      diem_so: '(điểm {so})',
      giao_luc: 'Giao lúc',
      nguoi_nhan: 'Người nhận',
      sdt_nguoi_nhan: 'Số điện thoại người nhận',
      ket_qua_giao: 'Kết quả giao',
      kq_du: 'Giao đủ hàng',
      kq_thieu: 'Giao thiếu',
      kq_tu_choi: 'Khách từ chối nhận',
      anh_bien_ban: 'Ảnh biên bản / phiếu giao (bắt buộc)',
      chu_ky_nguoi_nhan: 'Chữ ký người nhận — ký trực tiếp bên dưới',
      da_ky: 'Đã ký',
      chua_ky: 'Chưa ký',
      ky_lai: 'Ký lại',
      tinh_trang_hang: 'Tình trạng hàng / ghi chú',
      vi_du_tinh_trang: 'Nguyên niêm phong, không móp vỡ',
      thieu_anh: 'Điểm giao {so} chưa có ảnh biên bản.',
      thieu_chu_ky: 'Điểm giao {so} chưa có chữ ký người nhận.',
      thieu_gio: 'Điểm giao {so} chưa nhập giờ giao.',
      da_ky_va_chot: 'Đã ký nhận và chốt giá cho {ma}. Giá cuối: {gia}',
      ghi_chu_ky: 'Tài xế ký nhận trên trang tài xế',
      khai_khi_ky: 'Tài xế khai khi ký nhận',

      // chung
      xac_nhan: 'Xác nhận',
      dong_y: 'Đồng ý',
      da_cap_nhat: 'Đã cập nhật.',
      khong_doc_duoc_tai_xe: 'Không đọc được danh sách tài xế:',
      khong_goi_duoc: 'Không gọi được máy chủ: {loi}',
      khong_gui_duoc: 'Không gửi được: {loi}',
      dia_chi_may_chu: 'Địa chỉ máy chủ EPL',
      dia_chi_may_chu_noi: 'Để trống thì trang này gọi API ở cùng địa chỉ với nó.',
      doi_dia_chi: 'Đổi địa chỉ máy chủ API',
      luu_va_tai_lai: 'Lưu và tải lại',
    },

    // ---------------------------------------------------------------- en
    en: {
      ten_ngon_ngu: 'English',
      ung_dung: 'Driver app',
      khach_hang: 'Customer',
      ma_chuyen: 'Trip code',
      han_giao: 'Deadline',
      xe: 'Vehicle',
      to_lai: 'Crew',
      chang_cua_chuyen: 'Trip legs',
      chang_da_xong: 'done',
      chang_da_huy: 'cancelled',
      chang_chua_di: 'not started',
      den_thuc_te: 'Actual arrival: {gio}',
      ke_hoach: 'Planned: {gio}',
      nut_ghi_moc_la: '\ud83d\udccd Record: {ten}',
      nut_hoan_tat_giao: '\u270d Complete delivery',
      goi_y_ghi_moc_truoc: 'Record <b>{ten}</b> first, then you can sign for it.',
      goi_y_da_ky_du: 'Every drop point on this order has been signed for.',
      cap_nhat: 'Refresh',
      toi_la_ai: 'Which driver am I',
      chon_ten: 'Select your name',
      cham_de_chon: 'Tap to select',
      dang_tai_tai_xe: 'Loading drivers…',
      chuyen_cua_toi: 'My trips',
      cham_vao_ten: 'Tap your name above to see your trips.',
      chua_co_chuyen: 'You have no running trips assigned today.',
      quay_lai: 'Back',
      canh_qua_han: '<b>This order is past its delivery deadline.</b> If you are still on the road, report an incident so dispatch knows why.',
      canh_su_co: '<b>{so} open incident(s)</b> on this trip.',
      canh_gps_mo_phong: 'The position on the map is <b>simulated along the route</b>, not your phone\u2019s GPS. Record a milestone below to update the real position.',
      chang_delivery: 'Delivery leg',
      chang_outbound: 'Through leg',
      chang_pickup: 'Collection leg',
      chang_empty_return: 'Empty return',
      chang_backhaul: 'Backhaul',
      chang_warehouse_transfer: 'Warehouse transfer',
      ban_do_hong: 'The map library could not load.<br>You can still record milestones and sign for deliveries.',
      dong: 'Close',

      moc_check_in: 'Check in',
      moc_pickup: 'Collect',
      moc_departure: 'Depart',
      moc_arrival: 'Arrive',
      moc_unloading: 'Unload',
      moc_delivered: 'Delivered',

      tt_dispatched: 'Assigned · awaiting departure',
      tt_pending: 'Awaiting dispatch',
      tt_departed: 'Departed',
      tt_completed: 'Completed',
      tt_in_transit: 'On the road',
      tt_arrived: 'Arrived · awaiting signature',
      tt_delivered: 'Delivered · returning to yard',
      chua_ro: 'Unknown',

      da_di: 'Covered',
      con_lai: 'Remaining',
      toc_do: 'Speed',
      den_luc: 'Arrival',

      lenh_giao_hang: 'Delivery order',
      khach: 'Customer',
      tuyen: 'Route',

      chua_co_lenh: 'This trip has no freight order yet, so no milestone can be recorded.',
      hoi_ghi_moc: 'Record milestone "{ten}"?',
      hoi_ghi_moc_noi: 'Recording for {ma} right now. The milestone enters the trip history and '
                     + 'moves the vehicle on the dispatcher’s map. It cannot be undone.',
      nut_ghi_moc: 'Record',
      nut_chua_ghi: 'Not yet',
      da_ghi_moc: 'Milestone "{ten}" recorded.',
      ghi_chu_moc: 'Driver recorded milestone "{ten}" in the driver app',

      bao_su_co: '⚠ Report incident',
      loai_su_co: 'Incident type',
      sc_ket_xe: 'Traffic jam',
      sc_hong_hoc: 'Breakdown',
      sc_thoi_tiet: 'Weather',
      sc_giay_to: 'Paperwork',
      sc_tai_nan: 'Accident',
      sc_hang_hu: 'Cargo damage',
      sc_khac: 'Other',
      muc_do: 'Severity',
      md_thap: 'Low — can still drive',
      md_trung: 'Medium — will be late',
      md_cao: 'High — cannot continue',
      dang_o_dau: 'Where are you',
      vi_du_vi_tri: 'For example: QL51, Long Thanh section',
      chuyen_gi_xay_ra: 'What happened',
      vi_du_su_co: 'Rear right tyre blew out, recovery called.',
      gui_bao_cao: 'Send report',

      hoan_tat_giao_hang: '✍ Complete delivery',
      buoc_1_pod: '1 · Proof of delivery',
      buoc_2_gia: '2 · Final price',
      nut_hoan_tat: '✔ Complete',
      dang_doc_gia: 'Loading the price record…',
      khong_con_chang: 'This order has no delivery leg left to sign for.',
      diem_so: '(stop {so})',
      giao_luc: 'Delivered at',
      nguoi_nhan: 'Recipient',
      sdt_nguoi_nhan: 'Recipient phone',
      ket_qua_giao: 'Delivery outcome',
      kq_du: 'Delivered in full',
      kq_thieu: 'Short delivery',
      kq_tu_choi: 'Refused by customer',
      anh_bien_ban: 'Photo of the delivery note (required)',
      chu_ky_nguoi_nhan: 'Recipient signature — sign directly below',
      da_ky: 'Signed',
      chua_ky: 'Not signed',
      ky_lai: 'Sign again',
      tinh_trang_hang: 'Cargo condition / notes',
      vi_du_tinh_trang: 'Seal intact, no dents or breakage',
      thieu_anh: 'Stop {so} has no photo of the delivery note.',
      thieu_chu_ky: 'Stop {so} has no recipient signature.',
      thieu_gio: 'Stop {so} has no delivery time.',
      da_ky_va_chot: 'Signed and price locked for {ma}. Final price: {gia}',
      ghi_chu_ky: 'Signed off by the driver in the driver app',
      khai_khi_ky: 'Entered by the driver at signing',

      xac_nhan: 'Confirm',
      dong_y: 'OK',
      da_cap_nhat: 'Updated.',
      khong_doc_duoc_tai_xe: 'Could not load the driver list:',
      khong_goi_duoc: 'Could not reach the server: {loi}',
      khong_gui_duoc: 'Could not send: {loi}',
      dia_chi_may_chu: 'EPL server address',
      dia_chi_may_chu_noi: 'Leave it blank and this page calls the API at its own address.',
      doi_dia_chi: 'Change API server address',
      luu_va_tai_lai: 'Save and reload',
    },

    // ---------------------------------------------------------------- lo
    lo: {
      ten_ngon_ngu: 'ລາວ',
      ung_dung: 'ແອັບຄົນຂັບ',
      khach_hang: 'ລູກຄ້າ',
      ma_chuyen: 'ລະຫັດຖ້ຽວ',
      han_giao: 'ກຳນົດສົ່ງ',
      xe: 'ລົດ',
      to_lai: 'ທີມຂັບ',
      chang_cua_chuyen: 'ຊ່ວງທາງຂອງຖ້ຽວ',
      chang_da_xong: 'ສຳເລັດແລ້ວ',
      chang_da_huy: 'ຍົກເລີກແລ້ວ',
      chang_chua_di: 'ຍັງບໍ່ໄດ້ໄປ',
      den_thuc_te: 'ຮອດຕົວຈິງ: {gio}',
      ke_hoach: 'ແຜນ: {gio}',
      nut_ghi_moc_la: '📍 ບັນທຶກ: {ten}',
      nut_hoan_tat_giao: '✍ ສຳເລັດການສົ່ງ',
      goi_y_ghi_moc_truoc: 'ບັນທຶກ <b>{ten}</b> ກ່ອນ, ແລ້ວຈຶ່ງເຊັນຮັບໄດ້.',
      goi_y_da_ky_du: 'ທຸກຈຸດສົ່ງຂອງໃບສັ່ງນີ້ໄດ້ເຊັນຮັບຄົບແລ້ວ.',
      cap_nhat: 'ໂຫຼດຄືນ',
      toi_la_ai: 'ຂ້ອຍແມ່ນຄົນຂັບຄົນໃດ',
      chon_ten: 'ເລືອກຊື່ຂອງທ່ານ',
      cham_de_chon: 'ແຕະເພື່ອເລືອກ',
      dang_tai_tai_xe: 'ກຳລັງໂຫຼດລາຍຊື່ຄົນຂັບ…',
      chuyen_cua_toi: 'ຖ້ຽວຂອງຂ້ອຍ',
      cham_vao_ten: 'ແຕະຊື່ຂອງທ່ານຂ້າງເທິງເພື່ອເບິ່ງຖ້ຽວ.',
      chua_co_chuyen: 'ມື້ນີ້ທ່ານຍັງບໍ່ໄດ້ຮັບມອບໝາຍຖ້ຽວໃດທີ່ກຳລັງແລ່ນ.',
      quay_lai: 'ກັບຄືນ',
      canh_qua_han: '<b>ໃບສັ່ງນີ້ເກີນກຳນົດສົ່ງແລ້ວ.</b> ຖ້າຍັງຢູ່ເທິງທາງ ກະລຸນາລາຍງານເຫດການ ເພື່ອໃຫ້ຜູ້ປ່ອຍລົດຮູ້ເຫດຜົນ.',
      canh_su_co: '<b>ມີ {so} ເຫດການຍັງບໍ່ປິດ</b> ໃນຖ້ຽວນີ້.',
      canh_gps_mo_phong: 'ຕຳແໜ່ງເທິງແຜນທີ່ແມ່ນ <b>ຈຳລອງຕາມເສັ້ນທາງ</b>, ບໍ່ແມ່ນ GPS ຂອງເຄື່ອງທ່ານ. ບັນທຶກຂັ້ນຕອນຂ້າງລຸ່ມເພື່ອອັບເດດຕຳແໜ່ງຈິງ.',
      chang_delivery: 'ຊ່ວງສົ່ງ',
      chang_outbound: 'ຊ່ວງຜ່ານ',
      chang_pickup: 'ຊ່ວງຮັບສິນຄ້າ',
      chang_empty_return: 'ກັບລົດເປົ່າ',
      chang_backhaul: 'ສິນຄ້າຂາກັບ',
      chang_warehouse_transfer: 'ຍ້າຍສາງ',
      ban_do_hong: 'ໂຫຼດແຜນທີ່ບໍ່ໄດ້.<br>ຍັງບັນທຶກຂັ້ນຕອນ ແລະ ເຊັນຮັບໄດ້ຕາມປົກກະຕິ.',
      dong: 'ປິດ',

      moc_check_in: 'ເຂົ້າກອງລົດ',
      moc_pickup: 'ຮັບສິນຄ້າ',
      moc_departure: 'ອອກເດີນທາງ',
      moc_arrival: 'ມາຮອດຈຸດສົ່ງ',
      moc_unloading: 'ລົງສິນຄ້າ',
      moc_delivered: 'ສົ່ງສຳເລັດ',

      tt_dispatched: 'ຈັດລົດແລ້ວ · ລໍຖ້າອອກເດີນທາງ',
      tt_pending: 'ລໍຖ້າຈັດລົດ',
      tt_departed: 'ອອກເດີນທາງແລ້ວ',
      tt_completed: 'ສຳເລັດແລ້ວ',
      tt_in_transit: 'ກຳລັງເດີນທາງ',
      tt_arrived: 'ມາຮອດແລ້ວ · ລໍຖ້າເຊັນຮັບ',
      tt_delivered: 'ສົ່ງແລ້ວ · ລໍຖ້າລົດກັບກອງ',
      chua_ro: 'ຍັງບໍ່ຈະແຈ້ງ',

      da_di: 'ແລ່ນໄປແລ້ວ',
      con_lai: 'ຍັງເຫຼືອ',
      toc_do: 'ຄວາມໄວ',
      den_luc: 'ຮອດເວລາ',

      lenh_giao_hang: 'ໃບສັ່ງປ່ອຍສິນຄ້າ',
      khach: 'ລູກຄ້າ',
      tuyen: 'ເສັ້ນທາງ',

      chua_co_lenh: 'ຖ້ຽວນີ້ຍັງບໍ່ມີໃບສັ່ງຂົນສົ່ງ ຈຶ່ງຍັງບັນທຶກຂັ້ນຕອນບໍ່ໄດ້.',
      hoi_ghi_moc: 'ບັນທຶກຂັ້ນຕອນ "{ten}" ບໍ?',
      hoi_ghi_moc_noi: 'ບັນທຶກໃຫ້ {ma} ໃນຕອນນີ້. ຂັ້ນຕອນຈະເຂົ້າປະຫວັດຖ້ຽວ ແລະ ອັບເດດຕຳແໜ່ງລົດ '
                     + 'ເທິງໜ້າຈໍຜູ້ປ່ອຍລົດ. ຄືນຫຼັງບໍ່ໄດ້.',
      nut_ghi_moc: 'ບັນທຶກ',
      nut_chua_ghi: 'ຍັງບໍ່ບັນທຶກ',
      da_ghi_moc: 'ບັນທຶກຂັ້ນຕອນ "{ten}" ແລ້ວ.',
      ghi_chu_moc: 'ຄົນຂັບບັນທຶກຂັ້ນຕອນ "{ten}" ເທິງແອັບຄົນຂັບ',

      bao_su_co: '⚠ ລາຍງານເຫດການ',
      loai_su_co: 'ປະເພດເຫດການ',
      sc_ket_xe: 'ລົດຕິດ',
      sc_hong_hoc: 'ລົດເສຍ',
      sc_thoi_tiet: 'ສະພາບອາກາດ',
      sc_giay_to: 'ເອກະສານ',
      sc_tai_nan: 'ອຸບັດຕິເຫດ',
      sc_hang_hu: 'ສິນຄ້າເສຍຫາຍ',
      sc_khac: 'ອື່ນໆ',
      muc_do: 'ລະດັບຄວາມຮ້າຍແຮງ',
      md_thap: 'ຕ່ຳ — ຍັງແລ່ນໄດ້',
      md_trung: 'ປານກາງ — ຈະຊ້າເວລາ',
      md_cao: 'ສູງ — ແລ່ນຕໍ່ບໍ່ໄດ້',
      dang_o_dau: 'ຢູ່ໃສ',
      vi_du_vi_tri: 'ຕົວຢ່າງ: ທາງເລກ 13 ຊ່ວງໂພນຫົງ',
      chuyen_gi_xay_ra: 'ເກີດຫຍັງຂຶ້ນ',
      vi_du_su_co: 'ຢາງຫຼັງຂວາແຕກ, ໄດ້ໂທເອີ້ນລົດກູ້ໄພແລ້ວ.',
      gui_bao_cao: 'ສົ່ງລາຍງານ',

      hoan_tat_giao_hang: '✍ ສຳເລັດການຈັດສົ່ງ',
      buoc_1_pod: '1 · ຫຼັກຖານການຈັດສົ່ງ',
      buoc_2_gia: '2 · ລາຄາສຸດທ້າຍ',
      nut_hoan_tat: '✔ ສຳເລັດ',
      dang_doc_gia: 'ກຳລັງໂຫຼດຂໍ້ມູນລາຄາ…',
      khong_con_chang: 'ໃບສັ່ງນີ້ບໍ່ມີຊ່ວງສົ່ງທີ່ຕ້ອງເຊັນອີກແລ້ວ.',
      diem_so: '(ຈຸດທີ {so})',
      giao_luc: 'ສົ່ງເມື່ອ',
      nguoi_nhan: 'ຜູ້ຮັບ',
      sdt_nguoi_nhan: 'ເບີໂທຜູ້ຮັບ',
      ket_qua_giao: 'ຜົນການສົ່ງ',
      kq_du: 'ສົ່ງຄົບ',
      kq_thieu: 'ສົ່ງຂາດ',
      kq_tu_choi: 'ລູກຄ້າປະຕິເສດຮັບ',
      anh_bien_ban: 'ຮູບໃບສົ່ງສິນຄ້າ (ຈຳເປັນ)',
      chu_ky_nguoi_nhan: 'ລາຍເຊັນຜູ້ຮັບ — ເຊັນຢູ່ຂ້າງລຸ່ມນີ້',
      da_ky: 'ເຊັນແລ້ວ',
      chua_ky: 'ຍັງບໍ່ເຊັນ',
      ky_lai: 'ເຊັນໃໝ່',
      tinh_trang_hang: 'ສະພາບສິນຄ້າ / ໝາຍເຫດ',
      vi_du_tinh_trang: 'ຊີນຍັງດີ, ບໍ່ບຸບ ບໍ່ແຕກ',
      thieu_anh: 'ຈຸດສົ່ງ {so} ຍັງບໍ່ມີຮູບໃບສົ່ງສິນຄ້າ.',
      thieu_chu_ky: 'ຈຸດສົ່ງ {so} ຍັງບໍ່ມີລາຍເຊັນຜູ້ຮັບ.',
      thieu_gio: 'ຈຸດສົ່ງ {so} ຍັງບໍ່ໄດ້ປ້ອນເວລາສົ່ງ.',
      da_ky_va_chot: 'ເຊັນຮັບ ແລະ ລັອກລາຄາໃຫ້ {ma} ແລ້ວ. ລາຄາສຸດທ້າຍ: {gia}',
      ghi_chu_ky: 'ຄົນຂັບເຊັນຮັບເທິງແອັບຄົນຂັບ',
      khai_khi_ky: 'ຄົນຂັບປ້ອນຕອນເຊັນຮັບ',

      xac_nhan: 'ຢືນຢັນ',
      dong_y: 'ຕົກລົງ',
      da_cap_nhat: 'ອັບເດດແລ້ວ.',
      khong_doc_duoc_tai_xe: 'ອ່ານລາຍຊື່ຄົນຂັບບໍ່ໄດ້:',
      khong_goi_duoc: 'ຕິດຕໍ່ເຊີບເວີບໍ່ໄດ້: {loi}',
      khong_gui_duoc: 'ສົ່ງບໍ່ໄດ້: {loi}',
      dia_chi_may_chu: 'ທີ່ຢູ່ເຊີບເວີ EPL',
      dia_chi_may_chu_noi: 'ປະຫວ່າງໄວ້ ໜ້ານີ້ຈະເອີ້ນ API ຢູ່ທີ່ຢູ່ດຽວກັນກັບມັນ.',
      doi_dia_chi: 'ປ່ຽນທີ່ຢູ່ເຊີບເວີ API',
      luu_va_tai_lai: 'ບັນທຶກ ແລະ ໂຫຼດຄືນ',
    },
  };

  var ma = 'vi';
  try {
    var luu = localStorage.getItem(LUU);
    if (luu && CHU[luu]) ma = luu;
  } catch (e) { /* trình duyệt chặn lưu trữ */ }

  /** Lấy chuỗi theo ngôn ngữ đang chọn; thiếu khoá thì rơi về tiếng Việt chứ không hiện trống. */
  function T(khoa, thay) {
    var s = (CHU[ma] && CHU[ma][khoa]) || CHU.vi[khoa] || khoa;
    if (thay) {
      s = s.replace(/\{(\w+)\}/g, function (_, k) { return thay[k] == null ? '' : thay[k]; });
    }
    return s;
  }

  function ngonNgu() { return ma; }

  /** Thay nhãn tĩnh trong HTML. Phần do JS sinh ra thì `veLai` lo. */
  function veNhanTinh(goc) {
    var d = goc || document;
    d.querySelectorAll('[data-i18n]').forEach(function (n) { n.textContent = T(n.getAttribute('data-i18n')); });
    d.querySelectorAll('[data-i18n-ph]').forEach(function (n) { n.placeholder = T(n.getAttribute('data-i18n-ph')); });
    d.querySelectorAll('[data-i18n-al]').forEach(function (n) {
      n.setAttribute('aria-label', T(n.getAttribute('data-i18n-al')));
    });
    document.documentElement.lang = ma;
    document.querySelectorAll('[data-ngonngu]').forEach(function (b) {
      b.setAttribute('aria-checked', b.getAttribute('data-ngonngu') === ma ? 'true' : 'false');
    });
  }

  /** Đổi ngôn ngữ. `veLai` do `tai-xe.js` gắn vào — vẽ lại cả phần JS sinh ra. */
  function datNgonNgu(moi) {
    if (!CHU[moi] || moi === ma) return;
    ma = moi;
    try { localStorage.setItem(LUU, ma); } catch (e) { /* bỏ qua */ }
    veNhanTinh();
    if (typeof window.veLaiTheoNgonNgu === 'function') window.veLaiTheoNgonNgu();
  }

  window.T = T;
  window.ngonNgu = ngonNgu;
  window.datNgonNgu = datNgonNgu;
  window.veNhanTinh = veNhanTinh;
  window.DANH_SACH_NGON_NGU = ['vi', 'en', 'lo'].map(function (k) {
    return { ma: k, ten: CHU[k].ten_ngon_ngu };
  });
})();

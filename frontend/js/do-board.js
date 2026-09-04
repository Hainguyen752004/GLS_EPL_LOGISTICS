/**
 * Phân loại Lệnh giao hàng (DO) cho màn lập kế hoạch.
 *
 * Ba vấn đề của bản cũ, tìm được khi đối chiếu với dữ liệu thật:
 *
 *   1. Tab mặc định là "Gần trễ" và nó đang có **0 DO**, nên mở màn ra là một
 *      bảng trống — trong khi 9 DO thật nằm ở các tab khác. Người dùng phải tự
 *      đoán là phải bấm sang tab nào.
 *
 *   2. "Gần trễ" gộp *sắp tới hạn* với *đã quá hạn* vào một rổ. Một DO quá hạn
 *      ba tuần và một DO tới hạn chiều nay là hai mức cấp bách hoàn toàn khác
 *      nhau; gộp lại thì không ai biết phải làm gì trước.
 *
 *   3. Ba DO "Chờ vận chuyển" trong cơ sở dữ liệu **không có ngày nào cả** —
 *      `pickup_window_start`, `pickup_date`, `delivery_date` đều rỗng. Bản cũ
 *      lấy `created_at` làm hạn giao thay thế, tức **bịa ra một hạn không tồn
 *      tại**: ngày tạo phiếu không phải ngày phải giao. Hệ quả là DO thiếu hạn
 *      bị trộn lẫn vào "Chờ vận chuyển" và không ai thấy nó thiếu, dù nó không
 *      lập kế hoạch được và cũng không đo trễ được.
 *
 * Module thuần: không đọc DOM, không gọi mạng.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  }
  root.DoBoard = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const DAY = 24 * 60 * 60 * 1000;

  /**
   * Các rổ, xếp theo MỨC CẤP BÁCH giảm dần.
   *
   * Thứ tự này quyết định tab nào được mở sẵn: rổ cấp bách nhất mà **có dòng**.
   * Bản cũ mở cứng "Gần trễ" nên gặp bảng trống.
   */
  const BUCKETS = [
    { key: 'incident', label: 'Gặp sự cố', hint: 'Có sự cố chưa xử lý', icon: 'fa-circle-exclamation', tone: 'danger' },
    { key: 'overdue', label: 'Đã quá hạn', hint: 'Quá hạn giao, cần xử lý ngay', icon: 'fa-clock-rotate-left', tone: 'danger' },
    { key: 'undated', label: 'Thiếu hạn giao', hint: 'Chưa có ngày lấy/giao nên không lập kế hoạch được', icon: 'fa-calendar-xmark', tone: 'warning' },
    { key: 'due_soon', label: 'Sắp tới hạn', hint: 'Tới hạn trong 24 giờ tới', icon: 'fa-hourglass-half', tone: 'warning' },
    { key: 'pending', label: 'Chờ vận chuyển', hint: 'Đã có hạn, chờ điều phối xe', icon: 'fa-calendar-check', tone: 'info' },
    { key: 'active', label: 'Đang vận chuyển', hint: 'Xe đã nhận lệnh và đang chạy', icon: 'fa-truck-fast', tone: 'info' },
    { key: 'completed', label: 'Hoàn thành', hint: 'Đã có POD ghi nhận', icon: 'fa-circle-check', tone: 'ok' },
  ];

  function normalizeKey(value) {
    return String(value || '')
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .replace(/đ/gi, 'd')
      .toLowerCase()
      .trim()
      .replace(/\s+/g, '_');
  }

  /**
   * Hạn giao THẬT của một DO, hoặc null nếu chưa có.
   *
   * Cố ý KHÔNG lấy `created_at` làm hạn thay thế: ngày tạo phiếu không phải
   * ngày phải giao. Lấy nó là bịa ra một hạn không tồn tại, rồi mọi con số
   * "trễ" tính từ đó đều sai.
   */
  function dueAt(order) {
    const candidates = [
      order?.delivery_window_end,
      order?.delivery_date,
      order?.delivery_window_start,
      order?.pickup_window_start,
      order?.pickup_date,
    ];
    for (const candidate of candidates) {
      const time = Date.parse(candidate || '');
      if (!Number.isNaN(time)) return time;
    }
    return null;
  }

  /** Rổ của một DO. `now` truyền vào được để kiểm chứng. */
  function bucketOf(order, now = Date.now()) {
    const key = normalizeKey(order?.canonical_status || order?.status);

    if (['incident', 'issue', 'exception', 'problem', 'gap_su_co', 'su_co'].includes(key)) return 'incident';
    if (['delivered', 'completed', 'settled', 'posted', 'da_giao', 'hoan_thanh', 'hoan_tat'].includes(key)) return 'completed';
    if (['dispatched', 'in_transit', 'arrived', 'dang_van_chuyen', 'da_den_noi'].includes(key)) return 'active';

    // Còn lại là chưa lên đường. Lúc này hạn giao mới có ý nghĩa.
    const due = dueAt(order);
    if (due === null) return 'undated';
    if (due < now) return 'overdue';
    if (due <= now + DAY) return 'due_soon';
    return 'pending';
  }

  /** Đếm từng rổ. Rổ nào không có DO nào vẫn xuất hiện với số 0. */
  function counts(orders, now = Date.now()) {
    const result = {};
    BUCKETS.forEach(bucket => { result[bucket.key] = 0; });
    (orders || []).forEach(order => {
      const key = bucketOf(order, now);
      result[key] = (result[key] || 0) + 1;
    });
    return result;
  }

  /**
   * Rổ nên mở sẵn: rổ cấp bách nhất mà CÓ DÒNG.
   *
   * Nếu không rổ nào có dòng thì trả về rổ cuối, để màn hình vẫn có tab được
   * chọn thay vì không tab nào.
   */
  function defaultBucket(orders, now = Date.now()) {
    const tally = counts(orders, now);
    const found = BUCKETS.find(bucket => tally[bucket.key] > 0);
    return found ? found.key : BUCKETS[BUCKETS.length - 1].key;
  }

  /** Số ngày quá hạn (số dương) hoặc còn lại (số âm). null nếu chưa có hạn. */
  function daysLate(order, now = Date.now()) {
    const due = dueAt(order);
    if (due === null) return null;
    return Math.floor((now - due) / DAY);
  }

  function filter(orders, bucket, now = Date.now()) {
    return (orders || []).filter(order => bucketOf(order, now) === bucket);
  }

  /**
   * Xếp trong một rổ: việc gấp nhất lên trước.
   *
   * Luôn TĂNG DẦN theo hạn giao — vì cả hai nghĩa đều trỏ tới hạn nhỏ nhất:
   * trong rổ quá hạn thì "quá hạn lâu nhất" là hạn cũ nhất, còn ở các rổ chưa
   * tới hạn thì "tới hạn sờm nhất" cũng là hạn gần nhất.
   *
   * DO chưa có hạn xếp theo mã cho ổn định, và luôn đẩy xuống cuối ở các rổ
   * khác — không có hạn thì không xếp thứ tự cấp bách được.
   */
  function sortWithin(orders, bucket, now = Date.now()) {
    const rows = [...(orders || [])];
    if (bucket === 'undated') {
      return rows.sort((a, b) => String(a?.id || '').localeCompare(String(b?.id || '')));
    }
    return rows.sort((a, b) => {
      const left = dueAt(a);
      const right = dueAt(b);
      if (left === null && right === null) return String(a?.id || '').localeCompare(String(b?.id || ''));
      if (left === null) return 1;
      if (right === null) return -1;
      return left - right;
    });
  }

  return { DAY, BUCKETS, normalizeKey, dueAt, bucketOf, counts, defaultBucket, daysLate, filter, sortWithin };
});

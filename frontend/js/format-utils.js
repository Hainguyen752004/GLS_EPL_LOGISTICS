/**
 * Các hàm định dạng dùng chung: escape, tiền, ngày giờ.
 *
 * Tách ra khỏi app.js (15.000+ dòng) vì cùng một việc đang được viết lại nhiều
 * lần dưới những cái tên khác nhau — và các bản sao đã trôi khỏi nhau, sinh ra
 * hai lỗi thật:
 *
 * 1. escapeRouteCheckpointText dùng `|| ''` thay vì `?? ''`, nên giá trị số 0
 *    bị biến thành chuỗi rỗng, trong khi escapeVehicleHtml và
 *    escapeCloseoutText cùng cảnh trả về "0".
 *
 * 2. financeMasterDateInput thiếu bước bù múi giờ mà ba hàm ngày khác đều có,
 *    nên với UTC+7 nó trả SAI NGÀY cho mọi thời điểm trước 07:00 sáng:
 *    2026-01-01T00:00:00 hiện thành 2025-12-31. Hàm này dùng cho ngày bắt đầu
 *    kỳ kế toán, nên lệch một ngày ở đó là lệch biên kỳ.
 *
 * Đây là lý do gộp các bản sao lại đáng làm: nó không chỉ gọn code mà còn phơi
 * ra chỗ đã sai.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) {
    root.FormatUtils = api;
    // Phơi ra tên toàn cục để app.js dùng trực tiếp, và để các hàm cũ uỷ quyền
    // sang đây thay vì tự viết lại.
    root.escapeHtml = api.escapeHtml;
    root.escapeJsAttr = api.escapeJsAttr;
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  /** Escape HTML. Dùng ?? nên số 0 vẫn ra "0", không thành chuỗi rỗng. */
  function escapeHtml(value) {
    if (value === null || value === undefined) return '';
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  /**
   * Escape cho giá trị nằm trong chuỗi JavaScript bên trong thuộc tính HTML,
   * ví dụ onclick="editDriverById('GIÁ_TRỊ')".
   *
   * Chỉ escapeHtml là KHÔNG đủ: trình duyệt giải mã thực thể HTML trong giá trị
   * thuộc tính TRƯỚC khi đọc phần còn lại như JavaScript, nên &#39; quay lại
   * thành dấu nháy và thoát khỏi chuỗi. Phải escape hai lớp: JS trước, HTML sau.
   */
  function escapeJsAttr(value) {
    if (value === null || value === undefined) return '';
    const jsEscaped = String(value)
      .replace(/\\/g, '\\\\')
      .replace(/'/g, "\\'")
      .replace(/\r/g, '\\r')
      .replace(/\n/g, '\\n');
    return escapeHtml(jsEscaped);
  }

  /** Định dạng tiền theo locale Việt Nam. Thiếu mã tiền thì mặc định VND. */
  function formatMoney(value, currency) {
    const amount = Number(value || 0);
    return `${amount.toLocaleString('vi-VN')} ${currency || 'VND'}`;
  }

  /**
   * Chuỗi ISO theo giờ ĐỊA PHƯƠNG, cắt tới độ dài yêu cầu.
   *
   * Bước bù getTimezoneOffset() là phần bắt buộc: toISOString() trả về giờ UTC,
   * nên với UTC+7 mọi thời điểm trước 07:00 sáng sẽ rơi về ngày hôm trước.
   */
  function localIsoSlice(value, length) {
    const date = value === undefined || value === null ? new Date() : new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, length);
  }

  /** yyyy-mm-dd theo giờ địa phương — dùng cho <input type="date">. */
  function dateInputValue(value) {
    return localIsoSlice(value, 10);
  }

  /** yyyy-mm-ddThh:mm theo giờ địa phương — dùng cho <input type="datetime-local">. */
  function dateTimeInputValue(value) {
    return localIsoSlice(value, 16);
  }

  /** Ghép ngày với mốc đầu hoặc cuối ngày, giữ nguyên chuỗi ngày đã có. */
  function dayBoundary(dateValue, endOfDay) {
    if (!dateValue) return '';
    return `${dateValue}${endOfDay ? 'T23:59:59' : 'T00:00:00'}`;
  }

  return {
    escapeHtml,
    escapeJsAttr,
    formatMoney,
    localIsoSlice,
    dateInputValue,
    dateTimeInputValue,
    dayBoundary,
  };
});

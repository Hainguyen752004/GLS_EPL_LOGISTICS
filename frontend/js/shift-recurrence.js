/**
 * Lịch ca lặp theo tuần — phần tính toán.
 *
 * Vì sao tách ra file riêng: hộp thoại cũ ("Thiết lập lịch làm việc mặc định")
 * hỏi người dùng 10 câu rồi im lặng ghi khoảng 78 ca thật vào cơ sở dữ liệu mà
 * KHÔNG hề nói trước là sẽ ghi bao nhiêu ca, cho ai, ngày nào. Phần dễ sai nhất
 * chính là phép đếm đó, nên nó phải nằm ở chỗ kiểm chứng được bằng Node.
 *
 * Module này thuần: không đọc DOM, không gọi mạng.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  }
  root.ShiftRecurrence = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  /** Backend chỉ nhận tối đa 366 ngày cho một khoảng áp dụng. */
  const MAX_RANGE_DAYS = 366;

  const WEEKDAYS = [
    { index: 0, short: 'T2', label: 'Thứ Hai' },
    { index: 1, short: 'T3', label: 'Thứ Ba' },
    { index: 2, short: 'T4', label: 'Thứ Tư' },
    { index: 3, short: 'T5', label: 'Thứ Năm' },
    { index: 4, short: 'T6', label: 'Thứ Sáu' },
    { index: 5, short: 'T7', label: 'Thứ Bảy' },
    { index: 6, short: 'CN', label: 'Chủ Nhật' },
  ];

  /**
   * Giờ ca lấy đúng theo js/driver-roster.js để hai chỗ không nói hai kiểu.
   *
   * Bản cũ để "Giờ bắt đầu / Giờ kết thúc" và "Loại ca" thành hai ô rời nhau,
   * nên đặt được 06:00–14:00 mà vẫn gắn nhãn "Ca đêm" — không có gì đối chiếu.
   * Nay loại ca QUYẾT ĐỊNH giờ; muốn giờ khác thì chọn "Tùy chỉnh".
   */
  const SHIFT_PRESETS = [
    { key: 'morning', label: 'Ca sáng', start: '06:00', end: '14:00' },
    { key: 'afternoon', label: 'Ca chiều', start: '14:00', end: '22:00' },
    { key: 'night', label: 'Ca đêm', start: '22:00', end: '06:00' },
    { key: 'custom', label: 'Tùy chỉnh', start: '', end: '' },
  ];

  function preset(key) {
    return SHIFT_PRESETS.find(item => item.key === key) || null;
  }

  function toMinutes(time) {
    const match = /^(\d{1,2}):(\d{2})$/.exec(String(time || '').trim());
    if (!match) return null;
    const hours = Number(match[1]);
    const minutes = Number(match[2]);
    if (hours > 23 || minutes > 59) return null;
    return hours * 60 + minutes;
  }

  /**
   * Ca qua đêm được SUY RA từ giờ, không hỏi người dùng.
   *
   * Bản cũ có ô "Kết thúc sau: Trong ngày / 1 ngày / ..." rồi phải viết thêm
   * một đoạn giải thích ở cuối hộp thoại. Máy tự biết 22:00 → 06:00 là qua đêm;
   * bắt người dùng khai lại chỉ tạo thêm chỗ để sai.
   */
  function derivedEndDayOffset(startTime, endTime) {
    const start = toMinutes(startTime);
    const end = toMinutes(endTime);
    if (start === null || end === null) return 0;
    return end <= start ? 1 : 0;
  }

  /** Độ dài một ca, tính bằng phút — đã tính cả phần qua đêm. */
  function shiftMinutes(startTime, endTime, endDayOffset) {
    const start = toMinutes(startTime);
    const end = toMinutes(endTime);
    if (start === null || end === null) return 0;
    const offset = endDayOffset === undefined || endDayOffset === null
      ? derivedEndDayOffset(startTime, endTime)
      : Number(endDayOffset) || 0;
    return end - start + offset * 24 * 60;
  }

  function parseDateKey(value) {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value || '').trim());
    if (!match) return null;
    // Dựng theo giờ địa phương, không qua Date.parse: chuỗi "YYYY-MM-DD" được
    // hiểu là UTC nên ở múi giờ Việt Nam sẽ lùi mất một ngày.
    const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
    return Number.isFinite(date.getTime()) ? date : null;
  }

  function dateKey(date) {
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${date.getFullYear()}-${month}-${day}`;
  }

  /** Thứ trong tuần theo quy ước Thứ Hai = 0, khớp với backend. */
  function weekdayIndex(date) {
    return (date.getDay() + 6) % 7;
  }

  /**
   * Liệt kê những NGÀY THẬT sẽ sinh ca, thay vì chỉ nói "lặp theo tuần".
   *
   * Đây là con số người dùng cần thấy trước khi bấm lưu: một khoảng 3 tháng với
   * 6 ngày mỗi tuần là khoảng 78 ca, không phải "một lịch".
   */
  function expandRecurrence(options) {
    const weekdays = [...new Set((options && options.weekdays) || [])]
      .map(Number)
      .filter(value => Number.isInteger(value) && value >= 0 && value <= 6);
    const start = parseDateKey(options && options.effectiveStart);
    const end = parseDateKey(options && options.effectiveEnd);
    if (!weekdays.length || !start || !end || start > end) return [];

    const span = Math.round((end - start) / 86400000) + 1;
    if (span > MAX_RANGE_DAYS) return [];

    const keys = [];
    const cursor = new Date(start);
    while (cursor <= end) {
      if (weekdays.includes(weekdayIndex(cursor))) keys.push(dateKey(cursor));
      cursor.setDate(cursor.getDate() + 1);
    }
    return keys;
  }

  /**
   * Những ca đã có sẵn của một người trong các ngày sắp sinh.
   *
   * Backend dùng mã ca tự sinh theo (người, ngày, giờ) nên bấm lưu hai lần với
   * cùng thiết lập thì GHI ĐÈ, không nhân đôi. Nhưng đổi giờ đi một phút rồi
   * lưu lại thì thành hai ca chồng nhau — đó là lúc cần cảnh báo.
   */
  function existingOverlaps(driverId, dateKeys, existingShifts) {
    const wanted = new Set(dateKeys);
    return (existingShifts || []).filter(shift => {
      if (!shift || String(shift.driver_id) !== String(driverId)) return false;
      if (String(shift.status || '') === 'cancelled') return false;
      const key = String(shift.shift_start || '').slice(0, 10);
      return wanted.has(key);
    }).length;
  }

  /**
   * Toàn bộ những gì hộp thoại cần biết TRƯỚC khi ghi vào cơ sở dữ liệu.
   *
   * Trả về cả `errors` để nút lưu tự khóa lại, thay vì để người dùng bấm rồi
   * mới nhận một dòng thông báo đỏ như bản cũ.
   */
  function planRecurrence(options) {
    const settings = options || {};
    const driverIds = [...new Set((settings.driverIds || []).map(id => String(id || '').trim()).filter(Boolean))];
    const startTime = String(settings.startTime || '').trim();
    const endTime = String(settings.endTime || '').trim();
    const endDayOffset = settings.endDayOffset === undefined || settings.endDayOffset === null
      ? derivedEndDayOffset(startTime, endTime)
      : Number(settings.endDayOffset) || 0;
    const dates = expandRecurrence(settings);
    const minutes = shiftMinutes(startTime, endTime, endDayOffset);

    const errors = [];
    if (!driverIds.length) errors.push('Chọn ít nhất một nhân sự.');
    if (!((settings.weekdays || []).length)) errors.push('Chọn ít nhất một ngày trong tuần.');
    if (toMinutes(startTime) === null || toMinutes(endTime) === null) {
      errors.push('Nhập giờ bắt đầu và giờ kết thúc.');
    } else if (minutes <= 0) {
      errors.push('Giờ kết thúc phải sau giờ bắt đầu.');
    }
    const start = parseDateKey(settings.effectiveStart);
    const end = parseDateKey(settings.effectiveEnd);
    if (!start || !end) {
      errors.push('Chọn khoảng ngày áp dụng.');
    } else if (start > end) {
      errors.push('Ngày kết thúc phải sau ngày bắt đầu.');
    } else if (Math.round((end - start) / 86400000) + 1 > MAX_RANGE_DAYS) {
      errors.push(`Khoảng áp dụng không được quá ${MAX_RANGE_DAYS} ngày.`);
    } else if (!dates.length) {
      errors.push('Không có ngày nào khớp: khoảng ngày áp dụng không chứa ngày trong tuần đã chọn.');
    }

    const perDriver = driverIds.map(id => ({
      driverId: id,
      shiftCount: dates.length,
      existingCount: existingOverlaps(id, dates, settings.existingShifts),
    }));

    return {
      driverIds,
      dates,
      perDriver,
      startTime,
      endTime,
      endDayOffset,
      shiftMinutes: minutes,
      crossesMidnight: endDayOffset > 0,
      totalShifts: dates.length * driverIds.length,
      existingShifts: perDriver.reduce((sum, item) => sum + item.existingCount, 0),
      errors,
      valid: errors.length === 0,
    };
  }

  function plural(count, word) {
    return `${count} ${word}`;
  }

  /** "2026-09-01" -> "01/09/2026", đúng thứ tự người Việt đọc ngày. */
  function viDate(key) {
    const parts = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(key || ''));
    return parts ? `${parts[3]}/${parts[2]}/${parts[1]}` : String(key || '');
  }

  /**
   * Câu tóm tắt hiện ngay trên nút lưu và trong khung xem trước.
   *
   * Mục đích duy nhất: người dùng đọc được "sẽ ghi bao nhiêu ca, cho bao nhiêu
   * người" trước khi bấm — điều bản cũ không hề nói.
   */
  function summarize(plan) {
    if (!plan || !plan.valid) return { headline: 'Chưa đủ thông tin để tạo ca', detail: '' };
    const people = plan.driverIds.length;
    const headline = `Sẽ tạo ${plural(plan.totalShifts, 'ca làm việc')}`;
    const hours = Math.round(plan.shiftMinutes / 6) / 10;
    const detail = [
      `${plural(people, 'nhân sự')} × ${plural(plan.dates.length, 'ngày')}`,
      `${plan.startTime} – ${plan.endTime}${plan.crossesMidnight ? ' (qua đêm)' : ''}`,
      `${hours} giờ mỗi ca`,
      `${viDate(plan.dates[0])} → ${viDate(plan.dates[plan.dates.length - 1])}`,
    ].join(' · ');
    return { headline, detail };
  }

  return {
    MAX_RANGE_DAYS,
    WEEKDAYS,
    SHIFT_PRESETS,
    preset,
    toMinutes,
    derivedEndDayOffset,
    shiftMinutes,
    viDate,
    expandRecurrence,
    existingOverlaps,
    planRecurrence,
    summarize,
  };
});

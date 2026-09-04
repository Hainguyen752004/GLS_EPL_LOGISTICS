/**
 * Công thức giá thành ĐỘNG — mô hình biểu thức.
 *
 * Chủ dự án cần đổi được cách tính: thêm/bớt cấu phần, đổi dấu, đổi hệ số nhân.
 *
 * Vì sao KHÔNG dùng lại trình dựng biểu thức kéo thả tự do (bản cũ, đã bị ẩn
 * bằng display:none từ lâu): nó cho phép dựng ra công thức **sai thứ nguyên** mà
 * không có gì kiểm được — nhân cước theo kg với số km chẳng hạn — và người dùng
 * chỉ phát hiện khi báo giá đã gửi cho khách.
 *
 * Mô hình ở đây vẫn động nhưng có cấu trúc: công thức là một danh sách **hạng
 * tử**, mỗi hạng tử gồm
 *
 *     dấu (+ hoặc −)  ·  đơn giá  ·  hệ số nhân (mỗi km / mỗi kg / ... )
 *
 * Thêm được hạng tử mới, xóa, đổi thứ tự, đổi dấu, đổi hệ số. Và vì hệ số là
 * một lựa chọn có tên chứ không phải một biểu thức tự do, nên luôn kiểm được
 * đơn vị: mỗi đơn giá khai mình tính theo gì, lệch là báo ngay.
 *
 * Module thuần: không đọc DOM, không gọi mạng.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  }
  root.FormulaModel = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  /**
   * Các hệ số nhân dùng được.
   *
   * `unit` là đơn vị mà một đơn giá PHẢI có để dùng hệ số này. Đây là chỗ chặn
   * công thức sai thứ nguyên.
   */
  const FACTORS = {
    per_km: { label: 'mỗi km', short: '× số km', unit: '/km', of: trip => trip.km },
    per_kg: { label: 'mỗi kg hàng', short: '× số kg', unit: '/kg', of: trip => trip.tonnes * 1000 },
    per_tonne: { label: 'mỗi tấn hàng', short: '× số tấn', unit: '/tấn', of: trip => trip.tonnes },
    per_trip: { label: 'mỗi chuyến', short: '× 1 chuyến', unit: '/chuyến', of: () => 1 },
    per_stop: { label: 'mỗi điểm giao', short: '× số điểm', unit: '/điểm', of: trip => trip.stops },
  };

  const OPERATORS = {
    add: { label: 'Cộng', sign: '+', factor: 1 },
    sub: { label: 'Trừ', sign: '−', factor: -1 },
  };

  /** Chuyến mẫu mặc định. Mọi con số tổng đều là ước tính cho một chuyến. */
  const DEFAULT_TRIP = { km: 200, tonnes: 15, stops: 1 };

  function toNumber(value) {
    if (value === null || value === undefined || value === '') return 0;
    const parsed = Number(String(value).replace(/[,\s]/g, ''));
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function normalizeTrip(trip) {
    const source = trip || {};
    const km = toNumber(source.km);
    const stops = toNumber(source.stops);
    return {
      // 0 km là vô nghĩa nên quay về mẫu; 0 tấn thì GIỮ, vì chuyến chạy rỗng
      // là có thật và lúc đó phần cước theo kg đúng là bằng 0.
      km: km > 0 ? km : DEFAULT_TRIP.km,
      tonnes: 'tonnes' in source ? Math.max(0, toNumber(source.tonnes)) : DEFAULT_TRIP.tonnes,
      stops: stops > 0 ? stops : DEFAULT_TRIP.stops,
    };
  }

  /** Một hạng tử đã được làm sạch. Trả về null nếu không dùng được. */
  function normalizeTerm(term, index) {
    if (!term || typeof term !== 'object') return null;
    const factor = FACTORS[term.factor] ? term.factor : 'per_trip';
    const operator = OPERATORS[term.operator] ? term.operator : 'add';
    const key = String(term.key || '').trim() || `term_${index + 1}`;
    return {
      key,
      label: String(term.label || key).trim().slice(0, 120),
      operator,
      factor,
      rate: Math.max(0, toNumber(term.rate)),
      // Cấu phần dựng sẵn thì không cho xóa, để công thức không bị rỗng ruột.
      builtin: Boolean(term.builtin),
    };
  }

  function normalize(terms) {
    return (Array.isArray(terms) ? terms : [])
      .map(normalizeTerm)
      .filter(Boolean)
      .slice(0, 30);
  }

  /**
   * Tính một chuyến mẫu, bóc tách từng hạng tử.
   *
   * Không dùng eval hay Function: biểu thức là một danh sách hạng tử cộng/trừ
   * nên chỉ cần cộng dồn. Không có đường nào để một chuỗi từ người dùng chạy
   * thành mã.
   */
  function evaluate(terms, trip) {
    const sample = normalizeTrip(trip);
    const rows = normalize(terms).map(term => {
      const factor = FACTORS[term.factor];
      const multiplier = factor.of(sample);
      const signed = OPERATORS[term.operator].factor;
      return {
        ...term,
        multiplier,
        unit: factor.unit,
        factorLabel: factor.short,
        sign: OPERATORS[term.operator].sign,
        amount: signed * term.rate * multiplier,
      };
    });
    const total = rows.reduce((sum, row) => sum + row.amount, 0);
    return {
      trip: sample,
      rows,
      total,
      perKm: sample.km ? total / sample.km : 0,
      configured: rows.some(row => row.rate > 0),
    };
  }

  /**
   * Công thức viết ra thành chữ, sinh từ chính các hạng tử.
   *
   * Bản trước là một chuỗi viết cứng, nên sửa công thức xong nó vẫn đọc y như
   * cũ — một kiểu nói dối nữa.
   */
  function toText(terms) {
    const rows = normalize(terms);
    if (!rows.length) return 'Chưa có cấu phần nào';
    return rows.map((term, index) => {
      const factor = FACTORS[term.factor];
      const piece = term.factor === 'per_trip'
        ? term.label
        : `(${term.label} ${factor.short})`;
      if (index === 0) return term.operator === 'sub' ? `− ${piece}` : piece;
      return `${OPERATORS[term.operator].sign} ${piece}`;
    }).join(' ');
  }

  /**
   * Những chỗ công thức tự mâu thuẫn.
   *
   * Đây là thứ mà trình dựng biểu thức tự do không làm được, và cũng là lý do
   * chọn mô hình hạng tử: mỗi hạng tử khai rõ mình tính theo gì nên kiểm được.
   */
  function problems(terms) {
    const rows = normalize(terms);
    const issues = [];
    if (!rows.length) {
      issues.push({ level: 'error', message: 'Công thức chưa có cấu phần nào.' });
      return issues;
    }
    const seen = new Map();
    rows.forEach(term => {
      if (seen.has(term.key)) {
        issues.push({ level: 'error', key: term.key, message: `Cấu phần "${term.label}" bị khai hai lần.` });
      }
      seen.set(term.key, true);
      if (!term.rate) {
        issues.push({ level: 'warn', key: term.key, message: `"${term.label}" đang để 0 nên không góp gì vào tổng.` });
      }
      // Nhãn nói /kg mà hệ số lại là mỗi km (hoặc ngược lại) — đúng loại sai
      // thứ nguyên đã gây ra chuyện điền số xăng dầu vào ô cước phí.
      const declared = /\/\s*(km|kg|t[ấa]n|chuy[ếe]n|đi[ểe]m)/i.exec(term.label || '');
      if (declared) {
        const expected = FACTORS[term.factor].unit.replace('/', '').toLowerCase();
        const found = declared[1].toLowerCase().replace('a', 'ấ').replace('e', 'ế');
        if (!expected.startsWith(found.slice(0, 2))) {
          issues.push({
            level: 'error',
            key: term.key,
            message: `"${term.label}" ghi đơn vị /${declared[1]} nhưng đang nhân theo ${FACTORS[term.factor].label}.`,
          });
        }
      }
    });
    if (rows.every(term => !term.rate)) {
      issues.push({ level: 'error', message: 'Mọi cấu phần đều bằng 0 nên tổng luôn bằng 0.' });
    }
    return issues;
  }

  /** Năm cấu phần dựng sẵn, khớp với các ô đã có trên màn hình. */
  function defaultTerms() {
    return [
      { key: 'fuel', label: 'Chi phí xăng dầu /km', operator: 'add', factor: 'per_km', rate: 0, builtin: true },
      { key: 'driver', label: 'Phụ cấp chuyến tài xế', operator: 'add', factor: 'per_trip', rate: 0, builtin: true },
      { key: 'toll', label: 'Phí cầu đường / BOT', operator: 'add', factor: 'per_trip', rate: 0, builtin: true },
      { key: 'wh', label: 'Phí bãi & lưu kho', operator: 'add', factor: 'per_trip', rate: 0, builtin: true },
      { key: 'rate', label: 'Cước phí vận chuyển /kg', operator: 'add', factor: 'per_kg', rate: 0, builtin: true },
    ];
  }

  /** Di chuyển một hạng tử lên/xuống. Trả về mảng mới. */
  function move(terms, index, delta) {
    const rows = normalize(terms);
    const target = index + delta;
    if (index < 0 || index >= rows.length || target < 0 || target >= rows.length) return rows;
    const copy = [...rows];
    [copy[index], copy[target]] = [copy[target], copy[index]];
    return copy;
  }

  return {
    FACTORS, OPERATORS, DEFAULT_TRIP,
    toNumber, normalizeTrip, normalize, evaluate, toText, problems, defaultTerms, move,
  };
});

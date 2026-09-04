/**
 * Ước tính chi phí một chuyến từ công thức giá thành.
 *
 * Vì sao cần một "chuyến mẫu": năm cấu phần chi phí có **đơn vị khác nhau** —
 * xăng dầu tính trên 1 km, phụ cấp và phí BOT tính trên 1 chuyến, cước phí tính
 * trên 1 kg hàng. Không thể cộng thẳng chúng lại thành một con số "tổng" nếu
 * chưa biết chuyến đó đi bao nhiêu km và chở bao nhiêu hàng.
 *
 * Nên "tổng" ở đây luôn là **ước tính cho một chuyến mẫu**, và màn hình phải
 * nói rõ chuyến mẫu đó là bao nhiêu km / bao nhiêu tấn. Đưa ra một con số tổng
 * mà không nói giả định thì lại là một con số nói dối nữa.
 *
 * Module thuần: không đọc DOM, không gọi mạng.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  }
  root.CostEstimate = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  /** Chuyến mẫu mặc định: 200 km, 15 tấn — cỡ một chuyến liên tỉnh thường gặp. */
  const DEFAULT_TRIP = { km: 200, tonnes: 15 };

  /**
   * Năm cấu phần, kèm cách mỗi cấu phần góp vào tổng.
   *
   * `basis` nói rõ con số nhân với cái gì — đây chính là thông tin mà bảng cũ
   * thiếu, khiến người dùng không biết vì sao cộng ra được tổng.
   */
  const COMPONENTS = [
    { key: 'fuel', label: 'Chi phí xăng dầu', basis: 'per_km', unit: '/km', icon: 'fa-gas-pump' },
    { key: 'driver', label: 'Phụ cấp chuyến tài xế', basis: 'per_trip', unit: '/chuyến', icon: 'fa-user-gear' },
    { key: 'toll', label: 'Phí cầu đường / BOT', basis: 'per_trip', unit: '/chuyến', icon: 'fa-road-barrier' },
    { key: 'wh', label: 'Phí bãi & lưu kho', basis: 'per_trip', unit: '/chuyến', icon: 'fa-warehouse' },
    { key: 'rate', label: 'Cước phí vận chuyển', basis: 'per_kg', unit: '/kg', icon: 'fa-weight-hanging' },
  ];

  function toNumber(value) {
    if (value === null || value === undefined || value === '') return 0;
    const cleaned = String(value).replace(/[,\s]/g, '');
    const parsed = Number(cleaned);
    return Number.isFinite(parsed) && parsed >= 0 ? parsed : 0;
  }

  function normalizeTrip(trip) {
    const km = toNumber((trip || {}).km) || DEFAULT_TRIP.km;
    const tonnes = toNumber((trip || {}).tonnes);
    // Khối lượng ĐƯỢC PHÉP bằng 0 — chuyến chạy rỗng là có thật, và lúc đó
    // phần cước theo kg đúng là bằng 0. Riêng quãng đường 0 km thì vô nghĩa
    // nên quay về mẫu mặc định.
    return { km, tonnes: tonnes || (trip && 'tonnes' in trip ? 0 : DEFAULT_TRIP.tonnes) };
  }

  /** Số nhân của một cấu phần trong chuyến mẫu. */
  function multiplier(basis, trip) {
    if (basis === 'per_km') return trip.km;
    if (basis === 'per_kg') return trip.tonnes * 1000;
    return 1;
  }

  /**
   * Bóc tách chi phí một chuyến mẫu thành từng dòng, kèm tổng.
   *
   * `values` là bảng đơn giá đã cấu hình: { fuel, driver, toll, wh, rate }.
   */
  function estimate(values, trip) {
    const sample = normalizeTrip(trip);
    const lines = COMPONENTS.map(component => {
      const rate = toNumber((values || {})[component.key]);
      const times = multiplier(component.basis, sample);
      return {
        key: component.key,
        label: component.label,
        icon: component.icon,
        unit: component.unit,
        basis: component.basis,
        rate,
        multiplier: times,
        amount: rate * times,
      };
    });
    return {
      trip: sample,
      lines,
      total: lines.reduce((sum, line) => sum + line.amount, 0),
      // Chi phí trên mỗi km — con so sánh được giữa các loại xe, khác với
      // tổng vốn phụ thuộc độ dài chuyến mẫu.
      perKm: sample.km ? lines.reduce((sum, line) => sum + line.amount, 0) / sample.km : 0,
      configured: COMPONENTS.some(component => toNumber((values || {})[component.key]) > 0),
    };
  }

  /**
   * Công thức viết ra thành chữ, để người dùng đọc được cách ra con số.
   *
   * Bản cũ là một trình dựng biểu thức bằng thẻ kéo thả — mạnh nhưng dễ dựng ra
   * công thức sai mà không ai kiểm được. Ở đây công thức là cố định và đúng
   * theo đơn vị của từng cấu phần; thứ người dùng đổi là các ĐƠN GIÁ.
   */
  function formulaText() {
    return '(Xăng dầu × số km) + Phụ cấp tài xế + Phí BOT + Phí bãi + (Cước × số kg)';
  }

  return { DEFAULT_TRIP, COMPONENTS, toNumber, normalizeTrip, multiplier, estimate, formulaText };
});

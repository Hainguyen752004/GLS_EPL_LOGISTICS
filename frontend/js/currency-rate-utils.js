(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.CurrencyRateUtils = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
  function parseCurrencyRateNumber(value) {
    const raw = String(value ?? '').trim().replace(/\s/g, '').replace(/[^\d.,+-]/g, '');
    if (!raw || !/\d/.test(raw)) return NaN;

    const dot = raw.lastIndexOf('.');
    const comma = raw.lastIndexOf(',');
    let normalized = raw;

    if (dot >= 0 && comma >= 0) {
      const decimalSeparator = dot > comma ? '.' : ',';
      const groupingSeparator = decimalSeparator === '.' ? ',' : '.';
      normalized = raw.split(groupingSeparator).join('').replace(decimalSeparator, '.');
    } else {
      const separator = dot >= 0 ? '.' : (comma >= 0 ? ',' : '');
      if (separator) {
        const parts = raw.split(separator);
        const grouped = parts.length > 2
          ? parts.slice(1).every(part => part.length === 3)
          : parts[1]?.length === 3;
        normalized = grouped ? parts.join('') : `${parts[0]}.${parts.slice(1).join('')}`;
      }
    }

    const parsed = Number(normalized);
    return Number.isFinite(parsed) ? parsed : NaN;
  }

  function convertVndByRate(amount, rate) {
    const amountValue = parseCurrencyRateNumber(amount);
    const rateValue = parseCurrencyRateNumber(rate);
    if (!Number.isFinite(amountValue) || !Number.isFinite(rateValue) || rateValue <= 0) return NaN;
    return Number((amountValue / rateValue).toFixed(2));
  }

  function formatCurrencyRateNumber(value, maximumFractionDigits = 6) {
    const parsed = typeof value === 'number' ? value : parseCurrencyRateNumber(value);
    if (!Number.isFinite(parsed)) return '-';
    return parsed.toLocaleString('vi-VN', { maximumFractionDigits });
  }

  return { parseCurrencyRateNumber, convertVndByRate, formatCurrencyRateNumber };
});

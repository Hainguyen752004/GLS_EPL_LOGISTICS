/**
 * Giá gốc của DO đọc theo BÁO GIÁ, không còn từ vựng "SO" trên hai màn.
 * Chủ dự án chỉ: "Xem DO" hiện 0 VNĐ (đọc SO), màn Hoàn tất còn "SO nguồn", "Theo SO".
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');

// 1. Nguồn giá của khối quyết toán trong "Xem DO": báo giá trước, rồi unit_price của DO. SO đã trục xuất.
{
  const i = app.indexOf('function setDOSettlementFromSource(source = {})');
  const t = app.slice(i, app.indexOf('window.setDOSettlementFromSource', i));
  assert.ok(/const bg = baoGiaCuaDO\(source\)/.test(t), 'phải tra báo giá của DO');
  assert.ok(/\(bg && bg\.selling_price\) \|\| source\.unit_price/.test(t) && !/findSalesOrderForDO/.test(t), 'thứ tự: báo giá → unit_price, không còn SO');
  assert.ok(/\(bg && bg\.currency_code\) \|\| 'VND'/.test(t), 'tiền tệ theo báo giá trước');
  assert.ok(/Theo báo giá \$\{bg\.id\}/.test(t) && !/Theo SO/.test(t), 'nhãn nguồn là báo giá');
}

// 2. Không còn từ vựng SO trên màn Xem DO và Hoàn tất.
['Theo SO', 'SO nguồn', 'View DO ban đầu', 'Giữ giá hợp đồng đã chốt từ SO', 'Giá hợp đồng ban đầu'].forEach(tu => {
  assert.ok(!app.includes(tu), 'app.js còn "' + tu + '"');
  assert.ok(!html.includes(tu), 'index.html còn "' + tu + '"');
});
assert.ok(/\['Báo giá nguồn', closeout\.quotation_id \|\| row\.order\.quotation_id/.test(app));
assert.ok(/Theo báo giá: \$\{completionMoney\(base, currency\)\}/.test(app));
assert.ok(/id="completion-base-price-badge">Theo báo giá</.test(html));

console.log('gia-goc-theo-bao-gia-khong-so: OK');

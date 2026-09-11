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

// 1b. CHẠY THẬT hàm điền cước với nguồn rỗng và nguồn có báo giá — không được ném lỗi.
//     Đo 11/09: còn một vết `so.id` (biến của bước SO đã bỏ) trong nhánh nhãn nguồn →
//     ReferenceError ngay lúc `moKhungFormDO()` gọi `setDOSettlementFromSource({})`,
//     TRƯỚC khi lệnh tắt spinner được đặt: form "Xem DO" treo "Đang chuẩn bị form DO...",
//     mọi ô trống, 0 VNĐ ở mọi DO. Bài kiểm quét chữ không bắt được vì `so.id` là mã hợp lệ.
{
  const i = app.indexOf('function baoGiaCuaDO(source)');
  const j = app.indexOf('window.setDOSettlementFromSource', i);
  const than = app.slice(i, j);
  assert.ok(!/\bso\.[a-z_]+/.test(than), 'còn tham chiếu biến `so` đã bỏ trong khối điền cước');
  const cacO = {};
  const o = id => (cacO[id] ||= { value: '', textContent: '', dataset: {}, innerHTML: '' });
  const goi = [];
  const chay = new Function('document', 'crmQuotations', 'appState', 'renderDOSettlementLines',
    'refreshDOSettlementTotals', 'formatWorkflowCurrencyAmount', 'window',
    than + '\nreturn setDOSettlementFromSource;');
  const ham = chay({ getElementById: o }, [{ id: 'QT-1', selling_price: 2486000, currency_code: 'VND' }], {},
    x => goi.push(x), () => {}, (n, c) => `${n} ${c}`, {});
  assert.doesNotThrow(() => ham({}), 'nguồn rỗng (lúc mở khung) phải chạy được');
  assert.strictEqual(o('do-settlement-source-badge').textContent, 'Theo báo giá');
  assert.doesNotThrow(() => ham({ quotation_id: 'QT-1', unit_price: 2486000 }));
  assert.strictEqual(o('do-settlement-source-badge').textContent, 'Theo báo giá QT-1');
  assert.strictEqual(o('do-original-contract-amount-display').value, '2486000 VND', 'cước theo báo giá phải hiện, không 0');
  assert.doesNotThrow(() => ham({ quotation_id: 'QT-KHONG-TRONG-BO-NHO', unit_price: 1000 }));
  assert.strictEqual(o('do-settlement-source-badge').textContent, 'Theo báo giá QT-KHONG-TRONG-BO-NHO');
  assert.strictEqual(o('do-original-contract-amount-display').value, '1000 VND', 'không có báo giá trong bộ nhớ thì lấy unit_price của DO');
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

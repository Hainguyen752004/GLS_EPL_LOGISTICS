/**
 * Ước tính chi phí một chuyến từ công thức giá thành.
 *
 * Vì sao phải có "chuyến mẫu": năm cấu phần có **đơn vị khác nhau** — xăng dầu
 * tính trên 1 km, phụ cấp và phí BOT tính trên 1 chuyến, cước phí tính trên
 * 1 kg. Không cộng thẳng được thành một con số "tổng" nếu chưa biết chuyến đó
 * đi bao nhiêu km và chở bao nhiêu hàng.
 *
 * Nên mọi con số tổng đều là ước tính cho một chuyến mẫu, và màn hình phải nói
 * rõ giả định đó. Đưa ra một con số tổng mà giấu giả định thì lại là một con số
 * nói dối nữa — đúng loại lỗi đã dọn suốt dự án này.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const frontendRoot = path.join(__dirname, '..');
const CE = require(path.join(frontendRoot, 'js', 'cost-estimate.js'));
const app = fs.readFileSync(path.join(frontendRoot, 'js', 'app.js'), 'utf8');
const html = fs.readFileSync(path.join(frontendRoot, 'index.html'), 'utf8');

const RATES = { fuel: 4800, driver: 400000, toll: 150000, wh: 100000, rate: 1200 };

// --- 1. Mỗi cấu phần nhân với đúng thứ của nó ------------------------------

{
  const result = CE.estimate(RATES, { km: 200, tonnes: 15 });
  const byKey = Object.fromEntries(result.lines.map(line => [line.key, line]));

  assert.strictEqual(byKey.fuel.multiplier, 200, 'xăng dầu nhân với số km');
  assert.strictEqual(byKey.fuel.amount, 4800 * 200);

  assert.strictEqual(byKey.driver.multiplier, 1, 'phụ cấp tính một lần cho cả chuyến');
  assert.strictEqual(byKey.toll.multiplier, 1);
  assert.strictEqual(byKey.wh.multiplier, 1);

  // 15 tấn = 15.000 kg. Nhầm tấn với kg ở đây là sai 1.000 lần.
  assert.strictEqual(byKey.rate.multiplier, 15000, 'cước phí nhân với số KG, không phải số tấn');
  assert.strictEqual(byKey.rate.amount, 1200 * 15000);

  assert.strictEqual(result.total, 960000 + 400000 + 150000 + 100000 + 18000000);
  assert.strictEqual(result.perKm, result.total / 200);
}

// --- 2. Chuyến mẫu ---------------------------------------------------------

assert.deepStrictEqual(CE.DEFAULT_TRIP, { km: 200, tonnes: 15 });
assert.deepStrictEqual(CE.normalizeTrip(), CE.DEFAULT_TRIP, 'không truyền gì thì dùng mẫu mặc định');
assert.deepStrictEqual(CE.normalizeTrip({ km: 0 }), CE.DEFAULT_TRIP, '0 km là vô nghĩa, quay về mặc định');

// Chuyến chạy rỗng LÀ CÓ THẬT: 0 tấn phải được giữ nguyên, không bị thay bằng
// mẫu mặc định — nếu thay, màn hình sẽ tính cước cho hàng không tồn tại.
{
  const empty = CE.normalizeTrip({ km: 120, tonnes: 0 });
  assert.deepStrictEqual(empty, { km: 120, tonnes: 0 });
  const result = CE.estimate(RATES, empty);
  const rateLine = result.lines.find(line => line.key === 'rate');
  assert.strictEqual(rateLine.amount, 0, 'chạy rỗng thì không có cước theo kg');
  assert.strictEqual(result.total, 4800 * 120 + 400000 + 150000 + 100000);
}

// --- 3. Đơn giá bẩn không được làm vỡ phép tính ----------------------------

assert.strictEqual(CE.toNumber('4,800'), 4800, 'phải bỏ được dấu phân cách nghìn');
assert.strictEqual(CE.toNumber(' 1 200 '), 1200);
[null, undefined, '', 'không phải số', -5, NaN, Infinity].forEach(value => {
  assert.strictEqual(CE.toNumber(value), 0, `giá trị bẩn phải thành 0: ${String(value)}`);
});
{
  const result = CE.estimate({ fuel: 'abc', driver: null, toll: -1 }, { km: 100, tonnes: 1 });
  assert.strictEqual(result.total, 0);
  assert.strictEqual(result.configured, false, 'chưa có đơn giá nào thì phải nói là chưa cấu hình');
}
assert.strictEqual(CE.estimate({ fuel: 1 }).configured, true);
assert.strictEqual(CE.estimate(null).total, 0, 'không có gì cũng không được vỡ');

// --- 4. Công thức viết ra thành chữ ----------------------------------------

{
  const text = CE.formulaText();
  ['Xăng dầu', 'số km', 'Phụ cấp', 'BOT', 'Cước', 'số kg'].forEach(part => {
    assert.ok(text.includes(part), `công thức phải nhắc "${part}"`);
  });
}

// --- 5. Giao diện --------------------------------------------------------

assert.match(html, /js\/cost-estimate\.js/, 'index.html phải nạp module');
assert.ok(
  html.indexOf('js/cost-estimate.js') < html.indexOf('js/app.js?v='),
  'cost-estimate.js phải nạp trước app.js'
);
assert.match(html, /id="cost-formula-view"/, 'phải có khung hiển thị công thức');
// Khung công thức phải nằm NGOÀI cột trái 320px, nếu không bảng bị bóp lại.
{
  const panel = html.indexOf('id="vehicle-cost-panel"');
  const leftColumn = html.indexOf('Left Types List');
  const rightColumn = html.indexOf('Right Table');
  assert.ok(panel > rightColumn && rightColumn > leftColumn,
    'bảng giá thành từng xe phải nằm sau cả hai cột, không nằm trong cột trái');
}

{
  const start = app.indexOf('window.renderCostFormulaView = function');
  assert.ok(start > 0, 'phải có hàm vẽ công thức');
  const fn = app.slice(start, app.indexOf(String.fromCharCode(10) + '};', start));
  assert.match(fn, /Tổng chi phí chuyến mẫu/, 'phải có dòng tổng');
  assert.match(fn, /Bình quân mỗi km/, 'phải có con số so sánh được giữa các loại xe');
  // Giả định phải hiện ra ngay cạnh con số, không giấu đi.
  assert.match(fn, /costSampleTrip\.km/);
  assert.match(fn, /costSampleTrip\.tonnes/);
  assert.match(fn, /masterCostCurrencyCode\(\)/, 'phải theo đơn vị tiền tệ đang chọn');
}

// Đổi ô đơn giá thì tổng phải cập nhật ngay.
assert.match(html, /onCostComponentInput\(\)/, 'ô đơn giá phải nối vào khối công thức');
assert.strictEqual(
  (html.match(/onCostComponentInput\(\)/g) || []).length, 5,
  'cả năm ô đơn giá đều phải nối'
);

console.log('cost-estimate: tất cả kiểm tra đã qua');

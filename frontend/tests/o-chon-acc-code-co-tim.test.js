/**
 * Ô chọn Acc code CÓ TÌM — danh mục thật của bên công nợ có ~500 tài khoản kế
 * toán Lào (4 cấp, tên dài); một <select> 500 dòng không ai cuộn được. Chủ dự án:
 * "anh biết nó dài nên em xem có cách nào thiết kế lại".
 *
 * Khoá: ô hiện MÃ đậm + tên ngắn; bấm mở bảng có ô tìm theo mã/tên/diễn giải,
 * lọc "chi tiết" (postable) mặc định bật, Enter chọn dòng đầu, Esc đóng, bấm
 * ngoài đóng, có nút Bỏ mã; chưa nối API thì ô ở trạng thái chờ và bị khoá.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8');
const css = fs.readFileSync(path.join(ROOT, 'css', 'cost-formula-v2.css'), 'utf8');

const than = (neo, ket) => { const i = app.indexOf(neo); assert.ok(i >= 0, 'không thấy ' + neo); const j = ket ? app.indexOf(ket, i) : -1; return app.slice(i, j > 0 ? j : i + 6000); };

// 1. Ô chọn không còn là <select>; hiện mã + tên; chờ API thì khoá.
{
  const o = than('function oChonAccCode(index, row)', 'window.renderCostFormulaEditor = function');
  assert.ok(!/<select class=/.test(o), 'không còn <select> 500 dòng');
  assert.ok(/class="cfv2-acc cfv2-acc-cho" disabled/.test(o), 'chưa có danh mục thì ô khoá, ghi rõ đang chờ');
  assert.ok(/onclick="moBangChonAccCode\(\$\{index\}, this\)"/.test(o));
  assert.ok(/<b>\$\{escapeHtml\(hienTai \|\| '—'\)\}<\/b><small>/.test(o), 'mã đậm, tên nhỏ bên dưới');
  assert.ok(/cfv2-acc-la/.test(o), 'mã đã lưu nhưng không còn trong danh mục phải được đánh dấu, không xoá');
}

// 2. Bảng chọn: tìm theo mã/tên/diễn giải, lọc chi tiết, phím tắt, bỏ mã.
{
  const b = than('window.moBangChonAccCode = function (index, nut)', 'function dongBangChonAccCode()');
  assert.ok(/id="cfv2-acc-tim"/.test(b) && /type="search"/.test(b));
  assert.ok(/id="cfv2-acc-post" checked/.test(b), 'lọc tài khoản hạch toán được bật mặc định');
  assert.ok(/String\(x\.code\)\.toLowerCase\(\)\.startsWith\(q\)/.test(b), 'mã tìm theo tiền tố');
  assert.ok(/x\.description \|\| ''\)\.toLowerCase\(\)\.includes\(q\)/.test(b), 'tìm cả diễn giải tiếng Việt');
  assert.ok(/slice\(0, 80\)/.test(b), 'chỉ vẽ 80 dòng đầu, gõ thêm để lọc');
  assert.ok(/ev\.key === 'Escape'/.test(b) && /ev\.key === 'Enter'/.test(b));
  assert.ok(/setCostTermField\(index, 'cost_index', ma\)/.test(b), 'chọn xong ghi vào cost_index của đúng dòng');
  assert.ok(/cfv2-acc-bo/.test(b) && /chon\(''\)/.test(b), 'có nút Bỏ mã');
  assert.ok(/document\.addEventListener\('mousedown', dongNeuNgoai, true\)/.test(b), 'bấm ngoài thì đóng');
}

// 3. Bảng chọn KHÔNG nằm trong lát của bong bóng công thức (test khác cấm gắn listener ở đó).
assert.ok(app.indexOf('window.moBangChonAccCode = function') > app.indexOf('window.renderCostFormulaEditor = function'));

// 4. CSS.
['.cfv2-acc-pop', '.cfv2-acc-row', '.cfv2-acc.cfv2-acc-cho', '.cfv2-acc-pop-hd input[type="search"]'].forEach(k =>
  assert.ok(css.includes(k), 'thiếu CSS ' + k));

console.log('o-chon-acc-code-co-tim: OK');

/**
 * Màn Công thức giá thành: ba cột, và chuyến mẫu sửa được NGAY trên thẻ.
 *
 * Hai chỗ bài kiểm này giữ:
 *
 *   1. Cặp km/tấn của chuyến mẫu phải nằm trên thẻ, không nằm trong hộp thoại
 *      sửa công thức. Bản cũ chỉ có nó bên trong hộp thoại, còn màn chính ghi
 *      "ước tính một chuyến mẫu 200 km · 15 tấn" như một câu chú thích — nên
 *      muốn thử "cùng tuyến này nhưng 30 tấn thì lãi bao nhiêu" thì phải mở một
 *      hộp thoại nghe như sắp đổi cấu hình, trong khi người dùng chỉ muốn xem.
 *
 *   2. Ba con số kết quả phải nằm ở KHUNG PHẢI, không nằm ở chân bảng cấu phần.
 *      Ở chân bảng chúng đọc như tổng của bảng — mà "cước thu khách" không phải
 *      một dòng chi phí được cộng lại, nó là tiền THU về. Và tuyệt đối không
 *      được có một con số gộp cả năm cấu phần: cộng chi phí với doanh thu thì
 *      ra một số không phải giá thành cũng không phải giá bán.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const NL = String.fromCharCode(10);
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8')
  .split(String.fromCharCode(13)).join('');

const iVe = app.indexOf('window.renderCostFormulaEditor = function ()');
assert.ok(iVe > 0, 'không thấy trình vẽ khung công thức');
const the = app.slice(iVe, app.indexOf('renderCostFormulaPopover(result, money)', iVe));

// --- 1. Ba cột ---------------------------------------------------------

{
  assert.ok(/class="cf-shell"/.test(the), 'thiếu khung hai cột .cf-shell');
  assert.ok(/class="cf-main"/.test(the), 'thiếu cột nội dung .cf-main');
  assert.ok(/class="cf-side"/.test(the), 'thiếu cột chuyến mẫu .cf-side');

  // Phần trình bày phải có thật, không thì hai cột nằm chồng lên nhau.
  const css = html.replace(/\/\*[\s\S]*?\*\//g, ' ');
  assert.ok(/\.cf-shell\s*\{[^}]*grid-template-columns/.test(css),
    '.cf-shell phải chia cột bằng grid');
  // Màn hẹp phải về một cột — 300px cộng bảng cấu phần không vừa màn 1180px.
  const i = css.indexOf('@media (max-width:1180px)');
  assert.ok(i > 0, 'thiếu quy tắc cho màn hẹp');
  assert.ok(/\.cf-shell\s*\{\s*grid-template-columns:minmax\(0,1fr\)/.test(css.slice(i, i + 400)),
    'màn hẹp phải về một cột');
}

// --- 2. Chuyến mẫu sửa được trên thẻ -----------------------------------

{
  assert.ok(/setCostSampleTrip\('km'/.test(the),
    'ô km phải nằm trên thẻ, ngoài hộp thoại sửa công thức');
  assert.ok(/setCostSampleTrip\('tonnes'/.test(the),
    'ô tấn phải nằm trên thẻ, ngoài hộp thoại sửa công thức');
  // Phải nói rõ đổi hai số này KHÔNG ảnh hưởng báo giá thật, không thì người
  // dùng tưởng mình vừa sửa giá của khách.
  assert.ok(/không ảnh hưởng báo giá/i.test(the),
    'phải nói rõ chuyến mẫu không ảnh hưởng báo giá thật');

  // Đổi chuyến mẫu phải tính lại CẢ các thẻ loại xe bên trái, không thì hai
  // chỗ trên cùng màn hình nói hai con số khác nhau.
  const j = app.indexOf('window.setCostSampleTrip = function');
  const than = app.slice(j, app.indexOf(NL + '};', j));
  assert.ok(/updateCostFormulaTotals\(\)/.test(than), 'phải cập nhật lại kết quả');
  assert.ok(/renderDynamicFormulaVehicleTypes\(\)/.test(than),
    'phải tính lại các thẻ loại xe bên trái');
  // Nhưng KHÔNG được vẽ lại chính khung công thức: vẽ lại là mất con trỏ giữa
  // lúc đang gõ số.
  assert.ok(!/renderCostFormulaEditor\(\)/.test(than),
    'không được vẽ lại khung công thức khi đang gõ — mất con trỏ');
}

// --- 3. Ba con số ở khung phải, và không có số gộp ---------------------

{
  const iSide = the.indexOf('class="cf-side"');
  assert.ok(iSide > 0);
  const khungPhai = the.slice(iSide);
  ['cf-cost', 'cf-revenue', 'cf-total', 'cf-margin', 'cf-perkm', 'cf-trip-note'].forEach(ma => {
    assert.ok(khungPhai.includes(`id="${ma}"`),
      `#${ma} phải nằm trong khung phải`);
  });

  // Chân bảng cấu phần không còn giữ ba con số đó.
  const iBang = the.indexOf('<table class="cf-table">');
  const bang = the.slice(iBang, the.indexOf('</table>', iBang));
  assert.ok(!/tfoot/.test(bang),
    'chân bảng cấu phần không được giữ lại ba con số — chúng đã sang khung phải');

  // Nhãn phải nói rõ loại tiền.
  assert.ok(/tiền CHI ra/.test(khungPhai), 'giá thành phải nói rõ là tiền CHI ra');
  assert.ok(/tiền THU về/.test(khungPhai), 'cước phải nói rõ là tiền THU về');
  // Và tuyệt đối không có một con số gộp cả chi phí lẫn doanh thu.
  assert.ok(!/Tổng chi phí chuyến|Tổng cộng tất cả/.test(the),
    'không được có con số gộp chi phí với doanh thu');
}

// --- 4. Không còn tiêu đề trùng với tầng 3 -----------------------------

{
  ['title_cost_formula_mgmt', 'desc_cost_formula_mgmt'].forEach(khoa => {
    assert.ok(!html.includes(khoa),
      `index.html còn khóa "${khoa}" — tiêu đề đó trùng với tầng 3`);
  });
  const lang = JSON.parse(fs.readFileSync(path.join(ROOT, 'js', 'lang.json'), 'utf8'));
  ['title_cost_formula_mgmt', 'desc_cost_formula_mgmt'].forEach(khoa => {
    assert.ok(!lang[khoa], `lang.json còn khóa chết "${khoa}"`);
  });
  assert.ok(!/Quản Lý Công Thức Giá Thành Theo Loại Xe/.test(html),
    'index.html còn tiêu đề trùng với tầng 3');
}

console.log('gia-thanh-ba-cot: ba cột, chuyến mẫu sửa được trên thẻ, ba con số ở khung phải');

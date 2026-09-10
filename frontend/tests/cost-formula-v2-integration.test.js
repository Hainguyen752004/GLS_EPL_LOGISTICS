const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8');

function blockBetween(source, startText, endText) {
  const start = source.indexOf(startText);
  assert.ok(start >= 0, `khong tim thay ${startText}`);
  const end = source.indexOf(endText, start);
  assert.ok(end > start, `khong tim thay diem ket thuc ${endText}`);
  return source.slice(start, end);
}

const formulasTab = blockBetween(html, 'id="md-tab-formulas"', '<!-- TAB 3: VEHICLE TYPES');

assert.match(formulasTab, /class="cfv2-shell"/, 'man Cong thuc gia thanh phai dung layout v2');
assert.match(formulasTab, /id="formula-vehicle-types-list"/, 'danh muc loai xe phai do JS nap tu backend');
assert.match(formulasTab, /id="cost-formula-view"/, 'khung cong thuc phai con de JS ve tu du lieu that');
assert.match(formulasTab, /id="vehicle-cost-panel"/, 'phai con tang gia rieng tung xe');
assert.match(formulasTab, /id="md-cost-currency"[^>]*onchange="onMasterCostCurrencyChange\(\)"/,
  'bo chon tien te phai hien tren UI va goi logic doi tien te');
assert.match(formulasTab, /onclick="saveCostFormula\(\)"/,
  'nut luu phai goi ham luu that, khong phai nut mau');
assert.doesNotMatch(formulasTab, /<div style="background: #ffffff; border-radius: 12px;[^>]*>\s*<\/div>/,
  'khong duoc con khung trang rong lam lech UI');

assert.match(html, /\.cfv2-shell\s*\{[^}]*grid-template-columns/,
  'layout v2 phai co CSS chia cot that');
assert.match(html, /\.cfv2-workbench\s*\{[^}]*min-height:640px/,
  'vung lam viec phai co chieu cao on dinh, khong bi rong/le ngang');

const saveFn = blockBetween(app, 'window.saveCostFormula = async function ()', '\n};');
assert.match(saveFn, /freight_rate:\s*rateInput/,
  'frontend phai gui freight_rate ve backend de API/bao gia cu van doc duoc');
assert.match(saveFn, /fetch\(`\$\{API_BASE\}\/api\/cost-formulas`/,
  'luu cong thuc phai di qua API that');
assert.match(saveFn, /if\s*\(!response\.ok\)[\s\S]*return false/,
  'luu that bai phai bao that bai, khong duoc thong bao thanh cong gia');

console.log('cost-formula-v2-integration: UI v2 va API luu that da duoc rang buoc');

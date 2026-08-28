const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'frontend', 'index.html'), 'utf8');
const js = fs.readFileSync(path.join(root, 'frontend', 'js', 'app.js'), 'utf8');

function assert(condition, message) {
  if (!condition) {
    console.error(`FAIL: ${message}`);
    process.exitCode = 1;
  }
}

assert(!html.includes('id="btn-approve-do"'), 'DO detail must not render an approve button');
assert(!html.includes('id="btn-save-do-form"'), 'DO detail must not render a save-DO button');
assert(!html.includes('Duyệt Lệnh'), 'DO detail must not display the approve command');
assert(!html.includes('Lưu Lệnh DO'), 'DO detail must not display the save-DO command');
assert(html.includes('id="btn-add-do-settlement-line"'), 'settlement must expose an add-cost button');
assert(html.includes('Thêm khoản phí'), 'add-cost button must use clear business wording');
assert(html.includes('Số tiền phát sinh'), 'settlement table must accept one user-entered amount');
assert(!html.includes('Giá ban đầu</th>'), 'settlement table must not ask for an original line amount');
assert(!html.includes('Giá tăng / thực tế'), 'settlement table must not ask for an actual line amount');
assert(!html.includes('Tăng thêm</th>'), 'settlement table must not calculate a line delta');

assert(js.includes('do-settlement-amount'), 'settlement rows must use a single amount input');
assert(!js.includes('do-settlement-original'), 'old original amount input must be removed');
assert(!js.includes('do-settlement-actual'), 'old actual amount input must be removed');
assert(!js.includes('do-settlement-delta'), 'old delta display must be removed');
assert(js.includes("renderDOSettlementLines([])"), 'a new DO must start with an empty cost list');
assert(js.includes("const amount = parseWorkflowMoneyValue(row.querySelector('.do-settlement-amount')"), 'totals must sum the user-entered amount');

if (!process.exitCode) {
  console.log('DO_SETTLEMENT_UI_OK');
}

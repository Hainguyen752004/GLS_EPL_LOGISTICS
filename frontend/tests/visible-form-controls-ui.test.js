const assert = require('assert');
const fs = require('fs');
const path = require('path');

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');

// Trinh dung bieu thuc bang the keo tha da duoc thay bang cong thuc VIET RA
// THANH CHU. Ban cu con cho phep dung ra cong thuc sai don vi (nhan cuoc theo
// kg voi so km chang han) ma khong co gi kiem duoc; va no da bi an bang
// display:none tu lau nen nguoi dung khong con thay cong thuc dau ca.
//
// Y dinh can giu: cong thuc phai HIEN RA va doc duoc, khong bi an.
assert.match(html, /id="cost-formula-view"/, 'Cong thuc gia thanh phai co khung hien thi.');
assert.ok(
  !/appendFormulaToken/.test(html),
  'Khong duoc quay lai trinh dung bieu thuc keo tha — no dung duoc cong thuc sai don vi.'
);
{
  const block = /<section id="cost-formula-view"[^>]*>/.exec(html);
  assert.ok(block, 'phai tim thay khung cong thuc');
  assert.ok(!/display:\s*none/.test(block[0]), 'Khung cong thuc khong duoc bi an.');
}
assert.match(html, /Thêm Khách Hàng Mới/, 'Customer create button must keep the full Vietnamese label.');

console.log('VISIBLE_FORM_CONTROLS_UI_OK');

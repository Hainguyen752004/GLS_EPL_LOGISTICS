/* Kiểm giao diện: cú pháp JS, đủ khoá dịch, và bốn chế độ ngôn ngữ chạy đúng.
 *
 * Chạy: node frontend/tests/kiem-giao-dien.js
 */
'use strict';

const fs = require('fs');
const path = require('path');

const GOC = path.join(__dirname, '..');
let loi = [];

function kiem(dieu_kien, nhan) {
  if (dieu_kien) console.log('  OK   ' + nhan);
  else { console.log('  FAIL ' + nhan); loi.push(nhan); }
}

/* -------------------------------------------------------------- cú pháp JS */
console.log('\n[1] Cú pháp mọi tệp JS');
const tepJS = [
  'js/khung.js',
  'modules/don-hang/don-hang.js',
  'modules/packing-list/packing-list.js',
  'modules/giao-hang/giao-hang.js',
  'modules/quet-tem/quet-tem.js',
  'modules/khach-hang/khach-hang.js',
  'modules/theo-doi/theo-doi.js',
  'modules/tuyen-duong/tuyen-duong.js',
];
for (const tep of tepJS) {
  try {
    new Function(fs.readFileSync(path.join(GOC, tep), 'utf8'));
    kiem(true, tep);
  } catch (e) {
    kiem(false, tep + ' — ' + e.message);
  }
}

/* -------------------------------------------------- khoá dịch dùng trong HTML */
console.log('\n[2] Mọi khoá data-i18n trong HTML đều có trong lang.json');
const tuDien = JSON.parse(fs.readFileSync(path.join(GOC, 'lang.json'), 'utf8'));
const tepHTML = [
  'index.html',
  'modules/don-hang/don-hang.html',
  'modules/packing-list/packing-list.html',
  'modules/giao-hang/giao-hang.html',
  'modules/quet-tem/quet-tem.html',
  'modules/khach-hang/khach-hang.html',
  'modules/theo-doi/theo-doi.html',
  'modules/tuyen-duong/tuyen-duong.html',
];
let thieu = [];
for (const tep of tepHTML) {
  const chu = fs.readFileSync(path.join(GOC, tep), 'utf8');
  const re = /data-i18n(?:-ph|-title)?="([^"]+)"/g;
  let m;
  while ((m = re.exec(chu))) {
    if (!tuDien[m[1]]) thieu.push(tep + ' → ' + m[1]);
  }
}
kiem(thieu.length === 0, 'không có khoá lạ' + (thieu.length ? ' — thiếu: ' + thieu.join(', ') : ''));

console.log('\n[3] Khoá dùng trong JS cũng phải có');
let thieuJS = [];
for (const tep of tepJS) {
  const chu = fs.readFileSync(path.join(GOC, tep), 'utf8');
  const re = /\b(?:t|mot|oChu)\(\s*'([a-z][a-z0-9_]+)'/g;
  let m;
  while ((m = re.exec(chu))) {
    const k = m[1];
    // Bỏ qua các khoá ghép động: 'pack_status_' + x, 'err_' + ma
    if (/_$/.test(k)) continue;
    if (!tuDien[k]) thieuJS.push(tep + ' → ' + k);
  }
}
kiem(thieuJS.length === 0, 'không có khoá lạ trong JS' + (thieuJS.length ? ' — thiếu: ' + thieuJS.join(', ') : ''));

/* --------------------------------------------------------- bốn chế độ ngôn ngữ */
console.log('\n[4] Bốn chế độ: vi / en / lo / vi+lo');
const khung = fs.readFileSync(path.join(GOC, 'js', 'khung.js'), 'utf8');

// Rút hàm t() ra chạy thử, không chép lại logic.
const bd = khung.indexOf('function t(khoa, macDinh)');
const kt = khung.indexOf('function apDungNgonNgu');
const doan = khung.slice(bd, kt);
const taoT = new Function('tuDien', 'ngonNgu', doan + '\n return t;');

for (const che_do of ['vi', 'en', 'lo', 'both']) {
  const t = taoT(tuDien, che_do);
  const chu = t('nav_packing');
  if (che_do === 'both') {
    const p = t('so_title').split('\n');
    kiem(p.length === 2 && p[0] && p[1], 'chế độ both trả hai dòng Việt + Lào');
    kiem(p[0] === tuDien.so_title.vi && p[1] === tuDien.so_title.lo, 'both ghép đúng bản vi và lo');
  } else {
    kiem(chu === tuDien.nav_packing[che_do], 'chế độ ' + che_do + ' trả đúng bản dịch');
  }
}

console.log('\n[5] Khoá trạng thái phải đủ cho mọi giá trị máy chủ trả về');
const canCo = []
  .concat(['new', 'packing', 'packed', 'delivering', 'delivered', 'cancelled'].map(x => 'so_status_' + x))
  .concat(['ready', 'parked', 'gate_in', 'loaded', 'dispatched', 'delivered', 'cancelled'].map(x => 'pack_status_' + x))
  .concat(['planned', 'loading', 'in_transit', 'arrived', 'delivered', 'cancelled'].map(x => 'dl_status_' + x))
  .concat(['full', 'short', 'failed', 'returned'].map(x => 'pod_result_' + x))
  .concat(['customer', 'vendor', 'depot'].map(x => 'kh_kind_' + x));
const thieuTT = canCo.filter(k => !tuDien[k]);
kiem(thieuTT.length === 0, 'đủ nhãn trạng thái' + (thieuTT.length ? ' — thiếu: ' + thieuTT.join(', ') : ''));

console.log('\n' + '='.repeat(60));
if (loi.length) {
  console.log('CÓ ' + loi.length + ' MỤC HỎNG:');
  loi.forEach(x => console.log('  - ' + x));
  process.exit(1);
}
console.log('GIAO DIỆN: CÚ PHÁP, KHOÁ DỊCH VÀ BỐN CHẾ ĐỘ ĐỀU ĐÚNG');
process.exit(0);

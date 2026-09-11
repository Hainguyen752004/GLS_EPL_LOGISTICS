/**
 * QUAY LẠI — nút quay lại và lịch sử trình duyệt cho mọi màn.
 *
 * Chủ dự án (12/09/2026): *"UI UX của toàn dự án khi ấn vào tính năng gì đó không có nút quay
 * về có phải hong nè"*. Đo lại: đúng — ứng dụng có 10 màn và KHÔNG một dòng
 * `pushState`/`popstate` nào, nên trình duyệt coi cả ứng dụng là MỘT trang. Bấm nút Back (hay
 * vuốt lùi trên điện thoại) là thoát hẳn khỏi ứng dụng, không phải lùi một màn; chỉ hai màn
 * có một nút "Quay lại Dashboard" chắp tay, tám màn còn lại không có đường lùi nào.
 *
 * Bài này CHẠY THẬT phần lịch sử trong jsdom, vì cái dễ hỏng là hành vi chứ không phải chữ:
 *  1. Đổi màn → đẩy mốc vào lịch sử, địa chỉ mang `#mã-màn` (F5 vẫn ở đúng màn).
 *  2. Mở lại CHÍNH màn đang xem → KHÔNG đẩy mốc (nếu không, bấm hai lần vào một mục menu là
 *     phải bấm Back hai lần mới ra — đúng kiểu lỗi làm người dùng tưởng treo).
 *  3. Bấm Back → mở lại màn trước, và KHÔNG đẩy thêm mốc mới (nếu không thì lùi mãi không ra).
 *  4. Nút "Quay lại" ẩn khi chưa đi đâu — một nút quay lại không lùi được là một nút nói dối.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const { JSDOM } = require(path.join(ROOT, 'node_modules', 'jsdom'));
const ma = fs.readFileSync(path.join(ROOT, 'js', 'khung-moi.js'), 'utf8')
  .split(String.fromCharCode(13)).join('');

/* ---- Bóc ba hàm lịch sử ra chạy độc lập, kèm các biến trạng thái của chúng ---- */
function boc(ten) {
  const i = ma.indexOf('function ' + ten + '(');
  assert.ok(i > 0, 'không thấy ' + ten);
  return ma.slice(i, ma.indexOf(String.fromCharCode(10) + '  }', i) + 4);
}
const dom = new JSDOM(
  '<body><div class="epl-sub" id="epl-sub"><div><h1 id="epl-h1"></h1></div></div></body>',
  { url: 'http://localhost/' });
const w = dom.window;
const daMo = [];
w.switchView = function (man, scroll) { daMo.push([man, scroll || null]); return true; };

// Truyền thẳng `window/document/location/history` của jsdom vào: mã gốc dùng chúng như biến
// toàn cục của trình duyệt, và jsdom không dựng sẵn phạm vi đó cho hàm tạo ngoài realm.
const nap = new Function('T', 'window', 'document', 'location', 'history', `
  let manHienTai = '';
  let soBuocDaDay = 0;
  let dangLuiLai = false;
  ${boc('veNutQuayLai')}
  ${boc('ganLichSuMan')}
  ${boc('ghiLichSu')}
  return { veNutQuayLai, ganLichSuMan, ghiLichSu,
           doc: () => ({ manHienTai, soBuocDaDay, dangLuiLai }) };
`);
const H = nap((k, md) => md, w, w.document, w.location, w.history);
H.ganLichSuMan();

const nut = () => w.document.getElementById('epl-quay-lai');

/* 1. Chưa đi đâu: chưa có nút (chỉ dựng khi có màn đầu tiên). */
assert.strictEqual(nut(), null);

/* 2. Màn đầu tiên → replaceState, KHÔNG tạo mốc mới, nút vẫn ẩn. */
H.ghiLichSu('dashboard');
assert.strictEqual(w.location.hash, '#dashboard');
assert.strictEqual(H.doc().soBuocDaDay, 0, 'màn đầu tiên không được tính là một bước lùi');
assert.ok(nut(), 'phải dựng nút quay lại');
assert.strictEqual(nut().hidden, true, 'chưa đi đâu thì nút phải ẩn');
assert.match(nut().textContent, /Quay lại/);
assert.strictEqual(w.document.getElementById('epl-sub').firstChild, nut(),
  'nút quay lại phải đứng đầu dải tiêu đề, trước tên màn');

/* 3. Đổi màn → đẩy mốc, hiện nút. */
H.ghiLichSu('ops-planning', 'fiori-do-list');
assert.strictEqual(w.location.hash, '#ops-planning');
assert.strictEqual(H.doc().soBuocDaDay, 1);
assert.strictEqual(nut().hidden, false, 'đã đi một màn thì nút phải hiện');
assert.deepStrictEqual(w.history.state, { eplMan: 'ops-planning', eplScroll: 'fiori-do-list' },
  'phải nhớ cả chỗ cuộn, để lùi về đúng vị trí đang xem');

/* 4. Mở LẠI chính màn đang xem → không đẩy thêm mốc. */
H.ghiLichSu('ops-planning');
assert.strictEqual(H.doc().soBuocDaDay, 1, 'mở lại màn đang xem mà vẫn đẩy mốc');

H.ghiLichSu('tracking');
assert.strictEqual(H.doc().soBuocDaDay, 2);

/* 5. Bấm Back → mở lại màn trước, KHÔNG đẩy mốc mới, và trừ đúng một bước. */
daMo.length = 0;
w.dispatchEvent(new w.PopStateEvent('popstate',
  { bubbles: true, state: { eplMan: 'ops-planning', eplScroll: 'fiori-do-list' } }));
assert.deepStrictEqual(daMo, [['ops-planning', 'fiori-do-list']], 'Back phải mở lại màn trước');
assert.strictEqual(H.doc().soBuocDaDay, 1, 'Back phải trừ một bước, không cộng thêm');

/* 6. Back về tới màn đầu → nút ẩn lại. */
w.dispatchEvent(new w.PopStateEvent('popstate', { bubbles: true, state: { eplMan: 'dashboard' } }));
assert.strictEqual(H.doc().soBuocDaDay, 0);
assert.strictEqual(nut().hidden, true, 'về tới màn đầu thì nút phải ẩn lại');

/* 7. Back khi trình duyệt không gửi state (vào thẳng bằng đường dẫn) → đọc từ địa chỉ. */
daMo.length = 0;
w.history.replaceState(null, '', '#master-data');
w.dispatchEvent(new w.PopStateEvent('popstate', { bubbles: true }));
assert.deepStrictEqual(daMo, [['master-data', null]],
  'không có state thì phải lấy mã màn từ địa chỉ');

/* ---- Ràng buộc nguồn: lịch sử phải gắn ở chỗ DÙNG CHUNG cho mọi màn ---- */
assert.ok(/ghiLichSu\(man, scrollToId\)/.test(ma),
  'phải ghi lịch sử ngay trong bọc switchView — gắn lẻ từng màn là sẽ quên màn mới');
assert.ok(/ganLichSuMan\(\);[\s\S]{0,80}moManTheoDiaChi\(\);/.test(ma),
  'phải nghe popstate và mở màn theo địa chỉ lúc dựng khung');
assert.ok(/function moManTheoDiaChi\(\)[\s\S]{0,400}getElementById\('view-' \+ man\)/.test(ma),
  'mở màn theo địa chỉ phải kiểm màn có thật, không tin mù địa chỉ người dùng gõ');

console.log('quay-lai-va-lich-su-man-hinh: OK');

/**
 * Hộp thoại toàn màn phải nằm NGOÀI mọi khung màn.
 *
 * `switchView` đặt `display:none` cho mọi khung màn không hoạt động. Một phần
 * tử `position: fixed` nằm trong tổ tiên `display:none` thì KHÔNG được vẽ ra —
 * dù chính nó đã `display:flex`. Nên bất kỳ nút nào ở màn A mở hộp thoại nằm
 * trong màn B đều "bấm không ăn gì": hàm chạy đúng, hộp thoại mở đúng, mà
 * người dùng không thấy gì cả. Không có lỗi nào trong console, nên nhìn từ
 * ngoài thì y như một cái nút chết.
 *
 * Đó chính là nút "Xem DO" ở màn Hoàn tất giao: nó gọi `editFioriDO`, mà
 * `#fiori-do-form` lại nằm trong `#view-ops-planning`.
 *
 * Quét cả trang thì CHÍN hộp thoại đều bị giam như vậy. Bài kiểm này giữ danh
 * sách, và quan trọng hơn: nó QUÉT LẠI cả trang để bắt hộp thoại thứ mười nếu
 * mai này có ai thêm một cái mới vào trong khung màn.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const NL = String.fromCharCode(10);
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8')
  .split(String.fromCharCode(13)).join('');

// --- 1. Danh sách và hàm dời chỗ phải còn ------------------------------

{
  const i = app.indexOf('const HOP_THOAI_TOAN_MAN = [');
  assert.ok(i > 0, 'thiếu danh sách hộp thoại toàn màn');
  const ds = new Function(
    app.slice(i, app.indexOf(NL + '];', i) + 3) + NL + 'return HOP_THOAI_TOAN_MAN;')();
  assert.ok(Array.isArray(ds) && ds.length >= 9,
    `danh sách phải có ít nhất 9 hộp thoại, thấy ${ds.length}`);
  // Mọi id trong danh sách phải THẬT SỰ có trong HTML — danh sách trôi khỏi
  // markup thì hàm dời chỗ lặng lẽ không làm gì.
  ds.forEach(ma => {
    assert.ok(html.includes(`id="${ma}"`), `#${ma} trong danh sách mà không có trong HTML`);
  });

  const t = app.slice(app.indexOf('function duaHopThoaiRaNgoaiKhungMan()'));
  const than = t.slice(0, t.indexOf(NL + '}') + 2);
  assert.ok(/document\.body\.appendChild\(el\)/.test(than), 'phải dời sang <body>');
  assert.ok(/closest\('\.view-section'\)/.test(than),
    'chỉ dời cái đang nằm trong khung màn, và dời lại lần nữa thì không đổi gì');
}

// --- 2. Phải được gọi TRƯỚC khi người dùng bấm được gì -----------------

{
  const i = app.indexOf('document.addEventListener("DOMContentLoaded", async () => {');
  assert.ok(i > 0, 'không thấy khối khởi tạo chính');
  const dau = app.slice(i, i + 600);
  assert.ok(/duaHopThoaiRaNgoaiKhungMan\(\)/.test(dau),
    'phải gọi ngay đầu khối khởi tạo — gọi muộn thì lần bấm đầu tiên vẫn không hiện');
}

// --- 3. Quét lại cả trang: không còn hộp thoại nào bị giam -------------
//
// Đây là phần đáng giá nhất. Danh sách ở mục 1 chỉ giữ chín cái đã biết; phép
// quét này bắt cái thứ mười.

{
  // Hộp thoại toàn màn = có id, `position: fixed`, và phủ kín màn.
  const bat = [];
  const reThe = /<(?:div|section)\b[^>]*\bid="([a-z0-9_-]+)"[^>]*>/gi;
  let m;
  while ((m = reThe.exec(html)) !== null) {
    const the = m[0];
    if (!/position:\s*fixed/i.test(the)) continue;
    const phuKin = /100vw|100vh/i.test(the)
      || (/top:\s*0/i.test(the) && /left:\s*0/i.test(the));
    if (!phuKin) continue;
    bat.push({ ma: m[1], vi: m.index });
  }
  assert.ok(bat.length >= 9,
    `phép quét phải thấy ít nhất 9 hộp thoại toàn màn, thấy ${bat.length}`);

  // Cái nào nằm trong một khung màn? Dò bằng cách đếm thẻ mở/đóng của
  // `.view-section` phía trước nó.
  const trongKhung = [];
  bat.forEach(({ ma, vi }) => {
    const truoc = html.slice(0, vi);
    // Khung màn gần nhất phía trước còn đang mở hay đã đóng?
    const moKhung = [...truoc.matchAll(/<section\b[^>]*class="[^"]*view-section[^"]*"[^>]*id="([a-z0-9_-]+)"/gi)];
    if (!moKhung.length) return;
    const cuoi = moKhung[moKhung.length - 1];
    const sau = truoc.slice(cuoi.index);
    const mo = (sau.match(/<section\b/gi) || []).length;
    const dong = (sau.match(/<\/section>/gi) || []).length;
    if (mo > dong) trongKhung.push({ ma, khung: cuoi[1] });
  });

  // Chín cái này VẪN nằm trong khung màn ở HTML — đó là bình thường, vì việc
  // dời chỗ làm bằng JS lúc nạp trang, không cắt dán trong 570 KB HTML. Điều
  // bài kiểm giữ là: MỌI cái nằm trong khung màn đều phải có trong danh sách.
  const i = app.indexOf('const HOP_THOAI_TOAN_MAN = [');
  const ds = new Function(
    app.slice(i, app.indexOf(NL + '];', i) + 3) + NL + 'return HOP_THOAI_TOAN_MAN;')();
  const sot = trongKhung.filter(x => !ds.includes(x.ma));
  assert.deepStrictEqual(sot, [],
    'có hộp thoại toàn màn nằm trong khung màn mà KHÔNG có trong danh sách dời'
    + ' chỗ — bấm từ màn khác sẽ không hiện:' + NL
    + sot.map(x => `  #${x.ma} nằm trong #${x.khung}`).join(NL));
}

// --- 4. Nút "Xem DO" ở màn Hoàn tất giao -------------------------------

{
  assert.ok(/onclick="viewCompletionDO\('\$\{completionEscape\(order\.id\)\}'\)"/
    .test(app), 'nút "Xem DO" phải gọi viewCompletionDO với mã đã thoát ký tự');
  const i = app.indexOf('window.viewCompletionDO = function (doId)');
  assert.ok(i > 0, 'không thấy viewCompletionDO');
  const than = app.slice(i, app.indexOf(NL + '};', i));
  // Nó nạp dữ liệu DO vào bộ đệm chung TRƯỚC khi mở form — không thì form mở
  // ra rỗng, vì `editFioriDO` chỉ đọc từ `eplDeliveryOrders`.
  assert.ok(than.indexOf('eplDeliveryOrders') < than.indexOf('editFioriDO('),
    'phải nạp DO vào bộ đệm trước khi mở form');
  assert.ok(/editFioriDO\(doId\)/.test(than));
}

console.log('hop-thoai-phai-hien-duoc: tất cả kiểm tra đã qua');

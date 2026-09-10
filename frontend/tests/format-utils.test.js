/**
 * Test cho js/format-utils.js.
 *
 * Module này gộp các hàm định dạng từng được viết lại nhiều lần trong app.js
 * dưới những cái tên khác nhau. Các bản sao đã trôi khỏi nhau và sinh ra hai
 * lỗi thật — hai lỗi đó được khóa lại ở mục 3 và 4 dưới đây.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const utils = require(path.join(__dirname, '..', 'js', 'format-utils.js'));

// --------------------------------------------------------------------------
// 1. escapeHtml
// --------------------------------------------------------------------------

assert.strictEqual(
  utils.escapeHtml('<img src=x onerror=alert(1)>'),
  '&lt;img src=x onerror=alert(1)&gt;'
);
assert.strictEqual(utils.escapeHtml('A & B'), 'A &amp; B');
assert.strictEqual(utils.escapeHtml('nói "xin chào"'), 'nói &quot;xin chào&quot;');
assert.strictEqual(utils.escapeHtml("O'Brien"), 'O&#39;Brien');
assert.strictEqual(utils.escapeHtml(null), '');
assert.strictEqual(utils.escapeHtml(undefined), '');
assert.strictEqual(utils.escapeHtml('Công ty CP Vissan'), 'Công ty CP Vissan');

// --------------------------------------------------------------------------
// 2. escapeJsAttr — chuỗi JavaScript bên trong thuộc tính HTML
// --------------------------------------------------------------------------

// Mô phỏng điều trình duyệt làm: giải mã thực thể HTML trong giá trị thuộc
// tính, RỒI mới đọc phần còn lại như JavaScript.
{
  const attacked = utils.escapeJsAttr("'); fetch('//evil'); ('");
  const afterHtmlDecode = attacked.split('&#39;').join("'");
  for (let i = 0; i < afterHtmlDecode.length; i++) {
    if (afterHtmlDecode[i] === "'") {
      assert.strictEqual(
        afterHtmlDecode[i - 1],
        '\\',
        'dấu nháy chưa được escape ở cấp JavaScript nên thoát được chuỗi'
      );
    }
  }
}
assert.ok(utils.escapeJsAttr('O\\Brien').startsWith('O\\\\'));
assert.ok(!utils.escapeJsAttr('a\nb').includes('\n'), 'xuống dòng cắt đứt câu lệnh JS');
assert.strictEqual(utils.escapeJsAttr(null), '');
assert.strictEqual(utils.escapeJsAttr('DRV-001'), 'DRV-001');

// --------------------------------------------------------------------------
// 3. LỖI ĐÃ SỬA: số 0 không được biến thành chuỗi rỗng
// --------------------------------------------------------------------------

// escapeRouteCheckpointText cũ dùng `|| ''` nên escape(0) trả về '', trong khi
// escapeVehicleHtml và escapeCloseoutText cùng cảnh trả về '0'. Một mốc kiểm
// tra tuyến đường có giá trị 0 sẽ biến mất khỏi giao diện.
assert.strictEqual(utils.escapeHtml(0), '0', 'số 0 phải giữ nguyên, không thành rỗng');
assert.strictEqual(utils.escapeHtml(false), 'false');
assert.strictEqual(utils.escapeHtml(''), '');

// --------------------------------------------------------------------------
// 4. LỖI ĐÃ SỬA: lệch ngày do thiếu bù múi giờ
// --------------------------------------------------------------------------

// financeMasterDateInput cũ gọi toISOString() mà không bù getTimezoneOffset(),
// nên với UTC+7 mọi thời điểm trước 07:00 sáng trả về NGÀY HÔM TRƯỚC. Hàm này
// dùng cho ngày bắt đầu/kết thúc kỳ kế toán, nên lệch một ngày là lệch biên kỳ.
{
  // Cách cũ, để đối chiếu.
  const buggy = value => new Date(value).toISOString().slice(0, 10);

  const cases = ['2026-08-20T00:00:00', '2026-08-20T06:00:00', '2026-01-01T00:00:00'];
  const offsetMinutes = new Date('2026-08-20T00:00:00').getTimezoneOffset();

  for (const value of cases) {
    const expected = value.slice(0, 10);
    assert.strictEqual(
      utils.dateInputValue(value),
      expected,
      `dateInputValue phải giữ đúng ngày địa phương cho ${value}`
    );
    // Chỉ khẳng định cách cũ SAI khi máy chạy test ở múi giờ dương (như UTC+7).
    if (offsetMinutes < 0) {
      assert.notStrictEqual(
        buggy(value),
        expected,
        `cách cũ phải sai ở múi giờ này, nếu không phép so sánh vô nghĩa cho ${value}`
      );
    }
  }
}

// dateTimeInputValue giữ cả giờ phút theo giờ địa phương.
assert.strictEqual(utils.dateTimeInputValue('2026-08-20T06:30:00'), '2026-08-20T06:30');

// Giá trị không hợp lệ trả về chuỗi rỗng, không phải "Invalid Date".
assert.strictEqual(utils.dateInputValue('khong-phai-ngay'), '');
assert.strictEqual(utils.dateTimeInputValue('khong-phai-ngay'), '');

// --------------------------------------------------------------------------
// 5. formatMoney
// --------------------------------------------------------------------------

assert.strictEqual(utils.formatMoney(4670000, 'VND'), '4.670.000 VND');
assert.strictEqual(utils.formatMoney(0, 'VND'), '0 VND');
// Thiếu mã tiền thì mặc định VND, không để lộ "undefined" ra giao diện.
assert.strictEqual(utils.formatMoney(1000), '1.000 VND');
assert.strictEqual(utils.formatMoney(1000, null), '1.000 VND');
assert.strictEqual(utils.formatMoney(1000, ''), '1.000 VND');
assert.strictEqual(utils.formatMoney(null, 'USD'), '0 USD');

// --------------------------------------------------------------------------
// 6. dayBoundary
// --------------------------------------------------------------------------

assert.strictEqual(utils.dayBoundary('2026-08-20', false), '2026-08-20T00:00:00');
assert.strictEqual(utils.dayBoundary('2026-08-20', true), '2026-08-20T23:59:59');
assert.strictEqual(utils.dayBoundary('', true), '');
assert.strictEqual(utils.dayBoundary(null, false), '');

// --------------------------------------------------------------------------
// 7. app.js phải UỶ QUYỀN, không viết lại
// --------------------------------------------------------------------------

const app = fs.readFileSync(path.join(__dirname, '..', 'js', 'app.js'), 'utf8');

// Không còn định nghĩa trùng: một hàm, một nguồn.
assert.ok(
  !/window\.escapeHtml\s*=\s*function/.test(app),
  'app.js không được định nghĩa lại escapeHtml — nó đến từ format-utils.js'
);
assert.ok(!/window\.escapeJsAttr\s*=\s*function/.test(app));

// Các tên cũ vẫn tồn tại (để không phải sửa hàng trăm chỗ gọi) nhưng phải uỷ quyền.
for (const name of ['escapeVehicleHtml', 'escapeCloseoutText', 'escapeRouteCheckpointText']) {
  const fn = app.slice(app.indexOf(`function ${name}(`), app.indexOf(`function ${name}(`) + 120);
  assert.ok(fn.includes('escapeHtml(value)'), `${name} phải uỷ quyền sang escapeHtml`);
}
for (const name of ['formatVehicleMoney', 'closeoutMoney', 'completionMoney']) {
  const fn = app.slice(app.indexOf(`function ${name}(`), app.indexOf(`function ${name}(`) + 140);
  assert.ok(fn.includes('FormatUtils.formatMoney'), `${name} phải uỷ quyền sang FormatUtils`);
}
for (const [name, expected] of [
  ['financeMasterDateInput', 'FormatUtils.dateInputValue'],
  ['dispatchDateInputValue', 'FormatUtils.dateInputValue'],
  ['localDateTimeInput', 'FormatUtils.dateTimeInputValue'],
  // tenderDateTimeLocal da bi do cung cum Tender khi go man Dau thau.
  ['financeMasterDateTime', 'FormatUtils.dayBoundary'],
]) {
  const fn = app.slice(app.indexOf(`function ${name}(`), app.indexOf(`function ${name}(`) + 400);
  assert.ok(fn.includes(expected), `${name} phải uỷ quyền sang ${expected}`);
}

// Không còn chỗ nào gọi toISOString().slice(0, 10) mà thiếu bù múi giờ.
assert.ok(
  !/new Date\(value\)\.toISOString\(\)\.slice\(0, 10\)/.test(app),
  'toISOString().slice(0,10) không bù múi giờ sẽ trả sai ngày ở UTC+7'
);

// --------------------------------------------------------------------------
// 8. Thứ tự nạp script
// --------------------------------------------------------------------------

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');

// Đo vị trí THẺ SCRIPT, không phải mọi lần tên file xuất hiện: các chú thích
// trong HTML cũng nhắc tên file và sẽ làm phép so sánh thứ tự sai lệch.
function scriptPosition(file) {
  const index = html.indexOf(`<script src="/static/${file}`);
  assert.notStrictEqual(index, -1, `index.html phải có thẻ script cho ${file}`);
  return index;
}

const formatUtilsAt = scriptPosition('js/format-utils.js');
for (const consumer of ['js/app.js', 'js/sla-analytics.js']) {
  assert.ok(
    formatUtilsAt < scriptPosition(consumer),
    `format-utils.js phải nạp trước ${consumer}`
  );
}

console.log('format-utils: tất cả kiểm tra đã qua');

// --------------------------------------------------------------------------
// 9. "Hôm nay" phải là hôm nay theo giờ ĐỊA PHƯƠNG
// --------------------------------------------------------------------------

// `new Date().toISOString().slice(0, 10)` trả về ngày theo giờ UTC, nên với
// UTC+7 nó cho NGÀY HÔM QUA cho bất kỳ ai mở ứng dụng trước 07:00 sáng — mà
// nghề vận tải làm từ sớm. Mẫu này từng xuất hiện ở 8 chỗ để lấy giá trị mặc
// định cho các ô ngày, và ở chỗ gom cảnh báo SLA theo ngày.
{
  const files = ['js/app.js', 'js/transport-reporting.js'];
  for (const file of files) {
    const source = fs.readFileSync(path.join(__dirname, '..', file), 'utf8');
    assert.ok(
      !/new Date\(\)\.toISOString\(\)\.slice\(0, 10\)/.test(source),
      `${file} còn dùng toISOString() để lấy "hôm nay" — sẽ ra sai ngày ở UTC+7`
    );
  }
}

// tms-cockpit-utils.js là module UMD chạy cả trong Node nên không dùng biến
// toàn cục FormatUtils; nó phải tự bù offset.
{
  const cockpit = fs.readFileSync(
    path.join(__dirname, '..', 'js', 'tms-cockpit-utils.js'),
    'utf8'
  );
  const cockpitLines = cockpit.split('\n');
  // Dòng thứ N (đếm từ 1) nằm ở chỉ số N-1 của mảng, nên 5 dòng ngay trên nó là
  // các chỉ số N-6 .. N-2. Tính sai khoảng này sẽ báo oan những chỗ đã bù đúng.
  const unsafe = cockpitLines
    .map((line, index) => [index + 1, line])
    .filter(([, line]) => /\.toISOString\(\)\.slice\(0, 10\)/.test(line))
    .filter(([lineNumber]) => {
      const before = cockpitLines
        .slice(Math.max(0, lineNumber - 6), lineNumber - 1)
        .join(' ');
      return !/getTimezoneOffset/.test(before);
    });
  assert.deepStrictEqual(
    unsafe.map(([index]) => index),
    [],
    'tms-cockpit-utils.js còn chỗ cắt ngày mà chưa bù múi giờ'
  );
}

// --------------------------------------------------------------------------
// 10. Không còn bản sao hàm escape nào
// --------------------------------------------------------------------------

// Sáu hàm escape từng tồn tại song song trong app.js: escapeVehicleHtml,
// escapeCloseoutText, escapeRouteCheckpointText, doBoardEscape,
// và window.escapeHtml. Tất cả đều viết đúng nhưng đã trôi khỏi nhau — một bản
// biến số 0 thành chuỗi rỗng.
{
  const app = fs.readFileSync(path.join(__dirname, '..', 'js', 'app.js'), 'utf8');
  const copies = (app.match(/replace\(\/&\/g, '&amp;'\)/g) || []).length;
  assert.strictEqual(
    copies,
    0,
    `app.js còn ${copies} bản tự viết lại phép escape — phải uỷ quyền sang escapeHtml`
  );
  for (const name of ['doBoardEscape']) {
    const fn = app.slice(app.indexOf(`function ${name}(`), app.indexOf(`function ${name}(`) + 90);
    assert.ok(fn.includes('escapeHtml(value)'), `${name} phải uỷ quyền sang escapeHtml`);
  }
}

console.log('ngay dia phuong + gop escape: tất cả kiểm tra đã qua');

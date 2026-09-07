/**
 * Bàn điều phối ba cột: DO chờ xếp | lịch xe | ngoại lệ.
 *
 * Màn Điều phối ghi ngay trên đầu: "Chọn DO, đối chiếu lịch xe rồi gán nguồn
 * lực NGAY TRÊN MỘT MÀN HÌNH". Đo lại thì câu đó không đúng:
 *
 *   · `#dispatch-queue` để `hidden`, chỉ hiện khi bấm bước 1 — và lúc đó nó bị
 *     DỜI vào một hộp thoại che kín màn.
 *   · `#dispatch-calendar-conflicts` nằm trong một ngăn kéo phải bấm "Công cụ"
 *     mới mở.
 *
 * Nên thực tế màn chỉ hiện một thứ: lịch xe. Người điều phối phải mở hộp thoại
 * để chọn DO, đóng lại để xem lịch, rồi mở tiếp — đúng cái việc mà câu chữ trên
 * đầu nói là không phải làm.
 *
 * Bản mẫu `dispatch-v2-crew.html` xếp ba cột cạnh nhau. Bài kiểm này giữ điều
 * đó, và giữ luôn hai hệ quả: ngăn kéo "Công cụ" đã bỏ hẳn (nó chỉ có một mục),
 * và bước 1 không còn mở hộp thoại.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const NL = String.fromCharCode(10);
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8')
  .split(String.fromCharCode(13)).join('');
const css = html.replace(/\/\*[\s\S]*?\*\//g, ' ');

// --- 1. Ba cột đều hiện sẵn -------------------------------------------

{
  // Cột DO không còn `hidden`. Đây là chốt quan trọng nhất: thẻ có `hidden` thì
  // dù bố cục ba cột đúng, cột đó vẫn không có gì trong đó.
  const the = html.slice(html.indexOf('<section id="dispatch-queue"'));
  const dong = the.slice(0, the.indexOf('>') + 1);
  assert.ok(!/\bhidden\b/.test(dong),
    `cột "DO chờ điều phối" còn hidden: ${dong}`);

  ['dispatch-queue', 'dispatch-timeline', 'dispatch-exceptions'].forEach(ma => {
    assert.strictEqual((html.match(new RegExp(`id="${ma}"`, 'g')) || []).length, 1,
      `#${ma} phải có đúng một chỗ`);
  });

  // Cả ba phải là con TRỰC TIẾP của lưới, không thì grid không xếp chúng.
  const iLuoi = html.indexOf('id="dispatch-calendar-panel"');
  assert.ok(iLuoi > 0, 'không thấy lưới bàn điều phối');
  const luoi = html.slice(iLuoi, html.indexOf('id="dispatch-step-modal"'));
  ['dispatch-queue', 'dispatch-timeline', 'dispatch-exceptions'].forEach(ma => {
    assert.ok(luoi.includes(`id="${ma}"`), `#${ma} phải nằm trong lưới`);
  });
}

// --- 2. Lưới chia ba cột, và màn hẹp thì gộp -------------------------

{
  const i = css.indexOf('.dispatch-workbench-grid {');
  assert.ok(i > 0, 'thiếu quy tắc lưới');
  const luat = css.slice(i, css.indexOf('}', i));
  assert.ok(/grid-template-columns:\s*\d+px\s+minmax\(0,\s*1fr\)\s+\d+px/.test(luat),
    `lưới phải chia ba cột (hai cột bên cố định, cột giữa linh hoạt): ${luat.trim()}`);

  // Màn hẹp: ba cột cạnh nhau là không đọc được cột nào. Và cột ngoại lệ phải
  // xuống DƯỚI lịch xe, không lên trên — lên trên là lặp lại đúng lỗi che mất
  // lịch xe mà bố cục này sinh ra để sửa.
  const j = css.indexOf('@media (max-width:1400px)');
  assert.ok(j > 0, 'thiếu quy tắc cho màn hẹp');
  const hep = css.slice(j, j + 400);
  assert.ok(/#dispatch-exceptions\s*\{\s*grid-column:1 \/ -1/.test(hep),
    'màn hẹp: cột ngoại lệ phải trải hết chiều ngang ở hàng dưới');

  // Danh sách ngoại lệ phải cuộn TRONG cột của nó: một ngày xấu 40 ngoại lệ kéo
  // cột phải dài gấp ba lần lịch xe.
  assert.ok(/\.dispatch-exceptions-list\s*\{[^}]*overflow-y:\s*auto/.test(css),
    'danh sách ngoại lệ phải cuộn trong cột của nó');
}

// --- 3. Ngăn kéo "Công cụ" đã bỏ hẳn ---------------------------------

{
  // Ngăn kéo chỉ có MỘT mục là "Cảnh báo". Khối cảnh báo nay là cột thứ ba
  // thường trực, nên ngăn kéo còn lại một cái vỏ rỗng.
  ['dispatch-tools-button', 'dispatch-tools-panel', 'dispatch-tool-drawer',
    'dispatch-tool-pane-alerts', 'dispatch-tool-alerts', 'dispatch-tool-title',
    'openDispatchTool', 'closeDispatchTool', 'toggleDispatchTools'].forEach(dauVet => {
    assert.ok(!html.includes(dauVet), `index.html còn dấu vết ngăn kéo: ${dauVet}`);
    assert.ok(!app.includes(dauVet), `app.js còn dấu vết ngăn kéo: ${dauVet}`);
  });

  // Nhưng chỗ chứa số liệu phải CÒN: các hàm khác ghi vào đó rồi khối khác đọc
  // ra. Bỏ nó là chúng lặng lẽ không ghi được gì.
  assert.ok(/class="dispatch-resource-data"/.test(html),
    'chỗ chứa số liệu điều phối phải còn');
  ['dispatch-veh-ready-count', 'dispatch-veh-busy-count',
    'dispatch-driver-ready-count'].forEach(ma => {
    assert.ok(html.includes(`id="${ma}"`), `mất chỗ chứa số liệu #${ma}`);
  });

  // Phần trình bày của ngăn kéo cũng phải dọn — quy tắc cho thẻ không tồn tại
  // là chỗ để người sau tưởng thẻ đó còn.
  ['.dispatch-tools-wrap', '.dispatch-tools-panel', '.dispatch-tool-drawer'].forEach(lop => {
    assert.ok(!css.includes(lop + ' ') && !css.includes(lop + '{')
      && !css.includes(lop + ' {'),
      `còn quy tắc trình bày cho ${lop}`);
  });
}

// --- 4. Bước 1 không mở hộp thoại nữa --------------------------------

{
  const i = app.indexOf('window.openDispatchStepModal = function (step) {');
  assert.ok(i > 0, 'không thấy openDispatchStepModal');
  const dau = app.slice(i, i + 900);
  assert.ok(/step === 'do'/.test(dau),
    'bước 1 phải được chặn ở ĐẦU hàm, trước khi tới phần mở hộp thoại');
  assert.ok(/dispatch-do-search-input/.test(dau),
    'bước 1 phải đưa con trỏ vào ô tìm của cột DO');

  // Và bảng cấu hình hộp thoại không được còn khai bước 'do' — khai thì một
  // đường khác gọi vào là lại dời cột đang hiện vào hộp thoại.
  const j = app.indexOf('const dispatchStepModalConfig = {');
  const bang = app.slice(j, app.indexOf(NL + '};', j));
  assert.ok(!/^\s*do:\s*\{/m.test(bang),
    'bảng cấu hình hộp thoại không được còn khai bước "do"');
  // Ba bước còn lại thì phải còn: chúng là hộp thoại thật.
  ['trip', 'schedule', 'resources'].forEach(b => {
    assert.ok(new RegExp(`\\b${b}:\\s*\\{`).test(bang), `mất khai bước "${b}"`);
  });
}

console.log('dieu-phoi-ba-cot: ba cột hiện sẵn, ngăn kéo Công cụ đã bỏ, bước 1 không mở hộp thoại');

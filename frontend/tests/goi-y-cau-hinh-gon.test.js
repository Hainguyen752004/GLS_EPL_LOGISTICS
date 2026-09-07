/**
 * Gợi ý cấu hình phải GỌN, và phần dài phải gấp được.
 *
 * Bản trước là một cột `<aside>` rộng 300px, sticky, cao gần hết màn hình:
 * nhãn "GỢI Ý CẤU HÌNH", tiêu đề, một đoạn mô tả, một hộp "DỮ LIỆU HIỆN CÓ"
 * cao ba dòng chỉ để nói một con số, hai nút xếp dọc, rồi ba dòng gợi ý bước
 * tiếp. Nó chiếm một phần tư chiều rộng màn Dữ liệu gốc vĩnh viễn.
 *
 * Bản này chia theo mức độ CẦN:
 *   · thứ cần luôn — đang xem danh mục nào, có bao nhiêu dòng, và hai nút hay
 *     bấm nhất — nằm trên MỘT dải một dòng, không phải bấm gì;
 *   · thứ chỉ cần lúc đầu — đoạn mô tả và ba dòng gợi ý — gấp vào nút dấu hỏi,
 *     và lựa chọn mở/đóng được nhớ lại nên không phải bấm lại mỗi lần vào.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const NL = String.fromCharCode(10);
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8')
  .split(String.fromCharCode(13)).join('');

// --- 1. Cột 300px đã bỏ ------------------------------------------------

{
  assert.ok(!/<aside id="master-data-guidance-panel"/.test(html),
    'còn cột <aside> kiểu cũ');
  // Neo vào KHUNG CHỨA khối gợi ý, không neo vào chuỗi CSS thô
  // `minmax(0,1fr) 300px`: chuỗi đó là một cách chia cột rất thường, và màn
  // Công thức giá thành dùng đúng nó cho khung "chuyến mẫu" bên phải — bắt vào
  // chuỗi thì bài kiểm này đỏ vì một màn khác chẳng liên quan.
  {
    const i = html.indexOf('<div id="master-data-command-center"');
    assert.ok(i > 0, 'không thấy khung Dữ liệu gốc');
    const the = html.slice(i, html.indexOf('>', i) + 1);
    assert.ok(!/grid-template-columns/.test(the),
      `khung Dữ liệu gốc còn chia cột cho khối gợi ý: ${the}`);
  }
  assert.ok(html.includes('<div id="master-data-command-center">'),
    'khung phải về một cột, không đặt grid nữa');
}

// --- 2. Dải một dòng có đủ thứ cần luôn -------------------------------

{
  const i = html.indexOf('class="md-guide-bar"');
  assert.ok(i > 0, 'thiếu dải gợi ý');
  const dai = html.slice(i, html.indexOf('</div>' + NL + '          <div id="master-data-guidance-panel"', i));

  // Bốn thứ phải thấy mà KHÔNG cần bấm.
  ['master-data-selected-title', 'master-data-health-list',
    'master-data-guide-add', 'master-data-guide-reload'].forEach(ma => {
    assert.ok(dai.includes(`id="${ma}"`), `dải thiếu #${ma}`);
  });
  // Hai nút hay bấm nhất KHÔNG được nằm trong khối gấp — để trong đó thì
  // muốn bấm phải mở khối ra trước, tức thêm một lần bấm cho một việc làm
  // thường xuyên.
  const khoi = html.slice(html.indexOf('id="master-data-guidance-panel"'));
  const thanKhoi = khoi.slice(0, khoi.indexOf('</div>' + NL + NL));
  assert.ok(!thanKhoi.includes('master-data-guide-add'),
    'nút "Thêm / cấu hình" phải ở trên dải, không nằm trong khối gấp');

  // Nút gấp phải khai báo đầy đủ cho trình đọc màn hình.
  assert.ok(/id="master-data-guide-toggle"/.test(dai), 'thiếu nút gấp');
  assert.ok(/aria-expanded="false"/.test(dai) && /aria-controls="master-data-guidance-panel"/.test(dai),
    'nút gấp phải có aria-expanded và aria-controls');
}

// --- 3. Khối gấp: mặc định ĐÓNG, và ẩn được thật -----------------------

{
  const i = html.indexOf('<div id="master-data-guidance-panel"');
  const the = html.slice(i, html.indexOf('>', i) + 1);
  assert.ok(/\bhidden\b/.test(the), 'khối gấp phải đóng sẵn trong HTML tĩnh');

  // `hidden` chỉ có tác dụng nhờ luật chung — không có nó thì `.md-guide-panel`
  // với `padding`/`background` vẫn hiện. Đây chính là bẫy đã sửa ở commit
  // trước, nên khẳng định lại tại đây.
  assert.ok(/\[hidden\] \{ display: none !important; \}/.test(html),
    'thiếu luật chung [hidden] thì khối gấp không ẩn được');
}

// --- 4. Hàm mở/đóng và việc nhớ trạng thái ----------------------------

{
  ['moGoiYCauHinh', 'apDungTrangThaiGoiY'].forEach(n => {
    assert.ok(app.includes(`window.${n} =`), `thiếu ${n}`);
  });
  const t = app.slice(app.indexOf('function docTrangThaiGoiY()'),
    app.indexOf('window.apDungTrangThaiGoiY'));
  assert.ok(/localStorage/.test(t), 'phải nhớ lựa chọn mở/đóng');
  // `localStorage` ném lỗi được (cửa sổ riêng tư, chặn dữ liệu trang) — một
  // gợi ý không mở được thì không đáng làm sập cả màn.
  assert.ok((t.match(/catch \(e\)/g) || []).length >= 2,
    'mọi lần đọc/ghi localStorage phải bọc try/catch');
  // Mặc định là ĐÓNG: chỉ mở khi đã lưu đúng "1".
  assert.ok(/getItem\(KHOA_GOI_Y_CAU_HINH\) === "1"/.test(t),
    'mặc định phải là đóng');

  // Áp trạng thái đã nhớ NGAY khi nạp trang, không thì lần vào đầu tiên khối
  // vẫn đóng dù người dùng đã chọn mở.
  const i = app.indexOf('document.addEventListener("DOMContentLoaded", async () => {');
  assert.ok(/apDungTrangThaiGoiY\(\)/.test(app.slice(i, i + 700)),
    'phải áp trạng thái đã nhớ lúc nạp trang');
}

// --- 5. Viên số liệu, và dấu đỏ chỉ bật khi CÓ việc -------------------

{
  const i = app.indexOf('window.updateMasterDataGuidance = function');
  assert.ok(i > 0, 'không thấy updateMasterDataGuidance');
  const t = app.slice(i, app.indexOf(NL + '};', i));

  assert.ok(/md-guide-pill-ok/.test(t) && /md-guide-pill-thieu/.test(t),
    'viên số liệu phải đổi màu theo có/không có dữ liệu');
  // Hộp ba dòng cũ đã bỏ: nhãn "DỮ LIỆU HIỆN CÓ" chỉ mô tả chính nó, mà viên
  // đã nằm ngay cạnh tên danh mục.
  assert.ok(!/\$\{dataHeader\}/.test(t), 'còn hộp đếm ba dòng kiểu cũ');
  assert.ok(!/1\.35rem/.test(t), 'còn con số cỡ 1.35rem kiểu cũ');

  // Dấu đỏ chỉ bật khi danh mục CHƯA có dòng nào. Một dấu đỏ thường trực thì
  // chẳng còn nghĩa gì.
  assert.ok(/oDau\.hidden = rows > 0/.test(t),
    'dấu đỏ phải tắt khi đã có dữ liệu');

  // Hai nút gán bằng `onclick` trong JS, nên nhãn ba ngôn ngữ vẫn dùng lại
  // `btnAdd` / `btnReload` có sẵn.
  assert.ok(/oThem\.innerHTML = btnAdd/.test(t) && /oNapLai\.innerHTML = btnReload/.test(t),
    'hai nút phải dùng lại nhãn đã dịch');
  assert.ok(/openMasterDataPrimaryAction\(tabId\)/.test(t), 'nút Thêm phải gọi đúng hàm');
}

console.log('goi-y-cau-hinh-gon: tất cả kiểm tra đã qua');

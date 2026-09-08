/**
 * Màn "Sắp lịch xe và tài xế" — bản mẫu phải nằm TRONG phạm vi của nó.
 *
 * Rủi ro lớn nhất khi bê một bản mẫu vào ứng dụng không phải là màn mới trông
 * sai, mà là MƯỜI MÀN CŨ trông sai. Bản mẫu
 * `shift-schedule-v5-staff-vehicle.html` dùng những tên lớp rất chung —
 * `.card`, `.tag`, `.panel`, `.grid`, `.cell`, `.search`, `.chip`, `.legend`,
 * `.who` — mà ứng dụng cũng đã có. Một quy tắc để trần trong tệp CSS này sẽ ghi
 * đè lên mọi màn khác, và không ai nối được lỗi đó về đây.
 *
 * Bài kiểm cũng soi hai điều khác không được rơi mất:
 *   · khối markup cũ phải CÒN trong trang và ẨN — `app.js` có gần một nghìn
 *     dòng ghi vào các `id` của nó, và `switchMasterDataTab` gọi vào mỗi lần
 *     mở thẻ này;
 *   · hộp thoại hồ sơ tài xế phải nằm NGOÀI khối ẩn, vì nút "+ Tài xế / phụ xe"
 *     ở đầu màn mới gọi vào nó — để trong khối ẩn thì bấm xong không thấy gì.
 */
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const goc = path.join(__dirname, '..');
const css = fs.readFileSync(path.join(goc, 'css', 'sap-lich-v5.css'), 'utf8');
const js = fs.readFileSync(path.join(goc, 'js', 'sap-lich-v5.js'), 'utf8');
const html = fs.readFileSync(path.join(goc, 'index.html'), 'utf8');

test('mọi quy tắc CSS của bản mẫu đều bọc trong .ssv5', () => {
  const chung = ['card', 'tag', 'panel', 'grid', 'cell', 'search', 'chip', 'chips',
    'legend', 'who', 'seg', 'date', 'cover', 'need', 'opt', 'sum', 'check',
    'empty', 'lbl', 'hdr', 'crumb', 'teams', 'heat', 'dep', 'tot', 'scroller',
    'primary', 'ghost', 'cta', 'shifts', 'sopt', 'dd', 'pat', 'sh', 'vs', 'vc',
    'vrow', 'rep', 'pb', 'dn', 'cov', 'tfoot', 'col-h'];
  chung.forEach(lop => {
    const re = new RegExp('(^|[},])\\s*\\.' + lop + '[\\s,{:]', 'm');
    const viPham = re.exec(css);
    assert.ok(!viPham,
      `quy tắc \`.${lop}\` để trần, phải bọc trong \`.ssv5\`: ${viPham && viPham[0]}`);
  });
});

test('không có quy tắc nào chạm vào thẻ trần ngoài phạm vi .ssv5', () => {
  // `body`, `button`, `select`, `input` để trần thì đổi phông và con trỏ của cả
  // ứng dụng. Bản mẫu có đúng những dòng đó ở đầu tệp gốc.
  ['body', 'button', 'select', 'input', 'html', '\\*'].forEach(the => {
    const re = new RegExp('(^|[},])\\s*' + the + '[\\s,{]', 'm');
    const viPham = re.exec(css);
    assert.ok(!viPham, `thẻ \`${the}\` để trần trong sap-lich-v5.css: ${viPham && viPham[0]}`);
  });
});

test('khối markup cũ còn trong trang và bị ẩn, hộp thoại tài xế thì không', () => {
  const i = html.indexOf('id="md-tab-vehicles"');
  const j = html.indexOf('<!-- /#md-tab-vehicles -->');
  assert.ok(i > 0 && j > i, 'không tìm thấy thẻ Sắp lịch xe và tài xế');
  const doan = html.slice(i, j);

  assert.match(doan, /id="ssv5-root"/, 'thiếu khung của màn mới');
  assert.match(doan, /id="ssv5-khoi-cu"[^>]*hidden/,
    'khối markup cũ phải còn trong trang và ẩn — `app.js` vẫn ghi vào các id của nó');
  assert.match(doan, /id="driver-shift-workbench"/,
    'các id cũ phải giữ nguyên, nếu không gần một nghìn dòng trong app.js ném lỗi');

  const anh = doan.indexOf('/#ssv5-khoi-cu');
  const hop = doan.indexOf('id="driver-modal-dialog"');
  assert.ok(anh > 0 && hop > anh,
    'hộp thoại hồ sơ tài xế phải nằm NGOÀI khối ẩn, nếu không bấm "+ Tài xế / phụ xe" không thấy gì');

  // Thẻ nạp của màn mới.
  assert.match(html, /css\/sap-lich-v5\.css\?v=/, 'thiếu thẻ nạp CSS');
  assert.match(html, /js\/sap-lich-v5\.js\?v=/, 'thiếu thẻ nạp JS');
});

test('mọi đường ghi đều gọi backend thật, không có dữ liệu cứng trong màn', () => {
  ['/api/tms/scheduling/board',
    '/api/tms/scheduling/driver-shifts',
    '/api/tms/scheduling/generate-from-pattern',
    '/api/tms/scheduling/drivers/'].forEach(duong => {
    assert.ok(js.includes(duong), `thiếu lời gọi ${duong}`);
  });
  // Bản mẫu sinh 42 người và 14 xe bằng một bộ sinh số giả. Không được mang
  // theo: một màn hình vẽ người không có thật thì mọi con số trên đó vô nghĩa.
  assert.doesNotMatch(js, /const (first|mid|last|plates|crews)\s*=/,
    'còn bộ sinh dữ liệu giả của bản mẫu trong mã');
  assert.doesNotMatch(js, /seed\s*=\s*\d+/, 'còn bộ sinh số giả của bản mẫu');
});

test('mốc gửi lên máy chủ có kèm múi giờ Việt Nam', () => {
  // Gửi mốc trần thì máy chủ hiểu là UTC, và một ca sáng 06:00 giờ Việt Nam bị
  // ghi thành 13:00 giờ Việt Nam — lệch đúng bảy tiếng, rơi vào giữa ca chiều.
  assert.match(js, /\+07:00/, 'mốc gửi lên phải kèm +07:00');
});

test('mã ca tiền định theo người, ngày và ca', () => {
  // Sinh mã ngẫu nhiên thì lưu hai lần cùng một ô tạo ra hai ca trùng chỗ:
  // lưới hiện một ca mà cột giờ tuần đếm cả hai.
  assert.match(js, /TAY-\$\{c\.drv\}-\$\{c\.ngay\.replace/,
    'mã ca phải tiền định theo (người, ngày, ca)');
});

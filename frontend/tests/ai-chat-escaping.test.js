/**
 * Test hồi quy cho việc escape ở frontend.
 *
 * Các hàm escape được nạp từ js/format-utils.js — chính module ứng dụng dùng,
 * không chép lại vào đây. Hành vi chi tiết của chúng nằm ở
 * tests/format-utils.test.js; file này kiểm các điểm ghi HTML trong app.js.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const source = fs.readFileSync(
  path.join(__dirname, '..', 'js', 'app.js'),
  'utf8'
);

// --------------------------------------------------------------------------
// escapeHtml và escapeJsAttr giờ ở js/format-utils.js, không còn trong app.js.
// Hành vi chi tiết của chúng được phủ ở tests/format-utils.test.js; ở đây chỉ
// dùng lại để kiểm các chỗ trong khung trò chuyện AI.
// --------------------------------------------------------------------------

const { escapeHtml, escapeJsAttr } = require(path.join(__dirname, '..', 'js', 'format-utils.js'));

// --------------------------------------------------------------------------
// 1. escapeHtml
// --------------------------------------------------------------------------

assert.strictEqual(
  escapeHtml('<img src=x onerror=alert(1)>'),
  '&lt;img src=x onerror=alert(1)&gt;'
);
assert.strictEqual(escapeHtml('A & B'), 'A &amp; B');
assert.strictEqual(escapeHtml('nói "xin chào"'), 'nói &quot;xin chào&quot;');
assert.strictEqual(escapeHtml(null), '');
assert.strictEqual(escapeHtml(undefined), '');
assert.strictEqual(escapeHtml(0), '0', 'số 0 không được biến thành chuỗi rỗng');
assert.strictEqual(escapeHtml('Công ty CP Vissan'), 'Công ty CP Vissan');

// --------------------------------------------------------------------------
// 2. escapeJsAttr — chuỗi JavaScript bên trong thuộc tính HTML
// --------------------------------------------------------------------------

// Chỉ escapeHtml là không đủ: trình duyệt giải mã thực thể HTML trong giá trị
// thuộc tính TRƯỚC khi đọc phần còn lại như JavaScript. Mô phỏng đúng thứ tự đó.
{
  const attacked = escapeJsAttr("'); fetch('//evil'); ('");
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

// Dấu gạch chéo ngược phải được nhân đôi, nếu không nó sẽ ăn mất dấu escape sau đó.
assert.ok(escapeJsAttr('O\\Brien').startsWith('O\\\\'));
assert.strictEqual(escapeJsAttr(null), '');
assert.strictEqual(escapeJsAttr('DRV-001'), 'DRV-001', 'giá trị bình thường giữ nguyên');

// Ký tự xuống dòng cũng phải bị vô hiệu — nó cắt đứt câu lệnh JavaScript.
assert.ok(!escapeJsAttr('a\nb').includes('\n'));

// --------------------------------------------------------------------------
// 3. Khung trò chuyện AI: escape trước khi sinh thẻ markdown
// --------------------------------------------------------------------------

const formatFn = source.slice(
  source.indexOf('function formatMarkdownToHTML'),
  source.indexOf('function formatMarkdownToHTML') + 1400
);
assert.ok(
  /let html = escapeHtml\(text\)/.test(formatFn),
  'formatMarkdownToHTML phải escape đầu vào trước khi áp dụng markdown'
);
assert.ok(
  formatFn.indexOf('escapeHtml(text)') < formatFn.indexOf('<strong>$1</strong>'),
  'phải escape TRƯỚC khi sinh thẻ, nếu không thẻ của ta cũng bị escape'
);

// Thẻ bản nháp không được nội suy dữ liệu thô.
assert.ok(
  !/<strong>Khách hàng:<\/strong> \$\{draftData\.customer/.test(source),
  'draftData.customer không được nội suy thô vào innerHTML'
);
assert.ok(/escapeHtml\(draftData\.customer/.test(source));

// --------------------------------------------------------------------------
// 4. showToast đặt nội dung qua textContent
// --------------------------------------------------------------------------

assert.ok(
  !source.includes('overflow-wrap:anywhere;">${cleanMessage}<'),
  'showToast không được nội suy cleanMessage vào innerHTML'
);
assert.ok(/toastBody\.textContent = cleanMessage/.test(source));

// Nút xác nhận không được hứa "Lưu" khi trợ lý không ghi gì.
assert.ok(
  !/onclick="confirmDraft\([^)]*\)">[^<]*Lưu</.test(source),
  'nút không được ghi "Lưu" vì confirmDraft không ghi dữ liệu vào hệ thống'
);

// --------------------------------------------------------------------------
// 5. Dữ liệu từ server phải được escape tại điểm ghi HTML
// --------------------------------------------------------------------------

const MUST_BE_ESCAPED = [
  'inc.description',   // mô tả sự cố — người ngoài đặt được
  'r.name',            // tên tuyến
  'q.customer',        // tên khách trên báo giá
  'carrier.name',      // tên nhà thầu
  'c.contact_person',  // người liên hệ
];
// Các sink văn bản thuần (innerText/textContent) KHÔNG được escape — escape ở
// đó sẽ khiến người dùng nhìn thấy "&amp;" thay vì "&". Chỉ soi các dòng dựng HTML.
const htmlLines = source
  .split('\n')
  .filter(line => !/\.(innerText|textContent)\s*=/.test(line) && !/showToast\(/.test(line))
  .join('\n');

for (const expr of MUST_BE_ESCAPED) {
  const raw = new RegExp('\\$\\{\\s*' + expr.replace('.', '\\.') + '\\s*\\}');
  assert.ok(!raw.test(htmlLines), `${expr} vẫn còn được nội suy thô vào HTML`);
}

// Các nút thao tác tài xế nằm trong ngữ cảnh JavaScript.
assert.ok(
  !/onclick="editDriverById\('\$\{d\.id \|\| d\.name\}'\)"/.test(source),
  'editDriverById không được nhận giá trị thô'
);
assert.ok(/escapeJsAttr\(d\.id \|\| d\.name\)/.test(source));

// --------------------------------------------------------------------------
// 6. Trang chủ không chứa token, CDN ghim phiên bản
// --------------------------------------------------------------------------

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
assert.ok(!html.includes('EPL_TMS_API_TOKEN'), 'index.html không được chứa token API');
assert.ok(html.includes('api-auth.js'), 'index.html phải nạp lớp bọc xác thực');
assert.ok(
  html.indexOf('api-auth.js') < html.indexOf('js/app.js'),
  'api-auth.js phải nạp trước app.js'
);
assert.ok(
  !/cdn\.jsdelivr\.net\/npm\/chart\.js["?]/.test(html),
  'chart.js phải ghim phiên bản tường minh'
);

console.log('ai-chat-escaping: tất cả kiểm tra đã qua');

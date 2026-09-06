/**
 * Mọi thuộc tính `onclick=` / `oninput=` … trong index.html phải gọi hàm CÓ
 * THẬT trong các tệp JS.
 *
 * Vì sao cần bài kiểm này: `onCostComponentInput()` được gọi ở năm ô nhập của
 * màn Công thức giá thành, mà thân hàm chỉ có một dòng
 * `window.renderCostFormulaView();`. Đợt viết lại công thức động gỡ cả hàm lẫn
 * trình dựng đó đi, nhưng năm thuộc tính `oninput=` trong HTML thì còn nguyên.
 * Hậu quả: mỗi lần gõ MỘT PHÍM vào ô đơn giá là một `ReferenceError`. Phép
 * tính vẫn chạy vì nó đứng trước trong cùng chuỗi lệnh, nên trên màn hình
 * không thấy gì bất thường — chỉ có console đầy lỗi. Đúng kiểu hỏng lặng lẽ
 * mà không ai phát hiện cho tới khi mở DevTools.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const js = fs.readdirSync(path.join(ROOT, 'js'))
  .filter(f => f.endsWith('.js'))
  .map(f => fs.readFileSync(path.join(ROOT, 'js', f), 'utf8'))
  .join('\n');

// Tên hàm được định nghĩa, ở mọi dạng mà tệp này đang dùng.
const dinhNghia = new Set();
for (const re of [
  /\bfunction\s+([A-Za-z_$][\w$]*)/g,
  /window\.([A-Za-z_$][\w$]*)\s*=/g,
  /(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(/g,
]) {
  let m;
  while ((m = re.exec(js)) !== null) dinhNghia.add(m[1]);
}

// `xxx.yyy(` là gọi PHƯƠNG THỨC trên một đối tượng, không phải hàm toàn cục —
// bỏ qua. Chỉ xét tên đứng một mình ngay trước dấu mở ngoặc.
const BO_QUA = new Set(['if', 'for', 'while', 'switch', 'return', 'typeof',
  'alert', 'confirm', 'prompt', 'parseInt', 'parseFloat', 'Number', 'String',
  'Boolean', 'Array', 'Object', 'JSON', 'Math', 'Date', 'setTimeout',
  'setInterval', 'encodeURIComponent', 'decodeURIComponent', 'catch']);

const thieu = new Map();
const thuocTinh = /\bon(?:click|change|input|submit|keyup|keydown|blur|focus|dblclick)="([^"]*)"/g;
let m;
while ((m = thuocTinh.exec(html)) !== null) {
  // Bỏ nội dung chuỗi trước đã: `showToast('... Vệ Tinh (Satellite Map)!')`
  // có một dấu mở ngoặc nằm TRONG chuỗi, và quét thô sẽ tưởng `Tinh` là tên
  // một hàm đang được gọi.
  const than = m[1].replace(/'[^']*'/g, "''").replace(/&quot;[^&]*&quot;/g, '');
  const goi = /(^|[^\w$.])([A-Za-z_$][\w$]*)\s*\(/g;
  let g;
  while ((g = goi.exec(than)) !== null) {
    const ten = g[2];
    if (BO_QUA.has(ten) || dinhNghia.has(ten)) continue;
    thieu.set(ten, (thieu.get(ten) || 0) + 1);
  }
}

assert.deepStrictEqual([...thieu.entries()], [],
  'thuộc tính on* gọi hàm không tồn tại — gõ vào là ReferenceError');

// Và hàm đã gỡ thì đừng còn dấu vết nào.
assert.ok(!html.includes('onCostComponentInput'));
assert.ok(!js.includes('renderCostFormulaView'));

// --- Nút chỉ hiện toast rồi không làm gì ---------------------------------
//
// Hai nút trên bản đồ lộ trình từng chạy đúng một lệnh:
// `showToast('Đang bật chế độ Vệ Tinh!')` và `showToast('Đang định vị xe!')`.
// Bản đồ không đổi một pixel nào. Người dùng bấm, đọc chữ "đang bật", rồi ngồi
// đợi một thứ không bao giờ tới. Nay nút Vệ Tinh đổi lớp nền thật, còn nút Vị
// Trí Xe đưa sang màn theo dõi GPS — trên bản đồ lộ trình không có xe nào để
// định vị cả.

{
  const nutDoi = [];
  const nut = /<button[^>]*onclick="([^"]*)"[^>]*>([\s\S]*?)<\/button>/g;
  let b;
  while ((b = nut.exec(html)) !== null) {
    const lenh = b[1].trim().replace(/;$/, '');
    if (/^(showToast|alert)\([^()]*(\([^()]*\))?[^()]*\)$/.test(lenh)) {
      nutDoi.push(b[2].replace(/<[^>]+>/g, '').trim().replace(/\s+/g, ' ') + ' -> ' + lenh);
    }
  }
  assert.deepStrictEqual(nutDoi, [],
    'nút chỉ hiện toast rồi không làm gì — hoặc cho nó chạy thật, hoặc gỡ đi');
}

// Nút Vệ Tinh phải đổi lớp nền THẬT, và hàm đó phải nạp được ảnh vệ tinh.
assert.ok(/id="nut-nen-ve-tinh"[^>]*onclick="doiNenBanDoLoTrinh\(\)"/.test(html)
  || /onclick="doiNenBanDoLoTrinh\(\)"[^>]*id="nut-nen-ve-tinh"/.test(html),
  'nút Vệ Tinh phải gọi hàm đổi nền thật');
assert.ok(/window\.doiNenBanDoLoTrinh = function/.test(js));
assert.ok(/World_Imagery/.test(js), 'phải có nguồn ảnh vệ tinh thật');
// Chưa mở bản đồ thì phải nói chưa sẵn sàng, không được báo "đã bật".
{
  const i = js.indexOf('window.doiNenBanDoLoTrinh = function');
  const than = js.slice(i, js.indexOf(String.fromCharCode(10) + '};', i));
  assert.ok(/chưa sẵn sàng/.test(than),
    'chưa có bản đồ thì phải nói thật, không được báo đã bật');
  assert.ok(/removeLayer/.test(than), 'phải gỡ lớp nền cũ, không chồng hai lớp');
}

console.log('onclick-goi-ham-co-that: tất cả kiểm tra đã qua');

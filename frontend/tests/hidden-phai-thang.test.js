/**
 * Thuộc tính `hidden` phải luôn thắng.
 *
 * `[hidden] { display: none }` là luật của TRÌNH DUYỆT. Bất kỳ luật `display:`
 * nào của trang cũng đè lên nó, vì luật của tác giả ưu tiên hơn luật của trình
 * duyệt. Hệ quả: một khối vừa có `.lớp { display: flex }` vừa được bật/tắt
 * bằng `el.hidden` thì KHÔNG BAO GIỜ ẩn đi được — nó hiện mãi.
 *
 * Đây là lỗi đã thấy trên ảnh chụp màn hình: thanh hành động của màn lập kế
 * hoạch nổi trên cả màn Tổng quan, ghi "0 DO Đã Chọn".
 *
 * Dự án đã vấp lỗi này BẢY LẦN trước đó, và lần nào cũng chỉ vá cho luật của
 * mình: `.dispatch-step-modal[hidden]`, `.driver-shift-pane[hidden]`,
 * `.dispatch-week-pane[hidden]`... Bảy lần vá cùng một lỗi là dấu hiệu thiếu
 * MỘT luật chung, không phải dấu hiệu cần vá lần thứ tám. Một phép đo tìm ra 9
 * chỗ vẫn còn hỏng lúc đó.
 *
 * Bài kiểm này giữ luật chung, và giữ luôn phép đo — để chỗ thứ mười không
 * lặng lẽ hỏng lại.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const NL = String.fromCharCode(10);
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8')
  .split(String.fromCharCode(13)).join('');

/**
 * Toàn bộ CSS của trang, đã bỏ thẻ `<style>` và mọi chú thích.
 *
 * Cả hai phép bỏ đều CẦN, và mỗi phép đã từng làm sai một kết quả:
 *  · không bỏ chú thích thì selector của một luật gồm cả chú thích đứng trên
 *    nó, nên `.do-fab` lọt lưới — phép đo báo "không có lỗi" trong khi lỗi
 *    đang hiện trên màn hình;
 *  · không bỏ thẻ thì selector của luật đầu mỗi bảng kiểu dính chuỗi
 *    `<style>`, nên luật chung `[hidden]` không tìm thấy dù nó đang có.
 */
function boChuThichVaThe(nguon) {
  return (nguon.match(/<style[^>]*>[\s\S]*?<\/style>/g) || [])
    .join(NL)
    .replace(/<\/?style[^>]*>/g, NL)
    .replace(/\/\*[\s\S]*?\*\//g, '');
}

// --- 1. Luật chung phải có, và phải `!important` -----------------------

{
  // Tách luật rồi so CẢ selector, chứ không dò chuỗi. Dò chuỗi thì kiểu gì
  // cũng có ca lọt: `.dispatch-step-modal[hidden]` lọt vì không có dấu cách,
  // và `.dispatch-cockpit-surface [hidden]` lọt vì CÓ dấu cách. Cả hai đều là
  // luật phạm vi hẹp, không phải luật chung — mà chúng làm phép kiểm xanh oan
  // đúng lúc luật chung đã mất.
  const luatHidden = [];
  const reMoiLuat = /([^{}]+)\{([^{}]*)\}/g;
  let r;
  // Bỏ CẢ thẻ <style> lẫn chú thích. Không bỏ thẻ thì selector của luật đầu
  // mỗi bảng kiểu dính luôn chuỗi "<style>", nên phép so `chon === '[hidden]'`
  // sai và phép đo báo KHÔNG tìm thấy luật chung dù nó đang có — tức đúng
  // kiểu xanh/đỏ oan mà bài kiểm này sinh ra để chặn.
  const kieu = boChuThichVaThe(html);
  while ((r = reMoiLuat.exec(kieu)) !== null) {
    // Selector của một luật có thể dính phần đuôi của luật trước; lấy đoạn
    // sau dấu `}` cuối cùng.
    const chon = r[1].split('}').pop().trim();
    if (chon === '[hidden]') luatHidden.push(r[2].trim());
  }
  assert.strictEqual(luatHidden.length, 1,
    `phải có đúng MỘT luật chung [hidden], thấy ${luatHidden.length}`);
  assert.ok(/^display:\s*none\s*!important;?$/.test(luatHidden[0]),
    `luật chung phải là display: none !important, thấy "${luatHidden[0]}"`);
  // Chứng cứ phép tách này thật sự loại được các luật phạm vi hẹp.
  assert.ok(/\.[a-z-]+\[hidden\]/.test(html) && /\.[a-z-]+ \[hidden\]/.test(html),
    'các luật [hidden] phạm vi hẹp vẫn còn trong tệp');

  // Và nó phải nằm trong bảng kiểu ĐẦU TIÊN, trước mọi luật `display:` khác.
  // Đặt sau thì thứ tự cascade không cứu được các luật cùng độ đặc hiệu...
  // thật ra `!important` thắng bất kể vị trí, nhưng đặt đầu là để người đọc
  // gặp nó trước, và để không ai vô tình đặt một `!important` khác lên trên.
  const bang1 = html.slice(html.indexOf('<style'), html.indexOf('</style>'));
  assert.ok(bang1.includes('[hidden] { display: none !important; }'),
    'luật chung phải ở bảng kiểu đầu tiên');
}

// --- 2. Không còn chỗ nào `hidden` bị đè -------------------------------
//
// Đo lại đúng phép đo đã tìm ra lỗi: lấy mọi lớp CÓ đặt `display:`, rồi đối
// chiếu với mọi id được bật/tắt bằng `.hidden =` trong app.js.

{
  const bangKieu = boChuThichVaThe(html);

  const coLuatHidden = /\[hidden\]\s*\{\s*display:\s*none\s*!important/.test(bangKieu);
  assert.ok(coLuatHidden, 'thiếu luật chung thì mọi phép đo dưới đây vô nghĩa');

  const coDisplay = new Map();
  const reLuat = /([^{}]+)\{([^{}]*)\}/g;
  let m;
  while ((m = reLuat.exec(bangKieu)) !== null) {
    const chon = m[1].trim();
    const than = m[2];
    if (chon.includes('@') || !chon.startsWith('.')) continue;
    if (!/(^|;)\s*display\s*:/.test(than)) continue;
    const gt = /display\s*:\s*([^;]+)/.exec(than)[1].trim();
    chon.split(',').forEach(mot => {
      mot = mot.trim();
      if (/^\.[a-zA-Z0-9_-]+$/.test(mot)) coDisplay.set(mot.slice(1), gt);
    });
  }
  assert.ok(coDisplay.size > 20, `phép đò phải thấy nhiều lớp, thấy ${coDisplay.size}`);
  // Chứng cứ phép đo còn chạy đúng: `.do-fab` là lớp có chú thích đứng trên,
  // đúng ca đã từng lọt lưới.
  assert.strictEqual(coDisplay.get('do-fab'), 'flex',
    'phép đo phải thấy .do-fab — nó là ca đã lọt lưới trước đây');

  // Id nào được bật/tắt bằng `.hidden =`?
  const bangHidden = new Set();
  const reKhai = /(?:const|let|var)\s+(\w+)\s*=\s*document\.getElementById\(['"]([\w-]+)['"]\)/g;
  while ((m = reKhai.exec(app)) !== null) {
    const ten = m[1].replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    if (new RegExp('\\b' + ten + '\\.hidden\\s*=').test(app)) bangHidden.add(m[2]);
  }
  const reTrucTiep = /getElementById\(['"]([\w-]+)['"]\)\s*\.hidden\s*=/g;
  while ((m = reTrucTiep.exec(app)) !== null) bangHidden.add(m[1]);
  assert.ok(bangHidden.size > 20,
    `phải thấy nhiều id bật/tắt bằng hidden, thấy ${bangHidden.size}`);
  assert.ok(bangHidden.has('do-fab'), 'phải thấy #do-fab');

  // Khối nào mang lớp có `display:` mà lại được bật/tắt bằng `hidden`?
  const nguyCo = [];
  bangHidden.forEach(maId => {
    const i = html.indexOf(`id="${maId}"`);
    if (i < 0) return;
    const truoc = html.slice(Math.max(0, i - 220), i);
    const mc = /class="([^"]*)"\s*$/.exec(truoc.replace(/\s+$/, '') + ' ')
      || /class="([^"]*)"[^"]*$/.exec(truoc);
    if (!mc) return;
    mc[1].split(/\s+/).forEach(lop => {
      if (coDisplay.has(lop)) nguyCo.push(`#${maId} mang .${lop} (display: ${coDisplay.get(lop)})`);
    });
  });
  // Có nguy cơ là BÌNH THƯỜNG — luật chung đã trung hòa hết. Điều bài kiểm
  // này giữ là: nếu luật chung mất đi thì 9 chỗ này hỏng ngay, nên nó phải
  // còn. Khẳng định lại một lần nữa cho rõ vì sao.
  assert.ok(nguyCo.length > 0,
    'phép đo phải thấy các chỗ phụ thuộc luật chung, không thì nó đã hỏng');
  assert.ok(coLuatHidden,
    `${nguyCo.length} khối phụ thuộc luật chung [hidden]:${NL}  `
    + nguyCo.slice(0, 12).join(NL + '  '));
}

// --- 3. Thanh hành động không được đi theo người dùng sang màn khác ----
//
// Thanh là `position: fixed`, không nằm trong khung màn nào. Sửa lỗi trên
// xong thì lúc chưa tick gì nó ẩn đúng, nhưng tick DO rồi rời màn lập kế
// hoạch thì nó vẫn nổi trên màn mới, mang theo nút "Tạo Trip" của màn cũ.

{
  const i = app.indexOf('window.switchView = function');
  assert.ok(i > 0, 'không thấy switchView');
  const than = app.slice(i, app.indexOf(NL + '};', i));
  assert.ok(/targetView !== 'ops-planning'[\s\S]{0,160}boChonTatCaDO\(\)/.test(than),
    'rời màn lập kế hoạch thì phải bỏ chọn DO');
  // Và phải kiểm hàm tồn tại trước khi gọi: switchView chạy ở MỌI màn, kể cả
  // khi khối lập kế hoạch chưa được nạp.
  assert.ok(/typeof boChonTatCaDO === 'function'/.test(than),
    'phải kiểm hàm tồn tại — switchView chạy trên mọi màn');
  assert.ok(/typeof doDaChon !== 'undefined'/.test(than),
    'phải kiểm biến tồn tại');
}

{
  // `boChonTatCaDO` phải dọn CẢ BA thứ: tập đã chọn, ô "chọn tất cả", và vẽ
  // lại thanh. Thiếu cái thứ ba thì thanh vẫn hiện với số cũ.
  const i = app.indexOf('window.boChonTatCaDO = function');
  assert.ok(i > 0, 'không thấy boChonTatCaDO');
  const than = app.slice(i, app.indexOf(NL + '};', i));
  assert.ok(/doDaChon\.clear\(\)/.test(than), 'phải xóa tập đã chọn');
  assert.ok(/do-pick-all/.test(than), 'phải bỏ tick ô "chọn tất cả"');
  assert.ok(/veThanhHanhDong\(\)/.test(than), 'phải vẽ lại thanh');
}

console.log('hidden-phai-thang: tất cả kiểm tra đã qua');

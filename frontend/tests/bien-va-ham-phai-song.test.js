/**
 * Hai loại lỗi âm thầm làm cả màn hình chết mà 67 bài kiểm khác không bắt.
 *
 * === LOẠI 1: biến được gán mà không hề khai báo ===
 *
 * Ở chế độ không strict, `X = 1` tạo một biến toàn cục ngầm — nên GHI thì
 * không báo gì. Nhưng ĐỌC nó trước lần ghi đầu tiên là ReferenceError, và lỗi
 * đó làm cả hàm dừng giữa.
 *
 * Tìm được sáu cái:
 *   tripReturnStatusFilter, activeTripReturnId, tripReturnSearchQuery,
 *   tripReturnActionSequence, activeTripReturnDetailTab
 *       -> `renderTripReturnCockpit` đọc `tripReturnStatusFilter` ở dòng lọc,
 *          nổ, dừng giữa hàm. Màn "Giao hàng & vận chuyển" báo "Chưa có
 *          chuyến đang chạy" trong khi Postgres có 2 chuyến `in_transit` và
 *          API trả về đủ 3. Nhìn vào thì tưởng lỗi dữ liệu.
 *          Năm dòng `let` này bị XÓA MẤT khi tôi gỡ chín trình vẽ chết: tôi
 *          cắt theo khoảng "từ hàm này đến hàm kế tiếp", mà chúng nằm đúng
 *          giữa hai hàm đó.
 *   (currentSourceQuotationId — thuộc form Đơn hàng, đã trục xuất cùng SO.)
 *
 * === LOẠI 2: hàm bị khối chú thích nuốt ===
 *
 * `renderDispatchSuggestedActions` mở `/* Legacy suggestions are
 * intentionally disabled ...` ở một dòng, và `*​/` nằm cách đó 201 DÒNG — nên
 * khối chú thích nuốt luôn NĂM HÀM ĐANG DÙNG:
 *     setDispatchResourceSelect, renderDispatchResourceChangePanel,
 *     openDispatchResourceChange, closeDispatchResourceChange,
 *     applyDispatchResourceChange
 * Nút "Lưu điều phối" và "Hủy" trên bảng đổi xe/tài xế gọi hai hàm cuối —
 * chúng không tồn tại, nên bấm vào không có gì xảy ra. Lỗi có từ commit
 * `7040994`, tức trước toàn bộ công việc trong dự án này.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const NL = String.fromCharCode(10);
const raw = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8')
  .split(String.fromCharCode(13)).join('');

// --- LOẠI 1: biến gán mà không khai báo -----------------------------

{
  // Bỏ chú thích và chuỗi trước, để không bắt vào văn bản.
  const ma = raw
    .replace(/\/\*[\s\S]*?\*\//g, ' ')
    .split(NL).map(d => d.replace(/\/\/.*$/, '')).join(NL)
    .replace(/`(?:\\.|[^`\\])*`/g, '``')
    .replace(/'(?:\\.|[^'\\\n])*'/g, "''")
    .replace(/"(?:\\.|[^"\\\n])*"/g, '""');

  const daKhai = new Set();
  for (const re of [
    // Bắt CẢ danh sách nhiều tên trên một dòng: `let khoa, ten, phu;`.
    //
    // Bản trước chỉ bắt tên ĐẦU TIÊN sau `let`, nên một cách viết hoàn toàn
    // bình thường làm bài kiểm báo oan: `phu` bị liệt là "gán mà không khai
    // báo" trong khi nó được khai ở cùng dòng với `khoa`. Báo oan còn tệ hơn
    // không báo, vì người đọc mất lòng tin vào cả bài kiểm rồi bỏ qua luôn
    // những dòng báo đúng.
    /\b(?:let|const|var)\s+([A-Za-z_$][\w$]*(?:\s*,\s*[A-Za-z_$][\w$]*)*)\s*[;=]/g,
    /\b(?:let|const|var)\s+([A-Za-z_$][\w$]*)/g,
    /\bfunction\s+([A-Za-z_$][\w$]*)/g,
    /\bclass\s+([A-Za-z_$][\w$]*)/g,
    /\bcatch\s*\(\s*([A-Za-z_$][\w$]*)/g,
    /\bfunction[^(]*\(([^)]*)\)/g,
    /\(([^()]*)\)\s*=>/g,
    /\b([A-Za-z_$][\w$]*)\s*=>/g,
    /\b(?:let|const|var)\s*[{[]([^}\]]*)[}\]]/g,
    /\bfor\s*\(\s*(?:let|const|var)\s+([A-Za-z_$][\w$]*)/g,
  ]) {
    let m;
    while ((m = re.exec(ma)) !== null) {
      String(m[1]).split(',').forEach(x => {
        const t = x.trim().split(/[:=\s]/)[0].replace(/^\.\.\./, '');
        if (/^[A-Za-z_$][\w$]*$/.test(t)) daKhai.add(t);
      });
    }
  }

  const SAN_CO = new Set(['window', 'document', 'console', 'Math', 'JSON', 'Date',
    'Number', 'String', 'Boolean', 'Array', 'Object', 'Promise', 'Set', 'Map',
    'RegExp', 'Error', 'Intl', 'URL', 'URLSearchParams', 'FormData', 'Headers',
    'localStorage', 'sessionStorage', 'location', 'navigator', 'history',
    'setTimeout', 'clearTimeout', 'setInterval', 'clearInterval', 'fetch',
    'alert', 'confirm', 'prompt', 'requestAnimationFrame', 'CSS',
    'L', 'Chart', 'module', 'exports', 'require', 'globalThis', 'undefined',
    'NaN', 'Infinity', 'arguments', 'this', 'crypto', 'Image', 'Event',
    'encodeURIComponent', 'decodeURIComponent', 'parseInt', 'parseFloat',
    'isNaN', 'isFinite', 'Symbol', 'WeakMap', 'MouseEvent', 'CustomEvent',
    // Đây là THUỘC TÍNH HTML nằm trong chuỗi mà phép lọc trên không bỏ hết —
    // `onclick=`, `oninput=`, `onchange=` trong template. Không phải biến.
    'onclick', 'oninput', 'onchange', 'onsubmit', 'onkeyup', 'onblur']);

  const nghi = new Map();
  ma.split(NL).forEach((dong, i) => {
    const m = dong.match(/^\s+([A-Za-z_$][\w$]*)\s*(?:=(?!=|>)|\+=|-=|\|\|=|\?\?=)/);
    if (!m) return;
    const ten = m[1];
    if (daKhai.has(ten) || SAN_CO.has(ten)) return;
    if (!nghi.has(ten)) nghi.set(ten, []);
    nghi.get(ten).push(i + 1);
  });

  const bao = [...nghi.entries()].map(([t, d]) => `${t} (dòng ${d.slice(0, 3).join(',')})`);
  assert.deepStrictEqual(bao, [],
    'biến được gán mà không hề khai báo — đọc nó trước lần ghi đầu tiên là'
    + ' ReferenceError, và cả hàm dừng giữa');

  // Và năm biến đã tìm được phải có khai báo thật.
  ['tripReturnStatusFilter', 'activeTripReturnId', 'tripReturnSearchQuery',
    'tripReturnActionSequence', 'activeTripReturnDetailTab'].forEach(ten => {
    assert.ok(new RegExp(`\\blet ${ten}\\b`).test(raw), `thiếu khai báo ${ten}`);
  });
}

// --- LOẠI 2: hàm bị khối chú thích nuốt ----------------------------
//
// Phép kiểm này NẠP THẬT app.js rồi hỏi `typeof` từng hàm khai ở cột 0. Đọc
// văn bản không bắt được, vì trên văn bản thì hàm vẫn "có mặt" — nó chỉ nằm
// trong một khối `/* ... */`.

let JSDOM;
try {
  ({ JSDOM } = require('jsdom'));
} catch (e) {
  console.log('bien-va-ham-phai-song: BỎ QUA phần nạp thật (chưa có jsdom)');
  console.log('bien-va-ham-phai-song: phần kiểm biến đã qua');
  process.exit(0);
}
const { VirtualConsole } = require('jsdom');

const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const dom = new JSDOM(
  html.replace(/<script\b[^>]*src="[^"]*"[^>]*><\/script>/g, '')
      .replace(/<link\b[^>]*>/g, ''),
  { url: 'http://127.0.0.1/', runScripts: 'dangerously', virtualConsole: new VirtualConsole() });
const w = dom.window;
w.fetch = () => Promise.resolve({
  ok: true, status: 200, json: () => Promise.resolve({ items: [], total: 0 }) });
w.alert = () => {};
w.confirm = () => true;
w.CSS = w.CSS || { escape: s => String(s) };

(html.match(/src="\/static\/js\/([a-z0-9-]+\.js)/g) || [])
  .map(x => x.replace('src="/static/js/', ''))
  .forEach(ten => {
    const s = w.document.createElement('script');
    s.textContent = fs.readFileSync(path.join(ROOT, 'js', ten), 'utf8');
    w.document.body.appendChild(s);
  });

{
  // Mọi hàm khai ở CỘT 0 phải thành hàm toàn cục.
  const chetLang = [];
  raw.split(NL).forEach((d, i) => {
    const m = d.match(/^(?:async )?function ([A-Za-z_$][\w$]*)/);
    if (!m) return;
    let co = typeof w[m[1]] === 'function';
    if (!co) { try { co = w.eval('typeof ' + m[1]) === 'function'; } catch (e) { co = false; } }
    if (!co) chetLang.push(`${m[1]} (dòng ${i + 1})`);
  });
  assert.deepStrictEqual(chetLang, [],
    'hàm khai ở cột 0 mà không thành hàm toàn cục — gần như luôn là do một'
    + ' khối /* ... */ nuốt nó; nút gọi nó sẽ bấm mà không có gì xảy ra');
}

{
  // Và mọi hàm mà thuộc tính on* gọi tới phải tồn tại.
  const BO_QUA = new Set(['if', 'for', 'while', 'return', 'typeof', 'alert',
    'confirm', 'prompt', 'parseInt', 'parseFloat', 'Number', 'String',
    'Boolean', 'Array', 'Object', 'JSON', 'Math', 'Date', 'setTimeout',
    'setInterval', 'catch', 'encodeURIComponent', 'decodeURIComponent']);
  const thieu = new Map();
  w.document.querySelectorAll('[onclick],[onchange],[oninput],[onsubmit]').forEach(el => {
    ['onclick', 'onchange', 'oninput', 'onsubmit'].forEach(attr => {
      const ma = el.getAttribute(attr);
      if (!ma) return;
      // Bỏ nội dung chuỗi: `showToast('... Vệ Tinh (Satellite)')` có dấu mở
      // ngoặc NẰM TRONG chuỗi, và quét thô tưởng đó là tên hàm.
      const sach = ma.replace(/'[^']*'/g, "''").replace(/"[^"]*"/g, '""');
      for (const m of sach.matchAll(/(^|[^\w$.])([A-Za-z_$][\w$]*)\s*\(/g)) {
        const ten = m[2];
        if (BO_QUA.has(ten)) continue;
        let co = typeof w[ten] === 'function';
        if (!co) { try { co = w.eval('typeof ' + ten) === 'function'; } catch (e) { co = false; } }
        if (!co) thieu.set(ten, (thieu.get(ten) || 0) + 1);
      }
    });
  });
  assert.deepStrictEqual([...thieu.keys()], [],
    'thuộc tính on* gọi hàm không tồn tại — bấm vào không có gì xảy ra');
}

console.log('bien-va-ham-phai-song: tất cả kiểm tra đã qua');
process.exit(0);

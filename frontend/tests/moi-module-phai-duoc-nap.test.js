/**
 * Mọi module `window.X` mà app.js đọc Ở CẤP CAO NHẤT đều phải có thẻ script
 * trong index.html.
 *
 * Đây là bài học từ một lỗi làm sập một nửa ứng dụng và im lặng suốt.
 *
 * `js/do-board.js` tồn tại, có test riêng, và xuất `window.DoBoard`. Nhưng
 * index.html KHÔNG nạp nó. Trong khi app.js có, ở cấp cao nhất:
 *
 *     const DELIVERY_ORDER_STAGES = window.DoBoard.BUCKETS.map(b => b.key);
 *
 * `window.DoBoard` là `undefined` nên dòng đó ném TypeError NGAY LÚC NẠP
 * app.js — và một lỗi lúc nạp làm TOÀN BỘ phần còn lại của tệp không bao giờ
 * được thực thi. Dòng đó ở khoảng 7.470 trên 17.000 dòng, nên mất luôn:
 *
 *     renderDeliveryOrders   renderRoutes        initLeafletRouteMap
 *     renderFioriDrivers     loadIncidents       và ~9.500 dòng nữa
 *
 * Trên màn hình: các bước 3 đến 7 của luồng (Lệnh DO, Tuyến đường, Điều phối,
 * GPS & POD, Hóa đơn) đều rỗng, và bản đồ tuyến đường mất hết điểm vẽ. Hai
 * triệu chứng trông không liên quan gì nhau, mà cùng một nguyên nhân.
 *
 * Vì sao nó im lặng lâu: lỗi chỉ hiện trong Console của trình duyệt. Không
 * một bài kiểm nào bắt được, vì mọi bài kiểm đều đọc `app.js` như VĂN BẢN —
 * chưa bài nào NẠP nó như trình duyệt nạp.
 *
 * Bài kiểm này làm hai việc: đối chiếu tĩnh danh sách module, và NẠP THẬT cả
 * trang trong jsdom để bắt mọi lỗi lúc nạp.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8')
  .split(String.fromCharCode(13)).join('');

// --- 1. Đối chiếu tĩnh: window.X đọc ở cấp cao nhất ↔ thẻ script ------

const scriptTags = [...html.matchAll(/src="\/static\/js\/([a-z0-9-]+\.js)/g)].map(m => m[1]);

// `window.X` xuất hiện ở đầu một dòng KHÔNG thụt lề (tức cấp cao nhất của
// tệp) là chỗ chạy ngay lúc nạp. Trong thân hàm thì nó chạy muộn hơn, và ở đó
// người viết còn có thể bọc `if (window.X)` — nên chỉ cấp cao nhất là bắt buộc.
const docLucNap = new Set();
app.split(String.fromCharCode(10)).forEach(dong => {
  if (/^\s/.test(dong) || dong.trim().startsWith('//') || dong.trim().startsWith('*')) return;
  for (const m of dong.matchAll(/window\.([A-Z][A-Za-z0-9_]*)\s*[.[]/g)) {
    docLucNap.add(m[1]);
  }
});

assert.ok(docLucNap.size > 0, 'phép dò không tìm thấy gì — hãy xem lại chính nó');
assert.ok(docLucNap.has('DoBoard'),
  'phải nhận ra được window.DoBoard — đúng module đã gây ra lỗi này');

// Tên module -> tệp khai báo nó.
const khaiBao = {};
fs.readdirSync(path.join(ROOT, 'js')).filter(f => f.endsWith('.js')).forEach(f => {
  const ma = fs.readFileSync(path.join(ROOT, 'js', f), 'utf8');
  for (const m of ma.matchAll(/root\.([A-Z][A-Za-z0-9_]*)\s*=\s*factory|window\.([A-Z][A-Za-z0-9_]*)\s*=\s*(?:factory|\{|function)/g)) {
    khaiBao[m[1] || m[2]] = f;
  }
});

const thieuThe = [];
docLucNap.forEach(ten => {
  const tep = khaiBao[ten];
  if (!tep) return;                       // module ngoài (Chart, L, …)
  if (!scriptTags.includes(tep)) thieuThe.push(`${ten} (${tep})`);
});
assert.deepStrictEqual(thieuThe, [],
  'app.js đọc module này lúc nạp nhưng index.html không nạp nó — cả phần còn'
  + ' lại của app.js sẽ không được thực thi');

// do-board.js phải nạp TRƯỚC app.js.
{
  const iDo = scriptTags.indexOf('do-board.js');
  const iApp = scriptTags.indexOf('app.js');
  assert.ok(iDo >= 0, 'index.html phải nạp do-board.js');
  assert.ok(iApp >= 0);
  assert.ok(iDo < iApp, 'do-board.js phải nạp TRƯỚC app.js');
}

// --- 2. Thư viện ngoài (CDN) phải được bọc ---------------------------
//
// Chart.js đến từ cdn.jsdelivr.net. Hệ thống chạy trên mạng nội bộ, nơi CDN
// bị chặn là chuyện thường — và `new Chart(...)` không bọc thì ném
// ReferenceError giữa `renderSummaryChart`, vốn nằm trong chuỗi khởi động của
// `loadAllData`. Mất mạng ra CDN sẽ làm ĐỨT cả bảng điều khiển, không chỉ mất
// mấy cái biểu đồ.

{
  const i = app.indexOf('function renderSummaryChart()');
  assert.ok(i > 0);
  const than = app.slice(i, i + 1200);
  assert.ok(/typeof Chart === 'undefined'/.test(than),
    'renderSummaryChart phải kiểm Chart.js có nạp được không rồi mới vẽ');
  assert.ok(/return;/.test(than), 'thiếu Chart.js thì thoát êm, không ném');
}

// --- 3. Nạp THẬT cả trang trong jsdom -------------------------------
//
// Đây là phần bắt được lỗi mà đối chiếu văn bản không bắt được. Mọi bài kiểm
// khác đọc app.js như văn bản; chưa bài nào NẠP nó như trình duyệt.

let JSDOM;
try {
  ({ JSDOM } = require('jsdom'));
} catch (e) {
  console.log('moi-module-phai-duoc-nap: BỎ QUA phần nạp thật (chưa có jsdom)');
  console.log('moi-module-phai-duoc-nap: hai phần đối chiếu tĩnh đã qua');
  process.exit(0);
}

const { VirtualConsole } = require('jsdom');
const loiLucNap = [];
const vc = new VirtualConsole();
vc.on('jsdomError', e => loiLucNap.push(String((e && e.message) || e)));

const thanTrang = html
  // Bỏ script ngoài (CDN) và stylesheet: bài kiểm này lo phần MÌNH viết.
  .replace(/<script\b[^>]*src="[^"]*"[^>]*><\/script>/g, '')
  .replace(/<link\b[^>]*>/g, '');

const dom = new JSDOM(thanTrang, {
  url: 'http://127.0.0.1/',
  runScripts: 'dangerously',
  virtualConsole: vc,
});
const w = dom.window;
// Không gọi mạng, không hộp thoại.
w.fetch = () => Promise.resolve({
  ok: true, status: 200,
  json: () => Promise.resolve({ items: [], total: 0 }),
});
w.alert = () => {};
w.confirm = () => true;

scriptTags.forEach(ten => {
  const s = w.document.createElement('script');
  s.textContent = fs.readFileSync(path.join(ROOT, 'js', ten), 'utf8');
  w.document.body.appendChild(s);
});

assert.deepStrictEqual(loiLucNap, [],
  'có lỗi khi NẠP các tệp JS — mọi thứ sau chỗ ném sẽ không được định nghĩa');

// Và những hàm nằm SAU dòng `window.DoBoard.BUCKETS` phải thật sự tồn tại.
// Đây là phép kiểm trực tiếp cho triệu chứng người dùng thấy.
const PHAI_CO = [
  'renderDeliveryOrders', 'renderRoutes', 'initLeafletRouteMap',
  'renderFioriDrivers', 'loadIncidents', 'huyLenhGiaoHang', 'xoaTuyenDuong',
];
const khongCo = PHAI_CO.filter(ten => {
  if (typeof w[ten] === 'function') return false;
  try {
    return w.eval('typeof ' + ten) !== 'function';
  } catch (e) {
    return true;
  }
});
assert.deepStrictEqual(khongCo, [],
  'các hàm này nằm sau chỗ đọc window.DoBoard — thiếu chúng nghĩa là app.js'
  + ' lại đứt giữa lúc nạp');

// `DELIVERY_ORDER_STAGES` phải có giá trị, không nằm trong vùng chết (TDZ).
const stages = w.eval('DELIVERY_ORDER_STAGES');
assert.ok(Array.isArray(stages) && stages.length >= 5, JSON.stringify(stages));

console.log('moi-module-phai-duoc-nap: tất cả kiểm tra đã qua');
process.exit(0);

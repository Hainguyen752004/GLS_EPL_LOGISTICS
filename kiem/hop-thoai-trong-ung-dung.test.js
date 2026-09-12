/**
 * TRANG TÀI XẾ KHÔNG ĐƯỢC DÙNG HỘP THOẠI GỐC CỦA TRÌNH DUYỆT.
 *
 * Chủ dự án đã bỏ confirm()/prompt() bên hệ thống chính vì hộp gốc in kèm dòng
 * "127.0.0.1:8090 says" — khách xem demo đọc thấy địa chỉ máy chủ, còn tài xế đứng ở cổng
 * cảng thì không hiểu đó là cái gì. Trang tài xế sót lại hai chỗ: nút "Ghi mốc" và ô đổi địa
 * chỉ máy chủ. Bài này khoá cả hai.
 *
 * Chạy: node kiem/hop-thoai-trong-ung-dung.test.js
 * (dùng jsdom trong EPL_System/frontend/node_modules)
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const GOC = path.join(__dirname, '..');
const { JSDOM } = require(path.join(GOC, '..', 'EPL_System', 'frontend', 'node_modules', 'jsdom'));

/* ---- một dòng bảng theo dõi đủ để nút "Ghi mốc" bật ---- */
const DONG = {
  key: 'TRIP-1:DO-1', trip_id: 'TRIP-1', trip_status: 'in_transit',
  freight_order_id: 'FO-TRIP-1', freight_order_version: 5,
  do_id: 'DO-2026-0050-DO01', status: 'departed', customer_name: 'Vinamilk Bình Dương',
  vehicle_id: 'DEMO-61H-888.02', driver_id: 'DEMO-DRV-015', driver_name: 'Somsak Phommachanh',
  route_name: 'Sóng Thần → Cảng Cát Lái', origin: 'Bãi Sóng Thần', destination: 'Cảng Cát Lái',
  route_distance_km: 31.2, next_milestone: { ma: 'arrival', ten: 'Đến điểm giao' },
  milestones: [], events: [], legs: [], pods: [], incidents: [],
  gps: { status: 'simulated', lat: 10.8, lng: 106.75 }, awaiting_pod: false, overdue: false,
};

const goiGoc = [];          // mọi lần trang gọi hộp thoại gốc đều ghi vào đây
const loiJS = [];
const daPOST = [];

const html = fs.readFileSync(path.join(GOC, 'web', 'index.html'), 'utf8')
  .split('<script src="js/ngon-ngu.js?v=1"></script>').join('')
  .split('<script src="js/tai-xe.js?v=3"></script>').join('')
  .replace(/<script src="https:[^"]*"><\/script>/g, '')
  .replace(/<link rel="stylesheet" href="https:[^"]*">/g, '');

const dom = new JSDOM(html, {
  url: 'http://localhost:8099/', runScripts: 'dangerously', pretendToBeVisual: true,
  beforeParse(w) {
    w.confirm = function () { goiGoc.push('confirm'); return true; };
    w.alert = function (m) { goiGoc.push('alert: ' + m); };
    w.prompt = function () { goiGoc.push('prompt'); return null; };
    w.fetch = function (u, o) {
      const duong = String(u);
      if ((o || {}).method === 'POST') { daPOST.push({ duong: duong, than: JSON.parse(o.body) }); }
      const than = duong.indexOf('/api/drivers') >= 0
        ? [{ id: 'DEMO-DRV-015', name: 'Somsak Phommachanh', role: 'Lái xe chính' }]
        : duong.indexOf('control-tower') >= 0 ? { items: [DONG], kpis: {} } : {};
      return Promise.resolve({ status: 200, ok: true, text: () => Promise.resolve(JSON.stringify(than)) });
    };
    w.addEventListener('error', (e) => loiJS.push(String(e.message)));
  },
});
const w = dom.window;
w.HTMLElement.prototype.scrollIntoView = function () {};
w.HTMLCanvasElement.prototype.getContext = () => ({
  scale() {}, beginPath() {}, moveTo() {}, lineTo() {}, stroke() {}, clearRect() {},
  set lineWidth(v) {}, set lineCap(v) {}, set strokeStyle(v) {},
});
// jsdom chưa dựng <dialog>: dựng tối thiểu, giữ đúng sự kiện `close` mà mã nguồn nghe.
w.HTMLDialogElement.prototype.showModal = function () { this.open = true; };
w.HTMLDialogElement.prototype.close = function () {
  if (!this.open) return;
  this.open = false;
  this.dispatchEvent(new w.Event('close'));
};

// Nạp ĐÚNG thứ tự như trang thật: bảng chữ trước, rồi mã ứng dụng.
['ngon-ngu.js', 'tai-xe.js'].forEach(function (ten) {
  const s = w.document.createElement('script');
  s.textContent = fs.readFileSync(path.join(GOC, 'web', 'js', ten), 'utf8');
  w.document.body.appendChild(s);
});

const d = w.document;
const el = (id) => d.getElementById(id);
const ngu = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  await ngu(600);
  assert.deepStrictEqual(loiJS, [], 'trang có lỗi JS: ' + loiJS.join(' | '));

  /* 1. Nguồn: không còn một lời gọi hộp thoại gốc nào trong mã.
   *    Bỏ chú thích trước khi soi — chính chú thích giải thích vì sao không dùng chúng cũng
   *    có chữ `confirm()`, và bắt cả chú thích thì bài kiểm này không bao giờ xanh được. */
  const ma = fs.readFileSync(path.join(GOC, 'web', 'js', 'tai-xe.js'), 'utf8')
    .replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:])\/\/.*$/gm, '$1');
  const sot = ma.match(/window\.(confirm|alert|prompt)\s*\(|[^.\w](confirm|alert|prompt)\s*\(/g) || [];
  assert.deepStrictEqual(sot, [], 'còn hộp thoại gốc trong mã: ' + sot.join(', '));

  /* 2. Chọn tài xế → mở chuyến → bấm "Ghi mốc". */
  const chon = el('chon-taixe');
  chon.value = 'DEMO-DRV-015';
  chon.dispatchEvent(new w.Event('change'));
  await ngu(400);

  const the = d.querySelector('#ds [data-key]');
  assert.ok(the, 'không thấy thẻ chuyến nào');
  the.click();
  await ngu(300);

  const nutMoc = el('nut-moc');
  assert.ok(nutMoc && !nutMoc.disabled, 'nút Ghi mốc phải bật khi có mốc kế tiếp');
  nutMoc.click();
  await ngu(200);

  /* 3. Hộp TRONG ỨNG DỤNG mở ra, KHÔNG phải hộp của trình duyệt. */
  assert.deepStrictEqual(goiGoc, [], 'vẫn gọi hộp thoại gốc: ' + goiGoc.join(', '));
  const hop = el('hop-xacnhan');
  assert.strictEqual(hop.open, true, 'hộp xác nhận trong ứng dụng phải mở');
  assert.match(el('xn-tieude').textContent, /Đến điểm giao/, 'tiêu đề phải nêu tên mốc');
  assert.match(el('xn-noidung').textContent, /DO-2026-0050-DO01/, 'nội dung phải nêu mã lệnh');
  assert.match(el('xn-noidung').textContent, /Không hoàn lại/, 'phải nói rõ không hoàn lại được');

  /* 4. Hai nút GỌI TÊN VIỆC, không phải OK/Cancel. */
  assert.strictEqual(el('xn-ok').textContent, 'Ghi mốc');
  assert.strictEqual(el('xn-huy').textContent, 'Chưa ghi');
  assert.ok(!/^(OK|Cancel|Đồng ý|Huỷ)$/.test(el('xn-ok').textContent),
    'nút chính phải gọi tên việc sẽ làm');
  assert.strictEqual(el('xn-boc-nhap').hidden, true, 'hộp xác nhận không có ô nhập');

  /* 5. Bấm "Chưa ghi" → đóng hộp và KHÔNG gửi gì. */
  const truoc = daPOST.length;
  el('xn-huy').click();
  await ngu(200);
  assert.strictEqual(hop.open, false, 'bấm Chưa ghi phải đóng hộp');
  assert.strictEqual(daPOST.length, truoc, 'bấm Chưa ghi mà vẫn gửi mốc lên máy chủ');

  /* 6. Bấm lại, chọn "Ghi mốc" → gửi đúng một lần, đúng đường và đúng phiên bản. */
  nutMoc.click();
  await ngu(200);
  el('xn-ok').click();
  await ngu(400);
  assert.strictEqual(hop.open, false, 'bấm Ghi mốc phải đóng hộp');
  const gui = daPOST.filter((x) => x.duong.indexOf('/events') >= 0);
  assert.strictEqual(gui.length, 1, 'phải gửi đúng một sự kiện, đang có ' + gui.length);
  assert.strictEqual(gui[0].than.event_type, 'arrival');
  assert.strictEqual(gui[0].than.expected_version, 5, 'phải gửi đúng phiên bản lệnh vận chuyển');
  assert.deepStrictEqual(goiGoc, [], 'vẫn gọi hộp thoại gốc: ' + goiGoc.join(', '));

  /* 7. Phím Esc đóng hộp = huỷ, không gửi gì. */
  nutMoc.click();
  await ngu(200);
  const truoc2 = daPOST.length;
  hop.close();                       // trình duyệt thật phát `close` khi bấm Esc
  await ngu(200);
  assert.strictEqual(daPOST.length, truoc2, 'đóng bằng Esc mà vẫn gửi mốc');

  console.log('hop-thoai-trong-ung-dung: OK — 7 phần, không còn hộp thoại gốc nào');
  process.exit(0);
})().catch((e) => { console.error('HỎNG:', e && e.message); process.exit(1); });

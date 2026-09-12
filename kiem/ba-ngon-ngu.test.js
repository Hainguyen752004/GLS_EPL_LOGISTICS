/**
 * TRANG TÀI XẾ PHẢI NÓI ĐƯỢC BA THỨ TIẾNG — và mỗi câu phải TRỌN một thứ tiếng.
 *
 * Tài xế chạy tuyến Viêng Chăn → Cảng Cửa Lò là người Lào. Bài này khoá bốn điều:
 *   1. Ba khoá ngôn ngữ có ĐỦ như nhau — thiếu một khoá ở tiếng Lào là chỗ đó rơi về
 *      tiếng Việt, tức một câu lai ngay giữa màn hình.
 *   2. Đổi ngôn ngữ vẽ lại CẢ phần do JS sinh ra, không chỉ nhãn tĩnh.
 *   3. Ở tiếng Lào KHÔNG còn chữ tiếng Việt nào trên màn — kể cả tên mốc, thứ mà máy chủ
 *      trả về bằng tiếng Việt và trang phải tự dịch lại theo mã mốc.
 *   4. Lựa chọn được nhớ qua lần mở sau.
 *
 * Chạy: node kiem/ba-ngon-ngu.test.js
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const GOC = path.join(__dirname, '..');
const { JSDOM } = require(path.join(GOC, '..', 'EPL_System', 'frontend', 'node_modules', 'jsdom'));

/** Dấu tiếng Việt — chữ không dấu (Somsak, Vinamilk) không tính. */
const VIET = /[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]/i;

const DONG = {
  key: 'T1:DO-1', trip_id: 'TRIP-1', trip_status: 'in_transit',
  freight_order_id: 'FO-1', freight_order_version: 5,
  do_id: 'DO-2026-0053-DO01', status: 'departed', customer_name: 'Vinamilk',
  vehicle_id: 'DEMO-51C-252.05', driver_id: 'DEMO-DRV-018', driver_name: 'Thongdy Keomany',
  route_name: 'Vientiane - Cua Lo', origin: 'Vientiane', destination: 'Cua Lo',
  route_distance_km: 475,
  // Máy chủ trả tên mốc bằng TIẾNG VIỆT. Trang phải dịch lại theo `ma`, không dùng `ten`.
  next_milestone: { ma: 'arrival', ten: 'Đến điểm giao' },
  milestones: [], events: [],
  legs: [{ id: 'L1', origin: 'Vientiane', destination: 'Cua Lo', type: 'delivery',
           status: 'pending', planned_arrival_at: '2026-09-15T12:00:00Z' }],
  pods: [], incidents: [], gps: { status: 'simulated', lat: 18, lng: 104 },
  awaiting_pod: false, overdue: false,
};

const loiJS = [];
const html = fs.readFileSync(path.join(GOC, 'web', 'index.html'), 'utf8')
  .split('<script src="js/ngon-ngu.js?v=1"></script>').join('')
  .split('<script src="js/tai-xe.js?v=3"></script>').join('')
  .replace(/<script src="https:[^"]*"><\/script>/g, '')
  .replace(/<link rel="stylesheet" href="https:[^"]*">/g, '');

const dom = new JSDOM(html, {
  url: 'http://localhost:8099/', runScripts: 'dangerously', pretendToBeVisual: true,
  beforeParse(w) {
    w.fetch = function (u) {
      const duong = String(u);
      const than = duong.indexOf('/api/drivers') >= 0
        ? [{ id: 'DEMO-DRV-018', name: 'Thongdy Keomany', role: 'Lái xe chính', license_type: 'FC' }]
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
w.HTMLDialogElement.prototype.showModal = function () { this.open = true; };
w.HTMLDialogElement.prototype.close = function () {
  if (!this.open) return;
  this.open = false;
  this.dispatchEvent(new w.Event('close'));
};
['ngon-ngu.js', 'tai-xe.js'].forEach(function (ten) {
  const s = w.document.createElement('script');
  s.textContent = fs.readFileSync(path.join(GOC, 'web', 'js', ten), 'utf8');
  w.document.body.appendChild(s);
});

const d = w.document;
const el = (id) => d.getElementById(id);
const ngu = (ms) => new Promise((r) => setTimeout(r, ms));
const doiTieng = (ma) => d.querySelector('#chon-tieng button[data-ngonngu="' + ma + '"]').click();

(async () => {
  await ngu(500);
  assert.deepStrictEqual(loiJS, [], 'trang có lỗi JS: ' + loiJS.join(' | '));

  /* 1. Ba bảng chữ phải ĐỦ KHOÁ như nhau. */
  const ma = fs.readFileSync(path.join(GOC, 'web', 'js', 'ngon-ngu.js'), 'utf8');
  const khoi = {};
  ['vi', 'en', 'lo'].forEach(function (t) {
    const i = ma.indexOf('\n    ' + t + ': {');
    assert.ok(i > 0, 'không thấy bảng chữ ' + t);
    const j = ma.indexOf('\n    },', i);
    khoi[t] = new Set((ma.slice(i, j).match(/^\s{6}(\w+):/gm) || [])
      .map((x) => x.trim().replace(':', '')));
  });
  ['en', 'lo'].forEach(function (t) {
    const thieu = [...khoi.vi].filter((k) => !khoi[t].has(k));
    const thua = [...khoi[t]].filter((k) => !khoi.vi.has(k));
    assert.deepStrictEqual(thieu, [], t + ' thiếu khoá: ' + thieu.join(', '));
    assert.deepStrictEqual(thua, [], t + ' thừa khoá: ' + thua.join(', '));
  });
  assert.ok(khoi.vi.size > 60, 'bảng chữ quá ít khoá, có thể đã đọc hụt: ' + khoi.vi.size);

  /* 2. Đổi ngôn ngữ đổi cả nhãn tĩnh lẫn phần JS sinh ra. */
  const chon = el('chon-taixe');
  chon.value = 'DEMO-DRV-018';
  chon.dispatchEvent(new w.Event('change'));
  await ngu(400);

  const tieuDe = {}, trangThai = {};
  for (const t of ['vi', 'en', 'lo']) {
    doiTieng(t);
    await ngu(60);
    assert.strictEqual(d.documentElement.lang, t, 'thuộc tính lang phải đổi theo');
    tieuDe[t] = d.querySelector('.tieu h2').textContent;            // nhãn TĨNH
    trangThai[t] = d.querySelector('#ds [data-key] .chip').textContent;  // do JS SINH RA
  }
  assert.strictEqual(new Set(Object.values(tieuDe)).size, 3, 'nhãn tĩnh không đổi theo ngôn ngữ');
  assert.strictEqual(new Set(Object.values(trangThai)).size, 3,
    'phần do JS sinh ra không đổi theo ngôn ngữ — đổi tiếng mà thẻ chuyến vẫn nguyên');
  assert.ok(!/^[a-z_]+$/.test(trangThai.en), 'trạng thái in ra mã thô thay vì nhãn: ' + trangThai.en);

  /* 3. Ở tiếng Lào không còn chữ tiếng Việt nào trên màn chi tiết. */
  doiTieng('lo');
  await ngu(60);
  d.querySelector('#ds [data-key]').click();
  await ngu(300);

  const boTenRieng = (s) => String(s)
    .replace(/DO-[0-9A-Z-]+|TRIP-[0-9A-Z-]+|FO-[0-9A-Z-]+|DEMO-[0-9A-Z.-]+/g, '')
    .replace(/Vinamilk|Thongdy Keomany|Vientiane|Cua Lo/g, '');
  const conViet = (s) => [...new Set((boTenRieng(s).match(/[A-Za-zÀ-ỹ]+/g) || []).filter((t) => VIET.test(t)))];

  const sotManHinh = conViet(el('man-chitiet').textContent);
  assert.deepStrictEqual(sotManHinh, [],
    'màn chi tiết tiếng Lào còn chữ tiếng Việt: ' + sotManHinh.join(', '));

  /* 4. Tên mốc phải dịch theo MÃ, không lấy chữ tiếng Việt máy chủ trả về. */
  el('nut-moc').click();
  await ngu(150);
  const sotHop = conViet(el('xn-tieude').textContent + ' ' + el('xn-noidung').textContent);
  assert.deepStrictEqual(sotHop, [],
    'hộp xác nhận tiếng Lào còn chữ tiếng Việt (thường là tên mốc máy chủ trả về): ' + sotHop.join(', '));
  assert.ok(!el('xn-tieude').textContent.includes('Đến điểm giao'),
    'tên mốc phải dịch lại theo mã, không dùng nguyên chữ máy chủ trả về');
  el('xn-huy').click();
  await ngu(100);

  /* 5. Lựa chọn được nhớ. */
  assert.strictEqual(w.localStorage.getItem('EPL_TAIXE_NGON_NGU'), 'lo',
    'phải nhớ ngôn ngữ đã chọn cho lần mở sau');

  console.log('ba-ngon-ngu: OK — %d khoá × 3 ngôn ngữ, không còn câu lai', khoi.vi.size);
  process.exit(0);
})().catch((e) => { console.error('HỎNG:', e && e.message); process.exit(1); });

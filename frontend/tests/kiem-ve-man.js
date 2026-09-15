/* Dựng thật từng màn trong jsdom với dữ liệu giả, để bắt lỗi lúc CHẠY.
 *
 * Bộ kiểm kia chỉ đọc cú pháp; bộ này đi đúng đường thật của ứng dụng — khung
 * nạp lang.json, rồi PL.moMan() nạp HTML của module và gọi khoiDong() — nên bắt
 * được những lỗi chỉ lộ ra khi vẽ: sai tên phần tử, đọc thuộc tính của null.
 *
 * Chạy: node frontend/tests/kiem-ve-man.js
 */
'use strict';

const fs = require('fs');
const path = require('path');

const GOC = path.join(__dirname, '..');
let JSDOM;
try {
  ({ JSDOM } = require(path.join('D:', 'Demo_Lao', 'EPL_System', 'frontend', 'node_modules', 'jsdom')));
} catch (e) {
  console.log('Bỏ qua: máy này chưa có jsdom (' + e.message + ')');
  process.exit(0);
}

let loi = [];
function kiem(dk, nhan) {
  if (dk) console.log('  OK   ' + nhan);
  else { console.log('  FAIL ' + nhan); loi.push(nhan); }
}

const tuDien = JSON.parse(fs.readFileSync(path.join(GOC, 'lang.json'), 'utf8'));

/* ------------------------------------------------------------ dữ liệu giả */
const DONG = { id: 11, line_no: 1, barcode: '885', product_code: '411', description: 'BISKIO DINO 15g',
  case_qty: 10, piece_qty: 120, packed_case_qty: 4, packed_piece_qty: 48,
  remaining_case_qty: 6, remaining_piece_qty: 72, unit_price: 343000, amount: 686000,
  weight_kg: 6.5, cube_m3: 0.035, uom: 'CT' };
const DON = { id: 'SO-2026-0001', po_number: '6003990191', status: 'packing', ship_to_name: 'PTTLAO DONEKOY',
  ship_to_code: '60039', currency: 'LAK', packing_list_count: 1, lines: [DONG],
  total_amount: 686000, total_case_qty: 10, remaining_case_qty: 6, remaining_piece_qty: 72,
  fully_packed: false, created_at: '2026-09-14T10:00:00' };
const TEM = { id: 'L1', package_no: 1, package_total: 2, qr_token: 'TOKEN1', status: 'ready',
  printed_at: null, reprint_count: 0, scanned_at: null };
const PL_MAU = { id: 'PL-2026-0001-01', so_id: 'SO-2026-0001', po_number: '6003990191', seq: 1,
  delivery_id: null, store_name: 'PTTLAO DONEKOY', route_name: 'Vientiane → Donekoy',
  box_count: 2, total_cases: 4, total_pieces: 48, total_weight_kg: 26, total_cube_m3: 0.14,
  status: 'ready', created_at: '2026-09-14T10:00:00', updated_at: '2026-09-14T10:00:00',
  items: [{ id: 1, so_line_id: 11, so_id: 'SO-2026-0001', line_no: 1, barcode: '885',
    description: 'BISKIO DINO 15g', case_qty: 4, piece_qty: 48, weight_kg: 26, uom: 'CT' }],
  labels: [TEM], events: [{ id: 1, event_type: 'created', occurred_at: '2026-09-14T10:00:00', actor: 'demo', note: '' }] };
const GH = { id: 'GH-2026-0001', code: 'GH-2026-0001', status: 'arrived', plate_head: 'ກທ 1234',
  plate_trailer: 'ກທ 5678', driver_name: 'Somsak', driver_phone: '020', route_name: 'V → D',
  departed_at: '2026-09-14T11:00:00', arrived_at: null, completed_at: null,
  packing_list_count: 1, total_cases: 4, total_weight_kg: 26,
  packing_lists: [Object.assign({}, PL_MAU, { status: 'dispatched', pod_received_by: null, pod_result: null })],
  events: [{ id: 1, event_type: 'created', occurred_at: '2026-09-14T10:00:00', actor: 'demo', note: '' }] };

const TRK = { delivery: GH, orders: ['SO-2026-0001'], packing_lists: ['PL-2026-0001-01'],
  depot: { lat: 17.9757, lng: 102.6331, name: 'Kho Vientiane' },
  destination: { lat: 17.938, lng: 102.625, name: 'PTTLAO DONEKOY' },
  position: { lat: 17.96, lng: 102.628, speed_kmh: 48, heading: 190, progress: 0.4, source: 'simulated', recorded_at: '2026-09-14T11:30:00' },
  stale: false, remaining_km: 2.5, route_km: 4.3 };

function duLieuApi(url) {
  if (url.indexOf('/api/sales-orders?') >= 0) return { items: [DON], total: 1 };
  if (/\/api\/sales-orders\/[^/?]+$/.test(url)) return DON;
  if (url.indexOf('/api/packing-lists/stats') >= 0) return { total: 3, ready: 1, parked: 1, gate_in: 0, loaded: 0, dispatched: 1, delivered: 0, cancelled: 0 };
  if (url.indexOf('/api/deliveries/stats') >= 0) return { total: 1, planned: 0, loading: 0, in_transit: 0, arrived: 1, delivered: 0, cancelled: 0 };
  if (url.indexOf('/api/packing-lists?') >= 0) return { items: [PL_MAU], total: 1 };
  if (/\/api\/packing-lists\/[^/?]+$/.test(url)) return PL_MAU;
  if (url.indexOf('/api/deliveries?') >= 0) return { items: [GH], total: 1 };
  if (/\/api\/deliveries\/[^/?]+$/.test(url)) return GH;
  if (url.indexOf('/api/vehicles') >= 0) return [{ id: 'v1', plate_head: 'ກທ 1234', plate_trailer: 'ກທ 5678', internal_no: '341' }];
  if (url.indexOf('/api/drivers') >= 0) return [{ id: 'd1', full_name: 'Somsak', phone: '020' }];
  if (url.indexOf('/api/routes') >= 0) return [
    { id: 'r1', code: 'RT-VTE-DONEKOY', name: 'Kho Vientiane -> PTTLAO DONEKOY', from_id: 'c3', to_id: 'c1',
      from_name: 'Kho Vientiane', to_name: 'PTTLAO DONEKOY', from_lat: 17.9757, from_lng: 102.6331,
      to_lat: 17.938, to_lng: 102.625, distance_km: 5.2, active: true },
  ];
  if (url.indexOf('/api/customers') >= 0) return [
    { id: 'c1', code: 'PTTLAO-DONEKOY', name: 'PTTLAO DONEKOY', kind: 'customer', address: 'Vientiane', lat: 17.938, lng: 102.625 },
    { id: 'c2', code: 'KPA-TRADE', name: 'KPA Trade', kind: 'vendor', tax_number: '2052891-31' },
    { id: 'c3', code: 'KHO-VTE', name: 'Kho Vientiane', kind: 'depot', lat: 17.9757, lng: 102.6331 },
  ];
  if (/\/api\/tracking\/[^/?]+$/.test(url)) return Object.assign({}, TRK, { trail: [{ lat: 17.97, lng: 102.63 }, { lat: 17.96, lng: 102.628 }] });
  if (url.indexOf('/api/tracking') >= 0) return [TRK];
  return null;
}

/* --------------------------------------------------------------- dựng khung */
function dungKhung() {
  const trang = fs.readFileSync(path.join(GOC, 'index.html'), 'utf8')
    .replace(/<script[^>]*><\/script>/g, '');   // khung.js nạp bằng tay bên dưới
  const dom = new JSDOM(trang, { url: 'http://localhost/', pretendToBeVisual: true, runScripts: 'dangerously' });
  const w = dom.window;
  const nhat = [];

  w.addEventListener('error', function (e) { nhat.push(String(e.message)); });
  w.fetch = function (url) {
    const u = String(url).split('?')[0];
    if (u.indexOf('/static/') === 0) {
      const tep = path.join(GOC, u.replace('/static/', ''));
      let chu = '';
      try { chu = fs.readFileSync(tep, 'utf8'); }
      catch (e) { return Promise.resolve({ ok: false, status: 404, text: () => Promise.resolve('') }); }
      return Promise.resolve({
        ok: true, status: 200,
        text: () => Promise.resolve(chu),
        json: () => Promise.resolve(JSON.parse(chu)),
      });
    }
    const d = duLieuApi(String(url));
    return Promise.resolve({
      ok: true, status: 200,
      text: () => Promise.resolve(JSON.stringify({ message: 'OK', data: d })),
      json: () => Promise.resolve(d),
    });
  };
  w.open = function () { return null; };
  // Leaflet không tải được trong jsdom — dựng bản giả tối thiểu để màn Theo dõi
  // vẫn đi hết đường vẽ. Bản đồ thật do trình duyệt kiểm khi anh bấm.
  const gia = () => ({ addTo() { return this; }, bindTooltip() { return this; }, on() { return this; },
    setView() { return this; }, clearLayers() {}, addLayer() {}, removeLayer() {}, fitBounds() {}, pad() { return this; } });
  w.L = { map: () => gia(), tileLayer: () => gia(), layerGroup: () => gia(), marker: () => gia(),
    polyline: () => gia(), divIcon: () => ({}), latLngBounds: () => gia() };
  w.HTMLCanvasElement.prototype.getContext = function () {
    return { lineWidth: 0, lineCap: '', strokeStyle: '', beginPath() {}, moveTo() {},
      lineTo() {}, stroke() {}, clearRect() {} };
  };

  // Khung phải chạy TRƯỚC: mỗi module tham chiếu PL ngay lúc nạp, đúng như
  // thứ tự thẻ <script> trong index.html.
  w.eval(fs.readFileSync(path.join(GOC, 'js', 'khung.js'), 'utf8'));

  // Nạp sẵn JS của mọi module và cắm thẻ đánh dấu, để khung không đi tải qua
  // mạng (jsdom không tải được) mà vẫn đi đúng nhánh "đã có sẵn".
  for (const ten of ['don-hang', 'packing-list', 'giao-hang', 'quet-tem', 'khach-hang', 'theo-doi', 'tuyen-duong']) {
    w.eval(fs.readFileSync(path.join(GOC, 'modules', ten, ten + '.js'), 'utf8'));
    const s = w.document.createElement('script');
    s.dataset.mod = ten;
    w.document.head.appendChild(s);
    const l = w.document.createElement('link');
    l.dataset.mod = ten;
    w.document.head.appendChild(l);
  }
  // khung.js chờ DOMContentLoaded, mà tài liệu đã dựng xong trước đó.
  w.document.dispatchEvent(new w.Event('DOMContentLoaded'));
  return { w, nhat };
}

function cho(ms) { return new Promise(r => setTimeout(r, ms)); }

/* ------------------------------------------------------------------- chạy */
(async function () {
  const man = [
    ['don-hang', 'dh-danh-sach'],
    ['packing-list', 'pk-danh-sach'],
    ['giao-hang', 'gh-danh-sach'],
    ['quet-tem', 'qt-ket-qua'],
    ['khach-hang', 'kh-danh-sach'],
    ['theo-doi', 'td-danh-sach'],
    ['tuyen-duong', 'td2-danh-sach'],
  ];

  const { w, nhat } = dungKhung();
  await cho(250);
  kiem(typeof w.PL === 'object', 'khung dựng được và PL sẵn sàng');
  kiem(w.document.querySelector('[data-i18n="app_title"]').textContent.length > 0,
    'chữ trên đầu trang đã được dịch');

  for (const [ten, oKiem] of man) {
    console.log('\n[' + ten + ']');
    const truoc = nhat.length;
    try {
      await w.PL.moMan(ten);
    } catch (e) {
      nhat.push(ten + ': ' + e.message);
    }
    await cho(220);
    const o = w.document.getElementById(oKiem);
    kiem(!!o, 'có phần tử ' + oKiem);
    if (o) kiem(o.innerHTML.trim().length > 0, 'vẽ được nội dung vào ' + oKiem);

    // Đổi qua cả bốn chế độ ngôn ngữ — chỗ này hay lộ lỗi lúc vẽ lại.
    for (const ma of ['en', 'lo', 'both', 'vi']) {
      try { w.PL.moMan && w.document.querySelector('.nut-ngon-ngu[data-lang="' + ma + '"]').click(); }
      catch (e) { nhat.push(ten + ' đổi sang ' + ma + ': ' + e.message); }
      await cho(60);
    }
    kiem(nhat.length === truoc, 'không ném lỗi khi vẽ và khi đổi ngôn ngữ' +
      (nhat.length > truoc ? ' — ' + nhat.slice(truoc).join(' | ') : ''));
  }

  console.log('\n' + '='.repeat(60));
  if (loi.length) {
    console.log('CÓ ' + loi.length + ' MỤC HỎNG:');
    loi.forEach(x => console.log('  - ' + x));
    process.exit(1);
  }
  console.log('BẢY MÀN ĐỀU DỰNG ĐƯỢC, VẼ RA NỘI DUNG VÀ ĐỔI ĐƯỢC BỐN NGÔN NGỮ');
  process.exit(0);
})();

/**
 * MỞ TỪNG MÀN VÀ ĐÒI NÓ HIỆN NỘI DUNG.
 *
 * VÌ SAO CẦN BÀI KIỂM NÀY. Một màn mở ra trắng trơn là lỗi nặng nhất của ứng
 * dụng này và cũng là lỗi dễ lọt nhất: mã nạp vẫn chạy, không có ngoại lệ nào,
 * `switchView` vẫn đổi lớp — chỉ có nội dung không dựng. Không bài kiểm nào
 * trong bộ này từng MỞ hết các màn rồi kiểm nội dung; `khung-ba-tang` kiểm 5
 * màn, và nó kiểm điều hướng chứ không kiểm nội dung.
 *
 * Chuyện đã xảy ra thật ở dự án này theo một dạng khác: `index.html` thiếu thẻ
 * script cho `do-board.js`, nên `window.DoBoard.BUCKETS` ném lỗi ngay lúc nạp
 * và 9.500 dòng sau đó không bao giờ chạy — nửa ứng dụng chết mà mọi bài kiểm
 * đọc-văn-bản vẫn xanh.
 *
 * Bài này KIỂM KHUNG, không kiểm dữ liệu: mọi lệnh gọi máy chủ trả về danh
 * sách rỗng. Một màn phải hiện được cấu trúc của nó kể cả khi chưa có dữ liệu —
 * và đó cũng là điều người dùng mới nhìn thấy trong lần mở đầu tiên.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');

let JSDOM;
let VirtualConsole;
try {
  ({ JSDOM, VirtualConsole } = require('jsdom'));
} catch (e) {
  console.log('moi-man-phai-hien-noi-dung: BỎ QUA (chưa cài jsdom)');
  process.exit(0);
}

/** Ô mà người dùng PHẢI thấy khi mở từng màn. */
const NOI_DUNG_CHINH = {
  'os-home': ['#os-dock .os-app', '#os-tiles .os-tile', '#tim-man-hinh'],
  dashboard: ['#view-dashboard .card-panel'],
  'co-hoi': ['#cohoi-root'],
  'crm-sales': ['#qtv2-root'],
  'ops-planning': ['#fiori-do-list', '#ops-planning-folder-tabs'],
  'delivery-shipment': ['#view-delivery-shipment'],
  dispatch: ['#view-dispatch'],
  tracking: ['#view-tracking'],
  'delivery-completion': ['#view-delivery-completion'],
  'parking-list': ['#view-parking-list'],
  'ai-checkpoint': ['#view-ai-checkpoint'],
  'master-data': ['#md-tab-routes', '#view-master-data'],
  'lab-summary': ['#view-lab-summary'],
};

const loi = [];
const vc = new VirtualConsole();
vc.on('jsdomError', e => {
  const chu = String((e && e.message) || e);
  // `window.scrollTo` và `window.print` không có trong jsdom. Đó là thiếu sót
  // của môi trường kiểm, không phải lỗi của ứng dụng — trình duyệt thật có cả
  // hai.
  if (/Not implemented: Window/.test(chu)) return;
  loi.push(chu);
});

const than = html
  .replace(/<script\b[^>]*src="[^"]*"[^>]*><\/script>/g, '')
  .replace(/<link\b[^>]*>/g, '');
const tepJs = [...html.matchAll(/src="\/static\/js\/([a-z0-9\-.]+\.js)/g)].map(m => m[1]);

const dom = new JSDOM(than, {
  url: 'http://127.0.0.1/', runScripts: 'dangerously', virtualConsole: vc,
});
const w = dom.window;
const d = w.document;
w.fetch = (u) => {
  if (String(u).includes('lang.json')) {
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(JSON.parse(
        fs.readFileSync(path.join(ROOT, 'js/lang.json'), 'utf8'))),
    });
  }
  return Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve({ items: [], total: 0, data: { items: [] } }),
    text: () => Promise.resolve('{}'),
  });
};
w.alert = () => {};
w.confirm = () => true;
w.prompt = () => '';
tepJs.forEach(ten => {
  const s = d.createElement('script');
  try {
    s.textContent = fs.readFileSync(path.join(ROOT, 'js', ten), 'utf8');
  } catch (e) {
    return;
  }
  d.body.appendChild(s);
});

function hien(el) {
  if (!el) return false;
  for (let x = el; x && x !== d.body; x = x.parentElement) {
    if (x.hasAttribute && x.hasAttribute('hidden')) return false;
    const st = x.getAttribute && x.getAttribute('style');
    if (st && /display\s*:\s*none/i.test(st)) return false;
    if (x.classList && (x.classList.contains('qt-hide') || x.classList.contains('hide'))) {
      return false;
    }
  }
  return true;
}

setTimeout(() => {
  assert.strictEqual(typeof w.switchView, 'function',
    'không có window.switchView — cả ứng dụng không điều hướng được');

  const manTrong = [];
  const manKhongNut = [];
  Object.entries(NOI_DUNG_CHINH).forEach(([man, cacO]) => {
    w.switchView(man);
    const co = cacO.some(s => hien(d.querySelector(s)));
    if (!co) manTrong.push(man + ' (' + cacO.join(', ') + ')');

    // Và màn phải có ít nhất một nút bấm được. Con số 0 nghĩa là nội dung chưa
    // dựng, hoặc dựng xong nhưng nằm trong một khối đang bị che.
    const sec = d.getElementById('view-' + man);
    const soNut = sec ? [...sec.querySelectorAll('button')].filter(hien).length : 0;
    if (!soNut) manKhongNut.push(man);
  });

  assert.deepStrictEqual(manTrong, [],
    'màn mở ra không hiện nội dung chính: ' + manTrong.join(' · '));
  assert.deepStrictEqual(manKhongNut, [],
    'màn không có nút nào bấm được: ' + manKhongNut.join(' · '));
  assert.deepStrictEqual(loi.slice(0, 3), [],
    'có lỗi JS khi mở các màn: ' + loi.slice(0, 3).join(' | '));

  console.log('moi-man-phai-hien-noi-dung: %d màn đều hiện nội dung và có nút bấm được',
    Object.keys(NOI_DUNG_CHINH).length);
  process.exit(0);
}, 1500);

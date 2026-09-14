/**
 * MÀN "XEM LỆNH GIAO HÀNG" PHẢI CHO BIẾT DO ĐÓ CHỞ HÀNG GÌ.
 *
 * Chủ dự án phát hiện ngày 14/09 trên DO-2026-0052-DO01: mở View DO thì thấy đủ tuyến,
 * khung giờ, Tải trọng 10.500 kg, Số pallet, cả bảng quyết toán chi phí — nhưng KHÔNG có
 * chỗ nào nói trên xe là hàng gì. Nguyên văn: *"nó không xem được cái DO đó chở hàng gì à"*.
 *
 * Dữ liệu vốn có sẵn: dòng hàng hoá nằm ở bảng `quotation_items` của BÁO GIÁ, và
 * `/api/quotations/{id}/detail` trả về trong trường `items`. Chỉ là màn DO không hiện.
 *
 * HAI CÁI BẪY mà bài này khoá lại:
 *
 *   1. `/api/quotations` (DANH SÁCH) KHÔNG trả `items` — chỉ `/detail` mới có. Điều kiện cũ
 *      `if (!baoGiaCuaDO(do_item) && ...)` chỉ tải chi tiết khi báo giá CHƯA nằm trong bộ nhớ
 *      trang. Mà mở màn Lệnh giao hàng là danh sách báo giá đã tải rồi — nên nhánh tải chi
 *      tiết không bao giờ chạy, và khối hàng hoá đứng mãi ở chữ "đang tải".
 *
 *   2. Khi chi tiết về, bản cũ đã nằm trong mảng thì phải GỘP vào chính nó. Bản trước dùng
 *      `if (!ds.some(q => q.id === bg.id)) ds.push(bg)` — thấy trùng mã là bỏ qua, tức vứt
 *      luôn `items` vừa tải được.
 *
 * Và một ràng buộc nghiệp vụ: khối này CHỈ ĐỌC. Hàng hoá là thứ hai bên đã thoả thuận trên
 * báo giá; cho gõ lại ở màn DO là tạo nguồn sự thật thứ hai, đối soát không biết tin bên nào.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const GOC = path.join(__dirname, '..');
const nguon = fs.readFileSync(path.join(GOC, 'js', 'app.js'), 'utf8');
const trang = fs.readFileSync(path.join(GOC, 'index.html'), 'utf8');

/* ------------------------------------------------------------------ 1. Ràng buộc nguồn */
assert.ok(/<div id="do-cargo-items"/.test(trang),
  'màn DO phải có ô chứa khối hàng hoá');
assert.ok(/function veHangHoaTrenDO\(do_item\)/.test(nguon),
  'phải có hàm vẽ khối hàng hoá trên màn DO');

// Bẫy 1: điều kiện tải chi tiết phải xét cả trường hợp "có báo giá nhưng thiếu items".
assert.ok(/!Array\.isArray\(bgDaCo\.items\)/.test(nguon),
  'phải tải chi tiết báo giá khi bản đang có THIẾU dòng hàng hoá — danh sách không trả items');

// Bẫy 2: phải gộp chi tiết vào bản cũ, không được bỏ qua khi trùng mã.
assert.ok(/Object\.assign\(ds\[k\], bg\)/.test(nguon),
  'chi tiết báo giá phải GỘP vào bản đã có, bỏ qua là mất items');

// Ràng buộc nghiệp vụ: khối này không được có ô nhập hay nút thêm dòng.
{
  const i = nguon.indexOf('function veHangHoaTrenDO(');
  const j = nguon.indexOf('window.veHangHoaTrenDO', i);
  assert.ok(i > 0 && j > i, 'không tìm thấy thân hàm veHangHoaTrenDO');
  const than = nguon.slice(i, j);
  assert.ok(!/<input/.test(than) && !/<select/.test(than),
    'khối hàng hoá trên màn DO phải CHỈ ĐỌC — không ô nhập, không ô chọn');
  assert.ok(!/Thêm dòng|Thêm khoản/.test(than),
    'không được có nút thêm dòng hàng hoá ở màn DO: sửa hàng hoá là việc của báo giá');
}

/* ------------------------------------------------------------------ 2. Chạy thật trên jsdom */
let JSDOM;
try {
  ({ JSDOM } = require(path.join(GOC, 'node_modules', 'jsdom')));
} catch (e) {
  console.log('man-do-phai-hien-hang-hoa: OK (phần đối chiếu nguồn) — chưa cài jsdom nên bỏ '
    + 'phần dựng HTML, chạy `npm install` để kiểm đủ');
  process.exit(0);
}

const dom = new JSDOM('<!doctype html><div id="do-cargo-items"></div>',
  { url: 'http://localhost:8001/' });
const w = dom.window;
global.window = w; global.document = w.document;

/** Bóc đúng hàm cần dùng: nạp cả app.js (~19.000 dòng) trong jsdom rất nặng và dễ vỡ. */
function bocHam(ten) {
  const k = nguon.indexOf('function ' + ten + '(');
  assert.ok(k > 0, 'không thấy hàm ' + ten);
  return nguon.slice(k, nguon.indexOf('\n}', k) + 2);
}

const ve = new w.Function('escapeHtml', 'baoGiaCuaDO', `
  ${bocHam('veHangHoaTrenDO')}
  return veHangHoaTrenDO;
`);

const esc = (s) => String(s == null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

/** Hồ sơ thật của DO-2026-0052-DO01 và báo giá QT-2026-061 (Lotte Mart, tuyến Lào). */
const DO_ITEM = {
  id: 'DO-2026-0052-DO01', quotation_id: 'QT-2026-061',
  packaging_spec: 'Nguyên khối, niêm phong tại kho', volume_m3: 23.45, seal_no: 'SEAL-77120',
};
const BAO_GIA = {
  id: 'QT-2026-061', cargo_type: 'Hàng bán lẻ siêu thị',
  items: [{ line_no: 1, name: 'Hàng bán lẻ siêu thị (LAK)', quantity: 1, uom: 'Chuyến', note: null }],
};

const o = w.document.getElementById('do-cargo-items');

/* --- a) Có đủ dữ liệu: phải hiện tên hàng, số lượng, ĐVT và NÓI RÕ nguồn là báo giá nào */
ve(esc, () => BAO_GIA)(DO_ITEM);
assert.ok(o.innerHTML.includes('Hàng bán lẻ siêu thị (LAK)'), 'phải hiện tên hàng hoá');
assert.ok(o.innerHTML.includes('Chuyến'), 'phải hiện đơn vị tính');
assert.ok(o.innerHTML.includes('QT-2026-061'),
  'phải nói rõ hàng hoá lấy từ báo giá nào — người đọc cần biết sửa ở đâu');
assert.ok(/Nguyên khối, niêm phong tại kho/.test(o.innerHTML), 'phải hiện quy cách đóng gói');
assert.ok(o.innerHTML.includes('SEAL-77120'), 'phải hiện số niêm phong');
assert.ok(!/<input|<select/.test(o.innerHTML), 'HTML dựng ra không được có ô nhập');

/* --- b) Chưa tải xong báo giá: nói "đang tải", KHÔNG nói "không có hàng hoá" */
ve(esc, () => null)(DO_ITEM);
assert.ok(/Đang tải/.test(o.innerHTML),
  'chưa có báo giá thì phải nói đang tải, đừng kết luận là không có hàng');
assert.ok(!/không khai dòng hàng hoá/.test(o.innerHTML),
  'chưa tải xong mà báo "không khai" là nói dối người đọc');

/* --- c) Báo giá có thật nhưng rỗng dòng hàng: nói THẲNG, không để ô trống */
ve(esc, () => ({ id: 'QT-2026-061', items: [] }))(DO_ITEM);
assert.ok(/không khai dòng hàng hoá/.test(o.innerHTML),
  'báo giá không khai hàng thì phải nói ra, đừng để ô trống cho người đọc tưởng hệ hỏng');

/* --- d) Lệnh không gắn báo giá gốc (DO cũ trước khi bỏ bước Đơn hàng) */
ve(esc, () => null)({ id: 'DO-CU-KHONG-QT' });
assert.ok(/không gắn báo giá gốc/.test(o.innerHTML),
  'DO không có báo giá gốc thì nói rõ, không im lặng');

/* --- e) Chống chèn mã: tên hàng do người dùng gõ, phải qua escapeHtml */
ve(esc, () => ({ id: 'QT-X', items: [{ name: '<img src=x onerror=alert(1)>', quantity: 1, uom: 'Kiện' }] }))(
  { id: 'DO-X', quotation_id: 'QT-X' });
assert.ok(!/<img/.test(o.innerHTML), 'tên hàng hoá phải được thoát HTML');
assert.ok(/&lt;img/.test(o.innerHTML), 'phải hiện ra dạng chữ, không thành thẻ');

console.log('man-do-phai-hien-hang-hoa: OK — màn DO hiện đúng hàng hoá theo báo giá gốc, '
  + 'chỉ đọc, nói rõ nguồn, và phân biệt "đang tải" với "không khai"');

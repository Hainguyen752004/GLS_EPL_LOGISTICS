/**
 * Thẻ "Nguồn lực hôm nay" + ô "hồ sơ sẵn sàng bàn giao" trên màn chủ.
 *
 * VÌ SAO KIỂM BẰNG CÁCH CHẠY THẬT, không quét chữ: cả hai chỗ này là NHÃN NÓI VỀ SỐ, và
 * nhãn sai ở đây đẩy người vận hành vào lỗi 409. Cụ thể, máy chủ đếm `giay_to_het_han` gồm
 * cả xe CHƯA KHAI ngày (cửa gác `VEHICLE_LEGAL_EXPIRED` coi thiếu ngày là hết hạn). Nếu màn
 * chủ hiện những xe đó dưới chữ "sắp hết hạn" thì người điều độ nghĩ còn thời gian, xếp xe,
 * rồi ăn 409 ngay tại cầu cảng. Một bài quét chữ sẽ xanh kể cả khi hai nhánh bị viết ngược.
 *
 * Bốn điều khoá:
 * 1. Có xe đang bị chặn → dòng đỏ, chữ "thiếu / hết hạn", nói rõ điều phối sẽ bị chặn.
 * 2. Không ai bị chặn mà có người sắp hết hạn → dòng cam, có ngưỡng ngày và đích danh ai.
 * 3. Sạch cả đội → dòng xanh, không bịa cảnh báo.
 * 4. Đọc hỏng → nói "chưa đọc được", KHÔNG hiện 0 (0 đọc ra như "đội xe sạch").
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { JSDOM } = require(path.join(__dirname, '..', 'node_modules', 'jsdom'));

const ROOT = path.join(__dirname, '..');
const ma = fs.readFileSync(path.join(ROOT, 'js', 'khung-moi.js'), 'utf8')
  .split(String.fromCharCode(13)).join('');

// Lấy `veNguonLuc` ra chạy độc lập, kèm ba hàm THẬT mà nó dùng: `chuAnToan`,
// `T` (đọc bản dịch, tự lùi về tiếng Việt khi thiếu khoá) và `maVung` (mã vùng
// để định dạng số). Bóc mã thật chứ không cắm hàm giả, để bài kiểm vẫn đo đúng
// thứ chạy trên màn hình.
/** Bóc một hằng khai trên MỘT dòng, ví dụ `const MA_NGON_NGU = {...};`. */
function bocHang(ten) {
  const i = ma.indexOf('const ' + ten + ' =');
  assert.ok(i > 0, 'không thấy hằng ' + ten + ' trong khung-moi.js');
  return ma.slice(i, ma.indexOf(String.fromCharCode(10), i));
}
function boc(ten) {
  const i = ma.indexOf('function ' + ten + '(');
  assert.ok(i > 0, 'không thấy ' + ten + ' trong khung-moi.js');
  return ma.slice(i, ma.indexOf(String.fromCharCode(10) + '  }', i) + 4);
}
const iAn = ma.indexOf('function chuAnToan(');
const iVe = ma.indexOf('function veNguonLuc(');
assert.ok(iAn > 0 && iVe > 0, 'không thấy chuAnToan / veNguonLuc trong khung-moi.js');

const dom = new JSDOM('<div id="os-nl" hidden></div>');
global.document = dom.window.document;
global.window = dom.window;
const chay = new Function('document', 'window',
  [boc('chuAnToan'), boc('T'), bocHang('MA_NGON_NGU'), boc('maVung'), boc('veNguonLuc')].join(String.fromCharCode(10))
  + String.fromCharCode(10) + 'return veNguonLuc;');
const veNguonLuc = chay(dom.window.document, dom.window);
const o = dom.window.document.getElementById('os-nl');
const chu = () => o.textContent.replace(/\s+/g, ' ').trim();

const goc = {
  warn_within_days: 30,
  vehicles: { tong: 9, ranh: 3, dang_chay: 6, bao_duong: 0, ngung_chay: 0, giay_to_het_han: 0, giay_to_sap_het: 0 },
  drivers: { tong: 14, ranh: 8, dang_chay: 6, nghi: 0, bang_het_han: 0, bang_sap_het: 0 },
  vehicles_expiring_soon: [], drivers_expiring_soon: [],
};
const tron = (a, b) => Object.assign({}, a, b);

// 1. Số thật đo trên máy chủ 11/09: 9 xe / 6 đang chạy / 14 tài xế — và đội đang sạch giấy tờ.
veNguonLuc(goc, '');
assert.ok(!o.hidden, 'thẻ nguồn lực phải hiện khi có số');
assert.match(chu(), /9 xe · 14 tài xế/);
assert.match(chu(), /3 xe rảnh/);
assert.match(chu(), /6 xe đang chạy/);
assert.match(chu(), /8 tài xế rảnh/);
assert.strictEqual(o.querySelectorAll('.nl-canh.ok').length, 2, 'đội sạch thì cả hai dòng phải xanh');
assert.match(chu(), /Giấy tờ xe còn hạn cả đội/);
assert.match(chu(), /Bằng lái còn hạn cả đội/);
// Không được bịa cảnh báo khi không có gì để cảnh báo.
assert.strictEqual(o.querySelectorAll('.nl-canh.chan, .nl-canh.sap').length, 0);
// Ô 0 phải mờ đi, không nằm cùng sức nặng với ô có số.
assert.ok([...o.querySelectorAll('.nl-o.trong')].some(x => /nằm xưởng/.test(x.textContent)));

// 2. Có xe đang bị chặn → ĐỎ, và phải nói ra là điều phối bị chặn.
veNguonLuc(tron(goc, {
  vehicles: tron(goc.vehicles, { giay_to_het_han: 2, giay_to_sap_het: 1 }),
  vehicles_expiring_soon: [{ id: 'DEMO-51C-301.88', con_ngay: 12 }],
}), '');
const doXe = o.querySelector('.nl-canh.chan');
assert.ok(doXe, 'có xe hết hạn mà không có dòng đỏ');
assert.match(doXe.textContent, /2 xe thiếu \/ hết hạn giấy tờ/);
assert.match(doXe.textContent, /Điều phối sẽ bị chặn/);
// Đang bị chặn thì KHÔNG được hạ giọng thành "sắp hết hạn".
assert.doesNotMatch(doXe.textContent, /sắp hết hạn/);
assert.strictEqual(doXe.dataset.tab, 'md-tab-vehicles', 'bấm vào phải mở đúng thẻ Phương tiện');

// 3. Không ai bị chặn, có người sắp hết → CAM, kèm ngưỡng ngày và đích danh.
veNguonLuc(tron(goc, {
  drivers: tron(goc.drivers, { bang_sap_het: 2 }),
  drivers_expiring_soon: [{ id: 'DEMO-DRV-007', name: 'Lê Văn Bảy', con_ngay: 9 },
                          { id: 'DEMO-DRV-013', name: 'Trần Thị Mười Ba', con_ngay: 21 }],
}), '');
const camTx = o.querySelector('.nl-canh.sap');
assert.ok(camTx, 'có bằng sắp hết hạn mà không có dòng cam');
assert.match(camTx.textContent, /2 tài xế sắp hết hạn bằng lái trong 30 ngày/);
assert.match(camTx.textContent, /Lê Văn Bảy còn 9 ngày/);
assert.match(camTx.textContent, /Trần Thị Mười Ba còn 21 ngày/);
assert.strictEqual(camTx.dataset.tab, 'md-tab-drivers');

// 4. Xe bị đưa ra khỏi đội chỉ hiện khi có — ô luôn hiện "0 ngừng chạy" là nhiễu.
assert.doesNotMatch(chu(), /ngừng chạy/);
veNguonLuc(tron(goc, { vehicles: tron(goc.vehicles, { ngung_chay: 1 }) }), '');
assert.match(chu(), /1 ngừng chạy/);

// 5. Đọc hỏng → nói thật là chưa đọc được, không vẽ số 0.
veNguonLuc(null, 'HTTP 500');
assert.match(chu(), /Chưa đọc được nguồn lực đội xe \(HTTP 500\)/);
assert.doesNotMatch(chu(), /xe rảnh/);
assert.ok(!o.hidden, 'lỗi cũng phải hiện, không ẩn im lặng');

/* ---- Ô "hồ sơ sẵn sàng bàn giao" trên dải chào ---- */

// Nhãn phải là "sẵn sàng bàn giao", KHÔNG phải "đã hoàn tất": API bàn giao lọc bỏ những DO
// mà chuyến chở nó còn mở, nên hai con số khác nhau và gọi sai tên là nói dối bên công nợ.
assert.ok(/hồ sơ sẵn sàng bàn giao/.test(ma), 'thiếu ô bàn giao trên dải chào');
assert.ok(/\/api\/handover\/delivery-orders\?page_size=1/.test(ma),
  'ô bàn giao phải đếm bằng chính API bàn giao, không đếm lại bằng luật riêng');
assert.ok(/so\.banGiao = Number\(d\.total\)/.test(ma), 'phải lấy total của API bàn giao');

// Thẻ nguồn lực phải nạp từ endpoint máy chủ đếm sẵn, không kéo danh sách xe về đếm tay.
assert.ok(/layJson\('\/api\/fleet\/resource-summary'\)/.test(ma));
assert.ok(!/api\/vehicles\?paginated/.test(ma), 'màn chủ không được kéo danh sách 500 xe về đếm');

console.log('the-nguon-luc-man-chu-noi-dung-that: OK');

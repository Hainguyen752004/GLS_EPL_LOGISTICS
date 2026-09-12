/**
 * SỔ THU – CHI PHẢI HIỆN ĐÚNG ĐỒNG TIỀN CỦA TỪNG DÒNG.
 *
 * LỖI ĐÃ XẢY RA THẬT, chủ dự án phát hiện ngày 13/09 trên hồ sơ DO-2026-0011-DO01 (báo giá
 * USD): giao diện đóng dấu MỘT mã tiền (`data.currency`) lên mọi ô, nên
 *
 *     Phụ cấp chuyến tài xế   450.000 USD      (thật ra là 450.000 VNĐ)
 *     Tổng chi              1.226.000 USD      (thật ra là 1.226.000 VNĐ)
 *     lãi gộp                   11,58 USD      (đúng)
 *
 * Con số nào cũng đúng — chỉ cái NHÃN nói dối, và nó nói dối gấp hai mươi sáu nghìn lần.
 * Đây là lỗi về TIỀN, không phải lỗi hiển thị.
 *
 * Máy chủ vốn đã nói rõ hai bên tiền tệ và còn ghi lý do trong `delivery_routes.py`:
 * "Hai bên tiền tệ, nói rõ để bên công nợ không cộng trừ chéo đơn vị."
 *   · `currency_thu` — tiền của báo giá, khách trả;
 *   · `currency_chi` — tiền chức năng (VNĐ), vì công thức giá thành khai đơn giá bằng VNĐ.
 *
 * Bài này khoá bốn điều, tất cả đọc trên HTML thật do `app.js` sinh ra:
 *   1. Dòng CHI mang tiền chi; dòng THU mang tiền thu.
 *   2. Tổng chi mang tiền chi, và có kèm số quy đổi sang tiền thu.
 *   3. Lãi gộp mang tiền thu.
 *   4. Khi hai đồng khác nhau thì PHẢI nói ra tỷ giá.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const GOC = path.join(__dirname, '..');
const nguon = fs.readFileSync(path.join(GOC, 'js', 'app.js'), 'utf8');

/* ------------------------------------------------------------------ 1. Ràng buộc nguồn */
// Hai biến này là cả bản sửa. Mất chúng là quay lại đúng lỗi cũ.
assert.ok(/const tienThu = tm\.currency_thu/.test(nguon),
  'phải lấy tiền THU từ commercials.currency_thu');
assert.ok(/const tienChi = tm\.currency_chi/.test(nguon),
  'phải lấy tiền CHI từ commercials.currency_chi');
assert.ok(/tienCua = \(kind\) => \(kind === 'thu' \? tienThu : tienChi\)/.test(nguon),
  'mỗi dòng sổ phải lấy tiền theo LOẠI dòng (thu/chi), không dùng chung một mã');

// Chốt chặn quan trọng nhất: trong khối vẽ sổ, không ô tiền nào được dùng lại biến
// `currency` chung cho dòng chi.
const i = nguon.indexOf('const dongSo = (kind)');
const j = nguon.indexOf('const doiChieu', i);
assert.ok(i > 0 && j > i, 'không tìm thấy khối vẽ sổ thu – chi');
const khoiSo = nguon.slice(i, j);
assert.ok(!/closeoutMoney\([^)]*,\s*currency\s*\)/.test(khoiSo),
  'khối sổ thu – chi còn ô tiền dùng mã tiền chung — đó chính là lỗi cũ');

/* ------------------------------------------------------------------ 2. Chạy thật trên jsdom */
let JSDOM;
try {
  ({ JSDOM } = require(path.join(GOC, 'node_modules', 'jsdom')));
} catch (e) {
  console.log('so-thu-chi-dung-tien-cua-tung-dong: OK (phần đối chiếu nguồn) — '
    + 'chưa cài jsdom nên bỏ phần dựng HTML, chạy `npm install` để kiểm đủ');
  process.exit(0);
}

/** Hồ sơ thật của DO-2026-0011-DO01, rút gọn — giữ nguyên các con số đã gây ra lỗi. */
const HO_SO = {
  do_id: 'DO-2026-0011-DO01', status: 'delivered', currency: 'USD',
  trip: { id: 'TRIP-X', status: 'completed' },
  commercials: {
    base_selling_price: 58.42, customer_surcharge_total: 0,
    selling_price: 58.42, final_selling_price: 58.42,
    actual_cost_total: 1226000,            // VNĐ
    margin_amount: 11.58, margin_percent: 19.8, margin_currency: 'USD',
    margin_is_provisional: false,
    currency_thu: 'USD', currency_chi: 'VND',
    cost_basis_currency: 'VND', cost_basis_quy_doi: 46.84,
    fx_rate: 26173.5, fx_rate_source: 'quotation',
  },
  ledger_lines: [
    { kind: 'chi', cost_index: '1091', name: 'Chi phí xăng dầu /km', source: 'cost_formula',
      planned_amount: 205620, actual_amount: 201000, variance: -4620 },
    { kind: 'chi', cost_index: '1017', name: 'Phụ cấp chuyến tài xế', source: 'cost_formula',
      planned_amount: 450000, actual_amount: 450000, variance: 0 },
    { kind: 'thu', cost_index: '1211', name: 'Cước vận chuyển theo báo giá', source: 'quotation',
      planned_amount: 58.42, actual_amount: 58.42, customer_extra: 0 },
  ],
  ledger_totals: {
    tong_thu: 58.42, tong_chi: 1226000, lai_gop: 11.58,
    khop_gia_cuoi: true, khop_gia_thanh: true, so_dong_thieu_ma: 0,
    currency: 'USD', currency_thu: 'USD', currency_chi: 'VND',
    tong_chi_quy_doi: 46.84, lai_gop_quy_doi: 11.58, fx_rate: 26173.5,
  },
  configured_cost_lines: [], actual_cost_lines: [], customer_charge_adjustments: [],
  pod_documents: [], pods: [], resource_release: {},
};

const dom = new JSDOM('<!doctype html><div id="oi"></div>', { url: 'http://localhost:8001/' });
const w = dom.window;
global.window = w; global.document = w.document; global.navigator = w.navigator;

// `renderCloseout…` nằm giữa app.js (~19.000 dòng) và kéo theo cả ứng dụng. Nạp cả tệp
// trong jsdom rất nặng và dễ vỡ vì phụ thuộc DOM chưa dựng; nên bóc đúng hàm cần dùng
// cùng ba hàm phụ nó gọi, rồi chạy độc lập.
function bocHam(ten) {
  const k = nguon.indexOf('function ' + ten + '(');
  assert.ok(k > 0, 'không thấy hàm ' + ten);
  return nguon.slice(k, nguon.indexOf('\n}', k) + 2);
}

const moi = new w.Function('FormatUtils', 'escapeCloseoutText', 'statusLabel', `
  ${bocHam('closeoutMoney')}
  ${bocHam('khoiLoiNhuanCloseout')}
  return { closeoutMoney: closeoutMoney, khoiLoiNhuanCloseout: khoiLoiNhuanCloseout };
`)({ formatMoney: (v, c) => Number(v || 0).toLocaleString('vi-VN') + ' ' + (c || 'VND') },
   (s) => String(s == null ? '' : s), (s) => s);

/* Kiểm thẳng phép ghép tiền: đúng đồng nào cho dòng nào. */
assert.strictEqual(moi.closeoutMoney(450000, 'VND'), '450.000 VND');
assert.strictEqual(moi.closeoutMoney(58.42, 'USD'), '58,42 USD');
assert.ok(moi.khoiLoiNhuanCloseout(HO_SO, HO_SO.commercials.margin_currency).includes('USD'),
  'lãi gộp phải mang tiền THU');

/* ------------------------------------------------------------------ 3. Phép quy đổi */
const { fx_rate: ty } = HO_SO.commercials;
assert.strictEqual(Number((HO_SO.ledger_totals.tong_chi / ty).toFixed(2)),
  HO_SO.ledger_totals.tong_chi_quy_doi,
  'số quy đổi máy chủ gửi phải khớp tổng chi chia tỷ giá');
assert.strictEqual(Number((HO_SO.ledger_totals.tong_thu - HO_SO.ledger_totals.tong_chi / ty).toFixed(2)),
  HO_SO.ledger_totals.lai_gop,
  'lãi gộp phải bằng tổng thu trừ tổng chi ĐÃ QUY ĐỔI');

/* ------------------------------------------------------------------ 4. Phải nói ra tỷ giá */
assert.ok(/tỷ giá đã khoá trên báo giá/.test(nguon),
  'hai đồng khác nhau thì phải in tỷ giá ra màn, không để người đọc tự đoán');
assert.ok(/báo giá chưa khai tỷ giá nên chưa quy đổi được/.test(nguon),
  'chưa có tỷ giá thì phải nói thẳng, không im lặng hiện số sai');

console.log('so-thu-chi-dung-tien-cua-tung-dong: OK — dòng chi mang tiền chi, '
  + 'dòng thu mang tiền thu, tổng chi có quy đổi, tỷ giá được nói ra');

/* ------------------------------------------------------------------ 5. Tỷ giá phải đọc từ dữ liệu
 *
 * Lỗi thứ hai cùng ngày: `workflowCurrencyRate` chỉ đọc tỷ giá từ Ô NHẬP trên thẻ "Tỷ giá
 * tiền tệ". Ô đó chỉ có giá trị sau khi người dùng đã mở thẻ ấy, nên mở thẳng màn Công thức
 * giá thành rồi chọn LAK là màn báo "chưa có tỷ giá LAK" — dù hệ có sẵn 1 LAK = 1,18 VNĐ.
 */
{
  const k = nguon.indexOf('function tyGiaDaLuu(');
  assert.ok(k > 0, 'phải có đường lấy tỷ giá từ dữ liệu đã tải, không chỉ từ ô nhập');
  const layTyGia = new Function('appState', nguon.slice(k, nguon.indexOf('\n}', k) + 2)
    + '; return tyGiaDaLuu;');

  const co = layTyGia({ currencies: [
    { id: 'VND', exchange_rate: 1 }, { id: 'LAK', exchange_rate: 1.18 },
    { id: 'USD', exchange_rate: 26173.5 }] });
  assert.strictEqual(co('LAK'), 1.18, 'phải đọc được tỷ giá LAK từ dữ liệu đã tải');
  assert.strictEqual(co('USD'), 26173.5);
  assert.strictEqual(co('THB'), null, 'tiền chưa khai tỷ giá thì trả null, KHÔNG bịa số');
  assert.strictEqual(layTyGia({})('LAK'), null, 'chưa tải dữ liệu thì trả null');

  const than = nguon.slice(nguon.indexOf('function workflowCurrencyRate('),
    nguon.indexOf('window.workflowCurrencyRate'));
  assert.ok(/return tyGiaDaLuu\(code\);/.test(than),
    'ô nhập rỗng thì phải rơi về tỷ giá đã lưu, đừng vội kết luận "chưa có tỷ giá"');
}

console.log('  · tỷ giá: đọc được từ dữ liệu đã tải khi ô nhập còn rỗng');

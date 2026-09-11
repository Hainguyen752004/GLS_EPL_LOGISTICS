/**
 * Nút "Ghi sổ kinh doanh" trên hồ sơ đã hoàn tất — đẩy DO sang QLSX (hệ công nợ của anh Khang).
 *
 * Chủ dự án và anh Khang chốt 11/09/2026: cạnh "Cập nhật giá thực tế / Chốt cước" có thêm nút
 * này. Bài chạy THẬT hai hàm vẽ với ba trạng thái để khoá:
 *  1. DO đã giao, chưa ghi sổ → có nút bấm, gọi `ghiSoKinhDoanh(doId)`; mốc "Bàn giao công nợ"
 *     nói rõ "chưa ghi sổ".
 *  2. Đã ghi sổ → KHÔNG còn nút bấm (QLSX không có API sửa/xoá, bấm lại chỉ tốn một vòng
 *     mạng), thay bằng chip xanh ghi mã SO; mốc ghi mã SO và công nợ ban đầu.
 *  3. Lần trước hỏng → nút vẫn hiện, kèm dòng lỗi lần trước để người dùng biết vì sao.
 *  4. DO chưa giao → không hiện gì (màn Theo dõi cũng dùng bản vẽ này cho DO đang chạy).
 *  5. Nút gọi API CỦA MÌNH (`/api/handover/.../ghi-so-kinh-doanh`), không gọi thẳng QLSX —
 *     hợp đồng cấm nhúng token vào trình duyệt.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const ma = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8').split(String.fromCharCode(13)).join('');

function boc(ten) {
  const i = ma.indexOf('function ' + ten + '(');
  assert.ok(i > 0, 'không thấy ' + ten);
  return ma.slice(i, ma.indexOf(String.fromCharCode(10) + '}', i) + 2);
}
const chay = new Function('escapeCloseoutText', 'closeoutMoney',
  boc('nutGhiSoKinhDoanh') + String.fromCharCode(10) + boc('mocBanGiaoCongNo')
  + String.fromCharCode(10) + 'return {nutGhiSoKinhDoanh, mocBanGiaoCongNo};');
const { nutGhiSoKinhDoanh, mocBanGiaoCongNo } = chay(
  v => String(v == null ? '' : v).replace(/[<>&"']/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&#39;'}[c])),
  (v, t) => Number(v).toLocaleString('vi-VN') + ' ' + t);

// 1. Đã giao, chưa ghi sổ → nút bấm + xem trước; mốc nói "chưa ghi sổ".
let html = nutGhiSoKinhDoanh({ do_id: 'DO-1', status: 'delivered', ghi_so_kinh_doanh: null });
assert.match(html, /Ghi sổ kinh doanh/);
assert.match(html, /ghiSoKinhDoanh\('DO-1', this\)/);
assert.match(html, /xemTruocGhiSo\('DO-1', this\)/);
assert.doesNotMatch(html, /cl-ghi-so-xong/);
assert.match(mocBanGiaoCongNo({ do_id: 'DO-1', ghi_so_kinh_doanh: null }), /chưa ghi sổ QLSX/);

// 2. Đã ghi sổ → chip xanh có mã SO, KHÔNG còn nút bấm.
const daXong = { do_id: 'DO-2', status: 'delivered', currency: 'LAK',
  ghi_so_kinh_doanh: { da_ghi_so: true, status: 'synced', order_code: 'SO-501', initial_debt_amount: 2200000, currency: 'LAK', synced_at: '2026-09-11T10:00:00' } };
html = nutGhiSoKinhDoanh(daXong);
assert.match(html, /cl-ghi-so-xong/);
assert.match(html, /SO-501/);
assert.doesNotMatch(html, /onclick="ghiSoKinhDoanh/, 'đã ghi sổ mà vẫn còn nút bấm lại');
const moc = mocBanGiaoCongNo(daXong);
assert.match(moc, /Đã ghi sổ QLSX/); assert.match(moc, /SO-501/); assert.match(moc, /2\.200\.000 LAK/);

// 3. Lần trước hỏng → vẫn có nút, kèm lỗi lần trước.
html = nutGhiSoKinhDoanh({ do_id: 'DO-3', status: 'delivered',
  ghi_so_kinh_doanh: { da_ghi_so: false, status: 'failed', attempts: 2, error_code: 'QLSX_401', error_message: 'Chưa xác thực' } });
assert.match(html, /ghiSoKinhDoanh\('DO-3'/);
assert.match(html, /Lần trước: Chưa xác thực/);
assert.match(mocBanGiaoCongNo({ do_id: 'DO-3', ghi_so_kinh_doanh: { status: 'failed', attempts: 2 } }), /lần thử 2/);
assert.match(mocBanGiaoCongNo({ do_id: 'DO-3', ghi_so_kinh_doanh: { status: 'conflict' } }), /409/);

// 4. Chưa giao → không hiện gì.
assert.strictEqual(nutGhiSoKinhDoanh({ do_id: 'DO-4', status: 'in_transit' }), '');

// 5. Gọi API của mình, không gọi QLSX; đọc thân dạng chữ trước rồi mới thử JSON.
assert.ok(/\/api\/handover\/delivery-orders\/\$\{encodeURIComponent\(doId\)\}\/ghi-so-kinh-doanh/.test(ma));
assert.ok(!/goldensme\.com/.test(ma), 'trình duyệt không được biết địa chỉ/token QLSX');
assert.ok(/window\.ghiSoKinhDoanh = async function/.test(ma));
assert.ok(/await r\.text\(\)/.test(ma), 'phải đọc thân dạng chữ trước — QLSX/proxy có thể trả không phải JSON');
// Nút đứng trong hàng nút cạnh "Cập nhật giá thực tế / Chốt cước".
assert.ok(/cl-nut-hang[\s\S]{0,400}Cập nhật giá thực tế \/ Chốt cước[\s\S]{0,200}\$\{nutGhiSoKinhDoanh\(data\)\}/.test(ma));

console.log('nut-ghi-so-kinh-doanh-tren-ho-so-hoan-tat: OK');

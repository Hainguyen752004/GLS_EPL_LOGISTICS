/**
 * Hồ sơ giao hàng mở thành HỘP THOẠI NỔI, và không còn "d is not defined".
 *
 * Chủ dự án gửi hai ảnh: bấm "Xem hồ sơ" ở màn Hoàn tất giao hàng thì (1) báo
 * lỗi "d is not defined" và (2) nội dung — nếu có — xuất hiện DƯỚI bảng, ở cả
 * hai tab Chờ hoàn tất và Đã hoàn tất, phải cuộn xuống mới thấy.
 *
 * (1) là một dòng tham chiếu `d.so_id` bị đặt lầm vào hàm `renderDeliveryOrderCloseout`
 *     — nơi không có biến `d` — thay vì hàm `khoiThongTinDOHoSo` nơi `d` là bản
 *     ghi lệnh giao hàng. Bài này khoá vị trí đúng.
 * (2) hai khối hồ sơ nay mở qua `moHoSoNoi` (cố định giữa màn, nền tối, Esc đóng).
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8');
const css = fs.readFileSync(path.join(ROOT, 'css', 'styles.css'), 'utf8');

function than(neo, ket) {
  const i = app.indexOf(neo);
  assert.ok(i >= 0, 'không thấy ' + neo);
  const j = ket ? app.indexOf(ket, i) : -1;
  return app.slice(i, j > 0 ? j : i + 8000);
}

// --- 1. Không còn tham chiếu `d` ở nơi không có `d` -------------------------
{
  const ve = than('function renderDeliveryOrderCloseout(data, target)', 'window.openCloseoutActualCostEditor');
  // Trong hàm này, `d` chỉ hợp lệ bên trong `soDong.map(d => ...)`. Mọi `d.so_id`
  // ở tầng hàm là lỗi — đúng cái người dùng gặp.
  assert.ok(!/d\.so_id/.test(ve), 'renderDeliveryOrderCloseout không được đọc d.so_id (d không tồn tại ở đó)');
  const khoi = than('function khoiThongTinDOHoSo(data)', 'function khoiPODHoSo');
  assert.ok(/const d = data\.delivery_order \|\| \{\}/.test(khoi), 'khoiThongTinDOHoSo định nghĩa d');
}

// --- 2. Hai khối hồ sơ mở nổi ------------------------------------------------
{
  assert.ok(/function moHoSoNoi\(section\)/.test(app) && /function dongHoSoNoi\(\)/.test(app));
  const xem = than('window.viewCompletedDelivery = async function', 'window.viewCompletedDelivery = ' === '' ? '' : '\n};');
  assert.ok(/moHoSoNoi\(target\)/.test(xem), 'hồ sơ đã hoàn tất phải mở nổi');
  assert.ok(!/scrollIntoView/.test(xem), 'không cuộn trang xuống nữa — hồ sơ đè lên bảng');
  assert.ok(/onclick="dongHoSoNoi\(\)"/.test(xem), 'nút đóng phải gọi dongHoSoNoi');

  const chon = than('deliveryCompletionState.selected = row;', 'window.closeDeliveryCompletionEditor');
  assert.ok(/moHoSoNoi\(editor\)/.test(chon), 'khối biên tập POD (tab Chờ hoàn tất) cũng phải mở nổi');
  assert.ok(!/editor\.scrollIntoView/.test(chon), 'không cuộn trang xuống nữa');

  const dong = than('window.closeDeliveryCompletionEditor = function', 'function moHoSoNoi');
  assert.ok(/dongHoSoNoi\(\)/.test(dong), 'Quay lại phải đóng hộp thoại nổi');

  const noi = than('function moHoSoNoi(section)', 'window.moHoSoNoi');
  assert.ok(/completion-float-open/.test(noi), 'khoá cuộn trang khi đang mở');
  assert.ok(/'Escape'/.test(noi), 'Esc phải đóng');
}

// --- 3. CSS của hộp thoại nổi -------------------------------------------------
{
  assert.ok(/\.completion-float\s*\{[^}]*position:\s*fixed/.test(css), '.completion-float phải cố định');
  assert.ok(/body\.completion-float-open\s*\{\s*overflow:\s*hidden/.test(css), 'khoá cuộn thân trang');
  assert.ok(/\.completion-float \.completion-editor-footer[^}]*position:\s*sticky/.test(css),
    'chân khối biên tập (nút Hoàn tất) phải dính đáy để không phải cuộn tìm');
}

console.log('ho-so-hoan-tat-mo-noi: OK');

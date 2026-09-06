/**
 * Mã khách hàng đề xuất không được trùng mã đang có.
 *
 * Bản cũ là `CUS-00${eplCustomers.length + 1}` — đếm SỐ LƯỢNG khách rồi cộng
 * một. Có CUS-001, CUS-002, CUS-003; xóa CUS-002 đi thì còn hai khách, và mã
 * đề xuất thành CUS-003 — trùng đúng khách còn lại. Gửi lên máy chủ thì khóa
 * chính trùng, SQLAlchemy ném IntegrityError, và người dùng nhận về 500
 * Internal Server Error cho một việc họ tự sửa được trong ba giây.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const app = fs.readFileSync(path.join(__dirname, '..', 'js', 'app.js'), 'utf8');

// Lấy đúng thân hàm ra chạy thật, không chỉ đọc bằng mắt.
const i = app.indexOf('function maKhachHangKeTiep()');
assert.ok(i > 0, 'phải có hàm maKhachHangKeTiep');
const than = app.slice(i, app.indexOf(String.fromCharCode(10) + '}', i) + 2);

let eplCustomers = [];
const maKhachHangKeTiep = new Function(
  'eplCustomers',
  than + String.fromCharCode(10) + 'return maKhachHangKeTiep();'
);

// Danh sách liền mạch.
assert.strictEqual(maKhachHangKeTiep([{ id: 'CUS-001' }, { id: 'CUS-002' }]), 'CUS-003');

// ĐÂY là ca hỏng của bản cũ: xóa một mã ở giữa.
assert.strictEqual(maKhachHangKeTiep([{ id: 'CUS-001' }, { id: 'CUS-003' }]), 'CUS-004');

// Chưa có khách nào.
assert.strictEqual(maKhachHangKeTiep([]), 'CUS-001');
assert.strictEqual(maKhachHangKeTiep(null), 'CUS-001');

// Bề rộng giữ nguyên theo mã đang dùng, không nhảy từ 3 chữ số lên 4.
assert.strictEqual(maKhachHangKeTiep([{ id: 'CUS-009' }]), 'CUS-010');
assert.strictEqual(maKhachHangKeTiep([{ id: 'CUS-0042' }]), 'CUS-0043');

// Mã do người dùng tự đặt, không theo khuôn, thì bỏ qua chứ đừng vỡ.
assert.strictEqual(
  maKhachHangKeTiep([{ id: 'KH-ABC' }, { id: 'CUS-007' }, { id: null }]),
  'CUS-008'
);

// Và không được sinh mã trùng bất kỳ mã nào đang có.
for (const ds of [
  [{ id: 'CUS-001' }, { id: 'CUS-003' }],
  [{ id: 'CUS-001' }, { id: 'CUS-002' }, { id: 'CUS-003' }],
  [{ id: 'CUS-010' }, { id: 'CUS-002' }],
]) {
  const moi = maKhachHangKeTiep(ds);
  assert.ok(!ds.some(x => x.id === moi), `${moi} trùng mã đang có`);
}

// Bản cũ không được quay lại. Chỉ soi các dòng LỆNH — chú thích ở đầu hàm
// có trích nguyên bản cũ để giải thích, và trích dẫn thì không phải mã chạy.
{
  const XUONG_DONG = String.fromCharCode(10);
  const lenh = app.split(String.fromCharCode(13)).join('')
    .split(XUONG_DONG)
    .filter(d => !d.trim().startsWith('*') && !d.trim().startsWith('//'))
    .join(XUONG_DONG);
  assert.ok(!/CUS-00\$\{/.test(lenh), 'còn cách sinh mã theo số lượng khách');
  assert.ok(/cus-id'\)\.value = maKhachHangKeTiep\(\)/.test(lenh),
    'ô mã khách hàng phải lấy từ hàm sinh mã');
}

console.log('ma-khach-hang: tất cả kiểm tra đã qua');

/**
 * Gọi API thất bại thì phải NÓI RA.
 *
 * Rất nhiều chỗ trong app.js viết `if (res.ok) { ... }` mà KHÔNG có nhánh else,
 * còn `catch` thì chỉ `console.error`. Hệ quả cụ thể: bấm "Xóa" một khách hàng
 * khi máy chủ từ chối (409 vì khách còn đơn tham chiếu) thì **không có gì xảy
 * ra và không một thông báo nào** — hàng vẫn nằm đó, người dùng bấm lại.
 *
 * Với các hàm NẠP danh sách còn tệ hơn: bảng giữ nguyên nội dung cũ, nên người
 * dùng thấy dữ liệu CŨ và tưởng đó là mới.
 *
 * Thêm một chi tiết dễ vấp: phong bì lỗi của máy chủ là
 * `{error: {code, message}, detail}` — KHÔNG có khóa `message` ở cấp cao nhất.
 * Nên `data.message` luôn undefined, và mọi chỗ viết
 * `showToast(data.message || 'Thành công!')` sẽ báo THÀNH CÔNG khi thất bại.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8');

function stripComments(source) {
  // Chuẩn hóa CRLF trước: tệp này dùng xuống dòng kiểu Windows, nên một dòng
  // kết thúc bằng `}` thật ra là `}\r\n`. Mọi phép tìm `\n}\n` để định vị cuối
  // hàm đều trượt, và đoạn cắt ra chạy lố sang hàng chục hàm phía sau.
  return source.replace(/\r\n/g, '\n').split('\n').filter(line => {
    const trimmed = line.trim();
    return !trimmed.startsWith('//') && !trimmed.startsWith('*')
      && !trimmed.startsWith('/*') && !trimmed.startsWith('*/');
  }).join('\n');
}
const code = stripComments(app);

// --- 1. Hai hàm dùng chung phải tồn tại và đọc đúng phong bì lỗi ---------

{
  const i = code.indexOf('async function baoLoiMayChu');
  assert.ok(i > 0, 'phải có hàm báo lỗi dùng chung');
  const fn = code.slice(i, code.indexOf('\n}', i));

  // Phải đọc cả ba lớp của phong bì lỗi, vì `data.message` luôn undefined.
  assert.ok(/data\?\.error\?\.message/.test(fn), 'phải đọc error.message');
  assert.ok(/data\?\.detail/.test(fn), 'phải đọc detail');
  // Thân phản hồi không phải JSON thì mã trạng thái vẫn đủ để nói thất bại.
  assert.ok(/res\.status/.test(fn));
  assert.ok(/401/.test(fn) && /403/.test(fn), 'thiếu quyền phải nói rõ là thiếu quyền');
  // Trả về false để gọi được dạng `if (!res.ok) return baoLoiMayChu(...)`.
  assert.ok(/return false;/.test(fn));
}
assert.ok(/function baoMatKetNoi/.test(code), 'phải có hàm báo mất kết nối');
{
  const i = code.indexOf('function baoMatKetNoi');
  const fn = code.slice(i, code.indexOf('\n}', i));
  // Mất kết nối thì phải nói rõ là CHƯA thực hiện, không chỉ nói "lỗi".
  assert.ok(/CHƯA/.test(fn), 'phải nói rõ thao tác chưa được thực hiện');
}

// --- 2. Mười một chỗ đã sửa: xóa, lưu, và nạp danh sách -----------------

const DA_SUA = [
  ['window.deleteCustomer', 'Xóa khách hàng'],
  ['window.deleteDriverRow', 'Xóa nhân sự'],
  ['window.saveDriverModal', 'Lưu nhân sự'],
  ['window.deleteFioriVehicle', 'Xóa phương tiện'],
  ['window.deleteVehType', 'Xóa loại phương tiện'],
  ['async function submitQuotationForm', 'Tạo/sửa báo giá'],
  ['async function submitDOForm', 'Tạo/sửa lệnh giao hàng'],
  ['async function submitIncidentForm', 'Ghi nhận sự cố'],
  ['window.loadCustomerList', 'Nạp danh sách khách hàng'],
  ['async function loadFioriDrivers', 'Nạp danh sách nhân sự'],
  ['async function loadVehTypes', 'Nạp danh mục loại xe'],
];

DA_SUA.forEach(([moc, ten]) => {
  const i = code.indexOf(moc);
  assert.ok(i > 0, `phải tìm được ${moc}`);
  // Lấy tới dấu đóng hàm ở cột 0 — đủ cho mọi hàm trong danh sách này.
  const cuoi = Math.min(
    ...[code.indexOf('\n};', i), code.indexOf('\n}\n', i)].filter(x => x > i)
  );
  const fn = code.slice(i, cuoi);

  assert.ok(/baoLoiMayChu/.test(fn),
    `${ten} (${moc}) chưa báo ra khi máy chủ từ chối`);
  assert.ok(/baoMatKetNoi/.test(fn),
    `${ten} (${moc}) chưa báo ra khi mất kết nối`);
  // Và `catch` không được chỉ ghi console rồi im.
  const catchOnly = /catch \([^)]*\) \{\s*console\.error\([^)]*\);\s*\}/.test(fn);
  assert.ok(!catchOnly, `${ten}: catch chỉ ghi console là nuốt lỗi`);
});

// --- 3. Thất bại thì GIỮ form mở --------------------------------------
//
// Đóng modal khi thất bại là xóa mất những gì người dùng vừa nhập, trong khi
// chưa có gì được ghi lại cả.

[['async function submitQuotationForm', 'modal-quotation'],
  ['async function submitDOForm', 'modal-do'],
  ['async function submitIncidentForm', 'modal-incident'],
  ['window.saveDriverModal', 'closeDriverModal']].forEach(([moc, dong]) => {
  const i = code.indexOf(moc);
  const fn = code.slice(i, Math.min(
    ...[code.indexOf('\n};', i), code.indexOf('\n}\n', i)].filter(x => x > i)
  ));
  const j = fn.indexOf('baoLoiMayChu');
  assert.ok(j > 0, `${moc} phải báo lỗi`);
  // Nhánh lỗi phải `return` trước khi tới chỗ đóng modal.
  const truocKhiDong = fn.slice(j, fn.indexOf(dong, j));
  assert.ok(truocKhiDong.length > 0, `${moc}: phải đóng ${dong} SAU khi báo lỗi`);
  assert.ok(/return |return;/.test(fn.slice(j - 20, j + 40)),
    `${moc}: thất bại thì phải dừng lại, không đi tiếp tới chỗ đóng form`);
});

// --- 4. Không nơi nào lấy `data.message` làm dấu hiệu thành công --------
//
// Phong bì lỗi không có khóa đó, nên `data.message || 'Thành công!'` sẽ báo
// thành công cho mọi lỗi.

{
  // Chỉ là lỗi khi KHÔNG có phép kiểm `res.ok` ngay trước đó. Chỗ nào đã chặn
  // rồi mới lấy `data.message` làm lời chúc mừng thì hoàn toàn đúng.
  const mau = /data\.message \|\| '[^']*(?:thành công|Thành công|Đã )[^']*'/g;
  const bay = [];
  let khop;
  while ((khop = mau.exec(code)) !== null) {
    const truoc = code.slice(Math.max(0, khop.index - 700), khop.index);
    const daChan = /if \(!res\.ok\)|if \(!response\.ok\)|res\.ok \?|throw new Error/.test(truoc);
    if (!daChan) bay.push(khop[0]);
  }
  assert.deepStrictEqual(bay, [],
    `còn chỗ lấy data.message làm dấu hiệu thành công mà không kiểm res.ok: ${bay.join(' | ')}`);
}

console.log('no-silent-failure: tất cả kiểm tra đã qua');

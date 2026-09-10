/**
 * Lệnh giao hàng (DO) sinh từ BÁO GIÁ, không tạo tay và không đi qua Đơn hàng.
 *
 * Chủ dự án chốt, nguyên văn: *"cái DO kế thừa từ cái QT nhé kiểu gen tự động
 * khi mà QT được duyệt hết"* — kèm ảnh form "Tạo lệnh giao hàng" đang có ô
 * "Tham Chiếu Đơn Hàng (SO-...)" và hỏi tại sao DO lại đẩy từ SO qua.
 *
 * Vì sao luật này quan trọng, chứ không chỉ là chuyện gọn màn hình: một DO tạo
 * tay KHÔNG có báo giá nào chống lưng, nên nó không có `unit_price` khoá theo
 * thoả thuận với khách. Bước quyết toán lấy giá từ đâu? Không đâu cả — và hồ sơ
 * đã hoàn tất của nó sẽ thiếu đúng con số mà bên công nợ cần để lập phiếu thu.
 *
 * Bốn điều phải giữ:
 *   1. Form DO từ chối tạo mới, và không gửi `so_id` nữa.
 *   2. Nút đầu trang màn Lập kế hoạch không mở form tạo DO trống.
 *   3. Ô tham chiếu trên form là BÁO GIÁ (QT), chỉ đọc.
 *   4. Ghi nhận khách chấp nhận là bước SINH DO — người bán phải được cảnh báo
 *      trước, vì nó tạo bản ghi thật ở dưới vận hành.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const khung = fs.readFileSync(path.join(ROOT, 'js', 'khung-moi.js'), 'utf8');
const baoGia = fs.readFileSync(path.join(ROOT, 'js', 'bao-gia-v2.js'), 'utf8');

function than(neo, ket) {
  const i = app.indexOf(neo);
  assert.ok(i >= 0, 'không thấy ' + neo);
  const j = ket ? app.indexOf(ket, i) : -1;
  return app.slice(i, j > 0 ? j : i + 4000);
}

// --- 1. Form DO không tạo mới, không gửi so_id -------------------------------
{
  const luu = than('window.saveFioriDO = async function', 'window.loadDeliveryOrders');
  assert.ok(/if\s*\(!currentDO\)\s*\{[\s\S]*?return;/.test(luu),
    'nhánh tạo mới của form DO phải dừng lại, không gửi lên máy chủ');
  assert.ok(!/payload\.so_id/.test(luu), 'form DO không được gửi so_id nữa');
  assert.ok(/báo giá/i.test(luu), 'phải nói cho người dùng biết DO sinh từ báo giá');
}

// --- 2. Nút mở form không dựng một DO trống ----------------------------------
{
  const mo = than('window.openFioriDOForm = function', 'function moKhungFormDO');
  assert.ok(/switchView/.test(mo), 'nút phải dẫn người dùng sang màn báo giá');
  assert.ok(!/el\.style\.display\s*=\s*'flex'/.test(mo),
    'nút không được mở hộp thoại tạo DO trống');
  // Khung form vẫn còn, nhưng chỉ để XEM một DO đã có.
  assert.ok(/function moKhungFormDO\(\)/.test(app), 'phải còn khung form để xem DO đã có');
  const xem = than('window.editFioriDO = function');
  assert.ok(/moKhungFormDO\(\)/.test(xem), 'đường XEM DO phải dùng khung form');
  assert.ok(!/openFioriDOForm\(\)/.test(xem), 'đường XEM DO không được gọi lại nút');
  assert.ok(/'ops-planning':\s*\[\['Lệnh giao hàng sinh từ báo giá/.test(khung),
    'nhãn nút đầu trang phải nói DO sinh từ báo giá');
}

// --- 3. Ô tham chiếu là BÁO GIÁ, chỉ đọc -------------------------------------
{
  const i = html.indexOf('id="do-so-ref"');
  assert.ok(i >= 0, 'không thấy ô tham chiếu trên form DO');
  const o = html.slice(i - 400, i + 200);
  assert.ok(/Báo giá gốc \(QT\)/.test(o), 'nhãn ô phải là "Báo giá gốc (QT)"');
  assert.ok(/placeholder="QT-\.\.\."/.test(o), 'gợi ý trong ô phải là mã báo giá');
  assert.ok(/id="do-so-ref"[^>]*readonly/.test(html.slice(i - 200, i + 300)),
    'ô tham chiếu phải chỉ đọc — không ai gõ tay gốc của một DO');
  const xem = than('window.editFioriDO = function');
  assert.ok(/do_item\.quotation_id/.test(xem) && !/so_id/.test(xem),
    'ô tham chiếu phải hiện quotation_id — so_id đã trục xuất khỏi hệ thống');
}

// --- 4. Chấp nhận báo giá = sinh DO, phải cảnh báo trước ---------------------
{
  const i = baoGia.indexOf('async function ghiNhanChapNhan');
  assert.ok(i >= 0, 'không thấy đường ghi nhận khách chấp nhận');
  const t = baoGia.slice(i, i + 900);
  assert.ok(/window\.confirm/.test(t), 'phải hỏi lại trước khi sinh DO thật');
  assert.ok(/lệnh giao hàng/i.test(t), 'câu hỏi phải nói rõ là sẽ sinh lệnh giao hàng');
  assert.ok(/soLuongHang\(\)/.test(t), 'phải nói sinh bao nhiêu DO');
  // Và mục DO trên phiếu báo giá không còn tự nhận là chỗ "tách tay".
  assert.ok(/6\. Lệnh giao hàng \(DO\) sinh từ báo giá/.test(baoGia),
    'tiêu đề mục phải nói DO sinh từ báo giá');
}

console.log('do-sinh-tu-bao-gia: OK');

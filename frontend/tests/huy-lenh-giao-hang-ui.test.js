/**
 * Giao diện phải có đường hủy lệnh giao hàng.
 *
 * Backend hỗ trợ `pending -> cancelled` từ lâu, kèm chốt an toàn 409
 * `ACTIVE_TRIP_EXISTS`. Nhưng giao diện không có một nút nào gọi nó: chữ
 * `cancelled` chỉ xuất hiện trong các bộ lọc, tức màn hình NHẬN RA đơn đã hủy
 * nhưng không HỦY được đơn nào.
 *
 * Hệ quả thực tế: khách hủy đơn thì người điều hành chỉ còn hai lựa chọn, và
 * cả hai đều sai — để đơn nằm ở "Chờ vận chuyển" mãi (làm sai mọi con số đếm
 * và mọi cảnh báo quá hạn), hoặc XÓA đơn đi (mất luôn lịch sử một việc đã
 * thật sự xảy ra).
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const NL = String.fromCharCode(10);
const app = fs.readFileSync(path.join(__dirname, '..', 'js', 'app.js'), 'utf8')
  .split(String.fromCharCode(13)).join('');

// --- 1. Nút chỉ hiện ở đúng trạng thái backend cho phép ----------------
//
// Hiện nó ở trạng thái khác thì bấm vào chỉ nhận 409 — tức lại là một nút
// nói dối. Chạy THẬT hàm quyết định, không dò chữ.

{
  const i = app.indexOf('function huyDuocDon(do_item)');
  assert.ok(i > 0, 'phải có hàm quyết định trạng thái nào hủy được');
  const than = app.slice(i, app.indexOf(NL + '}', i) + 2);
  const huyDuocDon = new Function(than + NL + 'return huyDuocDon;')();

  assert.strictEqual(huyDuocDon({ canonical_status: 'pending' }), true);
  ['in_transit', 'delivered', 'cancelled', 'completed', ''].forEach(tt => {
    assert.strictEqual(huyDuocDon({ canonical_status: tt }), false,
      `${tt || '(rỗng)'} không được hiện nút hủy`);
  });
  assert.strictEqual(huyDuocDon(null), false, 'không có đơn thì không có nút');
  // Chữ hoa/thường không được làm lệch kết quả.
  assert.strictEqual(huyDuocDon({ canonical_status: 'PENDING' }), true);
}

{
  // Hàm dựng nút phải trả về chuỗi RỖNG khi không hủy được, chứ không phải
  // một nút bị vô hiệu hóa — nút xám vẫn mời người ta bấm.
  const i = app.indexOf('function nutHuyDon(do_item, doId)');
  assert.ok(i > 0);
  const than = app.slice(i, app.indexOf(NL + '}', i) + 2);
  assert.ok(/if \(!huyDuocDon\(do_item\)\) return '';/.test(than), than.slice(0, 200));
  assert.ok(/huyLenhGiaoHang\('\$\{doId\}'\)/.test(than), 'nút phải gọi hàm hủy');
}

// --- 2. Nút phải được gắn vào dòng của bảng ---------------------------

assert.ok(/\$\{nutHuyDon\(do_item, doId\)\}/.test(app),
  'nút hủy phải được gắn vào dòng danh sách lệnh giao hàng');

// --- 3. Hàm hủy phải gửi đúng thứ, và báo lỗi thật -------------------

{
  const i = app.indexOf('window.huyLenhGiaoHang = async function');
  assert.ok(i > 0, 'phải có hàm hủy');
  const than = app.slice(i, app.indexOf(NL + '};', i));

  assert.ok(/\/api\/delivery-orders\/\$\{encodeURIComponent\(id\)\}\/status/.test(than),
    'phải gọi đúng đường đổi trạng thái, và thoát ký tự trong mã đơn');
  assert.ok(/method: 'PUT'/.test(than));
  assert.ok(/status: 'cancelled'/.test(than), "phải gửi đúng trạng thái 'cancelled'");

  // Hỏi lại trước khi hủy — đây là thao tác khó hoàn lại.
  assert.ok(/confirm\(/.test(than), 'phải hỏi lại trước khi hủy');

  // Thất bại phải nói ra, và nói LỜI CỦA MÁY CHỦ. 409 ACTIVE_TRIP_EXISTS là
  // câu trả lời có ích: còn chuyến đang chạy. Một câu "Lỗi khi hủy" chung
  // chung thì người dùng không biết phải làm gì.
  assert.ok(/if \(!res\.ok\) return baoLoiMayChu\(res, viec\)/.test(than),
    'máy chủ từ chối thì phải nói rõ lý do');
  assert.ok(/baoMatKetNoi\(viec, e\)/.test(than),
    'mất mạng thì phải nói CHƯA hủy, không được im');

  // Và phải nạp lại danh sách, không thì dòng vừa hủy vẫn nằm đó.
  assert.ok(/loadDeliveryOrders\(\)/.test(than));
}

// --- 4. Xóa DO cũng phải nói rõ lý do --------------------------------
//
// Nhánh lỗi cũ chỉ nói "Lỗi khi xóa DO" — mà lý do thường là thứ người dùng
// cần biết và tự xử lý được: đơn còn chuyến vận tải tham chiếu tới nó.

{
  const i = app.indexOf('window.deleteFioriDO = async function');
  assert.ok(i > 0);
  const than = app.slice(i, app.indexOf(NL + '};', i));
  assert.ok(!/showToast\('Lỗi khi xóa DO/.test(than), 'còn câu báo lỗi chung chung');
  assert.ok(/baoLoiMayChu\(res, viec\)/.test(than));
  assert.ok(/baoMatKetNoi\(viec, e\)/.test(than));
}

// --- 5. Xóa tuyến đường: giao diện phải gọi được -------------------
//
// `DELETE /api/routes/{id}` có ở backend nhưng chuỗi `api/routes/` không
// xuất hiện một lần nào trong các tệp JS. Nhập sai một tuyến thì nó nằm đó
// mãi trong danh mục, và người lập báo giá vẫn chọn được nó.

{
  const i = app.indexOf('window.xoaTuyenDuong = async function');
  assert.ok(i > 0, 'phải có hàm xóa tuyến đường');
  const than = app.slice(i, app.indexOf(NL + '};', i));
  assert.ok(/\/api\/routes\/\$\{encodeURIComponent\(id\)\}/.test(than),
    'phải gọi đúng đường, và thoát ký tự trong mã tuyến');
  assert.ok(/method: 'DELETE'/.test(than));
  assert.ok(/confirm\(/.test(than), 'phải hỏi lại trước khi xóa');
  // Backend trả 409 LOCKED_RECORD kèm câu nói rõ vướng ở đâu — câu đó phải
  // đến được người dùng, không bị thay bằng "Lỗi khi xóa".
  assert.ok(/baoLoiMayChu\(res, viec\)/.test(than));
  assert.ok(/baoMatKetNoi\(viec, e\)/.test(than));
  // Và nút phải được gắn vào thẻ tuyến đường.
  assert.ok(/onclick="xoaTuyenDuong\('\$\{routeId\}'\)"/.test(app),
    'nút xóa phải nằm trên thẻ tuyến đường');
}

console.log('huy-lenh-giao-hang-ui: tất cả kiểm tra đã qua');

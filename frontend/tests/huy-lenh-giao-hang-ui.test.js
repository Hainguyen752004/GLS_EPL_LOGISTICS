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

// --- 2. Nút phải nằm ngay trên dòng của bảng --------------------------
//
// Bản 2 dựng nút qua một hàm `nutHuyDon(do_item, doId)`. Bản 3 vẽ nút ngay
// trong dòng cùng nút xem chi tiết, nên hàm đó đã bỏ — nhưng LUẬT thì không
// đổi: không hủy được thì KHÔNG có nút, chứ không phải nút xám. Nút xám vẫn
// mời người ta bấm rồi nhận một câu từ chối.

{
  const i = app.indexOf('list.slice(0, GIOI_HAN_DONG_DO).forEach(do_item => {');
  assert.ok(i > 0, 'không thấy vòng vẽ dòng DO');
  const dong = app.slice(i, app.indexOf(NL + '  });', i));

  assert.ok(/const huyDuoc = huyDuocDon\(do_item\);/.test(dong),
    'mỗi dòng phải tự tra điều kiện hủy');
  // Điều kiện HIỆN nút là `huyDuoc`, không phải `lapDuoc`. Hai câu hỏi này
  // hiện trùng nhau, nhưng "hủy được không" và "lập Trip được không" là hai
  // luật khác nhau ở backend — buộc nút hủy vào luật lập Trip là để mai sau
  // nới một bên thì bên kia lặng lẽ nới theo.
  // Một phép dò duy nhất, đòi cả ba thứ cùng lúc: điều kiện là `huyDuoc`,
  // thân nhánh gọi `huyLenhGiaoHang`, và nhánh còn lại là chuỗi RỖNG.
  const m = dong.match(/\$\{huyDuoc \? `([\s\S]*?)` : ('.*?')\}/);
  assert.ok(m, 'nút hủy phải hiện theo điều kiện hủy, dạng huyDuoc ? ... : ...');
  assert.ok(m[1].includes("huyLenhGiaoHang('${doId}')"), 'nút phải gọi hàm hủy');
  assert.strictEqual(m[2], "''",
    'không hủy được thì không có nút, chứ không phải nút bị vô hiệu hóa');
  assert.ok(!/nutHuyDon/.test(app), 'hàm dựng nút bản 2 đã bỏ, đừng còn dấu vết');
}

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
  assert.ok(/(confirm|prompt)\(/.test(than), 'phải hỏi lại (kèm lý do) trước khi hủy');

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
  // Và nút phải được gắn vào dòng tuyến đường trong bảng.
  //
  // `event.stopPropagation()` là bắt buộc: cả dòng có onclick mở danh sách
  // chặng, nên thiếu nó thì bấm Xóa vừa hỏi xóa vừa mở/đóng chặng.
  assert.ok(/onclick="event\.stopPropagation\(\); xoaTuyenDuong\('\$\{routeId\}'\)"/
    .test(app), 'nút xóa phải nằm trên dòng tuyến đường và chặn nổi bọt');
}


// --- 7. Nút "Xe đã đến nơi" -------------------------------------------
//
// Hệ thống có hai lớp trạng thái: chuyến hàng đi qua sáu mốc
// (`check_in` … `delivered`), còn DO chỉ có ba. Sự kiện `arrival` từ GPS chỉ
// đổi lớp chuyến hàng, nên trước đây DO vẫn là "Đang vận chuyển" và người
// điều hành không phân biệt được xe còn trên đường hay đã tới bãi chờ bốc dỡ.
//
// Chủ dự án chốt cần CẢ HAI đường báo: GPS tự gửi, và người điều hành bấm tay
// được khi thiết bị mất tín hiệu. Đây là đường bấm tay.

{
  const i = app.indexOf('list.slice(0, GIOI_HAN_DONG_DO).forEach(do_item => {');
  assert.ok(i > 0, 'không thấy vòng vẽ dòng DO');
  const dong = app.slice(i, app.indexOf(NL + '  });', i));

  // Chỉ hiện khi xe đang trên đường. Ở `arrived` thì đã báo rồi, ở `pending`
  // thì chưa chạy, ở `delivered` thì xong — hiện nút ở những trạng thái đó là
  // mời bấm một việc không có nghĩa.
  assert.ok(/const denNoiDuoc = String\(do_item\?\.canonical_status \|\| ''\)\.toLowerCase\(\) === 'in_transit';/
    .test(dong), 'nút đến nơi chỉ hiện khi đang vận chuyển');
  const m = dong.match(/\$\{denNoiDuoc \? `([\s\S]*?)` : ('.*?')\}/);
  assert.ok(m, 'nút phải hiện theo điều kiện, dạng denNoiDuoc ? ... : ...');
  assert.ok(m[1].includes("ghiXeDaDenNoi('${doId}')"), 'nút phải gọi hàm ghi mốc');
  assert.strictEqual(m[2], "''", 'không đủ điều kiện thì không có nút');
}

{
  const i = app.indexOf('window.ghiXeDaDenNoi = async function (id) {');
  assert.ok(i > 0, 'không thấy ghiXeDaDenNoi');
  const than = app.slice(i, app.indexOf(NL + '};', i));

  assert.ok(/status: 'arrived'/.test(than), "phải gửi đúng trạng thái 'arrived'");
  assert.ok(/\/api\/delivery-orders\/\$\{encodeURIComponent\(id\)\}\/status/.test(than),
    'phải gọi đúng đường đổi trạng thái, và thoát ký tự trong mã đơn');
  assert.ok(/method: 'PUT'/.test(than));

  // Nói rõ vì sao trước khi gửi, thay vì để backend trả 409 chung chung.
  assert.ok(/tt !== 'in_transit'/.test(than), 'phải kiểm trạng thái tại chỗ');
  assert.ok(/đã ghi mốc đến nơi rồi/.test(than), 'ghi lần hai phải nói rõ');

  // Và phải nói THẲNG là tiền chưa chốt được — đây đúng là mốc mà người ta
  // hay tưởng đã xong rồi đi chốt tiền.
  assert.ok(/CHƯA chốt được/.test(than) && /POD/.test(than),
    'phải nói rõ ghi mốc này không mở quyết toán');
  assert.ok(/confirm\(/.test(than), 'phải hỏi lại trước khi ghi mốc');

  // Thất bại phải nói LỜI CỦA MÁY CHỦ.
  assert.ok(/baoLoiMayChu\(res, viec\)/.test(than) && /baoMatKetNoi\(viec, e\)/.test(than));
}

console.log('huy-lenh-giao-hang-ui: tất cả kiểm tra đã qua');

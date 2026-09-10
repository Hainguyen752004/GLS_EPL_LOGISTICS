/**
 * Huỷ chuyến, và điều phối chỉ đi qua chuyến.
 *
 * Hai lỗ hổng bản rà soát ngày 10/09 nêu, và chủ dự án yêu cầu sửa hoàn chỉnh:
 *
 * 1. **Màn Lệnh giao hàng cũ còn một nút điều phối lẻ.** Nó có đủ cửa kiểm
 *    nhưng KHÔNG lập chuyến, nên lệnh đi qua đó mắc ở "đang vận chuyển" vĩnh
 *    viễn: không nộp được POD, không lập được hoá đơn, không huỷ được. Nặng hơn
 *    là xe và cả hai tài xế bị giữ mãi vì mọi đường giải phóng đều đi qua
 *    chuyến. Bấm một lần trong buổi demo là mất một xe khỏi đội.
 *
 * 2. **Không có đường nào huỷ một chuyến.** Khách huỷ sau khi đã lập chuyến thì
 *    huỷ lệnh giao hàng bị chặn, mà màn Chuyến không có nút huỷ — đường duy
 *    nhất còn lại là xoá cứng lệnh trong khi chuyến vẫn trỏ vào nó.
 *
 * Bài kiểm này khoá phía giao diện: không nút nào còn gọi đường điều phối lẻ,
 * và hồ sơ chuyến có nút huỷ đi đúng đường máy chủ.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8');

function than(neo, ket) {
  const i = app.indexOf(neo);
  assert.ok(i >= 0, 'không thấy ' + neo);
  const j = ket ? app.indexOf(ket, i) : -1;
  return app.slice(i, j > 0 ? j : i + 5000);
}

// --- 1. Không nút nào gọi đường điều phối lẻ --------------------------------
{
  // Chỉ bắt LỜI GỌI THẬT, không bắt chỗ nhắc tên đường trong ghi chú: lời gọi
  // luôn chèn mã lệnh bằng `${...}` hoặc một mã cụ thể, còn ghi chú viết `{id}`.
  const goiLe = (app.match(/\/api\/delivery-orders\/[^`'"\s]*\/dispatch/g) || [])
    .filter(x => !x.includes('{id}') && !x.includes('{do_id}'));
  assert.strictEqual(goiLe.length, 0,
    'không được còn chỗ nào gọi PUT /api/delivery-orders/{id}/dispatch: ' + goiLe.join(', '));
  // Và đường chuẩn phải còn.
  assert.ok(/\/api\/tms\/trips\/\$\{[^}]*\}\/dispatch/.test(app),
    'phải điều phối qua PUT /api/tms/trips/{id}/dispatch');
}

// --- 2. Nút huỷ chuyến, và nó đi đúng đường ---------------------------------
{
  const huy = than('window.huyChuyenVanTai = async function', 'window.xacNhanXeDaVe');
  assert.ok(/\/api\/tms\/trips\/\$\{encodeURIComponent\(ma\)\}\/cancel/.test(huy),
    'nút huỷ phải gọi POST /api/tms/trips/{id}/cancel');
  assert.ok(/method:\s*'POST'/.test(huy), 'huỷ chuyến là một lệnh POST');

  // LÝ DO LÀ BẮT BUỘC: người đọc sổ sau này cần biết vì sao xe không chạy, và
  // máy chủ cũng chặn nếu thiếu. Chặn ngay ở giao diện thì người dùng không
  // phải bấm rồi nhận lỗi.
  assert.ok(/window\.prompt/.test(huy), 'phải hỏi lý do huỷ');
  assert.ok(/reason:\s*String\(lyDo\)\.trim\(\)/.test(huy), 'phải gửi lý do lên máy chủ');
  assert.ok(/Phải ghi lý do huỷ chuyến/.test(huy), 'thiếu lý do thì chặn tại chỗ');

  // ĐỌC LẠI PHIÊN BẢN NGAY TRƯỚC KHI GỬI, không dùng con số đang hiện trên màn:
  // giữa lúc mở hồ sơ và lúc bấm, người khác có thể đã sửa chuyến.
  assert.ok(/expected_version:\s*Number\(chuyen\.version\)/.test(huy),
    'phải gửi expected_version đọc lại từ máy chủ');
  assert.ok(huy.indexOf('/api/tms/trips/${encodeURIComponent(ma)}`') <
            huy.indexOf('/cancel'),
    'phải đọc chuyến trước rồi mới gửi lệnh huỷ');

  // Sau khi huỷ phải NẠP LẠI, không tự sửa trạng thái trong bộ đệm: chuyến vừa
  // trả xe, tổ lái và lệnh giao hàng về chỗ khác — nhiều bảng đổi cùng lúc.
  assert.ok(/loadAllData/.test(huy) && /renderTripReturnCockpit\(\)/.test(huy),
    'huỷ xong phải đọc lại dữ liệu từ máy chủ');
}

// --- 3. Nút chỉ hiện khi chuyến còn huỷ được -------------------------------
{
  const dieuKien = than('function tripCoTheHuy(chuyen)', 'window.huyChuyenVanTai');
  ['completed', 'settled', 'cancelled'].forEach(tt =>
    assert.ok(dieuKien.includes(`'${tt}'`), `phải loại trạng thái ${tt}`));
  assert.ok(/tripSoPOD/.test(dieuKien),
    'chuyến đã có POD thì không huỷ được — đó là bằng chứng của một lần giao thật');
  const khoiNut = than('const nut = [];', 'detailPane.insertAdjacentHTML');
  assert.ok(/tripCoTheHuy\(raw\)/.test(khoiNut), 'khối việc phải xét tripCoTheHuy');
  assert.ok(/huyChuyenVanTai\(decodeURIComponent\(/.test(khoiNut),
    'mã chuyến đi qua thuộc tính HTML nên phải mã hoá rồi giải mã tại chỗ gọi');
}

console.log('huy-chuyen-va-dieu-phoi-qua-chuyen: OK');

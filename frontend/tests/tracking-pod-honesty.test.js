/**
 * Màn theo dõi hành trình và POD: không khẳng định điều mình không biết.
 *
 * Năm chỗ trên màn này nói chắc chắn về những thứ hệ thống không có dữ liệu:
 *
 *   1. Badge "Lộ Trình Chuẩn" có dấu tích XANH, tức khẳng định xe đúng lộ
 *      trình — nhưng `route-dev-text` không xuất hiện ở bất kỳ đâu trong JS.
 *      Chức năng kiểm lệch tuyến được quảng cáo ở ba nơi và chưa được cài đặt,
 *      nên badge xanh hiện cho mọi chuyến, kể cả chuyến không có một toạ độ.
 *
 *   2. "TỐC ĐỘ HIỆN TẠI 0 km/h" — `speed_kmh` được đặt CỨNG bằng 0 lúc điều
 *      xe, và không có giao diện nào gửi toạ độ lên. Con số đó không đo được,
 *      không phải xe đang dừng.
 *
 *   3. "KHOẢNG CÁCH CÒN LẠI" thật ra là TỔNG chiều dài tuyến ghi lúc điều xe.
 *
 *   4. "DỰ KIẾN ĐẾN" thật ra là `planned_arrival_at` — giờ đến theo KẾ HOẠCH,
 *      không phải dự báo từ GPS.
 *
 *   5. Panel dòng thời gian GPS/POD hiển thị một DO TUỲ Ý, không phải DO đang
 *      xem: nhánh 1 đọc `#tracking-search-do` (id không tồn tại) và nhánh 2 so
 *      `status` với chuỗi tiếng Anh trong khi máy chủ trả tiếng Việt.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');

function stripComments(source) {
  return source.split('\n').filter(line => {
    const trimmed = line.trim();
    return !trimmed.startsWith('//') && !trimmed.startsWith('*')
      && !trimmed.startsWith('/*') && !trimmed.startsWith('*/');
  }).join('\n');
}
const code = stripComments(app);

// --- 1. Badge lệch tuyến không được khẳng định --------------------------

assert.ok(html.includes('id="route-dev-text"'), 'badge lệch tuyến phải còn để sau này cài đặt');
{
  // Không có mã nào tính nó, nên nó KHÔNG được mang dấu tích xanh.
  assert.ok(!/route-dev-text/.test(code),
    'nếu đã cài đặt phép kiểm lệch tuyến thì hãy cập nhật bài kiểm này');

  const i = html.indexOf('id="route-dev-alert"');
  const khoi = html.slice(i - 400, i + 700);
  assert.ok(!/fa-circle-check/.test(khoi),
    'không được dùng dấu tích xanh cho một phép kiểm chưa cài đặt');
  assert.ok(!/Lộ Trình Chuẩn/.test(khoi), 'không được khẳng định "Lộ Trình Chuẩn"');
  assert.ok(/Chưa kiểm lệch tuyến/.test(khoi), 'phải nói rõ là chưa kiểm');
}

// --- 2, 3, 4. Ba con số GPS phải nói đúng nghĩa -------------------------

{
  // Neo vào hàm `trackDO`, không phải vào `const track = await res.json()` —
  // chuỗi đó còn xuất hiện ở bảng điều phối nên `indexOf` bắt sai chỗ.
  const i = code.indexOf('window.trackDO = async function');
  assert.ok(i > 0, 'phải tìm được hàm trackDO');
  const fn = code.slice(i, code.indexOf('\n};', i));

  // Chưa có toạ độ thì KHÔNG hiện tốc độ — dấu gạch, không phải "0 km/h".
  assert.ok(/track\.lat != null && track\.lng != null/.test(fn),
    'phải xét có toạ độ hay không trước khi hiện tốc độ');
  assert.ok(/coToaDo/.test(fn));
  // Phải có nhánh hiện dấu gạch kèm lời giải thích.
  assert.ok(/chưa đo được tốc độ/i.test(fn) || /ch\\u01b0a \\u0111o/.test(fn),
    'thiếu toạ độ phải nói rõ là chưa đo được');

  // Hai con số còn lại phải mang chú thích nói đúng nguồn gốc.
  assert.ok(/Tổng chiều dài tuyến ghi lúc điều xe/.test(fn),
    '"khoảng cách" phải nói rõ là tổng chiều dài tuyến');
  assert.ok(/theo KẾ HOẠCH/.test(fn), 'ETA phải nói rõ là giờ theo kế hoạch');
}
{
  // Nhãn trên trang cũng phải đúng nghĩa, không chỉ chú thích khi trỏ chuột.
  assert.ok(!/lbl_curr_speed">Tốc Độ Hiện Tại/.test(html),
    'nhãn "Tốc Độ Hiện Tại" khẳng định một con số không đo được');
  assert.ok(!/lbl_rem_dist">Khoảng Cách Còn Lại/.test(html),
    'đó là tổng chiều dài tuyến, không phải phần còn lại');
  assert.ok(/lbl_rem_dist">Tổng Chiều Dài Tuyến/.test(html));
  assert.ok(/lbl_eta">Giờ Đến Theo Kế Hoạch/.test(html));

  // Ba tầng nhãn: lang.json phải khớp, không thì nó ghi đè lại chữ trong HTML.
  const lang = JSON.parse(fs.readFileSync(path.join(ROOT, 'js', 'lang.json'), 'utf8').replace(/^\uFEFF/, ''));
  assert.ok(!/Hiện Tại/.test(lang.lbl_curr_speed.vi), 'bản dịch cũng phải đổi theo');
  assert.ok(/Tổng chiều dài tuyến/.test(lang.lbl_rem_dist.vi));
  assert.ok(/kế hoạch/.test(lang.lbl_eta.vi));
  // Tiếng Lào giữ nguyên — không tự soạn tiếng Lào.
  assert.ok(lang.lbl_eta.la, 'không được xoá bản dịch tiếng Lào');
}

// --- 5. Dòng thời gian GPS/POD phải theo DO đang xem -------------------

{
  // Id ô tìm thật trong trang là `tracking-do-search`.
  assert.ok(html.includes('id="tracking-do-search"'));
  assert.ok(!/'tracking-search-do'/.test(code),
    'id `tracking-search-do` không tồn tại trong trang — mọi nhánh đọc nó là no-op');
  // Năm chỗ trong app.js từng dùng id sai đó (chỗ thứ sáu ở Shipment 360 — đã xoá 10/09).
  assert.ok((code.match(/'tracking-do-search'/g) || []).length >= 5,
    'cả năm chỗ phải dùng id thật');
}
{
  // Neo vao ham ve dong thoi gian, khong lay mot cua so ky tu quanh
  // `const selectedDo` — ham phu `dangChay` nam trước no va de bi cat mat.
  const i = code.indexOf('function renderGpsEventTimeline');
  assert.ok(i > 0, 'phai tim duoc ham ve dong thoi gian');
  const fn = code.slice(i, code.indexOf(String.fromCharCode(10) + '}', i));
  // Không được so trạng thái bằng chuỗi tiếng Anh: máy chủ trả tiếng Việt.
  assert.ok(!/\['In Transit', 'Arrived', 'Delivered'\]/.test(fn),
    'so với chuỗi tiếng Anh thì không bao giờ khớp — máy chủ trả tiếng Việt');
  assert.ok(/canonical_status/.test(fn),
    'phải so bằng canonical_status — trường không đổi theo ngôn ngữ');
  // Và phải nhận cả hai dạng.
  assert.ok(/in_transit/.test(fn) && /dang van chuyen/.test(fn));
}

// --- 6. Mở hồ sơ POD không bị chặn bởi phép kiểm của form báo giá ------

{
  const i = code.indexOf('window.submitPOD = async function');
  assert.ok(i > 0);
  const fn = code.slice(i, code.indexOf('\n};', i));
  assert.ok(!/refreshQuotationVehicleRecommendations/.test(fn),
    'mở hồ sơ POD không được đi kiểm form báo giá ở tab khác');
  assert.ok(/openDeliveryCompletionEditor/.test(fn));
}
{
  // Phép kiểm đó thuộc bước LƯU BÁO GIÁ, và phải nằm ở đó.
  const i = code.indexOf('window.saveOracleQT = async function');
  const fn = code.slice(i, code.indexOf('\n};', i));
  assert.ok(/const capacityState = window\.refreshQuotationVehicleRecommendations\(\)/.test(fn),
    'lưu báo giá phải kiểm lại tải trọng');
  assert.ok(/if \(!capacityState\.valid\)/.test(fn));
}

// --- 7. Chứng từ POD đọc từ bảng thật, và lợi nhuận tạm tính phải nói rõ --

{
  const i = code.indexOf('function chungTuPOD');
  assert.ok(i > 0, 'phải có chỗ đọc chứng từ POD thật');
  const fn = code.slice(i, code.indexOf('\n}', i));
  assert.ok(/pod_documents/.test(fn), 'phải đọc bảng chứng từ thật');
  assert.ok(/pod_record_id/.test(fn), 'phải nối theo pod_record_id');
}
{
  const i = code.indexOf('function khoiLoiNhuanCloseout');
  assert.ok(i > 0, 'phải có chỗ vẽ khối lợi nhuận');
  const fn = code.slice(i, code.indexOf('\n}', i));
  // Máy chủ đã gửi cờ này; không dùng nó là hiện "Margin 100%" xanh lá khi
  // chưa có chi phí thực tế — lợi nhuận bằng toàn bộ giá bán.
  assert.ok(/margin_is_provisional/.test(fn), 'phải dùng cờ tạm tính của máy chủ');
  assert.ok(/tạm tính/.test(fn), 'phải nói rõ là tạm tính');
  assert.ok(/Chưa có chi phí thực tế/.test(fn), 'phải giải thích vì sao');
}

console.log('tracking-pod-honesty: tất cả kiểm tra đã qua');

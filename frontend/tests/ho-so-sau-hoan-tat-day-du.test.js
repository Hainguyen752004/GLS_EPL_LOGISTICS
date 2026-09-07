/**
 * Hồ sơ sau hoàn tất phải đầy đủ như màn Hoàn tất giao hàng.
 *
 * Chủ dự án so hai ảnh: màn "Hoàn tất giao hàng" — lúc yêu cầu người nhận xác
 * nhận — có 21 ô thông tin DO và POD từng điểm với thời gian giao thực tế, kết
 * quả giao, người nhận, số điện thoại, tình trạng hàng hóa. Còn "Xem hồ sơ"
 * sau khi hoàn tất thì chỉ có năm ô tóm tắt và một dòng "1 điểm giao · 2 chứng
 * từ" — nói có hai chứng từ mà không cho mở cái nào.
 *
 * Đo được: phong bì closeout trả về 21 khóa, giao diện cũ chỉ dùng 9. Nên phần
 * lớn việc là HIỆN ra thứ đã có, không phải lấy thứ mới.
 *
 * Ba mốc nhãn cũng tách rõ theo yêu cầu của chủ dự án:
 *   in_transit -> "Đang vận chuyển"        xe còn trên đường
 *   arrived    -> "Đã đến nơi — chờ POD"   tới bãi, CHƯA ký nhận
 *   delivered  -> "Đã hoàn tất"            đã ký POD, đã chốt giá, đã hạch toán
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const NL = String.fromCharCode(10);
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8')
  .split(String.fromCharCode(13)).join('');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const uiUtils = fs.readFileSync(path.join(ROOT, 'js', 'workflow-ui-utils.js'), 'utf8');

function than(neo, ket) {
  const i = app.indexOf(neo);
  assert.ok(i > 0, `không thấy ${neo}`);
  return app.slice(i, app.indexOf(NL + (ket || '}'), i) + 2);
}

// --- 1. Ba mốc, ba nhãn — không dùng chung một chữ mơ hồ ---------------

{
  // CHẠY THẬT module, không dò chuỗi trong nguồn: `workflow-ui-utils.js` lưu
  // ASCII-only bằng escape `\uXXXX`, nên một phép dò chữ có dấu sẽ báo thiếu
  // dù nhãn đang đúng. Chạy thật thì không phụ thuộc cách lưu.
  const ui = require(path.join(ROOT, 'js', 'workflow-ui-utils.js'));
  assert.strictEqual(ui.statusLabel('in_transit'), 'Đang vận chuyển');
  assert.strictEqual(ui.statusLabel('arrived'), 'Đã đến nơi — chờ POD',
    'mốc đã đến nơi phải nói rõ là còn chờ POD');
  assert.strictEqual(ui.statusLabel('delivered'), 'Đã hoàn tất',
    '"Đã giao" mơ hồ — mốc này là đã ký POD, đã chốt giá, đã hạch toán');

  // Bí danh cũ phải GIỮ: dữ liệu và thiết bị cũ còn gửi những chuỗi đó, bỏ đi
  // là các bản ghi cũ không đối chiếu được nữa.
  assert.strictEqual(ui.workflowStatusKey('Đã giao hàng'), 'delivered');
  assert.strictEqual(ui.workflowStatusKey('Đã hoàn tất'), 'delivered');
  assert.strictEqual(ui.workflowStatusKey('Đã đến nơi'), 'arrived');
  assert.strictEqual(ui.workflowStatusKey('Đã đến nơi — chờ POD'), 'arrived');
}

// --- 2. Khối "Thông tin DO đầy đủ" ------------------------------------

{
  const t = than('function khoiThongTinDOHoSo(data)');
  // Đọc từ phong bì, KHÔNG từ bộ đệm trình duyệt: hồ sơ là chứng từ nên phải
  // tự đủ. Bộ đệm có thể trống (mở hồ sơ ngay sau khi tải trang) hoặc đã cũ.
  assert.ok(/data\.delivery_order/.test(t),
    'phải đọc từ `delivery_order` trong phong bì');
  assert.ok(!/eplDeliveryOrders/.test(t),
    'hồ sơ không được mượn bộ đệm trình duyệt — nó có thể trống hoặc cũ');

  // Đủ những ô mà màn Hoàn tất giao hàng đang hiện.
  ['Mã DO', 'Trạng thái', 'SO tham chiếu', 'Khách hàng', 'Mã tuyến', 'Trip',
    'Điểm đi', 'Điểm đến', 'Nhận hàng từ', 'Nhận hàng đến', 'Giao hàng từ',
    'Giao hàng đến', 'Xe vận chuyển', 'Tài xế', 'Tải trọng', 'Số pallet',
    'Thể tích', 'Quy cách đóng gói'].forEach(nhan => {
    assert.ok(t.includes(`["${nhan}"`), `khối thông tin DO thiếu ô "${nhan}"`);
  });
  // Và phải ghi rõ là chỉ đọc — hồ sơ đã chốt thì không sửa ở đây.
  assert.ok(/cl-chi-doc/.test(t) && /Chỉ đọc/.test(t), 'phải ghi rõ chỉ đọc');
}

// --- 3. Khối bằng chứng giao hàng, và chứng từ MỞ ĐƯỢC ----------------

{
  const t = than('function khoiPODHoSo(data)');
  ['Địa điểm giao', 'Thời gian giao thực tế', 'Kết quả giao', 'Người nhận',
    'Số điện thoại', 'Tình trạng hàng hóa', 'Ghi chú'].forEach(nhan => {
    assert.ok(t.includes(`["${nhan}"`), `khối POD thiếu ô "${nhan}"`);
  });

  // Từng chứng từ phải mở được. Bản trước chỉ ghi "2 chứng từ" — nói có mà
  // không cho xem thì con số đó vô dụng.
  assert.ok(/pod_documents/.test(t) && /pod_record_id/.test(t),
    'chứng từ phải nối theo pod_record_id');
  assert.ok(/href="\$\{escapeCloseoutText\(t\.download_url/.test(t),
    'từng chứng từ phải là một liên kết tải được');
  assert.ok(/t\.file_name \|\| t\.id/.test(t), 'phải hiện tên tệp');
  assert.ok(/rel="noopener"/.test(t), 'liên kết mở tab mới phải có rel=noopener');

  // Không có tệp mới thì vẫn đọc hai cột cũ — dữ liệu lịch sử còn ở đó.
  assert.ok(/chungTuPOD\(data, pod\)/.test(t),
    'phải dùng lại phép dự phòng đọc photo_url/signature_url cho dữ liệu cũ');
}

// --- 4. Lợi nhuận KHÔNG được hiện bằng một con số trần ----------------
//
// Máy chủ gửi cờ `margin_is_provisional`. Bỏ qua nó là hiện "Lợi nhuận 100%"
// xanh lá khi chưa có chi phí thực tế — lúc đó lợi nhuận đang bằng đúng toàn
// bộ giá bán. `khoiLoiNhuanCloseout` đã xử lý đúng chuyện đó.

{
  const t = than('function renderDeliveryOrderCloseout(data)');
  assert.ok(/khoiLoiNhuanCloseout\(data, currency\)/.test(t),
    'phải dùng lại khối lợi nhuận có xét cờ tạm tính');
  assert.ok(!/\["Lợi nhuận", tm\.margin_amount/.test(t),
    'không được hiện lợi nhuận bằng một con số trần');
  // Và hàm đó vẫn phải còn nguyên phép xét cờ.
  const t2 = than('function khoiLoiNhuanCloseout(data, currency)');
  assert.ok(/margin_is_provisional/.test(t2) && /tạm tính/.test(t2));
}

// --- 5. Kết quả giao phải dịch, không hiện mã máy ---------------------

{
  const t = than('function ketQuaGiaoHoSo(ma)');
  // Bộ nhãn phải khớp với ô chọn ở màn Hoàn tất giao hàng, để hai màn không
  // nói hai kiểu về cùng một kết quả.
  ['delivered_full', 'delivered_partial', 'delivery_failed', 'returned']
    .forEach(ma => assert.ok(t.includes(ma), `thiếu mã "${ma}"`));
  const f = new Function(t + NL + 'return ketQuaGiaoHoSo;')();
  assert.strictEqual(f('delivered_full'), 'Giao đủ hàng');
  assert.strictEqual(f('delivered_partial'), 'Giao thiếu hàng');
  assert.strictEqual(f(''), '');
  // Mã lạ thì hiện nguyên mã, không được trả rỗng — thà thấy mã còn hơn mất
  // thông tin trên một chứng từ.
  assert.strictEqual(f('ma_la'), 'ma_la');
  // Và nhãn phải trùng với ô chọn ở màn Hoàn tất giao hàng — ô đó dựng bằng
  // JS nên tìm trong app.js, không phải trong index.html.
  assert.ok(app.includes('value="delivered_full">Giao đủ hàng'),
    'nhãn phải khớp ô chọn ở màn Hoàn tất giao hàng');
}

// --- 6. Ba bảng tiền, và CSS phải có ---------------------------------

{
  const t = than('function renderDeliveryOrderCloseout(data)');
  assert.ok(/configured_cost_lines/.test(t), 'phải hiện giá thành theo loại xe');
  assert.ok(/actual_cost_lines/.test(t), 'phải hiện chi phí thực tế');
  assert.ok(/customer_charge_adjustments/.test(t), 'phải hiện khoản khách trả thêm');
  assert.ok(/data\.invoice/.test(t), 'phải hiện hóa đơn phải thu');
  assert.ok(/resource_release/.test(t), 'phải hiện việc giải phóng xe/tài xế');

  // Không có CSS thì các khối không có định dạng — hồ sơ thành một khối chữ.
  ['.cl-goc', '.cl-luoi', '.cl-o', '.cl-khoi', '.cl-pod', '.cl-tep-mot']
    .forEach(lop => {
      assert.ok(html.includes(lop + ' '), `thiếu luật CSS cho ${lop}`);
    });
}

console.log('ho-so-sau-hoan-tat-day-du: tất cả kiểm tra đã qua');

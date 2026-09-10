/**
 * Báo giá có HAI bản in, và phiếu gửi khách KHÔNG lộ giá thành.
 *
 * Chủ dự án (10/09): "phần báo giá sẽ có 2 phần: xuất nội bộ là xuất tất cả thông
 * tin hiện tại cho bên mình xem và chốt; còn khi gửi thông tin cho khách chỉ xuất
 * những trường trong ảnh" — ảnh là form của hệ thống cha: trọng lượng, tiền tệ,
 * giá gốc, doanh thu dự kiến, giá gốc sau chiết khấu, doanh thu có chiết khấu,
 * ngày nhập dữ liệu.
 *
 * Trước đó chỉ có một nút "Xem PDF" in cả bảng cấu phần giá thành (xăng dầu, phụ
 * cấp, BOT…) — đưa cho khách là lộ giá thành.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');
const bg = fs.readFileSync(path.join(ROOT, 'js', 'bao-gia-v2.js'), 'utf8').split(String.fromCharCode(13)).join('');
const NL = String.fromCharCode(10);

function than(neo) {
  const i = bg.indexOf(neo);
  assert.ok(i >= 0, 'không thấy ' + neo);
  const j = bg.indexOf(NL + '  }' + NL, i);
  return bg.slice(i, j > 0 ? j : i + 6000);
}

// --- 1. Hai nút, hai hàm ----------------------------------------------------
{
  assert.ok(/\['qtv2-sb-pdf', 'ghost', 'In nội bộ'/.test(bg), 'nút bản nội bộ');
  assert.ok(/\['qtv2-sb-khach', 'ghost', 'Phiếu gửi khách'/.test(bg), 'nút phiếu gửi khách');
  assert.ok(!/'Xem PDF'/.test(bg), 'không còn nút "Xem PDF" mơ hồ — phải nói rõ in cho ai');
  assert.ok(/noi\('qtv2-sb-khach', phieuKhach\)/.test(bg), 'nút phải nối vào hàm');
}

// --- 2. Phiếu gửi khách: đúng các trường của hệ thống cha, không lộ nội bộ ----
{
  const k = than('  function phieuKhach() {');
  ['Trọng lượng', 'Tiền tệ thanh toán', "'Giá gốc'", 'Doanh thu dự kiến từ vận chuyển dựa trên thực tế',
    'Giá gốc sau chiết khấu', '(Có chiết khấu) Doanh thu dự kiến từ vận chuyển', 'Ngày nhập dữ liệu']
    .forEach(t => assert.ok(k.includes(t), 'phiếu khách thiếu trường: ' + t));
  // Không có gì của nội bộ.
  ['total_cost', 'cac_dong', 'notes_internal', 'notes_ops', 'competitor_price', 'target_margin', 'q.bien', 'Giá thành']
    .forEach(t => assert.ok(!k.includes(t), 'phiếu khách KHÔNG được chứa: ' + t));
  // Giá gốc suy ngược từ giá cuối và % chiết khấu; giá cuối vẫn là unit_price.
  assert.ok(/1 \/ \(1 - ck\)/.test(k), 'giá gốc = giá cuối / (1 - chiết khấu)');
}

// --- 3. Bản nội bộ: đủ mọi thứ ------------------------------------------------
{
  const n = than('  function xemPdf() {');
  ['BẢN NỘI BỘ', "dongCua('chi')", "dongCua('thu')", 'Lợi nhuận một chuyến', 'Biên mục tiêu',
    'Giá đối thủ', 'notes_internal', 'notes_ops', 'notes_customer', 'Giá gốc trước chiết khấu']
    .forEach(t => assert.ok(n.includes(t), 'bản nội bộ thiếu: ' + t));
}

// --- 4. Ô chiết khấu đi tới máy chủ và về lại -----------------------------------
{
  assert.ok(/id="qtv2-ck"/.test(bg), 'phải có ô nhập chiết khấu');
  assert.ok(/discount_percent: Number\(q\.discount_percent\) > 0 \? q\.discount_percent : null/.test(bg),
    'payload lưu phải gửi discount_percent (null khi không chiết khấu)');
  assert.ok(/q\.discount_percent = p > 0 && p < 100 \? p \/ 100 : 0/.test(bg), 'lưu dạng 0..1, chặn ≥100%');
  assert.ok(/discount_percent: goc\.discount_percent/.test(bg), 'nhân bản báo giá mang theo chiết khấu');
}

console.log('phieu-gui-khach-va-ban-noi-bo: OK');

/**
 * Giao diện phải có đường đảo bút toán.
 *
 * Backend có đủ ba đường — `/costs/{id}/reverse`, `/ap-invoices/{id}/reverse`,
 * `/settlement-payments/{id}/reverse` — nhưng giao diện chưa bao giờ gọi
 * đường nào. Nó chỉ ĐỌC trạng thái `reversed` để hiển thị.
 *
 * Nghĩa là hạch toán sai một hóa đơn thì trên màn hình không có cách nào sửa:
 * người dùng phải nhờ ai đó gọi API bằng tay, hoặc sửa thẳng cơ sở dữ liệu.
 * Với một chứng từ đã vào sổ, cả hai cách đều tệ.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const NL = String.fromCharCode(10);
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8')
  .split(String.fromCharCode(13)).join('');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const cockpit = require(path.join(ROOT, 'js', 'tms-cockpit-utils.js'));

// --- 1. Ba thao tác đảo phải sinh ra, chạy THẬT hàm dựng --------------

const STATE = {
  freight_actual_costs: [
    { id: 'C1', status: 'approved', version: 2, total_amount: 100, currency_code: 'VND' },
    { id: 'C2', status: 'draft', version: 1, total_amount: 100, currency_code: 'VND' },
  ],
  ap_invoices: [
    { id: 'AP1', status: 'posted', version: 3, total_amount: 100, currency_code: 'VND' },
    { id: 'AP2', status: 'draft', version: 1, total_amount: 100, currency_code: 'VND' },
    // Bản thân là bút toán đảo — không được đảo tiếp.
    { id: 'AP3', status: 'posted', version: 1, reversal_of_ap_id: 'AP1', total_amount: 100 },
  ],
  settlements: [
    { id: 'S1', status: 'partially_paid', version: 1, total_amount: 100, currency_code: 'VND' },
    { id: 'S2', status: 'partially_paid', version: 1, total_amount: 100, currency_code: 'VND' },
  ],
  settlement_payments: [
    { id: 'P1', settlement_id: 'S1', status: 'reversed' },
    { id: 'P2', settlement_id: 'S1', status: 'posted' },
    // S2 chỉ có bút toán đảo -> không còn gì để đảo.
    { id: 'P3', settlement_id: 'S2', status: 'posted', reversal_of_payment_id: 'P0' },
  ],
};

function thaoTacDao(khoa) {
  return (cockpit.buildFinanceRecordDetail(STATE, khoa).actions || [])
    .filter(a => a.command && String(a.command.path).endsWith('/reverse'));
}

{
  // Chi phí thực tế: CHỈ `approved` mới đảo được (theo `_reverse_cost`).
  const co = thaoTacDao('actual_cost:C1');
  assert.strictEqual(co.length, 1, JSON.stringify(co));
  assert.strictEqual(co[0].command.path, '/api/tms/finance/costs/C1/reverse');
  assert.strictEqual(co[0].needs_reason, true, 'phải đánh dấu là cần lý do');
  assert.strictEqual(co[0].severity, 'critical', 'phải là thao tác nguy hiểm');
  // `expected_version` phải đi kèm, không thì backend trả VERSION_CONFLICT.
  assert.strictEqual(co[0].command.body.expected_version, 2);

  assert.deepStrictEqual(thaoTacDao('actual_cost:C2'), [],
    'chi phí còn ở nháp thì chưa có gì để đảo');
}

{
  // AP: chỉ `posted`, và không đảo một bút toán đảo.
  const co = thaoTacDao('ap_invoice:AP1');
  assert.strictEqual(co.length, 1, JSON.stringify(co));
  assert.strictEqual(co[0].command.path, '/api/tms/finance/ap-invoices/AP1/reverse');
  assert.strictEqual(co[0].command.body.expected_version, 3);

  assert.deepStrictEqual(thaoTacDao('ap_invoice:AP2'), [], 'AP nháp thì chưa đảo');
  assert.deepStrictEqual(thaoTacDao('ap_invoice:AP3'), [],
    'AP3 chính là bút toán đảo — đảo tiếp là vô nghĩa');
}

{
  // Thanh toán: đảo TỪNG LẦN, và bỏ qua lần đã đảo.
  const co = thaoTacDao('settlement:S1');
  assert.strictEqual(co.length, 1, JSON.stringify(co));
  assert.strictEqual(co[0].command.path,
    '/api/tms/finance/settlement-payments/P2/reverse',
    'phải chọn lần thanh toán chưa bị đảo, không phải P1');
  assert.ok(/P2/.test(co[0].label), co[0].label);

  assert.deepStrictEqual(thaoTacDao('settlement:S2'), [],
    'S2 chỉ còn bút toán đảo — không còn gì để đảo');
}

// --- 2. Hộp thoại phải hỏi lý do, và tự chặn khi để trống ------------

assert.ok(html.includes('id="finance-action-reason"'), 'phải có ô lý do');
assert.ok(/id="finance-action-reason-wrap"[^>]*display:\s*none/.test(html),
  'khối lý do phải ẩn sẵn, chỉ hiện khi đang đảo bút toán');

{
  const i = app.indexOf('function openFinanceActionForm(action)');
  const than = app.slice(i, app.indexOf(NL + '}' + NL, i));
  assert.ok(/const isReversal = command\.path\.endsWith\('\/reverse'\)/.test(than),
    'phải nhận biết được thao tác đảo');
  assert.ok(/setFinanceActionFieldVisible\('finance-action-reason-wrap', isReversal\)/
    .test(than), 'ô lý do chỉ hiện khi đảo');
}

{
  const i = app.indexOf('async function submitFinanceActionForm()');
  const than = app.slice(i, app.indexOf(NL + '}' + NL, i));
  assert.ok(/body\.reason = document\.getElementById\('finance-action-reason'\)\.value\.trim\(\)/
    .test(than), 'phải gửi lý do lên');
  // Chặn tại chỗ thay vì gửi lên rồi nhận 422 — người dùng đang mở đúng cái
  // form có ô đó.
  assert.ok(/body\.reason\.length < 10/.test(than),
    'lý do trống hoặc quá ngắn phải bị chặn ngay tại form');
  assert.ok(/return \{ ok: false \}/.test(than));
}

// --- 3. Nút đảo phải trông khác nút "bước tiếp theo" ----------------
//
// Đảo bút toán hủy hiệu lực một chứng từ đã vào sổ. Để nó trông giống nút
// tiến trình bình thường ngay bên cạnh là mời người ta bấm nhầm.

{
  const i = app.indexOf("actionsEl.innerHTML = detail.actions.map");
  assert.ok(i > 0);
  const than = app.slice(i, i + 900);
  assert.ok(/critical/.test(than), 'phải phân biệt thao tác nguy hiểm');
  assert.ok(/fa-rotate-left/.test(than), 'nút đảo phải có biểu tượng riêng');
  assert.ok(/#b42318/.test(than), 'nút đảo phải có màu cảnh báo');
  // Nhãn do dữ liệu sinh ra (có mã lần thanh toán) — phải thoát ký tự.
  assert.ok(/escapeHtml\(action\.label\)/.test(than), 'nhãn phải được thoát ký tự');
}

console.log('dao-but-toan-ui: tất cả kiểm tra đã qua');

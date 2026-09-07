/**
 * Hộp thoại xác nhận thao tác tài chính: JS đã có đủ, HTML thì chưa bao giờ
 * được dựng.
 *
 * `openFinanceActionForm`, `submitFinanceActionForm` và toàn bộ phần kiểm tra
 * dữ liệu đã viết đầy đủ từ lâu. Nhưng không có một thẻ nào mang id
 * `finance-action-form-modal` trong index.html, nên `getElementById` luôn trả
 * về null và mã rơi vào nhánh dự phòng:
 *
 *     if (!modal) return executeFinanceCommand(action.command);
 *
 * Tức GỬI THẲNG lệnh lên máy chủ, bỏ qua mọi trường người dùng lẽ ra phải
 * nhập. `create_ap_from_cost` ở backend đòi `vendor_invoice_no`,
 * `invoice_date` và `due_date`, nên kết quả là 422 — một lỗi cho cái form
 * người dùng chưa từng được thấy.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const NL = String.fromCharCode(10);
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8')
  .split(String.fromCharCode(13)).join('');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const idHtml = new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(m => m[1]));

function than(neo) {
  const i = app.indexOf(neo);
  assert.ok(i > 0, `không thấy ${neo}`);
  return app.slice(i, app.indexOf(NL + '}' + NL, i));
}

// --- 1. Mọi id mà ba hàm này chạm tới đều phải có thật -----------------
{
  const ma = than('function openFinanceActionForm(action)')
    + than('async function submitFinanceActionForm()');

  const cham = new Set();
  for (const m of ma.matchAll(/getElementById\('(finance-action-[^']+)'\)/g)) cham.add(m[1]);
  // `setFinanceActionFieldVisible` nhận id qua THAM SỐ, nên phép dò
  // `getElementById('...')` thông thường không thấy tám khối `*-wrap` này.
  for (const m of ma.matchAll(/setFinanceActionFieldVisible\('([^']+)'/g)) cham.add(m[1]);

  assert.ok(cham.size >= 19, `phải chạm ít nhất 19 id, thấy ${cham.size}`);
  const thieu = [...cham].filter(x => !idHtml.has(x)).sort();
  assert.deepStrictEqual(thieu, [],
    'JS chạm tới id không có trong index.html — hộp thoại không mở được'
    + ' và lệnh sẽ bị gửi thẳng, thiếu trường');
}

// --- 2. Kiểu ô nhập phải khớp với giá trị JS ghi vào -------------------
{
  const i = html.indexOf('id="finance-action-form-modal"');
  assert.ok(i > 0, 'chưa dựng hộp thoại');
  const khoi = html.slice(i, html.indexOf('id="modal-do"', i));

  // JS ghi `today.slice(0, 7)` = "2026-09" vào ô kỳ đối soát.
  assert.ok(/id="finance-action-settlement-period"[^>]*type="month"|type="month"[^>]*id="finance-action-settlement-period"/
    .test(khoi), 'kỳ đối soát phải là ô type="month" vì JS ghi vào dạng YYYY-MM');

  ['finance-action-invoice-date', 'finance-action-due-date', 'finance-action-posting-date']
    .forEach(id => {
      const o = khoi.match(new RegExp('<input[^>]*id="' + id + '"[^>]*>'));
      assert.ok(o, `không thấy ô ${id}`);
      assert.ok(/type="date"/.test(o[0]), `${id} phải là ô ngày`);
    });

  const tien = khoi.match(/<input[^>]*id="finance-action-payment-amount"[^>]*>/);
  assert.ok(tien && /type="number"/.test(tien[0]), 'số tiền phải là ô số');

  // JS chỉ chấp nhận hai giá trị này: `value === 'cash' ? 'cash' : 'bank_transfer'`
  const chon = khoi.slice(khoi.indexOf('id="finance-action-payment-method"'));
  const giaTri = [...chon.slice(0, 400).matchAll(/<option value="([^"]+)"/g)].map(m => m[1]);
  assert.deepStrictEqual(giaTri, ['bank_transfer', 'cash'],
    'ô hình thức thanh toán phải đúng hai giá trị JS biết đọc');
}

// --- 3. Phải có nút bấm gọi đúng hàm ------------------------------------
{
  const i = html.indexOf('id="finance-action-form-modal"');
  const khoi = html.slice(i, html.indexOf('id="modal-do"', i));
  assert.ok(/onclick="submitFinanceActionForm\(\)"/.test(khoi), 'phải có nút Xác nhận');
  assert.ok((khoi.match(/onclick="closeFinanceActionForm\(\)"/g) || []).length >= 2,
    'phải đóng được bằng cả nút X lẫn nút Hủy');
}

// --- 4. Các khối phải ẩn sẵn -------------------------------------------
//
// `setFinanceActionFieldVisible` bật khối bằng `style.display = 'grid'` và
// tắt bằng `'none'`. Khối nào không để sẵn `display:none` thì sẽ hiện ở MỌI
// loại thao tác — người ghi nhận thanh toán bị hỏi cả số hóa đơn nhà cung cấp.
{
  const i = html.indexOf('id="finance-action-form-modal"');
  const khoi = html.slice(i, html.indexOf('id="modal-do"', i));
  const wraps = [...than('function openFinanceActionForm(action)')
    .matchAll(/setFinanceActionFieldVisible\('([^']+)'/g)].map(m => m[1]);
  // Chín khối: ba cho tạo AP, một cho kỳ đối soát, bốn cho thanh toán,
  // và một cho LÝ DO ĐẢO BÚT TOÁN — `reason` là bắt buộc ở cả ba đường
  // đảo của backend, thiếu thì 422 REVERSAL_REASON_REQUIRED.
  assert.strictEqual(wraps.length, 9, `phải có 9 khối bật/tắt, thấy ${wraps.length}`);
  wraps.forEach(id => {
    const the = khoi.match(new RegExp('<div[^>]*id="' + id + '"[^>]*>'));
    assert.ok(the, `không thấy khối ${id}`);
    assert.ok(/display:\s*none/.test(the[0]), `${id} phải ẩn sẵn`);
  });
}

console.log('finance-action-form-ui: tất cả kiểm tra đã qua');

/**
 * Bốn nhóm giao diện chết hoặc nói dối, đã dọn.
 *
 *   1. TÁM HÀM VẼ BẢNG CHẾT HẲN. `renderQuotations`, `renderVehicles`, … tìm
 *      `table-quotations`, `table-vehicles`, … — không một id nào trong tám id
 *      đó tồn tại trong index.html, nên cả tám thoát ngay ở dòng
 *      `if (!tbody) return;`. `confirmAICheckin` gọi một trong số đó để "làm
 *      mới màn hình" sau khi mở barrier, nên thông báo "Đã mở barrier" hiện ra
 *      mà không có gì trên màn đổi cả.
 *
 *   2. THẺ "CC FORM" TRÊN DASHBOARD. 30 ô nhập không ai đọc, và 8 nút Lưu ghi
 *      cơ sở dữ liệu THẬT nhưng ghi dữ liệu của MỘT FORM KHÁC ở tab khác.
 *
 *   3. NÚT "CHỌN FILE HỢP ĐỒNG". Chọn xong toast báo "đã đính kèm", mà
 *      `so-contract-file` không xuất hiện trong bất kỳ tệp JS nào — không
 *      upload, không FormData. Tệp bị bỏ ngay tại đó.
 *
 *   4. `innerHTML +=` TRONG VÒNG LẶP. Mỗi vòng tuần tự hóa lại toàn bộ nội
 *      dung hiện có rồi phân tích lại — O(n²). Với 500 xe là dựng lại cả bảng
 *      500 lần.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');

function stripComments(source) {
  return source.replace(/\r\n/g, '\n').split('\n').filter(line => {
    const trimmed = line.trim();
    return !trimmed.startsWith('//') && !trimmed.startsWith('*')
      && !trimmed.startsWith('/*') && !trimmed.startsWith('*/');
  }).join('\n');
}
const code = stripComments(app);

// --- 1. Tám hàm vẽ bảng chết đã được gỡ --------------------------------

['renderQuotations', 'renderSalesOrders', 'renderDashboardDeliveryOrders',
  'renderDashboardRoutes', 'renderDispatches', 'renderIncidents',
  'renderInvoices', 'renderVehicles'].forEach(ten => {
  assert.ok(!new RegExp(`function ${ten}\\s*\\(`).test(code),
    `${ten} là mã chết — tbody của nó không tồn tại trong index.html`);
  assert.ok(!new RegExp(`(?<![\\w.])${ten}\\(\\)`).test(code),
    `còn chỗ gọi ${ten}()`);
});
// Và tám id tbody đó vẫn không tồn tại — nếu ai thêm lại thì phải xem lại
// bài kiểm này, vì lúc đó chúng không còn là mã chết nữa.
['table-quotations', 'table-sales-orders', 'table-delivery-orders',
  'table-dispatches', 'table-routes', 'table-incidents',
  'table-invoices', 'table-vehicles'].forEach(id => {
  assert.ok(!html.includes(`id="${id}"`), `${id} đã xuất hiện — hãy xem lại bài kiểm này`);
});
{
  // `confirmAICheckin` phải gọi hàm vẽ THẬT, không thì thông báo "Đã mở
  // barrier" hiện ra mà màn hình không đổi gì.
  const i = code.indexOf('confirmAICheckin');
  assert.ok(i > 0);
  const fn = code.slice(i, code.indexOf('\n};', i));
  assert.ok(/renderDeliveryOrders\(/.test(fn), 'phải gọi hàm vẽ thật của màn DO');
}

// --- 2. Thẻ CC FORM: không ô nào sửa được, không nút nào ghi form khác ---

{
  // Cắt đúng khối bằng cân bằng thẻ `div`, không lấy một cửa sổ ký tự cố
  // định — cửa sổ như thế lố sang màn hình khác và bắt nhầm những ô nhập
  // thật, đang chạy tốt, của màn đó.
  const dong = html.replace(/\r\n/g, '\n').split('\n');
  const batDau = dong.findIndex(l => l.includes('CC FORM'));
  assert.ok(batDau > 0, 'phải tìm được khối CC FORM');
  // Thẻ `card-panel` bọc ngoài nằm ngay trên dòng tiêu đề.
  let goc = batDau;
  while (goc > 0 && !dong[goc].includes('class="card-panel"')) goc -= 1;
  let can = 0;
  let ketThuc = goc;
  for (let k = goc; k < dong.length; k += 1) {
    can += (dong[k].match(/<div/g) || []).length - (dong[k].match(/<\/div>/g) || []).length;
    if (k > goc && can <= 0) { ketThuc = k; break; }
  }
  assert.ok(ketThuc > goc + 100, 'khối CC FORM phải đủ lớn');
  const than = dong.slice(goc, ketThuc + 1).join('\n');

  // Mọi ô nhập phải `disabled` — đúng như cờ "Mẫu minh họa" trên thẻ đã nói.
  const oMo = than.match(/<(?:input|select|textarea)\b(?![^>]*\bdisabled\b)[^>]*>/g) || [];
  assert.deepStrictEqual(oMo.slice(0, 3), [],
    `còn ${oMo.length} ô nhập sửa được trong khối CC FORM — gõ vào đó không ai đọc`);

  // Không nút nào được ghi cơ sở dữ liệu từ khối này.
  ['saveMasterForm', 'sendMasterForm', 'submitMasterForm',
    'approveMasterForm', 'publishMasterForm'].forEach(ten => {
    assert.ok(!than.includes(ten),
      `${ten} ghi dữ liệu của MỘT FORM KHÁC ở tab khác — không được gọi từ thẻ minh họa`);
  });

  // Thay vào đó là nút đi tới màn thật.
  assert.ok(/onclick="switchView\('[\w-]+'\)"[^>]*>\s*<i[^>]*><\/i> Mở /.test(than),
    'thẻ phải có nút mở màn hình thật');
}

// --- 3. Tab đính kèm nói đúng sự thật ----------------------------------

{
  const i = html.indexOf('id="so-tab-attachments"');
  assert.ok(i > 0);
  const than = html.slice(i, i + 2200);
  // Không được còn ô chọn tệp: nó không dẫn đi đâu cả.
  assert.ok(!/id="so-contract-file"/.test(than),
    'ô chọn tệp không dẫn đi đâu — backend chưa có endpoint đính kèm cho đơn');
  // Và không được còn câu toast khẳng định đã đính kèm.
  assert.ok(!/Đã chọn hợp đồng/.test(html),
    'không được nói "Đã chọn hợp đồng đính kèm" khi tệp bị bỏ');
  // Phải nói rõ là chưa dùng được, và nút phải tắt.
  assert.ok(/chưa dùng được/i.test(than), 'phải nói rõ chức năng chưa dùng được');
  assert.ok(/<button[^>]*\bdisabled\b/.test(than), 'nút phải tắt');
}

// --- 4. Không còn `innerHTML +=` -------------------------------------
//
// `innerHTML +=` đọc ra TOÀN BỘ nội dung hiện có, nối chuỗi, rồi phân tích lại
// từ đầu — O(n²) trong một vòng lặp. Nó còn HỦY rồi tạo lại mọi node con đã
// có, nên xóa mất trình lắng nghe sự kiện và trạng thái ô nhập của những dòng
// đã vẽ trước. `insertAdjacentHTML('beforeend', …)` không có cả hai vấn đề đó.

{
  const con = (code.match(/\.innerHTML \+=/g) || []).length;
  assert.strictEqual(con, 0, `còn ${con} chỗ dùng innerHTML +=`);
  const daDoi = (code.match(/insertAdjacentHTML\('beforeend'/g) || []).length;
  assert.ok(daDoi >= 40, `phải có ít nhất 40 chỗ đã đổi (thấy ${daDoi})`);
}

console.log('dead-ui-cleanup: tất cả kiểm tra đã qua');

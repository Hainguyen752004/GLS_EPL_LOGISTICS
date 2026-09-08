const assert = require('assert');
const fs = require('fs');
const path = require('path');

const frontendRoot = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(frontendRoot, 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(frontendRoot, 'js', 'app.js'), 'utf8');

const deliverySection = html.match(/<section id="view-delivery-shipment"[\s\S]*?<\/section>/)?.[0] || '';
const dispatchSection = html.match(/<section id="view-dispatch"[\s\S]*?<\/section>/)?.[0] || '';

assert.ok(deliverySection, 'Không tìm thấy màn Giao hàng & vận chuyển.');
assert.ok(dispatchSection, 'Không tìm thấy màn Điều phối & thực thi.');

assert.match(
  deliverySection,
  /openTripReturnAction\(['"]create-trip['"]\)/,
  'Màn Giao hàng phải có nút Tạo Trip.'
);
// ĐƯỜNG SANG ĐIỀU PHỐI chỉ có MỘT, và nó nằm trong hồ sơ chuyến do `app.js`
// vẽ ("Sửa ở Điều phối"), không nằm ở đầu trang.
//
// Vì sao đổi: đầu trang trước đây có thêm một nút "Qua điều phối" nữa. Hai nút
// cùng nghĩa mà khác việc — nút ở đầu trang chỉ đổi màn, nút trong hồ sơ mang
// theo chuyến đang chọn — nên người dùng bấm nút đầu trang rồi phải tự tìm lại
// chuyến vừa xem. Bỏ nút ở đầu trang, giữ nút trong hồ sơ.
assert.strictEqual(
  (deliverySection.match(/switchView\(['"]dispatch['"]\)/g) || []).length,
  0,
  'Đầu trang màn Giao hàng không được có nút Qua điều phối nữa — đường sang Điều phối nằm trong hồ sơ chuyến.'
);
assert.strictEqual(
  (app.match(/'Sửa ở Điều phối'/g) || []).length,
  1,
  'Hồ sơ chuyến phải có đúng một nút Sửa ở Điều phối.'
);
// Màn Điều phối phải có điểm tạo Trip. Nhưng sau khi dựng lại theo bản mẫu
// `dispatch-v2-crew.html`, nút đó không còn gọi `openTripReturnAction` thẳng
// trong thuộc tính `onclick` nữa — nó gọi `xepMoiDOConLai()`, và hàm đó mới
// gọi tiếp, vì phải kiểm trước là các DO đang chọn có cùng một tuyến hay không
// (một Trip chỉ chở được các DO cùng tuyến — chốt của backend).
//
// Nên bài kiểm soi qua HAI chặng: màn có nút, và nút đó dẫn tới đúng chỗ.
assert.match(
  dispatchSection,
  /onclick="xepMoiDOConLai\(\)"/,
  'Màn Điều phối phải có điểm tạo Trip.'
);
assert.match(
  app,
  /window\.xepMoiDOConLai = function[\s\S]{0,2000}?openTripReturnAction\(['"]create-trip['"]/,
  'Nút tạo Trip ở màn Điều phối phải dẫn tới form tạo Trip thật.'
);
assert.doesNotMatch(
  app,
  /delivery-empty-state[\s\S]{0,800}<button[^>]+switchView\(['"]dispatch['"]\)/,
  'Trạng thái rỗng không được lặp thêm nút Qua điều phối.'
);

for (const label of ['Khoản mục phát sinh', 'Giá ban đầu', 'Giá thực tế', 'Tăng thêm', 'Ghi chú']) {
  assert.match(html, new RegExp(label), `Thiếu cột chi phí: ${label}`);
}
assert.match(html, /id="btn-save-do-settlement"/);
assert.match(html, /id="btn-view-original-do"/, 'Thiếu nút view DO ban đầu trong khung quyết toán.');
assert.match(html, /id="do-original-contract-amount-display"/, 'Thiếu vùng hiển thị giá hợp đồng ban đầu ở đầu khung quyết toán.');
assert.match(app, /async function saveDOSettlementCost\s*\(/);
assert.match(app, /window\.viewOriginalDOFromSettlement\s*=\s*function/, 'Thiếu handler view DO ban đầu.');
assert.match(app, /\/api\/tms\/finance\/trips\/\$\{encodeURIComponent\(tripId\)\}\/actual-cost/);
assert.match(app, /original_amount:\s*original/);
assert.match(app, /actual_amount:\s*actual/);
assert.match(app, /position:sticky; right:0/, 'Cột xóa khoản phí phát sinh phải sticky để luôn thấy trên form hẹp.');
assert.doesNotMatch(app, /currentDO\.additional_cost_lines\s*=\s*collectDOSettlementLines/);

console.log('DELIVERY_COST_UI_OK');

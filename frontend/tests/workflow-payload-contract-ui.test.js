const assert = require('assert');
const fs = require('fs');
const path = require('path');

const appSource = fs.readFileSync(path.join(__dirname, '..', 'js', 'app.js'), 'utf8');

function latestFunctionBlock(start, end) {
  const startIndex = appSource.lastIndexOf(start);
  assert.notStrictEqual(startIndex, -1, `Missing source block starting at ${start}.`);
  const endIndex = appSource.indexOf(end, startIndex + start.length);
  assert.notStrictEqual(endIndex, -1, `Missing source block ending at ${end}.`);
  return appSource.slice(startIndex, endIndex);
}

const legacyQuotationSave = latestFunctionBlock('async function submitQuotationForm', 'async function submitDOForm');
assert.match(legacyQuotationSave, /customer_id\s*:/, 'Legacy Quotation form must use customer_id.');
assert.match(legacyQuotationSave, /route_id\s*:/, 'Legacy Quotation form must use route_id.');
for (const field of [
  'origin',
  'destination',
  'pickup_window_start',
  'pickup_window_end',
  'delivery_window_start',
  'delivery_window_end',
  'weight_kg',
  'volume_m3',
  'pallet_count',
  'packaging_spec',
]) {
  assert.match(
    legacyQuotationSave,
    new RegExp(`\\b${field}\\s*:`),
    `Legacy Quotation form must persist ${field}.`
  );
}
assert.doesNotMatch(legacyQuotationSave, /warehouse_fee\s*:/, 'Legacy Quotation form must not send unsupported warehouse_fee.');

const legacyDeliverySave = latestFunctionBlock('async function submitDOForm', 'async function submitIncidentForm');
assert.doesNotMatch(legacyDeliverySave, /so_id/, 'Legacy Delivery Order form must not reference Sales Order any more (SO expelled, migration 049).');
assert.match(legacyDeliverySave, /route_id\s*:/, 'Legacy Delivery Order form must use route_id.');
for (const field of ['customer', 'vehicle', 'driver', 'cargo_desc']) {
  assert.doesNotMatch(
    legacyDeliverySave,
    new RegExp(`\\b${field}\\s*:`),
    `Legacy Delivery Order form contains unsupported field ${field}.`
  );
}

const quotationSave = latestFunctionBlock('window.saveOracleQT = async function', 'window.approveQuotation');
assert.doesNotMatch(
  quotationSave,
  /body:\s*\{[\s\S]*?\bstatus\s*:/,
  'Quotation create/update payload must not submit server-owned workflow status.'
);

const deliveryOrderSave = latestFunctionBlock('window.saveFioriDO = async function', 'window.loadDeliveryOrders');
assert.doesNotMatch(
  deliveryOrderSave,
  /\bcustomer_id\s*:/,
  'Delivery Order customer must be inherited from the accepted quotation.'
);
// DO KHÔNG CÒN TẠO TAY, KHÔNG CÒN TỪ SO: máy chủ sinh DO khi khách chấp nhận báo
// giá. Form DO chỉ còn sửa DO đã có, nên nhánh "tạo mới" phải dừng lại và không
// được gửi `so_id` nữa.
assert.match(
  deliveryOrderSave,
  /if\s*\(!currentDO\)\s*\{[\s\S]*?return;/,
  'Delivery Order form must refuse to create a DO by hand — DOs are generated from accepted quotations.'
);
assert.doesNotMatch(deliveryOrderSave, /payload\.so_id/, 'Delivery Order form must not send so_id any more.');

console.log('WORKFLOW_PAYLOAD_CONTRACT_UI_OK');

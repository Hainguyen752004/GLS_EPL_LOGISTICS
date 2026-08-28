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
assert.doesNotMatch(legacyQuotationSave, /warehouse_fee\s*:/, 'Legacy Quotation form must not send unsupported warehouse_fee.');

const legacyDeliverySave = latestFunctionBlock('async function submitDOForm', 'async function submitIncidentForm');
assert.match(legacyDeliverySave, /payload\.so_id\s*=/, 'Legacy Delivery Order form must identify its confirmed Sales Order source.');
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

const salesOrderSave = latestFunctionBlock('window.saveOracleSO = async function', 'window.approveSO');
for (const field of ['customer_id', 'status', 'carrier_name', 'delivery_method', 'seal_weight']) {
  assert.doesNotMatch(
    salesOrderSave,
    new RegExp(`\\b${field}\\s*:`),
    `Sales Order payload contains unsupported field ${field}.`
  );
}
assert.match(
  salesOrderSave,
  /if\s*\(!currentSO\)\s*\{[\s\S]*?payload\.id[\s\S]*?payload\.quotation_id/,
  'Sales Order identity and quotation source must only be sent when creating.'
);

const deliveryOrderSave = latestFunctionBlock('window.saveFioriDO = async function', 'window.loadDeliveryOrders');
assert.doesNotMatch(
  deliveryOrderSave,
  /\bcustomer_id\s*:/,
  'Delivery Order customer must be inherited from the confirmed Sales Order.'
);
assert.match(
  deliveryOrderSave,
  /if\s*\(!currentDO\)\s*\{[\s\S]*?payload\.id[\s\S]*?payload\.so_id/,
  'Delivery Order identity and Sales Order source must only be sent when creating.'
);

console.log('WORKFLOW_PAYLOAD_CONTRACT_UI_OK');

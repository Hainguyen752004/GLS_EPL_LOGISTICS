const assert = require('assert');
const fs = require('fs');
const path = require('path');

const appSource = fs.readFileSync(path.join(__dirname, '..', 'js', 'app.js'), 'utf8');

assert.match(
  appSource,
  /function openShipment360FromDispatch[\s\S]*?switchView\('operations-360'\)/,
  'Shipment dossier button must open the operations-360 view'
);
assert.match(
  appSource,
  /fetch\(`\$\{API_BASE\}\/api\/data\/all`,\s*\{\s*headers:\s*financeAuthHeaders\(\)/,
  'the broad bootstrap endpoint must receive the configured bearer token'
);
assert.match(
  appSource,
  /api\/delivery-orders\/\$\{encodeURIComponent\(deliveryOrderId\)\}\/dossier/,
  'shipment dossier must load a shipment-scoped payload'
);
assert.match(
  appSource,
  /async function fetchAllPaginated[\s\S]*?page_size[\s\S]*?payload\.total/,
  'large delivery-order lists must be loaded page by page'
);
assert.match(
  appSource,
  /loadDeliveryOrders[\s\S]*?fetchAllPaginated\(`\$\{API_BASE\}\/api\/delivery-orders`/,
  'delivery orders must use the paginated loader instead of silently stopping at the first page'
);
assert.match(
  appSource,
  /function renderAllTables[\s\S]*?activeViewId/,
  'the broad bootstrap must render according to the visible view'
);

console.log('SHIPMENT_DOSSIER_NAVIGATION_OK');

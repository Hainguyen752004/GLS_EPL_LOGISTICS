const assert = require('assert');
const fs = require('fs');
const path = require('path');

const frontendRoot = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(frontendRoot, 'index.html'), 'utf8');
const appSource = fs.readFileSync(path.join(frontendRoot, 'js', 'app.js'), 'utf8');
const routeUtils = require(path.join(frontendRoot, 'js', 'route-map-utils.js'));

const route = {
  id: 'RT-MULTI-STOP',
  segments_json: JSON.stringify([
    { from: 'Kho A', to: 'Tram B', dist_km: 12.5 },
    { from: 'Tram B', to: 'Cang C', dist_km: 33 },
  ]),
};

assert.deepStrictEqual(
  routeUtils.buildRouteContext(route),
  { origin: 'Kho A', destination: 'Cang C' },
  'Route context must use the first and last checkpoints from segments_json.'
);

assert.deepStrictEqual(
  routeUtils.buildRouteCheckpointModel(route),
  [
    { label: 'Kho A', role: 'origin', distanceFromPreviousKm: 0 },
    { label: 'Tram B', role: 'checkpoint', distanceFromPreviousKm: 12.5 },
    { label: 'Cang C', role: 'destination', distanceFromPreviousKm: 33 },
  ],
  'Every configured checkpoint and leg distance must be available to the UI.'
);

for (const prefix of ['qt', 'so', 'do']) {
  assert.match(
    html,
    new RegExp(`id=["']${prefix}-route-checkpoints["']`),
    `${prefix.toUpperCase()} must expose a checkpoint timeline.`
  );
}

assert.match(
  html,
  /id="qt-route"[^>]+onchange="[^"]*selectMasterRoute\('qt',\s*this\.value\)/,
  'Quotation route selection must force-sync Route Master context.'
);
assert.match(
  html,
  /id="so-route-select"[^>]+onchange="[^"]*selectMasterRoute\('so',\s*this\.value\)/,
  'Sales Order route selection must force-sync Route Master context.'
);
assert.match(
  html,
  /id="do-route"[^>]+onchange="[^"]*selectMasterRoute\('do',\s*this\.value\)/,
  'Delivery Order route selection must force-sync Route Master context.'
);

assert.match(appSource, /window\.selectMasterRoute\s*=\s*function/, 'Missing shared Route Master selection handler.');

console.log('ROUTE_CONTEXT_AUTOFILL_UI_OK');

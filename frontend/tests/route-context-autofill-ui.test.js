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

// Tien to 'qt' da RA KHOI danh sach nay, va day KHONG phai mot lan cat bot pham
// vi kiem.
//
// `#qt-route-checkpoints` va `#qt-route` thuoc man Bao gia CU (`#qtv2-khoi-cu`).
// Khoi do van con trong index.html nhung bi `hidden` che, va se bo han khi cua
// chan tai trong duoc chuyen sang man moi — xem chu thich tai khoi do. Kiem mot
// khung khong ai thay duoc thi khong chung minh duoc gi ve nang luc that.
//
// Nang luc "chon tuyen thi hien so do chang" van duoc chot day du: tien to
// `do` con dung khung kieu cu (tien to `so` da truc xuat cung Don hang), con man Bao gia dang chay thi duoc chot boi
// hai phep khang dinh ngay duoi day.
for (const prefix of ['do']) {
  assert.match(
    html,
    new RegExp(`id=["']${prefix}-route-checkpoints["']`),
    `${prefix.toUpperCase()} must expose a checkpoint timeline.`
  );
}

// Man Bao gia MOI: khung so do chang, va no phai duoc ve tu `segments_json` that
// (`dist_km`) chu khong phai chi danh so "chang 1 / chang 2".
{
  const quotationSource = fs.readFileSync(path.join(frontendRoot, 'js', 'bao-gia-v2.js'), 'utf8');
  assert.match(quotationSource, /el\('qtv2-chain'\)/,
    'New quotation screen must expose its own checkpoint timeline container.');
  assert.match(quotationSource, /dist_km/,
    'New quotation timeline must read real leg distances from segments_json.');
  assert.match(html, /id="qtv2-root"/, 'New quotation screen root must exist.');
}

assert.match(
  html,
  /id="do-route"[^>]+onchange="[^"]*selectMasterRoute\('do',\s*this\.value\)/,
  'Delivery Order route selection must force-sync Route Master context.'
);

assert.match(appSource, /window\.selectMasterRoute\s*=\s*function/, 'Missing shared Route Master selection handler.');

console.log('ROUTE_CONTEXT_AUTOFILL_UI_OK');

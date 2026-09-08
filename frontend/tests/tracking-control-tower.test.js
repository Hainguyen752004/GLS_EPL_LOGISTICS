const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { JSDOM } = require('jsdom');
const source = () => fs.readFileSync(require.resolve('../js/tracking-control-tower.js'), 'utf8');
const css = () => fs.readFileSync(require.resolve('../css/tracking-control-tower.css'), 'utf8');

test('selection, search and API failure never display another order or fake success', async () => {
  const dom = new JSDOM('<section id="view-tracking"></section>', { runScripts: 'outside-only' });
  const w = dom.window;
  const row = id => ({ key: id, do_id: id, driver_name: 'Driver', gps: { status: 'missing' }, legs: [], events: [], incidents: [] });
  w.fetch = async () => ({ ok: true, json: async () => ({ items: [row('DO-A'), row('DO-B')], kpis: { total: 2 } }) });
  w.eval(source());
  await w.TrackingControlTower.load();
  w.TrackingControlTower.select('DO-B');
  assert.match(w.document.querySelector('#ct-detail').textContent, /DO-B/);
  const search = w.document.querySelector('#ct-search');
  search.value = 'DO-A';
  search.dispatchEvent(new w.Event('input', { bubbles: true }));
  assert.doesNotMatch(w.document.querySelector('#ct-list').textContent, /DO-B/);
  assert.doesNotMatch(w.document.querySelector('#ct-detail').textContent, /DO-B/);
  w.fetch = async () => ({ ok: false, status: 503, json: async () => ({ detail: 'Offline' }) });
  await w.TrackingControlTower.load();
  assert.match(w.document.querySelector('#ct-status').textContent, /Offline/);
  assert.equal(w.document.querySelectorAll('#ct-list [data-key]').length, 0);
  dom.window.close();
});

test('failed incident save keeps entered fields and sends the selected DO and vehicle', async () => {
  const dom = new JSDOM('<section id="view-tracking"></section>', { runScripts: 'outside-only' });
  const w = dom.window;
  w.HTMLDialogElement.prototype.showModal = function () { this.open = true; };
  w.HTMLDialogElement.prototype.close = function () { this.open = false; };
  const row = { key: 'T:B', do_id: 'B', vehicle_id: 'V-B', driver_name: '<img src=x onerror=alert(1)>', gps: { status: 'missing' }, legs: [], events: [], incidents: [] };
  let posted;
  w.fetch = async (url, options) => {
    if (options?.method === 'POST') {
      posted = JSON.parse(options.body);
      return { ok: false, status: 409, json: async () => ({ error: { message: 'Vehicle changed' } }) };
    }
    return { ok: true, json: async () => ({ items: [row], kpis: { total: 1 } }) };
  };
  w.eval(source());
  await w.TrackingControlTower.load();
  w.TrackingControlTower.select('T:B');
  assert.equal(w.document.querySelectorAll('#ct-detail img').length, 0);
  w.document.querySelector('[data-action="incident"]').click();
  const form = w.document.querySelector('#ct-incident-form');
  form.elements.location.value = 'Warehouse';
  form.elements.reporter.value = 'Tester';
  form.elements.description.value = 'Keep my report';
  form.dispatchEvent(new w.Event('submit', { bubbles: true, cancelable: true }));
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(posted.do_id, 'B');
  assert.equal(posted.vehicle_id, 'V-B');
  assert.equal(w.document.querySelector('#ct-incident').open, true);
  assert.equal(form.elements.description.value, 'Keep my report');
  assert.match(w.document.querySelector('#ct-incident-error').textContent, /Vehicle changed/);
  dom.window.close();
});

test('selecting a trip opens selected route mode and draws route waypoints', async () => {
  const dom = new JSDOM('<section id="view-tracking"></section>', { runScripts: 'outside-only', pretendToBeVisual: true });
  const w = dom.window;
  const calls = { polylines: [], markers: [] };
  const chain = () => ({ addTo() { return this; }, bindTooltip() { return this; }, on() { return this; } });
  w.requestAnimationFrame = cb => cb();
  w.L = {
    map: () => ({ setView() { return this; }, invalidateSize() {}, fitBounds() {}, hasLayer() { return false; }, removeLayer() {} }),
    tileLayer: () => ({ on() { return this; }, addTo() { return this; } }),
    layerGroup: () => ({ addTo() { return this; }, clearLayers() {} }),
    circleMarker: (point) => { calls.markers.push(point); return chain(); },
    marker: (point) => { calls.markers.push(point); return chain(); },
    divIcon: () => ({}),
    polyline: (points) => { calls.polylines.push(points); return chain(); },
  };
  const row = {
    key: 'TRIP-1:DO-1',
    trip_id: 'TRIP-1',
    do_id: 'DO-1',
    route_name: 'VSIP - Cat Lai',
    vehicle_id: 'V1',
    driver_name: 'Driver',
    gps: { status: 'missing' },
    route_segments: [
      { origin: 'Kho VSIP II-A', destination: 'Vanh dai 3', origin_lat: 11.0497, origin_lng: 106.7428, destination_lat: 10.8769, destination_lng: 106.7734 },
      { origin: 'Vanh dai 3', destination: 'Cang Cat Lai', origin_lat: 10.8769, origin_lng: 106.7734, destination_lat: 10.7567, destination_lng: 106.7828 },
    ],
    legs: [],
    events: [],
    incidents: []
  };
  w.fetch = async (url) => {
    if (String(url).includes('router.project-osrm.org')) {
      return { ok: true, json: async () => ({ routes: [{ geometry: { coordinates: [[106.7428, 11.0497], [106.751, 11.01], [106.7734, 10.8769], [106.7828, 10.7567]] } }] }) };
    }
    return { ok: true, json: async () => ({ items: [row], kpis: { total: 1 } }) };
  };
  w.eval(source());
  await w.TrackingControlTower.load();
  w.document.querySelector('[data-key="TRIP-1:DO-1"]').click();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(w.document.querySelector('[data-mode="route"]').getAttribute('aria-pressed'), 'true');
  assert.equal(calls.polylines.length > 0, true);
  assert.equal(JSON.stringify(calls.polylines.at(-1).map(([lat, lng]) => [lat, lng])), JSON.stringify([
    [11.0497, 106.7428],
    [11.01, 106.751],
    [10.8769, 106.7734],
    [10.7567, 106.7828],
  ]));
  assert.match(w.document.querySelector('#ct-map-note').textContent, /theo chuẩn đường xe chạy/i);
  dom.window.close();
});

test('incident dialog is a centered working form instead of a narrow side box', () => {
  const styles = css();
  assert.match(styles, /#ct-incident\s*\{[^}]*width:\s*min\(920px,\s*calc\(100vw - 32px\)\)/s);
  assert.match(styles, /#ct-incident\s*\{[^}]*margin:\s*auto/s);
  assert.match(styles, /\.ct-form-grid\s*\{[^}]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/s);
});

test('out-of-order refresh does not overwrite a newer response', async () => {
  const dom = new JSDOM('<section id="view-tracking"></section>', { runScripts: 'outside-only' });
  const w = dom.window, waiting = [];
  w.fetch = () => new Promise(resolve => waiting.push(resolve));
  w.eval(source());
  const first = w.TrackingControlTower.load(), second = w.TrackingControlTower.load();
  const response = id => ({ ok: true, json: async () => ({ kpis: { total: 1 }, items: [{ key:id,do_id:id,gps:{status:'missing'},legs:[],events:[],incidents:[] }] }) });
  waiting[1](response('NEW'));
  await second;
  waiting[0](response('OLD'));
  await first;
  assert.match(w.document.querySelector('#ct-list').textContent, /NEW/);
  assert.doesNotMatch(w.document.querySelector('#ct-list').textContent, /OLD/);
  dom.window.close();
});

// Nhan nut ghi moc: BIEU TUONG la markup, TEN MOC la du lieu.
//
// Loi da xay ra that va nguoi dung nhin thay ngay tren mat nut: ca nhan duoc boc
// `esc()`, nen nut hien nguyen chuoi `<i class="fa-solid fa-dolly"></i> Ghi moc:
// Do hang` thanh CHU. Bai kiem nay soi ca hai phia cua duong ranh do — mot phia
// long thi bieu tuong thanh chu, phia kia long thi ten moc tu may chu chen duoc
// the vao trang.
test('nut ghi moc: bieu tuong la the that, con ten moc thi duoc thoat', async () => {
  const dom = new JSDOM('<section id="view-tracking"></section>', { runScripts: 'outside-only' });
  const w = dom.window;
  const row = {
    key: 'T:D', do_id: 'D', vehicle_id: 'V', gps: { status: 'missing' }, legs: [], events: [],
    incidents: [], freight_order_id: 'FO-1', freight_order_version: 1,
    next_milestone: { ma: 'unloading', ten: 'Dỡ hàng <img src=x onerror=alert(1)>' },
    milestones: [{ ma: 'unloading', ten: 'Dỡ hàng' }],
  };
  w.fetch = async () => ({ ok: true, json: async () => ({ items: [row], kpis: { total: 1 } }) });
  w.eval(source());
  await w.TrackingControlTower.load();
  w.TrackingControlTower.select('T:D');
  const nut = [...w.document.querySelectorAll('#ct-detail [data-action="milestone"]')];
  assert.equal(nut.length, 1, 'phai co dung mot nut ghi moc');
  // Bieu tuong phai la MOT THE that, khong phai chu. Ten lop cua bieu tuong
  // khong bao gio duoc xuat hien trong phan CHU cua nut — no o day thi nghia la
  // markup da bi thoat va nguoi dung doc thay `<i class="fa-solid ...">`.
  assert.equal(nut[0].querySelectorAll('i.fa-dolly').length, 1);
  assert.doesNotMatch(nut[0].textContent, /fa-|class=/, 'bieu tuong bi thoat thanh chu tren mat nut');
  // Ten moc den tu may chu thi PHAI duoc thoat: hien nguyen van thanh CHU, va
  // khong tao ra the nao trong trang.
  assert.equal(nut[0].querySelectorAll('img').length, 0, 'ten moc phai duoc thoat');
  assert.match(nut[0].textContent, /Ghi mốc: Dỡ hàng <img src=x/);
  dom.window.close();
});

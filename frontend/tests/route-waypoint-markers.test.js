/**
 * Ghim tren so do lo trinh da chang.
 *
 * Van de cu: moi ghim deu la pin xanh mac dinh cua Leaflet nen khong doc duoc
 * dau la diem bat dau, dau la diem ket thuc.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const frontendRoot = path.join(__dirname, '..');
const utils = require(path.join(frontendRoot, 'js', 'route-map-utils.js'));
const app = fs.readFileSync(path.join(frontendRoot, 'js', 'app.js'), 'utf8');
const html = fs.readFileSync(path.join(frontendRoot, 'index.html'), 'utf8');

// --- 1. Vai tro gan theo thu tu di ---------------------------------------

{
  const model = utils.buildWaypointMarkerModel([
    { lat: 10.9, lng: 106.7, label: 'KCN VSIP II-A' },
    { lat: 10.8, lng: 106.8, label: 'Vành đai 3' },
    { lat: 10.7, lng: 106.9, label: 'Cảng Cát Lái' },
  ]);
  assert.deepStrictEqual(model.map(m => m.role), ['origin', 'stop', 'destination']);
  assert.deepStrictEqual(model.map(m => m.order), [1, 2, 3]);
  // Ba mau phai KHAC NHAU — day chinh la loi duoc bao.
  assert.strictEqual(new Set(model.map(m => m.color)).size, 3, 'ba vai tro phai ba mau khac nhau');
  assert.strictEqual(model[0].color, '#dc2626', 'diem di phai la mau do');
  assert.strictEqual(model[2].color, '#059669', 'diem den phai khac mau diem di');
  // Toa do giu nguyen de con ve duoc.
  assert.strictEqual(model[0].lat, 10.9);
  assert.strictEqual(model[0].lng, 106.7);
  assert.strictEqual(model[1].label, 'Vành đai 3');
}

// Chi hai diem: khong co diem trung chuyen nao.
assert.deepStrictEqual(
  utils.buildWaypointMarkerModel([{ lat: 1, lng: 2 }, { lat: 3, lng: 4 }]).map(m => m.role),
  ['origin', 'destination']
);

// Mot diem duy nhat la diem di: chua co dau den nao ca.
assert.deepStrictEqual(utils.buildWaypointMarkerModel([{ lat: 1, lng: 2 }]).map(m => m.role), ['origin']);

// Dau vao rong hoac sai kieu khong duoc lam vo ban do.
assert.deepStrictEqual(utils.buildWaypointMarkerModel([]), []);
assert.deepStrictEqual(utils.buildWaypointMarkerModel(null), []);
assert.deepStrictEqual(utils.buildWaypointMarkerModel([null, { lat: 1, lng: 2 }]).length, 1);

// --- 2. Mau khong bao gio dung mot minh ----------------------------------

{
  const model = utils.buildWaypointMarkerModel([{ lat: 1, lng: 2 }, { lat: 3, lng: 4 }, { lat: 5, lng: 6 }, { lat: 7, lng: 8 }]);
  // Hai dau mut deo icon rieng; diem giua deo SO THU TU.
  assert.strictEqual(model[0].glyph, '', 'diem di dung icon, khong dung so');
  assert.strictEqual(model[3].glyph, '', 'diem den dung icon, khong dung so');
  assert.deepStrictEqual([model[1].glyph, model[2].glyph], ['2', '3'], 'diem giua phai mang so thu tu');
  assert.notStrictEqual(model[0].icon, model[3].icon, 'diem di va diem den phai khac icon');
  model.forEach(m => {
    assert.ok(m.icon, 'moi diem phai co icon');
    assert.ok(m.roleLabel, 'moi diem phai co nhan doc duoc bang chu');
  });
  // Nhan chu phai la tieng Viet doc duoc, khong phai ma key.
  assert.deepStrictEqual(
    [...new Set(model.map(m => m.roleLabel))],
    ['Điểm đi', 'Điểm trung chuyển', 'Điểm đến']
  );
}

// --- 3. Tich hop trong app.js va CSS -------------------------------------

assert.match(app, /buildWaypointMarkerModel/, 'ban do phai dung model vai tro thay vi pin mac dinh');
assert.match(app, /L\.divIcon/, 'ghim phai la divIcon co mau, khong phai L.marker mac dinh');
assert.match(app, /renderRouteWaypointLegend/, 'phai co thanh chu giai duoi ban do');
// Nhan va ten diem den tu du lieu nguoi dung nhap, nen phai thoat ky tu.
{
  const start = app.indexOf('markerModel.forEach((w) => {');
  assert.ok(start > 0, 'phai con vong lap dung ghim');
  const fn = app.slice(start, app.indexOf('renderRouteWaypointLegend(markerModel)', start));
  // Chi xet phan DI VAO innerHTML. Rieng option title cua Leaflet thi de
  // nguyen la dung: no duoc dat qua thuoc tinh title, escape them se hien
  // "&amp;" cho nguoi dung.
  const intoHtml = fn.split(String.fromCharCode(10)).filter(line => line.includes('html:') || line.includes('bindPopup')).join(' | ');
  assert.ok(intoHtml, 'phai tim thay phan dung HTML cua ghim');
  assert.ok(!/\$\{w\.label\}/.test(intoHtml), 'ten diem phai di qua escapeHtml truoc khi vao innerHTML');
  assert.match(fn, /escapeHtml\(w\.label\)/);
}
// Chu giai phai duoc don khi xoa ghim, khong de lai chu giai cua tuyen cu.
{
  const start = app.indexOf('window.clearLeafletRouteMap = function ()');
  const fn = app.slice(start, app.indexOf('\n};', start));
  assert.match(fn, /renderRouteWaypointLegend\(\[\]\)/, 'xoa ghim phai xoa ca chu giai');
}

assert.match(html, /\.rmap-pin\s*\{/, 'index.html phai co CSS cho ghim mau');
assert.match(html, /\.rmap-legend\s*\{/, 'index.html phai co CSS cho thanh chu giai');
// Diem den con khac ca do day vien: khac HINH DANG, khong chi khac mau.
assert.match(html, /\.rmap-pin--destination\s*\{[^}]*border-width/, 'diem den phai khac ca hinh dang');

console.log('route-waypoint-markers: tất cả kiểm tra đã qua');

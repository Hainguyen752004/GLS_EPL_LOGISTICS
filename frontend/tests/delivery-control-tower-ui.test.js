const assert = require('assert');
const fs = require('fs');
const path = require('path');

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(__dirname, '..', 'js', 'app.js'), 'utf8');
const cockpit = require('../js/tms-cockpit-utils.js');

assert.ok(html.includes('id="trip-return-status-tabs"'), 'delivery control tower needs status tabs');
assert.ok(html.includes('id="trip-return-detail-tabs"'), 'selected trip needs focused detail tabs');
assert.ok(html.includes('id="trip-return-detail-pane"'), 'selected detail tab needs one stable content pane');
assert.ok(!html.includes('id="trip-return-kpis"'), 'old KPI-card strip should be removed');
// Man Giao hang & van chuyen da dung LAI theo ban mau
// `nhap_UI__duan/trip-lifecycle.html`, nen tam dong duoi day khong
// con: chung khoa dung nhung ma mau va ten lop cua THIET KE CU
// (`.delivery-control-heading`, `--delivery-divider: #bdcad8`, `#dcecff`...).
//
// Do la thu mot ban thay giao dien phai duoc phep doi. Nhung DIEU chung bao ve
// thi khong doi, va bai kiem doi moc sang bo cuc moi thay vi bo phep kiem:
//
//   · ba cot / hai cot deu phai co duong vien va vach chia thay duoc, khong
//     phai ba khoi trang lien nhau khong biet dau la ranh;
//   · dong chuyen dang chon phai noi bat han cac dong khac;
//   · khung ho so phai co ranh gioi rieng.
{
  const iMan = html.indexOf('<section id="view-delivery-shipment"');
  assert.ok(iMan > 0, 'khong thay man Giao hang & van chuyen');
  const man = html.slice(iMan, html.indexOf('<section id="view-', iMan + 10));

  // Dau muc rieng cho khung ho so, thay cho `.delivery-control-heading` cu.
  assert.ok(/<div class="ph"/.test(man) || man.includes('class="ph"'),
    'control tower title needs a distinct structural header');
  // Vach chia giua cac phan cua bang.
  assert.ok(/\.tlv2 \.life\s*\{[^}]*border-bottom:1px solid var\(--tl-line\)/.test(html),
    'control tower needs a visible section divider');
  assert.ok(/\.tlv2 \.card\s*\{[^}]*border:1px solid var\(--tl-line\)/.test(html),
    'control tower needs a clearly visible outer border');
  // Dong dang chon phai noi bat.
  assert.ok(/\.tlv2 \.trips tbody tr\.on\s*\{[^}]*background:var\(--tl-blue2\)/.test(html),
    'selected trip needs a stronger selected surface');
  // Khung ho so co ranh gioi rieng va dau muc rieng.
  assert.ok(/\.tlv2 \.ph\s*\{[^}]*border-bottom:1px solid var\(--tl-line\)/.test(html),
    'detail content needs a stable section boundary');
}

assert.ok(app.includes('function setTripReturnStatusTab('), 'status tabs need a controller');
assert.ok(app.includes('function setTripReturnDetailTab('), 'detail tabs need a controller');
assert.ok(app.includes('Chặng đường'));
assert.ok(app.includes('Xe & nhân sự'));
assert.ok(app.includes('POD'));
assert.ok(app.includes('Sự kiện'));
// Tab Chi phi la tab MOI, theo ban mau: chi phi thuc so ke hoach la thu quyet
// dinh chuyen co lo hay khong. Chi nap cho chuyen DANG CHON — mot loi goi —
// chu khong nap cho ca bang.
assert.ok(app.includes("'cost'"), 'trip profile needs an actual-vs-planned cost tab');
assert.ok(/setTripReturnDetailTab[\s\S]{0,300}'cost'/.test(app),
  'the cost tab must be accepted by the tab controller, not fall back to another tab');
assert.ok(app.includes('Việc cần làm tiếp'));

assert.strictEqual(cockpit.getTripStatusGroup({
  status: 'in_transit',
  legs: [{ leg_type: 'delivery', status: 'in_transit' }]
}), 'active');
assert.strictEqual(cockpit.getTripStatusGroup({
  status: 'in_transit',
  legs: [
    { leg_type: 'delivery', status: 'completed' },
    { leg_type: 'empty_return', status: 'planned' }
  ]
}), 'waiting_return');
assert.strictEqual(cockpit.getTripStatusGroup({ status: 'completed', legs: [] }), 'completed');
assert.strictEqual(cockpit.getTripStatusGroup({
  status: 'in_transit',
  legs: [{ leg_type: 'delivery', status: 'completed' }]
}), 'missing_return');

console.log('DELIVERY_CONTROL_TOWER_UI_OK');

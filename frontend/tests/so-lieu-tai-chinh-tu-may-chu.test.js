/**
 * Bon the so lieu cua Finance Cockpit phai lay so tu MAY CHU.
 *
 * SU THAT DA XAY RA. `/api/data/all` CO TINH boi trang ba tap du lieu tai
 * chinh — `freight_actual_costs`, `ap_invoices`, `settlements` — thanh mang
 * rong (xem `routes/data_export_routes.py`: du lieu tai chinh chi duoc phat
 * qua endpoint co kiem quyen). Nhung man Finance Cockpit lai dem bon con so
 * cua no ngay tren ba mang do trong `appState`. Ket qua: ca bon the hien 0
 * VINH VIEN, va ba danh sach ben duoi hien "khong co ... dang cho xu ly".
 *
 * Do duoc tren PostgreSQL that cua du an: co BA ho so chi phi dang o trang
 * thai `submitted` cho duyet, ma the "Actual Cost cho duyet" van ghi 0 va ba
 * viec can duyet do bien mat khoi tam mat nguoi lam tai chinh. Mot con so 0
 * sai trong y het mot con so 0 dung — day la cung ho loi voi bai
 * `dashboard-load-honesty`.
 *
 * Va ke ca sau khi nap bo sung, ba duong liet ke (`/costs`, `/ap-invoices`,
 * `/settlements`) deu chi tra 100 ban ghi moi nhat. O quy mo hang nghin
 * chuyen thi dem tren 100 dong la dem sai. Nen con so tong phai den tu
 * `COUNT(*)` cua may chu, con danh sach 100 dong la "viec can lam gan nhat".
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const gocFrontend = path.join(__dirname, '..');
const gocBackend = path.join(__dirname, '..', '..', 'backend', 'app');
const app = fs.readFileSync(path.join(gocFrontend, 'js', 'app.js'), 'utf8');
const dichVu = fs.readFileSync(
  path.join(gocBackend, 'services', 'tms_settlement_service.py'), 'utf8');
const xuatDuLieu = fs.readFileSync(
  path.join(gocBackend, 'routes', 'data_export_routes.py'), 'utf8');

// --- 1. Ba tap bi boi trang phai duoc nap bo sung -----------------------
//
// Kiem ca hai dau. Neu mot ngay nao do `/api/data/all` thoi boi trang thi bai
// nay se do o phan duoi va nguoi sua se doc duoc ly do — con neu nguoi ta bo
// ba dong nap bo sung o app.js thi no do o phan tren.

const TAP_BOI_TRANG = ['freight_actual_costs', 'ap_invoices', 'settlements'];

{
  const dau = app.indexOf('async function hydrateFinanceState()');
  assert.ok(dau > 0, 'phai con ham nap bo sung du lieu tai chinh');
  const than = app.slice(dau, app.indexOf('\nasync function loadAllData()', dau));

  const DUONG = {
    freight_actual_costs: '/api/tms/finance/costs',
    ap_invoices: '/api/tms/finance/ap-invoices',
    settlements: '/api/tms/finance/settlements',
  };
  TAP_BOI_TRANG.forEach(khoa => {
    assert.ok(
      than.includes(`'${khoa}'`),
      `hydrateFinanceState khong nap '${khoa}' — /api/data/all boi trang tap nay, `
      + 'nen Finance Cockpit se hien rong vinh vien');
    assert.ok(
      than.includes(DUONG[khoa]),
      `phai nap '${khoa}' tu ${DUONG[khoa]}`);
  });

  // Nap bo sung ma im lang khi 403 thi quay ve dung con so 0 sai cu.
  assert.match(than, /if \(!res\.ok\)/, 'phai xu ly truong hop may chu tu choi');
  assert.match(than, /baoNapThatBai/, 'that bai phai duoc bao ra man hinh');
}

{
  // Doi chieu voi ma may chu: dung ba tap nay dang bi boi trang.
  const khoiBoiTrang = /for sensitive_key in \(([^)]*)\)/.exec(xuatDuLieu);
  assert.ok(khoiBoiTrang, 'khong tim thay danh sach tap bi boi trang trong /api/data/all');
  TAP_BOI_TRANG.forEach(khoa => {
    assert.ok(
      khoiBoiTrang[1].includes(`"${khoa}"`),
      `'${khoa}' khong con bi boi trang trong /api/data/all — neu that thi go dong `
      + 'nap bo sung tuong ung o app.js, dung nap hai lan');
  });
}

// --- 2. Bon the phai duoc ghi de bang so cua may chu --------------------

{
  const dau = app.indexOf('function renderFinanceCockpit()');
  assert.ok(dau > 0, 'phai con ham ve Finance Cockpit');
  const than = app.slice(dau, dau + 4000);

  assert.match(than, /apSoLieuMayChuVaoTheKpi\(cockpit\.kpis\)/,
    'phai ap so dem-toan-bang cua may chu len bon the truoc khi ve');
  assert.match(than, /napSoLieuTaiChinhTuMayChu\(\)/,
    'lan dau vao man phai nap goi so lieu tu may chu');
  // Vao man lan dau phai ve lai sau khi goi ve, neu khong thi phai bam sang
  // man khac roi bam lai moi thay so.
  assert.match(than, /\.then\(goi => \{ if \(goi\) renderFinanceCockpit\(\); \}\)/,
    'nap xong phai ve lai mot lan');
}

{
  const dau = app.indexOf('async function napSoLieuTaiChinhTuMayChu()');
  assert.ok(dau > 0, 'phai con ham nap goi so lieu tai chinh');
  const than = app.slice(dau, app.indexOf('\nfunction apSoLieuMayChuVaoTheKpi', dau));
  assert.ok(than.includes('/api/tms/finance/dashboard'),
    'phai goi dung diem cuoi dashboard tai chinh');
  assert.match(than, /financeAuthHeaders\(\)/,
    'duong nay doi quyen finance_read nen phai gui token');
  assert.match(than, /if \(!res\.ok\)/, 'phai xu ly 401/403');
  assert.match(than, /baoNapThatBai/,
    'mot 403 lam man hinh quay ve dem tai may — tuc ve dung con so 0 sai cu — nen phai bao ra');
}

// --- 3. Ten truong hai ben phai TRUNG ----------------------------------
//
// Day la cho de vo nhat va vo IM LANG: doi ten mot khoa o Python thi
// `apSoLieuMayChuVaoTheKpi` khong tim thay gi, khong nem loi, va man hinh
// lang le quay ve con so dem tai may — dung cai loi bai nay di chua.

const KHOA_MAY_CHU = [
  'actual_cost_pending_count',
  'ap_waiting_post_count',
  'settlement_open_count',
  'total_payable',
  'currency_code',
  'list_row_cap',
];

{
  const dau = dichVu.indexOf('def get_finance_dashboard(');
  assert.ok(dau > 0, 'phai con ham get_finance_dashboard');
  const than = dichVu.slice(dau);

  const dauAp = app.indexOf('function apSoLieuMayChuVaoTheKpi(');
  assert.ok(dauAp > 0, 'phai con ham ap so lieu may chu vao the');
  const thanAp = app.slice(dauAp, app.indexOf('\nfunction renderFinanceCockpit', dauAp));

  KHOA_MAY_CHU.forEach(khoa => {
    assert.ok(than.includes(`"${khoa}"`),
      `may chu khong con tra ve '${khoa}'`);
    assert.ok(thanAp.includes(khoa),
      `giao dien khong doc '${khoa}' — doi ten mot ben ma khong doi ben kia thi `
      + 'man hinh lang le quay ve so dem tai may');
  });
}

// --- 4. Bo loc cua may chu phai TRUNG voi nhan nguoi dung doc ------------
//
// Nhan "cho duyet" ma dem ca dong da duyet thi con so dung ve ky thuat nhung
// sai voi cai nguoi doc hieu. Ghim tung tap trang thai lai day.

{
  const dau = dichVu.indexOf('def get_finance_dashboard(');
  const than = dichVu.slice(dau);

  assert.match(than, /FreightActualCost\.status\.in_\(\["draft", "submitted"\]\)/,
    '"Actual Cost cho duyet" = draft + submitted, khong gom approved');
  assert.match(than, /APInvoice\.status\.in_\(\["draft", "submitted", "approved"\]\)/,
    '"AP cho hach toan" = chua post len so');
  assert.match(than, /FreightSettlement\.status\.in_\(\["open", "partially_paid"\]\)/,
    '"Settlement con mo" = chua tra xong');

  // Dong da dao (`reversed`) mang `is_active = false` theo rang buoc cua bang.
  // Dem ca dong dao la cong mot khoan da bi huy vao cong no.
  const soLanLocHoatDong = (than.match(/is_active\.is_\(True\)/g) || []).length;
  assert.ok(soLanLocHoatDong >= 3,
    'moi phep dem/cong tren bang co cot is_active phai loc dong da dao — '
    + `dem duoc ${soLanLocHoatDong} cho loc`);

  // Tien phai cong theo cot QUY DOI. Hai hoa don 1.000 LAK va 1.000 USD cong
  // thang thi ra 2.000 cua mot don vi khong ton tai — ban cu cua ham nay cong
  // thang `total_amount` roi man hinh dan nhan "VND" len ket qua do.
  assert.match(than, /APInvoice\.functional_total_amount/,
    'tong phai tra phai cong theo cot quy doi, khong theo total_amount goc');
  assert.match(than, /SettlementPayment\.functional_amount/,
    'tong da thanh toan phai cong theo cot quy doi');
}

// --- 5. Vua ghi xong thi goi cu phai bi bo ------------------------------

{
  assert.match(app, /soLieuTaiChinhMayChu = null;\r?\n\s*if \(typeof renderFinanceCockpit/,
    'sau mot lenh tai chinh thanh cong phai bo goi so lieu cu — giu lai la hien '
    + 'mot con so ma chinh nguoi dung vua lam cho no sai');
}

console.log('so-lieu-tai-chinh-tu-may-chu: OK');

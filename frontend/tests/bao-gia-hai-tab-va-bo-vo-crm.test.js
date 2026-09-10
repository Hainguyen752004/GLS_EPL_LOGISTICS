/**
 * Màn Báo giá cước: bỏ vỏ hai thẻ CRM, phiếu chia hai tab.
 *
 * Chủ dự án chỉ ba ảnh (10/09): (1) màn báo giá mới đã có khung riêng nhưng bị
 * bọc thêm một khung "CRM / Báo giá cước / Đơn hàng vận chuyển" với hai thẻ —
 * "không làm dạng 2 tab nữa"; (2) thẻ "Khách hàng và cơ hội" là Kanban chạy
 * bằng dữ liệu Đơn hàng (bước đã bỏ) — muốn làm CRM thật thì phải ra màn riêng,
 * không để chung; (3) phiếu báo giá tám mục dồn một cột quá dài — mục 1–6 một
 * tab, mục 7–8 tab khác.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8');
const bg = fs.readFileSync(path.join(ROOT, 'js', 'bao-gia-v2.js'), 'utf8');
const css = fs.readFileSync(path.join(ROOT, 'css', 'bao-gia-v2.css'), 'utf8');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');

// 1. Không còn vỏ thẻ cho màn Kinh doanh.
{
  assert.ok(!/sectionId:\s*'view-crm-sales'/.test(app), 'installEnterpriseModuleTabs không còn bọc view-crm-sales');
  assert.ok(!/\['crm-sales-folder-tabs',\s*'quotation'\]/.test(app), 'không còn chọn thẻ Báo giá trong vỏ');
  assert.ok(!/getElementById\('crm-kanban-board'\)\.style\.display = 'grid'/.test(app), 'không còn lệnh bật lại Kanban');
}

// 2. Kanban cơ hội đã GỠ HẲN cùng bước Đơn hàng (SO) — không còn markup lẫn CSS.
{
  assert.ok(!/id="crm-kanban-board"/.test(html), 'markup Kanban phải gỡ hẳn');
  assert.ok(!/CRM Opportunity Management/.test(html), 'tiêu đề Kanban gỡ theo');
  assert.ok(!/\.kanban-board\s*\{/.test(html), 'CSS Kanban gỡ theo');
  assert.ok(!/id="so-khoi-cu"/.test(html), 'khối Đơn hàng cũ phải gỡ hẳn');
}

// 3. Phiếu chia hai tab: 1–6 và 7–8; nhớ tab khi vẽ lại; cuộn tới mục 6 thì về tab 1.
{
  const i = bg.indexOf('function vePhieu()');
  const than = bg.slice(i, bg.indexOf('<aside class="card rail">', i));
  assert.ok(/id="qtv2-phieu-tabs"/.test(than), 'có thanh tab, id KHÁC #qtv2-tabs của màn danh sách');
  assert.strictEqual((bg.match(/id="qtv2-tabs"/g) || []).length, 1, 'không trùng id với thẻ lọc của danh sách');
  assert.ok(/el\('qtv2-phieu-tabs'\)\.addEventListener\('click'/.test(bg), 'nút tab nối đúng phần tử');
  assert.ok(!/<b>1–6<\/b>/.test(than) && !/<b>7–8<\/b>/.test(than), 'không còn số 1–6 / 7–8 trên tab');
  const tab1 = than.slice(than.indexOf('data-tab="1" ${S.tabPhieu'), than.indexOf('data-tab="2" ${S.tabPhieu'));
  const tab2 = than.slice(than.indexOf('data-tab="2" ${S.tabPhieu'));
  ['mucChung', 'mucTuyen', 'mucHangHoa', 'mucLoaiXe', 'mucGia', 'mucTachDo'].forEach(m =>
    assert.ok(tab1.includes('${' + m + '('), 'tab 1 phải có ' + m));
  ['mucChungTu', 'mucGhiChu'].forEach(m => {
    assert.ok(tab2.includes('${' + m + '('), 'tab 2 phải có ' + m);
    assert.ok(!tab1.includes('${' + m + '('), m + ' không được ở tab 1');
  });
  assert.ok(/function chonTabPhieu\(so\)/.test(bg) && /S\.tabPhieu = so === 2 \? 2 : 1/.test(bg), 'nhớ tab vào S');
  const iCuon = bg.indexOf("cuonToi(el('qtv2-sec-do'))");
  assert.ok(iCuon > 0 && bg.slice(iCuon - 40, iCuon).includes('chonTabPhieu(1);'), 'cuộn tới mục 6 thì phải mở tab 1 trước');
  assert.ok(/\.qtv2 \.qtv2-tabs button\.on/.test(css) && /\.qtv2 \.qtv2-tab\[hidden\]/.test(css), 'CSS tab');
}

console.log('bao-gia-hai-tab-va-bo-vo-crm: OK');

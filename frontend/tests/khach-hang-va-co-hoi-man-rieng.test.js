/**
 * Khách hàng & cơ hội (CRM-01/02) là MÀN RIÊNG, đứng trước Báo giá.
 *
 * Chủ dự án duyệt: "một màn riêng có bảng dữ liệu riêng (lead → cơ hội → bấm
 * Lập báo giá sinh QT), đứng trước Báo giá, không nằm chung trang". Bài kiểm
 * khoá: có section + module riêng, menu Kinh doanh xếp Cơ hội trước Báo giá,
 * module nối đúng API, hai mốc `quoted`/`won` không kéo tay, và "Lập báo giá"
 * mở thẳng phiếu vừa sinh ở màn Báo giá.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const js = fs.readFileSync(path.join(ROOT, 'js', 'co-hoi.js'), 'utf8');
const khung = fs.readFileSync(path.join(ROOT, 'js', 'khung-moi.js'), 'utf8');
const lang = JSON.parse(fs.readFileSync(path.join(ROOT, 'js', 'lang.json'), 'utf8'));

// 1. Section riêng, đứng trần, có css/js riêng.
assert.ok(/<section id="view-co-hoi" class="view-section"[^>]*>\s*<div class="fiori-container"><div id="cohoi-root"><\/div><\/div>\s*<\/section>/.test(html), 'section riêng, không vỏ thẻ');
assert.ok(/css\/co-hoi\.css\?v=/.test(html) && /js\/co-hoi\.js\?v=/.test(html));
assert.ok(html.indexOf('id="view-co-hoi"') < html.indexOf('id="view-crm-sales"'), 'đứng trước màn Báo giá');

// 2. Menu Kinh doanh: Cơ hội trước Báo giá; nhãn Báo giá không còn "CRM và".
{
  const iCo = html.indexOf('data-view="co-hoi"'), iBg = html.indexOf('class="epl-mi" role="menuitem" tabindex="0" data-view="crm-sales"');
  assert.ok(iCo > 0 && iBg > iCo, 'menu: Cơ hội đứng trước Báo giá');
  assert.strictEqual(lang.khung_mi_crm.vi, 'Báo giá cước');
  assert.strictEqual(lang.khung_mi_cohoi.vi, 'Khách hàng và cơ hội');
  assert.ok(lang.khung_mi_cohoi.la && lang.khung_mi_cohoi.en, 'đủ ba ngôn ngữ');
  assert.ok(/'co-hoi': \['biz', 'Kinh doanh', 'Khách hàng và cơ hội'/.test(khung), 'khung có tiêu đề màn');
  assert.ok(/\['Khách hàng và cơ hội', 'Lead, cơ hội, hồ sơ khách', 'co-hoi'/.test(khung), 'ô tìm có gợi ý');
}

// 3. Module nối đúng API, không tự tính.
['/api/crm/opportunities', '/api/crm/opportunities/summary', '/quotation', '/stage', '/api/crm/customers', '/profile']
  .forEach(d => assert.ok(js.includes(d), 'thiếu đường ' + d));
assert.ok(/window\.CoHoiV1 = \{ nap, moHopThoai, moHoSo, doiChe/.test(js));
assert.ok(/if \(man === 'co-hoi'\) nap\(\)/.test(js), 'mở màn thì nạp');

// 4. Kéo tay không tới `quoted` / `won`; mất phải có lý do; lập báo giá cần tuyến.
{
  const keo = js.slice(js.indexOf('const KEO_DUOC'), js.indexOf('const S = {'));
  assert.ok(!/'quoted'\]/.test(keo.replace(/quoted: \[/, '')) || true);
  assert.ok(!/: \[[^\]]*'quoted'[^\]]*\]/.test(keo), 'không cột nào kéo tới quoted');
  assert.ok(!/: \[[^\]]*'won'[^\]]*\]/.test(keo), 'không cột nào kéo tới won');
  assert.ok(/Đánh mất cơ hội phải ghi lý do/.test(js));
  assert.ok(/Chọn tuyến \(Dữ liệu gốc\) cho cơ hội trước/.test(js));
}

// 5. Lập báo giá → mở thẳng phiếu ở màn Báo giá.
assert.ok(/switchView\('crm-sales', 'qtv2-root'\)/.test(js) && /BaoGiaV2\.moPhieu\(qid\)/.test(js));

// 6. Chữ có dấu (không rơi về không dấu).
assert.ok(/Khách hàng &amp; cơ hội/.test(js) && /Lập báo giá/.test(js));

console.log('khach-hang-va-co-hoi-man-rieng: OK');

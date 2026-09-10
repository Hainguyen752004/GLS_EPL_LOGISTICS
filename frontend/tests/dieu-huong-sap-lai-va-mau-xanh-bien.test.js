/**
 * Sắp lại điều hướng và đổi màu chủ đạo (10/09), theo lời chủ dự án:
 *  · Vận hành theo luồng: DO → Giao hàng & vận chuyển → Điều phối → Theo dõi →
 *    Hoàn tất (Packing list cuối); bỏ "Chuẩn bị nguồn lực"; Trạm kiểm soát AI
 *    sang "Báo cáo và khác".
 *  · Dữ liệu gốc: bảng chọn HAI CỘT mang đủ 12 thẻ (mẫu Golden Enterprise).
 *  · Ẩn dải "Danh mục cấu hình Master Data" và dải gợi ý — chúng ăn chiều cao.
 *  · Màu chủ đạo: xanh nước biển (#2563eb), không còn SAP blue #0a6ed1.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const khungCss = fs.readFileSync(path.join(ROOT, 'css', 'khung-moi.css'), 'utf8');
const khung = fs.readFileSync(path.join(ROOT, 'js', 'khung-moi.js'), 'utf8');
const lang = JSON.parse(fs.readFileSync(path.join(ROOT, 'js', 'lang.json'), 'utf8'));

// Khoanh một bảng chọn: từ id của nó tới bảng chọn kế tiếp (hoặc hết <nav>).
const bang = id => {
  const i = html.indexOf(`id="${id}" role="menu"`);
  const ke = html.indexOf('class="epl-menu', i + 10);
  const het = html.indexOf('</nav>', i);
  return html.slice(i, ke > 0 && ke < het ? ke : het);
};

// 1. Vận hành: đúng thứ tự, không còn Chuẩn bị nguồn lực, không còn AI.
{
  const ops = bang('epl-m-ops');
  const thuTu = [...ops.matchAll(/data-view="([a-z0-9-]+)"/g)].map(m => m[1]);
  assert.deepStrictEqual(thuTu, ['ops-planning', 'delivery-shipment', 'dispatch', 'tracking', 'delivery-completion', 'parking-list']);
  assert.ok(!/CHUẨN BỊ NGUỒN LỰC|khung_hd_ops_res/.test(ops), 'không còn nhóm Chuẩn bị nguồn lực');
  assert.ok(!/data-md-tab=/.test(ops), 'Vận hành không còn trỏ thẻ Dữ liệu gốc');
  assert.ok(/data-view="ai-checkpoint"/.test(bang('epl-m-more')), 'Trạm kiểm soát AI nằm ở Báo cáo và khác');
  assert.ok(/'ai-checkpoint': \['more'/.test(khung), 'đầu trang AI sáng mục Báo cáo và khác');
}

// 2. Dữ liệu gốc: hai cột, đủ 12 thẻ, mỗi thẻ có nút mở thật và khung nội dung.
{
  const md = bang('epl-m-master');
  // thuộc tính class đứng TRƯỚC id nên nằm ngoài lát cắt — kiểm trên cả tệp.
  assert.ok(/class="epl-menu epl-menu-2col" id="epl-m-master"/.test(html), 'bảng chọn hai cột');
  const the = [...md.matchAll(/data-md-tab="([a-z0-9-]+)"/g)].map(m => m[1]);
  assert.strictEqual(the.length, 10, 'phải đủ 10 thẻ (bỏ Thuế, Kỳ kế toán 10/09), thấy ' + the.length);
  assert.strictEqual(new Set(the).size, 10, 'không thẻ nào lặp');
  the.forEach(t => {
    assert.ok(html.includes(`switchMasterDataTab('${t}'`), 'thiếu nút mở thẻ ' + t);
    assert.ok(html.includes(`id="${t}"`), 'thiếu khung nội dung ' + t);
  });
  assert.ok(/\.epl-menu\.epl-menu-2col\.epl-show \{ display: grid; \}/.test(khungCss));
  // nhãn nào có data-i18n đều dịch được ba ngôn ngữ
  [...md.matchAll(/data-i18n="([a-z0-9_]+)"/g)].map(m => m[1]).forEach(k => {
    assert.ok(lang[k] && lang[k].vi && lang[k].en && lang[k].la, 'thiếu bản dịch ' + k);
  });
}

// 3. Hai dải trên màn Dữ liệu gốc đã ẩn (markup giữ để JS và bài kiểm cũ còn đọc).
{
  assert.ok(/id="master-data-left-nav" class="master-data-config-hover" style="display:none"/.test(html), 'dải Danh mục cấu hình phải ẩn');
  assert.ok(/class="md-guide-bar" style="display:none"/.test(html), 'dải gợi ý phải ẩn');
}

// 4. Màu chủ đạo xanh nước biển.
{
  const css = fs.readdirSync(path.join(ROOT, 'css')).filter(f => f.endsWith('.css'))
    .map(f => fs.readFileSync(path.join(ROOT, 'css', f), 'utf8')).join('\n');
  assert.ok(!/#0a6ed1/i.test(css) && !/#0a6ed1/i.test(html), 'không còn SAP blue #0a6ed1');
  assert.ok(/--epl-blue: #2563eb;/.test(khungCss) && /--epl-nav: #0b2e5c;/.test(khungCss), 'token khung đổi sang xanh biển');
}

console.log('dieu-huong-sap-lai-va-mau-xanh-bien: OK');

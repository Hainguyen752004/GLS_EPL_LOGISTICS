/**
 * Theo dõi và kiểm soát: MỘT màn thay ba tab.
 *
 * Màn này trước chia ba không gian, đổi bằng ba thẻ lớn: GPS/POD, Sự cố, Chuỗi
 * sự kiện. Ba thứ đó là ba MẶT của cùng một chuyến — người trực tháp kiểm soát
 * thấy một chuyến đỏ, rồi hỏi "nó đang ở đâu", "đã ký POD chưa", "có sự cố gì".
 * Mỗi câu hỏi là một lần đổi thẻ và mất ngữ cảnh; tệ hơn, chọn DO ở thẻ GPS rồi
 * sang thẻ Sự cố là phải chọn lại.
 *
 * Bản mẫu `tracking-control-tower.html` ghi đúng điều đó ngay trên đầu: "Một
 * màn thay 3 tab: danh sách chuyến đang chạy (trái) · bản đồ (giữa) · hồ sơ
 * chuyến (phải)".
 *
 * Bài kiểm giữ ba chốt, mỗi chốt ứng với một lỗi đã đo được:
 *
 *   1. THẺ ĐÓNG BỊ THIẾU. Markup thiếu một `</div>`, nên Chuỗi sự kiện và Sự cố
 *      là CON của khối GPS/POD chứ không phải khối ngang hàng. Chạy lên vẫn
 *      trông ổn vì bộ máy thẻ dời chúng ra ngoài lúc chạy — nên lỗi này không
 *      bao giờ lộ ra bằng mắt, chỉ lộ khi đếm thẻ.
 *
 *   2. QUY TẮC LƯỚI phải ràng theo `.active` VÀ có `!important`. `switchView`
 *      ghi `sec.style.display` trực tiếp trên thẻ; style nội tuyến thắng mọi
 *      quy tắc lớp, nên không có `!important` thì lưới không bao giờ áp. Nhưng
 *      `!important` một mình lại buộc màn này luôn hiện kể cả khi đã đóng.
 *
 *   3. Màn Theo dõi không còn trong bảng cấu hình thẻ lớn.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const NL = String.fromCharCode(10);
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8')
  .split(String.fromCharCode(13)).join('');
const css = html.replace(/\/\*[\s\S]*?\*\//g, ' ');

// --- 1. Thẻ trong màn Theo dõi phải cân bằng -------------------------

{
  const ds = html.split(NL);
  const n0 = ds.findIndex(d => d.includes('id="view-tracking"'));
  const n1 = ds.findIndex(d => d.includes('id="view-accounting"'));
  assert.ok(n0 > 0 && n1 > n0, 'không khoanh được màn Theo dõi');

  let sau = 0;
  const moc = {};
  for (let n = n0; n < n1; n += 1) {
    const d = ds[n];
    sau += (d.match(/<(div|section|aside|main)\b/g) || []).length
      - (d.match(/<\/(div|section|aside|main)>/g) || []).length;
    ['tracking-gps-pod-workspace', 'tracking-events-workspace',
      'tracking-incident-workspace'].forEach(ma => {
      if (d.includes(`id="${ma}"`)) moc[ma] = sau;
    });
  }
  assert.strictEqual(sau, 0,
    `màn Theo dõi lệch ${sau} thẻ — thiếu thẻ đóng thì các khối lồng vào nhau sai`);

  // Và cả ba khối phải ở CÙNG một độ sâu: chúng là khối ngang hàng, không phải
  // khối lồng nhau. Đây chính là phép kiểm bắt được lỗi thiếu `</div>`.
  const dsSau = Object.values(moc);
  assert.strictEqual(dsSau.length, 3, 'thiếu một trong ba khối của màn Theo dõi');
  assert.strictEqual(new Set(dsSau).size, 1,
    `ba khối phải ngang hàng, đang ở các độ sâu khác nhau: ${JSON.stringify(moc)}`);
}

// --- 2. Lưới: ràng theo .active và có !important ---------------------

{
  assert.ok(/class="view-section tk-board-view"/.test(html),
    'màn Theo dõi phải mang lớp .tk-board-view');

  const i = css.indexOf('.view-section.tk-board-view.active {');
  assert.ok(i > 0,
    'quy tắc lưới phải ràng theo `.view-section.tk-board-view.active` — '
    + 'không ràng theo .active thì !important buộc màn này luôn hiện');
  const luat = css.slice(i, css.indexOf('}', i));
  assert.ok(/display:\s*grid\s*!important/.test(luat),
    'phải có !important: `switchView` ghi display nội tuyến, mà nội tuyến thắng lớp');
  assert.ok(/grid-template-columns:\s*minmax\(0,\s*1fr\)\s+\d+px/.test(luat),
    `lưới phải là một cột linh hoạt cộng một cột hồ sơ cố định: ${luat.trim()}`);

  // Không được có quy tắc `!important` nào KHÔNG ràng theo .active — đó đúng là
  // cái làm màn này không đóng lại được.
  const xau = /\.tk-board-view\s*\{[^}]*display:\s*grid\s*!important/.test(css);
  assert.ok(!xau,
    'có quy tắc display:grid !important không ràng theo .active — màn sẽ không đóng được');

  // Màn hẹp phải về một cột, và cũng phải ràng theo .active cho khớp độ ưu tiên.
  const j = css.indexOf('@media (max-width:1280px)');
  assert.ok(j > 0, 'thiếu quy tắc cho màn hẹp');
  assert.ok(/\.view-section\.tk-board-view\.active\s*\{\s*grid-template-columns:minmax\(0,1fr\)/
    .test(css.slice(j, j + 400)),
    'quy tắc màn hẹp phải ràng theo .active, không thì nó không thắng quy tắc trên');
}

// --- 3. Không còn ba thẻ lớn cho màn Theo dõi -----------------------

{
  assert.ok(!app.includes("sectionId: 'view-tracking'"),
    'bảng cấu hình thẻ lớn còn khai màn Theo dõi');
  assert.ok(!app.includes('tracking-folder-tabs'),
    'còn dấu vết bộ thẻ cũ của màn Theo dõi');
  assert.ok(!html.includes('tracking-folder-tabs'),
    'index.html còn dấu vết bộ thẻ cũ');

  // Ba khối phải CÒN, và mỗi khối đúng một chỗ.
  ['tracking-gps-pod-workspace', 'tracking-events-workspace',
    'tracking-incident-workspace'].forEach(ma => {
    assert.strictEqual((html.match(new RegExp(`id="${ma}"`, 'g')) || []).length, 1,
      `#${ma} phải có đúng một chỗ`);
  });

  // Và bản đồ vẫn phải được nhắc tính lại kích thước khi VÀO MÀN: Leaflet dựng
  // trong lúc màn còn ẩn thì tính sai kích thước. Trước đây việc này nằm ở chỗ
  // mở thẻ GPS; thẻ đã bỏ nên chỗ nhắc phải là lúc vào màn.
  const i = app.indexOf("} else if (targetView === 'tracking') {");
  assert.ok(i > 0, 'không thấy nhánh vào màn Theo dõi trong switchView');
  const nhanh = app.slice(i, i + 500);
  assert.ok(/invalidateSize\(\)/.test(nhanh),
    'vào màn Theo dõi phải nhắc bản đồ tính lại kích thước');
}

console.log('theo-doi-mot-man: thẻ cân bằng, ba khối ngang hàng, lưới ràng theo .active, đã bỏ ba thẻ lớn');

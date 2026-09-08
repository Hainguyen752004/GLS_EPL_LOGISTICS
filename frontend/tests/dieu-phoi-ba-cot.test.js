/**
 * Bàn điều phối ba cột: DO chờ xếp | đội xe hoặc xe ứng viên | ngoại lệ hoặc
 * khung gán.
 *
 * LỖI GỐC mà bài kiểm này sinh ra để chặn. Màn Điều phối ghi ngay trên đầu:
 * "Chọn DO, đối chiếu lịch xe rồi gán nguồn lực NGAY TRÊN MỘT MÀN HÌNH". Đo lại
 * thì câu đó không đúng:
 *
 *   · cột DO để `hidden`, chỉ hiện khi bấm bước 1 — và lúc đó nó bị DỜI vào một
 *     hộp thoại che kín màn;
 *   · danh sách ngoại lệ nằm trong một ngăn kéo phải bấm "Công cụ" mới mở.
 *
 * Nên thực tế màn chỉ hiện một thứ. Người điều phối phải mở hộp thoại để chọn
 * DO, đóng lại để xem lịch, rồi mở tiếp — đúng cái việc mà câu chữ trên đầu nói
 * là không phải làm.
 *
 * Màn nay dựng lại theo bản mẫu `dispatch-v2-crew.html`, ba cột cạnh nhau. Bài
 * kiểm giữ điều đó, và giữ luôn hai hệ quả: ngăn kéo "Công cụ" đã bỏ hẳn, và
 * bước 1 không còn mở hộp thoại.
 *
 * Bài kiểm cũ khoá theo `id` của bản cũ (`#dispatch-queue`, `#dispatch-timeline`,
 * `.dispatch-workbench-grid`). Những `id` đó không còn, nhưng ĐIỀU CẦN BẢO VỆ
 * thì không đổi — nên bài kiểm đổi mốc chứ không bỏ.
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

// Chỉ soi trong phần thân của màn Điều phối, không soi cả tệp: tên lớp của bản
// mẫu (`.card`, `.row`, `.panel`) rất chung, và các màn khác cũng có.
const iMan = html.indexOf('<section id="view-dispatch"');
assert.ok(iMan > 0, 'không thấy màn Điều phối');
const man = html.slice(iMan, html.indexOf('<section id="view-', iMan + 10));

// --- 1. Ba cột đều hiện sẵn, không cột nào bị ẩn ----------------------

{
  const iBan = man.indexOf('<div class="board">');
  assert.ok(iBan > 0, 'không thấy bàn ba cột `.board` của bản mẫu');
  const ban = man.slice(iBan, man.indexOf('id="dispatch-step-modal"') > 0
    ? man.indexOf('id="dispatch-step-modal"') : man.length);

  // Cột 1: DO chờ xếp. Đây là chốt quan trọng nhất — thẻ có `hidden` thì dù bố
  // cục ba cột đúng, cột đó vẫn không có gì trong đó.
  const iDs = ban.indexOf('id="dispatch-do-list"');
  assert.ok(iDs > 0, 'cột 1 phải có chỗ đổ danh sách DO');
  const theDs = ban.slice(ban.lastIndexOf('<', iDs), ban.indexOf('>', iDs) + 1);
  assert.ok(!/\bhidden\b/.test(theDs), `cột DO còn hidden: ${theDs}`);

  // Cột 2: đội xe theo bãi, đổi sang xe ứng viên khi đã chọn DO. Khối đội xe
  // phải hiện sẵn; khối ứng viên thì ẩn cho tới khi có đơn, vì "ứng viên" là
  // ứng viên CHO một đơn cụ thể.
  const iFleet = ban.indexOf('id="dispatch-fleetview"');
  assert.ok(iFleet > 0, 'cột 2 phải có khối đội xe theo bãi');
  const theFleet = ban.slice(ban.lastIndexOf('<', iFleet), ban.indexOf('>', iFleet) + 1);
  assert.ok(!/\bhidden\b/.test(theFleet), 'khối đội xe phải hiện sẵn khi chưa chọn DO');
  const iCand = ban.indexOf('id="dispatch-cand"');
  assert.ok(iCand > 0, 'cột 2 phải có khối xe ứng viên');
  const theCand = ban.slice(ban.lastIndexOf('<', iCand), ban.indexOf('>', iCand) + 1);
  assert.ok(/\bhidden\b/.test(theCand),
    'khối xe ứng viên phải ẩn khi chưa chọn DO — không có đơn thì không có tiêu chí xếp hạng');

  // Cột 3: ngoại lệ, đổi sang khung gán khi đã chọn DO.
  const iExc = ban.indexOf('id="dispatch-exceptions-view"');
  assert.ok(iExc > 0, 'cột 3 phải có danh sách ngoại lệ');
  const theExc = ban.slice(ban.lastIndexOf('<', iExc), ban.indexOf('>', iExc) + 1);
  assert.ok(!/\bhidden\b/.test(theExc), 'danh sách ngoại lệ phải hiện sẵn');
  assert.ok(ban.includes('id="dispatch-calendar-conflicts"'),
    'khối ngoại lệ phải nằm TRONG cột ba, không nằm trong ngăn kéo');

  // Mỗi mốc phải có đúng MỘT chỗ: hai chỗ thì hàm vẽ ghi vào cái nào là chuyện
  // may rủi theo thứ tự trong tài liệu.
  ['dispatch-do-list', 'dispatch-fleetview', 'dispatch-cand',
    'dispatch-exceptions-view', 'dispatch-calendar-conflicts',
    'dispatch-kpis', 'dispatch-detail'].forEach(ma => {
    assert.strictEqual((html.match(new RegExp(`id="${ma}"`, 'g')) || []).length, 1,
      `#${ma} phải có đúng một chỗ`);
  });
}

// --- 2. Lưới chia ba cột, và màn hẹp thì gộp -------------------------

{
  const i = css.indexOf('.dpv2 .board {');
  assert.ok(i > 0, 'thiếu quy tắc lưới ba cột `.dpv2 .board`');
  const luat = css.slice(i, css.indexOf('}', i));
  const cot = luat.match(
    /grid-template-columns:\s*minmax\(([^,]+),\s*([\d.]+)fr\)\s+minmax\(([^,]+),\s*([\d.]+)fr\)\s+(\d+)px/);
  assert.ok(cot,
    `lưới phải chia ba cột (hai cột đầu linh hoạt, cột phải cố định): ${luat.trim()}`);

  // CỘT GIỮA PHẢI RỘNG HƠN CỘT DO.
  //
  // Đây là chỗ đã sai một lần và chủ dự án phải gửi ảnh màn hình để chỉ ra. Bản
  // mẫu cho cột DO 1.15fr và cột lịch xe 1fr, nhưng trên màn thật tỉ lệ đó bóp
  // cột giữa đến mức biển số bị cắt thành "DEMO-51C-1…" và các dòng xe chồng
  // lên nhau. Lý do là cột giữa phải chứa 234px tên xe CỘNG mười bốn ô giờ,
  // còn cột DO chỉ cần đủ đọc bốn mẩu thông tin.
  //
  // Nguyên văn yêu cầu: "cái DO chờ điều phối em làm nó ngắn lại không đc dài
  // ra nữa cho cái ở giữa đc mở ra thêm cho đầy đủ thông tin".
  const doiDO = Number(cot[2]);
  const doiGiua = Number(cot[4]);
  assert.ok(doiGiua > doiDO * 1.5,
    `cột giữa (lịch xe ứng viên) phải rộng hơn cột DO đáng kể — cột giữa còn `
    + `phải chứa tên xe cộng mười bốn ô giờ. Đang là DO ${doiDO}fr / giữa ${doiGiua}fr.`);

  // Và cột DO phải có SÀN, không được co vô hạn: co dưới khoảng 300px thì bốn ô
  // trong dòng DO chồng lên nhau.
  assert.match(cot[1], /\d+px/,
    `cột DO phải có sàn tính bằng px để không co xuống mức không đọc được: ${cot[1]}`);

  // Màn hẹp: ba cột cạnh nhau là không đọc được cột nào. Và cột phải phải xuống
  // DƯỚI, không lên trên — lên trên là lặp lại đúng lỗi che mất lịch xe mà bố
  // cục này sinh ra để sửa.
  const j = css.indexOf('@media (max-width:1400px)');
  assert.ok(j > 0, 'thiếu quy tắc cho màn hẹp');
  const hep = css.slice(j, j + 500);
  assert.ok(/\.dpv2 \.panel\s*\{[^}]*grid-column:1 \/ -1/.test(hep),
    'màn hẹp: cột phải phải trải hết chiều ngang ở hàng dưới');
}

// --- 3. Ngăn kéo "Công cụ" đã bỏ hẳn ---------------------------------

{
  ['dispatch-tools-button', 'dispatch-tools-panel', 'dispatch-tool-drawer',
    'dispatch-tool-pane-alerts', 'dispatch-tool-alerts', 'dispatch-tool-title',
    'openDispatchTool', 'closeDispatchTool', 'toggleDispatchTools'].forEach(dauVet => {
    assert.ok(!html.includes(dauVet), `index.html còn dấu vết ngăn kéo: ${dauVet}`);
    assert.ok(!app.includes(dauVet), `app.js còn dấu vết ngăn kéo: ${dauVet}`);
  });

  // Nhưng chỗ chứa số liệu phải CÒN: các hàm khác ghi vào đó rồi khối khác đọc
  // ra. Bỏ nó là chúng lặng lẽ không ghi được gì.
  assert.ok(/class="dispatch-resource-data"/.test(html),
    'chỗ chứa số liệu điều phối phải còn');
  ['dispatch-veh-ready-count', 'dispatch-veh-busy-count',
    'dispatch-driver-ready-count'].forEach(ma => {
    assert.ok(html.includes(`id="${ma}"`), `mất chỗ chứa số liệu #${ma}`);
  });

  // Phần trình bày của ngăn kéo cũng phải dọn — quy tắc cho thẻ không tồn tại
  // là chỗ để người sau tưởng thẻ đó còn.
  ['.dispatch-tools-wrap', '.dispatch-tools-panel', '.dispatch-tool-drawer'].forEach(lop => {
    assert.ok(!css.includes(lop + ' ') && !css.includes(lop + '{')
      && !css.includes(lop + ' {'),
      `còn quy tắc trình bày cho ${lop}`);
  });
}

// --- 4. Bước 1 không mở hộp thoại nữa --------------------------------

{
  const i = app.indexOf('window.openDispatchStepModal = function (step) {');
  assert.ok(i > 0, 'không thấy openDispatchStepModal');
  const dau = app.slice(i, i + 900);
  assert.ok(/step === 'do'/.test(dau),
    'bước 1 phải được chặn ở ĐẦU hàm, trước khi tới phần mở hộp thoại');
  assert.ok(/dispatch-do-search-input/.test(dau),
    'bước 1 phải đưa con trỏ vào ô tìm của cột DO');

  // Và bảng cấu hình hộp thoại không được còn khai bước 'do' — khai thì một
  // đường khác gọi vào là lại dời cột đang hiện vào hộp thoại.
  const j = app.indexOf('const dispatchStepModalConfig = {');
  const bang = app.slice(j, app.indexOf(NL + '};', j));
  assert.ok(!/^\s*do:\s*\{/m.test(bang),
    'bảng cấu hình hộp thoại không được còn khai bước "do"');
  // Ba bước còn lại thì phải còn: chúng là hộp thoại thật.
  ['trip', 'schedule', 'resources'].forEach(b => {
    assert.ok(new RegExp(`\\b${b}:\\s*\\{`).test(bang), `mất khai bước "${b}"`);
  });
}

// --- 5. CSS của bản mẫu phải nằm TRONG phạm vi `.dpv2` ---------------

{
  // Bản mẫu dùng những tên lớp rất chung — `.card`, `.row`, `.tag`, `.panel`,
  // `.search` — mà ứng dụng cũng đã có. Không bọc phạm vi thì bản mẫu ghi đè
  // lên mọi màn khác, và ta chữa một màn để làm hỏng mười màn.
  ['card', 'row', 'tag', 'panel', 'search', 'kpi', 'grp', 'team', 'crew',
    'lane', 'veh', 'seg'].forEach(lop => {
    const re = new RegExp('(^|[},])\\s*\\.' + lop + '[\\s,{]', 'm');
    const viPham = re.exec(css);
    assert.ok(!viPham,
      `quy tắc \`.${lop}\` để trần, phải bọc trong \`.dpv2\`: ${viPham && viPham[0]}`);
  });
}

/**
 * Màn "Sắp lịch xe và tài xế": hai cột, lọc nhanh, và nhắc bảo dưỡng chưa duyệt.
 *
 * Ba thứ bài kiểm này giữ, mỗi thứ ứng với một lỗi đã đo được:
 *
 *   1. HAI CỘT. Bản cũ xếp dọc — dải độ phủ, danh sách "cần xếp", rồi mới tới
 *      ma trận. Đo trên màn 1600×1200 thì ma trận bắt đầu ở khoảng 1000px: người
 *      xếp ca mở màn ra là KHÔNG thấy cái bảng mình phải làm việc trên đó. Cả
 *      hai tab (Nhân sự và Xe) phải cùng bố cục, không thì đổi tab là phải học
 *      lại chỗ nhìn.
 *
 *   2. LỌC NHANH có định nghĩa ĐO ĐƯỢC. "Vượt giờ" phải nói rõ là trên bao
 *      nhiêu giờ, và phải tính từ giờ gốc trong `driverShifts` chứ không từ nhãn
 *      giờ đã định dạng — cộng chuỗi "06:00" thì ra rác.
 *
 *   3. Nhắc BẢO DƯỠNG CHƯA DUYỆT. `vehicle-availability` cố ý chỉ trả kỳ đã
 *      duyệt, vì chỉ kỳ đã duyệt mới chặn điều phối. Nhưng như vậy kỳ mới xin
 *      là vô hình, và người xếp lịch xếp chuyến vào đúng ngày thợ đã xin xe.
 *      Khối nhắc phải nói rõ nó CHƯA chặn gì — không thì người đọc tưởng xe đã
 *      nằm bãi và bỏ trống cả tuần.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const NL = String.fromCharCode(10);
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8')
  .split(String.fromCharCode(13)).join('');
const roster = fs.readFileSync(path.join(ROOT, 'js', 'driver-roster.js'), 'utf8')
  .split(String.fromCharCode(13)).join('');
const css = fs.readFileSync(path.join(ROOT, 'css', 'driver-roster.css'), 'utf8');

/** Bỏ chú thích trước khi dò, để không bắt vào chính lời giải thích. */
function boChuThich(ma) {
  return ma
    .replace(/\/\*[\s\S]*?\*\//g, ' ')
    .split(NL).map(d => d.replace(/^\s*\/\/.*$/, '')).join(NL);
}

const appMa = boChuThich(app);
const cssMa = css.replace(/\/\*[\s\S]*?\*\//g, ' ');

// --- 1. Tên màn đã đổi ở CẢ BA tầng nhãn -----------------------------

{
  // Nhãn cũ "Quản Lý Tài Xế & Sắp Ca" và "Xe và thiết bị" đều sai: thẻ này
  // không chứa danh mục xe (danh mục nằm ở md-tab-veh-types).
  const lang = JSON.parse(fs.readFileSync(path.join(ROOT, 'js', 'lang.json'), 'utf8'));
  // Hai khóa nhãn: nhãn thẻ trong dải Dữ liệu gốc, và mục trong dải điều hướng.
  // Tiêu đề bên trong màn thì KHÔNG còn khóa nào — nó đã bỏ, vì tầng 3 nói đúng
  // câu đó rồi và để cả hai thì cùng một câu hiện hai lần cách nhau 80px.
  const KHOA_TEN = ['tab_md_drivers', 'khung_mi_vehicles'];
  KHOA_TEN.forEach(khoa => {
    assert.ok(lang[khoa], `thiếu khóa ${khoa}`);
    assert.ok(/Sắp lịch xe và tài xế/i.test(lang[khoa].vi),
      `khóa ${khoa} còn tên cũ: "${lang[khoa].vi}"`);
    ['en', 'la'].forEach(ng => {
      assert.ok(lang[khoa][ng] && lang[khoa][ng].trim(),
        `khóa ${khoa} thiếu bản dịch ${ng}`);
    });
  });
  ['title_driver_shift_mgmt', 'desc_driver_shift_mgmt'].forEach(khoa => {
    assert.ok(!lang[khoa], `lang.json còn khóa chết "${khoa}" — tiêu đề trong màn đã bỏ`);
    assert.ok(!html.includes(khoa), `index.html còn dùng khóa đã bỏ "${khoa}"`);
  });
  assert.ok(!/Xe và thiết bị/.test(html), 'index.html còn nhãn "Xe và thiết bị"');
  assert.ok(!/Quản lý tài xế, phụ xe/.test(html), 'index.html còn tiêu đề cũ');

  // Và `forceCriticalVietnameseLabels` không được ghi đè — nó chạy SAU
  // changeLanguage nên nó luôn thắng.
  const i = app.indexOf('function forceCriticalVietnameseLabels()');
  const than = app.slice(i, app.indexOf(NL + '}', i));
  KHOA_TEN.forEach(khoa => {
    assert.ok(!than.includes(khoa), `forceCriticalVietnameseLabels còn ghi đè ${khoa}`);
  });
}

// --- 2. Mục nằm trong nhóm Vận hành, không nằm ở Dữ liệu gốc ---------

{
  // Xếp ca là việc làm hằng tuần, không phải dữ liệu gốc "khai một lần rồi để
  // đó". Để chung thì người điều phối phải vào "Dữ liệu gốc" để làm một việc
  // vận hành.
  const iOps = html.indexOf('id="epl-m-ops"');
  const iBiz = html.indexOf('id="epl-m-biz"');
  const iMuc = html.indexOf('data-md-tab="md-tab-vehicles"');
  assert.ok(iOps > 0 && iBiz > iOps, 'không khoanh được bảng chọn Vận hành');
  assert.ok(iMuc > iOps && iMuc < iBiz,
    'mục "Sắp lịch xe và tài xế" phải nằm trong bảng chọn Vận hành');
  assert.strictEqual((html.match(/data-md-tab="md-tab-vehicles"/g) || []).length, 1,
    'mục bị nhân đôi ở hai bảng chọn');

  // Và đầu trang phải khai riêng cho thẻ này, không thì đi vào từ Vận hành mà
  // đường dẫn lại ghi "Dữ liệu gốc".
  const khung = fs.readFileSync(path.join(ROOT, 'js', 'khung-moi.js'), 'utf8');
  const i = khung.indexOf('const DAU_TRANG_THEO_THE = {');
  assert.ok(i > 0, 'thiếu bảng đầu trang theo thẻ');
  const bang = new Function(
    khung.slice(i, khung.indexOf(NL + '  };', i) + 5) + NL + 'return DAU_TRANG_THEO_THE;')();
  const d = bang['md-tab-vehicles'];
  assert.ok(d, 'thẻ md-tab-vehicles chưa khai đầu trang riêng');
  assert.strictEqual(d[0], 'ops', 'thẻ xếp ca phải sáng mục Vận hành ở tầng 2');
  assert.strictEqual(d[1], 'Vận hành', `đường dẫn phải là "Vận hành", thấy "${d[1]}"`);
}

// --- 3. Hai cột, cả hai tab -------------------------------------------

{
  assert.ok(/\.dr-shell\s*\{[^}]*grid-template-areas/.test(cssMa),
    '.dr-shell phải là bố cục hai cột (grid-template-areas)');
  ['cover', 'main', 'side'].forEach(vung => {
    assert.ok(new RegExp(`\\.dr-${vung === 'cover' ? 'cover-slot' : vung}\\s*\\{`).test(cssMa),
      `thiếu quy tắc cho vùng .dr-${vung}`);
  });
  // Màn hẹp phải về MỘT cột, và danh sách thiếu xuống DƯỚI lưới — lên trên là
  // lặp lại đúng lỗi che mất lưới mà bố cục này sinh ra để sửa.
  const hep = cssMa.slice(cssMa.indexOf('@media (max-width: 1280px)'));
  assert.ok(/"cover"\s*"main"\s*"side"/.test(hep),
    'màn hẹp phải xếp cover → main → side, không được đưa side lên trước main');

  // Cả hai tab dùng cùng bố cục.
  ['renderDriverShiftCalendarTable', 'renderDriverVehicleWeek'].forEach(ham => {
    const i = appMa.indexOf(`function ${ham}()`);
    assert.ok(i > 0, `không thấy ${ham}`);
    const than = appMa.slice(i, i + 6000);
    assert.ok(than.includes('dr-cover-slot'), `${ham} chưa dùng vùng .dr-cover-slot`);
    assert.ok(than.includes('class="dr-main"'), `${ham} chưa dùng vùng .dr-main`);
    assert.ok(than.includes('class="dr-side"'), `${ham} chưa dùng vùng .dr-side`);
  });

  // Danh sách việc cần xử lý phải nằm TRONG cột phải, không còn ở trên lưới.
  const iCa = appMa.indexOf('function renderDriverShiftCalendarTable()');
  const thanCa = appMa.slice(iCa, iCa + 6000);
  const iSide = thanCa.indexOf('class="dr-side"');
  const iGap = thanCa.indexOf('crewGapList');
  assert.ok(iGap > iSide,
    'danh sách "cần xếp" phải nằm trong cột phải, không nằm trên lưới');
}

// --- 4. Lọc nhanh: định nghĩa đo được, và tính từ giờ gốc -------------

{
  assert.ok(/function filterChips\(/.test(roster), 'thiếu bộ dựng dải lọc nhanh');
  const i = roster.indexOf('function filterChips(');
  const than = roster.slice(i, roster.indexOf(NL + '  }', i));
  ['all', 'need', 'over', 'leave'].forEach(ma => {
    assert.ok(than.includes(`'${ma}'`), `dải lọc thiếu nhóm "${ma}"`);
  });
  // Mỗi nhóm phải có một câu nói ĐỊNH NGHĨA, không để người dùng đoán.
  assert.ok(/48 giờ/.test(than), 'nhóm "vượt giờ" không nói rõ ngưỡng là bao nhiêu giờ');
  assert.ok(/không có ca nào/.test(than), 'nhóm "chưa xếp" không nói rõ định nghĩa');
  // Nhóm rỗng phải mờ chứ không ẩn — ẩn thì dải nút nhảy chỗ mỗi lần đổi tuần.
  assert.ok(/is-empty/.test(than) && /disabled/.test(than),
    'nhóm rỗng phải mờ và không bấm được, chứ không ẩn hẳn');

  // Giờ phải tính từ `driverShifts` gốc. Nhãn giờ trong `data.people` là chuỗi
  // "06:00" để hiện ra — cộng chuỗi thì ra rác.
  const j = appMa.indexOf('function gioLamTrongTuan(');
  assert.ok(j > 0, 'thiếu hàm tính giờ làm trong tuần');
  const thanGio = appMa.slice(j, appMa.indexOf(NL + '}', j));
  assert.ok(/driverShifts/.test(thanGio), 'phải tính từ driverShifts gốc');
  assert.ok(/shift_start/.test(thanGio) && /shift_end/.test(thanGio),
    'phải đọc giờ gốc shift_start / shift_end');
  assert.ok(/start_label|end_label/.test(thanGio) === false,
    'không được cộng nhãn giờ đã định dạng');
  // Chỉ ca làm việc mới tính giờ — một ngày nghỉ phép không phải giờ làm.
  assert.ok(/availability_kind/.test(thanGio),
    'phải bỏ qua ngày nghỉ khi tính giờ làm');

  // Đổi nhóm phải đặt lại số dòng đang hiện — giữ nguyên thì đổi từ nhóm 200
  // người sang nhóm 3 người mà vẫn còn nút "xem thêm".
  const k = appMa.indexOf('window.setDriverShiftChip =');
  assert.ok(k > 0, 'thiếu hàm đổi nhóm lọc');
  const thanChip = appMa.slice(k, appMa.indexOf(NL + '};', k));
  assert.ok(/driverShiftVisibleCount\s*=/.test(thanChip),
    'đổi nhóm phải đặt lại số dòng đang hiện');

  // Biến trạng thái phải được KHAI, không chỉ gán — gán mà không khai thì lần
  // đọc đầu tiên là ReferenceError và cả hàm vẽ dừng giữa.
  assert.ok(/^let driverShiftChip = /m.test(appMa),
    'driverShiftChip phải được khai bằng let ở cấp cao nhất');
}

// --- 5. Nhắc bảo dưỡng chưa duyệt -------------------------------------

{
  const i = appMa.indexOf('function khoiBaoDuongChuaDuyet()');
  assert.ok(i > 0, 'thiếu khối nhắc bảo dưỡng chưa duyệt');
  const than = appMa.slice(i, appMa.indexOf(NL + '}', i));
  assert.ok(/requested/.test(than),
    'chỉ nhắc kỳ ở trạng thái requested — kỳ đã duyệt đã hiện trên lưới rồi');
  // Phải nói rõ nó CHƯA chặn gì, không thì người đọc tưởng xe đã nằm bãi.
  assert.ok(/chưa<\/strong> chặn|chưa chặn/.test(than),
    'phải nói rõ kỳ chưa duyệt CHƯA chặn điều phối');

  // Lấy bằng MỘT lời gọi cho cả tuần. Đường theo từng xe không dùng được ở quy
  // mô ~500 xe.
  assert.ok(/\/api\/vehicle-maintenance-requests\?/.test(appMa),
    'phải gọi đường bảo dưỡng theo khoảng thời gian');
  assert.ok(!/vehicles\/\$\{[^}]*\}\/maintenance-requests/.test(
    appMa.slice(appMa.indexOf('window.loadDriverShiftPlanner'),
      appMa.indexOf('window.moveDriverShiftWeek'))),
    'không được gọi đường bảo dưỡng theo từng xe trong vòng lặp');

  // Biến chứa dữ liệu phải được khai.
  assert.ok(/^let driverVehicleMaintenance = /m.test(appMa),
    'driverVehicleMaintenance phải được khai bằng let ở cấp cao nhất');

  // Màu: kỳ chưa duyệt KHÔNG được dùng đỏ — nó chưa chặn gì, dùng đỏ là nói quá
  // và làm loãng màu đỏ của những việc chặn thật.
  const iCss = cssMa.indexOf('.dr-mt-pending {');
  assert.ok(iCss > 0, 'thiếu phần trình bày cho khối nhắc bảo dưỡng');
  const luat = cssMa.slice(iCss, cssMa.indexOf('}', iCss));
  assert.ok(!/#d32f2f|#b3261e|\bred\b/i.test(luat),
    'khối nhắc bảo dưỡng chưa duyệt không được dùng màu đỏ');
}

console.log('sap-lich-xe-tai-xe: đã đổi tên, hai cột cả hai tab, lọc nhanh có định nghĩa, nhắc bảo dưỡng chưa duyệt');

/**
 * `renderDispatchWeekPlanner` CHƯA được bật, và đó là quyết định có chủ đích.
 *
 * Hàm này vẽ vào ba khối `dispatch-week-planner-kpis`, `-grid`, `-guidance`
 * mà index.html không có, nên nó thoát ngay ở `if (!kpisEl || !gridEl ||
 * !guidanceEl) return;`. Nhìn qua thì đây là "mã chết, xóa đi" — nhưng
 * `dispatch-workbench-ui.test.js` khóa mười ba lớp CSS nằm trong chính thân
 * hàm này (`dispatch-week-pane-schedule`, `dispatch-week-cell`,
 * `dispatch-free-day`, …), tức nó là tính năng có chủ đích chứ không phải rác.
 *
 * Nhưng CHỈ thêm ba khối chứa vào index.html là sai. `buildDispatchWeekPlanner`
 * trả về `vehicle_rows` KHÔNG giới hạn — một dòng cho mỗi xe — rồi trình vẽ
 * nhân với bảy ngày. Đo thật bằng đúng khuôn dòng của thân hàm:
 *
 *       3 xe  ->  0,01 MB HTML,    21 nút
 *      50 xe  ->  0,11 MB HTML,   350 nút
 *     200 xe  ->  0,43 MB HTML, 1.400 nút
 *     500 xe  ->  1,06 MB HTML, 3.500 nút   <-- quy mô vận hành thật
 *
 * Đội xe thật khoảng 500 chiếc, nên bật nguyên trạng là dựng 1 MB HTML và
 * 3.500 nút bấm trong MỘT lần `innerHTML`, mỗi lần đổi tuần lại dựng lại toàn
 * bộ. Đúng cái đã phải sửa một lần ở màn lịch xe.
 *
 * Muốn bật thì phải đổi cách hiển thị trước: mặc định chỉ hiện các trường hợp
 * cần xử lý (trùng lịch, sắp bảo dưỡng) cộng băng năng lực theo ngày, rồi mới
 * lọc xuống từng xe — chứ không liệt kê hết.
 *
 * Bài kiểm này giữ hai điều: hàm còn đó, và ba khối chứa vẫn CHƯA được thêm.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const utils = fs.readFileSync(path.join(ROOT, 'js', 'tms-cockpit-utils.js'), 'utf8');

assert.ok(/function renderDispatchWeekPlanner\(\)/.test(app),
  'đừng gỡ hàm này — dispatch-workbench-ui.test.js khóa các lớp CSS trong thân nó');

const KHOI = ['dispatch-week-planner-kpis', 'dispatch-week-planner-grid',
  'dispatch-week-planner-guidance'];

// Nếu ai thêm ba khối này, họ phải xử lý chuyện 500 xe trước.
const daThem = KHOI.filter(id => html.includes(`id="${id}"`));
if (daThem.length) {
  // Dấu hiệu "đã chặn" phải nằm ĐÚNG ở chỗ dựng `vehicle_rows`, và chỉ ở đó.
  //
  // Hai phép dò trước đều vô dụng, vì cả hai đều đã đúng sẵn khi chưa ai chặn
  // gì: `/\.slice\(0, \d+\)/` khớp 24 chỗ khác trong tms-cockpit-utils.js, còn
  // `dispatch-week-more` là một quy tắc CSS còn sót trong index.html. Một chốt
  // an toàn mà đã xanh từ đầu thì không phải chốt.
  //
  // Cách làm cho bài kiểm này xanh là ĐỔI CÁCH DỰNG `vehicle_rows` — giới hạn
  // số dòng, phân trang, hoặc chỉ trả về những xe cần xử lý — rồi cập nhật
  // phép đo ở đầu tệp này.
  const daChan = !/vehicle_rows: vehicleRows,/.test(utils);
  assert.ok(daChan,
    `đã thêm ${daThem.join(', ')} nhưng vehicle_rows vẫn dựng một dòng cho MỖI`
    + ' xe: ở 500 xe đây là 1 MB HTML và 3.500 nút trong một lần innerHTML,'
    + ' dựng lại toàn bộ mỗi lần đổi tuần.');
}

// Và con số đo được phải còn đúng: nếu ai cắt bớt khuôn dòng thì phép đo trên
// hết giá trị, nên neo vào những lớp CSS làm nên độ nặng đó.
['dispatch-week-row', 'dispatch-week-cell', 'dispatch-free-day', 'dispatch-week-vehicle']
  .forEach(lop => assert.ok(app.includes(lop), `thân hàm phải còn lớp ${lop}`));

// `vehicle_rows` chưa bị giới hạn — ghi nhận hiện trạng để lần sau đổi thì
// bài kiểm này buộc phải đọc lại.
assert.ok(/vehicle_rows: vehicleRows,/.test(utils),
  'vehicle_rows đã đổi cách dựng — hãy đo lại rồi cập nhật bài kiểm này');

console.log('dispatch-week-planner-chua-bat: tất cả kiểm tra đã qua');

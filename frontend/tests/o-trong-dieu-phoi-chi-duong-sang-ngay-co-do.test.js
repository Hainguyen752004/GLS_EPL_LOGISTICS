/**
 * Ô trống của cột "DO chờ điều phối" phải CHỈ ĐƯỜNG sang ngày có việc.
 *
 * VÌ SAO CÓ BÀI NÀY. Màn điều phối lọc theo một ngày. Ngày 11/09 hết đơn chờ, và màn chỉ nói
 * "Chưa có lệnh giao hàng sẵn sàng điều phối ngày 2026-09-11" rồi im — trong khi hệ vẫn còn
 * 13 đơn đang chờ ở các ngày 12/09 đến 18/09. Chủ dự án mở màn lên và hỏi thẳng *"sao cái
 * trang điều phối này nó không nhận dữ liệu DO nữa rùi nè"*. Một ngày rỗng trông y hệt một
 * hệ thống hỏng, nên ô trống phải tự nói ra việc đang nằm ở đâu.
 *
 * Bốn điều khoá, CHẠY THẬT hàm chứ không quét chữ:
 * 1. Đếm đúng tổng số đơn chờ ở những ngày KHÁC ngày đang xem (không tính ngày đang xem).
 * 2. "Gần nhất" là ngày về SAU gần nhất — không phải ngày nhỏ nhất trong danh sách.
 * 3. Đơn ở ngày ĐÃ QUA là TỒN ĐỌNG, phải tách riêng: nó gấp hơn việc của ngày mai, mà gộp
 *    chung vào một con số "ngày gần nhất" thì nó biến mất.
 * 4. Đơn thiếu ngày lấy hàng không được đếm vào đây — đã có cảnh báo riêng cho chúng.
 */
const assert = require('assert');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const { ngayGanNhatCoDonCho } = require(path.join(ROOT, 'js', 'tms-cockpit-utils.js'));

assert.strictEqual(typeof ngayGanNhatCoDonCho, 'function',
  'tms-cockpit-utils.js chưa xuất ngayGanNhatCoDonCho');

const don = (id, ngay) => ({ id, pickup_window_start: ngay ? ngay + 'T08:00:00+07:00' : null });

// Dựng đúng hình dạng dữ liệu thật đo được ngày 11/09: 13 đơn chờ, không đơn nào của hôm nay.
const thuc = [
  don('DO-31', '2026-09-12'),
  don('DO-01', '2026-09-13'),
  don('DO-32', '2026-09-14'), don('DO-35', '2026-09-14'),
  don('DO-04', '2026-09-15'), don('DO-33', '2026-09-15'),
  don('DO-36', '2026-09-16'), don('DO-40', '2026-09-16'), don('DO-34', '2026-09-16'),
  don('DO-37', '2026-09-17'),
  don('DO-38', '2026-09-18'), don('DO-41', '2026-09-18'), don('DO-39', '2026-09-18'),
];

// 1. Đứng ở 11/09: 13 đơn ở ngày khác, ngày gần nhất về sau là 12/09 với 1 đơn, không tồn đọng.
let kq = ngayGanNhatCoDonCho(thuc, '2026-09-11');
assert.strictEqual(kq.tong, 13, 'tổng đơn chờ ở ngày khác phải là 13');
assert.deepStrictEqual({ iso: kq.sau.iso, so: kq.sau.so, cach: kq.sau.cach_ngay },
  { iso: '2026-09-12', so: 1, cach: 1 });
assert.strictEqual(kq.truoc, null, 'ngày 11/09 không có tồn đọng nào phía trước');

// 2. Đứng ở 15/09 (ngày CÓ đơn): ngày đang xem không được tự đếm vào "ngày khác".
kq = ngayGanNhatCoDonCho(thuc, '2026-09-15');
assert.strictEqual(kq.tong, 11, '2 đơn của chính ngày 15/09 phải bị loại khỏi phép đếm');
assert.strictEqual(kq.sau.iso, '2026-09-16', 'gần nhất về sau phải là 16/09');
assert.strictEqual(kq.sau.so, 3);
// Tồn đọng phải là ngày ĐÃ QUA GẦN NHẤT (14/09), không phải ngày xa nhất (12/09).
assert.strictEqual(kq.truoc.iso, '2026-09-14', 'tồn đọng phải lấy ngày đã qua GẦN nhất');
assert.strictEqual(kq.truoc.so, 2);
assert.strictEqual(kq.truoc.cach_ngay, -1);

// 3. Đứng ở 20/09, sau tất cả: chỉ còn tồn đọng, không còn gì phía trước.
kq = ngayGanNhatCoDonCho(thuc, '2026-09-20');
assert.strictEqual(kq.sau, null, 'không còn ngày nào về sau');
assert.strictEqual(kq.truoc.iso, '2026-09-18');
assert.strictEqual(kq.truoc.so, 3);
assert.strictEqual(kq.tong, 13);

// 4. Đơn thiếu ngày lấy hàng KHÔNG được đếm — chúng đã có dải cảnh báo riêng, đếm thêm ở đây
//    là nói với người trực rằng có việc ở một ngày nào đó mà bấm sang sẽ chẳng thấy gì.
kq = ngayGanNhatCoDonCho([don('DO-X', null), don('DO-Y', null), don('DO-31', '2026-09-12')],
  '2026-09-11');
assert.strictEqual(kq.tong, 1, 'đơn thiếu ngày không được cộng vào tổng');
assert.strictEqual(kq.sau.iso, '2026-09-12');

// 5. Không còn đơn chờ nào ở ngày khác → không vẽ gì, khỏi thêm nhiễu vào ô trống.
kq = ngayGanNhatCoDonCho([], '2026-09-11');
assert.deepStrictEqual(kq, { sau: null, truoc: null, tong: 0 });
kq = ngayGanNhatCoDonCho([don('DO-31', '2026-09-11')], '2026-09-11');
assert.strictEqual(kq.tong, 0, 'chỉ có đơn của chính ngày đang xem thì coi như không có');

// 6. Nhận cả `pickup_date` và `planned_pickup_at` — ba tên trường cùng nghĩa trong hệ.
kq = ngayGanNhatCoDonCho([
  { id: 'A', pickup_date: '2026-09-13T08:00:00+07:00' },
  { id: 'B', planned_pickup_at: '2026-09-13T09:00:00+07:00' },
], '2026-09-11');
assert.strictEqual(kq.tong, 2);
assert.strictEqual(kq.sau.iso, '2026-09-13');

console.log('o-trong-dieu-phoi-chi-duong-sang-ngay-co-do: OK');

/**
 * Phân loại Lệnh giao hàng (DO).
 *
 * Ba vấn đề của màn cũ, tìm được khi đối chiếu với dữ liệu thật trong Postgres:
 *
 *   1. Tab mặc định là "Gần trễ" và nó đang có **0 DO**, nên mở màn ra là bảng
 *      trống trong khi 9 DO thật nằm ở các tab khác.
 *   2. "Gần trễ" gộp *sắp tới hạn* với *đã quá hạn*. Một DO quá hạn ba tuần và
 *      một DO tới hạn chiều nay là hai mức cấp bách khác nhau.
 *   3. Ba DO "Chờ vận chuyển" **không có ngày nào cả** — pickup_window_start,
 *      pickup_date, delivery_date đều rỗng. Màn cũ lấy `created_at` làm hạn
 *      giao thay thế, tức bịa ra một hạn không tồn tại: ngày tạo phiếu không
 *      phải ngày phải giao.
 */
const assert = require('assert');
const path = require('path');

const B = require(path.join(__dirname, '..', 'js', 'do-board.js'));

const NOW = Date.parse('2026-09-05T10:00:00Z');

// --- 1. Không được bịa ra hạn giao ----------------------------------------

// Đúng hình dạng của ba DO thật trong cơ sở dữ liệu: chỉ có created_at.
const UNDATED = { id: 'D-UNDATED', status: 'Chờ vận chuyển', created_at: '2026-08-11T10:37:02' };

assert.strictEqual(B.dueAt(UNDATED), null, 'ngày tạo phiếu KHÔNG phải hạn giao');
assert.strictEqual(B.bucketOf(UNDATED, NOW), 'undated');
assert.strictEqual(B.daysLate(UNDATED, NOW), null, 'không có hạn thì không có số ngày trễ');

// Và nó phải là một rổ RIÊNG, không trộn vào "chờ vận chuyển": DO không có ngày
// thì không lập kế hoạch được và cũng không đo trễ được.
assert.notStrictEqual(B.bucketOf(UNDATED, NOW), 'pending');

// --- 2. Tách quá hạn khỏi sắp tới hạn ------------------------------------

const OVERDUE = { id: 'D-OVERDUE', status: 'Chờ vận chuyển', delivery_window_end: '2026-08-20T00:00:00Z' };
const DUE_SOON = { id: 'D-SOON', status: 'Chờ vận chuyển', delivery_window_end: '2026-09-05T20:00:00Z' };
const PENDING = { id: 'D-PENDING', status: 'Chờ vận chuyển', delivery_window_end: '2026-09-30T00:00:00Z' };

assert.strictEqual(B.bucketOf(OVERDUE, NOW), 'overdue');
assert.strictEqual(B.bucketOf(DUE_SOON, NOW), 'near_late');
assert.strictEqual(B.bucketOf(PENDING, NOW), 'pending');
assert.strictEqual(B.daysLate(OVERDUE, NOW), 16, 'phải nói rõ quá hạn bao nhiêu ngày');

// Đúng mốc 24 giờ: trong 24h là sắp tới hạn, quá 24h là còn thời gian.
assert.strictEqual(B.bucketOf({ status: 'pending', delivery_date: '2026-09-06T09:00:00Z' }, NOW), 'near_late');
assert.strictEqual(B.bucketOf({ status: 'pending', delivery_date: '2026-09-06T11:00:00Z' }, NOW), 'pending');

// --- 3. Trạng thái vận hành thắng hạn giao -------------------------------
//
// Xe đã lên đường thì hạn giao không còn quyết định rổ nữa.
assert.strictEqual(B.bucketOf({ status: 'Đang vận chuyển', delivery_date: '2026-08-01' }, NOW), 'active');
assert.strictEqual(B.bucketOf({ status: 'Đã giao', delivery_date: '2026-08-01' }, NOW), 'completed');
assert.strictEqual(B.bucketOf({ status: 'Gặp sự cố', delivery_date: '2026-12-01' }, NOW), 'incident');
// Nhận cả tiếng Anh lẫn tiếng Việt, có dấu hay không.
['in_transit', 'In Transit', 'dispatched', 'dang van chuyen'].forEach(status => {
  assert.strictEqual(B.bucketOf({ status }, NOW), 'active', `phải nhận trạng thái "${status}"`);
});
assert.strictEqual(B.bucketOf({ canonical_status: 'delivered' }, NOW), 'completed');

// --- 4. Tab mở sẵn phải là rổ CẤP BÁCH NHẤT MÀ CÓ DÒNG -------------------

{
  // Đúng tình huống đang gặp: không có DO quá hạn nào, nhưng có DO thiếu hạn.
  const real = [UNDATED, UNDATED, UNDATED,
    { status: 'Đang vận chuyển' }, { status: 'Đang vận chuyển' }, { status: 'Đang vận chuyển' },
    { status: 'Đã giao' }, { status: 'Đã giao' }, { status: 'Đã giao' }];
  const tally = B.counts(real, NOW);
  assert.strictEqual(tally.undated, 3);
  assert.strictEqual(tally.active, 3);
  assert.strictEqual(tally.completed, 3);
  assert.strictEqual(tally.overdue, 0);
  // KHÔNG được mở một rổ rỗng.
  assert.strictEqual(B.defaultBucket(real, NOW), 'undated');
  assert.ok(tally[B.defaultBucket(real, NOW)] > 0, 'rổ mở sẵn luôn phải có dòng');
}

{
  // Có sự cố thì sự cố lên trước tất cả.
  const withIncident = [OVERDUE, UNDATED, { status: 'Gặp sự cố' }];
  assert.strictEqual(B.defaultBucket(withIncident, NOW), 'incident');
}

// Không có DO nào thì vẫn phải có một rổ được chọn, không để màn hình không tab.
assert.ok(B.BUCKETS.some(bucket => bucket.key === B.defaultBucket([], NOW)));

// Mọi rổ đều xuất hiện trong bảng đếm, kể cả rổ rỗng — nếu không thẻ sẽ biến mất.
{
  const tally = B.counts([], NOW);
  assert.deepStrictEqual(Object.keys(tally).sort(), B.BUCKETS.map(b => b.key).sort());
  assert.ok(Object.values(tally).every(value => value === 0));
}

// --- 5. Rổ xếp theo mức cấp bách giảm dần -------------------------------

{
  const order = B.BUCKETS.map(bucket => bucket.key);
  assert.ok(order.indexOf('incident') < order.indexOf('overdue'));
  assert.ok(order.indexOf('overdue') < order.indexOf('undated'));
  assert.ok(order.indexOf('undated') < order.indexOf('near_late'));
  assert.ok(order.indexOf('near_late') < order.indexOf('pending'));
  assert.ok(order.indexOf('pending') < order.indexOf('completed'));
}

// --- 6. Xếp trong một rổ: việc gấp nhất lên trước -----------------------

{
  const late = [
    { id: 'A', status: 'pending', delivery_date: '2026-09-01' },
    { id: 'B', status: 'pending', delivery_date: '2026-07-01' },
    { id: 'C', status: 'pending', delivery_date: '2026-08-15' },
  ];
  // Luon TANG DAN theo han giao, vi ca hai nghia deu tro toi han nho nhat:
  // "qua han lau nhat" la han cu nhat, va "toi han som nhat" la han gan nhat.
  assert.deepStrictEqual(B.sortWithin(late, 'overdue', NOW).map(row => row.id), ['B', 'C', 'A']);
  assert.deepStrictEqual(B.sortWithin(late, 'pending', NOW).map(row => row.id), ['B', 'C', 'A']);
  // DO chua co han luon bi day xuong cuoi o cac ro khac.
  const mixed = [{ id: 'X' }, { id: 'Y', delivery_date: '2026-09-01' }];
  assert.deepStrictEqual(B.sortWithin(mixed, 'pending', NOW).map(row => row.id), ['Y', 'X']);
  // DO chưa có hạn xếp theo mã cho ổn định.
  const undated = [{ id: 'Z' }, { id: 'A' }, { id: 'M' }];
  assert.deepStrictEqual(B.sortWithin(undated, 'undated', NOW).map(row => row.id), ['A', 'M', 'Z']);
  // Không được làm mất dòng nào.
  assert.strictEqual(B.sortWithin(late, 'overdue', NOW).length, 3);
}

// --- 7. Lọc và dữ liệu bẩn ----------------------------------------------

assert.strictEqual(B.filter([OVERDUE, DUE_SOON, PENDING], 'overdue', NOW).length, 1);
assert.deepStrictEqual(B.filter(null, 'pending', NOW), []);
assert.deepStrictEqual(B.counts(null, NOW).pending, 0);
assert.strictEqual(B.bucketOf({}, NOW), 'undated', 'không có gì thì là thiếu hạn giao');
assert.strictEqual(B.bucketOf({ delivery_date: 'không phải ngày' }, NOW), 'undated');

// --- Rổ "Đã huỷ" -----------------------------------------------------------
//
// LỖI ĐO ĐƯỢC TRÊN DỮ LIỆU THẬT: một DO khách đã huỷ hiện ở tab "Sắp tới hạn".
// Nhánh else ở cuối coi mọi trạng thái không phải đã-giao / đang-chạy là chưa
// lên đường rồi đo hạn giao của nó — nên một đơn đã chết vẫn báo sắp trễ, và
// người điều phối thấy một việc không có gì để làm.
{
  const sapToiHan = new Date(NOW + 3 * 60 * 60 * 1000).toISOString();
  assert.strictEqual(
    B.bucketOf({ canonical_status: 'cancelled', delivery_window_end: sapToiHan }, NOW),
    'cancelled',
    'DO đã huỷ phải vào rổ Đã huỷ, không phải Sắp tới hạn'
  );
  assert.strictEqual(B.bucketOf({ canonical_status: 'Đã hủy' }, NOW), 'cancelled',
    'nhãn tiếng Việt cũng phải vào rổ Đã huỷ');
  // Và nó là rổ CUỐI thang cấp bách: việc đã huỷ không bao giờ là việc mở sẵn.
  assert.strictEqual(B.BUCKETS[B.BUCKETS.length - 1].key, 'cancelled');
  assert.strictEqual(
    B.defaultBucket([{ canonical_status: 'cancelled' }, { canonical_status: 'in_transit' }], NOW),
    'active',
    'tab mở sẵn phải bỏ qua rổ Đã huỷ khi còn việc đang chạy'
  );
}

console.log('do-board: tất cả kiểm tra đã qua');

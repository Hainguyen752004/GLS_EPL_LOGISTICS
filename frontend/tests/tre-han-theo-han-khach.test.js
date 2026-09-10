/**
 * Bảng Chuyến gán "trễ hạn" theo HẠN KHÁCH, không theo kế hoạch nội bộ.
 *
 * Chủ dự án hỏi: "một cái đã hoàn tất tại sao lại gán mác trễ hạn". Vì
 * `tripHanGiao` cũ lấy `planned_arrival_at` — mốc hệ thống tự tính lúc lập
 * chuyến — làm hạn; chuyến tới sau mốc đó 2 giờ nhưng vẫn trong khung giao
 * khách cho phép liền bị tô đỏ. Bài kiểm này chạy thật ba hàm trên dữ liệu
 * giả để khoá định nghĩa mới.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8');

function than(neo, ket) {
  const i = app.indexOf(neo); assert.ok(i >= 0, 'không thấy ' + neo);
  const j = ket ? app.indexOf(ket, i) : -1; return app.slice(i, j > 0 ? j : i + 4000);
}

// Nạp đúng ba hàm + tripGioToiNoi vào một phạm vi riêng có appState giả.
const ma = than('function tripHanGiao(raw)', 'function tripTreHan(raw)')
  + than('function tripTreHan(raw)', '/** Chuyến có chặng về hay không.')
  + than('function tripGioToiNoi(raw)', '/** Chuyến có chặng về hay không.');
const lam = new Function('appState', ma + '; return { tripHanGiao, tripKeHoachToi, tripTreHan, tripGioToiNoi };');

const KH = '2026-07-01T13:00:00+00:00';        // hạn khách
const keHoach = '2026-07-01T05:30:00+00:00';   // kế hoạch nội bộ

// 1. Có `delivery_due_at` từ backend: hạn = hạn khách; tới sau kế hoạch nhưng trước hạn => KHÔNG trễ.
{
  const f = lam({ delivery_orders: [] });
  const raw = { delivery_due_at: KH, planned_arrival_at: keHoach, actual_arrival_at: '2026-07-01T07:00:00+00:00',
    is_late: false, behind_plan_minutes: 90, delivery_order_ids: ['DO-1'] };
  assert.strictEqual(f.tripHanGiao(raw).toISOString(), new Date(KH).toISOString());
  assert.strictEqual(f.tripKeHoachToi(raw).toISOString(), new Date(keHoach).toISOString());
  assert.strictEqual(f.tripTreHan(raw), false, 'lệch kế hoạch không phải trễ hạn');
}

// 2. Tới sau hạn khách => trễ.
{
  const f = lam({ delivery_orders: [] });
  const raw = { delivery_due_at: KH, planned_arrival_at: keHoach, actual_arrival_at: '2026-07-01T13:25:00+00:00',
    is_late: true, delivery_order_ids: ['DO-1'] };
  assert.strictEqual(f.tripTreHan(raw), true);
}

// 3. Chưa tới nơi thì không bao giờ "trễ" (dù backend có cờ).
{
  const f = lam({ delivery_orders: [] });
  assert.strictEqual(f.tripTreHan({ delivery_due_at: KH, is_late: true, actual_arrival_at: null }), false);
}

// 4. Backend cũ chưa có `delivery_due_at`: tra khung giao của DO đang nạp; không có thì null, KHÔNG suy ra trễ.
{
  const f = lam({ delivery_orders: [{ id: 'DO-1', delivery_window_end: KH }, { id: 'DO-2', delivery_window_end: '2026-07-01T10:00:00+00:00' }] });
  const raw = { planned_arrival_at: keHoach, actual_arrival_at: '2026-07-01T07:00:00+00:00', delivery_order_ids: ['DO-1', 'DO-2'] };
  assert.strictEqual(f.tripHanGiao(raw).toISOString(), new Date(KH).toISOString(), 'lấy khung muộn nhất trong các DO');
  assert.strictEqual(f.tripTreHan(raw), false);
  const g = lam({ delivery_orders: [] });
  assert.strictEqual(g.tripHanGiao(raw), null, 'không có hạn thì null, không lấy kế hoạch làm hạn');
  assert.strictEqual(g.tripTreHan(raw), false);
}

// 5. Bảng và dải số liệu dùng đúng hàm mới; không còn `toi > han` với planned.
{
  const bang = than('const dong = items.map(item => {', 'const dsDO = raw.delivery_order_ids');
  assert.ok(/const treHan = tripTreHan\(raw\)/.test(bang), 'bảng dùng tripTreHan');
  assert.ok(!/toi > han/.test(bang));
  const kpi = than('function tripNhomKpi(raw, nhomVongDoi)', 'const pod = tripSoPOD(raw)');
  assert.ok(/tripTreHan\(raw\)/.test(kpi) && !/toi > han/.test(kpi), 'dải số liệu dùng tripTreHan');
  assert.ok(/hạn khách/.test(than("+ '<td class=\"eta '", "'<td><span class=\"pod\">")), 'ô ETA ghi rõ đó là hạn khách');
  assert.ok(/lệch KH/.test(app), 'lệch kế hoạch hiện là ghi chú vàng riêng');
}

console.log('tre-han-theo-han-khach: OK');

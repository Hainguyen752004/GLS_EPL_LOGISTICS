/**
 * Điều phối xe khác loại xe của báo giá: hỏi xác nhận rồi gửi lại, không chặn cứng.
 *
 * Máy chủ trả 409 `VEHICLE_TYPE_MISMATCH`; trước đây bộ chuẩn hoá lỗi bỏ mã đi
 * nên màn chỉ hiện chữ và không có cách nào gửi lại có xác nhận. Bài kiểm chạy
 * thật `dieuPhoiCoXacNhanLoaiXe` với executeWorkflowCommand giả.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8');
const policy = require(path.join(ROOT, 'js', 'command-policy.js'));

// 1. normalizeCommandError giữ `code`.
{
  const pol = policy.normalizeCommandError || (policy.default && policy.default.normalizeCommandError);
  if (typeof pol === 'function') {
    const e = pol({ detail: { code: 'VEHICLE_TYPE_MISMATCH', message: 'x' } });
    assert.strictEqual(e.code, 'VEHICLE_TYPE_MISMATCH');
  } else {
    const src = fs.readFileSync(path.join(ROOT, 'js', 'command-policy.js'), 'utf8');
    assert.ok(/code: typeof detail\.code === 'string' \? detail\.code : ''/.test(src), 'normalizeCommandError phải giữ code');
  }
}

// 2. Chạy thật hàm hỏi xác nhận.
const i = app.indexOf('async function dieuPhoiCoXacNhanLoaiXe(command)');
assert.ok(i > 0);
const than = app.slice(i, app.indexOf('async function executeWorkflowCommand(', i));
const lam = (ketQuaLanDau, dongY) => {
  const goi = [];
  const ctx = {
    executeWorkflowCommand: async (ten, cmd) => { goi.push(cmd); return goi.length === 1 ? ketQuaLanDau : { ok: true, payload: {} }; },
    window: { confirm: () => dongY },
  };
  const f = new Function('executeWorkflowCommand', 'window', than + '; return dieuPhoiCoXacNhanLoaiXe;')(ctx.executeWorkflowCommand, ctx.window);
  return { f, goi };
};
const cmd = { path: '/api/tms/trips/T1/dispatch', method: 'PUT', body: { vehicle_id: 'V1' } };

(async () => {
  // ok ngay → một lần gọi
  let { f, goi } = lam({ ok: true }, true);
  await f(cmd); assert.strictEqual(goi.length, 1);

  // lỗi khác → không hỏi, không gửi lại
  ({ f, goi } = lam({ ok: false, error: { code: 'RESOURCE_BUSY', message: 'bận' } }, true));
  let kq = await f(cmd); assert.strictEqual(goi.length, 1); assert.strictEqual(kq.ok, false);

  // khác loại + đồng ý → gửi lại với cờ xác nhận, body cũ giữ nguyên
  ({ f, goi } = lam({ ok: false, error: { code: 'VEHICLE_TYPE_MISMATCH', message: 'khác loại' } }, true));
  kq = await f(cmd);
  assert.strictEqual(goi.length, 2);
  assert.strictEqual(goi[1].body.confirm_vehicle_type_mismatch, true);
  assert.strictEqual(goi[1].body.vehicle_id, 'V1');
  assert.strictEqual(kq.ok, true);

  // khác loại + từ chối → dừng
  ({ f, goi } = lam({ ok: false, error: { code: 'VEHICLE_TYPE_MISMATCH', message: 'khác loại' } }, false));
  kq = await f(cmd); assert.strictEqual(goi.length, 1); assert.strictEqual(kq.ok, false);

  // hai chỗ điều phối đều đi qua hàm này
  assert.strictEqual((app.match(/await dieuPhoiCoXacNhanLoaiXe\(/g) || []).length, 2, 'cả hai màn điều phối dùng hàm hỏi xác nhận');
  assert.ok(!/executeWorkflowCommand\('dispatch', \{\n\s*path: `\/api\/tms\/trips\/\$\{trip\.id\}\/dispatch`/.test(app));
  console.log('dieu-phoi-xac-nhan-khac-loai-xe: OK');
})().catch(e => { console.error(e); process.exit(1); });

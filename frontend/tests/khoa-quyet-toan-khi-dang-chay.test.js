/**
 * Đang vận chuyển thì CẤM sửa quyết toán chi phí.
 *
 * Giá hợp đồng đã chốt từ SO. Trong lúc xe còn trên đường thì chưa biết phát
 * sinh là bao nhiêu, và chưa có POD ký nhận — nên không được sửa tiền. Mở ra
 * là mở cửa cho người ta đổi số giữa chuyến.
 *
 * Backend ĐÃ chặn đúng từ trước: `_save_trip_cost_rows` trả 409
 * `TRIP_NOT_COMPLETED` — "Chỉ được quyết toán chi phí sau khi chuyến đã hoàn
 * thành POD". Nhưng giao diện vẫn hiện nút "Thêm khoản phí" và "Lưu chi phí"
 * cho một DO đang vận chuyển, nên bấm vào chỉ nhận một lời từ chối. Đó là một
 * nút NÓI DỐI: nó mời người ta bấm một việc hệ thống không cho làm.
 *
 * Lỗi nằm ở `refreshDOSettlementLineControls()`: nó LUÔN mở nút và bỏ
 * `disabled` mọi ô nhập, không xét trạng thái nào cả.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const NL = String.fromCharCode(10);
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8')
  .split(String.fromCharCode(13)).join('');

function than(neo, ket) {
  const i = app.indexOf(neo);
  assert.ok(i > 0, `không thấy ${neo}`);
  return app.slice(i, app.indexOf(NL + (ket || '}'), i) + 2);
}

// --- 1. Hai nút và mọi ô nhập đều theo trạng thái ---------------------

{
  const t = than('function refreshDOSettlementLineControls(quyetToanDuoc = true, lyDo = "")');

  // Nút "Thêm khoản phí": ẩn hẳn, không phải làm mờ. Nút xám vẫn mời bấm.
  assert.ok(/addBtn\.style\.display = quyetToanDuoc \? 'inline-flex' : 'none'/.test(t),
    'nút Thêm khoản phí phải ẨN khi chưa được quyết toán');
  // Mọi ô nhập phải khóa — ẩn nút mà để ô sửa được thì vẫn sửa được số.
  assert.ok(/input\.disabled = !quyetToanDuoc/.test(t),
    'mọi ô nhập phải khóa khi chưa được quyết toán');
  // Nút xóa từng dòng cũng vậy.
  assert.ok(/button\.style\.display = quyetToanDuoc \? 'inline-flex' : 'none'/.test(t),
    'nút xóa từng dòng cũng phải ẩn');
  // Và phải NÓI RÕ vì sao — ẩn nút mà không nói gì thì tưởng màn hình hỏng.
  assert.ok(/do-settlement-locked-note/.test(t), 'phải có chỗ nói lý do');

  assert.ok(html.includes('id="do-settlement-locked-note"'), 'thiếu ô nói lý do trong HTML');
  const i = html.indexOf('id="do-settlement-locked-note"');
  const the = html.slice(html.lastIndexOf('<', i), html.indexOf('>', i) + 1);
  assert.ok(/\bhidden\b/.test(the), 'ô nói lý do phải ẩn sẵn trong HTML tĩnh');
  // Và nó chỉ ẩn được nhờ luật chung `[hidden]` — không có luật đó thì nó hiện
  // mãi, vì `.md-...`/inline style đè lên luật của trình duyệt.
  assert.ok(/\[hidden\] \{ display: none !important; \}/.test(html),
    'thiếu luật chung [hidden] thì ô nói lý do không ẩn được');
}

// --- 2. MỘT chỗ quyết định, không để mỗi nút tự đoán ------------------

{
  const t = than('function setDOSettlementSaveState(trip, loading = false)');
  assert.ok(/refreshDOSettlementLineControls\(Boolean\(trip\)/.test(t),
    'nơi biết có Trip hoàn thành phải là nơi quyết định cho cả hai nút');
  assert.ok(/lyDoChuaQuyetToanDuoc\(doId\)/.test(t), 'phải kèm lý do đúng trạng thái');
  // Nút Lưu vẫn phải khóa khi không có Trip hoàn thành.
  assert.ok(/button\.disabled = loading \|\| !trip/.test(t));
}

// --- 3. Lý do phải nói ĐÚNG việc cần làm cho từng trạng thái ----------
//
// Một câu "chưa quyết toán được" chung chung thì người dùng không biết phải
// chờ gì. Chạy THẬT hàm này với từng trạng thái.

{
  const t = than('function lyDoChuaQuyetToanDuoc(doId)');
  const f = ds => new Function('eplDeliveryOrders',
    t + NL + 'return lyDoChuaQuyetToanDuoc;')(ds);

  const goi = (tt) => f([{ id: 'DO-1', canonical_status: tt }])('DO-1');

  // Đang vận chuyển: phải nói rõ CẤM sửa, và nói mốc mở là sau khi có POD.
  const dangChay = goi('in_transit');
  assert.ok(/KHÔNG được sửa/.test(dangChay), dangChay);
  assert.ok(/POD/.test(dangChay), dangChay);

  // Đã đến nơi mà chưa có POD thì vẫn chưa chốt được — cùng luật với backend.
  assert.strictEqual(goi('arrived'), dangChay, 'đã đến nơi nhưng chưa có POD thì vẫn khóa');

  // Chưa xuất bến: chưa có gì phát sinh.
  assert.ok(/chưa xuất bến/.test(goi('pending')), goi('pending'));
  // Đã hủy: không quyết toán.
  assert.ok(/đã hủy/.test(goi('cancelled')), goi('cancelled'));
  // Trạng thái lạ thì vẫn phải nói được một việc cần làm, không trả rỗng.
  ['delivered', 'completed', '', 'gi_do_la'].forEach(tt => {
    assert.ok(goi(tt).length > 20, `trạng thái "${tt}" trả lý do rỗng`);
  });
  // DO không có trong bộ đệm cũng không được vỡ.
  assert.ok(f([])('DO-9').length > 20);
}

// --- 4. Ba con số phải hiện đủ: ban đầu, phát sinh, giá cuối ----------

{
  ['do-contract-total', 'do-extra-cost-total-display', 'do-payable-total']
    .forEach(ma => {
      assert.ok(html.includes(`id="${ma}"`), `thiếu ô tổng #${ma}`);
    });
  // Nhãn phải gọi đúng là "Giá cuối cùng" — "Tổng tiền phải trả" không nói ra
  // rằng đây là con số ĐÃ CHỐT sau khi cộng phát sinh.
  assert.ok(html.includes('Giá cuối cùng'), 'thiếu nhãn "Giá cuối cùng"');
  assert.ok(html.includes('Tổng giá ban đầu'), 'phải giữ nhãn giá ban đầu');
  assert.ok(html.includes('Tổng chi phí phát sinh'), 'phải giữ nhãn chi phí phát sinh');
}

// --- 5. Giá hợp đồng ban đầu KHÔNG được sửa trực tiếp -----------------

{
  const i = html.indexOf('id="do-original-contract-amount-display"');
  const the = html.slice(html.lastIndexOf('<', i), html.indexOf('>', i) + 1);
  assert.ok(/\breadonly\b/.test(the),
    'giá hợp đồng ban đầu phải chỉ đọc — phát sinh nhập ở các dòng bên dưới');
  ['do-contract-total', 'do-extra-cost-total-display', 'do-payable-total']
    .forEach(ma => {
      const j = html.indexOf(`id="${ma}"`);
      const t2 = html.slice(html.lastIndexOf('<', j), html.indexOf('>', j) + 1);
      assert.ok(/\breadonly\b/.test(t2), `#${ma} phải chỉ đọc`);
    });
}

// --- 6. Giá thực tế không được nhỏ hơn giá ban đầu --------------------

{
  const t = than('async function saveDOSettlementCost()', '}');
  assert.ok(/actual_amount < line\.original_amount/.test(t),
    'phải chặn giá thực tế nhỏ hơn giá ban đầu');
  // Và vẫn phải có mốc Trip hoàn thành trước khi gửi.
  assert.ok(/Chỉ được quyết toán chi phí sau khi Trip của DO đã hoàn thành/.test(t),
    'phải nói rõ mốc Trip hoàn thành');
}

console.log('khoa-quyet-toan-khi-dang-chay: tất cả kiểm tra đã qua');

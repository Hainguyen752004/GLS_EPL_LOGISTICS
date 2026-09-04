/**
 * Định giá báo giá — kiểm chứng bằng đúng số liệu thật trên màn hình.
 *
 * Màn báo giá đang hiện một con số chỉ bằng một phần nhỏ giá thật theo công thức
 * đã cấu hình. Ba nguyên nhân cộng lại:
 *
 *   1. Cước phí vận chuyển (1.200 đ/kg × 3.000 kg = 3.600.000 đ) bị bỏ hẳn —
 *      ô cước không hề được đọc.
 *   2. Một hệ số bịa `max_weight / 15000` = 0,67 nhân vào xăng dầu và phụ cấp.
 *   3. Phí bãi bị gộp vào ô "Phí cầu đường" nên ô đó nói sai tên con số.
 */
const assert = require('assert');
const path = require('path');

const P = require(path.join(__dirname, '..', 'js', 'quotation-pricing.js'));

// Đúng cấu hình đang có trong cơ sở dữ liệu cho loại xe "Xe tải 5 tấn".
const FORMULA = {
  name: 'Xe tải 5 tấn',
  currency: 'VND',
  vehicleTypeId: 'VT-002',
  vehicleTypeName: 'Xe tải 5 tấn',
  terms: [
    { key: 'fuel', label: 'Chi phí xăng dầu /km', operator: 'add', factor: 'per_km', rate: 4800, builtin: true },
    { key: 'driver', label: 'Phụ cấp chuyến tài xế', operator: 'add', factor: 'per_trip', rate: 400000, builtin: true },
    { key: 'toll', label: 'Phí cầu đường / BOT', operator: 'add', factor: 'per_trip', rate: 150000, builtin: true },
    { key: 'wh', label: 'Phí bãi & lưu kho', operator: 'add', factor: 'per_trip', rate: 100000, builtin: true },
    { key: 'rate', label: 'Cước phí vận chuyển /kg', operator: 'add', factor: 'per_kg', rate: 1200, builtin: true },
  ],
};
const STORE = { 'vt-002-VND': FORMULA };
const TYPES = [{ id: 'VT-002', name: 'Xe tải 5 tấn', max_weight: 5000 }];
const ROUTE = { id: 'RT-001', name: 'Hà Nội ➔ Hải Phòng', distance_km: 128.45 };

function priceStandard(extra) {
  return P.price({
    store: STORE, vehicleTypes: TYPES, cargoType: 'Xe tải 5 tấn',
    route: ROUTE, tonnes: 3, ...extra,
  });
}

// --- 1. Ra đúng con số, không thiếu cấu phần nào -------------------------

{
  const result = priceStandard();
  assert.ok(result.ready, 'đủ đầu vào thì phải ra giá: ' + JSON.stringify(result.blockers));

  // 4800 × 128,45 + 400000 + 150000 + 100000 + 1200 × 3000
  const expected = 4800 * 128.45 + 400000 + 150000 + 100000 + 1200 * 3000;
  assert.strictEqual(result.total, expected);
  assert.strictEqual(Math.round(result.total), 4866560, 'phải khớp con số tính tay');

  // Cấu phần lớn nhất KHÔNG được biến mất. Đây là lỗi nặng nhất của bản cũ.
  const byKey = Object.fromEntries(result.rows.map(row => [row.key, row]));
  assert.strictEqual(byKey.rate.amount, 3600000, 'cước theo kg phải có trong giá');
  assert.ok(result.rows.length >= 5, 'phải hiện đủ mọi cấu phần đã cấu hình');

  // Không còn hệ số bịa 0,67: xăng dầu đúng bằng đơn giá × số km của tuyến.
  assert.strictEqual(byKey.fuel.amount, 4800 * 128.45);
  assert.strictEqual(byKey.fuel.multiplier, 128.45, 'phải lấy tổng km của tuyến đang chọn');
  assert.strictEqual(byKey.driver.amount, 400000, 'phụ cấp chuyến không được nhân theo tải trọng loại xe');

  // Phí bãi là một dòng RIÊNG, không gộp vào phí cầu đường.
  assert.strictEqual(byKey.toll.amount, 150000);
  assert.strictEqual(byKey.wh.amount, 100000);
}

// Cấu phần người dùng tự thêm cũng phải vào giá — bản cũ chỉ hiện ba ô cố định.
{
  const store = {
    'vt-002-VND': {
      ...FORMULA,
      terms: [
        ...FORMULA.terms,
        { key: 'loading', label: 'Phí bốc xếp /tấn', operator: 'add', factor: 'per_tonne', rate: 80000 },
        { key: 'promo', label: 'Giảm giá khách quen', operator: 'sub', factor: 'per_trip', rate: 200000 },
      ],
    },
  };
  const result = P.price({ store, vehicleTypes: TYPES, cargoType: 'Xe tải 5 tấn', route: ROUTE, tonnes: 3 });
  const byKey = Object.fromEntries(result.rows.map(row => [row.key, row]));
  assert.strictEqual(byKey.loading.amount, 80000 * 3);
  assert.strictEqual(byKey.promo.amount, -200000, 'cấu phần trừ phải làm giảm giá');
  assert.strictEqual(result.total, 4800 * 128.45 + 650000 + 1200 * 3000 + 80000 * 3 - 200000);
}

// --- 2. Tải trọng nhân vào cước, không phải tải trọng tối đa của loại xe --

{
  // Cùng loại xe, cùng tuyến, chỉ khác khối lượng hàng.
  const light = priceStandard({ tonnes: 1 });
  const heavy = priceStandard({ tonnes: 5 });
  assert.strictEqual(heavy.total - light.total, 1200 * 4000, 'chênh 4 tấn là chênh đúng 4.000 kg cước');
  // Phần không phụ thuộc khối lượng phải giữ nguyên.
  const fuelOf = result => result.rows.find(row => row.key === 'fuel').amount;
  assert.strictEqual(fuelOf(light), fuelOf(heavy));
}

// Chuyến chạy rỗng LÀ CÓ THẬT: 0 tấn thì cước bằng 0 nhưng vẫn ra giá, và phải
// nói rõ để người báo giá không tưởng là hệ thống quên tính.
{
  const empty = priceStandard({ tonnes: 0 });
  assert.ok(empty.ready);
  assert.strictEqual(empty.rows.find(row => row.key === 'rate').amount, 0);
  assert.ok(empty.notes.some(note => /0 t[ấa]n/.test(note)), 'phải nhắc là đang tính với 0 tấn');
}

// Ô khối lượng trên đơn vận chuyển là ô CHỮ, đang chứa "25.0 Tonnes".
assert.strictEqual(P.parseTonnes('25.0 Tonnes'), 25);
assert.strictEqual(P.parseTonnes('3,5 tấn'), 3.5, 'phải đọc được dấu phẩy thập phân kiểu Việt');
assert.strictEqual(P.parseTonnes('12.000'), 12000, 'dấu chấm nghìn kiểu Việt');
assert.strictEqual(P.parseTonnes('0'), 0);
// Chưa nhập KHÁC 0 tấn: chưa nhập là chưa biết, 0 là chuyến chạy rỗng.
assert.strictEqual(P.parseTonnes(''), null);
assert.strictEqual(P.parseTonnes(null), null);
assert.strictEqual(P.parseTonnes('chưa rõ'), null);
assert.strictEqual(P.parseTonnes('-4'), null, 'khối lượng âm là vô nghĩa');

// --- 3. Thiếu đầu vào thì KHÔNG được đưa ra con số ----------------------
//
// Đây là quy tắc chung của dự án: màn hình không bao giờ hiện một con số trông
// chắc chắn khi nó thật ra không tính được.

{
  const noRoute = priceStandard({ route: null });
  assert.ok(!noRoute.ready);
  assert.strictEqual(noRoute.total, null, 'chưa có tuyến thì không có tổng, kể cả số 0');
  assert.strictEqual(noRoute.perKm, null);
  assert.ok(noRoute.blockers.some(item => item.field === 'route'));
}

{
  // Tuyến có trong danh mục nhưng chưa nhập số km — phải nói rõ tuyến nào.
  const noKm = priceStandard({ route: { id: 'RT-009', name: 'Tuyến mới', distance_km: 0 } });
  assert.ok(!noKm.ready);
  assert.strictEqual(noKm.total, null);
  assert.ok(noKm.blockers.some(item => /Tuyến mới/.test(item.message)));
}

{
  const noType = priceStandard({ cargoType: '' });
  assert.ok(!noType.ready);
  assert.ok(noType.blockers.some(item => item.field === 'cargoType'));
}

{
  // Loại xe chưa có công thức: phải chỉ đúng chỗ đi cấu hình, và tuyệt đối
  // KHÔNG lấy công thức của loại xe khác thay thế.
  const other = P.price({
    store: STORE, vehicleTypes: [...TYPES, { id: 'VT-777', name: 'Xe đầu kéo 40 tấn' }],
    cargoType: 'Xe đầu kéo 40 tấn', route: ROUTE, tonnes: 3,
  });
  assert.ok(!other.ready);
  assert.strictEqual(other.total, null);
  assert.strictEqual(other.formulaKey, '', 'không được mượn công thức của loại xe khác');
  assert.ok(other.blockers.some(item => /chưa có công thức/.test(item.message)));
  assert.ok(other.blockers.some(item => /Dữ liệu gốc/.test(item.message)), 'phải chỉ đường đi cấu hình');
}

{
  // Công thức có cước theo kg mà chưa nhập tải trọng: không được coi như 0 tấn
  // rồi âm thầm bỏ mất 3,6 triệu tiền cước.
  const noWeight = priceStandard({ tonnes: '' });
  assert.ok(!noWeight.ready);
  assert.strictEqual(noWeight.total, null);
  assert.ok(noWeight.blockers.some(item => item.field === 'tonnes'));
}

{
  // Nhưng công thức KHÔNG có cấu phần theo khối lượng thì không được đòi tải trọng.
  const store = {
    'vt-002-VND': { ...FORMULA, terms: FORMULA.terms.filter(term => term.key !== 'rate') },
  };
  const result = P.price({ store, vehicleTypes: TYPES, cargoType: 'Xe tải 5 tấn', route: ROUTE, tonnes: '' });
  assert.ok(result.ready, 'không có cước theo kg thì không cần tải trọng');
  assert.strictEqual(result.total, 4800 * 128.45 + 650000);
}

{
  // Mọi đơn giá bằng 0 là chưa cấu hình xong, không phải "chuyến miễn phí".
  const store = { 'vt-002-VND': { ...FORMULA, terms: FORMULA.terms.map(term => ({ ...term, rate: 0 })) } };
  const result = P.price({ store, vehicleTypes: TYPES, cargoType: 'Xe tải 5 tấn', route: ROUTE, tonnes: 3 });
  assert.ok(!result.ready);
  assert.strictEqual(result.total, null, 'không được báo giá 0 đồng');
}

// --- 4. KHÔNG có số cứng dự phòng --------------------------------------

{
  // Chưa nạp được cấu hình nào: phải chịu không có số, chứ không lấy
  // 6250 / 500000 / 300000 / 200000 rồi hiện ra như giá thật.
  const empty = P.price({ store: {}, vehicleTypes: TYPES, cargoType: 'Xe tải 5 tấn', route: ROUTE, tonnes: 3 });
  assert.ok(!empty.ready);
  assert.strictEqual(empty.total, null);
}
{
  const source = require('fs').readFileSync(path.join(__dirname, '..', 'js', 'quotation-pricing.js'), 'utf8');
  const code = source.split('\n').filter(line => {
    const trimmed = line.trim();
    return !trimmed.startsWith('*') && !trimmed.startsWith('//') && !trimmed.startsWith('/*');
  }).join('\n');
  ['6250', '500000', '300000', '200000', '15000'].forEach(magic => {
    assert.ok(!code.includes(magic), `không được còn số cứng ${magic} trong phần định giá`);
  });
}

// --- 5. Công thức tìm theo loại xe, cả bằng tên lẫn bằng mã -------------

assert.strictEqual(P.resolveFormula(STORE, TYPES, 'Xe tải 5 tấn').key, 'vt-002-VND');
{
  // Công thức chỉ lưu mã loại xe, không lưu tên: vẫn phải nối được qua danh mục.
  const store = { 'k': { vehicleTypeId: 'VT-002', currency: 'VND' } };
  assert.strictEqual(P.resolveFormula(store, TYPES, 'Xe tải 5 tấn').key, 'k');
}
assert.strictEqual(P.resolveFormula(STORE, TYPES, ''), null);
assert.strictEqual(P.resolveFormula(null, null, 'Xe tải 5 tấn'), null);
// Khoảng trắng thừa trong tên không được làm mất công thức.
assert.strictEqual(P.resolveFormula(STORE, TYPES, '  Xe tải 5 tấn  ').key, 'vt-002-VND');

// --- 6. Công thức lưu từ trước khi có hạng tử vẫn tính ra tiền ----------

{
  const legacy = { 'k': { vehicleTypeName: 'Xe tải 5 tấn', fuel: '4,800', driver: '400,000', toll: '150,000', wh: '100,000', rate: '1,200' } };
  const result = P.price({ store: legacy, vehicleTypes: TYPES, cargoType: 'Xe tải 5 tấn', route: ROUTE, tonnes: 3 });
  assert.ok(result.ready, 'cấu hình cũ chưa có hạng tử vẫn phải tính được');
  assert.strictEqual(Math.round(result.total), 4866560);
}

// --- 7. Dữ liệu bẩn không được làm vỡ ----------------------------------

assert.strictEqual(P.price().total, null);
assert.strictEqual(P.price({}).total, null);
assert.ok(P.price(null).blockers.length > 0);
assert.strictEqual(priceStandard({ stops: 0 }).stops, 1, 'ít nhất một điểm giao');
assert.strictEqual(priceStandard({ stops: 'ba' }).stops, 1);

console.log('quotation-pricing: tất cả kiểm tra đã qua');

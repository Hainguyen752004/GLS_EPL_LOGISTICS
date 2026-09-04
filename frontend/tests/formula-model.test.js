/**
 * Công thức giá thành động — mô hình biểu thức.
 *
 * Chủ dự án cần đổi được cách tính: thêm/bớt cấu phần, đổi dấu, đổi hệ số nhân.
 *
 * Vì sao không dùng lại trình dựng biểu thức kéo thả tự do (bản cũ, bị ẩn bằng
 * display:none từ lâu): nó cho phép dựng ra công thức **sai thứ nguyên** mà
 * không gì kiểm được — nhân cước theo kg với số km chẳng hạn. Mô hình hạng tử ở
 * đây vẫn động nhưng mỗi hạng tử khai rõ mình tính theo gì, nên kiểm được.
 */
const assert = require('assert');
const path = require('path');

const M = require(path.join(__dirname, '..', 'js', 'formula-model.js'));

function withRates(rates) {
  const terms = M.defaultTerms();
  terms.forEach(term => { term.rate = rates[term.key] || 0; });
  return terms;
}

const RATES = { fuel: 4800, driver: 400000, toll: 150000, wh: 100000, rate: 1200 };

// --- 1. Mỗi hệ số nhân với đúng thứ của nó --------------------------------

{
  const result = M.evaluate(withRates(RATES), { km: 200, tonnes: 15 });
  const byKey = Object.fromEntries(result.rows.map(row => [row.key, row]));

  assert.strictEqual(byKey.fuel.multiplier, 200, 'mỗi km nhân với số km');
  assert.strictEqual(byKey.driver.multiplier, 1, 'mỗi chuyến tính một lần');
  // 15 tấn = 15.000 kg. Nhầm tấn với kg ở đây là sai 1.000 lần.
  assert.strictEqual(byKey.rate.multiplier, 15000, 'mỗi kg nhân với số KG');
  // Bon cau phan dau la CHI PHI, cuoc theo kg la GIA BAN. Cong chung thi ra
  // mot con so khong phai gia thanh cung khong phai gia ban.
  assert.strictEqual(result.cost, 960000 + 400000 + 150000 + 100000);
  assert.strictEqual(result.revenue, 18000000);
  assert.strictEqual(result.profit, 18000000 - 1610000);
  assert.ok(Math.abs(result.marginPct - (16390000 / 18000000) * 100) < 1e-9);
  // Binh quan moi km la cua GIA THANH: chia cuoc theo kg cho so km thi ra mot
  // con so khong phai don gia cua thu gi ca.
  assert.strictEqual(result.perKm, result.cost / 200);
}

// Hệ số theo tấn và theo điểm giao.
{
  const terms = [
    { key: 'a', label: 'Bốc xếp', operator: 'add', factor: 'per_tonne', rate: 80000 },
    { key: 'b', label: 'Phí điểm', operator: 'add', factor: 'per_stop', rate: 50000 },
  ];
  const result = M.evaluate(terms, { km: 100, tonnes: 12, stops: 3 });
  assert.strictEqual(result.rows[0].amount, 80000 * 12);
  assert.strictEqual(result.rows[1].amount, 50000 * 3);
  assert.strictEqual(result.cost, 80000 * 12 + 50000 * 3, 'mac dinh la chi phi');
  assert.strictEqual(result.revenue, 0);
  assert.strictEqual(result.marginPct, null, 'chua co gia ban thi khong co ti le nao ca');
}

// --- 2. Động: thêm cấu phần và phép TRỪ -----------------------------------

{
  const terms = withRates(RATES);
  terms.push({ key: 'loading', label: 'Phí bốc xếp /tấn', operator: 'add', factor: 'per_tonne', rate: 80000 });
  terms.push({ key: 'discount', label: 'Giảm giá khách quen', operator: 'sub', factor: 'per_trip', rate: 500000 });

  const result = M.evaluate(terms, { km: 200, tonnes: 15 });
  const byKey = Object.fromEntries(result.rows.map(row => [row.key, row]));
  assert.strictEqual(byKey.loading.amount, 80000 * 15);
  assert.strictEqual(byKey.discount.amount, -500000, 'phép trừ phải ra số âm');
  assert.strictEqual(byKey.discount.sign, '−');
  // Cau phan tu them mac dinh la CHI PHI, nen cong vao gia thanh.
  assert.strictEqual(byKey.loading.kind, 'cost');
  assert.strictEqual(byKey.discount.kind, 'cost');
  assert.strictEqual(result.cost, 1610000 + 1200000 - 500000);
  assert.strictEqual(result.revenue, 18000000);
}

// --- 3. Công thức chữ SINH TỪ hạng tử, không viết cứng --------------------

{
  const text = M.toText(withRates(RATES));
  assert.ok(text.includes('× số km'), 'phải nói rõ nhân với số km');
  assert.ok(text.includes('× số kg'));
  // Cấu phần tính theo chuyến không cần dấu nhân — viết ra sẽ rối.
  assert.ok(!text.includes('Phụ cấp chuyến tài xế ×'));

  // Thêm cấu phần thì câu công thức phải đổi theo. Bản trước là chuỗi viết
  // cứng nên sửa công thức xong nó vẫn đọc y như cũ — một kiểu nói dối nữa.
  const more = withRates(RATES);
  more.push({ key: 'x', label: 'Phí lưu ca', operator: 'sub', factor: 'per_trip', rate: 1 });
  const changed = M.toText(more);
  assert.notStrictEqual(changed, text);
  assert.ok(changed.includes('− Phí lưu ca'));

  assert.strictEqual(M.toText([]), 'Chưa có cấu phần nào');
}

// --- 4. Bắt công thức tự mâu thuẫn ----------------------------------------

{
  // Nhãn ghi /kg mà lại nhân theo km — đúng loại sai thứ nguyên đã gây ra
  // chuyện điền số xăng dầu (đ/km) vào ô cước phí (đ/kg).
  const issues = M.problems([{ key: 'x', label: 'Cước phí /kg', operator: 'add', factor: 'per_km', rate: 1200 }]);
  const dimension = issues.find(issue => issue.level === 'error' && /đơn vị/.test(issue.message));
  assert.ok(dimension, 'phải bắt được sai thứ nguyên');
  assert.ok(dimension.message.includes('mỗi km'));
}

{
  // Nhãn và hệ số khớp nhau thì KHÔNG được báo bừa.
  const issues = M.problems([{ key: 'x', label: 'Cước phí /kg', operator: 'add', factor: 'per_kg', rate: 1200 }]);
  assert.ok(!issues.some(issue => /đơn vị/.test(issue.message)), 'khớp đơn vị thì không được cảnh báo');
}

{
  const empty = M.problems([]);
  assert.ok(empty.some(issue => issue.level === 'error'), 'công thức rỗng là lỗi');

  const allZero = M.problems(withRates({}));
  assert.ok(allZero.some(issue => /luôn bằng 0/.test(issue.message)), 'mọi cấu phần bằng 0 là lỗi');

  const duplicate = M.problems([
    { key: 'fuel', label: 'A', operator: 'add', factor: 'per_km', rate: 1 },
    { key: 'fuel', label: 'B', operator: 'add', factor: 'per_km', rate: 2 },
  ]);
  assert.ok(duplicate.some(issue => /hai l[ầa]n/.test(issue.message)), 'khai trùng là lỗi');
}

// --- 5. Chuyến mẫu -------------------------------------------------------

assert.deepStrictEqual(M.normalizeTrip(), M.DEFAULT_TRIP);
assert.strictEqual(M.normalizeTrip({ km: 0 }).km, M.DEFAULT_TRIP.km, '0 km vô nghĩa, quay về mẫu');
// Chuyến chạy rỗng LÀ CÓ THẬT: 0 tấn phải được giữ, không thay bằng mẫu.
assert.strictEqual(M.normalizeTrip({ km: 120, tonnes: 0 }).tonnes, 0);
{
  const result = M.evaluate(withRates(RATES), { km: 120, tonnes: 0 });
  const byKey = Object.fromEntries(result.rows.map(row => [row.key, row]));
  assert.strictEqual(byKey.rate.amount, 0, 'chạy rỗng thì không có cước theo kg');
}
assert.strictEqual(M.normalizeTrip({ tonnes: -5 }).tonnes, 0, 'khối lượng âm là vô nghĩa');

// --- 6. Dữ liệu bẩn không được làm vỡ ------------------------------------

assert.deepStrictEqual(M.normalize(null), []);
assert.deepStrictEqual(M.normalize(['không phải đối tượng', 42, null]), []);
{
  // Hệ số và dấu lạ phải rơi về mặc định an toàn thay vì ném lỗi.
  const [term] = M.normalize([{ key: 'x', label: 'X', operator: 'nhân', factor: 'per_parsec', rate: '1,500' }]);
  assert.strictEqual(term.factor, 'per_trip');
  assert.strictEqual(term.operator, 'add');
  assert.strictEqual(term.rate, 1500, 'phải bỏ được dấu phân cách nghìn');
}
assert.strictEqual(M.normalize([{ key: 'x', rate: -99 }])[0].rate, 0, 'đơn giá âm phải thành 0');
assert.strictEqual(M.normalize(Array(50).fill({ key: 'x', rate: 1 })).length, 30, 'phải có trần số hạng tử');
assert.strictEqual(M.evaluate(null).cost, 0, 'không có gì cũng không được vỡ');
assert.strictEqual(M.evaluate(null).revenue, 0);

// --- 6b. Chi phí và giá bán là hai loại khác nhau ---------------------------
//
// Chủ dự án đã chốt: bốn cấu phần đầu (xăng dầu, phụ cấp, BOT, phí bãi) là
// tiền CHI RA, còn cước phí theo kg là tiền THU CỦA KHÁCH. Bảng `quotations`
// đã có sẵn ba cột total_cost / selling_price / margin_pct, và dữ liệu thật xác
// nhận: selling_price 3.600.000 đúng bằng 1.200 đ/kg × 3.000 kg.

{
  const terms = M.defaultTerms();
  const byKey = Object.fromEntries(terms.map(term => [term.key, term]));
  ['fuel', 'driver', 'toll', 'wh'].forEach(key => {
    assert.strictEqual(byKey[key].kind, 'cost', `${key} phải là chi phí`);
  });
  assert.strictEqual(byKey.rate.kind, 'revenue', 'cước theo kg là giá bán');
}

{
  // Đúng con số trên màn hình: tuyến 44 km, 3 tấn, loại "Xe tải thùng 10 tấn".
  const result = M.evaluate(withRates(RATES), { km: 44, tonnes: 3 });
  assert.strictEqual(result.cost, 4800 * 44 + 400000 + 150000 + 100000);
  assert.strictEqual(result.cost, 861200);
  assert.strictEqual(result.revenue, 3600000);
  assert.strictEqual(result.profit, 2738800);
  assert.ok(Math.abs(result.marginPct - 76.077) < 0.01);
  // 4.461.200 là con số cũ — không phải giá thành, cũng không phải giá bán.
  assert.notStrictEqual(result.cost, 4461200);
  assert.notStrictEqual(result.revenue, 4461200);
}

{
  // Đổi loại một cấu phần thì hai con số chuyển chỗ cho nhau.
  const terms = withRates(RATES).map(term =>
    term.key === 'toll' ? { ...term, kind: 'revenue' } : term);
  const result = M.evaluate(terms, { km: 44, tonnes: 3 });
  assert.strictEqual(result.cost, 861200 - 150000);
  assert.strictEqual(result.revenue, 3600000 + 150000);
}

// Loại lạ phải rơi về CHI PHÍ — nhầm một khoản chi thành doanh thu sẽ làm lợi
// nhuận trông ra cao hơn thực tế.
assert.strictEqual(M.normalize([{ key: 'x', kind: 'lợi nhuận', rate: 1 }])[0].kind, 'cost');
assert.strictEqual(M.normalize([{ key: 'x', rate: 1 }])[0].kind, 'cost');

// Công thức không có cấu phần giá bán thì không báo giá được — phải nói ra.
{
  const chiCoChiPhi = withRates(RATES).filter(term => term.key !== 'rate');
  const issues = M.problems(chiCoChiPhi);
  assert.ok(issues.some(issue => issue.level === 'error' && /giá bán/.test(issue.message)));
}

// Bán dưới giá thành là lỗ. Không chặn, nhưng phải nói rõ.
{
  const banLo = withRates({ ...RATES, rate: 10 });
  const issues = M.problems(banLo);
  assert.ok(issues.some(issue => issue.level === 'error' && /THẤP HƠN giá thành/.test(issue.message)));
  // Còn lãi thì không được báo bừa.
  assert.ok(!M.problems(withRates(RATES)).some(issue => /THẤP HƠN/.test(issue.message)));
}

// --- 7. Đổi thứ tự hạng tử ------------------------------------------------

{
  const terms = withRates(RATES);
  const moved = M.move(terms, 0, 1);
  assert.strictEqual(moved[0].key, 'driver');
  assert.strictEqual(moved[1].key, 'fuel');
  // Ra ngoài biên thì giữ nguyên, không được vỡ hay mất hạng tử.
  assert.strictEqual(M.move(terms, 0, -1)[0].key, 'fuel');
  assert.strictEqual(M.move(terms, terms.length - 1, 1).length, terms.length);
}

// --- 8. Không có đường nào để chuỗi người dùng chạy thành mã -------------

{
  const source = require('fs').readFileSync(path.join(__dirname, '..', 'js', 'formula-model.js'), 'utf8');
  ['eval(', 'new Function', 'setTimeout(\''].forEach(danger => {
    assert.ok(!source.includes(danger), `mô hình không được dùng ${danger}`);
  });
  // Nhãn do người dùng đặt: phải đi qua được mà không thành mã.
  const nasty = [{ key: 'x', label: '<img src=x onerror=alert(1)>', operator: 'add', factor: 'per_trip', rate: 1 }];
  assert.strictEqual(M.evaluate(nasty).cost, 1);
  assert.ok(M.toText(nasty).includes('<img'), 'mô hình giữ nguyên chuỗi; việc thoát ký tự là của tầng vẽ');
}

console.log('formula-model: tất cả kiểm tra đã qua');

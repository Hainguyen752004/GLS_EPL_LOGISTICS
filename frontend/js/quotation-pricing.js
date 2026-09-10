/**
 * Định giá một chuyến để đưa vào báo giá và đơn vận chuyển.
 *
 * Bản cũ tính sai tiền, không phải sai một chút:
 *
 *   1. **Bỏ hẳn cước phí vận chuyển.** Nó chỉ đọc bốn ô xăng dầu / phụ cấp /
 *      BOT / bãi, còn ô cước theo kg — thường là cấu phần LỚN NHẤT — không hề
 *      được đọc. Với 3 tấn ở 1.200 đ/kg là 3.600.000 đ biến mất khỏi báo giá.
 *
 *   2. **Nhân bừa một hệ số bịa.** `(loại xe.max_weight / 15000)` được nhân vào
 *      xăng dầu và phụ cấp. Con số 15000 không có nguồn nào; và nó lấy tải
 *      trọng TỐI ĐA của loại xe, không phải khối lượng hàng thật, nên xe 10 tấn
 *      chở 1 tấn vẫn bị nhân 0,67.
 *
 *   3. **Có số cứng dự phòng.** Chưa nạp được cấu hình thì nó lấy 6250 / 500000
 *      / 300000 / 200000 rồi hiện ra một con số trông rất chắc chắn. Người dùng
 *      không có cách nào biết đó không phải giá mình đã cấu hình.
 *
 *   4. **Gộp phí bãi vào phí cầu đường** khi hiển thị, nên ô "Phí cầu đường"
 *      nói một con số không phải phí cầu đường.
 *
 *   5. **Chỉ hiện ba cấu phần.** Cấu phần người dùng tự thêm trong Master Data
 *      không xuất hiện ở đâu cả, dù vẫn phải nằm trong giá.
 *
 * Nay tiền được tính bằng đúng công thức của LOẠI XE đang chọn, với số km của
 * TUYẾN đang chọn và khối lượng hàng THẬT đã nhập. Thiếu thứ nào thì nói thiếu
 * thứ đó và không đưa ra con số — thà không có số hơn là có một số sai trông
 * như đúng.
 *
 * Module thuần: không đọc DOM, không gọi mạng.
 */
(function (root, factory) {
  const api = factory(root.FormulaModel || (typeof require === 'function' ? require('./formula-model.js') : null));
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  }
  root.QuotationPricing = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function (FormulaModel) {
  function toNumber(value) {
    if (value === null || value === undefined || value === '') return 0;
    const parsed = Number(String(value).replace(/[,\s]/g, ''));
    return Number.isFinite(parsed) ? parsed : 0;
  }

  /**
   * Số tấn đọc từ một ô người dùng nhập.
   *
   * Ô khối lượng trên đơn vận chuyển là ô CHỮ, đang chứa những giá trị như
   * "25.0 Tonnes", nên phải bóc số ra. Trả về null khi chưa nhập — khác hẳn với
   * 0: chưa nhập là chưa biết, còn 0 là chuyến chạy rỗng.
   */
  function parseTonnes(value) {
    const text = String(value === null || value === undefined ? '' : value).trim();
    if (!text) return null;
    const match = /-?[\d.,]+/.exec(text.replace(/\s/g, ''));
    if (!match) return null;
    // "25.000" trong tiếng Việt là hai mươi lăm nghìn, còn "25.0" là hai mươi
    // lăm phẩy không. Phân biệt bằng số chữ số sau dấu chấm cuối.
    let raw = match[0];
    const lastDot = raw.lastIndexOf('.');
    const lastComma = raw.lastIndexOf(',');
    if (lastComma > lastDot) {
      raw = raw.replace(/\./g, '').replace(',', '.');
    } else if (lastDot > -1 && raw.length - lastDot - 1 === 3 && !/,/.test(raw)) {
      raw = raw.replace(/\./g, '');
    } else {
      raw = raw.replace(/,/g, '');
    }
    const parsed = Number(raw);
    if (!Number.isFinite(parsed)) return null;
    // Khối lượng âm là vô nghĩa; coi như chưa nhập thay vì trừ tiền khách.
    return parsed < 0 ? null : parsed;
  }

  /**
   * Tìm công thức của loại xe đang chọn.
   *
   * Ô chọn loại xe trên báo giá mang TÊN loại xe, còn công thức lưu theo mã
   * loại xe, nên phải nối qua danh mục loại xe. Không tìm được thì trả về
   * `null` — tuyệt đối không lấy công thức của loại xe khác thay thế, vì mỗi
   * loại xe có giá riêng và lấy sai loại là báo giá sai mà không ai thấy.
   */
  function resolveFormula(store, vehicleTypes, cargoTypeName) {
    const name = String(cargoTypeName || '').trim();
    if (!name) return null;
    const entries = Object.entries(store || {});

    const byName = entries.find(([, formula]) =>
      String(formula?.vehicleTypeName || '').trim() === name);
    if (byName) return { key: byName[0], formula: byName[1] };

    const type = (vehicleTypes || []).find(item => String(item?.name || '').trim() === name);
    if (type) {
      const byId = entries.find(([, formula]) =>
        String(formula?.vehicleTypeId || '') === String(type.id || ''));
      if (byId) return { key: byId[0], formula: byId[1] };
    }
    return null;
  }

  /**
   * Hạng tử của một công thức đã lưu.
   *
   * Công thức lưu trước khi có mô hình hạng tử thì chỉ có năm đơn giá; dựng lại
   * hạng tử từ chúng để cấu hình cũ vẫn tính ra tiền.
   */
  function termsOf(formula) {
    if (!formula) return [];
    if (Array.isArray(formula.terms) && formula.terms.length) {
      return FormulaModel.normalize(formula.terms);
    }
    return FormulaModel.defaultTerms().map(term => ({
      ...term,
      rate: FormulaModel.toNumber(formula[term.key]),
    }));
  }

  /** Công thức có cần biết khối lượng hàng mới tính được không. */
  function needsWeight(terms) {
    return FormulaModel.normalize(terms).some(term =>
      term.rate > 0 && (term.factor === 'per_kg' || term.factor === 'per_tonne'));
  }

  /**
   * Giá một chuyến.
   *
   * `ready` nói con số có dùng được hay không. Chưa đủ đầu vào thì `ready` là
   * false và bên gọi phải hiện dấu gạch cùng lời nhắc, KHÔNG được hiện số 0 hay
   * một con số tính thiếu — đó chính là kiểu nói dối đã khiến báo giá trên màn
   * hình chỉ bằng một phần bảy giá thật.
   */
  function price(input) {
    const source = input || {};
    const blockers = [];
    const notes = [];

    const route = source.route || null;
    const routeKm = toNumber(route?.distance_km);
    if (!route) {
      blockers.push({ field: 'route', message: 'Chưa chọn tuyến đường nên chưa có số km để tính.' });
    } else if (routeKm <= 0) {
      blockers.push({
        field: 'route',
        message: `Tuyến "${route.name || route.id || ''}" chưa có tổng số km trong danh mục tuyến đường.`,
      });
    }

    const resolved = resolveFormula(source.store, source.vehicleTypes, source.cargoType);
    const terms = termsOf(resolved?.formula);
    if (!String(source.cargoType || '').trim()) {
      blockers.push({ field: 'cargoType', message: 'Chưa chọn loại xe nên chưa biết áp công thức nào.' });
    } else if (!resolved) {
      blockers.push({
        field: 'formula',
        message: `Loại xe "${source.cargoType}" chưa có công thức giá thành. Vào Dữ liệu gốc › Công thức giá thành để cấu hình.`,
      });
    } else if (!terms.some(term => term.rate > 0)) {
      blockers.push({
        field: 'formula',
        message: `Công thức của "${source.cargoType}" đang để mọi đơn giá bằng 0 nên tổng luôn bằng 0.`,
      });
    }

    const tonnes = parseTonnes(source.tonnes);
    if (needsWeight(terms)) {
      if (tonnes === null) {
        blockers.push({
          field: 'tonnes',
          message: 'Công thức có cước tính theo khối lượng hàng, nên phải nhập tải trọng mới ra giá.',
        });
      } else if (tonnes === 0 && !resolved?.formula?.expressions) {
        notes.push('Tải trọng đang là 0 tấn nên phần cước theo khối lượng bằng 0.');
      }
    }

    const stops = Math.max(1, Math.round(toNumber(source.stops)) || 1);
    let segments = route?.segments || [];
    try { if (route?.segments_json) segments = JSON.parse(route.segments_json); } catch { segments = []; }
    const expressions = resolved?.formula?.expressions;
    const uses = key => expressions && Object.values(expressions).some(e => new RegExp('\\b' + key + '\\b').test(e));
    if (uses('legs') && !segments.length && !source.legs) blockers.push({field:'legs',message:'Tuyến chưa có số chặng để tính công thức.'});
    if (uses('value') && source.value == null) blockers.push({field:'value',message:'Thiếu giá trị hàng để tính công thức.'});
    let result;
    try { result = FormulaModel.evaluate(terms, {
      km: routeKm,
      tonnes: tonnes === null ? 0 : tonnes,
      stops,
      legs: source.legs || segments.length || 1,
      value: source.value || 0,
    }, resolved?.formula?.expressions);
    } catch (error) {
      blockers.push({field:'formula',message:error.message});
      result = {rows:[]};
    }

    const ready = blockers.length === 0;
    return {
      ready,
      blockers,
      notes,
      formulaKey: resolved?.key || '',
      formulaName: resolved?.formula?.name || '',
      currency: resolved?.formula?.currency || source.currency || 'VND',
      km: routeKm,
      tonnes,
      stops,
      rows: result.rows,
      // Đầu vào còn thiếu thì KHÔNG trả về con số: bên gọi không thể vô tình
      // hiện một tổng tính thiếu ra như thể đó là giá thật.
      //
      // Ba con số tách rọi, không gộp: `cost` là tiền chi ra, `revenue` là cước
      // thu của khách. Cộng chúng lại thì ra một con số không phải giá thành
      // cũng không phải giá bán — đúng lỗi đã khiến màn báo giá hiện 4.461.200 đ
      // cho một chuyến mà giá thành là 861.200 đ và cước thu là 3.600.000 đ.
      cost: ready ? result.cost : null,
      revenue: ready ? result.revenue : null,
      profit: ready ? result.profit : null,
      marginPct: ready ? result.marginPct : null,
      perKm: ready ? result.perKm : null,
    };
  }

  return { toNumber, parseTonnes, resolveFormula, termsOf, needsWeight, price };
});

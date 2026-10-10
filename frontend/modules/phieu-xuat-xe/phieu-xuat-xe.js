/* Phiếu xuất xe đi vận chuyển — màn làm việc chính.
 *
 * Một phiếu, sáu mục. Người dùng nhập theo vai; mỗi mục có trạng thái duyệt riêng và nút hành
 * động theo vai (gửi kiểm · kiểm · trả lại · ghi sổ · chi). Máy chủ là nơi QUYẾT ĐỊNH quyền —
 * ở đây chỉ ẩn/hiện cho đỡ bấm nhầm, bấm sai thì máy chủ trả 403/409 và mình hiện thông báo.
 *
 * Phép tính tiền ở đây (tinh()) chép nguyên từ backend/app/services/tinh_toan.py để số nhảy
 * ngay khi gõ; sau khi Lưu, số của máy chủ (P.tinh) là số thật.
 */
(function () {

  const { API, NN, esc, so, AUTH, tag } = EPL;
  const MUC = ['info', 'trans', 'fuel', 'travel', 'repair', 'other'], MUC_CHI = ['fuel', 'travel', 'repair', 'other'];
  const COT_INFO = ['kind', 'company', 'owner_name', 'vehicle_id', 'brand_model', 'plate_head', 'plate_trailer', 'driver_id', 'doc_date', 'out_date', 'back_date', 'odo_out', 'odo_back'];
  const COT_TRANS = ['customer_id', 'route_id', 'goods_type', 'ore_bill_no', 'ore_bill_date', 'origin', 'destination', 'weight_origin', 'weight_dest', 'price', 'price_ccy', 'price_mode', 'hire_price', 'hire_ccy', 'fee_pct', 'over_limit_t', 'over_price'];
  // POD — biên bản giao nhận hàng (chốt 24/09): không thuộc mục nào, ghi được tới khi khoá phiếu
  const COT_POD = ['pod_no', 'pod_date', 'pod_receiver'];
  const SO = new Set(['odo_out', 'odo_back', 'weight_origin', 'weight_dest', 'price', 'hire_price', 'fee_pct', 'over_limit_t', 'over_price']);
  const QUYEN = {   // chép từ services/phan_quyen.py — chỉ để ẩn/hiện nút
    yard: { edit: MUC.filter(m => m !== 'repair'), verify: [], book: [], pay: [] },
    // Hai vai ở Thà Bốc (anh Khampla C1.2): thủ kho phụ tùng giữ kho, tổ sửa chữa nhập mục V.
    parts: { edit: [], verify: [], book: [], pay: [] },
    repair: { edit: ['repair'], verify: [], book: [], pay: [] },
    acct: { edit: [], verify: ['info', 'trans'], book: [], pay: [] },
    expacct: { edit: [], verify: ['travel', 'repair', 'other'], book: ['travel', 'repair', 'other'], pay: [] },
    fuel: { edit: [], verify: ['fuel'], book: ['fuel'], pay: [] },
    treasury: { edit: [], verify: [], book: [], pay: ['fuel'] },
    cash: { edit: [], verify: [], book: [], pay: ['travel', 'repair', 'other'] },
    rev: { edit: [], verify: [], book: [], pay: [] },
    admin: { edit: MUC, verify: MUC, book: MUC, pay: MUC },
  };
  let tab = 'all', tabTay = false;            // tab đang mở · người dùng đã tự chọn tab chưa
  const SO_LA_MA = ['I', 'II', 'III', 'IV', 'V', 'VI'];
  let LO = [];        // các lô hàng còn trong kho bãi, để phiếu giao chọn lấy từ đâu
  let root, P = null, DS = [], KM = null, DM = { customers: [], vehicles: [], drivers: [], routes: [], parts: [], places: [], the: [] }, moi = false, ty_gia = {};
  // Phiếu mới mà người lập TỰ GÕ số phiếu: đổi Gom / Giao không lấy số gợi ý đè lên nữa (rà 01/10 — trước đây bấm thẻ là mất số đã gõ)
  let soGoTay = false;
  /** Định khoản mặc định của một dòng chi — SOI GƯƠNG services/tai_khoan.dinh_khoan_dong (rà 30/09). Mã lấy từ máy chủ
   *  (KM.acct_rule), ở đây chỉ chọn vế: Nợ theo loại xe và mục; Có theo CÁCH TRẢ — lấy kho → kho · ghi nợ trạm / NCC / thẻ /
   *  sửa ngoài theo đợt (khoản mục NCC theo dõi nợ, KM.ncc_items) → phải trả NCC · sửa ngoài quỹ trả ngay → 1011 tiền mặt
   *  (06/10) · tiền mặt tài xế cầm đi → xe nhà 1601 tạm ứng nhân viên, xe thuê tiền mặt (ghi công nợ chủ
   *  xe) · trả cùng lương → phải trả nhân viên. Chủ xe tự chi thì không định khoản (''). */
  function tkMacDinh(m, d) {
    const R = KM.acct_rule, thue = P && P.company === 'joint';
    d = d || {};
    if (d.paid_by_epl === false) return '';
    let src = d.source;
    if (m === 'fuel') src = nguonCuaDiem(d);
    if (m === 'repair' && src !== 'kho') src = 'mua';
    const no = thue ? R.chu_xe : (m === 'repair' ? R.cp_sua : R.cp_di_lai);
    let co;
    if (src === 'kho') co = thue && m === 'fuel' ? R.ban_hang : R.kho;
    else if (d.ghi_no || d.toll_card_id || (m === 'repair' && !d.supplier_id && (KM.ncc_items || []).includes(d.item_key))) co = R.ncc;
    else if (m === 'repair') co = R.tien_mat;   // quỹ trả ngay mục V: phiếu chi «Chi khác» Nợ 614 (xe thuê 4022) / Có 1011
    else {
      let c = m === 'fuel' ? 'tien_mat' : (d.pay_channel || (KM.pay_default || {})[d.item_key] || 'tien_mat');
      if (thue && c === 'luong') c = 'tien_mat';
      co = c === 'ncc' ? R.ncc : c === 'luong' ? R.luong : (thue ? R.tien_mat : R.tam_ung);
    }
    return no + '/' + co;
  }
  /** Mã đang có hiệu lực: người dùng tự chọn (ngoài bộ mã máy đặt) thì giữ, còn lại theo luật — như TK.tk_dong. */
  const tkDong = (d) => (d.acct_code && !(KM.acct_rule.he_thong || []).includes(d.acct_code)) ? d.acct_code : tkMacDinh(d.section, d);
  /** Mã HIỆN của dòng (09/10, anh Khampla): như tkDong, nhưng mã theo luật thì thay bằng tài khoản riêng của nhà cung cấp trên dòng /
   *  chủ xe của phiếu (P.tk_rieng, máy chủ gửi — như services/tai_khoan.doi_cap). Lưu phiếu vẫn gửi tkDong (mã theo luật): gửi mã
   *  riêng thì máy chủ coi là mã tự chọn và ghim luôn trên dòng. */
  function tkHien(d) {
    const ma = tkDong(d);
    if (!ma || ma.indexOf('/') < 0 || (d.acct_code && !(KM.acct_rule.he_thong || []).includes(d.acct_code))) return ma;
    const R = KM.acct_rule, T = (P && P.tk_rieng) || {};
    // dòng ghi rõ nhà cung cấp → theo id; dòng chỉ mang khoản mục → nhà cung cấp theo dõi khoản đó (TK.ncc_cua_dong)
    const ncc = d.supplier_id ? (T.ncc || {})[d.supplier_id] : d.item_key ? (T.ncc_khoan || {})[d.item_key] : null, chu = T.chu_xe;
    let [no, co] = ma.split('/');
    if (ncc && co === R.ncc) {                       // chỉ dòng NỢ nhà cung cấp (Có 4021) — như doi_cap (soát 10/10)
      if (ncc.co) co = ncc.co;
      if ((no === R.cp_di_lai || no === R.cp_sua) && ncc.no) no = ncc.no;
    }
    if (chu && chu.co) { if (no === R.chu_xe) no = chu.co; if (co === R.chu_xe) co = chu.co; }
    return no + '/' + co;
  }
  /** Chữ khi rê chuột lên ô định khoản: tên hai vế; mã con của khách chưa mở bên kế toán thì nói rõ. */
  function tkTen(cap) {
    const T = KM.acct_rule.ten || {};
    return String(cap || '').split('/').map((ma, i) => {
      const x = T[ma];
      return NN.t(i ? 'acct_credit' : 'acct_debit') + ' ' + ma + (x ? ' · ' + (NN.lang === 'lo' ? x.lo : x.vi) + (x.trang_thai === 'ma_con_khach' ? ' (' + NN.t('acct_not_in_catalogue') + ')' : '') : '');
    }).join('\n');
  }
  const q = (s) => root.querySelector(s), g = (id) => root.querySelector('#' + id);
  const vai = () => AUTH.role;
  const perm = () => QUYEN[vai()] || QUYEN.yard;

  /* ---------------------------------------------------------------- tính tiền (mirror máy chủ) */
  /* Tỷ giá KHOÁ trên phiếu — bao nhiêu Kíp cho một đơn vị tiền đó. Soi gương services/tinh_toan.py. */
  function rate(ma) { return { USD: P.rate_usd || 22000, THB: P.rate_thb || 700, VND: P.rate_vnd || 1.2, CNY: P.rate_cny || 3000, LAK: 1 }[(ma || 'LAK').toUpperCase()] || 1; }
  const maCuoc = () => (P.price_ccy || 'USD').toUpperCase();
  const maThue = () => (P.hire_ccy || maCuoc()).toUpperCase();
  const khoan = () => (P.price_mode || 'ton') === 'chuyen';    // trọn chuyến: không nhân tấn
  const tronTien = (v, ma) => { const d = EPL.leTien(ma); return +(+v).toFixed(d); };
  const t2 = (v, ma) => EPL.tien(v, ma);
  // Xe thuê: dầu lấy từ kho là XUẤT BÁN cho chủ xe — thành tiền theo giá bán KT kho xăng dầu gõ (chép luật máy chủ, 29/09)
  // xe thuê: dầu (29/09) và phụ tùng (30/09) lấy KHO là xuất bán — tính theo giá bán cho chủ xe (soi gương tinh_toan.la_xuat_ban)
  const xuatBan = (d) => P.company === 'joint' && ((d.section === 'fuel' && nguonCuaDiem(d) === 'kho') || (d.section === 'repair' && d.source === 'kho'));
  const giaDong = (d) => (xuatBan(d) && d.sale_price != null && d.sale_price !== '') ? d.sale_price : d.unit_price;
  const tienDong = (d) => (EPL.doc(d.qty)) * (EPL.doc(giaDong(d))) * rate(d.currency);
  // giá vốn kho (30/09): thủ kho, tổ sửa chữa không thấy — máy chủ không gửi đơn giá dòng lấy kho và tổng chi
  const thayGiaKho = () => !['yard', 'driver', 'depot', 'parts', 'repair'].includes(vai());
  const anGia = (d) => !thayGiaKho() && d.source === 'kho';
  function tongMuc(m, chiUng = true) { return (P.expenses || []).filter(d => d.section === m && !(P.company === 'joint' && chiUng && !d.paid_by_epl)).reduce((a, d) => a + tienDong(d), 0); }
  function tinh() {
    const w = P.weight_dest != null && P.weight_dest !== '' ? EPL.doc(P.weight_dest) : EPL.doc(P.weight_origin);
    const ma = maCuoc(), rC = rate(ma);
    const gia = EPL.doc(P.price), dt = tronTien(khoan() ? gia : w * gia, ma);
    const chi = {}; MUC_CHI.forEach(m => { chi[m] = Math.round(tongMuc(m)); }); const tongChi = Object.values(chi).reduce((a, b) => a + b, 0);
    const hao = P.weight_origin && P.weight_dest != null && P.weight_dest !== '' ? (EPL.doc(P.weight_origin) - EPL.doc(P.weight_dest)) / EPL.doc(P.weight_origin) * 100 : null;
    const dtLak = Math.round(dt * rC);
    const k = { w, ma, rC, dt, dtLak, chi, tongChi, hao, lk: P.company === 'joint' };
    if (!k.lk) { k.laiLak = dtLak - tongChi; k.lai = tronTien(k.laiLak / rC, ma); return k; }
    // Xe liên kết: giá thuê có thể là tiền KHÁC với giá bán (bán USD, thuê xe Lào trả Kíp).
    const mh = maThue(), rH = rate(mh);
    k.mh = mh; k.rH = rH;
    const gt = P.hire_price != null && P.hire_price !== '' ? EPL.doc(P.hire_price) : gia * rC / rH;
    k.thue = tronTien(khoan() ? gt : w * gt, mh); k.phi = tronTien(k.thue * EPL.doc(P.fee_pct ?? 2) / 100, mh);
    k.vuot = Math.max(0, w - EPL.doc(P.over_limit_t ?? 40)); k.truVuot = tronTien(k.vuot * EPL.doc(P.over_price ?? 1), mh);
    k.ung = tronTien(tongChi / rH, mh); k.traChu = tronTien(k.thue - k.phi - k.truVuot - k.ung, mh);
    k.laiLak = dtLak - Math.round(k.thue * rH); k.lai = tronTien(k.laiLak / rC, ma); k.gt = gt;
    return k;
  }

  /* ---------------------------------------------------------------- vẽ */
  /** 50 phiếu mới nhất, hoặc kết quả tìm trên toàn bộ phiếu nếu ô tìm có chữ. DS.tong = tổng số khớp (header X-Tong). */
  async function napDs() {
    const t = (g('px-tim') && g('px-tim').value.trim()) || '';
    DS = await API.get('/api/trips?co=50' + (t ? '&q=' + encodeURIComponent(t) : ''));
    return DS;
  }
  /** Các dòng của ô chọn — phiếu đang mở luôn có mặt, kể cả khi nó không nằm trong 50 phiếu vừa nạp. */
  function dongChon() {
    const ds = P && P.id && !DS.some(p => p.id === P.id) ? [P, ...DS] : DS;
    return ds.map(p => `<option value="${p.id}" ${P && p.id === P.id ? 'selected' : ''}>${esc(p.doc_no)} · ${esc(p.truck_no || '')}${p.company === 'joint' ? ' · ' + NN.t('co_joint') : ''}</option>`).join('')
      + (DS.tong > DS.length ? `<option value="" disabled>… ${so(DS.length)} / ${so(DS.tong)}${DS.tongTran ? '+' : ''}</option>` : '');
  }
  function veChon() {
    g('px-chon').innerHTML = (moi ? `<option value="">— ${NN.t('new_slip')} —</option>` : '') + dongChon();
    if (moi) g('px-chon').value = '';
  }
  function veDanhMuc() {
    g('f-vehicle_id').innerHTML = `<option value="">—</option>` + DM.vehicles.filter(x => x.active || x.id === P.vehicle_id).map(x => `<option value="${x.id}" ${x.id === P.vehicle_id ? 'selected' : ''} data-tim="${esc([x.plate_trailer, x.brand_model, x.owner_name].filter(Boolean).join(' '))}">${esc(x.truck_no)} · ${esc(x.plate_head || '')}${x.owner_type === 'joint' ? ' · ' + NN.t('co_joint') : ''}</option>`).join('');
    g('f-driver_id').innerHTML = `<option value="">—</option>` + DM.drivers.filter(x => x.active || x.id === P.driver_id).map(x => `<option value="${x.id}" ${x.id === P.driver_id ? 'selected' : ''} data-tim="${esc([x.driver_code, x.phone].filter(Boolean).join(' '))}">${esc(EPL.tenTaiXe(x))}</option>`).join('');
    root.querySelectorAll('[data-loc]').forEach(inp => locChon(inp, false));   // ô tìm còn chữ thì lọc lại danh sách vừa dựng
    g('f-route_id').innerHTML = `<option value="">—</option>` + DM.routes.filter(x => x.active || x.id === P.route_id).map(x => `<option value="${x.id}" ${x.id === P.route_id ? 'selected' : ''}>${esc(x.name)} · ${so(x.total_km, 1)} km${x.return_km ? ' · ↩ ' + so(x.return_km, 1) + ' km' : ''}</option>`).join('');
    g('f-customer_id').innerHTML = `<option value="">—</option>` + DM.customers.filter(x => x.active || x.id === P.customer_id).map(x => `<option value="${x.id}" ${x.id === P.customer_id ? 'selected' : ''}>${esc(x.name)}</option>`).join('');
  }
  /* Ô tìm trên ô chọn xe / tài xế (anh Khampla 08/10: hơn 500 xe, ô chọn dài không tìm nổi). Gõ số xe, biển, hiệu xe, chủ xe /
   * tên, mã, điện thoại tài xế (không cần dấu) → ô chọn chỉ còn dòng khớp; khớp đúng một dòng thì chọn luôn (`chon`) — EPL.locChon.
   * Ô chọn khoá (mục I đã gửi / đã kiểm) thì giấu ô tìm. */
  const locChon = (inp, chon) => EPL.locChon(g(inp.dataset.loc), inp.value, chon, inp);
  function xoaTim() { root.querySelectorAll('[data-loc]').forEach(inp => { inp.value = ''; }); }
  function doTruong() {
    g('px-doc-no').value = P.doc_no || '';
    [...COT_INFO, ...COT_TRANS, ...COT_POD].forEach(c => { const el = g('f-' + c); if (!el) return; el.value = P[c] == null ? '' : P[c]; });
    q('#px-phieu').classList.toggle('is-joint', P.company === 'joint');
  }
  function veSo() {
    const k = tinh();
    g('v-odo_km').textContent = P.odo_out && P.odo_back ? so(Math.abs(EPL.doc(P.odo_back) - EPL.doc(P.odo_out))) : '—';
    // Km về ước tính = km lúc đi + km tuyến — để kế toán đối với km về thật ở bước kiểm lại
    const tuyen = (DM.routes || []).find(x => x.id === P.route_id);
    // km về ước tính = lúc đi + chiều đi + chiều về (tuyến có xe quay lại điểm đi — 29/09)
    const kmCa = tuyen ? EPL.doc(tuyen.total_km) + EPL.doc(tuyen.return_km || 0) : 0;
    g('v-odo_est').textContent = P.odo_out && kmCa ? so(EPL.doc(P.odo_out) + kmCa) : '—';
    g('v-hao').innerHTML = k.hao === null ? '—' : `${so(EPL.doc(P.weight_origin) - EPL.doc(P.weight_dest), 2)} t <span class="${k.hao > 1.5 ? 'neg' : 'muted'}">(${k.hao.toFixed(1)}%)</span>`;
    g('v-val-usd').textContent = t2(k.dt, k.ma); g('v-val-lak').textContent = k.ma === 'LAK' ? '—' : t2(k.dtLak, 'LAK');
    if (k.lk) { g('v-hire').textContent = t2(k.thue, k.mh); g('v-fee').textContent = '− ' + t2(k.phi, k.mh); g('v-over-t').textContent = so(k.vuot, 2) + ' t'; g('v-over').textContent = '− ' + t2(k.truVuot, k.mh); }
    // chỉ dòng có data-i — dòng "chưa có dữ liệu" không phải dòng chi
    MUC_CHI.forEach(m => { const tb = q(`table[data-bang="${m}"]`); tb.querySelectorAll('tbody tr[data-i]').forEach(tr => { const d = P.expenses[+tr.dataset.i]; if (d) tr.querySelector('.amt').textContent = anGia(d) ? '—' : so(tienDong(d)); });
      tb.querySelector('tfoot').innerHTML = dongTong(tb, m, k); });
    veBenTien(k);
    const box = g('px-tong-ket');
    if (!thayGiaKho()) {
      box.innerHTML = '';
    } else if (!thayTienBan()) {
      // vai không thấy tiền bán: máy chủ không gửi cước, giá thuê — chỉ tổng chi, không hiện doanh thu 0 / lãi sai
      box.innerHTML = `<div class="px-tong"><div class="o"><div class="l">${NN.h('sum_exp')}</div><div class="v">${so(k.tongChi)}<small>LAK</small></div></div></div>`;
    } else if (!k.lk) {
      const net = k.laiLak, phu = (v) => k.ma === 'LAK' ? 'LAK' : `LAK · ${t2(tronTien(v / k.rC, k.ma), k.ma)}`;
      box.innerHTML = `<div class="px-tong"><div class="o"><div class="l">${NN.h('sum_rev')}</div><div class="v">${so(k.dtLak)}<small>${phu(k.dtLak)}</small></div></div>
        <div class="o"><div class="l">${NN.h('sum_exp')}</div><div class="v">${so(k.tongChi)}<small>${phu(k.tongChi)}</small></div></div>
        <div class="o net"><div class="l">${NN.h('sum_net')}</div><div class="v">${net < 0 ? '−' : ''}${so(Math.abs(net))}<small>${phu(Math.abs(net))}</small></div></div></div>`;
    } else {
      const r = (l, d, v, cls = '') => `<div class="r ${cls}"><span>${l}${d ? `<small>${d}</small>` : ''}</span><span>${v}</span></div>`;
      box.innerHTML = `<div class="px-tt"><div class="o"><b>${NN.h('settle_title')}</b>
        ${r(NN.h('st_hire'), khoan() ? NN.t('pm_chuyen') : `${t2(k.gt, k.mh)}/t × ${so(k.w, 2)} t`, t2(k.thue, k.mh))}
        ${r(NN.h('st_fee'), `${EPL.doc(P.fee_pct ?? 2)}% × ${so(k.thue, EPL.leTien(k.mh))}`, '− ' + t2(k.phi, k.mh), 'neg')}
        ${r(NN.h('st_over'), `${so(k.vuot, 2)} t × ${t2(EPL.doc(P.over_price ?? 1), k.mh)}`, '− ' + t2(k.truVuot, k.mh), 'neg')}
        ${r(NN.h('st_adv'), `${so(k.tongChi)} LAK ÷ ${so(k.rH)}`, '− ' + t2(k.ung, k.mh), 'neg')}
        ${r(NN.h('st_net_owner'), k.mh === 'LAK' ? '' : `≈ ${so(k.traChu * k.rH)} LAK`, t2(k.traChu, k.mh), 'tot')}</div>
        <div class="o"><b>${NN.h('trip_profit')}</b>
        ${r(NN.h('do_money'), khoan() ? NN.t('pm_chuyen') : `${t2(EPL.doc(P.price), k.ma)}/t × ${so(k.w, 2)} t`, t2(k.dt, k.ma))}
        ${r(NN.h('st_hire'), k.mh === k.ma ? '' : t2(k.thue, k.mh), '− ' + t2(tronTien(k.thue * k.rH / k.rC, k.ma), k.ma), 'neg')}
        ${r(NN.h('trip_profit'), `≈ ${so(k.laiLak)} LAK · ${k.dt ? so(k.lai / k.dt * 100, 1) : 0}%`, t2(k.lai, k.ma), 'tot')}</div></div>
        <p class="small muted">${NN.h('settle_ex')}</p>`;
    }
  }
  /** Dòng tổng dưới bảng chi — dựng theo ĐÚNG từng ô đầu cột (cùng lớp px-gia · px-lk · no-print), để cột ẩn theo vai
   *  hay theo loại xe thì ô tổng ẩn theo. Trước đây đếm cột bằng tay: xe thuê thiếu một ô (nền xám hụt ở cột cuối), Bãi
   *  thừa ba ô (bảng mọc cột trống bên phải) — rà 01/10. */
  function dongTong(tb, m, k) {
    const coGiaKho = P.expenses.some(d => d.section === m && anGia(d));
    return '<tr>' + [...tb.querySelectorAll('thead th')].map((th, i) => {
      const khoa = th.dataset.i18n;
      const v = i === 1 ? NN.h('total')
        : khoa === 'qty_l' ? so(P.expenses.filter(d => d.section === m).reduce((a, d) => a + EPL.doc(d.qty), 0))
        : khoa === 'amount_lak' ? `<b>${coGiaKho ? '—' : so(k.chi[m])}</b>` : '';
      return `<td${th.className ? ` class="${th.className}"` : ''}>${v}</td>`;
    }).join('') + '</tr>';
  }
  /* ---------------------------------------------------------------- dòng hàng (hai DO)
   * DO gom: hàng bốc ở mỏ. DO giao: hàng lấy từ kho bãi, phải chỉ rõ lấy của lô nào (chính là DO gom
   * đã mang lô đó về) — đây là dây nối hai phiếu. Dòng "hao hụt" do máy ghi, người không sửa. */
  const laGom = () => (P.kind || 'giao') === 'gom';
  // Phiếu GOM đã về bãi là hàng đã vào kho: dòng hàng và hai ô cân đóng lại — cùng luật với máy chủ
  // (HANG_DA_NHAP_KHO). Sổ kho đã ghi theo số đó, sửa phiếu mà không sửa sổ là hai bên nói hai số.
  const daNhapKho = () => laGom() && !moi && P.transport_status === 'arrived';
  // Phiếu GOM một mặt hàng (chủ dự án 29/09): không còn bảng "Hàng trên phiếu" — Loại hàng + Cân tại mỏ là đủ, máy chủ tự
  // ghi dòng hàng. Phiếu gom đã có từ hai dòng hàng trở lên (phiếu cũ) thì vẫn hiện bảng để sửa từng dòng.
  const gomMotDong = () => laGom() && (P.goods || []).filter(x => x.loai !== 'hao_hut').length <= 1;
  function veHang() {
    const tb = q('#px-hang tbody'), khoaDuoc = suaDuoc('trans') && !daNhapKho();
    const dong = (P.goods || []);
    tb.innerHTML = dong.length ? dong.map((g, i) => {
      if (g.loai === 'hao_hut') return `<tr class="hao"><td>${esc(g.goods_name)}</td><td class="px-tu-lo"></td>
        <td class="num">${so(g.qty_t, 2)}</td><td class="small muted">${esc(g.note || NN.t('w_loss'))}</td><td class="no-print"></td></tr>`;
      const lo = LO.filter(x => x.con_t > 0 || x.lo_trip_id === g.tu_phieu_id);
      return `<tr data-i="${i}">
        <td><input data-i="${i}" data-f="goods_name" value="${esc(g.goods_name || '')}" lang="lo" ${khoaDuoc ? '' : 'disabled'}></td>
        <td class="px-tu-lo"><select data-i="${i}" data-f="tu_phieu_id" ${khoaDuoc ? '' : 'disabled'}>
          <option value="">—</option>${lo.map(x => `<option value="${x.lo_trip_id}" ${x.lo_trip_id === g.tu_phieu_id ? 'selected' : ''}>${esc(x.doc_no)} · ${so(x.con_t, 2)} t</option>`).join('')}</select></td>
        <td><input class="num" data-i="${i}" data-f="qty_t" value="${esc(g.qty_t ?? '')}" inputmode="decimal" ${khoaDuoc ? '' : 'disabled'}></td>
        <td><input data-i="${i}" data-f="note" value="${esc(g.note || '')}" ${khoaDuoc ? '' : 'disabled'}></td>
        <td class="no-print">${khoaDuoc ? `<button type="button" class="x" data-xoa-hang="${i}">×</button>` : ''}</td></tr>`;
    }).join('') : `<tr><td colspan="5" class="empty">${NN.h('no_goods_line')}</td></tr>`;
    q('#px-hang-them').hidden = !khoaDuoc;
    q('.px-hang-o').hidden = gomMotDong();
    g('px-can-mo-nhac').hidden = !laGom() || daNhapKho();
    q('#px-hang-nhac').innerHTML = NN.h(daNhapKho() ? 'goods_locked_gom' : laGom() ? 'goods_hint_gom' : 'goods_hint_giao');
    tb.querySelectorAll('input, select').forEach(el => el.addEventListener('input', () => {
      const g = P.goods[+el.dataset.i]; if (!g) return;
      g[el.dataset.f] = el.dataset.f === 'qty_t' ? EPL.doc(el.value) : el.value;
      if (el.dataset.f === 'qty_t') { const t = (P.goods || []).filter(x => x.loai !== 'hao_hut').reduce((a, x) => a + EPL.doc(x.qty_t), 0); P.weight_origin = t; g0('f-weight_origin', t); veSo(); }
    }));
    tb.querySelectorAll('[data-xoa-hang]').forEach(b => b.addEventListener('click', () => { P.goods.splice(+b.dataset.xoaHang, 1); veHang(); }));
  }
  const g0 = (id, v) => { const el = g(id); if (el) el.value = v; };

  function veChi() {
    const lk = P.company === 'joint';
    MUC_CHI.forEach(m => {
      const tb = q(`table[data-bang="${m}"] tbody`), khoa = KM.items[m], khoaDuoc = suaDuoc(m);
      const dong = P.expenses.map((d, i) => ({ d, i })).filter(x => x.d.section === m);
      tb.innerHTML = dong.length ? dong.map(({ d, i }, n) => {
        // khoản đã ngưng ở màn Khoản mục chi phí (08/10) mà dòng cũ còn mang: vẫn có trong ô chọn của dòng đó, không thành "Khác (tự gõ)"
        const kl = d.item_key && !khoa.includes(d.item_key) && ((KM.all_items || {})[m] || []).includes(d.item_key) ? [...khoa, d.item_key] : khoa;
        const tuGo = !kl.includes(d.item_key);
        const sel = `<select data-i="${i}" data-f="item_key" ${khoaDuoc ? '' : 'disabled'}>${kl.map(k => `<option value="${k}" ${k === d.item_key ? 'selected' : ''}>${esc(NN.t(k))}</option>`).join('')}<option value="" ${tuGo ? 'selected' : ''}>${esc(NN.t('x_custom'))}</option></select>${tuGo ? `<input data-i="${i}" data-f="item_name" value="${esc(d.item_name || '')}" placeholder="…" ${khoaDuoc ? '' : 'disabled'} style="margin-top:4px">` : ''}`;
        const giaMo = giaDuoc(m, d);
        const inp = (f, cls = 'num') => f === 'unit_price'
          ? `<input class="${cls}${giaMo && d.paid_by_epl && EPL.doc(d.qty) > 0 && !EPL.doc(d.unit_price) ? ' px-can-gia' : ''}" data-i="${i}" data-f="${f}" value="${esc(d[f] == null ? '' : d[f])}" ${giaMo ? '' : 'disabled'} inputmode="decimal" title="${esc(nguonKho(m, d) ? NN.t('price_avg_kho') : '')}">`
          : `<input class="${cls}" data-i="${i}" data-f="${f}" value="${esc(d[f] == null ? '' : d[f])}" ${khoaDuoc ? '' : 'disabled'} inputmode="decimal">`;
        // Phí cầu đường (C6.1): trả bằng THẺ nào. Thẻ bị trừ khi kế toán ghi sổ mục IV, nên chọn rồi
        // vẫn đổi được tới lúc đó; đã trừ rồi thì khoá lại và nói rõ.
        const theDuoc = m === 'travel' && ['x_toll', 'x_bridge'].includes(d.item_key);
        const daTru = !!d.card_move_id;
        // ô thẻ / cách trả bọc trong <div>: Excel đọc ô này thành hai dòng "khoản · cách trả", không dính liền một chữ (01/10)
        const theSel = !theDuoc ? '' : `<div><select data-i="${i}" data-f="toll_card_id" ${khoaDuoc && !daTru ? '' : 'disabled'} style="margin-top:4px">
            <option value="">${esc(NN.t('tct_tien_mat'))}</option>${DM.the.filter(t => t.active || t.id === d.toll_card_id)
              .map(t => `<option value="${t.id}" ${t.id === d.toll_card_id ? 'selected' : ''}>${esc(t.card_no)} · ${so(t.balance, EPL.leTien(t.currency))} ${esc(t.currency)}</option>`).join('')}</select></div>${
            daTru ? `<div class="small muted">${esc(NN.t('tct_da_tru'))} ✓</div>` : ''}`;
        // CÁCH TRẢ (Excel anh Khampla, 29/09): như cột ghi chú của tờ Excel — chi ngay khi xe đi (vào tạm ứng) · trả cùng
        // lương · nợ nhà cung cấp. Dòng phí cao tốc / cầu đường đã có ô thẻ ở trên (tiền mặt hay thẻ) nên không hỏi thêm.
        // Admin Thà Bốc KHÔNG thấy ô cách trả (anh Khampla 08/10 — không phải việc của người lập phiếu); vai khác thấy, KT Chi phí VC đổi
        const caDuoc = (m === 'travel' || m === 'other') && !theDuoc && thayChi();
        // Xe THUÊ không có "trả cùng lương" — EPL không trả lương tài xế của chủ xe; khoản EPL ứng là tạm ứng ghi công nợ chủ
        // xe (chủ dự án 30/09, chép luật máy chủ): chỉ còn "chi ngay khi xe đi" và "nợ NCC".
        const caMoc = d.pay_channel || ((KM.pay_default || {})[d.item_key] || 'tien_mat');
        const caEff = lk && caMoc === 'luong' ? 'tien_mat' : caMoc;
        // 08/10 (anh Khampla): Bãi — người lập phiếu — KHÔNG chọn cách trả; dòng mang mặc định (bộ gợi ý tuyến · khoản mục), KT Chi phí
        // VC đổi lúc kiểm mục, Sếp lúc nào cũng được. Máy chủ cũng bỏ qua cách trả vai khác gửi lên (phan_quyen.doi_cach_tra).
        const caSel = !caDuoc ? '' : `<div><select class="px-ca" data-i="${i}" data-f="pay_channel" ${caDoiDuoc(m) ? '' : `disabled title="${esc(NN.t('px_ca_kt'))}"`} style="margin-top:4px">${
          [['tien_mat', 'pm_on_dispatch'], ['luong', 'pm_trip_salary'], ['ncc', 'pm_supplier']].filter(([v]) => !(lk && v === 'luong')).map(([v, k]) => `<option value="${v}" ${v === caEff ? 'selected' : ''}>${esc(NN.t(k))}</option>`).join('')}</select></div>`;
        // .px-xuat: chữ ẩn cho Excel — xuat.js bỏ qua nút bấm, không có dòng này thì cột "Ai chi", "Mã kế toán" ra trống (01/10)
        // Xe thuê: dầu / phụ tùng LẤY KHO EPL luôn là xuất bán cho chủ xe (chủ dự án 30/09, nhắc lại 02/10) — không chọn được
        // "chủ xe tự trả" (máy chủ cũng chặn); dòng cũ còn ghi vậy thì người gõ giá bán (KT kho xăng dầu / KT Chi phí) bấm "EPL ứng"
        const khoXeThue = lk && (m === 'fuel' ? nguonCuaDiem(d) === 'kho' : m === 'repair' && d.source === 'kho');
        const eplDuoc = khoaDuoc || (khoXeThue && !d.paid_by_epl && suaTienDuoc(m));
        const pay = `<td class="px-lk"><span class="px-xuat" aria-hidden="true">${esc(NN.t(d.paid_by_epl ? 'pay_epl' : 'pay_own'))}</span><span class="px-pay"><button type="button" class="${d.paid_by_epl ? 'on' : ''}" data-i="${i}" data-pay="1" ${eplDuoc ? '' : 'disabled'}>${esc(NN.t('pay_epl'))}</button><button type="button" class="${!d.paid_by_epl ? 'on' : ''}" data-i="${i}" data-pay="0" ${khoaDuoc && !khoXeThue ? '' : 'disabled'}${khoXeThue ? ` title="${esc(NN.t('pay_kho_xe_thue'))}"` : ''}>${esc(NN.t('pay_own'))}</button></span></td>`;
        const tkd = tkHien(d);
        // xuất bán (02/10): mã máy đặt 4022/707 không còn là bút toán — phần bán thành SO nhiên liệu, chỉ giá vốn 607/1371.
        // Người dùng tự chọn mã khác (ngoài tập hệ thống) thì vẫn hiện mã đó.
        const xb = xuatBan(d) && tkd && !(d.acct_code && !(KM.acct_rule.he_thong || []).includes(d.acct_code));
        const acct = `<td class="px-gia">${tkd ? `<span class="px-xuat" aria-hidden="true">${esc(xb ? NN.t('px_tk_xb') + ' · ' + NN.t('px_tk_gv') : tkd)}</span>` : ''}<button type="button" class="acct px-acct${xb ? ' px-acct-xb' : ''}" data-acct="${i}" ${AUTH.la('acct', 'fuel', 'rev') && tkd && guiMuc(m) ? '' : 'disabled'} title="${esc(xb ? NN.t('px_tk_xb_t') : tkd ? tkTen(tkd) : NN.t('pay_own'))}">${xb ? `${NN.h('px_tk_xb')}<small>${NN.h('px_tk_gv')}</small>` : esc(tkd || '—')}</button></td>`;
        const xoa = `<td class="no-print">${khoaDuoc ? `<button type="button" class="x" data-xoa="${i}" title="${esc(NN.t('delete'))}">×</button>` : ''}</td>`;
        if (m === 'fuel') {
          // Đổ dầu ở trạm ngoài (nhất là bên Việt Nam): tài xế trả tiền mặt, hay TRẠM GHI NỢ để cuối
          // tháng EPL trả / cấn trừ với khách (C5.1). Chỉ hỏi khi nơi đổ là trạm ngoài.
          const muaNgoai = nguonCuaDiem(d) !== 'kho';
          // chưa tích thì Excel bỏ qua chữ "Ghi nợ tại trạm" (lớp xuat-bo) — không thì tệp ghi như thể trạm có ghi nợ
          const noSel = !muaNgoai ? '' : `<label class="px-ghino small${d.ghi_no ? '' : ' xuat-bo'}"><input type="checkbox" data-i="${i}" data-f="ghi_no" ${d.ghi_no ? 'checked' : ''} ${khoaDuoc ? '' : 'disabled'}> ${esc(NN.t('ncc_ghi_no'))}</label>`;
          // Xe thuê, dầu KHO, EPL ứng = xuất bán cho chủ xe: ô GIÁ BÁN dưới giá vốn bình quân — KT kho xăng dầu gõ khi kiểm
          // mục III (29/09). Vai không thấy tiền bán thì máy chủ không gửi ô này → không hiện.
          const banDuoc = lk && !muaNgoai && d.paid_by_epl;
          const giaBanMo = banDuoc && thayChi() && suaTienDuoc('fuel');
          const ban = !(banDuoc && ('sale_price' in d || giaBanMo)) ? '' : `<div class="px-ban"><div class="small muted">${NN.h('sale_price')}</div><div><input class="num${giaBanMo && EPL.doc(d.qty) > 0 && !EPL.doc(d.sale_price) ? ' px-can-gia' : ''}" data-i="${i}" data-f="sale_price" value="${esc(d.sale_price == null ? '' : d.sale_price)}" ${giaBanMo ? '' : 'disabled'} inputmode="decimal"></div></div>`;
          return `<tr data-i="${i}" class="${lk && !d.paid_by_epl ? 'own' : ''}"><td>${n + 1}</td><td>${sel}</td><td>${inp('qty')}</td><td class="px-gia">${inp('unit_price')}${ban}</td>
          <td class="px-gia"><select data-i="${i}" data-f="currency" ${giaMo ? '' : 'disabled'}>${['LAK', 'VND', 'THB', 'USD'].map(c => `<option ${c === d.currency ? 'selected' : ''}>${c}</option>`).join('')}</select></td><td class="num amt px-gia"></td>
          <td><select data-i="${i}" data-f="place_id" ${khoaDuoc ? '' : 'disabled'}>${diemChon(d)}</select>
            <div class="small muted px-nguon">${NN.h(nguonCuaDiem(d) === 'kho' ? 'src_kho' : 'src_mua')}</div>${nguonCuaDiem(d) === 'kho' ? xkChip(d) : ''}${noSel}</td>${pay}${acct}${xoa}</tr>`;
        }
        let nguon = '', banMucV = '';
        if (m === 'repair') {
          const kho = d.source === 'kho', daXuat = !!d.stock_move_id;
          // Xe thuê, phụ tùng KHO, EPL ứng = xuất bán cho chủ xe (30/09): ô GIÁ BÁN — KT Chi phí gõ khi kiểm mục V.
          const banPt = lk && kho && d.paid_by_epl, giaBanMoPt = banPt && thayChi() && suaTienDuoc('repair');
          banMucV = !(banPt && ('sale_price' in d || giaBanMoPt)) ? '' : `<div class="px-ban"><div class="small muted">${NN.h('sale_price')}</div><div><input class="num${giaBanMoPt && EPL.doc(d.qty) > 0 && !EPL.doc(d.sale_price) ? ' px-can-gia' : ''}" data-i="${i}" data-f="sale_price" value="${esc(d.sale_price == null ? '' : d.sale_price)}" ${giaBanMoPt ? '' : 'disabled'} inputmode="decimal"></div></div>`;
          nguon = `<td><select data-i="${i}" data-f="source" ${khoaDuoc && !daXuat ? '' : 'disabled'}><option value="mua" ${!kho ? 'selected' : ''}>${esc(NN.t('src_mua'))}</option><option value="kho" ${kho ? 'selected' : ''}>${esc(NN.t('src_kho'))}</option></select>${
            kho ? `<select data-i="${i}" data-f="part_id" ${khoaDuoc && !daXuat ? '' : 'disabled'} style="margin-top:4px"><option value="">—</option>${DM.parts.map(p => `<option value="${p.id}" ${p.id === d.part_id ? 'selected' : ''}>${esc(p.name)} · ${so(p.qty)}</option>`).join('')}</select>` : ''}${
            daXuat ? `<div class="small muted">${esc(NN.t('fs_out'))} ✓</div>` : ''}${kho ? xkChip(d) : ''}</td>`;
        }
        return `<tr data-i="${i}" class="${lk && !d.paid_by_epl ? 'own' : ''}"><td>${n + 1}</td><td>${sel}${theSel}${caSel}</td>${nguon}<td>${inp('qty')}</td><td class="px-gia">${inp('unit_price')}${banMucV}</td><td class="num amt px-gia"></td>${pay}${acct}${xoa}</tr>`;
      }).join('') : `<tr><td colspan="10" class="empty small">${NN.h('no_data')}</td></tr>`;
    });
    // dòng bản chất ở đầu mục III, IV: nội bộ (xe nhà) · xuất bán / ghi công nợ chủ xe (xe thuê) — 29/09
    root.querySelectorAll('.px-ht').forEach(el => { el.innerHTML = EPL.banChat(el.dataset.ht, EPL.maBanChat(el.dataset.ht, P.company), P.owner_name); });
    // 02/10 — mục có dòng lấy kho: một câu nói rõ lấy kho là gì với loại xe này (nội bộ → chi phí chuyến · xuất bán → công nợ đối tác)
    root.querySelectorAll('.px-xk-y').forEach(el => {
      const m = el.dataset.xk, co = (P.expenses || []).some(d => d.section === m && nguonKho(m, d));
      el.hidden = !co;
      const so = P.company === 'joint' && SO_NL[P.id] && SO_NL[P.id].trang_thai;
      el.innerHTML = co ? NN.h(P.company === 'joint' ? 'px_xk_y_ban_' + m : 'px_xk_y_noi_' + m)
        + (so ? ` <span class="px-xk-so">${so.status === 'synced' && so.order_code ? NN.h('px_so_nl_co', { so: so.order_code })
          : NN.h(so.status === 'synced' ? 'px_so_nl_co' : 'px_so_nl_loi', { so: so.order_code || '' })}</span>` : '') : '';
    });
    napSoNL();
    q('#px-phieu').querySelectorAll('.px-chi [data-f]').forEach(el => el.addEventListener('input', e => {
      const d = P.expenses[+el.dataset.i], f = el.dataset.f; d[f] = el.value; delete d._goiY;   // người lập đã sửa → không còn là dòng gợi ý
      if (f === 'item_key') { if (el.value === '') d.item_name = d.item_name || ''; else d.item_name = null; if (!['x_toll', 'x_bridge'].includes(el.value)) d.toll_card_id = null; d.pay_channel = null; veChi(); }
      if (f === 'toll_card_id') { d.toll_card_id = el.value || null; veChi(); }
      if (f === 'ghi_no') { d.ghi_no = el.checked; veChi(); }
      if (f === 'pay_channel') veChi();
      if (f === 'place_id') {
        // Nơi đổ quyết định LẤY KHO hay MUA NGOÀI, kéo theo vế Có của định khoản (kho · tạm ứng · nhà cung cấp).
        d.source = nguonCuaDiem(d);
        if (P.company === 'joint') d.paid_by_epl = d.source === 'kho';
        d.acct_code = null; veChi();
      }
      if (f === 'source') { if (el.value !== 'kho') d.part_id = null; else if (P.company === 'joint') d.paid_by_epl = true; d.acct_code = null; veChi(); }
      if (f === 'part_id') { const p = DM.parts.find(x => x.id === el.value); if (p) { d.item_key = null; d.item_name = p.name; if (thayGiaKho()) d.unit_price = p.unit_price || 0; else delete d.unit_price; } veChi(); }
      veSo();
    }));
    root.querySelectorAll('.px-chi [data-pay]').forEach(b => b.addEventListener('click', () => { P.expenses[+b.dataset.i].paid_by_epl = b.dataset.pay === '1'; veChi(); veSo(); }));
    root.querySelectorAll('.px-chi [data-xoa]').forEach(b => b.addEventListener('click', () => { P.expenses.splice(+b.dataset.xoa, 1); veChi(); veSo(); }));
    root.querySelectorAll('.px-chi [data-acct]').forEach(b => b.addEventListener('click', async () => {
      const d = P.expenses[+b.dataset.acct]; const v = await EPL.chonDinhKhoan(tkHien(d));
      if (v) { d.acct_code = v; veChi(); }
    }));
    veSo();
  }
  const VAI_SAU_KHOA = ['acct', 'expacct', 'rev', 'treasury', 'cash', 'fuel', 'admin'];
  const biKhoa = () => !moi && P.locked && !VAI_SAU_KHOA.includes(vai());
  // Phiếu mới cũng theo bảng quyền (01/10): Bãi lập phiếu nhưng KHÔNG nhập mục V (tổ sửa chữa nhập) — trước đây phiếu mới mở
  // hết sáu mục, Bãi thêm dòng sửa chữa rồi Lưu thì máy chủ chặn cả phiếu ("Mục repair đã khoá").
  function suaDuoc(m) { if (moi) return vai() === 'admin' || perm().edit.includes(m); if (biKhoa()) return false; const st = (P.sections || {})[m] || 'wait'; return vai() === 'admin' || (perm().edit.includes(m) && (st === 'wait' || st === 'entered')); }
  // Ô tiền của mục II (đơn giá, giá thuê, phí, ngưỡng): Bãi không thấy → người KIỂM mục II sửa được khi khác hợp đồng (chép luật máy chủ)
  const COT_TIEN = ['price', 'price_ccy', 'price_mode', 'hire_price', 'hire_ccy', 'fee_pct', 'over_limit_t', 'over_price'];
  // Số và ngày phiếu quặng: kế toán nhập KHI NHẬN GIẤY (anh Khampla, C3.7). Bãi thấy nhưng chỉ đọc, kể cả lúc lập phiếu.
  const COT_KE_TOAN = ['ore_bill_no', 'ore_bill_date'];
  function suaKeToanDuoc(m) { if (biKhoa()) return false; const st = moi ? 'wait' : ((P.sections || {})[m] || 'wait'); return vai() === 'admin' || (perm().verify.includes(m) && (st === 'wait' || st === 'entered')); }
  function suaTienDuoc(m) { if (moi) return true; if (biKhoa()) return false; const st = (P.sections || {})[m] || 'wait'; return vai() === 'admin' || (perm().verify.includes(m) && (st === 'wait' || st === 'entered')); }
  // Tiền CHI (anh Khampla A2 · C5.1): Bãi và tài xế không thấy, không nhập đơn giá. Người KIỂM mục nhập giá khi
  // mục còn "đã nhập"; dòng lấy từ kho thì giá là bình quân của kho, không ai gõ tay (C5.3). Chép luật máy chủ.
  const thayChi = () => vai() !== 'yard';
  const nguonKho = (m, d) => (m === 'fuel' && nguonCuaDiem(d) === 'kho') || (m === 'repair' && d.source === 'kho');
  /** SO nhiên liệu của DO xe thuê có dòng xuất bán (GET /api/trips/{id}/tao-so → nhien_lieu, chỉ đọc, không gọi mạng) — một lần mỗi
   *  phiếu, chỉ vai thấy tiền bán; đọc xong vẽ lại dòng nghĩa ở đầu mục III / V. */
  const SO_NL = {};
  async function napSoNL() {
    if (!P || !P.id || moi || P.company !== 'joint' || P.id in SO_NL || !thayTienBan()) return;
    if (!(P.expenses || []).some(d => xuatBan(d))) return;
    const id = P.id; SO_NL[id] = null;
    try { const r = await API.get('/api/trips/' + encodeURIComponent(id) + '/tao-so'); SO_NL[id] = (r && r.nhien_lieu) || null; }
    catch (e) { SO_NL[id] = null; return; }
    if (P && P.id === id && root && root.isConnected && SO_NL[id] && SO_NL[id].trang_thai) veChi();
  }
  /** Nhãn dòng lấy kho (02/10): xe nhà "Xuất nội bộ — xe nhà"; xe thuê "Xuất bán cho đối tác · giá bán …" (giá bán chỉ hiện với vai
   *  thấy tiền chi, khi KT kho xăng dầu / KT Chi phí đã gõ). Soi gương tinh_toan.la_xuat_ban. */
  function xkChip(d) {
    if (P.company !== 'joint') return `<div class="px-xk noi">${NN.h('px_xk_noi')}</div>`;
    const gb = thayChi() && d.sale_price != null && d.sale_price !== '' && EPL.doc(d.sale_price) > 0
      ? ` · ${NN.h('px_gia_ban')} ${so(EPL.doc(d.sale_price))} ${esc(d.currency || 'LAK')}` : '';
    return `<div class="px-xk ban">${NN.h('px_xk_ban')}${gb}</div>`;            // tên đối tác đã ở dòng bản chất đầu mục
  }
  function giaDuoc(m, d) {
    if (!thayChi() || nguonKho(m, d)) return false;
    if (moi) return true;
    return suaDuoc(m) || (MUC_CHI.includes(m) && !biKhoa() && perm().verify.includes(m) && ['wait', 'entered'].includes((P.sections || {})[m] || 'wait'));
  }
  // dòng chi của mục này có được GỬI lên khi Lưu không: mục còn sửa được, hoặc người kiểm còn nhập giá một dòng (mục khoá gửi
  // lên là máy chủ từ chối cả phiếu). Ô đổi mã kế toán theo đúng luật này — đổi mà không gửi được là sửa xong mất (rà 01/10).
  // ô GIÁ BÁN cho chủ xe trên dòng KHO của xe thuê (mục III dầu · mục V phụ tùng) — người kiểm gõ lúc kiểm (29/09 · 30/09).
  // Máy chủ nhận ô này từ người kiểm (_ap_gia); trước 06/10 màn không gửi dòng kho (giaDuoc loại dòng kho) → gõ giá bán rồi
  // Lưu / Kiểm là mất, 409 THIEU_GIA_BAN mãi (chạy thử kịch bản CA-3 / CA-6).
  const giaBanDuoc = (m, d) => thayChi() && xuatBan(d) && !!d.paid_by_epl && suaTienDuoc(m);
  const coGiaDeGui = (m) => P.expenses.some(e => e.section === m && (giaDuoc(m, e) || giaBanDuoc(m, e)));
  const guiMuc = (m) => suaDuoc(m) || (!moi && coGiaDeGui(m));
  const suaPodDuoc = () => !moi && AUTH.la('yard', 'acct', 'rev') && !biKhoa();
  // cách trả dòng mục IV / VI (08/10): KT Chi phí VC khi mục còn chờ / đã nhập (cùng lúc nhập đơn giá), Sếp — chép luật máy chủ
  const caDoiDuoc = (m) => AUTH.la('expacct') && suaTienDuoc(m);
  function veVaiVaTrangThai() {
    COT_POD.forEach(c => { const el = g('f-' + c); if (el) el.disabled = !suaPodDuoc(); });
    veHopDong();
    g('px-goi-y').innerHTML = NN.h('hint_' + (vai() === 'treasury' ? 'treasury' : vai()));
    g('px-doc-no').disabled = !suaDuoc('info');
    g('px-trang-thai').innerHTML = moi ? '' : `${tag(P.transport_status)} ${tag(P.finance_status)}${P.da_tao_so ? ` <span title="${esc(((P.so_ke_toan || {}).order_code) || '')}">${tag('paid', 'dt_st_da_tao_so')}</span>` : ''}${P.locked ? ` <span class="px-khoa" title="${esc(P.locked_by || '')}">🔒 ${NN.h('s_locked')}</span>` : ''}${P.owner_paid ? ' ' + tag('paid', 'owner_paid') : ''}`;
    MUC.forEach(m => {
      const sec = q(`.px-muc[data-muc="${m}"]`), st = moi ? 'wait' : (P.sections[m] || 'wait'), tuyChon = (m === 'repair' || m === 'other') && !P.expenses.some(d => d.section === m);
      const khoa = !suaDuoc(m); sec.classList.toggle('locked', khoa);
      const cot = m === 'info' ? COT_INFO : m === 'trans' ? COT_TRANS : [];
      cot.forEach(c => { const el = g('f-' + c); if (el) el.disabled = COT_KE_TOAN.includes(c) ? !suaKeToanDuoc(m) : ((khoa && !(COT_TIEN.includes(c) && suaTienDuoc(m))) || (daNhapKho() && (c === 'weight_origin' || c === 'weight_dest'))); });
      if (m === 'trans' && khoa && suaTienDuoc(m)) sec.classList.remove('locked');   // kế toán còn sửa được ô tiền thì mục chưa "khoá" với họ
      if (m === 'info' || m === 'trans') {
        // Ngày xe về, km về (mục I) và cân cuối (mục II) điền KHI XE VỀ (chủ dự án 29/09): "Báo đã về" hoặc "Xe đã tới ·
        // nhập cân cuối" — trước lúc đó chỉ xem, có dòng nhỏ nói khi nào điền; xe đã tới thì sửa được như cũ
        const chuaVe = moi || P.transport_status !== 'arrived';
        (m === 'info' ? ['back_date', 'odo_back'] : ['weight_dest']).forEach(c => {
          const el = g('f-' + c); if (!el) return;
          if (chuaVe) el.disabled = true;
          const nhac = el.parentElement.querySelector('.px-khi-ve'); if (nhac) nhac.hidden = !chuaVe;
        });
      }
      const e = sec.querySelector('.px-stt'); const k = tuyChon ? 'na' : st;
      e.className = 'px-stt ' + k; e.innerHTML = NN.h(khoaTT(m, k));
      const nut = []; const p = perm();
      if (!moi && !tuyChon) {
        if (st === 'wait' && (p.edit.includes(m) || vai() === 'admin')) nut.push(['ok', 'send', 'a_send']);
        // Phiếu đã khoá: không "Trả lại sửa" (trừ Sếp) — người nhập (Bãi, tổ sửa chữa) không ghi được vào phiếu đã khoá, trả lại
        // là mục kẹt "chưa gửi" không ai sửa; muốn sửa thì KT Thu/Chi mở khoá phiếu trước (máy chủ cũng chặn — rà 01/10)
        const traDuoc = !P.locked || vai() === 'admin';
        if (st === 'entered' && (p.verify.includes(m) || vai() === 'admin')) { nut.push(['ok', 'verify', 'a_verify']); if (traDuoc) nut.push(['warn', 'return', 'a_return']); }
        if (st === 'verified' && MUC_CHI.includes(m) && (p.book.includes(m) || vai() === 'admin')) nut.push(['ok', 'book', 'a_book']);
        if (st === 'verified' && traDuoc && (p.verify.includes(m) || vai() === 'admin')) nut.push(['warn', 'return', 'a_return']);
        // tạm ứng chi ở hệ kế toán (01/10): Quỹ không bấm chi mục IV ở đây — thủ quỹ ghi sổ phiếu chi bên đó (Sếp vẫn chi tay được)
        const cm = (P.chi_muc_ke_toan || {})[m];
        const chiKT = vai() !== 'admin' && ((m === 'travel' && (P.chi_tam_ung || {}).o_ke_toan) || (cm && cm.o_ke_toan && cm.so_dong_con > 0));
        if (st === 'booked' && !chiKT && (p.pay.includes(m) || vai() === 'admin')) nut.push(['ok', 'pay', 'a_pay']);
        if (vai() === 'admin' && !['wait', 'entered'].includes(st)) nut.push(['', 'unlock', 'a_unlock']);
      }
      sec.querySelector('.px-act').innerHTML = (m === 'travel' ? oChiKeToan(st) : (m === 'repair' || m === 'other') ? oChiMuc(m, st) : '') +
        nut.map(b => `<button type="button" class="btn sm ${b[0]}" data-muc-act="${m}" data-hd="${b[1]}">${NN.h(b[2])}</button>`).join('');
    });
    root.querySelectorAll('[data-muc-act]').forEach(b => b.addEventListener('click', () => duyet(b.dataset.mucAct, b.dataset.hd)));
    root.querySelectorAll('[data-chi-kt]').forEach(b => b.addEventListener('click', () => chiKeToan(b.dataset.chiKt)));
    root.querySelectorAll('[data-chi-muc]').forEach(b => b.addEventListener('click', () => chiMuc(b.dataset.muc, b.dataset.chiMuc)));
    // bước tổng thể
    const s = P.sections || {}; const idx = (m) => ['wait', 'entered', 'verified', 'booked', 'paid'].indexOf(s[m] || 'wait');
    const coChi = (m) => P.expenses.some(d => d.section === m);
    const done = [!moi, !moi && MUC.every(m => idx(m) >= 2 || ((m === 'repair' || m === 'other') && !coChi(m))),
      !moi && MUC_CHI.every(m => idx(m) >= 3 || !coChi(m)), !moi && MUC_CHI.every(m => idx(m) >= 4 || !coChi(m)), !moi && !!P.locked];
    let cur = done.findIndex(x => !x); root.querySelectorAll('#px-flow .step').forEach((el, i) => { el.classList.toggle('done', done[i]); el.classList.toggle('now', i === cur); });
    // hành động mức phiếu
    const ta = [];
    if (!moi) {
      if (AUTH.la('acct') && P.transport_status === 'arrived' && !P.locked) ta.push(`<button class="btn sm ok" data-hd-phieu="khoa">🔒 ${NN.h('a_lock')}</button>`);
      if (AUTH.la('acct') && P.locked && (!P.da_tao_so || vai() === 'admin')) ta.push(`<button class="btn sm" data-hd-phieu="mo-khoa">${NN.h('a_unlock_slip')}</button>`);
      // Trả chủ xe (01/10): KHÔNG còn nút sang trang kế toán tạm — tiền đi qua hệ kế toán anh Tune: KT Thu/Chi lập đề nghị trả ở
      // màn Xe liên kết ("Trả qua kế toán"), thủ quỹ chi và ghi sổ bên đó; phiếu bên này chỉ còn thẻ "Đã trả chủ xe"
      if (AUTH.la('yard') && !P.locked && P.transport_status === 'dispatched') ta.push(`<button class="btn sm" data-tt="transit">${NN.h('mark_transit')}</button>${nhacUngTruocChay()}`);
      // Xe hỏng nặng giữa đường thì đổi xe NGAY TRÊN PHIẾU NÀY (C2.2) — không lập phiếu mới, vì hàng,
      // khách, tuyến và tiền đã chi vẫn là của chuyến này.
      if (AUTH.la('yard') && !P.locked && P.transport_status !== 'arrived') ta.push(`<button class="btn sm" data-hd-phieu="doi-xe">${NN.h('change_truck')}</button>`);
      if (AUTH.la('yard') && !P.locked && P.transport_status !== 'arrived') ta.push(`<button class="btn sm ok" data-tt="arrived">${NN.h('mark_arrived')}</button>`);
      // Hoá đơn, thu tiền khách (01/10): KHÔNG còn nút sang trang kế toán tạm (hoá đơn lẻ, hoá đơn gộp, ghi thu) — số bên đó là
      // số thử, đã cắt sổ. Khoá phiếu là máy lập phiếu đề nghị thu → gửi hệ kế toán anh Tune lập SO, hoá đơn, thu tiền (nút
      // "Phiếu đề nghị thu" trên đầu màn); công nợ khách xem ở màn Khách hàng → Công nợ.
      if (AUTH.la('yard') && !P.locked && MUC.every(m => ['wait', 'entered'].includes(s[m] || 'wait'))) ta.push(`<button class="btn sm danger" data-hd-phieu="xoa">${NN.h('delete')}</button>`);
    }
    // không có việc mức phiếu thì giấu cả khối: trạng thái đã có ở đầu cột bên, lặp lại chỉ đẩy cột dài ra (01/10)
    const hd = g('px-hanh-dong'); hd.hidden = !ta.length;
    hd.innerHTML = ta.length ? `<span class="small muted">${NN.h('trip_status')}:</span> ${ta.join(' ')}` : '';
    root.querySelectorAll('[data-tt]').forEach(b => b.addEventListener('click', () => doiTrangThai(b.dataset.tt)));
    root.querySelectorAll('[data-hd-phieu]').forEach(b => b.addEventListener('click', () => b.dataset.hdPhieu === 'xoa' ? xoaPhieu() : b.dataset.hdPhieu === 'khoa' ? khoaPhieu() : b.dataset.hdPhieu === 'doi-xe' ? doiXe() : hanhDongPhieu(b.dataset.hdPhieu)));
    veTep();
    veBen();
    veButToan();
    root.querySelectorAll('[data-loc]').forEach(inp => { const sel = g(inp.dataset.loc); inp.hidden = !sel || sel.disabled; });
    g('px-log').innerHTML = `<h5>${NN.h('log_title')}</h5><ul>${(P.logs || []).length ? P.logs.map(l => `<li><span class="ts">${EPL.ngayGio(l.ts)}</span><span><b lang="lo">${esc(l.user)}</b> <span class="muted">(${NN.h('r_' + l.role)})</span> · ${esc(nhanLog(l.action))}</span></li>`).join('') : `<li class="muted">${NN.h('log_empty')}</li>`}</ul>`;
  }
  // mã nhật ký máy chủ ghi mà từ điển không có khoá cùng tên — lấy khoá sẵn có cùng nghĩa (01/10: nhật ký hiện chữ thô
  // "drv_back", "ev_refuel_reported")
  const LOG_KHOA = { drv_back: 'report_back', fin_undo: 'pay_del' };
  const coKhoa = (k) => NN.t(k) !== k;
  function nhanLog(a) {
    if (!a) return '';
    // G6 (06/10): "chi_that {json}" — KT Chi phí sửa chi thật một dòng mục IV (cũ → mới)
    if (a.startsWith('chi_that ')) {
      try { const n = JSON.parse(a.slice(9)); return NN.t('ct_log', { n: n.dong, khoan: tenDongCT(n), cu: EPL.tien(n.cu, n.tien_te), moi: EPL.tien(n.moi, n.tien_te) }) + (n.ghi_chu ? ' · ' + n.ghi_chu : ''); }
      catch (e) { return a; }
    }
    const m = a.match(/^sec_(\w+):(\w+)$/); if (m) return `${NN.t('sec' + (MUC.indexOf(m[1]) + 1))} → ${NN.t('a_' + m[2])}`;
    if (LOG_KHOA[a]) return NN.t(LOG_KHOA[a]);
    // ev_<việc>_<trạng thái> (đổ dầu dọc đường: tài xế báo · kế toán duyệt) → "Đổ dầu dọc đường · Chờ duyệt"
    const e = !coKhoa(a) && a.match(/^ev_(\w+)_(reported|approved|rejected)$/);
    if (e && coKhoa('ev_' + e[1])) return `${NN.t('ev_' + e[1])} · ${NN.t('st_' + e[2])}`;
    return NN.t(a);
  }
  /** Trạng thái mà vai này CÓ VIỆC ở một mục: nhập khi chờ/đã nhập, kiểm khi đã nhập, ghi sổ khi đã kiểm, chi khi đã ghi sổ. */
  function coViec(m, st) {
    if (moi) return m === 'info';
    const pq = perm();
    return (pq.edit.includes(m) && ['wait', 'entered'].includes(st)) || (pq.verify.includes(m) && st === 'entered')
      || (pq.book.includes(m) && st === 'verified') || (pq.pay.includes(m) && st === 'booked' && !(m === 'travel' && ivKhongTienMat()));
  }
  /** Tab mở sẵn theo vai: mục đầu tiên vai này có việc; không có việc thì mục đầu tiên vai này phụ trách;
   *  vai chỉ xem (doanh thu, Sếp, tài xế) thì Toàn phiếu. */
  function tabMacDinh() {
    if (moi) return 'info';
    const s = P.sections || {}, pq = perm();
    const cua = MUC.filter(m => pq.edit.includes(m) || pq.verify.includes(m) || pq.book.includes(m) || pq.pay.includes(m));
    if (!cua.length || vai() === 'admin') return 'all';
    // mục V / VI chưa có dòng nào là "Không phát sinh" — không tính là việc (Bãi mở phiếu từng rơi vào tab VI trống)
    const rong = (m) => (m === 'repair' || m === 'other') && !(P.expenses || []).some(d => d.section === m);
    return cua.find(m => !rong(m) && coViec(m, s[m] || 'wait')) || cua[0];
  }
  function datTab(t, tay) {
    tab = t; if (tay) tabTay = true;
    const ph = q('#px-phieu'); ph.dataset.tab = tab;
    MUC.forEach(m => { const sec = q(`.px-muc[data-muc="${m}"]`); if (sec) sec.classList.toggle('px-muc-hien', tab === 'all' || tab === m); });
    root.querySelectorAll('#px-tabs .px-tab').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
    capNhatNutLuu();
  }
  /** Nút Lưu chỉ hiện khi mục đang mở CÒN Ô vai này sửa được (rà 01/10: KT kho xăng dầu mở mục III đã ghi sổ, KT Thu/Chi mở
   *  phiếu đã khoá — mọi ô đều khoá mà nút Lưu vẫn sáng, bấm là ghi một lượt "lưu" rỗng vào nhật ký). Đọc thẳng các ô đang
   *  hiện trên màn, nên luôn khớp với chỗ đã khoá / mở theo vai; ô đính kèm tệp gửi ngay khi chọn nên không tính. */
  function capNhatNutLuu() {
    const luu = g('px-luu'); if (!luu) return;
    const hien = (el) => el.getClientRects().length > 0;
    const coO = !!P && tab !== 'all' && ((g('px-doc-no') && !g('px-doc-no').disabled)
      || [...root.querySelectorAll(['input', 'select', 'textarea', '.px-acct', '[data-pay]', '.px-them', '#px-hang-them'].map(s => '.px-muc.px-muc-hien ' + s).join(', '))]
        .some(el => !el.disabled && !el.hidden && el.type !== 'file' && hien(el)));
    luu.hidden = !coO;
  }
  /** Chữ trạng thái một mục. Mục I, II không có bước ghi sổ / chi — "đã kiểm" là xong, đừng ghi "chờ ghi sổ" (rà 01/10). */
  // 06/10 (điều phối, G4-0006): mục IV xe nhà KHÔNG có tạm ứng tiền mặt (mọi khoản EPL ứng trả cùng lương / nợ NCC / thẻ — máy chủ
  // gửi cờ tien_mat_tx từng dòng): không có phiếu chi tạm ứng cho quỹ chi, máy chủ cho mục tự qua bước Chi lúc ghi sổ. Sau ghi sổ
  // chữ trạng thái nói đúng chuyện: "Chi ở kế toán (cùng lương)" thay cho "Đã chi" / "Chờ chi".
  const ivKhongTienMat = () => !moi && !!P && P.company !== 'joint' && !(P.expenses || []).some(d => d.tien_mat_tx)
    && (P.expenses || []).some(d => d.section === 'travel' && d.paid_by_epl);
  const ivCungLuong = () => (P.expenses || []).some(d => d.section === 'travel' && d.paid_by_epl && d.cach_tra === 'luong');
  const khoaTT = (m, st) => (m === 'travel' && ['booked', 'paid'].includes(st) && ivKhongTienMat()) ? (ivCungLuong() ? 'stt_iv_luong' : 'stt_iv_khong_tm')
    : st === 'wait' ? 'stt_wait2' : (st === 'verified' && !MUC_CHI.includes(m)) ? 'stt_verified_12' : 'stt_' + st;
  function veTabs() {
    const s = (P && P.sections) || {};
    q('#px-tabs').innerHTML = MUC.map((m, i) => {
      const st = moi ? 'wait' : (s[m] || 'wait');
      const tuyChon = (m === 'repair' || m === 'other') && !moi && !P.expenses.some(d => d.section === m);
      return `<button type="button" class="px-tab ${tab === m ? 'active' : ''} ${coViec(m, st) ? 'viec' : ''}" data-tab="${m}" title="${esc(NN.t(khoaTT(m, tuyChon ? 'na' : st)))}">
        <b>${SO_LA_MA[i]}</b><span>${NN.h('sec' + (i + 1))}</span><i class="stt ${tuyChon ? 'na' : st}"></i>
        <em class="st-chu ${tuyChon ? 'na' : st}">${NN.h(khoaTT(m, tuyChon ? 'na' : st))}</em></button>`;
    }).join('') + `<button type="button" class="px-tab tat-ca ${tab === 'all' ? 'active' : ''}" data-tab="all"><span>${NN.h('px_tab_all')}</span></button>`;
    root.querySelectorAll('#px-tabs .px-tab').forEach(b => b.addEventListener('click', () => datTab(b.dataset.tab, true)));
  }

  /** K3: có khách + tuyến mà ô đơn giá còn trống → lấy giá hợp đồng từ bảng giá. Bãi không thấy tiền nên
   *  không hỏi (máy chủ tự điền khi Bãi lưu); kế toán đã gõ giá thì giữ nguyên. */
  async function dienGiaHopDong() {
    if (vai() === 'yard' || !P.customer_id || !P.route_id || EPL.doc(P.price) > 0) return;
    try {
      const gia = await API.get(`/api/bang-gia/tra?customer_id=${encodeURIComponent(P.customer_id)}&route_id=${encodeURIComponent(P.route_id)}&goods_type=${encodeURIComponent(P.goods_type || 'iron_ore')}${P.doc_date ? '&ngay=' + P.doc_date : ''}`);
      if (!gia || !gia.price) return;
      P.price = gia.price; g('f-price').value = gia.price;
      P.price_ccy = (gia.price_ccy || 'USD').toUpperCase(); g('f-price_ccy').value = P.price_ccy;
      P.price_mode = gia.price_mode || 'ton'; g('f-price_mode').value = P.price_mode;
      if (gia.hire_price && (P.hire_price == null || P.hire_price === '')) {
        P.hire_price = gia.hire_price; g('f-hire_price').value = gia.hire_price;
        P.hire_ccy = (gia.hire_ccy || gia.price_ccy || 'USD').toUpperCase(); g('f-hire_ccy').value = P.hire_ccy;
      }
      veSo(); nhanCan(); EPL.toast(NN.t('px_gia_tu_bang'), 'ok');
    } catch (e) { /* không có quyền xem giá hoặc chưa có bảng giá — để trống cho kế toán gõ */ }
  }

  /* ---------------------------------------------------------------- cột bên (30/09) */
  function veBen() {
    const gom = laGom();
    const the = (cls, nhan, phu) => `<span class="px-loai-the ${cls}"><b>${nhan}</b><small>${phu}</small></span>`;
    g('px-ben-loai').innerHTML = the(gom ? 'gom' : 'giao', NN.h(gom ? 'dn_gom' : 'dn_giao'), NN.h(gom ? 'do_gom' : 'do_giao'))
      + (P.company === 'joint' ? the('thue', NN.h('dn_xe_thue'), `<span lang="lo">${esc(P.owner_name || '')}</span>`) : '');
    g('px-loai-in').innerHTML = `<span class="px-loai-the nho ${gom ? 'gom' : 'giao'}"><b>${NN.h(gom ? 'do_gom' : 'do_giao')}</b></span>`;
    g('px-ben-so').innerHTML = moi ? `<span class="muted">${NN.h('new_slip')}</span> <span class="mono">${esc(P.doc_no || '')}</span>`
      : `<span class="mono">${esc(P.doc_no)}</span><small>${esc(P.truck_no || '')} · <span lang="lo">${esc(P.driver_name || '')}</span></small>`;
    g('px-ben-tt').innerHTML = g('px-trang-thai').innerHTML;
    veToKhoHang();
  }

  /* ---------------------------------------------------------------- phiếu kho HÀNG khách gửi (05/10)
   * Máy tự lập theo DO: DO gom Bãi bấm "Xe đã tới" (có cân bãi) → phiếu nhập kho hàng PNK_HH; DO giao lưu có lấy hàng từ lô →
   * phiếu xuất PXK_HH. GET /api/trips/{id}/to-kho-hang trả tờ để in; chưa có → 404 CHUA_CO_TO → ẩn khối "Phiếu kho hàng".
   * Hỏi lại khi mở phiếu, sau khi lưu, đổi trạng thái chuyến, đổi xe (các lúc tờ có thể vừa sinh / đổi). */
  let TO_KH = null;                      // { trip, to } — to = null: phiếu này chưa có tờ
  async function napToKhoHang() {
    const id = P && !moi ? P.id : null;
    TO_KH = { trip: id, to: null };
    veToKhoHang();
    if (!id) return;
    let to = null;
    try { to = await API.get('/api/trips/' + encodeURIComponent(id) + '/to-kho-hang'); }
    catch (e) { to = null; }            // 404 CHUA_CO_TO (hay máy chủ cũ chưa có đường này): chưa có tờ — không báo lỗi, chỉ ẩn nút
    if (!P || P.id !== id) return;
    TO_KH = { trip: id, to };
    if (root && root.isConnected) veToKhoHang();
  }
  const toNay = () => (TO_KH && P && !moi && TO_KH.trip === P.id) ? TO_KH.to : null;
  const laPhieuXuatKH = (to) => to.loai ? to.loai === 'PXK_HH' : P.kind !== 'gom';
  function veToKhoHang() {
    const k = g('px-kho-hang'); if (!k) return;
    const to = toNay();
    k.hidden = !to;
    if (!to) return;
    const chu = g('px-in-kho-hang-chu');
    chu.dataset.i18n = laPhieuXuatKH(to) ? 'khh_in_pxk' : 'khh_in_pnk'; chu.innerHTML = NN.h(chu.dataset.i18n);
    g('px-kho-hang-so').innerHTML = `<span class="mono">${esc(to.so || '')}</span>${to.ngay ? ' · ' + EPL.ngay(to.ngay) : ''}${to.tong_tan != null ? ' · ' + so(to.tong_tan, 2) + ' ' + NN.h('ton') : ''}`;
  }
  /** Mở tờ in ở cửa sổ riêng (như biên bản giao nhận). Cửa sổ mở NGAY lúc bấm — đợi máy chủ xong mới mở là trình duyệt chặn
   *  cửa sổ bật lên; rồi mới hỏi lại tờ mới nhất (cân có thể vừa sửa) và ghi vào. */
  async function inToKhoHang() {
    const id = P && P.id; if (!id) return;
    const w = window.open('', '_blank');
    if (!w) return EPL.toast(NN.t('khh_mo_cua_so'), 'loi');
    w.document.write(`<!doctype html><meta charset="utf-8"><title>…</title><p style="font-family:system-ui,sans-serif;color:#7A858F;padding:24px">${esc(NN.t('loading'))}</p>`);
    let to;
    try { to = await API.get('/api/trips/' + encodeURIComponent(id) + '/to-kho-hang'); }
    catch (e) { w.close(); if (e && e.ma === 'CHUA_CO_TO') { TO_KH = { trip: id, to: null }; veToKhoHang(); } return EPL.toast(NN.t('khh_in_loi', { loi: e.message || String(e) }), 'loi'); }
    if (P && P.id === id) { TO_KH = { trip: id, to }; veToKhoHang(); }
    w.document.open(); w.document.write(htmlToKhoHang(to)); w.document.close();
  }
  /** Tờ PNK_HH / PXK_HH khổ A4 — cùng kiểu tờ đề nghị xuất kho nhiên liệu (css/chung.css .ct-*): đầu tờ logo + địa chỉ, số tờ
   *  bên phải, tiêu đề giữa + dòng Lào · Anh, dòng bản chất, ô thông tin hai cột, bảng dòng lô × tấn, khối cân, bốn chỗ ký. */
  function htmlToKhoHang(to) {
    const xuat = laPhieuXuatKH(to);
    const T = (k, p) => esc(NN.t(k, p));
    const so2 = (v) => v == null || v === '' ? '—' : so(v, 2);
    const o = (k, v, lo) => `<div><span>${T(k)}</span><b${lo ? ' lang="lo"' : ''}>${v == null || v === '' ? '—' : esc(v)}</b></div>`;
    const dong = to.dong || [];
    const tong = to.tong_tan != null ? to.tong_tan : dong.reduce((a, d) => a + EPL.doc(d.tan), 0);
    // cân: phiếu nhập — tại mỏ, tại bãi khi về; phiếu xuất — lấy khỏi kho (bãi), tại nơi giao; hao hụt = hiệu hai số
    const goc = xuat ? to.can_bai : to.can_mo;
    const can = (xuat ? [['w_origin_giao', to.can_bai], ['w_dest_giao', to.can_noi_giao]] : [['w_origin_gom', to.can_mo], ['w_dest_gom', to.can_bai]])
      .map(([k, v]) => `<div><span>${T(k)}</span><b>${so2(v)}</b></div>`).join('')
      + `<div><span>${T('w_loss')}</span><b>${to.hao_hut == null ? '—' : so2(to.hao_hut) + ' ' + T('ton') + (EPL.doc(goc) > 0 ? ` (${so(EPL.doc(to.hao_hut) / EPL.doc(goc) * 100, 1)}%)` : '')}</b></div>`;
    const ky = (xuat ? [['khh_ky_kho_xuat', to.nguoi_xac_nhan], ['khh_ky_tx_nhan', to.tai_xe]] : [['khh_ky_tx_giao', to.tai_xe], ['khh_ky_kho_nhan', to.nguoi_xac_nhan]])
      .concat([['sg_chief_acct', ''], ['sg_director', '']])
      .map(([k, ten]) => `<div><div class="line"></div>${T(k)}<div class="muted" lang="lo">${esc(ten || '')}</div></div>`).join('');
    const logo = new URL('img/logo-epl.jpg', location.href).href;
    return `<!doctype html><html lang="${esc(document.documentElement.lang || 'vi')}"><head><meta charset="utf-8">
<title>${esc(to.so || '')} · ${esc(to.do_no || '')}</title>
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;600;700&family=Noto+Sans+Lao:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  @page{size:A4 portrait;margin:14mm}
  *{box-sizing:border-box}
  body{font-family:'Be Vietnam Pro','Noto Sans Lao',system-ui,sans-serif;color:#1C2229;font-size:13px;line-height:1.5;margin:0;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  [lang="lo"]{font-family:'Noto Sans Lao','Be Vietnam Pro',sans-serif}
  .muted{color:#7A858F;font-size:12px}
  .dau{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:2px solid #1C2229;padding-bottom:12px;margin-bottom:14px}
  .dau>div:first-child{display:flex;gap:12px;align-items:center}
  .logo{width:52px;height:52px;border-radius:8px;object-fit:cover}
  .so{text-align:right;font-size:13px} .so b{font-family:ui-monospace,Consolas,monospace;font-size:15px;display:block}
  .tieu-de{text-align:center;font-size:19px;font-weight:700;margin:4px 0;letter-spacing:.02em}
  .phu{text-align:center;color:#7A858F;font-size:12.5px;margin-bottom:14px}
  .ht{text-align:center;font-weight:600;font-size:13px;margin:-8px 0 14px}
  .meta{display:grid;grid-template-columns:1fr 1fr;gap:4px 28px;margin-bottom:14px}
  .meta>div{display:flex;justify-content:space-between;gap:10px;border-bottom:1px dotted #BFC8C0;padding:3px 0}
  .meta span{color:#4A5560;white-space:nowrap} .meta b{font-weight:600;text-align:right}
  h2{font-size:12.5px;margin:16px 0 6px;color:#145C4A;text-transform:uppercase;letter-spacing:.04em}
  table{width:100%;border-collapse:collapse} th,td{border:1px solid #BFC8C0;padding:6px 8px;text-align:left} th{background:#EDF0EC;font-weight:600}
  .num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap} .mono{font-family:ui-monospace,Consolas,monospace}
  tfoot td{font-weight:700}
  .ky{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:34px;text-align:center;font-size:12.5px}
  .ky .line{height:54px;border-bottom:1px solid #7A858F;margin-bottom:6px}
  .chan{margin-top:18px;color:#7A858F;font-size:11px}
  @media screen{body{max-width:820px;margin:24px auto;padding:0 20px}}
</style></head><body>
<div class="dau">
  <div><img src="${esc(logo)}" alt="EPL" class="logo"><div><b>EPL TRANSPORT</b><div class="muted">SAMKET VILLAGE, SIKHOTTABONG DISTRICT, VIENTIANE LAO<br>ໂທລະສັບ/Tel: 020 5889 9983</div></div></div>
  <div class="so">${T('voucher_no')}<b>${esc(to.so || '—')}</b>${esc(EPL.ngay(to.ngay))}</div>
</div>
<div class="tieu-de">${T(xuat ? 'khh_to_pxk' : 'khh_to_pnk')}</div>
<div class="phu">${xuat ? 'ໃບເບີກສິນຄ້າອອກສາງ · Goods issue note' : 'ໃບຮັບສິນຄ້າເຂົ້າສາງ · Goods receipt note'}</div>
<div class="ht">${T(xuat ? 'khh_to_pxk_ht' : 'khh_to_pnk_ht')}</div>
<div class="meta">
  ${o('khh_do', to.do_no)}${o('k2_bai', to.kho, true)}
  ${o('customer', to.khach, true)}${o('goods_type', to.loai_hang, true)}
  ${o('truck_no', to.xe)}${o('driver', to.tai_xe, true)}
  ${o('c_date', EPL.ngay(to.ngay))}${o('khh_xac_nhan', to.nguoi_xac_nhan, true)}
</div>
<h2>${T('khh_to_dong')}</h2>
<table><thead><tr><th style="width:42px">#</th><th>${T('khh_to_lo')}</th><th>${T('goods_type')}</th><th class="num">${T('qty_t')}</th></tr></thead><tbody>
  ${dong.length ? dong.map((d, i) => `<tr><td>${i + 1}</td><td class="mono">${esc(d.lo_doc_no || '—')}</td><td lang="lo">${esc(d.loai_hang || to.loai_hang || '')}</td><td class="num">${so2(d.tan)}</td></tr>`).join('') : '<tr><td colspan="4">—</td></tr>'}
</tbody><tfoot><tr><td colspan="3">${T('k2_tong')}</td><td class="num">${so2(tong)}</td></tr></tfoot></table>
<h2>${T('khh_to_can')}</h2>
<div class="meta">${can}</div>
<div class="ky">${ky}</div>
<div class="chan">${T('khh_to_chan', { do: to.do_no || '' })}</div>
<script>window.onload=function(){setTimeout(function(){window.print()},400)}<\/script>
</body></html>`;
  }
  /** Cột bên dính NGAY DƯỚI thanh đầu trang (01/10). Thanh menu trên (.tbar) và thanh tiêu đề (.topbar) đều dính ở đỉnh;
   *  cao bao nhiêu tuỳ kiểu menu, ngôn ngữ, dòng nút xuống hàng — đo thật rồi đặt --px-dinh (px trong khung đã zoom, nên
   *  chia --ty-le). Theo dõi bằng ResizeObserver: đổi kiểu menu, đổi tiếng, co cửa sổ là đo lại; rời màn thì thôi theo dõi. */
  let theoDinh = null;
  function datDinh() {
    const k = q('.px-khung'); if (!k) return;
    const tl = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--ty-le')) || 1;
    const cao = [...document.querySelectorAll('.tbar, .topbar')].filter(e => e.getClientRects().length && getComputedStyle(e).position === 'sticky')
      .reduce((a, e) => Math.max(a, e.getBoundingClientRect().height), 0);
    k.style.setProperty('--px-dinh', Math.ceil(cao / tl) + 'px');
    // khoảng đệm đáy trang: cuộn tới cuối thì cột dính bị đáy khung đẩy lên, chui đầu vào dưới thanh menu — cho cột lấn
    // xuống phần đệm này (CSS: margin-bottom âm). Đọc từ style tính sẵn nên đã là px trong khung zoom.
    const page = document.getElementById('noi-dung');
    k.style.setProperty('--px-chan', (page ? parseFloat(getComputedStyle(page).paddingBottom) || 0 : 0) + 'px');
  }
  function theoDoiDinh() {
    if (theoDinh) theoDinh.disconnect();
    datDinh();
    if (!window.ResizeObserver) return;
    theoDinh = new ResizeObserver(() => { if (!root || !root.isConnected) { theoDinh.disconnect(); theoDinh = null; return; } datDinh(); });
    document.querySelectorAll('.tbar, .topbar').forEach(e => theoDinh.observe(e));
  }

  /** Excel của tờ phiếu (01/10). Mặc định chỉ đọc bảng đang hiện — Bãi mở phiếu ở mục I (không có bảng) bấm Excel thì
   *  "chưa có bảng"; ở Toàn phiếu thì mất hết ô mục I–II (xe, tài xế, tuyến, cân…). Ở đây: sheet đầu là các ô mục I–II
   *  (nhãn · giá trị, đúng những ô vai này đang thấy), sau đó mỗi bảng hàng / chi một sheet — đọc ở chế độ Toàn phiếu
   *  rồi trả lại mục đang mở. */
  function xuatExcelPhieu(r) {
    if (!P) return [];
    const cu = tab, X = EPL._xlsx;
    datTab('all', false);
    try {
      const hien = (e) => e.getClientRects().length > 0;
      const chuNhan = (e) => e.innerText.replace(/\s*\n\s*/g, ' / ').trim();
      const giaTri = (f) => {                                             // undefined = ô này không có giá trị để ghi
        // ô xe / tài xế bọc trong .px-tim-o cùng ô tìm (08/10) — đọc ô chọn, bỏ ô tìm
        const o = f.querySelector(':scope > select, :scope > .px-tim-o > select, :scope > input, :scope > .ro, :scope > .px-hd');
        if (!o) return undefined;
        if (o.tagName === 'SELECT') return o.value === '' ? '' : (o.options[o.selectedIndex] || {}).text || '';
        if (o.tagName === 'INPUT') return o.type === 'date' ? EPL.oNgay(o.value) : (X ? X.sangO(o.value) : o.value);
        return X ? X.sangO(o.innerText.replace(/\s+/g, ' ')) : o.innerText.trim();
      };
      const dong = [[NN.t('doc_no'), P.doc_no || ''], [NN.t('trip_status'), g('px-trang-thai').innerText.replace(/\s+/g, ' ').trim()]];
      ['info', 'trans'].forEach(m => {
        const sec = q(`.px-muc[data-muc="${m}"]`); if (!sec || !hien(sec)) return;
        dong.push([`${SO_LA_MA[MUC.indexOf(m)]}. ${chuNhan(sec.querySelector('.px-muc-dau h4'))}`, '']);
        sec.querySelectorAll('.field').forEach(f => {
          if (!hien(f) || f.querySelector('.field, table')) return;      // khối POD / bảng hàng: ô con và bảng đi riêng
          const lb = f.querySelector(':scope > label'), v = giaTri(f);
          if (lb && v !== undefined) dong.push([chuNhan(lb), v === null ? '' : v]);
        });
      });
      const bang = X ? X.sheetMacDinh(r) : [];
      return [EPL.xuatSheet(NN.t('doc_dispatch'), [NN.t('xuat_chi_tieu'), NN.t('xuat_gia_tri')], dong), ...bang];
    } finally { datTab(cu, false); }
  }
  // vai thấy TIỀN BÁN (cước, doanh thu, giá thuê, lãi) — cùng danh sách với máy chủ (phan_quyen.thay_tien_ban)
  const thayTienBan = () => !['yard', 'driver', 'depot', 'parts', 'repair'].includes(vai());
  function veBenTien(k) {
    const o = g('px-ben-tien'); if (!o) return;
    const dong = (l, v, cls = '') => `<div class="r ${cls}"><span>${l}</span><b>${v}</b></div>`;
    if (!thayGiaKho()) { o.innerHTML = ''; return; }       // tổ sửa chữa: tổng chi có giá kho bên trong — không hiện
    if (!thayTienBan()) { o.innerHTML = dong(NN.h('sum_exp'), so(k.tongChi) + ' LAK'); return; }
    o.innerHTML = k.lk
      ? dong(NN.h('do_money'), t2(k.dt, k.ma)) + dong(NN.h('st_hire'), '− ' + t2(k.thue, k.mh)) + dong(NN.h('st_net_owner'), t2(k.traChu, k.mh), 'tot')
      : dong(NN.h('sum_rev'), t2(k.dt, k.ma)) + dong(NN.h('sum_exp'), so(k.tongChi) + ' LAK') + dong(NN.h('sum_net'), (k.laiLak < 0 ? '−' : '') + so(Math.abs(k.laiLak)) + ' LAK', 'tot');
  }
  function veHet() {
    q('#px-phieu').classList.toggle('px-an-tien', vai() === 'yard');
    q('#px-ben').classList.toggle('px-an-tien', vai() === 'yard');
    q('#px-phieu').classList.toggle('is-gom', laGom());
    q('#px-phieu').classList.toggle('is-giao', !laGom());
    veChon(); veDanhMuc(); doTruong(); veChi(); veHang(); veVaiVaTrangThai();
    // phiếu mới: hai thẻ lớn chọn Gom / Giao
    const cl = g('px-chon-loai'); cl.hidden = !moi;
    cl.querySelectorAll('button').forEach(b => b.classList.toggle('on', b.dataset.loai === (P.kind || 'giao')));
    if (!tabTay) tab = tabMacDinh();
    veTabs(); datTab(tab, false); NN.apDung(root); nhanCan();
    napChiThat();
  }
  /* ---- G6 (06/10): CHI THẬT mục IV sau khi đã chi tạm ứng. Tài xế về khai chi thật ít / nhiều hơn số đã ứng: KT Chi phí VC (và Sếp)
   * sửa SỐ CHI THẬT từng dòng tiền mặt tài xế cầm (xe nhà) tới khi kỳ tất toán tài xế chứa DO này chốt. Không đụng phiếu chi tạm ứng
   * đã chi — "đã ứng" giữ nguyên, chênh lệch đi vào Tất toán tài xế. Máy chủ quyết quyền và kỳ (GET / POST /api/trips/{id}/chi-that);
   * ở đây chỉ hiện khối cho đúng vai, đúng lúc. */
  let CHI_THAT = null;                                   // gói máy chủ của phiếu đang mở
  const chiThatHien = () => !moi && P && P.id && P.company !== 'joint' && AUTH.la('expacct') && (P.sections || {}).travel === 'paid'
    && (P.expenses || []).some(d => d.section === 'travel' && d.tien_mat_tx);
  async function napChiThat() {
    const o = g('px-chi-that'); if (!o) return;
    if (!chiThatHien()) { o.hidden = true; o.innerHTML = ''; CHI_THAT = null; return; }
    const id = P.id;
    if (CHI_THAT && CHI_THAT.trip_id === id) veChiThat();             // vẽ ngay bản đang có, rồi hỏi lại máy chủ
    try { const x = await API.get('/api/trips/' + encodeURIComponent(id) + '/chi-that'); if (!P || P.id !== id) return; CHI_THAT = x; }
    catch (e) { if (e.ma !== 'HUY' && e.status !== 403) EPL.baoLoi(e); return; }
    veChiThat();
  }
  /** Câu máy chủ (loi · loi_lo · loi_en) theo tiếng đang xem. */
  const chuMay = (x) => (!x ? '' : NN.lang === 'lo' && x.loi_lo ? x.loi_lo : NN.lang === 'en' && x.loi_en ? x.loi_en
    : NN.lang === 'both' && x.loi_lo ? x.loi + ' / ' + x.loi_lo : x.loi || '');
  const tenDongCT = (z) => (z.item_key ? NN.t(z.item_key) : z.item_name || '—');
  function veChiThat() {
    const o = g('px-chi-that'), x = CHI_THAT;
    if (!o || !x || !P || x.trip_id !== P.id) return;
    const ky = x.ky ? x.ky.slice(5, 7) + '/' + x.ky.slice(0, 4) : '';
    const sua = !!x.duoc_sua, le = (ma) => EPL.leTien(ma);
    o.hidden = false;
    o.innerHTML = `<div class="px-ct-dau"><b>${NN.h('ct_tieu_de')}</b>
        <span class="px-ct-tt ${sua ? 'mo' : 'khoa'}">${NN.h(sua ? 'ct_mo' : 'ct_khoa', { ky })}</span></div>
      <p class="small muted">${NN.h('ct_giai_thich', { ky })}</p>
      ${sua ? '' : `<p class="px-ct-ly">${esc(chuMay(x.ly_do))}</p>`}
      <div class="tbl-wrap"><table class="tbl tbl-compact px-ct-bang"><thead><tr><th>#</th><th>${NN.h('item')}</th><th class="num">${NN.h('qty_lan')}</th>
        <th class="num">${NN.h('ct_dang_ghi')}</th><th class="num">${NN.h('ct_chi_that')}</th></tr></thead>
      <tbody>${(x.dong || []).map(z => `<tr><td>${esc(z.line_no)}</td><td lang="lo">${esc(tenDongCT(z))}</td><td class="num">${so(z.qty, Number.isInteger(+z.qty) ? 0 : 2)}</td>
        <td class="num">${EPL.tien(z.chi_that, z.currency)}</td>
        <td class="num"><input class="num px-ct-o" data-ct="${esc(z.id)}" inputmode="decimal" value="${esc(so(z.chi_that, le(z.currency)))}" ${sua ? '' : 'disabled'}
          aria-label="${esc(NN.t('ct_chi_that') + ' · ' + tenDongCT(z))}"> <small class="muted">${esc(z.currency)}</small></td></tr>`).join('')
        || `<tr><td colspan="5" class="empty small">${NN.h('no_data')}</td></tr>`}</tbody></table></div>
      ${sua ? `<div class="px-ct-nut"><input id="px-ct-ghi" maxlength="200" placeholder="${esc(NN.t('ct_ghi_chu_ph'))}" aria-label="${esc(NN.t('note'))}">
        <button type="button" class="btn sm ok" id="px-ct-luu">${NN.h('ct_luu')}</button></div>` : ''}
      ${(x.nhat_ky || []).length ? `<details class="px-ct-nk"><summary>${NN.h('ct_lich_su', { n: x.nhat_ky.length })}</summary><ul>${x.nhat_ky.map(n =>
        `<li><span class="ts">${EPL.ngayGio(n.ts)}</span> <b lang="lo">${esc(n.user || '')}</b> · ${esc(NN.t('ct_dong', { n: n.dong, khoan: tenDongCT(n) }))}:
          ${EPL.tien(n.cu, n.tien_te)} → <b>${EPL.tien(n.moi, n.tien_te)}</b>${n.ghi_chu ? ` · <span lang="lo">${esc(n.ghi_chu)}</span>` : ''}</li>`).join('')}</ul></details>` : ''}`;
    const nut = g('px-ct-luu');
    if (nut) nut.addEventListener('click', luuChiThat);
  }
  async function luuChiThat() {
    const o = g('px-chi-that'), x = CHI_THAT; if (!o || !x) return;
    const dong = [...o.querySelectorAll('[data-ct]')].map(el => ({ id: el.dataset.ct, chi_that: EPL.doc(el.value), _tho: el.value.trim() }));
    if (dong.some(z => z._tho === '' || z.chi_that < 0)) return EPL.toast(NN.t('ct_so_sai'), 'loi');
    const doi = dong.filter(z => { const cu = (x.dong || []).find(d => d.id === z.id); return cu && Math.abs(cu.chi_that - z.chi_that) > 1e-6; });
    if (!doi.length) return EPL.toast(NN.t('ct_khong_doi'), 'ok');
    const nut = g('px-ct-luu'); if (nut) nut.disabled = true;
    try {
      CHI_THAT = await API.post('/api/trips/' + encodeURIComponent(P.id) + '/chi-that',
        { dong: doi.map(z => ({ id: z.id, chi_that: z.chi_that })), ghi_chu: (g('px-ct-ghi') || {}).value || undefined });
      P = await API.get('/api/trips/' + P.id); veHet();
      EPL.toast(NN.t('ct_da_luu'), 'ok');
    } catch (e) { EPL.baoLoi(e); if (nut) nut.disabled = false; }
  }
  /** Hai ô cân mang nghĩa khác nhau tuỳ loại DO, nên nhãn phải nói đúng chỗ cân; ô đơn giá theo cách tính cước.
   *  Đổi luôn data-i18n chứ không chỉ chữ (01/10): chung.js chạy NN.apDung lần nữa SAU init, trước đây nó ghi đè về
   *  "Cân đầu / Cân cuối" và "Đơn giá mỗi tấn" (kể cả phiếu trọn chuyến) ngay lần mở đầu tiên. */
  function nhanCan() {
    const dat = (lb, khoa) => { if (lb) { lb.dataset.i18n = khoa; lb.innerHTML = NN.h(khoa); } };
    const nhanCua = (id) => { const el = g(id); return el && el.closest('.field') && el.closest('.field').querySelector('label'); };
    dat(nhanCua('f-weight_origin'), laGom() ? 'w_origin_gom' : 'w_origin_giao');
    dat(nhanCua('f-weight_dest'), laGom() ? 'w_dest_gom' : 'w_dest_giao');
    dat(g('lbl-price'), khoan() ? 'price_trip' : 'price_usd');
  }

  /* ---------------------------------------------------------------- dữ liệu */
  function phieuTrong() {
    return { id: null, doc_no: '', kind: 'giao', goods: [], company: 'EPL', goods_type: 'iron_ore', doc_date: EPL.homNay(), out_date: EPL.homNay(), fee_pct: 2, over_limit_t: 40, over_price: 1, price_ccy: 'USD', price_mode: 'ton',
      rate_usd: ty_gia.USD || 22000, rate_thb: ty_gia.THB || 700, rate_vnd: ty_gia.VND || 1.2, rate_cny: ty_gia.CNY || 3000, transport_status: 'dispatched', finance_status: 'unpaid', invoiced: false,
      sections: {}, expenses: [], logs: [] };
  }
  async function moPhieu(id) { moi = false; tabTay = false; HD_DOI = {}; soGoTay = false; xoaTim(); P = await API.get('/api/trips/' + id); await napLo(P.id); anPhieu(false); veHet(); napToKhoHang(); }
  /** Chưa chọn tờ nào: giấu thân phiếu và dải bước, hiện câu nhắc; ô chọn có dòng trống đứng đầu. */
  function chuaChon() {
    P = null; moi = false;
    g('px-chon').innerHTML = `<option value="" selected>— ${NN.t('px_chon_phieu')} —</option>` + dongChon();
    g('px-moi').hidden = !AUTH.la('yard');
    anPhieu(true);
  }
  function anPhieu(an) {
    q('#px-phieu').hidden = an; const b = q('.px-buoc'); if (b) b.hidden = an;
    ['px-luu', 'px-chung-tu', 'px-phieu-linh', 'px-hoa-don'].forEach(id => { const el = g(id); if (el) el.disabled = an; });
    let nhac = g('px-chua-chon');
    if (an) {
      if (!nhac) { nhac = document.createElement('div'); nhac.id = 'px-chua-chon'; nhac.className = 'card'; q('#px-phieu').before(nhac); }
      nhac.innerHTML = `<div class="bd empty">${NN.h('px_chua_chon')}</div>`; nhac.hidden = false;
    } else if (nhac) nhac.hidden = true;
  }
  /** Lô còn hàng trong kho bãi. Khi đang sửa một phiếu giao thì trừ phần chính nó đang giữ ra,
   *  không thì mở lại phiếu cũ sẽ thấy lô hết hàng dù chính nó là người giữ. */
  async function napLo(truPhieu) {
    try { LO = await API.get('/api/kho-hang/lo' + (truPhieu ? '?tru_phieu=' + encodeURIComponent(truPhieu) : '')); }
    catch (e) { LO = []; }
  }
  async function phieuMoi() { moi = true; tabTay = false; HD_DOI = {}; soGoTay = false; xoaTim(); P = phieuTrong(); anNhacOdo(); await napLo();
    // công-tơ-mét của xe đổi mỗi lần một chuyến về tới (Xe đã tới) — nạp lại để ô Lúc đi điền đúng số mới nhất
    DM.vehicles = await API.get('/api/vehicles').catch(() => DM.vehicles); const s = await API.get('/api/trips-so-moi').catch(() => ({ doc_no: '' })); P.doc_no = s.doc_no; anPhieu(false); veHet(); }
  function anNhacOdo() { const o = g('f-odo_out'); if (o) delete o.dataset.tuDien; const n = g('px-odo-nhac'); if (n) n.hidden = true; }
  /* PHIẾU ĐANG LẬP DỞ (rà 01/10: "không mất dữ liệu khi chuyển qua lại"). Bãi đang gõ phiếu mới mà bấm sang màn khác xem
   * tuyến, xem kho rồi quay lại — trước đây ra tờ trắng, mất hết chữ đã gõ. Rời màn lúc phiếu mới có nội dung thì giữ bản
   * nháp trong bộ nhớ (chỉ trong phiên này, đúng tài khoản này); vào lại bằng menu là mở lại đúng tờ đó, kèm câu báo. Nút
   * "+ Phiếu mới" và Lưu xong là bỏ nháp. Không phải tự mở phiếu cũ đã lưu (anh bắt 22/09) — đây là tờ chưa lưu của chính mình. */
  let NHAP = null;
  const uidNay = () => (AUTH.user ? AUTH.user.id : '');
  function coNoiDung() {
    if (!moi || !P) return false;
    return ['vehicle_id', 'driver_id', 'customer_id', 'route_id', 'odo_out', 'weight_origin', 'brand_model', 'plate_head', 'plate_trailer',
      'ore_bill_no', 'origin', 'destination'].some(c => P[c] != null && P[c] !== '')
      || (P.expenses || []).some(d => !d._goiY) || (P.goods || []).length > 0 || soGoTay;
  }
  function giuNhap() { if (coNoiDung()) NHAP = { uid: uidNay(), P: JSON.parse(JSON.stringify(P)), tab, soGoTay }; }
  async function moNhap() {
    const n = NHAP; NHAP = null;
    moi = true; tabTay = true; HD_DOI = {}; soGoTay = n.soGoTay; P = n.P; tab = n.tab || 'info'; anNhacOdo(); await napLo();
    // số gợi ý có thể đã có người dùng trong lúc rời màn — xin lại số mới (trừ khi người lập tự gõ số)
    if (!soGoTay) { const s = await API.get('/api/trips-so-moi?kind=' + encodeURIComponent(P.kind || 'giao')).catch(() => null); if (s && s.doc_no) P.doc_no = s.doc_no; }
    anPhieu(false); veHet(); EPL.toast(NN.t('px_nhap_mo_lai'), 'ok');
  }
  function docForm() {
    P.doc_no = g('px-doc-no').value.trim();
    [...COT_INFO, ...COT_TRANS, ...COT_POD].forEach(c => { const el = g('f-' + c); if (!el || el.disabled) return; P[c] = el.value === '' ? null : (SO.has(c) ? EPL.doc(el.value) : el.value); });
  }
  /** Phiếu thiếu xe / tài xế (máy chủ chặn THIEU_XE · THIEU_TAI_XE — chủ dự án 01/10): báo bằng tiếng đang dùng, mở mục I,
   *  tô và đặt con trỏ vào đúng ô. Hỏi trước khi gửi (chỉ khi mục I còn sửa được — đúng lúc máy chủ xét), để khỏi một lượt
   *  422 và câu tiếng Việt của máy chủ hiện ra ở chế độ Lào / Anh. Máy chủ vẫn là nơi quyết định. */
  const LOI_O = { THIEU_XE: ['f-vehicle_id', 'px_thieu_xe'], THIEU_TAI_XE: ['f-driver_id', 'px_thieu_tai_xe'] };
  function baoThieu(ma) {
    const [id, khoa] = LOI_O[ma];
    if (tab !== 'info' && tab !== 'all') datTab('info', true);
    const el = g(id);
    if (el) { el.classList.add('px-thieu'); el.focus(); el.addEventListener('input', () => el.classList.remove('px-thieu'), { once: true }); }
    EPL.toast(NN.t(khoa), 'loi');
  }
  const baoLoiLuu = (e) => (e && LOI_O[e.ma] ? baoThieu(e.ma) : EPL.baoLoi(e));
  async function luu() {
    docForm();
    if (suaDuoc('info')) {
      if (!P.vehicle_id) { baoThieu('THIEU_XE'); return false; }
      if (!(P.driver_id || String(P.driver_name || '').trim())) { baoThieu('THIEU_TAI_XE'); return false; }
    }
    const x = DM.vehicles.find(v => v.id === P.vehicle_id); if (x) { P.truck_no = x.truck_no; if (!P.brand_model) P.brand_model = x.brand_model; if (!P.plate_head) P.plate_head = x.plate_head; if (!P.plate_trailer) P.plate_trailer = x.plate_trailer; }
    const d = DM.drivers.find(v => v.id === P.driver_id); if (d) P.driver_name = d.name;
    const k = DM.customers.find(v => v.id === P.customer_id); if (k) P.customer_name = k.name;
    // chỉ gửi ô còn mở với vai này — ô của mục đã khoá gửi lên là máy chủ từ chối cả phiếu
    const body = {};
    if (suaDuoc('info')) ['doc_no', 'truck_no', 'driver_name'].forEach(c => { if (P[c] !== undefined) body[c] = P[c]; });
    if (suaDuoc('trans') && P.customer_name !== undefined) body.customer_name = P.customer_name;
    // Bãi không thấy, không nhập tiền bán (anh Khampla A2): ô giá cước, thuê xe, phí bị giấu nhưng tờ phiếu trắng vẫn mang
    // mặc định (USD, theo tấn, phí 2 %…) — không gửi, máy chủ tự điền mặc định / theo hồ sơ chủ xe (lỗi Bãi lưu 28/09)
    [...COT_INFO, ...COT_TRANS].forEach(c => { const el = g('f-' + c); if (vai() === 'yard' && COT_TIEN.includes(c)) return; if (P[c] !== undefined && (!el || !el.disabled)) body[c] = P[c]; });
    COT_POD.forEach(c => { const el = g('f-' + c); if (el && !el.disabled && P[c] !== undefined) body[c] = P[c]; });
    // hợp đồng: chỉ gửi khi kế toán TỰ ĐỔI ô chọn — không thì máy chủ tự điền theo khách / chủ xe
    Object.entries(HD_DOI).forEach(([k, v]) => { body[k] = v || null; });
    // chỉ gửi dòng chi của mục còn sửa được — mục khoá gửi lên là máy chủ từ chối cả phiếu
    if (suaDuoc('trans') && !gomMotDong()) body.goods = (P.goods || []).filter(g => g.loai !== 'hao_hut')
      .map(g => ({ loai: 'hang', goods_name: g.goods_name, qty_t: EPL.doc(g.qty_t), tu_phieu_id: g.tu_phieu_id || null, note: g.note || null }));
    body.expenses = P.expenses.filter(e => guiMuc(e.section)).map(e => {
      const x = { ...e, qty: EPL.doc(e.qty), acct_code: tkDong(e) || null };
      if (thayChi()) x.unit_price = EPL.doc(e.unit_price); else { delete x.unit_price; delete x.currency; }
      return x;
    });
    try {
      P = moi ? await API.post('/api/trips', body) : await API.put('/api/trips/' + P.id, body);
      moi = false; HD_DOI = {}; NHAP = null; EPL.toast(NN.t('saved'), 'ok'); veHet(); napToKhoHang();   // lưu phiếu giao có lấy hàng → máy lập phiếu xuất kho hàng
      history.replaceState(null, '', '#/phieu-xuat-xe?id=' + P.id);
      // ô chọn phiếu nạp lại NGẦM sau khi đã báo "Đã lưu" — chờ nó thì nút Lưu chậm thêm 0,1–0,5 s (đo 01/10)
      napDs().then(() => { if (P) veChon(); }).catch(() => {});
      return true;
    } catch (e) { baoLoiLuu(e); return false; }
  }
  /** Cạnh nút «Xe đã lăn bánh»: phiếu chi tạm ứng bên kế toán chưa ghi sổ thì nhắc ngay (vẫn để bấm — Sếp / Bãi quyết cho xe chạy). */
  function nhacUngTruocChay() {
    const c = P.chi_tam_ung || {};
    if (!c.o_ke_toan || !c.status || c.status === 'da_chi') return '';
    return `<span class="px-nhac-ung ${c.status === 'loi' ? 'loi' : ''}">${c.status === 'loi' ? NN.h('px_nhac_ung_loi') : NN.h('px_nhac_ung_cho', { so: c.document_no || '' })}</span>`;
  }
  /** Ô trạng thái phiếu chi tạm ứng bên hệ kế toán, cạnh nút của mục IV (từ lúc ghi sổ). */
  function oChiKeToan(st) {
    const c = P.chi_tam_ung || {};
    if (!c.o_ke_toan || moi || !['booked', 'paid'].includes(st) || !c.status) return '';
    const so = c.document_no ? `<b class="mono">${esc(c.document_no)}</b>` : '';
    if (c.status === 'da_chi') return `<span class="px-chi-kt ok" title="${esc(EPL.ngayGio(c.post_at))}">${NN.h('ck_da_chi')} ${so}${c.post_by ? ' · <span lang="lo">' + esc(c.post_by) + '</span>' : ''}</span>`;
    if (c.status === 'da_gui') return `<span class="px-chi-kt cho">${NN.h('ck_cho_chi')} ${so}</span><button type="button" class="btn sm" data-chi-kt="cap-nhat">${NN.h('ck_cap_nhat')}</button>`;
    return `<span class="px-chi-kt loi" title="${esc(c.error_message || '')}">${NN.h('ck_loi_ngan')}</span>` +
      (AUTH.la('expacct') ? `<button type="button" class="btn sm warn" data-chi-kt="gui">${NN.h('ck_gui_lai')}</button>` : '');
  }
  /** Ô trạng thái phiếu chi "Chi khác" mục V / VI bên hệ kế toán (01/10), cạnh nút của mục — từ lúc ghi sổ, khi mục có khoản
   *  quỹ trả ngay. Lần gần nhất chưa huỷ: đã chi · chờ thủ quỹ (Cập nhật) · lỗi / phiếu bị xoá bên đó (Gửi lại — KT Chi phí). */
  function oChiMuc(m, st) {
    const c = (P.chi_muc_ke_toan || {})[m];
    if (!c || !c.o_ke_toan || moi || !['booked', 'paid'].includes(st)) return '';
    const lan = (c.lan || []).filter(r => r.status !== 'huy'), r = lan[lan.length - 1];
    if (!r) return '';
    const so = r.document_no ? `<b class="mono">${esc(r.document_no)}</b>` : '';
    if (r.status === 'da_chi') return `<span class="px-chi-kt ok" title="${esc(EPL.ngayGio(r.post_at))}">${NN.h('ck_da_chi')} ${so}${r.post_by ? ' · <span lang="lo">' + esc(r.post_by) + '</span>' : ''}</span>`;
    if (r.status === 'da_gui') return `<span class="px-chi-kt cho">${NN.h('cmt_cho_chi')} ${so}</span><button type="button" class="btn sm" data-chi-muc="cap-nhat" data-muc="${m}">${NN.h('ck_cap_nhat')}</button>`;
    return `<span class="px-chi-kt loi" title="${esc(r.error_message || '')}">${NN.h(r.error_code === 'PHIEU_CHI_MAT' ? 'ck_phieu_mat' : 'ck_loi_ngan')}</span>` +
      (AUTH.la('expacct') ? `<button type="button" class="btn sm warn" data-chi-muc="gui" data-muc="${m}">${NN.h('ck_gui_lai')}</button>` : '');
  }
  async function chiMuc(m, viec) {
    try {
      const r = viec === 'gui' ? await API.post(`/api/trips/${P.id}/chi-muc-ke-toan/${m}`) : (await API.get(`/api/trips/${P.id}/chi-muc-ke-toan?cap_nhat=1`))[m];
      P = await API.get(`/api/trips/${P.id}`); veHet();
      const lan = ((r || {}).lan || []).filter(x => x.status !== 'huy'), x = lan[lan.length - 1] || {};
      EPL.toast(NN.t(x.status === 'da_chi' ? 'ck_da_chi_ngan' : x.status === 'da_gui' ? 'cmt_cho_chi' : 'ck_loi_ngan'), x.status === 'loi' ? 'loi' : 'ok');
    } catch (e) { EPL.baoLoi(e); }
  }
  /** Khối "Bút toán chờ gửi" ở cột bên — chỉ ba vai máy chủ gửi khối này (KT Thu/Chi VC, KT Chi phí VC, Sếp). */
  function veButToan() {
    const o = g('px-btc'), ds = (!moi && Array.isArray(P.but_toan_cho)) ? P.but_toan_cho.filter(b => b.status !== 'huy' || b.can_dao) : [];
    if (!o) return;
    o.hidden = !ds.length;
    if (!ds.length) return;
    const tien = (v, ma) => `${so(v, ['LAK', 'VND'].includes(ma) ? 0 : 2)} ${esc(ma)}`;
    g('px-btc-ds').innerHTML = ds.map(b => `<div class="px-btc-o">
        <div class="d"><b>${NN.h('btc_nguon_' + b.nguon)}</b>${b.can_dao ? tag('unpaid', 'btc_can_dao') : tag(b.status === 'da_gui' ? 'paid' : 'transit', b.status === 'da_gui' ? 'dt_st_da_gui' : 'dt_st_cho_gui')}</div>
        ${(b.dong || []).slice(0, 4).map(d => `<div class="l"><span class="mono">${esc(d.no)} / ${esc(d.co)}</span><span>${tien(d.tien, d.ccy)}</span></div>`).join('')}
        ${(b.dong || []).length > 4 ? `<div class="l muted">+ ${(b.dong || []).length - 4}</div>` : ''}</div>`).join('')
      + `<a class="small" href="#/but-toan-cho?trip_id=${esc(P.id)}&doc=${encodeURIComponent(P.doc_no || '')}">${NN.h('btc_xem_man')} →</a>`;
  }
  async function chiKeToan(viec) {
    try {
      const r = viec === 'gui' ? await API.post(`/api/trips/${P.id}/chi-ke-toan`) : await API.get(`/api/trips/${P.id}/chi-ke-toan?cap_nhat=1`);
      P = await API.get(`/api/trips/${P.id}`); veHet();
      EPL.toast(NN.t(r.status === 'da_chi' ? 'ck_da_chi_toast' : r.status === 'da_gui' ? 'ck_cho_chi' : 'ck_loi_ngan'), r.status === 'loi' ? 'loi' : 'ok');
    } catch (e) { EPL.baoLoi(e); }
  }
  async function duyet(m, hd) {
    if (moi) return EPL.toast(NN.t('save') + '?', 'loi');
    if (hd === 'send' && suaDuoc(m)) { await luu(); if (moi) return; }
    // kế toán gõ đơn giá rồi bấm Kiểm: lưu giá trước, không thì máy chủ thấy dòng giá 0 và chặn
    if (hd === 'verify' && MUC_CHI.includes(m) && coGiaDeGui(m)) { if (!await luu()) return; }
    // Mục I, II cũng vậy (rà 01/10): KT Thu/Chi gõ số phiếu quặng, giá cước rồi bấm Kiểm luôn — máy chủ trả phiếu chưa có
    // các ô đó, vẽ lại là mất chữ vừa gõ. Còn ô nào của mục này đang mở với vai này thì lưu trước rồi mới kiểm.
    else if (hd === 'verify' && (m === 'info' ? COT_INFO : m === 'trans' ? COT_TRANS : []).some(c => { const el = g('f-' + c); return el && !el.disabled; })) {
      if (!await luu()) return;            // lưu hỏng thì thôi kiểm — kiểm tiếp là vẽ lại từ máy chủ, mất chữ đang gõ
    }
    if (hd === 'return' || hd === 'unlock') { if (!await EPL.hoi(NN.t('a_' + hd), NN.t('confirm_action'))) return; }
    try { P = await API.post(`/api/trips/${P.id}/sections/${m}/${hd}`); veHet(); } catch (e) { EPL.baoLoi(e); }
  }
  async function doiTrangThai(tt) {
    if (tt === 'arrived') return baoXeToi();
    try { P = await API.post(`/api/trips/${P.id}/transport-status`, { status: tt }); DS = await napDs(); veHet(); napToKhoHang(); } catch (e) { EPL.baoLoi(e); }
  }
  /** "Xe đã tới · nhập cân cuối". Ngày về và km về điền sẵn theo số TÀI XẾ đã báo (nút "Báo đã về" trên điện thoại) — Bãi chỉ
   *  thêm cân. Phiếu gom: hàng vào kho theo cân tại mỏ — hỏi luôn ô đó (29/09); tài xế đã báo từ mỏ thì điền sẵn.
   *  DO gom thiếu cân tại bãi (05/10): máy chủ trả 422 THIEU_CAN_BAI — phiếu nhập kho hàng lập theo cân này. Mở lại đúng hộp vừa
   *  điền (giữ số đã gõ), câu lỗi của máy chủ ở đầu hộp, con trỏ ở ô "Cân tại bãi khi về". */
  async function baoXeToi() {
    const hoiMo = laGom() && gomMotDong();
    let cu = { weight_origin: P.weight_origin ?? '', weight_dest: P.weight_dest ?? '', back_date: P.back_date || EPL.homNay(), odo_back: P.odo_back ?? '',
      pod_no: P.pod_no || '', pod_receiver: P.pod_receiver || '' }, loi = '';
    for (;;) {
      const hop = EPL.hopNhap(NN.t('mark_arrived'), [
        ...(hoiMo ? [{ id: 'weight_origin', label: 'w_origin_gom', type: 'number', value: cu.weight_origin }] : []),
        { id: 'weight_dest', label: laGom() ? 'w_dest_gom' : 'weight_dest_prompt', type: 'number', value: cu.weight_dest },
        { id: 'back_date', label: 'd_back', type: 'date', value: cu.back_date },
        { id: 'odo_back', label: 'odo_back_prompt', type: 'number', value: cu.odo_back },
        ...(laGom() ? [] : [{ id: 'pod_no', label: 'pod_no', value: cu.pod_no },
          { id: 'pod_receiver', label: 'pod_receiver', value: cu.pod_receiver }]),
      ], NN.t('ok'));
      if (loi) baoLoiTrongHop(loi, 'weight_dest');           // hộp đã hiện (EPL.hoi mở hộp ngay khi gọi)
      const v = await hop;
      if (!v) return;
      if (hoiMo && !(EPL.doc(v.weight_origin) > 0)) return EPL.toast(NN.t('w_origin_gom') + '?', 'loi');
      const body = { status: 'arrived', weight_dest: v.weight_dest, back_date: v.back_date };
      if (hoiMo) body.weight_origin = v.weight_origin;
      if (v.odo_back !== '') body.odo_back = v.odo_back;
      if (v.pod_no) body.pod_no = v.pod_no; if (v.pod_receiver) body.pod_receiver = v.pod_receiver;
      let r;
      try { r = await API.post(`/api/trips/${P.id}/transport-status`, body); }
      catch (e) {
        if (e && e.ma === 'THIEU_CAN_BAI') { cu = Object.assign(cu, v); loi = e.message || NN.t('w_dest_gom'); continue; }
        return EPL.baoLoi(e);
      }
      P = r;
      try { DS = await napDs(); } catch (e) { EPL.baoLoi(e); }
      veHet(); napToKhoHang();             // DO gom tới bãi → máy vừa lập phiếu nhập kho hàng: hiện nút In
      return;
    }
  }
  /** Câu lỗi ở đầu hộp nhập đang mở (EPL.hopNhap — ô mang id "hn-<id>"): tô đỏ ô `id` và đặt con trỏ vào đó. */
  function baoLoiTrongHop(loi, id) {
    const nd = document.getElementById('ht-noi-dung'), o = document.getElementById('hn-' + id);
    if (nd) { const p = document.createElement('p'); p.className = 'px-hop-loi'; p.setAttribute('role', 'alert'); p.textContent = loi; nd.prepend(p); }
    if (o) {
      o.classList.add('px-thieu'); o.setAttribute('aria-invalid', 'true'); o.focus(); if (o.select) o.select();
      o.addEventListener('input', () => { o.classList.remove('px-thieu'); o.removeAttribute('aria-invalid'); }, { once: true });
    }
  }
  // việc mức phiếu còn lại đi qua đây: mở khoá phiếu (hoá đơn, thu tiền ở hệ kế toán từ 01/10 — trước đây tiêu đề hộp hỏi
  // là "Xác nhận đã thu tiền khách" cả khi bấm Mở khoá)
  async function hanhDongPhieu(hd, body) {
    if (!await EPL.hoi(NN.t(hd === 'mo-khoa' ? 'a_unlock_slip' : 'a_' + hd), NN.t('confirm_action'))) return;
    try { P = await API.post(`/api/trips/${P.id}/${hd}`, body || {}); DS = await napDs(); veHet(); } catch (e) { EPL.baoLoi(e); }
  }

  /* Sổ thu tiền (hoá đơn · đã thu · còn lại · nút "Mở trang kế toán") bỏ 01/10: đó là bản chép số của trang kế toán tạm — số thử,
   * đã cắt sổ. Thu tiền khách ở hệ kế toán anh Tune; màn Khách hàng → Công nợ đọc lại số bên đó. */

  /** Đổi xe giữa đường (C2.2): chọn xe mới, ghi lý do. Máy chủ để lại dòng diễn biến và kéo mục I
   *  về "đã nhập" để kế toán kiểm lại — thông tin xe trên phiếu đã khác. */
  async function doiXe() {
    const con = (DM.vehicles || []).filter(x => x.active !== false && x.id !== P.vehicle_id);
    if (!con.length) return EPL.toast(NN.t('no_data'), 'loi');
    const v = await EPL.hopNhap(NN.t('change_truck'), [
      { id: 'vehicle_id', label: 'truck_no', type: 'select', value: con[0].id, tim: 'px_tim_xe',
        options: con.map(x => [x.id, `${x.truck_no}${x.plate_head ? ' · ' + x.plate_head : ''}${x.status === 'on_trip' ? ' · ' + NN.t('v_on_trip') : ''}`, false,
          [x.plate_trailer, x.brand_model, x.owner_name].filter(Boolean).join(' ')]) },
      { id: 'driver_id', label: 'driver', type: 'select', value: '', tim: 'px_tim_tai_xe',
        options: [['', NN.t('ct_giu_tai_xe')]].concat((DM.drivers || []).filter(d => d.active !== false).map(d => [d.id, EPL.tenTaiXe(d), false,
          [d.driver_code, d.phone].filter(Boolean).join(' ')])) },
      { id: 'ly_do', label: 'ct_ly_do', value: '', lo: true },
      { id: 'xe_cu_hong', label: 'ct_xe_cu', type: 'select', value: '1',
        options: [['1', NN.t('ct_xe_cu_hong')], ['0', NN.t('ct_xe_cu_ranh')]] },
    ], NN.t('change_truck'));
    if (!v) return;
    if (!String(v.ly_do || '').trim()) return EPL.toast(NN.t('ct_ly_do') + '?', 'loi');
    try {
      P = await API.post(`/api/trips/${P.id}/doi-xe`, {
        vehicle_id: v.vehicle_id, driver_id: v.driver_id || null, ly_do: v.ly_do, xe_cu_hong: v.xe_cu_hong === '1' });
      DS = await napDs(); DM.vehicles = await API.get('/api/vehicles');
      EPL.toast(NN.t('saved'), 'ok'); veHet(); napToKhoHang();
    } catch (e) { EPL.baoLoi(e); }
  }

  /** Bước 14: kế toán rà lại rồi khoá. Máy chủ trả các điểm lệch; có lệch thì hiện ra cho kế toán đọc rồi mới xác nhận khoá. */
  async function khoaPhieu() {
    try {
      const k = await API.get(`/api/trips/${P.id}/kiem-lai`);
      // còn chỗ CHẶN khoá (dầu kho chưa cấp, phụ tùng chưa xuất, xe thuê thiếu giá bán) → báo ngay, không mở hộp Khoá (06/10)
      if ((k.chan || []).length) { EPL.toast(k.chan.map(chuMay).join(' · '), 'loi'); return; }
      const cb = k.canh_bao || [];
      const ok = await EPL.hoi(NN.t('a_lock'), cb.length
        ? `<p class="small muted">${NN.h('lock_warn')}</p><ul class="px-cb">${cb.map(x => `<li>${esc(chuMay(x))}</li>`).join('')}</ul>`
        : `<p>${NN.h('lock_ok')}</p>`, NN.t('a_lock'));
      if (!ok) return;
      P = await API.post(`/api/trips/${P.id}/khoa`, { xac_nhan: true }); DS = await napDs(); EPL.toast(NN.t('saved'), 'ok'); veHet();
    } catch (e) { EPL.baoLoi(e); }
  }
  /* ---- hợp đồng trên phiếu (chốt 24/09): máy chủ tự điền theo khách / chủ xe; kế toán đổi được bằng ô chọn ---- */
  let HD_DOI = {};                      // { contract_id: … } — chỉ những ô kế toán tự đổi
  const tagHd = (st) => st ? EPL.tag('hd_' + st, 'hd_' + st) : '';
  async function veHopDong() {
    const ve = async (o, loai, cot, doiTac, duocDoi) => {
      if (!o) return;
      // phiếu mới chưa lưu: máy chưa tìm hợp đồng (tự điền lúc lưu) — nói rõ thay cho một gạch trông như lỗi (29/09)
      if (moi) { o.innerHTML = `<span class="muted small">${NN.h('hd_luu_roi')}</span>`; return; }
      const so = P[cot === 'contract_id' ? 'contract_no' : 'hire_contract_no'];
      const st = P[cot === 'contract_id' ? 'contract_state' : 'hire_contract_state'];
      const chu = so ? `<span class="so">${esc(so)}</span> ${tagHd(st)}` : `<span class="muted small">${NN.h(doiTac ? 'hd_chua_co' : 'hd_chon_doi_tac')}</span>`;
      if (!duocDoi || moi || !doiTac || biKhoa()) { o.innerHTML = chu; return; }
      let ds = [];
      try { ds = await API.get(`/api/hop-dong?kind=${loai}&${loai === 'khach' ? 'customer_id' : 'owner_id'}=${encodeURIComponent(doiTac)}`); } catch (e) { ds = []; }
      if (!ds.length) { o.innerHTML = chu; return; }
      const chon = cot in HD_DOI ? HD_DOI[cot] : (P[cot] || '');
      o.innerHTML = `<select data-hd="${cot}"><option value="">— ${NN.h('hd_khong_dung')} —</option>${ds.map(h =>
        `<option value="${h.id}" ${h.id === chon ? 'selected' : ''} title="${esc(NN.t('hd_' + h.trang_thai))}">${esc(h.contract_no)}${h.trang_thai === 'con_han' ? '' : ' (' + esc(NN.t('hd_' + h.trang_thai)) + ')'}</option>`).join('')}</select> ${tagHd(st)}`;
      o.querySelector('select').addEventListener('change', (e) => { HD_DOI[cot] = e.target.value; });
    };
    await ve(g('px-hd'), 'khach', 'contract_id', P.customer_id, AUTH.la('acct', 'rev'));
    await ve(g('px-hd-thue'), 'thue_xe', 'hire_contract_id', P.company === 'joint' ? P.owner_id : null, AUTH.la('acct'));
    capNhatNutLuu();                     // ô chọn hợp đồng về sau cùng — có thể là ô duy nhất vai này còn đổi được
  }
  /* ---- tệp đính kèm: phiếu quặng của khách (Bãi chụp lúc bốc; kế toán xem khi kiểm mục II) và POD — biên bản
     giao nhận hàng (chụp khi xe tới). Cùng một chỗ chứa, khác `kind`. ---- */
  let TEP = [];
  async function veTep() {
    const o = g('px-tep'), op = g('px-tep-pod'); if (!o) return;
    if (moi || !P.id) { o.innerHTML = op.innerHTML = `<span class="small muted">${NN.h('attach_after_save')}</span>`; return; }
    try { TEP = await API.get(`/api/trips/${P.id}/tep`); } catch (e) { TEP = []; }
    veTepVao(o, TEP.filter(t => !['pod', 'pod_sign'].includes(t.kind)), 'ore_bill');
    if (op) veTepVao(op, TEP.filter(t => t.kind === 'pod'), 'pod');
    veKyNhan();
  }
  /** Ký nhận trên điện thoại tài xế (giao hàng hoàn tất): chữ ký · người nhận · giờ · vị trí · tình trạng. */
  function veKyNhan() {
    const o = g('px-pod-ky'), nut = g('px-in-bb'); if (!o) return;
    const ky = TEP.filter(t => t.kind === 'pod_sign').pop(), tk = encodeURIComponent(API.token());
    const co = !!(ky || P.pod_at);
    o.hidden = !co;
    if (co) o.innerHTML = `${ky ? `<img src="${esc(ky.url)}?tk=${tk}" alt="">` : ''}
      <div><div><b lang="lo">${esc(P.pod_receiver || '')}</b>${P.pod_phone ? ' · ' + esc(P.pod_phone) : ''}</div>
        <div class="small muted">${P.pod_at ? EPL.ngayGio(P.pod_at) : ''}${P.pod_by ? ' · ' + esc(P.pod_by) : ''}${P.pod_lat != null ? ` · <a href="https://maps.google.com/?q=${P.pod_lat},${P.pod_lng}" target="_blank" rel="noopener">${NN.h('gh_vi_tri')}</a>` : ''}</div>
        ${P.pod_condition ? `<div class="tt ${esc(P.pod_condition)}">${NN.h('gh_tt_' + P.pod_condition)}${P.pod_note ? ' · <span lang="lo">' + esc(P.pod_note) + '</span>' : ''}</div>` : ''}</div>`;
    nut.hidden = moi || !(co || P.pod_no);
    nut.onclick = () => EPL.bienBan.in(P, TEP);
  }
  function veTepVao(o, ds, kind) {
    const tk = API.token();
    const themDuoc = AUTH.la('yard', 'acct', 'rev') && !biKhoa();
    o.innerHTML = ds.map(t => `<div class="tep">
        ${t.la_anh ? `<img src="${esc(t.url)}?tk=${encodeURIComponent(tk)}" alt="">` : `<span class="pdf">PDF</span>`}
        <div><a href="${esc(t.url)}?tk=${encodeURIComponent(tk)}" target="_blank" rel="noopener" title="${esc(t.filename)}">${esc(t.filename)}</a>
          <small lang="lo">${esc(t.by_user || '')} · ${EPL.ngayGio ? EPL.ngayGio(t.ts) : EPL.ngay(t.ts)}</small></div>
        ${(AUTH.la('acct') || t.by_user === AUTH.user?.full_name) && !biKhoa() ? `<button type="button" class="x" data-xoa-tep="${t.id}" title="${esc(NN.t('delete'))}">×</button>` : ''}
      </div>`).join('') + (themDuoc ? `<label class="btn sm quiet them">+ ${NN.h('attach_add')}<input type="file" accept="image/*,application/pdf" data-them-tep></label>` : '')
      + (!ds.length && !themDuoc ? `<span class="small muted">${NN.h('attach_none')}</span>` : '');
    o.querySelectorAll('[data-them-tep]').forEach(inp => inp.addEventListener('change', async () => {
      const f = inp.files && inp.files[0]; if (!f) return;
      let nen; try { nen = await EPL.nenTep(f); } catch (e) { return EPL.baoLoi(e); }
      const fd = new FormData(); fd.append('tep', nen, nen.name); fd.append('kind', kind);
      try { await API.tep(`/api/trips/${P.id}/tep`, fd); EPL.toast(NN.t('saved'), 'ok'); await veTep(); } catch (e) { EPL.baoLoi(e); }
    }));
    o.querySelectorAll('[data-xoa-tep]').forEach(b => b.addEventListener('click', async () => {
      const ok = await EPL.hoi(NN.t('delete'), `<p>${NN.h('attach_del')}</p>`, NN.t('delete')); if (!ok) return;
      try { await API.goi('/api/tep/' + b.dataset.xoaTep, { method: 'DELETE' }); await veTep(); } catch (e) { EPL.baoLoi(e); }
    }));
  }
  async function xoaPhieu() {
    if (!await EPL.hoi(NN.t('delete') + ' ' + P.doc_no, NN.t('confirm_delete'), NN.t('delete'))) return;
    try { await API.del('/api/trips/' + P.id); DS = await napDs(); EPL.toast(NN.t('px_da_xoa'), 'ok');
      // Xoá xong KHÔNG tự mở phiếu mới nhất — đó là phiếu của người khác, gõ tiếp là gõ đè (cùng lỗi anh bắt 22/09).
      // Người lập phiếu (Bãi, Sếp) thì ra phiếu mới trắng; vai khác để ô chọn trống.
      if (AUTH.la('yard')) await phieuMoi(); else chuaChon(); } catch (e) { EPL.baoLoi(e); }
  }
  /** Ô chọn nơi đổ — lấy từ danh mục Điểm đổ. Kho EPL xếp trước, trạm ngoài xếp sau. */
  function diemChon(d) {
    const ds = DM.places || [];
    if (!ds.length) return `<option value="">${esc(NN.t('no_data'))}</option>`;
    const nhom = (loai) => ds.filter(x => x.owner_type === loai)
      .map(x => `<option value="${x.id}" ${x.id === d.place_id ? 'selected' : ''}>${esc(x.name)}</option>`).join('');
    return `<optgroup label="${esc(NN.t('fp_epl'))}">${nhom('epl')}</optgroup>`
      + `<optgroup label="${esc(NN.t('fp_ngoai'))}">${nhom('ngoai')}</optgroup>`;
  }
  function nguonCuaDiem(d) {
    const x = (DM.places || []).find(y => y.id === d.place_id);
    return x ? (x.owner_type === 'epl' ? 'kho' : 'mua') : (d.source || 'kho');
  }

  /** Lập phiếu lĩnh nhiên liệu cho chuyến này rồi mở màn Chứng từ để in. */
  async function lapPhieuLinh() {
    if (!P || !P.id) return;
    try {
      const v = await API.post(`/api/trips/${P.id}/vouchers`, { kind: 'fuel' });
      EPL.toast(NN.t('saved'), 'ok');
      EPL.di('de-nghi-xuat-kho', { id: P.id, v: v[0] ? v[0].id : '' });
    } catch (e) { EPL.baoLoi(e); }
  }

  // GỢI Ý CHI PHÍ theo tuyến (sếp 30/09: "dựa vào Excel kê sẵn chi phí kiểu gợi ý, họ thêm bớt chỉnh sửa bình thường"):
  // chọn tuyến thì mục III, IV, VI tự có các dòng của bộ gợi ý — bộ riêng của tuyến, không có thì bộ chung Excel. Dòng gợi ý
  // chưa ai đụng (_goiY) thì đổi tuyến là thay; mục đã có dòng người lập tự khai thì không đè. Bãi không nhận đơn giá —
  // máy chủ điền giá gợi ý lúc lưu (như phí cao tốc theo tuyến), kế toán sửa khi kiểm.
  function dienGoiY(r) {
    if (!r || !Array.isArray(r.goi_y)) return;
    let dien = 0;
    ['fuel', 'travel', 'other'].forEach(m => {
      if (!suaDuoc(m)) return;
      P.expenses = P.expenses.filter(d => !(d.section === m && d._goiY));
      if (P.expenses.some(d => d.section === m)) return;
      r.goi_y.filter(x => x.section === m).forEach(x => {
        const d = { section: m, item_key: x.item_key || null, item_name: x.item_name || null, qty: x.qty, unit_price: x.unit_price || 0,
          currency: x.currency || 'LAK', place_id: x.place_id || null, paid_by_epl: true, pay_channel: x.pay_channel || null, _goiY: true };
        if (m === 'fuel') { d.source = nguonCuaDiem(d); if (P.company === 'joint') d.paid_by_epl = d.source === 'kho'; }
        // 06/10 (chạy thử kịch bản CA-3): xe THUÊ — khoản đi đường gợi ý theo tuyến (tiền nước, tiền chuyến, điện thoại…) mặc định
        // «Chủ xe tự trả»: EPL không trả lương tài xế của chủ xe, EPL ứng là tạm ứng ghi công nợ chủ xe — chỉ khi Bãi chọn «EPL ứng».
        // Trước đây gợi ý «EPL ứng · Chi ngay khi xe đi» → thành tạm ứng 4022/1011 cho đối tác nếu Bãi quên đổi.
        else if (P.company === 'joint') d.paid_by_epl = false;
        d.acct_code = null;
        P.expenses.push(d); dien++;
      });
    });
    const o = g('px-goi-y-cp');
    if (o) { o.hidden = !dien; o.innerHTML = dien ? NN.h(r.goi_y_nguon === 'tuyen' ? 'cp_goi_y_tuyen' : 'cp_goi_y_chung', { ten: r.name }) : ''; }
    if (dien) { veChi(); veVaiVaTrangThai(); }
  }

  function themDong(m) {
    if (!suaDuoc(m)) return;
    const khoDau = (DM.places || []).find(x => x.owner_type === 'epl');
    const d = m === 'fuel' ? { section: 'fuel', item_key: 'diesel', qty: 0, unit_price: 0, currency: 'LAK', place_id: khoDau ? khoDau.id : null, paid_by_epl: true, source: 'kho' }
      : { section: m, item_key: KM.items[m][0], qty: 1, unit_price: 0, currency: 'LAK', paid_by_epl: true, source: m === 'repair' ? 'mua' : null };
    d.acct_code = null;
    P.expenses.push(d);
    veChi(); veVaiVaTrangThai();
  }

  EPL.modules['phieu-xuat-xe'] = {
    async init(r, ctx) {
      root = r;
      [KM, DS, ty_gia, DM.customers, DM.vehicles, DM.drivers, DM.routes, DM.parts, DM.places, DM.the] = await Promise.all([
        API.get('/api/khoan-muc'), napDs(), API.get('/api/rates'), API.get('/api/customers'),
        API.get('/api/vehicles'), API.get('/api/drivers'), API.get('/api/routes'), API.get('/api/parts'),
        API.get('/api/fuel-places'), API.get('/api/the-cao-toc')]);
      EPL.themTu(KM.names);              // tên khoản mục thêm ở màn Khoản mục chi phí (08/10) — NN.t(item_key) như khoản có sẵn
      g('px-ve').addEventListener('click', () => EPL.di('theo-doi'));
      g('px-moi').addEventListener('click', () => { NHAP = null; phieuMoi().catch(EPL.baoLoi); });
      g('px-luu').addEventListener('click', luu);
      // Phiếu đề nghị thu (30/09): khoá phiếu là máy lập — nút mở màn Phiếu đề nghị thu đúng phiếu này. Chỉ vai thấy tiền bán.
      g('px-hoa-don').hidden = !AUTH.la('acct', 'expacct', 'rev', 'treasury', 'cash', 'fuel');
      // lập tờ đề nghị tạm ứng / xuất nhiên liệu: đúng các vai máy chủ cho lập (POST /api/trips/{id}/vouchers)
      const lapDeNghi = AUTH.la('yard', 'acct', 'expacct', 'fuel', 'cash', 'treasury');
      g('px-chung-tu').hidden = !lapDeNghi; g('px-phieu-linh').hidden = !lapDeNghi;
      g('px-hoa-don').addEventListener('click', () => P && P.id && EPL.di('de-nghi-thu', { id: P.id, thang: String(P.doc_date || '').slice(0, 7) }));
      root.querySelectorAll('#px-chon-loai button').forEach(b => b.addEventListener('click', () => {
        const el = g('f-kind'); if (!el || el.disabled) return;
        el.value = b.dataset.loai; el.dispatchEvent(new Event('input', { bubbles: true }));
      }));
      // Phiếu đề nghị tạm ứng: lập (hoặc cập nhật) tờ tạm ứng rồi mở màn in — không có khoản tiền mặt nào thì vẫn mở màn (màn
      // tự ghi "không có khoản tạm ứng"). Tờ tạm ứng KHÔNG có mã QR (chủ dự án đồng ý 01/10): tài xế lĩnh tiền ở quỹ kế toán
      // bằng số DO; chỉ tờ đề nghị xuất kho nhiên liệu còn QR cho thủ kho quét.
      g('px-chung-tu').addEventListener('click', async () => {
        if (!P || !P.id) return;
        try { await API.post(`/api/trips/${P.id}/vouchers`, { kind: 'advance' }); }
        catch (e) { if (!(e instanceof EPL.LoiAPI) || e.status !== 422) return EPL.baoLoi(e); }
        EPL.di('de-nghi-chi', { id: P.id, loai: 'advance' });
      });
      g('px-phieu-linh').addEventListener('click', lapPhieuLinh);
      g('px-in-kho-hang').addEventListener('click', inToKhoHang);
      // địa chỉ ghi theo tờ đang mở: tải lại trang hay bấm Quay lại từ màn khác là về đúng tờ này, không ra tờ trắng (rà 01/10)
      g('px-chon').addEventListener('change', e => { if (e.target.value) moPhieu(e.target.value).then(() => { if (P && P.id) history.replaceState(null, '', '#/phieu-xuat-xe?id=' + P.id); }).catch(EPL.baoLoi); });
      let hen = null;
      g('px-tim').addEventListener('input', () => { clearTimeout(hen); hen = setTimeout(() => napDs().then(() => {
        // chỉ nạp lại ô chọn — KHÔNG tự mở phiếu tìm được: người dùng có thể đang sửa dở phiếu khác
        if (P || moi) veChon(); else chuaChon();
      }).catch(EPL.baoLoi), 350); });
      root.querySelectorAll('.px-them').forEach(b => b.addEventListener('click', () => themDong(b.dataset.them)));
      root.querySelectorAll('[data-loc]').forEach(inp => inp.addEventListener('input', () => locChon(inp, true)));
      g('px-hang-them').addEventListener('click', () => { (P.goods = P.goods || []).push({ loai: 'hang', goods_name: NN.t('iron_ore'), qty_t: 0, tu_phieu_id: '' }); veHang(); });
      // đầu vào mục I–II → cập nhật số ngay
      [...COT_INFO, ...COT_TRANS].forEach(c => { const el = g('f-' + c); if (!el) return; el.addEventListener('input', () => {
        P[c] = el.value === '' ? null : (SO.has(c) ? el.value : el.value);
        if (c === 'company') { P.expenses.forEach(e => { e.acct_code = null; }); if (P.company === 'joint' && (P.hire_price == null || P.hire_price === '')) { P.hire_price = P.price; g('f-hire_price').value = P.price ?? ''; P.hire_ccy = maCuoc(); g('f-hire_ccy').value = P.hire_ccy; } q('#px-phieu').classList.toggle('is-joint', P.company === 'joint'); veChi(); }
        if (c === 'route_id') { const r = DM.routes.find(x => x.id === el.value); if (r) { g('f-origin').value = P.origin = r.origin; g('f-destination').value = P.destination = r.destination; dienGoiY(r); } }
        if (c === 'route_id' || c === 'customer_id') dienGiaHopDong();
        if (c === 'price_mode') nhanCan();   // "Đơn giá mỗi tấn" ↔ "Giá trọn chuyến" đổi ngay khi chọn
        if (c === 'kind') {
          // phiếu mới: số gợi ý theo loại — gom ra G4-…, giao ra T4-… (chỉ khi người lập chưa tự gõ số khác)
          // Vẽ lại NGAY (01/10, chủ dự án: bấm thẻ Gom / Giao phải chờ lâu mới nhảy). Trước đây chờ nạp lại lô kho bãi rồi
          // mới vẽ — lô không phụ thuộc loại DO và đã nạp lúc mở phiếu, nên bỏ hẳn lần nạp đó. Số gợi ý theo loại lấy
          // ngầm, về tới thì chỉ điền ô số phiếu và cột bên — kèm loại lúc hỏi, bấm qua lại nhanh thì bỏ kết quả cũ.
          const loaiHoi = P.kind || 'giao';
          if (moi && !soGoTay) API.get('/api/trips-so-moi?kind=' + encodeURIComponent(loaiHoi)).then(s => {
            if (!s || !s.doc_no || !moi || soGoTay || (P.kind || 'giao') !== loaiHoi) return;
            P.doc_no = s.doc_no; const o = g('px-doc-no'); if (o) o.value = s.doc_no; veBen();
          }).catch(() => {});
          veHet();
        }
        if (c === 'odo_out') { delete el.dataset.tuDien; g('px-odo-nhac').hidden = true; }   // Bãi tự gõ thì thôi không đè nữa
        if (c === 'vehicle_id' && moi) {
          // Lúc đi (chủ dự án 29/09): phiếu mới chọn xe thì điền sẵn công-tơ-mét của xe — km về chuyến trước ("Xe đã tới"
          // ghi vào xe). Vẫn sửa được: số thật là đồng hồ lúc lăn bánh. Bãi đã tự gõ thì không đè.
          const x = DM.vehicles.find(v => v.id === el.value), o = g('f-odo_out');
          if (o && (!o.value || o.dataset.tuDien === '1')) {
            const km = x && x.odometer_km ? String(x.odometer_km) : '';
            o.value = km; P.odo_out = km || null; o.dataset.tuDien = km ? '1' : '';
            g('px-odo-nhac').hidden = !km;
          }
        }
        if (c === 'vehicle_id') { const x = DM.vehicles.find(v => v.id === el.value); if (x) { g('f-brand_model').value = P.brand_model = x.brand_model || ''; g('f-plate_head').value = P.plate_head = x.plate_head || ''; g('f-plate_trailer').value = P.plate_trailer = x.plate_trailer || ''; if (x.owner_type === 'joint') { P.company = 'joint'; g('f-company').value = 'joint'; g('f-owner_name').value = P.owner_name = x.owner_name || ''; q('#px-phieu').classList.add('is-joint'); veChi(); } } }
        veSo();
      }); });
      // Số phiếu và ba ô POD cũng ghi NGAY vào P như các ô mục I–II (rà 01/10): veHet() — đổi tiếng, bấm thẻ Gom / Giao, đổi
      // loại phiếu — điền lại mọi ô từ P, nên trước đây số phiếu tự gõ và số / ngày / người nhận POD chưa lưu bị xoá trắng.
      g('px-doc-no').addEventListener('input', (e) => { if (!P) return; P.doc_no = e.target.value; if (moi) soGoTay = !!e.target.value.trim(); });
      COT_POD.forEach(c => { const el = g('f-' + c); if (el) el.addEventListener('input', () => { if (P) P[c] = el.value === '' ? null : el.value; }); });
      const t = ctx.tham || {};
      // KHÔNG tự mở phiếu cũ khi vào màn không kèm tham số (lỗi anh chủ dự án bắt 22/09: Bãi vào là
      // thấy phiếu mới nhất đang mở sẵn, gõ là gõ đè lên phiếu đó). Bãi và Sếp — người lập phiếu — vào
      // là PHIẾU MỚI trắng; vai khác không lập phiếu thì để ô chọn trống kèm câu nhắc, tự chọn tờ cần xem.
      // Tờ đang lập dở của chính người này (rời màn chưa lưu) thì mở lại — vào bằng menu, hoặc nút "Tạo phiếu" không kèm xe /
      // tài xế; mở từ hồ sơ một xe / một tài xế là muốn tờ mới cho đúng xe / người đó.
      if (NHAP && NHAP.uid !== uidNay()) NHAP = null;
      const moLaiNhap = NHAP && AUTH.la('yard') && !t.id && !t.xe && !t.tai_xe;
      if (moLaiNhap) await moNhap(); else if (t.moi) await phieuMoi(); else if (t.id) await moPhieu(t.id); else if (AUTH.la('yard')) await phieuMoi(); else chuaChon();
      // Mở từ màn Xe (nút "Tạo phiếu xuất xe" ở hồ sơ một chiếc): chọn sẵn chiếc đó.
      if (t.moi && t.xe && DM.vehicles.some(v => v.id === t.xe)) {
        const el = g('f-vehicle_id'); if (el) { el.value = t.xe; el.dispatchEvent(new Event('input', { bubbles: true })); }
      }
      // Mở từ màn Tài xế (nút "Tạo phiếu xuất xe" ở hồ sơ một người, ?tai_xe=): chọn sẵn người đó — trước đây tham số này
      // bị bỏ qua, phiếu mới ra ô tài xế trống (rà 01/10)
      if (t.moi && t.tai_xe && DM.drivers.some(d => d.id === t.tai_xe)) {
        const el = g('f-driver_id'); if (el) { el.value = t.tai_xe; el.dispatchEvent(new Event('input', { bubbles: true })); }
      }
      if (t.tab && (MUC.includes(t.tab) || t.tab === 'all')) datTab(t.tab, true);
      theoDoiDinh();
    },
    onLang() { if (P) veHet(); else if (root) chuaChon(); },
    xuatExcel: (r) => xuatExcelPhieu(r),
    destroy() { giuNhap(); if (theoDinh) { theoDinh.disconnect(); theoDinh = null; } },
  };
})();

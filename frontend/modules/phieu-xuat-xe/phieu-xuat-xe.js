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
  /** Định khoản mặc định — chép luật máy chủ: xe nhà 625/614, xe liên kết 4022; kho …/1371, mua ngoài …/4021. */
  function tkMacDinh(m, d) {
    const cty = P && P.company === 'joint' ? 'joint' : 'EPL', rule = KM.acct_rule[cty];
    let src = d && d.source;
    if (m === 'fuel') src = nguonCuaDiem(d || {});
    if (m === 'repair' && src !== 'kho') src = 'mua';
    if (m === 'travel' || m === 'other') return rule.mua[m];
    return rule[src][m];
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
  const giaDong = (d) => (P.company === 'joint' && d.section === 'fuel' && nguonCuaDiem(d) === 'kho' && d.sale_price != null && d.sale_price !== '') ? d.sale_price : d.unit_price;
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
    g('f-vehicle_id').innerHTML = `<option value="">—</option>` + DM.vehicles.filter(x => x.active || x.id === P.vehicle_id).map(x => `<option value="${x.id}" ${x.id === P.vehicle_id ? 'selected' : ''}>${esc(x.truck_no)} · ${esc(x.plate_head || '')}${x.owner_type === 'joint' ? ' · ' + NN.t('co_joint') : ''}</option>`).join('');
    g('f-driver_id').innerHTML = `<option value="">—</option>` + DM.drivers.filter(x => x.active || x.id === P.driver_id).map(x => `<option value="${x.id}" ${x.id === P.driver_id ? 'selected' : ''}>${esc(x.name)}</option>`).join('');
    g('f-route_id').innerHTML = `<option value="">—</option>` + DM.routes.filter(x => x.active || x.id === P.route_id).map(x => `<option value="${x.id}" ${x.id === P.route_id ? 'selected' : ''}>${esc(x.name)} · ${so(x.total_km, 1)} km${x.return_km ? ' · ↩ ' + so(x.return_km, 1) + ' km' : ''}</option>`).join('');
    g('f-customer_id').innerHTML = `<option value="">—</option>` + DM.customers.filter(x => x.active || x.id === P.customer_id).map(x => `<option value="${x.id}" ${x.id === P.customer_id ? 'selected' : ''}>${esc(x.name)}</option>`).join('');
  }
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
      const lk = k.lk; const cols = m === 'fuel' ? 9 : (m === 'repair' ? 8 : 7);
      tb.querySelector('tfoot').innerHTML = `<tr><td></td><td>${NN.h('total')}</td>${m === 'fuel' ? `<td class="num">${so(P.expenses.filter(d => d.section === 'fuel').reduce((a, d) => a + EPL.doc(d.qty), 0))}</td><td></td><td></td>` : (m === 'repair' ? '<td></td><td></td><td></td>' : '<td></td><td></td>')}<td class="num px-gia"><b>${P.expenses.some(d => d.section === m && anGia(d)) ? '—' : so(k.chi[m])}</b></td><td colspan="${cols - (m === 'fuel' ? 6 : 5)}"></td></tr>`; });
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
    const lk = P.company === 'joint', tk = KM.acct_codes;
    MUC_CHI.forEach(m => {
      const tb = q(`table[data-bang="${m}"] tbody`), khoa = KM.items[m], khoaDuoc = suaDuoc(m);
      const dong = P.expenses.map((d, i) => ({ d, i })).filter(x => x.d.section === m);
      tb.innerHTML = dong.length ? dong.map(({ d, i }, n) => {
        const tuGo = !khoa.includes(d.item_key);
        const sel = `<select data-i="${i}" data-f="item_key" ${khoaDuoc ? '' : 'disabled'}>${khoa.map(k => `<option value="${k}" ${k === d.item_key ? 'selected' : ''}>${esc(NN.t(k))}</option>`).join('')}<option value="" ${tuGo ? 'selected' : ''}>${esc(NN.t('x_custom'))}</option></select>${tuGo ? `<input data-i="${i}" data-f="item_name" value="${esc(d.item_name || '')}" placeholder="…" ${khoaDuoc ? '' : 'disabled'} style="margin-top:4px">` : ''}`;
        const giaMo = giaDuoc(m, d);
        const inp = (f, cls = 'num') => f === 'unit_price'
          ? `<input class="${cls}${giaMo && d.paid_by_epl && EPL.doc(d.qty) > 0 && !EPL.doc(d.unit_price) ? ' px-can-gia' : ''}" data-i="${i}" data-f="${f}" value="${esc(d[f] == null ? '' : d[f])}" ${giaMo ? '' : 'disabled'} inputmode="decimal" title="${esc(nguonKho(m, d) ? NN.t('price_avg_kho') : '')}">`
          : `<input class="${cls}" data-i="${i}" data-f="${f}" value="${esc(d[f] == null ? '' : d[f])}" ${khoaDuoc ? '' : 'disabled'} inputmode="decimal">`;
        // Phí cầu đường (C6.1): trả bằng THẺ nào. Thẻ bị trừ khi kế toán ghi sổ mục IV, nên chọn rồi
        // vẫn đổi được tới lúc đó; đã trừ rồi thì khoá lại và nói rõ.
        const theDuoc = m === 'travel' && ['x_toll', 'x_bridge'].includes(d.item_key);
        const daTru = !!d.card_move_id;
        const theSel = !theDuoc ? '' : `<select data-i="${i}" data-f="toll_card_id" ${khoaDuoc && !daTru ? '' : 'disabled'} style="margin-top:4px">
            <option value="">${esc(NN.t('tct_tien_mat'))}</option>${DM.the.filter(t => t.active || t.id === d.toll_card_id)
              .map(t => `<option value="${t.id}" ${t.id === d.toll_card_id ? 'selected' : ''}>${esc(t.card_no)} · ${so(t.balance, EPL.leTien(t.currency))} ${esc(t.currency)}</option>`).join('')}</select>${
            daTru ? `<div class="small muted">${esc(NN.t('tct_da_tru'))} ✓</div>` : ''}`;
        // CÁCH TRẢ (Excel anh Khampla, 29/09): như cột ghi chú của tờ Excel — chi ngay khi xe đi (vào tạm ứng) · trả cùng
        // lương · nợ nhà cung cấp. Dòng phí cao tốc / cầu đường đã có ô thẻ ở trên (tiền mặt hay thẻ) nên không hỏi thêm.
        const caDuoc = (m === 'travel' || m === 'other') && !theDuoc;
        // Xe THUÊ không có "trả cùng lương" — EPL không trả lương tài xế của chủ xe; khoản EPL ứng là tạm ứng ghi công nợ chủ
        // xe (chủ dự án 30/09, chép luật máy chủ): chỉ còn "chi ngay khi xe đi" và "nợ NCC".
        const caMoc = d.pay_channel || ((KM.pay_default || {})[d.item_key] || 'tien_mat');
        const caEff = lk && caMoc === 'luong' ? 'tien_mat' : caMoc;
        const caSel = !caDuoc ? '' : `<select class="px-ca" data-i="${i}" data-f="pay_channel" ${khoaDuoc ? '' : 'disabled'} style="margin-top:4px">${
          [['tien_mat', 'pm_on_dispatch'], ['luong', 'pm_trip_salary'], ['ncc', 'pm_supplier']].filter(([v]) => !(lk && v === 'luong')).map(([v, k]) => `<option value="${v}" ${v === caEff ? 'selected' : ''}>${esc(NN.t(k))}</option>`).join('')}</select>`;
        const pay = `<td class="px-lk"><span class="px-pay"><button type="button" class="${d.paid_by_epl ? 'on' : ''}" data-i="${i}" data-pay="1" ${khoaDuoc ? '' : 'disabled'}>${esc(NN.t('pay_epl'))}</button><button type="button" class="${!d.paid_by_epl ? 'on' : ''}" data-i="${i}" data-pay="0" ${khoaDuoc ? '' : 'disabled'}>${esc(NN.t('pay_own'))}</button></span></td>`;
        const acct = `<td class="px-gia"><button type="button" class="acct px-acct" data-acct="${i}" ${AUTH.la('acct', 'fuel', 'rev') ? '' : 'disabled'} title="${esc(NN.t('acct_pair'))}">${esc(d.acct_code || tkMacDinh(m, d))}</button></td>`;
        const xoa = `<td class="no-print">${khoaDuoc ? `<button type="button" class="x" data-xoa="${i}" title="${esc(NN.t('delete'))}">×</button>` : ''}</td>`;
        if (m === 'fuel') {
          // Đổ dầu ở trạm ngoài (nhất là bên Việt Nam): tài xế trả tiền mặt, hay TRẠM GHI NỢ để cuối
          // tháng EPL trả / cấn trừ với khách (C5.1). Chỉ hỏi khi nơi đổ là trạm ngoài.
          const muaNgoai = nguonCuaDiem(d) !== 'kho';
          const noSel = !muaNgoai ? '' : `<label class="px-ghino small"><input type="checkbox" data-i="${i}" data-f="ghi_no" ${d.ghi_no ? 'checked' : ''} ${khoaDuoc ? '' : 'disabled'}> ${esc(NN.t('ncc_ghi_no'))}</label>`;
          // Xe thuê, dầu KHO, EPL ứng = xuất bán cho chủ xe: ô GIÁ BÁN dưới giá vốn bình quân — KT kho xăng dầu gõ khi kiểm
          // mục III (29/09). Vai không thấy tiền bán thì máy chủ không gửi ô này → không hiện.
          const banDuoc = lk && !muaNgoai && d.paid_by_epl;
          const giaBanMo = banDuoc && thayChi() && suaTienDuoc('fuel');
          const ban = !(banDuoc && ('sale_price' in d || giaBanMo)) ? '' : `<div class="px-ban"><span class="small muted">${NN.h('sale_price')}</span><input class="num${giaBanMo && EPL.doc(d.qty) > 0 && !EPL.doc(d.sale_price) ? ' px-can-gia' : ''}" data-i="${i}" data-f="sale_price" value="${esc(d.sale_price == null ? '' : d.sale_price)}" ${giaBanMo ? '' : 'disabled'} inputmode="decimal"></div>`;
          return `<tr data-i="${i}" class="${lk && !d.paid_by_epl ? 'own' : ''}"><td>${n + 1}</td><td>${sel}</td><td>${inp('qty')}</td><td class="px-gia">${inp('unit_price')}${ban}</td>
          <td class="px-gia"><select data-i="${i}" data-f="currency" ${giaMo ? '' : 'disabled'}>${['LAK', 'VND', 'THB', 'USD'].map(c => `<option ${c === d.currency ? 'selected' : ''}>${c}</option>`).join('')}</select></td><td class="num amt px-gia"></td>
          <td><select data-i="${i}" data-f="place_id" ${khoaDuoc ? '' : 'disabled'}>${diemChon(d)}</select>
            <div class="small muted px-nguon">${NN.h(nguonCuaDiem(d) === 'kho' ? 'src_kho' : 'src_mua')}</div>${noSel}</td>${pay}${acct}${xoa}</tr>`;
        }
        let nguon = '';
        if (m === 'repair') {
          const kho = d.source === 'kho', daXuat = !!d.stock_move_id;
          nguon = `<td><select data-i="${i}" data-f="source" ${khoaDuoc && !daXuat ? '' : 'disabled'}><option value="mua" ${!kho ? 'selected' : ''}>${esc(NN.t('src_mua'))}</option><option value="kho" ${kho ? 'selected' : ''}>${esc(NN.t('src_kho'))}</option></select>${
            kho ? `<select data-i="${i}" data-f="part_id" ${khoaDuoc && !daXuat ? '' : 'disabled'} style="margin-top:4px"><option value="">—</option>${DM.parts.map(p => `<option value="${p.id}" ${p.id === d.part_id ? 'selected' : ''}>${esc(p.name)} · ${so(p.qty)}</option>`).join('')}</select>` : ''}${
            daXuat ? `<div class="small muted">${esc(NN.t('fs_out'))} ✓</div>` : ''}</td>`;
        }
        return `<tr data-i="${i}" class="${lk && !d.paid_by_epl ? 'own' : ''}"><td>${n + 1}</td><td>${sel}${theSel}${caSel}</td>${nguon}<td>${inp('qty')}</td><td class="px-gia">${inp('unit_price')}</td><td class="num amt px-gia"></td>${pay}${acct}${xoa}</tr>`;
      }).join('') : `<tr><td colspan="10" class="empty small">${NN.h('no_data')}</td></tr>`;
    });
    // dòng bản chất ở đầu mục III, IV: nội bộ (xe nhà) · xuất bán / ghi công nợ chủ xe (xe thuê) — 29/09
    root.querySelectorAll('.px-ht').forEach(el => { el.innerHTML = EPL.banChat(el.dataset.ht, EPL.maBanChat(el.dataset.ht, P.company), P.owner_name); });
    q('#px-phieu').querySelectorAll('.px-chi [data-f]').forEach(el => el.addEventListener('input', e => {
      const d = P.expenses[+el.dataset.i], f = el.dataset.f; d[f] = el.value; delete d._goiY;   // người lập đã sửa → không còn là dòng gợi ý
      if (f === 'item_key') { if (el.value === '') d.item_name = d.item_name || ''; else d.item_name = null; if (!['x_toll', 'x_bridge'].includes(el.value)) d.toll_card_id = null; d.pay_channel = null; veChi(); }
      if (f === 'toll_card_id') { d.toll_card_id = el.value || null; }
      if (f === 'ghi_no') { d.ghi_no = el.checked; }
      if (f === 'place_id') {
        // Nơi đổ quyết định LĨNH hay MUA, kéo theo định khoản …/371 hay …/402.
        d.source = nguonCuaDiem(d);
        if (P.company === 'joint') d.paid_by_epl = d.source === 'kho';
        d.acct_code = tkMacDinh('fuel', d); veChi();
      }
      if (f === 'source') { if (el.value !== 'kho') d.part_id = null; d.acct_code = tkMacDinh('repair', d); veChi(); }
      if (f === 'part_id') { const p = DM.parts.find(x => x.id === el.value); if (p) { d.item_key = null; d.item_name = p.name; if (thayGiaKho()) d.unit_price = p.unit_price || 0; else delete d.unit_price; } veChi(); }
      veSo();
    }));
    root.querySelectorAll('.px-chi [data-pay]').forEach(b => b.addEventListener('click', () => { P.expenses[+b.dataset.i].paid_by_epl = b.dataset.pay === '1'; veChi(); veSo(); }));
    root.querySelectorAll('.px-chi [data-xoa]').forEach(b => b.addEventListener('click', () => { P.expenses.splice(+b.dataset.xoa, 1); veChi(); veSo(); }));
    root.querySelectorAll('.px-chi [data-acct]').forEach(b => b.addEventListener('click', async () => {
      const d = P.expenses[+b.dataset.acct]; const v = await EPL.chonDinhKhoan(d.acct_code || tkMacDinh(d.section, d));
      if (v) { d.acct_code = v; veChi(); }
    }));
    veSo();
  }
  const VAI_SAU_KHOA = ['acct', 'expacct', 'rev', 'treasury', 'cash', 'fuel', 'admin'];
  const biKhoa = () => !moi && P.locked && !VAI_SAU_KHOA.includes(vai());
  function suaDuoc(m) { if (moi) return true; if (biKhoa()) return false; const st = (P.sections || {})[m] || 'wait'; return vai() === 'admin' || (perm().edit.includes(m) && (st === 'wait' || st === 'entered')); }
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
  function giaDuoc(m, d) {
    if (!thayChi() || nguonKho(m, d)) return false;
    if (moi) return true;
    return suaDuoc(m) || (MUC_CHI.includes(m) && !biKhoa() && perm().verify.includes(m) && ['wait', 'entered'].includes((P.sections || {})[m] || 'wait'));
  }
  const suaPodDuoc = () => !moi && AUTH.la('yard', 'acct', 'rev') && !biKhoa();
  function veVaiVaTrangThai() {
    COT_POD.forEach(c => { const el = g('f-' + c); if (el) el.disabled = !suaPodDuoc(); });
    veHopDong();
    g('px-goi-y').innerHTML = NN.h('hint_' + (vai() === 'treasury' ? 'treasury' : vai()));
    g('px-doc-no').disabled = !suaDuoc('info');
    g('px-trang-thai').innerHTML = moi ? '' : `${tag(P.transport_status)} ${tag(P.finance_status)}${P.invoiced ? ' ' + tag('paid', 'inv_done') : ''}${P.locked ? ` <span class="px-khoa" title="${esc(P.locked_by || '')}">🔒 ${NN.h('s_locked')}</span>` : ''}${P.owner_paid ? ' ' + tag('paid', 'owner_paid') : ''}`;
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
      e.className = 'px-stt ' + k; e.innerHTML = NN.h(k === 'wait' ? 'stt_wait2' : 'stt_' + k);
      const nut = []; const p = perm();
      if (!moi && !tuyChon) {
        if (st === 'wait' && (p.edit.includes(m) || vai() === 'admin')) nut.push(['ok', 'send', 'a_send']);
        if (st === 'entered' && (p.verify.includes(m) || vai() === 'admin')) { nut.push(['ok', 'verify', 'a_verify']); nut.push(['warn', 'return', 'a_return']); }
        if (st === 'verified' && MUC_CHI.includes(m) && (p.book.includes(m) || vai() === 'admin')) nut.push(['ok', 'book', 'a_book']);
        if (st === 'verified' && (p.verify.includes(m) || vai() === 'admin')) nut.push(['warn', 'return', 'a_return']);
        if (st === 'booked' && (p.pay.includes(m) || vai() === 'admin')) nut.push(['ok', 'pay', 'a_pay']);
        if (vai() === 'admin' && !['wait', 'entered'].includes(st)) nut.push(['', 'unlock', 'a_unlock']);
      }
      sec.querySelector('.px-act').innerHTML = nut.map(b => `<button type="button" class="btn sm ${b[0]}" data-muc-act="${m}" data-hd="${b[1]}">${NN.h(b[2])}</button>`).join('');
    });
    root.querySelectorAll('[data-muc-act]').forEach(b => b.addEventListener('click', () => duyet(b.dataset.mucAct, b.dataset.hd)));
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
      if (AUTH.la('acct') && P.locked && !P.invoiced) ta.push(`<button class="btn sm" data-hd-phieu="mo-khoa">${NN.h('a_unlock_slip')}</button>`);
      // Trả chủ xe ở TRANG KẾ TOÁN từ 28/09 (đợt 7b): nút mở màn Xe liên kết bên đó ở đúng tháng của phiếu
      if (AUTH.la('cash', 'treasury') && P.company === 'joint' && P.locked && !P.owner_paid && (P.tinh || {}).tra_chu_xe > 0) ta.push(`<button class="btn sm ok" data-kt-tra="">${NN.h('pay_owner')} · ${t2(P.tinh.tra_chu_xe, P.tinh.hire_ccy || maCuoc())} ↗</button>`);
      if (AUTH.la('yard') && !P.locked && P.transport_status === 'dispatched') ta.push(`<button class="btn sm" data-tt="transit">${NN.h('mark_transit')}</button>`);
      // Xe hỏng nặng giữa đường thì đổi xe NGAY TRÊN PHIẾU NÀY (C2.2) — không lập phiếu mới, vì hàng,
      // khách, tuyến và tiền đã chi vẫn là của chuyến này.
      if (AUTH.la('yard') && !P.locked && P.transport_status !== 'arrived') ta.push(`<button class="btn sm" data-hd-phieu="doi-xe">${NN.h('change_truck')}</button>`);
      if (AUTH.la('yard') && !P.locked && P.transport_status !== 'arrived') ta.push(`<button class="btn sm ok" data-tt="arrived">${NN.h('mark_arrived')}</button>`);
      // Hoá đơn và thu tiền ở TRANG KẾ TOÁN từ 28/09 (đợt 7a): các nút dưới mở màn bên đó, đúng phiếu này / đúng tờ gộp.
      // Khách gộp hoá đơn tháng (C8.2) thì KHÔNG xuất hoá đơn lẻ từng phiếu — sang màn Hoá đơn gộp.
      if (AUTH.la('rev') && s.trans === 'verified' && !P.invoiced && P.inv_mode !== 'thang') ta.push(`<button class="btn sm ok" data-kt-hd="">${NN.h('a_invoice')} ↗</button>`);
      if (AUTH.la('rev') && s.trans === 'verified' && !P.invoiced && P.inv_mode === 'thang') ta.push(`<button class="btn sm" data-di-gop="">${NN.h('hg_gop')} ↗</button>`);
      if (P.invoice_id) ta.push(`<button class="btn sm" data-di-gop="${esc(P.invoice_id)}">${NN.h('hg_thuoc')} ${esc(P.inv_no || '')} ↗</button>`);
      // Không còn nút "đánh dấu đã thu": tiền về bao nhiêu thì ghi bấy nhiêu (ở trang kế toán), trạng thái tự suy ra.
      if (AUTH.la('rev') && P.invoiced && !P.invoice_id && P.finance_status !== 'paid') ta.push(`<button class="btn sm ok" data-kt-hd="">${NN.h('collect_new')} ↗</button>`);
      if (AUTH.la('yard') && !P.locked && MUC.every(m => ['wait', 'entered'].includes(s[m] || 'wait'))) ta.push(`<button class="btn sm danger" data-hd-phieu="xoa">${NN.h('delete')}</button>`);
    }
    g('px-hanh-dong').innerHTML = ta.length ? `<span class="small muted">${NN.h('trip_status')}:</span> ${ta.join(' ')}` : `<span class="small muted">${NN.h('trip_status')}: ${moi ? NN.h('new_slip') : tag(P.transport_status) + ' ' + tag(P.finance_status)}</span>`;
    root.querySelectorAll('[data-tt]').forEach(b => b.addEventListener('click', () => doiTrangThai(b.dataset.tt)));
    root.querySelectorAll('[data-di-gop]').forEach(b => b.addEventListener('click', () => EPL.moKeToan('hoa-don-gop',
      Object.assign({ thang: String(P.doc_date || '').slice(0, 7) }, b.dataset.diGop ? { id: b.dataset.diGop } : {}))));
    root.querySelectorAll('[data-kt-hd]').forEach(b => b.addEventListener('click', () => EPL.moKeToan('hoa-don', { id: P.id })));
    root.querySelectorAll('[data-kt-tra]').forEach(b => b.addEventListener('click', () => EPL.moKeToan('xe-lien-ket', { thang: String(P.doc_date || '').slice(0, 7), id: P.id })));
    root.querySelectorAll('[data-hd-phieu]').forEach(b => b.addEventListener('click', () => b.dataset.hdPhieu === 'xoa' ? xoaPhieu() : b.dataset.hdPhieu === 'khoa' ? khoaPhieu() : b.dataset.hdPhieu === 'doi-xe' ? doiXe() : hanhDongPhieu(b.dataset.hdPhieu)));
    veThuTien();
    veTep();
    veBen();
    g('px-log').innerHTML = `<h5>${NN.h('log_title')}</h5><ul>${(P.logs || []).length ? P.logs.map(l => `<li><span class="ts">${EPL.ngayGio(l.ts)}</span><span><b lang="lo">${esc(l.user)}</b> <span class="muted">(${NN.h('r_' + l.role)})</span> · ${esc(nhanLog(l.action))}</span></li>`).join('') : `<li class="muted">${NN.h('log_empty')}</li>`}</ul>`;
  }
  function nhanLog(a) {
    if (!a) return ''; const m = a.match(/^sec_(\w+):(\w+)$/); if (m) return `${NN.t('sec' + (MUC.indexOf(m[1]) + 1))} → ${NN.t('a_' + m[2])}`;
    return NN.t(a);
  }
  /** Trạng thái mà vai này CÓ VIỆC ở một mục: nhập khi chờ/đã nhập, kiểm khi đã nhập, ghi sổ khi đã kiểm, chi khi đã ghi sổ. */
  function coViec(m, st) {
    if (moi) return m === 'info';
    const pq = perm();
    return (pq.edit.includes(m) && ['wait', 'entered'].includes(st)) || (pq.verify.includes(m) && st === 'entered')
      || (pq.book.includes(m) && st === 'verified') || (pq.pay.includes(m) && st === 'booked');
  }
  /** Tab mở sẵn theo vai: mục đầu tiên vai này có việc; không có việc thì mục đầu tiên vai này phụ trách;
   *  vai chỉ xem (doanh thu, Sếp, tài xế) thì Toàn phiếu. */
  function tabMacDinh() {
    if (moi) return 'info';
    const s = P.sections || {}, pq = perm();
    const cua = MUC.filter(m => pq.edit.includes(m) || pq.verify.includes(m) || pq.book.includes(m) || pq.pay.includes(m));
    if (!cua.length || vai() === 'admin') return 'all';
    return cua.find(m => coViec(m, s[m] || 'wait')) || cua[0];
  }
  function datTab(t, tay) {
    tab = t; if (tay) tabTay = true;
    const ph = q('#px-phieu'); ph.dataset.tab = tab;
    MUC.forEach(m => { const sec = q(`.px-muc[data-muc="${m}"]`); if (sec) sec.classList.toggle('px-muc-hien', tab === 'all' || tab === m); });
    root.querySelectorAll('#px-tabs .px-tab').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
    const luu = g('px-luu'); if (luu) luu.hidden = tab === 'all';
  }
  function veTabs() {
    const s = (P && P.sections) || {};
    q('#px-tabs').innerHTML = MUC.map((m, i) => {
      const st = moi ? 'wait' : (s[m] || 'wait');
      const tuyChon = (m === 'repair' || m === 'other') && !moi && !P.expenses.some(d => d.section === m);
      return `<button type="button" class="px-tab ${tab === m ? 'active' : ''} ${coViec(m, st) ? 'viec' : ''}" data-tab="${m}" title="${esc(NN.t(tuyChon ? 'na' : (st === 'wait' ? 'stt_wait2' : 'stt_' + st)))}">
        <b>${SO_LA_MA[i]}</b><span>${NN.h('sec' + (i + 1))}</span><i class="stt ${tuyChon ? 'na' : st}"></i>
        <em class="st-chu ${tuyChon ? 'na' : st}">${NN.h(tuyChon ? 'stt_na' : (st === 'wait' ? 'stt_wait2' : 'stt_' + st))}</em></button>`;
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
      veSo(); EPL.toast(NN.t('px_gia_tu_bang'), 'ok');
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
    const lp = g('lbl-price'); if (lp) lp.innerHTML = NN.h(khoan() ? 'price_trip' : 'price_usd');
    q('#px-phieu').classList.toggle('is-gom', laGom());
    q('#px-phieu').classList.toggle('is-giao', !laGom());
    veChon(); veDanhMuc(); doTruong(); veChi(); veHang(); veVaiVaTrangThai();
    // phiếu mới: hai thẻ lớn chọn Gom / Giao
    const cl = g('px-chon-loai'); cl.hidden = !moi;
    cl.querySelectorAll('button').forEach(b => b.classList.toggle('on', b.dataset.loai === (P.kind || 'giao')));
    if (!tabTay) tab = tabMacDinh();
    veTabs(); datTab(tab, false); NN.apDung(root); nhanCan();
  }
  /** Hai ô cân mang nghĩa khác nhau tuỳ loại DO, nên nhãn phải nói đúng chỗ cân — chạy SAU NN.apDung
   *  vì apDung ghi lại nhãn theo data-i18n. */
  function nhanCan() {
    const dat = (id, khoa) => { const el = q(`label[for="${id}"], #${id}`); const lb = el && el.closest('.field') && el.closest('.field').querySelector('label'); if (lb) lb.textContent = NN.t(khoa); };
    dat('f-weight_origin', laGom() ? 'w_origin_gom' : 'w_origin_giao');
    dat('f-weight_dest', laGom() ? 'w_dest_gom' : 'w_dest_giao');
  }

  /* ---------------------------------------------------------------- dữ liệu */
  function phieuTrong() {
    return { id: null, doc_no: '', kind: 'giao', goods: [], company: 'EPL', goods_type: 'iron_ore', doc_date: EPL.homNay(), out_date: EPL.homNay(), fee_pct: 2, over_limit_t: 40, over_price: 1, price_ccy: 'USD', price_mode: 'ton',
      rate_usd: ty_gia.USD || 22000, rate_thb: ty_gia.THB || 700, rate_vnd: ty_gia.VND || 1.2, rate_cny: ty_gia.CNY || 3000, transport_status: 'dispatched', finance_status: 'unpaid', invoiced: false,
      sections: {}, expenses: [], logs: [] };
  }
  async function moPhieu(id) { moi = false; tabTay = false; HD_DOI = {}; P = await API.get('/api/trips/' + id); await napLo(P.id); anPhieu(false); veHet(); }
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
  async function phieuMoi() { moi = true; tabTay = false; HD_DOI = {}; P = phieuTrong(); anNhacOdo(); await napLo();
    // công-tơ-mét của xe đổi mỗi lần một chuyến về tới (Xe đã tới) — nạp lại để ô Lúc đi điền đúng số mới nhất
    DM.vehicles = await API.get('/api/vehicles').catch(() => DM.vehicles); const s = await API.get('/api/trips-so-moi').catch(() => ({ doc_no: '' })); P.doc_no = s.doc_no; anPhieu(false); veHet(); }
  function anNhacOdo() { const o = g('f-odo_out'); if (o) delete o.dataset.tuDien; const n = g('px-odo-nhac'); if (n) n.hidden = true; }
  function docForm() {
    P.doc_no = g('px-doc-no').value.trim();
    [...COT_INFO, ...COT_TRANS, ...COT_POD].forEach(c => { const el = g('f-' + c); if (!el || el.disabled) return; P[c] = el.value === '' ? null : (SO.has(c) ? EPL.doc(el.value) : el.value); });
  }
  async function luu() {
    docForm();
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
    const guiMuc = (m) => suaDuoc(m) || (!moi && P.expenses.some(e => e.section === m && giaDuoc(m, e)));
    body.expenses = P.expenses.filter(e => guiMuc(e.section)).map(e => {
      const x = { ...e, qty: EPL.doc(e.qty), acct_code: e.acct_code || tkMacDinh(e.section, e) };
      if (thayChi()) x.unit_price = EPL.doc(e.unit_price); else { delete x.unit_price; delete x.currency; }
      return x;
    });
    try {
      P = moi ? await API.post('/api/trips', body) : await API.put('/api/trips/' + P.id, body);
      moi = false; HD_DOI = {}; DS = await napDs(); EPL.toast(NN.t('saved'), 'ok'); veHet();
      history.replaceState(null, '', '#/phieu-xuat-xe?id=' + P.id);
    } catch (e) { EPL.baoLoi(e); }
  }
  async function duyet(m, hd) {
    if (moi) return EPL.toast(NN.t('save') + '?', 'loi');
    if (hd === 'send' && suaDuoc(m)) { await luu(); if (moi) return; }
    // kế toán gõ đơn giá rồi bấm Kiểm: lưu giá trước, không thì máy chủ thấy dòng giá 0 và chặn
    if (hd === 'verify' && MUC_CHI.includes(m) && P.expenses.some(e => e.section === m && giaDuoc(m, e))) { await luu(); }
    if (hd === 'return' || hd === 'unlock') { if (!await EPL.hoi(NN.t('a_' + hd), NN.t('confirm_action'))) return; }
    try { P = await API.post(`/api/trips/${P.id}/sections/${m}/${hd}`); veHet(); } catch (e) { EPL.baoLoi(e); }
  }
  async function doiTrangThai(tt) {
    const body = { status: tt };
    if (tt === 'arrived') {
      // Ngày về và km về điền sẵn theo số TÀI XẾ đã báo (nút "Báo đã về" trên điện thoại) — Bãi chỉ thêm cân.
      // Phiếu gom: hàng vào kho theo cân tại mỏ — hỏi luôn ô đó (29/09); tài xế đã báo từ mỏ thì điền sẵn.
      const hoiMo = laGom() && gomMotDong();
      const v = await EPL.hopNhap(NN.t('mark_arrived'), [
        ...(hoiMo ? [{ id: 'weight_origin', label: 'w_origin_gom', type: 'number', value: P.weight_origin ?? '' }] : []),
        { id: 'weight_dest', label: laGom() ? 'w_dest_gom' : 'weight_dest_prompt', type: 'number', value: P.weight_dest ?? '' },
        { id: 'back_date', label: 'd_back', type: 'date', value: P.back_date || EPL.homNay() },
        { id: 'odo_back', label: 'odo_back_prompt', type: 'number', value: P.odo_back ?? '' },
        ...(laGom() ? [] : [{ id: 'pod_no', label: 'pod_no', value: P.pod_no || '' },
          { id: 'pod_receiver', label: 'pod_receiver', value: P.pod_receiver || '' }]),
      ], NN.t('ok'));
      if (!v) return;
      if (hoiMo) { if (!(EPL.doc(v.weight_origin) > 0)) return EPL.toast(NN.t('w_origin_gom') + '?', 'loi'); body.weight_origin = v.weight_origin; }
      body.weight_dest = v.weight_dest; body.back_date = v.back_date; if (v.odo_back !== '') body.odo_back = v.odo_back;
      if (v.pod_no) body.pod_no = v.pod_no; if (v.pod_receiver) body.pod_receiver = v.pod_receiver;
    }
    try { P = await API.post(`/api/trips/${P.id}/transport-status`, body); DS = await napDs(); veHet(); } catch (e) { EPL.baoLoi(e); }
  }
  async function hanhDongPhieu(hd, body) {
    if (!await EPL.hoi(NN.t(hd === 'invoice' ? 'a_invoice' : 'a_collect'), NN.t('confirm_action'))) return;
    try { P = await API.post(`/api/trips/${P.id}/${hd}`, body || {}); DS = await napDs(); veHet(); } catch (e) { EPL.baoLoi(e); }
  }

  /* ---------------------------------------------------------------- sổ thu tiền
   * Hoá đơn một tờ, tiền có thể về làm nhiều lần và bằng tiền khác với tiền ghi trên hoá đơn —
   * hoá đơn USD mà khách chuyển Kíp là chuyện bình thường ở đây. Mỗi lần thu là một dòng ở trang kế toán;
   * trạng thái "đã thu đủ" do tổng quyết định.
   */
  /** Sổ thu tiền ở TRANG KẾ TOÁN từ 28/09 (đợt 7a). Phiếu bên này chỉ còn bản chép: tiền hoá đơn, đã thu, còn lại —
   *  bấm nút để mở đúng phiếu này bên đó (ghi thu, xoá lần thu, in phiếu thu). */
  function veThuTien() {
    const o = g('px-thu-tien'); if (!o) return;
    if (moi || !P.id || !P.invoiced) { o.innerHTML = ''; return; }
    const k = P.tinh || {};
    o.innerHTML = `<div class="card px-thu"><div class="hd"><h4>${NN.h('collect_log')}</h4><div class="grow"></div>
        <span class="small">${NN.h('c_value')}: <b>${EPL.tien(k.doanh_thu, k.ccy)}</b> · ${NN.h('collected')}: <b>${EPL.tien(k.da_thu, k.ccy)}</b> · ${NN.h('remaining')}: <b class="${k.con_lai ? 'neg' : 'pos'}">${EPL.tien(k.con_lai, k.ccy)}</b></span>
        <button class="btn sm no-print" data-kt-thu="">${NN.h('mo_ke_toan')} ↗</button></div>
      <div class="bd"><p class="small muted">${P.invoice_id ? NN.h('hg_thu_o_to') + ' ' + esc(P.inv_no || '') + ' · ' : ''}${NN.h('thu_o_ke_toan')}</p></div></div>`;
    o.querySelectorAll('[data-kt-thu]').forEach(b => b.addEventListener('click', () => (P.invoice_id
      ? EPL.moKeToan('hoa-don-gop', { thang: String(P.doc_date || '').slice(0, 7), id: P.invoice_id }) : EPL.moKeToan('hoa-don', { id: P.id }))));
  }

  /** Đổi xe giữa đường (C2.2): chọn xe mới, ghi lý do. Máy chủ để lại dòng diễn biến và kéo mục I
   *  về "đã nhập" để kế toán kiểm lại — thông tin xe trên phiếu đã khác. */
  async function doiXe() {
    const con = (DM.vehicles || []).filter(x => x.active !== false && x.id !== P.vehicle_id);
    if (!con.length) return EPL.toast(NN.t('no_data'), 'loi');
    const v = await EPL.hopNhap(NN.t('change_truck'), [
      { id: 'vehicle_id', label: 'truck_no', type: 'select', value: con[0].id,
        options: con.map(x => [x.id, `${x.truck_no}${x.plate_head ? ' · ' + x.plate_head : ''}${x.status === 'on_trip' ? ' · ' + NN.t('v_on_trip') : ''}`]) },
      { id: 'driver_id', label: 'driver', type: 'select', value: '',
        options: [['', NN.t('ct_giu_tai_xe')]].concat((DM.drivers || []).filter(d => d.active !== false).map(d => [d.id, d.name])) },
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
      EPL.toast(NN.t('saved'), 'ok'); veHet();
    } catch (e) { EPL.baoLoi(e); }
  }

  /** Bước 14: kế toán rà lại rồi khoá. Máy chủ trả các điểm lệch; có lệch thì hiện ra cho kế toán đọc rồi mới xác nhận khoá. */
  async function khoaPhieu() {
    try {
      const k = await API.get(`/api/trips/${P.id}/kiem-lai`);
      const cb = k.canh_bao || [];
      const ok = await EPL.hoi(NN.t('a_lock'), cb.length
        ? `<p class="small muted">${NN.h('lock_warn')}</p><ul class="px-cb">${cb.map(x => `<li>${esc(x.loi)}</li>`).join('')}</ul>`
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
    try { await API.del('/api/trips/' + P.id); DS = await napDs(); EPL.toast(NN.t('saved'), 'ok');
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
        d.acct_code = tkMacDinh(m, d);
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
    d.acct_code = tkMacDinh(m, d);
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
      g('px-ve').addEventListener('click', () => EPL.di('theo-doi'));
      g('px-moi').addEventListener('click', () => phieuMoi().catch(EPL.baoLoi));
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
      // Phiếu chi tạm ứng: lập (hoặc cập nhật) tờ tạm ứng có mã QR rồi mở màn in — không có khoản tiền mặt nào thì
      // vẫn mở màn (màn tự ghi "không có khoản tạm ứng"). 29/09: trước đây không nút nào lập tờ QR cho phiếu mới.
      g('px-chung-tu').addEventListener('click', async () => {
        if (!P || !P.id) return;
        try { await API.post(`/api/trips/${P.id}/vouchers`, { kind: 'advance' }); }
        catch (e) { if (!(e instanceof EPL.LoiAPI) || e.status !== 422) return EPL.baoLoi(e); }
        EPL.di('de-nghi-chi', { id: P.id, loai: 'advance' });
      });
      g('px-phieu-linh').addEventListener('click', lapPhieuLinh);
      g('px-chon').addEventListener('change', e => { if (e.target.value) moPhieu(e.target.value).catch(EPL.baoLoi); });
      let hen = null;
      g('px-tim').addEventListener('input', () => { clearTimeout(hen); hen = setTimeout(() => napDs().then(() => {
        // chỉ nạp lại ô chọn — KHÔNG tự mở phiếu tìm được: người dùng có thể đang sửa dở phiếu khác
        if (P || moi) veChon(); else chuaChon();
      }).catch(EPL.baoLoi), 350); });
      root.querySelectorAll('.px-them').forEach(b => b.addEventListener('click', () => themDong(b.dataset.them)));
      g('px-hang-them').addEventListener('click', () => { (P.goods = P.goods || []).push({ loai: 'hang', goods_name: NN.t('iron_ore'), qty_t: 0, tu_phieu_id: '' }); veHang(); });
      // đầu vào mục I–II → cập nhật số ngay
      [...COT_INFO, ...COT_TRANS].forEach(c => { const el = g('f-' + c); if (!el) return; el.addEventListener('input', () => {
        P[c] = el.value === '' ? null : (SO.has(c) ? el.value : el.value);
        if (c === 'company') { P.expenses.forEach(e => { e.acct_code = tkMacDinh(e.section, e); }); if (P.company === 'joint' && (P.hire_price == null || P.hire_price === '')) { P.hire_price = P.price; g('f-hire_price').value = P.price ?? ''; P.hire_ccy = maCuoc(); g('f-hire_ccy').value = P.hire_ccy; } q('#px-phieu').classList.toggle('is-joint', P.company === 'joint'); veChi(); }
        if (c === 'route_id') { const r = DM.routes.find(x => x.id === el.value); if (r) { g('f-origin').value = P.origin = r.origin; g('f-destination').value = P.destination = r.destination; dienGoiY(r); } }
        if (c === 'route_id' || c === 'customer_id') dienGiaHopDong();
        if (c === 'kind') {
          // phiếu mới: số gợi ý theo loại — gom ra G4-…, giao ra T4-… (chỉ khi người lập chưa tự gõ số khác)
          if (moi) API.get('/api/trips-so-moi?kind=' + encodeURIComponent(P.kind || 'giao')).then(s => { if (s && s.doc_no) { P.doc_no = s.doc_no; const o = g('px-doc-no'); if (o) o.value = s.doc_no; } }).catch(() => {});
          napLo().then(veHet);
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
      const t = ctx.tham || {};
      // KHÔNG tự mở phiếu cũ khi vào màn không kèm tham số (lỗi anh chủ dự án bắt 22/09: Bãi vào là
      // thấy phiếu mới nhất đang mở sẵn, gõ là gõ đè lên phiếu đó). Bãi và Sếp — người lập phiếu — vào
      // là PHIẾU MỚI trắng; vai khác không lập phiếu thì để ô chọn trống kèm câu nhắc, tự chọn tờ cần xem.
      if (t.moi) await phieuMoi(); else if (t.id) await moPhieu(t.id); else if (AUTH.la('yard')) await phieuMoi(); else chuaChon();
      // Mở từ màn Xe (nút "Tạo phiếu xuất xe" ở hồ sơ một chiếc): chọn sẵn chiếc đó.
      if (t.moi && t.xe && DM.vehicles.some(v => v.id === t.xe)) {
        const el = g('f-vehicle_id'); if (el) { el.value = t.xe; el.dispatchEvent(new Event('input', { bubbles: true })); }
      }
      if (t.tab && (MUC.includes(t.tab) || t.tab === 'all')) datTab(t.tab, true);
    },
    onLang() { if (P) veHet(); else if (root) chuaChon(); },
  };
})();

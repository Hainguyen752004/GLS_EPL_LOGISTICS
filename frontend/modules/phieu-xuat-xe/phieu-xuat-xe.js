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
  const tienDong = (d) => (EPL.doc(d.qty)) * (EPL.doc(d.unit_price)) * rate(d.currency);
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
  function veChon() {
    g('px-chon').innerHTML = (moi ? `<option value="">— ${NN.t('new_slip')} —</option>` : '') + DS.map(p => `<option value="${p.id}" ${P && p.id === P.id ? 'selected' : ''}>${esc(p.doc_no)} · ${esc(p.truck_no || '')}${p.company === 'joint' ? ' · ' + NN.t('co_joint') : ''}</option>`).join('');
    if (moi) g('px-chon').value = '';
  }
  function veDanhMuc() {
    g('f-vehicle_id').innerHTML = `<option value="">—</option>` + DM.vehicles.filter(x => x.active || x.id === P.vehicle_id).map(x => `<option value="${x.id}" ${x.id === P.vehicle_id ? 'selected' : ''}>${esc(x.truck_no)} · ${esc(x.plate_head || '')}${x.owner_type === 'joint' ? ' · ' + NN.t('co_joint') : ''}</option>`).join('');
    g('f-driver_id').innerHTML = `<option value="">—</option>` + DM.drivers.filter(x => x.active || x.id === P.driver_id).map(x => `<option value="${x.id}" ${x.id === P.driver_id ? 'selected' : ''}>${esc(x.name)}</option>`).join('');
    g('f-route_id').innerHTML = `<option value="">—</option>` + DM.routes.filter(x => x.active || x.id === P.route_id).map(x => `<option value="${x.id}" ${x.id === P.route_id ? 'selected' : ''}>${esc(x.name)} · ${so(x.total_km, 1)} km</option>`).join('');
    g('f-customer_id').innerHTML = `<option value="">—</option>` + DM.customers.filter(x => x.active || x.id === P.customer_id).map(x => `<option value="${x.id}" ${x.id === P.customer_id ? 'selected' : ''}>${esc(x.name)}</option>`).join('');
  }
  function doTruong() {
    g('px-doc-no').value = P.doc_no || '';
    [...COT_INFO, ...COT_TRANS].forEach(c => { const el = g('f-' + c); if (!el) return; el.value = P[c] == null ? '' : P[c]; });
    q('#px-phieu').classList.toggle('is-joint', P.company === 'joint');
  }
  function veSo() {
    const k = tinh();
    g('v-odo_km').textContent = P.odo_out && P.odo_back ? so(Math.abs(EPL.doc(P.odo_back) - EPL.doc(P.odo_out))) : '—';
    // Km về ước tính = km lúc đi + km tuyến — để kế toán đối với km về thật ở bước kiểm lại
    const tuyen = (DM.routes || []).find(x => x.id === P.route_id);
    g('v-odo_est').textContent = P.odo_out && tuyen && tuyen.total_km ? so(EPL.doc(P.odo_out) + EPL.doc(tuyen.total_km)) : '—';
    g('v-hao').innerHTML = k.hao === null ? '—' : `${so(EPL.doc(P.weight_origin) - EPL.doc(P.weight_dest), 2)} t <span class="${k.hao > 1.5 ? 'neg' : 'muted'}">(${k.hao.toFixed(1)}%)</span>`;
    g('v-val-usd').textContent = t2(k.dt, k.ma); g('v-val-lak').textContent = k.ma === 'LAK' ? '—' : t2(k.dtLak, 'LAK');
    if (k.lk) { g('v-hire').textContent = t2(k.thue, k.mh); g('v-fee').textContent = '− ' + t2(k.phi, k.mh); g('v-over-t').textContent = so(k.vuot, 2) + ' t'; g('v-over').textContent = '− ' + t2(k.truVuot, k.mh); }
    // chỉ dòng có data-i — dòng "chưa có dữ liệu" không phải dòng chi
    MUC_CHI.forEach(m => { const tb = q(`table[data-bang="${m}"]`); tb.querySelectorAll('tbody tr[data-i]').forEach(tr => { const d = P.expenses[+tr.dataset.i]; if (d) tr.querySelector('.amt').textContent = so(tienDong(d)); });
      const lk = k.lk; const cols = m === 'fuel' ? 9 : (m === 'repair' ? 8 : 7);
      tb.querySelector('tfoot').innerHTML = `<tr><td></td><td>${NN.h('total')}</td>${m === 'fuel' ? `<td class="num">${so(P.expenses.filter(d => d.section === 'fuel').reduce((a, d) => a + EPL.doc(d.qty), 0))}</td><td></td><td></td>` : (m === 'repair' ? '<td></td><td></td><td></td>' : '<td></td><td></td>')}<td class="num px-gia"><b>${so(k.chi[m])}</b></td><td colspan="${cols - (m === 'fuel' ? 6 : 5)}"></td></tr>`; });
    const box = g('px-tong-ket');
    if (!k.lk) {
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
        const pay = `<td class="px-lk"><span class="px-pay"><button type="button" class="${d.paid_by_epl ? 'on' : ''}" data-i="${i}" data-pay="1" ${khoaDuoc ? '' : 'disabled'}>${esc(NN.t('pay_epl'))}</button><button type="button" class="${!d.paid_by_epl ? 'on' : ''}" data-i="${i}" data-pay="0" ${khoaDuoc ? '' : 'disabled'}>${esc(NN.t('pay_own'))}</button></span></td>`;
        const acct = `<td class="px-gia"><button type="button" class="acct px-acct" data-acct="${i}" ${AUTH.la('acct', 'fuel', 'rev') ? '' : 'disabled'} title="${esc(NN.t('acct_pair'))}">${esc(d.acct_code || tkMacDinh(m, d))}</button></td>`;
        const xoa = `<td class="no-print">${khoaDuoc ? `<button type="button" class="x" data-xoa="${i}" title="${esc(NN.t('delete'))}">×</button>` : ''}</td>`;
        if (m === 'fuel') {
          // Đổ dầu ở trạm ngoài (nhất là bên Việt Nam): tài xế trả tiền mặt, hay TRẠM GHI NỢ để cuối
          // tháng EPL trả / cấn trừ với khách (C5.1). Chỉ hỏi khi nơi đổ là trạm ngoài.
          const muaNgoai = nguonCuaDiem(d) !== 'kho';
          const noSel = !muaNgoai ? '' : `<label class="px-ghino small"><input type="checkbox" data-i="${i}" data-f="ghi_no" ${d.ghi_no ? 'checked' : ''} ${khoaDuoc ? '' : 'disabled'}> ${esc(NN.t('ncc_ghi_no'))}</label>`;
          return `<tr data-i="${i}" class="${lk && !d.paid_by_epl ? 'own' : ''}"><td>${n + 1}</td><td>${sel}</td><td>${inp('qty')}</td><td class="px-gia">${inp('unit_price')}</td>
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
        return `<tr data-i="${i}" class="${lk && !d.paid_by_epl ? 'own' : ''}"><td>${n + 1}</td><td>${sel}${theSel}</td>${nguon}<td>${inp('qty')}</td><td class="px-gia">${inp('unit_price')}</td><td class="num amt px-gia"></td>${pay}${acct}${xoa}</tr>`;
      }).join('') : `<tr><td colspan="10" class="empty small">${NN.h('no_data')}</td></tr>`;
    });
    q('#px-phieu').querySelectorAll('.px-chi [data-f]').forEach(el => el.addEventListener('input', e => {
      const d = P.expenses[+el.dataset.i], f = el.dataset.f; d[f] = el.value;
      if (f === 'item_key') { if (el.value === '') d.item_name = d.item_name || ''; else d.item_name = null; if (!['x_toll', 'x_bridge'].includes(el.value)) d.toll_card_id = null; veChi(); }
      if (f === 'toll_card_id') { d.toll_card_id = el.value || null; }
      if (f === 'ghi_no') { d.ghi_no = el.checked; }
      if (f === 'place_id') {
        // Nơi đổ quyết định LĨNH hay MUA, kéo theo định khoản …/371 hay …/402.
        d.source = nguonCuaDiem(d);
        if (P.company === 'joint') d.paid_by_epl = d.source === 'kho';
        d.acct_code = tkMacDinh('fuel', d); veChi();
      }
      if (f === 'source') { if (el.value !== 'kho') d.part_id = null; d.acct_code = tkMacDinh('repair', d); veChi(); }
      if (f === 'part_id') { const p = DM.parts.find(x => x.id === el.value); if (p) { d.item_key = null; d.item_name = p.name; if (thayChi()) d.unit_price = p.unit_price || 0; } veChi(); }
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
  function veVaiVaTrangThai() {
    g('px-goi-y').innerHTML = NN.h('hint_' + (vai() === 'treasury' ? 'treasury' : vai()));
    g('px-doc-no').disabled = !suaDuoc('info');
    g('px-trang-thai').innerHTML = moi ? '' : `${tag(P.transport_status)} ${tag(P.finance_status)}${P.invoiced ? ' ' + tag('paid', 'inv_done') : ''}${P.locked ? ` <span class="px-khoa" title="${esc(P.locked_by || '')}">🔒 ${NN.h('s_locked')}</span>` : ''}${P.owner_paid ? ' ' + tag('paid', 'owner_paid') : ''}`;
    MUC.forEach(m => {
      const sec = q(`.px-muc[data-muc="${m}"]`), st = moi ? 'wait' : (P.sections[m] || 'wait'), tuyChon = (m === 'repair' || m === 'other') && !P.expenses.some(d => d.section === m);
      const khoa = !suaDuoc(m); sec.classList.toggle('locked', khoa);
      const cot = m === 'info' ? COT_INFO : m === 'trans' ? COT_TRANS : [];
      cot.forEach(c => { const el = g('f-' + c); if (el) el.disabled = COT_KE_TOAN.includes(c) ? !suaKeToanDuoc(m) : ((khoa && !(COT_TIEN.includes(c) && suaTienDuoc(m))) || (daNhapKho() && (c === 'weight_origin' || c === 'weight_dest'))); });
      if (m === 'trans' && khoa && suaTienDuoc(m)) sec.classList.remove('locked');   // kế toán còn sửa được ô tiền thì mục chưa "khoá" với họ
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
      !moi && MUC_CHI.every(m => idx(m) >= 3 || !coChi(m)), !moi && MUC_CHI.every(m => idx(m) >= 4 || !coChi(m)), !moi && P.invoiced];
    let cur = done.findIndex(x => !x); root.querySelectorAll('#px-flow .step').forEach((el, i) => { el.classList.toggle('done', done[i]); el.classList.toggle('now', i === cur); });
    // hành động mức phiếu
    const ta = [];
    if (!moi) {
      if (AUTH.la('acct') && P.transport_status === 'arrived' && !P.locked) ta.push(`<button class="btn sm ok" data-hd-phieu="khoa">🔒 ${NN.h('a_lock')}</button>`);
      if (AUTH.la('acct') && P.locked && !P.invoiced) ta.push(`<button class="btn sm" data-hd-phieu="mo-khoa">${NN.h('a_unlock_slip')}</button>`);
      if (AUTH.la('cash', 'treasury') && P.company === 'joint' && P.locked && !P.owner_paid && (P.tinh || {}).tra_chu_xe > 0) ta.push(`<button class="btn sm ok" data-hd-phieu="tra-chu-xe">${NN.h('pay_owner')} · ${t2(P.tinh.tra_chu_xe, P.tinh.hire_ccy || maCuoc())}</button>`);
      if (AUTH.la('yard') && !P.locked && P.transport_status === 'dispatched') ta.push(`<button class="btn sm" data-tt="transit">${NN.h('mark_transit')}</button>`);
      // Xe hỏng nặng giữa đường thì đổi xe NGAY TRÊN PHIẾU NÀY (C2.2) — không lập phiếu mới, vì hàng,
      // khách, tuyến và tiền đã chi vẫn là của chuyến này.
      if (AUTH.la('yard') && !P.locked && P.transport_status !== 'arrived') ta.push(`<button class="btn sm" data-hd-phieu="doi-xe">${NN.h('change_truck')}</button>`);
      if (AUTH.la('yard') && !P.locked && P.transport_status !== 'arrived') ta.push(`<button class="btn sm ok" data-tt="arrived">${NN.h('mark_arrived')}</button>`);
      // Khách gộp hoá đơn tháng (C8.2) thì KHÔNG xuất hoá đơn lẻ từng phiếu — sang màn Hoá đơn gộp.
      if (AUTH.la('rev') && s.trans === 'verified' && !P.invoiced && P.inv_mode !== 'thang') ta.push(`<button class="btn sm ok" data-hd-phieu="invoice">${NN.h('a_invoice')}</button>`);
      if (AUTH.la('rev') && s.trans === 'verified' && !P.invoiced && P.inv_mode === 'thang') ta.push(`<button class="btn sm" data-di-gop="">${NN.h('hg_gop')}</button>`);
      if (P.invoice_id) ta.push(`<button class="btn sm" data-di-gop="${esc(P.invoice_id)}">${NN.h('hg_thuoc')} ${esc(P.inv_no || '')}</button>`);
      // Không còn nút "đánh dấu đã thu": tiền về bao nhiêu thì ghi bấy nhiêu, trạng thái tự suy ra.
      if (AUTH.la('rev') && P.invoiced && !P.invoice_id && P.finance_status !== 'paid') ta.push(`<button class="btn sm ok" data-hd-phieu="thu-tien">${NN.h('collect_new')}</button>`);
      if (AUTH.la('yard') && !P.locked && MUC.every(m => ['wait', 'entered'].includes(s[m] || 'wait'))) ta.push(`<button class="btn sm danger" data-hd-phieu="xoa">${NN.h('delete')}</button>`);
    }
    g('px-hanh-dong').innerHTML = ta.length ? `<span class="small muted">${NN.h('trip_status')}:</span> ${ta.join(' ')}` : `<span class="small muted">${NN.h('trip_status')}: ${moi ? NN.h('new_slip') : tag(P.transport_status) + ' ' + tag(P.finance_status)}</span>`;
    root.querySelectorAll('[data-tt]').forEach(b => b.addEventListener('click', () => doiTrangThai(b.dataset.tt)));
    root.querySelectorAll('[data-di-gop]').forEach(b => b.addEventListener('click', () => EPL.di('hoa-don-gop',
      Object.assign({ thang: String(P.doc_date || '').slice(0, 7) }, b.dataset.diGop ? { id: b.dataset.diGop } : {}))));
    root.querySelectorAll('[data-hd-phieu]').forEach(b => b.addEventListener('click', () => b.dataset.hdPhieu === 'xoa' ? xoaPhieu() : b.dataset.hdPhieu === 'khoa' ? khoaPhieu() : b.dataset.hdPhieu === 'tra-chu-xe' ? traChuXe() : b.dataset.hdPhieu === 'thu-tien' ? ghiThuTien() : b.dataset.hdPhieu === 'doi-xe' ? doiXe() : hanhDongPhieu(b.dataset.hdPhieu)));
    veThuTien();
    veTep();
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
        <b>${SO_LA_MA[i]}</b><span>${NN.h('sec' + (i + 1))}</span><i class="stt ${tuyChon ? 'na' : st}"></i></button>`;
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

  function veHet() {
    q('#px-phieu').classList.toggle('px-an-tien', vai() === 'yard');
    const lp = g('lbl-price'); if (lp) lp.innerHTML = NN.h(khoan() ? 'price_trip' : 'price_usd');
    q('#px-phieu').classList.toggle('is-gom', laGom());
    q('#px-phieu').classList.toggle('is-giao', !laGom());
    veChon(); veDanhMuc(); doTruong(); veChi(); veHang(); veVaiVaTrangThai();
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
  async function moPhieu(id) { moi = false; tabTay = false; P = await API.get('/api/trips/' + id); await napLo(P.id); anPhieu(false); veHet(); }
  /** Chưa chọn tờ nào: giấu thân phiếu và dải bước, hiện câu nhắc; ô chọn có dòng trống đứng đầu. */
  function chuaChon() {
    P = null; moi = false;
    g('px-chon').innerHTML = `<option value="" selected>— ${NN.t('px_chon_phieu')} —</option>` + DS.map(p => `<option value="${p.id}">${esc(p.doc_no)} · ${esc(p.truck_no || '')}${p.company === 'joint' ? ' · ' + NN.t('co_joint') : ''}</option>`).join('');
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
  async function phieuMoi() { moi = true; tabTay = false; P = phieuTrong(); await napLo(); const s = await API.get('/api/trips-so-moi').catch(() => ({ doc_no: '' })); P.doc_no = s.doc_no; anPhieu(false); veHet(); }
  function docForm() {
    P.doc_no = g('px-doc-no').value.trim();
    [...COT_INFO, ...COT_TRANS].forEach(c => { const el = g('f-' + c); if (!el || el.disabled) return; P[c] = el.value === '' ? null : (SO.has(c) ? EPL.doc(el.value) : el.value); });
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
    [...COT_INFO, ...COT_TRANS].forEach(c => { const el = g('f-' + c); if (P[c] !== undefined && (!el || !el.disabled)) body[c] = P[c]; });
    // chỉ gửi dòng chi của mục còn sửa được — mục khoá gửi lên là máy chủ từ chối cả phiếu
    if (suaDuoc('trans')) body.goods = (P.goods || []).filter(g => g.loai !== 'hao_hut')
      .map(g => ({ loai: 'hang', goods_name: g.goods_name, qty_t: EPL.doc(g.qty_t), tu_phieu_id: g.tu_phieu_id || null, note: g.note || null }));
    const guiMuc = (m) => suaDuoc(m) || (!moi && P.expenses.some(e => e.section === m && giaDuoc(m, e)));
    body.expenses = P.expenses.filter(e => guiMuc(e.section)).map(e => {
      const x = { ...e, qty: EPL.doc(e.qty), acct_code: e.acct_code || tkMacDinh(e.section, e) };
      if (thayChi()) x.unit_price = EPL.doc(e.unit_price); else { delete x.unit_price; delete x.currency; }
      return x;
    });
    try {
      P = moi ? await API.post('/api/trips', body) : await API.put('/api/trips/' + P.id, body);
      moi = false; DS = await API.get('/api/trips'); EPL.toast(NN.t('saved'), 'ok'); veHet();
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
      const v = await EPL.hopNhap(NN.t('mark_arrived'), [
        { id: 'weight_dest', label: 'weight_dest_prompt', type: 'number', value: P.weight_dest ?? '' },
        { id: 'back_date', label: 'd_back', type: 'date', value: P.back_date || EPL.homNay() },
        { id: 'odo_back', label: 'odo_back_prompt', type: 'number', value: P.odo_back ?? '' },
      ], NN.t('ok'));
      if (!v) return; body.weight_dest = v.weight_dest; body.back_date = v.back_date; if (v.odo_back !== '') body.odo_back = v.odo_back;
    }
    try { P = await API.post(`/api/trips/${P.id}/transport-status`, body); DS = await API.get('/api/trips'); veHet(); } catch (e) { EPL.baoLoi(e); }
  }
  async function hanhDongPhieu(hd, body) {
    if (!await EPL.hoi(NN.t(hd === 'invoice' ? 'a_invoice' : 'a_collect'), NN.t('confirm_action'))) return;
    try { P = await API.post(`/api/trips/${P.id}/${hd}`, body || {}); DS = await API.get('/api/trips'); veHet(); } catch (e) { EPL.baoLoi(e); }
  }

  /* ---------------------------------------------------------------- sổ thu tiền
   * Hoá đơn một tờ, tiền có thể về làm nhiều lần và bằng tiền khác với tiền ghi trên hoá đơn —
   * hoá đơn USD mà khách chuyển Kíp là chuyện bình thường ở đây. Nên mỗi lần thu là một dòng có
   * ngày, số tiền, tiền tệ và tỷ giá của chính ngày đó; trạng thái "đã thu đủ" do tổng quyết định.
   */
  const PT_CACH = [['bank', 'pm_bank'], ['cash', 'pm_cash'], ['offset', 'pm_offset'], ['other', 'pm_other']];

  function veThuTien() {
    const o = g('px-thu-tien'); if (!o) return;
    if (moi || !P.id || !P.invoiced) { o.innerHTML = ''; return; }
    const k = P.tinh || {}, ds = P.thu_tien || [];
    const dong = ds.map(x => `<tr>
      <td class="nowrap">${EPL.ngay(x.pay_date)}</td>
      <td class="num"><b>${EPL.tien(x.amount, x.currency)}</b></td>
      <td class="num">${x.currency === 'LAK' ? '—' : so(x.rate_to_lak, x.currency === 'VND' ? 2 : 0)}</td>
      <td class="num">${so(x.amount_lak)}</td>
      <td>${NN.h(PT_CACH.find(c => c[0] === x.method) ? PT_CACH.find(c => c[0] === x.method)[1] : 'pm_other')}</td>
      <td class="mono small">${esc(x.ref || '')}</td>
      <td class="small muted">${esc(x.by_user || '')}</td>
      <td class="no-print">${AUTH.la('rev') && !x.invoice_payment_id ? `<button class="btn xs danger" data-xoa-thu="${x.id}" title="${esc(NN.t('pay_del'))}">×</button>` : ''}</td></tr>`).join('');
    o.innerHTML = `<div class="card px-thu"><div class="hd"><h4>${NN.h('collect_log')}</h4><div class="grow"></div>
        <span class="small">${NN.h('c_value')}: <b>${EPL.tien(k.doanh_thu, k.ccy)}</b> · ${NN.h('collected')}: <b>${EPL.tien(k.da_thu, k.ccy)}</b> · ${NN.h('remaining')}: <b class="${k.con_lai ? 'neg' : 'pos'}">${EPL.tien(k.con_lai, k.ccy)}</b></span>
        ${AUTH.la('rev') && k.con_lai > 0 && !P.invoice_id ? `<button class="btn sm ok no-print" data-hd-phieu="thu-tien">${NN.h('collect_new')}</button>` : ''}</div>
      <div class="bd">${ds.length ? `<table class="tbl tbl-compact"><thead><tr>
          <th>${NN.h('pay_date')}</th><th class="num">${NN.h('pay_amount')}</th><th class="num">${NN.h('rate_day')}</th>
          <th class="num">${NN.h('in_lak')}</th><th>${NN.h('pay_method')}</th><th>${NN.h('pay_ref')}</th><th>${NN.h('by_user')}</th><th class="no-print"></th>
        </tr></thead><tbody>${dong}</tbody></table>` : `<p class="small muted">${NN.h('pay_none')}</p>`}
        <p class="small muted">${P.invoice_id ? NN.h('hg_thu_o_to') + ' ' + esc(P.inv_no || '') : NN.h('fin_auto')}</p></div></div>`;
    o.querySelectorAll('[data-hd-phieu="thu-tien"]').forEach(b => b.addEventListener('click', ghiThuTien));
    o.querySelectorAll('[data-xoa-thu]').forEach(b => b.addEventListener('click', () => xoaThuTien(b.dataset.xoaThu)));
  }

  async function ghiThuTien() {
    const k = P.tinh || {}, ma = k.ccy || 'USD';
    const v = await EPL.hopNhap(NN.t('collect_new'), [
      { id: 'pay_date', label: 'pay_date', type: 'date', value: EPL.homNay() },
      { id: 'currency', label: 'ccy', type: 'select', value: ma, options: EPL.TIEN_TE.map(m => [m, m]) },
      { id: 'amount', label: 'pay_amount', type: 'number', value: k.con_lai },
      // Trống = máy dùng tỷ giá khoá trên phiếu (C5.8). Nói ra con số đó để người ghi biết đang quy theo tỷ giá nào.
      { id: 'rate_to_lak', label: 'rate_day', type: 'number', value: '', placeholder: ma === 'LAK' ? '' : `${NN.t('rate_on_slip')}: 1 ${ma} = ${so(rate(ma), 0)}` },
      { id: 'method', label: 'pay_method', type: 'select', value: 'bank', options: PT_CACH.map(([x, t]) => [x, NN.t(t)]) },
      { id: 'ref', label: 'pay_ref', value: '' },
      { id: 'note', label: 'note', value: '' },
    ], NN.t('save'));
    if (!v) return;
    const than = { pay_date: v.pay_date, amount: v.amount, currency: v.currency, method: v.method, ref: v.ref, note: v.note };
    if (v.rate_to_lak !== '' && v.rate_to_lak != null) than.rate_to_lak = v.rate_to_lak;
    try {
      P = await API.post(`/api/trips/${P.id}/thu-tien`, than);
    } catch (e) {
      // Thu nhiều hơn phần còn lại: hỏi lại rồi mới ghi, không âm thầm chặn cũng không âm thầm nhận.
      if (!/THU_QUA_HOA_DON/.test(e.ma || '') && !/THU_QUA_HOA_DON/.test(String(e.message))) return EPL.baoLoi(e);
      if (!await EPL.hoi(NN.t('pay_over'), `<p>${esc(e.message)}</p>`, NN.t('pay_over_ok'))) return;
      than.cho_thu_du = true;
      try { P = await API.post(`/api/trips/${P.id}/thu-tien`, than); } catch (e2) { return EPL.baoLoi(e2); }
    }
    DS = await API.get('/api/trips'); EPL.toast(NN.t('saved'), 'ok'); veHet();
  }

  async function xoaThuTien(id) {
    if (!await EPL.hoi(NN.t('pay_del'), `<p>${NN.h('confirm_delete')}</p>`, NN.t('delete'))) return;
    try { P = await API.goi('/api/thu-tien/' + id, { method: 'DELETE' }); DS = await API.get('/api/trips'); veHet(); } catch (e) { EPL.baoLoi(e); }
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
      DS = await API.get('/api/trips'); DM.vehicles = await API.get('/api/vehicles');
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
      P = await API.post(`/api/trips/${P.id}/khoa`, { xac_nhan: true }); DS = await API.get('/api/trips'); EPL.toast(NN.t('saved'), 'ok'); veHet();
    } catch (e) { EPL.baoLoi(e); }
  }
  async function traChuXe() {
    const k = P.tinh || {}, mh = k.hire_ccy || maCuoc();
    const ok = await EPL.hoi(NN.t('pay_owner'), `<p><b lang="lo">${esc(P.owner_name || '')}</b> · <span class="mono">${esc(P.doc_no)}</span></p>
      <p class="hi">${t2(k.tra_chu_xe, mh)}${mh === 'LAK' ? '' : ` <small class="muted">≈ ${so(k.tra_chu_xe_lak)} LAK</small>`}</p>
      <p class="small muted">${t2(k.tien_thue, mh)} − ${so(k.phi, EPL.leTien(mh))} − ${so(k.tru_vuot, EPL.leTien(mh))} − ${so(k.ung_truoc, EPL.leTien(mh))}</p>`, NN.t('pay_owner'));
    if (!ok) return;
    try { P = await API.post(`/api/trips/${P.id}/tra-chu-xe`, {}); EPL.toast(NN.t('saved'), 'ok'); veHet(); } catch (e) { EPL.baoLoi(e); }
  }
  /* ---- tệp đính kèm: phiếu quặng của khách. Bãi chụp đưa lên lúc bốc; kế toán xem khi kiểm mục II. ---- */
  let TEP = [];
  async function veTep() {
    const o = g('px-tep'); if (!o) return;
    if (moi || !P.id) { o.innerHTML = `<span class="small muted">${NN.h('attach_after_save')}</span>`; return; }
    try { TEP = await API.get(`/api/trips/${P.id}/tep`); } catch (e) { TEP = []; }
    const tk = API.token();
    const themDuoc = AUTH.la('yard', 'acct', 'rev') && !biKhoa();
    o.innerHTML = TEP.map(t => `<div class="tep">
        ${t.la_anh ? `<img src="${esc(t.url)}?tk=${encodeURIComponent(tk)}" alt="">` : `<span class="pdf">PDF</span>`}
        <div><a href="${esc(t.url)}?tk=${encodeURIComponent(tk)}" target="_blank" rel="noopener" title="${esc(t.filename)}">${esc(t.filename)}</a>
          <small lang="lo">${esc(t.by_user || '')} · ${EPL.ngayGio ? EPL.ngayGio(t.ts) : EPL.ngay(t.ts)}</small></div>
        ${(AUTH.la('acct') || t.by_user === AUTH.user?.full_name) && !biKhoa() ? `<button type="button" class="x" data-xoa-tep="${t.id}" title="${esc(NN.t('delete'))}">×</button>` : ''}
      </div>`).join('') + (themDuoc ? `<label class="btn sm quiet them">+ ${NN.h('attach_add')}<input type="file" accept="image/*,application/pdf" data-them-tep></label>` : '')
      + (!TEP.length && !themDuoc ? `<span class="small muted">${NN.h('attach_none')}</span>` : '');
    o.querySelectorAll('[data-them-tep]').forEach(inp => inp.addEventListener('change', async () => {
      const f = inp.files && inp.files[0]; if (!f) return;
      const fd = new FormData(); fd.append('tep', f, f.name); fd.append('kind', 'ore_bill');
      try { await API.tep(`/api/trips/${P.id}/tep`, fd); EPL.toast(NN.t('saved'), 'ok'); await veTep(); } catch (e) { EPL.baoLoi(e); }
    }));
    o.querySelectorAll('[data-xoa-tep]').forEach(b => b.addEventListener('click', async () => {
      const ok = await EPL.hoi(NN.t('delete'), `<p>${NN.h('attach_del')}</p>`, NN.t('delete')); if (!ok) return;
      try { await API.goi('/api/tep/' + b.dataset.xoaTep, { method: 'DELETE' }); await veTep(); } catch (e) { EPL.baoLoi(e); }
    }));
  }
  async function xoaPhieu() {
    if (!await EPL.hoi(NN.t('delete') + ' ' + P.doc_no, NN.t('confirm_delete'), NN.t('delete'))) return;
    try { await API.del('/api/trips/' + P.id); DS = await API.get('/api/trips'); EPL.toast(NN.t('saved'), 'ok');
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
      EPL.di('chung-tu', { id: P.id, tab: 'linh', v: v[0] ? v[0].id : '' });
    } catch (e) { EPL.baoLoi(e); }
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
        API.get('/api/khoan-muc'), API.get('/api/trips'), API.get('/api/rates'), API.get('/api/customers'),
        API.get('/api/vehicles'), API.get('/api/drivers'), API.get('/api/routes'), API.get('/api/parts'),
        API.get('/api/fuel-places'), API.get('/api/the-cao-toc')]);
      g('px-ve').addEventListener('click', () => EPL.di('theo-doi'));
      g('px-moi').addEventListener('click', () => phieuMoi().catch(EPL.baoLoi));
      g('px-luu').addEventListener('click', luu);
      g('px-hoa-don').addEventListener('click', () => P && P.id && EPL.di('hoa-don', { id: P.id }));
      g('px-chung-tu').addEventListener('click', () => P && P.id && EPL.di('chung-tu', { id: P.id }));
      g('px-phieu-linh').addEventListener('click', lapPhieuLinh);
      g('px-chon').addEventListener('change', e => { if (e.target.value) moPhieu(e.target.value).catch(EPL.baoLoi); });
      root.querySelectorAll('.px-them').forEach(b => b.addEventListener('click', () => themDong(b.dataset.them)));
      g('px-hang-them').addEventListener('click', () => { (P.goods = P.goods || []).push({ loai: 'hang', goods_name: NN.t('iron_ore'), qty_t: 0, tu_phieu_id: '' }); veHang(); });
      // đầu vào mục I–II → cập nhật số ngay
      [...COT_INFO, ...COT_TRANS].forEach(c => { const el = g('f-' + c); if (!el) return; el.addEventListener('input', () => {
        P[c] = el.value === '' ? null : (SO.has(c) ? el.value : el.value);
        if (c === 'company') { P.expenses.forEach(e => { e.acct_code = tkMacDinh(e.section, e); }); if (P.company === 'joint' && (P.hire_price == null || P.hire_price === '')) { P.hire_price = P.price; g('f-hire_price').value = P.price ?? ''; P.hire_ccy = maCuoc(); g('f-hire_ccy').value = P.hire_ccy; } q('#px-phieu').classList.toggle('is-joint', P.company === 'joint'); veChi(); }
        if (c === 'route_id') { const r = DM.routes.find(x => x.id === el.value); if (r) { g('f-origin').value = P.origin = r.origin; g('f-destination').value = P.destination = r.destination; } }
        if (c === 'route_id' || c === 'customer_id') dienGiaHopDong();
        if (c === 'kind') {
          // phiếu mới: số gợi ý theo loại — gom ra G4-…, giao ra T4-… (chỉ khi người lập chưa tự gõ số khác)
          if (moi) API.get('/api/trips-so-moi?kind=' + encodeURIComponent(P.kind || 'giao')).then(s => { if (s && s.doc_no) { P.doc_no = s.doc_no; const o = g('px-doc-no'); if (o) o.value = s.doc_no; } }).catch(() => {});
          napLo().then(veHet);
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

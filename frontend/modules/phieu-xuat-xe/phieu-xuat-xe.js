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
  const COT_INFO = ['company', 'owner_name', 'vehicle_id', 'brand_model', 'plate_head', 'plate_trailer', 'driver_id', 'doc_date', 'out_date', 'back_date', 'odo_out', 'odo_back'];
  const COT_TRANS = ['customer_id', 'route_id', 'goods_type', 'ore_bill_no', 'ore_bill_date', 'origin', 'destination', 'weight_origin', 'weight_dest', 'price_usd', 'hire_price_usd', 'fee_pct', 'over_limit_t', 'over_price_usd'];
  const SO = new Set(['odo_out', 'odo_back', 'weight_origin', 'weight_dest', 'price_usd', 'hire_price_usd', 'fee_pct', 'over_limit_t', 'over_price_usd']);
  const QUYEN = {   // chép từ services/phan_quyen.py — chỉ để ẩn/hiện nút
    yard: { edit: MUC, verify: [], book: [], pay: [] },
    acct: { edit: [], verify: ['info', 'trans', 'travel', 'repair', 'other'], book: ['travel', 'repair', 'other'], pay: [] },
    fuel: { edit: [], verify: ['fuel'], book: ['fuel'], pay: [] },
    treasury: { edit: [], verify: [], book: [], pay: ['fuel'] },
    cash: { edit: [], verify: [], book: [], pay: ['travel', 'repair', 'other'] },
    rev: { edit: [], verify: [], book: [], pay: [] },
    admin: { edit: MUC, verify: MUC, book: MUC, pay: MUC },
  };
  let root, P = null, DS = [], KM = null, DM = { customers: [], vehicles: [], drivers: [], routes: [], parts: [], places: [] }, moi = false, ty_gia = {};
  /** Định khoản mặc định — chép luật máy chủ: xe nhà 625/614, xe liên kết 4022; kho …/371, mua ngoài …/402. */
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
  function rate(ma) { return { USD: P.rate_usd || 22000, THB: P.rate_thb || 700, VND: P.rate_vnd || 1.2, LAK: 1 }[(ma || 'LAK').toUpperCase()] || 1; }
  const tienDong = (d) => (EPL.doc(d.qty)) * (EPL.doc(d.unit_price)) * rate(d.currency);
  function tongMuc(m, chiUng = true) { return (P.expenses || []).filter(d => d.section === m && !(P.company === 'joint' && chiUng && !d.paid_by_epl)).reduce((a, d) => a + tienDong(d), 0); }
  function tinh() {
    const w = P.weight_dest != null && P.weight_dest !== '' ? EPL.doc(P.weight_dest) : EPL.doc(P.weight_origin);
    const gia = EPL.doc(P.price_usd), dt = +(w * gia).toFixed(2), rU = rate('USD');
    const chi = {}; MUC_CHI.forEach(m => { chi[m] = Math.round(tongMuc(m)); }); const tongChi = Object.values(chi).reduce((a, b) => a + b, 0);
    const hao = P.weight_origin && P.weight_dest != null && P.weight_dest !== '' ? (EPL.doc(P.weight_origin) - EPL.doc(P.weight_dest)) / EPL.doc(P.weight_origin) * 100 : null;
    const k = { w, dt, chi, tongChi, hao, lk: P.company === 'joint', rU };
    if (!k.lk) { k.lai = +(dt - tongChi / rU).toFixed(2); return k; }
    const gt = P.hire_price_usd != null && P.hire_price_usd !== '' ? EPL.doc(P.hire_price_usd) : gia;
    k.thue = +(w * gt).toFixed(2); k.phi = +(k.thue * EPL.doc(P.fee_pct ?? 2) / 100).toFixed(2);
    k.vuot = Math.max(0, w - EPL.doc(P.over_limit_t ?? 40)); k.truVuot = +(k.vuot * EPL.doc(P.over_price_usd ?? 1)).toFixed(2);
    k.ung = +(tongChi / rU).toFixed(2); k.traChu = +(k.thue - k.phi - k.truVuot - k.ung).toFixed(2); k.lai = +(dt - k.thue).toFixed(2); k.gt = gt;
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
    g('v-hao').innerHTML = k.hao === null ? '—' : `${so(EPL.doc(P.weight_origin) - EPL.doc(P.weight_dest), 2)} t <span class="${k.hao > 1.5 ? 'neg' : 'muted'}">(${k.hao.toFixed(1)}%)</span>`;
    g('v-val-usd').textContent = so(k.dt, 2) + ' USD'; g('v-val-lak').textContent = so(k.dt * k.rU) + ' LAK';
    if (k.lk) { g('v-hire').textContent = so(k.thue, 2) + ' USD'; g('v-fee').textContent = '− ' + so(k.phi, 2) + ' USD'; g('v-over-t').textContent = so(k.vuot, 2) + ' t'; g('v-over').textContent = '− ' + so(k.truVuot, 2) + ' USD'; }
    // chỉ dòng có data-i — dòng "chưa có dữ liệu" không phải dòng chi
    MUC_CHI.forEach(m => { const tb = q(`table[data-bang="${m}"]`); tb.querySelectorAll('tbody tr[data-i]').forEach(tr => { const d = P.expenses[+tr.dataset.i]; if (d) tr.querySelector('.amt').textContent = so(tienDong(d)); });
      const lk = k.lk; const cols = m === 'fuel' ? 9 : (m === 'repair' ? 8 : 7);
      tb.querySelector('tfoot').innerHTML = `<tr><td></td><td>${NN.h('total')}</td>${m === 'fuel' ? `<td class="num">${so(P.expenses.filter(d => d.section === 'fuel').reduce((a, d) => a + EPL.doc(d.qty), 0))}</td><td></td><td></td>` : (m === 'repair' ? '<td></td><td></td><td></td>' : '<td></td><td></td>')}<td class="num"><b>${so(k.chi[m])}</b></td><td colspan="${cols - (m === 'fuel' ? 6 : 5)}"></td></tr>`; });
    const box = g('px-tong-ket');
    if (!k.lk) {
      const net = k.dt * k.rU - k.tongChi;
      box.innerHTML = `<div class="px-tong"><div class="o"><div class="l">${NN.h('sum_rev')}</div><div class="v">${so(k.dt * k.rU)}<small>LAK · ${so(k.dt, 2)} USD</small></div></div>
        <div class="o"><div class="l">${NN.h('sum_exp')}</div><div class="v">${so(k.tongChi)}<small>LAK · ${so(k.tongChi / k.rU, 2)} USD</small></div></div>
        <div class="o net"><div class="l">${NN.h('sum_net')}</div><div class="v">${net < 0 ? '−' : ''}${so(Math.abs(net))}<small>LAK · ${net < 0 ? '−' : ''}${so(Math.abs(net) / k.rU, 2)} USD</small></div></div></div>`;
    } else {
      const r = (l, d, v, cls = '') => `<div class="r ${cls}"><span>${l}${d ? `<small>${d}</small>` : ''}</span><span>${v}</span></div>`;
      box.innerHTML = `<div class="px-tt"><div class="o"><b>${NN.h('settle_title')}</b>
        ${r(NN.h('st_hire'), `${so(k.gt, 2)} $/t × ${so(k.w, 2)} t`, so(k.thue, 2) + ' USD')}
        ${r(NN.h('st_fee'), `${EPL.doc(P.fee_pct ?? 2)}% × ${so(k.thue, 2)}`, '− ' + so(k.phi, 2) + ' USD', 'neg')}
        ${r(NN.h('st_over'), `${so(k.vuot, 2)} t × ${EPL.doc(P.over_price_usd ?? 1)} $`, '− ' + so(k.truVuot, 2) + ' USD', 'neg')}
        ${r(NN.h('st_adv'), `${so(k.tongChi)} LAK ÷ ${so(k.rU)}`, '− ' + so(k.ung, 2) + ' USD', 'neg')}
        ${r(NN.h('st_net_owner'), `≈ ${so(k.traChu * k.rU)} LAK`, so(k.traChu, 2) + ' USD', 'tot')}</div>
        <div class="o"><b>${NN.h('trip_profit')}</b>
        ${r(NN.h('do_money'), `${so(EPL.doc(P.price_usd), 2)} $/t × ${so(k.w, 2)} t`, so(k.dt, 2) + ' USD')}
        ${r(NN.h('st_hire'), '', '− ' + so(k.thue, 2) + ' USD', 'neg')}
        ${r(NN.h('trip_profit'), `≈ ${so(k.lai * k.rU)} LAK · ${k.dt ? so(k.lai / k.dt * 100, 1) : 0}%`, so(k.lai, 2) + ' USD', 'tot')}</div></div>
        <p class="small muted">${NN.h('settle_ex')}</p>`;
    }
  }
  function veChi() {
    const lk = P.company === 'joint', tk = KM.acct_codes;
    MUC_CHI.forEach(m => {
      const tb = q(`table[data-bang="${m}"] tbody`), khoa = KM.items[m], khoaDuoc = suaDuoc(m);
      const dong = P.expenses.map((d, i) => ({ d, i })).filter(x => x.d.section === m);
      tb.innerHTML = dong.length ? dong.map(({ d, i }, n) => {
        const tuGo = !khoa.includes(d.item_key);
        const sel = `<select data-i="${i}" data-f="item_key" ${khoaDuoc ? '' : 'disabled'}>${khoa.map(k => `<option value="${k}" ${k === d.item_key ? 'selected' : ''}>${esc(NN.t(k))}</option>`).join('')}<option value="" ${tuGo ? 'selected' : ''}>${esc(NN.t('x_custom'))}</option></select>${tuGo ? `<input data-i="${i}" data-f="item_name" value="${esc(d.item_name || '')}" placeholder="…" ${khoaDuoc ? '' : 'disabled'} style="margin-top:4px">` : ''}`;
        const inp = (f, cls = 'num') => `<input class="${cls}" data-i="${i}" data-f="${f}" value="${esc(d[f] == null ? '' : d[f])}" ${khoaDuoc ? '' : 'disabled'} inputmode="decimal">`;
        const pay = `<td class="px-lk"><span class="px-pay"><button type="button" class="${d.paid_by_epl ? 'on' : ''}" data-i="${i}" data-pay="1" ${khoaDuoc ? '' : 'disabled'}>${esc(NN.t('pay_epl'))}</button><button type="button" class="${!d.paid_by_epl ? 'on' : ''}" data-i="${i}" data-pay="0" ${khoaDuoc ? '' : 'disabled'}>${esc(NN.t('pay_own'))}</button></span></td>`;
        const acct = `<td><button type="button" class="acct px-acct" data-acct="${i}" ${AUTH.la('acct', 'fuel', 'rev') ? '' : 'disabled'} title="${esc(NN.t('acct_pair'))}">${esc(d.acct_code || tkMacDinh(m, d))}</button></td>`;
        const xoa = `<td class="no-print">${khoaDuoc ? `<button type="button" class="x" data-xoa="${i}" title="${esc(NN.t('delete'))}">×</button>` : ''}</td>`;
        if (m === 'fuel') return `<tr data-i="${i}" class="${lk && !d.paid_by_epl ? 'own' : ''}"><td>${n + 1}</td><td>${sel}</td><td>${inp('qty')}</td><td>${inp('unit_price')}</td>
          <td><select data-i="${i}" data-f="currency" ${khoaDuoc ? '' : 'disabled'}>${['LAK', 'VND', 'THB', 'USD'].map(c => `<option ${c === d.currency ? 'selected' : ''}>${c}</option>`).join('')}</select></td><td class="num amt"></td>
          <td><select data-i="${i}" data-f="place_id" ${khoaDuoc ? '' : 'disabled'}>${diemChon(d)}</select>
            <div class="small muted px-nguon">${NN.h(nguonCuaDiem(d) === 'kho' ? 'src_kho' : 'src_mua')}</div></td>${pay}${acct}${xoa}</tr>`;
        let nguon = '';
        if (m === 'repair') {
          const kho = d.source === 'kho', daXuat = !!d.stock_move_id;
          nguon = `<td><select data-i="${i}" data-f="source" ${khoaDuoc && !daXuat ? '' : 'disabled'}><option value="mua" ${!kho ? 'selected' : ''}>${esc(NN.t('src_mua'))}</option><option value="kho" ${kho ? 'selected' : ''}>${esc(NN.t('src_kho'))}</option></select>${
            kho ? `<select data-i="${i}" data-f="part_id" ${khoaDuoc && !daXuat ? '' : 'disabled'} style="margin-top:4px"><option value="">—</option>${DM.parts.map(p => `<option value="${p.id}" ${p.id === d.part_id ? 'selected' : ''}>${esc(p.name)} · ${so(p.qty)}</option>`).join('')}</select>` : ''}${
            daXuat ? `<div class="small muted">${esc(NN.t('fs_out'))} ✓</div>` : ''}</td>`;
        }
        return `<tr data-i="${i}" class="${lk && !d.paid_by_epl ? 'own' : ''}"><td>${n + 1}</td><td>${sel}</td>${nguon}<td>${inp('qty')}</td><td>${inp('unit_price')}</td><td class="num amt"></td>${pay}${acct}${xoa}</tr>`;
      }).join('') : `<tr><td colspan="10" class="empty small">${NN.h('no_data')}</td></tr>`;
    });
    q('#px-phieu').querySelectorAll('.px-chi [data-f]').forEach(el => el.addEventListener('input', e => {
      const d = P.expenses[+el.dataset.i], f = el.dataset.f; d[f] = el.value;
      if (f === 'item_key') { if (el.value === '') d.item_name = d.item_name || ''; else d.item_name = null; veChi(); }
      if (f === 'place_id') {
        // Nơi đổ quyết định LĨNH hay MUA, kéo theo định khoản …/371 hay …/402.
        d.source = nguonCuaDiem(d);
        if (P.company === 'joint') d.paid_by_epl = d.source === 'kho';
        d.acct_code = tkMacDinh('fuel', d); veChi();
      }
      if (f === 'source') { if (el.value !== 'kho') d.part_id = null; d.acct_code = tkMacDinh('repair', d); veChi(); }
      if (f === 'part_id') { const p = DM.parts.find(x => x.id === el.value); if (p) { d.item_key = null; d.item_name = p.name; d.unit_price = p.unit_price || 0; } veChi(); }
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
  function suaDuoc(m) { if (moi) return true; const st = (P.sections || {})[m] || 'wait'; return vai() === 'admin' || (perm().edit.includes(m) && (st === 'wait' || st === 'entered')); }
  function veVaiVaTrangThai() {
    g('px-goi-y').innerHTML = NN.h('hint_' + (vai() === 'treasury' ? 'treasury' : vai()));
    g('px-doc-no').disabled = !suaDuoc('info');
    g('px-trang-thai').innerHTML = moi ? '' : `${tag(P.transport_status)} ${tag(P.finance_status)}${P.invoiced ? ' ' + tag('paid', 'inv_done') : ''}`;
    MUC.forEach(m => {
      const sec = q(`.px-muc[data-muc="${m}"]`), st = moi ? 'wait' : (P.sections[m] || 'wait'), tuyChon = (m === 'repair' || m === 'other') && !P.expenses.some(d => d.section === m);
      const khoa = !suaDuoc(m); sec.classList.toggle('locked', khoa);
      const cot = m === 'info' ? COT_INFO : m === 'trans' ? COT_TRANS : [];
      cot.forEach(c => { const el = g('f-' + c); if (el) el.disabled = khoa; });
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
      if (AUTH.la('yard') && P.transport_status === 'dispatched') ta.push(`<button class="btn sm" data-tt="transit">${NN.h('mark_transit')}</button>`);
      if (AUTH.la('yard') && P.transport_status !== 'arrived') ta.push(`<button class="btn sm ok" data-tt="arrived">${NN.h('mark_arrived')}</button>`);
      if (AUTH.la('rev') && s.trans === 'verified' && !P.invoiced) ta.push(`<button class="btn sm ok" data-hd-phieu="invoice">${NN.h('a_invoice')}</button>`);
      if (AUTH.la('rev') && P.invoiced && P.finance_status !== 'paid') ta.push(`<button class="btn sm ok" data-fin="paid">${NN.h('a_collect')}</button><button class="btn sm" data-fin="partial">${NN.h('s_partial')}</button>`);
      if (AUTH.la('yard') && MUC.every(m => ['wait', 'entered'].includes(s[m] || 'wait'))) ta.push(`<button class="btn sm danger" data-hd-phieu="xoa">${NN.h('delete')}</button>`);
    }
    g('px-hanh-dong').innerHTML = ta.length ? `<span class="small muted">${NN.h('trip_status')}:</span> ${ta.join(' ')}` : `<span class="small muted">${NN.h('trip_status')}: ${moi ? NN.h('new_slip') : tag(P.transport_status) + ' ' + tag(P.finance_status)}</span>`;
    root.querySelectorAll('[data-tt]').forEach(b => b.addEventListener('click', () => doiTrangThai(b.dataset.tt)));
    root.querySelectorAll('[data-fin]').forEach(b => b.addEventListener('click', () => hanhDongPhieu('finance-status', { status: b.dataset.fin })));
    root.querySelectorAll('[data-hd-phieu]').forEach(b => b.addEventListener('click', () => b.dataset.hdPhieu === 'xoa' ? xoaPhieu() : hanhDongPhieu(b.dataset.hdPhieu)));
    g('px-log').innerHTML = `<h5>${NN.h('log_title')}</h5><ul>${(P.logs || []).length ? P.logs.map(l => `<li><span class="ts">${EPL.ngayGio(l.ts)}</span><span><b lang="lo">${esc(l.user)}</b> <span class="muted">(${NN.h('r_' + l.role)})</span> · ${esc(nhanLog(l.action))}</span></li>`).join('') : `<li class="muted">${NN.h('log_empty')}</li>`}</ul>`;
  }
  function nhanLog(a) {
    if (!a) return ''; const m = a.match(/^sec_(\w+):(\w+)$/); if (m) return `${NN.t('sec' + (MUC.indexOf(m[1]) + 1))} → ${NN.t('a_' + m[2])}`;
    return NN.t(a);
  }
  function veHet() { veChon(); veDanhMuc(); doTruong(); veChi(); veVaiVaTrangThai(); NN.apDung(root); }

  /* ---------------------------------------------------------------- dữ liệu */
  function phieuTrong() {
    return { id: null, doc_no: '', company: 'EPL', goods_type: 'iron_ore', doc_date: EPL.homNay(), out_date: EPL.homNay(), fee_pct: 2, over_limit_t: 40, over_price_usd: 1,
      rate_usd: ty_gia.USD || 22000, rate_thb: ty_gia.THB || 700, rate_vnd: ty_gia.VND || 1.2, transport_status: 'dispatched', finance_status: 'unpaid', invoiced: false,
      sections: {}, expenses: [], logs: [] };
  }
  async function moPhieu(id) { moi = false; P = await API.get('/api/trips/' + id); veHet(); }
  async function phieuMoi() { moi = true; P = phieuTrong(); const s = await API.get('/api/trips-so-moi').catch(() => ({ doc_no: '' })); P.doc_no = s.doc_no; veHet(); }
  function docForm() {
    P.doc_no = g('px-doc-no').value.trim();
    [...COT_INFO, ...COT_TRANS].forEach(c => { const el = g('f-' + c); if (!el || el.disabled) return; P[c] = el.value === '' ? null : (SO.has(c) ? EPL.doc(el.value) : el.value); });
  }
  async function luu() {
    docForm();
    const x = DM.vehicles.find(v => v.id === P.vehicle_id); if (x) { P.truck_no = x.truck_no; if (!P.brand_model) P.brand_model = x.brand_model; if (!P.plate_head) P.plate_head = x.plate_head; if (!P.plate_trailer) P.plate_trailer = x.plate_trailer; }
    const d = DM.drivers.find(v => v.id === P.driver_id); if (d) P.driver_name = d.name;
    const k = DM.customers.find(v => v.id === P.customer_id); if (k) P.customer_name = k.name;
    const body = {}; ['doc_no', 'truck_no', 'driver_name', 'customer_name', ...COT_INFO, ...COT_TRANS].forEach(c => { if (P[c] !== undefined) body[c] = P[c]; });
    // chỉ gửi dòng chi của mục còn sửa được — mục khoá gửi lên là máy chủ từ chối cả phiếu
    body.expenses = P.expenses.filter(e => suaDuoc(e.section)).map(e => ({ ...e, qty: EPL.doc(e.qty), unit_price: EPL.doc(e.unit_price), acct_code: e.acct_code || tkMacDinh(e.section, e) }));
    if (!moi) { MUC_CHI.forEach(m => { if (!suaDuoc(m)) body.expenses = body.expenses.filter(e => e.section !== m); }); }
    try {
      P = moi ? await API.post('/api/trips', body) : await API.put('/api/trips/' + P.id, body);
      moi = false; DS = await API.get('/api/trips'); EPL.toast(NN.t('saved'), 'ok'); veHet();
      history.replaceState(null, '', '#/phieu-xuat-xe?id=' + P.id);
    } catch (e) { EPL.baoLoi(e); }
  }
  async function duyet(m, hd) {
    if (moi) return EPL.toast(NN.t('save') + '?', 'loi');
    if (hd === 'send' && suaDuoc(m)) { await luu(); if (moi) return; }
    if (hd === 'return' || hd === 'unlock') { if (!await EPL.hoi(NN.t('a_' + hd), NN.t('confirm_action'))) return; }
    try { P = await API.post(`/api/trips/${P.id}/sections/${m}/${hd}`); veHet(); } catch (e) { EPL.baoLoi(e); }
  }
  async function doiTrangThai(tt) {
    const body = { status: tt };
    if (tt === 'arrived') {
      const v = await EPL.hopNhap(NN.t('mark_arrived'), [{ id: 'weight_dest', label: 'weight_dest_prompt', type: 'number', value: P.weight_dest ?? '' }, { id: 'back_date', label: 'd_back', type: 'date', value: P.back_date || EPL.homNay() }], NN.t('ok'));
      if (!v) return; body.weight_dest = v.weight_dest; body.back_date = v.back_date;
    }
    try { P = await API.post(`/api/trips/${P.id}/transport-status`, body); DS = await API.get('/api/trips'); veHet(); } catch (e) { EPL.baoLoi(e); }
  }
  async function hanhDongPhieu(hd, body) {
    if (!await EPL.hoi(NN.t(hd === 'invoice' ? 'a_invoice' : 'a_collect'), NN.t('confirm_action'))) return;
    try { P = await API.post(`/api/trips/${P.id}/${hd}`, body || {}); DS = await API.get('/api/trips'); veHet(); } catch (e) { EPL.baoLoi(e); }
  }
  async function xoaPhieu() {
    if (!await EPL.hoi(NN.t('delete') + ' ' + P.doc_no, NN.t('confirm_delete'), NN.t('delete'))) return;
    try { await API.del('/api/trips/' + P.id); DS = await API.get('/api/trips'); EPL.toast(NN.t('saved'), 'ok'); if (DS.length) await moPhieu(DS[0].id); else await phieuMoi(); } catch (e) { EPL.baoLoi(e); }
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
      [KM, DS, ty_gia, DM.customers, DM.vehicles, DM.drivers, DM.routes, DM.parts, DM.places] = await Promise.all([
        API.get('/api/khoan-muc'), API.get('/api/trips'), API.get('/api/rates'), API.get('/api/customers'),
        API.get('/api/vehicles'), API.get('/api/drivers'), API.get('/api/routes'), API.get('/api/parts'),
        API.get('/api/fuel-places')]);
      g('px-ve').addEventListener('click', () => EPL.di('theo-doi'));
      g('px-moi').addEventListener('click', () => phieuMoi().catch(EPL.baoLoi));
      g('px-luu').addEventListener('click', luu);
      g('px-hoa-don').addEventListener('click', () => P && P.id && EPL.di('hoa-don', { id: P.id }));
      g('px-chung-tu').addEventListener('click', () => P && P.id && EPL.di('chung-tu', { id: P.id }));
      g('px-phieu-linh').addEventListener('click', lapPhieuLinh);
      g('px-chon').addEventListener('change', e => { if (e.target.value) moPhieu(e.target.value).catch(EPL.baoLoi); });
      root.querySelectorAll('.px-them').forEach(b => b.addEventListener('click', () => themDong(b.dataset.them)));
      // đầu vào mục I–II → cập nhật số ngay
      [...COT_INFO, ...COT_TRANS].forEach(c => { const el = g('f-' + c); if (!el) return; el.addEventListener('input', () => {
        P[c] = el.value === '' ? null : (SO.has(c) ? el.value : el.value);
        if (c === 'company') { P.expenses.forEach(e => { e.acct_code = tkMacDinh(e.section, e); }); if (P.company === 'joint' && (P.hire_price_usd == null || P.hire_price_usd === '')) { P.hire_price_usd = P.price_usd; g('f-hire_price_usd').value = P.price_usd ?? ''; } q('#px-phieu').classList.toggle('is-joint', P.company === 'joint'); veChi(); }
        if (c === 'route_id') { const r = DM.routes.find(x => x.id === el.value); if (r) { g('f-origin').value = P.origin = r.origin; g('f-destination').value = P.destination = r.destination; } }
        if (c === 'vehicle_id') { const x = DM.vehicles.find(v => v.id === el.value); if (x) { g('f-brand_model').value = P.brand_model = x.brand_model || ''; g('f-plate_head').value = P.plate_head = x.plate_head || ''; g('f-plate_trailer').value = P.plate_trailer = x.plate_trailer || ''; if (x.owner_type === 'joint') { P.company = 'joint'; g('f-company').value = 'joint'; g('f-owner_name').value = P.owner_name = x.owner_name || ''; q('#px-phieu').classList.add('is-joint'); veChi(); } } }
        veSo();
      }); });
      const t = ctx.tham || {};
      if (t.moi) await phieuMoi(); else if (t.id) await moPhieu(t.id); else if (DS.length) await moPhieu(DS[0].id); else await phieuMoi();
    },
    onLang() { if (P) veHet(); },
  };
})();

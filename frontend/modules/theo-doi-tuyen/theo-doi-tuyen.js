/* Theo dõi tuyến — xe đang ở chặng nào, sự cố, sửa xe trên đường (rơi vào mục V của phiếu). */
(function () {
  const { API, NN, esc, so, AUTH, tag } = EPL;
  let root, DS = [], P = null, PARTS = [], KM = null, nguon = 'kho';
  const q = (s) => root.querySelector(s);
  const laBai = () => AUTH.la('yard');

  function rate(ma) { return { USD: P.rate_usd, THB: P.rate_thb, VND: P.rate_vnd, LAK: 1 }[ma] || 1; }
  function veChon() {
    const chiChay = q('#tdt-chi-chay').checked;
    const ds = DS.filter(p => !chiChay || p.transport_status !== 'arrived' || (P && p.id === P.id));
    q('#tdt-chon').innerHTML = ds.map(p => `<option value="${p.id}" ${P && p.id === P.id ? 'selected' : ''}>${esc(p.doc_no)} · ${esc(p.truck_no || '')} · ${esc(p.origin || '')} → ${esc(p.destination || '')}</option>`).join('')
      || `<option value="">${esc(NN.t('no_data'))}</option>`;
  }
  function ve() {
    if (!P) { q('#tdt-tien-do').innerHTML = `<div class="muted">${NN.h('no_data')}</div>`; return; }
    q('#tdt-dau').innerHTML = `${tag(P.transport_status)} ${tag(P.finance_status)}`;
    const diem = P.route_stops || [], toi = P.stop_reached || 0;
    if (!diem.length) {
      q('#tdt-tien-do').innerHTML = `<div class="muted small">${NN.h('no_route')}</div>`;
    } else {
      q('#tdt-tien-do').innerHTML = `<div class="tdt-tuyen">${diem.map(s => {
        const done = s.seq <= toi, now = s.seq === toi + 1 && P.transport_status !== 'arrived';
        return `<div class="tdt-moc ${done ? 'done' : ''} ${now ? 'now' : ''}"><div class="cham">${done ? '✓' : s.seq}</div>
          <div class="ten" lang="lo">${esc(s.name)}</div><div class="km">${s.seq > 1 ? '+' + so(s.km_from_prev, 1) + ' km' : NN.t('origin')}</div>
          ${laBai() && now ? `<button class="btn sm ok" data-toi="${s.seq}">${NN.h('mark_stop')}</button>` : ''}</div>`; }).join('')}</div>
        <div class="small muted">${NN.h('total_km')}: <b>${so(diem.reduce((a, s) => a + (s.km_from_prev || 0), 0), 1)}</b> km · ${NN.h('ev_arrive_stop')}: ${toi}/${diem.length}</div>`;
      q('#tdt-tien-do').querySelectorAll('[data-toi]').forEach(b => b.addEventListener('click', () => toiDiem(+b.dataset.toi, diem.length)));
    }
    const ev = (P.events || []).slice().reverse();
    q('#tdt-su-kien').innerHTML = ev.length ? ev.map(e => `<tr><td class="nowrap">${EPL.ngayGio(e.ts)}</td>
      <td><span class="tag ${e.kind === 'incident' ? 'tdt-tag-in' : e.kind === 'repair' ? 'tdt-tag-rp' : 'plain'}">${NN.h('ev_' + e.kind)}${e.incident_type ? ' · ' + NN.h('inc_' + e.incident_type) : ''}</span></td>
      <td lang="lo">${e.stop_seq ? esc((diem.find(s => s.seq === e.stop_seq) || {}).name || e.stop_seq) : '—'}</td><td lang="lo">${esc(e.note) || ''}</td><td lang="lo">${esc(e.by_user) || ''}</td></tr>`).join('')
      : `<tr><td colspan="5" class="empty">${NN.h('log_empty')}</td></tr>`;
    // Báo hỏng của TÀI XẾ đang chờ: Bãi/admin duyệt (→ dòng mục V) hoặc từ chối
    const cho = (P.events || []).filter(e => e.status === 'reported');
    q('#tdt-khoi-cho').hidden = !cho.length;
    q('#tdt-cho-duyet').innerHTML = cho.map(e => `<tr><td class="nowrap">${EPL.ngayGio(e.ts)}</td><td>${NN.h('inc_' + (e.incident_type || 'other'))}</td><td lang="lo">${esc(e.note || '')}</td>
      <td class="num">${e.reported_cost != null ? so(e.reported_cost) + ' ' + esc(e.currency || 'LAK') : '—'}</td><td lang="lo">${esc(e.by_user || '')}</td>
      <td class="no-print">${laBai() ? `<button class="btn sm ok" data-duyet="${e.id}">${NN.h('approve')}</button> <button class="btn sm danger" data-tu-choi="${e.id}">${NN.h('reject')}</button>` : ''}</td></tr>`).join('');
    q('#tdt-cho-duyet').querySelectorAll('[data-duyet]').forEach(b => b.addEventListener('click', () => duyet(cho.find(e => e.id === b.dataset.duyet))));
    q('#tdt-cho-duyet').querySelectorAll('[data-tu-choi]').forEach(b => b.addEventListener('click', () => tuChoi(cho.find(e => e.id === b.dataset.tuChoi))));
    const sua = (P.expenses || []).filter(d => d.section === 'repair'); let tong = 0;
    q('#tdt-sua').innerHTML = sua.length ? sua.map(d => { const t = d.qty * d.unit_price * rate(d.currency); tong += t;
      return `<tr><td lang="lo">${esc(EPL.khoanMuc(d))}</td><td>${d.source ? NN.h('src_' + d.source) : '—'}</td><td class="num">${so(d.qty)}</td><td class="num">${so(t)}</td><td><span class="acct">${esc(d.acct_code || '')}</span></td></tr>`; }).join('')
      : `<tr><td colspan="5" class="empty">${NN.h('no_expense')}</td></tr>`;
    q('#tdt-sua-tom').innerHTML = `${NN.h('total')}: <b>${so(tong)} LAK</b> · ${NN.h('sections_status')} V: ${NN.h((P.sections || {}).repair === 'wait' ? 'stt_wait2' : 'stt_' + ((P.sections || {}).repair || 'wait'))}`;
    q('#tdt-xe').innerHTML = [['truck_no', P.truck_no], ['driver', P.driver_name], ['plate_head', P.plate_head], ['plate_trailer', P.plate_trailer],
      ['customer', P.customer_name], ['w_origin', so(P.weight_origin, 2) + ' t'], ['d_out', EPL.ngay(P.out_date)], ['d_back', EPL.ngay(P.back_date)]]
      .map(([k, v]) => `<div><span>${NN.h(k)}</span><span lang="lo">${esc(v == null ? '—' : v)}</span></div>`).join('');
    q('#tdt-su-co').hidden = q('#tdt-ghi-chu').hidden = !laBai() || P.finance_status === 'paid';
  }
  async function mo(id) { P = await API.get('/api/trips/' + id); veChon(); ve(); }
  async function toiDiem(seq, tong) {
    try {
      P = await API.post(`/api/trips/${P.id}/events`, { kind: 'arrive_stop', stop_seq: seq });
      if (seq === tong && P.transport_status !== 'arrived') {
        const v = await EPL.hopNhap(NN.t('mark_arrived'), [{ id: 'weight_dest', label: 'weight_dest_prompt', type: 'number', value: P.weight_dest ?? '' },
          { id: 'odo_back', label: 'odo_back', type: 'number', value: P.odo_back ?? '' }, { id: 'back_date', label: 'd_back', type: 'date', value: P.back_date || EPL.homNay() }], NN.t('ok'));
        if (v) P = await API.post(`/api/trips/${P.id}/transport-status`, { status: 'arrived', ...v });
      }
      DS = await API.get('/api/trips'); veChon(); ve();
    } catch (e) { EPL.baoLoi(e); }
  }
  async function ghiChu() {
    const v = await EPL.hopNhap(NN.t('add_note'), [{ id: 'note', label: 'note', value: '', lo: true }], NN.t('save'));
    if (!v || !v.note.trim()) return;
    try { P = await API.post(`/api/trips/${P.id}/events`, { kind: 'note', note: v.note }); ve(); } catch (e) { EPL.baoLoi(e); }
  }
  function moSuCo() {
    const dlg = q('#tdt-hop');
    q('#tdt-f-diem').innerHTML = `<option value="">—</option>` + (P.route_stops || []).map(s => `<option value="${s.seq}" ${s.seq === (P.stop_reached || 0) + 1 ? 'selected' : ''}>${s.seq}. ${esc(s.name)}</option>`).join('');
    q('#tdt-f-ghi').value = ''; q('#tdt-f-co-sua').checked = false; q('#tdt-f-sua').hidden = true; q('#tdt-f-sl').value = '1'; q('#tdt-f-gia').value = '';
    q('#tdt-f-part').innerHTML = PARTS.filter(p => p.qty > 0).map(p => `<option value="${p.id}" data-gia="${p.unit_price || 0}">${esc(p.name)} · ${NN.t('stock_left')} ${so(p.qty)} ${NN.t(p.unit)}</option>`).join('') || `<option value="">${esc(NN.t('no_data'))}</option>`;
    datNguon('kho'); NN.apDung(dlg); dlg.returnValue = '';
    dlg.addEventListener('close', async function xong() {
      dlg.removeEventListener('close', xong);
      if (dlg.returnValue !== 'ok') return;
      const body = { kind: q('#tdt-f-co-sua').checked ? 'repair' : 'incident', incident_type: q('#tdt-f-loai').value, note: q('#tdt-f-ghi').value };
      if (q('#tdt-f-diem').value) body.stop_seq = +q('#tdt-f-diem').value;
      if (q('#tdt-f-co-sua').checked) {
        body.repair = { source: nguon, qty: EPL.doc(q('#tdt-f-sl').value), currency: q('#tdt-f-tien').value };
        if (nguon === 'kho') body.repair.part_id = q('#tdt-f-part').value; else body.repair.item_name = q('#tdt-f-ten').value;
        if (q('#tdt-f-gia').value !== '') body.repair.unit_price = EPL.doc(q('#tdt-f-gia').value);
      }
      try { P = await API.post(`/api/trips/${P.id}/events`, body); PARTS = await API.get('/api/parts'); EPL.toast(NN.t('saved'), 'ok'); ve(); } catch (e) { EPL.baoLoi(e); }
    });
    dlg.showModal();
  }
  async function duyet(e) {
    const v = await EPL.hopNhap(NN.t('approve') + ' — ' + (e.note || ''), [
      { id: 'source', label: 'source', type: 'select', value: 'mua', options: [['mua', NN.t('src_mua')], ['kho', NN.t('src_kho')]] },
      { id: 'part_id', label: 'pick_part', type: 'select', value: '', options: [['', '—']].concat(PARTS.filter(p => p.qty > 0).map(p => [p.id, p.name + ' · ' + NN.t('stock_left') + ' ' + so(p.qty)])) },
      { id: 'item_name', label: 'item', value: e.note || '', lo: true },
      { id: 'qty', label: 'qty', type: 'number', value: '1' },
      { id: 'unit_price', label: 'unit_price', type: 'number', value: e.reported_cost != null ? e.reported_cost : '' },
      { id: 'currency', label: 'cur', type: 'select', value: e.currency || 'LAK', options: [['LAK', 'LAK'], ['VND', 'VND'], ['THB', 'THB'], ['USD', 'USD']] },
    ], NN.t('approve'));
    if (!v) return;
    if (v.source !== 'kho') delete v.part_id;
    if (v.unit_price === '') delete v.unit_price;
    try { P = await API.post(`/api/trips/${P.id}/events/${e.id}/duyet`, v); PARTS = await API.get('/api/parts'); EPL.toast(NN.t('saved'), 'ok'); ve(); } catch (x) { EPL.baoLoi(x); }
  }
  async function tuChoi(e) {
    const v = await EPL.hopNhap(NN.t('reject') + ' — ' + (e.note || ''), [{ id: 'reason', label: 'reject_reason', value: '', lo: true }], NN.t('reject'));
    if (!v) return;
    try { P = await API.post(`/api/trips/${P.id}/events/${e.id}/duyet`, { reject: true, reason: v.reason }); ve(); } catch (x) { EPL.baoLoi(x); }
  }
  function datNguon(n) {
    nguon = n; root.querySelectorAll('.tdt-nguon button').forEach(b => b.classList.toggle('on', b.dataset.src === n));
    q('#tdt-f-o-part').hidden = n !== 'kho'; q('#tdt-f-o-ten').hidden = n !== 'mua';
    if (n === 'kho') { const o = q('#tdt-f-part').selectedOptions[0]; if (o) q('#tdt-f-gia').value = o.dataset.gia || ''; }
  }

  EPL.modules['theo-doi-tuyen'] = {
    async init(r, ctx) {
      root = r;
      [DS, PARTS, KM] = await Promise.all([API.get('/api/trips'), API.get('/api/parts'), API.get('/api/khoan-muc')]);
      q('#tdt-chon').addEventListener('change', e => e.target.value && mo(e.target.value).catch(EPL.baoLoi));
      q('#tdt-chi-chay').addEventListener('change', veChon);
      q('#tdt-mo-phieu').addEventListener('click', () => P && EPL.di('phieu-xuat-xe', { id: P.id }));
      q('#tdt-su-co').addEventListener('click', moSuCo); q('#tdt-ghi-chu').addEventListener('click', ghiChu);
      q('#tdt-f-co-sua').addEventListener('change', e => { q('#tdt-f-sua').hidden = !e.target.checked; });
      root.querySelectorAll('.tdt-nguon button').forEach(b => b.addEventListener('click', () => datNguon(b.dataset.src)));
      q('#tdt-f-part').addEventListener('change', () => datNguon('kho'));
      const t = ctx.tham || {}; const dau = t.id || (DS.find(p => p.transport_status !== 'arrived') || DS[0] || {}).id;
      veChon(); if (dau) await mo(dau); else ve();
    },
    onLang() { if (root) { veChon(); ve(); } },
  };
})();

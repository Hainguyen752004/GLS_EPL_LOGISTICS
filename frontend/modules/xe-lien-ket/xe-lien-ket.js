/* Xe liên kết — mỗi dòng một phiếu xe ngoài, đủ phép tính trả chủ xe và lãi EPL. */
(function () {
  const { API, NN, esc, so, tag, AUTH } = EPL;
  let root, ds = [], chu = [], HD = [], chuHd = null;
  const OPM = { phieu: 'opm_phieu', thang: 'opm_thang', dot: 'opm_dot' };
  const CACH = [['cash', 'pm_cash'], ['bank', 'pm_bank'], ['offset', 'pm_offset'], ['other', 'pm_other']];

  /* ---------------------------------------------------------------- chủ xe liên kết (C4.2 · C4.3) */
  function veChu() {
    const o = root.querySelector('#xlk-chu'); if (!o) return;
    const themDuoc = AUTH.la('acct');
    root.querySelector('#xlk-them-chu').hidden = !themDuoc;
    o.innerHTML = chu.length ? chu.map(c => {
      const ct = c.cho_tra || {};
      return `<tr class="${c.active ? '' : 'xlk-tat'}">
        <td lang="lo"><b>${esc(c.name)}</b>${c.note ? `<div class="small muted">${esc(c.note)}</div>` : ''}</td>
        <td class="mono">${esc(c.phone || '—')}</td><td class="mono">${(c.so_xe || []).map(esc).join(', ') || '—'}</td>
        <td>${EPL.hopDong.nhan(EPL.hopDong.hienHanh(HD, c.id))}</td>
        <td>${NN.h(OPM[c.pay_mode] || 'opm_phieu')}</td>
        <td class="num tien">${c.fee_pct != null ? so(c.fee_pct, 1) + ' %' : '—'}</td>
        <td class="num tien">${c.over_limit_t != null ? `${so(c.over_limit_t, 1)} t · ${EPL.tien(c.over_price, c.hire_ccy)}/t` : '—'}</td>
        <td class="mono tien">${esc(c.hire_ccy || '')}</td>
        <td class="num tien">${ct.so_phieu ? `<b>${ct.so_phieu}</b> ${NN.t('trips')} · ${EPL.tienGop(ct.tong)}` : `<span class="muted">${NN.h('owner_no_pending')}</span>`}${
          ct.so_phieu_ban ? `<div class="small neg">− ${NN.h('owner_sales_pending')}: ${so(ct.ban_cho_tru_lak)} LAK (${ct.so_phieu_ban})</div>` : ''}</td>
        <td class="no-print">${themDuoc ? `<button class="btn sm" data-sua-chu="${c.id}">${NN.h('edit')}</button> ` : ''}<button class="btn sm ${chuHd && chuHd.id === c.id ? 'primary' : ''}" data-hd-chu="${c.id}">${NN.h('hd_nut')}</button> ${AUTH.la('cash', 'treasury') && ct.so_phieu ? `<button class="btn sm ok" data-tra-chu="${c.id}">${NN.h('owner_pay_batch')}</button>` : ''}</td></tr>`;
    }).join('') : `<tr><td colspan="10" class="empty">${NN.h('no_data')}</td></tr>`;
    o.querySelectorAll('[data-hd-chu]').forEach(b => b.addEventListener('click', () => moHd(chu.find(x => x.id === b.dataset.hdChu))));
    o.querySelectorAll('[data-sua-chu]').forEach(b => b.addEventListener('click', () => suaChu(chu.find(x => x.id === b.dataset.suaChu))));
    o.querySelectorAll('[data-tra-chu]').forEach(b => b.addEventListener('click', () => traGop(chu.find(x => x.id === b.dataset.traChu))));
  }
  async function suaChu(c) {
    const v = await EPL.hopNhap(c ? NN.t('edit') + ' · ' + c.name : NN.t('owner_add'), [
      { id: 'name', label: 'owner', value: c ? c.name : '', lo: true },
      { id: 'phone', label: 'phone', value: c ? c.phone : '' },
      { id: 'address', label: 'address', value: c ? c.address : '', lo: true },
      { id: 'pay_mode', label: 'owner_pay_mode', type: 'select', value: c ? c.pay_mode : 'phieu', options: Object.entries(OPM).map(([k, t]) => [k, NN.t(t)]) },
      { id: 'hire_ccy', label: 'ccy_hire', type: 'select', value: c ? (c.hire_ccy || 'USD') : 'USD', options: EPL.TIEN_TE.map(m => [m, m]) },
      { id: 'fee_pct', label: 'fee_pct', type: 'number', value: c ? c.fee_pct : 2 },
      { id: 'over_limit_t', label: 'limit_t', type: 'number', value: c ? c.over_limit_t : 40 },
      { id: 'over_price', label: 'over_p', type: 'number', value: c ? c.over_price : 1 },
      { id: 'note', label: 'note', type: 'textarea', value: c ? c.note : '' },
      ...(c ? [{ id: 'active', label: 'status', type: 'select', value: c.active ? '1' : '0', options: [['1', NN.t('active')], ['0', NN.t('inactive')]] }] : []),
    ], NN.t('save'));
    if (!v) return;
    if (!v.name.trim()) return EPL.toast(NN.t('owner') + '?', 'loi');
    const body = { name: v.name, phone: v.phone, address: v.address, pay_mode: v.pay_mode, hire_ccy: v.hire_ccy, fee_pct: v.fee_pct, over_limit_t: v.over_limit_t, over_price: v.over_price, note: v.note };
    if (c) body.active = v.active === '1';
    try { await (c ? API.put('/api/owners/' + c.id, body) : API.post('/api/owners', body)); EPL.toast(NN.t('saved'), 'ok'); await tai(); } catch (e) { EPL.baoLoi(e); }
  }
  /** Trả gộp: chọn các phiếu đã khoá chưa trả của chủ xe → một đợt, một chứng từ PC_CX. Số tiền là tổng
   *  "trả chủ xe" của các phiếu đã chọn, máy tính — không gõ tay. */
  async function traGop(c) {
    let cn;
    try { cn = await API.get(`/api/owners/${c.id}/cong-no`); } catch (e) { return EPL.baoLoi(e); }
    const ds_ = cn.cho_tra || [];
    if (!ds_.length) return EPL.toast(NN.t('owner_no_pending'), 'loi');
    const html = `<p class="small muted">${NN.h('owner_pick_trips')}</p>
      <div class="xlk-chon">${ds_.map(p => `<label><input type="checkbox" name="xlk-p" value="${esc(p.id)}" data-ccy="${esc(p.hire_ccy)}" data-tien="${p.tra_chu_xe}" checked>
        <span class="mono">${esc(p.doc_no)}</span> · ${EPL.ngay(p.doc_date)} · ${esc(p.truck_no || '')} · <b>${EPL.tien(p.tra_chu_xe, p.hire_ccy)}</b></label>`).join('')}</div>
      <div class="xlk-tong" id="xlk-tong"></div>
      ${(cn.ban_cho_tru || []).length ? `<div class="xlk-ban small"><b>${NN.h('owner_sales_pending')}</b> — ${NN.h('owner_sales_hint')}
        <ul>${cn.ban_cho_tru.map(b => `<li><span class="mono">${esc(b.doc_no)}</span> · ${EPL.ngay(b.sale_date)} · ${EPL.tien(b.total, b.currency)} (${so(b.total_lak)} LAK)</li>`).join('')}</ul></div>` : ''}
      <div class="field"><label>${NN.h('pay_date')}</label><input type="date" id="xlk-ngay" value="${EPL.homNay()}"></div>
      <div class="field"><label>${NN.h('pay_method')}</label><select id="xlk-cach">${CACH.map(([k, t]) => `<option value="${k}">${NN.t(t)}</option>`).join('')}</select></div>
      <div class="field"><label>${NN.h('pay_ref')}</label><input id="xlk-ref"></div>
      <div class="field"><label>${NN.h('note')}</label><input id="xlk-ghi"></div>`;
    // Tổng tự tính theo ô đang tích, chia theo tiền thuê — khác tiền thì máy chủ sẽ bắt tách đợt
    const capNhat = () => {
      const t = {}; document.querySelectorAll('input[name="xlk-p"]:checked').forEach(i => { t[i.dataset.ccy] = (t[i.dataset.ccy] || 0) + EPL.doc(i.dataset.tien); });
      const o = document.getElementById('xlk-tong'); if (o) o.innerHTML = `<b>${NN.h('total')}:</b> ${EPL.tienGop(t)}${Object.keys(t).length > 1 ? ` <span class="neg">· ${NN.h('owner_mixed_ccy')}</span>` : ''}`;
    };
    setTimeout(() => { document.querySelectorAll('input[name="xlk-p"]').forEach(i => i.addEventListener('change', capNhat)); capNhat(); }, 0);
    const ok = await EPL.hoi(`${NN.t('owner_pay_batch')} · ${c.name}`, html, NN.t('pay_owner'));
    if (!ok) return;
    const ids = [...document.querySelectorAll('input[name="xlk-p"]:checked')].map(i => i.value);
    const body = { trip_ids: ids, pay_date: document.getElementById('xlk-ngay').value, method: document.getElementById('xlk-cach').value,
      ref: document.getElementById('xlk-ref').value, note: document.getElementById('xlk-ghi').value };
    try { await API.post(`/api/owners/${c.id}/tra`, body); EPL.toast(NN.t('owner_paid_batch'), 'ok'); await tai(); } catch (e) { EPL.baoLoi(e); }
  }
  /* Mỗi phiếu có tiền bán và tiền thuê riêng, nên bảng in kèm mã tiền từng ô và cộng theo LAK. */
  function ve() {
    let tValL = 0, tThueL = 0, tTraL = 0, tLaiL = 0;
    const t = EPL.tien;
    root.querySelector('#xlk-than').innerHTML = ds.length ? ds.map((p, i) => {
      const c = p.tinh, ma = c.ccy, mh = c.hire_ccy || ma;
      tValL += c.doanh_thu_lak; tThueL += c.tien_thue_lak; tTraL += c.tra_chu_xe_lak; tLaiL += c.lai_lak; return `<tr data-id="${p.id}">
      <td>${i + 1}</td><td>${EPL.ngay(p.doc_date)}</td><td class="mono"><b>${esc(p.doc_no)}</b></td><td lang="lo">${esc(p.owner_name) || '—'}</td><td>${esc(p.truck_no)}</td>
      <td lang="lo" class="small">${esc(p.plate_head)}<br>${esc(p.plate_trailer)}</td><td lang="lo">${esc(p.driver_name) || '—'}</td>
      <td class="num">${so(c.tan_tinh, 2)}</td><td class="num">${t(p.price, ma)}</td><td class="num">${t(c.gia_thue, mh)}</td>
      <td class="num"><b>${t(c.doanh_thu, ma)}</b></td><td class="num">${t(c.tien_thue, mh)}</td><td class="num neg">− ${t(c.phi, mh)}</td><td class="num neg">− ${t(c.tru_vuot, mh)}</td><td class="num neg">− ${t(c.ung_truoc, mh)}</td>
      <td class="num"><b>${t(c.tra_chu_xe, mh)}</b></td><td class="num pos"><b>${t(c.lai, ma)}</b></td><td>${tag(p.transport_status)}</td><td>${tag(p.finance_status)}</td>
      <td class="no-print">${p.owner_paid ? tag('paid', 'owner_paid') : (p.locked ? (AUTH.la('cash', 'treasury') && c.tra_chu_xe > 0 ? (tungPhieu(p) ? `<button class="btn sm ok" data-tra="${p.id}">${NN.h('pay_owner')}</button>` : `<span class="small muted">${NN.h('owner_pay_in_batch')}</span>`) : `<span class="small muted">${NN.h('owner_unpaid')}</span>`) : `<span class="small muted">${NN.h('owner_wait_lock')}</span>`)}</td></tr>`; }).join('')
      : `<tr><td colspan="20" class="empty">${NN.h('no_data')}</td></tr>`;
    root.querySelector('#xlk-chan').innerHTML = `<tr><td colspan="10">${NN.ghep([{ k: 'total' }, ' · ' + ds.length + ' ', { k: 'trips' }])}</td><td class="num">${t(tValL, 'LAK')}</td><td class="num">${t(tThueL, 'LAK')}</td><td colspan="3"></td><td class="num">${t(tTraL, 'LAK')}</td><td class="num pos">${t(tLaiL, 'LAK')}</td><td colspan="3"></td></tr>`;
    root.querySelector('#xlk-dem').textContent = `${ds.length} ${NN.t('trips')} · ${NN.t('ccy_note')}`;
    root.querySelectorAll('#xlk-than tr[data-id]').forEach(tr => tr.addEventListener('click', (e) => { if (!e.target.closest('[data-tra]')) EPL.di('phieu-xuat-xe', { id: tr.dataset.id }); }));
    root.querySelectorAll('[data-tra]').forEach(b => b.addEventListener('click', async () => {
      const p = ds.find(x => x.id === b.dataset.tra), c = p.tinh, mh = c.hire_ccy || c.ccy;
      const ok = await EPL.hoi(NN.t('pay_owner'), `<p><b lang="lo">${esc(p.owner_name || '')}</b> · <span class="mono">${esc(p.doc_no)}</span></p><p class="hi">${EPL.tien(c.tra_chu_xe, mh)}</p>
        <p class="small muted">${EPL.tien(c.tien_thue, mh)} − ${so(c.phi, EPL.leTien(mh))} − ${so(c.tru_vuot, EPL.leTien(mh))} − ${so(c.ung_truoc, EPL.leTien(mh))}</p>`, NN.t('pay_owner'));
      if (!ok) return;
      try { await API.post(`/api/trips/${p.id}/tra-chu-xe`, {}); EPL.toast(NN.t('saved'), 'ok'); await tai(); } catch (e) { EPL.baoLoi(e); }
    }));
  }
  /** Chủ xe trả theo từng phiếu (hay phiếu chưa gắn chủ xe trong danh mục) thì nút trả nằm ngay trên dòng;
   *  trả gộp tháng / theo đợt thì bấm ở bảng Chủ xe phía trên để chọn nhiều phiếu một lần. */
  const tungPhieu = (p) => { const c = chu.find(x => x.id === p.owner_id); return !c || (c.pay_mode || 'phieu') === 'phieu'; };
  async function taiHd() { try { HD = await API.get('/api/hop-dong?kind=thue_xe'); } catch (e) { HD = []; } }
  async function moHd(c) {
    chuHd = c; veChu();
    await EPL.hopDong.mo(root.querySelector('#xlk-hd'), { kind: 'thue_xe', doiTacId: c.id, ten: c.name, suaDuoc: AUTH.la('acct'),
      onDoi: async () => { await taiHd(); if (root.querySelector('#xlk-hd').hidden) chuHd = null; veChu(); } });
  }
  async function tai() {
    await taiHd();
    const th = root.querySelector('#xlk-thang').value;
    [ds, chu] = await Promise.all([API.get('/api/bao-cao/xe-lien-ket' + (th ? '?thang=' + th : '')), API.get('/api/owners').catch(() => [])]);
    veChu(); ve();
  }
  EPL.modules['xe-lien-ket'] = {
    async init(r) { root = r; r.querySelector('#xlk-thang').addEventListener('change', () => tai().catch(EPL.baoLoi)); r.querySelector('#xlk-them-chu').addEventListener('click', () => suaChu(null)); await tai(); },
    onLang() { if (root) { veChu(); ve(); } },
  };
})();

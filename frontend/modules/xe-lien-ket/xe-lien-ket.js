/* Xe liên kết — mỗi dòng một phiếu xe ngoài, đủ phép tính trả chủ xe và lãi EPL. */
(function () {
  const { API, NN, esc, so, tag, AUTH } = EPL;
  let root, ds = [];
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
      <td class="no-print">${p.owner_paid ? tag('paid', 'owner_paid') : (p.locked ? (AUTH.la('cash', 'treasury') && c.tra_chu_xe > 0 ? `<button class="btn sm ok" data-tra="${p.id}">${NN.h('pay_owner')}</button>` : `<span class="small muted">${NN.h('owner_unpaid')}</span>`) : `<span class="small muted">${NN.h('owner_wait_lock')}</span>`)}</td></tr>`; }).join('')
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
  async function tai() { const th = root.querySelector('#xlk-thang').value; ds = await API.get('/api/bao-cao/xe-lien-ket' + (th ? '?thang=' + th : '')); ve(); }
  EPL.modules['xe-lien-ket'] = {
    async init(r) { root = r; r.querySelector('#xlk-thang').addEventListener('change', () => tai().catch(EPL.baoLoi)); await tai(); },
    onLang() { if (root) ve(); },
  };
})();

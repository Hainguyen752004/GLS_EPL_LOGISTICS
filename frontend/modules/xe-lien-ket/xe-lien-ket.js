/* Xe liên kết — mỗi dòng một phiếu xe ngoài, đủ phép tính trả chủ xe và lãi EPL. */
(function () {
  const { API, NN, esc, so, tag, AUTH } = EPL;
  let root, ds = [];
  function ve() {
    let tVal = 0, tThue = 0, tTra = 0, tLai = 0;
    root.querySelector('#xlk-than').innerHTML = ds.length ? ds.map((p, i) => { const c = p.tinh; tVal += c.doanh_thu_usd; tThue += c.tien_thue_usd; tTra += c.tra_chu_xe_usd; tLai += c.lai_usd; return `<tr data-id="${p.id}">
      <td>${i + 1}</td><td>${EPL.ngay(p.doc_date)}</td><td class="mono"><b>${esc(p.doc_no)}</b></td><td lang="lo">${esc(p.owner_name) || '—'}</td><td>${esc(p.truck_no)}</td>
      <td lang="lo" class="small">${esc(p.plate_head)}<br>${esc(p.plate_trailer)}</td><td lang="lo">${esc(p.driver_name) || '—'}</td>
      <td class="num">${so(c.tan_tinh, 2)}</td><td class="num">${so(p.price_usd, 2)}</td><td class="num">${so(c.gia_thue_usd, 2)}</td>
      <td class="num"><b>${so(c.doanh_thu_usd, 2)}</b></td><td class="num">${so(c.tien_thue_usd, 2)}</td><td class="num neg">− ${so(c.phi_usd, 2)}</td><td class="num neg">− ${so(c.tru_vuot_usd, 2)}</td><td class="num neg">− ${so(c.ung_truoc_usd, 2)}</td>
      <td class="num"><b>${so(c.tra_chu_xe_usd, 2)}</b></td><td class="num pos"><b>${so(c.lai_usd, 2)}</b></td><td>${tag(p.transport_status)}</td><td>${tag(p.finance_status)}</td>
      <td class="no-print">${p.owner_paid ? tag('paid', 'owner_paid') : (p.locked ? (AUTH.la('cash', 'treasury') && c.tra_chu_xe_usd > 0 ? `<button class="btn sm ok" data-tra="${p.id}">${NN.h('pay_owner')}</button>` : `<span class="small muted">${NN.h('owner_unpaid')}</span>`) : `<span class="small muted">${NN.h('owner_wait_lock')}</span>`)}</td></tr>`; }).join('')
      : `<tr><td colspan="20" class="empty">${NN.h('no_data')}</td></tr>`;
    root.querySelector('#xlk-chan').innerHTML = `<tr><td colspan="10">${NN.ghep([{ k: 'total' }, ' · ' + ds.length + ' ', { k: 'trips' }])}</td><td class="num">${so(tVal, 2)}</td><td class="num">${so(tThue, 2)}</td><td colspan="3"></td><td class="num">${so(tTra, 2)}</td><td class="num pos">${so(tLai, 2)}</td><td colspan="3"></td></tr>`;
    root.querySelector('#xlk-dem').textContent = `${ds.length} ${NN.t('trips')} · USD`;
    root.querySelectorAll('#xlk-than tr[data-id]').forEach(tr => tr.addEventListener('click', (e) => { if (!e.target.closest('[data-tra]')) EPL.di('phieu-xuat-xe', { id: tr.dataset.id }); }));
    root.querySelectorAll('[data-tra]').forEach(b => b.addEventListener('click', async () => {
      const p = ds.find(x => x.id === b.dataset.tra), c = p.tinh;
      const ok = await EPL.hoi(NN.t('pay_owner'), `<p><b lang="lo">${esc(p.owner_name || '')}</b> · <span class="mono">${esc(p.doc_no)}</span></p><p class="hi">${so(c.tra_chu_xe_usd, 2)} USD</p>
        <p class="small muted">${so(c.tien_thue_usd, 2)} − ${so(c.phi_usd, 2)} − ${so(c.tru_vuot_usd, 2)} − ${so(c.ung_truoc_usd, 2)} USD</p>`, NN.t('pay_owner'));
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

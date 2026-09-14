/* Xe liên kết — mỗi dòng một phiếu xe ngoài, đủ phép tính trả chủ xe và lãi EPL. */
(function () {
  const { API, NN, esc, so, tag } = EPL;
  let root, ds = [];
  function ve() {
    let tVal = 0, tThue = 0, tTra = 0, tLai = 0;
    root.querySelector('#xlk-than').innerHTML = ds.length ? ds.map((p, i) => { const c = p.tinh; tVal += c.doanh_thu_usd; tThue += c.tien_thue_usd; tTra += c.tra_chu_xe_usd; tLai += c.lai_usd; return `<tr data-id="${p.id}">
      <td>${i + 1}</td><td>${EPL.ngay(p.doc_date)}</td><td class="mono"><b>${esc(p.doc_no)}</b></td><td lang="lo">${esc(p.owner_name) || '—'}</td><td>${esc(p.truck_no)}</td>
      <td lang="lo" class="small">${esc(p.plate_head)}<br>${esc(p.plate_trailer)}</td><td lang="lo">${esc(p.driver_name) || '—'}</td>
      <td class="num">${so(c.tan_tinh, 2)}</td><td class="num">${so(p.price_usd, 2)}</td><td class="num">${so(c.gia_thue_usd, 2)}</td>
      <td class="num"><b>${so(c.doanh_thu_usd, 2)}</b></td><td class="num">${so(c.tien_thue_usd, 2)}</td><td class="num neg">− ${so(c.phi_usd, 2)}</td><td class="num neg">− ${so(c.tru_vuot_usd, 2)}</td><td class="num neg">− ${so(c.ung_truoc_usd, 2)}</td>
      <td class="num"><b>${so(c.tra_chu_xe_usd, 2)}</b></td><td class="num pos"><b>${so(c.lai_usd, 2)}</b></td><td>${tag(p.transport_status)}</td><td>${tag(p.finance_status)}</td></tr>`; }).join('')
      : `<tr><td colspan="19" class="empty">${NN.h('no_data')}</td></tr>`;
    root.querySelector('#xlk-chan').innerHTML = `<tr><td colspan="10">${NN.h('total')} · ${ds.length} ${NN.h('trips')}</td><td class="num">${so(tVal, 2)}</td><td class="num">${so(tThue, 2)}</td><td colspan="3"></td><td class="num">${so(tTra, 2)}</td><td class="num pos">${so(tLai, 2)}</td><td colspan="2"></td></tr>`;
    root.querySelector('#xlk-dem').textContent = `${ds.length} ${NN.t('trips')} · USD`;
    root.querySelectorAll('#xlk-than tr[data-id]').forEach(tr => tr.addEventListener('click', () => EPL.di('phieu-xuat-xe', { id: tr.dataset.id })));
  }
  async function tai() { const th = root.querySelector('#xlk-thang').value; ds = await API.get('/api/bao-cao/xe-lien-ket' + (th ? '?thang=' + th : '')); ve(); }
  EPL.modules['xe-lien-ket'] = {
    async init(r) { root = r; r.querySelector('#xlk-thang').addEventListener('change', () => tai().catch(EPL.baoLoi)); await tai(); },
    onLang() { if (root) ve(); },
  };
})();

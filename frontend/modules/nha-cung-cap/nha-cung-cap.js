/* Nhà cung cấp — công nợ = phát sinh trên phiếu − đã trả; ghi lần trả tại đây. */
(function () {
  const { API, NN, esc, so, AUTH } = EPL;
  let root, ds = [], KH = [], canTru = null;
  const xemCanTru = () => AUTH.la('acct', 'expacct', 'rev', 'treasury', 'cash');
  const KHOAN = ['x_chip_lao', 'x_chip_vn', 'x_tire', 'x_toll', 'x_bridge', 'x_border', 'x_parking', 'x_oil', 'x_brake', 'x_tow', 'x_air', 'x_misc'];
  const TK = ['625/4021', '614/4021', '614/1371', '625/1371'];
  const HAN = ['t_monthly', 't_prepaid', 'pm_on_dispatch'];

  function ve() {
    let tPS = 0, tDT = 0, tCN = 0;
    root.querySelector('#ncc-than').innerHTML = ds.length ? ds.map(s => { tPS += s.phat_sinh_lak; tDT += s.da_tra_lak; tCN += s.con_no_lak; return `<tr>
      <td lang="lo"><b>${esc(s.name)}</b></td><td>${s.item_key ? NN.h(s.item_key) : '—'}</td><td><span class="acct">${esc(s.acct_code) || '—'}</span></td>
      <td class="num">${s.so_dong}</td><td class="num">${so(s.phat_sinh_lak)}</td>
      <td class="num">${s.ghi_no_lak ? so(s.ghi_no_lak) : '—'}</td>
      <td class="tien" lang="lo">${esc(s.customer_name || '') || '—'}</td><td class="num">${so(s.da_tra_lak)}</td><td class="num ${s.con_no_lak > 0 ? 'ncc-no' : ''}">${so(s.con_no_lak)}</td>
      <td>${NN.h(s.payment_term || 't_monthly')}</td>
      <td class="no-print"><button class="btn sm" data-ls="${s.id}">${NN.h('payments')}</button>
        ${AUTH.la('expacct', 'cash', 'treasury') ? `<button class="btn sm ok" data-tra="${s.id}">${NN.h('pay_supplier')}</button>` : ''}
        ${AUTH.la('expacct') ? `<button class="btn sm" data-sua="${s.id}">${NN.h('edit')}</button>` : ''}</td></tr>`; }).join('')
      : `<tr><td colspan="11" class="empty">${NN.h('no_data')}</td></tr>`;
    root.querySelector('#ncc-chan').innerHTML = `<tr><td colspan="4">${NN.h('total')}</td><td class="num">${so(tPS)}</td><td colspan="2"></td><td class="num">${so(tDT)}</td><td class="num ${tCN > 0 ? 'ncc-no' : ''}">${so(tCN)}</td><td colspan="2"></td></tr>`;
    root.querySelectorAll('[data-ls]').forEach(b => b.addEventListener('click', () => lichSu(ds.find(x => x.id === b.dataset.ls))));
    root.querySelectorAll('[data-tra]').forEach(b => b.addEventListener('click', () => tra(ds.find(x => x.id === b.dataset.tra))));
    root.querySelectorAll('[data-sua]').forEach(b => b.addEventListener('click', () => sua(ds.find(x => x.id === b.dataset.sua))));
  }
  async function lichSu(s) {
    const ls = await API.get(`/api/suppliers/${s.id}/payments`);
    root.querySelector('#ncc-ls-ten').textContent = s.name;
    root.querySelector('#ncc-ls-than').innerHTML = ls.length ? ls.map(x => `<tr><td>${EPL.ngay(x.pay_date)}</td><td class="num">${so(x.amount_lak)}</td><td>${esc(x.note) || ''}</td><td lang="lo">${esc(x.by_user) || ''}</td></tr>`).join('') : `<tr><td colspan="4" class="empty">${NN.h('no_data')}</td></tr>`;
    root.querySelector('#ncc-lich-su').hidden = false;
  }
  async function tra(s) {
    const v = await EPL.hopNhap(NN.t('pay_supplier') + ' — ' + s.name, [
      { id: 'pay_date', label: 'pay_date', type: 'date', value: EPL.homNay() },
      { id: 'amount_lak', label: 'amount_lak', type: 'number', value: s.con_no_lak > 0 ? s.con_no_lak : '' },
      { id: 'note', label: 'note', value: '' },
    ], NN.t('save'));
    if (!v) return;
    try { await API.post(`/api/suppliers/${s.id}/payments`, v); EPL.toast(NN.t('saved'), 'ok'); await tai(); } catch (e) { EPL.baoLoi(e); }
  }
  async function sua(s) {
    const v = await EPL.hopNhap(s ? NN.t('edit') : NN.t('add'), [
      { id: 'name', label: 'supplier', value: s ? s.name : '', lo: true },
      { id: 'item_key', label: 'service', type: 'select', value: s ? s.item_key : 'x_chip_lao', options: KHOAN.map(k => [k, NN.t(k)]) },
      { id: 'acct_code', label: 'acct_code', type: 'select', value: s ? s.acct_code : '625/4021', options: TK.map(k => [k, k]) },
      { id: 'payment_term', label: 'terms', type: 'select', value: s ? s.payment_term : 't_monthly', options: HAN.map(k => [k, NN.t(k)]) },
      // Trạm dầu bên Việt Nam ghi nợ: cuối tháng trừ vào cước của khách nào (C5.1).
      { id: 'customer_id', label: 'ncc_can_tru_kh', type: 'select', value: s ? (s.customer_id || '') : '',
        options: [['', '—']].concat(KH.map(k => [k.id, k.name])) },
      { id: 'note', label: 'note', value: s ? s.note : '' },
    ], NN.t('save'));
    if (!v) return;
    if (!v.name.trim()) return EPL.toast(NN.t('supplier') + '?', 'loi');
    const than = { ...v, customer_id: v.customer_id || null };
    try { await (s ? API.put('/api/suppliers/' + s.id, than) : API.post('/api/suppliers', than)); EPL.toast(NN.t('saved'), 'ok'); await tai(); } catch (e) { EPL.baoLoi(e); }
  }
  /* Cấn trừ cuối tháng: khách trả hộ qua thẻ cao tốc và qua trạm dầu VN, trừ vào cước của họ. */
  function veCanTru() {
    const card = root.querySelector('#ncc-can-tru-card');
    card.hidden = !xemCanTru();
    if (!xemCanTru() || !canTru) return;
    const rows = canTru.ds || [];
    root.querySelector('#ncc-can-tru').innerHTML = rows.length ? rows.map(o => `<tr>
      <td lang="lo"><b>${esc(o.customer_name)}</b></td>
      <td class="num">${so(o.cuoc_lak)}</td>
      <td class="num">${o.the_lak ? so(o.the_lak) : '—'}</td>
      <td class="num">${o.dau_vn_lak ? so(o.dau_vn_lak) : '—'}</td>
      <td class="num"><b>${so(o.can_tru_lak)}</b></td>
      <td class="num ${o.con_thu_lak > 0 ? 'ncc-no' : ''}">${so(o.con_thu_lak)}</td>
      <td class="small muted">${[...o.the.map(t => t.card_no), ...o.tram.map(t => t.name)].map(esc).join(' · ')}</td></tr>`).join('')
      : `<tr><td colspan="7" class="empty">${NN.h('ncc_can_tru_trong')}</td></tr>`;
    root.querySelector('#ncc-can-tru-chan').innerHTML = rows.length ? `<tr><td>${NN.h('total')}</td>
      <td class="num">${so(canTru.tong_cuoc_lak)}</td><td colspan="2"></td>
      <td class="num"><b>${so(canTru.tong_can_tru_lak)}</b></td>
      <td class="num">${so(canTru.tong_con_thu_lak)}</td><td></td></tr>` : '';
  }

  async function tai() {
    ds = await API.get('/api/suppliers');
    if (xemCanTru()) {
      const thang = root.querySelector('#ncc-thang').value;
      try { canTru = await API.get('/api/bao-cao/can-tru' + (thang ? '?thang=' + thang : '')); } catch (e) { canTru = null; }
    }
    ve(); veCanTru();
  }
  EPL.modules['nha-cung-cap'] = {
    async init(r) {
      root = r; const t = r.querySelector('#ncc-them'); t.hidden = !AUTH.la('expacct'); t.addEventListener('click', () => sua(null));
      r.querySelector('#ncc-thang').value = new Date().toISOString().slice(0, 7);
      r.querySelector('#ncc-thang').addEventListener('change', () => tai().catch(EPL.baoLoi));
      try { KH = await API.get('/api/customers'); } catch (e) { KH = []; }
      r.querySelector('#ncc-ls-dong').addEventListener('click', () => { r.querySelector('#ncc-lich-su').hidden = true; });
      await tai();
    },
    onLang() { if (root) { ve(); veCanTru(); } },
  };
})();

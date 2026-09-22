/* Nhà cung cấp — công nợ = phát sinh trên phiếu − đã trả; ghi lần trả tại đây. */
(function () {
  const { API, NN, esc, so, AUTH } = EPL;
  let root, ds = [];
  const KHOAN = ['x_chip_lao', 'x_chip_vn', 'x_tire', 'x_toll', 'x_bridge', 'x_border', 'x_parking', 'x_oil', 'x_brake', 'x_tow', 'x_air', 'x_misc'];
  const TK = ['625/4021', '614/4021', '614/1371', '625/1371'];
  const HAN = ['t_monthly', 't_prepaid', 'pm_on_dispatch'];

  function ve() {
    let tPS = 0, tDT = 0, tCN = 0;
    root.querySelector('#ncc-than').innerHTML = ds.length ? ds.map(s => { tPS += s.phat_sinh_lak; tDT += s.da_tra_lak; tCN += s.con_no_lak; return `<tr>
      <td lang="lo"><b>${esc(s.name)}</b></td><td>${s.item_key ? NN.h(s.item_key) : '—'}</td><td><span class="acct">${esc(s.acct_code) || '—'}</span></td>
      <td class="num">${s.so_dong}</td><td class="num">${so(s.phat_sinh_lak)}</td><td class="num">${so(s.da_tra_lak)}</td><td class="num ${s.con_no_lak > 0 ? 'ncc-no' : ''}">${so(s.con_no_lak)}</td>
      <td>${NN.h(s.payment_term || 't_monthly')}</td>
      <td class="no-print"><button class="btn sm" data-ls="${s.id}">${NN.h('payments')}</button>
        ${AUTH.la('expacct', 'cash', 'treasury') ? `<button class="btn sm ok" data-tra="${s.id}">${NN.h('pay_supplier')}</button>` : ''}
        ${AUTH.la('expacct') ? `<button class="btn sm" data-sua="${s.id}">${NN.h('edit')}</button>` : ''}</td></tr>`; }).join('')
      : `<tr><td colspan="9" class="empty">${NN.h('no_data')}</td></tr>`;
    root.querySelector('#ncc-chan').innerHTML = `<tr><td colspan="4">${NN.h('total')}</td><td class="num">${so(tPS)}</td><td class="num">${so(tDT)}</td><td class="num ${tCN > 0 ? 'ncc-no' : ''}">${so(tCN)}</td><td colspan="2"></td></tr>`;
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
      { id: 'note', label: 'note', value: s ? s.note : '' },
    ], NN.t('save'));
    if (!v) return;
    if (!v.name.trim()) return EPL.toast(NN.t('supplier') + '?', 'loi');
    try { await (s ? API.put('/api/suppliers/' + s.id, v) : API.post('/api/suppliers', v)); EPL.toast(NN.t('saved'), 'ok'); await tai(); } catch (e) { EPL.baoLoi(e); }
  }
  async function tai() { ds = await API.get('/api/suppliers'); ve(); }
  EPL.modules['nha-cung-cap'] = {
    async init(r) {
      root = r; const t = r.querySelector('#ncc-them'); t.hidden = !AUTH.la('expacct'); t.addEventListener('click', () => sua(null));
      r.querySelector('#ncc-ls-dong').addEventListener('click', () => { r.querySelector('#ncc-lich-su').hidden = true; });
      await tai();
    },
    onLang() { if (root) ve(); },
  };
})();

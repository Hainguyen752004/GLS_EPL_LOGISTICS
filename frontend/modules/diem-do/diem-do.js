/* Điểm đổ nhiên liệu — danh mục quyết định hai việc: phiếu lĩnh chạy tới kho nào, và khoản dầu
   đó là LĨNH KHO hay MUA NGOÀI (kéo theo định khoản …/1371 hay …/4021). */
(function () {
  const { API, NN, esc, so, AUTH } = EPL;
  let root, ds = [], ncc = [];
  const suaDuoc = () => AUTH.la('yard', 'acct', 'fuel');

  function ve() {
    const t = root.querySelector('#dd-q').value.trim().toLowerCase();
    const rows = ds.filter(x => !t || [x.code, x.name, x.address].join(' ').toLowerCase().includes(t));
    root.querySelector('#dd-than').innerHTML = rows.length ? rows.map((x, i) => `<tr class="${x.active ? '' : 'dd-tat'}">
      <td>${i + 1}</td><td class="mono">${esc(x.code) || '—'}</td><td lang="lo"><b>${esc(x.name)}</b>
        ${x.address ? `<div class="small muted" lang="lo">${esc(x.address)}</div>` : ''}</td>
      <td>${NN.h(x.country === 'VN' ? 'fp_vn2' : 'fp_la')}</td>
      <td>${EPL.tag(x.owner_type === 'epl' ? 'ok' : 'plain', x.owner_type === 'epl' ? 'fp_epl' : 'fp_ngoai')}</td>
      <td lang="lo">${esc(x.supplier_name) || '—'}</td>
      <td class="num">${x.cho_cap ? `<b>${so(x.cho_cap)}</b>` : '—'}</td>
      <td>${EPL.tag(x.active ? 'ok' : 'plain', x.active ? 'active' : 'inactive')}</td>
      <td class="no-print">${suaDuoc() ? `<button class="btn sm" data-sua="${x.id}">${NN.h('edit')}</button>` : ''}</td></tr>`).join('')
      : `<tr><td colspan="9" class="empty">${NN.h('no_data')}</td></tr>`;
    root.querySelectorAll('[data-sua]').forEach(b => b.addEventListener('click', () => sua(ds.find(x => x.id === b.dataset.sua))));
  }

  async function sua(x) {
    const v = await EPL.hopNhap(x ? NN.t('edit') : NN.t('fp_new'), [
      { id: 'code', label: 'doc_no', value: x ? x.code : '' },
      { id: 'name', label: 'name', value: x ? x.name : '', lo: true },
      { id: 'country', label: 'fp_country', type: 'select', value: x ? x.country : 'LA',
        options: [['LA', NN.t('fp_la')], ['VN', NN.t('fp_vn2')]] },
      { id: 'owner_type', label: 'type', type: 'select', value: x ? x.owner_type : 'epl',
        options: [['epl', NN.t('fp_epl')], ['ngoai', NN.t('fp_ngoai')]] },
      { id: 'supplier_id', label: 'nav_supplier', type: 'select', value: x ? (x.supplier_id || '') : '',
        options: [['', '—']].concat(ncc.map(n => [n.id, n.name])) },
      { id: 'address', label: 'address', value: x ? x.address : '', lo: true },
      ...(x ? [{ id: 'active', label: 'status', type: 'select', value: x.active ? '1' : '0',
        options: [['1', NN.t('active')], ['0', NN.t('inactive')]] }] : []),
    ], NN.t('save'));
    if (!v) return;
    if (!v.name.trim()) return EPL.toast(NN.t('name') + '?', 'loi');
    const body = { code: v.code, name: v.name, country: v.country, owner_type: v.owner_type,
      supplier_id: v.supplier_id || null, address: v.address };
    if (x) body.active = v.active === '1';
    try {
      await (x ? API.put('/api/fuel-places/' + x.id, body) : API.post('/api/fuel-places', body));
      EPL.toast(NN.t('saved'), 'ok'); await tai();
    } catch (e) { EPL.baoLoi(e); }
  }

  async function tai() {
    ds = await API.get('/api/fuel-places?tat_ca=1');
    ve();
  }

  EPL.modules['diem-do'] = {
    async init(r) {
      root = r;
      r.querySelector('#dd-q').addEventListener('input', ve);
      const them = r.querySelector('#dd-them'); them.hidden = !suaDuoc();
      them.addEventListener('click', () => sua(null));
      try { ncc = await API.get('/api/suppliers'); } catch (e) { ncc = []; }
      await tai();
    },
    onLang() { if (root) ve(); },
  };
})();

/* Xe — hai biển số (đầu kéo + rơ-moóc), số hiệu nội bộ, xe công ty hay xe liên kết. */
(function () {
  const { API, NN, esc, AUTH } = EPL;
  let root, ds = [];
  const suaDuoc = () => AUTH.la('yard', 'acct');

  function ve() {
    const q = root.querySelector('#xe-q').value.trim().toLowerCase(), loai = root.querySelector('#xe-loai').value;
    const rows = ds.filter(x => (!loai || x.owner_type === loai) && (!q || [x.truck_no, x.brand_model, x.plate_head, x.plate_trailer, x.owner_name].join(' ').toLowerCase().includes(q)));
    root.querySelector('#xe-than').innerHTML = rows.length ? rows.map((x, i) => `<tr class="${x.active ? '' : 'xe-tat'}">
      <td>${i + 1}</td><td><b>${esc(x.truck_no)}</b></td><td>${esc(x.brand_model) || '—'}</td>
      <td class="xe-bien">${esc(x.plate_head) || '—'}</td><td class="xe-bien">${esc(x.plate_trailer) || '—'}</td>
      <td>${x.owner_type === 'joint' ? EPL.tag('plain', 'co_joint') : EPL.tag('ok', 'co_epl')}</td><td lang="lo">${esc(x.owner_name) || '—'}</td>
      <td class="small muted">${esc(x.note) || ''}</td><td>${EPL.tag(x.active ? 'ok' : 'plain', x.active ? 'active' : 'inactive')}</td>
      <td class="no-print">${suaDuoc() ? `<button class="btn sm" data-sua="${x.id}">${NN.h('edit')}</button>` : ''}</td></tr>`).join('')
      : `<tr><td colspan="10" class="empty">${NN.h('no_data')}</td></tr>`;
    root.querySelectorAll('[data-sua]').forEach(b => b.addEventListener('click', () => sua(ds.find(y => y.id === b.dataset.sua))));
  }
  async function sua(x) {
    const v = await EPL.hopNhap(x ? NN.t('edit') : NN.t('add'), [
      { id: 'truck_no', label: 'truck_no', value: x ? x.truck_no : '' },
      { id: 'brand_model', label: 'brand_model', value: x ? x.brand_model : '' },
      { id: 'plate_head', label: 'plate_head', value: x ? x.plate_head : '', lo: true },
      { id: 'plate_trailer', label: 'plate_trailer', value: x ? x.plate_trailer : '', lo: true },
      { id: 'owner_type', label: 'owner_type', type: 'select', value: x ? x.owner_type : 'EPL', options: [['EPL', NN.t('co_epl')], ['joint', NN.t('co_joint')]] },
      { id: 'owner_name', label: 'owner', value: x ? x.owner_name : '', lo: true },
      { id: 'note', label: 'note', type: 'textarea', value: x ? x.note : '' },
      ...(x ? [{ id: 'active', label: 'status', type: 'select', value: x.active ? '1' : '0', options: [['1', NN.t('active')], ['0', NN.t('inactive')]] }] : []),
    ], NN.t('save'));
    if (!v) return;
    if (!v.truck_no.trim()) return EPL.toast(NN.t('truck_no') + '?', 'loi');
    if (v.owner_type === 'joint' && !v.owner_name.trim()) return EPL.toast(NN.t('owner') + '?', 'loi');
    try {
      const body = { truck_no: v.truck_no, brand_model: v.brand_model, plate_head: v.plate_head, plate_trailer: v.plate_trailer,
        owner_type: v.owner_type, owner_name: v.owner_name, note: v.note };
      if (x) body.active = v.active === '1';
      await (x ? API.put('/api/vehicles/' + x.id, body) : API.post('/api/vehicles', body));
      EPL.toast(NN.t('saved'), 'ok'); await tai();
    } catch (e) { EPL.baoLoi(e); }
  }
  async function tai() { ds = await API.get('/api/vehicles'); ve(); }
  EPL.modules['xe'] = {
    async init(r) {
      root = r; ['xe-q', 'xe-loai'].forEach(id => r.querySelector('#' + id).addEventListener('input', ve));
      const them = r.querySelector('#xe-them'); them.hidden = !suaDuoc(); them.addEventListener('click', () => sua(null));
      await tai();
    },
    onLang() { if (root) ve(); },
  };
})();

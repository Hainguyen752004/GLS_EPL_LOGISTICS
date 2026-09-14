/* Tài xế & bằng lái — danh sách, hồ sơ, bằng lái hiện hành + lịch sử gia hạn, phiếu gần đây. */
(function () {
  const { API, NN, esc, so, AUTH, tag } = EPL;
  let root, DS = [], XE = [], chon = null;
  const q = (s) => root.querySelector(s);
  const suaDuoc = () => AUTH.la('yard', 'acct');
  const TT = { available: ['ok', 'd_available'], on_trip: ['transit', 'd_on_trip'], leave: ['partial', 'd_leave'], inactive: ['plain', 'd_inactive'] };
  const ttTag = (d) => { const k = d.active ? d.status : 'inactive'; return tag((TT[k] || TT.inactive)[0], (TT[k] || TT.inactive)[1]); };
  const cham = (k) => `<span class="tx-cham ${k}" title="${esc(NN.t('doc_' + k))}"></span>`;

  function veBang() {
    const s = q('#tx-q').value.trim().toLowerCase(), tt = q('#tx-tt').value;
    const rows = DS.filter(d => (!tt || d.status === tt) && (!s || [d.name, d.phone, d.license_no, d.driver_code].join(' ').toLowerCase().includes(s)));
    q('#tx-than').innerHTML = rows.length ? rows.map((d, i) => `<tr data-id="${d.id}" class="${chon && chon.id === d.id ? 'sel' : ''} ${d.active ? '' : 'tx-tat'}">
      <td>${i + 1}</td><td lang="lo"><b>${esc(d.name)}</b>${d.driver_code ? `<div class="small muted mono">${esc(d.driver_code)}</div>` : ''}</td><td>${esc(d.phone) || '—'}</td>
      <td>${NN.h(d.role === 'co' ? 'role_co' : 'role_main')}</td><td>${esc(d.license_type) || '—'}</td><td class="mono">${esc(d.license_no) || '—'}</td>
      <td>${d.license_valid_to ? cham(d.bang_lai) + EPL.ngay(d.license_valid_to) : `<span class="muted">${NN.h('doc_none')}</span>`}</td>
      <td>${esc(d.default_vehicle) || '—'}</td><td>${ttTag(d)}</td></tr>`).join('') : `<tr><td colspan="9" class="empty">${NN.h('no_data')}</td></tr>`;
    root.querySelectorAll('#tx-than tr[data-id]').forEach(tr => tr.addEventListener('click', () => moHoSo(tr.dataset.id)));
  }
  const dong = (k, v, lo) => `<div><span>${NN.h(k)}</span><b ${lo ? 'lang="lo"' : ''}>${v == null || v === '' ? '—' : v}</b></div>`;
  async function moHoSo(id) {
    chon = await API.get('/api/drivers/' + id); const d = chon;
    const o = q('#tx-ho-so'); o.hidden = false; q('#tx-hs-sua').hidden = !suaDuoc();
    q('#tx-hs-ten').textContent = d.name; q('#tx-hs-tt').innerHTML = ttTag(d);
    const canh = d.bang_lai === 'expired' ? `<div class="tx-canh do">${NN.h('license_valid_to')}: ${NN.h('doc_expired')} (${EPL.ngay(d.license_valid_to)})</div>`
      : d.bang_lai === 'soon' ? `<div class="tx-canh vang">${NN.h('license_valid_to')}: ${NN.h('doc_soon')} (${EPL.ngay(d.license_valid_to)})</div>` : '';
    q('#tx-hs-than').innerHTML = `
      <div class="tx-hs-luoi">${dong('driver_code', esc(d.driver_code))}${dong('driver_role', NN.h(d.role === 'co' ? 'role_co' : 'role_main'))}${dong('phone', esc(d.phone))}${dong('dob', d.dob ? EPL.ngay(d.dob) : null)}
        ${dong('id_card', esc(d.id_card))}${dong('hire_date', d.hire_date ? EPL.ngay(d.hire_date) : null)}${dong('address', esc(d.address), true)}${dong('default_vehicle', esc(d.default_vehicle))}
        ${dong('trips_count', d.so_phieu)}${dong('note', esc(d.note), true)}</div>
      <h5>${NN.h('license')}</h5>
      <div class="tx-bang-lai">${d.license_no ? `<span class="so">${esc(d.license_no)}</span><span>${NN.h('license_type')}: <b>${esc(d.license_type) || '—'}</b></span>
        <span>${cham(d.bang_lai)}${EPL.ngay(d.license_valid_from)} → <b>${EPL.ngay(d.license_valid_to)}</b></span>` : `<span class="muted">${NN.h('doc_none')}</span>`}
        <span class="grow"></span>${suaDuoc() ? `<button class="btn sm" id="tx-them-bl">${NN.h('add_license')}</button>` : ''}</div>
      ${canh}
      <h5>${NN.h('licenses')}</h5>
      <div class="tbl-wrap"><table class="tbl tbl-compact"><thead><tr><th>${NN.h('license_no')}</th><th>${NN.h('license_type')}</th><th>${NN.h('license_valid_from')}</th><th>${NN.h('license_valid_to')}</th><th>${NN.h('issued_by')}</th><th>${NN.h('verified_by')}</th></tr></thead>
        <tbody>${(d.licenses || []).map(l => `<tr><td class="mono">${esc(l.license_no)}</td><td>${esc(l.license_type) || '—'}</td><td>${EPL.ngay(l.valid_from)}</td><td>${EPL.ngay(l.valid_to)}</td><td lang="lo">${esc(l.issued_by) || '—'}</td><td lang="lo">${esc(l.verified_by) || '—'}</td></tr>`).join('') || `<tr><td colspan="6" class="empty">${NN.h('no_data')}</td></tr>`}</tbody></table></div>
      <h5>${NN.h('recent_trips')}</h5>
      <div class="tbl-wrap"><table class="tbl tbl-compact"><thead><tr><th>${NN.h('doc_no')}</th><th>${NN.h('c_date')}</th><th>${NN.h('truck_no')}</th><th>${NN.h('route')}</th><th>${NN.h('c_st_t')}</th></tr></thead>
        <tbody>${(d.phieu_gan_day || []).map(p => `<tr data-phieu="${p.id}" style="cursor:pointer"><td class="mono">${esc(p.doc_no)}</td><td>${EPL.ngay(p.doc_date)}</td><td>${esc(p.truck_no)}</td><td lang="lo">${esc(p.origin)} → ${esc(p.destination)}</td><td>${tag(p.transport_status)}</td></tr>`).join('') || `<tr><td colspan="5" class="empty">${NN.h('no_data')}</td></tr>`}</tbody></table></div>`;
    const bl = q('#tx-them-bl'); if (bl) bl.addEventListener('click', () => themBangLai(d));
    root.querySelectorAll('[data-phieu]').forEach(tr => tr.addEventListener('click', () => EPL.di('phieu-xuat-xe', { id: tr.dataset.phieu })));
    veBang();
  }
  async function themBangLai(d) {
    const v = await EPL.hopNhap(NN.t('add_license') + ' — ' + d.name, [
      { id: 'license_no', label: 'license_no', value: '' }, { id: 'license_type', label: 'license_type', value: d.license_type || 'C' },
      { id: 'valid_from', label: 'license_valid_from', type: 'date', value: EPL.homNay() }, { id: 'valid_to', label: 'license_valid_to', type: 'date', value: '' },
      { id: 'issued_by', label: 'issued_by', value: '', lo: true }, { id: 'note', label: 'note', value: '' }], NN.t('save'));
    if (!v) return;
    try { await API.post(`/api/drivers/${d.id}/licenses`, v); EPL.toast(NN.t('saved'), 'ok'); await tai(); await moHoSo(d.id); } catch (e) { EPL.baoLoi(e); }
  }
  async function sua(d) {
    const v = await EPL.hopNhap(d ? NN.t('edit') + ' — ' + d.name : NN.t('add'), [
      { id: 'driver_code', label: 'driver_code', value: d ? d.driver_code : '' }, { id: 'name', label: 'name', value: d ? d.name : '', lo: true },
      { id: 'phone', label: 'phone', value: d ? d.phone : '' }, { id: 'dob', label: 'dob', type: 'date', value: d ? d.dob : '' },
      { id: 'id_card', label: 'id_card', value: d ? d.id_card : '' }, { id: 'address', label: 'address', value: d ? d.address : '', lo: true },
      { id: 'role', label: 'driver_role', type: 'select', value: d ? d.role : 'main', options: [['main', NN.t('role_main')], ['co', NN.t('role_co')]] },
      { id: 'hire_date', label: 'hire_date', type: 'date', value: d ? d.hire_date : '' },
      ...(d ? [] : [{ id: 'license_no', label: 'license_no', value: '' }, { id: 'license_type', label: 'license_type', value: 'C' },
        { id: 'license_valid_from', label: 'license_valid_from', type: 'date', value: '' }, { id: 'license_valid_to', label: 'license_valid_to', type: 'date', value: '' }]),
      { id: 'default_vehicle_id', label: 'default_vehicle', type: 'select', value: d ? d.default_vehicle_id || '' : '', options: [['', '—'], ...XE.map(x => [x.id, x.truck_no + ' · ' + (x.plate_head || '')])] },
      { id: 'status', label: 'status', type: 'select', value: d ? d.status : 'available', options: Object.keys(TT).map(k => [k, NN.t(TT[k][1])]) },
      { id: 'note', label: 'note', type: 'textarea', value: d ? d.note : '' },
      ...(d ? [{ id: 'active', label: 'active', type: 'select', value: d.active ? '1' : '0', options: [['1', NN.t('active')], ['0', NN.t('inactive')]] }] : []),
    ], NN.t('save'));
    if (!v) return;
    if (!v.name.trim()) return EPL.toast(NN.t('name') + '?', 'loi');
    if (d) v.active = v.active === '1';
    if (!v.default_vehicle_id) v.default_vehicle_id = null;
    try { const r = await (d ? API.put('/api/drivers/' + d.id, v) : API.post('/api/drivers', v)); EPL.toast(NN.t('saved'), 'ok'); await tai(); await moHoSo(r.id); } catch (e) { EPL.baoLoi(e); }
  }
  async function tai() { [DS, XE] = await Promise.all([API.get('/api/drivers'), API.get('/api/vehicles')]); veBang(); }
  EPL.modules['tai-xe'] = {
    async init(r) {
      root = r; chon = null;
      ['tx-q', 'tx-tt'].forEach(id => q('#' + id).addEventListener('input', veBang));
      const them = q('#tx-them'); them.hidden = !suaDuoc(); them.addEventListener('click', () => sua(null));
      q('#tx-hs-sua').addEventListener('click', () => chon && sua(chon));
      await tai(); if (DS.length) await moHoSo(DS[0].id);
    },
    onLang() { if (root) { veBang(); if (chon) moHoSo(chon.id); } },
  };
})();

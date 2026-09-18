/* Xe — đầu kéo (hồ sơ, giấy tờ, sửa chữa) và rơ-moóc (lắp/tháo giữa các đầu kéo, có lịch sử). */
(function () {
  const { API, NN, esc, so, AUTH, tag } = EPL;
  let root, tab = 'tractor', XE = [], RM = [], chon = null;
  const q = (s) => root.querySelector(s);
  const suaDuoc = () => AUTH.la('yard', 'acct');
  const TT_XE = { available: 'v_available', on_trip: 'v_on_trip', maintenance: 'v_maintenance', inactive: 'v_inactive', attached: 'v_attached' };
  const MAU_TT = { available: 'ok', on_trip: 'transit', maintenance: 'unpaid', inactive: 'plain', attached: 'dispatched' };
  const cham = (k) => `<span class="xe-cham ${k}" title="${esc(NN.t('doc_' + k))}"></span>`;
  const gt = (g) => `<span class="xe-gt">${Object.values(g).map(cham).join('')}</span>`;

  /* ------------------------------------------------ danh sách */
  function veBang() {
    const s = q('#xe-q').value.trim().toLowerCase(), loai = q('#xe-loai').value;
    if (tab === 'tractor') {
      q('#xe-dau').innerHTML = `<tr><th>#</th><th>${NN.h('truck_no')}</th><th>${NN.h('brand_model')}</th><th>${NN.h('plate_head')}</th><th>${NN.h('plate_trailer')}</th><th>${NN.h('owner_type')}</th><th class="num">${NN.h('odometer_km')}</th><th>${NN.h('docs_status')}</th><th>${NN.h('status')}</th></tr>`;
      const rows = XE.filter(x => (!loai || x.owner_type === loai) && (!s || [x.truck_no, x.brand_model, x.plate_head, x.plate_trailer, x.owner_name].join(' ').toLowerCase().includes(s)));
      q('#xe-than').innerHTML = rows.length ? rows.map((x, i) => `<tr data-id="${x.id}" class="${chon && chon.id === x.id ? 'sel' : ''} ${x.active ? '' : 'xe-tat'}">
        <td>${i + 1}</td><td><b>${esc(x.truck_no)}</b></td><td>${esc(x.brand_model) || '—'}</td><td class="xe-bien">${esc(x.plate_head) || '—'}</td>
        <td class="xe-bien">${esc(x.plate_trailer) || `<span class="muted">${NN.h('not_attached')}</span>`}</td>
        <td>${x.owner_type === 'joint' ? tag('plain', 'co_joint') : tag('ok', 'co_epl')}</td><td class="num">${x.odometer_km ? so(x.odometer_km) : '—'}</td>
        <td>${gt(x.giay_to)}${x.can_bao_duong ? ' <span class="tag unpaid">' + NN.h('service_due') + '</span>' : ''}</td>
        <td>${tag(MAU_TT[x.active ? x.status : 'inactive'], TT_XE[x.active ? x.status : 'inactive'])}</td></tr>`).join('') : `<tr><td colspan="9" class="empty">${NN.h('no_data')}</td></tr>`;
    } else {
      q('#xe-dau').innerHTML = `<tr><th>#</th><th>${NN.h('plate')}</th><th>${NN.h('trailer_type')}</th><th class="num">${NN.h('capacity_t')}</th><th>${NN.h('owner_type')}</th><th>${NN.h('attached_to')}</th><th>${NN.h('docs_status')}</th><th>${NN.h('status')}</th></tr>`;
      const rows = RM.filter(t => (!loai || t.owner_type === loai) && (!s || [t.plate, t.trailer_type, t.owner_name].join(' ').toLowerCase().includes(s)));
      q('#xe-than').innerHTML = rows.length ? rows.map((t, i) => `<tr data-id="${t.id}" class="${chon && chon.id === t.id ? 'sel' : ''} ${t.active ? '' : 'xe-tat'}">
        <td>${i + 1}</td><td class="xe-bien">${esc(t.plate)}</td><td lang="lo">${esc(t.trailer_type) || '—'}</td><td class="num">${t.capacity_t ? so(t.capacity_t) : '—'}</td>
        <td>${t.owner_type === 'joint' ? tag('plain', 'co_joint') : tag('ok', 'co_epl')}</td>
        <td>${t.dang_lap_xe ? `<b>${esc(t.dang_lap_xe.truck_no)}</b> · <span class="xe-bien">${esc(t.dang_lap_xe.plate_head)}</span>` : `<span class="muted">${NN.h('not_attached')}</span>`}</td>
        <td>${gt(t.giay_to)}</td><td>${tag(MAU_TT[t.active ? t.status : 'inactive'], TT_XE[t.active ? t.status : 'inactive'])}</td></tr>`).join('') : `<tr><td colspan="8" class="empty">${NN.h('no_data')}</td></tr>`;
    }
    root.querySelectorAll('#xe-than tr[data-id]').forEach(tr => tr.addEventListener('click', () => moHoSo(tr.dataset.id)));
  }

  /* ------------------------------------------------ hồ sơ */
  const dong = (k, v, lo) => `<div><span>${NN.h(k)}</span><b ${lo ? 'lang="lo"' : ''}>${v == null || v === '' ? '—' : v}</b></div>`;
  const han = (ngay, k) => ngay ? `${EPL.ngay(ngay)} ${cham(k)}` : `<span class="muted">${NN.h('doc_none')}</span>`;
  async function moHoSo(id) {
    const o = q('#xe-ho-so'); o.hidden = false; q('#xe-hs-sua').hidden = !suaDuoc();
    if (tab === 'tractor') {
      chon = await API.get('/api/vehicles/' + id); const x = chon;
      q('#xe-hs-ten').innerHTML = `${esc(x.truck_no)} · <span class="xe-bien">${esc(x.plate_head || '')}</span>`;
      q('#xe-hs-tt').innerHTML = tag(MAU_TT[x.active ? x.status : 'inactive'], TT_XE[x.active ? x.status : 'inactive']);
      const canh = [];
      Object.entries(x.giay_to).forEach(([k, v]) => { if (v === 'expired') canh.push(`<div class="xe-canh">${NN.h(k === 'insurance' ? 'insurance_exp' : k === 'inspection' ? 'inspection_exp' : 'road_permit_exp')}: ${NN.h('doc_expired')}</div>`); else if (v === 'soon') canh.push(`<div class="xe-canh vang">${NN.h(k === 'insurance' ? 'insurance_exp' : k === 'inspection' ? 'inspection_exp' : 'road_permit_exp')}: ${NN.h('doc_soon')}</div>`); });
      if (x.can_bao_duong) canh.push(`<div class="xe-canh vang">${NN.h('service_due')}: ${so(x.odometer_km)} / ${so(x.next_service_km)} km</div>`);
      q('#xe-hs-than').innerHTML = `
        <div class="xe-hs-luoi">${dong('brand_model', esc(x.brand_model))}${dong('year', x.year)}${dong('owner_type', x.owner_type === 'joint' ? NN.h('co_joint') : NN.h('co_epl'))}${dong('owner', esc(x.owner_name), true)}
          ${dong('engine_no', esc(x.engine_no))}${dong('chassis_no', esc(x.chassis_no))}${dong('depot', esc(x.depot), true)}${dong('trips_count', x.so_phieu)}
          ${dong('odometer_km', x.odometer_km ? so(x.odometer_km) : null)}${dong('next_service_km', x.next_service_km ? so(x.next_service_km) : null)}
          ${dong('insurance_exp', han(x.insurance_exp, x.giay_to.insurance))}${dong('inspection_exp', han(x.inspection_exp, x.giay_to.inspection))}${dong('road_permit_exp', han(x.road_permit_exp, x.giay_to.road_permit))}${dong('note', esc(x.note), true)}</div>
        ${canh.join('')}
        <h5>${NN.h('trailer')}</h5>
        <div class="xe-rm">${x.trailer ? `<span class="xe-bien bien">${esc(x.trailer.plate)}</span><span class="small muted" lang="lo">${esc(x.trailer.trailer_type || '')} · ${x.trailer.capacity_t ? so(x.trailer.capacity_t) + ' t' : ''}</span>` : `<span class="muted">${NN.h('not_attached')}</span>`}
          <span class="grow"></span>${suaDuoc() ? `<button class="btn sm" id="xe-lap">${NN.h('attach_trailer')}</button>${x.trailer ? `<button class="btn sm warn" id="xe-thao">${NN.h('detach_trailer')}</button>` : ''}` : ''}</div>
        <h5>${NN.h('trailer_history')}</h5>
        <div class="tbl-wrap"><table class="tbl tbl-compact"><thead><tr><th>${NN.h('plate')}</th><th>${NN.h('attached_at')}</th><th>${NN.h('detached_at')}</th><th>${NN.h('swap_reason')}</th></tr></thead>
          <tbody>${(x.lich_su_ro_mooc || []).map(a => `<tr><td class="xe-bien">${esc(a.plate)}</td><td>${EPL.ngayGio(a.attached_at)}</td><td>${a.detached_at ? EPL.ngayGio(a.detached_at) : '<span class="tag ok">' + NN.h('v_attached') + '</span>'}</td><td>${esc(a.reason) || ''}</td></tr>`).join('') || `<tr><td colspan="4" class="empty">${NN.h('no_data')}</td></tr>`}</tbody></table></div>
        <h5>${NN.h('repairs_of_vehicle')}</h5>
        <div class="tbl-wrap"><table class="tbl tbl-compact"><thead><tr><th>${NN.h('doc_no')}</th><th>${NN.h('item')}</th><th>${NN.h('source')}</th><th class="num tien">${NN.h('amount_lak')}</th><th class="tien">${NN.h('acct_code')}</th></tr></thead>
          <tbody>${(x.sua_chua || []).map(s => `<tr><td class="mono">${esc(s.doc_no)}</td><td lang="lo">${esc(s.item_key ? NN.t(s.item_key) : s.item_name)}</td><td>${s.source ? NN.h('src_' + s.source) : '—'}</td><td class="num tien">${so(s.tien_lak)}</td><td class="tien"><span class="acct">${esc(s.acct_code || '')}</span></td></tr>`).join('') || `<tr><td colspan="5" class="empty">${NN.h('no_data')}</td></tr>`}</tbody></table></div>`;
      const lap = q('#xe-lap'), thao = q('#xe-thao');
      if (lap) lap.addEventListener('click', () => lapRoMooc(x));
      if (thao) thao.addEventListener('click', () => thaoRoMooc(x));
    } else {
      chon = RM.find(t => t.id === id); const t = chon;
      q('#xe-hs-ten').innerHTML = `<span class="xe-bien">${esc(t.plate)}</span>`;
      q('#xe-hs-tt').innerHTML = tag(MAU_TT[t.active ? t.status : 'inactive'], TT_XE[t.active ? t.status : 'inactive']);
      q('#xe-hs-than').innerHTML = `<div class="xe-hs-luoi">${dong('trailer_type', esc(t.trailer_type), true)}${dong('capacity_t', t.capacity_t ? so(t.capacity_t) : null)}${dong('year', t.year)}
        ${dong('owner_type', t.owner_type === 'joint' ? NN.h('co_joint') : NN.h('co_epl'))}${dong('owner', esc(t.owner_name), true)}
        ${dong('attached_to', t.dang_lap_xe ? `${esc(t.dang_lap_xe.truck_no)} · ${esc(t.dang_lap_xe.plate_head)}` : `<span class="muted">${NN.h('not_attached')}</span>`)}
        ${dong('insurance_exp', han(t.insurance_exp, t.giay_to.insurance))}${dong('inspection_exp', han(t.inspection_exp, t.giay_to.inspection))}${dong('note', esc(t.note), true)}</div>`;
    }
    veBang();
  }

  /* ------------------------------------------------ lắp / tháo rơ-moóc */
  async function lapRoMooc(x) {
    const ranh = RM.filter(t => t.active && t.status !== 'maintenance' && t.id !== x.trailer_id);
    if (!ranh.length) return EPL.toast(NN.t('no_data'), 'loi');
    const v = await EPL.hopNhap(NN.t('attach_trailer') + ' → ' + x.truck_no, [
      { id: 'trailer_id', label: 'trailer', type: 'select', value: ranh[0].id, options: ranh.map(t => [t.id, t.plate + (t.dang_lap_xe ? ' (' + NN.t('attached_to') + ' ' + t.dang_lap_xe.truck_no + ')' : '') + (t.trailer_type ? ' · ' + t.trailer_type : '')]) },
      { id: 'reason', label: 'swap_reason', value: '' }], NN.t('attach_trailer'));
    if (!v) return;
    try { await API.post(`/api/vehicles/${x.id}/trailer`, v); EPL.toast(NN.t('saved'), 'ok'); await tai(); await moHoSo(x.id); } catch (e) { EPL.baoLoi(e); }
  }
  async function thaoRoMooc(x) {
    const v = await EPL.hopNhap(NN.t('detach_trailer') + ' — ' + (x.trailer ? x.trailer.plate : ''), [{ id: 'reason', label: 'swap_reason', value: '' }], NN.t('detach_trailer'));
    if (!v) return;
    try { await API.post(`/api/vehicles/${x.id}/trailer`, { trailer_id: '', reason: v.reason }); EPL.toast(NN.t('saved'), 'ok'); await tai(); await moHoSo(x.id); } catch (e) { EPL.baoLoi(e); }
  }

  /* ------------------------------------------------ thêm / sửa */
  const TT_OPT = (ds) => ds.map(k => [k, NN.t(TT_XE[k])]);
  async function suaXe(x) {
    const v = await EPL.hopNhap(x ? NN.t('edit') + ' — ' + x.truck_no : NN.t('add') + ' ' + NN.t('tractors'), [
      { id: 'truck_no', label: 'truck_no', value: x ? x.truck_no : '' }, { id: 'brand_model', label: 'brand_model', value: x ? x.brand_model : '' },
      { id: 'year', label: 'year', type: 'number', value: x ? x.year : '' }, { id: 'plate_head', label: 'plate_head', value: x ? x.plate_head : '', lo: true },
      { id: 'owner_type', label: 'owner_type', type: 'select', value: x ? x.owner_type : 'EPL', options: [['EPL', NN.t('co_epl')], ['joint', NN.t('co_joint')]] },
      { id: 'owner_name', label: 'owner', value: x ? x.owner_name : '', lo: true },
      { id: 'engine_no', label: 'engine_no', value: x ? x.engine_no : '' }, { id: 'chassis_no', label: 'chassis_no', value: x ? x.chassis_no : '' },
      { id: 'insurance_exp', label: 'insurance_exp', type: 'date', value: x ? x.insurance_exp : '' }, { id: 'inspection_exp', label: 'inspection_exp', type: 'date', value: x ? x.inspection_exp : '' },
      { id: 'road_permit_exp', label: 'road_permit_exp', type: 'date', value: x ? x.road_permit_exp : '' },
      { id: 'odometer_km', label: 'odometer_km', type: 'number', value: x ? x.odometer_km : '' }, { id: 'next_service_km', label: 'next_service_km', type: 'number', value: x ? x.next_service_km : '' },
      { id: 'depot', label: 'depot', value: x ? x.depot : 'ທ່າບົກ', lo: true },
      { id: 'status', label: 'status', type: 'select', value: x ? x.status : 'available', options: TT_OPT(['available', 'on_trip', 'maintenance', 'inactive']) },
      { id: 'note', label: 'note', type: 'textarea', value: x ? x.note : '' },
      ...(x ? [{ id: 'active', label: 'active', type: 'select', value: x.active ? '1' : '0', options: [['1', NN.t('active')], ['0', NN.t('inactive')]] }] : []),
    ], NN.t('save'));
    if (!v) return;
    if (x) v.active = v.active === '1';
    try { const r = await (x ? API.put('/api/vehicles/' + x.id, v) : API.post('/api/vehicles', v)); EPL.toast(NN.t('saved'), 'ok'); await tai(); await moHoSo(r.id); } catch (e) { EPL.baoLoi(e); }
  }
  async function suaRM(t) {
    const v = await EPL.hopNhap(t ? NN.t('edit') + ' — ' + t.plate : NN.t('add') + ' ' + NN.t('trailer'), [
      { id: 'plate', label: 'plate', value: t ? t.plate : '', lo: true }, { id: 'trailer_type', label: 'trailer_type', value: t ? t.trailer_type : '', lo: true },
      { id: 'capacity_t', label: 'capacity_t', type: 'number', value: t ? t.capacity_t : '' }, { id: 'year', label: 'year', type: 'number', value: t ? t.year : '' },
      { id: 'owner_type', label: 'owner_type', type: 'select', value: t ? t.owner_type : 'EPL', options: [['EPL', NN.t('co_epl')], ['joint', NN.t('co_joint')]] },
      { id: 'owner_name', label: 'owner', value: t ? t.owner_name : '', lo: true },
      { id: 'insurance_exp', label: 'insurance_exp', type: 'date', value: t ? t.insurance_exp : '' }, { id: 'inspection_exp', label: 'inspection_exp', type: 'date', value: t ? t.inspection_exp : '' },
      { id: 'status', label: 'status', type: 'select', value: t ? t.status : 'available', options: TT_OPT(['available', 'attached', 'maintenance', 'inactive']) },
      { id: 'note', label: 'note', type: 'textarea', value: t ? t.note : '' },
      ...(t ? [{ id: 'active', label: 'active', type: 'select', value: t.active ? '1' : '0', options: [['1', NN.t('active')], ['0', NN.t('inactive')]] }] : []),
    ], NN.t('save'));
    if (!v) return;
    if (t) v.active = v.active === '1';
    try { const r = await (t ? API.put('/api/trailers/' + t.id, v) : API.post('/api/trailers', v)); EPL.toast(NN.t('saved'), 'ok'); await tai(); await moHoSo(r.id); } catch (e) { EPL.baoLoi(e); }
  }
  async function tai() { [XE, RM] = await Promise.all([API.get('/api/vehicles'), API.get('/api/trailers')]); veBang(); }

  EPL.modules['xe'] = {
    async init(r) {
      root = r; tab = 'tractor'; chon = null;
      r.querySelectorAll('.xe-tab button').forEach(b => b.addEventListener('click', () => { tab = b.dataset.tab; r.querySelectorAll('.xe-tab button').forEach(x => x.classList.toggle('active', x === b)); chon = null; q('#xe-ho-so').hidden = true; veBang(); }));
      ['xe-q', 'xe-loai'].forEach(id => q('#' + id).addEventListener('input', veBang));
      const them = q('#xe-them'); them.hidden = !suaDuoc(); them.addEventListener('click', () => tab === 'tractor' ? suaXe(null) : suaRM(null));
      q('#xe-hs-sua').addEventListener('click', () => chon && (tab === 'tractor' ? suaXe(chon) : suaRM(chon)));
      await tai(); if (XE.length) await moHoSo(XE[0].id);
    },
    onLang() { if (root) { veBang(); if (chon) moHoSo(chon.id); } },
  };
})();

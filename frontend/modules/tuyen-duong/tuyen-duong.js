/* Tuyến đường — danh sách, chi tiết chặng, hộp sửa với bảng điểm. */
(function () {
  const { API, NN, esc, so, AUTH } = EPL;
  let root, ds = [], chon = null, diemTam = [], cpTam = [], KM = null, DIEM = [];
  const suaDuoc = () => AUTH.la('yard', 'acct');
  // Bãi không thấy tiền (anh Khampla A2): cột đơn giá gợi ý chỉ hiện với vai được thấy tiền chi
  const thayGia = () => AUTH.role !== 'yard';
  const MUC_CP = [['fuel', 'sec3'], ['travel', 'sec4'], ['other', 'sec6']];
  const CACH = [['', '—'], ['tien_mat', 'pm_on_dispatch'], ['luong', 'pm_trip_salary'], ['ncc', 'pm_supplier']];
  const tenDiem = (id) => { const x = DIEM.find(d => d.id === id); return x ? x.name : '—'; };
  const tenKhoan = (x) => x.item_key ? NN.t(x.item_key) : (x.item_name || '—');

  /** Bảng chi phí gợi ý ở khung chi tiết (chỉ xem) */
  function veGoiY(r) {
    const o = root.querySelector('#tuy-cp'); if (!o) return;
    const coGia = (r.goi_y || []).some(x => 'unit_price' in x);
    const ds = r.goi_y || [];
    const dong = (x) => x.section === 'fuel'
      ? `<tr><td lang="lo">${esc(tenDiem(x.place_id))}</td><td class="num">${so(x.qty)} L</td>${coGia ? '<td></td>' : ''}<td></td></tr>`
      : `<tr><td lang="lo">${esc(tenKhoan(x))}</td><td class="num">${so(x.qty)}</td>${coGia ? `<td class="num">${x.unit_price != null ? so(x.unit_price) + ' ' + esc(x.currency || 'LAK') : '—'}</td>` : ''}
        <td class="small">${x.pay_channel ? NN.h((CACH.find(c => c[0] === x.pay_channel) || [])[1] || x.pay_channel) : ''}</td></tr>`;
    const nhom = MUC_CP.map(([m, k]) => [m, k, ds.filter(x => x.section === m)]).filter(g => g[2].length);
    o.innerHTML = `<div class="tuy-cp-dau"><b>${NN.h('cp_goi_y')}</b>${r.goi_y_nguon === 'chung' ? `<span class="small muted"> · ${NN.h('cp_nguon_chung')}</span>` : ''}</div>
      <table class="tbl tbl-compact tuy-cp-xem"><thead><tr><th>${NN.h('item')} · ${NN.h('fill_place')}</th><th class="num">${NN.h('cp_sl')}</th>${coGia ? `<th class="num">${NN.h('gia_goi_y')}</th>` : ''}<th>${NN.h('owner_pay_mode')}</th></tr></thead>
      <tbody>${nhom.map(([m, k, xs]) => `<tr class="tuy-cp-nhom"><td colspan="${coGia ? 4 : 3}">${NN.h(k)}</td></tr>` + xs.map(dong).join('')).join('')
        || `<tr><td colspan="4" class="empty small">${NN.h('no_data')}</td></tr>`}</tbody></table>`;
  }

  /** Bảng sửa chi phí gợi ý trong hộp sửa tuyến */
  function veCpTam() {
    const tb = root.querySelector('#tuy-f-cp tbody'); if (!tb) return;
    root.querySelectorAll('#tuy-f-cp .tuy-gia').forEach(el => { el.hidden = !thayGia(); });
    tb.innerHTML = cpTam.map((x, i) => {
      const khoan = (KM && KM.items[x.section]) || [];
      const tuGo = !x.item_key;
      return `<tr><td>${i + 1}</td>
        <td><select data-i="${i}" data-f="section">${MUC_CP.map(([v, k]) => `<option value="${v}" ${v === x.section ? 'selected' : ''}>${esc(NN.t(k))}</option>`).join('')}</select></td>
        <td><select data-i="${i}" data-f="item_key">${khoan.filter(k => k !== 'x_toll').map(k => `<option value="${k}" ${k === x.item_key ? 'selected' : ''}>${esc(NN.t(k))}</option>`).join('')}${x.section !== 'fuel' ? `<option value="" ${tuGo ? 'selected' : ''}>${esc(NN.t('x_custom'))}</option>` : ''}</select>
          ${tuGo && x.section !== 'fuel' ? `<input data-i="${i}" data-f="item_name" value="${esc(x.item_name || '')}" placeholder="…" style="margin-top:4px">` : ''}</td>
        <td><input class="num" data-i="${i}" data-f="qty" value="${esc(x.qty ?? '')}" inputmode="decimal"></td>
        <td>${x.section === 'fuel' ? `<select data-i="${i}" data-f="place_id"><option value="">—</option>${DIEM.map(d => `<option value="${d.id}" ${d.id === x.place_id ? 'selected' : ''}>${esc(d.name)}</option>`).join('')}</select>` : ''}</td>
        <td class="tuy-gia" ${thayGia() ? '' : 'hidden'}><input class="num" data-i="${i}" data-f="unit_price" value="${esc(x.unit_price ?? '')}" inputmode="decimal"></td>
        <td class="tuy-gia" ${thayGia() ? '' : 'hidden'}><select data-i="${i}" data-f="currency">${['LAK', 'VND', 'THB', 'USD'].map(c => `<option ${c === (x.currency || 'LAK') ? 'selected' : ''}>${c}</option>`).join('')}</select></td>
        <td>${x.section !== 'fuel' ? `<select data-i="${i}" data-f="pay_channel">${CACH.map(([v, k]) => `<option value="${v}" ${v === (x.pay_channel || '') ? 'selected' : ''}>${esc(k === '—' ? '—' : NN.t(k))}</option>`).join('')}</select>` : ''}</td>
        <td><button type="button" class="x" data-xoa-cp="${i}">×</button></td></tr>`;
    }).join('') || `<tr><td colspan="9" class="empty small">${NN.h('cp_nguon_chung')}</td></tr>`;
    tb.querySelectorAll('[data-f]').forEach(el => el.addEventListener('input', () => {
      const x = cpTam[+el.dataset.i], f = el.dataset.f;
      x[f] = el.value;
      if (f === 'section') { x.item_key = x.section === 'fuel' ? 'diesel' : ((KM && KM.items[x.section]) || []).filter(k => k !== 'x_toll')[0] || null; x.item_name = null; veCpTam(); }
      if (f === 'item_key') { if (!el.value) x.item_key = null; veCpTam(); }
    }));
    tb.querySelectorAll('[data-xoa-cp]').forEach(b => b.addEventListener('click', () => { cpTam.splice(+b.dataset.xoaCp, 1); veCpTam(); }));
  }

  function veDanhSach() {
    const q = root.querySelector('#tuy-q').value.trim().toLowerCase();
    const rows = ds.filter(r => !q || [r.name, r.origin, r.destination].join(' ').toLowerCase().includes(q));
    root.querySelector('#tuy-than').innerHTML = rows.length ? rows.map((r, i) => `<tr data-id="${r.id}" class="${chon && chon.id === r.id ? 'sel' : ''} ${r.active ? '' : 'kh-tat'}">
      <td>${i + 1}</td><td lang="lo"><b>${esc(r.name)}</b></td>
      <td class="num">${r.so_diem}</td><td class="num">${so(r.total_km, 1)}</td><td class="num">${r.return_km ? so(r.return_km, 1) : '—'}</td><td class="num">${so(r.toll_lak)} LAK</td>
      <td>${EPL.tag(r.active ? 'ok' : 'plain', r.active ? 'active' : 'inactive')}</td></tr>`).join('')
      : `<tr><td colspan="7" class="empty">${NN.h('no_data')}</td></tr>`;
    root.querySelectorAll('#tuy-than tr[data-id]').forEach(tr => tr.addEventListener('click', () => moChiTiet(tr.dataset.id)));
  }
  async function moChiTiet(id) {
    chon = await API.get('/api/routes/' + id);
    const o = root.querySelector('#tuy-chi-tiet'); o.hidden = false;
    root.querySelector('#tuy-ten').textContent = chon.name;
    root.querySelector('#tuy-sua').hidden = !suaDuoc();
    root.querySelector('#tuy-chang').innerHTML = chon.stops.map((s, i) => `${i ? '<div class="tuy-noi"></div>' : ''}
      <div class="tuy-diem"><span class="n">${s.seq}</span><span class="ten" lang="lo">${esc(s.name)}</span><span class="km">${i ? '+' + so(s.km_from_prev, 1) + ' km' : NN.t('origin')}</span></div>`).join('')
      // chiều về: xe quay lại điểm đi
      + (chon.return_km && chon.stops.length ? `<div class="tuy-noi ve"></div>
      <div class="tuy-diem ve"><span class="n">↩</span><span class="ten" lang="lo">${esc(chon.stops[0].name)}</span><span class="km">${NN.h('km_ve')} +${so(chon.return_km, 1)} km</span></div>` : '');
    veGoiY(chon);
    root.querySelector('#tuy-tom').innerHTML = `${NN.h('total_km')}: <b>${so(chon.total_km, 1)}</b> km${chon.return_km ? ` · ${NN.h('km_ve')}: <b>${so(chon.return_km, 1)}</b> km · ${NN.h('km_ca_chuyen')}: <b>${so(chon.round_km, 1)}</b> km` : ''} · ${NN.h('toll_bot')}: <b>${so(chon.toll_lak)}</b> LAK · ${NN.h('trips_count')}: <b>${chon.so_phieu}</b>${chon.note ? ' · ' + esc(chon.note) : ''}`;
    veDanhSach();
  }

  /* ------------------------------------------------ hộp sửa */
  function veDiemTam() {
    const tb = root.querySelector('#tuy-f-diem tbody');
    // Toạ độ để màn Theo dõi tuyến vẽ được bản đồ. Để trống cũng được: thiếu toạ độ thì màn đó
    // chỉ bỏ phần bản đồ chứ không hỏng, và thà bỏ còn hơn chấm đại một chỗ không đúng.
    tb.innerHTML = diemTam.map((d, i) => `<tr><td>${i + 1}</td><td><input data-i="${i}" data-f="name" value="${esc(d.name || '')}" lang="lo"></td>
      <td><input class="num" data-i="${i}" data-f="km_from_prev" value="${i ? esc(d.km_from_prev ?? '') : ''}" ${i ? '' : 'disabled placeholder="—"'}></td>
      <td><input class="num" data-i="${i}" data-f="lat" value="${esc(d.lat ?? '')}" placeholder="${esc(NN.t('st_lat'))}" inputmode="decimal"></td>
      <td><input class="num" data-i="${i}" data-f="lng" value="${esc(d.lng ?? '')}" placeholder="${esc(NN.t('st_lng'))}" inputmode="decimal"></td>
      <td>${diemTam.length > 2 ? `<button type="button" class="x" data-xoa="${i}">×</button>` : ''}</td></tr>`).join('');
    tb.querySelectorAll('input[data-f]').forEach(el => el.addEventListener('input', () => { diemTam[+el.dataset.i][el.dataset.f] = el.value; veNutVe(); }));
    veNutVe();
    tb.querySelectorAll('[data-xoa]').forEach(b => b.addEventListener('click', () => { diemTam.splice(+b.dataset.xoa, 1); veDiemTam(); }));
  }
  // Nút "= … km" cạnh ô Km chiều về: chép tổng chiều đi (xe về đúng đường cũ)
  const kmDi = () => diemTam.slice(1).reduce((a, d) => a + EPL.doc(d.km_from_prev), 0);
  function veNutVe() { const b = root.querySelector('#tuy-f-ve-bang'); if (b) b.textContent = '= ' + so(kmDi(), 1) + ' km'; }
  function moHop(r) {
    const dlg = root.querySelector('#tuy-hop');
    root.querySelector('#tuy-hop-tieu-de').textContent = r ? NN.t('edit') + ' — ' + r.name : NN.t('add');
    root.querySelector('#tuy-f-name').value = r ? r.name : '';
    root.querySelector('#tuy-f-toll').value = r ? r.toll_lak : '';
    root.querySelector('#tuy-f-note').value = r ? (r.note || '') : '';
    root.querySelector('#tuy-f-ve').value = r && r.return_km ? r.return_km : '';
    root.querySelector('#tuy-f-active-o').hidden = !r; if (r) root.querySelector('#tuy-f-active').value = r.active ? '1' : '0';
    diemTam = r ? r.stops.map(s => ({ name: s.name, km_from_prev: s.km_from_prev, lat: s.lat, lng: s.lng }))
      : [{ name: '' }, { name: '', km_from_prev: '' }];
    cpTam = r && Array.isArray(r.cost_template) ? r.cost_template.map(x => ({ ...x })) : [];
    veDiemTam(); veCpTam(); NN.apDung(dlg);
    dlg.returnValue = '';
    dlg.addEventListener('close', async function xong() {
      dlg.removeEventListener('close', xong);
      if (dlg.returnValue !== 'ok') return;
      const body = { name: root.querySelector('#tuy-f-name').value, toll_lak: EPL.doc(root.querySelector('#tuy-f-toll').value),
        note: root.querySelector('#tuy-f-note').value, return_km: EPL.doc(root.querySelector('#tuy-f-ve').value),
        stops: diemTam.map(d => ({ name: d.name, km_from_prev: EPL.doc(d.km_from_prev),
          lat: d.lat === '' || d.lat == null ? null : EPL.doc(d.lat),
          lng: d.lng === '' || d.lng == null ? null : EPL.doc(d.lng) })),
        // bộ chi phí gợi ý — Bãi gửi không kèm giá (máy chủ giữ giá kế toán đã đặt)
        cost_template: cpTam.map(x => ({ section: x.section, item_key: x.item_key || null, item_name: x.item_name || null, qty: EPL.doc(x.qty),
          place_id: x.section === 'fuel' ? (x.place_id || null) : undefined, pay_channel: x.section === 'fuel' ? undefined : (x.pay_channel || null),
          ...(thayGia() ? { unit_price: x.unit_price === '' || x.unit_price == null ? null : EPL.doc(x.unit_price), currency: x.currency || 'LAK' } : {}) })) };
      if (r) body.active = root.querySelector('#tuy-f-active').value === '1';
      try { const moi = await (r ? API.put('/api/routes/' + r.id, body) : API.post('/api/routes', body)); EPL.toast(NN.t('saved'), 'ok'); ds = await API.get('/api/routes'); await moChiTiet(moi.id); }
      catch (e) { EPL.baoLoi(e); }
    });
    dlg.showModal();
  }

  EPL.modules['tuyen-duong'] = {
    async init(r) {
      root = r;
      [ds, KM, DIEM] = await Promise.all([API.get('/api/routes'), API.get('/api/khoan-muc'), API.get('/api/fuel-places').catch(() => [])]);
      r.querySelector('#tuy-q').addEventListener('input', veDanhSach);
      const them = r.querySelector('#tuy-them'); them.hidden = !suaDuoc(); them.addEventListener('click', () => moHop(null));
      r.querySelector('#tuy-sua').addEventListener('click', () => chon && moHop(chon));
      r.querySelector('#tuy-f-them-diem').addEventListener('click', () => { diemTam.push({ name: '', km_from_prev: '' }); veDiemTam(); });
      r.querySelector('#tuy-f-ve-bang').addEventListener('click', () => { r.querySelector('#tuy-f-ve').value = Math.round(kmDi() * 10) / 10; });
      r.querySelector('#tuy-f-them-cp').addEventListener('click', () => { cpTam.push({ section: 'travel', item_key: 'x_water', qty: 1, currency: 'LAK' }); veCpTam(); });
      r.querySelector('#tuy-f-chep-chung').addEventListener('click', async () => {
        try { cpTam = (await API.get('/api/tuyen-bo-chung')).map(x => ({ ...x })); veCpTam(); } catch (e) { EPL.baoLoi(e); }
      });
      veDanhSach(); if (ds.length) await moChiTiet(ds[0].id);
    },
    onLang() { if (root) { veDanhSach(); if (chon) moChiTiet(chon.id); } },
  };
})();

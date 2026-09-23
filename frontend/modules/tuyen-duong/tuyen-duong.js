/* Tuyến đường — danh sách, chi tiết chặng, hộp sửa với bảng điểm. */
(function () {
  const { API, NN, esc, so, AUTH } = EPL;
  let root, ds = [], chon = null, diemTam = [];
  const suaDuoc = () => AUTH.la('yard', 'acct');

  function veDanhSach() {
    const q = root.querySelector('#tuy-q').value.trim().toLowerCase();
    const rows = ds.filter(r => !q || [r.name, r.origin, r.destination].join(' ').toLowerCase().includes(q));
    root.querySelector('#tuy-than').innerHTML = rows.length ? rows.map((r, i) => `<tr data-id="${r.id}" class="${chon && chon.id === r.id ? 'sel' : ''} ${r.active ? '' : 'kh-tat'}">
      <td>${i + 1}</td><td lang="lo"><b>${esc(r.name)}</b></td><td lang="lo">${esc(r.origin)}</td><td lang="lo">${esc(r.destination)}</td>
      <td class="num">${r.so_diem}</td><td class="num">${so(r.total_km, 1)}</td><td class="num">${so(r.toll_lak)} LAK</td>
      <td>${EPL.tag(r.active ? 'ok' : 'plain', r.active ? 'active' : 'inactive')}</td></tr>`).join('')
      : `<tr><td colspan="8" class="empty">${NN.h('no_data')}</td></tr>`;
    root.querySelectorAll('#tuy-than tr[data-id]').forEach(tr => tr.addEventListener('click', () => moChiTiet(tr.dataset.id)));
  }
  async function moChiTiet(id) {
    chon = await API.get('/api/routes/' + id);
    const o = root.querySelector('#tuy-chi-tiet'); o.hidden = false;
    root.querySelector('#tuy-ten').textContent = chon.name;
    root.querySelector('#tuy-sua').hidden = !suaDuoc();
    root.querySelector('#tuy-chang').innerHTML = chon.stops.map((s, i) => `${i ? '<div class="tuy-noi"></div>' : ''}
      <div class="tuy-diem"><span class="n">${s.seq}</span><span class="ten" lang="lo">${esc(s.name)}</span><span class="km">${i ? '+' + so(s.km_from_prev, 1) + ' km' : NN.t('origin')}</span></div>`).join('');
    root.querySelector('#tuy-tom').innerHTML = `${NN.h('total_km')}: <b>${so(chon.total_km, 1)}</b> km · ${NN.h('toll_bot')}: <b>${so(chon.toll_lak)}</b> LAK · ${NN.h('trips_count')}: <b>${chon.so_phieu}</b>${chon.note ? ' · ' + esc(chon.note) : ''}`;
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
    tb.querySelectorAll('input[data-f]').forEach(el => el.addEventListener('input', () => { diemTam[+el.dataset.i][el.dataset.f] = el.value; }));
    tb.querySelectorAll('[data-xoa]').forEach(b => b.addEventListener('click', () => { diemTam.splice(+b.dataset.xoa, 1); veDiemTam(); }));
  }
  function moHop(r) {
    const dlg = root.querySelector('#tuy-hop');
    root.querySelector('#tuy-hop-tieu-de').textContent = r ? NN.t('edit') + ' — ' + r.name : NN.t('add');
    root.querySelector('#tuy-f-name').value = r ? r.name : '';
    root.querySelector('#tuy-f-toll').value = r ? r.toll_lak : '';
    root.querySelector('#tuy-f-note').value = r ? (r.note || '') : '';
    root.querySelector('#tuy-f-active-o').hidden = !r; if (r) root.querySelector('#tuy-f-active').value = r.active ? '1' : '0';
    diemTam = r ? r.stops.map(s => ({ name: s.name, km_from_prev: s.km_from_prev, lat: s.lat, lng: s.lng }))
      : [{ name: '' }, { name: '', km_from_prev: '' }];
    veDiemTam(); NN.apDung(dlg);
    dlg.returnValue = '';
    dlg.addEventListener('close', async function xong() {
      dlg.removeEventListener('close', xong);
      if (dlg.returnValue !== 'ok') return;
      const body = { name: root.querySelector('#tuy-f-name').value, toll_lak: EPL.doc(root.querySelector('#tuy-f-toll').value),
        note: root.querySelector('#tuy-f-note').value,
        stops: diemTam.map(d => ({ name: d.name, km_from_prev: EPL.doc(d.km_from_prev),
          lat: d.lat === '' || d.lat == null ? null : EPL.doc(d.lat),
          lng: d.lng === '' || d.lng == null ? null : EPL.doc(d.lng) })) };
      if (r) body.active = root.querySelector('#tuy-f-active').value === '1';
      try { const moi = await (r ? API.put('/api/routes/' + r.id, body) : API.post('/api/routes', body)); EPL.toast(NN.t('saved'), 'ok'); ds = await API.get('/api/routes'); await moChiTiet(moi.id); }
      catch (e) { EPL.baoLoi(e); }
    });
    dlg.showModal();
  }

  EPL.modules['tuyen-duong'] = {
    async init(r) {
      root = r; ds = await API.get('/api/routes');
      r.querySelector('#tuy-q').addEventListener('input', veDanhSach);
      const them = r.querySelector('#tuy-them'); them.hidden = !suaDuoc(); them.addEventListener('click', () => moHop(null));
      r.querySelector('#tuy-sua').addEventListener('click', () => chon && moHop(chon));
      r.querySelector('#tuy-f-them-diem').addEventListener('click', () => { diemTam.push({ name: '', km_from_prev: '' }); veDiemTam(); });
      veDanhSach(); if (ds.length) await moChiTiet(ds[0].id);
    },
    onLang() { if (root) { veDanhSach(); if (chon) moChiTiet(chon.id); } },
  };
})();

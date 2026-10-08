/* Điểm đổ nhiên liệu — ສະຖານທີ່ເຕີມນໍ້າມັນ (08/10, anh Khampla: "có thêm chức năng tạo kho mới"; chủ dự án duyệt).
 *
 * Ô "Nơi đổ" trên phiếu xuất xe đọc danh sách này. Trang kế toán tạm 8031 (người ghi danh sách từ 28/09) đã bỏ 05/10 → mở lại ở đây:
 *   · Kho dầu EPL: tạo ở Web (Quản lý kho → Khai báo kho), rồi «Thêm kho dầu từ danh mục kho» chọn kho đó — mã điểm đổ = mã kho (cũng là
 *     mã kho khi xuất dầu); tên, địa chỉ, đang dùng / ngưng theo Web. Ở đây chỉ sửa nước và ghi chú.
 *   · Trạm dầu ngoài: thêm / sửa / ngưng tại đây (mã, tên, nước, nhà cung cấp, địa chỉ, ghi chú).
 * Không xoá điểm đổ (phiếu, phiếu đề nghị trỏ vào) — ngưng dùng. Quyền sửa do máy chủ trả (GET /api/fuel-places/quyen).
 */
(function () {
  const { API, NN, esc, tag } = EPL;
  let root, DS = [], KHO = null, NCC = null, Q = { sua: false };

  const g = (id) => root.querySelector('#' + id);
  const nuoc = (c) => NN.h(c === 'VN' ? 'fp_vn2' : 'fp_la');

  /* ---------------------------------------------------------------- danh sách điểm đổ */
  function ve() {
    const q = g('dd-q').value.trim().toLowerCase();
    const rows = DS.filter(x => !q || [x.code, x.name, x.supplier_name, x.address, x.note].join(' ').toLowerCase().includes(q));
    g('dd-than').innerHTML = rows.length ? rows.map(x => `<tr class="${x.active ? '' : 'dd-tat'}">
      <td class="mono"><b>${esc(x.code || '')}</b></td>
      <td><span lang="lo">${esc(x.name || '')}</span>${x.owner_type === 'epl' && x.wh_id ? `<span class="dd-web">${NN.h('dd_theo_web')}${x.wh_synced_at ? ' · ' + esc(EPL.ngayGio(x.wh_synced_at)) : ''}</span>` : ''}</td>
      <td>${NN.h(x.owner_type === 'epl' ? 'fp_epl' : 'fp_ngoai')}</td>
      <td>${nuoc(x.country)}</td>
      <td lang="lo">${esc(x.supplier_name || '') || '—'}</td>
      <td class="small" lang="lo">${esc(x.address || '') || '—'}${x.note ? `<div class="small muted" lang="lo">${esc(x.note)}</div>` : ''}</td>
      <td>${tag(x.active ? 'ok' : 'plain', x.active ? 'active' : 'inactive')}</td>
      <td class="no-print">${Q.sua ? `<button class="btn sm" data-sua="${esc(x.id)}">${NN.h('edit')}</button>` : ''}</td></tr>`).join('')
      : `<tr><td colspan="8" class="empty">${NN.h('no_data')}</td></tr>`;
    g('dd-dem').textContent = rows.length ? `${rows.length} ${NN.t('rows')}` : '';
    root.querySelectorAll('[data-sua]').forEach(b => b.addEventListener('click', () => sua(DS.find(x => x.id === b.dataset.sua))));
  }

  /* ---------------------------------------------------------------- thêm / sửa */
  async function napNcc() {
    if (NCC) return NCC;
    try { NCC = await API.get('/api/suppliers'); } catch (e) { NCC = []; }
    return NCC;
  }
  const oNuoc = (v) => ({ id: 'country', label: 'fp_country', type: 'select', value: v || 'LA', options: [['LA', NN.t('fp_la')], ['VN', NN.t('fp_vn2')]] });

  async function sua(x) {
    if (!x) return;
    if (x.owner_type === 'epl') {
      // kho dầu EPL: tên, mã, địa chỉ, đang dùng theo Web — ở đây chỉ nước và ghi chú
      const v = await EPL.hopNhap(NN.t('edit') + ' · ' + (x.code || ''), [oNuoc(x.country), { id: 'note', label: 'note', type: 'textarea', value: x.note || '' }],
        NN.t('save'));
      if (!v) return;
      return luu(() => API.put('/api/fuel-places/' + x.id, { country: v.country, note: v.note }));
    }
    return suaTram(x);
  }

  async function suaTram(x) {
    const ncc = await napNcc();
    const v = await EPL.hopNhap(x ? NN.t('edit') + ' · ' + (x.code || '') : NN.t('dd_them_tram'), [
      { id: 'code', label: 'code', value: x ? x.code || '' : '', placeholder: 'VN-02' },
      { id: 'name', label: 'name', value: x ? x.name || '' : '', lo: true },
      oNuoc(x ? x.country : 'LA'),
      { id: 'supplier_id', label: 'supplier', type: 'select', value: x ? x.supplier_id || '' : '', tim: 'search',
        options: [['', '—']].concat(ncc.filter(n => n.active !== false || (x && n.id === x.supplier_id)).map(n => [n.id, n.name, false, n.code || ''])) },
      { id: 'address', label: 'address', value: x ? x.address || '' : '', lo: true },
      { id: 'note', label: 'note', type: 'textarea', value: x ? x.note || '' : '' },
      ...(x ? [{ id: 'active', label: 'status', type: 'select', value: x.active ? '1' : '0', options: [['1', NN.t('active')], ['0', NN.t('inactive')]] }] : []),
    ], NN.t('save'));
    if (!v) return;
    if (!String(v.code || '').trim()) return EPL.toast(NN.t('code') + '?', 'loi');
    if (!String(v.name || '').trim()) return EPL.toast(NN.t('name') + '?', 'loi');
    const than = { code: v.code, name: v.name, country: v.country, supplier_id: v.supplier_id || null, address: v.address, note: v.note };
    if (x) than.active = v.active === '1';
    return luu(() => (x ? API.put('/api/fuel-places/' + x.id, than) : API.post('/api/fuel-places', than)));
  }

  async function luu(goi) {
    try { await goi(); EPL.toast(NN.t('saved'), 'ok'); await tai(); } catch (e) { EPL.baoLoi(e); }
  }

  /* ---------------------------------------------------------------- danh mục kho trên Web */
  function veKho() {
    const o = g('dd-kho'); o.hidden = !KHO;
    root.querySelector('.dd-khung').classList.toggle('co-kho', !!KHO);
    if (!KHO) return;
    const q = g('dd-kho-q').value.trim().toLowerCase();
    const rows = KHO.filter(w => !q || [w.code, w.name, w.loai, w.don_vi].join(' ').toLowerCase().includes(q));
    g('dd-kho-than').innerHTML = rows.length ? rows.map(w => `<tr class="${w.active ? '' : 'dd-tat'}">
      <td class="mono"><b>${esc(w.code)}</b></td>
      <td lang="lo">${esc(w.name || '')}${w.don_vi ? `<div class="small muted">${esc(w.don_vi)}</div>` : ''}</td>
      <td class="small">${esc(w.loai || '')}</td>
      <td>${tag(w.active ? 'ok' : 'plain', w.active ? 'active' : 'inactive')}</td>
      <td class="no-print">${w.place_id ? `<span class="small muted">${NN.h('dd_da_gan')}</span>`
        : `<button class="btn sm ok" data-chon="${esc(String(w.wh_id))}">${NN.h('dd_chon')}</button>`}</td></tr>`).join('')
      : `<tr><td colspan="5" class="empty">${NN.h('no_data')}</td></tr>`;
    root.querySelectorAll('[data-chon]').forEach(b => b.addEventListener('click', () => chonKho(KHO.find(w => String(w.wh_id) === b.dataset.chon))));
  }

  async function moKho() {
    try {
      KHO = await API.get('/api/fuel-places/kho-web');   // máy chủ chép lại luôn thông tin các kho đã gắn
      veKho(); await tai();
    } catch (e) { EPL.baoLoi(e); }
  }

  async function chonKho(w) {
    if (!w) return;
    const v = await EPL.hopNhap(NN.t('dd_chon') + ' · ' + w.code, [oNuoc('LA')], NN.t('dd_chon'));
    if (!v) return;
    try {
      await API.post('/api/fuel-places/kho-web/' + encodeURIComponent(w.wh_id), { country: v.country });
      EPL.toast(NN.t('dd_da_chon', { ma: w.code }), 'ok');
      KHO = await API.get('/api/fuel-places/kho-web'); veKho(); await tai();
    } catch (e) { EPL.baoLoi(e); }
  }

  async function capNhat() {
    try {
      const kq = await API.post('/api/fuel-places/dong-bo-kho', {});
      EPL.toast(NN.t('dd_da_cap_nhat', { n: kq.cap_nhat || 0 }) + ((kq.mat || []).length ? ' · ' + NN.t('dd_mat', { ds: kq.mat.join(', ') }) : ''),
        (kq.mat || []).length ? 'loi' : 'ok');
      await tai();
    } catch (e) { EPL.baoLoi(e); }
  }

  /* ---------------------------------------------------------------- nạp dữ liệu */
  async function tai() {
    [DS, Q] = await Promise.all([API.get('/api/fuel-places?tat_ca=1'), API.get('/api/fuel-places/quyen').catch(() => ({ sua: false }))]);
    // kho dầu EPL trước, rồi trạm ngoài; trong nhóm theo mã
    DS.sort((a, b) => (a.owner_type === b.owner_type ? 0 : a.owner_type === 'epl' ? -1 : 1) || String(a.code || '').localeCompare(String(b.code || '')));
    ['dd-tu-kho', 'dd-them-tram', 'dd-cap-nhat'].forEach(id => { g(id).hidden = !Q.sua; });
    ve();
  }

  EPL.modules['diem-do'] = {
    async init(r) {
      root = r; KHO = null; NCC = null;
      g('dd-q').addEventListener('input', ve);
      g('dd-kho-q').addEventListener('input', veKho);
      g('dd-tu-kho').addEventListener('click', moKho);
      g('dd-them-tram').addEventListener('click', () => suaTram(null));
      g('dd-cap-nhat').addEventListener('click', capNhat);
      g('dd-kho-dong').addEventListener('click', () => { KHO = null; veKho(); });
      await tai();
    },
    onLang() { if (root) { ve(); veKho(); } },
  };
})();

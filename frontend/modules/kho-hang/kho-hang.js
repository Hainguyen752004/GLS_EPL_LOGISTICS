/* Kho hàng ở bãi Thà Bốc — nơi quặng nằm giữa hai chặng.
   Lô = một phiếu GOM hàng đã về bãi. Xuất kho = một phiếu GIAO hàng lấy hàng của lô đó đi.
   Tồn luôn cộng dồn từ sổ (GET /api/kho-hang), không có bảng tồn riêng nên không bao giờ lệch. */
(function () {
  const { API, NN, esc, so, AUTH } = EPL;
  const dieuChinhDuoc = () => AUTH.la('acct');   // KT Thu/Chi VC (người kiểm mục II) và Sếp
  let root, d = null;

  function ve() {
    root.querySelector('#kh-kpi').innerHTML = [
      ['kh_ton_tong', so(d.ton_t, 2), NN.t('ton'), NN.t('kh_ton_sub')],
      ['kh_con_lo', so(d.con_lo, 0), NN.t('kh_lo_dv'), NN.t('kh_con_lo_sub')],
      ['kh_so_dong', so(d.so.length, 0), NN.t('kh_dong_dv'), NN.t('kh_so_hint')],
    ].map(k => `<div class="kpi"><div class="l">${NN.h(k[0])}</div><div class="v">${k[1]}<small>${esc(k[2])}</small></div><div class="s">${esc(k[3])}</div></div>`).join('');

    root.querySelector('#kh-lo').innerHTML = d.lo.length ? d.lo.map(l => `<tr class="${l.con_t > 0.0005 ? '' : 'kh-het'}" data-phieu="${esc(l.doc_no || '')}">
      <td class="mono"><b>${esc(l.doc_no) || '—'}</b></td><td>${EPL.ngay(l.ngay)}</td><td lang="lo">${esc(l.goods_name)}</td>
      <td lang="lo">${esc(l.customer_name) || '—'}</td><td>${esc(l.truck_no) || '—'}</td>
      <td class="num">${so(l.nhap_t, 2)}</td><td class="num">${l.dieu_chinh_t ? (l.dieu_chinh_t > 0 ? '+' : '') + so(l.dieu_chinh_t, 2) : '—'}</td><td class="num"><b>${so(l.con_t, 2)}</b></td>
      <td>${EPL.tag(l.con_t > 0.0005 ? 'ok' : 'plain', l.con_t > 0.0005 ? 'kh_con_hang' : 'kh_het_hang')}</td>
      <td class="no-print">${dieuChinhDuoc() ? `<button type="button" class="btn sm" data-dc="${esc(l.lo_trip_id)}">${NN.h('kh_dieu_chinh')}</button>` : ''}</td></tr>`).join('')
      : `<tr><td colspan="10" class="empty">${NN.h('kh_chua_co')}</td></tr>`;
    root.querySelectorAll('[data-dc]').forEach(b => b.addEventListener('click', e => { e.stopPropagation(); dieuChinh(d.lo.find(x => x.lo_trip_id === b.dataset.dc)); }));

    root.querySelector('#kh-so').innerHTML = d.so.length ? d.so.slice().reverse().map(m => `<tr data-phieu="${esc(m.doc_no || '')}">
      <td>${EPL.ngay(m.ngay)}</td><td>${EPL.tag(m.kind === 'in' ? 'ok' : m.kind === 'adj' ? 'partial' : 'plain', m.kind === 'in' ? 'kh_nhap' : m.kind === 'adj' ? 'kh_dc' : 'kh_xuat')}</td>
      <td lang="lo">${esc(m.goods_name)}${m.kind === 'adj' && m.note ? `<div class="small muted">${esc(m.note)}</div>` : ''}</td><td class="mono">${esc(m.doc_no) || '—'}</td>
      <td class="num kh-vao">${m.kind === 'in' || (m.kind === 'adj' && m.qty_t > 0) ? (m.kind === 'adj' ? '+' : '') + so(m.qty_t, 2) : ''}</td><td class="num kh-ra">${m.kind === 'out' ? so(m.qty_t, 2) : m.kind === 'adj' && m.qty_t < 0 ? so(-m.qty_t, 2) : ''}</td>
      <td class="num"><b>${so(m.ton_t, 2)}</b></td><td lang="lo">${esc(m.by_user) || '—'}</td></tr>`).join('')
      : `<tr><td colspan="8" class="empty">${NN.h('kh_chua_co')}</td></tr>`;

    // Bấm một dòng là mở đúng phiếu sinh ra nó — kho và phiếu là hai mặt của một việc.
    root.querySelectorAll('[data-phieu]').forEach(tr => tr.addEventListener('click', () => {
      if (tr.dataset.phieu) EPL.di('theo-doi', { q: tr.dataset.phieu });
    }));
  }

  /** Điều chỉnh tồn một lô: +/− tấn kèm lý do. Không sửa lịch sử nhập/xuất — thêm một dòng có dấu. */
  async function dieuChinh(lo) {
    if (!lo) return;
    const v = await EPL.hopNhap(`${NN.t('kh_dieu_chinh')} · ${lo.doc_no} (${NN.t('kh_con')} ${so(lo.con_t, 2)} t)`, [
      { id: 'qty_t', label: 'kh_dc_so', type: 'number', value: '' },
      { id: 'ly_do', label: 'kh_dc_ly_do', type: 'textarea', value: '' },
    ], NN.t('save'));
    if (!v) return;
    try {
      await API.post('/api/kho-hang/dieu-chinh', { lo_trip_id: lo.lo_trip_id, qty_t: v.qty_t, ly_do: v.ly_do });
      EPL.toast(NN.t('saved'), 'ok'); d = await API.get('/api/kho-hang'); ve();
    } catch (e) { EPL.baoLoi(e); }
  }

  EPL.modules['kho-hang'] = {
    async init(r) { root = r; d = await API.get('/api/kho-hang'); ve(); },
    onLang() { if (d) ve(); },
  };
})();

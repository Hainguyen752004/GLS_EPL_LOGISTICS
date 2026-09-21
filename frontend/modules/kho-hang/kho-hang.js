/* Kho hàng ở bãi Thà Bốc — nơi quặng nằm giữa hai chặng.
   Lô = một phiếu GOM hàng đã về bãi. Xuất kho = một phiếu GIAO hàng lấy hàng của lô đó đi.
   Tồn luôn cộng dồn từ sổ (GET /api/kho-hang), không có bảng tồn riêng nên không bao giờ lệch. */
(function () {
  const { API, NN, esc, so } = EPL;
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
      <td class="num">${so(l.nhap_t, 2)}</td><td class="num"><b>${so(l.con_t, 2)}</b></td>
      <td>${EPL.tag(l.con_t > 0.0005 ? 'ok' : 'plain', l.con_t > 0.0005 ? 'kh_con_hang' : 'kh_het_hang')}</td></tr>`).join('')
      : `<tr><td colspan="8" class="empty">${NN.h('kh_chua_co')}</td></tr>`;

    root.querySelector('#kh-so').innerHTML = d.so.length ? d.so.slice().reverse().map(m => `<tr data-phieu="${esc(m.doc_no || '')}">
      <td>${EPL.ngay(m.ngay)}</td><td>${EPL.tag(m.kind === 'in' ? 'ok' : 'plain', m.kind === 'in' ? 'kh_nhap' : 'kh_xuat')}</td>
      <td lang="lo">${esc(m.goods_name)}</td><td class="mono">${esc(m.doc_no) || '—'}</td>
      <td class="num kh-vao">${m.kind === 'in' ? so(m.qty_t, 2) : ''}</td><td class="num kh-ra">${m.kind === 'out' ? so(m.qty_t, 2) : ''}</td>
      <td class="num"><b>${so(m.ton_t, 2)}</b></td><td lang="lo">${esc(m.by_user) || '—'}</td></tr>`).join('')
      : `<tr><td colspan="8" class="empty">${NN.h('kh_chua_co')}</td></tr>`;

    // Bấm một dòng là mở đúng phiếu sinh ra nó — kho và phiếu là hai mặt của một việc.
    root.querySelectorAll('[data-phieu]').forEach(tr => tr.addEventListener('click', () => {
      if (tr.dataset.phieu) EPL.di('theo-doi', { q: tr.dataset.phieu });
    }));
  }

  EPL.modules['kho-hang'] = {
    async init(r) { root = r; d = await API.get('/api/kho-hang'); ve(); },
    onLang() { if (d) ve(); },
  };
})();

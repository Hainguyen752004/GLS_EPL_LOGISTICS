/* Tổng quan — mọi số lấy từ /api/bao-cao/tong-quan, tính lại từ phiếu lúc gọi. */
(function () {
  const { API, NN, esc, so, tien } = EPL;
  let root, thang, du_lieu, ty_gia;

  async function tai() {
    thang = root.querySelector('#tq-thang').value || EPL.thangNay();
    [du_lieu, ty_gia] = await Promise.all([API.get('/api/bao-cao/tong-quan?thang=' + thang), API.get('/api/rates')]);
    ve();
  }

  function ve() {
    const d = du_lieu, r_usd = ty_gia.USD || 22000;
    root.querySelector('#tq-kpi').innerHTML = [
      ['k_rev', so(d.doanh_thu_usd, 2), 'USD', `${d.so_phieu} ${NN.t('trips')} · ≈ ${so(d.doanh_thu_usd * r_usd)} LAK`],
      ['k_exp', so(d.chi_lak / 1e6, 1), 'M LAK', `≈ ${so(d.chi_lak / r_usd)} USD · ${d.doanh_thu_usd ? so(d.chi_lak / r_usd / d.doanh_thu_usd * 100) : 0}% ${NN.t('revenue').replace(/\s*\(.*\)/, '')}`],
      ['k_tons', so(d.tan_giao, 2), NN.t('ton'), `${d.dem.arrived} ${NN.t('trips')} · ${NN.t('s_arrived')}`],
      ['k_unpaid', so(d.chua_thu_usd, 2), 'USD', `${d.chua_thu_so} ${NN.t('trips')} · ${NN.t('s_unpaid')}`],
    ].map(k => `<div class="kpi"><div class="l">${NN.h(k[0])}</div><div class="v">${k[1]}<small>${esc(k[2])}</small></div><div class="s">${esc(k[3])}</div></div>`).join('');

    const P = [['s_dispatched', d.dem.dispatched, 'dispatched'], ['s_transit', d.dem.transit, 'transit'],
               ['s_arrived', d.dem.arrived, 'arrived'], ['p_invoiced', d.dem.invoiced, ''], ['s_paid', d.dem.paid, '']];
    root.querySelector('#tq-tien-do').innerHTML = P.map(p => `<div class="pipe" role="button" tabindex="0" data-st="${p[2]}"><div class="n">${p[1]}</div><div class="l">${NN.h(p[0])}</div></div>`).join('');
    root.querySelectorAll('.pipe').forEach(el => el.addEventListener('click', () => EPL.di('theo-doi', el.dataset.st ? { transport_status: el.dataset.st } : {})));

    const cm = d.chi_theo_muc, tong = Object.values(cm).reduce((a, b) => a + b, 0) || 1;
    root.querySelector('#tq-co-cau').innerHTML = [['e_fuel', 'fuel', 'fuel'], ['e_travel', 'travel', ''], ['e_repair', 'repair', 'rep'], ['e_other', 'other', 'oth']]
      .map(b => `<div class="bar"><span>${NN.h(b[0])}</span><div class="track"><div class="fill ${b[2]}" style="width:${cm[b[1]] / tong * 100}%"></div></div><span class="v">${so(cm[b[1]])} <span class="muted small">${so(cm[b[1]] / tong * 100)}%</span></span></div>`).join('');

    root.querySelector('#tq-ty-gia').innerHTML = `<div class="tq-ty-gia">${['USD', 'THB', 'VND'].map(m => `<div><span class="small muted">1 ${m} =</span><b>${so(ty_gia[m], m === 'VND' ? 2 : 0)} LAK</b></div>`).join('')}</div>`;

    const cy = d.chu_y || [];
    root.querySelector('#tq-chu-y').innerHTML = cy.length
      ? `<div class="tq-chu-y">${cy.map(c => `<div data-doc="${esc(c.doc_no || '')}">${esc(NN.t('attention_' + c.loai, c))}</div>`).join('')}</div>`
      : `<div class="muted small">${NN.h('none_attention')}</div>`;
    root.querySelectorAll('.tq-chu-y div[data-doc]').forEach(el => el.addEventListener('click', () => {
      if (el.dataset.doc) EPL.di('theo-doi', { q: el.dataset.doc }); else EPL.di('phieu-xuat-xe');
    }));
  }

  EPL.modules['tong-quan'] = {
    async init(r) {
      root = r;
      // Mặc định là THÁNG CÓ PHIẾU GẦN NHẤT, không phải tháng hiện tại: mở màn mà thấy toàn số 0
      // chỉ vì tháng này chưa lập phiếu nào thì người xem tưởng hệ thống trống.
      let thangMacDinh = EPL.thangNay();
      try { const ds = await API.get('/api/trips'); if (ds.length && ds[0].doc_date) thangMacDinh = ds[0].doc_date.slice(0, 7); } catch (e) { /* giữ tháng nay */ }
      r.querySelector('#tq-thang').value = thangMacDinh;
      r.querySelector('#tq-thang').addEventListener('change', () => tai().catch(EPL.baoLoi));
      r.querySelector('#tq-moi').addEventListener('click', () => EPL.di('phieu-xuat-xe', { moi: 1 }));
      await tai();
    },
    onLang() { if (du_lieu) ve(); },
  };
})();

/* Hoá đơn vận chuyển — in một phiếu. Mọi con số lấy từ máy chủ (trường `tinh`), không tính lại ở đây. */
(function () {
  const { API, NN, esc, so, tag } = EPL;
  let root, ds = [], P;

  function bang(sec, tieuDe, nhanSL) {
    const dong = (P.expenses || []).filter(d => d.section === sec); if (!dong.length) return '';
    const lk = P.tinh.lien_ket; const rate = { USD: P.rate_usd, THB: P.rate_thb, VND: P.rate_vnd, LAK: 1 };
    let tongSL = 0, tong = 0;
    const rows = dong.map((d, i) => { const t = d.qty * d.unit_price * (rate[d.currency] || 1); tongSL += d.qty; if (!lk || d.paid_by_epl) tong += t;
      return `<tr class="${lk && !d.paid_by_epl ? 'hd-mo' : ''}"><td>${i + 1}</td><td>${esc(EPL.khoanMuc(d))}${sec === 'fuel' && d.place ? ` <span class="muted small">(${NN.h(d.place)})</span>` : ''}</td><td class="num">${so(d.qty)}</td><td class="num">${so(d.unit_price)}${d.currency !== 'LAK' ? ' ' + esc(d.currency) : ''}</td><td class="num">${so(t)}</td>${lk ? `<td>${NN.h(d.paid_by_epl ? 'pay_epl' : 'pay_own')}</td>` : ''}</tr>`; }).join('');
    return `<h5>${tieuDe}</h5><table class="tbl tbl-compact"><thead><tr><th>#</th><th>${NN.h('item')}</th><th class="num">${NN.h(nhanSL)}</th><th class="num">${NN.h('unit_price')}</th><th class="num">${NN.h('amount_lak')}</th>${lk ? `<th>${NN.h('who_pays')}</th>` : ''}</tr></thead>
      <tbody>${rows}</tbody><tfoot><tr><td></td><td>${NN.h('total')}</td><td class="num">${sec === 'fuel' ? so(tongSL) : ''}</td><td></td><td class="num">${so(tong)}</td>${lk ? '<td></td>' : ''}</tr></tfoot></table>`;
  }
  function thanhToan(c) {
    const r = (l, d, v, cls = '') => `<div class="r ${cls}"><span>${l}${d ? `<small>${d}</small>` : ''}</span><span>${v}</span></div>`;
    return `<div class="hd-tt"><div class="o"><b>${NN.h('settle_title')}</b>
      ${r(NN.h('st_hire'), `${so(c.gia_thue_usd, 2)} $/t × ${so(c.tan_tinh, 2)} t`, so(c.tien_thue_usd, 2) + ' USD')}
      ${r(NN.h('st_fee'), `${P.fee_pct}%`, '− ' + so(c.phi_usd, 2) + ' USD')}
      ${r(NN.h('st_over'), `${so(c.vuot_tan, 2)} t × ${P.over_price_usd} $`, '− ' + so(c.tru_vuot_usd, 2) + ' USD')}
      ${r(NN.h('st_adv'), `${so(c.tong_chi_lak)} LAK ÷ ${so(P.rate_usd)}`, '− ' + so(c.ung_truoc_usd, 2) + ' USD')}
      ${r(NN.h('st_net_owner'), `≈ ${so(c.tra_chu_xe_usd * P.rate_usd)} LAK`, so(c.tra_chu_xe_usd, 2) + ' USD', 'tot')}</div>
      <div class="o"><b>${NN.h('trip_profit')}</b>
      ${r(NN.h('do_money'), `${so(P.price_usd, 2)} $/t × ${so(c.tan_tinh, 2)} t`, so(c.doanh_thu_usd, 2) + ' USD')}
      ${r(NN.h('st_hire'), '', '− ' + so(c.tien_thue_usd, 2) + ' USD')}
      ${r(NN.h('trip_profit'), `≈ ${so(c.lai_lak)} LAK`, so(c.lai_usd, 2) + ' USD', 'tot')}</div></div>`;
  }
  function ve() {
    if (!P) { root.querySelector('#hd-than').innerHTML = `<div class="empty muted">${NN.h('no_data')}</div>`; return; }
    const c = P.tinh, m = (k, v, lo) => `<div><span>${NN.h(k)}</span><span ${lo ? 'lang="lo"' : ''}>${v}</span></div>`;
    root.querySelector('#hd-than').innerHTML = `
      <div class="hd-tieu-de">${NN.h('doc_bill')}</div>
      <div class="hd-meta" style="grid-template-columns:1fr;margin-bottom:6px"><div><span>${NN.h('doc_no')}</span><span><b>${esc(P.doc_no)}</b> · ${EPL.ngay(P.doc_date)} · ${tag(P.finance_status)}</span></div></div>
      <div class="hd-meta">
        ${m('truck_type', c.lien_ket ? NN.h('co_joint') + (P.owner_name ? ' · ' + esc(P.owner_name) : '') : 'EPL', true)}${m('goods_type', NN.h(P.goods_type || 'iron_ore'))}
        ${m('brand_model', esc(P.brand_model) || '—')}${m('w_origin', so(P.weight_origin, 2) + ' ' + NN.t('ton'))}
        ${m('truck_no', esc(P.truck_no))}${m('w_dest', (P.weight_dest != null ? so(P.weight_dest, 2) : '—') + ' ' + NN.t('ton'))}
        ${m('plate_head', esc(P.plate_head), true)}${m('price_usd', so(P.price_usd, 2) + ' USD')}
        ${m('plate_trailer', esc(P.plate_trailer), true)}${m('value_usd', '<b>' + so(c.doanh_thu_usd, 2) + ' USD</b>')}
        ${m('driver', esc(P.driver_name), true)}${m('customer', esc(P.customer_name), true)}
        ${m('route', esc(P.origin) + ' → ' + esc(P.destination), true)}${m('ore_bill_no', esc(P.ore_bill_no) || '—')}
      </div>
      ${bang('fuel', 'I. ' + NN.h('bill_fuel'), 'qty_l')}
      ${bang('travel', 'II. ' + NN.h('bill_pay'), 'qty')}
      ${bang('repair', 'III. ' + NN.h('bill_repair'), 'qty')}
      ${bang('other', 'IV. ' + NN.h('bill_other'), 'qty')}
      ${c.lien_ket ? thanhToan(c) : `<div class="hd-tong"><div><span>${NN.h('grand_total')}</span><span>${so(c.tong_chi_lak)} LAK</span></div></div>`}
      <div class="hd-ky"><div><div class="line"></div>${NN.h(c.lien_ket ? 'owner' : 'sg_driver')}</div><div><div class="line"></div>${NN.h('sg_printer')}</div><div><div class="line"></div>${NN.h('sg_payer')}</div></div>`;
  }
  async function chon(id) { P = await API.get('/api/trips/' + id); root.querySelector('#hd-chon').value = id; ve(); }
  EPL.modules['hoa-don'] = {
    async init(r, ctx) {
      root = r; ds = await API.get('/api/trips');
      r.querySelector('#hd-chon').innerHTML = ds.map(p => `<option value="${p.id}">${esc(p.doc_no)} · ${esc(p.truck_no || '')}${p.company === 'joint' ? ' · ' + NN.t('co_joint') : ''}</option>`).join('');
      r.querySelector('#hd-chon').addEventListener('change', e => chon(e.target.value).catch(EPL.baoLoi));
      r.querySelector('#hd-ve').addEventListener('click', () => EPL.di('theo-doi'));
      r.querySelector('#hd-mo').addEventListener('click', () => P && EPL.di('phieu-xuat-xe', { id: P.id }));
      const id = (ctx.tham && ctx.tham.id) || (ds[0] && ds[0].id);
      if (id) await chon(id); else ve();
    },
    onLang() { if (root) ve(); },
  };
})();

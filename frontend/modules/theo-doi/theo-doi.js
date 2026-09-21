/* Theo dõi phiếu vận chuyển — một dòng một phiếu, đủ cột như sheet ໜ້າລາຍງານຂົນສົ່ງ. */
(function () {
  const { API, NN, esc, so, tag } = EPL;
  let root, ds = [];

  function locVaVe() {
    const q = root.querySelector('#td-q').value.trim().toLowerCase();
    const vc = root.querySelector('#td-vc').value, tc = root.querySelector('#td-tc').value, cty = root.querySelector('#td-cty').value;
    const rows = ds.filter(p => (!vc || p.transport_status === vc) && (!tc || p.finance_status === tc) && (!cty || p.company === cty)
      && (!q || [p.doc_no, p.driver_name, p.truck_no, p.customer_name, p.plate_head, p.plate_trailer, p.origin, p.destination, p.ore_bill_no]
        .join(' ').toLowerCase().includes(q)));
    let sVal = 0, sExp = 0, sNet = 0; const d = '<span class="muted">—</span>';
    root.querySelector('#td-than').innerHTML = rows.length ? rows.map((p, i) => {
      const c = p.tinh; sVal += c.doanh_thu_usd; sExp += c.tong_chi_lak; sNet += c.lai_usd;
      const hao = c.hao_hut_pct !== null && c.hao_hut_pct > 1.5 ? `<span class="td-hao" title="${esc(NN.t('w_loss'))}">${so(c.hao_hut_pct, 1)}%</span>` : '';
      return `<tr data-id="${p.id}">
        <td>${i + 1}</td><td class="nowrap">${EPL.ngay(p.doc_date)}</td><td class="nowrap mono"><b>${esc(p.doc_no)}</b></td>
        <td class="mono">${esc(p.ore_bill_no) || d}</td><td class="nowrap" lang="lo">${esc(p.origin)} → ${esc(p.destination)}</td>
        <td>${p.company === 'joint' ? tag('plain', 'co_joint') : 'EPL'}</td><td lang="lo" class="nowrap">${esc(p.driver_name) || d}</td>
        <td lang="lo" class="nowrap">${esc(p.plate_head) || d}</td><td lang="lo" class="nowrap">${esc(p.plate_trailer) || d}</td><td>${esc(p.truck_no) || d}</td>
        <td lang="lo">${esc(p.customer_name) || d}</td><td>${tag('ore', p.goods_type || 'iron_ore')}</td>
        <td class="num">${so(p.weight_origin, 2)}</td><td class="num">${p.weight_dest != null ? so(p.weight_dest, 2) : d}${hao}</td>
        <td class="num tien">${so(p.price_usd, 2)}</td><td class="num tien"><b>${so(c.doanh_thu_usd, 2)}</b></td>
        <td class="num tien">${c.lien_ket ? so(c.tien_thue_usd, 2) : d}</td><td class="num tien">${c.lien_ket ? so(c.phi_usd, 2) + ' $' : d}</td><td class="num tien">${c.lien_ket ? so(c.tru_vuot_usd, 2) + ' $' : d}</td>
        <td class="num">${so(c.chi.fuel)}</td><td class="num">${so(c.chi.travel)}</td><td class="num">${c.chi.repair ? so(c.chi.repair) : d}</td><td class="num">${c.chi.other ? so(c.chi.other) : d}</td><td class="num"><b>${so(c.tong_chi_lak)}</b></td>
        <td class="num tien ${c.lai_usd < 0 ? 'neg' : 'pos'}"><b>${so(c.lai_usd, 2)}</b></td>
        <td>${tag(p.transport_status)}</td><td>${tag(p.finance_status)}</td></tr>`;
    }).join('') : `<tr><td colspan="28" class="empty">${NN.h('no_data')}</td></tr>`;
    root.querySelector('#td-chan').innerHTML = `<tr><td colspan="15">${NN.ghep([{ k: 'total' }, ' · ' + rows.length + ' ', { k: 'trips' }])}</td><td class="num tien">${so(sVal, 2)}</td><td class="tien"></td><td class="tien"></td><td class="tien"></td><td></td><td></td><td></td><td></td><td class="num">${so(sExp)}</td><td class="num tien ${sNet < 0 ? 'neg' : 'pos'}">${so(sNet, 2)}</td><td colspan="2"></td></tr>`;
    root.querySelector('#td-dem').textContent = `${rows.length} / ${ds.length} ${NN.t('rows')}`;
    root.querySelectorAll('#td-than tr[data-id]').forEach(tr => tr.addEventListener('click', () => EPL.di('phieu-xuat-xe', { id: tr.dataset.id })));
  }

  async function tai() {
    const thang = root.querySelector('#td-thang').value;
    ds = await API.get('/api/bao-cao/theo-doi' + (thang ? '?thang=' + thang : ''));
    locVaVe();
  }

  function xuatCSV() {
    const th = [...root.querySelectorAll('.td-bang thead tr:first-child th, .td-bang thead tr:nth-child(2) th')].map(t => t.textContent.trim());
    const dong = [...root.querySelectorAll('#td-than tr[data-id]')].map(tr => [...tr.children].map(td => '"' + td.textContent.trim().replace(/"/g, '""') + '"').join(','));
    const blob = new Blob(['﻿' + th.join(',') + '\n' + dong.join('\n')], { type: 'text/csv;charset=utf-8' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'theo-doi-phieu-van-chuyen.csv'; a.click();
  }

  EPL.modules['theo-doi'] = {
    async init(r, ctx) {
      root = r;
      const t = ctx.tham || {};
      // Mở từ Tổng quan: mang sẵn bộ lọc và tháng đang xem sang đây.
      if (t.transport_status) r.querySelector('#td-vc').value = t.transport_status;
      if (t.finance_status) r.querySelector('#td-tc').value = t.finance_status;
      if (t.cty) r.querySelector('#td-cty').value = t.cty;
      if (t.thang) r.querySelector('#td-thang').value = t.thang;
      if (t.q) r.querySelector('#td-q').value = t.q;
      ['td-q', 'td-vc', 'td-tc', 'td-cty'].forEach(id => r.querySelector('#' + id).addEventListener('input', locVaVe));
      r.querySelector('#td-thang').addEventListener('change', () => tai().catch(EPL.baoLoi));
      r.querySelector('#td-xuat').addEventListener('click', xuatCSV);
      r.querySelector('#td-moi').addEventListener('click', () => EPL.di('phieu-xuat-xe', { moi: 1 }));
      await tai();
      if (t.xuat) xuatCSV();               // nút "Xuất báo cáo" bên Tổng quan bấm thẳng sang đây
    },
    onLang() { if (ds.length) locVaVe(); },
  };
})();

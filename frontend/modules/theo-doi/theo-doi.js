/* Theo dõi phiếu vận chuyển — một dòng một phiếu, đủ cột như sheet ໜ້າລາຍງານຂົນສົ່ງ.
 *
 * TIỀN TỆ. Mỗi phiếu tính theo tiền của hợp đồng phiếu đó (USD · LAK · CNY · THB), nên bảng này có
 * cột **Tiền** nói rõ từng dòng là tiền gì, và dòng tổng cộng RIÊNG TỪNG LOẠI TIỀN thay vì cộng
 * táo với cam. Ai muốn một con số duy nhất thì đổi ô "Quy đổi" sang Kíp hoặc USD — lúc đó mọi dòng
 * quy theo tỷ giá đã khoá trên chính phiếu đó, và dòng tổng còn một con số.
 * Riêng khối chi phí luôn là Kíp: dòng chi vốn đã trộn LAK · VND · THB nên quy về Kíp ngay từ máy chủ.
 */
(function () {
  const { API, NN, esc, so, tien, tag } = EPL;
  let root, ds = [], tyGia = {};

  /** Tỷ giá quy đổi của MỘT phiếu — lấy ngay trên phiếu, không lấy tỷ giá hôm nay. */
  function rate(p, ma) {
    return { USD: p.rate_usd || 22000, THB: p.rate_thb || 700, VND: p.rate_vnd || 1.2,
      CNY: p.rate_cny || 3000, LAK: 1 }[String(ma || 'LAK').toUpperCase()] || 1;
  }
  const quy = () => root.querySelector('#td-quy').value;       // '' = giữ tiền của phiếu
  /** Đổi một số tiền của phiếu p từ `tu` sang tiền đang hiển thị. */
  function ve_tien(p, v, tu) {
    const dich = quy();
    if (v == null) return { v: null, ma: tu };
    if (!dich || dich === tu) return { v, ma: tu };
    return { v: v * rate(p, tu) / rate(p, dich), ma: dich };
  }
  const oTien = (p, v, tu, dam) => {
    const t = ve_tien(p, v, tu);
    if (t.v == null) return '<span class="muted">—</span>';
    const chu = so(t.v, EPL.leTien(t.ma));
    return dam ? `<b>${chu}</b>` : chu;
  };
  /** Cộng dồn theo từng loại tiền; khi đang quy đổi thì tất cả rơi vào một khoá. */
  function cong(tong, p, v, tu) {
    const t = ve_tien(p, v, tu);
    if (t.v == null) return;
    tong[t.ma] = (tong[t.ma] || 0) + t.v;
  }

  function locVaVe() {
    const q = root.querySelector('#td-q').value.trim().toLowerCase();
    const vc = root.querySelector('#td-vc').value, tc = root.querySelector('#td-tc').value, cty = root.querySelector('#td-cty').value;
    const rows = ds.filter(p => (!vc || p.transport_status === vc) && (!tc || p.finance_status === tc) && (!cty || p.company === cty)
      && (!q || [p.doc_no, p.driver_name, p.truck_no, p.customer_name, p.plate_head, p.plate_trailer, p.origin, p.destination, p.ore_bill_no]
        .join(' ').toLowerCase().includes(q)));
    const sVal = {}, sThu = {}, sCon = {}, sNet = {}; let sExp = 0; const d = '<span class="muted">—</span>';
    root.querySelector('#td-than').innerHTML = rows.length ? rows.map((p, i) => {
      const c = p.tinh, ma = c.ccy, mh = c.hire_ccy || ma;
      cong(sVal, p, c.doanh_thu, ma); cong(sThu, p, c.da_thu, ma); cong(sCon, p, c.con_lai, ma);
      cong(sNet, p, c.lai, ma); sExp += c.tong_chi_lak;
      const hao = c.hao_hut_pct !== null && c.hao_hut_pct > 1.5 ? `<span class="td-hao" title="${esc(NN.t('w_loss'))}">${so(c.hao_hut_pct, 1)}%</span>` : '';
      return `<tr data-id="${p.id}">
        <td>${i + 1}</td><td class="nowrap">${EPL.ngay(p.doc_date)}</td><td class="nowrap mono"><b>${esc(p.doc_no)}</b></td>
        <td class="mono">${esc(p.ore_bill_no) || d}</td><td class="nowrap" lang="lo">${esc(p.origin)} → ${esc(p.destination)}</td>
        <td>${p.company === 'joint' ? tag('plain', 'co_joint') : 'EPL'}</td><td lang="lo" class="nowrap">${esc(p.driver_name) || d}</td>
        <td lang="lo" class="nowrap">${esc(p.plate_head) || d}</td><td lang="lo" class="nowrap">${esc(p.plate_trailer) || d}</td><td>${esc(p.truck_no) || d}</td>
        <td lang="lo">${esc(p.customer_name) || d}</td><td>${tag('ore', p.goods_type || 'iron_ore')}</td>
        <td class="num">${so(p.weight_origin, 2)}</td><td class="num">${p.weight_dest != null ? so(p.weight_dest, 2) : d}${hao}</td>
        <td class="mono tien td-ccy">${esc(quy() || ma)}</td>
        <td class="num tien">${oTien(p, p.price, ma)}</td><td class="num tien">${oTien(p, c.doanh_thu, ma, true)}</td>
        <td class="num tien">${c.da_thu ? oTien(p, c.da_thu, ma) : d}</td><td class="num tien ${c.con_lai ? 'neg' : ''}">${c.con_lai ? oTien(p, c.con_lai, ma) : d}</td>
        <td class="num tien">${c.lien_ket ? oTien(p, c.tien_thue, mh) : d}</td><td class="num tien">${c.lien_ket ? oTien(p, c.phi, mh) : d}</td><td class="num tien">${c.lien_ket ? oTien(p, c.tru_vuot, mh) : d}</td>
        <td class="num">${so(c.chi.fuel)}</td><td class="num">${so(c.chi.travel)}</td><td class="num">${c.chi.repair ? so(c.chi.repair) : d}</td><td class="num">${c.chi.other ? so(c.chi.other) : d}</td><td class="num"><b>${so(c.tong_chi_lak)}</b></td>
        <td class="num tien ${c.lai < 0 ? 'neg' : 'pos'}"><b>${oTien(p, c.lai, ma)}</b></td>
        <td>${tag(p.transport_status)}</td><td>${tag(p.finance_status)}</td></tr>`;
    }).join('') : `<tr><td colspan="31" class="empty">${NN.h('no_data')}</td></tr>`;
    const gop = (t) => `<span class="td-gop">${EPL.tienGop(t, '<br>')}</span>`;
    root.querySelector('#td-chan').innerHTML = `<tr><td colspan="15">${NN.ghep([{ k: 'total' }, ' · ' + rows.length + ' ', { k: 'trips' }])}</td>
      <td class="tien"></td><td class="num tien">${gop(sVal)}</td><td class="num tien">${gop(sThu)}</td><td class="num tien">${gop(sCon)}</td>
      <td class="tien"></td><td class="tien"></td><td class="tien"></td><td></td><td></td><td></td><td></td>
      <td class="num">${so(sExp)} LAK</td><td class="num tien">${gop(sNet)}</td><td colspan="2"></td></tr>`;
    root.querySelector('#td-dem').textContent = `${rows.length} / ${ds.length} ${NN.t('rows')}`;
    root.querySelectorAll('#td-than tr[data-id]').forEach(tr => tr.addEventListener('click', () => EPL.di('phieu-xuat-xe', { id: tr.dataset.id })));
  }

  function veChuThich() {
    const o = root.querySelector('#td-ty-gia');
    if (!o) return;
    const ds_ = EPL.TIEN_TE.filter(m => m !== 'LAK' && tyGia[m]).map(m => `1 ${m} = ${so(tyGia[m], m === 'VND' ? 2 : 0)} LAK`);
    o.innerHTML = ds_.length ? `<span class="small muted">${NN.h('rate_on_slip')}: ${esc(ds_.join(' · '))}</span>` : '';
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
      r.querySelector('#td-quy').addEventListener('change', locVaVe);
      r.querySelector('#td-thang').addEventListener('change', () => tai().catch(EPL.baoLoi));
      r.querySelector('#td-xuat').addEventListener('click', xuatCSV);
      r.querySelector('#td-moi').addEventListener('click', () => EPL.di('phieu-xuat-xe', { moi: 1 }));
      try { tyGia = await API.get('/api/rates'); } catch (e) { tyGia = {}; }
      veChuThich();
      await tai();
      if (t.xuat) xuatCSV();               // nút "Xuất báo cáo" bên Tổng quan bấm thẳng sang đây
    },
    onLang() { veChuThich(); if (ds.length) locVaVe(); },
  };
})();

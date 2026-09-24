/* Tất toán tài xế theo tháng — đối tiền ứng với tiền chi thật, chênh thì bù hoặc thu lại.
 *
 * Chênh lệch = đã chi thật − đã ứng.  Dương: công ty chi bù.  Âm: tài xế nộp lại.
 * Bảng KHÔNG tính những khoản công ty trả thẳng nhà cung cấp theo đợt (chipping, thẻ cao tốc…),
 * vì tiền đó chưa bao giờ đi qua tay tài xế.
 */
(function () {
  const { API, NN, esc, so, AUTH } = EPL;
  let root, BANG = null, CHON = null;
  const q = (s) => root.querySelector(s);
  const chotDuoc = () => AUTH.la('expacct', 'cash', 'treasury');

  function veTom() {
    if (!BANG) return;
    const bu = BANG.dong.filter(d => d.chenh_lech_lak > 0).reduce((a, d) => a + d.chenh_lech_lak, 0);
    const lai = BANG.dong.filter(d => d.chenh_lech_lak < 0).reduce((a, d) => a - d.chenh_lech_lak, 0);
    q('#tt-tom').innerHTML = [
      ['tt_advanced', so(BANG.tong_ung_lak), ''],
      ['tt_spent', so(BANG.tong_chi_lak), ''],
      ['tt_pay_more', so(bu), 'pos'],
      ['tt_give_back', so(lai), 'neg'],
    ].map(([k, v, c]) => `<div class="o ${c}"><div class="l">${NN.h(k)}</div><div class="v">${v} <small>LAK</small></div></div>`).join('');
  }

  function veBang() {
    if (!BANG) return;
    q('#tt-than').innerHTML = BANG.dong.length ? BANG.dong.map(d => {
      const ch = d.chenh_lech_lak;
      const nhan = Math.abs(ch) < 1 ? NN.h('tt_even') : ch > 0 ? NN.h('tt_pay_more') : NN.h('tt_give_back');
      return `<tr data-tx="${d.driver_id}" class="${CHON === d.driver_id ? 'chon' : ''}">
        <td lang="lo"><b>${esc(d.driver_name)}</b><div class="small muted">${esc(d.driver_code || '')}</div></td>
        <td class="num">${d.so_phieu}</td>
        <td class="num">${so(d.tong_ung_lak)} LAK</td>
        <td class="num">${so(d.tong_chi_lak)} LAK</td>
        <td class="num ${ch > 0 ? 'pos' : ch < 0 ? 'neg' : ''}"><b>${so(Math.abs(ch))}</b><div class="small muted">${nhan}</div></td>
        <td>${d.da_tat_toan ? EPL.tag('paid', 'tt_done') : EPL.tag('plain', 'v_cho')}</td>
        <td class="no-print">${chotDuoc() ? (d.da_tat_toan
          ? `<button class="btn sm" data-bo="${d.driver_id}">${NN.h('tt_undo')}</button>`
          : `<button class="btn sm ok" data-chot="${d.driver_id}">${NN.h('tt_do')}</button>`) : ''}</td></tr>`;
    }).join('') : `<tr><td colspan="7" class="empty">${NN.h('no_data')}</td></tr>`;

    q('#tt-than').querySelectorAll('tr[data-tx]').forEach(tr => tr.addEventListener('click', e => {
      if (e.target.closest('button')) return;
      CHON = tr.dataset.tx; veBang(); veChiTiet();
    }));
    q('#tt-than').querySelectorAll('[data-chot]').forEach(b => b.addEventListener('click', () => chot(b.dataset.chot)));
    q('#tt-than').querySelectorAll('[data-bo]').forEach(b => b.addEventListener('click', () => boChot(b.dataset.bo)));
  }

  function veChiTiet() {
    const d = BANG && BANG.dong.find(x => x.driver_id === CHON);
    q('#tt-khoi').hidden = !d;
    if (!d) return;
    q('#tt-ten').textContent = d.driver_name;
    q('#tt-ky-hien').textContent = d.period;
    // bảng tháng tải bản gọn (chi_tiet=0): danh sách phiếu của người đang chọn thì lấy riêng, một lần
    if (!d.phieu) {
      q('#tt-phieu').innerHTML = '';
      API.get('/api/tat-toan/' + encodeURIComponent(d.driver_id) + '?ky=' + encodeURIComponent(d.period))
        .then(x => { d.phieu = x.phieu || []; if (CHON === d.driver_id) veChiTiet(); }).catch(EPL.baoLoi);
      return;
    }
    q('#tt-phieu').innerHTML = d.phieu.length ? d.phieu.map(p => `<tr>
      <td class="mono">${esc(p.doc_no)}</td><td>${EPL.ngay(p.out_date)}</td><td>${esc(p.truck_no || '')}</td>
      <td lang="lo">${esc((p.origin || '') + ' → ' + (p.destination || ''))}</td>
      <td class="num">${so(p.chi_lak)} LAK</td></tr>`).join('')
      : `<tr><td colspan="5" class="empty">${NN.h('no_data')}</td></tr>`;
  }

  async function chot(id) {
    const d = BANG.dong.find(x => x.driver_id === id);
    const ch = d.chenh_lech_lak;
    const cau = Math.abs(ch) < 1 ? NN.t('tt_even')
      : (ch > 0 ? NN.t('tt_pay_more') : NN.t('tt_give_back')) + ': <b>' + so(Math.abs(ch)) + ' LAK</b>';
    const ok = await EPL.hoi(NN.t('tt_do'),
      `${NN.t('tt_confirm', { ky: BANG.ky, ten: d.driver_name })}<div style="margin-top:8px">${cau}</div>`, NN.t('tt_do'));
    if (!ok) return;
    try { await API.post('/api/tat-toan', { driver_id: id, period: BANG.ky }); EPL.toast(NN.t('saved'), 'ok'); await tai(); }
    catch (e) { EPL.baoLoi(e); }
  }
  async function boChot(id) {
    const ok = await EPL.hoi(NN.t('tt_undo'), '', NN.t('tt_undo'));
    if (!ok) return;
    try { await API.del('/api/tat-toan/' + id + '?ky=' + BANG.ky); EPL.toast(NN.t('saved'), 'ok'); await tai(); }
    catch (e) { EPL.baoLoi(e); }
  }

  async function tai() {
    BANG = await API.get('/api/tat-toan?chi_tiet=0&ky=' + q('#tt-ky').value);
    veTom(); veBang(); veChiTiet();
  }

  EPL.modules['tat-toan'] = {
    async init(r) {
      root = r;
      // Mặc định là tháng của phiếu mới nhất, không phải tháng hiện tại: dữ liệu demo nằm ở tháng cũ,
      // mở ra thấy bảng trống thì người dùng tưởng hỏng.
      let ky = EPL.thangNay();
      try {
        const ds = await API.get('/api/trips?co=1');     // chỉ cần phiếu mới nhất — đừng tải cả năm
        const ngay = ds.map(p => p.out_date || p.doc_date).filter(Boolean).sort();
        if (ngay.length) ky = ngay[ngay.length - 1].slice(0, 7);
      } catch (e) { /* không lấy được thì cứ tháng này */ }
      q('#tt-ky').value = ky;
      q('#tt-ky').addEventListener('change', () => { CHON = null; tai(); });
      await tai();
    },
    onLang() { if (root) { veTom(); veBang(); veChiTiet(); } },
  };
})();

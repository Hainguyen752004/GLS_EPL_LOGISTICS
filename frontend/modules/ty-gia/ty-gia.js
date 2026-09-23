/* Tỷ giá — ອັດຕາແລກປ່ຽນ.
 *
 * Kíp là tiền gốc của hệ này, nên mỗi thẻ đọc là **"1 <tiền đó> ăn bao nhiêu Kíp"** — khác bản
 * EPL_System bên Việt Nam quy về VNĐ. Bảng này chỉ là tỷ giá MẶC ĐỊNH cho phiếu lập mới: phiếu đã
 * lập khoá tỷ giá riêng của nó, nên sửa ở đây không làm đổi con số trên tờ phiếu đã in. Màn nói rõ
 * điều đó ngay trên đầu, vì hiểu nhầm chỗ này là hiểu nhầm về tiền.
 *
 * API: GET /api/rates/chi-tiet (số đang áp dụng · số lần trước · lịch sử) · PUT /api/rates.
 */
(function () {
  const { API, NN, esc, so, AUTH } = EPL;
  let root, D = { ds: [], lich_su: [] }, nhap = {};

  const suaDuoc = () => AUTH.la('acct', 'rev');
  const le = (ma) => ma === 'VND' ? 2 : 0;          // 1 VND ≈ 1,2 Kíp nên cần số lẻ

  /* ---------------------------------------------------------------- thẻ từng loại tiền */
  function veThe() {
    root.querySelector('#tg-the').innerHTML = D.ds.map(r => {
      const gt = nhap[r.code] !== undefined ? nhap[r.code] : (r.rate_to_lak == null ? '' : r.rate_to_lak);
      const doi = r.doi, co = doi != null && r.truoc;
      return `<div class="card tg-o tg-${esc(r.code.toLowerCase())}">
        <div class="hd"><h4>${NN.h('ccy_' + r.code.toLowerCase())} <span class="tg-ma">${esc(r.code)}</span></h4></div>
        <div class="bd">
          <label class="small muted">${NN.h('rate_input', { m: r.code })}</label>
          <div class="tg-nhap">
            <input class="num" data-ma="${esc(r.code)}" inputmode="decimal" value="${esc(gt)}" ${suaDuoc() ? '' : 'disabled'}>
            <span class="tg-goc">LAK</span>
          </div>
          <div class="tg-dong"><span>${NN.h('rate_now')}</span><b>${r.rate_to_lak == null ? '—' : so(r.rate_to_lak, le(r.code)) + ' LAK'}</b></div>
          <div class="tg-dong"><span>${NN.h('rate_prev')}</span><b>${r.truoc == null ? NN.h('rate_none') : so(r.truoc, le(r.code)) + ' LAK'}</b></div>
          <div class="tg-dong"><span>${NN.h('rate_by')}</span><b>${esc(r.by_user || '—')}${r.cap_nhat ? ' · ' + EPL.ngay(r.cap_nhat.slice(0, 10)) : ''}</b></div>
          <div class="tg-doi ${co ? (doi > 0 ? 'len' : 'xuong') : 'im'}">${co
            ? `${doi > 0 ? '+' : '−'}${so(Math.abs(doi), le(r.code))} LAK · ${doi > 0 ? '+' : '−'}${so(Math.abs(r.doi_pct), 2)}% ${NN.h('rate_vs_prev')}`
            : NN.h('rate_no_change')}</div>
        </div></div>`;
    }).join('');
    root.querySelectorAll('#tg-the input[data-ma]').forEach(el => el.addEventListener('input', () => {
      nhap[el.dataset.ma] = el.value; veMay();
    }));
  }

  /* ---------------------------------------------------------------- máy tính quy đổi */
  function tyGiaDangNhap(ma) {
    const r = D.ds.find(x => x.code === ma);
    const v = nhap[ma] !== undefined && nhap[ma] !== '' ? EPL.doc(nhap[ma]) : (r ? r.rate_to_lak : null);
    return v || null;
  }
  function veMay() {
    const oMa = root.querySelector('#tg-ma');
    if (!oMa.options.length) {
      oMa.innerHTML = ['LAK'].concat(D.ds.map(r => r.code)).map(m => `<option value="${m}">${m}</option>`).join('');
    }
    const ma = oMa.value || 'LAK', n = EPL.doc(root.querySelector('#tg-so').value);
    const rNguon = ma === 'LAK' ? 1 : tyGiaDangNhap(ma);
    const lak = rNguon ? n * rNguon : null;
    const dich = ['LAK'].concat(D.ds.map(r => r.code)).filter(m => m !== ma);
    root.querySelector('#tg-ket').innerHTML = dich.map(m => {
      const r = m === 'LAK' ? 1 : tyGiaDangNhap(m);
      const v = (lak != null && r) ? lak / r : null;
      return `<div class="tg-ket-o"><span class="small muted">${NN.h('rate_to', { m })}</span><b>${v == null ? '—' : EPL.tien(v, m)}</b></div>`;
    }).join('');
  }

  /* ---------------------------------------------------------------- lịch sử */
  function veLichSu() {
    const ds = D.lich_su || [];
    root.querySelector('#tg-than').innerHTML = ds.length ? ds.map(x => {
      const d = x.rate_cu ? x.rate_to_lak - x.rate_cu : null;
      return `<tr>
        <td class="mono"><b>${esc(x.code)}</b></td>
        <td class="num"><b>${so(x.rate_to_lak, le(x.code))} LAK</b></td>
        <td class="num">${x.rate_cu == null ? '—' : so(x.rate_cu, le(x.code)) + ' LAK'}</td>
        <td class="num ${d == null ? '' : (d > 0 ? 'pos' : 'neg')}">${d == null ? '—' : (d > 0 ? '+' : '−') + so(Math.abs(d), le(x.code))}</td>
        <td>${EPL.ngay(x.ap_dung_tu)}</td>
        <td>${NN.h(x.nguon === 'api' ? 'rate_src_api' : 'rate_src_hand')}</td>
        <td>${esc(x.by_user || '—')}</td>
        <td class="small muted">${esc(x.ghi_chu || '')}</td></tr>`;
    }).join('') : `<tr><td colspan="8" class="empty">${NN.h('rate_no_history')}</td></tr>`;
    root.querySelector('#tg-dem').textContent = ds.length ? `${ds.length} ${NN.t('rows')}` : '';
  }

  function veHet() { veThe(); veMay(); veLichSu(); }

  async function tai() { D = await API.get('/api/rates/chi-tiet'); nhap = {}; veHet(); }

  async function luu() {
    const than = {};
    D.ds.forEach(r => {
      const v = nhap[r.code];
      if (v === undefined || v === '') return;
      if (r.rate_to_lak != null && Math.abs(EPL.doc(v) - r.rate_to_lak) < 1e-9) return;   // không đổi thì bỏ qua
      than[r.code] = EPL.doc(v);
    });
    const ma = Object.keys(than);
    if (!ma.length) return EPL.toast(NN.t('rate_nothing'), 'loi');
    const v = await EPL.hopNhap(NN.t('rate_save'), [
      { id: 'ap_dung_tu', label: 'rate_from', type: 'date', value: EPL.homNay() },
      { id: 'ghi_chu', label: 'note', value: '' },
    ], NN.t('save'));
    if (!v) return;
    than.ap_dung_tu = v.ap_dung_tu; than.ghi_chu = v.ghi_chu;
    try {
      await API.put('/api/rates', than);
      EPL.toast(NN.t('saved'), 'ok');
      await tai();
    } catch (e) { EPL.baoLoi(e); }
  }

  EPL.modules['ty-gia'] = {
    async init(r) {
      root = r;
      r.querySelector('#tg-luu').hidden = !suaDuoc();
      r.querySelector('#tg-lam-lai').addEventListener('click', () => { nhap = {}; veHet(); });
      r.querySelector('#tg-luu').addEventListener('click', luu);
      r.querySelector('#tg-so').addEventListener('input', veMay);
      r.querySelector('#tg-ma').addEventListener('change', veMay);
      await tai();
    },
    onLang() { if (root) veHet(); },
    /* Excel: bảng tỷ giá đang dùng + lịch sử đổi — màn vẽ bằng thẻ nên dựng sheet từ dữ liệu */
    xuatExcel() {
      const T = NN.t, L = (v, ma) => EPL.oSo(v, le(ma), 'LAK');
      const ds = [EPL.xuatSheet(T('nav_rates'), [T('cur'), T('rate_now'), T('rate_prev'), T('rate_by'), T('c_date')],
        D.ds.map(r => [r.code, L(r.rate_to_lak, r.code), L(r.truoc, r.code), r.by_user || '', EPL.oNgay(r.cap_nhat)]))];
      if ((D.lich_su || []).length) ds.push(...EPL._xlsx.sheetMacDinh(root));    // bảng lịch sử đang hiện, đầu cột như trên màn
      return ds;
    },
  };
})();

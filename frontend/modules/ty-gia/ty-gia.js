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
  /* Mức đổi (%) của số đang gõ so với số đang dùng — null khi chưa gõ / chưa có số cũ. Quá ngưỡng của máy chủ
     (nguong_doi_lon_pct) thì thẻ cảnh báo ngay khi gõ và lúc lưu phải xác nhận rõ (01/10: USD từng bị đặt 1 Kíp, −99,995 %). */
  const nguong = () => (D && D.nguong_doi_lon_pct) || 20;
  function mucDoi(r) {
    const v = nhap[r.code];
    if (v === undefined || v === '' || !r.rate_to_lak) return null;
    const n = EPL.doc(v);
    return n > 0 ? (n - r.rate_to_lak) / r.rate_to_lak * 100 : null;
  }
  const quaNguong = (r) => { const p = mucDoi(r); return p != null && Math.abs(p) > nguong(); };
  // −99,995 % làm tròn hai số lẻ thành −100,00 % (như thể tỷ giá về 0) — gần 0 và gần 100 thì ba số lẻ
  const chuPhanTram = (p) => { const d = Math.abs(p); return (p > 0 ? '+' : '−') + so(d, d < 1 || (d > 99 && d < 100) ? 3 : 2) + '%'; };
  function veCanh(r) {
    const o = root.querySelector(`.tg-canh[data-ma="${r.code}"]`); if (!o) return;
    o.hidden = !quaNguong(r);
    o.innerHTML = o.hidden ? '' : NN.h('rate_big_live', { p: chuPhanTram(mucDoi(r)) });
  }

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
          <div class="tg-canh" data-ma="${esc(r.code)}" role="alert" hidden></div>
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
      const r = D.ds.find(x => x.code === el.dataset.ma); if (r) veCanh(r);
    }));
    D.ds.forEach(veCanh);
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
    // Một hộp thoại của trang: đổi quá ngưỡng thì khối cảnh báo đỏ đứng đầu (số cũ → số mới · mức đổi) và nút đổi chữ
    // thành "Đúng số này, lưu"; dưới là ngày áp dụng + ghi chú như trước.
    const lon = D.ds.filter(r => than[r.code] !== undefined && quaNguong(r));
    const canh = lon.length ? `<div class="tg-xac-nhan"><p>${NN.h('rate_big_body', { n: nguong() })}</p>
        <ul>${lon.map(r => `<li><b>${esc(r.code)}</b> ${so(r.rate_to_lak, le(r.code))} → <b>${so(than[r.code], le(r.code))}</b> LAK
          <span class="neg">(${chuPhanTram(mucDoi(r))})</span></li>`).join('')}</ul></div>` : '';
    const ok = await EPL.hoi(NN.t(lon.length ? 'rate_big_title' : 'rate_save'), canh
      + `<div class="field"><label>${NN.h('rate_from')}</label><input id="tg-hn-ngay" type="date" value="${esc(EPL.homNay())}"></div>
         <div class="field"><label>${NN.h('note')}</label><input id="tg-hn-ghi-chu" type="text" value=""></div>`,
      NN.t(lon.length ? 'rate_big_ok' : 'save'));
    if (!ok) return;
    than.ap_dung_tu = (document.getElementById('tg-hn-ngay') || {}).value || EPL.homNay();
    than.ghi_chu = (document.getElementById('tg-hn-ghi-chu') || {}).value || '';
    if (lon.length) than.xac_nhan_doi_lon = true;
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

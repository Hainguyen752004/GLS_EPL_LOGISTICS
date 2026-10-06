/* Tiền chuyến & tiền nước tài xế — tổng hợp theo tháng từ mục IV các phiếu (khoản trả cùng lương, xe nhà).
 *
 * Dựng lại 06/10: tiền theo PHIẾU THẬT — một dòng là "đã trả" chỉ khi phiếu chi lương bên kế toán anh Tune đã ghi sổ (máy chủ:
 * routes/bao_cao.tien_tai_xe đọc chi_luong_tune). Trạng thái từng tài xế: "Đã trả (phiếu …, ngày …)" theo từng phiếu đã ghi sổ,
 * phần còn lại "Chờ trả cùng lương". Dải tổng và dòng tổng tách hai phần. Bãi không vào màn này (máy chủ chặn 403).
 *
 * API: GET /api/bao-cao/tien-tai-xe?thang=YYYY-MM → {tu, den, rows[{driver, so_phieu, khoan, tong_lak, da_tra{tong_lak, so_dong,
 * khoan, phieu[{so, ngay, tien_lak}]}, cho_tra{tong_lak, so_dong, khoan}, trang_thai}], tong{tong_lak, da_tra_lak, cho_tra_lak}}.
 */
(function () {
  const { API, NN, esc, so } = EPL;
  const KHOAN = ['x_trip', 'x_water', 'x_phone', 'x_vn', 'x_food'];
  const PHIEU_TOI_DA = 3;                      // quá số này thì gộp "+n" để ô trạng thái không kéo dòng dài
  let root, d = null, LUOT = 0;
  const q = (s) => root.querySelector(s);
  const lak = (v) => `${so(v || 0)} <small>LAK</small>`;

  function oTrangThai(r) {
    if (r.trang_thai === 'none') return '<span class="muted">—</span>';
    const ph = (r.da_tra && r.da_tra.phieu) || [];
    const ds = ph.slice(0, PHIEU_TOI_DA).map(p => `<div class="ttx-dong"><span class="tag paid">${NN.h('ttx_da_tra_phieu', { so: p.so, ngay: EPL.ngay(p.ngay) })}</span>`
      + (ph.length > 1 ? ` <small class="muted">${so(p.tien_lak)}</small>` : '') + '</div>');
    if (ph.length > PHIEU_TOI_DA) ds.push(`<div class="ttx-dong small muted">+${ph.length - PHIEU_TOI_DA}</div>`);
    if ((r.cho_tra || {}).tong_lak > 0) ds.push(`<div class="ttx-dong"><span class="tag unpaid">${NN.h('ttx_cho_tra')}</span></div>`);
    return ds.join('');
  }

  function ve() {
    const rows = d.rows || [], tg = d.tong || {};
    const t = { phieu: 0 }; KHOAN.forEach(k => { t[k] = 0; });
    q('#ttx-ky').textContent = `${EPL.ngay(d.tu)} – ${EPL.ngay(d.den)}`;
    q('#ttx-tong').innerHTML = `
      <div class="kpi"><div class="l">${NN.h('ttx_tong_cung_luong')}</div><div class="v">${lak(tg.tong_lak)}</div></div>
      <div class="kpi ttx-da"><div class="l">${NN.h('ttx_da_tra')}</div><div class="v">${lak(tg.da_tra_lak)}</div><div class="s">${NN.h('ttx_da_tra_d')}</div></div>
      <div class="kpi ttx-cho"><div class="l">${NN.h('ttx_cho_tra')}</div><div class="v">${lak(tg.cho_tra_lak)}</div><div class="s">${NN.h('ttx_cho_tra_d')}</div></div>`;
    q('#ttx-than').innerHTML = rows.length ? rows.map(r => {
      const k = r.khoan || {};
      KHOAN.forEach(x => { t[x] += k[x] || 0; }); t.phieu += r.so_phieu;
      return `<tr><td lang="lo"><b>${esc(r.driver)}</b></td><td class="num">${r.so_phieu}</td>`
        + KHOAN.map(x => `<td class="num">${so(k[x] || 0)}</td>`).join('')
        + `<td class="num"><b>${so(r.tong_lak)}</b></td><td class="num ttx-so-da">${so(r.da_tra.tong_lak)}</td>`
        + `<td class="num ttx-so-cho">${so(r.cho_tra.tong_lak)}</td><td class="ttx-tt">${oTrangThai(r)}</td></tr>`;
    }).join('') : `<tr><td colspan="11" class="empty">${NN.h('no_data')}</td></tr>`;
    q('#ttx-chan').innerHTML = `<tr class="ttx-tong-dong"><td>${NN.h('total')}</td><td class="num">${t.phieu}</td>`
      + KHOAN.map(x => `<td class="num">${so(t[x])}</td>`).join('')
      + `<td class="num">${so(tg.tong_lak || 0)}</td><td class="num ttx-so-da">${so(tg.da_tra_lak || 0)}</td>`
      + `<td class="num ttx-so-cho">${so(tg.cho_tra_lak || 0)}</td><td></td></tr>`;
  }

  async function tai() {
    const luot = ++LUOT, th = q('#ttx-thang').value || EPL.thangNay();
    const x = await API.get('/api/bao-cao/tien-tai-xe?thang=' + encodeURIComponent(th));
    if (luot !== LUOT) return;
    d = x; ve();
  }

  EPL.modules['tien-tai-xe'] = {
    async init(r) {
      root = r; d = null;
      // Mặc định tháng có phiếu gần nhất — cùng lý do với màn Tổng quan.
      let thang = EPL.thangNay();
      try { const ds = await API.get('/api/trips?co=1'); if (ds.length && ds[0].doc_date) thang = ds[0].doc_date.slice(0, 7); } catch (e) { /* giữ tháng này */ }
      q('#ttx-thang').value = thang;
      q('#ttx-thang').addEventListener('change', () => tai().catch(EPL.baoLoi));
      q('#ttx-lam-moi').addEventListener('click', () => tai().catch(EPL.baoLoi));
      await tai();
    },
    onLang() { if (root && d) ve(); },
  };
})();

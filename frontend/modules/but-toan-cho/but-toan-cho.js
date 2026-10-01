/* Bút toán chờ gửi — khoản sổ kế toán phải ghi mà KHÔNG đi qua tiền (chủ dự án 01/10/2026).
 *
 * Nguồn: thue_xe (khoá phiếu xe thuê: Nợ 621 / Có 4022 = tiền thuê) · no_ncc (khoá phiếu: dòng chi ghi nợ nhà cung cấp …/4021) ·
 * tat_toan (quyết toán tạm ứng QT_TU Nợ 625 / Có 1601) · ban_chu_xe (hàng bán cho chủ xe trừ vào tiền trả: Nợ 4022 / Có 707).
 * Gửi sang hệ anh Tune (services/gui_but_toan_tune.py) khi máy chủ bật cờ QLSX_GUI_BUT_TOAN (`co_duong_gui`): ghi xong tự gửi;
 * màn có nút Gửi (một bản: chờ gửi → gửi, chờ đảo → đảo), Gửi hết, Cập nhật (hỏi lại số chứng từ). Cờ tắt: CHỈ XEM như cũ.
 * Đọc GET /api/but-toan-cho (routes/de_nghi.py) — vai KT Thu/Chi VC, KT Chi phí VC, Sếp, máy chủ chặn vai khác.
 */
(function () {
  const { API, NN, esc, so } = EPL;

  let root, DS = [], CHON = null, loc = '', tim = '', hen = null, LUOT = 0, PHIEU = null, TEN = {}, GUI = false;
  const guiDuoc = () => GUI && EPL.AUTH.la('acct', 'expacct');      // Sếp luôn qua (AUTH.la) — cùng danh sách máy chủ
  const q = (s) => root.querySelector(s);
  const NGUON = ['thue_xe', 'no_ncc', 'tat_toan', 'ban_chu_xe'];
  const LOC = ['', 'cho_gui', 'da_gui', 'huy', 'can_dao'];
  const NHAN_LOC = { '': 'all', cho_gui: 'dt_st_cho_gui', da_gui: 'dt_st_da_gui', huy: 'v_huy', can_dao: 'btc_can_dao' };
  const nhanNguon = (n) => (NGUON.includes(n) ? 'btc_nguon_' + n : n);
  // nguồn sinh từ MỘT phiếu xuất xe (lúc khoá): phiếu bị xoá thì trip_id về null (khoá ngoại SET NULL) — còn ma_nguon
  const nhanKy = (v) => (/^\d{4}-\d{2}$/.test(v || '') ? v.slice(5, 7) + '/' + v.slice(0, 4) : (v || ''));   // 2026-10 → 10/2026
  const tuPhieu = (b) => b.trip_id || b.nguon === 'thue_xe' || b.nguon === 'no_ncc';
  const tien = (v, ma) => `${so(v, ['LAK', 'VND'].includes(ma) ? 0 : 2)} <small>${esc(ma || '')}</small>`;

  /** Trạng thái hiện của một bút toán: chờ đảo đứng trước (đã gửi mà nguồn bị huỷ). */
  function trangThai(b) {
    if (b.can_dao) return { k: 'can_dao', nhan: 'btc_can_dao', mau: 'unpaid' };
    if (b.status === 'da_gui') return { k: 'da_gui', nhan: 'dt_st_da_gui', mau: 'paid' };
    if (b.status === 'huy') return { k: 'huy', nhan: 'v_huy', mau: 'plain' };
    return { k: 'cho_gui', nhan: 'dt_st_cho_gui', mau: 'transit' };
  }
  /** Tổng theo từng tiền của các dòng (bút toán nhiều tiền không cộng lẫn). */
  function tongTien(ds) {
    const t = {};
    ds.forEach(b => (b.dong || []).forEach(d => { t[d.ccy] = (t[d.ccy] || 0) + (d.tien || 0); }));
    return t;
  }
  const chuoiTien = (t) => Object.keys(t).length ? Object.entries(t).map(([m, v]) => tien(v, m)).join(' · ') : '—';
  /** Tên tài khoản dưới mã: tiếng Lào lấy nguyên tên danh mục anh Khampla (máy chủ gửi `no_ten_lo`), VI + ລາວ hai dòng. */
  function tenTK(d, ve) {
    const vi = d[ve + '_ten'] || '', lo = d[ve + '_ten_lo'] || '';
    if (NN.lang === 'lo') return esc(lo || vi);
    if (NN.lang === 'both' && lo && lo !== vi) return esc(vi) + '<span class="lo-sub" lang="lo">' + esc(lo) + '</span>';
    return esc(vi || lo);
  }

  function locDs() {
    const t = tim.toLowerCase();
    return DS.filter(b => (!loc || trangThai(b).k === loc)
      && (!t || [b.trip_doc_no, b.source_ref, b.dien_giai, ...(b.dong || []).map(d => d.dien_giai)].join(' ').toLowerCase().includes(t)));
  }

  /** Tên đối tượng: tra danh mục bên em theo loại + mã; không thấy thì mã. */
  function tenDoiTuong(dt) {
    if (!dt) return '—';
    const nhan = { chu_xe: 'owner', ncc: 'supplier', tai_xe: 'driver', khach: 'customer' }[dt.loai];
    const ten = (TEN[dt.loai] || {})[dt.ref_id];
    return `<span class="muted">${nhan ? NN.h(nhan) : esc(dt.loai)}</span> · <span lang="lo">${esc(ten || dt.ref_id)}</span>`;
  }
  /** Chứng từ gốc: phiếu xuất xe (mở được), bản chốt tất toán (mở màn Tất toán đúng kỳ), phiếu bán ở kho. */
  function goc(b) {
    // phiếu gốc đã bị xoá (máy chủ không còn số phiếu): nói thẳng, đừng bày mã máy của phiếu ra (rà 01/10)
    if (tuPhieu(b)) return b.trip_id && b.trip_doc_no ? `<a href="#/phieu-xuat-xe?id=${esc(b.trip_id)}" class="mono">${esc(b.trip_doc_no)}</a>`
      : `<span class="muted">${NN.h('btc_phieu_da_xoa')}</span>`;
    if (b.nguon === 'tat_toan') {
      const [tx, ky] = String(b.ma_nguon || '').split(':');
      return `<a href="#/tat-toan?ky=${esc(ky || '')}&tx=${esc(tx || '')}">${NN.h('nav_settle')} ${esc(nhanKy(ky))}</a>`;
    }
    const r = (b.dong || []).map(d => d.ref).find(Boolean);
    return `<span class="mono">${esc(r || b.ma_nguon)}</span>`;
  }

  /** Chứng từ gốc dạng chữ cho dòng phụ của danh sách: số phiếu · "Tất toán tài xế 2026-10" · phiếu đã xoá. Mã tham chiếu gửi
   *  bên kế toán (EPLLAO-tat_toan-…) chỉ hiện ở khung chi tiết — ở danh sách nó là chuỗi máy bị cắt cụt (rà 01/10). */
  function nhanGoc(b) {
    if (b.trip_doc_no) return esc(b.trip_doc_no);
    if (b.nguon === 'tat_toan') return NN.h('nav_settle') + ' ' + esc(nhanKy(String(b.ma_nguon || '').split(':')[1]));
    if (tuPhieu(b)) return NN.h('btc_phieu_da_xoa');
    return esc(b.source_ref || '');
  }

  /* ---------------------------------------------------------------- lọc + dải tổng */
  function veLoc() {
    const dem = {}; DS.forEach(b => { const k = trangThai(b).k; dem[k] = (dem[k] || 0) + 1; });
    q('#btc-loc').innerHTML = LOC.map(k => `<button type="button" data-loc="${k}" class="${loc === k ? 'on' : ''}">
      <span>${NN.h(NHAN_LOC[k])}</span><b>${k ? (dem[k] || 0) : DS.length}</b></button>`).join('');
    q('#btc-loc').querySelectorAll('button').forEach(b => b.addEventListener('click', () => { loc = b.dataset.loc; veHet(); }));
  }
  function veTong() {
    const cho = DS.filter(b => trangThai(b).k === 'cho_gui'), dao = DS.filter(b => b.can_dao);
    q('#btc-tong').innerHTML = (PHIEU ? `<span class="btc-loc-phieu">${NN.h('btc_loc_phieu', { doc: PHIEU.doc || PHIEU.id })}
        <button type="button" id="btc-bo-phieu" aria-label="×">×</button></span>` : '')
      + [['btc_tong_cho', `${cho.length}`, cho.length ? 'canh' : ''], ['amount', chuoiTien(tongTien(cho)), ''],
         ['btc_can_dao', `${dao.length}`, dao.length ? 'canh' : '']]
        .map(([k, v, c]) => `<div class="o ${c}"><div class="l">${NN.h(k)}</div><div class="v">${v}</div></div>`).join('')
      + `<div class="btc-bao"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8v.01"/></svg>
        <span>${NN.h(GUI ? 'btc_note_bat' : 'btc_note')}</span></div>`;
    const bo = q('#btc-bo-phieu');
    if (bo) bo.addEventListener('click', () => { PHIEU = null; history.replaceState(null, '', '#/but-toan-cho'); tai(); });
  }

  /* ---------------------------------------------------------------- danh sách */
  function veDs() {
    const ds = locDs();
    q('#btc-ds').innerHTML = ds.length ? ds.map(b => {
      const s = trangThai(b);
      return `<button type="button" class="btc-o st-${b.status} ${b.can_dao ? 'dao' : ''} ${CHON === b.id ? 'chon' : ''}" data-id="${esc(b.id)}">
        <span class="ten">${NN.h(nhanNguon(b.nguon))}</span>
        <span class="tien">${chuoiTien(tongTien([b]))}</span>
        <span class="phu">${EPL.ngay(b.ngay)} · ${nhanGoc(b)}${b.so_ben_ke_toan ? ' · <span class="mono">' + esc(b.so_ben_ke_toan) + '</span>' : ''}</span>
        <span class="tt">${EPL.tag(s.mau, s.nhan)}${b.error_code && b.status !== 'huy' ? ' <span class="tag unpaid" title="' + esc(b.loi_gui || '') + '">⚠</span>' : ''}</span>
        <span class="phu dg" lang="lo">${esc(b.dien_giai || '')}</span></button>`;
    }).join('') : `<div class="btc-trong">${NN.h('btc_trong')}</div>`;
    q('#btc-ds').querySelectorAll('[data-id]').forEach(b => b.addEventListener('click', () => { CHON = b.dataset.id; veDs(); veXem(); }));
  }

  /* ---------------------------------------------------------------- một bút toán */
  /** Tờ / tháng đang xem ghi vào địa chỉ (rà 01/10): bấm "Mở phiếu" sang Phiếu xuất xe rồi Quay lại, hay tải lại trang, là về
   *  đúng tờ đó — trước đây màn mở lại từ đầu, tờ vừa xem như biến mất. init đã đọc sẵn các tham số này. replaceState: không
   *  thêm bước lịch sử, không bắn hashchange (khung không nạp lại màn); màn đã bị rời (gốc tháo khỏi trang) thì thôi. */
  function ghiDiaChi(ts) {
    if (!root || !root.isConnected) return;
    [...ts.keys()].forEach(k => { if (!ts.get(k)) ts.delete(k); });
    const moi = '#/but-toan-cho' + (ts.toString() ? '?' + ts : '');
    if (location.hash !== moi) history.replaceState(null, '', moi);
  }

  function veXem() {
    const o = q('#btc-xem'), b = DS.find(x => x.id === CHON);
    ghiDiaChi(new URLSearchParams({ ky: q('#btc-ky').value || '', nguon: q('#btc-nguon').value || '', trip_id: PHIEU ? PHIEU.id : '', id: b ? b.id : '' }));
    const bang = (rows) => `<div class="tbl-wrap btc-dong"><table class="tbl tbl-compact">
      <thead><tr><th>#</th><th>${NN.h('btc_no')}</th><th>${NN.h('btc_co')}</th><th class="num">${NN.h('amount')}</th>
        <th>${NN.h('btc_doi_tuong')}</th><th>${NN.h('btc_dien_giai')}</th></tr></thead>
      <tbody>${rows}</tbody></table></div>`;
    if (!b) { o.innerHTML = bang(`<tr><td colspan="6" class="empty">${NN.h('btc_trong')}</td></tr>`); return; }
    const s = trangThai(b);
    const rows = (b.dong || []).map((d, i) => `<tr>
      <td>${i + 1}</td>
      <td><span class="ma">${esc(d.no)}</span><span class="ten" lang="lo">${tenTK(d, 'no')}</span></td>
      <td><span class="ma">${esc(d.co)}</span><span class="ten" lang="lo">${tenTK(d, 'co')}</span></td>
      <td class="num">${tien(d.tien, d.ccy)}${d.ccy_goc ? `<small>${NN.h('btc_tien_goc')}: ${so(d.tien_goc, ['LAK', 'VND'].includes(d.ccy_goc) ? 0 : 2)} ${esc(d.ccy_goc)}</small>` : ''}
        ${d.ccy !== 'LAK' && d.tien_lak ? `<small>≈ ${so(d.tien_lak)} LAK</small>` : ''}</td>
      <td>${d.doi_tuong || !d.doi_tuong_no ? tenDoiTuong(d.doi_tuong) : ''}${d.doi_tuong_no ? `${d.doi_tuong ? '<br>' : ''}${tenDoiTuong(d.doi_tuong_no)}` : ''}</td>
      <td lang="lo">${esc(d.dien_giai || '')}${d.canh_bao_tk ? `<div class="canh">⚠ ${NN.h('btc_canh_tk')}: ${esc(d.canh_bao_tk.join(', '))}</div>` : ''}</td></tr>`).join('');
    o.innerHTML = `<div class="btc-dau">
        <div><h3>${NN.h(nhanNguon(b.nguon))}</h3><div class="small muted mono">${esc(b.source_ref || '')}</div></div>
        <div class="grow"></div>${EPL.tag(s.mau, s.nhan)}
        ${guiDuoc() && (b.status === 'cho_gui' || b.can_dao) ? `<button type="button" class="btn sm primary" data-btc="gui">${NN.h('btc_gui')}</button>` : ''}
        ${guiDuoc() && b.status === 'da_gui' && !b.can_dao ? `<button type="button" class="btn sm" data-btc="cap-nhat">${NN.h('ck_cap_nhat')}</button>` : ''}</div>
      <div class="btc-the">
        <div><span>${NN.h('btc_ngay')}</span><b>${EPL.ngay(b.ngay)}</b></div>
        <div><span>${NN.h('btc_goc')}</span><b>${goc(b)}</b></div>
        <div><span>${NN.h('amount')}</span><b>${chuoiTien(tongTien([b]))}</b></div>
        <div><span>${NN.h(b.so_ben_ke_toan || b.ma_ben_ke_toan ? 'btc_so_kt' : 'status')}</span><b>${b.so_ben_ke_toan || b.ma_ben_ke_toan
          ? `<span class="mono">${esc(b.so_ben_ke_toan || b.ma_ben_ke_toan)}</span>` : NN.h(b.status === 'huy' ? 'v_huy' : GUI ? 'dt_st_cho_gui' : 'btc_cho_api')}</b></div>
      </div>
      ${b.dien_giai ? `<div class="small" lang="lo">${esc(b.dien_giai)}</div>` : ''}
      ${bang(rows || `<tr><td colspan="6" class="empty">${NN.h('no_data')}</td></tr>`)}
      <div class="btc-chan">
        <span>${NN.h('btc_lap')}: <b>${EPL.ngayGio(b.created_at)}</b>${b.created_by ? ` · <span lang="lo">${esc(b.created_by)}</span>` : ''}</span>
        ${b.huy_luc ? `<span>${NN.h('btc_huy_boi')}: <b lang="lo">${esc(b.huy_by || '')}</b> · ${EPL.ngayGio(b.huy_luc)}</span>` : ''}
        ${b.loi_gui && b.status !== 'huy' ? `<span class="neg">${b.attempts ? '#' + b.attempts + ' · ' : ''}${esc(b.loi_gui)}</span>` : ''}
      </div>`;
    o.querySelectorAll('[data-btc]').forEach(n => n.addEventListener('click', () => viec(b, n.dataset.btc, n)));
  }

  /** Gửi / đảo / hỏi lại MỘT bút toán, hoặc Gửi hết — rồi tải lại (lỗi bên kế toán hiện ngay, bản ghi giữ lỗi). */
  async function viec(b, v, nut) {
    if (nut) nut.disabled = true;
    try {
      if (v === 'gui-het') {
        const r = await API.post('/api/but-toan-cho/gui-het', {});
        EPL.toast(`${NN.t('btc_gui_het')}: ${r.da_gui} · ${NN.t('btc_can_dao')} ${r.da_dao}` + (r.loi ? ` · ⚠ ${r.loi}${r.chi_tiet_loi && r.chi_tiet_loi[0] ? ' — ' + r.chi_tiet_loi[0].loi : ''}` : ''),
          r.loi ? 'loi' : 'ok');
      } else {
        await API.post(`/api/but-toan-cho/${encodeURIComponent(b.id)}/${v}`, {});
        EPL.toast(NN.t(v === 'gui' ? 'dt_st_da_gui' : 'ck_cap_nhat'), 'ok');
      }
    } catch (e) { EPL.baoLoi(e); }
    await tai();
  }

  /* ---------------------------------------------------------------- cao vừa cửa sổ */
  let henCao = null;
  function datCao() {
    const ds = root && root.querySelector('.btc-ds');
    if (!ds || !ds.isConnected) return;
    if (root.classList.contains('mod-dang-tai')) { clearTimeout(henCao); henCao = setTimeout(datCao, 120); return; }
    const tl = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--ty-le')) || 1;
    const le = (parseFloat(getComputedStyle(document.getElementById('noi-dung')).paddingBottom) || 0) * tl;
    const cao = (window.innerHeight - (ds.getBoundingClientRect().top + window.scrollY) - le) / tl;
    root.style.setProperty('--btc-cao', Math.max(300, Math.floor(cao)) + 'px');
  }
  const khiDoiCo = () => { clearTimeout(henCao); henCao = setTimeout(datCao, 150); };

  /** Tiêu đề màn do khung vẽ trước khi nạp màn — từ điển chung chưa có khoá thì vẽ lại sau khi nạp (khoá dự phòng ở trên). */
  function veTieuDe() { const h = document.getElementById('pageTitle'); if (h) h.innerHTML = NN.h('title_but_toan_cho'); }

  function veHet() {
    const ds = locDs();
    if (!ds.some(b => b.id === CHON)) CHON = ds[0] ? ds[0].id : null;
    veLoc(); veTong(); veDs(); veXem();
    datCao();
  }

  async function tai() {
    const luot = ++LUOT, p = new URLSearchParams({ gioi_han: 1000 });
    const ky = q('#btc-ky').value, nguon = q('#btc-nguon').value;
    if (ky) p.set('thang', ky);
    if (nguon) p.set('nguon', nguon);
    if (PHIEU) p.set('trip_id', PHIEU.id);
    let g;
    try { g = await API.get('/api/but-toan-cho?' + p.toString()); } catch (e) { if (luot === LUOT) EPL.baoLoi(e); g = { ds: [] }; }
    if (luot !== LUOT) return;
    DS = g.ds || [];
    GUI = !!g.co_duong_gui;
    const het = q('#btc-gui-het'); if (het) het.hidden = !guiDuoc();
    if (PHIEU && !PHIEU.doc) PHIEU.doc = (DS.find(b => b.trip_doc_no) || {}).trip_doc_no;
    veHet();
  }

  /** Tên đối tượng cho cột Đối tượng — bốn danh mục, mỗi cái một lượt; hỏng thì hiện mã. */
  async function napTen() {
    const lay = async (duong, loai, ten) => { try { (await API.get(duong)).forEach(x => { (TEN[loai] = TEN[loai] || {})[x.id] = x[ten]; }); } catch (e) { /* hiện mã */ } };
    await Promise.all([lay('/api/owners', 'chu_xe', 'name'), lay('/api/suppliers', 'ncc', 'name'), lay('/api/drivers', 'tai_xe', 'name'),
      lay('/api/customers', 'khach', 'name')]);
  }

  function veNguon() {
    const s = q('#btc-nguon'), cu = s.value;
    s.innerHTML = `<option value="">${esc(NN.t('btc_tat_ca_nguon'))}</option>` + NGUON.map(n => `<option value="${n}">${esc(NN.t(nhanNguon(n)))}</option>`).join('');
    s.value = cu;
  }

  EPL.modules['but-toan-cho'] = {
    async init(r, ctx) {
      root = r; DS = []; CHON = null; loc = ''; tim = ''; TEN = {};
      veTieuDe();
      const t = (ctx && ctx.tham) || {};
      PHIEU = t.trip_id ? { id: t.trip_id, doc: t.doc || null } : null;
      if (t.id) CHON = t.id;
      veNguon();
      if (t.ky) q('#btc-ky').value = t.ky;
      if (t.nguon) q('#btc-nguon').value = t.nguon;
      q('#btc-ky').addEventListener('change', () => { CHON = null; tai(); });
      q('#btc-nguon').addEventListener('change', () => { CHON = null; tai(); });
      q('#btc-lam-moi').addEventListener('click', () => tai());
      q('#btc-gui-het').addEventListener('click', (e) => viec(null, 'gui-het', e.currentTarget));
      q('#btc-tim').addEventListener('input', (e) => { clearTimeout(hen); hen = setTimeout(() => { tim = e.target.value.trim(); veHet(); }, 200); });
      window.removeEventListener('resize', khiDoiCo); window.addEventListener('resize', khiDoiCo);
      await Promise.all([napTen(), tai()]);
      veXem();
    },
    onLang() { if (root) { veTieuDe(); veNguon(); veHet(); } },
    destroy() { window.removeEventListener('resize', khiDoiCo); clearTimeout(henCao); clearTimeout(hen); },
    xuatExcel() {
      const T = NN.t, rows = [];
      locDs().forEach(b => (b.dong || []).forEach((d, i) => rows.push([EPL.oNgay ? EPL.oNgay(b.ngay) : b.ngay, T(nhanNguon(b.nguon)),
        b.trip_doc_no || b.ma_nguon, T(trangThai(b).nhan), i + 1, d.no, d.co, EPL.oSo(d.tien, ['LAK', 'VND'].includes(d.ccy) ? 0 : 2), d.ccy,
        d.doi_tuong ? (T({ chu_xe: 'owner', ncc: 'supplier', tai_xe: 'driver', khach: 'customer' }[d.doi_tuong.loai] || d.doi_tuong.loai)
          + ' · ' + ((TEN[d.doi_tuong.loai] || {})[d.doi_tuong.ref_id] || d.doi_tuong.ref_id)) : '', d.dien_giai || '', b.source_ref || ''])));
      return [EPL.xuatSheet(T('btc_title'), [T('btc_ngay'), T('source'), T('btc_goc'), T('status'), '#', T('btc_no'), T('btc_co'),
        T('amount'), T('ccy'), T('btc_doi_tuong'), T('btc_dien_giai'), 'Ref'], rows)];
    },
  };
})();

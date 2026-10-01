/* Tất toán tài xế theo tháng — đối tiền ứng với tiền chi thật, chênh thì bù hoặc thu lại (dựng lại 01/10).
 *
 * Chênh lệch = đã chi thật − đã ứng.  Dương: công ty chi bù (phiếu chi "Chi khác" TT_CHI bên kế toán anh Tune).
 * Âm: tài xế nộp lại (phiếu thu "Thu khác" TT_THU).  Dưới 1 Kíp: không lập phiếu, chốt xong ngay.
 * Chốt cũng ghi quyết toán QT_TU (Nợ 625 / Có 1601 = đã chi thật) thành bút toán chờ gửi. Thủ quỹ bên đó chi / thu rồi GHI
 * SỔ; máy chủ hỏi lại → bản chốt "xong". Số tính và luật ở routes/tat_toan.py, tiền ở services/chi_tat_toan_tune.py.
 *
 * Ai làm gì (bảng Nhiệm Vụ, bước 19): KT Chi phí VC (và Sếp) chốt · bỏ chốt · gửi lại; quỹ tiền mặt / ngân hàng xem, cập nhật.
 */
(function () {
  const { API, NN, esc, so, AUTH } = EPL;
  let root, BANG = { dong: [] }, CHON = null, CT = {}, loc = '', tim = '', hen = null, LUOT = 0, TU_DONG = false, BAO = null;
  const q = (s) => root.querySelector(s);
  const chotDuoc = () => AUTH.la('expacct');          // Sếp luôn qua (AUTH.la)
  const LOC = ['', 'chua', 'cho', 'loi', 'xong'];
  const lak = (v) => `${so(v)} <small>LAK</small>`;
  const nhanThang = (v) => (v ? v.slice(5, 7) + '/' + v.slice(0, 4) : '');
  const thangTruoc = (v) => { const [y, m] = v.split('-').map(Number); const d = new Date(y, m - 2, 1);
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0'); };

  /* ---------------------------------------------------------------- trạng thái một dòng */
  /** {k: khoá lọc, nhan: khoá dịch, mau: lớp nhãn} — chưa chốt · chờ chi · lỗi · xong. */
  function trangThai(d) {
    const t = d.tat_toan;
    if (!d.da_tat_toan || !t) return { k: 'chua', nhan: 'tt_chua_chot', mau: 'plain' };
    if (t.status === 'xong') return { k: 'xong', nhan: 'tt_xong', mau: 'paid' };
    const p = t.phieu_ke_toan || {};
    if (p.status === 'loi') return { k: 'loi', nhan: p.error_code === 'PHIEU_CHI_MAT' ? 'ck_phieu_mat' : 'ck_loi_ngan', mau: 'unpaid' };
    return { k: 'cho', nhan: 'tt_cho_chi', mau: 'transit' };
  }
  const chieu = (ch) => (Math.abs(ch) < 1 ? 'tt_even' : ch > 0 ? 'tt_pay_more' : 'tt_give_back');
  const lop = (ch) => (Math.abs(ch) < 1 ? '' : ch > 0 ? 'pos' : 'neg');

  function locDs() {
    const t = tim.toLowerCase();
    return BANG.dong.filter(d => (!loc || trangThai(d).k === loc)
      && (!t || ((d.driver_name || '') + ' ' + (d.driver_code || '')).toLowerCase().includes(t)));
  }

  /* ---------------------------------------------------------------- thanh lọc + dải tổng */
  function veLoc() {
    const dem = {}; BANG.dong.forEach(d => { const k = trangThai(d).k; dem[k] = (dem[k] || 0) + 1; });
    const nhan = { '': 'all', chua: 'tt_chua_chot', cho: 'tt_cho_chi', loi: 'ck_loi_ngan', xong: 'tt_xong' };
    q('#tt2-loc').innerHTML = LOC.map(k => `<button type="button" data-loc="${k}" class="${loc === k ? 'on' : ''}">
      <span>${NN.h(nhan[k])}</span><b>${k ? (dem[k] || 0) : BANG.dong.length}</b></button>`).join('');
    q('#tt2-loc').querySelectorAll('button').forEach(b => b.addEventListener('click', () => { loc = b.dataset.loc; veHet(); }));
  }
  function veTong() {
    const ds = BANG.dong;
    const bu = ds.filter(d => d.chenh_lech_lak >= 1).reduce((a, d) => a + d.chenh_lech_lak, 0);
    const lai = ds.filter(d => d.chenh_lech_lak <= -1).reduce((a, d) => a - d.chenh_lech_lak, 0);
    const cho = ds.filter(d => trangThai(d).k === 'cho').length, loi = ds.filter(d => trangThai(d).k === 'loi').length;
    q('#tt2-tong').innerHTML = [
      ['tt_advanced', lak(BANG.tong_ung_lak), ''],
      ['tt_spent', lak(BANG.tong_chi_lak), ''],
      ['tt_pay_more', lak(bu), 'pos'],
      ['tt_give_back', lak(lai), 'neg'],
      ['tt_cho_chi', `${cho}${loi ? ` <small class="neg">· ${loi} ${esc(NN.t('ck_loi_ngan').toLowerCase())}</small>` : ''}`, cho || loi ? 'canh' : ''],
    ].map(([k, v, c]) => `<div class="o ${c}"><div class="l">${NN.h(k)}</div><div class="v">${v}</div></div>`).join('')
      + (BAO ? `<div class="tt2-bao"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8v.01"/></svg>
        <span>${NN.h('thang_trong_dang_xem', { trong: nhanThang(BAO.trong), xem: nhanThang(BAO.xem) })}</span></div>` : '')
      + `<p class="small muted tt2-note">${NN.h('tt_note')}</p>`;
  }

  /* ---------------------------------------------------------------- danh sách tài xế */
  function veDs() {
    const ds = locDs();
    q('#tt2-ds').innerHTML = ds.length ? ds.map(d => {
      const s = trangThai(d), ch = d.chenh_lech_lak, lech = d.tat_toan && d.tat_toan.lech;
      return `<button type="button" class="tt2-o st-${s.k} ${CHON === d.driver_id ? 'chon' : ''}" data-tx="${esc(d.driver_id)}">
        <span class="ten" lang="lo">${esc(d.driver_name)}</span>
        <span class="tien ${lop(ch)}">${so(Math.abs(ch))}</span>
        <span class="phu">${esc(d.driver_code || '')} · ${d.so_phieu} ${esc(NN.t('tt_slips').toLowerCase())}</span>
        <span class="tt">${EPL.tag(s.mau, s.nhan)}${lech ? ' ' + EPL.tag('partial', 'tt_lech') : ''}</span>
        <span class="phu">${NN.h(chieu(ch))}</span></button>`;
    }).join('') : `<div class="tt2-trong">${NN.h('no_data')}</div>`;
    q('#tt2-ds').querySelectorAll('[data-tx]').forEach(b => b.addEventListener('click', () => { CHON = b.dataset.tx; veDs(); veXem(); }));
  }

  /* ---------------------------------------------------------------- một tài xế */
  function nutCua(d) {
    const s = trangThai(d), t = d.tat_toan || {}, p = t.phieu_ke_toan, qt = t.quyet_toan || {};
    const nut = [];
    if (s.k === 'chua') {
      if (chotDuoc() && d.so_phieu) nut.push(['chot', 'primary', 'tt_chot']);
    } else {
      if (p && p.status === 'da_gui') nut.push(['cap-nhat', '', 'ck_cap_nhat']);
      if (p && p.status === 'loi' && chotDuoc()) nut.push(['gui-lai', 'warn', 'tt_gui_lai']);
      // bỏ chốt chỉ khi phiếu bên kế toán chưa ghi sổ và QT_TU chưa gửi — máy chủ vẫn chặn lại lần nữa
      if (chotDuoc() && !(p && p.status === 'da_chi') && qt.status !== 'da_gui') nut.push(['bo', 'danger', 'tt_bo_chot']);
    }
    return nut.map(([v, c, k]) => `<button type="button" class="btn ${c}" data-viec="${v}">${NN.h(k)}</button>`).join('');
  }

  function veXem() {
    const o = q('#tt2-xem');
    const d = BANG.dong.find(x => x.driver_id === CHON);
    if (!d) { o.innerHTML = `<div class="tt2-trong">${NN.h('no_data')}</div>`; return; }
    const c = CT[d.driver_id];                 // bản đầy đủ (phiếu trong kỳ, tạm ứng chờ, QT_TU) — tải riêng
    const x = c || d, t = x.tat_toan, ch = x.chenh_lech_lak, s = trangThai(x);
    const canh = [];
    if (t && t.lech) canh.push(`<div class="tt2-canh">${NN.h('tt_lech')}</div>`);
    if (c && c.tam_ung_cho && c.tam_ung_cho.length) {
      canh.push(`<div class="tt2-canh">${NN.h('tt_tam_ung_cho')}: ${c.tam_ung_cho.map(u =>
        `<a href="#/phieu-xuat-xe?id=${esc(u.trip_id)}" class="mono">${esc(u.doc_no || u.trip_id)}</a>${u.document_no ? ` (${esc(u.document_no)})` : ''}`).join(', ')}</div>`);
    }
    o.innerHTML = `<div class="tt2-dau">
        <div><h3 lang="lo">${esc(x.driver_name)}</h3><div class="small muted">${esc(x.driver_code || '')} · ${NN.h('tt_period')} ${nhanThang(x.period)}</div></div>
        <div class="grow"></div>${EPL.tag(s.mau, s.nhan)}<div class="tt2-nut no-print">${nutCua(x)}</div></div>
      ${canh.join('')}
      <div class="tt2-so">
        <div><span>${NN.h('tt_slips')}</span><b>${x.so_phieu}</b></div>
        <div><span>${NN.h('tt_advanced')}</span><b>${lak(x.tong_ung_lak)}</b></div>
        <div><span>${NN.h('tt_spent')}</span><b>${lak(x.tong_chi_lak)}</b></div>
        <div class="${lop(ch)}"><span>${NN.h('tt_diff')} · ${NN.h(chieu(ch))}</span><b>${lak(Math.abs(ch))}</b></div>
      </div>
      ${t ? veChot(t) : ''}
      <div class="tbl-wrap tt2-phieu">
        <table class="tbl tbl-compact">
          <thead><tr><th>${NN.h('doc_no')}</th><th>${NN.h('d_out')}</th><th>${NN.h('truck_no')}</th><th>${NN.h('route')}</th>
            <th class="num">${NN.h('tt_spent')}</th></tr></thead>
          <tbody>${!c ? `<tr><td colspan="5" class="empty">${NN.h('loading')}</td></tr>` : c.phieu.length ? c.phieu.map(p => `<tr>
            <td><a href="#/phieu-xuat-xe?id=${esc(p.trip_id)}" class="mono">${esc(p.doc_no)}</a></td><td>${EPL.ngay(p.out_date)}</td>
            <td>${esc(p.truck_no || '')}</td><td lang="lo">${p.origin || p.destination ? esc((p.origin || '') + ' → ' + (p.destination || '')) : '—'}</td>
            <td class="num">${so(p.chi_lak)}</td></tr>`).join('') : `<tr><td colspan="5" class="empty">${NN.h('no_data')}</td></tr>`}</tbody>
        </table>
      </div>`;
    o.querySelectorAll('[data-viec]').forEach(b => b.addEventListener('click', () => lam(x, b.dataset.viec, b)));
    if (!c) taiMot(d.driver_id);
  }

  /** Khối bản chốt: ai chốt, phiếu chi / thu bên kế toán (số phiếu, trạng thái, lỗi), quyết toán QT_TU. */
  function veChot(t) {
    const p = t.phieu_ke_toan, qt = t.quyet_toan;
    const ttQt = qt ? ({ cho_gui: 'dt_st_cho_gui', da_gui: 'dt_st_da_gui', huy: 'v_huy' }[qt.status] || qt.status) : null;
    const ttP = p ? ({ da_gui: 'tt_cho_chi', da_chi: 'ck_da_chi_ngan', huy: 'v_huy',
      loi: p.error_code === 'PHIEU_CHI_MAT' ? 'ck_phieu_mat' : 'ck_loi_ngan' }[p.status] || p.status) : null;
    return `<div class="tt2-chot">
      <div><span>${NN.h('tt_done')}</span><b>${esc(t.settled_by || '')}</b> <span class="muted">${EPL.ngayGio(t.settled_at)}</span>
        ${t.note ? `<div class="small muted">${esc(t.note)}</div>` : ''}</div>
      ${p ? `<div><span>${NN.h(p.loai === 'TT_THU' ? 'tt_thu_hoan' : 'tt_chi_bu')}</span>
        <b class="mono">${esc(p.document_no || '—')}</b>
        <span class="tt2-dong">${lak(p.amount)} · ${NN.h(p.phuong_thuc === 'bank' ? 'pm_bank' : 'pm_cash')}</span>
        <div>${EPL.tag(p.status === 'da_chi' ? 'paid' : p.status === 'loi' ? 'unpaid' : p.status === 'huy' ? 'plain' : 'transit', ttP)}
          ${p.post_by ? `<span class="small muted">${esc(p.post_by)} · ${EPL.ngayGio(p.post_at)}</span>` : ''}</div>
        ${p.error_message ? `<div class="small neg">${esc(p.error_message)}</div>` : ''}</div>` : `<div><span>${NN.h('tt_even')}</span></div>`}
      ${qt ? `<div><span>QT_TU · ${esc(NN.t('tt_qt_tu'))}</span><b>${lak(qt.tong)}</b>
        <div>${EPL.tag(qt.status === 'da_gui' ? 'paid' : qt.status === 'huy' ? 'plain' : 'transit', ttQt)}</div></div>` : ''}
    </div>`;
  }

  async function taiMot(id) {
    const ky = BANG.ky;
    try {
      const x = await API.get('/api/tat-toan/' + encodeURIComponent(id) + '?ky=' + encodeURIComponent(ky));
      if (BANG.ky !== ky) return;
      CT[id] = x; if (CHON === id) veXem();
    } catch (e) { EPL.baoLoi(e); }
  }

  /* ---------------------------------------------------------------- việc: chốt · cập nhật · gửi lại · bỏ chốt */
  async function lam(d, viec, nut) {
    const id = d.driver_id, ky = BANG.ky, duong = '/api/tat-toan/' + encodeURIComponent(id);
    if (viec === 'chot') {
      const ch = d.chenh_lech_lak, co = Math.abs(ch) >= 1;
      const html = `<p>${NN.h('tt_confirm', { ky: nhanThang(ky), ten: d.driver_name })}</p>
        <p><b>${NN.h(chieu(ch))}${co ? ': ' + so(Math.abs(ch)) + ' LAK' : ''}</b>${co ? ` — ${NN.h(ch > 0 ? 'tt_chi_bu' : 'tt_thu_hoan')}` : ''}</p>
        ${co ? `<div class="field"><label>${NN.h('tt_cach')}</label><select id="tt2-hn-cach">
          <option value="cash">${NN.h('pm_cash')}</option><option value="bank">${NN.h('pm_bank')}</option></select></div>` : ''}
        <div class="field"><label>${NN.h('note')}</label><textarea id="tt2-hn-note" rows="2"></textarea></div>`;
      if (!await EPL.hoi(NN.t('tt_chot'), html, NN.t('tt_chot'))) return;
      const cach = document.getElementById('tt2-hn-cach'), note = document.getElementById('tt2-hn-note');
      const body = { driver_id: id, period: ky, note: note ? note.value.trim() || undefined : undefined };
      if (cach) body.phuong_thuc = cach.value;
      return chay(nut, id, () => API.post('/api/tat-toan', body));
    }
    if (viec === 'bo') {
      if (!await EPL.hoi(NN.t('tt_bo_chot'), `<p>${NN.h('tt_bo_hoi', { ky: nhanThang(ky), ten: d.driver_name })}</p>`, NN.t('tt_bo_chot'))) return;
      return chay(nut, id, () => API.del(duong + '?ky=' + encodeURIComponent(ky)), true);
    }
    return chay(nut, id, () => API.post(duong + '/' + viec + '?ky=' + encodeURIComponent(ky), {}));
  }
  /** Gọi máy chủ, rồi tải lại bảng tháng (số, trạng thái, dải tổng) và bản đầy đủ của tài xế. Lỗi hiện ngay trên màn. */
  async function chay(nut, id, goi, xoaBan) {
    if (nut) nut.disabled = true;
    try {
      const x = await goi();
      if (!xoaBan && x && x.driver_id === id) CT[id] = x; else delete CT[id];
      EPL.toast(NN.t('saved'), 'ok');
    } catch (e) { EPL.baoLoi(e); delete CT[id]; }
    await tai(true);
  }

  /* ---------------------------------------------------------------- cao vừa cửa sổ */
  let henCao = null;
  function datCao() {
    const ds = root && root.querySelector('.tt2-ds');
    if (!ds || !ds.isConnected) return;
    if (root.classList.contains('mod-dang-tai')) { clearTimeout(henCao); henCao = setTimeout(datCao, 120); return; }
    const tl = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--ty-le')) || 1;
    const le = (parseFloat(getComputedStyle(document.getElementById('noi-dung')).paddingBottom) || 0) * tl;
    const cao = (window.innerHeight - (ds.getBoundingClientRect().top + window.scrollY) - le) / tl;
    root.style.setProperty('--tt-cao', Math.max(300, Math.floor(cao)) + 'px');
  }
  const khiDoiCo = () => { clearTimeout(henCao); henCao = setTimeout(datCao, 150); };

  function veHet() {
    const ds = locDs();
    if (!ds.some(d => d.driver_id === CHON)) CHON = ds[0] ? ds[0].driver_id : null;
    veLoc(); veTong(); veDs(); veXem();
    datCao();
  }

  /** Tải bảng tháng. `giu` = giữ tài xế đang chọn (sau một việc). Lần đầu vào màn không kèm kỳ: tháng này trống thì xem
   *  tháng trước (đầu tháng là lúc tất toán tháng vừa qua), kèm dòng báo. */
  async function tai(giu) {
    const luot = ++LUOT, ky = q('#tt2-ky').value || EPL.thangNay();
    let b;
    try { b = await API.get('/api/tat-toan?ky=' + encodeURIComponent(ky)); } catch (e) { if (luot === LUOT) EPL.baoLoi(e); b = { ky, dong: [] }; }
    if (luot !== LUOT) return;
    if (TU_DONG && !b.dong.length) {
      TU_DONG = false;
      const truoc = thangTruoc(ky);
      BAO = { trong: ky, xem: truoc }; q('#tt2-ky').value = truoc;
      return tai();
    }
    TU_DONG = false;
    if (!giu || (BANG.ky && BANG.ky !== b.ky)) CT = {};
    BANG = b;
    veHet();
  }

  EPL.modules['tat-toan'] = {
    async init(r, ctx) {
      root = r; BANG = { dong: [] }; CT = {}; CHON = null; loc = ''; tim = ''; BAO = null;
      const t = (ctx && ctx.tham) || {};
      if (t.ky) q('#tt2-ky').value = t.ky;
      TU_DONG = !t.ky;
      if (t.tx) CHON = t.tx;
      q('#tt2-ky').addEventListener('change', () => { TU_DONG = false; BAO = null; CHON = null; tai(); });
      q('#tt2-lam-moi').addEventListener('click', () => tai(true));
      q('#tt2-tim').addEventListener('input', (e) => { clearTimeout(hen); hen = setTimeout(() => { tim = e.target.value.trim(); veHet(); }, 200); });
      window.removeEventListener('resize', khiDoiCo); window.addEventListener('resize', khiDoiCo);
      await tai();
    },
    onLang() { if (root) veHet(); },
    destroy() { window.removeEventListener('resize', khiDoiCo); clearTimeout(henCao); clearTimeout(hen); },
    xuatExcel() {
      const T = NN.t;
      return [EPL.xuatSheet(T('nav_settle') + ' ' + nhanThang(BANG.ky), [T('driver'), T('tt_slips'), T('tt_advanced'), T('tt_spent'), T('tt_diff'),
        T('status'), T('tt_chi_bu') + ' / ' + T('tt_thu_hoan')],
        locDs().map(d => { const p = (d.tat_toan || {}).phieu_ke_toan || {};
          return [d.driver_name, d.so_phieu, d.tong_ung_lak, d.tong_chi_lak, d.chenh_lech_lak, T(trangThai(d).nhan), p.document_no || '']; }))];
    },
  };
})();

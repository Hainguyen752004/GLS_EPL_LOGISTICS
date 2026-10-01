/* Đề nghị theo DO — ໃບສະເໜີຕາມ DO (sếp 30/09).
 *
 * "DO nào phiếu chi gì, trạng thái gì; DO nào phiếu thu gì, trạng thái gì." Mỗi DO một dòng:
 *   · Đề nghị chi — đi theo từng bước của chuyến: tạm ứng (TU), xuất nhiên liệu (NL, mỗi kho một tờ), chi các mục III–VI
 *     (chờ nhập → đã nhập → đã kiểm → đã ghi sổ → đã chi);
 *   · Đề nghị thu — một tờ khi DO xong (khoá phiếu), gửi bên công nợ (anh Tune);
 *   · Chứng từ — bao nhiêu tờ của DO đã đối chiếu (đánh dấu tay ở tab Sổ chứng từ).
 * Bấm một DO → khung phải kể từng tờ, bấm tờ mở màn Phiếu đề nghị chi / thu để in.
 *
 * Tab "Sổ chứng từ": tờ bên mình sinh ở mỗi bước, để in / xem / định khoản và đánh dấu đối chiếu tay. Chủ dự án chốt 01/10
 * bỏ trang kế toán tạm phần tiền (8030 chỉ còn là kho tạm, việc tiền đi qua hệ kế toán anh Tune): bỏ thanh "Kết nối kế
 * toán", nút Đẩy hết / Đẩy từng tờ, lỗi đẩy, mã phiếu bên trang tạm; hộp Cấu hình chỉ còn hai mã bên kế toán cấp.
 * API: GET /api/de-nghi-theo-do?thang=&q= · GET /api/chung-tu?trip_id= · sổ: /api/chung-tu, POST /api/chung-tu/{id}/da-day ·
 * hai mã: GET/PUT /api/kho-tam/cau-hinh (máy chủ trước 52f673c: /api/ke-toan/cau-hinh).
 */
(function () {
  const { API, NN, esc, so, AUTH } = EPL;
  let root, tab = 'do', D = { ds: [] }, loc = '', tim = '', chonId = null, hen = null;
  let SO_LOAI = [], soLoaiChon = '';
  const XEM_SO = ['acct', 'expacct', 'rev', 'treasury', 'cash', 'fuel', 'depot', 'admin'];
  // loại đối tượng của tờ (services/chung_tu.py) → nhãn đã dịch; trước đây hiện mã thô "tai_xe", "khach"… dưới tên
  const DOI_TUONG = { khach: 'customer', tai_xe: 'driver', chu_xe: 'owner', kho: 'fuel_kho', ncc: 'supplier' };
  const MUC = [['fuel', 'III', 'e_fuel'], ['travel', 'IV', 'e_travel'], ['repair', 'V', 'e_repair'], ['other', 'VI', 'e_other']];
  const q = (s) => root.querySelector(s);
  const thangNay = () => EPL.thangNay();    // giờ máy — toISOString là giờ UTC, 0–7 giờ sáng ngày 1 ra tháng trước
  const tagTT = (s) => `<span class="tag dt_${esc(s)}">${NN.h('dt_st_' + s)}</span>`;
  /** Tên loại chứng từ theo tiếng đang xem — từ điển `ctl_<mã>` (rà 02/10: máy chủ chỉ gửi tên Việt / Lào, tiếng Anh hiện chữ
   *  Việt). Loại mới chưa có khoá thì lấy tên máy chủ gửi. `tho` = chữ thuần (cho <option>). */
  function tenLoai(ma, vi, lo, tho) {
    const k = 'ctl_' + String(ma || '').toLowerCase();
    if ((window.EPL_TU_DIEN || {})[k]) return tho ? esc(NN.t(k)) : NN.h(k);
    return esc(NN.lang === 'lo' ? lo || vi : vi || lo);
  }
  const veOLoai = () => {
    q('#ct-so-loai').innerHTML = `<option value="">${esc(NN.t('all'))}</option>` + SO_LOAI.map(l => `<option value="${l.ma}">${esc(l.ma)} · ${tenLoai(l.ma, l.ten, l.ten_lo, true)}</option>`).join('');
    q('#ct-so-loai').value = soLoaiChon;
  };
  /* Tháng trống (01/10): mở màn đầu tháng thấy "Chưa có dữ liệu", tưởng hỏng. TU_DONG = lượt tải đầu khi vào màn không kèm
   * tháng → tháng trống thì sang tháng gần nhất có DO, BAO giữ dòng báo; GAN = tháng cho nút ở khung trống. */
  let TU_DONG = false, BAO = null, GAN = null;
  const nhanThang = (v) => (v ? v.slice(5, 7) + '/' + v.slice(0, 4) : '');

  /** Tháng `th` có phiếu không; không có thì tháng nào GẦN NHẤT có (cùng bộ lọc `loc` của /api/trips). Hỏi hai lần, mỗi lần
   *  một dòng: phiếu mới nhất tới cuối tháng `th`, phiếu cũ nhất từ đầu tháng `th` — không tải cả năm. Cách đều: tháng trước. */
  async function thangGan(th, loc) {
    const [y, m] = th.split('-').map(Number);
    const hoi = (them) => { const p = new URLSearchParams(loc); p.set('co', '1'); Object.entries(them).forEach(([k, v]) => p.set(k, v));
      return API.get('/api/trips?' + p).then(d => (d && d[0] && d[0].doc_date ? d[0].doc_date.slice(0, 7) : null), () => null); };
    const [truoc, sau] = await Promise.all([hoi({ den: th + '-' + String(new Date(y, m, 0).getDate()).padStart(2, '0') }), hoi({ tu: th + '-01', sap: 'cu' })]);
    if (truoc === th || sau === th) return { co: true, gan: th };
    const n = (v) => v.slice(0, 4) * 12 + +v.slice(5, 7);
    return { co: false, gan: !truoc || !sau ? truoc || sau : (n(sau) - n(th) < n(th) - n(truoc) ? sau : truoc) };
  }
  /** Người dùng TỰ chọn tháng (ô tháng, nút ở khung trống): giữ đúng tháng đó, bỏ dòng báo, thôi tự sang tháng khác. */
  function chonThang(v) { TU_DONG = false; BAO = null; q('#ct2-thang').value = v; taiDo(); }
  function veBao() {
    const o = q('#ct2-bao');
    o.hidden = !BAO;
    o.innerHTML = BAO ? `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8v.01"/></svg><span>${NN.h('thang_trong_dang_xem', { trong: nhanThang(BAO.trong), xem: nhanThang(BAO.xem) })}</span>` : '';
  }
  /** Bảng trống: lý do đúng (tháng chưa có DO · chữ tìm / thẻ lọc không khớp) + nút về tháng gần nhất hoặc xem tất cả. */
  function oTrong() {
    const boLoc = D.ds.length || tim;
    return `<div class="ct2-trong-bang"><div>${boLoc ? NN.h('loc_trong') : NN.h('thang_trong_n', { thang: nhanThang(q('#ct2-thang').value) })}</div>
      ${D.ds.length && loc ? `<button type="button" class="btn sm" data-tat-ca="1">${NN.h('tq_view_all')}</button>` : ''}
      ${!D.ds.length && GAN ? `<button type="button" class="btn sm primary" data-thang="${esc(GAN)}">${NN.h('thang_xem_gan', { thang: nhanThang(GAN) })}</button>` : ''}</div>`;
  }

  /* ---------------------------------------------------------------- lọc */
  const conXk = (x) => x.nhien_lieu.some(v => v.status === 'cho');
  const conChi = (x) => x.tam_ung.some(v => v.status === 'cho')
    || Object.values(x.muc).some(m => m.status !== 'paid');
  // chờ thu = DO đã khoá mà chưa thu đủ: chưa lập / chờ gửi / đã tạo SO / thu một phần (trạng thái theo hệ kế toán, 01/10)
  const choThu = (x) => ['cho_gui', 'chua_lap', 'da_tao_so', 'thu_mot_phan'].includes(x.thu.trang_thai);
  function dsLoc() { return D.ds.filter(x => !loc || (loc === 'chi' ? conChi(x) : loc === 'xk' ? conXk(x) : choThu(x))); }

  /* ---------------------------------------------------------------- bảng DO */
  function chipDeNghi(x) {
    const tu = x.tam_ung.map(v => `<span class="ct2-chip ${esc(v.status)}" title="${esc(v.so)}">TU · ${NN.h('v_' + v.status)}</span>`).join('');
    const nl = x.nhien_lieu.length ? (() => {
      const cho = x.nhien_lieu.filter(v => v.status === 'cho').length;
      return `<span class="ct2-chip ${cho ? 'cho' : 'da_cap'}" title="${esc(x.nhien_lieu.map(v => v.so).join(', '))}">NL ×${x.nhien_lieu.length} · ${NN.h(cho ? 'v_cho' : 'v_da_cap')}</span>`;
    })() : '';
    const muc = `<span class="ct2-muc">${MUC.map(([k, la, ten]) => {
      const m = x.muc[k];
      return m ? `<i class="${esc(m.status)}" title="${esc(NN.t(ten))} · ${esc(NN.t('stt_' + m.status))}">${la}</i>`
        : `<i class="khong" title="${esc(NN.t(ten))} · —">${la}</i>`;
    }).join('')}</span>`;
    return { chi: tu + muc, xk: nl || '<span class="muted">—</span>' };
  }

  function veBang() {
    const b = q('#ct2-bang'), ds = dsLoc();
    q('#ct2-n-all').textContent = D.ds.length;
    q('#ct2-n-chi').textContent = D.ds.filter(conChi).length;
    q('#ct2-n-xk').textContent = D.ds.filter(conXk).length;
    q('#ct2-n-thu').textContent = D.ds.filter(choThu).length;
    root.querySelectorAll('#ct2-loc button').forEach(x => x.classList.toggle('on', x.dataset.loc === loc));
    const ban = D.thay_tien_ban;
    b.innerHTML = `<thead><tr><th>DO</th><th>${NN.h('truck_no')} · ${NN.h('driver')}</th><th>${NN.h('customer')} · ${NN.h('route')}</th>
      <th>${NN.h('ct_c_chi')}</th><th>${NN.h('ct_c_xk')}</th><th>${NN.h('ct_c_thu')}</th><th>${NN.h('ct_da_day')}</th></tr></thead>
      <tbody>${ds.length ? ds.map(x => `<tr data-id="${esc(x.trip_id)}" class="${x.trip_id === chonId ? 'sel' : ''}">
        <td><span class="so">${esc(x.doc_no)}</span><span class="ct2-k ${esc(x.kind)}">${NN.h(x.kind === 'gom' ? 'dn_gom' : 'dn_giao')}</span>${x.company === 'joint' ? `<span class="ct2-k joint">${NN.h('dn_xe_thue')}</span>` : ''}
          <span class="phu">${EPL.ngay(x.doc_date)}${x.locked ? ' · ' + NN.h('s_locked') : ''}</span></td>
        <td>${esc(x.truck_no || '—')}<span class="phu" lang="lo">${esc(x.driver_name || '')}</span></td>
        <td><span lang="lo">${esc(x.customer_name || '—')}</span>${x.origin || x.destination ? `<span class="phu" lang="lo">${esc(x.origin || '—')} → ${esc(x.destination || '—')}</span>` : ''}</td>
        <td>${chipDeNghi(x).chi}</td><td>${chipDeNghi(x).xk}</td>
        <td>${tagTT(x.thu.trang_thai)}${ban && x.thu.doanh_thu ? `<span class="phu">${EPL.tien(x.thu.doanh_thu, x.thu.ccy)}</span>` : ''}</td>
        <td class="ct2-ho">${x.ho_so.da_day}/${x.ho_so.tong}</td></tr>`).join('')
        : `<tr><td class="empty" colspan="7">${oTrong()}</td></tr>`}</tbody>`;
    b.querySelectorAll('tbody tr[data-id]').forEach(tr => tr.addEventListener('click', () => { chonId = tr.dataset.id; veBang(); veCt(); }));
    const nutThang = b.querySelector('[data-thang]'); if (nutThang) nutThang.addEventListener('click', () => chonThang(nutThang.dataset.thang));
    const nutHet = b.querySelector('[data-tat-ca]'); if (nutHet) nutHet.addEventListener('click', () => { loc = ''; chonId = D.ds[0] ? D.ds[0].trip_id : null; veBang(); veCt(); });
    // bảng trống: bỏ khung "Chọn một dòng" bên phải, bảng (và khung trống của nó) chiếm cả bề ngang
    q('#ct2-do').classList.toggle('trong', !ds.length); q('#ct2-ct').hidden = !ds.length;
    veBao();
    datCao();
    // chú thích màu bốn mục chi — nằm ngay dưới bảng, không chiếm hàng riêng trên đầu
    let chu = root.querySelector('.ct2-chu');
    if (!chu) { chu = document.createElement('div'); chu.className = 'ct2-chu'; q('.ct2-trai').appendChild(chu); }
    chu.innerHTML = `<span>III · IV · V · VI = ${NN.h('ct_bon_muc')}</span>` + ['wait', 'entered', 'verified', 'booked', 'paid'].map(s =>
      `<span><span class="ct2-muc"><i class="${s}">·</i></span>${NN.h('stt_' + s)}</span>`).join('');
    datCao();
  }

  /* ---------------------------------------------------------------- khung phải */
  /** Tờ / tháng đang xem ghi vào địa chỉ (rà 01/10): bấm "Mở phiếu" sang Phiếu xuất xe rồi Quay lại, hay tải lại trang, là về
   *  đúng tờ đó — trước đây màn mở lại từ đầu, tờ vừa xem như biến mất. init đã đọc sẵn các tham số này. replaceState: không
   *  thêm bước lịch sử, không bắn hashchange (khung không nạp lại màn); màn đã bị rời (gốc tháo khỏi trang) thì thôi. */
  function ghiDiaChi(ts) {
    if (!root || !root.isConnected) return;
    [...ts.keys()].forEach(k => { if (!ts.get(k)) ts.delete(k); });
    const moi = '#/chung-tu' + (ts.toString() ? '?' + ts : '');
    if (location.hash !== moi) history.replaceState(null, '', moi);
  }

  async function veCt() {
    const ct = q('#ct2-ct'), x = D.ds.find(y => y.trip_id === chonId);
    if (tab === 'do') ghiDiaChi(new URLSearchParams({ thang: q('#ct2-thang').value || '', id: x ? x.trip_id : '' }));
    if (!x) { ct.innerHTML = `<div class="ct2-chon">${NN.h('kx_chon')}</div>`; return; }
    const chi = D.thay_tien_chi, ban = D.thay_tien_ban;
    const dong = (t, n, r) => `<div class="ct2-dong"><div><div class="t">${t}</div>${n ? `<div class="n">${n}</div>` : ''}</div><div class="r">${r}</div></div>`;
    const tu = x.tam_ung.map(v => dong(`<a data-v="${esc(v.id)}" data-loai="advance">${esc(v.so)}</a>`, NN.h('v_advance'),
      `${chi && v.amount_lak != null ? so(v.amount_lak) + ' LAK · ' : ''}<span class="ct2-chip ${esc(v.status)}">${NN.h('v_' + v.status)}</span>`)).join('');
    const nl = x.nhien_lieu.map(v => dong(`<a data-v="${esc(v.id)}" data-loai="fuel">${esc(v.so)}</a>`, `<span lang="lo">${esc(v.place_name || '')}</span>`,
      `${so(v.qty_l, 0)} L${v.granted_qty != null && v.granted_qty !== v.qty_l ? ' → ' + so(v.granted_qty, 0) + ' L' : ''} · <span class="ct2-chip ${esc(v.status)}">${NN.h('v_' + v.status)}</span>`)).join('');
    const muc = MUC.filter(([k]) => x.muc[k]).map(([k, la, ten]) => {
      const m = x.muc[k], kt = m.ke_toan;     // mục V / VI: phiếu chi "Chi khác" bên hệ kế toán (01/10)
      // trạng thái phiếu chi bên kế toán xuống dòng phụ (dưới tên mục) — để cột phải không đẩy tên mục vỡ dòng
      const nhanKT = !kt ? '' : ' · ' + EPL.tag(kt.status === 'da_chi' ? 'paid' : kt.status === 'da_gui' ? 'partial' : 'unpaid',
        kt.status === 'da_chi' ? 'ck_da_chi_ngan' : kt.status === 'da_gui' ? 'cmt_cho_chi' : kt.error_code === 'PHIEU_CHI_MAT' ? 'ck_phieu_mat' : 'ck_loi_ngan')
        + (kt.document_no ? ` <span class="mono">${esc(kt.document_no)}</span>` : '');
      return dong(`${la} · ${NN.h(ten)}`, NN.h('ct_so_dong', { n: m.so_dong }) + nhanKT,
        `${chi && m.tien_lak != null ? so(m.tien_lak) + ' LAK · ' : ''}<span class="ct2-muc"><i class="${esc(m.status)}">${la}</i></span> ${NN.h('stt_' + m.status)}`);
    }).join('');
    const t = x.thu;
    const thu = dong(t.pdt ? `<a data-thu="1">${esc(t.pdt.so)}</a>` : NN.h('nav_de_nghi_thu'),
      t.da_tao_so ? NN.h('dt_so_da', { so: t.order_code || '' }) : (t.trang_thai === 'cho_khoa' ? NN.h('dt_goi_y_khoa') : ''),
      `${ban && t.doanh_thu != null ? EPL.tien(t.doanh_thu, t.ccy) + ' · ' : ''}${tagTT(t.trang_thai)}`)
      + (ban && t.doanh_thu_lak ? dong(NN.h('collected'), '', `${so(t.da_thu_lak)} LAK · ${NN.h('ncc_con_thu')} ${so(t.con_lai_lak)} LAK`) : '');
    ct.innerHTML = `<div class="ct2-dau"><h3>${esc(x.doc_no)}</h3>
        <div class="phu"><span lang="lo">${esc(x.customer_name || '')}</span>${x.origin || x.destination ? ` · <span lang="lo">${esc(x.origin || '—')} → ${esc(x.destination || '—')}</span>` : ''}</div>
        <div class="phu">${esc(x.truck_no || '')} · <span lang="lo">${esc(x.driver_name || '')}</span>${x.company === 'joint' ? ' · ' + NN.h('co_joint') + ' <span lang="lo">' + esc(x.owner_name || '') + '</span>' : ''}</div></div>
      <div class="ct2-cuon">
        <div class="ct2-nhom"><h4>${NN.h('nav_de_nghi_chi')}<a data-mo-chi="1">${NN.h('ct_mo_man')}</a></h4>
          ${tu || `<div class="ct2-trong">${NN.h('ct_chua_de_nghi_chi')}</div>`}</div>
        <div class="ct2-nhom"><h4>${NN.h('nav_de_nghi_xuat_kho')}<a data-mo-xk="1">${NN.h('ct_mo_man')}</a></h4>
          ${nl || `<div class="ct2-trong">${NN.h('ct_chua_de_nghi_xk')}</div>`}</div>
        <div class="ct2-nhom"><h4>${NN.h('ct_chi_theo_muc')}</h4>${muc || `<div class="ct2-trong">${NN.h('no_data')}</div>`}</div>
        ${ban || t.pdt ? `<div class="ct2-nhom"><h4>${NN.h('nav_de_nghi_thu')}${ban ? `<a data-thu="1">${NN.h('ct_mo_man')}</a>` : ''}</h4>${thu}</div>` : ''}
        <div class="ct2-nhom" id="ct2-ho-so"><h4>${NN.h('ct_so_chung_tu')}</h4><div class="ct2-trong">${NN.h('loading')}</div></div>
        <div class="ct2-nhom"><h4><a data-mo-phieu="1" style="margin-left:0">${NN.h('open_slip')} →</a></h4></div>
      </div>`;
    ct.querySelectorAll('a[data-v]').forEach(a => a.addEventListener('click', () => a.dataset.loai === 'fuel'
      ? EPL.di('de-nghi-xuat-kho', { id: x.trip_id, v: a.dataset.v }) : EPL.di('de-nghi-chi', { id: x.trip_id, v: a.dataset.v })));
    ct.querySelectorAll('a[data-mo-chi]').forEach(a => a.addEventListener('click', () => EPL.di('de-nghi-chi', { id: x.trip_id })));
    ct.querySelectorAll('a[data-mo-xk]').forEach(a => a.addEventListener('click', () => EPL.di('de-nghi-xuat-kho', { id: x.trip_id })));
    ct.querySelectorAll('a[data-thu]').forEach(a => a.addEventListener('click', () => EPL.di('de-nghi-thu', { id: x.trip_id, thang: (x.doc_date || '').slice(0, 7) })));
    ct.querySelectorAll('a[data-mo-phieu]').forEach(a => a.addEventListener('click', () => EPL.di('phieu-xuat-xe', { id: x.trip_id })));
    // chứng từ của DO này — vai không xem sổ (Bãi) thì bỏ khối
    const ho = q('#ct2-ho-so');
    if (!XEM_SO.includes(AUTH.role)) { ho.remove(); return; }
    let r;
    try { r = await API.get('/api/chung-tu?trip_id=' + encodeURIComponent(x.trip_id)); } catch (e) { ho.querySelector('.ct2-trong').textContent = e.message; return; }
    if (chonId !== x.trip_id || !ho.isConnected) return;
    ho.innerHTML = `<h4>${NN.h('ct_so_chung_tu')}<a data-so="1">${NN.h('ct_mo_man')}</a></h4>` + (r.ds.length ? r.ds.map(c => dong(
      `<span class="mono">${esc(c.so)}</span>`, tenLoai(c.loai, c.loai_ten, c.loai_ten_lo),
      `${c.tien != null ? EPL.tien(c.tien, c.tien_te) : ''}${c.loai === 'PDT' ? '' : (c.tien != null ? ' · ' : '') + (c.da_day ? '✓ ' + NN.h('ct_da_day') : '<span class="muted">' + NN.h('ct_chua_day') + '</span>')}`)).join('')
      : `<div class="ct2-trong">${NN.h('ct_khong_co')}</div>`);
    ho.querySelector('a[data-so]').addEventListener('click', () => doiTab('so'));
  }

  /* Bảng cao VỪA cửa sổ (rà 01/10: 22 DO là trang dài 1.700 px, Sổ chứng từ 17.000 px — khung chi tiết bên phải trôi mất):
   * đo từ đầu khung bảng của tab đang mở tới đáy cửa sổ, trừ lề đáy trang và dòng chú thích dưới bảng, đặt vào --ct-cao.
   * Bảng tự cuộn trong khung, dòng tiêu đề dính trên. Toạ độ là px màn hình, px CSS bên trong .app (zoom --ty-le) nên chia. */
  let henCao = null;
  function datCao() {
    const w = root && root.querySelector(tab === 'so' ? '#ct-so-ct .tbl-wrap' : '.ct2-trai .tbl-wrap');
    if (!w || !w.isConnected) return;
    if (root.classList.contains('mod-dang-tai')) { clearTimeout(henCao); henCao = setTimeout(datCao, 120); return; }
    const tl = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--ty-le')) || 1;
    const le = (parseFloat(getComputedStyle(document.getElementById('noi-dung')).paddingBottom) || 0) * tl;
    const chu = tab === 'so' ? null : root.querySelector('.ct2-chu');
    const duoi = chu ? chu.getBoundingClientRect().height + 8 * tl : 0;
    const cao = (window.innerHeight - (w.getBoundingClientRect().top + window.scrollY) - le - duoi) / tl;
    root.style.setProperty('--ct-cao', Math.max(260, Math.floor(cao)) + 'px');
  }
  const khiDoiCo = () => { clearTimeout(henCao); henCao = setTimeout(datCao, 150); };

  let LUOT = 0;                // lượt tải mới nhất — lượt cũ (đang tự sang tháng) về sau thì không vẽ đè
  async function taiDo() {
    const luot = ++LUOT;
    const thang = q('#ct2-thang').value || thangNay();
    const th = new URLSearchParams({ thang });
    if (tim) th.set('q', tim);
    let duoc = true, ve;
    try { ve = await API.get('/api/de-nghi-theo-do?' + th.toString()); } catch (e) { ve = { ds: [] }; duoc = false; if (luot === LUOT) EPL.baoLoi(e); }
    if (luot !== LUOT) return;
    D = ve; GAN = null;
    if (duoc && !D.ds.length) {
      const r = await thangGan(thang, tim ? { q: tim } : {});
      if (luot !== LUOT) return;
      GAN = r.co ? null : r.gan;
      if (TU_DONG && GAN) { TU_DONG = false; BAO = { trong: thang, xem: GAN }; q('#ct2-thang').value = GAN; return taiDo(); }
    }
    TU_DONG = false;
    const ds = dsLoc();
    if (!ds.some(x => x.trip_id === chonId)) chonId = ds[0] ? ds[0].trip_id : null;
    veBang(); veCt();
  }

  /* ---------------------------------------------------------------- Sổ chứng từ (in / xem / định khoản, đối chiếu tay) */
  function veSoTong(tong) {
    q('#ct-so-tong').innerHTML = Object.keys(tong).length ? SO_LOAI.filter(l => tong[l.ma]).map(l => {
      const t = tong[l.ma];
      return `<button type="button" class="o ${soLoaiChon === l.ma ? 'chon' : ''}" data-loai="${l.ma}"><b>${esc(l.ma)}</b>${tenLoai(l.ma, l.ten, l.ten_lo)}
        <div><span class="n">${t.so_to}</span> ${NN.h('ct_so_to').toLowerCase()} · <span class="n">${so(t.tien_lak)}</span> LAK${t.chua_day ? ` · <span class="c">${t.chua_day} ${NN.h('ct_chua_day').toLowerCase()}</span>` : ''}</div></button>`;
    }).join('') : '';
    q('#ct-so-tong').querySelectorAll('[data-loai]').forEach(b => b.addEventListener('click', () => { soLoaiChon = soLoaiChon === b.dataset.loai ? '' : b.dataset.loai; q('#ct-so-loai').value = soLoaiChon; veSo(); }));
  }
  /** Hai mã bên kế toán cấp (hàng khách gửi · giá vốn hàng bán) — gõ ở đây là mọi tờ sinh từ đó mang mã, không sửa mã nguồn.
   *  Địa chỉ / khoá trang kế toán tạm đã bỏ (01/10). Đường mới /api/kho-tam/cau-hinh; máy chủ cũ chỉ có /api/ke-toan/cau-hinh. */
  async function goiCauHinh(phuong, than) {
    const goi = (d) => (phuong === 'put' ? API.put(d, than) : API.get(d));
    try { return await goi('/api/kho-tam/cau-hinh'); } catch (e) { if (e.status !== 404 && e.status !== 405) throw e; }
    return goi('/api/ke-toan/cau-hinh');
  }
  async function moCauHinh() {
    let hien = {}; try { hien = await goiCauHinh('get'); } catch (e) { hien = {}; }
    const v = await EPL.hopNhap(NN.t('ct_cau_hinh'), [
      { id: 'ma_hang_khach_gui', label: 'ct_ma_hang_gui', value: hien.ma_hang_khach_gui || '' },
      { id: 'ma_gia_von', label: 'ct_ma_gia_von', value: hien.ma_gia_von || '' },
    ], NN.t('save'));
    if (!v) return;
    try { await goiCauHinh('put', { ma_hang_khach_gui: v.ma_hang_khach_gui, ma_gia_von: v.ma_gia_von }); EPL.toast(NN.t('saved'), 'ok'); }
    catch (e) { EPL.baoLoi(e); }
  }

  async function veSo() {
    const th = new URLSearchParams();
    if (soLoaiChon) th.set('loai', soLoaiChon);
    if (q('#ct-so-tu').value) th.set('tu', q('#ct-so-tu').value);
    if (q('#ct-so-den').value) th.set('den', q('#ct-so-den').value);
    if (q('#ct-so-chua').checked) th.set('chua_day', '1');
    let r;
    try { r = await API.get('/api/chung-tu?' + th.toString()); } catch (e) { q('#ct-so-than').innerHTML = `<tr><td colspan="10" class="empty neg">${esc(e.message)}</td></tr>`; return; }
    veSoTong(r.tong);
    datCao();
    const tk = (ma, ten) => ma ? `<span class="acct" title="${esc(ten || '')}">${esc(ma)}</span>` : `<span class="muted small" title="${esc(ten || '')}">?</span>`;
    const suaDuoc = AUTH.la('acct', 'expacct', 'rev', 'treasury', 'cash');   // đánh dấu đối chiếu tay
    q('#ct-so-than').innerHTML = r.ds.length ? r.ds.map(c => `<tr class="${c.da_day && c.loai !== 'PDT' ? 'da-day' : ''}" data-id="${c.id}">
      <td class="mono">${esc(c.so)}</td><td>${EPL.ngay(c.ngay)}</td>
      <td><b>${esc(c.loai)}</b><div class="small muted">${tenLoai(c.loai, c.loai_ten, c.loai_ten_lo)}</div></td>
      <td>${c.trip_id ? `<a href="#/phieu-xuat-xe?id=${esc(c.trip_id)}" class="mono">${esc(c.trip_doc_no || '')}</a>` : '<span class="muted">—</span>'}</td>
      <td lang="lo">${esc(c.doi_tuong_ten || '')}<div class="small muted">${DOI_TUONG[c.doi_tuong_loai] ? NN.h(DOI_TUONG[c.doi_tuong_loai]) : esc(c.doi_tuong_loai || '')}</div></td>
      <td class="num">${c.tien == null ? '—' : EPL.tien(c.tien, c.tien_te)}</td>
      <td class="num">${c.tien_lak == null ? '—' : so(c.tien_lak)}</td>
      <td>${c.no || c.co || c.no_ten ? `${tk(c.no, c.no_ten)} / ${tk(c.co, c.co_ten)}` : '<span class="muted">—</span>'}</td>
      <td class="small">${esc(c.mo_ta || '')}<div class="muted">${esc(c.by_user || '')}</div></td>
      <td class="small">${c.loai === 'PDT' ? '<span class="muted">—</span>' : c.da_day ? `✓ ${NN.h('ct_da_day')}` : `<span class="muted">${NN.h('ct_chua_day')}</span>`}</td>
      <td class="no-print">${c.loai === 'PDT' ? '' : suaDuoc ? `<button type="button" class="btn sm ${c.da_day ? 'quiet' : ''}" data-day="${c.id}" data-gia-tri="${c.da_day ? 0 : 1}">${NN.h(c.da_day ? 'ct_mo_lai' : 'ct_danh_dau')}</button>` : (c.da_day ? '✓' : '')}</td>
    </tr>`).join('') : `<tr><td colspan="11" class="empty small">${NN.h('ct_khong_co')}</td></tr>`;
    q('#ct-so-than').querySelectorAll('[data-day]').forEach(b => b.addEventListener('click', async () => {
      try { await API.post(`/api/chung-tu/${b.dataset.day}/da-day`, { da_day: b.dataset.giaTri === '1' }); await veSo(); } catch (e) { EPL.baoLoi(e); }
    }));
  }

  /* ---------------------------------------------------------------- hai tab */
  async function doiTab(t) {
    tab = t === 'so' && XEM_SO.includes(AUTH.role) ? 'so' : 'do';
    root.querySelectorAll('#ct2-tab button').forEach(b => b.classList.toggle('on', b.dataset.tab === tab));
    root.querySelectorAll('.ct2-khi-do').forEach(el => { el.hidden = tab !== 'do'; });
    q('#ct2-do').hidden = tab !== 'do'; q('#ct-so-ct').hidden = tab !== 'so';
    if (tab === 'so') {
      ghiDiaChi(new URLSearchParams({ tab: 'so', loai: soLoaiChon || '' }));
      // danh mục loại nạp một lần trong phiên, nhưng ô chọn thì của GỐC MÀN MỚI mỗi lần vào màn — luôn vẽ lại (trước đây lần
      // vào màn thứ hai ô Loại chứng từ chỉ còn "Tất cả")
      if (!SO_LOAI.length) SO_LOAI = await API.get('/api/chung-tu/loai').catch(() => []);
      veOLoai();
      await veSo();
    } else await taiDo();
  }

  EPL.modules['chung-tu'] = {
    async init(r, ctx) {
      root = r; D = { ds: [] }; tim = ''; loc = ''; chonId = null;
      const t = (ctx && ctx.tham) || {};
      // đường cũ ?tab=chi / ?tab=linh (tờ in) → màn Phiếu đề nghị chi
      if (t.tab === 'chi') return EPL.di('de-nghi-chi', { id: t.id || '', v: t.v || '' });
      if (t.tab === 'linh') return EPL.di('de-nghi-xuat-kho', { id: t.id || '', v: t.v || '' });
      // ô tháng mặc định là tháng này THEO GIỜ MÁY (EPL.doiOThang) — toISOString là giờ UTC, 0–7 giờ sáng ngày 1 ra tháng trước
      if (t.thang) q('#ct2-thang').value = t.thang;
      BAO = null; GAN = null; TU_DONG = !t.thang;
      if (t.id) chonId = t.id;
      if (!XEM_SO.includes(AUTH.role)) q('#ct2-tab button[data-tab="so"]').hidden = true;
      q('#ct-cau-hinh').hidden = AUTH.role !== 'admin';
      q('#ct-cau-hinh').addEventListener('click', moCauHinh);
      root.querySelectorAll('#ct2-tab button').forEach(b => b.addEventListener('click', () => doiTab(b.dataset.tab)));
      root.querySelectorAll('#ct2-loc button').forEach(b => b.addEventListener('click', () => { loc = b.dataset.loc; veBang(); }));
      q('#ct2-thang').addEventListener('change', (e) => chonThang(e.target.value));
      q('#ct2-tim').addEventListener('input', (e) => { clearTimeout(hen); hen = setTimeout(() => { tim = e.target.value.trim(); taiDo(); }, 300); });
      q('#ct-so-loai').addEventListener('change', e => { soLoaiChon = e.target.value; veSo(); });
      ['ct-so-tu', 'ct-so-den', 'ct-so-chua'].forEach(id => q('#' + id).addEventListener('change', veSo));
      window.removeEventListener('resize', khiDoiCo); window.addEventListener('resize', khiDoiCo);
      if (t.loai) soLoaiChon = String(t.loai).toUpperCase();
      await doiTab(t.tab === 'so' ? 'so' : 'do');
    },
    onLang() { if (root) { if (SO_LOAI.length) veOLoai(); if (tab === 'so') veSo(); else { veBang(); veCt(); } } },
    destroy() { window.removeEventListener('resize', khiDoiCo); clearTimeout(henCao); clearTimeout(hen); },
    xuatExcel() {
      if (tab === 'so') return EPL._xlsx.sheetMacDinh(root);
      const T = NN.t;
      return [EPL.xuatSheet(T('nav_vouchers'), ['DO', T('do_kind'), T('c_date'), T('truck_no'), T('driver'), T('customer'), T('route'),
        T('v_advance'), T('v_fuel'), 'III', 'IV', 'V', 'VI', T('nav_de_nghi_thu'), T('ct_da_day')],
        dsLoc().map(x => [x.doc_no, T(x.kind === 'gom' ? 'dn_gom' : 'dn_giao'), EPL.oNgay(x.doc_date), x.truck_no || '', x.driver_name || '', x.customer_name || '',
          (x.origin || '') + ' → ' + (x.destination || ''), x.tam_ung.map(v => v.so + ' · ' + T('v_' + v.status)).join('; '),
          x.nhien_lieu.map(v => v.so + ' · ' + T('v_' + v.status)).join('; '),
          ...MUC.map(([k]) => x.muc[k] ? T('stt_' + x.muc[k].status) : ''),
          (x.thu.pdt ? x.thu.pdt.so + ' · ' : '') + T('dt_st_' + x.thu.trang_thai), x.ho_so.da_day + '/' + x.ho_so.tong]))];
    },
  };
})();

/* Phiếu đề nghị chi — ໃບສະເໜີຈ່າຍ (sếp 30/09: tách "Phiếu chi · Phiếu thu" thành hai màn đề nghị chi / đề nghị thu).
 *
 * Hai loại tờ bên mình lập theo bước của chuyến:
 *   · Phiếu đề nghị tạm ứng (PTU). Từ 01/10 (chủ dự án: "chi thật là anh Tune xong update trạng thái về bên mình"): KT Chi phí
 *     ghi sổ mục IV → máy lập phiếu chi "Chi trước" bên hệ kế toán; thủ quỹ chi tiền và GHI SỔ ở đó; trang này hỏi lại, đã ghi
 *     sổ thì tờ thành "Đã cấp" và tài xế xuất phát được. Khối #dnc-kt: trạng thái + Cập nhật / Gửi lại.
 *   · Phiếu đề nghị xuất kho nhiên liệu (PLNL) — mỗi kho EPL một tờ; thủ kho quét QR, cấp dầu theo tờ.
 * Việc cấp thật ở bên kho / bên quỹ (màn Cấp phát trang kế toán). Màn này tìm, xem, in — không cấp, không chi.
 *
 * API: GET /api/vouchers?trang_thai=&loai=&q= · GET /api/trips/{id}/phieu-chi · GET /api/trips/{id}/vouchers · GET /api/trips/{id}.
 * Bãi không thấy tiền (anh Khampla A2): máy chủ không gửi số tiền — tờ tạm ứng chỉ khoản mục và số lượng.
 */
(function () {
  const { API, NN, esc, so, tag, AUTH } = EPL;
  let root, DS = [], tt = 'cho', tim = '', chonId = null, ACC = {}, LINH = [], hen = null;
  let phieuLe = null;               // phiếu mở từ phiếu xuất xe mà chưa có tờ tạm ứng — đổi tiếng thì vẽ lại đúng phiếu đó
  const loai = 'advance';            // chỉ tạm ứng (30/09 chiều) — xuất kho nhiên liệu ở màn Phiếu đề nghị xuất kho
  const q = (s) => root.querySelector(s);

  function tenTK(ma) {
    // "625/402" → hai nửa, mỗi nửa tra danh mục Acc code của bên kế toán; nửa không có thì nói thẳng
    return String(ma || '').split('/').map(m => { const x = ACC[m]; return `<span class="ct-acc" title="${esc(x ? (x.description || x.name) : NN.t('acct_not_in_catalogue'))}">${esc(m)}</span>`; }).join(' / ');
  }

  /** Khối mã QR in trên tờ. QR chỉ chứa ĐƯỜNG DẪN TRA CỨU, không nhồi số liệu: số liệu còn đổi sau lúc in. */
  function khoiQR(v) {
    if (!v) return '';
    return `<div class="ct-qr">
      <img src="${esc(v.qr)}" alt="QR" width="132" height="132">
      <div><div class="small muted">${NN.h('v_qr_hint')}</div>
        <div class="ct-ma">${NN.h('v_code')}: <b class="mono">${esc(v.token)}</b></div>
        <div class="small muted">${tag(v.status === 'da_cap' ? 'paid' : 'plain', 'v_' + v.status)}</div></div></div>`;
  }

  /* ---------------------------------------------------------------- tờ đề nghị tạm ứng */
  function veTamUng(d, v) {
    const coTien = d.tong_lak !== null && d.tong_lak !== undefined;
    q('#dnc-so').innerHTML = `${NN.h('voucher_no')}<b>${esc(v ? v.doc_no : d.so_phieu_chi)}</b>${EPL.ngay(v ? v.doc_date : d.doc_date)}`;
    const trangThai = d.trang_thai === 'wait' ? 'stt_wait2' : 'stt_' + d.trang_thai;
    if (!d.dong.length) { q('#dnc-to').innerHTML = `<div class="ct-tieu-de">${NN.h('voucher_payment')}</div><div class="ct-trong">${NN.h('no_advance_lines')}</div>`; return; }
    q('#dnc-to').innerHTML = `
      <div class="ct-tieu-de">${NN.h('voucher_payment')}</div>
      <div class="ct-phu">ໃບສະເໜີເບີກເງິນລ່ວງໜ້າ · Advance request</div>
      <div class="ct-ht">${EPL.banChat('tam_ung', d.hinh_thuc || EPL.maBanChat('tam_ung', d.company), d.owner_name)}</div>
      <div class="ct-meta">
        <div><span>${NN.h('payee')}</span><span lang="lo"><b>${esc(d.driver_name || '—')}</b></span></div><div><span>${NN.h('doc_no')}</span><span class="mono"><b>${esc(d.doc_no)}</b></span></div>
        <div><span>${NN.h('truck_no')}</span><span>${esc(d.truck_no)} · <span lang="lo">${esc(d.plate_head)} / ${esc(d.plate_trailer)}</span></span></div><div><span>${NN.h('truck_type')}</span><span>${d.company === 'joint' ? NN.h('co_joint') + ' · ' + esc(d.owner_name || '') : NN.h('co_epl')}</span></div>
        <div style="grid-column:1/-1"><span>${NN.h('purpose')}</span><span lang="lo">${NN.h('purpose_advance', { doc_no: d.doc_no, tuyen: d.origin || d.destination ? (d.origin || '—') + ' → ' + (d.destination || '—') : '—' })}</span></div>
      </div>
      <table class="tbl tbl-compact"><thead><tr><th>#</th><th>${NN.h('item')}</th><th class="num">${NN.h('qty')}</th>${coTien ? `<th class="num">${NN.h('unit_price')}</th><th class="num">${NN.h('amount_lak')}</th><th class="tien">${NN.h('acct_pair')}</th>` : ''}</tr></thead>
        <tbody>${d.dong.map((x, i) => `<tr><td>${i + 1}</td><td lang="lo">${esc(x.item_key ? NN.t(x.item_key) : x.item_name)}</td><td class="num">${so(x.qty)}</td>${coTien ? `<td class="num">${so(x.unit_price)}${x.currency !== 'LAK' ? ' ' + esc(x.currency) : ''}</td><td class="num">${so(x.tien_lak)}</td><td class="tien">${tenTK(x.acct_code)}</td>` : ''}</tr>`).join('')}</tbody></table>
      ${coTien ? `<div class="ct-tong"><div><span>${NN.h('total')}</span><span>${so(d.tong_lak)} LAK</span></div></div>` : ''}
      <div class="ct-tt"><span class="muted">${NN.h('voucher_stage')}:</span> ${tag(d.trang_thai === 'paid' ? 'paid' : d.trang_thai === 'wait' ? 'plain' : 'partial', trangThai)} ${d.tra_tien_xong ? '· ' + NN.h('advance_received') : ''}</div>
      ${khoiQR(v)}
      <div class="ct-ky"><div><div class="line"></div>${NN.h('sg_receiver')}<div class="small muted" lang="lo">${esc(d.driver_name || '')}</div></div><div><div class="line"></div>${NN.h('sg_cashier')}</div><div><div class="line"></div>${NN.h('sg_chief_acct')}</div><div><div class="line"></div>${NN.h('sg_director')}</div></div>`;
  }

  /* ---------------------------------------------------------------- danh sách */
  function veDs() {
    const ds = q('#dnc-ds');
    q('#dnc-dem').innerHTML = NN.h('dn_so_to', { n: DS.length });
    if (!DS.length) { ds.innerHTML = `<div class="dnc-trong">${NN.h('v_empty')}</div>`; return; }
    ds.innerHTML = DS.map(v => {
      const luong = v.kind === 'fuel' ? `${so(v.qty_l, 0)}<small>L</small>`
        : (v.amount_lak == null ? '' : `${so(v.amount_lak)}<small>LAK</small>`);
      const kt = v.chi_ke_toan;
      const nhanKT = !kt ? '' : tag(kt.status === 'da_chi' ? 'paid' : kt.status === 'da_gui' ? 'partial' : 'unpaid',
        kt.status === 'da_chi' ? 'ck_da_chi_ngan' : kt.status === 'da_gui' ? 'ck_cho_chi' : 'ck_loi_ngan');
      return `<button type="button" class="dnc-o ${v.kind} ${v.id === chonId ? 'chon' : ''}" data-id="${esc(v.id)}">
        <i class="soc"></i>
        <div class="so"><span class="dnc-loai ${v.kind}">${NN.h(v.kind === 'fuel' ? 'dn_nhien_lieu' : 'dn_tam_ung')}</span>${esc(v.doc_no)}</div>
        <div class="phai"><span class="luong">${luong}</span>${tag(v.status === 'da_cap' ? 'paid' : v.status === 'huy' ? 'unpaid' : 'plain', 'v_' + v.status)}</div>
        <div class="phu"><span class="mono">${esc(v.trip_doc_no || '')}</span> · ${esc(v.truck_no || '—')} · <span lang="lo">${esc(v.driver_name || '')}</span></div>
        <div class="nho">${EPL.ngay(v.doc_date)}${v.kind === 'fuel' && v.place_name ? ' · <span lang="lo">' + esc(v.place_name) + '</span>' : ''} ${nhanKT}</div>
      </button>`;
    }).join('');
    ds.querySelectorAll('.dnc-o').forEach(b => b.addEventListener('click', () => { chonId = b.dataset.id; phieuLe = null; veDs(); veTo(); }));
  }

  async function veTo() {
    const v = DS.find(x => x.id === chonId);
    q('#dnc-giay').scrollTop = 0;            // tờ cuộn trong khung riêng (01/10): chọn tờ khác thì về đầu tờ
    q('#dnc-mo-phieu').disabled = !v; q('#dnc-in').disabled = !v;
    if (!v) { q('#dnc-so').innerHTML = ''; q('#dnc-kt').innerHTML = ''; q('#dnc-to').innerHTML = `<div class="ct-trong">${NN.h('dn_chon_to')}</div>`; return; }
    veKT(v, v.chi_ke_toan);
    try {
      veTamUng(await API.get(`/api/trips/${v.trip_id}/phieu-chi`), v);
    } catch (e) { q('#dnc-to').innerHTML = `<div class="ct-trong neg">${esc(e.message)}</div>`; }
    // tờ đang chờ thủ quỹ bên kế toán: hỏi lại một lần lúc mở (thủ quỹ có khi vừa ghi sổ)
    if (v.chi_ke_toan && v.chi_ke_toan.status === 'da_gui') await chiKT(v, 'cap-nhat', true);
  }

  /** Trạng thái phiếu chi tạm ứng bên hệ kế toán của tờ đang xem — ở thanh nút, không in ra giấy. */
  function veKT(v, c) {
    const o = q('#dnc-kt');
    if (!c || !c.status) {
      const coGui = AUTH.la('expacct') && ['booked', 'paid'].includes(v.muc_travel) && v.status === 'cho';
      o.innerHTML = coGui ? `<span class="small muted">${NN.h('ck_chua_gui')}</span><button class="btn sm warn" type="button" data-kt="gui">${NN.h('ck_gui_lai')}</button>`
        : (v.status === 'cho' ? `<span class="small muted">${NN.h('ck_cho_ghi_so')}</span>` : '');
    } else if (c.status === 'da_chi') {
      o.innerHTML = `${tag('paid', 'ck_da_chi_ngan')} <span class="small"><b class="mono">${esc(c.document_no || '')}</b> · <span lang="lo">${esc(c.post_by || '')}</span> · ${EPL.ngayGio(c.post_at)}</span>`;
    } else if (c.status === 'da_gui') {
      o.innerHTML = `${tag('partial', 'ck_cho_chi')} <span class="small"><b class="mono">${esc(c.document_no || '')}</b></span><button class="btn sm" type="button" data-kt="cap-nhat">${NN.h('ck_cap_nhat')}</button>`;
    } else {
      o.innerHTML = `${tag('unpaid', 'ck_loi_ngan')} <span class="small neg" title="${esc(c.error_message || '')}">${esc((c.error_message || '').slice(0, 90))}</span>` +
        (AUTH.la('expacct') ? `<button class="btn sm warn" type="button" data-kt="gui">${NN.h('ck_gui_lai')}</button>` : '');
    }
    o.querySelectorAll('[data-kt]').forEach(b => b.addEventListener('click', () => chiKT(v, b.dataset.kt)));
  }

  async function chiKT(v, viec, im) {
    try {
      const c = viec === 'gui' ? await API.post(`/api/trips/${v.trip_id}/chi-ke-toan`) : await API.get(`/api/trips/${v.trip_id}/chi-ke-toan?cap_nhat=1`);
      const cu = v.chi_ke_toan && v.chi_ke_toan.status;
      v.chi_ke_toan = c.status ? c : null;
      if (c.status === 'da_chi' && cu !== 'da_chi') { await tai(); if (!im) EPL.toast(NN.t('ck_da_chi_toast'), 'ok'); return; }
      if (v.id === chonId) veKT(v, v.chi_ke_toan);
      veDs();
      if (!im) EPL.toast(NN.t(c.status === 'da_gui' ? 'ck_cho_chi' : 'ck_loi_ngan'), c.status === 'loi' ? 'loi' : 'ok');
    } catch (e) { if (!im) EPL.baoLoi(e); }
  }

  async function tai() {
    const th = new URLSearchParams({ trang_thai: tt, loai, co: '300' });
    if (tim) th.set('q', tim);
    phieuLe = null;
    try { DS = await API.get('/api/vouchers?' + th.toString()); } catch (e) { DS = []; EPL.baoLoi(e); }
    if (!DS.some(v => v.id === chonId)) chonId = DS[0] ? DS[0].id : null;
    veDs(); await veTo();
  }

  function datSeg() {
    root.querySelectorAll('#dnc-tt button').forEach(b => b.classList.toggle('on', b.dataset.tt === tt));
  }

  /** Mở từ phiếu xuất xe (?id=<phiếu>&loai=advance|fuel&v=<tờ>): tìm đúng tờ của phiếu đó, đặt bộ lọc cho tờ hiện trong
   *  danh sách. Phiếu chưa có tờ tạm ứng (không có khoản tiền mặt) → vẫn hiện nội dung tạm ứng của phiếu. */
  async function moTheoPhieu(t) {
    LINH = await API.get(`/api/trips/${t.id}/vouchers`).catch(() => []);
    const x = LINH.find(v => v.id === t.v && v.kind === 'advance') || LINH.find(v => v.kind === 'advance' && v.status !== 'huy');
    if (x) { chonId = x.id; tt = x.status; tim = ''; datSeg(); await tai(); return true; }
    if ((t.loai || 'advance') === 'advance') {
      await tai();
      chonId = null; phieuLe = t.id; veDs();
      await veLe();
      q('#dnc-mo-phieu').onclick = () => EPL.di('phieu-xuat-xe', { id: t.id });
      return true;
    }
    return false;
  }

  async function veLe() {
    q('#dnc-mo-phieu').disabled = false; q('#dnc-in').disabled = false;
    try { veTamUng(await API.get(`/api/trips/${phieuLe}/phieu-chi`), null); } catch (e) { EPL.baoLoi(e); }
  }

  EPL.modules['de-nghi-chi'] = {
    async init(r, ctx) {
      root = r; DS = []; chonId = null; tim = ''; tt = 'cho'; phieuLe = null;
      const acc = await API.get('/api/acc-codes').catch(() => ({ data: [], source: 'error' }));
      ACC = {}; (acc.data || []).forEach(x => { ACC[x.code] = x; });
      // data-i18n: đổi tiếng thì NN.apDung dịch lại dòng này (trước đây đứng chữ Việt ở tiếng Lào / Anh)
      q('#dnc-nguon').dataset.i18n = acc.source === 'remote' || acc.source === 'cached' ? 'acct_source_remote' : 'acct_source_fallback';
      q('#dnc-nguon').innerHTML = NN.h(q('#dnc-nguon').dataset.i18n);
      root.querySelectorAll('#dnc-tt button').forEach(b => b.addEventListener('click', () => { tt = b.dataset.tt; datSeg(); tai(); }));
      q('#dnc-tim').addEventListener('input', (e) => { clearTimeout(hen); hen = setTimeout(() => { tim = e.target.value.trim(); tai(); }, 300); });
      q('#dnc-in').addEventListener('click', () => window.print());
      q('#dnc-cap-nhat').hidden = !AUTH.la('acct', 'expacct', 'rev', 'treasury', 'cash', 'fuel', 'yard');
      q('#dnc-cap-nhat').addEventListener('click', async () => {
        try {
          const r = await API.post('/api/chi-ke-toan/cap-nhat');
          EPL.toast(NN.t('ck_da_hoi', { n: r.da_hoi, m: r.moi_da_chi }) + (r.loi ? ' — ' + r.loi : ''), r.loi ? 'loi' : 'ok');
          await tai();
        } catch (e) { EPL.baoLoi(e); }
      });
      q('#dnc-mo-phieu').addEventListener('click', () => { const v = DS.find(x => x.id === chonId); if (v) EPL.di('phieu-xuat-xe', { id: v.trip_id }); });
      const t = (ctx && ctx.tham) || {};
      // đường cũ ?loai=fuel → màn Phiếu đề nghị xuất kho
      if (t.loai === 'fuel') return EPL.di('de-nghi-xuat-kho', { id: t.id || '', v: t.v || '' });
      if (t.id && await moTheoPhieu(t)) return;
      await tai();
    },
    onLang() { if (root) { veDs(); if (phieuLe && !chonId) veLe(); else veTo(); } },
    xuatExcel() {
      const T = NN.t;
      return [EPL.xuatSheet(T('nav_de_nghi_chi'), [T('voucher_no'), T('do_kind'), T('doc_no'), T('truck_no'), T('driver'), T('fp_place'), T('qty_l'), T('amount_lak'), T('status'), T('c_date')],
        DS.map(v => [v.doc_no, T(v.kind === 'fuel' ? 'dn_nhien_lieu' : 'dn_tam_ung'), v.trip_doc_no || '', v.truck_no || '', v.driver_name || '', v.place_name || '',
          v.kind === 'fuel' ? EPL.oSo(v.qty_l, 1, 'L') : null, v.kind === 'advance' ? EPL.oSo(v.amount_lak, 0, 'LAK') : null, T('v_' + v.status), EPL.oNgay(v.doc_date)]))];
    },
  };
})();

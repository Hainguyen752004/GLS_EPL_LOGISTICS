/* Phiếu đề nghị chi — ໃບສະເໜີຈ່າຍ (sếp 30/09: tách "Phiếu chi · Phiếu thu" thành hai màn đề nghị chi / đề nghị thu).
 *
 * Hai loại tờ bên mình lập theo bước của chuyến:
 *   · Phiếu đề nghị tạm ứng (PTU). Từ 01/10 (chủ dự án: "chi thật là anh Tune xong update trạng thái về bên mình"): KT Chi phí
 *     ghi sổ mục IV → máy lập phiếu chi "Chi trước" bên hệ kế toán; thủ quỹ chi tiền và GHI SỔ ở đó; trang này hỏi lại, đã ghi
 *     sổ thì tờ thành "Đã cấp" và tài xế xuất phát được. Khối #dnc-kt: trạng thái + Cập nhật / Gửi lại.
 *   · Phiếu đề nghị xuất kho nhiên liệu (PLNL) — mỗi kho EPL một tờ; thủ kho quét QR, cấp dầu theo tờ.
 * Việc cấp thật ở bên kho / bên quỹ (màn Cấp phát trang kế toán). Màn này tìm, xem, in — không cấp, không chi.
 * Chi mục V–VI của chuyến (01/10): khoản quỹ trả ngay thành phiếu chi "Chi khác" bên hệ kế toán lúc KT Chi phí ghi sổ mục —
 * khối #dnc-kt-muc cạnh khối tạm ứng: chờ chi · đã chi · lỗi / bị xoá bên đó, Cập nhật / Gửi lại (GET|POST
 * /api/trips/{id}/chi-muc-ke-toan[/{muc}]).
 *
 * API: GET /api/vouchers?trang_thai=&loai=&q= · GET /api/trips/{id}/phieu-chi · GET /api/trips/{id}/vouchers · GET /api/trips/{id}.
 * Bãi không thấy tiền (anh Khampla A2): máy chủ không gửi số tiền — tờ tạm ứng chỉ khoản mục và số lượng.
 */
(function () {
  const { API, NN, esc, so, tag, AUTH } = EPL;
  let root, DS = [], tt = 'cho', tim = '', chonId = null, ACC = {}, LINH = [], hen = null;
  let phieuLe = null;               // phiếu mở từ phiếu xuất xe mà chưa có tờ tạm ứng — đổi tiếng thì vẽ lại đúng phiếu đó
  let accSan = Promise.resolve();   // danh mục Acc code đang nạp (song song với danh sách) — tờ in chờ nó rồi mới vẽ tên tài khoản
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

  /* Danh sách + tờ in cao VỪA cửa sổ (01/10): đo từ đầu danh sách tới đáy cửa sổ, trừ lề đáy trang, đặt vào --dn-cao (biến
   * CSS chứ không style trực tiếp: quy tắc in vẫn thắng). Số cố định trong CSS chỉ đúng tiếng Việt — chế độ VI + ລາວ (nhãn
   * hai dòng) trang còn cuộn dọc 40–100px. Toạ độ là điểm ảnh màn hình, px CSS bên trong .app (zoom --ty-le) nên chia. */
  let henCao = null;
  function datCao() {
    const ds = root && root.querySelector('.dnc-ds');
    if (!ds || !ds.isConnected) return;
    // lúc mở màn còn dải "Đang tải…" (chung.js: .mod-dang-tai::before) đẩy danh sách xuống — đo sau khi dải đó tắt
    if (root.classList.contains('mod-dang-tai')) { clearTimeout(henCao); henCao = setTimeout(datCao, 120); return; }
    const tl = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--ty-le')) || 1;
    const le = (parseFloat(getComputedStyle(document.getElementById('noi-dung')).paddingBottom) || 0) * tl;
    const cao = (window.innerHeight - (ds.getBoundingClientRect().top + window.scrollY) - le) / tl;
    root.style.setProperty('--dn-cao', Math.max(300, Math.floor(cao)) + 'px');
  }
  const khiDoiCo = () => { clearTimeout(henCao); henCao = setTimeout(datCao, 150); };   // sau khi chung.js đặt lại --ty-le

  function veDs() {
    datCao();
    const ds = q('#dnc-ds');
    q('#dnc-dem').innerHTML = NN.h('dn_so_to', { n: DS.length });
    if (!DS.length) {
      // "Không có phiếu nào đang chờ" chỉ đúng ở thẻ Chờ cấp không tìm; thẻ khác / có chữ tìm thì nói không khớp bộ lọc (01/10)
      const tatCa = !tt && !tim;
      ds.innerHTML = `<div class="dnc-trong"><div>${NN.h(tt === 'cho' && !tim ? 'v_empty' : tatCa ? 'no_data' : 'loc_trong')}</div>
        ${tatCa ? '' : `<button type="button" class="btn sm" data-tat-ca="1">${NN.h('tq_view_all')}</button>`}</div>`;
      const b = ds.querySelector('[data-tat-ca]');
      if (b) b.addEventListener('click', () => { tt = ''; tim = ''; q('#dnc-tim').value = ''; datSeg(); tai(); });
      return;
    }
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
    q('#dnc-giay').hidden = !DS.length;       // danh sách trống: khung trống bên trái nói lý do, bỏ tờ "Chọn một tờ bên trái"
    q('#dnc-mo-phieu').disabled = !v; q('#dnc-in').disabled = !v;
    if (!v) { q('#dnc-so').innerHTML = ''; q('#dnc-kt').innerHTML = ''; q('#dnc-kt-muc').innerHTML = ''; q('#dnc-to').innerHTML = `<div class="ct-trong">${NN.h('dn_chon_to')}</div>`; return; }
    veKT(v, v.chi_ke_toan);
    q('#dnc-kt-muc').innerHTML = '';
    const hoiMuc = chiMuc(v, 'xem');
    // tờ đang chờ thủ quỹ bên kế toán: hỏi lại một lần lúc mở (thủ quỹ có khi vừa ghi sổ) — SONG SONG với tờ in, hai khối
    // riêng trên màn (rà 01/10: trước đây hỏi xong tờ mới hỏi kế toán)
    const hoiKT = v.chi_ke_toan && v.chi_ke_toan.status === 'da_gui' ? chiKT(v, 'cap-nhat', true) : null;
    // trong lúc chờ mà đã chọn tờ khác / danh sách tải lại (kế toán vừa chi) thì tờ cũ không vẽ đè
    const conDung = () => DS.find(x => x.id === chonId) === v;
    try {
      const [d] = await Promise.all([API.get(`/api/trips/${v.trip_id}/phieu-chi`), accSan]);
      if (conDung()) veTamUng(d, v);
    } catch (e) { if (conDung()) q('#dnc-to').innerHTML = `<div class="ct-trong neg">${esc(e.message)}</div>`; }
    if (hoiKT) await hoiKT;
    await hoiMuc;
  }

  /** Phiếu chi mục V / VI bên hệ kế toán của chuyến — cùng kiểu khối tạm ứng; chỉ hiện mục có khoản quỹ trả ngay. */
  function veKTMuc(v, g) {
    const o = q('#dnc-kt-muc');
    o.innerHTML = [['repair', 'V'], ['other', 'VI']].map(([m, la]) => {
      const c = g && g[m]; if (!c || !c.o_ke_toan) return '';
      const lan = (c.lan || []).filter(r => r.status !== 'huy'), r = lan[lan.length - 1];
      const dau = `<b title="${esc(NN.t(m === 'repair' ? 'e_repair' : 'e_other'))}">${la}</b>`;
      if (!r) {
        if (!c.can_chi || !['booked', 'paid'].includes(c.muc)) return '';
        return `<span class="dnc-kt-o">${dau} <span class="small muted">${NN.h('ck_chua_gui')}</span>${AUTH.la('expacct')
          ? `<button class="btn sm warn" type="button" data-kt-muc="gui" data-muc="${m}">${NN.h('ck_gui_lai')}</button>` : ''}</span>`;
      }
      const so = `<span class="small"><b class="mono">${esc(r.document_no || '')}</b></span>`;
      if (r.status === 'da_chi') return `<span class="dnc-kt-o">${dau} ${tag('paid', 'ck_da_chi_ngan')} ${so}</span>`;
      if (r.status === 'da_gui') return `<span class="dnc-kt-o">${dau} ${tag('partial', 'cmt_cho_chi')} ${so}<button class="btn sm" type="button" data-kt-muc="cap-nhat" data-muc="${m}">${NN.h('ck_cap_nhat')}</button></span>`;
      return `<span class="dnc-kt-o">${dau} ${tag('unpaid', r.error_code === 'PHIEU_CHI_MAT' ? 'ck_phieu_mat' : 'ck_loi_ngan')} <span class="small neg" title="${esc(r.error_message || '')}">${esc((r.error_message || '').slice(0, 60))}</span>${AUTH.la('expacct')
        ? `<button class="btn sm warn" type="button" data-kt-muc="gui" data-muc="${m}">${NN.h('ck_gui_lai')}</button>` : ''}</span>`;
    }).join('');
    o.querySelectorAll('[data-kt-muc]').forEach(b => b.addEventListener('click', () => chiMuc(v, b.dataset.ktMuc, b.dataset.muc)));
  }

  async function chiMuc(v, viec, m) {
    try {
      let g;
      if (viec === 'gui') { const c = await API.post(`/api/trips/${v.trip_id}/chi-muc-ke-toan/${m}`); g = { [m]: c }; g = Object.assign(await API.get(`/api/trips/${v.trip_id}/chi-muc-ke-toan`), g); }
      else g = await API.get(`/api/trips/${v.trip_id}/chi-muc-ke-toan` + (viec === 'cap-nhat' ? '?cap_nhat=1' : ''));
      if (DS.find(x => x.id === chonId) !== v) return;
      veKTMuc(v, g);
      if (viec !== 'xem') {
        const lan = ((g[m] || {}).lan || []).filter(x => x.status !== 'huy'), r = lan[lan.length - 1] || {};
        EPL.toast(NN.t(r.status === 'da_chi' ? 'ck_da_chi_ngan' : r.status === 'da_gui' ? 'cmt_cho_chi' : 'ck_loi_ngan'), r.status === 'loi' ? 'loi' : 'ok');
      }
    } catch (e) { if (viec !== 'xem') EPL.baoLoi(e); }
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
    q('#dnc-giay').hidden = false;           // phiếu chưa có tờ tạm ứng: vẫn in nội dung tạm ứng của phiếu, dù danh sách trống
    q('#dnc-mo-phieu').disabled = false; q('#dnc-in').disabled = false;
    try { const [d] = await Promise.all([API.get(`/api/trips/${phieuLe}/phieu-chi`), accSan]); veTamUng(d, null); } catch (e) { EPL.baoLoi(e); }
  }

  EPL.modules['de-nghi-chi'] = {
    async init(r, ctx) {
      root = r; DS = []; chonId = null; tim = ''; tt = 'cho'; phieuLe = null;
      // Danh mục Acc code: EPL.accCodes (nạp một lần, dùng chung mọi màn), chạy SONG SONG với danh sách — rà 01/10 trước đây
      // chờ nó xong mới hỏi danh sách. Chỉ tờ in cần nó (tên tài khoản), nên veTo / veLe chờ accSan trước khi vẽ.
      accSan = EPL.accCodes().then(acc => {
        ACC = {}; (acc.data || []).forEach(x => { ACC[x.code] = x; });
        // data-i18n: đổi tiếng thì NN.apDung dịch lại dòng này (trước đây đứng chữ Việt ở tiếng Lào / Anh)
        const o = r.querySelector('#dnc-nguon');
        o.dataset.i18n = acc.source === 'remote' || acc.source === 'cached' ? 'acct_source_remote' : 'acct_source_fallback';
        o.innerHTML = NN.h(o.dataset.i18n);
      }, () => { ACC = {}; });
      root.querySelectorAll('#dnc-tt button').forEach(b => b.addEventListener('click', () => { tt = b.dataset.tt; datSeg(); tai(); }));
      q('#dnc-tim').addEventListener('input', (e) => { clearTimeout(hen); hen = setTimeout(() => { tim = e.target.value.trim(); tai(); }, 300); });
      q('#dnc-in').addEventListener('click', () => window.print());
      window.removeEventListener('resize', khiDoiCo); window.addEventListener('resize', khiDoiCo);
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
      if (t.id && await moTheoPhieu(t)) return accSan;
      await Promise.all([tai(), accSan]);
    },
    onLang() { if (root) { veDs(); if (phieuLe && !chonId) veLe(); else veTo(); } },
    destroy() { window.removeEventListener('resize', khiDoiCo); clearTimeout(henCao); },
    xuatExcel() {
      const T = NN.t;
      // cột Thành tiền chỉ khi máy chủ trả số tiền: vai không thấy tiền (Bãi…) nhận amount_lak null — tệp xuất cũng không có cột tiền
      const coTien = DS.some(v => v.amount_lak != null);
      return [EPL.xuatSheet(T('nav_de_nghi_chi'), [T('voucher_no'), T('do_kind'), T('doc_no'), T('truck_no'), T('driver'), T('fp_place'), T('qty_l'),
        ...(coTien ? [T('amount_lak')] : []), T('status'), T('c_date')],
        DS.map(v => [v.doc_no, T(v.kind === 'fuel' ? 'dn_nhien_lieu' : 'dn_tam_ung'), v.trip_doc_no || '', v.truck_no || '', v.driver_name || '', v.place_name || '',
          v.kind === 'fuel' ? EPL.oSo(v.qty_l, 1, 'L') : null, ...(coTien ? [v.kind === 'advance' ? EPL.oSo(v.amount_lak, 0, 'LAK') : null] : []),
          T('v_' + v.status), EPL.oNgay(v.doc_date)]))];
    },
  };
})();

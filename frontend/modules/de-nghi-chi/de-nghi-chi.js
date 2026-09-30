/* Phiếu đề nghị chi — ໃບສະເໜີຈ່າຍ (sếp 30/09: tách "Phiếu chi · Phiếu thu" thành hai màn đề nghị chi / đề nghị thu).
 *
 * Hai loại tờ bên mình lập theo bước của chuyến:
 *   · Phiếu đề nghị tạm ứng (PTU) — tài xế cầm đến quỹ; quỹ quét QR, chi theo tờ (PC_TU là phiếu chi thật theo đề nghị).
 *   · Phiếu đề nghị xuất nguyên liệu (PLNL) — mỗi kho EPL một tờ; thủ kho quét QR, cấp dầu theo tờ.
 * Việc cấp thật ở bên kho / bên quỹ (màn Cấp phát trang kế toán). Màn này tìm, xem, in — không cấp, không chi.
 *
 * API: GET /api/vouchers?trang_thai=&loai=&q= · GET /api/trips/{id}/phieu-chi · GET /api/trips/{id}/vouchers · GET /api/trips/{id}.
 * Bãi không thấy tiền (anh Khampla A2): máy chủ không gửi số tiền — tờ tạm ứng chỉ khoản mục và số lượng.
 */
(function () {
  const { API, NN, esc, so, tag } = EPL;
  let root, DS = [], loai = '', tt = 'cho', tim = '', chonId = null, ACC = {}, LINH = [], hen = null;
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
        <div style="grid-column:1/-1"><span>${NN.h('purpose')}</span><span lang="lo">${NN.h('purpose_advance', { doc_no: d.doc_no, tuyen: (d.origin || '') + ' → ' + (d.destination || '') })}</span></div>
      </div>
      <table class="tbl tbl-compact"><thead><tr><th>#</th><th>${NN.h('item')}</th><th class="num">${NN.h('qty')}</th>${coTien ? `<th class="num">${NN.h('unit_price')}</th><th class="num">${NN.h('amount_lak')}</th><th class="tien">${NN.h('acct_pair')}</th>` : ''}</tr></thead>
        <tbody>${d.dong.map((x, i) => `<tr><td>${i + 1}</td><td lang="lo">${esc(x.item_key ? NN.t(x.item_key) : x.item_name)}</td><td class="num">${so(x.qty)}</td>${coTien ? `<td class="num">${so(x.unit_price)}${x.currency !== 'LAK' ? ' ' + esc(x.currency) : ''}</td><td class="num">${so(x.tien_lak)}</td><td class="tien">${tenTK(x.acct_code)}</td>` : ''}</tr>`).join('')}</tbody></table>
      ${coTien ? `<div class="ct-tong"><div><span>${NN.h('total')}</span><span>${so(d.tong_lak)} LAK</span></div></div>` : ''}
      <div class="ct-tt"><span class="muted">${NN.h('voucher_stage')}:</span> ${tag(d.trang_thai === 'paid' ? 'paid' : d.trang_thai === 'wait' ? 'plain' : 'partial', trangThai)} ${d.tra_tien_xong ? '· ' + NN.h('advance_received') : ''}</div>
      ${khoiQR(v)}
      <div class="ct-ky"><div><div class="line"></div>${NN.h('sg_receiver')}<div class="small muted" lang="lo">${esc(d.driver_name || '')}</div></div><div><div class="line"></div>${NN.h('sg_cashier')}</div><div><div class="line"></div>${NN.h('sg_chief_acct')}</div><div><div class="line"></div>${NN.h('sg_director')}</div></div>`;
  }

  /* ---------------------------------------------------------------- tờ đề nghị xuất nguyên liệu
   * Lập LÚC XE CHƯA ĐI nên cố ý KHÔNG in ngày về, km chạy, cân cuối, thành tiền — lúc này chưa ai biết. */
  function veNhienLieu(v, p) {
    q('#dnc-so').innerHTML = `${NN.h('voucher_no')}<b>${esc(v.doc_no)}</b>${EPL.ngay(v.doc_date)}`;
    const o = (k, val, lo) => `<div><span>${NN.h(k)}</span><span ${lo ? 'lang="lo"' : ''}>${esc(val == null || val === '' ? '—' : val)}</span></div>`;
    q('#dnc-to').innerHTML = `
      <div class="ct-tieu-de">${NN.h('v_fuel')}</div>
      <div class="ct-phu">ໃບສະເໜີເບີກນໍ້າມັນ · Fuel issue request</div>
      <div class="ct-ht">${EPL.banChat('xuat', v.hinh_thuc, v.owner_name)}</div>
      <div class="ct-meta">
        ${o('doc_no', p.doc_no)}${o('fp_place', v.place_name, true)}
        ${o('truck_no', p.truck_no)}${o('driver', v.driver_name, true)}
        ${o('plate_head', p.plate_head, true)}${o('plate_trailer', p.plate_trailer, true)}
        ${o('customer', p.customer_name, true)}${o('goods_type', p.goods_type ? NN.t(p.goods_type) : '')}
        ${o('origin', p.origin, true)}${o('dest', p.destination, true)}
        ${o('c_w_origin', p.weight_origin != null ? so(p.weight_origin, 2) + ' ' + NN.t('ton') : '')}${o('d_out', EPL.ngay(p.out_date))}
      </div>
      <div class="ct-tong"><div><span>${NN.h('v_qty_ok')}</span><span>${so(v.qty_l, 1)} L</span></div></div>
      ${khoiQR(v)}
      ${v.status === 'da_cap' ? `<div class="ct-tt"><span class="muted">${NN.h('v_granted_by')}:</span> <b lang="lo">${esc(v.granted_by || '')}</b>
        ${v.granted_qty != null ? ' · ' + NN.h('v_qty_real') + ' <b>' + so(v.granted_qty, 1) + ' L</b>' : ''}</div>` : ''}
      <div class="ct-ky"><div><div class="line"></div>${NN.h('sg_receiver')}<div class="small muted" lang="lo">${esc(v.driver_name || '')}</div></div>
        <div><div class="line"></div>${NN.h('fp_keeper')}</div>
        <div><div class="line"></div>${NN.h('sg_chief_acct')}</div>
        <div><div class="line"></div>${NN.h('sg_director')}</div></div>`;
  }

  /* ---------------------------------------------------------------- danh sách */
  function veDs() {
    const ds = q('#dnc-ds');
    q('#dnc-dem').innerHTML = NN.h('dn_so_to', { n: DS.length });
    if (!DS.length) { ds.innerHTML = `<div class="dnc-trong">${NN.h('v_empty')}</div>`; return; }
    ds.innerHTML = DS.map(v => {
      const luong = v.kind === 'fuel' ? `${so(v.qty_l, 0)}<small>L</small>`
        : (v.amount_lak == null ? '' : `${so(v.amount_lak)}<small>LAK</small>`);
      return `<button type="button" class="dnc-o ${v.kind} ${v.id === chonId ? 'chon' : ''}" data-id="${esc(v.id)}">
        <i class="soc"></i>
        <div class="so"><span class="dnc-loai ${v.kind}">${NN.h(v.kind === 'fuel' ? 'dn_nhien_lieu' : 'dn_tam_ung')}</span>${esc(v.doc_no)}</div>
        <div class="phai"><span class="luong">${luong}</span>${tag(v.status === 'da_cap' ? 'paid' : v.status === 'huy' ? 'unpaid' : 'plain', 'v_' + v.status)}</div>
        <div class="phu"><span class="mono">${esc(v.trip_doc_no || '')}</span> · ${esc(v.truck_no || '—')} · <span lang="lo">${esc(v.driver_name || '')}</span></div>
        <div class="nho">${EPL.ngay(v.doc_date)}${v.kind === 'fuel' && v.place_name ? ' · <span lang="lo">' + esc(v.place_name) + '</span>' : ''}</div>
      </button>`;
    }).join('');
    ds.querySelectorAll('.dnc-o').forEach(b => b.addEventListener('click', () => { chonId = b.dataset.id; veDs(); veTo(); }));
  }

  async function veTo() {
    const v = DS.find(x => x.id === chonId);
    q('#dnc-mo-phieu').disabled = !v; q('#dnc-in').disabled = !v;
    if (!v) { q('#dnc-so').innerHTML = ''; q('#dnc-to').innerHTML = `<div class="ct-trong">${NN.h('dn_chon_to')}</div>`; return; }
    try {
      if (v.kind === 'advance') veTamUng(await API.get(`/api/trips/${v.trip_id}/phieu-chi`), v);
      else veNhienLieu(v, await API.get(`/api/trips/${v.trip_id}`));
    } catch (e) { q('#dnc-to').innerHTML = `<div class="ct-trong neg">${esc(e.message)}</div>`; }
  }

  async function tai() {
    const th = new URLSearchParams({ trang_thai: tt, loai, co: '300' });
    if (tim) th.set('q', tim);
    try { DS = await API.get('/api/vouchers?' + th.toString()); } catch (e) { DS = []; EPL.baoLoi(e); }
    if (!DS.some(v => v.id === chonId)) chonId = DS[0] ? DS[0].id : null;
    veDs(); await veTo();
  }

  function datSeg() {
    root.querySelectorAll('#dnc-loai button').forEach(b => b.classList.toggle('on', b.dataset.loai === loai));
    root.querySelectorAll('#dnc-tt button').forEach(b => b.classList.toggle('on', b.dataset.tt === tt));
  }

  /** Mở từ phiếu xuất xe (?id=<phiếu>&loai=advance|fuel&v=<tờ>): tìm đúng tờ của phiếu đó, đặt bộ lọc cho tờ hiện trong
   *  danh sách. Phiếu chưa có tờ tạm ứng (không có khoản tiền mặt) → vẫn hiện nội dung tạm ứng của phiếu. */
  async function moTheoPhieu(t) {
    LINH = await API.get(`/api/trips/${t.id}/vouchers`).catch(() => []);
    const x = LINH.find(v => v.id === t.v) || LINH.find(v => v.kind === (t.loai || 'advance') && v.status !== 'huy');
    if (x) { chonId = x.id; loai = ''; tt = x.status; tim = ''; datSeg(); await tai(); return true; }
    if ((t.loai || 'advance') === 'advance') {
      await tai();
      chonId = null; veDs();
      q('#dnc-mo-phieu').disabled = false; q('#dnc-in').disabled = false;
      try { veTamUng(await API.get(`/api/trips/${t.id}/phieu-chi`), null); } catch (e) { EPL.baoLoi(e); }
      q('#dnc-mo-phieu').onclick = () => EPL.di('phieu-xuat-xe', { id: t.id });
      return true;
    }
    return false;
  }

  EPL.modules['de-nghi-chi'] = {
    async init(r, ctx) {
      root = r; DS = []; chonId = null; tim = ''; loai = ''; tt = 'cho';
      const acc = await API.get('/api/acc-codes').catch(() => ({ data: [], source: 'error' }));
      ACC = {}; (acc.data || []).forEach(x => { ACC[x.code] = x; });
      q('#dnc-nguon').innerHTML = NN.h(acc.source === 'remote' || acc.source === 'cached' ? 'acct_source_remote' : 'acct_source_fallback');
      root.querySelectorAll('#dnc-loai button').forEach(b => b.addEventListener('click', () => { loai = b.dataset.loai; datSeg(); tai(); }));
      root.querySelectorAll('#dnc-tt button').forEach(b => b.addEventListener('click', () => { tt = b.dataset.tt; datSeg(); tai(); }));
      q('#dnc-tim').addEventListener('input', (e) => { clearTimeout(hen); hen = setTimeout(() => { tim = e.target.value.trim(); tai(); }, 300); });
      q('#dnc-in').addEventListener('click', () => window.print());
      q('#dnc-mo-phieu').addEventListener('click', () => { const v = DS.find(x => x.id === chonId); if (v) EPL.di('phieu-xuat-xe', { id: v.trip_id }); });
      const t = (ctx && ctx.tham) || {};
      if (t.id && await moTheoPhieu(t)) return;
      await tai();
    },
    onLang() { if (root) { veDs(); veTo(); } },
    xuatExcel() {
      const T = NN.t;
      return [EPL.xuatSheet(T('nav_de_nghi_chi'), [T('voucher_no'), T('do_kind'), T('doc_no'), T('truck_no'), T('driver'), T('fp_place'), T('qty_l'), T('amount_lak'), T('status'), T('c_date')],
        DS.map(v => [v.doc_no, T(v.kind === 'fuel' ? 'dn_nhien_lieu' : 'dn_tam_ung'), v.trip_doc_no || '', v.truck_no || '', v.driver_name || '', v.place_name || '',
          v.kind === 'fuel' ? EPL.oSo(v.qty_l, 1, 'L') : null, v.kind === 'advance' ? EPL.oSo(v.amount_lak, 0, 'LAK') : null, T('v_' + v.status), EPL.oNgay(v.doc_date)]))];
    },
  };
})();

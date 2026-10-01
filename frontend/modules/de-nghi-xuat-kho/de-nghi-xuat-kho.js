/* Phiếu đề nghị xuất kho — ໃບສະເໜີເບີກອອກສາງ (chủ dự án 30/09: tách khỏi Phiếu đề nghị chi).
 *
 * Tạm ứng là TIỀN (màn Phiếu đề nghị chi, bên quỹ / công nợ). Đề nghị xuất kho nhiên liệu là việc của KHO (bên anh Toàn):
 * mỗi kho EPL một tờ, thủ kho quét QR rồi cấp. Xe nhà là XUẤT NỘI BỘ; xe thuê mà EPL ứng dầu là XUẤT BÁN cho chủ xe —
 * cả hai đều là xuất kho, chỉ khác bản chất (dòng chữ đậm trên tờ). Màn này tìm, xem, in — không cấp.
 *
 * API: GET /api/vouchers?loai=fuel&trang_thai=&q= (thủ kho chỉ nhận tờ của kho mình) · GET /api/trips/{id}/vouchers ·
 * GET /api/trips/{id} · GET /api/fuel-places.
 */
(function () {
  const { API, NN, esc, so, tag } = EPL;
  let root, DS = [], KHO = [], ht = '', tt = 'cho', kho = '', tim = '', chonId = null, hen = null;
  const q = (s) => root.querySelector(s);

  function khoiQR(v) {
    if (!v) return '';
    return `<div class="ct-qr">
      <img src="${esc(v.qr)}" alt="QR" width="132" height="132">
      <div><div class="small muted">${NN.h('v_qr_hint')}</div>
        <div class="ct-ma">${NN.h('v_code')}: <b class="mono">${esc(v.token)}</b></div>
        <div class="small muted">${tag(v.status === 'da_cap' ? 'paid' : 'plain', 'v_' + v.status)}</div></div></div>`;
  }

  /** Tờ đề nghị xuất kho nhiên liệu — lập LÚC XE CHƯA ĐI nên cố ý KHÔNG in ngày về, km chạy, cân cuối, thành tiền. */
  function veTo(v, p) {
    q('#dnx-so').innerHTML = `${NN.h('voucher_no')}<b>${esc(v.doc_no)}</b>${EPL.ngay(v.doc_date)}`;
    const o = (k, val, lo) => `<div><span>${NN.h(k)}</span><span ${lo ? 'lang="lo"' : ''}>${esc(val == null || val === '' ? '—' : val)}</span></div>`;
    q('#dnx-to').innerHTML = `
      <div class="ct-tieu-de">${NN.h('v_fuel')}</div>
      <div class="ct-phu">ໃບສະເໜີເບີກນໍ້າມັນອອກສາງ · Fuel stock-out request</div>
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

  const loc = () => DS.filter(v => (!ht || v.hinh_thuc === ht) && (!kho || v.place_id === kho));


  /* Danh sách + tờ in cao VỪA cửa sổ (01/10): đo từ đầu danh sách tới đáy cửa sổ, trừ lề đáy trang, đặt vào --dn-cao (biến
   * CSS chứ không style trực tiếp: quy tắc in vẫn thắng). Số cố định trong CSS chỉ đúng tiếng Việt — chế độ VI + ລາວ (nhãn
   * hai dòng) trang còn cuộn dọc 40–100px. Toạ độ là điểm ảnh màn hình, px CSS bên trong .app (zoom --ty-le) nên chia. */
  let henCao = null;
  function datCao() {
    const ds = root && root.querySelector('.dnx-ds');
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
    const ds = loc(), o = q('#dnx-ds');
    q('#dnx-dem').innerHTML = NN.h('dn_so_to', { n: ds.length });
    if (!ds.length) {
      // "Không có phiếu nào đang chờ" chỉ đúng ở thẻ Chờ cấp, mọi hình thức, mọi kho, không tìm; còn lại là không khớp bộ lọc (01/10)
      const tatCa = !tt && !tim && !ht && !kho;
      o.innerHTML = `<div class="dnx-trong"><div>${NN.h(tt === 'cho' && !tim && !ht && !kho ? 'v_empty' : tatCa ? 'no_data' : 'loc_trong')}</div>
        ${tatCa ? '' : `<button type="button" class="btn sm" data-tat-ca="1">${NN.h('tq_view_all')}</button>`}</div>`;
      const b = o.querySelector('[data-tat-ca]');
      if (b) b.addEventListener('click', () => { ht = ''; tt = ''; kho = ''; tim = ''; q('#dnx-kho').value = ''; q('#dnx-tim').value = ''; datSeg(); tai(); });
      return;
    }
    o.innerHTML = ds.map(v => `<button type="button" class="dnx-o ${esc(v.hinh_thuc || '')} ${v.id === chonId ? 'chon' : ''}" data-id="${esc(v.id)}">
      <i class="soc"></i>
      <div class="so"><span class="dnx-ht ${esc(v.hinh_thuc || '')}">${NN.h(v.hinh_thuc === 'xuat_ban' ? 'dnx_xuat_ban' : 'dnx_noi_bo')}</span>${esc(v.doc_no)}</div>
      <div class="phai"><span class="luong">${so(v.status === 'da_cap' && v.granted_qty != null ? v.granted_qty : v.qty_l, 0)}<small>L</small></span>${tag(v.status === 'da_cap' ? 'paid' : v.status === 'huy' ? 'unpaid' : 'plain', 'v_' + v.status)}</div>
      <div class="phu"><span class="mono">${esc(v.trip_doc_no || '')}</span> · ${esc(v.truck_no || '—')} · <span lang="lo">${esc(v.driver_name || '')}</span></div>
      <div class="nho">${EPL.ngay(v.doc_date)} · <span lang="lo">${esc(v.place_name || '')}</span>${v.owner_name ? ' · <span lang="lo">' + esc(v.owner_name) + '</span>' : ''}</div>
    </button>`).join('');
    o.querySelectorAll('.dnx-o').forEach(b => b.addEventListener('click', () => { chonId = b.dataset.id; veDs(); veChon(); }));
  }

  async function veChon() {
    const v = DS.find(x => x.id === chonId);
    q('#dnx-giay').scrollTop = 0;            // tờ cuộn trong khung riêng (01/10): chọn tờ khác thì về đầu tờ
    q('#dnx-giay').hidden = !loc().length;    // danh sách trống: khung trống bên trái nói lý do, bỏ tờ "Chọn một tờ bên trái"
    q('#dnx-mo-phieu').disabled = !v; q('#dnx-in').disabled = !v;
    if (!v) { q('#dnx-so').innerHTML = ''; q('#dnx-to').innerHTML = `<div class="ct-trong">${NN.h('dn_chon_to')}</div>`; return; }
    try { veTo(v, await API.get(`/api/trips/${v.trip_id}`)); } catch (e) { q('#dnx-to').innerHTML = `<div class="ct-trong neg">${esc(e.message)}</div>`; }
  }

  async function tai() {
    const th = new URLSearchParams({ trang_thai: tt, loai: 'fuel', co: '300' });
    if (tim) th.set('q', tim);
    try { DS = await API.get('/api/vouchers?' + th.toString()); } catch (e) { DS = []; EPL.baoLoi(e); }
    const ds = loc();
    if (!ds.some(v => v.id === chonId)) chonId = ds[0] ? ds[0].id : null;
    veDs(); await veChon();
  }

  function datSeg() {
    root.querySelectorAll('#dnx-ht button').forEach(b => b.classList.toggle('on', b.dataset.ht === ht));
    root.querySelectorAll('#dnx-tt button').forEach(b => b.classList.toggle('on', b.dataset.tt === tt));
  }

  EPL.modules['de-nghi-xuat-kho'] = {
    async init(r, ctx) {
      root = r; DS = []; chonId = null; tim = ''; ht = ''; tt = 'cho'; kho = '';
      KHO = (await API.get('/api/fuel-places').catch(() => [])).filter(x => x.owner_type === 'epl');
      // data-i18n trên dòng "Tất cả kho": đổi tiếng thì NN.apDung dịch lại (trước đây còn chữ Việt ở tiếng Lào / Anh)
      q('#dnx-kho').innerHTML = `<option value="" data-i18n="fuel_all_kho">${NN.h('fuel_all_kho')}</option>` + KHO.map(x => `<option value="${esc(x.id)}">${esc(x.name)}</option>`).join('');
      q('#dnx-kho').addEventListener('change', (e) => { kho = e.target.value; veDs(); veChon(); });
      root.querySelectorAll('#dnx-ht button').forEach(b => b.addEventListener('click', () => { ht = b.dataset.ht; datSeg(); veDs(); veChon(); }));
      root.querySelectorAll('#dnx-tt button').forEach(b => b.addEventListener('click', () => { tt = b.dataset.tt; datSeg(); tai(); }));
      q('#dnx-tim').addEventListener('input', (e) => { clearTimeout(hen); hen = setTimeout(() => { tim = e.target.value.trim(); tai(); }, 300); });
      q('#dnx-in').addEventListener('click', () => window.print());
      window.removeEventListener('resize', khiDoiCo); window.addEventListener('resize', khiDoiCo);
      q('#dnx-mo-phieu').addEventListener('click', () => { const v = DS.find(x => x.id === chonId); if (v) EPL.di('phieu-xuat-xe', { id: v.trip_id }); });
      // mở từ phiếu xuất xe / Đề nghị theo DO (?id=<phiếu>&v=<tờ>): đúng tờ của phiếu đó, bộ lọc theo trạng thái của tờ
      const t = (ctx && ctx.tham) || {};
      if (t.id) {
        const vs = await API.get(`/api/trips/${t.id}/vouchers`).catch(() => []);
        const x = vs.find(v => v.id === t.v) || vs.find(v => v.kind === 'fuel' && v.status !== 'huy');
        if (x) { chonId = x.id; tt = x.status; datSeg(); }
      }
      await tai();
    },
    onLang() { if (root) { veDs(); veChon(); } },
    destroy() { window.removeEventListener('resize', khiDoiCo); clearTimeout(henCao); },
    xuatExcel() {
      const T = NN.t;
      return [EPL.xuatSheet(T('nav_de_nghi_xuat_kho'), [T('voucher_no'), T('status'), T('doc_no'), T('truck_no'), T('driver'), T('fp_place'), T('qty_l'), T('v_qty_real'), T('c_date')],
        loc().map(v => [v.doc_no, T(v.hinh_thuc === 'xuat_ban' ? 'dnx_xuat_ban' : 'dnx_noi_bo') + ' · ' + T('v_' + v.status), v.trip_doc_no || '', v.truck_no || '',
          v.driver_name || '', v.place_name || '', EPL.oSo(v.qty_l, 1, 'L'), v.granted_qty != null ? EPL.oSo(v.granted_qty, 1, 'L') : null, EPL.oNgay(v.doc_date)]))];
    },
  };
})();

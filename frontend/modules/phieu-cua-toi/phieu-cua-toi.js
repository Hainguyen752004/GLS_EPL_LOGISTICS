/* Phiếu của tôi — màn tài xế. Máy chủ chỉ trả phiếu của chính tài xế đang đăng nhập. */
(function () {
  const { API, NN, esc, so, tag } = EPL;
  let root, DS = [], CHON = null, DIEM = [];
  let theoDoiId = null, phieuChiaSe = null, lanGuiCuoi = 0, boNghe = null;
  const q = (s) => root.querySelector(s);

  /* ---------------------------------------------------------------- giao hàng hoàn tất (chốt 24/09)
   * Người nhận ký ngay trên điện thoại tài xế. Mất mạng vẫn ký được: lần gửi nằm trong hàng đợi của máy (localStorage,
   * ảnh đã nén), có mạng lại thì tự gửi; `ma_gui` giúp máy chủ không ghi hai lần khi gửi lại. */
  const uid = () => (EPL.AUTH.user ? EPL.AUTH.user.id : 'x');
  const K_HANG = () => 'epl_lao_giao_nhan_' + uid(), K_DS = () => 'epl_lao_pct_ds_' + uid();
  const doc = (k, md) => { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : md; } catch (e) { return md; } };
  const ghi = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch (e) { return false; } };
  const hangDoi = () => doc(K_HANG(), []);
  const choGui = (id) => hangDoi().some(x => x.trip_id === id);
  const laMatMang = (e) => !(e instanceof EPL.LoiAPI) || !e.status;
  const maMoi = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
  const sangBlob = (url) => { const [dau, b64] = url.split(','); const kieu = (dau.match(/:(.*?);/) || [])[1] || 'application/octet-stream';
    const bin = atob(b64); const u8 = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i); return new Blob([u8], { type: kieu }); };

  /** Ảnh nén bằng hàm chung (js/nen_anh.js, ≤ 200 KB) rồi đổi sang dataURL — để nằm được trong hàng đợi khi mất mạng. */
  async function nenAnh(f) {
    const nen = await EPL.nenTep(f);
    const url = await new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(r.result); r.onerror = rej; r.readAsDataURL(nen); });
    return { name: nen.name, type: nen.type, url };
  }

  /** Ô ký: vẽ bằng ngón tay / chuột (Pointer Events), nét mịn theo mật độ điểm ảnh của màn. */
  function oKy(cv) {
    let ve_ = false, co = false, truoc = null;
    const ctx = cv.getContext('2d');
    const dung = () => {
      const r = cv.getBoundingClientRect(), d = window.devicePixelRatio || 1;
      cv.width = Math.max(1, Math.round(r.width * d)); cv.height = Math.max(1, Math.round(r.height * d));
      ctx.setTransform(d, 0, 0, d, 0, 0); ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, r.width, r.height);
      ctx.lineWidth = 2.4; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.strokeStyle = '#11161b'; co = false;
    };
    const diem = (e) => { const r = cv.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
    cv.onpointerdown = (e) => { ve_ = true; truoc = diem(e); cv.setPointerCapture(e.pointerId); e.preventDefault(); };
    cv.onpointermove = (e) => { if (!ve_) return; const p = diem(e); ctx.beginPath(); ctx.moveTo(...truoc); ctx.lineTo(...p); ctx.stroke(); truoc = p; co = true; e.preventDefault(); };
    cv.onpointerup = cv.onpointercancel = () => { ve_ = false; };
    return { dung, coNet: () => co, anh: () => (co ? cv.toDataURL('image/png') : null) };
  }

  let KY = null, ANH = [], VT = null, GH = null;
  function moGiaoHang(id) {
    GH = DS.find(p => p.id === id); if (!GH) return;
    const dlg = q('#pct-gh'); ANH = []; VT = null;
    q('#pct-gh-phieu').innerHTML = `${esc(GH.doc_no)} · <span lang="lo">${esc(GH.customer_name || '')}</span> · <span lang="lo">${esc(GH.destination || '')}</span>`;
    q('#pct-gh-ten').value = GH.pod_receiver || ''; q('#pct-gh-sdt').value = GH.pod_phone || '';
    q('#pct-gh-tt').value = 'du'; q('#pct-gh-ghi').value = '';
    veAnh();
    dlg.showModal();
    KY = oKy(q('#pct-gh-canvas')); requestAnimationFrame(() => KY.dung());
    const gps = q('#pct-gh-gps'); gps.className = 'small pct-gh-gps'; gps.textContent = NN.t('gh_gps_dang');
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition((vt) => {
        VT = { lat: vt.coords.latitude, lng: vt.coords.longitude };
        gps.className = 'small pct-gh-gps co'; gps.textContent = `${NN.t('gh_gps_co')} · ${VT.lat.toFixed(5)}, ${VT.lng.toFixed(5)}`;
      }, () => { gps.textContent = NN.t('gh_gps_khong'); }, { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 });
    } else gps.textContent = NN.t('gh_gps_khong');
  }
  function veAnh() {
    q('#pct-gh-xem-anh').innerHTML = ANH.map((a, i) => `<div class="a">${a.type.startsWith('image/') ? `<img src="${a.url}" alt="">` : '<span class="pdf">PDF</span>'}<button type="button" class="x" data-bo-anh="${i}">×</button></div>`).join('');
    root.querySelectorAll('[data-bo-anh]').forEach(b => b.addEventListener('click', () => { ANH.splice(+b.dataset.boAnh, 1); veAnh(); }));
  }
  async function guiMot(x) {
    const fd = new FormData();
    Object.entries(x.truong).forEach(([k, v]) => { if (v !== null && v !== undefined) fd.append(k, v); });
    if (x.chu_ky) fd.append('chu_ky', sangBlob(x.chu_ky), 'chu-ky-' + x.ma_gui + '.png');
    (x.anh || []).forEach(a => fd.append('anh', sangBlob(a.url), a.name));
    return API.tep(`/api/trips/${x.trip_id}/giao-nhan`, fd);
  }
  async function guiGiaoHang() {
    const ten = q('#pct-gh-ten').value.trim(), chuKy = KY && KY.anh(), tt = q('#pct-gh-tt').value, ghiChu = q('#pct-gh-ghi').value.trim();
    if (!chuKy && !ANH.length) return EPL.toast(NN.t('gh_thieu'), 'loi');
    if (chuKy && !ten) return EPL.toast(NN.t('gh_thieu_ten'), 'loi');
    if (tt !== 'du' && !ghiChu) return EPL.toast(NN.t('gh_thieu_ghi'), 'loi');
    const x = { trip_id: GH.id, doc_no: GH.doc_no, ma_gui: maMoi(), chu_ky: chuKy, anh: ANH.slice(),
      truong: { nguoi_nhan: ten, sdt: q('#pct-gh-sdt').value.trim(), tinh_trang: tt, ghi_chu: ghiChu, luc: new Date().toISOString(),
        lat: VT ? String(VT.lat) : '', lng: VT ? String(VT.lng) : '', ma_gui: '' } };
    x.truong.ma_gui = x.ma_gui;
    const nut = q('#pct-gh-gui'); nut.disabled = true;
    try {
      await guiMot(x);
      q('#pct-gh').close(); EPL.toast(NN.t('gh_da_gui'), 'ok'); await tai();
    } catch (e) {
      if (laMatMang(e)) {
        const hd = hangDoi(); hd.push(x);
        if (!ghi(K_HANG(), hd)) EPL.toast(NN.t('gh_day_bo_nho'), 'loi');
        else { q('#pct-gh').close(); EPL.toast(NN.t('gh_cho_gui'), 'ok'); ve(); }
      } else EPL.baoLoi(e);
    } finally { nut.disabled = false; }
  }
  /** Có mạng lại (hoặc mở màn) → gửi hết hàng đợi. Lỗi nghiệp vụ (phiếu đã khoá, đã ký…) thì bỏ khỏi hàng và báo. */
  async function guiHangDoi() {
    let hd = hangDoi(); if (!hd.length) return;
    let xong = 0;
    for (const x of hd.slice()) {
      try { await guiMot(x); xong++; hd = hd.filter(y => y.ma_gui !== x.ma_gui); }
      catch (e) {
        if (laMatMang(e)) break;
        hd = hd.filter(y => y.ma_gui !== x.ma_gui); EPL.toast(`${x.doc_no}: ${e.message}`, 'loi');
      }
    }
    ghi(K_HANG(), hd);
    if (xong) { EPL.toast(NN.t('gh_da_gui_hang', { n: xong }), 'ok'); await tai().catch(() => {}); }
  }
  async function xemBienBan(id) {
    const p = DS.find(x => x.id === id); if (!p) return;
    let tep = [];
    try { tep = await API.get(`/api/trips/${id}/tep`); } catch (e) { return EPL.baoLoi(e); }
    EPL.bienBan.in(p, tep);
  }

  function tamUng(p) {
    // Khoản tiền mặt tài xế cầm đi: EPL ứng, không phải từ kho. Trạng thái = mục IV.
    // cùng luật máy chủ (la_tien_mat_tai_xe): không tính dầu kho, dầu trạm ghi nợ, phí trừ vào thẻ cao tốc
    const dong = (p.expenses || []).filter(d => d.paid_by_epl && d.source !== 'kho' && !d.ghi_no && !d.toll_card_id && ['fuel', 'travel', 'other'].includes(d.section));
    const r = { USD: p.rate_usd, THB: p.rate_thb, VND: p.rate_vnd, CNY: p.rate_cny || 3000, LAK: 1 };
    const tong = dong.reduce((a, d) => a + d.qty * d.unit_price * (r[d.currency] || 1), 0);
    return { co: dong.length > 0, tong, tt: (p.sections || {}).travel || 'wait' };
  }
  function ve() {
    if (!DS.length) { q('#pct-ds').innerHTML = `<div class="card"><div class="bd muted">${NN.h('no_my_slips')}</div></div>`; return; }
    q('#pct-ds').innerHTML = DS.map(p => {
      const tu = tamUng(p), daTra = tu.tt === 'paid', xong = p.transport_status === 'arrived';
      const bao = (p.events || []).filter(e => e.kind === 'incident' || e.kind === 'repair');
      return `<div class="pct-the" data-id="${p.id}">
        <div style="display:flex;justify-content:space-between;gap:8px;align-items:center"><span class="so">${esc(p.doc_no)}</span>${tag(p.transport_status)}</div>
        <div class="tuyen" lang="lo">${esc(p.origin)} → ${esc(p.destination)}</div>
        <div class="meta"><span>${NN.h('truck_no')}: <b>${esc(p.truck_no)}</b></span><span>${NN.h('customer')}: <b lang="lo">${esc(p.customer_name || '—')}</b></span>
          <span>${NN.h('d_out')}: <b>${EPL.ngay(p.out_date)}</b></span><span>${NN.h('w_origin')}: <b>${so(p.weight_origin, 2)} t</b></span></div>
        <div class="pct-tu ${!tu.co ? 'khong' : daTra ? 'ok' : 'cho'}"><span>${NN.h('advance')}${tu.co ? '' : ' · ' + NN.h('no_expense')}</span><b>${tu.co ? so(tu.tong) + ' LAK · ' + NN.t(daTra ? 'advance_received' : 'stt_' + (tu.tt === 'wait' ? 'wait2' : tu.tt)) : '—'}</b></div>
        ${bao.length ? `<div class="pct-bao">${bao.slice(-3).map(e => `<div>${tag(e.status === 'reported' ? 'partial' : e.status === 'approved' ? 'ok' : 'unpaid', 'st_' + (e.status || 'approved'))}<span lang="lo">${esc(e.note || NN.t('inc_' + (e.incident_type || 'other')))}</span>${e.reported_cost ? `<b>${so(e.reported_cost)} ${esc(e.currency || 'LAK')}</b>` : ''}</div>`).join('')}</div>` : ''}
        ${p.pod_signed || p.pod_no ? `<div class="pct-ky-xong">✓ ${NN.h('gh_da_ky')}: <b lang="lo">${esc(p.pod_receiver || '')}</b>${p.pod_at ? ' · ' + EPL.ngayGio(p.pod_at) : ''}</div>`
          : choGui(p.id) ? `<div class="pct-ky-xong cho">${NN.h('gh_cho_gui')}</div>` : ''}
        <div class="pct-nut">
          ${p.kind === 'giao' && ['transit', 'arrived'].includes(p.transport_status) && !p.locked && !p.pod_signed && !choGui(p.id)
            ? `<button class="btn ok" data-gh="${p.id}">${NN.h('gh_nut')}</button>` : ''}
          ${!xong && p.transport_status === 'dispatched' ? `<button class="btn primary" data-di="${p.id}" ${tu.co && !daTra ? 'disabled title="' + esc(NN.t('depart_blocked')) + '"' : ''}>${NN.h('depart')}</button>` : ''}
          ${p.transport_status === 'transit' ? `<button class="btn ok" data-ve="${p.id}">${NN.h('report_back')}</button>` : ''}
          ${!xong ? `<button class="btn warn" data-bao="${p.id}">${NN.h('report_breakdown')}</button>` : ''}
          ${!xong ? `<button class="btn" data-dau="${p.id}">${NN.h('df_declare')}</button>` : ''}
          ${p.transport_status === 'transit'
            ? `<button class="btn ${phieuChiaSe === p.id ? 'ok' : ''}" data-gps="${p.id}">${NN.h(phieuChiaSe === p.id ? 'gps_stop' : 'gps_share')}</button>` : ''}
          <button class="btn" data-pc="${p.id}">${NN.h('voucher_payment')}</button>
          ${p.pod_signed || p.pod_no ? `<button class="btn" data-bb="${p.id}">${NN.h('gh_xem')}</button>` : ''}
        </div></div>`;
    }).join('');
    root.querySelectorAll('[data-di]').forEach(b => b.addEventListener('click', () => xuatPhat(b.dataset.di)));
    root.querySelectorAll('[data-ve]').forEach(b => b.addEventListener('click', () => baoVe(b.dataset.ve)));
    root.querySelectorAll('[data-bao]').forEach(b => b.addEventListener('click', () => moBao(b.dataset.bao)));
    root.querySelectorAll('[data-pc]').forEach(b => b.addEventListener('click', () => EPL.di('chung-tu', { id: b.dataset.pc })));
    root.querySelectorAll('[data-dau]').forEach(b => b.addEventListener('click', () => moDau(b.dataset.dau)));
    root.querySelectorAll('[data-gps]').forEach(b => b.addEventListener('click', () => batTatGPS(b.dataset.gps)));
    root.querySelectorAll('[data-gh]').forEach(b => b.addEventListener('click', () => moGiaoHang(b.dataset.gh)));
    root.querySelectorAll('[data-bb]').forEach(b => b.addEventListener('click', () => xemBienBan(b.dataset.bb)));
    q('#pct-gps').hidden = !phieuChiaSe;
  }
  async function tai() {
    const mm = q('#pct-mat-mang');
    try {
      const ds = await API.get('/api/trips');
      DS = await Promise.all(ds.map(p => API.get('/api/trips/' + p.id)));   // cần expenses & events; tài xế chỉ có vài phiếu
      ghi(K_DS(), DS); mm.hidden = true;
    } catch (e) {
      if (!laMatMang(e)) throw e;
      DS = doc(K_DS(), []); mm.hidden = false; mm.textContent = NN.t('gh_mat_mang');
    }
    ve();
  }
  /** Tài xế báo đã về: ngày về + km về (C2.1). Máy chủ chỉ ghi hai số và đánh mốc tới điểm cuối;
   *  Bãi cân rồi bấm "Xe đã tới" mới là xong — nên nút này KHÔNG làm phiếu chuyển trạng thái. */
  async function baoVe(id) {
    const p = DS.find(x => x.id === id);
    const v = await EPL.hopNhap(NN.t('report_back'), [
      { id: 'back_date', label: 'd_back', type: 'date', value: p.back_date || EPL.homNay() },
      { id: 'odo_back', label: 'odo_back_prompt', type: 'number', value: p.odo_back ?? '' },
    ], NN.t('save'));
    if (!v) return;
    const body = { back_date: v.back_date }; if (v.odo_back !== '') body.odo_back = v.odo_back;
    try { await API.post(`/api/trips/${id}/bao-ve`, body); EPL.toast(NN.t('report_back_ok'), 'ok'); await tai(); } catch (e) { EPL.baoLoi(e); }
  }
  async function xuatPhat(id) {
    if (!await EPL.hoi(NN.t('depart'), NN.t('confirm_action'))) return;
    try { await API.post(`/api/trips/${id}/transport-status`, { status: 'transit' }); EPL.toast(NN.t('saved'), 'ok'); await tai(); } catch (e) { EPL.baoLoi(e); }
  }
  function moBao(id) {
    CHON = DS.find(p => p.id === id); const dlg = q('#pct-hop');
    q('#pct-f-diem').innerHTML = `<option value="">—</option>` + (CHON.route_stops || []).map(s => `<option value="${s.seq}">${s.seq}. ${esc(s.name)}</option>`).join('');
    q('#pct-f-ghi').value = ''; q('#pct-f-tien').value = ''; NN.apDung(dlg); dlg.returnValue = '';
    dlg.addEventListener('close', async function xong() {
      dlg.removeEventListener('close', xong);
      if (dlg.returnValue !== 'ok') return;
      const body = { incident_type: q('#pct-f-loai').value, note: q('#pct-f-ghi').value, currency: q('#pct-f-tt').value };
      if (q('#pct-f-diem').value) body.stop_seq = +q('#pct-f-diem').value;
      if (q('#pct-f-tien').value !== '') body.reported_cost = EPL.doc(q('#pct-f-tien').value);
      try { await API.post(`/api/trips/${CHON.id}/bao-hong`, body); EPL.toast(NN.t('saved'), 'ok'); await tai(); } catch (e) { EPL.baoLoi(e); }
    });
    dlg.showModal();
  }
  /** Khai đổ dầu DỌC ĐƯỜNG. Chỉ cho chọn trạm bán dầu bên ngoài: dầu lấy ở kho công ty thì phải
   *  có phiếu lĩnh và do thủ kho cấp, không phải tài xế tự khai. */
  function moDau(id) {
    CHON = DS.find(p => p.id === id);
    const ngoai = DIEM.filter(x => x.owner_type === 'ngoai');
    if (!ngoai.length) return EPL.toast(NN.t('no_data'), 'loi');
    const dlg = q('#pct-dau');
    q('#pct-d-diem').innerHTML = ngoai.map(x => `<option value="${x.id}">${esc(x.name)}${x.country === 'VN' ? ' · ' + NN.t('fp_vn2') : ''}</option>`).join('');
    q('#pct-d-lit').value = ''; q('#pct-d-gia').value = ''; q('#pct-d-ghi').value = '';
    NN.apDung(dlg); dlg.returnValue = '';
    dlg.addEventListener('close', async function xong() {
      dlg.removeEventListener('close', xong);
      if (dlg.returnValue !== 'ok') return;
      const lit = EPL.doc(q('#pct-d-lit').value);
      if (lit <= 0) return EPL.toast(NN.t('df_litres') + '?', 'loi');
      const body = { qty_l: lit, place_id: q('#pct-d-diem').value, currency: q('#pct-d-tt').value, note: q('#pct-d-ghi').value };
      // C5.1 (anh Khampla 23/09): tài xế chỉ báo số lít và trạm; giá do KT kho xăng dầu nhập — không gửi giá
      try { await API.post(`/api/trips/${CHON.id}/bao-nhien-lieu`, body); EPL.toast(NN.t('saved'), 'ok'); await tai(); }
      catch (e) { EPL.baoLoi(e); }
    });
    dlg.showModal();
  }

  /* ---------------------------------------------------------------- chia sẻ vị trí
   * Không cần cài app từ chợ ứng dụng: trình duyệt điện thoại có sẵn Geolocation. Tài xế bấm bật,
   * máy theo dõi vị trí và gửi về; văn phòng thấy xe chạy thật trên bản đồ màn Theo dõi tuyến.
   * Giữ trang mở thì mới gửi được — trình duyệt dừng nền khi đóng tab, và đó là giới hạn phải nói
   * thật với người dùng chứ không giấu.
   */
  const NHIP_GIAY = 25;                    // gửi thưa lại cho đỡ tốn pin và sóng

  function ngungGPS() {
    if (theoDoiId != null && navigator.geolocation) navigator.geolocation.clearWatch(theoDoiId);
    theoDoiId = null; phieuChiaSe = null; lanGuiCuoi = 0;
    if (root) { q('#pct-gps').hidden = true; ve(); }
  }

  function batTatGPS(id) {
    if (phieuChiaSe === id) return ngungGPS();
    if (!navigator.geolocation) return EPL.toast(NN.t('gps_nosupport'), 'loi');
    ngungGPS();
    phieuChiaSe = id;
    q('#pct-gps').hidden = false;
    q('#pct-gps-tin').textContent = NN.t('gps_hint');
    theoDoiId = navigator.geolocation.watchPosition(async (vt) => {
      const gio = Date.now();
      if (gio - lanGuiCuoi < NHIP_GIAY * 1000) return;
      lanGuiCuoi = gio;
      const c = vt.coords;
      try {
        await API.post(`/api/trips/${id}/vi-tri`, {
          lat: c.latitude, lng: c.longitude, accuracy_m: c.accuracy,
          speed_kmh: c.speed == null ? null : Math.round(c.speed * 3.6 * 10) / 10,
          heading: c.heading,
        });
        q('#pct-gps-tin').textContent = NN.t('gps_last', { luc: EPL.ngayGio(new Date().toISOString()) });
      } catch (e) {
        // Mất sóng giữa đường là chuyện thường: im lặng, lần sau gửi tiếp.
        if (e instanceof EPL.LoiAPI && e.status) { EPL.baoLoi(e); ngungGPS(); }
      }
    }, (loi) => {
      EPL.toast(NN.t(loi && loi.code === 1 ? 'gps_denied' : 'gps_nosupport'), 'loi');
      ngungGPS();
    }, { enableHighAccuracy: true, maximumAge: 10000, timeout: 20000 });
    ve();
  }

  EPL.modules['phieu-cua-toi'] = {
    async init(r) {
      root = r;
      DIEM = await API.get('/api/fuel-places').catch(() => []);
      q('#pct-gh-xoa-ky').addEventListener('click', () => KY && KY.dung());
      q('#pct-gh-huy').addEventListener('click', () => q('#pct-gh').close());
      q('#pct-gh-gui').addEventListener('click', guiGiaoHang);
      q('#pct-gh-anh').addEventListener('change', async (e) => {
        for (const f of [...e.target.files].slice(0, 5 - ANH.length)) {
          try { ANH.push(await nenAnh(f)); } catch (loi) { EPL.baoLoi(loi); }
        }
        e.target.value = ''; veAnh();
      });
      boNghe = () => guiHangDoi().catch(() => {});
      window.addEventListener('online', boNghe);
      await tai();
      await guiHangDoi().catch(() => {});
    },
    destroy() { ngungGPS(); if (boNghe) window.removeEventListener('online', boNghe); boNghe = null; },
    onLang() { if (root) ve(); },
  };
})();

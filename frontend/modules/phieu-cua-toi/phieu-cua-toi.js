/* Phiếu của tôi — màn tài xế. Máy chủ chỉ trả phiếu của chính tài xế đang đăng nhập. */
(function () {
  const { API, NN, esc, so, tag } = EPL;
  let root, DS = [], CHON = null, DIEM = [];
  let theoDoiId = null, phieuChiaSe = null, lanGuiCuoi = 0;
  const q = (s) => root.querySelector(s);

  function tamUng(p) {
    // Khoản tiền mặt tài xế cầm đi: EPL ứng, không phải từ kho. Trạng thái = mục IV.
    const dong = (p.expenses || []).filter(d => d.paid_by_epl && d.source !== 'kho' && ['fuel', 'travel', 'other'].includes(d.section));
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
        <div class="pct-nut">
          ${!xong && p.transport_status === 'dispatched' ? `<button class="btn primary" data-di="${p.id}" ${tu.co && !daTra ? 'disabled title="' + esc(NN.t('depart_blocked')) + '"' : ''}>${NN.h('depart')}</button>` : ''}
          ${!xong ? `<button class="btn warn" data-bao="${p.id}">${NN.h('report_breakdown')}</button>` : ''}
          ${!xong ? `<button class="btn" data-dau="${p.id}">${NN.h('df_declare')}</button>` : ''}
          ${p.transport_status === 'transit'
            ? `<button class="btn ${phieuChiaSe === p.id ? 'ok' : ''}" data-gps="${p.id}">${NN.h(phieuChiaSe === p.id ? 'gps_stop' : 'gps_share')}</button>` : ''}
          <button class="btn" data-pc="${p.id}">${NN.h('voucher_payment')}</button>
        </div></div>`;
    }).join('');
    root.querySelectorAll('[data-di]').forEach(b => b.addEventListener('click', () => xuatPhat(b.dataset.di)));
    root.querySelectorAll('[data-bao]').forEach(b => b.addEventListener('click', () => moBao(b.dataset.bao)));
    root.querySelectorAll('[data-pc]').forEach(b => b.addEventListener('click', () => EPL.di('chung-tu', { id: b.dataset.pc })));
    root.querySelectorAll('[data-dau]').forEach(b => b.addEventListener('click', () => moDau(b.dataset.dau)));
    root.querySelectorAll('[data-gps]').forEach(b => b.addEventListener('click', () => batTatGPS(b.dataset.gps)));
    q('#pct-gps').hidden = !phieuChiaSe;
  }
  async function tai() {
    const ds = await API.get('/api/trips');
    DS = await Promise.all(ds.map(p => API.get('/api/trips/' + p.id)));   // cần expenses & events; tài xế chỉ có vài phiếu
    ve();
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
      if (q('#pct-d-gia').value !== '') body.unit_price = EPL.doc(q('#pct-d-gia').value);
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
      await tai();
    },
    destroy() { ngungGPS(); },
    onLang() { if (root) ve(); },
  };
})();

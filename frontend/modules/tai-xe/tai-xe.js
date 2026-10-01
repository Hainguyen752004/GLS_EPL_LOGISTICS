/* Tài xế & bằng lái — dựng theo bản thiết kế anh gửi, nối vào API THẬT của dự án.
 *
 *   GET  /api/drivers                     danh sách, kèm số phiếu đã chạy và phiếu đang cầm
 *   GET  /api/drivers/{id}                hồ sơ đầy đủ: lịch sử bằng lái, phiếu gần đây
 *   POST PUT /api/drivers[/{id}]          thêm · sửa hồ sơ
 *   POST /api/drivers/{id}/licenses       ghi bằng mới / gia hạn (máy chủ tự chuyển bằng cũ vào lịch sử)
 *   GET  /api/drivers/{id}/lich?tuan=…    lịch tuần, dựng từ chính các phiếu người này cầm
 *
 * Bản mẫu viết theo một bộ API riêng (/api/tai-xe) với tên trường tiếng Việt. Không dựng API thứ hai
 * cho cùng một dữ liệu: module đổi tên trường ngay ở ranh giới (xem/gui) rồi phần vẽ giữ nguyên.
 *
 * ĐIỂM CHÍNH của màn này là cột **Kết luận**: phần mềm tự trả lời "người này có được điều xe không,
 * vì sao". Luật nằm ở `ketLuan` và mở ra ngoài qua `EPL.taiXe` để màn Phiếu xuất xe dùng chung một
 * luật, không ai chép lại lần thứ hai.
 */
(function () {
  const { API, NN, esc, AUTH } = EPL;
  const NGUONG_SAP_HET = 60;   // ngày — bằng lái "sắp hết hạn"; chuyến xếp xa sẽ bị cảnh báo
  const suaDuoc = () => AUTH.la('yard', 'acct');
  const UI_GOC = { sel: null, chip: null, q: '', vai: '', hang: '', tt: '', tuan: null };
  let root, thoat = null, tx = [], xeList = [], ui = { ...UI_GOC };

  /* ---------- tiện ích ---------- */
  const today = () => new Date(EPL.homNay());
  const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  const fmt = (s) => s ? s.split('-').reverse().join('/') : '—';
  const daysTo = (s) => s ? Math.round((new Date(s + 'T00:00:00') - today()) / 864e5) : null;
  const pill = (k, t) => `<span class="tx-pill ${k}">${esc(t)}</span>`;
  const ST = { running: ['amber', 'xe_st_running'], idle: ['green', 'xe_st_idle'], off: ['muted', 'tx_st_off'] };
  const stPill = (k) => { const s = ST[k] || ST.idle; return pill(s[0], NN.t(s[1])); };
  const initials = (d) => (d.ten_latin || d.ten || '?').split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase();
  // Có ảnh thì hiện ảnh, không thì hai chữ cái đầu như cũ. Thẻ <img> nhận phiên qua ?tk=… như tệp phiếu.
  const urlAnh = (u) => u ? `${u}?tk=${encodeURIComponent(EPL.API.token())}` : null;
  const avatar = (d, sm) => `<span class="tx-avatar ${sm ? 'sm' : ''}">${d.anh ? `<img src="${esc(d.anh)}" alt="">` : esc(initials(d))}</span>`;
  const toast = (m) => EPL.toast(m, 'ok');          // hộp báo chung của khung, không dựng cái thứ hai

  /* ---------- đổi tên trường giữa máy chủ và bản thiết kế ----------
   * Máy chủ nói: name/phone/role/status/license_no/license_valid_to…
   * Bản thiết kế nói: ten/sdt/vai/trang_thai/bang_lai.so/bang_lai.han…
   * Chỉ dịch ở đây. Trạng thái: máy chủ có 4 (available·on_trip·leave·inactive), màn có 3 — người
   * đã nghỉ việc và người đang nghỉ phép đều là "không điều được", gộp vào `off`. */
  const TT_TX = { on_trip: 'running', available: 'idle', leave: 'off', inactive: 'off' };
  const ngay = (v) => (v ? String(v).slice(0, 10) : null);

  function xem(d) {
    return {
      _id: d.id, ma: d.driver_code || d.id, ten: d.name, ten_latin: d.name_latin,
      vai: d.role === 'co' ? 'phu' : 'chinh', sdt: d.phone, ngay_sinh: ngay(d.dob), cmnd: d.id_card,
      ngay_vao: ngay(d.hire_date), dia_chi: d.address, hang_ho_so: d.license_class_hr,
      xe_thuong_lai: d.default_vehicle, xe_thuong_lai_id: d.default_vehicle_id,
      trang_thai: d.active === false ? 'off' : (TT_TX[d.status] || 'idle'),
      _status: d.status, _active: d.active !== false,
      phieu_hien_tai: d.phieu_hien_tai, so_phieu: d.so_phieu, ghi_chu: d.note,
      anh: d.anh_chinh ? urlAnh(d.anh_chinh) : null, anh_ds: (d.anh || []).map(a => ({ ...a, src: urlAnh(a.url) })),
      bang_lai: d.license_no ? {
        so: d.license_no, hang: d.license_type, cap: ngay(d.license_valid_from), han: ngay(d.license_valid_to),
        noi_cap: d.license_issued_by, trang_thai: d.license_status || 'active',
      } : {},
      lich_su_bang: (d.licenses || []).map(l => ({
        so: l.license_no, hang: l.license_type, cap: ngay(l.valid_from), han: ngay(l.valid_to),
        noi_cap: l.issued_by, nguoi_kiem: l.verified_by, ghi_chu: l.note,
      })),
      phieu_gan_day: (d.phieu_gan_day || []).map(p => ({
        _id: p.id, doc_no: p.doc_no, ngay: ngay(p.doc_date), so_xe: p.truck_no,
        tuyen: [p.origin, p.destination].filter(Boolean).join(' → '),
        tt: p.transport_status === 'dispatched' ? 'planned' : p.transport_status,
      })),
      _chi_tiet: !!d.licenses,
    };
  }
  function gui(o) {
    return {
      driver_code: o.ma, name: o.ten, name_latin: o.ten_latin, phone: o.sdt, dob: o.ngay_sinh || null,
      id_card: o.cmnd, address: o.dia_chi, role: o.vai === 'phu' ? 'co' : 'main',
      hire_date: o.ngay_vao || null, license_class_hr: o.hang_ho_so || null,
      default_vehicle_id: o.xe_thuong_lai_id || null,
      // "off" trên màn gộp hai thứ khác nhau; giữ nguyên trạng thái máy chủ nếu nó vốn đã là off,
      // để đổi từ "đang chạy" sang "nghỉ" không âm thầm biến người ta thành đã nghỉ việc.
      status: o.trang_thai === 'running' ? 'on_trip' : o.trang_thai === 'idle' ? 'available'
        : (['leave', 'inactive'].includes(o._status) ? o._status : 'leave'),
      license_no: o.bang_lai.so || null, license_type: o.bang_lai.hang || null,
      license_status: o.bang_lai.trang_thai || 'active',
      license_valid_from: o.bang_lai.cap || null, license_valid_to: o.bang_lai.han || null,
      note: o.ghi_chu,
    };
  }
  /** Nạp hồ sơ đầy đủ khi người dùng chọn một tài xế — danh sách không kèm sẵn lịch sử bằng lái. */
  async function napChiTiet(o) {
    if (!o || o._chi_tiet || !o._id) return o;
    try { Object.assign(o, xem(await API.get('/api/drivers/' + o._id))); } catch (e) { /* mất mạng thì vẫn xem phần đã có */ }
    return o;
  }

  /* ---------- cửa chặn điều phối ----------
   * Sáu kết luận, xếp theo mức nặng dần. Đây là luật DUY NHẤT của dự án về "ai được lái"; màn Phiếu
   * xuất xe gọi EPL.taiXe.ketLuan chứ không tự kiểm lại. */
  function ketLuan(d) {
    const b = d.bang_lai || {};
    if (!b.so) return { k: 'missing', lv: 'bad', pill: 'red' };
    if (b.trang_thai && b.trang_thai !== 'active') return { k: 'inactive', lv: 'bad', pill: 'red' };
    const n = daysTo(b.han);
    if (n != null && n < 0) return { k: 'expired', lv: 'bad', pill: 'red', n };
    if (d.hang_ho_so && b.hang && d.hang_ho_so !== b.hang) return { k: 'mismatch', lv: 'bad', pill: 'red' };
    if (n != null && n <= NGUONG_SAP_HET) return { k: 'soon', lv: 'warn', pill: 'amber', n };
    return { k: 'ok', lv: 'ok', pill: 'green', n };
  }
  const klText = (d) => {
    const v = ketLuan(d), b = d.bang_lai || {};
    const sub = {
      ok: `${NN.t('tx_valid_until')} ${fmt(b.han)}`,
      soon: `${NN.t('tx_expires_in')} ${v.n} ${NN.t('tq_days')} · ${fmt(b.han)}`,
      expired: `${NN.t('tx_expired_on')} ${fmt(b.han)}`,
      inactive: NN.t('tx_lic_' + (b.trang_thai || 'suspended')),
      mismatch: `${NN.t('tx_class_profile')} ${d.hang_ho_so} ≠ ${NN.t('tx_class_license')} ${b.hang}`,
      missing: NN.t('tx_gate_block'),
    }[v.k];
    return { v, title: NN.t('tx_kl_' + v.k), sub };
  };
  const lvClass = (v) => v.lv === 'ok' ? 'g' : v.lv === 'warn' ? 'a' : 'r';

  /* ---------- tải ---------- */
  async function tai() {
    const [a, b] = await Promise.all([API.get('/api/drivers'), API.get('/api/vehicles').catch(() => [])]);
    tx = a.map(xem);
    xeList = b.map(x => ({ _id: x.id, so_xe: x.truck_no, bien: x.plate_head, hang: x.brand_model,
      ro_mooc: x.plate_trailer, trang_thai: x.status === 'on_trip' ? 'running' : x.status === 'maintenance' ? 'repair' : 'idle' }));
    if (!ui.sel || !tx.some(d => d.ma === ui.sel)) ui.sel = tx[0] && tx[0].ma;
    ve(); chonXong();
  }
  async function chonXong() {
    const o = tx.find(d => d.ma === ui.sel);
    if (!o || o._chi_tiet) return;
    await napChiTiet(o);
    if (o.ma === ui.sel) veDetail();
  }

  /* ---------- chip xem nhanh ---------- */
  const chips = () => [
    ['xe_q_total', tx.length, '', () => true],
    ['xe_st_running', tx.filter(d => d.trang_thai === 'running').length, 'info', d => d.trang_thai === 'running'],
    ['xe_st_idle', tx.filter(d => d.trang_thai === 'idle').length, 'good', d => d.trang_thai === 'idle'],
    ['tx_st_off', tx.filter(d => d.trang_thai === 'off').length, 'tan', d => d.trang_thai === 'off'],
    ['tx_q_missing', tx.filter(d => ketLuan(d).k === 'missing').length, 'bad', d => ketLuan(d).k === 'missing'],
    ['tx_q_expired', tx.filter(d => ['expired', 'inactive'].includes(ketLuan(d).k)).length, 'bad', d => ['expired', 'inactive'].includes(ketLuan(d).k)],
    ['tx_q_soon', tx.filter(d => ketLuan(d).k === 'soon').length, 'warn', d => ketLuan(d).k === 'soon'],
    ['tx_q_mismatch', tx.filter(d => ketLuan(d).k === 'mismatch').length, 'bad', d => ketLuan(d).k === 'mismatch'],
    ['tx_q_no_vehicle', tx.filter(d => !d.xe_thuong_lai && d.vai === 'chinh').length, 'warn', d => !d.xe_thuong_lai && d.vai === 'chinh'],
  ];
  function veQuick() {
    const C = chips();
    root.querySelector('#tx-quick').innerHTML = `<span class="lbl">${NN.h('tq_quick')}</span>`
      + C.map((c, i) => `${i === 4 ? '<span class="sep" style="width:1px;height:20px;background:var(--tx-line);margin:0 2px"></span>' : ''}<button type="button" class="tx-chip ${c[2]} ${c[1] ? '' : 'zero'} ${ui.chip === i ? 'on' : ''}" data-i="${i}"><b>${c[1]}</b>${NN.h(c[0])}</button>`).join('')
      + `<span class="right">${NN.h('tx_gate_note')}</span>`;
    root.querySelectorAll('.tx-chip').forEach(el => el.addEventListener('click', () => {
      const i = +el.dataset.i; ui.chip = (ui.chip === i || i === 0) ? null : i; ve();
    }));
  }

  /* ---------- danh sách ---------- */
  function visible() {
    const q = ui.q.trim().toLowerCase(), C = chips(), test = ui.chip != null ? C[ui.chip][3] : () => true;
    return tx.filter(d => test(d) && (!ui.vai || d.vai === ui.vai) && (!ui.hang || (d.bang_lai && d.bang_lai.hang) === ui.hang) && (!ui.tt || d.trang_thai === ui.tt)
      && (!q || [d.ma, d.ten, d.ten_latin, d.sdt, d.xe_thuong_lai, d.bang_lai && d.bang_lai.so].join(' ').toLowerCase().includes(q)));
  }
  function veList() {
    const list = visible(), tb = root.querySelector('#tx-tbl');
    root.querySelector('#tx-count').textContent = `${list.length} / ${tx.length}`;
    if (!list.length) { tb.innerHTML = ''; root.querySelector('#tx-foot').innerHTML = `<span>${NN.h('tx_none')}</span>`; return; }
    if (!list.some(d => d.ma === ui.sel)) ui.sel = list[0].ma;
    tb.innerHTML = `<thead><tr><th>#</th><th>${NN.h('tx_driver')}</th><th>${NN.h('tx_license')}</th><th>${NN.h('tx_validity')}</th><th>${NN.h('tx_vehicle')}</th><th>${NN.h('tx_conclusion')}</th><th>${NN.h('xe_status')}</th></tr></thead><tbody>`
      + list.map((d, i) => {
        const b = d.bang_lai || {}, kl = klText(d);
        return `<tr class="${d.ma === ui.sel ? 'on' : ''}" data-id="${esc(d.ma)}"><td class="muted">${i + 1}</td>
          <td><div class="who">${avatar(d, true)}<div><div class="n lo" style="white-space:nowrap">${esc(d.ten)}${d.ten_latin ? ` <span class="muted" style="font-weight:400">(${esc(d.ten_latin)})</span>` : ''}</div><span class="sub" style="white-space:nowrap"><span class="mono">${esc(d.ma)}</span> · ${NN.h(d.vai === 'phu' ? 'tx_role_assist' : 'tx_role_main')}${d.sdt ? ` · <span class="mono">${esc(d.sdt)}</span>` : ''}</span></div></div></td>
          <td style="white-space:nowrap">${b.so ? `<span class="mono" style="font-weight:600">${esc(b.so)}</span> · ${NN.t('tx_class')} <b>${esc(b.hang || '—')}</b>` : `<span class="muted">—</span>`}<span class="sub">${NN.t('tx_class_profile')}: <b>${esc(d.hang_ho_so || '—')}</b></span></td>
          <td style="white-space:nowrap">${b.so ? `<span class="tx-dots"><i class="${lvClass(kl.v)}"></i></span> <b>${fmt(b.han)}</b><span class="sub">${NN.t('tx_issued')} ${fmt(b.cap)}</span>` : '—'}</td>
          <td class="mono">${d.xe_thuong_lai ? esc(d.xe_thuong_lai) : `<span class="muted">—</span>`}</td>
          <td><span class="tx-verdict">${pill(kl.v.pill, kl.title)}<small>${esc(kl.sub)}</small></span></td>
          <td>${stPill(d.trang_thai)}${d.phieu_hien_tai ? `<span class="sub mono">${esc(d.phieu_hien_tai)}</span>` : ''}</td></tr>`;
      }).join('') + '</tbody>';
    const ok = tx.filter(d => ketLuan(d).lv === 'ok').length;
    root.querySelector('#tx-foot').innerHTML = `<span>${ok}/${tx.length} ${NN.t('tx_kl_ok').toLowerCase()} · ${tx.filter(d => ketLuan(d).lv === 'bad').length} ${NN.t('tx_blocked').toLowerCase()}</span><span>${NN.h('tx_legend')}</span>`;
    tb.querySelectorAll('tbody tr').forEach(tr => {
      tr.addEventListener('click', () => { ui.sel = tr.dataset.id; veList(); veDetail(); openDetail(); chonXong(); });
      tr.addEventListener('dblclick', () => { const d = tx.find(v => v.ma === tr.dataset.id); if (d) napChiTiet(d).then(() => openHoSo(d)); });
    });
  }

  /* ---------- thẻ xem nhanh (chỉ đọc), trượt ra từ mép phải ---------- */
  const gateIcon = {
    ok: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l4 4L19 6"/></svg>',
    warn: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l10 18H2z"/><path d="M12 10v5"/><circle cx="12" cy="18" r=".8"/></svg>',
    bad: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M15 9l-6 6M9 9l6 6"/></svg>',
  };
  function licBlock(d) {
    const b = d.bang_lai;
    if (!b || !b.so) return `<div class="tx-trailer none" style="margin:0 14px 10px">${NN.h('tx_no_license')}</div>`;
    const v = ketLuan(d), n = daysTo(b.han);
    const total = (b.han && b.cap) ? Math.max(1, (new Date(b.han + 'T00:00:00') - new Date(b.cap + 'T00:00:00')) / 864e5) : 1;
    const pct = n == null ? 0 : Math.max(0, Math.min(100, n / total * 100));
    return `<div class="tx-lic"><span class="no">${esc(b.so)}</span><span class="cls">${NN.h('tx_class')}<b>${esc(b.hang || '—')}</b>${d.hang_ho_so && b.hang && d.hang_ho_so !== b.hang ? ` <span class="tx-pill red" style="margin-left:6px">${NN.h('tx_kl_mismatch')}</span>` : ''}</span><span class="cls">${esc(b.noi_cap || '')}</span>
      <div class="bar"><div><div style="display:flex;justify-content:space-between;margin-bottom:4px"><span>${fmt(b.cap)}</span><span><b>${fmt(b.han)}</b></span></div><div class="t"><b class="${lvClass(v)}" style="width:${pct}%"></b></div></div><span class="d">${n == null ? '' : n < 0 ? `${NN.t('xe_expired')} <b>${-n}</b> ${NN.t('tq_days')}` : `${NN.t('xe_left')} <b>${n}</b> ${NN.t('tq_days')}`}</span></div></div>`;
  }
  const gateBox = (d) => { const kl = klText(d); return `<div class="tx-gate ${kl.v.lv}">${gateIcon[kl.v.lv]}<div><b>${esc(kl.title)}</b><small>${esc(kl.sub)}${kl.v.lv !== 'ok' ? ' · ' + NN.t(kl.v.lv === 'bad' ? 'tx_gate_block' : 'tx_gate_far') : ''}</small></div></div>`; };
  const CLOSE_BTN = `<button type="button" class="tx-close" data-close-detail aria-label="${esc(NN.t('close'))}"><svg class="tx-i" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg></button>`;
  function openDetail() { root.querySelector('#tx-detail').classList.add('open'); root.querySelector('#tx-scrim').classList.add('open'); }
  function closeDetail() { root.querySelector('#tx-detail').classList.remove('open'); root.querySelector('#tx-scrim').classList.remove('open'); }

  function veDetail() {
    const box = root.querySelector('#tx-detail'), d = tx.find(v => v.ma === ui.sel);
    if (!d) { box.innerHTML = `<div class="tx-empty">${NN.h('tx_pick')}</div>`; return; }
    const xe = xeList.find(x => x.so_xe === d.xe_thuong_lai), kl = ketLuan(d);
    box.innerHTML = CLOSE_BTN + `
      <div class="tx-head">${avatar(d)}<div class="t"><b class="lo">${esc(d.ten)}</b>${d.ten_latin ? ` <span class="muted">(${esc(d.ten_latin)})</span>` : ''} ${stPill(d.trang_thai)}<small><span class="mono">${esc(d.ma)}</span> · ${NN.h(d.vai === 'phu' ? 'tx_role_assist' : 'tx_role_main')}</small>
        <div class="acts"><button class="tx-btn-sm dark" data-act="open"><svg class="tx-i" viewBox="0 0 24 24"><path d="M14 4h6v6"/><path d="M20 4l-9 9"/><path d="M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5"/></svg>${NN.h('xe_open_profile')}</button><button class="tx-btn-sm" data-act="dispatch" ${d.trang_thai === 'idle' && kl.lv !== 'bad' ? '' : 'disabled'}>${NN.h('new_dispatch')}</button>${d.sdt ? `<a class="tx-btn-sm" href="tel:${esc(d.sdt.replace(/\s/g, ''))}">${NN.h('tx_call')}</a>` : ''}</div></div></div>
      <div class="tx-kv">
        <div><span>${NN.h('tx_phone')}</span><b class="mono">${esc(d.sdt || '—')}</b></div><div><span>${NN.h('tx_dob')}</span><b>${fmt(d.ngay_sinh)}</b></div>
        <div><span>${NN.h('tx_id_card')}</span><b class="mono">${esc(d.cmnd || '—')}</b></div><div><span>${NN.h('tx_joined')}</span><b>${fmt(d.ngay_vao)}</b></div>
        <div><span>${NN.h('tx_address')}</span><b class="lo">${esc(d.dia_chi || '—')}</b></div><div><span>${NN.h('tx_vehicle')}</span><b class="mono">${esc(d.xe_thuong_lai || '—')}</b></div>
        <div><span>${NN.h('xe_trips_done')}</span><b>${d.so_phieu ?? 0}</b></div><div><span>${NN.h('xe_current_trip')}</span><b class="mono">${esc(d.phieu_hien_tai || '—')}</b></div>
      </div>
      <div class="tx-sec">${NN.h('tx_license')}<span class="grow"></span>${pill(kl.pill, klText(d).title)}</div>
      ${licBlock(d)}
      ${gateBox(d)}
      ${d.ghi_chu ? `<div class="tx-note" style="background:var(--tx-tan);color:var(--tx-tan-ink)">${esc(d.ghi_chu)}</div>` : ''}
      ${xe ? `<div class="tx-sec">${NN.h('tx_vehicle')}</div><div class="tx-trailer"><span class="p mono">${esc(xe.so_xe)}</span><span class="m"><span class="lo">${esc(xe.bien || '')}</span>${xe.hang ? ' · ' + esc(xe.hang) : ''}${xe.ro_mooc ? ` · <span class="lo">${esc(xe.ro_mooc)}</span>` : ''}</span>${pill(xe.trang_thai === 'running' ? 'amber' : xe.trang_thai === 'repair' ? 'red' : 'green', NN.t(xe.trang_thai === 'running' ? 'xe_st_running' : xe.trang_thai === 'repair' ? 'xe_st_repair' : 'xe_st_idle'))}</div>` : ''}
      <div class="tx-hint">${NN.h('tx_quick_hint')}</div>`;
    box.querySelector('[data-act="open"]').onclick = () => napChiTiet(d).then(() => openHoSo(d));
    box.querySelector('[data-act="dispatch"]').onclick = () => EPL.di('phieu-xuat-xe', { moi: 1, tai_xe: d._id });
  }

  /* ---------- hộp hồ sơ có tab ---------- */
  const F = (id, label, ctrl, w) => `<div class="f ${w ? 'w' + w : ''}"><label for="${id}">${label}</label>${ctrl}</div>`;
  const I = (id, v, type, ph) => `<input id="${id}" type="${type || 'text'}" value="${esc(v ?? '')}" placeholder="${esc(ph || '')}">`;
  const SEL = (id, opts, v) => `<select id="${id}">${opts.map(([val, lb]) => `<option value="${esc(val)}" ${val === v ? 'selected' : ''}>${esc(lb)}</option>`).join('')}</select>`;
  const HANG = ['C', 'D', 'E', 'FC'];
  const close = () => { root.querySelector('#tx-modal-root').innerHTML = ''; };
  function startOfWeek(d) { const x = new Date(d); const day = (x.getDay() + 6) % 7; x.setDate(x.getDate() - day); x.setHours(0, 0, 0, 0); return x; }

  function openHoSo(o, tab) {
    closeDetail();                     // mở hộp đầy đủ thì thu ngăn trượt, không chồng hai lớp
    const isNew = !o._id;
    o.bang_lai = o.bang_lai || {}; o.lich_su_bang = o.lich_su_bang || [];
    const TABS = [['chung', 'xe_tab_general'], ['bang', 'tx_tab_license'], ['xe', 'tx_tab_vehicle'], ['lich', 'tx_tab_schedule'], ['phieu', 'xe_tab_trips_full']];
    let cur = tab || 'chung', sub = null; const vals = {};
    const rt = root.querySelector('#tx-modal-root');
    rt.innerHTML = `<div class="tx-backdrop"><div class="tx-modal tx-modal--lg">
      <div class="mh"><div><h3>${isNew ? NN.h('tx_add') : NN.h('tx_profile')}: <span class="lo">${esc(o.ten) || '—'}</span></h3><small>${NN.h('tx_edit_sub')}</small></div><button class="x" type="button" data-close><svg class="tx-i" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg></button></div>
      <div class="mtop"><div class="photo">${avatar(o).replace('class="tx-avatar', 'style="width:78px;height:78px;font-size:18px" class="tx-avatar')}
        <div><b>${NN.h('tx_photo')}</b><small id="m-anh-dem">${NN.h('xe_photo_n', { n: (o.anh_ds || []).length })}</small>
          ${suaDuoc() && o._id ? `<label class="tx-btn-sm" style="margin-top:4px;display:inline-block">${NN.h('xe_photo_add')}<input type="file" id="m-anh-them" accept="image/*" hidden></label>` : ''}</div></div>
        <div class="st" style="border-left-color:var(--tx-${ketLuan(o).lv === 'ok' ? 'good' : ketLuan(o).lv === 'warn' ? 'warn' : 'bad'})"><small>${NN.h('tx_conclusion')}</small><b>${esc(klText(o).title)}</b><p>${esc(klText(o).sub)}</p></div></div>
      <div class="mtabs" id="m-tabs"></div><div class="mb" id="m-body"></div>
      <div class="mf"><span class="small muted" id="m-note" style="margin-right:auto"></span><button class="btn" type="button" data-close>${NN.h('cancel')}</button><button class="btn primary" type="button" id="m-save">${NN.h('tx_save')}</button></div></div></div>`;
    rt.querySelectorAll('[data-close]').forEach(b => b.onclick = close);
    // Ảnh tài xế: đưa lên cùng chỗ chứa tệp với ảnh xe; ảnh đầu tiên tự thành ảnh đại diện.
    const oAnh = rt.querySelector('#m-anh-them');
    if (oAnh) oAnh.addEventListener('change', async () => {
      const f = oAnh.files && oAnh.files[0]; if (!f) return;
      let nen; try { nen = await EPL.nenTep(f); } catch (e) { return EPL.baoLoi(e); }
      const fd = new FormData(); fd.append('tep', nen, nen.name);
      try {
        const ds = await EPL.API.tep(`/api/drivers/${o._id}/anh`, fd);
        o.anh_ds = ds.map(a => ({ ...a, src: urlAnh(a.url) }));
        const c = ds.find(a => a.chinh); o.anh = c ? urlAnh(c.url) : null;
        const khung = rt.querySelector('.mtop .tx-avatar');
        if (khung && o.anh) khung.innerHTML = `<img src="${esc(o.anh)}" alt="">`;
        const dem = rt.querySelector('#m-anh-dem'); if (dem) dem.textContent = NN.t('xe_photo_n').replace('{n}', ds.length);
        toast(NN.t('saved'));
        await tai();
      } catch (e) { EPL.baoLoi(e); }
      oAnh.value = '';
    });
    rt.querySelector('.tx-backdrop').addEventListener('click', e => { if (e.target.classList.contains('tx-backdrop')) close(); });
    const body = rt.querySelector('#m-body');
    const grab = () => body.querySelectorAll('[id^="f-"]').forEach(el => { vals[el.id] = el.value; });
    const g = (k) => vals[k];
    const isForm = () => ['chung', 'bang', 'xe'].includes(cur);

    const formTab = () => {
      if (cur === 'chung') return F('f-ma', NN.h('tx_code'), I('f-ma', o.ma, 'text', 'VD: DRV-03')) + F('f-ten', NN.h('tx_name_lo'), I('f-ten', o.ten)) + F('f-latin', NN.h('tx_name_latin'), I('f-latin', o.ten_latin, 'text', 'VD: Bounmi'))
        + F('f-vai', NN.h('tx_role'), SEL('f-vai', [['chinh', NN.t('tx_role_main')], ['phu', NN.t('tx_role_assist')]], o.vai || 'chinh')) + F('f-sdt', NN.h('tx_phone'), I('f-sdt', o.sdt, 'tel')) + F('f-ns', NN.h('tx_dob'), I('f-ns', o.ngay_sinh, 'date'))
        + F('f-cmnd', NN.h('tx_id_card'), I('f-cmnd', o.cmnd)) + F('f-vao', NN.h('tx_joined'), I('f-vao', o.ngay_vao, 'date')) + F('f-hangho', NN.h('tx_class_profile'), SEL('f-hangho', [['', '—'], ...HANG.map(h => [h, h])], o.hang_ho_so || ''))
        + F('f-diachi', NN.h('tx_address'), I('f-diachi', o.dia_chi), 2) + F('f-tt', NN.h('xe_status'), SEL('f-tt', [['idle', NN.t('xe_st_idle')], ['running', NN.t('xe_st_running')], ['off', NN.t('tx_st_off')]], o.trang_thai || 'idle'))
        + F('f-ghichu', NN.h('xe_note'), `<textarea id="f-ghichu" rows="2">${esc(o.ghi_chu || '')}</textarea>`, 3);
      if (cur === 'bang') {
        const b = o.bang_lai;
        return `<div class="sech">${NN.h('tx_current_license')}</div>` + F('f-so', NN.h('tx_lic_no'), I('f-so', b.so, 'text', 'VD: LA-1907720')) + F('f-hang', NN.h('tx_class'), SEL('f-hang', [['', '—'], ...HANG.map(h => [h, h])], b.hang || '')) + F('f-lictt', NN.h('xe_status'), SEL('f-lictt', [['active', NN.t('tx_lic_active')], ['suspended', NN.t('tx_lic_suspended')], ['revoked', NN.t('tx_lic_revoked')]], b.trang_thai || 'active'))
          + F('f-cap', NN.h('tx_issued'), I('f-cap', b.cap, 'date')) + F('f-han', NN.h('tx_expiry'), I('f-han', b.han, 'date')) + F('f-noi', NN.h('tx_issuer'), I('f-noi', b.noi_cap, 'text', 'VD: ກົມຂົນສົ່ງ ວຽງຈັນ'))
          + `<div class="f w3"><div class="small muted">${NN.h('tx_lic_hint')}</div></div>`;
      }
      const xeOpts = [['', NN.t('tx_no_vehicle')], ...xeList.map(x => [x._id, `${x.so_xe}${x.bien ? ' · ' + x.bien : ''}${x.hang ? ' · ' + x.hang : ''}`])];
      // Tab chỉ còn một ô nên không cần dòng tiêu đề nữa — tên tab đã nói rồi, để thêm là đọc hai lần.
      return F('f-xe', NN.h('tx_vehicle'), SEL('f-xe', xeOpts, o.xe_thuong_lai_id || ''), 2) + `<div class="f w3"><div class="small muted">${NN.h('tx_vehicle_hint')}</div></div>`;
    };
    const histRows = () => {
      const h = o.lich_su_bang.slice().sort((a, c) => (c.cap || '').localeCompare(a.cap || ''));
      return h.length ? `<div class="tx-rows tx-rows--box">${h.map(r => `<div class="tx-row"><div class="k"><b>${esc(r.so)}</b> · ${NN.t('tx_class')} <b style="font-family:inherit">${esc(r.hang || '—')}</b><small>${fmt(r.cap)} → ${fmt(r.han)}${r.noi_cap ? ` · <span class="lo">${esc(r.noi_cap)}</span>` : ''}${r.nguoi_kiem ? ` · ${NN.t('tx_checked_by')} <span class="lo">${esc(r.nguoi_kiem)}</span>` : ''}${r.ghi_chu ? ` · ${esc(r.ghi_chu)}` : ''}</small></div><div class="v">${r.so === o.bang_lai.so ? pill('green', NN.t('tx_current')) : pill('muted', NN.t('tx_old'))}</div></div>`).join('')}</div>` : `<div class="tx-empty">${NN.h('tx_no_history')}</div>`;
    };
    const bangExtra = () => `<div class="sech" style="grid-column:1/-1;display:flex;align-items:center;gap:8px;margin-top:14px">${NN.h('tx_renewals')}<span style="flex:1"></span>${suaDuoc() && !isNew ? `<button class="tx-btn-sm dark" type="button" data-sub="renew">+ ${NN.h('tx_renew')}</button>` : ''}</div>
      ${sub === 'renew' ? `<div class="tx-subform" style="grid-column:1/-1"><div class="tx-form">${F('s-so', NN.h('tx_lic_no'), I('s-so', '', 'text', 'VD: LA-2609001'))}${F('s-hang', NN.h('tx_class'), SEL('s-hang', HANG.map(h => [h, h]), o.bang_lai.hang || 'C'))}${F('s-cap', NN.h('tx_issued'), I('s-cap', iso(today()), 'date'))}${F('s-han', NN.h('tx_expiry'), I('s-han', '', 'date'))}${F('s-noi', NN.h('tx_issuer'), I('s-noi', o.bang_lai.noi_cap || ''))}</div><div class="acts"><button class="tx-btn-sm" type="button" data-sub="">${NN.h('cancel')}</button><button class="tx-btn-sm dark" type="button" data-do="renew">${NN.h('tx_renew_save')}</button></div><div class="small muted" style="margin-top:6px">${NN.h('tx_renew_hint')}</div></div>` : ''}
      <div style="grid-column:1/-1">${histRows()}</div>`;

    async function lichTab() {
      const tuan = ui.tuan || iso(startOfWeek(today()));
      let lich = null;
      try { lich = await API.get(`/api/drivers/${encodeURIComponent(o._id)}/lich?tuan=${tuan}`); }
      catch (e) {          // lỗi máy chủ thì nói ra — vẽ tiếp là cả tuần "rảnh", sai sự thật (rà 01/10)
        if (cur === 'lich') body.innerHTML = `<div class="tx-empty neg">${esc(e.message)}</div>`;
        return;
      }
      if (cur !== 'lich') return;          // đã bấm sang tab khác trong lúc chờ — đừng đè lịch lên tab đó
      const days = Array.from({ length: 7 }, (_, i) => { const d = new Date(tuan + 'T00:00:00'); d.setDate(d.getDate() + i); return d; });
      const ev = (dIso) => ((lich && lich.ngay) || []).find(n => n.ngay === dIso);
      const cnt = { trip: 0, off: 0, free: 0 };
      days.forEach(d => { const e = ev(iso(d)); cnt[e && e.su_kien.length ? (e.su_kien.some(s => s.loai === 'off') ? 'off' : 'trip') : 'free']++; });
      body.innerHTML = `<div class="tx-weekhd" style="padding:0 0 6px"><button class="tx-btn-sm" data-w="-1">‹</button><b>${fmt(iso(days[0]))} – ${fmt(iso(days[6]))}</b><button class="tx-btn-sm" data-w="1">›</button><span class="grow"></span>${pill('blue', cnt.trip + ' ' + NN.t('xe_days_trip'))} ${pill('muted', cnt.off + ' ' + NN.t('tx_days_off'))} ${pill('green', cnt.free + ' ' + NN.t('xe_days_free'))}</div>
        <div class="tx-week tx-week--grid">${days.map(d => { const e = ev(iso(d)), isT = iso(d) === iso(today()); return `<div class="tx-day ${isT ? 'today' : ''}"><div class="d">${NN.t('xe_dow_' + d.getDay())}<b>${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}</b></div><div class="evs">${e && e.su_kien.length ? e.su_kien.map(s => `<span class="ev ${s.loai}">${esc(s.text)}</span>`).join('') : `<span class="ev">${NN.h('tx_free_day')}</span>`}</div></div>`; }).join('')}</div>
        <div class="small muted" style="margin-top:8px">${NN.h('tx_schedule_hint')}</div>`;
      body.querySelectorAll('[data-w]').forEach(bt => bt.onclick = () => { const d = new Date(tuan + 'T00:00:00'); d.setDate(d.getDate() + 7 * +bt.dataset.w); ui.tuan = iso(d); lichTab(); });
    }
    const phieuTab = () => {
      const p = o.phieu_gan_day || [];
      return p.length ? `<div class="tx-rows tx-rows--box">${p.map(v => `<div class="tx-row click" data-doc="${esc(v._id)}"><div class="k"><b>${esc(v.doc_no)}</b><small>${fmt(v.ngay)} · ${NN.t('xe_no')} <span class="mono">${esc(v.so_xe || '—')}</span> · <span class="lo">${esc(v.tuyen || '')}</span></small></div><div class="v">${pill(v.tt === 'paid' || v.tt === 'arrived' ? 'green' : v.tt === 'transit' ? 'blue' : 'muted', NN.t('xe_tt_' + v.tt))}</div></div>`).join('')}</div>` : `<div class="tx-empty">${NN.h('xe_no_trips')}</div>`;
    };

    function render() {
      rt.querySelector('#m-tabs').innerHTML = TABS.map(([id, k]) => `<button type="button" class="tx-tab ${cur === id ? 'active' : ''}" data-mt="${id}">${NN.h(k)}</button>`).join('');
      rt.querySelectorAll('[data-mt]').forEach(b => b.onclick = () => { if (isForm()) grab(); cur = b.dataset.mt; sub = null; render(); });
      rt.querySelector('#m-save').style.display = isForm() && suaDuoc() ? '' : 'none';
      rt.querySelector('#m-note').textContent = isForm() ? (cur === 'bang' ? NN.t('tx_bang_note') : '') : NN.t('xe_tab_autosave');
      if (cur === 'lich') { body.innerHTML = `<div class="tx-empty">…</div>`; lichTab(); return; }
      body.innerHTML = isForm() ? `<form class="tx-form" onsubmit="return false">${formTab()}${cur === 'bang' ? bangExtra() : ''}</form>` : phieuTab();
      if (isForm()) Object.entries(vals).forEach(([k, v]) => { const el = body.querySelector('#' + k); if (el) el.value = v; });
      if (!suaDuoc()) {          // vai chỉ xem: hồ sơ vẫn đọc được, nhưng không sửa được ô nào
        body.querySelectorAll('[data-sub]').forEach(b => b.remove());
        body.querySelectorAll('input, select, textarea').forEach(el => { el.disabled = true; });
      }
      body.querySelectorAll('[data-sub]').forEach(b => b.onclick = () => { grab(); sub = b.dataset.sub || null; render(); if (sub) setTimeout(() => { const el = body.querySelector('#s-so'); if (el) el.focus(); }, 30); });
      body.querySelectorAll('.tx-row.click').forEach(el => el.onclick = () => { close(); EPL.di('phieu-xuat-xe', { id: el.dataset.doc }); });
      const d = body.querySelector('[data-do="renew"]'); if (d) d.onclick = renew;
    }

    /** Gia hạn đi thẳng vào máy chủ: POST /licenses ghi một dòng lịch sử VÀ cập nhật bằng hiện hành.
     *  Bản mẫu nuốt lỗi API nên màn báo đã ghi trong khi máy chủ từ chối — ở đây lỗi phải hiện ra. */
    async function renew() {
      const r = {
        license_no: body.querySelector('#s-so').value.trim(), license_type: body.querySelector('#s-hang').value,
        valid_from: body.querySelector('#s-cap').value || null, valid_to: body.querySelector('#s-han').value || null,
        issued_by: body.querySelector('#s-noi').value.trim() || null,
      };
      if (!r.license_no) return body.querySelector('#s-so').focus();
      if (!r.valid_to) return body.querySelector('#s-han').focus();
      try { Object.assign(o, xem(await API.post(`/api/drivers/${o._id}/licenses`, r))); }
      catch (e) { return EPL.baoLoi(e); }
      ['f-so', 'f-hang', 'f-cap', 'f-han', 'f-noi', 'f-lictt'].forEach(k => delete vals[k]);
      sub = null; render();
      await tai();
      toast(`${NN.t('tx_renewed')} ${r.license_no} · ${NN.t('tx_class')} ${r.license_type}`);
    }

    async function save() {
      grab();
      Object.assign(o, {
        ma: g('f-ma') ?? o.ma, ten: g('f-ten') ?? o.ten, ten_latin: g('f-latin') ?? o.ten_latin, vai: g('f-vai') || o.vai,
        sdt: g('f-sdt') ?? o.sdt, ngay_sinh: g('f-ns') ?? o.ngay_sinh, cmnd: g('f-cmnd') ?? o.cmnd,
        ngay_vao: g('f-vao') ?? o.ngay_vao, hang_ho_so: g('f-hangho') ?? o.hang_ho_so, dia_chi: g('f-diachi') ?? o.dia_chi,
        trang_thai: g('f-tt') || o.trang_thai, ghi_chu: g('f-ghichu') ?? o.ghi_chu,
      });
      if (g('f-xe') !== undefined) {
        o.xe_thuong_lai_id = g('f-xe') || null;
        const x = xeList.find(v => v._id === o.xe_thuong_lai_id); o.xe_thuong_lai = x ? x.so_xe : null;
      }
      if (g('f-so') !== undefined) Object.assign(o.bang_lai, { so: g('f-so'), hang: g('f-hang'), trang_thai: g('f-lictt'), cap: g('f-cap'), han: g('f-han'), noi_cap: g('f-noi') });
      if (!o.ten || !o.ten.trim()) return EPL.toast(NN.t('tx_need_name'), 'loi');
      try {
        const d = isNew ? await API.post('/api/drivers', gui(o)) : await API.put('/api/drivers/' + o._id, gui(o));
        ui.sel = d.driver_code || d.id;
      } catch (e) { return EPL.baoLoi(e); }
      close();
      await tai();
      toast(`${NN.t('xe_saved')} ${o.ten}`);
    }
    rt.querySelector('#m-save').onclick = save;
    render();
  }

  function ve() { veQuick(); veList(); veDetail(); }

  EPL.modules['tai-xe'] = {
    async init(r) {
      root = r;
      // Vào lại màn thì về trạng thái gốc như HTML mới. Rà 01/10: gõ tìm / chọn bộ lọc, sang màn khác rồi quay lại thì ô
      // tìm trống mà biến cũ vẫn lọc — bảng "0 / 17", tưởng màn không tải được tài xế nào.
      ui = { ...UI_GOC };
      r.querySelectorAll('[data-i18n-ph]').forEach(el => el.placeholder = NN.t(el.dataset.i18nPh));
      r.querySelector('#tx-q').addEventListener('input', e => { ui.q = e.target.value; veList(); veDetail(); });
      r.querySelector('#tx-f-vai').addEventListener('change', e => { ui.vai = e.target.value; veList(); veDetail(); });
      r.querySelector('#tx-f-hang').addEventListener('change', e => { ui.hang = e.target.value; veList(); veDetail(); });
      r.querySelector('#tx-f-tt').addEventListener('change', e => { ui.tt = e.target.value; veList(); veDetail(); });
      r.querySelector('#tx-refresh').addEventListener('click', () => tai().then(() => toast(NN.t('xe_refreshed'))).catch(EPL.baoLoi));
      const them = r.querySelector('#tx-them'); them.hidden = !suaDuoc();
      them.addEventListener('click', () => openHoSo({ ma: '', ten: '', vai: 'chinh', trang_thai: 'idle', bang_lai: {}, lich_su_bang: [], phieu_gan_day: [], _chi_tiet: true }));
      r.querySelector('#tx-scrim').addEventListener('click', closeDetail);
      r.querySelector('#tx-detail').addEventListener('click', e => { if (e.target.closest('[data-close-detail]')) closeDetail(); });
      // Gỡ phím Esc khi rời màn — gắn mà không tháo thì mỗi lần mở màn lại chồng thêm một cái.
      thoat = (e) => { if (e.key !== 'Escape') return; if (r.querySelector('#tx-modal-root').innerHTML) close(); else closeDetail(); };
      document.addEventListener('keydown', thoat);
      await tai();
    },
    destroy() { if (thoat) document.removeEventListener('keydown', thoat); thoat = null; },
    onLang() { if (root) ve(); },
  };

  // Một luật chặn duy nhất cho cả dự án: màn Phiếu xuất xe đọc ở đây, không tự kiểm lại.
  EPL.taiXe = { ketLuan, NGUONG_SAP_HET };
})();

/**
 * KHÁCH HÀNG & CƠ HỘI (CRM-01 / CRM-02) — màn đứng TRƯỚC Báo giá cước.
 *
 * Tài liệu phạm vi mở chuỗi vận hành bằng "Lead / Customer → Quotation → …".
 * Màn này là bước đầu đó, dựng thành MÀN RIÊNG (`#view-co-hoi`), không nằm
 * chung trang Báo giá và không có vỏ thẻ bọc ngoài.
 *
 *   · Bảng cơ hội (Kanban 5 cột: Mới → Đã liên hệ → Đàm phán → Đã báo giá →
 *     Kết quả). Kéo thẻ để chuyển giai đoạn; hai mốc `Đã báo giá` và `Chốt`
 *     KHÔNG kéo được — máy chủ đặt khi có bằng chứng (lập báo giá / khách
 *     chấp nhận).
 *   · "Lập báo giá" trên thẻ → POST /api/crm/opportunities/{id}/quotation →
 *     mở thẳng phiếu báo giá nháp vừa sinh ở màn Báo giá cước.
 *   · Khách hàng: bảng khách với số cơ hội / báo giá / DO gom từ bảng thật,
 *     bấm một dòng mở hồ sơ (CRM-02) bên phải.
 *
 * Mọi con số đọc từ `/api/crm/*`; màn không tự tính gì.
 */
(function () {
  'use strict';
  const GOC = 'cohoi-root';
  const el = id => document.getElementById(id);
  const base = () => (typeof API_BASE !== 'undefined' ? API_BASE : '');
  const auth = () => (typeof financeAuthHeaders === 'function' ? financeAuthHeaders() : {});

  const GIAI_DOAN = [
    ['new', 'Mới', 'Khách vừa hỏi, chưa ai liên hệ'],
    ['contacted', 'Đã liên hệ', 'Đã nói chuyện, đang lấy yêu cầu'],
    ['negotiating', 'Đàm phán', 'Đang chốt tuyến, hàng, sản lượng'],
    ['quoted', 'Đã báo giá', 'Có báo giá nháp/đã gửi — chờ khách'],
    ['ket-qua', 'Kết quả', 'Chốt (khách chấp nhận) hoặc mất'],
  ];
  const TEN_GD = { new: 'Mới', contacted: 'Đã liên hệ', negotiating: 'Đàm phán', quoted: 'Đã báo giá', won: 'Đã chốt', lost: 'Đã mất' };
  const NGUON = { phone: 'Điện thoại', email: 'Email', web: 'Website', referral: 'Giới thiệu', tender: 'Đấu thầu', existing: 'Khách cũ', other: 'Khác' };
  // Kéo tay được tới đâu — trùng `CHUYEN_TAY` phía máy chủ; máy chủ là người quyết.
  const KEO_DUOC = { new: ['contacted', 'negotiating', 'ket-qua'], contacted: ['new', 'negotiating', 'ket-qua'],
    negotiating: ['contacted', 'ket-qua'], quoted: ['ket-qua'], lost: ['new'], won: [] };

  const S = { che: 'board', ds: [], kpi: null, khach: [], tuyen: [], dsKhach: [], hoSo: null,
    loc: { q: '', owner: '', kpi: '' }, daDung: false, dangSua: null };

  /* ------------------------------------------------------------ tiện ích -- */
  function esc(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  const so = (n, le) => { const x = Number(n); return isFinite(x) ? x.toLocaleString('vi-VN', { maximumFractionDigits: le === undefined ? 1 : le }) : '—'; };
  const tien = n => (n === null || n === undefined || !isFinite(Number(n))) ? '—' : Math.round(Number(n)).toLocaleString('vi-VN') + ' ₫';
  const tan = kg => { const x = Number(kg || 0); return x >= 1000 ? so(x / 1000, 1) + ' tấn' : so(x, 0) + ' kg'; };
  const ngay = iso => { if (!iso) return '—'; const d = new Date(iso); return isNaN(d) ? '—' : d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' }); };
  const ngayGio = iso => { if (!iso) return '—'; const d = new Date(iso); return isNaN(d) ? '—' : d.toLocaleString('vi-VN', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }); };
  const chuCai = t => String(t || '?').trim().split(/[\s._-]+/).map(x => x[0]).join('').slice(0, 2).toUpperCase() || '?';
  const nguoiDangDung = () => (typeof currentUserName !== 'undefined' && currentUserName) || (auth()['X-User-Id']) || 'sales';

  async function api(duong, tuyChon) {
    const tc = Object.assign({ headers: {} }, tuyChon || {});
    tc.headers = Object.assign({ 'Content-Type': 'application/json' }, auth(), tc.headers);
    const tra = await fetch(base() + duong, tc);
    let goi = {};
    try { goi = await tra.json(); } catch (e) { goi = {}; }
    if (!tra.ok) {
      const ct = goi && goi.detail;
      const loi = new Error((ct && ct.message) || goi.message || ('Máy chủ trả về HTTP ' + tra.status));
      loi.ma = ct && ct.code;
      throw loi;
    }
    return goi && Object.prototype.hasOwnProperty.call(goi, 'data') ? goi.data : goi;
  }

  function thongBao(chu, loi) {
    let t = el('chv1-toast');
    if (!t) { t = document.createElement('div'); t.id = 'chv1-toast'; el(GOC).appendChild(t); }
    t.className = 'toast' + (loi ? ' loi' : '');
    t.textContent = chu; t.hidden = false;
    clearTimeout(t._hen); t._hen = setTimeout(() => { t.hidden = true; }, 4200);
  }

  /* --------------------------------------------------------------- khung -- */
  function dungKhung() {
    const goc = el(GOC);
    if (!goc) return false;
    if (S.daDung) return true;
    S.daDung = true;
    goc.classList.add('chv1');
    goc.innerHTML = `
      <div class="hdr">
        <div>
          <h1>Khách hàng &amp; cơ hội</h1>
          <p>Ghi lại yêu cầu của khách trước khi có báo giá. Cơ hội đủ thông tin thì bấm <b>Lập báo giá</b> — báo giá nháp sinh ra kế thừa khách, tuyến, hàng và sản lượng, rồi đi tiếp luồng Báo giá → Lệnh giao hàng → Chuyến.</p>
        </div>
        <div class="acts">
          <div class="seg" id="chv1-che">
            <button type="button" class="on" data-che="board">Bảng cơ hội</button>
            <button type="button" data-che="khach">Khách hàng</button>
          </div>
          <button type="button" class="btn" id="chv1-lam-moi" title="Tải lại">↻</button>
          <button type="button" class="btn pri" id="chv1-them">+ Cơ hội</button>
        </div>
      </div>
      <div id="chv1-kpis" class="kpis"></div>
      <div class="tools" id="chv1-tools">
        <input id="chv1-q" placeholder="Tìm khách, liên hệ, loại hàng, ghi chú…">
        <select id="chv1-owner"><option value="">Người theo: tất cả</option></select>
        <span class="cnt" id="chv1-cnt"></span>
      </div>
      <div id="chv1-board" class="board"></div>
      <div id="chv1-khach" class="kh ch-hide">
        <div class="tbl-wrap"><table class="tbl" id="chv1-bang-khach"></table></div>
        <div class="prof" id="chv1-prof"><div class="rong">Chọn một khách hàng để xem hồ sơ.</div></div>
      </div>
      <dialog class="dlg" id="chv1-dlg"></dialog>`;
    el('chv1-che').addEventListener('click', ev => {
      const b = ev.target.closest('button[data-che]'); if (!b) return;
      doiChe(b.dataset.che);
    });
    el('chv1-them').addEventListener('click', () => moHopThoai(null));
    el('chv1-lam-moi').addEventListener('click', () => nap(true));
    el('chv1-q').addEventListener('input', () => { S.loc.q = el('chv1-q').value.trim(); veBoard(); veBangKhach(); });
    el('chv1-owner').addEventListener('change', () => { S.loc.owner = el('chv1-owner').value; veBoard(); });
    return true;
  }

  function doiChe(che) {
    S.che = che;
    el('chv1-che').querySelectorAll('button').forEach(b => b.classList.toggle('on', b.dataset.che === che));
    el('chv1-board').classList.toggle('ch-hide', che !== 'board');
    el('chv1-khach').classList.toggle('ch-hide', che !== 'khach');
    el('chv1-owner').classList.toggle('ch-hide', che !== 'board');
    el('chv1-q').placeholder = che === 'board' ? 'Tìm khách, liên hệ, loại hàng, ghi chú…' : 'Tìm khách hàng…';
    if (che === 'khach' && !S.dsKhach.length) napKhach();
  }

  /* ----------------------------------------------------------------- nạp -- */
  async function napDuLieuGoc() {
    if (S.khach.length && S.tuyen.length) return;
    const ra = await Promise.allSettled([api('/api/customers'), api('/api/routes')]);
    const mang = x => (x.status === 'fulfilled' ? (Array.isArray(x.value) ? x.value : (x.value && x.value.items) || []) : []);
    S.khach = mang(ra[0]); S.tuyen = mang(ra[1]);
  }

  async function nap(baoXong, lanThu) {
    if (!dungKhung()) return;
    try {
      await napDuLieuGoc();
      const [ds, kpi] = await Promise.all([api('/api/crm/opportunities'), api('/api/crm/opportunities/summary')]);
      S.ds = Array.isArray(ds) ? ds : []; S.kpi = kpi || null;
      veKpi(); veOwner(); veBoard();
      if (S.che === 'khach') await napKhach();
      if (baoXong) thongBao('Đã tải lại.');
    } catch (loi) {
      // Máy chủ đang nạp lại (uvicorn --reload) thì lời gọi đầu hay bị ngắt: thử
      // lại một lần sau 1,5 giây trước khi báo. Và báo NGAY TRÊN BẢNG, không chỉ
      // bằng toast biến mất sau vài giây — màn trống mà không có chữ nào là thứ
      // làm người dùng nghĩ "mất hết dữ liệu".
      if (!lanThu) { setTimeout(() => nap(baoXong, 1), 1500); return; }
      el('chv1-board').innerHTML = `<div class="rong" style="grid-column:1/-1;padding:40px 12px;background:#fff;border:1px dashed #cbd5e1;border-radius:14px">
        <b style="display:block;color:#b91c1c;margin-bottom:6px">Không tải được cơ hội</b>
        <span>${esc(loi.message)}</span><br>
        <button type="button" class="btn sm" id="chv1-thu-lai" style="margin-top:10px">Thử lại</button></div>`;
      const b = el('chv1-thu-lai'); if (b) b.onclick = () => nap(true);
      thongBao('Không tải được cơ hội: ' + loi.message, true);
    }
  }

  async function napKhach() {
    try {
      const ds = await api('/api/crm/customers');
      S.dsKhach = Array.isArray(ds) ? ds : [];
      veBangKhach();
    } catch (loi) { thongBao('Không tải được khách hàng: ' + loi.message, true); }
  }

  /* --------------------------------------------------------------- KPI -- */
  function veKpi() {
    const k = S.kpi || { open: 0, due_follow_up: 0, quoted_waiting: 0, won_30d: 0, lost_30d: 0, win_rate_30d: null, pipeline_kg_per_month: 0 };
    const the = [
      ['', 'Cơ hội đang mở', k.open, tan(k.pipeline_kg_per_month) + '/tháng tiềm năng', 'blue'],
      ['due', 'Cần liên hệ hôm nay', k.due_follow_up, 'đã tới hẹn liên hệ lại', 'amber'],
      ['quoted', 'Đã báo giá, chờ khách', k.quoted_waiting, 'theo dõi ở màn Báo giá', ''],
      ['won', 'Chốt 30 ngày', k.won_30d, (k.win_rate_30d === null || k.win_rate_30d === undefined) ? 'chưa có cơ hội đóng' : 'tỷ lệ chốt ' + Math.round(k.win_rate_30d * 100) + '% · mất ' + k.lost_30d, 'green'],
    ];
    el('chv1-kpis').innerHTML = the.map(x => `<button type="button" class="kpi ${x[4]} ${S.loc.kpi === x[0] ? 'on' : ''}" data-k="${x[0]}">
      <span>${esc(x[1])}</span><b>${esc(x[2])}</b><small>${esc(x[3])}</small></button>`).join('');
    el('chv1-kpis').querySelectorAll('.kpi').forEach(b => b.addEventListener('click', () => {
      S.loc.kpi = S.loc.kpi === b.dataset.k ? '' : b.dataset.k; veKpi(); doiChe('board'); veBoard();
    }));
  }

  function veOwner() {
    const o = el('chv1-owner'); const cu = o.value;
    const ds = [...new Set(S.ds.map(x => x.owner).filter(Boolean))].sort();
    o.innerHTML = '<option value="">Người theo: tất cả</option>' + ds.map(x => `<option value="${esc(x)}">${esc(x)}</option>`).join('');
    o.value = ds.includes(cu) ? cu : '';
  }

  /* ------------------------------------------------------------- board -- */
  function locDs() {
    const q = S.loc.q.toLowerCase(); const bayGio = Date.now();
    return S.ds.filter(x => {
      if (S.loc.owner && x.owner !== S.loc.owner) return false;
      if (q && ![x.id, x.customer_name, x.contact_name, x.cargo_type, x.notes, x.route_name].some(v => String(v || '').toLowerCase().includes(q))) return false;
      if (S.loc.kpi === 'due') return ['new', 'contacted', 'negotiating', 'quoted'].includes(x.stage) && x.next_action_at && new Date(x.next_action_at).getTime() <= bayGio;
      if (S.loc.kpi === 'quoted') return x.stage === 'quoted';
      if (S.loc.kpi === 'won') return x.stage === 'won';
      return true;
    });
  }

  function cotCua(stage) { return (stage === 'won' || stage === 'lost') ? 'ket-qua' : stage; }

  function veBoard() {
    const ds = locDs();
    el('chv1-cnt').textContent = ds.length + ' cơ hội' + (ds.length !== S.ds.length ? ' (đang lọc, tổng ' + S.ds.length + ')' : '');
    el('chv1-board').innerHTML = GIAI_DOAN.map(([ma, ten, goi]) => {
      const trong = ds.filter(x => cotCua(x.stage) === ma);
      const kg = trong.reduce((t, x) => t + Number(x.est_weight_kg || 0) * Number(x.est_trips_per_month || 0), 0);
      return `<div class="col" data-col="${ma}" title="${esc(goi)}">
        <h3><span>${esc(ten)} <span class="n">${trong.length}</span></span>${kg ? `<span class="kg">${esc(tan(kg))}/th</span>` : ''}</h3>
        <div class="cards">${trong.length ? trong.map(veThe).join('') : `<div class="rong">${ma === 'new' ? 'Chưa có cơ hội nào — bấm “+ Cơ hội”.' : 'Kéo thẻ vào đây'}</div>`}</div>
      </div>`;
    }).join('');
    noiKeoTha();
    el('chv1-board').querySelectorAll('.card').forEach(c => {
      c.addEventListener('click', ev => { if (ev.target.closest('button')) return; moHopThoai(c.dataset.id); });
    });
    el('chv1-board').querySelectorAll('button[data-act]').forEach(b => b.addEventListener('click', ev => {
      ev.stopPropagation(); hanhDong(b.dataset.act, b.dataset.id);
    }));
  }

  function veThe(x) {
    const bayGio = Date.now();
    const hen = x.next_action_at ? new Date(x.next_action_at) : null;
    const treHen = hen && hen.getTime() <= bayGio && !['won', 'lost'].includes(x.stage);
    const tuyen = x.route_name || [x.origin_text, x.destination_text].filter(Boolean).join(' → ') || '<i>chưa chọn tuyến</i>';
    const nut = [];
    if (['new', 'contacted', 'negotiating'].includes(x.stage)) nut.push(`<button type="button" class="q" data-act="bao-gia" data-id="${esc(x.id)}" title="Sinh báo giá nháp kế thừa cơ hội này">Lập báo giá</button>`);
    if (x.stage === 'quoted' && x.quotation_id) nut.push(`<button type="button" class="q" data-act="mo-bao-gia" data-id="${esc(x.id)}">Mở ${esc(x.quotation_id)}</button>`);
    if (x.stage === 'won' && x.quotation_id) nut.push(`<button type="button" data-act="mo-bao-gia" data-id="${esc(x.id)}">Xem báo giá</button>`);
    if (x.stage === 'lost') nut.push(`<button type="button" data-act="mo-lai" data-id="${esc(x.id)}">Mở lại</button>`);
    return `<div class="card s-${esc(x.stage)}" draggable="${KEO_DUOC[x.stage] && KEO_DUOC[x.stage].length ? 'true' : 'false'}" data-id="${esc(x.id)}" data-stage="${esc(x.stage)}">
      <div class="t"><b>${esc(x.customer_name || '—')}</b><span class="id">${esc(x.id)}</span></div>
      <div class="rt">${tuyen}${x.cargo_type ? ' · ' + esc(x.cargo_type) : ''}</div>
      <div class="meta">
        ${x.est_weight_kg ? `<span class="chip">${esc(tan(x.est_weight_kg))}</span>` : ''}
        ${x.est_trips_per_month ? `<span class="chip">${esc(x.est_trips_per_month)} chuyến/th</span>` : ''}
        ${x.expected_price ? `<span class="chip">mong ${esc(tien(x.expected_price))}</span>` : ''}
        ${x.stage === 'won' ? '<span class="chip green">Khách đã chấp nhận</span>' : ''}
        ${x.stage === 'lost' ? `<span class="chip red" title="${esc(x.lost_reason || '')}">Mất · ${esc((x.lost_reason || '').slice(0, 28))}</span>` : ''}
        ${x.stage === 'quoted' ? (x.quotation_expired
          ? '<span class="chip red" title="Báo giá đã quá ngày hiệu lực. Gia hạn ở màn Báo giá, hoặc kéo thẻ vào Kết quả để đánh mất.">Báo giá hết hạn</span>'
          : '<span class="chip violet">chờ khách</span>') : ''}
        ${hen && !['won', 'lost'].includes(x.stage) ? `<span class="chip ${treHen ? 'red' : 'blue'}" title="Hẹn liên hệ lại">⏰ ${esc(ngayGio(x.next_action_at))}</span>` : ''}
      </div>
      <div class="ft">
        <span class="av" title="${esc(x.owner || '')}">${esc(chuCai(x.owner))}</span>
        <div class="acts">${nut.join('')}</div>
      </div>
    </div>`;
  }

  // Cung loi voi may chu (CRM_STAGE_TRANSITION_INVALID): hai moc nay phai co bang chung.
  const VI_SAO_KHONG_KEO = {
    quoted: 'Dùng nút “Lập báo giá” — giai đoạn Đã báo giá chỉ đặt khi có báo giá thật.',
    'ket-qua': 'Chốt do khách chấp nhận báo giá ở màn Báo giá — không đặt tay. Kéo vào đây chỉ để đánh mất.',
  };
  const TEN_COT = Object.fromEntries(GIAI_DOAN.map(([ma, ten]) => [ma, ten]));
  function noiKeoTha() {
    let keo = null, daNhac = null;
    el('chv1-board').querySelectorAll('.card[draggable="true"]').forEach(c => {
      c.addEventListener('dragstart', ev => { keo = c; c.classList.add('dragging'); ev.dataTransfer.effectAllowed = 'move'; ev.dataTransfer.setData('text/plain', c.dataset.id); });
      c.addEventListener('dragend', () => { c.classList.remove('dragging'); keo = null; daNhac = null; el('chv1-board').querySelectorAll('.col.over').forEach(k => k.classList.remove('over')); });
    });
    el('chv1-board').querySelectorAll('.col').forEach(col => {
      col.addEventListener('dragover', ev => {
        if (!keo) return;
        const dich = col.dataset.col;
        if (!(KEO_DUOC[keo.dataset.stage] || []).includes(dich)) {
          // Cot khong nhan tha thi trinh duyet chi bat the ve cho cu, khong noi
          // gi. Nhac MOT lan cho moi lan keo — cung mot cau voi may chu.
          if (daNhac !== dich) { daNhac = dich; thongBao(VI_SAO_KHONG_KEO[dich] || `Không kéo tay từ ${TEN_GD[keo.dataset.stage] || keo.dataset.stage} sang ${TEN_COT[dich] || dich}.`, true); }
          return;
        }
        ev.preventDefault(); col.classList.add('over');
      });
      col.addEventListener('dragleave', () => col.classList.remove('over'));
      col.addEventListener('drop', ev => {
        ev.preventDefault(); col.classList.remove('over');
        const id = ev.dataTransfer.getData('text/plain'); const dich = col.dataset.col;
        if (!id) return;
        if (dich === 'ket-qua') { danhMat(id); return; }
        doiGiaiDoan(id, dich);
      });
    });
  }

  /* ------------------------------------------------------- hành động -- */
  const timCoHoi = id => S.ds.find(x => x.id === id);

  async function doiGiaiDoan(id, stage, lyDo) {
    const x = timCoHoi(id); if (!x) return;
    try {
      const kq = await api('/api/crm/opportunities/' + encodeURIComponent(id) + '/stage', {
        method: 'PUT', body: JSON.stringify({ stage, expected_version: x.version, lost_reason: lyDo || undefined }),
      });
      capNhat(kq); thongBao(`${id} → ${TEN_GD[stage] || stage}.`);
    } catch (loi) { thongBao(loi.message, true); }
  }

  function danhMat(id) {
    const lyDo = window.prompt('Lý do mất cơ hội (bắt buộc):', '');
    if (lyDo === null) return;
    if (!lyDo.trim()) { thongBao('Đánh mất cơ hội phải ghi lý do.', true); return; }
    doiGiaiDoan(id, 'lost', lyDo.trim());
  }

  async function lapBaoGia(id) {
    const x = timCoHoi(id); if (!x) return;
    if (!x.route_id) { thongBao('Chọn tuyến (Dữ liệu gốc) cho cơ hội trước — báo giá tính km và chặng từ tuyến.', true); moHopThoai(id); return; }
    if (!window.confirm(`Lập báo giá nháp cho ${x.customer_name} · ${x.route_name || ''}?\nBáo giá sẽ kế thừa khách, tuyến, ${tan(x.est_weight_kg)} và ${x.est_trips_per_month} chuyến/tháng; anh bổ sung loại xe và giá ở màn Báo giá.`)) return;
    try {
      const kq = await api('/api/crm/opportunities/' + encodeURIComponent(id) + '/quotation', {
        method: 'POST', body: JSON.stringify({ expected_version: x.version }),
      });
      capNhat(kq);
      thongBao('Đã lập báo giá ' + (kq.quotation && kq.quotation.id) + '. Đang mở…');
      moBaoGia(kq.quotation && kq.quotation.id);
    } catch (loi) { thongBao(loi.message, true); }
  }

  function moBaoGia(qid) {
    if (!qid) return;
    if (typeof window.switchView === 'function') window.switchView('crm-sales', 'qtv2-root');
    setTimeout(() => { if (window.BaoGiaV2 && typeof window.BaoGiaV2.moPhieu === 'function') window.BaoGiaV2.moPhieu(qid); }, 120);
  }

  function hanhDong(act, id) {
    const x = timCoHoi(id); if (!x) return;
    if (act === 'bao-gia') return lapBaoGia(id);
    if (act === 'mo-bao-gia') return moBaoGia(x.quotation_id);
    if (act === 'mo-lai') return doiGiaiDoan(id, 'new');
  }

  function capNhat(kq) {
    if (!kq || !kq.id) return;
    const i = S.ds.findIndex(x => x.id === kq.id);
    if (i >= 0) S.ds[i] = Object.assign({}, S.ds[i], kq); else S.ds.unshift(kq);
    api('/api/crm/opportunities/summary').then(k => { S.kpi = k; veKpi(); }).catch(() => {});
    veOwner(); veBoard();
  }

  /* ------------------------------------------------------- hộp thoại -- */
  function moHopThoai(id) {
    const dlg = el('chv1-dlg'); if (!dlg) return;
    const x = id ? (timCoHoi(id) || {}) : { stage: 'new', source: 'phone', owner: nguoiDangDung(), est_weight_kg: '', est_trips_per_month: '' };
    S.dangSua = id || null;
    const dong = !!id && (x.stage === 'won');
    const k = dong ? 'disabled' : '';
    const optKhach = '<option value="">— Khách chưa có trong danh mục —</option>' + S.khach.map(c => `<option value="${esc(c.id)}" ${c.id === x.customer_id ? 'selected' : ''}>${esc(c.name || c.id)}</option>`).join('');
    const optTuyen = '<option value="">— Chưa chọn tuyến —</option>' + S.tuyen.map(r => `<option value="${esc(r.id)}" ${r.id === x.route_id ? 'selected' : ''}>${esc(r.name || r.id)}${r.distance_km ? ' · ' + so(r.distance_km) + ' km' : ''}</option>`).join('');
    const henLocal = x.next_action_at ? (() => { const d = new Date(x.next_action_at); const p = n => String(n).padStart(2, '0'); return isNaN(d) ? '' : `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`; })() : '';
    // Bo cuc theo mau nhap_UI__duan/co-hoi-moi.html: moi muc la mot hang
    // hai cot (ten muc + chu giai | luoi 6 cot). Cac id chv1-f-* giu nguyen vi
    // docForm() va luu() doc theo id; doi id la form lang le gui rong.
    dlg.innerHTML = `
      <header class="hd">
        <div>
          <h3 id="chv1-dlg-ttl">${id ? esc(id) : 'Cơ hội mới'}</h3>
          <p>${id ? esc(TEN_GD[x.stage] || x.stage) + (x.quotation_id ? ' · báo giá ' + esc(x.quotation_id) : '') : 'Khách hỏi gì, ghi lại đây. Chưa cần đủ thông tin để báo giá.'}</p>
        </div>
        <button type="button" class="x" id="chv1-dlg-x" aria-label="Đóng"><svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M2 2l10 10M12 2L2 12"/></svg></button>
      </header>
      <div class="bd">
        ${dong ? '<div class="warn">Cơ hội đã chốt (khách chấp nhận báo giá) — chỉ xem.</div>' : ''}

        <section class="sec">
          <div class="sec-h"><h4>Khách hàng</h4><p>Chọn khách đã có trong danh mục, hoặc gõ tên khách mới nếu chưa có mã.</p></div>
          <div class="grid">
            <div class="f c3"><label for="chv1-f-khach">Khách trong danh mục</label><select id="chv1-f-khach" class="ctl" ${k}>${optKhach}</select></div>
            <div class="f c3"><label for="chv1-f-prospect">Tên khách tiềm năng</label><input id="chv1-f-prospect" class="ctl" value="${esc(x.prospect_name || '')}" placeholder="VD: Công ty May Hưng Thịnh" ${k}><span class="hint">Dùng khi khách chưa có mã</span></div>
            <div class="f c2"><label for="chv1-f-lh">Người liên hệ</label><input id="chv1-f-lh" class="ctl" value="${esc(x.contact_name || '')}" placeholder="Anh/chị…" ${k}></div>
            <div class="f c2"><label for="chv1-f-sdt">Điện thoại</label><input id="chv1-f-sdt" class="ctl" inputmode="tel" value="${esc(x.contact_phone || '')}" placeholder="09xx xxx xxx" ${k}></div>
            <div class="f c2"><label for="chv1-f-email">Email</label><input id="chv1-f-email" class="ctl" type="email" value="${esc(x.contact_email || '')}" placeholder="ten@congty.vn" ${k}></div>
          </div>
        </section>

        <section class="sec">
          <div class="sec-h"><h4>Nhu cầu vận chuyển</h4><p>Tuyến lấy từ Dữ liệu gốc và cần có để lập báo giá. Chưa có tuyến thì ghi tay điểm đi, điểm đến.</p></div>
          <div class="grid">
            <div class="f c3"><label for="chv1-f-tuyen">Tuyến</label><select id="chv1-f-tuyen" class="ctl" ${k}>${optTuyen}</select><span class="hint"><b>Cần để lập báo giá</b></span></div>
            <div class="f c3"><label for="chv1-f-hang">Loại hàng</label><input id="chv1-f-hang" class="ctl" value="${esc(x.cargo_type || '')}" placeholder="VD: Hàng tiêu dùng đóng pallet" ${k}></div>
            <div class="f c3"><label for="chv1-f-di">Điểm đi</label><input id="chv1-f-di" class="ctl" value="${esc(x.origin_text || '')}" placeholder="Kho / tỉnh thành" ${k}></div>
            <div class="f c3"><label for="chv1-f-den">Điểm đến</label><input id="chv1-f-den" class="ctl" value="${esc(x.destination_text || '')}" placeholder="Kho / tỉnh thành" ${k}></div>
            <div class="f c2"><label for="chv1-f-kg">Khối lượng mỗi chuyến</label><div class="unit"><input id="chv1-f-kg" class="ctl" type="number" min="0" value="${esc(x.est_weight_kg || '')}" placeholder="0" ${k}><span>kg</span></div></div>
            <div class="f c2"><label for="chv1-f-chuyen">Số chuyến mỗi tháng</label><div class="unit"><input id="chv1-f-chuyen" class="ctl" type="number" min="0" value="${esc(x.est_trips_per_month || '')}" placeholder="0" ${k}><span>chuyến</span></div></div>
            <div class="f c2"><label for="chv1-f-gia">Giá khách mong muốn</label><div class="unit"><input id="chv1-f-gia" class="ctl" type="number" min="0" value="${esc(x.expected_price || '')}" placeholder="0" ${k}><span>đ/chuyến</span></div><span class="hint">Nếu khách có nói</span></div>
          </div>
        </section>

        <section class="sec">
          <div class="sec-h"><h4>Theo dõi</h4><p>Ai đang theo cơ hội này và khi nào cần liên hệ lại.</p></div>
          <div class="grid">
            <div class="f c2"><label for="chv1-f-nguon">Nguồn</label><select id="chv1-f-nguon" class="ctl" ${k}>${Object.keys(NGUON).map(m => `<option value="${m}" ${(x.source || 'other') === m ? 'selected' : ''}>${esc(NGUON[m])}</option>`).join('')}</select></div>
            <div class="f c2"><label for="chv1-f-owner">Người theo</label><input id="chv1-f-owner" class="ctl" value="${esc(x.owner || '')}" ${k}></div>
            <div class="f c2"><label for="chv1-f-hen">Hẹn liên hệ lại</label><input id="chv1-f-hen" class="ctl" type="datetime-local" value="${henLocal}" ${k}></div>
            <div class="f c2"><label for="chv1-f-batdau">Dự kiến bắt đầu</label><input id="chv1-f-batdau" class="ctl" type="date" value="${esc(x.expected_start || '')}" ${k}></div>
            <div class="f c4"><label for="chv1-f-ghichu">Ghi chú</label><textarea id="chv1-f-ghichu" class="ctl" placeholder="Khách nói thêm gì, điều kiện đặc biệt, thời điểm gọi lại…" ${k}>${esc(x.notes || '')}</textarea></div>
          </div>
        </section>
      </div>
      <footer class="ft">
        <div class="l">
          ${id ? '' : '<span class="note">Có thể bổ sung tuyến và giá sau, khi lập báo giá.</span>'}
          ${id && !dong && x.stage !== 'lost' ? `<button type="button" class="btn ghost danger" id="chv1-dlg-mat">Đánh mất…</button>` : ''}
          ${id && ['new', 'contacted', 'negotiating'].includes(x.stage) ? `<button type="button" class="btn ghost" id="chv1-dlg-bg">Lập báo giá</button>` : ''}
          ${id && x.quotation_id ? `<button type="button" class="btn ghost" id="chv1-dlg-mo-bg">Mở ${esc(x.quotation_id)}</button>` : ''}
        </div>
        <div class="btns">
          <button type="button" class="btn ghost" id="chv1-dlg-huy">Đóng</button>
          ${dong ? '' : `<button type="button" class="btn primary" id="chv1-dlg-luu">${id ? 'Lưu' : 'Ghi nhận cơ hội'}</button>`}
        </div>
      </footer>`;
    const dong_ = () => { try { dlg.close(); } catch (e) { dlg.removeAttribute('open'); } };
    el('chv1-dlg-x').onclick = dong_; el('chv1-dlg-huy').onclick = dong_;
    if (el('chv1-dlg-luu')) el('chv1-dlg-luu').onclick = () => luu(dong_);
    if (el('chv1-dlg-mat')) el('chv1-dlg-mat').onclick = () => { dong_(); danhMat(id); };
    if (el('chv1-dlg-bg')) el('chv1-dlg-bg').onclick = () => { dong_(); lapBaoGia(id); };
    if (el('chv1-dlg-mo-bg')) el('chv1-dlg-mo-bg').onclick = () => { dong_(); moBaoGia(x.quotation_id); };
    if (typeof dlg.showModal === 'function') dlg.showModal(); else dlg.setAttribute('open', '');
  }

  function docForm() {
    const v = id => (el(id) ? el(id).value.trim() : '');
    const hen = v('chv1-f-hen');
    return {
      customer_id: v('chv1-f-khach') || null, prospect_name: v('chv1-f-prospect') || null,
      contact_name: v('chv1-f-lh') || null, contact_phone: v('chv1-f-sdt') || null, contact_email: v('chv1-f-email') || null,
      route_id: v('chv1-f-tuyen') || null, cargo_type: v('chv1-f-hang') || null,
      est_weight_kg: v('chv1-f-kg') || 0, est_trips_per_month: v('chv1-f-chuyen') || 0,
      expected_price: v('chv1-f-gia') || null,
      origin_text: v('chv1-f-di') || null, destination_text: v('chv1-f-den') || null,
      source: v('chv1-f-nguon') || 'other', owner: v('chv1-f-owner') || null,
      next_action_at: hen ? new Date(hen).toISOString() : null,
      expected_start: v('chv1-f-batdau') || null, notes: v('chv1-f-ghichu') || null,
    };
  }

  async function luu(dongHop) {
    const than = docForm();
    if (!than.customer_id && !than.prospect_name) { thongBao('Chọn khách trong danh mục hoặc ghi tên khách tiềm năng.', true); return; }
    try {
      let kq;
      if (S.dangSua) {
        const x = timCoHoi(S.dangSua) || {};
        kq = await api('/api/crm/opportunities/' + encodeURIComponent(S.dangSua), { method: 'PUT', body: JSON.stringify(Object.assign({ expected_version: x.version }, than)) });
      } else {
        kq = await api('/api/crm/opportunities', { method: 'POST', body: JSON.stringify(than) });
      }
      capNhat(kq); dongHop(); thongBao(S.dangSua ? 'Đã lưu cơ hội.' : 'Đã ghi nhận cơ hội ' + kq.id + '.');
    } catch (loi) { thongBao(loi.message, true); }
  }

  /* ------------------------------------------------------- khách hàng -- */
  function veBangKhach() {
    const b = el('chv1-bang-khach'); if (!b) return;
    const q = S.loc.q.toLowerCase();
    const ds = S.dsKhach.filter(k => !q || [k.id, k.name, k.contact_person].some(v => String(v || '').toLowerCase().includes(q)));
    if (S.che === 'khach') el('chv1-cnt').textContent = ds.length + ' khách hàng';
    b.innerHTML = `<thead><tr><th>Khách hàng</th><th class="r">Cơ hội mở</th><th class="r">Báo giá</th><th class="r">Lệnh giao hàng</th><th class="r">Doanh thu đã chốt</th><th>Hoạt động gần nhất</th></tr></thead>
      <tbody>${ds.length ? ds.map(k => `<tr data-id="${esc(k.id)}" class="${S.hoSo && S.hoSo.customer && S.hoSo.customer.id === k.id ? 'on' : ''}">
        <td><b>${esc(k.name)}</b><span class="sub">${esc(k.id)}${k.contact_person ? ' · ' + esc(k.contact_person) : ''}${k.phone ? ' · ' + esc(k.phone) : ''}</span></td>
        <td class="r">${k.open_opportunities || '—'}</td>
        <td class="r">${k.quotations_total || 0}<span class="sub">${k.quotations_accepted || 0} chấp nhận · ${k.quotations_sent || 0} chờ</span></td>
        <td class="r">${k.do_total || 0}<span class="sub">${k.do_delivered || 0} xong · ${k.do_active || 0} đang chạy</span></td>
        <td class="r">${esc(tien(k.accepted_revenue))}</td>
        <td>${esc(k.last_activity_at ? ngayGio(k.last_activity_at) : '—')}</td>
      </tr>`).join('') : '<tr><td colspan="6" style="text-align:center;color:#64748b;padding:22px">Chưa có khách hàng nào.</td></tr>'}</tbody>`;
    b.querySelectorAll('tr[data-id]').forEach(tr => tr.addEventListener('click', () => moHoSo(tr.dataset.id)));
  }

  async function moHoSo(id) {
    try {
      S.hoSo = await api('/api/crm/customers/' + encodeURIComponent(id) + '/profile');
      veBangKhach(); veHoSo();
    } catch (loi) { thongBao(loi.message, true); }
  }

  const TT_BG = { draft: 'Nháp', pending_approval: 'Chờ duyệt', approved: 'Đã duyệt', sent: 'Đã gửi', accepted: 'Đã chấp nhận', rejected: 'Từ chối', expired: 'Hết hạn', split: 'Đã tách DO' };
  const TT_DO = { pending: 'Chờ', in_transit: 'Đang chạy', arrived: 'Đã đến', delivered: 'Đã giao', cancelled: 'Đã huỷ' };

  function veHoSo() {
    const h = S.hoSo; const p = el('chv1-prof'); if (!h || !p) return;
    const c = h.customer, s = h.summary || {};
    p.innerHTML = `
      <div><h2>${esc(c.name)}</h2><div class="sub">${esc(c.id)}${c.contact_person ? ' · ' + esc(c.contact_person) : ''}${c.phone ? ' · ' + esc(c.phone) : ''}${c.address ? ' · ' + esc(c.address) : ''}</div></div>
      <div class="grid4">
        <div class="st"><span>Cơ hội mở</span><b>${s.open_opportunities || 0}</b></div>
        <div class="st"><span>Báo giá chấp nhận</span><b>${s.quotations_accepted || 0}<small style="font-weight:600;color:#64748b"> / ${s.quotations_total || 0}</small></b></div>
        <div class="st"><span>DO đã giao</span><b>${s.do_delivered || 0}<small style="font-weight:600;color:#64748b"> / ${s.do_total || 0}</small></b></div>
        <div class="st"><span>Doanh thu đã chốt</span><b style="font-size:14px">${esc(tien(s.accepted_revenue))}</b></div>
      </div>
      <div style="display:flex;gap:8px"><button type="button" class="btn sm pri" id="chv1-prof-them">+ Cơ hội cho khách này</button></div>
      <h4>Cơ hội</h4>
      <div>${(h.opportunities || []).length ? h.opportunities.slice(0, 8).map(o => `<div class="row"><span>${esc(o.id)} · ${esc(o.route_name || o.cargo_type || '')}</span><a data-co-hoi="${esc(o.id)}">${esc(TEN_GD[o.stage] || o.stage)}</a></div>`).join('') : '<div class="rong">Chưa có cơ hội.</div>'}</div>
      <h4>Báo giá</h4>
      <div>${(h.quotations || []).length ? h.quotations.slice(0, 8).map(q => `<div class="row"><span>${esc(q.quote_no || q.id)} · ${esc(tien(q.selling_price))}</span><a data-bg="${esc(q.id)}">${esc(TT_BG[q.canonical_status] || q.canonical_status)}</a></div>`).join('') : '<div class="rong">Chưa có báo giá.</div>'}</div>
      <h4>Lệnh giao hàng</h4>
      <div>${(h.delivery_orders || []).length ? h.delivery_orders.slice(0, 8).map(d => `<div class="row"><span>${esc(d.id)}${d.trips && d.trips.length ? ' · ' + esc(d.trips.map(t => t.id).join(', ')) : ''}</span><span>${esc(TT_DO[d.canonical_status] || d.canonical_status)}</span></div>`).join('') : '<div class="rong">Chưa có lệnh giao hàng.</div>'}</div>`;
    el('chv1-prof-them').onclick = () => { S.dangSua = null; moHopThoai(null); const sel = el('chv1-f-khach'); if (sel) sel.value = c.id; };
    p.querySelectorAll('a[data-bg]').forEach(a => a.addEventListener('click', () => moBaoGia(a.dataset.bg)));
    p.querySelectorAll('a[data-co-hoi]').forEach(a => a.addEventListener('click', () => { doiChe('board'); moHopThoai(a.dataset.coHoi); }));
  }

  /* --------------------------------------------------------------- cửa -- */
  window.CoHoiV1 = { nap, moHopThoai, moHoSo, doiChe, _trangThai: S };

  const chuyenManCu = window.switchView;
  if (typeof chuyenManCu === 'function') {
    window.switchView = function (man) {
      const ra = chuyenManCu.apply(this, arguments);
      if (man === 'co-hoi') nap();
      return ra;
    };
  }
  document.addEventListener('DOMContentLoaded', () => {
    const sec = el('view-co-hoi');
    if (el(GOC) && sec && sec.style.display !== 'none' && sec.classList.contains('active')) nap();
  });
})();

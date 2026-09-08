/* ============================================================================
   MÀN "SẮP LỊCH XE VÀ TÀI XẾ" — dựng theo bản mẫu
   `D:\Demo_Lao\nhap_UI__duan\shift-schedule-v5-staff-vehicle.html`.

   Bố cục và ngôn ngữ hình ảnh lấy nguyên từ bản mẫu. Cái khác là DỮ LIỆU: bản
   mẫu sinh 42 người và 14 xe bằng một bộ sinh số giả; ở đây mọi hàng, mọi ô và
   mọi con số đọc từ `GET /api/tms/scheduling/board`, và mọi nút ghi đều gọi
   backend thật.

   BA ĐƯỜNG GHI, và cả ba đi qua rào nghiệp vụ đã có:
     · lưu / sửa / xoá một ca      → /api/tms/scheduling/driver-shifts
     · sinh lịch theo mẫu xoay     → /api/tms/scheduling/generate-from-pattern
     · gán bãi, tổ và mẫu cho người → /api/tms/scheduling/drivers/{id}/assignment

   Đặt trong TỆP RIÊNG chứ không thêm vào `app.js`: màn cũ đã có gần một nghìn
   dòng lịch tài xế trong `app.js`, và tệp đó đang có người khác sửa cùng lúc.
   ========================================================================== */
(function () {
  'use strict';

  const KHUNG = 'ssv5-root';
  const LECH_PHUT = 7 * 60; // Việt Nam, không có giờ mùa hè

  const CA = [
    { ma: 'morning', ten: 'Sáng', ky: 'S', tu: 6, den: 14 },
    { ma: 'afternoon', ten: 'Chiều', ky: 'C', tu: 14, den: 22 },
    { ma: 'night', ten: 'Đêm', ky: 'Đ', tu: 22, den: 6 },
  ];
  const tenCa = ma => (CA.find(c => c.ma === ma) || {}).ten || ma;
  const kyCa = ma => (CA.find(c => c.ma === ma) || {}).ky || '?';
  const gioCa = ma => {
    const c = CA.find(x => x.ma === ma);
    return c ? `${String(c.tu).padStart(2, '0')}–${String(c.den).padStart(2, '0')}` : '';
  };

  const state = {
    tab: 'staff',        // staff | veh | depot
    mode: 'week',        // week | day | tl  (tl = dong thoi gian)
    ngayChon: null,      // ngay dang xem o che do Ngay va Dong thoi gian
    start: null,         // ISO ngày thứ Hai của kỳ đang xem
    soNgay: 7,
    depot: null,
    team: null,
    filter: 'all',
    vfilter: 'all',
    bang: null,
    dangNap: false,
    chon: null,          // ô nhân sự đang chọn
    chonXe: null,        // ô xe đang chọn
    khung: 'need',       // khối nào đang mở ở cột phải
    lanNap: 0,
  };

  const el = id => document.getElementById(id);
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g,
    c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const base = () => (typeof API_BASE !== 'undefined' ? API_BASE : '');

  /* ---------------------------------------------------------------- ngày ---- */
  function thuHai(d) {
    const x = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    x.setDate(x.getDate() - ((x.getDay() + 6) % 7));
    return x;
  }
  const isoNgay = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  const tuIso = s => { const [y, m, d] = String(s).split('-').map(Number); return new Date(y, m - 1, d); };
  const ddmm = s => { const d = tuIso(s); return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}`; };

  /**
   * Mốc ISO có múi giờ cho một ca của một ngày.
   *
   * Gửi kèm `+07:00` chứ không gửi mốc trần: máy chủ hiểu mốc trần là UTC, nên
   * một ca sáng 06:00 giờ Việt Nam sẽ được ghi thành 13:00 giờ Việt Nam.
   */
  function mocCa(ngayIso, maCa, cuoi) {
    const c = CA.find(x => x.ma === maCa);
    const d = tuIso(ngayIso);
    let gio = cuoi ? c.den : c.tu;
    if (cuoi && c.den <= c.tu) d.setDate(d.getDate() + 1);
    const p = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(gio)}:00:00+07:00`;
  }

  /* --------------------------------------------------------------- gọi API -- */
  async function api(duong, tuyChon) {
    const tra = await fetch(base() + duong, tuyChon);
    let goi = {};
    try { goi = await tra.json(); } catch (e) { goi = {}; }
    if (!tra.ok) {
      const loi = new Error((goi.error && goi.error.message) || goi.message
        || `Máy chủ trả về HTTP ${tra.status}.`);
      loi.ma = goi.error && goi.error.code;
      throw loi;
    }
    // Các điểm cuối xếp ca bọc dữ liệu trong `{message, data}`. Bỏ bước mở gói
    // này thì mọi thứ đọc được là `undefined` mà không có lỗi nào hiện ra.
    return goi && Object.prototype.hasOwnProperty.call(goi, 'data') ? goi.data : goi;
  }

  function thongBao(chu, loi) {
    let t = el('ssv5-toast');
    if (!t) {
      t = document.createElement('div');
      t.id = 'ssv5-toast';
      t.className = 'ssv5-toast';
      document.body.appendChild(t);
    }
    t.innerHTML = `<i>${loi ? '⚠' : '✓'}</i><span>${esc(chu)}</span>`;
    t.style.background = loi ? '#8a1c1c' : '#0f1c2e';
    t.hidden = false;
    clearTimeout(t._hen);
    t._hen = setTimeout(() => { t.hidden = true; }, 4600);
  }

  /* ------------------------------------------------------------------ khung -- */
  function dungKhung() {
    const goc = el(KHUNG);
    if (!goc || goc.dataset.dung === '1') return;
    goc.dataset.dung = '1';
    goc.innerHTML = `
      <div class="ssv5-host"><div class="ssv5-module">
        <div class="card hdr">
          <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap">
            <div>
              <h2>Sắp ca làm việc</h2>
              <div class="crumb" id="ssv5-crumb"></div>
            </div>
            <div class="seg" id="ssv5-tabs">
              <button type="button" class="on" data-tab="staff">Nhân sự <span class="n" id="ssv5-n-staff">0</span></button>
              <button type="button" data-tab="veh">Xe <span class="n" id="ssv5-n-veh">0</span></button>
            </div>
            <!-- Ba chế độ xem trả lời BA CÂU KHÁC NHAU, không thay nhau được:
                 Tuần = "tuần này ai trực ca nào", Ngày = "hôm nay đội hình thế
                 nào", Dòng thời gian = "lúc này ai đang trên đường". -->
            <div class="seg" id="ssv5-mode">
              <button type="button" class="on" data-m="week">Tuần</button>
              <button type="button" data-m="day">Ngày</button>
              <button type="button" data-m="tl">Dòng thời gian</button>
            </div>
          </div>
          <div class="searchwrap">
            <div class="search">
              <span class="q">⌕</span>
              <input id="ssv5-q" placeholder="Tìm tài xế, biển số, tổ hoặc bãi" autocomplete="off" aria-label="Tìm trong bảng sắp lịch">
              <kbd>/</kbd>
              <button type="button" class="go" id="ssv5-qbtn">Tìm</button>
            </div>
            <div class="dd" id="ssv5-dd" role="listbox"></div>
          </div>
          <div class="date">
            <button type="button" id="ssv5-prev" title="Kỳ trước">‹</button>
            <div class="d" id="ssv5-dlabel">—</div>
            <button type="button" id="ssv5-next" title="Kỳ sau">›</button>
            <button type="button" id="ssv5-today" title="Về tuần này">Tuần này</button>
          </div>
          <button type="button" class="ghost" id="ssv5-depot">▦ Toàn bãi</button>
          <!-- Hộp thoại hồ sơ tài xế của bản cũ GIỮ NGUYÊN và nối vào đây: nó
               là chỗ duy nhất thêm được người mới, mà một màn xếp ca không thêm
               được người thì không dùng được ở tuần đầu triển khai. -->
          <button type="button" class="ghost" id="ssv5-them-nguoi">+ Tài xế / phụ xe</button>
          <button type="button" class="ghost" id="ssv5-reload" title="Đọc lại từ máy chủ">↻</button>
          <button type="button" class="primary" id="ssv5-gen">⚙ Sinh lịch theo mẫu</button>
        </div>

        <div class="board">
          <section class="card" id="ssv5-v-staff">
            <div class="col-h">
              <h3 id="ssv5-staff-title">Nhân sự</h3>
              <div class="chips" id="ssv5-chips"></div>
            </div>
            <div class="gridwrap" id="ssv5-luoi">
              <div class="cover" id="ssv5-cover"></div>
              <div class="scroller" id="ssv5-rows"></div>
            </div>
            <div class="gridwrap hide" id="ssv5-tl">
              <div class="tl-head">
                <div id="ssv5-tl-day">—</div>
                <div class="hours" id="ssv5-hours"></div>
                <div></div>
              </div>
              <div class="scroller" id="ssv5-tl-rows"></div>
            </div>
            <div class="legend">
              <span><i style="background:#f59e0b"></i>Sáng 06–14</span>
              <span><i style="background:#1a73e8"></i>Chiều 14–22</span>
              <span><i style="background:#7c3aed"></i>Đêm 22–06</span>
              <span><i style="background:#0f1c2e"></i>Khoá (có Trip từ Điều phối)</span>
              <span><i style="background:#fff8e1;border:1.5px solid #f5d98a"></i>Nghỉ theo mẫu</span>
              <span><i style="background:#f1f5f9;border:1.5px solid #cbd5e1"></i>Nghỉ phép</span>
              <span><i style="background:#fdecec;border:1.5px dashed #d32f2f"></i>Cần người</span>
              <span><i style="background:#fff;box-shadow:0 0 0 2px #b45309"></i>Khác mẫu xoay</span>
            </div>
            <div class="tfoot">
              <span id="ssv5-foot">—</span>
              <span>Bấm một ô để xếp hoặc sửa ca · bấm mã mẫu ở cột trái để đổi tổ và mẫu xoay</span>
            </div>
          </section>

          <section class="card hide" id="ssv5-v-veh">
            <div class="col-h">
              <h3 id="ssv5-veh-title">Xe</h3>
              <div class="chips" id="ssv5-vchips"></div>
            </div>
            <div class="gridwrap">
              <div class="cover" id="ssv5-vcover"></div>
              <div class="scroller" id="ssv5-vrows"></div>
            </div>
            <div class="legend">
              <span><i style="background:#1a73e8"></i>Trip đã điều phối</span>
              <span><i style="background:#7c3aed"></i>Đang chạy</span>
              <span><i style="background:#15803d"></i>Hoàn thành</span>
              <span><i style="background:#f6fcf8;border:1.5px dashed #bfe3cf"></i>Sẵn sàng (có tổ lái trong ca)</span>
              <span><i style="background:#fff;border:1.5px dashed #cbd5e1"></i>Rảnh, chưa có tổ lái</span>
              <span><i style="background:repeating-linear-gradient(135deg,#f1f5f9 0 4px,#e2e8f0 4px 8px)"></i>Bảo dưỡng</span>
              <span><i style="background:#fdecec;border:1.5px solid #d32f2f"></i>Có Trip mà không có tổ lái</span>
              <span style="margin-left:auto;color:#7b8796">Vòng tròn = tổ lái theo ca · ô chia 3 cột = Sáng · Chiều · Đêm</span>
            </div>
            <div class="tfoot">
              <span id="ssv5-vfoot">—</span>
              <span>Bấm ô Trip để mở Điều phối · bấm ô rảnh để xem cách xử lý</span>
            </div>
          </section>

          <section class="card hide" id="ssv5-v-depot">
            <div class="col-h"><h3 id="ssv5-depot-title">Toàn bộ bãi</h3></div>
            <div class="teams" id="ssv5-teams"></div>
            <div class="gridwrap">
              <div class="cover" id="ssv5-dcover"></div>
              <div id="ssv5-drows"></div>
            </div>
            <div class="legend">
              <span><i style="background:#1a73e8"></i>Đủ người</span>
              <span><i style="background:#eef2f7;border:1px solid #cbd5e1"></i>Không có xe nào phải chạy</span>
              <span><i style="background:#c7ddf8"></i>Thiếu ≤ 20%</span>
              <span><i style="background:#fbd0d0"></i>Thiếu 20–50%</span>
              <span><i style="background:#d32f2f"></i>Thiếu &gt; 50%</span>
              <span style="margin-left:auto;color:#7b8796">Bấm một bãi để xuống lưới của bãi đó</span>
            </div>
          </section>

          <aside class="card panel">
            <div class="col-h"><h3 id="ssv5-ptitle">Việc cần làm</h3><small id="ssv5-pstep"></small></div>
            <div class="pb" id="ssv5-pbody"></div>
          </aside>
        </div>
      </div></div>`;
    ganSuKien();
  }

  /* --------------------------------------------------------------- sự kiện -- */
  function ganSuKien() {
    el('ssv5-tabs').addEventListener('click', e => {
      const b = e.target.closest('button[data-tab]');
      if (!b) return;
      state.tab = b.dataset.tab;
      state.khung = state.tab === 'veh' ? 'vneed' : 'need';
      ve();
    });
    el('ssv5-mode').addEventListener('click', e => {
      const b = e.target.closest('button[data-m]');
      if (!b) return;
      state.mode = b.dataset.m;
      // Chế độ Ngày và Dòng thời gian cần MỘT ngày. Chưa chọn thì lấy hôm nay
      // nếu hôm nay nằm trong kỳ, không thì lấy ngày đầu kỳ — nhảy sang một
      // ngày ngoài kỳ đang xem thì người dùng mất phương hướng.
      if (state.mode !== 'week' && !ngayTrongKy(state.ngayChon)) {
        const homNay = (state.bang.pham_vi.cac_ngay.find(n => n.hom_nay) || {}).ngay;
        state.ngayChon = homNay || state.bang.pham_vi.cac_ngay[0].ngay;
      }
      ve();
    });
    el('ssv5-prev').addEventListener('click', () => doiKy(-state.soNgay));
    el('ssv5-next').addEventListener('click', () => doiKy(state.soNgay));
    el('ssv5-today').addEventListener('click', () => { state.start = isoNgay(thuHai(new Date())); nap(); });
    el('ssv5-reload').addEventListener('click', () => nap());
    el('ssv5-them-nguoi').addEventListener('click', () => {
      if (typeof window.openAddDriverModal === 'function') window.openAddDriverModal();
      else thongBao('Chưa nạp được form hồ sơ tài xế. Tải lại trang rồi thử lại.', true);
    });
    el('ssv5-depot').addEventListener('click', () => { state.tab = 'depot'; ve(); });
    el('ssv5-gen').addEventListener('click', () => { state.khung = 'gen'; veCotPhai(); });

    el('ssv5-rows').addEventListener('click', async e => {
      const mau = e.target.closest('[data-mau]');
      if (mau) { moDoiTo(mau.dataset.mau); return; }
      const o = e.target.closest('.sh');
      if (!o) return;
      // Ô đỏ "cần người" là một CON SỐ CÒN THIẾU của cả ca, không phải một ô
      // của riêng người ở hàng đó. Bấm vào nên mở danh sách ai có thể nhận, chứ
      // không phải mở form xếp cho đúng người đang ở hàng đó — người đó có thể
      // là người tệ nhất để xếp.
      if (o.dataset.tt === 'need') { moLapCa(o.dataset.ngay, o.dataset.ca); return; }
      chonO(o);
    });
    el('ssv5-vrows').addEventListener('click', e => {
      const o = e.target.closest('.vs');
      if (o) chonOXe(o);
    });
    el('ssv5-chips').addEventListener('click', e => {
      const c = e.target.closest('.chip');
      if (c) { state.filter = c.dataset.f; ve(); }
    });
    el('ssv5-vchips').addEventListener('click', e => {
      const c = e.target.closest('.chip');
      if (c) { state.vfilter = c.dataset.f; ve(); }
    });
    el('ssv5-teams').addEventListener('click', e => {
      const b = e.target.closest('[data-team]');
      if (!b) return;
      state.team = b.dataset.team || null;
      state.depot = b.dataset.depot || null;
      state.tab = 'staff';
      nap();
    });
    el('ssv5-drows').addEventListener('click', e => {
      const b = e.target.closest('[data-depot]');
      if (!b) return;
      state.depot = b.dataset.depot || null;
      state.team = null;
      state.tab = 'staff';
      nap();
    });
    el('ssv5-crumb').addEventListener('click', e => {
      const b = e.target.closest('button[data-cap]');
      if (!b) return;
      if (b.dataset.cap === 'all') { state.depot = null; state.team = null; state.tab = 'depot'; nap(); }
      if (b.dataset.cap === 'depot') { state.team = null; nap(); }
    });
    el('ssv5-pbody').addEventListener('click', xuLyCotPhai);

    const q = el('ssv5-q');
    q.addEventListener('input', goiY);
    q.addEventListener('focus', goiY);
    q.addEventListener('keydown', e => {
      if (e.key === 'Escape') { el('ssv5-dd').classList.remove('show'); q.blur(); }
      if (e.key === 'Enter') { const f = el('ssv5-dd').querySelector('.it'); if (f) chonGoiY(f); }
    });
    el('ssv5-qbtn').addEventListener('click', () => {
      goiY();
      const f = el('ssv5-dd').querySelector('.it');
      if (f) chonGoiY(f);
    });
    el('ssv5-dd').addEventListener('click', e => {
      const it = e.target.closest('.it');
      if (it) chonGoiY(it);
    });
    document.addEventListener('click', e => {
      if (!e.target.closest('#' + KHUNG + ' .searchwrap')) {
        const dd = el('ssv5-dd');
        if (dd) dd.classList.remove('show');
      }
    });
  }

  const ngayTrongKy = iso => !!iso && !!state.bang
    && state.bang.pham_vi.cac_ngay.some(n => n.ngay === iso);

  function doiKy(so) {
    // Ở chế độ Ngày và Dòng thời gian thì mũi ‹ › đi TỪNG NGÀY, không nhảy cả
    // tuần: người dùng đang xem một ngày, và nhảy bảy ngày một nhịp thì họ mất
    // luôn cái ngày đang xem.
    if (state.mode !== 'week' && ngayTrongKy(state.ngayChon)) {
      const ds = state.bang.pham_vi.cac_ngay.map(n => n.ngay);
      const i = ds.indexOf(state.ngayChon) + (so > 0 ? 1 : -1);
      if (i >= 0 && i < ds.length) { state.ngayChon = ds[i]; ve(); return; }
      // Ra khỏi kỳ thì kéo cả kỳ theo, rồi neo vào đầu hoặc cuối kỳ mới.
      const d0 = tuIso(state.start);
      d0.setDate(d0.getDate() + (so > 0 ? state.soNgay : -state.soNgay));
      state.start = isoNgay(d0);
      state.ngayChon = null;
      state.neoCuoiKy = so < 0;
      nap();
      return;
    }
    const d = tuIso(state.start);
    d.setDate(d.getDate() + so);
    state.start = isoNgay(d);
    nap();
  }

  /* ------------------------------------------------------------------- nạp -- */
  async function nap() {
    if (!el(KHUNG)) return;
    if (!state.start) state.start = isoNgay(thuHai(new Date()));
    const lan = ++state.lanNap;
    state.dangNap = true;
    const chan = el('ssv5-foot');
    if (chan) chan.textContent = 'Đang đọc từ máy chủ…';
    try {
      const ds = new URLSearchParams({ start: state.start, days: String(state.soNgay) });
      if (state.depot) ds.set('depot', state.depot);
      if (state.team) ds.set('team', state.team);
      const bang = await api(`/api/tms/scheduling/board?${ds}`);
      // Bỏ kết quả CŨ về muộn. Bấm nhanh hai lần "kỳ sau" thì hai lần đọc chạy
      // song song, và lần về sau cùng chưa chắc là lần mới nhất.
      if (lan !== state.lanNap) return;
      state.bang = bang;
      if (state.mode !== 'week' && !ngayTrongKy(state.ngayChon)) {
        const ds = bang.pham_vi.cac_ngay;
        state.ngayChon = state.neoCuoiKy ? ds[ds.length - 1].ngay
          : ((ds.find(n => n.hom_nay) || ds[0]).ngay);
      }
      state.neoCuoiKy = false;
      ve();
    } catch (loi) {
      if (lan !== state.lanNap) return;
      state.bang = null;
      const r = el('ssv5-rows');
      if (r) r.innerHTML = `<div class="empty" style="margin:14px">Không đọc được bảng sắp lịch.<br>${esc(loi.message)}</div>`;
      if (chan) chan.textContent = 'Lỗi đọc dữ liệu';
      thongBao(loi.message, true);
    } finally {
      state.dangNap = false;
    }
  }

  /* -------------------------------------------------------------------- vẽ -- */
  function ve() {
    if (!state.bang) return;
    const b = state.bang;
    const cols = `260px repeat(${b.pham_vi.cac_ngay.length},minmax(96px,1fr)) 64px`;
    el(KHUNG).querySelector('.ssv5-module').style.setProperty('--ss-cols', cols);

    const ngayDangXem = state.mode === 'week' ? null : state.ngayChon;
    el('ssv5-dlabel').textContent = ngayDangXem
      ? `${(b.pham_vi.cac_ngay.find(n => n.ngay === ngayDangXem) || {}).thu || ''} ${ddmm(ngayDangXem)}`
      : `${ddmm(b.pham_vi.tu)} – ${ddmm(b.pham_vi.den)}`;
    [...el('ssv5-mode').querySelectorAll('button')].forEach(x =>
      x.classList.toggle('on', x.dataset.m === state.mode));
    // Dải chế độ xem chỉ có nghĩa với lưới nhân sự. Lưới xe và màn Toàn bãi
    // luôn là cả kỳ, nên để dải đó bấm được ở đó là hứa một thứ không xảy ra.
    el('ssv5-mode').classList.toggle('hide', state.tab !== 'staff');
    el('ssv5-n-staff').textContent = b.nhan_su.length;
    el('ssv5-n-veh').textContent = b.xe.length;
    [...el('ssv5-tabs').querySelectorAll('button')].forEach(x =>
      x.classList.toggle('on', x.dataset.tab === state.tab));
    veCrumb();

    el('ssv5-v-staff').classList.toggle('hide', state.tab !== 'staff');
    el('ssv5-v-veh').classList.toggle('hide', state.tab !== 'veh');
    el('ssv5-v-depot').classList.toggle('hide', state.tab !== 'depot');

    if (state.tab === 'staff') { if (state.mode === 'tl') veDongThoiGian(); else veNhanSu(); }
    else if (state.tab === 'veh') veXe();
    else veToanBai();
    veCotPhai();
  }

  function veCrumb() {
    const b = state.bang;
    // So sánh phải có `state.depot` thật. Để trống bộ lọc thì `state.depot` là
    // `null`, mà bảng có một mục giả `depot_code: null` cho nhóm "Chưa phân
    // bãi" — nên `find` khớp đúng mục đó và đường dẫn nói sai rằng đang xem
    // nhóm chưa phân bãi trong khi thực tế đang xem tất cả.
    const bai = state.depot ? (b.cac_bai || []).find(x => x.depot_code === state.depot) : null;
    const phan = ['<button type="button" data-cap="all">Toàn bộ bãi</button>'];
    if (state.depot) {
      phan.push('›');
      const ten = bai ? bai.ten : state.depot;
      phan.push(state.team
        ? `<button type="button" data-cap="depot">${esc(ten)}</button>`
        : `<b>${esc(ten)}</b>`);
    }
    if (state.team) phan.push('›', `<b>Tổ ${esc(state.team)}</b>`);
    if (!state.depot && !state.team) phan.push('›', '<b>Tất cả tài xế và xe</b>');
    el('ssv5-crumb').innerHTML = phan.join(' ');
  }

  /* ----- lưới nhân sự ----- */
  const coTrangThai = (p, tt) => p.cac_ngay.some(d => d.cac_o.some(o => o.trang_thai === tt));

  function locNhanSu() {
    const ds = state.bang.nhan_su;
    if (state.filter === 'need') return ds.filter(p => coTrangThai(p, 'need'));
    if (state.filter === 'warn') return ds.filter(p => p.vuot_gio);
    if (state.filter === 'leave') return ds.filter(p => coTrangThai(p, 'leave'));
    if (state.filter === 'noteam') return ds.filter(p => !p.team_code);
    return ds;
  }

  function veChips() {
    const ds = state.bang.nhan_su;
    const dem = {
      all: ds.length,
      need: ds.filter(p => coTrangThai(p, 'need')).length,
      warn: ds.filter(p => p.vuot_gio).length,
      leave: ds.filter(p => coTrangThai(p, 'leave')).length,
      noteam: ds.filter(p => !p.team_code).length,
    };
    const khai = [
      ['all', 'Tất cả', ''], ['need', 'Cần xếp', 'r'], ['warn', 'Vượt giờ', ''],
      ['leave', 'Nghỉ phép', ''], ['noteam', 'Chưa phân tổ', ''],
    ];
    el('ssv5-chips').innerHTML = khai.map(([f, ten, kieu]) =>
      `<button type="button" class="chip ${kieu} ${state.filter === f ? 'on' : ''}" data-f="${f}">${ten} <b>${dem[f]}</b></button>`).join('');
  }

  function oNhanSu(p, ngayIso, o) {
    const lop = ['sh'];
    let chu = kyCa(o.ca), phu = '';
    if (o.trang_thai === 'on' || o.trang_thai === 'lock') {
      lop.push(o.trang_thai === 'lock' ? 'lock' : 'on', o.ca);
      phu = gioCa(o.ca);
      if (o.khac_mau) lop.push('ex');
    } else if (o.trang_thai === 'leave') { lop.push('leave'); chu = 'Phép'; }
    else if (o.trang_thai === 'off') { lop.push('off'); chu = kyCa(o.ca); phu = 'nghỉ'; }
    else if (o.trang_thai === 'need') { lop.push('need'); phu = 'thiếu'; }
    const nhan = o.trang_thai === 'lock' ? '🔒 ' : '';
    const bien = o.vehicle_id ? `<span class="veh">${esc(String(o.vehicle_id).slice(-6))}</span>` : '';
    const goi = o.trang_thai === 'lock'
      ? `Ca ${tenCa(o.ca).toLowerCase()} · khoá vì có Trip ${o.trip_id || ''}`
      : `Ca ${tenCa(o.ca).toLowerCase()} ${gioCa(o.ca)}`;
    return `<div class="${lop.join(' ')}" role="button" tabindex="0" title="${esc(goi)}"
      data-drv="${esc(p.driver_id)}" data-ngay="${ngayIso}" data-ca="${o.ca}"
      data-tt="${o.trang_thai}" data-shift="${esc(o.shift_id || '')}"
      data-ver="${o.version == null ? '' : o.version}" data-trip="${esc(o.trip_id || '')}"
      >${nhan}${esc(chu)}${phu ? `<small>${esc(phu)}</small>` : ''}${bien}</div>`;
  }

  function veNhanSu() {
    const b = state.bang;
    veChips();
    const ds = locNhanSu();
    el('ssv5-staff-title').innerHTML = `${state.team ? 'Tổ ' + esc(state.team) : 'Nhân sự'}
      <small>${ds.length} người${state.depot ? ' · ' + esc(tenBai(state.depot)) : ''}</small>`;

    el('ssv5-luoi').classList.remove('hide');
    el('ssv5-tl').classList.add('hide');
    // Ở chế độ Ngày thì lưới còn MỘT cột ngày. Lưới bảy ngày trả lời "tuần này
    // ai trực ca nào"; một ngày trả lời "hôm nay đội hình thế nào", và để cả
    // bảy cột thì cột hôm nay lẫn trong sáu cột không liên quan.
    const cacNgay = state.mode === 'day' && ngayTrongKy(state.ngayChon)
      ? b.pham_vi.cac_ngay.filter(n => n.ngay === state.ngayChon)
      : b.pham_vi.cac_ngay;
    el(KHUNG).querySelector('.ssv5-module').style.setProperty('--ss-cols',
      `260px repeat(${cacNgay.length},minmax(96px,1fr)) 64px`);
    const trongTam = new Set(cacNgay.map(n => n.ngay));
    el('ssv5-cover').innerHTML = veDoPhu(b, 'nhan_su', trongTam);
    el('ssv5-rows').innerHTML = ds.length ? ds.map(p => {
      const mau = p.mau_xoay
        ? `<span class="pat" data-mau="${esc(p.driver_id)}" role="button" tabindex="0" title="Đổi tổ và mẫu xoay">${esc(p.mau_xoay)}</span>`
        : `<span class="pat none" data-mau="${esc(p.driver_id)}" role="button" tabindex="0" title="Chưa có mẫu xoay — bấm để gán">chưa có mẫu</span>`;
      const to = p.team_code ? `Tổ ${esc(p.team_code)}` : 'chưa phân tổ';
      return `<div class="grid" data-drv="${esc(p.driver_id)}">
        <div><div class="who"><span class="av">${esc(p.chu_cai)}</span>
          <div class="g"><b>${esc(p.ten)}</b>
            <span>${esc(p.driver_id)} · ${esc(p.vai_tro || '')} · ${to} · ${mau}</span></div></div></div>
        ${p.cac_ngay.filter(d => trongTam.has(d.ngay)).map(d => `<div><div class="cell">${d.cac_o.map(o => oNhanSu(p, d.ngay, o)).join('')}</div></div>`).join('')}
        <div class="tot ${p.vuot_gio ? 'warn' : ''}">${p.gio_tuan}<small>${p.vuot_gio ? 'h ⚠' : 'h'}</small></div>
      </div>`;
    }).join('') : `<div class="empty" style="margin:14px">Không có tài xế nào khớp bộ lọc đang chọn.</div>`;

    const thieu = b.do_phu.reduce((t, m) => t + m.cac_ca.reduce((s, c) => s + c.thieu, 0), 0);
    el('ssv5-foot').textContent = `${ds.length}/${b.nhan_su.length} người · ${thieu ? 'còn thiếu ' + thieu + ' suất trực' : 'đủ người cho số xe phải chạy'}`;
  }

  /**
   * CHE DO DONG THOI GIAN — 24 gio cua MOT ngay, mot lan moi nguoi.
   *
   * Luoi tuan tra loi "tuan nay ai truc ca nao". Cai nay tra loi mot cau KHAC
   * va khong the suy ra tu luoi tuan: "luc nay ai dang tren duong". Vach do
   * gio hien tai la thu lam che do nay co ich — bo no thi day chi la mot cach
   * ve lai cung mot bang.
   */
  function veDongThoiGian() {
    const b = state.bang;
    veChips();
    el('ssv5-luoi').classList.add('hide');
    el('ssv5-tl').classList.remove('hide');
    const iso = ngayTrongKy(state.ngayChon) ? state.ngayChon : b.pham_vi.cac_ngay[0].ngay;
    const muc = b.pham_vi.cac_ngay.find(n => n.ngay === iso) || {};
    el('ssv5-tl-day').textContent = `${muc.thu || ''} ${ddmm(iso)} · 24 giờ`;

    // Vach gio hien tai chi ve khi dang xem DUNG ngay hom nay. Ve no o mot ngay
    // khac la noi doi: "bay gio" khong nam trong ngay do.
    const gioBayGio = gioDiaPhuong();
    const laHomNay = !!muc.hom_nay;
    el('ssv5-hours').innerHTML =
      Array.from({ length: 24 }, (_, h) => `<span>${String(h).padStart(2, '0')}</span>`).join('')
      + (laHomNay ? `<span class="nowlbl" style="left:${(gioBayGio / 24) * 100}%">${nhanGio(gioBayGio)}</span>` : '');

    const ds = locNhanSu();
    el('ssv5-staff-title').innerHTML = `${state.team ? 'Tổ ' + esc(state.team) : 'Nhân sự'}
      <small>${ds.length} người · dòng thời gian ${ddmm(iso)}</small>`;
    el('ssv5-tl-rows').innerHTML = ds.length ? ds.map(p => {
      const ngay = p.cac_ngay.find(d => d.ngay === iso) || { cac_o: [] };
      // NGÀY NGHỈ vẽ MỘT thanh suốt ngày, không phải ba thanh "Nghỉ theo mẫu"
      // ở ba khung ca. Một người nghỉ thì họ nghỉ cả ngày; vẽ ba thanh nghỉ
      // cạnh nhau thì trục đọc ra như họ có ba việc, và ba thanh đó chiếm chỗ
      // của thứ duy nhất trục này cần cho thấy — ai đang trên đường.
      const nghi = ngay.cac_o.length
        && ngay.cac_o.every(o => o.trang_thai === 'off' || o.trang_thai === 'leave' || o.trang_thai === 'free');
      let thanh;
      if (nghi) {
        const phep = ngay.cac_o.some(o => o.trang_thai === 'leave');
        const theoMau = ngay.cac_o.some(o => o.trang_thai === 'off');
        thanh = `<div class="bar ${phep ? 'leave' : 'off'}" style="left:0;width:100%">${
          phep ? 'Nghỉ phép' : theoMau ? 'Nghỉ theo mẫu' : 'Không có ca nào'}</div>`;
      } else {
        // Ngày CÓ ca thì bỏ hẳn các ô nghỉ: "nghỉ ca chiều" của một người trực
        // ca sáng không phải là thông tin.
        thanh = ngay.cac_o
          .filter(o => o.trang_thai !== 'off' && o.trang_thai !== 'leave')
          .map(o => thanhCa(o, p)).filter(Boolean).join('');
      }
      return `<div class="tl">
        <div><div class="who"><span class="av">${esc(p.chu_cai)}</span>
          <div class="g"><b>${esc(p.ten)}</b><span>${esc(p.driver_id)} · ${esc(p.vai_tro || '')}</span></div></div></div>
        <div class="lane">${laHomNay ? `<div class="now" style="left:${(gioBayGio / 24) * 100}%"></div>` : ''}${thanh}</div>
        <div class="tot ${p.vuot_gio ? 'warn' : ''}">${p.gio_tuan}<small>h</small></div>
      </div>`;
    }).join('') : `<div class="empty" style="margin:14px">Không có tài xế nào khớp bộ lọc đang chọn.</div>`;

    const thieu = b.do_phu.filter(m => m.ngay === iso)
      .reduce((t, m) => t + m.cac_ca.reduce((x, c) => x + c.thieu, 0), 0);
    el('ssv5-foot').textContent = `${ds.length} người · ngày ${ddmm(iso)}`
      + (thieu ? ` · còn thiếu ${thieu} suất trực` : ' · đủ người cho số xe phải chạy');
  }

  /** Gio dia phuong hien tai duoi dang so thap phan, ví du 8.4 = 08:24. */
  function gioDiaPhuong() {
    const t = new Date();
    // Doi ve gio Viet Nam bat ke may nguoi dung dat mui gio nao: ca truc la gio
    // dia phuong cua bai, khong phai gio cua may xem.
    const utc = t.getTime() + t.getTimezoneOffset() * 60000;
    const vn = new Date(utc + LECH_PHUT * 60000);
    return vn.getHours() + vn.getMinutes() / 60;
  }
  const nhanGio = g => `${String(Math.floor(g)).padStart(2, '0')}:${String(Math.round((g % 1) * 60)).padStart(2, '0')}`;

  /** Mot thanh ca tren truc 24 gio, hoac chuoi rong khi o do khong co gi. */
  function thanhCa(o, p) {
    if (o.trang_thai === 'free') return '';
    const c = CA.find(x => x.ma === o.ca);
    // Ca dem vat qua nua dem. Cat o 24:00 va KHONG ve phan sang hom sau: phan
    // do thuoc ngay khac, ve no o day thi mot ca 8 tieng nhin nhu 2 tieng.
    const tu = c.tu;
    const den = c.den <= c.tu ? 24 : c.den;
    const rong = ((den - tu) / 24) * 100;
    const trai = (tu / 24) * 100;
    if (o.trang_thai === 'off' || o.trang_thai === 'leave') {
      return `<div class="bar ${o.trang_thai}" style="left:${trai}%;width:${rong}%">${o.trang_thai === 'leave' ? 'Nghỉ phép' : 'Nghỉ theo mẫu'}</div>`;
    }
    if (o.trang_thai === 'need') {
      return `<div class="bar need" style="left:${trai}%;width:${rong}%">${kyCa(o.ca)} thiếu người</div>`;
    }
    const khoa = o.trang_thai === 'lock';
    const lop = khoa ? 'lock' : o.ca;
    const phu = khoa && o.trip_id ? ` · ${esc(o.trip_id)}` : (o.vehicle_id ? ` · ${esc(o.vehicle_id)}` : '');
    return `<div class="bar ${lop}" style="left:${trai}%;width:${rong}%" title="${esc(tenCa(o.ca))} ${gioCa(o.ca)}${phu}"
      >${khoa ? '🔒 ' : ''}Ca ${esc(tenCa(o.ca).toLowerCase())} <small>${gioCa(o.ca)}${phu}</small></div>`;
  }

  const tenBai = ma => {
    const b = (state.bang.cac_bai || []).find(x => x.depot_code === ma);
    return b ? b.ten : (ma || 'Chưa phân bãi');
  };

  function veDoPhu(b, loai, trongTam) {
    const dau = loai === 'nhan_su'
      ? 'Độ phủ · người trực / số xe phải chạy'
      : 'Xe sẵn sàng / số xe phải chạy';
    let h = `<div>${dau}</div>`;
    b.do_phu.filter(m => !trongTam || trongTam.has(m.ngay)).forEach(m => {
      const thanh = c => {
        const co = loai === 'nhan_su' ? c.truc : c.xe_san_sang;
        // Không có xe nào phải chạy thì độ phủ ĐỦ, không phải 0%. Vẽ 0% ở đây
        // là báo động một ca mà chẳng ai cần trực.
        const ti = c.can === 0 ? 1 : Math.min(1, co / c.can);
        const lop = ti >= 1 ? '' : ti >= 0.7 ? 'a' : 'r';
        return `<i class="${lop}" style="--p:${Math.round(ti * 100)}%" title="${kyCa(c.ca)}: ${co}/${c.can}"></i>`;
      };
      const thieu = m.cac_ca.reduce((s, c) => s + c.thieu, 0);
      const co = m.cac_ca.map(c => loai === 'nhan_su' ? c.truc : c.xe_san_sang).join('/');
      const can = m.cac_ca.map(c => c.can).join('/');
      h += `<div><div class="dn ${m.hom_nay ? 'today' : ''}">${esc(m.thu)} <span>${ddmm(m.ngay)}</span></div>
        <div class="cov">${m.cac_ca.map(thanh).join('')}</div>
        <small>${co} · cần ${can}${thieu ? ` · <b>thiếu ${thieu}</b>` : ''}</small></div>`;
    });
    h += `<div style="display:flex;align-items:center;justify-content:center;font-size:11px;color:#7b8796;font-weight:700">Kỳ</div>`;
    return h;
  }

  /* ----- lưới xe ----- */
  const coTrangThaiXe = (v, ds) => v.cac_ngay.some(d => d.cac_o.some(o => ds.includes(o.trang_thai)));

  function locXe() {
    const ds = state.bang.xe;
    if (state.vfilter === 'conf') return ds.filter(v => coTrangThaiXe(v, ['conf']));
    if (state.vfilter === 'mt') return ds.filter(v => coTrangThaiXe(v, ['mt', 'lock']));
    if (state.vfilter === 'idle') return ds.filter(v => v.ngay_ranh === v.cac_ngay.length);
    return ds;
  }

  function veXe() {
    const b = state.bang;
    const dem = {
      all: b.xe.length,
      conf: b.xe.filter(v => coTrangThaiXe(v, ['conf'])).length,
      mt: b.xe.filter(v => coTrangThaiXe(v, ['mt', 'lock'])).length,
      idle: b.xe.filter(v => v.ngay_ranh === v.cac_ngay.length).length,
    };
    el('ssv5-vchips').innerHTML = [
      ['all', 'Tất cả', ''], ['conf', 'Trip thiếu tổ lái', 'r'],
      ['mt', 'Bảo dưỡng / khoá', ''], ['idle', 'Rảnh cả kỳ', ''],
    ].map(([f, ten, kieu]) =>
      `<button type="button" class="chip ${kieu} ${state.vfilter === f ? 'on' : ''}" data-f="${f}">${ten} <b>${dem[f]}</b></button>`).join('');

    const ds = locXe();
    el('ssv5-veh-title').innerHTML = `Xe <small>${ds.length} xe${state.depot ? ' · ' + esc(tenBai(state.depot)) : ''}</small>`;
    el('ssv5-vcover').innerHTML = veDoPhu(b, 'xe');
    el('ssv5-vrows').innerHTML = ds.length ? ds.map(v => `
      <div class="vrow" data-veh="${esc(v.vehicle_id)}">
        <div><div class="who"><span class="av v">${esc(String(v.vehicle_id).slice(-6))}</span>
          <div class="g"><b>${esc(v.vehicle_id)}</b>
            <span>${esc(v.loai || 'chưa khai loại xe')} · đăng kiểm ${esc(v.han_dang_kiem || 'chưa khai')}</span>
            ${thanhKm(v)}</div></div></div>
        ${v.cac_ngay.map(d => `<div><div class="vc">${d.cac_o.map(o => oXe(v, d.ngay, o)).join('')}</div></div>`).join('')}
        <div class="tot ${v.ngay_ranh >= 3 ? 'warn' : ''}">${v.ngay_ranh}<small>ngày rảnh</small></div>
      </div>`).join('') : `<div class="empty" style="margin:14px">Không có xe nào khớp bộ lọc đang chọn.</div>`;

    el('ssv5-vfoot').textContent = `${ds.length}/${b.xe.length} xe · ${dem.conf ? dem.conf + ' xe có Trip mà chưa có tổ lái' : 'mọi Trip đều đã có tổ lái'}`;
  }

  /**
   * Thanh KM DEN KY BAO DUONG duoi bien so.
   *
   * Doi xe that lap lich bao duong theo km chay, khong theo ngay lich: mot chiec
   * chay 400 km mot ngay thi mot ngay lich khong noi duoc gi.
   *
   * CHUA KHAI SO KM thi KHONG ve thanh — noi ra bang chu. Mot thanh 0% doc ra
   * nhu "xe den han bao duong gap", va nguoi dieu do se goi xe ve garage trong
   * khi khong ai biet no da chay bao nhieu.
   */
  function thanhKm(v) {
    if (v.con_km_bao_duong == null) {
      return `<span class="kmnone" title="Khai số km đồng hồ và mốc bảo dưỡng kế tiếp ở hồ sơ xe">chưa khai số km</span>`;
    }
    const con = Number(v.con_km_bao_duong);
    // Vẽ theo một TẦM NGẮM 5.000 km, không theo độ dài chu kỳ — hệ thống chỉ
    // lưu mốc đồng hồ kế tiếp, không lưu chu kỳ, nên không có cách nào biết
    // chiếc này bảo dưỡng mỗi 10.000 hay 20.000 km. Trong tầm ngắm thì thanh
    // đầy dần khi xe càng gần kỳ; ngoài tầm ngắm thì thanh rỗng, nghĩa là
    // "chưa phải lo". Con số thật nằm ở chú giải, thanh chỉ để nhìn nhanh.
    const TAM_NGAM = 5000;
    const daDung = con <= 0 ? 100
      : Math.min(100, Math.max(0, Math.round((1 - con / TAM_NGAM) * 100)));
    const lop = con <= 500 ? 'r' : con <= 2000 ? 'a' : '';
    const chu = con <= 0
      ? `đã quá kỳ bảo dưỡng ${Math.abs(con).toLocaleString('vi-VN')} km`
      : `còn ${con.toLocaleString('vi-VN')} km đến kỳ bảo dưỡng`;
    return `<div class="kmbar" title="${esc(chu)} · đồng hồ ${Number(v.so_km).toLocaleString('vi-VN')} km · thanh vẽ trong tầm ${TAM_NGAM.toLocaleString('vi-VN')} km"
      ><i class="${lop}" style="width:${daDung}%"></i></div>`;
  }

  function oXe(v, ngayIso, o) {
    const chu = {
      free: '', ready: 'sẵn sàng', trip: 'Trip', run: 'đang chạy',
      done: 'xong', mt: '🔧 bảo dưỡng', lock: '🔒 khoá', conf: '⚠ thiếu tổ lái',
    }[o.trang_thai] || '';
    const to = (o.to_lai || []).length
      ? `<span class="cr">${o.to_lai.map(c => `<i>${esc(c)}</i>`).join('')}</span>` : '';
    const goi = o.trip_id ? `${o.trip_id} · ${tenCa(o.ca).toLowerCase()}` : `${tenCa(o.ca)} · ${chu || 'rảnh'}`;
    return `<div class="vs ${o.trang_thai}" role="button" tabindex="0" title="${esc(goi)}"
      data-veh="${esc(v.vehicle_id)}" data-ngay="${ngayIso}" data-ca="${o.ca}"
      data-tt="${o.trang_thai}" data-trip="${esc(o.trip_id || '')}"
      ><span class="t">${kyCa(o.ca)}</span>${chu ? `<small>${esc(chu)}</small>` : ''}${to}</div>`;
  }

  /* ----- toàn bãi ----- */
  function veToanBai() {
    const b = state.bang;
    el('ssv5-depot-title').innerHTML = `Toàn bộ bãi <small>${b.cac_bai.length} bãi · ${b.cac_to.length} tổ</small>`;
    el('ssv5-teams').innerHTML = b.cac_to.map(t =>
      `<button type="button" class="teamb" data-team="${esc(t.team_code || '')}" data-depot="${esc(t.depot_code || '')}">
        <b>${esc(t.ten)}</b> ${t.so_tai_xe} người</button>`).join('')
      || '<span style="color:#7b8796;font-size:12.5px">Chưa có tổ nào — gán tổ cho tài xế ở cột trái của lưới nhân sự.</span>';

    el('ssv5-dcover').innerHTML = `<div>Bãi · người và xe</div>`
      + b.pham_vi.cac_ngay.map(n => `<div><div class="dn ${n.hom_nay ? 'today' : ''}">${esc(n.thu)} <span>${ddmm(n.ngay)}</span></div></div>`).join('')
      + `<div style="display:flex;align-items:center;justify-content:center;font-size:11px;color:#7b8796;font-weight:700">Thiếu</div>`;

    // Mỗi bãi MỘT dải riêng, tính từ `do_phu_theo_bai`. Trước đây cả ba bãi
    // dùng chung độ phủ của toàn phạm vi, nên ba hàng giống nhau y hệt và dải
    // nhiệt không nói được điều duy nhất nó tồn tại để nói: bãi nào đang thiếu.
    // Ba hàng giống nhau còn tệ hơn không có dải nào, vì người xem tin là ba
    // bãi đều đủ.
    // "Không có xe nào phải chạy" KHÁC "đủ người". Tô cả hai cùng màu xanh thì
    // một bãi ngồi không cả tuần đọc ra như một bãi chạy hết công suất — và cả
    // dải nhiệt thành một khối xanh không nói gì. Xám nhạt = không có việc.
    const KHONG_VIEC = '#eef2f7';
    const mau = t => t >= 1 ? '#1a73e8' : t >= 0.8 ? '#c7ddf8' : t >= 0.5 ? '#fbd0d0' : '#d32f2f';
    const theoBai = b.do_phu_theo_bai || [];
    el('ssv5-drows').innerHTML = theoBai.map(bb => {
      const o = bb.cac_ngay.map(n => {
        // Một ô = 24 giờ, chia thành ba khối tám giờ theo ba ca. Chia đều 24
        // vạch như bản mẫu thì ba ca không phân biệt được, mà ranh giới ca
        // chính là chỗ độ phủ thay đổi.
        const vach = n.cac_ca.map(c => {
          const khongViec = c.can === 0;
          const t = khongViec ? KHONG_VIEC : mau(Math.min(1, c.truc / c.can));
          const goi = khongViec
            ? `${kyCa(c.ca)} ${n.thu}: không có xe nào phải chạy · ${c.truc} người trực`
            : `${kyCa(c.ca)} ${n.thu}: ${c.truc} người trực / ${c.can} xe phải chạy`;
          return Array.from({ length: 8 },
            () => `<i style="--h:${t}" title="${esc(goi)}"></i>`).join('');
        }).join('');
        return `<div><div class="heat">${vach}</div></div>`;
      }).join('');
      return `<button type="button" class="dep" data-depot="${esc(bb.depot_code || '')}">
        <div><b>${esc(bb.ten)}</b><div style="font-size:11px;color:#7b8796">${bb.so_tai_xe} người · ${bb.so_xe} xe${
          bb.so_xe && !bb.so_tai_xe ? ' · <span style="color:#d32f2f;font-weight:700">chưa có tài xế</span>' : ''}</div></div>
        ${o}
        <div class="side ${bb.thieu >= 8 ? 'r' : bb.thieu ? 'a' : 'g'}">${bb.thieu}<small>${bb.thieu ? 'suất' : 'đủ'}</small></div>
      </button>`;
    }).join('') || '<div class="empty" style="margin:14px">Chưa có bãi nào khai mã bãi.</div>';
  }

  /* ------------------------------------------------------------- cột phải -- */
  function moKhung(ma, tieuDe, buoc) {
    state.khung = ma;
    el('ssv5-ptitle').innerHTML = tieuDe;
    el('ssv5-pstep').textContent = buoc || '';
    veCotPhai();
  }

  function veCotPhai() {
    if (!state.bang) return;
    const than = el('ssv5-pbody');
    if (state.khung === 'shift') { than.innerHTML = khungXepCa(); return; }
    if (state.khung === 'vcell') { than.innerHTML = khungOXe(); return; }
    if (state.khung === 'gen') { than.innerHTML = khungSinhLich(); return; }
    if (state.khung === 'team') { than.innerHTML = khungDoiTo(); return; }
    if (state.khung === 'fill') { than.innerHTML = khungLapCa(); return; }
    than.innerHTML = khungViecCanLam();
  }

  function khungViecCanLam() {
    const v = state.bang.viec_can_lam;
    const ds = state.tab === 'veh' ? v.xe : v.nhan_su;
    el('ssv5-ptitle').innerHTML = `Việc cần làm <span class="tag ${ds.length ? 't-red' : 't-green'}">${ds.length}</span>`;
    el('ssv5-pstep').textContent = state.tab === 'veh' ? 'của xe trong kỳ này' : 'của nhân sự trong kỳ này';
    if (!ds.length) {
      return `<div class="check ok">✓ Không có việc nào đang treo trong kỳ này.</div>`;
    }
    return ds.map((x, i) => {
      const coDich = x.ngay && x.ca;
      // Ca thiếu người thì việc cần làm là XẾP NGƯỜI, nên nút chính là "Xếp".
      // "Tới đó" chỉ nhảy tới ô trống, còn phải tự đoán xếp ai.
      const lap = x.loai === 'thieu_nguoi';
      return `<div class="need">
        <div class="g"><b>${esc(x.tieu_de)}</b><span>${esc(x.mo_ta)}</span></div>
        ${lap ? `<button type="button" class="a" data-lap-ca="1" data-ngay="${esc(x.ngay)}" data-ca="${esc(x.ca)}">Xếp</button>`
          : coDich ? `<button type="button" class="a ${x.muc === 'cao' ? '' : 'n'}" data-viec="${i}">Tới đó</button>` : ''}
      </div>`;
    }).join('');
  }

  function khungXepCa() {
    const c = state.chon;
    if (!c) return `<div class="empty">Chọn một ô trên lưới để xếp ca.</div>`;
    const p = state.bang.nhan_su.find(x => x.driver_id === c.drv) || {};
    const daCo = !!c.shift;
    const khoa = c.tt === 'lock';
    return `
      <div class="sum">
        <div><span>Nhân sự</span><b>${esc(p.ten || c.drv)}</b></div>
        <div><span>Ngày</span><b>${ddmm(c.ngay)}</b></div>
      </div>
      <div class="lbl">Ca</div>
      <div class="shifts" id="ssv5-ca-chon">
        ${CA.map(x => `<button type="button" class="sopt ${x.ma === c.ca ? 'on' : ''}" data-ca="${x.ma}">
          <b>${x.ten}</b><span>${gioCa(x.ma)}</span></button>`).join('')}
      </div>
      <div class="lbl">Xe đi kèm</div>
      <select class="cta2" id="ssv5-xe-chon" style="height:36px;text-align:left;padding:0 8px">
        <option value="">— không gán xe —</option>
        ${state.bang.xe.map(v => `<option value="${esc(v.vehicle_id)}" ${v.vehicle_id === (c.veh || p.xe_mac_dinh) ? 'selected' : ''}>${esc(v.vehicle_id)}${v.loai ? ' · ' + esc(v.loai) : ''}</option>`).join('')}
      </select>
      ${khoa ? `<div class="check bad">Ca này đang khoá vì có Trip ${esc(c.trip)} từ màn Điều phối. Sửa xe, giờ hoặc tổ lái ở màn Điều phối — sửa ở đây là sửa sau lưng Điều phối.</div>`
        : `<div class="check info">Máy chủ kiểm khi lưu: không trùng ca, nghỉ giữa hai ca, và trần ${esc(48)}h/tuần. Vướng thì nó nói ra vướng gì.</div>`}
      <button type="button" class="cta" id="ssv5-luu" ${khoa ? 'disabled' : ''}>${daCo ? 'Lưu thay đổi' : 'Lưu ca'}</button>
      <button type="button" class="cta2" id="ssv5-phep" ${khoa ? 'disabled' : ''}>Đánh dấu nghỉ phép</button>
      ${daCo && !khoa ? `<button type="button" class="cta3" id="ssv5-xoa">Xoá ca</button>` : ''}
      ${khoa && c.trip ? `<button type="button" class="cta2" id="ssv5-mo-dieu-phoi">Mở Điều phối →</button>` : ''}
      <button type="button" class="cta2" data-ve-viec="1">← Quay lại Việc cần làm</button>`;
  }

  function khungOXe() {
    const c = state.chonXe;
    if (!c) return `<div class="empty">Chọn một ô trên lưới xe.</div>`;
    const v = state.bang.xe.find(x => x.vehicle_id === c.veh) || {};
    let than = '';
    if (['trip', 'run', 'done'].includes(c.tt)) {
      than = `<div class="check info">Trip thuộc màn Điều phối. Sửa xe, giờ hoặc tổ lái ở đó.</div>
        <button type="button" class="cta" id="ssv5-mo-dieu-phoi">Mở Điều phối →</button>`;
    } else if (c.tt === 'conf') {
      than = `<div class="check bad">✗ ${esc(c.trip)} đã điều phối cho xe này nhưng không ai trực ca ${tenCa(c.ca).toLowerCase()}. Điều phối sẽ không gửi được lệnh.</div>
        <div class="lbl">Xử lý</div>
        <button type="button" class="opt" data-sang-nhan-su="1"><span class="av">👤</span>
          <div class="g"><b>Xếp người vào ca này</b><span>Sang lưới nhân sự, lọc đúng ca đang thiếu</span></div></button>
        <button type="button" class="cta2" id="ssv5-mo-dieu-phoi">Mở Điều phối →</button>`;
    } else if (c.tt === 'mt' || c.tt === 'lock') {
      than = `<div class="sum"><div><span>Lý do</span><b>${esc(c.nhan || (c.tt === 'mt' ? 'Bảo dưỡng' : 'Khoá xe'))}</b></div>
        <div><span>Nguồn</span><b>${c.tt === 'mt' ? 'Yêu cầu bảo dưỡng' : 'Trạng thái xe'}</b></div></div>
        <div class="check info">Lịch bảo dưỡng do màn Bảo dưỡng quản. Màn này chỉ hiện ra để người xếp ca không xếp người vào một xe đang trong garage.</div>`;
    } else {
      const coTo = (c.to_lai || '').length > 0;
      than = `<div class="check ${coTo ? 'ok' : 'info'}">${coTo
        ? '✓ Xe rảnh và đã có tổ lái trong ca này — Điều phối sẽ thấy xe này là ứng viên.'
        : 'Xe rảnh nhưng không ai trực ca này, nên Điều phối sẽ không đề xuất xe. Xếp người vào ca ở lưới nhân sự.'}</div>
        <div class="lbl">Làm gì với ca này</div>
        <button type="button" class="opt" data-sang-nhan-su="1"><span class="av">👤</span>
          <div class="g"><b>Xếp tổ lái vào ca này</b><span>Sang lưới nhân sự để chọn người</span></div></button>`;
    }
    return `
      <div class="sum">
        <div><span>Xe</span><b>${esc(v.vehicle_id || c.veh)}</b></div>
        <div><span>Ngày · ca</span><b>${ddmm(c.ngay)} · ${tenCa(c.ca)}</b></div>
      </div>
      ${than}
      <button type="button" class="cta2" data-ve-viec="1">← Quay lại Việc cần làm</button>`;
  }

  function khungSinhLich() {
    const soNguoi = state.bang.nhan_su.length;
    const coMau = state.bang.nhan_su.filter(p => p.mau_xoay).length;
    el('ssv5-ptitle').textContent = 'Sinh lịch theo mẫu';
    el('ssv5-pstep').textContent = state.team ? `Tổ ${state.team}` : (state.depot ? tenBai(state.depot) : 'tất cả tài xế');
    return `
      <div class="sum">
        <div><span>Phạm vi</span><b>${soNguoi} người</b></div>
        <div><span>Từ ngày</span><b>${ddmm(state.start)}</b></div>
      </div>
      <div class="lbl">Số ngày sinh</div>
      <select class="cta2" id="ssv5-gen-ngay" style="height:36px;text-align:left;padding:0 8px">
        <option value="7">7 ngày (một tuần)</option>
        <option value="14">14 ngày</option>
        <option value="30" selected>30 ngày (một tháng)</option>
      </select>
      <div class="lbl">Mẫu xoay dùng cho người CHƯA có mẫu riêng</div>
      <input class="cta2" id="ssv5-gen-mau" value="SSCCĐĐ--" style="height:36px;text-align:left;padding:0 8px;font-family:ui-monospace,Menlo,monospace">
      <div class="check info">${coMau}/${soNguoi} người đã có mẫu riêng — những người đó dùng mẫu của họ, không dùng mẫu ở trên.
        S sáng · C chiều · Đ đêm · <b>-</b> nghỉ.</div>
      <div class="check ok">Không ghi đè: ngày nào đã có lịch thì bỏ qua — kể cả ca đã khoá vì có Trip và ngày nghỉ phép.</div>
      <button type="button" class="cta" id="ssv5-gen-thu">Chạy thử (chưa ghi)</button>
      <button type="button" class="cta2" id="ssv5-gen-that">Sinh thật vào hệ thống</button>
      <div id="ssv5-gen-kq"></div>
      <button type="button" class="cta2" data-ve-viec="1">← Quay lại Việc cần làm</button>`;
  }

  /**
   * KHUNG LAP CA THIEU NGUOI — mot phuong an that, khong phai bon phuong an gia.
   *
   * Ban mau ve bon cach xu ly: doi ca, muon nguoi to khac, tang ca cho duyet,
   * dang ca mo tren app. Ba cach sau khong co co so nao trong he thong — khong
   * co bang dang ky nhan ca, khong co luong duyet tang ca. Ve bon nut ma ba nut
   * khong lam gi thi nguoi dung bam thu ba lan roi thoi tin ca man hinh.
   *
   * Con lai MOT cach that: ai dang ranh ca do. May chu tinh tu lich that, xep
   * de truoc kho sau, va bam mot nguoi la GHI THAT qua dung duong luu ca — nen
   * moi rang buoc cua may chu van chan.
   */
  function khungLapCa() {
    const f = state.lapCa;
    if (!f) return `<div class="empty">Chọn một ca đang thiếu người.</div>`;
    el('ssv5-ptitle').innerHTML = `Lấp ca thiếu người`;
    el('ssv5-pstep').textContent = `${tenCa(f.ca)} ${ddmm(f.ngay)}`;
    if (f.dangNap) return `<div class="empty">Đang tính danh sách người có thể nhận ca này…</div>`;
    if (f.loi) return `<div class="check bad">${esc(f.loi)}</div>
      <button type="button" class="cta2" data-ve-viec="1">← Quay lại Việc cần làm</button>`;

    const uv = f.ung_vien || [];
    const nhomTen = { ranh: 'Rảnh hôm đó', doi_ca: 'Đang trực ca khác — phải đổi ca', qua_gio: 'Nhận vào là vượt trần giờ' };
    const nhomKieu = { ranh: '', doi_ca: 'w', qua_gio: 'kho' };
    let than = `<div class="sum">
      <div><span>Ca cần người</span><b>${esc(tenCa(f.ca))} ${gioCa(f.ca)}</b></div>
      <div><span>Ngày</span><b>${ddmm(f.ngay)}</b></div></div>`;
    if (!uv.length) {
      return than + `<div class="check bad">Không còn ai có thể nhận ca này trong phạm vi đang xem.
        Ai cũng đã trực đúng ca đó, đang có chuyến, hoặc đang nghỉ phép. Mở rộng phạm vi sang cả bãi,
        hoặc xem lại số xe phải chạy ca này ở màn Điều phối.</div>
        <button type="button" class="cta2" data-ve-viec="1">← Quay lại Việc cần làm</button>`;
    }
    ['ranh', 'doi_ca', 'qua_gio'].forEach(muc => {
      const ds = uv.filter(x => x.muc === muc);
      if (!ds.length) return;
      than += `<div class="lbl">${nhomTen[muc]} · ${ds.length} người</div>`
        + ds.map(x => `<button type="button" class="opt" data-uv="${esc(x.driver_id)}">
            <span class="av">${esc(x.chu_cai)}</span>
            <div class="g"><b>${esc(x.ten)}</b><span>${esc(x.ly_do)}</span></div>
            <span class="why ${nhomKieu[muc]}">${x.gio_tuan}h → ${x.gio_sau_khi_nhan}h</span></button>`).join('');
    });
    than += `<div class="check info">Bấm một người là ghi ca thật vào hệ thống. Máy chủ vẫn kiểm
      trùng ca, nghỉ giữa hai ca và trần 48h/tuần — vướng thì nó nói ra vướng gì.</div>
      <button type="button" class="cta2" data-ve-viec="1">← Quay lại Việc cần làm</button>`;
    return than;
  }

  async function moLapCa(ngay, ma_ca) {
    state.lapCa = { ngay, ca: ma_ca, dangNap: true };
    moKhung('fill', 'Lấp ca thiếu người', `${tenCa(ma_ca)} ${ddmm(ngay)}`);
    try {
      const ds = new URLSearchParams({ date: ngay, shift: ma_ca });
      if (state.depot) ds.set('depot', state.depot);
      if (state.team) ds.set('team', state.team);
      const kq = await api(`/api/tms/scheduling/fill-candidates?${ds}`);
      state.lapCa = { ngay, ca: ma_ca, ung_vien: kq.ung_vien, so_gio_ca: kq.so_gio_ca };
    } catch (loi) {
      state.lapCa = { ngay, ca: ma_ca, loi: loi.message };
    }
    veCotPhai();
  }

  /** Ghi ca cho mot ung vien duoc chon. Di dung duong luu ca da co. */
  async function nhanCa(nut, driverId) {
    const f = state.lapCa;
    if (!f) return;
    const nguoi = (f.ung_vien || []).find(x => x.driver_id === driverId);
    if (!nguoi) return;
    if (!window.confirm(`Xếp ${nguoi.ten} vào ca ${tenCa(f.ca).toLowerCase()} ngày ${ddmm(f.ngay)}?`
      + `

${nguoi.ly_do}`)) return;
    nut.disabled = true;
    try {
      await api('/api/tms/scheduling/driver-shifts', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: `TAY-${driverId}-${f.ngay.replace(/-/g, '')}-${f.ca}`,
          driver_id: driverId,
          vehicle_id: nguoi.xe_mac_dinh || null,
          shift_type: f.ca,
          availability_kind: 'work',
          shift_start: mocCa(f.ngay, f.ca, false),
          shift_end: mocCa(f.ngay, f.ca, true),
          status: 'planned',
          notes: `Lấp ca thiếu người từ màn Sắp lịch (${nguoi.muc})`,
        }),
      });
      thongBao(`Đã xếp ${nguoi.ten} vào ca ${tenCa(f.ca).toLowerCase()} ${ddmm(f.ngay)}.`);
      await nap();
      await moLapCa(f.ngay, f.ca);
    } catch (loi) {
      thongBao(loi.message, true);
    } finally {
      nut.disabled = false;
    }
  }

  function khungDoiTo() {
    const p = state.bang.nhan_su.find(x => x.driver_id === state.doiTo);
    if (!p) return `<div class="empty">Không thấy tài xế này trong kỳ đang xem.</div>`;
    el('ssv5-ptitle').textContent = 'Bãi, tổ và mẫu xoay';
    el('ssv5-pstep').textContent = p.ten;
    const bai = state.bang.cac_bai.filter(b => b.depot_code);
    return `
      <div class="sum"><div><span>Nhân sự</span><b>${esc(p.ten)}</b></div>
        <div><span>Mã</span><b>${esc(p.driver_id)}</b></div></div>
      <div class="lbl">Bãi</div>
      <select class="cta2" id="ssv5-to-bai" style="height:36px;text-align:left;padding:0 8px">
        <option value="">— chưa phân bãi —</option>
        ${bai.map(b => `<option value="${esc(b.depot_code)}" ${b.depot_code === p.depot_code ? 'selected' : ''}>${esc(b.ten)}</option>`).join('')}
      </select>
      <div class="lbl">Tổ</div>
      <input class="cta2" id="ssv5-to-ma" value="${esc(p.team_code || '')}" placeholder="Ví dụ: A" style="height:36px;text-align:left;padding:0 8px">
      <div class="lbl">Mẫu xoay ca</div>
      <input class="cta2" id="ssv5-to-mau" value="${esc(p.mau_xoay || '')}" placeholder="SSCCĐĐ--" style="height:36px;text-align:left;padding:0 8px;font-family:ui-monospace,Menlo,monospace">
      <div class="check info">Mẫu neo vào một mốc cố định, không vào tuần đang xem — nên xem tuần sau thì chu kỳ chạy tiếp, không quay lại từ đầu. Để trống là bỏ mẫu, trở lại xếp tay.</div>
      <button type="button" class="cta" id="ssv5-to-luu">Lưu</button>
      <button type="button" class="cta2" data-ve-viec="1">← Quay lại Việc cần làm</button>`;
  }

  /* ------------------------------------------------------- chọn ô, ghi dữ liệu */
  function chonO(o) {
    el('ssv5-rows').querySelectorAll('.sh.sel').forEach(x => x.classList.remove('sel'));
    o.classList.add('sel');
    state.chon = {
      drv: o.dataset.drv, ngay: o.dataset.ngay, ca: o.dataset.ca, tt: o.dataset.tt,
      shift: o.dataset.shift || null, ver: o.dataset.ver === '' ? null : Number(o.dataset.ver),
      trip: o.dataset.trip || null, veh: null,
    };
    const daCo = !!state.chon.shift;
    moKhung('shift', daCo ? 'Sửa ca' : 'Xếp ca', daCo ? 'đã có ca · sửa hoặc xoá' : 'ô trống · chọn ca rồi lưu');
  }

  function chonOXe(o) {
    el('ssv5-vrows').querySelectorAll('.vs.sel').forEach(x => x.classList.remove('sel'));
    o.classList.add('sel');
    const v = state.bang.xe.find(x => x.vehicle_id === o.dataset.veh);
    const ngay = (v && v.cac_ngay.find(d => d.ngay === o.dataset.ngay)) || { cac_o: [] };
    const oData = ngay.cac_o.find(x => x.ca === o.dataset.ca) || {};
    state.chonXe = {
      veh: o.dataset.veh, ngay: o.dataset.ngay, ca: o.dataset.ca, tt: o.dataset.tt,
      trip: o.dataset.trip || null, nhan: oData.nhan, to_lai: oData.to_lai || [],
    };
    const ten = { trip: 'Chi tiết Trip', run: 'Trip đang chạy', done: 'Trip đã xong',
      conf: 'Trip thiếu tổ lái', mt: 'Bảo dưỡng', lock: 'Xe bị khoá',
      ready: 'Xe sẵn sàng', free: 'Xe rảnh' }[o.dataset.tt] || 'Ô xe';
    moKhung('vcell', esc(ten), `${o.dataset.veh} · ${ddmm(o.dataset.ngay)}`);
  }

  function moDoiTo(driverId) {
    state.doiTo = driverId;
    moKhung('team', 'Bãi, tổ và mẫu xoay', '');
  }

  async function xuLyCotPhai(e) {
    const nut = e.target.closest('button, .opt, .sopt');
    if (!nut) return;

    if (nut.dataset.veViec) { state.khung = state.tab === 'veh' ? 'vneed' : 'need'; veCotPhai(); return; }
    if (nut.dataset.viec != null) { toiViec(Number(nut.dataset.viec)); return; }
    if (nut.dataset.uv) { await nhanCa(nut, nut.dataset.uv); return; }
    if (nut.dataset.lapCa) { await moLapCa(nut.dataset.ngay, nut.dataset.ca); return; }
    if (nut.dataset.ca) {
      el('ssv5-ca-chon').querySelectorAll('.sopt').forEach(x => x.classList.remove('on'));
      nut.classList.add('on');
      return;
    }
    if (nut.dataset.sangNhanSu) {
      state.tab = 'staff';
      state.filter = 'all';
      ve();
      thongBao('Đã sang lưới nhân sự — chọn một ô ở đúng ngày và ca để xếp người.');
      return;
    }
    if (nut.id === 'ssv5-mo-dieu-phoi') {
      if (typeof window.switchView === 'function') window.switchView('dispatch');
      return;
    }
    if (nut.id === 'ssv5-luu') { await luuCa(nut, 'work'); return; }
    if (nut.id === 'ssv5-phep') { await luuCa(nut, 'leave'); return; }
    if (nut.id === 'ssv5-xoa') { await xoaCa(nut); return; }
    if (nut.id === 'ssv5-gen-thu') { await sinhLich(nut, true); return; }
    if (nut.id === 'ssv5-gen-that') { await sinhLich(nut, false); return; }
    if (nut.id === 'ssv5-to-luu') { await luuPhanTo(nut); return; }
  }

  function toiViec(i) {
    const v = state.bang.viec_can_lam;
    const x = (state.tab === 'veh' ? v.xe : v.nhan_su)[i];
    if (!x) return;
    if (x.vehicle_id) {
      state.tab = 'veh';
      state.vfilter = 'all';
      ve();
      const o = el('ssv5-vrows').querySelector(
        `.vs[data-veh="${CSS.escape(x.vehicle_id)}"][data-ngay="${x.ngay}"][data-ca="${x.ca}"]`);
      if (o) { o.scrollIntoView({ block: 'center' }); chonOXe(o); }
      return;
    }
    // Ca thiếu người: về lưới nhân sự, lọc đúng những người đang có ô "cần xếp"
    // rồi tô sáng cột của ngày đó. Không tự chọn một người — chọn ai là quyết
    // định của người xếp lịch, không phải của màn hình.
    state.tab = 'staff';
    state.filter = 'need';
    ve();
    const cot = el('ssv5-rows').querySelectorAll(`.sh[data-ngay="${x.ngay}"][data-ca="${x.ca}"]`);
    cot.forEach(o => { o.classList.add('sel'); });
    if (cot[0]) cot[0].scrollIntoView({ block: 'center' });
    thongBao(`${cot.length} ô đang trống ở ca ${tenCa(x.ca).toLowerCase()} ${ddmm(x.ngay)} — bấm một ô để xếp người.`);
  }

  async function luuCa(nut, loai) {
    const c = state.chon;
    if (!c) return;
    const maCa = (el('ssv5-ca-chon').querySelector('.sopt.on') || {}).dataset
      ? el('ssv5-ca-chon').querySelector('.sopt.on').dataset.ca : c.ca;
    const xe = el('ssv5-xe-chon').value || null;
    // Máy chủ ĐÒI mã ca — nó không tự sinh. Và mã phải TIỀN ĐỊNH theo
    // (người, ngày, ca) chứ không phải sinh ngẫu nhiên: lưu hai lần cùng một ô
    // thì lần sau là SỬA, không phải tạo thêm một ca thứ hai trùng chỗ. Có hai
    // ca trùng một ô thì lưới hiện một ca mà giờ tuần đếm cả hai.
    const ma = `TAY-${c.drv}-${c.ngay.replace(/-/g, '')}-${maCa}`;
    const than = {
      id: ma,
      driver_id: c.drv,
      vehicle_id: loai === 'leave' ? null : xe,
      shift_type: maCa,
      availability_kind: loai,
      shift_start: mocCa(c.ngay, maCa, false),
      shift_end: mocCa(c.ngay, maCa, true),
      status: 'planned',
      notes: loai === 'leave' ? 'Nghỉ phép, ghi từ màn Sắp lịch' : 'Xếp tay từ màn Sắp lịch',
    };
    nut.disabled = true;
    try {
      if (c.shift) {
        // Sửa một ca đã có: mã trong đường dẫn thắng, nên KHÔNG gửi kèm `id`
        // đã tính ở trên — đổi ca sáng thành ca chiều thì mã tính ra khác mã
        // đang có, và gửi cả hai đọc như đang đòi đổi mã bản ghi.
        delete than.id;
        than.expected_version = c.ver;
        await api(`/api/tms/scheduling/driver-shifts/${encodeURIComponent(c.shift)}`,
          { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(than) });
      } else {
        await api('/api/tms/scheduling/driver-shifts',
          { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(than) });
      }
      thongBao(`Đã lưu ${loai === 'leave' ? 'nghỉ phép' : 'ca ' + tenCa(maCa).toLowerCase()} · ${ddmm(c.ngay)}.`);
      state.chon = null;
      state.khung = 'need';
      await nap();
    } catch (loi) {
      thongBao(loi.message, true);
    } finally {
      nut.disabled = false;
    }
  }

  async function xoaCa(nut) {
    const c = state.chon;
    if (!c || !c.shift) return;
    if (!window.confirm(`Xoá ca ${tenCa(c.ca).toLowerCase()} ngày ${ddmm(c.ngay)}?`)) return;
    nut.disabled = true;
    try {
      await api(`/api/tms/scheduling/driver-shifts/${encodeURIComponent(c.shift)}`, { method: 'DELETE' });
      thongBao('Đã xoá ca.');
      state.chon = null;
      state.khung = 'need';
      await nap();
    } catch (loi) {
      thongBao(loi.message, true);
    } finally {
      nut.disabled = false;
    }
  }

  async function sinhLich(nut, chiThu) {
    const soNgay = Number(el('ssv5-gen-ngay').value) || 7;
    const mau = el('ssv5-gen-mau').value.trim();
    if (!chiThu && !window.confirm(`Sinh lịch ${soNgay} ngày từ ${ddmm(state.start)} cho ${state.bang.nhan_su.length} người?`
      + '\n\nNgày nào đã có lịch thì bỏ qua, không ghi đè.')) return;
    nut.disabled = true;
    try {
      const kq = await api('/api/tms/scheduling/generate-from-pattern', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start: state.start, days: soNgay, depot: state.depot, team: state.team,
          rotation_pattern: mau || null, dry_run: chiThu,
        }),
      });
      const d = kq.dem;
      el('ssv5-gen-kq').innerHTML = `
        <div class="sum" style="margin-top:8px">
          <div style="background:#e7f6ec"><span style="color:#15803d">${chiThu ? 'Sẽ sinh' : 'Đã sinh'}</span><b style="color:#15803d">${d.da_sinh} ca</b></div>
          <div><span>Nghỉ theo mẫu</span><b>${d.bo_qua_nghi_theo_mau}</b></div>
          <div><span>Đã có lịch</span><b>${d.bo_qua_da_co}</b></div>
          <div style="background:${d.loi ? '#fdecec' : '#f8fafc'}"><span style="color:${d.loi ? '#d32f2f' : '#7b8796'}">Vướng ràng buộc</span><b style="color:${d.loi ? '#d32f2f' : 'inherit'}">${d.loi}</b></div>
        </div>
        ${d.khong_co_mau ? `<div class="check info">${d.khong_co_mau} người không có mẫu xoay và cũng không nhận mẫu chung — chưa sinh cho họ.</div>` : ''}
        ${(kq.loi || []).length ? `<div class="check bad">${kq.loi.slice(0, 5).map(x =>
          `${esc(x.ten)} · ${ddmm(x.ngay)} · ${esc(x.thong_diep)}`).join('<br>')}</div>` : ''}`;
      if (!chiThu) { thongBao(`Đã sinh ${d.da_sinh} ca vào hệ thống.`); await nap(); state.khung = 'gen'; veCotPhai(); }
    } catch (loi) {
      thongBao(loi.message, true);
    } finally {
      nut.disabled = false;
    }
  }

  async function luuPhanTo(nut) {
    nut.disabled = true;
    try {
      await api(`/api/tms/scheduling/drivers/${encodeURIComponent(state.doiTo)}/assignment`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          depot_code: el('ssv5-to-bai').value || null,
          team_code: el('ssv5-to-ma').value.trim() || null,
          rotation_pattern: el('ssv5-to-mau').value.trim() || null,
        }),
      });
      thongBao('Đã lưu bãi, tổ và mẫu xoay.');
      state.khung = 'need';
      await nap();
    } catch (loi) {
      thongBao(loi.message, true);
    } finally {
      nut.disabled = false;
    }
  }

  /* ------------------------------------------------------------- tìm kiếm -- */
  const toSang = (chu, q) => esc(chu).replace(
    new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi'), m => `<mark>${m}</mark>`);

  function goiY() {
    const dd = el('ssv5-dd');
    const q = el('ssv5-q').value.trim();
    if (!q || !state.bang) { dd.classList.remove('show'); return; }
    const ql = q.toLowerCase();
    const co = x => String(x || '').toLowerCase().includes(ql);
    const ng = state.bang.nhan_su.filter(p => co(p.ten) || co(p.driver_id) || co(p.team_code)).slice(0, 6);
    const xe = state.bang.xe.filter(v => co(v.vehicle_id) || co(v.loai)).slice(0, 5);
    const to = state.bang.cac_to.filter(t => co(t.ten) || co(t.team_code)).slice(0, 4);
    const bai = state.bang.cac_bai.filter(b => co(b.ten) || co(b.depot_code)).slice(0, 4);
    let h = '';
    if (ng.length) h += `<div class="sec">TÀI XẾ</div>` + ng.map(p =>
      `<button type="button" class="it" data-k="p" data-id="${esc(p.driver_id)}">
        <span class="av">${esc(p.chu_cai)}</span>
        <div><b>${toSang(p.ten, q)}</b><span>${toSang(p.driver_id, q)} · ${esc(p.vai_tro || '')} · ${p.team_code ? 'Tổ ' + esc(p.team_code) : 'chưa phân tổ'}</span></div>
        <span class="tag ${p.vuot_gio ? 't-amber' : 't-green'}">${p.gio_tuan}h</span></button>`).join('');
    if (xe.length) h += `<div class="sec">XE</div>` + xe.map(v =>
      `<button type="button" class="it" data-k="v" data-id="${esc(v.vehicle_id)}">
        <span class="av g">${esc(String(v.vehicle_id).slice(-6))}</span>
        <div><b>${toSang(v.vehicle_id, q)}</b><span>${esc(v.loai || 'chưa khai loại xe')} · ${v.ngay_ranh} ngày rảnh</span></div>
        <span class="tag ${coTrangThaiXe(v, ['conf']) ? 't-red' : 't-green'}">${coTrangThaiXe(v, ['conf']) ? 'thiếu tổ lái' : 'ổn'}</span></button>`).join('');
    if (to.length) h += `<div class="sec">TỔ</div>` + to.map(t =>
      `<button type="button" class="it" data-k="t" data-id="${esc(t.team_code || '')}" data-depot="${esc(t.depot_code || '')}">
        <span class="av g">${esc((t.team_code || '?').slice(0, 2))}</span>
        <div><b>${toSang(t.ten, q)}</b><span>${t.so_tai_xe} người</span></div>
        <span class="tag">mở lưới</span></button>`).join('');
    if (bai.length) h += `<div class="sec">BÃI</div>` + bai.map(b =>
      `<button type="button" class="it" data-k="d" data-id="${esc(b.depot_code || '')}">
        <span class="av g">▦</span>
        <div><b>${toSang(b.ten, q)}</b><span>${b.so_tai_xe} người · ${b.so_xe} xe</span></div>
        <span class="tag">độ phủ</span></button>`).join('');
    if (!h) h = `<div class="empty">Không thấy "${esc(q)}" trong kỳ đang xem. Thử mã tài xế hoặc biển số.</div>`;
    dd.innerHTML = h;
    dd.classList.add('show');
  }

  function chonGoiY(it) {
    el('ssv5-dd').classList.remove('show');
    const k = it.dataset.k, id = it.dataset.id;
    if (k === 'p') {
      state.tab = 'staff'; state.filter = 'all'; ve();
      const hang = el('ssv5-rows').querySelector(`.grid[data-drv="${CSS.escape(id)}"]`);
      if (hang) { hang.scrollIntoView({ block: 'center' }); toSangHang(hang); }
      el('ssv5-q').value = (state.bang.nhan_su.find(p => p.driver_id === id) || {}).ten || id;
    } else if (k === 'v') {
      state.tab = 'veh'; state.vfilter = 'all'; ve();
      const hang = el('ssv5-vrows').querySelector(`.vrow[data-veh="${CSS.escape(id)}"]`);
      if (hang) { hang.scrollIntoView({ block: 'center' }); toSangHang(hang); }
      el('ssv5-q').value = id;
    } else if (k === 't') {
      state.team = id || null;
      state.depot = it.dataset.depot || null;
      state.tab = 'staff'; el('ssv5-q').value = ''; nap();
    } else {
      state.depot = id || null; state.team = null; state.tab = 'staff';
      el('ssv5-q').value = ''; nap();
    }
  }

  function toSangHang(hang) {
    hang.classList.add('hl');
    setTimeout(() => hang.classList.remove('hl'), 2500);
  }

  /* ------------------------------------------------------------------ gắn -- */
  function mo() {
    if (!el(KHUNG)) return;
    dungKhung();
    if (!state.bang) nap();
  }

  // Bọc `switchMasterDataTab` thay vì sửa nó: hàm đó nằm trong `app.js` — tệp
  // đang có người khác sửa cùng lúc — và nó còn mười thẻ khác gọi vào.
  function bocDoiThe() {
    const cu = window.switchMasterDataTab;
    if (typeof cu !== 'function' || cu._ssv5) return false;
    const moi = function (ten, nut) {
      const kq = cu.apply(this, arguments);
      if (ten === 'md-tab-vehicles') setTimeout(mo, 0);
      return kq;
    };
    moi._ssv5 = true;
    window.switchMasterDataTab = moi;
    return true;
  }

  function batDau() {
    if (!bocDoiThe()) {
      // `app.js` nạp sau tệp này thì thử lại vài nhịp rồi thôi. Thử mãi thì một
      // trang không có màn Dữ liệu gốc sẽ chạy một bộ hẹn giờ vô hạn.
      let con = 40;
      const hen = setInterval(() => {
        if (bocDoiThe() || --con <= 0) clearInterval(hen);
      }, 150);
    }
    const the = el('md-tab-vehicles');
    if (the && the.style.display !== 'none') mo();
    document.addEventListener('keydown', e => {
      const q = el('ssv5-q');
      if (e.key === '/' && q && document.activeElement !== q && el(KHUNG)
        && el(KHUNG).offsetParent !== null) {
        e.preventDefault();
        q.focus();
      }
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', batDau);
  else batDau();

  // `moLapCa` xuất ra ngoài để màn khác gọi được vào đúng một ca đang thiếu —
  // và để bộ kiểm mở được khung đó khi bộ dữ liệu của tuần đang đủ người.
  window.SapLichV5 = { mo, nap, state, moLapCa };
})();

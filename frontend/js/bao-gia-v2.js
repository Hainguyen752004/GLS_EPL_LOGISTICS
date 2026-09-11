/* ==========================================================================
   MÀN BÁO GIÁ CƯỚC — dựng theo `nhap_UI__duan/quotation-page (1).html` và
   `nhap_UI__duan/SPEC-quotation-page.md`.

   THAY HẲN màn cũ, không chắp thêm vào nó. Màn cũ là một bảng "oracle" cộng
   một hộp thoại; bản thiết kế là một trang danh sách và một TRANG chi tiết có
   thanh đáy cố định — spec ghi rõ "không có modal". Khối cũ vẫn còn trong
   trang nhưng bị ẩn (`#qtv2-khoi-cu`), vì `app.js` còn vài đường gọi vào các
   ô của nó; xoá hẳn là một việc khác, làm riêng.

   BỐN CHỖ KHÁC BẢN MẪU, và đều khác có lý do:

     1. GIÁ THÀNH DO MÁY CHỦ TÍNH. Bản mẫu tự nhân `fuel × km + …` trong
        trình duyệt. Spec mục 6 tự ghi "đây là chỗ tính giá thành — UI không
        tự tính", và điều đó đúng: công thức thật do người dùng cấu hình ở màn
        Dữ liệu gốc, nên một bản sao trong JavaScript sẽ trôi khỏi nó và hai
        màn hiện hai con số cho cùng một chuyến.
     2. KHÔNG CÓ HỆ SỐ ×3,9. Bản mẫu điền sẵn `giá thành × 3,9` và chính spec
        gọi đó là "số demo, không có ý nghĩa nghiệp vụ". Thay bằng các mốc giá
        có nguồn mà `/price-preview` trả về (biên mục tiêu, lần trước).
     3. CÓ THÊM ĐƠN VỊ TÍNH CƯỚC. Chủ dự án chốt: báo giá theo đơn vị của
        khách (chuyến / tấn / m³ / kg / km), còn lệnh giao hàng khoá `VNĐ/chuyến`.
        Máy chủ quy đổi, nên hai con số không thể lệch nhau.
     4. TỶ GIÁ LẤY TỪ BẢNG TỶ GIÁ THẬT, không phải `USD: 25.400` viết cứng
        trong mã.
   ========================================================================== */

(function () {
  'use strict';

  const GOC = 'qtv2-root';
  const el = id => document.getElementById(id);

  /**
   * Cuon tới mot o. Khong vo neu moi truong khong co `scrollIntoView`.
   *
   * Vai webview nhung va cac phep soi bang jsdom khong co ham do. Truoc day
   * goi thang, va mot moi truong thieu no lam vo CA luoc bam: bam "Ghi nhan
   * khach chap nhan" thi trang thai da doi tren may chu roi, nhung man hinh
   * dung lai o giua vi buoc cuon nem loi.
   */
  function cuonToi(n) {
    if (n && typeof n.scrollIntoView === 'function') {
      n.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }
  const base = () => (window.API_BASE || window.location.origin || '');

  /* ---------------------------------------------------------------- số và chữ -- */

  /** Số kiểu Việt Nam: 1.407.740 chứ không phải 1,407,740. */
  function tien(n) {
    const x = Number(n);
    if (!isFinite(x)) return '—';
    return Math.round(x).toLocaleString('vi-VN');
  }

  /** Số có phần thập phân: 31,2 km. */
  function so(n, le) {
    const x = Number(n);
    if (!isFinite(x)) return '—';
    return x.toLocaleString('vi-VN', {
      minimumFractionDigits: 0,
      maximumFractionDigits: le === undefined ? 1 : le,
    });
  }

  function phanTram(x, le) {
    if (x === null || x === undefined || !isFinite(Number(x))) return '—';
    return so(Number(x) * 100, le === undefined ? 1 : le) + '%';
  }

  /** Đọc một số người dùng gõ, chấp nhận cả `4.200.000` và `4200000`. */
  function docSo(chu) {
    const s = String(chu === null || chu === undefined ? '' : chu)
      .replace(/[^\d,.-]/g, '')
      .replace(/\./g, '')
      .replace(',', '.');
    const x = parseFloat(s);
    return isFinite(x) ? x : 0;
  }

  function esc(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  /** `2026-09-08T07:00:00` -> giá trị cho `<input type="datetime-local">`. */
  function chuanDatetimeLocal(v) {
    if (!v) return '';
    const s = String(v);
    // Mốc lưu có thể kèm múi giờ hoặc là mốc trần. Đưa về giờ địa phương để ô
    // nhập hiện đúng thứ người dùng đã gõ, chứ không lệch 7 giờ.
    const d = new Date(s.length <= 10 ? s + 'T00:00:00' : s);
    if (isNaN(d.getTime())) return s.slice(0, 16);
    const p = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
  }

  /**
   * Mốc gửi lên máy chủ, KÈM MÚI GIỜ.
   *
   * Máy chủ hiểu một mốc trần là UTC. Gửi `2026-09-12T07:00` trần thì một ca
   * lấy hàng 07:00 giờ Việt Nam được ghi thành 14:00 giờ Việt Nam.
   */
  function mocGuiLen(v) {
    if (!v) return '';
    const s = String(v);
    if (/[+\-]\d\d:\d\d$/.test(s) || /Z$/.test(s)) return s;
    return (s.length === 16 ? s + ':00' : s) + '+07:00';
  }

  /**
   * Mốc do máy chủ trả về, hiện theo GIỜ VIỆT NAM.
   *
   * Máy chủ lưu mốc theo UTC và trả về dạng `2026-09-20 00:00:00` — không có
   * dấu múi giờ nào. In thẳng chuỗi đó ra màn hình thì một chuyến lấy hàng
   * 07:00 sáng hiện thành 00:00, và người điều phối đọc ra là nửa đêm.
   *
   * Không có dấu múi giờ thì hiểu là UTC, đúng theo cách hệ thống này lưu.
   */
  function gioVietNam(v) {
    if (!v) return '—';
    const s = String(v).trim();
    if (s.length <= 10) return s;                       // chỉ có ngày, không có giờ
    const coMuiGio = /[+\-]\d\d:?\d\d$/.test(s) || /Z$/i.test(s);
    const d = new Date(coMuiGio ? s : s.replace(' ', 'T') + 'Z');
    if (isNaN(d.getTime())) return s;
    const p = n => String(n).padStart(2, '0');
    return `${p(d.getDate())}/${p(d.getMonth() + 1)} ${p(d.getHours())}:${p(d.getMinutes())}`;
  }

  function ngayHomNayCong(ngay) {
    const d = new Date();
    d.setDate(d.getDate() + ngay);
    const p = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
  }

  /* ------------------------------------------------------------------ gọi API -- */

  async function api(duong, tuyChon) {
    const tra = await fetch(base() + duong, Object.assign({
      headers: { 'Content-Type': 'application/json' },
    }, tuyChon || {}));
    let goi = {};
    try { goi = await tra.json(); } catch (e) { goi = {}; }
    if (!tra.ok) {
      const loi = new Error((goi.error && goi.error.message) || goi.message
        || (goi.detail && (goi.detail.message || goi.detail))
        || `Máy chủ trả về HTTP ${tra.status}.`);
      loi.ma = (goi.error && goi.error.code) || (goi.detail && goi.detail.code);
      loi.http = tra.status;
      throw loi;
    }
    return goi && Object.prototype.hasOwnProperty.call(goi, 'data') ? goi.data : goi;
  }

  const doc = duong => api(duong);
  const ghi = (duong, than, cach) => api(duong, {
    method: cach || 'POST',
    body: JSON.stringify(than === undefined ? {} : than),
  });

  /**
   * Như `api` nhưng trả về CẢ GÓI, giữ lại `message` của máy chủ.
   *
   * Vì sao cần: `/send` trả hai câu khác nhau cho hai kết cục khác nhau — "đã
   * gửi cho khách" và "biên dưới ngưỡng nên chuyển sang chờ duyệt nội bộ".
   * Hiện một câu viết sẵn ở màn hình là để người bán ngồi đợi một câu trả lời
   * sẽ không bao giờ đến.
   */
  async function apiGoi(duong, tuyChon) {
    const tra = await fetch(base() + duong, Object.assign({
      headers: { 'Content-Type': 'application/json' },
    }, tuyChon || {}));
    let goi = {};
    try { goi = await tra.json(); } catch (e) { goi = {}; }
    if (!tra.ok) {
      const loi = new Error((goi.error && goi.error.message) || goi.message
        || (goi.detail && (goi.detail.message || goi.detail))
        || `Máy chủ trả về HTTP ${tra.status}.`);
      loi.ma = (goi.error && goi.error.code) || (goi.detail && goi.detail.code);
      loi.http = tra.status;
      throw loi;
    }
    return goi || {};
  }

  function thongBao(chu, loi) {
    if (!loi && typeof window.showToast === 'function') { window.showToast(chu); return; }
    let t = el('qtv2-toast');
    if (!t) {
      t = document.createElement('div');
      t.id = 'qtv2-toast';
      t.style.cssText = 'position:fixed;right:28px;bottom:78px;color:#fff;border-radius:12px;'
        + 'padding:12px 16px;font:600 13px/1.45 Inter,system-ui,sans-serif;display:flex;gap:10px;'
        + 'align-items:center;box-shadow:0 12px 32px rgba(15,28,46,.28);max-width:560px;z-index:60';
      document.body.appendChild(t);
    }
    t.innerHTML = `<span>${loi ? '⚠' : '✓'}</span><span>${esc(chu)}</span>`;
    t.style.background = loi ? '#8a1c1c' : '#0b2e5c';
    t.hidden = false;
    clearTimeout(t._hen);
    t._hen = setTimeout(() => { t.hidden = true; }, loi ? 7000 : 4600);
  }

  /* -------------------------------------------------------------- bảng tra cứu -- */

  const TRANG_THAI = {
    draft: ['Nháp', 't-blue'],
    pending_approval: ['Chờ duyệt nội bộ', 't-amber'],
    sent: ['Đã gửi · chờ khách', 't-amber'],
    approved: ['Đã gửi · chờ khách', 't-amber'],
    accepted: ['Đã chấp nhận', 't-green'],
    split: ['Đã tách DO', 't-purple'],
    rejected: ['Từ chối', ''],
    expired: ['Hết hạn', 't-red'],
  };

  const DON_VI_CUOC = [
    ['per_trip', 'Mỗi chuyến', 'chuyến'],
    ['per_tonne', 'Mỗi tấn', 'tấn'],
    ['per_m3', 'Mỗi m³', 'm³'],
    ['per_kg', 'Mỗi kg', 'kg'],
    ['per_km', 'Mỗi km', 'km'],
  ];
  const DVT_HANG = ["40'", "20'", 'Tấn', 'Pallet', 'Kiện', 'm³'];
  const LOAI_CHUNG_TU = ['Hợp đồng', 'PO của khách', 'Phiếu xuất kho', 'Packing list',
    'Tờ khai hải quan', 'Khác'];
  const LOAI_HANG = ['Hàng khô', 'Hàng lạnh', 'Hàng nặng / quá tải', 'Hàng nguy hiểm'];
  const XEP_CHONG = ['Không xếp chồng', 'Tối đa 2 lớp', 'Tối đa 3 lớp'];
  const NIEM_PHONG = ['Có · ghi số seal khi lấy hàng', 'Không'];
  const DIEU_KHOAN = ['30 ngày sau hoá đơn', '15 ngày sau hoá đơn', '45 ngày sau hoá đơn',
    'Trả trước'];

  const DO_VUA_TAI = {
    phu_hop: ['Phù hợp', 'ok'],
    sat_tai: ['Vừa sát tải', 'w'],
    khong_du_tai: ['Không đủ tải', 'no'],
    chua_biet: ['nhập tải trọng để gợi ý', 'q'],
  };

  const mauBien = b => (b === null || b === undefined) ? ''
    : (b >= 0.20 ? 'g' : b >= 0.15 ? 'a' : 'r');

  /* ------------------------------------------------------------------ trạng thái -- */

  const S = {
    khach: [], tuyen: [], loaiXe: [], tienTe: [],
    ds: [], kpi: null,
    the: 'all', locKpi: 'all',
    loc: { customer_id: '', route_id: '', owner: '', q: '' },
    q: null,              // báo giá đang mở
    xemTruoc: null,       // kết quả /price-preview gần nhất
    dongTach: [],         // các dòng của bảng tách DO
    dangLuu: false,
    henTinh: null,
  };

  const tuyenTheoMa = ma => S.tuyen.find(x => x.id === ma) || null;
  /** Số km của một tuyến, theo đúng thứ tự ưu tiên mà máy chủ dùng khi tính cước.
   *
   *  Một tuyến có hai con số km: `distance_km` là quãng danh nghĩa, `km_duong_bo`
   *  là quãng đường bộ thật (máy chủ gọi cột này là `road_distance_km`). Hàm tính
   *  giá thành lấy km đường bộ trước, chỉ rơi về quãng danh nghĩa khi nó trống.
   *  Tuyến VSIP II-A → Cái Mép chênh hẳn 8 km giữa hai con số, nên chỗ nào hiển
   *  thị km mà quên thứ tự này là in một quãng đường trong khi tiền tính theo
   *  quãng khác. Gom vào một chỗ để không phải nhớ lại ở từng màn.
   */
  const kmTuyen = rt => Number((rt && (rt.km_duong_bo || rt.road_distance_km || rt.distance_km)) || 0);
  const tenKhach = ma => {
    const k = S.khach.find(x => x.id === ma);
    return k ? (k.name || k.id) : (ma || '—');
  };
  const tenLoaiXe = ma => {
    const v = S.loaiXe.find(x => x.id === ma);
    return v ? (v.name || v.id) : (ma || '—');
  };
  const tyGia = ma => {
    if (!ma || ma === 'VND') return 1;
    const t = S.tienTe.find(x => String(x.code || x.id).toUpperCase() === String(ma).toUpperCase());
    const r = Number((t && (t.exchange_rate || t.rate)) || 0);
    return r > 0 ? r : 0;
  };
  /**
   * Đơn vị tiền HIỆN RA MÀN HÌNH. Chủ dự án chốt dùng CHỮ chứ không dùng ký
   * hiệu: "VNĐ" chứ không phải "₫", và ngoại tệ để nguyên mã (USD, THB, LAK).
   */
  const kyHieu = ma => ({ VND: 'VNĐ', USD: 'USD', THB: 'THB', LAK: 'LAK' })[ma] || (ma || 'VNĐ');

  /**
   * Tỷ giá của CHÍNH phiếu — `fx_rate` được khoá lúc gửi khách, nên số trên
   * phiếu cũ không nhảy theo bảng tỷ giá hôm nay. Phiếu chưa có thì lấy tỷ giá
   * hiện hành.
   */
  const tyGiaPhieu = q => {
    const r = Number(q && q.fx_rate);
    return r > 0 ? r : (tyGia(q && q.currency_code) || 1);
  };

  /**
   * Tiền theo ĐÚNG tiền tệ của phiếu. Máy chủ lưu mọi số tiền bằng VNĐ, nên
   * phải chia theo tỷ giá rồi mới gắn mã — gắn mã mà không chia là con số VNĐ
   * đội lốt USD. Ngoại tệ giữ hai số lẻ; VNĐ làm tròn.
   */
  function tienTT(vnd, q) {
    const ma = (q && q.currency_code) || 'VND';
    const x = Number(vnd) / tyGiaPhieu(q);
    if (!isFinite(x)) return '—';
    return (ma === 'VND'
      ? Math.round(x).toLocaleString('vi-VN')
      : x.toLocaleString('vi-VN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    ) + ' ' + kyHieu(ma);
  }

  /** Các chặng của một tuyến, theo thứ tự đi. */
  function changCuaTuyen(rt) {
    if (!rt) return [];
    let ds = rt.segments_geo;
    if (!Array.isArray(ds) || !ds.length) {
      try { ds = JSON.parse(rt.segments_json || '[]'); } catch (e) { ds = []; }
    }
    return Array.isArray(ds) ? ds : [];
  }

  function diemDauCuoi(rt) {
    const c = changCuaTuyen(rt);
    if (!c.length) return ['', ''];
    const dau = c[0].from_location || c[0].from || c[0].origin || '';
    const cuoi = c[c.length - 1].to_location || c[c.length - 1].to || c[c.length - 1].destination || '';
    return [dau, cuoi];
  }

  /* =========================================================================
     KHUNG
     ========================================================================= */

  function dungKhung() {
    const goc = el(GOC);
    if (!goc || goc.dataset.dung === '1') return !!goc;
    goc.dataset.dung = '1';
    goc.className = 'qtv2';
    goc.innerHTML = `
      <div class="qt-module">
        <div class="ribbon"><b>Báo giá cước → DO</b> Bỏ bước đơn hàng: báo giá được khách chấp
          nhận thì tách thẳng thành Lệnh giao hàng cho vận hành.</div>

        <div id="qtv2-list">
          <div class="hdr">
            <div>
              <div class="crumb">Kinh doanh</div>
              <h1>Báo giá cước</h1>
              <p>Báo giá theo tuyến và loại xe. Khách chấp nhận → tách thẳng thành Lệnh giao
                hàng (DO). Giá thành tính từ công thức ở Dữ liệu gốc.</p>
            </div>
            <div style="display:flex;gap:8px">
              <button type="button" class="ghost" id="qtv2-lam-moi">↻ Làm mới</button>
              <button type="button" class="ghost" id="qtv2-xuat">↓ Xuất Excel</button>
              <button type="button" class="primary" id="qtv2-moi">+ Báo giá</button>
            </div>
          </div>
          <div class="kpis" id="qtv2-kpis"></div>
          <section class="card">
            <div class="tabs" id="qtv2-tabs"></div>
            <div class="tools">
              <div class="search">⌕ <input id="qtv2-tim"
                placeholder="Tìm mã báo giá, khách, tuyến, loại xe"></div>
              <select id="qtv2-loc-khach"></select>
              <select id="qtv2-loc-tuyen"></select>
              <select id="qtv2-loc-nguoi"></select>
              <span class="cnt" id="qtv2-dem"></span>
            </div>
            <div class="table-wrap">
              <table>
                <thead><tr>
                  <th>Báo giá</th><th>Khách hàng</th><th>Tuyến · loại xe</th><th>Hàng</th>
                  <th class="r">Cước</th><th class="r">Biên</th><th>Hiệu lực</th>
                  <th>Trạng thái</th><th>Lệnh giao hàng</th>
                </tr></thead>
                <tbody id="qtv2-dong"></tbody>
              </table>
            </div>
            <div class="tfoot">
              <span id="qtv2-chan"></span>
              <span>Biên = (cước − giá thành theo công thức loại xe) / cước</span>
            </div>
          </section>
        </div>

        <div id="qtv2-detail" class="qt-hide"></div>
      </div>`;

    if (!el('qtv2-sbar')) {
      const sb = document.createElement('div');
      sb.id = 'qtv2-sbar';
      sb.className = 'qt-hide';
      document.body.appendChild(sb);
    }

    el('qtv2-lam-moi').addEventListener('click', () => napDanhSach(true));
    el('qtv2-moi').addEventListener('click', () => moPhieu(null));
    el('qtv2-xuat').addEventListener('click', xuatExcel);
    el('qtv2-tim').addEventListener('input', () => {
      clearTimeout(S._henTim);
      S._henTim = setTimeout(() => { S.loc.q = el('qtv2-tim').value.trim(); napDanhSach(); }, 320);
    });
    ['qtv2-loc-khach', 'qtv2-loc-tuyen', 'qtv2-loc-nguoi'].forEach(id => {
      el(id).addEventListener('change', () => {
        S.loc.customer_id = el('qtv2-loc-khach').value;
        S.loc.route_id = el('qtv2-loc-tuyen').value;
        S.loc.owner = el('qtv2-loc-nguoi').value;
        napDanhSach();
      });
    });
    return true;
  }

  /* =========================================================================
     DỮ LIỆU GỐC — nạp một lần, dùng cho cả bộ lọc và các ô chọn của phiếu
     ========================================================================= */

  async function napDuLieuGoc() {
    if (S.khach.length && S.tuyen.length && S.loaiXe.length) return;
    // `Promise.allSettled` chứ không `all`: bảng tỷ giá thiếu thì màn vẫn phải
    // mở được và báo giá bằng VNĐ vẫn làm được — chỉ mất phần đổi tiền.
    const ra = await Promise.allSettled([
      doc('/api/customers'), doc('/api/routes'), doc('/api/vehicle-types'),
      doc('/api/currencies'),
    ]);
    const mang = x => (x.status === 'fulfilled'
      ? (Array.isArray(x.value) ? x.value : (x.value && x.value.items) || []) : []);
    S.khach = mang(ra[0]);
    S.tuyen = mang(ra[1]);
    S.loaiXe = mang(ra[2]);
    S.tienTe = mang(ra[3]);
    const hong = ra.map((x, i) => x.status === 'rejected'
      ? ['khách hàng', 'tuyến đường', 'loại xe', 'tỷ giá'][i] : null).filter(Boolean);
    if (hong.length) thongBao('Không tải được dữ liệu gốc: ' + hong.join(', ') + '.', true);

    const oKhach = el('qtv2-loc-khach');
    if (oKhach) {
      oKhach.innerHTML = '<option value="">Khách: Tất cả</option>'
        + S.khach.map(k => `<option value="${esc(k.id)}">${esc(k.name || k.id)}</option>`).join('');
      el('qtv2-loc-tuyen').innerHTML = '<option value="">Tuyến: Tất cả</option>'
        + S.tuyen.map(r => `<option value="${esc(r.id)}">${esc(r.name || r.id)}</option>`).join('');
      const nguoi = Array.from(new Set(S.ds.map(x => x.created_by).filter(Boolean)));
      el('qtv2-loc-nguoi').innerHTML = '<option value="">Người tạo: Tất cả</option>'
        + nguoi.map(n => `<option value="${esc(n)}">${esc(n)}</option>`).join('');
    }
  }

  /* =========================================================================
     DANH SÁCH
     ========================================================================= */

  async function napDanhSach(noiKhiXong) {
    if (!dungKhung()) return;
    const than = el('qtv2-dong');
    if (than && !S.ds.length) {
      than.innerHTML = '<tr><td colspan="9" style="text-align:center;color:#7b8796">'
        + 'Đang tải danh sách báo giá…</td></tr>';
    }
    try {
      await napDuLieuGoc();
      const tv = new URLSearchParams({ status: trangThaiTheThe() });
      ['customer_id', 'route_id', 'owner', 'q'].forEach(k => {
        if (S.loc[k]) tv.set(k, S.loc[k]);
      });
      const goi = await doc('/api/quotations/board?' + tv.toString());
      S.ds = (goi && goi.items) || [];
      S.kpi = (goi && goi.kpis) || null;
      veKpi();
      veThe();
      veDong();
      if (noiKhiXong) thongBao(`Đã tải ${S.ds.length} báo giá.`);
    } catch (loi) {
      if (than) {
        than.innerHTML = `<tr><td colspan="9" style="text-align:center;color:#d32f2f">`
          + `Không tải được danh sách báo giá: ${esc(loi.message)}</td></tr>`;
      }
      thongBao('Không tải được danh sách báo giá: ' + loi.message, true);
    }
  }

  /**
   * Trạng thái gửi lên máy chủ theo thẻ đang chọn.
   *
   * Thẻ "Sắp hết hạn" là BỘ LỌC ĐỘNG (0 ≤ ngày còn lại ≤ 7), không phải một
   * trạng thái lưu trong cơ sở dữ liệu — spec ghi rõ điều đó, và máy chủ tính
   * nó lúc đọc nên không cần tiến trình nào chạy nền mỗi đêm.
   */
  function trangThaiTheThe() {
    if (S.locKpi === 'wait') return 'sent';
    if (S.locKpi === 'exp') return 'sap_het_han';
    if (S.locKpi === 'acc') return 'accepted';
    if (S.locKpi !== 'all') return 'all';
    return ({
      all: 'dang_mo', draft: 'draft', sent: 'sent', acc: 'accepted',
      exp: 'sap_het_han', rej: 'rejected',
    })[S.the] || 'all';
  }

  function veKpi() {
    const k = S.kpi || {};
    const nguong = phanTram(k.nguong_bien === undefined ? 0.15 : k.nguong_bien, 0);
    const o = [
      ['all', 'blue', 'Đang mở', k.dang_mo, `${S.ds.length} dòng đang hiện`],
      ['wait', 'amber', 'Chờ khách phản hồi', k.cho_khach_phan_hoi, 'đã gửi, chưa có trả lời'],
      ['exp', 'red', 'Hết hạn trong 7 ngày', k.het_han_trong_7_ngay, 'soát giá rồi gia hạn'],
      ['acc', 'green', 'Đã chấp nhận, chưa tách DO',
        k.da_chap_nhan_chua_tach, '≈ ' + tien(k.tien_da_chap_nhan) + ' VNĐ'],
      ['low', 'red', 'Biên dưới ngưỡng ' + nguong, k.bien_duoi_nguong, 'cần duyệt nội bộ'],
      ['rate', 'purple', 'Tỷ lệ chốt 30 ngày',
        k.ty_le_chot_30_ngay === null || k.ty_le_chot_30_ngay === undefined
          ? '—' : phanTram(k.ty_le_chot_30_ngay, 0),
        `${k.so_chot_30_ngay || 0} / ${k.so_co_ket_qua_30_ngay || 0}`],
    ];
    el('qtv2-kpis').innerHTML = o.map(x => `
      <div class="card kpi ${x[1]} ${S.locKpi === x[0] ? 'on' : ''}" data-f="${x[0]}">
        <span>${esc(x[2])}</span><b>${x[3] === null || x[3] === undefined ? '—' : x[3]}</b>
        <small>${esc(x[4])}</small></div>`).join('');
    el('qtv2-kpis').querySelectorAll('.kpi').forEach(n => n.addEventListener('click', () => {
      S.locKpi = n.dataset.f === S.locKpi ? 'all' : n.dataset.f;
      S.the = 'all';
      napDanhSach();
    }));
  }

  function veThe() {
    const k = S.kpi || {};
    const o = [
      ['all', 'Tất cả', k.dang_mo, ''],
      ['draft', 'Nháp', null, ''],
      ['sent', 'Đã gửi · chờ khách', k.cho_khach_phan_hoi, 'warn'],
      ['acc', 'Đã chấp nhận', k.da_chap_nhan_chua_tach, ''],
      ['exp', 'Sắp hết hạn', k.het_han_trong_7_ngay, 'red'],
      ['rej', 'Từ chối / hết hạn', null, ''],
    ];
    el('qtv2-tabs').innerHTML = o.map(x => `
      <button type="button" class="tb ${S.the === x[0] && S.locKpi === 'all' ? 'on' : ''} ${x[3]}"
        data-s="${x[0]}">${esc(x[1])}${x[2] === null || x[2] === undefined ? ''
        : `<span class="n">${x[2]}</span>`}</button>`).join('');
    el('qtv2-tabs').querySelectorAll('.tb').forEach(n => n.addEventListener('click', () => {
      S.the = n.dataset.s;
      S.locKpi = 'all';
      napDanhSach();
    }));
  }

  function veDong() {
    const than = el('qtv2-dong');
    let ds = S.ds;
    // Bộ lọc "biên dưới ngưỡng" lọc ở máy khách vì máy chủ trả cả danh sách
    // đang mở kèm biên đã tính — lọc lại ở đây không sinh thêm lượt gọi.
    if (S.locKpi === 'low') {
      const nguong = (S.kpi && S.kpi.nguong_bien) || 0.15;
      ds = ds.filter(x => x.bien !== null && x.bien !== undefined && x.bien < nguong);
    }
    if (!ds.length) {
      than.innerHTML = '<tr><td colspan="9" style="text-align:center;color:#7b8796;padding:28px">'
        + 'Không có báo giá nào khớp bộ lọc đang chọn.</td></tr>';
      el('qtv2-dem').textContent = '0 báo giá';
      el('qtv2-chan').textContent = '';
      return;
    }
    than.innerHTML = ds.map(x => {
      const rt = tuyenTheoMa(x.route_id);
      const km = kmTuyen(rt);
      const tt = TRANG_THAI[x.canonical_status] || [x.canonical_status, ''];
      const con = x.con_lai_ngay;
      const hieuLuc = !x.valid_to ? 'Chưa khai hiệu lực'
        : con === null || con === undefined ? '—'
          : con < 0 ? 'Hết hạn' : 'Còn ' + con + ' ngày';
      const mauHl = con === null || con === undefined || con < 0 ? ''
        : con <= 3 ? 'r' : con <= 7 ? 'a' : '';
      return `<tr data-id="${esc(x.id)}">
        <td><span class="id">${esc(x.quote_no || x.id)}</span>
          <span class="sub">v${x.version || 1} · ${esc(x.created_by || '—')}</span></td>
        <td><span class="cus">${esc(tenKhach(x.customer_id))}</span></td>
        <td>${esc((rt && (rt.name || rt.id)) || x.route_id || '—')}
          <span class="sub">${esc(tenLoaiXe(x.vehicle_type_id))}${km > 0 ? ' · ' + so(km) + ' km' : ''}</span></td>
        <td>${x.so_do_du_kien
        ? x.so_do_du_kien + ' đơn vị · ' + so(Number(x.weight_kg || 0) / 1000) + ' tấn'
        // "0 đơn vị" đọc ra là "báo giá này chở không có gì", trong khi sự thật
        // là bảng hàng hoá chưa được kê. Hai điều đó khác nhau.
        : '<span style="color:#b45309">chưa kê hàng</span> · '
        + so(Number(x.weight_kg || 0) / 1000) + ' tấn'}
          <span class="sub">${esc(x.cargo_type || '—')} · ${x.trips_per_month || 0} chuyến/tháng</span></td>
        <td class="r"><span class="money">${tienTT(x.selling_price, x)}</span>
          <span class="sub">giá thành ${tienTT(x.total_cost, x)}</span></td>
        <td class="r"><span class="mg ${mauBien(x.bien)}">${phanTram(x.bien)}${
        x.bien !== null && x.bien !== undefined && x.bien < 0.15 ? ' ⚠' : ''}</span></td>
        <td><span class="valid ${mauHl}">${esc(hieuLuc)}</span>
          <span class="sub">${esc(x.valid_to || '—')}</span></td>
        <td><span class="tag ${tt[1]}">${esc(tt[0])}</span></td>
        <td>${x.so_do
        ? `<span class="so">${x.so_do_xong || 0}/${x.so_do} DO xong →</span>`
        : x.canonical_status === 'accepted'
          // "Đã chấp nhận" mà KHÔNG có DO nào là một BẤT THƯỜNG kể từ 09/09:
          // ghi nhận chấp nhận và sinh DO nay là cùng một giao dịch. Còn thấy
          // dòng này thì đó là bản ghi cũ, và nói "+ Tách N DO" là mời người
          // dùng đi tìm một cái nút không còn nữa.
          ? `<span class="so warn">⚠ chưa sinh DO (dữ liệu cũ)</span>`
          : '<span class="so none">—</span>'}</td></tr>`;
    }).join('');
    than.querySelectorAll('tr[data-id]').forEach(n => n.addEventListener('click',
      () => moPhieu(n.dataset.id)));
    el('qtv2-dem').textContent = ds.length + ' báo giá';
    el('qtv2-chan').textContent = `${ds.length} báo giá · tổng cước `
      + tien(ds.reduce((s, x) => s + Number(x.selling_price || 0), 0)) + ' VNĐ';
  }

  function xuatExcel() {
    // Xuất từ ĐÚNG những dòng đang hiện, không gọi lại máy chủ: nếu gọi lại thì
    // tệp tải về có thể khác thứ người dùng đang xem trên màn hình.
    const ds = S.ds;
    if (!ds.length) { thongBao('Không có dòng nào để xuất.', true); return; }
    const cot = ['Mã báo giá', 'Khách hàng', 'Tuyến', 'Loại xe', 'Tải trọng kg', 'Giá thành',
      'Cước', 'Biên %', 'Hiệu lực đến', 'Còn lại ngày', 'Trạng thái', 'DO dự kiến', 'DO đã tách'];
    const dong = ds.map(x => [
      x.quote_no || x.id, tenKhach(x.customer_id),
      (tuyenTheoMa(x.route_id) || {}).name || x.route_id || '',
      tenLoaiXe(x.vehicle_type_id), x.weight_kg || 0, x.total_cost || 0, x.selling_price || 0,
      x.bien === null || x.bien === undefined ? '' : (x.bien * 100).toFixed(1),
      x.valid_to || '', x.con_lai_ngay === null ? '' : x.con_lai_ngay,
      (TRANG_THAI[x.canonical_status] || [x.canonical_status])[0],
      x.so_do_du_kien || 0, x.so_do || 0,
    ]);
    const oNhay = v => {
      const s = String(v === null || v === undefined ? '' : v);
      return /[";\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
    };
    // BOM và dấu chấm phẩy: Excel bản tiếng Việt đọc CSV theo dấu chấm phẩy, và
    // không có BOM thì mọi chữ có dấu hiện thành ký tự lạ.
    const csv = '\uFEFF' + [cot, ...dong].map(r => r.map(oNhay).join(';')).join('\r\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    a.download = `bao-gia-cuoc-${ngayHomNayCong(0)}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    thongBao(`Đã xuất ${ds.length} báo giá ra tệp CSV mở được bằng Excel.`);
  }

  /* =========================================================================
     PHIẾU BÁO GIÁ — trang chi tiết, không phải hộp thoại
     ========================================================================= */

  async function moPhieu(qid) {
    dungKhung();
    await napDuLieuGoc();
    S.dongTach = [];
    S.xemTruoc = null;
    if (qid) {
      try {
        S.q = await doc('/api/quotations/' + encodeURIComponent(qid) + '/detail');
      } catch (loi) {
        thongBao('Không mở được báo giá ' + qid + ': ' + loi.message, true);
        return;
      }
    } else {
      S.q = phieuTrong();
    }
    el('qtv2-list').classList.add('qt-hide');
    el('qtv2-detail').classList.remove('qt-hide');
    el('qtv2-sbar').classList.remove('qt-hide');
    vePhieu();
    const cuon = document.querySelector('.content-body') || window;
    if (cuon.scrollTo) cuon.scrollTo(0, 0);
    tinhLaiGia();
  }

  function dongPhieu() {
    S.q = null;
    S.xemTruoc = null;
    S.dongTach = [];
    el('qtv2-detail').classList.add('qt-hide');
    el('qtv2-sbar').classList.add('qt-hide');
    el('qtv2-list').classList.remove('qt-hide');
    napDanhSach();
  }

  function phieuTrong() {
    return {
      id: '', quote_no: '', canonical_status: 'draft', version: 1,
      customer_id: (S.khach[0] && S.khach[0].id) || '', route_id: '', vehicle_type_id: '',
      origin: '', destination: '',
      pickup_window_start: '', pickup_window_end: '',
      delivery_window_start: '', delivery_window_end: '',
      weight_kg: 0, volume_m3: 0, pallet_count: 0, cargo_value: 0,
      cargo_type: LOAI_HANG[0], temperature_requirement: '',
      stacking: XEP_CHONG[0], sealing: NIEM_PHONG[0], recipient_contact: '',
      valid_to: ngayHomNayCong(30),
      price_basis: 'per_trip', unit_price: 0, min_qty_per_trip: 0,
      selling_price: 0, total_cost: 0, bien: null,
      currency_code: 'VND', fx_rate: 1, payment_terms: DIEU_KHOAN[0],
      waiting_surcharge: 0, sales_rep: nguoiDangDung(), trips_per_month: 0,
      competitor_price: 0, discount_percent: 0,
      notes_customer: '', notes_ops: '', notes_internal: '',
      items: [{ line_no: 1, name: '', quantity: 1, uom: "40'", note: '' }],
      attachments: [], versions: [], delivery_orders: [],
      so_do: 0, so_do_xong: 0, so_do_du_kien: 1, con_lai_ngay: 30,
    };
  }

  function nguoiDangDung() {
    return (window.EPL_PRINCIPAL || window.currentUser || '') || 'sales';
  }

  const laNhap = () => S.q && ['draft', 'pending_approval'].includes(S.q.canonical_status);
  const suaDuoc = () => S.q && ['draft', 'pending_approval', 'sent', 'approved']
    .includes(S.q.canonical_status);

  /* ------------------------------------------------------------- vẽ cả phiếu -- */

  /** Chuyển tab của phiếu; nhớ vào S để vẽ lại (sau lưu) không nhảy tab. */
  function chonTabPhieu(so) {
    S.tabPhieu = so === 2 ? 2 : 1;
    document.querySelectorAll('#qtv2-phieu-tabs button[data-tab]').forEach(b =>
      b.classList.toggle('on', Number(b.dataset.tab) === S.tabPhieu));
    document.querySelectorAll('.qtv2-tab[data-tab]').forEach(k => {
      k.hidden = Number(k.dataset.tab) !== S.tabPhieu;
    });
  }

  function vePhieu() {
    const q = S.q;
    if (!q) return;
    if (!S.tabPhieu) S.tabPhieu = 1;
    const tt = TRANG_THAI[q.canonical_status] || [q.canonical_status, ''];
    const rt = tuyenTheoMa(q.route_id);
    el('qtv2-detail').innerHTML = `
      <div class="hdr">
        <div>
          <div class="crumb"><a id="qtv2-quay-lai">← Báo giá cước</a></div>
          <h1>${esc(q.quote_no || q.id || 'Báo giá mới')}</h1>
          <p>${esc(tenKhach(q.customer_id))}${rt ? ' · ' + esc(rt.name || rt.id) : ''} · ${esc(tt[0])}</p>
        </div>
        <div style="display:flex;gap:8px">
          ${q.id ? '<button type="button" class="ghost" id="qtv2-nhan-ban">Nhân bản</button>' : ''}
          ${q.id ? '<button type="button" class="ghost" id="qtv2-lich-su">Lịch sử giá</button>' : ''}
        </div>
      </div>
      <div class="dt">
        <section class="card">
          <!-- Hai tab: phieu tam muc don mot cot thi dai qua mot man, muc 7–8
               (chung tu, ghi chu) la viec lam SAU khi da co gia, nen tach ra. -->
          <!-- id RIÊNG: màn danh sách đã có #qtv2-tabs (thẻ lọc trạng thái); trùng id
               thì el() bám vào thẻ đó và nút ở đây bấm không phản ứng. -->
          <div class="qtv2-tabs" role="tablist" id="qtv2-phieu-tabs">
            <button type="button" role="tab" data-tab="1" class="${S.tabPhieu === 2 ? '' : 'on'}">Báo giá &amp; lệnh giao hàng</button>
            <button type="button" role="tab" data-tab="2" class="${S.tabPhieu === 2 ? 'on' : ''}">Chứng từ &amp; ghi chú</button>
          </div>
          <div class="qtv2-tab" data-tab="1" ${S.tabPhieu === 2 ? 'hidden' : ''}>
          ${mucChung(q)}
          ${mucTuyen(q, rt)}
          ${mucHangHoa(q, rt)}
          ${mucLoaiXe(q)}
          ${mucGia(q)}
          ${mucTachDo(q)}
          </div>
          <div class="qtv2-tab" data-tab="2" ${S.tabPhieu === 2 ? '' : 'hidden'}>
          ${mucChungTu(q)}
          ${mucGhiChu(q)}
          </div>
        </section>
        <aside class="card rail">
          <div class="rl">
            <h4>Kết quả</h4>
            <div class="big cost"><span>Giá thành / chuyến</span><b id="qtv2-r-cost">—</b></div>
            <div class="big rev"><span>Cước báo khách</span><b id="qtv2-r-rev">—</b></div>
            <div class="big pf"><span>Lợi nhuận</span><b id="qtv2-r-pf">—</b></div>
            <div class="bar"><i id="qtv2-r-bar" style="width:0"></i>
              <span class="t" id="qtv2-r-nguong" style="left:30%" title="ngưỡng biên"></span></div>
            <div class="hint2" id="qtv2-r-nguong-chu"></div>
            <div class="hint2" id="qtv2-r-thang" style="margin-top:6px"></div>
          </div>
          <div class="rl"><h4>Kiểm tra trước khi gửi</h4><div id="qtv2-r-chk"></div></div>
          <div class="rl" id="qtv2-r-lichsu"><h4>Giá đã báo cho khách này</h4>
            <div class="hint2">Đang tải…</div></div>
          <div class="rl" id="qtv2-r-ver"></div>
        </aside>
      </div>`;

    el('qtv2-quay-lai').addEventListener('click', dongPhieu);
    el('qtv2-phieu-tabs').addEventListener('click', ev => {
      const nut = ev.target.closest('button[data-tab]');
      if (!nut) return;
      chonTabPhieu(Number(nut.dataset.tab));
    });
    if (el('qtv2-nhan-ban')) el('qtv2-nhan-ban').addEventListener('click', nhanBan);
    if (el('qtv2-lich-su')) el('qtv2-lich-su').addEventListener('click', () => {
      const n = el('qtv2-r-ver');
      cuonToi(n);
    });
    noiSuKien();
    veHangHoa();
    veChungTu();
    veTachDo();
    vePhienBan();
    napGiaDaBao();
  }

  /* ---------------------------------------------- 1. Thông tin chung -------- */

  function mucChung(q) {
    const dsKhach = S.khach.map(k =>
      `<option value="${esc(k.id)}" ${k.id === q.customer_id ? 'selected' : ''}>${esc(k.name || k.id)}</option>`).join('');
    const dsTuyen = S.tuyen.map(r =>
      `<option value="${esc(r.id)}" ${r.id === q.route_id ? 'selected' : ''}>${esc(r.name || r.id)}${
        r.distance_km ? ' · ' + so(r.distance_km) + ' km' : ''}</option>`).join('');
    const dsTien = ['VND'].concat(S.tienTe.map(t => String(t.code || t.id).toUpperCase())
      .filter(c => c && c !== 'VND'));
    return `
      <div class="sec">
        <h3>1. Thông tin chung</h3>
        <div class="g3">
          <div class="f"><label>Mã báo giá <span class="hint">cấp khi gửi khách</span></label>
            <input id="qtv2-code" value="${esc(q.quote_no || '')}"
              placeholder="${q.id ? esc(q.id) : 'Tự sinh khi gửi khách (QT-2026-…)'}" readonly></div>
          <div class="f"><label>Khách hàng <span class="req">*</span></label>
            <select id="qtv2-khach" ${suaDuoc() ? '' : 'disabled'}>${dsKhach}</select></div>
          <div class="f"><label>Nhân viên kinh doanh</label>
            <input id="qtv2-sales" value="${esc(q.sales_rep || nguoiDangDung())}" readonly></div>
        </div>
        <div class="g3" style="margin-top:10px">
          <div class="f"><label>Tuyến đường <span class="req">*</span>
              <span class="hint">từ Dữ liệu gốc</span></label>
            <select id="qtv2-tuyen" ${suaDuoc() ? '' : 'disabled'}>
              <option value="">— Chọn tuyến —</option>${dsTuyen}</select>
            <span class="hint2" id="qtv2-tuyen-chu">Chọn tuyến để có số km, chặng và BOT.</span></div>
          <div class="f"><label>Tiền tệ báo giá <span class="hint">lưu VNĐ</span></label>
            <select id="qtv2-tien" ${suaDuoc() ? '' : 'disabled'}>${dsTien.map(c =>
      `<option value="${esc(c)}" ${c === (q.currency_code || 'VND') ? 'selected' : ''}>${esc(c)}${
        c === 'VND' ? ' · Việt Nam đồng' : ' · 1 = ' + tien(tyGia(c)) + ' VNĐ'}</option>`).join('')}</select></div>
          <div class="f"><label>Hiệu lực đến <span class="req">*</span></label>
            <input type="date" id="qtv2-valid" value="${esc((q.valid_to || '').slice(0, 10))}"
              ${suaDuoc() ? '' : 'disabled'}></div>
        </div>
      </div>`;
  }

  /* ---------------------------------------------- 2. Tuyến và chặng --------- */

  function mucTuyen(q, rt) {
    return `
      <div class="sec">
        <h3>2. Tuyến và chặng <span class="tag" id="qtv2-rtcode">${
      rt ? esc(rt.id) : 'chưa chọn'}</span></h3>
        <p>Lấy từ Dữ liệu gốc → Tuyến đường. Sửa tuyến ở đó thì mọi báo giá dùng tuyến này đổi
          theo — nên ở đây chỉ xem.</p>
        <div class="chain" id="qtv2-chain"></div>
      </div>`;
  }

  function veChang() {
    const rt = tuyenTheoMa(S.q && S.q.route_id);
    const o = el('qtv2-chain');
    if (!o) return;
    const chang = changCuaTuyen(rt);
    if (!rt || !chang.length) {
      o.innerHTML = '<div style="padding:6px 10px;color:#7b8796;font-size:12.5px">'
        + (rt ? 'Tuyến này chưa khai chặng nào ở Dữ liệu gốc → Tuyến đường.'
          : 'Chọn tuyến ở trên để xem chặng.') + '</div>';
      return;
    }
    // Mốc = điểm đi + điểm đến của từng chặng, bỏ trùng ở chỗ nối.
    const moc = [];
    chang.forEach((c, i) => {
      const tu = c.from_location || c.from || '';
      const den = c.to_location || c.to || '';
      // `dist_km` là tên thật trong `segments_json`. Đọc sai tên thì mọi chặng
      // hiện "chặng 1 / chặng 2" thay vì số km, mà số km mới là thứ người xem
      // cần để biết chặng nào dài.
      const km = Number(c.dist_km || c.distance_km || 0);
      if (!moc.length) moc.push([tu, 'Điểm đi']);
      moc.push([den, km > 0 ? so(km) + ' km' : 'chặng ' + (i + 1)]);
    });
    o.innerHTML = moc.map((m, k) => `
      <div class="cp ${k === 0 ? 'a' : k === moc.length - 1 ? 'z' : ''}">
        <span class="d">${k + 1}</span><b>${esc(m[0] || '—')}</b><span>${esc(m[1])}</span></div>`).join('');
  }

  function capNhatChuTuyen() {
    const rt = tuyenTheoMa(S.q && S.q.route_id);
    const chu = el('qtv2-tuyen-chu');
    const ma = el('qtv2-rtcode');
    if (ma) { ma.textContent = rt ? rt.id : 'chưa chọn'; }
    if (!chu) return;
    if (!rt) { chu.textContent = 'Chọn tuyến để có số km, chặng và BOT.'; return; }
    const km = kmTuyen(rt);
    const nChang = changCuaTuyen(rt).length;
    const bot = Number(rt.bot_fee || 0);
    chu.textContent = `${km > 0 ? so(km) + ' km' : 'chưa khai km'} · ${nChang} chặng · `
      + (bot > 0 ? 'BOT ước ' + tien(bot) + ' VNĐ' : 'chưa khai phí BOT cho tuyến này');
    const [dau, cuoi] = diemDauCuoi(rt);
    if (el('qtv2-from')) el('qtv2-from').value = dau || '';
    if (el('qtv2-to')) el('qtv2-to').value = cuoi || '';
    veChang();
  }

  /* ---------------------------------------------- 3. Hàng hoá và thời gian -- */

  function mucHangHoa(q, rt) {
    const [dau, cuoi] = diemDauCuoi(rt);
    const oChon = (id, ds, gt) => `<select id="${id}" ${suaDuoc() ? '' : 'disabled'}>${
      ds.map(v => `<option ${v === gt ? 'selected' : ''}>${esc(v)}</option>`).join('')}</select>`;
    return `
      <div class="sec">
        <h3>3. Hàng hoá và thời gian dự kiến</h3>
        <p>Điểm đi/đến lấy theo tuyến. Kê từng loại hàng — mình là đơn vị vận chuyển nên chỉ
          tính cước, không tính tiền hàng.</p>
        <div class="g4">
          <div class="f"><label>Điểm đi</label>
            <input id="qtv2-from" value="${esc(q.origin || dau || '')}" placeholder="theo tuyến" readonly></div>
          <div class="f"><label>Điểm đến</label>
            <input id="qtv2-to" value="${esc(q.destination || cuoi || '')}" placeholder="theo tuyến" readonly></div>
          <div class="f"><label>Lấy hàng · từ</label>
            <input type="datetime-local" id="qtv2-p1"
              value="${esc(chuanDatetimeLocal(q.pickup_window_start))}" ${suaDuoc() ? '' : 'disabled'}></div>
          <div class="f"><label>Lấy hàng · đến</label>
            <input type="datetime-local" id="qtv2-p2"
              value="${esc(chuanDatetimeLocal(q.pickup_window_end))}" ${suaDuoc() ? '' : 'disabled'}></div>
        </div>
        <div class="g4" style="margin-top:10px">
          <div class="f"><label>Giao hàng · từ</label>
            <input type="datetime-local" id="qtv2-d1"
              value="${esc(chuanDatetimeLocal(q.delivery_window_start))}" ${suaDuoc() ? '' : 'disabled'}></div>
          <div class="f"><label>Giao hàng · đến</label>
            <input type="datetime-local" id="qtv2-d2"
              value="${esc(chuanDatetimeLocal(q.delivery_window_end))}" ${suaDuoc() ? '' : 'disabled'}></div>
          <div class="f"><label>Số chuyến / tháng</label>
            <input id="qtv2-trips" inputmode="numeric" value="${q.trips_per_month || ''}"
              placeholder="24" ${suaDuoc() ? '' : 'disabled'}></div>
          <div class="f"><label>Người nhận tại điểm giao</label>
            <input id="qtv2-recip" value="${esc(q.recipient_contact || '')}"
              placeholder="Cổng B · Nguyễn T. · 090…" ${suaDuoc() ? '' : 'disabled'}></div>
        </div>

        <div class="lbl" style="margin-top:14px">Hàng hoá vận chuyển
          <em>mỗi dòng một loại hàng · số lượng theo ĐVT</em></div>
        <div class="it" id="qtv2-items"></div>
        <div class="itsum" id="qtv2-itsum"></div>

        <div class="lbl" style="margin-top:14px">Quy cách vận chuyển</div>
        <div class="g4">
          <div class="f"><label>Loại hàng</label>${oChon('qtv2-kind', LOAI_HANG, q.cargo_type)}</div>
          <div class="f"><label>Nhiệt độ yêu cầu</label>
            <input id="qtv2-temp" value="${esc(q.temperature_requirement || '')}"
              placeholder="—" ${suaDuoc() ? '' : 'disabled'}></div>
          <div class="f"><label>Xếp chồng</label>${oChon('qtv2-stack', XEP_CHONG, q.stacking)}</div>
          <div class="f"><label>Niêm phong</label>${oChon('qtv2-seal', NIEM_PHONG, q.sealing)}</div>
        </div>
        <div class="g4" style="margin-top:10px">
          <div class="f"><label>Tổng tải trọng (kg) <span class="req">*</span>
              <span class="hint">dùng để gợi ý xe</span></label>
            <input id="qtv2-kg" inputmode="numeric" value="${q.weight_kg ? tien(q.weight_kg) : ''}"
              placeholder="12.000" ${suaDuoc() ? '' : 'disabled'}></div>
          <div class="f"><label>Tổng thể tích (m³)</label>
            <input id="qtv2-m3" inputmode="decimal" value="${q.volume_m3 || ''}"
              placeholder="24" ${suaDuoc() ? '' : 'disabled'}></div>
          <div class="f"><label>Số pallet</label>
            <input id="qtv2-pal" inputmode="numeric" value="${q.pallet_count || ''}"
              placeholder="12" ${suaDuoc() ? '' : 'disabled'}></div>
          <div class="f"><label>Giá trị hàng (VNĐ)
              <span class="hint">chỉ để tính bảo hiểm</span></label>
            <input id="qtv2-val" inputmode="numeric" value="${q.cargo_value ? tien(q.cargo_value) : ''}"
              placeholder="800.000.000" ${suaDuoc() ? '' : 'disabled'}></div>
        </div>
      </div>`;
  }

  const soLuongHang = () => (S.q && S.q.items || [])
    .reduce((a, i) => a + (parseInt(i.quantity, 10) || 0), 0);

  function veHangHoa() {
    const q = S.q;
    const o = el('qtv2-items');
    if (!o || !q) return;
    if (!q.items || !q.items.length) {
      q.items = [{ line_no: 1, name: '', quantity: 1, uom: "40'", note: '' }];
    }
    const khoa = suaDuoc() ? '' : 'disabled';
    o.innerHTML = `<div class="r"><span>Tên hàng hoá</span><span>Số lượng</span><span>ĐVT</span>
        <span>Ghi chú</span><span></span></div>`
      + q.items.map((it, k) => `<div class="r">
          <input value="${esc(it.name || '')}" data-k="${k}" data-f="name"
            placeholder="Ví dụ: linh kiện motor" ${khoa}>
          <input value="${it.quantity || 1}" data-k="${k}" data-f="quantity" inputmode="numeric" ${khoa}>
          <select data-k="${k}" data-f="uom" ${khoa}>${DVT_HANG.map(u =>
        `<option ${it.uom === u ? 'selected' : ''}>${esc(u)}</option>`).join('')}</select>
          <input value="${esc(it.note || '')}" data-k="${k}" data-f="note"
            placeholder="seal, nhiệt độ…" ${khoa}>
          <button type="button" class="x" data-k="${k}" title="Xoá dòng" ${khoa}>×</button>
        </div>`).join('')
      + (suaDuoc() ? '<button type="button" class="add" id="qtv2-them-hang">+ Thêm dòng hàng hoá</button>' : '');

    const n = soLuongHang();
    const dvt = (q.items[0] && q.items[0].uom) || '';
    el('qtv2-itsum').innerHTML = `<span>Tổng <b>${n}</b> ${
      esc(["40'", "20'"].includes(dvt) ? 'cont' : 'đơn vị')}</span>`
      + `<span>→ gợi ý <b>${n} DO</b></span>`
      + `<span>Cước tính theo <b>${esc((DON_VI_CUOC.find(x => x[0] === (q.price_basis || 'per_trip')) || [])[2] || 'chuyến')}</b>, không theo giá trị hàng</span>`;

    o.querySelectorAll('input,select').forEach(x => x.addEventListener('change', () => {
      const k = +x.dataset.k, f = x.dataset.f;
      q.items[k][f] = f === 'quantity'
        ? Math.max(1, parseInt(String(x.value).replace(/\D/g, ''), 10) || 1)
        : x.value;
      S.dongTach = [];
      veHangHoa();
      veTachDo();
      veThanhDay();
    }));
    o.querySelectorAll('.x').forEach(b => b.addEventListener('click', () => {
      if (q.items.length < 2) {
        thongBao('Bảng hàng hoá phải còn tối thiểu một dòng.', true);
        return;
      }
      q.items.splice(+b.dataset.k, 1);
      q.items.forEach((it, i) => { it.line_no = i + 1; });
      S.dongTach = [];
      veHangHoa();
      veTachDo();
      veThanhDay();
    }));
    if (el('qtv2-them-hang')) {
      el('qtv2-them-hang').addEventListener('click', () => {
        q.items.push({ line_no: q.items.length + 1, name: '', quantity: 1, uom: dvt || "40'", note: '' });
        S.dongTach = [];
        veHangHoa();
        veTachDo();
        veThanhDay();
      });
    }
  }

  /* ---------------------------------------------- 4. Loại xe ---------------- */

  function mucLoaiXe(q) {
    return `
      <div class="sec">
        <h3>4. Loại xe <span class="tag t-blue" id="qtv2-vhint">nhập tải trọng để gợi ý</span></h3>
        <p>Quyết định công thức giá thành nào được áp. Xe không đủ tải bị chặn.</p>
        <div class="vsug" id="qtv2-vsug"></div>
      </div>`;
  }

  /**
   * Vì sao loại xe này không chở được — nói ĐÚNG CHIỀU vượt, không nói chung.
   *
   * Máy chủ chấm `do_vua_tai` theo cả ba chiều (tải trọng, thể tích, số
   * pallet), nhưng gói trả về chỉ có kết luận chứ không có lý do. Nói "không đủ
   * tải" cho một lô hàng nhẹ mà khối lớn là nói sai: người bán đổi sang xe nặng
   * hơn rồi vẫn vướng, vì cái vượt thực sự là thể tích.
   *
   * Dùng ĐÚNG bộ đánh giá mà máy chủ dùng (`WorkflowUIUtils.evaluateVehicleCapacity`
   * — cùng ba chiều, cùng hai mã lý do với `vehicle_recommendation_service`), nên
   * hai bên không thể nói hai câu khác nhau.
   */
  function lyDoKhongDu(maLoaiXe) {
    const CHIEU = { weight: 'tải trọng', volume: 'thể tích', pallet: 'số pallet' };
    const v = (S.loaiXe || []).find(x => x.id === maLoaiXe);
    const danhGia = window.WorkflowUIUtils && window.WorkflowUIUtils.evaluateVehicleCapacity;
    if (!v || !danhGia) return 'năng lực cho lô hàng này';
    const ket = danhGia({
      max_weight: v.max_weight,
      volume_capacity_m3: v.volume_capacity_m3,
      pallet_capacity: v.pallet_capacity,
    }, {
      weight_kg: Number(S.q.weight_kg || 0),
      volume_m3: Number(S.q.volume_m3 || 0),
      pallet_count: Number(S.q.pallet_count || 0),
    });
    if (!ket.reasons.length) return 'năng lực cho lô hàng này';
    return ket.reasons.map(r => `${CHIEU[r.dimension] || r.dimension} `
      + `(${so(r.required)}/${so(r.capacity)} ${r.unit})`).join(' và ');
  }

  function veLoaiXe() {
    const o = el('qtv2-vsug');
    if (!o || !S.q) return;
    const kg = Number(S.q.weight_kg || 0);
    const hint = el('qtv2-vhint');
    if (hint) hint.textContent = kg > 0 ? `hàng ${so(kg / 1000)} tấn` : 'nhập tải trọng để gợi ý';

    // Danh sách loại xe kèm ĐỘ VỪA TẢI do MÁY CHỦ chấm, không tự chấm ở đây:
    // sức tải và việc loại xe đã có công thức chưa đều là dữ liệu gốc.
    const ds = (S.xemTruoc && S.xemTruoc.cac_loai_xe) || S.loaiXe.map(v => ({
      id: v.id, ten: v.name, suc_tai_kg: v.max_weight, the_tich_m3: v.volume_capacity_m3,
      do_vua_tai: 'chua_biet', co_cong_thuc: true,
    }));
    o.innerHTML = ds.map(v => {
      const [nhan, mau] = DO_VUA_TAI[v.do_vua_tai] || DO_VUA_TAI.chua_biet;
      const hong = v.do_vua_tai === 'khong_du_tai';
      return `<div class="vc ${S.q.vehicle_type_id === v.id ? 'on' : ''} ${hong ? 'bad' : ''}"
          data-v="${esc(v.id)}" data-hong="${hong ? '1' : ''}">
          <b>${esc(v.ten || v.id)}</b>
          <span>Tải ${so(Number(v.suc_tai_kg || 0) / 1000)} tấn${
        v.the_tich_m3 ? ' · ' + so(v.the_tich_m3) + ' m³' : ''}${
        v.so_pallet ? ' · ' + v.so_pallet + ' pallet' : ''}</span>
          <span>${v.co_cong_thuc
        // Hai con số này cho biết vì sao hai loại xe cùng chở được 24 tấn lại
        // ra hai giá thành khác nhau. Không có chúng thì người bán chọn xe chỉ
        // theo sức tải.
        ? [Number(v.dau_moi_km) > 0 ? 'Dầu ' + tien(v.dau_moi_km) + ' VNĐ/km' : '',
          Number(v.khau_hao_moi_km) > 0 ? 'khấu hao ' + tien(v.khau_hao_moi_km) + ' VNĐ/km' : '',
          Number(v.phu_cap_chuyen) > 0 ? 'phụ cấp ' + tien(v.phu_cap_chuyen) + ' VNĐ' : '']
          .filter(Boolean).join(' · ') || 'Đã có công thức giá thành'
        : '⚠ chưa cấu hình công thức giá thành'}</span>
          <span class="fit ${mau}">${esc(nhan)}</span></div>`;
    }).join('');

    o.querySelectorAll('.vc').forEach(n => n.addEventListener('click', () => {
      if (!suaDuoc()) return;
      if (n.dataset.hong) {
        thongBao(`Loại xe này không đủ ${lyDoKhongDu(n.dataset.v)} — chọn loại xe lớn hơn `
          + 'hoặc chia thành nhiều chuyến.', true);
        return;
      }
      S.q.vehicle_type_id = n.dataset.v;
      veLoaiXe();
      tinhLaiGia();
    }));
  }

  /* ---------------------------------------------- 5. Cước và giá thành ------ */

  function mucGia(q) {
    const dv = q.price_basis || 'per_trip';
    const theoSoLuong = ['per_tonne', 'per_m3', 'per_kg'].includes(dv);
    return `
      <div class="sec">
        <h3>5. Cước và giá thành <span class="tag" id="qtv2-fsrc">công thức Dữ liệu gốc</span></h3>
        <p id="qtv2-fdesc">Tự tính khi đã có tuyến (km) và loại xe (công thức). Máy chủ tính,
          màn hình không tự nhân — công thức chỉ có một chỗ để sửa.</p>
        <div id="qtv2-nocalc" class="warn amber">⚠
          <div><b>Chưa tính được cước</b><ul id="qtv2-missing"></ul></div></div>
        <div id="qtv2-calc" class="qt-hide">
          <div class="ct" id="qtv2-ct"></div>
          <div class="g3" style="margin-top:10px">
            <div class="f"><label>Đơn vị tính cước <span class="req">*</span>
                <span class="hint">theo cách khách mua</span></label>
              <select id="qtv2-basis" ${suaDuoc() ? '' : 'disabled'}>${DON_VI_CUOC.map(d =>
      `<option value="${d[0]}" ${d[0] === dv ? 'selected' : ''}>${esc(d[1])}</option>`).join('')}</select></div>
            <div class="f"><label>Đơn giá cước báo khách <span class="req">*</span>
                <span class="hint" id="qtv2-price-unit"></span></label>
              <div class="sugs" id="qtv2-sugs"></div>
              <span class="edit"><input id="qtv2-price"
                value="${q.unit_price ? tien(q.unit_price / (tyGia(q.currency_code) || 1)) : ''}"
                ${suaDuoc() ? '' : 'disabled'}> <span id="qtv2-cursym">${esc(kyHieu(q.currency_code))}</span></span></div>
            <div class="f ${theoSoLuong ? '' : 'qt-hide'}" id="qtv2-min-wrap">
              <label>Số lượng tối thiểu / chuyến
                <span class="hint">chặn xe chạy thiếu tải</span></label>
              <input id="qtv2-minqty" inputmode="decimal"
                value="${q.min_qty_per_trip || ''}" placeholder="20" ${suaDuoc() ? '' : 'disabled'}>
              <span class="hint2">Xe chở ít hơn mức này vẫn tính tiền theo mức này — giá thành
                không giảm một đồng nào khi xe chở non tải.</span></div>
          </div>
          <div class="g3" style="margin-top:10px">
            <div class="f"><label>Phụ phí chờ quá 2 giờ <span class="hint">VNĐ / giờ</span></label>
              <input id="qtv2-wait" inputmode="numeric"
                value="${q.waiting_surcharge ? tien(q.waiting_surcharge) : ''}"
                placeholder="200.000" ${suaDuoc() ? '' : 'disabled'}></div>
            <div class="f"><label>Điều khoản thanh toán</label>
              <select id="qtv2-terms" ${suaDuoc() ? '' : 'disabled'}>${DIEU_KHOAN.map(d =>
      `<option ${d === (q.payment_terms || DIEU_KHOAN[0]) ? 'selected' : ''}>${esc(d)}</option>`).join('')}</select></div>
            <div class="f"><label>Biên mục tiêu riêng cho khách này
                <span class="hint">% · để trống là theo công ty</span></label>
              <input id="qtv2-target" inputmode="decimal"
                value="${q.target_margin ? so(q.target_margin * 100) : ''}"
                placeholder="20" ${suaDuoc() ? '' : 'disabled'}></div>
          </div>
          <div class="g3" style="margin-top:10px">
            <div class="f"><label>Giá đối thủ · khách nói ra
                <span class="hint">VNĐ/chuyến · để trống nếu khách không nói</span></label>
              <input id="qtv2-competitor" inputmode="numeric"
                value="${q.competitor_price ? tien(q.competitor_price) : ''}"
                placeholder="3.850.000" ${suaDuoc() ? '' : 'disabled'}>
              <span class="hint2">Ghi ở đây chứ không ghi vào ô ghi chú: một con số nằm
                trong đoạn văn tự do thì sau này không lọc lại được để trả lời câu "mình
                mất khách vì giá hay vì thứ khác".</span></div>
            <div class="f"><label>Chiết khấu cho khách
                <span class="hint">% · để trống nếu không chiết khấu</span></label>
              <input id="qtv2-ck" inputmode="decimal"
                value="${q.discount_percent ? so(q.discount_percent * 100) : ''}"
                placeholder="5" ${suaDuoc() ? '' : 'disabled'}>
              <span class="hint2">Đơn giá ở trên là giá CUỐI khách trả. Phần trăm này chỉ để
                phiếu gửi khách in ra "giá gốc" trước chiết khấu — DO, biên, hoá đơn không đổi.</span></div>
          </div>
          <div id="qtv2-mgwarn"></div>
        </div>
      </div>`;
  }

  /* ---------------------------------------------- 6. Tách lệnh giao hàng ---- */

  function mucTachDo(q) {
    return `
      <div class="sec" id="qtv2-sec-do">
        <h3>6. Lệnh giao hàng (DO) sinh từ báo giá
          <span class="tag" id="qtv2-dotag">sinh khi khách chấp nhận</span></h3>
        <p>Không còn bước Đơn hàng và không còn tách tay: <b>ghi nhận khách chấp nhận là hệ
          thống sinh DO ngay</b>, kế thừa tuyến, giá khoá và khung giờ của báo giá.
          <b>1 DO = 1 cont (hoặc 1 xe) = 1 chuyến.</b> Số niêm phong ghi vào DO trước khi
          điều phối.</p>
        <div class="rule">
          <div><b>Số DO</b>Gợi ý = tổng số lượng ở bảng Hàng hoá (mỗi cont/xe một DO). Thêm
            hoặc bớt được.</div>
          <div><b>Giờ lấy hàng</b>Là hạn để Điều phối xếp xe. Mặc định lấy từ khung "Lấy hàng ·
            từ", cách nhau 2–3 giờ.</div>
          <div><b>Hạn giao</b>Lấy từ khung "Giao hàng · đến" của báo giá. Sửa riêng từng DO nếu
            khách cần lệch.</div>
        </div>
        <div id="qtv2-dobody"></div>
      </div>`;
  }

  function veTachDo() {
    const q = S.q;
    const than = el('qtv2-dobody');
    const muc = el('qtv2-sec-do');
    const the = el('qtv2-dotag');
    if (!q || !than || !muc) return;
    const rt = tuyenTheoMa(q.route_id);

    if (q.delivery_orders && q.delivery_orders.length) {
      the.textContent = q.delivery_orders.length + ' DO đã tách';
      the.className = 'tag t-blue';
      muc.classList.remove('lock');
      const mauTt = {
        pending: ['p', 'Chờ xếp'], planned: ['p', 'Đã lập chuyến'],
        in_transit: ['r', 'Đang giao'], arrived: ['r', 'Đã đến nơi'],
        delivered: ['d', 'Đã giao'], completed: ['d', 'Xong'],
      };
      than.innerHTML = q.delivery_orders.map(d => {
        const [mau, nhan] = mauTt[d.canonical_status] || ['', d.canonical_status];
        return `<div class="dorow"><span class="st ${mau}"></span>
          <div><b>${esc(d.id)} · giá khoá ${tien(d.unit_price)} VNĐ/chuyến</b>
            <span>lấy ${esc(gioVietNam(d.pickup_date))} · hạn giao ${esc(gioVietNam(d.delivery_date))}${
          d.driver_note ? ' · ' + esc(d.driver_note) : ''}</span></div>
          <span class="tag ${mau === 'd' ? 't-green' : mau === 'r' ? 't-purple' : 't-blue'}">${esc(nhan)}</span>
        </div>`;
      }).join('')
        + `<div class="warn blue">ⓘ <div>Khách tăng hàng? Thêm dòng ở bảng Hàng hoá rồi tách
            tiếp — DO cũ giữ nguyên. Mở danh sách ở <a id="qtv2-mo-do"
            style="text-decoration:underline;cursor:pointer">Lệnh giao hàng</a>.</div></div>`;
      if (el('qtv2-mo-do')) {
        el('qtv2-mo-do').addEventListener('click', () => {
          if (typeof window.switchView === 'function') window.switchView('ops-planning');
        });
      }
      return;
    }

    if (q.canonical_status !== 'accepted') {
      the.textContent = 'sinh khi khách chấp nhận';
      the.className = 'tag';
      muc.classList.add('lock');
      than.innerHTML = `<div class="warn blue">ⓘ <div>Báo giá đang ở trạng thái
        <b>${esc((TRANG_THAI[q.canonical_status] || [q.canonical_status])[0])}</b>. Khi ghi nhận
        khách chấp nhận, hệ thống sinh ${soLuongHang()} DO (mỗi đơn vị hàng hoá một DO) và
        chúng hiện ở đây.</div></div>`;
      return;
    }

    muc.classList.remove('lock');
    the.textContent = 'sẵn sàng tách';
    the.className = 'tag t-green';

    const n = soLuongHang();
    if (S.dongTach.length !== n) S.dongTach = dungDongTach(n);
    // CÓ NIÊM PHONG THÌ PHẢI CÓ CHỖ GHI SỐ SEAL.
    //
    // Đây là một CHỐT XUẤT BẾN: hàng nguyên cont không đếm kiện, nên bằng
    // chứng duy nhất cho biết hàng không bị mở trên đường là số niêm phong —
    // và bước điều phối chặn xe không có nó. Không có cột này thì mọi chuyến
    // container dừng ở màn Điều phối với một thông báo không có chỗ nào sửa.
    const canSeal = /^có/i.test(String(q.sealing || '').trim());
    const hong = d => !rt || !d.pick || (canSeal && !String(d.seal || '').trim());
    than.innerHTML = `<div class="split-wrap"><div class="split${canSeal ? ' co-seal' : ''}">
        <div class="r"><span>#</span><span>Hàng hoá</span><span>Đơn vị</span><span>Ngày lấy</span>
          <span>Giờ lấy</span><span>Hạn giao</span>${canSeal ? '<span>Số niêm phong</span>' : ''}
          <span>Ghi chú cho tài xế</span><span></span></div>
        ${S.dongTach.map((x, i) => `<div class="r ${hong(x) ? 'bad' : ''}">
          <i>${i + 1}</i>
          <span>${esc(x.name || '—')}<br><small style="color:#7b8796">${
      esc(rt ? (rt.name || rt.id) : 'chưa có tuyến')}</small></span>
          <select data-i="${i}" data-f="unit">${DVT_HANG.map(u =>
        `<option ${x.unit === u ? 'selected' : ''}>${esc(u)}</option>`).join('')}</select>
          <input type="date" value="${esc(x.date)}" data-i="${i}" data-f="date">
          <input value="${esc(x.pick)}" data-i="${i}" data-f="pick" placeholder="07:00">
          <input type="datetime-local" value="${esc(x.due)}" data-i="${i}" data-f="due">
          ${canSeal ? `<input value="${esc(x.seal || '')}" data-i="${i}" data-f="seal"
            placeholder="SL-0001">` : ''}
          <input value="${esc(x.note || '')}" data-i="${i}" data-f="note"
            placeholder="cổng B, mang phiếu xuất kho…">
          <button type="button" class="x" data-i="${i}" title="Bớt dòng">×</button></div>`).join('')}
        <button type="button" class="add" id="qtv2-them-do">+ Thêm DO</button>
      </div></div>
      <div class="warn ${(!rt || S.dongTach.some(hong)) ? 'red' : 'green'}">${!rt
        ? '✗ <div>Chưa chọn tuyến — không tách DO được.</div>'
        : S.dongTach.some(hong)
          ? `✗ <div>${S.dongTach.filter(hong).length} dòng chưa đủ: `
            + `${canSeal ? 'hàng nguyên khối phải ghi số niêm phong, và ' : ''}`
            + 'phải có giờ lấy hàng. Thiếu số niêm phong thì bước Điều phối '
            + 'không cho xe xuất bến.</div>`'
        : `✓ <div>Sẽ tạo <b>${S.dongTach.length} DO</b> · tuyến ${esc(rt.name || rt.id)} ·
            xuất hiện ở "Lệnh giao hàng → Cần xử lý" để Điều phối xếp xe. Giá cước
            <b>${tien(q.selling_price)} VNĐ/chuyến</b> được khoá theo báo giá.</div>`}</div>`;

    than.querySelectorAll('input,select').forEach(x => x.addEventListener('change', () => {
      S.dongTach[+x.dataset.i][x.dataset.f] = x.value;
      veTachDo();
    }));
    than.querySelectorAll('.x').forEach(b => b.addEventListener('click', () => {
      if (S.dongTach.length < 2) {
        thongBao('Phải còn tối thiểu một DO để tách.', true);
        return;
      }
      S.dongTach.splice(+b.dataset.i, 1);
      veTachDo();
      veThanhDay();
    }));
    el('qtv2-them-do').addEventListener('click', () => {
      const m = S.dongTach[S.dongTach.length - 1] || {};
      S.dongTach.push({
        name: (S.q.items[0] && S.q.items[0].name) || '—',
        unit: m.unit || (S.q.items[0] && S.q.items[0].uom) || "40'",
        date: m.date || ngayHomNayCong(2),
        pick: m.pick || '07:00',
        due: m.due || chuanDatetimeLocal(S.q.delivery_window_end) || '',
        seal: '', note: '',
      });
      veTachDo();
      veThanhDay();
    });
    veThanhDay();
  }

  /**
   * Dựng N dòng tách, mỗi đơn vị hàng một dòng.
   *
   * Giờ lấy cách nhau 2 giờ 30 kể từ khung "Lấy hàng · từ" của báo giá: mấy
   * chiếc cùng một tuyến không xếp cùng một giờ được, và một hàng dài toàn
   * 07:00 làm màn Điều phối không biết xếp cái nào trước.
   */
  function dungDongTach(n) {
    const q = S.q;
    const batDau = q.pickup_window_start ? new Date(q.pickup_window_start) : null;
    const hanGiao = chuanDatetimeLocal(q.delivery_window_end);
    const ra = [];
    let k = 0;
    (q.items || []).forEach(it => {
      const sl = parseInt(it.quantity, 10) || 0;
      for (let j = 0; j < sl; j++) {
        let ngay = ngayHomNayCong(2);
        let gio = '07:00';
        if (batDau && !isNaN(batDau.getTime())) {
          const d = new Date(batDau.getTime() + k * 150 * 60000);
          const p = x => String(x).padStart(2, '0');
          ngay = `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
          gio = `${p(d.getHours())}:${p(d.getMinutes())}`;
        }
        ra.push({
          name: it.name || '—', unit: it.uom || "40'",
          date: ngay, pick: gio, due: hanGiao, seal: '', note: it.note || '',
        });
        k++;
      }
    });
    return ra.length ? ra : [{
      name: '—', unit: "40'", date: ngayHomNayCong(2), pick: '07:00', due: hanGiao,
      seal: '', note: '',
    }];
  }

  /* ---------------------------------------------- 7. Chứng từ đính kèm ------ */

  function mucChungTu(q) {
    return `
      <div class="sec">
        <h3>7. Chứng từ đính kèm
          <span class="tag" id="qtv2-doctag">${(q.attachments || []).length} tệp</span></h3>
        <p>PDF, DOCX, PNG, JPG · tối đa 25 MB mỗi tệp. Đính kèm được ngay khi còn nháp; chứng từ
          đi theo DO xuống vận hành và kế toán.</p>
        <div class="g3">
          <div class="f"><label>Loại chứng từ</label>
            <select id="qtv2-doctype">${LOAI_CHUNG_TU.map(t =>
      `<option>${esc(t)}</option>`).join('')}</select></div>
          <div class="f"><label>Ghi chú</label>
            <input id="qtv2-docnote" placeholder="Bản ký ngày 04/09"></div>
          <div class="f"><label>&nbsp;</label>
            <button type="button" class="ghost" id="qtv2-chon-tep">☁ Chọn tệp và đính kèm</button>
            <input type="file" id="qtv2-tep" class="qt-hide"
              accept=".pdf,.doc,.docx,.png,.jpg,.jpeg"></div>
        </div>
        <div id="qtv2-files" style="margin-top:8px"></div>
        <div class="up" id="qtv2-tha">Kéo tệp vào đây hoặc bấm "Chọn tệp" ở trên</div>
      </div>`;
  }

  function veChungTu() {
    const q = S.q;
    const o = el('qtv2-files');
    if (!o || !q) return;
    const ds = q.attachments || [];
    el('qtv2-doctag').textContent = ds.length + ' tệp';
    o.innerHTML = ds.map(a => {
      const kb = Number(a.size_bytes || 0);
      const co = kb >= 1048576 ? so(kb / 1048576) + ' MB' : Math.max(1, Math.round(kb / 1024)) + ' KB';
      const duoi = (String(a.file_name || '').split('.').pop() || '').toUpperCase().slice(0, 4);
      return `<div class="fl">
        <span class="ic">${esc(duoi || '?')}</span>
        <div><b>${esc(a.file_name)}</b>
          <span>${esc(a.doc_type)} · ${co}${a.note ? ' · ' + esc(a.note) : ''}</span></div>
        <span style="font-size:11.5px;color:#7b8796">${esc(a.uploaded_by || '—')}</span>
        <span style="font-size:11.5px;color:#7b8796">${esc((a.uploaded_at || '').slice(0, 10))}</span>
        <button type="button" class="x" data-a="${esc(a.id)}" title="Xoá">×</button></div>`;
    }).join('') || '<div class="hint2">Chưa có chứng từ nào.</div>';

    o.querySelectorAll('.fl b').forEach((b, i) => {
      b.style.cursor = 'pointer';
      b.style.textDecoration = 'underline';
      b.addEventListener('click', () => {
        const a = ds[i];
        window.open(base() + `/api/quotations/${encodeURIComponent(q.id)}`
          + `/attachments/${encodeURIComponent(a.id)}/file`, '_blank');
      });
    });
    o.querySelectorAll('.x').forEach(b => b.addEventListener('click', () => xoaChungTu(b.dataset.a)));
  }

  async function guiChungTu(tep) {
    const q = S.q;
    if (!tep) return;
    if (!q.id) {
      thongBao('Bấm "Lưu nháp" một lần trước đã — chứng từ cần một mã báo giá để gắn vào.', true);
      return;
    }
    if (tep.size > 25 * 1024 * 1024) {
      thongBao(`Tệp ${tep.name} lớn hơn 25 MB.`, true);
      return;
    }
    const goi = new FormData();
    goi.append('doc_type', el('qtv2-doctype').value);
    goi.append('note', el('qtv2-docnote').value || '');
    goi.append('file', tep);
    try {
      // KHÔNG đặt Content-Type: trình duyệt phải tự đặt kèm `boundary`, đặt tay
      // là máy chủ không tách được các phần của biểu mẫu.
      const tra = await fetch(base() + `/api/quotations/${encodeURIComponent(q.id)}/attachments`,
        { method: 'POST', body: goi });
      const kq = await tra.json().catch(() => ({}));
      if (!tra.ok) {
        throw new Error((kq.error && kq.error.message) || (kq.detail && (kq.detail.message
          || kq.detail)) || `HTTP ${tra.status}`);
      }
      q.attachments = (q.attachments || []).concat([kq.data]);
      el('qtv2-docnote').value = '';
      veChungTu();
      thongBao(kq.message || 'Đã đính kèm chứng từ.');
    } catch (loi) {
      thongBao('Không đính kèm được: ' + loi.message, true);
    }
  }

  async function xoaChungTu(aid) {
    const q = S.q;
    if (!window.confirm('Xoá chứng từ này khỏi báo giá?')) return;
    try {
      await api(`/api/quotations/${encodeURIComponent(q.id)}/attachments/${encodeURIComponent(aid)}`,
        { method: 'DELETE' });
      q.attachments = (q.attachments || []).filter(a => a.id !== aid);
      veChungTu();
      thongBao('Đã xoá chứng từ.');
    } catch (loi) {
      thongBao('Không xoá được chứng từ: ' + loi.message, true);
    }
  }

  /* ---------------------------------------------- 8. Ghi chú ---------------- */

  function mucGhiChu(q) {
    const k = suaDuoc() ? '' : 'disabled';
    return `
      <div class="sec">
        <h3>8. Ghi chú và điều kiện</h3>
        <div class="g2">
          <div class="f"><label>Ghi chú gửi khách <span class="hint">in trên PDF</span></label>
            <textarea rows="3" id="qtv2-n-cus" ${k}
              placeholder="Giá chưa gồm VAT. Phụ phí lưu bãi tính theo thực tế…">${esc(q.notes_customer || '')}</textarea></div>
          <div class="f"><label>Ghi chú cho vận hành
              <span class="hint">hiện trên DO và lệnh tài xế</span></label>
            <textarea rows="3" id="qtv2-n-ops" ${k}
              placeholder="Cổng B chỉ nhận đến 16:30. Gọi trước 30 phút.">${esc(q.notes_ops || '')}</textarea></div>
          <div class="f" style="grid-column:1/-1"><label>Ghi chú nội bộ
              <span class="hint">không in</span></label>
            <textarea rows="2" id="qtv2-n-int" ${k}
              placeholder="Khách đang so giá với đối thủ, tối đa giảm 3%…">${esc(q.notes_internal || '')}</textarea></div>
        </div>
      </div>`;
  }

  /* =========================================================================
     NỐI SỰ KIỆN CỦA PHIẾU
     ========================================================================= */

  function noiSuKien() {
    const q = S.q;
    const noi = (id, sk, ham) => { const n = el(id); if (n) n.addEventListener(sk, ham); };

    noi('qtv2-khach', 'change', () => { q.customer_id = el('qtv2-khach').value; napGiaDaBao(); tinhLaiGia(); });
    noi('qtv2-tuyen', 'change', () => {
      q.route_id = el('qtv2-tuyen').value;
      const rt = tuyenTheoMa(q.route_id);
      const [dau, cuoi] = diemDauCuoi(rt);
      q.origin = dau;
      q.destination = cuoi;
      capNhatChuTuyen();
      S.dongTach = [];
      tinhLaiGia();
    });
    noi('qtv2-tien', 'change', () => { q.currency_code = el('qtv2-tien').value; tinhLaiGia(); });
    noi('qtv2-valid', 'change', () => { q.valid_to = el('qtv2-valid').value; tinhLaiGia(); });

    [['qtv2-p1', 'pickup_window_start'], ['qtv2-p2', 'pickup_window_end'],
      ['qtv2-d1', 'delivery_window_start'], ['qtv2-d2', 'delivery_window_end']]
      .forEach(([id, ten]) => noi(id, 'change', () => {
        q[ten] = el(id).value;
        S.dongTach = [];
        veTachDo();
        tinhLaiGia();
      }));
    noi('qtv2-trips', 'change', () => {
      q.trips_per_month = parseInt(String(el('qtv2-trips').value).replace(/\D/g, ''), 10) || 0;
      veKetQua();
    });
    noi('qtv2-recip', 'change', () => { q.recipient_contact = el('qtv2-recip').value; });
    noi('qtv2-kind', 'change', () => { q.cargo_type = el('qtv2-kind').value; });
    noi('qtv2-temp', 'change', () => { q.temperature_requirement = el('qtv2-temp').value; });
    noi('qtv2-stack', 'change', () => { q.stacking = el('qtv2-stack').value; });
    noi('qtv2-seal', 'change', () => { q.sealing = el('qtv2-seal').value; });

    noi('qtv2-kg', 'input', () => {
      q.weight_kg = docSo(el('qtv2-kg').value);
      tinhLaiGia();
    });
    noi('qtv2-m3', 'change', () => { q.volume_m3 = docSo(el('qtv2-m3').value); tinhLaiGia(); });
    noi('qtv2-pal', 'change', () => {
      q.pallet_count = parseInt(String(el('qtv2-pal').value).replace(/\D/g, ''), 10) || 0;
    });
    noi('qtv2-val', 'change', () => { q.cargo_value = docSo(el('qtv2-val').value); tinhLaiGia(); });

    noi('qtv2-chon-tep', 'click', () => el('qtv2-tep').click());
    noi('qtv2-tep', 'change', () => {
      const t = el('qtv2-tep').files && el('qtv2-tep').files[0];
      el('qtv2-tep').value = '';
      guiChungTu(t);
    });
    const tha = el('qtv2-tha');
    if (tha) {
      ['dragenter', 'dragover'].forEach(sk => tha.addEventListener(sk, e => {
        e.preventDefault();
        tha.classList.add('drag');
      }));
      ['dragleave', 'drop'].forEach(sk => tha.addEventListener(sk, e => {
        e.preventDefault();
        tha.classList.remove('drag');
      }));
      tha.addEventListener('drop', e => {
        const t = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
        if (t) guiChungTu(t);
      });
    }

    ['qtv2-n-cus', 'qtv2-n-ops', 'qtv2-n-int'].forEach((id, i) => noi(id, 'change', () => {
      q[['notes_customer', 'notes_ops', 'notes_internal'][i]] = el(id).value;
    }));

    noiSuKienGia();
    capNhatChuTuyen();
  }

  /** Nối riêng các ô của mục Cước — mục này được vẽ lại sau mỗi lần tính. */
  function noiSuKienGia() {
    const q = S.q;
    const noi = (id, sk, ham) => { const n = el(id); if (n) n.addEventListener(sk, ham); };
    noi('qtv2-basis', 'change', () => {
      q.price_basis = el('qtv2-basis').value;
      veHangHoa();
      tinhLaiGia();
    });
    noi('qtv2-price', 'input', () => {
      // Ô nhập theo TIỀN TỆ ĐANG CHỌN; số lưu là VNĐ. Không quy đổi ở đây thì
      // báo giá bằng USD được lưu thành mấy nghìn đồng.
      q.unit_price = docSo(el('qtv2-price').value) * (tyGia(q.currency_code) || 1);
      veKetQua();
    });
    noi('qtv2-minqty', 'change', () => {
      q.min_qty_per_trip = docSo(el('qtv2-minqty').value);
      veKetQua();
    });
    noi('qtv2-wait', 'change', () => { q.waiting_surcharge = docSo(el('qtv2-wait').value); });
    noi('qtv2-terms', 'change', () => { q.payment_terms = el('qtv2-terms').value; });
    noi('qtv2-competitor', 'change', () => {
      q.competitor_price = docSo(el('qtv2-competitor').value);
      napGiaDaBao();
    });
    noi('qtv2-ck', 'change', () => {
      const p = docSo(el('qtv2-ck').value);
      q.discount_percent = p > 0 && p < 100 ? p / 100 : 0;
    });
    noi('qtv2-target', 'change', () => {
      const p = docSo(el('qtv2-target').value);
      q.target_margin = p > 0 ? p / 100 : 0;
      tinhLaiGia();
    });
  }

  /* =========================================================================
     TÍNH GIÁ — máy chủ tính, màn hình chỉ hiện
     ========================================================================= */

  function tinhLaiGia() {
    clearTimeout(S.henTinh);
    S.henTinh = setTimeout(goiXemTruoc, 260);
  }

  async function goiXemTruoc() {
    const q = S.q;
    if (!q) return;
    try {
      S.xemTruoc = await ghi('/api/quotations/price-preview', {
        route_id: q.route_id || '',
        vehicle_type_id: q.vehicle_type_id || '',
        weight_kg: q.weight_kg || 0,
        cargo_value: q.cargo_value || 0,
        customer_id: q.customer_id || '',
        // GỬI `null` chứ không gửi 0 khi không khai biên riêng cho khách này.
        // Gửi 0 làm mất mốc giá "Biên mục tiêu", vì máy chủ đọc 0 thành một
        // biên mục tiêu 0% — mà biên 0% thì không có giá nào đạt được.
        target_margin: Number(q.target_margin) > 0 ? q.target_margin : null,
      });
    } catch (loi) {
      S.xemTruoc = null;
      thongBao('Không tính được giá thành: ' + loi.message, true);
    }
    veLoaiXe();
    veKetQua();
  }

  /** Số lượng của MỘT chuyến, theo đơn vị tính cước. */
  function soLuongMoiChuyen() {
    const q = S.q;
    const rt = tuyenTheoMa(q.route_id);
    const km = kmTuyen(rt);
    switch (q.price_basis || 'per_trip') {
      case 'per_tonne': return Number(q.weight_kg || 0) / 1000;
      case 'per_kg': return Number(q.weight_kg || 0);
      case 'per_m3': return Number(q.volume_m3 || 0);
      case 'per_km': return km;
      default: return 1;
    }
  }

  /** Cước MỘT CHUYẾN, quy từ đơn giá theo đơn vị của khách. */
  function cuocMoiChuyen() {
    const q = S.q;
    const dv = q.price_basis || 'per_trip';
    let sl = soLuongMoiChuyen();
    const toiThieu = Number(q.min_qty_per_trip || 0);
    if (['per_tonne', 'per_m3', 'per_kg'].includes(dv) && toiThieu > 0) sl = Math.max(sl, toiThieu);
    return Number(q.unit_price || 0) * (dv === 'per_trip' ? 1 : sl);
  }

  function veKetQua() {
    const q = S.q;
    const xt = S.xemTruoc;
    if (!q || !el('qtv2-nocalc')) return;
    const thieu = (xt && xt.viec_con_thieu) || ['Đang tính lại giá thành…'];
    const tinhDuoc = !!(xt && xt.tinh_duoc);

    el('qtv2-nocalc').classList.toggle('qt-hide', tinhDuoc);
    el('qtv2-calc').classList.toggle('qt-hide', !tinhDuoc);
    if (!tinhDuoc) {
      el('qtv2-missing').innerHTML = thieu.map(m => `<li>${esc(m)}</li>`).join('');
      ['qtv2-r-cost', 'qtv2-r-rev', 'qtv2-r-pf'].forEach(id => { el(id).textContent = '—'; });
      el('qtv2-r-bar').style.width = '0';
      el('qtv2-r-thang').textContent = '';
      el('qtv2-r-nguong-chu').textContent = '';
      el('qtv2-r-chk').innerHTML = thieu.map(m =>
        `<div class="chk"><i class="no">✕</i><span>${esc(m)}</span></div>`).join('');
      veThanhDay();
      return;
    }

    const ty = tyGia(q.currency_code) || 1;
    const sym = kyHieu(q.currency_code);
    const giaThanh = Number(xt.gia_thanh || 0);
    const cuoc = cuocMoiChuyen();
    const bien = cuoc > 0 ? (cuoc - giaThanh) / cuoc : null;
    const nguong = Number(q.target_margin || xt.nguong_bien || 0.15);
    const mucTieu = Number(q.target_margin || xt.bien_muc_tieu || 0.20);
    q.selling_price = cuoc;
    q.total_cost = giaThanh;
    q.bien = bien;

    const dv = DON_VI_CUOC.find(x => x[0] === (q.price_basis || 'per_trip')) || DON_VI_CUOC[0];
    const oUnit = el('qtv2-price-unit');
    if (oUnit) oUnit.textContent = `${sym} / ${dv[2]}`;
    el('qtv2-cursym').textContent = sym;
    el('qtv2-min-wrap').classList.toggle('qt-hide',
      !['per_tonne', 'per_m3', 'per_kg'].includes(q.price_basis));

    // Bảng cấu phần. Hàng `thu` KHÔNG được cộng vào giá thành — máy chủ đã tách
    // hai loại, ở đây chỉ hiện đúng thứ nó gửi về.
    el('qtv2-ct').innerHTML = `<div class="r"><span>Khoản mục · công thức ${
      esc(tenLoaiXe(q.vehicle_type_id))}</span><span class="n">Đơn giá</span>
      <span class="n">Nhân với</span><span class="amt">Thành tiền</span></div>`
      + (xt.cac_dong || []).map(d => `<div class="r ${d.loai === 'thu' ? 'rev' : 'cost'}">
          <span>${esc(d.nhan)}<span class="kind ${d.loai === 'thu' ? 'k-r' : 'k-c'}">${
        d.loai === 'thu' ? 'thu' : 'chi'}</span></span>
          <span class="n">${tien(d.don_gia / ty)} ${esc(sym)}</span>
          <span class="n">${esc(d.nhan_voi)}</span>
          <span class="amt">${tien(d.thanh_tien / ty)} ${esc(sym)}</span></div>`).join('')
      + `<div class="r sumline"><span>Giá thành một chuyến</span><span class="n"></span>
          <span class="n"></span><span class="amt">${tien(giaThanh / ty)} ${esc(sym)}</span></div>`
      + `<div class="r rev"><span>Cước báo khách<span class="kind k-r">thu</span></span>
          <span class="n">${q.unit_price ? tien(q.unit_price / ty) + ' ' + esc(sym) : ''}</span>
          <span class="n">${q.price_basis === 'per_trip' ? '1 chuyến'
        : '× ' + so(soLuongMoiChuyen()) + ' ' + esc(dv[2])}</span>
          <span class="amt">${tien(cuoc / ty)} ${esc(sym)}</span></div>`
      + `<div class="r sumline"><span>Lợi nhuận một chuyến</span><span class="n"></span>
          <span class="n"></span><span class="amt" style="color:#0b4faa">${
        tien((cuoc - giaThanh) / ty)} ${esc(sym)} · ${phanTram(bien)}</span></div>`;

    const rt = tuyenTheoMa(q.route_id);
    el('qtv2-fdesc').textContent = `Công thức của ${tenLoaiXe(q.vehicle_type_id)} · `
      + `${so(xt.km)} km · ${xt.so_chang} chặng · phí BOT lấy từ `
      + ({ tuyen: 'tuyến đường', loai_xe: 'công thức loại xe', khong_co: 'chưa khai ở đâu' })[xt.cach_lay_bot]
      + '. Sửa công thức ở Dữ liệu gốc → Công thức giá thành.';
    if (rt) el('qtv2-fsrc').textContent = 'công thức Dữ liệu gốc · ' + rt.id;

    veMocGia(xt, giaThanh, ty, sym);

    // Cảnh báo biên.
    el('qtv2-mgwarn').innerHTML = bien === null
      ? '<div class="warn amber">⚠ <div>Chưa nhập đơn giá cước nên chưa có biên.</div></div>'
      : bien < 0
        ? `<div class="warn red">✗ <div><b>Đang LỖ ${tien((giaThanh - cuoc) / ty)} ${esc(sym)}
            mỗi chuyến</b><div style="font-weight:500">Báo giá lỗ không duyệt và không gửi được.
            Giá tối thiểu để không lỗ: <b>${tien(giaThanh / ty)} ${esc(sym)}</b>
            /chuyến.</div></div></div>`
        : bien < nguong
          ? `<div class="warn red">✗ <div><b>Biên ${phanTram(bien)} dưới ngưỡng ${
            phanTram(nguong, 0)}</b><div style="font-weight:500">Gửi khách sẽ chuyển sang
            "Chờ duyệt nội bộ". Giá để đạt ngưỡng: <b>${tien(giaThanh / (1 - nguong) / ty)}
            ${esc(sym)}</b>/chuyến.</div></div></div>`
          : bien < mucTieu
            ? `<div class="warn amber">⚠ <div>Biên ${phanTram(bien)} — sát ngưỡng. Cân nhắc
              <b>${tien(giaThanh / (1 - mucTieu) / ty)} ${esc(sym)}</b>/chuyến để đạt
              ${phanTram(mucTieu, 0)}.</div></div>`
            : `<div class="warn green">✓ <div>Biên ${phanTram(bien)} — trên ngưỡng công
              ty.</div></div>`;

    noiSuKienGia();
    veKetQuaCotPhai(giaThanh, cuoc, bien, nguong, ty, sym);
    veThanhDay();
  }

  /**
   * Ba mốc giá của cột Đơn giá.
   *
   * Bản mẫu điền sẵn `giá thành × 3,9` và spec tự gọi đó là "số demo, không có
   * ý nghĩa nghiệp vụ". Nên ở đây chỉ hiện những mốc CÓ NGUỒN mà máy chủ trả
   * về; mốc nào không có nguồn thì không có nút, chứ không đoán một con số
   * người dùng sẽ tin mà không kiểm lại.
   */
  function veMocGia(xt, giaThanh, ty, sym) {
    const o = el('qtv2-sugs');
    if (!o) return;
    const moc = xt.goi_y_gia || {};
    const nhan = { theo_cong_thuc: 'Theo công thức', bien_muc_tieu: 'Biên mục tiêu', hop_dong: 'Hợp đồng', lan_truoc: 'Lần trước' };
    const ds = Object.keys(moc);
    if (!ds.length) { o.innerHTML = ''; return; }
    // Mốc là giá MỘT CHUYẾN. Đổi về đơn giá theo đơn vị đang chọn để bấm vào là
    // điền đúng ô — điền giá một chuyến vào ô "VNĐ/tấn" thì cước gấp 24 lần.
    const sl = soLuongMoiChuyen();
    const chia = (S.q.price_basis || 'per_trip') === 'per_trip' ? 1 : (sl > 0 ? sl : 1);
    o.innerHTML = ds.map(k => {
      const donGia = Number(moc[k].gia) / chia;
      return `<button type="button" data-gia="${donGia}" title="${esc(moc[k].mo_ta)}">${
        esc(nhan[k] || k)} → ${tien(donGia / ty)} ${esc(sym)}</button>`;
    }).join('');
    o.querySelectorAll('button').forEach(b => b.addEventListener('click', () => {
      S.q.unit_price = Number(b.dataset.gia);
      el('qtv2-price').value = tien(S.q.unit_price / ty);
      veKetQua();
    }));
  }

  function veKetQuaCotPhai(giaThanh, cuoc, bien, nguong, ty, sym) {
    const q = S.q;
    el('qtv2-r-cost').textContent = tien(giaThanh / ty) + ' ' + sym;
    el('qtv2-r-rev').textContent = cuoc > 0 ? tien(cuoc / ty) + ' ' + sym : '—';
    el('qtv2-r-pf').textContent = cuoc > 0
      ? tien((cuoc - giaThanh) / ty) + ' ' + sym + ' · ' + phanTram(bien) : '—';

    const bar = el('qtv2-r-bar');
    // Thang 0–50%: biên vận tải hiếm khi qua 50%, nên chia hết 0–100% thì mọi
    // báo giá đều là một vạch ngắn nhìn không phân biệt được.
    const pt = bien === null ? 0 : Math.min(100, Math.max(0, bien * 200));
    bar.style.width = pt + '%';
    bar.style.background = bien === null ? '#cbd5e1'
      : bien >= 0.20 ? '#15803d' : bien >= nguong ? '#b45309' : '#d32f2f';
    el('qtv2-r-nguong').style.left = Math.min(100, nguong * 200) + '%';
    el('qtv2-r-nguong-chu').textContent = `Vạch đỏ = ngưỡng biên ${phanTram(nguong, 0)}`
      + `${q.target_margin ? ' (riêng cho khách này)' : ' của công ty'}. `
      + 'Dưới ngưỡng cần trưởng phòng duyệt. Thang 0–50%.';

    const tr = Number(q.trips_per_month || 0);
    el('qtv2-r-thang').innerHTML = tr > 0 && cuoc > 0
      ? `Cam kết ${tr} chuyến/tháng → doanh thu ≈ <b>${tien(cuoc * tr / ty)} ${esc(sym)}</b>, `
        + `lợi nhuận ≈ <b>${tien((cuoc - giaThanh) * tr / ty)} ${esc(sym)}</b>/tháng`
      : '';

    const con = q.valid_to ? soNgayConLai(q.valid_to) : null;
    const chk = [
      [q.route_id && Number(S.xemTruoc && S.xemTruoc.km) > 0, 'Đã có tuyến và số km'],
      [!!q.vehicle_type_id, 'Đã chọn loại xe đủ tải'],
      [!!q.valid_to && con !== null && con >= 0,
        con !== null && con < 0 ? 'Hiệu lực đã qua — cần gia hạn' : 'Đã có hiệu lực và điều khoản'],
      [Number(q.unit_price || 0) > 0, 'Đã nhập đơn giá cước'],
      [bien !== null && bien >= nguong,
        bien === null ? 'Chưa có biên' : bien < 0 ? 'Đang lỗ — không gửi được'
          : `Biên trên ngưỡng ${phanTram(nguong, 0)}`],
      [!!(q.items || []).some(i => String(i.name || '').trim()), 'Bảng hàng hoá đã ghi tên hàng'],
      [!!q.pickup_window_start, 'Đã có khung giờ lấy hàng (không bắt buộc)'],
    ];
    el('qtv2-r-chk').innerHTML = chk.map(c =>
      `<div class="chk"><i class="${c[0] ? 'ok' : 'no'}">${c[0] ? '✓' : '✕'}</i>
        <span>${esc(c[1])}</span></div>`).join('');
  }

  function soNgayConLai(valid_to) {
    const d = new Date(String(valid_to).slice(0, 10) + 'T00:00:00');
    if (isNaN(d.getTime())) return null;
    const homNay = new Date();
    homNay.setHours(0, 0, 0, 0);
    return Math.round((d - homNay) / 86400000);
  }

  function vePhienBan() {
    const q = S.q;
    const o = el('qtv2-r-ver');
    if (!o || !q) return;
    const ds = q.versions || [];
    o.innerHTML = '<h4>Phiên bản giá</h4>' + (ds.length
      ? ds.map((v, i) => `<div class="ver"><span>v${v.version}</span>
          <b>${i === 0 ? 'Hiện tại · ' : ''}${tien(v.selling_price)} VNĐ</b>
          <span>· ${esc((v.created_at || '').slice(0, 10))}${v.note ? ' · ' + esc(v.note) : ''}</span>
        </div>`).join('')
      : '<div class="hint2">Chưa có phiên bản nào — phiên bản được chốt mỗi lần gửi khách '
        + 'hoặc sửa giá sau khi đã gửi.</div>');
  }

  async function napGiaDaBao() {
    const q = S.q;
    const o = el('qtv2-r-lichsu');
    if (!o || !q || !q.customer_id) return;
    o.innerHTML = '<h4>Giá đã báo cho khách này</h4><div class="hint2">Đang tải…</div>';
    try {
      const tv = new URLSearchParams({ limit: '3' });
      if (q.route_id) tv.set('route_id', q.route_id);
      // Bỏ chính báo giá đang mở: nó không phải "lần trước".
      if (q.id) tv.set('exclude', q.id);
      const ds = await doc(`/api/customers/${encodeURIComponent(q.customer_id)}`
        + '/price-history?' + tv.toString());
      o.innerHTML = '<h4>Giá đã báo cho khách này</h4>' + ((ds && ds.length)
        ? ds.map(x => `<div class="ver">
            <span>${esc((x.created_at || x.valid_to || '').slice(0, 10))}</span>
            <b>${tien(x.selling_price)} VNĐ</b>
            <span>· ${esc(x.quote_no || x.id)} · ${esc((TRANG_THAI[x.canonical_status]
          || [x.canonical_status])[0])}</span></div>`).join('')
        : '<div class="hint2">Chưa từng báo giá cho khách này trên tuyến này — không có mốc để '
          + 'so, nên soát kỹ giá thành trước khi gửi.</div>')
        // Chi hien khi CO SO THAT. Mot dong "gia doi thu —" lam nguoi doc tuong
        // da tra ma khong ra, khac han voi viec khach chua noi gi.
        + (Number(q.competitor_price) > 0
          ? `<div class="ver"><span>Đối thủ · khách nói</span>
              <b>≈ ${tien(q.competitor_price)} VNĐ</b>
              <span>· ${Number(q.selling_price) > 0
            ? (q.selling_price > q.competitor_price
              ? 'mình cao hơn ' + tien(q.selling_price - q.competitor_price) + ' VNĐ'
              : q.selling_price < q.competitor_price
                ? 'mình thấp hơn ' + tien(q.competitor_price - q.selling_price) + ' VNĐ'
                : 'bằng nhau')
            : 'chưa có cước của mình để so'}</span></div>`
          : '');
    } catch (loi) {
      o.innerHTML = '<h4>Giá đã báo cho khách này</h4>'
        + `<div class="hint2" style="color:#d32f2f">Không tải được: ${esc(loi.message)}</div>`;
    }
  }

  /* =========================================================================
     THANH ĐÁY CỐ ĐỊNH
     ========================================================================= */

  function veThanhDay() {
    const q = S.q;
    const sb = el('qtv2-sbar');
    if (!sb || !q) return;
    const xt = S.xemTruoc;
    const ty = tyGia(q.currency_code) || 1;
    const sym = kyHieu(q.currency_code);
    const tinhDuoc = !!(xt && xt.tinh_duoc);
    const bien = q.bien;
    const nguong = Number(q.target_margin || (xt && xt.nguong_bien) || 0.15);
    const nDo = soLuongHang();

    const chu = tinhDuoc
      ? `Giá thành <b>${tien(q.total_cost / ty)} ${esc(sym)}</b> · cước
         <b>${tien(q.selling_price / ty)} ${esc(sym)}</b> · biên
         <b style="color:${bien === null ? '#7b8796' : bien >= 0.20 ? '#15803d'
        : bien >= nguong ? '#b45309' : '#d32f2f'}">${phanTram(bien)}</b> · ${nDo} DO dự kiến`
      : `<b>Còn ${((xt && xt.viec_con_thieu) || []).length || 1} việc</b> trước khi gửi khách`;

    // Nút theo trạng thái — bảng ở spec mục 3.10.
    const tt = q.canonical_status;
    const duoiNguong = bien !== null && bien !== undefined && bien < nguong;
    const dayDu = tinhDuoc && Number(q.unit_price || 0) > 0 && !!q.valid_to
      && (soNgayConLai(q.valid_to) || 0) >= 0 && bien !== null && bien >= 0;
    const nut = [];
    nut.push(['qtv2-sb-huy', 'ghost', 'Huỷ', true]);
    if (suaDuoc()) nut.push(['qtv2-sb-nhap', 'ghost', S.dangLuu ? 'Đang lưu…' : 'Lưu nháp', !S.dangLuu]);
    if (q.id) {
      // HAI ban in: NOI BO (du moi thu, de ben minh xem va chot) va PHIEU GUI KHACH
      // (chi cac truong he thong cha can). Truoc chi co mot ban PDF chung in ca
      // bang gia thanh cho khach doc — lo het don gia xang dau, phu cap, BOT.
      nut.push(['qtv2-sb-pdf', 'ghost', 'In nội bộ', true]);
      nut.push(['qtv2-sb-khach', 'ghost', 'Phiếu gửi khách', Number(q.unit_price || 0) > 0]);
    }

    if (tt === 'draft') {
      nut.push(['qtv2-sb-gui', 'primary' + (duoiNguong ? ' amber' : ''),
        duoiNguong ? 'Gửi duyệt nội bộ' : 'Gửi khách', dayDu]);
    } else if (tt === 'pending_approval') {
      nut.push(['qtv2-sb-tra', 'ghost', 'Trả về nháp', true]);
      nut.push(['qtv2-sb-duyet', 'primary amber', 'Duyệt nội bộ và gửi khách', dayDu]);
    } else if (tt === 'sent' || tt === 'approved') {
      nut.push(['qtv2-sb-giahan', 'ghost', 'Gia hạn', true]);
      nut.push(['qtv2-sb-tuchoi', 'ghost', 'Khách từ chối', true]);
      nut.push(['qtv2-sb-nhan', 'primary green', 'Ghi nhận khách chấp nhận', true]);
    } else if (tt === 'accepted') {
      nut.push(['qtv2-sb-do', 'primary green',
        `Tạo ${S.dongTach.length || nDo} DO và chuyển vận hành →`, !!q.route_id]);
    } else if (tt === 'split') {
      nut.push(['qtv2-sb-modo', 'primary', 'Mở Lệnh giao hàng →', true]);
    } else if (tt === 'expired') {
      nut.push(['qtv2-sb-giahan', 'primary amber', 'Soát giá rồi gia hạn', true]);
    } else if (tt === 'rejected') {
      nut.push(['qtv2-sb-nhanban', 'primary', 'Nhân bản thành báo giá mới', true]);
    }

    sb.innerHTML = `<span class="s">${chu}</span><span class="sp"></span>`
      + nut.map(n => `<button type="button" id="${n[0]}" class="${n[1]}" ${
        n[3] ? '' : 'disabled'}>${esc(n[2])}</button>`).join('');

    const noi = (id, ham) => { const n = el(id); if (n) n.addEventListener('click', ham); };
    noi('qtv2-sb-huy', () => dongPhieu());
    noi('qtv2-sb-nhap', () => luuNhap(true));
    noi('qtv2-sb-pdf', xemPdf);
    noi('qtv2-sb-khach', phieuKhach);
    noi('qtv2-sb-gui', guiKhach);
    noi('qtv2-sb-duyet', () => lenh('internal-approve', {}, 'Đã duyệt nội bộ.'));
    noi('qtv2-sb-tra', traVeNhap);
    noi('qtv2-sb-giahan', giaHan);
    noi('qtv2-sb-tuchoi', khachTuChoi);
    noi('qtv2-sb-nhan', ghiNhanChapNhan);
    noi('qtv2-sb-do', tachDo);
    noi('qtv2-sb-modo', () => {
      if (typeof window.switchView === 'function') window.switchView('ops-planning');
    });
    noi('qtv2-sb-nhanban', nhanBan);
  }

  /* =========================================================================
     LƯU VÀ CÁC LỆNH
     ========================================================================= */

  /** Thân yêu cầu lưu. Mốc thời gian KÈM MÚI GIỜ — máy chủ đòi vậy. */
  function thanLuu() {
    const q = S.q;
    return {
      customer_id: q.customer_id,
      route_id: q.route_id,
      vehicle_type_id: q.vehicle_type_id || null,
      origin: q.origin || '',
      destination: q.destination || '',
      pickup_window_start: mocGuiLen(q.pickup_window_start),
      pickup_window_end: mocGuiLen(q.pickup_window_end),
      delivery_window_start: mocGuiLen(q.delivery_window_start),
      delivery_window_end: mocGuiLen(q.delivery_window_end),
      weight_kg: q.weight_kg || 0,
      volume_m3: q.volume_m3 || 0,
      pallet_count: q.pallet_count || 0,
      cargo_type: q.cargo_type || '',
      cargo_value: q.cargo_value || 0,
      temperature_requirement: q.temperature_requirement || '',
      stacking: q.stacking || '',
      sealing: q.sealing || '',
      recipient_contact: q.recipient_contact || '',
      valid_to: q.valid_to || '',
      price_basis: q.price_basis || 'per_trip',
      unit_price: q.unit_price || 0,
      min_qty_per_trip: q.min_qty_per_trip || 0,
      // `selling_price` KHÔNG gửi lên: máy chủ suy ra từ đơn giá và đơn vị. Gửi
      // cả hai thì hai con số có thể nói hai điều khác nhau về cùng một báo giá.
      total_cost: q.total_cost || 0,
      currency_code: q.currency_code || 'VND',
      fx_rate: tyGia(q.currency_code) || 1,
      payment_terms: q.payment_terms || '',
      waiting_surcharge: q.waiting_surcharge || 0,
      sales_rep: q.sales_rep || nguoiDangDung(),
      trips_per_month: q.trips_per_month || 0,
      // GỬI `null` chứ không gửi 0 khi không khai biên riêng cho khách này.
      //
      // Gửi 0 từng làm NGƯỠNG BIÊN THÀNH 0%: một báo giá biên 10% vẫn đi thẳng
      // sang khách dù nút đã ghi đúng "Gửi duyệt nội bộ". Máy chủ giờ cũng coi
      // 0 là không khai, nhưng phía này đừng nói sai ngay từ đầu.
      target_margin: Number(q.target_margin) > 0 ? q.target_margin : null,
      competitor_price: Number(q.competitor_price) > 0 ? q.competitor_price : null,
      discount_percent: Number(q.discount_percent) > 0 ? q.discount_percent : null,
      notes_customer: q.notes_customer || '',
      notes_ops: q.notes_ops || '',
      notes_internal: q.notes_internal || '',
    };
  }

  function thieuTruongBatBuoc() {
    const q = S.q;
    const thieu = [];
    if (!q.customer_id) thieu.push('khách hàng');
    if (!q.route_id) thieu.push('tuyến đường');
    if (!q.valid_to) thieu.push('hiệu lực đến');
    if (!Number(q.weight_kg || 0)) thieu.push('tổng tải trọng');
    return thieu;
  }

  async function luuNhap(noiKhiXong) {
    const q = S.q;
    const thieu = thieuTruongBatBuoc();
    if (thieu.length) {
      thongBao('Chưa khai: ' + thieu.join(', ') + '. Bốn ô đó là mức tối thiểu để lưu.', true);
      return false;
    }
    if (S.dangLuu) return false;
    S.dangLuu = true;
    veThanhDay();
    try {
      const than = thanLuu();
      const kq = q.id
        ? await ghi('/api/quotations/' + encodeURIComponent(q.id), than, 'PUT')
        : await ghi('/api/quotations', than, 'POST');
      const maMoi = (kq && (kq.id || (kq.quotation && kq.quotation.id))) || q.id;
      if (!maMoi) throw new Error('Máy chủ không trả về mã báo giá.');
      // BẢNG HÀNG HOÁ lưu bằng một đường riêng, và phải sau khi đã có mã.
      await ghi('/api/quotations/' + encodeURIComponent(maMoi) + '/items', {
        items: (q.items || []).map((it, i) => ({
          line_no: i + 1, name: it.name || '', quantity: Number(it.quantity) || 1,
          uom: it.uom || "40'", note: it.note || '',
        })),
      }, 'PUT');
      const truoc = q.id;
      S.q = await doc('/api/quotations/' + encodeURIComponent(maMoi) + '/detail');
      S.dongTach = [];
      vePhieu();
      tinhLaiGia();
      if (noiKhiXong) {
        thongBao(truoc ? `Đã lưu báo giá ${S.q.quote_no || S.q.id}.`
          : `Đã lưu nháp ${S.q.id}. Mã hiện cho khách được cấp khi gửi khách.`);
      }
      return true;
    } catch (loi) {
      thongBao('Không lưu được báo giá: ' + loi.message, true);
      return false;
    } finally {
      S.dangLuu = false;
      veThanhDay();
    }
  }

  /** Khuôn chung cho mọi lệnh chuyển trạng thái: lưu trước, rồi gọi lệnh. */
  async function lenh(duong, than, chuMacDinh, khongLuuTruoc) {
    const q = S.q;
    if (!khongLuuTruoc) {
      if (!await luuNhap(false)) return;
    }
    const ma = S.q.id || q.id;
    try {
      const goi = await apiGoi(`/api/quotations/${encodeURIComponent(ma)}/${duong}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(than || {}),
      });
      const d = goi.data || {};
      S.q = d && d.id ? d : await doc('/api/quotations/' + encodeURIComponent(ma) + '/detail');
      S.dongTach = [];
      vePhieu();
      tinhLaiGia();
      // Câu của máy chủ thắng câu viết sẵn: nó là chỗ duy nhất biết kết cục
      // thật của lệnh vừa chạy.
      thongBao(goi.message || chuMacDinh);
      return d;
    } catch (loi) {
      thongBao(loi.message, true);
      return null;
    }
  }

  async function guiKhach() {
    const bien = S.q.bien;
    const nguong = Number(S.q.target_margin
      || (S.xemTruoc && S.xemTruoc.nguong_bien) || 0.15);
    if (bien !== null && bien < nguong) {
      if (!window.confirm(`Biên ${phanTram(bien)} dưới ngưỡng ${phanTram(nguong, 0)}.\n\n`
        + 'Báo giá sẽ chuyển sang "Chờ duyệt nội bộ" thay vì gửi thẳng cho khách. Tiếp tục?')) return;
    }
    await lenh('send', {}, 'Đã xử lý xong bước gửi khách.');
  }

  async function ghiNhanChapNhan() {
    if (!window.confirm(`Ghi nhận khách chấp nhận báo giá?\n\nHệ thống sẽ sinh ngay ${soLuongHang()} `
      + `lệnh giao hàng, giá khoá ${tien(S.q.selling_price)} VNĐ/chuyến theo báo giá.`)) return;
    await lenh('accept', {}, 'Đã ghi nhận khách chấp nhận và sinh lệnh giao hàng.', true);
    chonTabPhieu(1);
    cuonToi(el('qtv2-sec-do'));
  }

  async function khachTuChoi() {
    const ly = window.prompt('Khách từ chối vì lý do gì? (ghi lại để soát giá lần sau)', '');
    if (ly === null) return;
    await lenh('reject', { reason: ly }, 'Đã đóng báo giá.', true);
  }

  async function giaHan() {
    const moi = window.prompt('Gia hạn hiệu lực đến ngày nào? (YYYY-MM-DD)', ngayHomNayCong(30));
    if (!moi) return;
    await lenh('extend', { valid_to: moi }, 'Đã gia hạn hiệu lực báo giá.', true);
  }

  async function traVeNhap() {
    const ly = window.prompt('Trả về nháp vì lý do gì?', 'Giá cần soát lại');
    if (ly === null) return;
    await lenh('return-to-draft', { reason: ly }, 'Đã trả báo giá về bản nháp.', true);
  }

  async function tachDo() {
    const q = S.q;
    if (!q.route_id) { thongBao('Chưa chọn tuyến — không tách DO được.', true); return; }
    const thieu = S.dongTach.filter(d => !d.pick).length;
    if (thieu) { thongBao(`${thieu} dòng chưa có giờ lấy hàng.`, true); return; }
    if (/^có/i.test(String(q.sealing || '').trim())) {
      const thieuSeal = S.dongTach.filter(d => !String(d.seal || '').trim()).length;
      if (thieuSeal) {
        thongBao(`${thieuSeal} dòng chưa có số niêm phong. Báo giá này khai hàng có `
          + 'niêm phong, và bước Điều phối sẽ không cho xe xuất bến khi thiếu số seal.',
        true);
        return;
      }
    }
    if (!window.confirm(`Tạo ${S.dongTach.length} lệnh giao hàng từ báo giá này?\n\n`
      + `Giá cước ${tien(q.selling_price)} VNĐ/chuyến sẽ được khoá theo báo giá và không sửa `
      + 'ở dưới vận hành.')) return;
    const dos = S.dongTach.map(d => ({
      unit: d.unit,
      pickup_at: mocGuiLen(`${d.date}T${(d.pick || '07:00').slice(0, 5)}`),
      due_at: mocGuiLen(d.due),
      seal_no: d.seal || '',
      driver_note: d.note || '',
    }));
    const goi = await lenh('split', { dos }, 'Đang tạo lệnh giao hàng…', true);
    if (goi && goi.do_ids) {
      thongBao(`Đã tạo ${goi.do_ids.length} DO · giá ${tien(goi.gia_moi_chuyen)} VNĐ/chuyến khoá `
        + 'theo báo giá. Chúng nằm ở "Lệnh giao hàng → Cần xử lý".');
      S.q = await doc('/api/quotations/' + encodeURIComponent(S.q.id || q.id) + '/detail');
      vePhieu();
      tinhLaiGia();
    }
  }

  async function nhanBan() {
    const q = S.q;
    if (!window.confirm('Nhân bản báo giá này thành một bản nháp mới?')) return;
    const goc = q;
    S.q = Object.assign(phieuTrong(), {
      customer_id: goc.customer_id, route_id: goc.route_id,
      vehicle_type_id: goc.vehicle_type_id, origin: goc.origin, destination: goc.destination,
      weight_kg: goc.weight_kg, volume_m3: goc.volume_m3, pallet_count: goc.pallet_count,
      cargo_type: goc.cargo_type, cargo_value: goc.cargo_value,
      temperature_requirement: goc.temperature_requirement,
      stacking: goc.stacking, sealing: goc.sealing, recipient_contact: goc.recipient_contact,
      price_basis: goc.price_basis, unit_price: goc.unit_price,
      min_qty_per_trip: goc.min_qty_per_trip,
      currency_code: goc.currency_code, payment_terms: goc.payment_terms,
      waiting_surcharge: goc.waiting_surcharge, trips_per_month: goc.trips_per_month,
      target_margin: goc.target_margin,
      competitor_price: goc.competitor_price,
      discount_percent: goc.discount_percent,
      notes_customer: goc.notes_customer, notes_ops: goc.notes_ops,
      // Ghi chú NỘI BỘ không nhân bản: nó thường nói về một lần thương lượng cụ
      // thể ("tối đa giảm 3%"), và mang sang một báo giá khác thì sai ngữ cảnh.
      notes_internal: '',
      items: (goc.items || []).map((it, i) => ({
        line_no: i + 1, name: it.name, quantity: it.quantity, uom: it.uom, note: it.note,
      })),
    });
    S.dongTach = [];
    vePhieu();
    tinhLaiGia();
    thongBao('Đã tạo bản nháp từ báo giá cũ. Soát lại giá rồi bấm "Lưu nháp".');
  }

  /* ------------------------------------------------ Hai bản in của báo giá ----
     · `xemPdf`     BẢN NỘI BỘ: đủ mọi thông tin đang có — cấu phần giá thành, cước,
                    biên, giá đối thủ, chiết khấu, ba ô ghi chú — để bên mình xem và chốt.
     · `phieuKhach` PHIẾU GỬI KHÁCH: chỉ những trường hệ thống cha của tập đoàn cần
                    (ảnh chủ dự án đưa 10/09): trọng lượng, tiền tệ, giá gốc, doanh thu
                    dự kiến, giá sau chiết khấu, doanh thu có chiết khấu, ngày nhập.
                    KHÔNG có giá thành, KHÔNG có biên, KHÔNG có ghi chú nội bộ. */
  /* =========================================================================
     HAI BẢN IN — áo thương hiệu EPL: đỏ #b5121b, xanh lá #3fa72f (màu logo).

     `print-color-adjust: exact` là BẮT BUỘC: thiếu nó thì trình duyệt bỏ mọi
     nền màu khi in, dải đầu trang và hàng tổng ra trắng trơn trên giấy.
     Ảnh logo phải là đường TUYỆT ĐỐI — cửa sổ in mở bằng `about:blank` nên
     đường tương đối `/static/...` không phân giải được.
     ========================================================================= */
  const LOGO = () => (typeof location !== 'undefined' ? location.origin : '') + '/static/img/logo-epl.jpg';
  const KIEU_IN = `<style>
    :root { --do:#b5121b; --do-2:#8d0d14; --do-nhat:#fdf2f2; --xanh:#3fa72f; --xanh-2:#2f7d23; --xanh-nhat:#f2faf0;
            --muc:#1e293b; --muc-2:#475569; --muc-3:#7b8796; --vien:#e4e9f0; }
    * { box-sizing:border-box; -webkit-print-color-adjust:exact; print-color-adjust:exact; }
    body { font:13px/1.55 "Segoe UI",system-ui,-apple-system,sans-serif; color:var(--muc); margin:0;
           background:#fff; }
    .to { max-width:820px; margin:0 auto; padding:26px 30px 40px; position:relative; }
    /* dải đầu trang: logo + tên công ty | tiêu đề phiếu */
    .dau { display:flex; align-items:flex-start; gap:18px; padding-bottom:14px; border-bottom:3px solid var(--do); }
    .dau .logo { width:70px; height:70px; flex:none; object-fit:contain; }
    .dau .ten { flex:1; min-width:0; }
    .dau .ten b { display:block; font-size:20px; font-weight:800; letter-spacing:.02em; color:var(--do); line-height:1.15; }
    .dau .ten span { display:block; font-size:11.5px; color:var(--muc-3); margin-top:3px; }
    .dau .ten em { display:block; font-style:normal; font-size:11.5px; color:var(--xanh-2); font-weight:700; margin-top:2px; }
    .dau .phai { text-align:right; flex:none; }
    .dau .phai h1 { margin:0; font-size:17px; font-weight:800; letter-spacing:.01em; color:var(--muc); }
    .dau .phai .ma { font-size:12.5px; color:var(--muc-2); margin-top:4px; font-variant-numeric:tabular-nums; }
    .dau .phai .ma b { color:var(--do); }
    .soc { height:4px; background:linear-gradient(90deg,var(--do) 0 55%,var(--xanh) 55% 100%); border-radius:0 0 3px 3px; }
    /* nhãn bản nội bộ + vân chìm */
    .noibo { display:inline-block; background:var(--do-nhat); color:var(--do); border:1px solid #f0b9bc;
             border-radius:999px; padding:3px 11px; font-size:11px; font-weight:800; letter-spacing:.04em; }
    .van { position:fixed; inset:0; display:grid; place-items:center; pointer-events:none; z-index:0; }
    .van span { font-size:120px; font-weight:800; color:rgba(181,18,27,.05); transform:rotate(-28deg);
                letter-spacing:.1em; white-space:nowrap; }
    .to > * { position:relative; z-index:1; }
    /* mục */
    h2 { font-size:12.5px; font-weight:800; text-transform:uppercase; letter-spacing:.06em; color:var(--muc-2);
         margin:22px 0 8px; padding-left:10px; border-left:4px solid var(--xanh); }
    .khoi { background:var(--xanh-nhat); border:1px solid #dcecd7; border-radius:10px; padding:11px 14px; }
    .khoi.do { background:var(--do-nhat); border-color:#f3d4d6; }
    .cap { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px 22px; }
    .cap div { display:flex; justify-content:space-between; gap:10px; padding:5px 0; border-bottom:1px dashed var(--vien); font-size:12.5px; }
    .cap div span { color:var(--muc-3); } .cap div b { font-weight:700; text-align:right; }
    /* bảng */
    table { width:100%; border-collapse:collapse; margin-top:4px; border:1px solid var(--vien); border-radius:10px; overflow:hidden; }
    th { background:var(--xanh-nhat); color:var(--xanh-2); font-size:10.5px; font-weight:800; text-transform:uppercase;
         letter-spacing:.05em; text-align:left; padding:8px 10px; border-bottom:1px solid #dcecd7; }
    td { border-bottom:1px solid var(--vien); padding:7px 10px; text-align:left; font-size:12.5px; }
    tr:last-child td { border-bottom:0; }
    .r { text-align:right; font-variant-numeric:tabular-nums; }
    .tong td { font-weight:800; background:var(--do-nhat); color:var(--do-2); border-top:1px solid #f0b9bc; }
    /* ô giá nổi bật trên phiếu khách */
    .gia { display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap;
           background:linear-gradient(100deg,var(--do) 0%,var(--do-2) 100%); color:#fff; border-radius:12px;
           padding:16px 20px; margin-top:6px; }
    .gia .nhan { font-size:12px; font-weight:700; letter-spacing:.05em; text-transform:uppercase; opacity:.9; }
    .gia .con { font-size:28px; font-weight:800; letter-spacing:-.01em; font-variant-numeric:tabular-nums; line-height:1.1; }
    .gia .don { font-size:12.5px; opacity:.9; }
    .gia .ck { background:rgba(255,255,255,.16); border:1px solid rgba(255,255,255,.3); border-radius:999px;
               padding:4px 12px; font-size:12px; font-weight:700; }
    .ghi { white-space:pre-wrap; background:#f8fafc; border:1px solid var(--vien); border-left:4px solid var(--xanh);
           padding:11px 13px; border-radius:0 10px 10px 0; font-size:12.5px; }
    /* chữ ký + chân trang */
    .ky { display:grid; grid-template-columns:1fr 1fr; gap:40px; margin-top:34px; page-break-inside:avoid; }
    .ky div { text-align:center; }
    .ky b { display:block; font-size:12px; font-weight:800; text-transform:uppercase; letter-spacing:.05em; color:var(--muc-2); }
    .ky small { display:block; color:var(--muc-3); font-size:11px; margin-top:2px; }
    .ky i { display:block; margin-top:58px; border-top:1px dotted var(--muc-3); font-style:normal; font-size:11px; color:var(--muc-3); padding-top:5px; }
    .chan { margin-top:26px; padding-top:12px; border-top:1px solid var(--vien); display:flex; justify-content:space-between;
            gap:14px; flex-wrap:wrap; font-size:11px; color:var(--muc-3); }
    .chan b { color:var(--do); font-weight:700; }
    @page { margin:12mm; }
    @media print { .to { padding:0; max-width:none; } body { font-size:12px; } .van span { font-size:150px; } }
  </style>`;

  /** Dải đầu trang dùng chung cho hai bản in. `nhan` là chip cạnh tiêu đề. */
  /**
   * Chữ trên PHIẾU IN phải dịch ngay lúc dựng chuỗi.
   *
   * Phiếu mở ở cửa sổ mới bằng window.open, là một tài liệu KHÁC — bộ dịch DOM
   * của ứng dụng (translateAllDOMTexts) chỉ chạy trên trang chính nên không bao
   * giờ với tới đó. Thiếu bản dịch thì lùi về tiếng Việt, không hiện tên khoá.
   */
  function TI(khoa, macDinh) {
    if (typeof window.t !== 'function') return macDinh;
    const ra = window.t(khoa);
    return (ra && ra !== khoa) ? ra : macDinh;
  }
  const MA_VUNG_IN = { vi: 'vi-VN', en: 'en-GB', la: 'lo-LA', lo: 'lo-LA' };
  /** Ngày trên phiếu theo ngôn ngữ đang chọn; `<html lang>` do changeLanguage đặt. */
  function ngayIn(d) {
    const l = (document.documentElement && document.documentElement.lang) || 'vi';
    return (d || new Date()).toLocaleDateString(MA_VUNG_IN[String(l).toLowerCase()] || 'vi-VN');
  }
  /** Đơn vị tính cước, dịch được (chuyến / tấn / kg / km / m³). */
  const KHOA_DV = { 'chuyến': 'in_dv_chuyen', 'tấn': 'in_dv_tan', 'kg': 'in_dv_kg', 'km': 'in_dv_km', 'm³': 'in_dv_m3' };
  const dvIn = don => TI(KHOA_DV[don] || '', don);

  function dauTrangIn(tieuDe, ma, dongPhu, nhan) {
    return `<div class="dau">
      <img class="logo" src="${LOGO()}" alt="EPL Logistics">
      <div class="ten"><b>EPL LOGISTICS</b><span>${esc(TI('in_tagline', 'Vận tải và giao nhận · Việt Nam – Lào'))}</span>${(document.documentElement.lang || 'vi').toLowerCase().startsWith('lo') ? '' : `<em>ການຂົນສົ່ງ ແລະ ການຈັດສົ່ງ</em>`}</div>
      <div class="phai"><h1>${esc(tieuDe)}</h1><div class="ma">${ma}</div>${nhan ? `<div style="margin-top:6px">${nhan}</div>` : ''}</div>
    </div><div class="soc"></div>
    ${dongPhu ? `<div style="margin-top:10px;font-size:12.5px;color:var(--muc-2)">${dongPhu}</div>` : ''}`;
  }

  function moCuaSoIn(tieuDe, than) {
    const w = window.open('', '_blank');
    if (!w) { thongBao('Trình duyệt chặn cửa sổ mới — cho phép rồi bấm lại.', true); return; }
    w.document.write(`<!doctype html><html lang="vi"><meta charset="utf-8"><title>${esc(tieuDe)}</title>${KIEU_IN}<body><div class="to">${than}</div>`);
    w.document.close();
    // Chờ ẢNH LOGO tải xong mới gọi in: gọi sớm thì hộp in chụp trang khi logo
    // còn trống, và bản in ra mất logo.
    const inRa = () => { try { w.print(); } catch (e) { /* người dùng tự in */ } };
    const anh = w.document.querySelector('img.logo');
    if (anh && !anh.complete) { anh.addEventListener('load', () => setTimeout(inRa, 120)); anh.addEventListener('error', () => setTimeout(inRa, 120)); setTimeout(inRa, 2500); }
    else setTimeout(inRa, 400);
  }

  function xemPdf() {
    const q = S.q;
    const rt = tuyenTheoMa(q.route_id);
    const xt = S.xemTruoc;
    const ty = tyGia(q.currency_code) || 1;
    const sym = kyHieu(q.currency_code);
    const dongCua = loai => (xt && xt.cac_dong || []).filter(d => d.loai === loai)
      .map(d => `<tr><td>${esc(d.nhan)}</td><td class="r">${tien(d.don_gia / ty)}</td>
        <td>${esc(d.nhan_voi)}</td><td class="r">${tien(d.thanh_tien / ty)}</td></tr>`).join('');
    const dv = DON_VI_CUOC.find(x => x[0] === (q.price_basis || 'per_trip')) || DON_VI_CUOC[0];
    const bien = q.bien === null || q.bien === undefined ? '—' : phanTram(q.bien);
    const ck = Number(q.discount_percent || 0);
    moCuaSoIn(`Báo giá ${q.quote_no || q.id} — bản nội bộ`, `
      <div class="van" aria-hidden="true"><span>${esc(TI('in_van_noi_bo', 'NỘI BỘ'))}</span></div>
      ${dauTrangIn(TI('in_tieu_de_noi_bo', 'BÁO GIÁ CƯỚC VẬN CHUYỂN'),
    `<b>${esc(q.quote_no || q.id || TI('in_ban_nhap', 'bản nháp'))}</b> · ${esc(TI('in_ngay', 'ngày'))} ${ngayIn()}`,
    `${esc(TI('in_trang_thai', 'Trạng thái'))} <b>${esc(q.canonical_status || '')}</b> · ${esc(TI('in_nvkd', 'NVKD'))} ${esc(q.sales_rep || '')}`,
    `<span class="noibo">${esc(TI('in_nhan_noi_bo', 'BẢN NỘI BỘ — không gửi khách'))}</span>`)}
      <h2>${esc(TI('in_kh_va_hanh_trinh', 'Khách hàng và hành trình'))}</h2>
      <div class="khoi cap">
        <div><span>${esc(TI('in_khach_hang', 'Khách hàng'))}</span><b>${esc(tenKhach(q.customer_id))}</b></div>
        <div><span>${esc(TI('in_tuyen', 'Tuyến'))}</span><b>${esc((rt && (rt.name || rt.id)) || '—')}</b></div>
        <div><span>${esc(TI('in_phuong_tien', 'Phương tiện'))}</span><b>${esc(tenLoaiXe(q.vehicle_type_id))}</b></div>
        <div><span>${esc(TI('in_quang_duong', 'Quãng đường'))}</span><b>${xt ? so(xt.km) + ' km' : '—'}</b></div>
        <div><span>${esc(TI('in_hang', 'Hàng'))}</span><b>${so(Number(q.weight_kg || 0) / 1000)} ${esc(TI('in_tan', 'tấn'))}${
      q.volume_m3 ? ' · ' + so(q.volume_m3) + ' m³' : ''}${q.pallet_count ? ' · ' + so(q.pallet_count) + ' pallet' : ''}</b></div>
        <div><span>${esc(TI('in_loai_hang', 'Loại hàng'))}</span><b>${esc(q.cargo_type || '—')}</b></div>
      </div>
      <h2>${esc(TI('in_muc_chi', 'Khoản mục giá thành một chuyến (chi)'))}</h2>
      <table><thead><tr><th>${esc(TI('in_khoan_muc', 'Khoản mục'))}</th><th class="r">${esc(TI('in_don_gia', 'Đơn giá'))}</th><th>${esc(TI('in_nhan_voi', 'Nhân với'))}</th>
        <th class="r">${esc(TI('in_thanh_tien', 'Thành tiền'))} (${esc(sym)})</th></tr></thead><tbody>${dongCua('chi')}
        <tr class="tong"><td colspan="3">${esc(TI('in_gia_thanh_chuyen', 'Giá thành một chuyến'))}</td>
          <td class="r">${tien(Number(q.total_cost || 0) / ty)}</td></tr></tbody></table>
      ${dongCua('thu') ? `<h2>${esc(TI('in_muc_thu', 'Khoản mục doanh thu trong công thức (thu · tham khảo)'))}</h2>
      <table><tbody>${dongCua('thu')}</tbody></table>` : ''}
      <h2>${esc(TI('in_cuoc_va_bien', 'Cước và biên'))}</h2>
      <table><tbody>
        <tr><td>${esc(TI('in_don_gia_cuoc', 'Đơn giá cước (giá cuối)'))}</td><td class="r">${tien(Number(q.unit_price || 0) / ty)} ${esc(sym)} / ${esc(dvIn(dv[2]))}</td></tr>
        ${ck > 0 ? `<tr><td>${esc(TI('in_gia_goc_truoc_ck', 'Giá gốc trước chiết khấu'))} ${so(ck * 100)}%</td><td class="r">${tien(Number(q.unit_price || 0) / (1 - ck) / ty)} ${esc(sym)} / ${esc(dvIn(dv[2]))}</td></tr>` : ''}
        <tr class="tong"><td>${esc(TI('in_cuoc_mot_chuyen', 'Cước một chuyến'))}</td><td class="r">${tien(Number(q.selling_price || 0) / ty)} ${esc(sym)}</td></tr>
        <tr><td>${esc(TI('in_loi_nhuan_chuyen', 'Lợi nhuận một chuyến'))}</td><td class="r">${tien((Number(q.selling_price || 0) - Number(q.total_cost || 0)) / ty)} ${esc(sym)} · ${esc(TI('in_bien', 'biên'))} ${bien}</td></tr>
        <tr><td>${esc(TI('in_bien_muc_tieu', 'Biên mục tiêu'))}</td><td class="r">${q.target_margin ? phanTram(q.target_margin, 0) + ' (' + TI('in_rieng_khach_nay', 'riêng khách này') + ')' : TI('in_theo_cong_ty', 'theo công ty')}</td></tr>
        <tr><td>${esc(TI('in_gia_doi_thu', 'Giá đối thủ khách nói ra'))}</td><td class="r">${Number(q.competitor_price) > 0 ? tien(q.competitor_price) + ' ' + TI('in_vnd_moi_chuyen', 'VNĐ/chuyến') : '—'}</td></tr>
        <tr><td>${esc(TI('in_phu_phi_cho', 'Phụ phí chờ quá 2 giờ'))}</td><td class="r">${tien(Number(q.waiting_surcharge || 0) / ty)} ${esc(sym)}/${esc(TI('in_gio', 'giờ'))}</td></tr>
        <tr><td>${esc(TI('in_dieu_khoan_tt', 'Điều khoản thanh toán'))}</td><td class="r">${esc(q.payment_terms || '—')}</td></tr>
        <tr><td>${esc(TI('in_hieu_luc_den', 'Hiệu lực đến'))}</td><td class="r">${esc(q.valid_to || '—')}</td></tr>
        <tr><td>${esc(TI('in_so_chuyen_thang', 'Số chuyến / tháng dự kiến'))}</td><td class="r">${q.trips_per_month || '—'}</td></tr>
        ${q.currency_code && q.currency_code !== 'VND'
      ? `<tr><td>${esc(TI('in_ty_gia', 'Tỷ giá áp dụng'))}</td><td class="r">1 ${esc(q.currency_code)} = ${tien(ty)} VNĐ</td></tr>` : ''}
      </tbody></table>
      ${(q.items || []).length ? `<h2>${esc(TI('in_hang_hoa', 'Hàng hoá'))}</h2><table><thead><tr><th>#</th><th>${esc(TI('in_ten_hang', 'Tên hàng'))}</th><th class="r">${esc(TI('in_so_luong', 'Số lượng'))}</th><th>${esc(TI('in_dvt', 'ĐVT'))}</th><th>${esc(TI('in_ghi_chu', 'Ghi chú'))}</th></tr></thead><tbody>${
      (q.items || []).map((it, i) => `<tr><td>${i + 1}</td><td>${esc(it.name || '')}</td><td class="r">${so(it.quantity)}</td><td>${esc(it.uom || '')}</td><td>${esc(it.note || '')}</td></tr>`).join('')}</tbody></table>` : ''}
      ${q.notes_customer ? `<h2>${esc(TI('in_ghi_chu_khach', 'Ghi chú gửi khách'))}</h2><div class="ghi">${esc(q.notes_customer)}</div>` : ''}
      ${q.notes_ops ? `<h2>${esc(TI('in_ghi_chu_van_hanh', 'Ghi chú vận hành'))}</h2><div class="ghi">${esc(q.notes_ops)}</div>` : ''}
      ${q.notes_internal ? `<h2>${esc(TI('in_ghi_chu_noi_bo', 'Ghi chú nội bộ'))}</h2><div class="ghi">${esc(q.notes_internal)}</div>` : ''}
      <div class="chan"><span><b>EPL LOGISTICS</b> · ${esc(TI('in_chan_noi_bo', 'bản nội bộ, không gửi khách'))}</span>
        <span>${esc(TI('in_chan_nguon', 'Số liệu lấy từ công thức giá thành ở Dữ liệu gốc tại thời điểm in'))} · ${esc(TI('in_chan_gui_khach', 'gửi khách dùng nút “Phiếu gửi khách”'))}</span></div>`);
  }

  function phieuKhach() {
    const q = S.q;
    const ty = tyGia(q.currency_code) || 1;
    const tienTe = kyHieu(q.currency_code || 'VND');
    const ck = Number(q.discount_percent || 0);
    const donGiaCuoi = Number(q.unit_price || 0) / ty;
    const cuocCuoi = Number(q.selling_price || 0) / ty;
    const heSo = ck > 0 && ck < 1 ? 1 / (1 - ck) : 1;
    const dv = DON_VI_CUOC.find(x => x[0] === (q.price_basis || 'per_trip')) || DON_VI_CUOC[0];
    // Tuyến và loại xe là hai thứ khách cần đọc để biết mình đang mua chuyến nào.
    // Số km đi qua kmTuyen() để in đúng quãng đường mà cước được tính theo.
    const rt = tuyenTheoMa(q.route_id);
    const km = kmTuyen(rt);
    const tenTuyen = (rt && (rt.name || rt.id)) || '—';
    const dong = (nhan, giaTri) => `<tr><td>${nhan}</td><td class="r">${giaTri}</td></tr>`;
    moCuaSoIn(`Báo giá ${q.quote_no || q.id} — phiếu gửi khách`, `
      ${dauTrangIn(TI('in_tieu_de_khach', 'THÔNG TIN VẬN CHUYỂN'),
    `<b>${esc(q.quote_no || q.id || '')}</b> · ${esc(TI('in_ngay', 'ngày'))} ${ngayIn()}`,
    `${esc(TI('in_kinh_gui', 'Kính gửi'))} <b>${esc(tenKhach(q.customer_id))}</b>`, '')}
      <h2>${esc(TI('in_cuoc_van_chuyen', 'Cước vận chuyển'))}</h2>
      <div class="gia">
        <div><div class="nhan">${esc(TI('in_don_gia', 'Đơn giá'))}</div><div class="con">${tien(donGiaCuoi)} ${esc(tienTe)}</div><div class="don">/ ${esc(dvIn(dv[2]))}</div></div>
        ${ck > 0 ? `<div class="ck">${esc(TI('in_da_chiet_khau', 'Đã chiết khấu'))} ${so(ck * 100)}%</div>` : ''}
      </div>
      <h2>${esc(TI('in_chi_tiet', 'Chi tiết'))}</h2>
      <table><tbody>
        ${dong(TI('in_tuyen_duong', 'Tuyến đường'), esc(tenTuyen) + (km > 0 ? ' · ' + so(km) + ' km' : ''))}
        ${dong(TI('in_loai_xe', 'Loại xe'), esc(tenLoaiXe(q.vehicle_type_id)))}
        ${dong(TI('in_trong_luong', 'Trọng lượng'), so(Number(q.weight_kg || 0) / 1000) + ' ' + TI('in_tan_hoa', 'Tấn'))}
        ${dong(TI('in_tien_te_tt', 'Tiền tệ thanh toán'), esc(tienTe))}
        ${dong(TI('in_gia_goc', 'Giá gốc'), tien(donGiaCuoi * heSo) + ' ' + esc(tienTe) + ' / ' + esc(dvIn(dv[2])))}
        ${dong(TI('in_gia_goc_sau_ck', 'Giá gốc sau chiết khấu') + (ck > 0 ? ' (' + so(ck * 100) + '%)' : ''), tien(donGiaCuoi) + ' ' + esc(tienTe) + ' / ' + esc(dvIn(dv[2])))}
        ${dong(TI('in_chiet_khau_khach', 'Chiết khấu cho khách') + (ck > 0 ? ' (' + so(ck * 100) + '%)' : ''),
      ck > 0
        ? '− ' + tien(donGiaCuoi * heSo - donGiaCuoi) + ' ' + esc(tienTe) + ' / ' + esc(dvIn(dv[2]))
        : TI('in_khong_chiet_khau', 'Không có chiết khấu'))}
        ${dong(TI('in_ngay_nhap', 'Ngày nhập dữ liệu'), ngayIn())}
        <tr class="tong"><td>${esc(TI('in_bao_gia_hieu_luc', 'Báo giá có hiệu lực đến'))}</td><td class="r">${esc(q.valid_to || '—')}</td></tr>
      </tbody></table>
      ${q.notes_customer ? `<h2>${esc(TI('in_ghi_chu', 'Ghi chú'))}</h2><div class="ghi">${esc(q.notes_customer)}</div>` : ''}
      <div class="ky">
        <div><b>${esc(TI('in_khach_hang', 'Khách hàng'))}</b><small>${esc(TI('in_ky_ten', 'Ký, ghi rõ họ tên'))}</small><i>${esc(TI('in_ben_nhan', 'Bên nhận dịch vụ'))}</i></div>
        <div><b>EPL Logistics</b><small>${esc(q.sales_rep || TI('in_nvkd_dai', 'Nhân viên kinh doanh'))}</small><i>${esc(TI('in_ben_cung_cap', 'Bên cung cấp dịch vụ'))}</i></div>
      </div>
      <div class="chan"><span><b>EPL LOGISTICS</b> · ${esc(TI('in_chan_khach', 'Vận tải và giao nhận Việt Nam – Lào'))}</span>
        <span>${esc(TI('in_bao_gia_hieu_luc', 'Báo giá có hiệu lực đến'))} ${esc(q.valid_to || '—')}</span></div>`);
  }

  /* =========================================================================
     CỬA VÀO
     ========================================================================= */

  window.BaoGiaV2 = {
    nap: napDanhSach,
    moPhieu,
    dongPhieu,
    /** Cho `khung-moi.js` và các nút cũ gọi "+ Báo giá". */
    moPhieuMoi: () => moPhieu(null),
    _trangThai: S,
  };

  // Thanh đáy chỉ được hiện khi đang mở phiếu. Rời màn CRM sang màn khác mà
  // thanh còn nằm đó thì nó che nút của màn kia.
  const chuyenManCu = window.switchView;
  if (typeof chuyenManCu === 'function') {
    window.switchView = function (man) {
      const ra = chuyenManCu.apply(this, arguments);
      const sb = el('qtv2-sbar');
      if (sb && man !== 'crm-sales') sb.classList.add('qt-hide');
      if (man === 'crm-sales') napDanhSach();
      return ra;
    };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => { if (el(GOC)) napDanhSach(); });
  } else if (el(GOC)) {
    napDanhSach();
  }
})();

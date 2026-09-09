/* ==========================================================================
   TÀI XẾ & BẰNG LÁI — thẻ dữ liệu gốc.

   VÌ SAO MÀN NÀY PHẢI CÓ. Điều phối xe CHẶN tài xế không đủ bằng lái:
   `tms_dispatch_service` bật `DRIVER_LICENSE_INVALID` ở hai chỗ (xếp nguồn lực
   và điều lệnh vận chuyển). Cửa chặn đó còn trả về gợi ý `["master-data/drivers"]`
   — tức máy chủ BẢO người dùng sang màn Tài xế mà sửa. Nhưng dự án chưa có màn
   dữ liệu gốc nào cho tài xế, và không có ô nào khai được bằng lái. Hệ quả
   thật: người vận hành gặp chặn thì KHÔNG CÓ CÁCH NÀO TỰ SỬA — phải nhờ người
   viết mã chạy tệp lệnh, hoặc sửa thẳng vào cơ sở dữ liệu. Một cái cổng khoá
   mà không phát chìa.

   BA QUYẾT ĐỊNH THIẾT KẾ, và lý do:

     1. KẾT LUẬN TRÊN MÀN PHẢI TRÙNG ĐÚNG ĐIỀU KIỆN CỦA CỬA CHẶN. `ketLuan()`
        dưới đây sao lại y nguyên năm điều kiện của `tms_dispatch_service`. Nếu
        hai bên lệch nhau thì màn hình báo "đủ điều kiện" rồi điều phối vẫn
        chặn, và người dùng mất niềm tin vào cả hai. Sửa cửa chặn thì phải sửa
        cả hàm này — có bài kiểm giữ hai bên khớp.

     2. XÉT THEO MỘT NGÀY CHỌN ĐƯỢC, không phải hôm nay. Cửa chặn so hiệu lực
        với NGÀY CHẠY CHUYẾN, không phải ngày hôm nay. Nên một bằng còn hiệu
        lực hôm nay mà hết hạn sau mười ngày vẫn chặn chuyến của tuần sau. Ô
        "Xét theo ngày" cho người xếp lịch hỏi đúng câu họ cần: "chuyến ngày
        20/10 có bị chặn không".

     3. SỬA HẠNG BẰNG THÌ GHI CẢ HAI CHỖ. Cửa chặn đòi
        `giấy_phép.license_type` BẰNG `tài_xế.license_type`. Hai giá trị nằm ở
        hai bảng, và `POST /driver-qualifications` chỉ ghi bảng giấy phép. Nên
        khi người dùng đổi hạng, màn này ghi thêm một lượt `POST /api/drivers`
        để hai bên không trôi khỏi nhau — kèm cảnh báo trên phiếu, vì đây là
        thứ người dùng không thể tự suy ra.

   CẨN THẬN VỚI `POST /api/drivers`: nó là upsert và ghi đè `phone`, `role`,
   `shift`, `assigned_vehicle` bằng GIÁ TRỊ MẶC ĐỊNH nếu payload không có. Nên
   phải gửi TRỌN bản ghi đọc được từ `GET /api/drivers`, không gửi lẻ một
   trường. Gửi lẻ là sửa bằng lái xong thì mất số điện thoại tài xế.
   ========================================================================== */

(function () {
  'use strict';

  const GOC = 'md-tab-drivers';
  const NGUONG_SAP_HET = 60;          // ngày — mốc gọi là "sắp hết hạn"
  const el = id => document.getElementById(id);
  const base = () => (window.API_BASE || window.location.origin || '');

  /* ------------------------------------------------------------- chữ và số -- */

  function esc(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  /** `2027-10-14T00:00:00` -> `14/10/2027`. Trả `—` nếu không đọc được. */
  function ngayVN(s) {
    const d = docNgay(s);
    if (!d) return '—';
    return d.toLocaleDateString('vi-VN');
  }

  /**
   * Đọc một mốc thời gian thành NGÀY, bỏ hẳn phần giờ.
   *
   * Cửa chặn ở máy chủ so `.date()` với `.date()`, nên mọi so sánh ở đây cũng
   * phải ở mức ngày. So ở mức giờ là sai lệch một ngày với những bản ghi lưu
   * `valid_to` vào lúc 00:00 — bằng hết hạn 14/10 thì chuyến ngày 14/10 vẫn
   * hợp lệ theo máy chủ (`valid_to.date() < trip_date` là sai khi bằng nhau).
   */
  function docNgay(s) {
    if (!s) return null;
    const chu = String(s).slice(0, 10);
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(chu);
    if (!m) return null;
    return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  }

  function ngayIso(d) {
    const x = new Date(d.getTime() - d.getTimezoneOffset() * 60000);
    return x.toISOString().slice(0, 10);
  }

  function homNay() {
    const d = new Date();
    return new Date(d.getFullYear(), d.getMonth(), d.getDate());
  }

  function soNgayCach(a, b) {
    return Math.round((b.getTime() - a.getTime()) / 86400000);
  }

  /* ------------------------------------------------------------ gọi máy chủ -- */

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
  const ghi = (duong, than) => api(duong, {
    method: 'POST', body: JSON.stringify(than === undefined ? {} : than),
  });

  /**
   * Kéo HẾT bằng lái, không dừng ở trang đầu.
   *
   * Màn này kết luận "ai thiếu bằng" bằng cách trừ danh sách bằng lái ra khỏi
   * danh sách tài xế. Thiếu một trang là kết luận sai cho cả trang đó — nên
   * đây là chỗ tuyệt đối không được cắt ngắn.
   */
  async function keoHetGiayPhep() {
    const ds = [];
    let trang = 1;
    let tong = Infinity;
    while (ds.length < tong && trang <= 50) {
      const goi = await doc(`/api/tms/driver-qualifications?paginated=true&page=${trang}&page_size=200`);
      const phan = Array.isArray(goi) ? goi : (goi && goi.items) || [];
      ds.push(...phan);
      tong = goi && isFinite(Number(goi.total)) ? Number(goi.total) : ds.length;
      if (!phan.length || phan.length < 200) break;
      trang += 1;
    }
    return ds;
  }

  function thongBao(chu, loi) {
    if (typeof window.showToast === 'function') { window.showToast(chu); return; }
    if (loi) console.error(chu); else console.log(chu);
  }

  /* ------------------------------------------------------------- trạng thái -- */

  const S = {
    taiXe: [],
    giayPhep: [],
    ngayXet: ngayIso(homNay()),
    loc: '',            // '' | 'thieu' | 'het-han' | 'sap-het' | 'lech-hang'
    tim: '',
    dangSua: null,      // mã tài xế đang mở phiếu
    dangNap: false,
    daDung: false,
  };

  const gpCua = maTaiXe => S.giayPhep.find(g => String(g.driver_id) === String(maTaiXe)) || null;

  /* ==========================================================================
     KẾT LUẬN — bản sao Y NGUYÊN năm điều kiện của cửa chặn điều phối.

     Nguyên văn ở `backend/app/services/tms_dispatch_service.py`:

         if (not qualification or qualification.status != "active"
                 or qualification.valid_from.date() > trip_date
                 or qualification.valid_to.date() < trip_date
                 or qualification.license_type != driver.license_type):
             raise conflict("DRIVER_LICENSE_INVALID", ...)

     Thứ tự kiểm ở đây giữ đúng thứ tự đó, để khi một tài xế vướng nhiều lỗi
     cùng lúc thì màn hình nêu đúng cái lỗi mà máy chủ sẽ nêu.
     ========================================================================== */

  function ketLuan(tx, gp, ngayXet) {
    const ngay = docNgay(ngayXet) || homNay();
    if (!gp) {
      return {
        ma: 'thieu', chan: true, mau: 'do',
        chu: 'Thiếu bằng lái — điều phối sẽ chặn',
        vi: 'Chưa có dòng bằng lái nào cho tài xế này.',
      };
    }
    if (String(gp.status || '') !== 'active') {
      return {
        ma: 'khong-hieu-luc', chan: true, mau: 'do',
        chu: 'Bằng lái không hiệu lực',
        vi: `Trạng thái đang là "${gp.status || '(trống)'}", cửa chặn chỉ nhận "active".`,
      };
    }
    const tu = docNgay(gp.valid_from);
    const den = docNgay(gp.valid_to);
    if (tu && soNgayCach(tu, ngay) < 0) {
      return {
        ma: 'chua-hieu-luc', chan: true, mau: 'do',
        chu: 'Chưa tới ngày hiệu lực',
        vi: `Bằng chỉ có hiệu lực từ ${ngayVN(gp.valid_from)}.`,
      };
    }
    if (den && soNgayCach(ngay, den) < 0) {
      return {
        ma: 'het-han', chan: true, mau: 'do',
        chu: 'Đã hết hạn',
        vi: `Hết hạn ngày ${ngayVN(gp.valid_to)}.`,
      };
    }
    if (String(gp.license_type || '') !== String(tx.license_type || '')) {
      return {
        ma: 'lech-hang', chan: true, mau: 'do',
        chu: 'Lệch hạng với hồ sơ tài xế',
        vi: `Hồ sơ tài xế ghi "${tx.license_type || '(trống)'}" còn giấy phép ghi `
          + `"${gp.license_type || '(trống)'}". Cửa chặn đòi hai giá trị bằng nhau.`,
      };
    }
    const conLai = den ? soNgayCach(ngay, den) : null;
    if (conLai !== null && conLai <= NGUONG_SAP_HET) {
      return {
        ma: 'sap-het', chan: false, mau: 'vang',
        chu: `Còn ${conLai} ngày`,
        vi: `Hết hạn ${ngayVN(gp.valid_to)}. Chuyến xếp sau ngày đó sẽ bị chặn.`,
      };
    }
    return {
      ma: 'du', chan: false, mau: 'xanh',
      chu: 'Đủ điều kiện',
      vi: den ? `Còn hiệu lực tới ${ngayVN(gp.valid_to)}.` : 'Còn hiệu lực.',
    };
  }

  window.EplBangLai = { ketLuan, NGUONG_SAP_HET };

  /* -------------------------------------------------------------- dựng khung -- */

  function dungKhung() {
    const goc = el(GOC);
    if (!goc || S.daDung) return !!goc;
    goc.innerHTML = `
      <div class="btl">
        <header class="btl-dau">
          <div>
            <h3>Tài xế &amp; bằng lái</h3>
            <p>Điều phối xe <b>chặn</b> tài xế không đủ bằng lái. Khai và gia hạn bằng ở
               đây; kết luận trên bảng dùng đúng điều kiện mà điều phối kiểm.</p>
          </div>
          <div class="btl-dau-nut">
            <label class="btl-ngay">Xét theo ngày
              <input id="btl-ngay" type="date" value="${esc(S.ngayXet)}">
            </label>
            <button id="btl-tai-lai" type="button" class="btl-nut btl-nut-phu">
              <i class="fa-solid fa-rotate"></i> Tải lại
            </button>
            <button id="btl-them-tx" type="button" class="btl-nut btl-nut-phu">
              <i class="fa-solid fa-user-plus"></i> Thêm tài xế
            </button>
            <button id="btl-khai" type="button" class="btl-nut btl-nut-chinh">
              <i class="fa-solid fa-id-card"></i> Khai bằng lái
            </button>
          </div>
        </header>

        <div id="btl-canh-bao" class="btl-canh-bao" hidden></div>
        <div id="btl-kpi" class="btl-kpi"></div>

        <div class="btl-thanh-loc">
          <input id="btl-tim" type="search" placeholder="Tìm theo tên hoặc mã tài xế…"
                 value="${esc(S.tim)}">
          <span id="btl-dem" class="btl-dem"></span>
        </div>

        <div class="btl-bang-khung">
          <table class="btl-bang">
            <thead>
              <tr>
                <th>Tài xế</th>
                <th>Hạng trên hồ sơ</th>
                <th>Hạng trên giấy phép</th>
                <th>Hiệu lực</th>
                <th>Trạng thái</th>
                <th>Kết luận</th>
                <th></th>
              </tr>
            </thead>
            <tbody id="btl-rows"></tbody>
          </table>
        </div>
      </div>

      <div id="btl-phieu" class="btl-phieu" hidden>
        <div class="btl-phieu-nen" data-dong="1"></div>
        <form id="btl-form" class="btl-phieu-hop">
          <div class="btl-phieu-dau">
            <strong id="btl-phieu-ten">Khai bằng lái</strong>
            <button type="button" class="btl-phieu-x" data-dong="1" aria-label="Đóng">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>
          <div class="btl-phieu-than">
            <label class="btl-o">Tài xế
              <select id="btl-f-taixe" required></select>
            </label>
            <label class="btl-o">Hạng bằng
              <input id="btl-f-hang" type="text" required
                     placeholder="Ví dụ: Hạng FC" list="btl-hang-goi">
              <datalist id="btl-hang-goi"></datalist>
              <small id="btl-f-hang-nhac" class="btl-nhac"></small>
            </label>
            <div class="btl-o-doi">
              <label class="btl-o">Hiệu lực từ
                <input id="btl-f-tu" type="date" required>
              </label>
              <label class="btl-o">Hết hạn
                <input id="btl-f-den" type="date" required>
              </label>
            </div>
            <label class="btl-o">Trạng thái
              <select id="btl-f-trangthai">
                <option value="active">active — đang hiệu lực</option>
                <option value="suspended">suspended — tạm giữ</option>
                <option value="revoked">revoked — đã thu hồi</option>
              </select>
              <small class="btl-nhac">Chỉ <b>active</b> mới qua được cửa điều phối.</small>
            </label>
            <div id="btl-f-loi" class="btl-loi" hidden></div>
          </div>
          <div class="btl-phieu-day">
            <button type="button" class="btl-nut btl-nut-phu" data-dong="1">Hủy</button>
            <button id="btl-f-luu" type="submit" class="btl-nut btl-nut-chinh">
              <i class="fa-solid fa-floppy-disk"></i> Lưu bằng lái
            </button>
          </div>
        </form>
      </div>`;
    S.daDung = true;
    ganSuKien();
    return true;
  }

  /* ------------------------------------------------------------------ vẽ ---- */

  function danhSachHien() {
    const tim = S.tim.trim().toLowerCase();
    return S.taiXe.filter(tx => {
      if (tim) {
        const chu = `${tx.id || ''} ${tx.name || ''}`.toLowerCase();
        if (!chu.includes(tim)) return false;
      }
      if (!S.loc) return true;
      const kl = ketLuan(tx, gpCua(tx.id), S.ngayXet);
      if (S.loc === 'het-han') return kl.ma === 'het-han' || kl.ma === 'chua-hieu-luc' || kl.ma === 'khong-hieu-luc';
      return kl.ma === S.loc;
    });
  }

  function demNhom() {
    const d = { tong: S.taiXe.length, thieu: 0, 'het-han': 0, 'sap-het': 0, 'lech-hang': 0 };
    S.taiXe.forEach(tx => {
      const kl = ketLuan(tx, gpCua(tx.id), S.ngayXet);
      if (kl.ma === 'thieu') d.thieu += 1;
      else if (kl.ma === 'het-han' || kl.ma === 'chua-hieu-luc' || kl.ma === 'khong-hieu-luc') d['het-han'] += 1;
      else if (kl.ma === 'sap-het') d['sap-het'] += 1;
      if (kl.ma === 'lech-hang') d['lech-hang'] += 1;
    });
    return d;
  }

  function veKpi() {
    const host = el('btl-kpi');
    if (!host) return;
    const d = demNhom();
    const the = [
      ['', 'Tổng tài xế', d.tong, 'toàn bộ nhân sự lái xe', 'lam'],
      ['thieu', 'Thiếu bằng lái', d.thieu, 'điều phối sẽ chặn ngay', 'do'],
      ['het-han', 'Hết hạn / không hiệu lực', d['het-han'], 'phải gia hạn mới đi được', 'do'],
      ['sap-het', `Sắp hết hạn (≤ ${NGUONG_SAP_HET} ngày)`, d['sap-het'], 'chuyến xếp xa sẽ bị chặn', 'vang'],
      ['lech-hang', 'Lệch hạng với hồ sơ', d['lech-hang'], 'hai bảng ghi hai hạng khác nhau', 'do'],
    ];
    // Thẻ không có ai thì làm mờ và KHÔNG cho bấm, kèm chú giải nói rõ lý do —
    // cùng khuôn với dải thẻ ở màn Chuyến và màn Điều phối. Cho bấm rồi hiện
    // bảng trống thì người dùng phải thử mới biết là không có ai.
    host.innerHTML = the.map(([ma, nhan, so, phu, mau]) => {
      const tat = ma !== '' && !so;
      return `<button type="button" class="btl-the ${mau}${S.loc === ma ? ' on' : ''}"
        ${tat ? 'disabled title="Không có tài xế nào trong nhóm này"'
      : `data-loc="${esc(ma)}" title="Bấm để lọc bảng theo nhóm này"`}>
        <span>${esc(nhan)}</span><b>${Number(so).toLocaleString('vi-VN')}</b>
        <small>${esc(phu)}</small></button>`;
    }).join('');
  }

  function veBang() {
    const host = el('btl-rows');
    if (!host) return;
    const ds = danhSachHien();
    const dem = el('btl-dem');
    if (dem) {
      dem.textContent = ds.length === S.taiXe.length
        ? `${ds.length} tài xế`
        : `${ds.length} / ${S.taiXe.length} tài xế`;
    }
    if (!ds.length) {
      host.innerHTML = `<tr><td colspan="7" class="btl-trong">${
        S.dangNap ? 'Đang tải…' : 'Không có tài xế nào khớp bộ lọc.'}</td></tr>`;
      return;
    }
    host.innerHTML = ds.map(tx => {
      const gp = gpCua(tx.id);
      const kl = ketLuan(tx, gp, S.ngayXet);
      const lech = kl.ma === 'lech-hang';
      return `<tr>
        <td>
          <div class="btl-ten">${esc(tx.name || tx.id)}</div>
          <div class="btl-ma">${esc(tx.id)}${tx.role ? ' · ' + esc(tx.role) : ''}</div>
        </td>
        <td>${esc(tx.license_type || '—')}</td>
        <td class="${lech ? 'btl-lech' : ''}">${gp ? esc(gp.license_type || '—') : '<i>chưa khai</i>'}</td>
        <td>${gp ? `${ngayVN(gp.valid_from)} → ${ngayVN(gp.valid_to)}` : '—'}</td>
        <td>${gp ? esc(gp.status || '—') : '—'}</td>
        <td>
          <span class="btl-dau-cham ${kl.mau}">${esc(kl.chu)}</span>
          <div class="btl-vi">${esc(kl.vi)}</div>
        </td>
        <td class="btl-cot-nut">
          <button type="button" class="btl-nut btl-nut-nho" data-hoso="${esc(tx.id)}"
                  title="Sửa tên, số điện thoại, vai trò, hạng bằng, ca làm">Hồ sơ</button>
          <button type="button" class="btl-nut btl-nut-nho btl-nut-chinh" data-sua="${esc(tx.id)}">
            ${gp ? 'Sửa bằng' : 'Khai bằng'}
          </button>
        </td>
      </tr>`;
    }).join('');
  }

  function veCanhBao(chu) {
    const o = el('btl-canh-bao');
    if (!o) return;
    if (!chu) { o.hidden = true; o.textContent = ''; return; }
    o.hidden = false;
    o.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> ${esc(chu)}`;
  }

  function ve() {
    veKpi();
    veBang();
  }

  /* ------------------------------------------------------------------ nạp ---- */

  async function nap() {
    if (!dungKhung()) return;
    S.dangNap = true;
    veBang();
    try {
      const [taiXe, giayPhep] = await Promise.all([
        doc('/api/drivers'),
        keoHetGiayPhep(),
      ]);
      S.taiXe = (Array.isArray(taiXe) ? taiXe : []).slice().sort((a, b) =>
        String(a.name || a.id).localeCompare(String(b.name || b.id), 'vi'));
      S.giayPhep = Array.isArray(giayPhep) ? giayPhep : [];
      veCanhBao('');
    } catch (e) {
      veCanhBao(`Không tải được dữ liệu bằng lái: ${e.message} — bảng dưới đây có thể `
        + 'chưa đầy đủ, đừng dựa vào nó để kết luận ai thiếu bằng.');
    } finally {
      S.dangNap = false;
      ve();
    }
  }

  /* ----------------------------------------------------------------- phiếu --- */

  function goiHang() {
    // Gợi ý hạng bằng lấy từ DỮ LIỆU THẬT đang có, không phải một danh sách
    // viết cứng: hồ sơ tài xế của dự án đang dùng cả "Hạng FC" và "FC", và một
    // danh sách cố định sẽ đẩy người dùng khai lệch với hồ sơ — đúng cái lỗi
    // "lệch hạng" mà màn này để chữa.
    const t = new Set();
    S.taiXe.forEach(x => { if (x.license_type) t.add(String(x.license_type)); });
    S.giayPhep.forEach(x => { if (x.license_type) t.add(String(x.license_type)); });
    return [...t].sort((a, b) => a.localeCompare(b, 'vi'));
  }

  function moPhieu(maTaiXe) {
    if (!dungKhung()) return;
    const tx = S.taiXe.find(x => String(x.id) === String(maTaiXe)) || null;
    S.dangSua = tx ? tx.id : null;
    const gp = tx ? gpCua(tx.id) : null;

    const chon = el('btl-f-taixe');
    chon.innerHTML = S.taiXe.map(x =>
      `<option value="${esc(x.id)}"${String(x.id) === String(S.dangSua) ? ' selected' : ''}>${
        esc(x.name || x.id)} — ${esc(x.license_type || 'chưa ghi hạng')}</option>`).join('');
    if (!S.taiXe.length) chon.innerHTML = '<option value="">(chưa có tài xế nào)</option>';

    el('btl-hang-goi').innerHTML = goiHang().map(h => `<option value="${esc(h)}"></option>`).join('');
    el('btl-phieu-ten').textContent = gp
      ? `Sửa bằng lái — ${tx.name || tx.id}`
      : (tx ? `Khai bằng lái — ${tx.name || tx.id}` : 'Khai bằng lái');

    const nay = homNay();
    const sau5nam = new Date(nay.getFullYear() + 5, nay.getMonth(), nay.getDate());
    el('btl-f-hang').value = (gp && gp.license_type) || (tx && tx.license_type) || '';
    el('btl-f-tu').value = gp && docNgay(gp.valid_from) ? String(gp.valid_from).slice(0, 10) : ngayIso(nay);
    el('btl-f-den').value = gp && docNgay(gp.valid_to) ? String(gp.valid_to).slice(0, 10) : ngayIso(sau5nam);
    el('btl-f-trangthai').value = (gp && gp.status) || 'active';
    el('btl-f-loi').hidden = true;
    nhacHang();

    el('btl-phieu').hidden = false;
  }

  function dongPhieu() {
    const p = el('btl-phieu');
    if (p) p.hidden = true;
    S.dangSua = null;
  }

  /**
   * Nói trước cho người dùng biết việc ghi sẽ chạm vào MẤY bảng.
   *
   * Đây là thứ không ai tự suy ra được: đổi hạng bằng thì phải ghi cả hồ sơ
   * tài xế, không thì cửa chặn vẫn chặn vì hai bảng ghi hai hạng khác nhau.
   */
  function nhacHang() {
    const o = el('btl-f-hang-nhac');
    if (!o) return;
    const ma = el('btl-f-taixe').value;
    const tx = S.taiXe.find(x => String(x.id) === String(ma));
    const hang = String(el('btl-f-hang').value || '').trim();
    if (!tx) { o.textContent = ''; return; }
    const hoSo = String(tx.license_type || '').trim();
    if (!hang || hang === hoSo) {
      o.className = 'btl-nhac';
      o.textContent = `Khớp hồ sơ tài xế ("${hoSo || 'chưa ghi'}").`;
      return;
    }
    o.className = 'btl-nhac btl-nhac-vang';
    o.textContent = `Hồ sơ tài xế đang ghi "${hoSo || 'chưa ghi'}". Lưu sẽ cập nhật `
      + `hồ sơ tài xế sang "${hang}" luôn, vì điều phối đòi hai bên bằng nhau.`;
  }

  async function luu(sk) {
    if (sk && sk.preventDefault) sk.preventDefault();
    const oLoi = el('btl-f-loi');
    const nutLuu = el('btl-f-luu');
    const ma = el('btl-f-taixe').value;
    const hang = String(el('btl-f-hang').value || '').trim();
    const tu = el('btl-f-tu').value;
    const den = el('btl-f-den').value;
    const trangThai = el('btl-f-trangthai').value;

    const bao = chu => { oLoi.hidden = false; oLoi.textContent = chu; };
    if (!ma) return bao('Chọn một tài xế.');
    if (!hang) return bao('Nhập hạng bằng.');
    if (!tu || !den) return bao('Nhập đủ ngày hiệu lực và ngày hết hạn.');
    if (tu >= den) return bao('Ngày hết hạn phải sau ngày bắt đầu hiệu lực.');

    const tx = S.taiXe.find(x => String(x.id) === String(ma));
    if (!tx) return bao('Không tìm thấy tài xế này trong danh sách đã tải.');

    oLoi.hidden = true;
    nutLuu.disabled = true;
    try {
      // 1) Ghi bảng giấy phép.
      await ghi('/api/tms/driver-qualifications', {
        driver_id: ma,
        license_type: hang,
        valid_from: `${tu}T00:00:00`,
        valid_to: `${den}T00:00:00`,
        status: trangThai,
      });

      // 2) Nếu hạng khác hồ sơ tài xế thì ghi luôn hồ sơ, không thì cửa chặn
      //    vẫn chặn. Gửi TRỌN bản ghi: `POST /api/drivers` là upsert và ghi đè
      //    `phone`, `role`, `shift`, `assigned_vehicle` bằng mặc định nếu
      //    payload thiếu — gửi lẻ một trường là xoá trắng số điện thoại.
      let daSuaHoSo = false;
      if (String(tx.license_type || '').trim() !== hang) {
        await ghi('/api/drivers', {
          id: tx.id,
          name: tx.name || tx.id,
          role: tx.role || 'Lái xe chính',
          license_type: hang,
          phone: tx.phone || '',
          assigned_vehicle: tx.assigned_vehicle || 'Chưa gán',
          shift: tx.shift || 'Ca Sáng (06:00 - 14:00)',
          photo_url: tx.photo_url || '',
        });
        daSuaHoSo = true;
      }

      dongPhieu();
      await nap();
      thongBao(daSuaHoSo
        ? `Đã lưu bằng lái và cập nhật hạng trên hồ sơ ${tx.name || tx.id} sang "${hang}".`
        : `Đã lưu bằng lái cho ${tx.name || tx.id}.`);
    } catch (e) {
      bao(e.message || 'Lưu không thành công.');
    } finally {
      nutLuu.disabled = false;
    }
  }

  /* =========================================================== hồ sơ tài xế ==

     CỬA CHO MỘT BIỂU MẪU BỊ BỎ QUÊN.

     `driver-modal-dialog` là biểu mẫu DUY NHẤT trong dự án sửa được tên, số
     điện thoại, vai trò, hạng bằng và ca làm của tài xế. Nó vẫn nằm trong
     trang, và lúc nạp `duaHopThoaiRaNgoaiKhungMan()` còn chuyển nó ra ngoài
     khung màn nên nó không bị khối ẩn `ssv5-khoi-cu` giam. Nhưng dò cả trang
     thì KHÔNG có một nút nào mở nó — nên trước hai nút dưới đây, hồ sơ tài xế
     không sửa được từ giao diện, chỉ sửa được bằng tệp lệnh.

     Đặt cửa ở đây là chỗ hợp nhất: đây là màn duy nhất liệt kê tài xế, và một
     nửa số lỗi mà màn này báo ("lệch hạng với hồ sơ tài xế") chỉ chữa được khi
     sửa được cả hồ sơ.

     HAI CHỖ PHẢI CẨN THẬN:

       1. `editDriverById` đọc từ mảng `fioriDrivers` của `app.js`, KHÔNG đọc từ
          dữ liệu của màn này. Mảng đó rỗng thì hàm im lặng thoát ngay
          (`if (!driver) return;`) — bấm vào không có gì xảy ra, đúng dạng nút
          nói dối mà cả lần rà soát này đi dọn. Nên phải gọi
          `loadFioriDrivers()` trước, và nếu vẫn không mở được thì NÓI RA.
       2. `saveDriverModal` kết thúc bằng `loadFioriDrivers()` — nó không biết
          gì về màn này. Nên phải bọc nó để màn tự nạp lại, không thì người dùng
          sửa hạng bằng xong mà bảng vẫn hiện giá trị cũ.
     ========================================================================== */

  async function moHoSo(maTaiXe) {
    if (typeof window.editDriverById !== 'function'
        || !document.getElementById('driver-modal-dialog')) {
      thongBao('Không mở được biểu mẫu hồ sơ tài xế trên trang này.', true);
      return;
    }
    // Nạp mảng mà `editDriverById` đọc. Thất bại thì vẫn thử mở — có thể mảng
    // đã được nạp sẵn từ lúc mở màn khác.
    if (typeof window.loadFioriDrivers === 'function') {
      try { await window.loadFioriDrivers(); } catch (e) { /* thử mở tiếp */ }
    }
    document.getElementById('driver-modal-dialog').style.display = 'none';
    window.editDriverById(maTaiXe);
    if (document.getElementById('driver-modal-dialog').style.display !== 'flex') {
      thongBao(`Chưa mở được hồ sơ của ${maTaiXe}: danh sách tài xế của ứng dụng `
        + 'chưa nạp xong. Bấm "Tải lại" rồi thử lại.', true);
    }
  }

  function noiVaoLuuHoSo() {
    const cu = window.saveDriverModal;
    if (typeof cu !== 'function' || cu.__btlDaBoc) return false;
    const moi = async function () {
      const kq = await cu.apply(this, arguments);
      // Chỉ nạp lại khi thẻ này đang mở — người dùng có thể sửa hồ sơ tài xế
      // từ một màn khác, và lúc đó nạp lại là gọi máy chủ vô ích.
      const goc = el(GOC);
      if (goc && goc.style.display !== 'none' && S.daDung) nap();
      return kq;
    };
    moi.__btlDaBoc = true;
    window.saveDriverModal = moi;
    return true;
  }

  /* ---------------------------------------------------------------- sự kiện -- */

  function ganSuKien() {
    el('btl-tai-lai').addEventListener('click', nap);
    el('btl-khai').addEventListener('click', () => moPhieu(null));
    el('btl-them-tx').addEventListener('click', () => {
      if (typeof window.openAddDriverModal === 'function') window.openAddDriverModal();
      else thongBao('Không mở được biểu mẫu thêm tài xế trên trang này.', true);
    });

    el('btl-ngay').addEventListener('change', e => {
      S.ngayXet = e.target.value || ngayIso(homNay());
      ve();
    });

    el('btl-tim').addEventListener('input', e => { S.tim = e.target.value || ''; veBang(); });

    el('btl-kpi').addEventListener('click', e => {
      const nut = e.target.closest('button[data-loc]');
      if (!nut) return;
      const ma = nut.getAttribute('data-loc') || '';
      S.loc = (S.loc === ma) ? '' : ma;
      ve();
    });

    el('btl-rows').addEventListener('click', e => {
      const nutBang = e.target.closest('button[data-sua]');
      if (nutBang) { moPhieu(nutBang.getAttribute('data-sua')); return; }
      const nutHoSo = e.target.closest('button[data-hoso]');
      if (nutHoSo) moHoSo(nutHoSo.getAttribute('data-hoso'));
    });

    el('btl-phieu').addEventListener('click', e => {
      if (e.target.closest('[data-dong]')) dongPhieu();
    });
    el('btl-form').addEventListener('submit', luu);
    el('btl-f-taixe').addEventListener('change', () => {
      const tx = S.taiXe.find(x => String(x.id) === String(el('btl-f-taixe').value));
      if (tx && !gpCua(tx.id)) el('btl-f-hang').value = tx.license_type || '';
      nhacHang();
    });
    el('btl-f-hang').addEventListener('input', nhacHang);
  }

  /* ------------------------------------------------------------------ nối ---- */

  /**
   * Tự móc vào `switchMasterDataTab` thay vì sửa `app.js`.
   *
   * `app.js` đang có người khác sửa cùng lúc, và mọi dòng tôi chèn vào đó là
   * một chỗ va chạm khi chốt. Bọc hàm ở đây thì màn này tự nạp khi thẻ được mở,
   * mà không cần một dòng nào trong `app.js`.
   */
  function noiVaoDieuHuong() {
    const cu = window.switchMasterDataTab;
    if (typeof cu !== 'function' || cu.__btlDaBoc) return false;
    const moi = function (tabId, btn) {
      const kq = cu.apply(this, arguments);
      if (tabId === GOC) nap();
      return kq;
    };
    moi.__btlDaBoc = true;
    window.switchMasterDataTab = moi;
    return true;
  }

  window.eplMoBangLaiTaiXe = function () {
    if (typeof window.switchView === 'function') window.switchView('master-data');
    if (typeof window.switchMasterDataTab === 'function') window.switchMasterDataTab(GOC);
    else nap();
  };

  function batDau() {
    // `app.js` nạp sau tệp này thì cả `switchMasterDataTab` lẫn `saveDriverModal`
    // đều chưa tồn tại. Thử lại vài nhịp rồi thôi — không lặp vô hạn. Chỉ dừng
    // khi bọc được CẢ HAI.
    if (noiVaoDieuHuong() && noiVaoLuuHoSo()) return;
    let con = 40;
    const h = setInterval(() => {
      const xong = noiVaoDieuHuong() || window.switchMasterDataTab?.__btlDaBoc;
      const xong2 = noiVaoLuuHoSo() || window.saveDriverModal?.__btlDaBoc;
      if ((xong && xong2) || (con -= 1) <= 0) clearInterval(h);
    }, 150);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', batDau);
  } else {
    batDau();
  }
})();

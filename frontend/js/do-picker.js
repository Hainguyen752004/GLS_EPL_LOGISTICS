/* ==========================================================================
   BỘ CHỌN DO cho hộp thoại tạo Trip — bản v2.

   Bản cũ là một `<select multiple size="6">`. Ba chỗ dở đo được:

     · Sáu dòng CỐ ĐỊNH. Có 3 DO thì thừa một khoảng trống lớn ngay giữa hộp
       thoại; có 300 DO thì phải cuộn trong một ô cao đúng 6 dòng.
     · Không tìm được. Ở quy mô thật vài trăm DO mỗi ngày thì không ai cuộn hết
       để tìm một mã.
     · Chọn nhiều phải giữ Ctrl, và bấm nhầm một dòng là MẤT HẾT những dòng đã
       chọn trước đó — không có gì báo, và người dùng không biết mình vừa mất gì.

   Bản này: các thẻ đã chọn ở trên, ô tìm ở giữa, danh sách có ô tích ở dưới.
   Ô ẩn `trip-return-do-ids` giữ nguyên là NGUỒN SỰ THẬT, vì
   `submitTripReturnActionForm` đọc chính nó bằng `split(",")`.

   VÌ SAO ĐỂ RIÊNG MỘT TỆP: phần này dựng HTML bằng chuỗi lồng nhiều lớp. Viết
   nó qua một lớp sinh mã trung gian là tự mở đường cho lỗi thoát ký tự; viết
   thẳng ra tệp JS thì đọc được đúng cái sẽ chạy.
   ========================================================================== */

(function () {
  'use strict';

  /** Chữ người dùng đang gõ ở ô tìm. Chỉ ảnh hưởng cách hiện, không ảnh hưởng
   *  danh sách đã chọn — lọc rồi chọn tiếp thì các DO chọn trước vẫn còn. */
  let tuTim = '';

  function oAn() {
    return document.getElementById('trip-return-do-ids');
  }

  /** Các mã DO đang chọn, đọc từ ô ẩn — nguồn sự thật duy nhất. */
  function dsDangChon() {
    const o = oAn();
    return String((o && o.value) || '')
      .split(',').map(x => x.trim()).filter(Boolean);
  }

  /** Bỏ dấu để "cat lai" khớp "Cát Lái" — người dùng hiếm khi gõ đủ dấu. */
  function boDau(chuoi) {
    return String(chuoi === null || chuoi === undefined ? '' : chuoi)
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')  // dau thanh roi ra sau NFD
      .replace(/đ/g, 'd')
      .replace(/Đ/g, 'D')
      .toLowerCase();
  }

  function anToan(chuoi) {
    if (typeof window.doBoardEscape === 'function') return window.doBoardEscape(chuoi);
    if (typeof window.escapeHtml === 'function') return window.escapeHtml(chuoi);
    const d = document.createElement('div');
    d.textContent = chuoi === null || chuoi === undefined ? '' : chuoi;
    return d.innerHTML;
  }

  /** Danh sách DO chọn được, lấy từ chính nguồn mà hộp thoại vẫn dùng. */
  function dsDon() {
    const lay = window.tripReturnAllDeliveryOrders;
    const tho = typeof lay === 'function' ? (lay() || []) : [];
    return tho
      .map(don => ({
        id: String(don.id || ''),
        // Hiện luôn MÃ TUYẾN: một Trip chỉ chở được các DO CÙNG một tuyến, nên
        // đó là thứ người dùng phải đối chiếu trước khi tick.
        tuyen: String(don.route_id || don.route || ''),
        khach: String(don.customer_id || ''),
      }))
      .filter(d => d.id);
  }

  function ghiVaoOAn(ds) {
    const o = oAn();
    if (o) o.value = ds.join(',');
  }

  function capNhatXemTruoc() {
    if (typeof window.hydrateTripReturnRoutePreview === 'function') {
      window.hydrateTripReturnRoutePreview();
    }
  }

  /* ------------------------------ Vẽ ------------------------------ */

  function ve() {
    const hopDS = document.getElementById('do-picker-list');
    if (!hopDS) return;
    const hopThe = document.getElementById('do-picker-chips');
    const hopChan = document.getElementById('do-picker-foot');

    const dsChon = dsDangChon();
    const tatCa = dsDon();
    const q = boDau(tuTim).trim();
    const loc = q
      ? tatCa.filter(d => boDau(d.id + ' ' + d.tuyen + ' ' + d.khach).indexOf(q) >= 0)
      : tatCa;

    // --- Thẻ đã chọn ---
    if (hopThe) {
      if (dsChon.length) {
        const the = dsChon.map(function (ma) {
          const d = tatCa.filter(x => x.id === ma)[0];
          const phu = d ? [d.tuyen, d.khach].filter(Boolean).join(' · ') : '';
          return '<span class="do-chip" title="' + anToan(phu || ma) + '">'
            + anToan(ma)
            + '<button type="button" aria-label="Bỏ ' + anToan(ma) + ' khỏi Trip"'
            + ' data-do-bo="' + anToan(ma) + '">×</button></span>';
        }).join('');
        hopThe.innerHTML = the
          + '<button type="button" class="do-chip-clear" data-do-bo-het="1">Bỏ hết</button>';
      } else {
        hopThe.innerHTML = '<span class="do-chip-empty">'
          + 'Chưa chọn DO nào. Tick ở danh sách bên dưới.</span>';
      }
    }

    // --- Danh sách ---
    if (!loc.length) {
      // Nói rõ vì sao trống: không có DO nào, hay chữ tìm không khớp. Hai chuyện
      // đó dẫn tới hai việc khác nhau.
      hopDS.innerHTML = q
        ? '<p class="do-picker-none">Không có DO nào khớp <b>' + anToan(tuTim)
          + '</b>. Xóa chữ tìm để xem lại tất cả.</p>'
        : '<p class="do-picker-none">Chưa có lệnh giao hàng nào để lập Trip.</p>';
    } else {
      hopDS.innerHTML = loc.map(function (d) {
        const chon = dsChon.indexOf(d.id) >= 0;
        const phu = [d.tuyen, d.khach].filter(Boolean).join(' · ');
        return '<label class="do-opt' + (chon ? ' is-on' : '') + '">'
          + '<input type="checkbox"' + (chon ? ' checked' : '')
          + ' data-do-ma="' + anToan(d.id) + '">'
          + '<span><b>' + anToan(d.id) + '</b>'
          + (phu ? '<small>' + anToan(phu) + '</small>' : '')
          + '</span></label>';
      }).join('');
    }

    // --- Dòng chân ---
    if (hopChan) {
      hopChan.innerHTML = 'Đang chọn <b>' + dsChon.length + '</b> DO · hiện <b>'
        + loc.length + '</b>/' + tatCa.length
        + '. Một Trip chỉ chở được các DO <b>cùng một tuyến</b>.';
    }
  }

  /* --------------------------- Thao tác --------------------------- */

  /**
   * Tick hoặc bỏ tick một DO.
   *
   * Ghi vào ô ẩn TRƯỚC rồi mới vẽ lại, vì hàm vẽ đọc chính ô ẩn đó — làm ngược
   * lại thì thẻ vừa tick không hiện ra cho tới lần vẽ sau.
   */
  function doiChon(ma) {
    const ds = dsDangChon();
    const i = ds.indexOf(String(ma));
    if (i >= 0) ds.splice(i, 1); else ds.push(String(ma));
    ghiVaoOAn(ds);
    ve();
    capNhatXemTruoc();
  }

  function boHet() {
    ghiVaoOAn([]);
    ve();
    capNhatXemTruoc();
  }

  /**
   * Đổ lại danh sách và đánh dấu các DO đang chọn.
   *
   * GIỮ NGUYÊN TÊN HÀM cũ `populateTripReturnDoSelect`: `openTripReturnAction`
   * và vài chỗ khác gọi nó, và ý nghĩa không đổi — chỉ cách trình bày đổi từ ô
   * chọn nhiều sang bộ chọn có tìm kiếm.
   */
  function nap(selectedDoIds) {
    const ds = Array.isArray(selectedDoIds)
      ? selectedDoIds.map(String).filter(Boolean)
      : (selectedDoIds ? [String(selectedDoIds)] : []);
    ghiVaoOAn(ds);
    tuTim = '';
    const oTim = document.getElementById('do-picker-search');
    if (oTim) oTim.value = '';
    ve();
  }

  /* --------------------------- Móc nối ---------------------------- */

  // Nghe ở CẤP KHUNG chứ không gắn onclick vào từng dòng: hàm vẽ dựng lại toàn
  // bộ danh sách mỗi lần tick, nên gắn vào từng dòng là gắn lại hàng trăm lần.
  function gan() {
    const khung = document.getElementById('do-picker');
    if (!khung || khung.dataset.daGan) return;
    khung.dataset.daGan = '1';

    khung.addEventListener('change', function (e) {
      const ma = e.target && e.target.getAttribute
        && e.target.getAttribute('data-do-ma');
      if (ma) doiChon(ma);
    });

    khung.addEventListener('click', function (e) {
      const nut = e.target && e.target.closest ? e.target.closest('[data-do-bo],[data-do-bo-het]') : null;
      if (!nut) return;
      e.preventDefault();
      if (nut.hasAttribute('data-do-bo-het')) boHet();
      else doiChon(nut.getAttribute('data-do-bo'));
    });

    const oTim = document.getElementById('do-picker-search');
    if (oTim) {
      oTim.addEventListener('input', function () {
        tuTim = oTim.value;
        ve();
      });
      // Escape xóa chữ tìm thay vì đóng cả hộp thoại — người dùng đang gõ trong
      // một ô tìm thì Escape nghĩa là "bỏ chữ vừa gõ".
      oTim.addEventListener('keydown', function (e) {
        if (e.key !== 'Escape' || !oTim.value) return;
        e.stopPropagation();
        oTim.value = '';
        tuTim = '';
        ve();
      });
    }
  }

  window.populateTripReturnDoSelect = nap;
  window.veDanhSachDOChon = ve;
  window.doiChonDO = doiChon;
  window.boChonHetDO = boHet;
  window.ganBoChonDO = gan;

  /**
   * Gom lại các DO đang chọn vào ô ẩn.
   *
   * Bộ chọn này ghi thẳng vào ô ẩn mỗi lần tick, nên hàm chỉ còn việc vẽ lại và
   * cập nhật xem trước tuyến. Giữ tên hàm vì thanh chọn DO ở màn Lập kế hoạch
   * gọi nó.
   */
  window.capNhatDSDOChonTrongHopThoai = function () {
    ve();
    capNhatXemTruoc();
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', gan);
  } else {
    gan();
  }
})();

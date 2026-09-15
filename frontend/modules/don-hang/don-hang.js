/* Module Đơn hàng khách (Sale Order).
 *
 * Màn này chỉ lo phần ĐƠN: xem đơn, tạo đơn, và cho thấy mỗi dòng hàng đã đóng
 * bao nhiêu, còn lại bao nhiêu. Việc đóng gói nằm ở màn Packing List.
 */

window.DonHang = (function () {
  'use strict';

  var t = PL.t, an = PL.an, so = PL.so;
  var danhSach = [];
  var dangChon = null;
  var soDongMoi = 0;

  var TRANG_THAI = ['new', 'packing', 'packed', 'delivering', 'delivered', 'cancelled'];
  var MAU = {
    new: 'xam', packing: 'cam', packed: 'lam',
    delivering: 'tim', delivered: 'xanh', cancelled: 'do',
  };

  function nhanTrangThai(ma) {
    return t('so_status_' + ma, ma).replace('\n', ' · ');
  }

  /* ------------------------------------------------------------ danh sách */
  function veDanhSach() {
    var khung = document.getElementById('dh-danh-sach');
    if (!khung) return;
    if (!danhSach.length) {
      khung.innerHTML = '<div class="trong">' + an(t('common_empty').replace('\n', ' · ')) + '</div>';
      return;
    }
    khung.innerHTML = danhSach.map(function (d) {
      return '<div class="ds-muc' + (dangChon && dangChon.id === d.id ? ' dang-chon' : '') +
        '" data-id="' + an(d.id) + '">' +
        '<div style="display:flex;justify-content:space-between;gap:8px;align-items:start">' +
        '<span class="ma">' + an(d.id) + '</span>' +
        '<span class="nhan ' + (MAU[d.status] || 'xam') + '">' + an(nhanTrangThai(d.status)) + '</span>' +
        '</div>' +
        '<div class="phu-de">PO ' + an(d.po_number) + ' · ' + an(d.ship_to_name || '—') + '</div>' +
        '<div class="phu-de">' + an(t('so_pl_count').split('\n')[0]) + ': ' + d.packing_list_count + '</div>' +
        '</div>';
    }).join('');
    khung.querySelectorAll('.ds-muc').forEach(function (el) {
      el.addEventListener('click', function () { moDon(el.dataset.id); });
    });
  }

  function napDanhSach() {
    var tim = (document.getElementById('dh-tim') || {}).value || '';
    var tt = (document.getElementById('dh-loc-trang-thai') || {}).value || '';
    var dd = '/api/sales-orders?page_size=100';
    if (tim.trim()) dd += '&q=' + encodeURIComponent(tim.trim());
    if (tt) dd += '&status=' + encodeURIComponent(tt);
    return PL.goi(dd).then(function (kq) {
      danhSach = (kq && kq.items) || [];
      veDanhSach();
    }).catch(PL.baoLoi);
  }

  /* ------------------------------------------------------------- chi tiết */
  function veChiTiet() {
    var khung = document.getElementById('dh-chi-tiet');
    if (!khung) return;
    if (!dangChon) {
      khung.innerHTML = '<div class="the"><div class="trong">' +
        an(t('so_pick_hint').replace('\n', ' · ')) + '</div></div>';
      return;
    }
    var d = dangChon;
    var dong = d.lines || [];

    var hang = dong.map(function (x) {
      var het = x.remaining_case_qty === 0 && x.remaining_piece_qty === 0;
      return '<tr>' +
        '<td class="giua">' + x.line_no + '</td>' +
        '<td><code>' + an(x.barcode || '—') + '</code></td>' +
        '<td>' + an(x.product_code || '—') + '</td>' +
        '<td>' + an(x.description) +
          (x.description_en ? '<div class="phu-mo">' + an(x.description_en) + '</div>' : '') + '</td>' +
        '<td class="phai">' + so(x.case_qty, 0) + '</td>' +
        '<td class="phai">' + so(x.packed_case_qty, 0) + '</td>' +
        '<td class="phai"><b class="' + (het ? 'het' : 'con') + '">' + so(x.remaining_case_qty, 0) + '</b></td>' +
        '<td class="phai">' + so(x.unit_price, 0) + '</td>' +
        '<td class="phai">' + so(x.amount, 0) + '</td>' +
        '</tr>';
    }).join('');

    khung.innerHTML =
      '<div class="the">' +
        '<div class="the-dau">' +
          '<h3>' + an(d.id) + ' · PO ' + an(d.po_number) + '</h3>' +
          '<div style="display:flex;gap:8px;align-items:center">' +
            '<span class="nhan ' + (MAU[d.status] || 'xam') + '">' + an(nhanTrangThai(d.status)) + '</span>' +
            (d.status !== 'cancelled' && d.status !== 'delivered'
              ? '<button type="button" class="nut nho" id="dh-di-dong-goi">' +
                an(t('pack_title').replace('\n', ' · ')) + ' →</button>'
              : '') +
            (d.status === 'new' || d.status === 'packing'
              ? '<button type="button" class="nut nguy-hiem nho" id="dh-huy">' +
                an(t('so_cancel_title').replace('\n', ' · ')) + '</button>'
              : '') +
          '</div>' +
        '</div>' +
        '<div class="the-than">' +
          '<div class="luoi-3 thong-tin">' +
            o(t('so_ship_to'), (d.ship_to_name || '—') + (d.ship_to_code ? ' (' + d.ship_to_code + ')' : '')) +
            o(t('so_vendor'), d.vendor_name || '—') +
            o(t('so_tax_number'), d.tax_number || '—') +
            o(t('so_order_date'), d.order_date || '—') +
            o(t('so_shipping_date'), d.shipping_date || '—') +
            o(t('so_currency'), d.currency || 'LAK') +
            o(t('so_ship_to_address'), d.ship_to_address || '—') +
            o(t('so_pl_count'), String(d.packing_list_count)) +
            o(t('common_total'), so(d.total_amount, 0) + ' ' + (d.currency || 'LAK')) +
          '</div>' +
          '<div class="tinh-trang ' + (d.fully_packed ? 'du' : 'thieu') + '">' +
            an((d.fully_packed ? t('so_fully_packed_yes') : t('so_fully_packed_no')).replace('\n', ' · ')) +
            ' — ' + an(t('so_remaining').split('\n')[0]) + ': ' + so(d.remaining_case_qty, 0) +
          '</div>' +
        '</div>' +
      '</div>' +
      '<div class="the">' +
        '<div class="the-dau"><h3 data-i18n="so_lines"></h3></div>' +
        '<div class="bang-cuon">' +
          '<table class="bang"><thead><tr>' +
            '<th class="giua" data-i18n="so_line_no"></th>' +
            '<th data-i18n="so_barcode"></th>' +
            '<th data-i18n="so_product_code"></th>' +
            '<th data-i18n="so_description"></th>' +
            '<th class="phai" data-i18n="so_case_qty"></th>' +
            '<th class="phai" data-i18n="so_packed"></th>' +
            '<th class="phai" data-i18n="so_remaining"></th>' +
            '<th class="phai" data-i18n="so_unit_price"></th>' +
            '<th class="phai" data-i18n="so_amount"></th>' +
          '</tr></thead><tbody>' + hang + '</tbody></table>' +
        '</div>' +
      '</div>';

    PL.apDungNgonNgu(khung);

    var nutDongGoi = document.getElementById('dh-di-dong-goi');
    if (nutDongGoi) {
      nutDongGoi.addEventListener('click', function () {
        try { localStorage.setItem('PL_DEMO_SO_DANG_CHON', d.id); } catch (e) { /* bỏ qua */ }
        PL.moMan('packing-list');
      });
    }
    var nutHuy = document.getElementById('dh-huy');
    if (nutHuy) nutHuy.addEventListener('click', huyDon);
  }

  function o(nhan, gia_tri) {
    var chu = String(nhan);
    var hai = chu.indexOf('\n') >= 0 ? chu.split('\n') : null;
    return '<div class="o-tt"><div class="nhan-tt">' +
      (hai ? '<span class="d-vi">' + an(hai[0]) + '</span><span class="d-lo">' + an(hai[1]) + '</span>'
           : an(chu)) +
      '</div><div class="gia-tri-tt">' + an(gia_tri) + '</div></div>';
  }

  function moDon(id) {
    return PL.goi('/api/sales-orders/' + encodeURIComponent(id)).then(function (d) {
      dangChon = d;
      veDanhSach();
      veChiTiet();
    }).catch(PL.baoLoi);
  }

  function huyDon() {
    if (!dangChon) return;
    PL.hoiXacNhan({
      tieu_de: t('so_cancel_title').replace('\n', ' · '),
      mo_ta: t('so_cancel_warn').replace('\n', ' '),
      o_nhap: true,
      nguy_hiem: true,
      chu_dong_y: t('common_confirm').replace('\n', ' · '),
    }).then(function (kq) {
      if (!kq) return;
      PL.goi('/api/sales-orders/' + encodeURIComponent(dangChon.id) + '/cancel', {
        method: 'POST', body: { reason: kq.chu },
      }).then(function () {
        PL.thongBao(t('ok_so_cancelled').replace('\n', ' · '));
        return napDanhSach().then(function () { return moDon(dangChon.id); });
      }).catch(PL.baoLoi);
    });
  }

  /* --------------------------------------------------------------- tạo đơn */
  function themDongMoi(mau) {
    soDongMoi += 1;
    var tb = document.querySelector('#dh-bang-dong tbody');
    var tr = document.createElement('tr');
    tr.innerHTML =
      '<td class="giua stt">' + soDongMoi + '</td>' +
      '<td><input type="text" class="c-barcode"></td>' +
      '<td><input type="text" class="c-ma"></td>' +
      '<td><input type="text" class="c-mo-ta"></td>' +
      '<td><input type="number" class="c-thung phai" min="0" value="0"></td>' +
      '<td><input type="number" class="c-cai phai" min="0" value="0"></td>' +
      '<td><input type="number" class="c-gia phai" min="0" value="0"></td>' +
      '<td><input type="number" class="c-kg phai" min="0" step="0.001" value="0"></td>' +
      '<td class="giua"><button type="button" class="nut nho bo-dong">×</button></td>';
    if (mau) {
      tr.querySelector('.c-barcode').value = mau.barcode || '';
      tr.querySelector('.c-ma').value = mau.product_code || '';
      tr.querySelector('.c-mo-ta').value = mau.description || '';
    }
    tb.appendChild(tr);
    tr.querySelector('.bo-dong').addEventListener('click', function () {
      tr.remove();
      danhLaiSTT();
    });
  }

  function danhLaiSTT() {
    document.querySelectorAll('#dh-bang-dong tbody tr').forEach(function (tr, i) {
      tr.querySelector('.stt').textContent = i + 1;
    });
  }

  function luuDon() {
    var dong = [];
    document.querySelectorAll('#dh-bang-dong tbody tr').forEach(function (tr, i) {
      var mo_ta = tr.querySelector('.c-mo-ta').value.trim();
      var thung = Number(tr.querySelector('.c-thung').value || 0);
      var cai = Number(tr.querySelector('.c-cai').value || 0);
      if (!mo_ta && !thung && !cai) return;   // dòng trống thì bỏ qua
      var gia = Number(tr.querySelector('.c-gia').value || 0);
      dong.push({
        line_no: i + 1,
        barcode: tr.querySelector('.c-barcode').value.trim(),
        product_code: tr.querySelector('.c-ma').value.trim(),
        description: mo_ta,
        case_qty: thung,
        piece_qty: cai,
        unit_price: gia,
        amount: gia * thung,
        weight_kg: Number(tr.querySelector('.c-kg').value || 0),
      });
    });

    PL.goi('/api/sales-orders', {
      method: 'POST',
      body: {
        po_number: document.getElementById('dh-po').value.trim(),
        order_date: document.getElementById('dh-ngay-dat').value,
        shipping_date: document.getElementById('dh-ngay-giao').value,
        currency: document.getElementById('dh-tien-te').value,
        ship_to_code: document.getElementById('dh-ma-giao').value.trim(),
        ship_to_name: document.getElementById('dh-ten-giao').value.trim(),
        ship_to_address: document.getElementById('dh-dia-chi').value.trim(),
        vendor_name: document.getElementById('dh-vendor').value.trim(),
        tax_number: document.getElementById('dh-mst').value.trim(),
        lines: dong,
      },
    }).then(function (d) {
      PL.thongBao(t('ok_so_created').replace('\n', ' · '));
      document.getElementById('dh-form').hidden = true;
      dungForm();
      return napDanhSach().then(function () { return moDon(d.id); });
    }).catch(PL.baoLoi);
  }

  function dungForm() {
    document.querySelector('#dh-bang-dong tbody').innerHTML = '';
    soDongMoi = 0;
    ['dh-po', 'dh-ngay-dat', 'dh-ngay-giao', 'dh-ma-giao', 'dh-ten-giao',
     'dh-dia-chi', 'dh-vendor', 'dh-mst'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.value = '';
    });
    themDongMoi();
  }

  function veLocTrangThai() {
    var el = document.getElementById('dh-loc-trang-thai');
    if (!el) return;
    var cu = el.value;
    el.innerHTML = '<option value="">' + an(t('common_all').replace('\n', ' · ')) + '</option>' +
      TRANG_THAI.map(function (x) {
        return '<option value="' + x + '">' + an(nhanTrangThai(x)) + '</option>';
      }).join('');
    el.value = cu;
  }

  /* ------------------------------------------------------------- khởi động */
  function khoiDong() {
    veLocTrangThai();
    dungForm();

    document.getElementById('dh-bat-tat-form').addEventListener('click', function () {
      var f = document.getElementById('dh-form');
      f.hidden = !f.hidden;
    });
    document.getElementById('dh-them-dong').addEventListener('click', function () { themDongMoi(); });
    document.getElementById('dh-luu').addEventListener('click', luuDon);
    document.getElementById('dh-lam-moi').addEventListener('click', napDanhSach);

    var hen = null;
    document.getElementById('dh-tim').addEventListener('input', function () {
      clearTimeout(hen);
      hen = setTimeout(napDanhSach, 300);
    });
    document.getElementById('dh-loc-trang-thai').addEventListener('change', napDanhSach);

    napDanhSach().then(function () {
      var luu = null;
      try { luu = localStorage.getItem('PL_DEMO_SO_DANG_CHON'); } catch (e) { /* bỏ qua */ }
      var dau = danhSach.filter(function (x) { return x.id === luu; })[0] || danhSach[0];
      if (dau) moDon(dau.id);
    });
  }

  function veLai() {
    veLocTrangThai();
    veDanhSach();
    veChiTiet();
  }

  return { khoiDong: khoiDong, veLai: veLai };
})();

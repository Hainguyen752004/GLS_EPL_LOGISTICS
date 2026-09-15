/* Module Quét tem QR.
 *
 * Đây là màn chứng minh yêu cầu gốc của bản demo: cầm một kiện bất kỳ lên, quét
 * tem, là biết ngay kiện đó thuộc Packing List nào, đơn hàng nào, và trong kiện
 * có những dòng hàng nào của đơn.
 */

window.QuetTem = (function () {
  'use strict';

  var t = PL.t, an = PL.an, so = PL.so;
  var BUOC = ['parked', 'gate_in', 'loaded', 'dispatched'];
  var MAU_PL = {
    ready: 'xam', parked: 'lam', gate_in: 'tim',
    loaded: 'cam', dispatched: 'cam', delivered: 'xanh', cancelled: 'do',
  };
  var ketQua = null;

  function mot(khoa) { return t(khoa).replace('\n', ' · '); }
  function nhanPL(ma) { return t('pack_status_' + ma, ma).replace('\n', ' · '); }

  function oTT(nhanChu, giaTri) {
    var chu = String(nhanChu);
    var hai = chu.indexOf('\n') >= 0 ? chu.split('\n') : null;
    return '<div class="o-tt"><div class="nhan-tt">' +
      (hai ? '<span class="d-vi">' + an(hai[0]) + '</span><span class="d-lo">' + an(hai[1]) + '</span>'
           : an(chu)) +
      '</div><div class="gia-tri-tt">' + an(giaTri) + '</div></div>';
  }

  function veBuoc() {
    var el = document.getElementById('qt-buoc');
    if (!el) return;
    var cu = el.value;
    el.innerHTML = '<option value="">' + an(mot('scan_step_none')) + '</option>' +
      BUOC.map(function (b) {
        return '<option value="' + b + '">' + an(nhanPL(b)) + '</option>';
      }).join('');
    el.value = cu;
  }

  function veKetQua() {
    var khung = document.getElementById('qt-ket-qua');
    if (!khung) return;
    if (!ketQua) {
      khung.innerHTML = '<div class="the"><div class="trong">' + an(mot('scan_empty')) + '</div></div>';
      return;
    }
    var lb = ketQua.label, p = ketQua.packing_list, d = ketQua.sales_order;

    khung.innerHTML =
      '<div class="the">' +
        '<div class="the-dau">' +
          '<h3 data-i18n="scan_result"></h3>' +
          '<span class="nhan ' + (MAU_PL[p.status] || 'xam') + '">' + an(nhanPL(p.status)) + '</span>' +
        '</div>' +
        '<div class="the-than">' +
          (lb
            ? '<div class="lan-quet ' + (lb.first_scan ? 'dau' : 'lap') + '">' +
                an(lb.first_scan ? mot('scan_first') : mot('scan_again')) +
              '</div>' +
              '<div class="day-so">' +
                '<span>' + an(mot('pack_package_no')) + ': <b>' + lb.package_no + ' / ' + lb.package_total + '</b></span>' +
                '<span>' + an(mot('scan_scanned_count')) + ': <b>' + lb.scanned_count + '</b> ' +
                  an(mot('common_of')) + ' ' + so(p.box_count, 0) + '</span>' +
              '</div>'
            : '<div class="lan-quet dau">' + an(mot('scan_list_qr')) + '</div>' +
              '<div class="day-so"><span>' + an(mot('pack_box_count')) + ': <b>' + so(p.box_count, 0) + '</b></span>' +
              '<span>' + an(mot('so_case_qty')) + ': <b>' + so(p.total_cases, 0) + '</b></span></div>') +
        '</div>' +
      '</div>' +

      '<div class="the">' +
        '<div class="the-dau"><h3>' + an(mot('pack_belongs_to')) + '</h3></div>' +
        '<div class="the-than">' +
          '<div class="luoi-3 thong-tin">' +
            oTT(t('nav_packing'), p.id) +
            oTT(t('so_code'), d.id) +
            oTT(t('so_po'), d.po_number || '—') +
            oTT(t('so_ship_to'), d.ship_to_name || '—') +
            oTT(t('pack_route'), p.route_name || '—') +
            oTT(t('common_status'), nhanPL(p.status)) +
          '</div>' +
        '</div>' +
      '</div>' +

      '<div class="the">' +
        '<div class="the-dau"><h3 data-i18n="pack_items"></h3></div>' +
        '<div class="bang-cuon"><table class="bang bang-truy-nguoc"><thead><tr>' +
          '<th data-i18n="pack_from_line"></th>' +
          '<th data-i18n="so_barcode"></th>' +
          '<th data-i18n="so_description"></th>' +
          '<th class="phai" data-i18n="so_case_qty"></th>' +
        '</tr></thead><tbody>' +
        (p.items || []).map(function (it) {
          return '<tr><td class="giua"><b>' + an(it.so_id) + ' #' + (it.line_no || '?') + '</b></td>' +
            '<td><code>' + an(it.barcode || '—') + '</code></td>' +
            '<td>' + an(it.description || '') + '</td>' +
            '<td class="phai">' + so(it.case_qty, 0) + '</td></tr>';
        }).join('') +
        '</tbody></table></div>' +
      '</div>';

    PL.apDungNgonNgu(khung);
  }

  function quet() {
    var o = document.getElementById('qt-ma');
    var ma = (o.value || '').trim();
    if (!ma) return;
    PL.goi('/api/labels/scan', {
      method: 'POST',
      body: { token: ma, step: document.getElementById('qt-buoc').value || null },
    }).then(function (kq) {
      ketQua = kq;
      veKetQua();
      PL.thongBao(mot('ok_scan'));
      o.value = '';
      o.focus();
    }).catch(function (loi) {
      PL.baoLoi(loi);
      o.select();
    });
  }

  function khoiDong() {
    veBuoc();
    document.getElementById('qt-quet').addEventListener('click', quet);
    document.getElementById('qt-ma').addEventListener('keydown', function (e) {
      // Máy đọc mã vạch gõ xong thì bắn Enter — bắt luôn để khỏi phải bấm nút.
      if (e.key === 'Enter') { e.preventDefault(); quet(); }
    });
    document.getElementById('qt-ma').focus();
  }

  function veLai() {
    veBuoc();
    veKetQua();
  }

  return { khoiDong: khoiDong, veLai: veLai };
})();

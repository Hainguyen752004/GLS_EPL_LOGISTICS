/* Module Danh mục khách hàng.
 *
 * Nguồn cho các ô CHỌN trên phiếu đơn hàng. Ba loại trong cùng một danh mục:
 * khách nhận hàng, nhà cung cấp, và kho xuất hàng của mình. Toạ độ khai ở đây
 * là thứ màn Theo dõi dùng để vẽ đường xe.
 */

window.KhachHang = (function () {
  'use strict';

  var t = PL.t, an = PL.an;
  var ds = [], dangChon = null, dangSua = false;
  var LOAI = ['customer', 'vendor', 'depot'];
  var MAU = { customer: 'lam', vendor: 'tim', depot: 'xanh' };

  function mot(k) { return t(k).replace('\n', ' · '); }
  function nhanLoai(k) { return t('kh_kind_' + k, k).replace('\n', ' · '); }

  /* ------------------------------------------------------------ danh sách */
  function veDanhSach() {
    var khung = document.getElementById('kh-danh-sach');
    if (!khung) return;
    if (!ds.length) {
      khung.innerHTML = '<div class="trong">' + an(mot('common_empty')) + '</div>';
      return;
    }
    khung.innerHTML = ds.map(function (c) {
      return '<div class="ds-muc' + (dangChon && dangChon.id === c.id ? ' dang-chon' : '') +
        '" data-id="' + an(c.id) + '">' +
        '<div style="display:flex;justify-content:space-between;gap:8px;align-items:start">' +
        '<span class="ma">' + an(c.name) + '</span>' +
        '<span class="nhan ' + (MAU[c.kind] || 'xam') + '">' + an(nhanLoai(c.kind)) + '</span></div>' +
        '<div class="phu-de">' + an(c.code) + (c.address ? ' · ' + an(c.address) : '') + '</div>' +
        '<div class="phu-de">' + (c.lat != null ? '📍 ' + c.lat + ', ' + c.lng : an(mot('kh_no_coord'))) + '</div>' +
        '</div>';
    }).join('');
    khung.querySelectorAll('.ds-muc').forEach(function (el) {
      el.addEventListener('click', function () {
        dangChon = ds.filter(function (c) { return c.id === el.dataset.id; })[0] || null;
        dangSua = false;
        veDanhSach(); veChiTiet();
      });
    });
  }

  function napDanhSach() {
    var tim = (document.getElementById('kh-tim') || {}).value || '';
    var loai = (document.getElementById('kh-loc-loai') || {}).value || '';
    var dd = '/api/customers?x=1';
    if (tim.trim()) dd += '&q=' + encodeURIComponent(tim.trim());
    if (loai) dd += '&kind=' + encodeURIComponent(loai);
    return PL.goi(dd).then(function (kq) {
      ds = kq || [];
      if (dangChon) dangChon = ds.filter(function (c) { return c.id === dangChon.id; })[0] || null;
      veDanhSach();
    }).catch(PL.baoLoi);
  }

  /* ------------------------------------------------------------- chi tiết */
  function oTT(nhanChu, giaTri) {
    var chu = String(nhanChu);
    var hai = chu.indexOf('\n') >= 0 ? chu.split('\n') : null;
    return '<div class="o-tt"><div class="nhan-tt">' +
      (hai ? '<span class="d-vi">' + an(hai[0]) + '</span><span class="d-lo">' + an(hai[1]) + '</span>' : an(chu)) +
      '</div><div class="gia-tri-tt">' + an(giaTri) + '</div></div>';
  }

  function veChiTiet() {
    var khung = document.getElementById('kh-chi-tiet');
    if (!khung) return;
    if (dangSua) { veForm(khung, dangChon); return; }
    if (!dangChon) {
      khung.innerHTML = '<div class="the"><div class="trong">' + an(mot('kh_pick_hint')) + '</div></div>';
      return;
    }
    var c = dangChon;
    khung.innerHTML =
      '<div class="the">' +
        '<div class="the-dau">' +
          '<h3>' + an(c.name) + ' <span class="nhan ' + (MAU[c.kind] || 'xam') + '">' + an(nhanLoai(c.kind)) + '</span></h3>' +
          '<div style="display:flex;gap:8px">' +
            '<button type="button" class="nut nho" id="kh-sua">' + an(mot('kh_edit')) + '</button>' +
            '<button type="button" class="nut nguy-hiem nho" id="kh-xoa">' + an(mot('common_delete')) + '</button>' +
          '</div>' +
        '</div>' +
        '<div class="the-than"><div class="luoi-3 thong-tin">' +
          oTT(t('kh_code'), c.code) +
          oTT(t('kh_tax'), c.tax_number || '—') +
          oTT(t('kh_phone'), c.phone || '—') +
          oTT(t('kh_contact'), c.contact_name || '—') +
          oTT(t('kh_address'), c.address || '—') +
          oTT(t('kh_lat') + ' / ' + t('kh_lng').split('\n')[0],
            c.lat != null ? c.lat + ', ' + c.lng : mot('kh_no_coord')) +
        '</div>' +
        (c.note ? '<p class="goi-y" style="margin-top:10px">' + an(c.note) + '</p>' : '') +
        '</div>' +
      '</div>';
    PL.apDungNgonNgu(khung);
    document.getElementById('kh-sua').addEventListener('click', function () { dangSua = true; veChiTiet(); });
    document.getElementById('kh-xoa').addEventListener('click', xoa);
  }

  function veForm(khung, c) {
    c = c || {};
    khung.innerHTML =
      '<div class="the kh-form">' +
        '<div class="the-dau"><h3>' + an(c.id ? mot('kh_edit') : mot('kh_new')) + '</h3></div>' +
        '<div class="the-than">' +
          '<div class="hang-o">' +
            '<label class="o"><span>' + an(mot('kh_code')) + ' *</span><input type="text" id="khf-code" value="' + an(c.code || '') + '"></label>' +
            '<label class="o"><span>' + an(mot('kh_name')) + ' *</span><input type="text" id="khf-name" value="' + an(c.name || '') + '"></label>' +
            '<label class="o"><span>' + an(mot('kh_kind')) + '</span><select id="khf-kind">' +
              LOAI.map(function (k) {
                return '<option value="' + k + '"' + ((c.kind || 'customer') === k ? ' selected' : '') + '>' + an(nhanLoai(k)) + '</option>';
              }).join('') + '</select></label>' +
            '<label class="o"><span>' + an(mot('kh_tax')) + '</span><input type="text" id="khf-tax" value="' + an(c.tax_number || '') + '"></label>' +
            '<label class="o"><span>' + an(mot('kh_phone')) + '</span><input type="text" id="khf-phone" value="' + an(c.phone || '') + '"></label>' +
            '<label class="o"><span>' + an(mot('kh_contact')) + '</span><input type="text" id="khf-contact" value="' + an(c.contact_name || '') + '"></label>' +
          '</div>' +
          '<label class="o"><span>' + an(mot('kh_address')) + '</span><input type="text" id="khf-address" value="' + an(c.address || '') + '"></label>' +
          '<div class="hang-o">' +
            '<label class="o"><span>' + an(mot('kh_lat')) + '</span><input type="number" step="0.000001" id="khf-lat" value="' + (c.lat != null ? c.lat : '') + '"></label>' +
            '<label class="o"><span>' + an(mot('kh_lng')) + '</span><input type="number" step="0.000001" id="khf-lng" value="' + (c.lng != null ? c.lng : '') + '"></label>' +
          '</div>' +
          '<p class="goi-y">' + an(mot('kh_coord_hint')) + '</p>' +
          '<label class="o"><span>' + an(mot('common_note')) + '</span><input type="text" id="khf-note" value="' + an(c.note || '') + '"></label>' +
          '<div class="nut-day">' +
            '<button type="button" class="nut phu" id="khf-huy">' + an(mot('common_cancel')) + '</button>' +
            '<button type="button" class="nut chinh" id="khf-luu">' + an(mot('common_save')) + '</button>' +
          '</div>' +
        '</div>' +
      '</div>';
    document.getElementById('khf-huy').addEventListener('click', function () { dangSua = false; veChiTiet(); });
    document.getElementById('khf-luu').addEventListener('click', function () { luu(c.id); });
  }

  function luu(id) {
    var lat = document.getElementById('khf-lat').value;
    var lng = document.getElementById('khf-lng').value;
    var body = {
      code: document.getElementById('khf-code').value.trim(),
      name: document.getElementById('khf-name').value.trim(),
      kind: document.getElementById('khf-kind').value,
      tax_number: document.getElementById('khf-tax').value.trim(),
      phone: document.getElementById('khf-phone').value.trim(),
      contact_name: document.getElementById('khf-contact').value.trim(),
      address: document.getElementById('khf-address').value.trim(),
      lat: lat === '' ? null : Number(lat),
      lng: lng === '' ? null : Number(lng),
      note: document.getElementById('khf-note').value.trim(),
    };
    var yc = id
      ? PL.goi('/api/customers/' + encodeURIComponent(id), { method: 'PUT', body: body })
      : PL.goi('/api/customers', { method: 'POST', body: body });
    yc.then(function (c) {
      PL.thongBao(mot('ok_kh_saved'));
      dangSua = false;
      dangChon = c;
      return napDanhSach().then(veChiTiet);
    }).catch(PL.baoLoi);
  }

  function xoa() {
    if (!dangChon) return;
    PL.hoiXacNhan({
      tieu_de: mot('kh_delete_title'),
      mo_ta: dangChon.name + ' — ' + t('kh_delete_warn').replace('\n', ' '),
      nguy_hiem: true,
    }).then(function (kq) {
      if (!kq) return;
      PL.goi('/api/customers/' + encodeURIComponent(dangChon.id), { method: 'DELETE' })
        .then(function () {
          PL.thongBao(mot('ok_kh_deleted'));
          dangChon = null;
          return napDanhSach().then(veChiTiet);
        }).catch(PL.baoLoi);
    });
  }

  function veLocLoai() {
    var el = document.getElementById('kh-loc-loai');
    if (!el) return;
    var cu = el.value;
    el.innerHTML = '<option value="">' + an(mot('common_all')) + '</option>' +
      LOAI.map(function (k) { return '<option value="' + k + '">' + an(nhanLoai(k)) + '</option>'; }).join('');
    el.value = cu;
  }

  function khoiDong() {
    veLocLoai();
    document.getElementById('kh-lam-moi').addEventListener('click', napDanhSach);
    document.getElementById('kh-them').addEventListener('click', function () {
      dangChon = null; dangSua = true; veDanhSach(); veChiTiet();
    });
    var hen = null;
    document.getElementById('kh-tim').addEventListener('input', function () {
      clearTimeout(hen); hen = setTimeout(napDanhSach, 300);
    });
    document.getElementById('kh-loc-loai').addEventListener('change', napDanhSach);
    napDanhSach().then(function () {
      if (ds.length && !dangChon) { dangChon = ds[0]; veDanhSach(); veChiTiet(); }
    });
  }

  function veLai() { veLocLoai(); veDanhSach(); veChiTiet(); }

  return { khoiDong: khoiDong, veLai: veLai };
})();

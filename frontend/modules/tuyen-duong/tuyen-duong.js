/* Module Tuyến đường.
 *
 * Nguồn cho ô "Tuyến giao" trên phiếu đóng gói. Trước đây tuyến là ô gõ tay nên
 * ai không gõ thì phiếu in ra để trống và bản đồ không biết vẽ từ đâu tới đâu.
 * Thành danh mục thì khai một lần, mọi phiếu chọn lại, và màn Theo dõi có điểm
 * đầu điểm cuối thật.
 */

window.TuyenDuong = (function () {
  'use strict';

  var t = PL.t, an = PL.an, so = PL.so;
  var ds = [], dsDiem = [], dangChon = null, dangSua = false;

  function mot(k) { return t(k).replace('\n', ' · '); }

  function oTT(nhanChu, giaTri) {
    var chu = String(nhanChu);
    var hai = chu.indexOf('\n') >= 0 ? chu.split('\n') : null;
    return '<div class="o-tt"><div class="nhan-tt">' +
      (hai ? '<span class="d-vi">' + an(hai[0]) + '</span><span class="d-lo">' + an(hai[1]) + '</span>' : an(chu)) +
      '</div><div class="gia-tri-tt">' + an(giaTri) + '</div></div>';
  }

  /* ------------------------------------------------------------ danh sách */
  function veDanhSach() {
    var khung = document.getElementById('td2-danh-sach');
    if (!khung) return;
    if (!ds.length) {
      khung.innerHTML = '<div class="trong">' + an(mot('common_empty')) + '</div>';
      return;
    }
    khung.innerHTML = ds.map(function (r) {
      return '<div class="ds-muc' + (dangChon && dangChon.id === r.id ? ' dang-chon' : '') +
        '" data-id="' + an(r.id) + '">' +
        '<div style="display:flex;justify-content:space-between;gap:8px;align-items:start">' +
        '<span class="ma">' + an(r.code) + '</span>' +
        '<span class="nhan ' + (r.active ? 'xanh' : 'xam') + '">' +
          an(r.active ? mot('rt_active') : mot('rt_inactive')) + '</span></div>' +
        '<div class="phu-de">' + an(r.name) + '</div>' +
        '<div class="rt-doan">' + an(r.from_name || '—') + ' → ' + an(r.to_name || '—') +
          (r.distance_km ? ' · ' + so(r.distance_km, 1) + ' km' : '') + '</div>' +
        '</div>';
    }).join('');
    khung.querySelectorAll('.ds-muc').forEach(function (el) {
      el.addEventListener('click', function () {
        dangChon = ds.filter(function (r) { return r.id === el.dataset.id; })[0] || null;
        dangSua = false;
        veDanhSach(); veChiTiet();
      });
    });
  }

  function napDanhSach() {
    var tim = (document.getElementById('td2-tim') || {}).value || '';
    var dd = '/api/routes?x=1';
    if (tim.trim()) dd += '&q=' + encodeURIComponent(tim.trim());
    return PL.goi(dd).then(function (kq) {
      ds = kq || [];
      if (dangChon) dangChon = ds.filter(function (r) { return r.id === dangChon.id; })[0] || null;
      veDanhSach();
    }).catch(PL.baoLoi);
  }

  function napDiem() {
    return PL.goi('/api/customers').then(function (d) { dsDiem = d || []; }).catch(function () {});
  }

  /* ------------------------------------------------------------- chi tiết */
  function veChiTiet() {
    var khung = document.getElementById('td2-chi-tiet');
    if (!khung) return;
    if (dangSua) { veForm(khung, dangChon); return; }
    if (!dangChon) {
      khung.innerHTML = '<div class="the"><div class="trong">' + an(mot('rt_pick_hint')) + '</div></div>';
      return;
    }
    var r = dangChon;
    khung.innerHTML =
      '<div class="the">' +
        '<div class="the-dau">' +
          '<h3>' + an(r.code) + ' · ' + an(r.name) + '</h3>' +
          '<div style="display:flex;gap:8px">' +
            '<button type="button" class="nut nho" id="td2-sua">' + an(mot('rt_edit')) + '</button>' +
            '<button type="button" class="nut nguy-hiem nho" id="td2-xoa">' + an(mot('common_delete')) + '</button>' +
          '</div>' +
        '</div>' +
        '<div class="the-than">' +
          '<div class="rt-duong">' +
            '<span class="diem">' + an(r.from_name || mot('rt_no_point')) + '</span>' +
            '<span class="mui">→</span>' +
            '<span class="diem">' + an(r.to_name || mot('rt_no_point')) + '</span>' +
            '<span class="km">' + so(r.distance_km, 1) + ' km</span>' +
          '</div>' +
          '<div class="luoi-3 thong-tin" style="margin-top:12px">' +
            oTT(t('rt_code'), r.code) +
            oTT(t('rt_from'), r.from_name || '—') +
            oTT(t('rt_to'), r.to_name || '—') +
            oTT(t('rt_distance'), so(r.distance_km, 1) + ' km') +
            oTT(t('common_status'), r.active ? mot('rt_active') : mot('rt_inactive')) +
            oTT(t('rt_has_coord'),
              (r.from_lat != null && r.to_lat != null) ? mot('common_yes') : mot('rt_coord_missing')) +
          '</div>' +
          (r.note ? '<p class="goi-y" style="margin-top:10px">' + an(r.note) + '</p>' : '') +
        '</div>' +
      '</div>';
    PL.apDungNgonNgu(khung);
    document.getElementById('td2-sua').addEventListener('click', function () { dangSua = true; veChiTiet(); });
    document.getElementById('td2-xoa').addEventListener('click', xoa);
  }

  function oChonDiem(id, chon, nhan) {
    return '<label class="o"><span>' + an(nhan) + '</span><select id="' + id + '">' +
      '<option value="">—</option>' +
      dsDiem.map(function (c) {
        return '<option value="' + an(c.id) + '"' + (chon === c.id ? ' selected' : '') + '>' +
          an(c.name) + ' · ' + an(c.code) + (c.lat == null ? ' (' + an(mot('kh_no_coord')) + ')' : '') +
          '</option>';
      }).join('') + '</select></label>';
  }

  function veForm(khung, r) {
    r = r || {};
    khung.innerHTML =
      '<div class="the rt-form">' +
        '<div class="the-dau"><h3>' + an(r.id ? mot('rt_edit') : mot('rt_new')) + '</h3></div>' +
        '<div class="the-than">' +
          '<div class="hang-o">' +
            '<label class="o"><span>' + an(mot('rt_code')) + ' *</span><input type="text" id="rtf-code" value="' + an(r.code || '') + '"></label>' +
            '<label class="o"><span>' + an(mot('rt_name')) + ' *</span><input type="text" id="rtf-name" value="' + an(r.name || '') + '"></label>' +
          '</div>' +
          '<div class="hang-o">' +
            oChonDiem('rtf-from', r.from_id, mot('rt_from')) +
            oChonDiem('rtf-to', r.to_id, mot('rt_to')) +
            '<label class="o"><span>' + an(mot('rt_distance')) + '</span>' +
              '<input type="number" step="0.1" min="0" id="rtf-km" value="' + (r.distance_km != null ? r.distance_km : 0) + '"></label>' +
          '</div>' +
          '<p class="goi-y">' + an(mot('rt_coord_hint')) + '</p>' +
          '<label class="o"><span>' + an(mot('common_note')) + '</span><input type="text" id="rtf-note" value="' + an(r.note || '') + '"></label>' +
          '<label class="o-lo" style="display:flex;align-items:center;gap:8px">' +
            '<input type="checkbox" id="rtf-active" style="width:auto"' + (r.id && !r.active ? '' : ' checked') + '>' +
            '<span>' + an(mot('rt_active')) + '</span></label>' +
          '<div class="nut-day">' +
            '<button type="button" class="nut phu" id="rtf-huy">' + an(mot('common_cancel')) + '</button>' +
            '<button type="button" class="nut chinh" id="rtf-luu">' + an(mot('common_save')) + '</button>' +
          '</div>' +
        '</div>' +
      '</div>';
    document.getElementById('rtf-huy').addEventListener('click', function () { dangSua = false; veChiTiet(); });
    document.getElementById('rtf-luu').addEventListener('click', function () { luu(r.id); });
  }

  function luu(id) {
    var body = {
      code: document.getElementById('rtf-code').value.trim(),
      name: document.getElementById('rtf-name').value.trim(),
      from_id: document.getElementById('rtf-from').value || null,
      to_id: document.getElementById('rtf-to').value || null,
      distance_km: Number(document.getElementById('rtf-km').value || 0),
      note: document.getElementById('rtf-note').value.trim(),
      active: document.getElementById('rtf-active').checked,
    };
    var yc = id
      ? PL.goi('/api/routes/' + encodeURIComponent(id), { method: 'PUT', body: body })
      : PL.goi('/api/routes', { method: 'POST', body: body });
    yc.then(function (r) {
      PL.thongBao(mot('ok_rt_saved'));
      dangSua = false;
      dangChon = r;
      return napDanhSach().then(veChiTiet);
    }).catch(PL.baoLoi);
  }

  function xoa() {
    if (!dangChon) return;
    PL.hoiXacNhan({
      tieu_de: mot('rt_delete_title'),
      mo_ta: dangChon.name + ' — ' + t('rt_delete_warn').replace('\n', ' '),
      nguy_hiem: true,
    }).then(function (kq) {
      if (!kq) return;
      PL.goi('/api/routes/' + encodeURIComponent(dangChon.id), { method: 'DELETE' })
        .then(function () {
          PL.thongBao(mot('ok_rt_deleted'));
          dangChon = null;
          return napDanhSach().then(veChiTiet);
        }).catch(PL.baoLoi);
    });
  }

  function khoiDong() {
    document.getElementById('td2-lam-moi').addEventListener('click', napDanhSach);
    document.getElementById('td2-them').addEventListener('click', function () {
      dangChon = null; dangSua = true; veDanhSach(); veChiTiet();
    });
    var hen = null;
    document.getElementById('td2-tim').addEventListener('input', function () {
      clearTimeout(hen); hen = setTimeout(napDanhSach, 300);
    });
    napDiem().then(napDanhSach).then(function () {
      if (ds.length && !dangChon) { dangChon = ds[0]; veDanhSach(); veChiTiet(); }
    });
  }

  function veLai() { veDanhSach(); veChiTiet(); }

  return { khoiDong: khoiDong, veLai: veLai };
})();

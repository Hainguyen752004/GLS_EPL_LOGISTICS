/* Module Tuyến đường — dựng theo module Tuyến đường của EPL_System.
 *
 * Một tuyến là một chuỗi CHẶNG A → B → C. Tổng km LÀ tổng các chặng, không ai
 * gõ tay một con số rồi quên sửa. Bản đồ vẽ đúng lộ trình qua từng chặng chứ
 * không phải một đoạn thẳng nối hai đầu.
 */

window.TuyenDuong = (function () {
  'use strict';

  var t = PL.t, an = PL.an, so = PL.so;
  var ds = [], dsDiem = [], dangSua = null;   // dangSua = tuyến đang mở trong form
  var chang = [];                             // các chặng đang soạn
  var banDo = null, lopNen = null, lopVe = null;

  function mot(k) { return t(k).replace('\n', ' · '); }

  /* ------------------------------------------------------------- Leaflet */
  function napLeaflet() {
    if (window.L) return Promise.resolve();
    return new Promise(function (xong, hong) {
      if (!document.querySelector('link[data-leaflet]')) {
        var l = document.createElement('link');
        l.rel = 'stylesheet'; l.dataset.leaflet = '1';
        l.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
        document.head.appendChild(l);
      }
      var sc = document.createElement('script');
      sc.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
      sc.onload = xong;
      sc.onerror = function () { hong(new Error('Leaflet')); };
      document.head.appendChild(sc);
    });
  }

  var NEN = {
    street: { url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png', attr: '&copy; OpenStreetMap' },
    satellite: {
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      attr: 'Tiles &copy; Esri',
    },
  };

  function dungBanDo() {
    var o = document.getElementById('rt-ban-do');
    if (!o || banDo) return;
    banDo = L.map(o, { zoomControl: true }).setView([17.9757, 102.6331], 12);
    doiNen('street');
    lopVe = L.layerGroup().addTo(banDo);
    veBanDo();
  }

  function doiNen(ten) {
    if (!banDo) return;
    if (lopNen) banDo.removeLayer(lopNen);
    lopNen = L.tileLayer(NEN[ten].url, { attribution: NEN[ten].attr, maxZoom: 19 }).addTo(banDo);
    var a = document.getElementById('rt-nen-duong'), b = document.getElementById('rt-nen-ve-tinh');
    if (a) a.classList.toggle('dang-chon', ten === 'street');
    if (b) b.classList.toggle('dang-chon', ten === 'satellite');
  }

  function ghim(lop, chu) {
    return L.divIcon({
      className: '',
      html: '<div class="ghim-chang ' + lop + '">' + an(chu) + '</div>',
      iconSize: [26, 26], iconAnchor: [13, 13],
    });
  }

  function veBanDo() {
    if (!banDo || !lopVe) return;
    lopVe.clearLayers();

    // Chuỗi điểm dọc lộ trình, bỏ điểm trùng liền nhau.
    var diem = [];
    chang.forEach(function (c) {
      [[c.from_lat, c.from_lng, c.from_name], [c.to_lat, c.to_lng, c.to_name]].forEach(function (x) {
        if (x[0] == null || x[1] == null) return;
        var cuoi = diem[diem.length - 1];
        if (cuoi && cuoi[0] === x[0] && cuoi[1] === x[1]) return;
        diem.push(x);
      });
    });

    var ghiChu = document.getElementById('rt-ghi-chu-ban-do');
    if (ghiChu) {
      ghiChu.textContent = diem.length >= 2 ? mot('rt_map_hint') : mot('rt_map_no_coord');
    }
    if (!diem.length) return;

    diem.forEach(function (x, i) {
      var lop = i === 0 ? 'dau' : (i === diem.length - 1 ? 'cuoi' : '');
      lopVe.addLayer(L.marker([x[0], x[1]], { icon: ghim(lop, String(i + 1)) })
        .bindTooltip(String(x[2] || '')));
    });
    if (diem.length >= 2) {
      lopVe.addLayer(L.polyline(diem.map(function (x) { return [x[0], x[1]]; }),
        { color: '#2563eb', weight: 4, opacity: .85 }));
    }
    try {
      banDo.fitBounds(L.latLngBounds(diem.map(function (x) { return [x[0], x[1]]; })).pad(0.3),
        { maxZoom: 14 });
    } catch (e) { /* bỏ qua */ }
  }

  /* ---------------------------------------------------------- danh mục điểm */
  function veGoiYDiem() {
    var dl = document.getElementById('rt-goi-y-diem');
    if (!dl) return;
    dl.innerHTML = dsDiem.map(function (c) {
      return '<option value="' + an(c.name) + '">' + an(c.code) +
        (c.lat == null ? ' · ' + an(mot('kh_no_coord')) : '') + '</option>';
    }).join('');
  }

  function timDiem(ten) {
    var khoa = String(ten || '').trim().toLowerCase();
    return dsDiem.filter(function (c) {
      return (c.name || '').toLowerCase() === khoa || (c.code || '').toLowerCase() === khoa;
    })[0] || null;
  }

  /* --------------------------------------------------------------- chặng */
  function veChang() {
    var tb = document.getElementById('rt-bang-chang');
    if (!tb) return;
    if (!chang.length) {
      tb.innerHTML = '<tr><td colspan="5" class="trong">' + an(mot('rt_no_segment_yet')) + '</td></tr>';
    } else {
      tb.innerHTML = chang.map(function (c, i) {
        var duCho = c.from_lat != null && c.to_lat != null;
        return '<tr>' +
          '<td class="giua">' + (i + 1) + '</td>' +
          '<td><div class="diem">' + an(c.from_name) + '</div>' +
            '<div class="' + (c.from_lat != null ? 'co-toa-do' : 'thieu-toa-do') + '">' +
            an(c.from_lat != null ? '📍 ' + c.from_lat + ', ' + c.from_lng : mot('kh_no_coord')) + '</div></td>' +
          '<td><div class="diem">' + an(c.to_name) + '</div>' +
            '<div class="' + (c.to_lat != null ? 'co-toa-do' : 'thieu-toa-do') + '">' +
            an(c.to_lat != null ? '📍 ' + c.to_lat + ', ' + c.to_lng : mot('kh_no_coord')) + '</div></td>' +
          '<td class="phai">' + so(c.distance_km, 1) + ' km</td>' +
          '<td class="phai">' +
            '<button type="button" class="nut nho" data-len="' + i + '"' + (i === 0 ? ' disabled' : '') + '>↑</button> ' +
            '<button type="button" class="nut nho nguy-hiem" data-bo="' + i + '">×</button>' +
          '</td>' +
        '</tr>';
      }).join('');
      tb.querySelectorAll('[data-bo]').forEach(function (n) {
        n.addEventListener('click', function () {
          chang.splice(Number(n.dataset.bo), 1);
          veChang();
        });
      });
      tb.querySelectorAll('[data-len]').forEach(function (n) {
        n.addEventListener('click', function () {
          var i = Number(n.dataset.len);
          if (i <= 0) return;
          var tam = chang[i - 1]; chang[i - 1] = chang[i]; chang[i] = tam;
          veChang();
        });
      });
    }

    var tong = chang.reduce(function (a, c) { return a + Number(c.distance_km || 0); }, 0);
    var oTong = document.getElementById('rt-tong-km');
    if (oTong) oTong.textContent = so(tong, 1) + ' km';
    veBanDo();
  }

  function themChang() {
    var oDi = document.getElementById('rt-chang-di');
    var oDen = document.getElementById('rt-chang-den');
    var oKm = document.getElementById('rt-chang-km');
    var tenDi = (oDi.value || '').trim();
    var tenDen = (oDen.value || '').trim();
    if (!tenDi || !tenDen) { PL.baoLoi({ ma: 'RT_SEGMENT_NO_POINT' }); return; }
    var km = Number(oKm.value || 0);
    if (km < 0) { PL.baoLoi({ ma: 'RT_KM_NEGATIVE' }); return; }

    var di = timDiem(tenDi), den = timDiem(tenDen);
    chang.push({
      from_id: di ? di.id : null, to_id: den ? den.id : null,
      from_name: di ? di.name : tenDi, to_name: den ? den.name : tenDen,
      distance_km: km,
      from_lat: di ? di.lat : null, from_lng: di ? di.lng : null,
      to_lat: den ? den.lat : null, to_lng: den ? den.lng : null,
    });
    // Chặng kế tiếp thường bắt đầu ở nơi chặng này kết thúc — điền sẵn cho nhanh.
    oDi.value = tenDen;
    oDen.value = '';
    oKm.value = '';
    veChang();
    oDen.focus();
  }

  /* ------------------------------------------------------------- danh sách */
  function veChonTuyen() {
    var el = document.getElementById('rt-chon-tuyen');
    if (!el) return;
    el.innerHTML = '<option value="">' + an(mot('rt_pick_saved')) + '</option>' +
      ds.map(function (r) {
        return '<option value="' + an(r.id) + '"' + (dangSua && dangSua.id === r.id ? ' selected' : '') + '>' +
          an(r.code) + ' · ' + an(r.name) + ' · ' + so(r.distance_km, 1) + ' km' +
          (r.active ? '' : ' (' + an(mot('rt_inactive')) + ')') + '</option>';
      }).join('');
  }

  function napDanhSach() {
    return PL.goi('/api/routes').then(function (kq) {
      ds = kq || [];
      veChonTuyen();
    }).catch(PL.baoLoi);
  }

  function moTuyen(id) {
    var r = ds.filter(function (x) { return x.id === id; })[0];
    if (!r) { formTrong(); return; }
    dangSua = r;
    document.getElementById('rt-ma').value = r.code || '';
    document.getElementById('rt-ten').value = r.name || '';
    chang = (r.segments || []).map(function (c) { return Object.assign({}, c); });
    document.getElementById('rt-xoa').hidden = false;
    veChonTuyen();
    veChang();
  }

  function formTrong() {
    dangSua = null;
    chang = [];
    ['rt-ma', 'rt-ten', 'rt-chang-di', 'rt-chang-den', 'rt-chang-km'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.value = '';
    });
    var x = document.getElementById('rt-xoa');
    if (x) x.hidden = true;
    veChonTuyen();
    veChang();
  }

  function luu() {
    if (!chang.length) { PL.baoLoi({ ma: 'RT_NO_SEGMENT' }); return; }
    var body = {
      code: document.getElementById('rt-ma').value.trim(),
      name: document.getElementById('rt-ten').value.trim(),
      active: true,
      segments: chang.map(function (c) {
        return {
          from_id: c.from_id, to_id: c.to_id,
          from_name: c.from_name, to_name: c.to_name,
          distance_km: c.distance_km,
        };
      }),
    };
    var yc = dangSua
      ? PL.goi('/api/routes/' + encodeURIComponent(dangSua.id), { method: 'PUT', body: body })
      : PL.goi('/api/routes', { method: 'POST', body: body });
    yc.then(function (r) {
      PL.thongBao(mot('ok_rt_saved'));
      return napDanhSach().then(function () { moTuyen(r.id); });
    }).catch(PL.baoLoi);
  }

  function xoa() {
    if (!dangSua) return;
    PL.hoiXacNhan({
      tieu_de: mot('rt_delete_title'),
      mo_ta: dangSua.name + ' — ' + t('rt_delete_warn').replace('\n', ' '),
      nguy_hiem: true,
    }).then(function (kq) {
      if (!kq) return;
      PL.goi('/api/routes/' + encodeURIComponent(dangSua.id), { method: 'DELETE' })
        .then(function () {
          PL.thongBao(mot('ok_rt_deleted'));
          formTrong();
          return napDanhSach();
        }).catch(PL.baoLoi);
    });
  }

  /* ------------------------------------------------------------- khởi động */
  function khoiDong() {
    banDo = null;
    document.getElementById('rt-them').addEventListener('click', formTrong);
    document.getElementById('rt-huy').addEventListener('click', formTrong);
    document.getElementById('rt-luu').addEventListener('click', luu);
    document.getElementById('rt-xoa').addEventListener('click', xoa);
    document.getElementById('rt-nut-them-chang').addEventListener('click', themChang);
    document.getElementById('rt-chang-km').addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); themChang(); }
    });
    document.getElementById('rt-chon-tuyen').addEventListener('change', function (e) {
      if (e.target.value) moTuyen(e.target.value); else formTrong();
    });
    document.getElementById('rt-nen-duong').addEventListener('click', function () { doiNen('street'); });
    document.getElementById('rt-nen-ve-tinh').addEventListener('click', function () { doiNen('satellite'); });

    PL.goi('/api/customers').then(function (d) {
      dsDiem = d || [];
      veGoiYDiem();
    }).catch(function () {}).then(napDanhSach).then(function () {
      if (ds.length) moTuyen(ds[0].id); else formTrong();
    });

    napLeaflet().then(dungBanDo).catch(function () {
      var o = document.getElementById('rt-ban-do');
      if (o) o.innerHTML = '<div class="trong">' + an(mot('err_NETWORK')) + '</div>';
    });
  }

  function veLai() {
    veGoiYDiem();
    veChonTuyen();
    veChang();
  }

  return { khoiDong: khoiDong, veLai: veLai };
})();

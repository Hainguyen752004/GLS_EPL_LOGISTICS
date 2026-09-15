/* Module Theo dõi xe — xe của chuyến nào đang ở đâu.
 *
 * Bản đồ Leaflet, nền OSM/Esri như EPL_System. Vị trí lấy từ máy chủ; bản demo
 * chưa có GPS nên có nút "chạy tiếp" mô phỏng để thấy xe nhích trên bản đồ.
 */

window.TheoDoi = (function () {
  'use strict';

  var t = PL.t, an = PL.an, so = PL.so;
  var ds = [], dangChon = null, chiTiet = null;
  var banDo = null, lopNen = null, lopVe = null, henLamMoi = null;
  var MAU_GH = { planned: 'xam', loading: 'lam', in_transit: 'cam', arrived: 'tim', delivered: 'xanh', cancelled: 'do' };

  function mot(k) { return t(k).replace('\n', ' · '); }
  function nhanGH(ma) { return t('dl_status_' + ma, ma).replace('\n', ' · '); }

  /* ------------------------------------------------------------ Leaflet */
  function napLeaflet() {
    if (window.L) return Promise.resolve();
    return new Promise(function (xong, hong) {
      if (!document.querySelector('link[data-leaflet]')) {
        var l = document.createElement('link');
        l.rel = 'stylesheet'; l.dataset.leaflet = '1';
        l.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
        document.head.appendChild(l);
      }
      var s = document.createElement('script');
      s.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
      s.onload = xong;
      s.onerror = function () { hong(new Error('Leaflet')); };
      document.head.appendChild(s);
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
    var o = document.getElementById('td-ban-do');
    if (!o || banDo) return;
    banDo = L.map(o, { zoomControl: true }).setView([17.9757, 102.6331], 12);
    doiNen('street');
    lopVe = L.layerGroup().addTo(banDo);
  }

  function doiNen(ten) {
    if (!banDo) return;
    if (lopNen) banDo.removeLayer(lopNen);
    lopNen = L.tileLayer(NEN[ten].url, { attribution: NEN[ten].attr, maxZoom: 19 }).addTo(banDo);
    var a = document.getElementById('td-nen-duong'), b = document.getElementById('td-nen-ve-tinh');
    if (a) a.classList.toggle('dang-chon', ten === 'street');
    if (b) b.classList.toggle('dang-chon', ten === 'satellite');
  }

  function ghim(lop, mau, chu) {
    return L.divIcon({ className: '', html: '<div class="' + lop + ' ' + (mau || '') + '">' + (chu || '') + '</div>',
      iconSize: lop === 'ghim-xe' ? [34, 34] : [14, 14], iconAnchor: lop === 'ghim-xe' ? [17, 17] : [7, 7] });
  }

  function veBanDo() {
    if (!banDo || !lopVe) return;
    lopVe.clearLayers();
    var diem = [];

    ds.forEach(function (c) {
      var p = c.position;
      if (!p) return;
      var laChon = dangChon === c.delivery.id;
      var lop = c.delivery.status === 'arrived' ? 'toi-noi' : (c.stale ? 'cu' : '');
      var m = L.marker([p.lat, p.lng], { icon: ghim('ghim-xe', lop, '🚚'), zIndexOffset: laChon ? 1000 : 0 })
        .bindTooltip(c.delivery.code + ' · ' + (c.delivery.plate_head || ''), { permanent: laChon, direction: 'top' });
      m.on('click', function () { chon(c.delivery.id); });
      lopVe.addLayer(m);
      diem.push([p.lat, p.lng]);
    });

    if (chiTiet) {
      var kho = chiTiet.depot, dich = chiTiet.destination;
      if (kho && kho.lat != null) {
        lopVe.addLayer(L.marker([kho.lat, kho.lng], { icon: ghim('ghim-diem', 'kho') })
          .bindTooltip(mot('trk_depot') + ': ' + (kho.name || '')));
        diem.push([kho.lat, kho.lng]);
      }
      if (dich && dich.lat != null) {
        lopVe.addLayer(L.marker([dich.lat, dich.lng], { icon: ghim('ghim-diem', 'dich') })
          .bindTooltip(mot('trk_destination') + ': ' + (dich.name || '')));
        diem.push([dich.lat, dich.lng]);
        if (kho && kho.lat != null) {
          lopVe.addLayer(L.polyline([[kho.lat, kho.lng], [dich.lat, dich.lng]],
            { color: '#94a3b8', weight: 3, dashArray: '6 8' }));
        }
      }
      var vet = (chiTiet.trail || []).map(function (m) { return [m.lat, m.lng]; });
      if (vet.length > 1) {
        lopVe.addLayer(L.polyline(vet, { color: '#2563eb', weight: 4, opacity: .85 }));
      }
    }

    if (diem.length) {
      try { banDo.fitBounds(L.latLngBounds(diem).pad(0.25), { maxZoom: 14 }); } catch (e) { /* bỏ qua */ }
    }
  }

  /* ------------------------------------------------------------ danh sách */
  function veDanhSach() {
    var khung = document.getElementById('td-danh-sach');
    if (!khung) return;
    if (!ds.length) {
      khung.innerHTML = '<div class="trong">' + an(mot('trk_none')) + '</div>';
      return;
    }
    khung.innerHTML = ds.map(function (c) {
      var g = c.delivery, p = c.position;
      var tienDo = p ? Math.round((p.progress || 0) * 100) : 0;
      return '<div class="ds-muc td-muc' + (dangChon === g.id ? ' dang-chon' : '') +
        (g.status === 'arrived' ? ' toi-noi' : '') + '" data-id="' + an(g.id) + '">' +
        '<div style="display:flex;justify-content:space-between;gap:8px;align-items:start">' +
          '<span class="ma">' + an(g.code) + '</span>' +
          '<span class="nhan ' + (MAU_GH[g.status] || 'xam') + '">' + an(nhanGH(g.status)) + '</span></div>' +
        '<div class="phu-de">' + an(g.plate_head || '—') + (g.plate_trailer ? ' / ' + an(g.plate_trailer) : '') +
          ' · ' + an(g.driver_name || '—') + '</div>' +
        '<div class="phu-de">' + an(c.orders.join(', ')) + ' → ' + an((c.destination && c.destination.name) || '—') + '</div>' +
        '<div class="dong-so">' +
          (p ? '<span>' + an(mot('trk_remaining')) + ': <b>' + (c.remaining_km != null ? so(c.remaining_km, 1) + ' km' : '—') + '</b></span>' +
               '<span>' + an(mot('trk_speed')) + ': <b>' + so(p.speed_kmh, 0) + ' km/h</b></span>'
             : '<span>' + an(mot('trk_no_position')) + '</span>') +
          (c.stale ? '<span class="nhan cam">' + an(mot('trk_stale')) + '</span>' : '') +
        '</div>' +
        '<div class="thanh"><span style="width:' + tienDo + '%"></span></div>' +
        '</div>';
    }).join('');
    khung.querySelectorAll('.ds-muc').forEach(function (el) {
      el.addEventListener('click', function () { chon(el.dataset.id); });
    });
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
    var khung = document.getElementById('td-chi-tiet');
    if (!khung) return;
    if (!chiTiet) {
      khung.innerHTML = '<div class="trong">' + an(mot(ds.length ? 'dl_pick_hint' : 'trk_none')) + '</div>';
      return;
    }
    var c = chiTiet, g = c.delivery, p = c.position;
    var td = document.getElementById('td-tieu-de-ban-do');
    if (td) td.textContent = g.code + ' · ' + (g.plate_head || '');

    khung.innerHTML =
      (c.stale ? '<div class="canh-bao-cu" style="margin-bottom:10px">' + an(mot('trk_stale')) + '</div>' : '') +
      (!c.destination || c.destination.lat == null
        ? '<div class="canh-bao-cu" style="margin-bottom:10px">' + an(mot('trk_no_destination')) + '</div>' : '') +
      '<div class="luoi-3 thong-tin">' +
        oTT(t('common_status'), nhanGH(g.status)) +
        oTT(t('dl_driver'), (g.driver_name || '—') + (g.driver_phone ? ' · ' + g.driver_phone : '')) +
        oTT(t('so_code'), c.orders.join(', ') || '—') +
        oTT(t('trk_depot'), (c.depot && c.depot.name) || '—') +
        oTT(t('trk_destination'), (c.destination && c.destination.name) || '—') +
        oTT(t('trk_route_km'), c.route_km != null ? so(c.route_km, 1) + ' km' : '—') +
        oTT(t('trk_position'), p ? p.lat.toFixed(5) + ', ' + p.lng.toFixed(5) : mot('trk_no_position')) +
        oTT(t('trk_remaining'), c.remaining_km != null ? so(c.remaining_km, 1) + ' km' : '—') +
        oTT(t('trk_speed'), p ? so(p.speed_kmh, 0) + ' km/h' : '—') +
        oTT(t('trk_progress'), p ? Math.round((p.progress || 0) * 100) + '%' : '—') +
        oTT(t('trk_last_update'), p ? PL.gio(p.recorded_at) : '—') +
        oTT(t('trk_trail'), String((c.trail || []).length)) +
      '</div>' +
      '<div class="day-nut">' +
        (g.status !== 'delivered' && g.status !== 'cancelled'
          ? '<button type="button" class="nut chinh nho" id="td-mo-phong">' + an(mot('trk_simulate')) + '</button>' : '') +
        '<button type="button" class="nut nho" id="td-mo-chuyen">' + an(mot('trk_open_delivery')) + '</button>' +
        '<span class="goi-y" style="margin:0">' + an(mot('trk_simulate_hint')) + '</span>' +
      '</div>';

    var mp = document.getElementById('td-mo-phong');
    if (mp) mp.addEventListener('click', moPhong);
    document.getElementById('td-mo-chuyen').addEventListener('click', function () {
      try { localStorage.setItem('PL_DEMO_GH_DANG_CHON', g.id); } catch (e) { /* bỏ qua */ }
      PL.moMan('giao-hang');
    });
  }

  function moPhong() {
    if (!dangChon) return;
    PL.goi('/api/tracking/' + encodeURIComponent(dangChon) + '/simulate', { method: 'POST', body: { step: 0.15 } })
      .then(function () {
        PL.thongBao(mot('ok_trk_moved'));
        return napTatCa();
      }).catch(PL.baoLoi);
  }

  /* ------------------------------------------------------------------ nạp */
  function chon(id) {
    dangChon = id;
    try { localStorage.setItem('PL_DEMO_TD_DANG_CHON', id); } catch (e) { /* bỏ qua */ }
    veDanhSach();
    return PL.goi('/api/tracking/' + encodeURIComponent(id)).then(function (c) {
      chiTiet = c;
      veChiTiet();
      veBanDo();
    }).catch(PL.baoLoi);
  }

  function napTatCa() {
    return PL.goi('/api/tracking').then(function (kq) {
      ds = kq || [];
      if (dangChon && !ds.some(function (c) { return c.delivery.id === dangChon; })) { dangChon = null; chiTiet = null; }
      if (!dangChon && ds.length) {
        var luu = null;
        try { luu = localStorage.getItem('PL_DEMO_TD_DANG_CHON') || localStorage.getItem('PL_DEMO_GH_DANG_CHON'); } catch (e) { /* bỏ qua */ }
        dangChon = (ds.filter(function (c) { return c.delivery.id === luu; })[0] || ds[0]).delivery.id;
      }
      veDanhSach();
      if (dangChon) return chon(dangChon);
      chiTiet = null; veChiTiet(); veBanDo();
      return null;
    }).catch(PL.baoLoi);
  }

  function datLamMoi() {
    clearInterval(henLamMoi);
    var o = document.getElementById('td-tu-lam-moi');
    if (o && o.checked) henLamMoi = setInterval(function () {
      if (!document.getElementById('td-ban-do')) { clearInterval(henLamMoi); return; }
      napTatCa();
    }, 30000);
  }

  function khoiDong() {
    document.getElementById('td-lam-moi').addEventListener('click', napTatCa);
    document.getElementById('td-tu-lam-moi').addEventListener('change', datLamMoi);
    document.getElementById('td-nen-duong').addEventListener('click', function () { doiNen('street'); });
    document.getElementById('td-nen-ve-tinh').addEventListener('click', function () { doiNen('satellite'); });
    banDo = null;
    napLeaflet().then(dungBanDo).catch(function () {
      var o = document.getElementById('td-ban-do');
      if (o) o.innerHTML = '<div class="trong">' + an(mot('err_NETWORK')) + '</div>';
    }).then(napTatCa).then(datLamMoi);
  }

  function veLai() { veDanhSach(); veChiTiet(); veBanDo(); }

  return { khoiDong: khoiDong, veLai: veLai };
})();

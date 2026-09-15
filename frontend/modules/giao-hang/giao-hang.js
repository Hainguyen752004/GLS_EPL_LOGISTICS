/* Module Giao hàng.
 *
 * Một chuyến chở nhiều Packing List. Người nhận ký nhận theo TỪNG Packing List
 * chứ không ký một lần cho cả chuyến — vì một chuyến có thể chở hàng của nhiều
 * đơn, nhiều cửa hàng, và trách nhiệm phải rõ từng phiếu.
 */

window.GiaoHang = (function () {
  'use strict';

  var t = PL.t, an = PL.an, so = PL.so;
  var dsChuyen = [], dangChon = null;
  var dsXe = [], dsTaiXe = [], dsCho = [];
  var buc = null;   // canvas chữ ký đang mở

  var BUOC = ['planned', 'loading', 'in_transit', 'arrived', 'delivered'];
  var MAU = {
    planned: 'xam', loading: 'lam', in_transit: 'cam',
    arrived: 'tim', delivered: 'xanh', cancelled: 'do',
  };
  var MAU_PL = {
    ready: 'xam', parked: 'lam', gate_in: 'tim',
    loaded: 'cam', dispatched: 'cam', delivered: 'xanh', cancelled: 'do',
  };

  function mot(khoa) { return t(khoa).replace('\n', ' · '); }
  function nhanGH(ma) { return t('dl_status_' + ma, ma).replace('\n', ' · '); }
  function nhanPL(ma) { return t('pack_status_' + ma, ma).replace('\n', ' · '); }

  function oTT(nhanChu, giaTri) {
    var chu = String(nhanChu);
    var hai = chu.indexOf('\n') >= 0 ? chu.split('\n') : null;
    return '<div class="o-tt"><div class="nhan-tt">' +
      (hai ? '<span class="d-vi">' + an(hai[0]) + '</span><span class="d-lo">' + an(hai[1]) + '</span>'
           : an(chu)) +
      '</div><div class="gia-tri-tt">' + an(giaTri) + '</div></div>';
  }

  /* --------------------------------------------------------------- số liệu */
  function veSoLieu(tk) {
    var khung = document.getElementById('gh-so-lieu');
    if (!khung || !tk) return;
    khung.innerHTML = [
      ['common_total', tk.total],
      ['dl_status_planned', tk.planned],
      ['dl_status_loading', tk.loading],
      ['dl_status_in_transit', tk.in_transit],
      ['dl_status_arrived', tk.arrived],
      ['dl_status_delivered', tk.delivered],
    ].map(function (x) {
      return '<div class="o-so"><div class="nhan-so">' + PL.oChu(x[0]) +
        '</div><div class="gia-tri">' + so(x[1], 0) + '</div></div>';
    }).join('');
  }

  /* ------------------------------------------------------------ danh sách */
  function veDanhSach() {
    var khung = document.getElementById('gh-danh-sach');
    if (!khung) return;
    if (!dsChuyen.length) {
      khung.innerHTML = '<div class="trong">' + an(mot('common_empty')) + '</div>';
      return;
    }
    khung.innerHTML = dsChuyen.map(function (g) {
      return '<div class="ds-muc' + (dangChon && dangChon.id === g.id ? ' dang-chon' : '') +
        '" data-id="' + an(g.id) + '">' +
        '<div style="display:flex;justify-content:space-between;gap:8px;align-items:start">' +
        '<span class="ma">' + an(g.code) + '</span>' +
        '<span class="nhan ' + (MAU[g.status] || 'xam') + '">' + an(nhanGH(g.status)) + '</span></div>' +
        '<div class="phu-de">' + an(g.plate_head || '—') +
          (g.plate_trailer ? ' / ' + an(g.plate_trailer) : '') +
          ' · ' + an(g.driver_name || '—') + '</div>' +
        '<div class="phu-de">' + an(mot('dl_packing_lists')) + ': ' + g.packing_list_count + '</div>' +
        '</div>';
    }).join('');
    khung.querySelectorAll('.ds-muc').forEach(function (el) {
      el.addEventListener('click', function () { moChuyen(el.dataset.id); });
    });
  }

  function napDanhSach() {
    var tim = (document.getElementById('gh-tim') || {}).value || '';
    var tt = (document.getElementById('gh-loc-trang-thai') || {}).value || '';
    var dd = '/api/deliveries?page_size=100';
    if (tim.trim()) dd += '&q=' + encodeURIComponent(tim.trim());
    if (tt) dd += '&status=' + encodeURIComponent(tt);
    return PL.goi(dd).then(function (kq) {
      dsChuyen = (kq && kq.items) || [];
      veDanhSach();
    }).catch(PL.baoLoi);
  }

  /* ------------------------------------------------------------- chi tiết */
  function veChuoiBuoc(tt) {
    if (tt === 'cancelled') return '<span class="nhan do">' + an(nhanGH('cancelled')) + '</span>';
    var vt = BUOC.indexOf(tt);
    return '<div class="chuoi-buoc">' + BUOC.map(function (b, i) {
      var lop = i < vt ? 'xong' : (i === vt ? 'hien-tai' : '');
      return (i ? '<span class="noi"></span>' : '') +
        '<span class="buoc ' + lop + '"><span class="cham"></span>' + an(nhanGH(b)) + '</span>';
    }).join('') + '</div>';
  }

  function veChiTiet() {
    var khung = document.getElementById('gh-chi-tiet');
    if (!khung) return;
    if (!dangChon) {
      khung.innerHTML = '<div class="the"><div class="trong">' + an(mot('dl_pick_hint')) + '</div></div>';
      return;
    }
    var g = dangChon;
    var vt = BUOC.indexOf(g.status);
    var buocSau = g.status !== 'cancelled' && vt >= 0 && vt < BUOC.length - 1 ? BUOC[vt + 1] : null;

    khung.innerHTML =
      '<div class="the">' +
        '<div class="the-dau">' +
          '<h3>' + an(g.code) + '</h3>' +
          '<div class="day-nut" style="margin:0">' +
            (buocSau ? '<button type="button" class="nut chinh nho" id="gh-buoc-sau">' +
              an(mot('pack_next_step')) + ': ' + an(nhanGH(buocSau)) + '</button>' : '') +
            '<button type="button" class="nut nho" id="gh-xem-ban-do">' + an(mot('dl_view_map')) + '</button>' +
            (g.status === 'planned' || g.status === 'loading'
              ? '<button type="button" class="nut nguy-hiem nho" id="gh-huy">' +
                an(mot('dl_cancel_title')) + '</button>' : '') +
          '</div>' +
        '</div>' +
        '<div class="the-than">' +
          veChuoiBuoc(g.status) +
          '<div class="luoi-3 thong-tin" style="margin-top:12px">' +
            oTT(t('dl_plate_head'), g.plate_head || '—') +
            oTT(t('dl_plate_trailer'), g.plate_trailer || '—') +
            oTT(t('dl_driver'), (g.driver_name || '—') + (g.driver_phone ? ' · ' + g.driver_phone : '')) +
            oTT(t('dl_route'), g.route_name || '—') +
            oTT(t('dl_departed_at'), PL.gio(g.departed_at)) +
            oTT(t('dl_completed_at'), PL.gio(g.completed_at)) +
            oTT(t('so_case_qty'), so(g.total_cases, 0)) +
            oTT(t('so_weight'), so(g.total_weight_kg, 2) + ' kg') +
          '</div>' +
        '</div>' +
      '</div>' +

      '<div class="the">' +
        '<div class="the-dau"><h3 data-i18n="dl_packing_lists"></h3></div>' +
        '<div class="the-than luoi-phieu">' +
          (g.packing_lists || []).map(vePhieuTrenChuyen).join('') +
        '</div>' +
      '</div>' +

      '<div class="the">' +
        '<div class="the-dau"><h3 data-i18n="common_history"></h3></div>' +
        '<div class="bang-cuon"><table class="bang"><thead><tr>' +
          '<th data-i18n="common_time"></th><th data-i18n="common_status"></th>' +
          '<th data-i18n="common_actor"></th><th data-i18n="common_note"></th>' +
        '</tr></thead><tbody>' +
        (g.events || []).slice().reverse().map(function (ev) {
          return '<tr><td>' + an(PL.gio(ev.occurred_at)) + '</td>' +
            '<td>' + an(t('dl_status_' + ev.event_type, ev.event_type).replace('\n', ' · ')) + '</td>' +
            '<td>' + an(ev.actor) + '</td><td>' + an(ev.note || '') + '</td></tr>';
        }).join('') +
        '</tbody></table></div>' +
      '</div>';

    PL.apDungNgonNgu(khung);

    if (buocSau) {
      document.getElementById('gh-buoc-sau').addEventListener('click', function () {
        PL.goi('/api/deliveries/' + encodeURIComponent(g.id) + '/status', {
          method: 'POST', body: { status: buocSau },
        }).then(function () {
          PL.thongBao(mot('ok_dl_status'));
          return lamMoi(g.id);
        }).catch(PL.baoLoi);
      });
    }
    var nutHuy = document.getElementById('gh-huy');
    if (nutHuy) nutHuy.addEventListener('click', huyChuyen);
    document.getElementById('gh-xem-ban-do').addEventListener('click', function () {
      try { localStorage.setItem('PL_DEMO_TD_DANG_CHON', g.id); } catch (e) { /* bỏ qua */ }
      PL.moMan('theo-doi');
    });

    khung.querySelectorAll('.nut-pod').forEach(function (n) {
      n.addEventListener('click', function () { moFormPOD(n.dataset.pl); });
    });
    khung.querySelectorAll('.nut-bo-phieu').forEach(function (n) {
      n.addEventListener('click', function () { boPhieu(n.dataset.pl); });
    });
  }

  function vePhieuTrenChuyen(p) {
    var daKy = !!p.pod_received_by;
    return '<div class="phieu' + (daKy ? ' da-ky' : '') + '">' +
      '<div class="phieu-dau">' +
        '<b>' + an(p.id) + '</b>' +
        '<span class="nhan ' + (MAU_PL[p.status] || 'xam') + '">' + an(nhanPL(p.status)) + '</span>' +
      '</div>' +
      '<div class="phieu-than">' +
        '<div>' + an(mot('pack_belongs_to')) + ': <b>' + an(p.so_id) + '</b>' +
          (p.po_number ? ' · PO ' + an(p.po_number) : '') + '</div>' +
        '<div>' + an(p.store_name || '') + '</div>' +
        '<div>' + so(p.box_count, 0) + ' ' + an(mot('pack_package_no')) +
          ' · ' + so(p.total_cases, 0) + ' ' + an(t('so_case_qty').split('\n')[0]) +
          ' · ' + so(p.total_weight_kg, 2) + ' kg</div>' +
      '</div>' +
      '<div class="phieu-chan">' +
        (daKy
          ? '<span class="nhan xanh">' + an(mot('pod_done')) + ': ' + an(p.pod_received_by) + '</span>'
          : '<span class="nhan cam">' + an(mot('pod_pending')) + '</span>') +
        (p.status === 'dispatched' && !daKy
          ? '<button type="button" class="nut chinh nho nut-pod" data-pl="' + an(p.id) + '">' +
            an(mot('pod_save')) + '</button>' : '') +
        (dangChon && (dangChon.status === 'planned' || dangChon.status === 'loading')
          ? '<button type="button" class="nut nho nut-bo-phieu" data-pl="' + an(p.id) + '">' +
            an(mot('common_remove')) + '</button>' : '') +
      '</div>' +
    '</div>';
  }

  /* ------------------------------------------------------------------ POD */
  function moFormPOD(pl_id) {
    var nen = document.getElementById('pl-hop-thoai');
    nen.innerHTML =
      '<div class="hop hop-pod">' +
        '<h3>' + an(mot('pod_title')) + ' — ' + an(pl_id) + '</h3>' +
        '<label class="o"><span>' + an(mot('pod_received_by')) + ' *</span>' +
          '<input type="text" id="pod-nguoi-nhan"></label>' +
        '<label class="o"><span>' + an(mot('pod_result')) + '</span><select id="pod-ket-qua">' +
          ['full', 'short', 'failed', 'returned'].map(function (k) {
            return '<option value="' + k + '">' + an(mot('pod_result_' + k)) + '</option>';
          }).join('') +
        '</select></label>' +
        '<label class="o"><span>' + an(mot('pod_condition')) + '</span>' +
          '<input type="text" id="pod-tinh-trang" placeholder="' + an(mot('pod_condition_ph')) + '"></label>' +
        '<label class="o"><span>' + an(mot('common_note')) + '</span>' +
          '<input type="text" id="pod-ghi-chu"></label>' +
        '<div class="o"><span class="nhan-ky">' + an(mot('pod_signature')) + '</span>' +
          '<canvas id="pod-chu-ky" class="o-chu-ky" width="420" height="140"></canvas>' +
          '<div class="duoi-ky"><span>' + an(mot('pod_signature_hint')) + '</span>' +
            '<button type="button" class="nut nho" id="pod-xoa-ky">' + an(mot('pod_clear_signature')) + '</button>' +
          '</div>' +
        '</div>' +
        '<div class="nut-day">' +
          '<button type="button" class="nut phu" id="pod-dong">' + an(mot('common_cancel')) + '</button>' +
          '<button type="button" class="nut chinh" id="pod-luu">' + an(mot('pod_save')) + '</button>' +
        '</div>' +
      '</div>';
    nen.classList.add('hien');

    batDauKy(document.getElementById('pod-chu-ky'));
    document.getElementById('pod-xoa-ky').onclick = function () { xoaKy(); };
    document.getElementById('pod-dong').onclick = function () { dongHop(); };
    nen.onclick = function (e) { if (e.target === nen) dongHop(); };
    document.getElementById('pod-luu').onclick = function () {
      var ten = document.getElementById('pod-nguoi-nhan').value.trim();
      if (!ten) { PL.baoLoi({ ma: 'POD_NO_RECEIVER' }); return; }
      PL.goi('/api/packing-lists/' + encodeURIComponent(pl_id) + '/pod', {
        method: 'POST',
        body: {
          received_by: ten,
          result: document.getElementById('pod-ket-qua').value,
          goods_condition: document.getElementById('pod-tinh-trang').value.trim(),
          note: document.getElementById('pod-ghi-chu').value.trim(),
          signature_data: buc && buc.coNet ? buc.canvas.toDataURL('image/png') : null,
        },
      }).then(function () {
        dongHop();
        PL.thongBao(mot('ok_pod'));
        return lamMoi(dangChon ? dangChon.id : null);
      }).catch(PL.baoLoi);
    };
  }

  function dongHop() {
    var nen = document.getElementById('pl-hop-thoai');
    nen.classList.remove('hien');
    nen.innerHTML = '';
    buc = null;
  }

  function batDauKy(canvas) {
    if (!canvas) return;
    var ctx = canvas.getContext('2d');
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#0f172a';
    buc = { canvas: canvas, ctx: ctx, coNet: false, dangVe: false };

    function toa_do(e) {
      var r = canvas.getBoundingClientRect();
      var x = (e.touches ? e.touches[0].clientX : e.clientX) - r.left;
      var y = (e.touches ? e.touches[0].clientY : e.clientY) - r.top;
      return { x: x * (canvas.width / r.width), y: y * (canvas.height / r.height) };
    }
    function batDau(e) {
      e.preventDefault();
      buc.dangVe = true;
      var p = toa_do(e);
      ctx.beginPath();
      ctx.moveTo(p.x, p.y);
    }
    function ve(e) {
      if (!buc.dangVe) return;
      e.preventDefault();
      var p = toa_do(e);
      ctx.lineTo(p.x, p.y);
      ctx.stroke();
      buc.coNet = true;
    }
    function dung() { buc.dangVe = false; }

    canvas.addEventListener('mousedown', batDau);
    canvas.addEventListener('mousemove', ve);
    window.addEventListener('mouseup', dung);
    canvas.addEventListener('touchstart', batDau, { passive: false });
    canvas.addEventListener('touchmove', ve, { passive: false });
    canvas.addEventListener('touchend', dung);
  }

  function xoaKy() {
    if (!buc) return;
    buc.ctx.clearRect(0, 0, buc.canvas.width, buc.canvas.height);
    buc.coNet = false;
  }

  /* ---------------------------------------------------------------- lập chuyến */
  function veChoXep() {
    var khung = document.getElementById('gh-cho-xep');
    if (!khung) return;
    if (!dsCho.length) {
      khung.innerHTML = '<div class="trong">' + an(mot('common_empty')) + '</div>';
      return;
    }
    khung.innerHTML = dsCho.map(function (p) {
      return '<label class="muc-chon"><input type="checkbox" value="' + an(p.id) + '">' +
        '<span><b>' + an(p.id) + '</b> · ' + an(p.so_id) +
        (p.po_number ? ' · PO ' + an(p.po_number) : '') +
        '<span class="phu-mo">' + an(p.store_name || '') + ' · ' +
        so(p.box_count, 0) + ' ' + an(mot('pack_package_no')) + '</span></span></label>';
    }).join('');
  }

  function napChoXep() {
    return PL.goi('/api/packing-lists?page_size=100').then(function (kq) {
      dsCho = ((kq && kq.items) || []).filter(function (p) {
        return !p.delivery_id && ['ready', 'parked', 'gate_in'].indexOf(p.status) >= 0;
      });
      veChoXep();
    }).catch(PL.baoLoi);
  }

  function luuChuyen() {
    var chon = [];
    document.querySelectorAll('#gh-cho-xep input:checked').forEach(function (o) { chon.push(o.value); });
    if (!chon.length) { PL.baoLoi({ ma: 'DL_NO_PACKING_LIST' }); return; }
    PL.goi('/api/deliveries', {
      method: 'POST',
      body: {
        packing_list_ids: chon,
        vehicle_id: document.getElementById('gh-xe').value || null,
        driver_id: document.getElementById('gh-tai-xe').value || null,
        route_name: document.getElementById('gh-tuyen').value.trim(),
      },
    }).then(function (g) {
      PL.thongBao(mot('ok_dl_created') + ' ' + g.code);
      document.getElementById('gh-form').hidden = true;
      return lamMoi(g.id);
    }).catch(PL.baoLoi);
  }

  function boPhieu(pl_id) {
    PL.goi('/api/deliveries/' + encodeURIComponent(dangChon.id) + '/packing-lists/' +
      encodeURIComponent(pl_id), { method: 'DELETE' })
      .then(function () {
        PL.thongBao(mot('ok_dl_removed'));
        return lamMoi(dangChon.id);
      }).catch(PL.baoLoi);
  }

  function huyChuyen() {
    PL.hoiXacNhan({
      tieu_de: mot('dl_cancel_title'),
      mo_ta: t('dl_cancel_warn').replace('\n', ' '),
      o_nhap: true, nguy_hiem: true,
    }).then(function (kq) {
      if (!kq) return;
      PL.goi('/api/deliveries/' + encodeURIComponent(dangChon.id) + '/cancel', {
        method: 'POST', body: { reason: kq.chu },
      }).then(function () {
        PL.thongBao(mot('ok_dl_cancelled'));
        return lamMoi(dangChon.id);
      }).catch(PL.baoLoi);
    });
  }

  /* ----------------------------------------------------------------- chung */
  function moChuyen(id) {
    if (!id) return Promise.resolve();
    return PL.goi('/api/deliveries/' + encodeURIComponent(id)).then(function (g) {
      dangChon = g;
      veDanhSach();
      veChiTiet();
    }).catch(PL.baoLoi);
  }

  function lamMoi(mo_id) {
    return Promise.all([
      napDanhSach(),
      napChoXep(),
      PL.goi('/api/deliveries/stats').then(veSoLieu).catch(function () {}),
    ]).then(function () { return moChuyen(mo_id || (dangChon && dangChon.id)); });
  }

  function veDanhMuc() {
    var xe = document.getElementById('gh-xe');
    if (xe) {
      xe.innerHTML = '<option value="">—</option>' + dsXe.map(function (v) {
        return '<option value="' + an(v.id) + '">' + an(v.plate_head) +
          (v.plate_trailer ? ' / ' + an(v.plate_trailer) : '') +
          (v.internal_no ? ' · ' + an(v.internal_no) : '') + '</option>';
      }).join('');
    }
    var tx = document.getElementById('gh-tai-xe');
    if (tx) {
      tx.innerHTML = '<option value="">—</option>' + dsTaiXe.map(function (d) {
        return '<option value="' + an(d.id) + '">' + an(d.full_name) + '</option>';
      }).join('');
    }
  }

  function veLocTrangThai() {
    var el = document.getElementById('gh-loc-trang-thai');
    if (!el) return;
    var cu = el.value;
    el.innerHTML = '<option value="">' + an(mot('common_all')) + '</option>' +
      BUOC.concat(['cancelled']).map(function (x) {
        return '<option value="' + x + '">' + an(nhanGH(x)) + '</option>';
      }).join('');
    el.value = cu;
  }

  function khoiDong() {
    veLocTrangThai();
    document.getElementById('gh-bat-tat-form').addEventListener('click', function () {
      var f = document.getElementById('gh-form');
      f.hidden = !f.hidden;
      if (!f.hidden) napChoXep();
    });
    document.getElementById('gh-luu').addEventListener('click', luuChuyen);
    document.getElementById('gh-lam-moi').addEventListener('click', napDanhSach);

    var hen = null;
    document.getElementById('gh-tim').addEventListener('input', function () {
      clearTimeout(hen); hen = setTimeout(napDanhSach, 300);
    });
    document.getElementById('gh-loc-trang-thai').addEventListener('change', napDanhSach);

    Promise.all([
      PL.goi('/api/vehicles').then(function (d) { dsXe = d || []; }).catch(function () {}),
      PL.goi('/api/drivers').then(function (d) { dsTaiXe = d || []; }).catch(function () {}),
    ]).then(veDanhMuc);

    napDanhSach().then(function () {
      var luu = null;
      try { luu = localStorage.getItem('PL_DEMO_GH_DANG_CHON'); } catch (e) { /* bỏ qua */ }
      var dau = dsChuyen.filter(function (x) { return x.id === luu; })[0] || dsChuyen[0];
      if (dau) moChuyen(dau.id);
    });
    napChoXep();
    PL.goi('/api/deliveries/stats').then(veSoLieu).catch(function () {});
  }

  function veLai() {
    veLocTrangThai();
    veDanhMuc();
    veChoXep();
    veDanhSach();
    veChiTiet();
    PL.goi('/api/deliveries/stats').then(veSoLieu).catch(function () {});
  }

  return { khoiDong: khoiDong, veLai: veLai };
})();

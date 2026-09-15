/* Module Packing List — nơi hàng của đơn được đóng thành từng phiếu.
 *
 * Hai thứ màn này phải nói rõ cho người dùng:
 *   · mỗi dòng hàng CÒN LẠI bao nhiêu (để không đóng vượt);
 *   · mỗi kiện đang cầm THUỘC đơn nào, dòng nào (in thẳng lên tem và phiếu).
 */

window.PackingList = (function () {
  'use strict';

  var t = PL.t, an = PL.an, so = PL.so;
  var dsDon = [];
  var donDangChon = null;     // dữ liệu đầy đủ của đơn đang đóng
  var dsPL = [];
  var plDangChon = null;
  var dsTuyen = [];     // danh mục tuyến đường — nguồn cho ô chọn "Tuyến giao"

  var BUOC = ['ready', 'parked', 'gate_in', 'loaded', 'dispatched', 'delivered'];
  var MAU = {
    ready: 'xam', parked: 'lam', gate_in: 'tim',
    loaded: 'cam', dispatched: 'cam', delivered: 'xanh', cancelled: 'do',
  };

  function nhan(ma) { return t('pack_status_' + ma, ma).replace('\n', ' · '); }
  function mot(khoa) { return t(khoa).replace('\n', ' · '); }

  /* --------------------------------------------------------------- số liệu */
  function veSoLieu(tk) {
    var khung = document.getElementById('pk-so-lieu');
    if (!khung || !tk) return;
    var o = [
      ['common_total', tk.total, ''],
      ['pack_status_ready', tk.ready, 'xam'],
      ['pack_status_parked', tk.parked, 'lam'],
      ['pack_status_gate_in', tk.gate_in, 'tim'],
      ['pack_status_dispatched', tk.dispatched, 'cam'],
      ['pack_status_delivered', tk.delivered, 'xanh'],
    ];
    khung.innerHTML = o.map(function (x) {
      return '<div class="o-so"><div class="nhan-so">' + PL.oChu(x[0]) +
        '</div><div class="gia-tri">' + so(x[1], 0) + '</div></div>';
    }).join('');
  }

  /* ------------------------------------------------------- khung đóng gói */
  function veKhungDongGoi() {
    var khung = document.getElementById('pk-khung-dong-goi');
    if (!khung) return;
    if (!donDangChon) {
      khung.innerHTML = '<div class="trong">' + an(mot('pack_pick_order_first')) + '</div>';
      return;
    }
    var d = donDangChon;
    var conLai = (d.lines || []).filter(function (x) {
      return x.remaining_case_qty > 0 || x.remaining_piece_qty > 0;
    });

    if (!conLai.length) {
      khung.innerHTML = '<div class="tinh-trang du">' + an(mot('pack_no_remaining')) + '</div>';
      return;
    }

    khung.innerHTML =
      '<div class="bang-cuon"><table class="bang" id="pk-bang-dong"><thead><tr>' +
        '<th class="giua" data-i18n="so_line_no"></th>' +
        '<th data-i18n="so_description"></th>' +
        '<th class="phai" data-i18n="so_case_qty"></th>' +
        '<th class="phai" data-i18n="so_packed"></th>' +
        '<th class="phai" data-i18n="so_remaining"></th>' +
        '<th class="phai" style="width:130px" data-i18n="pack_qty_to_pack"></th>' +
      '</tr></thead><tbody>' +
      conLai.map(function (x) {
        return '<tr data-line="' + x.id + '" data-con="' + x.remaining_case_qty + '">' +
          '<td class="giua">' + x.line_no + '</td>' +
          '<td>' + an(x.description) +
            (x.barcode ? '<div class="phu-mo"><code>' + an(x.barcode) + '</code></div>' : '') + '</td>' +
          '<td class="phai">' + so(x.case_qty, 0) + '</td>' +
          '<td class="phai">' + so(x.packed_case_qty, 0) + '</td>' +
          '<td class="phai"><b class="con">' + so(x.remaining_case_qty, 0) + '</b></td>' +
          '<td><input type="number" class="o-dong phai" min="0" max="' + x.remaining_case_qty +
            '" value="0"></td>' +
        '</tr>';
      }).join('') +
      '</tbody></table></div>' +

      '<div class="hang-o" style="margin-top:12px">' +
        '<label class="o"><span data-i18n="pack_box_count"></span>' +
          '<input type="number" id="pk-so-kien" min="1" value="1"></label>' +
        '<label class="o"><span data-i18n="pack_route"></span><select id="pk-tuyen">' +
          '<option value="">' + an(mot('rt_pick')) + '</option>' +
          dsTuyen.filter(function (r) { return r.active; }).map(function (r) {
            return '<option value="' + an(r.id) + '">' + an(r.code) + ' · ' + an(r.name) +
              (r.distance_km ? ' (' + so(r.distance_km, 1) + ' km)' : '') + '</option>';
          }).join('') +
        '</select></label>' +
        '<label class="o"><span data-i18n="pack_wave"></span><input type="text" id="pk-dot"></label>' +
        '<label class="o"><span data-i18n="pack_gate"></span><input type="text" id="pk-cong"></label>' +
      '</div>' +
      '<p class="goi-y" data-i18n="pack_box_hint"></p>' +

      '<div class="day-nut">' +
        '<button type="button" class="nut chinh" id="pk-tao" data-i18n="pack_new"></button>' +
        '<span class="ngan"></span>' +
        '<span class="nhan-chia" data-i18n="pack_auto_count"></span>' +
        '<input type="number" id="pk-so-phieu" min="1" max="50" value="2" class="o-nho">' +
        '<button type="button" class="nut" id="pk-chia" data-i18n="pack_auto"></button>' +
      '</div>' +
      '<p class="goi-y" data-i18n="pack_auto_hint"></p>' +
      '<div style="margin-top:6px"><button type="button" class="nut nho" id="pk-quan-ly-tuyen">' +
        an(mot('rt_manage')) + '</button></div>';

    PL.apDungNgonNgu(khung);

    // Gõ số lượng tới đâu, số kiện gợi ý theo tới đó — người dùng khỏi tự cộng.
    khung.querySelectorAll('.o-dong').forEach(function (o) {
      o.addEventListener('input', function () {
        var tong = 0;
        khung.querySelectorAll('.o-dong').forEach(function (x) { tong += Number(x.value || 0); });
        var oKien = document.getElementById('pk-so-kien');
        if (oKien && !oKien.dataset.tuSua) oKien.value = Math.max(tong, 1);
      });
    });
    var oKien = document.getElementById('pk-so-kien');
    if (oKien) oKien.addEventListener('input', function () { oKien.dataset.tuSua = '1'; });

    document.getElementById('pk-tao').addEventListener('click', taoPhieu);
    document.getElementById('pk-chia').addEventListener('click', chiaTuDong);
    document.getElementById('pk-quan-ly-tuyen').addEventListener('click', function () {
      PL.moMan('tuyen-duong');
    });
  }

  function taoPhieu() {
    var mon = [];
    document.querySelectorAll('#pk-bang-dong tbody tr').forEach(function (tr) {
      var sl = Number(tr.querySelector('.o-dong').value || 0);
      if (sl > 0) mon.push({ so_line_id: Number(tr.dataset.line), case_qty: sl, piece_qty: 0 });
    });
    if (!mon.length) {
      PL.baoLoi({ ma: 'PL_NO_ITEMS' });
      return;
    }
    PL.goi('/api/sales-orders/' + encodeURIComponent(donDangChon.id) + '/packing-lists', {
      method: 'POST',
      body: {
        items: mon,
        box_count: Number((document.getElementById('pk-so-kien') || {}).value || 1),
        route_id: (document.getElementById('pk-tuyen') || {}).value || null,
        wave: (document.getElementById('pk-dot') || {}).value || '',
        gate: (document.getElementById('pk-cong') || {}).value || '',
      },
    }).then(function (pl) {
      PL.thongBao(mot('ok_pl_created') + ' ' + pl.id);
      return lamMoiTatCa(pl.id);
    }).catch(PL.baoLoi);
  }

  function chiaTuDong() {
    var n = Number((document.getElementById('pk-so-phieu') || {}).value || 1);
    PL.goi('/api/sales-orders/' + encodeURIComponent(donDangChon.id) + '/packing-lists/auto', {
      method: 'POST', body: { count: n },
    }).then(function (ds) {
      PL.thongBao(mot('ok_pl_split') + ' (' + (ds || []).length + ')');
      return lamMoiTatCa(ds && ds.length ? ds[0].id : null);
    }).catch(PL.baoLoi);
  }

  /* ------------------------------------------------------------ danh sách */
  function veDanhSach() {
    var khung = document.getElementById('pk-danh-sach');
    if (!khung) return;
    if (!dsPL.length) {
      khung.innerHTML = '<div class="trong">' + an(mot('common_empty')) + '</div>';
      return;
    }
    khung.innerHTML = dsPL.map(function (p) {
      return '<div class="ds-muc' + (plDangChon && plDangChon.id === p.id ? ' dang-chon' : '') +
        '" data-id="' + an(p.id) + '">' +
        '<div style="display:flex;justify-content:space-between;gap:8px;align-items:start">' +
        '<span class="ma">' + an(p.id) + '</span>' +
        '<span class="nhan ' + (MAU[p.status] || 'xam') + '">' + an(nhan(p.status)) + '</span></div>' +
        '<div class="phu-de">' + an(mot('pack_belongs_to')) + ' ' + an(p.so_id) +
          (p.po_number ? ' · PO ' + an(p.po_number) : '') + '</div>' +
        '<div class="phu-de">' + so(p.box_count, 0) + ' ' + an(mot('pack_package_no')) +
          ' · ' + so(p.total_cases, 0) + ' ' + an(t('so_case_qty').split('\n')[0]) + '</div>' +
        '</div>';
    }).join('');
    khung.querySelectorAll('.ds-muc').forEach(function (el) {
      el.addEventListener('click', function () { moPL(el.dataset.id); });
    });
  }

  function napDanhSach() {
    var tim = (document.getElementById('pk-tim') || {}).value || '';
    var tt = (document.getElementById('pk-loc-trang-thai') || {}).value || '';
    var chi = (document.getElementById('pk-chi-don-nay') || {}).checked;
    var dd = '/api/packing-lists?page_size=100';
    if (tim.trim()) dd += '&q=' + encodeURIComponent(tim.trim());
    if (tt) dd += '&status=' + encodeURIComponent(tt);
    if (chi && donDangChon) dd += '&so_id=' + encodeURIComponent(donDangChon.id);
    return PL.goi(dd).then(function (kq) {
      dsPL = (kq && kq.items) || [];
      veDanhSach();
    }).catch(PL.baoLoi);
  }

  /* ------------------------------------------------------------- chi tiết */
  function veChuoiBuoc(tt) {
    if (tt === 'cancelled') {
      return '<span class="nhan do">' + an(nhan('cancelled')) + '</span>';
    }
    var vt = BUOC.indexOf(tt);
    return '<div class="chuoi-buoc">' + BUOC.map(function (b, i) {
      var lop = i < vt ? 'xong' : (i === vt ? 'hien-tai' : '');
      return (i ? '<span class="noi"></span>' : '') +
        '<span class="buoc ' + lop + '"><span class="cham"></span>' + an(nhan(b)) + '</span>';
    }).join('') + '</div>';
  }

  function veChiTiet() {
    var khung = document.getElementById('pk-chi-tiet');
    if (!khung) return;
    if (!plDangChon) {
      khung.innerHTML = '<div class="the"><div class="trong">' + an(mot('pack_pick_hint')) + '</div></div>';
      return;
    }
    var p = plDangChon;
    var vt = BUOC.indexOf(p.status);
    var buocSau = p.status !== 'cancelled' && vt >= 0 && vt < BUOC.length - 1 ? BUOC[vt + 1] : null;

    khung.innerHTML =
      '<div class="the">' +
        '<div class="the-dau">' +
          '<h3>' + an(p.id) + '</h3>' +
          '<div class="day-nut" style="margin:0">' +
            (buocSau
              ? '<button type="button" class="nut chinh nho" id="pk-buoc-sau">' +
                an(mot('pack_next_step')) + ': ' + an(nhan(buocSau)) + '</button>' : '') +
            '<button type="button" class="nut nho" id="pk-in-tem">' + an(mot('pack_print_labels')) + '</button>' +
            '<button type="button" class="nut nho" id="pk-in-phieu">' + an(mot('pack_print_list')) + '</button>' +
            (p.status !== 'cancelled' && p.status !== 'dispatched' && p.status !== 'delivered'
              ? '<button type="button" class="nut nguy-hiem nho" id="pk-huy">' +
                an(mot('common_delete')) + '</button>' : '') +
          '</div>' +
        '</div>' +
        '<div class="the-than">' +
          veChuoiBuoc(p.status) +
          '<div class="luoi-3 thong-tin" style="margin-top:12px">' +
            oTT(t('pack_belongs_to'), p.so_id + (p.po_number ? ' · PO ' + p.po_number : '')) +
            oTT(t('pack_store'), p.store_name || '—') +
            oTT(t('pack_route'), p.route_name || '—') +
            oTT(t('pack_box_count'), so(p.box_count, 0)) +
            oTT(t('so_case_qty'), so(p.total_cases, 0)) +
            oTT(t('so_weight'), so(p.total_weight_kg, 2) + ' kg') +
          '</div>' +
          (p.pod
            ? '<div class="tinh-trang du" style="margin-top:12px">' + an(mot('pod_done')) + ': ' +
              an(p.pod.received_by || '') + ' · ' + an(PL.gio(p.pod.received_at)) + '</div>'
            : '') +
        '</div>' +
      '</div>' +

      '<div class="the">' +
        '<div class="the-dau"><h3 data-i18n="pack_items"></h3></div>' +
        '<div class="bang-cuon"><table class="bang"><thead><tr>' +
          '<th data-i18n="pack_from_line"></th>' +
          '<th data-i18n="so_barcode"></th>' +
          '<th data-i18n="so_description"></th>' +
          '<th class="phai" data-i18n="so_case_qty"></th>' +
          '<th class="phai" data-i18n="so_weight"></th>' +
        '</tr></thead><tbody>' +
        (p.items || []).map(function (it) {
          return '<tr><td class="giua"><b>#' + (it.line_no || '?') + '</b>' +
            '<div class="phu-mo">' + an(it.so_id) + '</div></td>' +
            '<td><code>' + an(it.barcode || '—') + '</code></td>' +
            '<td>' + an(it.description || '') + '</td>' +
            '<td class="phai">' + so(it.case_qty, 0) + '</td>' +
            '<td class="phai">' + so(it.weight_kg, 2) + '</td></tr>';
        }).join('') +
        '</tbody></table></div>' +
      '</div>' +

      '<div class="the">' +
        '<div class="the-dau"><h3 data-i18n="pack_list_qr"></h3></div>' +
        '<div class="the-than qr-phieu">' +
          '<img alt="QR" src="/api/packing-lists/' + encodeURIComponent(p.id) + '/qr.svg">' +
          '<div><b>PL:' + an(p.id) + '</b><div class="phu-mo">' + an(mot('in_scan_hint')) + '</div></div>' +
        '</div>' +
      '</div>' +

      '<div class="the">' +
        '<div class="the-dau"><h3 data-i18n="pack_labels"></h3></div>' +
        '<div class="the-than luoi-tem">' +
          (p.labels || []).map(function (lb) { return veTem(p, lb); }).join('') +
        '</div>' +
      '</div>' +

      '<div class="the">' +
        '<div class="the-dau"><h3 data-i18n="common_history"></h3></div>' +
        '<div class="bang-cuon"><table class="bang"><thead><tr>' +
          '<th data-i18n="common_time"></th><th data-i18n="common_status"></th>' +
          '<th data-i18n="common_actor"></th><th data-i18n="common_note"></th>' +
        '</tr></thead><tbody>' +
        (p.events || []).slice().reverse().map(function (ev) {
          return '<tr><td>' + an(PL.gio(ev.occurred_at)) + '</td>' +
            '<td>' + an(t('pack_status_' + ev.event_type, ev.event_type).replace('\n', ' · ')) + '</td>' +
            '<td>' + an(ev.actor) + '</td><td>' + an(ev.note || '') + '</td></tr>';
        }).join('') +
        '</tbody></table></div>' +
      '</div>';

    PL.apDungNgonNgu(khung);

    if (buocSau) {
      document.getElementById('pk-buoc-sau').addEventListener('click', function () {
        PL.goi('/api/packing-lists/' + encodeURIComponent(p.id) + '/status', {
          method: 'POST', body: { status: buocSau },
        }).then(function () {
          PL.thongBao(mot('ok_pl_status'));
          return lamMoiTatCa(p.id);
        }).catch(PL.baoLoi);
      });
    }
    document.getElementById('pk-in-tem').addEventListener('click', function () { inTem(p); });
    document.getElementById('pk-in-phieu').addEventListener('click', function () { inPhieu(p); });
    var nutHuy = document.getElementById('pk-huy');
    if (nutHuy) nutHuy.addEventListener('click', function () { huyPhieu(p); });
  }

  function oTT(nhanChu, giaTri) {
    var chu = String(nhanChu);
    var hai = chu.indexOf('\n') >= 0 ? chu.split('\n') : null;
    return '<div class="o-tt"><div class="nhan-tt">' +
      (hai ? '<span class="d-vi">' + an(hai[0]) + '</span><span class="d-lo">' + an(hai[1]) + '</span>'
           : an(chu)) +
      '</div><div class="gia-tri-tt">' + an(giaTri) + '</div></div>';
  }

  /* --------------------------------------------------------------- tem QR */
  function veTem(p, lb) {
    return '<div class="tem">' +
      '<div class="tem-dau">' +
        '<b>' + an(p.id) + '</b>' +
        '<span>' + lb.package_no + ' / ' + lb.package_total + '</span>' +
      '</div>' +
      '<img class="tem-qr" alt="QR" src="/api/labels/' + encodeURIComponent(lb.qr_token) + '/qr.svg">' +
      '<div class="tem-chan">' +
        '<div>' + an(mot('pack_belongs_to')) + ': <b>' + an(p.so_id) + '</b></div>' +
        (p.po_number ? '<div>PO: ' + an(p.po_number) + '</div>' : '') +
        '<div>' + an(p.store_name || '') + '</div>' +
        '<code>' + an(lb.qr_token) + '</code>' +
      '</div>' +
    '</div>';
  }

  /* Nhãn KHUNG của hai biểu mẫu giữ nguyên tiếng Anh, KHÔNG dịch theo nút ngôn
   * ngữ. Đây là biểu mẫu chuẩn của kho — y như chữ PURCHASE ORDER trên phiếu
   * của CP ALL. Tem dán lên thùng đi qua Việt · Lào · Thái nên nhãn tiếng Anh
   * là thứ cả ba bên đọc được. Phần NỘI DUNG (tên hàng, tên cửa hàng) vẫn là dữ
   * liệu thật nên vẫn ra đúng tiếng của hàng hoá. */
  var NHAN_IN = {
    rdc: 'RDC LAOS', store: 'STORE', route: 'ROUTE', wave: 'WAVE', gate: 'GATE',
    to: 'TO', so: 'SO', po: 'PO', item: 'ITEM', pack: 'PACK',
    weight: 'Weight', cube: 'Cube',
    packingList: 'Packing List', date: 'Date', storeName: 'Store',
    storeId: 'Store ID', box: 'Box',
    no: 'No', barcode: 'Barcode', idLaos: 'Item ID Laos', idThai: 'Item ID Thai',
    desc: 'Item Description', cas: 'Case', piece: 'Piece',
    totalWeight: 'Total weight (kg)', total: 'TOTAL',
  };

  /* ----------------------------------------------------------------- in ấn
   * Hai bản in đi theo ĐÚNG hai mẫu của EPL_System: mẫu 1 là tem kiện, mẫu 2 là
   * phiếu Packing List. Cửa sổ in là tài liệu riêng nên bộ dịch của trang không
   * với tới — mọi chữ phải dịch ngay lúc dựng chuỗi. */
  function moCuaSoIn(tieu_de, than, css) {
    var w = window.open('', '_blank', 'width=960,height=760');
    if (!w) { PL.thongBao(mot('err_UNKNOWN'), 'loi'); return; }
    w.document.write(
      '<!doctype html><html><head><meta charset="utf-8"><title>' + an(tieu_de) + '</title>' +
      '<style>' +
      'body{font:13px/1.45 Arial,"Segoe UI","Noto Sans Lao",sans-serif;color:#000;margin:0;padding:16px}' +
      '.thanh-in{display:flex;justify-content:flex-end;padding:0 0 12px}' +
      '.thanh-in button{padding:8px 16px;font:inherit;font-weight:700;border:1px solid #cbd5e1;border-radius:6px;background:#f8fafc;cursor:pointer}' +
      '@media print{.thanh-in{display:none}body{padding:0}}' +
      (css || '') +
      '</style></head><body>' +
      '<div class="thanh-in"><button onclick="window.print()">' + an(mot('in_print_button')) + '</button></div>' +
      than + '</body></html>'
    );
    w.document.close();
    w.focus();
  }

  /* Mẫu 2 — phiếu Packing List: RDC / Packing List / Đơn ở góc trái, QR của
   * phiếu ở góc phải, bảng đầu Date · Store · Store ID · Box, bảng hàng, dòng TỔNG. */
  function inPhieu(p) {
    var ngay = new Date(p.created_at && p.created_at.indexOf('Z') < 0 ? p.created_at + 'Z' : p.created_at);
    var ngayChu = isNaN(ngay.getTime()) ? '' : ngay.getDate() + '/' + (ngay.getMonth() + 1) + '/' + ngay.getFullYear();
    var tongThung = 0, tongCai = 0, tongKg = 0;
    var hang = (p.items || []).map(function (it, i) {
      tongThung += Number(it.case_qty || 0); tongCai += Number(it.piece_qty || 0); tongKg += Number(it.weight_kg || 0);
      return '<tr>' +
        '<td>' + (i + 1) + '</td>' +
        '<td>' + an(it.barcode || '-') + '</td>' +
        '<td>' + an(it.product_code || '-') + '</td>' +
        '<td>-</td>' +
        '<td>' + an(it.description || '') + (it.description_en ? '<div class="mo">' + an(it.description_en) + '</div>' : '') + '</td>' +
        '<td>' + so(it.case_qty, 0) + '</td>' +
        '<td>' + so(it.piece_qty, 0) + '</td>' +
        '<td>' + so(it.weight_kg, 3) + '</td>' +
      '</tr>';
    }).join('');

    var than =
      '<div class="dau">' +
        '<div class="trai">' +
          '<div><b>RDC:</b> ' + an(p.route_name || mot('in_rdc')) + '</div>' +
          '<div>' + an(NHAN_IN.packingList) + ': ' + an(p.id) + '</div>' +
          '<div>' + an(NHAN_IN.so) + ': ' + an(p.so_id) + (p.po_number ? ' · ' + an(NHAN_IN.po) + ' ' + an(p.po_number) : '') + '</div>' +
        '</div>' +
        '<div class="phai">' +
          '<img src="/api/packing-lists/' + encodeURIComponent(p.id) + '/qr.svg" alt="QR">' +
          '<div class="mo">' + an(mot('in_scan_hint')) + '</div>' +
        '</div>' +
      '</div>' +
      '<h1>' + an(NHAN_IN.packingList) + '</h1>' +
      '<table class="bang-dau"><tr>' +
        '<td><b>' + an(NHAN_IN.date) + '</b><br>' + an(ngayChu) + '</td>' +
        '<td><b>' + an(NHAN_IN.storeName) + '</b><br>' + an(p.store_name || '-') + '</td>' +
        '<td><b>' + an(NHAN_IN.storeId) + '</b><br>' + an(p.store_code || '-') + '</td>' +
        '<td><b>' + an(NHAN_IN.box) + '</b><br>' + so(p.box_count, 0) + '</td>' +
      '</tr></table>' +
      '<table class="bang-hang"><thead><tr>' +
        '<th>' + an(NHAN_IN.no) + '</th><th>' + an(NHAN_IN.barcode) + '</th>' +
        '<th>' + an(NHAN_IN.idLaos) + '</th><th>' + an(NHAN_IN.idThai) + '</th>' +
        '<th>' + an(NHAN_IN.desc) + '</th><th>' + an(NHAN_IN.cas) + '</th>' +
        '<th>' + an(NHAN_IN.piece) + '</th><th>' + an(NHAN_IN.totalWeight) + '</th>' +
      '</tr></thead><tbody>' + hang +
      '<tr class="tong"><td colspan="5">' + an(NHAN_IN.total) + '</td>' +
        '<td>' + so(tongThung, 0) + '</td><td>' + so(tongCai, 0) + '</td><td>' + so(tongKg, 3) + '</td></tr>' +
      '</tbody></table>';

    moCuaSoIn(mot('in_packing_list') + ' ' + p.id, than,
      '.dau{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;font-size:16px;line-height:1.5}' +
      '.dau .trai div:first-child{font-weight:700}' +
      '.dau .phai{text-align:center;width:170px}.dau img{width:150px;height:150px;display:block;margin:0 auto}' +
      '.mo{color:#475569;font-size:11px}' +
      'h1{text-align:center;font-size:30px;margin:10px 0 12px}' +
      'table{width:100%;border-collapse:collapse}' +
      'td,th{border:1px solid #000;padding:6px 8px;text-align:left;vertical-align:top}' +
      '.bang-dau td{font-size:16px}.bang-dau b{display:block;font-size:17px}' +
      '.bang-hang{margin-top:12px;font-size:13px}.bang-hang th{font-weight:700}' +
      '.bang-hang .tong td{font-weight:700}');
  }

  /* Mẫu 1 — tem kiện: RDC LAOS, bốn ô STORE · ROUTE · WAVE · GATE, dòng TO,
   * QR + Đơn / ITEM / PACK / Weight / Cube, số kiện n/N ở góc. Mỗi kiện một tem,
   * mỗi tem một trang khi in. */
  function inTem(p) {
    PL.goi('/api/packing-lists/' + encodeURIComponent(p.id) + '/print', {
      method: 'POST', body: { reprint: true },
    }).then(function (moi) {
      var soMat = (p.items || []).length;
      var than = (moi.labels || []).map(function (lb) {
        return '<div class="tem">' +
          '<div class="rdc">' + an(NHAN_IN.rdc) + '</div>' +
          '<table class="bon-o"><tr>' +
            '<td><div class="nh">' + an(NHAN_IN.store) + '</div><div class="gt">' + an(p.store_code || p.store_name || '-') + '</div></td>' +
            '<td><div class="nh">' + an(NHAN_IN.route) + '</div><div class="gt">' + an(p.route_name || '-') + '</div></td>' +
            '<td><div class="nh">' + an(NHAN_IN.wave) + '</div><div class="gt">' + an(p.wave || '-') + '</div></td>' +
            '<td><div class="nh">' + an(NHAN_IN.gate) + '</div><div class="gt">' + an(p.gate || '-') + '</div></td>' +
          '</tr></table>' +
          '<div class="to"><b>' + an(NHAN_IN.to) + ':</b> ' + an(p.store_name || '-') + '</div>' +
          '<div class="duoi">' +
            '<img src="/api/labels/' + encodeURIComponent(lb.qr_token) + '/qr.svg" alt="QR">' +
            '<div class="tt">' +
              '<div>' + an(NHAN_IN.so) + ': <b>' + an(p.so_id) + '</b>' + (p.po_number ? ' &nbsp; ' + an(NHAN_IN.po) + ': <b>' + an(p.po_number) + '</b>' : '') + '</div>' +
              '<div>' + an(NHAN_IN.item) + ': <b>' + soMat + '</b> &nbsp; ' + an(NHAN_IN.pack) + ': <b>' + so(p.box_count, 0) + '</b></div>' +
              '<div>' + an(NHAN_IN.weight) + ': <b>' + so(p.total_weight_kg, 3) + ' kg</b></div>' +
              '<div>' + an(NHAN_IN.cube) + ': <b>' + so(p.total_cube_m3, 3) + ' m³</b></div>' +
            '</div>' +
            '<div class="so-kien">' + lb.package_no + '/' + lb.package_total + '</div>' +
          '</div>' +
        '</div>';
      }).join('');

      moCuaSoIn(mot('pack_print_labels') + ' ' + p.id, than,
        '.tem{border:2px solid #000;padding:14px 16px;margin-bottom:14px;page-break-after:always;break-after:page}' +
        '.tem:last-child{page-break-after:auto;break-after:auto}' +
        '.rdc{font-size:22px;font-weight:800;margin-bottom:8px}' +
        '.bon-o{width:100%;border-collapse:collapse}.bon-o td{border:1px solid #000;padding:10px 6px;text-align:center;width:25%;vertical-align:top}' +
        '.bon-o .nh{font-size:17px;letter-spacing:.3px}.bon-o .gt{font-size:30px;font-weight:800;line-height:1.15;margin-top:6px;word-break:break-word}' +
        '.to{font-size:17px;margin:10px 0}' +
        '.duoi{display:flex;align-items:flex-start;gap:24px;position:relative}' +
        '.duoi img{width:160px;height:160px;flex:none}' +
        '.tt{font-size:17px;line-height:1.7}' +
        '.so-kien{position:absolute;right:0;bottom:0;font-size:30px;font-weight:800}');
      PL.thongBao(mot('ok_pl_printed'));
      return lamMoiTatCa(p.id);
    }).catch(PL.baoLoi);
  }

  function huyPhieu(p) {
    PL.hoiXacNhan({
      tieu_de: mot('pack_cancel_title'),
      mo_ta: t('pack_cancel_warn').replace('\n', ' '),
      o_nhap: true, nguy_hiem: true,
    }).then(function (kq) {
      if (!kq) return;
      PL.goi('/api/packing-lists/' + encodeURIComponent(p.id) + '/cancel', {
        method: 'POST', body: { reason: kq.chu },
      }).then(function () {
        PL.thongBao(mot('ok_pl_cancelled'));
        return lamMoiTatCa(p.id);
      }).catch(PL.baoLoi);
    });
  }

  /* --------------------------------------------------------------- chung */
  function moPL(id) {
    return PL.goi('/api/packing-lists/' + encodeURIComponent(id)).then(function (p) {
      plDangChon = p;
      veDanhSach();
      veChiTiet();
    }).catch(PL.baoLoi);
  }

  function moDon(id) {
    if (!id) { donDangChon = null; veKhungDongGoi(); return Promise.resolve(); }
    try { localStorage.setItem('PL_DEMO_SO_DANG_CHON', id); } catch (e) { /* bỏ qua */ }
    return PL.goi('/api/sales-orders/' + encodeURIComponent(id)).then(function (d) {
      donDangChon = d;
      veKhungDongGoi();
    }).catch(PL.baoLoi);
  }

  function lamMoiTatCa(mo_pl) {
    return Promise.all([
      donDangChon ? moDon(donDangChon.id) : Promise.resolve(),
      napDanhSach(),
      PL.goi('/api/packing-lists/stats').then(veSoLieu).catch(function () {}),
    ]).then(function () {
      if (mo_pl) return moPL(mo_pl);
      if (plDangChon) return moPL(plDangChon.id);
      return null;
    });
  }

  function veChonDon() {
    var el = document.getElementById('pk-chon-don');
    if (!el) return;
    el.innerHTML = dsDon.map(function (d) {
      return '<option value="' + an(d.id) + '">' + an(d.id) + ' · PO ' + an(d.po_number) +
        ' · ' + an(d.ship_to_name || '') + '</option>';
    }).join('');
    if (donDangChon) el.value = donDangChon.id;
  }

  function veLocTrangThai() {
    var el = document.getElementById('pk-loc-trang-thai');
    if (!el) return;
    var cu = el.value;
    el.innerHTML = '<option value="">' + an(mot('common_all')) + '</option>' +
      BUOC.concat(['cancelled']).map(function (x) {
        return '<option value="' + x + '">' + an(nhan(x)) + '</option>';
      }).join('');
    el.value = cu;
    var nh = document.getElementById('pk-nhan-chi-don-nay');
    if (nh) nh.textContent = mot('pack_belongs_to');
  }

  function khoiDong() {
    veLocTrangThai();
    document.getElementById('pk-lam-moi').addEventListener('click', napDanhSach);
    document.getElementById('pk-lam-moi-don').addEventListener('click', napDsDon);
    document.getElementById('pk-chon-don').addEventListener('change', function (e) {
      moDon(e.target.value).then(function () {
        if (document.getElementById('pk-chi-don-nay').checked) napDanhSach();
      });
    });
    document.getElementById('pk-chi-don-nay').addEventListener('change', napDanhSach);

    var hen = null;
    document.getElementById('pk-tim').addEventListener('input', function () {
      clearTimeout(hen); hen = setTimeout(napDanhSach, 300);
    });
    document.getElementById('pk-loc-trang-thai').addEventListener('change', napDanhSach);

    napDsTuyen();
    napDsDon().then(function () {
      return Promise.all([
        napDanhSach(),
        PL.goi('/api/packing-lists/stats').then(veSoLieu).catch(function () {}),
      ]);
    });
  }

  function napDsTuyen() {
    return PL.goi('/api/routes?active_only=true').then(function (d) {
      dsTuyen = d || [];
      veKhungDongGoi();
    }).catch(function () {});
  }

  function napDsDon() {
    return PL.goi('/api/sales-orders?page_size=100').then(function (kq) {
      dsDon = ((kq && kq.items) || []).filter(function (d) { return d.status !== 'cancelled'; });
      var luu = null;
      try { luu = localStorage.getItem('PL_DEMO_SO_DANG_CHON'); } catch (e) { /* bỏ qua */ }
      var chon = dsDon.filter(function (d) { return d.id === luu; })[0] || dsDon[0];
      veChonDon();
      if (chon) {
        document.getElementById('pk-chon-don').value = chon.id;
        return moDon(chon.id);
      }
      return null;
    }).catch(PL.baoLoi);
  }

  function veLai() {
    veLocTrangThai();
    veChonDon();
    veKhungDongGoi();
    veDanhSach();
    veChiTiet();
    PL.goi('/api/packing-lists/stats').then(veSoLieu).catch(function () {});
  }

  return { khoiDong: khoiDong, veLai: veLai };
})();

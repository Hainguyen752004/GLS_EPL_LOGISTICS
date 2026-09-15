/* Module Nhận đơn tự động.
 *
 * Máy đọc, người duyệt. Phiếu khách gửi tới (qua hộp thư hoặc tự tải lên) được
 * AI đọc thành BẢN NHÁP; màn này đặt tệp gốc ngay cạnh bản nháp để người duyệt
 * soi từng dòng, sửa lại rồi mới bấm duyệt. Duyệt xong mới có đơn hàng thật, và
 * đơn đó đi vào màn Đóng gói y như đơn gõ tay.
 */

window.NhanDon = (function () {
  'use strict';

  var t = PL.t, an = PL.an;
  var ds = [], dangChon = null, dsKhach = [], ketNoi = {};
  var TRANG_THAI = ['pending', 'parsed', 'failed', 'approved', 'rejected', 'all'];
  var MAU = {
    'new': 'xam', parsed: 'lam', failed: 'do', approved: 'xanh', rejected: 'xam'
  };

  function mot(k, md) { return t(k, md).replace('\n', ' · '); }

  /* -------------------------------------------------------------- kết nối */
  function veKetNoi() {
    var o = document.getElementById('nd-ket-noi');
    if (!o) return;
    var hang = [];
    hang.push('<span class="cham ' + (ketNoi.gmail_ready ? 'bat' : 'tat') + '"></span>' +
      an(mot('nd_mailbox')) + ': ' +
      an(ketNoi.gmail_ready ? (ketNoi.mailbox || mot('nd_connected')) : mot('nd_not_connected')));
    hang.push('<span class="cham ' + (ketNoi.ai_ready ? 'bat' : 'tat') + '"></span>' +
      an(mot('nd_reader')) + ': ' +
      an(ketNoi.ai_ready ? mot('nd_connected') : mot('nd_not_connected')));
    o.innerHTML = hang.join('<br>');

    // Hộp thư chưa dùng được thì nói LÝ DO và chỉ đúng lệnh cần chạy, chứ
    // không để một nút bấm vào là ra lỗi khó hiểu.
    if (!ketNoi.gmail_ready && ketNoi.gmail_reason) {
      o.innerHTML += '<br><span class="nd-ly-do">' +
        an(mot('err_' + ketNoi.gmail_reason, mot('nd_not_connected'))) +
        ' — ' + an(mot('nd_grant_hint')) + '</span>';
    }

    var nut = document.getElementById('nd-quet');
    if (nut) {
      nut.textContent = mot('nd_scan');
      nut.disabled = !ketNoi.gmail_ready;
      nut.title = ketNoi.gmail_ready ? '' : mot('nd_grant_hint');
    }
  }

  function napKetNoi() {
    return PL.goi('/api/inbound/status').then(function (d) {
      ketNoi = d || {};
      veKetNoi();
    }).catch(function () { ketNoi = {}; veKetNoi(); });
  }

  /* ------------------------------------------------------------ danh sách */
  function veDanhSach() {
    var khung = document.getElementById('nd-danh-sach');
    if (!khung) return;
    if (!ds.length) {
      khung.innerHTML = '<div class="trong">' + an(mot('nd_empty')) + '</div>';
      return;
    }
    khung.innerHTML = ds.map(function (x) {
      var phu = [];
      if (x.po_number) phu.push(mot('nd_po') + ' ' + x.po_number);
      if (x.line_count) phu.push(x.line_count + ' ' + mot('nd_lines'));
      if (x.so_id) phu.push(x.so_id);
      return '<div class="ds-muc' + (dangChon && dangChon.id === x.id ? ' dang-chon' : '') +
        '" data-id="' + an(x.id) + '">' +
        '<div style="display:flex;justify-content:space-between;gap:8px;align-items:start">' +
        '<span class="ma">' + an(x.subject || x.file_name || x.id) + '</span>' +
        '<span class="nhan ' + (MAU[x.status] || 'xam') + '">' +
        an(mot('nd_st_' + x.status, x.status)) + '</span></div>' +
        '<div class="phu-de">' + an(x.from_email || '—') + ' · ' + an(PL.gio(x.received_at)) + '</div>' +
        (phu.length ? '<div class="phu-de">' + an(phu.join(' · ')) + '</div>' : '') +
        '</div>';
    }).join('');
    khung.querySelectorAll('.ds-muc').forEach(function (el) {
      el.addEventListener('click', function () { moPhieu(el.dataset.id); });
    });
  }

  function napDanhSach() {
    var loc = (document.getElementById('nd-loc') || {}).value || 'pending';
    var tim = ((document.getElementById('nd-tim') || {}).value || '').trim();
    var dd = '/api/inbound?status=' + encodeURIComponent(loc);
    if (tim) dd += '&q=' + encodeURIComponent(tim);
    return PL.goi(dd).then(function (kq) {
      ds = (kq && kq.items) || [];
      var dem = document.getElementById('nd-dem');
      if (dem && kq) dem.textContent = mot('nd_pending') + ': ' + (kq.counts.pending || 0);
      veDanhSach();
    }).catch(PL.baoLoi);
  }

  function moPhieu(id) {
    return PL.goi('/api/inbound/' + encodeURIComponent(id)).then(function (d) {
      dangChon = d;
      veDanhSach();
      veChiTiet();
    }).catch(PL.baoLoi);
  }

  /* ------------------------------------------------------------- chi tiết */
  function oChon(id, chon, loai, nhan) {
    var lua = dsKhach.filter(function (c) { return c.kind === loai; });
    return '<label class="o"><span>' + an(nhan) + '</span><select id="' + id + '">' +
      '<option value="">' + an(mot('common_choose')) + '</option>' +
      lua.map(function (c) {
        return '<option value="' + an(c.id) + '"' + (c.id === chon ? ' selected' : '') + '>' +
          an(c.name) + ' (' + an(c.code) + ')</option>';
      }).join('') + '</select></label>';
  }

  function veTepGoc(x) {
    if (!x.has_file) return '';
    var dd = '/api/inbound/' + encodeURIComponent(x.id) + '/file';
    var la_anh = (x.file_mime || '').indexOf('image/') === 0;
    var xem = la_anh
      ? '<img src="' + an(dd) + '" alt="' + an(x.file_name || '') + '">'
      : ((x.file_mime || '').indexOf('pdf') >= 0
        ? '<iframe src="' + an(dd) + '" title="' + an(x.file_name || '') + '"></iframe>'
        : '');
    return '<div class="nd-goc">' +
      '<div class="nd-goc-dau"><strong>' + an(x.file_name || mot('nd_file')) + '</strong>' +
      '<a class="nut nho" href="' + an(dd) + '" target="_blank" rel="noopener">' +
      an(mot('nd_open_file')) + '</a></div>' + xem + '</div>';
  }

  function veCanhBao(x) {
    var ra = '';
    if (x.ai_error) {
      ra += '<div class="nd-loi"><strong>' + an(mot('nd_read_failed')) + '</strong><br>' +
        an(x.ai_error) + '</div>';
    }
    var cb = x.ai_warnings || [];
    if (cb.length) {
      ra += '<div class="nd-canh-bao"><h4>' + an(mot('nd_warnings')) + '</h4><ul>' +
        cb.map(function (c) { return '<li>' + an(c) + '</li>'; }).join('') + '</ul></div>';
    }
    return ra;
  }

  function hangDong(d, i) {
    return '<tr>' +
      '<td class="so">' + (i + 1) + '</td>' +
      '<td><input class="c-barcode" value="' + an(d.barcode || '') + '"></td>' +
      '<td><input class="c-ma" value="' + an(d.product_code || '') + '"></td>' +
      '<td><input class="c-mo-ta" value="' + an(d.description || '') + '"></td>' +
      '<td><input class="c-quy-cach so" type="number" min="1" value="' + (d.pack_size || 1) + '"></td>' +
      '<td><input class="c-thung so" type="number" min="0" value="' + (d.case_qty || 0) + '"></td>' +
      '<td><input class="c-cai so" type="number" min="0" value="' + (d.piece_qty || 0) + '"></td>' +
      '<td><input class="c-gia so" type="number" min="0" step="0.01" value="' + (d.unit_price || 0) + '"></td>' +
      '<td><button type="button" class="nut nguy-hiem nho c-bo">×</button></td>' +
      '</tr>';
  }

  function veChiTiet() {
    var khung = document.getElementById('nd-chi-tiet');
    if (!khung) return;
    if (!dangChon) {
      khung.innerHTML = '<div class="the"><div class="trong">' + an(mot('nd_pick_hint')) + '</div></div>';
      return;
    }
    var x = dangChon, n = x.draft || {};
    var mucTinCay = x.ai_confidence >= 80 ? 'cao' : (x.ai_confidence >= 50 ? 'vua' : 'thap');

    if (x.status === 'approved') {
      khung.innerHTML =
        '<div class="the"><div class="the-dau"><h3>' + an(x.subject || x.id) + '</h3>' +
        '<span class="nhan xanh">' + an(mot('nd_st_approved')) + '</span></div>' +
        '<div class="the-than">' +
        '<p>' + an(mot('nd_approved_hint')) + ' <strong>' + an(x.so_id) + '</strong></p>' +
        '<div class="nd-nut-day">' +
        '<button type="button" class="nut chinh" id="nd-xem-don">' + an(mot('nd_open_order')) + '</button>' +
        '</div>' + veTepGoc(x) + '</div></div>';
      var xd = document.getElementById('nd-xem-don');
      if (xd) xd.addEventListener('click', function () { PL.moMan('don-hang'); });
      return;
    }

    khung.innerHTML =
      '<div class="the">' +
        '<div class="the-dau">' +
          '<h3>' + an(x.subject || x.file_name || x.id) + '</h3>' +
          '<span class="nd-tin-cay ' + mucTinCay + '">' +
          an(mot('nd_confidence')) + ': ' + (x.ai_confidence || 0) + '%</span>' +
        '</div>' +
        '<div class="the-than">' +
          veCanhBao(x) +
          veTepGoc(x) +
          '<div class="hang-o">' +
            '<label class="o"><span>' + an(mot('nd_po')) + '</span>' +
              '<input type="text" id="nd-po" value="' + an(n.po_number || '') + '"></label>' +
            '<label class="o"><span>' + an(mot('nd_order_date')) + '</span>' +
              '<input type="date" id="nd-ngay-dat" value="' + an(n.order_date || '') + '"></label>' +
            '<label class="o"><span>' + an(mot('nd_ship_date')) + '</span>' +
              '<input type="date" id="nd-ngay-giao" value="' + an(n.shipping_date || '') + '"></label>' +
            '<label class="o"><span>' + an(mot('nd_currency')) + '</span>' +
              '<select id="nd-tien-te">' +
              ['LAK', 'THB', 'USD', 'VND'].map(function (m) {
                return '<option value="' + m + '"' + (m === (n.currency || 'LAK') ? ' selected' : '') +
                  '>' + m + '</option>';
              }).join('') + '</select></label>' +
          '</div>' +
          '<div class="hang-o">' +
            oChon('nd-khach', n.customer_id || n.ship_to_suggest_id, 'customer', mot('nd_customer')) +
            oChon('nd-vendor', n.vendor_id || n.vendor_suggest_id, 'vendor', mot('nd_vendor')) +
            '<label class="o"><span>' + an(mot('nd_tax')) + '</span>' +
              '<input type="text" id="nd-mst" value="' + an(n.tax_number || '') + '"></label>' +
          '</div>' +
          '<p class="gioi-thieu">' + an(mot('nd_read_on_paper')) + ': ' +
          an([n.ship_to_code, n.ship_to_name, n.ship_to_address].filter(Boolean).join(' · ') || '—') +
          '</p>' +
          '<div class="nd-cuon"><table class="nd-bang-nhap" id="nd-bang">' +
            '<thead><tr>' +
              '<th>#</th><th>' + an(mot('nd_barcode')) + '</th><th>' + an(mot('nd_code')) + '</th>' +
              '<th>' + an(mot('nd_desc')) + '</th><th>' + an(mot('nd_pack')) + '</th>' +
              '<th>' + an(mot('nd_case')) + '</th><th>' + an(mot('nd_piece')) + '</th>' +
              '<th>' + an(mot('nd_price')) + '</th><th></th>' +
            '</tr></thead><tbody>' +
            (n.lines || []).map(hangDong).join('') +
            '</tbody></table></div>' +
          '<div class="nd-nut-day">' +
            '<button type="button" class="nut nho trai" id="nd-them-dong">' +
              an(mot('nd_add_line')) + '</button>' +
            '<button type="button" class="nut nho" id="nd-doc-lai">' + an(mot('nd_reparse')) + '</button>' +
            '<button type="button" class="nut nho" id="nd-luu">' + an(mot('nd_save_draft')) + '</button>' +
            '<button type="button" class="nut nguy-hiem nho" id="nd-bo">' + an(mot('nd_reject')) + '</button>' +
            '<button type="button" class="nut chinh" id="nd-duyet">' + an(mot('nd_approve')) + '</button>' +
          '</div>' +
        '</div>' +
      '</div>';

    gan();
  }

  function gan() {
    var bang = document.getElementById('nd-bang');
    if (bang) {
      bang.addEventListener('click', function (e) {
        var nut = e.target.closest('.c-bo');
        if (nut) nut.closest('tr').remove();
      });
    }
    var them = document.getElementById('nd-them-dong');
    if (them) {
      them.addEventListener('click', function () {
        var tbody = document.querySelector('#nd-bang tbody');
        var so = tbody.querySelectorAll('tr').length;
        tbody.insertAdjacentHTML('beforeend', hangDong({ pack_size: 1 }, so));
      });
    }
    var m = {
      'nd-doc-lai': docLai, 'nd-luu': luuNhap, 'nd-duyet': duyet, 'nd-bo': bo
    };
    Object.keys(m).forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.addEventListener('click', m[id]);
    });
  }

  /* --------------------------------------------------------------- thao tác */
  function gomNhap() {
    var dong = [];
    document.querySelectorAll('#nd-bang tbody tr').forEach(function (tr, i) {
      var mo_ta = tr.querySelector('.c-mo-ta').value.trim();
      var thung = Number(tr.querySelector('.c-thung').value || 0);
      var cai = Number(tr.querySelector('.c-cai').value || 0);
      if (!mo_ta && !thung && !cai) return;
      var gia = Number(tr.querySelector('.c-gia').value || 0);
      dong.push({
        line_no: i + 1,
        barcode: tr.querySelector('.c-barcode').value.trim(),
        product_code: tr.querySelector('.c-ma').value.trim(),
        description: mo_ta,
        pack_size: Number(tr.querySelector('.c-quy-cach').value || 1),
        case_qty: thung,
        piece_qty: cai,
        unit_price: gia,
        amount: gia * thung
      });
    });
    return {
      po_number: document.getElementById('nd-po').value.trim(),
      order_date: document.getElementById('nd-ngay-dat').value || null,
      shipping_date: document.getElementById('nd-ngay-giao').value || null,
      currency: document.getElementById('nd-tien-te').value,
      customer_id: document.getElementById('nd-khach').value || null,
      vendor_id: document.getElementById('nd-vendor').value || null,
      tax_number: document.getElementById('nd-mst').value.trim(),
      lines: dong
    };
  }

  function luuNhap() {
    if (!dangChon) return;
    PL.goi('/api/inbound/' + encodeURIComponent(dangChon.id) + '/draft', {
      method: 'PUT', body: gomNhap()
    }).then(function (d) {
      dangChon = d;
      PL.thongBao(mot('ok_draft_saved'));
      return napDanhSach();
    }).catch(PL.baoLoi);
  }

  function docLai() {
    if (!dangChon) return;
    PL.thongBao(mot('nd_reading'));
    PL.goi('/api/inbound/' + encodeURIComponent(dangChon.id) + '/parse', { method: 'POST' })
      .then(function (d) {
        dangChon = d;
        veChiTiet();
        return napDanhSach();
      }).catch(PL.baoLoi);
  }

  function duyet() {
    if (!dangChon) return;
    var nhap = gomNhap();
    if (!nhap.customer_id) { PL.baoLoi({ ma: 'IB_NO_CUSTOMER' }); return; }
    PL.hoiXacNhan(mot('nd_confirm_approve')).then(function (dong_y) {
      if (!dong_y) return;
      PL.goi('/api/inbound/' + encodeURIComponent(dangChon.id) + '/approve', {
        method: 'POST', body: nhap
      }).then(function (d) {
        PL.thongBao(mot('ok_inbound_approved') + ' ' + (d.order ? d.order.id : ''));
        dangChon = d.inbound;
        veChiTiet();
        return napDanhSach();
      }).catch(PL.baoLoi);
    });
  }

  function bo() {
    if (!dangChon) return;
    PL.hoiXacNhan(mot('nd_confirm_reject')).then(function (dong_y) {
      if (!dong_y) return;
      PL.goi('/api/inbound/' + encodeURIComponent(dangChon.id) + '/reject', {
        method: 'POST', body: {}
      }).then(function () {
        dangChon = null;
        veChiTiet();
        return napDanhSach();
      }).catch(PL.baoLoi);
    });
  }

  function quet() {
    PL.thongBao(mot('nd_scanning'));
    PL.goi('/api/inbound/scan', { method: 'POST', body: { limit: 10 } })
      .then(function (kq) {
        PL.thongBao(mot('nd_scan_done')
          .replace('{new}', kq.new || 0)
          .replace('{skipped}', kq.skipped || 0));
        return napDanhSach();
      }).catch(PL.baoLoi);
  }

  function taiLen(tep) {
    if (!tep) return;
    var fd = new FormData();
    fd.append('file', tep);
    PL.thongBao(mot('nd_reading'));
    // Không dùng PL.goi ở đây: nó ép Content-Type là JSON, mà tệp phải đi bằng
    // multipart để trình duyệt tự đặt ranh giới (boundary).
    fetch('/api/inbound/upload', { method: 'POST', body: fd })
      .then(function (r) { return r.text().then(function (c) { return { ok: r.ok, chu: c }; }); })
      .then(function (kq) {
        var d = null;
        try { d = kq.chu ? JSON.parse(kq.chu) : null; } catch (e) { d = null; }
        if (!kq.ok) {
          var ma = (d && d.detail && d.detail.code) || 'UNKNOWN';
          throw Object.assign(new Error(ma), { ma: ma });
        }
        return napDanhSach().then(function () { return moPhieu(d.data.id); });
      }).catch(PL.baoLoi);
  }

  /* ------------------------------------------------------------------ vào */
  function veOLoc() {
    var o = document.getElementById('nd-loc');
    if (!o) return;
    var cu = o.value || 'pending';
    o.innerHTML = TRANG_THAI.map(function (m) {
      return '<option value="' + m + '"' + (m === cu ? ' selected' : '') + '>' +
        an(mot('nd_filter_' + m, m)) + '</option>';
    }).join('');
  }

  function khoiDong() {
    ds = []; dangChon = null;
    veOLoc();

    var loc = document.getElementById('nd-loc');
    if (loc) loc.addEventListener('change', napDanhSach);
    var tim = document.getElementById('nd-tim');
    if (tim) {
      var cho = null;
      tim.addEventListener('input', function () {
        clearTimeout(cho);
        cho = setTimeout(napDanhSach, 300);
      });
    }
    var lm = document.getElementById('nd-lam-moi');
    if (lm) lm.addEventListener('click', function () { napKetNoi(); napDanhSach(); });
    var nq = document.getElementById('nd-quet');
    if (nq) nq.addEventListener('click', quet);
    var ot = document.getElementById('nd-tep');
    if (ot) {
      ot.addEventListener('change', function () {
        taiLen(ot.files && ot.files[0]);
        ot.value = '';
      });
    }

    return PL.goi('/api/customers').then(function (d) {
      dsKhach = d || [];
    }).catch(function () { dsKhach = []; }).then(function () {
      return Promise.all([napKetNoi(), napDanhSach()]);
    });
  }

  return { khoiDong: khoiDong };
})();

/* Khung chung của bản demo Packing List.
 *
 * Giữ bốn việc: bốn ngôn ngữ, chuyển màn, gọi API, và hộp thoại trong ứng dụng.
 * Mỗi module có bộ html + css + js riêng nên sửa màn nào chỉ động vào màn đó.
 */

window.PL = (function () {
  'use strict';

  var API = '';                 // cùng gốc với trang, không cần cấu hình

  // MỘT mã phiên bản cho MỌI tệp tĩnh. Sửa bất cứ module nào cũng đổi số này.
  //
  // Lỗi đã xảy ra thật: HTML của màn Tuyến đường đã là bản mới (có bảng chặng)
  // mà JS thì trình duyệt vẫn dùng bản cũ trong bộ nhớ đệm — bản cũ đi tìm một
  // phần tử không còn tồn tại nên không đổ được dữ liệu, và màn hiện ra trống
  // trơn dù máy chủ trả đủ. Gom vào một chỗ để không bao giờ lệch nữa.
  var PHIEN_BAN = '20260915b';
  var KHOA_NGON_NGU = 'PL_DEMO_NGON_NGU';
  var tuDien = {};
  var ngonNgu = 'vi';
  var moduleDangMo = null;

  // Bốn chế độ. 'both' là Việt trên, Lào dưới — người Lào đọc được mà người Việt
  // vẫn đối chiếu được, đúng thứ chủ dự án yêu cầu cho lúc bàn giao.
  var CHE_DO = ['vi', 'en', 'lo', 'both'];

  /* ---------------------------------------------------------------- ngôn ngữ */
  function t(khoa, macDinh) {
    var muc = tuDien[khoa];
    if (!muc) return macDinh !== undefined ? macDinh : khoa;
    if (ngonNgu === 'both') {
      var v = muc.vi || '';
      var l = muc.lo || '';
      if (!l || l === v) return v;
      return v + '\n' + l;
    }
    return muc[ngonNgu] || muc.vi || (macDinh !== undefined ? macDinh : khoa);
  }

  function laHaiDong() {
    return ngonNgu === 'both';
  }

  function apDungNgonNgu(goc) {
    var pham = goc || document;
    pham.querySelectorAll('[data-i18n]').forEach(function (el) {
      var chu = t(el.getAttribute('data-i18n'));
      if (laHaiDong() && chu.indexOf('\n') >= 0) {
        var phan = chu.split('\n');
        el.innerHTML = '<span class="d-vi"></span><span class="d-lo"></span>';
        el.firstChild.textContent = phan[0];
        el.lastChild.textContent = phan[1];
      } else {
        el.textContent = chu;
      }
    });
    pham.querySelectorAll('[data-i18n-ph]').forEach(function (el) {
      // Ô nhập không xuống dòng được, nên chế độ hai thứ tiếng ghép bằng dấu ·
      el.setAttribute('placeholder', t(el.getAttribute('data-i18n-ph')).replace('\n', ' · '));
    });
    pham.querySelectorAll('[data-i18n-title]').forEach(function (el) {
      el.setAttribute('title', t(el.getAttribute('data-i18n-title')).replace('\n', ' · '));
    });
  }

  function datNgonNgu(ma) {
    if (CHE_DO.indexOf(ma) < 0) return;
    ngonNgu = ma;
    try { localStorage.setItem(KHOA_NGON_NGU, ma); } catch (e) { /* bị chặn thì thôi */ }
    document.documentElement.lang = ma === 'lo' || ma === 'both' ? 'lo' : ma;
    document.body.classList.toggle('che-do-hai-dong', ma === 'both');
    document.querySelectorAll('.nut-ngon-ngu').forEach(function (nut) {
      nut.classList.toggle('dang-chon', nut.dataset.lang === ma);
    });
    apDungNgonNgu();
    // Màn đang mở tự vẽ lại để chữ do JS sinh ra cũng đổi theo.
    if (moduleDangMo && typeof moduleDangMo.veLai === 'function') moduleDangMo.veLai();
  }

  /* ------------------------------------------------------------------- API */
  function maLoiTuPhanHoi(du_lieu) {
    if (!du_lieu) return 'UNKNOWN';
    var ct = du_lieu.detail;
    if (ct && typeof ct === 'object' && ct.code) return ct.code;
    if (typeof ct === 'string') return ct;
    return 'UNKNOWN';
  }

  function goi(duong_dan, tuy_chon) {
    var cau_hinh = Object.assign({ headers: {} }, tuy_chon || {});
    cau_hinh.headers['Content-Type'] = 'application/json';
    if (cau_hinh.body && typeof cau_hinh.body !== 'string') {
      cau_hinh.body = JSON.stringify(cau_hinh.body);
    }
    return fetch(API + duong_dan, cau_hinh).then(function (phan_hoi) {
      return phan_hoi.text().then(function (chu) {
        var du_lieu = null;
        try { du_lieu = chu ? JSON.parse(chu) : null; } catch (e) { du_lieu = null; }
        if (!phan_hoi.ok) {
          var ma = maLoiTuPhanHoi(du_lieu);
          var loi = new Error(ma);
          loi.ma = ma;
          loi.chi_tiet = du_lieu && du_lieu.detail && du_lieu.detail.detail;
          throw loi;
        }
        return du_lieu ? du_lieu.data : null;
      });
    }, function () {
      var loi = new Error('NETWORK');
      loi.ma = 'NETWORK';
      throw loi;
    });
  }

  function chuLoi(loi) {
    var ma = (loi && loi.ma) || 'UNKNOWN';
    var khoa = 'err_' + ma;
    var chu = t(khoa, null);
    return chu === null || chu === khoa ? t('err_UNKNOWN') : chu;
  }

  /* --------------------------------------------------------------- thông báo */
  function thongBao(chu, loai) {
    var hop = document.getElementById('pl-toast');
    if (!hop) return;
    hop.className = 'pl-toast hien ' + (loai || 'ok');
    hop.textContent = chu;
    clearTimeout(hop._hen);
    hop._hen = setTimeout(function () { hop.className = 'pl-toast'; }, 4200);
  }

  function baoLoi(loi) {
    var chu = chuLoi(loi);
    // Đóng vượt số đặt là lỗi hay gặp nhất khi đóng gói, nên nói rõ dòng nào.
    if (loi && loi.ma === 'PL_OVER_ORDERED' && loi.chi_tiet && loi.chi_tiet.lines) {
      var ds = loi.chi_tiet.lines.map(function (d) {
        return '#' + d.line_no + ' ' + (d.description || '') +
          ' (' + t('so_remaining').split('\n')[0] + ': ' +
          Math.max(d.ordered_case - d.packed_case, 0) + ')';
      });
      chu += ' — ' + ds.join('; ');
    }
    thongBao(chu, 'loi');
  }

  /* ------------------------------------------------- hộp thoại trong ứng dụng
   * KHÔNG dùng confirm()/alert() của trình duyệt: hộp "127.0.0.1 says" đọc như
   * lỗi kỹ thuật khi chiếu cho khách. */
  function hoiXacNhan(tuy_chon) {
    return new Promise(function (tra_loi) {
      var nen = document.getElementById('pl-hop-thoai');
      nen.innerHTML =
        '<div class="hop">' +
        '<h3></h3>' +
        '<p class="mo-ta"></p>' +
        (tuy_chon.o_nhap
          ? '<label class="o-ly-do"><span></span><input type="text" id="pl-ly-do"></label>'
          : '') +
        '<div class="nut-day">' +
        '<button class="nut phu" id="pl-huy-bo"></button>' +
        '<button class="nut ' + (tuy_chon.nguy_hiem ? 'nguy-hiem' : 'chinh') + '" id="pl-dong-y"></button>' +
        '</div></div>';
      nen.querySelector('h3').textContent = tuy_chon.tieu_de || t('common_confirm');
      nen.querySelector('.mo-ta').textContent = tuy_chon.mo_ta || '';
      if (tuy_chon.o_nhap) nen.querySelector('.o-ly-do span').textContent = tuy_chon.nhan_o_nhap || t('common_reason');
      nen.querySelector('#pl-huy-bo').textContent = tuy_chon.chu_huy || t('common_cancel');
      nen.querySelector('#pl-dong-y').textContent = tuy_chon.chu_dong_y || t('common_confirm');
      nen.classList.add('hien');

      function dong(ket_qua) {
        nen.classList.remove('hien');
        nen.innerHTML = '';
        tra_loi(ket_qua);
      }
      nen.querySelector('#pl-huy-bo').onclick = function () { dong(null); };
      nen.querySelector('#pl-dong-y').onclick = function () {
        var o = nen.querySelector('#pl-ly-do');
        dong({ ok: true, chu: o ? o.value.trim() : '' });
      };
      nen.onclick = function (su_kien) { if (su_kien.target === nen) dong(null); };
    });
  }

  /* -------------------------------------------------------------- định dạng */
  function so(x, le) {
    var n = Number(x || 0);
    if (!isFinite(n)) return '0';
    return n.toLocaleString('en-US', {
      minimumFractionDigits: le || 0,
      maximumFractionDigits: le === undefined ? 2 : le,
    });
  }

  function tien(x, ma_tien) {
    return so(x, 0) + ' ' + (ma_tien || 'LAK');
  }

  function gio(chuoi) {
    if (!chuoi) return '—';
    var d = new Date(chuoi.length <= 19 && chuoi.indexOf('Z') < 0 ? chuoi + 'Z' : chuoi);
    if (isNaN(d.getTime())) return String(chuoi);
    var vung = { vi: 'vi-VN', en: 'en-GB', lo: 'lo-LA', both: 'lo-LA' }[ngonNgu] || 'vi-VN';
    return d.toLocaleString(vung, { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  function an(chuoi) {
    return String(chuoi === null || chuoi === undefined ? '' : chuoi)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  /** Chữ cho một ô do JS sinh: chế độ hai thứ tiếng thì xuống dòng. */
  function oChu(khoa) {
    var chu = t(khoa);
    if (chu.indexOf('\n') < 0) return an(chu);
    var p = chu.split('\n');
    return '<span class="d-vi">' + an(p[0]) + '</span><span class="d-lo">' + an(p[1]) + '</span>';
  }

  /* ------------------------------------------------------------- chuyển màn */
  var MODULE = {
    'don-hang': { js: 'DonHang' },
    'packing-list': { js: 'PackingList' },
    'giao-hang': { js: 'GiaoHang' },
    'quet-tem': { js: 'QuetTem' },
    'khach-hang': { js: 'KhachHang' },
    'theo-doi': { js: 'TheoDoi' },
    'tuyen-duong': { js: 'TuyenDuong' },
  };

  function napTaiNguyen(ten) {
    var cho = [];
    if (!document.querySelector('link[data-mod="' + ten + '"]')) {
      cho.push(new Promise(function (xong) {
        var link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = '/static/modules/' + ten + '/' + ten + '.css?v=' + PHIEN_BAN;
        link.dataset.mod = ten;
        link.onload = link.onerror = xong;
        document.head.appendChild(link);
      }));
    }
    if (!document.querySelector('script[data-mod="' + ten + '"]')) {
      cho.push(new Promise(function (xong, hong) {
        var s = document.createElement('script');
        s.src = '/static/modules/' + ten + '/' + ten + '.js?v=' + PHIEN_BAN;
        s.dataset.mod = ten;
        s.onload = xong;
        s.onerror = function () { hong(new Error('Không nạp được ' + ten + '.js')); };
        document.head.appendChild(s);
      }));
    }
    return Promise.all(cho);
  }

  function moMan(ten) {
    if (!MODULE[ten]) ten = 'don-hang';
    var khung = document.getElementById('pl-noi-dung');
    khung.innerHTML = '<div class="dang-tai" data-i18n="common_loading"></div>';
    apDungNgonNgu(khung);

    document.querySelectorAll('.nut-nav').forEach(function (n) {
      n.classList.toggle('dang-chon', n.dataset.man === ten);
    });
    try { localStorage.setItem('PL_DEMO_MAN', ten); } catch (e) { /* bỏ qua */ }

    return fetch('/static/modules/' + ten + '/' + ten + '.html?v=' + PHIEN_BAN)
      .then(function (r) { return r.text(); })
      .then(function (html) {
        khung.innerHTML = html;
        return napTaiNguyen(ten);
      })
      .then(function () {
        apDungNgonNgu(khung);
        var mod = window[MODULE[ten].js];
        moduleDangMo = mod || null;
        if (mod && typeof mod.khoiDong === 'function') mod.khoiDong();
      })
      .catch(function (loi) {
        khung.innerHTML = '<div class="dang-tai">' + an(loi.message || 'Lỗi') + '</div>';
      });
  }

  /* ---------------------------------------------------------------- khởi động */
  function batDau() {
    fetch('/static/lang.json?v=' + PHIEN_BAN)
      .then(function (r) { return r.json(); })
      .then(function (d) { tuDien = d; })
      .catch(function () { tuDien = {}; })
      .then(function () {
        var luu = 'vi';
        try { luu = localStorage.getItem(KHOA_NGON_NGU) || 'vi'; } catch (e) { /* bỏ qua */ }
        datNgonNgu(CHE_DO.indexOf(luu) >= 0 ? luu : 'vi');

        document.querySelectorAll('.nut-ngon-ngu').forEach(function (nut) {
          nut.addEventListener('click', function () { datNgonNgu(nut.dataset.lang); });
        });
        document.querySelectorAll('.nut-nav').forEach(function (nut) {
          nut.addEventListener('click', function () { moMan(nut.dataset.man); });
        });

        var man = 'don-hang';
        try { man = localStorage.getItem('PL_DEMO_MAN') || 'don-hang'; } catch (e) { /* bỏ qua */ }
        moMan(man);
      });
  }

  document.addEventListener('DOMContentLoaded', batDau);

  return {
    t: t, oChu: oChu, an: an, so: so, tien: tien, gio: gio,
    goi: goi, baoLoi: baoLoi, thongBao: thongBao, hoiXacNhan: hoiXacNhan,
    apDungNgonNgu: apDungNgonNgu, moMan: moMan, laHaiDong: laHaiDong,
    ngonNgu: function () { return ngonNgu; },
  };
})();

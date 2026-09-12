/* eslint-env browser */
/**
 * EPL Trợ lý — trang chat.
 *
 * Trình duyệt chỉ giữ lịch sử trò chuyện (localStorage) và gửi câu hỏi lên `POST /hoi`.
 * Khóa Gemini, token EPL, và toàn bộ việc gọi công cụ nằm ở máy chủ `chay.py`.
 *
 * STREAM: `/hoi` trả text/event-stream. Trang vẽ từng công cụ đang tra ngay khi mô hình gọi
 * (chip "Đã xem"), rồi chữ trả lời chảy ra dần. Không có ba dấu chấm 6 giây nữa.
 *
 * TRÍ NHỚ: mỗi câu trả lời kèm `ngu_canh` — dữ liệu đã tra, đã rút gọn. Lượt sau gửi lại nó
 * cùng lời hỏi-đáp, nên hỏi tiếp "cái đó bao nhiêu" là mô hình có sẵn số.
 *
 * THÔNG BÁO: hỏi `/thong-bao` mỗi 10 giây; báo giá mới, DO mới, xe xuất phát, xe hoàn tất →
 * chuông + toast, và Notification của trình duyệt nếu anh cho phép.
 *
 * Ba ngôn ngữ: nhãn giao diện đổi ngay; câu trả lời của mô hình đi theo `ngon_ngu` gửi kèm.
 */
(function () {
  'use strict';

  var LUU = 'EPL_TROLY_V1';
  var LUU_NGON_NGU = 'EPL_TROLY_NGON_NGU';
  var LUU_GIAO_DIEN = 'EPL_TROLY_GIAO_DIEN';
  var LUU_THONG_BAO = 'EPL_TROLY_THONG_BAO';
  var CHU_KY_THONG_BAO = 10000;

  // ------------------------------------------------------------------ chữ giao diện
  var CHU = {
    vi: {
      tro_ly: 'Trợ lý', phu_ten: 'Quản lý vận tải', tro_chuyen_moi: 'Trò chuyện mới', gan_day: 'Gần đây',
      giao_dien: 'Giao diện', phu_chao: 'Hỏi em bất cứ gì về vận hành hôm nay — lệnh giao hàng, chuyến đang chạy, sự cố, báo giá, đội xe.',
      goi_y_nhap: 'Hỏi em điều gì về vận hành…',
      chu_thich: 'Trợ lý chỉ đọc dữ liệu thật từ hệ thống EPL và có thể nhầm — hãy kiểm lại con số quan trọng trên màn hình gốc.',
      chao_sang: 'Chào buổi sáng', chao_chieu: 'Chào buổi chiều', chao_toi: 'Chào buổi tối',
      dang_nghi: 'Đang suy nghĩ…', dang_tra: 'Đang tra', da_xem: 'Đã xem', sao_chep: 'Sao chép', da_sao_chep: 'Đã sao chép',
      thu_lai: 'Thử lại', xoa: 'Xoá', chua_co: 'Chưa có cuộc trò chuyện nào.', loi_mang: 'Không gọi được máy chủ trợ lý.',
      epl_tat: 'Không nối được hệ thống EPL', thieu_khoa: 'Thiếu khóa Gemini', cuoc_moi: 'Cuộc trò chuyện mới',
      thong_bao: 'Thông báo', doc_het: 'Đánh dấu đã đọc', bao_ngoai: 'Báo cả khi đang ở tab khác',
      chua_thong_bao: 'Chưa có gì mới. Em đang canh: báo giá mới, lệnh mới, xe xuất phát, xe hoàn tất.',
      hoi_them: 'Hỏi em về việc này', giam_sat_luc: 'Kiểm lần cuối', gia: 'giá',
      tb: {
        bao_gia_moi: 'Báo giá mới {ma} cho {khach}{gia}',
        do_moi: 'Lệnh giao hàng mới {ma} cho {khach}',
        xe_xuat_phat: 'Xe {xe} đã xuất phát — chuyến {ma}{khach}',
        xe_hoan_tat: 'Xe {xe} đã báo hoàn tất chuyến {ma}{khach}',
        do_giao_xong: 'Lệnh {ma} đã giao xong cho {khach}'
      },
      hoi_tb: {
        bao_gia_moi: 'Cho em xem chi tiết báo giá {ma}',
        do_moi: 'Lệnh giao hàng {ma} có gì, khách nào, hạn giao khi nào?',
        xe_xuat_phat: 'Chuyến {ma} của xe {xe} đang chở gì và bao giờ tới?',
        xe_hoan_tat: 'Chuyến {ma} của xe {xe} hoàn tất chưa, có hồ sơ hoàn tất chưa?',
        do_giao_xong: 'Lệnh {ma} đã giao xong — giá cuối và lợi nhuận là bao nhiêu?'
      },
      goi_y: [
        'Hôm nay có gì cần lo không?',
        'Có sự cố nào đang mở không?',
        'Bao nhiêu lệnh giao hàng đang chạy, cái nào sắp trễ?',
        'Báo giá nào sắp hết hạn trong 7 ngày?',
        'Xe và tài xế nào đang rảnh?',
        'Giấy tờ xe hay bằng lái nào sắp hết hạn?'
      ]
    },
    en: {
      tro_ly: 'Assistant', phu_ten: 'Transport management', tro_chuyen_moi: 'New chat', gan_day: 'Recent',
      giao_dien: 'Appearance', phu_chao: 'Ask anything about today’s operations — delivery orders, running trips, incidents, quotations, the fleet.',
      goi_y_nhap: 'Ask about operations…',
      chu_thich: 'The assistant reads live data from the EPL system and can still be wrong — verify important figures on the original screen.',
      chao_sang: 'Good morning', chao_chieu: 'Good afternoon', chao_toi: 'Good evening',
      dang_nghi: 'Thinking…', dang_tra: 'Checking', da_xem: 'Checked', sao_chep: 'Copy', da_sao_chep: 'Copied',
      thu_lai: 'Retry', xoa: 'Delete', chua_co: 'No conversations yet.', loi_mang: 'Could not reach the assistant server.',
      epl_tat: 'EPL system unreachable', thieu_khoa: 'Gemini key missing', cuoc_moi: 'New chat',
      thong_bao: 'Notifications', doc_het: 'Mark all read', bao_ngoai: 'Notify me in other tabs too',
      chua_thong_bao: 'Nothing new yet. Watching for: new quotations, new orders, departures, completions.',
      hoi_them: 'Ask about this', giam_sat_luc: 'Last check', gia: 'price',
      tb: {
        bao_gia_moi: 'New quotation {ma} for {khach}{gia}',
        do_moi: 'New delivery order {ma} for {khach}',
        xe_xuat_phat: 'Vehicle {xe} departed — trip {ma}{khach}',
        xe_hoan_tat: 'Vehicle {xe} reported trip {ma} complete{khach}',
        do_giao_xong: 'Order {ma} delivered to {khach}'
      },
      hoi_tb: {
        bao_gia_moi: 'Show me quotation {ma} in detail',
        do_moi: 'What is in delivery order {ma}, which customer, what deadline?',
        xe_xuat_phat: 'What is trip {ma} of vehicle {xe} carrying and when does it arrive?',
        xe_hoan_tat: 'Is trip {ma} of vehicle {xe} closed, is there a completion record?',
        do_giao_xong: 'Order {ma} is delivered — final price and profit?'
      },
      goi_y: [
        'Anything I should worry about today?',
        'Any open incidents?',
        'How many orders are in transit, which are about to be late?',
        'Which quotations expire within 7 days?',
        'Which vehicles and drivers are free?',
        'Any vehicle papers or licences expiring soon?'
      ]
    },
    lo: {
      tro_ly: 'ຜູ້ຊ່ວຍ', phu_ten: 'ຄຸ້ມຄອງການຂົນສົ່ງ', tro_chuyen_moi: 'ສົນທະນາໃໝ່', gan_day: 'ຫຼ້າສຸດ',
      giao_dien: 'ຮູບແບບ', phu_chao: 'ຖາມຫຍັງກໍໄດ້ກ່ຽວກັບການດຳເນີນງານມື້ນີ້ — ໃບສັ່ງປ່ອຍສິນຄ້າ, ຖ້ຽວທີ່ກຳລັງແລ່ນ, ເຫດການ, ໃບສະເໜີລາຄາ, ກອງລົດ.',
      goi_y_nhap: 'ຖາມກ່ຽວກັບການດຳເນີນງານ…',
      chu_thich: 'ຜູ້ຊ່ວຍອ່ານຂໍ້ມູນຈິງຈາກລະບົບ EPL ແລະ ອາດຜິດພາດໄດ້ — ກະລຸນາກວດຕົວເລກສຳຄັນຢູ່ໜ້າຈໍຕົ້ນສະບັບ.',
      chao_sang: 'ສະບາຍດີຕອນເຊົ້າ', chao_chieu: 'ສະບາຍດີຕອນບ່າຍ', chao_toi: 'ສະບາຍດີຕອນແລງ',
      dang_nghi: 'ກຳລັງຄິດ…', dang_tra: 'ກຳລັງກວດ', da_xem: 'ໄດ້ເບິ່ງ', sao_chep: 'ສຳເນົາ', da_sao_chep: 'ສຳເນົາແລ້ວ',
      thu_lai: 'ລອງໃໝ່', xoa: 'ລຶບ', chua_co: 'ຍັງບໍ່ມີການສົນທະນາ.', loi_mang: 'ຕິດຕໍ່ເຊີບເວີຜູ້ຊ່ວຍບໍ່ໄດ້.',
      epl_tat: 'ເຊື່ອມຕໍ່ລະບົບ EPL ບໍ່ໄດ້', thieu_khoa: 'ຂາດກະແຈ Gemini', cuoc_moi: 'ສົນທະນາໃໝ່',
      thong_bao: 'ການແຈ້ງເຕືອນ', doc_het: 'ໝາຍວ່າອ່ານແລ້ວທັງໝົດ', bao_ngoai: 'ແຈ້ງແມ່ນຢູ່ແທັບອື່ນ',
      chua_thong_bao: 'ຍັງບໍ່ມີຫຍັງໃໝ່. ກຳລັງເຝົ້າ: ໃບສະເໜີລາຄາໃໝ່, DO ໃໝ່, ລົດອອກເດີນທາງ, ລົດສຳເລັດ.',
      hoi_them: 'ຖາມກ່ຽວກັບເລື່ອງນີ້', giam_sat_luc: 'ກວດຄັ້ງຫຼ້າສຸດ', gia: 'ລາຄາ',
      tb: {
        bao_gia_moi: 'ໃບສະເໜີລາຄາໃໝ່ {ma} ສຳລັບ {khach}{gia}',
        do_moi: 'DO ໃໝ່ {ma} ສຳລັບ {khach}',
        xe_xuat_phat: 'ລົດ {xe} ອອກເດີນທາງແລ້ວ — ຖ້ຽວ {ma}{khach}',
        xe_hoan_tat: 'ລົດ {xe} ລາຍງານສຳເລັດຖ້ຽວ {ma}{khach}',
        do_giao_xong: 'DO {ma} ສົ່ງສຳເລັດໃຫ້ {khach}'
      },
      hoi_tb: {
        bao_gia_moi: 'ຂໍເບິ່ງລາຍລະອຽດໃບສະເໜີລາຄາ {ma}',
        do_moi: 'DO {ma} ມີຫຍັງ, ລູກຄ້າໃດ, ກຳນົດສົ່ງເມື່ອໃດ?',
        xe_xuat_phat: 'ຖ້ຽວ {ma} ຂອງລົດ {xe} ບັນທຸກຫຍັງ ແລະ ຈະຮອດເມື່ອໃດ?',
        xe_hoan_tat: 'ຖ້ຽວ {ma} ຂອງລົດ {xe} ປິດແລ້ວບໍ, ມີບັນທຶກສຳເລັດແລ້ວບໍ?',
        do_giao_xong: 'DO {ma} ສົ່ງສຳເລັດແລ້ວ — ລາຄາສຸດທ້າຍ ແລະ ກຳໄລເທົ່າໃດ?'
      },
      goi_y: [
        'ມື້ນີ້ມີຫຍັງຕ້ອງກັງວົນບໍ?',
        'ມີເຫດການໃດຍັງເປີດຢູ່ບໍ?',
        'ມີ DO ຈັກໃບກຳລັງຂົນສົ່ງ, ໃບໃດໃກ້ຊ້າ?',
        'ໃບສະເໜີລາຄາໃດຈະໝົດອາຍຸໃນ 7 ມື້?',
        'ລົດ ແລະ ຄົນຂັບຄັນໃດຫວ່າງ?',
        'ເອກະສານລົດ ຫຼື ໃບຂັບຂີ່ໃດໃກ້ໝົດອາຍຸ?'
      ]
    }
  };
  var BIEU_TUONG_TB = { bao_gia_moi: '🧾', do_moi: '📦', xe_xuat_phat: '🚚', xe_hoan_tat: '✅', do_giao_xong: '✅' };

  // ------------------------------------------------------------------ trạng thái
  var tt = { ngonNgu: 'vi', cuoc: [], hienTai: null, dangGui: false,
             thongBao: [], daDocToi: 0, moiNhat: 0, choPhepNgoai: false };
  var el = function (id) { return document.getElementById(id); };
  var $ung = el('ung-dung'), $ds = el('ds-cuoc'), $tin = el('tin'), $form = el('o-hoi'),
      $cauHoi = el('cau-hoi'), $nutGui = el('nut-gui'), $goiY = el('goi-y'), $tieuDe = el('tieu-de-cuoc');

  function t(k) { return (CHU[tt.ngonNgu] || CHU.vi)[k] || CHU.vi[k] || k; }
  function dien(mau, d) { return mau.replace(/\{(\w+)\}/g, function (_, k) { return d[k] == null ? '' : d[k]; }); }

  function luu() {
    try { localStorage.setItem(LUU, JSON.stringify({ cuoc: tt.cuoc.slice(0, 60), hienTai: tt.hienTai })); } catch (e) { /* riêng tư / đầy */ }
  }
  function nap() {
    try {
      var d = JSON.parse(localStorage.getItem(LUU) || 'null');
      if (d && Array.isArray(d.cuoc)) { tt.cuoc = d.cuoc; tt.hienTai = d.hienTai; }
      tt.ngonNgu = localStorage.getItem(LUU_NGON_NGU) || (navigator.language || 'vi').slice(0, 2);
      if (!CHU[tt.ngonNgu]) tt.ngonNgu = 'vi';
      var tb = JSON.parse(localStorage.getItem(LUU_THONG_BAO) || 'null');
      if (tb) { tt.thongBao = tb.thongBao || []; tt.daDocToi = tb.daDocToi || 0; tt.moiNhat = tb.moiNhat || 0; tt.choPhepNgoai = !!tb.choPhepNgoai; }
    } catch (e) { tt.ngonNgu = 'vi'; }
  }
  function luuThongBao() {
    try { localStorage.setItem(LUU_THONG_BAO, JSON.stringify({ thongBao: tt.thongBao.slice(-100), daDocToi: tt.daDocToi, moiNhat: tt.moiNhat, choPhepNgoai: tt.choPhepNgoai })); } catch (e) {}
  }

  // ------------------------------------------------------------------ Markdown → HTML (an toàn)
  function thoat(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function trongDong(s) {
    s = thoat(s);
    s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
    s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/(^|[^*\w])\*([^*\n]+)\*(?!\w)/g, '$1<em>$2</em>');
    s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    return s;
  }
  var SO = /^[\s$€£₭฿]*[-+]?[\d.,]+\s*(%|VNĐ|VND|USD|THB|LAK|đ|kg|km|m3|m³)?\s*$/i;
  function bang(dong) {
    var hang = dong.map(function (d) {
      return d.replace(/^\s*\|/, '').replace(/\|\s*$/, '').split('|').map(function (c) { return c.trim(); });
    });
    var dau = hang[0], than = hang.slice(1).filter(function (h) { return !/^[-:\s|]+$/.test(h.join('|')); });
    var h = '<table><thead><tr>' + dau.map(function (c) { return '<th>' + trongDong(c) + '</th>'; }).join('') + '</tr></thead><tbody>';
    than.forEach(function (r) {
      h += '<tr>' + dau.map(function (_, i) {
        var c = r[i] || '';
        return '<td' + (SO.test(c) ? ' class="so"' : '') + '>' + trongDong(c) + '</td>';
      }).join('') + '</tr>';
    });
    return h + '</tbody></table>';
  }
  function markdown(md) {
    var dong = String(md || '').replace(/\r/g, '').split('\n'), ra = [], i = 0;
    while (i < dong.length) {
      var d = dong[i];
      if (/^```/.test(d)) {
        var ma = []; i++;
        while (i < dong.length && !/^```/.test(dong[i])) ma.push(dong[i++]);
        i++; ra.push('<pre><code>' + thoat(ma.join('\n')) + '</code></pre>'); continue;
      }
      if (/^\s*\|.*\|\s*$/.test(d) && i + 1 < dong.length && /^\s*\|?[\s:|-]+\|?\s*$/.test(dong[i + 1])) {
        var b = []; while (i < dong.length && /^\s*\|.*\|\s*$/.test(dong[i])) b.push(dong[i++]);
        ra.push(bang(b)); continue;
      }
      var m = /^(#{1,3})\s+(.*)$/.exec(d);
      if (m) { ra.push('<h' + m[1].length + '>' + trongDong(m[2]) + '</h' + m[1].length + '>'); i++; continue; }
      if (/^\s*([-*•])\s+/.test(d)) {
        var u = []; while (i < dong.length && /^\s*([-*•])\s+/.test(dong[i])) u.push(dong[i++].replace(/^\s*[-*•]\s+/, ''));
        ra.push('<ul>' + u.map(function (x) { return '<li>' + trongDong(x) + '</li>'; }).join('') + '</ul>'); continue;
      }
      if (/^\s*\d+[.)]\s+/.test(d)) {
        var o = []; while (i < dong.length && /^\s*\d+[.)]\s+/.test(dong[i])) o.push(dong[i++].replace(/^\s*\d+[.)]\s+/, ''));
        ra.push('<ol>' + o.map(function (x) { return '<li>' + trongDong(x) + '</li>'; }).join('') + '</ol>'); continue;
      }
      if (/^\s*>\s?/.test(d)) {
        var q = []; while (i < dong.length && /^\s*>\s?/.test(dong[i])) q.push(dong[i++].replace(/^\s*>\s?/, ''));
        ra.push('<blockquote>' + trongDong(q.join(' ')) + '</blockquote>'); continue;
      }
      if (/^\s*(-{3,}|\*{3,})\s*$/.test(d)) { ra.push('<hr>'); i++; continue; }
      if (!d.trim()) { i++; continue; }
      var p = []; while (i < dong.length && dong[i].trim() && !/^(#{1,3}\s|\s*[-*•]\s|\s*\d+[.)]\s|\s*\||```|\s*>)/.test(dong[i])) p.push(dong[i++]);
      if (!p.length) { p.push(d); i++; }
      ra.push('<p>' + trongDong(p.join(' ')) + '</p>');
    }
    return ra.join('');
  }

  // ------------------------------------------------------------------ vẽ
  function veNgonNgu() {
    document.documentElement.lang = tt.ngonNgu;
    document.querySelectorAll('[data-i18n]').forEach(function (n) { n.textContent = t(n.getAttribute('data-i18n')); });
    document.querySelectorAll('[data-i18n-ph]').forEach(function (n) { n.placeholder = t(n.getAttribute('data-i18n-ph')); });
    document.querySelectorAll('#chon-ngon-ngu button').forEach(function (b) {
      b.setAttribute('aria-checked', b.getAttribute('data-ngon-ngu') === tt.ngonNgu ? 'true' : 'false');
    });
    var g = new Date().getHours();
    el('loi-chao').textContent = g < 12 ? t('chao_sang') : g < 18 ? t('chao_chieu') : t('chao_toi');
    $goiY.innerHTML = '';
    t('goi_y').forEach(function (c) {
      var b = document.createElement('button'); b.type = 'button'; b.textContent = c;
      b.addEventListener('click', function () { $cauHoi.value = c; guiCauHoi(); });
      $goiY.appendChild(b);
    });
    veDanhSach(); veThongBao();
  }

  function cuocHienTai() {
    for (var i = 0; i < tt.cuoc.length; i++) if (tt.cuoc[i].id === tt.hienTai) return tt.cuoc[i];
    return null;
  }

  function veDanhSach() {
    $ds.innerHTML = '';
    if (!tt.cuoc.length) { var e = document.createElement('div'); e.className = 'ds-trong'; e.textContent = t('chua_co'); $ds.appendChild(e); return; }
    tt.cuoc.forEach(function (c) {
      var b = document.createElement('button'); b.type = 'button'; b.className = 'cuoc' + (c.id === tt.hienTai ? ' dang-chon' : '');
      var ten = document.createElement('span'); ten.className = 'ten'; ten.textContent = c.tieuDe || t('cuoc_moi');
      var x = document.createElement('span'); x.className = 'xoa'; x.textContent = '×'; x.title = t('xoa'); x.setAttribute('role', 'button');
      x.addEventListener('click', function (ev) { ev.stopPropagation(); xoaCuoc(c.id); });
      b.appendChild(ten); b.appendChild(x);
      b.addEventListener('click', function () { moCuoc(c.id); });
      $ds.appendChild(b);
    });
  }

  var nutTin = {};   // id tin → nút DOM đang hiện, để cập nhật khi stream mà không vẽ lại cả trang

  function veTin() {
    var c = cuocHienTai();
    $tin.innerHTML = ''; nutTin = {};
    $ung.classList.toggle('dang-chat', !!(c && c.tin.length));
    $tieuDe.textContent = c && c.tin.length ? (c.tieuDe || '') : '';
    if (!c || !c.tin.length) return;
    var cot = document.createElement('div'); cot.className = 'cot-tin';
    c.tin.forEach(function (m) { cot.appendChild(veMotTin(m)); });
    $tin.appendChild(cot);
    $tin.scrollTop = $tin.scrollHeight;
  }

  function veChipDaXem(m, dx) {
    dx.innerHTML = '';
    var nhan = document.createElement('span'); nhan.textContent = (m.dangNghi ? t('dang_tra') : t('da_xem')) + ':'; dx.appendChild(nhan);
    var daCo = {};
    (m.congCu || []).forEach(function (cc) {
      var k = cc.nhan || cc.ten; if (daCo[k]) return; daCo[k] = 1;
      var chip = document.createElement('span'); chip.className = 'chip' + (cc.loi ? ' loi' : '') + (cc.xong ? '' : ' dang'); chip.textContent = k;
      if (cc.loi) chip.title = cc.loi;
      dx.appendChild(chip);
    });
  }

  function veMotTin(m) {
    var w = document.createElement('article');
    if (m.vai === 'user') {
      w.className = 'tin-nhan nguoi';
      var nd = document.createElement('div'); nd.className = 'noi-dung'; nd.textContent = m.noiDung;
      w.appendChild(nd); return w;
    }
    w.className = 'tin-nhan tro-ly';
    var av = document.createElement('img'); av.className = 'avatar'; av.src = 'img/logo-epl.jpg'; av.alt = '';
    var than = document.createElement('div'); than.className = 'than';
    var dx = document.createElement('div'); dx.className = 'da-xem'; dx.hidden = !(m.congCu && m.congCu.length);
    veChipDaXem(m, dx); than.appendChild(dx);
    if (m.loi) {
      var l = document.createElement('div'); l.className = 'loi-tin'; l.textContent = m.loi;
      var tl = document.createElement('button'); tl.type = 'button'; tl.textContent = t('thu_lai');
      tl.addEventListener('click', function () { thuLai(m); });
      l.appendChild(tl); than.appendChild(l);
    } else if (m.dangNghi && !m.noiDung) {
      var dn = document.createElement('div'); dn.className = 'dang-nghi';
      var ch = document.createElement('span'); ch.className = 'cham'; dn.appendChild(ch);
      var tx = document.createElement('span'); tx.textContent = t('dang_nghi'); dn.appendChild(tx);
      than.appendChild(dn);
    } else {
      var nd2 = document.createElement('div'); nd2.className = 'noi-dung'; nd2.innerHTML = markdown(m.noiDung);
      than.appendChild(nd2);
      if (!m.dangNghi) {
        var hcc = document.createElement('div'); hcc.className = 'hang-cong-cu';
        var sc = document.createElement('button'); sc.type = 'button'; sc.textContent = t('sao_chep');
        sc.addEventListener('click', function () {
          (navigator.clipboard ? navigator.clipboard.writeText(m.noiDung) : Promise.reject()).then(function () {
            sc.textContent = t('da_sao_chep'); setTimeout(function () { sc.textContent = t('sao_chep'); }, 1500);
          }, function () {});
        });
        hcc.appendChild(sc);
        if (m.giay) { var luc = document.createElement('span'); luc.className = 'luc'; luc.textContent = m.giay + 's'; hcc.appendChild(luc); }
        than.appendChild(hcc);
      }
    }
    w.appendChild(av); w.appendChild(than);
    if (m.id) nutTin[m.id] = w;
    return w;
  }

  /** Vẽ lại đúng MỘT tin đang stream (thay nút cũ), giữ vị trí cuộn ở đáy. */
  function veLaiTin(m) {
    var cu = nutTin[m.id];
    if (!cu || !cu.parentNode) { veTin(); return; }
    var moi = veMotTin(m);
    cu.parentNode.replaceChild(moi, cu);
    $tin.scrollTop = $tin.scrollHeight;
  }

  // ------------------------------------------------------------------ hành vi
  function taoCuoc() {
    var c = { id: 'c' + Date.now().toString(36), tieuDe: '', tin: [], luc: Date.now(), ngonNgu: tt.ngonNgu };
    tt.cuoc.unshift(c); tt.hienTai = c.id; luu(); veDanhSach(); veTin(); $cauHoi.focus();
    return c;
  }
  function moCuoc(id) { tt.hienTai = id; luu(); veDanhSach(); veTin(); if (window.innerWidth <= 820) $ung.classList.add('ben-an'); }
  function xoaCuoc(id) {
    tt.cuoc = tt.cuoc.filter(function (c) { return c.id !== id; });
    if (tt.hienTai === id) tt.hienTai = tt.cuoc.length ? tt.cuoc[0].id : null;
    luu(); veDanhSach(); veTin();
  }

  function guiCauHoi(cauSan) {
    var cau = (cauSan || $cauHoi.value).trim();
    if (!cau || tt.dangGui) return;
    var c = cuocHienTai() || taoCuoc();
    if (!c.tieuDe) c.tieuDe = cau.length > 48 ? cau.slice(0, 46) + '…' : cau;
    c.tin.push({ vai: 'user', noiDung: cau, luc: Date.now() });
    var cho = { id: 'm' + Date.now().toString(36), vai: 'model', noiDung: '', dangNghi: true, congCu: [], luc: Date.now() };
    c.tin.push(cho);
    $cauHoi.value = ''; coGian(); luu(); veDanhSach(); veTin();
    hoiMayChu(c, cho, cau);
  }

  function thuLai(m) {
    var c = cuocHienTai(); if (!c) return;
    var i = c.tin.indexOf(m); if (i < 1) return;
    var cau = c.tin[i - 1].noiDung;
    c.tin[i] = { id: 'm' + Date.now().toString(36), vai: 'model', noiDung: '', dangNghi: true, congCu: [], luc: Date.now() };
    veTin(); hoiMayChu(c, c.tin[i], cau);
  }

  /** Đọc text/event-stream từ fetch: gọi `xuLy(event, data)` cho từng sự kiện. */
  function docSSE(phanHoi, xuLy) {
    var doc = phanHoi.body.getReader(), giai = new TextDecoder('utf-8'), dem = '';
    function tiep() {
      return doc.read().then(function (r) {
        if (r.done) { return; }
        dem += giai.decode(r.value, { stream: true });
        var khoi;
        while ((khoi = dem.indexOf('\n\n')) >= 0) {
          var goi = dem.slice(0, khoi); dem = dem.slice(khoi + 2);
          var ev = 'message', du = '';
          goi.split('\n').forEach(function (d) {
            if (d.indexOf('event:') === 0) ev = d.slice(6).trim();
            else if (d.indexOf('data:') === 0) du += d.slice(5).trim();
          });
          if (du) { try { xuLy(ev, JSON.parse(du)); } catch (e) { /* mảnh hỏng thì bỏ */ } }
        }
        return tiep();
      });
    }
    return tiep();
  }

  function hoiMayChu(c, cho, cau) {
    tt.dangGui = true; $nutGui.disabled = true;
    // Lịch sử gửi lên: mọi lượt TRƯỚC câu hỏi này — lời hỏi-đáp kèm dữ liệu đã tra.
    var lichSu = [];
    for (var i = 0; i < c.tin.length; i++) {
      var m = c.tin[i];
      if (m === cho) break;
      if (m.vai === 'user' && c.tin[i + 1] && c.tin[i + 1] === cho) break;
      if (m.dangNghi || m.loi) continue;
      var muc = { vai: m.vai === 'user' ? 'user' : 'model', noi_dung: m.noiDung };
      if (m.nguCanh) muc.ngu_canh = m.nguCanh;
      lichSu.push(muc);
    }
    var xong = false;
    fetch('/hoi', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cau_hoi: cau, lich_su: lichSu, ngon_ngu: tt.ngonNgu })
    }).then(function (r) {
      if (!r.ok || !r.body) { return r.json().then(function (g) { throw new Error(g.loi || ('HTTP ' + r.status)); }); }
      return docSSE(r, function (ev, g) {
        if (ev === 'cong_cu') { cho.congCu.push({ ten: g.ten, nhan: g.nhan, xong: false }); veLaiTin(cho); }
        else if (ev === 'cong_cu_xong') {
          for (var k = 0; k < cho.congCu.length; k++) if (cho.congCu[k].ten === g.ten && !cho.congCu[k].xong) { cho.congCu[k].xong = true; cho.congCu[k].loi = g.loi; break; }
          veLaiTin(cho);
        }
        else if (ev === 'chu_them') { cho.noiDung += g; veLaiTin(cho); }
        else if (ev === 'chu_xoa') { cho.noiDung = ''; veLaiTin(cho); }
        else if (ev === 'xong') { xong = true; cho.dangNghi = false; cho.noiDung = g.tra_loi || cho.noiDung; cho.congCu = (g.cong_cu_da_dung || []).map(function (x) { x.xong = true; return x; }); cho.giay = g.giay; cho.nguCanh = g.ngu_canh || ''; }
        else if (ev === 'loi') { xong = true; cho.dangNghi = false; cho.loi = g.loi; cho.congCu = g.cong_cu_da_dung || cho.congCu; }
      });
    }).then(function () {
      if (!xong) { cho.dangNghi = false; if (!cho.noiDung) cho.loi = t('loi_mang'); }
    }).catch(function (e) {
      cho.dangNghi = false; cho.loi = (e && e.message) || t('loi_mang');
    }).then(function () {
      tt.dangGui = false; luu(); veLaiTin(cho); capNhatNutGui(); $cauHoi.focus();
    });
  }

  function coGian() { $cauHoi.style.height = 'auto'; $cauHoi.style.height = Math.min($cauHoi.scrollHeight, 200) + 'px'; }
  function capNhatNutGui() { $nutGui.disabled = tt.dangGui || !$cauHoi.value.trim(); }

  function kiemSucKhoe() {
    var $t = el('trang-thai-may');
    fetch('/suc-khoe').then(function (r) { return r.json(); }).then(function (g) {
      if (g.mo_hinh) el('nhan-mo-hinh').textContent = String(g.mo_hinh).replace(/^gemini-/i, 'Gemini ').replace(/-/g, ' ').replace(/\b\w/g, function (x) { return x.toUpperCase(); });
      var loi = [];
      if (!g.gemini_co_khoa) loi.push(t('thieu_khoa'));
      if (!g.epl_ok) loi.push(t('epl_tat'));
      $t.hidden = !loi.length; $t.textContent = loi.join(' · '); $t.classList.toggle('loi', !g.epl_ok);
    }).catch(function () { $t.hidden = false; $t.textContent = t('loi_mang'); $t.classList.add('loi'); });
  }

  function datGiaoDien(che) {
    if (che === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
    else document.documentElement.removeAttribute('data-theme');
    try { localStorage.setItem(LUU_GIAO_DIEN, che); } catch (e) {}
  }

  // ------------------------------------------------------------------ thông báo
  function cauThongBao(s) {
    var d = { ma: s.ma, xe: s.xe || '—', khach: s.khach || '', gia: '' };
    if (s.loai === 'bao_gia_moi' && s.gia) d.gia = ' · ' + t('gia') + ' ' + dinhDangTien(s.gia, s.tien_te);
    if ((s.loai === 'xe_xuat_phat' || s.loai === 'xe_hoan_tat')) d.khach = s.khach ? ' (' + s.khach + ')' : '';
    return dien((t('tb') || {})[s.loai] || (s.loai + ' ' + s.ma), d);
  }
  function dinhDangTien(so, tien) {
    var n = Number(so); if (!isFinite(n)) return String(so);
    var chu = tt.ngonNgu === 'en' ? n.toLocaleString('en-US') : n.toLocaleString('de-DE');
    return chu + ' ' + (tien === 'VND' && tt.ngonNgu !== 'en' ? 'VNĐ' : (tien || ''));
  }
  function gioNgan(iso) {
    var d = new Date(iso); if (isNaN(d)) return '';
    return ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2) + ' · ' + ('0' + d.getDate()).slice(-2) + '/' + ('0' + (d.getMonth() + 1)).slice(-2);
  }

  function veThongBao() {
    var $ds2 = el('ds-thong-bao'), $dem = el('dem-chuong');
    var chuaDoc = tt.thongBao.filter(function (s) { return s.id > tt.daDocToi; }).length;
    $dem.hidden = !chuaDoc; $dem.textContent = chuaDoc > 99 ? '99+' : String(chuaDoc);
    $ds2.innerHTML = '';
    if (!tt.thongBao.length) { var tr = document.createElement('div'); tr.className = 'trong'; tr.textContent = t('chua_thong_bao'); $ds2.appendChild(tr); }
    tt.thongBao.slice().reverse().slice(0, 60).forEach(function (s) {
      var w = document.createElement('div'); w.className = 'tb ' + s.loai + (s.id > tt.daDocToi ? ' chua-doc' : '');
      var bt = document.createElement('span'); bt.className = 'bt'; bt.textContent = BIEU_TUONG_TB[s.loai] || '•';
      var noi = document.createElement('div'); noi.className = 'noi';
      var chu = document.createElement('div'); chu.textContent = cauThongBao(s); noi.appendChild(chu);
      var luc = document.createElement('span'); luc.className = 'luc'; luc.textContent = gioNgan(s.luc); noi.appendChild(luc);
      var hoi = document.createElement('button'); hoi.type = 'button'; hoi.textContent = t('hoi_them');
      hoi.addEventListener('click', function () {
        dongBangThongBao();
        guiCauHoi(dien((t('hoi_tb') || {})[s.loai] || ('{ma}'), { ma: s.ma, xe: s.xe || '' }));
      });
      noi.appendChild(hoi);
      w.appendChild(bt); w.appendChild(noi); $ds2.appendChild(w);
    });
    el('check-trinh-duyet').checked = tt.choPhepNgoai;
  }

  function toast(s) {
    var $v = el('toast-vung');
    var w = document.createElement('div'); w.className = 'toast';
    var bt = document.createElement('span'); bt.className = 'bt'; bt.textContent = BIEU_TUONG_TB[s.loai] || '•';
    var chu = document.createElement('div'); chu.textContent = cauThongBao(s);
    var x = document.createElement('button'); x.type = 'button'; x.className = 'dong'; x.textContent = '×'; x.setAttribute('aria-label', 'Đóng');
    x.addEventListener('click', function () { w.remove(); });
    w.appendChild(bt); w.appendChild(chu); w.appendChild(x); $v.appendChild(w);
    setTimeout(function () { if (w.parentNode) w.remove(); }, 9000);
    if (tt.choPhepNgoai && document.hidden && window.Notification && Notification.permission === 'granted') {
      try { new Notification('EPL ' + t('tro_ly'), { body: cauThongBao(s), icon: 'img/logo-epl.jpg', tag: 'epl-' + s.id }); } catch (e) {}
    }
  }

  function keoThongBao() {
    fetch('/thong-bao?sau=' + encodeURIComponent(tt.moiNhat)).then(function (r) { return r.json(); }).then(function (g) {
      var moi = g.su_kien || [];
      // Máy chủ khởi động lại thì bộ đếm về 0: đồng bộ lại, không báo lại cái cũ.
      if (typeof g.moi_nhat === 'number' && g.moi_nhat < tt.moiNhat) { tt.moiNhat = g.moi_nhat; tt.daDocToi = Math.min(tt.daDocToi, g.moi_nhat); moi = []; }
      if (moi.length) {
        moi.forEach(function (s) { tt.thongBao.push(s); toast(s); });
        tt.thongBao = tt.thongBao.slice(-100);
        tt.moiNhat = Math.max(tt.moiNhat, moi[moi.length - 1].id);
        luuThongBao(); veThongBao();
      }
      if (g.lan_doc_cuoi) el('giam-sat-luc').textContent = t('giam_sat_luc') + ' ' + gioNgan(g.lan_doc_cuoi).split(' · ')[0];
    }).catch(function () { /* mất mạng một nhịp thì lần sau hỏi lại */ });
  }

  function moBangThongBao() {
    el('bang-thong-bao').hidden = false; el('nut-chuong').setAttribute('aria-expanded', 'true'); veThongBao();
  }
  function dongBangThongBao() {
    el('bang-thong-bao').hidden = true; el('nut-chuong').setAttribute('aria-expanded', 'false');
  }

  // ------------------------------------------------------------------ gắn sự kiện
  $form.addEventListener('submit', function (ev) { ev.preventDefault(); guiCauHoi(); });
  $cauHoi.addEventListener('input', function () { coGian(); capNhatNutGui(); });
  $cauHoi.addEventListener('keydown', function (ev) {
    if (ev.key === 'Enter' && !ev.shiftKey && !ev.isComposing) { ev.preventDefault(); guiCauHoi(); }
  });
  el('nut-moi').addEventListener('click', function () { taoCuoc(); if (window.innerWidth <= 820) $ung.classList.add('ben-an'); });
  el('nut-dong-ben').addEventListener('click', function () { $ung.classList.add('ben-an'); });
  el('nut-mo-ben').addEventListener('click', function () { $ung.classList.remove('ben-an'); });
  el('chon-ngon-ngu').addEventListener('click', function (ev) {
    var b = ev.target.closest('button[data-ngon-ngu]'); if (!b) return;
    tt.ngonNgu = b.getAttribute('data-ngon-ngu');
    try { localStorage.setItem(LUU_NGON_NGU, tt.ngonNgu); } catch (e) {}
    veNgonNgu(); veTin();
  });
  el('nut-giao-dien').addEventListener('click', function () {
    datGiaoDien(document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
  });
  el('nut-chuong').addEventListener('click', function () {
    if (el('bang-thong-bao').hidden) moBangThongBao(); else dongBangThongBao();
  });
  el('nut-doc-het').addEventListener('click', function () { tt.daDocToi = tt.moiNhat; luuThongBao(); veThongBao(); });
  el('check-trinh-duyet').addEventListener('change', function (ev) {
    tt.choPhepNgoai = ev.target.checked; luuThongBao();
    if (tt.choPhepNgoai && window.Notification && Notification.permission === 'default') Notification.requestPermission();
  });
  document.addEventListener('click', function (ev) {
    if (!el('bang-thong-bao').hidden && !ev.target.closest('.chuong-vung')) dongBangThongBao();
  });
  document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') dongBangThongBao(); });

  // ------------------------------------------------------------------ khởi động
  nap();
  var gd = null; try { gd = localStorage.getItem(LUU_GIAO_DIEN); } catch (e) {}
  if (gd === 'dark' || (!gd && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)) datGiaoDien('dark');
  if (window.innerWidth <= 820) $ung.classList.add('ben-an');
  veNgonNgu(); veTin(); capNhatNutGui(); kiemSucKhoe();
  keoThongBao(); setInterval(keoThongBao, CHU_KY_THONG_BAO);
  $cauHoi.focus();

  window.EPL_TROLY = { markdown: markdown, CHU: CHU, cauThongBao: cauThongBao, guiCauHoi: guiCauHoi };   // cho bộ kiểm
})();

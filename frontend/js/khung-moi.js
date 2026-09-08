/* ==========================================================================
   KHUNG BA TẦNG — điều hướng trên, đầu trang, và tìm để đi tới màn.

   Khung cũ có bốn mục "mega menu" chia theo PHÂN HỆ, cộng một dải dọc bên trái
   lặp lại đúng sơ đồ tám bước đã có sẵn trên Bảng điều khiển. Dải dọc ăn 78px
   chiều ngang của MỌI màn, còn cách chia theo phân hệ buộc người dùng phải biết
   trước "Giao hàng & chứng từ" khác "Điều phối & thực thi" ở chỗ nào.

   Khung mới chia theo CÔNG VIỆC: một người điều phối chỉ mở "Vận hành".

   VÌ SAO ĐỂ RIÊNG MỘT TỆP: `app.js` đã 950 KB. Khung là thứ ít đổi và không
   phụ thuộc màn nào, nên tách ra thì sau này muốn xem khung gồm những gì chỉ
   phải đọc một tệp. Tệp này nạp SAU `app.js` và chỉ móc vào một chỗ duy nhất —
   `window.switchView` — bằng cách bọc lại hàm đó.
   ========================================================================== */

(function () {
  'use strict';

  /**
   * Mỗi màn khai: nhóm ở tầng 2, đường dẫn, tiêu đề, và một câu nói màn này để
   * làm gì. Câu mô tả không phải để trang trí — nó là chỗ duy nhất nói rõ ranh
   * giới giữa các màn gần nhau, ví dụ vì sao chọn DO ở màn này mà ghép xe ở màn
   * khác.
   */
  const DAU_TRANG_THEO_MAN = {
    'dashboard': ['', '', 'Bảng điều khiển',
      'Số liệu hôm nay và sơ đồ luồng A–Z của tám nhóm chức năng.'],
    'ops-planning': ['ops', 'Vận hành', 'Lệnh giao hàng (DO)',
      'Chọn DO cần chạy rồi lập Trip. Xe và tổ lái được ghép ở màn Điều phối.'],
    'delivery-shipment': ['ops', 'Vận hành', 'Giao hàng và vận chuyển',
      'Trip vận chuyển: gộp DO cùng tuyến, đặt thời gian bốc dỡ và kế hoạch chặng về.'],
    'dispatch': ['ops', 'Vận hành', 'Điều phối và thực thi',
      'Gán xe và tổ lái cho Trip, kiểm điều kiện rồi cho xuất bến.'],
    'tracking': ['ops', 'Vận hành', 'Theo dõi và kiểm soát',
      'GPS, tiến độ từng chặng, mốc đã đến nơi và sự cố của các chuyến đang chạy.'],
    'delivery-completion': ['ops', 'Vận hành', 'Hoàn tất giao hàng',
      'Nộp POD ký nhận, quyết toán chi phí và đóng DO. Tiền chỉ chốt được sau khi có POD.'],
    'parking-list': ['ops', 'Vận hành', 'Packing List và tem QR',
      'Gói hàng theo chuyến và in tem QR để soi ở chốt.'],
    'ai-checkpoint': ['ops', 'Vận hành', 'Trạm kiểm soát AI',
      'Đọc ảnh biển số và niêm phong tại chốt, đối chiếu với Trip đang chạy.'],
    'crm-sales': ['biz', 'Kinh doanh', 'CRM và Báo giá cước',
      'Khách hàng và báo giá cước. Khách chấp nhận báo giá là tách thẳng thành '
      + 'lệnh giao hàng — không còn bước Đơn hàng ở giữa.'],
    'accounting': ['biz', 'Kinh doanh', 'Kế toán và tài chính',
      'Hóa đơn, công nợ và hạch toán từ các chuyến đã hoàn tất.'],
    'master-data': ['master', 'Dữ liệu gốc', 'Dữ liệu gốc',
      'Tuyến, công thức giá thành, loại xe, xe, khách hàng — nguồn mà báo giá và điều phối đọc.'],
    'lab-summary': ['more', 'Báo cáo và khác', 'Phân tích doanh thu và chi phí',
      'Giá thành, cước báo giá và lợi nhuận theo tuyến, xe và khách.'],
    'operations-360': ['more', 'Báo cáo và khác', 'Quản trị / Shipment 360°',
      'Một chuyến, xem hết mọi tầng: DO, Trip, chứng từ, chi phí.'],
  };

  /**
   * Nút chính của từng màn: [chữ, kiểu, tên hàm, đối số nếu có].
   *
   * HAI chốt khi thêm vào bảng này:
   *
   *   1. Hàm phải CÓ THẬT và gọi được với đúng số đối số đó — trước khi vẽ nút
   *      còn kiểm `typeof` một lần nữa. Một nút "+ Tạo gì đó" bấm vào không ra
   *      gì làm người dùng mất tin cả những nút chạy thật.
   *   2. Việc đó phải CHƯA có nút nào trong màn. Bảng này thoạt đầu khai sáu
   *      nút, tra lại thì bốn cái trùng với nút đã có sẵn ngay trong màn:
   *      `openTripReturnAction` đã có nút ở cả Giao hàng và Điều phối,
   *      `openIncidentModal` và `openPODFormForSelectedDO` đã có ở Theo dõi,
   *      `openOracleQTForm` đã có ở CRM. Hai nút cho cùng một việc thì người
   *      dùng phải đoán chúng có khác nhau không, và khi một bên đổi thì bên
   *      kia lặng lẽ lệch.
   *
   * Nên bảng chỉ còn hai nút, là hai việc chưa có chỗ nào bấm được.
   */
  const NUT_DAU_TRANG = {
    'ops-planning': [['+ Tạo lệnh giao hàng', 'primary', 'openFioriDOForm']],
    // Màn CRM KHÔNG khai nút ở đây nữa.
    //
    // Trước là "+ Đơn hàng vận chuyển" (`openOracleSOForm`). Bước Đơn hàng đã
    // bị bỏ khỏi luồng — báo giá được chấp nhận thì tách thẳng thành lệnh giao
    // hàng — nên một nút mở form của bước đó là mời người dùng đi vào một
    // đường không còn dẫn tới đâu. Nút "+ Báo giá" của luồng mới đã có sẵn
    // ngay trong màn, ở đầu trang danh sách báo giá.
  };

  /**
   * Đầu trang cho từng THẺ của màn Dữ liệu gốc.
   *
   * Vì sao cần riêng: màn `master-data` gộp 11 thẻ rất khác nhau, và hai trong
   * số đó không phải dữ liệu gốc theo nghĩa "khai một lần rồi để đó". Rõ nhất là
   * thẻ xếp ca: nó nằm trong nhóm Vận hành của dải điều hướng, nên đi vào từ đó
   * mà đường dẫn lại ghi "Dữ liệu gốc" thì người dùng tưởng mình bấm sai chỗ.
   *
   * Thẻ không khai ở đây thì dùng đầu trang chung của màn Dữ liệu gốc.
   */
  const DAU_TRANG_THEO_THE = {
    'md-tab-vehicles': ['ops', 'Vận hành', 'Sắp lịch xe và tài xế',
      'Ca trực của tài xế, lịch xe theo tuần và kỳ bảo dưỡng — nguồn nhân lực mà màn Điều phối lấy để gán vào Trip.'],
    'md-tab-routes': ['master', 'Dữ liệu gốc', 'Tuyến đường',
      'Chặng A → B → C và km kế hoạch. Báo giá cước, lệnh giao hàng và ETA đều đọc từ đây.'],
    'md-tab-formulas': ['master', 'Dữ liệu gốc', 'Công thức giá thành',
      'Chi phí trên 1 km theo loại xe, và giá cước thu của khách. Hai loại này không cộng chung.'],
    'md-tab-veh-types': ['master', 'Dữ liệu gốc', 'Loại xe và phương tiện',
      'Tải trọng, định mức dầu và giá thành nền của từng loại xe.'],
    'md-tab-customers': ['master', 'Dữ liệu gốc', 'Khách hàng',
      'Thông tin và điều khoản của khách — nguồn mà báo giá cước và đơn hàng đọc.'],
    'md-tab-carriers': ['master', 'Dữ liệu gốc', 'Nhà vận chuyển',
      'Đối tác chạy thuê ngoài, dùng khi đội xe nội bộ không đủ.'],
  };

  /* ----------------------------- Tầng 3: đầu trang ----------------------- */

  function capNhatDauTrang(man, the) {
    // Thẻ khai riêng thì thắng đầu trang của màn — xem `DAU_TRANG_THEO_THE`.
    const d = (the && DAU_TRANG_THEO_THE[the]) || DAU_TRANG_THEO_MAN[man];
    const oCrumb = document.getElementById('epl-crumb');
    const oH1 = document.getElementById('epl-h1');
    const oDesc = document.getElementById('epl-desc');
    const oActs = document.getElementById('epl-subacts');
    if (!oCrumb || !oH1) return;

    // Màn chưa khai trong bảng vẫn phải hiện được tiêu đề chứ không để trống
    // trơn — các màn giữ chỗ (`lab-summary-placeholder`, `lab-panorama-source`)
    // rơi vào nhánh này.
    const nhom = d ? d[0] : '';
    oCrumb.textContent = d ? d[1] : '';
    oH1.textContent = d ? d[2] : man;
    if (oDesc) {
      oDesc.textContent = d ? d[3] : '';
      oDesc.hidden = !(d && d[3]);
    }

    if (oActs) {
      oActs.textContent = '';
      (NUT_DAU_TRANG[man] || []).forEach(function (khai) {
        const chu = khai[0], kieu = khai[1], ten = khai[2], doi = khai[3];
        if (typeof window[ten] !== 'function') return;
        const b = document.createElement('button');
        b.type = 'button';
        b.className = kieu === 'primary' ? 'epl-btn-primary' : 'epl-btn-ghost';
        b.textContent = chu;
        b.addEventListener('click', function () {
          if (doi === undefined) window[ten]();
          else window[ten](doi);
        });
        oActs.appendChild(b);
      });
    }

    // Tầng 2: sáng mục chứa màn đang mở. Nút "Hôm nay" khai `data-view`, bốn nút
    // còn lại khai `data-menu`, nên phải so hai kiểu khác nhau.
    document.querySelectorAll('.epl-nb').forEach(function (b) {
      const dung = b.dataset.menu ? (b.dataset.menu === nhom) : (b.dataset.view === man);
      b.classList.toggle('epl-on', dung);
    });
    document.querySelectorAll('.epl-menu .epl-mi').forEach(function (el) {
      el.classList.toggle('epl-on', !el.dataset.mdTab && el.dataset.view === man);
    });
  }

  /* -------------------------- Tầng 2: bảng chọn -------------------------- */

  function dongBangChon() {
    document.querySelectorAll('.epl-menu').forEach(function (m) {
      m.classList.remove('epl-show');
    });
    document.querySelectorAll('.epl-nb[data-menu]').forEach(function (b) {
      b.setAttribute('aria-expanded', 'false');
    });
  }

  function ganBangChon() {
    const bar = document.getElementById('epl-bar2');
    if (!bar) return;

    document.querySelectorAll('.epl-nb[data-menu]').forEach(function (b) {
      const m = document.getElementById('epl-m-' + b.dataset.menu);
      if (!m) return;
      function mo() {
        dongBangChon();
        // Bảng chọn đặt tuyệt đối trong dải, nên phải tự dóng theo nút. Nếu
        // dóng làm bảng tràn phải khung thì kéo lùi lại cho vừa.
        const trai = Math.min(b.offsetLeft, Math.max(0, bar.clientWidth - m.offsetWidth - 12));
        m.style.left = trai + 'px';
        m.classList.add('epl-show');
        b.setAttribute('aria-expanded', 'true');
      }
      b.addEventListener('click', function (e) {
        e.stopPropagation();
        if (m.classList.contains('epl-show')) dongBangChon(); else mo();
      });
      // Đã mở một bảng rồi thì rê qua nút khác là đổi luôn — không phải bấm
      // lại. Chưa mở bảng nào thì rê qua KHÔNG mở, để con trỏ đi ngang dải
      // không làm bảng nhảy ra.
      b.addEventListener('mouseenter', function () {
        if (document.querySelector('.epl-menu.epl-show')) mo();
      });
    });

    document.addEventListener('click', function (e) {
      if (!e.target.closest('.epl-bar2')) dongBangChon();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') dongBangChon();
    });
  }

  /* ------------ Mọi chỗ khai `data-view` / `data-md-tab` đều đi được ------ */

  function ganDiChuyen() {
    document.querySelectorAll('[data-view], [data-md-tab]').forEach(function (el) {
      if (el.dataset.khungDaGan) return;
      el.dataset.khungDaGan = '1';
      function di() {
        const the = el.dataset.mdTab;
        if (the) {
          // Dùng lại đường mở thẻ Dữ liệu gốc đã có sẵn, chứ không tự đi tìm
          // nút thẻ một lần nữa — hai chỗ làm cùng một việc là hai chỗ để lệch.
          if (typeof window.openMasterSetupStep === 'function') window.openMasterSetupStep(the);
          else window.switchView('master-data');
          // Đặt đầu trang SAU lời gọi trên: `switchView` bên trong nó ghi đầu
          // trang chung của màn Dữ liệu gốc, nên đặt trước là bị ghi đè ngay.
          capNhatDauTrang('master-data', the);
        } else {
          window.switchView(el.dataset.view, el.dataset.scroll || undefined);
        }
        dongBangChon();
      }
      el.addEventListener('click', function (e) {
        e.stopPropagation();
        di();
      });
      if (el.getAttribute('tabindex') !== null) {
        el.addEventListener('keydown', function (e) {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            di();
          }
        });
      }
    });
  }

  /* ------------- Tìm để ĐI TỚI MÀN — cố ý không tìm dữ liệu -------------- */

  /**
   * Mỗi dòng: [tên hiện ra, mô tả, mã màn, thẻ Dữ liệu gốc nếu có, từ khóa].
   *
   * Từ khóa để cả dạng không dấu và tên tiếng Anh cũ, vì người dùng hay gõ
   * "dieu phoi" hoặc "dispatch" chứ không gõ đủ dấu "điều phối".
   */
  const MUC_TIM_MAN = [
    ['Bảng điều khiển', 'Số liệu hôm nay, sơ đồ A–Z', 'dashboard', '',
     'bang dieu khien dashboard tong quan home so do az'],
    ['Lệnh giao hàng (DO)', 'Chọn DO, lập Trip', 'ops-planning', '',
     'lenh giao hang do delivery order lap ke hoach planning'],
    ['Giao hàng và vận chuyển', 'Trip, chặng về', 'delivery-shipment', '',
     'giao hang van chuyen trip shipment chang ve backhaul return'],
    ['Điều phối và thực thi', 'Gán xe và tổ lái', 'dispatch', '',
     'dieu phoi thuc thi dispatch gan xe to lai tai xe xuat ben'],
    ['Theo dõi và kiểm soát', 'GPS, tiến độ, sự cố', 'tracking', '',
     'theo doi kiem soat tracking gps su co eta da den noi'],
    ['Hoàn tất giao hàng', 'POD, quyết toán, đóng DO', 'delivery-completion', '',
     'hoan tat giao hang pod quyet toan ky nhan closeout'],
    ['Packing List và tem QR', 'Gói hàng, in tem', 'parking-list', '',
     'packing list tem qr goi hang in tem parking'],
    ['Trạm kiểm soát AI', 'Đọc ảnh tại chốt', 'ai-checkpoint', '',
     'tram kiem soat ai checkpoint anh bien so niem phong'],
    ['CRM và Kinh doanh', 'Khách hàng, báo giá cước, đơn hàng', 'crm-sales', '',
     'crm kinh doanh khach hang bao gia cuoc quotation don hang van chuyen sales order so qt'],
    ['Kế toán và tài chính', 'Hóa đơn, công nợ', 'accounting', '',
     'ke toan tai chinh accounting hoa don cong no hach toan invoice'],
    ['Phân tích doanh thu và chi phí', 'Lợi nhuận theo tuyến, xe, khách', 'lab-summary', '',
     'phan tich doanh thu chi phi loi nhuan bao cao report analysis'],
    ['Quản trị / Shipment 360°', 'Một chuyến, xem hết mọi tầng', 'operations-360', '',
     'quan tri shipment 360 mot chuyen tat ca'],
    ['Tuyến đường', 'Chặng A → B → C, km kế hoạch', 'master-data', 'md-tab-routes',
     'tuyen duong route chang km ke hoach'],
    ['Công thức giá thành', 'Chi phí trên 1 km và giá cước', 'master-data', 'md-tab-formulas',
     'cong thuc gia thanh cost formula chi phi km cuoc xang dau'],
    ['Loại xe', 'Tải trọng, định mức dầu', 'master-data', 'md-tab-veh-types',
     'loai xe vehicle type tai trong dinh muc dau'],
    ['Xe và thiết bị', 'Đăng kiểm, bảo dưỡng, bãi', 'master-data', 'md-tab-vehicles',
     'xe thiet bi vehicle dang kiem bao duong bai bien so'],
    ['Khách hàng', 'Thông tin và điều khoản', 'master-data', 'md-tab-customers',
     'khach hang customer dieu khoan'],
    ['Nhà vận chuyển', 'Đối tác chạy thuê ngoài', 'master-data', 'md-tab-carriers',
     'nha van chuyen carrier doi tac thue ngoai'],
    ['Dữ liệu gốc', 'Cả 11 thẻ, kèm bước thiết lập', 'master-data', '',
     'du lieu goc master data danh muc thiet lap'],
  ];

  /** Bỏ dấu để "dieu phoi" khớp "Điều phối" — người dùng hiếm khi gõ đủ dấu. */
  function boDau(chuoi) {
    return String(chuoi === null || chuoi === undefined ? '' : chuoi)
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')  // dau thanh va dau mu roi ra sau NFD
      .replace(/đ/g, 'd')
      .replace(/Đ/g, 'D')
      .toLowerCase();
  }

  function chuAnToan(chuoi) {
    if (typeof window.escapeHtml === 'function') return window.escapeHtml(chuoi);
    const d = document.createElement('div');
    d.textContent = chuoi;
    return d.innerHTML;
  }

  function diToiMuc(muc) {
    const man = muc[2], the = muc[3];
    if (the && typeof window.openMasterSetupStep === 'function') {
      window.openMasterSetupStep(the);
      capNhatDauTrang(man, the);
    } else {
      window.switchView(man);
    }
  }

  /**
   * Bấm thẳng vào dải thẻ BÊN TRONG màn Dữ liệu gốc cũng phải đổi đầu trang.
   *
   * Không bọc thì đường dẫn chỉ đúng khi người dùng đi từ dải điều hướng: bấm
   * "Sắp lịch xe và tài xế" ở dải thẻ trong màn thì tiêu đề vẫn nằm ở thẻ trước
   * đó. Bọc ngoài chứ không sửa trong `app.js` vì hàm gốc còn được gọi từ nhiều
   * chỗ khác, và ở đây chỉ cần thêm việc, không cần đổi việc cũ.
   */
  function bocSwitchMasterDataTab() {
    const goc = window.switchMasterDataTab;
    if (typeof goc !== 'function' || goc.daBocKhung) return;
    const boc = function (the) {
      const kq = goc.apply(this, arguments);
      try {
        capNhatDauTrang('master-data', the);
      } catch (loi) {
        console.error('Không cập nhật được đầu trang theo thẻ:', loi);
      }
      return kq;
    };
    boc.daBocKhung = true;
    window.switchMasterDataTab = boc;
  }

  function ganTimManHinh() {
    const o = document.getElementById('tim-man-hinh');
    if (!o) return;

    const bang = document.createElement('div');
    bang.id = 'ket-qua-tim-man';
    bang.className = 'epl-gres';
    bang.setAttribute('role', 'listbox');
    bang.hidden = true;
    o.parentElement.appendChild(bang);

    let dsHien = [];
    let iChon = -1;

    function dong() {
      bang.hidden = true;
      o.setAttribute('aria-expanded', 'false');
      iChon = -1;
    }

    function danhDau() {
      bang.querySelectorAll('.epl-gr').forEach(function (el, i) {
        el.classList.toggle('epl-on', i === iChon);
      });
    }

    function ve() {
      const q = boDau(o.value).trim();
      if (!q) { dong(); return; }
      dsHien = MUC_TIM_MAN.filter(function (m) {
        return boDau(m[0]).indexOf(q) >= 0 || boDau(m[1]).indexOf(q) >= 0
          || m[4].indexOf(q) >= 0;
      });
      if (!dsHien.length) {
        // Nói rõ ô này làm gì, thay vì chỉ "không có kết quả": người gõ mã DO
        // vào đây mà chỉ thấy "không có kết quả" sẽ kết luận hệ thống hỏng.
        bang.innerHTML = '<div class="epl-gempty">Không có màn nào khớp. Ô này'
          + ' <b>đi tới màn</b>, không tìm dữ liệu — mã DO hay biển số thì tìm'
          + ' bên trong màn tương ứng.</div>';
        iChon = -1;
      } else {
        bang.innerHTML = dsHien.map(function (m, i) {
          return '<div class="epl-gr' + (i === 0 ? ' epl-on' : '') + '"'
            + ' role="option" data-i="' + i + '"><i>›</i><div><b>'
            + chuAnToan(m[0]) + '</b><span>' + chuAnToan(m[1])
            + '</span></div></div>';
        }).join('');
        iChon = 0;
        bang.querySelectorAll('.epl-gr').forEach(function (el) {
          // `mousedown` chứ không `click`: `blur` của ô nhập chạy trước `click`
          // và đóng bảng đi, nên gắn vào `click` thì bấm chuột không ăn.
          el.addEventListener('mousedown', function (ev) {
            ev.preventDefault();
            diToiMuc(dsHien[Number(el.dataset.i)]);
            o.value = '';
            dong();
          });
        });
      }
      bang.hidden = false;
      o.setAttribute('aria-expanded', 'true');
    }

    o.addEventListener('input', ve);
    o.addEventListener('focus', function () { if (o.value) ve(); });
    o.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        if (bang.hidden || !dsHien.length) return;
        e.preventDefault();
        iChon = (iChon + (e.key === 'ArrowDown' ? 1 : -1) + dsHien.length) % dsHien.length;
        danhDau();
      } else if (e.key === 'Enter') {
        if (bang.hidden || iChon < 0 || !dsHien[iChon]) return;
        e.preventDefault();
        diToiMuc(dsHien[iChon]);
        o.value = '';
        dong();
      } else if (e.key === 'Escape') {
        o.value = '';
        dong();
      }
    });
    o.addEventListener('blur', function () { setTimeout(dong, 140); });

    // Gõ "/" ở bất cứ đâu là nhảy vào ô tìm — trừ khi đang gõ trong một ô nhập
    // khác, vì lúc đó "/" là ký tự người dùng muốn nhập thật.
    document.addEventListener('keydown', function (e) {
      if (e.key !== '/' || e.ctrlKey || e.altKey || e.metaKey) return;
      const dang = document.activeElement;
      const the = dang && dang.tagName;
      if (the === 'INPUT' || the === 'TEXTAREA' || the === 'SELECT'
        || (dang && dang.isContentEditable)) return;
      e.preventDefault();
      o.focus();
    });
  }

  /* ------------------------------- Móc nối ------------------------------- */

  function ganNutSoDoAZ() {
    const b = document.getElementById('nut-so-do-az');
    if (!b) return;
    b.addEventListener('click', function () {
      window.switchView('dashboard', 'sec-so-do-tong-quan');
    });
  }

  /**
   * Bọc `switchView` để tầng 3 đổi theo màn. Bọc chứ không sửa trong `app.js`
   * vì `switchView` có sáu đường ra sớm (`return` khi không tìm thấy màn, khi
   * thiếu tham số…); thêm lời gọi vào giữa những nhánh đó là mời một nhánh bị
   * quên. Bọc ngoài thì chỉ chạy khi hàm gốc đã chạy xong và không trả `false`.
   */
  function bocSwitchView() {
    const goc = window.switchView;
    if (typeof goc !== 'function' || goc.daBocKhung) return;
    const boc = function (man, scrollToId) {
      const kq = goc.apply(this, arguments);
      if (kq !== false) {
        try {
          capNhatDauTrang(man);
        } catch (loi) {
          // Đầu trang sai thì màn vẫn phải mở được — không để một lỗi hiển thị
          // chặn cả việc chuyển màn.
          console.error('Không cập nhật được đầu trang:', loi);
        }
      }
      dongBangChon();
      return kq;
    };
    boc.daBocKhung = true;
    window.switchView = boc;
  }

  function dungKhung() {
    bocSwitchView();
    bocSwitchMasterDataTab();
    ganBangChon();
    ganDiChuyen();
    ganTimManHinh();
    ganNutSoDoAZ();

    // Màn nào đang mở lúc nạp thì đầu trang phải khớp ngay, chứ không đợi tới
    // lần chuyển màn đầu tiên.
    const dangMo = document.querySelector('.view-section.active');
    const man = dangMo ? dangMo.id.replace(/^view-/, '') : 'dashboard';
    capNhatDauTrang(man);
  }

  // `app.js` cũng nghe `DOMContentLoaded`; tệp này nạp sau nên trình duyệt gọi
  // hàm của nó sau, tức `switchView` đã có mặt để bọc.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', dungKhung);
  } else {
    dungKhung();
  }

  window.capNhatDauTrang = capNhatDauTrang;
  window.dongBangChon = dongBangChon;
  window.ganDiChuyenKhung = ganDiChuyen;
})();

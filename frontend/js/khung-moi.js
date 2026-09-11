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
    'os-home': ['', '', 'Trang chủ',
      'Chọn một màn trên dock hoặc lưới, hoặc gõ để đi tới màn.'],
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
    'ai-checkpoint': ['more', 'Báo cáo và khác', 'Trạm kiểm soát AI',
      'Đọc ảnh biển số và niêm phong tại chốt, đối chiếu với Trip đang chạy.'],
    'co-hoi': ['biz', 'Kinh doanh', 'Khách hàng và cơ hội',
      'Ghi nhận yêu cầu của khách trước khi có báo giá. Từ cơ hội bấm "Lập báo giá" để sinh '
      + 'báo giá nháp kế thừa khách, tuyến, hàng và sản lượng.'],
    'crm-sales': ['biz', 'Kinh doanh', 'Báo giá cước',
      'Báo giá theo tuyến và loại xe. Khách chấp nhận báo giá là tách thẳng thành '
      + 'lệnh giao hàng — không còn bước Đơn hàng ở giữa.'],
    'master-data': ['master', 'Dữ liệu gốc', 'Dữ liệu gốc',
      'Tuyến, công thức giá thành, loại xe, xe, khách hàng — nguồn mà báo giá và điều phối đọc.'],
    'lab-summary': ['more', 'Báo cáo và khác', 'Phân tích doanh thu và chi phí',
      'Giá thành, cước báo giá và lợi nhuận theo tuyến, xe và khách.'],
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
    // KHONG con nut "Tao lenh giao hang" tao ra mot DO trong.
    //
    // DO khong phai thu nguoi van hanh tu go ra: no la thu bao gia sinh ra khi
    // khach chap nhan, mang theo tuyen, gia khoa va khung gio da thoa thuan.
    // Mot form DO trong la moi nguoi dung dam ngang vao giua luong, va DO do
    // khong co bao gia nao chong lung nen buoc quyet toan khong biet lay gia
    // dau ra. Nut nay dan ve man Bao gia — dung cho de bat dau.
    'ops-planning': [['Lệnh giao hàng sinh từ báo giá →', 'primary', 'openFioriDOForm']],
    // Màn CRM KHÔNG khai nút ở đây nữa.
    //
    // Trước là "+ Đơn hàng vận chuyển". Bước Đơn hàng (SO) đã trục xuất — và
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
    'md-tab-setup': ['master', 'Dữ liệu gốc', 'Thiết lập A–Z',
      'Thứ tự khai dữ liệu gốc để chạy được trọn luồng báo giá → lệnh giao hàng → chuyến.'],
    'md-tab-drivers': ['master', 'Dữ liệu gốc', 'Tài xế và bằng lái',
      'Hạng bằng và hiệu lực của từng tài xế — cửa chặn điều phối đọc từ đây.'],
    'md-tab-currencies': ['master', 'Dữ liệu gốc', 'Tỷ giá tiền tệ',
      'VND, LAK, USD và tỷ giá tham chiếu dùng khi báo giá bằng ngoại tệ.'],
    'md-tab-account-mappings': ['master', 'Dữ liệu gốc', 'Mapping tài khoản',
      'Nối khoản mục chi phí với tài khoản kế toán của bên công nợ.'],
    'md-tab-vehicles': ['master', 'Dữ liệu gốc', 'Sắp lịch xe và tài xế',
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
      const dung = b.dataset.menu ? (b.dataset.menu === nhom)
        : (b.dataset.view === man || (b.dataset.view === 'os-home' && man === 'dashboard'));
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
    ['Sơ đồ luồng A–Z', 'Tám nhóm chức năng, từ báo giá tới hạch toán', 'dashboard', '',
     'so do luong a-z bang dieu khien dashboard tong quan tam nhom chuc nang',
     'fa-diagram-project', '#2563eb,#1e3a8a'],
    ['Lệnh giao hàng (DO)', 'Chọn DO, lập Trip', 'ops-planning', '',
     'lenh giao hang do delivery order lap ke hoach planning',
     'fa-boxes-packing', '#fb923c,#dc2626'],
    ['Giao hàng và vận chuyển', 'Trip, chặng về', 'delivery-shipment', '',
     'giao hang van chuyen trip shipment chang ve backhaul return',
     'fa-route', '#34d399,#0f766e'],
    ['Điều phối và thực thi', 'Gán xe và tổ lái', 'dispatch', '',
     'dieu phoi thuc thi dispatch gan xe to lai tai xe xuat ben',
     'fa-truck-ramp-box', '#38bdf8,#1d4ed8'],
    ['Theo dõi và kiểm soát', 'GPS, tiến độ, sự cố', 'tracking', '',
     'theo doi kiem soat tracking gps su co eta da den noi',
     'fa-location-crosshairs', '#c084fc,#7e22ce'],
    ['Hoàn tất giao hàng', 'POD, quyết toán, đóng DO', 'delivery-completion', '',
     'hoan tat giao hang pod quyet toan ky nhan closeout',
     'fa-clipboard-check', '#f472b6,#be123c'],
    ['Packing List và tem QR', 'Gói hàng, in tem', 'parking-list', '',
     'packing list tem qr goi hang in tem parking',
     'fa-qrcode', '#fbbf24,#d97706'],
    ['Trạm kiểm soát AI', 'Đọc ảnh tại chốt', 'ai-checkpoint', '',
     'tram kiem soat ai checkpoint anh bien so niem phong',
     'fa-camera-retro', '#a78bfa,#4c1d95'],
    ['Thiết lập A–Z', 'Thứ tự khai dữ liệu gốc', 'master-data', 'md-tab-setup',
     'thiet lap setup a-z khoi tao du lieu goc',
     'fa-wand-magic-sparkles', '#60a5fa,#1e40af'],
    ['Tài xế và bằng lái', 'Hạng bằng, hiệu lực', 'master-data', 'md-tab-drivers',
     'tai xe bang lai license driver hang bang',
     'fa-id-card', '#2dd4bf,#0f766e'],
    ['Tỷ giá tiền tệ', 'VND, LAK, USD', 'master-data', 'md-tab-currencies',
     'ty gia tien te currency lak usd vnd',
     'fa-coins', '#facc15,#b45309'],
    ['Mapping tài khoản', 'Khoản mục ↔ tài khoản', 'master-data', 'md-tab-account-mappings',
     'mapping tai khoan account mapping acc code',
     'fa-diagram-project', '#94a3b8,#334155'],
    ['Khách hàng và cơ hội', 'Lead, cơ hội, hồ sơ khách', 'co-hoi', '',
     'khach hang co hoi lead opportunity crm customer profile ho so khach',
     'fa-handshake', '#06b6d4,#2563eb'],
    ['Báo giá cước', 'Báo giá theo tuyến, loại xe', 'crm-sales', '',
     'crm kinh doanh khach hang bao gia cuoc quotation don hang van chuyen sales order so qt',
     'fa-file-contract', '#a855f7,#6d28d9'],
    ['Phân tích doanh thu và chi phí', 'Lợi nhuận theo tuyến, xe, khách', 'lab-summary', '',
     'phan tich doanh thu chi phi loi nhuan bao cao report analysis',
     'fa-chart-line', '#4ade80,#15803d'],
    ['Tuyến đường', 'Chặng A → B → C, km kế hoạch', 'master-data', 'md-tab-routes',
     'tuyen duong route chang km ke hoach',
     'fa-route', '#38bdf8,#0369a1'],
    ['Công thức giá thành', 'Chi phí trên 1 km và giá cước', 'master-data', 'md-tab-formulas',
     'cong thuc gia thanh cost formula chi phi km cuoc xang dau',
     'fa-calculator', '#f59e0b,#b45309'],
    ['Loại xe', 'Tải trọng, định mức dầu', 'master-data', 'md-tab-veh-types',
     'loai xe vehicle type tai trong dinh muc dau',
     'fa-truck', '#818cf8,#3730a3'],
    ['Xe và thiết bị', 'Đăng kiểm, bảo dưỡng, bãi', 'master-data', 'md-tab-vehicles',
     'xe thiet bi vehicle dang kiem bao duong bai bien so',
     'fa-calendar-days', '#22d3ee,#0e7490'],
    ['Khách hàng', 'Thông tin và điều khoản', 'master-data', 'md-tab-customers',
     'khach hang customer dieu khoan',
     'fa-building-user', '#f472b6,#9d174d'],
    ['Nhà vận chuyển', 'Đối tác chạy thuê ngoài', 'master-data', 'md-tab-carriers',
     'nha van chuyen carrier doi tac thue ngoai',
     'fa-warehouse', '#fb7185,#9f1239'],
    ['Dữ liệu gốc', 'Cả 11 thẻ, kèm bước thiết lập', 'master-data', '',
     'du lieu goc master data danh muc thiet lap',
     'fa-database', '#2563eb,#1e3a8a'],
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
      // Ô nằm trong màn chính: đang ở màn khác thì về đó trước, không thì
      // focus vào một ô đang display:none và không có gì xảy ra.
      const manChinh = document.getElementById('view-os-home');
      if (manChinh && !manChinh.classList.contains('active') && typeof window.switchView === 'function') {
        window.switchView('os-home');
      }
      o.focus();
    });
  }

  /* ------------------------------ Màn chính OS ------------------------------ */

  /**
   * Lưới "Tiện ích chức năng" vẽ từ MUC_TIM_MAN (trừ chính màn chính), nên thêm
   * một màn vào bảng đó là có luôn trong lưới và trong ô tìm. Dock 8 bước lấy
   * chấm sáng từ `window.currentWorkflowStep`, số đỏ từ hai lời gọi máy chủ.
   */
  /* ----------------------------- Dịch thuật ------------------------------ */

  /**
   * Chữ trên trang chủ do JS sinh ra nên `changeLanguage` (chạy trên các thẻ
   * `data-i18n`) không chạm tới được. `T` đọc `lang.json` qua `window.t`, và
   * TRẢ VỀ TIẾNG VIỆT nếu khoá chưa có bản dịch — `t()` trả lại chính khoá khi
   * thiếu, mà để nguyên khoá trên màn hình thì tệ hơn để tiếng Việt.
   */
  function T(khoa, macDinh) {
    if (typeof window.t !== 'function') return macDinh;
    const ra = window.t(khoa);
    return (ra && ra !== khoa) ? ra : macDinh;
  }
  // `currentLang` trong app.js khai bằng `let` ở cấp cao nhất nên KHÔNG nằm trên
  // `window` — đọc nó ở đây luôn ra undefined và ngày tháng kẹt ở tiếng Việt.
  // `changeLanguage` có đặt `<html lang>`, nên lấy mã ngôn ngữ từ đó.
  const MA_NGON_NGU = { vi: 'vi-VN', en: 'en-GB', la: 'lo-LA', lo: 'lo-LA' };
  function maVung() {
    const l = (document.documentElement && document.documentElement.lang) || 'vi';
    return MA_NGON_NGU[String(l).toLowerCase()] || 'vi-VN';
  }

  /**
   * Đổi ngôn ngữ thì vẽ lại trang chủ. Bọc `changeLanguage` thay vì sửa app.js:
   * hàm đó có nhiều đường ra sớm, và ở đây chỉ cần THÊM việc chứ không đổi việc.
   */
  function bocDoiNgonNgu() {
    const goc = window.changeLanguage;
    if (typeof goc !== 'function' || goc.daBocTrangChu) return;
    const boc = function () {
      const kq = goc.apply(this, arguments);
      try {
        if (document.body.classList.contains('epl-os-home')) { veHello(); napSoDock(); veLuoiTram(); napBanLamViec(); }
      } catch (loi) { console.error('Không vẽ lại được trang chủ sau khi đổi ngôn ngữ:', loi); }
      return kq;
    };
    boc.daBocTrangChu = true;
    window.changeLanguage = boc;
  }

  /* ------------------------- Bàn làm việc hôm nay ------------------------- */

  const goc = function () { return window.API_BASE || ''; };
  function layJson(duong) {
    return fetch(goc() + duong).then(function (r) { return r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status)); })
      .then(function (g) { return g && Object.prototype.hasOwnProperty.call(g, 'data') ? g.data : g; });
  }
  function danhSach(g) { return Array.isArray(g) ? g : (g && Array.isArray(g.items) ? g.items : []); }
  const cuoiNgay = function () { const d = new Date(); d.setHours(23, 59, 59, 999); return d.getTime(); };
  function gioNgay(iso) {
    const d = new Date(iso); if (isNaN(d)) return '';
    const homNay = new Date().toDateString() === d.toDateString();
    return homNay ? d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }) : d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
  }

  /** Mở đúng bản ghi ở màn của nó; màn nạp dữ liệu xong mới mở hộp. */
  function moBanGhi(loai, id) {
    if (loai === 'co-hoi') {
      window.switchView('co-hoi');
      let lan = 0;
      const cho = setInterval(function () {
        const C = window.CoHoiV1; lan++;
        if (C && C._trangThai && C._trangThai.ds.some(function (x) { return x.id === id; })) { clearInterval(cho); C.moHopThoai(id); }
        else if (lan > 25) clearInterval(cho);
      }, 120);
    } else if (loai === 'bao-gia') {
      window.switchView('crm-sales', 'qtv2-root');
      setTimeout(function () { if (window.BaoGiaV2 && window.BaoGiaV2.moPhieu) window.BaoGiaV2.moPhieu(id); }, 150);
    } else if (loai === 'do') {
      window.switchView('ops-planning', 'fiori-do-list');
    } else if (loai === 'su-co') {
      window.switchView('tracking');
    }
  }

  function dongViec(v) {
    return '<button type="button" class="os-vi tone-' + v.tone + '" data-loai="' + v.loai + '" data-id="' + chuAnToan(v.id || '') + '">'
      + '<span class="ic"><i class="fa-solid ' + v.icon + '" aria-hidden="true"></i></span>'
      + '<span class="txt"><b>' + chuAnToan(v.tieuDe) + '</b><span>' + chuAnToan(v.chiTiet || '') + '</span></span>'
      + (v.nhan ? '<span class="when">' + chuAnToan(v.nhan) + '</span>' : '') + '<i class="fa-solid fa-chevron-right mui" aria-hidden="true"></i></button>';
  }

  /** Sáu trạm của dòng chảy. `khoa` là con số đo được ở napBanLamViec. */
  const TRAM = [
    { kTen: 'os_tram_cohoi', ten: 'Cơ hội', icon: 'fa-handshake', man: 'co-hoi', khoa: 'coHoi', kDon: 'os_don_dangmo', don: 'đang mở' },
    { kTen: 'os_tram_baogia', ten: 'Báo giá', icon: 'fa-file-contract', man: 'crm-sales', khoa: 'baoGia', kDon: 'os_don_dangmo', don: 'đang mở' },
    { kTen: 'os_tram_do', ten: 'Lệnh giao hàng', icon: 'fa-boxes-packing', man: 'ops-planning', khoa: 'doCho', kDon: 'os_don_chualenduong', don: 'chưa lên đường' },
    { kTen: 'os_tram_dispatch', ten: 'Điều phối', icon: 'fa-truck-ramp-box', man: 'dispatch', khoa: 'doDieuPhoi', kDon: 'os_don_choxe', don: 'chờ xe' },
    { kTen: 'os_tram_dangchay', ten: 'Đang chạy', icon: 'fa-location-crosshairs', man: 'tracking', khoa: 'doChay', kDon: 'os_don_chuyen', don: 'chuyến', suCo: true },
    { kTen: 'os_tram_hoantat', ten: 'Hoàn tất', icon: 'fa-check', man: 'delivery-completion', khoa: 'hoanTat', kDon: 'os_don_dacopod', don: 'đã có POD', cuoi: true },
  ];

  let soTramCuoi = {};
  /** Vẽ lại dòng chảy bằng SỐ ĐÃ ĐỌC lần trước — dùng khi chỉ đổi ngôn ngữ. */
  function veLuoiTram() { veLuong(soTramCuoi); }

  function veLuong(so) {
    soTramCuoi = so || {};
    const o = document.getElementById('os-luong-ds'); if (!o) return;
    const gia = TRAM.map(function (t) { const n = Number(so[t.khoa]); return isFinite(n) ? n : null; });
    // Trạm tắc: nhiều nhất trong năm trạm đầu (Hoàn tất càng nhiều càng tốt, không tính).
    let max = 0; gia.slice(0, 5).forEach(function (n) { if (n !== null && n > max) max = n; });
    const lonNhat = Math.max(1, max);
    o.innerHTML = TRAM.map(function (t, i) {
      const n = gia[i], coSo = n !== null, tac = coSo && max > 0 && n === max && !t.cuoi;
      const suCo = t.suCo && isFinite(Number(so.suCo)) && Number(so.suCo) > 0 ? Number(so.suCo) : 0;
      // Ống nối tới trạm này: dày theo số đang chuyển qua (2–12px).
      const ong = i === 0 ? '' : '<span class="os-ong" aria-hidden="true"><span style="height:' + (coSo ? Math.max(2, Math.round(2 + 10 * n / lonNhat)) : 2) + 'px"></span></span>';
      return ong + '<button type="button" role="listitem" class="os-tram' + (tac ? ' tac' : '') + (t.cuoi ? ' cuoi' : '') + (coSo && n === 0 ? ' trong' : '') + '" data-man="' + t.man + '" title="' + T(t.kTen, t.ten) + (coSo ? ': ' + n + ' ' + T(t.kDon, t.don) : '') + '">'
        + '<span class="vong"><b>' + (coSo ? n.toLocaleString('vi-VN') : '·') + '</b>'
        + (suCo ? '<span class="su-co" title="' + suCo + ' ' + T('os_suco_chuaxuly', 'sự cố chưa xử lý') + '"><i class="fa-solid fa-triangle-exclamation" aria-hidden="true"></i>' + suCo + '</span>' : '')
        + '</span>'
        + '<span class="ten"><i class="fa-solid ' + t.icon + '" aria-hidden="true"></i> ' + T(t.kTen, t.ten) + '</span>'
        + '<small>' + (coSo ? (tac ? T('os_dang_don', 'đang dồn') + ' · ' : '') + T(t.kDon, t.don) : '&nbsp;') + '</small></button>';
    }).join('');
    o.querySelectorAll('.os-tram').forEach(function (b) { b.addEventListener('click', function () { window.switchView(b.dataset.man); }); });
    const ghi = document.getElementById('os-dong-ghi');
    if (ghi && Object.keys(so).length) {
      ghi.textContent = T('os_dong_ghi', 'Số trong trạm là bản ghi đang nằm ở đó. Trạm cam là chỗ đang dồn nhiều nhất.')
        + ' ' + T('os_cap_nhat', 'Cập nhật') + ' ' + new Date().toLocaleTimeString(maVung(), { hour: '2-digit', minute: '2-digit' }) + '.';
    }
  }

  /**
   * Thẻ "Nguồn lực hôm nay" dưới dòng chảy: xe/người đang ở đâu, và giấy tờ nào sắp chặn.
   *
   * Hai dòng cảnh báo đọc thẳng số của `GET /api/fleet/resource-summary`, và máy chủ đếm
   * bằng ĐÚNG luật của hai cửa gác điều phối. Nên nhãn ở đây phải nói thật là nó chặn:
   * "hết hạn" gồm cả trường hợp CHƯA KHAI ngày, vì cửa gác coi thiếu ngày là hết hạn.
   * Viết "sắp hết hạn" cho một chiếc đang bị chặn là đẩy người điều độ vào lỗi 409.
   */
  function veNguonLuc(d, loi) {
    const o = document.getElementById('os-nl'); if (!o) return;
    if (!d) {
      o.innerHTML = '<div class="os-rong nho">' + T('os_nl_chua_doc', 'Chưa đọc được nguồn lực đội xe') + (loi ? ' (' + chuAnToan(loi) + ')' : '') + '.</div>';
      o.hidden = false; return;
    }
    const xe = d.vehicles || {}, tx = d.drivers || {}, ngay = Number(d.warn_within_days) || 30;
    const so = function (n) { const v = Number(n); return isFinite(v) ? v.toLocaleString(maVung()) : '·'; };
    const o1 = function (nhan, n, lop) {
      return '<span class="nl-o' + (lop ? ' ' + lop : '') + (Number(n) ? '' : ' trong') + '"><b>' + so(n) + '</b>' + nhan + '</span>';
    };
    // Một dòng cảnh báo: đỏ nếu đang chặn, cam nếu sắp, xanh nếu sạch.
    const canh = function (chan, sap, dsSap, tenChan, tenSap, tenSach, tab) {
      let lop = 'ok', chu = tenSach, phu = '';
      if (Number(chan) > 0) { lop = 'chan'; chu = so(chan) + tenChan; phu = T('os_nl_se_bi_chan', 'Điều phối sẽ bị chặn ở những xe/người này.'); }
      else if (Number(sap) > 0) {
        lop = 'sap'; chu = so(sap) + tenSap + ' ' + T('os_nl_trong', 'trong') + ' ' + ngay + ' ' + T('os_ngay', 'ngày');
        phu = (dsSap || []).slice(0, 3).map(function (x) {
          return (x.name ? x.name : x.id) + ' ' + T('os_con_ngay', 'còn') + ' ' + x.con_ngay + ' ' + T('os_ngay', 'ngày');
        }).join(' · ');
      }
      return '<button type="button" class="nl-canh ' + lop + '" data-tab="' + tab + '">'
        + '<i class="fa-solid ' + (lop === 'ok' ? 'fa-circle-check' : lop === 'sap' ? 'fa-triangle-exclamation' : 'fa-ban') + '" aria-hidden="true"></i>'
        + '<span><b>' + chuAnToan(chu) + '</b>' + (phu ? '<small>' + chuAnToan(phu) + '</small>' : '') + '</span>'
        + '<i class="fa-solid fa-chevron-right mui" aria-hidden="true"></i></button>';
    };
    o.innerHTML = '<div class="nl-dau"><h3><i class="fa-solid fa-truck-front" aria-hidden="true"></i> ' + T('os_nl_h', 'Nguồn lực hôm nay') + '</h3>'
      + '<span>' + so(xe.tong) + ' ' + T('os_nl_xe', 'xe') + ' · ' + so(tx.tong) + ' ' + T('os_nl_taixe', 'tài xế') + '</span></div>'
      + '<div class="nl-hang">' + o1(' ' + T('os_nl_xe_ranh', 'xe rảnh'), xe.ranh, 'xanh') + o1(' ' + T('os_nl_xe_dang_chay', 'xe đang chạy'), xe.dang_chay)
      + o1(' ' + T('os_nl_nam_xuong', 'nằm xưởng'), xe.bao_duong) + (Number(xe.ngung_chay) ? o1(' ' + T('os_nl_ngung_chay', 'ngừng chạy'), xe.ngung_chay) : '')
      + o1(' ' + T('os_nl_tx_ranh', 'tài xế rảnh'), tx.ranh, 'xanh') + '</div>'
      + canh(xe.giay_to_het_han, xe.giay_to_sap_het, d.vehicles_expiring_soon,
             ' ' + T('os_nl_xe_het_giay', 'xe thiếu / hết hạn giấy tờ'), ' ' + T('os_nl_xe_sap_giay', 'xe sắp hết hạn giấy tờ'),
             T('os_nl_giay_con_han', 'Giấy tờ xe còn hạn cả đội'), 'md-tab-vehicles')
      + canh(tx.bang_het_han, tx.bang_sap_het, d.drivers_expiring_soon,
             ' ' + T('os_nl_tx_het_bang', 'tài xế thiếu / hết hạn bằng lái'), ' ' + T('os_nl_tx_sap_bang', 'tài xế sắp hết hạn bằng lái'),
             T('os_nl_bang_con_han', 'Bằng lái còn hạn cả đội'), 'md-tab-drivers')
      + (loi ? '<div class="os-rong nho">' + T('os_chua_doc_duoc', 'Chưa đọc được') + ': ' + chuAnToan(loi) + '.</div>' : '');
    o.hidden = false;
    o.querySelectorAll('.nl-canh').forEach(function (b) {
      b.addEventListener('click', function () {
        if (typeof window.openMasterSetupStep === 'function') window.openMasterSetupStep(b.dataset.tab);
        else window.switchView('master-data');
      });
    });
  }

  function veViec(ds, loi) {
    const o = document.getElementById('os-viec-ds'), dem = document.getElementById('os-viec-dem');
    if (!o) return;
    if (!ds.length) {
      o.innerHTML = '<div class="os-rong ok"><i class="fa-solid fa-circle-check" aria-hidden="true"></i> ' + T('os_khong_viec_gap', 'Không có việc gấp — mọi thứ đang đúng hạn.')
        + (loi.length ? '<br><small>' + T('os_chua_doc_duoc', 'Chưa đọc được') + ': ' + chuAnToan(loi.join(', ')) + '.</small>' : '') + '</div>';
      if (dem) dem.textContent = '';
    } else {
      o.innerHTML = ds.map(dongViec).join('') + (loi.length ? '<div class="os-rong nho">' + T('os_chua_doc_duoc', 'Chưa đọc được') + ': ' + chuAnToan(loi.join(', ')) + '.</div>' : '');
      if (dem) dem.textContent = ds.length + ' ' + T('os_dem_viec', 'việc');
      o.querySelectorAll('.os-vi').forEach(function (b) { b.addEventListener('click', function () { moBanGhi(b.dataset.loai, b.dataset.id); }); });
    }
  }

  /** Đọc bốn nguồn, mỗi nguồn hỏng riêng thì nói riêng — không để một lỗi làm trống cả bàn. */
  function napBanLamViec() {
    if (!document.getElementById('os-ban') || typeof fetch !== 'function') return;
    const viec = [], loi = [], so = {};
    const D = window.DoBoard;
    let nguonLuc = null, loiNguonLuc = '';
    const xong = function () { veViec(viec.slice(0, 12), loi); veLuong(so); veNguonLuc(nguonLuc, loiNguonLuc); };
    Promise.all([
      layJson('/api/crm/opportunities').then(function (g) {
        const ds = danhSach(g), moc = cuoiNgay();
        so.coHoi = ds.filter(function (x) { return !['won', 'lost'].includes(x.stage); }).length;
        ds.filter(function (x) { return x.next_action_at && !['won', 'lost'].includes(x.stage) && new Date(x.next_action_at).getTime() <= moc; })
          .sort(function (a, b) { return new Date(a.next_action_at) - new Date(b.next_action_at); })
          .forEach(function (x) {
            const tre = new Date(x.next_action_at).getTime() < Date.now();
            viec.push({ loai: 'co-hoi', id: x.id, tone: tre ? 'do' : 'cam', icon: 'fa-phone', tieuDe: (tre ? T('os_tre_hen', 'Trễ hẹn liên hệ') : T('os_hen_lien_he', 'Hẹn liên hệ')) + ' · ' + (x.customer_name || x.id),
              chiTiet: [x.route_name, x.cargo_type].filter(Boolean).join(' · ') || x.id, nhan: gioNgay(x.next_action_at) });
          });
      }).catch(function () { loi.push(T('os_nguon_cohoi', 'cơ hội')); }),
      layJson('/api/quotations/board?status=all').then(function (g) {
        const ds = danhSach(g);
        so.baoGia = ds.filter(function (q) { return ['draft', 'pending_approval', 'approved', 'sent'].includes(q.canonical_status); }).length;
        ds.filter(function (q) { return q.canonical_status === 'expired' || (q.canonical_status === 'sent' && isFinite(Number(q.con_lai_ngay)) && Number(q.con_lai_ngay) <= 3); })
          .forEach(function (q) {
            const het = q.canonical_status === 'expired';
            viec.push({ loai: 'bao-gia', id: q.id, tone: het ? 'do' : 'cam', icon: 'fa-file-contract', tieuDe: (het ? T('os_bg_het_han', 'Báo giá hết hạn') : T('os_bg_sap_het', 'Báo giá sắp hết hạn')) + ' · ' + (q.quote_no || q.id),
              chiTiet: [q.customer_name || q.customer_id, q.origin && q.destination ? q.origin + ' → ' + q.destination : ''].filter(Boolean).join(' · '),
              nhan: het ? T('os_gia_han_dong', 'gia hạn / đóng') : T('os_con_ngay', 'còn') + ' ' + q.con_lai_ngay + ' ' + T('os_ngay', 'ngày') });
          });
        ds.filter(function (q) { return q.canonical_status === 'pending_approval'; }).forEach(function (q) {
          viec.push({ loai: 'bao-gia', id: q.id, tone: 'vang', icon: 'fa-stamp', tieuDe: T('os_cho_duyet', 'Chờ duyệt nội bộ') + ' · ' + (q.quote_no || q.id),
            chiTiet: (q.customer_name || q.customer_id || '') + (q.bien != null ? ' · ' + T('os_bien', 'biên') + ' ' + q.bien + '%' : ''), nhan: T('os_duyet', 'duyệt') });
        });
      }).catch(function () { loi.push(T('os_nguon_baogia', 'báo giá')); }),
      layJson('/api/delivery-orders?page_size=200').then(function (g) {
        const ds = danhSach(g);
        if (!D) return;
        const dem = D.counts(ds);
        so.doCho = dem.overdue + dem.near_late + dem.pending + dem.undated;
        so.doDieuPhoi = dem.pending + dem.near_late + dem.overdue;
        so.doChay = dem.active; so.hoanTat = dem.completed;
        D.sortWithin(D.filter(ds, 'overdue'), 'overdue').slice(0, 5).forEach(function (o) {
          viec.push({ loai: 'do', id: o.id, tone: 'do', icon: 'fa-clock-rotate-left', tieuDe: T('os_do_qua_han', 'DO quá hạn giao') + ' · ' + o.id,
            chiTiet: (o.customer_name || o.customer_id || '') + (o.route_name ? ' · ' + o.route_name : ''), nhan: T('os_qua', 'quá') + ' ' + D.daysLate(o) + ' ' + T('os_ngay', 'ngày') });
        });
        D.sortWithin(D.filter(ds, 'near_late'), 'near_late').slice(0, 5).forEach(function (o) {
          viec.push({ loai: 'do', id: o.id, tone: 'cam', icon: 'fa-hourglass-half', tieuDe: T('os_do_toi_han', 'DO tới hạn trong 24 giờ') + ' · ' + o.id,
            chiTiet: (o.customer_name || o.customer_id || '') + (o.route_name ? ' · ' + o.route_name : ''), nhan: T('os_dieu_phoi_xe', 'điều phối xe') });
        });
        if (dem.undated) viec.push({ loai: 'do', id: '', tone: 'vang', icon: 'fa-calendar-xmark', tieuDe: dem.undated + ' ' + T('os_do_thieu_han', 'DO thiếu hạn giao'),
          chiTiet: T('os_thieu_han_giai', 'Chưa có ngày lấy/giao nên chưa lập kế hoạch được'), nhan: T('os_bo_sung', 'bổ sung') });
      }).catch(function () { loi.push(T('os_nguon_do', 'lệnh giao hàng')); }),
      layJson('/api/incidents').then(function (g) {
        const ds = danhSach(g).filter(function (i) { return !['Resolved', 'Closed', 'resolved', 'closed', 'Đã xử lý'].includes(String(i.status || '')); });
        so.suCo = ds.length;
        ds.slice(0, 5).forEach(function (i) {
          viec.push({ loai: 'su-co', id: String(i.id), tone: 'do', icon: 'fa-triangle-exclamation', tieuDe: T('os_su_co', 'Sự cố') + ' · ' + (i.incident_type || T('os_chua_ro_loai', 'chưa rõ loại')) + (i.do_id ? ' · ' + i.do_id : ''), chiTiet: [i.vehicle_id, i.location].filter(Boolean).join(' · ') || (i.description || '').slice(0, 60), nhan: i.severity || '' });
        });
      }).catch(function () { loi.push(T('os_nguon_suco', 'sự cố')); }),
      // Nguồn lực: máy chủ đếm sẵn. Hỏng riêng thì thẻ đó nói riêng, không làm trống cả bàn.
      layJson('/api/fleet/resource-summary').then(function (g) { nguonLuc = g; })
        .catch(function (e) { loiNguonLuc = String((e && e.message) || e); }),
    ]).then(function () {
      const thuTu = { do: 0, cam: 1, vang: 2 };
      viec.sort(function (a, b) { return (thuTu[a.tone] || 0) - (thuTu[b.tone] || 0); });
      xong();
    });
  }

  function veManChinh() {
    const dock = document.getElementById('os-dock');
    if (dock) {
      dock.querySelectorAll('.os-app').forEach(function (b) {
        b.addEventListener('click', function () {
          if (b.dataset.cuon) window.switchView(b.dataset.man, b.dataset.cuon); else window.switchView(b.dataset.man);
        });
      });
    }
    const soDo = document.getElementById('os-xem-so-do');
    if (soDo) soDo.addEventListener('click', function () { window.switchView('dashboard', 'sec-so-do-tong-quan'); });
    veLuong({});
    ganCuonDock();
    veHello();
  }

  /** Dock thu thành thanh mỏng khi cuộn xuống (như mẫu) — nghe cả khung cuộn lẫn window. */
  function ganCuonDock() {
    const man = document.getElementById('view-os-home'); if (!man) return;
    const khung = [document.querySelector('.content-body'), document.querySelector('.samsung-main-wrapper'), window];
    let daThu = false;
    const xuLy = function () {
      const y = Math.max.apply(null, khung.map(function (k) { return k ? (k === window ? window.scrollY : k.scrollTop) || 0 : 0; }));
      if (!daThu && y > 100) { man.classList.add('scrolled'); daThu = true; }
      else if (daThu && y < 20) { man.classList.remove('scrolled'); daThu = false; }
    };
    khung.forEach(function (k) { if (k) k.addEventListener('scroll', xuLy, { passive: true }); });
  }

  /** Dải "hôm nay": chào theo giờ + ngày; các con số ghi khi máy chủ trả về. */
  function veHello() {
    const o = document.getElementById('os-hello'); if (!o) return;
    const gio = new Date().getHours();
    const chao = gio < 11 ? T('os_chao_sang', 'Chào buổi sáng') : gio < 14 ? T('os_chao_trua', 'Chào buổi trưa')
      : gio < 18 ? T('os_chao_chieu', 'Chào buổi chiều') : T('os_chao_toi', 'Chào buổi tối');
    const ngay = new Date().toLocaleDateString(maVung(), { weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric' });
    o.innerHTML = '<div class="os-hello-chao"><b>' + chao + '</b><span>' + chuAnToan(ngay) + '</span></div>'
      + '<div class="os-hello-so" id="os-hello-so"></div>'
      + '<button type="button" class="os-vao" id="os-vao-trang-chinh"><i class="fa-solid fa-gauge-high" aria-hidden="true"></i> ' + T('os_vao_trang_chinh', 'Vào trang chính') + ' <span aria-hidden="true">→</span></button>';
    o.hidden = false;
    document.getElementById('os-vao-trang-chinh').addEventListener('click', function () { window.switchView('dashboard'); });
  }
  function ghiSoHello(ds) {
    const o = document.getElementById('os-hello-so'); if (!o) return;
    const co = ds.filter(function (x) { return isFinite(Number(x.so)); });
    o.innerHTML = co.map(function (x) {
      return '<button type="button" class="os-so' + (Number(x.so) > 0 && x.nong ? ' nong' : '') + '" data-man="' + x.man + '">'
        + '<b>' + Number(x.so).toLocaleString('vi-VN') + '</b><span>' + chuAnToan(x.nhan) + '</span></button>';
    }).join('');
    o.querySelectorAll('.os-so').forEach(function (b) { b.addEventListener('click', function () { window.switchView(b.dataset.man); }); });
  }

  /** Chấm sáng dưới dock: màn vừa mở gần nhất (trả lời "anh vừa ở đâu"). */
  let manDockCuoi = null;
  function sangBuocDock() {
    const dock = document.getElementById('os-dock');
    if (!dock) return;
    dock.querySelectorAll('.os-app').forEach(function (b) {
      b.classList.toggle('is-active', !!manDockCuoi && b.dataset.man === manDockCuoi);
    });
  }

  /**
   * Ngăn tùy chỉnh hình nền — như bản mẫu. Ảnh chọn được nhớ trong localStorage
   * của trình duyệt này (khóa epl_os_bg); thư viện lấy từ picsum.photos, mạng
   * không tới được thì nói rõ chứ không để ô trống.
   */
  const KHOA_NEN = 'epl_os_bg';
  function apNen(url) {
    const man = document.getElementById('view-os-home');
    if (!man) return;
    // Có ảnh: ảnh đè lên cảnh cảng vẽ CSS (.os-scene ẩn đi). Không: trả lại cảnh.
    man.classList.toggle('co-anh', !!url);
    man.style.backgroundImage = url ? 'url("' + url.replace(/"/g, '%22') + '")' : '';
  }
  function nhoNen(url) {
    try { if (url) localStorage.setItem(KHOA_NEN, url); else localStorage.removeItem(KHOA_NEN); }
    catch (e) { console.warn('Ảnh quá lớn để nhớ trong trình duyệt; chỉ áp cho lần này.'); }
  }
  function ganNganNen() {
    const fab = document.getElementById('os-fab'), ngan = document.getElementById('os-drawer'),
      nen = document.getElementById('os-drawer-backdrop');
    if (!fab || !ngan || !nen) return;
    try { const cu = localStorage.getItem(KHOA_NEN); if (cu) apNen(cu); } catch (e) { /* bỏ qua */ }
    const moDong = function (mo) {
      ngan.classList.toggle('open', mo); nen.classList.toggle('show', mo);
      ngan.setAttribute('aria-hidden', String(!mo));
      if (mo && !document.getElementById('os-gallery').children.length) napThuVien();
    };
    fab.addEventListener('click', function () { moDong(!ngan.classList.contains('open')); });
    nen.addEventListener('click', function () { moDong(false); });
    document.getElementById('os-drawer-x').addEventListener('click', function () { moDong(false); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && ngan.classList.contains('open')) moDong(false); });
    document.getElementById('os-bg-file').addEventListener('change', function (e) {
      const f = e.target.files && e.target.files[0]; if (!f) return;
      const r = new FileReader();
      r.onload = function (ev) { apNen(ev.target.result); nhoNen(ev.target.result); boChonThuVien(); };
      r.readAsDataURL(f);
    });
    document.getElementById('os-bg-url-ok').addEventListener('click', function () {
      const o = document.getElementById('os-bg-url'), url = o.value.trim();
      if (!url) return;
      apNen(url); nhoNen(url); boChonThuVien(); o.value = '';
    });
    document.getElementById('os-bg-reset').addEventListener('click', function () { apNen(''); nhoNen(''); boChonThuVien(); });
  }
  function boChonThuVien() {
    document.querySelectorAll('#os-gallery .bg').forEach(function (b) { b.classList.remove('active'); });
  }
  function napThuVien() {
    const g = document.getElementById('os-gallery'); if (!g || typeof fetch !== 'function') return;
    g.innerHTML = '<div class="rong"><i class="fa-solid fa-circle-notch fa-spin" aria-hidden="true"></i> Đang tải kho ảnh…</div>';
    let hienTai = ''; try { hienTai = localStorage.getItem(KHOA_NEN) || ''; } catch (e) { /* bỏ qua */ }
    const trang = Math.floor(Math.random() * 10) + 1;
    fetch('https://picsum.photos/v2/list?page=' + trang + '&limit=10').then(function (r) { return r.json(); }).then(function (ds) {
      g.innerHTML = ds.map(function (a) {
        const lon = 'https://picsum.photos/id/' + a.id + '/1920/1080', nho = 'https://picsum.photos/id/' + a.id + '/300/150';
        return '<button type="button" class="bg' + (hienTai === lon ? ' active' : '') + '" data-url="' + lon + '" title="Ảnh: ' + chuAnToan(a.author || '') + '"><img src="' + nho + '" alt="" loading="lazy"></button>';
      }).join('');
      g.querySelectorAll('.bg').forEach(function (b) {
        b.addEventListener('click', function () { apNen(b.dataset.url); nhoNen(b.dataset.url); boChonThuVien(); b.classList.add('active'); });
      });
    }).catch(function () {
      g.innerHTML = '<div class="rong"><i class="fa-solid fa-triangle-exclamation" aria-hidden="true"></i> Không tới được kho ảnh (mạng). Dùng "Tải lên từ máy tính" hoặc dán URL bên dưới.</div>';
    });
  }

  /** Số đỏ trên dock: chỉ đặt ở bước có con số thật tương ứng. */
  function napSoDock() {
    const dock = document.getElementById('os-dock');
    if (!dock || typeof fetch !== 'function') return;
    const goc = window.API_BASE || '';
    const dat = function (buoc, so) {
      const o = dock.querySelector('.os-app[data-step="' + buoc + '"] .os-badge');
      if (!o) return;
      const n = Number(so);
      if (!isFinite(n) || n <= 0) { o.hidden = true; return; }
      o.textContent = n > 99 ? '99+' : String(n);
      o.hidden = false;
    };
    const so = {};
    const ve = function () {
      ghiSoHello([
        { so: so.doOpen, nhan: T('os_so_do', 'lệnh giao hàng'), man: 'ops-planning' },
        { so: so.transit, nhan: T('os_so_chuyen', 'chuyến đang đi'), man: 'tracking' },
        { so: so.dueCrm, nhan: T('os_so_cohoi', 'cơ hội cần liên hệ hôm nay'), man: 'co-hoi', nong: true },
        { so: so.incidents, nhan: T('os_so_suco', 'sự cố phát sinh'), man: 'tracking', nong: true },
        // HỒ SƠ SẴN SÀNG BÀN GIAO — con số cuối của luồng, và là thứ bên công nợ chờ.
        // Khác với "đã có POD": một DO đã giao xong mà chuyến chở nó còn mở (xe chưa về,
        // chưa xác nhận) thì CHƯA xuất hiện ở API bàn giao, nên chưa lấy được. Đúng bộ lọc
        // của `GET /api/handover/delivery-orders`, không đếm lại bằng luật riêng ở đây.
        { so: so.banGiao, nhan: 'hồ sơ sẵn sàng bàn giao', man: 'delivery-completion' },
      ]);
    };
    fetch(goc + '/api/crm/opportunities/summary').then(function (r) { return r.ok ? r.json() : null; })
      .then(function (g) { const d = g && (g.data || g); if (d) { dat(1, d.open); so.dueCrm = d.due_follow_up; ve(); } }).catch(function () {});
    fetch(goc + '/api/handover/delivery-orders?page_size=1').then(function (r) { return r.ok ? r.json() : null; })
      .then(function (g) { const d = g && (g.data || g); if (d && isFinite(Number(d.total))) { so.banGiao = Number(d.total); ve(); } }).catch(function () {});
    fetch(goc + '/api/dashboard/stats').then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { if (d) { dat(6, d.in_transit_orders); dat(3, d.pending_deliveries); so.doOpen = d.total_deliveries; so.transit = d.in_transit_orders; so.incidents = d.incidents_count; ve(); } }).catch(function () {});
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
  /* ==================================================================
     QUAY LẠI — lịch sử trình duyệt cho toàn ứng dụng.

     VẤN ĐỀ ĐÃ ĐO (12/09/2026). Ứng dụng có 10 màn và KHÔNG một dòng
     `pushState`/`popstate` nào, nên trình duyệt coi cả ứng dụng là MỘT
     trang: bấm nút Back (hoặc vuốt lùi trên điện thoại, hoặc phím
     Alt+←) là THOÁT HẲN khỏi ứng dụng, không phải lùi một màn. Chủ dự
     án nói đúng: *"ấn vào tính năng gì đó không có nút quay về"*. Trước
     đây chỉ có hai màn chắp tay một nút "Quay lại Dashboard", tám màn
     còn lại không có đường lùi nào ngoài việc đi lại từ thanh menu.

     Sửa ở ĐÚNG MỘT CHỖ: mọi lần đổi màn đều đi qua `switchView`, nên
     gắn lịch sử vào đây thì cả mười màn được hưởng, kể cả màn thêm sau
     này — thay vì đi dán một cái nút vào từng màn rồi quên mất vài màn.

     Ba việc:
       · đổi màn → đẩy một mốc vào lịch sử trình duyệt (kèm `#mã-màn`,
         nên tải lại trang vẫn ở đúng màn đang xem);
       · người dùng bấm Back → `popstate` mở lại màn trước;
       · một nút "Quay lại" hiện trên đầu trang cho người không nghĩ tới
         nút Back của trình duyệt.
     ================================================================== */
  let manHienTai = '';
  let soBuocDaDay = 0;      // số mốc ứng dụng tự đẩy — biết còn chỗ nào để lùi không
  let dangLuiLai = false;   // đang xử lý popstate: KHÔNG đẩy tiếp, nếu không sẽ lùi mãi không ra

  function veNutQuayLai() {
    const oSub = document.getElementById('epl-sub');
    if (!oSub) return;
    let b = document.getElementById('epl-quay-lai');
    if (!b) {
      b = document.createElement('button');
      b.type = 'button';
      b.id = 'epl-quay-lai';
      b.className = 'epl-quay-lai';
      b.title = 'Quay lại màn trước (hoặc bấm nút Back của trình duyệt)';
      b.innerHTML = '<i class="fa-solid fa-arrow-left" aria-hidden="true"></i>'
        + '<span>' + (typeof T === 'function' ? T('btn_back', 'Quay lại') : 'Quay lại') + '</span>';
      b.addEventListener('click', function () { window.history.back(); });
      oSub.insertBefore(b, oSub.firstChild);
    }
    // Ẩn khi chưa đi đâu cả: một nút quay lại không lùi được là một nút nói dối.
    b.hidden = soBuocDaDay <= 0;
  }

  function ganLichSuMan() {
    if (typeof window.history !== 'object' || !window.history.pushState) return;
    window.addEventListener('popstate', function (su) {
      const man = (su.state && su.state.eplMan)
        || (String(location.hash || '').replace(/^#/, '') || '');
      if (!man || typeof window.switchView !== 'function') return;
      dangLuiLai = true;
      try {
        window.switchView(man, (su.state && su.state.eplScroll) || undefined);
      } finally {
        dangLuiLai = false;
      }
      soBuocDaDay = Math.max(0, soBuocDaDay - 1);
      veNutQuayLai();
    });
  }

  /** Mở màn ghi trong địa chỉ (`#ops-planning`) khi vừa tải trang — để F5 không văng về đầu. */
  function moManTheoDiaChi() {
    const man = String(location.hash || '').replace(/^#/, '').trim();
    if (!man || typeof window.switchView !== 'function') return;
    if (!document.getElementById('view-' + man)) return;
    dangLuiLai = true;                 // đang khôi phục, không phải người dùng đi tới
    try { window.switchView(man); } finally { dangLuiLai = false; }
  }

  function bocSwitchView() {
    const goc = window.switchView;
    if (typeof goc !== 'function' || goc.daBocKhung) return;
    const boc = function (man, scrollToId) {
      const kq = goc.apply(this, arguments);
      if (kq !== false) {
        document.body.classList.toggle('epl-os-home', man === 'os-home');
        if (man === 'os-home') { sangBuocDock(); napSoDock(); napBanLamViec(); } else { manDockCuoi = man; }
        try {
          capNhatDauTrang(man);
        } catch (loi) {
          // Đầu trang sai thì màn vẫn phải mở được — không để một lỗi hiển thị
          // chặn cả việc chuyển màn.
          console.error('Không cập nhật được đầu trang:', loi);
        }
        try {
          ghiLichSu(man, scrollToId);
        } catch (loi) {
          // Lịch sử hỏng thì vẫn phải đổi màn được.
          console.error('Không ghi được lịch sử màn:', loi);
        }
      }
      dongBangChon();
      return kq;
    };
    boc.daBocKhung = true;
    window.switchView = boc;
  }

  /** Ghi một mốc lịch sử cho màn vừa mở. Mở lại chính màn đang xem thì KHÔNG ghi —
   *  nếu không, bấm hai lần vào một mục menu là phải bấm Back hai lần mới ra. */
  function ghiLichSu(man, scrollToId) {
    if (!window.history || !window.history.pushState || man === manHienTai) return;
    const trangThai = { eplMan: man, eplScroll: scrollToId || null };
    if (dangLuiLai || !manHienTai) {
      // Lần đầu, hoặc đang lùi: thay mốc hiện tại, không tạo mốc mới.
      history.replaceState(trangThai, '', '#' + man);
    } else {
      history.pushState(trangThai, '', '#' + man);
      soBuocDaDay += 1;
    }
    manHienTai = man;
    veNutQuayLai();
  }

  function dungKhung() {
    bocSwitchView();
    ganLichSuMan();
    moManTheoDiaChi();
    bocSwitchMasterDataTab();
    ganBangChon();
    ganDiChuyen();
    ganTimManHinh();
    ganNutSoDoAZ();

    // Màn nào đang mở lúc nạp thì đầu trang phải khớp ngay, chứ không đợi tới
    // lần chuyển màn đầu tiên.
    const dangMo = document.querySelector('.view-section.active');
    const man = dangMo ? dangMo.id.replace(/^view-/, '') : 'os-home';
    capNhatDauTrang(man);
    document.body.classList.toggle('epl-os-home', man === 'os-home');
    veManChinh();
    ganNganNen();
    bocDoiNgonNgu();
    if (man === 'os-home') { napSoDock(); napBanLamViec(); }
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

/* ==========================================================================
   Nút đổi ngôn ngữ — theo mẫu nhap_UI__duan/language-switcher.html.
   Chỉ lo mở/đóng, phím mũi tên và đồng bộ cờ + mã trên nút. Việc dịch giao
   diện vẫn là changeLanguage() của app.js — ở đây chỉ gọi nó với mã đã chọn.
   ========================================================================== */
(function () {
  // Có thể có NHIỀU nút cùng lúc (header và trang chủ); tất cả dùng chung một
  // trạng thái và đổi cùng nhau, để bấm ở chỗ này thì chỗ kia không hiện cờ cũ.
  const cacNut = Array.from(document.querySelectorAll('.epl-lang')).map(function (root) {
    const btn = root.querySelector('.epl-lang-btn'), menu = root.querySelector('.epl-lang-menu');
    if (!btn || !menu) return null;
    return { root: root, btn: btn, menu: menu, items: Array.from(menu.querySelectorAll('.epl-lang-item')) };
  }).filter(Boolean);
  if (!cacNut.length) return;

  function hienThi(code) {
    cacNut.forEach(function (n) {
      const it = n.items.find(function (i) { return i.dataset.code === code; }) || n.items[0];
      n.items.forEach(function (i) { i.setAttribute('aria-selected', String(i === it)); });
      n.btn.querySelector('.cur').textContent = it.dataset.short;
      n.btn.querySelector('.flag use').setAttribute('href', it.querySelector('.flag use').getAttribute('href'));
      n.root.dataset.lang = it.dataset.code;
    });
  }
  function chon(code) {
    hienThi(code);
    if (typeof window.changeLanguage === 'function') window.changeLanguage(code);
  }

  cacNut.forEach(function (n) {
    const dangMo = function () { return n.root.classList.contains('open'); };
    const moDong = function (mo) {
      n.root.classList.toggle('open', mo);
      n.btn.setAttribute('aria-expanded', String(mo));
      if (mo) (n.items.find(function (i) { return i.getAttribute('aria-selected') === 'true'; }) || n.items[0]).focus();
    };
    n.btn.addEventListener('click', function () { moDong(!dangMo()); });
    n.items.forEach(function (it) { it.addEventListener('click', function () { chon(it.dataset.code); moDong(false); n.btn.focus(); }); });
    document.addEventListener('click', function (e) { if (!n.root.contains(e.target)) moDong(false); });
    n.root.addEventListener('keydown', function (e) {
      const i = n.items.indexOf(document.activeElement);
      if (e.key === 'Escape') { moDong(false); n.btn.focus(); }
      if (e.key === 'ArrowDown') { e.preventDefault(); dangMo() ? n.items[(i + 1) % n.items.length].focus() : moDong(true); }
      if (e.key === 'ArrowUp') { e.preventDefault(); if (dangMo()) n.items[(i - 1 + n.items.length) % n.items.length].focus(); }
    });
  });
})();

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
  const TEN_NHOM = { ops: 'Vận hành', biz: 'Kinh doanh', master: 'Dữ liệu gốc', more: 'Báo cáo và khác' };
  const THU_TU_NHOM = ['ops', 'biz', 'master', 'more'];
  let nhomDangLoc = null;

  /** Nhóm điều hướng của một dòng MUC_TIM_MAN — lấy từ bảng đầu trang, không khai lại. */
  function nhomCua(m) {
    const d = DAU_TRANG_THEO_MAN[m[2]];
    const n = d && d[0];
    return n || 'more'; // Sơ đồ luồng A–Z nằm ở "Báo cáo và khác" trên thanh điều hướng
  }
  /** Bỏ thẻ bao trùm "Dữ liệu gốc — cả 11 thẻ": 11 thẻ con đã nằm ngay đó. */
  const DS_THE = MUC_TIM_MAN.filter(function (m) { return m[2] !== 'os-home' && !(m[2] === 'master-data' && !m[3]); });

  function veLuoi() {
    const luoi = document.getElementById('os-tiles');
    if (!luoi) return;
    const nhomHien = nhomDangLoc ? [nhomDangLoc] : THU_TU_NHOM;
    luoi.innerHTML = nhomHien.map(function (nhom) {
      const ds = DS_THE.filter(function (m) { return nhomCua(m) === nhom; });
      if (!ds.length) return '';
      return '<h3 class="os-nhom"><span>' + chuAnToan(TEN_NHOM[nhom]) + '</span><small>' + ds.length + ' màn</small></h3>'
        + '<div class="os-tiles-nhom">' + ds.map(function (m) {
          const i = DS_THE.indexOf(m);
          return '<button type="button" class="os-tile" data-i="' + i + '">'
            + '<span class="os-tile-icon" style="background:linear-gradient(135deg,' + m[6] + ')"><i class="fa-solid ' + m[5] + '" aria-hidden="true"></i></span>'
            + '<span><b>' + chuAnToan(m[0]) + '</b><span>' + chuAnToan(m[1]) + '</span></span></button>';
        }).join('') + '</div>';
    }).join('');
    luoi.querySelectorAll('.os-tile').forEach(function (b) {
      b.addEventListener('click', function () { diToiMuc(DS_THE[Number(b.dataset.i)]); });
    });
    const nhan = document.getElementById('os-pill-loc');
    if (nhan) {
      nhan.hidden = !nhomDangLoc;
      nhan.textContent = nhomDangLoc ? '· ' + TEN_NHOM[nhomDangLoc] + '  ✕' : '';
    }
    sangBuocDock();
  }

  function veManChinh() {
    veLuoi();
    const pill = document.getElementById('os-pill');
    if (pill) pill.addEventListener('click', function () { nhomDangLoc = null; veLuoi(); });
    const dock = document.getElementById('os-dock');
    if (dock) {
      dock.querySelectorAll('.os-app').forEach(function (b) {
        b.addEventListener('click', function () {
          // Lần một: lọc lưới về nhóm của icon. Lần hai (đang lọc đúng nhóm này): mở màn.
          if (nhomDangLoc !== b.dataset.nhom) { nhomDangLoc = b.dataset.nhom; veLuoi(); return; }
          if (b.dataset.cuon) window.switchView(b.dataset.man, b.dataset.cuon); else window.switchView(b.dataset.man);
        });
      });
    }
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
    const chao = gio < 11 ? 'Chào buổi sáng' : gio < 14 ? 'Chào buổi trưa' : gio < 18 ? 'Chào buổi chiều' : 'Chào buổi tối';
    const ngay = new Date().toLocaleDateString('vi-VN', { weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric' });
    o.innerHTML = '<div class="os-hello-chao"><b>' + chao + '</b><span>' + chuAnToan(ngay) + '</span></div><div class="os-hello-so" id="os-hello-so"></div>';
    o.hidden = false;
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

  /** Chấm sáng dưới dock: các icon thuộc nhóm đang lọc. */
  function sangBuocDock() {
    const dock = document.getElementById('os-dock');
    if (!dock) return;
    dock.querySelectorAll('.os-app').forEach(function (b) {
      b.classList.toggle('is-active', !!nhomDangLoc && b.dataset.nhom === nhomDangLoc);
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
    man.style.backgroundImage = url
      ? 'url("' + url.replace(/"/g, '%22') + '"), linear-gradient(160deg, #0b1f3a 0%, #123a6b 45%, #0b2f6e 100%)'
      : '';
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
        { so: so.doOpen, nhan: 'lệnh giao hàng', man: 'ops-planning' },
        { so: so.transit, nhan: 'chuyến đang đi', man: 'tracking' },
        { so: so.dueCrm, nhan: 'cơ hội cần liên hệ hôm nay', man: 'co-hoi', nong: true },
        { so: so.incidents, nhan: 'sự cố phát sinh', man: 'tracking', nong: true },
      ]);
    };
    fetch(goc + '/api/crm/opportunities/summary').then(function (r) { return r.ok ? r.json() : null; })
      .then(function (g) { const d = g && (g.data || g); if (d) { dat(1, d.open); so.dueCrm = d.due_follow_up; ve(); } }).catch(function () {});
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
  function bocSwitchView() {
    const goc = window.switchView;
    if (typeof goc !== 'function' || goc.daBocKhung) return;
    const boc = function (man, scrollToId) {
      const kq = goc.apply(this, arguments);
      if (kq !== false) {
        document.body.classList.toggle('epl-os-home', man === 'os-home');
        if (man === 'os-home') { napSoDock(); }
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
    const man = dangMo ? dangMo.id.replace(/^view-/, '') : 'os-home';
    capNhatDauTrang(man);
    document.body.classList.toggle('epl-os-home', man === 'os-home');
    veManChinh();
    ganNganNen();
    if (man === 'os-home') napSoDock();
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

/* ============================================================================
   LỚP NỀN BẢN ĐỒ — có dự phòng, và tự nhớ nguồn nào chạy được.

   VẤN ĐỀ ĐÃ CÓ. Cả ba bản đồ trong ứng dụng (sơ đồ lộ trình, bản đồ GPS, tháp
   kiểm soát) đều nạp ảnh nền từ MỘT nguồn duy nhất:
   `https://{s}.tile.openstreetmap.org/...`.

   Đo được trên mạng của dự án: host đó **không tới được**. Kết quả là ô bản đồ
   xám trơn — có toạ độ đúng, có đường kẻ tuyến, nhưng không có ảnh nền nào để
   đặt chúng lên, nên người xem đọc ra là "bản đồ hỏng".

   Một nguồn duy nhất cho một thứ nằm ngoài tầm kiểm soát là một điểm vỡ đơn.
   Tệp này biến nó thành một chuỗi: thử lần lượt, nguồn nào lỗi thì sang nguồn
   kế tiếp, và GHI NHỚ nguồn chạy được để lần sau đi thẳng vào đó.
   ========================================================================== */
(function () {
  'use strict';

  const KHOA_NHO = 'epl-lop-nen-ban-do';

  /**
   * Các nguồn ảnh nền, thử theo thứ tự.
   *
   * Nhiều nguồn là CÓ Ý, không phải để chọn cho đẹp: mỗi nguồn là một dịch vụ
   * ngoài có thể bị chặn ở một mạng nào đó, và ở Việt Nam thì
   * `tile.openstreetmap.org` là nguồn hay bị chặn nhất.
   *
   * Mỗi nguồn giữ nguyên dòng ghi công của nó — đó là điều kiện dùng của cả ba
   * dịch vụ, không phải một dòng chữ trang trí.
   */
  /* MỘT NGUỒN CHỈ ĐƯỢC VÀO DANH SÁCH NÀY NẾU NÓ TRẢ ẢNH SẠCH KHÔNG CẦN KHOÁ.
   *
   * SAI LẦM ĐÃ MẮC: tôi từng đặt `basemaps.cartocdn.com` làm nguồn đầu vì thử
   * bằng `curl` thấy HTTP 200. Nhưng 200 chỉ nghĩa là họ CÓ trả ảnh — và ảnh đó
   * bị đóng chữ "API KEY REQUIRED" chéo khắp bản đồ. Người dùng thấy nguyên một
   * màn hình đầy chữ đó giữa lúc demo.
   *
   * Nên phép thử đúng cho một nguồn ảnh nền không phải mã trả về, mà là MỞ MỘT
   * Ô ẢNH RA XEM. Ba nguồn dưới đây đều đã xem bằng mắt: ảnh sạch, không dấu,
   * không đòi khoá.
   */
  const NGUON = [
    {
      ma: 'osm-de',
      url: 'https://{s}.tile.openstreetmap.de/{z}/{x}/{y}.png',
      tuyChon: { subdomains: 'abc', maxZoom: 18, attribution: '&copy; OpenStreetMap contributors' },
    },
    {
      ma: 'osm',
      url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      tuyChon: { subdomains: 'abc', maxZoom: 19, attribution: '&copy; OpenStreetMap contributors' },
    },
    {
      ma: 'esri',
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
      tuyChon: { maxZoom: 19, attribution: 'Tiles &copy; Esri' },
    },
  ];

  const NGUON_VE_TINH = {
    ma: 'esri-anh',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    tuyChon: {
      maxZoom: 19,
      attribution: 'Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics',
    },
  };

  //: Bao nhiêu ô ảnh lỗi thì coi là nguồn đó không dùng được.
  //:
  //: Không phải 1: một ô lỗi lẻ xảy ra cả trên nguồn tốt (một ô chưa kịp sinh,
  //: một lần mất gói). Nhảy nguồn vì một ô là nhảy liên tục và bản đồ nháy.
  //: Cũng không quá cao: người dùng đang nhìn một ô xám và đợi.
  const NGUONG_LOI = 4;

  function nhoNguon(ma) {
    try { localStorage.setItem(KHOA_NHO, ma); } catch (e) { /* trình duyệt chặn lưu */ }
  }
  function nguonDaNho() {
    try { return localStorage.getItem(KHOA_NHO); } catch (e) { return null; }
  }

  /**
   * Danh sách nguồn đã xếp lại: nguồn từng chạy được đứng đầu.
   *
   * Không có bước này thì trên một mạng chặn OpenStreetMap, mỗi lần mở bản đồ
   * lại mất một nhịp thử nguồn chết trước khi tới nguồn tốt.
   */
  function thuTuNguon() {
    const nho = nguonDaNho();
    if (!nho) return NGUON.slice();
    const dau = NGUON.filter(x => x.ma === nho);
    return dau.concat(NGUON.filter(x => x.ma !== nho));
  }

  /**
   * Tạo lớp nền cho một bản đồ Leaflet, tự chuyển nguồn khi nguồn hiện tại lỗi.
   *
   * Trả về `{ lop, doiSangVeTinh, doiSangDuong }` để màn nào có nút "Vệ tinh"
   * dùng tiếp; màn không có nút thì chỉ cần gọi rồi bỏ đó.
   */
  function tao(map, tuyChon) {
    if (typeof L === 'undefined' || !map) return null;
    const cauHinh = tuyChon || {};
    const ds = thuTuNguon();
    let i = 0;
    let lop = null;
    let demLoi = 0;

    function veTinh(nguon) {
      demLoi = 0;
      if (lop) map.removeLayer(lop);
      lop = L.tileLayer(nguon.url, nguon.tuyChon).addTo(map);
      lop.on('tileerror', function () {
        demLoi += 1;
        if (demLoi < NGUONG_LOI) return;
        // Hết nguồn thì DỪNG, giữ lại nguồn cuối. Xoay vòng mãi thì bản đồ nháy
        // liên tục và người dùng không đọc được gì; giữ lại một nền xám im lặng
        // thì ít nhất đường kẻ tuyến và các điểm vẫn đọc được.
        if (i + 1 >= ds.length) {
          if (typeof cauHinh.khiHetNguon === 'function') cauHinh.khiHetNguon();
          return;
        }
        i += 1;
        veTinh(ds[i]);
      });
      lop.on('load', function () {
        // Chỉ ghi nhớ khi ĐÃ tải được ảnh thật, không ghi lúc vừa tạo lớp.
        nhoNguon(nguon.ma);
      });
      return lop;
    }

    veTinh(ds[0]);

    return {
      get lop() { return lop; },
      doiSangVeTinh() {
        demLoi = 0;
        if (lop) map.removeLayer(lop);
        lop = L.tileLayer(NGUON_VE_TINH.url, NGUON_VE_TINH.tuyChon).addTo(map);
        return lop;
      },
      doiSangDuong() {
        i = 0;
        return veTinh(thuTuNguon()[0]);
      },
    };
  }

  window.LopNenBanDo = { tao, NGUON, NGUON_VE_TINH, NGUONG_LOI };
})();

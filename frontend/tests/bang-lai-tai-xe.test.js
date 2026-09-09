/**
 * MÀN "TÀI XẾ & BẰNG LÁI" — kết luận trên màn phải trùng cửa chặn điều phối.
 *
 * VÌ SAO BÀI NÀY QUAN TRỌNG HƠN NÓ TRÔNG. Màn này tồn tại để chữa một cái cổng
 * khoá mà không phát chìa: `tms_dispatch_service` chặn điều phối bằng
 * `DRIVER_LICENSE_INVALID`, và trước đây không có màn nào khai được bằng lái.
 * Nhưng một màn nói SAI về việc ai bị chặn thì còn tệ hơn không có màn: người
 * vận hành đọc "đủ điều kiện", xếp chuyến, rồi điều phối vẫn chặn — và từ đó
 * họ không tin cả hai chỗ nữa.
 *
 * Nên bảng trường hợp dưới đây là BẢN SAO của bảng trường hợp ở
 * `backend/tests/test_tms_dispatch_eligibility.py`. Năm trạng thái làm máy chủ
 * bật `DRIVER_LICENSE_INVALID` phải là đúng năm trạng thái mà `ketLuan()` gọi
 * là `chan: true`. Sửa điều kiện ở service mà quên một trong hai chỗ thì một
 * trong hai bộ kiểm sẽ đỏ — đó là điều mong muốn.
 *
 * Nguyên văn điều kiện ở service, để người sửa sau không phải đi tìm:
 *
 *     if (not qualification or qualification.status != "active"
 *             or qualification.valid_from.date() > trip_date
 *             or qualification.valid_to.date() < trip_date
 *             or qualification.license_type != driver.license_type):
 *         raise conflict("DRIVER_LICENSE_INVALID", ...)
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');

let JSDOM;
let VirtualConsole;
try {
  ({ JSDOM, VirtualConsole } = require('jsdom'));
} catch (e) {
  console.log('bang-lai-tai-xe: BỎ QUA (chưa cài jsdom)');
  process.exit(0);
}

/* -------------------------------------------------- phần không cần trình duyệt -- */

// Khung trang phải có đủ ba thứ, không thì tệp JS không bao giờ chạy.
assert.ok(html.includes('id="md-tab-drivers"'),
  'thiếu khung #md-tab-drivers trong index.html');
assert.ok(/src="\/static\/js\/bang-lai-tai-xe\.js/.test(html),
  'thiếu thẻ script cho bang-lai-tai-xe.js');
assert.ok(/href="\/static\/css\/bang-lai-tai-xe\.css/.test(html),
  'thiếu thẻ link cho bang-lai-tai-xe.css');
assert.ok(html.includes("switchMasterDataTab('md-tab-drivers'"),
  'thiếu nút mở thẻ Tài xế & Bằng lái');

// Số thứ tự trên các thẻ phải liên tục, không trùng và không nhảy. Thêm một thẻ
// vào giữa mà quên đánh số lại là để hai thẻ cùng mang số 5.
//
// Dãy bắt đầu từ 1, không phải 0: thẻ "0. Setup A-Z" không mang khoá
// `tab_md_*` (nó dùng khoá chữ 'Setup A-Z'), nên nó không nằm trong dãy đo được.
{
  const so = [...html.matchAll(/data-i18n="tab_md_[a-z_]+">(\d+)\./g)].map(m => Number(m[1]));
  assert.deepStrictEqual(so, so.map((_, i) => i + 1),
    'số thứ tự các thẻ Dữ liệu gốc phải là 1,2,3,… liên tục — đang là: ' + so.join(','));
}

// Và cùng bộ số đó phải có trong lang.json cho CẢ BA thứ tiếng, không thì đổi
// sang tiếng Anh là số nhảy lung tung.
{
  const lang = JSON.parse(fs.readFileSync(path.join(ROOT, 'js/lang.json'), 'utf8'));
  assert.ok(lang.tab_md_licenses, 'thiếu khoá tab_md_licenses trong lang.json');
  ['vi', 'en', 'la'].forEach(t => {
    assert.ok(lang.tab_md_licenses[t], `tab_md_licenses thiếu tiếng ${t}`);
    assert.ok(/^5\./.test(lang.tab_md_licenses[t]),
      `tab_md_licenses (${t}) phải mang số 5 — đang là "${lang.tab_md_licenses[t]}"`);
  });
  ['tab_md_currencies', 'tab_md_customers', 'tab_md_taxes',
    'tab_md_periods', 'tab_md_carriers', 'tab_md_mappings'].forEach(k => {
    ['vi', 'en', 'la'].forEach(t => {
      const so = Number(String(lang[k][t]).split('.')[0]);
      assert.ok(so >= 6, `${k} (${t}) phải mang số từ 6 trở lên sau khi chèn thẻ 5 `
        + `— đang là "${lang[k][t]}"`);
    });
  });
}

/* --------------------------------------------------------- nạp trong jsdom -- */

const loi = [];
const vc = new VirtualConsole();
vc.on('jsdomError', e => {
  const c = String((e && e.message) || e);
  if (!/Not implemented: Window/.test(c)) loi.push(c.split('\n')[0]);
});

const than = html
  .replace(/<script\b[^>]*src="[^"]*"[^>]*><\/script>/g, '')
  .replace(/<link\b[^>]*>/g, '');
const tepJs = [...html.matchAll(/src="\/static\/js\/([a-z0-9\-.]+\.js)/g)].map(m => m[1]);
const dom = new JSDOM(than, {
  url: 'http://127.0.0.1/', runScripts: 'dangerously', virtualConsole: vc,
});
const w = dom.window;
const d = w.document;

/** Hai tài xế đủ điều kiện, một tài xế chưa khai bằng. */
const TAI_XE = [
  { id: 'DRV-A', name: 'Tài xế A', license_type: 'FC', phone: '0900000001', role: 'Lái xe chính' },
  { id: 'DRV-B', name: 'Tài xế B', license_type: 'C', phone: '0900000002', role: 'Lái xe chính' },
  { id: 'DRV-C', name: 'Tài xế C', license_type: 'B2', phone: '0900000003', role: 'Lái xe chính' },
];
const GIAY_PHEP = [
  {
    driver_id: 'DRV-A', license_type: 'FC', status: 'active',
    valid_from: '2025-01-01T00:00:00', valid_to: '2030-01-01T00:00:00',
  },
  {
    driver_id: 'DRV-B', license_type: 'C', status: 'active',
    valid_from: '2025-01-01T00:00:00', valid_to: '2030-01-01T00:00:00',
  },
];

w.fetch = (u) => {
  const duong = String(u);
  const tra = goi => Promise.resolve({
    ok: true, status: 200,
    json: () => Promise.resolve(goi),
    text: () => Promise.resolve('{}'),
  });
  if (duong.includes('lang.json')) {
    return tra(JSON.parse(fs.readFileSync(path.join(ROOT, 'js/lang.json'), 'utf8')));
  }
  if (duong.includes('/api/tms/driver-qualifications')) {
    return tra({ items: GIAY_PHEP, page: 1, page_size: 200, total: GIAY_PHEP.length });
  }
  if (duong.includes('/api/drivers')) return tra(TAI_XE);
  return tra({ items: [], total: 0, data: { items: [] } });
};
w.alert = () => {};
w.confirm = () => true;
w.prompt = () => '';
tepJs.forEach(ten => {
  const s = d.createElement('script');
  try {
    s.textContent = fs.readFileSync(path.join(ROOT, 'js', ten), 'utf8');
  } catch (e) {
    return;
  }
  d.body.appendChild(s);
});

/* ================================================================ bảng ca ==== */

const NGAY_CHUYEN = '2026-08-11';          // cùng ngày chuyến với bài kiểm máy chủ
const DU = {
  license_type: 'FC', status: 'active',
  valid_from: '2025-01-01T00:00:00', valid_to: '2028-01-01T00:00:00',
};
const TAI_XE_FC = { id: 'X', license_type: 'FC' };

/** [tên, tài xế, giấy phép, có bị chặn không, mã kết luận mong đợi] */
const CAC_CA = [
  ['đủ cả năm điều kiện thì đi được', TAI_XE_FC, DU, false, 'du'],
  ['không có dòng bằng lái nào', TAI_XE_FC, null, true, 'thieu'],
  ['trạng thái không phải active', TAI_XE_FC,
    Object.assign({}, DU, { status: 'suspended' }), true, 'khong-hieu-luc'],
  ['chưa tới ngày hiệu lực', TAI_XE_FC,
    Object.assign({}, DU, { valid_from: '2026-09-01T00:00:00' }), true, 'chua-hieu-luc'],
  ['đã hết hạn trước ngày chuyến', TAI_XE_FC,
    Object.assign({}, DU, { valid_to: '2026-08-10T00:00:00' }), true, 'het-han'],
  ['hạng trên giấy phép lệch hồ sơ tài xế', TAI_XE_FC,
    Object.assign({}, DU, { license_type: 'C' }), true, 'lech-hang'],
];

/* Hai mốc biên, vì lỗi lệch một ngày là lỗi phổ biến nhất ở chỗ này. Máy chủ
   dùng `valid_to.date() < trip_date`, nên bằng hết hạn ĐÚNG ngày chuyến thì
   VẪN ĐI ĐƯỢC; và `valid_from.date() > trip_date`, nên bằng có hiệu lực đúng
   ngày chuyến cũng đi được. */
const CA_BIEN = [
  ['hết hạn đúng ngày chuyến thì vẫn đi được', TAI_XE_FC,
    Object.assign({}, DU, { valid_to: NGAY_CHUYEN + 'T00:00:00' }), false],
  ['có hiệu lực đúng ngày chuyến thì đi được', TAI_XE_FC,
    Object.assign({}, DU, { valid_from: NGAY_CHUYEN + 'T00:00:00' }), false],
];

setTimeout(() => {
  assert.strictEqual(typeof w.switchMasterDataTab, 'function', 'không có switchMasterDataTab');
  assert.strictEqual(w.switchMasterDataTab.__btlDaBoc, true,
    'bang-lai-tai-xe.js chưa bọc switchMasterDataTab — mở thẻ sẽ không nạp gì');
  assert.ok(w.EplBangLai && typeof w.EplBangLai.ketLuan === 'function',
    'không có window.EplBangLai.ketLuan');

  const { ketLuan } = w.EplBangLai;

  // --- 1. Bảng trường hợp: trùng đúng cửa chặn của máy chủ ---------------
  CAC_CA.forEach(([ten, tx, gp, chan, ma]) => {
    const kq = ketLuan(tx, gp, NGAY_CHUYEN);
    assert.strictEqual(kq.chan, chan,
      `"${ten}": mong đợi chan=${chan}, nhận được ${kq.chan} (${kq.ma} — ${kq.chu})`);
    assert.strictEqual(kq.ma, ma, `"${ten}": mong đợi mã "${ma}", nhận được "${kq.ma}"`);
    // Mọi kết luận phải có câu giải thích. Một nhãn đỏ không kèm lý do thì
    // người vận hành biết mình bị chặn mà không biết phải sửa gì.
    assert.ok(kq.chu && kq.vi, `"${ten}": thiếu nhãn hoặc thiếu câu giải thích`);
  });

  // --- 2. Hai mốc biên một ngày -----------------------------------------
  CA_BIEN.forEach(([ten, tx, gp, chan]) => {
    const kq = ketLuan(tx, gp, NGAY_CHUYEN);
    assert.strictEqual(kq.chan, chan,
      `"${ten}": mong đợi chan=${chan}, nhận được ${kq.chan} (${kq.ma})`);
  });

  // --- 3. Cảnh báo sắp hết hạn là CẢNH BÁO, không phải chặn --------------
  {
    const sapHet = new Date(2026, 7, 11 + 10);      // 10 ngày sau ngày chuyến
    const kq = ketLuan(TAI_XE_FC, Object.assign({}, DU, {
      valid_to: `${sapHet.getFullYear()}-${String(sapHet.getMonth() + 1).padStart(2, '0')}-`
        + `${String(sapHet.getDate()).padStart(2, '0')}T00:00:00`,
    }), NGAY_CHUYEN);
    assert.strictEqual(kq.ma, 'sap-het', 'còn 10 ngày phải rơi vào nhóm "sắp hết hạn"');
    assert.strictEqual(kq.chan, false,
      '"sắp hết hạn" KHÔNG được coi là chặn — máy chủ vẫn cho đi, đây chỉ là nhắc trước');
  }

  // --- 4. Màn hình dựng được và nói đúng ---------------------------------
  w.switchView('master-data');
  w.switchMasterDataTab('md-tab-drivers');

  setTimeout(() => {
    const goc = d.getElementById('md-tab-drivers');
    assert.ok(goc.querySelector('.btl'), 'khung màn không được dựng');

    const dong = [...d.querySelectorAll('#btl-rows tr')];
    assert.strictEqual(dong.length, 3, `phải hiện đủ 3 tài xế, đang hiện ${dong.length}`);

    // DRV-C chưa khai bằng -> phải bị nêu là thiếu, và thẻ "Thiếu bằng lái"
    // phải đếm đúng 1. Đây là chỗ một màn dễ nói dối nhất: trừ hai danh sách
    // cho nhau mà lấy thiếu một trang là kết luận sai cho cả trang đó.
    const the = [...d.querySelectorAll('#btl-kpi button')];
    const thieu = the.find(b => /Thiếu bằng lái/.test(b.textContent));
    assert.ok(thieu, 'thiếu thẻ "Thiếu bằng lái"');
    assert.strictEqual(thieu.querySelector('b').textContent.trim(), '1',
      'thẻ "Thiếu bằng lái" phải đếm đúng 1 (DRV-C chưa khai)');
    assert.ok(!thieu.hasAttribute('disabled'),
      'thẻ có 1 người thì phải bấm được để lọc');

    // Thẻ rỗng phải `disabled` KÈM chú giải — cùng khuôn với màn Chuyến và màn
    // Điều phối. Cho bấm rồi hiện bảng trống thì người dùng phải thử mới biết.
    const lech = the.find(b => /Lệch hạng/.test(b.textContent));
    assert.ok(lech && lech.hasAttribute('disabled'),
      'thẻ "Lệch hạng" đang là 0 nên phải disabled');
    assert.ok(/Không có tài xế nào/.test(lech.getAttribute('title') || ''),
      'thẻ disabled phải có chú giải nói rõ vì sao không bấm được');

    // Mỗi dòng phải có đúng một nút mở phiếu bằng lái, và nhãn nút phải nói
    // đúng việc: "Khai bằng" khi chưa có, "Sửa bằng" khi đã có.
    const nut = [...d.querySelectorAll('#btl-rows button[data-sua]')];
    assert.strictEqual(nut.length, 3, 'mỗi dòng phải có đúng một nút mở phiếu bằng lái');
    const nutC = nut.find(b => b.getAttribute('data-sua') === 'DRV-C');
    assert.strictEqual(nutC.textContent.trim(), 'Khai bằng',
      'tài xế chưa có bằng thì nút phải ghi "Khai bằng", không phải "Sửa bằng"');
    const nutA = nut.find(b => b.getAttribute('data-sua') === 'DRV-A');
    assert.strictEqual(nutA.textContent.trim(), 'Sửa bằng',
      'tài xế đã có bằng thì nút ghi "Sửa bằng"');

    // Ô "Xét theo ngày" phải đổi được kết luận — đây là điểm khác biệt chính so
    // với một bảng chỉ xét hôm nay: cửa chặn so với NGÀY CHẠY CHUYẾN.
    const oNgay = d.getElementById('btl-ngay');
    assert.ok(oNgay, 'thiếu ô "Xét theo ngày"');
    oNgay.value = '2031-01-01';                 // sau khi cả hai bằng hết hạn
    oNgay.dispatchEvent(new w.Event('change', { bubbles: true }));
    const hetHan = the2('het-han');
    assert.strictEqual(hetHan, 2,
      `xét ngày 2031 thì hai bằng (hết hạn 2030) phải vào nhóm hết hạn, đang là ${hetHan}`);

    // --- 5. CỬA CHO BIỂU MẪU HỒ SƠ TÀI XẾ ---------------------------------
    //
    // `driver-modal-dialog` là biểu mẫu duy nhất sửa được tên, số điện thoại,
    // vai trò, hạng bằng, ca làm — và trước khi có màn này thì KHÔNG có nút nào
    // trong toàn bộ trang mở nó, nên hồ sơ tài xế không sửa được từ giao diện.
    // Bài này chốt lại cửa đó.
    {
      assert.ok(d.getElementById('btl-them-tx'), 'thiếu nút "Thêm tài xế"');
      assert.strictEqual(typeof w.openAddDriverModal, 'function',
        'không còn hàm openAddDriverModal — nút "Thêm tài xế" sẽ không mở được gì');

      const hoSo = [...d.querySelectorAll('#btl-rows button[data-hoso]')];
      assert.strictEqual(hoSo.length, 3, 'mỗi dòng phải có một nút "Hồ sơ"');
      assert.strictEqual(hoSo[0].textContent.trim(), 'Hồ sơ');

      // Và nó phải MỞ THẬT. `editDriverById` đọc từ mảng `fioriDrivers` của
      // `app.js`, không đọc từ dữ liệu của màn này; mảng rỗng thì hàm im lặng
      // thoát ngay. Nên phải bấm rồi đo, không chỉ kiểm nút có tồn tại.
      const hop = d.getElementById('driver-modal-dialog');
      assert.ok(hop, 'không có #driver-modal-dialog trong trang');
      assert.ok(!hop.closest('.view-section'),
        'hộp thoại phải được chuyển ra ngoài khung màn, không thì khối ẩn giam nó');

      const nutA = hoSo.find(b => b.getAttribute('data-hoso') === 'DRV-A');
      nutA.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
      setTimeout(() => {
        assert.strictEqual(hop.style.display, 'flex',
          'bấm "Hồ sơ" phải mở được biểu mẫu tài xế — đang là "'
          + hop.style.display + '"');
        assert.strictEqual(d.getElementById('drv-name').value, 'Tài xế A',
          'biểu mẫu phải điền sẵn đúng tài xế được chọn');
        assert.strictEqual(d.getElementById('drv-phone').value, '0900000001',
          'biểu mẫu phải điền sẵn số điện thoại — đây là trường dễ bị xoá trắng nhất');

        // Và việc lưu hồ sơ phải làm màn này nạp lại, không thì sửa hạng bằng
        // xong mà bảng vẫn hiện giá trị cũ.
        assert.strictEqual(w.saveDriverModal.__btlDaBoc, true,
          'bang-lai-tai-xe.js chưa bọc saveDriverModal — lưu hồ sơ xong bảng không nạp lại');

        assert.deepStrictEqual(loi.slice(0, 3), [], 'có lỗi JS: ' + loi.slice(0, 3).join(' | '));
        console.log('bang-lai-tai-xe: %d ca kết luận + %d ca biên + màn dựng được '
          + '+ cửa hồ sơ tài xế mở được, khớp cửa chặn', CAC_CA.length, CA_BIEN.length);
        process.exit(0);
      }, 600);
    }
  }, 700);

  function the2(ma) {
    const b = d.querySelector(`#btl-kpi button[data-loc="${ma}"]`);
    if (!b) return 0;    // thẻ rỗng bị disabled thì không có data-loc
    return Number(String(b.querySelector('b').textContent).replace(/[^\d]/g, '') || 0);
  }
}, 1500);

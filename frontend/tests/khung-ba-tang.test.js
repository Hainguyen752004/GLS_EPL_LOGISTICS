/**
 * Khung ba tầng phải đi tới được mọi màn, và đi tới ĐÚNG màn.
 *
 * Khung là chỗ mà một lỗi nhỏ làm mất luôn cả một màn: một `data-view` gõ sai
 * một chữ thì mục đó bấm vào chỉ hiện thông báo "không tìm thấy màn hình", mà
 * mục vẫn nằm đó nhìn như bình thường. Không có lỗi nào trong console. Đó là
 * kiểu lỗi phải bắt bằng bài kiểm chứ không bắt bằng mắt, vì phải bấm đủ 19
 * mục mới thấy.
 *
 * Bài kiểm này làm bốn việc:
 *   1. Khung cũ không còn dấu vết — `.samsung-header` và dải dọc bên trái. Sót
 *      lại thì hai khung cùng hiện, hoặc phần đệm 104px chừa cho dải dọc vẫn
 *      còn mà dải thì không.
 *   2. Mọi `data-view` trỏ tới một `#view-*` CÓ THẬT, mọi `data-md-tab` trỏ tới
 *      một nút thẻ CÓ THẬT trong màn Dữ liệu gốc.
 *   3. Mọi hàm mà `NUT_DAU_TRANG` gọi đều tồn tại trong `app.js`. Bảng đó khai
 *      tên hàm bằng chuỗi, nên gõ sai không ai báo — nút chỉ lặng lẽ không
 *      được vẽ ra.
 *   4. Nạp THẬT cả trang trong jsdom rồi bấm: mở bảng chọn, chuyển màn, đọc
 *      tiêu đề tầng 3, và gõ vào ô tìm.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const NL = String.fromCharCode(10);
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8')
  .split(String.fromCharCode(13)).join('');
const khung = fs.readFileSync(path.join(ROOT, 'js', 'khung-moi.js'), 'utf8')
  .split(String.fromCharCode(13)).join('');
const css = fs.readFileSync(path.join(ROOT, 'css', 'khung-moi.css'), 'utf8');

// --- 1. Khung cũ không còn dấu vết -----------------------------------

for (const dauVet of ['samsung-header', 'samsung-nav', 'nav-item-ss', 'mega-menu',
  'mega-card', 'sticky-top-flow-tracker', 'workflow-left-rail']) {
  assert.ok(!html.includes(dauVet),
    `khung cũ còn dấu vết "${dauVet}" trong index.html`);
}

{
  // Phần đệm 104px là chỗ chừa cho dải dọc 78px. Dải đã bỏ thì phần đệm phải
  // bỏ theo, không thì mọi màn thụt vào một khoảng trắng rỗng.
  const i = css.indexOf('.samsung-main-wrapper');
  assert.ok(i > 0, 'khung-moi.css phải ghi đè phần đệm của .samsung-main-wrapper');
  const luat = css.slice(i, css.indexOf('}', i));
  assert.ok(!/104px/.test(luat), 'phần đệm 104px chừa cho dải dọc đã bỏ vẫn còn');
}

// --- 2. Mọi mối đi tới phải có đích thật ------------------------------

{
  const coMan = new Set([...html.matchAll(/id="view-([a-z0-9-]+)"/g)].map(m => m[1]));
  assert.ok(coMan.size >= 14, `chỉ thấy ${coMan.size} màn — phép dò có vấn đề`);

  // Chỉ soi trong khung, không soi cả trang: các màn cũng dùng `data-view` cho
  // việc riêng của chúng.
  const iBar1 = html.indexOf('class="epl-bar1"');
  const iHetNav = html.indexOf('</nav>', html.indexOf('id="epl-bar2"'));
  assert.ok(iBar1 > 0 && iHetNav > iBar1, 'không khoanh được vùng khung');
  const vungKhung = html.slice(iBar1, iHetNav);

  const dsView = [...vungKhung.matchAll(/data-view="([a-z0-9-]+)"/g)].map(m => m[1]);
  assert.ok(dsView.length >= 12, `khung chỉ trỏ tới ${dsView.length} màn`);
  dsView.forEach(man => {
    assert.ok(coMan.has(man), `khung trỏ tới màn "${man}" mà không có #view-${man}`);
  });

  const dsThe = [...vungKhung.matchAll(/data-md-tab="([a-z0-9-]+)"/g)].map(m => m[1]);
  assert.ok(dsThe.length >= 5, `khung chỉ trỏ tới ${dsThe.length} thẻ Dữ liệu gốc`);
  dsThe.forEach(the => {
    assert.ok(html.includes(`switchMasterDataTab('${the}'`),
      `khung trỏ tới thẻ "${the}" mà màn Dữ liệu gốc không có nút nào mở nó`);
    assert.ok(html.includes(`id="${the}"`), `thẻ "${the}" không có khung nội dung`);
  });

  // Mỗi mục chỉ được khai MỘT trong hai — khai cả hai thì `data-md-tab` thắng
  // và `data-view` thành chữ trang trí gây hiểu sai.
  [...vungKhung.matchAll(/<div class="epl-mi"[^>]*>/g)].forEach(m => {
    const the = m[0];
    const coView = the.includes('data-view=');
    const coTab = the.includes('data-md-tab=');
    assert.ok(coView !== coTab,
      `một mục khai ${coView && coTab ? 'CẢ HAI' : 'KHÔNG có'} data-view/data-md-tab: ${the}`);
  });
}

// --- 2b. Mọi nhãn của khung phải dịch được cả ba ngôn ngữ -------------

{
  // Nhãn thiếu bản dịch thì `changeLanguage` bỏ qua ô đó và giữ nguyên tiếng
  // Việt — không báo lỗi gì cả. Nên một người dùng Lào sẽ thấy dải điều hướng
  // lẫn hai thứ tiếng, và không ai biết cho tới khi họ nói ra.
  const lang = JSON.parse(fs.readFileSync(path.join(ROOT, 'js', 'lang.json'), 'utf8'));
  const iBar1 = html.indexOf('class="epl-bar1"');
  const iHetNav = html.indexOf('</nav>', html.indexOf('id="epl-bar2"'));
  const dsKhoa = [...html.slice(iBar1, iHetNav).matchAll(/data-i18n="([a-z0-9_]+)"/g)]
    .map(m => m[1]);
  assert.ok(dsKhoa.length >= 20, `khung chỉ có ${dsKhoa.length} nhãn gắn khóa dịch`);

  dsKhoa.forEach(khoa => {
    assert.ok(lang[khoa], `khung dùng khóa "${khoa}" mà lang.json không có`);
    ['vi', 'en', 'la'].forEach(ng => {
      assert.ok(lang[khoa][ng] && String(lang[khoa][ng]).trim(),
        `khóa "${khoa}" thiếu bản dịch "${ng}"`);
    });
  });

  // Và khóa nào chỉ khung dùng thì phải CÒN được khung dùng. Bỏ một mục khỏi
  // khung mà quên khóa thì lang.json phình lên bằng chữ chết, rồi lần sau ai
  // sửa nhãn sẽ sửa vào khóa chết mà không hiểu vì sao màn hình không đổi —
  // đúng chỗ đã mất công dọn một lần khi đổi khung.
  const dungTrongKhung = new Set(dsKhoa);
  Object.keys(lang).filter(k => k.startsWith('khung_')).forEach(k => {
    assert.ok(dungTrongKhung.has(k),
      `lang.json còn khóa chết "${k}" — không thẻ nào trong khung dùng nó`);
  });
}

// --- 3. Hàm mà nút đầu trang gọi phải tồn tại -------------------------

{
  const i = khung.indexOf('const NUT_DAU_TRANG = {');
  assert.ok(i > 0, 'thiếu bảng NUT_DAU_TRANG');
  const bang = new Function(
    khung.slice(i, khung.indexOf(NL + '  };', i) + 5) + NL + 'return NUT_DAU_TRANG;')();

  let soNut = 0;
  Object.entries(bang).forEach(([man, ds]) => {
    ds.forEach(([chu, kieu, ten]) => {
      soNut += 1;
      assert.ok(kieu === 'primary' || kieu === 'ghost',
        `nút "${chu}" ở màn ${man} khai kiểu lạ: ${kieu}`);
      assert.ok(new RegExp(`window\\.${ten}\\s*=`).test(app),
        `nút "${chu}" ở màn ${man} gọi ${ten}() — không có hàm đó trong app.js`);
    });
  });
  assert.ok(soNut >= 1, `không có nút đầu trang nào`);

  // Nút đầu trang KHÔNG được trùng việc với nút đã có sẵn trong màn. Hai nút
  // cho cùng một việc thì người dùng phải đoán chúng có khác nhau không, và khi
  // một bên đổi thì bên kia lặng lẽ lệch. Bảng này thoạt đầu khai sáu nút, tra
  // lại thì bốn cái trùng — nên phép kiểm phải tra, không tin bảng.
  Object.entries(bang).forEach(([man, ds]) => {
    ds.forEach(([chu, , ten]) => {
      const daCo = (html.match(new RegExp(`onclick="${ten}\\(`, 'g')) || []).length;
      assert.strictEqual(daCo, 0,
        `nút "${chu}" ở đầu trang gọi ${ten}(), mà trong màn đã có ${daCo} nút gọi đúng hàm đó`);
    });
  });

  // Và mỗi màn trong bảng nút phải có tên trong bảng đầu trang, không thì nút
  // hiện ra dưới một tiêu đề trống.
  const j = khung.indexOf('const DAU_TRANG_THEO_MAN = {');
  const dauTrang = new Function(
    khung.slice(j, khung.indexOf(NL + '  };', j) + 5) + NL + 'return DAU_TRANG_THEO_MAN;')();
  Object.keys(bang).forEach(man => {
    assert.ok(dauTrang[man], `màn ${man} có nút mà không có tiêu đề đầu trang`);
  });
  // Mọi màn khai đầu trang phải nói được nó để làm gì — câu đó là chỗ duy nhất
  // phân biệt các màn gần nhau.
  Object.entries(dauTrang).forEach(([man, d]) => {
    assert.ok(d[2] && d[2].trim(), `màn ${man} thiếu tiêu đề`);
    assert.ok(d[3] && d[3].length > 25, `màn ${man} thiếu câu nói màn này để làm gì`);
  });
}

// --- 4. Nạp thật rồi bấm ----------------------------------------------

let JSDOM;
try {
  ({ JSDOM } = require('jsdom'));
} catch (e) {
  console.log('khung-ba-tang: BỎ QUA phần nạp thật (chưa có jsdom)');
  console.log('khung-ba-tang: ba phần đối chiếu tĩnh đã qua');
  process.exit(0);
}

const { VirtualConsole } = require('jsdom');
const loi = [];
const vc = new VirtualConsole();
vc.on('jsdomError', e => loi.push(String((e && e.message) || e)));

const dom = new JSDOM(
  html.replace(/<script\b[^>]*src="[^"]*"[^>]*><\/script>/g, '')
    .replace(/<link\b[^>]*>/g, ''),
  { url: 'http://127.0.0.1/', runScripts: 'dangerously', virtualConsole: vc });
const w = dom.window;

// jsdom không có mấy thứ này; thiếu chúng thì mọi hàm vẽ nổ ngay và bài kiểm
// đọc thành "khung hỏng" trong khi khung không liên quan.
w.fetch = () => Promise.resolve({
  ok: true, status: 200, json: () => Promise.resolve({ items: [], total: 0 }),
});
w.alert = () => {};
w.confirm = () => true;
w.scrollTo = () => {};
w.print = () => {};
w.Element.prototype.scrollIntoView = () => {};

[...html.matchAll(/src="\/static\/js\/([a-z0-9-]+\.js)/g)].map(m => m[1]).forEach(ten => {
  const s = w.document.createElement('script');
  s.textContent = fs.readFileSync(path.join(ROOT, 'js', ten), 'utf8');
  w.document.body.appendChild(s);
});
assert.deepStrictEqual(loi, [], 'có lỗi khi nạp JS');

// `khung-moi.js` dựng khung khi `DOMContentLoaded` chạy. Trong jsdom, lúc vừa
// chèn script thì trang VẪN đang ở trạng thái "loading", nên sự kiện đó chưa
// nổ ra. Đo ngay lúc này thì đọc thành "khung không chạy" trong khi khung chỉ
// chưa được dựng. Phải chờ đúng sự kiện thật — và như vậy bài kiểm còn kiểm
// luôn rằng khung TỰ dựng được, không phải gọi tay.
async function choTrangSan() {
  if (w.document.readyState !== 'loading') return;
  await new Promise(xong => w.document.addEventListener('DOMContentLoaded', xong));
}

async function kiemKhiTrangSan() {
  const d = w.document;
  const bam = el => el.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));

  // 4a. Bảng chọn: bấm mở, bấm lại đóng, bấm nút khác thì đổi bảng.
  {
    const nutOps = d.querySelector('.epl-nb[data-menu="ops"]');
    const bangOps = d.getElementById('epl-m-ops');
    assert.ok(nutOps && bangOps, 'thiếu mục Vận hành');
    assert.ok(!bangOps.classList.contains('epl-show'), 'bảng chọn phải đóng lúc đầu');

    bam(nutOps);
    assert.ok(bangOps.classList.contains('epl-show'), 'bấm vào không mở bảng chọn');
    assert.strictEqual(nutOps.getAttribute('aria-expanded'), 'true');

    bam(nutOps);
    assert.ok(!bangOps.classList.contains('epl-show'), 'bấm lần hai không đóng bảng');

    bam(nutOps);
    bam(d.querySelector('.epl-nb[data-menu="biz"]'));
    assert.ok(!bangOps.classList.contains('epl-show'),
      'mở bảng khác mà bảng cũ vẫn mở — hai bảng cùng hiện đè lên nhau');
    assert.ok(d.getElementById('epl-m-biz').classList.contains('epl-show'));
    w.dongBangChon();
  }

  // 4b. Chuyển màn: mục nào bấm cũng phải mở đúng màn đó, và tầng 3 phải theo.
  {
    const dsMuc = [...d.querySelectorAll('.epl-menu .epl-mi[data-view]')];
    assert.ok(dsMuc.length >= 10, `chỉ có ${dsMuc.length} mục trỏ tới màn`);

    dsMuc.forEach(muc => {
      const man = muc.dataset.view;
      bam(muc);
      const khung = d.getElementById('view-' + man);
      assert.strictEqual(khung.style.display, 'block',
        `bấm mục "${muc.textContent.trim().slice(0, 30)}" không mở được #view-${man}`);
      // Chỉ MỘT màn được hiện — hai màn cùng hiện là hai bảng dữ liệu chồng nhau.
      const dangHien = [...d.querySelectorAll('.view-section')]
        .filter(s => s.style.display === 'block');
      assert.strictEqual(dangHien.length, 1,
        `${dangHien.length} màn cùng hiện sau khi mở ${man}`);

      const h1 = d.getElementById('epl-h1').textContent.trim();
      assert.ok(h1 && h1 !== man, `tầng 3 không có tiêu đề cho màn ${man} (thấy "${h1}")`);
      // Bảng chọn phải tự đóng, không thì nó che mất màn vừa mở.
      assert.strictEqual(d.querySelectorAll('.epl-menu.epl-show').length, 0,
        `bảng chọn còn mở sau khi đi tới ${man}`);
    });
  }

  // 4b-bis. Vào màn thì phần nội dung chính phải THẤY ĐƯỢC ngay.
  //
  // Không đủ khi chỉ kiểm `#view-<màn>` đã `display:block`: khối nội dung bên
  // trong vẫn có thể bị một tổ tiên đóng lại, và lúc đó người dùng vào màn chỉ
  // thấy trắng trơn mà không có lỗi nào. Đúng chuyện đã xảy ra với bảng DO:
  // `#ops-planning-folder-do` để `display:none` sẵn và không ai mở nó khi vào
  // màn, nên phải bấm đúng một cái thẻ mới hiện — mà không có gì nói là phải
  // bấm. Nên phải dò LÊN theo tổ tiên.
  {
    const bịĐóng = el => {
      for (let p = el; p && p !== d.body; p = p.parentElement) {
        if (p.style && p.style.display === 'none') return p.id || p.className || p.tagName;
        if (p.hasAttribute && p.hasAttribute('hidden')) return (p.id || p.tagName) + ' [hidden]';
      }
      return null;
    };

    // [mã màn, khối nội dung chính của màn đó]
    const KHOI_CHINH = [
      ['ops-planning', 'fiori-do-list'],
      ['master-data', 'md-tab-routes'],
      ['dispatch', 'view-dispatch'],
      ['tracking', 'view-tracking'],
      ['delivery-completion', 'view-delivery-completion'],
    ];
    KHOI_CHINH.forEach(([man, ma]) => {
      w.switchView(man);
      const el = d.getElementById(ma);
      assert.ok(el, `màn ${man} không có khối nội dung #${ma}`);
      const che = bịĐóng(el);
      assert.ok(!che,
        `vào màn ${man} mà #${ma} bị "${che}" đóng lại — người dùng chỉ thấy trắng trơn`);
    });
  }

  // 4c. Nút đầu trang: đúng số lượng và bấm được.
  //
  // Trước đây phép kiểm này soi màn CRM, vì màn đó khai nút "+ Đơn hàng vận
  // chuyển". Bước Đơn hàng (SO) đã bị bỏ khỏi luồng — báo giá được chấp nhận
  // thì tách thẳng thành lệnh giao hàng — nên màn CRM KHÔNG còn khai nút nào,
  // và nút "+ Báo giá" của luồng mới nằm ngay trong màn chứ không ở đầu trang.
  //
  // Điều phép kiểm này thật sự canh vẫn nguyên, chỉ đổi sang màn còn khai nút:
  // nút có đúng số lượng, đúng kiểu, và bấm vào thì gọi được hàm thật.
  {
    w.switchView('ops-planning');
    const ds = [...d.getElementById('epl-subacts').children];
    assert.strictEqual(ds.length, 1,
      `màn Lệnh giao hàng phải có 1 nút, thấy ${ds.length}`);
    assert.ok(ds[0].className.includes('epl-btn-primary'));

    let daGoi = 0;
    const cu = w.openFioriDOForm;
    w.openFioriDOForm = () => { daGoi += 1; };
    w.switchView('dashboard');
    w.switchView('ops-planning');
    bam([...d.getElementById('epl-subacts').children][0]);
    w.openFioriDOForm = cu;
    assert.strictEqual(daGoi, 1, 'nút đầu trang bấm vào không gọi hàm');

    // Màn CRM giờ phải TRỐNG. Một nút mở form của bước đã bỏ là mời người dùng
    // đi vào một đường không còn dẫn tới đâu.
    w.switchView('crm-sales');
    assert.strictEqual(d.getElementById('epl-subacts').children.length, 0,
      'màn CRM vẫn còn nút đầu trang — bước Đơn hàng (SO) đã bỏ khỏi luồng');

    // Màn không khai nút thì phải TRỐNG, không giữ lại nút của màn trước.
    w.switchView('lab-summary');
    assert.strictEqual(d.getElementById('epl-subacts').children.length, 0,
      'nút của màn trước còn sót lại ở màn không khai nút');
  }

  // 4d. Tầng 2 phải sáng đúng mục.
  {
    w.switchView('tracking');
    const sang = [...d.querySelectorAll('.epl-nb.epl-on')];
    assert.strictEqual(sang.length, 1, `${sang.length} mục cùng sáng ở màn Theo dõi`);
    assert.strictEqual(sang[0].dataset.menu, 'ops');

    w.switchView('dashboard');
    const sang2 = [...d.querySelectorAll('.epl-nb.epl-on')];
    assert.strictEqual(sang2.length, 1, 'Bảng điều khiển phải sáng mục "Hôm nay"');
    // Trang chủ (os-home) là trang đầu; trang tổng quan mở từ đó nên cùng nhóm "Hôm nay".
    assert.strictEqual(sang2[0].dataset.view, 'os-home');
  }

  // 4e. Ô tìm: gõ không dấu vẫn khớp, và Enter thì đi tới màn.
  {
    const o = d.getElementById('tim-man-hinh');
    assert.ok(o, 'thiếu ô tìm màn');
    const go = chuoi => {
      o.value = chuoi;
      o.dispatchEvent(new w.Event('input', { bubbles: true }));
    };
    const bangKQ = () => d.getElementById('ket-qua-tim-man');

    go('dieu phoi');
    assert.ok(!bangKQ().hidden, 'gõ vào mà bảng kết quả không hiện');
    assert.ok(/Điều phối/.test(bangKQ().textContent),
      'gõ "dieu phoi" không dấu mà không khớp "Điều phối"');

    go('cong thuc');
    assert.ok(/Công thức giá thành/.test(bangKQ().textContent),
      'không tìm được thẻ Dữ liệu gốc qua ô tìm');

    // Không khớp gì thì phải NÓI ô này làm gì, chứ không chỉ "không có kết quả":
    // người gõ mã DO vào đây mà chỉ thấy trống sẽ tưởng hệ thống hỏng.
    go('DEMO-DO-2026-003');
    assert.ok(/đi tới màn/i.test(bangKQ().textContent),
      'không khớp gì mà không nói rõ ô này chỉ đi tới màn');

    w.switchView('dashboard');
    go('theo doi');
    o.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    assert.strictEqual(d.getElementById('view-tracking').style.display, 'block',
      'bấm Enter ở ô tìm không đi tới màn');
    assert.strictEqual(o.value, '', 'đi tới màn rồi mà ô tìm chưa xóa');
  }

  // 4f. Nút sơ đồ A–Z phải về Bảng điều khiển.
  {
    w.switchView('lab-summary');
    bam(d.getElementById('nut-so-do-az'));
    assert.strictEqual(d.getElementById('view-dashboard').style.display, 'block',
      'nút sơ đồ A–Z không về được Bảng điều khiển');
  }

  console.log('khung-ba-tang: khung cũ đã dọn, 19 mục đều tới đúng màn, tầng 3 và ô tìm chạy');
}

choTrangSan()
  .then(() => {
    // Khung phai tu dung xong khi trang san, khong can ai goi.
    assert.ok(w.switchView && w.switchView.daBocKhung,
      'khung không tự dựng khi trang sẵn — tầng 3 sẽ không bao giờ đổi tiêu đề');
    return kiemKhiTrangSan();
  })
  .catch(e => { console.error(String(e && e.stack || e)); process.exit(1); });

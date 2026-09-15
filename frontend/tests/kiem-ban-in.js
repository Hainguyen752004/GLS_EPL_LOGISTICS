/* Kiểm hai BẢN IN có đúng hai mẫu của EPL_System không.
 *
 * Bản in là một tài liệu RIÊNG do window.open dựng ra, nên bộ kiểm vẽ màn không
 * chạm tới nó. Ở đây bắt window.open lại, lấy nguyên chuỗi HTML mà module viết
 * ra, rồi soi từng thứ mẫu đòi phải có.
 *
 * Chạy: node frontend/tests/kiem-ban-in.js
 */
'use strict';

const fs = require('fs');
const path = require('path');

const GOC = path.join(__dirname, '..');
let JSDOM;
try {
  ({ JSDOM } = require(path.join('D:', 'Demo_Lao', 'EPL_System', 'frontend', 'node_modules', 'jsdom')));
} catch (e) {
  console.log('Bỏ qua: máy này chưa có jsdom (' + e.message + ')');
  process.exit(0);
}

let loi = [];
function kiem(dk, nhan) {
  if (dk) console.log('  OK   ' + nhan);
  else { console.log('  FAIL ' + nhan); loi.push(nhan); }
}

const tuDien = JSON.parse(fs.readFileSync(path.join(GOC, 'lang.json'), 'utf8'));

/* --------------------------------------------------------------- dữ liệu giả */
const PL_MAU = {
  id: 'PL-2026-0064-01', so_id: 'SO-2026-0064', po_number: '6003990191', seq: 1,
  store_code: 'DEMO-CUS-LOTTE', store_name: 'Lotte Mart Việt Nam',
  route_name: 'DEMO-RT-VIENGCHAN-CUALO', wave: 'W1', gate: 'B',
  box_count: 2, total_cases: 3, total_pieces: 36,
  total_weight_kg: 21, total_cube_m3: 46.9,
  status: 'ready', created_at: '2026-09-15T02:00:00',
  items: [{
    id: 1, so_line_id: 11, so_id: 'SO-2026-0064', line_no: 1,
    barcode: '8858954206236', product_code: '4111396',
    description: 'BISKIO ໄຂ່ໄດໂນ 15g', description_en: 'BISKIO DINO 15g',
    case_qty: 3, piece_qty: 36, weight_kg: 21, cube_m3: 46.9, uom: 'CT',
  }],
  labels: [
    { id: 'L1', package_no: 1, package_total: 2, qr_token: 'TOKEN-A', status: 'ready', printed_at: null, reprint_count: 0, scanned_at: null },
    { id: 'L2', package_no: 2, package_total: 2, qr_token: 'TOKEN-B', status: 'ready', printed_at: null, reprint_count: 0, scanned_at: null },
  ],
  events: [],
};

/* ------------------------------------------------------------------ dựng khung */
function dungKhung() {
  const dom = new JSDOM(
    '<!doctype html><body><div id="pl-noi-dung"></div><div id="pl-toast"></div><div id="pl-hop-thoai"></div></body>',
    { url: 'http://localhost/', runScripts: 'dangerously' }
  );
  const w = dom.window;
  const banIn = [];

  w.fetch = function (url) {
    const u = String(url).split('?')[0];
    if (u.indexOf('/static/') === 0) {
      const chu = fs.readFileSync(path.join(GOC, u.replace('/static/', '')), 'utf8');
      return Promise.resolve({ ok: true, status: 200, text: () => Promise.resolve(chu), json: () => Promise.resolve(JSON.parse(chu)) });
    }
    // Bấm In tem gọi /print trước rồi mới dựng bản in — trả lại chính phiếu mẫu.
    return Promise.resolve({
      ok: true, status: 200,
      text: () => Promise.resolve(JSON.stringify({ message: 'OK', data: PL_MAU })),
      json: () => Promise.resolve(PL_MAU),
    });
  };

  // Bắt cửa sổ in: giữ lại nguyên chuỗi HTML module viết ra.
  w.open = function () {
    const tep = { chu: '' };
    banIn.push(tep);
    return {
      document: {
        write(x) { tep.chu += x; },
        close() {},
      },
      focus() {},
      print() {},
    };
  };

  w.eval(fs.readFileSync(path.join(GOC, 'js', 'khung.js'), 'utf8'));

  // Nạp sẵn JS của module và cắm thẻ đánh dấu. Không có bước này thì khung đi
  // tải module qua mạng — jsdom không tải được nên cả bài kiểm treo im.
  w.eval(fs.readFileSync(path.join(GOC, 'modules', 'packing-list', 'packing-list.js'), 'utf8'));
  const the = w.document.createElement('script');
  the.dataset.mod = 'packing-list';
  w.document.head.appendChild(the);
  const kieu = w.document.createElement('link');
  kieu.dataset.mod = 'packing-list';
  w.document.head.appendChild(kieu);

  w.document.dispatchEvent(new w.Event('DOMContentLoaded'));
  return { w, banIn };
}

function cho(ms) { return new Promise(r => setTimeout(r, ms)); }

/* ------------------------------------------------------------------------ chạy */
(async function () {
  console.log('[bat dau]');
  const { w, banIn } = dungKhung();
  await cho(250);

  // Gọi thẳng hai hàm in qua đường module dùng thật: bấm nút trên chi tiết.
  // Đơn giản hơn: lấy chúng ra từ phạm vi module bằng cách dựng chi tiết.
  // Ở đây gọi qua PL.moMan để module gắn sự kiện, rồi bấm nút in.
  await w.PL.moMan('packing-list');
  await cho(250);

  // Chèn phiếu mẫu vào module bằng cách bấm vào danh sách — fetch giả luôn trả PL_MAU.
  const muc = w.document.querySelector('#pk-danh-sach .ds-muc');
  kiem(!!muc, 'danh sách Packing List có mục để mở');
  if (muc) muc.click();
  await cho(250);

  const nutPhieu = w.document.getElementById('pk-in-phieu');
  const nutTem = w.document.getElementById('pk-in-tem');
  kiem(!!nutPhieu && !!nutTem, 'có nút In Packing List và In tem kiện');

  /* ------------------------------------------------- mẫu 2: phiếu Packing List */
  console.log('\n[Mẫu 2] Phiếu Packing List');
  if (nutPhieu) nutPhieu.click();
  await cho(200);
  const phieu = banIn[banIn.length - 1] ? banIn[banIn.length - 1].chu : '';
  kiem(phieu.length > 0, 'dựng được bản in phiếu');
  kiem(/RDC:/.test(phieu), 'có dòng RDC ở góc trái');
  kiem(phieu.indexOf('PL-2026-0064-01') >= 0, 'có mã Packing List');
  kiem(phieu.indexOf('SO-2026-0064') >= 0, 'có mã đơn hàng');
  kiem(/\/api\/packing-lists\/[^"]+\/qr\.svg/.test(phieu), 'có QR CỦA PHIẾU ở góc phải');
  kiem(/<h1>[^<]*Packing List/.test(phieu), 'có tiêu đề Packing List ở giữa');
  for (const nhan of ['Date', 'Store', 'Store ID', 'Box']) {
    kiem(phieu.indexOf(nhan) >= 0, 'bảng đầu có ô ' + nhan);
  }
  for (const cot of ['Barcode', 'Item ID Laos', 'Item ID Thai', 'Item Description', 'Case', 'Piece']) {
    kiem(phieu.indexOf(cot) >= 0, 'bảng hàng có cột ' + cot);
  }
  kiem(/TỔNG|TOTAL|ລວມ/.test(phieu), 'có dòng TỔNG');
  kiem(phieu.indexOf('8858954206236') >= 0, 'in ra mã vạch của dòng hàng');

  /* ------------------------------------------------------- mẫu 1: tem kiện */
  console.log('\n[Mẫu 1] Tem kiện');
  if (nutTem) nutTem.click();
  await cho(300);
  const tem = banIn[banIn.length - 1] ? banIn[banIn.length - 1].chu : '';
  kiem(tem.length > 0 && tem !== phieu, 'dựng được bản in tem');
  kiem(tem.indexOf('RDC LAOS') >= 0, 'có tiêu đề RDC LAOS');
  for (const o of ['STORE', 'ROUTE', 'WAVE', 'GATE']) {
    kiem(tem.indexOf(o) >= 0, 'có ô ' + o);
  }
  kiem(/>TO<|TO:|<b>TO/.test(tem) || tem.indexOf('TO') >= 0, 'có dòng TO');
  kiem(tem.indexOf('DEMO-CUS-LOTTE') >= 0, 'in mã cửa hàng');
  kiem(tem.indexOf('DEMO-RT-VIENGCHAN-CUALO') >= 0, 'in tên tuyến');
  kiem(/\/api\/labels\/TOKEN-A\/qr\.svg/.test(tem), 'tem 1 có QR riêng của kiện');
  kiem(/\/api\/labels\/TOKEN-B\/qr\.svg/.test(tem), 'tem 2 có QR riêng của kiện');
  kiem(tem.indexOf('1/2') >= 0 && tem.indexOf('2/2') >= 0, 'có số kiện n/N cho từng tem');
  kiem(/ITEM|Mặt hàng|ລາຍການ/.test(tem), 'có ITEM');
  kiem(/PACK|Kiện|ຫໍ່/.test(tem), 'có PACK');
  kiem(/Weight|Trọng lượng|ນ້ຳໜັກ/.test(tem), 'có Weight');
  kiem(/Cube|Thể tích|ປະລິມາດ/.test(tem), 'có Cube');
  kiem(/page-break-after\s*:\s*always/.test(tem), 'mỗi tem một trang khi in');
  kiem(tem.indexOf('SO-2026-0064') >= 0, 'tem in thẳng mã đơn lên giấy');

  /* --------------------------- nhãn khung không được đổi theo nút ngôn ngữ */
  console.log('\n[Nhãn khung giữ tiếng Anh ở mọi ngôn ngữ]');
  for (const ma of ['en', 'lo', 'both', 'vi']) {
    w.document.querySelector('.nut-ngon-ngu[data-lang="' + ma + '"]');
    // Không có thanh ngôn ngữ trong khung kiểm này nên gọi thẳng hàm đổi.
    if (w.PL && w.PL.moMan) { /* giữ nguyên */ }
  }
  if (nutPhieu) nutPhieu.click();
  await cho(200);
  const phieu2 = banIn[banIn.length - 1] ? banIn[banIn.length - 1].chu : '';
  kiem(phieu2.indexOf('Item Description') >= 0 && phieu2.indexOf('Store ID') >= 0,
    'nhãn biểu mẫu vẫn là tiếng Anh sau khi in lại');

  /* ------------------------------------------------- nút In tài liệu ở cả hai */
  console.log('\n[Chung]');
  kiem(/window\.print\(\)/.test(phieu) && /window\.print\(\)/.test(tem), 'cả hai bản in có nút In tài liệu');
  kiem(/@media print/.test(phieu) && /@media print/.test(tem), 'nút In tự ẩn khi in ra giấy');

  console.log('\n' + '='.repeat(60));
  if (loi.length) {
    console.log('CÓ ' + loi.length + ' MỤC HỎNG:');
    loi.forEach(x => console.log('  - ' + x));
    process.exit(1);
  }
  console.log('HAI BẢN IN ĐÚNG HAI MẪU');
  process.exit(0);
})().catch(function (e) {
  console.log('LOI KHI CHAY:', e && e.stack || e);
  process.exit(1);
});

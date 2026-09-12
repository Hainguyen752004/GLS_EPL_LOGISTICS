// Đổi sang tiếng Anh/Lào KHÔNG được làm mất dữ liệu vừa nạp.
//
// Lỗi đã xảy ra thật, chủ dự án báo "chuyển tiếng anh và tiếng lào nó không
// load được data": bộ dịch nhớ đệm chữ của một thẻ ngay lần gặp đầu tiên — lúc
// đó thẻ mới chỉ là ô chứa với chữ "Đang tải dữ liệu...". Khi dữ liệu thật đổ
// vào, lượt dịch sau vẫn so theo chữ CŨ, khớp, rồi ghi bản dịch của câu chờ đè
// lên dữ liệu. Bài này giữ cho chuyện đó không tái diễn.
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const GOC = path.join(__dirname, '..');
const src = fs.readFileSync(path.join(GOC, 'js', 'app.js'), 'utf8');
const lang = JSON.parse(fs.readFileSync(path.join(GOC, 'js', 'lang.json'), 'utf8'));

const dom = new JSDOM('<!doctype html><body></body>');
const w = dom.window;

// Lấy NGUYÊN VĂN cụm hàm dịch trong app.js, không chép lại logic.
const bd = src.indexOf('let _transDebounceTimer');
const kt = src.indexOf('if (typeof MutationObserver');
assert.ok(bd > 0 && kt > bd, 'không tách được cụm hàm dịch trong app.js');

const getViTranslationMap = () => {
  const m = new Map();
  for (const k of Object.keys(lang)) {
    const e = lang[k];
    if (e.vi) m.set(String(e.vi).trim().toLowerCase(), e);
    if (e.en) m.set(String(e.en).trim().toLowerCase(), e);
  }
  return m;
};
const dich = new Function(
  'appTranslations', 'fixUIText', 'getViTranslationMap', 'document', 'window', 'NodeFilter',
  src.slice(bd, kt) + '\n return translateAllDOMTexts;'
)(lang, s => s, getViTranslationMap, w.document, w, w.NodeFilter);

function chay(nhan, dungThe) {
  w.document.body.innerHTML = '<div id="o"><span>Đang tải dữ liệu...</span></div>';
  const o = w.document.getElementById('o');

  // Lượt dịch ĐẦU chạy lúc ô còn là chữ chờ — đây là lúc bản cũ nhớ đệm sai.
  dich('en');

  // Rồi dữ liệu thật đổ vào, đúng như các hàm vẽ bảng vẫn làm.
  if (dungThe) o.innerHTML = '<span>DO-2026-0046-DO01</span><span>1.902.100 VNĐ</span>';
  else {
    // Tìm nút chữ sâu nhất rồi sửa thẳng nodeValue, đúng kiểu mã cập nhật số liệu.
    const w2 = w.document.createTreeWalker(o, w.NodeFilter.SHOW_TEXT, null, false);
    const nut = w2.nextNode();
    assert.ok(nut, nhan + ': không tìm thấy nút chữ nào trong ô chứa');
    nut.nodeValue = 'DO-2026-0046-DO01';
  }

  // Lượt dịch SAU (quan sát viên DOM vẫn gọi sau mỗi lần vẽ lại).
  dich('en');

  assert.ok(o.textContent.includes('DO-2026-0046-DO01'),
    nhan + ': dữ liệu vừa nạp bị bộ dịch ghi đè — còn lại "' + o.textContent.trim() + '"');
  assert.ok(!/Đang tải dữ liệu|Loading the data/i.test(o.textContent),
    nhan + ': chữ chờ cũ bị dựng lại đè lên dữ liệu');
}

chay('vẽ lại bằng innerHTML', true);
chay('sửa thẳng nodeValue', false);

// Và đổi ngôn ngữ nhiều lần liên tiếp cũng không được làm mất dữ liệu.
w.document.body.innerHTML = '<div id="o"><span>Chưa có dữ liệu</span></div>';
dich('en');
const o = w.document.getElementById('o');
o.innerHTML = '<span>DEMO-51C-777.01</span>';
['la', 'en', 'vi', 'la'].forEach(l => dich(l));
assert.ok(o.textContent.includes('DEMO-51C-777.01'),
  'đổi qua lại nhiều ngôn ngữ làm mất dữ liệu — còn lại "' + o.textContent.trim() + '"');

console.log('doi-ngon-ngu-khong-duoc-lam-mat-du-lieu: OK');
process.exit(0);

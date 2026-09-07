/**
 * Chạy toàn bộ bộ kiểm giao diện, in ra bài nào đỏ.
 *
 * Mỗi bài kiểm là một tệp node độc lập, không có framework. Chạy từng tệp
 * trong một tiến trình RIÊNG là có chủ đích: nhiều bài dùng `new Function(...)`
 * và `jsdom` để nạp app.js, nên gộp chung một tiến trình thì trạng thái của
 * bài này rò sang bài khác.
 *
 *     node tests/chay-tat-ca.js
 */
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const THU_MUC = __dirname;
const ds = fs.readdirSync(THU_MUC).filter(f => f.endsWith('.test.js')).sort();

const do_ = [];
let xanh = 0;

for (const ten of ds) {
  try {
    execFileSync(process.execPath, [path.join(THU_MUC, ten)], {
      stdio: 'pipe',
      timeout: 240000,
      encoding: 'utf8',
    });
    xanh += 1;
  } catch (loi) {
    // Chọn dòng CÓ LỜI, không phải dòng đầu tiên khớp chữ "Error". Dòng
    // `throw new AssertionError(obj);` là mã nguồn của chính node, luôn xuất
    // hiện trước lời báo thật, nên bắt nó là in ra một dòng vô ích.
    const dong = String((loi.stdout || '') + (loi.stderr || ''))
      .split('\n')
      .map(d => d.trim())
      .filter(Boolean)
      .find(d => /^(AssertionError|TypeError|ReferenceError|SyntaxError|Error)\b.*:\s*\S/.test(d))
      || (loi.signal ? `hết thời gian (${loi.signal})` : 'không rõ — chạy riêng tệp để xem');
    do_.push([ten, dong.slice(0, 200)]);
  }
}

console.log(`\n${xanh}/${ds.length} bài kiểm xanh`);
if (do_.length) {
  console.log(`\n${do_.length} bài ĐỎ:`);
  for (const [ten, vi_sao] of do_) console.log(`  ${ten}\n      ${vi_sao}`);
  process.exit(1);
}

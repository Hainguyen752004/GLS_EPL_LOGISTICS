const assert = require('assert');
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(root, 'js', 'app.js'), 'utf8');

assert.match(html, /id="dispatch-detail"[^>]*\bhidden\b/, 'Detail must be hidden before a DO is dropped.');
assert.doesNotMatch(html, /id="dispatch-tool-week"/, 'The old 7-day drawer entry must be removed.');
assert.doesNotMatch(html, /id="dispatch-tool-pane-week"/, 'The old 7-day drawer pane must be removed.');
// Ngan keo "Cong cu" da bo. No chi co mot muc la "Canh bao", ma khoi canh bao
// nay gio la COT THU BA thuong truc cua ban dieu phoi — de sau mot cai nut thi
// nguoi dieu phoi khong biet la hom nay con viec. Nen kiem hop dong moi: khoi
// canh bao nam trong luoi, va ngan keo khong con dau vet nao.
// Man Dieu phoi da dung lai theo ban mau `dispatch-v2-crew.html`, nen cot ba
// khong con mang lop `dispatch-workbench-pane` cua ban cu. Dieu CAN BAO VE thi
// khong doi: khoi ngoai le phai nam TRONG ban ba cot, khong nam trong ngan keo.
{
  const iBan = html.indexOf('<div class="board">');
  assert.ok(iBan > 0, 'Khong thay ban ba cot cua man Dieu phoi.');
  const ban = html.slice(iBan, html.indexOf('id="dispatch-step-modal"'));
  assert.ok(ban.includes('id="dispatch-exceptions-view"'),
    'Khoi ngoai le phai la mot cot cua ban dieu phoi.');
}
assert.match(html, /id="dispatch-calendar-conflicts"/,
  'Khoi ngoai le phai co cho de ve du lieu vao.');
['dispatch-tools-button', 'dispatch-tools-panel', 'dispatch-tool-drawer',
  'dispatch-tool-pane-alerts', 'openDispatchTool'].forEach((dauVet) => {
  assert.ok(!html.includes(dauVet), `index.html con dau vet ngan keo: ${dauVet}`);
  assert.ok(!app.includes(dauVet), `app.js con dau vet ngan keo: ${dauVet}`);
});
// Va cot DO phai HIEN SAN, khong con `hidden`: cau chu tren dau man hua
// "chon DO, doi chieu lich xe roi gan nguon luc ngay tren mot man hinh".
{
  // Cot DO phai HIEN SAN, khong con `hidden`. Moc doi tu `#dispatch-queue`
  // (ban cu) sang `#dispatch-do-list` (ban theo mau), nhung y nghia giu nguyen:
  // cau chu tren dau man hua "chon DO, doi chieu lich xe roi gan nguon luc
  // ngay tren mot man hinh".
  const i = html.indexOf('id="dispatch-do-list"');
  assert.ok(i > 0, 'Khong thay cot DO cho dieu phoi.');
  const the = html.slice(html.lastIndexOf('<', i), html.indexOf('>', i) + 1);
  assert.ok(!/\bhidden\b/.test(the), 'Cot DO cho dieu phoi phai hien san: ' + the);
}
assert.match(app, /window\.selectDispatchDO = function \(id, revealDetail = false\)/, 'DO selection must distinguish click from drop.');
assert.match(app, /if \(revealDetail\) openDispatchDetail/, 'Only a drop may reveal assignment details.');
assert.match(app, /window\.selectDispatchDO\(doId, true\)/, 'Drag and drop must reveal details after a valid target is chosen.');
assert.match(app, /detailEl\.hidden = !selectedDispatchCalendarOrderId \|\| !dispatchDetailUnlocked/, 'Detail visibility must be state-driven.');

console.log('TEST_26_8_P2_UI_OK');

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
assert.match(html, /id="dispatch-exceptions"[^>]*class="[^"]*dispatch-workbench-pane/,
  'Khoi ngoai le phai la mot cot cua ban dieu phoi.');
assert.match(html, /id="dispatch-calendar-conflicts"/,
  'Khoi ngoai le phai co cho de ve du lieu vao.');
['dispatch-tools-button', 'dispatch-tools-panel', 'dispatch-tool-drawer',
  'dispatch-tool-pane-alerts', 'openDispatchTool'].forEach((dauVet) => {
  assert.ok(!html.includes(dauVet), `index.html con dau vet ngan keo: ${dauVet}`);
  assert.ok(!app.includes(dauVet), `app.js con dau vet ngan keo: ${dauVet}`);
});
// Va cot DO phai HIEN SAN, khong con `hidden`: cau chu tren dau man hua
// "chon DO, doi chieu lich xe roi gan nguon luc ngay tren mot man hinh".
assert.doesNotMatch(html, /id="dispatch-queue"[^>]*\bhidden\b/,
  'Cot DO cho dieu phoi phai hien san.');
assert.match(app, /window\.selectDispatchDO = function \(id, revealDetail = false\)/, 'DO selection must distinguish click from drop.');
assert.match(app, /if \(revealDetail\) openDispatchDetail/, 'Only a drop may reveal assignment details.');
assert.match(app, /window\.selectDispatchDO\(doId, true\)/, 'Drag and drop must reveal details after a valid target is chosen.');
assert.match(app, /detailEl\.hidden = !selectedDispatchCalendarOrderId \|\| !dispatchDetailUnlocked/, 'Detail visibility must be state-driven.');

console.log('TEST_26_8_P2_UI_OK');

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(root, 'js', 'app.js'), 'utf8');

assert.match(html, /id="dispatch-detail"[^>]*\bhidden\b/, 'Detail must be hidden before a DO is dropped.');
assert.doesNotMatch(html, /id="dispatch-tool-week"/, 'The old 7-day drawer entry must be removed.');
assert.doesNotMatch(html, /id="dispatch-tool-pane-week"/, 'The old 7-day drawer pane must be removed.');
assert.match(app, /const allowed = \['alerts'\]/, 'Dispatch tools must keep only the alerts drawer.');
assert.match(app, /window\.selectDispatchDO = function \(id, revealDetail = false\)/, 'DO selection must distinguish click from drop.');
assert.match(app, /if \(revealDetail\) openDispatchDetail/, 'Only a drop may reveal assignment details.');
assert.match(app, /window\.selectDispatchDO\(doId, true\)/, 'Drag and drop must reveal details after a valid target is chosen.');
assert.match(app, /detailEl\.hidden = !selectedDispatchCalendarOrderId \|\| !dispatchDetailUnlocked/, 'Detail visibility must be state-driven.');

console.log('TEST_26_8_P2_UI_OK');

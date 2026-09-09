const assert = require('assert');
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(root, 'js', 'app.js'), 'utf8');

assert.match(html, /data-view="delivery-completion"/, 'Completion navigation module is missing.');
assert.match(html, /id="view-delivery-completion"/, 'Completion workbench is missing.');
assert.match(html, /id="completion-do-list"/, 'Pending/completed DO list is missing.');
assert.match(html, /id="completion-pod-fields"/, 'POD form region is missing.');
assert.match(html, /id="completion-do-details"/, 'Full read-only DO details region is missing.');
assert.match(html, /id="completion-charge-lines"/, 'Customer surcharge editor is missing.');
assert.match(html, /id="completion-final-total"/, 'Final DO total is missing.');
assert.match(html, /id="tracking-do-list"/, 'Tracking DO list is missing.');
// Truoc day khung POD cu chi bi `display:none` che di, va phep khang dinh o day
// chot dung trang thai "con nam do nhung bi che". Nay no da BO HAN khoi
// index.html, nen phep khang dinh manh hon: no khong duoc con ton tai. Duong
// tat "chon DO o man Theo doi roi nhay sang man Hoan tat" da chet tu lau vi bi
// che; man Hoan tat tu liet ke va tu mo bang soan nen khong mat duong nao.
assert.doesNotMatch(html, /id="legacy-tracking-pod-panel"/,
  'Legacy POD panel was removed from Tracking — it must not come back.');
assert.match(html, /id="tracking-closeout-panel" style="display:none;/, 'Legacy closeout must be hidden from Tracking.');

assert.match(app, /complete-delivery/, 'Frontend must call the atomic completion API.');
assert.match(app, /new FormData\(\)/, 'Completion must upload real multipart POD documents.');
assert.match(app, /data-pod="signature"/, 'Completion form needs a handwritten signature canvas.');
assert.match(app, /pointerdown/, 'Signature pad must support Pointer Events for mouse and touch.');
assert.match(app, /pointermove/, 'Signature pad must draw continuously on mouse and touch.');
assert.match(app, /toBlob/, 'Handwritten signature must be exported as a real image upload.');
assert.match(app, /signature_file_field/, 'Signature upload must be mapped to its POD entry.');
assert.match(app, /clearDeliverySignature/, 'User needs a clear-signature action.');
assert.match(app, /toggleDeliveryPodStop/, 'Delivery stops need a controlled expand/collapse action.');
assert.match(app, /completion-pod-stop\.expanded/, 'Only the selected delivery stop should remain expanded.');
assert.match(app, /data-completion-stop-toggle/, 'Each delivery stop needs a compact grid toggle.');
assert.match(app, /canvas\.dataset\.signatureInitialized/, 'Signature pads must not be reset after collapsing a stop.');
assert.match(app, /actual_amount:String/, 'Customer surcharge actual amount is missing.');
assert.match(app, /configured_cost_lines/, 'Configured vehicle costs must preload the finalization table.');
assert.match(app, /line\.source === 'configured'/, 'Configured and manually added cost lines need distinct behavior.');
assert.match(app, /Chi phí chốt ban đầu/, 'The table must explain the initial configured cost column.');
assert.match(app, /customer_surcharge_total/, 'Final customer surcharge is not rendered.');
assert.match(app, /completion-update-receipt/, 'Completed delivery must show where persisted data was updated.');
assert.match(app, /Hóa đơn phải thu/, 'Completed delivery must expose the posted AR invoice.');
assert.match(app, /data\.trip\?\.status/, 'Completed delivery must expose the persisted Trip status.');
assert.match(app, /data\.pod_documents/, 'Completed delivery must expose persisted POD and signature documents.');
assert.match(app, /data\.resource_release/, 'Completed delivery must expose released vehicle and driver state.');
assert.match(app, /showToast\(error\.message, 'error'\)/, 'Completion errors need explicit error severity.');
const legacyPodHandler = app.match(/window\.submitPOD\s*=\s*async function[\s\S]*?\n\};/);
assert.ok(legacyPodHandler, 'Missing compatibility POD handler.');
assert.doesNotMatch(legacyPodHandler[0], /\/api\/pod\//, 'Legacy POD handler must not persist through the non-atomic API.');
assert.doesNotMatch(legacyPodHandler[0], /\/api\/invoices\/post/, 'Legacy POD handler must not post a separate invoice.');
assert.match(app, /isGpsLiveTrackingStatus/, 'Tracking must filter live DO status.');
assert.match(
  app,
  /window\.viewCompletionDO\s*=\s*function\s*\(doId\)[\s\S]*?editFioriDO\(doId\)/,
  'View DO in delivery completion must open the full read-only DO form.'
);

console.log('DELIVERY_COMPLETION_UI_OK');

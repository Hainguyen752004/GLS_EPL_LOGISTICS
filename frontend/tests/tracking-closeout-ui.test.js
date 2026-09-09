const assert = require('assert');
const fs = require('fs');
const path = require('path');

const frontendRoot = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(frontendRoot, 'index.html'), 'utf8');
const appSource = fs.readFileSync(path.join(frontendRoot, 'js', 'app.js'), 'utf8');
const failures = [];

function check(name, assertion) {
  try {
    assertion();
  } catch (error) {
    failures.push(`${name}: ${error.message}`);
  }
}

check('tracking page exposes a separate closeout selector for delivered DOs', () => {
  assert.match(html, /id=["']tracking-closeout-do-select["']/, 'Missing closeout DO selector.');
  assert.match(html, /id=["']tracking-closeout-content["']/, 'Missing closeout render container.');
  assert.match(html, /loadDeliveryOrderCloseout\(this\.value\)/, 'Closeout selector must load selected DO.');
});

// Khoi kiem nay TRUOC DAY chot duong tat "chon DO o man Theo doi roi bam Mo ho
// so de nhay sang man Hoan tat" (`#legacy-tracking-pod-panel`,
// `#btn-open-pod-form`, `openPODFormForSelectedDO`). Duong tat do bi
// `display:none` che tu lau nen da chet trong thuc te — khong co nut nao nguoi
// dung thay duoc — va khoi markup cua no da bo khoi index.html.
//
// Dieu PHAI GIU lai la y nghia goc cua khoi kiem: man Theo doi khong duoc co
// mot form POD ghi khong vao dau, va bang chung giao hang phai di qua duong
// hoan tat co luu that. Hai phep khang dinh duoi day chot dung hai dieu do.
check('Tracking has no unpersisted POD form; completion lives on its own screen', () => {
  assert.doesNotMatch(html, /id=["']pod-entry-form["']/,
    'Tracking must not expose an unpersisted POD entry form.');
  assert.doesNotMatch(html, /id=["']btn-open-pod-form["']/,
    'The dead POD hand-off shortcut was removed — it must not come back.');
  assert.match(html, /id=["']view-delivery-completion["']/,
    'The persisted completion workflow must have its own screen.');
  assert.match(html, /id=["']completion-do-list["']/,
    'That screen must list delivery orders itself, so no hand-off shortcut is needed.');
  assert.match(appSource, /window\.submitPOD\s*=/,
    'The atomic completion submit must still exist.');
});

check('closeout selector uses delivered/completed status instead of GPS live status', () => {
  assert.match(appSource, /function\s+isCloseoutReadyStatus\s*\(/, 'Missing closeout status guard.');
  const selector = appSource.match(/function\s+populateCloseoutDOSelector\s*\([^)]*\)\s*\{[\s\S]*?\n\}/);
  assert.ok(selector, 'Missing populateCloseoutDOSelector().');
  assert.match(selector[0], /isCloseoutReadyStatus/, 'Closeout selector must filter delivered/completed DOs.');
  assert.doesNotMatch(selector[0], /isGpsLiveTrackingStatus/, 'Closeout selector must not reuse live GPS guard.');
});

check('closeout view fetches the real backend closeout API', () => {
  assert.match(appSource, /window\.loadDeliveryOrderCloseout\s*=\s*async\s*function/, 'Missing loadDeliveryOrderCloseout().');
  assert.match(appSource, /\/api\/delivery-orders\/\$\{encodeURIComponent\(doId\)\}\/closeout/, 'Closeout view must call backend closeout API.');
  assert.match(appSource, /renderDeliveryOrderCloseout/, 'Closeout response must be rendered.');
});

check('closeout view opens the actual cost editor for the selected DO and Trip', () => {
  assert.match(appSource, /window\.openCloseoutActualCostEditor\s*=\s*async\s*function/, 'Missing closeout actual-cost handoff.');
  assert.match(appSource, /data-closeout-cost-action/, 'Closeout must render an explicit actual-cost action button.');
  assert.match(appSource, /editFioriDO\(doId\)/, 'Actual-cost handoff must open the DO form for the selected DO.');
  assert.match(appSource, /dataset\.tripId\s*=\s*tripId/, 'Actual-cost handoff must bind the resolved Trip to the save button.');
  assert.match(appSource, /dataset\.refreshCloseoutDoId\s*=\s*doId/, 'Saving actual cost must know which closeout to refresh.');
});

check('saving actual cost from closeout refreshes the closeout price table', () => {
  assert.match(appSource, /refreshCloseoutDoId/, 'Missing closeout refresh marker on actual-cost save.');
  assert.match(appSource, /loadDeliveryOrderCloseout\(refreshCloseoutDoId\)/, 'Actual-cost save must reload closeout after server confirmation.');
});

check('legacy tracking POD action opens the atomic delivery completion workbench', () => {
  const podHandler = appSource.match(/window\.submitPOD\s*=\s*async function[\s\S]*?\n\};/);
  assert.ok(podHandler, 'Missing submitPOD handler.');
  assert.match(podHandler[0], /switchView\('delivery-completion'\)/, 'Legacy POD action must open the completion module.');
  assert.match(podHandler[0], /openDeliveryCompletionEditor\(doId\)/, 'Selected DO must open in the atomic completion editor.');
  assert.doesNotMatch(podHandler[0], /\/api\/pod\//, 'Legacy tracking must not write a partial POD record.');
  assert.doesNotMatch(podHandler[0], /\/api\/invoices\/post/, 'Legacy tracking must not post accounting separately.');
});

check('closeout POD cards expose persisted POD document names', () => {
  // Thẻ POD phải đọc BẢNG CHỨNG TỪ THẬT (`data.pod_documents`), không phải hai
  // cột `photo_url` / `signature_url` trên bản ghi POD.
  //
  // Hai cột đó là cột chết: `complete_delivery` không bao giờ ghi chúng — ảnh
  // và chữ ký nằm ở bảng `delivery_pod_documents`. Nên POD có đủ biên bản và
  // chữ ký vẫn hiển thị "Chưa đính kèm", trong khi `data.pod_documents` ngay
  // trong cùng response đó lại có hai dòng.
  //
  // Bài kiểm cũ khóa đúng cách làm sai: nó đòi có `pod.photo_url` và nhãn
  // "POD/hop dong". Ý định thì đúng (phải hiện chứng từ đã lưu), chỉ là nó
  // chốt vào đúng hai cột không có dữ liệu.
  assert.match(appSource, /function chungTuPOD/, 'Closeout must resolve POD evidence through a helper.');
  assert.match(
    appSource,
    /pod_documents \|\| \[\]\)\.filter\(doc =>[\s\S]{0,120}pod_record_id/,
    'Closeout must read the real POD documents table, keyed by pod_record_id.'
  );
  // Ý định của khẳng định này là: tên chứng từ đã lưu phải HIỆN RA. Bản trước
  // in ra một dòng chữ "Chứng từ: 2 tệp (...)"; bản này liệt kê từng tệp kèm
  // `download_url` nên mở được luôn — làm đúng ý định đó và làm hơn thế. Nên
  // khẳng định neo vào Ý ĐỊNH, không neo vào cách viết cũ.
  assert.match(appSource, /escapeCloseoutText\(t\.file_name \|\| t\.id\)/,
    'Closeout must show each persisted POD document name.');
  assert.match(appSource, /href="\$\{escapeCloseoutText\(t\.download_url/,
    'Each POD document must be openable through its stored download_url.');
  assert.match(appSource, /Chứng từ \(\$\{tep\.length\}\)/,
    'Closeout must still label the POD evidence block with a count.');
  // Vẫn đọc thêm hai cột cũ làm dự phòng, cho dữ liệu lịch sử từ bản trước.
  assert.match(appSource, /pod\?\.photo_url \|\| pod\?\.signature_url/, 'Legacy rows must still be shown.');
  // Và không được quay lại việc lấy hai cột đó làm nguồn chính.
  assert.doesNotMatch(
    appSource,
    /escapeCloseoutText\(pod\.photo_url \|\| pod\.signature_url \|\| 'Chua dinh kem'\)/,
    'Must not treat the dead columns as the primary source again.'
  );
});

if (failures.length) {
  throw new Error(`Tracking closeout UI contract is not implemented:\n- ${failures.join('\n- ')}`);
}

console.log('TRACKING_CLOSEOUT_UI_OK');

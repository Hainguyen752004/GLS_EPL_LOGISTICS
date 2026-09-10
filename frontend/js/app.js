const API_BASE = (typeof window !== 'undefined' && window.location && window.location.origin)
  ? window.location.origin
  : "http://127.0.0.1:8000";

let appState = {
  quotations: [],
  delivery_orders: [],
  routes: [],
  dispatches: [],
  invoices: [],
  incidents: [],
  vehicles: []
};

let appTranslations = {};
let currentLang = 'vi';
let eplCustomers = [];

function paginatedItems(payload) {
  return payload && Array.isArray(payload.items) ? payload.items : [];
}

async function fetchAllPaginated(url, pageSize = 200, options = {}) {
  const items = [];
  let page = 1;
  let total = Number.POSITIVE_INFINITY;
  while (items.length < total) {
    const separator = url.includes('?') ? '&' : '?';
    const response = await fetch(`${url}${separator}page=${page}&page_size=${pageSize}`, options);
    if (!response.ok) throw new Error(`HTTP ${response.status} while loading ${url}`);
    const payload = await response.json();
    const pageItems = paginatedItems(payload);
    items.push(...pageItems);
    total = Number.isFinite(Number(payload.total)) ? Number(payload.total) : items.length;
    if (!pageItems.length || pageItems.length < pageSize) break;
    page += 1;
  }
  return items;
}

const STATUS_LABELS_VI = {
  "Draft": "B\u1ea3n nh\u00e1p",
  "Lead": "Kh\u00e1ch ti\u1ec1m n\u0103ng",
  "Negotiation": "\u0110ang \u0111\u00e0m ph\u00e1n",
  "Quoted": "\u0110\u00e3 b\u00e1o gi\u00e1",
  "Approved": "\u0110\u00e3 duy\u1ec7t",
  "Confirmed": "\u0110\u00e3 x\u00e1c nh\u1eadn",
  "Won": "\u0110\u00e3 ch\u1ed1t",
  "Pending": "Ch\u1edd x\u1eed l\u00fd",
  "Pending Approval": "Ch\u1edd duy\u1ec7t",
  "Planned": "\u0110\u00e3 l\u1eadp k\u1ebf ho\u1ea1ch",
  "Picked": "\u0110\u00e3 l\u1ea5y h\u00e0ng",
  "Packed": "\u0110\u00e3 \u0111\u00f3ng g\u00f3i",
  "Ready for Dispatch": "S\u1eb5n s\u00e0ng \u0111i\u1ec1u ph\u1ed1i",
  "In Transit": "\u0110ang v\u1eadn chuy\u1ec3n",
  "Arrived": "\u0110\u00e3 \u0111\u1ebfn n\u01a1i",
  "Delivered": "\u0110\u00e3 giao h\u00e0ng",
  "Completed": "Ho\u00e0n t\u1ea5t",
  "Posted": "\u0110\u00e3 h\u1ea1ch to\u00e1n",
  "Maintenance": "B\u1ea3o d\u01b0\u1ee1ng",
  "Available": "S\u1eb5n s\u00e0ng",
  "Busy": "B\u1eadn",
  "Active": "\u0110ang ho\u1ea1t \u0111\u1ed9ng",
  "Inactive": "Ng\u01b0ng ho\u1ea1t \u0111\u1ed9ng",
  "Paid": "\u0110\u00e3 thanh to\u00e1n",
  "Unpaid": "Ch\u01b0a thanh to\u00e1n",
  "Cancelled": "\u0110\u00e3 h\u1ee7y"
};

function statusLabel(status) {
  if (!status) return "";
  if (window.WorkflowUIUtils && typeof window.WorkflowUIUtils.statusLabel === 'function') {
    return window.WorkflowUIUtils.statusLabel(status);
  }
  let text = String(status);
  Object.entries(STATUS_LABELS_VI).forEach(([en, vi]) => {
    text = text.replaceAll(en, vi);
  });
  return text;
}

function workflowStatusKeySafe(status) {
  if (window.WorkflowUIUtils && typeof window.WorkflowUIUtils.workflowStatusKey === 'function') {
    return window.WorkflowUIUtils.workflowStatusKey(status);
  }
  return String(status || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/Ä‘/g, 'd')
    .replace(/Đ/g, 'D')
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '_');
}

function contextualWorkflowStatusLabel(entity, status) {
  const key = workflowStatusKeySafe(status);
  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
  if (entity === 'quotation') {
    if (key === 'approved' || key === 'da_duyet') {
      if (lang === 'la') return 'ໃບສະເໜີລາຄາອະນຸມັດແລ້ວ';
      if (lang === 'en') return 'Approved Quotation';
      return 'Báo giá đã duyệt';
    }
    if (!key || key === 'draft' || key === 'ban_nhap') {
      if (lang === 'la') return 'à»ƒàºšàºªàº°à»€à»œàºµàº¥àº²àº„àº²àº®à»ˆàº²àº‡';
      if (lang === 'en') return 'Draft Quotation';
      return 'Báo giá nháp';
    }
    return `Báo giá ${statusLabel(status)}`;
  }
  return statusLabel(status);
}

function setFormLoadingState(formId, isLoading, message = 'Đang nạp dữ liệu...') {
  const form = document.getElementById(formId);
  if (!form) return;
  const dialog = form.firstElementChild || form;
  if (dialog && getComputedStyle(dialog).position === 'static') {
    dialog.style.position = 'relative';
  }
  let badge = form.querySelector('[data-form-loading-state]');
  if (!badge) {
    badge = document.createElement('div');
    badge.setAttribute('data-form-loading-state', '');
    badge.style.cssText = [
      'position:absolute',
      'right:86px',
      'top:22px',
      'z-index:20',
      'display:none',
      'align-items:center',
      'gap:8px',
      'padding:8px 12px',
      'border-radius:999px',
      'background:rgba(255,255,255,.18)',
      'color:#fff',
      'font-weight:800',
      'font-size:.84rem',
      'box-shadow:0 8px 20px rgba(15,23,42,.14)'
    ].join(';');
    dialog.appendChild(badge);
  }
  badge.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> ${message}`;
  badge.style.display = isLoading ? 'inline-flex' : 'none';
}

function fixUIText(value) {
  if (window.WorkflowUIUtils && typeof window.WorkflowUIUtils.fixVietnameseMojibake === 'function') {
    return window.WorkflowUIUtils.fixVietnameseMojibake(value);
  }
  return value;
}

function forceCriticalVietnameseLabels() {
  if (typeof document === 'undefined') return;
  if (typeof currentLang !== 'undefined' && currentLang !== 'vi') return;
  // CỐ Ý không còn lệnh ghi đè nào ở đây.
  //
  // Trước đây có ba lệnh nhắm vào `mega_finance_title`, `menu_accounting` và
  // `menu_fleet_catalog` — ba nhãn của "mega menu" cũ. Khung mới không còn
  // thẻ nào mang các khóa đó, nên ba lệnh ấy chỉ còn là chỗ để quên: đọc thì
  // tưởng nhãn được ghi đè, mà thật ra chúng không khớp gì cả.
  //
  // C\u1ed0 \u00dd kh\u00f4ng ghi \u0111\u00e8 `lbl_sales_rep` \u1edf \u0111\u00e2y.
  //
  // \u0110\u00e2y l\u00e0 h\u1ec7 th\u1ed1ng V\u1eacN T\u1ea2I, kh\u00f4ng ph\u1ea3i b\u00e1n h\u00e0ng h\u00f3a, n\u00ean d\u00f9ng t\u1eeb "Nh\u00e2n vi\u00ean
  // kinh doanh". lang.json v\u00e0 index.html \u0111\u1ec1u \u0111\u00e3 \u0111\u00fang; hai ch\u1ed7 ghi \u0111\u00e8 trong t\u1ec7p
  // n\u00e0y k\u00e9o ng\u01b0\u1ee3c v\u1ec1 "Nh\u00e2n Vi\u00ean B\u00e1n H\u00e0ng" \u2014 v\u00e0 v\u00ec h\u00e0m n\u00e0y ch\u1ea1y SAU
  // changeLanguage n\u00ean n\u00f3 LU\u00d4N th\u1eafng. S\u1eeda lang.json xong ch\u1eef tr\u00ean m\u00e0n h\u00ecnh v\u1eabn
  // y nh\u01b0 c\u0169.
  // CỐ Ý không còn bộ nhãn viết cứng ở đây.
  //
  // Trước đây chỗ này chép lại 16 nhãn của lang.json rồi ghi đè lên chúng —
  // một TẦNG NHÃN THỨ BA. Vì hàm này chạy SAU changeLanguage nên nó luôn
  // thắng, tức mọi lần sửa lang.json đều bị nó âm thầm hoàn tác. Đối chiếu
  // lúc gỡ: 14/16 nhãn đã trùng khớp y hệt lang.json (thừa hoàn toàn), và
  // đúng 2 nhãn còn lại — `lbl_route_stops` và `lbl_order_lines` — là chỗ nó
  // kéo ngược về chữ cũ sau khi lang.json đã được sửa cho đúng ngành vận tải.
  //
  // Nhãn nào cần sửa thì sửa trong lang.json và trong index.html. Hai tầng là
  // đủ; tầng thứ ba chỉ tạo ra một chỗ để quên.

  // Ô tìm và ô NVKD của form Đơn vận chuyển đã gỡ cùng bước SO (10/09).
}

function workflowActionMode(status, entity) {
  if (entity && window.WorkflowPresentation?.actionsForStatus) {
    const actions = window.WorkflowPresentation.actionsForStatus(entity, status);
    return { canView: actions.view, canEdit: actions.edit, canDelete: actions.delete };
  }
  if (window.WorkflowUIUtils && typeof window.WorkflowUIUtils.workflowActionMode === 'function') {
    return window.WorkflowUIUtils.workflowActionMode(status);
  }
  const st = String(status || '').toLowerCase();
  const locked = [
    'approved',
    'confirmed',
    'in transit',
    'delivered',
    'completed',
    'posted',
    'đã duyệt',
    'da duyet',
    'đã xác nhận',
    'da xac nhan',
    'đang vận chuyển',
    'dang van chuyen',
    'đã giao hàng',
    'da giao hang',
    'hoàn tất',
    'hoan tat'
  ].includes(st);
  return { canEdit: !locked, canDelete: !locked, canView: true };
}

function isWorkflowLocked(status) {
  return !workflowActionMode(status).canEdit;
}

function canonicalDOStatusValue(order) {
  const status = order?.canonical_status || order?.status || 'pending';
  const key = window.WorkflowUIUtils?.workflowStatusKey?.(status) || String(status).toLowerCase().trim();
  const map = {
    pending: 'Pending',
    planned: 'Pending',
    approved: 'Pending',
    in_transit: 'In Transit',
    delivered: 'Delivered',
    completed: 'Delivered',
    cancelled: 'Cancelled'
  };
  return map[key] || 'Pending';
}

async function loadTranslations() {
  try {
    const res = await fetch(`${API_BASE}/static/js/lang.json?v=20260908g-dieu-phoi`);
    appTranslations = await res.json();
    appTranslations.menu_accounting = appTranslations.menu_accounting || {};
    appTranslations.menu_accounting.vi = '6. Kế toán & Tài chính';
    appTranslations.menu_fleet_catalog = appTranslations.menu_fleet_catalog || {};
    appTranslations.menu_fleet_catalog.vi = 'Danh Mục Đội Xe';
    // C\u1ed0 \u00dd kh\u00f4ng ghi \u0111\u00e8 `lbl_sales_rep` \u1edf \u0111\u00e2y \u2014 xem gi\u1ea3i th\u00edch \u1edf
    // forceCriticalVietnameseLabels(). lang.json \u0111\u00e3 c\u00f3 "Nh\u00e2n vi\u00ean kinh doanh".
    // Khoi tao theo ngon ngu dang chon tren nut doi ngon ngu (data-lang o goc #epl-lang).
    const nutNgonNgu = document.getElementById('epl-lang');
    if (nutNgonNgu) changeLanguage(nutNgonNgu.dataset.lang || 'vi');
  } catch (e) {
    // Không có lang.json thì `appTranslations` rỗng, và `changeLanguage` có
    // `if (!value) return;` cho từng khóa — nên gạt sang tiếng Lào hay tiếng
    // Anh sẽ KHÔNG đổi được một chữ nào, mà cũng không báo gì. Người dùng
    // bấm đi bấm lại cái ô chọn ngôn ngữ và tưởng nó hỏng.
    baoNapThatBai('bản dịch giao diện', e);
  }
}



// escapeHtml và escapeJsAttr đến từ js/format-utils.js (nạp trước file này).
// Trước đây chúng được định nghĩa lại ở đây, và app.js nạp sau nên bản ở đây
// ghi đè bản của module — hai bản giống nhau nên không đổi hành vi, nhưng có
// hai nguồn cho cùng một hàm là chỗ để chúng trôi khỏi nhau.

/**
 * Bao ra khi may chu tu choi mot thao tac.
 *
 * Nhieu cho trong tep nay viet `if (res.ok) { ... }` ma KHONG co nhanh else,
 * con `catch` thi chi `console.error`. He qua: bam "Xoa" mot khach hang khi
 * may chu tu choi (409 vi con don tham chieu) thi KHONG CO GI XAY RA va khong
 * mot thong bao nao — hang van nam do, nguoi dung bam lai.
 *
 * Phong bi loi cua may chu la `{error: {code, message}, detail}`, KHONG co
 * khoa `message` o cap cao nhat — nen `data.message` luon undefined. Ham nay
 * doc dung ba lop do.
 *
 * Tra ve `false` de goi duoc dang `if (!res.ok) return baoLoiMayChu(...)`.
 */
async function baoLoiMayChu(res, viec) {
  let chi_tiet = '';
  try {
    const data = await res.json();
    chi_tiet = data?.error?.message || data?.detail || data?.message || '';
    if (chi_tiet && typeof chi_tiet !== 'string') chi_tiet = JSON.stringify(chi_tiet);
  } catch (e) {
    // Than phan hoi khong phai JSON. Ma trang thai van du de noi that bai.
  }
  if (!chi_tiet) {
    chi_tiet = res.status === 401 || res.status === 403
      ? 'Không có quyền thực hiện thao tác này.'
      : `Máy chủ trả lỗi HTTP ${res.status}.`;
  }
  showToast(`❌ ${viec} không thành công: ${chi_tiet}`);
  return false;
}
window.baoLoiMayChu = baoLoiMayChu;

/** Bao ra khi khong ket noi duoc toi may chu. */
function baoMatKetNoi(viec, loi) {
  console.error(viec, loi);
  showToast(`❌ Không kết nối được tới máy chủ. ${viec} CHƯA được thực hiện.`);
  return false;
}
window.baoMatKetNoi = baoMatKetNoi;

/* ==========================================================================
   Nạp danh sách thất bại thì phải NÓI RA.

   Mười tám chỗ trong tệp này từng bắt lỗi rồi chỉ `console.error(...)`. Hậu
   quả không phải là "mất một tính năng" mà là NÓI SAI: `loadDeliveryOrders` hỏng
   thì `eplDeliveryOrders` GIỮ NGUYÊN giá trị cũ và không vẽ lại gì cả, nên màn
   hình vẫn hiện danh sách của lần nạp trước như thể đó là dữ liệu hiện tại.
   Còn khi chưa nạp được lần nào thì mảng rỗng, và hàm vẽ hiện đúng dòng
   "Chưa có dữ liệu" — người dùng đọc thành "công ty chưa có đơn nào", trong
   khi sự thật là máy chủ đang không trả lời.

   Vì sao gom lại thay vì mỗi chỗ một toast: `showToast` XÓA toast cũ trước
   khi hiện toast mới (xem ngay bên dưới). Mở màn hình là hàng chục hàm nạp
   chạy song song, nên mất mạng sẽ bắn ra hàng chục lời báo giống nhau, chín
   cái đầu nhấp nháy rồi biến mất và chỉ cái cuối cùng ở lại — mà cái cuối
   cùng thường là thứ ít quan trọng nhất.
   ========================================================================== */

const dsNapThatBai = new Set();
let henBaoNapThatBai = null;

function baoNapThatBai(viec, loi) {
  console.error('Nạp thất bại: ' + viec, loi);
  dsNapThatBai.add(viec);
  clearTimeout(henBaoNapThatBai);
  henBaoNapThatBai = setTimeout(() => {
    const ds = [...dsNapThatBai];
    dsNapThatBai.clear();
    const ten = ds.length > 3
      ? `${ds.slice(0, 3).join(', ')} và ${ds.length - 3} mục khác`
      : ds.join(', ');
    showToast(
      `⚠️ Không nạp được ${ten}. Số liệu đang hiện có thể là bản cũ hoặc thiếu`
      + ` — đừng dựa vào nó để quyết định. Kiểm tra kết nối rồi tải lại trang.`,
      'warning'
    );
  }, 400);
  return false;
}
window.baoNapThatBai = baoNapThatBai;

window.showToast = function (msg) {
  const severity = arguments[1];
  msg = fixUIText(msg);
  document.querySelectorAll('[data-app-toast]').forEach(el => el.remove());
  const toast = document.createElement('div');
  const inferred = /⏳|đang|dang/i.test(String(msg || '')) ? 'loading'
    : /⚠/u.test(String(msg || '')) ? 'warning'
      : /error|lỗi|loi|failed|fail/i.test(String(msg || '')) ? 'error' : 'success';
  const kind = ['success','info','warning','error','loading'].includes(severity) ? severity : inferred;
  const tones = {
    success: { title: 'Đã hoàn tất', icon: 'fa-check', color: '#087a57', soft: '#eaf9f2', border: '#7ad6b4', progress: '#0ea978' },
    info: { title: 'Thông tin', icon: 'fa-circle-info', color: '#086ac1', soft: '#edf6ff', border: '#9bc7ed', progress: '#1684d8' },
    warning: { title: 'Cần bổ sung', icon: 'fa-triangle-exclamation', color: '#a85b00', soft: '#fff7e8', border: '#edc078', progress: '#e58a16' },
    error: { title: 'Không thể thực hiện', icon: 'fa-circle-xmark', color: '#c92d39', soft: '#fff0f1', border: '#ef9fa6', progress: '#dd4050' },
    loading: { title: 'Đang xử lý', icon: 'fa-spinner fa-spin', color: '#086ac1', soft: '#edf6ff', border: '#9bc7ed', progress: '#1684d8' }
  };
  const tone = tones[kind];
  const cleanMessage = String(msg || '')
    .replace(/^[✅🎉📁📂⏳⚠️⚠🚀]\s*/u, '')
    .trim();
  toast.setAttribute('data-app-toast', 'top-right');
  toast.setAttribute('role', 'status');
  toast.setAttribute('aria-live', 'polite');
  toast.innerHTML = `
    <div data-toast-icon-badge style="width:32px; height:32px; border-radius:999px; display:grid; place-items:center; flex:0 0 auto; background:${tone.soft}; border:1px solid ${tone.border};">
      <i class="fa-solid ${tone.icon}" style="color:${tone.color}; font-size:.82rem;"></i>
    </div>
    <div data-toast-copy style="display:flex; align-items:baseline; gap:6px; flex-wrap:wrap; min-width:0; flex:1;">
      <span data-toast-title style="font-size:.72rem; line-height:1.2; letter-spacing:0; color:${tone.color}; font-weight:900; white-space:nowrap;">${tone.title}</span>
      <span aria-hidden="true" style="color:#a8b2c1; font-size:.78rem;">•</span>
      <span data-toast-body style="min-width:150px; flex:1; font-size:.88rem; line-height:1.3; color:#172033; font-weight:700; overflow-wrap:anywhere;"></span>
    </div>
    <button type="button" data-toast-close aria-label="Đóng thông báo" onclick="this.closest('[data-app-toast]').remove()" style="width:28px; height:28px; border:0; border-radius:7px; background:#f1f5f9; color:#64748b; display:grid; place-items:center; cursor:pointer; flex:0 0 auto;">
      <i class="fa-solid fa-xmark"></i>
    </button>
    <div data-toast-progress style="position:absolute; left:0; right:0; bottom:0; height:3px; background:linear-gradient(90deg, ${tone.progress}, rgba(255,255,255,.1)); transform-origin:left center; animation:toastProgress 3s linear forwards;"></div>
  `;
  // Nội dung thông báo đặt qua textContent, KHÔNG nội suy vào innerHTML.
  // showToast nhận cả tên bản ghi do người ngoài đặt và error.message từ
  // server, nên nội suy thẳng vào HTML biến mọi tên thành script — và đây là
  // sink dùng ở khắp ứng dụng nên là chỗ đáng bịt trước tiên.
  const toastBody = toast.querySelector('[data-toast-body]');
  if (toastBody) toastBody.textContent = cleanMessage;

  toast.style.position = 'fixed';
  toast.style.top = 'calc(var(--header-height, 72px) + 12px)';
  toast.style.right = '20px';
  toast.style.transform = 'translateY(-10px) scale(0.98)';
  toast.style.background = 'rgba(255, 255, 255, 0.98)';
  toast.style.color = '#0f172a';
  toast.style.padding = '9px 10px 11px';
  toast.style.borderRadius = '8px';
  toast.style.border = '1px solid #dce3ec';
  toast.style.borderLeft = `3px solid ${tone.progress}`;
  toast.style.boxShadow = '0 10px 24px rgba(15, 23, 42, 0.13), 0 2px 7px rgba(15, 23, 42, 0.06)';
  toast.style.fontFamily = 'inherit';
  toast.style.fontSize = '0.95rem';
  toast.style.fontWeight = '800';
  toast.style.lineHeight = '1.35';
  toast.style.zIndex = '2147483647';
  toast.style.opacity = '0';
  toast.style.transition = 'opacity 0.22s ease, transform 0.22s ease';
  toast.style.display = 'flex';
  toast.style.alignItems = 'center';
  toast.style.gap = '9px';
  toast.style.width = 'min(390px, calc(100vw - 24px))';
  toast.style.maxWidth = 'min(390px, calc(100vw - 24px))';
  toast.style.maxHeight = 'calc(100vh - 32px)';
  toast.style.textAlign = 'left';
  toast.style.pointerEvents = 'auto';
  toast.style.overflow = 'hidden';
  toast.style.backdropFilter = 'blur(14px)';

  document.body.appendChild(toast);
  if (!document.getElementById('toast-progress-style')) {
    const style = document.createElement('style');
    style.id = 'toast-progress-style';
    style.textContent = `
      @keyframes toastProgress { from { transform:scaleX(1); } to { transform:scaleX(0); } }
      @media (max-width: 600px) {
        [data-app-toast="top-right"] {
          top: calc(var(--header-height, 72px) + 8px) !important;
          right: 12px !important;
          left: 12px !important;
          width: auto !important;
          max-width: none !important;
        }
      }
    `;
    document.head.appendChild(style);
  }

  setTimeout(() => {
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0) scale(1)';
  }, 10);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-8px) scale(0.98)';
    setTimeout(() => toast.remove(), 300);
  }, kind === 'loading' ? 6000 : 3800);
};

function getViTranslationMap() {
  if (window._viTranslationMap && window._viTranslationMapLangCount === Object.keys(appTranslations).length) {
    return window._viTranslationMap;
  }
  const map = new Map();
  if (typeof appTranslations === 'object') {
    Object.keys(appTranslations).forEach(k => {
      const entry = appTranslations[k];
      if (entry) {
        if (entry.vi) map.set(entry.vi.trim().toLowerCase(), entry);
        if (entry.en) map.set(entry.en.trim().toLowerCase(), entry);
      }
    });
  }
  window._viTranslationMap = map;
  window._viTranslationMapLangCount = Object.keys(appTranslations).length;
  return map;
}

let _transDebounceTimer = null;
let _isTranslating = false;

function translateAllDOMTexts(lang) {
  if (_isTranslating) return;
  const viMap = getViTranslationMap();
  if (!viMap || viMap.size === 0) return;

  _isTranslating = true;
  try {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
    let node;
    while ((node = walker.nextNode())) {
      const parent = node.parentElement;
      if (!parent) continue;
      const tagName = parent.tagName;
      if (tagName === 'SCRIPT' || tagName === 'STYLE' || tagName === 'CODE' || tagName === 'NOSCRIPT') continue;
      if (parent.closest('[data-i18n]')) continue;

      if (node._origText === undefined) {
        node._origText = node.nodeValue;
      }
      const orig = node._origText;
      if (!orig) continue;
      const trimmed = orig.trim();
      if (trimmed.length < 2) continue;
      if (/^\d+([\.,]\d+)*\s*(VNĐ|USD|LAK|THB|%|min|m|h)?$/.test(trimmed)) continue;

      if (lang === 'vi') {
        node.nodeValue = orig;
        continue;
      }

      let entry = viMap.get(trimmed.toLowerCase());
      if (entry && entry[lang]) {
        node.nodeValue = orig.replace(trimmed, fixUIText(entry[lang]));
      } else {
        let modified = orig;
        if (!window._sortedViKeys || window._sortedViKeysLang !== lang) {
          window._sortedViKeys = Array.from(viMap.entries())
            .filter(([k, v]) => k.length >= 4 && v[lang])
            .sort((a, b) => b[0].length - a[0].length);
          window._sortedViKeysLang = lang;
        }
        for (const [k, v] of window._sortedViKeys) {
          if (v[lang] && modified.toLowerCase().includes(k)) {
            const regex = new RegExp(k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
            modified = modified.replace(regex, fixUIText(v[lang]));
          }
        }
        if (modified !== orig) {
          node.nodeValue = modified;
        }
      }
    }

    document.querySelectorAll('input[placeholder], textarea[placeholder]').forEach(input => {
      if (input.hasAttribute('data-i18n')) return;
      if (!input.dataset.origPh) input.dataset.origPh = input.getAttribute('placeholder');
      const orig = input.dataset.origPh;
      if (!orig) return;
      if (lang === 'vi') {
        input.setAttribute('placeholder', orig);
        return;
      }
      const entry = viMap.get(orig.trim().toLowerCase());
      if (entry && entry[lang]) {
        input.setAttribute('placeholder', fixUIText(entry[lang]));
      }
    });

    document.querySelectorAll('select option').forEach(opt => {
      if (opt.hasAttribute('data-i18n')) return;
      if (!opt.dataset.origText) opt.dataset.origText = opt.textContent.trim();
      const orig = opt.dataset.origText;
      if (!orig) return;
      if (lang === 'vi') {
        opt.textContent = orig;
        return;
      }
      const entry = viMap.get(orig.toLowerCase());
      if (entry && entry[lang]) {
        opt.textContent = fixUIText(entry[lang]);
      }
    });
  } catch (err) {
    // CỐ Ý chỉ ghi console. Đây không phải lỗi nạp dữ liệu mà là lỗi trong
    // chính vòng dịch: chữ đã dịch được thì vẫn nằm trên màn, phần còn lại
    // giữ nguyên ngôn ngữ cũ. Bắn toast ở đây là bắn mỗi lần đổi ngôn ngữ,
    // trong khi người dùng nhìn màn hình đã thấy ngay chỗ nào chưa dịch.
    console.error('Translation error:', err);
  } finally {
    _isTranslating = false;
  }
}

if (typeof MutationObserver !== 'undefined') {
  const observer = new MutationObserver(() => {
    if (typeof currentLang !== 'undefined' && currentLang !== 'vi') {
      clearTimeout(_transDebounceTimer);
      _transDebounceTimer = setTimeout(() => {
        translateAllDOMTexts(currentLang);
      }, 100);
    }
  });
  window.addEventListener('DOMContentLoaded', () => {
    observer.observe(document.body, { childList: true, subtree: true });
  });
}

window.changeLanguage = function (lang) {
  currentLang = lang;
  document.documentElement.lang = lang === 'la' ? 'lo' : lang;
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    const value = appTranslations[key] && appTranslations[key][lang];
    if (!value) return;
    const cleanValue = fixUIText(value);
    const attr = el.getAttribute('data-i18n-attr');
    if (attr) el.setAttribute(attr, cleanValue);
    else if (el.tagName === 'INPUT' && el.type !== 'button' && el.hasAttribute('placeholder')) el.setAttribute('placeholder', cleanValue);
    else if (el.tagName === 'OPTION') el.textContent = cleanValue;
    else if (el.querySelector('input, select, textarea')) {
      // The nay BOC mot o nhap. Gan innerHTML se XOA MAT o nhap do — dung loi
      // da xay ra o tab "Quy cach van chuyen" cua don hang van chuyen: sau khi
      // dich xong, sau nhan con lai tro tro, khong con o nao de dien.
      //
      // Chi doi node VAN BAN dau tien, giu nguyen moi the con.
      const textNode = [...el.childNodes].find(node => node.nodeType === 3 && node.textContent.trim());
      if (textNode) textNode.textContent = cleanValue;
      else el.insertBefore(document.createTextNode(cleanValue), el.firstChild);
    }
    else el.innerHTML = cleanValue;
  });
  translateAllDOMTexts(lang);
  if (typeof updateActiveFlowStep === 'function') {
    updateActiveFlowStep(window.currentWorkflowStep !== undefined ? window.currentWorkflowStep : 1, false);
  }
  if (typeof installEnterpriseModuleTabs === 'function') installEnterpriseModuleTabs();
  if (typeof renderOracleQTList === 'function' && typeof crmQuotations !== 'undefined') renderOracleQTList(crmQuotations);
  if (typeof renderMasterDataCommandCenter === 'function') renderMasterDataCommandCenter();
  if (typeof renderDynamicFormulaVehicleTypes === 'function') renderDynamicFormulaVehicleTypes();
  if (typeof renderFioriVehicles === 'function' && typeof fioriVehicles !== 'undefined') renderFioriVehicles(fioriVehicles);
  if (typeof renderFioriDrivers === 'function' && typeof fioriDrivers !== 'undefined') renderFioriDrivers(fioriDrivers);
  if (typeof syncAllDynamicDropdowns === 'function') syncAllDynamicDropdowns();

  if (Object.keys(appTranslations).length > 0) {
    showToast(t(`lang_changed_${lang}`));
    if (typeof renderAllTables === 'function') renderAllTables();
    if (typeof loadDashboard === 'function') loadDashboard();
    if (currentLang === 'vi') {
      forceCriticalVietnameseLabels();
    }
  }
};

window.t = function (key) {
  return (appTranslations[key] && appTranslations[key][currentLang]) ? appTranslations[key][currentLang] : key;
};

function initNavigation() {
  window.addEventListener("click", (e) => {
    // Bỏ qua mọi thao tác trên phần tử tương tác. Tám thẻ .master-form-card
    // trong Bảng điều khiển vừa mang data-view vừa chứa form thật, nên nếu
    // không lọc thì người dùng bấm vào ô nhập hay nút Gửi trong form "Incident
    // Report" sẽ bị chuyển thẳng sang màn "Báo cáo & Phân tích" trước khi form
    // kịp xử lý. Listener này chạy ở capture phase trên window nên nó chặn
    // trước cả handler của chính phần tử đó.
    if (e.target.closest("input, select, textarea, button, a, label, [contenteditable='true']")) {
      return;
    }
    const viewItem = e.target.closest("[data-view]");
    if (viewItem) {
      const targetView = viewItem.getAttribute("data-view");
      if (targetView) {
        window.switchView(targetView);
      }
    }
  }, true);
}

document.addEventListener("DOMContentLoaded", async () => {
  // Dời hộp thoại toàn màn ra ngoài khung màn TRƯỚC khi người dùng bấm được
  // gì — nếu để muộn hơn thì lần bấm đầu tiên vẫn không hiện.
  duaHopThoaiRaNgoaiKhungMan();
  apDungTrangThaiGoiY();
  initNavigation();
  initAIDrawer();
  if (typeof installEnterpriseModuleTabs === 'function') installEnterpriseModuleTabs();
  await loadTranslations();
  renderStats();
  await loadAllData();
  if (typeof currentLang !== 'undefined' && currentLang === 'vi') {
    forceCriticalVietnameseLabels();
  }
  if (typeof window.loadRoutePlanningDropdown === 'function') {
    window.loadRoutePlanningDropdown();
  }
  setTimeout(() => {
    if (typeof window.loadRoutePlanningDropdown === 'function') {
      window.loadRoutePlanningDropdown();
    }
  }, 500);
});

window.currentWorkflowStep = 0;

const workflowStepsData = {
  0: { id: 'step-0', view: 'master-data', title: '0. Master Data & thiết lập nền', role: 'Admin / System Data Manager', db: 'vehicles, drivers, routes, cost_formulas', icon: 'fa-database' },
  1: { id: 'step-1', view: 'co-hoi', title: '1. Khách hàng & cơ hội', role: 'Sales / CRM', db: 'crm_opportunities', icon: 'fa-handshake' },
  2: { id: 'step-2', view: 'crm-sales', title: '2. Báo giá cước (Quotation)', role: 'Pricing / Sales Rep', db: 'quotations', icon: 'fa-file-contract' },
  3: { id: 'step-3', view: 'ops-planning', title: '3. Lệnh giao hàng (Delivery Order)', role: 'Kho / Điều phối', db: 'delivery_orders', icon: 'fa-clipboard-check' },
  4: { id: 'step-4', view: 'ops-planning', title: '4. Kế hoạch tuyến đường (Route)', role: 'Planner / Route Ops', db: 'routes', icon: 'fa-route' },
  5: { id: 'step-5', view: 'dispatch', title: '5. Lập lịch & điều phối (Dispatch)', role: 'Fleet Dispatcher', db: 'delivery_orders', icon: 'fa-truck-ramp-box' },
  6: { id: 'step-6', view: 'tracking', title: '6. Giám sát GPS & ký nhận POD', role: 'Driver & GPS Monitor', db: 'vehicle_tracking, pod', icon: 'fa-location-crosshairs' },
  7: { id: 'step-7', view: 'accounting', title: '7. Hóa đơn & kế toán (Invoice & GL)', role: 'Chief Accountant', db: 'ar_invoices, gl_transactions', icon: 'fa-file-invoice-dollar' }
};

window.updateActiveFlowStep = function (stepNum, showToastMsg = false) {
  if (stepNum < 0 || stepNum > 7) return;
  window.currentWorkflowStep = stepNum;
  const s = workflowStepsData[stepNum];

  // Dynamic translated title
  const stepKey = `flow_step_${stepNum}_title`;
  const stepTitle = (typeof t === 'function' && t(stepKey) !== stepKey) ? t(stepKey) : s.title;

  let prefix = '';
  let navText = '';
  if (typeof currentLang !== 'undefined' && currentLang === 'la') {
    prefix = stepNum === 0 ? 'ຂັ້ນຕອນເລີ່ມຕົ້ນ 0/7' : `ຂັ້ນຕອນ ${stepNum}/7`;
    navText = stepNum === 0 ? 'ຂັ້ນຕອນ 0 (MASTER DATA)' : `ຂັ້ນຕອນ ${stepNum}/7`;
  } else if (typeof currentLang !== 'undefined' && currentLang === 'en') {
    prefix = stepNum === 0 ? 'Prerequisite Step 0/7' : `Step ${stepNum}/7`;
    navText = stepNum === 0 ? 'STEP 0 (MASTER DATA)' : `STEP ${stepNum}/7`;
  } else {
    prefix = stepNum === 0 ? 'Bước tiền đề 0/7' : `Bước ${stepNum}/7`;
    navText = stepNum === 0 ? 'BƯỚC 0 (MASTER DATA)' : `BƯỚC ${stepNum}/7`;
  }

  // Update navbar badge
  const navBadge = document.getElementById('flow-badge-step-nav');
  if (navBadge) navBadge.innerText = navText;

  // Update top sticky tracker bar title
  const topTrackerStepText = document.getElementById('top-tracker-step-title');
  if (topTrackerStepText) {
    topTrackerStepText.innerHTML = `<i class="fa-solid ${s.icon}"></i><span><strong>${prefix}:</strong> ${stepTitle}</span>`;
  }

  // Update top sticky tracker bar mini step items
  document.querySelectorAll('.flow-bar-step-item').forEach((item) => {
    const itemStep = parseInt(item.getAttribute('data-step') || '-1');
    if (itemStep === stepNum) {
      item.classList.add('active');
      item.classList.remove('completed');
    } else if (itemStep < stepNum) {
      item.classList.add('completed');
      item.classList.remove('active');
    } else {
      item.classList.remove('active', 'completed');
    }
  });

  // Highlight active card on Sơ Đồ Luồng A-Z view
  document.querySelectorAll('.flow-diagram-card').forEach((card) => {
    const cardStep = parseInt(card.getAttribute('data-step') || '-1');
    if (cardStep === stepNum) {
      card.classList.add('active-step-card');
    } else {
      card.classList.remove('active-step-card');
    }
  });

  if (showToastMsg) {
    showToast(`🎯 ${prefix}: ${stepTitle}`);
  }
};

/* ==========================================================================
   Hộp thoại toàn màn phải nằm NGOÀI mọi khung màn.

   `switchView` đặt `display:none` cho mọi khung màn không hoạt động. Một
   phần tử `position: fixed` nằm trong tổ tiên `display:none` thì KHÔNG được
   vẽ ra — dù chính nó đã `display:flex`. Nên bất kỳ nút nào ở màn A mở hộp
   thoại nằm trong màn B đều "bấm không ăn gì": hàm chạy đúng, hộp thoại mở
   đúng, mà người dùng không thấy gì cả.

   Đó chính là nút "Xem DO" ở màn Hoàn tất giao — nó gọi `editFioriDO`, mà
   `#fiori-do-form` lại nằm trong `#view-ops-planning`.

   Quét cả trang thì CHÍN hộp thoại đều bị giam như vậy. Dời chúng ra
   `<body>` bằng JS lúc nạp trang, thay vì cắt dán trong 570 KB HTML: cách
   này giữ nguyên mọi id, mọi `onclick` viết thẳng trong thẻ, và mọi luật
   CSS. Đã kiểm trước hai điều kiện an toàn — không luật CSS nào neo chúng
   qua tổ tiên là khung màn, và không selector nào trong JS phạm vi theo
   `#view-*`.
   ========================================================================== */

const HOP_THOAI_TOAN_MAN = [
  'route-detail-modal',    // Sơ đồ lộ trình — trong #view-ops-planning
  'fiori-do-form',         // Lệnh giao hàng — trong #view-ops-planning
  'incident-form-panel',   // Báo sự cố — trong #view-tracking
  'veh-type-form-panel',   // Loại xe — trong #view-master-data
  'fiori-object-page',     // Phương tiện — trong #view-master-data
  'driver-modal-dialog',   // Tài xế — trong #view-master-data
  'customer-form-modal',   // Khách hàng — trong #view-master-data
];

function duaHopThoaiRaNgoaiKhungMan() {
  const daDoi = [];
  HOP_THOAI_TOAN_MAN.forEach(ma => {
    const el = document.getElementById(ma);
    if (!el) return;
    if (!el.closest('.view-section')) return;   // đã ở ngoài rồi
    document.body.appendChild(el);
    daDoi.push(ma);
  });
  return daDoi;
}
window.switchView = function (targetView, scrollToId) {
  if (!targetView) return;
  const viewAliases = {
    overview: 'dashboard',
    crm: 'co-hoi',
    'sales-orders': 'crm-sales',
    tender: 'accounting',
    // Không có màn hình nào tên "transportation". Trip Return Cockpit — nơi
    // người dùng chọn Trip — nằm trong #view-delivery-shipment. Trước đây hai
    // lời gọi switchView('transportation') trong luồng điều phối chỉ hiện
    // thông báo "không tìm thấy màn hình", nên hệ thống bảo người dùng đi mở
    // Trip rồi lại không đưa họ tới được.
    transportation: 'delivery-shipment'
  };
  targetView = viewAliases[targetView] || targetView;
  const targetSection = document.getElementById(`view-${targetView}`);
  if (!targetSection) {
    if (typeof showToast === 'function') {
      showToast(`Không tìm thấy màn hình "${targetView}". Vui lòng tải lại trang hoặc liên hệ quản trị hệ thống.`);
    }
    return false;
  }

  const viewToStep = {
    'dashboard': 0,
    'master-data': 0,
    'co-hoi': 1,
    'crm-sales': 1,
    'parking-list': 3,
    'delivery-shipment': 3,
    'ops-planning': 4,
    'dispatch': 5,
    'delivery-completion': 6,
    'tracking': 6,
    'operations-360': 6,
    'accounting': 7
  };
  if (viewToStep[targetView] !== undefined) {
    window.updateActiveFlowStep(viewToStep[targetView], false);
  }

  document.querySelectorAll(".mega-card").forEach(nav => {
    if (nav.getAttribute("data-view") === targetView) {
      nav.classList.add("active");
    } else {
      nav.classList.remove("active");
    }
  });

  const viewSections = document.querySelectorAll(".view-section");
  let found = false;
  viewSections.forEach(sec => {
    if (sec.id === `view-${targetView}`) {
      sec.classList.add("active");
      sec.style.display = "block";
      found = true;
    } else {
      sec.classList.remove("active");
      sec.style.display = "none";
    }
  });

  if (found) {
    if (typeof installEnterpriseModuleTabs === 'function') {
      setTimeout(() => {
        installEnterpriseModuleTabs();
        selectEnterpriseTabForTarget(scrollToId);
      }, 40);
    }
    if (scrollToId) {
      setTimeout(() => {
        selectEnterpriseTabForTarget(scrollToId);
        const targetEl = document.getElementById(scrollToId);
        if (targetEl) targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 60);
    } else {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }

  const titleText = document.getElementById("page-title-text");
  if (titleText) {
    const activeNav = document.querySelector(`.mega-card[data-view="${targetView}"] span`);
    if (activeNav) {
      titleText.textContent = activeNav.textContent;
    }
  }

  if (typeof translateAllDOMTexts === 'function' && typeof currentLang !== 'undefined' && currentLang !== 'vi') {
    setTimeout(() => translateAllDOMTexts(currentLang), 80);
  }

  // Thanh hành động của màn lập kế hoạch là `position: fixed`, không nằm
  // trong khung màn nào. Tick DO rồi rời màn đó thì nó vẫn nổi trên màn
  // mới, mang theo nút "Tạo Trip" của màn cũ. Nên bỏ chọn khi rời màn.
  if (targetView !== 'ops-planning' && typeof boChonTatCaDO === 'function'
    && typeof doDaChon !== 'undefined' && doDaChon.size) {
    boChonTatCaDO();
  }

  if (targetView === 'crm-sales') {
    // Không nạp gì thêm: màn Báo giá mới tự nạp `GET /api/quotations/board`;
    // bảng oracle cũ nằm trong `#qtv2-khoi-cu` đang ẩn, còn Kanban cơ hội
    // (chạy bằng dữ liệu Đơn hàng — bước đã trục xuất) đã gỡ.
  } else if (targetView === 'ops-planning') {
    if (typeof loadDeliveryOrders === 'function') loadDeliveryOrders();
  } else if (targetView === 'delivery-shipment') {
    if (typeof loadDispatchBoard === 'function') loadDispatchBoard();
    if (typeof renderTripReturnCockpit === 'function') renderTripReturnCockpit();
    if (typeof renderShipments === 'function') renderShipments();
  } else if (targetView === 'parking-list') {
    if (window.ParkingListUI) window.ParkingListUI.load({ silent: true });
  } else if (targetView === 'dispatch') {
    if (typeof loadDispatchBoard === 'function') loadDispatchBoard();
    if (typeof renderDispatchCalendar === 'function') renderDispatchCalendar();
  } else if (targetView === 'delivery-completion') {
    if (typeof loadDeliveryCompletionWorkbench === 'function') loadDeliveryCompletionWorkbench();
  } else if (targetView === 'tracking') {
    if (window.TrackingControlTower) {
      window.TrackingControlTower.load();
    } else {
      if (typeof loadIncidents === 'function') loadIncidents();
      setTimeout(() => {
        if (typeof initGPSTrackingMap === 'function') initGPSTrackingMap();
        if (typeof gpsTrackingMap !== 'undefined' && gpsTrackingMap) gpsTrackingMap.invalidateSize();
      }, 200);
    }
  } else if (targetView === 'operations-360') {
    if (typeof renderTmsCockpit === 'function') renderTmsCockpit();
  } else if (targetView === 'accounting') {
    if (typeof loadAccountingData === 'function') loadAccountingData();
  } else if (targetView === 'lab-summary') {
    if (typeof loadDashboard === 'function') loadDashboard();
    // Pane Chất lượng dịch vụ nằm trong workspace này, nên dựng sẵn để khi
    // người dùng chuyển sang góc nhìn đó là đã có nội dung.
    if (typeof renderReportingDrilldown === 'function') renderReportingDrilldown();
    if (window.TransportReporting) {
      window.TransportReporting.load();
      window.TransportReporting.selectWorkspacePane('overview');
    }
  } else if (targetView === 'master-data') {
    if (typeof loadFioriVehicles === 'function') loadFioriVehicles();
    if (typeof syncAllDynamicDropdowns === 'function') syncAllDynamicDropdowns();
    if (typeof loadRoutePlanningDropdown === 'function') loadRoutePlanningDropdown();
    if (typeof renderMasterDataSetupWizard === 'function') renderMasterDataSetupWizard();
    if (typeof renderMasterDataCommandCenter === 'function') renderMasterDataCommandCenter();
    setTimeout(() => {
      if (typeof initLeafletRouteMap === 'function') initLeafletRouteMap();
      if (typeof renderMasterDataCommandCenter === 'function') renderMasterDataCommandCenter();
    }, 200);
  }
  return true;
};

function measureEnterprisePanelHeight(panel, host) {
  if (!panel) return 0;
  const wasDisplayed = panel.style.display;
  const wasVisibility = panel.style.visibility;
  const wasPosition = panel.style.position;
  const wasInset = panel.style.inset;
  const wasWidth = panel.style.width;

  panel.style.display = 'block';
  panel.style.visibility = 'hidden';
  panel.style.position = 'absolute';
  panel.style.inset = '0 auto auto 0';
  if (host && host.clientWidth) panel.style.width = `${host.clientWidth}px`;

  const height = Math.max(panel.scrollHeight, panel.offsetHeight);

  panel.style.display = wasDisplayed;
  panel.style.visibility = wasVisibility;
  panel.style.position = wasPosition;
  panel.style.inset = wasInset;
  panel.style.width = wasWidth;
  return height;
}

function stabilizeEnterpriseTabHost(tabsId) {
  const panels = Array.from(document.querySelectorAll(`[data-enterprise-tabs="${tabsId}"]`));
  if (!panels.length) return;
  const host = panels[0].closest('[data-enterprise-panel-host]');
  if (!host) return;
  const currentMinHeight = parseFloat(host.dataset.stableMinHeight || '0') || 0;
  const maxHeight = panels.reduce((max, panel) => Math.max(max, measureEnterprisePanelHeight(panel, host)), 0);
  const stableHeight = Math.max(currentMinHeight, maxHeight);
  if (stableHeight > 0) {
    host.dataset.stableMinHeight = String(stableHeight);
    host.style.minHeight = `${stableHeight}px`;
  }
}

function releaseEnterpriseTabHostHeight(tabsId) {
  const panel = document.querySelector(`[data-enterprise-tabs="${tabsId}"]`);
  const host = panel?.closest('[data-enterprise-panel-host]');
  if (!host) return;
  clearTimeout(host._enterpriseReleaseTimer);
  host._enterpriseReleaseTimer = setTimeout(() => {
    host.style.minHeight = '';
    delete host.dataset.stableMinHeight;
  }, 220);
}

function selectEnterpriseTabForTarget(targetId) {
  const tabMap = {
    // `qtv2-root`, không còn `oracle-qt-list`: khối báo giá cũ đã bỏ hẳn, nên
    // neo của bước Báo giá là màn mới. Bỏ sót chỗ này thì nút "Thao Tác Ở Bước
    // Này" của bước 1 nhảy sang màn Kinh doanh mà KHÔNG mở thẻ Báo giá cước —
    // và vì thẻ đó tình cờ là thẻ đầu nên lỗi chỉ lộ ra khi người dùng vừa xem
    // thẻ Khách hàng rồi bấm nút đó.
    // Man Kinh doanh khong con vo the (xem `installEnterpriseModuleTabs`), nen
    // `qtv2-root` khong can chon the nao — de trong la dung.
  };
  const tabTarget = tabMap[targetId];
  if (!tabTarget || typeof window.showEnterpriseModuleTab !== 'function') return;
  window.showEnterpriseModuleTab(tabTarget[0], tabTarget[1]);
}

window.showEnterpriseModuleTab = function (tabsId, key) {
  stabilizeEnterpriseTabHost(tabsId);
  document.querySelectorAll(`[data-enterprise-tabs="${tabsId}"]`).forEach(panel => {
    panel.style.display = panel.getAttribute('data-enterprise-key') === key ? 'block' : 'none';
  });
  document.querySelectorAll(`[data-enterprise-tab-button="${tabsId}"]`).forEach(button => {
    const active = button.getAttribute('data-enterprise-key') === key;
    button.classList.toggle('active', active);
    button.style.borderColor = active ? '#2563eb' : '#e2e8f0';
    button.style.background = active ? '#eff6ff' : '#ffffff';
    button.style.color = active ? '#2563eb' : '#334155';
    button.style.boxShadow = active ? '0 4px 12px rgba(10,110,209,.12)' : 'none';
  });
  // CỐ Ý không còn nhánh riêng cho màn Theo dõi ở đây.
  //
  // Trước đây khi mở thẻ "GPS / POD" thì gọi `gpsTrackingMap.invalidateSize()`:
  // Leaflet dựng bản đồ trong lúc thẻ còn ẩn thì tính sai kích thước, phải nhắc
  // lại khi hiện ra. Nay màn Theo dõi không còn chia thẻ — cả ba khối hiện cùng
  // lúc — nên chỗ nhắc đúng là lúc VÀO MÀN, và `switchView('tracking')` đã làm
  // việc đó rồi. Giữ thêm ở đây là hai chỗ làm cùng một việc.
  releaseEnterpriseTabHostHeight(tabsId);
};

function normalizeEnterprisePanelHeading(previous) {
  if (!previous) return;
  previous.style.margin = '0 0 14px 0';
  previous.style.lineHeight = '1.25';
}

function moveElementWithHeading(panel, selector) {
  let element = document.querySelector(selector);
  if (!element || element.getAttribute('data-enterprise-tabbed') === '1') return false;
  if (element.tagName === 'TBODY') {
    element = element.closest('.fiori-table-wrapper') || element.closest('table') || element;
  }
  const previous = element.previousElementSibling;
  if (previous && /^H[234]$/i.test(previous.tagName) && previous.parentElement === element.parentElement) {
    previous.setAttribute('data-enterprise-tabbed', '1');
    normalizeEnterprisePanelHeading(previous);
    panel.appendChild(previous);
  }
  element.setAttribute('data-enterprise-tabbed', '1');
  panel.appendChild(element);
  return true;
}

window.switchDemoReadinessTab = function (key, button) {
  const selected = key || 'overview';
  document.querySelectorAll('[data-demo-readiness-panel]').forEach(panel => {
    panel.style.display = panel.getAttribute('data-demo-readiness-panel') === selected ? 'grid' : 'none';
  });
  document.querySelectorAll('.demo-readiness-tab').forEach(tab => {
    const active = tab === button || tab.id === `demo-readiness-tab-${selected}`;
    tab.classList.toggle('active', active);
    tab.style.border = active ? '2px solid #2563eb' : '1px solid #dbeafe';
    tab.style.background = active ? '#eff6ff' : '#ffffff';
    tab.style.color = active ? '#2563eb' : '#475569';
  });
};

window.switchOperations360Tab = function (key, button) {
  const selected = key || 'shipment';
  document.querySelectorAll('[data-operations-360-panel]').forEach(panel => {
    panel.style.display = panel.getAttribute('data-operations-360-panel') === selected ? 'grid' : 'none';
  });
  document.querySelectorAll('.operations-360-tab').forEach(tab => {
    const active = tab === button || tab.id === `operations-360-tab-${selected}`;
    tab.classList.toggle('active', active);
    tab.style.border = active ? '2px solid #2563eb' : '1px solid #dbeafe';
    tab.style.background = active ? '#eff6ff' : '#ffffff';
    tab.style.color = active ? '#2563eb' : '#475569';
  });
};

window.switchFinanceSubTab = function (key, button) {
  const selected = key || 'overview';
  document.querySelectorAll('[data-finance-sub-panel]').forEach(panel => {
    panel.style.display = panel.getAttribute('data-finance-sub-panel') === selected ? 'grid' : 'none';
  });
  document.querySelectorAll('.finance-sub-tab').forEach(tab => {
    const active = tab === button || tab.id === `finance-sub-tab-${selected}`;
    tab.classList.toggle('active', active);
    tab.style.border = active ? '2px solid #2563eb' : '1px solid #dbeafe';
    tab.style.background = active ? '#eff6ff' : '#ffffff';
    tab.style.color = active ? '#2563eb' : '#475569';
  });
};

window.installEnterpriseModuleTabs = function () {
  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
  const crmTitle = lang === 'la' ? 'CRM / ໃບສະເໜີລາຄາ / ໃບສັ່ງຂາຍ' : (lang === 'en' ? 'CRM / Quotations / Transport Orders' : 'CRM / Báo giá cước / Đơn hàng vận chuyển');
  const singleGroupHint = lang === 'la' ? 'ເປີດເທື່ອລະກຸ່ມເພື່ອບໍ່ໃຫ້ໜ້າຈໍສັບສົນ.' : (lang === 'en' ? 'Open one group at a time to reduce clutter.' : 'Chỉ mở một nhóm nghiệp vụ mỗi lần để đỡ rối màn hình.');

  const configs = [
    // MAN KINH DOANH (view-crm-sales) CO Y KHONG CO O DAY.
    //
    // Truoc day no boc man Bao gia moi (`#qtv2-root`) trong mot vo hai the
    // "Bao gia cuoc | Khach hang va co hoi". Chu du an nhin thay mot khung nam
    // trong mot khung khac va noi ro: khong lam dang hai the nua. The "Khach
    // hang va co hoi" la bang Kanban chay bang du lieu Don hang (SO) — buoc da
    // truc xuat khoi he thong — nen da go han khoi index.html. Man Bao gia gio dung tran, khong vo.
    // MAN THEO DOI CO Y KHONG CO O DAY.
    //
    // Truoc day no chia ba the lon: GPS/POD, Su co, Chuoi su kien. Ba thu do la
    // ba MAT cua cung mot chuyen: nguoi truc thap kiem soat thay mot chuyen do,
    // roi hoi "no dang o dau", "da ky POD chua", "co su co gi". Moi cau hoi la
    // mot lan doi the va mat ngu canh — va chon DO o the GPS roi sang the Su co
    // la phai chon lai.
    //
    // Nay ba khoi hien cung luc, xep thanh mot bang hai cot bang CSS tren
    // `#view-tracking`. Xem `.tk-board-view` trong index.html.
    {
      sectionId: 'view-accounting',
      tabsId: 'accounting-folder-tabs',
      title: 'Finance cockpit',
      groups: [
        {
          key: 'cockpit',
          label: 'Actual Cost / AP / Settlement',
          hint: lang === 'la' ? 'ສາຍງານການເງິນການຂົນສົ່ງຫຼັກ.' : (lang === 'en' ? 'Main transportation finance pipeline.' : 'Luồng tài chính vận tải chính.'),
          selectors: ['#finance-cockpit-panel']
        },
        {
          key: 'legacy',
          label: 'AR / GL',
          hint: lang === 'la' ? 'ໃບເກັບເງິນ AR ແລະ ບັນຊີແຍກປະເພດ.' : (lang === 'en' ? 'AR Invoices and General Ledger.' : 'Hóa đơn AR và sổ cái kế toán.'),
          selectors: ['#fiori-invoice-tbody', '#fiori-gl-tbody']
        }
      ]
    }
  ];

  configs.forEach(config => {
    const section = document.getElementById(config.sectionId);
    if (!section) return;
    const existingShell = document.getElementById(config.tabsId);
    if (existingShell) {
      // Update text in place safely without removing child panels
      const titleEl = existingShell.querySelector('.enterprise-tabs-title');
      if (titleEl) titleEl.innerHTML = `<i class="fa-solid fa-folder-tree" style="color:#2563eb;"></i> ${config.title}`;
      const hintEl = existingShell.querySelector('.enterprise-tabs-hint');
      if (hintEl) hintEl.textContent = singleGroupHint;

      config.groups.forEach(group => {
        const btn = existingShell.querySelector(`[data-enterprise-tab-button="${config.tabsId}"][data-enterprise-key="${group.key}"]`);
        if (btn) {
          btn.innerHTML = `<i class="fa-solid fa-layer-group" style="color:#2563eb;margin-top:2px;"></i><span><span style="display:block;">${group.label}</span><small style="display:block;color:#64748b;font-weight:650;margin-top:3px;line-height:1.35;">${group.hint}</small></span>`;
        }
      });
      return;
    }

    const anchor = section.querySelector('[data-enterprise-tabs-anchor]');
    const container = section.querySelector('.fiori-container') || section;
    const shell = document.createElement('div');
    shell.id = config.tabsId;
    shell.style.cssText = 'background:#ffffff;border:1px solid #dbeafe;border-radius:16px;padding:14px;margin:0 0 18px 0;box-shadow:0 6px 18px rgba(15,23,42,.05);';
    shell.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:12px;">
        <div class="enterprise-tabs-title" style="font-weight:950;color:#0f172a;"><i class="fa-solid fa-folder-tree" style="color:#2563eb;"></i> ${config.title}</div>
        <div class="enterprise-tabs-hint" style="font-size:.76rem;color:#64748b;font-weight:800;">${singleGroupHint}</div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px;"></div>
    `;
    const buttonRow = shell.lastElementChild;
    const panelHost = document.createElement('div');
    panelHost.setAttribute('data-enterprise-panel-host', config.tabsId);
    panelHost.style.cssText = 'display:grid;gap:12px;margin-top:12px;transition:min-height .18s ease;';
    shell.appendChild(panelHost);
    if (anchor && anchor.parentElement) {
      anchor.parentElement.insertBefore(shell, anchor);
    } else {
      container.insertBefore(shell, container.firstElementChild);
    }

    config.groups.forEach((group, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.setAttribute('data-enterprise-tab-button', config.tabsId);
      button.setAttribute('data-enterprise-key', group.key);
      button.onclick = () => window.showEnterpriseModuleTab(config.tabsId, group.key);
      button.style.cssText = 'border:2px solid #e2e8f0;background:#ffffff;color:#334155;border-radius:14px;padding:13px 14px;text-align:left;font-weight:900;cursor:pointer;display:flex;gap:10px;align-items:flex-start;';
      button.innerHTML = `<i class="fa-solid fa-layer-group" style="color:#2563eb;margin-top:2px;"></i><span><span style="display:block;">${group.label}</span><small style="display:block;color:#64748b;font-weight:650;margin-top:3px;line-height:1.35;">${group.hint}</small></span>`;
      buttonRow.appendChild(button);

      const panel = document.createElement('div');
      panel.setAttribute('data-enterprise-tabs', config.tabsId);
      panel.setAttribute('data-enterprise-key', group.key);
      panel.style.cssText = `display:${index === 0 ? 'block' : 'none'};border:1px solid #e2e8f0;border-radius:14px;padding:12px;background:#f8fbff;`;
      group.selectors.forEach(selector => moveElementWithHeading(panel, selector));
      if (!panel.children.length) {
        panel.innerHTML = '<div style="color:#64748b;font-size:.84rem;">Nhóm này chưa có panel chính hoặc đang được render động.</div>';
      }
      panelHost.appendChild(panel);
    });
    window.showEnterpriseModuleTab(config.tabsId, config.groups[0].key);
  });
};


function initAIDrawer() {
  const widget = document.getElementById("ai-widget");
  const toggleBtn = document.getElementById("toggle-ai-btn");
  const closeBtn = document.getElementById("close-ai-btn");

  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => widget.classList.add("open"));
  }
  if (closeBtn) {
    closeBtn.addEventListener("click", () => widget.classList.remove("open"));
  }
}

function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = "flex";
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = "none";
}

/**
 * Nạp lại các tập dữ liệu tài chính mà /api/data/all cố tình bỏ trống.
 *
 * Lỗi không nạp bổ sung được thì bỏ qua trong im lặng ở mức từng tập: thiếu
 * dữ liệu tài chính không được làm hỏng cả màn hình, và các hàm render đều đã
 * xử lý được trường hợp mảng rỗng.
 */
async function hydrateFinanceState() {
  const sources = [
    { key: 'invoices', path: '/api/invoices' },
    { key: 'gl_transactions', path: '/api/gl-transactions' },
    // Ba tập của Finance Cockpit. `/api/data/all` bôi trắng đúng ba tập này
    // (xem `routes/data_export_routes.py`), nên trước đây cả bốn thẻ số liệu
    // và ba danh sách bên dưới đều hiện rỗng VĨNH VIỄN — kể cả khi trong cơ
    // sở dữ liệu đang có hồ sơ chi phí chờ duyệt. Đó chính là cái bẫy mà đoạn
    // chú thích ngay dưới đây nói tới, chỉ khác là nó chỉ được vá cho
    // `invoices` mà bỏ sót ba tập tài chính vận tải.
    { key: 'freight_actual_costs', path: '/api/tms/finance/costs' },
    { key: 'ap_invoices', path: '/api/tms/finance/ap-invoices' },
    { key: 'settlements', path: '/api/tms/finance/settlements' },
  ];
  await Promise.all(sources.map(async ({ key, path }) => {
    try {
      const res = await fetch(`${API_BASE}${path}`, { headers: financeAuthHeaders() });
      // `if (!res.ok) return;` trần là chỗ nguy hiểm nhất trong hàm này: một
      // 403 vì thiếu quyền tài chính làm Finance Cockpit hiện 0 VĨNH VIỄN,
      // trong khi bảng ngay bên dưới liệt kê hóa đơn thật. Con số 0 đó trông
      // y hệt một con số 0 đúng.
      if (!res.ok) {
        return baoNapThatBai(`số liệu tài chính (${key})`,
          new Error(`Máy chủ trả về ${res.status}`));
      }
      const payload = await res.json();
      const rows = Array.isArray(payload) ? payload : (payload.data || payload.items);
      if (Array.isArray(rows)) appState[key] = rows;
    } catch (err) {
      baoNapThatBai(`số liệu tài chính (${key})`, err);
    }
  }));
}

async function loadAllData() {
  try {
    const res = await fetch(`${API_BASE}/api/data/all`, { headers: financeAuthHeaders() });
    if (res.ok) {
      appState = await res.json();
      if (appState.quotations) crmQuotations = appState.quotations;
      if (appState.delivery_orders) eplDeliveryOrders = appState.delivery_orders;
      if (appState.routes) eplRoutes = appState.routes;
      if (appState.customers) eplCustomers = appState.customers;
      if (appState.vehicles) fioriVehicles = appState.vehicles;
      if (appState.drivers) fioriDrivers = appState.drivers;
      if (appState.vehicle_types) vehTypes = appState.vehicle_types;

      // /api/data/all cố tình trả về mảng rỗng cho invoices, ap_invoices,
      // settlements... (xem main.py::_data_all). Nhưng Finance Cockpit và các
      // biểu đồ tài chính lại đọc từ appState, nên chúng hiện 0 vĩnh viễn
      // trong khi bảng ngay bên dưới liệt kê hóa đơn thật. Nạp bổ sung từ
      // endpoint chuyên trách — nó cũng đã được bảo vệ bằng xác thực như
      // /api/data/all nên không nới lỏng gì.
      await hydrateFinanceState();

      renderAllTables();
      if (typeof syncAllDynamicDropdowns === 'function') syncAllDynamicDropdowns();
      if (typeof loadDispatchBoard === 'function') loadDispatchBoard();
    }
  } catch (err) {
    // Đây là hàm nạp gốc của cả màn tổng quan. Hỏng ở đây là mọi bảng, mọi
    // ô đếm trên Dashboard đều rỗng — và rỗng thì trông hệt như "công ty
    // chưa có đơn nào".
    baoNapThatBai('dữ liệu tổng quan', err);
  }
}

window.loadData = async function () {
  await loadAllData();
  showToast('Đã tải lại dữ liệu từ CSDL.');
};

function renderAllTables() {
  const activeViewId = document.querySelector('.view-section.active')?.id || 'view-dashboard';
  // Đã bỏ tám lời gọi ở đây: renderQuotations, renderSalesOrders,
  // renderDashboardDeliveryOrders, renderDashboardRoutes, renderDispatches,
  // renderIncidents, renderInvoices, renderVehicles.
  //
  // Tám hàm đó tìm `table-quotations`, `table-vehicles`, ... — KHÔNG MỘT id nào
  // trong số đó tồn tại trong index.html, nên cả tám đều thoát ngay ở dòng
  // `if (!tbody) return;`. Mỗi màn đều đã có hàm vẽ THẬT riêng
  // (renderOracleQTList, renderFioriVehicles, renderDeliveryOrders, ...) — các
  // hàm đó vẫn ở đây.
  renderStats();
  renderSummaryChart();

  if (activeViewId === 'view-crm-sales') {
    if (typeof renderOracleQTList === 'function') renderOracleQTList(crmQuotations);
  } else if (activeViewId === 'view-master-data') {
    renderMasterDataSetupWizard();
  } else if (activeViewId === 'view-dispatch') {
    renderDispatchCalendar();
    if (typeof renderDispatchDOs === 'function') renderDispatchDOs();
  } else if (activeViewId === 'view-tracking') {
    renderGpsEventTimeline();
    napVetGpsChoManTheoDoi();
  } else if (activeViewId === 'view-operations-360') {
    renderTmsCockpit();
  } else if (activeViewId === 'view-accounting') {
    renderFinanceCockpit();
    renderFinanceActionWorkbench();
    renderFinanceMasterDataTabs();
  } else if (activeViewId === 'view-lab-summary') {
    // Pane Chất lượng dịch vụ (SLA) thuộc workspace Phân tích.
    renderReportingDrilldown();
  } else if (activeViewId === 'view-delivery-shipment') {
    renderTripReturnCockpit();
  } else if (activeViewId === 'view-parking-list') {
    if (window.ParkingListUI) window.ParkingListUI.load({ silent: true });
  }

  if (typeof installEnterpriseModuleTabs === 'function') installEnterpriseModuleTabs();
  if (typeof translateAllDOMTexts === 'function' && typeof currentLang !== 'undefined' && currentLang !== 'vi') {
    translateAllDOMTexts(currentLang);
  }
}

function openMasterSetupStep(tabId) {
  switchView('master-data');
  if (!tabId) {
    showToast('Mục này đã có dữ liệu backend, cần bổ sung tab quản trị riêng trong Master Data.');
    return;
  }
  setTimeout(() => {
    const buttons = Array.from(document.querySelectorAll('.md-tab-btn'));
    const button = buttons.find(btn => (btn.getAttribute('onclick') || '').includes(tabId));
    if (button && typeof switchMasterDataTab === 'function') {
      switchMasterDataTab(tabId, button);
      const target = document.getElementById(tabId);
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, 80);
}

let activeMasterSetupStepKey = '';

function selectMasterSetupStep(stepKey) {
  activeMasterSetupStepKey = stepKey || '';
  renderMasterDataSetupWizard();
}

function renderMasterDataSetupWizard() {
  if (!window.TmsCockpit || typeof document === 'undefined') return;
  const progressEl = document.getElementById('master-setup-progress');
  const stepsEl = document.getElementById('master-setup-wizard-steps');
  const guidanceEl = document.getElementById('master-setup-guidance');
  const detailEl = document.getElementById('master-setup-selected-detail');
  const impactEl = document.getElementById('master-setup-detail-impact');
  if (!progressEl || !stepsEl || !guidanceEl) return;

  const wizard = window.TmsCockpit.buildMasterSetupWizardSteps(appState || {});
  if (!activeMasterSetupStepKey) {
    activeMasterSetupStepKey = (wizard.steps.find(step => step.status === 'missing') || wizard.steps[0] || {}).key || '';
  }
  progressEl.innerText = `${wizard.progress.percent}%`;
  progressEl.title = `${wizard.progress.done}/${wizard.progress.total} nhóm dữ liệu đã có`;
  stepsEl.innerHTML = wizard.steps.map(step => `
    <div onclick="selectMasterSetupStep('${step.key}')" style="border:1px solid ${String(activeMasterSetupStepKey) === String(step.key) ? '#2563eb' : step.status === 'done' ? '#bbf7d0' : '#fed7aa'}; background:${step.status === 'done' ? '#f0fdf4' : '#fff7ed'}; border-radius:12px; padding:12px; display:grid; gap:8px; cursor:pointer;">
      <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
        <span style="font-weight:900; color:#0f172a;">${step.order}. ${step.label}</span>
        <span style="font-size:.7rem; font-weight:900; color:${step.status === 'done' ? '#047857' : '#c2410c'};">${step.status === 'done' ? 'Đủ dữ liệu' : 'Thiếu'}</span>
      </div>
      <div style="color:#64748b; font-size:.78rem; line-height:1.35;">${step.message}</div>
      <button class="fiori-btn" onclick="event.stopPropagation(); openMasterSetupStep('${step.tabId || ''}')" style="justify-content:center; background:${step.uiStatus === 'ready' ? '#2563eb' : '#64748b'}; color:#ffffff; border:none; font-weight:800; padding:7px 10px;">
        <i class="fa-solid ${step.uiStatus === 'ready' ? 'fa-arrow-right' : 'fa-screwdriver-wrench'}"></i> ${step.actionLabel}
      </button>
    </div>
  `).join('');

  if (detailEl && impactEl && window.TmsCockpit.buildMasterSetupGuidedDetail) {
    const detail = window.TmsCockpit.buildMasterSetupGuidedDetail(appState || {}, activeMasterSetupStepKey);
    detailEl.innerHTML = `
      <div style="border:1px solid ${detail.status === 'done' ? '#bbf7d0' : '#fed7aa'}; background:${detail.status === 'done' ? '#f0fdf4' : '#fff7ed'}; border-radius:14px; padding:13px 14px;">
        <div style="display:flex; justify-content:space-between; gap:12px; align-items:flex-start;">
          <div>
            <div style="font-size:.74rem; font-weight:900; color:#64748b; text-transform:uppercase;">Bước ${detail.order || ''}</div>
            <h4 style="margin:3px 0 4px; color:#0f172a;">${detail.title}</h4>
            <div style="font-size:.82rem; color:#475569;">${detail.message}</div>
          </div>
          <span style="font-size:.72rem; font-weight:950; border-radius:999px; padding:5px 9px; color:${detail.status === 'done' ? '#047857' : '#c2410c'}; background:#ffffff; border:1px solid ${detail.status === 'done' ? '#bbf7d0' : '#fed7aa'};">${detail.status_label}</span>
        </div>
        <button class="fiori-btn" onclick="openMasterSetupStep('${detail.tabId || ''}')" style="margin-top:10px; background:#2563eb; color:white; border:none; font-weight:900; padding:8px 12px;">
          <i class="fa-solid fa-arrow-right"></i> ${detail.actionLabel}
        </button>
      </div>
    `;
    impactEl.innerHTML = [
      ...(detail.flow_impact || []).map(item => ({ icon: 'fa-diagram-project', text: item })),
      ...(detail.guidance || []).map(item => ({ icon: 'fa-lightbulb', text: item }))
    ].map(item => `
      <div style="background:#ffffff; border:1px solid #dbeafe; border-radius:10px; padding:9px 11px; color:#475569; font-size:.82rem;">
        <i class="fa-solid ${item.icon}" style="color:#2563eb;"></i> ${item.text}
      </div>
    `).join('');
  }

  guidanceEl.innerHTML = wizard.guidance.length ? `
    <div style="background:#f8fafc; border:1px dashed #cbd5e1; border-radius:12px; padding:12px 14px; color:#475569;">
      <div style="font-weight:900; color:#0f172a; margin-bottom:6px;"><i class="fa-solid fa-lightbulb" style="color:#f59e0b;"></i> Gợi ý để đạt UX như hệ thống lớn</div>
      ${wizard.guidance.map(item => `<div style="font-size:.82rem; margin-top:4px;">• ${item}</div>`).join('')}
    </div>
  ` : `
    <div style="background:#ecfdf5; border:1px solid #bbf7d0; border-radius:12px; padding:12px 14px; color:#047857; font-weight:800;">
      <i class="fa-solid fa-circle-check"></i> Wizard đã sẵn sàng cho demo luồng Master Data.
    </div>
  `;
}

let tmsActiveTimelineDoId = '';
let tmsActiveShipment360Id = '';
let shipmentDossierState = null;
let activeShipmentDossierTab = 'overview';
let activeShipment360StepContext = { deliveryOrderId: '', stepKey: 'delivery_order' };

function shipmentStateFor(deliveryOrderId) {
  const scopedId = shipmentDossierState?.delivery_orders?.[0]?.id || '';
  return String(scopedId) === String(deliveryOrderId || '') ? shipmentDossierState : (appState || {});
}

async function loadShipmentDossier(deliveryOrderId) {
  if (!deliveryOrderId) return null;
  try {
    const response = await fetch(
      `${API_BASE}/api/delivery-orders/${encodeURIComponent(deliveryOrderId)}/dossier`,
      { headers: financeAuthHeaders() }
    );
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    shipmentDossierState = await response.json();
    return shipmentDossierState;
  } catch (error) {
    shipmentDossierState = null;
    console.warn('Không tải được hồ sơ chuyến theo DO.', error);
    if (typeof showToast === 'function') showToast('Không tải được hồ sơ chuyến. Dữ liệu tổng sẽ không được dùng thay thế.');
    return null;
  }
}

function selectOrderTimeline(deliveryOrderId) {
  tmsActiveTimelineDoId = deliveryOrderId || '';
  tmsActiveShipment360Id = deliveryOrderId || tmsActiveShipment360Id;
  renderTmsCockpit();
}

async function selectShipment360(deliveryOrderId) {
  tmsActiveShipment360Id = deliveryOrderId || '';
  tmsActiveTimelineDoId = deliveryOrderId || tmsActiveTimelineDoId;
  await loadShipmentDossier(deliveryOrderId);
  renderShipment360Detail();
}

function selectShipmentDossierFromSearch(value) {
  const deliveryOrderId = String(value || '').trim();
  if (!deliveryOrderId) return;
  selectShipment360(deliveryOrderId);
}

function switchShipmentDossierTab(tabName, button) {
  activeShipmentDossierTab = ['overview', 'journey', 'finance'].includes(tabName) ? tabName : 'overview';
  document.querySelectorAll('[data-dossier-tab]').forEach(item => {
    item.classList.toggle('active', item === button || item.dataset.dossierTab === activeShipmentDossierTab);
  });
  const visibility = {
    overview: ['shipment-360-summary', 'shipment-360-alerts', 'shipment-360-timeline', 'shipment-360-actions'],
    journey: ['shipment-360-events', 'shipment-360-documents'],
    finance: ['shipment-360-finance', 'shipment-360-settlement-readiness']
  };
  const visibleIds = new Set(visibility[activeShipmentDossierTab]);
  Object.values(visibility).flat().forEach(id => {
    const element = document.getElementById(id);
    if (element) element.style.display = visibleIds.has(id) ? 'grid' : 'none';
  });
  const primaryGrid = document.getElementById('shipment-dossier-primary-grid');
  const secondaryGrid = document.getElementById('shipment-dossier-secondary-grid');
  if (primaryGrid) {
    primaryGrid.style.display = activeShipmentDossierTab === 'finance' ? 'none' : 'grid';
    primaryGrid.style.gridTemplateColumns = 'minmax(0, 1fr)';
  }
  if (secondaryGrid) {
    secondaryGrid.style.display = activeShipmentDossierTab === 'overview' || activeShipmentDossierTab === 'journey' || activeShipmentDossierTab === 'finance' ? 'grid' : 'none';
    secondaryGrid.style.gridTemplateColumns = 'minmax(0, 1fr)';
  }
}

window.selectShipmentDossierFromSearch = selectShipmentDossierFromSearch;
window.switchShipmentDossierTab = switchShipmentDossierTab;
/* Trạng thái của màn Theo dõi chuyến (Trip Return Cockpit).
   ------------------------------------------------------------------------
   Năm dòng này TỪNG BỊ XÓA MẤT — và đó là lỗi của tôi. Khi gỡ chín trình vẽ
   chết ở commit 78cd1a9, tôi cắt theo khoảng dòng "từ định nghĩa hàm này đến
   định nghĩa hàm kế tiếp". Năm dòng `let` nằm ĐÚNG GIỮA
   `renderTripReturnCockpitLegacy` và `switchDeliveryWorkbenchView`, nên
   chúng bị cắt theo.

   Hậu quả trông không giống một lỗi lập trình: `renderTripReturnCockpit` đọc
   `tripReturnStatusFilter` ở dòng lọc, gặp ReferenceError, dừng giữa hàm — nên
   màn "Giao hàng & vận chuyển" báo "Chưa có chuyến đang chạy" trong khi cơ sở
   dữ liệu có 2 chuyến `in_transit`. Nhìn vào thì tưởng lỗi dữ liệu hoặc lỗi
   backend, mà API trả về đủ 3 chuyến.

   Vì sao im lặng: ở chế độ không strict, `X = 1` tạo một biến toàn cục ngầm
   nên GHI thì không báo gì; chỉ ĐỌC trước lần ghi đầu tiên mới nổ. Lỗi chỉ
   hiện trong Console.

   Bài học đã đưa vào `tests/bien-phai-duoc-khai-bao.test.js`: quét mọi phép
   gán trần mà không có khai báo. */

let activeTripReturnId = '';
let tripReturnActionSequence = 0;
let tripReturnSearchQuery = '';
let tripReturnStatusFilter = '';
let activeTripReturnDetailTab = 'journey';

function switchDeliveryWorkbenchView(tabName = 'shipments') {
  const planningTabs = ['board', 'do', 'planning', 'pending'];
  const dispatchTabs = ['dispatch', 'schedule', 'calendar', 'alerts'];

  if (planningTabs.includes(tabName)) {
    switchView('ops-planning');
    return;
  }

  if (dispatchTabs.includes(tabName)) {
    switchView('dispatch');
    if (typeof renderDispatchCalendar === 'function') renderDispatchCalendar();
    return;
  }

  if (typeof renderTripReturnCockpit === 'function') renderTripReturnCockpit();
  if (typeof renderShipments === 'function') renderShipments();
}

function switchDeliveryRunningView(tabName = 'list') {
  if (tabName === 'calendar' || tabName === 'alerts') {
    switchView('dispatch');
    if (typeof renderDispatchCalendar === 'function') renderDispatchCalendar();
    return;
  }

  if (typeof renderTripReturnCockpit === 'function') renderTripReturnCockpit();
  if (typeof renderShipments === 'function') renderShipments();
}
function tripReturnFormatTime(value) {
  if (!value) return 'Chưa có giờ';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString('vi-VN', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
  });
}

function tripReturnRowsForSelected(selected, keys) {
  const rows = keys.flatMap(key => Array.isArray(appState?.[key]) ? appState[key] : []);
  const doIds = new Set((selected?.raw?.delivery_order_ids || selected?.delivery_order_ids || []).map(String));
  const tripId = String(selected?.id || '');
  const khop = rows.filter(row => String(row.trip_id || row.transport_trip_id || '') === tripId
    || doIds.has(String(row.do_id || row.delivery_order_id || '')));
  // BỎ TRÙNG theo id. Hàm này gom từ NHIỀU khoá của `appState` (ví dụ `pods` và
  // `pod_records`), và cùng một bản ghi có thể nằm ở cả hai — nên tab POD hiện
  // một chữ ký nhận hai lần. Đo được: chuyến DEMO-TRIP-2026-003 có đúng một POD
  // mà danh sách hiện hai dòng giống hệt, đọc ra như thể có hai người ký.
  // Khoá bỏ trùng là một TỔ HỢP, không phải `id`. Đo được: hai bản ghi POD của
  // cùng một lần ký đến từ hai khoá khác nhau của `appState` (`pods` và
  // `pod_records`), và bản ở khoá này KHÔNG có `id` — nên so theo `id` thì
  // không bắt được, và tab POD hiện một chữ ký nhận hai lần, đọc ra như thể có
  // hai người ký.
  //
  // Tổ hợp lấy những thứ định danh một lần ký THẬT: đơn nào, điểm dừng thứ
  // mấy, ký lúc nào, ai ký. Hai bản ghi khớp cả bốn thì đúng là một.
  //
  // `id` CỐ Ý không nằm trong khoá — nó chính là mẩu khác nhau giữa hai bản của
  // cùng một lần ký, nên đưa vào là khoá lại tách chúng ra làm hai.
  const daThay = new Set();
  return khop.filter(row => {
    const khoa = [
      row.do_id || row.delivery_order_id || '',
      row.stop_no !== undefined && row.stop_no !== null ? row.stop_no : '',
      row.delivery_time || row.event_time || row.created_at || '',
      row.receiver_name || '',
    ].map(String).join('|');
    // Không có mẩu nào để định danh thì giữ lại: mất một dòng thật tệ hơn hiện
    // thừa một dòng.
    if (khoa === '|||') return true;
    if (daThay.has(khoa)) return false;
    daThay.add(khoa);
    return true;
  });
}


/* --------------------------------------------------------------------------
   DẢI SỐ LIỆU — năm thẻ, bấm được để lọc bảng.
   -------------------------------------------------------------------------- */

function renderTripKpis(items, groupFor) {
  const host = document.getElementById('trip-kpis');
  if (!host) return;

  const dem = { 'thieu-ve': 0, 'tre-han': 0, 'thieu-pod': 0, 'doi-soat-duoc': 0 };
  let kmRong = 0;
  items.forEach(item => {
    const raw = item.raw || item;
    const nhom = tripNhomKpi(raw, groupFor(item));
    nhom.forEach(n => { if (n in dem) dem[n] += 1; });
    if (nhom.has('thieu-ve')) kmRong += Number(raw.total_distance_km || 0);
  });

  const the = [
    ['', 'Chuyến đang mở', items.length, 'toàn bộ chuyến chưa đối soát', 'blue'],
    ['thieu-ve', 'Chưa có chặng về', dem['thieu-ve'],
      kmRong ? '≈ ' + Math.round(kmRong).toLocaleString('vi-VN') + ' km chạy rỗng nếu không ghép'
        : 'không có km rỗng', 'amber'],
    ['tre-han', 'Trễ hạn giao', dem['tre-han'], 'tới nơi sau hạn khách cho phép', 'red'],
    ['thieu-pod', 'Xong nhưng thiếu POD', dem['thieu-pod'], 'không xuất được hoá đơn', 'purple'],
    ['doi-soat-duoc', 'Sẵn sàng đối soát', dem['doi-soat-duoc'], 'đủ POD trên mọi DO', 'green'],
  ];

  host.innerHTML = the.map(cap => {
    const ma = cap[0], nhan = cap[1], so = cap[2], phu = cap[3], mau = cap[4];
    // Thẻ không có chuyến nào thì làm mờ — cho bấm rồi bảng trống thì người
    // dùng phải thử mới biết là không có gì.
    const tat = ma !== '' && !so;
    return '<button type="button" class="card kpi ' + mau
      + (tripKpiFilter === ma ? ' on' : '') + '"'
      + (tat ? ' disabled title="Không có chuyến nào trong nhóm này"'
        : ' onclick="setTripKpiFilter(\'' + ma + '\')" title="Bấm để lọc bảng chuyến theo nhóm này"')
      + '><span>' + escapeHtml(nhan) + '</span><b>' + Number(so).toLocaleString('vi-VN')
      + '</b><small>' + escapeHtml(phu) + '</small></button>';
  }).join('');
}

/* --------------------------------------------------------------------------
   BẢNG CHUYẾN — bảy cột, đúng bảy câu hỏi người đối soát phải trả lời.
   -------------------------------------------------------------------------- */

function tripChuCaiTen(ten) {
  const tu = String(ten || '').trim().split(/\s+/).filter(Boolean);
  if (!tu.length) return '?';
  if (tu.length === 1) return tu[0].slice(0, 2).toUpperCase();
  return (tu[tu.length - 2][0] + tu[tu.length - 1][0]).toUpperCase();
}

function tripTenNguoi(ma) {
  if (!ma) return '';
  const ds = (availableDrivers && availableDrivers.length) ? availableDrivers : (fioriDrivers || []);
  const nguoi = ds.find(t => String(t.id) === String(ma));
  return (nguoi && nguoi.name) || String(ma);
}

function renderTripBang(items, groupFor) {
  const host = document.getElementById('trip-return-queue');
  if (!host) return;

  if (!items.length) {
    host.innerHTML = '<div class="empty" style="margin:14px 16px">'
      + (tripKpiFilter
        ? 'Không có chuyến nào trong nhóm đang lọc. Bấm lại thẻ số liệu để bỏ lọc.'
        : 'Không tìm thấy chuyến phù hợp bộ lọc.')
      + '</div>';
    return;
  }

  const dong = items.map(item => {
    const raw = item.raw || item;
    const journey = window.TmsCockpit.getTripJourneyPresentation(raw);
    const ma = encodeURIComponent(String(item.id || ''));
    const td = tripTienDo(raw);
    const pod = tripSoPOD(raw);
    const han = tripHanGiao(raw);
    const toi = tripGioToiNoi(raw);
    const thucTe = Boolean(raw.actual_arrival_at);
    const treHan = tripTreHan(raw);
    // Lệch kế hoạch nội bộ: chỉ là ghi chú (xám/vàng), không phải "trễ hạn".
    const lechKH = Number.isFinite(Number(raw.behind_plan_minutes)) ? Number(raw.behind_plan_minutes) : null;
    const gio = d => d ? d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }) : '—';
    const gioNgay = d => d ? d.toLocaleString('vi-VN', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' }) : '—';

    const dsDO = raw.delivery_order_ids || [];
    const chang = raw.legs || [];
    const tuyen = chang.length
      ? escapeHtml(String(chang[0].origin || '')) + ' → '
        + escapeHtml(String(chang[chang.length - 1].destination || ''))
      : '<em style="color:#7b8796">chưa có chặng</em>';

    // POD vẽ thành từng CHẤM, một chấm một DO — như bản mẫu. Chấm ĐỎ chỉ khi
    // chuyến đã xong mà đơn vẫn chưa ký: chuyến đang chạy thì chưa ký là bình
    // thường, tô đỏ là báo động giả.
    const xongRoi = td.phanTram === 100;
    const chamPOD = pod.tong
      ? Array.from({ length: pod.tong }, (_, i) =>
        '<i class="' + (i < pod.co ? 'd' : (xongRoi ? 'm' : '')) + '"></i>').join('')
      : '';

    const toLai = [raw.driver_id, raw.co_driver_id].filter(Boolean);
    const vongTron = toLai.length
      ? toLai.map(x => '<span class="av" title="' + escapeHtml(tripTenNguoi(x)) + '">'
        + escapeHtml(tripChuCaiTen(tripTenNguoi(x))) + '</span>').join('')
      : '<span class="av" title="Chưa gán tổ lái" style="background:#fff;border:1.5px dashed #cbd5e1;color:#7b8796">+</span>';

    const nhom = groupFor(item);
    const co = tripThieuChangVe(raw) && nhom !== 'completed';
    const canhBao = (nhom === 'missing_return' || co)
      ? '<span class="tag t-amber">thiếu chặng về</span>'
      : (treHan ? '<span class="tag t-red" title="Tới nơi sau hạn khách cho phép">trễ hạn</span>'
        : (xongRoi && pod.co < pod.tong ? '<span class="tag t-red">thiếu POD</span>'
          : (thucTe && lechKH !== null && lechKH > 0
            ? '<span class="tag t-amber" title="Tới nơi chậm hơn kế hoạch nội bộ ' + lechKH + ' phút nhưng vẫn trong hạn khách">lệch KH +' + lechKH + "'</span>"
            : '')));

    const mauTd = treHan ? 'r' : (xongRoi ? 'g' : '');

    return '<tr' + (String(item.id) === String(activeTripReturnId) ? ' class="on"' : '')
      + ' tabindex="0" role="button"'
      + ' onclick="selectTripReturnWorkItem(decodeURIComponent(\'' + ma + '\'))"'
      + ' onkeydown="if(event.key===\'Enter\'){event.preventDefault();this.click();}"'
      + ' title="Bấm để mở hồ sơ chuyến ' + escapeHtml(String(item.id)) + '">'
      + '<td><span class="id">' + escapeHtml(String(item.id)) + '</span>'
      + '<span class="sub">' + dsDO.length + ' DO · ' + escapeHtml(journey.status_label || '') + '</span></td>'
      + '<td><span class="rt">' + tuyen + '</span>'
      + '<span class="sub">' + (dsDO.length ? escapeHtml(dsDO.join(' · ')) : 'chưa liên kết DO') + '</span></td>'
      + '<td><div class="crew">' + vongTron
      + '<span style="margin-left:8px;font-weight:600">' + escapeHtml(String(raw.vehicle_id || 'chưa gán xe')) + '</span></div>'
      + '<span class="sub">' + (toLai.length ? escapeHtml(toLai.map(tripTenNguoi).join(' + ')) : 'chưa gán tổ lái') + '</span></td>'
      + '<td><div class="prog"><i class="' + mauTd + '" style="width:' + td.phanTram + '%"></i></div>'
      + '<div class="pl">chặng ' + td.xong + '/' + td.tong
      + (co ? ' · <b style="color:#b45309">thiếu chặng về</b>' : '') + '</div></td>'
      + '<td class="eta ' + (treHan ? 'r' : '') + '" title="Hạn khách: ' + escapeHtml(gioNgay(han)) + (tripKeHoachToi(raw) ? ' · Kế hoạch: ' + escapeHtml(gioNgay(tripKeHoachToi(raw))) : '') + '">'
      + '<b>' + (thucTe ? '' : 'dự kiến ') + gio(toi) + '</b>'
      + '<span class="sub">hạn khách ' + (han ? gioNgay(han) : '—') + '</span></td>'
      + '<td><span class="pod">' + chamPOD + '</span>'
      + '<span class="sub">' + (pod.tong ? pod.co + '/' + pod.tong : '—') + '</span></td>'
      + '<td>' + canhBao + '</td>'
      + '</tr>';
  }).join('');

  host.innerHTML = '<table class="trips">'
    + '<colgroup><col class="c-id"><col class="c-rt"><col class="c-crew"><col class="c-prog"><col class="c-eta"><col class="c-pod"><col class="c-warn"></colgroup>'
    + '<thead><tr>'
    + '<th>Chuyến</th><th>Tuyến · DO</th><th>Xe · tổ lái</th>'
    + '<th>Tiến độ</th><th>Tới nơi / hạn</th><th>POD</th><th></th>'
    + '</tr></thead><tbody>' + dong + '</tbody></table>';
}

/* --------------------------------------------------------------------------
   HỒ SƠ CHUYẾN — đầu mục và bốn tab.
   -------------------------------------------------------------------------- */

//: Nhãn và màu của năm giai đoạn vòng đời.
const TLV2_GIAI_DOAN = {
  active: ['t-purple', 'Đang giao hàng'],
  waiting_return: ['t-amber', 'Chờ quay về'],
  missing_return: ['t-red', 'Thiếu kế hoạch về'],
  completed: ['t-green', 'Đã hoàn tất'],
};

function renderTripPh(selected, journey, nhom) {
  const host = document.getElementById('trip-return-detail-summary');
  if (!host) return;
  if (!selected) {
    host.innerHTML = '<div class="top"><h3>Hồ sơ chuyến</h3></div>'
      + '<div class="m">Chọn một chuyến bên trái</div>';
    return;
  }
  const raw = selected.raw || selected;
  const gd = TLV2_GIAI_DOAN[nhom] || ['', journey.status_label || ''];
  const pod = tripSoPOD(raw);
  const td = tripTienDo(raw);
  const toLai = [raw.driver_id, raw.co_driver_id].filter(Boolean);
  const chang = raw.legs || [];
  const tuyen = chang.length
    ? String(chang[0].origin || '') + ' → ' + String(chang[chang.length - 1].destination || '')
    : 'chưa có chặng';

  // Thẻ POD đỏ CHỈ khi chuyến đã xong mà còn đơn chưa ký. Chuyến đang chạy thì
  // chưa ký là bình thường.
  const podDo = td.phanTram === 100 && pod.tong && pod.co < pod.tong;

  host.innerHTML = '<div class="top"><h3>' + escapeHtml(String(selected.id)) + '</h3>'
    + '<span class="tag ' + gd[0] + '">' + escapeHtml(gd[1]) + '</span></div>'
    + '<div class="m">' + escapeHtml(tuyen)
    + ((raw.delivery_order_ids || []).length ? ' · ' + escapeHtml(raw.delivery_order_ids.join(' · ')) : '')
    + '</div>'
    + '<div class="chips">'
    + '<span class="tag">' + escapeHtml(String(raw.vehicle_id || 'chưa gán xe')) + '</span>'
    + '<span class="tag">chặng ' + td.xong + '/' + td.tong + '</span>'
    + (pod.tong ? '<span class="tag ' + (podDo ? 't-red' : 't-green') + '">POD '
      + pod.co + '/' + pod.tong + '</span>' : '')
    + '<span class="tag">' + (toLai.length ? toLai.length + ' người' : 'chưa có tổ lái') + '</span>'
    + (Number(raw.total_distance_km || 0)
      ? '<span class="tag">' + Number(raw.total_distance_km).toLocaleString('vi-VN') + ' km</span>' : '')
    + '</div>';
}

/** Bốn tab hồ sơ, vẽ bằng markup dải của bản mẫu. */
function renderTripDetailTabs() {
  const host = document.getElementById('trip-return-detail-tabs');
  if (!host) return;
  const tabs = [
    ['journey', 'Chặng đường'],
    ['resources', 'Xe & nhân sự'],
    ['pod', 'POD'],
    ['cost', 'Chi phí'],
    ['events', 'Sự kiện'],
  ];
  host.innerHTML = tabs.map(t =>
    '<button type="button" class="lt' + (activeTripReturnDetailTab === t[0] ? ' on' : '') + '"'
    + ' onclick="setTripReturnDetailTab(\'' + t[0] + '\')">' + t[1] + '</button>').join('');
}

/** Khối "việc cần làm tiếp" — lý do màn này tồn tại. */
function renderTripNext(selected, journey, nhom) {
  const raw = selected.raw || selected;
  const pod = tripSoPOD(raw);
  const td = tripTienDo(raw);
  let mau = 'blue';
  let chu = journey.next_action || 'Theo dõi chuyến.';
  let nhanNut = '';
  let viec = '';

  if (td.phanTram === 100 && pod.tong && pod.co < pod.tong) {
    mau = 'red';
    chu = pod.thieu.join(', ') + ' chưa có POD → chuyến không đối soát được, hoá đơn treo.';
    nhanNut = 'Ghi POD';
    viec = "switchView('tracking')";
  } else if (nhom === 'missing_return' || (tripThieuChangVe(raw) && nhom !== 'completed')) {
    mau = 'amber';
    const km = Number(raw.total_distance_km || 0);
    chu = 'Chưa có chặng về'
      + (km ? ' cho quãng ' + km.toLocaleString('vi-VN') + ' km — xe chạy rỗng về bãi.' : '.');
    nhanNut = 'Lập lượt về';
    viec = "openTripReturnAction('add-leg')";
  } else if (nhom === 'completed' && pod.tong && pod.co === pod.tong) {
    // Khong con buoc "hach toan" trong he nay: chu du an khong dung module ke
    // toan. Diem cuoi cua mot chuyen la HO SO DA HOAN TAT — so thu/chi tung dong
    // de ben cong no lap phieu.
    mau = 'green';
    chu = 'Đủ POD trên mọi lệnh. Hồ sơ hoàn tất sẵn sàng bàn giao cho bên công nợ.';
    nhanNut = 'Mở hồ sơ hoàn tất';
    viec = "switchView('delivery-completion')";
  } else if (nhom === 'active') {
    mau = 'blue';
    nhanNut = 'Mở Theo dõi';
    viec = "switchView('tracking')";
  }

  return '<div class="lbl">Việc cần làm tiếp</div>'
    + '<div class="next ' + mau + '">'
    + '<span>' + escapeHtml(chu) + '</span>'
    + (nhanNut ? '<button type="button" class="a" onclick="' + viec + '">'
      + escapeHtml(nhanNut) + '</button>' : '')
    + '</div>';
}

function renderTripReturnDetailPane(selected, journey) {
  const pane = document.getElementById('trip-return-detail-pane');
  if (!pane || !selected) return;
  const raw = selected.raw || selected;
  const safe = escapeHtml;

  if (activeTripReturnDetailTab === 'resources') {
    const dong = (ma, vai) => {
      if (!ma) return '';
      const ten = tripTenNguoi(ma);
      return '<div class="crewrow"><span class="av">' + safe(tripChuCaiTen(ten)) + '</span>'
        + '<div><b>' + safe(ten) + '</b><span>' + safe(vai) + ' · ' + safe(String(ma)) + '</span></div></div>';
    };
    const xe = (dispatchDanhSachXe ? dispatchDanhSachXe() : [])
      .find(v => String(v.id) === String(raw.vehicle_id));
    pane.innerHTML = '<div class="lbl">Tổ lái</div>'
      + (dong(raw.driver_id, 'Tài xế chính') || '<div class="empty">Chưa gán tài xế chính.</div>')
      + dong(raw.co_driver_id, 'Phụ xe')
      + '<div class="lbl">Xe</div>'
      + (raw.vehicle_id
        ? '<div class="crewrow"><span class="av v">🚚</span><div><b>' + safe(String(raw.vehicle_id)) + '</b>'
          + '<span>' + safe([
            xe && typeof tenLoaiXe === 'function' ? tenLoaiXe(xe.type) : '',
            xe && xe.depot ? String(xe.depot) : '',
            xe && xe.inspection_exp ? 'đăng kiểm ' + String(xe.inspection_exp) : '',
          ].filter(Boolean).join(' · ') || 'chưa có thông tin xe') + '</span></div></div>'
        : '<div class="empty">Chưa gán xe.</div>')
      + '<div class="lbl">Thời gian</div>'
      + '<div class="sum">'
      + '<div><span>Giờ xuất bến</span><b>' + safe(tripReturnFormatTime(raw.planned_departure_at)) + '</b></div>'
      + '<div><span>Xe dự kiến rảnh</span><b>' + safe(tripReturnFormatTime(raw.planned_return_at)) + '</b></div>'
      + '</div>';
    return;
  }

  if (activeTripReturnDetailTab === 'pod') {
    const pod = tripSoPOD(raw);
    const pods = tripReturnRowsForSelected(selected, ['pods', 'pod_records']);
    pane.innerHTML = '<div class="lbl">Đã ký ' + pod.co + ' trên ' + pod.tong + ' DO</div>'
      + (pods.length
        ? pods.map(p => '<div class="crewrow"><span class="av">✓</span>'
          + '<div><b>' + safe(String(p.do_id || p.location_text || '')) + '</b>'
          + '<span>' + safe(String(p.receiver_name || 'chưa có người nhận')) + ' · '
          + safe(tripReturnFormatTime(p.delivery_time)) + '</span></div></div>').join('')
        : '<div class="empty">Chưa có POD nào cho chuyến này.</div>')
      // Nói RÕ đơn nào còn thiếu, không chỉ nói "thiếu 1": người đi đòi POD cần
      // biết đòi cho đơn nào.
      + (pod.thieu.length
        ? '<div class="lbl">Còn thiếu POD</div>'
          + pod.thieu.map(x => '<div class="crewrow"><span class="av" style="background:#fdecec;color:#d32f2f">!</span>'
            + '<div><b>' + safe(x) + '</b><span>chưa ai ký nhận</span></div></div>').join('')
        : '');
    return;
  }

  if (activeTripReturnDetailTab === 'cost') {
    const goi = tripChiPhiThuc[String(raw.id)];
    if (goi === undefined) {
      napChiPhiChuyen(String(raw.id));
      pane.innerHTML = '<div class="empty">Đang nạp chi phí…</div>';
      return;
    }
    if (!goi || goi.error) {
      pane.innerHTML = '<div class="empty">Chưa có chi phí thực cho chuyến này. '
        + 'Chi phí được nhập ở bước hoàn tất giao hàng.</div>';
      return;
    }
    const dong = Array.isArray(goi.lines) ? goi.lines : [];
    const tienChu = v => Number(v || 0).toLocaleString('vi-VN');
    const lech = (thuc, kh) => {
      if (!kh) return { chu: '—', lop: '' };
      const p = Math.round((thuc - kh) / kh * 100);
      return { chu: (p > 0 ? '+' : '') + p + '%', lop: p > 0 ? 'up' : (p < 0 ? 'dn' : '') };
    };
    const tongThuc = Number(goi.total_amount || 0);
    // May chu khong tra ve tong ke hoach, nen cong tu cac dong: `original_amount`
    // la con so DUOC DUYET truoc chuyen, `actual_amount` la con so da chi.
    const tongKH = dong.reduce((t, l) => t + Number(l.original_amount || 0), 0);
    const t = lech(tongThuc, tongKH);
    pane.innerHTML = '<div class="lbl">Chi phí thực so kế hoạch</div><div class="cost">'
      + '<div class="crow"><span>Khoản mục</span><span class="n">Kế hoạch</span>'
      + '<span class="n">Thực</span><span class="dv">±</span></div>'
      + (dong.length
        ? dong.map(l => {
          const thuc = Number(l.actual_amount || 0);
          const kh = Number(l.original_amount || 0);
          const d = lech(thuc, kh);
          // Dong nao co `increase_amount` la mot khoan PHAT SINH — phai noi ra,
          // vi do la cho tien roi ra khoi ke hoach.
          const psinh = Number(l.increase_amount || 0);
          return '<div class="crow"' + (psinh ? ' style="color:#d32f2f"' : '') + '>'
            + '<span>' + safe(String(l.name || '—'))
            + (psinh ? ' <small>phát sinh ' + tienChu(psinh) + '</small>' : '') + '</span>'
            + '<span class="n">' + (kh ? tienChu(kh) : '—') + '</span>'
            + '<span class="n">' + tienChu(thuc) + '</span>'
            + '<span class="dv ' + d.lop + '">' + d.chu + '</span></div>';
        }).join('')
        : '<div class="crow"><span style="color:#7b8796">chưa có khoản mục nào</span>'
          + '<span class="n">—</span><span class="n">—</span><span class="dv">—</span></div>')
      + '<div class="crow tot"><span>Tổng</span>'
      + '<span class="n">' + (tongKH ? tienChu(tongKH) : '—') + '</span>'
      + '<span class="n">' + tienChu(tongThuc) + '</span>'
      + '<span class="dv ' + t.lop + '">' + t.chu + '</span></div>'
      + '</div>';
    return;
  }

  if (activeTripReturnDetailTab === 'events') {
    const events = [
      ...(Array.isArray(raw.events) ? raw.events : []),
      ...tripReturnRowsForSelected(selected, ['gps_events', 'tracking_events', 'execution_events'])
    ].sort((a, b) => String(b.event_time || b.created_at || '')
      .localeCompare(String(a.event_time || a.created_at || '')));
    pane.innerHTML = events.length
      ? '<div class="tl">' + events.map(e => '<div class="lg done"><div class="h">'
        + '<b>' + safe(statusLabel(e.event_type || e.type || e.status || 'Sự kiện')) + '</b>'
        + '<span>' + safe(tripReturnFormatTime(e.event_time || e.created_at)) + '</span></div></div>').join('')
        + '</div>'
      : '<div class="empty">Chưa có sự kiện vận hành cho chuyến này.</div>';
    return;
  }

  // CHẶNG THẬT của chuyến — trục dọc có mốc, đúng khối `.tl` của bản mẫu.
  const loai = { pickup: ['k-pick', 'LẤY'], delivery: ['k-drop', 'GIAO'], return: ['k-ret', 'VỀ'] };
  pane.innerHTML = '<div class="lbl">Chặng thật của chuyến</div>'
    + (journey.legs.length
      ? '<div class="tl">' + journey.legs.map(l => {
        const tt = String(l.status || '');
        const lop = tt === 'completed' ? 'done'
          : (['in_transit', 'arrived'].includes(tt) ? 'now' : '');
        const k = loai[String(l.leg_type || '')] || ['k-via', 'QUA'];
        return '<div class="lg ' + lop + '"><div class="h">'
          + '<b><span class="kind ' + k[0] + '">' + k[1] + '</span>'
          + safe(String(l.label || l.destination || '')) + '</b>'
          + '<span>' + safe(tripReturnFormatTime(l.actual_arrival_at || l.planned_arrival_at)) + '</span>'
          + '</div>'
          + '<div class="d">' + safe(String(l.route_label || ''))
          + (Number(l.distance_km || 0)
            ? ' · ' + Number(l.distance_km).toLocaleString('vi-VN', { maximumFractionDigits: 1 }) + ' km' : '')
          + (Number(l.avg_speed_kmh || 0)
            ? ' · ' + Number(l.avg_speed_kmh).toLocaleString('vi-VN', { maximumFractionDigits: 0 }) + ' km/h' : '')
          + ' · <small>' + safe(String(l.status_label || '')) + '</small></div></div>';
      }).join('')
      // Chuyến MỘT CHIỀU chưa lập lượt về thì vẽ thêm một mốc NÉT ĐỨT ở cuối:
      // chặng về là việc còn thiếu, và nó phải hiện ra ở đúng chỗ nó thuộc về
      // trong dòng thời gian, không phải nằm trong một cảnh báo rời.
      + (tripThieuChangVe(raw)
        ? '<div class="lg back"><div class="h">'
          + '<b><span class="kind k-ret">VỀ</span>Chặng về · chưa có kế hoạch</b><span>—</span></div>'
          + '<div class="d">Xe sẽ chạy rỗng về bãi nếu không ghép DO hàng nhập.</div></div>'
        : '')
      + '</div>'
      : '<div class="empty">Trip chưa có chặng vận chuyển.</div>');
}

function renderTripReturnCockpit() {
  if (!window.TmsCockpit || typeof document === 'undefined') return;
  const statusTabs = document.getElementById('trip-return-status-tabs');
  const queue = document.getElementById('trip-return-queue');
  const summary = document.getElementById('trip-return-detail-summary');
  const detailTabs = document.getElementById('trip-return-detail-tabs');
  const detailPane = document.getElementById('trip-return-detail-pane');
  const guidance = document.getElementById('trip-return-guidance-list');
  if (!statusTabs || !queue || !summary || !detailTabs || !detailPane) return;

  const cockpit = window.TmsCockpit.buildTripReturnCockpit(appState || {});
  const groupFor = item => window.TmsCockpit.getTripStatusGroup(item.raw || item);

  // Nạp POD khi ĐÃ có danh sách chuyến, không nạp ở `switchView`.
  //
  // Đã đo thật: gọi ở `switchView` thì `appState.transport_trips` còn rỗng, hàm
  // thoát sớm và KHÔNG BAO GIỜ thử lại — nên cột POD báo "0/1" cho cả những
  // chuyến thực sự đã ký POD. Đợi đến đây thì chắc chắn có mã đơn để hỏi.
  //
  // `dangNapPOD` chặn gọi lại vòng tròn: hàm này vẽ xong lại gọi chính nó.
  if (!dangNapPOD && !Array.isArray(appState?.pod_records) && cockpit.items.length) {
    dangNapPOD = true;
    napPODChoBangChuyen().finally(() => { dangNapPOD = false; renderTripReturnCockpit(); });
  }

  const counts = cockpit.items.reduce((result, item) => {
    const group = groupFor(item);
    result[group] = (result[group] || 0) + 1;
    return result;
  }, {});

  // DẢI VÒNG ĐỜI, không phải tab phẳng.
  //
  // Năm nhóm này không ngang hàng nhau — chúng là các chặng NỐI TIẾP của một
  // chuyến: đang giao hàng → chờ quay về → hoàn tất. "Thiếu kế hoạch về" là một
  // nhánh lệch ra khỏi dòng đó, không phải một chặng. Vẽ phẳng như tab thì mất
  // hết thứ tự đó, và người dùng phải tự đoán nhóm nào đứng trước nhóm nào.
  //
  // Bản mẫu `trip-lifecycle.html` vẽ chúng thành một dòng có mũi chuyển tiếp.
  const statusOptions = [
    { key: '', label: 'Tất cả', count: cockpit.items.length },
    { key: 'active', label: 'Đang giao hàng', count: counts.active || 0, buoc: true },
    { key: 'waiting_return', label: 'Chờ quay về', count: counts.waiting_return || 0, buoc: true },
    { key: 'completed', label: 'Đã hoàn tất', count: counts.completed || 0, buoc: true },
    // Đặt SAU cùng: đây là việc phải xử, không phải một chặng mà chuyến đi qua.
    { key: 'missing_return', label: 'Thiếu kế hoạch về', count: counts.missing_return || 0, alert: true }
  ];
  statusTabs.innerHTML = statusOptions.map((option, i) => {
    const truoc = statusOptions[i - 1];
    // Mũi chuyển tiếp chỉ đặt GIỮA hai chặng liền nhau của dòng, không đặt
    // trước "Tất cả" và không đặt trước nhánh lệch.
    const mui = (truoc && truoc.buoc && option.buoc)
      ? '<span class="arrow" aria-hidden="true">›</span>' : '';
    return mui + '<button type="button" class="lt'
      + (tripReturnStatusFilter === option.key ? ' on' : '')
      + (option.alert ? ' warn' : '') + '"'
      + ' onclick="setTripReturnStatusTab(\'' + option.key + '\')">'
      + escapeHtml(option.label) + ' <span class="n">' + option.count + '</span></button>';
  }).join('');

  const visibleItems = cockpit.items.filter(item => {
    const raw = item.raw || item;
    const journey = window.TmsCockpit.getTripJourneyPresentation(raw);
    const legText = (raw.legs || []).flatMap(leg => [leg.origin, leg.destination]).join(' ');
    const haystack = [item.id, item.subtitle, raw.vehicle_id, raw.driver_id, journey.status_label,
      journey.location_label, legText, ...(raw.delivery_order_ids || [])].join(' ').toLowerCase();
    return (!tripReturnSearchQuery || haystack.includes(tripReturnSearchQuery))
      && (!tripReturnStatusFilter || groupFor(item) === tripReturnStatusFilter);
  });

  // Dải số liệu đếm trên TOÀN BỘ chuyến đang mở, không đếm danh sách đã lọc —
  // một con số biến đổi theo chính cái lọc của nó thì không nói lên được gì.
  renderTripKpis(cockpit.items, groupFor);
  const loc = tripKpiFilter
    ? visibleItems.filter(item => tripNhomKpi(item.raw || item, groupFor(item)).has(tripKpiFilter))
    : visibleItems;

  let selected = loc.find(item => item.id === activeTripReturnId) || loc[0] || null;
  activeTripReturnId = selected?.id || '';
  renderTripBang(loc, groupFor);

  const demEl = document.getElementById('trip-count');
  if (demEl) demEl.textContent = loc.length + ' chuyến';
  const footEl = document.getElementById('trip-foot');
  if (footEl) {
    const ten = (statusOptions.find(o => o.key === tripReturnStatusFilter) || statusOptions[0]).label;
    footEl.textContent = 'Giai đoạn: ' + ten + ' · ' + loc.length + ' chuyến'
      + (tripKpiFilter ? ' · đang lọc theo thẻ số liệu' : '');
  }

  const searchEl = document.getElementById('trip-return-search');
  const statusEl = document.getElementById('trip-return-status-filter');
  if (searchEl && searchEl.value !== tripReturnSearchQuery) searchEl.value = tripReturnSearchQuery;
  if (statusEl && statusEl.value !== tripReturnStatusFilter) statusEl.value = tripReturnStatusFilter;

  if (!selected) {
    renderTripPh(null);
    detailTabs.innerHTML = '';
    detailPane.innerHTML = '<div class="empty">Hồ sơ gom đủ: chặng thật (lấy · giao · về), '
      + 'tổ lái, POD, chi phí thực so kế hoạch, và kế hoạch chặng về.</div>';
    return;
  }

  const raw = selected.raw || selected;
  const journey = window.TmsCockpit.getTripJourneyPresentation(raw);
  const nhom = groupFor(selected);

  renderTripPh(selected, journey, nhom);
  renderTripDetailTabs();

  // Khối "việc cần làm tiếp" đứng TRÊN các tab, vì nó là thứ người dùng cần đọc
  // trước — còn các tab là chỗ để đi sâu khi cần.
  const truoc = document.getElementById('trip-next-slot');
  const khoiNext = renderTripNext(selected, journey, nhom);
  if (truoc) truoc.innerHTML = khoiNext;
  else detailTabs.insertAdjacentHTML('beforebegin',
    '<div id="trip-next-slot">' + khoiNext + '</div>');

  renderTripReturnDetailPane(selected, journey);

  // Các nút việc ở CUỐI hồ sơ, đúng khối `.acts` của bản mẫu. Chỉ hiện nút nào
  // làm được ở giai đoạn này — hiện hết rồi để mờ thì người dùng vẫn phải đọc
  // qua những nút không dùng được.
  const nut = [];
  if (nhom === 'active') {
    nut.push(['', 'Mở Theo dõi realtime', "switchView('tracking')"]);
    nut.push(['', 'Báo sự cố', "switchView('tracking')"]);
  }
  const pod = tripSoPOD(raw);
  const td = tripTienDo(raw);
  if (nhom === 'completed' && pod.tong && pod.co < pod.tong) {
    nut.push(['red', 'Ghi POD thủ công', "switchView('tracking')"]);
  }
  if (nhom === 'completed' && pod.tong && pod.co === pod.tong) {
    nut.push(['p', 'Xem hồ sơ hoàn tất', "switchView('delivery-completion')"]);
  }
  if (tripThieuChangVe(raw) && nhom !== 'completed') {
    nut.push(['p', 'Lập lượt về cho chuyến này', "openTripReturnAction('add-leg')"]);
  }
  // XÁC NHẬN XE ĐÃ VỀ — bước cuối của một chuyến khứ hồi, và trước đây giao
  // diện không có chỗ nào bấm. Thiếu nó thì chuyến nằm mãi ở "đang giao", bước
  // quyết toán chi phí từ chối, và tiền của chuyến không vào báo cáo.
  if (tripChoXacNhanVe(raw)) {
    // `decodeURIComponent` ở ngoài, đúng lối đã dùng cho
    // `selectTripReturnWorkItem`: mã chuyến đi qua một thuộc tính HTML nên phải
    // mã hoá, và giải mã NGAY tại chỗ gọi để hàm nhận đúng mã gốc — mã hoá hai
    // lần thì máy chủ tra một mã không tồn tại.
    nut.push(['p', 'Xác nhận xe đã về bãi',
      "xacNhanXeDaVe(decodeURIComponent('"
      + encodeURIComponent(String(raw.id || '')) + "'))"]);
  }
  // HUỶ CHUYẾN — trước đây giao diện KHÔNG có nút này, và máy chủ cũng không
  // có đường nào. Nên khách huỷ hàng sau khi đã lập chuyến thì: huỷ lệnh giao
  // hàng bị chặn ("còn chuyến đang hoạt động") và màn Chuyến không có gì để
  // bấm — người dùng mắc hẳn ở giữa. Chỉ hiện khi chuyến còn huỷ được.
  if (tripCoTheHuy(raw)) {
    nut.push(['red', 'Huỷ chuyến',
      "huyChuyenVanTai(decodeURIComponent('"
      + encodeURIComponent(String(raw.id || '')) + "'))"]);
  }
  nut.push(['', 'Sửa ở Điều phối', "switchView('dispatch')"]);
  // "Xem 360° lô hàng" đã gỡ (10/09): chủ dự án bỏ module Shipment 360.
  detailPane.insertAdjacentHTML('beforeend', '<div class="acts">'
    + nut.map(n => '<button type="button"' + (n[0] ? ' class="' + n[0] + '"' : '')
      + ' onclick="' + n[2] + '">' + escapeHtml(n[1]) + '</button>').join('')
    + '</div>');

  if (guidance) {
    guidance.innerHTML = cockpit.guidance.map(item =>
      '<div style="padding:9px 10px; border-bottom:1px solid #e2e8f0; color:#475569; font-size:.8rem;">'
      + '<i class="fa-solid fa-circle-info" style="color:#2563eb;"></i> '
      + completionEscape(item) + '</div>').join('');
  }
}



/* ==========================================================================
   MÀN GIAO HÀNG & VẬN CHUYỂN — dải số liệu và bảng chuyến, theo bản mẫu
   `trip-lifecycle.html`.

   Vì sao đổi từ danh sách thẻ sang BẢNG: thẻ chỉ đọc được vài chục dòng. Đội xe
   này chạy hàng nghìn chuyến, và người đối soát cần so sáu thứ trên cùng một
   dòng mắt — tiến độ, hạn giao, POD, chặng về. Thẻ xếp dọc thì phải cuộn và
   nhớ, bảng thì quét ngang một lượt là thấy.

   Bản mẫu có sáu thẻ số liệu. Thẻ "Vượt chi phí kế hoạch" ở đây LƯỢC BỎ, vì
   đường lấy chi phí thực là `/api/tms/finance/trips/{id}/actual-cost` — MỘT lời
   gọi cho MỘT chuyến. Vẽ thẻ đó cho cả bảng nghĩa là gọi hàng nghìn lần mỗi lần
   mở màn, không dùng được ở quy mô thật. Chi phí thực vẫn xem được, nhưng ở
   khung hồ sơ bên phải cho đúng một chuyến đang chọn — một lời gọi.
   ========================================================================== */

let tripKpiFilter = '';
//: Chan goi lai vong tron khi nap POD: ham ve goi ham nap, ham nap ve xong lai
//: goi ham ve.
let dangNapPOD = false;

/** Nap POD cho ca bang chuyen bang MOT loi goi.
 *
 *  Duong `/api/pod/` tra ve toan bo POD. Duong theo tung don thi phai goi mot
 *  lan moi chuyen — o quy mo hang nghin chuyen la man hinh khong mo duoc.
 *
 *  Chiu loi im lang: thieu POD thi bang van ve duoc, chi la cot POD trong; con
 *  chan ca man hinh vi mot loi goi phu thi te hon.
 */
async function napPODChoBangChuyen() {
  const chuyen = (appState && Array.isArray(appState.transport_trips)) ? appState.transport_trips : [];
  const maDon = [...new Set(chuyen.flatMap(t => (t.delivery_order_ids || []).map(String)))];
  if (!maDon.length) {
    if (appState && typeof appState === 'object') appState.pod_records = [];
    return;
  }
  // Chia lo 200: may chu chan o dung con so do, vi mot cau `IN (...)` dai lam
  // PostgreSQL cham lap ke hoach. Chia o day de bang van ve duoc khi doi xe
  // chay hang nghin chuyen.
  const lo = [];
  for (let i = 0; i < maDon.length; i += 200) lo.push(maDon.slice(i, i + 200));
  try {
    const goi = await Promise.all(lo.map(async phan => {
      const tra = await fetch(
        API_BASE + '/api/pod-records?do_ids=' + encodeURIComponent(phan.join(',')),
        { headers: financeAuthHeaders() });
      if (!tra.ok) return [];
      const d = await tra.json();
      return (d && Array.isArray(d.records)) ? d.records : [];
    }));
    if (appState && typeof appState === 'object') appState.pod_records = goi.flat();
  } catch (loi) {
    console.warn('Khong nap duoc POD cho bang chuyen:', loi && loi.message);
    // Dat mang RONG, khong de `undefined`: dieu kien goi o ham ve xet
    // `Array.isArray`, nen de `undefined` thi no goi lai mai mai.
    if (appState && typeof appState === 'object') appState.pod_records = [];
  }
}

/** Hạn giao của một chuyến: mốc muộn nhất mà KHÁCH cho phép giao xong.
 *
 *  Lấy `delivery_due_at` backend đã tính (khung giao muộn nhất trên các DO của
 *  chuyến). Không lấy `planned_arrival_at`: đó là KẾ HOẠCH nội bộ lúc lập
 *  chuyến, không phải hạn với khách — so giờ tới thực tế với nó thì một chuyến
 *  giao đúng hẹn nhưng chậm hơn kế hoạch 2 giờ vẫn bị gán "trễ hạn" (lỗi cũ).
 *  Backend cũ chưa có trường này thì tra khung giao của DO đang nạp trên máy;
 *  không có nốt thì trả null và bảng ghi "—", KHÔNG suy ra trễ.
 */
function tripHanGiao(raw) {
  let moc = raw.delivery_due_at || null;
  if (!moc) {
    const ds = (appState && Array.isArray(appState.delivery_orders)) ? appState.delivery_orders : [];
    const ids = new Set((raw.delivery_order_ids || []).map(String));
    const han = ds.filter(d => ids.has(String(d.id)))
      .map(d => d.delivery_window_end || d.planned_arrival_at || d.delivery_date)
      .filter(Boolean).map(x => new Date(x)).filter(d => !isNaN(d));
    if (han.length) moc = new Date(Math.max.apply(null, han));
  }
  if (!moc) return null;
  const d = new Date(moc);
  return isNaN(d) ? null : d;
}

/** Kế hoạch tới nơi nội bộ của chuyến (để ghi chú "lệch kế hoạch", không để kết luận trễ). */
function tripKeHoachToi(raw) {
  const moc = raw.planned_arrival_at || (raw.legs || [])
    .filter(l => String(l.leg_type || '') === 'delivery')
    .map(l => l.planned_arrival_at).filter(Boolean).pop();
  if (!moc) return null;
  const d = new Date(moc);
  return isNaN(d) ? null : d;
}

/** Chuyến có trễ hạn với khách không: chỉ khi ĐÃ tới nơi và tới sau hạn khách. */
function tripTreHan(raw) {
  if (typeof raw.is_late === 'boolean') return raw.is_late && Boolean(raw.actual_arrival_at);
  const han = tripHanGiao(raw);
  const toi = tripGioToiNoi(raw);
  return Boolean(raw.actual_arrival_at && han && toi && toi > han);
}

/** Giờ tới nơi thực tế, hoặc dự kiến nếu chưa tới. */
function tripGioToiNoi(raw) {
  const moc = raw.actual_arrival_at || raw.planned_arrival_at;
  if (!moc) return null;
  const d = new Date(moc);
  return isNaN(d) ? null : d;
}

/** Chuyến có chặng về hay không.
 *
 *  Chạy rỗng là khoản lỗ lớn nhất và im lặng nhất của vận tải: xe vẫn tốn dầu,
 *  tài xế vẫn tính giờ, mà không có doanh thu. Nên "chưa có chặng về" phải là
 *  một con số đập vào mắt, không phải thứ phải đi tìm.
 */
/** Ba loại chặng về mà backend thật sự dùng.
 *
 * KHÔNG có loại nào tên `'return'`. Trước đây `tripThieuChangVe` so với đúng
 * chuỗi đó, nên phép so KHÔNG BAO GIỜ đúng: một chuyến đã có chặng về vẫn bị
 * coi là thiếu, và nút "Lập lượt về cho chuyến này" cứ hiện mãi. Xem
 * `RETURN_PURPOSES` và `leg_type` trong `services/tms_trip_service.py`.
 */
const LOAI_CHANG_VE = ['empty_return', 'backhaul', 'returned_goods'];

const changVeCua = raw => (raw.legs || [])
  .filter(l => LOAI_CHANG_VE.includes(String(l.leg_type || '')));

function tripThieuChangVe(raw) {
  // "Thiếu chặng về" chỉ có nghĩa với chuyến KHỨ HỒI / BACKHAUL. Chuyến một
  // chiều và nhiều điểm dừng không có chặng về theo định nghĩa — bản trước gắn
  // cảnh báo vàng lên MỌI chuyến một chiều, nên cả bảng nhấp nháy một cảnh báo
  // không ai làm gì được.
  const loai = String(raw.trip_type || 'one_way');
  if (loai === 'one_way' || loai === 'multi_stop') return false;
  if (loai === 'round_trip') return false;
  return changVeCua(raw).length === 0;
}

/**
 * Chuyến đã có chặng về nhưng CHƯA đóng — tức đang chờ xác nhận xe đã về bãi.
 *
 * VÌ SAO CẦN Ô NÀY. Chuyến khứ hồi chỉ chuyển sang `completed` khi xe đã về,
 * không phải khi hàng đã giao — và đúng: chặng về rỗng cũng tốn dầu và cũng
 * giữ xe. Nhưng trước đây giao diện KHÔNG CÓ chỗ nào xác nhận việc đó
 * (`openTripReturnAction` chỉ có `create-trip` và `add-leg`), nên chuyến khứ
 * hồi nằm mãi ở `in_transit`, và bước quyết toán chi phí từ chối với câu "Chỉ
 * được quyết toán chi phí sau khi chuyến đã hoàn thành POD". Kết quả là tiền
 * của chuyến đó không bao giờ vào báo cáo.
 */
function tripChoXacNhanVe(raw) {
  const ve = changVeCua(raw);
  if (!ve.length) return false;
  if (['completed', 'settled', 'cancelled'].includes(String(raw.status || ''))) return false;
  return ve.some(l => String(l.status || '') !== 'completed');
}

/**
 * Xác nhận xe đã về bãi — đóng các chặng về và hoàn thành chuyến.
 *
 * Đọc lại phiên bản chuyến NGAY TRƯỚC KHI gửi, chứ không dùng con số đang hiện
 * trên màn: giữa lúc mở hồ sơ và lúc bấm nút, một người khác có thể đã sửa
 * chuyến — và chốt `expected_version` tồn tại đúng để chặn việc ghi đè đó.
 */
/**
 * Chuyến này còn huỷ được không.
 *
 * Máy chủ là nơi quyết định thật (`POST /api/tms/trips/{id}/cancel` từ chối
 * chuyến đã hoàn tất, đã quyết toán, hoặc đã có POD). Hàm này chỉ để KHÔNG
 * hiện một cái nút chắc chắn sẽ bị từ chối — mời người dùng bấm một nút rồi
 * báo lỗi là tệ hơn không có nút.
 */
function tripCoTheHuy(chuyen) {
  const tt = String((chuyen && chuyen.status) || '').trim().toLowerCase();
  if (['completed', 'settled', 'cancelled'].includes(tt)) return false;
  // Đã có POD thì chuyến đó đã giao thật một phần — huỷ là xoá dấu vết.
  const pod = tripSoPOD(chuyen);
  if (pod && pod.co > 0) return false;
  return true;
}

/**
 * Huỷ một chuyến: trả xe, tổ lái và lệnh giao hàng về đúng chỗ.
 *
 * Đọc lại phiên bản chuyến NGAY TRƯỚC KHI gửi, cùng lý do như
 * `xacNhanXeDaVe`: giữa lúc mở hồ sơ và lúc bấm, người khác có thể đã sửa.
 */
window.huyChuyenVanTai = async function (tripId) {
  const ma = String(tripId || '').trim();
  if (!ma) {
    showToast('Chưa chọn chuyến nào để huỷ.');
    return;
  }
  const lyDo = window.prompt('Huỷ chuyến ' + ma + ' vì lý do gì?\n\n'
    + 'Xe và tổ lái sẽ được trả về sẵn sàng, và lệnh giao hàng của chuyến quay '
    + 'lại hàng đợi Điều phối (không bị xoá).', '');
  if (lyDo === null) return;
  if (!String(lyDo).trim()) {
    showToast('Phải ghi lý do huỷ chuyến — người đọc sổ sau này cần biết vì sao xe không chạy.');
    return;
  }
  try {
    const tra = await fetch(`${API_BASE}/api/tms/trips/${encodeURIComponent(ma)}`,
      { headers: financeAuthHeaders() });
    const goi = await tra.json().catch(() => ({}));
    if (!tra.ok) {
      showToast(goi?.detail?.message || goi?.message || 'Không đọc được chuyến để huỷ.');
      return;
    }
    const chuyen = goi?.data || goi || {};
    const ketQua = await fetch(
      `${API_BASE}/api/tms/trips/${encodeURIComponent(ma)}/cancel`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Idempotency-Key': 'huy-chuyen-' + ma + '-' + Date.now(),
          ...financeAuthHeaders(),
        },
        body: JSON.stringify({
          expected_version: Number(chuyen.version) || 1,
          reason: String(lyDo).trim(),
        }),
      });
    const d = await ketQua.json().catch(() => ({}));
    if (!ketQua.ok) {
      showToast(d?.detail?.message || d?.message || 'Không huỷ được chuyến.');
      return;
    }
    showToast('Đã huỷ chuyến ' + ma + '. Xe và tổ lái về sẵn sàng; lệnh giao hàng '
      + 'quay lại hàng đợi Điều phối.');
    if (typeof loadAllData === 'function') await loadAllData();
    renderTripReturnCockpit();
  } catch (error) {
    showToast('Không kết nối được backend để huỷ chuyến.');
  }
};

window.xacNhanXeDaVe = async function (tripId) {
  const ma = String(tripId || '').trim();
  if (!ma) {
    showToast('Chưa chọn chuyến nào để xác nhận.');
    return;
  }
  if (!window.confirm('Xác nhận xe của chuyến ' + ma + ' đã về bãi?\n\n'
    + 'Chuyến sẽ chuyển sang HOÀN THÀNH và giải phóng xe cùng tổ lái. '
    + 'Sau bước này mới quyết toán được chi phí thực của chuyến.')) return;
  try {
    const tra = await fetch(`${API_BASE}/api/tms/trips/${encodeURIComponent(ma)}`,
      { headers: financeAuthHeaders() });
    const goi = await tra.json().catch(() => ({}));
    if (!tra.ok) {
      showToast(goi?.detail?.message || goi?.message || 'Không đọc được chuyến để xác nhận.');
      return;
    }
    const chuyen = goi?.data || goi || {};
    const ketQua = await fetch(
      `${API_BASE}/api/tms/trips/${encodeURIComponent(ma)}/complete-return`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Idempotency-Key': 've-bai-' + ma + '-' + Date.now(),
          ...financeAuthHeaders(),
        },
        body: JSON.stringify({
          expected_version: Number(chuyen.version) || 1,
          actual_return_at: new Date().toISOString(),
        }),
      });
    const d = await ketQua.json().catch(() => ({}));
    if (!ketQua.ok) {
      showToast(d?.detail?.message || d?.message || 'Không xác nhận được xe đã về.');
      return;
    }
    showToast('Đã xác nhận xe về bãi. Chuyến chuyển sang hoàn thành — quyết toán '
      + 'chi phí thực ở màn Kế toán.');
    if (typeof loadAllData === 'function') await loadAllData();
    renderTripReturnCockpit();
  } catch (error) {
    showToast('Không kết nối được backend để xác nhận xe đã về.');
  }
};

/** Số DO của chuyến đã có POD, trên tổng số DO. */
function tripSoPOD(raw) {
  const dsDO = (raw.delivery_order_ids || []).map(String);
  if (!dsDO.length) return { co: 0, tong: 0, thieu: [] };
  const pods = (appState && Array.isArray(appState.pod_records)) ? appState.pod_records : [];
  const coPOD = new Set(pods.map(p => String(p.do_id || p.delivery_order_id || '')));
  return {
    co: dsDO.filter(x => coPOD.has(x)).length,
    tong: dsDO.length,
    // Trả về CẢ danh sách đơn còn thiếu, không chỉ con số. Người đi đòi POD cần
    // biết đòi cho đơn nào — "thiếu 1" thì họ vẫn phải mở hồ sơ ra đếm.
    thieu: dsDO.filter(x => !coPOD.has(x)),
  };
}

//: Chi phí thực của MỘT chuyến, nạp theo yêu cầu.
//:
//: Vì sao không nạp cho cả bảng: đường `/api/tms/finance/trips/{id}/actual-cost`
//: là MỘT lời gọi cho MỘT chuyến. Ở quy mô hàng nghìn chuyến thì nạp cho cả
//: bảng là hàng nghìn lời gọi mỗi lần mở màn — màn hình không mở được. Nên chi
//: phí chỉ nạp cho chuyến đang chọn, và đó cũng là lúc người dùng cần nó.
let tripChiPhiThuc = {};
let tripDangNapChiPhi = '';

async function napChiPhiChuyen(maTrip) {
  if (!maTrip || tripChiPhiThuc[maTrip] !== undefined) return;
  if (tripDangNapChiPhi === maTrip) return;
  tripDangNapChiPhi = maTrip;
  try {
    const tra = await fetch(
      `${API_BASE}/api/tms/finance/trips/${encodeURIComponent(maTrip)}/actual-cost`,
      { headers: financeAuthHeaders() });
    // Chưa có chi phí thực KHÔNG phải lỗi: chuyến đang chạy thì chưa ai nhập.
    // Ghi `null` để phân biệt "chưa có" với "chưa hỏi" — không thì hàm này gọi
    // lại mãi mỗi lần vẽ.
    //
    // Và phải BÓC lớp `data`: đường này trả về `{message, data}` chứ không phải
    // thân chi phí trần. Đọc thẳng `goi.lines` thì luôn rỗng và bảng chi phí
    // báo "chưa có cấu phần nào" trong khi máy chủ trả về đủ bốn dòng.
    if (tra.ok) {
      const goi = await tra.json();
      tripChiPhiThuc[maTrip] = (goi && goi.data !== undefined) ? goi.data : goi;
    } else tripChiPhiThuc[maTrip] = null;
  } catch (loi) {
    console.warn('Khong nap duoc chi phi cho chuyen', maTrip, loi && loi.message);
    tripChiPhiThuc[maTrip] = null;
  } finally {
    tripDangNapChiPhi = '';
    renderTripReturnCockpit();
  }
}

/** Tiến độ chuyến theo số chặng đã xong. */
function tripTienDo(raw) {
  const ds = raw.legs || [];
  if (!ds.length) return { xong: 0, tong: 0, phanTram: 0 };
  const xong = ds.filter(l => String(l.status || '') === 'completed').length;
  // Chang DANG CHAY dem mot nua. Truoc day mot chuyen co dung mot chang va
  // chang do dang chay thi thanh tien do RONG hoan toan — doc ra la "chua di
  // gi ca", trong khi xe dang tren duong. Nua thanh noi dung hon.
  const dangChay = ds.filter(l => ['in_transit', 'arrived'].includes(String(l.status || ''))).length;
  const phanTram = Math.round((xong + dangChay * 0.5) / ds.length * 100);
  return { xong: xong, tong: ds.length, phanTram: phanTram };
}

/** Nhóm của một chuyến cho dải số liệu. Một chuyến có thể thuộc nhiều nhóm. */
function tripNhomKpi(raw, nhomVongDoi) {
  const nhom = new Set();
  if (tripThieuChangVe(raw)) nhom.add('thieu-ve');

  // Chi dem la tre khi DA toi noi THUC TE va toi SAU HAN KHACH (khong so voi
  // ke hoach noi bo — xem `tripHanGiao`).
  if (tripTreHan(raw)) nhom.add('tre-han');

  const pod = tripSoPOD(raw);
  const xongRoi = nhomVongDoi === 'completed';
  if (xongRoi && pod.tong && pod.co < pod.tong) nhom.add('thieu-pod');
  if (xongRoi && pod.tong && pod.co === pod.tong) nhom.add('doi-soat-duoc');
  return nhom;
}

window.setTripKpiFilter = function (nhom) {
  tripKpiFilter = tripKpiFilter === nhom ? '' : String(nhom || '');
  renderTripReturnCockpit();
};

/**
 * Dải số liệu của màn Giao hàng & vận chuyển.
 *
 * Năm thẻ, và bấm được: mỗi thẻ lọc bảng chuyến theo đúng nhóm đó. Một dải số
 * mà bấm không ra gì thì chỉ chiếm chỗ.
 */

/**
 * Bảng chuyến, thay cho danh sách thẻ.
 *
 * Bảy cột đúng bằng bảy câu hỏi người đối soát phải trả lời cho từng chuyến:
 * chuyến nào, đi đâu chở đơn nào, ai lái xe nào, chạy tới đâu rồi, có kịp hạn
 * không, đã ký POD chưa. Cột "chi phí thực" của bản mẫu không có ở đây — xem
 * ghi chú ở đầu khối này.
 */


function setTripReturnStatusTab(status) {
  tripReturnStatusFilter = String(status || '');
  renderTripReturnCockpit();
}

function setTripReturnDetailTab(tab) {
  // `cost` là tab MỚI. Thiếu nó trong danh sách này thì bấm vào tab Chi phí lại
  // rơi về tab Chặng đường — nút bấm được mà không đi đâu, thứ khó hiểu hơn cả
  // một nút bị mờ.
  activeTripReturnDetailTab =
    ['journey', 'resources', 'pod', 'cost', 'events'].includes(tab) ? tab : 'journey';
  renderTripReturnCockpit();
}

function openTripReturnGuidanceModal() {
  renderTripReturnCockpit();
  const modal = document.getElementById('trip-return-guidance-modal');
  if (modal) modal.style.display = 'flex';
}

function closeTripReturnGuidanceModal() {
  const modal = document.getElementById('trip-return-guidance-modal');
  if (modal) modal.style.display = 'none';
}

function selectTripReturnWorkItem(id) {
  activeTripReturnId = id || '';
  renderTripReturnCockpit();
}

function filterTripReturnQueue() {
  const searchEl = document.getElementById('trip-return-search');
  const statusEl = document.getElementById('trip-return-status-filter');
  tripReturnSearchQuery = String(searchEl?.value || '').trim().toLowerCase();
  tripReturnStatusFilter = String(statusEl?.value || '').trim();
  renderTripReturnCockpit();
}

function clearTripReturnFilters() {
  tripReturnSearchQuery = '';
  tripReturnStatusFilter = '';
  renderTripReturnCockpit();
}

function tripReturnField(id) {
  return typeof document === 'undefined' ? null : document.getElementById(id);
}

function tripReturnNowLocal() {
  const date = new Date(Date.now() + 60 * 60 * 1000);
  const pad = value => String(value).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function tripReturnSelectedItem() {
  if (!window.TmsCockpit) return null;
  const cockpit = window.TmsCockpit.buildTripReturnCockpit(appState || {});
  return cockpit.items.find(item => item.id === activeTripReturnId) || cockpit.items[0] || null;
}

function tripReturnSetValue(id, value) {
  const el = tripReturnField(id);
  if (el) el.value = value == null ? '' : String(value);
}

function tripReturnIdempotencyKey(prefix) {
  tripReturnActionSequence += 1;
  return `${prefix}-${Date.now()}-${tripReturnActionSequence}`;
}

function tripReturnAllDeliveryOrders() {
  const tatCa = Array.isArray(eplDeliveryOrders) && eplDeliveryOrders.length
    ? eplDeliveryOrders
    : (Array.isArray(appState?.delivery_orders) ? appState.delivery_orders : []);
  // CHI LENH LAP CHUYEN DUOC: dang cho dieu phoi va CHUA thuoc chuyen nao con
  // song. Ban truoc liet ke moi lenh, nen mo hop thoai ra thay ca lenh da giao
  // xong va lenh da co chuyen — chon nham la lap chuyen thu hai cho cung mot
  // lenh, va mo lai FO cua chuyen cu (do duoc: o "Ma Freight Order" tu dien
  // FO-TRIP-...-C14-1 khi tao chuyen moi cho DO-2026-0014-DO02).
  const chuyen = Array.isArray(appState?.transport_trips) ? appState.transport_trips : [];
  const dangSong = new Set(['draft', 'planned', 'dispatched', 'in_transit']);
  const coChuyen = new Set();
  chuyen.forEach(t => {
    if (!dangSong.has(String(t.status || ''))) return;
    (t.delivery_order_ids || t.do_ids || []).forEach(x => coChuyen.add(String(x && x.id ? x.id : x)));
  });
  return tatCa.filter(d => String(d.canonical_status || 'pending') === 'pending' && !coChuyen.has(String(d.id)));
}

/**
 * Vận tốc kế hoạch cho một lệnh: lấy từ LOẠI XE trên báo giá của lệnh đó.
 *
 * Bản trước ghi cứng 45 km/h vào ô và vào cả payload (`|| 45`). Một xe lạnh 5
 * tấn và một đầu kéo 40' không cùng tốc độ, và con số đó đi thẳng vào giờ dự
 * kiến đến — thứ người điều phối và khách hàng nhìn. Loại xe có
 * `avg_speed_kmh` là dữ liệu gốc thật; không tra được thì ĐỂ TRỐNG và bắt
 * người dùng khai, không bịa.
 */
function vanTocKeHoachChoDO(doId) {
  const don = tripReturnDeliveryOrderById(doId);
  if (!don) return { toc: '', nguon: '' };
  const dsBaoGia = (Array.isArray(crmQuotations) && crmQuotations.length) ? crmQuotations
    : (Array.isArray(appState?.quotations) ? appState.quotations : []);
  const bg = dsBaoGia.find(q => String(q.id) === String(don.quotation_id || ''));
  const maLoai = bg && bg.vehicle_type_id;
  const loai = maLoai ? (vehTypes || []).find(t => String(t.id) === String(maLoai)) : null;
  if (loai && Number(loai.avg_speed_kmh) > 0) {
    return { toc: String(Number(loai.avg_speed_kmh)), nguon: `theo loại xe ${loai.name || loai.id}` };
  }
  return { toc: '', nguon: don.quotation_id ? 'báo giá chưa khai loại xe có tốc độ — nhập tay' : 'lệnh không có báo giá — nhập tay' };
}

function tripReturnAllRoutes() {
  return Array.isArray(eplRoutes) && eplRoutes.length
    ? eplRoutes
    : (Array.isArray(appState?.routes) ? appState.routes : []);
}

function tripReturnDeliveryOrderById(doId) {
  return tripReturnAllDeliveryOrders().find(item => String(item?.id || '') === String(doId || '')) || null;
}

function tripReturnRouteById(routeId) {
  return tripReturnAllRoutes().find(item => {
    const id = String(item?.id || '');
    const name = String(item?.name || '');
    return id === String(routeId || '') || name === String(routeId || '');
  }) || null;
}

/**
 * Mã DO đầu tiên đang chọn.
 *
 * Chỉ đọc ô ẩn `trip-return-do-ids`. Trước đây còn thử đọc
 * `trip-return-do-select` trước — ô chọn nhiều cũ — nhưng ô đó đã thay bằng bộ
 * chọn có tìm kiếm, và một ô không tồn tại thì `tripReturnBodyValue` trả về
 * chuỗi rỗng nên nhánh đó chỉ còn là một phép thử luôn thất bại.
 *
 * Ô ẩn vẫn là NGUỒN SỰ THẬT duy nhất: `submitTripReturnActionForm` cũng đọc
 * chính nó.
 */
function tripReturnSelectedDoId() {
  return tripReturnBodyValue('trip-return-do-ids').split(',')[0]?.trim() || '';
}

function tripReturnSourceFromSelectedDo() {
  const doId = tripReturnSelectedDoId();
  const deliveryOrder = tripReturnDeliveryOrderById(doId);
  const routeId = deliveryOrder?.route_id || deliveryOrder?.route || deliveryOrder?.route_code || '';
  const route = tripReturnRouteById(routeId);
  return { doId, deliveryOrder, route, routeId };
}

function tripReturnPrimaryStopDefaults(source, legs = []) {
  const deliveryOrder = source?.deliveryOrder || {};
  const lastLeg = legs[legs.length - 1] || {};
  return {
    sequence_no: Number(lastLeg.sequence_no || legs.length || 1),
    stop_name: deliveryOrder.delivery_location || deliveryOrder.delivery_address || deliveryOrder.destination || lastLeg.destination || '',
    receiver_name: deliveryOrder.receiver_name || deliveryOrder.consignee_name || deliveryOrder.contact_person || deliveryOrder.customer_id || '',
    receiver_phone: deliveryOrder.receiver_phone || deliveryOrder.consignee_phone || deliveryOrder.contact_phone || deliveryOrder.phone || '',
    delivery_note: deliveryOrder.delivery_note || deliveryOrder.note || ''
  };
}

function hydrateTripReturnStopFields(source, legs = []) {
  const defaults = tripReturnPrimaryStopDefaults(source, legs);
  [
    ['trip-return-stop-name', defaults.stop_name],
    ['trip-return-receiver-name', defaults.receiver_name],
    ['trip-return-receiver-phone', defaults.receiver_phone],
    ['trip-return-delivery-note', defaults.delivery_note]
  ].forEach(([id, value]) => {
    const el = tripReturnField(id);
    if (el && !el.value) el.value = value || '';
  });
}

function tripReturnStopPlan(legs = null) {
  const source = tripReturnSourceFromSelectedDo();
  const resolvedLegs = Array.isArray(legs) && legs.length ? legs : buildTripReturnLegsFromRoute(source);
  const defaults = tripReturnPrimaryStopDefaults(source, resolvedLegs);
  const stopName = tripReturnBodyValue('trip-return-stop-name') || defaults.stop_name;
  const receiverName = tripReturnBodyValue('trip-return-receiver-name') || defaults.receiver_name;
  const receiverPhone = tripReturnBodyValue('trip-return-receiver-phone') || defaults.receiver_phone;
  const deliveryNote = tripReturnBodyValue('trip-return-delivery-note') || defaults.delivery_note;
  const sequenceNo = defaults.sequence_no || 1;
  if (![stopName, receiverName, receiverPhone, deliveryNote].some(Boolean)) return [];
  return [{
    sequence_no: sequenceNo,
    stop_name: stopName || undefined,
    receiver_name: receiverName || undefined,
    receiver_phone: receiverPhone || undefined,
    delivery_note: deliveryNote || undefined,
    dwell_minutes: tripReturnNumberValue('trip-return-dwell', 30) || 0
  }];
}

function tripReturnIsoFromLocal(value) {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toISOString();
}

function tripReturnFormatPreviewTime(localValue, offsetMinutes) {
  if (!localValue) return '-';
  const date = new Date(localValue);
  if (Number.isNaN(date.getTime())) return '-';
  date.setMinutes(date.getMinutes() + offsetMinutes);
  return date.toLocaleString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
}

function buildTripReturnLegsFromRoute(source) {
  const deliveryOrder = source?.deliveryOrder || null;
  const route = source?.route || null;
  const rawSegments = route ? routeSegments(route) : [];
  const fallbackDistance = route ? routeTotalDistanceKm(route) : parseFloat(deliveryOrder?.distance_km || deliveryOrder?.total_distance_km || 0) || 0;
  const segments = rawSegments.length
    ? rawSegments
    : [{
      from: deliveryOrder?.origin || route?.origin || 'Điểm đi',
      to: deliveryOrder?.destination || route?.destination || 'Điểm đến',
      distance_km: fallbackDistance
    }];

  return segments.map((segment, index) => ({
    id: `LEG-${Date.now().toString().slice(-6)}-${index + 1}`,
    sequence_no: index + 1,
    leg_type: 'delivery',
    origin: routeSegmentFrom(segment),
    destination: routeSegmentTo(segment),
    distance_km: routeSegmentDistanceKm(segment)
  })).filter(leg => leg.origin && leg.destination);
}

// `populateTripReturnDoSelect` CHUYỂN sang js/do-picker.js.
//
// Ban cu la mot o <select multiple size="6">: sau dong co dinh (thua cho khi it
// DO, khong du cho khi nhieu), khong tim duoc, va bam nham mot dong la mat het
// nhung dong da chon. Ban v2 co o tim va o tich, nen phai dung HTML nhieu lop —
// de rieng mot tep thi doc duoc dung cai se chay.

function populateTripReturnReturnSelectors() {
  const source = tripReturnSourceFromSelectedDo();
  const routeSelect = tripReturnField('trip-return-return-route-select');
  const doSelect = tripReturnField('trip-return-return-do-select');
  if (routeSelect) routeSelect.innerHTML = '<option value="">Chon tuyen chieu ve...</option>' + tripReturnAllRoutes().map(route => `<option value="${doBoardEscape(route.id || '')}">${doBoardEscape(route.id || '')} - ${doBoardEscape(route.name || route.id || '')}</option>`).join('');
  if (doSelect) doSelect.innerHTML = '<option value="">Chon DO chieu ve...</option>' + tripReturnAllDeliveryOrders().filter(order => String(order.id || '') !== String(source.doId || '')).map(order => `<option value="${doBoardEscape(order.id || '')}">${doBoardEscape(order.id || '')} - ${doBoardEscape(order.customer_id || order.customer_name || '')}</option>`).join('');
}

function syncTripReturnTripType() {
  const mode = tripReturnBodyValue('trip-return-action-mode') || 'create-trip';
  const type = tripReturnBodyValue('trip-return-trip-type') || 'one_way';
  const purpose = tripReturnField('trip-return-purpose');
  if (mode === 'create-trip' && purpose) {
    if (type === 'round_trip' && purpose.value === 'none') purpose.value = 'empty_return';
    if (type === 'backhaul') purpose.value = 'backhaul';
    if (type === 'one_way' || type === 'multi_stop') purpose.value = 'none';
    purpose.disabled = type === 'one_way' || type === 'multi_stop';
  }
  syncTripReturnPurpose();
}

function hydrateTripReturnRoutePreview() {
  const source = tripReturnSourceFromSelectedDo();
  const { doId, deliveryOrder, route, routeId } = source;
  const badge = tripReturnField('trip-return-route-badge');
  const sourceInput = tripReturnField('trip-return-route-source');
  const preview = tripReturnField('trip-return-route-preview');
  const speed = tripReturnNumberValue('trip-return-speed', 0) || 0;
  const dwell = tripReturnNumberValue('trip-return-dwell', 30) || 0;
  const departure = tripReturnBodyValue('trip-return-departure');
  const mode = tripReturnBodyValue('trip-return-action-mode') || 'create-trip';
  const purpose = tripReturnBodyValue('trip-return-purpose') || 'none';
  const returnRoute = tripReturnRouteById(tripReturnBodyValue('trip-return-return-route-select'));
  const returnConfig = tripReturnField('trip-return-return-config');
  const returnWarning = tripReturnField('trip-return-return-warning');
  if (returnConfig) returnConfig.style.display = mode === 'create-trip' && purpose !== 'none' ? 'block' : 'none';
  if (returnWarning) returnWarning.textContent = purpose !== 'none' && !returnRoute
    ? 'Chọn tuyến chiều về trong Dữ liệu gốc để hệ thống tính giờ dự kiến và lúc xe sẵn sàng.'
    : '';

  // KHÔNG ghi đè `trip-return-do-ids` bằng MỘT mã DO.
  //
  // Ô chọn DO cho chọn nhiều — cái mạnh nhất của luồng này là gộp các DO cùng
  // một tuyến vào một Trip. Hàm này chỉ vẽ phần xem trước tuyến, và nó lấy DO
  // ĐẦU TIÊN làm nguồn tuyến (đúng, vì mọi DO phải cùng tuyến). Nhưng nếu nó
  // ghi mã đó vào ô ẩn thì danh sách bị cắt còn một, và lúc gửi lên sẽ MẤT các
  // DO còn lại — chọn 3 DO chỉ tạo Trip cho 1.
  //
  // Ô ẩn do `capNhatDSDOChonTrongHopThoai` và `populateTripReturnDoSelect` giữ;
  // ở đây chỉ điền khi nó đang trống (mở form từ chỗ khác, chưa qua ô chọn).
  if (doId && !tripReturnBodyValue('trip-return-do-ids')) {
    tripReturnSetValue('trip-return-do-ids', doId);
  }

  if (badge) {
    badge.textContent = route ? 'Lấy từ Master Data' : (deliveryOrder ? 'DO thiếu tuyến' : 'Chưa chọn DO');
    badge.className = `fiori-status ${route ? 'fiori-status-approved' : 'fiori-status-pending'}`;
  }
  if (sourceInput) {
    sourceInput.textContent = route
      ? `${route.id || routeId} · ${route.name || routeId}`
      : (deliveryOrder ? `${routeId || 'chưa có tuyến'} theo lệnh ${deliveryOrder.id}` : '');
  }
  if (!preview) return;

  if (!deliveryOrder) {
    preview.innerHTML = '<div style="border:1px dashed #cbd5e1; border-radius:10px; padding:12px; color:#64748b;">Chọn lệnh giao hàng để xem các chặng lấy từ tuyến trong Dữ liệu gốc.</div>';
    return;
  }

  const legs = buildTripReturnLegsFromRoute(source);
  if (!legs.length || !route) {
    preview.innerHTML = '<div style="border:1px dashed #fbbf24; background:#fffbeb; border-radius:10px; padding:12px; color:#92400e; font-weight:800;">DO này chưa có tuyến/chặng trong Master Data. Vào Master Data cấu hình route trước khi tạo Trip.</div>';
    return;
  }
  hydrateTripReturnStopFields(source, legs);
  const stopBySequence = new Map(tripReturnStopPlan(legs).map(stop => [Number(stop.sequence_no), stop]));

  let elapsed = 0;
  let totalKm = 0;
  const rows = legs.map(leg => {
    const stop = stopBySequence.get(Number(leg.sequence_no)) || {};
    const travelMinutes = speed > 0 ? Math.round((Number(leg.distance_km || 0) / speed) * 60) : 0;
    const startText = tripReturnFormatPreviewTime(departure, elapsed);
    elapsed += travelMinutes;
    const endText = tripReturnFormatPreviewTime(departure, elapsed);
    elapsed += dwell;
    totalKm += Number(leg.distance_km || 0);
    return `
      <div style="display:grid; grid-template-columns:44px minmax(0,1fr) 92px 124px; gap:10px; align-items:center; padding:10px 0; border-top:1px solid #e2e8f0;">
        <div style="width:30px; height:30px; border-radius:999px; background:#eff6ff; color:#2563eb; display:flex; align-items:center; justify-content:center; font-weight:900;">${leg.sequence_no}</div>
        <div style="min-width:0;">
          <div style="font-weight:900; color:#0f172a; overflow-wrap:anywhere;">${doBoardEscape(leg.origin)} <span style="color:#64748b;">â†’</span> ${doBoardEscape(leg.destination)}</div>
          <div style="font-size:.78rem; color:#64748b; margin-top:3px;">${doBoardEscape(startText)} - ${doBoardEscape(endText)}</div>
          ${stop.receiver_name || stop.stop_name ? `<div style="font-size:.77rem; color:#047857; margin-top:4px; font-weight:800;"><i class="fa-solid fa-user-check"></i> ${doBoardEscape(stop.stop_name || leg.destination)}${stop.receiver_name ? ` • ${doBoardEscape(stop.receiver_name)}` : ''}${stop.receiver_phone ? ` • ${doBoardEscape(stop.receiver_phone)}` : ''}</div>` : ''}
          ${stop.delivery_note ? `<div style="font-size:.75rem; color:#64748b; margin-top:3px;">${doBoardEscape(stop.delivery_note)}</div>` : ''}
        </div>
        <div style="text-align:right;"><span class="fiori-status fiori-status-pending">${doBoardEscape(formatRouteKm(leg.distance_km))} km</span></div>
        <div style="font-size:.78rem; color:#64748b; text-align:right;">Dừng ${doBoardEscape(dwell)} phút</div>
      </div>
    `;
  }).join('');

  const firstLeg = legs[0];
  tripReturnSetValue('trip-return-origin', firstLeg?.origin || '');
  tripReturnSetValue('trip-return-destination', firstLeg?.destination || '');
  tripReturnSetValue('trip-return-distance', firstLeg?.distance_km || 0);
  let returnRows = '';
  if (mode === 'create-trip' && purpose !== 'none' && returnRoute) {
    const returnLegs = buildTripReturnLegsFromRoute({ route: returnRoute, routeId: returnRoute.id });
    returnRows = `
      <div style="margin-top:12px; padding-top:10px; border-top:2px solid #fed7aa; color:#9a3412; font-weight:900;">&#8617; Chiều về · ${doBoardEscape(returnRoute.name || returnRoute.id || '')}</div>
      ${returnLegs.map(leg => `
        <div style="display:grid; grid-template-columns:44px minmax(0,1fr) 92px 124px; gap:10px; align-items:center; padding:10px 0; border-top:1px solid #ffedd5;">
          <div style="width:30px; height:30px; border-radius:999px; background:#fff7ed; color:#c2410c; display:flex; align-items:center; justify-content:center; font-weight:900;">&#8617;</div>
          <div style="min-width:0; font-weight:900; color:#7c2d12; overflow-wrap:anywhere;">${doBoardEscape(leg.origin)} <span style="color:#9a3412;">-&gt;</span> ${doBoardEscape(leg.destination)}</div>
          <div style="text-align:right;"><span class="fiori-status fiori-status-pending">${doBoardEscape(formatRouteKm(leg.distance_km))} km</span></div>
          <div style="font-size:.78rem; color:#9a3412; text-align:right;">Dừng ${doBoardEscape(dwell)} phút</div>
        </div>
      `).join('')}
    `;
  }
  preview.innerHTML = `
    <div style="display:flex; justify-content:space-between; gap:10px; align-items:center; flex-wrap:wrap; padding:8px 0;">
      <strong style="color:#0f172a;">${doBoardEscape(route.name || route.id || 'Tuyến vận chuyển')}</strong>
      <span style="display:flex; gap:6px; flex-wrap:wrap;">
        <span class="fiori-status fiori-status-pending">${doBoardEscape(formatRouteKm(totalKm))} km</span>
        <span class="fiori-status fiori-status-approved">${legs.length} chặng</span>
      </span>
    </div>
    ${rows}
    ${returnRows}
  `;
}

/**
 * `preferredDoId` nhận một mã DO, hoặc một MẢNG mã khi mở từ thanh chọn DO
 * ở màn Lập kế hoạch — ở đó người dùng tick nhiều DO cùng một tuyến để gộp
 * vào một Trip.
 */
function openTripReturnAction(action, preferredDoId = '') {
  const dsUuTien = Array.isArray(preferredDoId)
    ? preferredDoId.map(String).filter(Boolean)
    : (preferredDoId ? [String(preferredDoId)] : []);
  const modal = tripReturnField('trip-return-action-modal');
  if (!modal) {
    showToast('Thiếu form Trip/Return trên giao diện. Vui lòng tải lại trang.');
    return;
  }
  if (modal.parentElement !== document.body) {
    document.body.appendChild(modal);
  }

  const selected = tripReturnSelectedItem();
  const mode = action === 'add-leg' ? 'add-leg' : 'create-trip';
  const raw = selected?.raw || selected || {};
  const tripId = raw.id || selected?.id || '';
  const doIds = raw.delivery_order_ids || raw.do_ids || (raw.do_id ? [raw.do_id] : []);
  const nextSequence = Array.isArray(raw.legs) ? raw.legs.length + 1 : 1;
  const generatedTripId = `TRIP-${FormatUtils.dateInputValue().replaceAll('-', '')}-${Date.now().toString().slice(-5)}`;
  const generatedLegId = `LEG-${Date.now().toString().slice(-6)}`;
  const selectedDoId = dsUuTien[0]
    || (Array.isArray(doIds) ? doIds[0] : String(doIds || '').split(',')[0]?.trim());
  // Mở từ thanh chọn DO thì lấy TẤT CẢ mã đã tick, không chỉ mã đầu.
  const dsDat = dsUuTien.length ? dsUuTien : (selectedDoId ? [selectedDoId] : []);
  const preferredOrder = tripReturnDeliveryOrderById(selectedDoId);

  tripReturnSetValue('trip-return-action-mode', mode);
  tripReturnSetValue('trip-return-trip-id', mode === 'add-leg' ? tripId : generatedTripId);
  tripReturnSetValue('trip-return-fo-id', mode === 'add-leg' ? (raw.freight_order_id || raw.fo_id || '') : '');
  populateTripReturnDoSelect(dsDat);
  tripReturnSetValue('trip-return-do-ids', dsDat.join(','));
  tripReturnSetValue('trip-return-trip-type', raw.trip_type || (mode === 'add-leg' ? 'round_trip' : 'one_way'));
  tripReturnSetValue('trip-return-purpose', mode === 'add-leg' ? 'empty_return' : 'none');
  tripReturnSetValue('trip-return-leg-type', mode === 'add-leg' ? 'empty_return' : 'delivery');
  tripReturnSetValue('trip-return-leg-id', generatedLegId);
  tripReturnSetValue('trip-return-leg-seq', nextSequence);
  tripReturnSetValue('trip-return-origin', raw.destination || '');
  tripReturnSetValue('trip-return-destination', raw.origin || '');
  tripReturnSetValue('trip-return-distance', raw.total_distance_km || raw.distance_km || '');
  {
    const vt = vanTocKeHoachChoDO(selectedDoId);
    tripReturnSetValue('trip-return-speed', vt.toc);
    const goiY = tripReturnField('trip-return-speed-hint');
    if (goiY) goiY.textContent = vt.nguon;
  }
  tripReturnSetValue('trip-return-dwell', '30');
  tripReturnSetValue('trip-return-departure', preferredOrder?.pickup_window_start || preferredOrder?.pickup_date || tripReturnNowLocal());
  tripReturnSetValue('trip-return-version', raw.version || 1);
  tripReturnSetValue('trip-return-stop-name', '');
  tripReturnSetValue('trip-return-receiver-name', '');
  tripReturnSetValue('trip-return-receiver-phone', '');
  tripReturnSetValue('trip-return-delivery-note', '');
  populateTripReturnReturnSelectors();

  const title = tripReturnField('trip-return-action-title');
  if (title) {
    const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
    title.textContent = mode === 'add-leg'
      ? (lang === 'la' ? 'ເພີ່ມໄລຍະ / ຖ້ຽວກັບ / backhaul ສຳລັບ Trip' : (lang === 'en' ? 'Add Leg / Return / Backhaul for Trip' : 'Thêm chặng / lượt về / backhaul cho Trip'))
      : (lang === 'la' ? 'ສ້າງ Trip / ເພີ່ມໄລຍະຂົນສົ່ງ' : (lang === 'en' ? 'Create trip from delivery orders' : 'Tạo chuyến từ lệnh giao hàng'));
  }
  hydrateTripReturnRoutePreview();
  syncTripReturnTripType();
  modal.style.display = 'flex';
}

function syncTripReturnPurpose() {
  const purpose = tripReturnBodyValue('trip-return-purpose') || 'none';
  const legType = purpose === 'empty_return' ? 'empty_return' : 'backhaul';
  tripReturnSetValue('trip-return-leg-type', legType);
  const note = tripReturnField('trip-return-delivery-note');
  if (note && purpose === 'returned_goods' && !note.value.trim()) {
    note.value = 'Nhận hàng hoàn từ DO nguồn';
  }
  const returnDoSelect = tripReturnField('trip-return-return-do-select');
  const returnDoWrap = tripReturnField('trip-return-return-do-wrap');
  // Bộ chọn DO không phải một `<select>` nữa nên không đặt `required` lên nó
  // được. Chỗ chặn thật vẫn còn và đúng hơn: `submitTripReturnActionForm` từ
  // chối khi ô ẩn `trip-return-do-ids` rỗng, và nói rõ là chưa chọn DO nào —
  // thay vì một dòng nhắc mặc định của trình duyệt.
  if (returnDoSelect) {
    returnDoSelect.required = purpose === 'backhaul' || purpose === 'returned_goods';
    returnDoSelect.setAttribute('aria-required', returnDoSelect.required ? 'true' : 'false');
  }
  if (returnDoWrap) {
    returnDoWrap.style.display = purpose === 'backhaul' || purpose === 'returned_goods' ? 'block' : 'none';
  }
  hydrateTripReturnRoutePreview();
}

function closeTripReturnActionForm() {
  const modal = tripReturnField('trip-return-action-modal');
  if (modal) modal.style.display = 'none';
}

function tripReturnBodyValue(id) {
  return (tripReturnField(id)?.value || '').trim();
}

function tripReturnNumberValue(id, fallback = null) {
  const value = tripReturnBodyValue(id);
  if (!value) return fallback;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

async function submitTripReturnActionForm() {
  const mode = tripReturnBodyValue('trip-return-action-mode') || 'create-trip';
  const tripId = tripReturnBodyValue('trip-return-trip-id');
  const doIds = tripReturnBodyValue('trip-return-do-ids')
    .split(',')
    .map(value => value.trim())
    .filter(Boolean);
  const purpose = tripReturnBodyValue('trip-return-purpose') || 'none';
  syncTripReturnPurpose();
  if (mode === 'add-leg' && purpose !== 'empty_return' && !doIds[0]) {
    showToast('Chặng ghép DO hoặc nhận hàng hoàn phải chọn DO nguồn.');
    return;
  }
  const headers = {
    'Content-Type': 'application/json',
    'Idempotency-Key': tripReturnIdempotencyKey(mode),
    ...financeAuthHeaders()
  };

  if (mode === 'add-leg') {
    const payload = {
      id: tripReturnBodyValue('trip-return-leg-id') || undefined,
      do_id: doIds[0] || undefined,
      sequence_no: tripReturnNumberValue('trip-return-leg-seq', 1),
      leg_type: purpose === 'empty_return' ? 'empty_return' : 'backhaul',
      origin: tripReturnBodyValue('trip-return-origin'),
      destination: tripReturnBodyValue('trip-return-destination'),
      distance_km: tripReturnNumberValue('trip-return-distance', 0),
      avg_speed_kmh: tripReturnNumberValue('trip-return-speed', 0),
      dwell_minutes: tripReturnNumberValue('trip-return-dwell', 0),
      stop_name: tripReturnBodyValue('trip-return-stop-name') || undefined,
      receiver_name: tripReturnBodyValue('trip-return-receiver-name') || undefined,
      receiver_phone: tripReturnBodyValue('trip-return-receiver-phone') || undefined,
      delivery_note: tripReturnBodyValue('trip-return-delivery-note') || undefined,
      planned_departure_at: tripReturnBodyValue('trip-return-departure') || undefined,
      expected_version: tripReturnNumberValue('trip-return-version', 1)
    };
    try {
      const response = await fetch(`${API_BASE}/api/tms/trips/${encodeURIComponent(tripId)}/legs`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload)
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) {
        const message = result?.detail?.message || result?.message || 'Không lưu được chặng. Kiểm tra Master Data và dữ liệu bắt buộc.';
        showToast(message);
        return;
      }
      showToast('Đã lưu chặng Trip/Return.');
      closeTripReturnActionForm();
      if (typeof loadAllData === 'function') await loadAllData();
      renderTripReturnCockpit();
    } catch (error) {
      showToast('Không kết nối được backend Trip/Return. Kiểm tra server API đang chạy.');
    }
    return;
  }

  if (!doIds.length) {
    showToast('Chọn lệnh giao hàng trước khi tạo chuyến.');
    return;
  }
  if (!(tripReturnNumberValue('trip-return-speed', 0) > 0)) {
    showToast('Nhập vận tốc kế hoạch (km/h). Loại xe trên báo giá chưa có tốc độ nên hệ thống không tự điền.');
    tripReturnField('trip-return-speed')?.focus();
    return;
  }
  const returnRouteId = tripReturnBodyValue('trip-return-return-route-select');
  const returnDoId = tripReturnBodyValue('trip-return-return-do-select');
  if (purpose !== 'none' && !returnRouteId) {
    showToast('Chọn tuyến chiều về từ Route Master để tính ETA và ngày xe sẵn sàng.');
    return;
  }
  if ((purpose === 'backhaul' || purpose === 'returned_goods') && !returnDoId) {
    showToast('Chọn DO chiều về cho chuyến backhaul hoặc nhận hàng hoàn.');
    return;
  }

  const payload = {
    id: tripId,
    trip_type: tripReturnBodyValue('trip-return-trip-type') || 'one_way',
    do_ids: doIds,
    planned_departure_at: tripReturnIsoFromLocal(tripReturnBodyValue('trip-return-departure')) || undefined,
    avg_speed_kmh: String(tripReturnNumberValue('trip-return-speed', 0)),
    dwell_minutes: tripReturnNumberValue('trip-return-dwell', 30) || 0,
    stop_plan: tripReturnStopPlan(),
    return_purpose: purpose,
    return_route_id: returnRouteId || undefined,
    return_do_id: returnDoId || undefined
  };

  try {
    const response = await fetch(`${API_BASE}/api/tms/trips/from-delivery-orders`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload)
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      const message = result?.detail?.message || result?.message || 'Không tạo được Trip từ DO. Kiểm tra DO pending, tuyến Master Data và khung giờ lấy/giao.';
      showToast(message);
      return;
    }

    showToast('Đã tạo Trip từ DO và tự sinh chặng theo tuyến Master Data.');
    closeTripReturnActionForm();
    if (typeof loadAllData === 'function') await loadAllData();
    if (typeof loadDispatchBoard === 'function') await loadDispatchBoard();
    renderTripReturnCockpit();
  } catch (error) {
    showToast('Không kết nối được backend Trip/Return. Kiểm tra server API đang chạy.');
  }
}

window.selectTripReturnWorkItem = selectTripReturnWorkItem;
window.openTripReturnAction = openTripReturnAction;
window.closeTripReturnActionForm = closeTripReturnActionForm;
window.hydrateTripReturnRoutePreview = hydrateTripReturnRoutePreview;
window.submitTripReturnActionForm = submitTripReturnActionForm;
window.switchDeliveryWorkbenchView = switchDeliveryWorkbenchView;
window.switchDeliveryRunningView = switchDeliveryRunningView;
window.switchDeliveryShipmentFlowTab = switchDeliveryWorkbenchView;
window.openTripReturnGuidanceModal = openTripReturnGuidanceModal;
window.closeTripReturnGuidanceModal = closeTripReturnGuidanceModal;

function renderTmsCockpit() {
  if (!window.TmsCockpit || typeof document === 'undefined') return;
  const state = appState || {};
  const checklistEl = document.getElementById('tms-master-setup-checklist');
  const towerEl = document.getElementById('tms-control-tower');
  const workQueueEl = document.getElementById('transport-control-workqueue');
  const timelineEl = document.getElementById('tms-order-timeline');
  const timelineSelectorEl = document.getElementById('tms-order-timeline-selector');
  const timelineDetailEl = document.getElementById('tms-order-timeline-detail');
  const financeEl = document.getElementById('tms-finance-worklist');

  if (checklistEl) {
    const items = window.TmsCockpit.buildMasterSetupChecklist(state);
    checklistEl.innerHTML = items.map(item => `
      <div onclick="switchView('master-data')" title="${item.message}" style="display:flex; align-items:center; justify-content:space-between; gap:10px; padding:9px 10px; border-radius:10px; background:${item.status === 'done' ? '#ecfdf5' : '#fff7ed'}; border:1px solid ${item.status === 'done' ? '#bbf7d0' : '#fed7aa'}; cursor:pointer;">
        <span style="font-weight:700; color:#0f172a;"><i class="fa-solid ${item.icon}" style="color:${item.status === 'done' ? '#059669' : '#f97316'}; margin-right:7px;"></i>${item.label}</span>
        <span style="font-size:.74rem; font-weight:800; color:${item.status === 'done' ? '#047857' : '#c2410c'};">${item.status === 'done' ? 'Đã cấu hình' : 'Cần cấu hình'}</span>
      </div>
    `).join('');
  }

  if (towerEl) {
    const tower = window.TmsCockpit.buildControlTower(state);
    towerEl.innerHTML = Object.values(tower).map(card => `
      <div onclick="switchView('${card.target === 'accounting' ? 'accounting' : card.target === 'tracking' ? 'tracking' : card.target === 'dispatch' ? 'dispatch' : 'master-data'}')" style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:13px; cursor:pointer;">
        <div style="font-size:.76rem; color:#64748b; font-weight:700; min-height:30px;">${card.label}</div>
        <div style="font-size:1.65rem; color:#2563eb; font-weight:900; margin-top:4px;">${card.count}</div>
      </div>
    `).join('');
  }
  renderTransportationWorkQueue(workQueueEl);


  if (timelineEl) {
    const deliveryOrders = state.delivery_orders || [];
    const activeDo = deliveryOrders.find(d => String(d.id) === String(tmsActiveTimelineDoId))
      || deliveryOrders.find(d => ['In Transit', 'Approved', 'Planned', 'Delivered'].includes(d.status))
      || deliveryOrders[0];
    if (activeDo && !tmsActiveTimelineDoId) tmsActiveTimelineDoId = activeDo.id;
    if (activeDo && !tmsActiveShipment360Id) tmsActiveShipment360Id = activeDo.id;
    if (timelineSelectorEl) {
      timelineSelectorEl.innerHTML = [
        '<option value="">Chọn đơn giao hàng</option>',
        ...deliveryOrders.map(order => `<option value="${order.id}" ${activeDo && String(order.id) === String(activeDo.id) ? 'selected' : ''}>${order.id} • ${statusLabel(order.status || order.canonical_status || '')}</option>`)
      ].join('');
    }
    const steps = window.TmsCockpit.buildOrderTimeline(state, activeDo && activeDo.id);
    timelineEl.innerHTML = `
      <div style="font-size:.78rem; color:#64748b; margin-bottom:10px;">${activeDo ? `Đang xem: <strong style="color:#0f172a;">${activeDo.id}</strong>` : 'Chưa có DO để hiển thị timeline.'}</div>
      <div style="display:grid; gap:7px;">
        ${steps.map((step, index) => `
          <div onclick="openTimelineStepContext('${activeDo?.id || ''}', '${step.key}')" title="${step.message}" style="display:flex; align-items:center; gap:9px; cursor:pointer; padding:8px 9px; border-radius:10px; background:${step.status === 'done' ? '#f0fdf4' : step.status === 'blocked' ? '#fff1f2' : '#f8fafc'}; border:1px solid ${step.status === 'done' ? '#bbf7d0' : step.status === 'blocked' ? '#fecaca' : '#e2e8f0'};">
            <span style="width:24px; height:24px; border-radius:999px; display:inline-flex; align-items:center; justify-content:center; font-size:.72rem; font-weight:900; color:white; background:${step.status === 'done' ? '#059669' : step.status === 'blocked' ? '#dc2626' : '#cbd5e1'};">${index + 1}</span>
            <span style="font-weight:800; color:${step.status === 'done' ? '#0f172a' : step.status === 'blocked' ? '#991b1b' : '#64748b'};">${step.label}</span>
            <span style="font-size:.68rem; font-weight:900; color:${step.health === 'critical' ? '#dc2626' : step.health === 'warning' ? '#d97706' : '#059669'}; margin-left:auto;">${step.status === 'done' ? 'Xong' : step.status === 'blocked' ? 'Thiếu dữ liệu' : 'Chờ xử lý'}</span>
            <i class="fa-solid fa-chevron-right" style="margin-left:auto; color:#94a3b8; font-size:.7rem;"></i>
          </div>
        `).join('')}
      </div>
    `;
    if (timelineDetailEl && activeDo) {
      renderOrderTimelineDetail(activeDo.id, steps.find(step => step.status === 'pending')?.key || steps[0]?.key || 'delivery_order');
    }
  }

  renderShipment360Detail();

  if (financeEl) {
    const finance = window.TmsCockpit.buildFinanceWorklist(state);
    financeEl.innerHTML = [
      ['Actual Cost chờ xử lý', finance.actual_cost_pending],
      ['AP chờ hạch toán', finance.ap_waiting_post],
      ['Settlement còn mở', finance.settlement_open]
    ].map(([label, count]) => `
      <div style="display:flex; justify-content:space-between; gap:10px; align-items:center; padding:10px 11px; border-radius:10px; background:#f8fafc; border:1px solid #e2e8f0;">
        <span style="color:#475569; font-weight:700;">${label}</span>
        <span style="font-weight:900; color:${count ? '#dc2626' : '#059669'};">${count}</span>
      </div>
    `).join('');
  }
}
function uiHealthEscape(value) {
  return escapeHtml(value);
}
function openUiHealthTarget(target) {
  const view = target && target.view || 'overview';
  const tabId = target && target.tabId || '';
  const targetId = tabId || (target && target.target) || '';
  switchView(view, targetId);
  setTimeout(() => {
    if (tabId && typeof switchMasterDataTab === 'function') {
      const tabButton = document.querySelector(`.md-tab-btn[onclick*="${tabId}"]`);
      switchMasterDataTab(tabId, tabButton || null);
    }
    const scrollId = (target && target.target) || tabId || '';
    const scrollTarget = scrollId ? document.getElementById(scrollId) : null;
    if (scrollTarget) scrollTarget.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, 140);
}

window.openUiHealthActionByKey = function (key) {
  if (!window.TmsCockpit?.buildUiHealthChecklist) return;
  const health = window.TmsCockpit.buildUiHealthChecklist(appState || {}, new Date());
  const item = (health.items || []).find(candidate => String(candidate.key) === String(key));
  if (!item || !item.target) return;
  openUiHealthTarget(item.target);
  if (typeof showToast === 'function') showToast(item.message || 'Đã mở màn hình liên quan.');
};

window.openCockpitNavigation = function (view, targetId) {
  switchView(view || 'overview', targetId || '');
  if (!targetId) return;
  setTimeout(() => {
    if (targetId.startsWith('md-tab-') && typeof switchMasterDataTab === 'function') {
      const tabButton = document.querySelector(`.md-tab-btn[onclick*="${targetId}"]`);
      switchMasterDataTab(targetId, tabButton || null);
    }
    const target = document.getElementById(targetId);
    if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, 120);
};

function renderTransportationWorkQueue(container) {
  if (!container || !window.TmsCockpit?.buildTransportationWorkQueue) return;
  const queue = window.TmsCockpit.buildTransportationWorkQueue(appState || {}, new Date());
  const color = item => item.severity === 'critical' ? '#dc2626' : item.severity === 'warning' ? '#d97706' : '#2563eb';
  container.innerHTML = `
    <div style="border:1px solid #dbeafe; background:#ffffff; border-radius:14px; padding:13px;">
      <div style="display:flex; justify-content:space-between; gap:12px; align-items:flex-start; margin-bottom:10px;">
        <div>
          <div style="font-weight:950; color:#0f172a;"><i class="fa-solid fa-tower-broadcast" style="color:#2563eb;"></i> Transportation Work Queue</div>
          <div style="font-size:.78rem; color:#64748b; margin-top:3px;">Danh sách việc vận chuyển cần xử lý theo mức ưu tiên, giống control tower vận hành.</div>
        </div>
      </div>
      <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(135px,1fr)); gap:8px; margin-bottom:10px;">
        ${queue.kpis.map(kpi => `
          <div style="border:1px solid #e2e8f0; border-radius:11px; padding:8px 9px; background:#f8fafc;">
            <div style="font-size:.7rem; color:#64748b; font-weight:900;">${kpi.label}</div>
            <div style="font-size:1.15rem; color:#2563eb; font-weight:950;">${kpi.count}</div>
          </div>
        `).join('')}
      </div>
      <div style="display:grid; gap:8px;">
        ${queue.items.length ? queue.items.map(item => `
          <div onclick="openCockpitNavigation('${item.navigation.view}', '${item.navigation.target || ''}')" style="display:grid; grid-template-columns:1fr auto; gap:10px; align-items:center; border:1px solid ${item.severity === 'critical' ? '#fecaca' : item.severity === 'warning' ? '#fed7aa' : '#bfdbfe'}; background:${item.severity === 'critical' ? '#fff1f2' : item.severity === 'warning' ? '#fff7ed' : '#eff6ff'}; border-radius:12px; padding:10px; cursor:pointer;">
            <div>
              <div style="font-weight:950; color:#0f172a;"><i class="fa-solid fa-circle-dot" style="color:${color(item)};"></i> ${escapeHtml(item.title)}</div>
              <div style="font-size:.76rem; color:#475569; margin-top:3px;">${item.message}</div>
              <div style="font-size:.7rem; color:#64748b; margin-top:4px; font-weight:900;">Chủ trách nhiệm: ${item.owner}</div>
            </div>
            <button class="fiori-btn" style="padding:8px 10px; white-space:nowrap;" onclick="event.stopPropagation(); openCockpitNavigation('${item.navigation.view}', '${item.navigation.target || ''}')">${item.action_label}</button>
          </div>
        `).join('') : `<div style="color:#047857; background:#ecfdf5; border:1px solid #bbf7d0; border-radius:12px; padding:11px; font-weight:850;">${queue.empty_message}</div>`}
      </div>
    </div>
  `;
}

function renderOrderTimelineDeepActions(detail) {
  const actions = Array.isArray(detail && detail.deep_actions) ? detail.deep_actions : [];
  return actions.map(action => {
    const color = action.severity === 'warning' ? '#d97706' : action.severity === 'critical' ? '#dc2626' : '#2563eb';
    const icon = action.code === 'OPEN_GPS_POD'
      ? 'fa-location-dot'
      : action.code === 'OPEN_DISPATCH'
        ? 'fa-truck-ramp-box'
        : action.code === 'OPEN_FINANCE_COCKPIT'
          ? 'fa-file-invoice-dollar'
          : action.code === 'OPEN_DELIVERY_ORDER'
            ? 'fa-boxes-packing'
            : 'fa-arrow-up-right-from-square';
    const view = action.navigation && action.navigation.view || 'overview';
    return `
      <button class="fiori-btn" onclick="executeShipment360StepAction('${detail.key || 'delivery_order'}', '${action.code || 'OPEN_TIMELINE_CONTEXT'}')" style="justify-content:flex-start; align-items:flex-start; gap:8px; text-align:left; background:#ffffff; border-color:${color};">
        <i class="fa-solid ${icon}" style="color:${color}; margin-top:2px;"></i>
        <span>
          <strong style="display:block; color:${color};">${action.label}</strong>
          <small style="display:block; color:#64748b; font-weight:700; line-height:1.35;">${action.description}</small>
        </span>
      </button>
    `;
  }).join('');
}

function renderShipment360Detail() {
  if (!window.TmsCockpit?.buildShipment360Detail || typeof document === 'undefined') return;
  const selector = document.getElementById('shipment-360-selector');
  const summaryEl = document.getElementById('shipment-360-summary');
  const alertsEl = document.getElementById('shipment-360-alerts');
  const timelineEl = document.getElementById('shipment-360-timeline');
  const eventsEl = document.getElementById('shipment-360-events');
  const documentsEl = document.getElementById('shipment-360-documents');
  const financeEl = document.getElementById('shipment-360-finance');
  const actionsEl = document.getElementById('shipment-360-actions');
  const readinessEl = document.getElementById('shipment-360-settlement-readiness');
  if (!summaryEl || !alertsEl || !timelineEl || !eventsEl || !documentsEl || !financeEl || !actionsEl) return;

  const deliveryOrders = (typeof eplDeliveryOrders !== 'undefined' && eplDeliveryOrders.length)
    ? eplDeliveryOrders
    : (appState.delivery_orders || []);
  const activeId = tmsActiveShipment360Id || tmsActiveTimelineDoId || deliveryOrders[0]?.id || '';
  if (activeId && !tmsActiveShipment360Id) tmsActiveShipment360Id = activeId;
  if (selector) {
    selector.innerHTML = [
      '<option value="">Chọn DO/FO</option>',
      ...deliveryOrders.map(order => `<option value="${order.id}" ${String(order.id) === String(activeId) ? 'selected' : ''}>${order.id} • ${statusLabel(order.status || order.canonical_status || '')}</option>`)
    ].join('');
  }
  const searchInput = document.getElementById('shipment-dossier-search');
  const searchOptions = document.getElementById('shipment-dossier-options');
  if (searchInput && document.activeElement !== searchInput) searchInput.value = activeId;
  if (searchOptions) {
    searchOptions.innerHTML = deliveryOrders.map(order =>
      `<option value="${order.id}">${statusLabel(order.status || order.canonical_status || '')}</option>`
    ).join('');
  }

  const shipment = window.TmsCockpit.buildShipment360Detail(shipmentStateFor(activeId), activeId, new Date());
  const summaryCards = [
    ['Mã đơn/chuyến', shipment.id || 'Chưa chọn'],
    ['Trạng thái', shipment.summary.status_label],
    ['Khách hàng', shipment.summary.customer_id],
    ['Tuyến', shipment.summary.route_label],
    ['Xe', shipment.summary.vehicle_label],
    ['Tài xế', shipment.summary.driver_label],
    ['ETA đến', shipment.summary.eta_label],
    ['ETA quay đầu/về', shipment.summary.return_eta_label],
    ['Khoảng cách', shipment.summary.distance_label]
  ];
  summaryEl.innerHTML = summaryCards.map(([label, value]) => `
    <div style="background:#ffffff; border:1px solid #dbeafe; border-radius:12px; padding:10px;">
      <div style="font-size:.72rem; color:#64748b; font-weight:900;">${label}</div>
      <div style="font-size:.92rem; color:#0f172a; font-weight:950; margin-top:4px;">${value || '—'}</div>
    </div>
  `).join('');

  alertsEl.innerHTML = shipment.alerts.length ? shipment.alerts.map(alert => `
    <div style="border:1px solid ${alert.severity === 'critical' ? '#fecaca' : '#fed7aa'}; background:${alert.severity === 'critical' ? '#fff1f2' : '#fff7ed'}; color:#7f1d1d; border-radius:11px; padding:9px 10px; font-size:.8rem; font-weight:850;">
      <i class="fa-solid ${alert.severity === 'critical' ? 'fa-triangle-exclamation' : 'fa-circle-info'}"></i> ${alert.message}
    </div>
  `).join('') : '<div style="background:#ecfdf5; border:1px solid #bbf7d0; color:#047857; border-radius:11px; padding:9px 10px; font-weight:850;">Hồ sơ chuyến chưa có cảnh báo nổi bật.</div>';

  timelineEl.innerHTML = `
    <div style="font-weight:950; color:#0f172a;"><i class="fa-solid fa-timeline" style="color:#2563eb;"></i> Timeline A-Z</div>
    ${shipment.timeline.map((step, index) => `
      <div onclick="openTimelineStepContext('${shipment.id}', '${step.key}')" style="display:flex; align-items:center; gap:8px; border:1px solid ${step.status === 'done' ? '#bbf7d0' : step.status === 'blocked' ? '#fecaca' : '#e2e8f0'}; background:${step.status === 'done' ? '#f0fdf4' : step.status === 'blocked' ? '#fff1f2' : '#ffffff'}; border-radius:10px; padding:8px; cursor:pointer;">
        <span style="width:22px; height:22px; border-radius:999px; display:inline-flex; align-items:center; justify-content:center; background:${step.status === 'done' ? '#059669' : '#cbd5e1'}; color:white; font-size:.7rem; font-weight:950;">${index + 1}</span>
        <span style="font-weight:850; color:#0f172a;">${step.label}</span>
      </div>
    `).join('')}
  `;

  eventsEl.innerHTML = `
    <div style="font-weight:950; color:#0f172a;"><i class="fa-solid fa-location-dot" style="color:#dc2626;"></i> GPS/Event mới nhất</div>
    ${shipment.latest_event && shipment.latest_event.label ? `
      <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:11px; padding:10px;">
        <div style="font-weight:950; color:#0f172a;">${shipment.latest_event.label}</div>
        <div style="font-size:.76rem; color:#64748b; margin-top:4px;">${shipment.latest_event.time_label || 'Chưa có thời gian'} • ${shipment.latest_event.source_label || 'Không rõ nguồn'}</div>
        <div style="font-size:.78rem; color:#475569; margin-top:5px;">${shipment.latest_event.location_text || 'Chưa có vị trí'}</div>
        <button class="fiori-btn fiori-btn-secondary" onclick="openShipment360Action('OPEN_GPS_POD', '${shipment.id || ''}')" style="margin-top:8px; padding:5px 9px; font-size:.72rem;"><i class="fa-solid fa-location-crosshairs"></i> Mở GPS/POD</button>
      </div>
    ` : '<div style="background:#fff7ed; border:1px solid #fed7aa; border-radius:11px; padding:10px; color:#92400e;">Chưa có event GPS/POD.</div>'}
    ${(shipment.events || []).slice(-3).reverse().map(event => `<div style="font-size:.76rem; color:#475569; background:#ffffff; border:1px solid #f1f5f9; border-radius:9px; padding:7px;">${event.label} • ${event.time_label}</div>`).join('')}
  `;

  documentsEl.innerHTML = `
    <div style="font-weight:950; color:#0f172a;"><i class="fa-solid fa-file-signature" style="color:#059669;"></i> POD/Chứng từ</div>
    <div style="border:1px solid ${shipment.pod.status === 'done' ? '#bbf7d0' : '#fed7aa'}; background:${shipment.pod.status === 'done' ? '#f0fdf4' : '#fff7ed'}; border-radius:11px; padding:10px; color:#0f172a; font-weight:850;">${shipment.pod.label}</div>
    ${(shipment.pod.records || []).map(record => `
      <div style="background:#ffffff; border:1px solid #dcfce7; border-radius:10px; padding:8px; font-size:.76rem;">
        <div style="font-weight:950; color:#0f172a;">POD điểm ${record.stop_no || 1} • Xe ${record.vehicle_id || '—'}</div>
        <div style="color:#475569; margin-top:3px;">Tài xế ${record.driver_id || '—'} • Người nhận ${record.receiver_name || record.receiver || '—'}</div>
        <div style="color:#64748b; margin-top:3px;">${record.delivery_time || 'Chưa có giờ giao'} ${record.location_text ? `• ${record.location_text}` : ''}</div>
      </div>
    `).join('')}
    <button class="fiori-btn ${shipment.pod.status === 'done' ? 'fiori-btn-secondary' : 'fiori-btn-primary'}" onclick="openShipment360Action('OPEN_GPS_POD', '${shipment.id || ''}')" style="padding:7px 10px; font-size:.76rem; justify-content:center;">
      <i class="fa-solid ${shipment.pod.status === 'done' ? 'fa-eye' : 'fa-upload'}"></i> ${shipment.pod.status === 'done' ? 'Xem POD' : 'Bổ sung POD'}
    </button>
  `;

  const money = (amount, currency = 'VND') => `${Number(amount || 0).toLocaleString('vi-VN')} ${currency}`;
  financeEl.innerHTML = `
    <div style="font-weight:950; color:#0f172a;"><i class="fa-solid fa-file-invoice-dollar" style="color:#2563eb;"></i> Cost/AP/Settlement</div>
    ${shipment.finance.items.length ? shipment.finance.items.map(item => `
      <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:9px;">
        <div style="font-weight:900; color:#0f172a;">${item.type} ${item.id ? `• ${item.id}` : ''}</div>
        <div style="font-size:.76rem; color:#64748b;">${item.status_label} • ${money(item.amount, item.currency_code)}</div>
        <button class="fiori-btn fiori-btn-secondary" onclick="openFinanceDeepForm('${item.type === 'AP Invoice' ? 'ap_invoice' : item.type === 'Settlement' ? 'settlement' : 'actual_cost'}', '${item.id || ''}')" style="margin-top:8px; padding:5px 9px; font-size:.72rem;"><i class="fa-solid fa-up-right-from-square"></i> Mở hồ sơ tài chính</button>
      </div>
    `).join('') : '<div style="background:#fff7ed; border:1px solid #fed7aa; border-radius:11px; padding:10px; color:#92400e;">Chưa có Actual Cost/AP liên quan.</div>'}
  `;

  const nextAction = shipment.actions.find(action => action.severity !== 'info') || shipment.actions[0];
  actionsEl.innerHTML = `
    <div style="font-weight:950; color:#0f172a;"><i class="fa-solid fa-bolt" style="color:#f97316;"></i> Hành động tiếp theo</div>
    ${nextAction ? `
      <button class="fiori-btn ${nextAction.severity === 'info' ? 'fiori-btn-secondary' : ''}" onclick="openShipment360Action('${nextAction.code}', '${shipment.id || ''}')" title="${nextAction.description}" style="justify-content:flex-start; padding:9px 10px;">
        <i class="fa-solid fa-arrow-right"></i> ${nextAction.label}
      </button>
    ` : ''}
  `;
  renderShipmentSettlementReadiness(shipment.id, readinessEl);
  switchShipmentDossierTab(activeShipmentDossierTab);
}

function renderShipmentSettlementReadiness(deliveryOrderId, container) {
  const target = container || document.getElementById('shipment-360-settlement-readiness');
  if (!target || !window.TmsCockpit?.buildShipmentSettlementReadiness) return;
  const targetId = deliveryOrderId || tmsActiveShipment360Id || tmsActiveTimelineDoId;
  const readiness = window.TmsCockpit.buildShipmentSettlementReadiness(shipmentStateFor(targetId), targetId, new Date());
  const color = readiness.status === 'ready' ? '#059669' : readiness.status === 'warning' ? '#d97706' : '#dc2626';
  target.innerHTML = `
    <div style="border:1px solid ${readiness.status === 'ready' ? '#bbf7d0' : readiness.status === 'warning' ? '#fed7aa' : '#fecaca'}; background:${readiness.status === 'ready' ? '#f0fdf4' : readiness.status === 'warning' ? '#fff7ed' : '#fff1f2'}; border-radius:14px; padding:12px;">
      <div style="display:flex; justify-content:space-between; gap:12px; align-items:flex-start; margin-bottom:10px;">
        <div>
          <div style="font-weight:950; color:#0f172a;"><i class="fa-solid fa-flag-checkered" style="color:${color};"></i> Điều kiện chốt chuyến / Settlement Readiness</div>
          <div style="font-size:.8rem; color:#475569; margin-top:3px;">${readiness.status_label}</div>
        </div>
        <span style="font-size:.72rem; font-weight:950; color:${color}; background:#ffffff; border:1px solid ${color}; border-radius:999px; padding:5px 9px;">${readiness.status.toUpperCase()}</span>
      </div>
      <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(135px,1fr)); gap:8px; margin-bottom:10px;">
        ${readiness.summary.map(item => `
          <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:8px;">
            <div style="font-size:.7rem; color:#64748b; font-weight:900;">${item.label}</div>
            <div style="font-size:.82rem; color:#0f172a; font-weight:950; margin-top:3px;">${item.value}</div>
          </div>
        `).join('')}
      </div>
      <div style="display:grid; gap:7px; margin-bottom:10px;">
        ${readiness.checks.map(check => `
          <div style="display:grid; grid-template-columns:150px 1fr; gap:8px; align-items:center; background:#ffffff; border:1px solid ${check.status === 'done' ? '#bbf7d0' : check.status === 'not_applicable' ? '#bfdbfe' : check.status === 'warning' ? '#fed7aa' : '#fecaca'}; border-radius:10px; padding:8px;">
            <strong style="font-size:.78rem; color:${check.status === 'done' ? '#047857' : check.status === 'not_applicable' ? '#075fb3' : check.status === 'warning' ? '#9a3412' : '#b91c1c'};"><i class="fa-solid ${check.status === 'done' ? 'fa-check' : check.status === 'not_applicable' ? 'fa-minus' : 'fa-circle-exclamation'}"></i> ${check.label}</strong>
            <span style="font-size:.76rem; color:#475569;">${check.message}</span>
          </div>
        `).join('')}
      </div>
      <div style="display:flex; flex-wrap:wrap; gap:8px;">
        ${readiness.actions.map(action => `
          <button class="fiori-btn ${action.code === 'OPEN_TIMELINE' ? 'fiori-btn-secondary' : ''}" onclick="openShipment360Action('${action.code}', '${readiness.id || ''}')" style="padding:7px 10px; font-weight:900;">
            <i class="fa-solid fa-arrow-up-right-from-square"></i> ${action.label}
          </button>
        `).join('')}
      </div>
    </div>
  `;
}

function renderOrderTimelineDetail(deliveryOrderId, stepKey) {
  if (!window.TmsCockpit || typeof document === 'undefined') return;
  const detailEl = document.getElementById('tms-order-timeline-detail');
  if (!detailEl) return;
  const detail = window.TmsCockpit.buildOrderTimelineDetail(shipmentStateFor(deliveryOrderId), deliveryOrderId, stepKey || 'delivery_order');
  const fieldRows = Object.entries(detail.primary || {})
    .filter(([, value]) => value !== null && value !== undefined && typeof value !== 'object')
    .slice(0, 6)
    .map(([key, value]) => `<div style="display:flex; justify-content:space-between; gap:10px; border-bottom:1px dashed #e2e8f0; padding:5px 0;"><span style="color:#64748b;">${key}</span><strong style="color:#0f172a;">${String(value)}</strong></div>`)
    .join('');
  detailEl.innerHTML = `
    <div style="margin-top:12px; border:1px solid ${detail.status === 'done' ? '#bbf7d0' : '#fed7aa'}; background:${detail.status === 'done' ? '#f0fdf4' : '#fff7ed'}; border-radius:12px; padding:12px;">
      <div style="display:flex; justify-content:space-between; gap:10px; align-items:center; margin-bottom:8px;">
        <strong style="color:#0f172a;"><i class="fa-solid ${detail.status === 'done' ? 'fa-circle-check' : 'fa-circle-info'}" style="color:${detail.status === 'done' ? '#059669' : '#f97316'};"></i> ${detail.title}</strong>
        <button class="fiori-btn fiori-btn-secondary" onclick="switchView('${detail.navigation.view}')" style="padding:5px 10px; font-size:.75rem;">Mở màn liên quan</button>
      </div>
      <div style="font-size:.8rem; color:#475569; margin-bottom:8px;">${detail.message}</div>
      <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:8px; margin-bottom:9px;">
        ${renderOrderTimelineDeepActions(detail)}
      </div>
      <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:9px; font-size:.76rem;">
        ${fieldRows || '<div style="color:#64748b;">Chưa có dữ liệu chi tiết cho bước này.</div>'}
      </div>
      <div style="display:flex; flex-wrap:wrap; gap:6px; margin-top:9px;">
        ${(detail.checklist || []).map(item => `
          <span style="display:inline-flex; align-items:center; gap:5px; border-radius:999px; padding:5px 8px; background:${item.status === 'done' ? '#ecfdf5' : '#fff7ed'}; border:1px solid ${item.status === 'done' ? '#bbf7d0' : '#fed7aa'}; color:${item.status === 'done' ? '#047857' : '#9a3412'}; font-size:.7rem; font-weight:900;">
            <i class="fa-solid ${item.status === 'done' ? 'fa-check' : 'fa-circle-exclamation'}"></i> ${item.label}
          </span>
        `).join('')}
      </div>
      <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-top:9px; font-size:.74rem;">
        <div style="background:#ffffff; border-radius:9px; padding:8px; text-align:center;"><strong>${detail.related.events.length}</strong><br><span style="color:#64748b;">Event</span></div>
        <div style="background:#ffffff; border-radius:9px; padding:8px; text-align:center;"><strong>${detail.related.pod ? 'Có' : 'Chưa'}</strong><br><span style="color:#64748b;">POD</span></div>
        <div style="background:#ffffff; border-radius:9px; padding:8px; text-align:center;"><strong>${detail.related.finance.length}</strong><br><span style="color:#64748b;">Finance</span></div>
      </div>
    </div>
  `;
}

window.openOrderTimelineStep = function (deliveryOrderId, stepKey) {
  renderOrderTimelineDetail(deliveryOrderId, stepKey);
};

function openTimelineBusinessForm(detail) {
  const navigation = detail && detail.navigation || {};
  const view = navigation.view || 'overview';
  const entityId = navigation.entity_id || '';
  const scrollTarget = detail.navigation.scroll_to || navigation.scroll_to || '';
  switchView(view, scrollTarget);

  setTimeout(() => {
    if (!entityId) return;
    if (detail.key === 'quotation' && typeof editOracleQT === 'function') {
      editOracleQT(entityId);
    } else if (detail.key === 'delivery_order' && typeof editFioriDO === 'function') {
      editFioriDO(entityId);
    }
  }, 80);
}

function closeShipment360StepModal() {
  const modal = document.getElementById('shipment-360-step-modal');
  if (modal) modal.style.display = 'none';
}

function shipment360FieldRows(primary) {
  return Object.entries(primary || {})
    .filter(([, value]) => value !== null && value !== undefined && typeof value !== 'object')
    .slice(0, 8)
    .map(([key, value]) => `
      <div style="display:flex; justify-content:space-between; gap:10px; border-bottom:1px dashed #e2e8f0; padding:6px 0;">
        <span style="color:#64748b; font-size:.76rem; font-weight:800;">${key}</span>
        <strong style="color:#0f172a; font-size:.78rem; text-align:right;">${String(value)}</strong>
      </div>
    `).join('');
}

function renderShipment360StepModal(detail) {
  const modal = document.getElementById('shipment-360-step-modal');
  if (!modal || !detail) return;
  const titleEl = document.getElementById('shipment-360-step-title');
  const subtitleEl = document.getElementById('shipment-360-step-subtitle');
  const statusEl = document.getElementById('shipment-360-step-status');
  const fieldsEl = document.getElementById('shipment-360-step-fields');
  const checklistEl = document.getElementById('shipment-360-step-checklist');
  const relatedEl = document.getElementById('shipment-360-step-related');
  const actionsEl = document.getElementById('shipment-360-step-actions');
  const statusColor = detail.status === 'done' ? '#059669' : detail.health === 'critical' ? '#dc2626' : '#d97706';
  const related = detail.related || {};
  const relatedCards = [
    ['Báo giá', related.quotation && related.quotation.id],
    ['DO', related.delivery_order && related.delivery_order.id],
    ['POD', related.pod ? 'Có POD' : 'Chưa POD'],
    ['Event', Array.isArray(related.events) ? related.events.length : 0],
    ['Finance', Array.isArray(related.finance) ? related.finance.length : 0]
  ];
  if (titleEl) titleEl.textContent = detail.title || 'Shipment 360°';
  if (subtitleEl) subtitleEl.textContent = `DO/FO: ${activeShipment360StepContext.deliveryOrderId || 'chưa chọn'} • Bước: ${detail.key || '—'}`;
  if (statusEl) {
    statusEl.innerHTML = `
      <div style="display:flex; justify-content:space-between; gap:12px; align-items:flex-start;">
        <div>
          <div style="font-size:.78rem; color:#64748b; font-weight:900;">Trạng thái bước</div>
          <div style="font-size:1rem; color:${statusColor}; font-weight:950; margin-top:3px;">${detail.status === 'done' ? 'Đã có dữ liệu' : 'Chưa hoàn tất / cần bổ sung'}</div>
        </div>
        <button class="fiori-btn" onclick="executeShipment360StepAction('${detail.key || 'delivery_order'}', 'OPEN_TIMELINE_CONTEXT')" style="background:#2563eb; color:#ffffff; border-color:#2563eb; padding:7px 11px; white-space:nowrap;">
          <i class="fa-solid fa-up-right-from-square"></i> Mở đúng form
        </button>
      </div>
      <div style="font-size:.82rem; color:#475569; margin-top:8px;">${detail.message || 'Kiểm tra dữ liệu bước này trước khi đi tiếp.'}</div>
    `;
  }
  if (fieldsEl) fieldsEl.innerHTML = shipment360FieldRows(detail.primary) || '<div style="color:#64748b; font-size:.8rem;">Chưa có dữ liệu chính cho bước này. Hãy dùng nút hành động để cấu hình/bổ sung.</div>';
  if (checklistEl) {
    checklistEl.innerHTML = (detail.checklist || []).map(item => `
      <span style="display:inline-flex; align-items:center; gap:5px; border-radius:999px; padding:6px 9px; background:${item.status === 'done' ? '#ecfdf5' : '#fff7ed'}; border:1px solid ${item.status === 'done' ? '#bbf7d0' : '#fed7aa'}; color:${item.status === 'done' ? '#047857' : '#9a3412'}; font-size:.72rem; font-weight:900;">
        <i class="fa-solid ${item.status === 'done' ? 'fa-check' : 'fa-circle-exclamation'}"></i> ${item.label}
      </span>
    `).join('');
  }
  if (relatedEl) {
    relatedEl.innerHTML = relatedCards.map(([label, value]) => `
      <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:9px;">
        <div style="font-size:.7rem; color:#64748b; font-weight:900;">${label}</div>
        <div style="font-size:.9rem; color:#0f172a; font-weight:950; margin-top:3px;">${value || '—'}</div>
      </div>
    `).join('');
  }
  if (actionsEl) actionsEl.innerHTML = renderOrderTimelineDeepActions(detail) || '<div style="color:#64748b;">Chưa có hành động gợi ý.</div>';
  modal.style.display = 'flex';
}

function openModalFromTimelineStep(deliveryOrderId, stepKey) {
  const detail = window.TmsCockpit?.buildOrderTimelineDetail
    ? window.TmsCockpit.buildOrderTimelineDetail(shipmentStateFor(deliveryOrderId), deliveryOrderId, stepKey || 'delivery_order')
    : null;
  if (!detail) return;
  activeShipment360StepContext = { deliveryOrderId: deliveryOrderId || '', stepKey: stepKey || 'delivery_order' };
  renderShipment360StepModal(detail);
}

function executeShipment360StepAction(stepKey, actionCode) {
  const deliveryOrderId = activeShipment360StepContext.deliveryOrderId || tmsActiveShipment360Id || tmsActiveTimelineDoId || '';
  const detail = window.TmsCockpit?.buildOrderTimelineDetail
    ? window.TmsCockpit.buildOrderTimelineDetail(shipmentStateFor(deliveryOrderId), deliveryOrderId, stepKey || activeShipment360StepContext.stepKey || 'delivery_order')
    : null;
  if (!detail) {
    showToast('Chưa có dữ liệu Shipment 360 để mở bước này.');
    return;
  }
  if (actionCode === 'OPEN_GPS_POD') {
    switchView('tracking');
  } else if (actionCode === 'OPEN_DISPATCH') {
    switchView('dispatch');
  } else if (actionCode === 'OPEN_FINANCE_COCKPIT') {
    switchView('accounting');
  } else if (actionCode === 'OPEN_DELIVERY_ORDER') {
    switchView('ops-planning', 'fiori-do-list');
  } else {
    openTimelineBusinessForm(detail);
  }
  closeShipment360StepModal();
  setTimeout(() => {
    if (detail.navigation.view === 'tracking' && typeof renderGpsEventTimeline === 'function') renderGpsEventTimeline();
    if (detail.navigation.view === 'dispatch' && typeof renderDispatchCalendar === 'function') renderDispatchCalendar();
    if (detail.navigation.view === 'accounting' && typeof renderFinanceCockpit === 'function') renderFinanceCockpit();
  }, 0);
}

window.openTimelineStepContext = function (deliveryOrderId, stepKey) {
  if (deliveryOrderId) {
    tmsActiveTimelineDoId = deliveryOrderId;
    tmsActiveShipment360Id = deliveryOrderId;
  }
  renderOrderTimelineDetail(deliveryOrderId, stepKey);
  openModalFromTimelineStep(deliveryOrderId, stepKey || 'delivery_order');
  const detail = window.TmsCockpit?.buildOrderTimelineDetail
    ? window.TmsCockpit.buildOrderTimelineDetail(shipmentStateFor(deliveryOrderId), deliveryOrderId, stepKey || 'delivery_order')
    : null;
  const view = detail?.navigation?.view || ({
    quotation: 'crm-sales',
    delivery_order: 'ops-planning',
    dispatch: 'dispatch',
    gps: 'tracking',
    pod: 'tracking',
    cost: 'accounting',
    ap: 'accounting',
    settlement: 'accounting'
  })[stepKey] || 'overview';
  setTimeout(() => {
    if (view === 'tracking') {
      const input = document.getElementById('tracking-do-search');
      if (input && deliveryOrderId) input.value = deliveryOrderId;
      if (typeof renderGpsEventTimeline === 'function') renderGpsEventTimeline();
    }
    if (view === 'dispatch' && deliveryOrderId) {
      selectedDispatchCalendarOrderId = deliveryOrderId;
      if (typeof renderDispatchCalendar === 'function') renderDispatchCalendar();
    }
    if (view === 'accounting') {
      renderFinanceCockpit();
    }
  }, 0);
};

window.closeShipment360StepModal = closeShipment360StepModal;
window.renderShipment360StepModal = renderShipment360StepModal;
window.openModalFromTimelineStep = openModalFromTimelineStep;
window.executeShipment360StepAction = executeShipment360StepAction;

function renderRolePermissionBoard() {
  if (!window.TmsCockpit || typeof document === 'undefined') return;
  const kpisEl = document.getElementById('role-permission-kpis');
  const rolesEl = document.getElementById('role-permission-roles');
  const usersEl = document.getElementById('role-permission-users');
  const matrixEl = document.getElementById('role-permission-matrix');
  const warningsEl = document.getElementById('role-permission-warnings');
  if (!kpisEl || !rolesEl || !usersEl) return;

  const board = window.TmsCockpit.buildRolePermissionBoard(appState || {});
  kpisEl.innerHTML = Object.values(board.kpis).map(kpi => `
    <div onclick="switchView('master-data')" style="background:#ffffff; border:1px solid ${kpi.count && kpi.label.includes('Cảnh báo') ? '#fecaca' : '#ddd6fe'}; border-radius:12px; padding:10px; cursor:pointer;">
      <div style="font-size:.72rem; color:#64748b; font-weight:800;">${kpi.label}</div>
      <div style="font-size:1.35rem; color:${kpi.count && kpi.label.includes('Cảnh báo') ? '#dc2626' : '#7c3aed'}; font-weight:950; margin-top:3px;">${kpi.count}</div>
    </div>
  `).join('');

  rolesEl.innerHTML = board.roles.length ? board.roles.slice(0, 8).map(role => `
    <div style="background:#ffffff; border:1px solid ${role.missing_permissions.length ? '#fed7aa' : '#bbf7d0'}; border-radius:12px; padding:10px;">
      <div style="display:flex; justify-content:space-between; gap:10px; align-items:center;">
        <strong style="color:#0f172a;">${role.id}</strong>
        <span style="font-size:.72rem; font-weight:900; color:${role.missing_permissions.length ? '#c2410c' : '#047857'};">${role.coverage_label}</span>
      </div>
      <div style="font-size:.75rem; color:#64748b; margin-top:5px;">${role.permission_count} quyền • ${role.permissions.slice(0, 4).join(', ') || 'Chưa cấu hình quyền'}</div>
    </div>
  `).join('') : `
    <div style="background:#fff7ed; border:1px solid #fed7aa; color:#9a3412; border-radius:12px; padding:12px; font-weight:800;">Chưa có role. Vào Master Data → Người dùng & Vai trò để cấu hình.</div>
  `;

  usersEl.innerHTML = board.users.length ? board.users.slice(0, 8).map(user => `
    <div style="background:#ffffff; border:1px solid ${user.status === 'configured' ? '#ddd6fe' : '#fecaca'}; border-radius:12px; padding:10px;">
      <div style="display:flex; justify-content:space-between; gap:10px; align-items:center;">
        <strong style="color:#0f172a;">${user.username}</strong>
        <span style="font-size:.72rem; font-weight:900; color:${user.status === 'configured' ? '#7c3aed' : '#dc2626'};">${user.role_label}</span>
      </div>
      <div style="font-size:.75rem; color:#64748b; margin-top:5px;">${user.permission_count} quyền hiệu lực</div>
    </div>
  `).join('') : `
    <div style="background:#fff7ed; border:1px solid #fed7aa; color:#9a3412; border-radius:12px; padding:12px; font-weight:800;">Chưa có user. Vào Master Data → Người dùng để cấu hình người demo.</div>
  `;

  if (matrixEl && board.permission_matrix) {
    const statusMeta = {
      complete: { label: 'Đủ', bg: '#ecfdf5', border: '#bbf7d0', color: '#047857' },
      partial: { label: 'Thiếu một phần', bg: '#fff7ed', border: '#fed7aa', color: '#c2410c' },
      missing: { label: 'Thiếu', bg: '#fff1f2', border: '#fecaca', color: '#b91c1c' }
    };
    matrixEl.innerHTML = `
      <div style="background:#ffffff; border:1px solid #e9d5ff; border-radius:12px; padding:10px;">
        <div style="font-weight:950; color:#0f172a; margin-bottom:8px;"><i class="fa-solid fa-table-cells-large" style="color:#7c3aed;"></i> Ma trận quyền theo module</div>
        <div style="display:grid; gap:7px;">
          ${board.permission_matrix.rows.map(row => `
            <div style="display:grid; grid-template-columns:minmax(110px,.8fr) repeat(${board.permission_matrix.modules.length}, minmax(95px,1fr)); gap:6px; align-items:stretch;">
              <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:9px; padding:7px; font-weight:950; color:#0f172a;">${row.role_id}</div>
              ${board.permission_matrix.modules.map(module => {
      const cell = row.modules[module.key];
      const meta = statusMeta[cell.status] || statusMeta.missing;
      return `<div title="Thiếu: ${cell.missing.join(', ') || 'không'}" style="background:${meta.bg}; border:1px solid ${meta.border}; color:${meta.color}; border-radius:9px; padding:7px; text-align:center; font-size:.72rem; font-weight:900;">
                  <div>${module.label}</div>
                  <div style="font-size:.68rem; margin-top:3px;">${meta.label} • ${cell.coverage_percent}%</div>
                </div>`;
    }).join('')}
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  if (warningsEl) {
    warningsEl.innerHTML = board.warnings.length ? board.warnings.slice(0, 6).map(warning => `
      <div onclick="switchView('master-data')" style="background:#fff7ed; border:1px solid #fed7aa; color:#9a3412; border-radius:10px; padding:8px 9px; font-size:.78rem; font-weight:850; cursor:pointer;">
        <i class="fa-solid fa-triangle-exclamation"></i> ${warning.message}
      </div>
    `).join('') : `
      <div style="background:#ecfdf5; border:1px solid #bbf7d0; color:#047857; border-radius:10px; padding:8px 9px; font-size:.78rem; font-weight:850;">
        <i class="fa-solid fa-circle-check"></i> Role/permission đã đủ cho demo vận hành.
      </div>
    `;
  }
  renderRoleAdminWorkbench();
}

function renderRoleAdminWorkbench() {
  if (!window.TmsCockpit || typeof document === 'undefined') return;
  const templatesEl = document.getElementById('role-admin-templates');
  const worklistEl = document.getElementById('role-admin-worklist');
  const guidanceEl = document.getElementById('role-admin-guidance');
  if (!templatesEl || !worklistEl || !guidanceEl || !window.TmsCockpit.buildRoleAdminWorkbench) return;

  const workbench = window.TmsCockpit.buildRoleAdminWorkbench(appState || {});
  templatesEl.innerHTML = workbench.role_templates.map(template => `
    <div onclick="switchView('master-data')" title="${template.permissions.join(', ')}" style="background:#faf5ff; border:1px solid #ddd6fe; border-radius:10px; padding:9px; cursor:pointer;">
      <div style="display:flex; justify-content:space-between; gap:8px; align-items:center;">
        <strong style="color:#0f172a;">${template.label}</strong>
        <span style="font-size:.68rem; color:#7c3aed; font-weight:950;">${template.permissions.length} quyền</span>
      </div>
      <div style="font-size:.74rem; color:#64748b; line-height:1.35; margin-top:4px;">${template.description}</div>
    </div>
  `).join('');

  worklistEl.innerHTML = workbench.worklist.length ? workbench.worklist.slice(0, 6).map(item => `
    <div onclick="switchView('${item.navigation.view}')" style="background:${item.severity === 'critical' ? '#fff1f2' : '#fff7ed'}; border:1px solid ${item.severity === 'critical' ? '#fecaca' : '#fed7aa'}; border-radius:10px; padding:9px; cursor:pointer;">
      <div style="display:flex; justify-content:space-between; gap:8px; align-items:center;">
        <strong style="color:#0f172a; font-size:.82rem;">${escapeHtml(item.title)}</strong>
        <span style="font-size:.68rem; font-weight:950; color:${item.severity === 'critical' ? '#dc2626' : '#c2410c'};">${item.action_label}</span>
      </div>
      <div style="font-size:.74rem; color:#64748b; line-height:1.35; margin-top:4px;">${escapeHtml(item.description)}</div>
    </div>
  `).join('') : `
    <div style="background:#ecfdf5; border:1px solid #bbf7d0; color:#047857; border-radius:10px; padding:9px; font-weight:850;">
      <i class="fa-solid fa-circle-check"></i> Quyền demo đã sạch, chưa có việc cần cấu hình thêm.
    </div>
  `;

  guidanceEl.innerHTML = [
    ...workbench.permission_actions.map(action => ({ icon: 'fa-bolt', text: `${action.label}: ${action.description}` })),
    ...workbench.guidance.map(text => ({ icon: 'fa-lightbulb', text }))
  ].map(item => `
    <div style="background:#f8fafc; border:1px dashed #cbd5e1; border-radius:9px; padding:8px; font-size:.75rem; color:#475569;">
      <i class="fa-solid ${item.icon}" style="color:#7c3aed;"></i> ${item.text}
    </div>
  `).join('');
}

/**
 * Dịch các nhãn do dữ liệu mang theo sang ngôn ngữ đang chọn.
 *
 * Các bản đồ dịch này vốn nằm trong app.js nên giữ nguyên tại đây; phần TRÌNH
 * BÀY đã chuyển sang js/sla-analytics.js để kiểm chứng được bằng Node. Nhờ
 * tách vậy, module trình bày chỉ nhận chuỗi đã dịch và không cần biết gì về
 * i18n của dữ liệu.
 */
function localizeReportingDrilldown(report, lang) {
  const pick = (map, value) => (map[value] && map[value][lang]) || value;

  const kpiLabelMap = {
    'Tổng đơn phân tích': { vi: 'Tổng đơn phân tích', en: 'Total Analyzed Orders', la: 'ຈຳນວນໃບສັ່ງທັງໝົດທີ່ວິເຄາະ' },
    'Tỉ lệ đúng hạn': { vi: 'Tỉ lệ đúng hạn', en: 'On-Time Delivery Rate', la: 'ອັດຕາຕົງເວລາ' },
    'Cảnh báo SLA/KPI': { vi: 'Cảnh báo SLA/KPI', en: 'SLA/KPI Alerts', la: 'ແຈ້ງເຕືອນ SLA/KPI' },
    'Cảnh báo nghiêm trọng': { vi: 'Cảnh báo nghiêm trọng', en: 'Critical Alerts', la: 'ແຈ້ງເຕືອນຮ້າຍແຮງ' },
    'Đơn vượt chi phí': { vi: 'Đơn vượt chi phí', en: 'Cost Overrun Orders', la: 'ໃບສັ່ງເກີນຕົ້ນທຶນ' }
  };

  const agingLabelMap = {
    'Dưới 30 phút': { vi: 'Dưới 30 phút', en: 'Under 30 mins', la: 'ຕ່ຳກວ່າ 30 ນາທີ' },
    '30–60 phút': { vi: '30–60 phút', en: '30–60 mins', la: '30–60 ນາທີ' },
    '60–120 phút': { vi: '60–120 phút', en: '60–120 mins', la: '60–120 ນາທີ' },
    'Trên 120 phút': { vi: 'Trên 120 phút', en: 'Over 120 mins', la: 'ເກີນ 120 ນາທີ' }
  };

  const playbookLabelMap = {
    'Xử lý trễ giao hàng': { vi: 'Xử lý trễ giao hàng', en: 'Handle Late Delivery', la: 'ແກ້ໄຂການສົ່ງສິນຄ້າຊັກຊ້າ' },
    'Bổ sung POD': { vi: 'Bổ sung POD', en: 'Complete POD', la: 'ເພີ່ມເຕີມ POD' },
    'Kiểm tra vượt chi phí': { vi: 'Kiểm tra vượt chi phí', en: 'Review Cost Overrun', la: 'ກວດສອບຕົ້ນທຶນເກີນ' }
  };

  const playbookInstrMap = {
    'Mở GPS/POD, gọi tài xế, cập nhật ETA và thông báo khách hàng nếu cần.': {
      vi: 'Mở GPS/POD, gọi tài xế, cập nhật ETA và thông báo khách hàng nếu cần.',
      en: 'Open GPS/POD, contact driver, update ETA, notify customer if needed.',
      la: 'ເປີດ GPS/POD, ໂທຫາຄົນຂັບ, ອັບເດດ ETA ແລະ ແຈ້ງລູກຄ້າຖ້າຈຳເປັນ.'
    },
    'Yêu cầu upload biên bản ký nhận trước khi chốt AP/Settlement.': {
      vi: 'Yêu cầu upload biên bản ký nhận trước khi chốt AP/Settlement.',
      en: 'Require signed POD upload before AP/Settlement closeout.',
      la: 'ຮຽກຮ້ອງໃຫ້ອັບໂຫຼດໃບຢັ້ງຢືນການຮັບສິນຄ້າກ່ອນປິດ AP/Settlement.'
    },
    'Mở Finance Cockpit để kiểm tra Actual Cost, nguyên nhân và quyền duyệt.': {
      vi: 'Mở Finance Cockpit để kiểm tra Actual Cost, nguyên nhân và quyền duyệt.',
      en: 'Open Finance Cockpit to verify Actual Cost, root cause, and approval rights.',
      la: 'ເປີດ Finance Cockpit ເພື່ອກວດສອບ Actual Cost, ສາເຫດ ແລະ ສິດອະນຸມັດ.'
    }
  };

  const dimMap = {
    'Khách hàng': { vi: 'Khách hàng', en: 'Customer', la: 'ລູກຄ້າ' },
    'Tuyến đường': { vi: 'Tuyến đường', en: 'Route', la: 'ເສັ້ນທາງ' },
    'Tài xế': { vi: 'Tài xế', en: 'Driver', la: 'ຄົນຂັບ' }
  };

  const issueLabelMap = {
    'Trễ lấy hàng': { vi: 'Trễ lấy hàng', en: 'Late Pickup', la: 'ຊັກຊ້າໃນການຮັບສິນຄ້າ' },
    'Trễ giao hàng': { vi: 'Trễ giao hàng', en: 'Late Delivery', la: 'ຊັກຊ້າໃນການສົ່ງສິນຄ້າ' },
    'Lệch ETA': { vi: 'Lệch ETA', en: 'ETA Variance', la: 'ຄາດເຄື່ອນ ETA' },
    'Thiếu POD': { vi: 'Thiếu POD', en: 'Missing POD', la: 'ຂາດ POD' },
    'Vượt chi phí': { vi: 'Vượt chi phí', en: 'Cost Overrun', la: 'ເກີນຕົ້ນທຶນ' },
    'Giao trễ thực tế': { vi: 'Giao trễ thực tế', en: 'Actual Late Delivery', la: 'ສົ່ງຊັກຊ້າຕົວຈິງ' }
  };

  const ownerMap = {
    'Điều phối': { vi: 'Điều phối', en: 'Dispatch', la: 'ການປ່ອຍລົດ' },
    'Vận hành': { vi: 'Vận hành', en: 'Operations', la: 'ການປະຕິບັດງານ' },
    'Kế toán': { vi: 'Kế toán', en: 'Accounting', la: 'ບັນຊີ' }
  };

  const actionMap = {
    'Mở điều phối': { vi: 'Mở điều phối', en: 'Open Dispatch', la: 'ເປີດໜ້າປ່ອຍລົດ' },
    'Mở GPS/POD': { vi: 'Mở GPS/POD', en: 'Open GPS/POD', la: 'ເປີດ GPS/POD' },
    'Mở Finance': { vi: 'Mở Finance', en: 'Open Finance', la: 'ເປີດໜ້າການເງິນ' }
  };

  const formatMetric = (metric) => {
    if (!metric) return '—';
    if (lang === 'la') {
      return String(metric)
        .replace(/phút\/ngày/gi, 'ນາທີ/ວັນ')
        .replace(/phút/gi, 'ນາທີ')
        .replace(/ngày/gi, 'ວັນ')
        .replace(/đơn/gi, 'ໃບສັ່ງ');
    }
    if (lang === 'en') {
      return String(metric)
        .replace(/phút\/ngày/gi, 'mins/day')
        .replace(/phút/gi, 'mins')
        .replace(/ngày/gi, 'days')
        .replace(/đơn/gi, 'orders');
    }
    return metric;
  };

  const localizeSummary = (summary) => {
    if (lang !== 'la' || !summary) return summary;
    return String(summary)
      .replace(/SLA có (\d+) cảnh báo, (\d+) cảnh báo nghiêm trọng/gi, 'SLA ມີ $1 ແຈ້ງເຕືອນ, $2 ແຈ້ງເຕືອນຮ້າຍແຮງ')
      .replace(/ưu tiên xử lý các bucket trễ lớn và gửi POD trước khi demo/gi, 'ໃຫ້ບູລິມະສິດແກ້ໄຂບັນດາ bucket ຊັກຊ້າຫຼາຍ ແລະ ສົ່ງ POD ກ່ອນ demo')
      .replace(/ưu tiên xử lý các bucket trễ lớn và thiếu POD trước khi demo/gi, 'ໃຫ້ບູລິມະສິດແກ້ໄຂບັນດາ bucket ຊັກຊ້າຫຼາຍ ແລະ ຂາດ POD ກ່ອນ demo');
  };

  const kpis = {};
  Object.keys(report.kpis || {}).forEach(key => {
    const kpi = report.kpis[key];
    kpis[key] = Object.assign({}, kpi, { label: pick(kpiLabelMap, kpi.label) });
  });

  return {
    kpis,
    executive_summary: localizeSummary(report.executive_summary),
    aging_buckets: (report.aging_buckets || []).map(bucket => (
      Object.assign({}, bucket, { label: pick(agingLabelMap, bucket.label) })
    )),
    trend_by_day: report.trend_by_day || [],
    risk_heatmap: (report.risk_heatmap || []).map(group => (
      Object.assign({}, group, { dimension: pick(dimMap, group.dimension) })
    )),
    sla_playbook: (report.sla_playbook || []).map(item => Object.assign({}, item, {
      label: pick(playbookLabelMap, item.label),
      instruction: pick(playbookInstrMap, item.instruction)
    })),
    drilldown_rows: (report.drilldown_rows || []).slice(0, 12).map(row => Object.assign({}, row, {
      issue_label: pick(issueLabelMap, row.issue_label),
      owner: pick(ownerMap, row.owner),
      action_label: pick(actionMap, row.action_label),
      metric: formatMetric(row.metric)
    }))
  };
}

/**
 * Dựng pane "Chất lượng dịch vụ" trong workspace Phân tích.
 *
 * Phần trình bày nằm ở js/sla-analytics.js. Hàm này chỉ lo lấy dữ liệu, dịch
 * nhãn, rồi gắn HTML vào các container.
 */
function renderReportingDrilldown() {
  if (!window.TmsCockpit || !window.SlaAnalytics || typeof document === 'undefined') return;

  const heroEl = document.getElementById('reporting-hero');
  const tilesEl = document.getElementById('reporting-kpi-cards');
  const panelsEl = document.getElementById('reporting-panels');
  const heatmapEl = document.getElementById('reporting-risk-heatmap');
  const tableEl = document.getElementById('reporting-drilldown-table');
  if (!heroEl || !tilesEl || !panelsEl || !tableEl) return;

  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
  const report = localizeReportingDrilldown(
    window.TmsCockpit.buildReportingDrilldown(appState || {}),
    lang
  );
  const view = window.SlaAnalytics;

  heroEl.innerHTML = view.onTimeHero(report.kpis, report.executive_summary, lang);
  tilesEl.innerHTML = view.kpiTiles(report.kpis, lang);
  panelsEl.innerHTML = [
    view.agingBuckets(report.aging_buckets, lang),
    view.trendByDay(report.trend_by_day, lang),
    view.slaPlaybook(report.sla_playbook, lang)
  ].join('');
  if (heatmapEl) heatmapEl.innerHTML = view.riskHeatmap(report.risk_heatmap, lang);
  tableEl.innerHTML = view.drilldownRows(report.drilldown_rows, lang);
}

/*
   Gói /api/tms/finance/dashboard gần nhất, và cờ chống gọi lặp.

   VÌ SAO PHẢI LẤY SỐ TỪ MÁY CHỦ. Bốn thẻ số liệu của Finance Cockpit trước
   đây được đếm ngay tại máy khách, trên ba mảng `appState.freight_actual_costs
   / ap_invoices / settlements`. Hai điều làm con số đó sai mà không ai thấy:

     · `/api/data/all` bôi trắng đúng ba mảng đó, nên chúng RỖNG. Đo trên dữ
       liệu thật: ba hồ sơ chi phí đang chờ duyệt, thẻ vẫn ghi 0.
     · Kể cả sau khi nạp bổ sung (`hydrateFinanceState`), ba đường liệt kê
       đều chỉ trả 100 bản ghi mới nhất. Ở quy mô hàng nghìn chuyến thì đếm
       trên 100 dòng là đếm sai, và màn hình không nói ra điều đó.

   Máy chủ đếm bằng `COUNT(*)` trên toàn bảng nên không vướng cả hai. Danh
   sách bên dưới vẫn là 100 dòng mới nhất — đó là việc CẦN LÀM GẦN NHẤT, khác
   với con số tổng, nên khi hai bên lệch thì thẻ nói rõ "xem được N mới nhất".
*/
let soLieuTaiChinhMayChu = null;
let dangNapSoLieuTaiChinh = false;

async function napSoLieuTaiChinhTuMayChu() {
  if (dangNapSoLieuTaiChinh) return soLieuTaiChinhMayChu;
  dangNapSoLieuTaiChinh = true;
  try {
    const res = await fetch(`${API_BASE}/api/tms/finance/dashboard`, { headers: financeAuthHeaders() });
    // Không được im lặng ở đây. Một 403 vì thiếu quyền tài chính sẽ khiến
    // màn hình quay về đếm tại máy — tức về đúng con số 0 sai cũ — nên phải
    // báo ra, giống cách `hydrateFinanceState` xử lý.
    if (!res.ok) {
      baoNapThatBai('bảng số liệu tài chính', new Error(`Máy chủ trả về ${res.status}`));
      return null;
    }
    const payload = await res.json();
    soLieuTaiChinhMayChu = (payload && payload.data) || null;
    return soLieuTaiChinhMayChu;
  } catch (err) {
    baoNapThatBai('bảng số liệu tài chính', err);
    return null;
  } finally {
    dangNapSoLieuTaiChinh = false;
  }
}

/**
 * Thay bốn con số đếm-tại-máy bằng số đếm-toàn-bảng của máy chủ.
 *
 * Chỉ ghi đè những khoá máy chủ thật sự trả về: thiếu một khoá thì giữ số cũ
 * chứ không đặt về 0 — số cũ sai vì hẹp, còn 0 thì sai hẳn.
 */
function apSoLieuMayChuVaoTheKpi(kpis) {
  const goi = soLieuTaiChinhMayChu;
  if (!goi || !kpis) return kpis;
  const cap = Number(goi.list_row_cap || 0);
  const dat = (khoa, so) => {
    if (!kpis[khoa] || so === null || so === undefined) return;
    kpis[khoa].count = Number(so);
    if (cap > 0 && Number(so) > cap) kpis[khoa].note = `xem được ${cap} mới nhất bên dưới`;
  };
  dat('actual_cost_pending', goi.actual_cost_pending_count);
  dat('ap_waiting_post', goi.ap_waiting_post_count);
  dat('settlement_open', goi.settlement_open_count);
  if (kpis.total_payable && goi.total_payable !== null && goi.total_payable !== undefined) {
    kpis.total_payable.amount = Number(goi.total_payable);
    kpis.total_payable.currency = goi.currency_code || kpis.total_payable.currency || 'VND';
  }
  return kpis;
}

function renderFinanceCockpit() {
  if (!window.TmsCockpit || typeof document === 'undefined') return;
  const kpisEl = document.getElementById('finance-cockpit-kpis');
  const costsEl = document.getElementById('finance-cockpit-costs');
  const apEl = document.getElementById('finance-cockpit-ap');
  const settlementsEl = document.getElementById('finance-cockpit-settlements');
  if (!kpisEl || !costsEl || !apEl || !settlementsEl) return;

  // Lần đầu vào màn thì gói của máy chủ chưa có; nạp rồi vẽ lại đúng một lần.
  if (!soLieuTaiChinhMayChu && !dangNapSoLieuTaiChinh) {
    napSoLieuTaiChinhTuMayChu().then(goi => { if (goi) renderFinanceCockpit(); });
  }

  const cockpit = window.TmsCockpit.buildFinanceCockpitSummary(appState || {});
  apSoLieuMayChuVaoTheKpi(cockpit.kpis);
  const money = (amount, currency = 'VND') => `${Number(amount || 0).toLocaleString('vi-VN')} ${currency}`;
  kpisEl.innerHTML = Object.values(cockpit.kpis).map(kpi => `
    <div style="background:#ffffff; border:1px solid #dbeafe; border-radius:14px; padding:14px; box-shadow:0 4px 12px rgba(15,23,42,0.04);">
      <div style="font-size:.78rem; color:#64748b; font-weight:800; text-transform:uppercase;">${kpi.label}</div>
      <div style="font-size:1.55rem; font-weight:950; color:#2563eb; margin-top:6px;">${kpi.amount !== undefined ? money(kpi.amount, kpi.currency) : kpi.count}</div>
      ${kpi.note ? `<div style="font-size:.7rem; color:#94a3b8; font-weight:700; margin-top:4px;">${escapeHtml(kpi.note)}</div>` : ''}
    </div>
  `).join('');

  const renderRows = (rows, emptyText, kind) => rows.length ? rows.map(row => `
    <div style="border:1px solid #e2e8f0; border-radius:12px; padding:11px 12px; background:#f8fafc; display:grid; gap:5px;">
      <div style="display:flex; justify-content:space-between; gap:10px; align-items:center;">
        <strong style="color:#0f172a;">${escapeHtml(row.title)}</strong>
        <span style="font-size:.72rem; font-weight:900; color:#0369a1; background:#e0f2fe; border-radius:999px; padding:4px 8px;">${row.status_label}</span>
      </div>
      <div style="font-size:.78rem; color:#64748b;">${row.subtitle}</div>
      <div style="display:flex; justify-content:space-between; gap:10px; align-items:center; flex-wrap:wrap;">
        <div style="font-size:.9rem; color:#15803d; font-weight:900;">${money(row.amount, row.currency)}</div>
        <button class="fiori-btn fiori-btn-secondary" onclick="openFinanceDeepForm('${escapeJsAttr(kind)}', '${escapeJsAttr(row.id || row.title || '')}')" style="padding:5px 9px; font-size:.72rem;"><i class="fa-solid fa-up-right-from-square"></i> Mở hồ sơ</button>
      </div>
    </div>
  `).join('') : `
    <div style="border:1px dashed #cbd5e1; border-radius:12px; padding:16px; color:#64748b; text-align:center; background:#ffffff;">${emptyText}</div>
  `;

  costsEl.innerHTML = renderRows(cockpit.costs, 'Không có Actual Cost đang chờ xử lý.', 'actual_cost');
  apEl.innerHTML = renderRows(cockpit.ap_invoices, 'Không có AP Invoice đang chờ hạch toán.', 'ap_invoice');
  settlementsEl.innerHTML = renderRows(cockpit.settlements, 'Không có settlement đang mở.', 'settlement');
  renderFinanceProcessCockpit();
  renderFinanceCloseoutWorkbench();
  renderFinanceConfigHealth();
  renderFinanceRecordDetail();
}

let selectedFinanceDetailKey = '';
let financeCommandCounter = 0;
let pendingFinanceAction = null;

function renderFinanceProcessCockpit() {
  if (!window.TmsCockpit || !window.TmsCockpit.buildFinanceProcessCockpit || typeof document === 'undefined') return;
  const flowEl = document.getElementById('finance-process-flow');
  const lanesEl = document.getElementById('finance-process-lanes');
  const blockersEl = document.getElementById('finance-process-blockers');
  if (!flowEl || !lanesEl || !blockersEl) return;
  const process = window.TmsCockpit.buildFinanceProcessCockpit(appState || {});
  flowEl.innerHTML = process.flow.map((step, index) => `
    <div style="display:flex; align-items:center; gap:7px;">
      <div style="border:1px solid ${step.status === 'active' ? '#93c5fd' : '#e2e8f0'}; background:${step.status === 'active' ? '#eff6ff' : '#ffffff'}; color:${step.status === 'active' ? '#2563eb' : '#64748b'}; border-radius:999px; padding:7px 10px; font-size:.78rem; font-weight:950;">
        ${step.order}. ${step.label} <span style="margin-left:4px;">${step.count}</span>
      </div>
      ${index < process.flow.length - 1 ? '<i class="fa-solid fa-arrow-right" style="color:#94a3b8; font-size:.75rem;"></i>' : ''}
    </div>
  `).join('');
  lanesEl.innerHTML = process.lanes.map(lane => `
    <div style="border:1px solid #dbeafe; border-radius:13px; background:#ffffff; padding:11px; display:grid; gap:8px;">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px;">
        <div>
          <strong style="color:#0f172a;">${lane.label}</strong>
          <div style="font-size:.73rem; color:#64748b; margin-top:3px;">${lane.description}</div>
        </div>
        <span style="font-size:.72rem; font-weight:950; color:#0369a1; background:#e0f2fe; border-radius:999px; padding:4px 8px;">${lane.count}</span>
      </div>
      <div style="display:grid; gap:7px;">
        ${lane.cards.length ? lane.cards.map(card => {
    const onClick = card.kind === 'payment' ? "switchView('accounting')" : `selectFinanceWorkItem('${card.detail_key}')`;
    return `
          <button onclick="${onClick}" style="text-align:left; border:1px solid #e2e8f0; border-radius:10px; background:#f8fafc; padding:8px; cursor:pointer;">
            <div style="display:flex; justify-content:space-between; gap:6px;"><strong style="color:#0f172a;">${card.title}</strong><span style="font-size:.68rem; font-weight:900; color:#64748b;">${card.status_label}</span></div>
            <div style="font-size:.72rem; color:#64748b; margin-top:3px;">${card.subtitle}</div>
            <div style="font-size:.76rem; color:#15803d; font-weight:950; margin-top:3px;">${card.amount_label}</div>
          </button>
        `;
  }).join('') : `<div style="border:1px dashed #cbd5e1; border-radius:10px; padding:10px; color:#64748b; text-align:center; font-size:.78rem;">Chưa có hồ sơ ở bước này.</div>`}
      </div>
    </div>
  `).join('');
  blockersEl.innerHTML = process.blockers.length ? process.blockers.map(blocker => `
    <button onclick="openCockpitNavigation('${blocker.navigation.view}', '${blocker.navigation.target}')" style="text-align:left; border:1px solid #fed7aa; background:#fff7ed; color:#92400e; border-radius:10px; padding:9px 11px; cursor:pointer; font-weight:850;">
      <i class="fa-solid fa-triangle-exclamation"></i> ${blocker.message}
    </button>
  `).join('') : `
    <div style="border:1px solid #bbf7d0; background:#ecfdf5; color:#047857; border-radius:10px; padding:9px 11px; font-weight:850;">
      <i class="fa-solid fa-circle-check"></i> Cấu hình Finance đủ để chạy Actual Cost → AP → Settlement/Payment.
    </div>
  `;
}

function renderFinanceCloseoutWorkbench() {
  if (!window.TmsCockpit?.buildFinanceCloseoutWorkbench || typeof document === 'undefined') return;
  const kpisEl = document.getElementById('finance-closeout-kpis');
  const listEl = document.getElementById('finance-closeout-list');
  const actionsEl = document.getElementById('finance-closeout-actions');
  if (!kpisEl || !listEl || !actionsEl) return;
  const workbench = window.TmsCockpit.buildFinanceCloseoutWorkbench(appState || {});
  const money = (amount, currency = 'VND') => `${Number(amount || 0).toLocaleString('vi-VN')} ${currency}`;
  kpisEl.innerHTML = Object.values(workbench.kpis).map(kpi => `
    <div style="background:#ffffff; border:1px solid #dbeafe; border-radius:12px; padding:10px;">
      <div style="font-size:.72rem; color:#64748b; font-weight:900;">${kpi.label}</div>
      <div style="font-size:1.25rem; color:#2563eb; font-weight:950; margin-top:4px;">${kpi.count}</div>
    </div>
  `).join('');
  listEl.innerHTML = workbench.items.length ? workbench.items.slice(0, 8).map(item => {
    const color = item.readiness === 'ready' ? '#059669' : item.readiness === 'warning' ? '#d97706' : '#dc2626';
    return `
      <div style="display:grid; grid-template-columns:1fr auto; gap:10px; align-items:center; background:#ffffff; border:1px solid ${color}; border-radius:12px; padding:10px;">
        <div>
          <div style="font-weight:950; color:#0f172a;">${item.trace_label}</div>
          <div style="font-size:.78rem; color:#64748b; margin-top:4px;">${item.status_label} • ${money(item.amount, item.currency_code)}</div>
        </div>
        <button class="fiori-btn" onclick="openFinanceCloseoutAction('${item.next_action.code}', '${item.next_action.detail_key}')" style="background:#ffffff; border-color:${color}; color:${color}; font-weight:950; white-space:nowrap;">
          <i class="fa-solid fa-arrow-up-right-from-square"></i> ${item.next_action.label}
        </button>
      </div>
    `;
  }).join('') : '<div style="background:#ffffff; border:1px dashed #cbd5e1; border-radius:12px; padding:14px; color:#64748b; text-align:center;">Chưa có Actual Cost để closeout.</div>';
  actionsEl.innerHTML = (workbench.guidance || []).map(text => `
    <div style="background:#ffffff; border:1px dashed #bfdbfe; border-radius:10px; padding:8px 10px; color:#475569; font-size:.78rem; font-weight:800;">
      <i class="fa-solid fa-circle-info" style="color:#2563eb;"></i> ${text}
    </div>
  `).join('');
}

function openFinanceCloseoutAction(actionCode, detailKey) {
  selectedFinanceDetailKey = detailKey || selectedFinanceDetailKey;
  switchView('accounting');
  renderFinanceRecordDetail();
  setTimeout(() => {
    document.getElementById('finance-detail-summary')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    showToast(actionCode === 'CLOSEOUT_DONE'
      ? 'Hồ sơ này đã đủ điều kiện chốt/đối soát.'
      : 'Đã mở hồ sơ tài chính đúng bước. Kiểm tra rồi bấm action trong hồ sơ để ghi nhận.');
  }, 0);
}

function renderFinanceActionWorkbench() {
  if (!window.TmsCockpit || typeof document === 'undefined') return;
  const kpisEl = document.getElementById('finance-action-kpis');
  const listEl = document.getElementById('finance-action-worklist');
  const guidanceEl = document.getElementById('finance-action-guidance');
  if (!kpisEl || !listEl || !guidanceEl || !window.TmsCockpit.buildFinanceActionWorkbench) return;

  const filters = {
    kind: document.getElementById('finance-action-kind-filter')?.value || '',
    status: document.getElementById('finance-action-status-filter')?.value || '',
    search: document.getElementById('finance-action-search-input')?.value || ''
  };
  const workbench = window.TmsCockpit.buildFinanceActionWorkbench(appState || {}, filters);
  if (!selectedFinanceDetailKey && workbench.worklist[0]) {
    selectedFinanceDetailKey = workbench.worklist[0].detail_key;
  }
  const money = (amount, currency = 'VND') => `${Number(amount || 0).toLocaleString('vi-VN')} ${currency}`;
  kpisEl.innerHTML = Object.values(workbench.kpis).map(kpi => `
    <div style="background:#ffffff; border:1px solid #dbeafe; border-radius:12px; padding:11px 12px;">
      <div style="font-size:.72rem; color:#64748b; font-weight:900; text-transform:uppercase;">${kpi.label}</div>
      <div style="font-size:1.25rem; color:#2563eb; font-weight:950; margin-top:4px;">${kpi.count}</div>
    </div>
  `).join('');

  const severityStyle = {
    warning: { border: '#f59e0b', bg: '#fffbeb', color: '#92400e', label: 'Cần xử lý' },
    success: { border: '#10b981', bg: '#ecfdf5', color: '#047857', label: 'Sẵn sàng' },
    info: { border: '#38bdf8', bg: '#f0f9ff', color: '#0369a1', label: 'Theo dõi' }
  };
  listEl.innerHTML = workbench.worklist.length ? workbench.worklist.slice(0, 12).map(item => {
    const style = severityStyle[item.severity] || severityStyle.info;
    return `
      <div style="border-left:4px solid ${style.border}; border-radius:12px; background:#ffffff; padding:12px 13px; box-shadow:0 3px 10px rgba(15,23,42,0.04); display:grid; gap:8px;">
        <div style="display:flex; justify-content:space-between; gap:12px; align-items:flex-start;">
          <div>
            <div style="font-weight:950; color:#0f172a;">${escapeHtml(item.title)}</div>
            <div style="font-size:.8rem; color:#64748b; margin-top:3px;">${item.subtitle}</div>
          </div>
          <span style="font-size:.72rem; font-weight:950; border-radius:999px; padding:4px 8px; background:${style.bg}; color:${style.color}; white-space:nowrap;">${style.label}</span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap;">
          <div style="font-size:.82rem; color:#334155;">
            <strong>${item.status_label}</strong> • <span style="color:#15803d; font-weight:900;">${money(item.amount, item.currency)}</span>
          </div>
          <button class="fiori-btn fiori-btn-secondary" onclick="selectFinanceWorkItem('${item.detail_key}')" style="padding:6px 10px; font-size:.76rem;">Xem chi tiết</button>
          <button class="fiori-btn fiori-btn-primary" onclick="runFinanceWorkbenchAction('${item.detail_key}')" style="padding:6px 10px; font-size:.76rem;">${item.action_label}</button>
        </div>
      </div>
    `;
  }).join('') : `
    <div style="border:1px dashed #bfdbfe; border-radius:12px; padding:16px; color:#047857; background:#ffffff; text-align:center; font-weight:850;">Không có việc tài chính tồn đọng.</div>
  `;

  guidanceEl.innerHTML = workbench.guidance.map(text => `
    <div style="border:1px solid #dbeafe; border-radius:10px; padding:9px 11px; background:#ffffff; color:#475569; font-size:.82rem;">
      <i class="fa-solid fa-circle-info" style="color:#2563eb;"></i> ${text}
    </div>
  `).join('');
  renderFinanceRecordDetail();
}

window.applyFinanceActionFilters = function () {
  renderFinanceActionWorkbench();
};

window.selectFinanceWorkItem = function (detailKey) {
  selectedFinanceDetailKey = detailKey || '';
  renderFinanceRecordDetail();
};

window.openFinanceDeepForm = function (kind, id) {
  const normalizedKind = kind === 'actual_cost' ? 'cost' : kind === 'ap_invoice' ? 'ap' : kind;
  const candidateKey = `${normalizedKind}:${id}`;
  selectedFinanceDetailKey = candidateKey;
  switchView('accounting');
  setTimeout(() => {
    renderFinanceActionWorkbench();
    renderFinanceRecordDetail();
    document.getElementById('finance-detail-summary')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, 0);
};

function financeAuthHeaders() {
  const token = (typeof window !== 'undefined' && window.EPL_TMS_API_TOKEN)
    || (typeof localStorage !== 'undefined' && localStorage.getItem('EPL_TMS_API_TOKEN'))
    || '';
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function executeFinanceCommand(command) {
  if (!command || !command.path) {
    showToast('Thao tác tài chính này chưa có endpoint xử lý. Vui lòng kiểm tra cấu hình Finance Cockpit.');
    return { ok: false };
  }
  const opId = recordOperationLog({
    status: 'pending',
    title: `Dang xu ly: ${command.name || 'finance'}`,
    detail: 'Dang gui lenh len server, vui long doi xac nhan.',
    path: `${command?.method || 'POST'} ${command?.path || ''}`,
  });
  financeCommandCounter += 1;
  const idempotencyKey = `finance-ui-${Date.now()}-${financeCommandCounter}`;
  try {
    const response = await fetch(`${API_BASE}${command.path}`, {
      method: command.method || 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Idempotency-Key': idempotencyKey,
        ...financeAuthHeaders()
      },
      body: JSON.stringify(command.body || {})
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = payload.detail || {};
      const message = detail.message || payload.message || 'Thao tác tài chính chưa thực hiện được. Kiểm tra quyền, token hoặc Master Data.';
      showToast(`⚠️ ${message}`);
      recordOperationLog({
        id: opId,
        status: 'error',
        title: `Khong luu duoc: ${command.name || 'finance'}`,
        detail: message,
        path: `${command?.method || 'POST'} ${command?.path || ''}`,
      });
      return { ok: false, payload };
    }
    showToast(payload.message || 'Đã xử lý thao tác tài chính thành công.');
    recordOperationLog({
      id: opId,
      status: 'success',
      title: `Da luu: ${command.name || 'finance'}`,
      detail: payload.message || 'Server da xac nhan thao tac tai chinh.',
      path: `${command?.method || 'POST'} ${command?.path || ''}`,
    });
    if (typeof window.loadAllData === 'function') await window.loadAllData();
    // Vừa duyệt / hạch toán / thanh toán xong thì bốn con số đếm-toàn-bảng đã
    // cũ. Bỏ gói cũ đi để lần vẽ ngay dưới đây nạp lại từ máy chủ — giữ gói cũ
    // là hiện một con số mà chính người dùng vừa làm cho nó sai.
    soLieuTaiChinhMayChu = null;
    if (typeof renderFinanceCockpit === 'function') renderFinanceCockpit();
    if (typeof renderFinanceActionWorkbench === 'function') renderFinanceActionWorkbench();
    return { ok: true, payload };
  } catch (error) {
    showToast(`⚠️ Không gọi được API tài chính: ${error.message}`);
    recordOperationLog({
      id: opId,
      status: 'error',
      title: `Mat ket noi: ${command.name || 'finance'}`,
      detail: error.message,
      path: `${command?.method || 'POST'} ${command?.path || ''}`,
    });
    return { ok: false, error };
  }
}

function setFinanceActionFieldVisible(fieldId, visible) {
  const element = document.getElementById(fieldId);
  if (element) element.style.display = visible ? 'grid' : 'none';
}

function openFinanceActionForm(action) {
  if (!action || !action.command) {
    showToast('Thao tác tài chính này chưa có lệnh xử lý.');
    return { ok: false };
  }
  const modal = document.getElementById('finance-action-form-modal');
  if (!modal) return executeFinanceCommand(action.command);
  pendingFinanceAction = action;
  const command = action.command;
  const body = command.body || {};
  const isCreateAp = command.path.includes('/ap-invoices') && command.path.includes('/costs/');
  const isCreateSettlement = command.path.includes('/settlements') && command.path.includes('/ap-invoices/');
  const isPayment = command.path.includes('/payments');
  // Đảo bút toán: backend BẮT BUỘC có `reason` (422 REVERSAL_REASON_REQUIRED).
  const isReversal = command.path.endsWith('/reverse');
  const today = FormatUtils.dateInputValue();

  document.getElementById('finance-action-form-title').textContent = action.label || 'Thao tác tài chính';
  document.getElementById('finance-action-form-subtitle').textContent = isCreateAp
    ? 'Nhập thông tin hóa đơn nhà cung cấp trước khi tạo AP Invoice.'
    : isCreateSettlement
      ? 'Chọn kỳ đối soát trước khi tạo Settlement.'
      : isPayment
        ? 'Nhập chứng từ và số tiền thanh toán. Hệ thống sẽ kiểm tra số dư còn lại.'
        : isReversal
          ? 'Đảo bút toán hủy hiệu lực chứng từ đã hạch toán. Bắt buộc ghi lý do — lý do đi vào Audit Log và không sửa được sau.'
          : 'Xác nhận chuyển trạng thái hồ sơ. Thao tác sẽ được ghi Audit Log.';
  document.getElementById('finance-action-confirm-note').textContent = `Hồ sơ: ${selectedFinanceDetailKey || 'đang chọn'} • ${action.label || 'Xác nhận thao tác'}`;

  setFinanceActionFieldVisible('finance-action-vendor-invoice-wrap', isCreateAp);
  setFinanceActionFieldVisible('finance-action-invoice-date-wrap', isCreateAp);
  setFinanceActionFieldVisible('finance-action-due-date-wrap', isCreateAp);
  setFinanceActionFieldVisible('finance-action-settlement-period-wrap', isCreateSettlement);
  setFinanceActionFieldVisible('finance-action-payment-amount-wrap', isPayment);
  setFinanceActionFieldVisible('finance-action-payment-method-wrap', isPayment);
  setFinanceActionFieldVisible('finance-action-reference-wrap', isPayment);
  setFinanceActionFieldVisible('finance-action-posting-date-wrap', isPayment);
  setFinanceActionFieldVisible('finance-action-reason-wrap', isReversal);

  document.getElementById('finance-action-vendor-invoice').value = body.vendor_invoice_no || '';
  document.getElementById('finance-action-invoice-date').value = body.invoice_date || today;
  document.getElementById('finance-action-due-date').value = body.due_date || today;
  document.getElementById('finance-action-settlement-period').value = body.settlement_period || today.slice(0, 7);
  document.getElementById('finance-action-payment-amount').value = body.amount || '';
  document.getElementById('finance-action-payment-method').value = body.payment_method === 'cash' ? 'cash' : 'bank_transfer';
  document.getElementById('finance-action-reference').value = body.reference_no || '';
  document.getElementById('finance-action-posting-date').value = body.posting_date || today;
  document.getElementById('finance-action-reason').value = body.reason || '';
  modal.style.display = 'flex';
  return { ok: true };
}

function closeFinanceActionForm() {
  const modal = document.getElementById('finance-action-form-modal');
  if (modal) modal.style.display = 'none';
  pendingFinanceAction = null;
}

async function submitFinanceActionForm() {
  const action = pendingFinanceAction;
  if (!action || !action.command) {
    showToast('Chưa có thao tác tài chính để xác nhận.');
    return { ok: false };
  }
  const command = action.command;
  const body = { ...(command.body || {}) };
  const isCreateAp = command.path.includes('/ap-invoices') && command.path.includes('/costs/');
  const isCreateSettlement = command.path.includes('/settlements') && command.path.includes('/ap-invoices/');
  const isPayment = command.path.includes('/payments');
  const isReversal = command.path.endsWith('/reverse');

  if (isReversal) {
    body.reason = document.getElementById('finance-action-reason').value.trim();
    // Chặn tại đây thay vì gửi lên rồi nhận 422: người dùng đang mở đúng cái form có ô đó.
    if (body.reason.length < 10) {
      showToast('⚠️ Lý do đảo bút toán phải ghi rõ, ít nhất 10 ký tự. Lý do này đi vào Audit Log.');
      return { ok: false };
    }
  }

  if (isCreateAp) {
    body.vendor_invoice_no = document.getElementById('finance-action-vendor-invoice').value.trim();
    body.invoice_date = document.getElementById('finance-action-invoice-date').value;
    body.due_date = document.getElementById('finance-action-due-date').value;
    if (!body.vendor_invoice_no || !body.invoice_date || !body.due_date) {
      showToast('⚠️ Vui lòng nhập đủ số hóa đơn, ngày hóa đơn và ngày đến hạn.');
      return { ok: false };
    }
    if (body.due_date < body.invoice_date) {
      showToast('Ngày đến hạn không được nhỏ hơn ngày hóa đơn.');
      return { ok: false };
    }
  }
  if (isCreateSettlement) {
    body.settlement_period = document.getElementById('finance-action-settlement-period').value;
    if (!body.settlement_period) {
      showToast('⚠️ Vui lòng chọn kỳ đối soát.');
      return { ok: false };
    }
  }
  if (isPayment) {
    body.amount = Number(document.getElementById('finance-action-payment-amount').value || 0);
    body.payment_method = document.getElementById('finance-action-payment-method').value;
    body.reference_no = document.getElementById('finance-action-reference').value.trim();
    body.posting_date = document.getElementById('finance-action-posting-date').value;
    if (!Number.isFinite(body.amount) || body.amount <= 0) {
      showToast('⚠️ Số tiền thanh toán phải lớn hơn 0.');
      return { ok: false };
    }
    if (!body.reference_no || !body.posting_date) {
      showToast('⚠️ Vui lòng nhập mã tham chiếu và ngày hạch toán.');
      return { ok: false };
    }
  }
  closeFinanceActionForm();
  return executeFinanceCommand({ ...command, body });
}

async function runFinanceDetailAction(actionIndex = 0) {
  const detail = window.TmsCockpit.buildFinanceRecordDetail(appState || {}, selectedFinanceDetailKey);
  const action = (detail.actions || [])[Number(actionIndex) || 0];
  if (!action) {
    showToast('Chưa có thao tác tài chính cho hồ sơ này.');
    return { ok: false };
  }
  if (!action.command) {
    switchView('accounting');
    return { ok: true };
  }
  return openFinanceActionForm(action);
}

async function runFinanceWorkbenchAction(detailKey) {
  selectedFinanceDetailKey = detailKey || selectedFinanceDetailKey;
  renderFinanceRecordDetail();
  return runFinanceDetailAction(0);
}

function renderFinanceRecordDetail() {
  if (!window.TmsCockpit || !window.TmsCockpit.buildFinanceRecordDetail || typeof document === 'undefined') return;
  const summaryEl = document.getElementById('finance-detail-summary');
  const timelineEl = document.getElementById('finance-detail-timeline');
  const actionsEl = document.getElementById('finance-detail-actions');
  if (!summaryEl || !timelineEl || !actionsEl) return;
  const detail = window.TmsCockpit.buildFinanceRecordDetail(appState || {}, selectedFinanceDetailKey);
  summaryEl.innerHTML = `
    <div style="display:flex; justify-content:space-between; gap:12px; align-items:flex-start; border:1px solid #e2e8f0; border-radius:12px; padding:12px; background:#f8fafc;">
      <div>
        <div style="font-size:.78rem; color:#64748b; font-weight:900;">${detail.kind_label}</div>
        <div style="font-size:1.05rem; color:#0f172a; font-weight:950; margin-top:3px;">${detail.title}</div>
      </div>
      <div style="text-align:right;">
        <div style="font-size:.78rem; color:#64748b; font-weight:900;">${detail.status_label}</div>
        <div style="font-size:1rem; color:#15803d; font-weight:950; margin-top:3px;">${detail.amount_label}</div>
      </div>
    </div>
    <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(120px,1fr)); gap:8px;">
      ${detail.fields.map(field => `
        <div style="border:1px solid #e2e8f0; border-radius:10px; padding:9px; background:#ffffff;">
          <div style="font-size:.7rem; color:#64748b; font-weight:900; text-transform:uppercase;">${field.label}</div>
          <div style="font-size:.85rem; color:#0f172a; font-weight:850; margin-top:3px;">${field.value}</div>
        </div>
      `).join('')}
    </div>
  `;
  const stageStyle = {
    done: { bg: '#ecfdf5', color: '#047857', icon: 'fa-circle-check', label: 'Xong' },
    current: { bg: '#eff6ff', color: '#2563eb', icon: 'fa-circle-play', label: 'Đang xử lý' },
    pending: { bg: '#f8fafc', color: '#64748b', icon: 'fa-clock', label: 'Chờ' }
  };
  timelineEl.innerHTML = detail.timeline.map(step => {
    const style = stageStyle[step.status] || stageStyle.pending;
    return `
      <div style="background:${style.bg}; color:${style.color}; border:1px solid #dbeafe; border-radius:12px; padding:10px;">
        <div style="font-weight:950; display:flex; align-items:center; gap:6px;"><i class="fa-solid ${style.icon}"></i> ${step.label}</div>
        <div style="font-size:.72rem; font-weight:900; margin-top:4px;">${style.label}</div>
      </div>
    `;
  }).join('');
  // Thao tác `critical` là đảo bút toán — nó hủy hiệu lực một chứng từ đã
  // hạch toán. Cho nó màu đỏ và biểu tượng riêng, đừng để nó trông giống
  // "bước tiếp theo" nằm ngay bên cạnh.
  actionsEl.innerHTML = detail.actions.map((action, index) => {
    const nangCap = action.severity === 'critical';
    const lop = nangCap ? 'fiori-btn-secondary'
      : (action.severity === 'success' ? 'fiori-btn-primary' : 'fiori-btn-secondary');
    const mau = nangCap ? ' color:#b42318; border-color:#fecaca;' : '';
    const icon = nangCap ? 'fa-rotate-left'
      : (action.command ? 'fa-play' : 'fa-arrow-up-right-from-square');
    return `
    <button class="fiori-btn ${lop}" onclick="runFinanceDetailAction(${index})" style="padding:7px 11px; font-size:.78rem;${mau}">
      <i class="fa-solid ${icon}"></i> ${escapeHtml(action.label)}
    </button>`;
  }).join('');
}

function renderFinanceConfigHealth() {
  if (!window.TmsCockpit || !window.TmsCockpit.buildFinanceConfigHealth || typeof document === 'undefined') return;
  const progressEl = document.getElementById('finance-config-health-progress');
  const itemsEl = document.getElementById('finance-config-health-items');
  if (!progressEl || !itemsEl) return;
  const health = window.TmsCockpit.buildFinanceConfigHealth(appState || {});
  progressEl.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
      <span style="font-size:.78rem; color:#64748b; font-weight:900;">Mức sẵn sàng cấu hình</span>
      <strong style="color:#2563eb;">${health.progress.percent}%</strong>
    </div>
    <div style="height:8px; border-radius:999px; background:#e2e8f0; overflow:hidden;">
      <div style="height:100%; width:${health.progress.percent}%; background:linear-gradient(90deg,#2563eb,#10b981);"></div>
    </div>
  `;
  itemsEl.innerHTML = health.items.map(item => `
    <button onclick="openCockpitNavigation('master-data', '${item.target}')" style="text-align:left; border:1px solid ${item.status === 'done' ? '#bbf7d0' : '#fed7aa'}; background:${item.status === 'done' ? '#f0fdf4' : '#fff7ed'}; color:#0f172a; border-radius:10px; padding:9px 10px; cursor:pointer;">
      <div style="display:flex; justify-content:space-between; gap:8px; align-items:center;">
        <strong>${item.label}</strong>
        <span style="font-size:.7rem; font-weight:950; color:${item.status === 'done' ? '#047857' : '#92400e'};">${item.status === 'done' ? 'Đã có' : 'Thiếu'}</span>
      </div>
      <div style="font-size:.75rem; color:#64748b; margin-top:3px;">${item.message}</div>
    </button>
  `).join('');
}

function renderFinanceMasterDataTabs() {
  if (!window.TmsCockpit || typeof document === 'undefined') return;
  const tabs = window.TmsCockpit.buildFinanceMasterDataTabs(appState || {});
  const targets = {
    'md-tab-tax-codes': {
      bodyId: 'finance-master-tax-table',
      actionId: 'finance-master-tax-actions',
      kind: 'tax_code',
      idKey: 'code',
      columns: ['code', 'rate', 'mode', 'effective', 'status_label']
    },
    'md-tab-accounting-periods': {
      bodyId: 'finance-master-period-table',
      actionId: 'finance-master-period-actions',
      kind: 'accounting_period',
      idKey: 'id',
      columns: ['id', 'name', 'range', 'status_label']
    },
    'md-tab-carriers': {
      bodyId: 'finance-master-carrier-table',
      actionId: 'finance-master-carrier-actions',
      kind: 'carrier',
      idKey: 'id',
      columns: ['id', 'name', 'tax_code', 'type', 'status_label']
    },
    'md-tab-account-mappings': {
      bodyId: 'finance-master-mapping-table',
      actionId: 'finance-master-mapping-actions',
      kind: 'account_mapping',
      idKey: 'mapping_key',
      columns: ['mapping_key', 'account_code', 'effective', 'status_label']
    }
  };

  tabs.forEach(tab => {
    const target = targets[tab.id];
    if (!target) return;
    const body = document.getElementById(target.bodyId);
    renderFinanceMasterConfigActions(tab, target.actionId);
    const count = document.querySelector(`[data-finance-master-count="${tab.id}"]`);
    if (count) count.innerText = `${tab.count} dòng`;
    if (!body) return;
    body.innerHTML = tab.rows.length ? tab.rows.map(row => `
      <tr>
        ${target.columns.map(key => `<td>${row[key] || '—'}</td>`).join('')}
        <td>${renderFinanceMasterRowActions(target.kind, row[target.idKey], row.status_label)}</td>
      </tr>
    `).join('') : `
      <tr><td colspan="${target.columns.length + 1}" style="text-align:center; color:#64748b; padding:18px;">${tab.empty_message || 'Chưa có dữ liệu. Vào Master Data hoặc script seed để cấu hình trước khi demo.'}</td></tr>
    `;
  });
}

function renderFinanceMasterRowActions(kind, id, statusLabelText = '') {
  const safeId = String(id || '').replace(/'/g, "\\'");
  const locked = /khóa|ngưng|inactive|closed/i.test(String(statusLabelText || ''));
  return `
    <div style="display:flex; gap:6px; flex-wrap:wrap;">
      <button class="fiori-btn fiori-btn-secondary" onclick="editFinanceMasterRecord('${kind}', '${safeId}')" style="padding:5px 8px; font-size:.72rem;"><i class="fa-solid fa-pen"></i> Sửa</button>
      <button class="fiori-btn fiori-btn-secondary" onclick="toggleFinanceMasterStatus('${kind}', '${safeId}')" style="padding:5px 8px; font-size:.72rem;"><i class="fa-solid ${locked ? 'fa-unlock' : 'fa-lock'}"></i> ${locked ? 'Mở' : 'Khóa'}</button>
      <button class="fiori-btn" onclick="deleteFinanceMasterRecord('${kind}', '${safeId}')" style="padding:5px 8px; font-size:.72rem; border-color:#fecaca; color:#b91c1c; background:#fff1f2;"><i class="fa-solid fa-trash"></i> Xóa</button>
    </div>
  `;
}

function renderFinanceMasterConfigActions(tab, actionId) {
  const container = document.getElementById(actionId);
  if (!container) return;
  const actions = Array.isArray(tab.actions) ? tab.actions : [];
  container.innerHTML = actions.map(action => `
    <button class="fiori-btn ${action.severity === 'secondary' ? 'fiori-btn-secondary' : ''}" onclick="${action.code === 'SEED_EXAMPLE' ? `seedFinanceMasterExample('${action.kind}')` : `openFinanceMasterConfig('${action.kind}')`}" style="padding:8px 12px; font-size:.82rem; white-space:nowrap;">
      <i class="fa-solid ${action.code === 'SEED_EXAMPLE' ? 'fa-wand-magic-sparkles' : 'fa-plus'}"></i> ${action.label}
    </button>
  `).join('');
  if (tab.guidance && tab.guidance.length) {
    container.insertAdjacentHTML('beforeend', `
      <button class="fiori-btn fiori-btn-secondary" onclick="showToast('${tab.guidance[0].replace(/'/g, "\\'")}')" style="padding:8px 12px; font-size:.82rem; white-space:nowrap;">
        <i class="fa-solid fa-circle-info"></i> Hướng dẫn
      </button>
    `);
  }
}

const FINANCE_MASTER_CONFIG = {
  tax_code: {
    title: 'Thêm mã thuế',
    subtitle: 'Dùng cho Actual Cost, AP Invoice và hạch toán thuế.',
    path: '/api/master-data/tax-codes',
    fieldsId: 'finance-master-tax-fields'
  },
  accounting_period: {
    title: 'Thêm kỳ kế toán',
    subtitle: 'Kỳ mở/khóa kiểm soát thời điểm post AP, payment và settlement.',
    path: '/api/master-data/accounting-periods',
    fieldsId: 'finance-master-period-fields'
  },
  carrier: {
    title: 'Thêm carrier/vendor',
    subtitle: 'Cấu hình nhà vận chuyển thuê ngoài hoặc đội xe nội bộ của công ty.',
    path: '/api/tms/carriers',
    fieldsId: 'finance-master-carrier-fields'
  },
  account_mapping: {
    title: 'Thêm mapping tài khoản',
    subtitle: 'Mapping GL cho cost, AP, payment và chênh lệch tỷ giá.',
    path: '/api/master-data/account-mappings',
    fieldsId: 'finance-master-mapping-fields'
  }
};

function financeMasterValue(id) {
  return (document.getElementById(id)?.value || '').trim();
}

function financeMasterDateTime(dateValue, endOfDay = false) {
  return FormatUtils.dayBoundary(dateValue, endOfDay);
}

// SỬA LỖI: bản gốc gọi toISOString() mà KHÔNG bù múi giờ, nên với UTC+7 mọi
// thời điểm trước 07:00 sáng trả về sai ngày — 2026-01-01T00:00:00 hiện thành
// 2025-12-31. Hàm này dùng cho ngày bắt đầu/kết thúc KỲ KẾ TOÁN, nên lệch một
// ngày ở đây là lệch biên kỳ. FormatUtils.dateInputValue có bước bù đó.
function financeMasterDateInput(value) {
  if (!value) return '';
  const formatted = FormatUtils.dateInputValue(value);
  return formatted || String(value).slice(0, 10);
}

function findFinanceMasterRecord(kind, id) {
  const value = String(id || '');
  if (kind === 'tax_code') return (appState.tax_codes || []).find(row => String(row.code || row.id) === value);
  if (kind === 'accounting_period') return (appState.accounting_periods || []).find(row => String(row.id || row.period_id) === value);
  if (kind === 'carrier') return (appState.carriers || []).find(row => String(row.id || row.carrier_id) === value);
  if (kind === 'account_mapping') return (appState.account_mappings || []).find(row => String(row.mapping_key || row.key) === value);
  return null;
}

window.openFinanceMasterConfig = function (kind, record = null) {
  const config = FINANCE_MASTER_CONFIG[kind];
  if (!config) {
    showToast('Chưa có form cấu hình cho mục Master Data này.');
    return;
  }
  const modal = document.getElementById('finance-master-config-modal');
  if (!modal) return;
  const today = FormatUtils.dateInputValue();
  document.getElementById('finance-master-kind').value = kind;
  document.getElementById('finance-master-edit-id').value = record
    ? String(record.code || record.id || record.carrier_id || record.mapping_key || record.key || '')
    : '';
  document.getElementById('finance-master-config-title').innerText = config.title;
  document.getElementById('finance-master-config-subtitle').innerText = config.subtitle;
  ['finance-master-tax-fields', 'finance-master-period-fields', 'finance-master-carrier-fields', 'finance-master-mapping-fields'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = id === config.fieldsId ? 'grid' : 'none';
  });

  const titlePrefix = record ? 'Sửa' : 'Thêm';
  document.getElementById('finance-master-config-title').innerText = config.title.replace('Thêm', titlePrefix);

  if (kind === 'tax_code') {
    document.getElementById('finance-master-tax-code').value = record?.code || record?.id || '';
    document.getElementById('finance-master-tax-rate').value = record?.rate ?? '0.08';
    document.getElementById('finance-master-tax-mode').value = record?.mode || record?.tax_mode || 'exclusive';
    document.getElementById('finance-master-tax-from').value = financeMasterDateInput(record?.effective_from) || today;
    document.getElementById('finance-master-tax-to').value = financeMasterDateInput(record?.effective_to);
  } else if (kind === 'accounting_period') {
    document.getElementById('finance-master-period-id').value = record?.id || today.slice(0, 7);
    document.getElementById('finance-master-period-start').value = financeMasterDateInput(record?.starts_at || record?.start_date) || `${today.slice(0, 7)}-01`;
    document.getElementById('finance-master-period-end').value = financeMasterDateInput(record?.ends_at || record?.end_date) || today;
    document.getElementById('finance-master-period-status').value = record?.status || 'open';
  } else if (kind === 'carrier') {
    document.getElementById('finance-master-carrier-id').value = record?.id || record?.carrier_id || '';
    document.getElementById('finance-master-carrier-name').value = record?.name || record?.carrier_name || '';
    document.getElementById('finance-master-carrier-tax').value = record?.tax_code || record?.tax_id || '';
    document.getElementById('finance-master-carrier-contact').value = record?.contact_person || '';
    document.getElementById('finance-master-carrier-phone').value = record?.phone || '';
    document.getElementById('finance-master-carrier-email').value = record?.email || '';
    document.getElementById('finance-master-carrier-internal').checked = Boolean(record?.is_internal);
  } else if (kind === 'account_mapping') {
    document.getElementById('finance-master-mapping-key').value = record?.mapping_key || record?.key || '';
    document.getElementById('finance-master-mapping-account').value = record?.account_code || record?.gl_account || '';
    document.getElementById('finance-master-mapping-from').value = financeMasterDateInput(record?.effective_from) || today;
    document.getElementById('finance-master-mapping-to').value = financeMasterDateInput(record?.effective_to);
  }
  modal.style.display = 'flex';
};

window.closeFinanceMasterConfig = function () {
  const modal = document.getElementById('finance-master-config-modal');
  if (modal) modal.style.display = 'none';
};

window.submitFinanceMasterConfig = async function () {
  const kind = document.getElementById('finance-master-kind')?.value || '';
  const editId = document.getElementById('finance-master-edit-id')?.value || '';
  const config = FINANCE_MASTER_CONFIG[kind];
  if (!config) {
    showToast('Chưa chọn loại Master Data cần lưu.');
    return;
  }
  const payloadByKind = {
    tax_code: () => ({
      code: financeMasterValue('finance-master-tax-code'),
      rate: financeMasterValue('finance-master-tax-rate'),
      mode: financeMasterValue('finance-master-tax-mode') || 'exclusive',
      effective_from: financeMasterValue('finance-master-tax-from'),
      effective_to: financeMasterValue('finance-master-tax-to') || null,
      is_active: true
    }),
    accounting_period: () => ({
      id: financeMasterValue('finance-master-period-id'),
      starts_at: financeMasterDateTime(financeMasterValue('finance-master-period-start')),
      ends_at: financeMasterDateTime(financeMasterValue('finance-master-period-end'), true),
      status: financeMasterValue('finance-master-period-status') || 'open'
    }),
    carrier: () => ({
      id: financeMasterValue('finance-master-carrier-id'),
      name: financeMasterValue('finance-master-carrier-name'),
      tax_code: financeMasterValue('finance-master-carrier-tax') || null,
      contact_person: financeMasterValue('finance-master-carrier-contact') || null,
      phone: financeMasterValue('finance-master-carrier-phone') || null,
      email: financeMasterValue('finance-master-carrier-email') || null,
      is_internal: Boolean(document.getElementById('finance-master-carrier-internal')?.checked),
      status: 'active'
    }),
    account_mapping: () => ({
      mapping_key: financeMasterValue('finance-master-mapping-key'),
      account_code: financeMasterValue('finance-master-mapping-account'),
      effective_from: financeMasterDateTime(financeMasterValue('finance-master-mapping-from')) || null,
      effective_to: financeMasterDateTime(financeMasterValue('finance-master-mapping-to'), true) || null
    })
  };
  const payload = payloadByKind[kind]();
  const editPath = editId ? financeMasterRecordPath(kind, editId) : '';
  try {
    const response = await fetch(`${API_BASE}${editPath || config.path}`, {
      method: editPath ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      showToast(`⚠️ ${result?.detail?.message || result?.message || 'Không lưu được Master Data Finance.'}`);
      return;
    }
    showToast(result.message || 'Đã lưu cấu hình Master Data vào CSDL.');
    closeFinanceMasterConfig();
    await loadData();
  } catch (error) {
    showToast(`⚠️ Không gọi được API Master Data Finance: ${error.message}`);
  }
};

function financeMasterRecordPath(kind, id) {
  const encoded = encodeURIComponent(id || '');
  if (kind === 'tax_code') return `/api/master-data/tax-codes/${encoded}`;
  if (kind === 'accounting_period') return `/api/master-data/accounting-periods/${encoded}`;
  if (kind === 'carrier') return `/api/tms/carriers/${encoded}`;
  if (kind === 'account_mapping') return `/api/master-data/account-mappings/${encoded}`;
  return '';
}

window.editFinanceMasterRecord = function (kind, id) {
  const record = findFinanceMasterRecord(kind, id);
  if (!record) {
    showToast('Không tìm thấy dòng Master Data cần sửa. Vui lòng tải lại dữ liệu.');
    return;
  }
  openFinanceMasterConfig(kind, record);
};

window.toggleFinanceMasterStatus = async function (kind, id) {
  const record = findFinanceMasterRecord(kind, id);
  const basePath = financeMasterRecordPath(kind, id);
  if (!record || !basePath) {
    showToast('Không tìm thấy dòng Master Data cần khóa/mở.');
    return;
  }
  const current = String(record.status || (record.is_active === false ? 'inactive' : 'active')).toLowerCase();
  const lock = !['inactive', 'closed'].includes(current);
  const body = kind === 'accounting_period'
    ? { status: lock ? 'closed' : 'open' }
    : kind === 'tax_code'
      ? { is_active: !lock }
      : { status: lock ? 'inactive' : 'active' };
  try {
    const response = await fetch(`${API_BASE}${basePath}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      showToast(`⚠️ ${payload?.detail?.message || 'Không cập nhật được trạng thái Master Data.'}`);
      return;
    }
    showToast(payload.message || 'Đã cập nhật trạng thái Master Data.');
    await loadData();
  } catch (error) {
    showToast(`⚠️ Không gọi được API trạng thái Master Data: ${error.message}`);
  }
};

window.deleteFinanceMasterRecord = async function (kind, id) {
  const basePath = financeMasterRecordPath(kind, id);
  if (!basePath) {
    showToast('Không tìm thấy endpoint xóa Master Data.');
    return;
  }
  if (!confirm(`Xóa cấu hình "${id}" khỏi Master Data Finance? Nếu dữ liệu đang được dùng, hệ thống sẽ báo khóa thay vì xóa.`)) return;
  try {
    const response = await fetch(`${API_BASE}${basePath}`, { method: 'DELETE' });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      showToast(`⚠️ ${payload?.detail?.message || 'Không xóa được Master Data. Có thể dữ liệu đang được sử dụng.'}`);
      return;
    }
    showToast(payload.message || 'Đã xóa Master Data.');
    await loadData();
  } catch (error) {
    showToast(`⚠️ Không gọi được API xóa Master Data: ${error.message}`);
  }
};

window.seedFinanceMasterExample = async function (kind) {
  const today = FormatUtils.dateInputValue();
  const examples = {
    tax_code: {
      path: '/api/master-data/tax-codes',
      payload: { code: 'VAT8', rate: '0.08', mode: 'exclusive', effective_from: today, is_active: true }
    },
    accounting_period: {
      path: '/api/master-data/accounting-periods',
      payload: { id: today.slice(0, 7), starts_at: `${today.slice(0, 7)}-01T00:00:00`, ends_at: `${today.slice(0, 7)}-28T23:59:59`, status: 'open' }
    },
    carrier: {
      path: '/api/tms/carriers',
      payload: { id: 'EPL-INTERNAL-FLEET', name: 'EPL Logistics - Đội xe nội bộ', tax_code: '0312345678', is_internal: true, status: 'active' }
    },
    account_mapping: {
      path: '/api/master-data/account-mappings',
      payload: { mapping_key: 'carrier_expense:freight', account_code: '6427', effective_from: `${today}T00:00:00` }
    }
  };
  const example = examples[kind];
  if (!example) {
    showToast('Chưa có mẫu cấu hình cho mục này.');
    return;
  }
  try {
    const response = await fetch(`${API_BASE}${example.path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(example.payload)
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      showToast(`⚠️ ${payload?.detail?.message || payload?.message || 'Không lưu được Master Data Finance.'}`);
      return;
    }
    showToast(payload.message || 'Đã lưu dữ liệu mẫu Master Data Finance vào CSDL.');
    await loadData();
  } catch (error) {
    showToast(`⚠️ Không gọi được API Master Data Finance: ${error.message}`);
  }
};


let dispatchCalendarFilters = { vehicle_id: '', driver_id: '', status: '' };
let dispatchCalendarDate = new Date();
let dispatchCalendarView = 'week';
let selectedDispatchCalendarOrderId = '';
let selectedDispatchFleetIsoDate = '';
let dispatchDayFleetFilters = { query: '', status: '', page: 1, page_size: 50 };
let dispatchEligibleVehicleIds = null;
let draggedDispatchDOId = '';
let pendingDispatchResourceChange = { orderId: '', actionCode: '' };
let dispatchResourceChangeSequence = 0;
let activeDispatchWorkState = 'pending';
let activeDispatchAnalysisTab = 'schedule';
let activeDispatchWeekView = 'schedule';
let dispatchDetailReturnFocus = null;
let dispatchDetailUnlocked = false;
let dispatchStepModalState = { step: '', target: null, parent: null, nextSibling: null, returnFocus: null, bodyOverflow: '' };
let dispatchDayWorkbenchState = {
  open: false,
  queueParent: null,
  queueNextSibling: null,
  detailParent: null,
  detailNextSibling: null,
  bodyOverflow: ''
};

function dispatchDateInputValue(value = dispatchCalendarDate) {
  return FormatUtils.dateInputValue(value);
}

window.setDispatchCalendarDate = function (value) {
  if (!value) return;
  dispatchCalendarDate = new Date(`${value}T12:00:00`);
  selectedDispatchFleetIsoDate = value;
  renderDispatchCalendar();
  renderDispatchDOs();
};

window.moveDispatchCalendarDate = function (days) {
  const next = new Date(dispatchCalendarDate);
  const increment = Number(days || 0) * (dispatchCalendarView === 'week' ? 7 : 1);
  next.setDate(next.getDate() + increment);
  dispatchCalendarDate = next;
  selectedDispatchFleetIsoDate = dispatchDateInputValue(next);
  renderDispatchCalendar();
  renderDispatchDOs();
};

window.setDispatchCalendarView = function (view) {
  dispatchCalendarView = view === 'week' ? 'week' : 'day';
  renderDispatchCalendar();
};

function switchDispatchWeekView(viewName) {
  activeDispatchWeekView = viewName === 'available' ? 'available' : 'schedule';
}

function openDispatchDetail(trigger) {
  const detail = document.getElementById('dispatch-detail');
  if (!detail) return;
  dispatchDetailReturnFocus = trigger || document.activeElement;
  detail.hidden = false;
  if (window.matchMedia?.('(max-width: 1100px)').matches) {
    detail.querySelector('[data-drawer-focusable="true"]')?.focus();
  }
}

function closeDispatchDetail() {
  const detail = document.getElementById('dispatch-detail');
  if (!detail || !window.matchMedia?.('(max-width: 1100px)').matches) return;
  detail.hidden = true;
  dispatchDetailReturnFocus?.focus?.();
}

/**
 * Bàn phím cho khung chi tiết điều phối.
 *
 * Trước đây hàm này còn lo cả bảng chọn "Công cụ" — mũi lên/xuống giữa các mục,
 * Escape để đóng. Bảng chọn đó đã bỏ: nó chỉ có một mục là "Cảnh báo", mà khối
 * cảnh báo nay là cột thứ ba thường trực, nên bấm nút chỉ mở ra một ngăn trống.
 */
function setupDispatchWorkbenchAccessibility() {
  const detail = document.getElementById('dispatch-detail');
  detail?.addEventListener('keydown', event => {
    if (event.key === 'Escape') return closeDispatchDetail();
    if (event.key !== 'Tab' || !window.matchMedia?.('(max-width: 1100px)').matches) return;
    const items = Array.from(detail.querySelectorAll('[data-drawer-focusable="true"]:not([hidden])'));
    if (!items.length) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
}

if (typeof document !== 'undefined') document.addEventListener('DOMContentLoaded', setupDispatchWorkbenchAccessibility);

function setDispatchButtonState(button, active) {
  if (!button) return;
  button.classList.toggle('active', active);
  button.setAttribute('aria-selected', active ? 'true' : 'false');
}

function switchDispatchAnalysisTab(tabName, options = {}) {
  const allowedTabs = ['schedule', 'capacity', 'alerts', 'week'];
  activeDispatchAnalysisTab = allowedTabs.includes(tabName) ? tabName : 'schedule';
  allowedTabs.forEach(name => {
    setDispatchButtonState(
      document.getElementById(`dispatch-analysis-${name}`),
      name === activeDispatchAnalysisTab
    );
    const pane = document.getElementById(`dispatch-analysis-pane-${name}`);
    if (pane) pane.classList.toggle('active', name === activeDispatchAnalysisTab);
  });
  const shell = document.getElementById('dispatch-calendar-panel');
  if (shell) shell.hidden = false;
  if (options.scroll !== false && shell) shell.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function switchDispatchWorkState(stateName) {
  const allowedStates = ['pending', 'scheduled', 'conflict'];
  activeDispatchWorkState = allowedStates.includes(stateName) ? stateName : 'pending';
  allowedStates.forEach(name => setDispatchButtonState(
    document.getElementById(`dispatch-state-${name}`),
    name === activeDispatchWorkState
  ));

  const primaryWorkspace = document.getElementById('dispatch-primary-workspace');
  const analysisShell = document.getElementById('dispatch-calendar-panel');
  if (primaryWorkspace) primaryWorkspace.hidden = false;
  if (analysisShell) analysisShell.hidden = false;

  if (activeDispatchWorkState !== 'pending') {
    switchDispatchAnalysisTab(activeDispatchWorkState === 'conflict' ? 'alerts' : 'schedule', { scroll: false });
  }
}

function dispatchResourceIdempotencyKey(orderId, actionCode) {
  dispatchResourceChangeSequence += 1;
  return `dispatch-resource-${orderId || 'DO'}-${actionCode || 'CHANGE_RESOURCE'}-${Date.now()}-${dispatchResourceChangeSequence}`;
}

function setDispatchCalendarOptions(selectEl, options, emptyLabel, selectedValue) {
  if (!selectEl) return;
  const selected = selectedValue || '';
  selectEl.innerHTML = [
    `<option value="">${emptyLabel}</option>`,
    ...(options || []).map(option => `<option value="${option.value}" ${String(option.value) === selected ? 'selected' : ''}>${option.label}</option>`)
  ].join('');
  selectEl.value = selected;
}

function normalizeDispatchStaticText() {
  if (typeof document === 'undefined') return;
  if (typeof currentLang !== 'undefined' && currentLang !== 'vi') return;
  const setText = (selector, text) => {
    const el = document.querySelector(selector);
    if (el) el.textContent = text;
  };
  const setHTML = (selector, html) => {
    const el = document.querySelector(selector);
    if (el) el.innerHTML = html;
  };

  setHTML('#dispatch-workbench-header h2', '<i class="fa-solid fa-truck-ramp-box" style="color:#2563eb;"></i> Điều phối & thực thi');
  const headerNote = document.querySelector('#dispatch-workbench-header h2')?.parentElement?.querySelector('div');
  if (headerNote) headerNote.textContent = 'Gán xe, tài xế, kiểm tra lịch và cảnh báo trước khi xuất bến.';
  setText('#dispatch-resource-subtitle', 'Chọn DO ở bên trái, gán xe/tài xế rồi chuyển sang lịch điều phối.');

  const setStateTab = (id, icon, title, subtitle) => {
    const btn = document.getElementById(id);
    if (!btn) return;
    const countEl = btn.querySelector('.dispatch-state-count');
    const count = countEl ? countEl.textContent : '0';
    const strong = btn.querySelector('strong');
    const small = btn.querySelector('small');
    if (strong) strong.innerHTML = `<i class="${icon}"></i> ${title} <span id="${id}-count" class="dispatch-state-count">${count}</span>`;
    if (small) small.textContent = subtitle;
  };
  setStateTab('dispatch-state-pending', 'fa-solid fa-inbox', 'Chờ điều phối', 'DO cần gán xe và tài xế');
  setStateTab('dispatch-state-scheduled', 'fa-solid fa-calendar-check', 'Đã điều phối', 'Chuyến đã có lịch xuất phát');
  setStateTab('dispatch-state-conflict', 'fa-solid fa-triangle-exclamation', 'Có xung đột', 'Trùng lịch hoặc thiếu tài nguyên');

  const setAnalysisTab = (id, icon, title, subtitle) => {
    const btn = document.getElementById(id);
    if (!btn) return;
    const strong = btn.querySelector('strong');
    const small = btn.querySelector('small');
    if (strong) strong.innerHTML = `<i class="${icon}"></i> ${title}`;
    if (small) small.textContent = subtitle;
  };
  setAnalysisTab('dispatch-analysis-schedule', 'fa-solid fa-chart-gantt', 'Lịch xe', 'Xem chuyến theo xe và khung giờ');
  setAnalysisTab('dispatch-analysis-capacity', 'fa-solid fa-gauge-high', 'Năng lực', 'Xe, tài xế và DO chưa xếp lịch');
  setAnalysisTab('dispatch-analysis-alerts', 'fa-solid fa-triangle-exclamation', 'Cảnh báo', 'Trùng lịch và thiếu tài nguyên');
  setAnalysisTab('dispatch-analysis-week', 'fa-solid fa-calendar-week', 'Kế hoạch 7 ngày', 'Thời điểm xe rảnh lại');

  const search = document.getElementById('dispatch-do-search-input');
  if (search) search.placeholder = 'Tìm nhanh mã DO, khách hàng, tuyến...';

  const selectedDo = document.getElementById('dispatch-selected-do');
  if (selectedDo && selectedDo.options.length) {
    selectedDo.options[0].textContent = 'Chọn DO để gán xe/tài xế...';
  }

  setHTML('#subtab-btn-dispatch', '<i class="fa-solid fa-clipboard-check"></i> Gán xe/tài xế');
  setHTML('#subtab-btn-drivers-ready', '<i class="fa-solid fa-user-check"></i> Tài xế rảnh');
  setHTML('#subtab-btn-vehs-ready', '<i class="fa-solid fa-truck"></i> Xe rảnh');
  setHTML('#subtab-btn-busy', '<i class="fa-solid fa-lock"></i> Đang bận');

  setText('#dispatch-veh-ready-count', document.getElementById('dispatch-veh-ready-count')?.textContent?.replace(/\bXe\b/i, 'xe') || '0 xe');
  const busyCountEl = document.getElementById('dispatch-veh-busy-count');
  if (busyCountEl) busyCountEl.previousElementSibling && (busyCountEl.previousElementSibling.textContent = 'Xe & tài xế bận');
  const driverCountEl = document.getElementById('dispatch-driver-ready-count');
  if (driverCountEl) {
    driverCountEl.previousElementSibling && (driverCountEl.previousElementSibling.textContent = 'Tài xế sẵn sàng');
    driverCountEl.textContent = driverCountEl.textContent.replace('Ngi', 'người').replace('Người', 'người');
  }
}

function applyDispatchCalendarFilters() {
  const vehicleEl = document.getElementById('dispatch-calendar-filter-vehicle');
  const driverEl = document.getElementById('dispatch-calendar-filter-driver');
  const statusEl = document.getElementById('dispatch-calendar-filter-status');
  dispatchCalendarFilters = {
    vehicle_id: vehicleEl ? vehicleEl.value : '',
    driver_id: driverEl ? driverEl.value : '',
    status: statusEl ? statusEl.value : ''
  };
  renderDispatchCalendar();
}

function selectDispatchCalendarItem(orderId) {
  selectedDispatchCalendarOrderId = orderId || '';
  dispatchDetailUnlocked = Boolean(orderId);
  if (orderId) tmsActiveShipment360Id = orderId;
  activeDispatchWorkState = 'scheduled';
  activeDispatchAnalysisTab = 'schedule';
  renderDispatchCalendar();
  if (orderId) openDispatchDetail(document.activeElement);
}

function openShipment360FromDispatch(orderId) {
  const targetId = orderId || selectedDispatchCalendarOrderId || '';
  if (targetId) {
    tmsActiveShipment360Id = targetId;
    tmsActiveTimelineDoId = targetId;
  }
  switchView('operations-360');
  setTimeout(() => selectShipment360(targetId), 0);
}

window.openShipment360Action = function (actionCode, deliveryOrderId) {
  const targetId = deliveryOrderId || tmsActiveShipment360Id || tmsActiveTimelineDoId || selectedDispatchCalendarOrderId || '';
  if (targetId) {
    tmsActiveShipment360Id = targetId;
    tmsActiveTimelineDoId = targetId;
    selectedDispatchCalendarOrderId = targetId;
  }

  if (actionCode === 'OPEN_DISPATCH') {
    switchView('dispatch');
    setTimeout(() => {
      if (targetId) selectedDispatchCalendarOrderId = targetId;
      if (typeof renderDispatchCalendar === 'function') renderDispatchCalendar();
    }, 0);
    return;
  }

  if (actionCode === 'OPEN_GPS_POD') {
    switchView('tracking');
    setTimeout(() => {
      const input = document.getElementById('tracking-do-search');
      if (input && targetId) input.value = targetId;
      if (typeof renderGpsEventTimeline === 'function') renderGpsEventTimeline();
      if (typeof window.trackDO === 'function' && targetId) window.trackDO();
    }, 0);
    return;
  }

  if (actionCode === 'OPEN_FINANCE' || actionCode === 'OPEN_FINANCE_COCKPIT') {
    switchView('accounting');
    setTimeout(() => {
      if (typeof loadAccountingData === 'function') loadAccountingData();
    }, 0);
    return;
  }

  // Đường rơi về Shipment 360 đã bỏ: hành động không có màn riêng thì về Theo dõi.
  switchView('tracking');
};

function renderDispatchSuggestedActions(detail) {
  const actionsEl = document.getElementById('dispatch-calendar-detail-actions');
  if (!actionsEl) return;
  actionsEl.innerHTML = '';
  actionsEl.hidden = true;
  return;
  /* Legacy suggestions are intentionally disabled in the focused dispatch wizard.
  if (!detail.kind) {
    actionsEl.innerHTML = '';
    actionsEl.hidden = true;
    return;
  }
  actionsEl.hidden = false;
  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
  const actions = Array.isArray(detail && detail.suggested_actions) ? detail.suggested_actions : [];
  const orderId = detail && detail.order && detail.order.id || detail && detail.id || '';

  const actionTranslationMap = {
    CHANGE_VEHICLE: {
      label: { vi: 'Đổi xe', en: 'Change Vehicle', la: 'ປ່ຽນລົດ' },
      desc: {
        vi: 'Chuyến chưa đủ xe, vào Dispatch để phân xe phù hợp.',
        en: 'Trip lacks assigned vehicle, assign a suitable truck.',
        la: 'ຖ້ຽວລົດຍັງຂາດລົດ, ເຂົ້າໄປໜ້າປ່ອຍລົດເພື່ອມອບໝາຍລົດທີ່ເໝາະສົມ.'
      }
    },
    CHANGE_DRIVER: {
      label: { vi: 'Đổi tài xế', en: 'Change Driver', la: 'ປ່ຽນຄົນຂັບ' },
      desc: {
        vi: 'Chuyến chưa đủ tài xế, vào Dispatch để phân công.',
        en: 'Trip lacks assigned driver, assign a driver.',
        la: 'ຖ້ຽວລົດຍັງຂາດຄົນຂັບ, ເຂົ້າໄປໜ້າປ່ອຍລົດເພື່ອມອບໝາຍຄົນຂັບ.'
      }
    },
    OPEN_SHIPMENT_360: {
      label: { vi: 'Mở Shipment 360°', en: 'Open Shipment 360°', la: 'ເປີດ Shipment 360°' },
      desc: {
        vi: 'Xem hồ sơ chuyến tổng hợp: timeline A-Z, GPS/POD, dispatch, cost/AP và cảnh báo còn thiếu.',
        en: 'View comprehensive shipment record: timeline A-Z, GPS/POD, dispatch, cost/AP and alerts.',
        la: 'ເບິ່ງຂໍ້ມູນຖ້ຽວລົດແບບຄົບຊຸດ: ຕາຕະລາງ A-Z, GPS/POD, ການປ່ອຍລົດ, ຕົ້ນທຶນ/AP ແລະ ແຈ້ງເຕືອນ.'
      }
    },
    OPEN_DISPATCH: {
      label: { vi: 'Mở điều phối', en: 'Open Dispatch', la: 'ເປີດໜ້າປ່ອຍລົດ' },
      desc: {
        vi: 'Xem chi tiết điều phối, trạng thái xe/tài xế và lịch vận hành.',
        en: 'View dispatch details, vehicle/driver status and operating schedule.',
        la: 'ເບິ່ງລາຍລະອຽດການປ່ອຍລົດ, ສະຖານະພາບລົດ/ຄົນຂັບ ແລະ ຕາຕະລາງປະຕິບັດງານ.'
      }
    },
    OPEN_GPS_POD: {
      label: { vi: 'Mở GPS/POD', en: 'Open GPS/POD', la: 'ເປີດ GPS/POD' },
      desc: {
        vi: 'Theo dõi vị trí, cập nhật sự kiện và bằng chứng giao hàng.',
        en: 'Track live GPS location, status events and proof of delivery.',
        la: 'ຕິດຕາມຕຳແໜ່ງ GPS, ອັບເດດເຫດການ ແລະ ຫຼັກຖານການຈັດສົ່ງ (POD).'
      }
    }
  };

  actionsEl.innerHTML = actions.length ? actions.map(action => {
    const color = action.severity === 'critical' ? '#dc2626' : action.severity === 'warning' ? '#d97706' : '#2563eb';
    const icon = action.code === 'CHANGE_VEHICLE'
      ? 'fa-truck'
      : action.code === 'CHANGE_DRIVER'
        ? 'fa-id-card'
        : action.code === 'OPEN_GPS_POD'
          ? 'fa-location-dot'
          : 'fa-arrow-up-right-from-square';
    const view = action.navigation && action.navigation.view || 'dispatch';
    const clickHandler = ['CHANGE_VEHICLE', 'CHANGE_DRIVER'].includes(action.code)
      ? `openDispatchResourceChange('${orderId}', '${action.code}')`
      // OPEN_SHIPMENT_360: module đã bỏ — đưa về màn Theo dõi, nơi có cùng dữ liệu chuyến.
      : action.code === 'OPEN_SHIPMENT_360'
        ? `switchView('tracking')`
        : `switchView('${view}')`;

    const trans = actionTranslationMap[action.code];
    const displayLabel = (trans && trans.label && trans.label[lang]) || action.label || (lang === 'la' ? 'ເປີດການດຳເນີນງານ' : 'Mở thao tác');
    const displayDesc = (trans && trans.desc && trans.desc[lang]) || action.description || (lang === 'la' ? 'ປະມວນຜົນຖ້ຽວລົດທີ່ເລືອກ.' : 'Xử lý chuyến đang chọn.');

    return `
      <button type="button" class="dispatch-quick-action" onclick="${clickHandler}" style="--dispatch-action-color:${color};">
        <i class="fa-solid ${icon}"></i>
        <span>
          <strong>${displayLabel}</strong>
          <small>${displayDesc}</small>
        </span>
      </button>
    `;
  }).join('') : `
    <div class="dispatch-week-empty">
      ${lang === 'la' ? 'ເລືອກຖ້ຽວລົດເທິງ Gantt ເພື່ອເບິ່ງການດຳເນີນງານທີ່ແນະນຳ.' : 'Chọn một chuyến trên Gantt để xem thao tác gợi ý.'}
    </div>
  `;
  */
}

function setDispatchResourceSelect(selectEl, options, selectedValue) {
  if (!selectEl) return;
  selectEl.innerHTML = (options || []).map(option => {
    const disabled = option.selectable ? '' : 'disabled';
    const selected = String(option.id || '') === String(selectedValue || '') ? 'selected' : '';
    const marker = option.availability === 'available'
      ? 'Rảnh'
      : option.availability === 'current'
        ? 'Hiện tại'
        : option.availability === 'conflict'
          ? 'Trùng lịch'
          : 'Không sẵn sàng';
    return `<option value="${option.id}" ${selected} ${disabled}>${option.label} — ${marker}</option>`;
  }).join('');
  if (selectedValue) selectEl.value = selectedValue;
}

function renderDispatchResourceChangePanel() {
  const panel = document.getElementById('dispatch-resource-change-panel');
  const messageEl = document.getElementById('dispatch-resource-change-message');
  const modeEl = document.getElementById('dispatch-resource-change-mode');
  const vehicleEl = document.getElementById('dispatch-resource-vehicle-select');
  const driverEl = document.getElementById('dispatch-resource-driver-select');
  const versionEl = document.getElementById('dispatch-resource-expected-version');
  const reasonEl = document.getElementById('dispatch-resource-reason');
  if (!panel || !window.TmsCockpit || !window.TmsCockpit.buildDispatchResourceOptions) return;
  const orderId = pendingDispatchResourceChange.orderId || selectedDispatchCalendarOrderId || '';
  if (!orderId) {
    panel.hidden = true;
    panel.style.display = 'none';
    return;
  }
  const options = window.TmsCockpit.buildDispatchResourceOptions(appState || {}, orderId, new Date());
  if (!options.order) {
    panel.hidden = true;
    panel.style.display = 'none';
    return;
  }
  panel.hidden = false;
  panel.style.display = 'block';
  const mode = pendingDispatchResourceChange.actionCode || 'CHANGE_RESOURCE';
  if (modeEl) modeEl.value = mode;
  if (messageEl) {
    const modeLabel = mode === 'CHANGE_VEHICLE' ? 'Đổi xe' : mode === 'CHANGE_DRIVER' ? 'Đổi tài xế' : 'Đổi tài nguyên';
    messageEl.innerHTML = `<i class="fa-solid fa-screwdriver-wrench" style="color:#2563eb;"></i> <strong>${modeLabel}</strong> cho ${orderId}: ${options.message}`;
  }
  setDispatchResourceSelect(vehicleEl, options.vehicles, options.recommended_vehicle_id || options.current_vehicle_id);
  setDispatchResourceSelect(driverEl, options.drivers, options.recommended_driver_id || options.current_driver_id);
  if (versionEl) versionEl.value = options.order.version || options.order.workflow_version || 1;
  if (reasonEl && !reasonEl.value) reasonEl.value = mode === 'CHANGE_VEHICLE'
    ? 'Đổi xe theo cảnh báo Dispatch Calendar/Gantt.'
    : mode === 'CHANGE_DRIVER'
      ? 'Đổi tài xế theo cảnh báo Dispatch Calendar/Gantt.'
      : 'Điều chỉnh xe/tài xế theo Dispatch Calendar/Gantt.';
}
function openDispatchResourceChange(orderId, actionCode) {
  pendingDispatchResourceChange = { orderId: orderId || selectedDispatchCalendarOrderId || '', actionCode: actionCode || '' };
  selectedDispatchCalendarOrderId = pendingDispatchResourceChange.orderId;
  renderDispatchResourceChangePanel();
}

function closeDispatchResourceChange() {
  pendingDispatchResourceChange = { orderId: '', actionCode: '' };
  const panel = document.getElementById('dispatch-resource-change-panel');
  if (panel) {
    panel.hidden = true;
    panel.style.display = 'none';
  }
}

async function applyDispatchResourceChange() {
  const doId = pendingDispatchResourceChange.orderId || selectedDispatchCalendarOrderId || '';
  const vehicleId = document.getElementById('dispatch-resource-vehicle-select')?.value || '';
  const driverId = document.getElementById('dispatch-resource-driver-select')?.value || '';
  const mode = document.getElementById('dispatch-resource-change-mode')?.value || pendingDispatchResourceChange.actionCode || 'CHANGE_RESOURCE';
  const expectedVersion = Number(document.getElementById('dispatch-resource-expected-version')?.value || 1);
  const reason = (document.getElementById('dispatch-resource-reason')?.value || '').trim();
  if (!doId || !vehicleId || !driverId) {
    showToast('Vui lòng chọn đủ DO, xe và tài xế trước khi lưu điều phối.');
    return;
  }
  if (!Number.isInteger(expectedVersion) || expectedVersion < 1) {
    showToast('Version kỳ vọng không hợp lệ. Vui lòng tải lại dữ liệu trước khi điều phối.');
    return;
  }
  // ĐI ĐƯỜNG CHUẨN — điều phối CHUYẾN, không điều lẻ từng DO.
  //
  // Bản trước gọi `PUT /api/delivery-orders/{id}/dispatch`: đường đó đưa DO sang
  // "đang chạy" mà bỏ 9/13 cửa (hạn pháp lý xe, bằng lái, ca trực, Packing
  // List…) và KHÔNG tạo Trip / Freight Order / phân công — DO đi đường đó không
  // hoàn tất được, xe không được giải phóng đúng. Đây là nút duy nhất trên giao
  // diện còn gọi nó. Máy chủ nay cũng từ chối điều lẻ một DO đã có chuyến.
  const tripGate = resolveDispatchTripGate(doId);
  const trip = tripGate && tripGate.trip;
  if (!trip) {
    showToast(`${doId} chưa có chuyến. Lập chuyến ở màn Lệnh giao hàng trước, rồi điều phối chuyến.`);
    return;
  }
  if (trip.status !== 'planned') {
    // Đổi xe / tài xế giữa chuyến đang chạy chưa có đường máy chủ nào hỗ trợ —
    // nói thật thay vì đi cửa tắt và để lại một chuyến với phân công cũ.
    showToast(`Chuyến ${trip.id} đã điều phối (${trip.status}). Đổi xe/tài xế giữa chuyến chưa hỗ trợ: huỷ chuyến rồi lập và điều lại.`);
    return;
  }
  const tripStart = trip.planned_departure_at;
  const tripEnd = trip.planned_return_at || trip.planned_arrival_at;
  if (!tripStart || !tripEnd) {
    showToast('Chuyến thiếu giờ khởi hành hoặc giờ kết thúc. Hoàn thiện chuyến trước khi điều phối.');
    return;
  }
  const result = await dieuPhoiCoXacNhanLoaiXe({
    path: `/api/tms/trips/${trip.id}/dispatch`,
    method: 'PUT',
    body: {
      vehicle_id: vehicleId,
      driver_id: driverId,
      co_driver_id: null,
      expected_version: Number(trip.version || 1),
      assignment_start: new Date(tripStart).toISOString(),
      assignment_end: new Date(tripEnd).toISOString()
    }
  });
  if (!result.ok) return;
  const order = (appState.delivery_orders || []).find(item => String(item.id || '') === String(doId));
  if (order) {
    order.vehicle_id = vehicleId;
    order.driver_id = driverId;
  }
  showToast(`Đã lưu điều phối cho ${doId}: xe ${vehicleId}, tài xế ${driverId}.`);
  closeDispatchResourceChange();
  renderDispatchCalendar();
  if (typeof renderDispatchDOs === 'function') renderDispatchDOs();
  if (typeof renderDispatchSelects === 'function') renderDispatchSelects();
}

function resolveDispatchTripGate(doId) {
  if (!doId || !window.TmsCockpit?.resolveDispatchTripGate) {
    return { state: 'missing', trip: null, trips: [] };
  }
  return window.TmsCockpit.resolveDispatchTripGate(
    doId,
    appState?.transport_trips || [],
    appState?.trip_delivery_orders || []
  );
}

function openDispatchTripGate(doId) {
  const gate = resolveDispatchTripGate(doId);
  if (gate.state === 'ready') {
    showToast(`Trip ${gate.trip.id} đã sẵn sàng. Tiếp tục chọn xe.`);
    window.openDispatchStepModal('schedule');
    return;
  }
  if (gate.state === 'choose') {
    showToast('DO có nhiều Trip đã lập kế hoạch. Vui lòng mở Trip và chọn đúng chuyến trước khi điều phối.');
    switchView('transportation');
    return;
  }
  if (gate.state === 'unavailable') {
    showToast('Trip của DO đã được điều phối hoặc đang vận chuyển, không thể tạo điều phối mới.');
    return;
  }
  if (gate.state === 'draft') {
    activeTripReturnId = gate.trip.id;
    showToast(`Trip ${gate.trip.id} còn ở bản nháp. Hoàn thiện Trip hiện có trước khi chọn xe.`);
    switchView('transportation');
    return;
  }
  openTripReturnAction('create-trip', doId);
}

function updateDispatchWorkflowSteps() {
  const hasDO = Boolean(selectedDispatchCalendarOrderId || document.getElementById('dispatch-selected-do')?.value);
  const tripGate = resolveDispatchTripGate(selectedDispatchCalendarOrderId || document.getElementById('dispatch-selected-do')?.value);
  const hasPlannedTrip = tripGate.state === 'ready';
  const hasVehicle = Boolean(document.getElementById('dispatch-vehicle')?.value);
  const steps = [
    { id: 'dispatch-step-do', active: !hasDO, complete: hasDO },
    { id: 'dispatch-step-trip', active: hasDO && !hasPlannedTrip, complete: hasPlannedTrip },
    { id: 'dispatch-step-schedule', active: hasPlannedTrip && !hasVehicle, complete: hasPlannedTrip && hasVehicle },
    { id: 'dispatch-step-resources', active: hasPlannedTrip && hasVehicle, complete: false }
  ];
  steps.forEach(step => {
    const element = document.getElementById(step.id);
    if (!element) return;
    element.classList.toggle('is-active', step.active);
    element.classList.toggle('is-complete', step.complete);
    const locked = step.id === 'dispatch-step-trip'
      ? !hasDO
      : (step.id === 'dispatch-step-schedule' ? !hasPlannedTrip : (step.id === 'dispatch-step-resources' ? !hasVehicle : false));
    element.setAttribute('aria-disabled', locked ? 'true' : 'false');
  });
}

const dispatchStepModalConfig = {
  // Bước 1 CỐ Ý không có ở đây: cột "DO chờ điều phối" hiện sẵn bên trái, nên
  // đưa nó vào hộp thoại là lấy một thứ đang thấy được rồi che kín màn hình
  // bằng chính nó. `openDispatchStepModal` chặn bước đó ở đầu hàm.
  trip: {
    targetId: '',
    title: 'Kiểm tra Trip',
    description: 'Tạo hoặc hoàn thiện Trip trước khi chọn xe.',
    icon: 'fa-route'
  },
  schedule: {
    targetId: 'dispatch-timeline',
    title: 'Xếp lịch xe',
    description: 'Chọn ngày và phương tiện còn trống.',
    icon: 'fa-calendar-days'
  },
  resources: {
    targetId: 'dispatch-detail',
    title: 'Nhân sự & xuất bến',
    description: 'Gán tài xế, phụ xe, quy cách đóng gói và chốt điều phối.',
    icon: 'fa-id-card'
  }
};

window.openDispatchStepModal = function (step) {
  // BƯỚC 1 không còn mở hộp thoại. Cột "DO chờ điều phối" nay hiện sẵn ở bên
  // trái, nên đưa nó vào hộp thoại là lấy một thứ đang thấy được rồi che kín
  // màn hình bằng chính nó. Bấm bước 1 thì chỉ đưa con trỏ vào ô tìm của cột
  // đó — việc mà người dùng định làm.
  if (step === 'do') {
    const cot = document.getElementById('dispatch-queue');
    const oTim = document.getElementById('dispatch-do-search-input');
    if (cot) cot.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    if (oTim) oTim.focus();
    return;
  }

  const hasDO = Boolean(selectedDispatchCalendarOrderId || document.getElementById('dispatch-selected-do')?.value);
  const tripGate = resolveDispatchTripGate(selectedDispatchCalendarOrderId || document.getElementById('dispatch-selected-do')?.value);
  const hasPlannedTrip = tripGate.state === 'ready';
  const hasVehicle = Boolean(document.getElementById('dispatch-vehicle')?.value);
  if (step === 'trip' && !hasDO) {
    showToast('Vui lòng chọn một DO trước khi kiểm tra Trip.');
    return;
  }
  if (step === 'trip') {
    openDispatchTripGate(selectedDispatchCalendarOrderId || document.getElementById('dispatch-selected-do')?.value);
    return;
  }
  if (step === 'schedule' && !hasPlannedTrip) {
    showToast('DO phải có Trip ở trạng thái Đã lập kế hoạch trước khi chọn xe.');
    openDispatchTripGate(selectedDispatchCalendarOrderId || document.getElementById('dispatch-selected-do')?.value);
    return;
  }
  if (step === 'resources' && !hasVehicle) {
    showToast(hasDO ? 'Vui lòng chọn ngày và xe ở bước 2 trước.' : 'Vui lòng chọn DO và xếp lịch xe trước.');
    return;
  }

  const config = dispatchStepModalConfig[step];
  const modal = document.getElementById('dispatch-step-modal');
  const body = document.getElementById('dispatch-step-modal-body');
  const target = config ? document.getElementById(config.targetId) : null;
  if (!config || !modal || !body || !target) return;

  if (dispatchStepModalState.target) window.closeDispatchStepModal();
  dispatchStepModalState = {
    step,
    target,
    parent: target.parentNode,
    nextSibling: target.nextSibling,
    returnFocus: document.activeElement,
    bodyOverflow: document.body.style.overflow
  };

  document.getElementById('dispatch-step-modal-title').textContent = config.title;
  document.getElementById('dispatch-step-modal-description').textContent = config.description;
  const icon = document.getElementById('dispatch-step-modal-icon');
  if (icon) icon.className = `fa-solid ${config.icon}`;
  modal.dataset.step = step;
  body.appendChild(target);
  target.hidden = false;
  modal.hidden = false;
  document.body.style.overflow = 'hidden';

  if (step === 'resources') dispatchDetailUnlocked = true;
  if (typeof renderDispatchCalendar === 'function') renderDispatchCalendar();
  target.hidden = false;
  document.getElementById('dispatch-step-modal-close')?.focus();
};

window.closeDispatchStepModal = function (event) {
  if (event && event.target !== event.currentTarget) return;
  const modal = document.getElementById('dispatch-step-modal');
  const state = dispatchStepModalState;
  if (!modal || !state.target) {
    if (modal) modal.hidden = true;
    return;
  }

  if (state.nextSibling && state.nextSibling.parentNode === state.parent) {
    state.parent.insertBefore(state.target, state.nextSibling);
  } else {
    state.parent?.appendChild(state.target);
  }
  if (state.step === 'resources') {
    state.target.hidden = true;
    dispatchDetailUnlocked = false;
  }
  modal.hidden = true;
  delete modal.dataset.step;
  document.body.style.overflow = state.bodyOverflow || '';
  const returnFocus = state.returnFocus;
  dispatchStepModalState = { step: '', target: null, parent: null, nextSibling: null, returnFocus: null, bodyOverflow: '' };
  returnFocus?.focus?.();
};

if (typeof document !== 'undefined') document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && !document.getElementById('dispatch-day-workbench-modal')?.hidden) {
    event.preventDefault();
    window.closeDispatchDayWorkbench();
    return;
  }
  if (event.key === 'Escape' && !document.getElementById('dispatch-step-modal')?.hidden) {
    event.preventDefault();
    window.closeDispatchStepModal();
  }
});

function dispatchWeekCellHTML(row, day) {
  const vehicleId = completionEscape(row.resource_id || row.vehicle_id || '');
  const isoDate = completionEscape(day.iso_date || '');
  if (day.status === 'available') {
    return `<button type="button" class="dispatch-week-day-cell is-available" data-dispatch-week-slot="${vehicleId}-${isoDate}" draggable="false" ondragover="onDispatchLaneDragOver(event)" ondrop="onDispatchWeekSlotDrop(event, '${vehicleId}', '${isoDate}')" onclick="selectDispatchWeekSlot('${vehicleId}', '${isoDate}')" aria-label="Xe ${vehicleId} rảnh ngày ${completionEscape(day.label)}">
      <span class="dispatch-week-free-label"><i class="fa-solid fa-circle-plus"></i>Rảnh cả ngày<small>Chọn để xếp DO</small></span>
    </button>`;
  }
  if (day.status === 'maintenance') {
    return `<div class="dispatch-week-day-cell" data-dispatch-week-maintenance="${vehicleId}-${isoDate}">
      <div class="dispatch-week-time-block" style="--dispatch-block-color:#d97706;background:#fff7ed;">
        <strong><i class="fa-solid fa-screwdriver-wrench"></i> ${completionEscape(day.maintenance_label || 'Bảo dưỡng')}</strong>
        <span>Cả ngày · Không điều phối</span>
      </div>
    </div>`;
  }
  const items = day.items || [];
  const firstTripId = completionEscape(items[0]?.id || '');
  const blocks = items.slice(0, 3).map(item => `
    <div class="dispatch-week-time-block" style="--dispatch-block-color:${item.status_color || '#2563eb'};">
      <strong>${completionEscape(item.id || 'Trip')}</strong>
      <span>${completionEscape(item.start_label || '--:--')} → ${completionEscape(item.end_label || '--:--')}</span>
      <span>${completionEscape(statusLabel(item.status_label || ''))}</span>
    </div>
  `).join('');
  return `<button type="button" class="dispatch-week-day-cell ${day.status === 'conflict' ? 'is-conflict' : ''}" onclick="selectDispatchWeekTrip('${firstTripId}')" aria-label="${items.length} chuyến của xe ${vehicleId} ngày ${completionEscape(day.label)}">
    ${blocks}
    ${items.length > 3 ? `<span class="dispatch-week-more">+${items.length - 3} chuyến khác</span>` : ''}
  </button>`;
}

/* `renderDispatchWeekPlanner` da duoc go: no la BAN CU cua man lich tuan,
   da bi `renderDispatchWeekTimetable` ngay ben tren thay the.

   Ban cu ve mot ma tran XE x NGAY, mot dong cho MOI xe. Do bang chinh khuon
   dong cua no: 500 xe -> 1,06 MB HTML va 3.500 nut bam trong MOT lan
   `innerHTML`, dung lai toan bo moi lan doi tuan. Ba khoi chua cua no
   (`dispatch-week-planner-kpis`, `-grid`, `-guidance`) chua bao gio duoc
   dung trong index.html, nen thuc te no chua tung chay.

   Ban dang chay lam khac han, va dung huong da chot cho quy mo ~500 xe:
   mot bang nang luc theo ngay (7 the, moi the la con so ranh/ban/sua
   chua/xung dot), roi `buildDispatchDayFleet` cho danh sach xe cua ngay
   duoc chon — ham do chan `page_size` o 100 dong ke ca khi goi voi
   `Number.MAX_SAFE_INTEGER`, nen so dong ve ra KHONG phu thuoc vao co doi
   xe. Do that voi 500 xe: buildDispatchWeekPlanner mat 47 ms va
   buildDispatchDayFleet tra ve dung 100 dong.

   Hai lop `dispatch-week-pane-schedule` va `dispatch-week-pane-available`
   chi ton tai trong ban cu do va KHONG co mot quy tac CSS nao — them mot
   dau hieu nua rang phan giao dien do chua bao gio duoc hoan thien. */

function renderDispatchWeekTimetable(week) {
  const weekDays = week.days || [];
  if (!weekDays.some(day => day.iso_date === selectedDispatchFleetIsoDate)) {
    const selectedDate = dispatchDateInputValue();
    selectedDispatchFleetIsoDate = weekDays.some(day => day.iso_date === selectedDate)
      ? selectedDate
      : (weekDays[0]?.iso_date || '');
  }
  const dayFleet = window.TmsCockpit.buildDispatchDayFleet(
    week,
    selectedDispatchFleetIsoDate,
    { ...dispatchDayFleetFilters, page: 1, page_size: Number.MAX_SAFE_INTEGER }
  );
  dispatchEligibleVehicleIds = new Set(
    dayFleet.rows.filter(row => row.can_assign).map(row => String(row.vehicle_id))
  );
  const dayCards = weekDays.map(day => {
    const fleet = window.TmsCockpit.buildDispatchDayFleet(week, day.iso_date, { page_size: 10 });
    const orders = dispatchDayOrderSummary(day.iso_date);
    const active = day.iso_date === selectedDispatchFleetIsoDate;
    return `<button type="button" class="dispatch-week-day-summary ${active ? 'is-active' : ''}" onclick="selectDispatchFleetDay('${completionEscape(day.iso_date)}')" aria-label="Mở điều phối ngày ${completionEscape(day.iso_date)}, ${orders.count} DO chờ sắp xếp">
      <strong>${completionEscape(day.label || day.iso_date)}</strong>
      <span class="dispatch-day-order-count ${orders.urgent ? 'is-urgent' : orders.count ? '' : 'is-empty'}">${completionEscape(orders.label)}</span>
      <span><b>${fleet.summary.available}</b> rảnh · <b>${fleet.summary.busy}</b> bận</span>
      <small>${fleet.summary.maintenance} sửa chữa · ${fleet.summary.conflict} xung đột</small>
    </button>`;
  }).join('');
  return `<div class="dispatch-week-day-summaries">${dayCards}</div><div class="dispatch-week-calendar-note"><i class="fa-solid fa-circle-info"></i> Chọn một ngày để xem DO cần sắp, kiểm tra Trip và điều phối nguồn lực.</div>`;
}

function dispatchDayOrderSummary(isoDate) {
  const pending = (eplDeliveryOrders || dispatchDOs || []).filter(isDispatchPendingDO);
  const result = window.TmsCockpit?.filterDispatchOrdersByDate
    ? window.TmsCockpit.filterDispatchOrdersByDate(pending, isoDate)
    : { orders: pending.filter(order => String(order.pickup_window_start || '').slice(0, 10) === isoDate) };
  const count = result.orders?.length || 0;
  const today = dispatchDateInputValue(new Date());
  const urgent = count > 0 && isoDate <= today;
  return {
    count,
    urgent,
    label: count ? `${count} DO ${urgent ? 'cần sắp gấp' : 'cần sắp xếp'}` : 'Không có DO chờ sắp'
  };
}

window.openDispatchDayWorkbench = function (isoDate) {
  const modal = document.getElementById('dispatch-day-workbench-modal');
  const body = document.getElementById('dispatch-day-workbench-body');
  const queue = document.getElementById('dispatch-queue');
  const detail = document.getElementById('dispatch-detail');
  if (!modal || !body || !queue || !detail || !isoDate) return;
  if (dispatchDayWorkbenchState.open) window.closeDispatchDayWorkbench();
  selectedDispatchFleetIsoDate = isoDate;
  dispatchCalendarDate = new Date(`${isoDate}T12:00:00`);
  selectedDispatchCalendarOrderId = '';
  dispatchDetailUnlocked = false;
  dispatchDayWorkbenchState = {
    open: true,
    queueParent: queue.parentNode,
    queueNextSibling: queue.nextSibling,
    detailParent: detail.parentNode,
    detailNextSibling: detail.nextSibling,
    bodyOverflow: document.body.style.overflow
  };
  body.append(queue, detail);
  queue.hidden = false;
  detail.hidden = false;
  const assignment = document.getElementById('subtab-content-dispatch');
  if (assignment) assignment.hidden = true;
  const title = document.getElementById('dispatch-day-workbench-title');
  const description = document.getElementById('dispatch-day-workbench-description');
  if (title) title.innerHTML = `<i class="fa-solid fa-calendar-day"></i> Điều phối ngày ${completionEscape(isoDate)}`;
  if (description) description.textContent = 'Bên trái là DO của ngày đã chọn. DO chưa có Trip sẽ mở form tạo Trip; DO hợp lệ sẽ mở form gán xe và nhân sự.';
  modal.hidden = false;
  document.body.style.overflow = 'hidden';
  renderDispatchDOs();
  renderDispatchCalendar();
  queue.hidden = false;
  detail.hidden = false;
};

window.closeDispatchDayWorkbench = function (event) {
  const modal = document.getElementById('dispatch-day-workbench-modal');
  if (event && event.target !== modal) return;
  const queue = document.getElementById('dispatch-queue');
  const detail = document.getElementById('dispatch-detail');
  const state = dispatchDayWorkbenchState;
  if (queue && state.queueParent) state.queueParent.insertBefore(queue, state.queueNextSibling);
  if (detail && state.detailParent) state.detailParent.insertBefore(detail, state.detailNextSibling);
  if (queue) queue.hidden = true;
  if (detail) detail.hidden = true;
  if (modal) modal.hidden = true;
  document.body.style.overflow = state.bodyOverflow || '';
  dispatchDayWorkbenchState = { open: false, queueParent: null, queueNextSibling: null, detailParent: null, detailNextSibling: null, bodyOverflow: '' };
};

window.selectDispatchFleetDay = function (isoDate) {
  selectedDispatchFleetIsoDate = isoDate || selectedDispatchFleetIsoDate;
  dispatchDayFleetFilters.page = 1;
  renderDispatchCalendar();
  window.openDispatchDayWorkbench(selectedDispatchFleetIsoDate);
};
window.changeDispatchDayFleetPage = function (increment) {
  dispatchDayFleetFilters.page = Math.max(1, Number(dispatchDayFleetFilters.page || 1) + Number(increment || 0));
  renderDispatchCalendar();
};

window.selectDispatchFleetVehicle = function (vehicleId, isoDate) {
  window.selectDispatchWeekSlot(vehicleId, isoDate);
};

window.selectDispatchWeekSlot = function (vehicleId, isoDate) {
  if (isoDate) dispatchCalendarDate = new Date(`${isoDate}T12:00:00`);
  window.selectDispatchVehicleLane(vehicleId);
  updateDispatchWorkflowSteps();
};

window.selectDispatchWeekTrip = function (tripId) {
  selectDispatchCalendarItem(tripId);
};

window.onDispatchWeekSlotDrop = function (event, vehicleId, isoDate) {
  event?.preventDefault();
  const doId = event?.dataTransfer?.getData('text/plain') || draggedDispatchDOId || selectedDispatchCalendarOrderId;
  if (doId) window.selectDispatchDO(doId, true);
  window.selectDispatchWeekSlot(vehicleId, isoDate);
  draggedDispatchDOId = '';
};

function renderDispatchCalendar() {
  if (!window.TmsCockpit || typeof document === 'undefined') return;
  const kpisEl = document.getElementById('dispatch-calendar-kpis');
  const lanesEl = document.getElementById('dispatch-calendar-lanes');
  const conflictsEl = document.getElementById('dispatch-calendar-conflicts');
  const vehicleFilterEl = document.getElementById('dispatch-calendar-filter-vehicle');
  const driverFilterEl = document.getElementById('dispatch-calendar-filter-driver');
  const statusFilterEl = document.getElementById('dispatch-calendar-filter-status');
  const legendEl = document.getElementById('dispatch-calendar-legend');
  const detailSummaryEl = document.getElementById('dispatch-calendar-detail-summary');
  const detailAlertsEl = document.getElementById('dispatch-calendar-detail-alerts');
  const detailEl = document.getElementById('dispatch-detail');
  if (!kpisEl || !lanesEl || !conflictsEl) return;
  if (detailEl) detailEl.hidden = !selectedDispatchCalendarOrderId || !dispatchDetailUnlocked;

  const dateInput = document.getElementById('dispatch-calendar-date');
  if (dateInput && dateInput.value !== dispatchDateInputValue()) dateInput.value = dispatchDateInputValue();
  document.getElementById('dispatch-view-day')?.classList.toggle('active', dispatchCalendarView === 'day');
  document.getElementById('dispatch-view-week')?.classList.toggle('active', dispatchCalendarView === 'week');
  const calendar = window.TmsCockpit.buildDispatchCalendar(appState || {}, dispatchCalendarDate, dispatchCalendarFilters);
  const scheduledIds = new Set(
    (calendar.lanes || []).flatMap(lane => (lane.items || []).map(item => String(item.id || ''))).filter(Boolean)
  );
  const dispatchCounts = {
    pending: (eplDeliveryOrders || dispatchDOs || []).filter(isDispatchPendingDO).length,
    scheduled: scheduledIds.size,
    conflict: (calendar.capacity_alerts || []).length + (calendar.conflicts || []).length
  };
  Object.entries(dispatchCounts).forEach(([name, count]) => {
    const countEl = document.getElementById(`dispatch-state-${name}-count`);
    if (countEl) countEl.textContent = String(count);
  });
  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
  setDispatchCalendarOptions(vehicleFilterEl, calendar.filter_options.vehicles, lang === 'la' ? 'ລົດທັງໝົດ' : (lang === 'en' ? 'All Vehicles' : 'Tất cả xe'), calendar.filters.vehicle_id);
  setDispatchCalendarOptions(driverFilterEl, calendar.filter_options.drivers, lang === 'la' ? 'ຄົນຂັບທັງໝົດ' : (lang === 'en' ? 'All Drivers' : 'Tất cả tài xế'), calendar.filters.driver_id);
  setDispatchCalendarOptions(statusFilterEl, calendar.filter_options.statuses, lang === 'la' ? 'ສະຖານະທັງໝົດ' : (lang === 'en' ? 'All Statuses' : 'Tất cả trạng thái'), calendar.filters.status);
  
  const legendLabelMap = {
    'Chờ xếp lịch': { vi: 'Chờ xếp lịch', en: 'Pending Schedule', la: 'ລໍຖ້າຈັດຕາຕະລາງ' },
    'Chờ điều phối': { vi: 'Chờ điều phối', en: 'Pending Dispatch', la: 'ລໍຖ້າປ່ອຍລົດ' },
    'Đã điều phối': { vi: 'Đã điều phối', en: 'Dispatched', la: 'ປ່ອຍລົດແລ້ວ' },
    'Đang vận chuyển': { vi: 'Đang vận chuyển', en: 'In Transit', la: 'ກຳລັງຂົນສົ່ງ' },
    'Hoàn thành': { vi: 'Hoàn thành', en: 'Completed', la: 'ສຳເລັດແລ້ວ' },
    'Đã hủy': { vi: 'Đã hủy', en: 'Cancelled', la: 'ຍົກເລີກແລ້ວ' }
  };

  if (legendEl) {
    legendEl.innerHTML = calendar.legend.map(item => {
      const localized = (legendLabelMap[item.label] && legendLabelMap[item.label][lang]) || item.label;
      return `
      <span style="display:inline-flex; align-items:center; gap:5px; padding:5px 8px; border-radius:999px; background:#ffffff; border:1px solid #e2e8f0; font-weight:800;">
        <span style="width:9px; height:9px; border-radius:999px; background:${item.color}; display:inline-block;"></span>${localized}
      </span>
    `;
    }).join('');
  }
  kpisEl.innerHTML = Object.values(calendar.kpis).map(kpi => `
    <div style="background:#ffffff; border:1px solid #e0f2fe; border-radius:12px; padding:12px;">
      <div style="font-size:.75rem; color:#64748b; font-weight:800;">${kpi.label}</div>
      <div style="font-size:1.35rem; color:${kpi.count && kpi.label.includes('Cảnh báo') ? '#dc2626' : '#2563eb'}; font-weight:950; margin-top:4px;">${kpi.count}</div>
    </div>
  `).join('');
  const dayLanesHtml = calendar.lanes.length ? calendar.lanes.map(lane => `
    <div class="dispatch-vehicle-lane ${lane.is_available ? 'dispatch-vehicle-lane--available' : ''}" data-dispatch-vehicle-lane="${lane.resource_id}" ondragover="onDispatchLaneDragOver(event)" ondrop="onDispatchLaneDrop(event, '${lane.resource_id}')" onclick="selectDispatchVehicleLane('${lane.resource_id}')" tabindex="0" role="button" aria-label="${lane.is_available ? 'Xe rảnh, chọn để gán DO' : 'Xem lịch xe'} ${lane.resource_id}">
      <div style="background:#f8fafc; padding:10px 12px; font-weight:900; color:#0f172a; border-bottom:1px solid #e2e8f0; display:flex; justify-content:space-between; gap:10px; align-items:center;">
        <span>${lane.label}${lane.is_available ? ' <small class="dispatch-lane-ready">Rảnh, thả DO vào đây</small>' : ''}</span>
        <span style="font-size:.72rem; color:${lane.load_level === 'overlap' ? '#dc2626' : lane.load_level === 'high' ? '#d97706' : '#0369a1'}; background:#ffffff; border:1px solid #e2e8f0; border-radius:999px; padding:4px 8px;">${lang === 'la' ? 'ນຳໃຊ້' : (lang === 'en' ? 'Utilization' : 'Sử dụng')} ${lane.utilization_percent}% • ${lane.load_level === 'overlap' ? (lang === 'la' ? 'ຕາຕະລາງຊ້ອນກັນ' : 'Trùng lịch') : lane.load_level === 'high' ? (lang === 'la' ? 'ໃກ້ເຕັມຕາຕະລາງ' : 'Gần kín lịch') : (lang === 'la' ? 'ປົກກະຕິ' : 'Ổn')}</span>
      </div>
      <div style="display:grid; grid-template-columns:repeat(${calendar.time_axis.labels.length},1fr); gap:0; padding:8px 10px 0; color:#94a3b8; font-size:.68rem; font-weight:800;">
        ${calendar.time_axis.labels.map(label => `<span>${label}</span>`).join('')}
      </div>
      <div style="display:grid; gap:8px; padding:10px;">
        ${lane.items.length ? lane.items.map(item => `
          <div style="position:relative; min-height:58px; background:linear-gradient(90deg,#f8fafc,#ffffff); border:1px dashed #dbeafe; border-radius:12px; overflow:hidden;">
            <button type="button" class="dispatch-calendar-item" data-dispatch-timeline="${item.id}" onclick="selectDispatchCalendarItem('${item.id}')" aria-label="Trip ${item.id}, xe ${item.vehicle_id}, tài xế ${item.driver_id}, từ ${item.start_label} đến ${item.end_label}, trạng thái ${item.status_label}" title="Bấm để xem chi tiết ${item.id}" style="position:absolute; left:${item.gantt.left_percent}%; width:${item.gantt.width_percent}%; min-width:130px; top:7px; bottom:7px; border-left:5px solid ${item.status_color}; background:${String(selectedDispatchCalendarOrderId) === String(item.id) ? '#dbeafe' : '#eff6ff'}; border-radius:7px; padding:8px 10px; cursor:pointer; box-shadow:0 4px 10px rgba(15,23,42,.08);">
              <div style="display:flex; justify-content:space-between; gap:8px;"><strong>${item.id}</strong><span style="font-weight:900; color:#0369a1;">${item.start_label} â†’ ${item.end_label}</span></div>
              <div style="font-size:.74rem; color:#64748b; margin-top:3px;">${item.driver_id} • ${item.duration_hours} ${lang === 'la' ? 'ຊົ່ວໂມງ' : 'giờ'} • ${statusLabel(item.status_label)}</div>
              <div style="font-size:.68rem; color:#0f766e; font-weight:900; margin-top:2px;">${item.relationship_label || ''} ${item.return_distance_label ? `• ${item.return_distance_label}` : ''}</div>
              <div style="font-size:.68rem; color:#ea580c; font-weight:850; margin-top:2px;">${item.timeline_label || ''}</div>
              ${(item.compliance_alerts || []).length ? `<div style="font-size:.68rem; color:#dc2626; font-weight:950; margin-top:2px;"><i class="fa-solid fa-shield-halved"></i> ${(item.compliance_alerts || []).length} ${lang === 'la' ? 'ແຈ້ງເຕືອນລົດ/ຄົນຂັບ' : 'cảnh báo xe/tài xế'}</div>` : ''}
              <div style="font-size:.68rem; color:${item.status_color}; font-weight:900; margin-top:2px;"><i class="fa-solid fa-arrow-up-right-from-square"></i> ${item.navigation.label}</div>
            </button>
          </div>
        `).join('') : `<div class="dispatch-lane-empty"><i class="fa-solid fa-circle-plus"></i><span>Chọn hoặc kéo DO vào xe này</span></div>`}
      </div>
    </div>
  `).join('') : `<div style="color:#64748b; text-align:center; padding:16px;">${lang === 'la' ? 'ຍັງບໍ່ມີຖ້ຽວໃດມີລົດ/ຄົນຂັບ ແລະ ໄລຍະເວລາພຽງພໍເພື່ອສະແດງເທິງ Gantt.' : (lang === 'en' ? 'No trips ready with assigned vehicle/driver and time window.' : 'Chưa có chuyến nào đủ xe/tài xế và khung giờ để lên Gantt.')}</div>`;
  if (dispatchCalendarView === 'week' && window.TmsCockpit.buildDispatchWeekPlanner) {
    const week = window.TmsCockpit.buildDispatchWeekPlanner(appState || {}, dispatchCalendarDate);
    lanesEl.innerHTML = renderDispatchWeekTimetable(week);
  } else {
    lanesEl.innerHTML = dayLanesHtml;
  }

  conflictsEl.innerHTML = [
    ...calendar.capacity_alerts.map(item => `<button type="button" class="dispatch-alert-row ${item.severity === 'critical' ? 'dispatch-alert-row--critical' : ''}" onclick="switchView('${item.navigation.view}')"><i class="fa-solid fa-gauge-high"></i><span>${item.message}</span></button>`),
    ...calendar.conflicts.map(item => `<button type="button" class="dispatch-alert-row" onclick="switchView('${item.navigation.view}')"><i class="fa-solid fa-triangle-exclamation"></i><span>${item.message}<small>${item.action_label}</small></span></button>`),
    ...calendar.unscheduled.slice(0, 5).map(item => `<div class="dispatch-alert-row"><i class="fa-solid fa-circle-info"></i><span><strong>${item.id}</strong>: ${escapeHtml(item.reason)}</span></div>`)
  ].join('') || `<div style="background:#ecfdf5; border:1px solid #bbf7d0; color:#047857; border-radius:10px; padding:10px; font-weight:800;"><i class="fa-solid fa-circle-check"></i> ${lang === 'la' ? 'ບໍ່ພົບຕາຕະລາງຊ້ອນກັນໃນກະດານປ່ອຍລົດ.' : (lang === 'en' ? 'No scheduling conflicts detected.' : 'Không phát hiện trùng lịch trong bảng điều phối.')}</div>`;

  // Dem ngoai le SAU khi khoi do da duoc ghi: the o dai so lieu doc tu chinh
  // DOM cua khoi ngoai le, nen ve nguoc thu tu thi no luon bao 0.
  const excEl = document.getElementById('dispatch-exc-count');
  if (excEl) {
    excEl.textContent = String(conflictsEl.querySelectorAll('.dispatch-alert-row').length);
  }

  if (detailSummaryEl && detailAlertsEl && window.TmsCockpit.buildDispatchCalendarDetail) {
    const targetOrderId = selectedDispatchCalendarOrderId || '';
    const detail = window.TmsCockpit.buildDispatchCalendarDetail(appState || {}, targetOrderId, dispatchCalendarDate);
    const order = detail.order;
    renderDispatchSuggestedActions(detail);
    if (pendingDispatchResourceChange.orderId) renderDispatchResourceChangePanel();
    // Khung tom tat cua man Dieu phoi do `dpv2VeTomTatDon()` lam chu, vi no
    // phai ra dung bon o `.sum` cua ban mau. Ghi de o day thi mot the
    // `.dispatch-detail-card` cua ban cu nhet vao trong luoi hai cot va bo cuc
    // vo — hai kieu trinh bay chong len nhau trong cung mot cho.
    if (typeof dpv2VeTomTatDon === 'function') {
      dpv2VeTomTatDon(order);
    } else detailSummaryEl.innerHTML = order ? `
      <div class="dispatch-detail-card">
        <div class="dispatch-detail-hero">
          <div>
            <strong class="dispatch-detail-code">${order.id}</strong>
            <div class="dispatch-detail-resource-line">${lang === 'la' ? 'ລົດ' : 'Xe'} ${order.vehicle_id || (lang === 'la' ? 'ຍັງບໍ່ໄດ້ກຳນົດ' : 'chưa gắn')} · ${lang === 'la' ? 'ຄົນຂັບ' : 'Tài xế'} ${order.driver_id || (lang === 'la' ? 'ຍັງບໍ່ໄດ້ກຳນົດ' : 'chưa gắn')}</div>
          </div>
          <span class="dispatch-detail-status">${statusLabel(order.status_label || '') || (lang === 'la' ? 'ຍັງບໍ່ຊັດເຈນ' : 'Chưa rõ trạng thái')}</span>
        </div>
        <div class="dispatch-detail-facts">
          <div class="dispatch-detail-fact"><span>${lang === 'la' ? 'ເລີ່ມ' : 'Bắt đầu'}</span><strong>${order.start_label || '-'}</strong></div>
          <div class="dispatch-detail-fact"><span>${lang === 'la' ? 'ສິ້ນສຸດ' : 'Kết thúc'}</span><strong>${order.end_label || '-'}</strong></div>
          <div class="dispatch-detail-fact"><span>${lang === 'la' ? 'ໄລຍະເວລາ' : 'Thời lượng'}</span><strong>${order.duration_hours || 0} ${lang === 'la' ? 'ຊົ່ວໂມງ' : 'giờ'}</strong></div>
          <div class="dispatch-detail-fact"><span>Lane</span><strong>${detail.related_lane.label || detail.related_lane.resource_id || '-'}</strong></div>
          <div class="dispatch-detail-fact"><span>${lang === 'la' ? 'DO - àº¥àº»àº”' : 'DO - xe'}</span><strong>${order.relationship_label || '-'}</strong></div>
          <div class="dispatch-detail-fact"><span>${lang === 'la' ? 'ລ້ຽວກັບ' : 'Quay đầu'}</span><strong>${order.return_distance_label || (lang === 'la' ? 'ບໍ່ມີ' : 'Chưa có')}</strong></div>
          <div class="dispatch-detail-fact"><span>${lang === 'la' ? 'ເງື່ອນໄຂ' : 'Điều kiện'}</span><strong>${(order.compliance_alerts || []).length ? `${order.compliance_alerts.length} ${lang === 'la' ? 'ແຈ້ງເຕືອນ' : 'cảnh báo'}` : (lang === 'la' ? 'ຜ່ານ' : 'Đạt')}</strong></div>
          <div class="dispatch-detail-fact"><span>${lang === 'la' ? 'ຂັ້ນຕໍ່ໄປ' : 'Tiếp theo'}</span><strong>${detail.next_action.label}</strong></div>
        </div>
      </div>
    ` : `
      <div style="background:#ffffff; border:1px dashed #bfdbfe; border-radius:12px; padding:14px; color:#64748b; text-align:center;">${lang === 'la' ? 'ຍັງບໍ່ໄດ້ເລືອກຖ້ຽວເທິງ Gantt. ກົດທີ່ແຖບຕາຕະລາງເພື່ອເບິ່ງລາຍລະອຽດ.' : detail.message}</div>
    `;
    if (!detail.kind) {
      const detailActionsEl = document.getElementById('dispatch-calendar-detail-actions');
      if (detailActionsEl) detailActionsEl.hidden = true;
      detailAlertsEl.hidden = true;
    } else {
      detailAlertsEl.hidden = false;
    }
    detailAlertsEl.innerHTML = !order ? '' : detail.alerts.length ? detail.alerts.map(alert => `
      <div style="background:${alert.severity === 'critical' ? '#fff1f2' : '#fff7ed'}; border:1px solid ${alert.severity === 'critical' ? '#fecaca' : '#fed7aa'}; color:${alert.severity === 'critical' ? '#b91c1c' : '#9a3412'}; border-radius:10px; padding:9px 10px; font-weight:850;">
        <i class="fa-solid fa-triangle-exclamation"></i> ${alert.message}
      </div>
    `).join('') : `<div class="dispatch-status-note"><i class="fa-solid fa-circle-check"></i><span>${lang === 'la' ? 'ຖ້ຽວລົດທີ່ເລືອກບໍ່ມີການແຈ້ງເຕືອນໃດໆ.' : (lang === 'en' ? 'Selected trip has no specific alerts.' : 'Chuyến đang chọn chưa có cảnh báo riêng.')}</span></div>`;
  }
  updateDispatchWorkflowSteps();
  switchDispatchWorkState(activeDispatchWorkState);
  if (dispatchDayWorkbenchState.open && detailEl) detailEl.hidden = false;
}

/* Bảy trình vẽ dưới đây đã được gỡ. Mỗi hàm vẽ vào một khối mà index.html
   KHÔNG có, nên `getElementById` trả về null và toàn bộ thân hàm rơi vào
   những nhánh `if (el)` không bao giờ đúng — không một người dùng nào chạm
   tới được:

     renderExecutionModeCockpit    execution-mode-primary, -guidance
     renderMasterSetupSidebar      tms-master-setup-checklist, -next-actions, -quick-links
     renderUiHealthChecklist       tms-ui-health-list, -progress   (0 nơi gọi)
     renderSlaKpiIssueDetail       sla-kpi-issue-detail            (cùng openSlaKpiIssue)
     renderDispatchCapacityBoard   dispatch-capacity-*             (0 nơi gọi)
     updateDispatchDayFleetFilter  dispatch-day-fleet-search       (0 nơi gọi)
     renderGPSTrackingWidget       gps-do, gps-vehicle, gps-driver, gps-dist

   Cách kiểm: xóa thử từng hàm rồi chạy cả bộ test — bảy hàm này không làm
   vỡ bài kiểm nào. Với renderDispatchCapacityBoard, dispatch-workbench-ui
   .test.js còn CẤM gọi nó (`assert.doesNotMatch`) — nó đã bị cố ý tháo từ
   trước.

   `renderDispatchWeekPlanner` lúc đầu có làm vỡ một bài kiểm, nên đợt đó nó
   được giữ lại. Tra kỹ hơn thì bài kiểm ấy chỉ dò xem vài chuỗi tên lớp CSS
   có xuất hiện ở đâu đó trong `index.html` cộng `app.js` hay không — nó
   không hề kiểm rằng trình vẽ đó chạy. Mà bản đang chạy là
   `renderDispatchWeekTimetable`; xem chú thích ngay trên hàm đó. */
function renderGpsEventTimeline() {
  if (!window.TmsCockpit || typeof document === 'undefined') return;
  const kpisEl = document.getElementById('gps-event-timeline-kpis');
  const listEl = document.getElementById('gps-event-timeline-list');
  const alertsEl = document.getElementById('gps-event-timeline-alerts');
  if (!kpisEl || !listEl || !alertsEl) return;
  // DO dang xem. Ba nhanh, theo do uu tien.
  //
  // Ban cu sai o CA HAI nhanh dau, nen no LUON roi xuong `delivery_orders[0]`
  // — mot DO tuy y, khong lien quan gi toi DO dang xem tren ban do:
  //
  //   · nhanh 1 doc `#tracking-search-do`, mot id KHONG TON TAI (o that la
  //     `#tracking-do-search`);
  //   · nhanh 2 so `order.status` voi chuoi tieng Anh 'In Transit', trong khi
  //     may chu tra ve tieng Viet ("Dang van chuyen").
  //
  // Nay so bang `canonical_status` — truong khong doi theo ngon ngu.
  const dangChay = order => {
    const key = String(order?.canonical_status || order?.status || '')
      .normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/gi, 'd')
      .toLowerCase().trim();
    return ['dispatched', 'in_transit', 'arrived', 'delivered',
      'dang van chuyen', 'da den noi', 'da giao'].includes(key.replace(/\s+/g, ' '));
  };
  const selectedDo = document.getElementById('tracking-do-search')?.value?.trim()
    || (appState.delivery_orders || []).find(dangChay)?.id
    || (appState.delivery_orders || [])[0]?.id
    || '';
  const timeline = window.TmsCockpit.buildGpsEventTimeline(appState || {}, selectedDo);

  kpisEl.innerHTML = Object.values(timeline.kpis).map(kpi => `
    <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:10px;">
      <div style="font-size:.72rem; color:#64748b; font-weight:800;">${kpi.label}</div>
      <div style="font-size:1.05rem; color:${kpi.status === 'missing' ? '#dc2626' : '#2563eb'}; font-weight:950; margin-top:3px;">${kpi.count ?? kpi.value}</div>
    </div>
  `).join('');

  listEl.innerHTML = timeline.events.length ? timeline.events.map((event, index) => `
    <div style="display:grid; grid-template-columns:36px minmax(0,1fr); gap:10px; align-items:start; background:#ffffff; border:1px solid ${event.severity === 'critical' ? '#fecaca' : event.severity === 'warning' ? '#fed7aa' : '#dbeafe'}; border-radius:12px; padding:10px;">
      <div style="width:32px; height:32px; border-radius:999px; background:${event.severity === 'critical' ? '#dc2626' : event.severity === 'warning' ? '#f59e0b' : '#2563eb'}; color:#ffffff; display:flex; align-items:center; justify-content:center; font-weight:900;">${index + 1}</div>
      <div>
        <div style="display:flex; justify-content:space-between; gap:8px;">
          <strong style="color:#0f172a;"><i class="fa-solid ${event.icon}" style="color:${event.severity === 'warning' ? '#f59e0b' : '#2563eb'};"></i> ${event.label}</strong>
          <span style="font-size:.72rem; color:#64748b; font-weight:800;">${event.source_label}</span>
        </div>
        <div style="font-size:.78rem; color:#475569; margin-top:4px;">${event.time_label} • ${event.location_text}</div>
        <div style="font-size:.72rem; color:#64748b; margin-top:3px;">${event.lat || event.lng ? `Tọa độ: ${event.lat || '--'}, ${event.lng || '--'}` : 'Chưa có tọa độ'}${event.speed_kmh ? ` • ${event.speed_kmh} km/h` : ''}</div>
      </div>
    </div>
  `).join('') : `
    <div style="background:#f8fafc; border:1px dashed #cbd5e1; color:#64748b; border-radius:12px; padding:16px; text-align:center;">Chưa có event GPS/POD cho DO ${timeline.order_id || 'đang chọn'}.</div>
  `;

  alertsEl.innerHTML = [
    ...timeline.alerts.map(alert => `
      <div style="background:${alert.severity === 'critical' ? '#fff1f2' : '#fff7ed'}; border:1px solid ${alert.severity === 'critical' ? '#fecaca' : '#fed7aa'}; color:${alert.severity === 'critical' ? '#b91c1c' : '#9a3412'}; border-radius:12px; padding:10px; font-weight:800;">
        <i class="fa-solid fa-triangle-exclamation"></i> ${alert.message}
      </div>
    `),
    `<button class="fiori-btn fiori-btn-secondary" onclick="switchView('${timeline.next_action.navigation.view}')" style="justify-content:center;"><i class="fa-solid fa-arrow-right"></i> ${timeline.next_action.label}</button>`
  ].join('');
}

let summaryChartInstance = null;
let chartCRMInst = null;
let chartDOInst = null;
let chartVehInst = null;
let chartFinInst = null;

function renderSummaryChart() {
  // Chart.js đến từ CDN (cdn.jsdelivr.net). Hệ thống này chạy trên mạng nội
  // bộ, nơi CDN bị chặn là chuyện thường — và khi đó `new Chart(...)` ném
  // ReferenceError giữa hàm này. Hàm này nằm trong chuỗi khởi động của
  // `loadAllData`, nên một cái CDN không tới được sẽ làm ĐỨT cả bảng điều
  // khiển, không chỉ mất mấy cái biểu đồ.
  //
  // Nói ra một lần rồi vẽ tiếp phần còn lại. Thiếu biểu đồ thì màn hình vẫn
  // dùng được; đứt giữa thì không.
  if (typeof Chart === 'undefined') {
    if (!renderSummaryChart._daBao) {
      renderSummaryChart._daBao = true;
      baoNapThatBai('thư viện biểu đồ (Chart.js) từ CDN',
        new Error('Chart is not defined — kiểm tra kết nối ra cdn.jsdelivr.net'));
    }
    return;
  }
  // 1. Du lieu tong quan
  const qtCount = appState.quotations ? appState.quotations.length : 0;
  const doCount = appState.delivery_orders ? appState.delivery_orders.length : 0;
  const dispatchCount = appState.dispatches ? appState.dispatches.length : 0;
  const invoiceCount = appState.invoices ? appState.invoices.length : 0;
  const incidentCount = appState.incidents ? appState.incidents.length : 0;

  // 2. Ham tien ich de ve bieu do con (Doughnut)
  const drawDoughnut = (ctxId, instance, labels, data, colors) => {
    const ctx = document.getElementById(ctxId);
    if (!ctx) return instance;
    if (instance) instance.destroy();
    return new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: colors,
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 10 } } }
        }
      }
    });
  };

  // --- Ve Bieu do CRM (Bao Gia) ---
  const qts = appState.quotations || [];
  const qtApproved = qts.filter(q => q.status === 'Approved').length;
  const qtPending = qts.length - qtApproved;
  chartCRMInst = drawDoughnut('chartCRM', chartCRMInst, [t('chart_label_approved'), t('chart_label_pending')], [qtApproved, qtPending], ['#10b981', '#f59e0b']);

  // --- Ve Bieu do DO ---
  const dos = appState.delivery_orders || [];
  const doTransit = dos.filter(d => d.status === 'In Transit').length;
  const doPlanned = dos.length - doTransit;
  chartDOInst = drawDoughnut('chartDO', chartDOInst, [t('chart_label_delivering'), t('chart_label_planned')], [doTransit, doPlanned], ['#3b82f6', '#94a3b8']);

  // --- Ve Bieu do Xe (Vehicles) ---
  const vehs = appState.vehicles || [];
  const vehAvail = vehs.filter(v => v.status === 'Available').length;
  const vehBusy = vehs.length - vehAvail;
  chartVehInst = drawDoughnut('chartVehicles', chartVehInst, [t('chart_label_available'), t('chart_label_busy')], [vehAvail, vehBusy], ['#10b981', '#ef4444']);

  // --- Ve Bieu do Tai Chinh ---
  const invs = appState.invoices || [];
  const invPaid = invs.filter(i => i.status === 'Paid').length;
  const invUnpaid = invs.length - invPaid;
  chartFinInst = drawDoughnut('chartFinance', chartFinInst, [t('chart_label_paid'), t('chart_label_unpaid')], [invPaid, invUnpaid], ['#8b5cf6', '#f59e0b']);


  // --- Ve Bieu do Tong Quan Cuoi Cung (Pie Chart) ---
  const ctx = document.getElementById('summaryPieChart');
  if (ctx) {
    if (summaryChartInstance) summaryChartInstance.destroy();
    summaryChartInstance = new Chart(ctx, {
      type: 'pie',
      data: {
        labels: [t('chart_label_quotes'), t('chart_label_delivery_orders'), t('chart_label_dispatches'), t('chart_label_invoices'), t('chart_label_incidents')],
        datasets: [{
          data: [qtCount, doCount, dispatchCount, invoiceCount, incidentCount],
          backgroundColor: [
            '#3b82f6', // blue
            '#10b981', // emerald
            '#f59e0b', // amber
            '#8b5cf6', // purple
            '#ef4444'  // red
          ],
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right' }
        }
      }
    });
  }
}

function renderStats() {
  if (typeof loadDashboard === 'function') {
    loadDashboard();
    return;
  }
}
function quotationMarginLabel(quotation) {
  const cost = Number(quotation?.total_cost || 0);
  const selling = Number(quotation?.selling_price || 0);
  // Chưa có cước thu khách thì không có tỉ lệ nào cả. Hiện dấu gạch chứ không
  // phải 0%, vì 0% nghĩa là bán đúng bằng giá thành.
  if (!(selling > 0)) return '—';
  return `${(((selling - cost) / selling) * 100).toFixed(1)}%`;
}
window.quotationMarginLabel = quotationMarginLabel;

// Interactive Form Submissions
async function submitQuotationForm(e) {
  e.preventDefault();
  const fieldValue = (...ids) => {
    for (const fieldId of ids) {
      const element = document.getElementById(fieldId);
      if (element && element.value !== undefined) return element.value;
    }
    return '';
  };
  const numberValue = (...ids) => {
    const value = parseFloat(String(fieldValue(...ids)).replace(/,/g, ''));
    return Number.isFinite(value) && value >= 0 ? value : 0;
  };
  const intValue = (...ids) => Math.max(0, parseInt(fieldValue(...ids), 10) || 0);
  const id = document.getElementById("modal-qt-id").value;
  const fuelCost = parseFloat(document.getElementById("modal-qt-fuel").value || 0);
  const driverCost = parseFloat(document.getElementById("modal-qt-driver").value || 0);
  const tollFee = parseFloat(document.getElementById("modal-qt-toll").value || 0);
  const warehouseCost = parseFloat(document.getElementById("qt-warehouse").value || 0);
  const payload = {
    customer_id: document.getElementById("modal-qt-customer").value,
    route_id: document.getElementById("modal-qt-route").value,
    cargo_type: document.getElementById("qt-cargo").value,
    valid_to: document.getElementById("qt-valid").value,
    fuel_cost: fuelCost,
    driver_cost: driverCost,
    toll_fee: tollFee,
    total_cost: fuelCost + driverCost + tollFee + warehouseCost,
    selling_price: parseWorkflowMoneyValue(document.getElementById("qt-lbl-selling-price").textContent),
    // Keep the legacy modal compatible with the real workflow contract. These
    // fields are optional for old markup but must be persisted when present.
    origin: fieldValue('modal-qt-origin', 'qt-origin'),
    destination: fieldValue('modal-qt-destination', 'qt-destination'),
    pickup_window_start: fieldValue('modal-qt-pickup-window-start', 'qt-pickup-window-start'),
    pickup_window_end: fieldValue('modal-qt-pickup-window-end', 'qt-pickup-window-end'),
    delivery_window_start: fieldValue('modal-qt-delivery-window-start', 'qt-delivery-window-start'),
    delivery_window_end: fieldValue('modal-qt-delivery-window-end', 'qt-delivery-window-end'),
    weight_kg: numberValue('modal-qt-weight', 'qt-weight-kg'),
    volume_m3: numberValue('modal-qt-volume', 'qt-volume-m3'),
    pallet_count: intValue('modal-qt-pallets', 'qt-pallet-count'),
    packaging_spec: fieldValue('modal-qt-packaging', 'qt-packaging-spec')
  };

  const url = id ? `${API_BASE}/api/quotations/${id}` : `${API_BASE}/api/quotations`;
  const method = id ? "PUT" : "POST";

  const viec = id ? `Cập nhật báo giá ${id}` : 'Tạo báo giá';
  let res;
  try {
    res = await fetch(url, {
      method: method,
      headers: { "Content-Type": "application/json", ...financeAuthHeaders() },
      body: JSON.stringify(payload)
    });
  } catch (e) {
    // Khong co try/catch thi mat mang la nem loi khong ai bat, va nguoi dung
    // chi thay form dung im.
    return baoMatKetNoi(viec, e);
  }

  // That bai thi giu modal MO. Truoc day khong co nhanh else, nen may chu tu
  // choi la khong co gi xay ra va khong mot thong bao nao.
  if (!res.ok) return baoLoiMayChu(res, viec);
  closeModal("modal-quotation");
  await loadAllData();
  showToast(id ? t('msg_quote_updated') : t('msg_quote_created'));
}

async function submitDOForm(e) {
  e.preventDefault();
  const id = document.getElementById("modal-do-id").value;
  if (!id) {
    // DO sinh tự động khi khách chấp nhận báo giá — không tạo tay (POST đã bỏ).
    showToast('Lệnh giao hàng sinh từ báo giá được chấp nhận, không tạo tay.');
    return;
  }
  const payload = {
    route_id: document.getElementById("modal-do-route").value,
    pickup_date: tripReturnIsoFromLocal(document.getElementById("do-pickup-date").value),
    delivery_date: tripReturnIsoFromLocal(document.getElementById("do-delivery-date").value),
    weight_kg: parseFloat(document.getElementById("do-weight").value || 0)
  };

  const url = id ? `${API_BASE}/api/delivery-orders/${id}` : `${API_BASE}/api/delivery-orders`;
  const method = id ? "PUT" : "POST";

  const viec = id ? `Cập nhật lệnh giao hàng ${id}` : 'Tạo lệnh giao hàng';
  let res;
  try {
    res = await fetch(url, {
      method: method,
      headers: { "Content-Type": "application/json", ...financeAuthHeaders() },
      body: JSON.stringify(payload)
    });
  } catch (e) {
    return baoMatKetNoi(viec, e);
  }

  if (!res.ok) return baoLoiMayChu(res, viec);
  closeModal("modal-do");
  await loadAllData();
  showToast(id ? t('msg_do_updated') : t('msg_do_created'));
}

async function submitIncidentForm(e) {
  e.preventDefault();
  const payload = {
    do_id: document.getElementById("inc-do").value,
    driver: document.getElementById("inc-driver").value,
    incident_type: document.getElementById("modal-inc-type").value,
    location: document.getElementById("modal-inc-location").value,
    description: document.getElementById("modal-inc-desc").value
  };

  let res;
  try {
    res = await fetch(`${API_BASE}/api/incidents`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
  } catch (e) {
    return baoMatKetNoi('Ghi nhận sự cố', e);
  }

  if (!res.ok) return baoLoiMayChu(res, 'Ghi nhận sự cố');
  closeModal("modal-incident");
  await loadAllData();
  showToast(t('msg_incident_reported'));
}

function createDOFromQuotation(qId) {
  const q = appState.quotations.find(x => x.id === qId);
  if (!q) return;

  // Switch to DO View
  const doMenu = document.querySelector('.mega-card[data-view="delivery-shipment"]');
  if (doMenu) doMenu.click();

  // Open DO Form
  openNewDO();

  // Auto Fill data
  document.getElementById('do-customer').value = q.customer;
  document.getElementById('do-route').value = q.route;
  document.getElementById('do-cargo').value = q.cargo_type;
}

async function deleteQuotation(qid) {
  if (confirm(t('msg_confirm_delete_quote').replace('{id}', qid))) {
    const res = await fetch(`${API_BASE}/api/quotations/${qid}`, { method: "DELETE" });
    if (res.ok) await loadAllData();
  }
}

async function deleteDO(doid) {
  if (confirm(t('msg_confirm_delete_do').replace('{id}', doid))) {
    const res = await fetch(`${API_BASE}/api/delivery-orders/${doid}`, { method: "DELETE" });
    if (res.ok) await loadAllData();
  }
}

// AI Gateway Integration (Gemini 2.5 Flash API)
async function sendChatMessage() {
  const input = document.getElementById("chat-input");
  const prompt = input.value.trim();
  if (!prompt) return;

  input.value = "";
  appendUserMessage(prompt);

  // Intent badge removed

  try {
    const res = await fetch(`${API_BASE}/api/v1/ai/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: prompt })
    });

    if (res.ok) {
      const data = await res.json();
      const gatewayInfo = data.gateway_info;
      const respPayload = data.response;

      const isAction = gatewayInfo.detected_intent.includes("ACTION");
      const isDraft = respPayload.is_draft || false;
      const draftData = respPayload.draft_data || null;

      appendAIMessage(respPayload.reply, gatewayInfo.executing_agent, isAction, draftData);

      if (respPayload.mutation) {
        await loadAllData();
      }
    }
  } catch (err) {
    appendAIMessage("\u26a0\ufe0f L\u1ed7i k\u1ebft n\u1ed1i API Gateway Port 8006.", "Gateway Error", false, null);
  }
}

async function confirmDraft(draftDataStr) {
  // T\u00ean h\u00e0m gi\u1eef nguy\u00ean \u0111\u1ec3 kh\u00f4ng ph\u00e1 c\u00e1c ch\u1ed7 g\u1ecdi s\u1eb5n c\u00f3, nh\u01b0ng n\u00f3 KH\u00d4NG ghi d\u1eef
  // li\u1ec7u: tr\u1ee3 l\u00fd ch\u1ec9 tr\u1ea3 v\u1ec1 h\u01b0\u1edbng d\u1eabn thao t\u00e1c. Xem
  // backend/app/agents/action_agent.py::execute_draft.
  const draftData = JSON.parse(decodeURIComponent(draftDataStr));
  appendUserMessage("\ud83d\udccb Xem h\u01b0\u1edbng d\u1eabn thao t\u00e1c");

  try {
    const res = await fetch(`${API_BASE}/api/v1/ai/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: "CONFIRM", is_confirmed: true, draft_data: draftData })
    });

    if (res.ok) {
      const data = await res.json();
      const gatewayInfo = data.gateway_info;
      const respPayload = data.response;
      appendAIMessage(respPayload.reply, gatewayInfo.executing_agent, true, null);
      if (respPayload.mutation) {
        await loadAllData();
      }
    }
  } catch (err) {
    appendAIMessage("\u26a0\ufe0f L\u1ed7i k\u1ebft n\u1ed1i API Gateway Port 8006.", "Gateway Error", false, null);
  }
}

function cancelDraft() {
  appendUserMessage("\u274c H\u1ee7y b\u1ea3n nh\u00e1p");
  appendAIMessage("\u0110\u00e3 h\u1ee7y b\u1ea3n nh\u00e1p. B\u1ea1n c\u1ea7n t\u00f4i h\u1ed7 tr\u1ee3 nghi\u1ec7p v\u1ee5 g\u00ec kh\u00e1c kh\u00f4ng?", "Action Agent", true, null);
}

function sendQuickPrompt(promptText) {
  const drawer = document.getElementById("ai-drawer");
  drawer.classList.add("open");
  document.getElementById("chat-input").value = promptText;
  sendChatMessage();
}

function appendUserMessage(msg) {
  const history = document.getElementById("chat-history");
  const div = document.createElement("div");
  div.className = "chat-msg user";
  div.textContent = msg;
  history.appendChild(div);
  history.scrollTop = history.scrollHeight;
}

function formatMarkdownToHTML(text) {
  if (!text) return "";
  // Escape TRƯỚC khi áp dụng các quy tắc markdown. Kết quả của hàm này được
  // gán vào innerHTML, và đầu vào là phản hồi của mô hình ngôn ngữ — vốn đọc
  // lại dữ liệu nghiệp vụ như tên khách hàng hay ghi chú sự cố. Không escape
  // thì một cái tên chứa thẻ script sẽ chạy trong phiên của điều phối viên.
  // Thứ tự quan trọng: escape trước, rồi mới sinh ra <strong>/<li>/<br> của
  // chính chúng ta, nếu không chúng cũng bị escape luôn.
  let html = escapeHtml(text);

  // Convert Bold **text** -> <strong>text</strong>
  html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

  // Convert Bullet points - item -> <li>item</li>
  html = html.replace(/^-\s+(.*$)/gim, "<li>$1</li>");

  // Convert Newlines -> <br>
  html = html.replace(/\n/g, "<br>");

  return html;
}

function appendAIMessage(reply, agentName, isAction, draftData = null) {
  const history = document.getElementById("chat-history");
  const div = document.createElement("div");
  div.className = "chat-msg ai";

  const formattedHTML = formatMarkdownToHTML(reply);

  let draftHTML = "";
  if (draftData) {
    const encodedData = encodeURIComponent(JSON.stringify(draftData));

    // Translate action
    const actionMap = { 'create': 'T\u1ea1o m\u1edbi', 'update': 'C\u1eadp nh\u1eadt', 'delete': 'X\u00f3a b\u1ecf', 'none': 'Kh\u00f4ng x\u00e1c \u0111\u1ecbnh' };
    const viAction = actionMap[draftData.action] || draftData.action;

    // Translate entity
    const entityMap = { 'quotation': 'B\u00e1o gi\u00e1', 'delivery_order': 'L\u1ec7nh giao h\u00e0ng (DO)', 'incident': 'B\u00e1o c\u00e1o s\u1ef1 c\u1ed1' };
    const viEntity = entityMap[draftData.entity] || draftData.entity;

    draftHTML = `
      <div class="draft-card">
        <div class="draft-title">\u{1F4DD} Chi ti\u1ebft d\u1eef li\u1ec7u b\u00f3c t\u00e1ch:</div>
        <div style="margin-bottom:4px;"><strong>Thao t\u00e1c:</strong> <span class="badge badge-warning">${escapeHtml(viAction)}</span></div>
        <div style="margin-bottom:4px;"><strong>\u0110\u1ed1i t\u01b0\u1ee3ng:</strong> ${escapeHtml(viEntity)}</div>
        <div style="margin-bottom:4px;"><strong>Kh\u00e1ch h\u00e0ng:</strong> ${escapeHtml(draftData.customer || '-')}</div>
        <div style="margin-bottom:4px;"><strong>Tuy\u1ebfn \u0111\u01b0\u1eddng:</strong> ${escapeHtml(draftData.route || '-')}</div>
        <div style="margin-bottom:4px;"><strong>Lo\u1ea1i h\u00e0ng/S\u1ef1 c\u1ed1:</strong> ${escapeHtml(draftData.cargo_type || '-')}</div>
        <div class="draft-actions">
          <button class="btn btn-primary btn-sm" onclick="confirmDraft('${encodedData}')">\u{1F4CB} Xem h\u01b0\u1edbng d\u1eabn thao t\u00e1c</button>
          <button class="btn btn-danger btn-sm" onclick="cancelDraft()">\u274c H\u1ee7y b\u1ecf</button>
        </div>
      </div>
    `;
  }

  div.innerHTML = `
    <div style="margin-top:4px;">${formattedHTML}</div>
    ${draftHTML}
  `;

  history.appendChild(div);
  history.scrollTop = history.scrollHeight;
}

function switchTab(prefix, tabName) {
  const tabs = document.querySelectorAll(`#modal-${prefix} .erp-tab`);
  const contents = document.querySelectorAll(`#modal-${prefix} .erp-tab-content`);

  tabs.forEach(t => t.classList.remove('active'));
  contents.forEach(c => c.classList.remove('active'));

  // Logic map tabName to DOM elements based on prefix and onclick values
  const activeTab = Array.from(tabs).find(t => t.getAttribute('onclick').includes(`'${tabName}'`));
  if (activeTab) activeTab.classList.add('active');

  const contentEl = document.getElementById(`tab-${prefix}-${tabName}`);
  if (contentEl) contentEl.classList.add('active');
}

function toggleFormMode(formId, isView) {
  const form = document.getElementById(formId);
  if (!form) return;
  const inputs = form.querySelectorAll('input:not([type="hidden"]), select, textarea');
  inputs.forEach(el => {
    if (isView) {
      el.setAttribute('disabled', 'true');
    } else {
      if (el.id !== `${formId.split('-')[2]}-display-id` && !el.hasAttribute('readonly') || el.id === 'do-status') {
        el.removeAttribute('disabled');
      }
    }
  });
}

// ----------------- CRUD & ACTION LOGIC ----------------- //

// --- QUOTATIONS ---
function openNewQuotation() {
  document.getElementById("modal-qt-id").value = "";
  document.getElementById("form-create-quotation").reset();
  document.getElementById("modal-qt-subtitle").textContent = t("modal_quotation_new");
  document.getElementById("btn-qt-save").style.display = "block";
  document.getElementById("qt-margin").value = 15;
  document.getElementById("qt-lbl-total-cost").textContent = "0";
  document.getElementById("qt-lbl-selling-price").textContent = "0";
  toggleFormMode("form-create-quotation", false);
  document.getElementById("modal-quotation").style.display = "flex";
}

function viewQuotation(qid) {
  const q = appState.quotations.find(x => x.id === qid);
  if (!q) return;

  document.getElementById("modal-qt-id").value = q.id;
  document.getElementById("qt-display-id").value = q.id;
  document.getElementById("modal-qt-customer").value = q.customer || "";
  document.getElementById("modal-qt-route").value = q.route || "";
  document.getElementById("qt-cargo").value = q.cargo_type || "";
  document.getElementById("qt-valid").value = q.valid_to || "";
  document.getElementById("modal-qt-fuel").value = q.fuel_cost || 0;
  document.getElementById("modal-qt-driver").value = q.driver_cost || 0;
  document.getElementById("modal-qt-toll").value = q.toll_fee || 0;
  document.getElementById("qt-warehouse").value = q.warehouse_fee || 0;
  document.getElementById("qt-margin").value = q.margin_pct || 15;
  document.getElementById("qt-lbl-total-cost").textContent = (q.total_cost || 0).toLocaleString();
  document.getElementById("qt-lbl-selling-price").textContent = (q.selling_price || 0).toLocaleString();

  document.getElementById("modal-qt-subtitle").textContent = t("modal_quotation_view");
  document.getElementById("btn-qt-save").style.display = "none";

  toggleFormMode("form-create-quotation", true);
  document.getElementById("modal-quotation").style.display = "flex";
}

function editQuotation(qid) {
  const q = appState.quotations.find(x => x.id === qid);
  if (!q) return;

  document.getElementById("modal-qt-id").value = q.id;
  document.getElementById("qt-display-id").value = q.id;
  document.getElementById("modal-qt-customer").value = q.customer || "";
  document.getElementById("modal-qt-route").value = q.route || "";
  document.getElementById("qt-cargo").value = q.cargo_type || "";
  document.getElementById("qt-valid").value = q.valid_to || "";
  document.getElementById("modal-qt-fuel").value = q.fuel_cost || 0;
  document.getElementById("modal-qt-driver").value = q.driver_cost || 0;
  document.getElementById("modal-qt-toll").value = q.toll_fee || 0;
  document.getElementById("qt-warehouse").value = q.warehouse_fee || 0;
  document.getElementById("qt-margin").value = q.margin_pct || 15;
  document.getElementById("qt-lbl-total-cost").textContent = (q.total_cost || 0).toLocaleString();
  document.getElementById("qt-lbl-selling-price").textContent = (q.selling_price || 0).toLocaleString();

  document.getElementById("modal-qt-subtitle").textContent = t("modal_quotation_edit");
  document.getElementById("btn-qt-save").style.display = "block";

  toggleFormMode("form-create-quotation", false);
  document.getElementById("modal-quotation").style.display = "flex";
}

// approveQuotation defined below (full version with error handling)

// --- DELIVERY ORDERS ---
function openNewDO() {
  document.getElementById("modal-do-id").value = "";
  document.getElementById("form-create-do").reset();
  document.getElementById("modal-do-subtitle").textContent = t("modal_delivery_new");
  document.getElementById("btn-do-save").style.display = "block";
  toggleFormMode("form-create-do", false);
  switchTab("do", "cargo");
  document.getElementById("modal-do").style.display = "flex";
}

function viewDO(doid) {
  const d = appState.delivery_orders.find(x => x.id === doid);
  if (!d) return;

  document.getElementById("modal-do-id").value = d.id;
  document.getElementById("do-display-id").value = d.id;
  document.getElementById("modal-do-customer").value = d.customer || "";
  document.getElementById("modal-do-route").value = d.route || "";
  document.getElementById("do-vehicle").value = d.vehicle || "";
  document.getElementById("do-driver").value = d.driver || "";
  document.getElementById("do-pickup-date").value = d.pickup_date || "";
  document.getElementById("do-delivery-date").value = d.delivery_date || "";
  document.getElementById("do-cargo").value = d.cargo_desc || "";
  document.getElementById("do-weight").value = d.weight_kg || 0;
  document.getElementById("do-status").value = canonicalDOStatusValue(d);

  document.getElementById("modal-do-subtitle").textContent = t("modal_delivery_view");
  document.getElementById("btn-do-save").style.display = "none";

  toggleFormMode("form-create-do", true);
  switchTab("do", "cargo");
  document.getElementById("modal-do").style.display = "flex";
}

function editDO(doid) {
  const d = appState.delivery_orders.find(x => x.id === doid);
  if (!d) return;

  document.getElementById("modal-do-id").value = d.id;
  document.getElementById("do-display-id").value = d.id;
  document.getElementById("modal-do-customer").value = d.customer || "";
  document.getElementById("modal-do-route").value = d.route || "";
  document.getElementById("do-vehicle").value = d.vehicle || "";
  document.getElementById("do-driver").value = d.driver || "";
  document.getElementById("do-pickup-date").value = d.pickup_date || "";
  document.getElementById("do-delivery-date").value = d.delivery_date || "";
  document.getElementById("do-cargo").value = d.cargo_desc || "";
  document.getElementById("do-weight").value = d.weight_kg || 0;
  document.getElementById("do-status").value = canonicalDOStatusValue(d);

  document.getElementById("modal-do-subtitle").textContent = t("modal_delivery_edit");
  document.getElementById("btn-do-save").style.display = "block";

  toggleFormMode("form-create-do", false);
  switchTab("do", "cargo");
  document.getElementById("modal-do").style.display = "flex";
}

// --- INCIDENTS ---
function openNewIncident() {
  document.getElementById("inc-id").value = "";
  document.getElementById("form-create-incident").reset();
  document.getElementById("modal-inc-subtitle").textContent = t("modal_incident_new");
  document.getElementById("btn-inc-save").style.display = "block";
  document.getElementById("btn-inc-submit").style.display = "inline-block";
  toggleFormMode("form-create-incident", false);
  document.getElementById("modal-incident").style.display = "flex";
}

window.processAICheckin = async function (event) {
  const file = event.target.files[0];
  if (!file) return;

  const btn = document.getElementById("btn-ai-checkin");
  const logBox = document.getElementById("ai-system-log");
  const videoFeed = document.getElementById("ai-video-feed");
  const uploadedImg = document.getElementById("ai-uploaded-img");
  const truckBox = document.getElementById("ai-truck-box");
  const plateBox = document.getElementById("ai-plate-box");
  const scanLine = document.getElementById("ai-scan-line");
  const cropImg = document.getElementById("ai-crop-img");
  const cropPlaceholder = document.getElementById("ai-crop-placeholder");
  const ocrResult = document.getElementById("ai-ocr-result");

  // Reset UI
  truckBox.style.display = "none";
  plateBox.style.display = "none";
  cropImg.style.display = "none";
  cropPlaceholder.style.display = "block";
  ocrResult.value = "";
  btn.disabled = true;

  logBox.insertAdjacentHTML('beforeend', `> Uploading and analyzing...<br>`);

  // Show image preview
  const objectUrl = URL.createObjectURL(file);
  uploadedImg.src = objectUrl;
  uploadedImg.style.display = "block";
  videoFeed.style.display = "none";
  scanLine.style.display = "block";

  // Wait for image to load to get dimensions for bounding boxes
  await new Promise(resolve => { uploadedImg.onload = resolve; });

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch(`${API_BASE}/api/ai/checkpoint/scan`, {
      method: "POST",
      body: formData
    });

    scanLine.style.display = "none";

    if (!res.ok) {
      logBox.insertAdjacentHTML('beforeend', `> Error analyzing image.<br>`);
      return;
    }

    const data = await res.json();

    // Original dimensions needed for boxes
    const origW = uploadedImg.naturalWidth;
    const origH = uploadedImg.naturalHeight;

    if (data.vehicle_detected) {
      logBox.insertAdjacentHTML('beforeend', `> ${t('ai_log_botsort')}<br>`);
      const [x1, y1, x2, y2] = data.vehicle_bbox;
      truckBox.style.left = (x1 / origW * 100) + "%";
      truckBox.style.top = (y1 / origH * 100) + "%";
      truckBox.style.width = ((x2 - x1) / origW * 100) + "%";
      truckBox.style.height = ((y2 - y1) / origH * 100) + "%";
      truckBox.style.display = "block";
    }

    if (data.plate_detected) {
      logBox.insertAdjacentHTML('beforeend', `> ${t('ai_log_plate')}<br>`);
      const [px1, py1, px2, py2] = data.plate_bbox;
      plateBox.style.left = (px1 / origW * 100) + "%";
      plateBox.style.top = (py1 / origH * 100) + "%";
      plateBox.style.width = ((px2 - px1) / origW * 100) + "%";
      plateBox.style.height = ((py2 - py1) / origH * 100) + "%";
      plateBox.style.display = "block";

      if (data.cropped_plate_img) {
        cropPlaceholder.style.display = "none";
        cropImg.src = data.cropped_plate_img;
        cropImg.style.display = "block";
      }

      logBox.insertAdjacentHTML('beforeend', `> ${t('ai_log_ppocr')}<br>`);
      if (data.plate_text) {
        ocrResult.value = data.plate_text;
        logBox.insertAdjacentHTML('beforeend', `> ${t('ai_log_match')}<br>`);
        logBox.insertAdjacentHTML('beforeend', `<span style='color:green;font-weight:bold;'>> ${t('ai_log_valid')}</span><br>`);
        btn.disabled = false;
      }
    } else {
      logBox.insertAdjacentHTML('beforeend', `> No plate detected.<br>`);
    }
    logBox.scrollTop = logBox.scrollHeight;
  } catch (e) {
    logBox.insertAdjacentHTML('beforeend', `> API Error: ${e.message}<br>`);
    scanLine.style.display = "none";
  }
};

window.confirmAICheckin = async function () {
  const logBox = document.getElementById("ai-system-log");

  // Get the DO ID from the OCR result or dispatch context (do not hardcode)
  const ocrVal = document.getElementById('ocr-result')?.value || '';
  const doId = ocrVal || (appState.delivery_orders.find(d => d.status === 'In Transit' || d.status === 'Planned')?.id) || '';
  if (!doId) {
    showToast('⚠️ Không xác định được lệnh giao hàng để xác nhận qua trạm AI.');
    return;
  }
  const result = await executeWorkflowCommand('shipmentStep', {
    path: `/api/delivery-orders/${doId}/status`, method: 'PUT', body: { status: 'In Transit' }
  });
  if (result.ok) {
    logBox.insertAdjacentHTML('beforeend', `<span style='color:blue;font-weight:bold;'>> ${t('ai_log_barrier_opened')}</span><br>`);
    logBox.scrollTop = logBox.scrollHeight;
    // Gọi hàm vẽ THẬT. Trước đây gọi renderDashboardDeliveryOrders() — một hàm
    // chỉ tìm một tbody không tồn tại rồi thoát, nên thông báo "Đã mở barrier" hiện
    // ra mà không có gì trên màn đổi cả.
    if (typeof renderDeliveryOrders === 'function') renderDeliveryOrders(eplDeliveryOrders);
    showToast(`✅ ${t('msg_barrier_opened').replace('{id}', doId)}`);
  }
};

// ==========================================
// SAP FIORI MASTER DATA: VEHICLES
// ==========================================

let fioriVehicles = [];
let currentFioriVehMode = 'create';
let vehicleScheduleStartDate = '';
let vehicleScheduleRefreshTimer = null;
let currentVehicleMaintenanceRequests = [];

async function loadFioriVehicles() {
  try {
    const data = await fetchAllPaginated(`${API_BASE}/api/vehicles?paginated=true`, 200);
    fioriVehicles = data || [];
  } catch (error) {
    baoNapThatBai('danh sách phương tiện', error);
  }
  napBoLocDoiXe();
  veKpiDoiXe();
  filterFioriVehicles();
  if (typeof syncAllDynamicDropdowns === 'function') syncAllDynamicDropdowns();
  // Bang loai xe co cot "xe thuoc loai" doc tu doi xe — ve lai cho khop.
  if (document.getElementById('veh-types-tbody') && Array.isArray(vehTypes)) renderVehTypesTable(vehTypes);
}

/** Bộ lọc bãi và loại xe trên tab Đội xe — bãi đọc từ /api/depots, loại từ vehTypes. */
async function napBoLocDoiXe() {
  const selBai = document.getElementById('fleet-filter-depot');
  const selLoai = document.getElementById('fleet-filter-type');
  if (selBai) {
    try {
      const r = await fetch(`${API_BASE}/api/depots`, { headers: financeAuthHeaders() });
      if (r.ok) { const j = await r.json(); danhMucBai = Array.isArray(j) ? j : []; }
    } catch (e) { /* giu danh muc cu */ }
    if (!Array.isArray(danhMucBai)) danhMucBai = [];
    const cur = selBai.value;
    selBai.innerHTML = '<option value="">' + escapeHtml(nhanDich('opt_all_depots', 'Tất cả bãi')) + '</option>'
      + (danhMucBai || []).map(b => `<option value="${escapeHtml(b.name)}">${escapeHtml(b.name)} (${b.vehicle_count})</option>`).join('');
    // Xe mang ten bai KHONG co trong danh muc: van cho loc duoc.
    const la = [...new Set((fioriVehicles || []).map(v => String(v.depot_name || v.depot || '').trim()).filter(Boolean))]
      .filter(x => !(danhMucBai || []).some(b => b.name === x));
    la.forEach(x => selBai.insertAdjacentHTML('beforeend', `<option value="${escapeHtml(x)}">${escapeHtml(x)} · ngoài danh mục</option>`));
    if ([...selBai.options].some(o => o.value === cur)) selBai.value = cur;
  }
  if (selLoai) {
    const cur = selLoai.value;
    selLoai.innerHTML = '<option value="">' + escapeHtml(nhanDich('opt_all_types', 'Tất cả loại xe')) + '</option>'
      + (Array.isArray(vehTypes) ? vehTypes : []).map(vt => `<option value="${escapeHtml(vt.id)}">${escapeHtml(vt.name)}</option>`).join('');
    if ([...selLoai.options].some(o => o.value === cur)) selLoai.value = cur;
  }
}

/** Mở hộp thoại thêm bãi. Bãi là một địa điểm trong `locations`, không phải chuỗi trên xe. */
window.moThemBai = function () {
  const dlg = document.getElementById('depot-dialog');
  if (!dlg) return;
  ['depot-id', 'depot-name', 'depot-address'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
  if (typeof dlg.showModal === 'function') dlg.showModal(); else dlg.setAttribute('open', '');
  document.getElementById('depot-id')?.focus();
};

window.luuBaiMoi = async function () {
  const ma = String(document.getElementById('depot-id')?.value || '').trim().toUpperCase().replace(/\s+/g, '-');
  const ten = String(document.getElementById('depot-name')?.value || '').trim();
  const loai = document.getElementById('depot-type')?.value || 'Depot';
  const diaChi = String(document.getElementById('depot-address')?.value || '').trim();
  if (!ma || !ten) { showToast('Bãi cần cả mã (để lọc) và tên (để hiện).'); return; }
  try {
    const r = await fetch(`${API_BASE}/api/depots`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', ...financeAuthHeaders() },
      body: JSON.stringify({ id: ma, name: ten, type: loai, address: diaChi }),
    });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) { showToast(d?.detail?.message || d?.message || 'Không lưu được bãi.'); return; }
    showToast(d.message || `Đã thêm bãi ${ten}.`);
    document.getElementById('depot-dialog')?.close();
    await napBoLocDoiXe();
    const sel = document.getElementById('fleet-filter-depot');
    if (sel && [...sel.options].some(o => o.value === ten)) { sel.value = ten; filterFioriVehicles(); }
  } catch (e) {
    showToast('Không kết nối được backend để lưu bãi.');
  }
};

function nhanDich(khoa, macDinh) {
  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
  const g = (typeof appTranslations !== 'undefined' && appTranslations[khoa]) || null;
  return (g && (g[lang] || g.vi)) || macDinh;
}

/** Hạn pháp lý gần nhất của một xe (đăng kiểm / bảo hiểm): số ngày còn lại, hoặc null. */
function hanPhapLyXe(v) {
  const moc = [v.inspection_exp, v.insurance_date].map(x => Date.parse(x || '')).filter(x => !Number.isNaN(x));
  if (!moc.length) return null;
  return Math.floor((Math.min(...moc) - Date.now()) / 86400000);
}

let fleetKpiFilter = '';
/** Dải số liệu đội xe — mọi con số đếm từ mã trạng thái thật, bấm vào để lọc. */
function veKpiDoiXe() {
  const host = document.getElementById('fleet-kpi-strip');
  if (!host) return;
  const ds = fioriVehicles || [];
  const dem = { available: 0, on_trip: 0, maintenance: 0, out_of_service: 0 };
  let phapLy = 0;
  ds.forEach(v => {
    const k = String(v.operational_status || 'available');
    if (k in dem) dem[k] += 1;
    const ngay = hanPhapLyXe(v);
    if (ngay !== null && ngay < 30) phapLy += 1;
  });
  const the = [
    ['', 'kpi_fleet_total', ds.length, 'Tổng xe'],
    ['available', 'kpi_fleet_available', dem.available, 'Sẵn sàng'],
    ['on_trip', 'kpi_fleet_on_trip', dem.on_trip, 'Đang chạy'],
    ['maintenance', 'kpi_fleet_maintenance', dem.maintenance, 'Bảo dưỡng'],
    ['out_of_service', 'kpi_fleet_out', dem.out_of_service, 'Ngoài đội'],
    ['legal', 'kpi_fleet_legal_due', phapLy, 'Sắp hết hạn pháp lý'],
  ];
  host.innerHTML = the.map(([k, khoa, n, mac]) =>
    `<button type="button" class="fleet-kpi k-${k || 'total'}${fleetKpiFilter === k && k ? ' on' : ''}" onclick="locKpiDoiXe('${k}')"><span>${escapeHtml(nhanDich(khoa, mac))}</span><strong>${n}</strong></button>`).join('');
  const seg = document.getElementById('fleet-seg-fleet-count');
  if (seg) seg.textContent = String(ds.length);
}
window.locKpiDoiXe = function (k) {
  fleetKpiFilter = fleetKpiFilter === k ? '' : k;
  const sel = document.getElementById('fiori-filter-status');
  if (sel) sel.value = ['available', 'on_trip', 'maintenance', 'out_of_service'].includes(fleetKpiFilter) ? fleetKpiFilter : '';
  veKpiDoiXe();
  filterFioriVehicles();
};

/**
 * Nhãn trạng thái vận hành theo MÃ, đọc từ lang.json.
 *
 * Máy chủ trả `operational_status` là một mã chuẩn (available / on_trip /
 * maintenance / out_of_service cho xe; available / on_trip / off_duty /
 * inactive cho tài xế). Chữ hiện ra đi qua lang.json nên dịch được — trước
 * đây nhãn tiếng Việt ghi cứng từ máy chủ, bản tiếng Lào đọc ra tiếng Việt.
 */
function nhanTrangThaiVanHanh(loai, ma, ref) {
  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
  const khoa = (loai === 'drv' ? 'drv_status_' : 'veh_status_') + String(ma || 'available');
  const goi = (typeof appTranslations !== 'undefined' && appTranslations[khoa]) || null;
  const chu = (goi && (goi[lang] || goi.vi)) || String(ma || '');
  return ref && (ma === 'on_trip' || ma === 'maintenance') ? `${chu} · ${ref}` : chu;
}

/** Đặt tay trạng thái vận hành của một xe. */
window.datTrangThaiXe = async function (vehicleId, trangThai) {
  const ma = String(vehicleId || '').trim();
  if (!ma) return;
  let ghiChu = '';
  if (trangThai === 'out_of_service') {
    ghiChu = window.prompt('Đưa xe ' + ma + ' ra khỏi đội vì lý do gì?\n\n'
      + 'Xe sẽ không điều được cho tới khi đưa lại hoạt động.', '');
    if (ghiChu === null) return;
    if (!ghiChu.trim()) { showToast('Phải ghi lý do đưa xe ra khỏi đội.'); return; }
  }
  try {
    const tra = await fetch(`${API_BASE}/api/vehicles/${encodeURIComponent(ma)}/operational-status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...financeAuthHeaders() },
      body: JSON.stringify({ status: trangThai, note: ghiChu.trim() }),
    });
    const d = await tra.json().catch(() => ({}));
    if (!tra.ok) { showToast(d?.detail?.message || d?.message || 'Không cập nhật được trạng thái xe.'); return; }
    showToast(d.message || 'Đã cập nhật trạng thái xe.');
    if (typeof loadAllData === 'function') await loadAllData();
  } catch (e) {
    showToast('Không kết nối được backend để cập nhật trạng thái xe.');
  }
};

/** Đặt tay trạng thái của một nhân sự. */
window.datTrangThaiTaiXe = async function (driverId, trangThai) {
  const ma = String(driverId || '').trim();
  if (!ma) return;
  let ghiChu = '';
  if (trangThai === 'inactive') {
    ghiChu = window.prompt('Cho nhân sự ' + ma + ' nghỉ việc vì lý do gì?', '');
    if (ghiChu === null) return;
    if (!ghiChu.trim()) { showToast('Phải ghi lý do cho nhân sự nghỉ việc.'); return; }
  }
  try {
    const tra = await fetch(`${API_BASE}/api/drivers/${encodeURIComponent(ma)}/operational-status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...financeAuthHeaders() },
      body: JSON.stringify({ status: trangThai, note: ghiChu.trim() }),
    });
    const d = await tra.json().catch(() => ({}));
    if (!tra.ok) { showToast(d?.detail?.message || d?.message || 'Không cập nhật được trạng thái nhân sự.'); return; }
    showToast(d.message || 'Đã cập nhật trạng thái nhân sự.');
    if (typeof loadAllData === 'function') await loadAllData();
  } catch (e) {
    showToast('Không kết nối được backend để cập nhật trạng thái nhân sự.');
  }
};

/** Danh mục bãi / chi nhánh, đọc từ `GET /api/depots`, nạp vào ô chọn của hồ sơ xe. */
let danhMucBai = [];
async function napDanhMucBai(maDangChon, tenCu) {
  const sel = document.getElementById('fiori-veh-depot-code');
  if (!sel) return;
  try {
    const r = await fetch(`${API_BASE}/api/depots`, { headers: financeAuthHeaders() });
    if (r.ok) { const j = await r.json(); danhMucBai = Array.isArray(j) ? j : []; }
  } catch (e) { /* giu danh muc cu */ }
  const ds = Array.isArray(danhMucBai) ? danhMucBai : [];
  let html = '<option value="">-- Chưa gán bãi --</option>' + ds.map(b =>
    `<option value="${escapeHtml(b.id)}" data-name="${escapeHtml(b.name)}">${escapeHtml(b.name)} · ${escapeHtml(b.id)}</option>`).join('');
  // Xe cu mang mot ma bai KHONG co trong danh muc: van hien de nguoi dung thay
  // va sua, khong am tham xoa.
  if (maDangChon && !ds.some(b => String(b.id) === String(maDangChon))) {
    html += `<option value="${escapeHtml(maDangChon)}" data-name="${escapeHtml(tenCu || maDangChon)}">${escapeHtml(tenCu || maDangChon)} · ${escapeHtml(maDangChon)} (không có trong danh mục)</option>`;
  }
  sel.innerHTML = html;
  sel.value = maDangChon || '';
  const ten = document.getElementById('fiori-veh-depot');
  if (ten) ten.textContent = sel.value ? ((sel.options[sel.selectedIndex] || {}).dataset || {}).name || '' : '—';
  sel.onchange = () => {
    if (ten) ten.textContent = sel.value ? ((sel.options[sel.selectedIndex] || {}).dataset || {}).name || '' : '—';
  };
}

function renderFioriVehicles(data) {
  const tbody = document.getElementById('fiori-veh-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
  if (!data || data.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="fleet-empty">${escapeHtml(nhanDich('status_no_vehicles', 'Chưa có xe nào.'))}</td></tr>`;
    return;
  }
  data.forEach(v => {
    // TRANG THAI THEO MA (moc 045) — nhan tra tu lang.json, nut dat tay theo ma.
    const maTT = String(v.operational_status || 'available');
    const nhanTT = nhanTrangThaiVanHanh('veh', maTT, null);
    const nutTT = maTT === 'out_of_service'
      ? `<button class="fiori-btn fiori-btn-secondary btn-ico" title="${escapeHtml(nhanDich('btn_veh_back_in_service', 'Đưa lại hoạt động'))}${v.operational_note ? ' — ' + escapeHtml(v.operational_note) : ''}" onclick="datTrangThaiXe('${escapeHtml(v.id)}','available')"><i class="fa-solid fa-rotate-left"></i></button>`
      : (maTT === 'available'
        ? `<button class="fiori-btn fiori-btn-secondary btn-ico" title="${escapeHtml(nhanDich('btn_veh_out_of_service', 'Ngưng hoạt động'))}" onclick="datTrangThaiXe('${escapeHtml(v.id)}','out_of_service')"><i class="fa-solid fa-power-off"></i></button>`
        : '');

    // Loai xe: hien TEN; xe chua gan loai la mot VAN DE, khong phai mot o trong.
    const hasType = Boolean(String(v.vehicle_type_id || v.type || '').trim());
    const typeRow = (vehTypes || []).find(t => String(t.id) === String(v.vehicle_type_id || v.type)
      || String(t.name).toLowerCase() === String(v.type || '').toLowerCase());
    const typeText = v.vehicle_type_name || (typeRow && typeRow.name) || v.type || '';
    // Nang luc cua XE va cua LOAI la hai con so rieng; dieu phoi dung con so cua XE.
    const typeCap = Number(typeRow?.max_weight || 0);
    const vehCap = Number(v.weight_capacity || 0);
    const capacityWarning = (hasType && typeCap && vehCap && vehCap > typeCap)
      ? `<span class="fv-cap-warn" title="${escapeHtml(`Loại xe ${typeRow.name} chuẩn hóa ${typeCap.toLocaleString('vi-VN')} kg. Điều phối dùng con số của XE, nên xe này sẽ được xếp hàng nặng hơn chuẩn loại.`)}"><i class="fa-solid fa-triangle-exclamation" aria-hidden="true"></i> vượt chuẩn loại</span>`
      : '';

    // Han phap ly gan nhat: dang kiem / bao hiem.
    const ngay = hanPhapLyXe(v);
    let legal;
    if (ngay === null) legal = `<span class="fleet-legal l-none">${escapeHtml(nhanDich('legal_none', 'chưa khai'))}</span>`;
    else if (ngay < 0) legal = `<span class="fleet-legal l-expired">${escapeHtml(nhanDich('legal_expired', 'đã hết hạn'))}</span>`;
    else legal = `<span class="fleet-legal ${ngay < 30 ? 'l-soon' : 'l-ok'}">${escapeHtml(nhanDich('legal_days', 'còn {n} ngày').replace('{n}', String(ngay)))}</span>`;
    const legalPhu = [v.inspection_exp ? 'ĐK ' + escapeHtml(String(v.inspection_exp)) : '', v.insurance_date ? 'BH ' + escapeHtml(String(v.insurance_date)) : ''].filter(Boolean).join(' · ');

    // Anh 404 khong duoc hien alt text tran vao bang: onerror doi sang icon xe,
    // cung o kich voi xe khong co anh, nen moi hang can nhau.
    const fallbackIcon = '<span class="fleet-img-none"><i class="fa-solid fa-truck"></i></span>';
    const anh = v.image_url
      ? `<img class="fleet-img" src="${escapeHtml(v.image_url)}" alt="" loading="lazy" onerror="this.outerHTML=this.dataset.fallback" data-fallback="${escapeHtml(fallbackIcon)}">`
      : fallbackIcon;

    tbody.insertAdjacentHTML('beforeend', `
      <tr>
        <td>${anh}<span class="ma">${escapeHtml(v.id)}</span>${v.brand ? `<span class="phu" style="margin-left:54px">${escapeHtml(v.brand)}</span>` : ''}</td>
        <td>${hasType ? escapeHtml(typeText) : `<span class="fv-untyped"><i class="fa-solid fa-triangle-exclamation" aria-hidden="true"></i> ${escapeHtml(nhanDich('vt_untyped', 'Chưa gán loại xe'))}</span>`}</td>
        <td>${escapeHtml(v.depot_name || v.depot || '—')}${v.depot_code ? `<span class="phu">${escapeHtml(v.depot_code)}</span>` : ''}</td>
        <td><span class="ma" style="color:#2563eb">${vehCap.toLocaleString('vi-VN')} kg</span>${capacityWarning}<span class="phu">${Number(v.volume_capacity_m3 || 0)} m³ · ${Number(v.pallet_capacity || 0)} pallet</span></td>
        <td><span class="fleet-badge s-${maTT}">${escapeHtml(nhanTT)}</span>${v.operational_ref ? `<span class="phu">${escapeHtml(v.operational_ref)}</span>` : ''}</td>
        <td>${legal}${legalPhu ? `<span class="phu">${legalPhu}</span>` : ''}</td>
        <td class="act">
          ${nutTT}<button class="fiori-btn fiori-btn-secondary btn-ico" onclick="editFioriVehicle('${escapeHtml(v.id)}')" title="Sửa"><i class="fa-solid fa-pen"></i></button>
          <button class="fiori-btn btn-ico" style="background:#ef4444;border-color:#ef4444;" onclick="deleteFioriVehicle('${escapeHtml(v.id)}')" title="Xóa"><i class="fa-solid fa-trash"></i></button>
        </td>
      </tr>`);
  });
}

function filterFioriVehicles() {
  const query = (document.getElementById('fiori-search-veh')?.value || '').toLowerCase();
  const status = document.getElementById('fiori-filter-status')?.value || '';
  const bai = document.getElementById('fleet-filter-depot')?.value || '';
  const loai = document.getElementById('fleet-filter-type')?.value || '';
  const filtered = (fioriVehicles || []).filter(v => {
    const matchQuery = !query || v.id.toLowerCase().includes(query)
      || (v.vehicle_type_name || v.type || '').toLowerCase().includes(query)
      || (v.depot_name || v.depot || '').toLowerCase().includes(query);
    // Loc theo MA trang thai, khong so nhan.
    const matchStatus = !status || String(v.operational_status || 'available') === status;
    const matchBai = !bai || String(v.depot_name || v.depot || '') === bai;
    const matchLoai = !loai || String(v.vehicle_type_id || v.type || '') === loai;
    const ngay = hanPhapLyXe(v);
    const matchLegal = fleetKpiFilter !== 'legal' || (ngay !== null && ngay < 30);
    return matchQuery && matchStatus && matchBai && matchLoai && matchLegal;
  });
  renderFioriVehicles(filtered);
}
window.filterFioriVehicles = filterFioriVehicles;

/** Mở hộp thoại THÊM xe: xoá trắng mọi ô, mở khoá biển số, ảnh về ô trống. */
window.openFioriVehicleForm = function () {
  const modal = document.getElementById('fiori-object-page');
  if (modal) modal.style.display = 'flex';
  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
  const titleText = lang === 'la' ? 'ເພີ່ມພາຫະນະຂົນສົ່ງໃໝ່' : lang === 'en' ? 'Add New Vehicle' : 'Thêm Mới Phương Tiện';
  const tieuDe = document.getElementById('fiori-form-title');
  if (tieuDe) tieuDe.innerHTML = `<i class="fa-solid fa-truck" style="font-size: 1.3rem;"></i> <span>${titleText}</span>`;
  currentFioriVehMode = 'create';
  const dat = (id, gt) => { const el = document.getElementById(id); if (el) el.value = gt; };
  const idEl = document.getElementById('fiori-veh-id');
  if (idEl) { idEl.value = ''; idEl.disabled = false; }
  dat('fiori-veh-brand', '');
  dat('fiori-veh-type', '');
  dat('fiori-veh-weight', '');
  dat('fiori-veh-fuel', '');
  // Toc do: de trong, khong dien mot con so bia — may chu doi khai neu can.
  dat('fiori-veh-min-speed', '');
  dat('fiori-veh-max-speed', '');
  ['fiori-veh-maint', 'fiori-veh-engine', 'fiori-veh-chassis', 'fiori-veh-insur', 'fiori-veh-insp-date',
    'fiori-veh-insp-place', 'fiori-veh-insp-exp', 'fiori-veh-engine-cap', 'fiori-veh-dims'].forEach(id => dat(id, ''));
  const tt = document.getElementById('fiori-veh-status-text');
  if (tt) tt.textContent = nhanTrangThaiVanHanh('veh', 'available', null);
  napDanhMucBai('', '');
  setFioriVehicleImage('');
  if (typeof loadVehicleMaintenanceRequests === 'function') loadVehicleMaintenanceRequests('');
};

window.closeFioriVehicleForm = function () {
  const modal = document.getElementById('fiori-object-page');
  if (modal) modal.style.display = 'none';
  currentFioriVehMode = 'create';
};

window.editFioriVehicle = function (id) {
  const veh = fioriVehicles.find(v => v.id === id);
  if (!veh) return;

  openFioriVehicleForm();
  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
  const editTitleText = lang === 'la' ? `ແກ້ໄຂພາຫະນະ: ${veh.id}` : lang === 'en' ? `Edit Vehicle: ${veh.id}` : `Chỉnh Sửa Phương Tiện: ${veh.id}`;
  document.getElementById('fiori-form-title').innerHTML = `<i class="fa-solid fa-pen" style="font-size: 1.3rem;"></i> <span>${editTitleText}</span>`;
  currentFioriVehMode = 'edit';

  document.getElementById('fiori-veh-id').value = veh.id;
  document.getElementById('fiori-veh-id').disabled = true;
  if (document.getElementById('fiori-veh-brand')) document.getElementById('fiori-veh-brand').value = veh.brand || '';
  // Chon theo MA; xe cu con luu ten thi tra ma tu ten.
  {
    const maLoai = veh.vehicle_type_id
      || ((vehTypes || []).find(t => String(t.name).toLowerCase() === String(veh.type || '').toLowerCase()) || {}).id
      || veh.type || '';
    document.getElementById('fiori-veh-type').value = maLoai;
  }
  document.getElementById('fiori-veh-weight').value = veh.weight_capacity || 0;
  document.getElementById('fiori-veh-fuel').value = veh.fuel_norm || 0;
  if (document.getElementById('fiori-veh-min-speed')) document.getElementById('fiori-veh-min-speed').value = veh.min_speed_kmh || veh.min_speed || veh.speed_min || 35;
  if (document.getElementById('fiori-veh-max-speed')) document.getElementById('fiori-veh-max-speed').value = veh.max_speed_kmh || veh.max_speed || veh.speed_max || 80;
  if (document.getElementById('fiori-veh-status-text')) {
    document.getElementById('fiori-veh-status-text').textContent =
      nhanTrangThaiVanHanh('veh', veh.operational_status || 'available', veh.operational_ref);
  }
  document.getElementById('fiori-veh-maint').value = veh.maintenance_date || '';
  document.getElementById('fiori-veh-engine').value = veh.engine_no || '';
  document.getElementById('fiori-veh-chassis').value = veh.chassis_no || '';
  document.getElementById('fiori-veh-insur').value = veh.insurance_date || '';

  // New Inspection & Specs fields
  if (document.getElementById('fiori-veh-insp-date')) document.getElementById('fiori-veh-insp-date').value = veh.inspection_date || '';
  if (document.getElementById('fiori-veh-insp-place')) document.getElementById('fiori-veh-insp-place').value = veh.inspection_place || '';
  napDanhMucBai(veh.depot_code || '', veh.depot || '');
  if (document.getElementById('fiori-veh-insp-exp')) document.getElementById('fiori-veh-insp-exp').value = veh.inspection_exp || '';
  if (document.getElementById('fiori-veh-engine-cap')) document.getElementById('fiori-veh-engine-cap').value = veh.engine_cap || '';
  if (document.getElementById('fiori-veh-dims')) document.getElementById('fiori-veh-dims').value = veh.dimensions || '';
  setFioriVehicleImage(veh.image_url || '');
  loadVehicleMaintenanceRequests(veh.id);
}

function setFioriVehicleImage(imageUrl) {
  const hidden = document.getElementById('fiori-veh-image-url');
  const preview = document.getElementById('fiori-veh-image-preview');
  const wrap = document.getElementById('fiori-veh-image-preview-wrap');
  const placeholder = document.getElementById('fiori-veh-image-placeholder');
  const fileInput = document.getElementById('fiori-veh-image-file');

  if (hidden) hidden.value = imageUrl || '';
  if (preview) preview.src = imageUrl || '';
  if (wrap) wrap.style.display = imageUrl ? 'block' : 'none';
  if (placeholder) placeholder.style.display = imageUrl ? 'none' : 'grid';
  if (!imageUrl && fileInput) fileInput.value = '';
}

async function uploadMasterDataImage(file, entityType) {
  const formData = new FormData();
  formData.append('entity_type', entityType);
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/api/uploads/images`, {
    method: 'POST',
    body: formData
  });
  const result = await res.json().catch(() => ({}));
  if (!res.ok) {
    const message = result?.detail?.message || result?.message || 'Không tải được ảnh lên hệ thống.';
    throw new Error(message);
  }
  return result?.data?.url || '';
}

window.uploadMasterDataImage = uploadMasterDataImage;

window.previewFioriVehicleImage = async function (event) {
  const file = event?.target?.files?.[0];
  if (!file) {
    clearFioriVehicleImage();
    return;
  }

  if (!file.type.startsWith('image/')) {
    showToast('Vui lòng chọn đúng file ảnh phương tiện.');
    clearFioriVehicleImage();
    return;
  }

  if (file.size > 2 * 1024 * 1024) {
    showToast('Ảnh xe tối đa 2MB để lưu demo nhanh và nhẹ.');
    clearFioriVehicleImage();
    return;
  }

  try {
    showToast('Đang tải ảnh xe lên hệ thống...');
    const uploadedUrl = await uploadMasterDataImage(file, 'vehicles');
    setFioriVehicleImage(uploadedUrl);
    showToast('Đã tải ảnh xe lên. Bấm Lưu để ghi vào hồ sơ xe.');
  } catch (err) {
    clearFioriVehicleImage();
    showToast(err?.message || 'Không tải được ảnh xe, anh chọn ảnh khác giúp em nhé.');
  }
}

window.clearFioriVehicleImage = function () {
  setFioriVehicleImage('');
}

window.switchVehicleFormTab = function (tab, button) {
  document.querySelectorAll('#fiori-object-page .vehicle-form-pane').forEach(pane => {
    const active = pane.id === `vehicle-form-pane-${tab}`;
    pane.hidden = !active;
    pane.classList.toggle('active', active);
  });
  document.querySelectorAll('#fiori-object-page .vehicle-form-tabs button').forEach(item => item.classList.remove('active'));
  if (button) button.classList.add('active');
  if (tab === 'maintenance') {
    const vehicleId = document.getElementById('fiori-veh-id')?.value?.trim();
    if (vehicleId && currentFioriVehMode === 'edit') loadVehicleMaintenanceRequests(vehicleId);
  }
  if (tab === 'schedule') {
    const dateInput = document.getElementById('vehicle-schedule-date');
    if (dateInput && !dateInput.value) {
      const today = new Date();
      dateInput.value = new Date(today.getTime() - today.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
    }
    vehicleScheduleStartDate = dateInput?.value || vehicleScheduleStartDate;
    renderVehicleSchedule();
    if (!vehicleScheduleRefreshTimer) {
      vehicleScheduleRefreshTimer = setInterval(async () => {
        const pane = document.getElementById('vehicle-form-pane-schedule');
        if (pane && !pane.hidden) {
          await loadAllData();
          renderVehicleSchedule();
        }
      }, 30000);
    }
  } else if (vehicleScheduleRefreshTimer) {
    clearInterval(vehicleScheduleRefreshTimer);
    vehicleScheduleRefreshTimer = null;
  }
}

function vehicleScheduleDateLabel(value) {
  return new Date(`${value}T00:00:00`).toLocaleDateString('vi-VN', { weekday: 'short', day: '2-digit', month: '2-digit' });
}

function vehicleScheduleItemHtml(item) {
  const kind = item.kind === 'maintenance' ? 'maintenance' : 'busy';
  const title = item.kind === 'maintenance' ? 'Bảo dưỡng / sửa chữa' : (item.id || 'Trip');
  const detail = item.kind === 'maintenance'
    ? (item.description || 'Có lịch bảo dưỡng')
    : `${item.start_label || ''} - ${item.end_label || ''}`;
  return `<div class="vehicle-schedule-cell ${kind}"><strong>${escapeVehicleHtml(title)}</strong><small>${escapeVehicleHtml(detail)}</small></div>`;
}

window.renderVehicleSchedule = function () {
  const grid = document.getElementById('vehicle-schedule-grid');
  const vehicleId = document.getElementById('fiori-veh-id')?.value?.trim();
  if (!grid || !vehicleId || !window.TmsCockpit?.buildVehicleSchedule) return;
  const dateInput = document.getElementById('vehicle-schedule-date');
  const startDate = dateInput?.value || vehicleScheduleStartDate || FormatUtils.dateInputValue();
  vehicleScheduleStartDate = startDate;
  const schedule = window.TmsCockpit.buildVehicleSchedule(appState || {}, vehicleId, startDate);
  const vehicle = (appState.vehicles || fioriVehicles || []).find(item => String(item.id || item.vehicle_id || item.plate_no || '') === vehicleId) || {};
  const busy = (schedule.days || []).filter(day => ['busy', 'conflict'].includes(day.status)).length;
  const maintenance = (schedule.days || []).filter(day => day.status === 'maintenance').length;
  const available = Math.max(0, (schedule.days || []).length - busy - maintenance);
  const summary = document.getElementById('vehicle-schedule-summary');
  if (summary) summary.innerHTML = `<span class="busy">Có chuyến: ${busy} ngày</span><span class="maintenance">Bảo dưỡng: ${maintenance} ngày</span><span class="available">Rảnh: ${available} ngày</span><span>Loại xe: ${escapeVehicleHtml(vehicle.type || vehicle.vehicle_type || 'Chưa cấu hình')}</span>`;
  const range = document.getElementById('vehicle-schedule-range');
  if (range && schedule.days?.length) range.textContent = `${schedule.days[0].label} - ${schedule.days[schedule.days.length - 1].label}`;
  grid.innerHTML = (schedule.days || []).map(day => {
    const items = (day.items || []).map(vehicleScheduleItemHtml).join('');
    const fallback = day.status === 'maintenance' ? '<div class="vehicle-schedule-cell maintenance"><strong>Bảo dưỡng</strong><small>Xe không nhận chuyến</small></div>' : day.status === 'available' ? '<div class="vehicle-schedule-cell"><strong>Rảnh cả ngày</strong><small>Có thể xếp DO</small></div>' : '';
    return `<div class="vehicle-schedule-day"><strong>${escapeVehicleHtml(vehicleScheduleDateLabel(day.iso_date))}</strong>${items || fallback}</div>`;
  }).join('') || '<div class="vehicle-empty-state">Chưa có dữ liệu lịch cho xe này.</div>';
};

window.shiftVehicleSchedule = function (days) {
  const input = document.getElementById('vehicle-schedule-date');
  const current = new Date(`${input?.value || vehicleScheduleStartDate || FormatUtils.dateInputValue()}T00:00:00`);
  current.setDate(current.getDate() + Number(days || 0));
  const value = new Date(current.getTime() - current.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  if (input) input.value = value;
  vehicleScheduleStartDate = value;
  renderVehicleSchedule();
};

window.refreshVehicleSchedule = async function () {
  const button = document.getElementById('vehicle-schedule-refresh');
  if (button) button.disabled = true;
  try {
    await loadAllData();
    renderVehicleSchedule();
  } finally {
    if (button) button.disabled = false;
  }
};

function escapeVehicleHtml(value) {
  return escapeHtml(value);
}

function vehicleMaintenanceStatusLabel(status) {
  return ({
    requested: 'Chờ duyệt', approved: 'Đã duyệt', in_progress: 'Đang sửa',
    completed: 'Hoàn tất', cancelled: 'Đã hủy'
  })[status] || status;
}

// Uỷ quyền sang FormatUtils.formatMoney. Giữ tên cũ để không phải sửa hàng
// trăm chỗ gọi; bản gốc trùng với closeoutMoney và completionMoney.
function formatVehicleMoney(value, currency = 'VND') {
  return FormatUtils.formatMoney(value, currency);
}

async function loadVehicleMaintenanceRequests(vehicleId) {
  const list = document.getElementById('vehicle-maintenance-list');
  if (list) list.innerHTML = '<div class="vehicle-empty-state"><i class="fa-solid fa-spinner fa-spin"></i><span>Đang tải sổ sửa chữa...</span></div>';
  try {
    const response = await fetch(`${API_BASE}/api/vehicles/${encodeURIComponent(vehicleId)}/maintenance-requests`);
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result?.error?.message || result?.detail?.message || 'Không tải được sổ sửa chữa.');
    currentVehicleMaintenanceRequests = result.data || [];
    renderVehicleMaintenanceRequests();
  } catch (error) {
    currentVehicleMaintenanceRequests = [];
    if (list) list.innerHTML = `<div class="vehicle-empty-state"><i class="fa-solid fa-triangle-exclamation"></i><span>${escapeVehicleHtml(error.message)}</span></div>`;
  }
}

function renderVehicleMaintenanceRequests() {
  const list = document.getElementById('vehicle-maintenance-list');
  if (!list) return;
  if (!currentVehicleMaintenanceRequests.length) {
    list.innerHTML = '<div class="vehicle-empty-state"><i class="fa-solid fa-screwdriver-wrench"></i><strong>Chưa có phiếu sửa chữa</strong><span>Lập phiếu đầu tiên để lưu lịch sửa, nội dung và toàn bộ chi phí của xe.</span></div>';
    return;
  }
  list.innerHTML = currentVehicleMaintenanceRequests.map(item => {
    const start = item.planned_start ? new Date(item.planned_start).toLocaleString('vi-VN') : '-';
    const end = item.planned_end ? new Date(item.planned_end).toLocaleString('vi-VN') : '-';
    let actions = '';
    if (item.status === 'requested') actions = `<button class="fiori-btn" onclick="transitionVehicleMaintenance('${item.id}','approve',${item.version})">Duyệt</button>`;
    if (item.status === 'approved') actions = `<button class="fiori-btn" onclick="transitionVehicleMaintenance('${item.id}','start',${item.version})">Bắt đầu sửa</button>`;
    if (item.status === 'in_progress') actions = `<button class="fiori-btn" onclick="transitionVehicleMaintenance('${item.id}','complete',${item.version})">Hoàn tất</button>`;
    if (['requested', 'approved', 'in_progress'].includes(item.status)) actions += `<button class="fiori-btn fiori-btn-secondary" onclick="transitionVehicleMaintenance('${item.id}','cancel',${item.version})">Hủy phiếu</button>`;
    return `<article class="vehicle-maintenance-card">
      <div><h5>${escapeVehicleHtml(item.request_no)} · ${escapeVehicleHtml(item.description)}</h5><p>${start} → ${end} · ${escapeVehicleHtml(item.workshop || 'Chưa chọn xưởng')}</p></div>
      <div><span class="vehicle-status-chip ${escapeVehicleHtml(item.status)}">${vehicleMaintenanceStatusLabel(item.status)}</span><p style="margin-top:7px">Dự kiến: <strong>${formatVehicleMoney(item.estimated_total, item.currency_code)}</strong>${item.status === 'completed' ? `<br>Thực tế: <strong>${formatVehicleMoney(item.actual_total, item.currency_code)}</strong>` : ''}</p></div>
      <div class="vehicle-maintenance-card-actions">${actions}</div>
    </article>`;
  }).join('');
}

window.openVehicleMaintenanceRequestForm = function () {
  const vehicleId = document.getElementById('fiori-veh-id')?.value?.trim();
  if (!vehicleId || currentFioriVehMode !== 'edit') {
    showToast('Vui lòng lưu hồ sơ xe trước khi lập phiếu sửa chữa.');
    return;
  }
  const form = document.getElementById('vehicle-maintenance-request-form');
  form.reset();
  document.getElementById('vehicle-maintenance-cost-lines').innerHTML = '';
  addVehicleMaintenanceCostLine();
  form.hidden = false;
  form.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

window.closeVehicleMaintenanceRequestForm = function () {
  const form = document.getElementById('vehicle-maintenance-request-form');
  if (form) form.hidden = true;
}

window.addVehicleMaintenanceCostLine = function () {
  const container = document.getElementById('vehicle-maintenance-cost-lines');
  if (!container) return;
  const row = document.createElement('div');
  row.className = 'vehicle-maintenance-cost-line';
  row.innerHTML = `<label>Nội dung<input class="fiori-input maint-cost-description" placeholder="Phụ tùng, nhân công..." required></label>
    <label>Số lượng<input type="number" class="fiori-input maint-cost-quantity" min="0.01" step="0.01" value="1" required></label>
    <label>Đơn vị<input class="fiori-input maint-cost-unit" value="lần"></label>
    <label>Đơn giá dự kiến<input type="number" class="fiori-input maint-cost-price" min="0" step="1" value="0" required></label>
    <button type="button" class="fiori-btn fiori-btn-secondary" title="Xóa khoản phí" onclick="this.parentElement.remove()"><i class="fa-solid fa-trash"></i></button>`;
  container.appendChild(row);
}

window.saveVehicleMaintenanceRequest = async function (event) {
  event.preventDefault();
  const vehicleId = document.getElementById('fiori-veh-id').value.trim();
  const costLines = [...document.querySelectorAll('#vehicle-maintenance-cost-lines .vehicle-maintenance-cost-line')].map(row => ({
    category: 'other',
    description: row.querySelector('.maint-cost-description').value.trim(),
    quantity: Number(row.querySelector('.maint-cost-quantity').value || 1),
    unit: row.querySelector('.maint-cost-unit').value.trim() || 'lần',
    estimated_unit_cost: Number(row.querySelector('.maint-cost-price').value || 0)
  }));
  const startValue = document.getElementById('vehicle-maint-start').value;
  const endValue = document.getElementById('vehicle-maint-end').value;
  const payload = {
    request_no: document.getElementById('vehicle-maint-request-no').value.trim(),
    category: document.getElementById('vehicle-maint-category').value,
    priority: document.getElementById('vehicle-maint-priority').value,
    planned_start: startValue ? new Date(startValue).toISOString() : '',
    planned_end: endValue ? new Date(endValue).toISOString() : '',
    workshop: document.getElementById('vehicle-maint-workshop').value.trim(),
    description: document.getElementById('vehicle-maint-description').value.trim(),
    currency_code: 'VND',
    cost_lines: costLines
  };
  try {
    const response = await fetch(`${API_BASE}/api/vehicles/${encodeURIComponent(vehicleId)}/maintenance-requests`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result?.error?.message || result?.detail?.message || 'Không lưu được phiếu sửa chữa.');
    showToast('Đã lưu phiếu yêu cầu sửa chữa vào CSDL.');
    closeVehicleMaintenanceRequestForm();
    await loadVehicleMaintenanceRequests(vehicleId);
  } catch (error) {
    showToast(error.message);
  }
}

window.transitionVehicleMaintenance = async function (requestId, action, version) {
  const payload = { expected_version: version };
  if (action === 'cancel') {
    const reason = prompt('Nhập lý do hủy phiếu sửa chữa:');
    if (!reason) return;
    payload.reason = reason;
  }
  if (action === 'complete') {
    const nextDate = prompt('Ngày bảo dưỡng tiếp theo (YYYY-MM-DD), có thể để trống:') || '';
    payload.next_maintenance_date = nextDate;
    const item = currentVehicleMaintenanceRequests.find(row => row.id === requestId);
    const actualCostLines = [];
    for (const line of (item?.cost_lines || [])) {
      const entered = prompt(
        `Đơn giá thực tế - ${escapeHtml(line.description)} (${item.currency_code || 'VND'}):`,
        String(Number(line.estimated_unit_cost || 0))
      );
      if (entered === null) return;
      const actualUnitCost = Number(String(entered).replace(/[,\s]/g, ''));
      if (!Number.isFinite(actualUnitCost) || actualUnitCost < 0) {
        showToast(`Đơn giá thực tế của "${escapeHtml(line.description)}" không hợp lệ.`);
        return;
      }
      actualCostLines.push({ line_id: line.id, actual_unit_cost: actualUnitCost });
    }
    payload.actual_cost_lines = actualCostLines;
  }
  try {
    const response = await fetch(`${API_BASE}/api/vehicle-maintenance-requests/${encodeURIComponent(requestId)}/${action}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Idempotency-Key': `${action}-${requestId}-${version}` },
      body: JSON.stringify(payload)
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result?.error?.message || result?.detail?.message || 'Không cập nhật được phiếu sửa chữa.');
    showToast(`Đã cập nhật phiếu: ${vehicleMaintenanceStatusLabel(result.data.status)}.`);
    await loadVehicleMaintenanceRequests(document.getElementById('fiori-veh-id').value.trim());
    await loadFioriVehicles();
  } catch (error) {
    showToast(error.message);
  }
}

window.saveFioriVehicle = async function () {
  const id = document.getElementById('fiori-veh-id').value;
  if (!id) {
    showToast("Vui lòng nhập Biển Số Xe");
    return;
  }

  const payload = {
    id: id,
    brand: document.getElementById('fiori-veh-brand')?.value || '',
    type: document.getElementById('fiori-veh-type').value,
    weight_capacity: parseFloat(document.getElementById('fiori-veh-weight').value) || 0,
    fuel_norm: parseFloat(document.getElementById('fiori-veh-fuel').value) || 0,
    min_speed_kmh: parseFloat(document.getElementById('fiori-veh-min-speed')?.value) || 0,
    max_speed_kmh: parseFloat(document.getElementById('fiori-veh-max-speed')?.value) || 0,
    maintenance_date: document.getElementById('fiori-veh-maint').value,
    engine_no: document.getElementById('fiori-veh-engine').value,
    chassis_no: document.getElementById('fiori-veh-chassis').value,
    insurance_date: document.getElementById('fiori-veh-insur').value,
    inspection_date: document.getElementById('fiori-veh-insp-date')?.value || '',
    inspection_place: document.getElementById('fiori-veh-insp-place')?.value || '',
    // Ten bai lay theo ma da chon trong danh muc — khong go tay hai o lech nhau.
    depot_code: document.getElementById('fiori-veh-depot-code')?.value || '',
    depot: (function () {
      const sel = document.getElementById('fiori-veh-depot-code');
      const o = sel && sel.options[sel.selectedIndex];
      return (o && o.value) ? (o.dataset.name || o.textContent) : '';
    })(),
    inspection_exp: document.getElementById('fiori-veh-insp-exp')?.value || '',
    engine_cap: document.getElementById('fiori-veh-engine-cap')?.value || '',
    dimensions: document.getElementById('fiori-veh-dims')?.value || '',
    image_url: document.getElementById('fiori-veh-image-url')?.value || ''
  };

  try {
    const res = await fetch(`${API_BASE}/api/vehicles`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    // Máy chủ từ chối thì GIỮ FORM MỞ và nói rõ lý do. `result.detail` có thể
    // là một object (phong bì lỗi `{error:{code,message}}`), và nhét object
    // vào toast cho ra chữ "[object Object]" — baoLoiMayChu đọc đúng ba lớp.
    if (!res.ok) return baoLoiMayChu(res, 'Lưu phương tiện');
    showToast('Đã lưu phương tiện vào CSDL.');
    closeFioriVehicleForm();
    loadFioriVehicles();
  } catch (e) {
    // Mất mạng giữa chừng: trước đây chỗ này im hoàn toàn, người dùng bấm
    // "Lưu" rồi ngồi nhìn form không nhúc nhích, không biết đã lưu hay chưa.
    return baoMatKetNoi('Lưu phương tiện', e);
  }
}

window.deleteFioriVehicle = async function (id) {
  if (!confirm(`Sếp có chắc chắn muốn xóa phương tiện ${id} khỏi CSDL không?`)) return;
  try {
    const res = await fetch(`${API_BASE}/api/vehicles/${id}`, { method: 'DELETE' });
    if (!res.ok) return baoLoiMayChu(res, `Xóa phương tiện ${id}`);
    showToast("🗑️ Đã xóa phương tiện khỏi hệ thống!");
    loadFioriVehicles();
  } catch (e) {
    return baoMatKetNoi(`Xóa phương tiện ${id}`, e);
  }
}

// Ensure Fiori functions are globally accessible since they are called from onclick inline HTML
window.loadFioriVehicles = loadFioriVehicles;
// ==========================================
// VEHICLE TYPES (DANH MỤC LOẠI PHƯƠNG TIỆN - ENTERPRISE TABLE API CONNECTED)
// ==========================================

let vehTypes = [];

async function loadVehTypes() {
  try {
    const res = await fetch(`${API_BASE}/api/vehicle-types`);
    if (res.ok) {
      vehTypes = await res.json();
    } else {
      await baoLoiMayChu(res, 'Nạp danh mục loại xe');
    }
  } catch (err) {
    baoMatKetNoi('Nạp danh mục loại xe', err);
  }
  renderVehTypesTable(vehTypes);
  // Hai tab dung chung danh muc: them/xoa o day thi man Cong thuc gia thanh
  // phai theo kip, khong de nguoi dung thay hai con so khac nhau.
  if (typeof window.renderDynamicFormulaVehicleTypes === 'function') {
    window.renderDynamicFormulaVehicleTypes();
  }
}

function filterVehTypes() {
  const query = (document.getElementById('search-veh-types')?.value || '').toLowerCase();
  const filtered = (vehTypes || []).filter(vt =>
    (vt.id || '').toLowerCase().includes(query) ||
    (vt.name || '').toLowerCase().includes(query) ||
    (vt.fuel_type || vt.fuelType || '').toLowerCase().includes(query)
  );
  renderVehTypesTable(filtered);
}

function renderVehTypesTable(data) {
  const tbody = document.getElementById('veh-types-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
  const t = k => ((typeof appTranslations !== 'undefined' && appTranslations[k]) || {})[lang]
    || ((typeof appTranslations !== 'undefined' && appTranslations[k]) || {}).vi || k;
  const dem = document.getElementById('fleet-seg-types-count');
  if (dem) dem.textContent = String((Array.isArray(vehTypes) ? vehTypes : []).length);
  if (!data || data.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="fleet-empty">${t('status_no_vehicles')}</td></tr>`;
    syncAllDynamicDropdowns();
    return;
  }
  // So xe thuoc tung loai — doc tu doi xe that, khop theo MA hoac TEN (xe cu).
  const soXe = new Map();
  (fioriVehicles || []).forEach(v => {
    const k = String(v.vehicle_type_id || v.type || '').toLowerCase();
    if (k) soXe.set(k, (soXe.get(k) || 0) + 1);
  });
  data.forEach(vt => {
    const kg = Number(vt.max_weight || 0);
    const m3 = Number(vt.volume_capacity_m3 || 0);
    const pallet = Number(vt.pallet_capacity || 0);
    const n = (soXe.get(String(vt.id).toLowerCase()) || 0) + (soXe.get(String(vt.name || '').toLowerCase()) || 0);
    tbody.insertAdjacentHTML('beforeend', `
      <tr>
        <td><span class="ma">${escapeHtml(vt.name || '')}</span><span class="chip">${escapeHtml(vt.fuel_type || 'Diesel')}</span><span class="phu">${escapeHtml(vt.id)}${vt.dims ? ' · ' + escapeHtml(vt.dims) : ''}</span></td>
        <td><span class="ma">${(kg / 1000).toLocaleString('vi-VN', { maximumFractionDigits: 1 })} ${t('uom_ton')}</span><span class="phu">${kg.toLocaleString('vi-VN')} kg · ${m3} m³ · ${pallet} pallet</span></td>
        <td class="num">${Number(vt.fuel_norm || 0)}<small>L/100km</small></td>
        <td class="num">${vt.avg_speed_kmh ? Number(vt.avg_speed_kmh) + ' km/h' : '—'}</td>
        <td class="num">${Number(vt.maint_cost || 0).toLocaleString('vi-VN')} ₫</td>
        <td class="num">${n ? `<button type="button" class="fleet-count" onclick="locDoiXeTheoLoai('${escapeHtml(vt.id)}')" title="Xem các xe thuộc loại này"><i class="fa-solid fa-truck"></i> ${n} xe <i class="fa-solid fa-arrow-right"></i></button>` : '<span style="color:#94a3b8">0</span>'}</td>
        <td class="act">
          <button class="fiori-btn fiori-btn-secondary btn-ico" onclick="openVehTypeForm('${escapeHtml(vt.id)}')" title="Sửa"><i class="fa-solid fa-pen"></i></button>
          <button class="fiori-btn btn-ico" style="background:#ef4444;border-color:#ef4444;" onclick="deleteVehType('${escapeHtml(vt.id)}')" title="Xóa"><i class="fa-solid fa-trash"></i></button>
        </td>
      </tr>`);
  });
  syncAllDynamicDropdowns();
}

/** Bấm số xe ở bảng loại xe → sang tab Đội xe, đã lọc theo loại đó. */
window.locDoiXeTheoLoai = function (maLoai) {
  const nut = document.querySelector(".fleet-seg .vehicle-folder-tab[onclick*=\"'fleet'\"]");
  switchVehicleCatalogFolder('fleet', nut);
  setTimeout(() => {
    const sel = document.getElementById('fleet-filter-type');
    if (sel) { sel.value = maLoai; filterFioriVehicles(); }
  }, 150);
};

window.openVehTypeForm = function (id = null) {
  const panel = document.getElementById('veh-type-form-panel');
  if (panel) panel.style.display = 'flex';
  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';

  const editHeader = lang === 'la' ? '<i class="fa-solid fa-pen" style="font-size: 1.3rem;"></i> <span>ແກ້ໄຂ ປະເພດພາຫະນະ</span>' :
                     lang === 'en' ? '<i class="fa-solid fa-pen" style="font-size: 1.3rem;"></i> <span>Edit Vehicle Type</span>' :
                     '<i class="fa-solid fa-pen" style="font-size: 1.3rem;"></i> <span>Chỉnh Sửa Loại Phương Tiện</span>';

  const addHeader = lang === 'la' ? '<i class="fa-solid fa-plus-circle" style="color:#2563eb;"></i> <span>ເພີ່ມໃໝ່ ປະເພດພາຫະນະ</span>' :
                    lang === 'en' ? '<i class="fa-solid fa-plus-circle" style="color:#2563eb;"></i> <span>Add New Vehicle Type</span>' :
                    '<i class="fa-solid fa-plus-circle" style="color:#2563eb;"></i> <span>Thêm Loại Phương Tiện Mới</span>';

  if (id) {
    document.getElementById('veh-type-form-title').innerHTML = editHeader;
    const vt = vehTypes.find(v => v.id === id);
    if (vt) {
      document.getElementById('vt-edit-id').value = vt.id;
      document.getElementById('vt-id').value = vt.id;
      document.getElementById('vt-id').disabled = true;
      document.getElementById('vt-name').value = vt.name || '';
      document.getElementById('vt-max-weight').value = vt.max_weight || vt.maxWeight || 0;
      document.getElementById('vt-fuel-norm').value = vt.fuel_norm || vt.fuelNorm || 0;
      document.getElementById('vt-volume-capacity').value = vt.volume_capacity_m3 || vt.volumeCapacityM3 || 0;
      document.getElementById('vt-pallet-capacity').value = vt.pallet_capacity || vt.palletCapacity || 0;
      document.getElementById('vt-maint-cost').value = vt.maint_cost || vt.maintCost || 0;
      document.getElementById('vt-dims').value = vt.dims || '';
      document.getElementById('vt-fuel-type').value = vt.fuel_type || vt.fuelType || 'Diesel';
      document.getElementById('vt-special').value = vt.special || '';
      document.getElementById('vt-notes').value = vt.notes || '';
    }
  } else {
    document.getElementById('veh-type-form-title').innerHTML = addHeader;
    document.getElementById('vt-edit-id').value = '';
    document.getElementById('vt-id').value = '';
    document.getElementById('vt-id').disabled = false;
    document.getElementById('vt-name').value = '';
    document.getElementById('vt-max-weight').value = '';
    document.getElementById('vt-fuel-norm').value = '';
    document.getElementById('vt-volume-capacity').value = '';
    document.getElementById('vt-pallet-capacity').value = '';
    document.getElementById('vt-maint-cost').value = '';
    document.getElementById('vt-dims').value = '';
    document.getElementById('vt-fuel-type').value = 'Diesel';
    document.getElementById('vt-special').value = '';
    document.getElementById('vt-notes').value = '';
  }
}

window.closeVehTypeForm = function () {
  document.getElementById('veh-type-form-panel').style.display = 'none';
}

window.saveVehType = async function () {
  const id = document.getElementById('vt-id').value;
  const name = document.getElementById('vt-name').value;
  if (!id || !name) {
    showToast('Vui lòng nhập Mã và Tên Loại Phương Tiện!');
    return;
  }

  const payload = {
    id: id,
    name: name,
    maxWeight: Number(document.getElementById('vt-max-weight').value) || 0,
    volumeCapacityM3: Number(document.getElementById('vt-volume-capacity').value) || 0,
    palletCapacity: Number(document.getElementById('vt-pallet-capacity').value) || 0,
    fuelNorm: Number(document.getElementById('vt-fuel-norm').value) || 0,
    maintCost: Number(document.getElementById('vt-maint-cost').value) || 0,
    dims: document.getElementById('vt-dims').value,
    fuelType: document.getElementById('vt-fuel-type').value,
    special: document.getElementById('vt-special').value,
    notes: document.getElementById('vt-notes').value
  };

  try {
    const res = await fetch(`${API_BASE}/api/vehicle-types`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      showToast(`Đã lưu loại phương tiện ${id} vào CSDL!`);
      closeVehTypeForm();
      loadVehTypes();
    } else {
      showToast('Lỗi khi lưu loại phương tiện!');
    }
  } catch (err) {
    console.error(err);
    showToast('Lỗi kết nối CSDL!');
  }
}

window.deleteVehType = async function (id) {
  if (!confirm(`Bạn có chắc muốn xóa loại phương tiện ${id} khỏi CSDL?`)) return;
  try {
    const res = await fetch(`${API_BASE}/api/vehicle-types/${id}`, { method: 'DELETE' });
    if (!res.ok) return baoLoiMayChu(res, `Xóa loại phương tiện ${id}`);
    showToast(`Đã xóa loại phương tiện ${id}!`);
    loadVehTypes();
  } catch (err) {
    return baoMatKetNoi(`Xóa loại phương tiện ${id}`, err);
  }
}

window.loadVehTypes = loadVehTypes;
window.filterVehTypes = filterVehTypes;

// ==========================================
// QUOTATION — bảng oracle cũ (đang ẩn trong `#qtv2-khoi-cu`)
// ==========================================

// --- QUOTATION LOGIC ---
let crmQuotations = [];
window.loadQuotations = async function () {
  try {
    const data = await fetchAllPaginated(`${API_BASE}/api/quotations`, 200);
    if (data) {
      crmQuotations = data;
    } else {
      crmQuotations = [];
    }
  } catch (err) {
    console.error(err);
    crmQuotations = [];
  }
  renderOracleQTList(crmQuotations);
}

function renderOracleQTList(data) {
  const tbody = document.getElementById('oracle-qt-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
  if (!data || data.length === 0) {
    const emptyMsg = lang === 'la' ? 'ຍັງບໍ່ມີໃບສະເໜີລາຄາໃນຖານຂໍ້ມູນ. ກະລຸນາປ້ອນຂໍ້ມູນແລ້ວກົດບັນທຶກ.' : (lang === 'en' ? 'No quotations in database. Please enter details and save.' : 'Chưa có báo giá nào trong CSDL. Vui lòng nhập thông tin trong form và bấm Lưu.');
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:#888; padding:15px;"><i class="fa-solid fa-folder-open"></i> ${emptyMsg}</td></tr>`;
    return;
  }
  data.forEach(qt => {
    const presented = window.WorkflowPresentation?.presentRecord(qt) || qt;
    const demoBadge = presented.is_demo ? ` <span class="fiori-status fiori-status-pending">${lang === 'la' ? 'ຂໍ້ມູນທົດລອງ' : (lang === 'en' ? 'Demo Data' : 'Dữ liệu demo')}</span>` : '';
    const st = fixUIText(qt.status || 'Bản nháp');
    const actions = workflowActionMode(st, 'quotation');
    const statusKey = workflowStatusKeySafe(st);
    const isApproved = statusKey === 'approved' || statusKey === 'da_duyet';
    const badgeClass = isApproved ? 'fiori-status-approved' : 'fiori-status-pending';
    const editBtnText = lang === 'la' ? 'ແກ້ໄຂ' : (lang === 'en' ? 'Edit' : 'Sửa');
    const viewBtnTitle = lang === 'la' ? 'ເບິ່ງໃບສະເໜີລາຄາ' : (lang === 'en' ? 'View quotation' : 'Xem báo giá');
    const deleteBtnText = lang === 'la' ? 'ລຶບ' : (lang === 'en' ? 'Delete' : 'Xóa');
    const convertBtnText = lang === 'la' ? 'ປ່ຽນເປັນ SO' : (lang === 'en' ? 'Convert to SO' : 'Chuyển thành SO');

    const editOrViewButton = actions.canEdit
      ? `<button class="oracle-btn oracle-btn-secondary" style="padding: 4px 10px; font-size: 0.8rem; border: 1px solid #ccc; white-space: nowrap;" onclick="editOracleQT('${qt.id}')"><i class="fa-solid fa-pen-to-square"></i> ${editBtnText}</button>`
      : `<button class="oracle-btn oracle-btn-secondary" title="${viewBtnTitle}" aria-label="${viewBtnTitle}" style="width:36px; height:32px; padding:0; font-size:0.8rem; border:1px solid #ccc; white-space:nowrap; display:inline-flex; align-items:center; justify-content:center;" onclick="editOracleQT('${qt.id}')"><i class="fa-solid fa-eye"></i></button>`;
    const deleteButton = actions.canDelete
      ? `<button class="oracle-btn" style="padding: 4px 10px; font-size: 0.8rem; background: #ef4444; color: white; border: none; white-space: nowrap;" onclick="deleteOracleQT('${qt.id}')"><i class="fa-solid fa-trash"></i> ${deleteBtnText}</button>`
      : '';

    tbody.insertAdjacentHTML('beforeend', `
      <tr>
        <td><a href="#" onclick="editOracleQT('${qt.id}')" style="color:#005a9e; font-weight:bold; text-decoration:none;">${qt.id}</a>${demoBadge}</td>
        <td>${qt.customer_id || '—'}</td>
        <td>${qt.route_id || '—'}</td>
        <td>${qt.valid_to || '—'}</td>
        <td class="qt-price-cell">${(qt.selling_price || 0).toLocaleString('vi-VN')} VNĐ</td>
        <td class="qt-status-cell"><span class="fiori-status ${badgeClass}">${contextualWorkflowStatusLabel('quotation', st)}</span></td>
        <td class="qt-action-cell">
          <div>
            ${editOrViewButton}
            <button class="oracle-btn" style="padding: 4px 10px; font-size: 0.8rem; background: ${isApproved ? '#059669' : '#94a3b8'}; color: white; cursor: ${isApproved ? 'pointer' : 'not-allowed'}; border: none; white-space: nowrap;" ${isApproved ? `onclick="convertQTToSO('${qt.id}')"` : 'disabled aria-disabled="true"'}><i class="fa-solid fa-arrow-right-to-bracket"></i> ${convertBtnText}</button>
            ${deleteButton}
          </div>
        </td>
      </tr>
    `);
  });
}

function quotationSearchText(qt) {
  const st = fixUIText(qt.status || 'Bản nháp');
  const amount = Number(qt.selling_price || 0);
  return [
    qt.id,
    qt.customer_id,
    qt.route_id,
    qt.valid_to,
    qt.selling_price,
    amount.toLocaleString('vi-VN'),
    amount.toLocaleString('en-US'),
    statusLabel(st),
    contextualWorkflowStatusLabel('quotation', st)
  ].join(' ');
}

function filterQuotations() {
  const query = normalizeSearchText(document.getElementById('oracle-search-qt')?.value || '');
  const filtered = crmQuotations.filter(qt => normalizeSearchText(quotationSearchText(qt)).includes(query));
  renderOracleQTList(filtered);
}
window.filterQuotations = filterQuotations;

window.deleteOracleQT = async function (id) {
  const qt = (crmQuotations || []).find(q => q.id === id);
  if (qt && isWorkflowLocked(qt.status)) {
    showToast('Đơn hàng đã duyệt/xác nhận chỉ được xem, không được xóa.');
    return;
  }
  if (!confirm('Bạn có chắc chắn muốn xóa Đơn Hàng Vận Chuyển ' + id + '?')) return;
  try {
    const res = await fetch(API_BASE + '/api/quotations/' + id, { method: 'DELETE' });
    if (res.ok) {
      showToast('Đã xóa Báo Giá ' + id + ' thành công!');
      loadQuotations();
    } else {
      showToast('⚠ Lỗi khi xóa Đơn Hàng ' + id);
    }
  } catch (e) {
    console.error(e);
    showToast('Lỗi kết nối mạng khi xóa Đơn Hàng. Vui lòng thử lại.');
  }
};

window.openOracleQTForm = function () {
  const el = document.getElementById('oracle-qt-form');
  if (el) {
    el.style.display = 'flex';
  }
  setFormLoadingState('oracle-qt-form', true, 'Đang nạp danh mục...');
  ['qt-id', 'qt-valid-to', 'qt-fuel', 'qt-driver', 'qt-toll', 'qt-selling-price'].forEach(id => {
    const input = document.getElementById(id);
    if (input) input.value = '';
  });
  ['qt-customer', 'qt-route', 'qt-cargo-type'].forEach(id => {
    const select = document.getElementById(id);
    if (select) select.value = '';
  });
  if (document.getElementById('qt-currency')) document.getElementById('qt-currency').value = 'VND';
  document.querySelectorAll('#oracle-qt-form input, #oracle-qt-form select, #oracle-qt-form textarea').forEach(el => {
    if (el.type !== 'hidden') el.disabled = false;
  });
  const saveBtn = document.querySelector('#oracle-qt-form button[onclick="saveOracleQT()"]');
  if (saveBtn) saveBtn.style.display = 'inline-flex';
  const approveBtn = document.getElementById('btn-approve-qt');
  if (approveBtn) approveBtn.style.display = 'none';
  setRouteContextFields('qt', {});
  // Load fresh customer, route, vehicle-type data into dropdowns from CSDL
  if (typeof window.syncAllDynamicDropdowns === 'function') {
    window.syncAllDynamicDropdowns()
      .then(() => {
        // Auto-reset pricing grid after dropdowns are loaded
        if (typeof autoCalculateMasterDataCost === 'function') {
          autoCalculateMasterDataCost('qt');
        }
      })
      .catch(err => console.error(err))
      .finally(() => setFormLoadingState('oracle-qt-form', false));
  } else if (typeof autoCalculateMasterDataCost === 'function') {
    autoCalculateMasterDataCost('qt');
    setFormLoadingState('oracle-qt-form', false);
  } else {
    setFormLoadingState('oracle-qt-form', false);
  }
}
window.closeOracleQTForm = function () {
  setFormLoadingState('oracle-qt-form', false);
  const el = document.getElementById('oracle-qt-form');
  if (el) el.style.display = 'none';
};

window.calcQTTotal = function () {
  const f = workflowCostFieldVndValue('qt-fuel');
  const d = workflowCostFieldVndValue('qt-driver');
  const t = workflowCostFieldVndValue('qt-toll');
  const curr = document.getElementById('qt-currency')?.value || 'VND';
  setWorkflowTotalField('qt-selling-price', f + d + t, curr);
};

/* `legacySaveOracleQT` da duoc go.
   Ham nay tao bao gia bang mot duong RIENG, khong ai goi den — khong mot
   thuoc tinh onclick nao trong index.html, khong mot cho nao trong JS.
   No cung khong co nhanh `else`: may chu tu choi thi KHONG CO GI xay ra,
   khong mot thong bao nao, va `catch` thi chi console.error. Duong tao bao
   gia dang chay la `saveOracleQT`. */

window.editOracleQT = function (id) {
  openOracleQTForm();
  document.getElementById('qt-id').value = id;
  const qt = crmQuotations.find(q => q.id === id);
  if (qt) {
    const locked = isWorkflowLocked(qt.status);
    if (document.getElementById('qt-customer')) document.getElementById('qt-customer').value = qt.customer_id;
    if (document.getElementById('qt-route')) document.getElementById('qt-route').value = qt.route_id;
    if (document.getElementById('qt-cargo-type')) document.getElementById('qt-cargo-type').value = qt.cargo_type || '';
    if (document.getElementById('qt-valid-to')) document.getElementById('qt-valid-to').value = qt.valid_to || '';
    const curr = document.getElementById('qt-currency')?.value || 'VND';
    setWorkflowCostField('qt-fuel', qt.fuel_cost || 0, curr);
    setWorkflowCostField('qt-driver', qt.driver_cost || 0, curr);
    setWorkflowCostField('qt-toll', qt.toll_fee || 0, curr);
    setWorkflowTotalField('qt-selling-price', qt.selling_price || 0, curr);
    setRouteContextFields('qt', qt);

    document.querySelectorAll('#oracle-qt-form input, #oracle-qt-form select, #oracle-qt-form textarea').forEach(el => {
      if (el.type !== 'hidden') el.disabled = locked;
    });
    const saveBtn = document.querySelector('#oracle-qt-form button[onclick="saveOracleQT()"]');
    if (saveBtn) saveBtn.style.display = locked ? 'none' : 'inline-flex';

    const btnApprove = document.getElementById('btn-approve-qt');
    if (btnApprove) {
      const statusKey = window.WorkflowUIUtils?.workflowStatusKey?.(qt.status || '') || '';
      btnApprove.style.display = (!locked && (!statusKey || statusKey === 'draft')) ? 'inline-flex' : 'none';
    }
  }
}

window.legacyApproveQuotation = async function () {
  const id = document.getElementById('qt-id').value;
  if (!id) return;
  try {
    const res = await fetch(`${API_BASE}/api/quotations/${id}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'Approved' })
    });
    if (res.ok) {
      showToast(`✅ Đã duyệt Báo Giá ${id} thành công!`);
      closeOracleQTForm();
      loadQuotations();
    }
  } catch (e) { console.error(e); }
}

function normalizeSearchText(value) {
  return String(value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/Ä‘/g, 'd')
    .replace(/Đ/g, 'D')
    .toLowerCase();
}

function stabilizeModalContentHeight(formId) {
  const form = document.getElementById(formId);
  if (!form) return;
  const content = form.querySelector('.stable-modal-content');
  if (!content) return;
  content.style.minHeight = 'calc(94vh - 210px)';
}
window.stabilizeModalContentHeight = stabilizeModalContentHeight;

window.switchFormSecTab = function (contentId, tabBtn) {
  const parentSection = tabBtn.closest('.fiori-op-section, .master-form-card, .oracle-container');
  if (parentSection) {
    parentSection.querySelectorAll('.form-sec-content').forEach(el => el.style.display = 'none');
    parentSection.querySelectorAll('.form-sec-tab').forEach(btn => {
      btn.classList.remove('active');
      btn.style.color = '#666';
      btn.style.borderBottom = 'none';
      btn.style.fontWeight = 'normal';
    });
    const target = parentSection.querySelector('#' + contentId);
    if (target) target.style.display = 'block';
    tabBtn.classList.add('active');
    tabBtn.style.color = '#2563eb';
    tabBtn.style.borderBottom = '2px solid #2563eb';
    tabBtn.style.fontWeight = 'bold';
    const modal = parentSection.closest('.fiori-op-container');
    if (modal && modal.id) stabilizeModalContentHeight(modal.id);
  }
};

window.addRouteStop = function (containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const currentStops = container.querySelectorAll('.route-stop-item').length;
  const newIndex = currentStops + 1;
  const div = document.createElement('div');
  div.className = 'route-stop-item';
  div.innerHTML = `
    <span style="font-weight: bold; color: #555; width: 60px;">Điểm ${newIndex}:</span>
    <input type="text" placeholder="Ví dụ: Tên địa điểm" class="stop-input">
    <button type="button" class="btn" style="background:transparent; border:none; color: #d32f2f; cursor:pointer;" onclick="this.parentElement.remove()">
      <i class="fa-solid fa-trash"></i>
    </button>
  `;
  container.appendChild(div);
}

// ==========================================
// DELIVERY ORDER & OPERATIONS PLANNING
// ==========================================

let eplDeliveryOrders = [];
let eplRoutes = [];
let currentDOMode = 'create';
/**
 * Rổ đang mở. `null` nghĩa là CHƯA CHỌN — lần vẽ đầu tiên sẽ tự chọn rổ cấp
 * bách nhất mà có dòng.
 *
 * Trước đây mở cứng "Gần trễ", mà rổ đó đang có **0 DO**, nên mở màn ra là một
 * bảng trống trong khi 9 DO thật nằm ở các tab khác. Người dùng phải tự đoán là
 * phải bấm sang tab nào.
 */
let activeDOStage = null;
let deliveryOrderAnalysis = null;
/**
 * Các rổ, xếp theo MỨC CẤP BÁCH giảm dần.
 *
 * Sinh từ js/do-board.js thay vì viết cứng: thêm một rổ thì không phải sửa hai
 * chỗ, và không thể có rổ nào ở danh sách này mà thiếu ở bộ phân loại.
 */
const DELIVERY_ORDER_STAGES = window.DoBoard.BUCKETS.map(bucket => bucket.key);

function refreshDOFormControls() {
  const isView = currentDOMode === 'view';
  const closeBtn = document.getElementById('btn-close-do-form');
  if (closeBtn) closeBtn.textContent = 'Đóng';
  if (typeof refreshDOSettlementLineControls === 'function') refreshDOSettlementLineControls();
}

function doBoardEscape(value) {
  return escapeHtml(value);
}

function deliveryOrderStatusKey(order) {
  const raw = order?.canonical_status || order?.status || '';
  return window.WorkflowUIUtils?.workflowStatusKey?.(raw) || String(raw).toLowerCase().replace(/\s+/g, '_').trim();
}

function deliveryOrderAnalysisRecord(order) {
  const id = String(order?.id || '');
  return (deliveryOrderAnalysis?.records || []).find(record => String(record.id || '') === id) || null;
}

/**
 * Rổ của một DO.
 *
 * Máy chủ là bộ phân loại CHÍNH THỨC: nó biết số sự cố chưa xử lý và số POD,
 * những thứ trình duyệt không có. Chỉ khi gọi phân tích thất bại mới tự xếp, và
 * lúc đó dùng js/do-board.js — bản soi gương có cùng tên rổ và cùng thứ tự.
 *
 * Bản dự phòng trước đây tự viết lại phép xếp, và nó lấy `created_at` làm hạn
 * giao thay thế — tức **bịa ra một hạn không tồn tại**: ngày tạo phiếu không phải
 * ngày phải giao. Ba DO thật trong cơ sở dữ liệu không có ngày nào cả, nên chúng
 * bị xếp vào "gần trễ" theo ngày tạo phiếu.
 */
function deliveryOrderStage(order) {
  const analyzed = deliveryOrderAnalysisRecord(order);
  if (analyzed?.stage) return analyzed.stage;
  return window.DoBoard.bucketOf(order);
}

function deliveryOrderOperationalStatus(order) {
  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';

  // "Đã đến nơi" phải nói ra được, và nói TRƯỚC nhãn từ máy chủ.
  //
  // Máy chủ xếp `arrived` vào rổ `active` — đúng, vì xe vẫn đang trong
  // chuyến — nhưng nhãn của rổ đó là "Đang vận chuyển". Nên trước đây xe đã
  // tới bãi chờ bốc dỡ mà màn hình vẫn ghi đang chạy, và người điều hành
  // không phân biệt được hai việc rất khác nhau đó.
  //
  // Nhãn kèm luôn "chờ POD", vì đây đúng là mốc mà người ta hay tưởng đã
  // xong rồi đi chốt tiền — mà tiền chỉ chốt sau khi có chứng từ ký nhận.
  if (String(order?.canonical_status || '').toLowerCase() === 'arrived') {
    return {
      label: lang === 'la' ? 'ຮອດຈຸດຫມາຍແລ້ວ — ລໍຖ້າ POD'
        : (lang === 'en' ? 'Arrived — awaiting POD' : 'Đã đến nơi — chờ POD'),
      className: 'fiori-status-warning',
    };
  }

  const analyzed = deliveryOrderAnalysisRecord(order);
  if (analyzed?.operational_status) {
    const className = analyzed.stage === 'incident'
      ? 'fiori-status-danger'
      : analyzed.stage === 'cancelled'
        ? 'fiori-status-rejected'
        : analyzed.stage === 'near_late'
          ? 'fiori-status-warning'
          : analyzed.stage === 'completed' || analyzed.stage === 'active'
            ? 'fiori-status-approved'
            : 'fiori-status-pending';
    return { label: statusLabel(analyzed.operational_status), className };
  }
  const key = deliveryOrderStatusKey(order);
  const stage = deliveryOrderStage(order);
  if (stage === 'incident') {
    return { label: lang === 'la' ? 'ພົບບັນຫາ / ເກີດອຸບັດຕິເຫດ' : (lang === 'en' ? 'Incident' : 'Gặp sự cố'), className: 'fiori-status-danger' };
  }
  if (stage === 'cancelled') {
    return { label: lang === 'la' ? 'ຍົກເລີກແລ້ວ' : (lang === 'en' ? 'Cancelled' : 'Đã huỷ'), className: 'fiori-status-rejected' };
  }
  if (stage === 'completed') {
    return { label: lang === 'la' ? 'ສຳເລັດແລ້ວ' : (lang === 'en' ? 'Completed' : 'Hoàn thành'), className: 'fiori-status-approved' };
  }
  if (stage === 'active') {
    return { label: lang === 'la' ? 'ກຳລັງຂົນສົ່ງ' : (lang === 'en' ? 'In Transit' : 'Đang vận chuyển'), className: 'fiori-status-approved' };
  }
  if (stage === 'near_late') {
    return { label: lang === 'la' ? 'ໃກ້ຊັກຊ້າ' : (lang === 'en' ? 'Near Late' : 'Gần trễ'), className: 'fiori-status-warning' };
  }
  if (['approved', 'planned', 'pending', 'draft', 'unknown'].includes(key) || !key) {
    return { label: lang === 'la' ? 'ລໍຖ້າການຂົນສົ່ງ' : (lang === 'en' ? 'Pending Dispatch' : 'Chờ vận chuyển'), className: 'fiori-status-pending' };
  }
  return { label: statusLabel(order?.status || order?.canonical_status || ''), className: 'fiori-status-pending' };
}

function deliveryOrderDateValue(order, stage = activeDOStage) {
  const candidates = stage === 'completed'
    ? [order?.completed_at, order?.delivered_at, order?.pod_time, order?.delivery_date, order?.delivery_window_end, order?.updated_at]
    // CỐ Ý không có `created_at`: ngày tạo phiếu không phải ngày phải giao.
    // Lấy nó là bịa ra một hạn không tồn tại, rồi mọi con số "trễ" tính từ đó đều sai.
    : [order?.pickup_window_start, order?.pickup_date, order?.delivery_window_start, order?.delivery_date, order?.delivery_window_end];
  for (const candidate of candidates) {
    const time = Date.parse(candidate || '');
    if (!Number.isNaN(time)) return time;
  }
  return stage === 'completed' ? 0 : Number.MAX_SAFE_INTEGER;
}

function deliveryOrderDateLabel(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

function deliveryOrderSearchText(order) {
  return normalizeSearchText([
    order?.id,
    order?.quotation_id,
    order?.customer_id,
    order?.route_id,
    order?.origin,
    order?.destination,
    deliveryOrderAnalysisRecord(order)?.operational_status,
    statusLabel(order?.status || order?.canonical_status || '')
  ].join(' '));
}

async function loadDeliveryOrders() {
  try {
    eplDeliveryOrders = await fetchAllPaginated(`${API_BASE}/api/delivery-orders`);
    if (eplDeliveryOrders) {
      try {
        const resAnalysis = await fetch(`${API_BASE}/api/delivery-orders/analysis`);
        deliveryOrderAnalysis = resAnalysis.ok ? await resAnalysis.json() : null;
      } catch (analysisError) {
        console.warn('Delivery order analysis unavailable; falling back to local grouping', analysisError);
        deliveryOrderAnalysis = null;
      }
      renderDeliveryOrders(eplDeliveryOrders);
    }
    eplRoutes = await fetchAllPaginated(`${API_BASE}/api/routes?paginated=true`);
    renderRoutes(eplRoutes);
  } catch (error) {
    baoNapThatBai('dữ liệu vận hành (lệnh giao hàng, tuyến đường)', error);
  }
}

/* ==========================================================================
   Hủy lệnh giao hàng.

   Backend đã hỗ trợ đầy đủ từ lâu: `update_delivery_status` cho phép chuyển
   `pending -> cancelled`, và có chốt an toàn — còn chuyến vận tải đang hoạt
   động thì trả 409 kèm mã `ACTIVE_TRIP_EXISTS`. Nhưng giao diện KHÔNG có một
   đường nào để gọi nó: chữ `cancelled` chỉ xuất hiện trong các bộ lọc, tức
   màn hình NHẬN RA đơn đã hủy nhưng không HỦY được đơn nào.

   Hệ quả thực tế: khách hủy đơn thì người điều hành không ghi nhận được. Họ
   chỉ còn hai lựa chọn, và cả hai đều sai — để đơn nằm ở "Chờ vận chuyển"
   mãi (làm sai mọi con số đếm và mọi cảnh báo quá hạn), hoặc XÓA đơn đi
   (mất luôn lịch sử một việc đã thật sự xảy ra).

   Nút chỉ hiện ở đúng trạng thái backend cho phép hủy. Hiện nó ở trạng thái
   khác thì bấm vào chỉ nhận 409 — tức lại là một nút nói dối.
   ========================================================================== */

/** Trạng thái này có hủy được không — theo đúng bảng chuyển của backend. */
function huyDuocDon(do_item) {
  const tt = String(do_item?.canonical_status || '').toLowerCase();
  return tt === 'pending';
}

/* ==========================================================================
   Ghi mốc "xe đã đến nơi".

   Hệ thống có hai lớp trạng thái: chuyến hàng đi qua sáu mốc
   (`check_in` … `delivered`), còn DO chỉ có ba. Sự kiện `arrival` từ GPS
   chỉ đổi lớp chuyến hàng, nên trước đây DO vẫn là "Đang vận chuyển" và
   người điều hành không phân biệt được xe còn trên đường hay đã tới bãi
   chờ bốc dỡ.

   Đây là đường BẤM TAY, dùng khi thiết bị GPS mất tín hiệu — GPS tự báo
   vẫn là đường chính. Ghi mốc này KHÔNG mở quyết toán chi phí: tiền chỉ
   chốt sau khi có POD ký nhận.
   ========================================================================== */

window.ghiXeDaDenNoi = async function (id) {
  const don = (eplDeliveryOrders || []).find(d => String(d.id) === String(id));
  const tt = String(don?.canonical_status || '').toLowerCase();
  if (don && tt !== 'in_transit') {
    // Nói rõ vì sao, thay vì gửi lên rồi nhận một câu 409 chung chung.
    showToast(tt === 'arrived'
      ? `⚠️ Lệnh ${id} đã ghi mốc đến nơi rồi.`
      : '⚠️ Chỉ ghi mốc đến nơi cho lệnh đang vận chuyển.');
    return;
  }
  const XUONG_DONG = String.fromCharCode(10);
  if (!confirm(`Ghi nhận xe của lệnh ${id} đã đến điểm giao?`
    + XUONG_DONG + XUONG_DONG
    + 'Đây chỉ là mốc hành trình. Tiền vẫn CHƯA chốt được —'
    + ' phải nộp POD ký nhận trước.')) return;

  const viec = `Ghi mốc đến nơi cho lệnh ${id}`;
  let res;
  try {
    res = await fetch(`${API_BASE}/api/delivery-orders/${encodeURIComponent(id)}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'arrived' }),
    });
  } catch (e) {
    return baoMatKetNoi(viec, e);
  }
  if (!res.ok) return baoLoiMayChu(res, viec);
  showToast(`✅ Đã ghi mốc: lệnh ${id} đã đến nơi. Nộp POD để chốt tiền.`);
  if (typeof loadDeliveryOrders === 'function') loadDeliveryOrders();
};
/** Xóa hẳn một DO ĐÃ HỦY (chủ dự án: "đã hủy thì cho phép xóa"). Máy chủ chỉ cho xóa pending/cancelled. */
window.xoaLenhDaHuy = async function (id) {
  const don = (eplDeliveryOrders || []).find(d => String(d.id) === String(id));
  if (!don || String(don.canonical_status || '').toLowerCase() !== 'cancelled') {
    showToast('⚠️ Chỉ xóa được lệnh đã hủy.'); return;
  }
  if (!confirm(`Xóa hẳn lệnh ${id} khỏi danh sách?` + String.fromCharCode(10)
    + (don.cancel_reason ? `Lý do hủy đã ghi: ${don.cancel_reason}` + String.fromCharCode(10) : '')
    + 'Không khôi phục được; Audit Log vẫn giữ dấu vết.')) return;
  const viec = `Xóa lệnh ${id}`;
  let res;
  try {
    res = await fetch(`${API_BASE}/api/delivery-orders/${encodeURIComponent(id)}`, { method: 'DELETE', headers: financeAuthHeaders() });
  } catch (e) { return baoMatKetNoi(viec, e); }
  if (!res.ok) return baoLoiMayChu(res, viec);
  showToast(`🗑 Đã xóa lệnh ${id}.`);
  if (typeof loadDeliveryOrders === 'function') await loadDeliveryOrders();
};

window.huyLenhGiaoHang = async function (id) {
  const don = (eplDeliveryOrders || []).find(d => String(d.id) === String(id));
  if (don && !huyDuocDon(don)) {
    // Nói rõ vì sao, thay vì gửi lên rồi nhận một câu 409 chung chung.
    showToast('⚠️ Chỉ hủy được lệnh đang ở trạng thái chờ vận chuyển.'
      + ' Lệnh đã xuất bến thì xử lý ở màn Theo dõi hành trình.');
    return;
  }
  const XUONG_DONG = String.fromCharCode(10);
  // Máy chủ đòi lý do (422 CANCEL_REASON_REQUIRED) — hỏi ngay ở đây, một lần.
  const lyDo = window.prompt(`Hủy lệnh giao hàng ${id}?`
    + XUONG_DONG + 'Lệnh sẽ chuyển sang Đã hủy, không còn được điều xe; ghi vào Audit Log.'
    + XUONG_DONG + XUONG_DONG + 'Lý do hủy (bắt buộc):', '');
  if (lyDo === null) return;
  if (!lyDo.trim()) { showToast('⚠️ Hủy lệnh phải ghi lý do.'); return; }

  const viec = `Hủy lệnh giao hàng ${id}`;
  let res;
  try {
    res = await fetch(`${API_BASE}/api/delivery-orders/${encodeURIComponent(id)}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'cancelled', reason: lyDo.trim() })
    });
  } catch (e) {
    return baoMatKetNoi(viec, e);
  }
  // 409 ACTIVE_TRIP_EXISTS là câu trả lời CÓ ÍCH: còn chuyến đang chạy.
  // `baoLoiMayChu` đọc đúng ba lớp của phong bì lỗi nên lời của backend đến
  // được người dùng, thay vì một câu "Lỗi khi hủy" chung chung.
  if (!res.ok) return baoLoiMayChu(res, viec);
  showToast(`🚫 Đã hủy lệnh giao hàng ${id}.`);
  if (typeof loadDeliveryOrders === 'function') await loadDeliveryOrders();
};

/* ==========================================================================
   Lập kế hoạch giao hàng: chọn DO → xem tuyến → tạo Trip, không rời màn.

   Trước đây muốn lập một Trip thì phải rời màn này sang màn Điều phối rồi
   chọn lại đúng những DO vừa xem — mà màn này thì hai phần ba dưới để trống.

   Bốn chỗ bản thiết kế mẫu nói khác backend, ở đây làm theo BACKEND:

     1. `create_trip_from_delivery_orders` có `if len(route_ids) != 1 or None
        in route_ids: raise conflict("DELIVERY_ORDERS_INCOMPATIBLE")`. Tức các
        DO khác tuyến thì KHÔNG TẠO ĐƯỢC, chứ không phải "đi vòng thêm km" như
        mẫu ghi. Nên nút bị chặn hẳn kèm lý do thật.
     2. Chỉ DO `pending` được lập Trip (`DELIVERY_ORDER_NOT_PENDING`), nên ô
        tick của DO đang chạy / đã xong bị vô hiệu hóa.
     3. `planned_departure_at` và `avg_speed_kmh` (> 0) là BẮT BUỘC. Thiếu là
        422, nên phải có ô nhập chứ không đoán hộ.
     4. Endpoint này KHÔNG nhận vehicle_id/driver_id — điều xe là bước riêng.
        Nên ở đây không có ô chọn xe; nói rõ bước sau ở đâu.
   ========================================================================== */

/** Các DO đang được tick. Dùng Set để tick/bỏ tick không phải quét mảng. */
const doDaChon = new Set();

/**
 * Số dòng tối đa vẽ ra một lần.
 *
 * Quy mô thật là hàng nghìn đơn. Dựng hết vào một lần `innerHTML` là đúng lỗi
 * đã phải sửa ở màn lịch xe (500 xe → 1 MB HTML, 3.500 nút). Ba nhóm và ô
 * chọn tình trạng chính là bộ lọc; con số bị cắt được NÓI RA ở cuối bảng.
 */
const GIOI_HAN_DONG_DO = 100;

/* Ba nhóm của bản 3, gộp từ bảy rổ của `window.DoBoard.BUCKETS`.
   `need` = mọi thứ CHƯA chạy và cần người xử lý. `run` = đang trên đường.
   `completed` cố ý KHÔNG có nhóm riêng — nó tới qua ô chọn tình trạng hoặc
   nhóm "Tất cả", vì việc đã xong thì không phải việc cần làm. */
const NHOM_DO = {
  need: ['incident', 'overdue', 'undated', 'near_late', 'pending'],
  run: ['active'],
  done: ['completed'],
  cancelled: ['cancelled'],
  all: null,
};

let activeDOGroup = 'need';

/** Tình trạng chi tiết đang lọc, hoặc '' nếu không lọc. */
function rroDangLoc() {
  return String(document.getElementById('do-status-filter')?.value || '');
}

window.chonNhomDO = function (nhom) {
  activeDOGroup = NHOM_DO[nhom] !== undefined ? nhom : 'need';
  // Chọn nhóm thì bỏ lọc tình trạng chi tiết — hai bộ lọc cùng lúc dễ cho ra
  // bảng rỗng mà người dùng không hiểu vì sao.
  const oTT = document.getElementById('do-status-filter');
  if (oTT) oTT.value = '';
  activeDOStage = null;
  filterDeliveryOrders();
};

window.chonTrangThaiDO = function (stage) {
  activeDOStage = DELIVERY_ORDER_STAGES.includes(stage) ? stage : null;
  // Lọc theo một tình trạng cụ thể thì phải nhìn trên TẤT CẢ, không thì rổ
  // "Hoàn thành" chọn trong nhóm "Cần xử lý" sẽ luôn ra 0 dòng.
  if (activeDOStage) activeDOGroup = 'all';
  filterDeliveryOrders();
};

/** Bấm vào ô trạng thái trên một dòng thì lọc ngay theo tình trạng đó. */
window.locTheoOTrangThai = function (stage) {
  const oTT = document.getElementById('do-status-filter');
  if (oTT) oTT.value = String(stage || '');
  chonTrangThaiDO(stage);
};

window.boChonTatCaDO = function () {
  doDaChon.clear();
  document.querySelectorAll('#fiori-do-tbody input[data-do-id]').forEach(o => {
    o.checked = false;
    o.closest('tr')?.classList.remove('picked');
  });
  const oAll = document.getElementById('do-pick-all');
  if (oAll) oAll.checked = false;
  veThanhHanhDong();
};

/** Chỉ DO đang chờ vận chuyển mới lập Trip được — theo đúng luật backend. */
function doLapTripDuoc(do_item) {
  return String(do_item?.canonical_status || '').toLowerCase() === 'pending';
}

/**
 * DO có đủ bốn mốc thời gian mà backend đòi hay chưa.
 *
 * `create_trip_from_delivery_orders` có:
 *     if min(map(len, (pickup_starts, pickup_ends,
 *                      delivery_starts, delivery_ends))) != len(orders):
 *         raise DomainError("DELIVERY_TIME_WINDOW_REQUIRED", ...)
 *
 * Tức MỌI DO trong chuyến phải có CẢ BỐN mốc, không phải chỉ giờ giao. Kiểm ở
 * đây để nói trước, thay vì để người dùng tick, bấm, rồi nhận 422 — đúng cái
 * đã xảy ra khi tôi chạy thử luồng này lần đầu.
 */
function doDuKhungGio(do_item) {
  return Boolean(do_item?.pickup_window_start && do_item?.pickup_window_end
    && do_item?.delivery_window_start && do_item?.delivery_window_end);
}

/* Quãng đường và danh sách chặng dùng `routeSegments` và
   `routeSegmentDistanceKm` đã có sẵn trong tệp này (xem gần cuối tệp). Tôi đã
   viết hai hàm trùng lặp cho đúng việc đó rồi mới phát hiện chúng có sẵn — và
   bản có sẵn cũng đã xử lý đúng cả bốn tên khóa mà `segments_json` dùng trong
   dữ liệu thật (`distance_km`, `dist_km`, `distance`, `km`). Hai nguồn cho
   cùng một phép đọc là chỗ để chúng trôi khỏi nhau. */

/** Tra tuyến trong Dữ liệu gốc theo mã. */
function tuyenTheoMa(routeId) {
  if (!routeId) return null;
  return (eplRoutes || []).find(r => String(r.id) === String(routeId)) || null;
}

/**
 * Tuyến có lệch giữa `distance_km` và tổng các chặng hay không.
 *
 * Backend từ chối lập Trip khi hai con số này lệch quá 0,05 km
 * (`ROUTE_DISTANCE_MISMATCH`). Trong cơ sở dữ liệu thật đã từng có 2 trên 4
 * tuyến bị lệch — kể cả tuyến demo chính. Nói ra để người dùng biết TRƯỚC khi
 * tick DO và bấm, thay vì bấm rồi mới nhận 422.
 */
function lechQuangDuongTuyen(tuyen) {
  if (!tuyen) return null;
  const chang = routeSegments(tuyen);
  if (!chang.length) return null;
  const tongChang = chang.reduce((s, c) => s + routeSegmentDistanceKm(c), 0);
  const khaiBao = Number(tuyen.distance_km || 0);
  if (Math.abs(tongChang - khaiBao) < 0.05) return null;
  return { khaiBao, tongChang };
}

/** Mô tả hàng hóa từ các trường THẬT của lệnh giao hàng. */
function moTaHangHoa(do_item) {
  const phan = [];
  const kg = Number(do_item?.weight_kg || 0);
  const pallet = Number(do_item?.pallet_count || 0);
  const m3 = Number(do_item?.volume_m3 || 0);
  if (kg > 0) phan.push(`${kg.toLocaleString('vi-VN')} kg`);
  if (pallet > 0) phan.push(`${pallet} pallet`);
  // Hiện CẢ ba khi có cả ba: khối, số pallet và thể tích là ba con số khác
  // nhau, và xe chở được hay không phụ thuộc cả ba. Bỏ m³ chỉ vì đã có kg
  // là bỏ đúng con số quyết định với hàng nhẹ mà chiếm chỗ.
  if (m3 > 0) phan.push(`${m3.toLocaleString('vi-VN')} m³`);
  return { chinh: phan.join(' · ') || '—', phu: do_item?.packaging_spec || '' };
}

// Tham so thu ba la CHINH o vua bam. Ban truoc khong nhan no ma di do lai
// bang mot phep querySelector co thoat ky tu — mot vong ve quanh cai da
// nam trong tay, va keo them mot API cua trinh duyet chi de dung mot lan.
window.tickDO = function (id, tick, o) {
  if (tick) doDaChon.add(String(id));
  else doDaChon.delete(String(id));
  const dong = o && typeof o.closest === 'function' ? o.closest('tr') : null;
  if (dong) dong.classList.toggle('picked', Boolean(tick));
  veThanhHanhDong();
};

window.tickTatCaDO = function (tick) {
  document.querySelectorAll('#fiori-do-tbody input[data-do-id]').forEach(o => {
    if (o.disabled) return;
    o.checked = Boolean(tick);
    const ma = String(o.dataset.doId);
    if (tick) doDaChon.add(ma);
    else doDaChon.delete(ma);
    o.closest('tr')?.classList.toggle('picked', Boolean(tick));
  });
  veThanhHanhDong();
};

/**
 * Vẽ thanh hành động nổi theo các DO đang tick.
 *
 * Trả về `{ dsChon, chanLai, lyDo }` để `moHopThoaiTaoTrip` dùng lại đúng một phép
 * quyết định — hai nơi tự kiểm riêng là chỗ để chúng lệch nhau.
 */
function veThanhHanhDong() {
  const fab = document.getElementById('do-fab');
  const dsChon = (eplDeliveryOrders || []).filter(d => doDaChon.has(String(d.id)));

  if (fab) fab.hidden = dsChon.length === 0;
  const oN = document.getElementById('do-fab-n');
  if (oN) oN.textContent = String(dsChon.length);

  const maTuyen = [...new Set(dsChon.map(d => d.route_id || ''))];
  const thieuTuyen = maTuyen.includes('');
  const nhieuTuyen = maTuyen.length > 1;
  const thieuGio = dsChon.filter(d => !doDuKhungGio(d));
  const chuaPending = dsChon.filter(d => !doLapTripDuoc(d));
  const tuyen = nhieuTuyen || thieuTuyen ? null : tuyenTheoMa(maTuyen[0]);
  const lech = lechQuangDuongTuyen(tuyen);

  // Dòng thông tin: tuyến và tổng khối lượng.
  const oRoute = document.getElementById('do-fab-route');
  if (oRoute) {
    const tongKg = dsChon.reduce((s, d) => s + Number(d.weight_kg || 0), 0);
    const km = tuyen ? routeTotalDistanceKm(tuyen) : 0;
    oRoute.innerHTML = tuyen
      ? `Tuyến <b>${escapeHtml(tuyen.name || tuyen.id)}</b>`
        + ` · <b>${formatRouteKm(km)} km</b>`
        + (tongKg > 0 ? ` · <b>${tongKg.toLocaleString('vi-VN')} kg</b>` : '')
      : (nhieuTuyen
        ? `<b>${maTuyen.length} tuyến khác nhau</b>`
        : '<b>DO chưa gán tuyến</b>');
  }

  // Lý do chặn — lấy đúng theo luật backend, không đoán.
  let lyDo = '';
  if (chuaPending.length) {
    lyDo = `${chuaPending.length} DO không ở trạng thái chờ vận chuyển.`
      + ' Chỉ DO đang chờ mới lập Trip được.';
  } else if (thieuTuyen) {
    lyDo = 'Có DO chưa gán tuyến trong Dữ liệu gốc. Không có quãng đường thì'
      + ' máy chủ không tính được ETA và từ chối lập Trip.';
  } else if (nhieuTuyen) {
    lyDo = `Các DO này thuộc ${maTuyen.length} tuyến khác nhau`
      + ` (${maTuyen.map(x => x || '(chưa gán)').join(', ')}).`
      + ' Một Trip chỉ chở được các DO CÙNG MỘT tuyến — hãy tách ra và tạo'
      + ' từng Trip một.';
  } else if (thieuGio.length) {
    lyDo = `${thieuGio.length} DO chưa đủ khung giờ lấy và giao`
      + ` (${thieuGio.slice(0, 3).map(d => d.id).join(', ')}${thieuGio.length > 3 ? '…' : ''}).`
      + ' Máy chủ cần cả bốn mốc để tính ETA từng chặng.';
  } else if (lech) {
    lyDo = `Tuyến ${tuyen.id} khai ${formatRouteKm(lech.khaiBao)} km`
      + ` nhưng tổng các chặng là ${formatRouteKm(lech.tongChang)} km.`
      + ' Máy chủ từ chối lập Trip khi hai con số này lệch.';
  }

  const oWarn = document.getElementById('do-fab-warn');
  if (oWarn) {
    oWarn.hidden = !lyDo;
    oWarn.textContent = lyDo ? '⚠ ' + lyDo : '';
  }

  const chanLai = Boolean(lyDo);
  const nut = document.getElementById('do-fab-go');
  if (nut) nut.disabled = chanLai;
  const chu = document.getElementById('do-fab-go-text');
  if (chu) {
    // Nút không tự tạo Trip nữa mà mở form cấu hình, nên chữ phải nói đúng
    // việc nó làm — người dùng bấm "Tạo Trip" mà ra một form thì thấy lạ.
    chu.textContent = chanLai ? 'Chưa lập Trip được'
      : `Cấu hình & tạo Trip từ ${dsChon.length} DO`;
  }
  return { dsChon, chanLai, lyDo };
}
window.veThanhHanhDong = veThanhHanhDong;

/* ==========================================================================
   MỘT đường tạo Trip duy nhất.

   Trước đây màn này tự gửi lên `POST /api/tms/trips/from-delivery-orders`,
   nhưng chỉ gửi 5 trong 11 trường mà endpoint nhận. Hộp thoại "Tạo Trip vận
   chuyển từ DO/FO" ở màn Giao hàng & vận chuyển gọi CÙNG endpoint đó với đủ
   11 trường. Hai đường song song sinh ra đúng hai chỗ lệch có hậu quả thật:

     · `dwell_minutes` không gửi nên backend lấy 0 phút — ETA từng chặng BỎ
       LUÔN thời gian bốc dỡ, còn hộp thoại gửi 30 phút. Cùng một tuyến, hai
       đường ra hai ETA khác nhau.
     · `return_purpose` không gửi nên luôn là "none" — mọi Trip tạo từ đây
       đều tự sinh việc cho tab "Thiếu kế hoạch về".

   Nay thanh này chỉ làm việc nó giỏi: chọn DO và kiểm TRƯỚC năm chốt của
   backend, nói rõ lý do chặn ngay khi tick. Việc tạo Trip giao cho hộp thoại
   — nơi có đủ trường. Bỏ đường thứ hai thì hai chỗ lệch tự hết.
   ========================================================================== */

window.moHopThoaiTaoTrip = function () {
  // Hỏi lại chính hàm đã quyết định chặn/không chặn, thay vì kiểm song song
  // một lần nữa ở đây — hai phép kiểm là chỗ để nút bảo "được" mà lệnh gửi
  // lên bị từ chối.
  const { dsChon, chanLai, lyDo } = veThanhHanhDong();
  if (!dsChon.length) {
    showToast('⚠️ Chưa chọn DO nào để lập Trip.');
    return;
  }
  if (chanLai) {
    showToast('⚠️ ' + (lyDo || 'Chưa lập Trip được từ các DO đang chọn.'));
    return;
  }
  if (typeof openTripReturnAction !== 'function') {
    showToast('⚠️ Chưa nạp được form tạo Trip. Hãy tải lại trang.');
    return;
  }

  // Sang màn Giao hàng & vận chuyển rồi mở form, vì hộp thoại đọc dữ liệu
  // Trip của màn đó. Mở khi màn chưa nạp thì ô chọn DO rỗng.
  const dsMa = dsChon.map(d => String(d.id));
  switchView('delivery-shipment');
  setTimeout(() => {
    openTripReturnAction('create-trip', dsMa);
  }, 260);
};

// `capNhatDSDOChonTrongHopThoai` cũng chuyển sang js/do-picker.js.


/**
 * Vẽ ba con chip nhóm, nhãn ô chọn tình trạng, và dòng chân bảng.
 *
 * Nhãn ô chọn mang luôn số đếm của từng rổ, lấy từ `window.DoBoard.counts` —
 * nên con số trong ô chọn luôn khớp bảng, không phải một danh sách tĩnh.
 */
/**
 * Câu ghi chú theo rổ, lấy từ mấy con số MÁY CHỦ tính thêm.
 *
 * Ba con số dưới đây không nằm trong danh sách DO trả về — chỉ
 * `/api/delivery-orders/analysis` mới tính: bao nhiêu DO đã đến điểm mà
 * chưa ghi POD, bao nhiêu sự cố còn mở, bao nhiêu DO đã quá hạn. Bản 2
 * hiện chúng ở dòng chữ nhỏ dưới bảy thẻ đếm; bản 3 bỏ bảy thẻ đó, nên
 * nếu không dời sang đây thì giao diện mất luôn phần này — mà nó là phần
 * nói ra VIỆC CẦN LÀM, chứ không chỉ đếm dòng.
 */
function ghiChuRoDO() {
  const ro = (typeof deliveryOrderAnalysis !== 'undefined'
    && deliveryOrderAnalysis) ? deliveryOrderAnalysis.buckets : null;
  if (!ro) return '';
  const cau = [];
  if ((ro.incident && ro.incident.open_incidents) > 0) {
    cau.push(ro.incident.open_incidents + ' sự cố chưa xử lý');
  }
  if ((ro.active && ro.active.arrived) > 0) {
    cau.push(ro.active.arrived + ' DO đã đến điểm, cần cập nhật POD');
  }
  if ((ro.overdue && ro.overdue.count) > 0) {
    cau.push(ro.overdue.count + ' DO đã quá hạn');
  }
  return cau.join(' · ');
}
function veChipVaChanTrang(soDongHien) {
  const tong = (eplDeliveryOrders || []).length;
  const dem = {};
  DELIVERY_ORDER_STAGES.forEach(ro => { dem[ro] = 0; });
  (eplDeliveryOrders || []).forEach(d => {
    const ro = deliveryOrderStage(d);
    dem[ro] = (dem[ro] || 0) + 1;
  });

  const demNhom = {};
  Object.entries(NHOM_DO).forEach(([nhom, ds]) => {
    demNhom[nhom] = ds ? ds.reduce((s, ro) => s + (dem[ro] || 0), 0) : tong;
  });
  Object.entries(demNhom).forEach(([nhom, so]) => {
    const chip = document.getElementById(`do-group-${nhom}`);
    if (chip) chip.classList.toggle('active', nhom === activeDOGroup);
    const oSo = document.getElementById(`do-group-count-${nhom}`);
    if (oSo) oSo.textContent = String(so);
  });

  // Nhóm "Cần xử lý" chỉ có dấu đỏ khi thật sự còn việc.
  const dot = document.querySelector('#do-group-need .do-chip-dot');
  if (dot) dot.style.visibility = demNhom.need > 0 ? 'visible' : 'hidden';

  const oTT = document.getElementById('do-status-filter');
  if (oTT) {
    [...oTT.options].forEach(op => {
      if (!op.value) return;
      // Nhãn gốc = chữ ĐANG hiện, đã bóc phần đếm cũ. Lấy như vậy thì đổi
      // ngôn ngữ là ô chọn đổi theo, mà vẽ lại nhiều lần cũng không dồn
      // thành "Gần trễ (2) (2)".
      const nhan = op.textContent.replace(/\s*\(\d+\)$/, '');
      op.textContent = `${nhan} (${dem[op.value] || 0})`;
    });
  }

  const oDem = document.getElementById('do-plan-count');
  if (oDem) {
    const hien = Math.min(soDongHien, GIOI_HAN_DONG_DO);
    const nhanRo = activeDOStage
      ? (window.DoBoard?.BUCKETS || []).find(b => b.key === activeDOStage)?.label
      : ({ need: 'cần xử lý', run: 'đang chạy', done: 'hoàn thành', cancelled: 'đã huỷ', all: '' })[activeDOGroup];
    oDem.textContent = soDongHien
      ? `Đang xem ${hien}${soDongHien > hien ? ` trên ${soDongHien}` : ''} DO`
        + `${nhanRo ? ' ' + String(nhanRo).toLowerCase() : ''} · tổng ${tong} DO`
      : `Không có DO nào khớp bộ lọc này · tổng ${tong} DO`;
  }
  const oNote = document.getElementById('do-plan-note');
  if (oNote) {
    const soChon = doDaChon.size;
    // Đang tick thì nói việc đang làm; chưa tick thì ưu tiên VIỆC CẦN LÀM
    // từ máy chủ, hết việc mới xuống câu chỉ dẫn.
    const viec = ghiChuRoDO();
    oNote.textContent = soChon
      ? `${soChon} DO đã tick — xem thanh hành động ở dưới`
      : (viec
        ? viec
        : 'Tick ô vuông để gộp DO vào một Trip · bấm ô trạng thái để lọc nhanh');
  }

  const oTabDO = document.getElementById('do-subtab-count-delivery');
  if (oTabDO) oTabDO.textContent = String(tong);
  const oTabRT = document.getElementById('do-subtab-count-routes');
  if (oTabRT) oTabRT.textContent = String((eplRoutes || []).length);
}
window.veChipVaChanTrang = veChipVaChanTrang;

function renderDeliveryOrders(data) {
  const tbody = document.getElementById('fiori-do-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';

  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';

  // Chưa chọn rổ nào thì mở rổ CẤP BÁCH NHẤT MÀ CÓ DÒNG.
  //
  // Trước đây mở cứng "Gần trễ", mà rổ đó đang có 0 DO, nên mở màn ra là một
  // bảng trống trong khi 9 DO thật nằm ở các tab khác.
  // Bản 3 KHÔNG tự chọn rổ nữa. Bản 2 mở màn ra là nhảy vào rổ cấp bách
  // nhất mà có dòng, nên mỗi lần nạp lại người dùng thấy một rổ khác — khó
  // đoán. Nay mặc định là nhóm "Cần xử lý", và nó gộp cả năm rổ chưa chạy
  // nên không bao giờ rỗng oan.

  // Lọc theo NHÓM (ba con chip) hoặc theo TÌNH TRẠNG chi tiết (ô chọn).
  // Bản 2 chỉ có một tầng: đúng một trong bảy rổ. Bản 3 có hai tầng, và ô
  // chọn thắng khi có giá trị.
  const roCuaNhom = NHOM_DO[activeDOGroup] || null;
  const list = (data || [])
    .filter(order => {
      const ro = deliveryOrderStage(order);
      if (activeDOStage) return ro === activeDOStage;
      return !roCuaNhom || roCuaNhom.includes(ro);
    })
    .sort((a, b) => {
      const aDate = deliveryOrderDateValue(a, activeDOStage);
      const bDate = deliveryOrderDateValue(b, activeDOStage);
      // Rổ đã xong thì mới nhất lên đầu; còn lại thì gần hạn lên đầu.
      const roMoi = activeDOStage || (activeDOGroup === 'run' ? 'active' : 'pending');
      return roMoi === 'completed' ? bDate - aDate : aDate - bDate;
    });

  if (list.length === 0) {
    const emptyMap = {
      near_late: {
        vi: 'Không có DO gần trễ. Những DO sắp tới hạn hoặc quá hạn sẽ hiện ở đây.',
        en: 'No near-late DOs. Orders nearing deadline or overdue will appear here.',
        la: 'ບໍ່ມີ DO ໃກ້ຊັກຊ້າ. DO ທີ່ໃກ້ຮອດກຳນົດ ຫຼື ກາຍກຳນົດຈະສະແດງຢູ່ນີ້.'
      },
      pending: {
        vi: 'Chưa có DO chờ vận chuyển. Tạo DO từ đơn vận chuyển đã xác nhận để lập kế hoạch.',
        en: 'No pending DOs. Create DOs from confirmed Transport Orders to start planning.',
        la: 'ຍັງບໍ່ມີ DO ລໍຖ້າການຂົນສົ່ງ. ສ້າງ DO ຈາກໃບສັ່ງຂາຍທີ່ຢືນຢັນແລ້ວເພື່ອວາງແຜນ.'
      },
      active: {
        vi: 'Chưa có DO đang vận chuyển. Khi xe được điều phối, dữ liệu sẽ nằm ở đây.',
        en: 'No DOs in transit. Once trucks are dispatched, active DOs will appear here.',
        la: 'ຍັງບໍ່ມີ DO ກຳລັງຂົນສົ່ງ. ເມື່ອປ່ອຍລົດແລ້ວ, ຂໍ້ມູນຈະສະແດງຢູ່ນີ້.'
      },
      completed: {
        vi: 'Chưa có DO hoàn thành. DO đã giao/POD xong sẽ nằm ở tab này.',
        en: 'No completed DOs. Delivered orders with POD will appear here.',
        la: 'ຍັງບໍ່ມີ DO ສຳເລັດແລ້ວ. DO ທີ່ຈັດສົ່ງ/POD ສຳເລັດຈະສະແດງຢູ່ນີ້.'
      },
      incident: {
        vi: 'Không có DO gặp sự cố. Incident chưa xử lý sẽ được gom vào tab này.',
        en: 'No incident reported. Unresolved incidents will appear here.',
        la: 'ບໍ່ມີ DO ທີ່ພົບບັນຫາ. ອຸບັດຕິເຫດທີ່ຍັງບໍ່ໄດ້ແກ້ໄຂຈະສະແດງຢູ່ນີ້.'
      }
    };
    const emptyText = (emptyMap[activeDOStage] && emptyMap[activeDOStage][lang]) || (lang === 'la' ? 'ຍັງບໍ່ມີໃບສັ່ງສົ່ງສິນຄ້າທີ່ກົງກັນ.' : (lang === 'en' ? 'No matching delivery orders.' : 'Chưa có lệnh giao hàng phù hợp.'));
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:#64748b; padding:24px;"><i class="fa-solid fa-folder-open"></i> ${emptyText}</td></tr>`;
    return;
  }

  // Cắt xuống GIOI_HAN_DONG_DO trước khi vẽ. Con số bị cắt được nói ra ngay
  // dưới bảng, chứ không âm thầm bỏ bớt.
  list.slice(0, GIOI_HAN_DONG_DO).forEach(do_item => {
    const presented = window.WorkflowPresentation?.presentRecord(do_item) || do_item;
    const operationalStatus = deliveryOrderOperationalStatus(do_item);
    const pickupLabel = deliveryOrderDateLabel(do_item.pickup_window_start || do_item.pickup_date);
    const deliveryLabel = deliveryOrderDateLabel(do_item.delivery_window_start || do_item.delivery_date || do_item.delivery_window_end);
    const doId = doBoardEscape(do_item.id);
    const lapDuoc = doLapTripDuoc(do_item);
    // Hủy được hay không là một câu hỏi KHÁC với lập Trip được hay không,
    // dù hiện hai điều kiện trùng nhau. Tra riêng để mai này backend nới một
    // bên thì bên kia không lặng lẽ nới theo.
    const huyDuoc = huyDuocDon(do_item);
    // Chỉ hiện nút "đã đến nơi" khi xe đang trên đường. Ở `arrived` thì đã
    // báo rồi, ở `pending` thì chưa chạy, ở `delivered` thì xong — hiện nút
    // ở những trạng thái đó là mời bấm một việc không có nghĩa.
    const denNoiDuoc = String(do_item?.canonical_status || '').toLowerCase() === 'in_transit';
    const daChon = doDaChon.has(String(do_item.id));
    const tuyen = tuyenTheoMa(do_item.route_id);
    const ro = deliveryOrderStage(do_item);
    const hang = moTaHangHoa(do_item);
    const soTre = typeof window.DoBoard?.daysLate === "function"
      ? window.DoBoard.daysLate(do_item) : 0;

    // Màu ô trạng thái theo rổ, để đọc được tình trạng mà không phải dò chữ.
    const mauRo = {
      incident: "do-pill-red", overdue: "do-pill-red",
      undated: "do-pill-amber", near_late: "do-pill-amber",
      pending: "do-pill-grey", active: "do-pill-blue",
      completed: "do-pill-green",
    }[ro] || "do-pill-grey";

    // Thiếu hạn giao thì sửa NGAY TẠI DÒNG, không bắt người dùng rời màn.
    const oGiao = deliveryLabel && deliveryLabel !== "—"
      ? `<div class="do-cell-main">${doBoardEscape(do_item.destination || "")}</div>`
        + `<div class="do-cell-sub">${doBoardEscape(deliveryLabel)}</div>`
      : `<div class="do-cell-main">${doBoardEscape(do_item.destination || "")}</div>`
        + `<button type="button" class="do-cell-fix" onclick="editFioriDO('${doId}')">`
        + 'Chưa có hạn giao — thêm ngay</button>';

    tbody.insertAdjacentHTML('beforeend', `
      <tr class="${daChon ? 'picked' : ''}">
        <td class="do-plan-tick">
          <input type="checkbox" data-do-id="${doId}" ${daChon ? 'checked' : ''}
                 ${lapDuoc ? '' : 'disabled'}
                 title="${lapDuoc ? 'Chọn để lập Trip' : 'Chỉ DO đang chờ vận chuyển mới lập Trip được'}"
                 onchange="tickDO('${doId}', this.checked, this)">
        </td>
        <td><div class="do-cell-id">${doId}</div>
            <div class="do-cell-sub">${doBoardEscape(do_item.quotation_id || '—')}</div></td>
        <td><div class="do-cell-main">${doBoardEscape(do_item.customer_id || '—')}</div>
            ${presented.is_demo ? '<div class="do-cell-sub">Dữ liệu mẫu</div>' : ''}</td>
        <td><div class="do-cell-main">${doBoardEscape(do_item.origin || '')}</div>
            <div class="do-cell-sub">${doBoardEscape(pickupLabel)}</div></td>
        <td>${oGiao}
            ${soTre > 0 ? `<div class="do-cell-late">Trễ ${soTre} ngày</div>` : ''}</td>
        <td><div class="do-cell-main">${doBoardEscape(hang.chinh)}</div>
            ${hang.phu ? `<div class="do-cell-sub">${doBoardEscape(hang.phu)}</div>` : ''}</td>
        <td>${tuyen
              ? `<div class="do-cell-main">${doBoardEscape(tuyen.name || tuyen.id)}</div>`
                + `<div class="do-cell-sub">${formatRouteKm(routeTotalDistanceKm(tuyen))} km`
                + ` · ${routeSegments(tuyen).length} chặng</div>`
              : '<div class="do-cell-sub">Chưa gán tuyến</div>'}</td>
        <td>
          <button type="button" class="do-status-pill ${mauRo}"
                  title="Bấm để lọc theo tình trạng này"
                  onclick="locTheoOTrangThai('${ro}')">${doBoardEscape(operationalStatus.label)}</button>
          ${ro === 'cancelled' && do_item.cancel_reason ? `<div class="do-cell-sub" title="Lý do hủy">Lý do: ${doBoardEscape(do_item.cancel_reason)}</div>` : ''}
        </td>
        <td>
          <div class="do-row-act">
            <button type="button" title="Xem chi tiết DO"
                    onclick="editFioriDO('${doId}')"><i class="fa-solid fa-eye"></i></button>
            ${denNoiDuoc ? `<button type="button" class="den-noi" title="Xe đã đến nơi — ghi mốc, chưa chốt tiền"
                    onclick="ghiXeDaDenNoi('${doId}')"><i class="fa-solid fa-map-pin"></i></button>` : ''}
            ${huyDuoc ? `<button type="button" class="huy" title="Hủy lệnh giao hàng"
                    onclick="huyLenhGiaoHang('${doId}')"><i class="fa-solid fa-ban"></i></button>` : ''}
            ${ro === 'cancelled' ? `<button type="button" class="huy" title="Xóa lệnh đã hủy khỏi danh sách"
                    onclick="xoaLenhDaHuy('${doId}')"><i class="fa-solid fa-trash"></i></button>` : ''}
          </div>
        </td>
      </tr>`);
  });

  // Chan so dong ve ra. O hang nghin don thi dung mot lan innerHTML cho tat
  // ca la dung lai loi da phai sua o man lich xe.
  if (list.length > GIOI_HAN_DONG_DO) {
    tbody.insertAdjacentHTML('beforeend', `
      <tr><td colspan="9" style="padding:14px 20px; background:#fffbeb; color:#92400e; font-size:.78rem; font-weight:600;">
        Đang hiện ${GIOI_HAN_DONG_DO} trên ${list.length} DO của rổ này.
        Dùng ô tìm kiếm hoặc chọn rổ khác để thu hẹp lại.
      </td></tr>`);
  }

  veChipVaChanTrang(list.length);
  veThanhHanhDong();
}

window.deleteFioriDO = async function (id) {
  const doItem = (eplDeliveryOrders || []).find(d => d.id === id);
  const actions = doItem ? workflowActionMode(doItem.canonical_status || doItem.status, 'delivery_order') : { canDelete: true };
  if (doItem && !actions.canDelete) {
    showToast('Lệnh giao hàng đã duyệt/đang chạy chỉ được xem, không được xóa.');
    return;
  }
  // XÓA khác HỦY. Xóa là bỏ hẳn bản ghi, dùng cho đơn nhập sai; hủy là ghi
  // nhận một việc đã xảy ra thật và giữ lại lịch sử — xem `huyLenhGiaoHang`.
  if (!confirm('Bạn có chắc chắn muốn xóa Lệnh Giao Hàng ' + id + '?')) return;
  const viec = 'Xóa lệnh giao hàng ' + id;
  let res;
  try {
    res = await fetch(API_BASE + '/api/delivery-orders/' + encodeURIComponent(id),
                      { method: 'DELETE' });
  } catch (e) {
    return baoMatKetNoi(viec, e);
  }
  // Trước đây nhánh này chỉ nói "Lỗi khi xóa DO" — không nói VÌ SAO. Mà lý do
  // thường là thứ người dùng cần biết và tự xử lý được: đơn còn chuyến vận tải
  // tham chiếu tới nó.
  if (!res.ok) return baoLoiMayChu(res, viec);
  showToast('Đã xóa DO ' + id + ' thành công!');
  await loadDeliveryOrders();
};

function filterDeliveryOrders() {
  const query = normalizeSearchText(document.getElementById('do-search-input')?.value || '');
  const filtered = eplDeliveryOrders.filter(d => deliveryOrderSearchText(d).includes(query));
  renderDeliveryOrders(filtered);
}

window.switchDeliveryOrderStage = function (stage) {
  // Rổ lạ thì đặt lại về `null` để lần vẽ sau tự chọn rổ cấp bách nhất mà có
  // dòng, thay vì rơi cứng về một rổ có thể đang rỗng.
  activeDOStage = DELIVERY_ORDER_STAGES.includes(stage) ? stage : null;
  filterDeliveryOrders();
};

window.switchDeliveryOrderSubtab = function (tab) {
  const activeTab = tab === 'routes' ? 'routes' : 'delivery';
  document.querySelectorAll('[data-do-subtab-panel]').forEach(panel => {
    panel.style.display = panel.getAttribute('data-do-subtab-panel') === activeTab ? '' : 'none';
  });
  document.querySelectorAll('.do-workspace-subtab').forEach(button => {
    const isActive = button.id === `do-subtab-${activeTab === 'delivery' ? 'delivery' : 'routes'}`;
    button.classList.toggle('active', isActive);
  });
  if (activeTab === 'routes') {
    renderRoutes(eplRoutes || []);
    const search = document.getElementById('route-reference-search');
    if (search) search.focus({ preventScroll: true });
  } else {
    filterDeliveryOrders();
  }
};

function routeSegments(route) {
  const raw = route?.segments_json;
  if (Array.isArray(raw)) return raw;
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (error) {
    console.warn('Invalid route segments_json', route?.id, error);
    return [];
  }
}

function routeSegmentDistanceKm(segment) {
  return parseFloat(segment?.distance_km ?? segment?.dist_km ?? segment?.distance ?? segment?.km ?? 0) || 0;
}

function routeSegmentFrom(segment) {
  return segment?.from || segment?.origin || segment?.start || segment?.from_name || 'Điểm đi';
}

function routeSegmentTo(segment) {
  return segment?.to || segment?.destination || segment?.end || segment?.to_name || 'Điểm đến';
}

function routeTotalDistanceKm(route) {
  const segments = routeSegments(route);
  const savedKm = parseFloat(route?.distance_km ?? route?.dist_km ?? route?.distance ?? route?.km ?? 0) || 0;
  if (savedKm > 0) return savedKm;
  return segments.reduce((sum, segment) => sum + routeSegmentDistanceKm(segment), 0);
}

function formatRouteKm(km) {
  const value = Number(km || 0);
  return Number(value.toFixed(1)).toLocaleString('vi-VN');
}

function routeReferenceSearchText(route) {
  const segments = routeSegments(route);
  return normalizeSearchText([
    route?.id,
    route?.name,
    route?.distance_km,
    ...segments.flatMap(segment => [
      routeSegmentFrom(segment),
      routeSegmentTo(segment),
      routeSegmentDistanceKm(segment)
    ])
  ].join(' '));
}

window.filterRouteReferences = function () {
  const query = normalizeSearchText(document.getElementById('route-reference-search')?.value || '');
  renderRoutes((eplRoutes || []).filter(route => routeReferenceSearchText(route).includes(query)));
};

window.closeRouteDetailModal = function () {
  const modal = document.getElementById('route-detail-modal');
  if (modal) modal.style.display = 'none';
};

window.openRouteDetailModal = function (routeId) {
  const route = (eplRoutes || []).find(item => String(item.id || '') === String(routeId || ''));
  if (!route) return;
  const modal = document.getElementById('route-detail-modal');
  const title = document.getElementById('route-detail-title');
  const subtitle = document.getElementById('route-detail-subtitle');
  const summary = document.getElementById('route-detail-summary');
  const body = document.getElementById('route-detail-segments');
  if (!modal || !title || !subtitle || !summary || !body) return;

  const segments = routeSegments(route);
  const totalKm = routeTotalDistanceKm(route);

  // Thời gian chạy: chỉ hiện khi có nguồn thật, và NÓI RÕ tính ở tốc độ nào.
  //
  // Bản trước là `(totalKm / 50).toFixed(1)` rồi dán nhãn "giờ dự kiến". Con
  // số 50 km/h không có nguồn nào — không phải tốc độ của loại xe, không phải
  // tốc độ kế hoạch của chuyến — nhưng kết quả hiện ra trông y hệt một con số
  // thật. Nay lấy tốc độ kế hoạch người dùng đang đặt; không có thì không
  // đoán.
  const tocDoKeHoach = Number(document.getElementById('trip-avg-speed')?.value || 0);
  const nhanGio = route.est_hours || route.hrs
    ? `${doBoardEscape(route.est_hours || route.hrs)} giờ`
    : (totalKm > 0 && tocDoKeHoach > 0
      ? `${(totalKm / tocDoKeHoach).toFixed(1)} giờ ở ${tocDoKeHoach} km/h`
      : 'chưa có tốc độ kế hoạch');

  // Lệch giữa `distance_km` và tổng các chặng thì phải nói ra: backend từ
  // chối lập Trip trên tuyến lệch (ROUTE_DISTANCE_MISMATCH).
  const lech = lechQuangDuongTuyen(route);

  title.innerHTML = `<i class="fa-solid fa-route"></i> ${doBoardEscape(route.name || route.id || 'Chi tiết tuyến')}`;
  subtitle.textContent = `${route.id || ''} - dữ liệu chặng từ Master Data`;
  summary.innerHTML = `
    <span class="fiori-status fiori-status-pending">${doBoardEscape(formatRouteKm(totalKm))} km</span>
    <span class="fiori-status fiori-status-approved">${nhanGio}</span>
    <span class="fiori-status fiori-status-pending">${segments.length} chặng</span>
    ${lech ? `<span class="fiori-status fiori-status-rejected" title="Máy chủ từ chối lập Trip khi hai con số này lệch">`
      + `Chặng cộng lại ${doBoardEscape(formatRouteKm(lech.tongChang))} km — lệch</span>` : ''}
  `;

  if (segments.length === 0) {
    body.innerHTML = '<div style="padding:18px; border:1px dashed #cbd5e1; border-radius:10px; color:#64748b; font-weight:700;">Tuyến này chưa có cấu hình chặng trong Master Data.</div>';
  } else {
    let cumulative = 0;
    body.innerHTML = segments.map((segment, index) => {
      const segmentKm = routeSegmentDistanceKm(segment);
      cumulative += segmentKm;
      return `
        <div style="display:grid; grid-template-columns:40px minmax(0,1fr) 118px; gap:12px; align-items:center; padding:13px 0; border-bottom:1px solid #e2e8f0;">
          <div style="width:32px; height:32px; border-radius:999px; background:#eff6ff; color:#2563eb; display:flex; align-items:center; justify-content:center; font-weight:900;">${index + 1}</div>
          <div style="min-width:0;">
            <div style="font-weight:900; color:#0f172a; overflow-wrap:anywhere;">${doBoardEscape(routeSegmentFrom(segment))} <span style="color:#64748b;">â†’</span> ${doBoardEscape(routeSegmentTo(segment))}</div>
            <div style="font-size:.8rem; color:#64748b; margin-top:3px;">Lũy kế ${doBoardEscape(formatRouteKm(cumulative))} km</div>
          </div>
          <div style="text-align:right;"><span class="fiori-status fiori-status-pending">${doBoardEscape(formatRouteKm(segmentKm))} km</span></div>
        </div>
      `;
    }).join('');
  }
  modal.style.display = 'flex';
};

/* ==========================================================================
   Xóa tuyến đường.

   `DELETE /api/routes/{id}` có ở backend nhưng giao diện chưa bao giờ gọi —
   chuỗi `api/routes/` không xuất hiện một lần nào trong các tệp JS. Nghĩa là
   nhập sai một tuyến thì nó nằm đó mãi trong danh mục, và người lập báo giá
   vẫn chọn được nó.

   Backend có chốt an toàn: tuyến đang được báo giá / đơn vận chuyển / lệnh
   giao hàng tham chiếu thì trả 409 `LOCKED_RECORD` kèm câu nói rõ vướng ở
   đâu. `baoLoiMayChu` đọc đúng ba lớp của phong bì lỗi nên câu đó đến được
   người dùng, thay vì một câu "Lỗi khi xóa" chung chung.
   ========================================================================== */

window.xoaTuyenDuong = async function (id) {
  const tuyen = (eplRoutes || []).find(r => String(r.id) === String(id));
  const ten = tuyen?.name ? `${id} — ${tuyen.name}` : id;
  if (!confirm(`Xóa tuyến đường ${ten}?`
    + String.fromCharCode(10) + String.fromCharCode(10)
    + 'Nếu tuyến đang được báo giá hoặc đơn nào tham chiếu thì hệ thống sẽ'
    + ' từ chối và nói rõ vướng ở đâu.')) return;

  const viec = `Xóa tuyến đường ${id}`;
  let res;
  try {
    res = await fetch(`${API_BASE}/api/routes/${encodeURIComponent(id)}`,
                      { method: 'DELETE' });
  } catch (e) {
    return baoMatKetNoi(viec, e);
  }
  if (!res.ok) return baoLoiMayChu(res, viec);
  showToast(`🗑️ Đã xóa tuyến đường ${id}.`);
  if (typeof loadDeliveryOrders === 'function') await loadDeliveryOrders();
};

/**
 * Đếm chứng từ đang tham chiếu một tuyến.
 *
 * Nối thẳng với chốt 409 `LOCKED_RECORD` của `delete_route`: backend từ chối
 * xóa tuyến đang được báo giá / đơn vận chuyển / lệnh giao hàng dùng tới.
 * Đếm ở đây để người dùng biết TRƯỚC khi bấm xóa, thay vì bấm rồi nhận lỗi.
 *
 * Đếm từ dữ liệu ĐÃ NẠP, không gọi thêm máy chủ — nên con số có thể cũ hơn
 * một chút, và đó là lý do câu chốt cuối cùng vẫn thuộc về backend. Ở đây chỉ
 * cần đủ đúng để không mời người ta bấm một cái nút sẽ bị từ chối.
 */
function demChungTuDungTuyen(routeId) {
  const ma = String(routeId || '');
  if (!ma) return { tong: 0, chi_tiet: [] };
  const nhom = [
    ['báo giá', (crmQuotations || []).filter(q => String(q.route_id || '') === ma).length],
    ['lệnh giao hàng', (eplDeliveryOrders || []).filter(d => String(d.route_id || '') === ma).length],
  ].filter(([, n]) => n > 0);
  return {
    tong: nhom.reduce((s, [, n]) => s + n, 0),
    chi_tiet: nhom.map(([ten, n]) => `${n} ${ten}`),
  };
}

/** Tuyến kiểm thử do các script E2E / stress sinh ra. */
function laTuyenKiemThu(routeId) {
  return /^(E2E|STRESS|TEST)/i.test(String(routeId || ''));
}

window.moChangTuyen = function (routeId) {
  const dong = document.getElementById(`route-legs-${routeId}`);
  if (dong) dong.hidden = !dong.hidden;
};

window.filterRouteReference = function () {
  renderRoutes(eplRoutes);
};

function renderRoutes(data) {
  const body = document.getElementById('fiori-route-strip');
  if (!body) return;

  const tim = normalizeSearchText(
    document.getElementById('route-reference-search')?.value || '');
  const anKiemThu = Boolean(document.getElementById('route-hide-test')?.checked);

  const tatCa = data || [];
  const routes = tatCa.filter(r => {
    if (anKiemThu && laTuyenKiemThu(r.id)) return false;
    if (!tim) return true;
    const chuoi = normalizeSearchText([
      r.id, r.name,
      ...routeSegments(r).flatMap(s => [routeSegmentFrom(s), routeSegmentTo(s)]),
    ].join(' '));
    return chuoi.includes(tim);
  });

  const oDem = document.getElementById('route-reference-count');
  if (oDem) {
    const dungRoi = tatCa.filter(r => demChungTuDungTuyen(r.id).tong > 0).length;
    oDem.textContent = `${routes.length}${routes.length !== tatCa.length ? `/${tatCa.length}` : ''}`
      + ` tuyến · ${dungRoi} đang được dùng`;
  }

  if (routes.length === 0) {
    body.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:26px; color:#64748b;">`
      + `<i class="fa-solid fa-folder-open"></i> `
      + (tim || anKiemThu
        ? 'Không có tuyến nào khớp bộ lọc hiện tại.'
        : 'Chưa có tuyến đường nào trong Dữ liệu gốc.')
      + '</td></tr>';
    return;
  }

  body.innerHTML = '';
  routes.forEach(r => {
    const routeId = doBoardEscape(r.id || '');
    const chang = routeSegments(r);
    const lech = lechQuangDuongTuyen(r);
    const dung = demChungTuDungTuyen(r.id);
    const tocDo = Number(document.getElementById('trip-avg-speed')?.value || 0);
    const km = routeTotalDistanceKm(r);
    // Thời gian chỉ hiện khi CÓ cả quãng đường và tốc độ kế hoạch. Bản trước
    // viết cứng `km / 50` rồi gọi đó là "giờ chạy thực tế" — 50 km/h không có
    // nguồn nào, và con số ra trông y hệt một con số thật.
    const phut = km > 0 && tocDo > 0 ? Math.round((km / tocDo) * 60) : null;

    let luyKe = 0;
    body.insertAdjacentHTML('beforeend', `
      <tr onclick="moChangTuyen('${routeId}')" style="cursor:pointer;">
        <td>
          <div class="do-cell-main">${doBoardEscape(r.name || r.id || 'Tuyến chưa đặt tên')}</div>
          <div class="do-cell-sub">${routeId}${laTuyenKiemThu(r.id)
            ? ' <span class="do-route-tag">Kiểm thử</span>' : ''}</div>
        </td>
        <td>
          <div class="do-cell-main">${formatRouteKm(km)} km</div>
          ${lech
            ? `<div class="do-cell-late" title="Máy chủ từ chối lập Trip khi hai con số này lệch">`
              + `Chặng cộng lại ${formatRouteKm(lech.tongChang)} km — lệch</div>`
            : (phut != null
              ? `<div class="do-cell-sub">~${phut} phút ở ${tocDo} km/h</div>`
              : '<div class="do-cell-sub">chưa có tốc độ kế hoạch</div>')}
        </td>
        <td><div class="do-cell-main">${chang.length}</div></td>
        <td>
          ${dung.tong
            ? `<div class="do-cell-main">${doBoardEscape(dung.chi_tiet.join(' · '))}</div>`
              + '<div class="do-cell-sub">Không xóa được khi còn tham chiếu</div>'
            : '<div class="do-cell-sub">Chưa dùng</div>'}
        </td>
        <td style="white-space:nowrap;">
          <button class="fiori-btn fiori-btn-secondary" title="Xem sơ đồ lộ trình"
                  style="width:32px; height:30px; padding:0; border-radius:7px;"
                  onclick="event.stopPropagation(); openRouteDetailModal('${routeId}')">
            <i class="fa-solid fa-map-location-dot"></i></button>
          <button class="fiori-btn fiori-btn-secondary" title="Xóa tuyến đường"
                  style="width:32px; height:30px; padding:0; margin-left:5px; border-radius:7px; color:#b42318;"
                  onclick="event.stopPropagation(); xoaTuyenDuong('${routeId}')">
            <i class="fa-solid fa-trash"></i></button>
        </td>
      </tr>
      <tr id="route-legs-${routeId}" hidden>
        <td colspan="5" style="background:#f8fafc; padding:12px 20px;">
          ${chang.length
            ? `<ul class="do-side-legs" style="margin:0;">${chang.map((c, k) => {
                const d = routeSegmentDistanceKm(c);
                luyKe += d;
                return `<li><i>${k + 1}</i>`
                  + `<b>${doBoardEscape(routeSegmentFrom(c))} → ${doBoardEscape(routeSegmentTo(c))}</b>`
                  + `<span>${formatRouteKm(d)} km`
                  + `${chang.length > 1 ? ` · lũy kế ${formatRouteKm(luyKe)}` : ''}</span></li>`;
              }).join('')}</ul>`
            : '<div class="do-cell-sub">Tuyến này chưa có chặng nào trong Dữ liệu gốc.'
              + ' Máy chủ từ chối lập Trip khi tuyến không có chặng hợp lệ.</div>'}
        </td>
      </tr>`);
  });
}
// LỆNH GIAO HÀNG KHÔNG CÒN TẠO TAY, KHÔNG CÒN TẠO TỪ SO.
//
// Chủ dự án chốt: "DO kế thừa từ QT — gen tự động khi QT được duyệt hết".
// Máy chủ sinh DO ngay lúc ghi nhận khách chấp nhận báo giá
// (`POST /api/quotations/{id}/accept`), mang theo tuyến, giá khoá và khung giờ
// của báo giá. Một form tạo DO trống ở đây là mời người dùng đâm ngang vào
// luồng — nên nút "+ Tạo lệnh giao hàng" dẫn về màn Báo giá.
window.openFioriDOForm = function () {
  showToast('Lệnh giao hàng được sinh tự động từ báo giá khi khách chấp nhận. '
    + 'Mở báo giá, ghi nhận khách chấp nhận — DO sẽ xuất hiện ở "Cần xử lý".');
  if (typeof window.switchView === 'function') window.switchView('crm-sales', 'qtv2-root');
};

// Khung form DO — CHỈ dùng để XEM một DO đã có (editFioriDO).
function moKhungFormDO() {
  const el = document.getElementById('fiori-do-form');
  if (el) {
    el.style.display = 'flex';
  }
  setFormLoadingState('fiori-do-form', true, 'Đang chuẩn bị form DO...');
  currentDOMode = 'create';
  const titleEl = document.getElementById('fiori-do-form-title');
  if (titleEl) titleEl.innerText = 'Lệnh Giao Hàng';
  const subtitleEl = titleEl?.closest('div')?.querySelector('div');
  if (subtitleEl) subtitleEl.textContent = 'Lệnh giao hàng xuất kho - bản nháp';
  ['do-id', 'do-so-ref', 'do-customer', 'do-route', 'do-pickup', 'do-delivery', 'do-extra-cost-reason'].forEach(id => {
    const input = document.getElementById(id);
    if (!input) return;
    input.value = '';
    input.readOnly = false;
    input.style.background = '';
  });
  setDOSettlementFromSource({});
  setDOSettlementSaveState(null, false);
  document.querySelectorAll('#fiori-do-form input, #fiori-do-form select, #fiori-do-form textarea').forEach(el => {
    if (el.type !== 'hidden') el.disabled = false;
  });
  refreshDOFormControls();
  setRouteContextFields('do', {});
  setTimeout(() => setFormLoadingState('fiori-do-form', false), 120);
}

window.closeFioriDOForm = function () {
  setFormLoadingState('fiori-do-form', false);
  const el = document.getElementById('fiori-do-form');
  if (el) el.style.display = 'none';
};

window.editFioriDO = function (id) {
  const do_item = (eplDeliveryOrders || []).find(d => d.id === id) || {
    id: id || '',
    quotation_id: '',
    customer_id: '',
    route_id: ''
  };
  const locked = true;

  moKhungFormDO();
  const titleEl = document.getElementById('fiori-do-form-title');
  if (titleEl) titleEl.innerText = 'Xem Lệnh Giao Hàng: ' + do_item.id;
  const subtitleEl = titleEl?.closest('div')?.querySelector('div');
  if (subtitleEl) {
    const opStatus = deliveryOrderOperationalStatus(do_item);
    subtitleEl.textContent = `${opStatus.label} - chỉ xem, không chỉnh sửa tại màn DO`;
  }
  currentDOMode = 'view';

  if (document.getElementById('do-id')) {
    document.getElementById('do-id').value = do_item.id;
    document.getElementById('do-id').disabled = true;
  }
  // Ô "Báo giá gốc": DO sinh từ báo giá mang `quotation_id`; DO cũ (trước khi
  // bỏ bước Đơn hàng) không còn mã đơn — cột đó đã trục xuất ở migration 049.
  if (document.getElementById('do-so-ref')) document.getElementById('do-so-ref').value = do_item.quotation_id || '';
  if (document.getElementById('do-customer')) document.getElementById('do-customer').value = do_item.customer_id || '';
  if (document.getElementById('do-route')) document.getElementById('do-route').value = do_item.route_id || '';
  setRouteContextFields('do', do_item);
  setDOSettlementFromSource(do_item);

  document.querySelectorAll('#fiori-do-form input, #fiori-do-form select, #fiori-do-form textarea').forEach(el => {
    if (el.type !== 'hidden') el.disabled = true;
  });
  refreshDOFormControls();
  loadDOSettlementCost(do_item.id);
}

window.saveFioriDO = async function () {
  if (currentDOMode === 'view') {
    showToast('DO đang ở chế độ chỉ xem, không được chỉnh sửa tại màn này.');
    return;
  }
  const currentId = document.getElementById('do-id')?.value || '';
  const currentDO = (eplDeliveryOrders || []).find(d => d.id === currentId);
  const currentActions = currentDO ? workflowActionMode(currentDO.canonical_status || currentDO.status, 'delivery_order') : { canEdit: true };
  if (currentDO && !currentActions.canEdit) {
    showToast('DO đã khóa nghiệp vụ. Chi phí thực tế phải lưu bằng nút Lưu chi phí sau khi Trip hoàn thành.');
    return;
  }
  const routeContext = routeContextFromFields('do');
  const payload = {
    route_id: document.getElementById('do-route').value,
    ...routeContext,
    pickup_window_start: tripReturnIsoFromLocal(routeContext.pickup_window_start),
    pickup_window_end: tripReturnIsoFromLocal(routeContext.pickup_window_end),
    delivery_window_start: tripReturnIsoFromLocal(routeContext.delivery_window_start),
    delivery_window_end: tripReturnIsoFromLocal(routeContext.delivery_window_end),
    pickup_date: tripReturnIsoFromLocal(document.getElementById('do-pickup').value),
    delivery_date: tripReturnIsoFromLocal(document.getElementById('do-delivery').value)
  };
  if (!currentDO) {
    // Không có đường tạo DO tay: DO là thứ báo giá sinh ra khi khách chấp nhận.
    showToast('Không tạo lệnh giao hàng bằng tay. Mở báo giá và ghi nhận khách chấp nhận — '
      + 'DO sẽ được sinh tự động, kế thừa tuyến và giá khoá của báo giá.');
    return;
  }

  const doPath = currentDO ? `/api/delivery-orders/${encodeURIComponent(currentId)}` : '/api/delivery-orders';
  const result = await executeWorkflowCommand(currentDO ? 'deliveryOrderEdit' : 'deliveryOrderCreate', {
    path: doPath, method: currentDO ? 'PUT' : 'POST', body: payload
  });
  if (result.ok) {
    showToast(result.payload?.message || 'Đã lưu Lệnh Giao Hàng DO thành công!');
    closeFioriDOForm();
    window.updateActiveFlowStep(4, true);
  }
}

window.loadDeliveryOrders = loadDeliveryOrders;

// ==========================================
// DISPATCH PLANNING & TRACKING
// ==========================================

let dispatchDOs = [];
let availableVehicles = [];
let availableDrivers = [];
let dispatchTrackingByDO = {};

const DISPATCH_PENDING_CANONICAL_STATUSES = new Set([
  'pending',
  'planned',
  'approved',
  'ready',
  'ready_for_dispatch'
]);

const DISPATCH_DONE_CANONICAL_STATUSES = new Set([
  'in_transit',
  'delivered',
  'completed',
  'cancelled',
  'canceled'
]);

function normalizeStatusForFlow(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[đĐ]/g, 'd')
    .toLowerCase()
    .trim();
}

function isDriverBusyForDispatch(status) {
  const s = normalizeStatusForFlow(status);
  return s.includes('ban') ||
    s.includes('dang theo xe') ||
    s.includes('dang van chuyen') ||
    s.includes('in transit');
}

function isVehicleBusyForDispatch(status) {
  const s = normalizeStatusForFlow(status);
  return s.includes('bận') ||
    s.includes('ban') ||
    s.includes('đang vận chuyển') ||
    s.includes('dang van chuyen') ||
    s.includes('in transit') ||
    s.includes('giao đơn') ||
    s.includes('giao don') ||
    s.includes('bảo dưỡng') ||
    s.includes('bao duong') ||
    s.includes('maintenance');
}

function isDOInTransitForDispatch(status, canonicalStatus = '') {
  const s = normalizeStatusForFlow(status);
  const c = normalizeStatusForFlow(canonicalStatus);
  return c === 'in_transit' ||
    s.includes('đang vận chuyển') ||
    s.includes('dang van chuyen') ||
    s.includes('in transit') ||
    s.includes('Ä‘ang giao') ||
    s.includes('dang giao');
}

function calcDispatchProgress(doRow, routeObj) {
  const track = dispatchTrackingByDO[doRow.id] || {};
  const totalKm = Number(routeObj?.distance_km || track.route_distance_km || 0);
  const remainingRaw = track.remaining_distance_km ?? track.remaining_km;
  const remainingKm = remainingRaw === undefined || remainingRaw === null || remainingRaw === ''
    ? totalKm
    : Math.max(0, Number(remainingRaw) || 0);
  const doneKm = totalKm > 0 ? Math.max(0, totalKm - remainingKm) : 0;
  const pct = totalKm > 0 ? Math.min(100, Math.max(0, Math.round((doneKm / totalKm) * 100))) : 0;
  return {
    totalKm,
    remainingKm,
    doneKm,
    pct,
    eta: track.eta || track.eta_time || ''
  };
}

async function refreshDispatchTrackingMap(dos) {
  dispatchTrackingByDO = {};
  const candidates = (dos || []).filter(d => isDOInTransitForDispatch(d.status, d.canonical_status));
  // Đếm số chuyến hỏng thay vì báo từng chuyến một: hàm này chạy song song
  // cho MỌI đơn đang trên đường, nên mất mạng là hàng chục lời báo giống hệt
  // nhau — mà `showToast` chỉ giữ được cái cuối cùng.
  const hong = [];
  // 404 kem mã `TRACKING_NOT_FOUND` KHÔNG phải lỗi: máy chủ đang nói
  // chuyến này chưa điều phối xe, hoặc thiết bị GPS chưa gửi điểm nào.
  // Gộp nó vào "nạp thất bại" là đẩy người điều độ đi kiểm tra mạng và
  // máy chủ, trong khi việc cần làm là điều phối xe.
  const chuaCoGps = [];
  await Promise.all(candidates.map(async (d) => {
    try {
      const res = await fetch(`${API_BASE}/api/tracking/${encodeURIComponent(d.id)}`);
      if (res.status === 404) { chuaCoGps.push(d.id); return; }
      if (!res.ok) { hong.push(d.id); return; }
      const track = await res.json();
      dispatchTrackingByDO[d.id] = track || {};
    } catch (err) {
      console.warn('Không tải được tracking cho DO', d.id, err);
      hong.push(d.id);
    }
  }));
  // Thiếu vị trí thì xe biến mất khỏi bản đồ điều độ. Không nói ra thì người
  // điều độ đếm xe trên màn và tưởng số xe đang chạy ít hơn thực tế.
  if (hong.length) {
    baoNapThatBai(`vị trí của ${hong.length}/${candidates.length} chuyến đang chạy`,
      new Error(hong.slice(0, 5).join(', ')));
  }
  // Chưa có GPS thì nói đúng việc cần làm, và nói MỘT lần cho cả nhóm.
  if (chuaCoGps.length) {
    showToast(`⚠️ ${chuaCoGps.length}/${candidates.length} chuyến đang chạy chưa có dữ liệu GPS${chuaCoGps.length <= 3 ? ` (${chuaCoGps.join(", ")})` : ""}. Hãy điều phối xe hoặc kiểm tra thiết bị GPS — xe sẽ không hiện trên bản đồ điều độ.`);
  }
  return hong;
}

async function loadDispatchBoard() {
  try {
    normalizeDispatchStaticText();
    const [allDOs, vehicles, drivers, trips] = await Promise.all([
      fetchAllPaginated(`${API_BASE}/api/delivery-orders`, 200),
      fetchAllPaginated(`${API_BASE}/api/vehicles?paginated=true`, 200),
      fetch(`${API_BASE}/api/drivers`).then(async response => {
        if (!response.ok) throw new Error(`HTTP ${response.status} while loading drivers`);
        return response.json();
      }),
      fetchAllPaginated(`${API_BASE}/api/tms/trips`, 200, { headers: financeAuthHeaders() })
    ]);

    eplDeliveryOrders = allDOs;
    appState.delivery_orders = allDOs;
    dispatchDOs = allDOs.filter(isDispatchPendingDO);
    renderDispatchDOs();

    availableVehicles = Array.isArray(vehicles) ? vehicles : [];
    appState.vehicles = availableVehicles;
    availableDrivers = Array.isArray(drivers) ? drivers : [];
    appState.drivers = availableDrivers;
    appState.transport_trips = Array.isArray(trips) ? trips : [];

    await refreshDispatchTrackingMap(allDOs);
    // Ca truc va lich xe: hai duong nay von chi duoc goi o man Sap lich xe, nen
    // vao man Dieu phoi la cot xe ung vien khong biet xe nao dang chay va tai
    // xe nao dang trong ca. Nap o day de cham diem du tieu chi.
    await napCaTrucChoDieuPhoi();
    renderDispatchSelects();
    renderDispatchScopeOptions();
    renderDispatchCalendar();
    // Ve LAI cot DO o day, khong chi ve cot xe ung vien: dai so lieu sinh ra tu
    // trong `renderDispatchDOs`, va the "Tai xe trong ca" doc `driverShifts`.
    // Ve dai truoc khi ca truc ve thi the do bao 0 trong khi bang ca truc co du
    // dong — da do that.
    renderDispatchDOs();
    renderDispatchCandidates();
    normalizeDispatchStaticText();
  } catch (e) {
    console.error("Failed to load dispatch data", e);
    availableVehicles = [];
    availableDrivers = [];
    renderDispatchSelects();
    normalizeDispatchStaticText();
  }
}

window.filterDispatchDOs = function () {
  const query = normalizeSearchText(document.getElementById('dispatch-do-search-input')?.value || '').trim();
  renderDispatchDOs(query);
};

function isDispatchPendingDO(order) {
  const canonical = normalizeStatusForFlow(order?.canonical_status || '');
  const status = normalizeStatusForFlow(order?.status || '');

  if (DISPATCH_DONE_CANONICAL_STATUSES.has(canonical)) return false;
  if (DISPATCH_PENDING_CANONICAL_STATUSES.has(canonical)) return true;

  return [
    'pending',
    'pending approval',
    'ready for dispatch',
    'san sang dieu phoi',
    'san sang',
    'draft',
    'confirmed',
    'lap ke hoach',
    'planned',
    'picked',
    'packed',
    'cho van chuyen',
    'do cho dieu phoi',
    'da xac nhan',
    'so da xac nhan',
    'do da duyet',
    'da duyet'
  ].includes(status);
}

function renderDispatchDOSelector(sourceDOs = null) {
  const dispatchSelectedDoEl = document.getElementById('dispatch-selected-do');
  if (!dispatchSelectedDoEl) return;

  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
  const currentValue = dispatchSelectedDoEl.value || '';
  const rawDOs = sourceDOs || (eplDeliveryOrders && eplDeliveryOrders.length > 0 ? eplDeliveryOrders : (dispatchDOs || []));
  const selectableDOs = rawDOs.filter(isDispatchPendingDO);

  const defaultOptionText = lang === 'la' ? 'ເລືອກ DO ເພື່ອມອບໝາຍລົດ/ຄົນຂັບ...' : (lang === 'en' ? 'Select DO to assign vehicle/driver...' : 'Chọn DO để gán xe/tài xế...');
  dispatchSelectedDoEl.innerHTML = `<option value="">${defaultOptionText}</option>` + selectableDOs.map(d => {
    const meta = [d.customer_id, d.route_id].filter(Boolean).join(' | ');
    return `<option value="${d.id}">${d.id}${meta ? ` - ${meta}` : ''}</option>`;
  }).join('');

  if (currentValue && selectableDOs.some(d => String(d.id) === String(currentValue))) {
    dispatchSelectedDoEl.value = currentValue;
  }
}

/* ==========================================================================
   DẢI SỐ LIỆU kiêm BỘ LỌC cho màn Điều phối, theo bản mẫu `dispatch-v2-crew`.

   Sáu con số, và bấm vào một thẻ là LỌC cột DO theo đúng nhóm đó. Một dải số mà
   bấm không ra gì thì chỉ chiếm chỗ — nên mỗi nhóm ở đây có một phép lọc thật,
   và nhóm nào không có dòng nào thì thẻ mờ đi và không bấm được.
   ========================================================================== */

/** Nhóm lọc đang chọn ở dải số liệu: '' | 'cho' | 'xong' | 'thieu-trip' | 'thieu-hang' */
let dispatchKpiFilter = '';

/**
 * Phân loại một DO vào các nhóm của dải số liệu.
 *
 * Một DO có thể thuộc NHIỀU nhóm — thiếu Trip và thiếu hàng hóa là hai chuyện
 * độc lập — nên trả về một tập, không phải một nhãn.
 */
function dispatchNhomCuaDO(d) {
  const nhom = new Set();
  const tt = String(d.canonical_status || '').toLowerCase();
  if (tt === 'pending') nhom.add('cho');
  if (tt === 'in_transit' || tt === 'arrived' || tt === 'delivered') nhom.add('xong');

  const cong = resolveDispatchTripGate(d.id);
  if (cong.state !== 'ready') nhom.add('thieu-trip');

  // Đơn chưa khai hàng hóa thì phép kiểm năng lực xe ở máy chủ không kiểm được
  // gì: cả ba con số bằng 0 thì xe nào cũng "vừa". Đó là một ngoại lệ thật.
  const kg = Number(d.weight_kg || 0);
  const m3 = Number(d.volume_m3 || 0);
  const pallet = Number(d.pallet_count || 0);
  if (!kg && !m3 && !pallet) nhom.add('thieu-hang');

  return nhom;
}

window.setDispatchKpiFilter = function (nhom) {
  dispatchKpiFilter = dispatchKpiFilter === nhom ? '' : String(nhom || '');
  renderDispatchDOs();
};

/** Vẽ dải số liệu. Mọi con số lấy từ dữ liệu thật, không có số cứng nào. */
/* ==========================================================================
   MÀN ĐIỀU PHỐI — các hàm vẽ, dựng theo bản mẫu
   `D:\Demo_Lao\nhap_UI__duan\dispatch-v2-crew.html`.

   Mọi thứ ở đây sinh ra markup của bản mẫu (`.kpi`, `.grp`, `.row`, `.g-row`,
   `.team`, `.crew`) và đọc dữ liệu từ backend thật. Không có dòng nào cứng.
   ========================================================================== */

//: Trục giờ của Gantt xe ứng viên: 06:00 đến 20:00, mười bốn ô một giờ — đúng
//: bằng bản mẫu. Chọn khung này vì ca sáng bắt đầu 06:00 và ca chiều kết thúc
//: 22:00; vẽ cả 24 giờ thì mỗi ô hẹp tới mức không đọc được nhãn nào.
const DPV2_GIO_DAU = 6;
const DPV2_SO_O = 14;

/** Đổi một mốc thời gian thành phần trăm trên trục giờ. */
function dpv2ViTri(moc) {
  if (!moc) return null;
  const d = (moc instanceof Date) ? moc : new Date(moc);
  if (isNaN(d)) return null;
  const gio = d.getHours() + d.getMinutes() / 60;
  return ((gio - DPV2_GIO_DAU) / DPV2_SO_O) * 100;
}

function dpv2Gio(moc) {
  if (!moc) return '';
  const d = (moc instanceof Date) ? moc : new Date(moc);
  if (isNaN(d)) return '';
  return d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
}

/** Vẽ nhãn giờ và vạch "bây giờ" trên trục. */
function renderDispatchCandHours() {
  const host = document.getElementById('dispatch-cand-hours');
  if (!host) return;
  const bayGio = dpv2ViTri(new Date());
  const nhan = [];
  // Vạch đỏ "bây giờ" chỉ vẽ khi giờ hiện tại NẰM TRONG trục. Ngoài giờ làm
  // việc thì `left` âm hoặc quá 100% và vạch dán vào mép, nói sai chỗ.
  if (bayGio !== null && bayGio >= 0 && bayGio <= 100) {
    nhan.push('<span class="nowlbl" style="left:' + bayGio.toFixed(2) + '%">'
      + dpv2Gio(new Date()) + '</span>');
  }
  for (let i = 0; i < DPV2_SO_O; i += 1) {
    nhan.push('<span>' + String(DPV2_GIO_DAU + i).padStart(2, '0') + '</span>');
  }
  host.innerHTML = nhan.join('');
}

/* --------------------------------------------------------------------------
   DẢI SỐ LIỆU — sáu thẻ, đúng bằng bản mẫu.
   -------------------------------------------------------------------------- */

function renderDispatchKpis(dsTrongNgay, dsHienRa) {
  const host = document.getElementById('dispatch-kpis');
  if (!host) return;

  const dem = { cho: 0, xong: 0, 'thieu-trip': 0, 'thieu-hang': 0 };
  dsTrongNgay.forEach(d => {
    dispatchNhomCuaDO(d).forEach(n => { if (n in dem) dem[n] += 1; });
  });

  // Chọn nguồn xe bằng ĐỘ DÀI, không bằng `||`: một mảng rỗng là truthy trong
  // JavaScript, nên `driverShiftVehicles || fioriVehicles` trả về đúng mảng
  // rỗng khi màn này chưa nạp danh sách xe. Đã đo được: thẻ "Xe rảnh" hiện 0
  // trong khi cơ sở dữ liệu có 9 xe.
  const dsXe = dispatchDanhSachXe();
  const xeDangChay = new Set((driverVehicleAvailability || [])
    .filter(x => String(x.kind || '') === 'trip' && x.vehicle_id)
    .map(x => String(x.vehicle_id)));
  // Theo MA trang thai (moc 045), khong tim chuoi trong nhan. Xe ngoai doi
  // (`out_of_service`) khong tinh vao "ranh".
  const xeBaoDuong = dsXe.filter(v => String(v.operational_status || '') === 'maintenance').length;
  const xeNgoaiDoi = dsXe.filter(v => String(v.operational_status || '') === 'out_of_service').length;
  const xeChay = dsXe.filter(v => xeDangChay.has(String(v.id))
    || String(v.operational_status || '') === 'on_trip').length;
  const xeRanh = Math.max(0, dsXe.length - xeBaoDuong - xeChay - xeNgoaiDoi);

  // "Tài xế trong ca", KHÔNG phải "tài xế còn giờ lái" như bản mẫu: hệ thống
  // không lưu số giờ đã lái trong ngày của từng người, nên không tính được con
  // số đó. Đổi nhãn cho đúng thứ đo được, thay vì giữ nhãn của mẫu rồi điền
  // vào một con số nói chuyện khác.
  const taiXeTrongCa = new Set((driverShifts || [])
    .filter(c => String(c.availability_kind || 'work') === 'work' && c.driver_id)
    .map(c => String(c.driver_id))).size;
  const tongTaiXe = dispatchDanhSachTaiXe().length;

  const soNgoaiLe = document.querySelectorAll('#dispatch-calendar-conflicts .dispatch-alert-row').length;
  const excEl = document.getElementById('dispatch-exc-count');
  if (excEl) excEl.textContent = String(soNgoaiLe);

  const the = [
    ['', 'DO trong ngày', dsTrongNgay.length, dsHienRa + ' đang hiện', 'blue'],
    ['xong', 'Đã xuất bến', dem.xong, 'đang chạy hoặc đã xong', 'green'],
    ['cho', 'Chờ xếp', dem.cho, 'chưa xuất bến', 'amber'],
    ['thieu-trip', 'Thiếu Trip', dem['thieu-trip'], 'phải lập Trip trước', 'red'],
    // Hai thẻ cuối CHỈ ĐỂ ĐỌC: chúng nói về xe và người, không lọc được cột DO.
    // `null` làm chúng không bấm được, thay vì cho bấm rồi không có gì xảy ra.
    [null, 'Xe rảnh / tổng', xeRanh + '<span style="font-size:13px;color:#7b8796"> / ' + dsXe.length + '</span>',
      xeChay + ' chạy · ' + xeBaoDuong + ' bảo dưỡng', ''],
    [null, 'Tài xế trong ca', taiXeTrongCa, 'trên ' + tongTaiXe + ' người', ''],
  ];

  host.innerHTML = the.map(cap => {
    const ma = cap[0], nhan = cap[1], so = cap[2], phu = cap[3], mau = cap[4];
    const chiDoc = ma === null;
    const tat = !chiDoc && ma !== '' && !so;
    const soChu = (typeof so === 'number') ? Number(so).toLocaleString('vi-VN') : String(so);
    return '<button type="button" class="card kpi' + (mau ? ' ' + mau : '')
      + (dispatchKpiFilter === ma && !chiDoc ? ' on' : '') + '"'
      + (chiDoc || tat
        ? ' disabled title="' + (chiDoc ? 'Chỉ để xem' : 'Không có DO nào trong nhóm này') + '"'
        : ' onclick="setDispatchKpiFilter(\'' + ma + '\')" title="Bấm để lọc cột DO theo nhóm này"')
      + '>'
      + '<span>' + nhan + '</span><b>' + soChu + '</b><small>' + phu + '</small>'
      + '</button>';
  }).join('');
}

/* --------------------------------------------------------------------------
   CỘT 1 — DO chờ xếp, gom nhóm và mở gập được.
   -------------------------------------------------------------------------- */

//: Cách gom cột DO: theo tuyến, theo khách, hay theo hạn giao.
let dispatchDoGroup = 'route';
//: Nhóm nào đang mở. Mặc định mở nhóm ĐẦU TIÊN — mở hết thì cột dài mấy trăm
//: dòng và mất tác dụng gom; đóng hết thì người dùng phải bấm mới thấy gì.
let dispatchNhomMo = new Set();
//: DO đã tick, để "Xếp cả nhóm" và nút xếp hàng loạt biết chọn gì.
let dispatchDaTick = new Set();

window.setDispatchDoGroup = function (kieu) {
  dispatchDoGroup = ['route', 'customer', 'due'].includes(kieu) ? kieu : 'route';
  document.querySelectorAll('#dispatch-do-group-seg button').forEach(b =>
    b.classList.toggle('on', b.dataset.grp === dispatchDoGroup));
  dispatchNhomMo = new Set();
  renderDispatchDOs();
};

window.moNhomDO = function (khoa) {
  if (dispatchNhomMo.has(khoa)) dispatchNhomMo.delete(khoa);
  else dispatchNhomMo.add(khoa);
  renderDispatchDOs();
};

window.tickDO = function (ma, event) {
  if (event) event.stopPropagation();
  if (dispatchDaTick.has(ma)) dispatchDaTick.delete(ma);
  else dispatchDaTick.add(ma);
  const el = document.getElementById('dispatch-ticked-count');
  if (el) el.textContent = String(dispatchDaTick.size);
  capNhatNutXepTuDong();
};

/**
 * Bấm Enter hoặc Space trên một dòng DO thì mở dòng đó.
 *
 * Bản mẫu vẽ dòng này bằng một `<div>` chỉ có `onclick`, và thừa nguyên cách đó
 * là một bước lùi về trợ năng: người dùng bàn phím không tới được dòng nào.
 * Đặt cả dòng thành `<button>` cũng không được — trong dòng có sẵn một ô tick,
 * mà lồng một ô bấm được vào trong một nút là HTML không hợp lệ và trình đọc
 * màn hình đọc sai.
 *
 * Cách đúng cho một HÀNG có sẵn điều khiển riêng: `role="button"` +
 * `tabindex="0"` + bắt phím ở đây, còn ô tick giữ nguyên là ô tick.
 */
window.dpv2BamPhimDong = function (event, maDO) {
  if (!event) return;
  if (event.key !== 'Enter' && event.key !== ' ' && event.key !== 'Spacebar') return;
  // Bấm Space khi con trỏ đang ở ô tick thì để ô tick tự xử — chặn ở đây là
  // tick bằng bàn phím không dùng được nữa.
  const dich = event.target;
  if (dich && String(dich.tagName || '').toLowerCase() === 'input') return;
  event.preventDefault();
  window.selectDispatchDO(maDO);
};

/** Hạn giao còn lại, dạng "Còn 4h36" — cột `due` của bản mẫu. */
function dpv2ConLai(don) {
  const han = don.delivery_window_end || don.delivery_window_start
    || don.planned_arrival_at || don.delivery_date;
  if (!han) return { chu: '—', mau: '' };
  const d = new Date(han);
  if (isNaN(d)) return { chu: '—', mau: '' };
  const phut = Math.round((d.getTime() - Date.now()) / 60000);
  if (phut < 0) {
    const h = Math.floor(-phut / 60), m = (-phut) % 60;
    return { chu: 'Trễ ' + (h ? h + 'h' : '') + String(m).padStart(2, '0'), mau: 'r' };
  }
  const h = Math.floor(phut / 60), m = phut % 60;
  // Dưới sáu giờ là gấp (đỏ), dưới mười hai giờ là cần để ý (cam). Hai ngưỡng
  // này khớp với thực tế: một chuyến nội vùng mất khoảng một tới ba giờ, nên
  // còn dưới sáu giờ là đã sát.
  const mau = phut < 360 ? 'r' : (phut < 720 ? 'a' : '');
  return { chu: 'Còn ' + h + 'h' + String(m).padStart(2, '0'), mau: mau };
}

function renderDispatchDOs(filterQuery = '') {
  const container = document.getElementById('dispatch-do-list');
  if (!container) return;

  const query = filterQuery
    || normalizeSearchText(document.getElementById('dispatch-do-search-input')?.value || '').trim();

  const allDOsRaw = eplDeliveryOrders && eplDeliveryOrders.length > 0 ? eplDeliveryOrders : (dispatchDOs || []);
  renderDispatchDOSelector(allDOsRaw);
  let allDOs = allDOsRaw.filter(isDispatchPendingDO);
  const planningDate = selectedDispatchFleetIsoDate || dispatchDateInputValue(dispatchCalendarDate);
  const dateResult = window.TmsCockpit?.filterDispatchOrdersByDate
    ? window.TmsCockpit.filterDispatchOrdersByDate(allDOs, planningDate)
    : { orders: allDOs, undated: [] };
  allDOs = dateResult.orders;

  if (query) {
    allDOs = allDOs.filter(d =>
      normalizeSearchText([d.id, d.customer_id, d.route_id, d.origin, d.destination,
        d.packaging_spec, statusLabel(d.status || '')].join(' ')).includes(query));
  }

  // Dải số liệu đếm trên TOÀN BỘ đơn trong ngày, KHÔNG theo bộ lọc đang chọn.
  // Đếm theo bộ lọc thì bấm "Thiếu Trip" xong mọi thẻ khác về 0, và người dùng
  // mất luôn mốc để so — đó là dải số liệu tự xóa nghĩa của chính nó.
  const dsTrongNgay = allDOs.slice();
  if (dispatchKpiFilter) {
    allDOs = allDOs.filter(d => dispatchNhomCuaDO(d).has(dispatchKpiFilter));
  }
  renderDispatchKpis(dsTrongNgay, allDOs.length);
  renderDispatchFleet();
  renderDispatchCandHours();

  const pendingCountEl = document.getElementById('dispatch-state-pending-count');
  if (pendingCountEl) pendingCountEl.textContent = String(allDOs.length);
  capNhatNutXepTuDong(allDOs.length);

  const canhBaoThieuNgay = dateResult.undated.length
    ? '<div class="empty" style="margin:12px 14px;border-color:#f59e0b;color:#b45309">'
      + '<i class="fa-solid fa-triangle-exclamation"></i> ' + dateResult.undated.length
      + ' DO thiếu ngày lấy hàng nên chưa xuất hiện trong lịch. '
      + 'Hãy bổ sung thời gian trên DO trước khi điều phối.</div>'
    : '';

  if (!allDOs.length) {
    container.innerHTML = canhBaoThieuNgay
      + '<div class="empty" style="margin:12px 14px;">'
      + (query ? 'Không tìm thấy lệnh giao hàng phù hợp'
        : (dispatchKpiFilter ? 'Không có DO nào trong nhóm đang lọc. Bấm lại thẻ số liệu để bỏ lọc.'
          : 'Chưa có lệnh giao hàng sẵn sàng điều phối'))
      + ' ngày ' + planningDate + '</div>';
    const foot = document.getElementById('dispatch-do-foot');
    if (foot) foot.textContent = '0 DO';
    return;
  }

  // GOM NHÓM. Vì sao gom theo tuyến là mặc định: một Trip chỉ chở được các DO
  // CÙNG một tuyến — đó là chốt của backend, không phải một quy ước trình bày.
  // Danh sách phẳng buộc người điều phối tự đọc mã tuyến từng dòng rồi tự nhóm
  // trong đầu; ở quy mô vài trăm DO mỗi ngày thì việc đó vừa chậm vừa dễ ghép
  // sai tuyến rồi bị backend từ chối sau khi đã điền xong cả form.
  const nhom = new Map();
  allDOs.forEach(d => {
    let khoa, ten, phu;
    if (dispatchDoGroup === 'customer') {
      khoa = String(d.customer_id || '').trim() || '(chưa có khách)';
      const kh = (eplCustomers || []).find(c => String(c.id || '') === khoa);
      ten = (kh && kh.name) || khoa;
      phu = '';
    } else if (dispatchDoGroup === 'due') {
      const c = dpv2ConLai(d);
      khoa = c.mau === 'r' ? 'gap' : (c.mau === 'a' ? 'som' : 'con-thoi-gian');
      ten = khoa === 'gap' ? 'Gấp — còn dưới 6 giờ'
        : (khoa === 'som' ? 'Cần để ý — còn dưới 12 giờ' : 'Còn thời gian');
      phu = '';
    } else {
      khoa = String(d.route_id || d.route_name || '').trim() || '(chưa có tuyến)';
      const t = (eplRoutes || []).find(r => String(r.id || '') === khoa);
      ten = (t && t.name) || khoa;
      phu = (t && t.distance_km)
        ? Number(t.distance_km).toLocaleString('vi-VN') + ' km'
        : '';
    }
    if (!nhom.has(khoa)) nhom.set(khoa, { ten: ten, phu: phu, ds: [] });
    nhom.get(khoa).ds.push(d);
  });

  // Nhóm nhiều DO nhất xếp lên trước: đó là nhóm ghép được nhiều nhất vào một
  // chuyến, tức việc đáng làm trước.
  const dsNhom = [...nhom.entries()].sort((a, b) => b[1].ds.length - a[1].ds.length);
  // Mặc định mở nhóm đầu. Mở hết thì cột dài mấy trăm dòng và mất tác dụng gom;
  // đóng hết thì người dùng phải bấm mới thấy gì.
  if (!dispatchNhomMo.size && dsNhom.length) dispatchNhomMo.add(dsNhom[0][0]);

  const html = dsNhom.map(cap => {
    const khoa = cap[0], g = cap[1];
    const mo = dispatchNhomMo.has(khoa);
    const tongKg = g.ds.reduce((t, x) => t + Number(x.weight_kg || 0), 0);
    const soGap = g.ds.filter(x => dpv2ConLai(x).mau === 'r').length;
    const soThieuTrip = g.ds.filter(x => resolveDispatchTripGate(x.id).state === 'missing').length;

    let theNhom = '';
    if (soGap) theNhom = '<span class="tag t-red">' + soGap + ' gấp</span>';
    else if (soThieuTrip) theNhom = '<span class="tag t-amber">' + soThieuTrip + ' thiếu Trip</span>';
    else theNhom = '<span></span>';

    // Chỉ mời "Xếp cả nhóm" khi nhóm có TỪ HAI DO: một DO thì nút đó chỉ là một
    // đường vòng tới cùng việc mà bấm vào chính dòng đó đã làm được.
    const nutNhom = g.ds.length > 1
      ? '<button type="button" class="btn" onclick="xepCaNhomDO(' + JSON.stringify(khoa).replace(/"/g, '&quot;') + ');event.stopPropagation()"'
        + ' title="Tick cả ' + g.ds.length + ' DO của nhóm này rồi mở form tạo Trip">Xếp cả nhóm</button>'
      : '<span></span>';

    const dong = g.ds.map(d => {
      const cong = resolveDispatchTripGate(d.id);
      const theTrip = cong.state === 'ready'
        ? '<span class="tag t-green">Trip ' + escapeHtml(String(cong.trip.id)) + '</span>'
        : (cong.state === 'draft'
          ? '<span class="tag t-amber">Trip nháp</span>'
          : '<span class="tag t-red">Chưa có Trip</span>');
      const kh = (eplCustomers || []).find(c => String(c.id || '') === String(d.customer_id || ''));
      const tenKH = (kh && kh.name) || d.customer_id || '—';
      const conLai = dpv2ConLai(d);
      const maAn = JSON.stringify(String(d.id)).replace(/"/g, '&quot;');
      return '<div class="row' + (String(selectedDispatchCalendarOrderId) === String(d.id) ? ' on' : '') + '"'
        + ' data-dispatch-do="' + escapeHtml(String(d.id)) + '"'
        + ' data-dispatch-queue="' + escapeHtml(String(d.id)) + '"'
        + ' draggable="true" ondragstart="onDispatchDODragStart(event, ' + maAn + ')"'
        + ' onclick="selectDispatchDO(' + maAn + ')"'
        + ' role="button" tabindex="0"'
        + ' onkeydown="dpv2BamPhimDong(event, ' + maAn + ')"'
        + ' aria-label="Chọn DO ' + escapeHtml(String(d.id)) + ' để gán xe và tổ lái"'
        + ' title="Bấm để gán xe và tổ lái cho ' + escapeHtml(String(d.id)) + '">'
        + '<input type="checkbox"' + (dispatchDaTick.has(String(d.id)) ? ' checked' : '')
        + ' onclick="tickDO(' + maAn + ', event)" aria-label="Tick DO ' + escapeHtml(String(d.id)) + '">'
        + '<div><div class="id">' + escapeHtml(String(d.id)) + '</div>'
        + '<div class="m">' + escapeHtml(tenKH)
        + (d.quotation_id ? ' · ' + escapeHtml(String(d.quotation_id)) : '') + '</div></div>'
        // Giờ lấy và giờ giao gộp vào MỘT ô hai dòng. Cột DO nay hẹp lại để
        // nhường chỗ cho cột giữa, và sáu ô ngang trong khoảng đó thì mỗi ô
        // còn chưa tới 70px — chữ bị cắt hết. Cùng lượng thông tin, xếp theo
        // chiều dọc thay vì chiều ngang.
        + '<div><div>Lấy ' + (dpv2Gio(d.pickup_window_start || d.pickup_date) || '—')
        + ' · ' + escapeHtml(String(d.origin || '—')) + '</div>'
        + '<div class="m">Giao ' + (dpv2Gio(d.delivery_window_start || d.delivery_date) || '—')
        + ' · ' + escapeHtml(String(d.destination || '—')) + '</div></div>'
        + '<div><span class="due ' + conLai.mau + '">' + conLai.chu + '</span>'
        + theTrip + '</div>'
        + '</div>';
    }).join('');

    return '<div class="grp' + (mo ? ' open' : '') + '">'
      + '<button type="button" class="grp-h" onclick="moNhomDO(' + JSON.stringify(khoa).replace(/"/g, '&quot;') + ')"'
      + ' aria-expanded="' + (mo ? 'true' : 'false') + '">'
      + '<span class="car">&#9654;</span>'
      + '<div class="nm">' + escapeHtml(g.ten)
      + (g.phu ? ' <span>' + escapeHtml(g.phu) + '</span>' : '') + '</div>'
      // Số DO, thẻ cảnh báo và nút xếp gộp vào MỘT ô bên phải, tự xuống dòng
      // khi chật — thay vì ba ô riêng tranh nhau chỗ ngang và đẩy nhau ra
      // ngoài khung khi tên tuyến dài.
      + '<span class="rt"><span class="cnt">' + g.ds.length + ' DO · '
      + tongKg.toLocaleString('vi-VN') + ' kg</span>'
      + theNhom + nutNhom + '</span>'
      + '</button>'
      + '<div class="rows">' + dong + '</div></div>';
  }).join('');

  container.innerHTML = canhBaoThieuNgay + html;
  const foot = document.getElementById('dispatch-do-foot');
  if (foot) {
    foot.textContent = allDOs.length + ' DO · ' + dsNhom.length + ' nhóm · sắp theo số DO';
  }
  const tickEl = document.getElementById('dispatch-ticked-count');
  if (tickEl) tickEl.textContent = String(dispatchDaTick.size);
}

/* --------------------------------------------------------------------------
   CỘT 2a — đội xe theo bãi, khi chưa chọn DO.
   -------------------------------------------------------------------------- */

function renderDispatchFleet() {
  const host = document.getElementById('dispatch-fleet-list');
  if (!host) return;
  const dsXe = dispatchDanhSachXe();
  const tongEl = document.getElementById('dispatch-fleet-total');
  if (tongEl) tongEl.textContent = String(dsXe.length);

  const xeDangChay = new Set((driverVehicleAvailability || [])
    .filter(x => String(x.kind || '') === 'trip' && x.vehicle_id)
    .map(x => String(x.vehicle_id)));

  const theoBai = new Map();
  dsXe.forEach(v => {
    const bai = String(v.depot_name || v.depot || '').trim() || '(chưa gán bãi)';
    if (!theoBai.has(bai)) theoBai.set(bai, []);
    theoBai.get(bai).push(v);
  });

  const phanLoai = ds => {
    let ranh = 0, chay = 0, baoDuong = 0;
    ds.forEach(v => {
      const tt = String(v.operational_status || '');
      if (tt === 'maintenance' || tt === 'out_of_service') baoDuong += 1;
      else if (xeDangChay.has(String(v.id)) || tt === 'on_trip') chay += 1;
      else ranh += 1;
    });
    return { ranh: ranh, chay: chay, baoDuong: baoDuong, tong: ds.length };
  };

  const thanh = p => {
    const pc = n => p.tong ? (n / p.tong * 100).toFixed(1) + '%' : '0%';
    return '<div class="stack">'
      + '<i style="width:' + pc(p.ranh) + ';background:#15803d"></i>'
      + '<i style="width:' + pc(p.chay) + ';background:#7c3aed"></i>'
      + '<i style="width:' + pc(p.baoDuong) + ';background:#cbd5e1"></i></div>';
  };

  // Bãi nhiều xe nhất lên trước, và trong mỗi bãi thì tách theo LOẠI XE — người
  // điều phối không hỏi "bãi này có bao nhiêu xe", họ hỏi "bãi này còn đầu kéo
  // 40 nào rảnh không".
  const dsBai = [...theoBai.entries()].sort((a, b) => b[1].length - a[1].length);
  host.innerHTML = dsBai.map(cap => {
    const bai = cap[0], ds = cap[1];
    const p = phanLoai(ds);
    const dong = ['<button type="button" class="team" onclick="chonBaiDieuPhoi(' + JSON.stringify(bai).replace(/"/g, '&quot;') + ')"'
      + ' title="Bấm để giới hạn phạm vi về bãi này">'
      + '<div class="nm">' + escapeHtml(bai) + '<span>' + p.tong + ' xe</span></div>'
      + '<div class="tot">' + p.tong + '<span>xe</span></div>'
      + '<div>' + thanh(p)
      + '<div class="lg"><span><i style="background:#15803d"></i>' + p.ranh + ' rảnh</span>'
      + '<span><i style="background:#7c3aed"></i>' + p.chay + ' chạy</span>'
      + '<span><i style="background:#cbd5e1"></i>' + p.baoDuong + ' bảo dưỡng</span></div></div>'
      + '<div class="free">' + p.ranh + '<span>rảnh</span></div>'
      + '</button>'];

    const theoLoai = new Map();
    ds.forEach(v => {
      const loai = tenLoaiXe(v.type) || '(chưa gán loại)';
      if (!theoLoai.has(loai)) theoLoai.set(loai, []);
      theoLoai.get(loai).push(v);
    });
    [...theoLoai.entries()].sort((a, b) => b[1].length - a[1].length).forEach(c => {
      const q = phanLoai(c[1]);
      dong.push('<button type="button" class="team sub" onclick="chonLoaiXeDieuPhoi(' + JSON.stringify(c[0]).replace(/"/g, '&quot;') + ')"'
        + ' title="Bấm để giới hạn phạm vi về loại xe này">'
        + '<div class="nm">' + escapeHtml(c[0]) + '<span>' + q.tong + ' xe</span></div>'
        + '<div class="tot">' + q.tong + '<span>xe</span></div>'
        + '<div>' + thanh(q) + '</div>'
        + '<div class="free">' + q.ranh + '<span>rảnh</span></div>'
        + '</button>');
    });
    return dong.join('');
  }).join('') || '<div class="empty" style="margin:12px 14px">Chưa có xe nào trong danh mục.</div>';
}

window.chonBaiDieuPhoi = function (bai) {
  const el = document.getElementById('dispatch-scope-depot');
  if (el) { el.value = bai; window.setDispatchScope(); }
};
window.chonLoaiXeDieuPhoi = function (loai) {
  const el = document.getElementById('dispatch-scope-type');
  if (el) { el.value = loai; window.setDispatchScope(); }
};

/* --------------------------------------------------------------------------
   CỘT 2b — Gantt xe ứng viên, khi đã chọn DO.
   -------------------------------------------------------------------------- */

function renderDispatchCandidates() {
  const khungEl = document.getElementById('dispatch-cand');
  const fleetEl = document.getElementById('dispatch-fleetview');
  const hop = document.getElementById('dispatch-cand-list');
  if (!khungEl || !hop) return;

  const maDO = selectedDispatchCalendarOrderId
    || (document.getElementById('dispatch-selected-do') || {}).value || '';
  const don = (eplDeliveryOrders || []).find(d => String(d.id) === String(maDO));

  // Chưa chọn DO thì hiện tổng quan đội xe, đúng như bản mẫu: "ứng viên" là ứng
  // viên CHO một đơn, không có đơn thì không có tiêu chí nào để xếp hạng.
  khungEl.hidden = !don;
  if (fleetEl) fleetEl.hidden = Boolean(don);
  if (!don) return;

  renderDispatchCandHours();
  const gio = khungGioLayHang(don);
  let ds = dispatchDanhSachXe().slice();
  const tong = ds.length;
  if (dispatchScope.depot) ds = ds.filter(v => String(v.depot_name || v.depot || '') === dispatchScope.depot);
  if (dispatchScope.type) ds = ds.filter(v => (tenLoaiXe(v.type) || v.type) === dispatchScope.type);

  let cham = ds.map(xe => Object.assign({ xe: xe }, chamDiemXe(xe, don, gio)));
  if (!dispatchCandNoiDieuKien) {
    const dieuDuoc = cham.filter(c => !c.chan);
    // Chỉ siết khi thật sự còn xe — siết đến trống rỗng thì màn hình không nói
    // được điều gì, mà điều phối viên vẫn phải điều cho xong đơn.
    if (dieuDuoc.length) cham = dieuDuoc;
  }

  const xepTheo = {
    score: (a, b) => b.diem - a.diem || String(a.xe.id).localeCompare(String(b.xe.id)),
    depot: (a, b) => (Number(b.cungBai) - Number(a.cungBai)) || b.diem - a.diem,
    free: (a, b) => (a.dangChay.length - b.dangChay.length) || b.diem - a.diem,
  };
  cham.sort(xepTheo[dispatchCandSort] || xepTheo.score);

  const demEl = document.getElementById('dispatch-cand-count');
  if (demEl) demEl.textContent = String(cham.length);

  const whyEl = document.getElementById('dispatch-cand-why');
  if (whyEl) {
    const dk = [];
    if (Number(don.weight_kg || 0)) {
      dk.push('chở nổi <b>' + Number(don.weight_kg).toLocaleString('vi-VN') + ' kg</b>');
    }
    if (don.origin) dk.push('gần <b>' + escapeHtml(String(don.origin)) + '</b>');
    if (gio) dk.push('rảnh <b>' + dpv2Gio(gio.tu) + '–' + dpv2Gio(gio.den) + '</b>');
    dk.push('<b>có tài xế trong ca</b>');
    whyEl.innerHTML = 'Lọc từ <b>' + tong + ' xe</b> còn <b>' + cham.length + '</b> cho <b>'
      + escapeHtml(String(don.id)) + '</b>: ' + dk.join(' · ') + '. '
      + '<button type="button" onclick="noiDieuKienUngVien()">'
      + (dispatchCandNoiDieuKien ? 'Siết lại điều kiện' : 'Nới điều kiện')
      + '</button> · Bấm vào dòng xe để gán xe và tổ lái.';
  }

  if (!cham.length) {
    hop.innerHTML = '<div class="empty" style="margin:10px 0">'
      + 'Không có xe nào trong phạm vi đang chọn. Bỏ giới hạn bãi hoặc loại xe ở đầu màn, '
      + 'hoặc bấm "Nới điều kiện" để xem cả xe chưa hoàn toàn vừa.</div>';
    return;
  }

  const maXeDangChon = (document.getElementById('dispatch-vehicle') || {}).value || '';
  const dsTaiXe = dispatchDanhSachTaiXe();
  const bayGio = dpv2ViTri(new Date());
  const vachBayGio = (bayGio !== null && bayGio >= 0 && bayGio <= 100)
    ? '<div class="now" style="left:' + bayGio.toFixed(2) + '%"></div>' : '';

  hop.innerHTML = cham.slice(0, 60).map(c => {
    const bac = c.chan ? 'r' : (c.diem >= 80 ? 'g' : (c.diem >= 55 ? 'a' : 'r'));
    // CHỈ lấy ca của ĐÚNG chiếc xe này. Trước đây có một bước dự phòng lấy
    // người đầu tiên đang trong ca ở BẤT KỲ xe nào, nên mọi dòng đều hiện cùng
    // một tên, như thể anh ấy lái được cả bảy chiếc cùng lúc. Đó là một con số
    // nói dối, và bấm vào thì gán sai người vào chuyến.
    const caChinh = c.ca.cuaXe[0] || null;
    const nguoiChinh = caChinh ? dsTaiXe.find(t => String(t.id) === String(caChinh.driver_id)) : null;
    const tenChinh = (nguoiChinh && nguoiChinh.name) || (caChinh && caChinh.driver_id) || '';
    const caPhu = c.ca.cuaXe[1] || null;
    const nguoiPhu = caPhu ? dsTaiXe.find(t => String(t.id) === String(caPhu.driver_id)) : null;
    const tenPhu = (nguoiPhu && nguoiPhu.name) || (caPhu && caPhu.driver_id) || '';
    const conNguoiRanh = c.ca.cuaXe.length ? 0 : c.ca.tatCa.length;

    let the;
    if (c.chan === 'bảo dưỡng') the = '<span class="st tag">Bảo dưỡng</span>';
    else if (c.chan === 'trùng chuyến' || c.dangChay.length) the = '<span class="st tag t-blue">Đang chạy</span>';
    else if (c.chan) the = '<span class="st tag t-red">' + escapeHtml(c.chan) + '</span>';
    else the = '<span class="st tag t-green">Rảnh</span>';

    const kieuCa = { morning: ['s', 'Ca sáng 06–14'], afternoon: ['c', 'Ca chiều 14–22'], night: ['d', 'Ca đêm 22–06'] };
    const kc = caChinh ? kieuCa[String(caChinh.shift_type || '')] : null;
    const nhanCa = kc ? '<span class="shift ' + kc[0] + '">' + kc[1] + '</span> ' : '';

    const suc = Number(c.xe.weight_capacity || 0);
    const dongPhu = nhanCa + [
      escapeHtml(tenLoaiXe(c.xe.type)),
      c.xe.depot ? escapeHtml(String(c.xe.depot)) : '',
      suc ? (suc / 1000).toLocaleString('vi-VN') + ' T' : '',
      c.lyDo.length ? c.lyDo.join(', ') : '',
    ].filter(Boolean).join(' · ');

    // Thanh việc đã xếp trên làn giờ. Vẽ từ `vehicle-availability` thật: chuyến
    // màu tím, bảo dưỡng là vùng gạch chéo — đúng bảng màu của bản mẫu.
    const thanhViec = viecDaXepCuaXe(c.xe.id, null).map(v => {
      const l = dpv2ViTri(v.khung.tu), r = dpv2ViTri(v.khung.den);
      if (l === null || r === null) return '';
      const trai = Math.max(0, Math.min(100, l));
      const rong = Math.max(3, Math.min(100 - trai, r - l));
      const goi = escapeHtml(String(v.origin || '') + (v.destination ? ' → ' + v.destination : ''))
        + ' · ' + dpv2Gio(v.khung.tu) + '–' + dpv2Gio(v.khung.den);
      if (String(v.kind || '') === 'maintenance') {
        return '<div class="maint" style="left:' + trai.toFixed(2) + '%;right:auto;width:' + rong.toFixed(2) + '%"'
          + ' title="' + escapeHtml(String(v.maintenance_label || 'Bảo dưỡng')) + '">Bảo dưỡng</div>';
      }
      return '<div class="bar b-purple" style="left:' + trai.toFixed(2) + '%;width:' + rong.toFixed(2) + '%"'
        + ' title="' + goi + '">' + dpv2Gio(v.khung.tu)
        + '<small>' + dpv2Gio(v.khung.den) + '</small></div>';
    }).join('');

    // Khung giờ của chuyến ĐANG XẾP, vẽ nét đứt — để người điều phối thấy ngay
    // nó có chồng lên việc nào của xe hay không, thay vì phải tự so hai giờ.
    const bongChuyen = (gio && !c.chan) ? (() => {
      const l = dpv2ViTri(gio.tu), r = dpv2ViTri(gio.den);
      if (l === null || r === null) return '';
      const trai = Math.max(0, Math.min(100, l));
      const rong = Math.max(4, Math.min(100 - trai, r - l));
      return '<div class="bar b-ghost" style="left:' + trai.toFixed(2) + '%;width:' + rong.toFixed(2) + '%"'
        + ' title="Chuyến đang xếp · ' + dpv2Gio(gio.tu) + '–' + dpv2Gio(gio.den) + '">'
        + 'Đang xếp<small>' + dpv2Gio(gio.tu) + '</small></div>';
    })() : '';

    const nhanBam = c.chan ? '' : ' onclick="chonXeUngVien('
      + JSON.stringify(String(c.xe.id)).replace(/"/g, '&quot;') + ','
      + JSON.stringify(String((caChinh && caChinh.driver_id) || '')).replace(/"/g, '&quot;') + ','
      + JSON.stringify(String((caPhu && caPhu.driver_id) || '')).replace(/"/g, '&quot;') + ')"';

    return '<div class="g-row' + (c.chan ? ' dim' : '')
      + (String(maXeDangChon) === String(c.xe.id) ? ' pick' : '') + '"'
      + nhanBam
      + (c.chan ? '' : ' tabindex="0" role="button"'
        + ' onkeydown="if(event.key===\'Enter\'){event.preventDefault();this.click();}"')
      + ' title="' + (c.chan ? 'Không điều được: ' + escapeHtml(c.chan)
        : (c.lyDo.length ? 'Trừ điểm vì: ' + escapeHtml(c.lyDo.join(', ')) : 'Phù hợp mọi tiêu chí')) + '">'
      + '<div class="veh">'
      + '<div class="sc ' + bac + '">' + (c.chan ? '—' : c.diem)
      + '<small>' + (c.chan ? escapeHtml(c.chan) : 'điểm') + '</small></div>'
      // Biển số và VÒNG TRÒN TỔ LÁI là hai thứ NGANG HÀNG trong một hàng flex,
      // không phải tổ lái nằm bên trong biển số. Bản mẫu lồng `.vcrew` vào
      // trong thẻ `<b>` đang mang `white-space:nowrap; overflow:hidden` — và đo
      // trên màn thật thì hai vòng tròn tụt xuống dòng dưới, làm mỗi dòng xe
      // cao hơn 58px và các dòng chồng lên nhau.
      + '<div class="g"><div class="ln">'
      + '<b>' + escapeHtml(String(c.xe.id))
      + (tenChinh ? ' · ' + escapeHtml(tenChinh) : '') + '</b>'
      + '<span class="vcrew">'
      + '<i' + (tenChinh ? '' : ' class="q"') + ' title="'
      + (tenChinh ? escapeHtml(tenChinh) + ' · tài xế chính' : 'Chưa có tài xế chính') + '">'
      + (tenChinh ? chuCaiTen(tenChinh) : '+') + '</i>'
      + '<i' + (tenPhu ? '' : ' class="q"') + ' title="'
      + (tenPhu ? escapeHtml(tenPhu) + ' · phụ xe' : 'Chưa có phụ xe (không bắt buộc)') + '">'
      + (tenPhu ? chuCaiTen(tenPhu) : '+') + '</i>'
      + '</span></div>'
      + '<span>' + dongPhu
      + (conNguoiRanh ? ' · ' + conNguoiRanh + ' tài xế đang trong ca' : '')
      + '</span></div>'
      + the
      + '</div>'
      + '<div class="lane">' + vachBayGio + thanhViec + bongChuyen + '</div>'
      + '</div>';
  }).join('');
}

/* --------------------------------------------------------------------------
   CỘT 3 — đổi giữa danh sách ngoại lệ và khung gán.
   -------------------------------------------------------------------------- */

/**
 * Bốn ô tóm tắt đơn ở đầu khung gán — đúng khối `.sum` của bản mẫu.
 *
 * Vì sao khối này phải có: dòng DO ở cột một chỉ hiện sáu cột (mã, khách, giờ
 * lấy, giờ giao, hạn, Trip). Khối lượng, số pallet và quy cách hàng KHÔNG nằm
 * ở đó — bản mẫu cũng vậy, nó để những thứ đó sang cột phải. Nhưng người điều
 * phối phải thấy được khối lượng trước khi chốt xe, không thì họ gán một
 * container 30 tấn cho xe tải 15 tấn rồi bị máy chủ từ chối.
 */
function dpv2VeTomTatDon(don) {
  const host = document.getElementById('dispatch-calendar-detail-summary');
  if (!host) return;
  const maDO = selectedDispatchCalendarOrderId
    || (document.getElementById('dispatch-selected-do') || {}).value || '';
  const d = don || (eplDeliveryOrders || []).find(x => String(x.id) === String(maDO));
  if (!d) { host.innerHTML = ''; return; }

  const kh = (eplCustomers || []).find(c => String(c.id || '') === String(d.customer_id || ''));
  const tuyen = (eplRoutes || []).find(r => String(r.id || '') === String(d.route_id || ''));
  const nang = Number(d.weight_kg || 0);
  const pallet = Number(d.pallet_count || 0);
  const hang = [
    nang ? nang.toLocaleString('vi-VN') + ' kg' : '',
    pallet ? pallet + ' pallet' : '',
    d.packaging_spec ? String(d.packaging_spec) : '',
  ].filter(Boolean).join(' · ');

  const o = (nhan, giaTri, ma) => '<div><span>' + escapeHtml(nhan) + '</span><b'
    + (ma ? ' class="dispatch-do-' + ma + '"' : '') + '>'
    + escapeHtml(String(giaTri || '—')) + '</b></div>';

  host.innerHTML = o('DO đã chọn', d.id, 'code')
    + o('Khách hàng', (kh && kh.name) || d.customer_id, 'customer')
    + o('Tuyến (Dữ liệu gốc)',
      (tuyen && tuyen.name) || d.route_id
        || [d.origin, d.destination].filter(Boolean).join(' → '), 'route')
    // Chưa khai hàng thì nói THẲNG, đừng để một dấu gạch: khi khối lượng bằng
    // không thì máy chủ không kiểm được tải trọng, và mọi xe đều "vừa".
    + o('Hàng', hang || 'chưa khai khối lượng', 'cargo')
    + o('Lấy hàng', deliveryOrderDateLabel(d.pickup_window_start || d.pickup_date), 'pickup')
    + o('Giao hàng', deliveryOrderDateLabel(d.delivery_window_start || d.delivery_date), 'delivery')
    + o('Tải trọng', nang ? nang.toLocaleString('vi-VN') + ' kg' : 'chưa khai', 'weight')
    + o('Số pallet', pallet ? pallet + ' pallet' : 'chưa khai', 'pallet');
}

/** Đổi cột phải sang khung gán, hoặc về danh sách ngoại lệ. */
function dpv2MoKhungGan(coDon) {
  const exc = document.getElementById('dispatch-exceptions-view');
  const chiTiet = document.getElementById('dispatch-detail');
  const tieuDe = document.getElementById('dispatch-panel-title');
  const buoc = document.getElementById('dispatch-panel-step');
  const demExc = document.getElementById('dispatch-exc-count');
  if (exc) exc.hidden = Boolean(coDon);
  if (chiTiet) chiTiet.hidden = !coDon;
  if (demExc) demExc.hidden = Boolean(coDon);
  if (tieuDe) {
    const nhan = tieuDe.querySelector('span:not(.n)');
    if (nhan) nhan.textContent = coDon ? 'Gán xe và tổ lái' : 'Ngoại lệ cần duyệt';
    const bieuTuong = tieuDe.querySelector('i');
    if (bieuTuong) {
      bieuTuong.className = coDon ? 'fa-solid fa-id-card' : 'fa-solid fa-triangle-exclamation';
    }
  }
  if (buoc) {
    buoc.textContent = coDon
      ? String(selectedDispatchCalendarOrderId || '')
      : 'việc của điều phối viên';
  }
  // Cap nhat hai dong to lai VA trang thai nut chot ngay khi mo khung. Khong
  // goi o day thi nut "Chot dieu phoi" bam duoc tu dau, va bam vao thi may chu
  // tu choi vi chua co xe — mot loi ma man hinh von da biet truoc.
  if (coDon) { dpv2VeTomTatDon(); dpv2VeToLai(); }
}

window.boChonDODieuPhoi = function () {
  selectedDispatchCalendarOrderId = '';
  dispatchDetailUnlocked = false;
  const o = document.getElementById('dispatch-selected-do');
  if (o) o.value = '';
  dpv2MoKhungGan(false);
  renderDispatchCandidates();
  renderDispatchDOs();
};

/**
 * Đồng bộ hai nút tổ lái với hai ô ẩn.
 *
 * Bản mẫu vẽ tổ lái thành hai dòng có avatar và tên. Nhưng các hàm cũ đọc và
 * ghi tên người vào `#dispatch-driver-display` — nên phần hiển thị và phần lưu
 * là hai chỗ khác nhau, và phải chép qua sau mỗi lần đổi. Không chép thì nút
 * vẫn ghi "Chọn xe trước" trong khi tài xế đã được gán.
 */
function dpv2VeToLai() {
  const cap = [
    ['dispatch-driver', 'dispatch-driver-display', 'dispatch-driver-display-btn', 'Chọn xe trước'],
    ['dispatch-co-driver', 'dispatch-co-driver-display', 'dispatch-co-driver-display-btn', '—'],
  ];
  cap.forEach(c => {
    const ma = (document.getElementById(c[0]) || {}).value || '';
    const ten = (document.getElementById(c[1]) || {}).value || '';
    const nut = document.getElementById(c[2]);
    if (!nut) return;
    if (!ma) {
      nut.className = 'who empty';
      nut.textContent = c[3];
      return;
    }
    const nguoi = dispatchDanhSachTaiXe().find(t => String(t.id) === String(ma));
    const hienThi = (nguoi && nguoi.name) || ten || ma;
    nut.className = 'who';
    nut.innerHTML = '<span class="av">' + escapeHtml(chuCaiTen(hienThi)) + '</span>'
      + '<span style="min-width:0"><b>' + escapeHtml(hienThi) + '</b>'
      + '<span>' + escapeHtml(String((nguoi && nguoi.license_type) || ma)) + '</span></span>';
  });

  // Dòng "Chốt điều phối" chỉ bấm được khi đã có ĐỦ xe và tài xế chính. Cho bấm
  // khi còn thiếu thì máy chủ từ chối, và người dùng phải đọc một lỗi để biết
  // điều mà màn hình đã biết từ đầu.
  const coXe = Boolean((document.getElementById('dispatch-vehicle') || {}).value);
  const coTaiXe = Boolean((document.getElementById('dispatch-driver') || {}).value);
  const nut = document.getElementById('dispatch-submit-btn');
  if (nut) {
    nut.disabled = !(coXe && coTaiXe);
    nut.textContent = coXe
      ? (coTaiXe ? 'Chốt điều phối & xuất bến' : 'Chọn tài xế chính để chốt')
      : 'Chọn xe để chốt';
  }
  const kiem = document.getElementById('dispatch-check');
  if (kiem) {
    kiem.hidden = !(coXe || coTaiXe);
    kiem.className = 'check ' + (coXe && coTaiXe ? 'ok' : 'bad');
    kiem.textContent = coXe && coTaiXe
      ? '\u2713 Đủ xe và tài xế chính, chốt được.'
      : (coXe ? 'Còn thiếu tài xế chính.' : 'Còn thiếu xe.');
  }
}

/* --------------------------------------------------------------------------
   Nút ngày và nút xếp hàng loạt ở đầu trang.
   -------------------------------------------------------------------------- */

window.veHomNayDieuPhoi = function () {
  const homNay = new Date();
  const iso = homNay.getFullYear() + '-'
    + String(homNay.getMonth() + 1).padStart(2, '0') + '-'
    + String(homNay.getDate()).padStart(2, '0');
  if (typeof setDispatchCalendarDate === 'function') setDispatchCalendarDate(iso);
};

function capNhatNutXepTuDong(soConLai) {
  const nut = document.getElementById('dispatch-auto-btn');
  const nhan = document.getElementById('dispatch-auto-label');
  if (!nut || !nhan) return;
  const soTick = dispatchDaTick.size;
  if (soTick) {
    nhan.textContent = 'Xếp ' + soTick + ' DO đã tick';
    nut.disabled = false;
    return;
  }
  const con = (typeof soConLai === 'number')
    ? soConLai
    : document.querySelectorAll('#dispatch-do-list .row').length;
  nhan.textContent = con ? 'Xếp ' + con + ' DO còn lại' : 'Không còn DO nào chờ';
  nut.disabled = !con;
}

/**
 * Nút "Xếp DO còn lại" ở đầu trang.
 *
 * Bản mẫu gọi nút này "Xếp tự động" và vẽ một thanh tiến trình chạy nền. Hệ
 * thống KHÔNG có đường API nào xếp hàng loạt, nên ở đây nó làm một việc THẬT
 * bằng backend đang có: mở hộp thoại tạo Trip với các DO đã tick — hoặc, nếu
 * chưa tick gì, với mọi DO đang hiện. Một thanh tiến trình giả thì đẹp hơn
 * nhưng nó không xếp được chuyến nào.
 */
window.xepMoiDOConLai = function () {
  const dsHien = [...document.querySelectorAll('#dispatch-do-list .row')]
    .map(r => r.getAttribute('data-dispatch-do')).filter(Boolean);
  const chon = dispatchDaTick.size ? [...dispatchDaTick] : dsHien;
  if (!chon.length) {
    if (typeof showToast === 'function') showToast('Không còn DO nào chờ điều phối.', 'info');
    return;
  }
  const ds = (eplDeliveryOrders || []).filter(d => chon.includes(String(d.id)));
  // Một Trip chỉ chở được các DO CÙNG một tuyến — đó là chốt của backend. Nói
  // trước ở đây, thay vì để người dùng điền xong cả form rồi bị từ chối.
  const soTuyen = new Set(ds.map(d => String(d.route_id || d.route_name || ''))).size;
  if (soTuyen > 1) {
    if (typeof showToast === 'function') {
      showToast(chon.length + ' DO đang chọn thuộc ' + soTuyen + ' tuyến khác nhau. '
        + 'Một Trip chỉ chở được các DO cùng tuyến — hãy bấm "Xếp cả nhóm" trên từng nhóm tuyến.', 'error');
    }
    return;
  }
  if (typeof switchView === 'function') switchView('delivery-shipment');
  if (typeof openTripReturnAction === 'function') openTripReturnAction('create-trip', ds);
};



/* ==========================================================================
   XE ỨNG VIÊN — cột giữa của bản mẫu `dispatch-v2-crew.html`.

   Mục đích: khi điều phối viên chọn một DO, màn hình phải TỰ nói "trong 500 xe
   thì mấy chiếc này điều được, và vì sao chiếc đầu tiên là tốt nhất". Bảng danh
   mục xe không trả lời được câu đó — nó liệt kê xe theo thứ tự nhập, còn ở đây
   thứ tự chính là câu trả lời.

   Điểm phù hợp tính từ dữ liệu THẬT, mỗi tiêu chí là một cột trong cơ sở dữ
   liệu, không có tiêu chí nào bịa:

     · tải trọng xe so với khối lượng đơn      (vehicles.weight_capacity / DO.weight_kg)
     · bãi đỗ so với điểm lấy hàng             (vehicles.depot / DO.origin)
     · xe rảnh trong khung giờ lấy hàng        (vehicle-availability: chuyến + bảo dưỡng)
     · có tài xế đang trong ca ở khung giờ đó  (driver-shifts)
     · xe đang ở trạng thái vận hành được      (vehicles.operational_status)

   Bản mẫu còn chấm "lịch sử chạy tuyến" và "khoảng cách km tới điểm lấy". Hệ
   thống chưa lưu hai thứ đó (không có bảng lịch sử tuyến theo xe, không có toạ
   độ bãi), nên lược bỏ — chấm điểm bằng một con số bịa thì cả cột mất ý nghĩa,
   và người điều phối tin vào nó mới là cái hại.
   ========================================================================== */

let dispatchScope = { depot: '', type: '' };
let dispatchCandSort = 'score';
// "Nới điều kiện" — bỏ lọc cứng để xem cả xe không hoàn toàn vừa. Bản mẫu có
// đường dẫn này và nó thật sự cần: ở quy mô ~500 xe vẫn có ngày không chiếc nào
// đủ điều kiện, mà màn hình trống thì không nói được là vì sao.
let dispatchCandNoiDieuKien = false;

/** Ca trực và lịch xe cho màn Điều phối.
 *
 *  Hai đường này vốn chỉ được gọi ở màn Sắp lịch xe và tài xế, nên vào màn Điều
 *  phối là `driverShifts` và `driverVehicleAvailability` đều rỗng — cột xe ứng
 *  viên không biết xe nào đang chạy và tài xế nào đang trong ca. Nạp thêm ở đây,
 *  và chịu lỗi im lặng: thiếu ca trực thì cột vẫn vẽ được, chỉ là chấm điểm
 *  thiếu một tiêu chí, còn chặn cả màn hình vì một lời gọi phụ thì tệ hơn.
 */
async function napCaTrucChoDieuPhoi() {
  const ngay = selectedDispatchFleetIsoDate || dispatchDateInputValue(dispatchCalendarDate);
  if (!ngay) return;
  const moc = new Date(ngay + 'T00:00:00');
  // Lay TU HOM TRUOC, khong phai tu hom nay: ca sang 06:00 gio Viet Nam duoc
  // luu la 23:00Z cua NGAY HOM TRUOC, nen hoi tu dung ngay hom nay la mat ca
  // sang — dung ca ca dang phu khung gio lay hang. Da do that: moi xe deu bao
  // "chua co tai xe trong ca" trong khi bang ca truc co du 20 dong.
  const tu = new Date(moc.getTime() - 86400000);
  const den = new Date(moc.getTime() + 2 * 86400000);
  const q = 'start=' + tu.toISOString().slice(0, 10) + '&end=' + den.toISOString().slice(0, 10);
  // Dung `driverShiftApiJson`, khong dung `fetch` tran: hai duong nay tra ve
  // `{message, data}` chu khong phai mot mang, va ham do biet boc lop `data`.
  // Goi tran thi `Array.isArray` sai va ca truc bi bo im lang.
  const ket = await Promise.allSettled([
    driverShiftApiJson('/api/tms/scheduling/driver-shifts?' + q),
    driverShiftApiJson('/api/tms/scheduling/vehicle-availability?' + q),
  ]);
  if (ket[0].status === 'fulfilled' && Array.isArray(ket[0].value)) driverShifts = ket[0].value;
  if (ket[1].status === 'fulfilled' && Array.isArray(ket[1].value)) driverVehicleAvailability = ket[1].value;
}

/** Danh sách xe dùng cho màn Điều phối, ưu tiên nguồn nào CÓ dòng.
 *
 *  Phải xét ĐỘ DÀI chứ không dùng `||`: một mảng rỗng là truthy trong
 *  JavaScript, nên `availableVehicles || fioriVehicles` trả về đúng mảng rỗng
 *  khi màn này chưa nạp xong. Lỗi đó đã xảy ra thật ở thẻ "Xe / tài xế rảnh".
 */
function dispatchDanhSachXe() {
  if (Array.isArray(availableVehicles) && availableVehicles.length) return availableVehicles;
  if (Array.isArray(driverShiftVehicles) && driverShiftVehicles.length) return driverShiftVehicles;
  return Array.isArray(fioriVehicles) ? fioriVehicles : [];
}

function dispatchDanhSachTaiXe() {
  if (Array.isArray(availableDrivers) && availableDrivers.length) return availableDrivers;
  return Array.isArray(fioriDrivers) ? fioriDrivers : [];
}

/** Hai chữ đầu của tên, để vẽ vòng tròn tổ lái. */
function chuCaiTen(ten) {
  const tu = String(ten || '').trim().split(/\s+/).filter(Boolean);
  if (!tu.length) return '?';
  if (tu.length === 1) return tu[0].slice(0, 2).toUpperCase();
  return (tu[tu.length - 2][0] + tu[tu.length - 1][0]).toUpperCase();
}

/** Khung giờ lấy hàng của một DO, dạng hai mốc thời gian. */
function khungGioLayHang(don) {
  const batDau = don && (don.pickup_window_start || don.planned_departure_at || don.pickup_date);
  const ketThuc = don && (don.pickup_window_end || don.planned_arrival_at);
  if (!batDau) return null;
  const tu = new Date(batDau);
  if (isNaN(tu)) return null;
  let den = ketThuc ? new Date(ketThuc) : null;
  // Không có giờ kết thúc thì lấy hai giờ — đủ để phát hiện trùng chuyến mà
  // không rộng tới mức loại hết mọi xe.
  if (!den || isNaN(den)) den = new Date(tu.getTime() + 2 * 3600000);
  return { tu: tu, den: den };
}

function haiKhungChongNhau(a, b) {
  return a.tu < b.den && b.tu < a.den;
}

/** Việc đã xếp cho một xe, chồng lên khung giờ đang xét. */
function viecDaXepCuaXe(maXe, khung) {
  const cham = [];
  (driverVehicleAvailability || []).forEach(x => {
    if (String(x.vehicle_id || '') !== String(maXe)) return;
    const tu = x.planned_departure_at ? new Date(x.planned_departure_at) : null;
    if (!tu || isNaN(tu)) return;
    const den = x.planned_arrival_at ? new Date(x.planned_arrival_at) : null;
    const khungXe = { tu: tu, den: (den && !isNaN(den)) ? den : new Date(tu.getTime() + 3600000) };
    if (!khung || haiKhungChongNhau(khung, khungXe)) cham.push(Object.assign({}, x, { khung: khungXe }));
  });
  return cham;
}

/** Tài xế đang trong ca ở khung giờ đang xét, ưu tiên người đã gán cho xe đó. */
function taiXeTrongCa(maXe, khung) {
  const ca = (driverShifts || []).filter(c => {
    if (String(c.availability_kind || 'work') !== 'work') return false;
    if (String(c.status || '').toLowerCase() === 'cancelled') return false;
    const tu = c.shift_start ? new Date(c.shift_start) : null;
    const den = c.shift_end ? new Date(c.shift_end) : null;
    if (!tu || !den || isNaN(tu) || isNaN(den)) return false;
    return !khung || haiKhungChongNhau(khung, { tu: tu, den: den });
  });
  return { cuaXe: ca.filter(c => String(c.vehicle_id || '') === String(maXe)), tatCa: ca };
}

/**
 * Chấm điểm một xe cho một DO.
 *
 * Trả về cả điểm VÀ lý do trừ điểm, vì một con số trơ thì người điều phối không
 * kiểm lại được — mà họ là người chịu trách nhiệm cho chuyến, không phải hệ
 * thống. Lý do hiện ngay trên dòng.
 */
function chamDiemXe(xe, don, khung) {
  let diem = 100;
  const lyDo = [];
  let chan = '';

  const ttMa = String(xe.operational_status || '');
  if (ttMa === 'maintenance') chan = 'bảo dưỡng';
  if (ttMa === 'out_of_service') chan = 'ngưng hoạt động';

  const viec = viecDaXepCuaXe(xe.id, khung);
  const dangChay = viec.filter(v => String(v.kind || '') === 'trip');
  const baoDuong = viec.filter(v => String(v.kind || '') === 'maintenance');
  if (baoDuong.length) chan = 'bảo dưỡng';
  else if (dangChay.length && !chan) chan = 'trùng chuyến';

  // Tải trọng là tiêu chí CỨNG: xe không chở nổi thì không phải "kém phù hợp",
  // nó là sai — máy chủ cũng chặn bằng `require_vehicle_capacity`.
  const suc = Number(xe.weight_capacity || 0);
  const canNang = Number((don && don.weight_kg) || 0);
  let quaTai = false;
  if (suc && canNang) {
    if (canNang > suc) {
      quaTai = true;
      lyDo.push('không chở nổi ' + (canNang / 1000).toLocaleString('vi-VN') + ' T');
    } else {
      const tiLe = canNang / suc;
      // Xe quá to cho đơn quá nhỏ vẫn chạy được, nhưng tốn dầu — trừ điểm, chứ
      // không loại.
      if (tiLe < 0.35) { diem -= 18; lyDo.push('xe quá lớn cho đơn'); }
      else if (tiLe > 0.95) { diem -= 6; lyDo.push('gần kín tải'); }
    }
  } else if (!canNang) {
    lyDo.push('đơn chưa khai khối lượng');
  }

  // Bãi đỗ so với điểm lấy hàng: khớp bằng chữ, vì hệ thống chưa lưu toạ độ bãi.
  const bai = normalizeSearchText(xe.depot || '');
  const diemLay = normalizeSearchText((don && don.origin) || '');
  let cungBai = false;
  if (bai && diemLay) {
    cungBai = bai.split(/\s+/).filter(t => t.length > 3).some(t => diemLay.indexOf(t) >= 0);
    if (!cungBai) { diem -= 22; lyDo.push('khác bãi điểm lấy'); }
  }

  const ca = taiXeTrongCa(xe.id, khung);
  if (!ca.cuaXe.length) {
    if (!ca.tatCa.length) { diem -= 30; lyDo.push('không có tài xế trong ca'); }
    else { diem -= 12; lyDo.push('tài xế chưa gán cho xe này'); }
  }

  if (chan || quaTai) diem = 0;
  return {
    diem: Math.max(0, Math.min(100, diem)),
    chan: chan || (quaTai ? 'quá tải' : ''),
    lyDo: lyDo,
    cungBai: cungBai,
    dangChay: dangChay,
    ca: ca,
  };
}

/** Tên loại xe cho người đọc, thay vì mã `DEMO-VT-...`. */
function tenLoaiXe(ma) {
  if (!ma) return '';
  const nguon = (typeof vehTypes !== 'undefined' && Array.isArray(vehTypes) && vehTypes.length)
    ? vehTypes
    : ((appState && appState.vehicle_types) || []);
  const loai = nguon.find(t => String(t.id) === String(ma));
  return (loai && loai.name) || String(ma);
}

window.setDispatchScope = function () {
  dispatchScope = {
    depot: (document.getElementById('dispatch-scope-depot') || {}).value || '',
    type: (document.getElementById('dispatch-scope-type') || {}).value || '',
  };
  renderDispatchCandidates();
};

window.setDispatchCandSort = function (kieu) {
  dispatchCandSort = String(kieu || 'score');
  document.querySelectorAll('.dispatch-cand-sort button').forEach(b =>
    b.classList.toggle('is-on', b.dataset.sort === dispatchCandSort));
  renderDispatchCandidates();
};

window.noiDieuKienUngVien = function () {
  dispatchCandNoiDieuKien = !dispatchCandNoiDieuKien;
  renderDispatchCandidates();
};

/** Điền hai ô phạm vi (bãi, loại xe) từ dữ liệu xe thật. */
function renderDispatchScopeOptions() {
  const ds = dispatchDanhSachXe();
  const dat = (id, giaTri, nhanMacDinh) => {
    const el = document.getElementById(id);
    if (!el) return;
    const dangChon = el.value;
    const dem = new Map();
    giaTri.forEach(v => { if (v) dem.set(v, (dem.get(v) || 0) + 1); });
    el.innerHTML = '<option value="">' + nhanMacDinh + ' (' + ds.length + ')</option>'
      + [...dem.entries()].sort((a, b) => b[1] - a[1]).map(cap =>
        '<option value="' + escapeHtml(cap[0]) + '">' + escapeHtml(cap[0]) + ' (' + cap[1] + ')</option>').join('');
    if (dangChon && dem.has(dangChon)) el.value = dangChon;
  };
  // Ten bai tu DANH MUC (depot_name), khong tu chuoi go tay.
  dat('dispatch-scope-depot', ds.map(v => v.depot_name || v.depot), 'Tất cả bãi');
  dat('dispatch-scope-type', ds.map(v => tenLoaiXe(v.type) || v.type), 'Tất cả loại xe');
}

function tenCaTruc(kieu) {
  const bang = { morning: 'sáng', afternoon: 'chiều', night: 'đêm' };
  return bang[String(kieu || '')] || String(kieu || '');
}


/**
 * Bấm một dòng xe ứng viên: gán XE và TÀI XẾ vào ô điều phối.
 *
 * Gán cả tài xế, không chỉ xe: dòng này vốn đã biết ai đang trong ca với chiếc
 * xe đó, nên để người dùng tự đi chọn lại tài xế ở ô khác là bắt họ làm hai lần
 * một việc — và dễ chọn ra người đang ở ca khác.
 */
window.chonXeUngVien = function (maXe, maTaiXe, maPhuXe) {
  if (!maXe) return;
  window.selectDispatchVehicleLane(maXe);
  const datNguoi = (oId, hienId, ma) => {
    if (!ma) return;
    const o = document.getElementById(oId);
    const hien = document.getElementById(hienId);
    const nguoi = dispatchDanhSachTaiXe().find(t => String(t.id) === String(ma));
    if (o) o.value = ma;
    if (hien) hien.value = (nguoi && nguoi.name) ? nguoi.name + ' (' + ma + ')' : String(ma);
  };
  datNguoi('dispatch-driver', 'dispatch-driver-display', maTaiXe);
  // Gan luon PHU XE neu ca truc co nguoi thu hai cho dung chiec xe do. Bo qua
  // thi dieu phoi vien phai di chon lai mot nguoi ma man hinh von da biet.
  datNguoi('dispatch-co-driver', 'dispatch-co-driver-display', maPhuXe);
  if (maTaiXe && typeof window.onDispatchDriverChange === 'function') window.onDispatchDriverChange();
  if (typeof updateDispatchWorkflowSteps === 'function') updateDispatchWorkflowSteps();
  dpv2VeToLai();
  renderDispatchCandidates();
};


/**
 * "Xếp cả nhóm": tick tất cả DO của một tuyến rồi mở form tạo Trip.
 *
 * Một Trip chỉ chở được các DO CÙNG một tuyến, nên cả nhóm là đúng một đơn vị
 * ghép được. Không tự gửi lệnh tạo Trip: form còn sáu trường nữa mà backend
 * nhận — thời gian bốc dỡ, kế hoạch chặng về, giờ khởi hành — và đoán hộ những
 * trường đó là cách sinh ra chuyến sai giờ mà không ai bấm.
 */
window.xepCaNhomDO = function (maTuyen) {
  const nguon = (eplDeliveryOrders && eplDeliveryOrders.length) ? eplDeliveryOrders : (dispatchDOs || []);
  const ds = nguon
    .filter(isDispatchPendingDO)
    .filter(d => (String(d.route_id || d.route_name || '').trim() || '(chưa có tuyến)') === String(maTuyen))
    .map(d => String(d.id));
  if (!ds.length) {
    showToast('Nhóm này không còn DO nào chờ điều phối.');
    return;
  }
  if (typeof openTripReturnAction !== 'function') {
    showToast('Chưa nạp được form tạo Trip. Hãy tải lại trang.');
    return;
  }
  // Sang màn Giao hàng & vận chuyển trước: form đọc dữ liệu Trip của màn đó,
  // mở khi chưa nạp thì bộ chọn DO rỗng.
  switchView('delivery-shipment');
  setTimeout(() => openTripReturnAction('create-trip', ds), 260);
};

function dispatchCrewRole(driver) {
  return String(driver?.role || '')
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_|_$/g, '');
}

function isMainDriverRole(driver) {
  const role = dispatchCrewRole(driver);
  return !role || role === 'lai_xe_chinh' || role === 'tai_xe_chinh';
}

function isCoDriverRole(driver) {
  return dispatchCrewRole(driver) === 'phu_xe' || dispatchCrewRole(driver) === 'co_driver';
}

function renderDispatchSelects() {
  const vehSelect = document.getElementById('dispatch-vehicle');
  const drvSelect = document.getElementById('dispatch-driver');
  const coDrvSelect = document.getElementById('dispatch-co-driver');
  if (!vehSelect || !drvSelect) return;

  let readyVehCount = 0;
  let busyVehCount = 0;
  const activeVehicleIds = new Set((eplDeliveryOrders || [])
    .filter(d => isDOInTransitForDispatch(d.status, d.canonical_status) && d.vehicle_id)
    .map(d => d.vehicle_id));
  const activeDriverIds = new Set((eplDeliveryOrders || [])
    .filter(d => isDOInTransitForDispatch(d.status, d.canonical_status))
    .flatMap(d => [d.driver_id, d.co_driver_id, d.co_driver].filter(Boolean)));

  vehSelect.innerHTML = `<option value="">-- Chọn Xe Đang Sẵn Sàng (Rảnh) --</option>`;
  (availableVehicles || []).forEach((v) => {
    const isBusy = isVehicleBusyForDispatch(v.status) || activeVehicleIds.has(v.id);
    if (isBusy) {
      busyVehCount++;
      vehSelect.insertAdjacentHTML('beforeend', `<option value="${v.id}" disabled style="color:#ef4444;">[BẬN] ${v.id} (${escapeHtml(v.brand || 'Xe')} - Đang giao hàng / Bảo dưỡng)</option>`);
    } else {
      readyVehCount++;
      const capText = v.volume_capacity_m3 ? ` | Sức chứa ${v.volume_capacity_m3}m³` : '';
      vehSelect.insertAdjacentHTML('beforeend', `<option value="${v.id}">[RẢNH] ${v.id} (${escapeHtml(v.brand || 'Xe')} ${v.type || ''}${capText})</option>`);
    }
  });

  let readyDrvCount = 0;
  let busyDrvCount = 0;
  drvSelect.innerHTML = `<option value="">-- Chọn Tài Xế Chính Sẵn Sàng (Rảnh) --</option>`;
  if (coDrvSelect) coDrvSelect.innerHTML = `<option value="">-- Không có phụ xế (Chạy 1 mình) --</option>`;

  (availableDrivers || []).forEach((d) => {
    const isBusy = isDriverBusyForDispatch(d.status) || activeDriverIds.has(d.id) || activeDriverIds.has(d.name);
    if (isBusy) {
      busyDrvCount++;
      if (isMainDriverRole(d)) drvSelect.insertAdjacentHTML('beforeend', `<option value="${d.id}" disabled style="color:#ef4444;">[BẬN] ${d.id} - ${escapeHtml(d.name)} (Đang theo xe)</option>`);
      if (coDrvSelect && isCoDriverRole(d)) coDrvSelect.insertAdjacentHTML('beforeend', `<option value="${d.id}" disabled style="color:#ef4444;">[BẬN] ${d.id} - ${escapeHtml(d.name)} (Đang theo xe)</option>`);
    } else {
      readyDrvCount++;
      if (isMainDriverRole(d)) drvSelect.insertAdjacentHTML('beforeend', `<option value="${d.id}">[RẢNH] ${d.id} - ${escapeHtml(d.name)} (${d.role || 'Lái chính'})</option>`);
      if (coDrvSelect && isCoDriverRole(d)) {
        coDrvSelect.insertAdjacentHTML('beforeend', `<option value="${d.id}">[RẢNH] ${d.id} - ${escapeHtml(d.name)} (${d.role || 'Phụ xế'})</option>`);
      }
    }
  });

  // Update Summary Counts
  if (document.getElementById('dispatch-veh-ready-count')) document.getElementById('dispatch-veh-ready-count').innerText = `${readyVehCount} Xe`;
  if (document.getElementById('dispatch-veh-busy-count')) document.getElementById('dispatch-veh-busy-count').innerText = `${busyVehCount} Xe`;
  if (document.getElementById('dispatch-driver-ready-count')) document.getElementById('dispatch-driver-ready-count').innerText = `${readyDrvCount} Người`;

  renderDispatchSubTabContents(readyVehCount, busyVehCount, readyDrvCount);
}

window.switchDispatchResourceTab = function (tabName) {
  const panes = ['dispatch', 'drivers-ready', 'vehs-ready', 'busy'];
  panes.forEach(p => {
    const paneEl = document.getElementById(`subtab-content-${p}`);
    const btnEl = document.getElementById(`subtab-btn-${p}`);
    if (paneEl) paneEl.style.display = (p === tabName) ? 'block' : 'none';
    if (btnEl) {
      if (p === tabName) {
        btnEl.classList.add('active');
        btnEl.style.color = '#2563eb';
        btnEl.style.borderBottom = '3px solid #2563eb';
        btnEl.style.fontWeight = '700';
      } else {
        btnEl.classList.remove('active');
        btnEl.style.color = '#64748b';
        btnEl.style.borderBottom = '3px solid transparent';
        btnEl.style.fontWeight = '600';
      }
    }
  });
};

function renderDispatchSubTabContents(readyVehCount, busyVehCount, readyDrvCount) {
  // 1. Sub-Tab 2: Tài Xế Rảnh (Nhấp vào thẻ là gán trực tiếp vào Form)
  const driversList = document.getElementById('dispatch-drivers-ready-list');
  if (driversList) {
    driversList.innerHTML = '';
    const activeDriverIds = new Set((eplDeliveryOrders || [])
      .filter(d => isDOInTransitForDispatch(d.status, d.canonical_status))
      .flatMap(d => [d.driver_id, d.co_driver_id, d.co_driver].filter(Boolean)));
    const freeDrivers = (availableDrivers || []).filter(d =>
      !isDriverBusyForDispatch(d.status) && !activeDriverIds.has(d.id) && !activeDriverIds.has(d.name));
    if (freeDrivers.length === 0) {
      driversList.innerHTML = `<div style="padding:16px; text-align:center; color:#64748b;">Không có tài xế nào rảnh hiện tại</div>`;
    } else {
      freeDrivers.forEach(d => {
        driversList.insertAdjacentHTML('beforeend', `
          <div style="padding:12px 14px; background:#ffffff; border:1px solid #e2e8f0; border-left:4px solid #059669; border-radius:8px; display:flex; justify-content:space-between; align-items:center; cursor:pointer; transition: all 0.2s ease;" onclick="selectResourceFromPanoramic('driver', '${d.id}')" title="Nhấp vào để Gán Tài Xế Này vào Đơn">
            <div>
              <div style="font-weight:700; color:#0f172a;">${d.id} - ${escapeHtml(d.name)}</div>
              <div style="font-size:0.8rem; color:#64748b; margin-top:2px;"><i class="fa-solid fa-id-card"></i> ${d.license_type || 'Bằng FC'} | Ca: ${d.shift || 'Ca Sáng (06:00 - 14:00)'}</div>
            </div>
            <button class="fiori-btn" style="padding:4px 10px; font-size:0.78rem; background:#f0fdf4; color:#16a34a; border:1px solid #86efac; font-weight:700;">
              <i class="fa-solid fa-check"></i> Gán Tài Xế Này
            </button>
          </div>
        `);
      });
    }
  }

  // 2. Sub-Tab 3: Xe Rảnh (Nhấp vào thẻ là gán trực tiếp vào Form)
  const vehsList = document.getElementById('dispatch-vehs-ready-list');
  if (vehsList) {
    vehsList.innerHTML = '';
    const activeVehicleIds = new Set((eplDeliveryOrders || [])
      .filter(d => isDOInTransitForDispatch(d.status, d.canonical_status) && d.vehicle_id)
      .map(d => d.vehicle_id));
    const freeVehs = (availableVehicles || []).filter(v => !isVehicleBusyForDispatch(v.status) && !activeVehicleIds.has(v.id));
    if (freeVehs.length === 0) {
      vehsList.innerHTML = `<div style="padding:16px; text-align:center; color:#64748b;">Không có xe nào rảnh hiện tại</div>`;
    } else {
      freeVehs.forEach(v => {
        vehsList.insertAdjacentHTML('beforeend', `
          <div style="padding:12px 14px; background:#ffffff; border:1px solid #e2e8f0; border-left:4px solid #2563eb; border-radius:8px; display:flex; justify-content:space-between; align-items:center; cursor:pointer; transition: all 0.2s ease;" onclick="selectResourceFromPanoramic('vehicle', '${v.id}')" title="Nhấp vào để Gán Xe Này vào Đơn">
            <div>
              <div style="font-weight:800; color:#2563eb;">${v.id} <span style="font-size:0.8rem; color:#475569; font-weight:600;">(${escapeHtml(v.brand || 'Hyundai')} ${v.type || 'Container 20FT'})</span></div>
              <div style="font-size:0.8rem; color:#64748b; margin-top:2px;"><i class="fa-solid fa-cubes"></i> Sức chứa thùng: <strong>${v.volume_capacity_m3 || 30} m³</strong> | Tải trọng: ${v.weight_capacity || 15000} kg</div>
            </div>
            <button class="fiori-btn" style="padding:4px 10px; font-size:0.78rem; background:#e0f2fe; color:#0284c7; border:1px solid #7dd3fc; font-weight:700;">
              <i class="fa-solid fa-check"></i> Gán Xe Này
            </button>
          </div>
        `);
      });
    }
  }

  // 3. Sub-Tab 4: Xe & Tài Xế Bận (Kèm Tiến Độ & GPS Jump)
  const busyList = document.getElementById('dispatch-busy-list');
  if (busyList) {
    busyList.innerHTML = '';
    const activeVehicleIds = new Set((eplDeliveryOrders || [])
      .filter(d => isDOInTransitForDispatch(d.status, d.canonical_status) && d.vehicle_id)
      .map(d => d.vehicle_id));
    const busyVehicles = (availableVehicles || []).filter(v => isVehicleBusyForDispatch(v.status) || activeVehicleIds.has(v.id));
    const inTransitDOs = (eplDeliveryOrders || []).filter(d => isDOInTransitForDispatch(d.status, d.canonical_status));

    if (busyVehicles.length === 0 && inTransitDOs.length === 0) {
      busyList.innerHTML = `
        <div style="padding:20px; background:#f8fafc; border:1px dashed #cbd5e1; border-radius:8px; text-align:center; color:#64748b; font-size:0.88rem;">
          <i class="fa-solid fa-circle-info" style="color:#2563eb; margin-right:6px;"></i>Hiện tại chưa có chuyến xe nào đang lăn bánh trên đường.
        </div>
      `;
    } else {
      const renderedVehs = new Set();

      // Render Active In-Transit Delivery Orders (100% CSDL Data, 0% Mock Data)
      inTransitDOs.forEach((d, idx) => {
        const vehPlate = d.vehicle_id || 'Chưa gán xe';
        if (d.vehicle_id) renderedVehs.add(d.vehicle_id);

        const mainDrvObj = (availableDrivers || []).find(drv => drv.id === d.driver_id || drv.name === d.driver_id);
        const driverName = mainDrvObj ? `${mainDrvObj.name} (${mainDrvObj.id})` : (d.driver_id ? d.driver_id : 'Chưa gán tài xế');
        const coDriverName = d.co_driver || 'Không có phụ xế';

        const routeObj = (eplRoutes || []).find(r => r.id === d.route_id);
        const routeName = routeObj ? `${routeObj.id}: ${routeObj.name} (${routeObj.distance_km} km)` : (d.route_id || 'Tuyến vận chuyển');
        const progressInfo = calcDispatchProgress(d, routeObj);
        const pctCompleted = progressInfo.pct;
        const progressDetail = progressInfo.totalKm > 0
          ? `Đã đi ${progressInfo.doneKm.toFixed(1)} / ${progressInfo.totalKm.toFixed(1)} km • Còn lại ${progressInfo.remainingKm.toFixed(1)} km${progressInfo.eta ? ` • ETA ${progressInfo.eta}` : ''}`
          : 'Chưa có dữ liệu GPS hoặc quãng đường tuyến';

        const volUsed = d.volume_m3 || 0; // Removed mock 18.5
        const matchedVeh = (availableVehicles || []).find(v => v.id === vehPlate);
        const totalVol = matchedVeh?.volume_capacity_m3 || 30.0;
        const freeVolPct = Math.round(((totalVol - volUsed) / totalVol) * 100);

        busyList.insertAdjacentHTML('beforeend', `
          <div style="padding:16px; background:#ffffff; border:1px solid #fed7aa; border-left:4px solid #f97316; border-radius:10px; box-shadow:0 2px 6px rgba(0,0,0,0.03); margin-bottom: 12px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
              <div>
                <span style="font-size:1.05rem; font-weight:800; color:#c2410c;"><i class="fa-solid fa-truck-fast"></i> ${vehPlate}</span>
                <span style="background:#fff7ed; color:#c2410c; padding:2px 8px; border-radius:10px; font-size:0.75rem; font-weight:700; margin-left:8px;">Đang vận chuyển DO ${d.id}</span>
              </div>
              <button class="fiori-btn" onclick="jumpToGPSFromDispatch('${vehPlate}', '${d.id}')" style="padding:4px 10px; font-size:0.78rem; background:#0284c7; color:#fff;">
                <i class="fa-solid fa-location-dot"></i> Nhảy Xem GPS Realtime
              </button>
            </div>

            <div style="font-size:0.83rem; color:#475569; display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-bottom:10px; background:#fafafa; padding:8px 10px; border-radius:6px;">
              <div><strong style="color:#0f172a;">Tài xế chính:</strong> ${driverName}</div>
              <div><strong style="color:#0284c7;">Phụ xế ca:</strong> ${coDriverName}</div>
              <div style="grid-column: span 2;"><strong style="color:#0f172a;">Lộ trình:</strong> ${routeName}</div>
            </div>

            <div style="cursor:pointer;" onclick="jumpToGPSFromDispatch('${vehPlate}', '${d.id}')" title="Nhấp vào để xem GPS Realtime">
              <div style="display:flex; justify-content:space-between; font-size:0.78rem; font-weight:700; color:#334155; margin-bottom:4px;">
                <span><i class="fa-solid fa-route" style="color:#2563eb;"></i> Tiến độ quãng đường đã đi:</span>
                <span style="color:#059669; font-weight:800;">${pctCompleted}% hoàn thành</span>
              </div>
              <div style="font-size:0.76rem; color:#64748b; margin-bottom:6px;">${progressDetail}</div>
              <div style="height:10px; background:#e2e8f0; border-radius:6px; overflow:hidden; margin-bottom:8px;">
                <div style="width:${pctCompleted}%; height:100%; background:linear-gradient(90deg, #10b981, #059669); border-radius:6px;"></div>
              </div>
            </div>

            <div style="font-size:0.76rem; color:#64748b; display:flex; justify-content:space-between; align-items:center; background:#f0f9ff; padding:6px 10px; border-radius:6px; border:1px solid #bae6fd;">
              <span><i class="fa-solid fa-boxes-stacked" style="color:#0284c7;"></i> Đã xếp hàng: <strong>${volUsed} / ${totalVol} m³</strong></span>
              <span style="color:#0369a1; font-weight:700;">Thùng xe còn trống: ${freeVolPct}% (${(totalVol - volUsed).toFixed(1)} m³)</span>
            </div>
          </div>
        `);
      });

      // Also render any Busy Vehicles from CSDL not linked to inTransitDOs
      busyVehicles.forEach(v => {
        if (!renderedVehs.has(v.id)) {
          renderedVehs.add(v.id);
          const drvAssigned = (availableDrivers || []).find(drv => drv.assigned_vehicle === v.id);
          const drvText = drvAssigned ? `${drvAssigned.name} (${drvAssigned.id})` : 'Tài xế phân công theo ca';

          let statusColor = '#f97316';
          let bgColor = '#fed7aa';
          let iconStr = '<i class="fa-solid fa-truck-fast"></i>';
          let badgeText = `🔴 ${v.status}`;

          if (v.status === 'Bảo dưỡng' || v.status === 'Maintenance') {
            statusColor = '#ef4444';
            bgColor = '#fecaca';
            iconStr = '<i class="fa-solid fa-screwdriver-wrench"></i>';
            badgeText = `Đang bảo dưỡng`;
          } else {
            badgeText = `Không có DO đang vận chuyển (${v.status})`;
          }

          busyList.insertAdjacentHTML('beforeend', `
            <div style="padding:16px; background:#ffffff; border:1px solid ${bgColor}; border-left:4px solid ${statusColor}; border-radius:10px; box-shadow:0 2px 6px rgba(0,0,0,0.03); margin-bottom: 12px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <div>
                  <span style="font-size:1.05rem; font-weight:800; color:${statusColor};">${iconStr} ${v.id}</span>
                  <span style="background:#fff7ed; color:${statusColor}; padding:2px 8px; border-radius:10px; font-size:0.75rem; font-weight:700; margin-left:8px;">${badgeText}</span>
                </div>
                <button class="fiori-btn" onclick="jumpToGPSFromDispatch('${v.id}', '')" style="padding:4px 10px; font-size:0.78rem; background:#0284c7; color:#fff;">
                  <i class="fa-solid fa-location-dot"></i> Xem Đội Xe GPS
                </button>
              </div>

              <div style="font-size:0.83rem; color:#475569; display:grid; grid-template-columns:1fr 1fr; gap:6px; background:#fafafa; padding:8px 10px; border-radius:6px;">
                <div><strong style="color:#0f172a;">Loại xe:</strong> ${escapeHtml(v.brand || '')} ${v.type || ''}</div>
                <div><strong style="color:#0284c7;">Tài xế phụ trách:</strong> ${drvText}</div>
                <div style="grid-column: span 2;"><strong style="color:#0f172a;">Tải trọng:</strong> ${v.weight_capacity || 15000} kg | Sức chứa: ${v.volume_capacity_m3 || 30} m³</div>
              </div>
            </div>
          `);
        }
      });
    }
  }
}

/* PANORAMIC RESOURCE SELECTOR STUDIO LOGIC */
let currentPanoramicTargetType = 'vehicle'; // 'vehicle', 'driver', or 'co-driver'

window.openPanoramicSelector = function (targetType) {
  currentPanoramicTargetType = targetType;

  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
  const btnVeh = document.getElementById('btn-panoramic-type-veh');
  const btnDrv = document.getElementById('btn-panoramic-type-drv');
  const titleEl = document.getElementById('panoramic-modal-title');

  if (targetType === 'vehicle') {
    if (titleEl) titleEl.innerHTML = `<i class="fa-solid fa-truck-moving"></i> ${lang === 'la' ? 'ເບິ່ງພາບລວມລົດຂົນສົ່ງ & ເລືອກດ້ວຍຕາ' : (lang === 'en' ? 'VIEW TRANSPORT VEHICLES & SELECT' : 'XEM TOÀN CẢNH XE VẬN CHUYỂN & CHỌN TRỰC QUAN')}`;
    if (btnVeh) { btnVeh.style.background = '#2563eb'; btnVeh.style.color = '#fff'; }
    if (btnDrv) { btnDrv.style.background = '#f1f5f9'; btnDrv.style.color = '#475569'; }
  } else {
    const roleText = targetType === 'co-driver'
      ? (lang === 'la' ? 'ຜູ້ຊ່ວຍຄົນຂັບ' : (lang === 'en' ? 'CO-DRIVER' : 'PHỤ XE'))
      : (lang === 'la' ? 'ຄົນຂັບຫຼັກ' : (lang === 'en' ? 'MAIN DRIVER' : 'TÀI XẾ CHÍNH'));
    if (titleEl) titleEl.innerHTML = `<i class="fa-solid fa-id-card"></i> ${lang === 'la' ? `ເບິ່ງພາບລວມພະນັກງານຄົນຂັບ & ເລືອກ (${roleText})` : (lang === 'en' ? `VIEW DRIVER STAFF & SELECT (${roleText})` : `XEM TOÀN CẢNH NHÂN SỰ LÁI XE & CHỌN (${roleText})`)}`;
    if (btnVeh) { btnVeh.style.background = '#f1f5f9'; btnVeh.style.color = '#475569'; }
    if (btnDrv) { btnDrv.style.background = '#2563eb'; btnDrv.style.color = '#fff'; }
  }

  if (document.getElementById('panoramic-search-input')) {
    document.getElementById('panoramic-search-input').value = '';
  }

  renderPanoramicCardsGrid();
  const modal = document.getElementById('modal-panoramic-resource-selector');
  if (modal) {
    modal.style.display = 'flex';
    if (typeof translateAllDOMTexts === 'function') translateAllDOMTexts();
  }
};

window.switchPanoramicResourceType = function (type) {
  currentPanoramicTargetType = type;
  window.openPanoramicSelector(type);
};

window.filterPanoramicCards = function () {
  const query = document.getElementById('panoramic-search-input')?.value || '';
  const weightFilter = document.getElementById('panoramic-weight-filter')?.value || '';
  renderPanoramicCardsGrid(query, weightFilter);
};

function renderPanoramicCardsGrid(filterText = '', weightFilter = '') {
  const container = document.getElementById('panoramic-cards-grid');
  if (!container) return;
  container.innerHTML = '';

  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
  const query = filterText.toLowerCase();

  if (currentPanoramicTargetType === 'vehicle') {
    const freeVehs = (availableVehicles || []).filter(v =>
      v.status !== 'Bận' &&
      v.status !== 'In Transit' &&
      v.status !== 'Bảo dưỡng' &&
      (!dispatchEligibleVehicleIds || dispatchEligibleVehicleIds.has(String(v.id)))
    );
    let filtered = freeVehs.filter(v =>
      v.id.toLowerCase().includes(query) ||
      (v.brand || '').toLowerCase().includes(query) ||
      (v.type || '').toLowerCase().includes(query) ||
      (v.weight_capacity || 0).toString().includes(query)
    );

    // Apply Weight Filter dropdown
    if (weightFilter) {
      if (weightFilter === 'light') {
        filtered = filtered.filter(v => (v.weight_capacity || 0) < 10000);
      } else if (weightFilter === 'medium') {
        filtered = filtered.filter(v => (v.weight_capacity || 0) >= 10000 && (v.weight_capacity || 0) <= 20000);
      } else if (weightFilter === 'heavy') {
        filtered = filtered.filter(v => (v.weight_capacity || 0) > 20000);
      } else {
        filtered = filtered.filter(v => (v.type || '').toLowerCase().includes(weightFilter.toLowerCase()));
      }
    }

    if (filtered.length === 0) {
      const emptyVehMsg = lang === 'la' ? 'ບໍ່ພົບລົດທີ່ກົງກັບຕົວກັ່ນຕອງ' : (lang === 'en' ? 'No vehicles match filter criteria' : 'Không tìm thấy xe phù hợp với bộ lọc tải trọng');
      container.innerHTML = `<div style="grid-column: span 3; padding: 40px; text-align: center; color: #64748b;"><i class="fa-solid fa-truck" style="font-size: 2rem; color: #cbd5e1; margin-bottom: 8px;"></i><br>${emptyVehMsg}</div>`;
      return;
    }

    filtered.forEach(v => {
      // Synchronize 100% with Master Data Vehicle Type specs
      const matchedType = (vehTypes || []).find(vt => vt.name.toLowerCase() === (v.type || '').toLowerCase());
      const maxWeight = v.weight_capacity || matchedType?.max_weight || 15000;
      const volCapacity = v.volume_capacity_m3 || matchedType?.volume_capacity_m3 || 30.0;

      let typeDisp = v.type || 'Container 20FT';
      if (lang === 'la') {
        typeDisp = typeDisp.replace(/Xe tải thùng/gi, 'ລົດບັນທຸກຕູ້').replace(/Xe tải/gi, 'ລົດບັນທຸກ').replace(/Container/gi, 'ຕູ້ຄອນເທນເນີ').replace(/tấn/gi, 'ໂຕນ').replace(/Tấn/gi, 'ໂຕນ');
      } else if (lang === 'en') {
        typeDisp = typeDisp.replace(/Xe tải thùng/gi, 'Box Truck').replace(/Xe tải/gi, 'Truck').replace(/tấn/gi, 'Tons').replace(/Tấn/gi, 'Tons');
      }

      const tonLabel = lang === 'la' ? 'ໂຕນ' : (lang === 'en' ? 'Tons' : 'Tấn');
      const readyLabel = lang === 'la' ? 'ພ້ອມໃຊ້ງານ' : (lang === 'en' ? 'Ready' : 'Sẵn Sàng');
      const brandLabel = lang === 'la' ? 'ຍີ່ຫໍ້:' : (lang === 'en' ? 'Brand:' : 'Thương hiệu:');
      const bodyTypeLabel = lang === 'la' ? 'ປະເພດຕູ້:' : (lang === 'en' ? 'Body Type:' : 'Loại thùng:');
      const capacityLabel = lang === 'la' ? 'ຄວາມຈຸຕູ້:' : (lang === 'en' ? 'Capacity Volume:' : 'Sức chứa thùng:');
      const maxPayloadLabel = lang === 'la' ? 'ນ້ຳໜັກບັນທຸກສູງສຸດ:' : (lang === 'en' ? 'Max Payload:' : 'Tải trọng tối đa:');
      const assignVehBtn = lang === 'la' ? '+ ມອບໝາຍລົດນີ້ໃຫ້ໃບສັ່ງ' : (lang === 'en' ? '+ Assign This Vehicle' : '+ Gán Xe Này Vào Lệnh');

      container.insertAdjacentHTML('beforeend', `
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-top: 4px solid #2563eb; border-radius: 12px; padding: 18px; box-shadow: 0 4px 12px rgba(0,0,0,0.03); display: flex; flex-direction: column; justify-content: space-between; transition: transform 0.2s ease, box-shadow 0.2s ease;">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
              <span style="font-size: 1.2rem; font-weight: 800; color: #2563eb;"><i class="fa-solid fa-truck"></i> ${v.id}</span>
              <span style="background: #f0fdf4; color: #16a34a; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 700;">🟢 ${readyLabel}</span>
            </div>
            <div style="font-size: 0.85rem; color: #334155; margin-bottom: 12px; display: flex; flex-direction: column; gap: 4px;">
              <div><strong>${brandLabel}</strong> ${escapeHtml(v.brand || 'Hyundai Heavy Duty')}</div>
              <div><strong>${bodyTypeLabel}</strong> <span style="font-weight: 700; color: #0f172a;">${typeDisp}</span></div>
              <div><strong>${capacityLabel}</strong> <span style="color: #0284c7; font-weight: 700;">${volCapacity} m³</span></div>
              <div><strong>${maxPayloadLabel}</strong> <span style="color: #059669; font-weight: 700;">${maxWeight.toLocaleString('vi-VN')} kg</span> (${(maxWeight / 1000).toFixed(0)} ${tonLabel})</div>
            </div>
          </div>
          <button type="button" class="fiori-btn" onclick="selectResourceFromPanoramic('vehicle', '${v.id}')" style="width: 100%; justify-content: center; background: #2563eb; color: white; padding: 10px; font-weight: 700; border-radius: 8px;">
            <i class="fa-solid fa-plus-circle"></i> ${assignVehBtn}
          </button>
        </div>
      `);
    });
  } else {
    // Drivers or Co-Drivers
    const freeDrivers = (availableDrivers || []).filter(d => {
      if (isDriverBusyForDispatch(d.status)) return false;
      return currentPanoramicTargetType === 'co-driver' ? isCoDriverRole(d) : isMainDriverRole(d);
    });
    const filtered = freeDrivers.filter(d => d.id.toLowerCase().includes(query) || d.name.toLowerCase().includes(query) || (d.license_type || '').toLowerCase().includes(query));

    if (filtered.length === 0) {
      const emptyDrvMsg = lang === 'la' ? 'ບໍ່ພົບພະນັກງານຂັບລົດທີ່ເໝາະສົມ' : (lang === 'en' ? 'No driver staff found' : 'Không tìm thấy nhân sự lái xe phù hợp');
      container.innerHTML = `<div style="grid-column: span 3; padding: 40px; text-align: center; color: #64748b;"><i class="fa-solid fa-id-card" style="font-size: 2rem; color: #cbd5e1; margin-bottom: 8px;"></i><br>${emptyDrvMsg}</div>`;
      return;
    }

    filtered.forEach(d => {
      let licDisp = d.license_type || 'Hạng FC';
      let shiftDisp = d.shift || 'Ca Sáng (06:00 - 14:00)';

      if (lang === 'la') {
        licDisp = licDisp.replace(/Hạng\s*/gi, 'ຊັ້ນ ');
        shiftDisp = shiftDisp
          .replace(/Ca Sáng/gi, 'ກະເຊົ້າ')
          .replace(/Ca Chiều/gi, 'ກະບ່າຍ')
          .replace(/Ca Tối/gi, 'ກະຄ່ຳ')
          .replace(/Ca Đêm/gi, 'ກະດຶກ')
          .replace(/Ca hành chính/gi, 'ກະກາງເວັນ')
          .replace(/Ca trực/gi, 'ກະປະຈຳການ');
      } else if (lang === 'en') {
        licDisp = licDisp.replace(/Hạng\s*/gi, 'Class ');
        shiftDisp = shiftDisp
          .replace(/Ca Sáng/gi, 'Morning')
          .replace(/Ca Chiều/gi, 'Afternoon')
          .replace(/Ca Tối/gi, 'Evening')
          .replace(/Ca Đêm/gi, 'Night')
          .replace(/Ca hành chính/gi, 'Office Shift')
          .replace(/Ca trực/gi, 'Duty Shift');
      }

      const readyLabel = lang === 'la' ? 'ພ້ອມໃຊ້ງານ' : (lang === 'en' ? 'Ready' : 'Sẵn Sàng');
      const driverIdLabel = lang === 'la' ? 'ລະຫັດຄົນຂັບ:' : (lang === 'en' ? 'Driver ID:' : 'Mã tài xế:');
      const licTypeLabel = lang === 'la' ? 'ປະເພດໃບຂັບຂີ່:' : (lang === 'en' ? 'License Type:' : 'Hạng bằng lái:');
      const shiftLabel = lang === 'la' ? 'ກະເຮັດວຽກ:' : (lang === 'en' ? 'Shift:' : 'Ca trực:');
      const phoneLabel = lang === 'la' ? 'ເບີໂທລະສັບ:' : (lang === 'en' ? 'Phone:' : 'Số điện thoại:');
      const assignStaffBtn = lang === 'la' ? 'ມອບໝາຍພະນັກງານຄົນນີ້' : (lang === 'en' ? 'Assign This Staff' : 'Gán Nhân Sự Này');

      container.insertAdjacentHTML('beforeend', `
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-top: 4px solid #059669; border-radius: 12px; padding: 18px; box-shadow: 0 4px 12px rgba(0,0,0,0.03); display: flex; flex-direction: column; justify-content: space-between;">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
              <span style="font-size: 1.05rem; font-weight: 800; color: #0f172a;"><i class="fa-solid fa-user-gear" style="color: #059669;"></i> ${escapeHtml(d.name)}</span>
              <span style="background: #eff6ff; color: #2563eb; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 700;">🟢 ${readyLabel}</span>
            </div>
            <div style="font-size: 0.85rem; color: #334155; margin-bottom: 12px; display: flex; flex-direction: column; gap: 4px;">
              <div><strong>${driverIdLabel}</strong> ${d.id}</div>
              <div><strong>${licTypeLabel}</strong> <span style="color: #d97706; font-weight: 700;">${licDisp}</span></div>
              <div><strong>${shiftLabel}</strong> ${shiftDisp}</div>
              <div><strong>${phoneLabel}</strong> ${d.phone || '0912.345.678'}</div>
            </div>
          </div>
          <button type="button" class="fiori-btn" onclick="selectResourceFromPanoramic('${currentPanoramicTargetType}', '${d.id}')" style="width: 100%; justify-content: center; background: #059669; color: white; padding: 10px; font-weight: 700; border-radius: 8px;">
            <i class="fa-solid fa-user-check"></i> ${assignStaffBtn}
          </button>
        </div>
      `);
    });
  }
}

window.selectResourceFromPanoramic = function (targetType, resourceId) {
  if (targetType === 'vehicle') {
    const valEl = document.getElementById('dispatch-vehicle');
    const dispEl = document.getElementById('dispatch-vehicle-display');
    if (valEl) valEl.value = resourceId;
    const v = (availableVehicles || []).find(x => x.id === resourceId);
    if (dispEl) dispEl.value = `🚛 ${resourceId} (${v?.brand || 'Xe'} ${v?.type || ''} - ${v?.volume_capacity_m3 || 30} m³)`;
    window.onDispatchVehicleChange();
    showToast(`Đã chọn Xe ${resourceId} từ View Toàn Cảnh vào Lệnh Giao Hàng!`);
  } else if (targetType === 'driver') {
    const valEl = document.getElementById('dispatch-driver');
    const dispEl = document.getElementById('dispatch-driver-display');
    if (valEl) valEl.value = resourceId;
    const d = (availableDrivers || []).find(x => x.id === resourceId);
    if (dispEl) dispEl.value = `👨‍✈️ ${d?.id || resourceId} - ${d?.name || 'Tài xế'} (${d?.license_type || 'Lái chính'})`;
    showToast(`Đã chọn Tài Xế Chính ${d?.name || resourceId} từ View Toàn Cảnh!`);
  } else if (targetType === 'co-driver') {
    const valEl = document.getElementById('dispatch-co-driver');
    const dispEl = document.getElementById('dispatch-co-driver-display');
    if (valEl) valEl.value = resourceId;
    const d = (availableDrivers || []).find(x => x.id === resourceId);
    if (dispEl) dispEl.value = `👨‍✈️ ${d?.id || resourceId} - ${d?.name || 'Phụ xế'} (${d?.license_type || 'Phụ xế'})`;
    showToast(`Đã chọn Phụ Xế ${d?.name || resourceId} từ View Toàn Cảnh!`);
  }

  closeModal('modal-panoramic-resource-selector');
  window.switchDispatchResourceTab('dispatch');
};

/**
 * Dong ho suc chua thung xe o man Dieu phoi.
 *
 * Ban cu bia toan bo con so:
 *
 *     const totalVol = v ? (v.volume_capacity_m3 || 30.0) : 30.0;
 *     const usedVol = 6.0; // Default order cargo volume
 *
 * `usedVol` cung 6,0 m3 — khong doc the tich cua don dang chon. Nen nguoi
 * dieu phoi LUON thay "Xe con trong 80% (24,0 / 30 m3)" bat ke don that nang
 * hay nhe. Day la con so duy nhat tren man noi ve nang luc cho, va no khong
 * lien quan gi toi du lieu.
 *
 * Nay doc the tich THAT cua don dang chon va suc chua THAT cua xe. Thieu so
 * nao thi noi ro la chua khai, KHONG bia mot con so — mot ti le phan tram
 * tu tin te hon mot dau gach.
 */
window.onDispatchVehicleChange = function () {
  const vehSelect = document.getElementById('dispatch-vehicle');
  const meterBox = document.getElementById('dispatch-capacity-meter-box');
  if (!vehSelect || !meterBox) return;

  const vehId = vehSelect.value;
  if (!vehId) {
    meterBox.style.display = 'none';
    return;
  }
  meterBox.style.display = 'block';

  const dat = (id, chu) => {
    const node = document.getElementById(id);
    if (node) node.innerText = chu;
  };
  const bar = document.getElementById('capacity-meter-bar');

  const v = (availableVehicles || []).find(x => x.id === vehId);
  const doId = document.getElementById('dispatch-selected-do')?.value || '';
  const don = (eplDeliveryOrders || []).find(x => x.id === doId);

  const sucChua = Number(v?.volume_capacity_m3 || 0);
  const daXep = Number(don?.volume_m3 || 0);

  // Xe chua khai the tich thung: khong co mau so nao de tinh ti le.
  if (!(sucChua > 0)) {
    dat('capacity-meter-badge', `Xe ${vehId} chưa khai thể tích thùng — chưa tính được độ lấp`);
    dat('capacity-used-text', daXep > 0 ? `${daXep} m³` : '—');
    dat('capacity-total-text', '—');
    if (bar) bar.style.width = '0%';
    return;
  }

  // Don chua khai the tich: bao ro, dung coi la 0 roi ket luan "con trong 100%".
  if (!(daXep > 0)) {
    dat('capacity-meter-badge',
      `Sức chứa ${sucChua} m³ — đơn ${doId || '(chưa chọn)'} chưa khai thể tích hàng`);
    dat('capacity-used-text', '—');
    dat('capacity-total-text', `${sucChua} m³`);
    if (bar) bar.style.width = '0%';
    return;
  }

  const conTrong = sucChua - daXep;
  const tiLeDaXep = Math.min(100, Math.round((daXep / sucChua) * 100));
  const tiLeConTrong = Math.max(0, 100 - tiLeDaXep);

  dat('capacity-meter-badge', conTrong >= 0
    ? `Xe còn trống ${tiLeConTrong}% (${conTrong.toFixed(1)} / ${sucChua} m³)`
    : `QUÁ TẢI ${Math.abs(conTrong).toFixed(1)} m³ (đã xếp ${daXep} / ${sucChua} m³)`);
  dat('capacity-used-text', `${daXep} m³`);
  dat('capacity-total-text', `${sucChua} m³`);
  if (bar) {
    bar.style.width = `${tiLeDaXep}%`;
    // Qua tai thi phai NHIN RA duoc, khong chi la thanh xanh day.
    bar.style.background = conTrong < 0 ? '#b91c1c' : '';
  }
};

let currentDetailDOId = null;
window.openOrderDetailModal = function (doId, e) {
  if (e) e.stopPropagation();
  currentDetailDOId = doId;

  const d = (eplDeliveryOrders || []).find(x => x.id === doId) || (dispatchDOs || []).find(x => x.id === doId);
  if (!d) return;

  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';

  const titleEl = document.getElementById('modal-order-detail-title');
  if (titleEl) {
    titleEl.innerHTML = `<i class="fa-solid fa-file-invoice"></i> ${lang === 'la' ? 'ລາຍລະອຽດໃບສັ່ງສົ່ງສິນຄ້າ (DO)' : (lang === 'en' ? 'DELIVERY ORDER DETAILS (DO)' : 'CHI TIẾT ĐƠN HÀNG VẬN TẢI')}`;
  }

  if (document.getElementById('detail-do-id')) document.getElementById('detail-do-id').innerText = d.id;
  if (document.getElementById('detail-so-id')) document.getElementById('detail-so-id').innerText = d.quotation_id || '-';
  if (document.getElementById('detail-customer')) document.getElementById('detail-customer').innerText = d.customer_id || '-';
  if (document.getElementById('detail-route')) document.getElementById('detail-route').innerText = d.route_id || '-';
  if (document.getElementById('detail-pickup-date')) document.getElementById('detail-pickup-date').innerText = d.pickup_date || '-';
  if (document.getElementById('detail-delivery-date')) document.getElementById('detail-delivery-date').innerText = d.delivery_date || '-';

  const noVehText = lang === 'la' ? 'ຍັງບໍ່ໄດ້ກຳນົດລົດ' : (lang === 'en' ? 'Not assigned' : 'Chưa gán xe');
  const noDrvText = lang === 'la' ? 'ຍັງບໍ່ໄດ້ກຳນົດຄົນຂັບ' : (lang === 'en' ? 'Not assigned' : 'Chưa gán tài xế');
  const noCoDrvText = lang === 'la' ? 'ບໍ່ມີຜູ້ຊ່ວຍຄົນຂັບ' : (lang === 'en' ? 'No co-driver' : 'Không có phụ xế');

  if (document.getElementById('detail-vehicle')) document.getElementById('detail-vehicle').innerText = d.vehicle_id || noVehText;
  if (document.getElementById('detail-driver')) document.getElementById('detail-driver').innerText = d.driver_id || noDrvText;
  if (document.getElementById('detail-co-driver')) document.getElementById('detail-co-driver').innerText = d.co_driver || noCoDrvText;

  let pkg = d.packaging_spec || 'Thùng carton (tiêu chuẩn)';
  if (lang === 'la') {
    pkg = pkg.replace(/Thùng carton\s*\(tiêu chuẩn\)/gi, 'ກ່ອງເຈ້ຍ Carton (ມາດຕະຖານ)')
             .replace(/Thùng carton/gi, 'ກ່ອງເຈ້ຍ Carton')
             .replace(/Pallet gỗ/gi, 'ພາເລດໄມ້')
             .replace(/Bao bì chống sốc/gi, 'ຖົງກັນກະແທກ')
             .replace(/Hàng rời\/Nguyên khối/gi, 'ສິນຄ້າແຍກສ່ວນ/ເປັນທ່ອນ');
  } else if (lang === 'en') {
    pkg = pkg.replace(/Thùng carton\s*\(tiêu chuẩn\)/gi, 'Carton Box (Standard)')
             .replace(/Thùng carton/gi, 'Carton Box')
             .replace(/Pallet gỗ/gi, 'Wooden Pallet')
             .replace(/Bao bì chống sốc/gi, 'Cushioning Packaging')
             .replace(/Hàng rời\/Nguyên khối/gi, 'Bulk / Solid Cargo');
  }
  if (document.getElementById('detail-packaging')) document.getElementById('detail-packaging').innerText = pkg;

  const statusBadgeEl = document.getElementById('detail-status-badge');
  if (statusBadgeEl) {
    statusBadgeEl.innerHTML = `<span style="background: #e0f2fe; color: #0369a1; padding: 4px 12px; border-radius: 20px; font-size: 0.82rem; font-weight: 700;">${statusLabel(d.status || '')}</span>`;
  }

  const detailWeight = d.weight_kg || 0;
  const detailVol = d.volume_m3 || 0;
  const detailVeh = (availableVehicles || []).find(v => v.id === d.vehicle_id);
  const detailTotalVol = detailVeh?.volume_capacity_m3 || 30.0;
  if (document.getElementById('detail-weight')) document.getElementById('detail-weight').innerText = `${detailWeight.toLocaleString('vi-VN')} kg`;
  if (document.getElementById('detail-volume')) document.getElementById('detail-volume').innerText = `${detailVol} m³`;
  const pctLabel = lang === 'la' ? 'ຕູ້ລົດ' : (lang === 'en' ? 'Capacity' : 'Thùng Xe');
  if (document.getElementById('detail-capacity-pct')) document.getElementById('detail-capacity-pct').innerText = detailTotalVol > 0 ? `${Math.round((detailVol / detailTotalVol) * 100)}% ${pctLabel}` : '-';

  const modal = document.getElementById('modal-order-detail');
  if (modal) {
    modal.style.display = 'flex';
    if (typeof translateAllDOMTexts === 'function') translateAllDOMTexts();
  }
};

window.jumpToGPSFromDispatch = function (vehId, doId) {
  showToast(`Đang chuyển sang Bản Đồ GPS Realtime cho Xe ${vehId}...`);
  window.switchView('tracking');
  if (typeof window.initGPSTrackingMap === 'function') {
    window.initGPSTrackingMap(vehId, doId);
  }
};

window.jumpToGPSFromModal = function () {
  closeModal('modal-order-detail');
  if (currentDetailDOId) {
    const d = (eplDeliveryOrders || []).find(x => x.id === currentDetailDOId);
    window.jumpToGPSFromDispatch(d?.vehicle_id || '', currentDetailDOId);
  } else {
    window.switchView('tracking');
  }
};

window.onDispatchDODragStart = function (event, doId) {
  draggedDispatchDOId = doId || '';
  selectedDispatchCalendarOrderId = draggedDispatchDOId;
  if (event?.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', draggedDispatchDOId);
  }
};

window.onDispatchLaneDragOver = function (event) {
  event?.preventDefault();
  if (event?.dataTransfer) event.dataTransfer.dropEffect = 'move';
};

window.onDispatchLaneDrop = function (event, vehicleId) {
  event?.preventDefault();
  const doId = event?.dataTransfer?.getData('text/plain') || draggedDispatchDOId || selectedDispatchCalendarOrderId;
  if (doId) window.selectDispatchDO(doId, true);
  window.selectDispatchVehicleLane(vehicleId);
  draggedDispatchDOId = '';
};

window.selectDispatchVehicleLane = function (vehicleId) {
  if (!vehicleId) return;
  const vehicleInput = document.getElementById('dispatch-vehicle');
  const vehicleDisplay = document.getElementById('dispatch-vehicle-display');
  const vehicle = (availableVehicles || []).find(item => String(item.id) === String(vehicleId));
  if (vehicleInput) vehicleInput.value = vehicleId;
  // Hien TEN loai xe, khong hien ma: "DEMO-VT-TRACTOR20" khong noi cho nguoi
  // dieu phoi biet day la dau keo 20 feet hay xe tai.
  const tenLoai = vehicle?.type
    ? (typeof tenLoaiXe === 'function' ? tenLoaiXe(vehicle.type) : vehicle.type)
    : '';
  if (vehicleDisplay) vehicleDisplay.value = `${vehicleId}${tenLoai ? ` · ${tenLoai}` : ''}`;
  window.onDispatchVehicleChange();
  if (typeof dpv2VeToLai === 'function') dpv2VeToLai();
  updateDispatchWorkflowSteps();
  if (dispatchStepModalState.step === 'schedule') window.closeDispatchStepModal();
  else if (selectedDispatchCalendarOrderId) openDispatchDetail(document.activeElement);
};

window.selectDispatchDO = function (id, revealDetail = false) {
  const dispatchSelectedDoEl = document.getElementById('dispatch-selected-do');
  if (dispatchSelectedDoEl) dispatchSelectedDoEl.value = id || '';
  selectedDispatchCalendarOrderId = id || '';
  if (revealDetail) dispatchDetailUnlocked = Boolean(id);
  if (!id) {
    updateDispatchWorkflowSteps();
    if (typeof dpv2MoKhungGan === 'function') dpv2MoKhungGan(false);
    if (typeof renderDispatchCalendar === 'function') renderDispatchCalendar();
    if (typeof renderDispatchCandidates === 'function') renderDispatchCandidates();
    return;
  }
  // Cot phai doi sang khung gan, dung nhu ban mau: danh sach ngoai le la thu
  // xem khi CHUA co viec cu the, con khi da chon mot don thi cho do phai la
  // noi gan xe va to lai.
  if (typeof dpv2MoKhungGan === 'function') dpv2MoKhungGan(true);
  tmsActiveShipment360Id = id;
  tmsActiveTimelineDoId = id;
  window.switchDispatchResourceTab('dispatch');
  window.onDispatchVehicleChange();
  if (typeof renderDispatchCalendar === 'function') renderDispatchCalendar();
  if (typeof renderDispatchCandidates === 'function') renderDispatchCandidates();
  updateDispatchWorkflowSteps();
  const tripGate = resolveDispatchTripGate(id);
  if (tripGate.state === 'ready') {
    if (dispatchDayWorkbenchState.open) {
      dispatchDetailUnlocked = true;
      const assignment = document.getElementById('subtab-content-dispatch');
      if (assignment) assignment.hidden = false;
      renderDispatchCalendar();
      const detail = document.getElementById('dispatch-detail');
      if (detail) detail.hidden = false;
    } else if (revealDetail) openDispatchDetail(document.activeElement);
    else window.openDispatchStepModal('schedule');
  } else {
    openDispatchTripGate(id);
  }
};

/**
 * Hoi lai khi dieu xe cho mot don CHUA KHAI hang hoa.
 *
 * Khi khoi luong, the tich va so pallet deu bang 0, `require_vehicle_capacity`
 * o may chu khong chan duoc gi ca — moi xe deu "vua". Chu du an da chot: canh
 * bao nhung van cho dieu, vi chuyen chay rong la co that trong van tai.
 */
function confirmDispatchWithoutCargo(doId) {
  const order = (eplDeliveryOrders || []).find(item => String(item.id) === String(doId));
  if (!order) return true;
  const weight = Number(order.weight_kg || order.total_weight_kg || 0);
  const volume = Number(order.volume_m3 || order.total_volume_m3 || 0);
  const pallets = Number(order.pallet_count || order.total_pallet_count || 0);
  if (weight || volume || pallets) return true;

  return confirm(
    `Lệnh ${doId} chưa khai khối lượng, thể tích hay số pallet.`
    + String.fromCharCode(10, 10)
    + 'Hệ thống sẽ KHÔNG kiểm được xe có chở vừa hay không — một container 30 tấn '
    + 'vẫn có thể được xếp lên xe tải 2 tấn.'
    + String.fromCharCode(10, 10)
    + 'Nếu đây là chuyến chạy rỗng thì bấm OK để tiếp tục. Nếu không, hãy khai '
    + 'hàng hóa vận chuyển trong Đơn hàng vận chuyển trước.'
  );
}

window.submitDispatch = async function () {
  const doId = document.getElementById('dispatch-selected-do')?.value;
  const vehId = document.getElementById('dispatch-vehicle')?.value;
  const drvId = document.getElementById('dispatch-driver')?.value;
  const coDrvId = document.getElementById('dispatch-co-driver')?.value || '';
  const pkgSpec = document.getElementById('dispatch-packaging-spec')?.value || 'Thùng carton (tiêu chuẩn)';

  if (!doId) {
    showToast('Vui lòng nhấp chọn Lệnh Giao Hàng (DO) ở danh sách bên trái!');
    return;
  }
  if (!vehId) {
    showToast('Vui lòng chọn Xe vận chuyển trong danh mục Phân Bổ!');
    return;
  }
  if (!drvId) {
    showToast('Vui lòng chọn Tài Xế phụ trách trong danh mục Phân Bổ!');
    return;
  }
  if (coDrvId && coDrvId === drvId) {
    showToast('Tài xế chính và phụ xe phải là hai người khác nhau.');
    return;
  }

  // Đơn chưa khai hàng hóa thì phép kiểm năng lực xe ở máy chủ KHÔNG kiểm được
  // gì cả: cả ba con số bằng 0 thì xe nào cũng "vừa", kể cả container 30 tấn
  // trên xe tải 2 tấn. Cố tình KHÔNG chặn — chuyến chạy rỗng là có thật — nhưng
  // phải nói rõ để người điều phối tự quyết.
  if (!confirmDispatchWithoutCargo(doId)) return;

  showToast(`Đang đăng ký điều phối & cấp lệnh xuất bến cho Lệnh ${doId}...`);

  const tripGate = resolveDispatchTripGate(doId);
  if (tripGate.state !== 'ready' || !tripGate.trip) {
    showToast('Không thể xuất bến: DO phải có đúng một Trip ở trạng thái Đã lập kế hoạch.');
    openDispatchTripGate(doId);
    return;
  }
  const plannedTrip = tripGate.trip;
  const tripStart = plannedTrip?.planned_departure_at;
  const tripEnd = plannedTrip?.planned_return_at || plannedTrip?.planned_arrival_at;
  if (!tripStart || !tripEnd) {
    showToast('Trip thiếu giờ khởi hành hoặc giờ kết thúc/quay về. Vui lòng hoàn thiện Trip trước khi xuất bến.');
    return;
  }
  const command = {
    path: `/api/tms/trips/${plannedTrip.id}/dispatch`,
    method: 'PUT',
    body: {
      vehicle_id: vehId,
      driver_id: drvId,
      co_driver_id: coDrvId || null,
      expected_version: Number(plannedTrip.version || 1),
      assignment_start: new Date(tripStart).toISOString(),
      assignment_end: new Date(tripEnd).toISOString()
    }
  };
  const commandResult = await dieuPhoiCoXacNhanLoaiXe(command);

  if (commandResult.ok) {
    showToast(`Đã điều phối & cấp lệnh xuất bến thành công cho Lệnh ${doId}! (Xe: ${vehId}, Tài xế: ${drvId})`);

    if (document.getElementById('dispatch-selected-do')) {
      document.getElementById('dispatch-selected-do').value = '';
    }

    if (typeof renderDispatchDOs === 'function') renderDispatchDOs();
    if (typeof renderDispatchSelects === 'function') renderDispatchSelects();
    window.switchDispatchResourceTab('busy');

    // Advance live flow tracker to Step 6 (GPS & POD)
    window.updateActiveFlowStep(6, true);

    // Automatically transition to Step 6 GPS Tracking View & Initialize Map!
    setTimeout(() => {
      window.switchView('tracking');
      if (typeof window.initGPSTrackingMap === 'function') {
        window.initGPSTrackingMap(vehId, doId);
      }
    }, 400);
  }
};

let gpsTrackingMap = null;
let gpsTruckMarker = null;
let gpsTrackingLayerGroup = null;
let snappedCoordOnRoute = [10.8456, 106.7725];

function isGpsLiveTrackingStatus(status) {
  const key = String(status || '')
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[\s-]+/g, '_');
  return key === 'in_transit' || key === 'dang_van_chuyen' || key === 'dang_giao_hang';
}

function populateTrackingDOSelector(selectedDoId = '') {
  const selectEl = document.getElementById('tracking-active-do-select');
  if (!selectEl) return;

  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
  const allDOs = (eplDeliveryOrders && eplDeliveryOrders.length > 0 ? eplDeliveryOrders : (dispatchDOs || []));
  const liveDOs = allDOs.filter(d => isGpsLiveTrackingStatus(d.status || d.canonical_status));
  
  const sortedDOs = [...liveDOs].sort((a, b) => String(a.id || '').localeCompare(String(b.id || '')));

  const defaultText = lang === 'la' ? '-- ເລືອກຖ້ຽວລົດເພື່ອຕິດຕາມ GPS Live --' : (lang === 'en' ? '-- Select a trip to track Live GPS --' : '-- Chọn chuyến xe để theo dõi GPS Live --');

  selectEl.innerHTML = `<option value="">${defaultText}</option>` + sortedDOs.map(d => {
    const vehLabel = d.vehicle_id ? (lang === 'la' ? `🚛 ລົດ [${d.vehicle_id}]` : `🚛 Xe [${d.vehicle_id}]`) : '📋';
    const statusText = statusLabel(d.status || '');
    const meta = [d.customer_id, d.route_id].filter(Boolean).join(' • ');
    return `<option value="${d.id}">${vehLabel} • ${d.id}${meta ? ` (${meta})` : ''} - [${statusText}]</option>`;
  }).join('');

  if (selectedDoId && sortedDOs.some(d => String(d.id) === String(selectedDoId))) {
    selectEl.value = selectedDoId;
  }
  if (typeof window.populatePODDeliverySelector === 'function') {
    window.populatePODDeliverySelector(selectedDoId);
  }
  window.renderTrackingDOList(selectedDoId);
}


/* ==========================================================================
   MÀN THEO DÕI & KIỂM SOÁT — dải số liệu, theo bản mẫu
   `tracking-control-tower.html`.

   Đây là tháp kiểm soát: người ngồi đây không đi tìm việc, việc phải tự nổi lên
   trước mắt họ. Trước đây màn này chỉ có một danh sách "DO đang vận chuyển" xếp
   theo mã — nhìn vào không biết chuyến nào cần xử trước. Dải này trả lời đúng
   câu đó, và bấm được: mỗi thẻ lọc danh sách bên dưới.

   Bản mẫu có BẢY thẻ. Thẻ "Lệch tuyến" LƯỢC BỎ: hệ thống không có logic hành
   lang tuyến nào cả — đo được, `#route-dev-alert` trong trang là markup chết,
   không hàm nào ghi vào nó. Vẽ một con số lệch tuyến khi không có phép đo nào
   là nói dối người đang trực, và họ sẽ tin.

   Sáu thẻ còn lại đọc từ dữ liệu thật:

     · Đang chạy      — số DO đang vận chuyển
     · Nguy cơ trễ    — ETA của GPS muộn hơn hạn giao của đơn
     · Đúng tiến độ   — có GPS, và ETA còn trước hạn
     · Mất GPS > 15'  — mốc `last_update` cũ hơn 15 phút
     · Sự cố mở       — `/api/incidents` còn sự cố chưa đóng
     · Thiếu POD      — xe đã đến nơi mà chưa có bản ghi POD
   ========================================================================== */

let trackingKpiFilter = '';
//: Chan goi lai vong tron khi nap vet GPS: ham nap ve xong lai goi ham ve.
let dangNapVetGps = false;

/** Nap vet GPS cho man Theo doi.
 *
 *  `dispatchTrackingByDO` von chi duoc `loadDispatchBoard` dien, nen vao man
 *  Theo doi truc tiep la no RONG. Ca sau the so lieu doc bien do, nen dai bao
 *  "mat GPS" cho MOI chuyen — ke ca chuyen dang gui toa do binh thuong. Do la
 *  con so te nhat co the hien tren mot thap kiem soat: no bao dong gia.
 *
 *  Chiu loi im lang va dat co ve lai: thieu vet GPS thi ban do va dai van ve
 *  duoc, chi la thieu so lieu, con chan ca man hinh thi te hon.
 */
async function napVetGpsChoManTheoDoi() {
  if (dangNapVetGps) return;
  const all = (eplDeliveryOrders && eplDeliveryOrders.length ? eplDeliveryOrders : (dispatchDOs || []));
  if (!all.length) return;
  if (dispatchTrackingByDO && Object.keys(dispatchTrackingByDO).length) return;
  dangNapVetGps = true;
  try {
    await refreshDispatchTrackingMap(all);
  } catch (loi) {
    // PHAI noi ra, khong chi ghi log. Man nay la thap kiem soat: neu vet GPS
    // khong nap duoc thi dai so lieu bao "mat GPS" cho MOI chuyen, va nguoi
    // truc se di goi hang chuc tai xe cho mot su co khong ton tai. Im lang o
    // day dat dung nhung dieu bao dong gia len man hinh.
    console.warn('Khong nap duoc vet GPS cho man Theo doi:', loi && loi.message);
    if (typeof showToast === 'function') {
      showToast('Khong tai duoc vi tri GPS. Cac so lieu "mat GPS" tren man hinh '
        + 'co the la bao dong gia — bam "Cap nhat GPS" de thu lai.', 'error');
    }
  } finally {
    dangNapVetGps = false;
    renderTrackingKpis();
    const oChon = document.getElementById('tracking-active-do-select');
    if (typeof window.renderTrackingDOList === 'function') {
      window.renderTrackingDOList((oChon && oChon.value) || '');
    }
  }
}
//: Sự cố mở, nạp một lần cho cả dải. Để rỗng chứ không để `undefined`, không
//: thì điều kiện nạp lại gọi mãi.
let trackingSuCoMo = null;

/** Mốc thời gian coi là "mất tín hiệu GPS". */
const TRACKING_MAT_GPS_PHUT = 15;

/** Hạn giao của một lệnh: mốc muộn nhất phải giao xong. */
function trackingHanGiao(don) {
  const moc = don.delivery_window_end || don.planned_arrival_at || don.delivery_date;
  if (!moc) return null;
  const d = new Date(moc);
  return isNaN(d) ? null : d;
}

/** Nhóm của một lệnh cho dải số liệu. Một lệnh có thể thuộc nhiều nhóm. */
function trackingNhomCuaDO(don) {
  const nhom = new Set();
  const vet = (typeof dispatchTrackingByDO === 'object' && dispatchTrackingByDO)
    ? dispatchTrackingByDO[don.id] : null;

  // MẤT GPS. Không có vết nào cũng tính là mất: xe đang trên đường mà hệ thống
  // không biết nó ở đâu thì hậu quả y như thiết bị tắt, và người trực phải gọi
  // tài xế trong cả hai trường hợp.
  const mocCuoi = vet && vet.last_update ? new Date(vet.last_update) : null;
  const coGps = Boolean(mocCuoi && !isNaN(mocCuoi));
  if (!coGps) nhom.add('mat-gps');
  else if ((Date.now() - mocCuoi.getTime()) / 60000 > TRACKING_MAT_GPS_PHUT) nhom.add('mat-gps');

  // NGUY CƠ TRỄ: ETA do GPS tính ra muộn hơn hạn giao của đơn. Đây là con số
  // duy nhất trên màn này báo trước được, chứ không báo sau khi đã trễ.
  const han = trackingHanGiao(don);
  const eta = vet && vet.eta ? new Date(vet.eta) : null;
  const coEta = Boolean(eta && !isNaN(eta));
  if (coEta && han && eta > han) nhom.add('nguy-co-tre');

  // ĐÚNG TIẾN ĐỘ chỉ tính khi CÓ đo được: không có GPS thì không thể nói là
  // đúng tiến độ, chỉ là không biết. Gộp "không biết" vào "ổn" là thứ làm người
  // trực yên tâm sai chỗ.
  if (coGps && !nhom.has('mat-gps') && !nhom.has('nguy-co-tre')) nhom.add('dung-tien-do');

  // THIẾU POD: xe đã đến nơi mà chưa ai ký nhận. Đây là chỗ hoá đơn bị treo.
  const tt = String(don.canonical_status || don.status || '');
  const daDen = /arrived|da den|đã đến/i.test(tt);
  if (daDen) {
    const pods = (appState && Array.isArray(appState.pod_records)) ? appState.pod_records : [];
    const daKy = pods.some(p => String(p.do_id || p.delivery_order_id || '') === String(don.id));
    if (!daKy) nhom.add('thieu-pod');
  }

  return nhom;
}

/** Nạp sự cố còn mở, một lần cho cả dải. */
async function napSuCoMoChoTheoDoi() {
  try {
    const tra = await fetch(API_BASE + '/api/incidents', { headers: financeAuthHeaders() });
    if (!tra.ok) { trackingSuCoMo = []; return; }
    const goi = await tra.json();
    const ds = Array.isArray(goi) ? goi : (goi && (goi.data || goi.items)) || [];
    trackingSuCoMo = (Array.isArray(ds) ? ds : []).filter(x =>
      !/closed|resolved|da dong|đã đóng|đã xử/i.test(String(x.status || '')));
  } catch (loi) {
    console.warn('Khong nap duoc su co cho man Theo doi:', loi && loi.message);
    trackingSuCoMo = [];
  }
}

window.setTrackingKpiFilter = function (nhom) {
  trackingKpiFilter = trackingKpiFilter === nhom ? '' : String(nhom || '');
  renderTrackingKpis();
  // Khong co bien "DO dang chon" o man nay; o `select` chinh la noi giu no.
  const oChon = document.getElementById('tracking-active-do-select');
  window.renderTrackingDOList((oChon && oChon.value) || '');
};

function renderTrackingKpis() {
  const host = document.getElementById('tracking-kpis');
  if (!host) return;

  const all = (eplDeliveryOrders && eplDeliveryOrders.length ? eplDeliveryOrders : (dispatchDOs || []));
  const dangChay = all.filter(d => isGpsLiveTrackingStatus(d.canonical_status || d.status));

  if (trackingSuCoMo === null) {
    trackingSuCoMo = [];
    napSuCoMoChoTheoDoi().then(() => renderTrackingKpis());
  }

  const dem = { 'dung-tien-do': 0, 'nguy-co-tre': 0, 'mat-gps': 0, 'thieu-pod': 0 };
  dangChay.forEach(d => trackingNhomCuaDO(d).forEach(n => { if (n in dem) dem[n] += 1; }));

  const soXe = new Set(dangChay.map(d => String(d.vehicle_id || '')).filter(Boolean)).size;
  const soSuCo = (trackingSuCoMo || []).length;

  const the = [
    ['', 'Đang chạy', dangChay.length, soXe + ' xe trên đường', 'blue'],
    ['dung-tien-do', 'Đúng tiến độ', dem['dung-tien-do'], 'có GPS, ETA còn trước hạn', 'green'],
    ['nguy-co-tre', 'Nguy cơ trễ', dem['nguy-co-tre'], 'ETA muộn hơn hạn giao', 'amber'],
    ['mat-gps', 'Mất GPS > ' + TRACKING_MAT_GPS_PHUT + "'", dem['mat-gps'], 'không biết xe đang ở đâu', 'red'],
    // Sự cố không lọc được danh sách DO (một sự cố chưa chắc gắn với DO đang
    // chạy), nên thẻ này CHỈ ĐỂ ĐỌC — `null` làm nó không bấm được, thay vì cho
    // bấm rồi không có gì xảy ra.
    [null, 'Sự cố mở', soSuCo, soSuCo ? 'chưa đóng' : 'không có sự cố nào', 'red'],
    ['thieu-pod', 'Thiếu POD', dem['thieu-pod'], 'đã đến nơi, chưa ký nhận', 'purple'],
  ];

  host.innerHTML = the.map(cap => {
    const ma = cap[0], nhan = cap[1], so = cap[2], phu = cap[3], mau = cap[4];
    const chiDoc = ma === null;
    const tat = !chiDoc && ma !== '' && !so;
    return '<button type="button"'
      + ' class="tracking-kpi tracking-kpi--' + mau
      + (trackingKpiFilter === ma && !chiDoc ? ' is-active' : '') + '"'
      + (chiDoc || tat
        ? ' disabled title="' + (chiDoc ? 'Chỉ để xem' : 'Không có chuyến nào trong nhóm này') + '"'
        : ' onclick="setTrackingKpiFilter(\'' + ma + '\')" title="Bấm để lọc danh sách theo nhóm này"')
      + (chiDoc ? ' aria-disabled="true"' : '')
      + '>'
      + '<span>' + escapeHtml(nhan) + '</span>'
      + '<b>' + Number(so).toLocaleString('vi-VN') + '</b>'
      + '<small>' + escapeHtml(phu) + '</small>'
      + '</button>';
  }).join('');
}

window.renderTrackingDOList = function (selectedDoId = '') {
  const target = document.getElementById('tracking-do-list');
  if (!target) return;
  const query = String(document.getElementById('tracking-do-search')?.value || '').trim().toLowerCase();
  const all = (eplDeliveryOrders && eplDeliveryOrders.length ? eplDeliveryOrders : (dispatchDOs || []));
  let rows = all.filter(item => isGpsLiveTrackingStatus(item.canonical_status || item.status)).filter(item => !query || [item.id,item.vehicle_id,item.driver_id,item.customer_id].join(' ').toLowerCase().includes(query));
  // Loc theo the so lieu dang bam. Dat SAU o tim, truoc khi dem: con so canh
  // dau danh sach phai dung bang so dong dang hien, khong thi no noi mot dieu
  // ma man hinh khong the hien.
  if (trackingKpiFilter) rows = rows.filter(item => trackingNhomCuaDO(item).has(trackingKpiFilter));
  const count = document.getElementById('tracking-live-count');
  if (count) count.textContent = rows.length;
  renderTrackingKpis();
  target.innerHTML = rows.map(item => `<button type="button" class="tracking-do-item ${String(item.id) === String(selectedDoId) ? 'active' : ''}" data-tracking-do="${completionEscape(item.id)}" onclick="onTrackingSelectChange('${completionEscape(item.id)}'); renderTrackingDOList('${completionEscape(item.id)}')"><strong>${completionEscape(item.id)}</strong><span><i class="fa-solid fa-truck"></i> ${completionEscape(item.vehicle_id || 'Chưa gán xe')} · ${completionEscape(item.driver_id || 'Chưa gán tài xế')}</span><b>Đang vận chuyển</b></button>`).join('') || ('<div class="completion-empty">'
    + (trackingKpiFilter
      ? 'Không có chuyến nào trong nhóm đang lọc. Bấm lại thẻ số liệu để bỏ lọc.'
      : 'Không có DO đang vận chuyển.')
    + '</div>');
};

function isPODSelectableStatus(status) {
  const key = String(status || '')
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[\s-]+/g, '_');
  return key === 'in_transit' || key === 'dang_van_chuyen' || key === 'dang_giao_hang' || key === 'arrived' || key === 'da_den';
}

function selectedPODDeliveryOrder(doId = '') {
  const allDOs = (eplDeliveryOrders && eplDeliveryOrders.length > 0 ? eplDeliveryOrders : (dispatchDOs || []));
  return allDOs.find(d => String(d.id || '') === String(doId || '')) || null;
}

window.populatePODDeliverySelector = function (selectedDoId = '') {
  const selectEl = document.getElementById('pod-delivery-do-select');
  if (!selectEl) return;
  const allDOs = (eplDeliveryOrders && eplDeliveryOrders.length > 0 ? eplDeliveryOrders : (dispatchDOs || []));
  const podDOs = allDOs.filter(d => isPODSelectableStatus(d.status || d.canonical_status));
  const sortedDOs = [...podDOs].sort((a, b) => String(a.id || '').localeCompare(String(b.id || '')));
  selectEl.innerHTML = '<option value="">-- Chọn DO đang giao/chờ POD --</option>' + sortedDOs.map(d => {
    const meta = [d.vehicle_id || d.vehicle, d.driver_id || d.driver_name || d.driver, d.customer_id || d.customer].filter(Boolean).join(' • ');
    return `<option value="${escapeCloseoutText(d.id)}">${escapeCloseoutText(d.id)}${meta ? ` (${escapeCloseoutText(meta)})` : ''}</option>`;
  }).join('');
  if (selectedDoId && sortedDOs.some(d => String(d.id) === String(selectedDoId))) {
    selectEl.value = selectedDoId;
    window.previewPODDeliveryDO(selectedDoId);
  }
};

window.previewPODDeliveryDO = function (doId = '') {
  const summary = document.getElementById('pod-selected-do-summary');
  const podBadge = document.getElementById('pod-do-badge');
  if (podBadge) podBadge.innerText = 'Chưa chọn DO';
  if (!summary) return;
  const order = selectedPODDeliveryOrder(doId);
  if (!doId || !order) {
    summary.innerHTML = 'Chưa chọn DO. Chọn một DO rồi bấm Mở form để nhập POD.';
    return;
  }
  const route = order.route_id || order.route || '';
  const vehicle = order.vehicle_id || order.vehicle || 'Chưa gán xe';
  const driver = order.driver_id || order.driver_name || order.driver || 'Chưa gán tài xế';
  summary.innerHTML = `<div style="display:grid; gap:3px;"><strong style="color:#0f172a;">${escapeCloseoutText(doId)}</strong><span>Xe: ${escapeCloseoutText(vehicle)} • Tài xế: ${escapeCloseoutText(driver)}${route ? ` • Tuyến: ${escapeCloseoutText(route)}` : ''}</span></div>`;
};

window.openPODFormForSelectedDO = async function () {
  const selectEl = document.getElementById('pod-delivery-do-select');
  const doId = (selectEl?.value || '').trim();
  if (!doId) {
    showToast('Vui lòng chọn DO cần xác nhận giao hàng trước.');
    return;
  }
  const podBadge = document.getElementById('pod-do-badge');
  const searchInput = document.getElementById('tracking-do-search');
  window.previewPODDeliveryDO(doId);
  if (podBadge) podBadge.innerText = doId;
  if (searchInput) searchInput.value = doId;
  await window.submitPOD();
};

function escapeCloseoutText(value) {
  return escapeHtml(value);
}

function closeoutMoney(value, currency = 'VND') {
  return FormatUtils.formatMoney(value, currency);
}

function isCloseoutReadyStatus(status) {
  const key = String(status || '')
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[\s-]+/g, '_');
  return key === 'delivered' || key === 'completed' || key === 'hoan_thanh' || key === 'da_giao_hang';
}

function populateCloseoutDOSelector(selectedDoId = '') {
  const selectEl = document.getElementById('tracking-closeout-do-select');
  if (!selectEl) return;
  const allDOs = (eplDeliveryOrders && eplDeliveryOrders.length > 0 ? eplDeliveryOrders : (dispatchDOs || []));
  const closeoutDOs = allDOs.filter(d => isCloseoutReadyStatus(d.canonical_status || d.status));
  const sortedDOs = [...closeoutDOs].sort((a, b) => String(a.id || '').localeCompare(String(b.id || '')));
  selectEl.innerHTML = '<option value="">-- Chon DO da giao de xem closeout --</option>' + sortedDOs.map(d => {
    const customer = d.customer_id || d.customer || '';
    const route = d.route_id || d.route || '';
    return `<option value="${escapeCloseoutText(d.id)}">${escapeCloseoutText(d.id)}${customer || route ? ` (${escapeCloseoutText([customer, route].filter(Boolean).join(' - '))})` : ''}</option>`;
  }).join('');
  if (selectedDoId && sortedDOs.some(d => String(d.id) === String(selectedDoId))) {
    selectEl.value = selectedDoId;
  }
}

/**
 * Khối "Lợi nhuận" của hồ sơ sau giao.
 *
 * Máy chủ trả kèm cờ `margin_is_provisional` (bằng true khi chưa có
 * `FreightActualCost`), nhưng bản cũ không dùng cờ đó ở đâu. Chưa có chi phí
 * thực tế thì `actual_cost_total` = 0, nên lợi nhuận = TOÀN BỘ giá bán và
 * `margin_percent` = 100. Ô "Margin 100%" xanh lá là hệ quả của việc thiếu dữ
 * liệu, không phải lãi thật — và đó là con số người ta dùng để đánh giá chuyến.
 */
function khoiLoiNhuanCloseout(data, currency) {
  const tamTinh = Boolean(data?.commercials?.margin_is_provisional);
  const tien = closeoutMoney(data?.commercials?.margin_amount, currency);
  const tiLe = Number(data?.commercials?.margin_percent || 0).toLocaleString('vi-VN');
  if (tamTinh) {
    return `<div style="border:1px solid #fde68a; border-radius:9px; padding:10px; background:#fffbeb;">`
      + `<div style="color:#b45309; font-size:.75rem; font-weight:900;">Lợi nhuận (tạm tính)</div>`
      + `<div style="font-weight:950; color:#b45309;">${tien} (${tiLe}%)</div>`
      + `<div style="font-size:.72rem; color:#92400e; margin-top:3px; font-weight:700;">`
      + `Chưa có chi phí thực tế, nên con số này đang bằng toàn bộ giá bán.</div></div>`;
  }
  return `<div style="border:1px solid #bfdbfe; border-radius:9px; padding:10px; background:#eff6ff;">`
    + `<div style="color:#2563eb; font-size:.75rem; font-weight:900;">Lợi nhuận</div>`
    + `<div style="font-weight:950; color:#2563eb;">${tien} (${tiLe}%)</div></div>`;
}

/**
 * Số chứng từ POD của một điểm giao.
 *
 * Bản cũ đọc `pod.photo_url || pod.signature_url`. Hai cột đó là **cột chết**:
 * `complete_delivery` không bao giờ ghi chúng — ảnh và chữ ký nằm ở bảng
 * `delivery_pod_documents`. Nên POD có đủ biên bản + chữ ký vẫn hiển thị
 * "Chua dinh kem", trong khi `data.pod_documents` ngay trong cùng response đó
 * lại có hai dòng.
 */
function chungTuPOD(data, pod) {
  const tep = (data?.pod_documents || []).filter(doc =>
    String(doc?.pod_record_id || '') === String(pod?.id || ''));
  if (!tep.length) {
    // Còn đọc thêm hai cột cũ: dự liệu lịch sử từ bản trước có thể còn ở đó.
    const cu = pod?.photo_url || pod?.signature_url;
    return cu ? escapeCloseoutText(cu) : 'Chưa đính kèm';
  }
  const loai = tep.map(doc => escapeCloseoutText(doc.document_type || 'tệp')).join(', ');
  return `${tep.length} tệp (${loai})`;
}

/**
 * Một hàng nhãn — giá trị, dùng chung cho mọi khối trong hồ sơ.
 *
 * Giá trị rỗng vẫn hiện dấu gạch chứ không ẩn ô đi: hồ sơ là chứng từ, chỗ
 * trống phải nhìn thấy được để biết là thiếu, không phải biến mất.
 */
function oHoSo(nhan, giaTri) {
  const chu = (giaTri === null || giaTri === undefined || giaTri === "")
    ? "—" : String(giaTri);
  return `<div class="cl-o"><span>${escapeCloseoutText(nhan)}</span>`
    + `<strong>${escapeCloseoutText(chu)}</strong></div>`;
}

/** Mốc thời gian dạng ISO về dạng người đọc được. */
function gioHoSo(giaTri) {
  if (!giaTri) return "";
  const d = new Date(giaTri);
  if (Number.isNaN(d.getTime())) return String(giaTri);
  const hai = n => String(n).padStart(2, "0");
  return `${hai(d.getDate())}/${hai(d.getMonth() + 1)}/${d.getFullYear()}`
    + ` ${hai(d.getHours())}:${hai(d.getMinutes())}`;
}

/**
 * Khối "Thông tin DO đầy đủ" — đúng 18 ô như màn Hoàn tất giao hàng.
 *
 * Đọc từ `data.delivery_order` trong phong bì closeout, KHÔNG từ bộ đệm
 * `eplDeliveryOrders`: hồ sơ là chứng từ nên phải tự đủ. Bộ đệm có thể trống
 * (mở hồ sơ ngay sau khi tải trang) hoặc đã cũ.
 */
function khoiThongTinDOHoSo(data) {
  const d = data.delivery_order || {};
  const o = [
    ["Mã DO", d.id || data.do_id],
    ["Trạng thái", statusLabel(d.canonical_status || data.status) || d.status],
    // DONG "SO THAM CHIEU" DA BO. Buoc Don hang khong con trong luong, nen mot
    // dong luon rong chi lam nguoi doc di tim mot ban ghi khong ton tai. DO cu
    // (tao truoc khi bo buoc do) cung khong con ma don — cot da truc xuat (049).
    ["Báo giá cước", data.quotation_id],
    ["Khách hàng", d.customer_id || data.customer_id],
    ["Mã tuyến", d.route_id || data.route?.id],
    ["Tên tuyến", data.route?.name],
    ["Trip", data.trip?.id],
    ["Điểm đi", d.origin],
    ["Điểm đến", d.destination],
    ["Nhận hàng từ", gioHoSo(d.pickup_window_start) || d.pickup_date],
    ["Nhận hàng đến", gioHoSo(d.pickup_window_end)],
    ["Giao hàng từ", gioHoSo(d.delivery_window_start) || d.delivery_date],
    ["Giao hàng đến", gioHoSo(d.delivery_window_end)],
    ["Xe vận chuyển", d.vehicle_id || data.vehicle_id],
    ["Tài xế", d.driver_id || data.driver_id],
    ["Phụ xe", d.co_driver],
    ["Tải trọng", d.weight_kg ? `${Number(d.weight_kg).toLocaleString("vi-VN")} kg` : ""],
    ["Số pallet", d.pallet_count],
    ["Thể tích", d.volume_m3 ? `${Number(d.volume_m3).toLocaleString("vi-VN")} m³` : ""],
    ["Quy cách đóng gói", d.packaging_spec],
  ];
  return `<section class="cl-khoi">
      <div class="cl-khoi-dau">
        <div><span class="cl-kicker">Lệnh giao hàng</span>
             <h4>Thông tin DO đầy đủ</h4></div>
        <span class="cl-chi-doc"><i class="fa-solid fa-lock"></i> Chỉ đọc</span>
      </div>
      <div class="cl-luoi">${o.map(x => oHoSo(x[0], x[1])).join("")}</div>
    </section>`;
}

/**
 * Khối "Bằng chứng giao hàng" — đầy đủ như màn Hoàn tất giao hàng.
 *
 * Bản trước chỉ hiện địa điểm, người nhận và thời gian, rồi ghi "2 chứng từ"
 * mà không cho mở cái nào. Nay mỗi điểm giao hiện đủ bảy trường, và từng
 * chứng từ là một liên kết tải được — `download_url` đã có sẵn trong phong
 * bì, chỉ là chưa ai dùng.
 */
/**
 * `delivery_result` là mã máy (`delivered_full`...). Hồ sơ là để người đọc,
 * nên phải dịch — và bộ nhãn lấy đúng từ ô chọn ở màn Hoàn tất giao hàng, để
 * hai màn không nói hai kiểu về cùng một kết quả.
 */
function ketQuaGiaoHoSo(ma) {
  if (!ma) return '';
  return {
    delivered_full: 'Giao đủ hàng',
    delivered_partial: 'Giao thiếu hàng',
    delivery_failed: 'Giao không thành công',
    returned: 'Trả hàng về',
  }[String(ma)] || String(ma);
}
function khoiPODHoSo(data) {
  const ds = data.pod_records || [];
  const chungTu = data.pod_documents || [];
  if (!ds.length) {
    return `<section class="cl-khoi"><div class="cl-khoi-dau">
        <div><span class="cl-kicker">Bằng chứng giao hàng</span>
             <h4>POD đã nộp</h4></div></div>
      <div class="cl-trong">Chưa có POD nào cho lệnh này.</div></section>`;
  }
  const diem = ds.map((pod, i) => {
    const tep = chungTu.filter(t => String(t.pod_record_id) === String(pod.id));
    const o = [
      ["Địa điểm giao", pod.location_text],
      ["Thời gian giao thực tế", gioHoSo(pod.delivery_time)],
      ["Kết quả giao", ketQuaGiaoHoSo(pod.delivery_result)],
      ["Người nhận", pod.receiver_name],
      ["Số điện thoại", pod.receiver_phone],
      ["Tình trạng hàng hóa", pod.cargo_condition],
      ["Ghi chú", pod.note],
    ];
    return `<div class="cl-pod">
        <div class="cl-pod-dau">
          <span class="cl-pod-so">${i + 1}</span>
          <strong>Điểm giao ${pod.stop_no || i + 1}</strong>
          <span class="cl-pod-nguoi">${escapeCloseoutText(pod.receiver_name || "Chưa có người nhận")}</span>
        </div>
        <div class="cl-luoi">${o.map(x => oHoSo(x[0], x[1])).join("")}</div>
        <div class="cl-tep">
          <span class="cl-tep-nhan"><i class="fa-solid fa-paperclip"></i>
            Chứng từ (${tep.length})</span>
          ${tep.length
            ? tep.map(t => `<a class="cl-tep-mot" href="${escapeCloseoutText(t.download_url || "#")}"
                  target="_blank" rel="noopener"
                  title="${escapeCloseoutText(t.mime_type || "")}">`
                + `<i class="fa-solid fa-file-arrow-down"></i>`
                + `${escapeCloseoutText(t.file_name || t.id)}</a>`).join("")
            // Không có dòng nào trong `pod_documents` thì vẫn phải đọc hai cột
            // cũ `photo_url` / `signature_url` — dữ liệu lịch sử từ bản trước
            // còn nằm ở đó. `chungTuPOD` đã làm đúng phép dự phòng này.
            : `<span class="cl-tep-thieu">${chungTuPOD(data, pod)}</span>`}
        </div>
      </div>`;
  }).join("");
  return `<section class="cl-khoi">
      <div class="cl-khoi-dau">
        <div><span class="cl-kicker">Bằng chứng giao hàng</span>
             <h4>POD đã nộp</h4></div>
        <span class="cl-dem">${ds.length} điểm giao · ${chungTu.length} chứng từ</span>
      </div>
      ${diem}
    </section>`;
}

function renderDeliveryOrderCloseout(data, target) {
  // `target` tuỳ chọn: màn Theo dõi vẽ vào ô của nó; màn Hoàn tất giao hàng
  // ("Hồ sơ đã hoàn tất") truyền ô riêng — CÙNG MỘT bản vẽ, để anh Khang lấy
  // từng dòng thu/chi có Acc code ở bất kỳ màn nào cũng thấy đúng một bảng.
  target = target || document.getElementById('tracking-closeout-content');
  if (!target) return;
  if (!data || !data.do_id) {
    target.innerHTML = 'Chưa có dữ liệu hồ sơ cho DO đang chọn.';
    return;
  }
  const currency = data.currency || 'VND';
  const tripId = data.trip?.id || '';
  const tm = data.commercials || {};

  // Năm con số tiền: giá ban đầu, khách trả thêm, giá cuối, chi phí, lợi
  // nhuận. Giữ nguyên vì đây là phần đọc nhanh nhất của hồ sơ.
  const soTien = [
    // "Cuoc theo bao gia", khong phai "Gia SO ban dau": con so nay la
    // `unit_price` khoa theo bao gia luc khach chap nhan. Goi no la gia SO la
    // tro nguoi doc sang mot buoc da bi bo khoi luong.
    ["Cước theo báo giá", tm.base_selling_price, "#0f172a", "#f8fafc", "#e2e8f0"],
    ["Khách hàng trả thêm", tm.customer_surcharge_total, "#b45309", "#fff7ed", "#fed7aa"],
    ["Giá cuối DO", tm.selling_price ?? tm.final_selling_price, "#047857", "#f0fdf4", "#bbf7d0"],
    ["Chi phí nội bộ", tm.actual_cost_total, "#b42318", "#fef2f2", "#fecaca"],
  ].map(x => `<div class="cl-tien" style="background:${x[3]}; border-color:${x[4]};">`
      + `<span>${escapeCloseoutText(x[0])}</span>`
      + `<strong style="color:${x[2]};">${closeoutMoney(x[1], currency)}</strong></div>`).join("")
    // Lợi nhuận KHÔNG hiện bằng một con số trần. Máy chủ gửi cờ
    // `margin_is_provisional`; bỏ qua nó là hiện "Lợi nhuận 100%" xanh lá khi
    // chưa có chi phí thực tế — lúc đó lợi nhuận đang bằng đúng toàn bộ giá
    // bán. `khoiLoiNhuanCloseout` đã xử lý đúng chuyện đó nên dùng lại, thay
    // vì viết một ô mới rồi vấp lại đúng cái bẫy cũ.
    + khoiLoiNhuanCloseout(data, currency);

  // Bốn mốc đã ghi vào hệ thống — để biết hồ sơ này đã đi hết luồng chưa.
  const moc = [
    ["Lệnh giao hàng", `${data.do_id} · ${statusLabel(data.status) || data.status || "—"}`],
    ["Trip vận chuyển", tripId ? `${tripId} · ${statusLabel(data.trip?.status) || data.trip?.status || ""}` : "—"],
    ["Hóa đơn phải thu", data.invoice?.id
      ? `${data.invoice.id} · ${statusLabel(data.invoice.canonical_status) || data.invoice.canonical_status || ""}`
      : "Chưa lập hóa đơn"],
    ["Xe & tài xế", [data.resource_release?.vehicle_status, data.resource_release?.driver_status]
      .filter(Boolean).join(" · ") || "—"],
  ].map(x => oHoSo(x[0], x[1])).join("");

  // SỔ THU – CHI TỪNG DÒNG. Đây là phần anh Khang (bên công nợ) lấy để lập
  // phiếu thu / phiếu chi, nên nó phải là TỪNG DÒNG có MÃ COSTINDEX, không phải
  // ba khối tóm tắt như bản trước. Máy chủ gộp ba nguồn — chi theo công thức
  // (đã áp đơn giá của xe), chi thực tế, thu theo báo giá + khách trả thêm —
  // thành `ledger_lines`; ở đây chỉ vẽ, không tính lại con số nào.
  const soDong = Array.isArray(data.ledger_lines) ? data.ledger_lines : [];
  const tong = data.ledger_totals || {};
  const nguonNhan = { vehicle: 'đơn giá của xe', cost_formula: 'công thức loại xe',
    actual_cost: 'phát sinh khi chốt', quotation: 'theo báo giá',
    delivery_order: 'theo lệnh giao', customer_surcharge: 'khách trả thêm' };
  const oMa = d => d.cost_index
    ? `<code class="cl-ma">${escapeCloseoutText(d.cost_index)}</code>`
    : '<code class="cl-ma is-thieu" title="Công thức giá thành chưa chọn Acc code cho khoản mục này">chưa có acc code</code>';
  const dongSo = (kind) => soDong.filter(d => d.kind === kind).map(d => `<tr class="cl-so-dong">
      <td>${oMa(d)}</td>
      <td><strong>${escapeCloseoutText(d.name)}</strong>
          <small>${escapeCloseoutText(nguonNhan[d.source] || d.source || '')}${d.calculation ? ' · ' + escapeCloseoutText(d.calculation) : ''}</small></td>
      <td class="cl-so-tien">${closeoutMoney(d.planned_amount, currency)}</td>
      <td class="cl-so-tien"><b>${closeoutMoney(d.actual_amount, currency)}</b></td>
      <td class="cl-so-tien ${d.kind === 'thu' ? 'cl-so-them' : 'cl-so-lech'}">${
        d.kind === 'thu' ? closeoutMoney(d.customer_extra, currency)
                         : (d.variance ? (d.variance > 0 ? '+' : '') + closeoutMoney(d.variance, currency) : '—')}</td>
    </tr>`).join('');
  const nhomSo = (kind, nhan, tongTien) => `
      <tr class="cl-so-nhom"><td colspan="5">${nhan}</td></tr>
      ${dongSo(kind) || `<tr><td colspan="5" class="cl-trong">Chưa có dòng ${kind}.</td></tr>`}
      <tr class="cl-so-tong"><td colspan="3">Tổng ${kind}</td><td class="cl-so-tien"><b>${closeoutMoney(tongTien, currency)}</b></td><td></td></tr>`;
  const doiChieu = [
    tong.khop_gia_cuoi === false ? 'Tổng thu KHÔNG khớp giá cuối DO' : null,
    tong.khop_gia_thanh === false ? 'Tổng chi KHÔNG khớp giá thành dùng tính lãi' : null,
    tong.so_dong_thieu_ma ? `${tong.so_dong_thieu_ma} dòng chưa có Acc code — chọn ở Dữ liệu gốc → Công thức giá thành` : null,
  ].filter(Boolean);
  const bangSo = soDong.length ? `<section class="cl-khoi cl-so">
      <div class="cl-khoi-dau"><div><span class="cl-kicker">Sổ thu – chi của lệnh giao hàng</span>
        <h4>${soDong.length} dòng · lãi gộp ${closeoutMoney(tong.lai_gop, currency)}</h4></div>
        ${doiChieu.length ? `<span class="cl-dem cl-dem-canh">${doiChieu.map(escapeCloseoutText).join(' · ')}</span>`
                          : '<span class="cl-dem">Tổng thu và tổng chi khớp với hồ sơ</span>'}</div>
      <div class="cl-so-cuon"><table class="cl-so-bang">
        <thead><tr><th>Acc code</th><th>Khoản mục</th><th>Chốt ban đầu</th><th>Thực tế</th><th>Khách trả thêm / Chênh</th></tr></thead>
        <tbody>
          ${nhomSo('thu', 'THU — tiền khách trả', tong.tong_thu)}
          ${nhomSo('chi', 'CHI — chi phí của chuyến (phí của xe)', tong.tong_chi)}
        </tbody>
      </table></div>
    </section>` : '';

  // Ba khối tóm tắt cũ giữ lại làm đường lùi khi máy chủ chưa trả `ledger_lines`
  // (máy chủ cũ) — nhờ vậy hồ sơ vẫn đọc được, chỉ thiếu mã.
  const dongChiPhi = (data.configured_cost_lines || []).map(l => `<div class="cl-dong">
      <span><strong>${escapeCloseoutText(l.name)}</strong>
        <small>${escapeCloseoutText(l.calculation || "")}</small></span>
      <b>${closeoutMoney(l.original_amount, currency)}</b></div>`).join("")
    || '<div class="cl-trong">Chưa có công thức giá thành cho loại xe này.</div>';

  const dongThucTe = (data.actual_cost_lines || []).map(l => `<div class="cl-dong">
      <span><strong>${escapeCloseoutText(l.description || l.charge_type)}</strong>
        <small>${escapeCloseoutText(l.charge_type)}</small></span>
      <b>${closeoutMoney(l.actual_amount ?? l.total_amount, currency)}</b></div>`).join("")
    || '<div class="cl-trong">Chưa ghi chi phí thực tế.</div>';

  const dongPhuThu = (data.customer_charge_adjustments || []).map(l => `<div class="cl-dong">
      <span><strong>${escapeCloseoutText(l.name)}</strong>
        <small>${escapeCloseoutText(l.note || "")}</small></span>
      <b>${closeoutMoney(l.increase_amount ?? l.actual_amount, currency)}</b></div>`).join("")
    || '<div class="cl-trong">Khách hàng không trả thêm khoản nào.</div>';

  target.innerHTML = `
    <div class="cl-goc">
      <div class="cl-bang-tin">
        <div>
          <div class="cl-tieu-de"><i class="fa-solid fa-circle-check"></i>
            Đã cập nhật vào hệ thống</div>
          <div class="cl-phu">Toàn bộ thông tin dưới đây đọc lại từ cơ sở dữ liệu sau khi hoàn tất.</div>
        </div>
        <button type="button" class="fiori-btn" data-closeout-cost-action
          onclick="openCloseoutActualCostEditor('${escapeCloseoutText(data.do_id)}', '${escapeCloseoutText(tripId)}')">
          <i class="fa-solid fa-file-invoice-dollar"></i> Cập nhật giá thực tế / Chốt cước
        </button>
      </div>
      <div class="cl-luoi cl-moc">${moc}</div>
      <div class="cl-tien-hang">${soTien}</div>
      ${khoiThongTinDOHoSo(data)}
      ${bangSo}
      ${khoiPODHoSo(data)}
      <div class="cl-hai-cot" ${soDong.length ? 'hidden' : ''}>
        <section class="cl-khoi">
          <div class="cl-khoi-dau"><div><span class="cl-kicker">Giá thành theo loại xe</span>
            <h4>${escapeCloseoutText(data.cost_formula?.name || "Chưa cấu hình")}</h4></div></div>
          ${dongChiPhi}
        </section>
        <section class="cl-khoi">
          <div class="cl-khoi-dau"><div><span class="cl-kicker">Chi phí thực tế</span>
            <h4>Đã ghi nhận</h4></div></div>
          ${dongThucTe}
        </section>
        <section class="cl-khoi">
          <div class="cl-khoi-dau"><div><span class="cl-kicker">Khách hàng trả thêm</span>
            <h4>${closeoutMoney(tm.customer_surcharge_total, currency)}</h4></div></div>
          ${dongPhuThu}
        </section>
      </div>
    </div>`;
}
window.openCloseoutActualCostEditor = async function (doId = '', tripId = '') {
  if (!doId) {
    showToast('Chua chon DO de cap nhat gia thuc te.');
    return;
  }
  if (typeof window.switchView === 'function') window.switchView('ops-planning', 'fiori-do-list');
  if (typeof window.editFioriDO === 'function') {
    window.editFioriDO(doId);
  } else {
    const input = document.getElementById('do-id');
    if (input) input.value = doId;
  }
  let resolvedTripId = tripId;
  if (!resolvedTripId && typeof loadDOSettlementCost === 'function') {
    const trip = await loadDOSettlementCost(doId);
    resolvedTripId = trip?.id || '';
  }
  const button = document.getElementById('btn-save-do-settlement');
  if (button) {
    button.dataset.tripId = tripId;
    if (resolvedTripId) button.dataset.tripId = resolvedTripId;
    button.dataset.refreshCloseoutDoId = doId;
    button.disabled = !button.dataset.tripId;
    button.style.opacity = button.disabled ? '.58' : '1';
    button.style.cursor = button.disabled ? 'not-allowed' : 'pointer';
  }
  // Trạng thái mở/khóa do `setDOSettlementSaveState` quyết định (nó biết có
  // Trip hoàn thành hay không), nên ở đây chỉ truyền lại đúng thứ đã biết.
  refreshDOSettlementLineControls(Boolean(button?.dataset.tripId),
    button?.dataset.tripId ? "" : lyDoChuaQuyetToanDuoc(doId));
  const panel = document.getElementById('do-settlement-panel');
  if (panel) setTimeout(() => panel.scrollIntoView({ behavior: 'smooth', block: 'center' }), 160);
  showToast(`Da mo form chot cuoc/actual cost cho DO ${doId}.`);
};

window.loadDeliveryOrderCloseout = async function (doId = '') {
  const target = document.getElementById('tracking-closeout-content');
  if (!target || !doId) return;
  target.innerHTML = '<div style="padding:14px; color:#64748b; font-weight:900;">Dang tai ho so closeout tu database...</div>';
  try {
    const response = await fetch(`${API_BASE}/api/delivery-orders/${encodeURIComponent(doId)}/closeout`, {headers:financeAuthHeaders()});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    renderDeliveryOrderCloseout(data);
  } catch (error) {
    console.error(error);
    target.innerHTML = '<div style="padding:14px; color:#b45309; font-weight:900;">Chua doc duoc ho so closeout tu server.</div>';
  }
};

window.showPODCloseoutNextAction = async function (doId = '') {
  if (!doId) return;
  if (typeof window.switchView === 'function') window.switchView('tracking');
  if (typeof window.updateActiveFlowStep === 'function') window.updateActiveFlowStep(6, true);
  if (typeof populateCloseoutDOSelector === 'function') populateCloseoutDOSelector(doId);
  const selector = document.getElementById('tracking-closeout-do-select');
  if (selector) selector.value = doId;
  await window.loadDeliveryOrderCloseout(doId);
  const panel = document.getElementById('tracking-closeout-panel');
  if (panel) setTimeout(() => panel.scrollIntoView({ behavior: 'smooth', block: 'center' }), 120);
  showToast(`Da giao hang DO ${doId}. Mo ho so closeout de cap nhat gia thuc te/chot cuoc.`);
};

function ensureOperationLogPanel() {
  let panel = document.getElementById('operation-log-panel');
  if (panel) return panel;
  panel = document.createElement('div');
  panel.id = 'operation-log-panel';
  panel.style.position = 'fixed';
  panel.style.right = '18px';
  panel.style.bottom = '18px';
  panel.style.width = 'min(420px, calc(100vw - 36px))';
  panel.style.maxHeight = '260px';
  panel.style.overflow = 'auto';
  panel.style.background = '#ffffff';
  panel.style.border = '1px solid #dbeafe';
  panel.style.borderRadius = '10px';
  panel.style.boxShadow = '0 16px 42px rgba(15,23,42,0.16)';
  panel.style.zIndex = '9998';
  panel.style.padding = '10px';
  panel.style.display = 'none';
  panel.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; margin-bottom:8px;">
      <div style="font-weight:950; color:#0f172a; display:flex; align-items:center; gap:7px;"><i class="fa-solid fa-clock-rotate-left" style="color:#2563eb;"></i> Lich su thao tac</div>
      <button type="button" onclick="document.getElementById('operation-log-panel').style.display='none'" style="border:0; background:#eff6ff; color:#2563eb; width:28px; height:28px; border-radius:7px; cursor:pointer;"><i class="fa-solid fa-xmark"></i></button>
    </div>
    <div id="operation-log-list" style="display:grid; gap:7px;"></div>
  `;
  document.body.appendChild(panel);
  return panel;
}

function recordOperationLog({ id, status = 'pending', title = '', detail = '', path = '' } = {}) {
  const panel = ensureOperationLogPanel();
  const list = document.getElementById('operation-log-list');
  if (!list) return '';
  panel.style.display = 'block';
  const itemId = id || `op-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  let item = document.getElementById(itemId);
  if (!item) {
    item = document.createElement('div');
    item.id = itemId;
    list.prepend(item);
  }
  const palette = {
    pending: { bg: '#eff6ff', bd: '#bfdbfe', fg: '#2563eb', icon: 'fa-spinner fa-spin', label: 'Dang xu ly' },
    success: { bg: '#f0fdf4', bd: '#bbf7d0', fg: '#047857', icon: 'fa-circle-check', label: 'Da luu DB' },
    error: { bg: '#fff7ed', bd: '#fed7aa', fg: '#b45309', icon: 'fa-triangle-exclamation', label: 'Loi' },
  }[status] || {};
  item.style.border = `1px solid ${palette.bd}`;
  item.style.background = palette.bg;
  item.style.borderRadius = '8px';
  item.style.padding = '8px 10px';
  item.innerHTML = `
    <div style="display:flex; justify-content:space-between; gap:8px; align-items:flex-start;">
      <div style="font-weight:900; color:#0f172a; overflow-wrap:anywhere;"><i class="fa-solid ${palette.icon}" style="color:${palette.fg}; margin-right:6px;"></i>${fixUIText(title || 'Thao tac')}</div>
      <span style="white-space:nowrap; color:${palette.fg}; font-size:.74rem; font-weight:950;">${palette.label}</span>
    </div>
    <div style="color:#475569; font-size:.78rem; margin-top:4px; overflow-wrap:anywhere;">${fixUIText(detail || '')}</div>
    ${path ? `<div style="color:#94a3b8; font-size:.72rem; margin-top:3px; overflow-wrap:anywhere;">${path}</div>` : ''}
  `;
  while (list.children.length > 6) list.removeChild(list.lastElementChild);
  return itemId;
}

window.recordOperationLog = recordOperationLog;

window.refreshDeliveryOrderCloseout = function () {
  populateCloseoutDOSelector(document.getElementById('tracking-closeout-do-select')?.value || '');
  const selected = document.getElementById('tracking-closeout-do-select')?.value || '';
  if (selected) window.loadDeliveryOrderCloseout(selected);
};

window.onTrackingSelectChange = function (doId) {
  if (!doId) return;
  window.trackDO(doId);
};

window.refreshActiveTracking = function () {
  const selectEl = document.getElementById('tracking-active-do-select');
  const doId = selectEl?.value || '';
  if (doId) {
    window.trackDO(doId);
  } else {
    populateTrackingDOSelector();
    const firstVal = selectEl?.options[1]?.value;
    if (firstVal) {
      selectEl.value = firstVal;
      window.trackDO(firstVal);
    }
  }
};

window.initGPSTrackingMap = async function (vehicleId = '', doId = '') {
  if (window.TrackingControlTower) return window.TrackingControlTower.load(doId);
  const container = document.getElementById('gps-tracking-map');
  if (!container) return;

  if (!gpsTrackingMap && typeof L !== 'undefined') {
    gpsTrackingMap = L.map('gps-tracking-map', { zoomControl: true }).setView([10.8456, 106.7725], 11);

    // Xem ghi chú ở `initLeafletRouteMap`: một nguồn ảnh nền duy nhất là một
    // điểm vỡ đơn, và trên mạng của dự án thì đúng nguồn đó không tới được.
    if (window.LopNenBanDo) window.LopNenBanDo.tao(gpsTrackingMap);
    else L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19, attribution: '&copy; OpenStreetMap'
    }).addTo(gpsTrackingMap);

    gpsTrackingLayerGroup = L.layerGroup().addTo(gpsTrackingMap);
    setTimeout(() => { if (gpsTrackingMap) gpsTrackingMap.invalidateSize(); }, 300);
  } else if (gpsTrackingMap) {
    setTimeout(() => { gpsTrackingMap.invalidateSize(); }, 200);
  }

  // Determine target DO
  const allDOs = (eplDeliveryOrders && eplDeliveryOrders.length > 0 ? eplDeliveryOrders : (dispatchDOs || []));
  const liveDOs = allDOs.filter(d => isGpsLiveTrackingStatus(d.status || d.canonical_status));
  let targetDoId = doId || '';
  if (!targetDoId && vehicleId) {
    const match = liveDOs.find(d => String(d.vehicle_id) === String(vehicleId));
    if (match) targetDoId = match.id;
  }
  if (targetDoId && !liveDOs.some(d => String(d.id || '') === String(targetDoId))) {
    targetDoId = '';
  }
  if (!targetDoId) {
    const candidateId = selectedDispatchCalendarOrderId || tmsActiveTimelineDoId || currentDetailDOId || '';
    targetDoId = liveDOs.some(d => String(d.id || '') === String(candidateId)) ? candidateId : '';
  }
  if (!targetDoId && liveDOs.length > 0) {
    targetDoId = liveDOs[0].id;
  }

  populateTrackingDOSelector(targetDoId);
  if (targetDoId) {
    const selectEl = document.getElementById('tracking-active-do-select');
    if (selectEl) selectEl.value = targetDoId;
    window.trackDO(targetDoId);
  }
};

function renderRealTrackingOnMap(track) {
  if (!gpsTrackingMap || typeof L === 'undefined') return;
  if (!gpsTrackingLayerGroup) gpsTrackingLayerGroup = L.layerGroup().addTo(gpsTrackingMap);
  gpsTrackingLayerGroup.clearLayers();

  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
  const segments = Array.isArray(track.route_segments) ? track.route_segments : [];
  const routePoints = [];
  segments.forEach(seg => {
    if (Number.isFinite(Number(seg.from_lat)) && Number.isFinite(Number(seg.from_lng))) {
      routePoints.push([Number(seg.from_lat), Number(seg.from_lng)]);
    }
    if (Number.isFinite(Number(seg.to_lat)) && Number.isFinite(Number(seg.to_lng))) {
      routePoints.push([Number(seg.to_lat), Number(seg.to_lng)]);
    }
  });

  const truckPoint = [Number(track.lat), Number(track.lng)];
  const hasTruckPoint = Number.isFinite(truckPoint[0]) && Number.isFinite(truckPoint[1]);

  if (routePoints.length > 0) {
    const startSeg = segments[0] || {};
    const endSeg = segments[segments.length - 1] || {};
    const startLabel = lang === 'la' ? '📍 ຈຸດເລີ່ມຕົ້ນ:' : '📍 Điểm đi:';
    const endLabel = lang === 'la' ? '🏁 ຈຸດໝາຍປາຍທາງ:' : '🏁 Điểm đến:';
    L.marker(routePoints[0]).addTo(gpsTrackingLayerGroup).bindPopup(`<b>${startLabel}</b><br>${startSeg.from || (lang === 'la' ? 'ຈຸດເລີ່ມຕົ້ນ' : 'Điểm đi')}`);
    L.marker(routePoints[routePoints.length - 1]).addTo(gpsTrackingLayerGroup).bindPopup(`<b>${endLabel}</b><br>${endSeg.to || (lang === 'la' ? 'ຈຸດໝາຍປາຍທາງ' : 'Điểm đến')}`);
    const polyline = L.polyline(routePoints, { color: '#ef4444', weight: 6, opacity: 0.85 }).addTo(gpsTrackingLayerGroup);
    gpsTrackingMap.fitBounds(polyline.getBounds(), { padding: [40, 40] });
  }

  if (hasTruckPoint) {
    snappedCoordOnRoute = truckPoint;
    const vehLabel = lang === 'la' ? 'àº¥àº»àº”' : 'Xe';
    const doLabel = lang === 'la' ? 'ລະຫັດ DO' : 'Mã DO';
    const drvLabel = lang === 'la' ? 'ຄົນຂັບ' : 'Tài xế';
    const routeLabel = lang === 'la' ? 'ເສັ້ນທາງ' : 'Tuyến';
    gpsTruckMarker = L.marker(truckPoint, { title: track.vehicle_id || '' }).addTo(gpsTrackingLayerGroup)
      .bindPopup(`<b>🚛 ${vehLabel}: ${track.vehicle_id || (lang === 'la' ? 'ຍັງບໍ່ໄດ້ກຳນົດ' : 'Chưa gán xe')}</b><br>${doLabel}: ${track.do_id}<br>${drvLabel}: ${escapeHtml(track.driver_name || (lang === 'la' ? 'ຍັງບໍ່ໄດ້ກຳນົດ' : 'Chưa gán'))}<br>${routeLabel}: ${track.route_name || (lang === 'la' ? 'ບໍ່ມີເສັ້ນທາງ' : 'Chưa có tuyến')}`)
      .openPopup();
    if (routePoints.length === 0) gpsTrackingMap.setView(truckPoint, 13);
  }
}

function updateTrackingHeader(track) {
  const liveLabel = document.getElementById('gps-live-label');
  const podBadge = document.getElementById('pod-do-badge');
  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';

  if (liveLabel) {
    if (track) {
      const vehText = lang === 'la' ? 'àº¥àº»àº”' : 'Xe';
      liveLabel.innerHTML = `<i class="fa-solid fa-circle" style="color:#10b981; font-size:.55rem;"></i> GPS Live Tracking: ${vehText} ${track.vehicle_id || (lang === 'la' ? 'ຍັງບໍ່ໄດ້ກຳນົດ' : 'Chưa gán xe')} • ${track.do_id}`;
    } else {
      liveLabel.innerHTML = `<i class="fa-solid fa-circle" style="color:#94a3b8; font-size:.55rem;"></i> GPS Live Tracking: ${lang === 'la' ? 'ຍັງບໍ່ໄດ້ເລືອກໃບສັ່ງ DO' : 'Chưa chọn lệnh DO'}`;
    }
  }
  if (podBadge) podBadge.innerText = track?.do_id || (lang === 'la' ? 'ຍັງບໍ່ໄດ້ເລືອກ DO' : 'Chưa chọn DO');
}

function resetTrackingLiveMetrics() {
  const speed = document.getElementById('track-speed');
  const distance = document.getElementById('track-dist');
  const eta = document.getElementById('track-eta');
  if (speed) speed.innerText = '-- km/h';
  if (distance) distance.innerText = '-- km';
  if (eta) eta.innerText = '--:--';
  updateTrackingHeader(null);
  if (gpsTrackingLayerGroup) gpsTrackingLayerGroup.clearLayers();
  gpsTruckMarker = null;
}

function formatTrackingMetric(value, unit) {
  if (value === null || value === undefined || value === '') return `-- ${unit}`;
  const numericValue = Number(value);
  return Number.isFinite(numericValue)
    ? `${numericValue.toLocaleString('vi-VN')} ${unit}`
    : `-- ${unit}`;
}

window.trackDO = async function (targetDoId = null) {
  if (window.TrackingControlTower) return window.TrackingControlTower.load(targetDoId);
  const selectEl = document.getElementById('tracking-active-do-select');
  const doId = (targetDoId || selectEl?.value || document.getElementById('tracking-do-search')?.value || '').trim();
  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';

  if (!doId) {
    showToast(lang === 'la' ? 'ກະລຸນາເລືອກ ຫຼື ປ້ອນລະຫັດ DO ເພື່ອຕິດຕາມ.' : 'Vui lòng chọn hoặc nhập mã DO cần theo dõi.');
    return;
  }

  if (selectEl && selectEl.value !== doId) {
    selectEl.value = doId;
  }

  const allDOs = (eplDeliveryOrders && eplDeliveryOrders.length > 0 ? eplDeliveryOrders : (dispatchDOs || []));
  const matchedDO = allDOs.find(d => String(d.id) === String(doId)) || {};
  if (matchedDO.id && !isGpsLiveTrackingStatus(matchedDO.status || matchedDO.canonical_status)) {
    if (selectEl) selectEl.value = '';
    updateTrackingHeader(null);
    const statusText = statusLabel(matchedDO.status || matchedDO.canonical_status || '');
    showToast(lang === 'la'
      ? 'ຕິດຕາມ GPS ໄດ້ສະເພາະໃບສັ່ງທີ່ກຳລັງຂົນສົ່ງ.'
      : `Chỉ tracking GPS khi DO đang vận chuyển. DO này đang ở trạng thái: ${statusText || 'chưa chạy'}.`);
    return;
  }

  try {
    if (!gpsTrackingMap && typeof L !== 'undefined') {
      await window.initGPSTrackingMap();
    }
    const res = await fetch(`${API_BASE}/api/tracking/${encodeURIComponent(doId)}`);
    if (!res.ok) {
      let message = lang === 'la'
        ? 'ບໍ່ສາມາດອ່ານຂໍ້ມູນ GPS ຈາກເຊີບເວີ.'
        : 'Không lấy được dữ liệu GPS thật từ máy chủ.';
      try {
        const payload = await res.json();
        const detail = payload?.detail?.message || payload?.error?.message || payload?.detail;
        if (typeof detail === 'string' && detail.trim()) message = detail;
      } catch (error) {
        // The HTTP status still identifies the failed server request.
      }
      resetTrackingLiveMetrics();
      showToast(`⚠️ ${message}`);
      if (typeof renderGpsEventTimeline === 'function') renderGpsEventTimeline();
      return;
    }
    const track = await res.json();

    // Ba con so nay TRONG nhu do tu thiet bi, nhung khong phai:
    //
    //   · `speed_kmh` duoc dat CUNG bang 0 luc dieu xe (workflow_service va
    //     tms_dispatch_service deu ghi `speed_kmh = 0`), va khong co giao dien
    //     nao gui toa do len. Nen "0 km/h" duoi nhan "TOC DO HIEN TAI" la mot
    //     con so khong do duoc, khong phai xe dang dung.
    //
    //   · `remaining_distance_km` la TONG chieu dai tuyen ghi luc dieu xe,
    //     khong phai khoang cach con lai thuc te.
    //
    //   · `eta` la `planned_arrival_at` — GIO DEN THEO KE HOACH, khong phai
    //     du bao tu GPS. No lai la cot String nen du lieu mau nhet duoc
    //     '15:30 PM' vao.
    //
    // Chua co toa do thi khong khang dinh gi: hien dau gach va noi ro vi sao.
    const coToaDo = track && track.lat != null && track.lng != null;
    const dat = (id, chu, chu_thich) => {
      const node = document.getElementById(id);
      if (!node) return;
      node.innerText = chu;
      if (chu_thich) node.title = chu_thich;
    };

    if (coToaDo) {
      dat('track-speed', formatTrackingMetric(track.speed_kmh, 'km/h'));
    } else {
      dat('track-speed', '—',
        'Chưa có tọa độ từ thiết bị, nên chưa đo được tốc độ.');
    }

    // Doi nhan cho dung nghia: day la tong chieu dai tuyen, khong phai phan
    // con lai. Nhan tren trang duoc sua theo (xem index.html).
    dat('track-dist', formatTrackingMetric(track.remaining_distance_km, 'km'),
      'Tổng chiều dài tuyến ghi lúc điều xe.');

    dat('track-eta', track.eta || '--:--',
      'Giờ đến theo KẾ HOẠCH, không phải dự báo từ GPS.');
    updateTrackingHeader(track);
    renderRealTrackingOnMap(track);
    if (typeof renderGpsEventTimeline === 'function') renderGpsEventTimeline();
  } catch (e) {
    console.error(e);
    resetTrackingLiveMetrics();
    showToast(lang === 'la' ? 'ເກີດຂໍ້ຜິດພາດໃນການດຶງຂໍ້ມູນ GPS ຈາກເຊີບເວີ.' : 'Lỗi kết nối khi lấy dữ liệu GPS từ server.');
    if (typeof renderGpsEventTimeline === 'function') renderGpsEventTimeline();
  }
};

window.loadDispatchBoard = loadDispatchBoard;

// ==========================================
// ACCOUNTING & DASHBOARD
// ==========================================

/**
 * Nap hoa don va so cai.
 *
 * Ba loi cua ban cu:
 *
 *   1. `if (resInv.ok)` va `if (resGL.ok)` KHONG co nhanh else. Hai bang khoi
 *      tao bang chu "Dang tai hoa don..." / "Dang tai So Cai...", nen goi API
 *      that bai la hai bang giu nguyen dong do VINH VIEN — khong toast, khong
 *      dau hieu. Nguoi dung khong phan biet duoc "chua co hoa don" voi
 *      "khong ket noi duoc".
 *
 *   2. `inv.total.toLocaleString()` va `gl.debit.toLocaleString()` khong co
 *      guard. Mot ban ghi co total/debit/credit la NULL se nem TypeError giua
 *      forEach, nen bang dung o nua dong va phan con lai mat — ma loi bi
 *      `catch` o duoi nuot im.
 *
 *   3. `innerHTML +=` trong vong lap: moi vong parse lai toan bo chuoi HTML
 *      dang phinh. Dung mot lan `join('')` thay vi vay.
 */
async function loadAccountingData() {
  const bao_khong_nap_duoc = (id, so_cot, trang_thai) => {
    const tbody = document.getElementById(id);
    if (!tbody) return;
    const ly_do = trang_thai === 401 || trang_thai === 403
      ? 'Không có quyền xem số liệu kế toán.'
      : trang_thai
        ? `Máy chủ trả lỗi HTTP ${trang_thai}.`
        : 'Không kết nối được tới máy chủ.';
    // Dau gach, KHONG phai so 0: mot con so 0 tu tin te hon mot dau gach.
    tbody.innerHTML = `<tr><td colspan="${so_cot}" style="text-align:center; padding:18px; color:#b45309;">`
      + `<i class="fa-solid fa-triangle-exclamation" aria-hidden="true"></i> `
      + `Chưa nạp được — ${escapeHtml(ly_do)}</td></tr>`;
  };

  let resInv = null;
  let resGL = null;
  try {
    [resInv, resGL] = await Promise.all([
      fetch(`${API_BASE}/api/invoices`),
      fetch(`${API_BASE}/api/gl-transactions`)
    ]);
  } catch (e) {
    console.error("Failed to load accounting data", e);
    bao_khong_nap_duoc('fiori-invoice-tbody', 6, 0);
    bao_khong_nap_duoc('fiori-gl-tbody', 4, 0);
    showToast('❌ Không nạp được số liệu kế toán từ máy chủ.');
    return;
  }

  // Tien luon lay qua `|| 0`: mot ban ghi NULL khong duoc lam vo ca bang.
  const tien = gia_tri => Number(gia_tri || 0).toLocaleString('vi-VN');

  if (resInv.ok) {
    const invoices = await resInv.json().catch(() => []);
    const tbody = document.getElementById('fiori-invoice-tbody');
    if (tbody) {
      tbody.innerHTML = (Array.isArray(invoices) ? invoices : []).length
        ? invoices.map(inv => `
            <tr>
              <td><strong>${escapeHtml(inv.id)}</strong></td>
              <td>${escapeHtml(inv.customer_id || '—')}</td>
              <td>${escapeHtml(inv.do_id || '—')}</td>
              <td>${escapeHtml(inv.invoice_date || '—')}</td>
              <td>${tien(inv.total)}</td>
              <td><span class="fiori-status status-transit">${escapeHtml(statusLabel(inv.status))}</span></td>
            </tr>`).join('')
        : `<tr><td colspan="6" style="text-align:center;">${t('msg_no_invoices_yet')}</td></tr>`;
    }
  } else {
    bao_khong_nap_duoc('fiori-invoice-tbody', 6, resInv.status);
  }

  if (resGL.ok) {
    const glList = await resGL.json().catch(() => []);
    const tbody = document.getElementById('fiori-gl-tbody');
    if (tbody) {
      tbody.innerHTML = (Array.isArray(glList) ? glList : []).length
        ? glList.map(gl => `
            <tr>
              <td>${escapeHtml(gl.date || '—')}</td>
              <td><strong>${escapeHtml(gl.account_code || '—')}</strong></td>
              <td style="color:#2bba66;">${tien(gl.debit)}</td>
              <td style="color:#e53935;">${tien(gl.credit)}</td>
            </tr>`).join('')
        : `<tr><td colspan="4" style="text-align:center;">${t('msg_no_gl_entries')}</td></tr>`;
    }
  } else {
    bao_khong_nap_duoc('fiori-gl-tbody', 4, resGL.status);
  }

  if (!resInv.ok || !resGL.ok) {
    showToast('⚠️ Một phần số liệu kế toán chưa nạp được. Xem chi tiết trong bảng.');
  }

  if (typeof renderFinanceCockpit === 'function') renderFinanceCockpit();
  if (typeof renderFinanceActionWorkbench === 'function') renderFinanceActionWorkbench();

}

async function loadDashboard() {
  // Cố tình KHÔNG gọi TransportReporting.load() ở đây. loadDashboard() chạy
  // khi mở cả Bảng điều khiển lẫn màn "Báo cáo & Phân tích", nên kéo theo
  // TransportReporting nghĩa là mở màn Báo cáo lại đi vẽ chart của màn
  // "Tóm tắt & Phân tích" — trong khi màn đó đang display:none nên canvas
  // rộng 0px và chart hỏng khi người dùng chuyển sang. Màn Tóm tắt tự gọi
  // TransportReporting.load() trong switchView của chính nó.
  try {
    const res = await fetch(`${API_BASE}/api/dashboard/stats`);
    if (!res.ok) {
      // KHONG duoc de nguyen cac o KPI. Truoc day nhanh nay im lang, nen khi
      // token het han (401) man hinh van hien "0 VND / 0 Lenh DO / 0 Chuyen"
      // — nguoi dung doc ra la MAT SACH DU LIEU, trong khi that ra chi la
      // khong tai duoc. Mot con so 0 tu tin con te hon mot dau gach.
      markDashboardUnavailable(res.status);
      return;
    }
    {
      const data = await res.json();

      const currUnit = (typeof t === 'function' && t('unit_currency')) ? t('unit_currency') : 'VNĐ';
      const orderUnit = (typeof t === 'function' && t('unit_order')) ? t('unit_order') : 'Lệnh DO';
      const tripUnit = (typeof t === 'function' && t('unit_trip')) ? t('unit_trip') : 'Chuyến';
      const incUnit = (typeof t === 'function' && t('unit_incident')) ? t('unit_incident') : 'Sự cố';

      // Chỉ Bảng điều khiển hiển thị các số này. Hàng KPI trong workspace
      // Phân tích (#kpi-revenue, #kpi-deliveries, #kpi-vehicles) đã được dỡ vì
      // nó là bản sao của hàng này, lấy từ endpoint khác với bảng P&L ngay bên
      // dưới nó — nên màn đó hiện hai con số doanh thu cạnh nhau.
      const elRevenue = document.getElementById('stat-revenue');
      if (elRevenue) {
        elRevenue.innerText = `${(data.revenue_ytd || 0).toLocaleString()} ${currUnit}`;
      }

      const elOrders = document.getElementById('stat-dos');
      if (elOrders) {
        elOrders.innerText = `${data.total_deliveries || 0} ${orderUnit}`;
      }

      // Số LỆNH GIAO HÀNG đang lăn bánh — không phải số xe. Trước đây trường
      // active_vehicles của backend bị gán vào cả ô này và ô "Số xe hoạt
      // động", và chúng trùng khớp chỉ vì đội xe demo tình cờ cũng có 3 chiếc.
      const inTransitOrders = data.in_transit_orders ?? data.active_vehicles ?? 0;
      const elTransit = document.getElementById('stat-transit');
      if (elTransit) elTransit.innerText = `${inTransitOrders} ${tripUnit}`;

      const elInc = document.getElementById('stat-incidents');
      if (elInc) {
        elInc.innerText = `${data.incidents_count || 0} ${incUnit}`;
      }

    }
  } catch (e) {
    console.error("Failed to load dashboard data", e);
    markDashboardUnavailable(0);
  }
}

/**
 * Bao that rang Bang dieu khien khong tai duoc so lieu.
 *
 * Dat dau gach thay vi so, va noi ro nguyen nhan khi la 401 — do gan nhu luon
 * la token API chua duoc dat trong trinh duyet nay, khong phai du lieu bi mat.
 */
function markDashboardUnavailable(status) {
  const tiles = [
    ['stat-revenue', 'unit_currency', 'VNĐ'],
    ['stat-dos', 'unit_order', 'Lệnh DO'],
    ['stat-transit', 'unit_trip', 'Chuyến'],
    ['stat-incidents', 'unit_incident', 'Sự cố'],
  ];
  tiles.forEach(([id, key, fallback]) => {
    const el = document.getElementById(id);
    if (!el) return;
    const unit = (typeof t === 'function' && t(key)) ? t(key) : fallback;
    el.innerText = `— ${unit}`;
    el.title = 'Chưa tải được số liệu từ máy chủ.';
  });

  if (typeof showToast !== 'function') return;
  if (status === 401 || status === 403) {
    // api-auth.js da bao ve token roi, nen o day chi noi ro y nghia cua cac
    // o dang trong, khong lap lai huong dan.
    showToast('Chưa tải được số liệu Bảng điều khiển vì máy chủ từ chối phiên làm việc. Dữ liệu trong cơ sở dữ liệu vẫn còn nguyên.', 'error');
  } else {
    showToast('Chưa tải được số liệu Bảng điều khiển. Kiểm tra kết nối tới máy chủ rồi tải lại trang.', 'error');
  }
}

window.loadAccountingData = loadAccountingData;
window.loadDashboard = loadDashboard;

// ==========================================
// WAREHOUSE & SHIPMENT EXECUTION (Legacy helpers - main logic below at line ~4920)
// ==========================================

function normalizeMasterFormType(formType) {
  const type = String(formType || '').toLowerCase().replace(/_/g, '-');
  if (['qt', 'quotation', 'quote'].includes(type)) return 'qt';
  if (['so', 'sales-order', 'salesorder', 'order'].includes(type)) return 'so';
  if (['do', 'delivery-order', 'deliveryorder'].includes(type)) return 'do';
  return type;
}

window.sendMasterForm = function (formType) {
  const type = normalizeMasterFormType(formType);
  if (type === 'qt' && typeof window.approveQuotation === 'function') {
    window.approveQuotation();
    return;
  }
  if (type === 'so' && typeof window.approveSO === 'function') {
    window.approveSO();
    return;
  }
  showToast('Hành động này chưa có API ghi DB. Vui lòng dùng nút Lưu/Duyệt trong luồng nghiệp vụ.');
};

window.submitMasterForm = function (formType) {
  const type = normalizeMasterFormType(formType);
  if (type === 'qt' && typeof window.approveQuotation === 'function') {
    window.approveQuotation();
    return;
  }
  if (type === 'so' && typeof window.approveSO === 'function') {
    window.approveSO();
    return;
  }
  showToast('Hành động này chưa có API ghi DB. Vui lòng dùng nút Lưu/Duyệt trong luồng nghiệp vụ.');
};

window.publishMasterForm = function (formType) {
  // Trigger dispatch submit if on dispatch screen
  if (typeof window.submitDispatch === 'function') {
    window.submitDispatch();
  } else {
    showToast('Không thể phát lệnh: chức năng điều phối chưa sẵn sàng.');
  }
};

/* `window.postInvoice` ĐÃ BỎ — mã chết, và là mã chết nguy hiểm.
 *
 * Nó ghi một hoá đơn thật cùng bút toán sổ cái qua `POST /api/invoices/post`,
 * chọn lệnh giao hàng bằng "lệnh đã giao ĐẦU TIÊN tìm thấy" chứ không phải thứ
 * người dùng chọn. Chỗ gọi duy nhất của nó là nút "Post" trên một thẻ MINH HOẠ
 * ở Bảng điều khiển — thẻ mà mọi ô nhập đều `disabled`. Nút đó đã bỏ, nên hàm
 * này không còn ai gọi.
 *
 * VÀ KHÔNG MẤT TÍNH NĂNG NÀO. Hoá đơn được phát hành NGAY TRONG bước hoàn tất
 * giao hàng: `delivery_completion_service` gọi `post_ar_invoice` trong cùng một
 * giao dịch với POD và giá cuối. Đó là lý do bộ dữ liệu demo có hoá đơn mà
 * không ai bấm "Post" lần nào.
 *
 * `POST /api/invoices/post` vẫn còn ở máy chủ, làm cửa lập hoá đơn thủ công cho
 * những đơn cũ chưa đi qua đường hoàn tất. Nó không có màn nào gọi — xem
 * `docs/ra-soat-nut-va-luong.md`.
 */

window.submitIncident = function () {
  if (typeof window.submitIncidentReport === 'function') {
    window.submitIncidentReport();
    return;
  }
  showToast('Không tìm thấy form sự cố để ghi DB. Vui lòng tải lại trang rồi thử lại.');
};

window.openIncidentModal = async function () {
  const panel = document.getElementById('incident-form-panel');
  if (panel) panel.style.display = 'flex';

  // Hai ô chọn này quyết định sự cố được gắn vào ĐƠN NÀO và XE NÀO. Nạp
  // hỏng mà im lặng thì ô chọn giữ nguyên các lựa chọn cũ trong index.html,
  // và người dùng khai một sự cố thật vào một mã đơn không còn tồn tại.
  try {
    const resDo = await fetch(`${API_BASE}/api/delivery-orders`);
    const doSelect = document.getElementById('inc-do-id');
    if (!resDo.ok) {
      baoNapThatBai('danh sách lệnh giao hàng cho ô chọn sự cố',
        new Error(`Máy chủ trả về ${resDo.status}`));
    } else if (doSelect) {
      const dos = paginatedItems(await resDo.json());
      if (dos && dos.length > 0) {
        // Mã đơn và tên tuyến do người dùng đặt, và chúng đi thẳng vào
        // thuộc tính `value` — phải thoát ký tự.
        doSelect.innerHTML = dos.map(d =>
          `<option value="${escapeHtml(d.id)}">${escapeHtml(d.id)}`
          + ` (${escapeHtml(d.route_id || 'Tuyến chính')})</option>`).join('');
      }
    }

    const resVeh = await fetch(`${API_BASE}/api/vehicles`);
    const vehSelect = document.getElementById('inc-veh-id');
    if (!resVeh.ok) {
      baoNapThatBai('danh sách phương tiện cho ô chọn sự cố',
        new Error(`Máy chủ trả về ${resVeh.status}`));
    } else if (vehSelect) {
      // `/api/vehicles` KHÔNG kèm `paginated=true` thì trả về mảng thuần,
      // không phải phong bì `{items:[...]}` — đừng gọi paginatedItems ở đây,
      // nó trả về mảng rỗng cho mọi thứ không phải phong bì.
      const vehs = await resVeh.json();
      if (vehs && vehs.length > 0) {
        vehSelect.innerHTML = vehs.map(v =>
          `<option value="${escapeHtml(v.id)}">${escapeHtml(v.id)}`
          + ` (${escapeHtml(v.type || 'Xe tải')})</option>`).join('');
      }
    }
  } catch (e) {
    baoNapThatBai('danh sách cho ô chọn sự cố', e);
  }
};

window.closeIncidentModal = function () {
  const panel = document.getElementById('incident-form-panel');
  if (panel) panel.style.display = 'none';
};

window.loadIncidents = async function () {
  try {
    const res = await fetch(`${API_BASE}/api/incidents`);
    const driversRes = await fetch(`${API_BASE}/api/drivers`);
    let drivers = [];
    if (driversRes.ok) {
      drivers = await driversRes.json();
    }

    if (res.ok) {
      const list = await res.json();
      const tbody = document.getElementById('incidents-tbody');
      if (tbody) {
        tbody.innerHTML = '';
        list.forEach(inc => {
          let mainDriver = drivers.find(d => d.assigned_vehicle === inc.vehicle_id && d.role === 'Lái xe chính')?.name || '-';
          let coDriver = drivers.find(d => d.assigned_vehicle === inc.vehicle_id && d.role === 'Phụ xe')?.name || '-';

          tbody.insertAdjacentHTML('beforeend', `
            <tr style="border-bottom: 1px solid #f1f5f9;">
              <td style="padding: 10px 14px; font-size: 0.83rem; color: #64748b;">${inc.reported_at || 'Vừa mới đây'}</td>
              <td style="padding: 10px 14px; font-weight: 700; color: #2563eb;">${inc.do_id}</td>
              <td style="padding: 10px 14px; font-weight: 600; color: #1e293b;">${inc.vehicle_id}</td>
              <td style="padding: 10px 14px; font-weight: 600; color: #1e293b;">${mainDriver}</td>
              <td style="padding: 10px 14px; font-weight: 600; color: #1e293b;">${coDriver}</td>
              <td style="padding: 10px 14px; font-weight: 700; color: #dc2626;">${inc.incident_type}</td>
              <td style="padding: 10px 14px; font-size: 0.85rem; color: #334155;">${inc.location}</td>
              <td style="padding: 10px 14px; font-size: 0.85rem; color: #475569;">${escapeHtml(inc.description || 'Không có mô tả chi tiết')}</td>
            </tr>
          `);
        });
        if (list.length === 0) {
          tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding: 15px; color: #64748b;">Chưa có sự cố nào được khai báo trong hệ thống.</td></tr>`;
        }
      }
    }
  } catch (e) {
    baoNapThatBai('danh sách sự cố', e);
  }
};

/**
 * Gửi báo cáo sự cố.
 *
 * Bản cũ luôn thất bại nhưng luôn báo thành công, do ba lỗi cộng lại:
 *
 *   1. Máy chủ BẮT BUỘC trường `reporter`, mà payload không gửi nó (form cũng
 *      không có ô nào để nhập) → máy chủ luôn trả 422.
 *   2. Không kiểm `res.ok`.
 *   3. Phong bì lỗi của máy chủ là `{error, detail}`, không có khóa `message`,
 *      nên `data.message` là undefined và rơi vào chuỗi mặc định
 *      "Báo cáo sự cố thành công!".
 *
 * Hệ quả: người dùng nhập sự cố, thấy báo thành công, form đóng lại, và không
 * một dòng nào được ghi. Đây là nghiệp vụ khẩn cấp.
 */
window.submitIncidentReport = async function () {
  const do_id = document.getElementById('inc-do-id')?.value || '';
  const vehicle_id = document.getElementById('inc-veh-id')?.value || '';
  const incident_type = document.getElementById('inc-type')?.value || '';
  const location = document.getElementById('inc-location')?.value || '';
  const description = document.getElementById('inc-desc')?.value || '';
  const reporter = document.getElementById('inc-reporter')?.value?.trim() || '';

  // Chặn ngay tại đây những trường máy chủ bắt buộc, để người dùng biết phải
  // điền gì thay vì nhận một lỗi 422 không ai đọc.
  const thieu = [
    [do_id, 'Lệnh giao hàng'],
    [vehicle_id, 'Xe'],
    [incident_type, 'Loại sự cố'],
    [location, 'Vị trí hiện tại'],
    [reporter, 'Người báo cáo'],
  ].filter(([gia_tri]) => !gia_tri).map(([, ten]) => ten);
  if (thieu.length) {
    showToast(`⚠️ Chưa gửi được — còn thiếu: ${thieu.join(', ')}.`);
    return;
  }

  showToast(`⏳ Đang gửi báo cáo sự cố khẩn cấp cho Ban Điều Hành...`);

  try {
    const res = await fetch(`${API_BASE}/api/incidents`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ do_id, vehicle_id, incident_type, location, description, reporter })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      // Giữ form MỞ: đóng nó là xóa mất những gì người dùng vừa nhập, trong khi
      // chưa có gì được ghi lại cả.
      const chi_tiet = data?.error?.message || data?.detail || data?.message || `HTTP ${res.status}`;
      showToast(`❌ Không gửi được báo cáo sự cố: ${typeof chi_tiet === 'string' ? chi_tiet : JSON.stringify(chi_tiet)}`);
      return;
    }
    showToast(data.message || '✅ Đã ghi nhận báo cáo sự cố.');
    closeIncidentModal();
    loadIncidents();
    if (typeof loadDashboard === 'function') loadDashboard();
  } catch (e) {
    console.error(e);
    showToast('❌ Lỗi kết nối khi gửi báo cáo sự cố. Báo cáo CHƯA được ghi.');
  }
};

let leafletRouteMap = null;

/* ==========================================================================
   Nút "Vệ Tinh" trên bản đồ lộ trình.

   Trước đây nút này chỉ chạy `showToast('Đang bật chế độ Vệ Tinh!')` rồi
   thôi — bản đồ không đổi một pixel nào. Người dùng bấm, thấy chữ "đang bật",
   rồi ngồi đợi một thứ không bao giờ tới.

   Ảnh vệ tinh lấy từ Esri World Imagery: cùng chuẩn tile {z}/{y}/{x} như
   OpenStreetMap nên đổi lớp nền là đủ, không cần thư viện gì thêm.
   ========================================================================== */

let lopNenDuong = null;      // lớp nền bản đồ đường
let lopNenVeTinh = null;     // lớp nền ảnh vệ tinh
let dangDungVeTinh = false;

const NEN_VE_TINH = 'https://server.arcgisonline.com/ArcGIS/rest/services'
  + '/World_Imagery/MapServer/tile/{z}/{y}/{x}';

window.doiNenBanDoLoTrinh = function () {
  if (!leafletRouteMap || typeof L === 'undefined') {
    // Chưa mở màn bản đồ thì chưa có gì để đổi. Nói thật thay vì báo "đã bật".
    showToast('⚠️ Bản đồ chưa sẵn sàng. Hãy chọn một tuyến đường trước.');
    return;
  }
  if (!lopNenVeTinh) {
    lopNenVeTinh = L.tileLayer(NEN_VE_TINH, {
      maxZoom: 19,
      attribution: 'Ảnh vệ tinh &copy; Esri'
    });
  }
  if (dangDungVeTinh) {
    leafletRouteMap.removeLayer(lopNenVeTinh);
    if (lopNenDuong) lopNenDuong.addTo(leafletRouteMap);
    dangDungVeTinh = false;
    showToast('🗺️ Đã chuyển về bản đồ đường.');
  } else {
    if (lopNenDuong) leafletRouteMap.removeLayer(lopNenDuong);
    lopNenVeTinh.addTo(leafletRouteMap);
    dangDungVeTinh = true;
    showToast('🛰️ Đã bật ảnh vệ tinh.');
  }
  const nut = document.getElementById('nut-nen-ve-tinh');
  if (nut) {
    const nhan = nut.querySelector('span');
    if (nhan) nhan.textContent = dangDungVeTinh ? 'Bản đồ đường' : 'Vệ Tinh';
  }
};
let routeMapLayersGroup = null;

window.clearLeafletRouteMap = function () {
  if (routeMapLayersGroup) {
    routeMapLayersGroup.clearLayers();
  }
  // Xoa ghim thi phai xoa ca chu giai, khong de lai chu giai cua tuyen cu.
  if (typeof renderRouteWaypointLegend === 'function') renderRouteWaypointLegend([]);
};

/**
 * Thanh chu giai duoi ban do: liet ke cac diem THEO THU TU DI, kem dot mau va
 * so thu tu khop voi ghim tren ban do.
 *
 * Truoc day thanh nay chi hien mot cau tinh ("Chon tuyen duong de hien thi so
 * do lo trinh") ngay ca khi tuyen da ve xong. Nay no vua la chu giai mau vua
 * la danh sach chang — nho vay mau khong bao gio dung mot minh.
 */
function renderRouteWaypointLegend(markerModel) {
  const bar = document.getElementById('route-waypoint-bar');
  if (!bar) return;
  if (!markerModel || !markerModel.length) {
    bar.className = '';
    bar.innerHTML = 'Chọn tuyến đường để hiển thị sơ đồ lộ trình';
    return;
  }
  bar.className = 'rmap-legend';
  bar.innerHTML = markerModel.map((w, i) => `
    ${i ? '<i class="fa-solid fa-arrow-right rmap-legend-arrow" aria-hidden="true"></i>' : ''}
    <span class="rmap-legend-item" title="${escapeHtml(w.roleLabel)}">
      <span class="rmap-legend-dot" style="--rmap-pin:${escapeHtml(w.color)};">${
        w.glyph ? escapeHtml(w.glyph) : `<i class="fa-solid ${escapeHtml(w.icon)}" aria-hidden="true"></i>`
      }</span>
      <b>${escapeHtml(w.label)}</b>
      <small>${escapeHtml(w.roleLabel)}</small>
    </span>`).join('');
}

window.initLeafletRouteMap = async function (waypointsData, routeCode, routeName, duongBoTuMayChu) {
  const container = document.getElementById('route-leaflet-map');
  if (!container) return;

  if (!leafletRouteMap && typeof L !== 'undefined') {
    leafletRouteMap = L.map('route-leaflet-map', { zoomControl: true }).setView([10.88, 106.72], 10);

    // MỘT nguồn ảnh nền là một điểm vỡ đơn: đo được trên mạng của dự án thì
    // `tile.openstreetmap.org` không tới được, và ô bản đồ xám trơn dù toạ độ
    // và đường kẻ tuyến đều đúng. `LopNenBanDo` thử lần lượt nhiều nguồn và
    // nhớ nguồn nào chạy được.
    lopNenDuong = (window.LopNenBanDo
      ? window.LopNenBanDo.tao(leafletRouteMap).lop
      : L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          maxZoom: 19, attribution: '&copy; OpenStreetMap'
        }).addTo(leafletRouteMap));

    routeMapLayersGroup = L.layerGroup().addTo(leafletRouteMap);
  } else if (leafletRouteMap) {
    setTimeout(() => { leafletRouteMap.invalidateSize(); }, 200);
  }

  // CLEAR ALL OLD MARKERS & POLYLINES
  window.clearLeafletRouteMap();

  // If no waypoints provided, just show the empty base map - do NOT load hardcoded data
  if (!waypointsData || waypointsData.length === 0) return;

  // Ghim mau theo vai tro: diem di do, diem trung chuyen xanh duong co so thu
  // tu, diem den xanh la. Bay ghim giong nhau het nen khong biet dau la diem
  // bat dau — do la van de cu.
  const markerModel = window.RouteMapUtils?.buildWaypointMarkerModel
    ? window.RouteMapUtils.buildWaypointMarkerModel(waypointsData)
    : waypointsData.map((w, i) => ({ ...w, order: i + 1, color: '#1d4ed8', icon: 'fa-circle-dot', glyph: '', roleLabel: '' }));

  markerModel.forEach((w) => {
    const inner = w.glyph
      ? `<b>${escapeHtml(w.glyph)}</b>`
      : `<i class="fa-solid ${escapeHtml(w.icon)}" aria-hidden="true"></i>`;
    const marker = L.marker([w.lat, w.lng], {
      // KHONG escape o day: Leaflet dat option title qua thuoc tinh title cua
      // the, khong qua innerHTML. Escape them se khien nguoi dung nhin thay
      // "&amp;" thay vi "&" trong ten dia diem.
      title: `${w.order}. ${w.roleLabel}: ${w.label}`,
      icon: L.divIcon({
        className: 'rmap-pin-wrap',
        html: `<span class="rmap-pin rmap-pin--${escapeHtml(w.role)}" style="--rmap-pin:${escapeHtml(w.color)};">${inner}</span>`,
        iconSize: [30, 40],
        iconAnchor: [15, 38],
        popupAnchor: [0, -34]
      })
    });
    marker.bindPopup(`<b>${escapeHtml(w.label)}</b><br><span style="color:${escapeHtml(w.color)}; font-weight:700;">${escapeHtml(w.order + '. ' + w.roleLabel)}</span>`);
    routeMapLayersGroup.addLayer(marker);
  });

  renderRouteWaypointLegend(markerModel);

  const waypointsParam = waypointsData.map(w => `${w.lng},${w.lat}`).join(';');

  /* HÌNH TUYẾN: ưu tiên đường BỘ THẬT, và nếu chỉ có đường nối điểm thì NÓI RA.
   *
   * Chủ dự án đã chỉ ra đúng chỗ này: *"tui muốn cái tuyến đường đi là sự thật
   * nên vẽ cái đường thẳng mang đi demo kỳ lắm"*. Và đó là một lỗi thật chứ
   * không phải chuyện thẩm mỹ — một đường thẳng từ Long An sang Cái Mép đi
   * xuyên qua sông và qua khu dân cư, nói sai cả hai điều quan trọng nhất của
   * một tuyến: xe đi đường nào, và tuyến dài bao nhiêu.
   *
   * Ba đường, theo thứ tự:
   *   1. Hình do MÁY CHỦ trả về — đã lưu trong cơ sở dữ liệu, nên chạy được cả
   *      khi máy không có mạng, và không phải lấy lại mỗi lần mở màn.
   *   2. Lấy trực tiếp từ máy dẫn đường, cho những tuyến máy chủ chưa lưu.
   *   3. Đường NỐI ĐIỂM — vẽ nét đứt và ghi rõ "chưa có đường bộ thật". Một
   *      đường thẳng vẽ liền nét đọc ra như tuyến đi thật, và đó là điều không
   *      được để xảy ra nữa.
   */
  const veHinh = (diem, laDuongBo) => {
    const polyline = L.polyline(diem, laDuongBo
      ? { color: '#2563eb', weight: 6, opacity: 0.85 }
      : { color: '#2563eb', weight: 4, opacity: 0.75, dashArray: '10 8' });
    routeMapLayersGroup.addLayer(polyline);
    leafletRouteMap.fitBounds(polyline.getBounds(), { padding: [40, 40] });
    if (!laDuongBo) {
      polyline.bindTooltip('Đường nối điểm — chưa có hình đường bộ thật',
        { sticky: true, className: 'route-map-canhbao' });
    }
    const oNote = document.getElementById('route-map-note');
    if (oNote) {
      oNote.textContent = laDuongBo ? '' :
        'Nét đứt: đây là đường nối các điểm, chưa phải hình đường bộ thật của tuyến.';
      oNote.hidden = !!laDuongBo;
    }
  };

  if (Array.isArray(duongBoTuMayChu) && duongBoTuMayChu.length >= 2) {
    veHinh(duongBoTuMayChu, true);
    return;
  }
  try {
    const osrmUrl = `https://router.project-osrm.org/route/v1/driving/${waypointsParam}?overview=full&geometries=geojson`;
    const res = await fetch(osrmUrl);
    const data = await res.json();
    if (data && data.routes && data.routes.length > 0) {
      veHinh(data.routes[0].geometry.coordinates.map(c => [c[1], c[0]]), true);
    } else {
      veHinh(waypointsData.map(w => [w.lat, w.lng]), false);
    }
  } catch (e) {
    veHinh(waypointsData.map(w => [w.lat, w.lng]), false);
  }
};

const MASTER_DATA_GUIDANCE = {
  'md-tab-routes': {
    title: { vi: 'Tuyến đường cố định', en: 'Fixed Routes', la: 'ເສັ້ນທາງຄົງທີ່' },
    summary: { vi: 'Cấu hình chặng A → B → C, tổng km kế hoạch và bản đồ tuyến. Dữ liệu này đi thẳng vào Báo giá, SO, DO, Dispatch và ETA.', en: 'Configure segment A → B → C, plan km and route map. Flows into Quote, SO, DO, Dispatch and ETA.', la: 'ກຳນົດຊ່ວງ A → B → C, ໄລຍະທາງແຜນ ແລະ ແຜນທີ່ເສັ້ນທາງ. ໃຊ້ໃນໃບສະເໜີລາຄາ, SO, DO, Dispatch ແລະ ETA.' },
    dataLabel: { vi: 'tuyến đã lưu', en: 'saved routes', la: 'ເສັ້ນທາງທີ່ບັນທຶກ' },
    next: {
      vi: ['Tạo tuyến mới', 'Thêm chặng và kiểm tra tổng km realtime', 'Sau đó chọn tuyến ở Báo giá/SO/DO'],
      en: ['Create new route', 'Add segments and check total km realtime', 'Select route in Quote/SO/DO'],
      la: ['ສ້າງເສັ້ນທາງໃໝ່', 'ເພີ່ມຊ່ວງ ແລະ ກວດສອບໄລຍະທາງລວມ realtime', 'ເລືອກເສັ້ນທາງໃນໃບສະເໜີລາຄາ/SO/DO']
    },
    primaryAction: 'route'
  },
  'md-tab-formulas': {
    title: { vi: 'Công thức giá thành & xăng dầu', en: 'Cost Formula & Fuel', la: 'ສູດຄິດໄລ່ຕົ້ນທຶນ & ນ້ຳມັນ' },
    summary: { vi: 'Thiết lập khoản mục chi phí theo loại xe để tính giá kế hoạch và so sánh với chi phí thực tế.', en: 'Setup cost breakdown by vehicle type to calculate plan and actual cost.', la: 'ກຳນົດໂຄງສ້າງຕົ້ນທຶນຕາມປະເພດລົດເພື່ອຄິດໄລ່ລາຄາແຜນ ແລະ ສົມທຽບຕົ້ນທຶນຕົວຈິງ.' },
    dataLabel: { vi: 'loại xe/công thức', en: 'vehicle types/formulas', la: 'ປະເພດລົດ / ສູດຄິດໄລ່' },
    next: {
      vi: ['Chọn loại xe ở cột trái', 'Cấu hình định mức nhiên liệu, lương tài xế, phí cầu đường', 'Dùng để tính báo giá và actual cost'],
      en: ['Select vehicle type on left', 'Configure fuel norm, driver salary, toll fees', 'Used for Quote and actual cost'],
      la: ['ເລືອກປະເພດລົດຢູ່ຖັນຊ້າຍ', 'ຕັ້ງຄ່າມາດຕະຖານນ້ຳມັນ, ເງິນອຸດໜູນຄົນຂັບ, ຄ່າຜ່ານທາງ', 'ໃຊ້ສຳລັບໃບສະເໜີລາຄາ ແລະ ຕົ້ນທຶນຕົວຈິງ']
    },
    primaryAction: 'formula'
  },
  'md-tab-veh-types': {
    title: { vi: 'Loại phương tiện', en: 'Vehicle Types', la: 'ປະເພດພາຫະນະ' },
    summary: { vi: 'Chuẩn hóa tải trọng, thể tích và nhóm xe để hệ thống kiểm tra năng lực trước dispatch.', en: 'Standardize payload, volume and vehicle groups for capacity check before dispatch.', la: 'ສ້າງມາດຕະຖານນ້ຳໜັກບັນທຸກ, ບໍລິມາດ ແລະ ກຸ່ມລົດ ເພື່ອໃຫ້ລະບົບກວດສອບກ່ອນປ່ອຍລົດ.' },
    dataLabel: { vi: 'loại phương tiện', en: 'vehicle types', la: 'ປະເພດລົດ' },
    next: {
      vi: ['Tạo loại xe trước', 'Gắn loại xe vào từng phương tiện', 'Kiểm tra tải trọng/thể tích khi lập DO'],
      en: ['Create vehicle type first', 'Assign vehicle type to vehicles', 'Check payload/volume during DO creation'],
      la: ['ສ້າງປະເພດລົດກ່ອນ', 'ກຳນົດປະເພດລົດໃຫ້ກັບລົດແຕ່ລະຄັນ', 'ກວດສອບນ້ຳໜັກ/ບໍລິມາດເມື່ອສ້າງ DO']
    },
    primaryAction: 'vehicle_type'
  },
  'md-tab-vehicles': {
    title: { vi: 'Xe, tài xế và sắp ca', en: 'Vehicles, Drivers & Shifts', la: 'ລົດ, ຄົນຂັບ ແລະ ຈັດກະ' },
    summary: { vi: 'Quản lý hồ sơ xe/tài xế, hình ảnh, đăng kiểm, bảo hiểm và trạng thái sẵn sàng để phân bổ.', en: 'Manage vehicle/driver profiles, inspection, insurance and dispatch readiness.', la: 'ຄຸ້ມຄອງຂໍ້ມູນລົດ/ຄົນຂັບ, ກວດກາເຕັກນິກ, ປະກັນໄພ ແລະ ຄວາມພ້ອມປ່ອຍລົດ.' },
    dataLabel: { vi: 'xe/tài xế', en: 'vehicles/drivers', la: 'ລົດ/ຄົນຂັບ' },
    next: {
      vi: ['Thêm xe hoặc tài xế', 'Upload ảnh hồ sơ nếu cần demo', 'Chỉ dispatch khi xe/tài xế còn hiệu lực'],
      en: ['Add vehicle or driver', 'Upload profile image for demo', 'Only dispatch when valid'],
      la: ['ເພີ່ມລົດ ຫຼື ຄົນຂັບ', 'ອັບໂຫຼດຮູບຖ່າຍເອກະສານ', 'ປ່ອຍລົດເມື່ອລົດ/ຄົນຂັບພ້ອມໃຊ້ງານ']
    },
    primaryAction: 'vehicle'
  },
  'md-tab-currencies': {
    title: { vi: 'Tiền tệ và tỷ giá', en: 'Currencies & Rates', la: 'ສະກຸນເງິນ ແລະ ອັດຕາແລກປ່ຽນ' },
    summary: { vi: 'Thiết lập tiền tệ, tỷ giá và quy đổi phục vụ báo cáo tài chính/AP/settlement.', en: 'Configure currencies and exchange rates for AP and settlement.', la: 'ຕັ້ງຄ່າສະກຸນເງິນ ແລະ ອັດຕາແລກປ່ຽນ ສຳລັບລາຍງານການເງິນ/AP/settlement.' },
    dataLabel: { vi: 'tiền tệ', en: 'currencies', la: 'ສະກຸນເງິນ' },
    next: {
      vi: ['Kiểm tra VND/USD/LAK', 'Cập nhật tỷ giá theo ngày', 'Dùng cho AP và thanh toán đa tiền tệ'],
      en: ['Check VND/USD/LAK', 'Update daily exchange rate', 'Use for AP and multi-currency settlement'],
      la: ['ກວດສອບ VND/USD/LAK', 'ອັບເດດອັດຕາແລກປ່ຽນຕາມວັນ', 'ໃຊ້ສຳລັບ AP ແລະ ຊຳລະຫຼາຍສະກຸນເງິນ']
    },
    primaryAction: 'currency'
  },
  'md-tab-customers': {
    title: { vi: 'Khách hàng', en: 'Customers', la: 'ລູກຄ້າ' },
    summary: { vi: 'Danh mục khách hàng/đối tác để tạo báo giá, đơn hàng vận chuyển và địa điểm giao nhận.', en: 'Customer directory for quotes, sales orders and delivery locations.', la: 'ລາຍຊື່ລູກຄ້າ/ຄູ່ຮ່ວມງານ ສຳລັບສ້າງໃບສະເໜີລາຄາ, SO ແລະ ສະຖານທີ່ຮັບ-ສົ່ງ.' },
    dataLabel: { vi: 'khách hàng', en: 'customers', la: 'ລູກຄ້າ' },
    next: {
      vi: ['Thêm khách hàng', 'Bổ sung người liên hệ và địa chỉ kho', 'Chọn khách hàng ở bước Báo giá'],
      en: ['Add customer', 'Add contacts and warehouse addresses', 'Select customer in Quote step'],
      la: ['ເພີ່ມລູກຄ້າ', 'ເພີ່ມຜູ້ຕິດຕໍ່ ແລະ ທີ່ຢູ່ສາງ', 'ເລືອກລູກຄ້າໃນຂັ້ນຕອນໃບສະເໜີລາຄາ']
    },
    primaryAction: 'customer'
  },
  'md-tab-tax-codes': {
    title: { vi: 'Thuế', en: 'Tax Codes', la: 'ລະຫັດອາກອນ' },
    summary: { vi: 'Mã thuế và hiệu lực dùng cho actual cost, AP invoice và hạch toán.', en: 'Tax codes and validity for actual cost, AP and posting.', la: 'ລະຫັດອາກອນ ແລະ ຜົນບັງຄັບໃຊ້ ສຳລັບຕົ້ນທຶນຕົວຈິງ, ໃບແຈ້ງໜີ້ AP ແລະ ລົງບັນຊີ.' },
    dataLabel: { vi: 'mã thuế', en: 'tax codes', la: 'ລະຫັດອາກອນ' },
    next: {
      vi: ['Thêm mã thuế VAT/miễn thuế', 'Kiểm tra ngày hiệu lực', 'Dùng khi tạo dòng chi phí/AP'],
      en: ['Add VAT/exempt code', 'Check effective date', 'Use when creating cost/AP lines'],
      la: ['ເພີ່ມລະຫັດອາກອນ VAT/ຍົກເວັ້ນ', 'ກວດສອບວັນທີ່ມີຜົນ', 'ໃຊ້ເມື່ອສ້າງລາຍການຕົ້ນທຶນ/AP']
    },
    primaryAction: 'tax_code'
  },
  'md-tab-accounting-periods': {
    title: { vi: 'Kỳ kế toán', en: 'Accounting Periods', la: 'ງວດບັນຊີ' },
    summary: { vi: 'Mở/khóa kỳ kế toán để kiểm soát ngày post AP, payment và settlement.', en: 'Open/lock accounting periods to control AP, payment and settlement.', la: 'ເປີດ/ລັອກ ງວດບັນຊີ ເພື່ອຄວບຄຸມການລົງບັນຊີ AP, ຊຳລະເງິນ ແລະ ສະສາງ.' },
    dataLabel: { vi: 'kỳ kế toán', en: 'accounting periods', la: 'ງວດບັນຊີ' },
    next: {
      vi: ['Tạo kỳ tháng hiện tại', 'Mở kỳ trước demo', 'Khóa kỳ cũ khi cần kiểm soát'],
      en: ['Create current month period', 'Open period before demo', 'Lock old periods for control'],
      la: ['ສ້າງງວດເດືອນປັດຈຸບັນ', 'ເປີດງວດກ່ອນ demo', 'ລັອກງວດເກົ່າເມື່ອຕ້ອງການຄວບຄຸມ']
    },
    primaryAction: 'accounting_period'
  },
  'md-tab-carriers': {
    title: { vi: 'Carrier / Vendor', en: 'Carriers / Vendors', la: 'ຜູ້ໃຫ້ບໍລິການຂົນສົ່ງ / Carrier' },
    summary: { vi: 'Danh sách nhà vận chuyển thuê ngoài và đội xe nội bộ. Nếu công ty tự vận chuyển thì cấu hình carrier nội bộ để đi thẳng Dispatch.', en: 'Outsourced carriers and internal fleet. Configure internal carrier for direct Dispatch.', la: 'ລາຍຊື່ຜູ້ຮັບເໝົາຂົນສົ່ງພາຍນອກ ແລະ ທີມລົດພາຍໃນ. ຖ້າຂົນສົ່ງເອງໃຫ້ກຳນົດ carrier ພາຍໃນເພື່ອໄປ Dispatch ໂດຍກົງ.' },
    dataLabel: { vi: 'carrier/vendor', en: 'carriers/vendors', la: 'ຜູ້ໃຫ້ບໍລິການ' },
    next: {
      vi: ['Tạo carrier nội bộ cho đội xe công ty', 'Tạo carrier thuê ngoài nếu cần tender', 'Gắn carrier vào cost/AP'],
      en: ['Create internal carrier for fleet', 'Create outsourced carrier if tendering', 'Link carrier to cost/AP'],
      la: ['ສ້າງ carrier ພາຍໃນສຳລັບທີມລົດບໍລິສັດ', 'ສ້າງ carrier ພາຍນອກຖ້າຕ້ອງການ tender', 'ເຊື່ອມໂຍງ carrier ກັບຕົ້ນທຶນ/AP']
    },
    primaryAction: 'carrier'
  },
  'md-tab-account-mappings': {
    title: { vi: 'Mapping tài khoản', en: 'Account Mappings', la: 'ຜັງບັນຊີ Mapping' },
    summary: { vi: 'Mapping GL cho chi phí vận tải, AP, thanh toán và chênh lệch tỷ giá.', en: 'GL mapping for transport cost, AP, payment and FX diff.', la: 'ກຳນົດບັນຊີ GL ສຳລັບຕົ້ນທຶນຂົນສົ່ງ, AP, ຊຳລະເງິນ ແລະ ຜົນຕ່າງອັດຕາແລກປ່ຽນ.' },
    dataLabel: { vi: 'mapping tài khoản', en: 'account mappings', la: 'ຜັງບັນຊີ' },
    next: {
      vi: ['Tạo mapping chi phí vận tải', 'Tạo mapping AP/payment', 'Kiểm tra trước khi post journal'],
      en: ['Create freight cost mapping', 'Create AP/payment mapping', 'Check before journal posting'],
      la: ['ສ້າງ mapping ຕົ້ນທຶນຂົນສົ່ງ', 'ສ້າງ mapping AP/ຊຳລະເງິນ', 'ກວດສອບກ່ອນລົງບັນຊີລາຍວັນ']
    },
    primaryAction: 'account_mapping'
  }
};

function countMasterDataRows(tabId) {
  const count = value => Array.isArray(value) ? value.length : 0;
  if (tabId === 'md-tab-routes') return count(eplRoutes) || count(appState.routes);
  if (tabId === 'md-tab-formulas') return count(vehTypes) || count(appState.vehicle_types);
  if (tabId === 'md-tab-veh-types') return count(vehTypes) || count(appState.vehicle_types);
  if (tabId === 'md-tab-vehicles') return count(fioriVehicles) + count(fioriDrivers);
  if (tabId === 'md-tab-currencies') return count(appState.currencies) || count(appState.currency_rates);
  if (tabId === 'md-tab-customers') return count(eplCustomers) || count(appState.customers);
  if (tabId === 'md-tab-tax-codes') return count(appState.tax_codes);
  if (tabId === 'md-tab-accounting-periods') return count(appState.accounting_periods);
  if (tabId === 'md-tab-carriers') return count(appState.carriers);
  if (tabId === 'md-tab-account-mappings') return count(appState.account_mappings);
  return 0;
}

window.openMasterDataPrimaryAction = function (tabId) {
  const guidance = MASTER_DATA_GUIDANCE[tabId] || MASTER_DATA_GUIDANCE['md-tab-routes'];
  if (['tax_code', 'accounting_period', 'carrier', 'account_mapping'].includes(guidance.primaryAction)) {
    if (typeof openFinanceMasterConfig === 'function') return openFinanceMasterConfig(guidance.primaryAction);
  }
  if (guidance.primaryAction === 'route' && typeof createNewRouteForm === 'function') return createNewRouteForm();
  if (guidance.primaryAction === 'vehicle' && typeof openFioriVehicleForm === 'function') return openFioriVehicleForm();
  if (guidance.primaryAction === 'customer' && typeof openCustomerModal === 'function') return openCustomerModal();
  if (guidance.primaryAction === 'vehicle_type' && typeof addNewVehicleType === 'function') return addNewVehicleType();
  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
  const gTitle = (guidance.title && typeof guidance.title === 'object') ? (guidance.title[lang] || guidance.title.vi) : guidance.title;
  showToast(lang === 'la' ? `ກຳລັງເປີດເຂດຕັ້ງຄ່າ ${gTitle}.` : `Đang mở vùng cấu hình ${gTitle}.`);
  return null;
};

window.updateMasterDataGuidance = function (tabId = 'md-tab-routes') {
  const guidance = MASTER_DATA_GUIDANCE[tabId] || MASTER_DATA_GUIDANCE['md-tab-routes'];
  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
  const titleEl = document.getElementById('master-data-selected-title');
  const summaryEl = document.getElementById('master-data-selected-summary');
  const healthEl = document.getElementById('master-data-health-list');
  const actionsEl = document.getElementById('master-data-next-actions');

  const gTitle = (guidance.title && typeof guidance.title === 'object') ? (guidance.title[lang] || guidance.title.vi) : guidance.title;
  const gSummary = (guidance.summary && typeof guidance.summary === 'object') ? (guidance.summary[lang] || guidance.summary.vi) : guidance.summary;
  const gDataLabel = (guidance.dataLabel && typeof guidance.dataLabel === 'object') ? (guidance.dataLabel[lang] || guidance.dataLabel.vi) : guidance.dataLabel;
  const nextList = (guidance.next && typeof guidance.next === 'object' && !Array.isArray(guidance.next)) ? (guidance.next[lang] || guidance.next.vi || []) : (guidance.next || []);

  if (titleEl) titleEl.textContent = gTitle;
  if (summaryEl) summaryEl.textContent = gSummary;
  const rows = countMasterDataRows(tabId);

  const dataHeader = lang === 'la' ? 'ຂໍ້ມູນທີ່ມີຢູ່' : lang === 'en' ? 'AVAILABLE DATA' : 'DỮ LIỆU HIỆN CÓ';
  const readyMsg = lang === 'la' ? 'ສາມາດໃຊ້ສຳລັບການດຳເນີນງານ.' : lang === 'en' ? 'Ready for operation workflow.' : 'Có thể dùng cho luồng vận hành.';
  const missMsg = lang === 'la' ? 'ຂາດຂໍ້ມູນ — ຕ້ອງຕັ້ງຄ່າກ່ອນດຳເນີນງານ.' : lang === 'en' ? 'Missing data — configure before workflow.' : 'Thiếu dữ liệu — cần cấu hình trước khi đi luồng A-Z.';
  const btnAdd = lang === 'la' ? '<i class="fa-solid fa-plus"></i> ເພີ່ມ / ຕັ້ງຄ່າທັນທີ' : lang === 'en' ? '<i class="fa-solid fa-plus"></i> Add / Configure Now' : '<i class="fa-solid fa-plus"></i> Thêm / cấu hình ngay';
  const btnReload = lang === 'la' ? '<i class="fa-solid fa-rotate"></i> ໂຫຼດຂໍ້ມູນ CSDL ຄືນໃໝ່' : lang === 'en' ? '<i class="fa-solid fa-rotate"></i> Reload DB Data' : '<i class="fa-solid fa-rotate"></i> Tải lại dữ liệu CSDL';

  if (healthEl) {
    // Mot VIEN gon tren dai, khong con hop ba dong cao 90px. Con so va mau
    // la phan mang tin; `dataHeader` ("DU LIEU HIEN CO") chi la nhan mo ta
    // chinh no, nen bo di — cai viên nam ngay canh tieu de danh muc roi.
    healthEl.className = "md-guide-pill " + (rows ? "md-guide-pill-ok" : "md-guide-pill-thieu");
    healthEl.title = rows ? readyMsg : missMsg;
    healthEl.innerHTML = `<i class="fa-solid fa-${rows ? "circle-check" : "circle-exclamation"}"></i><b>${rows}</b> ${gDataLabel}`;
  }
  // Dau do tren nut gap: chi bat khi danh muc nay CHUA co dong nao. Mot dau
  // do thuong truc thi chang con nghia gi.
  const oDau = document.getElementById("master-data-guide-dot");
  if (oDau) oDau.hidden = rows > 0;
  // Hai nut hay bam nhat len DAI — thay vi nam trong khoi gap, vi de trong
  // do thi muon bam phai mo khoi ra truoc, tuc them mot lan bam cho mot viec
  // lam thuong xuyen.
  const oThem = document.getElementById("master-data-guide-add");
  if (oThem) {
    oThem.innerHTML = btnAdd;
    oThem.onclick = () => openMasterDataPrimaryAction(tabId);
    // Tab "Xe, tài xế và sắp ca" đã có nút "Thêm tài xế / phụ xe" ngay trên
    // thanh công cụ của bảng xếp ca; nút gộp "Thêm / cấu hình ngay" ở dải
    // trên là nút thứ hai cho cùng một việc — chủ dự án yêu cầu bỏ.
    oThem.hidden = tabId === 'md-tab-vehicles';
  }
  const oNapLai = document.getElementById("master-data-guide-reload");
  if (oNapLai) {
    oNapLai.innerHTML = btnReload;
    oNapLai.onclick = () => {
      loadAllData();
      setTimeout(() => updateMasterDataGuidance(tabId), 250);
    };
  }
  if (actionsEl) {
    actionsEl.innerHTML = nextList.map(text => `
      <div style="border:1px solid #dbeafe; background:#eff6ff; color:#1e3a8a;
                  border-radius:10px; padding:6px 10px; font-size:.77rem; font-weight:600;">
        <i class="fa-solid fa-circle-check"></i> ${text}
      </div>`).join("");
  }
};

/* ==========================================================================
   Mở / đóng khối gợi ý cấu hình.

   Phần dài — đoạn mô tả và ba dòng gợi ý bước tiếp — chỉ cần lúc đầu, nên
   nó gấp lại. Nhưng nhớ lựa chọn của người dùng: ai đã đóng thì lần sau vào
   không phải đóng lại, ai cần thì mở một lần là xong.
   ========================================================================== */

const KHOA_GOI_Y_CAU_HINH = "epl.goi-y-cau-hinh.mo";

function docTrangThaiGoiY() {
  // `localStorage` có thể ném lỗi (cửa sổ riêng tư, chặn dữ liệu trang), và
  // một gợi ý không mở được thì không đáng làm sập cả màn.
  try {
    return window.localStorage.getItem(KHOA_GOI_Y_CAU_HINH) === "1";
  } catch (e) {
    return false;
  }
}

function veGoiYCauHinh(mo) {
  const khoi = document.getElementById("master-data-guidance-panel");
  const nut = document.getElementById("master-data-guide-toggle");
  if (khoi) khoi.hidden = !mo;
  if (nut) {
    nut.setAttribute("aria-expanded", mo ? "true" : "false");
    nut.title = mo ? "Ẩn gợi ý cấu hình" : "Xem gợi ý cấu hình";
  }
}

window.moGoiYCauHinh = function () {
  const mo = !docTrangThaiGoiY();
  try {
    window.localStorage.setItem(KHOA_GOI_Y_CAU_HINH, mo ? "1" : "0");
  } catch (e) {
    /* không lưu được thì vẫn mở/đóng được trong phiên này */
  }
  veGoiYCauHinh(mo);
};

window.apDungTrangThaiGoiY = function () {
  veGoiYCauHinh(docTrangThaiGoiY());
};


window.renderMasterDataCommandCenter = function () {
  const activeButton = document.querySelector('.md-tab-btn.active');
  const onclickText = activeButton ? (activeButton.getAttribute('onclick') || '') : '';
  const match = onclickText.match(/switchMasterDataTab\('([^']+)'/);
  window.updateMasterDataGuidance(match ? match[1] : 'md-tab-routes');
};

window.switchMasterDataTab = function (tabId, btn) {
  if (!btn) {
    btn = Array.from(document.querySelectorAll('.md-tab-btn')).find(b => (b.getAttribute('onclick') || '').includes(`'${tabId}'`));
  }
  document.querySelectorAll('.md-tab-content').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.md-tab-btn').forEach(b => {
    b.classList.remove('active');
    b.style.background = 'transparent';
    b.style.color = '#64748b';
    b.style.fontWeight = '600';
  });

  const target = document.getElementById(tabId);
  if (target) target.style.display = 'block';
  if (btn) {
    btn.classList.add('active');
    btn.style.background = '#eff6ff';
    btn.style.color = '#2563eb';
    btn.style.fontWeight = '700';
  }

  if (tabId === 'md-tab-routes') {
    loadRoutePlanningDropdown(); // Load from API, show empty form if no routes
  } else if (tabId === 'md-tab-formulas') {
    // Truoc day tab nay KHONG co nhanh nao: mo len khong tai gi ca, chi hien
    // lai vehTypes con sot tu luc tai trang. Neu luc do chua tai xong thi panel
    // ket o "0 mau" mai mai, va nguoi dung khong the cau hinh gia thanh cho bat
    // ky loai xe nao — du Master Data van co du.
    if (typeof loadVehTypesForFormulas === 'function') loadVehTypesForFormulas();
  } else if (tabId === 'md-tab-veh-types') {
    if (typeof loadVehTypes === 'function') loadVehTypes();
    if (typeof loadFioriVehicles === 'function') loadFioriVehicles();
  } else if (tabId === 'md-tab-vehicles') {
    if (typeof loadDriverShiftPlanner === 'function') loadDriverShiftPlanner();
    else if (typeof loadFioriDrivers === 'function') loadFioriDrivers();
  } else if (tabId === 'md-tab-customers') {
    if (typeof loadCustomerList === 'function') loadCustomerList();
  } else if (tabId === 'md-tab-currencies') {
    if (typeof recalculateCurrencyPreview === 'function') recalculateCurrencyPreview();
    if (typeof loadCurrencyReferenceStatus === 'function') loadCurrencyReferenceStatus();
    if (typeof loadCurrencyRateHistory === 'function') loadCurrencyRateHistory();
  } else if (['md-tab-tax-codes', 'md-tab-accounting-periods', 'md-tab-carriers', 'md-tab-account-mappings'].includes(tabId)) {
    if (typeof renderFinanceMasterDataTabs === 'function') renderFinanceMasterDataTabs();
  }
  if (typeof updateMasterDataGuidance === 'function') updateMasterDataGuidance(tabId);
};

window.switchVehicleCatalogFolder = function (folder, btn) {
  const selected = folder === 'fleet' ? 'fleet' : 'types';
  const panels = {
    types: document.getElementById('md-vehicle-folder-types'),
    fleet: document.getElementById('md-vehicle-folder-fleet')
  };
  Object.entries(panels).forEach(([key, panel]) => {
    if (panel) panel.style.display = key === selected ? 'block' : 'none';
  });

  document.querySelectorAll('.vehicle-folder-tab').forEach(tab => {
    const isActive = tab === btn || (tab.getAttribute('onclick') || '').includes(`'${selected}'`);
    tab.classList.toggle('active', isActive);
  });

  if (selected === 'types' && typeof loadVehTypes === 'function') loadVehTypes();
  if (selected === 'fleet' && typeof loadFioriVehicles === 'function') loadFioriVehicles();
};

window.switchOpsPlanningFolder = function (folder, btn) {
  if (folder === 'trip') {
    switchView('delivery-shipment');
    return;
  }
  const selected = 'do';
  const panels = {
    do: document.getElementById('ops-planning-folder-do')
  };
  Object.entries(panels).forEach(([key, panel]) => {
    if (panel) panel.style.display = key === selected ? 'block' : 'none';
  });
  document.querySelectorAll('.ops-planning-folder-tab').forEach(tab => {
    const isActive = tab === btn || (tab.getAttribute('onclick') || '').includes(`'${selected}'`);
    tab.classList.toggle('active', isActive);
    tab.style.borderColor = isActive ? '#2563eb' : '#e2e8f0';
    tab.style.background = isActive ? '#eff6ff' : '#ffffff';
    tab.style.color = isActive ? '#2563eb' : '#334155';
    tab.style.boxShadow = isActive ? '0 4px 12px rgba(10,110,209,0.12)' : 'none';
  });
  if (selected === 'do' && typeof loadDeliveryOrders === 'function') loadDeliveryOrders();
};

// Load route dropdown from API and reset form to empty state
window.loadRoutePlanningDropdown = async function () {
  const select = document.getElementById('md-saved-routes-select');
  if (!select) return;
  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
  const ph = lang === 'la' ? '-- ເລືອກເສັ້ນທາງທີ່ບັນທຶກໄວ້ --' : lang === 'en' ? '-- Select Saved Route --' : '-- Chọn Tuyến Đường đã lưu --';
  select.innerHTML = `<option value="">${ph}</option>`;

  try {
    const routes = await fetchAllPaginated(`${API_BASE}/api/routes?paginated=true`);
    if (Array.isArray(routes)) {
      eplRoutes = routes;

      routes.forEach(r => {
        const opt = document.createElement('option');
        opt.value = r.id;
        // KHÔNG escape ở đây: giá trị đi vào innerText, vốn đã coi nội dung là văn
        // bản thuần. Escape thêm sẽ khiến người dùng nhìn thấy "&amp;" thay vì "&".
        opt.innerText = `${r.id}: ${r.name} (${r.distance_km || 0} km)`;
        select.appendChild(opt);
      });

      if (routes.length === 0) {
        // No routes yet — show empty form ready for input
        resetRoutePlanningForm();
      }
    }
  } catch (e) {
    baoNapThatBai('danh sách tuyến đường cho ô chọn', e);
  }

  // Init map with empty state (no hardcoded default)
  if (typeof window.initLeafletRouteMap === 'function') {
    window.initLeafletRouteMap(null, null, null);
  }
};

async function geocodeRouteLocation(location) {
  const query = `${String(location || '').trim()}, Vietnam`;
  if (!String(location || '').trim()) return null;

  try {
    const url = `https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=vn&q=${encodeURIComponent(query)}`;
    const res = await fetch(url);
    if (!res.ok) return null;

    const data = await res.json();
    if (!Array.isArray(data) || data.length === 0) return null;

    return {
      lat: Number(data[0].lat),
      lng: Number(data[0].lon),
      label: String(location).trim()
    };
  } catch (error) {
    console.error('Failed to geocode route location', location, error);
    return null;
  }
}

function resetRoutePlanningForm() {
  const codeEl = document.getElementById('md-route-code');
  const nameEl = document.getElementById('md-route-name');
  const tbody = document.getElementById('route-segments-tbody');
  const distEl = document.getElementById('route-total-distance');
  if (codeEl) codeEl.value = '';
  if (nameEl) nameEl.value = '';
  if (tbody) tbody.innerHTML = '';
  if (distEl) {
    distEl.dataset.km = '0';
    distEl.innerText = '0 km';
  }
}

window.calculateRealDistance = async function (locationA, locationB) {
  try {
    const resA = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(locationA + ', Vietnam')}`);
    const resB = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(locationB + ', Vietnam')}`);
    const dataA = await resA.json();
    const dataB = await resB.json();

    if (dataA && dataA.length > 0 && dataB && dataB.length > 0) {
      const lat1 = parseFloat(dataA[0].lat);
      const lon1 = parseFloat(dataA[0].lon);
      const lat2 = parseFloat(dataB[0].lat);
      const lon2 = parseFloat(dataB[0].lon);

      const osrmRes = await fetch(`https://router.project-osrm.org/route/v1/driving/${lon1},${lat1};${lon2},${lat2}?overview=full&geometries=geojson`);
      const osrmData = await osrmRes.json();
      if (osrmData && osrmData.routes && osrmData.routes.length > 0) {
        const distKm = Math.round(osrmData.routes[0].distance / 1000);
        const routePath = osrmData.routes[0].geometry.coordinates.map(c => [c[1], c[0]]);
        return { distKm, lat1, lon1, lat2, lon2, routePath };
      }
    }
  } catch (err) {
    console.warn("Geocoding API fallback", err);
  }
  return null;
};

window.addRouteSegment = async function () {
  const from = document.getElementById('seg-from')?.value || '';
  const to = document.getElementById('seg-to')?.value || '';
  let distInput = document.getElementById('seg-dist')?.value;
  let dist = parseInt(distInput || '0');

  if (!from || !to) {
    showToast('Vui lòng nhập đầy đủ Điểm Đi và Điểm Đến!');
    return;
  }

  if (!window.RouteSegmentPolicy) {
    showToast('Không tải được bộ kiểm tra khoảng cách tuyến đường. Vui lòng tải lại trang.');
    return;
  }

  const hasManualDistance = Number.isFinite(dist) && dist > 0;
  if (!hasManualDistance) showToast(`🔍 Đang tính toán đường đi thực tế giữa ${from} ➔ ${to}...`);
  const resolution = await window.RouteSegmentPolicy.resolveSegment({
    from,
    to,
    manual: hasManualDistance ? {
      km: dist,
      confirmed: window.confirm(`Xác nhận khoảng cách nhập tay ${dist} km cho chặng ${from} → ${to}?`),
      source: 'map_measurement',
      verifier: 'người dùng giao diện'
    } : null,
    routingClient: window.calculateRealDistance
  });
  if (!resolution.ok) {
    showToast(`⚠️ ${resolution.message}`);
    return;
  }

  const segment = resolution.segment;
  dist = segment.distance_km;
  const realData = segment.distance_source === 'routing_service' ? segment : null;
  if (realData) {
    showToast(`🎯 Khoảng cách thực tế từ GPS: ${dist} km!`);

    // Add dynamic markers and real road curve polyline to Leaflet map
    if (leafletRouteMap && routeMapLayersGroup && typeof L !== 'undefined') {
      const m1 = L.marker([realData.lat1, realData.lon1]).bindPopup(`<b>📍 ${from}</b>`);
      const m2 = L.marker([realData.lat2, realData.lon2]).bindPopup(`<b>📍 ${to}</b>`);
      routeMapLayersGroup.addLayer(m1);
      routeMapLayersGroup.addLayer(m2);

      if (realData.routePath && realData.routePath.length > 0) {
        const line = L.polyline(realData.routePath, { color: '#2563eb', weight: 6, opacity: 0.85 });
        routeMapLayersGroup.addLayer(line);
        leafletRouteMap.fitBounds(line.getBounds(), { padding: [30, 30] });
      }
    }
  } else {
    showToast(`Đã xác nhận khoảng cách nhập tay: ${dist} km.`);
  }

  const tbody = document.getElementById('route-segments-tbody');
  if (tbody) {
    const tr = document.createElement('tr');
    tr.dataset.segmentJson = JSON.stringify(segment);
    tr.style.borderBottom = '1px solid #f1f5f9';
    tr.innerHTML = `
      <td style="padding: 12px 16px; color: #1e293b; font-weight: 600;">${from}</td>
      <td style="padding: 12px 16px; color: #1e293b; font-weight: 600;">${to}</td>
      <td style="padding: 12px 16px; font-weight: 700; color: #2563eb;">${dist} km</td>
      <td style="padding: 12px 16px; text-align: right;">
        <button class="fiori-btn fiori-btn-secondary" style="padding: 4px 10px; font-size: 0.8rem; color: #ef4444; border-color: #fca5a5;" onclick="this.closest('tr').remove(); calculateTotalDistance();"><i class="fa-solid fa-trash"></i></button>
      </td>
    `;
    tbody.appendChild(tr);
    document.getElementById('seg-from').value = '';
    document.getElementById('seg-to').value = '';
    document.getElementById('seg-dist').value = '';
    calculateTotalDistance();
    showToast(`Đã thêm chặng tuyến đường mới: ${from} ➔ ${to} (${dist} km)!`);
  }
};

window.calculateTotalDistance = function () {
  const tbody = document.getElementById('route-segments-tbody');
  if (!tbody) return;
  let total = 0;
  tbody.querySelectorAll('tr').forEach(tr => {
    const text = tr.children[2]?.innerText || '';
    const num = parseFloat(text.replace(/[^0-9.,]/g, '').replace(',', '.')) || 0;
    total += num;
  });
  const totalEl = document.getElementById('route-total-distance');
  if (totalEl) {
    // Giu con so THAT trong dataset, khong chi co chu da dinh dang.
    //
    // `toLocaleString('vi-VN')` bien 1250 thanh "1.250 km", roi luc Luu ai do
    // doc lai bang `parseFloat("1.250")` va duoc 1,25. Tuyen 1.250 km vao co
    // so du lieu thanh 1,25 km — sai 1.000 lan, va moi cong thuc nhan theo km
    // sau do deu sai theo, trong khi thong bao van bao "da luu thanh cong".
    //
    // Doc lai tien/so tu chu da dinh dang luon la sai; day la cho de doc so.
    totalEl.dataset.km = String(Number(total.toFixed(1)));
    totalEl.innerText = `${Number(total.toFixed(1)).toLocaleString('vi-VN')} km`;
  }
};

window.legacySaveRouteConfig = async function () {
  const code = document.getElementById('md-route-code')?.value?.trim();
  const name = document.getElementById('md-route-name')?.value?.trim();

  if (!code) { showToast('⚠️ Vui lòng nhập Mã Tuyến (Route Code)!'); return; }
  if (!name) { showToast('⚠️ Vui lòng nhập Tên Tuyến Đường!'); return; }

  // Collect all segments from the table
  const tbody = document.getElementById('route-segments-tbody');
  const rows = tbody ? Array.from(tbody.querySelectorAll('tr')) : [];
  if (rows.length === 0) { showToast('⚠️ Vui lòng thêm ít nhất 1 chặng đường!'); return; }

  let totalKm = 0;
  const segments = rows.map(tr => {
    if (tr.dataset.segmentJson) {
      const segment = JSON.parse(tr.dataset.segmentJson);
      totalKm += routeSegmentDistanceKm(segment);
      return segment;
    }
    const cells = tr.querySelectorAll('td');
    const distText = cells[2]?.innerText || '0';
    const km = parseFloat(distText.replace(/[^0-9.,]/g, '').replace(',', '.')) || 0;
    totalKm += km;
    return { from: cells[0]?.innerText?.trim(), to: cells[1]?.innerText?.trim(), distance_km: km, dist_km: km };
  });

  const payload = { id: code, name: name, distance_km: totalKm, segments_json: JSON.stringify(segments) };

  showToast(`⏳ Đang lưu Tuyến Đường ${code} vào CSDL...`);
  try {
    const res = await fetch(`${API_BASE}/api/routes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    if (res.ok) {
      showToast(`✅ Đã lưu Tuyến Đường ${code}: ${name} (${totalKm} km) vào CSDL thành công!`);
      // Refresh route dropdown
      if (typeof loadDeliveryOrders === 'function') loadDeliveryOrders();
      if (typeof syncAllDynamicDropdowns === 'function') syncAllDynamicDropdowns();
      // Update the saved routes dropdown in Route Planning tab
      await loadRoutePlanningDropdown();
    } else {
      showToast(`⚠️ Lỗi khi lưu tuyến đường: ${result.detail || 'Vui lòng thử lại!'}`);
    }
  } catch (e) {
    console.error(e);
    showToast(`⚠️ Lỗi kết nối khi lưu Tuyến Đường!`);
  }
};

function masterCostCurrencyCode() {
  return document.getElementById('md-cost-currency')?.value || 'VND';
}

function updateMasterCostCurrencyUI() {
  const currency = masterCostCurrencyCode();
  const label = document.getElementById('md-cost-unit-price-label');
  if (label) label.innerText = currency;
  document.querySelectorAll('.md-cost-currency-suffix').forEach(el => {
    el.innerText = currency;
  });
}

window.onMasterCostCurrencyChange = async function () {
  // The loai xe hien tien theo don vi dang chon, nen doi tien te phai ve lai
  // ca danh muc ben trai chu khong chi panel ben phai.
  setTimeout(() => {
    if (typeof window.renderDynamicFormulaVehicleTypes === 'function') {
      window.renderDynamicFormulaVehicleTypes();
    }
    if (typeof window.renderCostFormulaEditor === 'function') window.renderCostFormulaEditor();
  }, 0);
  const requestedCurrency = masterCostCurrencyCode();
  const activeFormula = masterFormulaStore[activeCostFormulaKey];
  if (!activeFormula?.vehicleTypeId) {
    updateMasterCostCurrencyUI();
    return;
  }
  const select = document.getElementById('md-cost-currency');
  if (select) select.value = activeFormula.currency || 'VND';
  await window.requestCostFormulaContextChange(activeFormula.vehicleTypeId, requestedCurrency);
};

window.addCustomCostComponent = function () {
  const nameInput = document.getElementById('new-cost-name');
  const valInput = document.getElementById('new-cost-value');
  const name = nameInput?.value.trim();
  const val = valInput?.value.trim();
  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
  const currency = masterCostCurrencyCode();

  if (!name || !val) {
    const msg = lang === 'la' ? 'ກະລຸນາປ້ອນຊື່ລາຍການຕົ້ນທຶນ ແລະ ມູນຄ່າ!' :
                lang === 'en' ? 'Please enter cost field name and value!' :
                'Vui lòng nhập Tên trường chi phí và Giá trị!';
    showToast(msg);
    return;
  }

  const tbody = document.getElementById('cost-formula-tbody');
  if (tbody) {
    const tr = document.createElement('tr');
    tr.style.borderBottom = '1px solid #f1f5f9';
    tr.innerHTML = `
      <td style="padding: 12px 16px; color: #1e293b; font-weight: 600;"><i class="fa-solid fa-coins" style="color: #2563eb; margin-right: 8px;"></i> ${name}</td>
      <td style="padding: 12px 16px; text-align: right;"><div style="display:inline-flex; align-items:center; gap:8px;"><input type="text" class="fiori-input" value="${val}" style="width: 160px !important; text-align: right; font-weight: 700; color: #2563eb;"><span class="md-cost-currency-suffix" style="font-size:.78rem; font-weight:900; color:#64748b; min-width:34px; text-align:left;">${currency}</span></div></td>
      <td style="text-align: center;"><button class="fiori-btn fiori-btn-secondary" style="padding: 3px 8px; font-size: 0.75rem; color: #ef4444;" onclick="this.closest('tr').remove()"><i class="fa-solid fa-trash"></i></button></td>
    `;
    tbody.appendChild(tr);
    nameInput.value = '';
    valInput.value = '';
    const successMsg = lang === 'la' ? `ເພີ່ມລາຍການຕົ້ນທຶນໃໝ່ສຳເລັດ: "${name}" (${val} ${currency})!` :
                       lang === 'en' ? `Added new cost field: "${name}" (${val} ${currency})!` :
                       `Đã thêm trường chi phí mới: "${name}" (${val} ${currency})!`;
    showToast(successMsg);
  }
};

let masterFormulaStore = {
  'preset-1': {
    name: 'Mẫu 1: Standard Container Cost (Container 20FT - Tiêu chuẩn)',
    currency: 'VND',
    fuel: '6,250', driver: '500,000', toll: '300,000', wh: '200,000', rate: '1,500'
  },
  'preset-2': {
    name: 'Mẫu 2: Heavy Container 40FT (Container 40FT - Tải Nặng)',
    currency: 'VND',
    fuel: '9,500', driver: '750,000', toll: '450,000', wh: '300,000', rate: '2,200'
  },
  'preset-3': {
    name: 'Mẫu 3: Express Trucking Cost (Xe Tải 10 Tấn - Chuyển Phát Nhanh)',
    currency: 'VND',
    fuel: '4,800', driver: '400,000', toll: '150,000', wh: '100,000', rate: '1,200'
  },
  'preset-4': {
    name: 'Mẫu 4: Reefer Cold Chain (Container Lạnh - Hàng Đông Lạnh)',
    currency: 'VND',
    fuel: '11,000', driver: '900,000', toll: '300,000', wh: '500,000', rate: '3,500'
  }
};

function normalizeVehicleTypeFormulaText(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '');
}

function costFormulaKeyForVehicleType(vehicleType, currency = 'VND') {
  return `vehicle-type::${String(vehicleType?.id || '').trim()}::${String(currency || 'VND').trim().toUpperCase()}`;
}

function legacyFormulaForVehicleType(vehicleType) {
  const vehicleName = normalizeVehicleTypeFormulaText(vehicleType?.name);
  const signatures = ['20ft', '40ft', '10tan', 'reefer', 'containerlanh'];
  const signature = signatures.find(value => vehicleName.includes(value));
  const candidates = Object.values(masterFormulaStore).filter(formula => !formula.vehicleTypeId);
  return candidates.find(formula => {
    const formulaName = normalizeVehicleTypeFormulaText(formula.name);
    return formulaName.includes(vehicleName) || vehicleName.includes(formulaName) || (signature && formulaName.includes(signature));
  });
}

function ensureVehicleTypeFormula(vehicleType, currency = masterCostCurrencyCode()) {
  const normalizedCurrency = String(currency || 'VND').toUpperCase();
  const key = costFormulaKeyForVehicleType(vehicleType, normalizedCurrency);
  if (masterFormulaStore[key]) return key;
  const source = normalizedCurrency === 'VND' ? legacyFormulaForVehicleType(vehicleType) : null;
  masterFormulaStore[key] = {
    name: vehicleType.name || vehicleType.id,
    vehicleTypeId: vehicleType.id,
    vehicleTypeName: vehicleType.name || vehicleType.id,
    currency: normalizedCurrency,
    configured: false,
    fuel: source?.fuel || '0',
    driver: source?.driver || '0',
    toll: source?.toll || '0',
    wh: source?.wh || '0',
    // KHONG lay base_rate lam gia tri du phong cho o "Freight Rate / 1kg".
    //
    // Hai truong nay khac han don vi: base_rate la DON GIA TREN 1 KM (d/km),
    // con o kia la cuoc phi TREN 1 KG HANG (d/kg). Dien cai nay vao cho cai
    // kia khong chi sai so, ma sai ca thu nguyen — voi Container 20FT la 6.250
    // vao cho dang le 1.500, va no chay thang vao bao gia.
    //
    // De trong thi man hinh noi ro "Chua dat don gia/km" — sai ma THAY DUOC
    // tot hon sai ma im lang.
    rate: source?.rate || '0',
    terms: JSON.parse(JSON.stringify(source?.terms || []))
  };
  return key;
}

let activeCostFormulaKey = '';
let savedCostFormulaDraft = '';

function currentCostFormulaDraft() {
  return {
    fuel: document.getElementById('md-cost-fuel-rate')?.value || '0',
    driver: document.getElementById('md-cost-driver-allowance')?.value || '0',
    toll: document.getElementById('md-cost-toll-fee')?.value || '0',
    wh: document.getElementById('md-cost-warehouse-fee')?.value || '0',
    rate: document.getElementById('md-cost-freight-rate')?.value || '0',
    terms: JSON.stringify(costFormulaTerms || [])
    ,expressions: JSON.stringify(costFormulaExpressions)
  };
}

function hasUnsavedCostFormulaChanges() {
  if (savedCostFormulaDraft) {
    const saved = JSON.parse(savedCostFormulaDraft), current = currentCostFormulaDraft();
    return current.terms !== saved.terms || current.expressions !== saved.expressions;
  }
  if (!activeCostFormulaKey || !masterFormulaStore[activeCostFormulaKey]) return false;
  const stored = masterFormulaStore[activeCostFormulaKey];
  const draft = currentCostFormulaDraft();
  return ['fuel', 'driver', 'toll', 'wh', 'rate'].some(field => String(stored[field] || '0') !== String(draft[field] || '0'))
    || JSON.stringify(window.FormulaModel.normalize(stored.terms || [])) !== draft.terms;
}

function showCostFormulaUnsavedDialog() {
  return new Promise(resolve => {
    document.getElementById('cost-formula-unsaved-overlay')?.remove();
    const overlay = document.createElement('div');
    overlay.id = 'cost-formula-unsaved-overlay';
    overlay.style.cssText = 'position:fixed;inset:0;z-index:12000;background:rgba(15,23,42,.52);display:grid;place-items:center;padding:16px;';
    overlay.innerHTML = `
      <div role="dialog" aria-modal="true" aria-labelledby="cost-formula-unsaved-title" style="width:min(520px,100%);background:#fff;border-radius:8px;box-shadow:0 24px 64px rgba(15,23,42,.28);padding:22px;">
        <h3 id="cost-formula-unsaved-title" style="margin:0 0 8px;font-size:1.05rem;color:#0f172a;">Cấu hình giá thành chưa được lưu</h3>
        <p style="margin:0 0 20px;color:#64748b;line-height:1.5;">Anh muốn lưu bộ giá hiện tại trước khi chuyển loại xe hoặc tiền tệ không?</p>
        <div style="display:flex;justify-content:flex-end;gap:10px;flex-wrap:wrap;">
          <button type="button" data-action="stay" class="fiori-btn fiori-btn-secondary">Ở lại</button>
          <button type="button" data-action="discard" class="fiori-btn fiori-btn-secondary">Bỏ thay đổi</button>
          <button type="button" data-action="save" class="fiori-btn"><i class="fa-solid fa-floppy-disk"></i> Lưu thay đổi và chuyển</button>
        </div>
      </div>`;
    overlay.addEventListener('click', event => {
      const action = event.target.closest('[data-action]')?.dataset.action;
      if (!action) return;
      overlay.remove();
      resolve(action);
    });
    document.body.appendChild(overlay);
    overlay.querySelector('[data-action="stay"]')?.focus();
  });
}

window.requestCostFormulaContextChange = async function (vehicleTypeId, currency, element = null) {
  if (window.CostVehicleInline && !window.CostVehicleInline.close()) return;
  const normalizedCurrency = String(currency || 'VND').toUpperCase();
  const vehicleType = (vehTypes || []).find(item => String(item.id) === String(vehicleTypeId));
  if (!vehicleType) return;
  const nextKey = ensureVehicleTypeFormula(vehicleType, normalizedCurrency);
  if (nextKey === activeCostFormulaKey) {
    updateMasterCostCurrencyUI();
    return;
  }

  if (hasUnsavedCostFormulaChanges()) {
    const action = await showCostFormulaUnsavedDialog();
    if (action === 'stay') {
      const select = document.getElementById('md-cost-currency');
      if (select) select.value = masterFormulaStore[activeCostFormulaKey]?.currency || 'VND';
      updateMasterCostCurrencyUI();
      return;
    }
    if (action === 'save') {
      const saved = await window.saveCostFormula();
      if (!saved) return;
    }
    if (action === 'discard' && savedCostFormulaDraft) {
      const saved = JSON.parse(savedCostFormulaDraft);
      masterFormulaStore[activeCostFormulaKey] = {
        ...masterFormulaStore[activeCostFormulaKey], ...saved, terms: JSON.parse(saved.terms), expressions: JSON.parse(saved.expressions || 'null')
      };
    }
  }

  const select = document.getElementById('md-cost-currency');
  if (select) select.value = normalizedCurrency;
  const targetCard = element || Array.from(document.querySelectorAll('.veh-type-card'))
    .find(card => card.dataset.vehicleTypeId === String(vehicleTypeId));
  window.selectFormulaVehicleType(nextKey, targetCard, { notify: false });
};

window.loadSelectedFormulaPreset = function (key, options = {}) {
  const currentKey = key || document.getElementById('md-formula-preset-select')?.value || 'preset-1';
  const changedContext = activeCostFormulaKey !== currentKey;
  const p = masterFormulaStore[currentKey] || masterFormulaStore['preset-1'];

  const fuelInput = document.getElementById('md-cost-fuel-rate');
  const driverInput = document.getElementById('md-cost-driver-allowance');
  const tollInput = document.getElementById('md-cost-toll-fee');
  const whInput = document.getElementById('md-cost-warehouse-fee');
  const rateInput = document.getElementById('md-cost-freight-rate');
  const currencySelect = document.getElementById('md-cost-currency');

  if (fuelInput) fuelInput.value = p.fuel;
  if (driverInput) driverInput.value = p.driver;
  if (tollInput) tollInput.value = p.toll;
  if (whInput) whInput.value = p.wh;
  if (rateInput) rateInput.value = p.rate;
  if (currencySelect) currencySelect.value = p.currency || 'VND';
  updateMasterCostCurrencyUI();

  window.autoCalculateMasterDataCost('qt');
  if (options.notify !== false) {
    const displayName = p ? (p.name || currentKey) : currentKey;
    const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
    const toastMsg = lang === 'la' ? `📂 ໂຫຼດສູດຄິດໄລ່ & ລາຄາມາດຕະຖານຂອງ: ${displayName}` :
                     lang === 'en' ? `📂 Loaded custom formula & rates for: ${displayName}` :
                     `📂 Đã nạp công thức & đơn giá riêng của: ${displayName}`;
    showToast(toastMsg);
  }

  activeCostFormulaKey = currentKey;
  if (changedContext && window.FormulaModel) {
    window.loadCostFormulaTerms();
    savedCostFormulaDraft = JSON.stringify(currentCostFormulaDraft());
  }
};


/* ==========================================================================
   Tỷ giá quy đổi trên màn báo giá và đơn vận chuyển.

   Trước đây mỗi đồng tiền mang kèm một `defaultRate` viết cứng — USD 25.450,
   THB 710, LAK 1,18 — và `workflowCurrencyRate` rơi về con số đó bất cứ khi
   nào ô tỷ giá trống hoặc không đọc được. Ba con số ấy không có nguồn nào và
   không bao giờ được cập nhật, nhưng kết quả quy đổi thì hiện ra y hệt một
   con số thật: "$141.41 USD" trông không khác gì khi tỷ giá đúng.

   Đây là tiền báo cho khách. Không có tỷ giá thì phải NÓI LÀ CHƯA CÓ, chứ
   không được lấy một con số cũ ra dùng thay. Tỷ giá vận hành đến từ
   `/api/currencies/history` qua `renderCurrencyRateHistory(payload, true)`.
   ========================================================================== */

const WORKFLOW_CURRENCY_META = {
  // VND là đồng bản vị nên tỷ lệ 1 là định nghĩa, không phải giá trị dự phòng.
  VND: { label: 'VND - Việt Nam Đồng', symbol: 'VNĐ', rateInputId: null, rate: 1 },
  USD: { label: 'USD - Đô la Mỹ ($)', symbol: '$', rateInputId: 'rate-usd' },
  THB: { label: 'THB - Baht Thái (฿)', symbol: '฿', rateInputId: 'rate-thb' },
  LAK: { label: 'LAK - Kip Lào (₭)', symbol: '₭', rateInputId: 'rate-lak' }
};

function workflowCurrencyCodes() {
  const configured = Array.isArray(appState?.currencies)
    ? appState.currencies
      .map(c => String(c.code || c.id || '').trim().toUpperCase())
      .filter(code => WORKFLOW_CURRENCY_META[code])
    : [];
  const demoFallback = configured.length ? configured : ['USD', 'THB', 'LAK'];
  return Array.from(new Set(['VND', ...demoFallback]));
}

/**
 * Tỷ giá đang dùng của một đồng tiền, hoặc `null` nếu chưa có.
 *
 * Trả `null` chứ không rơi về một con số viết cứng: người gọi phải xử lý
 * trường hợp chưa có tỷ giá, thay vì nhận một con số trông như thật.
 */
function workflowCurrencyRate(code) {
  const meta = WORKFLOW_CURRENCY_META[code] || WORKFLOW_CURRENCY_META.VND;
  if (!meta.rateInputId) return meta.rate ?? null;
  const raw = document.getElementById(meta.rateInputId)?.value;
  const parsed = window.CurrencyRateUtils.parseCurrencyRateNumber(raw);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}
window.workflowCurrencyRate = workflowCurrencyRate;

function workflowCurrencyLabel(code) {
  return (WORKFLOW_CURRENCY_META[code] || { label: code }).label;
}

function workflowCurrencyConversionLabel(amountVnd, code) {
  const meta = WORKFLOW_CURRENCY_META[code];
  if (!meta || code === 'VND') return '';
  const rate = workflowCurrencyRate(code);
  // Chưa có tỷ giá thì nói thẳng. Con số quy đổi bịa ra trông không khác gì
  // con số đúng, và đây là tiền báo cho khách.
  if (rate == null) return ` (chưa có tỷ giá ${code})`;
  const converted = Number(amountVnd || 0) / rate;
  return ` (~ ${meta.symbol}${converted.toLocaleString('vi-VN', { maximumFractionDigits: 2 })} ${code})`;
}

function formatWorkflowCurrencyAmount(amountVnd, code) {
  const amount = Number(amountVnd || 0);
  const meta = WORKFLOW_CURRENCY_META[code];
  // Đồng Việt Nam không có đơn vị nhỏ hơn, nên làm tròn về đồng. `toLocaleString`
  // mặc định giữ tới ba chủ số thập phân, nên bình quân mỗi km 4.461.200 / 44 hiện
  // ra "101.390,909 VNĐ" — vừa không phải số tiền thật, vừa lẫn dấu chấm với dấu phẩy
  // nên đọc rất dễ nhầm.
  if (!meta || code === 'VND') {
    return `${amount.toLocaleString('vi-VN', { maximumFractionDigits: 0 })} VNĐ`;
  }
  const rate = workflowCurrencyRate(code);
  if (rate == null) {
    // Hiện số tiền gốc bằng VNĐ kèm lời nói rõ, thay vì một con số ngoại tệ
    // quy đổi từ tỷ giá không có nguồn.
    return `${amount.toLocaleString('vi-VN', { maximumFractionDigits: 0 })} VNĐ`
      + ` (chưa có tỷ giá ${code})`;
  }
  const converted = amount / rate;
  return `${meta.symbol}${converted.toLocaleString('vi-VN', { maximumFractionDigits: 2 })} ${code}`;
}
window.formatWorkflowCurrencyAmount = formatWorkflowCurrencyAmount;

function selectedWorkflowCurrencyMeta(code) {
  return WORKFLOW_CURRENCY_META[code] || WORKFLOW_CURRENCY_META.VND;
}
window.selectedWorkflowCurrencyMeta = selectedWorkflowCurrencyMeta;

function setWorkflowCostField(id, amountVnd, code) {
  const el = document.getElementById(id);
  if (!el) return;
  el.dataset.vndValue = String(Number(amountVnd || 0));
  el.value = formatWorkflowCurrencyAmount(amountVnd, code);
}
window.setWorkflowCostField = setWorkflowCostField;

function setWorkflowTotalField(id, amountVnd, code) {
  const el = document.getElementById(id);
  if (!el) return;
  const amount = Number(amountVnd || 0);
  el.dataset.vndValue = String(amount);
  el.value = `${amount.toLocaleString('vi-VN')} VNĐ${workflowCurrencyConversionLabel(amount, code)}`;
}
window.setWorkflowTotalField = setWorkflowTotalField;

function parseWorkflowMoneyValue(value) {
  const raw = String(value ?? '').split('(')[0].replace(/[^\d.,-]/g, '').trim();
  if (!raw) return 0;
  const normalized = raw.includes('.') && raw.includes(',')
    ? raw.replace(/\./g, '').replace(',', '.')
    : raw.replace(/\./g, '').replace(/,/g, '');
  const parsed = parseFloat(normalized);
  return Number.isFinite(parsed) ? parsed : 0;
}
window.parseWorkflowMoneyValue = parseWorkflowMoneyValue;

function workflowCostFieldVndValue(id) {
  const el = document.getElementById(id);
  if (!el) return 0;
  return parseWorkflowMoneyValue(el.dataset.vndValue || el.value);
}
window.workflowCostFieldVndValue = workflowCostFieldVndValue;

function workflowTotalFieldVndValue(id) {
  const el = document.getElementById(id);
  if (!el) return 0;
  return parseWorkflowMoneyValue(el.dataset.vndValue || el.value);
}

function workflowNumberInputValue(id) {
  const el = document.getElementById(id);
  if (!el) return 0;
  const raw = el.dataset?.vndValue || el.value;
  return parseWorkflowMoneyValue(raw);
}

/* ==========================================================================
   Đang vận chuyển thì CẤM sửa quyết toán chi phí.

   Giá đã chốt trên báo giá. Trong lúc xe còn trên đường thì chưa biết
   phát sinh là bao nhiêu, nên không được sửa tiền — mở ra là mở cửa cho
   người ta đổi số giữa chuyến, mà chứng từ ký nhận thì chưa có.

   Backend ĐÃ chặn: `_save_trip_cost_rows` trả 409 `TRIP_NOT_COMPLETED` —
   "Chỉ được quyết toán chi phí sau khi chuyến đã hoàn thành POD". Nhưng
   giao diện vẫn hiện nút "Thêm khoản phí" và "Lưu chi phí", nên bấm vào chỉ
   nhận một lời từ chối. Đó là một nút NÓI DỐI: nó mời người ta bấm một việc
   hệ thống không cho làm.

   Mốc mở là Trip đã hoàn thành POD, chứ không phải xe vừa đến nơi — tiền
   chỉ nên chốt khi đã có chứng từ ký nhận. `resolveCompletedTripForDO` là
   chỗ tra mốc đó, và `setDOSettlementSaveState` là chỗ nhận kết quả, nên hai
   nút cùng theo MỘT quyết định thay vì mỗi nút tự đoán.
   ========================================================================== */

function refreshDOSettlementLineControls(quyetToanDuoc = true, lyDo = "") {
  const addBtn = document.getElementById('btn-add-do-settlement-line');
  if (addBtn) {
    addBtn.style.display = quyetToanDuoc ? 'inline-flex' : 'none';
  }
  document.querySelectorAll('#do-settlement-lines-tbody input').forEach(input => {
    input.disabled = !quyetToanDuoc;
  });
  document.querySelectorAll('#do-settlement-lines-tbody button').forEach(button => {
    button.style.display = quyetToanDuoc ? 'inline-flex' : 'none';
  });

  // Nói RÕ vì sao không sửa được, ngay trong khối. Ẩn nút mà không nói gì
  // thì người dùng tưởng màn hình hỏng.
  const oLyDo = document.getElementById('do-settlement-locked-note');
  if (oLyDo) {
    oLyDo.hidden = Boolean(quyetToanDuoc) || !lyDo;
    oLyDo.innerHTML = lyDo ? `<i class="fa-solid fa-lock"></i> ${escapeHtml(lyDo)}` : '';
  }
}

/**
 * Lý do KHÔNG quyết toán được, nói theo đúng trạng thái đang có.
 *
 * Một câu "chưa quyết toán được" chung chung thì người dùng không biết phải
 * chờ gì. Mỗi trạng thái có một việc cần làm khác nhau.
 */
function lyDoChuaQuyetToanDuoc(doId) {
  const don = (eplDeliveryOrders || []).find(d => String(d.id) === String(doId));
  const tt = String(don?.canonical_status || '').toLowerCase();
  if (tt === "cancelled") {
    return "Lệnh giao hàng đã hủy nên không quyết toán chi phí.";
  }
  if (tt === "pending") {
    return "Lệnh chưa xuất bến nên chưa có chi phí phát sinh nào để quyết toán."
      + " Hãy điều phối xe và cho chuyến khởi hành trước.";
  }
  if (tt === "in_transit" || tt === "arrived") {
    return "Xe đang trên đường — trong lúc vận chuyển KHÔNG được sửa giá đã"
      + " chốt. Sau khi giao xong và có POD ký nhận thì mới thêm được khoản"
      + " phát sinh và chốt giá cuối.";
  }
  return "Chuyến của lệnh này chưa hoàn thành POD nên chưa quyết toán được."
    + " Hãy hoàn tất giao hàng ở màn Hoàn tất giao trước.";
}

function doSettlementLineTemplate(line = {}, index = 0) {
  const item = fixUIText(line.item || line.name || '');
  const original = Number(line.original_amount ?? line.original ?? line.base_amount ?? 0) || 0;
  const legacyIncrease = Number(line.amount ?? line.increase_amount ?? line.delta_amount ?? 0) || 0;
  const actual = Number(line.actual_amount ?? line.actual ?? line.increased_amount ?? (original + legacyIncrease)) || 0;
  const increase = Math.max(0, actual - original);
  const note = fixUIText(line.note || line.reason || '');
  const maCostindex = String(line.cost_index || '').trim();
  return `
    <tr data-do-settlement-line data-cost-index="${doBoardEscape(maCostindex)}" data-charge-type="${doBoardEscape(line.charge_type || '')}">
      <td style="padding:9px 12px; border-bottom:1px solid #eef2f7;">
        <input class="fiori-input do-settlement-item" type="text" value="${doBoardEscape(item)}" placeholder="Ví dụ: Xăng dầu" style="width:100%; border:0; border-bottom:1px solid #2563eb; background:transparent; outline:none; font-weight:800; color:#0f172a;">
        <small class="do-settlement-costindex" style="display:block; margin-top:3px; font-size:.7rem; color:${maCostindex ? '#0369a1' : '#b45309'}; font-weight:700;">${maCostindex ? 'Acc code ' + doBoardEscape(maCostindex) : 'chưa có acc code'}</small>
      </td>
      <td style="padding:9px 12px; border-bottom:1px solid #eef2f7;">
        <input class="fiori-input do-settlement-original" type="number" min="0" step="1000" value="${original}" oninput="refreshDOSettlementTotals()" placeholder="0" style="width:100%; padding:8px 10px; border:1px solid #cbd5e1; border-radius:7px; font-weight:800;">
      </td>
      <td style="padding:9px 12px; border-bottom:1px solid #eef2f7;">
        <input class="fiori-input do-settlement-actual" type="number" min="0" step="1000" value="${actual}" oninput="refreshDOSettlementTotals()" placeholder="0" style="width:100%; padding:8px 10px; border:1px solid #cbd5e1; border-radius:7px; font-weight:800;">
      </td>
      <td style="padding:9px 12px; border-bottom:1px solid #eef2f7;">
        <input class="fiori-input do-settlement-increase" type="text" value="${formatWorkflowCurrencyAmount(increase, 'VND')}" readonly data-value="${increase}" style="width:100%; padding:8px 10px; border:1px solid #fed7aa; border-radius:7px; background:#fff7ed; color:#b45309; font-weight:900;">
      </td>
      <td style="padding:9px 12px; border-bottom:1px solid #eef2f7;">
        <input class="fiori-input do-settlement-note" type="text" value="${doBoardEscape(note)}" placeholder="Lý do phát sinh..." style="width:100%; border:0; border-bottom:1px solid #cbd5e1; background:transparent; outline:none;">
      </td>
      <td style="padding:9px 12px; border-bottom:1px solid #eef2f7; text-align:center; position:sticky; right:0; background:#ffffff; z-index:1; box-shadow:-8px 0 12px rgba(15,23,42,.04);">
        <button type="button" onclick="removeDOSettlementLine(this)" title="Xóa dòng" style="width:30px; height:30px; border:1px solid #fecaca; color:#dc2626; background:#fff; border-radius:7px; cursor:pointer;"><i class="fa-solid fa-trash"></i></button>
      </td>
    </tr>
  `;
}

function renderDOSettlementLines(lines = []) {
  const tbody = document.getElementById('do-settlement-lines-tbody');
  if (!tbody) return;
  const safeLines = Array.isArray(lines) ? lines : [];
  tbody.innerHTML = safeLines.map((line, index) => doSettlementLineTemplate(line, index)).join('');
  refreshDOSettlementTotals();
  refreshDOSettlementLineControls();
}

function collectDOSettlementLines() {
  return Array.from(document.querySelectorAll('#do-settlement-lines-tbody tr[data-do-settlement-line]')).map(row => {
    const item = (row.querySelector('.do-settlement-item')?.value || '').trim();
    const original = parseWorkflowMoneyValue(row.querySelector('.do-settlement-original')?.value || 0);
    const actual = parseWorkflowMoneyValue(row.querySelector('.do-settlement-actual')?.value || 0);
    const note = row.querySelector('.do-settlement-note')?.value || '';
    // Mã costindex và mã khoản mục đi kèm dòng khi lưu, để bảng chi phí thực tế
    // mang đúng mã mà dòng đã có từ công thức — không để máy chủ phải đoán lại.
    const cost_index = (row.dataset.costIndex || '').trim() || undefined;
    const charge_type = (row.dataset.chargeType || '').trim() || undefined;
    return { name: item, original_amount: original, actual_amount: actual, note, cost_index, charge_type };
  }).filter(line => line.name || line.original_amount || line.actual_amount || line.note);
}

window.addDOSettlementLine = function (line = {}) {
  const tbody = document.getElementById('do-settlement-lines-tbody');
  if (!tbody) return;
  tbody.insertAdjacentHTML('beforeend', doSettlementLineTemplate({ name: '', original_amount: 0, actual_amount: 0, note: '', ...line }));
  refreshDOSettlementTotals();
};

window.removeDOSettlementLine = function (button) {
  const row = button?.closest?.('tr[data-do-settlement-line]');
  if (row) row.remove();
  refreshDOSettlementTotals();
};

function refreshDOSettlementTotals() {
  const contractInput = document.getElementById('do-contract-total');
  const originalDisplay = document.getElementById('do-original-contract-amount-display');
  const extraInput = document.getElementById('do-extra-cost');
  const extraDisplay = document.getElementById('do-extra-cost-total-display');
  const payableInput = document.getElementById('do-payable-total');
  if (!contractInput || !extraInput || !payableInput) return;
  const currency = contractInput.dataset.currency || 'VND';
  const contractVnd = workflowNumberInputValue('do-contract-total');
  let extraVnd = 0;
  const notes = [];
  document.querySelectorAll('#do-settlement-lines-tbody tr[data-do-settlement-line]').forEach(row => {
    const original = parseWorkflowMoneyValue(row.querySelector('.do-settlement-original')?.value || 0);
    const actual = parseWorkflowMoneyValue(row.querySelector('.do-settlement-actual')?.value || 0);
    const increase = Math.max(0, actual - original);
    extraVnd += increase;
    const increaseInput = row.querySelector('.do-settlement-increase');
    if (increaseInput) {
      increaseInput.dataset.value = String(increase);
      increaseInput.value = formatWorkflowCurrencyAmount(increase, currency);
    }
    const item = row.querySelector('.do-settlement-item')?.value || '';
    const note = row.querySelector('.do-settlement-note')?.value || '';
    if (item || note || original || actual) {
      notes.push(`${item || 'Khoản phát sinh'}: ${formatWorkflowCurrencyAmount(original, currency)} → ${formatWorkflowCurrencyAmount(actual, currency)}${note ? ` - ${note}` : ''}`);
    }
  });
  const payableVnd = contractVnd + extraVnd;
  contractInput.dataset.vndValue = String(contractVnd);
  extraInput.dataset.vndValue = String(extraVnd);
  extraInput.value = String(extraVnd);
  const reasonInput = document.getElementById('do-extra-cost-reason');
  if (reasonInput) reasonInput.value = notes.join('\n');
  if (extraDisplay) {
    extraDisplay.dataset.vndValue = String(extraVnd);
    extraDisplay.value = formatWorkflowCurrencyAmount(extraVnd, currency);
  }
  if (originalDisplay) {
    originalDisplay.dataset.vndValue = String(contractVnd);
    originalDisplay.value = formatWorkflowCurrencyAmount(contractVnd, currency);
  }
  payableInput.dataset.vndValue = String(payableVnd);
  contractInput.value = formatWorkflowCurrencyAmount(contractVnd, currency);
  payableInput.value = formatWorkflowCurrencyAmount(payableVnd, currency);
}
window.refreshDOSettlementTotals = refreshDOSettlementTotals;

/** Báo giá gốc của một DO (luồng mới: DO sinh từ báo giá, `quotation_id`). */
function baoGiaCuaDO(source) {
  const qid = source && (source.quotation_id || '');
  if (!qid) return null;
  const ds = (crmQuotations && crmQuotations.length) ? crmQuotations : (appState.quotations || []);
  return ds.find(q => String(q.id) === String(qid)) || null;
}

function setDOSettlementFromSource(source = {}) {
  // Giá gốc theo BÁO GIÁ: DO kế thừa `unit_price` lúc sinh từ báo giá được
  // chấp nhận. Bước Đơn hàng (SO) đã trục xuất khỏi hệ thống (migration 049).
  const bg = baoGiaCuaDO(source);
  const contractVnd = Number(source.contract_total || source.contract_total_amount || source.total_contract_amount
    || (bg && bg.selling_price) || source.unit_price || source.total_amount || 0) || 0;
  const extraVnd = Number(source.additional_cost_amount || source.extra_cost_amount || source.extra_cost || 0);
  const currency = source.currency_code || (bg && bg.currency_code) || 'VND';
  const contractInput = document.getElementById('do-contract-total');
  const originalDisplay = document.getElementById('do-original-contract-amount-display');
  const extraInput = document.getElementById('do-extra-cost');
  const reasonInput = document.getElementById('do-extra-cost-reason');
  const sourceBadge = document.getElementById('do-settlement-source-badge');
  const savedLines = source.additional_cost_lines || source.settlement_lines || source.extra_cost_lines || [];
  const reason = source.additional_cost_reason || source.extra_cost_reason || "";

  if (contractInput) {
    contractInput.dataset.vndValue = String(contractVnd);
    contractInput.dataset.currency = currency;
  }
  if (originalDisplay) {
    originalDisplay.dataset.vndValue = String(contractVnd);
    originalDisplay.value = formatWorkflowCurrencyAmount(contractVnd, currency);
  }
  if (extraInput) {
    extraInput.value = String(extraVnd || 0);
    extraInput.dataset.vndValue = String(extraVnd || 0);
  }
  if (reasonInput) reasonInput.value = reason;
  if (sourceBadge) sourceBadge.textContent = bg ? `Theo báo giá ${bg.id}` : (so.id ? `Theo đơn hàng cũ ${so.id}` : 'Theo báo giá');
  if (Array.isArray(savedLines) && savedLines.length) {
    renderDOSettlementLines(savedLines);
  } else if (extraVnd > 0) {
    renderDOSettlementLines([{ name: 'Chi phí phát sinh khác', original_amount: 0, actual_amount: extraVnd, note: reason }]);
  } else {
    renderDOSettlementLines([]);
  }
  refreshDOSettlementTotals();
}
window.setDOSettlementFromSource = setDOSettlementFromSource;

window.viewOriginalDOFromSettlement = function () {
  const doId = document.getElementById('do-id')?.value || '';
  const price = document.getElementById('do-original-contract-amount-display')?.value
    || document.getElementById('do-contract-total')?.value
    || '0 VND';
  if (!doId) {
    showToast('Chua co DO de xem gia ban dau.');
    return;
  }
  const target = document.getElementById('do-sec-info') || document.getElementById('fiori-do-form');
  if (target?.scrollIntoView) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  showToast(`DO ban dau ${doId}: gia hop dong ${price}. Ben duoi chi nhap chi phi phat sinh/extend.`);
};

function tripContainsDeliveryOrder(trip, doId) {
  const ids = trip?.delivery_order_ids || trip?.delivery_orders || trip?.do_ids || [];
  return (Array.isArray(ids) && ids.some(id => String(id) === String(doId)))
    || String(trip?.delivery_order_id || '') === String(doId);
}

function isCompletedSettlementTrip(trip) {
  return ['completed', 'delivered'].includes(String(trip?.status || '').toLowerCase());
}

async function resolveCompletedTripForDO(doId) {
  let trips = Array.isArray(appState?.transport_trips) ? appState.transport_trips : [];
  if (!trips.length || !trips.some(trip => tripContainsDeliveryOrder(trip, doId))) {
    const response = await fetch(`${API_BASE}/api/tms/trips`, { headers: financeAuthHeaders() });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload?.detail?.message || payload?.message || 'Không tải được danh sách Trip.');
    trips = paginatedItems(payload);
    if (appState && typeof appState === 'object') appState.transport_trips = trips;
  }
  return trips.find(trip => tripContainsDeliveryOrder(trip, doId) && isCompletedSettlementTrip(trip)) || null;
}

function setDOSettlementSaveState(trip, loading = false) {
  const button = document.getElementById('btn-save-do-settlement');
  if (!button) return;
  button.dataset.tripId = trip?.id || '';
  button.disabled = loading || !trip;
  // Đây là chỗ DUY NHẤT biết có Trip hoàn thành hay không, nên cũng là chỗ
  // quyết định cho hai nút kia — thay vì mỗi nút tự đoán trạng thái.
  if (!loading) {
    const doId = document.getElementById('do-id')?.value || '';
    refreshDOSettlementLineControls(Boolean(trip),
      trip ? '' : lyDoChuaQuyetToanDuoc(doId));
  }
  button.style.opacity = button.disabled ? '.58' : '1';
  button.style.cursor = button.disabled ? 'not-allowed' : 'pointer';
  button.title = loading
    ? 'Đang tải chi phí thực tế...'
    : trip
      ? `Lưu chi phí cho Trip ${trip.id}`
      : 'Chỉ quyết toán chi phí sau khi Trip hoàn thành';
}

async function loadDOSettlementCost(doId) {
  setDOSettlementSaveState(null, true);
  try {
    const trip = await resolveCompletedTripForDO(doId);
    setDOSettlementSaveState(trip, false);
    if (!trip) return null;
    const response = await fetch(`${API_BASE}/api/tms/finance/trips/${encodeURIComponent(trip.id)}/actual-cost`, {
      headers: financeAuthHeaders()
    });
    if (response.status === 404) {
      renderDOSettlementLines([]);
      return trip;
    }
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload?.detail?.message || payload?.message || 'Không tải được chi phí thực tế.');
    renderDOSettlementLines(payload?.data?.lines || []);
    return trip;
  } catch (error) {
    setDOSettlementSaveState(null, false);
    showToast(`⚠️ ${error.message}`);
    return null;
  }
}

async function saveDOSettlementCost() {
  const doId = document.getElementById('do-id')?.value || '';
  if (!doId) {
    showToast('Chưa xác định được DO để lưu chi phí.');
    return;
  }
  const button = document.getElementById('btn-save-do-settlement');
  let tripId = button?.dataset.tripId || '';
  if (!tripId) {
    const trip = await loadDOSettlementCost(doId);
    tripId = trip?.id || '';
  }
  if (!tripId) {
    showToast('Chỉ được quyết toán chi phí sau khi Trip của DO đã hoàn thành.');
    return;
  }
  const lines = collectDOSettlementLines();
  if (!lines.length || lines.some(line => !line.name)) {
    showToast('Mỗi dòng chi phí phải có tên khoản mục.');
    return;
  }
  if (lines.some(line => line.actual_amount < line.original_amount)) {
    showToast('Giá thực tế không được nhỏ hơn giá ban đầu.');
    return;
  }
  const currencyCode = document.getElementById('do-contract-total')?.dataset.currency || 'VND';
  const result = await executeFinanceCommand({
    path: `/api/tms/finance/trips/${encodeURIComponent(tripId)}/actual-cost`,
    method: 'PUT',
    body: { currency_code: currencyCode, lines }
  });
  if (result?.ok) {
    renderDOSettlementLines(result.payload?.data?.lines || lines);
    setDOSettlementSaveState({ id: tripId }, false);
    const refreshCloseoutDoId = button?.dataset.refreshCloseoutDoId || '';
    if (refreshCloseoutDoId && typeof window.loadDeliveryOrderCloseout === 'function') {
      window.loadDeliveryOrderCloseout(refreshCloseoutDoId);
      showToast(`Da cap nhat gia thuc te va nap lai closeout cho DO ${refreshCloseoutDoId}.`);
    }
  }
}
window.saveDOSettlementCost = saveDOSettlementCost;

function refreshWorkflowCurrencyAmounts(formType = 'qt') {
  if (formType !== 'qt') return;
  const curr = document.getElementById('qt-currency')?.value || 'VND';
  const fuel = workflowCostFieldVndValue('qt-fuel');
  const driver = workflowCostFieldVndValue('qt-driver');
  const toll = workflowCostFieldVndValue('qt-toll');
  const currentTotal = workflowTotalFieldVndValue('qt-selling-price') || fuel + driver + toll;
  setWorkflowCostField('qt-fuel', fuel, curr);
  setWorkflowCostField('qt-driver', driver, curr);
  setWorkflowCostField('qt-toll', toll, curr);
  setWorkflowTotalField('qt-selling-price', currentTotal, curr);
}
window.refreshWorkflowCurrencyAmounts = refreshWorkflowCurrencyAmounts;

window.onWorkflowCurrencyChange = function (formType = 'qt') {
  refreshWorkflowCurrencyAmounts(formType);
};

function renderWorkflowCurrencyOptions(selectIds = ['qt-currency']) {
  const codes = workflowCurrencyCodes();
  selectIds.forEach(id => {
    const sel = document.getElementById(id);
    if (!sel) return;
    const current = sel.value;
    sel.innerHTML = codes.map(code => `<option value="${code}">${workflowCurrencyLabel(code)}</option>`).join('');
    sel.value = codes.includes(current) ? current : codes[0];
  });
}
window.renderWorkflowCurrencyOptions = renderWorkflowCurrencyOptions;

async function loadCostFormulasFromBackend() {
  try {
    const response = await fetch(`${API_BASE}/api/cost-formulas`);
    if (!response.ok) return;
    const rows = await response.json();
    (Array.isArray(rows) ? rows : []).forEach(row => {
      const components = row.components || {};
      const storeKey = row.vehicle_type_id
        ? costFormulaKeyForVehicleType({ id: row.vehicle_type_id }, row.currency || 'VND')
        : row.id;
      masterFormulaStore[storeKey] = {
        ...(masterFormulaStore[storeKey] || {}),
        name: row.name || masterFormulaStore[storeKey]?.name || row.id,
        vehicleTypeId: row.vehicle_type_id || masterFormulaStore[storeKey]?.vehicleTypeId || '',
        vehicleTypeName: row.name || masterFormulaStore[storeKey]?.vehicleTypeName || row.id,
        currency: row.currency || 'VND',
        configured: row.configured !== false,
        terms: Array.isArray(row.terms) ? row.terms : masterFormulaStore[storeKey]?.terms,
        expressions: row.expressions || null,
        history: row.history || [],
        updatedAt: row.updated_at || null,
        fuel: components.fuel || masterFormulaStore[storeKey]?.fuel || '0',
        driver: components.driver || masterFormulaStore[storeKey]?.driver || '0',
        toll: components.toll || masterFormulaStore[storeKey]?.toll || '0',
        wh: components.warehouse || masterFormulaStore[storeKey]?.wh || '0',
        rate: components.freight_rate || masterFormulaStore[storeKey]?.rate || '0'
      };
    });
    window.loadSelectedFormulaPreset(
      document.getElementById('md-formula-preset-select')?.value || 'preset-1',
      { notify: false }
    );
  } catch (error) {
    baoNapThatBai('công thức giá thành', error);
  }
}
window.loadCostFormulasFromBackend = loadCostFormulasFromBackend;

window.saveCostFormula = async function () {
  if (costFormulaExpressions) {
    try { window.CostExpression.evaluate(costFormulaExpressions, costFormulaTerms, costSampleTrip); }
    catch (error) { showToast(error.message, 'error'); return false; }
  }
  const currentKey = activeCostFormulaKey || document.getElementById('md-formula-preset-select')?.value || 'preset-1';
  const currency = masterCostCurrencyCode();

  // O trong thi luu 0, KHONG bia mot don gia.
  //
  // Ban truoc rot san 6.250 / 500.000 / 300.000 / 200.000 / 1.500 vao khi o
  // trong, nen bam Luu ma chua nhap gi la co so du lieu co mot bo don gia
  // khong ai dat ra, va man hinh bao "Da cau hinh". Voi 0 thi man hinh noi
  // dung su that: "Chua dat don gia".
  const doc = id => document.getElementById(id)?.value?.trim() || '0';
  const fuelInput = doc('md-cost-fuel-rate');
  const driverInput = doc('md-cost-driver-allowance');
  const tollInput = doc('md-cost-toll-fee');
  const whInput = doc('md-cost-warehouse-fee');
  const rateInput = doc('md-cost-freight-rate');

  const badge = document.getElementById('selected-veh-type-badge');
  const selectedVehicleTypeId = masterFormulaStore[currentKey]?.vehicleTypeId || '';
  const vehTypeName = masterFormulaStore[currentKey]?.vehicleTypeName || (badge ? badge.innerText.trim() : (masterFormulaStore[currentKey]?.name || 'Loại xe đã chọn'));

  window.autoCalculateMasterDataCost('qt');
  updateMasterCostCurrencyUI();
  const payload = {
    id: currentKey,
    // Gui kem danh sach hang tu, de cong thuc dong di tron vong: mo lai
    // loai xe thi thay dung cac cau phan da them, ke ca cau phan tuy chinh.
    terms: costFormulaTerms,
    expressions: costFormulaExpressions,
    expected_updated_at: masterFormulaStore[currentKey]?.updatedAt || null,
    vehicle_type_id: selectedVehicleTypeId,
    name: vehTypeName,
    currency,
    fuel: fuelInput,
    driver: driverInput,
    toll: tollInput,
    warehouse: whInput,
    freight_rate: rateInput,
  };
  try {
    const response = await fetch(`${API_BASE}/api/cost-formulas`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const result = await response.json().catch(() => ({}));
    if (response.ok) {
      // Ve lai danh muc ben trai: truoc day the van hien con so cu vi no lay tu
      // base_rate, mot truong khac han va khong ai cap nhat.
      if (typeof window.renderDynamicFormulaVehicleTypes === 'function') {
        window.renderDynamicFormulaVehicleTypes();
      }
      // Acc code dung chung: may chu vua lan ma sang cong thuc cua loai xe khac, nap lai
      // de mo loai xe ke tiep khong con thay o trong.
      if (typeof loadCostFormulasFromBackend === 'function') loadCostFormulasFromBackend();
    }
    if (!response.ok) {
      showToast(result?.detail || 'Không lưu được công thức giá thành vào CSDL.', 'error');
      return false;
    }
    masterFormulaStore[currentKey] = {
      ...(masterFormulaStore[currentKey] || {}),
      fuel: fuelInput,
      driver: driverInput,
      toll: tollInput,
      wh: whInput,
      rate: rateInput,
      currency,
      configured: true,
      // Ghi ro hang tu: day la nguon su that cua cong thuc, khong phai nam o
      // don gia. Thieu no thi phep so sanh "co thay doi chua" o duoi so lech.
      terms: JSON.parse(JSON.stringify(costFormulaTerms || [])),
    };
    masterFormulaStore[currentKey].currency = currency;
    masterFormulaStore[currentKey].expressions = result.data?.expressions || costFormulaExpressions;
    masterFormulaStore[currentKey].history = result.data?.history || [];
    masterFormulaStore[currentKey].updatedAt = result.data?.updated_at || null;
    window.CostComparison?.invalidate();
    window.CostFormulaBuilder?.refresh();
    savedCostFormulaDraft = JSON.stringify(currentCostFormulaDraft());
    showToast(result?.message || `Đã lưu cấu hình giá thành ${currency} cho loại xe "${vehTypeName}" vào CSDL!`);
    return true;
  } catch (error) {
    showToast('Không kết nối được backend khi lưu công thức giá thành.');
    return false;
  }
};

/**
 * Vẽ bảng chi phí trên báo giá, sinh từ công thức của loại xe đang chọn.
 *
 * Bản cũ chỉ có ba ô cố định — nhiên liệu, tài xế, cầu đường — nên:
 *   · cước phí theo kg không có chỗ hiện và bị bỏ hẳn khỏi tổng;
 *   · phí bãi bị cộng vào ô "Phí cầu đường" nên ô đó nói sai tên con số;
 *   · cấu phần người dùng tự thêm không xuất hiện ở đâu cả.
 */
/** To mau nhan trang thai cua khoi chi phi. Dung chung cho bao gia va don hang. */
function setCostStatusBadge(id, text, tone) {
  const status = document.getElementById(id);
  if (!status) return;
  status.textContent = text;
  const tones = {
    ok: ['#ecfdf5', '#059669', '#a7f3d0'],
    warn: ['#fffbeb', '#b45309', '#fde68a'],
  };
  const [bg, fg, border] = tones[tone] || tones.warn;
  status.style.background = bg;
  status.style.color = fg;
  status.style.border = `1px solid ${border}`;
}

function renderCostBreakdown(hostId, quote, currencyId) {
  const host = document.getElementById(hostId);
  if (!host) return;
  const currency = document.getElementById(currencyId)?.value || quote.currency || 'VND';
  const money = amount => formatWorkflowCurrencyAmount(amount, currency);

  // Chưa đủ đầu vào thì nói thiếu gì và KHÔNG đưa ra con số. Một tổng tính
  // thiếu trông y như một tổng đúng, và đó là cách báo giá sai đi tới khách.
  if (!quote.ready) {
    host.innerHTML = `
      <div class="qt-cost-blocked">
        <b><i class="fa-solid fa-circle-exclamation" aria-hidden="true"></i> Chưa tính được cước</b>
        <ul>${quote.blockers.map(item => `<li>${escapeHtml(item.message)}</li>`).join('')}</ul>
      </div>`;
    return;
  }

  const nhom = kind => quote.rows.filter(row => row.kind === kind);

  /**
   * Mot khoi cau phan (chi phi hoac gia ban).
   *
   * Tach hai khoi la diem quan trong nhat cua man nay: bon cau phan xang dau /
   * phu cap / BOT / phi bai la tien CHI RA, con cuoc phi theo kg la tien THU
   * CUA KHACH. Truoc day cong ca nam vao mot dong "Tong cuoc bao gia", nen con
   * so 4.461.200 khong phai gia thanh (861.200) cung khong phai gia ban
   * (3.600.000) - no la chi phi cong doanh thu.
   */
  const khoi = (kind, tieuDe, tong, ghiChu) => {
    const rows = nhom(kind);
    if (!rows.length) return '';
    return `
      <tr class="qt-cost-group qt-cost-group-${kind}">
        <td colspan="4">${escapeHtml(tieuDe)}${ghiChu ? ` <small>${escapeHtml(ghiChu)}</small>` : ''}</td>
      </tr>
      ${rows.map(row => `
        <tr class="${row.rate ? '' : 'is-zero'}">
          <td><span class="qt-cost-sign">${row.operator === 'sub' ? '−' : '+'}</span>
              ${escapeHtml(row.label)}</td>
          <td class="qt-cost-num">${money(row.rate)}<small>${escapeHtml(row.unit)}</small></td>
          <td class="qt-cost-num">${row.factor === 'per_trip'
            ? '1 chuyến' : `× ${row.multiplier.toLocaleString('vi-VN')}`}</td>
          <td class="qt-cost-num qt-cost-amount">${money(row.amount)}</td>
        </tr>`).join('')}
      <tr class="qt-cost-subtotal">
        <td colspan="3">${escapeHtml(tong.nhan)}</td>
        <td class="qt-cost-num">${money(tong.gia_tri)}</td>
      </tr>`;
  };

  host.innerHTML = `
    <div class="qt-cost-scroll">
      <table class="qt-cost-table">
        <thead>
          <tr><th>Khoản mục</th><th>Đơn giá</th><th>Nhân với</th><th>Thành tiền</th></tr>
        </thead>
        <tbody>
          ${khoi('revenue', 'Cước thu khách', { nhan: 'Tổng cước báo giá', gia_tri: quote.revenue },
            'tiền khách trả')}
          ${khoi('cost', 'Giá thành chuyến', { nhan: 'Tổng giá thành', gia_tri: quote.cost },
            'tiền mình chi ra')}
        </tbody>
        <tfoot>
          <tr>
            <td colspan="3">Lợi nhuận chuyến
              <small>${escapeHtml(quote.formulaName || '')} · ${quote.km.toLocaleString('vi-VN')} km${
                quote.tonnes === null ? '' : ` · ${quote.tonnes.toLocaleString('vi-VN')} tấn`}</small></td>
            <td class="qt-cost-num qt-cost-total">${money(quote.profit)}${
              quote.marginPct === null ? '' : `<small> · ${quote.marginPct.toFixed(1)}%</small>`}</td>
          </tr>
          <tr class="qt-cost-perkm">
            <td colspan="3">Giá thành mỗi km</td>
            <td class="qt-cost-num">${money(quote.perKm)}/km</td>
          </tr>
        </tfoot>
      </table>
    </div>
    ${quote.notes.length ? `<ul class="qt-cost-notes">${quote.notes.map(note =>
      `<li><i class="fa-solid fa-circle-info" aria-hidden="true"></i> ${escapeHtml(note)}</li>`).join('')}</ul>` : ''}`;
}

/**
 * Tính cước báo giá từ công thức đã cấu hình trong Dữ liệu gốc.
 *
 * Bốn lỗi của bản cũ, đều làm sai tiền:
 *
 *   1. Không đọc ô cước phí vận chuyển, nên cấu phần lớn nhất — cước theo kg —
 *      biến mất khỏi báo giá.
 *   2. Nhân một hệ số bịa `(loại xe.max_weight / 15000)` vào xăng dầu và phụ
 *      cấp. Con số 15000 không có nguồn, và nó lấy tải trọng tối đa của loại xe
 *      chứ không phải khối lượng hàng thật.
 *   3. Có số cứng dự phòng 6250 / 500000 / 300000 / 200000, nên chưa nạp được
 *      cấu hình vẫn hiện ra một con số trông rất chắc chắn.
 *   4. Đọc năm ô đơn giá đang mở trên màn Dữ liệu gốc, tức công thức của loại
 *      xe MỞ GẦN NHẤT, chứ không phải loại xe đang chọn trên báo giá.
 *
 * Nay mọi con số đi qua js/quotation-pricing.js: đúng công thức của loại xe
 * đang chọn, số km của tuyến đang chọn, khối lượng hàng đã nhập.
 */
/**
 * Ket qua tinh cuoc gan nhat cua man bao gia.
 *
 * Luc Luu phai gui ba con so tach roi (gia thanh / cuoc thu khach / ti le loi
 * nhuan). Doc nguoc lai tu cac o hien thi la doc lai chinh cai minh vua ghi ra
 * chu, roi phai bo dau phan cach va ky hieu tien te - vong vo va de sai.
 */
let lastQuotationQuote = null;

window.autoCalculateMasterDataCost = function () {
  const setStatus = (text, tone) => setCostStatusBadge('qt-cost-status', text, tone);

  renderWorkflowCurrencyOptions(['qt-currency']);
  const currency = document.getElementById('qt-currency')?.value || 'VND';
  const routeId = document.getElementById('qt-route')?.value || '';
  // Chua nhap KHAC 0 kg: chua nhap la chua biet, 0 la chuyen chay rong.
  const qtWeightRaw = String(document.getElementById('qt-weight-kg')?.value ?? '').trim();

  const quote = window.QuotationPricing.price({
    store: masterFormulaStore,
    vehicleTypes: vehTypes,
    cargoType: document.getElementById('qt-cargo-type')?.value || '',
    route: (eplRoutes || []).find(route => route.id === routeId) || null,
    // Doc dung o "Tai trong (kg)" da co san o phan boi canh tuyen duong. O do
    // vua la cho nhap khoi luong hang, vua la can cu de de xuat loai xe phu
    // hop — nen dung them mot o rieng cho cong thuc la hai cho noi cung mot
    // thu va chac chan se lech nhau.
    tonnes: qtWeightRaw === '' ? '' : window.QuotationPricing.toNumber(qtWeightRaw) / 1000,
    stops: (eplRoutes || []).find(route => route.id === routeId)?.stop_count,
    currency,
  });

  renderCostBreakdown('qt-cost-breakdown', quote, 'qt-currency');

  // Bốn ô ẩn vẫn là nơi các chỗ khác đọc số. Chưa tính được thì để TRỐNG, không
  // ghi 0 — số 0 sẽ chảy tiếp vào đơn vận chuyển như thể đó là giá đã chốt.
  const byKey = Object.fromEntries((quote.rows || []).map(row => [row.key, row.amount]));
  const write = (id, amount) => {
    const input = document.getElementById(id);
    if (!input) return;
    if (!quote.ready) {
      input.value = '';
      delete input.dataset.vndValue;
      return;
    }
    setWorkflowCostField(id, amount, currency);
  };
  write('qt-fuel', byKey.fuel || 0);
  write('qt-driver', byKey.driver || 0);
  write('qt-toll', byKey.toll || 0);

  // Ô "giá bán" nhận CưỚC THU KHÁCH, không phải tổng đại số của mọi cấu phần.
  // Trước đây nó nhận cả chi phí cộng doanh thu, nên con số chảy tiếp vào đơn
  // vận chuyển và hóa đơn đều cao hơn giá thật.
  const total = document.getElementById('qt-selling-price');
  if (total) {
    if (quote.ready) setWorkflowTotalField('qt-selling-price', quote.revenue, currency);
    else { total.value = ''; delete total.dataset.vndValue; }
  }

  if (quote.ready) {
    setStatus(`Đã áp dụng công thức "${quote.formulaName || quote.formulaKey}"`, 'ok');
  } else {
    setStatus('Chưa đủ dữ liệu để áp công thức', 'warn');
  }
  lastQuotationQuote = quote;
  return quote;
};

/**
 * Chi phí chuyến của đơn vận chuyển, theo đúng công thức đã cấu hình.
 *
 * Trước đây màn này tính tiền bằng `số km × 6250 + 800000` ngay trong hàm đổi
 * tuyến. Hai con số đó không có nguồn nào, không dính gì đến công thức trong Dữ
 * liệu gốc, và mỗi lần đổi tuyến là đơn giá đã chốt bên báo giá bị xóa mất mà
 * không một lời nào.
 *
 * Nay dùng chung js/quotation-pricing.js với màn báo giá: công thức của loại xe
 * trên đơn, số km của tuyến đang chọn, và tải trọng THỰC TẾ của đơn — ô tải
 * trọng ở đây tính bằng kg nên phải quy về tấn.
 */
let newRouteCounter = 1; // Will be updated dynamically from API

window.createNewRouteForm = async function () {
  // Get the real next route number from API
  try {
    const routes = await fetchAllPaginated(`${API_BASE}/api/routes?paginated=true`);
    newRouteCounter = routes.length + 1;
  } catch (e) { /* use current counter */ }

  const paddedNum = String(newRouteCounter).padStart(3, '0');
  const nextCode = `RT-${paddedNum}`;
  newRouteCounter++;

  const codeInput = document.getElementById('md-route-code');
  const nameInput = document.getElementById('md-route-name');

  if (codeInput) codeInput.value = nextCode;
  if (nameInput) {
    nameInput.value = '';
    nameInput.placeholder = 'Ví dụ: Kho Cần Thơ ➔ Cảng Cái Mép';
    nameInput.focus();
  }

  const tbody = document.getElementById('route-segments-tbody');
  if (tbody) tbody.innerHTML = '';

  const distEl = document.getElementById('route-total-distance');
  if (distEl) {
    // Ghi CA dataset: luc Luu doc dataset, nen thieu no la Luu con so cua
    // tuyen mo truoc do.
    distEl.dataset.km = '0';
    distEl.innerText = '0 km';
  }

  // Wipe map clean for creating a new route
  if (typeof window.clearLeafletRouteMap === 'function') {
    window.clearLeafletRouteMap();
  }

  showToast(`✨ Đã mở Form tạo Tuyến Đường Mới (${nextCode})! Vui lòng nhập Tên tuyến đường và thêm các chặng.`);
};

/**
 * HIỆN CẢ HAI CON SỐ km cạnh nhau: số người khai và số đường bộ đo được.
 *
 * Vì sao không tự ghi đè số khai bằng số đo. `routes.distance_km` là con số
 * người dùng khai, và nó đang nuôi phép tính giá cước lẫn ETA — thay nó bằng
 * một con số máy lấy về là đổi tiền trên những đơn đã chốt, mà không ai bấm
 * đồng ý. Nên máy chỉ NÓI RA chênh lệch; quyết định là của người dùng.
 *
 * Ngưỡng 5%: dưới mức đó thì lệch là chuyện thường (điểm khai là một khu, không
 * phải một cổng), và tô đỏ mọi tuyến thì cái màu đỏ mất nghĩa.
 */
function veSoKmDuongBo(kmKhai, kmDuongBo) {
  const o = document.getElementById('route-road-distance-box');
  if (!o) return;
  const khai = Number(kmKhai || 0);
  const bo = Number(kmDuongBo || 0);
  if (!bo) {
    // Chưa đo được thì NÓI RA là chưa đo, không hiện một con số 0 — số 0 đọc
    // ra như "tuyến này dài 0 km".
    o.innerHTML = '<small style="color:#94a3b8; font-weight:600;">chưa đo được đường bộ thật</small>';
    o.hidden = false;
    return;
  }
  const lech = bo - khai;
  const phanTram = khai > 0 ? Math.abs(lech) / khai * 100 : 0;
  const dang = phanTram >= 5;
  const mau = dang ? '#b45309' : '#15803d';
  const nen = dang ? '#fff4e0' : '#e7f6ec';
  const dau = lech > 0 ? '+' : '';
  o.innerHTML = `
    <span>Đường bộ đo được: <strong style="color:${mau}; font-size:1rem;">${bo.toLocaleString('vi-VN')} km</strong></span>
    <span style="background:${nen}; color:${mau}; border-radius:6px; padding:2px 8px; font-weight:800; font-size:0.76rem; white-space:nowrap;"
      title="${dang ? 'Lệch trên 5% so với số khai — nên soát lại' : 'Lệch dưới 5%, trong khoảng bình thường'}"
      >${dau}${lech.toLocaleString('vi-VN', { maximumFractionDigits: 1 })} km · ${phanTram.toLocaleString('vi-VN', { maximumFractionDigits: 1 })}%</span>
    ${dang ? `<button type="button" id="route-dung-km-do" class="fiori-btn fiori-btn-secondary"
        style="padding:3px 9px; font-size:0.74rem;"
        title="Điền ${bo} km vào ô tổng quãng đường. Chưa lưu — bấm 'Hoàn tất & Lưu tuyến đường' mới ghi vào hệ thống."
        data-km="${bo}">Dùng số đo</button>` : ''}`;
  o.hidden = false;
  const nut = document.getElementById('route-dung-km-do');
  if (nut) {
    nut.onclick = () => {
      // KHÔNG tự lưu. Chỉ điền vào ô, và nói rõ điều đó ảnh hưởng tới đâu —
      // người dùng phải bấm Lưu mới ghi vào hệ thống.
      const xuongDong = String.fromCharCode(10);
      if (!window.confirm(`Điền ${bo.toLocaleString('vi-VN')} km vào ô tổng quãng đường?`
        + xuongDong + xuongDong
        + 'Số này nuôi phép tính giá cước và ETA của những đơn TẠO SAU khi lưu.'
        + xuongDong
        + 'Chưa lưu ngay — bấm "Hoàn tất & Lưu tuyến đường" mới ghi vào hệ thống.'
        + xuongDong + xuongDong
        // Nói ra chỗ này chứ không để người dùng tự phát hiện: km của TỪNG
        // CHẶNG vẫn là số cũ, nên hàm tính tổng sẽ ghi đè lại nếu họ sửa một
        // chặng. Không nói thì họ tưởng đã lưu số đo rồi mà nó lặng lẽ mất.
        + 'Lưu ý: km của từng chặng vẫn giữ số cũ. Nếu sửa một chặng thì tổng sẽ '
        + 'tính lại theo các chặng và mất số đo này.')) return;
      const distEl = document.getElementById('route-total-distance');
      if (distEl) {
        distEl.dataset.km = String(bo);
        distEl.innerText = `${bo.toLocaleString('vi-VN')} km`;
      }
      showToast(`Đã điền ${bo.toLocaleString('vi-VN')} km. Bấm "Hoàn tất & Lưu tuyến đường" để ghi vào hệ thống.`);
      veSoKmDuongBo(bo, bo);
    };
  }
}
window.veSoKmDuongBo = veSoKmDuongBo;

window.loadSavedRoutePreset = async function (code) {
  if (!code) return;

  // Try to find route in already-loaded eplRoutes (from API)
  let apiRoute = (eplRoutes || []).find(r => r.id === code);

  // If not found, fetch from API directly
  if (!apiRoute) {
    try {
      eplRoutes = await fetchAllPaginated(`${API_BASE}/api/routes?paginated=true`);
      apiRoute = eplRoutes.find(r => r.id === code);
    } catch (e) { console.error(e); }
  }

  if (apiRoute) {
    // Use real API data
    if (document.getElementById('md-route-code')) document.getElementById('md-route-code').value = apiRoute.id;
    if (document.getElementById('md-route-name')) document.getElementById('md-route-name').value = apiRoute.name;
    const distEl = document.getElementById('route-total-distance');
    if (distEl) {
      // Ghi CA dataset: luc Luu doc dataset, nen thieu no la Luu con so cua
      // tuyen mo truoc do.
      distEl.dataset.km = String(Number(apiRoute.distance_km || 0));
      distEl.innerText = `${Number(apiRoute.distance_km || 0).toLocaleString('vi-VN')} km`;
    }
    veSoKmDuongBo(apiRoute.distance_km, apiRoute.km_duong_bo);

    // Parse segments from segments_json if available
    let segments = [];
    const tbody = document.getElementById('route-segments-tbody');
    if (tbody) {
      try {
        const raw = JSON.parse(apiRoute.segments_json || '[]');
        if (Array.isArray(raw) && raw.length > 0) {
          if (typeof raw[0] === 'string') {
            segments = [];
            showToast('Tuyến cũ chưa có khoảng cách từng chặng được kiểm chứng. Vui lòng cấu hình lại trong Master Data.');
          } else {
            segments = raw;
          }
        }
      } catch (e) { segments = []; }

      if (segments.length > 0) {
        tbody.innerHTML = segments.map(s => {
          let km = parseFloat(s.distance_km ?? s.dist_km ?? s.distance ?? s.km ?? 0) || 0;
          const kmText = Number(km.toFixed(1)).toLocaleString('vi-VN');
          return `
            <tr style="border-bottom: 1px solid #f1f5f9;">
              <td style="padding: 12px 16px; color: #1e293b; font-weight: 600;">${s.from || s.origin || ''}</td>
              <td style="padding: 12px 16px; color: #1e293b; font-weight: 600;">${s.to || s.destination || ''}</td>
              <td style="padding: 12px 16px; font-weight: 700; color: #2563eb;">${kmText} km</td>
              <td style="padding: 12px 16px; text-align: right;">
                <button class="fiori-btn fiori-btn-secondary" style="padding: 4px 10px; font-size: 0.8rem; color: #ef4444; border-color: #fca5a5;" onclick="this.closest('tr').remove(); calculateTotalDistance();"><i class="fa-solid fa-trash"></i></button>
              </td>
            </tr>
          `;
        }).join('');
        tbody.querySelectorAll('tr').forEach((row, index) => {
          row.dataset.segmentJson = JSON.stringify(segments[index]);
        });
        calculateTotalDistance();
      } else {
        tbody.innerHTML = '<tr><td colspan="4" style="padding:12px 16px; color:#94a3b8; text-align:center;">Chưa có chặng đường. Dùng form bên dưới để thêm chặng.</td></tr>';
      }
    }

    // Draw on map using the saved PostgreSQL segments, geocoded to real coordinates.
    if (typeof window.RouteMapUtils?.drawSavedRoute === 'function' && typeof window.initLeafletRouteMap === 'function') {
      const badgeText = document.getElementById('route-map-badge-text');
      if (badgeText) badgeText.innerText = 'Đang xác định tọa độ và vẽ tuyến...';

      // TOẠ ĐỘ DO MÁY CHỦ TRẢ, không do trình duyệt đi hỏi.
      //
      // Trước đây màn này chỉ có một đường: hỏi `nominatim.openstreetmap.org`
      // cho từng điểm, từ trình duyệt người dùng. Đo được trên mạng của dự án:
      // host đó KHÔNG TỚI ĐƯỢC, nên đường này luôn thất bại và ô bản đồ trắng
      // trơn — trong khi màn "Theo dõi và kiểm soát" vẫn vẽ được đúng tuyến đó.
      // Hai màn nói hai điều trái ngược về cùng một tuyến.
      //
      // `/geo` tra ba tầng ở phía máy chủ (bảng địa điểm → bảng mồi → dịch vụ
      // ngoài) và GHI LẠI kết quả, nên tuyến mới với địa điểm mới cũng vẽ được,
      // và lần sau không cần mạng nữa. Nó có thể mất vài giây cho một địa điểm
      // chưa ai biết — chấp nhận được, vì người dùng đang đợi một bản đồ.
      let changCoToaDo = Array.isArray(apiRoute.segments_geo) && apiRoute.segments_geo.length
        ? apiRoute.segments_geo
        : segments;
      let diemThieu = apiRoute.diem_thieu_toa_do || [];
      // HÌNH ĐƯỜNG BỘ THẬT, cũng do máy chủ trả. Lấy từ `/geo` chứ không chỉ từ
      // danh sách: danh sách chỉ trả bản ĐÃ LƯU, còn `/geo` lấy mới cho tuyến
      // chưa từng mở — nên tuyến mới cũng có hình đường bộ ngay lần đầu xem.
      let duongBo = apiRoute.duong_bo || null;
      try {
        const traGeo = await fetch(`${API_BASE}/api/routes/${encodeURIComponent(apiRoute.id)}/geo`);
        if (traGeo.ok) {
          const goi = await traGeo.json();
          const duLieu = (goi && goi.data) || {};
          if (Array.isArray(duLieu.segments_geo) && duLieu.segments_geo.length) {
            changCoToaDo = duLieu.segments_geo;
            diemThieu = duLieu.diem_thieu_toa_do || [];
          }
          if (Array.isArray(duLieu.duong_bo) && duLieu.duong_bo.length >= 2) {
            duongBo = duLieu.duong_bo;
            // Ghi lại vào bản trong bộ nhớ để lần mở sau không phải gọi lại.
            apiRoute.duong_bo = duLieu.duong_bo;
            apiRoute.km_duong_bo = duLieu.km_duong_bo;
            // `/geo` co the vua DO XONG mot tuyen chua tung mo, nen ve lai o
            // so sanh — khong ve lai thi no con hien "chua do duoc".
            veSoKmDuongBo(apiRoute.distance_km, duLieu.km_duong_bo);
          }
        }
      } catch (e) {
        // Máy chủ không trả được thì vẫn vẽ bằng toạ độ đã có trong danh sách.
      }

      const didDraw = await window.RouteMapUtils.drawSavedRoute(
        { ...apiRoute, segments_json: changCoToaDo, duong_bo: duongBo },
        geocodeRouteLocation,
        window.initLeafletRouteMap
      );

      if (didDraw) {
        // KHÔNG escape ở đây: giá trị đi vào innerText, vốn đã coi nội dung là văn
        // bản thuần. Escape thêm sẽ khiến người dùng nhìn thấy "&amp;" thay vì "&".
        if (badgeText) badgeText.innerText = `${apiRoute.id} - ${apiRoute.name}`;
        if (diemThieu.length) {
          showToast(`Đã vẽ tuyến, nhưng chưa biết toạ độ của: ${diemThieu.join(', ')}. `
            + 'Khai toạ độ cho địa điểm đó ở thẻ Địa điểm để sơ đồ đủ điểm.');
        }
      } else {
        if (typeof window.clearLeafletRouteMap === 'function') window.clearLeafletRouteMap();
        // NÓI RA điểm nào chưa biết toạ độ. "Không xác định được toạ độ tuyến
        // đường" là một câu không hành động được: tuyến có ba chặng thì người
        // dùng không biết phải sửa điểm nào.
        if (badgeText) {
          badgeText.innerText = diemThieu.length
            ? `Chưa biết toạ độ: ${diemThieu.join(', ')}`
            : 'Không xác định được tọa độ tuyến đường';
        }
        showToast(diemThieu.length
          ? `Chưa biết toạ độ của: ${diemThieu.join(', ')}. Khai toạ độ cho địa điểm đó ở thẻ Địa điểm, `
            + 'hoặc sửa tên điểm đi/điểm đến cho rõ hơn (ví dụ thêm tên tỉnh).'
          : 'Không xác định được tọa độ cho tuyến đường này. Vui lòng nhập điểm đi/đến rõ hơn trong Master Data.');
      }
    }
    // KHÔNG escape ở đây: giá trị đi vào showToast (đặt nội dung qua textContent), vốn đã coi nội dung là văn
    // bản thuần. Escape thêm sẽ khiến người dùng nhìn thấy "&amp;" thay vì "&".
    showToast(`📂 Đã tải tuyến đường: ${apiRoute.id} - ${apiRoute.name} (${apiRoute.distance_km || 0} km)`);
  } else {
    showToast(`⚠️ Không tìm thấy tuyến đường ${code} trong CSDL!`);
  }
};

window.cancelNewRouteForm = function () {
  const selectVal = document.getElementById('md-saved-routes-select')?.value;
  if (selectVal) {
    window.loadSavedRoutePreset(selectVal);
  } else {
    resetRoutePlanningForm();
    if (typeof window.clearLeafletRouteMap === 'function') window.clearLeafletRouteMap();
  }
  showToast('Đã hủy thao tác!');
};

// ==========================================
// 🚀 TAB 2 FORMULA VEHICLE TYPE SELECTOR (SIDE-BY-SIDE)
// ==========================================
window.selectFormulaVehicleType = function (presetKey, element, options = {}) {
  const cards = document.querySelectorAll('.veh-type-card');
  cards.forEach(c => {
    c.classList.remove('active');
    c.style.border = '1px solid #e2e8f0';
    c.style.boxShadow = 'none';
  });

  if (element) {
    element.classList.add('active');
    element.style.border = '2px solid #2563eb';
    element.style.boxShadow = '0 2px 6px rgba(10,110,209,0.12)';
  }

  const badge = document.getElementById('selected-veh-type-badge');
  const p = masterFormulaStore[presetKey];
  if (badge) {
    badge.innerText = element?.dataset.vehicleTypeName || p?.vehicleTypeName || p?.name || presetKey;
  }

  const select = document.getElementById('md-formula-preset-select');
  if (select) select.value = presetKey;

  window.loadSelectedFormulaPreset(presetKey, options);
};

// ==========================================
// LIVE CURRENCY EXCHANGER (VNĐ -> USD, THB, LAK)
// ==========================================
window.recalculateCurrencyPreview = function () {
  const parser = window.CurrencyRateUtils;
  if (!parser) return;
  const rawVnd = document.getElementById('calc-vnd-input')?.value || '10,000,000';
  const values = {
    usd: parser.convertVndByRate(rawVnd, document.getElementById('rate-usd')?.value),
    thb: parser.convertVndByRate(rawVnd, document.getElementById('rate-thb')?.value),
    lak: parser.convertVndByRate(rawVnd, document.getElementById('rate-lak')?.value)
  };
  const render = (id, symbol, value) => {
    const element = document.getElementById(id);
    if (element) element.innerText = Number.isFinite(value)
      ? `${symbol} ${value.toLocaleString('vi-VN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
      : 'Tỷ giá không hợp lệ';
  };
  render('conv-usd-val', '$', values.usd);
  render('conv-thb-val', '฿', values.thb);
  render('conv-lak-val', '₭', values.lak);
};

function renderCurrencyReferenceStatus(data, proposalLoaded = false) {
  const status = document.getElementById('currency-reference-status');
  if (!status) return;
  const fetchedAt = data?.fetched_at ? new Date(data.fetched_at).toLocaleString('vi-VN') : '';
  const interval = Number(data?.refresh_interval_hours || 12);
  let message = `Chưa có tỷ giá tham chiếu. Chu kỳ tự động: ${interval} giờ.`;
  let color = '#334155';
  let background = '#eff6ff';
  let border = '#bfdbfe';

  if (data?.status === 'ready') {
    message = `Nguồn Open Exchange Rates${fetchedAt ? ` • cập nhật ${fetchedAt}` : ''} • Tham chiếu chưa áp dụng. Bấm Lưu tỷ giá mới để duyệt.`;
    if (proposalLoaded) message = `Đã nạp số tham chiếu vào biểu mẫu${fetchedAt ? ` lúc ${fetchedAt}` : ''}. Tham chiếu chưa áp dụng.`;
    color = '#166534';
    background = '#f0fdf4';
    border = '#86efac';
  } else if (data?.status === 'error') {
    message = 'Không cập nhật được nguồn tham chiếu. Tỷ giá vận hành hiện tại vẫn được giữ nguyên.';
    color = '#9a3412';
    background = '#fff7ed';
    border = '#fdba74';
  } else if (data?.status === 'not_configured') {
    message = 'Chưa cấu hình API key. Hệ thống đang dùng tỷ giá nhập thủ công; chu kỳ dự kiến là 12 giờ.';
  }

  status.style.color = color;
  status.style.background = background;
  status.style.borderColor = border;
  const label = status.querySelector('span');
  if (label) label.textContent = message;
}

function applyCurrencyReferenceProposal(data) {
  const rates = data?.rates || {};
  const formats = { USD: 2, THB: 4, LAK: 6 };
  for (const code of ['USD', 'THB', 'LAK']) {
    const value = Number(rates[code]);
    const input = document.getElementById(`rate-${code.toLowerCase()}`);
    if (!input || !Number.isFinite(value) || value <= 0) continue;
    input.value = value.toLocaleString('en-US', {
      minimumFractionDigits: 0,
      maximumFractionDigits: formats[code]
    });
    const reference = document.getElementById(`rate-reference-${code.toLowerCase()}`);
    if (reference) {
      reference.textContent = `${window.CurrencyRateUtils.formatCurrencyRateNumber(value)} VNĐ`;
    }
  }
  window.recalculateCurrencyPreview();
}

function renderCurrencyRateHistory(payload, syncInputs = false) {
  const currencies = Array.isArray(payload?.currencies) ? payload.currencies : [];
  const format = window.CurrencyRateUtils.formatCurrencyRateNumber;

  for (const item of currencies) {
    const code = String(item.code || '').toLowerCase();
    const current = document.getElementById(`rate-current-${code}`);
    const previous = document.getElementById(`rate-previous-${code}`);
    const change = document.getElementById(`rate-change-${code}`);
    const input = document.getElementById(`rate-${code}`);

    if (current) {
      current.textContent = item.current_rate == null ? 'Chưa lưu' : `${format(item.current_rate)} VNĐ`;
    }
    if (previous) {
      previous.textContent = item.previous_rate == null ? 'Chưa có' : `${format(item.previous_rate)} VNĐ`;
    }
    if (syncInputs && input) {
      // `current_rate == null` nghĩa là CHƯA AI LƯU tỷ giá cho đồng này. Bản
      // trước chỉ ghi khi có giá trị, nên ô nhập giữ nguyên con số viết cứng
      // trong index.html (25.450 / 710 / 1,18) — nhìn y hệt một tỷ giá đã
      // lưu, trong khi ô "Đang áp dụng" ngay bên cạnh ghi "Chưa lưu".
      input.value = item.current_rate == null ? '' : format(item.current_rate);
    }
    if (change) {
      change.classList.remove('up', 'down');
      if (item.change == null) {
        change.textContent = 'Chưa có biến động';
      } else {
        const direction = item.change > 0 ? 'up' : (item.change < 0 ? 'down' : '');
        const sign = item.change > 0 ? '+' : '';
        if (direction) change.classList.add(direction);
        change.textContent = `${sign}${format(item.change)} VNĐ · ${sign}${Number(item.change_percent || 0).toLocaleString('vi-VN', { maximumFractionDigits: 2 })}% so với lần trước`;
      }
    }
  }

  const body = document.getElementById('currency-rate-history-body');
  if (!body) return;
  const rows = currencies.flatMap(item => (item.history || []).map((row, index) => ({
    ...row,
    code: item.code,
    current: index === 0
  })));
  rows.sort((a, b) => String(b.rate_date || '').localeCompare(String(a.rate_date || '')) || Number(b.current) - Number(a.current));

  body.innerHTML = rows.length
    ? rows.slice(0, 18).map(row => {
      const source = row.source === 'APPROVED_UI'
        ? 'Duyệt trên hệ thống'
        : (row.source === 'PREVIOUS_UI' ? 'Giá trước khi đổi' : (row.source || '-'));
      return `<tr><td><strong>${row.code}</strong></td><td>${format(row.rate)} VNĐ</td><td>${row.rate_date || '-'}</td><td>${source}</td><td>${row.current ? 'Đang áp dụng' : 'Lịch sử'}</td></tr>`;
    }).join('')
    : '<tr><td colspan="5">Chưa có lịch sử tỷ giá.</td></tr>';
}

window.loadCurrencyRateHistory = async function () {
  try {
    const response = await fetch(`${API_BASE}/api/currencies/history`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    renderCurrencyRateHistory(await response.json(), true);
    window.recalculateCurrencyPreview();
  } catch (error) {
    baoNapThatBai('lịch sử tỷ giá', error);
  }
};

window.loadCurrencyReferenceStatus = async function () {
  try {
    const response = await fetch(`${API_BASE}/api/currencies/reference-rates`);
    if (!response.ok) return;
    renderCurrencyReferenceStatus(await response.json());
  } catch (error) {
    baoNapThatBai('trạng thái tỷ giá tham chiếu', error);
  }
};

window.refreshCurrencyReferenceRates = async function () {
  const button = document.getElementById('currency-reference-refresh');
  if (button) button.disabled = true;
  try {
    const response = await fetch(`${API_BASE}/api/currencies/reference-rates/refresh`, { method: 'POST' });
    const payload = await response.json();
    if (!response.ok) {
      renderCurrencyReferenceStatus({ status: response.status === 503 ? 'not_configured' : 'error' });
      const message = payload?.error?.message || payload?.detail?.message || 'Không thể cập nhật tỷ giá tham chiếu.';
      showToast(message);
      return;
    }
    applyCurrencyReferenceProposal(payload);
    renderCurrencyReferenceStatus(payload, true);
    showToast('Đã nạp tỷ giá tham chiếu. Hãy kiểm tra rồi bấm Lưu tỷ giá mới để áp dụng.');
  } catch (error) {
    renderCurrencyReferenceStatus({ status: 'error' });
    showToast('Không thể kết nối nguồn tỷ giá; cấu hình hiện tại không thay đổi.');
  } finally {
    if (button) button.disabled = false;
  }
};

window.saveCurrencyRates = async function () {
  const parseCurrencyRateNumber = window.CurrencyRateUtils.parseCurrencyRateNumber;
  const usd = parseCurrencyRateNumber(document.getElementById('rate-usd')?.value);
  const thb = parseCurrencyRateNumber(document.getElementById('rate-thb')?.value);
  const lak = parseCurrencyRateNumber(document.getElementById('rate-lak')?.value);

  if (![usd, thb, lak].every(value => Number.isFinite(value) && value > 0)) {
    showToast('Tỷ giá USD, THB và LAK phải là số dương hợp lệ. Vui lòng kiểm tra dấu chấm và dấu phẩy.');
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/currencies`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ USD: usd, THB: thb, LAK: lak })
    });
    const payload = await res.json();
    if (res.ok) {
      showToast(`Đã lưu tỷ giá mới vào CSDL (USD: ${usd.toLocaleString('vi-VN')} | THB: ${thb.toLocaleString('vi-VN')} | LAK: ${lak.toLocaleString('vi-VN')})`);
      renderCurrencyRateHistory(payload.data, true);
      if (typeof recalculateCurrencyPreview === 'function') recalculateCurrencyPreview();
    } else {
      showToast(payload?.detail?.message || payload?.error?.message || 'Không thể lưu tỷ giá mới.');
    }
  } catch (e) {
    console.error(e);
    showToast('Không thể kết nối máy chủ để lưu tỷ giá.');
  }
};

// ==========================================
// 🚀 DRIVER & CO-DRIVER MANAGEMENT (100% REST API Persistent)
// ==========================================
let fioriDrivers = [];
let currentEditingDriverRow = null;

function cleanDriverMasterText(value, fallback = '') {
  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
  let raw = String(value || fallback || '');
  if (raw.includes('\uFFFD')) raw = fallback || raw.replace(/\uFFFD/g, '');

  const vi = raw
    .replace(/Tài xế chính/g, 'Lái xe chính')
    .replace(/Ca Sáng/g, 'Ca sáng')
    .replace(/Ca Chiều/g, 'Ca chiều')
    .replace(/Ca Đêm/g, 'Ca đêm');

  if (lang !== 'la') return vi;
  return vi
    .replace(/Lái xe chính|Tài xế chính/g, 'ຄົນຂັບຫຼັກ')
    .replace(/Phụ xe/g, 'ຜູ້ຊ່ວຍຄົນຂັບ')
    .replace(/Lái xe dự phòng/g, 'ຄົນຂັບສຳຮອງ')
    .replace(/Hạng/g, 'ຊັ້ນ')
    .replace(/Chưa gán/g, 'ຍັງບໍ່ໄດ້ມອບໝາຍ')
    .replace(/Rảnh/g, 'ຫວ່າງ')
    .replace(/Sẵn sàng/g, 'ພ້ອມໃຊ້ງານ')
    .replace(/Bận/g, 'ບໍ່ຫວ່າງ')
    .replace(/Đang/g, 'ກຳລັງ')
    .replace(/Ca sáng/g, 'ກະເຊົ້າ')
    .replace(/Ca chiều/g, 'ກະບ່າຍ')
    .replace(/Ca đêm/g, 'ກະກາງຄືນ')
    .replace(/Ca ngày/g, 'ກະກາງເວັນ')
    .replace(/Ca hành chính/g, 'ກະບໍລິຫານ');
}

function cleanDriverStatus(value) {
  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
  const raw = cleanDriverMasterText(value, '');
  const lower = raw.toLowerCase();
  if (isDriverOperationalBusy(raw)) {
    if (lower.includes('đang thực hiện') || lower.includes('đang vận chuyển')) {
      return lang === 'vi' ? `Bận - ${raw}` : raw;
    }
    return lang === 'la' ? 'ບໍ່ຫວ່າງ - ພວມໄປກັບລົດ' : lang === 'en' ? 'Busy - On Trip' : 'Bận - Đang theo xe';
  }
  if (raw.includes('Nghỉ')) {
    return lang === 'la' ? 'ລາພັກ' : lang === 'en' ? 'On Leave' : 'Nghỉ phép';
  }
  const defaultStatus = lang === 'la' ? 'ຫວ່າງ (ພ້ອມໃຊ້ງານ)' : lang === 'en' ? 'Available' : 'Rảnh (Sẵn sàng)';
  return raw || defaultStatus;
}

function isDriverOperationalBusy(value) {
  const lower = cleanDriverMasterText(value, '').toLowerCase();
  return ['bận', 'theo xe', 'đang thực hiện', 'đang vận chuyển'].some(marker => lower.includes(marker));
}

// Nhan MA trang thai (moc 045) hoac ca ban ghi tai xe — khong nhan chuoi nhan.
function setDriverOperationalStatus(value) {
  const display = document.getElementById('drv-status-display');
  const text = document.getElementById('drv-status-text');
  const vehicle = document.getElementById('drv-vehicle');
  const ma = (value && typeof value === 'object')
    ? String(value.operational_status || 'available')
    : String(value || 'available');
  const ref = (value && typeof value === 'object') ? value.operational_ref : null;
  const busy = ma === 'on_trip';
  if (display) display.classList.toggle('is-busy', busy || ma === 'inactive' || ma === 'off_duty');
  if (text) text.textContent = nhanTrangThaiVanHanh('drv', ma, ref);
  if (vehicle) {
    vehicle.disabled = busy;
    vehicle.title = busy ? 'Xe đang do điều phối quản lý; hoàn tất chuyến trước khi đổi xe.' : '';
  }
}
async function loadFioriDrivers() {
  try {
    const res = await fetch(`${API_BASE}/api/drivers`);
    if (!res.ok) return baoLoiMayChu(res, 'Nạp danh sách nhân sự');
    fioriDrivers = await res.json();
    renderFioriDrivers(fioriDrivers);
  } catch (e) {
    return baoMatKetNoi('Nạp danh sách nhân sự', e);
  }
}

function renderFioriDrivers(data) {
  fioriDrivers = Array.isArray(data) ? data : [];
  if (document.getElementById('driver-shift-workbench')) {
    renderDriverShiftPlanner();
    return;
  }
  const tbody = document.getElementById('driver-list-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';

  if (!data || data.length === 0) {
    const emptyMsg = lang === 'la' ? 'ຍັງບໍ່ມີຄົນຂັບ/ຜູ້ຊ່ວຍໃນ CSDL.' : lang === 'en' ? 'No drivers/co-drivers in DB.' : 'Chưa có tài xế/phụ xe nào trong CSDL.';
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:#888; padding:15px;"><i class="fa-solid fa-user-xmark"></i> ${emptyMsg}</td></tr>`;
    return;
  }

  data.forEach(d => {
    // TRANG THAI THEO MA (moc 045). `d.status` chi con la nhan chieu.
    const maTT = String(d.operational_status || 'available');
    const isBusy = maTT === 'on_trip';
    const statusText = escapeHtml(nhanTrangThaiVanHanh('drv', maTT, d.operational_ref));
    const nutTT = maTT === 'available'
      ? `<button class="fiori-btn fiori-btn-secondary" title="${escapeHtml((appTranslations.btn_drv_off_duty || {})[lang] || 'Cho nghỉ phép')}" style="width:32px; height:32px; padding:0; justify-content:center; margin-right:4px;" onclick="datTrangThaiTaiXe('${escapeHtml(d.id)}','off_duty')"><i class="fa-solid fa-umbrella-beach"></i></button>`
      : (maTT === 'off_duty' || maTT === 'inactive'
        ? `<button class="fiori-btn fiori-btn-secondary" title="${escapeHtml((appTranslations.btn_drv_back_available || {})[lang] || 'Đưa lại làm việc')}" style="width:32px; height:32px; padding:0; justify-content:center; margin-right:4px;" onclick="datTrangThaiTaiXe('${escapeHtml(d.id)}','available')"><i class="fa-solid fa-rotate-left"></i></button>`
        : '');
    const driverPhoto = d.photo_url || d.image_url || '';
    const driverAvatar = driverPhoto
      ? `<img src="${driverPhoto}" alt="Ảnh ${escapeHtml(d.name || d.id)}">`
      : `<span class="driver-avatar-fallback"><i class="fa-solid fa-user"></i></span>`;
    const statusBadge = (isBusy || maTT === 'inactive' || maTT === 'off_duty') ?
      `<span class="driver-status-badge driver-status-badge--busy">${statusText}</span>` :
      `<span class="driver-status-badge driver-status-badge--ready">${statusText}</span>`;

    const role = String(d.role || '');
    const isAssistant = role.includes('Phụ') || role.includes('Phụ');
    const roleText = lang === 'la' ? (isAssistant ? 'ຜູ້ຊ່ວຍຄົນຂັບ' : 'ຄົນຂັບຫຼັກ') : (isAssistant ? 'Phụ xe' : 'Lái xe chính');
    const roleBadge = isAssistant ?
      `<span class="driver-role-badge driver-role-badge--assistant">${roleText}</span>` :
      `<span class="driver-role-badge driver-role-badge--main">${roleText}</span>`;

    const fallbackLicense = lang === 'la' ? 'ຊັ້ນ FC' : 'Hạng FC';
    const fallbackAssigned = lang === 'la' ? 'ຍັງບໍ່ໄດ້ມອບໝາຍ' : 'Chưa gán';
    const fallbackShift = lang === 'la' ? 'ກະເຊົ້າ (06:00 - 14:00)' : 'Ca sáng (06:00 - 14:00)';

    const licenseLabel = cleanDriverMasterText(d.license_type, fallbackLicense);
    const assignedVehicle = cleanDriverMasterText(d.assigned_vehicle, fallbackAssigned);
    const shiftLabel = cleanDriverMasterText(d.shift, fallbackShift);

    const editTip = lang === 'la' ? 'ແກ້ໄຂ' : lang === 'en' ? 'Edit' : 'Sửa';
    const delTip = lang === 'la' ? 'ລຶບ' : lang === 'en' ? 'Delete' : 'Xóa';

    tbody.insertAdjacentHTML('beforeend', `
      <tr style="border-bottom: 1px solid #f1f5f9;">
        <td style="padding: 12px 16px; font-weight: 700; color: #0f172a;"><div class="driver-name-cell">${driverAvatar}<strong title="${escapeHtml(d.name || d.id)}">${escapeHtml(d.name || d.id)}</strong></div></td>
        <td style="padding: 12px 16px;">${roleBadge}</td>
        <td style="padding: 12px 16px; font-weight: 700; color: #334155;">${licenseLabel}</td>
        <td style="padding: 12px 16px; color: #64748b;">${d.phone || ''}</td>
        <td style="padding: 12px 16px; font-weight: 700; color: #2563eb;">${assignedVehicle}</td>
        <td style="padding: 12px 16px; color: #334155; font-weight: 600;">${shiftLabel}</td>
        <td style="padding: 12px 16px;">${statusBadge}</td>
        <td style="padding: 12px 8px; text-align: center; white-space: nowrap; width:132px;">
          ${nutTT}<button class="fiori-btn fiori-btn-secondary" title="${editTip}" style="width:32px; height:32px; padding:0; justify-content:center; margin-right:4px;" onclick="editDriverById('${escapeJsAttr(d.id || d.name)}')"><i class="fa-solid fa-pen-to-square"></i></button>
          <button class="fiori-btn" title="${delTip}" style="width:32px; height:32px; padding:0; justify-content:center; background:#ef4444; border-color:#ef4444;" onclick="deleteDriverRow('${escapeJsAttr(d.id || d.name)}')"><i class="fa-solid fa-trash"></i></button>
        </td>
      </tr>
    `);
  });
}

let driverShiftWeekStart = null;
let driverShifts = [];
let driverVehicleAvailability = [];
let driverShiftVehicles = [];
// Kỳ bảo dưỡng có giao với tuần đang xem. Ô nào của lưới lịch xe trùng một kỳ
// thì phải kẻ sọc, để người xếp lịch không điều một xe đang nằm bãi đi chạy.
let driverVehicleMaintenance = [];
let selectedDriverForShiftId = '';
let selectedDriverShiftId = '';
let selectedDriverTripScheduleId = '';
let selectedDriverShiftDay = '';
let selectedDriverShiftType = 'morning';
let driverShiftTablePage = 1;
const DRIVER_SHIFT_PAGE_SIZE = 25;
let driverShiftTableSearch = '';
let driverShiftTableRole = '';
let driverShiftSearchTimer = null;
// Góc nhìn của bảng xếp ca: 'week' (ma trận người × ngày) hoặc 'day'.
// Thay cho driverShiftDayDialogOpen: chi tiết ngày giờ hiện NGAY TRONG
// TRANG, không còn hộp thoại che kín màn hình.
let driverRosterView = 'week';
// Chi dung mot trang nhan su moi lan: moi nguoi chiem 21 o (7 ngay x 3 ca).
let driverShiftVisibleCount = 50;
let driverShiftGapsOpen = false;
// Nhóm lọc nhanh đang chọn: 'all' | 'need' | 'over' | 'leave'. Khai bằng `let`
// ở cấp cao nhất — gán thẳng `driverShiftChip = ...` mà không khai thì lần ĐỌC
// đầu tiên là ReferenceError, và lỗi đó làm cả hàm vẽ dừng giữa.
let driverShiftChip = 'all';
let selectedDriverVehicleDay = '';
let driverVehicleTableSearch = '';
let driverVehicleTableStatus = '';
let driverVehicleTableType = '';
let driverVehicleTableDepot = '';
// Chi dung mot trang xe moi lan. Xem js/driver-roster.js de biet vi sao.
let driverVehicleVisibleCount = 50;
let driverVehicleExceptionsOpen = false;
let driverVehicleSearchTimer = null;

function startOfDriverShiftWeek(value = new Date()) {
  const date = new Date(value);
  date.setHours(0, 0, 0, 0);
  const day = date.getDay() || 7;
  date.setDate(date.getDate() - day + 1);
  return date;
}

function driverShiftDateKey(value) {
  const date = new Date(value);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function driverShiftWeekRange() {
  if (!driverShiftWeekStart) driverShiftWeekStart = startOfDriverShiftWeek();
  const end = new Date(driverShiftWeekStart);
  end.setDate(end.getDate() + 7);
  return { start: driverShiftWeekStart.toISOString(), end: end.toISOString() };
}

async function driverShiftApiJson(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...financeAuthHeaders(),
      ...(options.headers || {})
    }
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail || payload.message || {};
    const error = new Error(detail.message || detail.detail || detail || `Không thể cập nhật lịch làm việc (HTTP ${response.status}).`);
    error.status = response.status;
    throw error;
  }
  return payload.data !== undefined ? payload.data : payload;
}

window.loadDriverShiftPlanner = async function () {
  const range = driverShiftWeekRange();
  const query = `start=${encodeURIComponent(range.start)}&end=${encodeURIComponent(range.end)}`;
  // Lời gọi thứ năm KHÔNG trùng lời gọi thứ tư, dù cả hai nói về bảo dưỡng.
  //
  // `vehicle-availability` chỉ trả về kỳ bảo dưỡng đã `approved` hoặc
  // `in_progress` — đúng, vì chỉ hai trạng thái đó mới CHẶN điều phối. Nhưng
  // như vậy một kỳ mới ở trạng thái `requested` là vô hình với người xếp lịch:
  // họ xếp chuyến vào đúng ngày mà thợ đã xin xe, rồi kỳ đó được duyệt và
  // chuyến vỡ.
  //
  // Nên lấy thêm bằng đường theo KHOẢNG THỜI GIAN để nhắc các kỳ chưa duyệt ở
  // khung việc cần xử lý. Một lời gọi cho cả tuần, không phải một lời gọi mỗi
  // xe — đường theo từng xe không dùng được ở quy mô ~500 xe.
  const results = await Promise.allSettled([
      driverShiftApiJson('/api/drivers'),
      fetchAllPaginated(`${API_BASE}/api/vehicles?paginated=true`, 200),
      driverShiftApiJson(`/api/tms/scheduling/driver-shifts?${query}`),
      driverShiftApiJson(`/api/tms/scheduling/vehicle-availability?${query}`),
      driverShiftApiJson(`/api/vehicle-maintenance-requests?${query}`)
  ]);
  const currentValues = [fioriDrivers, driverShiftVehicles, driverShifts,
    driverVehicleAvailability, driverVehicleMaintenance];
  const values = results.map((result, index) => result.status === 'fulfilled' && Array.isArray(result.value) ? result.value : currentValues[index]);
  [fioriDrivers, driverShiftVehicles, driverShifts, driverVehicleAvailability,
    driverVehicleMaintenance] = values;
  if (typeof appState === 'object' && appState) {
    appState.drivers = fioriDrivers;
    appState.vehicles = driverShiftVehicles;
    appState.driver_shifts = driverShifts;
    appState.vehicle_availability = driverVehicleAvailability;
    appState.vehicle_maintenance = driverVehicleMaintenance;
  }
  renderDriverShiftPlanner();
  const failures = results.filter(result => result.status === 'rejected');
  if (failures.length) {
    console.error('Some driver shift planner data failed to load', failures.map(item => item.reason));
    showToast(`Đã tải dữ liệu hiện có. ${failures.length} nguồn lịch chưa phản hồi.`);
  }
};

window.moveDriverShiftWeek = function (days) {
  driverShiftWeekStart = days === 0 ? startOfDriverShiftWeek() : new Date(driverShiftWeekStart || startOfDriverShiftWeek());
  if (days !== 0) driverShiftWeekStart.setDate(driverShiftWeekStart.getDate() + Number(days || 0));
  selectedDriverShiftId = '';
  selectedDriverTripScheduleId = '';
  loadDriverShiftPlanner();
};

window.switchDriverShiftTab = function (name, button) {
  ['drivers', 'vehicles', 'alerts'].forEach(key => {
    document.getElementById(`driver-shift-pane-${key}`)?.toggleAttribute('hidden', key !== name);
    document.getElementById(`driver-shift-tab-${key}`)?.classList.toggle('active', key === name);
  });
  if (button) button.classList.add('active');
};

window.selectDriverForShift = function (driverId) {
  selectedDriverForShiftId = String(driverId || '');
  renderDriverShiftPlanner();
};

window.onDriverShiftDragStart = function (event, driverId) {
  selectedDriverForShiftId = String(driverId || '');
  event.dataTransfer.effectAllowed = 'copy';
  event.dataTransfer.setData('text/driver-id', selectedDriverForShiftId);
};

window.onDriverShiftDragOver = function (event) {
  event.preventDefault();
  event.currentTarget.classList.add('drag-over');
};

window.onDriverShiftDragLeave = function (event) {
  event.currentTarget.classList.remove('drag-over');
};

window.onDriverShiftDrop = async function (event, dateKey, shiftType) {
  event.preventDefault();
  event.currentTarget.classList.remove('drag-over');
  const driverId = event.dataTransfer.getData('text/driver-id') || selectedDriverForShiftId;
  await assignDriverToShiftSlot(driverId, dateKey, shiftType);
};

window.assignSelectedDriverToShift = async function (dateKey, shiftType) {
  if (!selectedDriverForShiftId) {
    showToast('Chọn một tài xế ở danh sách bên trái trước.');
    return;
  }
  await assignDriverToShiftSlot(selectedDriverForShiftId, dateKey, shiftType);
};

function driverShiftHours(dateKey, shiftType) {
  const hours = {
    morning: [6, 14, 0],
    afternoon: [14, 22, 0],
    night: [22, 6, 1]
  }[shiftType] || [8, 17, 0];
  const start = new Date(`${dateKey}T00:00:00`);
  start.setHours(hours[0], 0, 0, 0);
  const end = new Date(`${dateKey}T00:00:00`);
  end.setDate(end.getDate() + hours[2]);
  end.setHours(hours[1], 0, 0, 0);
  return { start, end };
}

async function assignDriverToShiftSlot(driverId, dateKey, shiftType) {
  if (!driverId) return;
  const period = driverShiftHours(dateKey, shiftType);
  const id = `SHIFT-${driverId}-${dateKey.replaceAll('-', '')}-${shiftType.toUpperCase()}-${Date.now().toString().slice(-5)}`;
  try {
    const saved = await driverShiftApiJson('/api/tms/scheduling/driver-shifts', {
      method: 'POST',
      body: JSON.stringify({
        id,
        driver_id: driverId,
        shift_type: shiftType,
        shift_start: period.start.toISOString(),
        shift_end: period.end.toISOString(),
        availability_kind: 'work',
        status: 'planned'
      })
    });
    selectedDriverShiftId = saved.id;
    await loadDriverShiftPlanner();
    showToast('Đã lưu ca làm việc vào hệ thống.');
  } catch (error) {
    showToast(error.message, 'error');
  }
}

window.openDriverShiftQuickForm = function (driverId, dateKey) {
  const driver = fioriDrivers.find(item => String(item.id) === String(driverId));
  if (!driver) return;
  document.getElementById('driver-shift-quick-dialog')?.remove();
  const vehicleOptions = driverShiftVehicles.map(vehicle => `<option value="${completionEscape(vehicle.id)}">${completionEscape(vehicle.id)} · ${completionEscape(vehicle.type || vehicle.brand || '')}</option>`).join('');
  const overlay = document.createElement('div');
  overlay.id = 'driver-shift-quick-dialog';
  overlay.className = 'shift-quick-overlay';
  overlay.onclick = event => { if (event.target === overlay) closeDriverShiftQuickForm(); };
  overlay.innerHTML = `<section class="shift-quick-dialog" role="dialog" aria-modal="true" aria-labelledby="shift-quick-title">
    <header><div><h3 id="shift-quick-title"><i class="fa-solid fa-calendar-plus"></i> Xếp ca cho ${completionEscape(driver.name || driver.id)}</h3><p>${completionEscape(driver.id)} · ${completionEscape(dateKey)}</p></div><button type="button" title="Đóng" onclick="closeDriverShiftQuickForm()"><i class="fa-solid fa-xmark"></i></button></header>
    <div class="shift-quick-body">
      <div class="shift-quick-types" role="group" aria-label="Chọn ca làm việc">
        <button type="button" class="active" data-shift-type="morning" onclick="selectDriverShiftQuickType(this,'morning')"><i class="fa-regular fa-sun"></i><b>Ca sáng</b><small>06:00 - 14:00</small></button>
        <button type="button" data-shift-type="afternoon" onclick="selectDriverShiftQuickType(this,'afternoon')"><i class="fa-solid fa-cloud-sun"></i><b>Ca chiều</b><small>14:00 - 22:00</small></button>
        <button type="button" data-shift-type="night" onclick="selectDriverShiftQuickType(this,'night')"><i class="fa-regular fa-moon"></i><b>Ca đêm</b><small>22:00 - 06:00</small></button>
      </div>
      <input id="shift-quick-driver" type="hidden" value="${completionEscape(driverId)}"><input id="shift-quick-date" type="hidden" value="${completionEscape(dateKey)}"><input id="shift-quick-type" type="hidden" value="morning">
      <label>Xe dự kiến <small>(không bắt buộc)</small><select id="shift-quick-vehicle"><option value="">Chưa gán xe</option>${vehicleOptions}</select></label>
      <label>Địa điểm làm việc<input id="shift-quick-location" placeholder="Kho, bãi hoặc điểm tập kết"></label>
    </div>
    <footer><button type="button" class="fiori-btn fiori-btn-secondary" onclick="closeDriverShiftQuickForm()">Hủy</button><button id="shift-quick-save" type="button" class="fiori-btn" onclick="saveDriverShiftQuickForm()"><i class="fa-solid fa-floppy-disk"></i> Lưu ca</button></footer>
  </section>`;
  document.body.appendChild(overlay);
};

window.closeDriverShiftQuickForm = function () { document.getElementById('driver-shift-quick-dialog')?.remove(); };
window.selectDriverShiftQuickType = function (button, shiftType) {
  document.querySelectorAll('.shift-quick-types button').forEach(item => item.classList.toggle('active', item === button));
  const input = document.getElementById('shift-quick-type');
  if (input) input.value = shiftType;
};
window.saveDriverShiftQuickForm = async function () {
  const driverId = document.getElementById('shift-quick-driver')?.value || '';
  const dateKey = document.getElementById('shift-quick-date')?.value || '';
  const shiftType = document.getElementById('shift-quick-type')?.value || 'morning';
  const period = driverShiftHours(dateKey, shiftType);
  const button = document.getElementById('shift-quick-save');
  if (button) button.disabled = true;
  try {
    await driverShiftApiJson('/api/tms/scheduling/driver-shifts', { method: 'POST', body: JSON.stringify({
      id: `SHIFT-${driverId}-${dateKey.replaceAll('-', '')}-${shiftType.toUpperCase()}-${Date.now().toString().slice(-5)}`,
      driver_id: driverId, vehicle_id: document.getElementById('shift-quick-vehicle')?.value || null,
      shift_type: shiftType, shift_start: period.start.toISOString(), shift_end: period.end.toISOString(),
      availability_kind: 'work', work_location: document.getElementById('shift-quick-location')?.value || null, status: 'planned'
    }) });
    closeDriverShiftQuickForm();
    await loadDriverShiftPlanner();
    showToast('Đã lưu ca làm việc và cập nhật lịch nhân sự.', 'success');
  } catch (error) {
    showToast(error.message, 'error');
    if (button) button.disabled = false;
  }
};

window.openDriverShiftInspector = function (shiftId) {
  selectedDriverShiftId = String(shiftId || '');
  selectedDriverTripScheduleId = '';
  renderDriverShiftInspector();
};

function driverTripScheduleEntries() {
  return driverVehicleAvailability.flatMap(trip => [
    trip.driver_id ? { ...trip, crew_driver_id: trip.driver_id, crew_role: 'Tài xế chính' } : null,
    trip.co_driver_id ? { ...trip, crew_driver_id: trip.co_driver_id, crew_role: 'Phụ xe' } : null
  ].filter(Boolean));
}

window.openDriverTripScheduleInspector = function (tripId, driverId) {
  selectedDriverShiftId = '';
  selectedDriverTripScheduleId = `${String(tripId || '')}::${String(driverId || '')}`;
  renderDriverShiftInspector();
};

window.deleteDriverShiftById = async function (shiftId, event) {
  event?.stopPropagation?.();
  selectedDriverShiftId = String(shiftId || '');
  selectedDriverTripScheduleId = '';
  await deleteSelectedDriverShift();
};

window.toggleDriverShiftVehicle = function (enabled) {
  const select = document.getElementById('driver-shift-edit-vehicle');
  const kind = document.getElementById('driver-shift-edit-availability')?.value || 'work';
  if (select) select.disabled = !enabled || kind !== 'work';
};

window.saveDriverShiftInspector = async function () {
  const shift = driverShifts.find(item => String(item.id) === selectedDriverShiftId);
  if (!shift) return;
  const start = document.getElementById('driver-shift-edit-start')?.value;
  const end = document.getElementById('driver-shift-edit-end')?.value;
  const useVehicle = document.getElementById('driver-shift-use-vehicle')?.checked;
  const availabilityKind = document.getElementById('driver-shift-edit-availability')?.value || 'work';
  try {
    await driverShiftApiJson(`/api/tms/scheduling/driver-shifts/${encodeURIComponent(shift.id)}`, {
      method: 'PUT',
      body: JSON.stringify({
        id: shift.id,
        driver_id: shift.driver_id,
        vehicle_id: availabilityKind === 'work' && useVehicle ? (document.getElementById('driver-shift-edit-vehicle')?.value || null) : null,
        trip_id: shift.trip_id || null,
        shift_type: document.getElementById('driver-shift-edit-type')?.value || shift.shift_type,
        availability_kind: availabilityKind,
        shift_start: new Date(start).toISOString(),
        shift_end: new Date(end).toISOString(),
        work_location: document.getElementById('driver-shift-edit-location')?.value || null,
        notes: document.getElementById('driver-shift-edit-notes')?.value || null,
        status: shift.status || 'planned',
        expected_version: shift.version
      })
    });
    await loadDriverShiftPlanner();
    showToast('Đã cập nhật ca và xe được gán.');
  } catch (error) {
    showToast(error.message, 'error');
  }
};

window.deleteSelectedDriverShift = async function () {
  const shift = driverShifts.find(item => String(item.id) === selectedDriverShiftId);
  if (!shift || !confirm('Hủy ca làm việc này?')) return;
  try {
    await driverShiftApiJson(`/api/tms/scheduling/driver-shifts/${encodeURIComponent(shift.id)}`, { method: 'DELETE' });
    selectedDriverShiftId = '';
    await loadDriverShiftPlanner();
    showToast('Đã hủy ca làm việc trong hệ thống.');
  } catch (error) {
    showToast(error.message, 'error');
  }
};

function renderDriverShiftRoster() {
  const list = document.getElementById('driver-shift-roster-list');
  if (!list) return;
  const keyword = String(document.getElementById('driver-shift-search')?.value || '').trim().toLowerCase();
  const rows = fioriDrivers.filter(driver => `${driver.id} ${escapeHtml(driver.name)} ${driver.license_type}`.toLowerCase().includes(keyword));
  const count = document.getElementById('driver-shift-roster-count');
  if (count) count.textContent = String(rows.length);
  list.innerHTML = rows.map(driver => {
    const initials = String(driver.name || driver.id || '?').split(/\s+/).slice(-2).map(part => part[0]).join('').toUpperCase();
    return `<button type="button" class="driver-roster-card ${String(driver.id) === selectedDriverForShiftId ? 'selected' : ''}" draggable="true" ondragstart="onDriverShiftDragStart(event, '${completionEscape(driver.id)}')" onclick="selectDriverForShift('${completionEscape(driver.id)}')">
      <span class="driver-roster-avatar">${completionEscape(initials)}</span>
      <span><b>${completionEscape(driver.name || driver.id)}</b><small>${completionEscape(driver.license_type || '')} · ${completionEscape(cleanDriverStatus(driver.status))}</small></span>
      <span class="driver-profile-button" role="button" title="Xem hồ sơ" onclick="event.stopPropagation(); editDriverById('${completionEscape(driver.id)}')"><i class="fa-solid fa-eye"></i></span>
    </button>`;
  }).join('') || '<div class="driver-shift-empty-inspector">Không tìm thấy tài xế.</div>';
}

function renderDriverShiftCalendar() {
  const host = document.getElementById('driver-shift-calendar');
  if (!host || !window.TmsCockpit?.buildDriverShiftPlanner) return;
  const planner = window.TmsCockpit.buildDriverShiftPlanner({ drivers: fioriDrivers, vehicles: driverShiftVehicles, driver_shifts: driverShifts, vehicle_availability: driverVehicleAvailability }, driverShiftWeekStart);
  const types = [
    { key: 'morning', label: 'Ca sáng', time: '06:00 - 14:00' },
    { key: 'afternoon', label: 'Ca chiều', time: '14:00 - 22:00' },
    { key: 'night', label: 'Ca đêm', time: '22:00 - 06:00' }
  ];
  const head = `<div class="driver-calendar-corner">Ca / ngày</div>${planner.days.map(day => `<div class="driver-calendar-day"><span>${completionEscape(day.label)}</span><b>${completionEscape(day.key.slice(8))}</b></div>`).join('')}`;
  const body = types.map(type => {
    const cells = planner.days.map(day => {
      const shifts = driverShifts.filter(item => {
        if (driverShiftDateKey(item.shift_start) !== day.key) return false;
        if (item.shift_type === type.key) return true;
        if (item.shift_type !== 'custom') return false;
        const hour = new Date(item.shift_start).getHours();
        const displayType = hour >= 22 || hour < 6 ? 'night' : hour >= 14 ? 'afternoon' : 'morning';
        return displayType === type.key;
      });
      const period = driverShiftHours(day.key, type.key);
      const tripEntries = driverTripScheduleEntries().filter(item => {
        const start = new Date(item.planned_departure_at);
        const end = new Date(item.available_at_origin || item.available_at_destination || item.planned_arrival_at || item.planned_departure_at);
        return Number.isFinite(start.getTime()) && Number.isFinite(end.getTime()) && start < period.end && end > period.start;
      });
      return `<div class="driver-shift-slot" ondragover="onDriverShiftDragOver(event)" ondragleave="onDriverShiftDragLeave(event)" ondrop="onDriverShiftDrop(event, '${day.key}', '${type.key}')" onclick="assignSelectedDriverToShift('${day.key}', '${type.key}')">
        ${shifts.map(shift => {
          const driver = fioriDrivers.find(item => String(item.id) === String(shift.driver_id));
          const availabilityLabels = { work: 'Làm việc', leave: 'Nghỉ phép', sick: 'Nghỉ bệnh', off: 'Nghỉ ca', unavailable: 'Không sẵn sàng' };
          const kind = shift.availability_kind || 'work';
          return `<div class="driver-shift-card ${shift.vehicle_id ? 'vehicle-assigned' : ''} ${kind !== 'work' ? 'driver-shift-card--absence' : ''}" onclick="event.stopPropagation(); openDriverShiftInspector('${completionEscape(shift.id)}')"><div class="driver-shift-card-heading"><b>${completionEscape(driver?.name || shift.driver_id)}</b><span class="driver-shift-card-actions"><button type="button" title="Sửa ca" onclick="event.stopPropagation(); openDriverShiftInspector('${completionEscape(shift.id)}')"><i class="fa-solid fa-pen"></i></button><button type="button" title="Xóa ca" onclick="deleteDriverShiftById('${completionEscape(shift.id)}', event)"><i class="fa-solid fa-trash"></i></button></span></div><span>${new Date(shift.shift_start).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })} - ${new Date(shift.shift_end).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}</span><em>${kind !== 'work' ? availabilityLabels[kind] : shift.vehicle_id ? `Xe ${completionEscape(shift.vehicle_id)}` : 'Làm việc · chưa gán xe'}</em></div>`;
        }).join('')}${tripEntries.map(item => {
          const driver = fioriDrivers.find(row => String(row.id) === String(item.crew_driver_id));
          const end = item.available_at_origin || item.available_at_destination || item.planned_arrival_at;
          return `<div class="driver-shift-card driver-shift-card--trip" onclick="event.stopPropagation(); openDriverTripScheduleInspector('${completionEscape(item.trip_id)}', '${completionEscape(item.crew_driver_id)}')"><div class="driver-shift-card-heading"><b>${completionEscape(driver?.name || item.crew_driver_id)}</b><i class="fa-solid fa-lock" title="Lịch được khóa từ Điều phối"></i></div><span>Trip ${completionEscape(item.trip_id)} · ${completionEscape(item.crew_role)}</span><span>${new Date(item.planned_departure_at).toLocaleString('vi-VN')} → ${end ? new Date(end).toLocaleString('vi-VN') : 'chưa có giờ rảnh'}</span><em>Xe ${completionEscape(item.vehicle_id || 'chưa gán')} · Khóa lịch thật</em></div>`;
        }).join('') || (!shifts.length ? '<div class="driver-shift-slot-empty">Kéo tài xế vào đây<br>hoặc chạm để xếp ca</div>' : '')}
      </div>`;
    }).join('');
    return `<div class="driver-shift-label"><b>${type.label}</b>${type.time}</div>${cells}`;
  }).join('');
  host.innerHTML = `<div class="driver-shift-calendar-grid">${head}${body}</div>`;
}

function localDateTimeInput(value) {
  return FormatUtils.dateTimeInputValue(value);
}

function renderDriverShiftInspector() {
  const host = document.getElementById('driver-shift-inspector-content');
  const inspector = document.getElementById('driver-shift-inspector');
  if (!host) return;
  const shift = driverShifts.find(item => String(item.id) === selectedDriverShiftId);
  const [selectedTripId, selectedTripDriverId] = selectedDriverTripScheduleId.split('::');
  const tripEntry = driverTripScheduleEntries().find(item => String(item.trip_id) === selectedTripId && String(item.crew_driver_id) === selectedTripDriverId);
  if (inspector) inspector.hidden = !shift && !tripEntry;
  if (tripEntry) {
    const driver = fioriDrivers.find(item => String(item.id) === String(tripEntry.crew_driver_id));
    const end = tripEntry.available_at_origin || tripEntry.available_at_destination || tripEntry.planned_arrival_at;
    host.className = 'driver-shift-trip-inspector';
    host.innerHTML = `<div><strong>${completionEscape(driver?.name || tripEntry.crew_driver_id)}</strong><div class="driver-turnaround-meta">${completionEscape(tripEntry.crew_role)} · Trip ${completionEscape(tripEntry.trip_id)}</div></div><div class="driver-shift-trip-facts"><span><b>Xe</b>${completionEscape(tripEntry.vehicle_id || 'Chưa gán')}</span><span><b>Bắt đầu</b>${new Date(tripEntry.planned_departure_at).toLocaleString('vi-VN')}</span><span><b>Rảnh lại</b>${end ? new Date(end).toLocaleString('vi-VN') : 'Chưa xác định'}</span><span><b>Hành trình</b>${completionEscape(tripEntry.origin || '')} → ${completionEscape(tripEntry.destination || '')}</span></div><div class="dispatch-status-note"><i class="fa-solid fa-lock"></i><span>Lịch này sinh từ Điều phối và khóa toàn bộ khoảng chuyến. Muốn đổi xe hoặc nhân sự, hãy cập nhật tại Điều phối.</span></div><button type="button" class="fiori-btn" onclick="switchView('dispatch')"><i class="fa-solid fa-arrow-up-right-from-square"></i> Mở Điều phối</button>`;
    return;
  }
  if (!shift) {
    host.className = 'driver-shift-empty-inspector';
    host.innerHTML = selectedDriverForShiftId ? 'Đã chọn tài xế. Chạm một ô lịch hoặc kéo tài xế vào ca cần xếp.' : 'Chọn tài xế rồi chọn một ô lịch, hoặc mở ca đã có để xem và chỉnh sửa.';
    return;
  }
  const driver = fioriDrivers.find(item => String(item.id) === String(shift.driver_id));
  host.className = 'driver-shift-form';
  host.innerHTML = `<div><strong>${completionEscape(driver?.name || shift.driver_id)}</strong><div class="driver-turnaround-meta">${completionEscape(shift.id)}</div></div>
    <label>Trạng thái lịch<select id="driver-shift-edit-availability" onchange="toggleDriverShiftAvailability(this.value)"><option value="work">Làm việc</option><option value="leave">Nghỉ phép</option><option value="sick">Nghỉ bệnh</option><option value="off">Nghỉ ca</option><option value="unavailable">Không sẵn sàng</option></select></label>
    <label>Loại ca<select id="driver-shift-edit-type"><option value="morning">Ca sáng</option><option value="afternoon">Ca chiều</option><option value="night">Ca đêm</option><option value="custom">Tùy chỉnh</option></select></label>
    <label>Bắt đầu<input id="driver-shift-edit-start" type="datetime-local" value="${localDateTimeInput(shift.shift_start)}"></label>
    <label>Kết thúc<input id="driver-shift-edit-end" type="datetime-local" value="${localDateTimeInput(shift.shift_end)}"></label>
    <label>Địa điểm làm việc<input id="driver-shift-edit-location" value="${completionEscape(shift.work_location || '')}" placeholder="Kho, bãi hoặc điểm giao"></label>
    <div class="driver-shift-toggle"><span>Gán xe cho ca này</span><input id="driver-shift-use-vehicle" type="checkbox" ${shift.vehicle_id ? 'checked' : ''} onchange="toggleDriverShiftVehicle(this.checked)"></div>
    <label>Xe<select id="driver-shift-edit-vehicle" ${shift.vehicle_id ? '' : 'disabled'}><option value="">Chọn xe</option>${driverShiftVehicles.map(vehicle => `<option value="${completionEscape(vehicle.id)}" ${String(vehicle.id) === String(shift.vehicle_id) ? 'selected' : ''}>${completionEscape(vehicle.id)} · ${completionEscape(vehicle.type || '')}</option>`).join('')}</select></label>
    <label>Ghi chú<textarea id="driver-shift-edit-notes" rows="3">${completionEscape(shift.notes || '')}</textarea></label>
    <div class="driver-shift-actions"><button class="fiori-btn" onclick="saveDriverShiftInspector()"><i class="fa-solid fa-floppy-disk"></i> Lưu ca</button><button class="fiori-btn fiori-btn-secondary" title="Hủy ca" onclick="deleteSelectedDriverShift()"><i class="fa-solid fa-trash"></i></button></div>`;
  const typeSelect = document.getElementById('driver-shift-edit-type');
  if (typeSelect) typeSelect.value = shift.shift_type || 'custom';
  const availabilitySelect = document.getElementById('driver-shift-edit-availability');
  if (availabilitySelect) availabilitySelect.value = shift.availability_kind || 'work';
  toggleDriverShiftAvailability(shift.availability_kind || 'work');
}

window.toggleDriverShiftAvailability = function (kind) {
  const canAssignVehicle = kind === 'work';
  const useVehicle = document.getElementById('driver-shift-use-vehicle');
  const vehicleSelect = document.getElementById('driver-shift-edit-vehicle');
  if (useVehicle) {
    useVehicle.disabled = !canAssignVehicle;
    if (!canAssignVehicle) useVehicle.checked = false;
  }
  if (vehicleSelect) vehicleSelect.disabled = !canAssignVehicle || !useVehicle?.checked;
};

/**
 * Gom dữ liệu lịch xe theo hợp đồng của js/driver-roster.js:
 * { days: [{key,label}], vehicles: [{vehicle_id,label,type,days:[...]}] }
 *
 * Bộ lọc áp ở đây (không áp trong module trình bày) để module kia thuần và
 * kiểm chứng được bằng Node.
 */
/**
 * Bai / chi nhanh cua mot xe.
 *
 * O doi 500 xe day la bo loc chinh. Xe chua duoc gan bai thi noi ro la "Chua
 * gan bai" chu khong gop chung vao mot bai nao — gop vao se lam bo loc noi doi.
 */
function depotOf(vehicleId) {
  const vehicle = (fioriVehicles || []).find(item => String(item.id) === String(vehicleId));
  return {
    depot: (vehicle && vehicle.depot) || '',
    code: (vehicle && vehicle.depot_code) || '',
  };
}

function buildDriverVehicleRosterData(planner, options) {
  const ignore = Boolean(options && options.ignoreFilters);
  const keyword = ignore ? '' : driverVehicleTableSearch.trim().toLowerCase();
  const status = ignore ? '' : driverVehicleTableStatus;
  const vehicleType = ignore ? '' : driverVehicleTableType;
  const depot = ignore ? '' : driverVehicleTableDepot;
  const vehicles = planner.vehicle_rows
    .map(row => ({
      vehicle_id: String(row.vehicle_id || ''),
      label: row.label || row.vehicle_id || '',
      type: row.type || '',
      // planner khong mang theo bai, nen tra cuu tu ho so xe day du.
      depot: depotOf(row.vehicle_id).depot,
      depot_code: depotOf(row.vehicle_id).code,
      days: planner.days.map((day, index) => {
        const source = row.days[index] || {};
        const drivers = [...new Set([
          ...(source.timelines || []).flatMap(item => [item.driver_id, item.co_driver_id]),
          ...(source.driver_ids || []),
        ].filter(Boolean))];
        return {
          key: day.key,
          status: source.status || 'available',
          trip_ids: source.trip_ids || [],
          maintenances: source.maintenances || [],
          shifts: source.shifts || [],
          driver_ids: drivers,
        };
      }),
    }))
    .filter(vehicle => {
      const text = `${vehicle.vehicle_id} ${vehicle.label} ${vehicle.type} ${vehicle.days.map(day => `${day.trip_ids.join(' ')} ${day.maintenances.map(item => item.label).join(' ')}`).join(' ')}`.toLowerCase();
      if (keyword && !text.includes(keyword)) return false;
      // Lọc trạng thái theo CẢ TUẦN, không theo một ngày: bảng này là bảng
      // tuần, nên "chỉ xem xe đang bảo dưỡng" phải giữ lại xe có bảo dưỡng ở
      // bất kỳ ngày nào, kèm ngữ cảnh các ngày còn lại.
      if (status && !vehicle.days.some(day => day.status === status)) return false;
      if (vehicleType && vehicle.type !== vehicleType) return false;
      // '__none__' nghia la "chua gan bai" — mot lua chon that, khong phai
      // khong loc gi.
      if (depot === '__none__' && vehicle.depot_code) return false;
      if (depot && depot !== '__none__' && vehicle.depot_code !== depot) return false;
      return true;
    });

  return { days: planner.days.map(day => ({ key: day.key, label: day.label })), vehicles };
}

/**
 * Lịch xe 7 ngày.
 *
 * Thay bản cũ gồm dải 7 nút chỉ hiện số tổng ("3 rảnh · 0 bận") cộng một hộp
 * thoại che kín màn hình cho từng ngày — nhìn vào đó không biết XE NÀO rảnh
 * ngày nào. Nay là ma trận xe × ngày, cùng dạng với bảng xếp ca tài xế.
 */
/**
 * Lich xe 7 ngay, thiet ke cho doi xe LON.
 *
 * Doi thu tu doc man hinh: tinh hinh truoc, viec can xu ly sau, chi tiet sau
 * cung. Ban truoc do la ma tran hien HET moi xe — rat hop ly voi doi vai chuc
 * xe, nhung o 500 xe thi sinh ra khoang 1,7 MB HTML va 3.500 nut trong mot lan
 * innerHTML, va quan trong hon la chon dung 5 xe co van de giua 495 xe binh
 * thuong. Voi 500 xe khong ai cuon het danh sach.
 */
/**
 * Nhắc các kỳ bảo dưỡng CHƯA DUYỆT có giao với tuần đang xem.
 *
 * Lưới lịch xe chỉ kẻ sọc những kỳ đã `approved` / `in_progress`, vì chỉ hai
 * trạng thái đó mới chặn điều phối. Nhưng như vậy một kỳ mới ở trạng thái
 * `requested` là vô hình: người xếp lịch xếp chuyến vào đúng ngày mà thợ đã xin
 * xe, rồi kỳ đó được duyệt và chuyến vỡ.
 *
 * Nên nhắc ở đây — và nói rõ nó CHƯA chặn gì, để không ai tưởng xe đã nằm bãi.
 */
function khoiBaoDuongChuaDuyet() {
  const ds = (driverVehicleMaintenance || [])
    .filter(ky => String(ky.status || '').toLowerCase() === 'requested');
  if (!ds.length) return '';

  const dong = ds.slice(0, 6).map(ky => {
    const tu = ky.planned_start ? new Date(ky.planned_start) : null;
    const den = ky.planned_end ? new Date(ky.planned_end) : null;
    const khi = tu
      ? `${tu.toLocaleDateString('vi-VN')} ${tu.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}`
        + (den ? ` → ${den.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}` : '')
      : 'chưa có lịch';
    return `<li>
      <b>${escapeHtml(ky.vehicle_id || '')}</b>
      <span>${escapeHtml(khi)} · ${escapeHtml(ky.description || ky.request_no || 'Bảo dưỡng')}</span>
    </li>`;
  }).join('');

  return `<section class="dr-mt-pending">
    <h4><i class="fa-solid fa-screwdriver-wrench" aria-hidden="true"></i>
      Bảo dưỡng chưa duyệt <b>${ds.length}</b></h4>
    <p>Các kỳ này <strong>chưa chặn</strong> điều phối, nên lưới bên cạnh vẫn để xe là rảnh.
      Duyệt xong thì xe mới thành nằm bãi — nên xếp chuyến vào đúng ngày này là rủi ro.</p>
    <ul>${dong}</ul>
    ${ds.length > 6 ? `<p class="dr-mt-more">và ${ds.length - 6} kỳ nữa</p>` : ''}
  </section>`;
}

function renderDriverVehicleWeek() {
  const host = document.getElementById('driver-vehicle-week-content');
  if (!host || !window.TmsCockpit?.buildDriverShiftPlanner || !window.DriverRoster) return;
  const planner = window.TmsCockpit.buildDriverShiftPlanner({ drivers: fioriDrivers, vehicles: driverShiftVehicles, driver_shifts: driverShifts, vehicle_availability: driverVehicleAvailability }, driverShiftWeekStart);
  if (!planner.vehicle_rows.length) {
    host.innerHTML = '<div class="driver-shift-empty-inspector">Chưa có xe trong Master Data để lập lịch.</div>';
    return;
  }
  if (!selectedDriverVehicleDay || !planner.days.some(day => day.key === selectedDriverVehicleDay)) {
    selectedDriverVehicleDay = planner.days[0]?.key || '';
  }

  const DR = window.DriverRoster;
  // Bang nang luc va danh sach ngoai le tinh tren CA DOI XE, khong theo bo loc:
  // loc mat 5 xe xung dot di thi ca man hinh bao "khong co viec can xu ly" —
  // dung kieu noi doi ma man hinh nay sinh ra de tranh.
  const everything = buildDriverVehicleRosterData(planner, { ignoreFilters: true });
  const filtered = buildDriverVehicleRosterData(planner);
  const statusLabels = { busy: 'Đang có lịch', maintenance: 'Bảo dưỡng / sửa chữa', conflict: 'Xung đột lịch', available: 'Còn rảnh' };
  const typeOptions = [...new Set(everything.vehicles.map(v => v.type).filter(Boolean))].sort();
  // Dem so xe moi bai: nguoi dieu phoi can biet bai nao bao nhieu xe truoc khi
  // bam vao, khong phai bam roi moi thay.
  const depotCounts = new Map();
  everything.vehicles.forEach(v => {
    if (!v.depot_code) return;
    const current = depotCounts.get(v.depot_code) || { code: v.depot_code, label: v.depot || v.depot_code, count: 0 };
    current.count += 1;
    depotCounts.set(v.depot_code, current);
  });
  const depotOptions = [...depotCounts.values()].sort((a, b) => a.label.localeCompare(b.label, 'vi'));
  const unassigned = everything.vehicles.filter(v => !v.depot_code).length;
  const narrowed = Boolean(driverVehicleTableSearch.trim() || driverVehicleTableStatus || driverVehicleTableType || driverVehicleTableDepot);

  // Hai cột, y như tab Nhân sự: lưới bên trái, việc cần xử lý bên phải. Hai tab
  // của cùng một màn mà một tab xếp dọc, một tab xếp hai cột thì người dùng phải
  // học lại chỗ nhìn mỗi lần đổi tab.
  host.innerHTML = `
    <div class="dr-shell">
      <div class="dr-cover-slot">
        ${DR.vehicleCapacityStrip(everything, { selectedDay: selectedDriverVehicleDay })}
      </div>

      <div class="dr-main">
      <div class="dr-toolbar">
        <input id="driver-vehicle-day-search" type="search" value="${escapeHtml(driverVehicleTableSearch)}"
               placeholder="Tìm biển số, loại xe, Trip hoặc việc sửa chữa..."
               oninput="filterDriverVehicleDay(this.value)" aria-label="Tìm xe">
        <select id="driver-vehicle-day-depot" onchange="filterDriverVehicleDepot(this.value)" aria-label="Lọc theo bãi">
          <option value="">Tất cả bãi</option>
          ${depotOptions.map(item => `<option value="${escapeHtml(item.code)}">${escapeHtml(item.label)} (${item.count})</option>`).join('')}
          ${unassigned ? `<option value="__none__">Chưa gán bãi (${unassigned})</option>` : ''}
        </select>
        <select id="driver-vehicle-day-type" onchange="filterDriverVehicleType(this.value)" aria-label="Lọc theo loại xe">
          <option value="">Tất cả loại xe</option>
          ${typeOptions.map(type => `<option value="${escapeHtml(type)}">${escapeHtml(type)}</option>`).join('')}
        </select>
        <select id="driver-vehicle-day-status" onchange="filterDriverVehicleStatus(this.value)" aria-label="Lọc theo trạng thái">
          <option value="">Tất cả trạng thái</option>
          ${Object.entries(statusLabels).map(([key, label]) => `<option value="${escapeHtml(key)}">${escapeHtml(label)}</option>`).join('')}
        </select>
        ${narrowed ? '<button type="button" class="dr-clear" onclick="clearDriverVehicleFilters()"><i class="fa-solid fa-eraser" aria-hidden="true"></i> Xóa bộ lọc</button>' : ''}
      </div>

      <div class="dr-scroll">${DR.vehicleMatrix(filtered, {
        selectedDay: selectedDriverVehicleDay,
        limit: driverVehicleVisibleCount,
      })}</div>
      ${DR.vehicleLegend()}
      </div>

      <aside class="dr-side" aria-label="Việc cần xử lý trước điều phối">
        ${DR.vehicleExceptionList(everything, { expanded: driverVehicleExceptionsOpen })}
        ${khoiBaoDuongChuaDuyet()}
      </aside>
    </div>`;

  const depotSelect = document.getElementById('driver-vehicle-day-depot');
  if (depotSelect) depotSelect.value = driverVehicleTableDepot;
  const typeSelect = document.getElementById('driver-vehicle-day-type');
  if (typeSelect) typeSelect.value = driverVehicleTableType;
  const statusSelect = document.getElementById('driver-vehicle-day-status');
  if (statusSelect) statusSelect.value = driverVehicleTableStatus;
}

window.filterDriverVehicleDepot = function (value) {
  driverVehicleTableDepot = String(value || '');
  driverVehicleVisibleCount = window.DriverRoster.VEHICLE_PAGE_SIZE;
  renderDriverVehicleWeek();
};

window.filterDriverVehicleType = function (value) {
  driverVehicleTableType = String(value || '');
  driverVehicleVisibleCount = window.DriverRoster.VEHICLE_PAGE_SIZE;
  renderDriverVehicleWeek();
};

window.clearDriverVehicleFilters = function () {
  driverVehicleTableSearch = '';
  driverVehicleTableStatus = '';
  driverVehicleTableType = '';
  driverVehicleTableDepot = '';
  driverVehicleVisibleCount = window.DriverRoster.VEHICLE_PAGE_SIZE;
  renderDriverVehicleWeek();
};

window.selectDriverVehicleDay = function (dateKey) {
  // Chỉ làm nổi bật cột ngày đó. Không mở hộp thoại nữa: mất ngữ cảnh tuần là
  // điều làm bản cũ khó dùng.
  selectedDriverVehicleDay = String(dateKey || '');
  renderDriverVehicleWeek();
};

window.closeDriverVehicleDayDialog = function () {
  // Không còn hộp thoại nào để đóng. Giữ hàm để mọi chỗ gọi sẵn có không vỡ,
  // và dọn nốt phần tử cũ nếu còn sót từ phiên trước khi tải lại trang.
  document.getElementById('driver-vehicle-day-dialog')?.remove();
};

window.filterDriverVehicleDay = function (value) {
  driverVehicleTableSearch = String(value || '');
  driverVehicleVisibleCount = window.DriverRoster.VEHICLE_PAGE_SIZE;
  clearTimeout(driverVehicleSearchTimer);
  driverVehicleSearchTimer = setTimeout(() => renderDriverVehicleWeek(), 160);
};

window.filterDriverVehicleStatus = function (value) {
  driverVehicleTableStatus = String(value || '');
  driverVehicleVisibleCount = window.DriverRoster.VEHICLE_PAGE_SIZE;
  renderDriverVehicleWeek();
};

function renderDriverShiftAlerts() {
  const host = document.getElementById('driver-shift-alert-content');
  if (!host || !window.TmsCockpit?.buildDriverShiftPlanner) return;
  const planner = window.TmsCockpit.buildDriverShiftPlanner({ drivers: fioriDrivers, vehicles: driverShiftVehicles, driver_shifts: driverShifts, vehicle_availability: driverVehicleAvailability }, driverShiftWeekStart);
  const count = document.getElementById('driver-shift-alert-count');
  if (count) count.textContent = String(planner.alerts.length);
  host.innerHTML = planner.alerts.map(alert => `<div class="driver-planning-alert ${alert.severity === 'critical' ? 'critical' : 'warning'}"><i class="fa-solid fa-triangle-exclamation"></i><span><strong>${completionEscape(alert.code)}</strong><br>${completionEscape(alert.message)}</span></div>`).join('') || '<div class="driver-planning-alert clean"><i class="fa-solid fa-circle-check"></i><span>Không có xung đột ca, bảo dưỡng hoặc cảnh báo quay đầu trong tuần này.</span></div>';
}

function driverShiftDisplayType(shift) {
  if (shift.shift_type !== 'custom') return shift.shift_type;
  const hour = new Date(shift.shift_start).getHours();
  return hour >= 22 || hour < 6 ? 'night' : hour >= 14 ? 'afternoon' : 'morning';
}

function driverShiftTripsForPeriod(period) {
  return driverTripScheduleEntries().filter(item => {
    const start = new Date(item.planned_departure_at);
    const end = new Date(item.available_at_origin || item.available_at_destination || item.planned_arrival_at || item.planned_departure_at);
    return Number.isFinite(start.getTime()) && Number.isFinite(end.getTime()) && start < period.end && end > period.start;
  });
}

window.selectDriverShiftDay = function (dateKey) {
  // Chọn một ngày chỉ làm nổi bật cột đó trên ma trận và đổi ngày cho góc nhìn
  // "Một ngày". Không mở hộp thoại nữa: mất ngữ cảnh tuần là điều làm bản cũ
  // khó dùng.
  selectedDriverShiftDay = String(dateKey || '');
  selectedDriverShiftId = '';
  selectedDriverTripScheduleId = '';
  renderDriverShiftCalendarTable();
  renderDriverShiftInspector();
};

window.closeDriverShiftDayDialog = function () {
  // Không còn hộp thoại nào để đóng. Giữ hàm để mọi chỗ gọi sẵn có không vỡ,
  // và dọn nốt phần tử cũ nếu còn sót từ phiên trước khi tải lại trang.
  document.getElementById('driver-shift-day-dialog')?.remove();
};

window.selectDriverShiftType = function (type) {
  selectedDriverShiftType = String(type || 'morning');
  driverShiftTablePage = 1;
  renderDriverShiftCalendarTable();
};

window.changeDriverShiftTablePage = function (delta) {
  driverShiftTablePage = Math.max(1, driverShiftTablePage + Number(delta || 0));
  renderDriverShiftCalendarTable();
};

window.filterDriverShiftDay = function (value) {
  driverShiftTableSearch = String(value || '');
  driverShiftTablePage = 1;
  driverShiftVisibleCount = window.DriverRoster.PERSON_PAGE_SIZE;
  clearTimeout(driverShiftSearchTimer);
  driverShiftSearchTimer = setTimeout(() => {
    renderDriverShiftCalendarTable();
    const input = document.getElementById('driver-shift-day-search');
    if (input) { input.focus(); input.setSelectionRange(input.value.length, input.value.length); }
  }, 180);
};

window.filterDriverShiftRole = function (value) {
  driverShiftTableRole = String(value || '');
  driverShiftTablePage = 1;
  driverShiftVisibleCount = window.DriverRoster.PERSON_PAGE_SIZE;
  renderDriverShiftCalendarTable();
};

window.closeDriverDayScheduleView = function () {
  document.getElementById('driver-day-schedule-view')?.remove();
};

window.addDriverShiftFromDayView = function (driverId, dateKey, shiftType) {
  closeDriverDayScheduleView();
  openDriverShiftQuickForm(driverId, dateKey);
  const typeButton = document.querySelector(`.shift-quick-types button[data-shift-type="${shiftType}"]`);
  if (typeButton) selectDriverShiftQuickType(typeButton, shiftType);
};

window.editDriverShiftFromDayView = function (shiftId) {
  closeDriverDayScheduleView();
  closeDriverShiftDayDialog();
  openDriverShiftInspector(shiftId);
  document.getElementById('driver-shift-inspector')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
};

window.viewDriverTripFromDayView = function (tripId, driverId) {
  closeDriverDayScheduleView();
  closeDriverShiftDayDialog();
  openDriverTripScheduleInspector(tripId, driverId);
  document.getElementById('driver-shift-inspector')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
};

window.deleteDriverShiftFromDayView = async function (shiftId) {
  closeDriverDayScheduleView();
  await deleteDriverShiftById(shiftId);
};

window.openDriverDayScheduleView = function (driverId, dateKey) {
  const driver = fioriDrivers.find(item => String(item.id) === String(driverId));
  if (!driver) return;
  const dayPeriod = { start: new Date(`${dateKey}T00:00:00`), end: new Date(`${dateKey}T00:00:00`) };
  dayPeriod.end.setDate(dayPeriod.end.getDate() + 1);
  const shifts = driverShifts.filter(item => String(item.driver_id) === String(driverId) && driverShiftDateKey(item.shift_start) === dateKey);
  const trips = driverShiftTripsForPeriod(dayPeriod).filter(item => String(item.crew_driver_id) === String(driverId));
  const labels = { work: 'Làm việc', leave: 'Nghỉ phép', sick: 'Nghỉ bệnh', off: 'Nghỉ ca', unavailable: 'Không sẵn sàng' };
  const types = [
    { key: 'morning', label: 'Ca sáng', time: '06:00 - 14:00', icon: 'fa-regular fa-sun' },
    { key: 'afternoon', label: 'Ca chiều', time: '14:00 - 22:00', icon: 'fa-solid fa-cloud-sun' },
    { key: 'night', label: 'Ca đêm', time: '22:00 - 06:00', icon: 'fa-regular fa-moon' }
  ];
  const shiftColumns = types.map(type => {
    const entries = shifts.filter(item => driverShiftDisplayType(item) === type.key);
    const content = entries.map(item => {
      const kind = item.availability_kind || 'work';
      const start = new Date(item.shift_start).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
      const end = new Date(item.shift_end).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
      return `<article class="driver-day-view-entry ${kind !== 'work' ? 'absence' : ''}"><div><b>${completionEscape(labels[kind] || kind)}</b><span>${start} - ${end}</span><small>${item.vehicle_id ? `Xe ${completionEscape(item.vehicle_id)}` : 'Không gán xe'}${item.work_location ? ` · ${completionEscape(item.work_location)}` : ''}</small></div><div class="driver-day-view-entry-actions"><button type="button" title="Sửa ca" onclick="editDriverShiftFromDayView('${completionEscape(item.id)}')"><i class="fa-solid fa-pen"></i></button><button type="button" title="Xóa ca" onclick="deleteDriverShiftFromDayView('${completionEscape(item.id)}')"><i class="fa-solid fa-trash"></i></button></div></article>`;
    }).join('') || `<div class="driver-day-view-empty">Chưa có lịch trong khung giờ này.</div>`;
    return `<section class="driver-day-view-shift"><header><span><i class="${type.icon}"></i><b>${type.label}</b><small>${type.time}</small></span><button type="button" title="Thêm ${type.label.toLowerCase()}" onclick="addDriverShiftFromDayView('${completionEscape(driverId)}','${completionEscape(dateKey)}','${type.key}')"><i class="fa-solid fa-plus"></i></button></header>${content}</section>`;
  }).join('');
  const tripRows = trips.map(item => `<article class="driver-day-view-trip"><i class="fa-solid fa-lock"></i><div><b>Trip ${completionEscape(item.trip_id)}</b><span>${completionEscape(item.crew_role || 'Nhân sự chuyến')}</span><small>${completionEscape(item.vehicle_id || 'Chưa có xe')} · lịch do Điều phối khóa</small></div><button type="button" title="Xem chuyến" onclick="viewDriverTripFromDayView('${completionEscape(item.trip_id)}','${completionEscape(driverId)}')"><i class="fa-solid fa-eye"></i></button></article>`).join('') || '<div class="driver-day-view-empty">Không có chuyến vận chuyển khóa lịch trong ngày.</div>';
  document.getElementById('driver-day-schedule-view')?.remove();
  const overlay = document.createElement('div');
  overlay.id = 'driver-day-schedule-view';
  overlay.className = 'driver-day-view-overlay';
  overlay.onclick = event => { if (event.target === overlay) closeDriverDayScheduleView(); };
  overlay.innerHTML = `<section class="driver-day-view-dialog" role="dialog" aria-modal="true" aria-labelledby="driver-day-view-title"><header class="driver-day-dialog-header"><div><h3 id="driver-day-view-title"><i class="fa-solid fa-eye"></i> Lịch của ${completionEscape(driver.name || driver.id)}</h3><p>${completionEscape(driver.id)} · ${completionEscape(dateKey)} · xem đủ ca và chuyến trong ngày</p></div><button type="button" title="Đóng" onclick="closeDriverDayScheduleView()"><i class="fa-solid fa-xmark"></i></button></header><div class="driver-day-view-body"><div class="driver-day-view-shifts">${shiftColumns}</div><section class="driver-day-view-trips"><h4><i class="fa-solid fa-route"></i> Chuyến khóa lịch</h4>${tripRows}</section></div></section>`;
  document.body.appendChild(overlay);
};

/**
 * Dựng dữ liệu cho bảng xếp ca theo hợp đồng của js/driver-roster.js.
 *
 * Hàm này chỉ lo GOM dữ liệu; phần trình bày nằm ở module kia nên kiểm chứng
 * được bằng Node.
 */
function buildDriverRosterData(options) {
  const planner = window.TmsCockpit.buildDriverShiftPlanner(
    {
      drivers: fioriDrivers,
      vehicles: driverShiftVehicles,
      driver_shifts: driverShifts,
      vehicle_availability: driverVehicleAvailability,
    },
    driverShiftWeekStart
  );

  const ignore = Boolean(options && options.ignoreFilters);
  const keyword = ignore ? '' : driverShiftTableSearch.trim().toLowerCase();
  const role = ignore ? '' : driverShiftTableRole;
  const people = fioriDrivers
    .filter(driver => {
      const text = `${driver.id} ${driver.name || ''} ${driver.license_type || ''} ${driver.role || ''}`.toLowerCase();
      return (!keyword || text.includes(keyword)) && (!role || String(driver.role || '').includes(role));
    })
    .map(driver => ({
      id: String(driver.id || ''),
      name: driver.name || driver.id || '',
      role: driver.role || 'Tài xế',
      license: driver.license_type || '',
      days: planner.days.map(day => {
        const period = { start: new Date(`${day.key}T00:00:00`), end: new Date(`${day.key}T00:00:00`) };
        period.end.setDate(period.end.getDate() + 1);
        const shifts = driverShifts
          .filter(item => String(item.driver_id) === String(driver.id) && driverShiftDateKey(item.shift_start) === day.key)
          .map(item => ({
            id: String(item.id || ''),
            type: driverShiftDisplayType(item),
            kind: item.availability_kind || 'work',
            vehicle_id: item.vehicle_id || '',
            start_label: new Date(item.shift_start).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
            end_label: new Date(item.shift_end).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
          }));
        const trips = driverShiftTripsForPeriod(period)
          .filter(item => String(item.crew_driver_id) === String(driver.id))
          .map(item => ({
            trip_id: String(item.trip_id || ''),
            role: item.crew_role || '',
            vehicle_id: item.vehicle_id || '',
            // Xếp chuyến vào ca theo giờ khởi hành, để nó nằm đúng ô thay vì
            // chiếm cả ba ca của ngày đó.
            shift_type: driverShiftDisplayType({ shift_start: item.planned_departure_at, shift_type: 'custom' }),
          }));
        return { key: day.key, shifts, trips };
      }),
    }));

  return { days: planner.days.map(day => ({ key: day.key, label: day.label })), people };
}

/**
 * Bảng xếp ca tài xế.
 *
 * Thay bản cũ gồm dải 7 ngày chỉ hiện số tổng, cộng một hộp thoại che kín màn
 * hình cho từng ngày. Xem js/driver-roster.js để biết vì sao ma trận
 * người × ngày là dạng đúng cho việc xếp ca.
 */
/**
 * Ba nhóm lọc nhanh, mỗi nhóm một định nghĩa ĐO ĐƯỢC.
 *
 * Tính giờ từ `driverShifts` gốc chứ không từ nhãn giờ đã định dạng trong
 * `data.people`: nhãn là chuỗi "06:00" để hiện ra, cộng chuỗi thì ra rác. Và
 * chỉ tính ca `work` — một ngày nghỉ phép không phải giờ làm việc.
 */
function gioLamTrongTuan(maTaiXe) {
  return driverShifts
    .filter(ca => String(ca.driver_id) === String(maTaiXe)
      && (ca.availability_kind || 'work') === 'work')
    .reduce((tong, ca) => {
      const bd = new Date(ca.shift_start);
      const kt = new Date(ca.shift_end);
      if (Number.isNaN(bd.getTime()) || Number.isNaN(kt.getTime())) return tong;
      return tong + Math.max(0, (kt - bd) / 3600000);
    }, 0);
}

const GIO_TOI_DA_TUAN = 48;

function nhomCuaNhanSu(nguoi) {
  const caLamViec = driverShifts.filter(ca => String(ca.driver_id) === String(nguoi.id)
    && (ca.availability_kind || 'work') === 'work');
  const coNghi = driverShifts.some(ca => String(ca.driver_id) === String(nguoi.id)
    && (ca.availability_kind || 'work') !== 'work');
  return {
    need: caLamViec.length === 0,
    over: gioLamTrongTuan(nguoi.id) > GIO_TOI_DA_TUAN,
    leave: coNghi,
  };
}

function demNhomLocNhanh(duLieuCaDoi) {
  const dem = { all: duLieuCaDoi.people.length, need: 0, over: 0, leave: 0 };
  duLieuCaDoi.people.forEach(nguoi => {
    const n = nhomCuaNhanSu(nguoi);
    if (n.need) dem.need += 1;
    if (n.over) dem.over += 1;
    if (n.leave) dem.leave += 1;
  });
  return dem;
}

function locNhanSuTheoNhom(dsNguoi) {
  if (driverShiftChip === 'all') return dsNguoi;
  return dsNguoi.filter(nguoi => nhomCuaNhanSu(nguoi)[driverShiftChip]);
}

/**
 * Đổi nhóm lọc nhanh. Đặt lại số dòng đang hiện về trang đầu — giữ nguyên thì
 * đổi từ nhóm 200 người sang nhóm 3 người mà vẫn còn nút "xem thêm".
 */
window.setDriverShiftChip = function (nhom) {
  driverShiftChip = ['all', 'need', 'over', 'leave'].includes(nhom) ? nhom : 'all';
  driverShiftVisibleCount = window.DriverRoster.PERSON_PAGE_SIZE;
  renderDriverShiftCalendarTable();
};

function renderDriverShiftCalendarTable() {
  const host = document.getElementById('driver-shift-calendar');
  if (!host || !window.TmsCockpit?.buildDriverShiftPlanner || !window.DriverRoster) return;

  const DR = window.DriverRoster;
  const data = buildDriverRosterData();
  // Bang phu ca va danh sach cho hong tinh tren CA DOI, khong theo bo loc: loc
  // con lai 3 nguoi thi man hinh bao "tuan nay da kin ca", trong khi ca dem thu
  // Nam van khong co ai truc.
  const everyone = buildDriverRosterData({ ignoreFilters: true });
  if (!selectedDriverShiftDay || !data.days.some(day => day.key === selectedDriverShiftDay)) {
    selectedDriverShiftDay = data.days[0]?.key || '';
  }

  // Lọc nhanh chạy TRÊN kết quả của bộ lọc chữ và vai trò, chứ không thay nó:
  // người dùng gõ tên tổ rồi mới hỏi "trong tổ này ai chưa xếp".
  const nhom = demNhomLocNhanh(everyone);
  const nguoiLoc = locNhanSuTheoNhom(data.people);
  const dataLoc = Object.assign({}, data, { people: nguoiLoc });

  const view = driverRosterView === 'day' ? 'day' : 'week';
  const body = view === 'week'
    ? `<div class="dr-scroll">${DR.weekMatrix(dataLoc, { selectedDay: selectedDriverShiftDay, limit: driverShiftVisibleCount })}</div>`
    : DR.dayDetail(dataLoc, selectedDriverShiftDay);

  const dayOptions = data.days
    .map(day => `<option value="${escapeHtml(day.key)}"${day.key === selectedDriverShiftDay ? ' selected' : ''}>${escapeHtml(day.label)}</option>`)
    .join('');

  // HAI CỘT: lưới bên trái, việc cần xử lý bên phải.
  //
  // Bản cũ xếp dọc — dải độ phủ, rồi danh sách "cần xếp", rồi mới tới ma trận.
  // Đo trên màn 1600×1200 thì ma trận bắt đầu ở khoảng 1000px, tức người xếp ca
  // mở màn ra là KHÔNG thấy cái bảng mình phải làm việc trên đó, phải cuộn qua
  // một danh sách mà họ chỉ đọc một lần. Danh sách việc cần xử lý là thứ để
  // TRA trong lúc xếp, nên chỗ đúng của nó là cột bên cạnh.
  //
  // Dải độ phủ theo 7 ngày thì giữ nguyên chiều ngang phía trên: nó là đầu bảng
  // của chính ma trận, nhồi vào cột hẹp 336px là mất luôn nghĩa.
  host.innerHTML = `
    <div class="dr-shell">
      <div class="dr-cover-slot">
        ${DR.crewCoverageStrip(everyone, { selectedDay: selectedDriverShiftDay })}
      </div>

      <div class="dr-main">
        <div class="dr-toolbar">
          <div class="dr-views" role="group" aria-label="Góc nhìn lịch">
            <button type="button" class="${view === 'week' ? 'is-active' : ''}" onclick="setDriverRosterView('week')">
              <i class="fa-solid fa-table-cells" aria-hidden="true"></i> Cả tuần
            </button>
            <button type="button" class="${view === 'day' ? 'is-active' : ''}" onclick="setDriverRosterView('day')">
              <i class="fa-solid fa-calendar-day" aria-hidden="true"></i> Một ngày
            </button>
          </div>
          <input id="driver-shift-day-search" type="search" value="${escapeHtml(driverShiftTableSearch)}"
                 placeholder="Tìm tên, mã nhân sự, hạng bằng..." oninput="filterDriverShiftDay(this.value)"
                 aria-label="Tìm nhân sự">
          <select id="driver-shift-day-role" onchange="filterDriverShiftRole(this.value)" aria-label="Lọc theo vai trò">
            <option value="">Tất cả vai trò</option>
            <option value="Lái xe">Tài xế chính</option>
            <option value="Phụ xe">Phụ xe</option>
          </select>
          ${view === 'day' ? `<select onchange="selectDriverShiftDay(this.value)" aria-label="Chọn ngày">${dayOptions}</select>` : ''}
        </div>
        ${DR.filterChips(nhom, driverShiftChip, 'setDriverShiftChip')}
        ${nguoiLoc.length ? '' : `<p class="dr-chip-empty">Không có nhân sự nào trong nhóm này. Bấm <b>Tất cả</b> để xem lại toàn đội.</p>`}
        ${body}
        ${DR.legend()}
      </div>

      <aside class="dr-side" aria-label="Việc cần xử lý trước điều phối">
        ${DR.crewGapList(everyone, { expanded: driverShiftGapsOpen })}
      </aside>
    </div>`;

  const roleSelect = document.getElementById('driver-shift-day-role');
  if (roleSelect) roleSelect.value = driverShiftTableRole;
}

/** Hành động của các ô trong bảng xếp ca. */
window.DriverRosterActions = {
  selectDay(dateKey) {
    selectedDriverShiftDay = String(dateKey || '');
    renderDriverShiftCalendarTable();
  },
  assign(driverId, dateKey, shiftType) {
    // Hàng của ma trận ĐÃ LÀ tài xế, nên gọi thẳng hàm cấp thấp thay vì
    // assignSelectedDriverToShift — bản cũ buộc phải chọn tài xế ở danh sách
    // bên trái trước rồi mới bấm được vào ô lịch. Ở đây thao tác đó là dư.
    selectedDriverShiftDay = String(dateKey || '');
    assignDriverToShiftSlot(String(driverId || ''), dateKey, shiftType);
  },
  openShift(shiftId) {
    openDriverShiftInspector(shiftId);
  },
  openTrip(tripId, driverId) {
    openDriverTripScheduleInspector(tripId, driverId);
  },
  selectVehicleDay(dateKey) {
    selectDriverVehicleDay(dateKey);
  },
  showMorePeople() {
    driverShiftVisibleCount += window.DriverRoster.PERSON_PAGE_SIZE;
    renderDriverShiftCalendarTable();
  },
  toggleGaps() {
    driverShiftGapsOpen = !driverShiftGapsOpen;
    renderDriverShiftCalendarTable();
  },
  focusPerson(driverId) {
    // Loc thang den dung nguoi do thay vi bat nguoi dung tu tim trong 400 dong.
    driverShiftTableSearch = String(driverId || '');
    driverShiftVisibleCount = window.DriverRoster.PERSON_PAGE_SIZE;
    selectedDriverForShiftId = String(driverId || '');
    renderDriverShiftCalendarTable();
    renderDriverShiftInspector();
  },
  openVehicle(vehicleId) {
    editFioriVehicle(String(vehicleId || ''));
  },
  showMoreVehicles() {
    driverVehicleVisibleCount += window.DriverRoster.VEHICLE_PAGE_SIZE;
    renderDriverVehicleWeek();
  },
  toggleExceptions() {
    driverVehicleExceptionsOpen = !driverVehicleExceptionsOpen;
    renderDriverVehicleWeek();
  },
};

window.setDriverRosterView = function (view) {
  driverRosterView = view === 'day' ? 'day' : 'week';
  renderDriverShiftCalendarTable();
};

window.renderDriverShiftPlanner = function () {
  if (!driverShiftWeekStart) driverShiftWeekStart = startOfDriverShiftWeek();
  const label = document.getElementById('driver-shift-week-label');
  if (label) {
    const end = new Date(driverShiftWeekStart);
    end.setDate(end.getDate() + 6);
    label.textContent = `${driverShiftWeekStart.toLocaleDateString('vi-VN')} - ${end.toLocaleDateString('vi-VN')}`;
  }
  renderDriverShiftCalendarTable();
  renderDriverShiftInspector();
  renderDriverVehicleWeek();
  renderDriverShiftAlerts();
};

/**
 * Trạng thái của hộp thoại tạo ca lặp.
 *
 * Trước đây mọi thứ đọc thẳng từ DOM lúc bấm Lưu, nên không thể hiện được số ca
 * sẽ tạo trong khi người dùng còn đang chỉnh. Giữ một bản trạng thái ở đây thì
 * mỗi lần đổi là tính lại và vẽ lại khung xem trước.
 */
let recurrenceDraft = null;

function defaultRecurrenceDraft() {
  const start = driverShiftWeekStart || startOfDriverShiftWeek();
  const end = new Date(start);
  // Mặc định MỘT tháng, không phải ba. Bản cũ mặc định 3 tháng × 6 ngày/tuần =
  // khoảng 78 ca cho mỗi người ngay từ lúc mở hộp thoại — một con số lớn như
  // vậy phải là lựa chọn có ý thức, không phải giá trị sẵn.
  end.setMonth(end.getMonth() + 1);
  return {
    driverIds: selectedDriverForShiftId ? [String(selectedDriverForShiftId)] : [],
    weekdays: [0, 1, 2, 3, 4],
    shiftType: 'morning',
    startTime: '06:00',
    endTime: '14:00',
    effectiveStart: driverShiftDateKey(start),
    effectiveEnd: driverShiftDateKey(end),
    vehicleId: '',
    workLocation: '',
    search: '',
    // So dong nhan su dung mot lan. Hang tram nut checkbox trong mot hop thoai
    // lam trinh duyet cham va cuon khong noi.
    visibleCount: 60,
  };
}

function recurrencePlan() {
  return window.ShiftRecurrence.planRecurrence({
    driverIds: recurrenceDraft.driverIds,
    weekdays: recurrenceDraft.weekdays,
    effectiveStart: recurrenceDraft.effectiveStart,
    effectiveEnd: recurrenceDraft.effectiveEnd,
    startTime: recurrenceDraft.startTime,
    endTime: recurrenceDraft.endTime,
    existingShifts: driverShifts,
  });
}

/**
 * Hộp thoại tạo ca lặp theo tuần.
 *
 * Đổi tên khỏi "Thiết lập lịch làm việc mặc định": cái tên đó nghe như một thiết
 * lập có thể sửa lại sau, trong khi thao tác này ghi thẳng từng ca thật vào cơ
 * sở dữ liệu và không lưu quy tắc lặp nào cả. Nay tiêu đề, khung xem trước và
 * nhãn trên nút đều nói đúng số ca sẽ được ghi.
 */
window.openWeeklyDriverSchedule = function () {
  document.getElementById('weekly-driver-schedule-dialog')?.remove();
  if (!window.ShiftRecurrence) return;
  recurrenceDraft = defaultRecurrenceDraft();

  const dialog = document.createElement('div');
  dialog.id = 'weekly-driver-schedule-dialog';
  dialog.className = 'weekly-schedule-overlay';
  dialog.onclick = event => { if (event.target === dialog) closeWeeklyDriverSchedule(); };
  dialog.innerHTML = `<div class="weekly-schedule-dialog sr-dialog" role="dialog" aria-modal="true" aria-labelledby="weekly-schedule-title">
    <header>
      <div>
        <h3 id="weekly-schedule-title"><i class="fa-solid fa-repeat"></i> Tạo ca lặp theo tuần</h3>
        <p>Sinh sẵn từng ca làm việc thật cho khoảng thời gian đã chọn. Mỗi ca sau đó sửa hoặc xóa được riêng trên lịch.</p>
      </div>
      <button type="button" title="Đóng" onclick="closeWeeklyDriverSchedule()"><i class="fa-solid fa-xmark"></i></button>
    </header>
    <div class="sr-body" id="weekly-schedule-body"></div>
    <footer>
      <button type="button" class="fiori-btn fiori-btn-secondary" onclick="closeWeeklyDriverSchedule()">Hủy</button>
      <button id="weekly-schedule-save" type="button" class="fiori-btn" onclick="saveWeeklyDriverSchedule()"></button>
    </footer>
  </div>`;
  document.body.appendChild(dialog);
  renderWeeklyScheduleBody();
};

/** Vẽ lại toàn bộ phần thân theo trạng thái hiện tại. */
function renderWeeklyScheduleBody() {
  const host = document.getElementById('weekly-schedule-body');
  if (!host || !recurrenceDraft) return;
  const SR = window.ShiftRecurrence;
  const plan = recurrencePlan();
  const custom = recurrenceDraft.shiftType === 'custom';

  const keyword = recurrenceDraft.search.trim().toLowerCase();
  // KHÔNG escape trước khi so khớp: bản cũ escape rồi mới .includes() nên tìm
  // một cái tên có dấu "&" thì không bao giờ khớp, vì trong chuỗi tìm nó đã
  // thành "&amp;".
  const people = fioriDrivers.filter(driver => {
    const text = `${driver.name || ''} ${driver.id || ''} ${driver.role || ''} ${driver.license_type || ''} ${driver.phone || ''}`.toLowerCase();
    return !keyword || text.includes(keyword);
  });
  const chosen = new Set(recurrenceDraft.driverIds);

  // KHONG cat cung o 60 nua. Voi hang tram tai xe, nguoi thu 61 tro di khong
  // the tim ra duoc: danh sach chi hien 60 dong dau, va o tim kiem thi loc
  // TRUOC khi cat, nen go dung ten van ra — nhung neu khong go dung thi ho
  // bien mat hoan toan ma man hinh khong noi gi.
  //
  // Nay van gioi han so DONG DUNG (de khong nhoi hang tram nut vao DOM) nhung
  // noi ro con bao nhieu nguoi chua hien, va tai them duoc.
  const visible = people.slice(0, recurrenceDraft.visibleCount);
  const hiddenPeople = people.length - visible.length;
  const peopleRows = visible.map(driver => {
    const id = String(driver.id || '');
    const initials = String(driver.name || id || '?').split(/\s+/).slice(-2).map(part => part[0] || '').join('').toUpperCase();
    return `<label class="sr-person${chosen.has(id) ? ' is-on' : ''}">
      <input type="checkbox" ${chosen.has(id) ? 'checked' : ''} onchange="toggleRecurrenceDriver('${escapeJsAttr(id)}', this.checked)">
      <span class="sr-person-avatar">${escapeHtml(initials)}</span>
      <span class="sr-person-text">
        <b>${escapeHtml(driver.name || id)}</b>
        <small>${escapeHtml(id)} · ${escapeHtml(driver.role || 'Nhân sự')} · ${escapeHtml(driver.license_type || 'Chưa có hạng bằng')}</small>
      </span>
      <i class="fa-solid fa-check sr-person-tick" aria-hidden="true"></i>
    </label>`;
  }).join('') || '<div class="sr-empty">Không tìm thấy nhân sự phù hợp.</div>';

  const peopleFooter = hiddenPeople > 0
    ? `<div class="sr-people-more">
        <span>Đang hiện <b>${visible.length}</b> trên <b>${people.length}</b> người</span>
        <button type="button" class="sr-mini" onclick="showMoreRecurrenceDrivers()">
          <i class="fa-solid fa-chevron-down" aria-hidden="true"></i> Xem thêm ${Math.min(hiddenPeople, 60)} người
        </button>
      </div>`
    : '';

  const vehicleOptions = driverShiftVehicles.map(vehicle => {
    const id = String(vehicle.id || '');
    return `<option value="${escapeHtml(id)}"${recurrenceDraft.vehicleId === id ? ' selected' : ''}>${escapeHtml(id)} · ${escapeHtml(vehicle.type || '')}</option>`;
  }).join('');

  host.innerHTML = `
    <section class="sr-step">
      <h4><span class="sr-step-no">1</span> Chọn nhân sự <small>${recurrenceDraft.driverIds.length ? `đã chọn ${recurrenceDraft.driverIds.length}` : 'chưa chọn ai'}</small></h4>
      <div class="sr-row">
        <div class="sr-search">
          <i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i>
          <input id="weekly-schedule-driver-search" type="search" autocomplete="off"
                 value="${escapeHtml(recurrenceDraft.search)}"
                 placeholder="Nhập tên, mã nhân sự, vai trò hoặc hạng bằng..."
                 oninput="filterWeeklyScheduleDrivers(this.value)" aria-label="Tìm nhân sự">
        </div>
        <button type="button" class="sr-mini" onclick="selectAllRecurrenceDrivers()"><i class="fa-solid fa-users" aria-hidden="true"></i> Chọn cả ${people.length} người khớp</button>
        ${recurrenceDraft.driverIds.length ? '<button type="button" class="sr-mini" onclick="clearRecurrenceDrivers()"><i class="fa-solid fa-eraser" aria-hidden="true"></i> Bỏ chọn hết</button>' : ''}
      </div>
      <div class="sr-people">${peopleRows}</div>
      ${peopleFooter}
    </section>

    <section class="sr-step">
      <h4><span class="sr-step-no">2</span> Ngày trong tuần <small>${recurrenceDraft.weekdays.length ? `${recurrenceDraft.weekdays.length} ngày mỗi tuần` : 'chưa chọn ngày'}</small></h4>
      <div class="sr-row">
        <div class="sr-days" role="group" aria-label="Ngày làm việc lặp lại">
          ${SR.WEEKDAYS.map(day => `<button type="button" class="sr-day${recurrenceDraft.weekdays.includes(day.index) ? ' is-on' : ''}"
            aria-pressed="${recurrenceDraft.weekdays.includes(day.index)}"
            title="${escapeHtml(day.label)}"
            onclick="toggleRecurrenceWeekday(${day.index})">${escapeHtml(day.short)}</button>`).join('')}
        </div>
        <button type="button" class="sr-mini" onclick="setRecurrenceWeekdays('weekdays')">T2–T6</button>
        <button type="button" class="sr-mini" onclick="setRecurrenceWeekdays('sixdays')">T2–T7</button>
        <button type="button" class="sr-mini" onclick="setRecurrenceWeekdays('all')">Cả tuần</button>
      </div>
    </section>

    <section class="sr-step">
      <h4><span class="sr-step-no">3</span> Ca làm việc</h4>
      <div class="sr-shifts" role="group" aria-label="Loại ca">
        ${SR.SHIFT_PRESETS.map(item => `<button type="button" class="sr-shift${recurrenceDraft.shiftType === item.key ? ' is-on' : ''}"
          aria-pressed="${recurrenceDraft.shiftType === item.key}"
          onclick="setRecurrenceShiftType('${escapeJsAttr(item.key)}')">
          <b>${escapeHtml(item.label)}</b>
          <small>${item.start ? escapeHtml(`${item.start} – ${item.end}`) : 'Tự đặt giờ'}</small>
        </button>`).join('')}
      </div>
      <div class="sr-grid">
        <label>Giờ bắt đầu
          <input type="time" value="${escapeHtml(recurrenceDraft.startTime)}" ${custom ? '' : 'disabled'}
                 onchange="setRecurrenceTime('startTime', this.value)">
        </label>
        <label>Giờ kết thúc
          <input type="time" value="${escapeHtml(recurrenceDraft.endTime)}" ${custom ? '' : 'disabled'}
                 onchange="setRecurrenceTime('endTime', this.value)">
        </label>
      </div>
      ${plan.crossesMidnight ? `<p class="sr-hint"><i class="fa-solid fa-moon" aria-hidden="true"></i> Ca này qua đêm: kết thúc ${escapeHtml(recurrenceDraft.endTime)} của ngày hôm sau. Hệ thống tự nhận ra, anh không phải khai thêm.</p>` : ''}
    </section>

    <section class="sr-step">
      <h4><span class="sr-step-no">4</span> Khoảng áp dụng</h4>
      <div class="sr-grid">
        <label>Từ ngày
          <input type="date" value="${escapeHtml(recurrenceDraft.effectiveStart)}" onchange="setRecurrenceRange('effectiveStart', this.value)">
        </label>
        <label>Đến ngày
          <input type="date" value="${escapeHtml(recurrenceDraft.effectiveEnd)}" onchange="setRecurrenceRange('effectiveEnd', this.value)">
        </label>
      </div>
      <div class="sr-row">
        <button type="button" class="sr-mini" onclick="setRecurrenceMonths(1)">1 tháng</button>
        <button type="button" class="sr-mini" onclick="setRecurrenceMonths(3)">3 tháng</button>
        <button type="button" class="sr-mini" onclick="setRecurrenceMonths(6)">6 tháng</button>
      </div>
    </section>

    <section class="sr-step">
      <h4><span class="sr-step-no">5</span> Tùy chọn <small>không bắt buộc</small></h4>
      <div class="sr-grid">
        <label>Xe gán cố định
          <select onchange="setRecurrenceField('vehicleId', this.value)">
            <option value="">Không gán cố định xe</option>${vehicleOptions}
          </select>
        </label>
        <label>Địa điểm làm việc
          <input type="text" value="${escapeHtml(recurrenceDraft.workLocation)}" placeholder="Kho, bãi hoặc điểm tập kết"
                 oninput="setRecurrenceField('workLocation', this.value)">
        </label>
      </div>
    </section>

    ${renderRecurrencePreview(plan)}`;

  renderRecurrenceSaveButton(plan);
}

/**
 * Khung xem trước — phần quan trọng nhất của bản thiết kế lại.
 *
 * Bản cũ không nói gì cả: bấm "Tạo lịch mặc định" rồi mới biết vừa ghi bao
 * nhiêu ca qua một dòng thông báo. Với thiết lập mặc định cũ (T2–T7, 3 tháng)
 * đó là khoảng 78 ca cho MỖI người được chọn.
 */
function renderRecurrencePreview(plan) {
  const SR = window.ShiftRecurrence;
  if (!plan.valid) {
    return `<section class="sr-preview sr-preview--blocked">
      <h4><i class="fa-solid fa-circle-exclamation" aria-hidden="true"></i> Còn thiếu thông tin</h4>
      <ul>${plan.errors.map(error => `<li>${escapeHtml(error)}</li>`).join('')}</ul>
    </section>`;
  }

  const summary = SR.summarize(plan);
  const heavy = plan.totalShifts > 200;
  const busiest = plan.perDriver.filter(item => item.existingCount > 0);

  return `<section class="sr-preview${heavy ? ' sr-preview--heavy' : ''}">
    <h4><i class="fa-solid fa-clipboard-check" aria-hidden="true"></i> Trước khi lưu</h4>
    <p class="sr-preview-headline">${escapeHtml(summary.headline)}</p>
    <p class="sr-preview-detail">${escapeHtml(summary.detail)}</p>
    <ul class="sr-preview-people">
      ${plan.perDriver.slice(0, 6).map(item => {
        const driver = fioriDrivers.find(person => String(person.id) === item.driverId);
        return `<li><b>${escapeHtml(driver?.name || item.driverId)}</b> <span>${item.shiftCount} ca</span>${
          item.existingCount ? `<em><i class="fa-solid fa-triangle-exclamation" aria-hidden="true"></i> ${item.existingCount} ngày đã có ca</em>` : ''
        }</li>`;
      }).join('')}
      ${plan.perDriver.length > 6 ? `<li class="sr-preview-more">và ${plan.perDriver.length - 6} người nữa</li>` : ''}
    </ul>
    ${busiest.length ? `<p class="sr-warn"><i class="fa-solid fa-triangle-exclamation" aria-hidden="true"></i>
      ${escapeHtml(`${busiest.length} người đã có ca trong một số ngày trên. Ca cùng người, cùng ngày, cùng giờ sẽ được ghi đè; khác giờ thì thành hai ca chồng nhau và Dispatch sẽ báo xung đột.`)}</p>` : ''}
    ${heavy ? `<p class="sr-warn"><i class="fa-solid fa-layer-group" aria-hidden="true"></i>
      ${escapeHtml(`Đây là ${plan.totalShifts} bản ghi trong một lần bấm. Cân nhắc thu ngắn khoảng áp dụng hoặc chia theo nhóm nhân sự.`)}</p>` : ''}
  </section>`;
}

/** Nhãn trên nút lưu mang luôn số ca, để con số không nằm ở chỗ khác. */
function renderRecurrenceSaveButton(plan) {
  const button = document.getElementById('weekly-schedule-save');
  if (!button) return;
  button.disabled = !plan.valid;
  button.innerHTML = plan.valid
    ? `<i class="fa-solid fa-floppy-disk" aria-hidden="true"></i> Tạo ${plan.totalShifts} ca`
    : '<i class="fa-solid fa-floppy-disk" aria-hidden="true"></i> Tạo ca';
}

function updateRecurrenceDraft(changes) {
  Object.assign(recurrenceDraft, changes);
  renderWeeklyScheduleBody();
}

window.showMoreRecurrenceDrivers = function () {
  recurrenceDraft.visibleCount += 60;
  renderWeeklyScheduleBody();
};

window.filterWeeklyScheduleDrivers = function (value) {
  recurrenceDraft.search = String(value || '');
  recurrenceDraft.visibleCount = 60;
  renderWeeklyScheduleBody();
  // Vẽ lại làm mất con trỏ, nên đưa tiêu điểm về đúng ô tìm kiếm.
  const input = document.getElementById('weekly-schedule-driver-search');
  if (input) {
    input.focus();
    input.setSelectionRange(input.value.length, input.value.length);
  }
};

window.toggleRecurrenceDriver = function (driverId, on) {
  const id = String(driverId || '');
  const next = new Set(recurrenceDraft.driverIds);
  if (on) next.add(id); else next.delete(id);
  updateRecurrenceDraft({ driverIds: [...next] });
};

/**
 * Chon dung mot nguoi.
 *
 * Giu lai vi cac cho khac trong app.js van goi ten nay. Ban cu ghi
 * `input.value = escapeHtml(...)` nen ten co dau "&" hien ra thanh "&amp;"
 * truoc mat nguoi dung — o day khong con dan ten vao o chu nua nen loi do bien
 * mat theo.
 */
window.selectWeeklyScheduleDriver = function (driverId) {
  updateRecurrenceDraft({ driverIds: [String(driverId || '')].filter(Boolean) });
};

window.selectAllRecurrenceDrivers = function () {
  const keyword = recurrenceDraft.search.trim().toLowerCase();
  const ids = fioriDrivers.filter(driver => {
    const text = `${driver.name || ''} ${driver.id || ''} ${driver.role || ''} ${driver.license_type || ''} ${driver.phone || ''}`.toLowerCase();
    return !keyword || text.includes(keyword);
  }).map(driver => String(driver.id || '')).filter(Boolean);
  updateRecurrenceDraft({ driverIds: [...new Set([...recurrenceDraft.driverIds, ...ids])] });
};

window.clearRecurrenceDrivers = function () {
  updateRecurrenceDraft({ driverIds: [] });
};

window.toggleRecurrenceWeekday = function (index) {
  const next = new Set(recurrenceDraft.weekdays);
  if (next.has(index)) next.delete(index); else next.add(index);
  updateRecurrenceDraft({ weekdays: [...next].sort((a, b) => a - b) });
};

window.setRecurrenceWeekdays = function (mode) {
  const presets = { weekdays: [0, 1, 2, 3, 4], sixdays: [0, 1, 2, 3, 4, 5], all: [0, 1, 2, 3, 4, 5, 6] };
  updateRecurrenceDraft({ weekdays: presets[mode] || presets.weekdays });
};

window.setRecurrenceShiftType = function (key) {
  const item = window.ShiftRecurrence.preset(key);
  if (!item) return;
  // Chọn ca sẵn thì giờ đi theo ca, nên không thể có "06:00–14:00 · Ca đêm".
  updateRecurrenceDraft(item.start
    ? { shiftType: key, startTime: item.start, endTime: item.end }
    : { shiftType: key });
};

window.setRecurrenceTime = function (field, value) {
  updateRecurrenceDraft({ [field]: String(value || '') });
};

window.setRecurrenceRange = function (field, value) {
  updateRecurrenceDraft({ [field]: String(value || '') });
};

window.setRecurrenceMonths = function (months) {
  const from = new Date(`${recurrenceDraft.effectiveStart}T00:00:00`);
  if (!Number.isFinite(from.getTime())) return;
  const to = new Date(from);
  to.setMonth(to.getMonth() + Number(months || 1));
  updateRecurrenceDraft({ effectiveEnd: driverShiftDateKey(to) });
};

window.setRecurrenceField = function (field, value) {
  // Ô chữ thì không vẽ lại: vẽ lại giữa lúc đang gõ sẽ làm mất con trỏ.
  recurrenceDraft[field] = String(value || '');
  if (field !== 'workLocation') renderWeeklyScheduleBody();
};

window.closeWeeklyDriverSchedule = function () {
  document.getElementById('weekly-driver-schedule-dialog')?.remove();
  recurrenceDraft = null;
};

async function saveWeeklyScheduleCompat(payload) {
  try {
    return await driverShiftApiJson('/api/tms/scheduling/driver-shifts/weekly-schedule', {
      method: 'POST', body: JSON.stringify(payload)
    });
  } catch (error) {
    if (error.status !== 404 && error.status !== 405) throw error;
    const start = new Date(`${payload.effective_start}T00:00:00`);
    const end = new Date(`${payload.effective_end}T00:00:00`);
    const created = [];
    for (const cursor = new Date(start); cursor <= end; cursor.setDate(cursor.getDate() + 1)) {
      const weekday = (cursor.getDay() + 6) % 7;
      if (!payload.weekdays.includes(weekday)) continue;
      const dateKey = driverShiftDateKey(cursor);
      const startAt = new Date(`${dateKey}T${payload.start_time}:00`);
      const endAt = new Date(`${dateKey}T${payload.end_time}:00`);
      endAt.setDate(endAt.getDate() + Number(payload.end_day_offset || 0));
      created.push(await driverShiftApiJson('/api/tms/scheduling/driver-shifts', {
        method: 'POST', body: JSON.stringify({
          id: `WEEKLY-${payload.driver_id}-${dateKey.replaceAll('-', '')}-${payload.start_time.replace(':', '')}-${payload.end_time.replace(':', '')}-D${payload.end_day_offset || 0}`,
          driver_id: payload.driver_id, vehicle_id: payload.vehicle_id, shift_type: payload.shift_type,
          shift_start: startAt.toISOString(), shift_end: endAt.toISOString(), availability_kind: 'work',
          work_location: payload.work_location, notes: 'Lịch làm việc mặc định lặp theo tuần', status: 'planned'
        })
      }));
    }
    return { created_count: created.length, shifts: created };
  }
}

window.saveWeeklyDriverSchedule = async function () {
  if (!recurrenceDraft) return;
  const plan = recurrencePlan();
  if (!plan.valid) {
    showToast(plan.errors[0], 'error');
    return;
  }

  const button = document.getElementById('weekly-schedule-save');
  if (button) button.disabled = true;

  // Backend nhận một người mỗi lần gọi, nên nhiều người thì gọi lần lượt. Báo
  // cáo trung thực từng người: một người lỗi không được làm mất kết quả của
  // những người đã ghi xong.
  const done = [];
  const failed = [];
  for (const driverId of plan.driverIds) {
    try {
      const result = await saveWeeklyScheduleCompat({
        driver_id: driverId,
        weekdays: recurrenceDraft.weekdays,
        start_time: plan.startTime,
        end_time: plan.endTime,
        end_day_offset: plan.endDayOffset,
        timezone_offset_minutes: new Date().getTimezoneOffset(),
        effective_start: recurrenceDraft.effectiveStart,
        effective_end: recurrenceDraft.effectiveEnd,
        shift_type: recurrenceDraft.shiftType,
        vehicle_id: recurrenceDraft.vehicleId || null,
        work_location: recurrenceDraft.workLocation || null,
      });
      done.push({ driverId, count: result.created_count || 0 });
    } catch (error) {
      failed.push({ driverId, message: error.message });
    }
  }

  const created = done.reduce((sum, item) => sum + item.count, 0);
  const lastDriver = plan.driverIds[plan.driverIds.length - 1];
  if (done.length) {
    closeWeeklyDriverSchedule();
    selectedDriverForShiftId = done[done.length - 1].driverId || lastDriver;
    await loadDriverShiftPlanner();
  } else if (button) {
    button.disabled = false;
  }

  if (failed.length && done.length) {
    showToast(`Đã tạo ${created} ca cho ${done.length} người, nhưng ${failed.length} người lỗi: ${failed[0].message}`, 'error');
  } else if (failed.length) {
    showToast(failed[0].message, 'error');
  } else {
    showToast(`Đã tạo ${created} ca làm việc cho ${done.length} nhân sự.`);
  }
};

window.openAddDriverModal = function () {
  currentEditingDriverRow = null;
  if (typeof syncAllDynamicDropdowns === 'function') syncAllDynamicDropdowns();
  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
  const titleSpan = document.getElementById('driver-modal-title-text');
  if (titleSpan) {
    titleSpan.innerText = lang === 'la' ? 'ເພີ່ມຄົນຂັບ / ຜູ້ຊ່ວຍຄົນຂັບໃໝ່' : (lang === 'en' ? 'Add New Driver / Co-driver' : 'Thêm tài xế / phụ xe');
  }
  if (document.getElementById('drv-id')) {
    document.getElementById('drv-id').value = '';
    document.getElementById('drv-id').disabled = false;
  }
  if (document.getElementById('drv-name')) document.getElementById('drv-name').value = '';
  if (document.getElementById('drv-role')) document.getElementById('drv-role').value = 'Lái xe chính';
  if (document.getElementById('drv-license')) document.getElementById('drv-license').value = 'Hạng FC';
  if (document.getElementById('drv-phone')) document.getElementById('drv-phone').value = '';
  if (document.getElementById('drv-vehicle')) document.getElementById('drv-vehicle').value = 'Chưa gán';
  if (document.getElementById('drv-shift')) document.getElementById('drv-shift').value = 'Ca sáng (06:00 - 14:00)';
  setDriverOperationalStatus('available');
  clearDriverPhoto();
  if (document.getElementById('driver-modal-dialog')) document.getElementById('driver-modal-dialog').style.display = 'flex';
};

window.closeDriverModal = function () {
  if (document.getElementById('driver-modal-dialog')) document.getElementById('driver-modal-dialog').style.display = 'none';
  currentEditingDriverRow = null;
};

function setDriverPhoto(photoUrl) {
  const hidden = document.getElementById('drv-photo-url');
  const preview = document.getElementById('drv-photo-preview');
  const placeholder = document.getElementById('drv-photo-placeholder');
  const fileInput = document.getElementById('drv-photo-file');

  if (hidden) hidden.value = photoUrl || '';
  if (preview) {
    preview.src = photoUrl || '';
    preview.style.display = photoUrl ? 'block' : 'none';
  }
  if (placeholder) placeholder.style.display = photoUrl ? 'none' : 'block';
  if (!photoUrl && fileInput) fileInput.value = '';
}

window.previewDriverPhoto = async function (event) {
  const file = event?.target?.files?.[0];
  if (!file) {
    clearDriverPhoto();
    return;
  }
  if (!file.type.startsWith('image/')) {
    showToast('Vui lòng chọn đúng file ảnh tài xế.');
    clearDriverPhoto();
    return;
  }
  if (file.size > 2 * 1024 * 1024) {
    showToast('Ảnh tài xế tối đa 2MB để lưu demo nhanh và nhẹ.');
    clearDriverPhoto();
    return;
  }
  try {
    showToast('Đang tải ảnh tài xế lên hệ thống...');
    const uploadedUrl = await uploadMasterDataImage(file, 'drivers');
    setDriverPhoto(uploadedUrl);
    showToast('Đã tải ảnh tài xế lên. Bấm Lưu để ghi vào hồ sơ tài xế.');
  } catch (err) {
    clearDriverPhoto();
    showToast(err?.message || 'Không tải được ảnh tài xế, anh chọn ảnh khác giúp em nhé.');
  }
};

window.clearDriverPhoto = function () {
  setDriverPhoto('');
};

window.editDriverById = function (id) {
  const driver = fioriDrivers.find(d => (d.id || d.name) === id);
  if (!driver) return;
  currentEditingDriverRow = null;
  if (typeof syncAllDynamicDropdowns === 'function') syncAllDynamicDropdowns();

  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
  const titleSpan = document.getElementById('driver-modal-title-text');
  if (titleSpan) {
    titleSpan.innerText = lang === 'la' ? `ແກ້ໄຂບຸກຄະລາກອນ: ${escapeHtml(driver.name || driver.id)}` : (lang === 'en' ? `Edit Personnel: ${escapeHtml(driver.name || driver.id)}` : `Chỉnh sửa nhân sự: ${escapeHtml(driver.name || driver.id)}`);
  }
  if (document.getElementById('drv-id')) {
    document.getElementById('drv-id').value = driver.id || driver.name || '';
    document.getElementById('drv-id').disabled = true;
  }
  if (document.getElementById('drv-name')) document.getElementById('drv-name').value = driver.name || driver.id || '';
  if (document.getElementById('drv-role')) document.getElementById('drv-role').value = cleanDriverMasterText(driver.role, 'Lái xe chính');
  if (document.getElementById('drv-license')) document.getElementById('drv-license').value = cleanDriverMasterText(driver.license_type, 'Hạng FC');
  if (document.getElementById('drv-phone')) document.getElementById('drv-phone').value = driver.phone || '';
  if (document.getElementById('drv-vehicle')) document.getElementById('drv-vehicle').value = cleanDriverMasterText(driver.assigned_vehicle, 'Chưa gán');
  if (document.getElementById('drv-shift')) document.getElementById('drv-shift').value = cleanDriverMasterText(driver.shift, 'Ca sáng (06:00 - 14:00)');
  setDriverOperationalStatus(driver);
  setDriverPhoto(driver.photo_url || driver.image_url || '');
  if (document.getElementById('driver-modal-dialog')) document.getElementById('driver-modal-dialog').style.display = 'flex';
};

window.editDriverRow = function (btn) {
  const tr = btn.closest('tr');
  if (!tr) return;
  currentEditingDriverRow = tr;
  if (typeof syncAllDynamicDropdowns === 'function') syncAllDynamicDropdowns();
  const tds = tr.querySelectorAll('td');

  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
  const titleSpan = document.getElementById('driver-modal-title-text');
  if (titleSpan) {
    titleSpan.innerText = lang === 'la' ? 'ແກ້ໄຂບຸກຄະລາກອນ ຄົນຂັບ / ຜູ້ຊ່ວຍຄົນຂັບ' : (lang === 'en' ? 'Edit Driver / Co-driver' : 'Chỉnh sửa nhân sự tài xế / phụ xe');
  }
  if (document.getElementById('driver-modal-dialog')) document.getElementById('driver-modal-dialog').style.display = 'flex';
};

window.deleteDriverRow = async function (btnOrId) {
  let id = btnOrId;
  if (typeof btnOrId !== 'string') {
    const tr = btnOrId.closest('tr');
    id = tr ? tr.querySelector('td')?.innerText.trim() : '';
  }
  if (!id) return;
  if (!confirm(`Sếp có chắc chắn muốn xóa nhân sự ${id} khỏi CSDL không?`)) return;
  try {
    const res = await fetch(`${API_BASE}/api/drivers/${encodeURIComponent(id)}`, { method: 'DELETE' });
    if (!res.ok) return baoLoiMayChu(res, `Xóa nhân sự ${id}`);
    showToast("Đã xóa nhân sự khỏi CSDL!");
    loadFioriDrivers();
    syncAllDynamicDropdowns();
  } catch (e) {
    return baoMatKetNoi(`Xóa nhân sự ${id}`, e);
  }
};

window.saveDriverModal = async function () {
  const id = document.getElementById('drv-id')?.value.trim() || '';
  const name = document.getElementById('drv-name')?.value.trim() || id;
  if (!name) {
    showToast("Vui lòng nhập mã và họ tên nhân sự!");
    return;
  }
  const role = document.getElementById('drv-role')?.value || 'Lái xe chính';
  const license = document.getElementById('drv-license')?.value || 'Hạng FC';
  const phone = document.getElementById('drv-phone')?.value || '';
  const vehicle = document.getElementById('drv-vehicle')?.value || 'Chưa gán';
  const shift = document.getElementById('drv-shift')?.value || 'Ca sáng (06:00 - 14:00)';
  const photoUrl = document.getElementById('drv-photo-url')?.value || '';

  const payload = {
    id: id || name,
    name: name,
    role: role,
    license_type: license,
    phone: phone,
    assigned_vehicle: vehicle,
    shift: shift,
    photo_url: photoUrl
  };

  try {
    const res = await fetch(`${API_BASE}/api/drivers`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    // That bai thi GIU form mo: dong no la xoa mat nhung gi vua nhap trong
    // khi chua ghi duoc gi.
    if (!res.ok) return baoLoiMayChu(res, `Lưu nhân sự ${name}`);
    showToast(`Đã lưu nhân sự vào CSDL: ${name}`);
    closeDriverModal();
    loadFioriDrivers();
    syncAllDynamicDropdowns();
  } catch (e) {
    return baoMatKetNoi(`Lưu nhân sự ${name}`, e);
  }
};

window.resetAllOrdersData = async function () {
  showToast('Để tránh xóa nhầm dữ liệu production, chức năng xóa hàng loạt đã được khóa. Nếu cần dọn dữ liệu demo, chạy script cleanup có kiểm soát trong backend/tests.');
};

/** Từ khóa lọc danh mục loại xe ở màn Công thức giá thành. */
let formulaVehicleTypeSearch = '';

/** "10000" -> "10 tấn"; "800" -> "800 kg". Đọc nhanh hơn một dãy số dài. */
function formatPayload(kg) {
  const value = Number(kg || 0);
  if (!value) return '';
  return value >= 1000 ? `${Math.round(value / 100) / 10} tấn` : `${Math.round(value)} kg`;
}

window.filterFormulaVehicleTypes = function (value) {
  formulaVehicleTypeSearch = String(value || '');
  window.renderDynamicFormulaVehicleTypes();
  const input = document.getElementById('formula-vehicle-type-search');
  if (input) {
    input.focus();
    input.setSelectionRange(input.value.length, input.value.length);
  }
};

/**
 * Xóa THẬT một loại xe khỏi cơ sở dữ liệu.
 *
 * Bản cũ chỉ gỡ thẻ khỏi màn hình rồi báo "Đã xóa Loại Xe khỏi danh mục" —
 * bản ghi vẫn nằm nguyên trong cơ sở dữ liệu, tải lại trang là nó hiện về.
 * Endpoint DELETE /api/vehicle-types/{id} đã có sẵn từ trước, chỉ là chưa bao
 * giờ được gọi.
 */
window.deleteVehicleTypeCard = async function (btn) {
  const card = btn.closest('.veh-type-card');
  const id = card?.dataset.vehicleTypeId || '';
  const name = card?.dataset.vehicleTypeName || id;
  if (!id) return;
  if (!confirm(`Xóa loại xe "${name}" khỏi Master Data?\n\nCác xe đang gán loại này sẽ mất định mức giá thành cho tới khi được gán loại khác.`)) return;

  btn.disabled = true;
  try {
    const res = await fetch(`${API_BASE}/api/vehicle-types/${encodeURIComponent(id)}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(`Máy chủ trả về ${res.status}`);
    const payload = await res.json().catch(() => ({}));
    // Máy chủ trả 200 kèm "Không tìm thấy" khi bản ghi đã biến mất — đừng báo
    // thành công cho một việc không xảy ra.
    if (String(payload.message || '').includes('Không tìm thấy')) {
      showToast(`Không tìm thấy loại xe ${name} trong cơ sở dữ liệu.`, 'error');
    } else {
      showToast(`Đã xóa loại xe ${name}.`, 'success');
    }
  } catch (error) {
    btn.disabled = false;
    showToast(`Chưa xóa được loại xe: ${error.message}`, 'error');
    return;
  }

  // Tải lại NẰM NGOÀI khối try ở trên, và là một việc riêng.
  //
  // Để chung thì một lỗi mạng lúc tải lại sẽ báo "Chưa xóa được loại xe"
  // trong khi việc xóa ĐÃ THÀNH CÔNG — lời nói dối ngược lại với lỗi cũ,
  // và cũng nguy hiểm như nhau: người dùng sẽ bấm xóa lại.
  try {
    const listRes = await fetch(`${API_BASE}/api/vehicle-types`);
    if (listRes.ok) vehTypes = await listRes.json();
    window.renderDynamicFormulaVehicleTypes();
    if (typeof syncAllDynamicDropdowns === 'function') syncAllDynamicDropdowns();
  } catch (error) {
    showToast('Đã xóa xong nhưng chưa tải lại được danh mục. Tải lại trang để xem đúng.', 'error');
  }
};

/**
 * Danh mục loại xe ở màn Công thức giá thành.
 *
 * Bản cũ mỗi thẻ chỉ có tên xe cộng hai dòng chữ "Loại phương tiện CSDL" và
 * "Cước định mức: CSDL" — không phải con số nào cả, chỉ là nhãn nói "lấy từ cơ
 * sở dữ liệu". Nhìn vào không biết xe đó tải bao nhiêu, đơn giá nền bao nhiêu,
 * nên phải bấm từng thẻ mới so sánh được.
 */
/**
 * Tai danh muc loai xe cho man Cong thuc gia thanh.
 *
 * Tai LAI moi lan mo tab thay vi chi khi trong: loai xe co the vua duoc them
 * hoac xoa o tab "3. Loai Phuong Tien", va hai tab nay dung chung mot danh muc.
 */
/* ==========================================================================
   Bảng công thức giá thành — một bảng làm cả hai việc
   --------------------------------------------------------------------------
   Bản trước tách làm hai khối: bảng đơn giá ở trên, khung công thức ở dưới —
   nên phải cuộn xuống mới nhập được, và sửa xong lại cuộn lên xem tổng.

   Nay mỗi DÒNG vừa là ô nhập đơn giá vừa là một hạng tử của công thức. Thêm
   cấu phần là thêm một dòng ngay tại chỗ. Xem js/formula-model.js để biết vì
   sao chọn mô hình hạng tử thay vì trình dựng biểu thức tự do.
   ========================================================================== */

/** Các hạng tử đang sửa. Mỗi loại xe một danh sách riêng. */
let costFormulaTerms = [];

/** Chuyến mẫu chỉ để XEM TRƯỚC. Báo giá thật dùng km của tuyến và tải trọng thật. */
let costSampleTrip = { km: 200, tonnes: 15, stops: 1 };
let costFormulaExpressions = null;

/** Năm ô ẩn `md-cost-*` vẫn là nơi các phần khác của ứng dụng đọc số. */
const BUILTIN_INPUT_IDS = {
  fuel: 'md-cost-fuel-rate',
  driver: 'md-cost-driver-allowance',
  toll: 'md-cost-toll-fee',
  wh: 'md-cost-warehouse-fee',
  rate: 'md-cost-freight-rate',
};

/**
 * Ghi ngược năm đơn giá dựng sẵn vào các ô cũ.
 *
 * Các chỗ khác trong ứng dụng (autoCalculateMasterDataCost, saveCostFormula)
 * đọc trực tiếp năm ô đó. Giữ chúng đồng bộ để không phải sửa cả loạt, trong
 * khi giao diện người dùng thấy là bảng mới.
 */
function syncBuiltinCostInputs() {
  Object.entries(BUILTIN_INPUT_IDS).forEach(([key, id]) => {
    const input = document.getElementById(id);
    if (!input) return;
    const term = costFormulaTerms.find(item => item.key === key);
    input.value = term ? Number(term.rate || 0).toLocaleString('vi-VN') : '0';
  });
}

/** Nạp hạng tử của loại xe đang chọn. */
window.loadCostFormulaTerms = function () {
  const key = activeCostFormulaKey || document.getElementById('md-formula-preset-select')?.value || '';
  const stored = masterFormulaStore[key] || {};
  costFormulaExpressions = stored.expressions || null;
  if (Array.isArray(stored.terms) && stored.terms.length) {
    costFormulaTerms = window.FormulaModel.normalize(stored.terms);
  } else {
    // Chưa lưu hạng tử nào thì dựng từ năm đơn giá đã có, để không mất cấu hình cũ.
    costFormulaTerms = window.FormulaModel.defaultTerms().map(term => ({
      ...term,
      rate: window.FormulaModel.toNumber(stored[term.key]),
    }));
  }
  window.renderCostFormulaEditor();
  savedCostFormulaDraft = JSON.stringify(currentCostFormulaDraft());
};

function persistCostFormulaTerms() {
  const key = activeCostFormulaKey || document.getElementById('md-formula-preset-select')?.value || '';
  if (!key) return;
  masterFormulaStore[key] = { ...(masterFormulaStore[key] || {}), terms: costFormulaTerms };
}

function afterTermChange() {
  costFormulaTerms = window.FormulaModel.normalize(costFormulaTerms);
  syncBuiltinCostInputs();
  persistCostFormulaTerms();
  window.renderCostFormulaEditor();
  if (typeof window.renderDynamicFormulaVehicleTypes === 'function') {
    window.renderDynamicFormulaVehicleTypes();
  }
  if (typeof window.autoCalculateMasterDataCost === 'function') {
    window.autoCalculateMasterDataCost('qt');
  }
}

window.setCostTermField = function (index, field, value) {
  const term = costFormulaTerms[index];
  if (!term) return;
  if (field === 'rate') term.rate = window.FormulaModel.toNumber(value);
  else if (field === 'label') term.label = String(value || '');
  else term[field] = String(value || '');
  // Sửa đơn giá hay nhãn thì KHÔNG vẽ lại cả bảng: vẽ lại giữa lúc đang gõ sẽ
  // làm mất con trỏ. Chỉ cập nhật phần tổng.
  // `cost_index` cũng gõ tay, nên cũng không vẽ lại cả bảng giữa lúc gõ.
  if (field === 'rate' || field === 'label' || field === 'cost_index') {
    syncBuiltinCostInputs();
    persistCostFormulaTerms();
    updateCostFormulaTotals();
    if (typeof window.autoCalculateMasterDataCost === 'function') window.autoCalculateMasterDataCost('qt');
    return;
  }
  afterTermChange();
};

/**
 * Xếp hàng tử để VẼ theo nhóm: mọi khoản CHI trước, mọi khoản THU sau — giữ thứ tự
 * tương đối và giữ `index` gốc (ô nhập gọi setCostTermField(index) đúng dòng).
 *
 * Trước đây bảng vẽ theo thứ tự lưu và chỉ chèn tiêu đề nhóm khi `kind` đổi so với
 * dòng liền trước — thêm một khoản chi SAU khoản thu là sinh ra hai tiêu đề
 * "CHI RA — GIÁ THÀNH". Chủ dự án chỉ đúng lỗi đó.
 */
function hangTheoNhom(rows) {
  const xep = (rows || []).map((row, index) => ({ row, index }))
    .sort((a, b) => ((a.row.kind === 'revenue') - (b.row.kind === 'revenue')) || (a.index - b.index));
  return xep.map((x, i) => ({ ...x, truoc: i ? xep[i - 1].row : null }));
}

window.addCostTerm = function () {
  // Khoản mới mặc định là CHI: chèn vào cuối nhóm chi (trước khoản thu đầu tiên),
  // để cả bảng lẫn bong bóng cấu hình đều thấy nó nằm đúng nhóm.
  const viTriThu = costFormulaTerms.findIndex(t => t.kind === 'revenue');
  const chenTai = viTriThu < 0 ? costFormulaTerms.length : viTriThu;
  costFormulaTerms.splice(chenTai, 0, {
    key: `custom_${Date.now().toString(36)}`,
    label: '',
    operator: 'add',
    factor: 'per_trip',
    // Mac dinh CHI PHI: phan lon cau phan phat sinh (boc xep, luu ca, phi diem
    // giao) la tien chi ra. Nham mot khoan chi thanh doanh thu se lam loi nhuan
    // trong ra cao hon thuc te.
    kind: 'cost',
    rate: 0,
    cost_index: '',
  });
  afterTermChange();
};

window.removeCostTerm = function (index) {
  const term = costFormulaTerms[index];
  if (!term) return;
  if (term.builtin) {
    showToast('Khoản mục dựng sẵn không xóa được. Đặt đơn giá về 0 nếu không dùng.', 'error');
    return;
  }
  costFormulaTerms.splice(index, 1);
  afterTermChange();
};

window.moveCostTerm = function (index, delta) {
  costFormulaTerms = window.FormulaModel.move(costFormulaTerms, index, delta);
  afterTermChange();
};

window.setCostSampleTrip = function (field, value) {
  costSampleTrip = { ...costSampleTrip, [field]: window.FormulaModel.toNumber(value) };
  updateCostFormulaTotals();
  if (typeof window.renderDynamicFormulaVehicleTypes === 'function') {
    window.renderDynamicFormulaVehicleTypes();
  }
};

/**
 * Bong bóng cấu hình đang mở hay không.
 *
 * Thẻ trên màn hình là chỗ ĐỌC: xem từng cấu phần thành bao nhiêu tiền và tổng
 * một chuyến mẫu là bao nhiêu. Việc SỬA nằm trong bong bóng, mở bằng chính câu
 * công thức. Trước đó bảng nhập và bảng tổng là hai khối rời nhau nên phải cuộn
 * xuống nhập rồi cuộn lên xem kết quả.
 */
let costFormulaPopoverOpen = false;

window.toggleCostFormulaPopover = function (force) {
  if (window.CostFormulaBuilder) {
    window.CostFormulaBuilder.toggle(force);
    return;
  }
  const next = typeof force === 'boolean' ? force : !costFormulaPopoverOpen;
  if (next === costFormulaPopoverOpen) return;
  costFormulaPopoverOpen = next;
  window.renderCostFormulaEditor();
  if (costFormulaPopoverOpen) {
    document.querySelector('#cf-pop input, #cf-pop select')?.focus();
  } else {
    document.getElementById('cf-trigger')?.focus();
  }
};

/**
 * Đóng bong bóng khi bấm ra ngoài hoặc bấm Esc.
 *
 * Gắn một lần ở tầng document: nếu gắn lại mỗi lần vẽ thì mỗi lần sửa một con
 * số lại thêm một trình lắng nghe, và sau vài chục lần gõ là hàng chục trình
 * lắng nghe cùng chạy.
 */
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && costFormulaPopoverOpen) window.toggleCostFormulaPopover(false);
});
document.addEventListener('mousedown', event => {
  if (!costFormulaPopoverOpen) return;
  // Lop nen nam NGOAI #cf-pop, nen bam vao nen la khong o trong hop thoai va
  // hop thoai dong lai — khong can xet rieng.
  if (event.target.closest('#cf-pop') || event.target.closest('#cf-trigger')) return;
  window.toggleCostFormulaPopover(false);
});

/**
 * Cập nhật riêng các con số, không dựng lại bảng — để không mất con trỏ.
 *
 * Cập nhật CẢ thẻ tóm tắt lẫn bong bóng: sửa trong bong bóng thì thẻ phía sau
 * phải đổi theo ngay, nếu không người dùng thấy hai con số khác nhau cho cùng
 * một cấu phần và không biết tin cái nào.
 */
function updateCostFormulaTotals() {
  const M = window.FormulaModel;
  if (!M) return;
  const result = M.evaluate(costFormulaTerms, costSampleTrip, costFormulaExpressions);
  const currency = masterCostCurrencyCode();
  const money = amount => formatWorkflowCurrencyAmount(amount, currency);
  const setText = (id, value) => {
    const node = document.getElementById(id);
    if (node) node.textContent = value;
  };

  result.rows.forEach((row, index) => {
    const multiplier = row.factor === 'per_trip' ? '1 chuyến' : `× ${row.multiplier.toLocaleString('vi-VN')}`;
    // Thẻ tóm tắt
    setText(`cf-sum-label-${index}`, row.label);
    setText(`cf-sum-sign-${index}`, row.operator === 'sub' ? '−' : '+');
    setText(`cf-sum-rate-${index}`, money(row.rate));
    setText(`cf-sum-unit-${index}`, row.unit);
    setText(`cf-sum-mul-${index}`, multiplier);
    setText(`cf-sum-amount-${index}`, money(row.amount));
    // Bong bóng
    setText(`cf-mul-${index}`, multiplier);
    setText(`cf-amount-${index}`, money(row.amount));
    setText(`cf-sum-kind-${index}`, M.KINDS[row.kind].short);
  });

  setText('cf-cost', money(result.cost));
  setText('cf-revenue', money(result.revenue));
  setText('cf-total', money(result.profit));
  setText('cf-margin', result.marginPct === null ? '' : ` · ${result.marginPct.toFixed(1)}%`);
  // Ba con so o chan hop thoai.
  setText('cf-pcost', money(result.cost));
  setText('cf-prevenue', money(result.revenue));
  setText('cf-pprofit', money(result.profit));
  setText('cf-pmargin', result.marginPct === null ? '' : `${result.marginPct.toFixed(1)}%`);
  setText('cf-perkm', `${money(result.perKm)}/km`);
  setText('cf-trip-note', `${costSampleTrip.km.toLocaleString('vi-VN')} km · ${costSampleTrip.tonnes.toLocaleString('vi-VN')} tấn`);
  setText('cf-text', M.toText(costFormulaTerms.filter(t => t.kind !== 'revenue')));
  setText('cfv2-cost-expression', M.toText(costFormulaTerms.filter(t => t.kind !== 'revenue')));
  setText('cfv2-revenue-expression', M.toText(costFormulaTerms.filter(t => t.kind === 'revenue')));

  const issues = document.getElementById('cf-issues');
  if (issues) issues.innerHTML = renderCostFormulaIssues();
  window.CostFormulaBuilder?.refresh();
}

/**
 * Công thức tự mâu thuẫn thì báo NGAY TRÊN THẺ, không chỉ trong bong bóng.
 *
 * Bong bóng đóng lại là lỗi biến mất khỏi mắt người dùng, rồi báo giá vẫn chạy
 * bằng công thức sai.
 */
function renderCostFormulaIssues() {
  const problems = window.FormulaModel.problems(costFormulaTerms);
  const errors = problems.filter(issue => issue.level === 'error');
  if (!errors.length) return '';
  return `<ul class="cf-issues">${errors.map(issue =>
    `<li><i class="fa-solid fa-triangle-exclamation" aria-hidden="true"></i> ${escapeHtml(issue.message)}</li>`
  ).join('')}</ul>`;
}

/**
 * Hộp thoại cấu hình công thức.
 *
 * Bản trước là một BẢNG BẢY CỘT (dấu · cấu phần · loại · đơn giá · nhân theo ·
 * thành tiền · nút). Bảy cột không bao giờ vừa một hộp thoại, nên thực tế trên
 * màn hình: cột "Thành tiền" bị cắt mất một nửa, cột nút (xóa, đổi thứ tự) nằm
 * hẳn ngoài vùng thấy được, và phải cuộn ngang mới đọc được con số của chính
 * dòng mình đang sửa.
 *
 * Nay mỗi cấu phần là MỘT THẺ hai dòng. Không còn cột nào để cắt, và câu chữ
 * đọc thành một câu:
 *
 *     ┌──────────────────────────────────────────────────────┐
 *     │ +  Chi phí xăng dầu /km          [Chi phí ▾]     ✕  │
 *     │    4.800  ×  [mỗi km ▾]  × 200  =  960.000 VNĐ  ↑↓  │
 *     └──────────────────────────────────────────────────────┘
 */
function renderCostFormulaPopover(result, money) {
  const M = window.FormulaModel;
  const factorOptions = Object.entries(M.FACTORS);

  const the = (row, index) => {
    const nhan = escapeHtml(row.label || 'khoản mục');
    return `
      <div class="cf-row cf-row--${escapeHtml(row.kind)} ${row.rate ? '' : 'is-zero'}">
        <div class="cf-row-top">
          <select class="cf-op" aria-label="Dấu của ${nhan}"
                  onchange="setCostTermField(${index}, 'operator', this.value)">
            ${Object.entries(M.OPERATORS).map(([key, op]) =>
              `<option value="${escapeHtml(key)}"${key === row.operator ? ' selected' : ''}>${escapeHtml(op.sign)}</option>`
            ).join('')}
          </select>

          ${row.builtin
            ? `<b class="cf-row-name">${escapeHtml(row.label)}</b>`
            : `<input class="cf-row-name" type="text" value="${escapeHtml(row.label)}"
                      placeholder="Tên khoản mục — ví dụ: Phí bốc xếp /tấn"
                      oninput="setCostTermField(${index}, 'label', this.value)"
                      aria-label="Tên khoản mục">`}

          <select class="cf-kind cf-kind-${escapeHtml(row.kind)}" aria-label="Loại của ${nhan}"
                  onchange="setCostTermField(${index}, 'kind', this.value)">
            ${Object.entries(M.KINDS).map(([key, kind]) =>
              `<option value="${escapeHtml(key)}"${key === row.kind ? ' selected' : ''}>${escapeHtml(kind.label)}</option>`
            ).join('')}
          </select>

          <button type="button" class="cf-del"
                  title="${row.builtin ? 'Khoản mục dựng sẵn — đặt đơn giá 0 nếu không dùng' : 'Xóa khoản mục'}"
                  aria-label="Xóa ${nhan}"
                  onclick="removeCostTerm(${index})" ${row.builtin ? 'disabled' : ''}>✕</button>
        </div>

        <div class="cf-row-calc">
          <input class="cf-rate" type="number" min="0" step="any" value="${Number(row.rate) || 0}"
                 oninput="setCostTermField(${index}, 'rate', this.value)"
                 aria-label="Đơn giá của ${nhan}">
          <span class="cf-x">×</span>
          <select class="cf-factor" aria-label="Hệ số nhân của ${nhan}"
                  onchange="setCostTermField(${index}, 'factor', this.value)">
            ${factorOptions.map(([key, factor]) =>
              `<option value="${escapeHtml(key)}"${key === row.factor ? ' selected' : ''}>${escapeHtml(factor.label)}</option>`
            ).join('')}
          </select>
          <span class="cf-mul" id="cf-mul-${index}">${row.factor === 'per_trip'
            ? '1 chuyến' : `× ${row.multiplier.toLocaleString('vi-VN')}`}</span>
          <span class="cf-eq">=</span>
          <b class="cf-amount" id="cf-amount-${index}">${money(row.amount)}</b>
          <span class="cf-move">
            <button type="button" title="Lên" aria-label="Đưa ${nhan} lên trên"
                    onclick="moveCostTerm(${index}, -1)" ${index === 0 ? 'disabled' : ''}>&#8593;</button>
            <button type="button" title="Xuống" aria-label="Đưa ${nhan} xuống dưới"
                    onclick="moveCostTerm(${index}, 1)" ${index === result.rows.length - 1 ? 'disabled' : ''}>&#8595;</button>
          </span>
        </div>
      </div>`;
  };

  return `
    <div class="cf-pop-backdrop" id="cf-pop-backdrop">
    <div class="cf-pop" id="cf-pop" role="dialog" aria-modal="true" aria-label="Cấu hình công thức giá thành">
      <div class="cf-pop-head">
        <b><i class="fa-solid fa-sliders" aria-hidden="true"></i> Cấu hình công thức</b>
        <button type="button" class="cf-pop-close" onclick="toggleCostFormulaPopover(false)"
                aria-label="Đóng cấu hình công thức" title="Đóng">✕</button>
      </div>

      <p class="cf-pop-hint">Mỗi thẻ là một khoản mục. Chọn <b>loại</b> để nói đó là tiền
        <b>chi ra</b> hay tiền <b>thu của khách</b> — hai thứ đó không cộng chung được.</p>

      <div class="cf-pop-body">
        ${result.rows.map(the).join('')}
        <button type="button" class="cf-add" onclick="addCostTerm()">
          <i class="fa-solid fa-plus" aria-hidden="true"></i> Thêm khoản mục
        </button>
      </div>

      <div class="cf-pop-foot">
        <div class="cf-sum">
          <div class="cf-sum-item cf-sum-item--cost">
            <span>Giá thành</span><b id="cf-pcost">${money(result.cost)}</b>
          </div>
          <div class="cf-sum-item cf-sum-item--revenue">
            <span>Cước thu khách</span><b id="cf-prevenue">${money(result.revenue)}</b>
          </div>
          <div class="cf-sum-item cf-sum-item--profit">
            <span>Lợi nhuận</span>
            <b id="cf-pprofit">${money(result.profit)}</b>
            <small id="cf-pmargin">${result.marginPct === null
              ? '' : `${result.marginPct.toFixed(1)}%`}</small>
          </div>
        </div>
        <div class="cf-sample">
          <label>Chuyến mẫu
            <span><input type="number" min="1" step="1" value="${costSampleTrip.km}"
                         oninput="setCostSampleTrip('km', this.value)" aria-label="Số km chuyến mẫu"> km</span>
          </label>
          <label>Hàng
            <span><input type="number" min="0" step="0.1" value="${costSampleTrip.tonnes}"
                         oninput="setCostSampleTrip('tonnes', this.value)" aria-label="Số tấn chuyến mẫu"> tấn</span>
          </label>
          <small>Chỉ để xem trước. Báo giá thật lấy <b>tổng km của tuyến</b> và <b>tải trọng đã nhập</b>.</small>
        </div>
      </div>
    </div>
    </div>`;
}

/*
   DANH MỤC ACC CODE — mã tài khoản kế toán của bên công nợ (anh Khang).

   Chủ dự án chốt: ô này là Ô CHỌN, danh mục do API của bên công nợ cấp
   (`GET /api/acc-codes` — máy chủ mình nối sang API đó qua biến
   `EPL_ACC_CODE_API`). API chưa có thì ô chọn ở trạng thái CHỜ: không tuỳ chọn,
   không tự sinh mã từ tên khoản mục. Giá trị đã lưu (nếu có) vẫn hiện để không
   mất dữ liệu, kể cả khi nó không nằm trong danh mục.
*/
let danhMucAccCode = null;          // null = chưa tải · {data, source, message}

let dangTaiAccCode = false;

async function napDanhMucAccCode() {
  if (dangTaiAccCode) return danhMucAccCode;
  dangTaiAccCode = true;
  try {
    const res = await fetch(`${API_BASE}/api/acc-codes`, { headers: financeAuthHeaders() });
    const goi = await res.json().catch(() => ({}));
    danhMucAccCode = res.ok ? goi : { data: [], source: 'error', message: `Máy chủ trả về ${res.status}` };
  } catch (err) {
    danhMucAccCode = { data: [], source: 'error', message: String(err && err.message || err) };
  } finally {
    dangTaiAccCode = false;
  }
  return danhMucAccCode;
}

function oChonAccCode(index, row) {
  const ds = (danhMucAccCode && Array.isArray(danhMucAccCode.data)) ? danhMucAccCode.data : [];
  const hienTai = String(row.cost_index || '').trim();
  const coDanhMuc = ds.length > 0;
  const mo = ds.find(x => x.code === hienTai);
  const trong = !danhMucAccCode ? 'đang tải danh mục…'
    : danhMucAccCode.source === 'unconfigured' ? 'chờ API mã tài khoản'
    : danhMucAccCode.source === 'error' ? 'không đọc được danh mục'
    : 'chọn Acc code';
  // Ô CHỌN CÓ TÌM thay cho <select> gần 500 dòng: danh mục của bên công nợ là
  // hệ thống tài khoản kế toán Lào (4 cấp), tên dài, không ai cuộn được. Ô hiện
  // MÃ đậm + tên ngắn; bấm mở bảng có ô tìm theo mã / tên / diễn giải.
  if (!coDanhMuc && !hienTai) {
    return `<button type="button" class="cfv2-acc cfv2-acc-cho" disabled
      title="${escapeHtml((danhMucAccCode && danhMucAccCode.message) || '')}">— ${escapeHtml(trong)} —</button>`;
  }
  // Tên tài khoản (tiếng Lào, đúng tên bên kế toán) đứng trên; diễn giải Việt ở dưới.
  const ten = mo ? (mo.name || mo.description) : (hienTai ? 'không có trong danh mục' : '');
  return `<button type="button" class="cfv2-acc ${hienTai ? '' : 'cfv2-acc-rong'} ${hienTai && !mo ? 'cfv2-acc-la' : ''}"
      aria-label="Acc code ${escapeHtml(row.label)}"
      title="${escapeHtml(mo ? (mo.code + ' · ' + mo.name + (mo.description ? ' — ' + mo.description : '')) : (hienTai || trong))}"
      onclick="moBangChonAccCode(${index}, this)">
      <b>${escapeHtml(hienTai || '—')}</b><small>${escapeHtml(hienTai ? ten : trong)}</small></button>`;
}

window.renderCostFormulaEditor = function () {
  // Lần đầu mở màn thì danh mục Acc code chưa có; tải rồi vẽ lại đúng một lần.
  if (danhMucAccCode === null && !dangTaiAccCode) {
    napDanhMucAccCode().then(() => { if (typeof window.renderCostFormulaEditor === 'function') window.renderCostFormulaEditor(); });
  }
  const host = document.getElementById('cost-formula-view');
  const M = window.FormulaModel;
  if (!host || !M) return;
  const currency = masterCostCurrencyCode();
  const result = M.evaluate(costFormulaTerms, costSampleTrip, costFormulaExpressions);
  const money = amount => formatWorkflowCurrencyAmount(amount, currency);

  // HAI CỘT: cấu phần bên trái, chuyến mẫu và kết quả bên phải.
  //
  // Bản cũ đặt ô nhập km/tấn BÊN TRONG hộp thoại sửa công thức, còn màn chính
  // chỉ ghi "ước tính một chuyến mẫu 200 km · 15 tấn" như một câu chú thích.
  // Nghĩa là muốn thử "cũng tuyến này nhưng 30 tấn thì lãi bao nhiêu" thì phải
  // mở hộp thoại sửa công thức — một việc nghe như sắp đổi cấu hình, trong khi
  // người dùng chỉ muốn xem thử.
  //
  // Ba con số kết quả cũng chuyển từ chân bảng sang khung phải, vì chúng là câu
  // TRẢ LỜI cho cặp km/tấn ở ngay trên, chứ không phải tổng của bảng cấu phần —
  // cước thu khách không phải một dòng chi phí được cộng lại.
  //
  // Mọi `id` giữ nguyên: `syncBuiltinCostInputs` và các hàm cập nhật tại chỗ
  // ghi thẳng vào `cf-cost`, `cf-revenue`, `cf-total`, `cf-margin`, `cf-perkm`,
  // `cf-trip-note`. Đổi id ở đây là chúng lặng lẽ không cập nhật gì nữa.
  host.innerHTML = `
    <div class="cf-head">
      <div class="cf-head-main">
        <h4><i class="fa-solid fa-calculator" aria-hidden="true"></i> Công thức</h4>
        <button type="button" class="cf-trigger" id="cf-trigger" aria-haspopup="dialog"
                aria-expanded="${costFormulaPopoverOpen ? 'true' : 'false'}"
                onclick="toggleCostFormulaPopover()">
          <span class="cf-equation" id="cf-text">${escapeHtml(M.toText(costFormulaTerms.filter(t => t.kind !== 'revenue')))}</span>
          <span class="cf-trigger-icon"><i class="fa-solid fa-sliders" aria-hidden="true"></i> Sửa công thức</span>
        </button>
        <div class="cfv2-equations">
          <div><b>Giá thành</b><span id="cfv2-cost-expression">${escapeHtml(M.toText(costFormulaTerms.filter(t => t.kind !== 'revenue')))}</span></div>
          <div><b>Cước</b><span id="cfv2-revenue-expression">${escapeHtml(M.toText(costFormulaTerms.filter(t => t.kind === 'revenue')))}</span></div>
          <div><b>Lợi nhuận</b><span>Cước thu khách − Giá thành</span></div>
        </div>
      </div>
    </div>

    <div id="cf-issues">${renderCostFormulaIssues()}</div>

    <div class="cf-shell">
    <div class="cf-main">
    <div class="cf-scroll">
      <table class="cf-table">
        <thead>
          <tr><th>Khoản mục</th><th title="Acc code — mã tài khoản kế toán của bên công nợ, chọn từ danh mục do API bên đó cấp">Acc code</th><th>Đơn giá · ${escapeHtml(currency)}</th><th id="th-base">Chuẩn của loại</th><th>Nhân với</th><th>Thành tiền · chuyến mẫu</th><th></th></tr>
        </thead>
        <tbody>
          ${hangTheoNhom(result.rows).map(({ row, index, truoc }) => `
            ${!truoc || truoc.kind !== row.kind ? `<tr class="cfv2-group"><td colspan="7">${row.kind === 'revenue' ? 'THU VỀ — CƯỚC KHÁCH' : 'CHI RA — GIÁ THÀNH'}</td></tr>` : ''}
            <tr class="${row.rate ? '' : 'is-zero'}">
              <td><span class="cf-sign" id="cf-sum-sign-${index}">${row.operator === 'sub' ? '−' : '+'}</span>
                  <span id="cf-sum-label-${index}">${escapeHtml(row.label)}</span>
                  <small class="cf-kind-tag cf-kind-${escapeHtml(row.kind)}" id="cf-sum-kind-${index}">${escapeHtml(M.KINDS[row.kind].short)}</small></td>
              <td>${oChonAccCode(index, row)}</td>
              <td class="cf-num"><input class="cfv2-rate-input" type="number" min="0" step="any" value="${row.rate}"
                  aria-label="Đơn giá ${escapeHtml(row.label)}" oninput="setCostTermField(${index}, 'rate', this.value)">
                  <span hidden id="cf-sum-rate-${index}">${money(row.rate)}</span>
                  <small id="cf-sum-unit-${index}">${escapeHtml(row.unit)}</small></td>
              <td><span class="cfb-source">chuẩn</span></td>
              <td class="cf-num" id="cf-sum-mul-${index}">× ${row.multiplier.toLocaleString('vi-VN')} ${
                escapeHtml((M.FACTORS[row.factor] || M.FACTORS.per_trip).unit.replace('/', ''))}</td>
              <td class="cf-num cf-amount" id="cf-sum-amount-${index}">${money(row.amount)}</td>
              <td><button class="cfb-remove" type="button" title="Xóa khoản mục" onclick="CostFormulaBuilder.remove(${index})"><i class="fa-solid fa-xmark"></i></button></td>
            </tr>`).join('')}
        <tr><td colspan="7"><button type="button" class="cfb-add" onclick="CostFormulaBuilder.add()">+ Thêm khoản mục</button></td></tr>
        </tbody>
      </table>
    </div>

    <p class="cf-note"><i class="fa-solid fa-circle-info" aria-hidden="true"></i>
      Bấm vào câu công thức để thêm, bớt hoặc đổi cách tính. Khi báo giá thật, hệ thống
      lấy <b>tổng km của tuyến đường</b> và <b>tải trọng thực tế</b> đã nhập.
      <b>Acc code dùng chung theo khoản mục</b>: đặt một lần ở một loại xe, các loại xe khác có cùng
      khoản mục tự kế thừa khi lưu, đổi ở đâu thì đổi chung; chỉ khoản mục mới phát sinh mới phải chọn Acc code.</p>
    </div>

    <aside class="cf-side" aria-label="Chuyến mẫu để xem trước">
      <div class="cf-side-head">
        <h5>Chuyến mẫu để xem trước</h5>
        <small>Đổi hai số này không ảnh hưởng báo giá thật.</small>
      </div>

      <div class="cf-side-input">
        <label>Quãng đường
          <span><input type="number" min="1" step="1" value="${costSampleTrip.km}"
                       oninput="setCostSampleTrip('km', this.value)"
                       aria-label="Số km của chuyến mẫu"> km</span>
        </label>
        <label>Hàng
          <span><input type="number" min="0" step="0.1" value="${costSampleTrip.tonnes}"
                       oninput="setCostSampleTrip('tonnes', this.value)"
                       aria-label="Số tấn của chuyến mẫu"> tấn</span>
        </label>
        <label>Điểm giao
          <span><input type="number" min="1" step="1" value="${costSampleTrip.stops || 1}"
                       oninput="setCostSampleTrip('stops', this.value)" aria-label="Số điểm giao chuyến mẫu"> điểm</span>
        </label>
        <label>Số chặng
          <span><input type="number" min="1" step="1" value="${costSampleTrip.legs || 1}" oninput="setCostSampleTrip('legs', this.value)" aria-label="Số chặng chuyến mẫu"> chặng</span>
        </label>
        <label>Giá trị hàng
          <span><input type="number" min="0" step="any" value="${costSampleTrip.value || 0}" oninput="setCostSampleTrip('value', this.value)" aria-label="Giá trị hàng chuyến mẫu"> ${escapeHtml(currency)}</span>
        </label>
      </div>

      <!-- Ba con số này là BA LOẠI khác nhau, cố ý không cộng vào một số:
           giá thành là tiền CHI ra, cước là tiền THU về, lợi nhuận là hiệu của
           hai cái đó. Cộng chung thì ra một số không phải giá thành cũng không
           phải giá bán. -->
      <dl class="cf-side-res">
        <div class="cf-res cf-res--cost">
          <dt>Giá thành <small>tiền CHI ra</small></dt>
          <dd id="cf-cost">${money(result.cost)}</dd>
        </div>
        <div class="cf-res cf-res--rev">
          <dt>Cước thu khách <small>tiền THU về</small></dt>
          <dd id="cf-revenue">${money(result.revenue)}</dd>
        </div>
        <div class="cf-res cf-res--profit">
          <dt>Lợi nhuận
            <small id="cf-trip-note">${costSampleTrip.km.toLocaleString('vi-VN')} km · ${costSampleTrip.tonnes.toLocaleString('vi-VN')} tấn</small></dt>
          <dd id="cf-total">${money(result.profit)}<small id="cf-margin">${
            result.marginPct === null ? '' : ` · ${result.marginPct.toFixed(1)}%`}</small></dd>
        </div>
        <div class="cf-res cf-res--perkm">
          <dt>Giá thành mỗi km <small>so được giữa các loại xe</small></dt>
          <dd id="cf-perkm">${money(result.perKm)}/km</dd>
        </div>
      </dl>
    </aside>
    </div>

    ${costFormulaPopoverOpen ? renderCostFormulaPopover(result, money) : ''}`;

  syncBuiltinCostInputs();
  window.CostFormulaBuilder?.mount();
};

/** Bảng chọn Acc code nổi cạnh ô: ô tìm + danh sách lọc theo mã/tên/diễn giải. */
window.moBangChonAccCode = function (index, nut) {
  const row = (Array.isArray(costFormulaTerms) && costFormulaTerms[index]) || {};
  window.moBangChonAccCodeChung(nut, String(row.cost_index || '').trim(), ma => {
    setCostTermField(index, 'cost_index', ma);
    if (typeof window.renderCostFormulaEditor === 'function') window.renderCostFormulaEditor();
  });
};

/** Bộ chọn Acc code dùng chung: `onChon(ma, banGhi)` — dùng cho công thức, danh mục khoản mục, … */
window.moBangChonAccCodeChung = function (nut, hienTai, onChon) {
  dongBangChonAccCode();
  const ds = (danhMucAccCode && Array.isArray(danhMucAccCode.data)) ? danhMucAccCode.data : [];
  hienTai = String(hienTai || '').trim();
  if (!ds.length && danhMucAccCode === null && !dangTaiAccCode) {
    napDanhMucAccCode().then(() => window.moBangChonAccCodeChung(nut, hienTai, onChon));
    return;
  }
  const bang = document.createElement('div');
  bang.className = 'cfv2-acc-pop';
  bang.id = 'cfv2-acc-pop';
  bang.innerHTML = `
    <div class="cfv2-acc-pop-hd">
      <input type="search" id="cfv2-acc-tim" placeholder="Gõ mã hoặc tên tài khoản… (${ds.length} mã)" autocomplete="off">
      <label class="cfv2-acc-chk" title="Chỉ tài khoản được phép hạch toán (cấp chi tiết)"><input type="checkbox" id="cfv2-acc-post" checked> chi tiết</label>
    </div>
    <div class="cfv2-acc-pop-ds" id="cfv2-acc-ds"></div>
    <div class="cfv2-acc-pop-ft">
      ${hienTai ? '<button type="button" class="cfv2-acc-bo" id="cfv2-acc-bo">Bỏ mã</button>' : '<span></span>'}
      <span class="cfv2-acc-hint">Enter chọn dòng đầu · Esc đóng</span>
    </div>`;
  document.body.appendChild(bang);
  const r = nut.getBoundingClientRect();
  const rong = 420;
  bang.style.left = Math.max(8, Math.min(r.left, window.innerWidth - rong - 8)) + 'px';
  bang.style.top = (r.bottom + 4 + window.scrollY) + 'px';

  const veDs = () => {
    const q = String(document.getElementById('cfv2-acc-tim').value || '').trim().toLowerCase();
    const chiChiTiet = document.getElementById('cfv2-acc-post').checked;
    const khop = ds.filter(x => (!chiChiTiet || x.postable !== false)
      && (!q || String(x.code).toLowerCase().startsWith(q) || String(x.name || '').toLowerCase().includes(q)
        || String(x.description || '').toLowerCase().includes(q)));
    const hien = khop.slice(0, 80);
    document.getElementById('cfv2-acc-ds').innerHTML = hien.length ? hien.map(x => `
      <div class="cfv2-acc-row ${x.code === hienTai ? 'on' : ''}" data-code="${escapeHtml(x.code)}" role="option">
        <b>${escapeHtml(x.code)}</b>
        <div><span>${escapeHtml(x.name || x.description)}</span>${x.description && x.name ? `<small>${escapeHtml(x.description)}</small>` : ''}</div>
      </div>`).join('') + (khop.length > hien.length ? `<div class="cfv2-acc-more">… còn ${khop.length - hien.length} mã, gõ thêm để lọc</div>` : '')
      : '<div class="cfv2-acc-more">Không có mã nào khớp.</div>';
    document.getElementById('cfv2-acc-ds').querySelectorAll('.cfv2-acc-row').forEach(d => d.addEventListener('click', () => chon(d.dataset.code)));
  };
  const chon = ma => {
    dongBangChonAccCode();
    onChon(ma, ds.find(x => x.code === ma) || null);
  };
  const tim = document.getElementById('cfv2-acc-tim');
  tim.addEventListener('input', veDs);
  document.getElementById('cfv2-acc-post').addEventListener('change', veDs);
  tim.addEventListener('keydown', ev => {
    if (ev.key === 'Escape') { dongBangChonAccCode(); return; }
    if (ev.key === 'Enter') { const d = document.querySelector('#cfv2-acc-ds .cfv2-acc-row'); if (d) chon(d.dataset.code); }
  });
  const bo = document.getElementById('cfv2-acc-bo');
  if (bo) bo.addEventListener('click', () => chon(''));
  veDs();
  setTimeout(() => { tim.focus(); document.addEventListener('mousedown', dongNeuNgoai, true); }, 0);
  function dongNeuNgoai(ev) { if (!bang.contains(ev.target) && ev.target !== nut) dongBangChonAccCode(); }
  bang._dong = () => document.removeEventListener('mousedown', dongNeuNgoai, true);
};

function dongBangChonAccCode() {
  const cu = document.getElementById('cfv2-acc-pop');
  if (cu) { if (typeof cu._dong === 'function') cu._dong(); cu.remove(); }
}


/* ==========================================================================
   Giá thành hai tầng — tầng thứ hai: từng chiếc xe
   --------------------------------------------------------------------------
   Công thức thuộc về LOẠI xe. Từng chiếc chỉ ghi đè vài con số khi thực tế
   khác đi — xe cũ tốn dầu hơn, xe trả góp gánh thêm khấu hao.

   Vì sao không cho mỗi chiếc một công thức riêng: đội xe khoảng 500 chiếc, nên
   đó là 500 công thức phải bảo trì. Đổi giá dầu phải sửa 500 chỗ, và rất dễ có
   xe bị bỏ sót rồi tính sai giá mà không ai biết.
   ========================================================================== */

/** Xe đang mở bảng ghi đè, và bản nháp đang sửa. */
let vehicleCostPanelId = '';
let vehicleCostDraft = null;

/**
 * Đếm số xe thuộc mỗi loại, để thẻ bên trái nói rõ "loại này có bao nhiêu xe".
 *
 * Nhận CẢ mã loại lẫn TÊN loại, vì `vehicles.type` trong dữ liệu thật có cả hai
 * kiểu: bản ghi cũ lưu tên ("Container 20FT"), bản ghi mới lưu mã
 * ("DEMO-VT-20FT"). Tầng nghiệp vụ đã tra theo cả hai
 * (`VehicleType.id == vehicle.type | VehicleType.name == vehicle.type`); chỗ này
 * so mỗi mã nên đếm sót.
 *
 * Hậu quả đo được: thẻ "Container 20FT" ghi "Chưa có xe nào thuộc loại này"
 * trong khi có đúng hai chiếc — và vì thế bảng ghi đè giá theo từng xe của loại
 * đó không mở được chiếc nào.
 */
function vehiclesOfType(typeId) {
  const loai = (vehTypes || []).find(t => String(t.id || '') === String(typeId));
  const ten = loai ? String(loai.name || '') : '';
  return (fioriVehicles || []).filter(v => {
    const cua_xe = String(v.type || '');
    return cua_xe === String(typeId) || (ten && cua_xe === ten);
  });
}

/**
 * Dòng "N chiếc xe" dưới mỗi thẻ loại xe, bấm được để mở tầng thứ hai.
 *
 * Vẽ riêng sau khi thẻ đã dựng, vì nó cần fioriVehicles vốn tải ở luồng khác.
 */
window.renderVehicleTypeFleetCounts = function () {
  (vehTypes || []).forEach(type => {
    const host = document.getElementById(`vt-fleet-${type.id}`);
    if (!host) return;
    const fleet = vehiclesOfType(type.id);
    if (!fleet.length) {
      host.innerHTML = '<span class="vt-fleet-empty">0 xe</span>';
      return;
    }
    const overridden = fleet.filter(v => vehicleOverrideCounts[v.id] > 0).length;
    host.innerHTML = `<button type="button" class="vt-fleet-btn"
        onclick="event.stopPropagation(); openVehicleCostList('${escapeJsAttr(type.id)}')">
      <i class="fa-solid fa-truck" aria-hidden="true"></i>
      <b>${fleet.length}</b> chiếc xe
      ${overridden ? `<em>${overridden} chiếc có giá riêng</em>` : ''}
      <i class="fa-solid fa-chevron-right" aria-hidden="true"></i>
    </button>
    <div class="cfv2-tree-vehicles">${fleet.slice(0, 12).map(v => `<button type="button" data-vehicle-cost-id="${escapeHtml(v.id)}"
      onclick="event.stopPropagation(); openVehicleCostEditor('${escapeJsAttr(v.id)}')">
      <span><b>${escapeHtml(v.id)}</b><small>${escapeHtml(v.brand || '')}</small></span>
      <em>${vehicleOverrideCounts[v.id] ? `${vehicleOverrideCounts[v.id]} ghi đè` : 'Kế thừa'}</em>
    </button>`).join('')}</div>`;
  });
  window.CostVehicleInline?.syncSelection();
};

/** Số cấu phần đã ghi đè của từng xe — nạp một lần để thẻ hiện được nhãn. */
let vehicleOverrideCounts = {};

window.loadVehicleOverrideCounts = async function () {
  const fleet = (fioriVehicles || []).map(v => v.id).filter(Boolean);
  if (!fleet.length) return;
  // Ở đội 500 xe, hỏi từng chiếc là 500 lệnh gọi. Chỉ hỏi những xe thuộc các
  // loại đang hiện trên màn hình.
  const shown = new Set((vehTypes || []).map(t => t.id));
  const target = (fioriVehicles || []).filter(v => shown.has(String(v.type || ''))).slice(0, 200);
  const results = await Promise.allSettled(target.map(async v => {
    const res = await fetch(`${API_BASE}/api/vehicles/${encodeURIComponent(v.id)}/cost`);
    if (!res.ok) return null;
    const data = (await res.json()).data || {};
    return [v.id, Number(data.override_count || 0)];
  }));
  results.forEach(item => {
    if (item.status === 'fulfilled' && item.value) vehicleOverrideCounts[item.value[0]] = item.value[1];
  });
  window.renderVehicleTypeFleetCounts();
};

/** Trạng thái của danh sách xe: đang lọc gì, đang xem trang nào. */
let vehicleCostListType = '';
let vehicleCostListSearch = '';
let vehicleCostListOnlyCustom = false;
let vehicleCostListShown = 24;

const VEHICLE_COST_PAGE = 24;

/**
 * Danh sách xe của một loại.
 *
 * Ở 500 xe thì một danh sách phẳng là vô dụng: không ai cuộn hết, và dựng hết
 * cũng nặng. Nên có tìm kiếm, lọc "chỉ xe đặt riêng", và tải dần từng trang —
 * cùng cách đã dùng cho lịch xe và bảng xếp ca.
 */
window.openVehicleCostList = function (typeId, options) {
  if (typeId !== undefined) {
    vehicleCostListType = String(typeId || '');
    if (!(options && options.keepFilters)) {
      vehicleCostListSearch = '';
      vehicleCostListOnlyCustom = false;
      vehicleCostListShown = VEHICLE_COST_PAGE;
    }
  }
  const host = document.getElementById('vehicle-cost-panel');
  if (!host) return;

  const type = (vehTypes || []).find(t => String(t.id) === String(vehicleCostListType));
  const all = vehiclesOfType(vehicleCostListType);
  const keyword = vehicleCostListSearch.trim().toLowerCase();
  const filtered = all.filter(v => {
    if (vehicleCostListOnlyCustom && !(vehicleOverrideCounts[v.id] > 0)) return false;
    if (!keyword) return true;
    return `${v.id} ${v.brand || ''} ${v.depot || ''}`.toLowerCase().includes(keyword);
  });
  const visible = filtered.slice(0, vehicleCostListShown);
  const customTotal = all.filter(v => vehicleOverrideCounts[v.id] > 0).length;

  host.hidden = false;
  host.innerHTML = `
    <div class="vc-head">
      <div>
        <h4><i class="fa-solid fa-layer-group" aria-hidden="true"></i> Giá thành từng xe</h4>
        <p>Loại <b>${escapeHtml(type?.name || vehicleCostListType)}</b> · ${all.length} chiếc,
           trong đó <b>${customTotal}</b> chiếc đặt giá riêng.
           Xe không đặt riêng thì <b>kế thừa</b> công thức của loại — sửa công thức là cả loại đổi theo.</p>
      </div>
      <button type="button" class="vc-close" title="Đóng" onclick="closeVehicleCostPanel()"><i class="fa-solid fa-xmark"></i></button>
    </div>

    <div class="vc-tools">
      <div class="vc-search">
        <i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i>
        <input id="vc-search" type="search" value="${escapeHtml(vehicleCostListSearch)}"
               placeholder="Tìm biển số, hãng xe, bãi..." oninput="filterVehicleCostList(this.value)"
               aria-label="Tìm xe">
      </div>
      <label class="vc-toggle">
        <input type="checkbox" ${vehicleCostListOnlyCustom ? 'checked' : ''}
               onchange="toggleVehicleCostOnlyCustom(this.checked)">
        <span>Chỉ xe đặt giá riêng${customTotal ? ` (${customTotal})` : ''}</span>
      </label>
    </div>

    ${filtered.length ? `
    <ul class="vc-fleet">
      ${visible.map(v => {
        const count = vehicleOverrideCounts[v.id] || 0;
        return `<li>
          <button type="button" class="vc-vehicle" onclick="openVehicleCostEditor('${escapeJsAttr(v.id)}')">
            <span class="vc-vehicle-id">${escapeHtml(v.id)}</span>
            <span class="vc-vehicle-sub">${escapeHtml(v.brand || '')}${v.depot ? ` · ${escapeHtml(v.depot)}` : ''}</span>
            <span class="vc-vehicle-state ${count ? 'is-custom' : ''}">
              <i class="fa-solid ${count ? 'fa-pen' : 'fa-link'}" aria-hidden="true"></i>
              ${count ? `${count} mục đặt riêng` : 'Kế thừa loại xe'}
            </span>
            <i class="fa-solid fa-chevron-right" aria-hidden="true"></i>
          </button>
        </li>`;
      }).join('')}
    </ul>
    <div class="vc-page">
      <span>Đang xem <b>${visible.length}</b> trên <b>${filtered.length}</b> xe${
        filtered.length !== all.length ? ` (lọc từ ${all.length})` : ''}</span>
      ${filtered.length > visible.length
        ? `<button type="button" onclick="showMoreVehicleCostRows()">
             <i class="fa-solid fa-chevron-down" aria-hidden="true"></i>
             Xem thêm ${Math.min(filtered.length - visible.length, VEHICLE_COST_PAGE)} xe
           </button>`
        : ''}
    </div>` : `<div class="vc-loading">Không có xe nào khớp bộ lọc.</div>`}`;
  host.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
};

window.filterVehicleCostList = function (value) {
  vehicleCostListSearch = String(value || '');
  vehicleCostListShown = VEHICLE_COST_PAGE;
  window.openVehicleCostList(undefined, { keepFilters: true });
  const input = document.getElementById('vc-search');
  if (input) { input.focus(); input.setSelectionRange(input.value.length, input.value.length); }
};

window.toggleVehicleCostOnlyCustom = function (on) {
  vehicleCostListOnlyCustom = Boolean(on);
  vehicleCostListShown = VEHICLE_COST_PAGE;
  window.openVehicleCostList(undefined, { keepFilters: true });
};

window.showMoreVehicleCostRows = function () {
  vehicleCostListShown += VEHICLE_COST_PAGE;
  window.openVehicleCostList(undefined, { keepFilters: true });
};

window.closeVehicleCostPanel = function () {
  const host = document.getElementById('vehicle-cost-panel');
  if (host) { host.hidden = true; host.innerHTML = ''; }
  vehicleCostPanelId = '';
  vehicleCostDraft = null;
};

/** Mở bảng ghi đè của MỘT chiếc xe. */
window.openVehicleCostEditor = async function (vehicleId) {
  if (window.CostVehicleInline) {
    if (hasUnsavedCostFormulaChanges()) {
      const action = await showCostFormulaUnsavedDialog();
      if (action === 'stay') return;
      if (action === 'save' && !(await window.saveCostFormula())) return;
      if (action === 'discard' && savedCostFormulaDraft) {
        const saved = JSON.parse(savedCostFormulaDraft);
        masterFormulaStore[activeCostFormulaKey] = {...masterFormulaStore[activeCostFormulaKey], ...saved,
          terms: JSON.parse(saved.terms), expressions: JSON.parse(saved.expressions || 'null')};
        window.loadCostFormulaTerms();
      }
    }
    return window.CostVehicleInline.open(vehicleId);
  }
  const host = document.getElementById('vehicle-cost-panel');
  if (!host) return;
  host.hidden = false;
  host.innerHTML = '<div class="vc-loading"><i class="fa-solid fa-circle-notch fa-spin"></i> Đang tải giá thành của xe...</div>';
  try {
    const res = await fetch(`${API_BASE}/api/vehicles/${encodeURIComponent(vehicleId)}/cost`);
    if (!res.ok) throw new Error(`Máy chủ trả về ${res.status}`);
    vehicleCostDraft = (await res.json()).data || null;
    vehicleCostPanelId = vehicleId;
  } catch (error) {
    host.innerHTML = `<div class="vc-loading">Chưa tải được giá thành của xe ${escapeHtml(vehicleId)}: ${escapeHtml(error.message)}
      <button type="button" class="sr-mini" onclick="openVehicleCostEditor('${escapeJsAttr(vehicleId)}')">Thử lại</button></div>`;
    return;
  }
  renderVehicleCostEditor();
};

function renderVehicleCostEditor() {
  const host = document.getElementById('vehicle-cost-panel');
  if (!host || !vehicleCostDraft) return;
  const currency = vehicleCostDraft.currency || 'VND';
  const data = vehicleCostDraft;

  host.innerHTML = `
    <div class="vc-head">
      <div>
        <h4><i class="fa-solid fa-truck" aria-hidden="true"></i> ${escapeHtml(data.vehicle_id)}</h4>
        <p>Loại <b>${escapeHtml(data.vehicle_type || 'chưa gán')}</b>.
           ${data.has_type_formula
             ? 'Các ô để trống nghĩa là <b>kế thừa</b> công thức của loại xe.'
             : '<b style="color:#b45309;">Loại xe này chưa có công thức</b> — hãy cấu hình ở panel bên phải trước.'}</p>
      </div>
      <button type="button" class="vc-close" title="Đóng giá riêng của xe"
              onclick="closeVehicleCostPanel()"><i class="fa-solid fa-xmark"></i></button>
    </div>

    <table class="vc-table">
      <thead>
        <tr>
          <th>Khoản mục chi phí</th>
          <th>Kế thừa từ loại xe</th>
          <th>Đặt riêng cho xe này</th>
          <th>Lý do</th>
        </tr>
      </thead>
      <tbody>
        ${data.components.map(row => `
          <tr class="${row.is_overridden ? 'is-custom' : ''}">
            <td><b>${escapeHtml(row.label)}</b></td>
            <td class="vc-inherited">${formatWorkflowCurrencyAmount(Number(row.inherited || 0), currency)}</td>
            <td>
              <input type="number" min="0" step="any"
                     id="vc-val-${escapeHtml(row.component)}"
                     value="${row.is_overridden ? Number(row.value) : ''}"
                     placeholder="Kế thừa"
                     oninput="markVehicleCostDirty()">
            </td>
            <td>
              <input type="text" id="vc-note-${escapeHtml(row.component)}"
                     value="${escapeHtml(row.note || '')}"
                     placeholder="Ví dụ: xe cũ, tốn dầu hơn"
                     oninput="markVehicleCostDirty()">
            </td>
          </tr>`).join('')}
      </tbody>
    </table>

    <p class="vc-hint"><i class="fa-solid fa-circle-info" aria-hidden="true"></i>
      Để trống ô "Đặt riêng" là xe quay về kế thừa. Sửa công thức của loại xe sẽ
      kéo theo mọi xe đang kế thừa, nhưng <b>không</b> đụng tới xe đã đặt riêng.</p>

    <div class="vc-actions">
      <button type="button" class="sr-mini" onclick="clearAllVehicleCostOverrides()">
        <i class="fa-solid fa-link" aria-hidden="true"></i> Cho xe này kế thừa hoàn toàn
      </button>
      <button type="button" class="fiori-btn" onclick="saveVehicleCostOverrides()">
        <i class="fa-solid fa-floppy-disk" aria-hidden="true"></i> Lưu giá riêng cho xe
      </button>
    </div>`;
}

window.markVehicleCostDirty = function () { /* giữ chỗ: ô nhập tự giữ giá trị */ };

window.clearAllVehicleCostOverrides = function () {
  if (!vehicleCostDraft) return;
  vehicleCostDraft.components.forEach(row => {
    const value = document.getElementById(`vc-val-${row.component}`);
    const note = document.getElementById(`vc-note-${row.component}`);
    if (value) value.value = '';
    if (note) note.value = '';
  });
};

window.saveVehicleCostOverrides = async function () {
  if (!vehicleCostDraft) return;
  const overrides = vehicleCostDraft.components.map(row => {
    const raw = document.getElementById(`vc-val-${row.component}`)?.value ?? '';
    if (String(raw).trim() === '') return null;   // để trống = kế thừa
    return {
      component: row.component,
      value: Number(raw),
      note: document.getElementById(`vc-note-${row.component}`)?.value || '',
    };
  }).filter(Boolean);

  try {
    const res = await fetch(`${API_BASE}/api/vehicles/${encodeURIComponent(vehicleCostDraft.vehicle_id)}/cost-overrides`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ overrides }),
    });
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(payload?.detail?.message || payload?.detail || `Máy chủ trả về ${res.status}`);
    vehicleOverrideCounts[vehicleCostDraft.vehicle_id] = overrides.length;
    showToast(overrides.length
      ? `Đã lưu ${overrides.length} mục giá riêng cho xe ${vehicleCostDraft.vehicle_id}.`
      : `Xe ${vehicleCostDraft.vehicle_id} quay về kế thừa công thức của loại xe.`, 'success');
    await window.openVehicleCostEditor(vehicleCostDraft.vehicle_id);
    window.renderVehicleTypeFleetCounts();
  } catch (error) {
    showToast(`Chưa lưu được giá riêng: ${error.message}`, 'error');
  }
};

window.loadVehTypesForFormulas = async function () {
  const container = document.getElementById('formula-vehicle-types-list');
  try {
    const res = await fetch(`${API_BASE}/api/vehicle-types`);
    if (res.ok) vehTypes = await res.json();
    else if (container && !(vehTypes || []).length) {
      container.innerHTML = `<div class="vt-empty"><p>Chưa tải được danh mục loại xe (máy chủ trả về ${res.status}).</p>
        <button type="button" onclick="loadVehTypesForFormulas()"><i class="fa-solid fa-rotate" aria-hidden="true"></i> Thử lại</button></div>`;
      return;
    }
  } catch (error) {
    // Khong tai duoc thi NOI RA, dung de man hinh khang dinh "chua co loai xe
    // nao" trong khi that ra chi la khong hoi duoc may chu.
    if (container && !(vehTypes || []).length) {
      container.innerHTML = `<div class="vt-empty"><p>Không kết nối được máy chủ để tải danh mục loại xe.</p>
        <button type="button" onclick="loadVehTypesForFormulas()"><i class="fa-solid fa-rotate" aria-hidden="true"></i> Thử lại</button></div>`;
      return;
    }
  }
  window.renderDynamicFormulaVehicleTypes();
  if (typeof window.loadCostFormulaTerms === 'function') window.loadCostFormulaTerms();
  if (typeof window.loadVehicleOverrideCounts === 'function') window.loadVehicleOverrideCounts();
  if (typeof syncAllDynamicDropdowns === 'function') syncAllDynamicDropdowns();
};

window.renderDynamicFormulaVehicleTypes = function () {
  const container = document.getElementById('formula-vehicle-types-list');
  if (!container) return;
  const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';

  const all = (vehTypes || []).filter(vt => vt?.id && vt?.name);
  const keyword = formulaVehicleTypeSearch.trim().toLowerCase();
  const types = keyword
    ? all.filter(vt => `${vt.id} ${vt.name} ${vt.fuel_type || ''}`.toLowerCase().includes(keyword)
        || vehiclesOfType(vt.id).some(v => String(v.id).toLowerCase().includes(keyword)))
    : all;

  // Con số này TRƯỚC ĐÂY viết cứng "4 Mẫu" trong index.html, nên nó nói dối cả
  // khi danh mục trống lẫn khi số thật khác 4 — màn hình tự mâu thuẫn: badge
  // ghi "4 Mẫu" ngay cạnh dòng chữ "Chưa có Loại Xe trong CSDL Master Data".
  const counter = document.getElementById('formula-vehicle-types-count');
  if (counter) {
    const word = lang === 'la' ? 'ແບບ' : lang === 'en' ? 'models' : 'mẫu';
    counter.innerText = keyword ? `${types.length}/${all.length} ${word}` : `${all.length} ${word}`;
  }

  const searchBox = all.length > 0
    ? `<div class="vt-search">
        <i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i>
        <input id="formula-vehicle-type-search" type="search" value="${escapeHtml(formulaVehicleTypeSearch)}"
               placeholder="Tìm loại xe hoặc biển số" oninput="filterFormulaVehicleTypes(this.value)" aria-label="Tìm loại xe hoặc biển số">
      </div>`
    : '';

  if (!all.length) {
    // Bản cũ ghi "Vui lòng thêm tại Tab 3!" — người dùng không đếm tab, và
    // cũng không bấm được vào một dòng chữ. Nay gọi đúng tên tab và mở thẳng.
    const emptyMsg = lang === 'la' ? 'ຍັງບໍ່ມີປະເພດລົດໃນ Master Data.'
      : lang === 'en' ? 'No vehicle types in Master Data yet.'
      : 'Chưa có loại xe nào trong Master Data.';
    const action = lang === 'la' ? 'ໄປທີ່ "3. ປະເພດພາຫະນະ"'
      : lang === 'en' ? 'Open "3. Vehicle Types"'
      : 'Mở tab "3. Loại Phương Tiện"';
    container.innerHTML = `<div class="vt-empty">
      <i class="fa-solid fa-truck-ramp-box" aria-hidden="true"></i>
      <p>${escapeHtml(emptyMsg)}</p>
      <button type="button" onclick="openVehicleTypesTab()">
        <i class="fa-solid fa-arrow-right" aria-hidden="true"></i> ${escapeHtml(action)}
      </button>
    </div>`;
    return;
  }

  if (!types.length) {
    container.innerHTML = `${searchBox}<div class="vt-empty"><p>Không có loại xe nào khớp "${escapeHtml(formulaVehicleTypeSearch)}".</p></div>`;
    return;
  }

  const delTitle = lang === 'la' ? 'ລຶບ' : lang === 'en' ? 'Delete' : 'Xóa loại xe này';
  const formulaKeys = [];

  const cards = types.map(vehicleType => {
    const formulaKey = ensureVehicleTypeFormula(vehicleType, masterCostCurrencyCode());
    formulaKeys.push(formulaKey);
    let vName = vehicleType.name;
    if (lang === 'la') {
      vName = vName.replace(/Xe tải thùng 10 tấn|Xe Tải 10 Tấn/gi, 'ລົດບັນທຸກ 10 ໂຕນ')
                   .replace(/Container Lạnh|Container Lệnh/gi, 'Container ຕູ້ເຢັນ');
    }

    // Thay hai dòng nhãn rỗng bằng CON SỐ THẬT, để so sánh được giữa các loại
    // xe mà không phải bấm vào từng thẻ.
    const facts = [
      formatPayload(vehicleType.max_weight) && { icon: 'fa-weight-hanging', text: formatPayload(vehicleType.max_weight), title: 'Tải trọng' },
      Number(vehicleType.volume_capacity_m3) && { icon: 'fa-cube', text: `${Number(vehicleType.volume_capacity_m3)} m³`, title: 'Thể tích thùng' },
      Number(vehicleType.pallet_capacity) && { icon: 'fa-pallet', text: `${Number(vehicleType.pallet_capacity)} pallet`, title: 'Số pallet' },
    ].filter(Boolean);

    // KHONG hien base_rate nua.
    //
    // base_rate chi duoc GHI mot lan luc tao loai xe va khong he duoc dung de
    // tinh bat cu thu gi trong ca he thong. Trong khi do nut "Luu Cau Hinh Gia
    // Thanh" o panel ben phai ghi vao BANG KHAC (cost_formulas), nen sua gia
    // ben phai thi con so tren the khong bao gio doi — hai con so nam canh nhau
    // trong nhu cung mot thu ma khong lien quan gi.
    //
    // Nay the hien dung cai dang duoc dung: chi phi xang dau / 1 km trong cong
    // thuc DA LUU, theo dung don vi tien te dang chon.
    const formula = masterFormulaStore[formulaKey] || {};
    const configured = formula.configured === true;
    const currency = masterCostCurrencyCode();
    // Tong chi phi mot chuyen mau. Nam cau phan co don vi khac nhau (d/km,
    // d/chuyen, d/kg) nen khong cong thang duoc — moi con so "tong" deu phai
    // kem gia dinh ve do dai chuyen va khoi luong hang.
    // Dung CHUNG mot mo hinh voi trinh sua cong thuc. Truoc do co hai module
    // tinh cung mot thu (CostEstimate va FormulaModel) — dung loai trung lap se
    // troi khoi nhau, giong phep kiem nang luc xe bi viet hai lan o dieu phoi.
    const terms = Array.isArray(formula.terms) && formula.terms.length
      ? formula.terms
      : window.FormulaModel.defaultTerms().map(term => ({
        ...term, rate: window.FormulaModel.toNumber(formula[term.key]),
      }));
    const estimate = window.FormulaModel
      ? window.FormulaModel.evaluate(terms, costSampleTrip, formula.expressions)
      : { total: 0, perKm: 0 };
    // Xăng dầu/km lấy từ `terms`, KHÔNG lấy từ `components`.
    //
    // `components` chỉ là chuỗi đã định dạng để hiển thị, và nó lệch với số
    // thật: công thức `Container 20FT` có `components.fuel = "6,250"` trong
    // khi `terms[].rate` là 4800. Hậu quả thấy ngay trên một ảnh chụp: thẻ
    // ghi "6.250 VNĐ/km", mà hộp thoại của chính thẻ đó hiện ô nhập 4800, và
    // dòng "Chi 1.610.000" ngay dưới lại đúng bằng 200 km × 4.800 + ba khoản
    // theo chuyến — tức mọi chỗ khác đều đã dùng 4.800.
    //
    // `terms` là thứ trình sửa công thức ghi vào, `FormulaModel.evaluate` đọc,
    // và backend dùng để tính giá thành. Nên thẻ phải đọc cùng nguồn đó.
    const termFuel = terms.find(term => term && term.key === "fuel");
    const fuelPerKm = termFuel
      ? window.FormulaModel.toNumber(termFuel.rate)
      : parseWorkflowMoneyValue(formula.fuel);
    return `
      <div class="veh-type-card" data-formula-key="${escapeHtml(formulaKey)}"
           data-vehicle-type-id="${escapeHtml(vehicleType.id)}" data-vehicle-type-name="${escapeHtml(vehicleType.name)}"
           onclick="requestCostFormulaContextChange(this.dataset.vehicleTypeId, masterCostCurrencyCode(), this)">
        <button type="button" class="vt-del" title="${escapeHtml(delTitle)}"
                onclick="event.stopPropagation(); deleteVehicleTypeCard(this);"><i class="fa-solid fa-trash"></i></button>
        <div class="vt-name"><i class="fa-solid fa-truck" aria-hidden="true"></i> ${escapeHtml(vName)}</div>
        <div class="vt-id">${escapeHtml(vehicleType.id)}</div>
        ${facts.length ? `<div class="vt-facts">${facts.map(fact =>
          `<span title="${escapeHtml(fact.title)}"><i class="fa-solid ${fact.icon}" aria-hidden="true"></i> ${escapeHtml(fact.text)}</span>`
        ).join('')}</div>` : ''}
        <div class="vt-rate">${configured
          ? `<b>${formatWorkflowCurrencyAmount(estimate.profit, currency)}</b> <small>lợi nhuận/chuyến mẫu${
               estimate.marginPct === null ? '' : ` · ${estimate.marginPct.toFixed(1)}%`}</small>
             <span class="vt-flag vt-flag--ok"><i class="fa-solid fa-circle-check" aria-hidden="true"></i> Đã cấu hình</span>
             <div class="vt-breakdown">
               <span title="Cước thu của khách cho chuyển mẫu">
                 <i class="fa-solid fa-arrow-down" aria-hidden="true"></i>
                 Thu ${formatWorkflowCurrencyAmount(estimate.revenue, currency)}
               </span>
               <span title="Giá thành chuyển mẫu — tổng tiền chi ra">
                 <i class="fa-solid fa-arrow-up" aria-hidden="true"></i>
                 Chi ${formatWorkflowCurrencyAmount(estimate.cost, currency)}
               </span>
               <span title="Giá thành mỗi km — so được giữa các loại xe">
                 <i class="fa-solid fa-route" aria-hidden="true"></i>
                 ${formatWorkflowCurrencyAmount(estimate.perKm, currency)}/km
               </span>
               <span title="Chi phí xăng dầu trên 1 km">
                 <i class="fa-solid fa-gas-pump" aria-hidden="true"></i>
                 ${formatWorkflowCurrencyAmount(fuelPerKm, currency)}/km
               </span>
             </div>`
          : `<span class="vt-flag vt-flag--todo"><i class="fa-solid fa-circle-exclamation" aria-hidden="true"></i> Chưa cấu hình công thức</span>`}</div>
        <div class="vt-fleet" id="vt-fleet-${escapeHtml(vehicleType.id)}"></div>
      </div>`;
  }).join('');

  // Noi ro tung con so tren the la gi. Ban truoc chi noi "so tien tren the la
  // uoc tinh mot chuyen mau", ma the hien MOT tong gop ca chi phi lan doanh
  // thu — mot con so khong phai gia thanh cung khong phai gia ban.
  const sampleNote = `<p class="vt-sample">Các số trên thẻ là <b>ước tính một chuyến mẫu</b>
    ${costSampleTrip.km.toLocaleString('vi-VN')} km · ${costSampleTrip.tonnes.toLocaleString('vi-VN')} tấn:
    <b>lợi nhuận</b> = cước thu khách − giá thành.
    Đổi hai số đó ở khung <b>Chuyến mẫu</b> bên phải thì cả các thẻ này tính lại theo.</p>`;
  container.innerHTML = searchBox + cards;

  // Tang thu hai: moi the co mot dong "N chiec xe" bam duoc.
  if (typeof window.renderVehicleTypeFleetCounts === 'function') window.renderVehicleTypeFleetCounts();

  const currentFormulaKey = document.getElementById('md-formula-preset-select')?.value;
  const firstFormulaKey = formulaKeys.includes(currentFormulaKey) ? currentFormulaKey : formulaKeys[0];
  const firstCard = Array.from(container.querySelectorAll('[data-formula-key]'))
    .find(card => card.dataset.formulaKey === firstFormulaKey);
  if (firstFormulaKey && firstCard) {
    if (firstFormulaKey !== activeCostFormulaKey) window.selectFormulaVehicleType(firstFormulaKey, firstCard, { notify: false });
    else firstCard.classList.add('active');
  }
};

/** Mở thẳng tab Loại Phương Tiện thay vì bảo người dùng tự đi tìm "Tab 3". */
window.openVehicleTypesTab = function () {
  const button = document.querySelector('[onclick*="md-tab-veh-types"]');
  if (button) switchMasterDataTab('md-tab-veh-types', button);
};

// --- CUSTOMER MANAGEMENT LOGIC (MASTER DATA TAB 6 & DROPDOWNS) ---
window.loadCustomerList = async function () {
  try {
    const res = await fetch(`${API_BASE}/api/customers`);
    if (!res.ok) return baoLoiMayChu(res, 'Nạp danh sách khách hàng');
    eplCustomers = await res.json();
    renderCustomerList(eplCustomers);
    if (typeof syncAllDynamicDropdowns === 'function') syncAllDynamicDropdowns();
  } catch (e) {
    return baoMatKetNoi('Nạp danh sách khách hàng', e);
  }
};

window.renderCustomerList = function (data) {
  const tbody = document.getElementById('customers-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  if (!data || data.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 20px; color: #64748b;">Chưa có khách hàng nào trong CSDL. Bấm "+ Thêm Khách Hàng Mới" để tạo!</td></tr>';
    return;
  }
  data.forEach(c => {
    tbody.insertAdjacentHTML('beforeend', `
      <tr style="border-bottom: 1px solid #f1f5f9; transition: background 0.15s ease;" onmouseover="this.style.background='#f8fafc'" onmouseout="this.style.background='transparent'">
        <td style="padding: 14px 18px; font-weight: 700; color: #2563eb;">${c.id}</td>
        <td style="padding: 14px 18px; font-weight: 700; color: #0f172a;">${escapeHtml(c.name)}</td>
        <td style="padding: 14px 18px;"><span style="background: #eff6ff; color: #2563eb; padding: 3px 10px; border-radius: 12px; font-weight: 700; font-size: 0.78rem;">${c.type || 'Account'}</span></td>
        <td style="padding: 14px 18px; color: #334155; font-weight: 600;">${escapeHtml(c.contact_person || '-')}</td>
        <td style="padding: 14px 18px; color: #16a34a; font-weight: 700;">${c.phone || '-'}</td>
        <td style="padding: 14px 18px; color: #475569; font-weight: 500;">${escapeHtml(c.address || '-')}</td>
        <td style="padding: 14px 18px; text-align: center; white-space: nowrap;">
          <button class="fiori-btn fiori-btn-secondary" style="padding: 4px 10px; font-size: 0.78rem; margin-right: 6px;" onclick="openCustomerModal('${c.id}')" title="Sửa"><i class="fa-solid fa-pen"></i></button>
          <button class="fiori-btn" style="background:#ef4444; border-color:#ef4444; padding: 4px 10px; font-size: 0.78rem;" onclick="deleteCustomer('${c.id}')" title="Xóa"><i class="fa-solid fa-trash"></i></button>
        </td>
      </tr>
    `);
  });
};

window.filterCustomerList = function () {
  const query = (document.getElementById('search-customers-input')?.value || '').toLowerCase();
  const filtered = (eplCustomers || []).filter(c =>
    (c.id || '').toLowerCase().includes(query) ||
    (c.name || '').toLowerCase().includes(query) ||
    (c.phone || '').toLowerCase().includes(query)
  );
  renderCustomerList(filtered);
};

/**
 * Mã khách hàng kế tiếp.
 *
 * Trước đây chỗ này là `CUS-00${eplCustomers.length + 1}`, tức đếm SỐ LƯỢNG
 * khách rồi cộng một. Hai chỗ hỏng:
 *
 *   · Xóa một khách ở giữa là mã kế tiếp TRÙNG với mã đang có. Có CUS-001,
 *     CUS-002, CUS-003; xóa CUS-002 thì còn hai khách, và mã đề xuất là
 *     CUS-003 — trùng đúng khách còn lại.
 *   · Quá 9 khách thì thành `CUS-0010`, dài hơn một chữ số so với CUS-001,
 *     nên sắp xếp theo chuỗi cho ra thứ tự sai.
 *
 * Nay lấy số LỚN NHẤT đang dùng rồi cộng một, và đệm số 0 theo đúng bề rộng
 * của các mã đang có.
 */
function maKhachHangKeTiep() {
  const ds = Array.isArray(eplCustomers) ? eplCustomers : [];
  let lonNhat = 0;
  let beRong = 3;
  ds.forEach(kh => {
    const m = String(kh?.id || '').match(/^CUS-(\d+)$/);
    if (!m) return;
    lonNhat = Math.max(lonNhat, parseInt(m[1], 10));
    beRong = Math.max(beRong, m[1].length);
  });
  return `CUS-${String(lonNhat + 1).padStart(beRong, '0')}`;
}

window.openCustomerModal = function (id = null) {
  const modal = document.getElementById('customer-form-modal');
  if (modal) modal.style.display = 'flex';

  if (id) {
    document.getElementById('cus-modal-title').innerHTML = '<i class="fa-solid fa-pen" style="font-size: 1.3rem;"></i> <span>Chỉnh Sửa Khách Hàng</span>';
    document.getElementById('cus-edit-mode').value = 'edit';
    const c = (eplCustomers || []).find(item => item.id === id);
    if (c) {
      document.getElementById('cus-id').value = c.id;
      document.getElementById('cus-id').disabled = true;
      document.getElementById('cus-name').value = c.name || '';
      document.getElementById('cus-type').value = c.type || 'Account';
      document.getElementById('cus-contact').value = c.contact_person || '';
      document.getElementById('cus-phone').value = c.phone || '';
      document.getElementById('cus-address').value = c.address || '';
    }
  } else {
    document.getElementById('cus-modal-title').innerHTML = '<i class="fa-solid fa-user-plus" style="font-size: 1.3rem;"></i> <span>Thêm Mới Khách Hàng</span>';
    document.getElementById('cus-edit-mode').value = 'create';
    document.getElementById('cus-id').value = maKhachHangKeTiep();
    document.getElementById('cus-id').disabled = false;
    document.getElementById('cus-name').value = '';
    document.getElementById('cus-type').value = 'Account';
    document.getElementById('cus-contact').value = '';
    document.getElementById('cus-phone').value = '';
    document.getElementById('cus-address').value = '';
  }
};

window.closeCustomerModal = function () {
  const modal = document.getElementById('customer-form-modal');
  if (modal) modal.style.display = 'none';
};

window.saveCustomer = async function () {
  const mode = document.getElementById('cus-edit-mode').value;
  const cid = document.getElementById('cus-id').value.trim();
  const name = document.getElementById('cus-name').value.trim();
  if (!cid || !name) {
    showToast('⚠️ Vui lòng nhập đầy đủ Mã và Tên Khách hàng!');
    return;
  }

  const payload = {
    id: cid,
    name: name,
    type: document.getElementById('cus-type').value,
    contact_person: document.getElementById('cus-contact').value.trim(),
    phone: document.getElementById('cus-phone').value.trim(),
    address: document.getElementById('cus-address').value.trim()
  };

  try {
    const url = mode === 'edit' ? `${API_BASE}/api/customers/${cid}` : `${API_BASE}/api/customers`;
    const method = mode === 'edit' ? 'PUT' : 'POST';
    const res = await fetch(url, {
      method: method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      showToast(mode === 'edit' ? `✅ Cập nhật Khách hàng "${name}" thành công!` : `✅ Thêm Khách hàng mới "${name}" vào CSDL thành công!`);
      closeCustomerModal();
      loadCustomerList();
    } else {
      const err = await res.json();
      showToast(`⚠️ Lỗi: ${err.detail || 'Không thể lưu thông tin Khách hàng'}`);
    }
  } catch (e) {
    console.error("Save Customer Error", e);
    showToast("⚠️ Lỗi kết nối CSDL khi lưu Khách hàng!");
  }
};

window.deleteCustomer = async function (id) {
  if (!confirm(`Bạn có chắc chắn muốn xóa Khách hàng "${id}" khỏi CSDL?`)) return;
  try {
    const res = await fetch(`${API_BASE}/api/customers/${id}`, { method: 'DELETE' });
    // May chu tu choi (vi du 409 khi khach con don tham chieu) thi PHAI noi ra.
    // Truoc day khong co nhanh else, nen bam Xoa la khong co gi xay ra va
    // khong mot thong bao nao.
    if (!res.ok) return baoLoiMayChu(res, `Xóa khách hàng ${id}`);
    showToast(`🗑️ Đã xóa Khách hàng ${id} khỏi CSDL!`);
    loadCustomerList();
  } catch (e) {
    return baoMatKetNoi(`Xóa khách hàng ${id}`, e);
  }
};

window.syncAllDynamicDropdowns = async function () {
  try {
    const [vehicles, resD, routes, resC, deliveryOrders, resVT] = await Promise.all([
      fetchAllPaginated(`${API_BASE}/api/vehicles?paginated=true`, 200).catch(() => null),
      fetch(`${API_BASE}/api/drivers`).catch(() => null),
      fetchAllPaginated(`${API_BASE}/api/routes?paginated=true`, 200).catch(() => null),
      fetch(`${API_BASE}/api/customers`).catch(() => null),
      fetchAllPaginated(`${API_BASE}/api/delivery-orders`, 200).catch(() => null),
      fetch(`${API_BASE}/api/vehicle-types`).catch(() => null)
    ]);

    if (Array.isArray(vehicles)) fioriVehicles = vehicles;
    if (resD && resD.ok) fioriDrivers = await resD.json();
    if (Array.isArray(routes)) eplRoutes = routes;
    if (resC && resC.ok) eplCustomers = await resC.json();
    if (resVT && resVT.ok) vehTypes = await resVT.json();
    if (typeof loadCostFormulasFromBackend === 'function') await loadCostFormulasFromBackend();
    eplDeliveryOrders = Array.isArray(deliveryOrders) ? deliveryOrders : [];
    if (typeof populateCloseoutDOSelector === 'function') populateCloseoutDOSelector();
    await refreshDispatchTrackingMap(eplDeliveryOrders);

    // 1. Populate Driver Modal Vehicle Dropdown (#drv-vehicle)
    const modalDrvVeh = document.getElementById('drv-vehicle');
    if (modalDrvVeh) {
      const cur = modalDrvVeh.value;
      const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
      const unassignedText = lang === 'la' ? '⚠️ ຍັງບໍ່ໄດ້ມອບໝາຍລົດ' : (lang === 'en' ? '⚠️ Unassigned Vehicle' : '⚠️ Chưa phân công xe');
      modalDrvVeh.innerHTML = `<option value="Chưa gán">${unassignedText}</option>`;
      (fioriVehicles || []).forEach(v => {
        let typeStr = v.type || '';
        if (lang === 'la') {
          typeStr = typeStr.replace(/Xe tải thùng 10 tấn|Xe Tải 10 Tấn/gi, 'ລົດບັນທຸກ 10 ໂຕນ')
                           .replace(/Container Lạnh|Container Lệnh/gi, 'Container ຕູ້ເຢັນ');
        }
        modalDrvVeh.insertAdjacentHTML('beforeend', `<option value="${v.id}">${v.id} (${escapeHtml(v.brand || (lang === 'la' ? 'àº¥àº»àº”' : 'Xe'))} - ${typeStr})</option>`);
      });
      if (cur) modalDrvVeh.value = cur;
    }

    // 2. Populate Vehicle Select Dropdowns (#dispatch-vehicle, #inc-veh-id)
    ['dispatch-vehicle', 'inc-veh-id'].forEach(id => {
      const sel = document.getElementById(id);
      if (sel) {
        const cur = sel.value;
        const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
        const chooseVehText = lang === 'la' ? '-- ເລືອກພາຫະນະຂົນສົ່ງ --' : (lang === 'en' ? '-- Select Transport Vehicle --' : '-- Chọn Xe Vận Chuyển --');
        const capLabel = lang === 'la' ? 'ນ້ຳໜັກບັນທຸກ' : (lang === 'en' ? 'Capacity' : 'Tải trọng');
        sel.innerHTML = `<option value="">${chooseVehText}</option>`;
        (fioriVehicles || []).forEach(v => {
          let typeStr = v.type || '';
          if (lang === 'la') {
            typeStr = typeStr.replace(/Xe tải thùng 10 tấn|Xe Tải 10 Tấn/gi, 'ລົດບັນທຸກ 10 ໂຕນ')
                             .replace(/Container Lạnh|Container Lệnh/gi, 'Container ຕູ້ເຢັນ');
          }
          sel.insertAdjacentHTML('beforeend', `<option value="${v.id}">${v.id} (${escapeHtml(v.brand || '')} ${typeStr}) - ${capLabel}: ${(v.weight_capacity || 0).toLocaleString()} kg</option>`);
        });
        if (cur) sel.value = cur;
      }
    });

    // 3. Populate Driver Select Dropdowns (#dispatch-driver)
    const doDrvSel = document.getElementById('dispatch-driver');
    if (doDrvSel) {
      const cur = doDrvSel.value;
      const lang = (typeof currentLang !== 'undefined') ? currentLang : 'vi';
      const chooseDrvText = lang === 'la' ? '-- ເລືອກຄົນຂັບປະຕິບັດງານ --' : (lang === 'en' ? '-- Select Assigned Driver --' : '-- Chọn Tài Xế Vận Hành --');
      doDrvSel.innerHTML = `<option value="">${chooseDrvText}</option>`;
      (fioriDrivers || []).forEach(d => {
        const lic = cleanDriverMasterText(d.license_type, lang === 'la' ? 'àºŠàº±à»‰àº™ FC' : 'FC');
        doDrvSel.insertAdjacentHTML('beforeend', `<option value="${d.id}">${d.id} - ${escapeHtml(d.name)} (${lic})</option>`);
      });
      if (cur) doDrvSel.value = cur;
    }

    // 4. Populate Route Select Dropdowns (#qt-route, #do-route, #md-saved-routes-select)
    ['qt-route', 'do-route', 'md-saved-routes-select'].forEach(id => {
      const sel = document.getElementById(id);
      if (sel) {
        const cur = sel.value;
        sel.innerHTML = '<option value="">-- Chọn Tuyến Đường --</option>';
        (eplRoutes || []).forEach(r => {
          sel.insertAdjacentHTML('beforeend', `<option value="${r.id}">${r.id}: ${escapeHtml(r.name || r.id)} (${r.distance_km || 0} km)</option>`);
        });
        if (cur) sel.value = cur;
      }
    });

    // 5. Populate Customer Select Dropdowns (#qt-customer, #do-customer, #m-qt-customer)
    ['qt-customer', 'do-customer', 'm-qt-customer'].forEach(id => {
      const sel = document.getElementById(id);
      if (sel) {
        const cur = sel.value;
        if (eplCustomers && eplCustomers.length > 0) {
          sel.innerHTML = eplCustomers.map(c => `<option value="${c.id}">${c.id} - ${escapeHtml(c.name)}</option>`).join('');
        } else {
          sel.innerHTML = '<option value="">-- Chưa có khách hàng trong CSDL --</option>';
        }
        if (cur) sel.value = cur;
      }
    });

    // 5.5 Populate Delivery Order & Vehicle Selects for Incidents (#inc-do-id, #inc-veh-id)
    const doIncSel = document.getElementById('inc-do-id');
    if (doIncSel) {
      const cur = doIncSel.value;
      // `dos` KHÔNG tồn tại: biến chứa danh sách lệnh giao hàng ở hàm này tên
      // là `deliveryOrders` (xem `Promise.all` ở đầu hàm). Dòng cũ ném
      // ReferenceError, và vì nó nằm giữa hàm nên MỌI ô chọn phía sau —
      // loại xe, tiền tệ, loại hàng, danh sách xe cho công thức giá thành —
      // đều không được nạp. Trước đây `catch` chỉ ghi console nên không ai
      // thấy; giờ nó báo ra và lộ đúng chỗ này.
      const dsDon = Array.isArray(deliveryOrders) ? deliveryOrders : (eplDeliveryOrders || []);
      if (dsDon.length > 0) {
        doIncSel.innerHTML = dsDon.map(d => `<option value="${escapeHtml(d.id)}">${escapeHtml(d.id)} (${escapeHtml(d.customer_id || '')} - ${escapeHtml(d.route_id || '')})</option>`).join('');
      } else {
        doIncSel.innerHTML = '<option value="">-- Chưa có lệnh giao hàng trong CSDL --</option>';
      }
      if (cur) doIncSel.value = cur;
    }

    const vehIncSel = document.getElementById('inc-veh-id');
    if (vehIncSel) {
      const cur = vehIncSel.value;
      if (fioriVehicles && fioriVehicles.length > 0) {
        vehIncSel.innerHTML = fioriVehicles.map(v => `<option value="${v.id}">${v.id} (${escapeHtml(v.brand || 'Xe')} - ${v.type || ''})</option>`).join('');
      } else {
        vehIncSel.innerHTML = '<option value="">-- Chưa có xe trong CSDL --</option>';
      }
      if (cur) vehIncSel.value = cur;
    }

    // 6. Populate Vehicle Types (#qt-cargo-type, #fiori-veh-type) from CSDL Master Data
    ['qt-cargo-type', 'fiori-veh-type'].forEach(id => {
      const sel = document.getElementById(id);
      if (sel) {
        const cur = sel.value;
        if (vehTypes && vehTypes.length > 0) {
          // GIA TRI LA MA LOAI XE, nhan la ten. Xe luu ma (may chu chuan hoa khi
          // luu), nen o chon theo ten thi mo xe ra thay trong — dung loi chu du an
          // gap: "loai phuong tien bi sai / chua co loai xe".
          sel.innerHTML = `<option value="">-- Chọn loại xe phù hợp --</option>` + vehTypes.map(vt => `<option value="${escapeHtml(vt.id)}">${escapeHtml(vt.name)} (${vt.max_weight || 0} kg - ${vt.volume_capacity_m3 || 0} m³ - ${vt.pallet_capacity || 0} pallet)</option>`).join('');
        } else {
          sel.innerHTML = '<option value="">-- Chưa có loại xe trong CSDL --</option>';
        }
        if (cur) sel.value = cur;
      }
    });

    // 6.7 Populate Panoramic Weight Filter (#panoramic-weight-filter) from CSDL Master Data
    const panoWeightSel = document.getElementById('panoramic-weight-filter');
    if (panoWeightSel) {
      const cur = panoWeightSel.value;
      let html = `<option value="">-- Lọc theo Tải Trọng --</option>
                  <option value="light">Tải Nhẹ (< 10 Tấn)</option>
                  <option value="medium">Tải Trung (10 - 20 Tấn)</option>
                  <option value="heavy">Tải Nặng (> 20 Tấn)</option>`;
      if (vehTypes && vehTypes.length > 0) {
        vehTypes.forEach(vt => {
          html += `<option value="${vt.name}">${vt.name} (${(vt.max_weight || vt.maxWeight || 0).toLocaleString('vi-VN')} kg)</option>`;
        });
      }
      panoWeightSel.innerHTML = html;
      if (cur) panoWeightSel.value = cur;
    }

    // 6.8 Populate Currency Select Dropdowns from Master Data Currency (#qt-currency)
    renderWorkflowCurrencyOptions(['qt-currency']);

    // 7. Populate Dynamic Vehicle Types in Master Data Tab 2 (#formula-vehicle-types-list)
    if (typeof renderDynamicFormulaVehicleTypes === 'function') {
      renderDynamicFormulaVehicleTypes();
    }
    if (typeof window.refreshQuotationVehicleRecommendations === 'function') {
      window.refreshQuotationVehicleRecommendations();
    }

  } catch (err) {
    baoNapThatBai('dữ liệu cho các ô chọn', err);
  }
};

window.loadFioriDrivers = loadFioriDrivers;

// ==========================================
// SHIPMENT EXECUTION LOGIC
// ==========================================

window.renderShipments = function (filterQuery = '') {
  const tbody = document.getElementById('fiori-shipment-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  // Use eplDeliveryOrders (primary) or appState.delivery_orders (fallback)
  const allDOs = (eplDeliveryOrders && eplDeliveryOrders.length > 0) ? eplDeliveryOrders : (appState.delivery_orders || []);
  let shipments = allDOs.filter(d =>
    d.canonical_status === 'pending' ||
    d.status === 'Chờ vận chuyển' ||
    d.status === 'Picked' || d.status === 'Packed'
  );

  if (!filterQuery) {
    const searchInput = document.getElementById('shipment-search-input');
    if (searchInput) filterQuery = searchInput.value || '';
  }

  if (filterQuery) {
    const q = filterQuery.toLowerCase();
    shipments = shipments.filter(d =>
      (d.id || '').toLowerCase().includes(q) ||
      (d.packaging_spec || '').toLowerCase().includes(q) ||
      (d.status || '').toLowerCase().includes(q)
    );
  }

  if (shipments.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 25px; color:#64748b;"><i class="fa-solid fa-box-open" style="margin-right:6px; color:#cbd5e1;"></i>Chưa có lô hàng chờ xử lý. Hãy tạo Lệnh Giao Hàng (DO) trước.</td></tr>';
    return;
  }

  shipments.forEach(s => {
    let statusColor = '#64748b';
    let statusText = s.status;
    if (s.canonical_status === 'pending' || s.status === 'Chờ vận chuyển') { statusText = 'Chờ lấy hàng'; statusColor = '#f59e0b'; }
    else if (s.status === 'Picked') { statusText = '📦 Đang đóng gói'; statusColor = '#0284c7'; }
    else if (s.status === 'Packed') { statusText = '✅ Chờ xuất kho'; statusColor = '#8b5cf6'; }
    else if (s.status === 'Ready for Dispatch') { statusText = '🚛 Sẵn sàng xếp xe'; statusColor = '#10b981'; }

    const canExecute = s.canonical_status === 'pending' || ['Chờ vận chuyển', 'Picked', 'Đã lấy hàng', 'Packed', 'Đã đóng gói'].includes(s.status);
    const execBtn = canExecute
      ? `<button class="fiori-btn fiori-btn-secondary" style="padding:4px 10px; font-size:0.8rem;" onclick="selectShipmentForExecution('${s.id}')">Chọn Xử Lý</button>`
      : `<span style="color:#94a3b8; font-size:0.8rem;">—</span>`;

    tbody.insertAdjacentHTML('beforeend', `
      <tr style="border-bottom: 1px solid #f1f5f9;">
        <td style="padding:10px 14px; font-weight:600; color:#0f172a;">${s.id}</td>
        <td style="padding:10px 14px;">${s.packaging_spec || 'Carton'}</td>
        <td style="padding:10px 14px;">Kho Tổng Bình Dương</td>
        <td style="padding:10px 14px;"><span style="background:#f0f9ff; color:${statusColor}; padding:4px 10px; border-radius:6px; font-size:0.75rem; font-weight:700; border:1px solid ${statusColor}40; white-space:nowrap;">${statusText}</span></td>
        <td style="padding:10px 14px;">${execBtn}</td>
      </tr>
    `);
  });
};

window.filterShipments = function () {
  const query = document.getElementById('shipment-search-input')?.value || '';
  window.renderShipments(query);
};

window.selectShipmentForExecution = function (id) {
  const s = (eplDeliveryOrders || []).find(d => d.id === id);
  if (!s) return;
  if (document.getElementById('exec-shipment-id')) document.getElementById('exec-shipment-id').value = s.id;
  if (document.getElementById('exec-do-ref')) document.getElementById('exec-do-ref').value = s.id;
  if (document.getElementById('exec-warehouse')) document.getElementById('exec-warehouse').value = 'Kho Tổng Bình Dương';
  showToast(`📦 Đã chọn lô hàng ${id} để tiến hành xử lý!`);
};

window.executeShipmentStep = async function (step) {
  const id = document.getElementById('exec-shipment-id')?.value;
  if (!id) {
    showToast('⚠️ Vui lòng chọn một lô hàng từ danh sách bên trái trước!');
    return;
  }

  // Find DO in both eplDeliveryOrders and appState
  const allDOs = (eplDeliveryOrders && eplDeliveryOrders.length > 0) ? eplDeliveryOrders : (appState.delivery_orders || []);
  const d = allDOs.find(x => x.id === id);
  if (!d) {
    showToast('⚠️ Không tìm thấy lệnh giao hàng này trong hệ thống!');
    return;
  }

  // Strict sequential status validation
  if (step === 'Pick' && d.canonical_status !== 'pending' && d.status !== 'Chờ vận chuyển') {
    showToast(`Không thể lấy hàng. DO "${id}" phải ở trạng thái "Chờ vận chuyển" (hiện tại: ${statusLabel(d.status)}).`);
    return;
  }
  if (step === 'Pack' && d.status !== 'Picked' && d.status !== 'Đã lấy hàng') {
    showToast(`⚠️ Không thể đóng gói! DO "${id}" phải ở trạng thái "Đã lấy hàng" (hiện tại: ${statusLabel(d.status)}).`);
    return;
  }
  if (step === 'Issue' && d.status !== 'Packed' && d.status !== 'Đã đóng gói') {
    showToast(`⚠️ Không thể xuất kho! DO "${id}" phải ở trạng thái "Đã đóng gói" (hiện tại: ${statusLabel(d.status)}).`);
    return;
  }

  let targetStatus = step === 'Issue' ? 'Ready for Dispatch' : step;

  if (!window.CommandPolicy) {
    showToast('Không tải được bộ kiểm soát thao tác. Vui lòng tải lại trang.');
    return;
  }
  const commandResult = await window.CommandPolicy.executeCommand({
    request: () => fetch(`${API_BASE}/api/delivery-orders/${id}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: targetStatus })
    }),
    reload: async () => {
      if (typeof window.loadAllData === 'function') await window.loadAllData();
    },
    onError: error => showToast(`⚠️ ${error.message}`)
  });
  if (!commandResult.ok) return;

  let msg = '';
  if (step === 'Pick') {
    msg = `✅ Hoàn tất lấy hàng cho lô ${id}!`;
  } else if (step === 'Pack') {
    msg = `✅ Hoàn tất đóng gói và dán nhãn lô ${id}!`;
  } else if (step === 'Issue') {
    msg = `✅ Xuất kho thành công! Lô ${id} đã sẵn sàng xếp xe.`;
    // Refresh dispatch board so the new "Ready for Dispatch" DO appears
    if (typeof window.loadDispatchBoard === 'function') window.loadDispatchBoard();
  }

  showToast(msg || `Đã cập nhật lô ${id}.`);
  // Re-render both shipment table and dispatch panel
  window.renderShipments();
  if (typeof renderDispatchDOs === 'function') renderDispatchDOs();
};

// ==========================================
// MASTER DATA LOGIC (MOCK)
// ==========================================

window.saveMasterForm = function (type) {
  type = normalizeMasterFormType(type);
  if (type === 'qt') { window.saveOracleQT(); return; }
  if (type === 'do') { if (typeof window.saveFioriDO === 'function') window.saveFioriDO(); return; }
  if (type === 'route') { window.saveRouteConfig(); return; }
  if (type === 'dispatch' && typeof window.submitDispatch === 'function') { window.submitDispatch(); return; }
  showToast('Chưa tìm thấy API lưu cho form này. Vui lòng kiểm tra lại màn hình đang chọn.');
};

window.approveMasterForm = function (type) {
  type = normalizeMasterFormType(type);
  if (type === 'qt') { window.approveQuotation(); return; }
  if (type === 'do' && typeof window.saveFioriDO === 'function') { window.saveFioriDO(); return; }
  showToast('Chưa tìm thấy API duyệt cho form này. Vui lòng kiểm tra lại màn hình đang chọn.');
};

// --- REAL API IMPLEMENTATIONS ---

async function refreshWorkflowCommandData(commandName) {
  if (commandName === 'quotationCreate' || commandName === 'quotationEdit' || commandName === 'quotationApprove') {
    await window.loadQuotations();
    appState.quotations = crmQuotations;
    return;
  }
  if (commandName === 'dispatch') {
    await loadDispatchBoard();
    return;
  }
  if (commandName === 'deliveryOrderCreate' || commandName === 'deliveryOrderEdit'
      || commandName === 'deliveryOrderApprove' || commandName === 'shipmentStep' || commandName === 'pod') {
    await loadDeliveryOrders();
    appState.delivery_orders = eplDeliveryOrders;
  }
}

/** Điều phối chuyến; xe khác loại xe của báo giá thì hỏi xác nhận rồi gửi lại.
 *
 *  Máy chủ trả 409 `VEHICLE_TYPE_MISMATCH` kèm câu giải thích (loại báo giá,
 *  loại xe thật, cước giữ theo báo giá, chi phí theo xe thật). Người điều phối
 *  đồng ý thì gửi lại đúng lệnh đó với `confirm_vehicle_type_mismatch: true`.
 *  Không chặn cứng vì có lúc cố ý lên loại to hơn để gộp chuyến.
 */
async function dieuPhoiCoXacNhanLoaiXe(command) {
  const kq = await executeWorkflowCommand('dispatch', command);
  if (kq.ok || (kq.error && kq.error.code) !== 'VEHICLE_TYPE_MISMATCH') return kq;
  const dongY = window.confirm((kq.error.message || 'Xe khác loại xe của báo giá.')
    + '\n\nVẫn điều xe này?');
  if (!dongY) return kq;
  return executeWorkflowCommand('dispatch', {
    ...command, body: { ...(command.body || {}), confirm_vehicle_type_mismatch: true },
  });
}

async function executeWorkflowCommand(commandName, command, applyServerState) {
  if (!window.WorkflowCommandAdapters) {
    showToast('Không tải được bộ kiểm soát thao tác. Vui lòng tải lại trang.');
    return { ok: false };
  }
  const opId = recordOperationLog({
    status: 'pending',
    title: `Dang xu ly: ${commandName}`,
    detail: 'Dang gui lenh len server, vui long doi xac nhan.',
    path: `${command?.method || 'POST'} ${command?.path || ''}`,
  });
  const adapters = window.WorkflowCommandAdapters.createWorkflowCommandAdapters({
    request: (path, options = {}) => fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        ...(options.headers || {}),
        ...financeAuthHeaders()
      }
    }),
    applyServerState,
    reload: async () => {
      await refreshWorkflowCommandData(commandName);
    },
    onError: error => showToast(`⚠️ ${error.message}`)
  });
  const result = await adapters[commandName](command);
  if (result.ok) {
    recordOperationLog({
      id: opId,
      status: 'success',
      title: `Da luu: ${commandName}`,
      detail: result.payload?.message || 'Server da xac nhan va du lieu da duoc nap lai.',
      path: `${command?.method || 'POST'} ${command?.path || ''}`,
    });
  } else {
    recordOperationLog({
      id: opId,
      status: 'error',
      title: `Khong luu duoc: ${commandName}`,
      detail: result.error?.message || 'Server tu choi thao tac hoac mat ket noi.',
      path: `${command?.method || 'POST'} ${command?.path || ''}`,
    });
  }
  return result;
}

function routeContextFromFields(prefix) {
  const get = suffix => document.getElementById(`${prefix}-${suffix}`)?.value || '';
  const numberValue = suffix => {
    const parsed = parseFloat(get(suffix).toString().replace(/,/g, ''));
    return Number.isFinite(parsed) && parsed >= 0 ? parsed : 0;
  };
  const intValue = suffix => {
    const parsed = parseInt(get(suffix), 10);
    return Number.isFinite(parsed) && parsed >= 0 ? parsed : 0;
  };
  return {
    origin: get('origin'),
    destination: get('destination'),
    pickup_window_start: get('pickup-window-start'),
    pickup_window_end: get('pickup-window-end'),
    delivery_window_start: get('delivery-window-start'),
    delivery_window_end: get('delivery-window-end'),
    weight_kg: numberValue('weight-kg'),
    volume_m3: numberValue('volume-m3'),
    pallet_count: intValue('pallet-count')
  };
}

function setRouteContextFields(prefix, source = {}) {
  const set = (suffix, value) => {
    const el = document.getElementById(`${prefix}-${suffix}`);
    if (el) el.value = value || '';
  };
  set('origin', source.origin);
  set('destination', source.destination);
  set('pickup-window-start', source.pickup_window_start || source.pickup_date);
  set('pickup-window-end', source.pickup_window_end);
  set('delivery-window-start', source.delivery_window_start);
  set('delivery-window-end', source.delivery_window_end || source.delivery_date);
  set('weight-kg', source.weight_kg || '');
  set('volume-m3', source.volume_m3 || '');
  set('pallet-count', source.pallet_count || '');
  if (source.route_id) renderMasterRouteCheckpoints(prefix, source.route_id);
}

function routeContextFromRoute(routeId) {
  const route = (eplRoutes || []).find(r => r.id === routeId);
  if (!route) return {};
  const parsedContext = window.RouteMapUtils?.buildRouteContext(route) || {};
  const segments = routeSegments(route);
  return {
    origin: parsedContext.origin || segments[0]?.origin || segments[0]?.from || route.origin || '',
    destination: parsedContext.destination || segments[segments.length - 1]?.destination || segments[segments.length - 1]?.to || route.destination || ''
  };
}

// Bản gốc dùng `|| ''` nên giá trị số 0 bị biến thành chuỗi rỗng, khác hai
// hàm escape cùng cảnh. escapeHtml dùng `??` nên 0 vẫn ra "0".
function escapeRouteCheckpointText(value) {
  return escapeHtml(value);
}

function renderMasterRouteCheckpoints(prefix, routeId) {
  const container = document.getElementById(`${prefix}-route-checkpoints`);
  if (!container) return;

  const route = (eplRoutes || []).find(item => item.id === routeId);
  if (!route) {
    container.innerHTML = '';
    return;
  }

  const checkpoints = window.RouteMapUtils?.buildRouteCheckpointModel(route) || [];
  if (checkpoints.length < 2) {
    container.innerHTML = `
      <div class="route-checkpoint-warning">
        <i class="fa-solid fa-triangle-exclamation" aria-hidden="true"></i>
        <span>Tuyến này chưa cấu hình đầy đủ checkpoint trong Route Master.</span>
      </div>`;
    return;
  }

  container.innerHTML = `
    <div class="route-checkpoint-track" aria-label="Các checkpoint của tuyến">
      ${checkpoints.map((checkpoint, index) => {
        const isOrigin = checkpoint.role === 'origin';
        const isDestination = checkpoint.role === 'destination';
        const roleLabel = isOrigin ? 'Điểm đi' : (isDestination ? 'Điểm đến' : `Checkpoint ${index}`);
        const distance = Number(checkpoint.distanceFromPreviousKm || 0);
        const distanceLabel = index > 0 && distance > 0 ? ` · ${formatRouteKm(distance)} km từ điểm trước` : '';
        return `
          <div class="route-checkpoint-node" data-role="${checkpoint.role}">
            <span class="route-checkpoint-marker">${index + 1}</span>
            <div class="route-checkpoint-label">${escapeRouteCheckpointText(checkpoint.label)}</div>
            <div class="route-checkpoint-meta">${roleLabel}${distanceLabel}</div>
          </div>`;
      }).join('')}
    </div>`;
}

window.selectMasterRoute = function (prefix, routeId) {
  const context = routeContextFromRoute(routeId);
  const origin = document.getElementById(`${prefix}-origin`);
  const destination = document.getElementById(`${prefix}-destination`);
  if (origin) origin.value = context.origin || '';
  if (destination) destination.value = context.destination || '';
  renderMasterRouteCheckpoints(prefix, routeId);
};

function fillEmptyRouteContext(prefix, source = {}) {
  const fallback = routeContextFromRoute(source.route_id || source.id || '');
  const merged = { ...fallback, ...source };
  ['origin', 'destination'].forEach(key => {
    const el = document.getElementById(`${prefix}-${key}`);
    if (el && !el.value && merged[key]) el.value = merged[key];
  });
  renderMasterRouteCheckpoints(prefix, source.route_id || source.id || '');
}

function quotationCapacityDemand() {
  const numberFrom = id => {
    const value = Number(document.getElementById(id)?.value || 0);
    return Number.isFinite(value) && value >= 0 ? value : 0;
  };
  return {
    weight_kg: numberFrom('qt-weight-kg'),
    volume_m3: numberFrom('qt-volume-m3'),
    pallet_count: numberFrom('qt-pallet-count')
  };
}

function vehicleTypeReadyCount(vehicleType) {
  const aliases = new Set([String(vehicleType.id || '').toLowerCase(), String(vehicleType.name || '').toLowerCase()]);
  return (fioriVehicles || []).filter(vehicle => {
    const status = window.WorkflowUIUtils?.workflowStatusKey?.(vehicle.status || '') || '';
    return aliases.has(String(vehicle.type || '').toLowerCase()) && status === 'available';
  }).length;
}

function capacityReasonText(reason) {
  const labels = { weight: 'tải trọng', volume: 'thể tích', pallet: 'pallet' };
  if (reason.code === 'CAPACITY_NOT_CONFIGURED') return `Chưa cấu hình ${labels[reason.dimension]}`;
  return `Vượt ${labels[reason.dimension]}: ${reason.required.toLocaleString('vi-VN')}/${reason.capacity.toLocaleString('vi-VN')} ${reason.unit}`;
}

window.selectRecommendedVehicleType = function (name) {
  const select = document.getElementById('qt-cargo-type');
  if (!select) return;
  select.value = name;
  window.refreshQuotationVehicleRecommendations();
  if (typeof autoCalculateMasterDataCost === 'function') autoCalculateMasterDataCost('qt');
};

window.refreshQuotationVehicleRecommendations = function () {
  const select = document.getElementById('qt-cargo-type');
  const panel = document.getElementById('qt-vehicle-recommendations');
  if (!select || !panel || !window.WorkflowUIUtils) return { valid: true };
  const demand = quotationCapacityDemand();
  const hasDemand = demand.weight_kg > 0 || demand.volume_m3 > 0 || demand.pallet_count > 0;
  const previous = select.value;
  const recommendations = window.WorkflowUIUtils.recommendVehicleTypes(vehTypes || [], demand);
  const unsuitableNames = new Set(recommendations.unsuitable.map(item => item.vehicleType.name));

  select.innerHTML = `<option value="">-- Chọn loại xe phù hợp --</option>` + (vehTypes || []).map(vehicleType => {
    const evaluation = window.WorkflowUIUtils.evaluateVehicleCapacity(vehicleType, demand);
    const disabled = hasDemand && !evaluation.fits;
    const suffix = disabled ? ` - Không đủ tải` : '';
    return `<option value="${escapeRouteCheckpointText(vehicleType.name)}" ${disabled ? 'disabled' : ''}>${escapeRouteCheckpointText(vehicleType.name)} (${Number(vehicleType.max_weight || 0).toLocaleString('vi-VN')} kg · ${Number(vehicleType.volume_capacity_m3 || 0)} m³ · ${Number(vehicleType.pallet_capacity || 0)} pallet)${suffix}</option>`;
  }).join('');
  select.value = previous && !unsuitableNames.has(previous) ? previous : '';

  if (!hasDemand) {
    panel.innerHTML = `<div style="padding:10px 12px;border:1px solid #bfdbfe;background:#eff6ff;color:#1e40af;font-weight:700;border-radius:6px;"><i class="fa-solid fa-circle-info"></i> Nhập tải trọng, thể tích và pallet để hệ thống gợi ý loại xe.</div>`;
    return { valid: true, demand, recommendations };
  }

  const selected = (vehTypes || []).find(item => item.name === select.value);
  const selectedEvaluation = selected ? window.WorkflowUIUtils.evaluateVehicleCapacity(selected, demand) : null;
  const suitableCards = recommendations.suitable.slice(0, 3).map((item, index) => {
    const vehicleType = item.vehicleType;
    const readyCount = vehicleTypeReadyCount(vehicleType);
    const encodedName = encodeURIComponent(String(vehicleType.name || '')).replace(/'/g, '%27');
    const readyVehicles = (fioriVehicles || [])
      .filter(vehicle => String(vehicle.type || '').toLowerCase() === String(vehicleType.name || '').toLowerCase())
      .filter(vehicle => (window.WorkflowUIUtils?.workflowStatusKey?.(vehicle.status || '') || '') === 'available')
      .map(vehicle => vehicle.id)
      .slice(0, 3);
    return `<button type="button" onclick="selectRecommendedVehicleType(decodeURIComponent('${encodedName}'))" style="text-align:left;padding:10px 12px;border:1.5px solid ${index === 0 ? '#22c55e' : '#bfdbfe'};background:${index === 0 ? '#f0fdf4' : '#ffffff'};border-radius:6px;cursor:pointer;">
      <strong style="display:block;color:#0f172a;">${index === 0 ? '<i class="fa-solid fa-star" style="color:#f59e0b;"></i> Đề xuất tốt nhất · ' : ''}${escapeRouteCheckpointText(vehicleType.name)}</strong>
      <span style="font-size:.78rem;color:#475569;">Dùng tối đa ${item.utilizationPct}% · ${readyCount} xe đang sẵn sàng${readyVehicles.length ? `: ${readyVehicles.map(escapeRouteCheckpointText).join(', ')}` : ''}</span>
    </button>`;
  }).join('');
  const invalidNotice = previous && unsuitableNames.has(previous)
    ? `<div style="padding:10px 12px;border:1px solid #fca5a5;background:#fef2f2;color:#b91c1c;font-weight:800;border-radius:6px;"><i class="fa-solid fa-ban"></i> Đã bỏ chọn ${escapeRouteCheckpointText(previous)} vì ${recommendations.unsuitable.find(item => item.vehicleType.name === previous).reasons.map(capacityReasonText).join('; ')}.</div>`
    : '';
  panel.innerHTML = `${invalidNotice}<div style="margin-top:${invalidNotice ? '8px' : '0'};padding:12px;border:1px solid #cbd5e1;background:#f8fafc;border-radius:6px;">
    <div style="font-weight:900;color:#0f172a;margin-bottom:8px;"><i class="fa-solid fa-wand-magic-sparkles" style="color:#2563eb;"></i> Loại xe phù hợp đề xuất</div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px;">${suitableCards || '<div style="color:#b91c1c;font-weight:800;">Không có loại xe đơn lẻ đủ tải. Cần chia nhiều xe/chuyến hoặc thuê ngoài.</div>'}</div>
  </div>`;
  return { valid: Boolean(selectedEvaluation?.fits), demand, recommendations };
};

window.saveOracleQT = async function () {
  const qid = document.getElementById('qt-id')?.value || '';
  const currentQT = (crmQuotations || []).find(q => q.id === qid);
  if (currentQT && isWorkflowLocked(currentQT.status)) {
    showToast('Báo giá đã duyệt chỉ được xem, không được sửa.');
    return;
  }
  const customer = document.getElementById('qt-customer')?.value || '';
  const route = document.getElementById('qt-route')?.value || '';
  const cargo = document.getElementById('qt-cargo-type')?.value || '';

  const parseVal = (id) => parseWorkflowMoneyValue(document.getElementById(id)?.value);

  const fuel = workflowCostFieldVndValue('qt-fuel');
  const driver = workflowCostFieldVndValue('qt-driver');
  const toll = workflowCostFieldVndValue('qt-toll');
  const selling = parseVal('qt-selling-price');
  const routeContext = routeContextFromFields('qt');

  // Ba con so TACH ROI, khong gop: `total_cost` la tien chi ra, `selling_price`
  // la cuoc thu cua khach. Bang `quotations` da co san ba cot nay nhung man
  // hinh chua bao gio ghi vao, nen bao cao lai lo hay lai lai khong doc duoc.
  const quote = lastQuotationQuote && lastQuotationQuote.ready ? lastQuotationQuote : null;

  if (!customer || !route || !cargo) {
    showToast('⚠️ Vui lòng nhập đủ Khách hàng, Lộ trình và Loại xe!');
    return;
  }

  // Kiểm tải trọng Ở ĐÂY — trên chính form báo giá.
  //
  // Phép kiểm này trước đây nằm trong `submitPOD`, tức bước MỞ HỒ SƠ POD bị
  // chặn vì form báo giá ở một tab khác chưa chọn loại xe, kèm một thông báo về
  // "lưu báo giá" hoàn toàn không liên quan. Đến bước POD thì xe đã chạy xong
  // rồi, chặn ghi nhận giao hàng vì tải trọng lúc đó là vô nghĩa.
  //
  // Tên bài kiểm cũ ("Quotation save must revalidate capacity") nói đúng ý định,
  // chỉ là mã đặt nó sai chỗ.
  const capacityState = window.refreshQuotationVehicleRecommendations();
  if (!capacityState.valid) {
    showToast('CAPACITY_EXCEEDED: Hãy chọn loại xe được đề xuất và đủ tải trước khi lưu báo giá.');
    return;
  }

  showToast('⏳ Đang lưu báo giá vào PostgreSQL...');
  const qtPath = currentQT ? `/api/quotations/${encodeURIComponent(qid)}` : '/api/quotations';
  const result = await executeWorkflowCommand(currentQT ? 'quotationEdit' : 'quotationCreate', {
    path: qtPath, method: currentQT ? 'PUT' : 'POST', body: {
      id: qid, customer_id: customer, route_id: route, cargo_type: cargo,
      ...routeContext,
      fuel_cost: fuel, driver_cost: driver, toll_fee: toll,
      selling_price: quote ? quote.revenue : selling,
      // O Ghi chu (textarea 4 dong, placeholder rat cu the ve dieu kien bao
      // gia). Truoc day khong co cot nao de chua va khong ai gui len, nen go
      // xong bam Luu la mat khong mot loi nao.
      notes: document.getElementById('qt-notes')?.value || '',
      // CO Y khong gui ti le loi nhuan: bang quotations khong co cot do, va ti
      // le suy ra duoc tu hai con so tren. Luu them mot cot thu ba la tao ra
      // ba con so co the troi khoi nhau.
      ...(quote ? { total_cost: quote.cost } : {}),
    }
  });
  if (result.ok) showToast(`✅ Máy chủ đã xác nhận lưu báo giá ${qid}.`);
};

window.approveQuotation = async function () {
  const qid = document.getElementById('qt-id')?.value;
  if (!qid) return;
  showToast(`⏳ Đang duyệt Báo Giá ${qid}...`);
  const result = await executeWorkflowCommand('quotationApprove', {
    path: `/api/quotations/${qid}/approve`, method: 'PUT'
  });
  if (result.ok) {
    showToast(`✅ Đã phê duyệt Báo Giá ${qid} thành công!`);
    if (typeof window.updateActiveFlowStep === 'function') window.updateActiveFlowStep(3);
  }
};


window.saveRouteConfig = async function () {
  const routeId = document.getElementById('md-route-code')?.value;
  const routeName = document.getElementById('md-route-name')?.value;
  // Doc con so THAT tu dataset. Doc `innerText` la doc lai chu da dinh dang
  // theo kieu Viet ("1.250 km"), va `parseFloat` cua no ra 1,25 — sai 1.000
  // lan voi moi tuyen tren 999 km.
  const totalEl = document.getElementById('route-total-distance');
  const totalDist = Number(totalEl?.dataset?.km ?? NaN);
  if (!Number.isFinite(totalDist)) {
    showToast('⚠️ Chưa tính được tổng số km của tuyến. Hãy thêm ít nhất một chặng.');
    return;
  }

  if (!routeId || !routeName) {
    showToast('⚠️ Vui lòng nhập Mã Tuyến và Tên Tuyến!');
    return;
  }

  const tbody = document.getElementById('route-segments-tbody');
  const trs = tbody ? tbody.querySelectorAll('tr') : [];
  let segments = [];
  trs.forEach(tr => {
    const tds = tr.querySelectorAll('td');
    if (tds.length >= 3) {
      if (tr.dataset.segmentJson) {
        segments.push(JSON.parse(tr.dataset.segmentJson));
        return;
      }
      segments.push({
        origin: tds[0].innerText.trim(),
        destination: tds[1].innerText.trim(),
        distance_km: parseFloat(tds[2].innerText.replace(/[^0-9.,]/g, '').replace(',', '.')) || 0
      });
    }
  });

  showToast(`⏳ Đang lưu Tuyến Đường ${routeId} vào CSDL...`);
  try {
    const res = await fetch(`${API_BASE}/api/routes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id: routeId, name: routeName, distance_km: totalDist, segments_json: JSON.stringify(segments)
      })
    });

    if (res.ok) {
      showToast(`✅ Đã lưu tuyến đường ${routeId} thành công!`);
      if (typeof window.syncAllDynamicDropdowns === 'function') window.syncAllDynamicDropdowns();
      if (typeof window.loadSavedRoutePreset === 'function') window.loadSavedRoutePreset(routeId);
    } else {
      const err = await res.json();
      showToast(`⚠️ Lỗi: ${err.detail || 'Không thể lưu tuyến'}`);
    }
  } catch (e) {
    showToast('⚠️ Lỗi kết nối CSDL khi lưu Tuyến!');
  }
};

// Note: Dynamic dropdowns & drivers are already loaded via the DOMContentLoaded at top of file
// via loadAllData() -> loadFioriVehicles() -> syncAllDynamicDropdowns() chain.
// No second DOMContentLoaded needed here.

window.submitPOD = async function () {
  const doIdSpan = document.getElementById('pod-do-badge');
  let doId = doIdSpan ? doIdSpan.innerText.trim() : '';
  if (!doId || doId === 'Chưa chọn DO') {
    const doSearchInput = document.getElementById('tracking-do-search');
    if (doSearchInput && doSearchInput.value.trim()) {
      doId = doSearchInput.value.trim();
    } else {
      showToast('⚠️ Vui lòng chọn hoặc nhập mã DO trước khi cập nhật POD.');
      return;
    }
  }

  switchView('delivery-completion');
  await loadDeliveryCompletionWorkbench();
  const row = deliveryCompletionState.rows.find(item => item.order.id === doId);
  if (!row) {
    showToast(`DO ${doId} chưa sẵn sàng để hoàn tất giao hàng.`, 'warning');
    return;
  }
  // CỐ Ý không gọi `refreshQuotationVehicleRecommendations()` ở đây.
  //
  // Bản cũ gọi nó rồi chặn việc mở hồ sơ POD nếu nó trả `valid: false`. Hai
  // điều sai:
  //
  //   1. Hàm đó đọc form BÁO GIÁ (`#qt-cargo-type`) ở một tab khác. Form báo
  //      giá đang có tải trọng nhưng chưa chọn loại xe là chuyện rất bình
  //      thường, và khi đó việc mở hồ sơ POD bị huỷ kèm một thông báo về
  //      "lưu báo giá" — hoàn toàn không liên quan.
  //
  //   2. Hàm đó có tác dụng phụ ghi đè DOM: nó viết lại `select.innerHTML` và
  //      đặt `select.value = ''`. Nên chỉ mở hồ sơ POD là đã XÓA lựa chọn loại xe
  //      trong form báo giá.
  //
  // Phép kiểm tải trọng thực sự thuộc bước điều xe, và máy chủ đã chặn ở
  // đó (`vehicle_capacity_policy`). Đến bước POD thì xe đã chạy xong rồi — chặn
  // ghi nhận giao hàng vì lý do tải trọng lúc này là vô nghĩa.
  openDeliveryCompletionEditor(doId);
  showToast(`Đã mở hồ sơ hoàn tất ${doId}. POD, chữ ký, giá cuối và hóa đơn sẽ được lưu trong một giao dịch.`, 'info');
};

/**
 * Doc bang "Hang hoa van chuyen" tu man hinh thanh mang de gui len may chu.
 *
 * Truoc day bang nay khong duoc gui di dau ca: saveOracleSO chi gui
 * customer_id, route_id va total_amount. Nguoi dung nhap mo ta hang, so luong,
 * don vi tinh, don gia cuoc — bam Luu — nhan thong bao thanh cong, va khong mot
 * dong nao duoc ghi lai.
 */
const deliveryCompletionState = {
  tab: 'pending', rows: [], selected: null, charges: [], submissionKey: ''
};

function completionEscape(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
}

function completionMoney(value, currency = 'VND') {
  return FormatUtils.formatMoney(value, currency);
}

window.switchDeliveryCompletionTab = function (tab, button) {
  deliveryCompletionState.tab = tab;
  document.querySelectorAll('.completion-tab').forEach(item => item.classList.toggle('active', item === button));
  closeDeliveryCompletionEditor();
  renderDeliveryCompletionList();
};

window.loadDeliveryCompletionWorkbench = async function () {
  const body = document.getElementById('completion-do-list');
  if (!body) return;
  body.innerHTML = '<tr><td colspan="6" class="completion-empty">Đang tải DO và Trip từ database...</td></tr>';
  try {
    const [doResponse, tripResponse] = await Promise.all([
      fetch(`${API_BASE}/api/delivery-orders?page=1&page_size=200`),
      fetch(`${API_BASE}/api/tms/trips?page=1&page_size=200`, {headers:financeAuthHeaders()})
    ]);
    if (!doResponse.ok || !tripResponse.ok) throw new Error('Không tải được danh sách DO/Trip.');
    const doPayload = await doResponse.json();
    const tripPayload = await tripResponse.json();
    const orders = doPayload.items || doPayload.data || [];
    const trips = tripPayload.items || tripPayload.data || [];
    // `arrived` PHAI co trong danh sach nay. Do la trang thai "xe da den noi,
    // chua ky POD" — dung luc phai nop POD, tuc dung viec cua chinh man nay.
    // Thieu no thi mot don da den noi khong hien ra o man nop POD, va nguoi
    // dung khong co cho nao de nop.
    const TRANG_THAI_LIEN_QUAN = ['in_transit', 'arrived', 'delivered'];
    const candidates = orders.filter(order =>
      TRANG_THAI_LIEN_QUAN.includes(String(order.canonical_status || '').toLowerCase()));
    deliveryCompletionState.rows = await Promise.all(candidates.map(async order => {
      const trip = trips.find(item => (item.delivery_order_ids || []).includes(order.id)) || null;
      let closeout = null;
      try {
        const response = await fetch(`${API_BASE}/api/delivery-orders/${encodeURIComponent(order.id)}/closeout`, {headers:financeAuthHeaders()});
        if (response.ok) closeout = await response.json();
      } catch (_) {}
      return { order, trip, closeout };
    }));
    renderDeliveryCompletionList();
  } catch (error) {
    body.innerHTML = `<tr><td colspan="6" class="completion-empty">${completionEscape(error.message)}</td></tr>`;
    showToast(error.message, 'error');
  }
};

window.renderDeliveryCompletionList = function () {
  const body = document.getElementById('completion-do-list');
  if (!body) return;
  const query = String(document.getElementById('completion-search')?.value || '').trim().toLowerCase();
  // Tab "Cho hoan tat" gom HAI trang thai, khong phai mot: don dang chay va
  // don da den noi. Ca hai deu chua ky POD nen deu thuoc viec cua tab nay.
  const TRANG_THAI_CHO = ['in_transit', 'arrived'];
  const trangThaiCanLay = deliveryCompletionState.tab === 'pending'
    ? TRANG_THAI_CHO : ['delivered'];
  const rows = deliveryCompletionState.rows.filter(row => {
    if (!trangThaiCanLay.includes(String(row.order.canonical_status || '').toLowerCase())) {
      return false;
    }
    const haystack = [row.order.id, row.order.vehicle_id, row.order.driver_id, row.order.customer_id, row.order.destination].join(' ').toLowerCase();
    return !query || haystack.includes(query);
  });
  // Don DA DEN NOI xep len truoc: no la don san sang nop POD ngay bay gio,
  // con don dang chay thi con phai doi xe toi. Xep lan lon thi nguoi dung
  // phai tu do trong danh sach xem don nao lam duoc.
  const UU_TIEN = { arrived: 0, in_transit: 1, delivered: 2 };
  rows.sort((a, b) => {
    const ta = UU_TIEN[String(a.order.canonical_status || '').toLowerCase()] ?? 9;
    const tb = UU_TIEN[String(b.order.canonical_status || '').toLowerCase()] ?? 9;
    if (ta !== tb) return ta - tb;
    return String(a.order.id || '').localeCompare(String(b.order.id || ''));
  });

  const count = document.getElementById('completion-result-count');
  if (count) count.textContent = `${rows.length} DO`;
  if (!rows.length) {
    body.innerHTML = `<tr><td colspan="6" class="completion-empty">${deliveryCompletionState.tab === 'pending' ? 'Không có DO nào đang vận chuyển hoặc đã đến nơi.' : 'Chưa có DO đã hoàn tất.'}</td></tr>`;
    return;
  }
  body.innerHTML = rows.map(row => {
    const order = row.order, closeout = row.closeout || {}, commercials = closeout.commercials || {};
    const basePrice = commercials.base_selling_price ?? commercials.selling_price ?? 0;
    // Ba mốc, ba nhãn tách rõ. "Đã giao" mơ hồ: xe tới bãi mà chưa ký
    // POD thì cũng là "đã giao" theo cách hiểu thường, nhưng lúc đó chưa
    // có gì xác nhận.
    // Nhãn và nút phải theo trạng thái của CHÍNH DÒNG NÀY, không theo trạng
    // thái của cả tab. Trước đây cả hai đọc `desiredStatus` — tức tab đang mở —
    // nên mọi dòng trong một tab đều mang cùng một nhãn. Nhãn `arrived` đã có
    // sẵn trong bảng dưới đây mà KHÔNG BAO GIỜ tới được, vì tab chỉ nhận đúng
    // `in_transit` hoặc `delivered`.
    const trangThaiDong = String(order.canonical_status || '').toLowerCase();
    const status = {
      in_transit: 'Đang vận chuyển',
      arrived: 'Đã đến nơi — chờ POD',
      delivered: 'Đã hoàn tất',
    }[trangThaiDong] || 'Đã hoàn tất';
    const action = trangThaiDong !== 'delivered'
      ? `<button class="fiori-btn fiori-btn-secondary" onclick="viewCompletionDO('${completionEscape(order.id)}')"><i class="fa-solid fa-eye"></i> Xem DO</button><button class="fiori-btn fiori-btn-primary" onclick="openDeliveryCompletionEditor('${completionEscape(order.id)}')"><i class="fa-solid fa-clipboard-check"></i> Hoàn tất giao</button>`
      : `<button class="fiori-btn fiori-btn-secondary" onclick="viewCompletedDelivery('${completionEscape(order.id)}')"><i class="fa-solid fa-folder-open"></i> Xem hồ sơ</button>`;
    return `<tr><td><strong>${completionEscape(order.id)}</strong><br><small>${completionEscape(order.destination || '')}</small></td><td><strong>${completionEscape(order.vehicle_id || row.trip?.vehicle_id || '-')}</strong><br><small>${completionEscape(order.driver_id || row.trip?.driver_id || '-')}</small></td><td>${completionEscape(order.customer_id || '-')}<br><small>${completionEscape(order.destination || '-')}</small></td><td><strong>${completionMoney(basePrice, closeout.currency || 'VND')}</strong></td><td><span class="completion-status">${status}</span></td><td><div class="completion-actions">${action}</div></td></tr>`;
  }).join('');
};

window.viewCompletionDO = function (doId) {
  const row = deliveryCompletionState.rows.find(item => item.order.id === doId);
  if (!row) {
    showToast(`Không tìm thấy dữ liệu DO ${doId}.`, 'error');
    return;
  }
  const existingIndex = eplDeliveryOrders.findIndex(order => order.id === doId);
  if (existingIndex >= 0) {
    eplDeliveryOrders[existingIndex] = { ...eplDeliveryOrders[existingIndex], ...row.order };
  } else {
    eplDeliveryOrders.push(row.order);
  }
  editFioriDO(doId);
};

function completionDisplayValue(value, suffix = '') {
  if (value === null || value === undefined || value === '') return '-';
  return `${value}${suffix}`;
}

function initializeDeliverySignaturePads(root = document) {
  root.querySelectorAll('canvas[data-pod="signature"]').forEach(canvas => {
    if (canvas.dataset.signatureInitialized === 'true') return;
    const pad = canvas.closest('.completion-signature-pad');
    const rect = canvas.getBoundingClientRect();
    if (rect.width < 2 || rect.height < 2) return;
    const ratio = Math.max(1, window.devicePixelRatio || 1);
    canvas.width = Math.max(1, Math.round(rect.width * ratio));
    canvas.height = Math.max(1, Math.round(rect.height * ratio));
    const context = canvas.getContext('2d');
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.lineWidth = 2.25;
    context.lineCap = 'round';
    context.lineJoin = 'round';
    context.strokeStyle = '#14243b';
    let drawing = false;
    const point = event => {
      const bounds = canvas.getBoundingClientRect();
      return {x:event.clientX - bounds.left, y:event.clientY - bounds.top};
    };
    canvas.addEventListener('pointerdown', event => {
      event.preventDefault();
      drawing = true;
      canvas.setPointerCapture?.(event.pointerId);
      const current = point(event);
      context.beginPath();
      context.moveTo(current.x, current.y);
    });
    canvas.addEventListener('pointermove', event => {
      if (!drawing) return;
      event.preventDefault();
      const current = point(event);
      context.lineTo(current.x, current.y);
      context.stroke();
      canvas.dataset.hasSignature = 'true';
      pad?.classList.add('has-signature');
    });
    const stopDrawing = event => {
      if (!drawing) return;
      event.preventDefault();
      drawing = false;
      context.closePath();
      canvas.releasePointerCapture?.(event.pointerId);
    };
    canvas.addEventListener('pointerup', stopDrawing);
    canvas.addEventListener('pointercancel', stopDrawing);
    canvas.dataset.signatureInitialized = 'true';
  });
}

window.toggleDeliveryPodStop = function (button) {
  const selectedStop = button.closest('.completion-pod-stop');
  if (!selectedStop) return;
  const shouldOpen = !selectedStop.classList.contains('expanded');
  document.querySelectorAll('#completion-pod-fields .completion-pod-stop.expanded').forEach(stop => {
    stop.classList.remove('expanded');
    stop.querySelector('[data-completion-stop-toggle]')?.setAttribute('aria-expanded', 'false');
  });
  if (!shouldOpen) return;
  selectedStop.classList.add('expanded');
  button.setAttribute('aria-expanded', 'true');
  requestAnimationFrame(() => initializeDeliverySignaturePads(selectedStop));
};

window.clearDeliverySignature = function (button) {
  const pad = button.closest('.completion-signature')?.querySelector('.completion-signature-pad');
  const canvas = pad?.querySelector('canvas[data-pod="signature"]');
  if (!canvas) return;
  canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
  canvas.dataset.hasSignature = 'false';
  pad.classList.remove('has-signature');
};

function deliverySignatureBlob(canvas) {
  return new Promise((resolve, reject) => canvas.toBlob(
    blob => blob ? resolve(blob) : reject(new Error('Không thể tạo ảnh chữ ký.')),
    'image/png'
  ));
}

window.openDeliveryCompletionEditor = function (doId) {
  const row = deliveryCompletionState.rows.find(item => item.order.id === doId);
  if (!row || !row.trip) {
    showToast('DO chưa có Trip đang vận chuyển để hoàn tất.', 'warning');
    return;
  }
  deliveryCompletionState.selected = row;
  deliveryCompletionState.charges = [];
  deliveryCompletionState.submissionKey = `complete-${doId}-${globalThis.crypto?.randomUUID?.() || Date.now()}`;
  const editor = document.getElementById('completion-editor');
  const history = document.getElementById('completion-history-detail');
  if (history) history.hidden = true;
  editor.hidden = false;
  moHoSoNoi(editor);
  document.getElementById('completion-editor-title').textContent = `Hoàn tất giao hàng · ${doId}`;
  const closeout = row.closeout || {}, commercials = closeout.commercials || {};
  const base = Number(commercials.base_selling_price ?? commercials.selling_price ?? 0);
  const currency = closeout.currency || row.order.currency_code || 'VND';
  row.basePrice = base; row.currency = currency;
  deliveryCompletionState.charges = (closeout.configured_cost_lines || []).map(line => ({
    name:line.name,
    original_amount:Number(line.original_amount || 0),
    actual_amount:Number(line.original_amount || 0),
    note:line.calculation || '',
    code:line.code,
    // Mã costindex đi theo dòng từ công thức giá thành tới lúc chốt; gửi lại
    // máy chủ khi hoàn tất để dòng "khách trả thêm" cũng mang mã.
    cost_index:line.cost_index || '',
    rate_source:line.rate_source || 'vehicle_type',
    source:'configured'
  }));
  document.getElementById('completion-do-summary').innerHTML = [
    ['Báo giá nguồn', closeout.quotation_id || row.order.quotation_id || '-'], ['Xe vận chuyển', row.order.vehicle_id || row.trip.vehicle_id || '-'],
    ['Tài xế', row.order.driver_id || row.trip.driver_id || '-'], ['Tuyến', `${escapeHtml(row.order.origin || '-')} → ${escapeHtml(row.order.destination || '-')}`],
    ['Giá ban đầu', completionMoney(base, currency)]
  ].map(item => `<div><span>${item[0]}</span><strong>${completionEscape(item[1])}</strong></div>`).join('');
  const order = row.order;
  const doDetails = [
    ['Mã DO', order.id], ['Trạng thái', order.canonical_status || order.status],
    ['Báo giá cước', closeout.quotation_id || order.quotation_id], ['Khách hàng', order.customer_id],
    ['Mã tuyến', order.route_id], ['Trip', row.trip.id],
    ['Điểm đi', order.origin], ['Điểm đến', order.destination],
    ['Nhận hàng từ', order.pickup_window_start], ['Nhận hàng đến', order.pickup_window_end],
    ['Giao hàng từ', order.delivery_window_start], ['Giao hàng đến', order.delivery_window_end],
    ['Xe vận chuyển', order.vehicle_id || row.trip.vehicle_id], ['Tài xế', order.driver_id || row.trip.driver_id],
    ['Tải trọng', completionDisplayValue(order.weight_kg, ' kg')], ['Số pallet', completionDisplayValue(order.pallet_count)],
    ['Thể tích', completionDisplayValue(order.volume_m3, ' m³')], ['Quy cách đóng gói', order.packaging_spec],
  ];
  document.getElementById('completion-do-details').innerHTML = doDetails.map(item => `<div class="completion-do-detail"><span>${item[0]}</span><strong>${completionEscape(completionDisplayValue(item[1]))}</strong></div>`).join('');
  document.getElementById('completion-base-price-badge').textContent = `Theo báo giá: ${completionMoney(base, currency)}`;
  const legs = (row.trip.legs || []).filter(leg => leg.do_id === doId && leg.leg_type === 'delivery');
  document.getElementById('completion-pod-fields').innerHTML = legs.map((leg, index) => `<div class="completion-pod-stop ${index === 0 ? 'expanded' : ''}" data-completion-leg="${completionEscape(leg.id)}">
    <button type="button" class="completion-pod-stop-toggle" data-completion-stop-toggle aria-expanded="${index === 0 ? 'true' : 'false'}" onclick="toggleDeliveryPodStop(this)">
      <span class="completion-stop-number">${index + 1}</span>
      <span class="completion-stop-summary"><strong>Điểm giao ${index + 1}</strong><small>${completionEscape(leg.stop_name || leg.destination)}</small></span>
      <span class="completion-stop-recipient">${completionEscape(leg.receiver_name || 'Chưa có người nhận')}</span>
      <i class="fa-solid fa-chevron-down"></i>
    </button>
    <div class="completion-pod-stop-body">
      <div class="completion-field wide"><label>Địa điểm giao</label><input value="${completionEscape(leg.stop_name || leg.destination)}" readonly></div>
      <div class="completion-field"><label>Thời gian giao thực tế</label><input type="datetime-local" data-pod="time"></div>
      <div class="completion-field"><label>Kết quả giao</label><select data-pod="result"><option value="delivered_full">Giao đủ hàng</option></select></div>
      <div class="completion-field"><label>Người nhận</label><input data-pod="receiver" value="${completionEscape(leg.receiver_name || '')}"></div>
      <div class="completion-field"><label>Số điện thoại</label><input data-pod="phone" value="${completionEscape(leg.receiver_phone || '')}"></div>
      <div class="completion-field wide"><label>Biên bản, chữ ký hoặc ảnh POD</label><input type="file" data-pod="file" accept="image/jpeg,image/png,application/pdf"></div>
      <div class="completion-field wide"><label>Tình trạng hàng hóa / ghi chú</label><textarea data-pod="condition" rows="2" placeholder="Nguyên niêm phong, không móp vỡ"></textarea></div>
      <div class="completion-signature">
        <div class="completion-signature-head"><label>Chữ ký xác nhận của người nhận <strong aria-hidden="true">*</strong></label><button type="button" class="completion-signature-clear" onclick="clearDeliverySignature(this)"><i class="fa-solid fa-eraser"></i> Xóa chữ ký</button></div>
        <div class="completion-signature-pad"><canvas data-pod="signature" aria-label="Vùng ký xác nhận giao hàng"></canvas><span class="completion-signature-hint"><i class="fa-solid fa-signature"></i><br>Ký bằng chuột hoặc cảm ứng trong vùng này</span></div>
        <span class="completion-signature-consent">Chữ ký này xác nhận người nhận đã kiểm tra thông tin DO và tình trạng hàng hóa.</span>
      </div>
    </div>
  </div>`).join('') || '<div class="completion-empty">Trip chưa có chặng giao hàng hợp lệ.</div>';
  initializeDeliverySignaturePads();
  renderDeliveryChargeLines();
  updateDeliveryCompletionTotals();
};

window.closeDeliveryCompletionEditor = function () {
  dongHoSoNoi();
  deliveryCompletionState.selected = null;
};

/**
 * HỒ SƠ MỞ THÀNH HỘP THOẠI NỔI, không đẩy xuống cuối trang.
 *
 * Chủ dự án bấm "Xem hồ sơ" và thấy nội dung xuất hiện DƯỚI bảng — phải cuộn
 * xuống, bảng 5 dòng thì còn thấy, bảng 200 dòng thì hồ sơ nằm ở đâu không ai
 * biết, và ở màn Chờ hoàn tất cũng vậy. Một hồ sơ là việc đang làm dở, nó phải
 * đè lên bảng, đóng lại thì bảng còn nguyên chỗ cũ.
 *
 * Cùng một hàm cho cả hai khối (biên tập POD và hồ sơ đã hoàn tất) để hai màn
 * mở giống nhau. Lớp `.completion-float` do CSS vẽ: cố định giữa màn, cuộn bên
 * trong, bóng phủ nền. Esc để đóng. Khoá cuộn của trang khi đang mở.
 */
function moHoSoNoi(section) {
  if (!section) return;
  document.querySelectorAll('.completion-float').forEach(el => {
    if (el !== section) { el.classList.remove('completion-float'); el.hidden = true; }
  });
  section.hidden = false;
  section.classList.add('completion-float');
  document.body.classList.add('completion-float-open');
  section.scrollTop = 0;
  if (!moHoSoNoi._esc) {
    moHoSoNoi._esc = ev => { if (ev.key === 'Escape') dongHoSoNoi(); };
    document.addEventListener('keydown', moHoSoNoi._esc);
  }
}

function dongHoSoNoi() {
  document.querySelectorAll('.completion-float').forEach(el => {
    el.classList.remove('completion-float');
    el.hidden = true;
  });
  document.body.classList.remove('completion-float-open');
}
window.moHoSoNoi = moHoSoNoi;
window.dongHoSoNoi = dongHoSoNoi;

window.addDeliveryChargeLine = function () {
  deliveryCompletionState.charges.push({name:'', original_amount:0, actual_amount:0, note:'', source:'manual'});
  renderDeliveryChargeLines();
};

window.removeDeliveryChargeLine = function (index) {
  if (deliveryCompletionState.charges[index]?.source === 'configured') return;
  deliveryCompletionState.charges.splice(index, 1);
  renderDeliveryChargeLines();
};

window.updateDeliveryChargeLine = function (index, field, value) {
  const line = deliveryCompletionState.charges[index];
  if (!line) return;
  if (line.source === 'configured' && (field === 'name' || field === 'original_amount')) return;
  line[field] = field === 'name' || field === 'note' ? value : Math.max(0, Number(value || 0));
  renderDeliveryChargeLines();
};

window.renderDeliveryChargeLines = function () {
  const target = document.getElementById('completion-charge-lines');
  if (!target) return;
  target.innerHTML = deliveryCompletionState.charges.map((line, index) => {
    const increase = Math.max(0, Number(line.actual_amount || 0) - Number(line.original_amount || 0));
    // Mã costindex hiện ngay cạnh tên: người chốt giá thấy dòng nào chưa có
    // mã thì biết phải gán ở Công thức giá thành trước khi hồ sơ sang bên công nợ.
    const maCostindex = line.cost_index
      ? `<code class="completion-costindex" title="Acc code">${completionEscape(line.cost_index)}</code>`
      : (line.source === 'configured' ? '<code class="completion-costindex is-missing" title="Công thức chưa chọn Acc code">chưa có acc code</code>' : '');
    const nguon = line.rate_source === 'vehicle' ? ' · đơn giá của xe' : '';
    const nameField = line.source === 'configured'
      ? `<div class="completion-configured-cost"><strong>${completionEscape(line.name)} ${maCostindex}</strong><small>${completionEscape((line.note || 'Theo cấu hình giá') + nguon)}</small></div>`
      : `<input aria-label="Khoản phí bổ sung" placeholder="Ví dụ: Phí chờ bốc dỡ" value="${completionEscape(line.name)}" onchange="updateDeliveryChargeLine(${index},'name',this.value)">`;
    const action = line.source === 'configured'
      ? '<span class="completion-cost-locked" title="Khoản đã chốt từ cấu hình"><i class="fa-solid fa-lock"></i></span>'
      : `<button class="completion-remove" title="Xóa khoản phí" onclick="removeDeliveryChargeLine(${index})"><i class="fa-solid fa-trash"></i></button>`;
    return `<div class="completion-charge-row ${line.source === 'configured' ? 'configured' : 'manual'}">${nameField}<input class="completion-original-cost" aria-label="Chi phí chốt ban đầu" type="number" min="0" value="${line.original_amount}" readonly><input aria-label="Chi phí thực tế" type="number" min="0" value="${line.actual_amount}" onchange="updateDeliveryChargeLine(${index},'actual_amount',this.value)"><input class="completion-charge-increase" aria-label="Khách hàng trả thêm" value="${increase.toLocaleString('vi-VN')}" readonly>${action}</div>`;
  }).join('') || '<div style="padding:14px 4px;color:#64748b;font-size:.8rem;">Chưa có chi phí cấu hình hoặc khoản bổ sung.</div>';
  updateDeliveryCompletionTotals();
};

window.updateDeliveryCompletionTotals = function () {
  const row = deliveryCompletionState.selected;
  const base = Number(row?.basePrice || 0);
  const surcharge = deliveryCompletionState.charges.reduce((total, line) => total + Math.max(0, Number(line.actual_amount || 0) - Number(line.original_amount || 0)), 0);
  const currency = row?.currency || 'VND';
  if (document.getElementById('completion-base-total')) document.getElementById('completion-base-total').textContent = completionMoney(base, currency);
  if (document.getElementById('completion-surcharge-total')) document.getElementById('completion-surcharge-total').textContent = completionMoney(surcharge, currency);
  if (document.getElementById('completion-final-total')) document.getElementById('completion-final-total').textContent = completionMoney(base + surcharge, currency);
};

window.submitDeliveryCompletion = async function () {
  const row = deliveryCompletionState.selected;
  if (!row) return showToast('Chưa chọn DO cần hoàn tất.', 'warning');
  const podEntries = [], files = {}, stops = [...document.querySelectorAll('#completion-pod-fields [data-completion-leg]')];
  for (let index = 0; index < stops.length; index += 1) {
    const stop = stops[index], legId = stop.dataset.completionLeg;
    const time = stop.querySelector('[data-pod="time"]')?.value;
    const receiver = stop.querySelector('[data-pod="receiver"]')?.value?.trim();
    const phone = stop.querySelector('[data-pod="phone"]')?.value?.trim();
    const condition = stop.querySelector('[data-pod="condition"]')?.value?.trim();
    const file = stop.querySelector('[data-pod="file"]')?.files?.[0];
    const signatureCanvas = stop.querySelector('[data-pod="signature"]');
    if (!time || !receiver || !phone || !condition || !file) return showToast(`Điểm giao ${index + 1} chưa đủ giờ giao, người nhận, tình trạng hàng và file POD.`, 'warning');
    if (!signatureCanvas || signatureCanvas.dataset.hasSignature !== 'true') return showToast(`Điểm giao ${index + 1} chưa có chữ ký xác nhận của người nhận.`, 'warning');
    const leg = row.trip.legs.find(item => item.id === legId), field = `pod_file_${index + 1}`, signatureField = `signature_file_${index + 1}`;
    const signatureBlob = await deliverySignatureBlob(signatureCanvas);
    podEntries.push({leg_id:legId, vehicle_id:row.trip.vehicle_id || row.order.vehicle_id, stop_no:leg.sequence_no, location_text:leg.stop_name || leg.destination, receiver_name:receiver, receiver_phone:phone, delivery_time:new Date(time).toISOString(), delivery_result:stop.querySelector('[data-pod="result"]').value, cargo_condition:condition, file_field:field, signature_file_field:signatureField, note:condition});
    files[field] = file;
    files[signatureField] = new File([signatureBlob], `signature-${row.order.id}-${index + 1}.png`, {type:'image/png'});
  }
  if (!podEntries.length) return showToast('Trip chưa có chặng giao hàng để nộp POD.', 'error');
  const invalidCharge = deliveryCompletionState.charges.find(line => !String(line.name || '').trim() || Number(line.actual_amount || 0) < 0);
  if (invalidCharge) return showToast('Khoản chi phí cần có tên và giá thực tế hợp lệ.', 'warning');
  const payload = {trip_id:row.trip.id, currency_code:row.currency, pod_entries:podEntries, charge_adjustments:deliveryCompletionState.charges.map(line => ({name:String(line.name).trim(), original_amount:String(line.original_amount || 0), actual_amount:String(line.actual_amount || 0), note:line.note || null, cost_index:(line.cost_index || '').trim() || null}))};
  const form = new FormData(); form.append('payload', JSON.stringify(payload)); Object.entries(files).forEach(([field,file]) => form.append(field,file));
  const button = document.getElementById('completion-submit'); if (button) button.disabled = true;
  showToast(`Đang lưu POD và chốt giá DO ${row.order.id}...`, 'loading');
  try {
    const response = await fetch(`${API_BASE}/api/delivery-orders/${encodeURIComponent(row.order.id)}/complete-delivery`, {method:'POST', headers:{...financeAuthHeaders(),'Idempotency-Key':deliveryCompletionState.submissionKey}, body:form});
    const result = await response.json();
    if (!response.ok) throw new Error(result?.detail?.message || result?.error?.message || 'Không thể hoàn tất giao hàng.');
    closeDeliveryCompletionEditor();
    showToast(`Đã hoàn tất ${row.order.id}. Giá cuối: ${completionMoney(result.data.commercials.final_selling_price, result.data.commercials.currency_code)}.`, 'success');
    deliveryCompletionState.tab = 'completed'; document.querySelectorAll('.completion-tab').forEach(item => item.classList.toggle('active', item.dataset.completionTab === 'completed'));
    await loadDeliveryCompletionWorkbench();
    viewCompletedDelivery(row.order.id);
  } catch (error) { showToast(error.message, 'error'); } finally { if (button) button.disabled = false; }
};

window.viewCompletedDelivery = async function (doId) {
  const target = document.getElementById('completion-history-detail');
  if (!target) return;
  target.hidden = false; target.innerHTML = '<div class="completion-empty">Đang tải hồ sơ đã giao...</div>';
  try {
    const response = await fetch(`${API_BASE}/api/delivery-orders/${encodeURIComponent(doId)}/closeout`, {headers:financeAuthHeaders()}), data = await response.json();
    if (!response.ok) throw new Error(data?.detail?.message || 'Không tải được hồ sơ.');
    // BẢN VẼ ĐẦY ĐỦ, không phải bản tóm tắt. Trước đây khối này chỉ hiện năm
    // con số tổng (giá SO, giá cuối, chi phí, margin) trong khi máy chủ đã trả
    // `ledger_lines` — từng dòng thu/chi có Acc code — và chỉ màn Theo dõi vẽ
    // nó. Anh Khang lấy hồ sơ từ MÀN NÀY để lập phiếu thu/chi, nên dùng chung
    // `renderDeliveryOrderCloseout` để hai màn không bao giờ lệch nhau nữa.
    target.innerHTML = `<header class="completion-editor-header"><div><span class="completion-eyebrow">Hồ sơ đã hoàn tất</span><h3>${completionEscape(doId)}</h3></div><button class="icon-button" title="Đóng (Esc)" onclick="dongHoSoNoi()"><i class="fa-solid fa-xmark"></i></button></header><div id="completion-history-closeout" class="completion-history-closeout"></div>`;
    renderDeliveryOrderCloseout(data, document.getElementById('completion-history-closeout'));
    moHoSoNoi(target);
  } catch (error) { target.innerHTML = `<div class="completion-empty">${completionEscape(error.message)}</div>`; showToast(error.message,'error'); }
};

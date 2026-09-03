/**
 * Gắn bearer token vào mọi lệnh gọi API, tại một chỗ duy nhất.
 *
 * Backend giờ xác thực theo kiểu mặc định-chặn (xem backend/app/auth_middleware.py),
 * nên tất cả các đường /api/ đều cần header Authorization. Ứng dụng có hơn 80
 * lệnh gọi fetch rải rác, nên việc gắn header được đặt trong một lớp bọc fetch
 * thay vì sửa từng chỗ gọi — cùng lý do như phía server: một điểm sửa thì không
 * bỏ sót, còn sửa 80 chỗ thì chắc chắn sót.
 *
 * Token do người vận hành đặt vào localStorage một lần:
 *   localStorage.setItem('EPL_TMS_API_TOKEN', '<token>')
 *
 * Trước đây server tự chèn token vào HTML của trang chủ, nhưng `GET /` là đường
 * công khai nên làm vậy là trao bí mật của server cho mọi khách vãng lai.
 */
(function installApiAuth(global) {
  'use strict';

  const TOKEN_KEY = 'EPL_TMS_API_TOKEN';
  const PUBLIC_PATHS = ['/api/health', '/api/parking-qr/'];

  function readToken() {
    try {
      const stored = global.localStorage && global.localStorage.getItem(TOKEN_KEY);
      if (stored && String(stored).trim()) return String(stored).trim();
    } catch (error) {
      // Cửa sổ ẩn danh hoặc trình duyệt chặn lưu trữ: coi như chưa có token.
    }
    return '';
  }

  function storeToken(token) {
    const value = String(token || '').trim();
    if (!value) return false;
    try {
      global.localStorage.setItem(TOKEN_KEY, value);
      return true;
    } catch (error) {
      return false;
    }
  }

  function isApiRequest(url) {
    const path = String(url || '');
    if (path.startsWith('/api/')) return true;
    // Đường dẫn tuyệt đối cùng origin cũng phải được gắn header.
    try {
      const parsed = new URL(path, global.location && global.location.href);
      return parsed.origin === global.location.origin
        && parsed.pathname.startsWith('/api/');
    } catch (error) {
      return false;
    }
  }

  function isPublic(url) {
    let pathname = String(url || '');
    try {
      pathname = new URL(pathname, global.location && global.location.href).pathname;
    } catch (error) {
      // giữ nguyên chuỗi đã có
    }
    return PUBLIC_PATHS.some(prefix => pathname.startsWith(prefix));
  }

  let missingTokenNotified = false;

  function warnMissingToken() {
    if (missingTokenNotified) return;
    missingTokenNotified = true;
    const message = 'Chưa cấu hình token API nên hệ thống không tải được dữ liệu. '
      + 'Mở Console và chạy: localStorage.setItem(\'' + TOKEN_KEY + '\', \'<token>\')';
    if (typeof global.showToast === 'function') {
      global.showToast(message, 'error');
    } else if (global.console && global.console.error) {
      global.console.error('[EPL] ' + message);
    }
  }

  const nativeFetch = global.fetch ? global.fetch.bind(global) : null;
  if (!nativeFetch) return;

  global.fetch = function authenticatedFetch(resource, options) {
    const url = (resource && typeof resource === 'object' && 'url' in resource)
      ? resource.url
      : resource;

    if (!isApiRequest(url) || isPublic(url)) {
      return nativeFetch(resource, options);
    }

    const token = readToken();
    if (!token) {
      warnMissingToken();
      return nativeFetch(resource, options);
    }

    const next = Object.assign({}, options || {});
    const headers = new Headers((options && options.headers) || {});
    // Không ghi đè header do chỗ gọi tự đặt (ví dụ financeAuthHeaders).
    if (!headers.has('Authorization')) {
      headers.set('Authorization', 'Bearer ' + token);
    }
    next.headers = headers;
    return nativeFetch(resource, next).then(response => {
      if (response && response.status === 401) {
        missingTokenNotified = false;
        warnMissingToken();
      }
      return response;
    });
  };

  // Tiện ích cho người vận hành, gọi được từ Console.
  global.eplSetApiToken = function eplSetApiToken(token) {
    const saved = storeToken(token);
    if (saved) {
      missingTokenNotified = false;
      if (typeof global.showToast === 'function') {
        global.showToast('Đã lưu token API. Đang tải lại trang.', 'success');
      }
      global.setTimeout(() => global.location.reload(), 400);
    }
    return saved;
  };

  global.eplHasApiToken = function eplHasApiToken() {
    return Boolean(readToken());
  };
})(typeof window !== 'undefined' ? window : globalThis);

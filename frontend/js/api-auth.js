/**
 * Gắn bearer token vào mọi lệnh gọi API, tại một chỗ duy nhất.
 *
 * Bình thường KHÔNG cần token: hệ thống này là một module bên trong một hệ
 * thống lớn hơn, và việc đăng nhập do hệ thống cha lo, nên backend mặc định
 * không chặn (xem backend/app/auth_middleware.py). Lớp bọc này vẫn tồn tại vì
 * backend bật lại được cổng token bằng EPL_REQUIRE_API_TOKEN=1 khi chạy độc
 * lập ở nơi không có hệ thống cha đứng trước.
 *
 * Ứng dụng có hơn 80 lệnh gọi fetch rải rác, nên việc gắn header được đặt
 * trong một lớp bọc fetch thay vì sửa từng chỗ gọi — cùng lý do như phía
 * server: một điểm sửa thì không bỏ sót, còn sửa 80 chỗ thì chắc chắn sót.
 *
 * Khi cổng token được bật, người vận hành đặt token một lần cho mỗi trình
 * duyệt bằng: eplSetApiToken('<token>')
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

  /**
   * Chỉ báo khi máy chủ THỰC SỰ từ chối (401), không báo chỉ vì thiếu token.
   *
   * Hệ thống này là một module bên trong một hệ thống lớn hơn, và việc đăng
   * nhập do hệ thống cha lo, nên bình thường KHÔNG có token nào cả — và đó là
   * trạng thái đúng, không phải lỗi. Báo đỏ mỗi lần mở trang chỉ làm người
   * dùng tưởng hỏng.
   */
  function warnRejectedSession() {
    if (missingTokenNotified) return;
    missingTokenNotified = true;
    const message = 'Máy chủ từ chối phiên làm việc nên chưa tải được dữ liệu. '
      + 'Nếu máy chủ đang bật EPL_REQUIRE_API_TOKEN, hãy đặt token bằng: eplSetApiToken(\'<token>\')';
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
      // Không có token là bình thường: cứ gửi đi, để máy chủ quyết định. Máy
      // chủ mặc định không chặn, nên lệnh gọi chạy bình thường.
      return nativeFetch(resource, options).then(response => {
        if (response && response.status === 401) warnRejectedSession();
        return response;
      });
    }

    const next = Object.assign({}, options || {});
    const headers = new Headers((options && options.headers) || {});
    // Không ghi đè header do chỗ gọi tự đặt (ví dụ financeAuthHeaders).
    if (!headers.has('Authorization')) {
      headers.set('Authorization', 'Bearer ' + token);
    }
    next.headers = headers;
    return nativeFetch(resource, next).then(response => {
      // KHÔNG đặt lại missingTokenNotified ở đây. Đặt lại nghĩa là mỗi lệnh
      // gọi 401 lại bật một thông báo mới, mà lúc token hỏng thì cả 80 lệnh
      // gọi cùng 401 — người dùng lãnh 80 thông báo đỏ liên tiếp. Cờ này chỉ
      // được mở lại khi có token mới (xem eplSetApiToken).
      if (response && response.status === 401) warnRejectedSession();
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

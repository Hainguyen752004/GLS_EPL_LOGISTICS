(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.CommandPolicy = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  function normalizeCommandError(body, fallback = 'Không thể hoàn tất thao tác. Vui lòng kiểm tra dữ liệu và thử lại.') {
    const detail = body?.detail;
    if (detail && typeof detail === 'object') {
      return {
        message: detail.message || fallback,
        // Mã lỗi để màn quyết định cách xử lý (VD: VEHICLE_TYPE_MISMATCH → hỏi
        // xác nhận rồi gửi lại), thay vì chỉ hiện chữ.
        code: typeof detail.code === 'string' ? detail.code : '',
        navigation_targets: Array.isArray(detail.navigation_targets) ? detail.navigation_targets : []
      };
    }
    return { message: typeof detail === 'string' ? detail : fallback, navigation_targets: [] };
  }

  async function executeCommand({ request, applySuccess, reload, onError }) {
    try {
      const response = await request();
      let payload = {};
      try { payload = await response.json(); } catch (_) { payload = {}; }
      if (!response.ok) {
        const error = normalizeCommandError(payload);
        if (typeof onError === 'function') onError(error);
        return { ok: false, status: response.status, error };
      }
      if (typeof applySuccess === 'function') await applySuccess(payload);
      if (typeof reload === 'function') await reload();
      return { ok: true, status: response.status, payload };
    } catch (_) {
      const error = { message: 'Mất kết nối máy chủ. Dữ liệu chưa được thay đổi; vui lòng thử lại.', navigation_targets: [] };
      if (typeof onError === 'function') onError(error);
      return { ok: false, status: 0, error };
    }
  }

  return { normalizeCommandError, executeCommand };
});

(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.RouteSegmentPolicy = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const MANUAL_SOURCES = new Set(['odometer', 'carrier_document', 'map_measurement', 'other']);

  function validateManualDistance({ km, confirmed, source, verifier, now = () => new Date().toISOString() }) {
    const distance = Number(km);
    if (!Number.isFinite(distance) || distance <= 0 || distance > 5000) {
      return { ok: false, code: 'INVALID_DISTANCE', message: 'Khoảng cách phải lớn hơn 0 và không quá 5.000 km.' };
    }
    if (!confirmed || !MANUAL_SOURCES.has(source)) {
      return { ok: false, code: 'MANUAL_DISTANCE_CONFIRMATION_REQUIRED', message: 'Vui lòng xác nhận và chọn nguồn khoảng cách thủ công.' };
    }
    return {
      ok: true,
      segment: {
        distance_km: distance,
        distance_source: source,
        distance_verified_by: String(verifier || 'system'),
        distance_verified_at: now(),
      },
    };
  }

  async function resolveSegment({ from, to, manual, routingClient, persist }) {
    if (!from || !to) return { ok: false, code: 'MISSING_LOCATION', message: 'Thiếu điểm đi hoặc điểm đến.' };
    let segment;
    if (manual) {
      const result = validateManualDistance(manual);
      if (!result.ok) return result;
      segment = { from, to, ...result.segment };
    } else {
      try {
        const routed = await routingClient(from, to);
        if (!routed || !Number.isFinite(Number(routed.distKm)) || Number(routed.distKm) <= 0) throw new Error('NO_ROUTE');
        segment = { from, to, distance_km: Number(routed.distKm), distance_source: 'routing_service', ...routed };
      } catch (_) {
        return { ok: false, code: 'ROUTING_UNAVAILABLE', message: 'Không tính được khoảng cách thực tế. Vui lòng kiểm tra địa điểm hoặc nhập khoảng cách thủ công có xác nhận.' };
      }
    }
    if (typeof persist === 'function') persist(segment);
    return { ok: true, segment };
  }

  function serializeSegments(segments) {
    return JSON.stringify(Array.isArray(segments) ? segments : []);
  }

  function deserializeSegments(value) {
    if (Array.isArray(value)) return value;
    try {
      const parsed = JSON.parse(value || '[]');
      return Array.isArray(parsed) ? parsed : [];
    } catch (_) {
      return [];
    }
  }

  return { validateManualDistance, resolveSegment, serializeSegments, deserializeSegments };
});

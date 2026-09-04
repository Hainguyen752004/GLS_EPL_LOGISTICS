(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  }
  root.RouteMapUtils = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  function normalizeText(value) {
    return String(value || '').trim();
  }

  function parseSegments(routeOrSegments) {
    if (Array.isArray(routeOrSegments)) return routeOrSegments;
    if (!routeOrSegments) return [];

    const raw = routeOrSegments.segments_json || routeOrSegments.segments || [];
    if (Array.isArray(raw)) return raw;

    if (typeof raw === 'string') {
      try {
        const parsed = JSON.parse(raw || '[]');
        return Array.isArray(parsed) ? parsed : [];
      } catch (error) {
        return [];
      }
    }

    return [];
  }

  function buildOrderedRouteLocations(routeOrSegments) {
    const segments = parseSegments(routeOrSegments);
    const locations = [];

    for (const segment of segments) {
      const from = normalizeText(segment && (segment.from || segment.origin));
      const to = normalizeText(segment && (segment.to || segment.destination));

      if (!from || !to) return [];

      if (locations[locations.length - 1] !== from) {
        locations.push(from);
      }

      if (locations[locations.length - 1] !== to) {
        locations.push(to);
      }
    }

    return locations;
  }

  function buildRouteContext(routeOrSegments) {
    const locations = buildOrderedRouteLocations(routeOrSegments);
    if (locations.length < 2) return {};

    return {
      origin: locations[0],
      destination: locations[locations.length - 1]
    };
  }

  function segmentDistanceKm(segment) {
    const value = Number(segment && (
      segment.distance_km ?? segment.dist_km ?? segment.distance ?? segment.km
    ));
    return Number.isFinite(value) && value > 0 ? value : 0;
  }

  function buildRouteCheckpointModel(routeOrSegments) {
    const segments = parseSegments(routeOrSegments);
    const checkpoints = [];

    for (const segment of segments) {
      const from = normalizeText(segment && (segment.from || segment.origin));
      const to = normalizeText(segment && (segment.to || segment.destination));
      if (!from || !to) return [];

      if (!checkpoints.length || checkpoints[checkpoints.length - 1].label !== from) {
        checkpoints.push({ label: from, role: 'checkpoint', distanceFromPreviousKm: 0 });
      }
      if (checkpoints[checkpoints.length - 1].label !== to) {
        checkpoints.push({
          label: to,
          role: 'checkpoint',
          distanceFromPreviousKm: segmentDistanceKm(segment)
        });
      }
    }

    if (checkpoints.length < 2) return [];
    checkpoints[0].role = 'origin';
    checkpoints[checkpoints.length - 1].role = 'destination';
    return checkpoints;
  }

  function makeWaypoint(label, lat, lng) {
    const parsedLat = Number(lat);
    const parsedLng = Number(lng);
    if (!Number.isFinite(parsedLat) || !Number.isFinite(parsedLng)) return null;

    return {
      lat: parsedLat,
      lng: parsedLng,
      label: normalizeText(label)
    };
  }

  function buildStoredCoordinateWaypoints(routeOrSegments) {
    const segments = parseSegments(routeOrSegments);
    const waypoints = [];

    for (const segment of segments) {
      const from = normalizeText(segment && (segment.from || segment.origin));
      const to = normalizeText(segment && (segment.to || segment.destination));
      const fromPoint = makeWaypoint(from, segment && (segment.from_lat ?? segment.origin_lat), segment && (segment.from_lng ?? segment.origin_lng));
      const toPoint = makeWaypoint(to, segment && (segment.to_lat ?? segment.destination_lat), segment && (segment.to_lng ?? segment.destination_lng));

      if (!from || !to || !fromPoint || !toPoint) return [];

      if (!waypoints.length || waypoints[waypoints.length - 1].label !== fromPoint.label) {
        waypoints.push(fromPoint);
      }

      if (waypoints[waypoints.length - 1].label !== toPoint.label) {
        waypoints.push(toPoint);
      }
    }

    return waypoints.length >= 2 ? waypoints : [];
  }

  async function resolveRouteWaypoints(route, geocodeFn) {
    const storedWaypoints = buildStoredCoordinateWaypoints(route);
    if (storedWaypoints.length >= 2) return storedWaypoints;

    if (typeof geocodeFn !== 'function') return [];

    const locations = buildOrderedRouteLocations(route);
    if (locations.length < 2) return [];

    const waypoints = [];
    for (const location of locations) {
      let geocoded;
      try {
        geocoded = await geocodeFn(location);
      } catch (error) {
        return [];
      }

      if (!geocoded || typeof geocoded !== 'object') return [];

      const lat = Number(geocoded && geocoded.lat);
      const lng = Number(geocoded && (geocoded.lng ?? geocoded.lon));
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) return [];

      waypoints.push({
        lat,
        lng,
        label: normalizeText(geocoded && geocoded.label) || location
      });
    }

    return waypoints;
  }

  async function drawSavedRoute(route, geocodeFn, drawFn) {
    if (typeof drawFn !== 'function') return false;

    const waypoints = await resolveRouteWaypoints(route, geocodeFn);
    if (waypoints.length < 2) return false;

    await drawFn(waypoints, route && route.id, route && route.name);
    return true;
  }

  /**
   * Vai tro cua tung diem tren mot tuyen.
   *
   * Bang mau da qua scripts/validate_palette.js (che do light, xet DU MOI CAP):
   * CVD DeltaE 8.6, thi luc binh thuong DeltaE 29.3 — dat nguong o moi kiem tra.
   *
   * Mau KHONG BAO GIO dung mot minh: diem di va diem den co icon rieng, diem
   * trung chuyen mang so thu tu, va thanh chu giai duoi ban do liet ke theo
   * dung thu tu di. Nguoi khong phan biet duoc do—xanh van doc duoc tuyen.
   *
   * Mau xanh cua diem trung chuyen trung voi mau duong ke tuyen (#0a6ed1) la
   * co y: chung deu la "dang tren duong", con do va xanh la la hai dau mut.
   */
  const WAYPOINT_ROLES = {
    origin: { color: '#dc2626', icon: 'fa-flag', label: 'Điểm đi' },
    stop: { color: '#1d4ed8', icon: 'fa-circle-dot', label: 'Điểm trung chuyển' },
    destination: { color: '#059669', icon: 'fa-flag-checkered', label: 'Điểm đến' }
  };

  /**
   * Gan vai tro, mau va ky hieu cho tung diem theo THU TU DI.
   *
   * Tach rieng khoi phan ve de kiem chung duoc bang Node: mau va thu tu la
   * phan de sai nhat, va cung la phan nguoi dung doc.
   */
  function buildWaypointMarkerModel(waypoints) {
    const list = Array.isArray(waypoints) ? waypoints.filter(item => item && typeof item === 'object') : [];
    const last = list.length - 1;
    return list.map((waypoint, index) => {
      // Mot diem duy nhat thi no la diem di: chua co dau den nao ca.
      const role = index === 0 ? 'origin' : index === last ? 'destination' : 'stop';
      const tone = WAYPOINT_ROLES[role];
      return {
        lat: Number(waypoint.lat),
        lng: Number(waypoint.lng),
        label: normalizeText(waypoint.label),
        index,
        order: index + 1,
        role,
        roleLabel: tone.label,
        color: tone.color,
        icon: tone.icon,
        // Diem dau va diem cuoi deo icon; diem giua deo so thu tu.
        glyph: role === 'stop' ? String(index + 1) : ''
      };
    });
  }

  return {
    WAYPOINT_ROLES,
    buildWaypointMarkerModel,
    buildOrderedRouteLocations,
    buildRouteContext,
    buildRouteCheckpointModel,
    buildStoredCoordinateWaypoints,
    resolveRouteWaypoints,
    drawSavedRoute
  };
});

(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.WorkflowUIUtils = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const VI = {
    draft: 'B\u1ea3n nh\u00e1p',
    lead: 'Kh\u00e1ch ti\u1ec1m n\u0103ng',
    negotiation: '\u0110ang \u0111\u00e0m ph\u00e1n',
    quoted: '\u0110\u00e3 b\u00e1o gi\u00e1',
    approved: '\u0110\u00e3 duy\u1ec7t',
    confirmed: '\u0110\u00e3 x\u00e1c nh\u1eadn',
    won: '\u0110\u00e3 ch\u1ed1t',
    pending: 'Ch\u1edd x\u1eed l\u00fd',
    pending_approval: 'Ch\u1edd duy\u1ec7t',
    planned: '\u0110\u00e3 l\u1eadp k\u1ebf ho\u1ea1ch',
    picked: '\u0110\u00e3 l\u1ea5y h\u00e0ng',
    packed: '\u0110\u00e3 \u0111\u00f3ng g\u00f3i',
    ready_for_dispatch: 'S\u1eb5n s\u00e0ng \u0111i\u1ec1u ph\u1ed1i',
    in_transit: '\u0110ang v\u1eadn chuy\u1ec3n',
    // Ba m\u1ed1c t\u00e1ch r\u00f5. "\u0110\u00e3 giao" m\u01a1 h\u1ed3: xe t\u1edbi b\u00e3i m\u00e0 ch\u01b0a k\u00fd POD th\u00ec theo
    // c\u00e1ch hi\u1ec3u th\u01b0\u1eddng c\u0169ng l\u00e0 "\u0111\u00e3 giao", nh\u01b0ng l\u00fac \u0111\u00f3 ch\u01b0a c\u00f3 g\u00ec x\u00e1c nh\u1eadn.
    // C\u00f2n `delivered` l\u00e0 \u0111\u00e3 k\u00fd POD, \u0111\u00e3 ch\u1ed1t gi\u00e1, \u0111\u00e3 h\u1ea1ch to\u00e1n.
    arrived: '\u0110\u00e3 \u0111\u1ebfn n\u01a1i \u2014 ch\u1edd POD',
    delivered: '\u0110\u00e3 ho\u00e0n t\u1ea5t',
    completed: 'Ho\u00e0n t\u1ea5t',
    posted: '\u0110\u00e3 h\u1ea1ch to\u00e1n',
    cancelled: '\u0110\u00e3 h\u1ee7y',
    maintenance: 'B\u1ea3o d\u01b0\u1ee1ng',
    available: 'S\u1eb5n s\u00e0ng',
    busy: 'B\u1eadn',
    active: '\u0110ang ho\u1ea1t \u0111\u1ed9ng',
    inactive: 'Ng\u01b0ng ho\u1ea1t \u0111\u1ed9ng',
    paid: '\u0110\u00e3 thanh to\u00e1n',
    unpaid: 'Ch\u01b0a thanh to\u00e1n'
  };

  const STATUS_KEYS = {
    draft: ['draft', VI.draft, 'ban nhap', 'nhap'],
    lead: ['lead', VI.lead, 'khach tiem nang'],
    negotiation: ['negotiation', VI.negotiation, 'dang dam phan'],
    quoted: ['quoted', VI.quoted, 'da bao gia'],
    approved: ['approved', VI.approved, 'da duyet'],
    confirmed: ['confirmed', VI.confirmed, 'won', VI.won, 'da xac nhan', 'da chot'],
    pending: ['pending', VI.pending, 'cho xu ly'],
    pending_approval: ['pending approval', VI.pending_approval, 'cho duyet'],
    planned: ['planned', VI.planned, 'lap ke hoach', 'da lap ke hoach'],
    picked: ['picked', VI.picked, 'da lay hang'],
    packed: ['packed', VI.packed, 'da dong goi'],
    ready_for_dispatch: ['ready for dispatch', VI.ready_for_dispatch, 'san sang dieu phoi'],
    in_transit: ['in transit', VI.in_transit, 'dang van chuyen', 'dang giao hang'],
    // Giữ cả bí danh cũ: dữ liệu và thiết bị cũ còn gửi những chuỗi đó.
    arrived: ['arrived', VI.arrived, 'da den noi', 'da den noi cho pod'],
    delivered: ['delivered', VI.delivered, 'da giao hang', 'da hoan tat'],
    completed: ['completed', VI.completed, 'hoan tat'],
    posted: ['posted', VI.posted, 'da hach toan'],
    cancelled: ['cancelled', 'canceled', VI.cancelled, 'da huy'],
    maintenance: ['maintenance', VI.maintenance, 'bao duong'],
    available: ['available', 'ready', VI.available, 'san sang', 'ranh'],
    busy: ['busy', VI.busy, 'ban'],
    active: ['active', VI.active, 'dang hoat dong'],
    inactive: ['inactive', VI.inactive, 'ngung hoat dong'],
    paid: ['paid', VI.paid, 'da thanh toan'],
    unpaid: ['unpaid', VI.unpaid, 'chua thanh toan']
  };

  const LOCKED_KEYS = new Set([
    'approved', 'confirmed', 'planned', 'picked', 'packed',
    'ready_for_dispatch', 'in_transit', 'arrived', 'delivered',
    'completed', 'posted', 'cancelled'
  ]);

  function fixVietnameseMojibake(value) {
    return value === null || value === undefined ? value : String(value);
  }

  function normalizeForKey(status) {
    return String(status || '')
      .toLowerCase()
      .trim()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/\u0111/g, 'd')
      .replace(/\s+/g, ' ');
  }

  function workflowStatusKey(status) {
    const fixed = String(status || '').trim();
    const normalized = normalizeForKey(fixed);
    for (const [key, labels] of Object.entries(STATUS_KEYS)) {
      if (labels.some((label) => normalizeForKey(label) === normalized)) return key;
    }
    return normalized;
  }

  function statusLabel(status) {
    if (status === null || status === undefined || status === '') return '';
    const fixed = String(status);
    return VI[workflowStatusKey(fixed)] || fixed;
  }

  function isLockedWorkflowStatus(status) {
    return LOCKED_KEYS.has(workflowStatusKey(status));
  }

  function workflowActionMode(status) {
    const locked = isLockedWorkflowStatus(status);
    return { canEdit: !locked, canDelete: !locked, canView: true };
  }

  const CAPACITY_DIMENSIONS = [
    { dimension: 'weight', demand: 'weight_kg', capacity: ['max_weight', 'maxWeight', 'weight_capacity'], unit: 'kg' },
    { dimension: 'volume', demand: 'volume_m3', capacity: ['volume_capacity_m3', 'volumeCapacityM3'], unit: 'm³' },
    { dimension: 'pallet', demand: 'pallet_count', capacity: ['pallet_capacity', 'palletCapacity'], unit: 'pallet' }
  ];

  function firstCapacityValue(source, keys) {
    for (const key of keys) {
      const parsed = Number(source && source[key]);
      if (Number.isFinite(parsed)) return parsed;
    }
    return 0;
  }

  function evaluateVehicleCapacity(vehicleType, demand) {
    const reasons = [];
    const ratios = [];
    CAPACITY_DIMENSIONS.forEach(config => {
      const required = Number(demand && demand[config.demand]) || 0;
      const capacity = firstCapacityValue(vehicleType, config.capacity);
      if (required <= 0) return;
      if (capacity <= 0) {
        reasons.push({ ...config, required, capacity, code: 'CAPACITY_NOT_CONFIGURED' });
        return;
      }
      ratios.push(required / capacity);
      if (required > capacity) {
        reasons.push({ ...config, required, capacity, code: 'CAPACITY_EXCEEDED' });
      }
    });
    return {
      fits: reasons.length === 0,
      reasons,
      utilizationPct: Math.round(Math.max(0, ...ratios) * 1000) / 10,
      fitScore: ratios.length ? ratios.reduce((sum, ratio) => sum + ratio, 0) / ratios.length : 0
    };
  }

  function recommendVehicleTypes(vehicleTypes, demand) {
    const evaluated = (Array.isArray(vehicleTypes) ? vehicleTypes : []).map(vehicleType => ({
      vehicleType,
      ...evaluateVehicleCapacity(vehicleType, demand)
    }));
    const suitable = evaluated
      .filter(item => item.fits)
      .sort((a, b) => b.fitScore - a.fitScore ||
        firstCapacityValue(a.vehicleType, ['max_weight', 'maxWeight']) - firstCapacityValue(b.vehicleType, ['max_weight', 'maxWeight']));
    const unsuitable = evaluated
      .filter(item => !item.fits)
      .sort((a, b) => firstCapacityValue(a.vehicleType, ['max_weight', 'maxWeight']) - firstCapacityValue(b.vehicleType, ['max_weight', 'maxWeight']));
    return { suitable, unsuitable };
  }

  return {
    fixVietnameseMojibake,
    statusLabel,
    workflowStatusKey,
    isLockedWorkflowStatus,
    workflowActionMode,
    evaluateVehicleCapacity,
    recommendVehicleTypes
  };
});

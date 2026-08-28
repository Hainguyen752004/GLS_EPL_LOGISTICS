(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.TmsCockpit = factory();
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const STATUS_DONE = new Set(['approved', 'confirmed', 'planned', 'dispatched', 'picked', 'packed', 'in_transit', 'arrived', 'delivered', 'completed', 'posted', 'paid']);
  const FINANCE_PENDING = new Set(['draft', 'submitted', 'approved', 'partially_paid', 'open', 'pending']);

  function list(state, key) {
    return Array.isArray(state && state[key]) ? state[key] : [];
  }

  function normalized(value) {
    return String(value || '').trim().toLowerCase().replace(/\s+/g, '_');
  }

  function numberValue(value) {
    const parsed = Number(value || 0);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function statusLabel(status) {
    const labels = {
      draft: 'Nháp',
      submitted: 'Đã gửi duyệt',
      approved: 'Đã duyệt',
      posted: 'Đã hạch toán',
      paid: 'Đã thanh toán',
      partially_paid: 'Thanh toán một phần',
      open: 'Đang mở',
      planned: 'Đã lập kế hoạch',
      dispatched: 'Đã điều phối',
      in_transit: 'Đang vận chuyển',
      arrived: 'Đã đến nơi',
      delivered: 'Đã giao hàng',
      completed: 'Hoàn tất',
      reversed: 'Đã đảo bút toán',
      cancelled: 'Đã hủy',
      active: 'Đang hoạt động',
      inactive: 'Ngưng hoạt động',
      closed: 'Đã khóa'
    };
    return labels[normalized(status)] || (status || 'Chưa rõ');
  }

  function shortDate(value) {
    return value ? String(value).slice(0, 10) : 'Chưa cấu hình';
  }

  function hasActive(rows) {
    return rows.some(row => {
      const status = normalized(row.status || row.canonical_status || row.is_active);
      return !['inactive', 'disabled', 'closed', 'false', 'deleted'].includes(status);
    });
  }

  function setupItem(key, label, target, rows, description) {
    const done = hasActive(rows);
    return {
      key,
      label,
      target,
      status: done ? 'done' : 'missing',
      icon: done ? 'fa-circle-check' : 'fa-triangle-exclamation',
      message: done
        ? 'Đã có dữ liệu để chạy luồng.'
        : `Thiếu ${label}. Vào Master Data → ${description} để cấu hình trước khi chạy demo.`
    };
  }

  function buildMasterSetupChecklist(state) {
    return [
      setupItem('currency', 'tiền tệ', 'master-data/currencies', list(state, 'currencies'), 'Tiền tệ'),
      setupItem('tax', 'mã thuế', 'master-data/tax-codes', list(state, 'tax_codes'), 'Thuế'),
      setupItem('accounting_period', 'kỳ kế toán', 'master-data/accounting-periods', list(state, 'accounting_periods'), 'Kỳ kế toán'),
      setupItem('customer', 'khách hàng', 'master-data/customers', list(state, 'customers'), 'Khách hàng'),
      setupItem('route', 'tuyến đường', 'master-data/routes', list(state, 'routes'), 'Tuyến đường'),
      setupItem('vehicle_driver', 'xe và tài xế', 'master-data/vehicles', [...list(state, 'vehicles'), ...list(state, 'drivers')], 'Xe / Tài xế'),
      setupItem('carrier', 'carrier/vendor', 'master-data/carriers', list(state, 'carriers'), 'Carrier / Vendor'),
      setupItem('account_mapping', 'mapping tài khoản', 'master-data/chart-of-accounts', list(state, 'account_mappings'), 'Mapping tài khoản')
    ];
  }

  function isWaitingDispatch(order) {
    const status = normalized(order.status || order.canonical_status);
    return ['approved', 'planned', 'ready_for_dispatch', 'packed'].includes(status);
  }

  function isAvailableVehicle(vehicle) {
    const status = normalized(vehicle.status);
    return ['available', 'ready', 'rảnh', 'sẵn_sàng', 'sẵn_sàng_hoạt_động'].includes(status);
  }

  function isTripLate(order, now) {
    const status = normalized(order.status || order.canonical_status);
    if (['delivered', 'completed', 'cancelled'].includes(status)) return false;
    const eta = order.eta || order.planned_delivery_at || order.delivery_window_end;
    if (!eta) return false;
    const etaDate = new Date(eta);
    return !Number.isNaN(etaDate.getTime()) && etaDate < now;
  }

  function buildControlTower(state, now = new Date()) {
    const deliveryOrders = list(state, 'delivery_orders');
    const pods = list(state, 'pods');
    const podSet = new Set(pods.map(p => String(p.do_id || p.delivery_order_id || p.id)));
    const delivered = deliveryOrders.filter(order => normalized(order.status || order.canonical_status) === 'delivered');
    const financePending = [
      ...list(state, 'freight_actual_costs'),
      ...list(state, 'ap_invoices'),
      ...list(state, 'settlements')
    ].filter(row => FINANCE_PENDING.has(normalized(row.status)));

    return {
      waiting_dispatch: {
        label: 'Đơn chờ điều phối',
        count: deliveryOrders.filter(isWaitingDispatch).length,
        target: 'dispatch'
      },
      available_vehicles: {
        label: 'Xe rảnh',
        count: list(state, 'vehicles').filter(isAvailableVehicle).length,
        target: 'master-data/vehicles'
      },
      late_trips: {
        label: 'Chuyến trễ SLA/ETA',
        count: deliveryOrders.filter(order => isTripLate(order, now)).length,
        target: 'tracking'
      },
      missing_pod: {
        label: 'Chuyến thiếu POD',
        count: delivered.filter(order => !podSet.has(String(order.id))).length,
        target: 'tracking'
      },
      finance_pending: {
        label: 'Chi phí/AP chờ xử lý',
        count: financePending.length,
        target: 'accounting'
      }
    };
  }

  function buildTransportationWorkQueue(state, now = new Date()) {
    const deliveryOrders = list(state, 'delivery_orders');
    const freightOrders = list(state, 'freight_orders');
    const tenders = list(state, 'tenders');
    const carriers = list(state, 'carriers');
    const pods = list(state, 'pods');
    const podSet = new Set(pods.map(p => String(p.do_id || p.delivery_order_id || p.id)));
    const tenderFoSet = new Set(tenders.map(tender => String(tender.freight_order_id || tender.fo_id || '')));
    const internalReady = carriers.some(carrier => isActiveRow(carrier) && (carrier.is_internal === true || normalized(carrier.type || carrier.carrier_type) === 'internal'))
      || list(state, 'vehicles').some(isAvailableVehicle)
      || list(state, 'drivers').some(driver => ['available', 'ready', 'rảnh', 'ranh', 'sẵn_sàng', 'san_sang'].includes(normalized(driver.status || (driver.is_active === false ? 'inactive' : 'available'))));

    const workItems = [];
    deliveryOrders.filter(isWaitingDispatch).slice(0, 6).forEach(order => {
      workItems.push({
        code: 'DO_WAITING_DISPATCH',
        severity: 'warning',
        owner: 'Điều phối',
        title: `${order.id || 'DO'} chờ điều phối`,
        message: 'Chọn xe/tài xế, kiểm tra trùng lịch và xác nhận dispatch.',
        action_label: 'Mở Dispatch',
        navigation: { view: 'dispatch', target: 'dispatch' }
      });
    });

    freightOrders
      .filter(order => ['planned', 'ready_for_dispatch'].includes(normalized(order.status || order.canonical_status)) && !tenderFoSet.has(String(order.id || '')))
      .slice(0, 6)
      .forEach(order => {
        workItems.push({
          code: 'FO_INTERNAL_DISPATCH',
          severity: 'info',
          owner: 'Đội xe nội bộ',
          title: `${order.id || 'FO'} có thể đi Dispatch nội bộ`,
          message: internalReady
            ? 'Đã có đội xe/tài xế hoặc carrier nội bộ sẵn sàng; không bắt buộc tender thuê ngoài.'
            : 'Chưa thấy đội xe nội bộ sẵn sàng; kiểm tra Master Data xe/tài xế/carrier nội bộ.',
          action_label: 'Đi Dispatch nội bộ',
          navigation: { view: 'dispatch', target: 'dispatch' }
        });
      });

    freightOrders
      .filter(order => ['ready_for_tender', 'tender_required'].includes(normalized(order.status || order.canonical_status)) || (!internalReady && ['planned', 'ready_for_dispatch'].includes(normalized(order.status || order.canonical_status))))
      .slice(0, 6)
      .forEach(order => {
        workItems.push({
          code: 'FO_NEEDS_TENDER',
          severity: 'critical',
          owner: 'Sourcing/Tender',
          title: `${order.id || 'FO'} cần tender thuê ngoài`,
          message: 'Tạo tender, mời carrier/vendor báo giá và chọn offer phù hợp.',
          action_label: 'Tạo tender thuê ngoài',
          navigation: { view: 'accounting', target: 'tender-cockpit-panel' }
        });
      });

    deliveryOrders.filter(order => isTripLate(order, now)).slice(0, 6).forEach(order => {
      workItems.push({
        code: 'SLA_LATE_TRIP',
        severity: 'critical',
        owner: 'Control Tower',
        title: `${order.id || 'DO'} trễ SLA/ETA`,
        message: 'Mở GPS/event timeline để kiểm tra nguyên nhân trễ và cập nhật ETA.',
        action_label: 'Xem GPS timeline',
        navigation: { view: 'tracking', target: 'tracking' }
      });
    });

    deliveryOrders
      .filter(order => normalized(order.status || order.canonical_status) === 'delivered' && !podSet.has(String(order.id || '')))
      .slice(0, 6)
      .forEach(order => {
        workItems.push({
          code: 'MISSING_POD',
          severity: 'warning',
          owner: 'POD/Chứng từ',
          title: `${order.id || 'DO'} thiếu POD`,
          message: 'Bổ sung biên bản giao hàng, chữ ký/hình ảnh POD trước khi đối soát.',
          action_label: 'Hoàn tất POD',
          navigation: { view: 'tracking', target: 'pod' }
        });
      });

    return {
      kpis: [
        { key: 'internal_dispatch', label: 'FO có thể đi Dispatch nội bộ', count: workItems.filter(item => item.code === 'FO_INTERNAL_DISPATCH').length },
        { key: 'outsourced_tender', label: 'FO cần tender thuê ngoài', count: workItems.filter(item => item.code === 'FO_NEEDS_TENDER').length },
        { key: 'waiting_dispatch', label: 'DO chờ điều phối', count: workItems.filter(item => item.code === 'DO_WAITING_DISPATCH').length },
        { key: 'exceptions', label: 'Trễ SLA / thiếu POD', count: workItems.filter(item => ['SLA_LATE_TRIP', 'MISSING_POD'].includes(item.code)).length }
      ],
      items: workItems.slice(0, 16),
      empty_message: 'Chưa có việc vận chuyển cần xử lý. Luồng hiện đang sạch.'
    };
  }

  function getTripJourneyPresentation(trip) {
    const source = trip || {};
    const legs = Array.isArray(source.legs) ? source.legs : [];
    const returnLegTypes = new Set(['empty_return', 'backhaul']);
    const normalizedStatus = normalized(source.status);
    const returnLeg = legs.find(leg => returnLegTypes.has(normalized(leg.leg_type)));
    const activeLeg = legs.find(leg => ['in_transit', 'arrived'].includes(normalized(leg.status)));
    const lastCompleted = [...legs].reverse().find(leg => normalized(leg.status) === 'completed');
    const destination = lastCompleted?.destination || legs.find(leg => !returnLegTypes.has(normalized(leg.leg_type)))?.destination || 'điểm giao';
    const origin = returnLeg?.destination || legs[0]?.origin || 'điểm gốc';
    let statusLabel = 'Chờ điều phối';
    let locationLabel = `Đang ở ${origin}`;
    let nextAction = 'Chọn xe và tài xế để điều phối';

    if (normalizedStatus === 'completed') {
      statusLabel = 'Đã hoàn tất';
      locationLabel = `Đã về ${origin}`;
      nextAction = 'Sẵn sàng nhận chuyến mới';
    } else if (activeLeg && returnLegTypes.has(normalized(activeLeg.leg_type))) {
      statusLabel = normalized(activeLeg.leg_type) === 'backhaul' ? 'Đang chở hàng chiều về' : 'Đang quay về rỗng';
      locationLabel = `Đang đi về ${activeLeg.destination || origin}`;
      nextAction = 'Theo dõi thời gian xe về điểm gốc';
    } else if (returnLeg && legs.some(leg => normalized(leg.leg_type) === 'delivery' && normalized(leg.status) === 'completed')) {
      statusLabel = 'Chờ quay về';
      locationLabel = `Đang ở ${destination}`;
      nextAction = 'Chọn hàng chiều về hoặc xác nhận quay về rỗng';
    } else if (activeLeg) {
      statusLabel = 'Đang giao hàng';
      locationLabel = `Đang đến ${activeLeg.destination || destination}`;
      nextAction = 'Theo dõi ETA và cập nhật POD';
    } else if (['dispatched', 'in_transit'].includes(normalizedStatus)) {
      statusLabel = 'Đang thực hiện';
      nextAction = 'Theo dõi chặng và cập nhật sự kiện';
    }

    const legLabels = {
      outbound: 'Di chuyển đến điểm lấy hàng',
      pickup: 'Lấy hàng',
      delivery: 'Giao hàng',
      empty_return: 'Quay về rỗng',
      backhaul: 'Nhận hàng chiều về',
      warehouse_transfer: 'Chuyển kho'
    };
    const legStatuses = {
      planned: 'Chờ thực hiện', ready: 'Sẵn sàng', in_transit: 'Đang thực hiện',
      arrived: 'Đã đến nơi', completed: 'Đã hoàn tất', cancelled: 'Đã hủy'
    };
    return {
      status_label: statusLabel,
      location_label: locationLabel,
      next_action: nextAction,
      legs: legs.map((leg, index) => ({
        ...leg,
        label: legLabels[normalized(leg.leg_type)] || 'Chặng vận chuyển',
        status_label: legStatuses[normalized(leg.status)] || 'Chưa xác định',
        route_label: `${leg.origin || '-'} → ${leg.destination || '-'}`
      }))
    };
  }

  function getTripStatusGroup(trip) {
    const source = trip || {};
    const status = normalized(source.status || source.canonical_status);
    const legs = Array.isArray(source.legs) ? source.legs : [];
    if (status === 'completed') return 'completed';

    const deliveryDone = legs.some(leg => normalized(leg.leg_type) === 'delivery'
      && normalized(leg.status) === 'completed');
    const returnLeg = legs.find(leg => ['empty_return', 'backhaul'].includes(normalized(leg.leg_type)));
    if (deliveryDone && !returnLeg) return 'missing_return';
    if (deliveryDone && returnLeg && !['in_transit', 'arrived', 'completed'].includes(normalized(returnLeg.status))) {
      return 'waiting_return';
    }
    return 'active';
  }

  function buildTripReturnCockpit(state) {
    const trips = list(state, 'transport_trips');
    const deliveryOrders = list(state, 'delivery_orders');
    const tripItems = trips.length ? trips : deliveryOrders
      .filter(order => ['approved', 'planned', 'dispatched', 'in_transit'].includes(normalized(order.status || order.canonical_status)))
      .map(order => ({
        id: order.trip_id || `TRIP-${order.id || 'DO'}`,
        freight_order_id: order.freight_order_id || order.fo_id || '',
        trip_type: order.return_distance_km ? 'round_trip' : 'one_way',
        status: order.status || order.canonical_status || 'planned',
        delivery_order_ids: [order.id],
        planned_departure_at: order.planned_departure_at || order.pickup_window_start,
        planned_arrival_at: order.planned_arrival_at || order.delivery_window_end,
        planned_return_at: order.planned_return_at,
        legs: []
      }));
    const returnTypes = new Set(['round_trip', 'backhaul']);
    const items = tripItems.map(trip => {
      const legs = Array.isArray(trip.legs) ? trip.legs : [];
      const hasReturn = Boolean(trip.planned_return_at) || legs.some(leg => ['empty_return', 'backhaul'].includes(normalized(leg.leg_type)));
      const summary = trip.relationship_summary || {};
      const doCount = Number(summary.do_count || (trip.delivery_order_ids || []).length || 0);
      const hasManyDos = Boolean(summary.has_many_dos_on_trip) || doCount > 1;
      const splitDos = Boolean(summary.has_split_do_across_trips);
      const returnDistance = numberValue(trip.return_distance_km || legs
        .filter(leg => ['empty_return', 'backhaul'].includes(normalized(leg.leg_type)))
        .reduce((sum, leg) => sum + numberValue(leg.distance_km), 0));
      const relationshipParts = [
        hasManyDos ? `1 xe/chuyến đang gom ${doCount} DO` : '1 xe/chuyến xử lý 1 DO chính',
        splitDos ? 'DO chia nhiều xe/chuyến' : 'DO chưa bị chia xe/chuyến'
      ];
      return {
        id: trip.id,
        title: `${trip.id || 'Trip'} · ${statusLabel(trip.status)}`,
        subtitle: `${trip.freight_order_id || 'FO chưa gắn'} · ${(trip.delivery_order_ids || []).join(', ') || 'Chưa chọn DO'}`,
        trip_type: trip.trip_type || 'one_way',
        status: trip.status || 'draft',
        leg_count: legs.length,
        return_label: hasReturn || returnTypes.has(normalized(trip.trip_type)) ? `Có lượt về: ${dateTimeLabel(trip.planned_return_at)}` : 'Chưa lập lượt về/backhaul',
        relationship_label: relationshipParts.join(' · '),
        return_distance_label: `Quãng đường quay đầu: ${returnDistance.toFixed(1)} km`,
        total_distance_label: `Tổng quãng đường: ${numberValue(trip.total_distance_km || legs.reduce((sum, leg) => sum + numberValue(leg.distance_km), 0)).toFixed(1)} km`,
        eta_label: dateTimeLabel(trip.planned_arrival_at),
        planned_return_at: trip.planned_return_at,
        legs,
        raw: trip
      };
    });
    return {
      kpis: [
        { key: 'trip_count', label: 'Tổng Trip', count: items.length },
        { key: 'active_trips', label: 'Đang chạy', count: items.filter(item => ['dispatched', 'in_transit'].includes(normalized(item.status))).length },
        { key: 'return_planned', label: 'Có lượt về/backhaul', count: items.filter(item => item.return_label.startsWith('Có lượt về')).length },
        { key: 'missing_return', label: 'Thiếu kế hoạch về', count: items.filter(item => item.return_label.startsWith('Chưa')).length }
      ],
      items,
      guidance: [
        'DO là yêu cầu vận chuyển; Trip là lần xe chạy thực tế.',
        '1 DO có thể chia nhiều xe/chuyến; 1 xe/chuyến có thể gom nhiều DO nếu cùng tuyến, khung giờ và còn tải.',
        'POD nên ghi theo từng DO/điểm giao trên từng xe/chuyến để tránh nhập nhằng trách nhiệm.',
        'Backhaul phải gắn DO chiều về; empty return dùng khi xe quay đầu rỗng.',
        'ETA lượt về tính từ chặng cuối dựa trên quãng đường, vận tốc và thời gian dừng.'
      ]
    };
  }

  function firstById(rows, id, keys = ['id']) {
    return rows.find(row => keys.some(key => String(row[key] || '') === String(id || ''))) || null;
  }

  function podsForOrder(state, deliveryOrderId) {
    return list(state, 'pods')
      .filter(item => String(item.do_id || item.delivery_order_id || '') === String(deliveryOrderId || ''))
      .sort((a, b) => numberValue(a.stop_no || 0) - numberValue(b.stop_no || 0)
        || String(a.delivery_time || '').localeCompare(String(b.delivery_time || ''))
        || String(a.id || '').localeCompare(String(b.id || '')));
  }

  function dateTimeLabel(value) {
    const date = parseTime(value);
    if (!date) return 'Chưa có ETA';
    const pad = number => String(number).padStart(2, '0');
    return `${pad(date.getDate())}/${pad(date.getMonth() + 1)}/${date.getFullYear()} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
  }

  function financeForOrder(state, order) {
    const orderId = String(order && order.id || '');
    const freightOrderIds = list(state, 'freight_order_legacy_links')
      .filter(link => String(link.delivery_order_id || link.do_id || '') === orderId)
      .map(link => String(link.freight_order_id || ''));
    const tripIds = list(state, 'trip_delivery_orders')
      .filter(link => String(link.delivery_order_id || link.do_id || '') === orderId)
      .map(link => String(link.trip_id || ''));
    const targetIds = new Set([
      orderId,
      String(order && (order.freight_order_id || order.fo_id) || ''),
      ...freightOrderIds,
      ...tripIds
    ].filter(Boolean));
    const costs = list(state, 'freight_actual_costs').filter(item =>
      targetIds.has(String(item.freight_order_id || item.trip_id || item.do_id || item.delivery_order_id || ''))
    );
    const costIds = new Set(costs.map(item => String(item.id || '')).filter(Boolean));
    const apInvoices = list(state, 'ap_invoices').filter(item =>
      costIds.has(String(item.cost_id || ''))
      || targetIds.has(String(item.do_id || item.delivery_order_id || item.freight_order_id || ''))
    );
    const apIds = new Set(apInvoices.map(item => String(item.id || '')).filter(Boolean));
    const settlements = list(state, 'settlements').filter(item => apIds.has(String(item.ap_invoice_id || '')));
    return { costs, apInvoices, settlements, all: [...costs, ...apInvoices, ...settlements] };
  }

  function buildOrderTimeline(state, deliveryOrderId) {
    const deliveryOrders = list(state, 'delivery_orders');
    const order = deliveryOrderId
      ? firstById(deliveryOrders, deliveryOrderId)
      : deliveryOrders[0] || {};
    const salesOrder = firstById(list(state, 'sales_orders'), order.so_id || order.sales_order_id);
    const quotation = firstById(list(state, 'quotations'), (salesOrder && (salesOrder.quotation_id || salesOrder.quote_id)) || order.quotation_id);
    const podRecords = podsForOrder(state, order.id);
    const pod = podRecords[0] || null;
    const status = normalized(order.status || order.canonical_status);
    const orderFinance = financeForOrder(state, order);

    const steps = [
      { key: 'quotation', label: 'Báo giá', done: quotation || order.quotation_id, view: 'crm-sales', action_label: 'Mở Báo giá' },
      { key: 'sales_order', label: 'SO', done: salesOrder || order.so_id, view: 'crm-sales', action_label: 'Mở SO' },
      { key: 'delivery_order', label: 'DO', done: order.id, view: 'ops-planning', action_label: 'Mở DO' },
      { key: 'dispatch', label: 'Điều phối', done: Boolean(order.vehicle_id && order.driver_id), view: 'dispatch', action_label: 'Mở Dispatch' },
      { key: 'pickup', label: 'Pickup', done: ['picked', 'packed', 'in_transit', 'arrived', 'delivered', 'completed'].includes(status), view: 'tracking', action_label: 'Mở GPS/POD' },
      { key: 'in_transit', label: 'Đang vận chuyển', done: ['in_transit', 'arrived', 'delivered', 'completed'].includes(status), view: 'tracking', action_label: 'Mở GPS/POD' },
      { key: 'arrival', label: 'Arrival / Unloading', done: ['arrived', 'delivered', 'completed'].includes(status), view: 'tracking', action_label: 'Mở GPS/POD' },
      { key: 'pod', label: 'POD', done: Boolean(pod), view: 'tracking', action_label: 'Mở GPS/POD' },
      { key: 'settlement', label: 'AP / Đối soát', done: orderFinance.settlements.length > 0, view: 'accounting', action_label: 'Mở Tài chính' }
    ];
    return steps.map(step => {
      const hardMissing = ['quotation', 'sales_order', 'delivery_order'].includes(step.key) && !step.done;
      const detail = buildOrderTimelineDetail(state, order.id, step.key);
      return {
        key: step.key,
        label: step.label,
        status: step.done ? 'done' : hardMissing ? 'blocked' : 'pending',
        health: step.done ? 'ok' : hardMissing ? 'critical' : 'warning',
        message: detail.message,
        action_label: step.action_label,
        navigation: detail.navigation
      };
    });
  }

  function buildOrderTimelineDetail(state, deliveryOrderId, stepKey) {
    const deliveryOrders = list(state, 'delivery_orders');
    const order = deliveryOrderId
      ? firstById(deliveryOrders, deliveryOrderId)
      : deliveryOrders[0] || {};
    const salesOrder = firstById(list(state, 'sales_orders'), order.so_id || order.sales_order_id);
    const quotation = firstById(list(state, 'quotations'), (salesOrder && (salesOrder.quotation_id || salesOrder.quote_id)) || order.quotation_id);
    const route = firstById(list(state, 'routes'), order.route_id || order.route, ['id', 'name']);
    const podRecords = podsForOrder(state, order.id);
    const pod = podRecords[0] || null;
    const events = list(state, 'transport_events')
      .filter(event => {
        const matchesDo = String(event.delivery_order_id || event.do_id || '') === String(order.id || '');
        const matchesFo = order.freight_order_id && String(event.freight_order_id || '') === String(order.freight_order_id);
        return matchesDo || matchesFo || (!event.delivery_order_id && !order.freight_order_id && String(event.do_id || '') === String(order.id || ''));
      })
      .sort((a, b) => String(a.event_time || a.recorded_at || '').localeCompare(String(b.event_time || b.recorded_at || '')));
    const orderFinance = financeForOrder(state, order);
    const finance = orderFinance.all;
    const status = normalized(order.status || order.canonical_status);
    const definitions = {
      quotation: { title: 'Báo giá', view: 'crm-sales', scrollTo: 'oracle-qt-list', primary: quotation, messageDone: 'Đã có báo giá liên kết với đơn.', messageMissing: 'Chưa có báo giá. Vào Nghiệp vụ → Báo giá để tạo trước.' },
      sales_order: { title: 'Sales Order / Đơn hàng', view: 'crm-sales', scrollTo: 'oracle-so-list', primary: salesOrder, messageDone: 'Đã có SO liên kết từ báo giá.', messageMissing: 'Chưa có SO. Vào Nghiệp vụ → SO để chốt đơn.' },
      delivery_order: { title: 'Delivery Order / Lệnh giao hàng', view: 'ops-planning', scrollTo: 'fiori-do-list', primary: order.id ? order : null, messageDone: 'Đã có DO để lập kế hoạch giao hàng.', messageMissing: 'Chưa có DO. Vào Nghiệp vụ → DO để tạo lệnh giao hàng.' },
      dispatch: { title: 'Dispatch / Điều phối', view: 'dispatch', primary: order.vehicle_id && order.driver_id ? order : null, messageDone: 'Đã phân đủ xe và tài xế cho DO.', messageMissing: 'Chưa phân đủ xe và tài xế. Vào Dispatch để điều phối.' },
      pickup: { title: 'Pickup / Lấy hàng', view: 'tracking', primary: events.find(e => ['pickup', 'check_in', 'departure'].includes(normalized(e.event_type))) || null, messageDone: 'Đã có sự kiện vận hành ở bước lấy hàng.', messageMissing: 'Chưa có sự kiện pickup. Vào GPS/POD để ghi nhận.' },
      in_transit: { title: 'Đang vận chuyển', view: 'tracking', primary: events.find(e => ['departure', 'route_deviation', 'delay'].includes(normalized(e.event_type))) || (['in_transit', 'arrived', 'delivered', 'completed'].includes(status) ? order : null), messageDone: 'Đã có dữ liệu xe đang chạy hoặc event hành trình.', messageMissing: 'Chưa có dữ liệu hành trình. Vào GPS/POD để cập nhật.' },
      arrival: { title: 'Arrival / Unloading', view: 'tracking', primary: events.find(e => ['arrival', 'unloading'].includes(normalized(e.event_type))) || null, messageDone: 'Đã có event đến nơi/dỡ hàng.', messageMissing: 'Chưa có event đến nơi. Vào GPS/POD để cập nhật.' },
      pod: { title: 'POD / Bằng chứng giao hàng', view: 'tracking', primary: pod || null, messageDone: 'Đã có chứng từ POD.', messageMissing: 'Chưa có POD. Vào GPS/POD để tải biên bản ký nhận.' },
      settlement: { title: 'AP / Đối soát', view: 'accounting', primary: orderFinance.settlements[0] || null, messageDone: 'Đã có settlement đúng chuyến.', messageMissing: 'Chưa hoàn tất settlement của chuyến. Vào Tài chính để kiểm tra Actual Cost/AP/đối soát.' }
    };
    const def = definitions[stepKey] || definitions.delivery_order;
    const done = Boolean(def.primary);
    const entityIds = {
      quotation: quotation && quotation.id,
      sales_order: salesOrder && salesOrder.id,
      delivery_order: order && order.id,
      dispatch: order && order.id,
      pickup: order && order.id,
      in_transit: order && order.id,
      arrival: order && order.id,
      pod: order && order.id,
      settlement: order && order.id
    };
    const navigation = {
      view: def.view,
      ...(def.scrollTo ? { scroll_to: def.scrollTo } : {}),
      ...(entityIds[stepKey] ? { entity_id: entityIds[stepKey] } : {})
    };
    const actionLabels = {
      quotation: 'Mở Báo giá',
      sales_order: 'Mở SO',
      delivery_order: 'Mở DO',
      dispatch: 'Mở Dispatch',
      pickup: 'Mở GPS/POD',
      in_transit: 'Mở GPS/POD',
      arrival: 'Mở GPS/POD',
      pod: 'Mở GPS/POD',
      settlement: 'Mở Tài chính'
    };
    const baseActions = [
      {
        code: 'OPEN_TIMELINE_CONTEXT',
        label: actionLabels[stepKey] || 'Mở màn liên quan',
        description: done ? 'Mở chứng từ hoặc màn xử lý của bước đang chọn.' : 'Mở đúng màn để bổ sung dữ liệu còn thiếu cho bước này.',
        severity: done ? 'info' : 'warning',
        navigation
      },
      {
        code: 'OPEN_DELIVERY_ORDER',
        label: 'Mở DO',
        description: 'Kiểm tra thông tin đơn giao hàng, tuyến, khung giờ lấy/giao và trạng thái khóa.',
        severity: order.id ? 'info' : 'warning',
        navigation: { view: 'ops-planning' }
      },
      {
        code: 'OPEN_DISPATCH',
        label: 'Mở Dispatch',
        description: 'Kiểm tra phân xe, tài xế, calendar/Gantt và xung đột tài nguyên.',
        severity: (order.vehicle_id && order.driver_id) ? 'info' : 'warning',
        navigation: { view: 'dispatch' }
      },
      {
        code: 'OPEN_GPS_POD',
        label: 'Mở GPS/POD',
        description: 'Xem chuỗi event, vị trí mới nhất, Arrival và chứng từ POD.',
        severity: events.length && pod ? 'info' : 'warning',
        navigation: { view: 'tracking' }
      },
      {
        code: 'OPEN_FINANCE_COCKPIT',
        label: 'Mở Finance',
        description: 'Theo dõi Actual Cost, AP Invoice, thanh toán và đối soát.',
        severity: finance.length ? 'info' : 'warning',
        navigation: { view: 'accounting' }
      }
    ];
    const deepActions = baseActions.filter((action, index, rows) =>
      rows.findIndex(item => item.code === action.code) === index
    );
    const checklist = [
      { label: 'Báo giá', status: quotation ? 'done' : 'missing' },
      { label: 'SO', status: salesOrder ? 'done' : 'missing' },
      { label: 'DO', status: order.id ? 'done' : 'missing' },
      { label: 'Xe/tài xế', status: (order.vehicle_id && order.driver_id) ? 'done' : 'missing' },
      { label: 'Event vận hành', status: events.length ? 'done' : 'missing' },
      { label: 'POD', status: podRecords.length ? 'done' : 'missing' },
      { label: 'Tài chính/AP', status: finance.length ? 'done' : 'missing' }
    ];
    return {
      key: stepKey,
      title: def.title,
      status: done ? 'done' : 'pending',
      health: done ? 'ok' : 'warning',
      primary: def.primary || {},
      related: { quotation, sales_order: salesOrder, delivery_order: order, route, pod, pod_records: podRecords, events, finance },
      navigation,
      message: done ? def.messageDone : def.messageMissing,
      action_label: actionLabels[stepKey] || 'Mở màn liên quan',
      deep_actions: deepActions,
      checklist
    };
  }

  function buildShipment360Detail(state, deliveryOrderId, now = new Date()) {
    const deliveryOrders = list(state, 'delivery_orders');
    const order = deliveryOrderId
      ? firstById(deliveryOrders, deliveryOrderId)
      : deliveryOrders[0] || {};
    const salesOrder = firstById(list(state, 'sales_orders'), order.so_id || order.sales_order_id);
    const quotation = firstById(list(state, 'quotations'), (salesOrder && (salesOrder.quotation_id || salesOrder.quote_id)) || order.quotation_id);
    const route = firstById(list(state, 'routes'), order.route_id || order.route, ['id', 'name']);
    const vehicle = firstById(list(state, 'vehicles'), order.vehicle_id || order.vehicle, ['id', 'vehicle_id', 'plate_no']);
    const driver = firstById(list(state, 'drivers'), order.driver_id || order.driver, ['id', 'driver_id', 'name']);
    const timeline = buildOrderTimeline(state, order.id);
    const gps = buildGpsEventTimeline(state, order.id);
    const latestEvent = gps.events[gps.events.length - 1] || {};
    const timelineDetail = buildOrderTimelineDetail(state, order.id, 'settlement');
    const pod = gps.pod;
    const alerts = [];

    if (isWaitingDispatch(order)) {
      alerts.push({
        code: 'DISPATCH_REQUIRED',
        severity: 'warning',
        message: `${order.id || 'DO'} chưa điều phối đủ xe/tài xế.`
      });
    }
    if (isTripLate(order, now)) {
      alerts.push({
        code: 'SLA_LATE',
        severity: 'critical',
        message: `${order.id || 'DO'} đang trễ SLA/ETA. Cần kiểm tra GPS và cập nhật ETA.`
      });
    }
    gps.alerts.forEach(alert => alerts.push(alert));

    const financeItems = (timelineDetail.related.finance || []).map(item => ({
      id: item.id || item.ap_invoice_id || item.freight_order_id || item.do_id || '',
      type: item.vendor_invoice_no ? 'AP Invoice' : item.ap_invoice_id ? 'Settlement' : 'Actual Cost',
      status_label: statusLabel(item.status || item.canonical_status || 'open'),
      amount: numberValue(item.total_amount ?? item.remaining_amount ?? item.approved_amount ?? item.amount),
      currency_code: item.currency_code || 'VND'
    }));

    const actions = [
      {
        code: 'OPEN_DISPATCH',
        label: 'Mở Dispatch',
        description: 'Điều phối hoặc kiểm tra xe/tài xế, calendar và xung đột tài nguyên.',
        navigation: { view: 'dispatch' },
        severity: order.vehicle_id && order.driver_id ? 'info' : 'warning'
      },
      {
        code: 'OPEN_GPS_POD',
        label: pod ? 'Xem POD' : 'Bổ sung POD',
        description: pod ? 'Xem chứng từ POD/ký nhận đã lưu.' : 'Bổ sung POD trước khi đối soát và xuất hóa đơn.',
        navigation: { view: 'tracking' },
        severity: pod ? 'info' : 'warning'
      },
      {
        code: 'OPEN_FINANCE',
        label: financeItems.length ? 'Mở tài chính' : 'Tạo Actual Cost',
        description: 'Kiểm tra chi phí thực tế, AP Invoice, payment và settlement.',
        navigation: { view: 'accounting' },
        severity: financeItems.length ? 'info' : 'warning'
      },
      {
        code: 'OPEN_TIMELINE',
        label: 'Xem timeline A-Z',
        description: 'Mở timeline nghiệp vụ từ báo giá đến settlement.',
        navigation: { view: 'overview' },
        severity: 'info'
      }
    ];

    return {
      id: order.id || deliveryOrderId || '',
      summary: {
        customer_id: order.customer_id || (salesOrder && salesOrder.customer_id) || (quotation && quotation.customer_id) || 'Chưa gắn khách hàng',
        status_label: statusLabel(order.status || order.canonical_status),
        route_label: route ? `${route.id || route.name || 'Tuyến'} • ${route.name || route.route_name || ''}`.trim() : (order.route_id || 'Chưa chọn tuyến'),
        vehicle_label: order.vehicle_id || (vehicle && (vehicle.plate_no || vehicle.id)) || 'Chưa phân xe',
        driver_label: order.driver_id || (driver && (driver.name || driver.id)) || 'Chưa phân tài xế',
        eta_label: dateTimeLabel(order.eta || order.planned_arrival_at || order.planned_delivery_at || order.delivery_date),
        return_eta_label: dateTimeLabel(order.planned_return_at || order.return_eta || order.vehicle_return_eta),
        distance_label: (order.distance_km || order.total_distance || order.planned_distance_km || (route && route.total_distance))
          ? `${numberValue(order.distance_km || order.total_distance || order.planned_distance_km || route.total_distance).toFixed(1)} km`
          : 'Chưa có dữ liệu'
      },
      timeline,
      latest_event: latestEvent,
      events: gps.events,
      pod: {
        status: pod ? 'done' : 'missing',
        label: pod ? `Đã có ${gps.pod_records.length} POD` : 'Thiếu POD',
        data: pod || null,
        records: gps.pod_records
      },
      finance: {
        items: financeItems,
        status: financeItems.length ? 'available' : 'missing'
      },
      alerts,
      actions
    };
  }

  function buildShipmentSettlementReadiness(state, deliveryOrderId, now = new Date()) {
    const shipment = buildShipment360Detail(state, deliveryOrderId, now);
    const order = firstById(list(state, 'delivery_orders'), shipment.id);
    const status = normalized(order && (order.status || order.canonical_status));
    const orderFinance = financeForOrder(state, order || {});
    const internalCarrierIds = new Set(list(state, 'carriers')
      .filter(carrier => carrier.is_internal === true || normalized(carrier.type || carrier.carrier_type) === 'internal')
      .map(carrier => String(carrier.id || carrier.carrier_id || ''))
      .filter(Boolean));
    const requiresAp = orderFinance.costs.some(cost => {
      const carrierId = String(cost.carrier_id || cost.vendor_id || '');
      return carrierId && !internalCarrierIds.has(carrierId);
    });
    const financeItems = shipment.finance.items || [];
    const hasActualCost = financeItems.some(item => item.type === 'Actual Cost');
    const hasAp = financeItems.some(item => item.type === 'AP Invoice');
    const hasSettlement = financeItems.some(item => item.type === 'Settlement');
    const plannedDistance = numberValue(order && (order.distance_km || order.total_distance || order.planned_distance_km));
    const actualDistance = numberValue(order && (order.actual_distance_km || order.gps_distance_km || order.distance_actual_km));
    const varianceKm = actualDistance && plannedDistance ? actualDistance - plannedDistance : 0;
    const variancePercent = actualDistance && plannedDistance ? Math.round((varianceKm / plannedDistance) * 1000) / 10 : 0;
    const checks = [
      {
        key: 'delivery_status',
        label: 'Hoàn tất giao hàng',
        status: ['delivered', 'completed', 'settled'].includes(status) ? 'done' : 'missing',
        message: ['delivered', 'completed', 'settled'].includes(status) ? 'Đơn đã qua bước giao hàng.' : 'Cần cập nhật Arrival/Delivered trước khi chốt.'
      },
      {
        key: 'pod',
        label: 'POD đầy đủ',
        status: shipment.pod.status === 'done' ? 'done' : 'missing',
        message: shipment.pod.status === 'done' ? shipment.pod.label : 'Thiếu POD/chữ ký/ảnh ký nhận.'
      },
      {
        key: 'actual_cost',
        label: 'Actual Cost',
        status: hasActualCost ? 'done' : 'missing',
        message: hasActualCost ? 'Đã có chi phí thực tế.' : 'Cần tạo Actual Cost trước AP/settlement.'
      },
      {
        key: 'ap_invoice',
        label: 'AP Invoice',
        status: !requiresAp ? 'not_applicable' : hasAp ? 'done' : 'missing',
        message: !requiresAp
          ? 'Chuyến nội bộ không phải lập AP nhà cung cấp.'
          : hasAp ? 'Đã có AP Invoice.' : 'Chưa có AP Invoice nhà cung cấp/chi phí.'
      },
      {
        key: 'distance_reconcile',
        label: 'Đối soát km',
        status: actualDistance && plannedDistance && Math.abs(variancePercent) <= 10 ? 'done' : 'warning',
        message: actualDistance && plannedDistance
          ? `Lệch ${varianceKm.toFixed(1)} km (${variancePercent}%).`
          : 'Chưa đủ planned/actual km để đối soát sâu.'
      }
    ];
    const blockers = checks.filter(check => check.status === 'missing');
    const warnings = checks.filter(check => check.status === 'warning');
    const statusLabelValue = blockers.length ? 'blocked' : warnings.length ? 'warning' : 'ready';
    return {
      id: shipment.id,
      status: statusLabelValue,
      status_label: statusLabelValue === 'ready'
        ? 'Sẵn sàng chốt chuyến'
        : statusLabelValue === 'warning'
          ? 'Có cảnh báo cần xem trước khi chốt'
          : 'Chưa đủ điều kiện chốt chuyến',
      summary: [
        { label: 'POD', value: shipment.pod.label },
        { label: 'Actual Cost/AP', value: `${hasActualCost ? 'Có Cost' : 'Thiếu Cost'} • ${!requiresAp ? 'AP không áp dụng' : hasAp ? 'Có AP' : 'Thiếu AP'}` },
        { label: 'Settlement', value: hasSettlement ? 'Đã có settlement' : 'Chưa settlement' },
        { label: 'Lệch km', value: actualDistance && plannedDistance ? `${varianceKm.toFixed(1)} km (${variancePercent}%)` : 'Chưa đủ dữ liệu' }
      ],
      checks,
      actions: [
        ...(shipment.pod.status === 'done' ? [] : [{ code: 'OPEN_GPS_POD', label: 'Bổ sung POD', navigation: { view: 'tracking' } }]),
        ...(!hasActualCost || (requiresAp && !hasAp) ? [{ code: 'OPEN_FINANCE', label: 'Mở Finance Cockpit', navigation: { view: 'accounting' } }] : []),
        { code: 'OPEN_TIMELINE', label: 'Xem timeline A-Z', navigation: { view: 'overview' } }
      ]
    };
  }

  function buildFinanceWorklist(state) {
    return {
      actual_cost_pending: list(state, 'freight_actual_costs').filter(row => ['draft', 'submitted'].includes(normalized(row.status))).length,
      ap_waiting_post: list(state, 'ap_invoices').filter(row => ['draft', 'submitted', 'approved'].includes(normalized(row.status))).length,
      settlement_open: list(state, 'settlements').filter(row => ['open', 'partially_paid', 'approved'].includes(normalized(row.status))).length
    };
  }

  function buildFinanceCockpitSummary(state) {
    const costs = list(state, 'freight_actual_costs');
    const apInvoices = list(state, 'ap_invoices');
    const settlements = list(state, 'settlements');
    const costsPending = costs.filter(row => ['draft', 'submitted'].includes(normalized(row.status)));
    const apWaitingPost = apInvoices.filter(row => ['draft', 'submitted', 'approved'].includes(normalized(row.status)));
    const settlementOpen = settlements.filter(row => ['open', 'partially_paid', 'approved'].includes(normalized(row.status)));
    const payableStatuses = new Set(['draft', 'submitted', 'approved', 'posted', 'partially_paid', 'open']);
    const totalPayable = apInvoices
      .filter(row => payableStatuses.has(normalized(row.status)))
      .reduce((sum, row) => sum + numberValue(row.total_amount ?? row.total ?? row.amount), 0);

    const rowCard = (row, subtitle) => ({
      id: row.id,
      title: row.id || row.code || 'Chưa có mã',
      subtitle,
      amount: numberValue(row.total_amount ?? row.remaining_amount ?? row.total ?? row.amount),
      currency: row.currency_code || 'VND',
      status: normalized(row.status),
      status_label: statusLabel(row.status)
    });

    return {
      kpis: {
        actual_cost_pending: { label: 'Actual Cost chờ duyệt', count: costsPending.length, target: 'finance-cockpit-costs' },
        ap_waiting_post: { label: 'AP chờ hạch toán', count: apWaitingPost.length, target: 'finance-cockpit-ap' },
        settlement_open: { label: 'Settlement còn mở', count: settlementOpen.length, target: 'finance-cockpit-settlements' },
        total_payable: { label: 'Tổng phải trả đang mở', amount: totalPayable, currency: 'VND', target: 'finance-cockpit-ap' }
      },
      costs: costsPending.slice(0, 8).map(row => rowCard(row, `FO: ${row.freight_order_id || row.fo_id || 'chưa gắn FO'} • Carrier: ${row.carrier_id || 'chưa chọn'}`)),
      ap_invoices: apWaitingPost.slice(0, 8).map(row => rowCard(row, `Carrier: ${row.carrier_id || row.vendor_id || 'chưa chọn'}`)),
      settlements: settlementOpen.slice(0, 8).map(row => rowCard(row, `AP: ${row.ap_invoice_id || row.invoice_id || 'chưa gắn AP'}`))
    };
  }

  function buildFinanceActionWorkbench(state, filters = {}) {
    const costs = list(state, 'freight_actual_costs');
    const apInvoices = list(state, 'ap_invoices');
    const settlements = list(state, 'settlements');
    const money = row => numberValue(row.total_amount ?? row.remaining_amount ?? row.total ?? row.amount);
    const currency = row => row.currency_code || 'VND';
    const nav = { view: 'accounting' };
    const task = (row, kind, title, subtitle, actionLabel, severity = 'info') => ({
      id: row.id || row.code || `${kind}-${title}`,
      kind,
      title,
      subtitle,
      status: normalized(row.status),
      status_label: statusLabel(row.status),
      amount: money(row),
      currency: currency(row),
      action_label: actionLabel,
      severity,
      navigation: nav
    });

    const costsNeedApproval = costs.filter(row => ['draft', 'submitted'].includes(normalized(row.status)));
    const costsReadyForAp = costs.filter(row => ['approved'].includes(normalized(row.status)));
    const apWaitingPost = apInvoices.filter(row => ['draft', 'submitted', 'approved'].includes(normalized(row.status)));
    const settlementOpen = settlements.filter(row => ['open', 'approved', 'partially_paid'].includes(normalized(row.status)));

    const worklist = [
      ...costsNeedApproval.map(row => task(
        row,
        'actual_cost',
        row.id || 'Actual Cost chưa có mã',
        `FO/DO: ${row.freight_order_id || row.fo_id || row.do_id || 'chưa gắn'} • Carrier: ${row.carrier_id || 'chưa chọn'}`,
        normalized(row.status) === 'draft' ? 'Hoàn thiện Actual Cost' : 'Duyệt Actual Cost',
        normalized(row.status) === 'submitted' ? 'warning' : 'info'
      )),
      ...costsReadyForAp.map(row => task(
        row,
        'actual_cost',
        row.id || 'Actual Cost đã duyệt',
        `FO/DO: ${row.freight_order_id || row.fo_id || row.do_id || 'chưa gắn'} • Sẵn sàng tạo công nợ phải trả`,
        'Tạo AP Invoice',
        'success'
      )),
      ...apWaitingPost.map(row => task(
        row,
        'ap_invoice',
        row.id || 'AP Invoice chưa có mã',
        `Carrier/Vendor: ${row.carrier_id || row.vendor_id || 'chưa chọn'} • Kiểm tra chứng từ trước khi post GL`,
        'Hạch toán AP',
        'warning'
      )),
      ...settlementOpen.map(row => task(
        row,
        'settlement',
        row.id || 'Settlement chưa có mã',
        `AP: ${row.ap_invoice_id || row.invoice_id || 'chưa gắn AP'} • Còn lại ${money(row).toLocaleString('vi-VN')} ${currency(row)}`,
        'Thanh toán / đối soát',
        normalized(row.status) === 'partially_paid' ? 'warning' : 'info'
      ))
    ];

    const blockers = worklist.filter(item => item.severity === 'warning').length;
    const guidance = [];
    if (costsNeedApproval.length) guidance.push('Actual Cost đã có dữ liệu, cần kiểm tra chứng từ và duyệt trước khi tạo AP.');
    if (costsReadyForAp.length) guidance.push('Có Actual Cost đã duyệt, bước tiếp theo là tạo AP Invoice để ghi nhận công nợ nhà vận chuyển.');
    if (apWaitingPost.length) guidance.push('AP Invoice chờ hạch toán cần kiểm tra kỳ kế toán, mapping tài khoản và thuế trước khi post GL.');
    if (settlementOpen.length) guidance.push('Settlement còn mở cần theo dõi thanh toán, đối soát và phần còn phải trả.');
    if (!guidance.length) guidance.push('Không có việc tài chính tồn đọng trong dữ liệu hiện tại.');

    const filterKind = normalized(filters.kind || '');
    const filterStatus = normalized(filters.status || '');
    const filterSearch = String(filters.search || '').trim().toLowerCase();
    const filteredWorklist = worklist.filter(item => {
      if (filterKind && item.kind !== filterKind) return false;
      if (filterStatus && item.status !== filterStatus) return false;
      if (filterSearch) {
        const haystack = `${item.id} ${item.title} ${item.subtitle} ${item.status_label}`.toLowerCase();
        if (!haystack.includes(filterSearch)) return false;
      }
      return true;
    });

    return {
      kpis: {
        costs_need_approval: { label: 'Cost cần duyệt', count: costsNeedApproval.length, target: 'finance-action-worklist' },
        costs_ready_for_ap: { label: 'Cost sẵn sàng tạo AP', count: costsReadyForAp.length, target: 'finance-action-worklist' },
        ap_waiting_post: { label: 'AP chờ hạch toán', count: apWaitingPost.length, target: 'finance-action-worklist' },
        settlement_open: { label: 'Settlement còn mở', count: settlementOpen.length, target: 'finance-action-worklist' },
        finance_blockers: { label: 'Cảnh báo cần xử lý', count: blockers, target: 'finance-action-guidance' }
      },
      worklist: filteredWorklist.map(item => ({ ...item, detail_key: `${item.kind}:${item.id}` })),
      all_worklist: worklist.map(item => ({ ...item, detail_key: `${item.kind}:${item.id}` })),
      filters_applied: {
        kind: filterKind,
        status: filterStatus,
        search: filterSearch,
        count: [filterKind, filterStatus, filterSearch].filter(Boolean).length
      },
      guidance
    };
  }

  function buildFinanceProcessCockpit(state) {
    const costs = list(state, 'freight_actual_costs');
    const apInvoices = list(state, 'ap_invoices');
    const settlements = list(state, 'settlements');
    const payments = list(state, 'settlement_payments');
    const money = (amount, currency = 'VND') => `${numberValue(amount).toLocaleString('vi-VN')} ${currency}`;
    const card = (row, kind, subtitle, actionLabel) => ({
      id: row.id || row.code || `${kind}-N/A`,
      kind,
      title: row.id || row.code || 'Chưa có mã',
      subtitle,
      status: normalized(row.status),
      status_label: statusLabel(row.status),
      amount_label: money(row.total_amount ?? row.remaining_amount ?? row.amount, row.currency_code || 'VND'),
      detail_key: `${kind}:${row.id || row.code || ''}`,
      action_label: actionLabel
    });
    const actualCostCards = costs
      .filter(row => !['reversed'].includes(normalized(row.status)))
      .map(row => card(
        row,
        'actual_cost',
        `FO/DO: ${row.freight_order_id || row.fo_id || row.do_id || 'chưa gắn'} • Carrier: ${row.carrier_id || 'chưa chọn'}`,
        normalized(row.status) === 'approved' ? 'Tạo AP' : 'Duyệt cost'
      ));
    const apCards = apInvoices.map(row => card(
      row,
      'ap_invoice',
      `Carrier/Vendor: ${row.carrier_id || row.vendor_id || 'chưa chọn'} • Kiểm tra trước khi post GL`,
      normalized(row.status) === 'posted' ? 'Tạo settlement' : 'Post GL'
    ));
    const settlementCards = settlements.map(row => card(
      row,
      'settlement',
      `AP: ${row.ap_invoice_id || row.invoice_id || 'chưa gắn AP'} • Còn lại ${money(row.remaining_amount ?? row.total_amount ?? row.amount, row.currency_code || 'VND')}`,
      'Thanh toán'
    ));
    const paymentCards = payments.map(row => card(
      row,
      'payment',
      `Settlement: ${row.settlement_id || 'chưa gắn'} • Tham chiếu: ${row.reference_no || row.payment_ref || 'chưa có'}`,
      'Xem chứng từ'
    ));
    const reversalCards = [
      ...costs.filter(row => normalized(row.status) === 'reversed' || row.reversal_of_cost_id || row.reversed_by_cost_id)
        .map(row => card(row, 'actual_cost', `Reversal: ${row.reversal_of_cost_id || row.reversed_by_cost_id || 'đã đảo'}`, 'Xem reversal')),
      ...apInvoices.filter(row => normalized(row.status) === 'reversed' || row.reversal_of_invoice_id || row.reversed_by_invoice_id)
        .map(row => card(row, 'ap_invoice', `Reversal: ${row.reversal_of_invoice_id || row.reversed_by_invoice_id || 'đã đảo'}`, 'Xem reversal'))
    ];
    const lanes = [
      { key: 'actual_cost', label: 'Actual Cost', description: 'Chi phí thực tế sau chuyến', count: actualCostCards.length, cards: actualCostCards.slice(0, 6) },
      { key: 'ap_invoice', label: 'AP Invoice', description: 'Công nợ phải trả carrier/vendor', count: apCards.length, cards: apCards.slice(0, 6) },
      { key: 'settlement', label: 'Settlement', description: 'Đối soát và trạng thái phải trả', count: settlementCards.length, cards: settlementCards.slice(0, 6) },
      { key: 'payment', label: 'Payment', description: 'Thanh toán đã ghi nhận', count: paymentCards.length, cards: paymentCards.slice(0, 6) },
      { key: 'reversal', label: 'Reversal', description: 'Đảo bút toán/hoàn tác có kiểm soát', count: reversalCards.length, cards: reversalCards.slice(0, 6) }
    ];
    const blockers = [];
    if (!list(state, 'account_mappings').some(isActiveRow)) {
      blockers.push({
        code: 'FINANCE_ACCOUNT_MAPPING_MISSING',
        severity: 'warning',
        message: 'Thiếu mapping tài khoản. Vào Master Data → Account Mapping để cấu hình trước khi post GL.',
        navigation: { view: 'master-data', target: 'md-tab-account-mappings' }
      });
    }
    if (!list(state, 'accounting_periods').some(row => ['open', 'active'].includes(normalized(row.status)))) {
      blockers.push({
        code: 'FINANCE_ACCOUNTING_PERIOD_MISSING',
        severity: 'warning',
        message: 'Thiếu kỳ kế toán mở. Vào Master Data → Kỳ kế toán để cấu hình trước khi settlement/payment.',
        navigation: { view: 'master-data', target: 'md-tab-accounting-periods' }
      });
    }
    if (!list(state, 'tax_codes').some(isActiveRow)) {
      blockers.push({
        code: 'FINANCE_TAX_CODE_MISSING',
        severity: 'warning',
        message: 'Thiếu mã thuế. Vào Master Data → Mã thuế để cấu hình trước khi tạo AP.',
        navigation: { view: 'master-data', target: 'md-tab-tax-codes' }
      });
    }
    const flow = lanes.map((lane, index) => ({
      key: lane.key,
      label: lane.label,
      order: index + 1,
      count: lane.count,
      status: lane.count > 0 ? 'active' : 'empty'
    }));
    return { lanes, blockers, flow };
  }

  function buildFinanceCloseoutWorkbench(state) {
    const costs = list(state, 'freight_actual_costs');
    const apInvoices = list(state, 'ap_invoices');
    const settlements = list(state, 'settlements');
    const apByCost = new Map(apInvoices.map(ap => [String(ap.cost_id || ap.actual_cost_id || ''), ap]));
    const settlementByAp = new Map(settlements.map(settlement => [String(settlement.ap_invoice_id || ''), settlement]));
    const representedApIds = new Set();
    const items = costs.map(cost => {
      const costStatus = normalized(cost.status);
      const ap = apByCost.get(String(cost.id || ''));
      if (ap) representedApIds.add(String(ap.id || ''));
      const settlement = ap ? settlementByAp.get(String(ap.id || '')) : null;
      let readiness = 'blocked';
      let nextAction = { code: 'VIEW_COST', label: 'Mở Actual Cost', detail_key: `actual_cost:${cost.id || ''}` };
      if (['draft', 'submitted'].includes(costStatus)) {
        nextAction = { code: 'APPROVE_COST', label: 'Duyệt Actual Cost', detail_key: `actual_cost:${cost.id || ''}` };
      } else if (!ap) {
        nextAction = { code: 'CREATE_AP', label: 'Tạo AP Invoice', detail_key: `actual_cost:${cost.id || ''}` };
      } else if (!['posted', 'paid', 'partially_paid'].includes(normalized(ap.status))) {
        readiness = 'warning';
        nextAction = { code: 'POST_AP', label: 'Hạch toán AP', detail_key: `ap_invoice:${ap.id || ''}` };
      } else if (!settlement || !['paid', 'closed'].includes(normalized(settlement.status))) {
        readiness = 'warning';
        nextAction = { code: 'PAY_SETTLEMENT', label: 'Thanh toán / đối soát', detail_key: settlement ? `settlement:${settlement.id || ''}` : `ap_invoice:${ap.id || ''}` };
      } else {
        readiness = 'ready';
        nextAction = { code: 'CLOSEOUT_DONE', label: 'Đã đủ điều kiện chốt', detail_key: `settlement:${settlement.id || ''}` };
      }
      return {
        id: cost.id || '',
        trace_label: `${cost.freight_order_id || cost.do_id || 'FO/DO chưa gắn'} → ${cost.id || 'Cost'}${ap ? ` → ${ap.id}` : ''}${settlement ? ` → ${settlement.id}` : ''}`,
        status_label: `${statusLabel(cost.status)}${ap ? ` / AP: ${statusLabel(ap.status)}` : ' / Chưa có AP'}${settlement ? ` / Settlement: ${statusLabel(settlement.status)}` : ''}`,
        amount: numberValue(cost.total_amount ?? cost.approved_amount ?? cost.amount),
        currency_code: cost.currency_code || 'VND',
        readiness,
        next_action: nextAction
      };
    });
    apInvoices
      .filter(ap => !representedApIds.has(String(ap.id || '')))
      .forEach(ap => {
        const settlement = settlementByAp.get(String(ap.id || ''));
        const apStatus = normalized(ap.status);
        let readiness = 'warning';
        let nextAction = { code: 'POST_AP', label: 'Hạch toán AP', detail_key: `ap_invoice:${ap.id || ''}` };
        if (['posted', 'paid', 'partially_paid'].includes(apStatus) && (!settlement || !['paid', 'closed'].includes(normalized(settlement.status)))) {
          nextAction = { code: 'PAY_SETTLEMENT', label: 'Thanh toán / đối soát', detail_key: settlement ? `settlement:${settlement.id || ''}` : `ap_invoice:${ap.id || ''}` };
        } else if (settlement && ['paid', 'closed'].includes(normalized(settlement.status))) {
          readiness = 'ready';
          nextAction = { code: 'CLOSEOUT_DONE', label: 'Đã đủ điều kiện chốt', detail_key: `settlement:${settlement.id || ''}` };
        }
        items.push({
          id: ap.id || '',
          trace_label: `${ap.cost_id || ap.freight_order_id || ap.do_id || 'Cost/FO chưa gắn'} → ${ap.id || 'AP'}${settlement ? ` → ${settlement.id}` : ''}`,
          status_label: `AP: ${statusLabel(ap.status)}${settlement ? ` / Settlement: ${statusLabel(settlement.status)}` : ' / Chưa settlement'}`,
          amount: numberValue(ap.total_amount ?? ap.remaining_amount ?? ap.amount),
          currency_code: ap.currency_code || 'VND',
          readiness,
          next_action: nextAction
        });
      });
    settlements.forEach(settlement => {
      if (items.some(item => item.next_action.detail_key === `settlement:${settlement.id || ''}`)) return;
      const settled = ['paid', 'closed'].includes(normalized(settlement.status));
      items.push({
        id: settlement.id || '',
        trace_label: `${settlement.ap_invoice_id || 'AP chưa gắn'} → ${settlement.id || 'Settlement'}`,
        status_label: `Settlement: ${statusLabel(settlement.status)}`,
        amount: numberValue(settlement.remaining_amount ?? settlement.total_amount ?? settlement.amount),
        currency_code: settlement.currency_code || 'VND',
        readiness: settled ? 'ready' : 'warning',
        next_action: settled
          ? { code: 'CLOSEOUT_DONE', label: 'Đã đủ điều kiện chốt', detail_key: `settlement:${settlement.id || ''}` }
          : { code: 'PAY_SETTLEMENT', label: 'Thanh toán / đối soát', detail_key: `settlement:${settlement.id || ''}` }
      });
    });
    return {
      kpis: {
        ready_or_done: { label: 'Đủ điều kiện / đang closeout', count: items.filter(item => item.readiness !== 'blocked').length },
        needs_ap: { label: 'Cần tạo AP', count: items.filter(item => item.next_action.code === 'CREATE_AP').length },
        needs_posting: { label: 'Cần hạch toán AP', count: items.filter(item => item.next_action.code === 'POST_AP').length },
        needs_payment: { label: 'Cần thanh toán/đối soát', count: items.filter(item => item.next_action.code === 'PAY_SETTLEMENT').length }
      },
      items,
      guidance: [
        'Actual Cost phải được duyệt trước khi tạo AP Invoice.',
        'AP Invoice phải hạch toán GL trước khi thanh toán/settlement.',
        'Nếu thiếu Master Data tài chính, vào Master Data → Thuế/Kỳ kế toán/Mapping tài khoản để cấu hình.'
      ]
    };
  }

  function buildFinanceRecordDetail(state, detailKey) {
    const [kind, id] = String(detailKey || '').split(':');
    const collections = {
      actual_cost: { rows: list(state, 'freight_actual_costs'), label: 'Actual Cost' },
      ap_invoice: { rows: list(state, 'ap_invoices'), label: 'AP Invoice' },
      settlement: { rows: list(state, 'settlements'), label: 'Settlement' }
    };
    const config = collections[kind] || collections.actual_cost;
    const row = config.rows.find(item => String(item.id || item.code) === String(id))
      || config.rows[0]
      || null;
    if (!row) {
      return {
        id: '',
        kind,
        kind_label: config.label,
        title: 'Chưa chọn hồ sơ tài chính',
        amount: 0,
        currency: 'VND',
        amount_label: '0 VND',
        status: '',
        status_label: 'Chưa có dữ liệu',
        fields: [],
        timeline: [
          { key: 'cost', label: 'Actual Cost', status: 'pending' },
          { key: 'ap', label: 'AP Invoice', status: 'pending' },
          { key: 'payment', label: 'Payment', status: 'pending' },
          { key: 'settlement', label: 'Settlement', status: 'pending' }
        ],
        actions: [{ label: 'Vào Master Data / Finance để tạo dữ liệu', target: 'accounting', severity: 'info' }]
      };
    }
    const status = normalized(row.status);
    const amount = numberValue(row.total_amount ?? row.remaining_amount ?? row.total ?? row.amount);
    const currency = row.currency_code || 'VND';
    const amountLabel = `${amount.toLocaleString('vi-VN')} ${currency}`;
    const timelineStatus = step => {
      if (kind === 'actual_cost') {
        if (step === 'cost') return ['submitted', 'approved', 'reversed'].includes(status) ? 'done' : 'current';
        if (step === 'ap') return status === 'approved' ? 'current' : 'pending';
        return 'pending';
      }
      if (kind === 'ap_invoice') {
        if (step === 'cost') return 'done';
        if (step === 'ap') return ['posted', 'paid', 'partially_paid'].includes(status) ? 'done' : 'current';
        if (step === 'payment') return status === 'posted' ? 'current' : 'pending';
        return 'pending';
      }
      if (step === 'cost' || step === 'ap') return 'done';
      if (step === 'payment') return ['paid', 'closed'].includes(status) ? 'done' : 'current';
      return ['paid', 'closed'].includes(status) ? 'done' : 'current';
    };
    const actions = [];
    if (kind === 'actual_cost') {
      if (['draft', 'submitted'].includes(status)) actions.push({ label: 'Duyệt Actual Cost', target: 'finance-cockpit-costs', severity: 'warning' });
      if (status === 'approved') actions.push({ label: 'Tạo AP Invoice', target: 'finance-cockpit-ap', severity: 'success' });
    } else if (kind === 'ap_invoice') {
      if (['draft', 'submitted', 'approved'].includes(status)) actions.push({ label: 'Post GL / hạch toán AP', target: 'finance-cockpit-ap', severity: 'warning' });
      if (status === 'posted') actions.push({ label: 'Tạo Settlement / thanh toán', target: 'finance-cockpit-settlements', severity: 'success' });
    } else {
      if (!['paid', 'closed'].includes(status)) actions.push({ label: 'Ghi nhận thanh toán / đối soát', target: 'finance-cockpit-settlements', severity: 'warning' });
    }
    const expectedVersion = row.version || 1;
    const today = shortDate(new Date());
    const financeCommand = (path, body = {}) => ({
      method: 'POST',
      path,
      body: { expected_version: expectedVersion, ...body }
    });
    if (actions.length) {
      actions[0].command = kind === 'actual_cost' && status === 'draft'
        ? financeCommand(`/api/tms/finance/costs/${row.id}/submit`)
        : kind === 'actual_cost' && status === 'submitted'
          ? financeCommand(`/api/tms/finance/costs/${row.id}/approve`)
          : kind === 'actual_cost' && status === 'approved'
            ? financeCommand(`/api/tms/finance/costs/${row.id}/ap-invoices`, { vendor_invoice_no: row.vendor_invoice_no || `AUTO-${row.id}`, invoice_date: row.invoice_date || today, due_date: row.due_date || today })
            : kind === 'ap_invoice' && status === 'draft'
              ? financeCommand(`/api/tms/finance/ap-invoices/${row.id}/submit`)
              : kind === 'ap_invoice' && status === 'submitted'
                ? financeCommand(`/api/tms/finance/ap-invoices/${row.id}/approve`)
                : kind === 'ap_invoice' && status === 'approved'
                  ? financeCommand(`/api/tms/finance/ap-invoices/${row.id}/post`)
                  : kind === 'ap_invoice' && status === 'posted'
                    ? financeCommand(`/api/tms/finance/ap-invoices/${row.id}/settlements`, { settlement_period: today.slice(0, 7) })
                    : kind === 'settlement' && !['paid', 'closed'].includes(status)
                      ? financeCommand(`/api/tms/finance/settlements/${row.id}/payments`, { amount: numberValue(row.remaining_amount ?? row.total_amount ?? row.amount), currency_code: row.currency_code || 'VND', posting_date: today, payment_method: row.payment_method || 'cash', reference_no: `PAY-${row.id}` })
                      : null;
      if (!actions[0].command) delete actions[0].command;
    }
    if (!actions.length) actions.push({ label: 'Theo dõi lịch sử và audit', target: 'accounting', severity: 'info' });
    return {
      id: row.id || row.code || '',
      kind,
      kind_label: config.label,
      title: `${config.label} ${row.id || row.code || ''}`.trim(),
      amount,
      currency,
      amount_label: amountLabel,
      status,
      status_label: statusLabel(row.status),
      fields: [
        { label: 'FO/DO', value: row.freight_order_id || row.fo_id || row.do_id || row.ap_invoice_id || 'Chưa gắn' },
        { label: 'Carrier/Vendor', value: row.carrier_id || row.vendor_id || 'Chưa chọn' },
        { label: 'Phiên bản', value: row.version ?? '—' }
      ],
      timeline: [
        { key: 'cost', label: 'Actual Cost', status: timelineStatus('cost') },
        { key: 'ap', label: 'AP Invoice', status: timelineStatus('ap') },
        { key: 'payment', label: 'Payment', status: timelineStatus('payment') },
        { key: 'settlement', label: 'Settlement', status: timelineStatus('settlement') }
      ],
      actions
    };
  }

  function buildFinanceConfigHealth(state) {
    const checks = [
      { key: 'currency', label: 'Tiền tệ', target: 'md-tab-currencies', ok: list(state, 'currencies').length > 0 },
      { key: 'tax', label: 'Mã thuế', target: 'md-tab-tax-codes', ok: list(state, 'tax_codes').some(isActiveRow) },
      { key: 'accounting_period', label: 'Kỳ kế toán mở', target: 'md-tab-accounting-periods', ok: list(state, 'accounting_periods').some(row => ['open', 'active'].includes(normalized(row.status))) },
      { key: 'carrier', label: 'Carrier/Vendor', target: 'md-tab-carriers', ok: list(state, 'carriers').some(isActiveRow) },
      { key: 'account_mapping', label: 'Mapping tài khoản', target: 'md-tab-account-mappings', ok: list(state, 'account_mappings').some(isActiveRow) }
    ];
    const done = checks.filter(item => item.ok).length;
    const items = checks.map(item => ({
      ...item,
      status: item.ok ? 'done' : 'missing',
      severity: item.ok ? 'success' : 'warning',
      message: item.ok
        ? `${item.label} đã sẵn sàng cho luồng tài chính.`
        : `Thiếu ${item.label}. Vào Master Data → ${item.target} để cấu hình trước khi post AP/settlement.`
    }));
    return {
      progress: { done, total: checks.length, percent: Math.round((done / checks.length) * 100) },
      items,
      guidance: items.some(item => item.status === 'missing')
        ? ['Vào Master Data để cấu hình các mục còn thiếu trước khi demo luồng AP/Settlement.', 'Không hiển thị lỗi kỹ thuật cho user; hãy điều hướng họ tới đúng tab cấu hình.']
        : ['Cấu hình finance đã đủ để demo luồng Actual Cost → AP → Payment → Settlement.']
    };
  }

  function buildFinanceMasterDataTabs(state) {
    const actionSet = (kind, label, seedLabel, endpoint, guidance = []) => ({
      actions: [
        { code: 'OPEN_CONFIG', kind, label, endpoint, severity: 'primary' },
        { code: 'SEED_EXAMPLE', kind, label: seedLabel, endpoint, severity: 'secondary' }
      ],
      guidance
    });
    const taxActions = actionSet(
      'tax_code',
      'Thêm mã thuế',
      'Nạp mẫu VAT demo',
      '/api/master-data/tax-codes',
      [
        'Cấu hình mã thuế trước khi tính Actual Cost, AP Invoice và hạch toán GL.',
        'Nếu thiếu API lưu dữ liệu, dùng script seed/master data backend để ghi vào CSDL PostgreSQL.'
      ]
    );
    const periodActions = actionSet(
      'accounting_period',
      'Thêm kỳ kế toán',
      'Nạp kỳ hiện tại',
      '/api/master-data/accounting-periods',
      [
        'Kỳ kế toán phải mở trước khi post AP, payment hoặc settlement.',
        'Không để user post vào kỳ đã khóa.'
      ]
    );
    const carrierActions = actionSet(
      'carrier',
      'Thêm carrier/vendor',
      'Nạp carrier nội bộ',
      '/api/tms/carriers',
      [
        'Nếu công ty tự vận chuyển, cấu hình carrier đội xe nội bộ để FO có thể đi Dispatch nội bộ.',
        'Nếu cần thuê ngoài, cấu hình carrier/vendor để chạy Tender.'
      ]
    );
    const mappingActions = actionSet(
      'account_mapping',
      'Thêm mapping tài khoản',
      'Nạp mapping GL demo',
      '/api/master-data/account-mappings',
      [
        'Mapping tài khoản là điều kiện trước khi post GL cho cost, AP, payment và chênh lệch tỷ giá.',
        'Thiếu mapping thì hệ thống phải báo vào Master Data → Mapping Tài Khoản để cấu hình.'
      ]
    );
    return [
      {
        id: 'md-tab-tax-codes',
        title: 'Mã thuế',
        count: list(state, 'tax_codes').length,
        empty_message: 'Chưa có mã thuế. Vào Master Data → Thuế để cấu hình trước khi tính chi phí/AP.',
        actions: taxActions.actions,
        guidance: taxActions.guidance,
        rows: list(state, 'tax_codes').map(row => ({
          code: row.code || row.id || 'N/A',
          rate: row.rate ?? row.tax_rate ?? '0',
          mode: row.tax_mode || row.mode || 'exclusive',
          status_label: statusLabel(row.status || (row.is_active === false ? 'inactive' : 'active')),
          effective: `${shortDate(row.effective_from)} → ${shortDate(row.effective_to)}`
        }))
      },
      {
        id: 'md-tab-accounting-periods',
        title: 'Kỳ kế toán',
        count: list(state, 'accounting_periods').length,
        empty_message: 'Chưa có kỳ kế toán mở. Vào Master Data → Kỳ Kế Toán để cấu hình trước khi hạch toán.',
        actions: periodActions.actions,
        guidance: periodActions.guidance,
        rows: list(state, 'accounting_periods').map(row => ({
          id: row.id || row.period_code || 'N/A',
          name: row.period_name || row.name || row.id || 'Kỳ kế toán',
          range: `${shortDate(row.start_date || row.starts_at)} → ${shortDate(row.end_date || row.ends_at)}`,
          status_label: statusLabel(row.status)
        }))
      },
      {
        id: 'md-tab-carriers',
        title: 'Carrier / vendor',
        count: list(state, 'carriers').length,
        empty_message: 'Chưa có carrier/vendor. Cấu hình carrier nội bộ nếu công ty tự vận chuyển, hoặc carrier thuê ngoài nếu cần tender.',
        actions: carrierActions.actions,
        guidance: carrierActions.guidance,
        rows: list(state, 'carriers').map(row => ({
          id: row.id || row.carrier_id || 'N/A',
          name: row.name || row.carrier_name || 'Chưa đặt tên',
          tax_code: row.tax_code || row.tax_id || 'Chưa có MST',
          type: row.is_internal ? 'Nội bộ' : 'Đối tác vận tải',
          status_label: statusLabel(row.status || (row.is_active === false ? 'inactive' : 'active'))
        }))
      },
      {
        id: 'md-tab-account-mappings',
        title: 'Mapping tài khoản',
        count: list(state, 'account_mappings').length,
        empty_message: 'Chưa có mapping tài khoản. Vào Master Data → Mapping Tài Khoản để cấu hình trước khi post GL.',
        actions: mappingActions.actions,
        guidance: mappingActions.guidance,
        rows: list(state, 'account_mappings').map(row => ({
          mapping_key: row.mapping_key || row.key || 'N/A',
          account_code: row.account_code || row.gl_account || 'Chưa gắn tài khoản',
          effective: `${shortDate(row.effective_from)} → ${shortDate(row.effective_to)}`,
          status_label: statusLabel(row.status || (row.is_active === false ? 'inactive' : 'active'))
        }))
      }
    ];
  }

  function isActiveRow(row) {
    return normalized(row && (row.status || (row.is_active === false ? 'inactive' : 'active'))) === 'active';
  }

  function buildExecutionModeCockpit(state) {
    const carriers = list(state, 'carriers');
    const vehicles = list(state, 'vehicles');
    const drivers = list(state, 'drivers');
    const freightOrders = list(state, 'freight_orders');
    const tenders = list(state, 'tenders');
    const tenderFoSet = new Set(tenders.map(tender => String(tender.freight_order_id || tender.fo_id || '')));
    const internalCarriers = carriers.filter(carrier => isActiveRow(carrier) && (carrier.is_internal === true || normalized(carrier.type || carrier.carrier_type) === 'internal'));
    const activeExternalCarriers = carriers.filter(carrier => isActiveRow(carrier) && !internalCarriers.includes(carrier));
    const readyVehicles = vehicles.filter(vehicle => ['available', 'ready', 'rảnh', 'ranh', 'sẵn_sàng', 'san_sang'].includes(normalized(vehicle.status || (vehicle.is_active === false ? 'inactive' : 'available'))));
    const readyDrivers = drivers.filter(driver => ['available', 'ready', 'rảnh', 'ranh', 'sẵn_sàng', 'san_sang'].includes(normalized(driver.status || (driver.is_active === false ? 'inactive' : 'available'))));
    const plannedOrders = freightOrders.filter(order => ['planned', 'ready_for_dispatch', 'ready_for_tender'].includes(normalized(order.status || order.canonical_status)));
    const internalReady = internalCarriers.length > 0 || readyVehicles.length > 0 || readyDrivers.length > 0;
    const internalCandidates = plannedOrders.filter(order => !tenderFoSet.has(String(order.id || '')));
    const outsourcedCandidates = plannedOrders.filter(order => tenderFoSet.has(String(order.id || '')) || !internalReady);
    const recommended = internalReady ? 'internal_fleet' : 'outsourced_carrier';
    const primary = recommended === 'internal_fleet'
      ? {
        title: 'Đội xe nội bộ',
        subtitle: 'Công ty tự vận chuyển: bỏ qua tender, đi thẳng sang Dispatch để chọn xe/tài xế.',
        action_label: 'Đi thẳng Dispatch',
        navigation: { view: 'dispatch' },
        count: internalCandidates.length
      }
      : {
        title: 'Thuê ngoài / Carrier Tender',
        subtitle: 'Chưa có đội xe nội bộ sẵn sàng, cần mở tender để chọn nhà vận chuyển.',
        action_label: 'Mở Tender Cockpit',
        navigation: { view: 'master-data' },
        count: outsourcedCandidates.length
      };

    return {
      recommended_mode: recommended,
      tender_required: !internalReady,
      primary,
      secondary: recommended === 'internal_fleet'
        ? {
          title: 'Thuê ngoài nếu cần',
          subtitle: 'Dùng khi đội xe nội bộ quá tải hoặc cần đối tác tuyến đặc biệt.',
          action_label: 'Mở Tender Cockpit',
          navigation: { view: 'master-data' },
          count: outsourcedCandidates.length
        }
        : {
          title: 'Thiết lập đội xe nội bộ',
          subtitle: 'Vào Master Data để cấu hình xe, tài xế và carrier nội bộ nếu công ty tự vận chuyển.',
          action_label: 'Mở Master Data',
          navigation: { view: 'master-data' },
          count: internalCandidates.length
        },
      kpis: {
        internal_carriers: { label: 'Carrier nội bộ', count: internalCarriers.length },
        ready_vehicles: { label: 'Xe nội bộ sẵn sàng', count: readyVehicles.length },
        ready_drivers: { label: 'Tài xế sẵn sàng', count: readyDrivers.length },
        external_carriers: { label: 'Carrier thuê ngoài', count: activeExternalCarriers.length }
      },
      internal_dispatch_candidates: internalCandidates.map(order => ({
        freight_order_id: order.id,
        status_label: statusLabel(order.status || order.canonical_status),
        action_label: 'Đi thẳng Dispatch',
        navigation: { view: 'dispatch' }
      })),
      guidance: internalReady
        ? [
          'Đội xe nội bộ là luồng mặc định cho công ty vận tải tự vận hành.',
          'Tender chỉ là nhánh thuê ngoài khi thiếu xe, thiếu tài xế hoặc cần đối tác tuyến đặc biệt.',
          'Nếu thiếu dữ liệu xe/tài xế, vào Master Data → Xe/Tài xế để cấu hình trước khi Dispatch.'
        ]
        : [
          'Chưa thấy đội xe nội bộ sẵn sàng, hệ thống đề xuất dùng Tender/Carrier.',
          'Nếu công ty tự vận chuyển, hãy cấu hình carrier nội bộ, xe và tài xế trong Master Data.'
        ]
    };
  }

  function buildTenderCockpit(state, now = new Date(), filters = {}) {
    const tenders = list(state, 'tenders');
    const offers = list(state, 'tender_offers');
    const carriers = list(state, 'carriers');
    const freightOrders = list(state, 'freight_orders');
    const executionMode = buildExecutionModeCockpit(state);
    const tenderFoSet = new Set(tenders.map(tender => String(tender.freight_order_id || tender.fo_id || '')));
    const openStatuses = new Set(['published', 'open', 'invited']);
    const awardedStatuses = new Set(['awarded', 'accepted']);
    const offerByTender = offers.reduce((acc, offer) => {
      const tenderId = String(offer.tender_id || '');
      acc[tenderId] = acc[tenderId] || [];
      acc[tenderId].push(offer);
      return acc;
    }, {});
    const activeCarriers = carriers.filter(carrier => normalized(carrier.status || (carrier.is_active === false ? 'inactive' : 'active')) === 'active');
    const plannedWithoutTender = freightOrders.filter(order => {
      const status = normalized(order.status || order.canonical_status);
      return ['planned', 'ready_for_tender'].includes(status) && !tenderFoSet.has(String(order.id));
    });
    const filterStatus = normalized(filters.status || '');
    const filterSearch = String(filters.search || '').trim().toLowerCase();
    const matchesFilters = tender => {
      if (filterStatus && normalized(tender.status) !== filterStatus) return false;
      if (filterSearch) {
        const haystack = `${tender.id || ''} ${tender.freight_order_id || tender.fo_id || ''} ${tender.status || ''}`.toLowerCase();
        if (!haystack.includes(filterSearch)) return false;
      }
      return true;
    };
    const openTenders = tenders.filter(tender => openStatuses.has(normalized(tender.status)) && matchesFilters(tender));
    const awardedTenders = tenders.filter(tender => awardedStatuses.has(normalized(tender.status)));
    const offersWaitingAward = offers.filter(offer => {
      const tender = tenders.find(item => String(item.id) === String(offer.tender_id));
      return tender && openStatuses.has(normalized(tender.status));
    });
    const money = (amount, currency = 'VND') => `${numberValue(amount).toLocaleString('vi-VN')} ${currency}`;
    return {
      kpis: {
        planned_without_tender: { label: executionMode.tender_required ? 'FO cần tender thuê ngoài' : 'FO có thể đi Dispatch nội bộ', count: plannedWithoutTender.length },
        open_tenders: { label: 'Tender đang mở', count: openTenders.length },
        offers_waiting_award: { label: 'Offer chờ chọn carrier', count: offersWaitingAward.length },
        awarded_tenders: { label: 'Tender đã award', count: awardedTenders.length },
        active_carriers: { label: 'Carrier đang hoạt động', count: activeCarriers.length },
        execution_mode: { label: 'Chế độ đề xuất', count: executionMode.recommended_mode === 'internal_fleet' ? 'Nội bộ' : 'Thuê ngoài' }
      },
      execution_mode: executionMode,
      open_tenders: openTenders.slice(0, 8).map(tender => {
        const deadline = tender.response_deadline ? new Date(tender.response_deadline) : null;
        const late = deadline && !Number.isNaN(deadline.getTime()) && deadline < now;
        return {
          id: tender.id,
          title: tender.id || 'Tender chưa có mã',
          freight_order_id: tender.freight_order_id || tender.fo_id || 'Chưa gắn FO',
          offer_count: (offerByTender[String(tender.id)] || []).length,
          deadline_label: tender.response_deadline ? shortDate(tender.response_deadline) : 'Chưa có hạn phản hồi',
          status_label: late ? 'Quá hạn phản hồi' : statusLabel(tender.status),
          detail_key: `tender:${tender.id}`
        };
      }),
      offers: offersWaitingAward
        .slice()
        .sort((a, b) => numberValue(a.amount) - numberValue(b.amount))
        .slice(0, 8)
        .map(offer => ({
          id: offer.id,
          tender_id: offer.tender_id,
          carrier_id: offer.carrier_id,
          amount_label: money(offer.amount, offer.currency_code || 'VND'),
          status_label: statusLabel(offer.status || 'submitted'),
          detail_key: `offer:${offer.id}`
        })),
      carriers: activeCarriers.slice(0, 8).map(carrier => ({
        id: carrier.id,
        name: carrier.name || carrier.carrier_name || carrier.id,
        type: carrier.is_internal ? 'Đội xe nội bộ' : 'Đối tác vận tải',
        tax_code: carrier.tax_code || 'Chưa có MST',
        detail_key: `carrier:${carrier.id}`
      })),
      filters_applied: {
        status: filterStatus,
        search: filterSearch,
        count: [filterStatus, filterSearch].filter(Boolean).length
      }
    };
  }

  function buildTenderRecordDetail(state, detailKey, now = new Date()) {
    const [kind, id] = String(detailKey || '').split(':');
    const tenders = list(state, 'tenders');
    const offers = list(state, 'tender_offers');
    const carriers = list(state, 'carriers');
    const freightOrders = list(state, 'freight_orders');
    const money = (amount, currency = 'VND') => `${numberValue(amount).toLocaleString('vi-VN')} ${currency}`;
    const activeExternalCarrier = carriers.find(carrier => isActiveRow(carrier) && carrier.is_internal !== true);
    const defaultOfferAmount = 1000000;
    const rankOffers = tenderId => offers
      .filter(offer => String(offer.tender_id || '') === String(tenderId || ''))
      .slice()
      .sort((a, b) => numberValue(a.amount) - numberValue(b.amount))
      .map((offer, index) => {
        const carrier = carriers.find(item => String(item.id) === String(offer.carrier_id));
        return {
          rank: index + 1,
          offer_id: offer.id || `OFFER-${index + 1}`,
          carrier_id: offer.carrier_id || '',
          carrier_name: carrier?.name || carrier?.carrier_name || offer.carrier_id || 'Chưa chọn carrier',
          amount_label: money(offer.amount, offer.currency_code || 'VND'),
          transit_time_hours: offer.transit_time_hours || 0,
          recommendation: index === 0 ? 'Giá tốt nhất' : 'Phương án dự phòng'
        };
      });

    if (kind === 'carrier') {
      const carrier = carriers.find(item => String(item.id) === String(id)) || carriers[0] || null;
      if (!carrier) {
        return { id: '', kind, kind_label: 'Carrier', title: 'Chưa có carrier', summary: [], offer_ranking: [], actions: [] };
      }
      const carrierOffers = offers.filter(offer => String(offer.carrier_id || '') === String(carrier.id || ''));
      return {
        id: carrier.id,
        kind,
        kind_label: 'Carrier',
        title: carrier.name || carrier.carrier_name || carrier.id,
        status_label: statusLabel(carrier.status || (carrier.is_active === false ? 'inactive' : 'active')),
        summary: [
          { label: 'Mã carrier', value: carrier.id },
          { label: 'Loại', value: carrier.is_internal ? 'Đội xe nội bộ' : 'Đối tác vận tải thuê ngoài' },
          { label: 'MST', value: carrier.tax_code || carrier.tax_id || 'Chưa có MST' },
          { label: 'Số offer', value: carrierOffers.length }
        ],
        offer_ranking: carrierOffers.map((offer, index) => ({
          rank: index + 1,
          offer_id: offer.id || `OFFER-${index + 1}`,
          carrier_id: carrier.id,
          carrier_name: carrier.name || carrier.id,
          amount_label: money(offer.amount, offer.currency_code || 'VND'),
          recommendation: statusLabel(offer.status || 'submitted')
        })),
        actions: [
          { label: carrier.is_internal ? 'Đi Dispatch nội bộ' : 'Mời carrier gửi offer', target: carrier.is_internal ? 'dispatch' : 'reporting', severity: carrier.is_internal ? 'success' : 'info' },
          { label: 'Mở Carrier Master', target: 'master-data', severity: 'info' }
        ]
      };
    }

    const tender = tenders.find(item => String(item.id) === String(id)) || tenders[0] || null;
    if (!tender) {
      return { id: '', kind: 'tender', kind_label: 'Tender', title: 'Chưa có tender', summary: [], offer_ranking: [], actions: [] };
    }
    const order = freightOrders.find(item => String(item.id) === String(tender.freight_order_id || tender.fo_id));
    const offerRanking = rankOffers(tender.id);
    const deadline = tender.response_deadline ? new Date(tender.response_deadline) : null;
    const overdue = deadline && !Number.isNaN(deadline.getTime()) && deadline < now;
    const bestOffer = offerRanking[0] || null;
    const tenderActions = [
      ...(bestOffer ? [{
        code: 'AWARD_BEST_OFFER',
        label: 'Chọn carrier tốt nhất',
        target: 'reporting',
        severity: 'success',
        confirm_required: true,
        command: {
          method: 'PUT',
          path: `/api/tms/tenders/${tender.id}/award`,
          body: { offer_id: bestOffer.offer_id, expected_version: tender.version || 1 }
        }
      }] : activeExternalCarrier ? [{
        code: 'INVITE_CARRIER_OFFER',
        label: 'Mời carrier gửi offer',
        target: 'reporting',
        severity: 'warning',
        requires_input: true,
        input_fields: [
          { name: 'carrier_id', label: 'Carrier', type: 'select', required: true },
          { name: 'amount', label: 'Giá chào', type: 'number', required: true },
          { name: 'currency_code', label: 'Tiền tệ', type: 'text', required: true },
          { name: 'note', label: 'Ghi chú', type: 'textarea' }
        ],
        command: {
          method: 'POST',
          path: `/api/tms/tenders/${tender.id}/offers`,
          body: {
            carrier_id: activeExternalCarrier.id || activeExternalCarrier.carrier_id,
            amount: defaultOfferAmount,
            currency_code: 'VND',
            note: 'Offer demo được tạo từ Tender Cockpit'
          }
        }
      }] : [{
        code: 'OPEN_CARRIER_MASTER',
        label: 'Mở Carrier Master',
        target: 'master-data',
        severity: 'warning'
      }]),
      { code: 'OPEN_CARRIER_MASTER', label: 'Mở Carrier Master', target: 'master-data', severity: 'info' }
    ];
    return {
      id: tender.id,
      kind: 'tender',
      kind_label: 'Tender',
      title: tender.id || 'Tender chưa có mã',
      status_label: overdue ? 'Quá hạn phản hồi' : statusLabel(tender.status),
      summary: [
        { label: 'FO', value: tender.freight_order_id || tender.fo_id || 'Chưa gắn FO' },
        { label: 'Trạng thái FO', value: statusLabel(order?.status || order?.canonical_status || 'planned') },
        { label: 'Hạn phản hồi', value: tender.response_deadline ? shortDate(tender.response_deadline) : 'Chưa có hạn phản hồi' },
        { label: 'Số offer', value: offerRanking.length }
      ],
      offer_ranking: offerRanking,
      legacy_actions: [
        ...(offerRanking.length ? [{ label: 'Chọn carrier tốt nhất', target: 'reporting', severity: 'success' }] : [{ label: 'Mời carrier gửi offer', target: 'reporting', severity: 'warning' }]),
        { label: 'Mở Carrier Master', target: 'master-data', severity: 'info' }
      ],
      actions: tenderActions
    };
  }

  function buildCarrierTenderHealth(state) {
    const mode = buildExecutionModeCockpit(state);
    const hasPlannedFo = list(state, 'freight_orders').some(order => ['planned', 'ready_for_tender', 'ready_for_dispatch'].includes(normalized(order.status || order.canonical_status)));
    const checks = [
      { key: 'internal_fleet', label: 'Đội xe nội bộ', ok: mode.kpis.ready_vehicles.count > 0 || mode.kpis.ready_drivers.count > 0 || mode.kpis.internal_carriers.count > 0, target: 'dispatch' },
      { key: 'external_carrier', label: 'Carrier thuê ngoài', ok: mode.kpis.external_carriers.count > 0, target: 'md-tab-carriers' },
      { key: 'planned_fo', label: 'FO chờ sourcing', ok: hasPlannedFo, target: 'reporting' },
      { key: 'tender_pipeline', label: 'Pipeline tender', ok: list(state, 'tenders').length > 0 || mode.tender_required === false, target: 'reporting' }
    ];
    const done = checks.filter(item => item.ok).length;
    const items = checks.map(item => ({
      ...item,
      status: item.ok ? 'done' : 'missing',
      message: item.ok
        ? `${item.label} đã sẵn sàng.`
        : `Thiếu ${item.label}. Vào ${item.target.includes('md-tab') ? 'Master Data' : item.target} để cấu hình.`
    }));
    return {
      progress: { done, total: checks.length, percent: Math.round((done / checks.length) * 100) },
      items,
      guidance: mode.tender_required
        ? ['FO cần tender thuê ngoài khi chưa có đội xe/tài xế nội bộ sẵn sàng.', 'Nếu công ty tự vận chuyển, cấu hình carrier nội bộ, xe và tài xế trước khi demo.']
        : ['FO có thể đi Dispatch nội bộ vì hệ thống thấy nguồn lực nội bộ sẵn sàng.', 'Tender chỉ dùng cho nhánh thuê ngoài khi thiếu xe/tài xế hoặc cần carrier chuyên tuyến.']
    };
  }

  function buildCarrierSourcingWorkbench(state, now = new Date()) {
    const freightOrders = list(state, 'freight_orders');
    const tenders = list(state, 'tenders');
    const executionMode = buildExecutionModeCockpit(state);
    const tenderFoSet = new Set(tenders.map(tender => String(tender.freight_order_id || tender.fo_id || '')));
    const responseDeadline = new Date(now.getTime() + 24 * 60 * 60 * 1000).toISOString();
    const plannedOrders = freightOrders.filter(order => {
      const status = normalized(order.status || order.canonical_status);
      return ['planned', 'ready_for_tender'].includes(status) && !tenderFoSet.has(String(order.id || ''));
    });
    const internalOrders = executionMode.tender_required ? [] : plannedOrders;
    const outsourcedOrders = executionMode.tender_required ? plannedOrders : [];
    const worklist = [
      ...internalOrders.map(order => ({
        freight_order_id: order.id,
        mode: 'internal_dispatch',
        title: `FO ${order.id}`,
        message: 'FO có thể đi Dispatch nội bộ vì công ty đang có đội xe/tài xế hoặc carrier nội bộ.',
        action_label: 'Đi Dispatch nội bộ',
        severity: 'success',
        navigation: { view: 'dispatch' }
      })),
      ...outsourcedOrders.map(order => ({
        freight_order_id: order.id,
        mode: 'outsourced_tender',
        title: `FO ${order.id}`,
        message: 'FO cần tender thuê ngoài vì chưa thấy nguồn lực nội bộ sẵn sàng.',
        action_label: 'Tạo tender thuê ngoài',
        severity: 'warning',
        navigation: { view: 'reporting' },
        requires_input: true,
        input_fields: [
          { name: 'freight_order_id', label: 'Freight Order', type: 'text', readonly: true, required: true },
          { name: 'response_deadline', label: 'Hạn phản hồi', type: 'datetime-local', required: true }
        ],
        command: {
          method: 'POST',
          path: '/api/tms/tenders',
          body: {
            freight_order_id: order.id,
            response_deadline: responseDeadline
          }
        }
      }))
    ];
    const alerts = outsourcedOrders.map(order => ({
      code: 'FO_NEEDS_OUTSOURCED_TENDER',
      freight_order_id: order.id,
      severity: 'warning',
      message: `FO ${order.id} cần tender thuê ngoài. Nếu công ty tự chạy được, hãy cấu hình đội xe nội bộ trong Master Data.`
    }));
    const guidance = executionMode.tender_required
      ? [
        'FO cần tender thuê ngoài chỉ xuất hiện khi hệ thống chưa thấy đội xe/tài xế nội bộ sẵn sàng.',
        'Nếu công ty anh tự vận chuyển, vào Master Data → Carrier/Vendor, Xe và Tài xế để cấu hình đội xe nội bộ trước.'
      ]
      : [
        'FO có thể đi Dispatch nội bộ khi công ty có đội xe/tài xế hoặc carrier nội bộ đang hoạt động.',
        'Tender chỉ dùng cho nhánh thuê ngoài: thiếu xe, thiếu tài xế hoặc cần đối tác tuyến đặc biệt.'
      ];
    return {
      kpis: {
        internal_dispatch: { label: 'FO có thể đi Dispatch nội bộ', count: internalOrders.length },
        outsourced_tender: { label: 'FO cần tender thuê ngoài', count: outsourcedOrders.length },
        active_mode: { label: 'Chế độ vận hành', count: executionMode.recommended_mode === 'internal_fleet' ? 'Nội bộ' : 'Thuê ngoài' }
      },
      worklist,
      alerts,
      guidance,
      execution_mode: executionMode
    };
  }

  function buildTenderDetailCockpit(state, now = new Date()) {
    const tenders = list(state, 'tenders');
    const offers = list(state, 'tender_offers');
    const carriers = list(state, 'carriers');
    const freightOrders = list(state, 'freight_orders');
    const executionMode = buildExecutionModeCockpit(state);
    const openStatuses = new Set(['published', 'open', 'invited']);
    const awardedStatuses = new Set(['awarded', 'accepted']);
    const carrierById = carriers.reduce((acc, carrier) => {
      acc[String(carrier.id || carrier.carrier_id || '')] = carrier;
      return acc;
    }, {});
    const offersByTender = offers.reduce((acc, offer) => {
      const tenderId = String(offer.tender_id || '');
      acc[tenderId] = acc[tenderId] || [];
      acc[tenderId].push(offer);
      return acc;
    }, {});
    const money = (amount, currency = 'VND') => `${numberValue(amount).toLocaleString('vi-VN')} ${currency}`;
    const activeExternalCarrier = carriers.find(carrier => isActiveRow(carrier) && carrier.is_internal !== true);
    const defaultOfferAmount = 1000000;
    const rankOffers = (rows) => rows
      .slice()
      .sort((a, b) => numberValue(a.amount) - numberValue(b.amount) || numberValue(a.transit_time_hours) - numberValue(b.transit_time_hours))
      .map((offer, index, sorted) => ({
        rank: index + 1,
        offer_id: offer.id,
        tender_id: offer.tender_id,
        carrier_id: offer.carrier_id,
        carrier_name: (carrierById[String(offer.carrier_id)] || {}).name || offer.carrier_id || 'Chưa rõ carrier',
        amount: numberValue(offer.amount),
        amount_label: money(offer.amount, offer.currency_code || 'VND'),
        transit_time_hours: numberValue(offer.transit_time_hours),
        recommendation: index === 0
          ? 'Giá tốt nhất'
          : numberValue(offer.transit_time_hours) < numberValue(sorted[0].transit_time_hours)
            ? 'Nhanh hơn nhưng giá cao hơn'
            : 'Phương án dự phòng',
        status_label: statusLabel(offer.status || 'submitted')
      }));

    const offerRanking = tenders.flatMap(tender => rankOffers(offersByTender[String(tender.id)] || []));
    const alerts = [];
    const pipeline = tenders.map(tender => {
      const status = normalized(tender.status);
      const rows = rankOffers(offersByTender[String(tender.id)] || []);
      const deadline = parseTime(tender.response_deadline);
      const overdue = deadline && deadline < now && openStatuses.has(status);
      const best = rows[0] || null;
      const awarded = awardedStatuses.has(status);
      const actions = [];
      if (!awarded && best) {
        actions.push({
          code: 'AWARD_BEST_OFFER',
          label: 'Chọn carrier tốt nhất',
          description: `Award offer ${best.offer_id} cho tender ${tender.id}.`,
          severity: 'success',
          confirm_required: true,
          command: {
            method: 'PUT',
            path: `/api/tms/tenders/${tender.id}/award`,
            body: { offer_id: best.offer_id, expected_version: tender.version || 1 }
          }
        });
      } else if (!awarded && activeExternalCarrier) {
        actions.push({
          code: 'INVITE_CARRIER_OFFER',
          label: 'Mời carrier gửi offer',
          description: `Tạo offer mẫu cho carrier ${activeExternalCarrier.id || activeExternalCarrier.carrier_id}.`,
          severity: overdue ? 'warning' : 'info',
          requires_input: true,
          input_fields: [
            { name: 'carrier_id', label: 'Carrier', type: 'select', required: true },
            { name: 'amount', label: 'Giá chào', type: 'number', required: true },
            { name: 'currency_code', label: 'Tiền tệ', type: 'text', required: true },
            { name: 'note', label: 'Ghi chú', type: 'textarea' }
          ],
          command: {
            method: 'POST',
            path: `/api/tms/tenders/${tender.id}/offers`,
            body: {
              carrier_id: activeExternalCarrier.id || activeExternalCarrier.carrier_id,
              amount: defaultOfferAmount,
              currency_code: 'VND',
              note: 'Offer demo được tạo từ Tender Cockpit'
            }
          }
        });
      }
      actions.push({
        code: 'OPEN_CARRIER_MASTER',
        label: 'Mở Carrier Master',
        description: 'Cấu hình carrier/vendor nếu thiếu nhà vận chuyển.',
        target: 'master-data',
        severity: 'info'
      });
      const actionLabel = awarded
        ? 'Đã award carrier'
        : rows.length
          ? 'So sánh & award carrier'
          : 'Mời carrier gửi offer';
      if (overdue && !rows.length) {
        alerts.push({
          code: 'TENDER_OVERDUE_NO_OFFER',
          tender_id: tender.id,
          severity: 'critical',
          message: `Tender ${tender.id} đã quá hạn nhưng chưa có offer.`
        });
      } else if (overdue) {
        alerts.push({
          code: 'TENDER_OVERDUE_WAITING_AWARD',
          tender_id: tender.id,
          severity: 'warning',
          message: `Tender ${tender.id} đã quá hạn, cần chọn carrier.`
        });
      }
      return {
        id: tender.id,
        freight_order_id: tender.freight_order_id || tender.fo_id || '',
        status,
        status_label: overdue ? 'Quá hạn phản hồi' : statusLabel(tender.status),
        offer_count: rows.length,
        best_offer_id: best && best.offer_id,
        best_carrier_id: best && best.carrier_id,
        best_amount_label: best ? best.amount_label : 'Chưa có offer',
        deadline_label: tender.response_deadline ? shortDate(tender.response_deadline) : 'Chưa có hạn phản hồi',
        action_label: actionLabel,
        actions,
        severity: overdue ? 'critical' : awarded ? 'done' : rows.length ? 'warning' : 'info'
      };
    });
    const tenderSet = new Set(tenders.map(tender => String(tender.freight_order_id || tender.fo_id || '')));
    const plannedWithoutTender = freightOrders.filter(order => {
      const status = normalized(order.status || order.canonical_status);
      const noTender = !tenderSet.has(String(order.id || ''));
      if (!['planned', 'ready_for_tender'].includes(status) || !noTender) return false;
      return executionMode.tender_required;
    });
    plannedWithoutTender.forEach(order => alerts.push({
      code: 'FO_WITHOUT_TENDER',
      tender_id: null,
      freight_order_id: order.id,
      severity: 'warning',
      message: `FO ${order.id} đã lập kế hoạch nhưng chưa có tender.`
    }));

    return {
      kpis: {
        tenders_need_action: { label: 'Tender cần xử lý', count: pipeline.filter(item => ['critical', 'warning', 'info'].includes(item.severity) && item.status !== 'awarded').length + plannedWithoutTender.length },
        offers_ranked: { label: 'Offer đã xếp hạng', count: offerRanking.length },
        overdue_tenders: { label: 'Tender quá hạn', count: pipeline.filter(item => item.severity === 'critical').length },
        awarded: { label: 'Đã award', count: pipeline.filter(item => item.status === 'awarded' || item.status === 'accepted').length }
      },
      pipeline,
      offer_ranking: offerRanking,
      alerts,
      execution_mode: executionMode,
      internal_dispatch_candidates: executionMode.internal_dispatch_candidates
    };
  }

  function buildTenderDecisionCockpit(state, now = new Date()) {
    const detail = buildTenderDetailCockpit(state, now);
    const executionMode = buildExecutionModeCockpit(state);
    const tenders = list(state, 'tenders');
    const offers = list(state, 'tender_offers');
    const carriers = list(state, 'carriers');
    const carrierById = carriers.reduce((acc, carrier) => {
      acc[String(carrier.id || carrier.carrier_id || '')] = carrier;
      return acc;
    }, {});
    const offersByTender = offers.reduce((acc, offer) => {
      const tenderId = String(offer.tender_id || '');
      acc[tenderId] = acc[tenderId] || [];
      acc[tenderId].push(offer);
      return acc;
    }, {});
    const money = (amount, currency = 'VND') => `${numberValue(amount).toLocaleString('vi-VN')} ${currency}`;
    const recommendedModeLabel = executionMode.recommended_mode === 'internal_fleet' ? 'Nội bộ' : 'Thuê ngoài';
    const modeMessage = executionMode.tender_required
      ? 'FO cần tender thuê ngoài khi chưa có đội xe/tài xế nội bộ sẵn sàng.'
      : 'FO có thể đi Dispatch nội bộ vì công ty đang có đội xe/tài xế hoặc carrier nội bộ.';
    const offerDecisions = tenders.map(tender => {
      const ranked = (offersByTender[String(tender.id)] || [])
        .slice()
        .sort((a, b) => numberValue(a.amount) - numberValue(b.amount) || numberValue(a.transit_time_hours) - numberValue(b.transit_time_hours));
      const best = ranked[0] || null;
      const second = ranked[1] || null;
      const carrier = best ? carrierById[String(best.carrier_id || '')] : null;
      const deadline = parseTime(tender.response_deadline);
      const overdue = deadline && deadline < now;
      return {
        tender_id: tender.id,
        freight_order_id: tender.freight_order_id || tender.fo_id || '',
        offer_count: ranked.length,
        best_offer_id: best && best.id || '',
        best_carrier_id: best && best.carrier_id || '',
        best_carrier_name: carrier?.name || carrier?.carrier_name || (best && best.carrier_id) || 'Chưa có carrier',
        best_amount: best ? numberValue(best.amount) : 0,
        best_amount_label: best ? money(best.amount, best.currency_code || 'VND') : 'Chưa có offer',
        saving_amount: best && second ? Math.max(0, numberValue(second.amount) - numberValue(best.amount)) : 0,
        saving_label: best && second ? money(Math.max(0, numberValue(second.amount) - numberValue(best.amount)), best.currency_code || second.currency_code || 'VND') : 'Chưa đủ offer để so sánh',
        decision_label: best ? 'Award carrier đề xuất' : overdue ? 'Mời carrier gấp' : 'Mời carrier gửi offer',
        severity: overdue && !best ? 'critical' : best ? 'success' : 'warning',
        navigation: { view: 'accounting', target: 'tender-cockpit-panel' }
      };
    });
    const carrierScorecards = carriers.map(carrier => {
      const carrierId = String(carrier.id || carrier.carrier_id || '');
      const carrierOffers = offers.filter(offer => String(offer.carrier_id || '') === carrierId);
      const awardedCount = tenders.filter(tender => String(tender.awarded_carrier_id || tender.carrier_id || '') === carrierId).length;
      const avgAmount = carrierOffers.length
        ? Math.round(carrierOffers.reduce((sum, offer) => sum + numberValue(offer.amount), 0) / carrierOffers.length)
        : 0;
      const avgTransit = carrierOffers.length
        ? Math.round(carrierOffers.reduce((sum, offer) => sum + numberValue(offer.transit_time_hours), 0) / carrierOffers.length)
        : 0;
      const status = isActiveRow(carrier) ? 'active' : 'inactive';
      return {
        carrier_id: carrierId,
        carrier_name: carrier.name || carrier.carrier_name || carrierId,
        type_label: carrier.is_internal ? 'Đội xe nội bộ' : 'Carrier thuê ngoài',
        status,
        offer_count: carrierOffers.length,
        awarded_count: awardedCount,
        avg_amount_label: avgAmount ? money(avgAmount, carrierOffers[0]?.currency_code || 'VND') : 'Chưa có offer',
        avg_transit_hours: avgTransit,
        score: Math.max(0, 100 - (status === 'inactive' ? 40 : 0) - Math.min(30, avgTransit * 2) + Math.min(20, awardedCount * 5)),
        navigation: { view: 'master-data', target: 'md-tab-carriers' }
      };
    }).sort((a, b) => b.score - a.score || String(a.carrier_id).localeCompare(String(b.carrier_id)));
    const riskBoard = [];
    offers.forEach(offer => {
      if (!carrierById[String(offer.carrier_id || '')]) {
        riskBoard.push({
          code: 'CARRIER_MASTER_MISSING',
          carrier_id: offer.carrier_id || '',
          title: `Carrier ${offer.carrier_id || ''} chưa có trong Master Data`,
          message: 'Offer đang tham chiếu carrier chưa cấu hình. Vào Master Data → Carrier/Vendor để bổ sung.',
          severity: 'critical',
          navigation: { view: 'master-data', target: 'md-tab-carriers' }
        });
      }
    });
    detail.pipeline.forEach(item => {
      if (item.severity === 'critical' || item.status_label === 'Quá hạn phản hồi') {
        riskBoard.push({
          code: 'TENDER_OVERDUE',
          tender_id: item.id,
          title: `Tender ${item.id} quá hạn`,
          message: item.offer_count ? 'Tender đã quá hạn, cần award carrier.' : 'Tender đã quá hạn nhưng chưa có offer.',
          severity: item.offer_count ? 'warning' : 'critical',
          navigation: { view: 'accounting', target: 'tender-cockpit-panel' }
        });
      }
    });
    const nextBestActions = [
      ...offerDecisions.filter(item => item.best_offer_id).slice(0, 3).map(item => ({
        code: 'AWARD_CARRIER',
        label: `Award carrier ${item.best_carrier_id} cho ${item.tender_id}`,
        description: `Offer tốt nhất ${item.best_amount_label}, tiết kiệm ${item.saving_label}.`,
        navigation: { view: 'accounting', target: 'tender-cockpit-panel' }
      })),
      ...offerDecisions.filter(item => !item.best_offer_id).slice(0, 3).map(item => ({
        code: 'INVITE_CARRIER',
        label: `Mời carrier gửi offer cho ${item.tender_id}`,
        description: 'Tender chưa có offer để so sánh, cần gửi mời giá hoặc cấu hình carrier.',
        navigation: { view: 'accounting', target: 'tender-cockpit-panel' }
      }))
    ];
    return {
      summary: {
        recommended_mode: executionMode.recommended_mode,
        recommended_mode_label: recommendedModeLabel,
        message: modeMessage,
        tender_required: executionMode.tender_required,
        open_decisions: offerDecisions.filter(item => item.severity !== 'success').length,
        risks: riskBoard.length
      },
      offer_decisions: offerDecisions,
      carrier_scorecards: carrierScorecards,
      risk_board: riskBoard,
      next_best_actions: nextBestActions
    };
  }

  function parseTime(value) {
    if (!value) return null;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function resourceComplianceAlerts(state, vehicleId, driverId, day = new Date()) {
    const alerts = [];
    const checkDate = new Date(day);
    checkDate.setHours(0, 0, 0, 0);
    const warningDate = new Date(checkDate);
    warningDate.setDate(warningDate.getDate() + 14);
    const vehicle = list(state, 'vehicles').find(item => String(item.id || item.vehicle_id || item.plate_no || '') === String(vehicleId || ''));
    const driver = list(state, 'drivers').find(item => String(item.id || item.driver_id || item.name || '') === String(driverId || ''));
    const addExpiryAlert = (codeExpired, codeSoon, label, value, ownerId, ownerType) => {
      const date = parseTime(value);
      if (!date) return;
      if (date < checkDate) {
        alerts.push({
          code: codeExpired,
          severity: 'critical',
          resource_id: ownerId,
          owner_type: ownerType,
          message: `${label} đã hết hạn (${shortDate(value)}). Vào Master Data để cập nhật trước khi điều phối.`,
          navigation: { view: 'master-data', label: 'Mở Master Data' }
        });
      } else if (date <= warningDate) {
        alerts.push({
          code: codeSoon,
          severity: 'warning',
          resource_id: ownerId,
          owner_type: ownerType,
          message: `${label} sắp hết hạn (${shortDate(value)}). Nên cập nhật Master Data trước chuyến kế tiếp.`,
          navigation: { view: 'master-data', label: 'Mở Master Data' }
        });
      }
    };
    if (vehicle) {
      const status = normalized(vehicle.status);
      if (['maintenance', 'bao_tri', 'bảo_trì', 'repair', 'inactive', 'disabled'].includes(status)) {
        alerts.push({
          code: 'VEHICLE_NOT_READY',
          severity: 'critical',
          resource_id: vehicleId,
          owner_type: 'vehicle',
          message: `Xe ${vehicleId} chưa sẵn sàng hoạt động. Vào Master Data → Xe để kiểm tra trạng thái/bảo dưỡng.`,
          navigation: { view: 'master-data', label: 'Mở Master Data' }
        });
      }
      addExpiryAlert('VEHICLE_INSPECTION_EXPIRED', 'VEHICLE_INSPECTION_EXPIRING', `Đăng kiểm xe ${vehicleId}`, vehicle.inspection_exp || vehicle.inspection_expiry || vehicle.registration_expiry, vehicleId, 'vehicle');
      addExpiryAlert('VEHICLE_INSURANCE_EXPIRED', 'VEHICLE_INSURANCE_EXPIRING', `Bảo hiểm xe ${vehicleId}`, vehicle.insurance_date || vehicle.insurance_exp || vehicle.insurance_expiry, vehicleId, 'vehicle');
      addExpiryAlert('VEHICLE_MAINTENANCE_DUE', 'VEHICLE_MAINTENANCE_SOON', `Bảo dưỡng xe ${vehicleId}`, vehicle.maintenance_date || vehicle.next_maintenance_date, vehicleId, 'vehicle');
    }
    if (driver) {
      const status = normalized(driver.status);
      if (['inactive', 'disabled', 'busy_unavailable', 'suspended', 'nghi', 'nghỉ'].includes(status)) {
        alerts.push({
          code: 'DRIVER_NOT_READY',
          severity: 'critical',
          resource_id: driverId,
          owner_type: 'driver',
          message: `Tài xế ${driverId} chưa sẵn sàng hoạt động. Vào Master Data → Tài xế để kiểm tra trạng thái.`,
          navigation: { view: 'master-data', label: 'Mở Master Data' }
        });
      }
      addExpiryAlert('DRIVER_LICENSE_EXPIRED', 'DRIVER_LICENSE_EXPIRING', `Bằng lái tài xế ${driverId}`, driver.license_exp || driver.license_expiry || driver.license_valid_to || driver.valid_to, driverId, 'driver');
    }
    return alerts;
  }

  function timeLabel(date) {
    if (!date) return '--:--';
    return date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
  }

  function dispatchStatusMeta(status) {
    const key = normalized(status || 'planned');
    const meta = {
      draft: { label: 'Nháp', color: '#64748b' },
      planned: { label: 'Chờ xếp lịch', color: '#f59e0b' },
      approved: { label: 'Chờ điều phối', color: '#f59e0b' },
      ready_for_dispatch: { label: 'Chờ điều phối', color: '#0ea5e9' },
      dispatched: { label: 'Đã điều phối', color: '#7c3aed' },
      picked: { label: 'Đã lấy hàng', color: '#0891b2' },
      in_transit: { label: 'Đang vận chuyển', color: '#2563eb' },
      arrived: { label: 'Đã đến nơi', color: '#16a34a' },
      delivered: { label: 'Hoàn thành', color: '#059669' },
      completed: { label: 'Hoàn thành', color: '#059669' },
      cancelled: { label: 'Đã hủy', color: '#dc2626' }
    };
    return { status_key: key, ...(meta[key] || { label: statusLabel(status), color: '#64748b' }) };
  }

  function uniqueOptions(items, valueKey, labelPrefix) {
    const seen = new Set();
    return items
      .map(item => item[valueKey])
      .filter(Boolean)
      .filter(value => {
        const key = String(value);
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      })
      .sort((a, b) => String(a).localeCompare(String(b)))
      .map(value => ({ value: String(value), label: labelPrefix ? `${labelPrefix} ${value}` : String(value) }));
  }

  function ganttPosition(start, end, axis) {
    const dayStart = new Date(start);
    dayStart.setHours(axis.start_hour, 0, 0, 0);
    const dayEnd = new Date(start);
    dayEnd.setHours(axis.end_hour, 0, 0, 0);
    const totalMs = Math.max(1, dayEnd - dayStart);
    const left = Math.max(0, Math.min(100, ((start - dayStart) / totalMs) * 100));
    const right = Math.max(0, Math.min(100, ((end - dayStart) / totalMs) * 100));
    return {
      left_percent: Math.round(left * 10) / 10,
      width_percent: Math.max(3, Math.round((right - left) * 10) / 10)
    };
  }

  function buildDispatchCalendar(state, day = new Date(), filters = {}) {
    const timeAxis = {
      start_hour: 6,
      end_hour: 22,
      labels: ['06:00', '10:00', '14:00', '18:00', '22:00']
    };
    const calendarDayStart = new Date(day);
    calendarDayStart.setHours(0, 0, 0, 0);
    const calendarDayEnd = new Date(calendarDayStart);
    calendarDayEnd.setDate(calendarDayEnd.getDate() + 1);
    const intersectsCalendarDay = (start, end) => start && end && end > calendarDayStart && start < calendarDayEnd;
    const deliveryOrders = list(state, 'delivery_orders');
    const trips = list(state, 'transport_trips');
    const scheduled = [];
    const unscheduled = [];
    const coveredDoIds = new Set();
    trips.forEach(trip => {
      (Array.isArray(trip.delivery_order_ids) ? trip.delivery_order_ids : []).forEach(doId => coveredDoIds.add(String(doId)));
      const start = parseTime(trip.planned_departure_at || trip.dispatch_at || trip.created_at);
      const end = parseTime(trip.planned_return_at || trip.actual_return_at || trip.planned_arrival_at || trip.actual_arrival_at);
      const vehicleId = trip.vehicle_id || trip.vehicle || trip.truck_id;
      const driverId = trip.driver_id || trip.driver || trip.main_driver_id;
      const status = trip.status || 'planned';
      const meta = dispatchStatusMeta(status);
      const summary = trip.relationship_summary || {};
      const doCount = Number(summary.do_count || (Array.isArray(trip.delivery_order_ids) ? trip.delivery_order_ids.length : 0));
      const returnDistance = numberValue(trip.return_distance_km);
      const complianceAlerts = resourceComplianceAlerts(state, vehicleId, driverId, day);
      if (start && end && !intersectsCalendarDay(start, end)) return;
      if (!start || !end || end <= start || !vehicleId || !driverId) {
        const missingParts = [
          !vehicleId ? 'xe' : '',
          !driverId ? 'tài xế' : '',
          (!start || !end || end <= start) ? 'giờ đi/giờ về' : ''
        ].filter(Boolean);
        unscheduled.push({
          id: trip.id,
          kind: 'trip',
          status,
          status_key: meta.status_key,
          status_label: meta.label,
          vehicle_id: vehicleId || '',
          driver_id: driverId || '',
          delivery_order_ids: Array.isArray(trip.delivery_order_ids) ? trip.delivery_order_ids : [],
          reason: 'Trip thiếu xe/tài xế hoặc thiếu giờ đi/giờ về để lên lịch điều phối',
          navigation: { view: 'dispatch', label: 'Mở Dispatch', entity_id: trip.id }
        });
        return;
      }
      const relationshipLabel = [
        doCount > 1 || summary.has_many_dos_on_trip ? `gom ${doCount} DO` : '1 DO',
        summary.has_split_do_across_trips ? 'DO chia nhiều xe/chuyến' : '',
      ].filter(Boolean).join(' · ');
      scheduled.push({
        id: trip.id,
        kind: 'trip',
        status,
        status_key: meta.status_key,
        status_label: meta.label,
        status_color: meta.color,
        resource_id: vehicleId || driverId,
        vehicle_id: vehicleId || 'Chưa gắn xe',
        driver_id: driverId || 'Chưa gắn tài xế',
        delivery_order_ids: Array.isArray(trip.delivery_order_ids) ? trip.delivery_order_ids : [],
        relationship_label: relationshipLabel,
        return_distance_label: `Quay đầu: ${returnDistance.toFixed(1)} km`,
        total_distance_label: `Tổng: ${numberValue(trip.total_distance_km).toFixed(1)} km`,
        timeline_label: trip.planned_return_at ? `Đi → giao → quay đầu (${timeLabel(end)})` : 'Đi → giao',
        compliance_alerts: complianceAlerts,
        start,
        end,
        start_label: timeLabel(start),
        end_label: timeLabel(end),
        duration_hours: Math.round((end - start) / 36e5 * 10) / 10,
        gantt: ganttPosition(start, end, timeAxis),
        navigation: {
          view: ['in_transit', 'arrived', 'delivered', 'completed'].includes(meta.status_key) ? 'tracking' : 'dispatch',
          label: ['in_transit', 'arrived', 'delivered', 'completed'].includes(meta.status_key) ? 'Mở GPS/POD' : 'Mở Dispatch',
          entity_id: trip.id
        }
      });
    });
    deliveryOrders.filter(order => !coveredDoIds.has(String(order.id || ''))).forEach(order => {
      const start = parseTime(order.pickup_date || order.planned_pickup_at || order.dispatch_date);
      const end = parseTime(order.delivery_date || order.planned_delivery_at || order.eta);
      const vehicleId = order.vehicle_id || order.vehicle || order.truck_id;
      const driverId = order.driver_id || order.driver || order.main_driver_id;
      const status = order.status || order.canonical_status || 'planned';
      const meta = dispatchStatusMeta(status);
      const complianceAlerts = resourceComplianceAlerts(state, vehicleId, driverId, day);
      if (start && end && !intersectsCalendarDay(start, end)) return;
      if (!start || !end || end <= start || !vehicleId || !driverId) {
        const missingParts = [
          !vehicleId ? 'xe' : '',
          !driverId ? 'tài xế' : '',
          (!start || !end || end <= start) ? 'khung giờ lấy/giao hàng' : ''
        ].filter(Boolean);
        unscheduled.push({
          id: order.id,
          kind: 'delivery_order',
          status,
          status_key: meta.status_key,
          status_label: meta.label,
          vehicle_id: vehicleId || '',
          driver_id: driverId || '',
          reason: 'Thiếu xe/tài xế hoặc thiếu khung giờ lấy-giao hàng',
          navigation: { view: 'dispatch', label: 'Mở Dispatch' }
        });
        return;
      }
      scheduled.push({
        id: order.id,
        kind: 'delivery_order',
        status,
        status_key: meta.status_key,
        status_label: meta.label,
        status_color: meta.color,
        resource_id: vehicleId || driverId,
        vehicle_id: vehicleId || 'Chưa gắn xe',
        driver_id: driverId || 'Chưa gắn tài xế',
        start,
        end,
        start_label: timeLabel(start),
        end_label: timeLabel(end),
        relationship_label: 'DO chưa gom vào Trip',
        return_distance_label: order.planned_return_at ? `Quay đầu: ${numberValue(order.return_distance_km).toFixed(1)} km` : 'Chưa có lượt về',
        total_distance_label: `Tổng: ${numberValue(order.distance_km || order.total_distance || order.planned_distance_km).toFixed(1)} km`,
        timeline_label: order.planned_return_at ? `Đi → giao → quay đầu (${timeLabel(parseTime(order.planned_return_at))})` : 'Đi → giao',
        compliance_alerts: complianceAlerts,
        duration_hours: Math.round((end - start) / 36e5 * 10) / 10,
        gantt: ganttPosition(start, end, timeAxis),
        navigation: {
          view: ['in_transit', 'arrived', 'delivered', 'completed'].includes(meta.status_key) ? 'tracking' : 'dispatch',
          label: ['in_transit', 'arrived', 'delivered', 'completed'].includes(meta.status_key) ? 'Mở GPS/POD' : 'Mở Dispatch'
        }
      });
    });

    const normalizedFilters = {
      vehicle_id: String(filters.vehicle_id || '').trim(),
      driver_id: String(filters.driver_id || '').trim(),
      status: String(filters.status || '').trim()
    };
    const filteredScheduled = scheduled.filter(item => {
      if (normalizedFilters.vehicle_id && String(item.vehicle_id) !== normalizedFilters.vehicle_id) return false;
      if (normalizedFilters.driver_id && String(item.driver_id) !== normalizedFilters.driver_id) return false;
      if (normalizedFilters.status && item.status_key !== normalized(normalizedFilters.status)) return false;
      return true;
    });
    const filteredUnscheduled = unscheduled.filter(item => {
      if (normalizedFilters.vehicle_id && String(item.vehicle_id) !== normalizedFilters.vehicle_id) return false;
      if (normalizedFilters.driver_id && String(item.driver_id) !== normalizedFilters.driver_id) return false;
      if (normalizedFilters.status && item.status_key !== normalized(normalizedFilters.status)) return false;
      return true;
    });

    const byResource = filteredScheduled.reduce((acc, item) => {
      acc[item.resource_id] = acc[item.resource_id] || [];
      acc[item.resource_id].push(item);
      return acc;
    }, {});
    const vehicles = list(state, 'vehicles');
    const vehicleById = new Map(vehicles.map(vehicle => [
      String(vehicle.id || vehicle.vehicle_id || ''),
      vehicle
    ]).filter(([id]) => id));
    const laneResourceIds = new Set(Object.keys(byResource));
    vehicles.forEach(vehicle => {
      const vehicleId = String(vehicle.id || vehicle.vehicle_id || '');
      if (vehicleId && (!normalizedFilters.vehicle_id || vehicleId === normalizedFilters.vehicle_id)) {
        laneResourceIds.add(vehicleId);
      }
    });
    const readyVehicleStatuses = new Set([
      'available', 'ready', 'ranh', 'san_sang', 'ranh_san_sang', 'sẵn_sàng', 'sẵn_sàng_rảnh'
    ]);
    const lanes = Array.from(laneResourceIds).map(resourceId => {
      const items = byResource[resourceId] || [];
      const sortedItems = items.slice().sort((a, b) => a.start - b.start);
      const bookedHours = sortedItems.reduce((sum, item) => sum + item.duration_hours, 0);
      const utilization = Math.min(100, Math.round(bookedHours * 100 / (timeAxis.end_hour - timeAxis.start_hour)));
      const vehicle = vehicleById.get(String(resourceId)) || {};
      const vehicleStatus = normalized(vehicle.status || (vehicle.is_active === false ? 'inactive' : 'available'));
      return {
        resource_id: resourceId,
        label: `Xe ${resourceId}`,
        vehicle_status: vehicle.status || '',
        is_available: sortedItems.length === 0 && readyVehicleStatuses.has(vehicleStatus),
        utilization_percent: utilization,
        load_level: utilization >= 80 ? 'high' : utilization >= 45 ? 'medium' : 'normal',
        items: sortedItems
      };
    }).sort((a, b) => String(a.resource_id).localeCompare(String(b.resource_id)));

    const conflicts = [];
    const capacityAlerts = [];
    lanes.forEach(lane => {
      lane.items.forEach(item => {
        (item.compliance_alerts || []).forEach(alert => {
          capacityAlerts.push({
            ...alert,
            trip_id: item.id,
            order_ids: item.delivery_order_ids || [item.id],
            action_label: 'Cập nhật Master Data trước khi điều phối',
            navigation: alert.navigation || { view: 'master-data', label: 'Mở Master Data' }
          });
        });
      });
      for (let index = 1; index < lane.items.length; index += 1) {
        const previous = lane.items[index - 1];
        const current = lane.items[index];
        if (current.start < previous.end) {
          conflicts.push({
            severity: 'critical',
            resource_id: lane.resource_id,
            order_ids: [previous.id, current.id],
            message: `Xe ${lane.resource_id} bị trùng lịch giữa ${previous.id} và ${current.id}.`,
            action_label: 'Mở Dispatch để xử lý trùng lịch',
            navigation: { view: 'dispatch', label: 'Mở Dispatch' }
          });
          lane.load_level = 'overlap';
          capacityAlerts.push({
            code: 'RESOURCE_OVERLAP',
            severity: 'critical',
            resource_id: lane.resource_id,
            message: `Xe ${lane.resource_id} có lịch chồng nhau, cần đổi xe hoặc đổi khung giờ.`,
            navigation: { view: 'dispatch', label: 'Mở Dispatch' }
          });
        }
      }
      if (lane.load_level === 'high') {
        capacityAlerts.push({
          code: 'RESOURCE_HIGH_UTILIZATION',
          severity: 'warning',
          resource_id: lane.resource_id,
          message: `Xe ${lane.resource_id} đang sử dụng ${lane.utilization_percent}% khung giờ vận hành.`,
          navigation: { view: 'dispatch', label: 'Mở Dispatch' }
        });
      }
    });

    const statusOptions = Array.from(new Map(scheduled.map(item => [item.status_key, {
      value: item.status,
      label: item.status_label,
      status_key: item.status_key,
      color: item.status_color
    }])).values()).sort((a, b) => a.label.localeCompare(b.label));
    const legend = [
      dispatchStatusMeta('planned'),
      dispatchStatusMeta('approved'),
      dispatchStatusMeta('dispatched'),
      dispatchStatusMeta('in_transit'),
      dispatchStatusMeta('delivered'),
      dispatchStatusMeta('cancelled')
    ].map(item => ({ status_key: item.status_key, label: item.label, color: item.color }));

    return {
      day: shortDate(day),
      kpis: {
        scheduled: { label: 'Chuyến đã lên lịch', count: filteredScheduled.length },
        conflicts: { label: 'Cảnh báo trùng lịch', count: conflicts.length },
        unscheduled: { label: 'DO/Trip thiếu lịch', count: filteredUnscheduled.length },
        return_planned: { label: 'Xe đã có giờ quay đầu', count: filteredScheduled.filter(item => item.timeline_label && item.timeline_label.includes('quay đầu')).length },
        multi_do_trips: { label: 'Trip gom nhiều DO', count: filteredScheduled.filter(item => item.relationship_label && item.relationship_label.includes('gom')).length },
        split_do_trips: { label: 'DO chia nhiều xe/chuyến', count: filteredScheduled.filter(item => item.relationship_label && item.relationship_label.includes('chia nhiều')).length },
        compliance_issues: { label: 'Cảnh báo xe/tài xế', count: filteredScheduled.reduce((sum, item) => sum + (item.compliance_alerts || []).length, 0) }
      },
      time_axis: timeAxis,
      lanes,
      conflicts,
      capacity_alerts: capacityAlerts,
      unscheduled: filteredUnscheduled,
      filters: normalizedFilters,
      filter_options: {
        vehicles: vehicles.map(vehicle => ({
          value: String(vehicle.id || vehicle.vehicle_id || ''),
          label: `Xe ${vehicle.id || vehicle.vehicle_id || ''}`
        })).filter(option => option.value).sort((a, b) => a.label.localeCompare(b.label)),
        drivers: uniqueOptions(scheduled, 'driver_id', 'Tài xế'),
        statuses: statusOptions
      },
      legend
    };
  }

  function buildDispatchCapacityBoard(state, day = new Date()) {
    const calendar = buildDispatchCalendar(state, day, {});
    const vehicles = list(state, 'vehicles');
    const scheduledVehicleIds = new Set(calendar.lanes.map(lane => String(lane.resource_id || '')));
    const readyVehicles = vehicles.filter(vehicle => {
      const status = normalized(vehicle.status || (vehicle.is_active === false ? 'inactive' : 'available'));
      return ['available', 'ready', 'ranh', 'rảnh', 'san_sang', 'sẵn_sàng'].includes(status)
        && !scheduledVehicleIds.has(String(vehicle.id || vehicle.vehicle_id || ''));
    });
    const vehicleCards = calendar.lanes.map(lane => {
      const riskLevel = lane.load_level === 'overlap'
        ? 'overlap'
        : lane.load_level === 'high'
          ? 'high'
          : lane.utilization_percent >= 45
            ? 'medium'
            : 'normal';
      return {
        resource_id: lane.resource_id,
        label: lane.label,
        utilization_percent: lane.utilization_percent,
        trip_count: lane.items.length,
        risk_level: riskLevel,
        risk_label: riskLevel === 'overlap' ? 'Trùng lịch' : riskLevel === 'high' ? 'Gần quá tải' : 'Ổn',
        action_label: riskLevel === 'overlap' ? 'Đổi xe/khung giờ' : 'Xem lịch xe',
        navigation: { view: 'dispatch', label: 'Mở Dispatch' }
      };
    });
    const priorityAlerts = [
      ...calendar.conflicts.map(alert => ({
        code: 'RESOURCE_OVERLAP',
        severity: 'critical',
        resource_id: alert.resource_id,
        message: alert.message,
        action_label: 'Đổi xe hoặc đổi khung giờ',
        navigation: alert.navigation || { view: 'dispatch', label: 'Mở Dispatch' }
      })),
      ...calendar.capacity_alerts
        .filter(alert => alert.code === 'RESOURCE_HIGH_UTILIZATION')
        .map(alert => ({
          code: alert.code,
          severity: alert.severity,
          resource_id: alert.resource_id,
          message: alert.message,
          action_label: 'Kiểm tra tải xe',
          navigation: alert.navigation || { view: 'dispatch', label: 'Mở Dispatch' }
        }))
    ];
    const unscheduledWorklist = calendar.unscheduled.map(item => ({
      id: item.id,
      status_label: item.status_label,
      reason: item.reason,
      action_label: 'Xếp lịch/điều phối',
      navigation: item.navigation || { view: 'dispatch', label: 'Mở Dispatch' }
    }));
    const recommendations = [];
    if (priorityAlerts.some(alert => alert.code === 'RESOURCE_OVERLAP')) {
      recommendations.push('Có xe bị trùng lịch: ưu tiên đổi xe hoặc đổi khung giờ trước khi xuất bến.');
    }
    if (unscheduledWorklist.length) {
      recommendations.push('Có DO chưa đủ lịch/tài nguyên: vào Dispatch để xếp lịch lấy-giao và phân xe/tài xế.');
    }
    if (!recommendations.length) {
      recommendations.push('Nguồn lực điều phối đang ổn, tiếp tục theo dõi GPS/POD cho các chuyến đang chạy.');
    }
    return {
      kpis: {
        ready_vehicles: { label: 'Xe rảnh thật sự', count: readyVehicles.length },
        busy_vehicles: { label: 'Xe đang có lịch', count: vehicleCards.length },
        overloaded_resources: { label: 'Xe quá tải/trùng lịch', count: vehicleCards.filter(card => ['overlap', 'high'].includes(card.risk_level)).length },
        unscheduled_orders: { label: 'DO cần xếp lịch', count: unscheduledWorklist.length }
      },
      vehicle_cards: vehicleCards,
      priority_alerts: priorityAlerts,
      unscheduled_worklist: unscheduledWorklist,
      recommendations
    };
  }

  function buildDispatchWeekPlanner(state, startDay = new Date()) {
    const start = new Date(startDay);
    start.setHours(0, 0, 0, 0);
    const daysSinceMonday = (start.getDay() + 6) % 7;
    start.setDate(start.getDate() - daysSinceMonday);
    const days = Array.from({ length: 7 }, (_, index) => {
      const date = new Date(start);
      date.setDate(start.getDate() + index);
      const localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
      return {
        key: shortDate(date),
        iso_date: localDate.toISOString().slice(0, 10),
        date,
        label: date.toLocaleDateString('vi-VN', { weekday: 'short', day: '2-digit', month: '2-digit' })
      };
    });
    const vehicles = list(state, 'vehicles');
    const calendars = days.map(day => buildDispatchCalendar(state, day.date, {}));
    const vehicleIds = Array.from(new Set([
      ...vehicles.map(vehicle => vehicle.id || vehicle.vehicle_id || vehicle.plate_no).filter(Boolean).map(String),
      ...calendars.flatMap(calendar => calendar.lanes.map(lane => String(lane.resource_id || '')).filter(Boolean))
    ])).sort((a, b) => a.localeCompare(b));
    const vehicleRows = vehicleIds.map(vehicleId => {
      const vehicle = vehicles.find(item => String(item.id || item.vehicle_id || item.plate_no || '') === vehicleId) || {};
      const dayCells = days.map((day, index) => {
        const lane = calendars[index].lanes.find(item => String(item.resource_id || '') === vehicleId);
        const items = lane ? lane.items : [];
        const lastTrip = items.slice().sort((a, b) => b.end - a.end)[0] || null;
        const maintenanceDate = String(vehicle.maintenance_date || vehicle.next_maintenance_date || '').slice(0, 10);
        const hasMaintenance = !items.length && maintenanceDate === day.iso_date;
        const status = hasMaintenance ? 'maintenance' : !items.length ? 'available' : (lane.load_level === 'overlap' ? 'conflict' : 'busy');
        return {
          date: day.key,
          iso_date: day.iso_date,
          label: day.label,
          status,
          trip_count: items.length,
          trip_ids: items.map(item => item.id),
          next_available_label: lastTrip ? lastTrip.end_label : 'Rảnh cả ngày',
          return_distance_km: items.reduce((sum, item) => sum + numberValue((item.return_distance_label || '').match(/[\d.]+/)?.[0]), 0),
          load_level: lane ? lane.load_level : 'available',
          maintenance_label: hasMaintenance ? 'Bảo dưỡng định kỳ' : '',
          items
        };
      });
      const latestBusyDay = dayCells.slice().reverse().find(day => day.trip_count > 0);
      return {
        vehicle_id: vehicleId,
        label: vehicleId,
        brand_label: vehicle.brand || vehicle.model || vehicle.type || '',
        status_label: statusLabel(vehicle.status || 'available'),
        days: dayCells,
        busy_days: dayCells.filter(day => day.trip_count > 0).length,
        conflict_days: dayCells.filter(day => day.status === 'conflict').length,
        next_available_label: latestBusyDay ? `${latestBusyDay.label} ${latestBusyDay.next_available_label}` : 'Rảnh trong tuần',
        guidance: latestBusyDay
          ? `Xe có lịch đến ${latestBusyDay.next_available_label}; kiểm tra quãng đường quay đầu trước khi xếp đơn kế tiếp.`
          : 'Xe rảnh trong tuần, có thể ưu tiên nhận đơn mới.'
      };
    });
    const availableByDay = days.map(day => ({
      key: day.key,
      label: day.label,
      vehicles: vehicleRows
        .filter(row => (row.days.find(cell => cell.date === day.key) || {}).status === 'available')
        .map(row => ({
          vehicle_id: row.vehicle_id,
          label: row.label,
          brand_label: row.brand_label,
          status_label: row.status_label,
          next_available_label: row.next_available_label
        }))
    }));
    return {
      days: days.map(({ key, iso_date, label }) => ({ key, iso_date, label })),
      vehicle_rows: vehicleRows,
      available_by_day: availableByDay,
      kpis: {
        vehicles_with_plan: { label: 'Xe có lịch tuần', count: vehicleRows.filter(row => row.busy_days > 0).length },
        return_planned: { label: 'Ngày có lượt quay đầu', count: vehicleRows.reduce((sum, row) => sum + row.days.filter(day => day.return_distance_km > 0).length, 0) },
        conflict_days: { label: 'Ngày trùng lịch', count: vehicleRows.reduce((sum, row) => sum + row.conflict_days, 0) },
        available_vehicles: { label: 'Xe rảnh cả tuần', count: vehicleRows.filter(row => row.busy_days === 0).length }
      },
      guidance: [
        'Xem theo tuần để biết xe nào rảnh lại sau lượt quay đầu.',
        'Nếu block ngày bị trùng lịch, xử lý ở Dispatch Calendar trước khi xuất bến.',
        'Các ngày rảnh là nguồn lực ưu tiên để ghép DO mới hoặc backhaul chiều về.'
      ]
    };
  }

  function buildVehicleSchedule(state, vehicleId, startDay = new Date()) {
    const targetId = String(vehicleId || '');
    const week = buildDispatchWeekPlanner(state, startDay);
    const row = (week.vehicle_rows || []).find(item => String(item.vehicle_id || '') === targetId);
    if (row) return { ...row, days: row.days || [], range: week.days || [] };
    const vehicle = list(state, 'vehicles').find(item => String(item.id || item.vehicle_id || item.plate_no || '') === targetId) || {};
    return {
      vehicle_id: targetId,
      label: targetId,
      brand_label: vehicle.brand || vehicle.model || vehicle.type || '',
      status_label: statusLabel(vehicle.status || 'available'),
      days: week.days.map(day => ({
        date: day.key, iso_date: day.iso_date, label: day.label,
        status: 'available', trip_count: 0, trip_ids: [], items: [],
        next_available_label: 'Rảnh cả ngày', return_distance_km: 0,
        load_level: 'available', maintenance_label: ''
      })),
      busy_days: 0, conflict_days: 0, next_available_label: 'Rảnh trong tuần',
      guidance: 'Xe rảnh trong tuần, có thể ưu tiên nhận đơn mới.',
      range: week.days || []
    };
  }

  function buildDispatchDayFleet(week, isoDate, filters = {}) {
    const rows = (week && Array.isArray(week.vehicle_rows) ? week.vehicle_rows : []).map(vehicle => {
      const day = (vehicle.days || []).find(item => String(item.iso_date || '') === String(isoDate || '')) || {
        status: 'available', trip_ids: [], items: []
      };
      const status = day.status || 'available';
      const tripIds = Array.isArray(day.trip_ids) ? day.trip_ids : [];
      const labels = {
        available: 'Rảnh trong ngày',
        busy: tripIds.length ? `Bận: Trip ${tripIds.join(', ')}` : 'Xe đang bận',
        maintenance: day.maintenance_label || 'Đang sửa chữa / bảo dưỡng',
        conflict: tripIds.length ? `Trùng lịch: ${tripIds.join(', ')}` : 'Xe đang trùng lịch'
      };
      return {
        vehicle_id: vehicle.vehicle_id,
        label: vehicle.label || vehicle.vehicle_id,
        brand_label: vehicle.brand_label || '',
        status,
        status_label: status === 'available' ? 'Rảnh' : status === 'busy' ? 'Bận' : status === 'maintenance' ? 'Sửa chữa' : 'Xung đột',
        trip_ids: tripIds,
        items: day.items || [],
        can_assign: status === 'available',
        availability_label: labels[status] || labels.busy,
        next_available_label: day.next_available_label || vehicle.next_available_label || ''
      };
    });
    const summary = rows.reduce((result, row) => {
      result.total += 1;
      if (Object.prototype.hasOwnProperty.call(result, row.status)) result[row.status] += 1;
      return result;
    }, { total: 0, available: 0, busy: 0, maintenance: 0, conflict: 0 });
    const query = normalized(filters.query || '');
    const statusFilter = normalized(filters.status || '');
    const filtered = rows.filter(row => {
      if (statusFilter && normalized(row.status) !== statusFilter) return false;
      if (!query) return true;
      return normalized(`${row.vehicle_id} ${row.label} ${row.brand_label} ${row.trip_ids.join(' ')}`).includes(query);
    });
    const pageSize = Math.min(100, Math.max(10, Number(filters.page_size) || 50));
    const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
    const page = Math.min(totalPages, Math.max(1, Number(filters.page) || 1));
    const offset = (page - 1) * pageSize;
    return {
      iso_date: isoDate,
      summary,
      filtered_count: filtered.length,
      page,
      page_size: pageSize,
      total_pages: totalPages,
      rows: filtered.slice(offset, offset + pageSize)
    };
  }

  function buildDispatchSuggestedActions(selected, alerts, navigation) {
    const actions = [];
    const hasOverlap = (alerts || []).some(alert => alert && alert.code === 'RESOURCE_OVERLAP');
    const hasConflict = (alerts || []).some(alert => alert && alert.code === 'SCHEDULE_CONFLICT');
    const dispatchNavigation = { view: 'dispatch', label: 'Mở Dispatch' };
    const trackingNavigation = { view: 'tracking', label: 'Mở GPS/POD' };
    const pushAction = (action) => {
      if (!action || !action.code || actions.some(item => item.code === action.code)) return;
      actions.push(action);
    };

    if (!selected) {
      pushAction({
        code: 'OPEN_DISPATCH',
        label: 'Mở Dispatch',
        description: 'Chọn hoặc tạo lịch điều phối cho chuyến.',
        severity: 'info',
        navigation: dispatchNavigation
      });
      return actions;
    }

    if (hasOverlap || hasConflict || !selected.vehicle_id) {
      pushAction({
        code: 'CHANGE_VEHICLE',
        label: 'Đổi xe',
        description: hasOverlap
          ? 'Xe đang bị trùng lịch, nên chọn xe rảnh trước khi xuất bến.'
          : 'Chuyến chưa đủ xe, vào Dispatch để phân xe phù hợp.',
        severity: hasOverlap ? 'critical' : 'warning',
        navigation: dispatchNavigation
      });
    }

    if (hasOverlap || hasConflict || !selected.driver_id) {
      pushAction({
        code: 'CHANGE_DRIVER',
        label: 'Đổi tài xế',
        description: hasOverlap
          ? 'Tài xế/xe có nguy cơ trùng ca, nên kiểm tra lại phân bổ.'
          : 'Chuyến chưa đủ tài xế, vào Dispatch để phân công.',
        severity: hasOverlap ? 'critical' : 'warning',
        navigation: dispatchNavigation
      });
    }

    if (navigation && navigation.view === 'tracking') {
      pushAction({
        code: 'OPEN_GPS_POD',
        label: 'Mở GPS/POD',
        description: 'Theo dõi vị trí, cập nhật sự kiện và bằng chứng giao hàng.',
        severity: 'info',
        navigation: trackingNavigation
      });
    }

    pushAction({
      code: 'OPEN_SHIPMENT_360',
      label: 'Mở Shipment 360°',
      description: 'Xem hồ sơ chuyến tổng hợp: timeline A-Z, GPS/POD, dispatch, cost/AP và cảnh báo còn thiếu.',
      severity: 'info',
      navigation: { view: 'overview', label: 'Mở Shipment 360°' }
    });

    pushAction({
      code: 'OPEN_DISPATCH',
      label: 'Mở Dispatch',
      description: 'Xem chi tiết điều phối, trạng thái xe/tài xế và lịch vận hành.',
      severity: 'info',
      navigation: dispatchNavigation
    });

    return actions;
  }

  function buildDispatchCalendarDetail(state, orderId, day = new Date()) {
    const calendar = buildDispatchCalendar(state, day, {});
    const targetId = String(orderId || '');
    const emptyDetail = {
      kind: null,
      id: '',
      order: null,
      linked_delivery_orders: [],
      total_payload_kg: 0,
      related_lane: { resource_id: '', label: 'Chưa có lane', items: [] },
      alerts: [],
      suggested_actions: [],
      next_action: {
        label: 'Mở Dispatch',
        navigation: { view: 'dispatch', label: 'Mở Dispatch' }
      },
      message: 'Chưa chọn chuyến trên Gantt. Bấm một thanh lịch để xem chi tiết.'
    };
    if (!targetId) return emptyDetail;

    const lane = calendar.lanes.find(item => item.items.some(order => String(order.id) === targetId)) || null;
    const order = lane ? lane.items.find(item => String(item.id) === targetId) : null;
    const unscheduled = !order ? calendar.unscheduled.find(item => String(item.id) === targetId) : null;
    const selected = order || unscheduled || null;
    if (!selected) return emptyDetail;

    const kind = selected.kind === 'trip' ? 'trip' : 'delivery_order';
    const deliveryOrders = list(state, 'delivery_orders');
    const trip = kind === 'trip'
      ? list(state, 'transport_trips').find(item => String(item.id || '') === targetId) || null
      : null;
    const linkedIds = kind === 'trip'
      ? (Array.isArray(trip && trip.delivery_order_ids)
          ? trip.delivery_order_ids
          : (Array.isArray(selected.delivery_order_ids) ? selected.delivery_order_ids : []))
      : [targetId];
    const linkedDeliveryOrders = linkedIds
      .map(id => deliveryOrders.find(item => String(item.id || '') === String(id)))
      .filter(Boolean);
    const totalPayloadKg = linkedDeliveryOrders.reduce((sum, deliveryOrder) => sum + numberValue(
      deliveryOrder.weight_kg
      || deliveryOrder.payload_kg
      || deliveryOrder.total_weight_kg
      || deliveryOrder.gross_weight_kg
    ), 0);
    const selectedCompliance = selected && Array.isArray(selected.compliance_alerts) ? selected.compliance_alerts : [];
    const alerts = [
      ...selectedCompliance,
      ...calendar.capacity_alerts.filter(alert => lane && String(alert.resource_id) === String(lane.resource_id)),
      ...calendar.conflicts.filter(alert => (alert.order_ids || []).map(String).includes(targetId))
    ].filter((alert, index, rows) => rows.findIndex(item => item.code === alert.code && item.message === alert.message) === index);
    const navigation = selected.navigation || { view: 'dispatch', label: 'Mở Dispatch' };
    return {
      kind,
      id: targetId,
      order: selected,
      linked_delivery_orders: linkedDeliveryOrders,
      total_payload_kg: totalPayloadKg,
      related_lane: lane || { resource_id: '', label: 'Chưa có lane', items: [] },
      alerts,
      suggested_actions: buildDispatchSuggestedActions(selected, alerts, navigation),
      next_action: {
        label: navigation.view === 'tracking' ? 'Mở GPS/POD' : 'Mở Dispatch',
        navigation
      },
      message: `Đang xem chi tiết lịch điều phối của ${selected.id}.`
    };
  }

  function resourceWindow(order) {
    const start = parseTime(order && (order.pickup_date || order.planned_pickup_at || order.dispatch_date));
    const end = parseTime(order && (order.delivery_date || order.planned_delivery_at || order.eta));
    return start && end && end > start ? { start, end } : null;
  }

  function isReadyResource(resource) {
    const status = normalized(resource && (resource.status || (resource.is_active === false ? 'inactive' : 'available')));
    return !['inactive', 'disabled', 'closed', 'deleted', 'false', 'maintenance', 'bao_tri', 'bảo_trì'].includes(status);
  }

  function hasResourceOverlap(orders, targetOrder, resourceField, resourceId) {
    const targetWindow = resourceWindow(targetOrder);
    if (!targetWindow || !resourceId) return false;
    return orders.some(order => {
      if (!order || String(order.id || '') === String(targetOrder.id || '')) return false;
      const assignedId = order[resourceField] || (resourceField === 'vehicle_id' ? order.vehicle || order.truck_id : order.driver || order.main_driver_id);
      if (String(assignedId || '') !== String(resourceId || '')) return false;
      const window = resourceWindow(order);
      if (!window) return false;
      return window.start < targetWindow.end && window.end > targetWindow.start;
    });
  }

  function buildDispatchResourceOptions(state, orderId, day = new Date()) {
    const orders = list(state, 'delivery_orders');
    const order = orders.find(item => String(item.id || '') === String(orderId || '')) || null;
    const targetWindow = resourceWindow(order);
    const currentVehicle = order && (order.vehicle_id || order.vehicle || order.truck_id) || '';
    const currentDriver = order && (order.driver_id || order.driver || order.main_driver_id) || '';
    const buildOptions = (rows, type, currentId) => rows.map(row => {
      const id = row.id || row.code || row.plate_no || row.license_plate || row.name || '';
      const active = isReadyResource(row);
      const conflict = hasResourceOverlap(orders, order || {}, type === 'vehicle' ? 'vehicle_id' : 'driver_id', id);
      const availability = String(id) === String(currentId)
        ? (conflict ? 'conflict' : 'current')
        : (!active ? 'inactive' : (conflict ? 'conflict' : 'available'));
      return {
        id,
        label: `${id}${row.name ? ` - ${row.name}` : row.brand ? ` - ${row.brand}` : ''}`,
        status: row.status || '',
        availability,
        selectable: availability === 'available' || availability === 'current',
        message: availability === 'available'
          ? 'Có thể phân công cho chuyến này.'
          : availability === 'current'
            ? 'Đang là tài nguyên hiện tại của chuyến.'
            : availability === 'conflict'
              ? 'Đang trùng lịch với chuyến khác trong cùng khung giờ.'
              : 'Tài nguyên chưa sẵn sàng hoạt động.'
      };
    }).filter(item => item.id).sort((a, b) => {
      const rank = { available: 0, current: 1, conflict: 2, inactive: 3 };
      return (rank[a.availability] ?? 9) - (rank[b.availability] ?? 9) || String(a.id).localeCompare(String(b.id));
    });
    const vehicles = buildOptions(list(state, 'vehicles'), 'vehicle', currentVehicle);
    const drivers = buildOptions(list(state, 'drivers'), 'driver', currentDriver);
    return {
      order,
      day: shortDate(day),
      has_time_window: Boolean(targetWindow),
      current_vehicle_id: currentVehicle,
      current_driver_id: currentDriver,
      recommended_vehicle_id: (vehicles.find(item => item.availability === 'available') || vehicles.find(item => item.availability === 'current') || {}).id || '',
      recommended_driver_id: (drivers.find(item => item.availability === 'available') || drivers.find(item => item.availability === 'current') || {}).id || '',
      vehicles,
      drivers,
      message: order
        ? `Chọn xe/tài xế rảnh cho ${order.id}; hệ thống sẽ cảnh báo nếu tài nguyên bị trùng lịch.`
        : 'Chưa chọn DO để đổi xe/tài xế.'
    };
  }

  function eventsForOrder(state, order) {
    return list(state, 'transport_events').filter(event => {
      const orderId = String(order && order.id || '');
      const freightOrderId = String(order && (order.freight_order_id || order.fo_id) || '');
      return String(event.delivery_order_id || event.do_id || '') === orderId
        || (freightOrderId && String(event.freight_order_id || '') === freightOrderId);
    });
  }

  function hasEventType(events, types) {
    const expected = new Set(types.map(normalized));
    return events.some(event => expected.has(normalized(event.event_type)));
  }

  function gpsEventMeta(eventType) {
    const key = normalized(eventType);
    const meta = {
      check_in: { label: 'Check-in điểm lấy/giao', icon: 'fa-clipboard-check', severity: 'info' },
      pickup: { label: 'Pickup / Lấy hàng', icon: 'fa-box', severity: 'done' },
      departure: { label: 'Departure / Xuất phát', icon: 'fa-truck-fast', severity: 'done' },
      route_deviation: { label: 'Lệch tuyến', icon: 'fa-triangle-exclamation', severity: 'warning' },
      delay: { label: 'Chậm tiến độ', icon: 'fa-clock', severity: 'warning' },
      arrival: { label: 'Arrival / Đến nơi', icon: 'fa-location-dot', severity: 'done' },
      unloading: { label: 'Unloading / Dỡ hàng', icon: 'fa-dolly', severity: 'done' },
      delivered: { label: 'Delivered / Đã giao', icon: 'fa-circle-check', severity: 'done' },
      incident: { label: 'Sự cố vận hành', icon: 'fa-triangle-exclamation', severity: 'critical' }
    };
    return { event_type: key, ...(meta[key] || { label: statusLabel(eventType), icon: 'fa-circle-dot', severity: 'info' }) };
  }

  function buildGpsEventTimeline(state, deliveryOrderId) {
    const order = firstById(list(state, 'delivery_orders'), deliveryOrderId) || { id: deliveryOrderId };
    const podRecords = podsForOrder(state, order.id);
    const pod = podRecords[0] || null;
    const tracking = firstById(list(state, 'vehicle_tracking'), order.id, ['do_id', 'delivery_order_id', 'id']);
    const rawEvents = eventsForOrder(state, order)
      .slice()
      .sort((a, b) => String(a.event_time || a.recorded_at || '').localeCompare(String(b.event_time || b.recorded_at || '')));
    const events = rawEvents.map((event, index) => {
      const meta = gpsEventMeta(event.event_type);
      const source = normalized(event.source || event.source_type);
      return {
        id: event.id || `${order.id || 'DO'}-${index + 1}`,
        event_type: meta.event_type,
        label: meta.label,
        icon: meta.icon,
        severity: meta.severity,
        sequence_status: ['warning', 'critical'].includes(meta.severity) ? meta.severity : 'done',
        event_time: event.event_time || event.recorded_at || '',
        time_label: event.event_time || event.recorded_at ? new Date(event.event_time || event.recorded_at).toLocaleString('vi-VN') : 'Chưa có thời gian',
        source_label: source === 'device' ? 'Thiết bị GPS' : source === 'manual' ? 'Thủ công' : 'Không rõ nguồn',
        location_text: event.location_text || event.location || 'Chưa có vị trí',
        lat: event.lat,
        lng: event.lng,
        speed_kmh: event.speed_kmh,
        note: event.reason || event.note || event.description || ''
      };
    });
    const status = normalized(order.status || order.canonical_status);
    const podDone = Boolean(pod);
    const alerts = [];
    if (!events.length) {
      alerts.push({
        code: 'EVENTS_MISSING',
        severity: 'warning',
        message: `Chưa có event GPS/POD cho ${order.id || deliveryOrderId}. Vào GPS/POD để ghi nhận check-in, pickup hoặc departure.`
      });
    }
    if (!podDone && ['delivered', 'completed'].includes(status)) {
      alerts.push({
        code: 'POD_MISSING',
        severity: 'critical',
        message: `Đơn ${order.id || deliveryOrderId} đã giao nhưng chưa có POD.`
      });
    } else if (!podDone) {
      alerts.push({
        code: 'POD_MISSING',
        severity: 'warning',
        message: `Đơn ${order.id || deliveryOrderId} chưa có POD/ký nhận.`
      });
    }
    const latest = events[events.length - 1] || null;
    return {
      order_id: order.id || deliveryOrderId || '',
      vehicle_id: order.vehicle_id || (tracking && tracking.vehicle_id) || '',
      kpis: {
        events: { label: 'Event GPS/POD', count: events.length },
        latest: { label: 'Event mới nhất', value: latest ? latest.label : 'Chưa có event' },
        pod: { label: 'POD', status: podDone ? 'done' : 'missing', value: podDone ? 'Đã có POD' : 'Thiếu POD' },
        source_device: { label: 'Event từ thiết bị', count: events.filter(event => event.source_label === 'Thiết bị GPS').length }
      },
      events,
      alerts,
      pod: pod || null,
      pod_records: podRecords,
      tracking: tracking || null,
      next_action: podDone
        ? { label: 'Mở báo cáo/KPI', navigation: { view: 'reporting' } }
        : { label: 'Cập nhật Arrival/POD', navigation: { view: 'tracking' } }
    };
  }

  function minutesBetween(later, earlier) {
    if (!later || !earlier) return 0;
    return Math.round((later.getTime() - earlier.getTime()) / 60000);
  }

  function buildSlaKpiDrilldown(state, now = new Date()) {
    const deliveryOrders = list(state, 'delivery_orders');
    const pods = list(state, 'pods');
    const podSet = new Set(pods.map(pod => String(pod.do_id || pod.delivery_order_id || pod.id || '')));
    const worklist = [];
    const orderContext = (orderId) => {
      const order = firstById(deliveryOrders, orderId);
      const route = firstById(list(state, 'routes'), order && (order.route_id || order.route), ['id', 'name']);
      return { order, route };
    };
    const issueActions = (issue) => {
      const actions = [{
        code: 'OPEN_ORDER_TIMELINE',
        label: 'Mở timeline đơn',
        description: 'Xem toàn bộ luồng QT → SO → DO → Dispatch → GPS/POD → Finance của đơn này.',
        navigation: { view: 'overview', label: 'Timeline A-Z' }
      }];
      if (issue.category_code === 'LATE_PICKUP') actions.push({
        code: 'OPEN_DISPATCH',
        label: 'Mở Dispatch',
        description: 'Kiểm tra xe, tài xế, khung giờ và xung đột lịch điều phối.',
        navigation: { view: 'dispatch', label: 'Dispatch Calendar' }
      });
      if (['LATE_DELIVERY', 'ETA_VARIANCE', 'MISSING_POD', 'ON_TIME_VARIANCE'].includes(issue.category_code)) actions.push({
        code: 'OPEN_GPS_POD',
        label: 'Mở GPS/POD',
        description: 'Kiểm tra vị trí, event Arrival/Delivered và chứng từ POD.',
        navigation: { view: 'tracking', label: 'GPS/POD' }
      });
      if (issue.category_code === 'COST_OVERRUN') actions.push({
        code: 'OPEN_FINANCE_COCKPIT',
        label: 'Mở Finance',
        description: 'Kiểm tra Actual Cost, AP Invoice và đối soát chi phí.',
        navigation: { view: 'accounting', label: 'Finance Cockpit' }
      });
      return actions;
    };
    const rootCauseFor = (issue) => ({
      LATE_PICKUP: 'Chưa có event check-in/pickup/departure; cần kiểm tra Dispatch Calendar và tài nguyên xe/tài xế.',
      LATE_DELIVERY: 'GPS/POD chưa ghi nhận Arrival/Delivered dù đã quá kế hoạch giao; cần kiểm tra vị trí và cập nhật sự kiện.',
      ETA_VARIANCE: 'ETA đang muộn hơn kế hoạch; cần kiểm tra vị trí GPS, điều kiện tuyến và cảnh báo lệch tuyến.',
      MISSING_POD: 'Đơn đã giao xong nhưng thiếu chứng từ POD; cần tài xế/điều phối tải biên bản ký nhận.',
      ON_TIME_VARIANCE: 'Thực tế giao muộn hơn kế hoạch; cần ghi nhận nguyên nhân SLA để báo cáo khách hàng.',
      COST_OVERRUN: 'Actual Cost vượt kế hoạch; cần Finance kiểm tra khoản phát sinh trước khi post AP.'
    }[issue.category_code] || 'Cần kiểm tra chi tiết trong Control Tower.');

    const addIssue = (issue) => {
      const context = orderContext(issue.order_id);
      const order = context.order || {};
      worklist.push({
        id: `${issue.category_code}:${issue.order_id || issue.title || worklist.length}`,
        severity: issue.severity || 'warning',
        category_code: issue.category_code,
        title: issue.title,
        description: issue.description,
        order_id: issue.order_id || null,
        vehicle_id: order.vehicle_id || order.vehicle || order.truck_id || '',
        driver_id: order.driver_id || order.driver || order.main_driver_id || '',
        route_id: order.route_id || order.route || '',
        route_label: (context.route && (context.route.name || context.route.route_name || context.route.id)) || order.route_name || order.route || 'Chưa rõ tuyến',
        root_cause: rootCauseFor(issue),
        owner: issue.owner || 'Điều phối',
        action_label: issue.action_label || `Mở ${issue.navigation && issue.navigation.label || 'màn xử lý'}`,
        navigation: issue.navigation || { view: 'overview', label: 'Tổng quan' },
        actions: issueActions(issue),
        metric: issue.metric || ''
      });
    };

    deliveryOrders.forEach(order => {
      const status = normalized(order.status || order.canonical_status);
      const terminal = ['delivered', 'completed', 'cancelled', 'reversed'].includes(status);
      const events = eventsForOrder(state, order);
      const plannedPickup = parseTime(order.planned_pickup_at || order.pickup_window_end || order.pickup_date);
      const plannedDelivery = parseTime(order.planned_delivery_at || order.delivery_window_end || order.delivery_date);
      const eta = parseTime(order.eta || order.estimated_arrival_at);
      const actualDelivery = parseTime(order.actual_delivery_at || order.delivered_at)
        || (events.filter(event => ['delivered', 'arrival'].includes(normalized(event.event_type))).map(event => parseTime(event.event_time)).filter(Boolean).sort((a, b) => b - a)[0] || null);

      if (!terminal && plannedPickup && plannedPickup < now && !hasEventType(events, ['check_in', 'pickup', 'departure'])) {
        addIssue({
          severity: 'critical',
          category_code: 'LATE_PICKUP',
          order_id: order.id,
          title: `Trễ lấy hàng: ${order.id}`,
          description: 'Đơn đã quá khung giờ lấy hàng nhưng chưa có event check-in/pickup/departure.',
          metric: `${minutesBetween(now, plannedPickup)} phút trễ`,
          navigation: { view: 'dispatch', label: 'Dispatch Calendar' },
          action_label: 'Mở Dispatch'
        });
      }

      if (!terminal && plannedDelivery && plannedDelivery < now && !hasEventType(events, ['arrival', 'unloading', 'delivered'])) {
        addIssue({
          severity: 'critical',
          category_code: 'LATE_DELIVERY',
          order_id: order.id,
          title: `Trễ giao hàng: ${order.id}`,
          description: 'Đơn đã quá ETA/kế hoạch giao nhưng chưa có event đến nơi hoặc POD.',
          metric: `${minutesBetween(now, plannedDelivery)} phút trễ`,
          navigation: { view: 'tracking', label: 'GPS/POD' },
          action_label: 'Mở GPS/POD'
        });
      }

      if (!terminal && eta && plannedDelivery && eta > plannedDelivery) {
        addIssue({
          severity: 'warning',
          category_code: 'ETA_VARIANCE',
          order_id: order.id,
          title: `Lệch ETA: ${order.id}`,
          description: 'ETA hiện tại đang muộn hơn kế hoạch giao hàng.',
          metric: `${minutesBetween(eta, plannedDelivery)} phút lệch`,
          navigation: { view: 'tracking', label: 'GPS/POD' },
          action_label: 'Mở GPS/POD'
        });
      }

      if (['delivered', 'completed'].includes(status) && !podSet.has(String(order.id))) {
        addIssue({
          severity: 'critical',
          category_code: 'MISSING_POD',
          order_id: order.id,
          title: `Thiếu POD: ${order.id}`,
          description: 'Đơn đã giao xong nhưng chưa có chứng từ POD/ký nhận.',
          metric: 'Thiếu chứng từ',
          navigation: { view: 'tracking', label: 'GPS/POD' },
          action_label: 'Mở GPS/POD'
        });
      }

      if (actualDelivery && plannedDelivery && actualDelivery > plannedDelivery) {
        addIssue({
          severity: 'warning',
          category_code: 'ON_TIME_VARIANCE',
          order_id: order.id,
          title: `Giao trễ thực tế: ${order.id}`,
          description: 'Thời điểm giao thực tế muộn hơn kế hoạch, cần ghi nhận SLA.',
          metric: `${minutesBetween(actualDelivery, plannedDelivery)} phút trễ`,
          navigation: { view: 'reporting', label: 'Báo cáo SLA/KPI' },
          action_label: 'Mở Báo cáo'
        });
      }
    });

    list(state, 'freight_actual_costs').forEach(cost => {
      const planned = numberValue(cost.planned_amount ?? cost.estimated_amount ?? cost.budget_amount ?? cost.planned_total_amount);
      const actual = numberValue(cost.total_amount ?? cost.actual_amount ?? cost.total);
      if (planned > 0 && actual > planned) {
        const variance = Math.round((actual - planned) * 100 / planned);
        addIssue({
          severity: variance >= 20 ? 'critical' : 'warning',
          category_code: 'COST_OVERRUN',
          order_id: cost.do_id || cost.delivery_order_id || cost.freight_order_id || null,
          title: `Vượt chi phí: ${cost.id || cost.freight_order_id || 'Actual Cost'}`,
          description: 'Actual Cost đang cao hơn dự toán/kế hoạch, cần kiểm tra trước khi hạch toán AP.',
          metric: `+${variance}%`,
          owner: 'Tài chính vận tải',
          navigation: { view: 'accounting', label: 'Finance Cockpit' },
          action_label: 'Mở Tài chính'
        });
      }
    });

    const severityRank = { critical: 0, warning: 1, info: 2 };
    worklist.sort((a, b) => (severityRank[a.severity] ?? 9) - (severityRank[b.severity] ?? 9)
      || String(a.order_id || a.title).localeCompare(String(b.order_id || b.title)));

    const countBy = code => worklist.filter(item => item.category_code === code).length;
    const reasonLabels = {
      LATE_PICKUP: 'Trễ lấy hàng',
      LATE_DELIVERY: 'Trễ giao hàng',
      ETA_VARIANCE: 'Lệch ETA',
      MISSING_POD: 'Thiếu POD',
      ON_TIME_VARIANCE: 'Giao trễ thực tế',
      COST_OVERRUN: 'Vượt chi phí'
    };
    const totalIssues = worklist.length || 1;
    const reasonBreakdown = Object.entries(reasonLabels)
      .map(([code, label]) => ({
        category_code: code,
        label,
        count: countBy(code),
        percent: Math.round(countBy(code) * 100 / totalIssues),
        severity: worklist.some(item => item.category_code === code && item.severity === 'critical') ? 'critical' : 'warning'
      }))
      .filter(item => item.count > 0)
      .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
    const recommendations = [];
    if (countBy('LATE_PICKUP')) recommendations.push('Có đơn trễ lấy hàng: kiểm tra Dispatch Calendar, khung giờ lấy hàng và trạng thái check-in/pickup.');
    if (countBy('LATE_DELIVERY') || countBy('ETA_VARIANCE')) recommendations.push('Có rủi ro trễ giao/ETA: mở GPS/POD để kiểm tra vị trí, sự kiện và điều phối hỗ trợ.');
    if (countBy('MISSING_POD')) recommendations.push('Có đơn thiếu POD: yêu cầu tài xế/điều phối cập nhật chứng từ ký nhận trước khi chốt settlement.');
    if (countBy('COST_OVERRUN')) recommendations.push('Có chi phí vượt kế hoạch: tài chính vận tải cần kiểm tra Actual Cost trước khi tạo AP.');
    if (!recommendations.length) recommendations.push('SLA/KPI hiện sạch; tiếp tục theo dõi Control Tower trong quá trình demo.');
    return {
      kpis: {
        late_pickup: { label: 'Trễ lấy hàng', count: countBy('LATE_PICKUP'), target: 'dispatch' },
        late_delivery: { label: 'Trễ giao hàng', count: countBy('LATE_DELIVERY'), target: 'tracking' },
        eta_variance: { label: 'Lệch ETA', count: countBy('ETA_VARIANCE'), target: 'tracking' },
        missing_pod: { label: 'Thiếu POD', count: countBy('MISSING_POD'), target: 'tracking' },
        cost_overrun: { label: 'Vượt chi phí', count: countBy('COST_OVERRUN'), target: 'accounting' }
      },
      worklist,
      reason_breakdown: reasonBreakdown,
      recommendations
    };
  }

  function buildSlaKpiIssueDetail(state, issueId, now = new Date()) {
    const drilldown = buildSlaKpiDrilldown(state, now);
    const issue = drilldown.worklist.find(item => String(item.id || '') === String(issueId || ''))
      || drilldown.worklist[0]
      || null;
    if (!issue) {
      return {
        issue: null,
        order: null,
        timeline: [],
        next_actions: [],
        message: 'Chưa có cảnh báo SLA/KPI để phân tích.'
      };
    }
    const order = firstById(list(state, 'delivery_orders'), issue.order_id);
    return {
      issue,
      order,
      timeline: buildOrderTimeline(state, issue.order_id),
      next_actions: issue.actions || [],
      message: `${issue.title}: ${issue.root_cause}`
    };
  }

  function asPermissionList(value) {
    if (Array.isArray(value)) return value.filter(item => typeof item === 'string' && item.trim()).map(item => item.trim());
    if (typeof value !== 'string' || !value.trim()) return [];
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed.filter(item => typeof item === 'string' && item.trim()).map(item => item.trim()) : [];
    } catch (error) {
      return [];
    }
  }

  function buildRolePermissionBoard(state) {
    const financeRequired = ['finance_read', 'finance_creator', 'finance_approver', 'finance_poster', 'finance_payment'];
    const dispatchRequired = ['dispatch_update', 'tracking_update'];
    const permissionModules = [
      { key: 'finance', label: 'Tài chính', permissions: financeRequired },
      { key: 'dispatch', label: 'Điều phối', permissions: dispatchRequired },
      { key: 'tracking', label: 'GPS/POD', permissions: ['tracking_update'] },
      { key: 'reporting', label: 'Báo cáo', permissions: ['finance_read', 'dispatch_update'] }
    ];
    const roles = list(state, 'roles').map(role => {
      const permissions = asPermissionList(role.permissions);
      const missingFinance = financeRequired.filter(permission => !permissions.includes(permission));
      const missingDispatch = dispatchRequired.filter(permission => !permissions.includes(permission));
      const coverageLabel = missingFinance.length === 0
        ? 'Đủ quyền tài chính'
        : missingFinance.length < financeRequired.length
          ? 'Thiếu một phần quyền tài chính'
          : 'Chưa có quyền tài chính';
      return {
        id: role.id || role.name || 'ROLE',
        permissions,
        permission_count: permissions.length,
        missing_permissions: missingFinance,
        missing_dispatch_permissions: missingDispatch,
        coverage_label: coverageLabel,
        status: permissions.length ? 'configured' : 'missing'
      };
    });
    const roleById = roles.reduce((acc, role) => {
      acc[String(role.id)] = role;
      return acc;
    }, {});
    const users = list(state, 'users').map(user => {
      const role = roleById[String(user.role_id || '')] || null;
      return {
        id: user.id || user.username || 'USER',
        username: user.username || user.id || 'Người dùng',
        role_id: user.role_id || '',
        role_label: role ? role.id : 'Chưa gán vai trò',
        permission_count: role ? role.permission_count : 0,
        status: role ? 'configured' : 'missing'
      };
    });
    const financeCovered = roles.filter(role => role.missing_permissions.length === 0);
    const usersWithoutRole = users.filter(user => user.status === 'missing');
    const rolesWithoutPermissions = roles.filter(role => role.permission_count === 0);
    const warnings = [
      ...usersWithoutRole.map(user => ({
        code: 'USER_ROLE_MISSING',
        target: 'master-data/users',
        message: `${user.username} chưa được gán vai trò. Vào Master Data → Người dùng & Vai trò để cấu hình.`
      })),
      ...rolesWithoutPermissions.map(role => ({
        code: 'ROLE_PERMISSION_MISSING',
        target: 'master-data/roles',
        message: `Vai trò ${role.id} chưa có quyền. Vào Master Data → Vai trò để bổ sung permission.`
      })),
      ...roles.filter(role => role.missing_permissions.length > 0 && role.permission_count > 0).map(role => ({
        code: 'FINANCE_PERMISSION_INCOMPLETE',
        target: 'master-data/roles',
        message: `Vai trò ${role.id} thiếu: ${role.missing_permissions.join(', ')}.`
      }))
    ];
    const matrixRows = roles.map(role => {
      const moduleCells = permissionModules.reduce((acc, module) => {
        const missing = module.permissions.filter(permission => !role.permissions.includes(permission));
        const granted = module.permissions.filter(permission => role.permissions.includes(permission));
        acc[module.key] = {
          status: missing.length === 0 ? 'complete' : granted.length ? 'partial' : 'missing',
          granted,
          missing,
          coverage_percent: module.permissions.length ? Math.round(granted.length * 100 / module.permissions.length) : 0
        };
        return acc;
      }, {});
      return {
        role_id: role.id,
        permission_count: role.permission_count,
        modules: moduleCells
      };
    });

    return {
      kpis: {
        roles: { label: 'Vai trò', count: roles.length },
        users: { label: 'Người dùng', count: users.length },
        finance_coverage: { label: 'Role đủ quyền tài chính', count: financeCovered.length },
        warnings: { label: 'Cảnh báo phân quyền', count: warnings.length }
      },
      roles,
      users,
      permission_matrix: {
        modules: permissionModules.map(module => ({ key: module.key, label: module.label, permissions: module.permissions })),
        rows: matrixRows
      },
      audit_recent: list(state, 'audit_logs').slice(0, 8).map(log => ({
        id: log.id,
        user_id: log.user_id || 'system',
        action: log.action || 'UNKNOWN',
        table_name: log.table_name || '',
        record_id: log.record_id || '',
        created_at: log.created_at || log.timestamp || ''
      })),
      warnings
    };
  }

  function buildRoleAdminWorkbench(state) {
    const board = buildRolePermissionBoard(state);
    const roleTemplates = [
      {
        id: 'FINANCE_CONTROLLER',
        label: 'Tài chính vận tải',
        description: 'Duyệt Actual Cost, tạo/post AP, thanh toán và xem báo cáo tài chính.',
        permissions: ['finance_read', 'finance_creator', 'finance_approver', 'finance_poster', 'finance_payment']
      },
      {
        id: 'DISPATCH_CONTROLLER',
        label: 'Điều phối vận tải',
        description: 'Điều phối xe/tài xế, cập nhật dispatch và theo dõi GPS/POD.',
        permissions: ['dispatch_update', 'tracking_update']
      },
      {
        id: 'CONTROL_TOWER_VIEWER',
        label: 'Control Tower Viewer',
        description: 'Xem dashboard, SLA/KPI, audit và các cảnh báo vận hành.',
        permissions: ['finance_read']
      },
      {
        id: 'TMS_ADMIN',
        label: 'Quản trị TMS',
        description: 'Cấu hình Master Data, role/permission và kiểm soát luồng A-Z.',
        permissions: ['finance_read', 'finance_creator', 'finance_approver', 'finance_poster', 'finance_payment', 'dispatch_update', 'tracking_update']
      }
    ];
    const usersMissingRole = board.users.filter(user => user.status === 'missing').map(user => ({
      code: 'ASSIGN_USER_ROLE',
      user_id: user.id,
      title: `Gán vai trò cho ${user.username}`,
      description: 'Người dùng chưa có role nên sẽ không đủ quyền thao tác trong demo.',
      severity: 'critical',
      action_label: 'Mở tab Người dùng',
      navigation: { view: 'master-data', target: 'md-tab-users' }
    }));
    const rolesMissingPermissions = board.roles
      .filter(role => role.missing_permissions.length || role.permission_count === 0)
      .map(role => {
        const missing = [...new Set(role.missing_permissions)];
        return {
          code: 'COMPLETE_ROLE_PERMISSIONS',
          role_id: role.id,
          title: `Bổ sung quyền cho ${role.id}`,
          description: missing.length
            ? `Role đang thiếu: ${missing.join(', ')}.`
            : 'Role chưa có permission, cần cấu hình trước khi giao cho user.',
          severity: role.permission_count ? 'warning' : 'critical',
          missing_permissions: missing,
          action_label: 'Mở tab Vai trò',
          navigation: { view: 'master-data', target: 'md-tab-roles' }
        };
      });
    const worklist = [...usersMissingRole, ...rolesMissingPermissions];
    const permissionActions = [
      {
        code: 'COPY_TEMPLATE',
        label: 'Sao chép template role',
        description: 'Chọn template phù hợp rồi tạo role trong Master Data → Người dùng & Vai trò.',
        navigation: { view: 'master-data', target: 'md-tab-roles' }
      },
      {
        code: 'ASSIGN_ROLE',
        label: 'Gán role cho user',
        description: 'Gán người demo vào đúng role để tránh lỗi thiếu quyền khi thao tác.',
        navigation: { view: 'master-data', target: 'md-tab-users' }
      },
      {
        code: 'REVIEW_AUDIT',
        label: 'Kiểm tra audit gần nhất',
        description: 'Đối chiếu actor/action để bảo đảm luồng duyệt không bị nhầm người.',
        navigation: { view: 'overview', target: 'role-permission-board-panel' }
      }
    ];
    const missingCount = worklist.filter(item => item.severity === 'critical').length;
    return {
      kpis: {
        templates: { label: 'Template role chuẩn', count: roleTemplates.length },
        actions_required: { label: 'Việc cần cấu hình', count: worklist.length },
        users_missing_role: { label: 'User thiếu role', count: usersMissingRole.length },
        critical_gaps: { label: 'Lỗ hổng quyền nghiêm trọng', count: missingCount }
      },
      role_templates: roleTemplates,
      worklist,
      permission_actions: permissionActions,
      guidance: [
        'Nên phân quyền theo vai trò nghiệp vụ: điều phối, tài chính, quản trị và người xem Control Tower.',
        'Không gán quyền duyệt và quyền thanh toán cho cùng một người nếu công ty yêu cầu tách nhiệm vụ.',
        'Nếu thiếu quyền, user vào Master Data → Người dùng & Vai trò để cấu hình trước khi chạy demo.'
      ]
    };
  }

  function groupOrderPerformance(state, drilldown, keyGetter) {
    const buckets = {};
    list(state, 'delivery_orders').forEach(order => {
      const key = keyGetter(order) || 'Chưa phân loại';
      buckets[key] = buckets[key] || { label: key, total_orders: 0, issue_count: 0, on_time_orders: 0 };
      buckets[key].total_orders += 1;
    });
    drilldown.worklist.forEach(issue => {
      const order = list(state, 'delivery_orders').find(item => String(item.id || '') === String(issue.order_id || ''));
      const key = keyGetter(order || {}) || issue.order_id || 'Chưa phân loại';
      buckets[key] = buckets[key] || { label: key, total_orders: 0, issue_count: 0, on_time_orders: 0 };
      buckets[key].issue_count += 1;
    });
    Object.values(buckets).forEach(row => {
      row.on_time_orders = Math.max(0, row.total_orders - row.issue_count);
      row.risk_level = row.issue_count ? (row.issue_count >= 2 ? 'Cao' : 'Cần theo dõi') : 'Ổn';
      row.on_time_rate = row.total_orders ? Math.max(0, Math.round(row.on_time_orders * 100 / row.total_orders)) : 0;
    });
    return Object.values(buckets)
      .sort((a, b) => b.issue_count - a.issue_count || String(a.label).localeCompare(String(b.label)))
      .slice(0, 8);
  }

  function buildReportingDrilldown(state, now = new Date()) {
    const deliveryOrders = list(state, 'delivery_orders');
    const salesOrders = list(state, 'sales_orders');
    const quotations = list(state, 'quotations');
    const drilldown = buildSlaKpiDrilldown(state, now);
    const totalOrders = deliveryOrders.length;
    const lateDelivered = new Set(drilldown.worklist
      .filter(item => item.category_code === 'ON_TIME_VARIANCE')
      .map(item => String(item.order_id || '')));
    const onTimeOrders = Math.max(0, totalOrders - lateDelivered.size);
    const onTimeRate = totalOrders ? Math.round(onTimeOrders * 100 / totalOrders) : 0;
    const costOverrunCount = drilldown.worklist.filter(item => item.category_code === 'COST_OVERRUN').length;
    const criticalCount = drilldown.worklist.filter(item => item.severity === 'critical').length;

    const issueLabels = {
      LATE_PICKUP: 'Trễ lấy hàng',
      LATE_DELIVERY: 'Trễ giao hàng',
      ETA_VARIANCE: 'Lệch ETA',
      MISSING_POD: 'Thiếu POD',
      COST_OVERRUN: 'Vượt chi phí',
      ON_TIME_VARIANCE: 'Giao trễ thực tế'
    };
    const metricMinutes = item => {
      const match = String(item.metric || '').match(/-?\d+/);
      return match ? Math.abs(Number(match[0])) : 0;
    };
    const agingDefinitions = [
      { key: 'under_30', label: 'Dưới 30 phút', min: 0, max: 29 },
      { key: '30_60', label: '30–60 phút', min: 30, max: 60 },
      { key: '60_120', label: '60–120 phút', min: 61, max: 120 },
      { key: 'over_120', label: 'Trên 120 phút', min: 121, max: Infinity }
    ];
    const agingBuckets = agingDefinitions.map(bucket => ({
      key: bucket.key,
      label: bucket.label,
      count: drilldown.worklist.filter(item => {
        const minutes = metricMinutes(item);
        return minutes >= bucket.min && minutes <= bucket.max;
      }).length,
      severity: bucket.key === 'over_120' ? 'critical' : bucket.key === '60_120' ? 'warning' : 'info'
    }));
    const issueDateFor = item => {
      const order = firstById(deliveryOrders, item.order_id);
      const raw = (order && (order.planned_delivery_at || order.delivery_date || order.planned_pickup_at || order.pickup_date || order.eta || order.actual_delivery_at))
        || now;
      const parsed = parseTime(raw) || now;
      return parsed.toISOString().slice(0, 10);
    };
    const trendMap = {};
    drilldown.worklist.forEach(item => {
      const date = issueDateFor(item);
      trendMap[date] = trendMap[date] || { date, issue_count: 0, critical_count: 0, warning_count: 0 };
      trendMap[date].issue_count += 1;
      if (item.severity === 'critical') trendMap[date].critical_count += 1;
      else trendMap[date].warning_count += 1;
    });
    const trendByDay = Object.values(trendMap).sort((a, b) => a.date.localeCompare(b.date));
    const heatmapRows = (dimension, rows, target) => ({
      dimension,
      target,
      items: rows.slice(0, 5).map(row => ({
        label: row.label,
        issue_count: row.issue_count,
        total_orders: row.total_orders,
        risk_level: row.issue_count >= 2 ? 'critical' : row.issue_count ? 'warning' : 'ok',
        on_time_rate: row.on_time_rate
      }))
    });
    const byCustomer = groupOrderPerformance(state, drilldown, order => {
      const so = firstById(salesOrders, order.so_id || order.sales_order_id);
      const quotation = firstById(quotations, (so && (so.quotation_id || so.quote_id)) || order.quotation_id);
      return order.customer_id || order.customer || (so && (so.customer_id || so.customer)) || (quotation && (quotation.customer_id || quotation.customer));
    });
    const byRoute = groupOrderPerformance(state, drilldown, order => {
      const so = firstById(salesOrders, order.so_id || order.sales_order_id);
      const quotation = firstById(quotations, (so && (so.quotation_id || so.quote_id)) || order.quotation_id);
      return order.route_id || order.route || (quotation && (quotation.route_id || quotation.route));
    });
    const byDriver = groupOrderPerformance(state, drilldown, order => order.driver_id || order.driver || order.main_driver_id);
    const slaPlaybook = [
      {
        code: 'ESCALATE_LATE_DELIVERY',
        label: 'Xử lý trễ giao hàng',
        trigger_count: drilldown.worklist.filter(item => item.category_code === 'LATE_DELIVERY').length,
        instruction: 'Mở GPS/POD, gọi tài xế, cập nhật ETA và thông báo khách hàng nếu cần.',
        navigation: { view: 'tracking' }
      },
      {
        code: 'FIX_MISSING_POD',
        label: 'Bổ sung POD',
        trigger_count: drilldown.worklist.filter(item => item.category_code === 'MISSING_POD').length,
        instruction: 'Yêu cầu upload biên bản ký nhận trước khi chốt AP/Settlement.',
        navigation: { view: 'tracking' }
      },
      {
        code: 'REVIEW_COST_OVERRUN',
        label: 'Kiểm tra vượt chi phí',
        trigger_count: drilldown.worklist.filter(item => item.category_code === 'COST_OVERRUN').length,
        instruction: 'Mở Finance Cockpit để kiểm tra Actual Cost, nguyên nhân và quyền duyệt.',
        navigation: { view: 'accounting' }
      }
    ].filter(item => item.trigger_count > 0);
    const executiveSummary = drilldown.worklist.length
      ? `SLA có ${drilldown.worklist.length} cảnh báo, ${criticalCount} cảnh báo nghiêm trọng; ưu tiên xử lý các bucket trễ lớn và thiếu POD trước khi demo.`
      : 'SLA hiện sạch: chưa phát hiện cảnh báo trễ, thiếu POD hoặc vượt chi phí trong dữ liệu hiện tại.';

    return {
      kpis: {
        total_orders: { label: 'Tổng đơn phân tích', count: totalOrders },
        on_time_rate: { label: 'Tỉ lệ đúng hạn', percent: onTimeRate },
        sla_risks: { label: 'Cảnh báo SLA/KPI', count: drilldown.worklist.length },
        critical_risks: { label: 'Cảnh báo nghiêm trọng', count: criticalCount },
        cost_overrun: { label: 'Vượt chi phí', count: costOverrunCount }
      },
      executive_summary: executiveSummary,
      aging_buckets: agingBuckets,
      trend_by_day: trendByDay,
      risk_heatmap: [
        heatmapRows('Khách hàng', byCustomer, 'customers'),
        heatmapRows('Tuyến đường', byRoute, 'routes'),
        heatmapRows('Tài xế', byDriver, 'drivers')
      ],
      sla_playbook: slaPlaybook,
      by_customer: byCustomer,
      by_route: byRoute,
      by_driver: byDriver,
      drilldown_rows: drilldown.worklist.map(item => ({
        order_id: item.order_id || 'N/A',
        issue_label: issueLabels[item.category_code] || item.category_code,
        severity: item.severity,
        metric: item.metric,
        owner: item.owner,
        action_label: item.action_label,
        navigation: item.navigation
      })),
      recommendations: [
        {
          target: 'reporting',
          title: 'Theo dõi SLA theo ngày/tuần',
          message: 'Dùng bảng drill-down để lọc nhóm khách hàng, tuyến hoặc tài xế có nhiều cảnh báo.'
        },
        {
          target: 'tracking',
          title: 'Chuẩn hóa event GPS/POD',
          message: 'Các đơn thiếu event hoặc thiếu POD sẽ làm giảm tỉ lệ đúng hạn trên báo cáo.'
        }
      ]
    };
  }

  function buildMissingConfigWarnings(state) {
    return buildMasterSetupChecklist(state)
      .filter(item => item.status === 'missing')
      .map(item => ({
        code: `MISSING_${item.key.toUpperCase()}`,
        target: item.target,
        message: item.message
      }));
  }

  function buildUiHealthChecklist(state, now = new Date()) {
    const setup = buildMasterSetupWizardSteps(state);
    const rows = key => list(state, key);
    const hasRows = key => rows(key).length > 0;
    const hasActive = key => rows(key).some(isActiveRow);
    const hasRouteDistance = rows('routes').some(route => numberValue(route.total_distance || route.total_distance_km || route.distance_km) > 0);
    const assignedOrders = rows('delivery_orders').filter(order => order.vehicle_id || order.driver_id);
    const executionMode = buildExecutionModeCockpit(state);
    const hasInternalFleetPath = executionMode && executionMode.recommended_mode === 'internal_fleet';
    const masterMissing = setup.steps.filter(step => step.status === 'missing');
    const setupLabel = key => ({
      currency: 'Tiền tệ',
      tax: 'Thuế',
      accounting_period: 'Kỳ kế toán',
      customer: 'Khách hàng',
      route: 'Tuyến đường',
      vehicle_driver: 'Xe / tài xế',
      carrier: 'Carrier / Vendor',
      account_mapping: 'Mapping tài khoản'
    }[key] || 'Master Data');

    const checks = [
      {
        key: 'master_data',
        label: 'Master Data nền',
        status: setup.progress.percent >= 100 ? 'ready' : 'warning',
        score: setup.progress.percent,
        message: setup.progress.percent >= 100
          ? 'Master Data nền đã đủ để chạy demo A-Z.'
          : `Thiếu ${setup.progress.total - setup.progress.done} nhóm Master Data. Vào Master Data để cấu hình trước khi chạy luồng.`,
        target: { view: 'master-data', tabId: (masterMissing[0] && masterMissing[0].tabId) || 'md-tab-currencies' },
        action_label: masterMissing[0] ? `Cấu hình ${setupLabel(masterMissing[0].key)}` : 'Rà lại Master Data'
      },
      {
        key: 'quotation_so_do',
        label: 'Báo giá → SO → DO',
        status: hasRows('quotations') && hasRows('sales_orders') && hasRows('delivery_orders') ? 'ready' : 'warning',
        score: [hasRows('quotations'), hasRows('sales_orders'), hasRows('delivery_orders')].filter(Boolean).length * 33 + 1,
        message: 'Cần có đủ Báo giá, Sales Order và Delivery Order để nhìn được luồng đơn hàng.',
        target: { view: 'crm-sales', target: 'quotation-section' },
        action_label: 'Mở Báo giá / SO / DO'
      },
      {
        key: 'route_distance',
        label: 'Tuyến / khoảng cách',
        status: hasRouteDistance ? 'ready' : 'warning',
        score: hasRouteDistance ? 100 : 40,
        message: hasRouteDistance
          ? 'Tuyến đã có tổng km để tính kế hoạch, ETA và lượt xe quay đầu.'
          : 'Thiếu tuyến có tổng km. Vào Master Data → Tuyến đường để cấu hình khoảng cách.',
        target: { view: 'master-data', tabId: 'md-tab-routes' },
        action_label: 'Cấu hình tuyến đường'
      },
      {
        key: 'dispatch',
        label: 'Dispatch / phân xe tài xế',
        status: hasRows('transport_trips') || assignedOrders.length > 0 ? 'ready' : 'warning',
        score: hasRows('transport_trips') ? 100 : assignedOrders.length ? 80 : 35,
        message: hasRows('transport_trips') || assignedOrders.length
          ? 'Đã có dữ liệu điều phối để xem Gantt, lịch tuần và trạng thái xe/tài xế.'
          : 'Chưa có chuyến hoặc DO được phân xe/tài xế. Mở Dispatch để lập kế hoạch.',
        target: { view: 'dispatch', target: 'dispatch-calendar-panel' },
        action_label: 'Mở Dispatch'
      },
      {
        key: 'gps_pod',
        label: 'GPS / Event / POD',
        status: hasRows('transport_events') && hasRows('pods') ? 'ready' : 'warning',
        score: [hasRows('transport_events'), hasRows('pods')].filter(Boolean).length * 50,
        message: hasRows('transport_events') && hasRows('pods')
          ? 'Đã có chuỗi sự kiện và POD để kiểm tra vận hành thực tế.'
          : 'Thiếu event GPS hoặc POD. Vào GPS/POD để cập nhật bằng chứng giao hàng.',
        target: { view: 'tracking', target: 'gps-event-timeline-panel' },
        action_label: 'Mở GPS / POD'
      },
      {
        key: 'tender_carrier',
        label: 'Tender / Carrier',
        status: hasActive('carriers') && (hasRows('tenders') || hasInternalFleetPath) ? 'ready' : 'warning',
        score: hasActive('carriers') ? (hasRows('tenders') || hasInternalFleetPath ? 100 : 70) : 35,
        message: hasInternalFleetPath
          ? 'Có đội xe nội bộ: FO có thể đi Dispatch nội bộ, chỉ tender khi cần thuê ngoài.'
          : 'Nếu cần thuê ngoài, cấu hình Carrier và Tender Cockpit để chọn nhà vận chuyển.',
        target: { view: hasActive('carriers') ? 'accounting' : 'master-data', tabId: hasActive('carriers') ? undefined : 'md-tab-carriers', target: hasActive('carriers') ? 'tender-cockpit-panel' : undefined },
        action_label: hasActive('carriers') ? 'Mở Tender Cockpit' : 'Cấu hình Carrier / Vendor'
      },
      {
        key: 'finance',
        label: 'Actual Cost / AP / Settlement',
        status: hasRows('freight_actual_costs') && hasRows('ap_invoices') && hasRows('settlements') ? 'ready' : 'warning',
        score: [hasRows('freight_actual_costs'), hasRows('ap_invoices'), hasRows('settlements')].filter(Boolean).length * 33 + 1,
        message: 'Cần đủ Actual Cost, AP Invoice và Settlement để demo chốt chuyến tài chính.',
        target: { view: 'accounting', target: 'finance-process-cockpit-panel' },
        action_label: 'Mở Finance Cockpit'
      },
      {
        key: 'roles_audit',
        label: 'Phân quyền / Audit',
        status: hasRows('roles') && hasRows('users') && hasRows('audit_logs') ? 'ready' : 'warning',
        score: [hasRows('roles'), hasRows('users'), hasRows('audit_logs')].filter(Boolean).length * 33 + 1,
        message: 'Phân quyền và audit giúp demo thao tác duyệt/khóa có người chịu trách nhiệm.',
        target: { view: 'reporting', target: 'role-permission-board-panel' },
        action_label: 'Mở Role / Audit'
      }
    ].map(check => ({
      ...check,
      score: Math.max(0, Math.min(100, Math.round(check.score || 0))),
      severity: check.status === 'ready' ? 'ok' : 'warning'
    }));

    const done = checks.filter(item => item.status === 'ready').length;
    const total = checks.length;
    const percent = total ? Math.round(done * 100 / total) : 0;
    const masterActions = masterMissing.slice(0, 3).map(step => ({
      key: `setup_${step.key}`,
      label: `Cấu hình ${setupLabel(step.key)}`,
      message: step.message,
      target: { view: 'master-data', tabId: step.tabId },
      severity: 'warning'
    }));
    const missingActions = checks
      .filter(item => item.status !== 'ready')
      .map(item => ({
        key: item.key,
        label: item.action_label,
        message: item.message,
        target: item.target,
        severity: item.severity
      }));
    const next_actions = [...masterActions, ...missingActions]
      .filter((action, index, arr) => arr.findIndex(candidate => candidate.label === action.label && JSON.stringify(candidate.target) === JSON.stringify(action.target)) === index)
      .slice(0, 8);
    if (!next_actions.length) {
      next_actions.push({
        key: 'open_control_tower',
        label: 'Mở Control Tower',
        message: 'Dữ liệu nền đã ổn, chuyển sang xem điều hành tổng quan.',
        target: { view: 'overview', target: 'tms-control-tower' },
        severity: 'ok'
      });
    }
    const guidance = checks
      .filter(item => item.status !== 'ready')
      .map(item => item.key === 'master_data'
        ? 'Vào Master Data để hoàn tất cấu hình nền trước khi demo khách hàng.'
        : item.message);
    return {
      generated_at: now instanceof Date && !Number.isNaN(now.getTime()) ? now.toISOString() : new Date().toISOString(),
      progress: { done, total, percent },
      items: checks,
      next_actions,
      guidance
    };
  }

  function buildMasterSetupWizardSteps(state) {
    const tabMap = {
      currency: { tabId: 'md-tab-currencies', uiStatus: 'ready', actionLabel: 'Cấu hình ngay' },
      tax: { tabId: 'md-tab-tax-codes', uiStatus: 'ready', actionLabel: 'Cấu hình ngay' },
      accounting_period: { tabId: 'md-tab-accounting-periods', uiStatus: 'ready', actionLabel: 'Cấu hình ngay' },
      customer: { tabId: 'md-tab-customers', uiStatus: 'ready', actionLabel: 'Cấu hình ngay' },
      route: { tabId: 'md-tab-routes', uiStatus: 'ready', actionLabel: 'Cấu hình ngay' },
      vehicle_driver: { tabId: 'md-tab-vehicles', uiStatus: 'ready', actionLabel: 'Cấu hình ngay' },
      carrier: { tabId: 'md-tab-carriers', uiStatus: 'ready', actionLabel: 'Cấu hình ngay' },
      account_mapping: { tabId: 'md-tab-account-mappings', uiStatus: 'ready', actionLabel: 'Cấu hình ngay' }
    };
    const steps = buildMasterSetupChecklist(state).map((item, index) => ({
      ...item,
      order: index + 1,
      ...(tabMap[item.key] || { tabId: null, uiStatus: 'needs_ui', actionLabel: 'Cần bổ sung UI' })
    }));
    const done = steps.filter(step => step.status === 'done').length;
    const total = steps.length;
    const percent = total ? Math.round(done * 100 / total) : 0;
    const guidance = steps
      .filter(step => step.uiStatus === 'needs_ui')
      .map(step => {
        const names = {
          tax: 'Thuế / mã thuế',
          accounting_period: 'Kỳ kế toán',
          carrier: 'Carrier / vendor',
          account_mapping: 'Mapping tài khoản'
        };
        const name = names[step.key] || `${step.label[0].toUpperCase()}${step.label.slice(1)}`;
        return `${name} đã có backend/master data, cần bổ sung tab quản trị riêng để đạt UX như hệ thống lớn.`;
      });
    return { progress: { done, total, percent }, steps, guidance };
  }

  function buildMasterSetupGuidedDetail(state, key) {
    const wizard = buildMasterSetupWizardSteps(state);
    const selected = wizard.steps.find(step => step.key === key)
      || wizard.steps.find(step => step.status === 'missing')
      || wizard.steps[0]
      || null;
    if (!selected) {
      return {
        key: '',
        status: 'missing',
        title: 'Chưa có bước setup',
        tabId: '',
        actionLabel: 'Cấu hình ngay',
        flow_impact: [],
        guidance: ['Chưa có dữ liệu checklist để hướng dẫn setup.']
      };
    }
    const impactMap = {
      currency: ['Tài chính, AP/AR và báo cáo cần tiền tệ để hiển thị số tiền đúng.', 'Nếu thiếu tiền tệ, user sẽ không biết đơn giá/chi phí dùng loại tiền nào.'],
      tax: ['Báo giá, Actual Cost và AP cần mã thuế để tính VAT/thuế đúng.', 'Nếu thiếu mã thuế, vào Master Data → Mã thuế trước khi demo tài chính.'],
      accounting_period: ['AP/Settlement cần kỳ kế toán mở để hạch toán và đối soát.', 'Nếu thiếu kỳ kế toán, Finance Cockpit chỉ nên xem dữ liệu, chưa nên post GL.'],
      customer: ['Báo giá và Sales Order cần khách hàng để tạo luồng bán hàng.', 'Nếu thiếu khách hàng, luồng QT → SO sẽ bị chặn ngay từ đầu.'],
      route: ['Báo giá, Delivery Order và Dispatch cần tuyến đường/khoảng cách để tính kế hoạch.', 'Tuyến đường giúp bản đồ, Gantt và KPI đọc đúng quãng đường dự kiến.'],
      vehicle_driver: ['Dispatch nội bộ cần xe và tài xế rảnh để phân bổ nguồn lực.', 'Nếu thiếu xe/tài xế, hệ thống sẽ gợi ý thuê ngoài hoặc cần cấu hình Master Data.'],
      carrier: ['Tender/Carrier cần vendor hoặc carrier nội bộ để chọn nhà vận chuyển.', 'Nếu công ty tự chạy xe, cấu hình carrier nội bộ để FO có thể đi Dispatch nội bộ.'],
      account_mapping: ['Actual Cost, AP Invoice và Settlement cần mapping tài khoản để hạch toán đúng.', 'Nếu thiếu mapping, Finance Cockpit chỉ nên dừng ở bước kiểm tra chi phí.']
    };
    const guidance = selected.status === 'done'
      ? [
        `${selected.label} đã có dữ liệu; bước này sẵn sàng cho demo.`,
        `Có thể bấm “${selected.actionLabel}” để rà lại hoặc chỉnh cấu hình trong Master Data.`
      ]
      : [
        selected.message,
        `Vào Master Data → ${selected.tabId || 'tab liên quan'} để cấu hình trước khi chạy luồng A-Z.`
      ];
    return {
      key: selected.key,
      order: selected.order,
      title: selected.label,
      status: selected.status,
      status_label: selected.status === 'done' ? 'Đã cấu hình' : 'Cần cấu hình',
      tabId: selected.tabId,
      actionLabel: selected.actionLabel,
      uiStatus: selected.uiStatus,
      message: selected.message,
      flow_impact: impactMap[selected.key] || ['Bước này ảnh hưởng trực tiếp tới luồng demo A-Z.'],
      guidance
    };
  }

  function buildDriverShiftPlanner(state, startDay = new Date()) {
    const scheduleDateKey = value => {
      const date = new Date(value);
      return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
    };
    const start = new Date(startDay);
    start.setHours(0, 0, 0, 0);
    const days = Array.from({ length: 7 }, (_, index) => {
      const date = new Date(start);
      date.setDate(start.getDate() + index);
      return {
        date,
        key: scheduleDateKey(date),
        label: date.toLocaleDateString('vi-VN', { weekday: 'short', day: '2-digit', month: '2-digit' })
      };
    });
    const shifts = list(state, 'driver_shifts');
    const drivers = list(state, 'drivers');
    const driverRows = drivers.map(driver => ({
      driver_id: String(driver.id || driver.driver_id || ''),
      name: driver.name || driver.id || '',
      status: driver.status || '',
      days: days.map(day => ({
        date: day.key,
        shifts: shifts.filter(shift => {
          const when = parseTime(shift.shift_start);
          return String(shift.driver_id || '') === String(driver.id || driver.driver_id || '')
            && when && scheduleDateKey(when) === day.key;
        }).sort((a, b) => parseTime(a.shift_start) - parseTime(b.shift_start))
      }))
    }));
    const sourceAvailability = list(state, 'vehicle_availability');
    const sourceTrips = sourceAvailability.length ? sourceAvailability : list(state, 'transport_trips');
    const maintenanceTimelines = sourceTrips.filter(item => normalized(item.kind) === 'maintenance' && item.vehicle_id).map(item => ({
      maintenance_request_id: item.maintenance_request_id || item.id,
      vehicle_id: item.vehicle_id,
      start_at: parseTime(item.planned_departure_at || item.planned_start),
      end_at: parseTime(item.available_at_origin || item.planned_arrival_at || item.planned_end),
      label: item.maintenance_label || item.description || item.request_no || 'Bảo dưỡng / sửa chữa'
    }));
    const vehicleTimelines = sourceTrips.filter(item => normalized(item.kind) !== 'maintenance' && item.vehicle_id).map(item => {
      const destination = item.destination || 'B';
      const availableDestination = parseTime(item.available_at_destination || item.planned_arrival_at);
      const availableOrigin = parseTime(item.available_at_origin || item.planned_return_at);
      const returnMode = item.return_mode || (item.planned_return_at ? 'empty_return' : 'missing');
      return {
        trip_id: item.trip_id || item.id,
        vehicle_id: item.vehicle_id,
        driver_id: item.driver_id || '',
        co_driver_id: item.co_driver_id || '',
        origin: item.origin || 'A',
        destination,
        departure_at: parseTime(item.planned_departure_at),
        available_at_destination: availableDestination,
        available_at_origin: availableOrigin,
        availability_at_destination_label: availableDestination
          ? `Sẵn sàng tại ${destination || 'B'}: ${dateTimeLabel(availableDestination)}`
          : `Chưa có mốc sẵn sàng tại ${destination || 'B'}`,
        availability_at_origin_label: availableOrigin
          ? `Về lại ${item.origin || 'A'}: ${dateTimeLabel(availableOrigin)}`
          : 'Chưa cấu hình tuyến quay đầu',
        return_mode: returnMode,
        return_planned: ['empty_return', 'backhaul'].includes(normalized(returnMode)) || Boolean(availableOrigin),
        warning_code: item.warning_code || (!availableOrigin ? 'RETURN_ROUTE_REQUIRED' : null),
        outbound_speed_kmh: numberValue(item.outbound_speed_kmh),
        outbound_speed_source: item.outbound_speed_source || '',
        return_speed_kmh: numberValue(item.return_speed_kmh),
        return_speed_source: item.return_speed_source || ''
      };
    });
    driverRows.forEach(row => {
      row.days.forEach((day, dayIndex) => {
        const dayStart = new Date(days[dayIndex].date);
        dayStart.setHours(0, 0, 0, 0);
        const dayEnd = new Date(dayStart);
        dayEnd.setDate(dayEnd.getDate() + 1);
        day.trip_timelines = vehicleTimelines.filter(item => {
          const isCrew = String(item.driver_id || '') === row.driver_id
            || String(item.co_driver_id || '') === row.driver_id;
          const startAt = item.departure_at;
          const endAt = item.available_at_origin || item.available_at_destination || startAt;
          return isCrew && startAt && endAt && startAt < dayEnd && endAt > dayStart;
        });
        day.trip_ids = day.trip_timelines.map(item => item.trip_id).filter(Boolean);
      });
    });
    const activeShifts = shifts.filter(shift => normalized(shift.status || 'planned') !== 'cancelled');
    const vehicles = list(state, 'vehicles');
    const vehicleRows = vehicles.map(vehicle => {
      const vehicleId = String(vehicle.id || vehicle.vehicle_id || '');
      return {
        vehicle_id: vehicleId,
        label: vehicle.license_plate || vehicle.name || vehicleId,
        type: vehicle.type || vehicle.vehicle_type_name || vehicle.vehicle_type_id || '',
        days: days.map(day => {
          const dayStart = new Date(day.date);
          dayStart.setHours(0, 0, 0, 0);
          const dayEnd = new Date(dayStart);
          dayEnd.setDate(dayEnd.getDate() + 1);
          const timelines = vehicleTimelines.filter(item => {
            if (String(item.vehicle_id || '') !== vehicleId) return false;
            const startAt = item.departure_at || item.available_at_destination;
            const endAt = item.available_at_origin || item.available_at_destination || startAt;
            return startAt && startAt < dayEnd && endAt >= dayStart;
          });
          const assignedShifts = activeShifts.filter(shift => {
            if (String(shift.vehicle_id || '') !== vehicleId) return false;
            const startAt = parseTime(shift.shift_start);
            const endAt = parseTime(shift.shift_end);
            return startAt && endAt && startAt < dayEnd && endAt > dayStart;
          });
          const maintenances = maintenanceTimelines.filter(item => String(item.vehicle_id || '') === vehicleId
            && item.start_at && item.end_at && item.start_at < dayEnd && item.end_at > dayStart);
          const hasOperationalSchedule = timelines.length || assignedShifts.length;
          return {
            date: day.key,
            status: maintenances.length && hasOperationalSchedule ? 'conflict'
              : maintenances.length ? 'maintenance'
                : hasOperationalSchedule ? 'busy' : 'available',
            timelines,
            shifts: assignedShifts,
            maintenances,
            trip_ids: timelines.map(item => item.trip_id).filter(Boolean),
            driver_ids: assignedShifts.map(item => item.driver_id).filter(Boolean)
          };
        })
      };
    });
    const alerts = [];
    for (let left = 0; left < activeShifts.length; left += 1) {
      for (let right = left + 1; right < activeShifts.length; right += 1) {
        const a = activeShifts[left];
        const b = activeShifts[right];
        const overlaps = parseTime(a.shift_start) < parseTime(b.shift_end)
          && parseTime(a.shift_end) > parseTime(b.shift_start);
        if (!overlaps) continue;
        if (String(a.driver_id) === String(b.driver_id)) {
          alerts.push({ code: 'DRIVER_SHIFT_OVERLAP', severity: 'critical', message: `Tài xế ${a.driver_id} bị trùng ca ${a.id} và ${b.id}.` });
        }
        if (a.vehicle_id && String(a.vehicle_id) === String(b.vehicle_id)) {
          alerts.push({ code: 'VEHICLE_SHIFT_OVERLAP', severity: 'critical', message: `Xe ${a.vehicle_id} bị gán vào hai ca trùng nhau.` });
        }
      }
    }
    vehicleTimelines.filter(item => item.warning_code).forEach(item => alerts.push({
      code: item.warning_code,
      severity: 'warning',
      message: `Trip ${item.trip_id} chưa đủ dữ liệu Route/Trip để tính thời điểm xe ${item.vehicle_id} quay về.`
    }));
    vehicleRows.forEach(row => row.days.filter(day => day.status === 'conflict').forEach(day => alerts.push({
      code: 'VEHICLE_MAINTENANCE_OVERLAP',
      severity: 'critical',
      message: `Vehicle ${row.label || row.vehicle_id} has a Trip/shift overlapping maintenance on ${day.date}.`
    })));
    return {
      days: days.map(({ key, label }) => ({ key, label })),
      driver_rows: driverRows,
      vehicle_rows: vehicleRows,
      vehicle_timelines: vehicleTimelines,
      maintenance_timelines: maintenanceTimelines,
      alerts
    };
  }

  function dispatchDateKey(value, timeZone = 'Asia/Bangkok') {
    if (!value) return '';
    const parsed = parseTime(value);
    if (!parsed) return '';
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    }).formatToParts(parsed).reduce((result, part) => {
      result[part.type] = part.value;
      return result;
    }, {});
    return `${parts.year}-${parts.month}-${parts.day}`;
  }

  function filterDispatchOrdersByDate(orders, isoDate, timeZone = 'Asia/Bangkok') {
    const source = Array.isArray(orders) ? orders : [];
    const undated = source.filter(order => !(
      order.pickup_window_start || order.pickup_date || order.planned_pickup_at
    ));
    if (!isoDate) return { orders: source.filter(order => !undated.includes(order)), undated };
    return {
      orders: source.filter(order => dispatchDateKey(
        order.pickup_window_start || order.pickup_date || order.planned_pickup_at,
        timeZone
      ) === isoDate),
      undated
    };
  }

  function resolveDispatchTripGate(doId, trips, tripLinks = []) {
    const targetId = String(doId || '');
    const linkedTripIds = new Set((Array.isArray(tripLinks) ? tripLinks : [])
      .filter(link => String(link.do_id || link.delivery_order_id || '') === targetId)
      .map(link => String(link.trip_id || ''))
      .filter(Boolean));
    const linked = (Array.isArray(trips) ? trips : []).filter(trip => {
      const ids = trip.delivery_order_ids || trip.delivery_orders || trip.do_ids || [];
      return linkedTripIds.has(String(trip.id || ''))
        || (Array.isArray(ids) && ids.some(id => String(id?.id || id) === targetId))
        || String(trip.delivery_order_id || trip.do_id || '') === targetId;
    });
    const normalizedStatus = trip => normalized(trip.status || '').replace(/\s+/g, '_');
    const planned = linked.filter(trip => ['planned', 'da_lap_ke_hoach'].includes(normalizedStatus(trip)));
    if (planned.length === 1) return { state: 'ready', trip: planned[0], trips: linked };
    if (planned.length > 1) return { state: 'choose', trip: null, trips: planned };
    const draft = linked.find(trip => ['draft', 'nhap'].includes(normalizedStatus(trip)));
    if (draft) return { state: 'draft', trip: draft, trips: linked };
    if (linked.length) return { state: 'unavailable', trip: null, trips: linked };
    return { state: 'missing', trip: null, trips: [] };
  }

  return {
    buildMasterSetupChecklist,
    buildUiHealthChecklist,
    buildMasterSetupWizardSteps,
    buildMasterSetupGuidedDetail,
    buildControlTower,
    buildTransportationWorkQueue,
    buildTripReturnCockpit,
    buildOrderTimeline,
    buildOrderTimelineDetail,
    buildShipment360Detail,
    buildShipmentSettlementReadiness,
    buildFinanceWorklist,
    buildFinanceCockpitSummary,
    buildFinanceActionWorkbench,
    buildFinanceProcessCockpit,
    buildFinanceCloseoutWorkbench,
    buildFinanceRecordDetail,
    buildFinanceConfigHealth,
    buildFinanceMasterDataTabs,
    buildExecutionModeCockpit,
    getTripJourneyPresentation,
    getTripStatusGroup,
    buildTenderCockpit,
    buildTenderRecordDetail,
    buildCarrierTenderHealth,
    buildCarrierSourcingWorkbench,
    buildTenderDetailCockpit,
    buildTenderDecisionCockpit,
    buildDispatchCapacityBoard,
    buildDispatchCalendar,
    buildDispatchWeekPlanner,
    buildVehicleSchedule,
    buildDispatchDayFleet,
    buildDriverShiftPlanner,
    buildDispatchCalendarDetail,
    filterDispatchOrdersByDate,
    resolveDispatchTripGate,
    buildDispatchResourceOptions,
    buildGpsEventTimeline,
    buildSlaKpiDrilldown,
    buildSlaKpiIssueDetail,
    buildRolePermissionBoard,
    buildRoleAdminWorkbench,
    buildReportingDrilldown,
    buildMissingConfigWarnings
  };
});

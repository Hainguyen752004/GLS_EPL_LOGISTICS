const assert = require('assert');
const cockpit = require('../js/tms-cockpit-utils.js');

const baseState = {
  delivery_orders: [{
    id: 'DO-A',
    status: 'delivered',
    vehicle_id: 'VEH-A',
    driver_id: '',
    freight_order_id: 'FO-A'
  }],
  freight_actual_costs: [{ id: 'COST-B', freight_order_id: 'FO-B', status: 'approved' }],
  ap_invoices: [{ id: 'AP-B', cost_id: 'COST-B', status: 'posted' }],
  settlements: [{ id: 'SET-B', ap_invoice_id: 'AP-B', status: 'completed' }],
  pods: [],
  transport_events: []
};

const timeline = cockpit.buildOrderTimeline(baseState, 'DO-A');
assert.strictEqual(timeline.find(step => step.key === 'dispatch').status, 'pending', 'dispatch needs both vehicle and driver');
assert.strictEqual(timeline.find(step => step.key === 'pod').status, 'pending', 'delivered status alone is not POD evidence');
assert.strictEqual(timeline.find(step => step.key === 'settlement').status, 'pending', 'another shipment settlement must not complete this shipment');

const financeDetail = cockpit.buildOrderTimelineDetail(baseState, 'DO-A', 'settlement');
assert.deepStrictEqual(financeDetail.related.finance, [], 'finance fallback must never expose another shipment records');

const costOnlyDetail = cockpit.buildOrderTimelineDetail({
  ...baseState,
  freight_actual_costs: [{ id: 'COST-A', freight_order_id: 'FO-A', status: 'approved' }],
  ap_invoices: [],
  settlements: []
}, 'DO-A', 'settlement');
assert.strictEqual(costOnlyDetail.status, 'pending', 'actual cost alone must not complete settlement detail');

const completeState = {
  ...baseState,
  delivery_orders: [{ ...baseState.delivery_orders[0], driver_id: 'DRV-A' }],
  pods: [{ id: 'POD-A', do_id: 'DO-A', delivery_time: '2026-08-27T10:00:00+07:00' }],
  freight_actual_costs: [{ id: 'COST-A', freight_order_id: 'FO-A', status: 'approved' }],
  ap_invoices: [{ id: 'AP-A', cost_id: 'COST-A', status: 'posted' }],
  settlements: [{ id: 'SET-A', ap_invoice_id: 'AP-A', status: 'completed' }]
};
const completeTimeline = cockpit.buildOrderTimeline(completeState, 'DO-A');
assert.strictEqual(completeTimeline.find(step => step.key === 'dispatch').status, 'done');
assert.strictEqual(completeTimeline.find(step => step.key === 'pod').status, 'done');
assert.strictEqual(completeTimeline.find(step => step.key === 'settlement').status, 'done');

const dossier = cockpit.buildShipment360Detail(baseState, 'DO-A');
assert.strictEqual(dossier.summary.distance_label, 'Chưa có dữ liệu', 'missing distance must not be shown as 0.0 km');

const internalState = {
  ...completeState,
  delivery_orders: [{ ...completeState.delivery_orders[0], distance_km: 44 }],
  carriers: [{ id: 'EPL-INTERNAL', is_internal: true, status: 'active' }],
  freight_actual_costs: [{ id: 'COST-A', freight_order_id: 'FO-A', carrier_id: 'EPL-INTERNAL', status: 'approved' }],
  ap_invoices: [],
  settlements: []
};
const internalReadiness = cockpit.buildShipmentSettlementReadiness(internalState, 'DO-A');
assert.strictEqual(
  internalReadiness.checks.find(check => check.key === 'ap_invoice').status,
  'not_applicable',
  'internal fleet costs must not require a supplier AP invoice'
);
assert.strictEqual(
  internalReadiness.checks.find(check => check.key === 'distance_reconcile').status,
  'warning',
  'missing actual distance must stay visible as a warning'
);

const externalState = {
  ...internalState,
  carriers: [{ id: 'CARRIER-OUT', is_internal: false, status: 'active' }],
  freight_actual_costs: [{ id: 'COST-A', freight_order_id: 'FO-A', carrier_id: 'CARRIER-OUT', status: 'approved' }]
};
const externalReadiness = cockpit.buildShipmentSettlementReadiness(externalState, 'DO-A');
assert.strictEqual(
  externalReadiness.checks.find(check => check.key === 'ap_invoice').status,
  'missing',
  'outsourced carrier costs must require a supplier AP invoice'
);

console.log('SHIPMENT_DOSSIER_ISOLATION_OK');

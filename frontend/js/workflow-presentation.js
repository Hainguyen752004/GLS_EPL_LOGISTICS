(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.WorkflowPresentation = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const LOCKED = {
    quotation: new Set(['approved', 'da_duyet']),
    sales_order: new Set(['confirmed', 'da_xac_nhan']),
    delivery_order: new Set([
      'approved',
      'da_duyet',
      'in_transit',
      'dang_van_chuyen',
      'arrived',
      'delivered',
      'completed',
      'posted',
      'cancelled'
    ])
  };

  function statusKey(status) {
    if (globalThis.WorkflowUIUtils?.workflowStatusKey) {
      return globalThis.WorkflowUIUtils.workflowStatusKey(status);
    }
    return String(status || '').trim().toLowerCase().replaceAll(' ', '_');
  }

  function presentRecord(record) {
    const source = record || {};
    const businessId = String(source.id || source.do_id || source.code || '');
    const isDemo = businessId.toUpperCase().startsWith('DEMO-');
    return { ...source, is_demo: isDemo, data_label: isDemo ? 'Dữ liệu demo' : '' };
  }

  function actionsForStatus(entity, status) {
    const locked = LOCKED[entity]?.has(statusKey(status)) || false;
    return { view: true, edit: !locked, delete: !locked };
  }

  return { presentRecord, actionsForStatus };
});

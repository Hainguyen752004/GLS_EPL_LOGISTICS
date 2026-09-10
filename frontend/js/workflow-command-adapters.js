(function (root, factory) {
  const policy = typeof module === 'object' && module.exports ? require('./command-policy.js') : root.CommandPolicy;
  const api = factory(policy);
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.WorkflowCommandAdapters = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function (policy) {
  const COMMAND_NAMES = ['quotationCreate', 'quotationEdit', 'quotationApprove', 'deliveryOrderCreate', 'deliveryOrderEdit', 'deliveryOrderApprove', 'dispatch', 'shipmentStep', 'pod'];

  function createWorkflowCommandAdapters({ request, reload, applyServerState, onError }) {
    const execute = ({ path, method = 'POST', body, headers = {} }) => policy.executeCommand({
      request: () => request(path, {
        method,
        headers: { 'Content-Type': 'application/json', ...headers },
        body: body === undefined ? undefined : JSON.stringify(body)
      }),
      applySuccess: payload => {
        if (typeof applyServerState === 'function') applyServerState(payload?.data);
      },
      reload,
      onError
    });
    return Object.fromEntries(COMMAND_NAMES.map(name => [name, execute]));
  }

  return { createWorkflowCommandAdapters };
});

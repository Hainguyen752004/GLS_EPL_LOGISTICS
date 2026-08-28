const assert = require('assert');
const fs = require('fs');
const path = require('path');

const frontendRoot = path.join(__dirname, '..');
const appSource = fs.readFileSync(path.join(frontendRoot, 'js', 'app.js'), 'utf8');
const failures = [];

function check(name, assertion) {
  try {
    assertion();
  } catch (error) {
    failures.push(`${name}: ${error.message}`);
  }
}

check('operation log panel is created and exposed for real user actions', () => {
  assert.match(appSource, /function\s+ensureOperationLogPanel\s*\(/, 'Missing operation log panel factory.');
  assert.match(appSource, /id\s*=\s*['"]operation-log-panel['"]/, 'Operation log panel id is missing.');
  assert.match(appSource, /function\s+recordOperationLog\s*\(/, 'Missing operation log recorder.');
  assert.match(appSource, /window\.recordOperationLog\s*=\s*recordOperationLog/, 'Recorder must be available to UI handlers.');
});

check('workflow commands show pending, success, and error database feedback', () => {
  const workflow = appSource.match(/async function executeWorkflowCommand[\s\S]*?\n\}/);
  assert.ok(workflow, 'Missing executeWorkflowCommand().');
  assert.match(workflow[0], /const\s+opId\s*=\s*recordOperationLog/, 'Workflow must create a pending operation log.');
  assert.match(workflow[0], /status:\s*['"]pending['"]/, 'Workflow must show pending state.');
  assert.match(workflow[0], /status:\s*['"]success['"]/, 'Workflow must show success state.');
  assert.match(workflow[0], /status:\s*['"]error['"]/, 'Workflow must show error state.');
  assert.match(workflow[0], /result\.payload\?\.message/, 'Workflow must surface server success message.');
  assert.match(workflow[0], /result\.error\?\.message/, 'Workflow must surface server error message.');
});

check('workflow commands authenticate browser mutations with the runtime API token', () => {
  const workflow = appSource.match(/async function executeWorkflowCommand[\s\S]*?\n\}/);
  assert.ok(workflow, 'Missing executeWorkflowCommand().');
  assert.match(
    workflow[0],
    /headers:\s*\{[\s\S]*?\.\.\.financeAuthHeaders\(\)[\s\S]*?\}/,
    'Workflow requests must merge the runtime authorization header before calling the API.'
  );
});

check('workflow success refreshes only the affected module instead of the whole application', () => {
  const workflow = appSource.match(/async function executeWorkflowCommand[\s\S]*?\n\}/);
  assert.ok(workflow, 'Missing executeWorkflowCommand().');
  assert.match(
    workflow[0],
    /refreshWorkflowCommandData\(commandName\)/,
    'Workflow reload must target the affected business module.'
  );
  assert.doesNotMatch(
    workflow[0],
    /window\.loadAllData|await\s+loadAllData/,
    'Workflow save must not render every application module after each mutation.'
  );
});

check('dispatch Trip loading authenticates the protected planning endpoint', () => {
  const dispatchLoader = appSource.match(/async function loadDispatchBoard[\s\S]*?\n\}/);
  assert.ok(dispatchLoader, 'Missing loadDispatchBoard().');
  assert.match(
    dispatchLoader[0],
    /fetchAllPaginated\(`\$\{API_BASE\}\/api\/tms\/trips`,\s*\d+,\s*\{\s*headers:\s*financeAuthHeaders\(\)\s*\}\)/,
    'Dispatch Trip request must load all pages with the runtime authorization header.'
  );
});

check('legacy quotation and delivery forms authenticate their direct API mutations', () => {
  for (const functionName of ['submitQuotationForm', 'submitDOForm']) {
    const handler = appSource.match(new RegExp(`async function ${functionName}\\([\\s\\S]*?\\n\\}`));
    assert.ok(handler, `Missing ${functionName}().`);
    assert.match(
      handler[0],
      /headers:\s*\{[\s\S]*?\.\.\.financeAuthHeaders\(\)[\s\S]*?\}/,
      `${functionName} must authenticate its write request.`
    );
  }
});

check('finance commands update the same log after backend response', () => {
  const finance = appSource.match(/async function executeFinanceCommand[\s\S]*?\n\}/);
  assert.ok(finance, 'Missing executeFinanceCommand().');
  assert.match(finance[0], /const\s+opId\s*=\s*recordOperationLog/, 'Finance must create a pending operation log.');
  assert.match(finance[0], /status:\s*['"]pending['"]/, 'Finance must show pending state.');
  assert.match(finance[0], /status:\s*['"]success['"]/, 'Finance must show success state.');
  assert.match(finance[0], /status:\s*['"]error['"]/, 'Finance must show error state.');
  assert.match(finance[0], /payload\.message/, 'Finance must surface server success message.');
  assert.match(finance[0], /error\.message/, 'Finance must surface connection errors.');
});

if (failures.length) {
  throw new Error(`Operation log UI contract is not implemented:\n- ${failures.join('\n- ')}`);
}

console.log('OPERATION_LOG_UI_OK');

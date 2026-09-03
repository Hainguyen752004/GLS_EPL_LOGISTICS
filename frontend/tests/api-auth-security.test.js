/**
 * Test hồi quy cho các bản vá an ninh phía frontend.
 *
 * 1. Lớp bọc fetch phải gắn bearer token cho mọi lệnh gọi /api/, vì backend
 *    giờ xác thực theo kiểu mặc định-chặn và ứng dụng có hơn 80 chỗ gọi fetch.
 * 2. showToast không được nội suy nội dung vào innerHTML — nó nhận cả tên bản
 *    ghi do người ngoài đặt và error.message từ server.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

// --------------------------------------------------------------------------
// 1. Lớp bọc fetch gắn token
// --------------------------------------------------------------------------

function loadApiAuth({ token }) {
  const store = new Map();
  if (token) store.set('EPL_TMS_API_TOKEN', token);

  const calls = [];
  const toasts = [];

  const sandbox = {
    console: { error() {}, log() {} },
    setTimeout() {},
    Headers: globalThis.Headers,
    URL: globalThis.URL,
    Object,
    Boolean,
    String,
    localStorage: {
      getItem: key => (store.has(key) ? store.get(key) : null),
      setItem: (key, value) => store.set(key, value),
    },
    location: { href: 'http://localhost:8001/', origin: 'http://localhost:8001' },
    showToast: message => toasts.push(message),
    fetch(resource, options) {
      calls.push({ resource, options });
      return Promise.resolve({ status: 200 });
    },
  };
  sandbox.window = sandbox;
  sandbox.globalThis = sandbox;

  const source = fs.readFileSync(
    path.join(__dirname, '..', 'js', 'api-auth.js'),
    'utf8'
  );
  vm.createContext(sandbox);
  vm.runInContext(source, sandbox);
  return { sandbox, calls, toasts };
}

function authHeaderOf(call) {
  const headers = call.options && call.options.headers;
  if (!headers) return null;
  return typeof headers.get === 'function'
    ? headers.get('Authorization')
    : headers.Authorization;
}

// Đường /api/ tương đối phải được gắn token.
{
  const { sandbox, calls } = loadApiAuth({ token: 'token-abc' });
  sandbox.fetch('/api/customers');
  assert.strictEqual(calls.length, 1);
  assert.strictEqual(authHeaderOf(calls[0]), 'Bearer token-abc');
}

// Đường tuyệt đối cùng origin cũng phải được gắn token.
{
  const { sandbox, calls } = loadApiAuth({ token: 'token-abc' });
  sandbox.fetch('http://localhost:8001/api/invoices');
  assert.strictEqual(authHeaderOf(calls[0]), 'Bearer token-abc');
}

// Phương thức ghi cũng phải mang token, và không được mất options đã có.
{
  const { sandbox, calls } = loadApiAuth({ token: 'token-abc' });
  sandbox.fetch('/api/routes', {
    method: 'POST',
    body: '{}',
    headers: { 'Content-Type': 'application/json' },
  });
  assert.strictEqual(authHeaderOf(calls[0]), 'Bearer token-abc');
  assert.strictEqual(calls[0].options.method, 'POST');
  assert.strictEqual(calls[0].options.body, '{}');
  assert.strictEqual(calls[0].options.headers.get('Content-Type'), 'application/json');
}

// Header do chỗ gọi tự đặt không bị ghi đè (ví dụ financeAuthHeaders).
{
  const { sandbox, calls } = loadApiAuth({ token: 'token-abc' });
  sandbox.fetch('/api/tms/costs', {
    headers: { Authorization: 'Bearer token-rieng' },
  });
  assert.strictEqual(authHeaderOf(calls[0]), 'Bearer token-rieng');
}

// Tài nguyên không thuộc API thì không được gắn token — tránh rò ra ngoài.
{
  const { sandbox, calls } = loadApiAuth({ token: 'token-abc' });
  sandbox.fetch('/static/js/app.js');
  assert.ok(!authHeaderOf(calls[0]), 'tài nguyên tĩnh không được mang token');

  sandbox.fetch('https://tile.openstreetmap.org/1/2/3.png');
  assert.ok(!authHeaderOf(calls[1]), 'host ngoài không được mang token');
}

// Các đường công khai không cần token.
{
  const { sandbox, calls } = loadApiAuth({ token: 'token-abc' });
  sandbox.fetch('/api/health');
  assert.ok(!authHeaderOf(calls[0]), '/api/health là đường công khai');
  sandbox.fetch('/api/parking-qr/abc123');
  assert.ok(!authHeaderOf(calls[1]), 'luồng quét QR là đường công khai');
}

// Thiếu token thì phải báo cho người vận hành, không im lặng.
{
  const { sandbox, toasts } = loadApiAuth({ token: '' });
  sandbox.fetch('/api/customers');
  assert.strictEqual(toasts.length, 1);
  assert.ok(
    toasts[0].includes('EPL_TMS_API_TOKEN'),
    'thông báo phải chỉ rõ cách đặt token'
  );
}

// Chỉ cảnh báo một lần, không spam mỗi request.
{
  const { sandbox, toasts } = loadApiAuth({ token: '' });
  sandbox.fetch('/api/customers');
  sandbox.fetch('/api/drivers');
  sandbox.fetch('/api/invoices');
  assert.strictEqual(toasts.length, 1);
}

// localStorage bị chặn (cửa sổ ẩn danh) thì không được bật lỗi.
{
  const source = fs.readFileSync(
    path.join(__dirname, '..', 'js', 'api-auth.js'),
    'utf8'
  );
  const calls = [];
  const sandbox = {
    console: { error() {} },
    setTimeout() {},
    Headers: globalThis.Headers,
    URL: globalThis.URL,
    Object,
    Boolean,
    String,
    localStorage: {
      getItem() { throw new Error('storage bị chặn'); },
      setItem() { throw new Error('storage bị chặn'); },
    },
    location: { href: 'http://localhost:8001/', origin: 'http://localhost:8001' },
    fetch(resource, options) { calls.push({ resource, options }); return Promise.resolve({ status: 200 }); },
  };
  sandbox.window = sandbox;
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(source, sandbox);
  sandbox.fetch('/api/customers');
  assert.strictEqual(calls.length, 1, 'request vẫn phải được gửi đi');
  assert.strictEqual(sandbox.eplHasApiToken(), false);
}

// --------------------------------------------------------------------------
// 2. showToast không nội suy nội dung vào innerHTML
// --------------------------------------------------------------------------

{
  const appSource = fs.readFileSync(
    path.join(__dirname, '..', 'js', 'app.js'),
    'utf8'
  );

  assert.ok(
    !appSource.includes('overflow-wrap:anywhere;">${cleanMessage}<'),
    'showToast không được nội suy cleanMessage vào innerHTML'
  );
  assert.ok(
    /toastBody\.textContent = cleanMessage/.test(appSource),
    'showToast phải đặt nội dung qua textContent'
  );
}

// --------------------------------------------------------------------------
// 3. Trang chủ không được chứa token, và CDN phải ghim phiên bản
// --------------------------------------------------------------------------

{
  const html = fs.readFileSync(
    path.join(__dirname, '..', 'index.html'),
    'utf8'
  );

  assert.ok(
    !html.includes('EPL_TMS_API_TOKEN'),
    'index.html không được chứa token API'
  );
  assert.ok(
    html.includes('api-auth.js'),
    'index.html phải nạp lớp bọc xác thực'
  );
  // Lớp bọc phải nạp trước app.js, nếu không các lệnh fetch sớm sẽ thiếu token.
  assert.ok(
    html.indexOf('api-auth.js') < html.indexOf('js/app.js'),
    'api-auth.js phải nạp trước app.js'
  );
  assert.ok(
    !/cdn\.jsdelivr\.net\/npm\/chart\.js["?]/.test(html),
    'chart.js phải ghim phiên bản tường minh'
  );
}

console.log('api-auth-security: tất cả kiểm tra đã qua');

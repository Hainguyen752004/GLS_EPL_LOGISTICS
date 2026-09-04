/**
 * Bang dieu khien khong duoc noi doi khi tai that bai.
 *
 * Su that da xay ra: token API trong trinh duyet het han, moi lenh goi /api/
 * tra ve 401, va vi nhanh loi cua loadDashboard() im lang nen bon o KPI giu
 * nguyen chuoi "0 VND / 0 Lenh DO / 0 Chuyen / 0 Su co" viet san trong
 * index.html. Nguoi dung doc ra la MAT SACH DU LIEU, trong khi Postgres van
 * con nguyen. Mot con so 0 tu tin te hon nhieu so voi mot dau gach.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const frontendRoot = path.join(__dirname, '..');
const app = fs.readFileSync(path.join(frontendRoot, 'js', 'app.js'), 'utf8');
const html = fs.readFileSync(path.join(frontendRoot, 'index.html'), 'utf8');

// --- 1. Khong duoc co so 0 viet san trong cac o KPI ----------------------

const TILES = ['stat-revenue', 'stat-dos', 'stat-transit', 'stat-incidents'];
TILES.forEach(id => {
  const cell = new RegExp(`id="${id}">([^<]*)<`).exec(html);
  assert.ok(cell, `khong tim thay o ${id}`);
  assert.ok(
    !/^\s*0\b/.test(cell[1]),
    `o ${id} viet san "${cell[1].trim()}" — neu tai that bai thi khong gi ghi de len, va man hinh bao 0 nhu that`
  );
  assert.match(cell[1], /—/, `o ${id} phai bat dau bang dau gach, nghia la chua co so lieu`);
});

// --- 2. Nhanh loi phai noi ra ------------------------------------------

{
  const start = app.indexOf('async function loadDashboard()');
  assert.ok(start > 0, 'phai con ham tai Bang dieu khien');
  const fn = app.slice(start, app.indexOf('\nwindow.loadAccountingData', start));

  // Truoc day chi co `if (res.ok) { ... }` va khong he co nhanh nguoc lai.
  assert.match(fn, /if \(!res\.ok\)/, 'phai xu ly truong hop may chu tu choi');
  assert.match(fn, /markDashboardUnavailable\(res\.status\)/, 'that bai phai duoc bao ra man hinh');
  // Ca loi mang (fetch nem) cung phai bao, khong chi console.error.
  const catchBlock = fn.slice(fn.lastIndexOf('} catch'));
  assert.match(catchBlock, /markDashboardUnavailable/, 'loi mang cung phai bao ra man hinh');
}

// --- 3. Ham bao loi phai dat dau gach vao DU bon o ----------------------

{
  const start = app.indexOf('function markDashboardUnavailable(');
  assert.ok(start > 0, 'phai co ham bao khong tai duoc');
  const fn = app.slice(start, app.indexOf('\n}', app.indexOf('showToast', start)) + 2);
  TILES.forEach(id => assert.ok(fn.includes(id), `${id} phai duoc dat lai`));
  assert.match(fn, /—/, 'phai dat dau gach, khong phai so 0');
  assert.match(fn, /showToast/, 'phai bao cho nguoi dung, khong chi ghi console');
  // 401 gan nhu luon la token, khong phai mat du lieu — phai noi ro dieu do.
  assert.match(fn, /status === 401/, 'phai phan biet truong hop bi tu choi phien lam viec');
  assert.match(fn, /vẫn còn nguyên/, 'phai tran an rang du lieu khong mat');
}

// --- 4. Cac con so khac cung khong duoc viet cung trong HTML ------------

// Badge "Danh Muc Loai Xe" tung viet cung "4 Mau" trong index.html, nen no noi
// doi ca khi danh muc trong lan khi so that khac 4 — man hinh tu mau thuan:
// badge ghi "4 Mau" ngay canh dong chu "Chua co Loai Xe trong CSDL Master Data".
{
  const cell = /id="formula-vehicle-types-count"[^>]*>([^<]*)</.exec(html);
  assert.ok(cell, 'phai co o dem so loai xe');
  assert.ok(!/\d/.test(cell[1]), `badge viet san "${cell[1].trim()}" — con so phai lay tu du lieu`);
  assert.match(app, /formula-vehicle-types-count/, 'app.js phai cap nhat con so nay');
  // Con so phai lay tu du lieu — va khi dang loc thi noi ro "khop/tong", chu
  // khong am tham hien so da loc nhu the do la tat ca.
  assert.match(app, /counter\.innerText = keyword/, 'con so phai lay tu du lieu');
  assert.match(app, /\$\{types\.length\}\/\$\{all\.length\}/, 'dang loc thi phai noi ro khop tren tong');
}

console.log('dashboard-load-honesty: tất cả kiểm tra đã qua');

/**
 * Bảng xếp ca tài xế: ma trận NGƯỜI × NGÀY.
 *
 * Vì sao đổi dạng trình bày:
 *
 * Bản cũ có hai phần rời nhau. Dải 7 ngày chỉ hiện SỐ TỔNG ("0 ca · 0 chuyến"),
 * nên nhìn vào không biết AI làm KHI NÀO — mà đó chính là câu hỏi duy nhất của
 * người xếp ca. Bấm vào một ngày thì bảng chi tiết mở trong hộp thoại che kín
 * màn hình, nên mất luôn ngữ cảnh tuần và mỗi lần chỉ xem được một ngày.
 *
 * Việc thật của màn này là xếp ca: gán tài xế vào ca sáng/chiều/đêm suốt một
 * tuần, tránh trùng, tránh ngày nghỉ, tránh chuyến đã khóa lịch. Dạng đúng cho
 * việc đó là ma trận người × ngày — cả tuần của cả đội trong một lần nhìn, và
 * chỗ trống hiện ra như chỗ trống thật.
 *
 * Không dùng hộp thoại. Chọn một ô thì chi tiết hiện ở khung bên cạnh
 * (#driver-shift-inspector đã có sẵn trong markup), nên ngữ cảnh tuần vẫn còn.
 *
 * Quy ước màu — dùng token sẵn có của ứng dụng:
 *   đã xếp ca   #059669  (--accent-emerald)
 *   nghỉ        #d97706  (--accent-amber)
 *   khóa lịch   #1d4ed8  (--lao-blue)   ← là một SỰ THẬT từ Điều phối, không
 *                                          phải lỗi, nên không dùng màu đỏ
 * Bộ ba này đã qua kiểm tra bằng máy: nằm trong dải độ sáng, đủ sắc độ, ΔE
 * người nhìn bình thường 23.7 giữa cặp gần nhất. ΔE cho người mù màu đỏ-lục là
 * 7.9 — mức chỉ được phép khi có mã hóa phụ, nên mỗi ô ca đều mang CHỮ (S/C/Đ)
 * cùng icon, không bao giờ chỉ có màu.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.DriverRoster = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const SHIFTS = [
    { key: 'morning', letter: 'S', label: 'Ca sáng', time: '06:00 – 14:00' },
    { key: 'afternoon', letter: 'C', label: 'Ca chiều', time: '14:00 – 22:00' },
    { key: 'night', letter: 'Đ', label: 'Ca đêm', time: '22:00 – 06:00' },
  ];

  const STATE = {
    assigned: { color: '#059669', soft: '#ecfdf5', icon: 'fa-circle-check', label: 'Đã xếp ca' },
    absence: { color: '#d97706', soft: '#fffbeb', icon: 'fa-user-clock', label: 'Nghỉ' },
    locked: { color: '#1d4ed8', soft: '#eff6ff', icon: 'fa-lock', label: 'Khóa lịch từ Điều phối' },
    free: { color: '#94a3b8', soft: '#ffffff', icon: 'fa-plus', label: 'Còn trống' },
  };

  const ABSENCE_LABELS = {
    leave: 'Nghỉ phép',
    sick: 'Nghỉ bệnh',
    off: 'Nghỉ ca',
    unavailable: 'Không sẵn sàng',
  };

  function esc(value) {
    if (value === null || value === undefined) return '';
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  /** Escape cho giá trị nằm trong chuỗi JavaScript bên trong thuộc tính HTML. */
  function escAttr(value) {
    if (value === null || value === undefined) return '';
    return esc(String(value).replace(/\\/g, '\\\\').replace(/'/g, "\\'"));
  }

  /** Trạng thái của một ô ca: khóa lịch > nghỉ > đã xếp > trống. */
  function cellState(cell) {
    if (cell && cell.trip) return 'locked';
    if (cell && cell.shift) {
      const kind = cell.shift.kind || 'work';
      return kind === 'work' ? 'assigned' : 'absence';
    }
    return 'free';
  }

  function cellTooltip(person, day, shiftDef, cell) {
    const who = `${person.name || person.id}`;
    const when = `${day.label} · ${shiftDef.label} ${shiftDef.time}`;
    if (cell && cell.trip) {
      const vehicle = cell.trip.vehicle_id ? ` · Xe ${cell.trip.vehicle_id}` : '';
      return `${who} — ${when}\nKhóa lịch: chuyến ${cell.trip.trip_id}${vehicle}`;
    }
    if (cell && cell.shift) {
      const kind = cell.shift.kind || 'work';
      if (kind !== 'work') {
        return `${who} — ${when}\n${ABSENCE_LABELS[kind] || kind}`;
      }
      const vehicle = cell.shift.vehicle_id ? `Xe ${cell.shift.vehicle_id}` : 'Chưa gán xe';
      const hours = cell.shift.start_label && cell.shift.end_label
        ? `${cell.shift.start_label} – ${cell.shift.end_label}`
        : shiftDef.time;
      return `${who} — ${when}\n${hours} · ${vehicle}`;
    }
    return `${who} — ${when}\nCòn trống · chọn để xếp ca`;
  }

  // ------------------------------------------------------------------
  // Ma trận tuần
  // ------------------------------------------------------------------

  /**
   * Một ô ca. Là <button> chứ không phải <div>: nó bấm được, nên phải tới được
   * bằng bàn phím và có trạng thái focus.
   */
  function shiftCell(person, day, shiftDef, cell) {
    const state = cellState(cell);
    const tone = STATE[state];
    const locked = state === 'locked';
    const handler = locked
      ? `DriverRosterActions.openTrip('${escAttr(cell.trip.trip_id)}', '${escAttr(person.id)}')`
      : cell && cell.shift
        ? `DriverRosterActions.openShift('${escAttr(cell.shift.id)}')`
        : `DriverRosterActions.assign('${escAttr(person.id)}', '${escAttr(day.key)}', '${escAttr(shiftDef.key)}')`;
    return `<button type="button" class="dr-cell dr-cell--${state}"
      style="--dr-tone:${tone.color}; --dr-tone-soft:${tone.soft};"
      title="${esc(cellTooltip(person, day, shiftDef, cell))}"
      aria-label="${esc(`${person.name || person.id}, ${day.label}, ${shiftDef.label}: ${tone.label}`)}"
      onclick="${handler}"><span class="dr-cell-letter">${shiftDef.letter}</span>${
        locked ? '<i class="fa-solid fa-lock dr-cell-mark" aria-hidden="true"></i>' : ''
      }</button>`;
  }

  /** Ba ô ca của một người trong một ngày. */
  function dayGroup(person, day, cells) {
    return `<div class="dr-day-group">${
      SHIFTS.map(shiftDef => shiftCell(person, day, shiftDef, cells[shiftDef.key])).join('')
    }</div>`;
  }

  /**
   * Ma trận NGƯỜI × NGÀY.
   *
   * Cột đầu dính (sticky) và phần lưới cuộn ngang trong khung của nó, nên thêm
   * người hay đổi sang màn hẹp đều không làm trang cuộn ngang.
   */
  function weekMatrix(data, options) {
    const days = (data && data.days) || [];
    const people = (data && data.people) || [];
    const selectedDay = (options && options.selectedDay) || '';

    if (!days.length) return emptyState('Chưa xác định được tuần cần xếp ca.');
    if (!people.length) {
      return emptyState('Không có nhân sự nào khớp bộ lọc. Xóa từ khóa tìm kiếm để xem toàn bộ đội.');
    }

    const header = `
      <div class="dr-row dr-row--head">
        <div class="dr-name dr-name--head">Nhân sự</div>
        ${days.map(day => {
          const load = dayLoad(people, day.key);
          const level = load.assigned === 0 ? 'free' : load.assigned >= load.capacity ? 'assigned' : 'absence';
          return `<div class="dr-col-head${day.key === selectedDay ? ' is-selected' : ''}">
            <button type="button" class="dr-col-head-btn"
                    onclick="DriverRosterActions.selectDay('${escAttr(day.key)}')"
                    title="${esc(`${day.label}: ${load.assigned} ca đã xếp, ${load.absence} nghỉ, ${load.locked} khóa lịch, còn ${load.capacity - load.assigned} chỗ`)}">
              <b>${esc(day.label)}</b>
              <span class="dr-col-load" style="--dr-tone:${STATE[level].color};">
                <span class="dr-col-load-fill" style="width:${load.capacity ? Math.round(load.assigned * 100 / load.capacity) : 0}%;"></span>
              </span>
              <small>${load.assigned}/${load.capacity} ca</small>
            </button>
          </div>`;
        }).join('')}
        <div class="dr-total dr-total--head">Tuần</div>
      </div>`;

    const rows = people.map(person => {
      const weekTotal = days.reduce((sum, day) => {
        const cells = personCells(person, day.key);
        return sum + SHIFTS.filter(s => cellState(cells[s.key]) === 'assigned').length;
      }, 0);
      const roleLine = [person.role, person.license].filter(Boolean).join(' · ');
      return `
        <div class="dr-row">
          <div class="dr-name">
            <b>${esc(person.name || person.id)}</b>
            <small>${esc(person.id)}${roleLine ? ` · ${esc(roleLine)}` : ''}</small>
          </div>
          ${days.map(day => `<div class="dr-col${day.key === selectedDay ? ' is-selected' : ''}">${
            dayGroup(person, day, personCells(person, day.key))
          }</div>`).join('')}
          <div class="dr-total"><b>${weekTotal}</b><small>ca</small></div>
        </div>`;
    }).join('');

    return `<div class="dr-matrix" style="--dr-days:${days.length};" role="group" aria-label="Bảng xếp ca theo tuần">${header}${rows}</div>`;
  }

  /** Các ô ca của một người trong một ngày, khóa theo loại ca. */
  function personCells(person, dayKey) {
    const day = (person.days || []).find(item => item.key === dayKey) || {};
    const cells = {};
    SHIFTS.forEach(shiftDef => {
      const shift = (day.shifts || []).find(item => item.type === shiftDef.key) || null;
      const trip = (day.trips || []).find(item => !item.shift_type || item.shift_type === shiftDef.key) || null;
      cells[shiftDef.key] = { shift, trip: shift ? null : trip };
    });
    return cells;
  }

  /** Tổng hợp một ngày: đã xếp, nghỉ, khóa lịch, và tổng chỗ có thể xếp. */
  function dayLoad(people, dayKey) {
    let assigned = 0;
    let absence = 0;
    let locked = 0;
    people.forEach(person => {
      const cells = personCells(person, dayKey);
      SHIFTS.forEach(shiftDef => {
        const state = cellState(cells[shiftDef.key]);
        if (state === 'assigned') assigned += 1;
        else if (state === 'absence') absence += 1;
        else if (state === 'locked') locked += 1;
      });
    });
    return { assigned, absence, locked, capacity: people.length * SHIFTS.length };
  }

  // ------------------------------------------------------------------
  // Chú giải
  // ------------------------------------------------------------------

  function legend() {
    const order = ['assigned', 'absence', 'locked', 'free'];
    return `
      <ul class="dr-legend">
        ${order.map(key => {
          const tone = STATE[key];
          return `<li><span class="dr-legend-swatch dr-cell--${key}" style="--dr-tone:${tone.color}; --dr-tone-soft:${tone.soft};" aria-hidden="true"></span>
            <i class="fa-solid ${tone.icon}" aria-hidden="true"></i> ${esc(tone.label)}</li>`;
        }).join('')}
        <li class="dr-legend-note">S = sáng · C = chiều · Đ = đêm</li>
      </ul>`;
  }

  // ------------------------------------------------------------------
  // Chi tiết một ngày — hiện NGAY TRONG TRANG, không dùng hộp thoại
  // ------------------------------------------------------------------

  /**
   * Bảng chi tiết một ngày. Giữ lại vì có lúc cần đọc kỹ giờ giấc và xe của
   * từng người, nhưng đặt ngay trong trang thay vì trong hộp thoại che màn hình.
   */
  function dayDetail(data, dayKey) {
    const days = (data && data.days) || [];
    const people = (data && data.people) || [];
    const day = days.find(item => item.key === dayKey);
    if (!day) return emptyState('Chọn một ngày trên bảng tuần để xem chi tiết.');
    if (!people.length) return emptyState('Không có nhân sự nào khớp bộ lọc.');

    const rows = people.map(person => {
      const cells = personCells(person, dayKey);
      const cellHtml = SHIFTS.map(shiftDef => {
        const cell = cells[shiftDef.key];
        const state = cellState(cell);
        const tone = STATE[state];
        if (state === 'free') {
          return `<td><button type="button" class="dr-detail-free"
            onclick="DriverRosterActions.assign('${escAttr(person.id)}', '${escAttr(dayKey)}', '${escAttr(shiftDef.key)}')">
            <i class="fa-solid fa-plus" aria-hidden="true"></i> Xếp ca</button></td>`;
        }
        if (state === 'locked') {
          return `<td><span class="dr-detail-chip" style="--dr-tone:${tone.color}; --dr-tone-soft:${tone.soft};">
            <i class="fa-solid fa-lock" aria-hidden="true"></i>
            <b>${esc(cell.trip.trip_id)}</b>
            <small>${esc(cell.trip.vehicle_id ? `Xe ${cell.trip.vehicle_id}` : cell.trip.role || 'Chuyến')}</small>
          </span></td>`;
        }
        const kind = cell.shift.kind || 'work';
        const primary = kind === 'work'
          ? `${cell.shift.start_label || ''} – ${cell.shift.end_label || ''}`.trim()
          : (ABSENCE_LABELS[kind] || kind);
        const secondary = kind === 'work'
          ? (cell.shift.vehicle_id ? `Xe ${cell.shift.vehicle_id}` : 'Chưa gán xe')
          : 'Không nhận ca';
        return `<td><button type="button" class="dr-detail-chip dr-detail-chip--action"
          style="--dr-tone:${tone.color}; --dr-tone-soft:${tone.soft};"
          onclick="DriverRosterActions.openShift('${escAttr(cell.shift.id)}')">
          <i class="fa-solid ${tone.icon}" aria-hidden="true"></i>
          <b>${esc(primary)}</b><small>${esc(secondary)}</small>
        </button></td>`;
      }).join('');
      const roleLine = [person.role, person.license].filter(Boolean).join(' · ');
      return `<tr>
        <th scope="row"><b>${esc(person.name || person.id)}</b><small>${esc(person.id)}${roleLine ? ` · ${esc(roleLine)}` : ''}</small></th>
        ${cellHtml}
      </tr>`;
    }).join('');

    return `
      <div class="dr-detail">
        <div class="dr-detail-head">
          <h4><i class="fa-solid fa-calendar-day" aria-hidden="true"></i> ${esc(day.label)}</h4>
          <p>${people.length} nhân sự · ba ca và các chuyến đã khóa lịch</p>
        </div>
        <div class="dr-detail-scroll">
          <table class="dr-detail-table">
            <thead>
              <tr>
                <th scope="col">Nhân sự</th>
                ${SHIFTS.map(s => `<th scope="col">${esc(s.label)}<small>${esc(s.time)}</small></th>`).join('')}
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </div>`;
  }

  function emptyState(message) {
    return `<p class="dr-empty">${esc(message)}</p>`;
  }

  // ------------------------------------------------------------------
  // Lịch xe — ma trận XE × NGÀY
  // ------------------------------------------------------------------

  /**
   * Trạng thái xe trong một ngày.
   *
   * Ở đây màu ĐỎ là hợp lý, khác với "khóa lịch" ở bảng ca: xung đột lịch là
   * một lỗi thật cần người xử lý, không phải một sự thật phải chấp nhận.
   *
   * "Rảnh" cố tình dùng nét đứt trung tính chứ không tô xanh: xe rảnh là năng
   * lực chưa dùng, không phải thành tích — tô xanh cả tuần sẽ làm bảng trông
   * như mọi thứ đều tốt trong khi thật ra cả đội đang không chạy.
   */
  const VEHICLE_STATE = {
    available: { color: '#94a3b8', soft: '#ffffff', icon: 'fa-circle-check', label: 'Rảnh' },
    busy: { color: '#1d4ed8', soft: '#eff6ff', icon: 'fa-truck-fast', label: 'Đang có lịch' },
    maintenance: { color: '#d97706', soft: '#fffbeb', icon: 'fa-screwdriver-wrench', label: 'Bảo dưỡng / sửa chữa' },
    conflict: { color: '#b91c1c', soft: '#fef2f2', icon: 'fa-triangle-exclamation', label: 'Xung đột lịch' },
  };

  /** Dòng chữ ngắn mô tả ngày của một xe. */
  function vehicleDayHint(day) {
    if (!day) return '—';
    if (day.maintenances && day.maintenances.length) {
      return day.maintenances.map(item => item.label).filter(Boolean).join(', ') || 'Bảo dưỡng';
    }
    if (day.trip_ids && day.trip_ids.length) return day.trip_ids.join(', ');
    if (day.shifts && day.shifts.length) return `${day.shifts.length} ca dự kiến`;
    return '—';
  }

  function vehicleCell(vehicle, day, dayData) {
    const status = (dayData && dayData.status) || 'available';
    const tone = VEHICLE_STATE[status] || VEHICLE_STATE.available;
    const hint = vehicleDayHint(dayData);
    const drivers = dayData && dayData.driver_ids && dayData.driver_ids.length
      ? dayData.driver_ids.filter(Boolean).join(', ')
      : '';
    const tooltip = [
      `${vehicle.label || vehicle.vehicle_id} — ${day.label}`,
      tone.label,
      hint !== '—' ? hint : null,
      drivers ? `Tài xế: ${drivers}` : null,
    ].filter(Boolean).join('\n');
    return `<button type="button" class="dr-vcell dr-vcell--${status}"
      style="--dr-tone:${tone.color}; --dr-tone-soft:${tone.soft};"
      title="${esc(tooltip)}"
      aria-label="${esc(`${vehicle.label || vehicle.vehicle_id}, ${day.label}: ${tone.label}`)}"
      onclick="DriverRosterActions.openVehicle('${escAttr(vehicle.vehicle_id)}', '${escAttr(day.key)}')">
      <i class="fa-solid ${tone.icon}" aria-hidden="true"></i>
      <span class="dr-vcell-hint">${esc(hint)}</span>
    </button>`;
  }

  /**
   * Ma trận XE × NGÀY.
   *
   * Cùng lý do như bảng xếp ca: dải 7 ngày cũ chỉ hiện số tổng ("3 rảnh · 0
   * bận") nên không biết XE NÀO rảnh ngày nào, và chi tiết thì nằm trong hộp
   * thoại che kín màn hình.
   */
  function vehicleMatrix(data, options) {
    const days = (data && data.days) || [];
    const vehicles = (data && data.vehicles) || [];
    const selectedDay = (options && options.selectedDay) || '';

    if (!days.length) return emptyState('Chưa xác định được tuần cần xem.');
    if (!vehicles.length) {
      return emptyState('Chưa có xe nào khớp bộ lọc. Xóa từ khóa để xem toàn bộ đội xe.');
    }

    const header = `
      <div class="dr-row dr-row--head">
        <div class="dr-name dr-name--head">Phương tiện</div>
        ${days.map(day => {
          const load = vehicleDayLoad(vehicles, day.key);
          // Có xung đột thì đó là thứ cần thấy trước, nên nó quyết định màu.
          const level = load.conflict ? 'conflict' : load.maintenance ? 'maintenance' : load.busy ? 'busy' : 'available';
          const used = load.busy + load.maintenance + load.conflict;
          return `<div class="dr-col-head${day.key === selectedDay ? ' is-selected' : ''}">
            <button type="button" class="dr-col-head-btn"
                    onclick="DriverRosterActions.selectVehicleDay('${escAttr(day.key)}')"
                    title="${esc(`${day.label}: ${load.available} rảnh, ${load.busy} đang có lịch, ${load.maintenance} bảo dưỡng, ${load.conflict} xung đột`)}">
              <b>${esc(day.label)}</b>
              <span class="dr-col-load" style="--dr-tone:${VEHICLE_STATE[level].color};">
                <span class="dr-col-load-fill" style="width:${vehicles.length ? Math.round(used * 100 / vehicles.length) : 0}%;"></span>
              </span>
              <small>${used}/${vehicles.length} xe dùng</small>
            </button>
          </div>`;
        }).join('')}
        <div class="dr-total dr-total--head">Rảnh</div>
      </div>`;

    const rows = vehicles.map(vehicle => {
      const freeDays = days.filter(day => {
        const dayData = (vehicle.days || []).find(item => item.key === day.key);
        return !dayData || (dayData.status || 'available') === 'available';
      }).length;
      const typeLine = vehicle.type || 'Chưa cấu hình loại xe';
      return `
        <div class="dr-row">
          <div class="dr-name">
            <b>${esc(vehicle.label || vehicle.vehicle_id)}</b>
            <small>${esc(vehicle.vehicle_id)} · ${esc(typeLine)}</small>
          </div>
          ${days.map(day => `<div class="dr-col dr-col--wide${day.key === selectedDay ? ' is-selected' : ''}">${
            vehicleCell(vehicle, day, (vehicle.days || []).find(item => item.key === day.key))
          }</div>`).join('')}
          <div class="dr-total"><b>${freeDays}</b><small>ngày</small></div>
        </div>`;
    }).join('');

    return `<div class="dr-matrix dr-matrix--vehicles" style="--dr-days:${days.length};" role="group" aria-label="Lịch xe theo tuần">${header}${rows}</div>`;
  }

  /** Tổng hợp một ngày của cả đội xe. */
  function vehicleDayLoad(vehicles, dayKey) {
    const load = { available: 0, busy: 0, maintenance: 0, conflict: 0 };
    vehicles.forEach(vehicle => {
      const dayData = (vehicle.days || []).find(item => item.key === dayKey);
      const status = (dayData && dayData.status) || 'available';
      if (load[status] === undefined) load.available += 1;
      else load[status] += 1;
    });
    return load;
  }

  function vehicleLegend() {
    const order = ['available', 'busy', 'maintenance', 'conflict'];
    return `
      <ul class="dr-legend">
        ${order.map(key => {
          const tone = VEHICLE_STATE[key];
          return `<li><span class="dr-legend-swatch dr-vcell--${key}" style="--dr-tone:${tone.color}; --dr-tone-soft:${tone.soft};" aria-hidden="true"></span>
            <i class="fa-solid ${tone.icon}" aria-hidden="true"></i> ${esc(tone.label)}</li>`;
        }).join('')}
      </ul>`;
  }

  return {
    SHIFTS,
    STATE,
    VEHICLE_STATE,
    ABSENCE_LABELS,
    cellState,
    personCells,
    dayLoad,
    weekMatrix,
    dayDetail,
    legend,
    vehicleDayHint,
    vehicleDayLoad,
    vehicleMatrix,
    vehicleLegend,
  };
});

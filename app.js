const DATA_KEY = 'little-days-events-v1';
const SETTINGS_KEY = 'little-days-settings-v1';
const SESSION_KEY = 'little-days-session-v1';
const $ = selector => document.querySelector(selector);
let events = load(DATA_KEY, []);
let settings = load(SETTINGS_KEY, { babyName: '', url: '', key: '' });
let session = load(SESSION_KEY, null);
let activeType = '';

function load(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; }
}
function saveEvents() { localStorage.setItem(DATA_KEY, JSON.stringify(events)); }
function saveSettings() { localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings)); }
function localDate(date = new Date()) {
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}
function parseDate(value) { return new Date(value); }
function sameDay(a, b = new Date()) { return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate(); }
function timeLabel(value) { return parseDate(value).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }); }
function dateLabel(value) { return parseDate(value).toLocaleDateString([], { month: 'short', day: 'numeric' }); }
function durationLabel(minutes) {
  const safe = Math.max(0, Math.round(minutes));
  return safe >= 60 ? `${Math.floor(safe / 60)}h ${safe % 60}m` : `${safe}m`;
}
function esc(value = '') {
  return String(value).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
}
function sorted(list = events) { return [...list].sort((a, b) => new Date(b.at) - new Date(a.at)); }
function todayEvents() { return events.filter(item => sameDay(parseDate(item.at))); }
function fmtAmount(item) {
  const bits = [];
  if (item.method) bits.push(item.method);
  if (item.side) bits.push(item.side);
  if (item.minutes) bits.push(`${item.minutes} min`);
  if (item.volume) bits.push(`${item.volume} ml`);
  return bits.join(' · ');
}
function titleFor(item) {
  if (item.type === 'feed') return 'Feed';
  if (item.type === 'sleep') return item.end ? 'Sleep' : 'Sleep started';
  if (item.type === 'diaper') return `${item.change} diaper`;
  if (item.type === 'note') return 'Note';
  if (item.type === 'growth') return 'Weight recorded';
  return 'Moment';
}
function detailFor(item) {
  if (item.type === 'feed') return fmtAmount(item) || 'Feed logged';
  if (item.type === 'sleep') return item.end ? durationLabel((new Date(item.end) - parseDate(item.at)) / 60000) : 'Still sleeping';
  if (item.type === 'diaper') return item.change === 'Both' ? 'Wet + dirty' : item.change;
  if (item.type === 'note') return item.text || '';
  if (item.type === 'growth') return `${item.weight} ${item.unit}`;
  return '';
}
function iconFor(item) { return ({ feed: '＋', sleep: '◷', diaper: '✳', note: '✎', growth: '↗' })[item.type] || '·'; }

function render() {
  $('#today-date').textContent = new Date().toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' });
  $('#baby-heading').textContent = settings.babyName || 'Your little one';
  const day = todayEvents();
  const feedCount = day.filter(item => item.type === 'feed').length;
  const dayStart = new Date().setHours(0, 0, 0, 0);
  const dayEnd = dayStart + 86400000;
  const sleepMs = events.filter(item => item.type === 'sleep').reduce((sum, item) => {
    const start = parseDate(item.at).getTime();
    const end = item.end ? parseDate(item.end).getTime() : Date.now();
    return sum + Math.max(0, Math.min(end, dayEnd) - Math.max(start, dayStart));
  }, 0);
  const ongoing = events.find(item => item.type === 'sleep' && !item.end);
  const sleepHours = sleepMs / 3600000;
  const diapers = day.filter(item => item.type === 'diaper').length;
  $('#summary').innerHTML = [
    ['Feeds today', feedCount, 'feed-icon', '＋'],
    ['Sleep today', sleepHours ? `${sleepHours.toFixed(1)}<span class="unit">hrs</span>` : `0<span class="unit">hrs</span>`, 'sleep-icon', '◷'],
    ['Diapers today', diapers, 'diaper-icon', '✳']
  ].map(([label, value, icon, glyph]) => `<article class="stat"><div><p class="eyebrow">${label}</p><div class="value">${value}</div></div><span class="stat-icon ${icon}">${glyph}</span></article>`).join('');
  $('#sleep-label').textContent = ongoing ? 'End sleep' : 'Start sleep';
  $('#sleep-detail').textContent = ongoing ? `Since ${timeLabel(ongoing.at)}` : 'Log a nap';
  const recent = sorted(day).slice(0, 6);
  $('#today-list').innerHTML = recent.length ? recent.map(item => `<article class="timeline-row"><time class="time">${timeLabel(item.at)}</time><span class="marker"></span><div class="copy"><b>${esc(titleFor(item))}</b><p>${esc(detailFor(item))}</p></div></article>`).join('') : '<div class="empty">Nothing logged yet today. Start with whatever just happened.</div>';
  renderHistory();
  renderProgress();
  updateCloudStatus();
}

function renderHistory() {
  const filter = $('#filter').value;
  const rows = sorted().filter(item => filter === 'all' || item.type === filter);
  $('#history-list').innerHTML = rows.length ? rows.map(item => `<article class="history-row"><time class="time">${dateLabel(item.at)}<br>${timeLabel(item.at)}</time><span class="marker">${iconFor(item)}</span><div class="copy"><b>${esc(titleFor(item))}</b><p>${esc(detailFor(item))}</p></div><button class="delete" data-delete="${esc(item.id)}" title="Delete entry" aria-label="Delete ${esc(titleFor(item))}">×</button></article>`).join('') : '<div class="empty">No moments here yet.</div>';
}

function renderProgress() {
  const today = new Date();
  const days = Array.from({ length: 7 }, (_, index) => {
    const day = new Date(today.getFullYear(), today.getMonth(), today.getDate() - (6 - index));
    const start = day.getTime();
    const end = start + 86400000;
    const logs = events.filter(item => parseDate(item.at) >= start && parseDate(item.at) < end);
    const feeds = logs.filter(item => item.type === 'feed').length;
    const sleepMs = events.filter(item => item.type === 'sleep').reduce((sum, item) => {
      const a = parseDate(item.at).getTime();
      const b = item.end ? parseDate(item.end).getTime() : Date.now();
      return sum + Math.max(0, Math.min(b, end) - Math.max(a, start));
    }, 0);
    return { day, feeds, hours: sleepMs / 3600000 };
  });
  const maxFeeds = Math.max(1, ...days.map(item => item.feeds));
  const maxSleep = Math.max(1, ...days.map(item => item.hours));
  $('#chart').innerHTML = days.map(item => `<div class="chart-day"><div class="bars"><span class="bar" title="${item.feeds} feeds" style="height:${Math.max(3, item.feeds / maxFeeds * 100)}%"></span><span class="bar sleeper" title="${item.hours.toFixed(1)} hours sleep" style="height:${Math.max(3, item.hours / maxSleep * 100)}%"></span></div><span class="chart-label">${item.day.toLocaleDateString([], { weekday: 'narrow' })}</span></div>`).join('');
  const weights = sorted().filter(item => item.type === 'growth');
  $('#weights').innerHTML = weights.length ? weights.map(item => `<div class="weight-row"><b>${esc(item.weight)} ${esc(item.unit)}</b><span>${dateLabel(item.at)}</span></div>`).join('') : '<div class="empty">Weight notes you add will appear here.</div>';
}

const input = (label, name, type = 'text', value = '', attrs = '') => `<label class="field">${label}<input name="${name}" type="${type}" value="${esc(value)}" ${attrs}></label>`;
const select = (label, name, options) => `<label class="field">${label}<select name="${name}">${options.map(([value, text]) => `<option value="${value}">${text}</option>`).join('')}</select></label>`;
function openEntry(type, extra = {}) {
  activeType = type;
  const now = localDate();
  const fields = {
    feed: `<div class="field"><span>How did baby feed?</span><div class="choices"><label class="choice"><input type="radio" name="method" value="Breast" checked><span>Breast</span></label><label class="choice"><input type="radio" name="method" value="Bottle"><span>Bottle</span></label><label class="choice"><input type="radio" name="method" value="Mixed"><span>Mixed</span></label></div></div><div class="row">${select('Side', 'side', [['', 'Not noted'], ['Left', 'Left'], ['Right', 'Right'], ['Both', 'Both']])}${input('Duration (minutes)', 'minutes', 'number', '', 'min="0" max="300" placeholder="Optional"')}</div><div class="row">${input('Bottle amount (ml)', 'volume', 'number', '', 'min="0" max="2000" placeholder="Optional"')}${input('Time', 'at', 'datetime-local', now, 'required')}</div>`,
    sleep: `<div class="row">${input('Started', 'at', 'datetime-local', extra.at || now, 'required')}${extra.end ? input('Woke up', 'end', 'datetime-local', now, 'required') : '<div></div>'}</div>`,
    diaper: `<div class="field"><span>Change</span><div class="choices"><label class="choice"><input type="radio" name="change" value="Wet" checked><span>Wet</span></label><label class="choice"><input type="radio" name="change" value="Dirty"><span>Dirty</span></label><label class="choice"><input type="radio" name="change" value="Both"><span>Both</span></label></div></div>${input('Time', 'at', 'datetime-local', now, 'required')}`,
    note: `<label class="field">A little detail<textarea name="text" rows="3" placeholder="A new sound, a sweet moment, something to remember…"></textarea></label>${input('Time', 'at', 'datetime-local', now, 'required')}`,
    growth: `<div class="row">${input('Weight', 'weight', 'number', '', 'min="0" step="0.001" placeholder="e.g. 3.6" required')}${select('Unit', 'unit', [['kg', 'kg'], ['lb', 'lb']])}</div>${input('Date', 'at', 'datetime-local', now, 'required')}`
  };
  const titles = { feed: 'Log a feed', sleep: extra.end ? 'End sleep' : 'Start sleep', diaper: 'Log a diaper', note: 'Add a note', growth: 'Add a weight note' };
  $('#entry-title').textContent = titles[type];
  $('#fields').innerHTML = fields[type];
  $('#entry-dialog').showModal();
}

async function persist() {
  saveEvents();
  render();
  if (session) {
    try { await syncEvents(); }
    catch (error) { setCloudMessage(`Saved on this device. Sync paused: ${error.message}`, true); }
  }
}
function entryFromForm(form) {
  const data = new FormData(form);
  const entry = { id: crypto.randomUUID(), type: activeType, at: data.get('at') ? new Date(data.get('at')).toISOString() : new Date().toISOString() };
  if (activeType === 'feed') {
    entry.method = data.get('method'); entry.side = data.get('side');
    if (data.get('minutes')) entry.minutes = Number(data.get('minutes'));
    if (data.get('volume')) entry.volume = Number(data.get('volume'));
  } else if (activeType === 'sleep' && data.get('end')) {
    entry.end = new Date(data.get('end')).toISOString();
    if (new Date(entry.end) <= new Date(entry.at)) throw new Error('Wake time must be after sleep started.');
  } else if (activeType === 'diaper') entry.change = data.get('change');
  else if (activeType === 'note') entry.text = data.get('text').trim();
  else if (activeType === 'growth') { entry.weight = Number(data.get('weight')); entry.unit = data.get('unit'); }
  return entry;
}

function apiHeaders(token = session?.access_token) {
  return { apikey: settings.key, Authorization: `Bearer ${token || settings.key}`, 'Content-Type': 'application/json' };
}
async function authRequest(path, body) {
  const response = await fetch(`${settings.url.replace(/\/$/, '')}/auth/v1/${path}`, { method: 'POST', headers: apiHeaders(null), body: JSON.stringify(body) });
  const result = await response.json();
  if (!response.ok) throw new Error(result.msg || result.message || result.error_description || result.error || 'Authentication failed.');
  return result;
}
function setSession(value) {
  session = value;
  localStorage.setItem(SESSION_KEY, JSON.stringify(value));
  $('#sign-in').classList.toggle('hidden', Boolean(value));
  $('#sign-up').classList.toggle('hidden', Boolean(value));
  $('#sign-out').classList.toggle('hidden', !value);
}
function setCloudMessage(text, isError = false) {
  $('#cloud-message').textContent = text;
  $('#cloud-message').classList.toggle('error', isError);
}
function updateCloudStatus() {
  const status = $('#sync-status');
  status.classList.toggle('on', Boolean(session));
  status.textContent = session ? 'Synced family log' : settings.url && settings.key ? 'Sign in to sync' : 'On this device';
  const dot = document.createElement('i'); status.prepend(dot);
}
async function refreshSession() {
  if (!session?.refresh_token) throw new Error('Please sign in again to reconnect.');
  const next = await authRequest('token?grant_type=refresh_token', { refresh_token: session.refresh_token });
  setSession(next);
}
async function dataRequest(path, options = {}, retry = true) {
  const response = await fetch(`${settings.url.replace(/\/$/, '')}/rest/v1/${path}`, { ...options, headers: { ...apiHeaders(), ...(options.headers || {}) } });
  if (response.status === 401 && retry) { await refreshSession(); return dataRequest(path, options, false); }
  if (!response.ok) { const message = await response.text(); throw new Error(message.slice(0, 220) || `Sync failed (${response.status}).`); }
  return response.status === 204 ? null : response.json();
}
async function syncEvents() {
  if (!session?.user?.id) return;
  const headers = { Prefer: 'resolution=merge-duplicates,return=minimal' };
  for (let offset = 0; offset < events.length; offset += 100) {
    const batch = events.slice(offset, offset + 100).map(({ id, ...payload }) => ({ id, payload }));
    if (batch.length) await dataRequest('baby_events?on_conflict=id', { method: 'POST', headers, body: JSON.stringify(batch) });
  }
  const remote = await dataRequest(`baby_events?select=id,payload&user_id=eq.${encodeURIComponent(session.user.id)}`);
  const byId = new Map(events.map(item => [item.id, item]));
  for (const row of remote) if (row.payload) byId.set(row.id, { ...row.payload, id: row.id });
  events = [...byId.values()];
  saveEvents(); render();
}
function updateSettingsForm() {
  $('#baby-name').value = settings.babyName;
  $('#project-url').value = settings.url;
  $('#project-key').value = settings.key;
  setSession(session);
}

document.addEventListener('click', async event => {
  const action = event.target.closest('[data-action]');
  if (action) {
    if (action.dataset.action === 'sleep') {
      const current = events.find(item => item.type === 'sleep' && !item.end);
      if (current) openEntry('sleep', { at: localDate(parseDate(current.at)), end: true });
      else { const entry = { id: crypto.randomUUID(), type: 'sleep', at: new Date().toISOString() }; events.push(entry); await persist(); }
    } else openEntry(action.dataset.action);
    return;
  }
  const tab = event.target.closest('[data-view]');
  if (tab) {
    document.querySelectorAll('.tab').forEach(item => item.classList.toggle('active', item === tab));
    document.querySelectorAll('.view').forEach(item => item.classList.toggle('hidden', item.id !== `${tab.dataset.view}-view`));
  }
  const goto = event.target.closest('[data-goto]');
  if (goto) document.querySelector(`[data-view="${goto.dataset.goto}"]`).click();
  const close = event.target.closest('[data-close]');
  if (close) close.closest('dialog').close();
  const remove = event.target.closest('[data-delete]');
  if (remove && confirm('Delete this moment from the log?')) {
    events = events.filter(item => item.id !== remove.dataset.delete);
    await persist();
    if (session) {
      try { await dataRequest(`baby_events?id=eq.${encodeURIComponent(remove.dataset.delete)}&user_id=eq.${encodeURIComponent(session.user.id)}`, { method: 'DELETE' }); }
      catch (error) { setCloudMessage(`Deleted here, but sync failed: ${error.message}`, true); }
    }
  }
});

$('#entry-form').addEventListener('submit', async event => {
  event.preventDefault();
  try {
    const entry = entryFromForm(event.currentTarget);
    if (activeType === 'sleep' && entry.end) {
      const current = events.find(item => item.type === 'sleep' && !item.end);
      if (current) current.end = entry.end;
      else events.push(entry);
    } else events.push(entry);
    $('#entry-dialog').close();
    await persist();
  } catch (error) { alert(error.message); }
});

$('#settings-open').addEventListener('click', () => { updateSettingsForm(); $('#settings-dialog').showModal(); });
$('#settings-form').addEventListener('submit', event => {
  event.preventDefault();
  settings = { babyName: $('#baby-name').value.trim(), url: $('#project-url').value.trim(), key: $('#project-key').value.trim() };
  saveSettings(); render(); $('#settings-dialog').close();
});
$('#sign-in').addEventListener('click', async () => {
  try {
    settings.url = $('#project-url').value.trim(); settings.key = $('#project-key').value.trim(); saveSettings();
    const result = await authRequest('token?grant_type=password', { email: $('#email').value.trim(), password: $('#password').value });
    setSession(result); await syncEvents(); setCloudMessage('Connected. This account can be used on both caregivers’ devices.'); render();
  } catch (error) { setCloudMessage(error.message, true); }
});
$('#sign-up').addEventListener('click', async () => {
  try {
    settings.url = $('#project-url').value.trim(); settings.key = $('#project-key').value.trim(); saveSettings();
    const result = await authRequest('signup', { email: $('#email').value.trim(), password: $('#password').value });
    if (result.access_token) { setSession(result); await syncEvents(); setCloudMessage('Account ready. Sign in on the other caregiver’s device with this family account.'); }
    else setCloudMessage('Check your email to confirm the account, then sign in here.');
  } catch (error) { setCloudMessage(error.message, true); }
});
$('#sign-out').addEventListener('click', () => { setSession(null); render(); setCloudMessage('Signed out. This browser still has its local copy.'); });
$('#filter').addEventListener('change', renderHistory);
$('#add-weight').addEventListener('click', () => openEntry('growth'));
$('#export').addEventListener('click', () => {
  const blob = new Blob([JSON.stringify({ babyName: settings.babyName, exportedAt: new Date().toISOString(), events }, null, 2)], { type: 'application/json' });
  const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = 'little-days-export.json'; link.click(); URL.revokeObjectURL(link.href);
});
window.addEventListener('online', () => { if (session) syncEvents().catch(error => setCloudMessage(error.message, true)); });

updateSettingsForm();
render();
if (session && settings.url && settings.key) syncEvents().catch(error => { setCloudMessage(error.message, true); $('#settings-dialog').showModal(); });
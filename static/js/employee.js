const cameraInput = document.getElementById('camera-input');
const finalPhotoInput = document.getElementById('final-photo-input');
const queueKey = 'upstage_offline_queue_v1';
let pendingAction = null;

function showResult(message, kind='success') {
  const box = document.getElementById('event-result');
  box.className = `alert ${kind}`;
  box.textContent = message;
}

function updateQueueLabel(){
  const items = JSON.parse(localStorage.getItem(queueKey) || '[]');
  const label = document.getElementById('offline-queue-size');
  if(label) label.textContent = `${items.length} pending offline action(s)`;
}

async function getLocation() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) return resolve({ lat: null, lng: null, address: 'GPS unavailable' });
    navigator.geolocation.getCurrentPosition(async (pos) => {
      resolve({
        lat: Number(pos.coords.latitude.toFixed(6)),
        lng: Number(pos.coords.longitude.toFixed(6)),
        address: `${pos.coords.latitude.toFixed(6)}, ${pos.coords.longitude.toFixed(6)}`,
      });
    }, () => resolve({ lat: null, lng: null, address: 'Location permission denied' }), { enableHighAccuracy: true, timeout: 8000 });
  });
}

function fileToDataURL(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function captureAndSend(type) {
  pendingAction = type;
  if (type === 'time-out') finalPhotoInput.click();
  cameraInput.click();
}

cameraInput?.addEventListener('change', async () => {
  const file = cameraInput.files[0];
  if (!file || !pendingAction) return;
  const photoData = await fileToDataURL(file);
  let finalPhotoData = null;
  if (pendingAction === 'time-out' && finalPhotoInput.files[0]) {
    finalPhotoData = await fileToDataURL(finalPhotoInput.files[0]);
  }
  const location = await getLocation();
  const payload = {
    job_id: Number(document.getElementById('job-select')?.value),
    summary: document.getElementById('summary-input')?.value || '',
    photo_data: photoData,
    final_photo_data: finalPhotoData,
    lat: location.lat,
    lng: location.lng,
    address: location.address,
    client_time: new Date().toISOString(),
    device_info: navigator.userAgent,
    offline: !navigator.onLine,
  };
  if (!navigator.onLine) {
    enqueueOffline({ type: pendingAction, payload });
    showResult(`Saved offline as PENDING SYNC: ${pendingAction}`, 'info');
    updateQueueLabel();
    cameraInput.value = '';
    finalPhotoInput.value = '';
    pendingAction = null;
    return;
  }
  const res = await fetch(`/api/attendance/${pendingAction}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  const data = await res.json();
  showResult(data.message ? `${data.message}${data.time ? ' · ' + data.time : ''}` : data.error, data.error ? 'danger' : 'success');
  cameraInput.value = '';
  finalPhotoInput.value = '';
  pendingAction = null;
  if (!data.error) setTimeout(() => location.reload(), 700);
});

async function sendBreak(type) {
  const locationData = await getLocation();
  const payload = {
    lat: locationData.lat,
    lng: locationData.lng,
    address: locationData.address,
    client_time: new Date().toISOString(),
    offline: !navigator.onLine,
  };
  if (!navigator.onLine) {
    enqueueOffline({ type, payload });
    showResult(`Saved offline as PENDING SYNC: ${type}`, 'info');
    updateQueueLabel();
    return;
  }
  const res = await fetch(`/api/attendance/${type}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  const data = await res.json();
  showResult(data.message || data.error, data.error ? 'danger' : 'success');
  if (!data.error) setTimeout(() => location.reload(), 700);
}

function enqueueOffline(entry) {
  const items = JSON.parse(localStorage.getItem(queueKey) || '[]');
  items.push(entry);
  localStorage.setItem(queueKey, JSON.stringify(items));
}

async function syncQueue() {
  const items = JSON.parse(localStorage.getItem(queueKey) || '[]');
  if (!items.length) return showResult('No pending offline actions.', 'info');
  const remaining = [];
  for (const item of items) {
    try {
      const res = await fetch(`/api/attendance/${item.type}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(item.payload) });
      const data = await res.json();
      if (data.error) remaining.push(item);
    } catch (e) { remaining.push(item); }
  }
  localStorage.setItem(queueKey, JSON.stringify(remaining));
  updateQueueLabel();
  showResult(remaining.length ? `${remaining.length} item(s) still pending sync.` : 'Offline queue synced.', remaining.length ? 'info' : 'success');
  if (!remaining.length) setTimeout(() => location.reload(), 700);
}

async function saveWorklog(e) {
  e.preventDefault();
  const payload = {
    task: document.getElementById('task-input').value,
    start_at: new Date(document.getElementById('start-input').value).toISOString(),
    end_at: new Date(document.getElementById('finish-input').value).toISOString(),
    notes: document.getElementById('worklog-notes').value,
  };
  const res = await fetch('/api/worklogs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  const data = await res.json();
  showResult(data.message || data.error, data.error ? 'danger' : 'success');
  if (!data.error) setTimeout(() => location.reload(), 700);
}

window.addEventListener('online', syncQueue);
updateQueueLabel();

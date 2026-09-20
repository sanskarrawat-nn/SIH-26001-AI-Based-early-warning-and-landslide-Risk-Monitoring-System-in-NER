/* Shared by the page and service worker. IndexedDB keeps evidence off localStorage. */
(function (scope) {
  const DB = 'ner-field-outbox-v2';
  function open() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB, 1);
      req.onupgradeneeded = () => req.result.createObjectStore('reports', { keyPath: 'id' });
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }
  async function transaction(mode, work) {
    const db = await open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction('reports', mode);
      const req = work(tx.objectStore('reports'));
      tx.oncomplete = () => { db.close(); resolve(req.result); };
      tx.onerror = tx.onabort = () => { db.close(); reject(tx.error || new Error('Device storage unavailable')); };
    });
  }
  const all = () => transaction('readonly', store => store.getAll());
  const put = row => transaction('readwrite', store => store.put(row));
  const remove = id => transaction('readwrite', store => store.delete(id));
  const lock = work => scope.navigator?.locks ? scope.navigator.locks.request('ner-report-sync', work) : work();
  async function migrate(endpoint) {
    if (!scope.localStorage) return;
    await lock(async () => {
      const old = JSON.parse(localStorage.getItem('ner-field-outbox-v1') || '[]');
      if (!Array.isArray(old)) throw new Error('Legacy outbox needs recovery');
      const existing = new Set((await all()).map(r => r.id));
      for (const report of old) {
        if (!report.id) throw new Error('Legacy report missing its ID');
        if (!existing.has(report.id)) await put({id: report.id, report, endpoint, created: Date.now(), requiresAuth: true});
      }
      localStorage.removeItem('ner-field-outbox-v1');
    });
  }
  async function sync(token, foreground = false, force = false) {
    return lock(async () => {
      const failures = [];
      for (const item of await all()) {
        if (!force && item.nextAttempt > Date.now()) continue;
        const key = token || item.token || '';
        if (item.requiresAuth && !key && !foreground) continue;
        try {
          const response = await fetch(item.endpoint, {method: 'POST', credentials: 'include', headers: {'Content-Type': 'application/json', ...(key ? {'X-Operations-Key': key} : {})}, body: JSON.stringify(item.report), signal: AbortSignal.timeout(45000)});
          if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(typeof data.detail === 'string' ? data.detail : `Submission rejected (${response.status}); review the saved report`);
          }
          await remove(item.id);
        } catch (error) {
          item.error = error.message; item.attempts = (item.attempts || 0) + 1; item.nextAttempt = Date.now() + Math.min(300000, 15000 * 2 ** Math.min(item.attempts, 5)); await put(item); failures.push(error.message);
        }
      }
      if (failures.length) throw new Error(failures[0]);
      return (await all()).length;
    });
  }
  scope.NEROutbox = {all, put: row => lock(() => put(row)), remove: id => lock(() => remove(id)), migrate, sync};
})(typeof window === 'undefined' ? self : window);

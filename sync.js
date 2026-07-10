/* Cross-reinstall favorites sync (shared by index.html, favorites.html, settings.html).
   Identity = SHA-256(TMDB key); the raw key is never sent to the sync endpoint.
   Favorites + ratings live in localStorage as usual; this mirrors them to the
   backend so re-entering the same TMDB key restores them. */
(function () {
  const API = "http://localhost:8080/api";
  const TMDB_KEY = "lumitrace_tmdb_key";
  const FAV_KEY = "lumitrace_favorites";
  const RATINGS_KEY = "lumitrace_ratings";

  async function syncId() {
    const key = (localStorage.getItem(TMDB_KEY) || "").trim();
    if (!key || !(window.crypto && window.crypto.subtle)) return null;
    const buf = await window.crypto.subtle.digest("SHA-256", new TextEncoder().encode(key));
    return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
  }

  function localFavorites() { try { return JSON.parse(localStorage.getItem(FAV_KEY) || "[]"); } catch { return []; } }
  function localRatings() { try { return JSON.parse(localStorage.getItem(RATINGS_KEY) || "{}"); } catch { return {}; } }

  // Union favorites by id (local copy wins for shared ids); ratings keep the
  // newer entry by updatedAt. This restores on a clean reinstall and merges
  // when both sides have data.
  function mergeFavorites(localF, remoteF) {
    const byId = new Map();
    (remoteF || []).forEach((m) => { if (m && m.id != null) byId.set(m.id, m); });
    (localF || []).forEach((m) => { if (m && m.id != null) byId.set(m.id, m); });
    return [...byId.values()];
  }
  function mergeRatings(localR, remoteR) {
    const out = { ...(remoteR || {}) };
    Object.entries(localR || {}).forEach(([id, r]) => {
      const ex = out[id];
      if (!ex || Number(r?.updatedAt || 0) >= Number(ex?.updatedAt || 0)) out[id] = r;
    });
    return out;
  }

  // Pull remote, merge into localStorage. Returns true if anything was applied.
  async function pullFavorites() {
    const id = await syncId();
    if (!id) return false;
    let data;
    try {
      const r = await fetch(`${API}/favorites`, { headers: { "X-Sync-Id": id } });
      if (!r.ok) return false;
      data = await r.json();
    } catch { return false; }
    const payload = data && data.payload;
    if (!payload) return false;
    const mergedF = mergeFavorites(localFavorites(), payload.favorites || []);
    const mergedR = mergeRatings(localRatings(), payload.ratings || {});
    localStorage.setItem(FAV_KEY, JSON.stringify(mergedF));
    localStorage.setItem(RATINGS_KEY, JSON.stringify(mergedR));
    return true;
  }

  async function pushFavorites() {
    const id = await syncId();
    if (!id) return;
    const body = JSON.stringify({ favorites: localFavorites(), ratings: localRatings() });
    try {
      await fetch(`${API}/favorites`, {
        method: "POST",
        headers: { "X-Sync-Id": id, "Content-Type": "application/json" },
        body,
      });
    } catch { /* offline / no backend: stay local-only */ }
  }

  let pushTimer = null;
  function schedulePush() {
    clearTimeout(pushTimer);
    pushTimer = setTimeout(pushFavorites, 1200);
  }

  window.lumitraceSync = { syncId, pullFavorites, pushFavorites, schedulePush };
})();

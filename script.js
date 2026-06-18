const BACKEND_URL = "http://localhost:8080/api";
const IMAGE_BASE = "https://image.tmdb.org/t/p/w500";
const KEY_STORAGE = "lumitrace_tmdb_key";
const FAVORITES_STORAGE = "lumitrace_favorites";
const RATINGS_STORAGE = "lumitrace_ratings";
const TMDB_LANGUAGE = "en-US";

let backendHasTmdbKey = false;
let currentCategory = "trending";
let currentGenre = "";
let currentSearchQuery = "";

// Infinite scroll
let scrollPage = 1;
let scrollLoading = false;
let scrollDone = false;
let scrollMode = "category";
const seenMovieIds = new Set();

// Panel
let panelOpen = false;
let recPage = 1;
let recLoading = false;
let recDone = false;

const CATEGORY_META = {
  trending:    { title: "Trending",    desc: "What is moving across TMDB this week.", endpoint: "trending/movie/week" },
  popular:     { title: "Popular",     desc: "Audience favorites with broad viewing momentum.", endpoint: "movie/popular" },
  top_rated:   { title: "Top rated",   desc: "Highest-rated films from the TMDB community.", endpoint: "movie/top_rated" },
  now_playing: { title: "Now playing", desc: "Films currently in theaters.", endpoint: "movie/now_playing" },
  upcoming:    { title: "Upcoming",    desc: "Movies arriving soon.", endpoint: "movie/upcoming" },
};

const GENRE_NAMES = {
  28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
  99: "Documentary", 18: "Drama", 10751: "Family", 14: "Fantasy", 27: "Horror",
  9648: "Mystery", 10749: "Romance", 878: "Sci-Fi", 53: "Thriller", 37: "Western",
};

// --- Init ---
document.addEventListener("DOMContentLoaded", async () => {
  bindUi();
  restoreKey();
  updateFabBadge();
  await loadBackendStatus();
  setupInfiniteScroll();
  if (hasTmdbAccess()) {
    loadCategory(currentCategory);
  } else {
    setStatus("Enter a TMDB API key, or set TMDB_API_KEY in your local .env file.");
  }
});

// --- Panel ---
let recScrollBound = false;

function openPanel() {
  panelOpen = true;
  document.getElementById("recommendPanel").style.transform = "translateY(0)";
  const ov = document.getElementById("recommendOverlay");
  ov.style.opacity = "1";
  ov.style.pointerEvents = "auto";
  document.body.style.overflow = "hidden";

  // Bind scroll event once
  if (!recScrollBound) {
    const area = document.getElementById("recScrollArea");
    area.addEventListener("scroll", onRecScroll);
    recScrollBound = true;
  }

  // Auto-load recommendations if grid is empty
  const grid = document.getElementById("recommendationGrid");
  if (grid.querySelectorAll("article").length === 0) loadMoreRecs();
}

function closePanel() {
  panelOpen = false;
  document.getElementById("recommendPanel").style.transform = "translateY(100%)";
  const ov = document.getElementById("recommendOverlay");
  ov.style.opacity = "0";
  ov.style.pointerEvents = "none";
  document.body.style.overflow = "";
}

function onRecScroll() {
  const area = document.getElementById("recScrollArea");
  if (area.scrollTop + area.clientHeight >= area.scrollHeight - 300) {
    if (!recLoading && !recDone) loadMoreRecs();
  }
}

function checkRecFill() {
  // If scroll area not full, load more automatically
  const area = document.getElementById("recScrollArea");
  if (area.scrollHeight <= area.clientHeight + 100 && !recLoading && !recDone) {
    loadMoreRecs();
  }
}

// --- UI Binding ---
function bindUi() {
  document.getElementById("saveKeyBtn").addEventListener("click", () => {
    const key = document.getElementById("apiKeyInput").value.trim();
    if (!key) { setStatus("Enter a TMDB API key first."); return; }
    localStorage.setItem(KEY_STORAGE, key);
    setStatus("API key saved. Loading movies...");
    loadCategory(currentCategory);
  });

  document.getElementById("clearKeyBtn").addEventListener("click", () => {
    localStorage.removeItem(KEY_STORAGE);
    document.getElementById("apiKeyInput").value = "";
    if (backendHasTmdbKey) {
      setStatus("Browser API key cleared. Using the backend .env TMDB key instead.");
      loadCategory(currentCategory);
    } else {
      clearMovieGrid();
      setStatus("API key cleared.");
    }
  });

  document.getElementById("searchBtn").addEventListener("click", runSearch);
  document.getElementById("searchInput").addEventListener("keydown", (e) => { if (e.key === "Enter") runSearch(); });
  document.getElementById("playlistBtn").addEventListener("click", runZeroShotPlaylist);
  document.getElementById("playlistPrompt").addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") runZeroShotPlaylist();
  });

  // Panel controls
  document.getElementById("recommendFab").addEventListener("click", () => panelOpen ? closePanel() : openPanel());
  document.getElementById("closePanelBtn").addEventListener("click", closePanel);
  document.getElementById("overlayBackdrop").addEventListener("click", closePanel);
  document.getElementById("closeExplanationBtn").addEventListener("click", closeExplanationModal);
  document.getElementById("explanationBackdrop").addEventListener("click", closeExplanationModal);

  // Rating modal
  document.getElementById("closeRatingBtn").addEventListener("click", closeRatingModal);
  document.getElementById("ratingBackdrop").addEventListener("click", closeRatingModal);
  document.getElementById("saveRatingBtn").addEventListener("click", () => {
    if (!currentRatingMovie || currentRatingScore === 0) return;
    const comment = document.getElementById("ratingComment").value.trim();
    saveRating(currentRatingMovie.id, currentRatingScore, comment);
    closeRatingModal();
    // Refresh grids
    const grid = document.getElementById("movieGrid");
    grid.querySelectorAll(".rating-badge").forEach((b) => {
      const card = b.closest("article");
      const title = card?.querySelector("h3")?.textContent;
      if (title === currentRatingMovie.title) {
        updateCardRating(b, currentRatingMovie.id);
      }
    });
  });
  document.getElementById("deleteRatingBtn").addEventListener("click", () => {
    if (!currentRatingMovie) return;
    deleteRating(currentRatingMovie.id);
    closeRatingModal();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (document.getElementById("explanationModal").style.display !== "none") closeExplanationModal();
      else if (panelOpen) closePanel();
    }
  });

  // Category tabs
  document.querySelectorAll(".category-tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      currentGenre = "";
      currentSearchQuery = "";
      document.getElementById("searchInput").value = "";
      document.querySelectorAll(".genre-chip").forEach((g) => g.classList.remove("active"));
      setActiveTab(btn.dataset.category);
      loadCategory(btn.dataset.category);
    });
  });

  // Genre chips
  document.querySelectorAll(".genre-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      const genreId = btn.dataset.genre;
      if (currentGenre === genreId) {
        currentGenre = "";
        btn.classList.remove("active");
        loadCategory(currentCategory);
      } else {
        currentGenre = genreId;
        currentSearchQuery = "";
        document.getElementById("searchInput").value = "";
        document.querySelectorAll(".genre-chip").forEach((g) => g.classList.remove("active"));
        btn.classList.add("active");
        loadGenre(genreId);
      }
    });
  });
}

// --- API Helpers ---
function restoreKey() { const k = getApiKey(); if (k) document.getElementById("apiKeyInput").value = k; }
function getApiKey() { return localStorage.getItem(KEY_STORAGE) || ""; }
function hasTmdbAccess() { return Boolean(getApiKey() || backendHasTmdbKey); }

async function loadBackendStatus() {
  try {
    const r = await fetch(`${BACKEND_URL}/health`);
    const d = await r.json();
    backendHasTmdbKey = Boolean(d.integrations?.tmdb_env_key);
  } catch { backendHasTmdbKey = false; }
}

function getFavorites() {
  try { return JSON.parse(localStorage.getItem(FAVORITES_STORAGE) || "[]"); }
  catch { return []; }
}

function saveFavorites(f) { localStorage.setItem(FAVORITES_STORAGE, JSON.stringify(f)); }

// --- Ratings ---
function getRatings() {
  try { return JSON.parse(localStorage.getItem(RATINGS_STORAGE) || "{}"); }
  catch { return {}; }
}

function saveRating(movieId, score, comment) {
  const ratings = getRatings();
  ratings[movieId] = { score, comment: comment || "", updatedAt: Date.now() };
  localStorage.setItem(RATINGS_STORAGE, JSON.stringify(ratings));
}

function deleteRating(movieId) {
  const ratings = getRatings();
  delete ratings[movieId];
  localStorage.setItem(RATINGS_STORAGE, JSON.stringify(ratings));
}

function getMovieRating(movieId) {
  return getRatings()[movieId] || null;
}

let currentRatingMovie = null;
let currentRatingScore = 0;

function openRatingModal(movie) {
  currentRatingMovie = movie;
  const existing = getMovieRating(movie.id);
  currentRatingScore = existing ? existing.score : 0;

  document.getElementById("ratingPoster").src = `${IMAGE_BASE}${movie.poster_path}`;
  document.getElementById("ratingTitle").textContent = movie.title;
  const year = movie.release_date ? movie.release_date.slice(0, 4) : "";
  document.getElementById("ratingMeta").textContent = `${year || "Unknown year"} / TMDB ${movie.vote_average.toFixed(1)}`;
  document.getElementById("ratingComment").value = existing ? existing.comment : "";
  document.getElementById("deleteRatingBtn").style.display = existing ? "" : "none";

  // Render score buttons
  const container = document.getElementById("ratingScoreBtns");
  container.innerHTML = "";
  for (let i = 1; i <= 10; i++) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = i;
    btn.className = `score-btn${i <= currentRatingScore ? " is-active" : ""}`;
    btn.addEventListener("click", () => {
      currentRatingScore = i;
      container.querySelectorAll("button").forEach((b, idx) => {
        const n = idx + 1;
        b.classList.toggle("is-active", n <= currentRatingScore);
      });
    });
    container.appendChild(btn);
  }

  const modal = document.getElementById("ratingModal");
  modal.style.display = "flex";
  requestAnimationFrame(() => {
    modal.style.opacity = "1";
    modal.querySelector("div:nth-child(2)").style.transform = "scale(1)";
  });
}

function closeRatingModal() {
  const modal = document.getElementById("ratingModal");
  modal.style.opacity = "0";
  modal.querySelector("div:nth-child(2)").style.transform = "scale(0.96)";
  setTimeout(() => { modal.style.display = "none"; }, 200);
  currentRatingMovie = null;
}

function tmdbHeaders() { const k = getApiKey(); return k ? { "X-TMDB-API-Key": k } : {}; }

async function tmdb(path) {
  const r = await fetch(`${BACKEND_URL}/tmdb/${path}`, { headers: tmdbHeaders() });
  const d = await r.json();
  if (!r.ok) throw new Error(d.status_message || d.error || "TMDB request failed");
  return d;
}

// --- FAB Badge ---
function updateFabBadge() {
  const badge = document.getElementById("fabBadge");
  const count = getFavorites().length;
  if (count > 0) { badge.style.display = "flex"; badge.textContent = count > 99 ? "99+" : count; }
  else { badge.style.display = "none"; }
}

// --- Category / Genre / Search ---
function setActiveTab(cat) {
  currentCategory = cat;
  document.querySelectorAll(".category-tab").forEach((b) => b.classList.toggle("active", b.dataset.category === cat));
  const m = CATEGORY_META[cat];
  if (m) { document.getElementById("categoryTitle").textContent = m.title; document.getElementById("categoryDesc").textContent = m.desc; }
}

function resetScrollState(mode) { scrollPage = 1; scrollLoading = false; scrollDone = false; scrollMode = mode; seenMovieIds.clear(); clearMovieGrid(); }
function clearMovieGrid() { document.getElementById("movieGrid").innerHTML = ""; document.getElementById("loadMoreSentinel")?.remove(); }

async function loadCategory(cat) {
  if (!requireKey()) return;
  const meta = CATEGORY_META[cat];
  if (!meta) return;
  resetScrollState("category");
  setActiveTab(cat);
  setStatus(`Loading ${meta.title.toLowerCase()}...`);
  try {
    const data = await tmdb(`${meta.endpoint}?language=${TMDB_LANGUAGE}&page=1`);
    const movies = normalizeMovies(data.results || []);
    movies.forEach((m) => seenMovieIds.add(m.id));
    appendMovieCards(movies);
    scrollPage = 2;
    setStatus(`Loaded ${movies.length} movies. Scroll down for more.`);
    attachSentinel();
  } catch (err) { setStatus(`Failed: ${err.message}`); }
}

async function loadGenre(genreId) {
  if (!requireKey()) return;
  const name = GENRE_NAMES[genreId] || genreId;
  resetScrollState("genre");
  document.getElementById("categoryTitle").textContent = `${name} movies`;
  document.getElementById("categoryDesc").textContent = `Best ${name.toLowerCase()} films ranked by rating.`;
  setStatus(`Loading ${name} movies...`);
  try {
    const data = await tmdb(`discover/movie?language=${TMDB_LANGUAGE}&sort_by=vote_average.desc&vote_count.gte=150&with_genres=${genreId}&page=1`);
    const movies = normalizeMovies(data.results || []);
    movies.forEach((m) => seenMovieIds.add(m.id));
    appendMovieCards(movies);
    scrollPage = 2;
    setStatus(`Loaded ${movies.length} ${name.toLowerCase()} movies.`);
    attachSentinel();
  } catch (err) { setStatus(`Failed: ${err.message}`); }
}

async function runSearch() {
  if (!requireKey()) return;
  const query = document.getElementById("searchInput").value.trim();
  if (!query) { loadCategory(currentCategory); return; }
  currentSearchQuery = query;
  resetScrollState("search");
  document.getElementById("categoryTitle").textContent = `Search: ${query}`;
  document.getElementById("categoryDesc").textContent = `Results for "${query}".`;
  setStatus(`Searching...`);
  try {
    const data = await tmdb(`search/movie?query=${encodeURIComponent(query)}&language=${TMDB_LANGUAGE}&page=1`);
    const movies = normalizeMovies(data.results || []);
    movies.forEach((m) => seenMovieIds.add(m.id));
    appendMovieCards(movies);
    scrollPage = 2;
    setStatus(`Found ${movies.length} movies.`);
    attachSentinel();
  } catch (err) { setStatus(`Search failed: ${err.message}`); }
}

async function runZeroShotPlaylist() {
  const prompt = document.getElementById("playlistPrompt").value.trim();
  if (!prompt) {
    setStatus("Describe a viewing mood first.");
    return;
  }

  const language = document.getElementById("playlistLanguage").value;
  const genre = document.getElementById("playlistGenre").value;
  const payload = {
    overviews: [prompt],
    exclude_ids: getFavorites().map((movie) => movie.id),
    user_genre_ids: genre ? [[Number(genre)]] : [],
    user_vote_counts: [8],
    playlist_genre_ids: genre ? [Number(genre)] : [],
    preferred_languages: language ? [language] : [],
    top_k: 30,
  };

  setStatus("Generating zero-shot semantic playlist...");
  resetRecScroll();
  recDone = true;
  document.getElementById("recommendationReason").textContent = "Tracing your scene prompt through the BERT vector index...";

  try {
    const response = await fetch(`${BACKEND_URL}/semantic-recommendations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok || data.error) {
      throw new Error(data.error || "Semantic playlist failed");
    }

    const movies = normalizeSemantic(data.results || []);
    if (!movies.length) {
      document.getElementById("recommendationReason").textContent = data.fallback || "No semantic playlist results.";
      setStatus(data.fallback || "No semantic playlist results.");
      openPanel();
      return;
    }

    movies.forEach((movie) => seenRecIds.add(movie.id));
    renderRecGrid(movies);
    const filters = data.playlist || {};
    const chips = [
      filters.genre_ids?.length ? `genres ${filters.genre_ids.join(", ")}` : "",
      filters.preferred_languages?.length ? `languages ${filters.preferred_languages.join(", ")}` : "",
      filters.relaxed_context_filters ? "filters relaxed" : "",
    ].filter(Boolean).join(" / ");
    document.getElementById("recommendationReason").textContent =
      `Zero-shot semantic playlist${chips ? ` (${chips})` : ""}.`;
    setStatus(`Generated ${movies.length} semantic playlist picks.`);
    openPanel();
  } catch (err) {
    setStatus(`Zero-shot playlist failed: ${err.message}`);
    document.getElementById("recommendationReason").textContent = `Failed: ${err.message}`;
    openPanel();
  }
}

// --- Infinite Scroll ---
function setupInfiniteScroll() {
  const obs = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && !scrollLoading && !scrollDone) loadMore();
  }, { rootMargin: "600px" });
  window._infiniteScrollObserver = obs;
}

function attachSentinel() {
  document.getElementById("loadMoreSentinel")?.remove();
  const grid = document.getElementById("movieGrid");
  const s = document.createElement("div");
  s.id = "loadMoreSentinel";
  s.className = "grid-sentinel";
  s.innerHTML = `<div class="loader-dots" id="loaderDots" style="opacity:0"><span></span><span></span><span></span></div>`;
  grid.appendChild(s);
  window._infiniteScrollObserver.observe(s);
}

async function loadMore() {
  if (scrollLoading || scrollDone) return;
  scrollLoading = true;
  setLoaderVisible(true);
  try {
    let ep;
    if (scrollMode === "search") ep = `search/movie?query=${encodeURIComponent(currentSearchQuery)}&language=${TMDB_LANGUAGE}&page=${scrollPage}`;
    else if (scrollMode === "genre") ep = `discover/movie?language=${TMDB_LANGUAGE}&sort_by=vote_average.desc&vote_count.gte=150&with_genres=${currentGenre}&page=${scrollPage}`;
    else { const m = CATEGORY_META[currentCategory]; ep = `${m.endpoint}?language=${TMDB_LANGUAGE}&page=${scrollPage}`; }
    const data = await tmdb(ep);
    const fresh = normalizeMovies(data.results || []).filter((m) => !seenMovieIds.has(m.id));
    fresh.forEach((m) => seenMovieIds.add(m.id));
    if (!fresh.length) { scrollDone = true; setStatus("No more movies."); document.getElementById("loadMoreSentinel")?.remove(); }
    else {
      const s = document.getElementById("loadMoreSentinel");
      if (s) window._infiniteScrollObserver.unobserve(s);
      appendMovieCards(fresh);
      scrollPage++;
      setStatus(`Loaded ${seenMovieIds.size} movies.`);
      const s2 = document.getElementById("loadMoreSentinel");
      if (s2) window._infiniteScrollObserver.observe(s2);
    }
  } catch (err) { setStatus(`Load more failed: ${err.message}`); }
  scrollLoading = false;
  setLoaderVisible(false);
}

function setLoaderVisible(v) { const d = document.getElementById("loaderDots"); if (d) d.style.opacity = v ? "1" : "0"; }

// --- Movie Cards ---
function tmdbBadge(movie) {
  const s = movie.vote_average;
  return `<span class="rating-value"><small>TMDB</small>${s.toFixed(1)}</span>`;
}

function ratingBadgeHtml(movieId) {
  const r = getMovieRating(movieId);
  if (!r) return `<button class="rating-badge" data-movie-id="${movieId}" type="button">Rate</button>`;
  return `<button class="rating-badge is-rated" data-movie-id="${movieId}" type="button">${r.score}/10</button>`;
}

function updateCardRating(badgeEl, movieId) {
  const r = getMovieRating(movieId);
  if (!r) {
    badgeEl.textContent = "Rate";
    badgeEl.className = "rating-badge";
  } else {
    badgeEl.textContent = `${r.score}/10`;
    badgeEl.className = "rating-badge is-rated";
  }
}

function appendMovieCards(movies) {
  const grid = document.getElementById("movieGrid");
  const favSet = new Set(getFavorites().map((m) => m.id));
  const sentinel = document.getElementById("loadMoreSentinel");
  movies.forEach((movie) => {
    const card = document.createElement("article");
    card.className = "poster-card";
    card.dataset.movieId = String(movie.id);
    const active = favSet.has(movie.id);
    const year = movie.release_date ? movie.release_date.slice(0, 4) : "";
    card.innerHTML = `
      <a class="poster-link" href="https://www.themoviedb.org/movie/${movie.id}" target="_blank" rel="noopener">
        <img class="poster-image" src="${IMAGE_BASE}${movie.poster_path}" alt="${esc(movie.title)} poster" loading="lazy">
      </a>
      <div class="poster-content">
        <h3 class="poster-title line-clamp-2">${esc(movie.title)}</h3>
        <div class="poster-meta">
          <span>${year || "N/A"}</span>
          ${tmdbBadge(movie)}
        </div>
        <div class="card-actions">
          ${ratingBadgeHtml(movie.id)}
        </div>
        <button class="fav-btn${active ? " is-saved" : ""}" data-movie-id="${movie.id}" type="button">${active ? "Saved" : "Save"}</button>
      </div>`;
    card.querySelector(".fav-btn").addEventListener("click", () => toggleFav(movie, card));
    card.querySelector(".rating-badge").addEventListener("click", (e) => { e.stopPropagation(); openRatingModal(movie); });
    if (sentinel) grid.insertBefore(card, sentinel); else grid.appendChild(card);
    // Trigger entrance animation
    requestAnimationFrame(() => card.classList.add("in-view"));
  });
}

function toggleFav(movie, cardEl) {
  const favs = getFavorites();
  const exists = favs.some((f) => f.id === movie.id);
  const next = exists ? favs.filter((f) => f.id !== movie.id) : [...favs, movie];
  saveFavorites(next);
  updateFabBadge();
  document.querySelectorAll(`.fav-btn[data-movie-id="${movie.id}"]`).forEach((btn) => {
    const isFav = next.some((f) => f.id === movie.id);
    btn.classList.toggle("is-saved", isFav);
    btn.textContent = isFav ? "Saved" : "Save";
  });
  // Update panel summary and reset recommendations
  updatePanelSummary();
  if (panelOpen) { resetRecScroll(); loadMoreRecs(); }
}

function updatePanelSummary() {
  const favs = getFavorites();
  const el = document.getElementById("panelFavSummary");
  const countEl = document.getElementById("panelFavCount");
  el.textContent = favs.length > 0 ? "recommendations based on your taste" : "no favorites yet; showing popular picks";
  if (countEl) countEl.textContent = favs.length > 0 ? favs.length : "";
}

// --- Recommendations (infinite scroll) ---
const seenRecIds = new Set();

async function loadMoreRecs() {
  if (recLoading || recDone || !requireKey()) return;
  recLoading = true;
  setRecLoaderVisible(true);

  try {
    const favs = getFavorites();
    const favIds = new Set(favs.map((m) => m.id));
    const ratings = getRatings();
    const lowRatedIds = new Set(Object.entries(ratings).filter(([, r]) => r.score <= 3).map(([id]) => Number(id)));
    updatePanelSummary();

    // No favorites → popular movies
    if (favs.length === 0) {
      const data = await tmdb(`movie/popular?language=${TMDB_LANGUAGE}&page=${recPage}`);
      const movies = normalizeMovies(data.results || []).filter((m) => !seenRecIds.has(m.id));
      movies.forEach((m) => seenRecIds.add(m.id));
      if (!movies.length) { recDone = true; document.getElementById("recommendationReason").textContent = "No more movies."; }
      else {
        appendRecCards(movies.map((m) => ({ ...m, recommendationScore: Math.round(Math.min(95, m.vote_average * 10)) })));
        recPage++;
        document.getElementById("recommendationReason").textContent = "Popular picks; save movies for personalized recommendations.";
      }
      recLoading = false;
      setRecLoaderVisible(false);
      return;
    }

    // First page: try semantic
    if (recPage === 1) {
      try {
        const sem = await loadSemanticRecs(favs);
        if (sem.length > 0) {
          sem.forEach((m) => seenRecIds.add(m.id));
          renderRecGrid(sem);
          document.getElementById("recommendationReason").textContent = `BERT semantic analysis from ${favs.length} favorites. Scroll for more.`;
          recPage = 2;
          recLoading = false;
          setRecLoaderVisible(false);
          return;
        }
      } catch {}
    }

    // Metadata pages
    const profile = buildProfile(favs);
    if (!profile.genreIds.length) {
      document.getElementById("recommendationReason").textContent = "Save more movies for better recommendations.";
      recDone = true;
      recLoading = false;
      setRecLoaderVisible(false);
      return;
    }

    const gq = profile.genreIds.slice(0, 3).join(",");
    const data = await tmdb(`discover/movie?language=${TMDB_LANGUAGE}&sort_by=vote_average.desc&vote_count.gte=150&with_genres=${gq}&page=${recPage}`);
    const raw = normalizeMovies(data.results || []).filter((m) => !favIds.has(m.id) && !seenRecIds.has(m.id) && !lowRatedIds.has(m.id));
    raw.forEach((m) => seenRecIds.add(m.id));

    if (!raw.length) {
      recDone = true;
      document.getElementById("recommendationReason").textContent = "No more recommendations.";
    } else {
      const scored = raw.map((m) => ({ ...m, _r: scoreMovie(m, profile) }));
      const maxS = Math.max(1, ...scored.map((m) => m._r));
      const candidates = scored.map((m) => ({ ...m, recommendationScore: Math.round((m._r / maxS) * 95) + 5 })).sort((a, b) => b.recommendationScore - a.recommendationScore);
      appendRecCards(candidates);
      recPage++;
      document.getElementById("recommendationReason").textContent = `From ${favs.length} favorites; scroll for more.`;
    }
  } catch (err) {
    document.getElementById("recommendationReason").textContent = `Failed: ${err.message}`;
  }

  recLoading = false;
  setRecLoaderVisible(false);

  // If content doesn't fill the scroll area, load more
  setTimeout(checkRecFill, 100);
}

function setRecLoaderVisible(v) { const d = document.getElementById("recLoaderDots"); if (d) d.style.opacity = v ? "1" : "0"; }

function resetRecScroll() {
  recPage = 1;
  recLoading = false;
  recDone = false;
  seenRecIds.clear();
  document.getElementById("recommendationGrid").innerHTML = "";
  document.getElementById("recommendationReason").textContent = "Scroll down for recommendations.";
}

async function loadSemanticRecs(favs) {
  const ratings = getRatings();
  const payload = {
    overviews: favs.map((movie) => semanticTasteText(movie, ratings[movie.id])).filter(Boolean),
    exclude_ids: favs.map((movie) => movie.id),
    user_genre_ids: favs.map((movie) => movie.genre_ids || []),
    user_vote_counts: favs.map((movie) => Number(ratings[movie.id]?.score || 5)),
    user_release_years: favs.map(movieReleaseYear).filter(Boolean),
    top_k: 18,
  };
  if (!payload.overviews.length) return [];
  const r = await fetch(`${BACKEND_URL}/semantic-recommendations`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  if (!r.ok) return [];
  return normalizeSemantic((await r.json()).results || []);
}

function semanticTasteText(movie, rating) {
  const parts = [];
  if (movie.title) parts.push(movie.title);
  const year = movieReleaseYear(movie);
  if (year) parts.push(`Release year: ${year}`);
  if (movie.original_language) parts.push(`Original language: ${movie.original_language}`);
  if (movie.overview) parts.push(movie.overview);
  if (rating?.comment) parts.push(`Viewer note: ${rating.comment}`);
  return parts.join(". ");
}

function movieReleaseYear(movie) {
  const year = Number(String(movie.release_date || "").slice(0, 4));
  return Number.isFinite(year) && year >= 1888 && year <= 2100 ? year : null;
}

function renderRecGrid(movies) {
  const grid = document.getElementById("recommendationGrid");
  grid.innerHTML = "";
  const sentinel = document.getElementById("recSentinel");
  movies.forEach((m) => {
    const card = makeRecCard(m);
    if (sentinel) grid.insertBefore(card, sentinel);
    else grid.appendChild(card);
    requestAnimationFrame(() => card.classList.add("in-view"));
  });
}

function appendRecCards(movies) {
  const grid = document.getElementById("recommendationGrid");
  const existing = new Set(Array.from(grid.querySelectorAll("h3")).map((h) => h.textContent));
  const sentinel = document.getElementById("recSentinel");
  movies.forEach((m) => {
    if (existing.has(m.title)) return;
    existing.add(m.title);
    const card = makeRecCard(m);
    if (sentinel) grid.insertBefore(card, sentinel);
    else grid.appendChild(card);
    requestAnimationFrame(() => card.classList.add("in-view"));
  });
}

function makeRecCard(movie) {
  const favs = getFavorites();
  const favSet = new Set(favs.map((m) => m.id));
  const card = document.createElement("article");
  card.className = "poster-card";
  card.dataset.movieId = String(movie.id);
  const active = favSet.has(movie.id);
  const year = movie.release_date ? movie.release_date.slice(0, 4) : "";
  const s = movie.vote_average;
  card.innerHTML = `
    <a class="poster-link" href="https://www.themoviedb.org/movie/${movie.id}" target="_blank" rel="noopener">
      <img class="poster-image" src="${IMAGE_BASE}${movie.poster_path}" alt="${esc(movie.title)} poster" loading="lazy">
    </a>
    <div class="poster-content">
      <h3 data-title="${esc(movie.title)}" class="poster-title line-clamp-2">${esc(movie.title)}</h3>
      <div class="poster-meta">
        <span>${year || "N/A"}</span>
        ${tmdbBadge(movie)}
      </div>
      <div class="rec-card-actions">
        ${movie.recommendationScore ? `<span class="match-badge">${Math.round(movie.recommendationScore)}%</span>` : ""}
        ${ratingBadgeHtml(movie.id)}
        <button class="why-btn" type="button">why?</button>
      </div>
      <button class="rec-fav-btn${active ? " is-saved" : ""}" data-movie-id="${movie.id}" type="button">${active ? "Saved" : "Save"}</button>
    </div>`;
  card.querySelector(".rating-badge").addEventListener("click", (e) => { e.stopPropagation(); openRatingModal(movie); });
  card.querySelector(".rec-fav-btn").addEventListener("click", () => {
    const all = getFavorites();
    const exists = all.some((f) => f.id === movie.id);
    const next = exists ? all.filter((f) => f.id !== movie.id) : [...all, movie];
    saveFavorites(next);
    updateFabBadge();
    updatePanelSummary();
    const btn = card.querySelector(".rec-fav-btn");
    const isFav = next.some((f) => f.id === movie.id);
    btn.classList.toggle("is-saved", isFav);
    btn.textContent = isFav ? "Saved" : "Save";
  });
  card.querySelector(".why-btn").addEventListener("click", (e) => { e.stopPropagation(); showExplanation(movie); });
  return card;
}

// --- Explanation Modal ---
function showExplanation(movie) {
  const favs = getFavorites();
  const profile = buildProfile(favs);
  const reasons = buildReasons(movie, profile, favs);
  const year = movie.release_date ? movie.release_date.slice(0, 4) : "N/A";
  document.getElementById("explanationBody").innerHTML = `
    <div class="flex gap-4 mb-5">
      <img src="${IMAGE_BASE}${movie.poster_path}" alt="${esc(movie.title)}" class="w-28 rounded-xl object-cover flex-shrink-0" style="aspect-ratio:2/3">
      <div class="flex flex-col gap-2 min-w-0">
        <h3 class="text-lg font-semibold leading-tight">${esc(movie.title)}</h3>
        <div class="flex items-center gap-2 text-sm text-white/50"><span>${year}</span><span>·</span><span>⭐ ${movie.vote_average.toFixed(1)}</span><span>·</span><span>${(movie.vote_count||0).toLocaleString()} votes</span></div>
        ${movie.recommendationScore ? `<span class="rounded-full bg-teal-500/15 px-2.5 py-1 text-xs font-semibold text-teal-300 w-fit">Match ${Math.round(movie.recommendationScore)}%</span>` : ""}
        <p class="text-xs text-white/45 leading-5 mt-1 line-clamp-3">${esc(movie.overview || "")}</p>
      </div>
    </div>
    <div class="space-y-3">
      ${reasons.length ? reasons.map((r) => `<div class="flex gap-3 rounded-xl bg-white/5 border border-white/8 p-3.5"><span class="text-xl flex-shrink-0 mt-0.5">${r.icon}</span><div><div class="text-sm font-semibold text-white/90">${r.title}</div><div class="text-xs text-white/50 leading-5 mt-0.5">${r.detail}</div></div></div>`).join("") : '<div class="text-sm text-white/45 text-center py-4">Save more movies for better analysis.</div>'}
    </div>`;
  const modal = document.getElementById("explanationModal");
  modal.style.display = "flex";
  requestAnimationFrame(() => { modal.style.opacity = "1"; modal.querySelector(".explanation-content").style.transform = "scale(1)"; });
}

function closeExplanationModal() {
  const modal = document.getElementById("explanationModal");
  modal.style.opacity = "0";
  modal.querySelector(".explanation-content").style.transform = "scale(0.92)";
  setTimeout(() => { modal.style.display = "none"; }, 250);
}

function buildReasons(movie, profile, favs) {
  const mg = movie.genre_ids || [];
  const reasons = [];
  const ratings = getRatings();

  // Genre match with rating boost
  const matched = mg.filter((id) => profile.genreWeights.has(id) && profile.genreWeights.get(id) > 0);
  if (matched.length) {
    const top = matched.sort((a, b) => (profile.genreWeights.get(b) || 0) - (profile.genreWeights.get(a) || 0))[0];
    const weight = profile.genreWeights.get(top) || 0;
    const genreName = GENRE_NAMES[top] || top;
    // Check if user rated this genre highly
    const ratedGenreMovies = favs.filter((f) => (f.genre_ids || []).includes(top) && ratings[f.id] && ratings[f.id].score > 5);
    if (ratedGenreMovies.length > 0) {
      const avgScore = ratedGenreMovies.reduce((s, m) => s + ratings[m.id].score, 0) / ratedGenreMovies.length;
      reasons.push({ icon: "🎭", title: `You rated ${genreName} highly`, detail: `Your ${genreName} movies avg ${avgScore.toFixed(1)}/10. This is also ${genreName}.`, w: 50 });
    } else {
      reasons.push({ icon: "🎭", title: `You like ${genreName}`, detail: `Weighted score: ${weight}. This is also ${genreName}.`, w: 40 });
    }
  }

  // Rating-based: check if user rated similar movies
  const ratedMovies = favs.filter((f) => ratings[f.id]);
  if (ratedMovies.length > 0) {
    const highRated = ratedMovies.filter((f) => ratings[f.id].score >= 8);
    if (highRated.length > 0) {
      const sharedGenres = highRated.filter((f) => (f.genre_ids || []).some((id) => mg.includes(id)));
      if (sharedGenres.length > 0) {
        reasons.push({ icon: "⭐", title: "Matches your top-rated movies", detail: `You rated ${sharedGenres.length} similar movie${sharedGenres.length > 1 ? "s" : ""} 8+.`, w: 45 });
      }
    }
  }

  const diff = Math.abs(movie.vote_average - profile.avgVote);
  if (diff < 1.5) reasons.push({ icon: "📊", title: "Rating matches your taste", detail: `Your favorites avg ${profile.avgVote.toFixed(1)} — this is ${movie.vote_average.toFixed(1)}.`, w: 25 });
  else if (movie.vote_average >= 7.5) reasons.push({ icon: "📊", title: "Highly rated", detail: `Rated ${movie.vote_average.toFixed(1)} on TMDB.`, w: 15 });
  if (movie.vote_count >= 10000) reasons.push({ icon: "🔥", title: "Widely loved", detail: `${movie.vote_count.toLocaleString()} ratings.`, w: 20 });
  if (movie.recommendationScore >= 70) reasons.push({ icon: "🧠", title: "Story & theme match", detail: "Highly similar to your favorites.", w: 35 });
  else if (movie.recommendationScore >= 50) reasons.push({ icon: "🧠", title: "Similar vibe", detail: "Shares themes with your favorites.", w: 20 });
  const fm = favs.map((f) => ({ t: f.title, o: (f.genre_ids || []).filter((id) => mg.includes(id)).length })).sort((a, b) => b.o - a.o);
  if (fm.length && fm[0].o >= 2) reasons.push({ icon: "🎬", title: `Like "${fm[0].t}"`, detail: `Shares ${fm[0].o} genres.`, w: 15 });
  return reasons.sort((a, b) => b.w - a.w).slice(0, 3);
}

function showExplanation(movie) {
  const favs = getFavorites();
  const profile = buildProfile(favs);
  const reasons = buildReasons(movie, profile, favs);
  const year = movie.release_date ? movie.release_date.slice(0, 4) : "N/A";
  const match = movie.recommendationScore ? `<span class="match-badge">Match ${Math.round(movie.recommendationScore)}%</span>` : "";
  document.getElementById("explanationBody").innerHTML = `
    <div class="explanation-preview">
      <img src="${IMAGE_BASE}${movie.poster_path}" alt="${esc(movie.title)} poster">
      <div>
        <h3 class="explanation-title">${esc(movie.title)}</h3>
        <div class="explanation-meta">
          <span>${year}</span>
          <span>TMDB ${movie.vote_average.toFixed(1)}</span>
          <span>${(movie.vote_count || 0).toLocaleString()} votes</span>
        </div>
        <div style="margin-top:10px;">${match}</div>
        <p class="explanation-overview line-clamp-3">${esc(movie.overview || "")}</p>
      </div>
    </div>
    <div class="reason-list">
      ${reasons.length ? reasons.map((reason) => `
        <div class="reason-card">
          <span class="reason-icon">${reason.icon}</span>
          <div>
            <b>${reason.title}</b>
            <span>${reason.detail}</span>
          </div>
        </div>`).join("") : '<div class="reason-card"><span class="reason-icon">TIP</span><div><b>Save more movies</b><span>LumiTrace can explain recommendations better after it sees more of your taste.</span></div></div>'}
    </div>`;
  const modal = document.getElementById("explanationModal");
  modal.style.display = "flex";
  requestAnimationFrame(() => {
    modal.style.opacity = "1";
    modal.querySelector(".explanation-content").style.transform = "scale(1)";
  });
}

function buildReasons(movie, profile, favs) {
  const movieGenres = movie.genre_ids || [];
  const reasons = [];
  const ratings = getRatings();
  const matched = movieGenres.filter((id) => profile.genreWeights.has(id) && profile.genreWeights.get(id) > 0);

  if (matched.length) {
    const top = matched.sort((a, b) => (profile.genreWeights.get(b) || 0) - (profile.genreWeights.get(a) || 0))[0];
    const weight = profile.genreWeights.get(top) || 0;
    const genreName = GENRE_NAMES[top] || top;
    const ratedGenreMovies = favs.filter((fav) => (fav.genre_ids || []).includes(top) && ratings[fav.id] && ratings[fav.id].score > 5);
    if (ratedGenreMovies.length) {
      const avgScore = ratedGenreMovies.reduce((sum, fav) => sum + ratings[fav.id].score, 0) / ratedGenreMovies.length;
      reasons.push({ icon: "GEN", title: `You rate ${genreName} well`, detail: `Your saved ${genreName} movies average ${avgScore.toFixed(1)}/10. This film sits in the same lane.`, w: 50 });
    } else {
      reasons.push({ icon: "GEN", title: `Strong ${genreName} signal`, detail: `Your collection gives ${genreName} a profile weight of ${weight}.`, w: 40 });
    }
  }

  const highRated = favs.filter((fav) => ratings[fav.id]?.score >= 8);
  const similarHighRated = highRated.filter((fav) => (fav.genre_ids || []).some((id) => movieGenres.includes(id)));
  if (similarHighRated.length) {
    reasons.push({ icon: "TOP", title: "Close to your top-rated films", detail: `It shares genre DNA with ${similarHighRated.length} movie${similarHighRated.length > 1 ? "s" : ""} you rated 8 or higher.`, w: 45 });
  }

  const diff = Math.abs(movie.vote_average - profile.avgVote);
  if (diff < 1.5) {
    reasons.push({ icon: "AVG", title: "Rating band match", detail: `Your favorites average ${profile.avgVote.toFixed(1)}. This film is ${movie.vote_average.toFixed(1)} on TMDB.`, w: 25 });
  } else if (movie.vote_average >= 7.5) {
    reasons.push({ icon: "RAT", title: "Critically strong candidate", detail: `TMDB viewers rate it ${movie.vote_average.toFixed(1)}.`, w: 15 });
  }

  if (movie.vote_count >= 10000) {
    reasons.push({ icon: "POP", title: "Large audience signal", detail: `${movie.vote_count.toLocaleString()} votes make the score harder to fake.`, w: 20 });
  }

  if (movie.recommendationScore >= 70) {
    reasons.push({ icon: "SEM", title: "Story and theme match", detail: "The semantic signal places this close to your saved films.", w: 35 });
  } else if (movie.recommendationScore >= 50) {
    reasons.push({ icon: "SIM", title: "Similar viewing mood", detail: "It shares enough profile signals to be worth testing.", w: 20 });
  }

  const closestFavorite = favs
    .map((fav) => ({ title: fav.title, overlap: (fav.genre_ids || []).filter((id) => movieGenres.includes(id)).length }))
    .sort((a, b) => b.overlap - a.overlap)[0];
  if (closestFavorite?.overlap >= 2) {
    reasons.push({ icon: "REF", title: `Near "${closestFavorite.title}"`, detail: `Shares ${closestFavorite.overlap} genres with that saved movie.`, w: 15 });
  }

  return reasons.sort((a, b) => b.w - a.w).slice(0, 3);
}

// --- Helpers ---
function normalizeMovies(movies) {
  return movies.filter((m) => m?.poster_path).map((m) => ({
    id: m.id, title: m.title || m.name || "Untitled", overview: m.overview || "",
    poster_path: m.poster_path, release_date: m.release_date || "",
    original_language: m.original_language || "", vote_average: Number(m.vote_average || 0), vote_count: Number(m.vote_count || 0), genre_ids: m.genre_ids || [],
  }));
}

function normalizeSemantic(movies) {
  const filtered = movies.filter((m) => m?.poster_path);
  const maxR = Math.max(0.001, ...filtered.map((m) => Number(m.diversified_score || m.score || m.semantic_score || 0)));
  return filtered.map((m) => {
    const raw = Number(m.diversified_score || m.score || m.semantic_score || 0);
    return { id: m.id, title: m.title || "Untitled", overview: m.overview || "", poster_path: m.poster_path, release_date: m.release_date || "", original_language: m.original_language || "", vote_average: Number(m.vote_average || 0), vote_count: Number(m.vote_count || 0), genre_ids: m.genre_ids || [], recommendationScore: Math.max(1, Math.min(100, Math.round((raw / maxR) * 70) + 30)) };
  });
}

function buildProfile(favs) {
  const gw = new Map();
  let avg = 0;

  // Favorites get +1 base weight per genre
  favs.forEach((m) => {
    avg += m.vote_average || 0;
    (m.genre_ids || []).forEach((id) => gw.set(id, (gw.get(id) || 0) + 1));
  });

  // User ratings adjust weights: 6-10 = add, 1-4 = subtract, 5 = neutral
  const ratings = getRatings();
  Object.entries(ratings).forEach(([movieId, rating]) => {
    const movie = favs.find((m) => m.id === Number(movieId));
    if (!movie) return; // only use rated movies that are also in favorites
    const delta = rating.score - 5; // -4 to +5
    (movie.genre_ids || []).forEach((id) => {
      gw.set(id, (gw.get(id) || 0) + delta);
    });
  });

  // Clamp weights to minimum 0
  for (const [id, weight] of gw) {
    if (weight < 0) gw.set(id, 0);
  }

  return {
    genreIds: [...gw.entries()].sort((a, b) => b[1] - a[1]).map(([id]) => id),
    genreWeights: gw,
    avgVote: favs.length ? avg / favs.length : 0,
  };
}

function scoreMovie(m, p) {
  const gs = (m.genre_ids || []).reduce((s, id) => s + (p.genreWeights.get(id) || 0), 0);
  return gs * 25 + Math.max(0, m.vote_average - 5) * 7 + Math.min(20, Math.log10(Math.max(1, m.vote_count)) * 6) + Math.max(0, 10 - Math.abs(m.vote_average - p.avgVote)) * 2;
}

function requireKey() { if (hasTmdbAccess()) return true; setStatus("Enter a TMDB API key first."); return false; }
function setStatus(msg) { document.getElementById("keyStatus").textContent = msg; }
function esc(v) { const d = document.createElement("div"); d.textContent = v || ""; return d.innerHTML; }

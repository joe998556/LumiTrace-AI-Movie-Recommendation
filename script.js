const BACKEND_URL = "http://localhost:8080/api";
const IMAGE_BASE = "https://image.tmdb.org/t/p/w500";
const KEY_STORAGE = "lumitrace_tmdb_key";
const FAVORITES_STORAGE = "lumitrace_favorites";

let activeMovies = [];

document.addEventListener("DOMContentLoaded", () => {
  bindUi();
  restoreKey();
  renderFavorites();
  if (getApiKey()) {
    loadTrending();
  } else {
    setStatus("請輸入 TMDB API key，或在 .env 設定 TMDB_API_KEY。");
  }
});

function bindUi() {
  document.getElementById("saveKeyBtn").addEventListener("click", () => {
    const key = document.getElementById("apiKeyInput").value.trim();
    if (!key) {
      setStatus("請先輸入 TMDB API key。");
      return;
    }
    localStorage.setItem(KEY_STORAGE, key);
    setStatus("已儲存 API key，正在載入趨勢電影...");
    loadTrending();
  });

  document.getElementById("clearKeyBtn").addEventListener("click", () => {
    localStorage.removeItem(KEY_STORAGE);
    document.getElementById("apiKeyInput").value = "";
    activeMovies = [];
    document.getElementById("movieGrid").innerHTML = "";
    setStatus("已清除 API key。");
  });

  document.getElementById("searchBtn").addEventListener("click", runSearch);
  document.getElementById("searchInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") runSearch();
  });

  document.getElementById("recommendBtn").addEventListener("click", loadRecommendations);
  document.getElementById("clearFavoritesBtn").addEventListener("click", () => {
    localStorage.removeItem(FAVORITES_STORAGE);
    renderFavorites();
    document.getElementById("recommendationGrid").innerHTML = "";
    document.getElementById("recommendationReason").textContent = "收藏幾部喜歡的電影後按推薦按鈕。";
    renderMovieGrid(activeMovies, "movieGrid");
  });
}

function restoreKey() {
  const key = getApiKey();
  if (key) {
    document.getElementById("apiKeyInput").value = key;
  }
}

function getApiKey() {
  return localStorage.getItem(KEY_STORAGE) || "";
}

function getFavorites() {
  try {
    return JSON.parse(localStorage.getItem(FAVORITES_STORAGE) || "[]");
  } catch {
    return [];
  }
}

function saveFavorites(favorites) {
  localStorage.setItem(FAVORITES_STORAGE, JSON.stringify(favorites));
}

function tmdbHeaders() {
  const key = getApiKey();
  return key ? { "X-TMDB-API-Key": key } : {};
}

async function tmdb(path) {
  const response = await fetch(`${BACKEND_URL}/tmdb/${path}`, {
    headers: tmdbHeaders(),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.status_message || data.error || "TMDB request failed");
  }
  return data;
}

async function loadTrending() {
  if (!requireKey()) return;
  setStatus("正在載入趨勢電影...");
  try {
    const data = await tmdb("trending/movie/week?language=zh-TW&page=1");
    activeMovies = normalizeMovies(data.results || []);
    renderMovieGrid(activeMovies, "movieGrid");
    setStatus(`已載入 ${activeMovies.length} 部趨勢電影。`);
  } catch (error) {
    setStatus(`載入失敗：${error.message}`);
  }
}

async function runSearch() {
  if (!requireKey()) return;
  const query = document.getElementById("searchInput").value.trim();
  if (!query) {
    loadTrending();
    return;
  }
  setStatus(`正在搜尋 ${query}...`);
  try {
    const data = await tmdb(`search/movie?query=${encodeURIComponent(query)}&language=zh-TW&page=1`);
    activeMovies = normalizeMovies(data.results || []);
    renderMovieGrid(activeMovies, "movieGrid");
    setStatus(`找到 ${activeMovies.length} 部電影。`);
  } catch (error) {
    setStatus(`搜尋失敗：${error.message}`);
  }
}

async function loadRecommendations() {
  if (!requireKey()) return;
  const favorites = getFavorites();
  if (favorites.length === 0) {
    document.getElementById("recommendationReason").textContent = "請先收藏幾部你喜歡的電影。";
    return;
  }

  const profile = buildTasteProfile(favorites);
  const favoriteIds = new Set(favorites.map((movie) => movie.id));

  document.getElementById("recommendationReason").textContent = "正在根據你的收藏建立推薦...";

  try {
    const semanticResults = await loadSemanticRecommendations(favorites);
    if (semanticResults.length > 0) {
      renderMovieGrid(semanticResults, "recommendationGrid", true);
      document.getElementById("recommendationReason").textContent =
        `已使用 BERT 語意向量服務，根據 ${favorites.length} 部收藏建立推薦。`;
      return;
    }
  } catch {
    // The semantic service is optional. The public demo falls back to TMDB metadata ranking.
  }

  if (profile.genreIds.length === 0) {
    document.getElementById("recommendationReason").textContent = "收藏的電影缺少類型資料，請再收藏幾部電影。";
    return;
  }

  try {
    const genreQuery = profile.genreIds.slice(0, 3).join(",");
    const data = await tmdb(
      `discover/movie?language=zh-TW&sort_by=vote_average.desc&vote_count.gte=150&with_genres=${genreQuery}&page=1`
    );
    const candidates = normalizeMovies(data.results || [])
      .filter((movie) => !favoriteIds.has(movie.id))
      .map((movie) => ({
        ...movie,
        recommendationScore: scoreMovie(movie, profile),
      }))
      .sort((a, b) => b.recommendationScore - a.recommendationScore)
      .slice(0, 18);

    renderMovieGrid(candidates, "recommendationGrid", true);
    document.getElementById("recommendationReason").textContent =
      `已用 TMDB metadata，根據 ${favorites.length} 部收藏建立推薦。`;
  } catch (error) {
    document.getElementById("recommendationReason").textContent = `推薦失敗：${error.message}`;
  }
}

async function loadSemanticRecommendations(favorites) {
  const payload = {
    overviews: favorites.map((movie) => movie.overview).filter(Boolean),
    exclude_ids: favorites.map((movie) => movie.id),
    user_genre_ids: favorites.map((movie) => movie.genre_ids || []),
    user_vote_counts: favorites.map((movie) => movie.vote_count || 0),
    top_k: 18,
  };

  if (payload.overviews.length === 0) {
    return [];
  }

  const response = await fetch(`${BACKEND_URL}/semantic-recommendations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    return [];
  }

  const data = await response.json();
  return normalizeSemanticMovies(data.results || []);
}

function normalizeMovies(movies) {
  return movies
    .filter((movie) => movie && movie.poster_path)
    .map((movie) => ({
      id: movie.id,
      title: movie.title || movie.name || "Untitled",
      overview: movie.overview || "",
      poster_path: movie.poster_path,
      release_date: movie.release_date || "",
      vote_average: Number(movie.vote_average || 0),
      vote_count: Number(movie.vote_count || 0),
      genre_ids: movie.genre_ids || [],
    }));
}

function normalizeSemanticMovies(movies) {
  return movies
    .filter((movie) => movie && movie.poster_path)
    .map((movie) => {
      const rawScore = Number(movie.score || movie.semantic_score || 0);
      const score = rawScore <= 1 ? rawScore * 100 : rawScore;
      return {
        id: movie.id,
        title: movie.title || "Untitled",
        overview: movie.overview || "",
        poster_path: movie.poster_path,
        release_date: movie.release_date || "",
        vote_average: Number(movie.vote_average || 0),
        vote_count: Number(movie.vote_count || 0),
        genre_ids: movie.genre_ids || [],
        recommendationScore: Math.max(1, Math.min(100, score)),
      };
    });
}

function renderMovieGrid(movies, targetId, showScore = false) {
  const grid = document.getElementById(targetId);
  const favorites = new Set(getFavorites().map((movie) => movie.id));
  grid.innerHTML = "";

  if (movies.length === 0) {
    grid.innerHTML = `<div class="col-span-full rounded-xl border border-white/10 p-8 text-center text-white/45">沒有找到電影。</div>`;
    return;
  }

  movies.forEach((movie) => {
    const card = document.createElement("article");
    card.className = "poster-card overflow-hidden rounded-2xl";
    const active = favorites.has(movie.id);
    const year = movie.release_date ? movie.release_date.slice(0, 4) : "N/A";
    const score = showScore && movie.recommendationScore
      ? `<span class="rounded-full bg-[#5db8a6]/20 px-2 py-1 text-[11px] font-semibold text-[#9df0de]">match ${Math.round(movie.recommendationScore)}</span>`
      : "";

    card.innerHTML = `
      <img class="aspect-[2/3] w-full object-cover" src="${IMAGE_BASE}${movie.poster_path}" alt="${escapeHtml(movie.title)}" loading="lazy">
      <div class="space-y-3 p-3">
        <div>
          <h3 class="line-clamp-2 min-h-[2.5rem] text-sm font-semibold">${escapeHtml(movie.title)}</h3>
          <div class="mt-2 flex items-center justify-between text-xs text-white/50">
            <span>${year}</span>
            <span>★ ${movie.vote_average.toFixed(1)}</span>
          </div>
        </div>
        <p class="line-clamp-3 min-h-[3.75rem] text-xs leading-5 text-white/48">${escapeHtml(movie.overview || "暫無簡介")}</p>
        <div class="flex items-center justify-between gap-2">
          ${score}
          <button class="favorite-btn ml-auto rounded-lg border border-white/10 px-3 py-2 text-xs font-semibold transition ${active ? "bg-[#cc785c] text-white" : "text-white/70 hover:bg-white/10"}">
            ${active ? "已收藏" : "加入收藏"}
          </button>
        </div>
      </div>
    `;

    card.querySelector(".favorite-btn").addEventListener("click", () => toggleFavorite(movie));
    grid.appendChild(card);
  });
}

function toggleFavorite(movie) {
  const favorites = getFavorites();
  const exists = favorites.some((item) => item.id === movie.id);
  const next = exists
    ? favorites.filter((item) => item.id !== movie.id)
    : [...favorites, movie];
  saveFavorites(next);
  renderFavorites();
  renderMovieGrid(activeMovies, "movieGrid");

  const recommendations = Array.from(document.querySelectorAll("#recommendationGrid article"));
  if (recommendations.length > 0) {
    loadRecommendations();
  }
}

function renderFavorites() {
  const favorites = getFavorites();
  document.getElementById("favoriteSummary").textContent =
    favorites.length === 0
      ? "尚未收藏電影。"
      : `已收藏 ${favorites.length} 部電影，會用來建立 taste profile。`;

  const list = document.getElementById("favoriteList");
  list.innerHTML = "";
  favorites.forEach((movie) => {
    const item = document.createElement("button");
    item.className = "rounded-full border border-white/10 bg-white/5 px-3 py-2 text-xs text-white/75 transition hover:bg-white/10";
    item.textContent = movie.title;
    item.addEventListener("click", () => toggleFavorite(movie));
    list.appendChild(item);
  });
}

function buildTasteProfile(favorites) {
  const genreWeights = new Map();
  let avgVote = 0;
  favorites.forEach((movie) => {
    avgVote += movie.vote_average || 0;
    (movie.genre_ids || []).forEach((genreId) => {
      genreWeights.set(genreId, (genreWeights.get(genreId) || 0) + 1);
    });
  });

  const genreIds = [...genreWeights.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([genreId]) => genreId);

  return {
    genreIds,
    genreWeights,
    avgVote: favorites.length ? avgVote / favorites.length : 0,
  };
}

function scoreMovie(movie, profile) {
  const genreScore = (movie.genre_ids || []).reduce((sum, genreId) => {
    return sum + (profile.genreWeights.get(genreId) || 0);
  }, 0);
  const ratingScore = Math.max(0, movie.vote_average - 5) * 7;
  const voteScore = Math.min(20, Math.log10(Math.max(1, movie.vote_count)) * 6);
  const tasteScore = Math.max(0, 10 - Math.abs((movie.vote_average || 0) - profile.avgVote)) * 2;
  return genreScore * 25 + ratingScore + voteScore + tasteScore;
}

function requireKey() {
  if (getApiKey()) return true;
  setStatus("請先輸入並儲存 TMDB API key。");
  return false;
}

function setStatus(message) {
  document.getElementById("keyStatus").textContent = message;
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value || "";
  return div.innerHTML;
}

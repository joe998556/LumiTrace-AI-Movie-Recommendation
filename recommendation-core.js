/* Shared recommendation state and request helpers for LumiTrace pages. */
(function () {
  "use strict";

  const KEYS = Object.freeze({
    favorites: "lumitrace_favorites",
    ratings: "lumitrace_ratings",
    feedback: "lumitrace_feedback",
    llmSession: "lumitrace_llm_session",
    llmRemembered: "lumitrace_llm_remembered",
    legacyLlm: "lumitrace_llm",
    searchUrl: "lumitrace_search_url",
    onboarding: "lumitrace_onboarding",
  });

  function readJson(storage, key, fallback) {
    try {
      const parsed = JSON.parse(storage.getItem(key) || "");
      return parsed && typeof parsed === "object" ? parsed : fallback;
    } catch {
      return fallback;
    }
  }

  function writeJson(storage, key, value) {
    storage.setItem(key, JSON.stringify(value));
  }

  function movieYear(movie) {
    const value = Number(String(movie?.release_date || "").slice(0, 4));
    return Number.isFinite(value) && value >= 1888 && value <= 2100 ? value : null;
  }

  function normalizedMovie(movie) {
    return {
      id: Number(movie?.id),
      title: String(movie?.title || movie?.name || "Untitled"),
      overview: String(movie?.overview || ""),
      poster_path: String(movie?.poster_path || ""),
      release_date: String(movie?.release_date || ""),
      vote_average: Number(movie?.vote_average || 0),
      vote_count: Number(movie?.vote_count || 0),
      genre_ids: Array.isArray(movie?.genre_ids) ? movie.genre_ids.map(Number).filter(Number.isFinite) : [],
      original_language: String(movie?.original_language || "").toLowerCase(),
    };
  }

  function getLlmConfig() {
    const session = readJson(sessionStorage, KEYS.llmSession, null);
    if (session?.api_url) return session;
    const remembered = readJson(localStorage, KEYS.llmRemembered, null);
    if (remembered?.api_url) {
      writeJson(sessionStorage, KEYS.llmSession, remembered);
      return remembered;
    }
    const legacy = readJson(localStorage, KEYS.legacyLlm, null);
    if (legacy?.api_url) {
      writeJson(sessionStorage, KEYS.llmSession, legacy);
      localStorage.removeItem(KEYS.legacyLlm);
      return legacy;
    }
    return {};
  }

  function saveLlmConfig(config, remember) {
    const clean = {
      api_url: String(config?.api_url || "").trim(),
      api_key: String(config?.api_key || "").trim(),
      model: String(config?.model || "").trim(),
    };
    writeJson(sessionStorage, KEYS.llmSession, clean);
    if (remember) writeJson(localStorage, KEYS.llmRemembered, clean);
    else localStorage.removeItem(KEYS.llmRemembered);
    return clean;
  }

  function clearLlmConfig() {
    sessionStorage.removeItem(KEYS.llmSession);
    localStorage.removeItem(KEYS.llmRemembered);
    localStorage.removeItem(KEYS.legacyLlm);
  }

  function getFeedback() {
    return readJson(localStorage, KEYS.feedback, {});
  }

  function recordFeedback(movie, direction) {
    const feedback = getFeedback();
    feedback[String(movie.id)] = {
      movie: normalizedMovie(movie),
      direction: direction === "less" ? "less" : "more",
      updated_at: Date.now(),
    };
    writeJson(localStorage, KEYS.feedback, feedback);
    return feedback;
  }

  function removeFeedback(movieId) {
    const feedback = getFeedback();
    delete feedback[String(movieId)];
    writeJson(localStorage, KEYS.feedback, feedback);
  }

  function tasteItems(favorites, ratings) {
    const items = new Map();
    (favorites || []).forEach((movie) => {
      const item = normalizedMovie(movie);
      if (!Number.isFinite(item.id)) return;
      const rating = Number(ratings?.[item.id]?.score || 5);
      items.set(item.id, { movie: item, rating: Math.max(1, Math.min(10, rating)), source: "saved" });
    });
    Object.values(getFeedback()).forEach((entry) => {
      if (!entry?.movie?.id) return;
      const item = normalizedMovie(entry.movie);
      items.set(item.id, { movie: item, rating: entry.direction === "less" ? 2 : 9, source: entry.direction });
    });
    return [...items.values()];
  }

  function buildPayload({ favorites = [], ratings = {}, prompt = "", topK = 18, diversity = 0.55, language = "", genre = "" } = {}) {
    const items = tasteItems(favorites, ratings);
    const payload = {
      items: items.map((item) => ({
        tmdb_id: item.movie.id,
        rating: item.rating,
        genre_ids: item.movie.genre_ids || [],
      })),
      // Legacy parallel arrays keep older self-hosted gateways compatible.
      user_movie_ids: items.map((item) => item.movie.id),
      exclude_ids: items.map((item) => item.movie.id),
      user_genre_ids: items.map((item) => item.movie.genre_ids || []),
      user_vote_counts: items.map((item) => item.rating),
      user_release_years: items.map((item) => movieYear(item.movie)).filter(Boolean),
      overviews: prompt.trim() ? [prompt.trim()] : [],
      playlist_genre_ids: genre ? [Number(genre)] : [],
      preferred_languages: language ? [language] : [],
      diversity: Math.max(0, Math.min(1, Number(diversity) || 0.55)),
      top_k: Math.max(1, Math.min(30, Number(topK) || 18)),
    };
    return withRequestExtras(payload);
  }

  function withRequestExtras(payload) {
    const next = { ...payload };
    const llm = getLlmConfig();
    if (window.__lumitraceClientLlm === true && llm.api_url && llm.model) next.llm = llm;
    const override = String(localStorage.getItem(KEYS.searchUrl) || "").trim();
    const locked = Boolean(window.__lumitraceRemoteLocked || window.__lumitraceSearchLocked);
    if (override && !locked) next.remote_search_url = override;
    return next;
  }

  async function requestRecommendations(apiBase, payload) {
    const response = await fetch(`${apiBase}/recommendations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok || body.error) throw new Error(body.error || "Recommendation request failed");
    return body;
  }

  function normalizeResults(raw) {
    const filtered = (Array.isArray(raw) ? raw : []).filter((movie) => Number.isFinite(Number(movie?.id)));
    const movies = filtered.map(normalizedMovie);
    const highest = Math.max(0.001, ...movies.map((movie) => Number(movie.score || movie.semantic_score || 0)));
    return movies.map((movie, index) => {
      const source = filtered[index] || {};
      const value = Number(source.score || source.semantic_score || 0);
      return {
        ...movie,
        score: value,
        semantic_score: Number(source.semantic_score || value || 0),
        recommendationScore: Math.max(1, Math.min(99, Math.round((value / highest) * 68 + 31))),
        negative_penalty: Number(source.negative_penalty || 0),
        diversity_penalty: Number(source.diversity_penalty || 0),
        evidence: source.evidence || {},
        llm_reason: String(source.llm_reason || ""),
      };
    });
  }

  async function hydrateResults(raw, fetchMovie, batchSize = 5) {
    const movies = normalizeResults(raw);
    if (typeof fetchMovie !== "function") return movies.filter((movie) => movie.poster_path);
    const hydrated = [];
    const size = Math.max(1, Math.min(10, Number(batchSize) || 5));
    for (let start = 0; start < movies.length; start += size) {
      const batch = movies.slice(start, start + size);
      const rows = await Promise.all(batch.map(async (movie) => {
        if (movie.poster_path) return movie;
        try {
          const detail = normalizedMovie(await fetchMovie(movie.id));
          return {
            ...movie,
            ...detail,
            score: movie.score,
            semantic_score: movie.semantic_score,
            recommendationScore: movie.recommendationScore,
            negative_penalty: movie.negative_penalty,
            diversity_penalty: movie.diversity_penalty,
            evidence: movie.evidence,
            llm_reason: movie.llm_reason,
          };
        } catch {
          return movie;
        }
      }));
      hydrated.push(...rows);
    }
    return hydrated.filter((movie) => movie.poster_path);
  }

  function evidenceRows(movie, genreNames = {}) {
    const evidence = movie?.evidence || {};
    const rows = [];
    const similar = Array.isArray(evidence.similar_to) ? evidence.similar_to.filter(Boolean) : [];
    const genres = (evidence.matched_genre_ids || []).map((id) => genreNames[id] || `Genre ${id}`);
    if (similar.length) rows.push({ label: "Similar taste", value: similar.join(" + ") });
    if (genres.length) rows.push({ label: "Genre signal", value: genres.join(", ") });
    if (evidence.rating_weight) rows.push({ label: "Rating weight", value: `${Number(evidence.rating_weight).toFixed(1)}/10 preference signal` });
    if (evidence.avoids_disliked) rows.push({ label: "Avoided", value: evidence.disliked_titles?.length ? `Reduced similarity to ${evidence.disliked_titles.join(", ")}` : "Reduced similarity to low-rated films" });
    if (movie.llm_reason) rows.push({ label: "AI narration", value: movie.llm_reason });
    return rows;
  }

  function compareMovies(left, right, genreNames = {}) {
    const leftGenres = new Set(left?.genre_ids || []);
    const rightGenres = new Set(right?.genre_ids || []);
    const shared = [...leftGenres].filter((genre) => rightGenres.has(genre)).map((genre) => genreNames[genre] || `Genre ${genre}`);
    const leftOnly = [...leftGenres].filter((genre) => !rightGenres.has(genre)).map((genre) => genreNames[genre] || `Genre ${genre}`);
    const rightOnly = [...rightGenres].filter((genre) => !leftGenres.has(genre)).map((genre) => genreNames[genre] || `Genre ${genre}`);
    const leftYear = movieYear(left);
    const rightYear = movieYear(right);
    return {
      shared,
      differences: [
        leftOnly.length || rightOnly.length ? `${left?.title} leans ${leftOnly.join(", ") || "elsewhere"}; ${right?.title} leans ${rightOnly.join(", ") || "elsewhere"}.` : "Their genre mix is closely aligned.",
        leftYear && rightYear ? `${Math.abs(leftYear - rightYear)} years apart (${leftYear} vs ${rightYear}).` : "Release-year comparison is unavailable.",
      ],
    };
  }

  function tasteSnapshot(favorites, ratings, genreNames = {}) {
    const movies = favorites || [];
    const rated = movies.map((movie) => ({ movie, rating: Number(ratings?.[movie.id]?.score || 0) })).filter((item) => item.rating > 0);
    const genreWeights = new Map();
    rated.forEach(({ movie, rating }) => (movie.genre_ids || []).forEach((genre) => genreWeights.set(genre, (genreWeights.get(genre) || 0) + rating)));
    const topGenres = [...genreWeights.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3).map(([genre]) => genreNames[genre] || `Genre ${genre}`);
    const topRated = [...rated].sort((a, b) => b.rating - a.rating).slice(0, 3);
    const byMonth = new Map();
    rated.forEach(({ rating, movie }) => {
      const time = Number(ratings?.[movie.id]?.updatedAt || 0);
      if (!time) return;
      const month = new Date(time).toLocaleDateString(undefined, { month: "short", year: "numeric" });
      byMonth.set(month, (byMonth.get(month) || 0) + 1);
    });
    return {
      watched: movies.length,
      rated: rated.length,
      average: rated.length ? rated.reduce((sum, item) => sum + item.rating, 0) / rated.length : 0,
      topGenres,
      topRated,
      months: [...byMonth.entries()].slice(-6),
    };
  }

  function exportTaste() {
    return {
      version: 1,
      exported_at: new Date().toISOString(),
      favorites: readJson(localStorage, KEYS.favorites, []),
      ratings: readJson(localStorage, KEYS.ratings, {}),
      feedback: getFeedback(),
      onboarding: readJson(localStorage, KEYS.onboarding, {}),
    };
  }

  function importTaste(data) {
    if (!data || typeof data !== "object" || !Array.isArray(data.favorites)) throw new Error("This is not a LumiTrace taste export.");
    writeJson(localStorage, KEYS.favorites, data.favorites.map(normalizedMovie).filter((movie) => Number.isFinite(movie.id)));
    writeJson(localStorage, KEYS.ratings, data.ratings && typeof data.ratings === "object" ? data.ratings : {});
    writeJson(localStorage, KEYS.feedback, data.feedback && typeof data.feedback === "object" ? data.feedback : {});
    if (data.onboarding && typeof data.onboarding === "object") writeJson(localStorage, KEYS.onboarding, data.onboarding);
  }

  function randomPick(movies, excludedId) {
    const choices = (movies || []).filter((movie) => movie.id !== excludedId);
    return choices.length ? choices[Math.floor(Math.random() * choices.length)] : null;
  }

  window.LumiTraceRecs = Object.freeze({
    KEYS,
    buildPayload,
    compareMovies,
    clearLlmConfig,
    evidenceRows,
    exportTaste,
    getFeedback,
    getLlmConfig,
    hydrateResults,
    importTaste,
    movieYear,
    normalizeResults,
    randomPick,
    recordFeedback,
    removeFeedback,
    requestRecommendations,
    saveLlmConfig,
    tasteItems,
    tasteSnapshot,
    withRequestExtras,
  });
})();

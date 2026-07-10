/* LumiTrace product interactions: onboarding, choice modes, and private taste tools. */
(function () {
  "use strict";

  const core = () => window.LumiTraceRecs;
  const state = { results: [], compare: [], rouletteDraws: 0, rouletteLast: null, tonightPicks: [], tonightRerolls: 0, onboardingQueue: [] };
  const imageBase = "https://image.tmdb.org/t/p/w500";
  const genreNames = window.GENRE_NAMES || {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime", 18: "Drama", 14: "Fantasy", 27: "Horror", 9648: "Mystery", 10749: "Romance", 878: "Sci-Fi", 53: "Thriller",
  };

  function escapeHtml(value) {
    const node = document.createElement("div");
    node.textContent = String(value || "");
    return node.innerHTML;
  }

  function favorites() { return typeof window.getFavorites === "function" ? window.getFavorites() : []; }
  function ratings() { return typeof window.getRatings === "function" ? window.getRatings() : {}; }
  function apiBase() { return window.LumiTraceConfig?.apiBase || "/api"; }

  function showToast(message) {
    let toast = document.getElementById("experienceToast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "experienceToast";
      toast.className = "experience-toast";
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add("is-visible");
    clearTimeout(showToast.timeout);
    showToast.timeout = setTimeout(() => toast.classList.remove("is-visible"), 2600);
  }

  function ensureModal() {
    let modal = document.getElementById("experienceModal");
    if (modal) return modal;
    modal = document.createElement("div");
    modal.id = "experienceModal";
    modal.className = "experience-modal";
    modal.innerHTML = '<div class="experience-backdrop" data-experience-close></div><section class="experience-dialog" role="dialog" aria-modal="true"><button class="experience-close" type="button" data-experience-close aria-label="Close">x</button><div id="experienceModalBody"></div></section>';
    document.body.appendChild(modal);
    modal.addEventListener("click", (event) => {
      if (event.target.closest("[data-experience-close]")) closeModal();
    });
    return modal;
  }

  function openModal(html, className = "") {
    const modal = ensureModal();
    modal.querySelector(".experience-dialog").className = `experience-dialog ${className}`.trim();
    modal.querySelector("#experienceModalBody").innerHTML = html;
    modal.classList.add("is-open");
    requestAnimationFrame(() => modal.querySelector(".experience-dialog").classList.add("is-live"));
    return modal;
  }

  function closeModal() {
    const modal = document.getElementById("experienceModal");
    if (!modal) return;
    modal.querySelector(".experience-dialog")?.classList.remove("is-live");
    setTimeout(() => modal.classList.remove("is-open"), 360);
  }

  function setRecommendationResults(movies, headline) {
    state.results = movies;
    if (typeof window.renderRecGrid === "function") window.renderRecGrid(movies);
    const reason = document.getElementById("recommendationReason");
    if (reason) reason.textContent = headline;
    if (typeof window.openPanel === "function") window.openPanel();
  }

  async function runSemantic({ prompt = "", sourceFavorites = favorites(), sourceRatings = ratings(), topK = 18, diversity = window.__lumiDiversity ?? 0.55, language = "", genre = "" } = {}) {
    const payload = core().buildPayload({ favorites: sourceFavorites, ratings: sourceRatings, prompt, topK, diversity, language, genre });
    if (!payload.user_movie_ids.length && !payload.overviews.length) {
      showToast("Choose a few films first, or describe the mood you want.");
      return [];
    }
    const response = await core().requestRecommendations(apiBase(), payload);
    const movies = await core().hydrateResults(
      response.results || [],
      (id) => window.tmdb(`movie/${id}?language=en-US`),
    );
    if (!movies.length) throw new Error(response.fallback || "No recommendations yet.");
    return movies;
  }

  function renderOnboardingCard(movie, onboarding) {
    const poster = movie.poster_path ? `${imageBase}${movie.poster_path}` : "";
    const progress = Math.min(10, onboarding.reviewed || 0);
    return `
      <div class="onboarding-shell">
        <div class="onboarding-head">
          <span class="eyebrow">First signal</span>
          <span class="onboarding-progress">${progress}<small>/10</small></span>
        </div>
        <div id="onboardingCard" class="onboarding-card">
          <div class="onboarding-poster">${poster ? `<img src="${poster}" alt="${escapeHtml(movie.title)} poster">` : "<span>L</span>"}</div>
          <div class="onboarding-copy">
            <p class="section-kicker">Does this feel like you?</p>
            <h2>${escapeHtml(movie.title)}</h2>
            <p>${escapeHtml(movie.overview || "A film from the LumiTrace discovery pool.")}</p>
            <div class="onboarding-meta"><span>${escapeHtml((movie.release_date || "").slice(0, 4) || "New")}</span><span>TMDB ${Number(movie.vote_average || 0).toFixed(1)}</span></div>
          </div>
        </div>
        <div class="onboarding-actions">
          <button class="onboarding-choice is-like" data-onboarding-choice="like" type="button"><span>Like</span><i>+</i></button>
          <button class="onboarding-choice is-skip" data-onboarding-choice="skip" type="button"><span>Not seen</span><i>o</i></button>
          <button class="onboarding-choice is-less" data-onboarding-choice="less" type="button"><span>Not for me</span><i>-</i></button>
        </div>
        <button class="onboarding-later" data-onboarding-later type="button">Do this later</button>
      </div>`;
  }

  async function fetchOnboardingQueue() {
    const endpoints = ["movie/popular?page=1", "movie/top_rated?page=1", "discover/movie?sort_by=popularity.desc&page=2"];
    const responses = await Promise.all(endpoints.map((endpoint) => window.tmdb(endpoint).catch(() => ({ results: [] }))));
    const pool = responses.flatMap((response) => response.results || []).map((movie) => core().normalizeResults([{ ...movie, score: movie.vote_average || 0 }])[0]).filter(Boolean);
    const seen = new Set();
    const unique = pool.filter((movie) => movie.poster_path && !seen.has(movie.id) && seen.add(movie.id));
    for (let index = unique.length - 1; index > 0; index -= 1) {
      const swap = Math.floor(Math.random() * (index + 1));
      [unique[index], unique[swap]] = [unique[swap], unique[index]];
    }
    return unique.slice(0, 18);
  }

  function onboardingState() {
    return JSON.parse(localStorage.getItem(core().KEYS.onboarding) || "{}");
  }

  function saveOnboarding(stateValue) {
    localStorage.setItem(core().KEYS.onboarding, JSON.stringify(stateValue));
  }

  async function openOnboarding() {
    const onboarding = onboardingState();
    if (onboarding.completed) return;
    if (typeof window.hasTmdbAccess === "function" && !window.hasTmdbAccess()) {
      openModal(`
        <div class="onboarding-shell onboarding-gate">
          <span class="eyebrow">First signal</span>
          <h2>Pick ten films that feel like you.</h2>
          <p>Connect your TMDB key first. LumiTrace will then deal a private set of movie cards and build your first taste profile.</p>
          <a class="btn btn-primary" href="/settings.html">Open Settings <span class="btn-icon">-&gt;</span></a>
        </div>`, "onboarding-dialog");
      return;
    }
    if (!state.onboardingQueue.length) state.onboardingQueue = await fetchOnboardingQueue();
    const movie = state.onboardingQueue.shift();
    if (!movie) return;
    openModal(renderOnboardingCard(movie, onboarding), "onboarding-dialog");
    const modal = document.getElementById("experienceModal");
    modal.querySelectorAll("[data-onboarding-choice]").forEach((button) => button.addEventListener("click", () => decideOnboarding(movie, button.dataset.onboardingChoice)));
    modal.querySelector("[data-onboarding-later]")?.addEventListener("click", () => {
      saveOnboarding({ ...onboarding, snoozed_until: Date.now() + 1000 * 60 * 60 * 12 });
      closeModal();
    });
  }

  async function decideOnboarding(movie, choice) {
    const card = document.getElementById("onboardingCard");
    if (!card) return;
    document.querySelectorAll("[data-onboarding-choice]").forEach((button) => { button.disabled = true; });
    card.classList.add(`is-dealing-${choice}`);
    const current = onboardingState();
    if (choice === "like") {
      const all = favorites();
      if (!all.some((item) => item.id === movie.id)) window.saveFavorites([...all, movie]);
      window.saveRating(movie.id, 9, "First signal");
    } else if (choice === "less") {
      core().recordFeedback(movie, "less");
    }
    const next = { ...current, reviewed: Math.min(10, Number(current.reviewed || 0) + 1) };
    setTimeout(async () => {
      if (next.reviewed >= 10) {
        next.completed = true;
        saveOnboarding(next);
        closeModal();
        showToast("Taste signal captured. Building your first recommendations...");
        try {
          const movies = await runSemantic({ topK: 18 });
          setRecommendationResults(movies, "Your first taste trace is ready.");
        } catch (error) { showToast(error.message); }
        return;
      }
      saveOnboarding(next);
      await openOnboarding();
    }, 520);
  }

  function openTonight() {
    openModal(`
      <div class="mode-shell">
        <span class="eyebrow">Tonight</span><h2>One film. The right mood.</h2>
        <p>Choose the shape of the evening. LumiTrace will return one best-fit pick and give you one redraw.</p>
        <div class="mode-grid">
          <label>When<select id="tonightTime"><option value="a quiet weeknight">Weeknight</option><option value="a relaxed weekend">Weekend</option><option value="late at night">Late night</option><option value="an afternoon break">Afternoon</option></select></label>
          <label>Feeling<select id="tonightMood"><option value="warm and restorative">Warm</option><option value="tense and atmospheric">Tense</option><option value="funny and light">Light</option><option value="curious and cerebral">Curious</option></select></label>
          <label>Runtime<select id="tonightRuntime"><option value="under two hours">Under 2 hours</option><option value="around two hours">Around 2 hours</option><option value="any runtime">Any length</option></select></label>
          <label>Thinking<select id="tonightThinking"><option value="easy to follow and not mentally demanding">Keep it easy</option><option value="with a little to unpack">A little depth</option><option value="challenging and thought-provoking">Challenge me</option></select></label>
        </div>
        <button id="tonightGenerate" class="btn btn-primary" type="button">Choose tonight's film <span class="btn-icon">-&gt;</span></button>
        <div id="tonightResult" class="tonight-result"></div>
      </div>`, "mode-dialog");
    document.getElementById("tonightGenerate").addEventListener("click", async () => {
      const prompt = `A ${document.getElementById("tonightMood").value} movie for ${document.getElementById("tonightTime").value}, ${document.getElementById("tonightRuntime").value}, and ${document.getElementById("tonightThinking").value}.`;
      try {
        const movies = await runSemantic({ prompt, topK: 8, diversity: window.__lumiDiversity ?? 0.55 });
        state.tonightPicks = movies;
        state.tonightRerolls = 0;
        renderTonightPick(core().randomPick(movies));
      } catch (error) { showToast(error.message); }
    });
  }

  function renderTonightPick(movie) {
    const target = document.getElementById("tonightResult");
    if (!target || !movie) return;
    state.rouletteLast = movie.id;
    target.innerHTML = `<article class="tonight-card"><img src="${imageBase}${movie.poster_path}" alt="${escapeHtml(movie.title)}"><div><span class="section-kicker">Tonight's pick</span><h3>${escapeHtml(movie.title)}</h3><p>${(core().evidenceRows(movie, genreNames)[0]?.value || "A focused match for your current mood.")}</p><div class="button-row"><button id="tonightKeep" class="btn btn-primary" type="button">Take this pick</button><button id="tonightReroll" class="btn btn-ghost" type="button">One redraw</button></div></div></article>`;
    document.getElementById("tonightKeep").addEventListener("click", () => { setRecommendationResults([movie], "Tonight's focused pick."); closeModal(); });
    document.getElementById("tonightReroll").addEventListener("click", () => {
      if (state.tonightRerolls >= 1) { showToast("Your redraw has already been used."); return; }
      state.tonightRerolls += 1;
      renderTonightPick(core().randomPick(state.tonightPicks, state.rouletteLast));
    });
  }

  function openCouple() {
    const pool = favorites();
    if (pool.length < 2) { showToast("Save a few films before making a shared list."); return; }
    const choices = (person) => pool.map((movie) => `<label class="couple-choice"><input type="checkbox" data-couple="${person}" value="${movie.id}"><span>${escapeHtml(movie.title)}</span></label>`).join("");
    openModal(`<div class="mode-shell"><span class="eyebrow">Two people</span><h2>Find the overlap.</h2><p>Choose up to three films for each person. LumiTrace looks for a neutral, shared lane.</p><div class="couple-columns"><div><h3>Person A</h3>${choices("a")}</div><div><h3>Person B</h3>${choices("b")}</div></div><button id="coupleGenerate" class="btn btn-primary" type="button">Find a shared pick <span class="btn-icon">-&gt;</span></button></div>`, "mode-dialog wide-dialog");
    document.getElementById("coupleGenerate").addEventListener("click", async () => {
      const idsA = [...document.querySelectorAll('[data-couple="a"]:checked')].slice(0, 3).map((input) => Number(input.value));
      const idsB = [...document.querySelectorAll('[data-couple="b"]:checked')].slice(0, 3).map((input) => Number(input.value));
      if (!idsA.length || !idsB.length) { showToast("Choose at least one film for each person."); return; }
      const lookup = new Map(pool.map((movie) => [movie.id, movie]));
      const combined = [...new Set([...idsA, ...idsB])].map((id) => lookup.get(id)).filter(Boolean);
      const sharedRatings = Object.fromEntries(combined.map((movie) => [movie.id, { score: 8 }]));
      try {
        const movies = await runSemantic({ sourceFavorites: combined, sourceRatings: sharedRatings, topK: 12, diversity: 0.8 });
        setRecommendationResults(movies, `Shared taste trace from ${idsA.length} + ${idsB.length} films.`);
        closeModal();
      } catch (error) { showToast(error.message); }
    });
  }

  function openTasteMap() {
    const snapshot = core().tasteSnapshot(favorites(), ratings(), genreNames);
    const islands = snapshot.topGenres.length ? snapshot.topGenres.map((genre, index) => `<div class="taste-island taste-island-${index}"><span>${index + 1}</span><b>${escapeHtml(genre)}</b><small>taste island</small></div>`).join("") : '<p class="empty-inline">Save and rate a few films to reveal your map.</p>';
    openModal(`<div class="mode-shell"><span class="eyebrow">Taste map</span><h2>Your viewing islands.</h2><div class="map-metrics"><div><b>${snapshot.watched}</b><span>saved</span></div><div><b>${snapshot.rated}</b><span>rated</span></div><div><b>${snapshot.average ? snapshot.average.toFixed(1) : "-"}</b><span>average</span></div></div><div class="taste-map">${islands}</div></div>`, "mode-dialog");
  }

  function openJournal() {
    const snapshot = core().tasteSnapshot(favorites(), ratings(), genreNames);
    const topRated = snapshot.topRated.length ? snapshot.topRated.map(({ movie, rating }) => `<li><span>${escapeHtml(movie.title)}</span><b>${rating.toFixed(1)}</b></li>`).join("") : '<li><span>No ratings yet</span></li>';
    const months = snapshot.months.length ? snapshot.months.map(([month, count]) => `<span class="journal-bar" style="--bar:${Math.min(100, count * 24)}%"><b>${count}</b><small>${escapeHtml(month)}</small></span>`).join("") : '<p class="empty-inline">Your diary starts when you rate a film.</p>';
    openModal(`<div class="mode-shell"><span class="eyebrow">Private journal</span><h2>Your taste, over time.</h2><div class="journal-layout"><section><p class="section-kicker">Top rated</p><ul class="journal-list">${topRated}</ul></section><section><p class="section-kicker">Most present</p><p class="journal-genres">${snapshot.topGenres.map(escapeHtml).join(" / ") || "Still forming"}</p></section></div><div class="journal-chart">${months}</div></div>`, "mode-dialog");
  }

  function openDataTools() {
    openModal(`<div class="mode-shell"><span class="eyebrow">Private data</span><h2>Keep your taste portable.</h2><p>Your export contains saved films, ratings, feedback, and onboarding state. It never includes your TMDB or LLM keys.</p><div class="button-row"><button id="exportTaste" class="btn btn-primary" type="button">Export JSON <span class="btn-icon">-&gt;</span></button><label class="btn btn-ghost import-label">Import JSON<input id="importTaste" type="file" accept="application/json"></label></div><p id="dataStatus" class="status-line"></p></div>`, "mode-dialog");
    document.getElementById("exportTaste").addEventListener("click", () => {
      const blob = new Blob([JSON.stringify(core().exportTaste(), null, 2)], { type: "application/json" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `lumitrace-taste-${new Date().toISOString().slice(0, 10)}.json`;
      link.click();
      URL.revokeObjectURL(link.href);
    });
    document.getElementById("importTaste").addEventListener("change", async (event) => {
      const file = event.target.files?.[0];
      if (!file) return;
      try {
        core().importTaste(JSON.parse(await file.text()));
        document.getElementById("dataStatus").textContent = "Imported. Refreshing your local collection...";
        setTimeout(() => location.reload(), 550);
      } catch (error) { document.getElementById("dataStatus").textContent = error.message; }
    });
  }

  function openRoulette() {
    if (!state.results.length) { showToast("Open recommendations first, then spin a pick."); return; }
    state.rouletteDraws = 0;
    state.rouletteLast = null;
    openModal(`<div class="roulette-shell"><span class="eyebrow">Decision wheel</span><h2>Let LumiTrace choose.</h2><div id="rouletteDisc" class="roulette-disc"><span>AI</span></div><div id="rouletteReveal" class="roulette-reveal">Ready when you are.</div><button id="rouletteSpin" class="btn btn-primary" type="button">Spin the pick <span class="btn-icon">-&gt;</span></button></div>`, "roulette-dialog");
    document.getElementById("rouletteSpin").addEventListener("click", () => {
      if (state.rouletteDraws >= 2) { showToast("Your one redraw has already been used."); return; }
      const disc = document.getElementById("rouletteDisc");
      disc.classList.remove("is-spinning");
      void disc.offsetWidth;
      disc.classList.add("is-spinning");
      setTimeout(() => {
        const pick = core().randomPick(state.results, state.rouletteLast);
        if (!pick) return;
        state.rouletteLast = pick.id;
        state.rouletteDraws += 1;
        document.getElementById("rouletteReveal").innerHTML = `<b>${escapeHtml(pick.title)}</b><span>${core().evidenceRows(pick, genreNames)[0]?.value || "A strong match from your current list."}</span>`;
        const button = document.getElementById("rouletteSpin");
        button.textContent = state.rouletteDraws === 1 ? "Use one redraw" : "Redraw used";
        button.disabled = state.rouletteDraws >= 2;
      }, 900);
    });
  }

  function handleFeedback(detail) {
    core().recordFeedback(detail.movie, detail.direction);
    showToast(detail.direction === "more" ? "More signal saved. Refreshing the taste trace..." : "Less signal saved. Similar candidates will be reduced.");
    runSemantic({ topK: 18 }).then((movies) => setRecommendationResults(movies, "Updated from your immediate feedback.")).catch((error) => showToast(error.message));
  }

  function handleCompare(movie) {
    const found = state.compare.findIndex((item) => item.id === movie.id);
    if (found >= 0) state.compare.splice(found, 1);
    else state.compare.push(movie);
    if (state.compare.length < 2) { showToast("Choose one more card to compare."); return; }
    const [left, right] = state.compare.splice(0, 2);
    const comparison = core().compareMovies(left, right, genreNames);
    openModal(`<div class="mode-shell"><span class="eyebrow">Compare</span><h2>${escapeHtml(left.title)} / ${escapeHtml(right.title)}</h2><div class="compare-grid"><div><img src="${imageBase}${left.poster_path}" alt=""><b>${escapeHtml(left.title)}</b></div><div><img src="${imageBase}${right.poster_path}" alt=""><b>${escapeHtml(right.title)}</b></div></div><div class="comparison-copy"><p><strong>Shared:</strong> ${comparison.shared.join(", ") || "Their overlap is more atmospheric than genre-specific."}</p>${comparison.differences.map((line) => `<p>${escapeHtml(line)}</p>`).join("")}</div></div>`, "mode-dialog");
  }

  function wireTools() {
    document.getElementById("tonightBtn")?.addEventListener("click", openTonight);
    document.getElementById("coupleBtn")?.addEventListener("click", openCouple);
    document.getElementById("tasteMapBtn")?.addEventListener("click", openTasteMap);
    document.getElementById("journalBtn")?.addEventListener("click", openJournal);
    document.getElementById("dataBtn")?.addEventListener("click", openDataTools);
    document.getElementById("rouletteBtn")?.addEventListener("click", openRoulette);
    const slider = document.getElementById("diversityRange");
    slider?.addEventListener("input", () => { window.__lumiDiversity = Number(slider.value) / 100; });
    slider?.addEventListener("change", () => {
      if (!state.results.length) return;
      runSemantic({ topK: 18, diversity: window.__lumiDiversity }).then((movies) => {
        setRecommendationResults(movies, window.__lumiDiversity > 0.6 ? "A wider, more surprising taste trace." : "A closer, more familiar taste trace.");
      }).catch((error) => showToast(error.message));
    });
    document.addEventListener("lumitrace:recommendations", (event) => { state.results = event.detail?.movies || []; });
    document.addEventListener("lumitrace:feedback", (event) => handleFeedback(event.detail));
    document.addEventListener("lumitrace:compare", (event) => handleCompare(event.detail.movie));
  }

  document.addEventListener("DOMContentLoaded", () => {
    wireTools();
    const onboarding = onboardingState();
    if (!onboarding.completed && favorites().length === 0 && (!onboarding.snoozed_until || onboarding.snoozed_until < Date.now())) {
      setTimeout(() => openOnboarding().catch((error) => showToast(error.message)), 900);
    }
  });
})();

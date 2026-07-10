"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

class MemoryStorage {
  constructor() { this.values = new Map(); }
  getItem(key) { return this.values.has(key) ? this.values.get(key) : null; }
  setItem(key, value) { this.values.set(key, String(value)); }
  removeItem(key) { this.values.delete(key); }
}

global.window = global;
global.localStorage = new MemoryStorage();
global.sessionStorage = new MemoryStorage();
vm.runInThisContext(fs.readFileSync("recommendation-core.js", "utf8"), { filename: "recommendation-core.js" });

const core = global.LumiTraceRecs;
const firstSignal = {
  id: 1,
  title: "First Signal",
  overview: "A quiet film.",
  poster_path: "/first.jpg",
  release_date: "2024-01-01",
  genre_ids: [18],
};
const lowSignal = {
  id: 2,
  title: "Low Signal",
  overview: "A loud film.",
  poster_path: "/low.jpg",
  release_date: "2023-01-01",
  genre_ids: [28],
};

core.saveLlmConfig({ api_url: "https://api.example/v1", api_key: "session-only", model: "demo" }, false);
assert.equal(JSON.parse(sessionStorage.getItem(core.KEYS.llmSession)).api_key, "session-only");
assert.equal(localStorage.getItem(core.KEYS.llmRemembered), null);

core.recordFeedback(lowSignal, "less");
const payload = core.buildPayload({
  favorites: [firstSignal],
  ratings: { 1: { score: 9 } },
  prompt: "A quiet evening",
  topK: 99,
});
assert.deepEqual(payload.user_movie_ids, [1, 2]);
assert.deepEqual(payload.user_vote_counts, [9, 2]);
assert.equal(payload.top_k, 30);
assert.deepEqual(payload.overviews, ["A quiet evening"]);

localStorage.setItem(core.KEYS.searchUrl, "http://127.0.0.1:5001/search");
global.__lumitraceRemoteLocked = true;
assert.equal(core.withRequestExtras({}).remote_search_url, undefined);
global.__lumitraceRemoteLocked = false;

const normalized = core.normalizeResults([
  { id: 99, title: "No poster", score: 0.99 },
  { id: 3, title: "Visible", poster_path: "/visible.jpg", score: 0.82, evidence: { similar_to: ["First Signal"] } },
]);
assert.equal(normalized.length, 1);
assert.equal(normalized[0].score, 0.82);
assert.deepEqual(normalized[0].evidence.similar_to, ["First Signal"]);

const exported = core.exportTaste();
assert.equal(exported.favorites.length, 0);
assert.equal(exported.feedback["2"].movie.title, "Low Signal");
assert.equal(JSON.stringify(exported).includes("session-only"), false);

console.log("recommendation core checks passed");

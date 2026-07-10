"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");

const index = fs.readFileSync("index.html", "utf8");
const settings = fs.readFileSync("settings.html", "utf8");
const experience = fs.readFileSync("experience.js", "utf8");
const styles = fs.readFileSync("styles.css", "utf8");
const collection = fs.readFileSync("favorites.html", "utf8");

for (const id of ["tonightBtn", "coupleBtn", "tasteMapBtn", "journalBtn", "dataBtn", "rouletteBtn", "diversityRange"]) {
  assert.match(index, new RegExp(`id="${id}"`));
  assert.match(experience, new RegExp(`getElementById\\("${id}"\\)`));
}

for (const marker of ["data-onboarding-choice=\"like\"", "data-onboarding-choice=\"skip\"", "data-onboarding-choice=\"less\"", "next.reviewed >= 10", "onboarding-card-in", "is-dealing-like", "is-dealing-less"]) {
  assert.ok(experience.includes(marker) || styles.includes(marker), `missing onboarding marker: ${marker}`);
}

assert.match(experience, /sharedRatings/);
assert.match(experience, /state\.rouletteDraws >= 2/);
assert.match(settings, /id="llmRemember"/);
assert.match(settings, /recommendation-core\.js/);
assert.match(collection, /LumiTraceRecs\.buildPayload/);
assert.match(collection, /LumiTraceRecs\.requestRecommendations/);

console.log("experience contract checks passed");

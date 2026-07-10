"use strict";

const fs = require("node:fs");
const vm = require("node:vm");

for (const file of ["index.html", "favorites.html", "settings.html"]) {
  const html = fs.readFileSync(file, "utf8");
  const scripts = [...html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/gi)]
    .filter((match) => !/\bsrc\s*=/i.test(match[1]));
  scripts.forEach((match, index) => {
    new vm.Script(match[2], { filename: `${file}:inline-${index + 1}` });
  });
}

console.log("inline script syntax checks passed");

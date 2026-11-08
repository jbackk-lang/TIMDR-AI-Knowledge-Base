/* Public, no-secret lexical search over a small allowlist of public GIA-TIMDR docs. */
(() => {
  "use strict";
  const root = "https://raw.githubusercontent.com/jbackk-lang/GIA-TIMDR/main/";
  const docs = [
    { path: "README.md", label: "GIA-TIMDR — README" },
    { path: "docs/theory/TIMDR_Chronoprocess.md", label: "Chronoproces — definicja formalna" },
    { path: "docs/theory/TIMDR_Branch_Specification.md", label: "Specyfikacja gałęzi" },
    { path: "SKILL_timdr-signal-framework.md", label: "TIMDR — framework sygnałowy" },
    { path: "TIMDR-Time-Formalism/README.md", label: "TIMDR-Time-Formalism" }
  ];
  const form = document.getElementById("search-form");
  const input = document.getElementById("search-query");
  const status = document.getElementById("search-status");
  const results = document.getElementById("search-results");
  let cache;
  const normalize = s => s.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  const terms = s => [...new Set(normalize(s).match(/[a-z0-9]{2,}/g) || [])];
  async function load() {
    if (!cache) {
      cache = Promise.all(docs.map(async d => {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 12000);
        try {
          const res = await fetch(root + d.path, { signal: controller.signal });
          if (!res.ok) throw new Error(String(res.status));
          const text = await res.text();
          return { ...d, text: text.slice(0, 180000) };
        } catch (_) {
          return { ...d, text: "" };
        } finally { clearTimeout(timer); }
      }));
    }
    return cache;
  }
  function snippets(text, queryTerms) {
    const lines = text.split(/\r?\n/);
    const found = [];
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line || line.length < 12) continue;
      const lower = normalize(line);
      const matches = queryTerms.filter(t => lower.includes(t)).length;
      if (matches) found.push({ matches, line: i + 1, text: line.slice(0, 450) });
    }
    return found.sort((a,b) => b.matches - a.matches || a.line - b.line).slice(0,2);
  }
  form.addEventListener("submit", async event => {
    event.preventDefault();
    const query = input.value.trim();
    const q = terms(query);
    results.replaceChildren();
    if (!q.length) { status.textContent = "Wpisz co najmniej jedno słowo."; return; }
    status.textContent = "Pobieranie publicznych dokumentów…";
    const data = await load();
    const matches = data.flatMap(doc => snippets(doc.text, q).map(hit => ({ doc, hit })))
      .sort((a,b) => b.hit.matches - a.hit.matches).slice(0, 10);
    if (!matches.length) {
      status.textContent = "Brak dopasowań w wybranych dokumentach. Spróbuj innych słów.";
      return;
    }
    status.textContent = "Znaleziono " + matches.length + " fragmentów w wybranych dokumentach.";
    matches.forEach(({doc,hit},i) => {
      const article = document.createElement("article");
      const title = document.createElement("a");
      title.href = "https://github.com/jbackk-lang/GIA-TIMDR/blob/main/" + doc.path + "#L" + hit.line;
      title.target = "_blank";
      title.rel = "noopener noreferrer";
      title.textContent = "[S" + (i+1) + "] " + doc.label + " — wiersz " + hit.line;
      const p = document.createElement("p");
      p.textContent = hit.text;
      article.append(title,p);
      results.append(article);
    });
  });
})();

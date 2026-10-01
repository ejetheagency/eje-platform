// api/_lib/llm.js
// Server-side cheap-LLM lane for the API. JS port of scripts/llm_router.py's Gemini path:
// Gemini flash-lite via the native generateContent endpoint (the call that works with AI-Studio keys),
// with the same 429 backoff. The key lives server-side (GEMINI_API_KEY in env), never in the browser.

const GEMINI_KEY = process.env.GEMINI_API_KEY;
const BASE = "https://generativelanguage.googleapis.com/v1beta";
const MODEL = "gemini-flash-lite-latest";

async function route(prompt) {
  if (!GEMINI_KEY) throw new Error("no GEMINI_API_KEY in env");
  for (let attempt = 0; attempt < 5; attempt++) {
    const r = await fetch(`${BASE}/models/${MODEL}:generateContent?key=${GEMINI_KEY}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }], generationConfig: { temperature: 0 } }),
    });
    if (r.status === 429 && attempt < 4) {
      await new Promise((s) => setTimeout(s, 3000 * (attempt + 1)));
      continue;
    }
    if (!r.ok) throw new Error("gemini " + r.status + ": " + (await r.text()).slice(0, 200));
    const j = await r.json();
    return j.candidates[0].content.parts[0].text;
  }
  throw new Error("gemini rate-limited after retries");
}

// Pull a JSON object out of an LLM reply. Grabs the FIRST balanced {...} object (string-aware), so
// trailing prose or a second object the model tacked on can't break the parse.
function parseJSON(raw) {
  const s = String(raw || "").trim().replace(/^```(json)?/gim, "").replace(/```$/gim, "").trim();
  const i = s.indexOf("{");
  if (i < 0) return JSON.parse(s);
  let depth = 0, inStr = false, esc = false;
  for (let j = i; j < s.length; j++) {
    const c = s[j];
    if (inStr) { if (esc) esc = false; else if (c === "\\") esc = true; else if (c === '"') inStr = false; }
    else if (c === '"') inStr = true;
    else if (c === "{") depth++;
    else if (c === "}") { depth--; if (depth === 0) return JSON.parse(s.slice(i, j + 1)); }
  }
  return JSON.parse(s.slice(i));
}

module.exports = { route, parseJSON };

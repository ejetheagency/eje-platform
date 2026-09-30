// api/_lib/db.js
// Server-side data access for the EJE platform. Runs ONLY in Vercel serverless functions,
// so it holds the Supabase SERVICE key (from env) instead of shipping a key to the browser.
// This is the first piece of the "proper infrastructure" spine: the app UI will call /api/*
// endpoints, and those endpoints use this helper. The browser never talks to PostgREST directly.
//
// Env required (set in Vercel project settings, NEVER committed):
//   SUPABASE_URL          e.g. https://ogdsuztzhmnnjolilsuo.supabase.co
//   SUPABASE_SERVICE_KEY  the service_role key (server-only, bypasses RLS; scope with care)

const SB = process.env.SUPABASE_URL;
const KEY = process.env.SUPABASE_SERVICE_KEY;

function headers(extra) {
  return { apikey: KEY, Authorization: "Bearer " + KEY, "Content-Type": "application/json", ...(extra || {}) };
}

// GET a table with a PostgREST query string. Auto-paginates past the 1000-row cap.
async function select(table, query = "") {
  const out = [];
  let offset = 0;
  const pageSize = 1000;
  for (;;) {
    const sep = query ? "&" : "";
    const url = `${SB}/rest/v1/${table}?${query}${sep}limit=${pageSize}&offset=${offset}`;
    const r = await fetch(url, { headers: headers() });
    if (!r.ok) throw new Error(`select ${table} ${r.status}: ${await r.text()}`);
    const rows = await r.json();
    out.push(...rows);
    if (rows.length < pageSize) break;
    offset += pageSize;
  }
  return out;
}

async function insert(table, body, { returning = false } = {}) {
  const r = await fetch(`${SB}/rest/v1/${table}`, {
    method: "POST",
    headers: headers({ Prefer: returning ? "return=representation" : "return=minimal" }),
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`insert ${table} ${r.status}: ${await r.text()}`);
  return returning ? r.json() : null;
}

async function patch(table, query, body) {
  const r = await fetch(`${SB}/rest/v1/${table}?${query}`, {
    method: "PATCH",
    headers: headers({ Prefer: "return=minimal" }),
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`patch ${table} ${r.status}: ${await r.text()}`);
}

function configured() {
  return Boolean(SB && KEY);
}

module.exports = { select, insert, patch, headers, configured, SB };

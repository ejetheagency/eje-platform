// api/_lib/auth.js
// Resolves the caller's identity + tenant scope from the request's Supabase access token.
// Tenant isolation is enforced HERE (validate token -> look up memberships with the service key),
// so a client can only ever see their own data even before table-level RLS is switched on.
// Every endpoint must call authContext() and scope every query to the returned clientIds.

const db = require("./db");
const SB = process.env.SUPABASE_URL;
const ANON = process.env.SUPABASE_ANON_KEY;

// Validate a Supabase access token by asking GoTrue who it belongs to (no JWT secret needed).
async function getUser(token) {
  const r = await fetch(SB + "/auth/v1/user", { headers: { apikey: ANON, Authorization: "Bearer " + token } });
  if (!r.ok) return null;
  return r.json(); // { id, email, ... }
}

// -> { user:{id,email}, isAdmin, clientIds:[...] } or null if unauthenticated.
async function authContext(req) {
  const h = (req.headers && (req.headers.authorization || req.headers.Authorization)) || "";
  const token = h.startsWith("Bearer ") ? h.slice(7) : null;
  if (!token) return null;
  const user = await getUser(token);
  if (!user || !user.id) return null;
  const mems = await db.select("memberships", `user_id=eq.${encodeURIComponent(user.id)}&select=client_id,role`);
  return {
    user: { id: user.id, email: user.email },
    isAdmin: mems.some((m) => m.role === "admin"),
    clientIds: mems.map((m) => m.client_id),
  };
}

// Admins may act on any client; members only on clients they belong to.
function canAccess(ctx, clientId) {
  return !!ctx && (ctx.isAdmin || ctx.clientIds.includes(clientId));
}

function fail(res, code, msg) {
  res.statusCode = code;
  res.setHeader("Content-Type", "application/json");
  res.end(JSON.stringify({ error: msg }));
}

module.exports = { authContext, canAccess, fail };

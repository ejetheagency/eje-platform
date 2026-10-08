// api/ops.js  ->  GET /api/ops  (ADMIN ONLY)
// Live factory/treasury snapshot for the ops dashboard: spend today/month, per-provider cap usage,
// pipeline states, per-client READY counts, pool size. Server-side rollup (ops_rollup) so it aggregates
// past the 1000-row REST cap. The web app only READS this.
const { authContext, fail } = require("./_lib/auth");
const db = require("./_lib/db");

module.exports = async (req, res) => {
  const ctx = await authContext(req);
  if (!ctx) return fail(res, 401, "unauthorized");
  if (!ctx.isAdmin) return fail(res, 403, "admin only");
  try {
    const now = new Date();
    const monthStart = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1)).toISOString();
    const todayStart = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate())).toISOString();
    const data = await db.rpc("ops_rollup", { p_month_start: monthStart, p_today_start: todayStart });
    // Per-client scheduled-report pipeline (today + future): what's READY (approved) vs BUILDING (staged/unapproved),
    // so the admin sees reports forming and ready across all clients. Lightweight: only the approved flag from JSONB.
    try {
      const todayDate = now.toISOString().slice(0, 10);
      const fut = await db.select("leads", `source_date=gte.${todayDate}&select=client_id,source_date,approved:lead_data->>approved`);
      const up = {};
      for (const r of (fut || [])) {
        const c = r.client_id, d = r.source_date; if (!c || !d) continue;
        up[c] = up[c] || {};
        up[c][d] = up[c][d] || { ready: 0, building: 0 };
        if (String(r.approved) === "true") up[c][d].ready++; else up[c][d].building++;
      }
      data.upcoming = up;
    } catch (e) { data.upcoming = {}; data.upcoming_error = e.message; }
    res.statusCode = 200;
    res.setHeader("Content-Type", "application/json");
    res.end(JSON.stringify({ ops: data }));
  } catch (e) {
    return fail(res, 502, "ops error: " + e.message);
  }
};

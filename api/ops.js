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
    res.statusCode = 200;
    res.setHeader("Content-Type", "application/json");
    res.end(JSON.stringify({ ops: data }));
  } catch (e) {
    return fail(res, 502, "ops error: " + e.message);
  }
};

// api/report.js  ->  GET /api/report?client_id=<id>
// The client's latest PRECOMPUTED factory report (pitch-ready leads: verified decisor, email, why-now, pitch).
// The web app only READS this; all the work happened overnight in the factory. Isolation enforced here.
const { authContext, canAccess, fail } = require("./_lib/auth");
const db = require("./_lib/db");

module.exports = async (req, res) => {
  const ctx = await authContext(req);
  if (!ctx) return fail(res, 401, "unauthorized");

  const url = new URL(req.url, "http://x");
  const clientId = url.searchParams.get("client_id");
  if (!clientId) return fail(res, 400, "client_id required");
  if (!canAccess(ctx, clientId)) return fail(res, 403, "forbidden");

  try {
    const rows = await db.select(
      "reports",
      `client_id=eq.${encodeURIComponent(clientId)}&select=report_date,payload&order=report_date.desc&limit=1`
    );
    const payload = rows[0] ? rows[0].payload : { count: 0, leads: [], stats: {} };
    res.statusCode = 200;
    res.setHeader("Content-Type", "application/json");
    res.end(JSON.stringify({ client_id: clientId, report_date: rows[0] ? rows[0].report_date : null, report: payload }));
  } catch (e) {
    return fail(res, 502, "report error: " + e.message);
  }
};

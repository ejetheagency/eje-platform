// api/health.js
// First endpoint of the EJE platform API layer. Confirms serverless functions deploy and that the
// server-side env (Supabase URL + service key) is wired, WITHOUT exposing any secret to the client.
// Visit /api/health after deploy; expect { ok: true, db: "configured" }.

const db = require("./_lib/db");

module.exports = async (req, res) => {
  res.setHeader("Content-Type", "application/json");
  res.status(200).end(JSON.stringify({
    ok: true,
    service: "eje-platform-api",
    db: db.configured() ? "configured" : "missing-env",
    ts: new Date().toISOString(),
  }));
};

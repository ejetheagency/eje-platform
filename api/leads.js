// api/leads.js  ->  GET /api/leads?client_id=<id>[&status=<status>]
// Client-scoped leads for the CRM surface. The caller must be authenticated AND belong to (or be
// admin over) the requested client. Isolation is enforced here, not trusted from the browser.

const { authContext, canAccess, fail } = require("./_lib/auth");
const db = require("./_lib/db");

module.exports = async (req, res) => {
  const ctx = await authContext(req);
  if (!ctx) return fail(res, 401, "unauthorized");

  const url = new URL(req.url, "http://x");
  const clientId = url.searchParams.get("client_id");
  if (!clientId) return fail(res, 400, "client_id required");
  if (!canAccess(ctx, clientId)) return fail(res, 403, "forbidden");

  let q =
    `client_id=eq.${encodeURIComponent(clientId)}` +
    `&select=id,company,contact_name,contact_email,country,score,status,source_date,lead_data` +
    `&order=source_date.desc.nullslast`;
  const status = url.searchParams.get("status");
  if (status) q += `&status=eq.${encodeURIComponent(status)}`;

  const leads = await db.select("leads", q);

  res.statusCode = 200;
  res.setHeader("Content-Type", "application/json");
  res.end(JSON.stringify({ client_id: clientId, count: leads.length, leads }));
};

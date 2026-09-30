// api/tracked-leads.js  ->  GET /api/tracked-leads?client_id=<id>   |   POST /api/tracked-leads
// Seguimiento records for a client. GET lists them; POST creates one (+ optional first note).

const { authContext, canAccess, fail } = require("./_lib/auth");
const db = require("./_lib/db");
const { readBody, send } = require("./_lib/http");

module.exports = async (req, res) => {
  const ctx = await authContext(req);
  if (!ctx) return fail(res, 401, "unauthorized");

  if (req.method === "GET") {
    const clientId = new URL(req.url, "http://x").searchParams.get("client_id");
    if (!clientId) return fail(res, 400, "client_id required");
    if (!canAccess(ctx, clientId)) return fail(res, 403, "forbidden");
    const rows = await db.select(
      "tracked_leads",
      `client_id=eq.${encodeURIComponent(clientId)}&select=*&order=created_at.desc`
    );
    return send(res, 200, { client_id: clientId, count: rows.length, tracked_leads: rows });
  }

  if (req.method === "POST") {
    const b = await readBody(req);
    const clientId = b.client_id;
    if (!clientId) return fail(res, 400, "client_id required");
    if (!canAccess(ctx, clientId)) return fail(res, 403, "forbidden");
    const who = ctx.user.email || "user";
    const row = (
      await db.insert(
        "tracked_leads",
        {
          client_id: clientId,
          user_name: who,
          company: b.company || "(sin nombre)",
          decisor_name: b.decisor_name || null,
          contact_email: b.contact_email || null,
          contact_phone: b.contact_phone || null,
          instagram: b.instagram || null,
          linkedin: b.linkedin || null,
          source: b.source || "manual",
          stage: b.stage || "nuevo",
        },
        { returning: true }
      )
    )[0];
    if (b.note) {
      await db.insert("tracked_lead_notes", {
        tracked_lead_id: row.id,
        client_id: clientId,
        user_name: who,
        note_text: b.note,
        stage_at_time: row.stage,
      });
    }
    return send(res, 201, { tracked_lead: row });
  }

  return fail(res, 405, "method not allowed");
};

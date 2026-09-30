// api/metrics.js  ->  GET /api/metrics?client_id=<id>
// Aggregates for the client Results/ROI dashboard (the renewal engine): totals + breakdowns + rates.
// Read-only, tenant-scoped. This is the data that proves the $200/mo is worth it.

const { authContext, canAccess, fail } = require("./_lib/auth");
const db = require("./_lib/db");
const { send } = require("./_lib/http");

module.exports = async (req, res) => {
  const ctx = await authContext(req);
  if (!ctx) return fail(res, 401, "unauthorized");
  const clientId = new URL(req.url, "http://x").searchParams.get("client_id");
  if (!clientId) return fail(res, 400, "client_id required");
  if (!canAccess(ctx, clientId)) return fail(res, 403, "forbidden");

  const scope = `client_id=eq.${encodeURIComponent(clientId)}`;
  const [leads, msgs] = await Promise.all([
    db.select("leads", `${scope}&select=status`),
    db.select("messages_sent", `${scope}&select=channel,sent_at`),
  ]);

  const byStatus = {}, byChannel = {};
  for (const l of leads) byStatus[l.status] = (byStatus[l.status] || 0) + 1;
  for (const m of msgs) byChannel[m.channel] = (byChannel[m.channel] || 0) + 1;

  // engaged = any lead past first contact; derive the funnel tolerantly from whatever statuses exist
  const n = (k) => byStatus[k] || 0;
  const contacted = n("contacted") + n("replied") + n("loom_sent") + n("meeting") + n("closed");
  const replied = n("replied") + n("meeting") + n("closed");
  const meetings = n("meeting") + n("closed");
  const closed = n("closed");

  send(res, 200, {
    client_id: clientId,
    totals: { leads: leads.length, touches: msgs.length, contacted, replied, meetings, closed },
    by_status: byStatus,
    by_channel: byChannel,
    rates: {
      reply_rate: contacted ? +(replied / contacted).toFixed(3) : 0,
      meeting_rate: contacted ? +(meetings / contacted).toFixed(3) : 0,
    },
  });
};

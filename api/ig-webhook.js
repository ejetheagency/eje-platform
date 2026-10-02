// api/ig-webhook.js  ->  GET + POST /api/ig-webhook
// Instagram messaging webhook. GET handles Meta's verification handshake (echoes hub.challenge when
// hub.verify_token matches IG_VERIFY_TOKEN). POST receives messaging events (inbound DMs), optionally
// verifies X-Hub-Signature-256 against IG_APP_SECRET, and records each message to ig_events. This is
// the capture side of IG reply intelligence; matching a DM to a lead/run + classifying it is a follow-up.
//
// Env (Vercel): IG_VERIFY_TOKEN (we choose it; pasted into Meta), IG_APP_SECRET (Meta app secret,
//               optional until set, enables POST signature verification), SUPABASE_* (already set).
const crypto = require("crypto");
const db = require("./_lib/db");
const { send } = require("./_lib/http");

function readRaw(req) {
  return new Promise((resolve) => {
    let d = "";
    req.on("data", (c) => (d += c));
    req.on("end", () => resolve(d));
    req.on("error", () => resolve(d));
  });
}

module.exports = async (req, res) => {
  // 1) Verification handshake (Meta calls GET once when you save the callback URL).
  if (req.method === "GET") {
    const u = new URL(req.url, "http://x");
    const mode = u.searchParams.get("hub.mode");
    const token = u.searchParams.get("hub.verify_token");
    const challenge = u.searchParams.get("hub.challenge");
    if (mode === "subscribe" && token && token === process.env.IG_VERIFY_TOKEN) {
      res.statusCode = 200;
      res.setHeader("Content-Type", "text/plain");
      return res.end(challenge || "");
    }
    res.statusCode = 403;
    return res.end("forbidden");
  }

  if (req.method !== "POST") return send(res, 405, { error: "method not allowed" });

  const raw = await readRaw(req);

  // 2) Optional signature verification (enabled once IG_APP_SECRET is set).
  const appSecret = process.env.IG_APP_SECRET;
  if (appSecret) {
    const sig = req.headers["x-hub-signature-256"] || "";
    const expected = "sha256=" + crypto.createHmac("sha256", appSecret).update(raw).digest("hex");
    let ok = false;
    try { ok = crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(expected)); } catch (e) {}
    if (!ok) return send(res, 403, { error: "bad signature" });
  }

  let body;
  try { body = JSON.parse(raw || "{}"); } catch (e) { return send(res, 400, { error: "bad payload" }); }

  // 3) Record each inbound message. Acknowledge 200 regardless so Meta does not disable the webhook.
  try {
    for (const entry of body.entry || []) {
      for (const m of entry.messaging || []) {
        const row = {
          object: body.object || null,
          entry_id: entry.id || null,
          sender_id: (m.sender && m.sender.id) || null,
          recipient_id: (m.recipient && m.recipient.id) || null,
          mid: (m.message && m.message.mid) || null,
          message_text: (m.message && m.message.text) || null,
          ts: m.timestamp ? new Date(Number(m.timestamp) || m.timestamp).toISOString() : null,
          raw: m,
        };
        try { await db.insert("ig_events", row); }
        catch (e) { if (!/duplicate|conflict|23505/i.test(e.message)) throw e; }
      }
    }
  } catch (e) { /* swallow: acknowledging is more important than a perfect record on a single event */ }

  return send(res, 200, { received: true });
};

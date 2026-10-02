// api/stripe-webhook.js  ->  POST /api/stripe-webhook
// Receives Stripe events (activation-fee payments). On checkout.session.completed it records the
// payment and, if the checkout carries metadata.client_id, enqueues a `provision_client` job so
// payment -> activation is automatic. Signature is verified with STRIPE_WEBHOOK_SECRET (HMAC-SHA256,
// no SDK). Until that secret is set in Vercel, the endpoint still accepts events (marked unverified)
// so the destination can be created and tested; it verifies strictly once the secret is present.
//
// Env (Vercel): STRIPE_WEBHOOK_SECRET (whsec_...), STRIPE_SECRET_KEY (optional, for later API calls),
//               SUPABASE_URL + SUPABASE_SERVICE_KEY (already set, used by _lib/db).
const crypto = require("crypto");
const db = require("./_lib/db");
const { send } = require("./_lib/http");

// Read the RAW request body (signature verification needs the exact bytes, not parsed JSON).
function readRaw(req) {
  return new Promise((resolve) => {
    let d = "";
    req.on("data", (c) => (d += c));
    req.on("end", () => resolve(d));
    req.on("error", () => resolve(d));
  });
}

// Verify Stripe's `stripe-signature` header: signed_payload = `${t}.${rawBody}`, HMAC-SHA256 hex.
function verify(raw, header, secret) {
  if (!header) return false;
  const parts = Object.fromEntries(header.split(",").map((kv) => kv.split("=")));
  const t = parts.t, v1 = parts.v1;
  if (!t || !v1) return false;
  const expected = crypto.createHmac("sha256", secret).update(`${t}.${raw}`).digest("hex");
  try {
    return crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(v1));
  } catch (e) {
    return false;
  }
}

module.exports = async (req, res) => {
  if (req.method !== "POST") return send(res, 405, { error: "method not allowed" });
  const raw = await readRaw(req);
  const secret = process.env.STRIPE_WEBHOOK_SECRET;
  const sig = req.headers["stripe-signature"];

  let verified = false;
  if (secret) {
    if (!verify(raw, sig, secret)) return send(res, 400, { error: "bad signature" });
    verified = true;
  }

  let event;
  try {
    event = JSON.parse(raw || "{}");
  } catch (e) {
    return send(res, 400, { error: "bad payload" });
  }

  // Only act on completed checkouts; acknowledge everything else so Stripe stops retrying.
  if (event.type !== "checkout.session.completed") {
    return send(res, 200, { received: true, ignored: event.type || "unknown", verified });
  }

  // Idempotency: one row per Stripe event id.
  if (event.id) {
    try {
      const seen = await db.select("payments", `stripe_event_id=eq.${encodeURIComponent(event.id)}&select=id`);
      if (seen.length) return send(res, 200, { received: true, duplicate: true });
    } catch (e) { /* if the lookup fails, fall through and try to insert (unique constraint guards dupes) */ }
  }

  const s = (event.data && event.data.object) || {};
  const clientId = (s.metadata && s.metadata.client_id) || null;
  const row = {
    stripe_event_id: event.id || null,
    type: event.type,
    session_id: s.id || null,
    payment_link: s.payment_link || null,
    customer_email: (s.customer_details && s.customer_details.email) || s.customer_email || null,
    amount_total: s.amount_total != null ? s.amount_total / 100 : null,
    currency: s.currency || null,
    client_id: clientId,
    status: clientId ? "provisioned" : "manual_review",
    raw: s,
  };

  try {
    await db.insert("payments", row);
  } catch (e) {
    // A duplicate (unique stripe_event_id) is fine; anything else is a real error.
    if (!/duplicate|conflict|23505/i.test(e.message)) return send(res, 500, { error: "record failed: " + e.message });
    return send(res, 200, { received: true, duplicate: true });
  }

  // payment -> activation: if we know the client, queue their provisioning. Else leave for manual review.
  if (clientId) {
    try {
      await db.insert("job_log", { type: "provision_client", client_id: clientId, status: "queued" });
    } catch (e) { /* recorded the payment already; provisioning can be retried from the payments row */ }
  }

  return send(res, 200, { received: true, verified, client_id: clientId, status: row.status });
};

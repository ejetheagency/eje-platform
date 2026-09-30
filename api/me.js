// api/me.js  ->  GET /api/me
// Returns the logged-in user + the workspaces they can open. The new CRM shell calls this first
// to decide what to render (admin sees all clients; a client sees only their own).

const { authContext, fail } = require("./_lib/auth");
const db = require("./_lib/db");

module.exports = async (req, res) => {
  const ctx = await authContext(req);
  if (!ctx) return fail(res, 401, "unauthorized");

  let workspaces = [];
  if (ctx.isAdmin) {
    workspaces = await db.select("clients", "select=id,name,icp_config&order=id");
  } else if (ctx.clientIds.length) {
    const ids = ctx.clientIds.map((c) => `"${c}"`).join(",");
    workspaces = await db.select("clients", `id=in.(${ids})&select=id,name,icp_config`);
  }

  res.statusCode = 200;
  res.setHeader("Content-Type", "application/json");
  res.end(JSON.stringify({ user: ctx.user, isAdmin: ctx.isAdmin, workspaces }));
};

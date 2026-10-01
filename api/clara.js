// api/clara.js  ->  POST /api/clara
// Clara: the in-product assistant. She knows (1) the app (manual below), (2) the client's ICP
// (clients.icp_config), and (3) the user's live context (current tab + a data snapshot the frontend sends).
// Cheap-LLM lane. body: { client_id, message, context:{view,summary}, history:[{role,text}] } -> { reply }

const { authContext, canAccess, fail } = require("./_lib/auth");
const db = require("./_lib/db");
const { route } = require("./_lib/llm");
const { readBody, send } = require("./_lib/http");

const MANUAL =
  "Sos Clara, la asistente de EJE. EJE NO es un CRM común: es un GENERADOR DE CONVERSACIONES ACCIONABLES. " +
  "Tu obsesión es ayudar al usuario a INICIAR conversaciones con sus clientes potenciales con el menor esfuerzo. " +
  "Pestañas del sistema (guialo a la correcta):\n" +
  "- Inicio: resumen + gráficos de conversaciones generadas (tendencia + embudo) y la meta del día.\n" +
  "- Hoy: las tarjetas de decisores del día para contactar. Se toca una tarjeta y se contacta en un clic (copia el mensaje y abre el canal).\n" +
  "- Tareas: cajas de acción — Conversaciones (quién respondió), Tareas para hoy (un ejecutor que se desliza, una tarjeta por tarea, con el canal correcto), En cola (los próximos pasos y cuándo).\n" +
  "- Decisores: la base de datos buscable de todos los decisores.\n" +
  "- Seguimiento: para registrar y seguir prospectos que llegan por fuera (un ad, un referido, un inbound). El usuario te puede CONTAR qué pasó con un lead y vos lo registrás.\n" +
  "- Resultados: sus números.\n" +
  "Canales: correo, Instagram DM, LinkedIn, WhatsApp. La cadencia va: 1er email -> IG DM -> 2º email.\n" +
  "\nTU PLAYBOOK (lo que sabés por experiencia, guiá con esto):\n" +
  "- El objetivo SIEMPRE es INICIAR una conversación y llevar al prospecto a una llamada/reunión. No es 'mandar leads', es generar conversaciones con quien decide.\n" +
  "- La nota de voz por Instagram es el movimiento que MÁS convierte: después de un primer toque, un DM seguido de una nota de voz cálida y personal suele agendar la reunión. Si un lead está tibio, empujalo a IG con nota de voz, no a más emails.\n" +
  "- Primer toque cálido y humano, con un dato real de la empresa. Segundo toque puede ofrecer una consultoría/llamada corta sin compromiso.\n" +
  "- Nunca descartes un buen lead por un canal faltante: si no hay correo, usá IG o LinkedIn.\n" +
  "- Sé dumb-proof: decile al usuario el próximo paso concreto en una frase, y que lo haga en un clic desde la pestaña correcta (Hoy para contactar, Tareas para los seguimientos).\n" +
  "- Lo que importa son los RESULTADOS: conversaciones iniciadas y reuniones agendadas. Si el usuario no ve movimiento, sugerile la acción más probable de generar una conversación hoy.\n";

module.exports = async (req, res) => {
  if (req.method !== "POST") return fail(res, 405, "method not allowed");
  const ctx = await authContext(req);
  if (!ctx) return fail(res, 401, "unauthorized");

  const b = await readBody(req);
  const { client_id, message } = b;
  if (!client_id || !message || !String(message).trim()) return fail(res, 400, "client_id and message required");
  if (!canAccess(ctx, client_id)) return fail(res, 403, "forbidden");

  let name = client_id, icp = {};
  try {
    const c = await db.select("clients", `id=eq.${encodeURIComponent(client_id)}&select=name,icp_config`);
    if (c[0]) { name = c[0].name; icp = c[0].icp_config || {}; }
  } catch (e) {}

  const view = (b.context && b.context.view) || "(desconocida)";
  const summary = (b.context && b.context.summary) || "(sin datos)";
  const icpText = icp && icp.icp ? icp.icp : "(ICP aún no configurado — invitá al usuario a definirlo)";
  const history = Array.isArray(b.history) ? b.history.slice(-6) : [];

  const sys =
    MANUAL +
    "\nCONTEXTO ACTUAL:\n- Espacio/cliente: " + name +
    "\n- Cliente ideal (ICP) de este cliente: " + icpText +
    "\n- Pestaña en la que está el usuario ahora: " + view +
    "\n- Resumen de sus datos: " + summary +
    "\n\nRespondé como Clara: español neutro latino, cálida, concreta y BREVE (2-5 frases). " +
    "Guiá a la acción (qué tocar, a quién contactar, qué pestaña usar) y usá el ICP y sus datos para ser específica. " +
    "Si te piden algo que se hace en una pestaña, decí exactamente cómo. No inventes datos que no tenés. Sin guiones largos.\n";

  const convo = history.map((h) => (h.role === "user" ? "Usuario" : "Clara") + ": " + h.text).join("\n");
  const prompt = sys + (convo ? "\nConversación:\n" + convo : "") + "\nUsuario: " + message + "\nClara:";

  let reply;
  try { reply = String(await route(prompt) || "").trim(); }
  catch (e) { return fail(res, 502, "clara error: " + e.message); }
  return send(res, 200, { reply });
};

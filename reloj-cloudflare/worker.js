// Reloj del vigilante: cada 5 min le pide a GitHub que ejecute el workflow "vigilar".
// GitHub retrasa o se salta sus horarios propios; Cloudflare los cumple.
// Secreto necesario: GH_TOKEN (token fino de GitHub, solo este repo, permiso Actions: escritura).
const REPO = "samipirela26-creator/vigilante-apps";

async function lanzar(env) {
  const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/vigilar.yml/dispatches`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.GH_TOKEN}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "reloj-vigilante",
    },
    body: JSON.stringify({ ref: "main" }),
  });
  return r.status; // 204 = lanzado
}

export default {
  async scheduled(_evento, env, ctx) {
    ctx.waitUntil(lanzar(env).then((s) => { if (s !== 204) console.log("GitHub respondió", s); }));
  },
  async fetch() {
    return new Response("Reloj del vigilante activo");
  },
};

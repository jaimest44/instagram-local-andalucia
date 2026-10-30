// Dispara la publicacion de las dos cuentas de Instagram en GitHub Actions, sin depender del PC.
//
// El `schedule` de GitHub se salta ejecuciones (el 30/10/2026 no lanzo ninguna entre las 07:00 y
// las 17:00) y el PC no siempre se despierta, asi que este Worker llama a `workflow_dispatch`
// de los dos repositorios a la hora de cada franja y repite un rato despues por si la primera
// falla. publicar.py solo publica la franja que toca y nunca dos veces la misma (y el workflow
// tiene `concurrency`), asi que los reintentos no duplican nada.
//
// Franjas (hora de Madrid): 11:00 esquemas (mar/vie), 14:00 Reel, 18:00 videos propios, 20:30 carrusel.
//
// Los crons de Cloudflare van en UTC y España cambia de hora dos veces al año: el cron salta en
// los minutos 2 y 32 de cada hora y aqui se comprueba la hora real de Madrid.
//
// Secreto necesario (no va en el codigo): GITHUB_TOKEN, un token fine-grained con permiso
// «Actions: Read and write» solo sobre los dos repositorios.

const REPOS = ['jaimest44/instagram-administrativo-local', 'jaimest44/instagram-local-andalucia'];
const WORKFLOW = 'publicar.yml';
// primera llamada a la hora de la franja y reintentos despues (HH:MM en Madrid)
const HORAS = ['11:02', '11:32', '12:32',
               '14:02', '14:32', '15:32',
               '18:02', '18:32', '19:32',
               '20:32', '21:02', '22:02'];

function horaMadrid(fecha) {
  return new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Madrid', hour: '2-digit', minute: '2-digit', hour12: false })
    .format(fecha);
}

async function disparar(env, repo) {
  const r = await fetch(`https://api.github.com/repos/${repo}/actions/workflows/${WORKFLOW}/dispatches`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${env.GITHUB_TOKEN}`,
      'Accept': 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'User-Agent': 'instagram-disparador',
    },
    body: JSON.stringify({ ref: 'main', inputs: { modo: 'publicar' } }),
  });
  // GitHub responde 204 sin cuerpo cuando acepta; lo demas queda en los logs del Worker
  if (r.status !== 204) {
    throw new Error(`${repo}: GitHub respondió ${r.status}: ${await r.text()}`);
  }
}

export default {
  async scheduled(evento, env, ctx) {
    const cuando = new Date(evento.scheduledTime);
    const minuto = cuando.getUTCMinutes();
    if (minuto !== 2 && minuto !== 32) return;  // solo los minutos programados
    const hora = horaMadrid(cuando);
    if (!HORAS.includes(hora)) return;
    console.log(`${hora} Madrid: se lanza la publicación de las dos cuentas.`);
    ctx.waitUntil(Promise.allSettled(REPOS.map(repo => disparar(env, repo))).then(rs => {
      for (const r of rs) if (r.status === 'rejected') console.error(String(r.reason));
    }));
  },
};

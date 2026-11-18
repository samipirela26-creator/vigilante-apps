# Vigilante de apps

Revisa mis apps cada 5 minutos **desde fuera de mis servidores** y me avisa por Telegram.

## Cómo funciona

```
Cloudflare Worker (reloj, cada 5 min)
        │  le pide a GitHub "ejecuta vigilar"
        ▼
GitHub Actions (workflow vigilar.yml)
        │  corre vigilar.py
        ▼
Revisa cada URL ──► si algo cambió ──► mensaje a Telegram (@Spirela_bot)
        │
        └─► guarda estado.json en el repo (para recordar qué estaba caído)
```

- **¿Por qué fuera?** Si el vigilante vive en el mismo servidor que las apps y ese servidor se apaga, nadie avisa.
- **¿Por qué Cloudflare como reloj?** GitHub tiene su propio horario (`schedule`), pero lo retrasa o se lo salta: en 6 horas corrió 1 vez. Cloudflare cumple el horario exacto. El `schedule` de GitHub queda como respaldo.
- **¿Por qué repo público?** En repos públicos GitHub Actions es gratis e ilimitado. Los secretos no se ven.

## Qué avisa

| Aviso | Cuándo |
|---|---|
| 🔴 X está CAÍDA | No responde, da error, o muestra "Site Not Found" y similares |
| ✅ X volvió (estuvo caída N min) | Al recuperarse |
| ⏰ X sigue CAÍDA | Cada 30 min mientras siga caída |
| 🐢 X está lenta | Tarda más de 10 s |
| ☀️ Resumen diario | 8 am (hora de Venezuela). Si no llega, el vigilante dejó de funcionar |
| 🔒 / 🌐 | Certificado HTTPS o dominio vence en menos de 15 días |

## Archivos

- `vigilar.py`: la lógica. Las apps están en la lista `APPS`, los dominios en `DOMINIOS`.
- `.github/workflows/vigilar.yml`: cómo GitHub lo ejecuta.
- `estado.json`: memoria entre ejecuciones (lo escribe el workflow solo).
- `reloj-cloudflare/`: el Worker que hace de reloj.

## Secretos (no están en el código)

| Dónde | Nombre | Qué es |
|---|---|---|
| GitHub → repo → Settings → Secrets → Actions | `TG_TOKEN` | Token del bot de Telegram (de @BotFather) |
| GitHub (igual) | `TG_CHAT` | Tu chat_id de Telegram |
| Cloudflare Worker | `GH_TOKEN` | Token fino de GitHub: solo este repo, permiso **Actions: Read and write** |

## Repetirlo en otro lugar (desde cero)

1. **Bot de Telegram**: en Telegram habla con @BotFather → `/newbot` → guarda el token.
   Escríbele algo a tu bot y abre `https://api.telegram.org/bot<TOKEN>/getUpdates` para ver tu `chat.id`.
2. **Repo**: copia esta carpeta, cambia la lista `APPS` (y `DOMINIOS`) en `vigilar.py`, y súbelo como repo **público**:
   ```bash
   gh repo create mi-vigilante --public --source . --push
   ```
3. **Secretos de GitHub**:
   ```bash
   gh secret set TG_TOKEN    # pega el token del bot
   gh secret set TG_CHAT     # pega tu chat_id
   ```
4. **Prueba**: en GitHub → Actions → vigilar → Run workflow → marca *prueba*. Debe llegarte el resumen a Telegram.
5. **Reloj en Cloudflare** (cuenta gratis):
   - En `reloj-cloudflare/worker.js` cambia `REPO` por `tu-usuario/mi-vigilante`.
   - Abre una vez *Compute → Workers & Pages* en el panel de Cloudflare (crea el subdominio workers.dev; sin él no se activa el reloj).
   - Crea un token fino en https://github.com/settings/personal-access-tokens/new → *Only select repositories* → tu repo → *Actions: Read and write*.
   ```bash
   cd reloj-cloudflare
   npx wrangler@4 login
   npx wrangler@4 deploy
   npx wrangler@4 secret put GH_TOKEN   # pega el token cuando pida "Enter a secret value"
   ```
6. **Comprobar**: a los 5 min, en GitHub → Actions deben aparecer ejecuciones `workflow_dispatch` cada 5 minutos.

## Cambios frecuentes

- **Agregar una app**: añade `("Nombre", "https://...")` a `APPS` en `vigilar.py` y haz push.
- **Mensaje de prueba**: Actions → vigilar → Run workflow → *prueba*.
- **Pausar todo**: Cloudflare → Workers → reloj-vigilante → desactivar el cron, y en GitHub → Actions → vigilar → *Disable workflow*.

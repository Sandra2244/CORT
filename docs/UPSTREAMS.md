# Qué tomar de cada repositorio

Los repos se clonan en `upstream/` (ignorado por git) **solo para leer y reutilizar ideas**. Revisa la licencia de cada uno antes de copiar código; si es MIT/Apache puedes adaptar con atribución. Si no la tiene, no copies: reescribe la idea.

| Repo | Úsalo para | Destino en CORT |
|---|---|---|
| OpenJarvis | Agentes, herramientas, memoria, integración con modelos locales | `services/core` |
| OpenClaw | Skills, gestos, control de hardware/dispositivos | `services/vision`, `services/sensors` |
| adewaskar/JARVIS | UI holográfica, voz en tiempo real | `apps/web`, `services/voice` |

## Cómo clonar
1. Edita `scripts/upstreams.txt` con las URLs **exactas** (verifícalas en el navegador; yo no pude comprobarlas desde mi entorno).
2. `bash scripts/clone-upstreams.sh`
3. Pídele a tu agente: "lee `upstream/<repo>` y resume qué módulos son reutilizables para CORT según docs/UPSTREAMS.md".

## Regla
No fusiones repos enteros. Extrae piezas pequeñas, una por fase, con prueba.

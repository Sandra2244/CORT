# El copiloto de Código: CORT guía y ejecuta los comandos (ronda 2.8)

Esto es el punto 4 de la lista de la dueña, dicho tal cual: *«Codigo no funciona y
aparte CORT debe guiarte como copiloto y ejecutar los comandos tu solo… mejórala así
como trabas tú QODER»». O sea: escribes lo que quieres averiguar, CORT te lo vuelve un
**plan de pasos**, y los pasos seguros **se ejecutan solos** con su ▶.

## Qué es, en una línea

`backend/app/copiloto.py` mira el comando que toca y decide si es **de sólo lectura**.
Si lo es, lo ejecuta y te enseña la salida. Si no, **no lo ejecuta** y te dice por qué,
con el comando escrito para que lo copies tú. Nada más.

## Las tres reglas que lo hacen seguro

1. **Sólo lectura, y en una sola lista.** La puerta son tres listas escritas a mano en
   el propio archivo: `LEE_SOLO` (el verbo y las banderas que **no** puede llevar:
   `tail` sin `-f`, `find` sin `-delete` ni `-exec`), `SUB_LECTURA` (los subórdenes
   permitidos de los mandos mixtos: `git status`, `git log`, `ollama list`,
   `systemctl status`, `crontab -l`…) y `NUNCA` (lo que no se hace ni pidiéndolo por
   favor: `rm`, `mv`, `dd`, `sudo`, `curl | sh`…). Lo que no esté en ninguna lista se
   **niega**: negar por defecto es el diseño, no el fallback.
2. **La puerta se comprueba dos veces.** Una al planear (`/api/copiloto/plan`) y otra
   **justo antes de ejecutar** (`/api/copiloto/ejecuta`), sobre el comando real. Así que
   un plan falseado a mano —con `"seguro": true` pegado a un `rm -rf`— sigue sin
   correrse. Y no hay `shell`: se pasa la lista de argumentos, con `~` expandida por
   Python; las redirecciones, las tuberías y `$( )` se rechazan con nombre y apellido.
3. **Ella manda, hasta cierto punto.** `~/.cort/copiloto.json` tiene dos listas:
   `permito` y `nunca`. Se **relee en cada llamada**, así que cambiarla no necesita
   reiniciar nada:

   ```json
   { "permito": ["mkdir", "du"], "nunca": ["ps"] }
   ```

   `permito` abre verbos nuevos de sólo lectura; `nunca` retira incluso los que venían
   abiertos. Lo que **no** puede `permito` es abrir la lista `NUNCA`: un
   `"permito": ["rm"]` se ignora, y si el JSON está roto manda la lista de casa.

## Cómo se usa desde la cara

Pantalla **Código** (☰ ▸ Código), con la casilla **copiloto** marcada:

- Escribes `¿qué está comiendo memoria?` y sale un plan: cinco pasos, cada uno con su
  orden, su ▶ (si es seguro) o su motivo (si no lo es).
- **▶ ejecuta los N seguros** los corre en fila y para en el primero que falla; el resto
  de los pasos se enseñan y se copian.
- Cada plan caduca a los **900 s** y sólo se ejecuta un paso por llamada, con la salida
  cortada en **8000 caracteres**.
- `> ` delante de la línea **salta el copiloto** y manda la orden como siempre (la
  salida de emergencia, para cuando quieras tú escribir el comando).
- En el teléfono, sin el portátil encendido, el copiloto lo dice en vez de fingir: no
  hay comandos que mirar sin PC, y ahí contesta el `Mente` del teléfono.

## Las ocho plantillas

Si no hay receta que encaje, el plan lo hace el cerebro de siempre; si la hay, la
plantilla da pasos que **sí** se pueden ejecutar solos. Son ocho: qué come memoria,
qué hay en casa, la red, el disco, el sistema, el repositorio, el polvorín (archivos
con espacios, paréntesis o duplicados) y los cerebros de Ollama. Ningún paso lleva
tubería ni redirección, porque sin `shell` no se pueden ejecutar.

## Lo que esto NO hace (dicho en vez de fingido)

- No borra, no mueve, no instala, no configura. Para ordenar archivos ya existe
  `/api/organizar`, que es plan + confirmación + marcha atrás, y ése es el sitio de los
  cambios.
- No abre un terminal interactivo: `top`, `less` o un `python3` con script dentro no
  son de sólo lectura y se niegan.
- El `rm` no entra aunque ella lo escriba en `permito`. Si un día se quiere, es otra
  ronda con su propio diseño (confirmación larga y lista de lo tocado), no un archivo.

## Cómo se comprueba (sin navegador y sin teléfono)

`scripts/prueba-costura.py`, sector **[23]**: importa `copiloto.py` de verdad y le
pregunta **20 comandos de escritura** (todos negados), **14 de lectura** (todos
autorizados) y los **25 pasos de las 8 plantillas** (todos ejecutables); forja un plan
con `seguro: true` sobre un `rm -rf` y exige el «no»; prueba `permito`/`nunca` con una
casa de mentira (`CORT_CASA`); cruza las tres rutas entre `main.py` y `pantallas.js`; y
verifica que la cara pinta ▶ sólo dentro de la rama segura. Cosido también la cara
contra su hoja de estilo: los **5 `id`** que el copiloto consulta tienen estar montados
en su propia plantilla (un `$('#cod-cop-chips')` contra un hueco devuelve `null` y la
hoja se queda muda sin error) y las **12 clases `cp-*`** que usa tienen tener en
`hud.css` una regla **sola** —contar el texto a secas tapaba el rojo, porque
`.cp-paso.maloz` contiene `.cp-paso`—. Después, una batería de **13 mutaciones** en un
árbol de enlaces duros (`sed -i` sólo, `cmp` para que ningún sed se quede ciego, y `rm`
antes de restaurar para no truncar el inodo compartido) confirma que cada una de esas
comprobaciones **se pone roja** si se rompe lo que dice mirar: un verde que no puede
caer no es prueba.

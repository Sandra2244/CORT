# CORT en el teléfono (Android) — qué es, qué necesita y qué no hace

**Autora:** Askher Vargas y Sandra Lopez · soporte: `Sandrasofialopezgomez3@gmail.com` ·
`Carlosa3325@gmail.com`. **Licencia:** MIT (ver `LICENSE`).

---

## 1. Qué es exactamente

Una aplicación que abre la interfaz de CORT **corriendo en tu PC de la casa**. No hay
servidor en internet, no hay cuenta, no hay nube: el teléfono es una ventana y un micrófono,
y el puente vive en la Classmate.

```
teléfono (WebView + botón ● hablar)
   │  http://IP_CASA:8766      ← la interfaz
   ├─ ws://IP_CASA:8765/ws      ← las órdenes y las respuestas
   └─ POST /mic  (WAV 16 kHz)   ← lo que tú digas, sólo mientras pulsas
             ↓
        el puente de la PC: reglas locales → Ollama si cabe → reja → acción → verificación
```

Todo lo que CORT sabe de ti (`memoria.json`, notas, lista) sigue estando en el PC. Si apagas
la PC, el teléfono no sabe nada: no hay copia en el teléfono.

## 2. Por qué una APK y no la web instalable (PWA)

Medido, no opinado:

- El puente sirve la interfaz por **http** en la red local (no hay certificado).
- Chrome/WebView sólo dan `getUserMedia` (micrófono) y el service worker de instalación a
  **orígenes seguros**. `http://192.168.x.x` no lo es.
- Con `https` sí se podría (el puente ya acepta `CORT_TLS=certificado,clave`), pero un
  certificado válido exige un nombre de dominio público, y eso es sacar la red de tu casa a
  internet. No se hizo.

Así que el cliente nativo resuelve las dos cosas: instala la interfaz sin necesitar service
worker y **graba el audio él mismo**, con el permiso del sistema, y se lo manda al puente.

## 3. Cómo se compila

**No se compila en esta máquina, y se dice por qué:** la Classmate tiene OpenJDK 21 sólo
*runtime* (`javac` no está), no tiene Gradle ni SDK de Android ni `adb`. Prometer un APK
"hecho en casa" sería mentira. Se compila en GitHub Actions con el workflow
`.github/workflows/apk.yml`, que:

1. baja JDK 17 y usa el SDK de Android del runner (si falta algo, instala las herramientas
   oficiales de Google con `sdkmanager` y lista lo instalado en el log);
2. corre `gradle assembleDebug` sobre `apps/android/`;
3. imprime **peso en bytes, peso en MB y SHA-256** del APK, y la lista de lo que lleva dentro;
4. sube el APK como artefacto, y la release lo lleva colgada.

El proyecto **no tiene dependencias externas**: `app/build.gradle` no declara ninguna
librería. Sólo `android.*` y `org.json`, que vienen con el SDK. No hay nada de terceros que
pueda cambiar después de publicado.

La firma es la **de depuración** (`applicationIdSuffix ".dep"`). Es instalable en tu teléfono
y basta para usar CORT, pero no es una firma de autora: si alguien quisiera suplantar la app,
el número de versionCode y la firma no se lo impedirían. La firma propia (clave en `keystore`
que **nunca** va al repo) está pendiente de que se monte el canal de publicación.

## 4. Instalarla en el Galaxy A16

1. **En la PC**, abrir el puente a la red local (una vez):
   ```bash
   ~/Escritorio/CORT/scripts/instala_cort.sh --red
   # o sin reinstalar:
   cd ~/Escritorio/CORT && CORT_BIND=0.0.0.0 .venv/bin/python -u cort-bridge/cort_server.py
   ```
   El puente imprime su dirección: `a la red local: http://192.168.x.x:8766/`. Apunta esa IP.
2. Bajar el `app-debug.apk` de la release en el teléfono. Android avisará de que la fuente
   no es conocida: **es verdad, es la firma de depuración**. Acepta sólo si el archivo viene
   de tu propio repo y **compara el SHA-256** con el que pone la release antes de abrirlo.
3. Abrir la aplicación. La primera vez pregunta dónde está CORT: escribe la dirección del
   paso 1 (`http://192.168.x.x:8766/index.html`). Se guarda en el teléfono.
4. Pedirá permiso de **micrófono**. Sin él la interfaz funciona igual; sólo falta «● hablar».

## 5. El botón «● hablar», y por qué tarda lo que tarda

Mantén y suelta no: **pulsa una vez para empezar, otra para terminar** (así se puede usar
con el pulgar y no depende de mantener la presión, que en pantalla táctil es lo que se cae).
Hasta 20 segundos; si te pasas, corta y sube lo grabado.

Números medidos con `scripts/prueba_mic_telefono.py` (audio sintético, sin teléfono de por
medio, `nice -19` en la Classmate):

| estado | round trip |
|---|---|
| primera subida (Vosk cargando el modelo de 58 MB) | 22,4 s |
| con el modelo ya en RAM | 2,8 s para ~2 s de habla |

Eso es la transcripción; después el puente contesta con sus reglas en 3–4 ms. **El cuello de
botella es esta CPU de 2 núcleos, no el teléfono ni el Wi-Fi.** Con el cerebro encendido
(Ollama) habría que sumarle su tiempo, y aquí no cabe: se dice con la cifra, no se esconde.

## 6. Qué no hace todavía, dicho con nombre

- **No hay emparejamiento ni clave** (fase S3). Quien esté en tu Wi‑Fi y sepa la IP puede
  abrir la misma página y darle órdenes al puente. Con `--red` eso es real: es la comodidad
  de usarlo desde la cama a cambio de la red abierta de tu casa. La puerta de verdad es
  token + TLS, y está pendiente.
- **No habla por el altavoz del teléfono**: CORT sintetiza en la PC, y en esta laptop no
  hay altavoz físico (`auto_null`), así que el audio sale por donde salga en el PC
  (HDMI o dongle USB). El micrófono del teléfono sí entra.
- **No hay notificaciones ni "ok CORT" en segundo plano.** Sin servicio que escuche
  siempre, la app hace de escucha mientras esté abierta.
- **La cámara del teléfono no se usa.** La mirada (S2) corre en el PC con su cámara.

## 7. Dónde está cada cosa

```
apps/android/app/src/main/java/es/cort/android/MainActivity.java   WebView, ajuste de
    dirección, botón de habla, WAV y subida a /mic
apps/android/app/src/main/AndroidManifest.xml                      dos permisos: INTERNET
    y RECORD_AUDIO; `usesCleartextTraffic` para http en la red de casa
cort-bridge/cort_server.py   ruta `POST /mic` (recibe, transcribe, borra el WAV)
.github/workflows/apk.yml    la compilación y las medidas
```

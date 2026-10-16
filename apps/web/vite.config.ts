import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // `./` y no `/`: desde `v0.17.0` este mismo `dist` viaja **dentro del APK**
  // (`apps/apk/assets/web/`) y lo sirve el WebView cortando las peticiones en
  // `shouldInterceptRequest`. Con la raíz absoluta el `index.html` habría pedido
  // `/assets/index-*.js` — y en el teléfono ese host no existe. Con relativos la
  // página funciona igual servida por `cort.py` en `http://IP:8780/` que desde
  // `https://cort.local/index.html` dentro del aparato. No es un arreglo para el
  // APK únicamente: un `file://` abierto a mano tampoco funciona, porque un
  // módulo ES desde `file://` lo bloquea el propio Chromium por CORS — de ahí que
  // el teléfono use un origen interceptado y no el disco.
  base: './',
  server: {
    port: 5173,
    // host true = escucha también en la red local, para abrir CORT desde el teléfono.
    // Solo sirve de verdad si el core deja de estar atado a 127.0.0.1 (ver docs/STATUS.md).
    host: true,
  },
})

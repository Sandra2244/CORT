import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // host true = escucha también en la red local, para abrir CORT desde el teléfono.
    // Solo sirve de verdad si el core deja de estar atado a 127.0.0.1 (ver docs/STATUS.md).
    host: true,
  },
})

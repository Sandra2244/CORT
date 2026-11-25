# Matriz de capacidades — PC y Android

La misma promesa de CORT puede tener implementaciones distintas. La interfaz y el protocolo se comparten; las acciones dependen del sistema operativo.

| Capacidad | PC | Android | Contrato compartido | Siguiente mejora |
|---|---|---|---|---|
| Interfaz | Web en `cort-web/` | La misma web dentro de WebView | Mensajes y estados | Modo teléfono táctil y modo escritorio opcional |
| Escucha | Vosk local | Vosk local | Texto reconocido y origen | Segundo plano confiable |
| Voz | espeak-ng / Piper | TTS de Android | Texto a pronunciar | Control de audio y auriculares |
| Reglas locales | Puente Python | Reglas Java | Intención y resultado | Una sola tabla de capacidades |
| Cerebro local | Ollama | GGUF con llama.cpp | Pregunta, contexto y respuesta | Carga medible y error legible |
| Nube | La UI la ofrece, pero la ruta de chat sólo usa Ollama | Anthropic y OpenAI-compatible; sin Gemini | Proveedor, consumo, latencia y error | Implementar adaptador real o declarar no disponible |
| Secretos | Ajustes web en `localStorage`; el puente acepta campos generales | `SharedPreferences` privado en claro | Configurada / no configurada; nunca valor | Keyring en PC y Keystore en Android |
| Archivos | Sí, con raíces permitidas | Sólo almacenamiento propio sin permisos amplios | Plan validado | No exponer acciones de PC en Android |
| Apps y ventanas | Sí en Linux | Sólo apps propias o Intents del sistema | Resultado `real` / `no disponible` | Filtrar paneles por plataforma |
| Memoria | JSON | SQLite | Preferencias y recuerdos | Sincronización con conflictos definidos |
| Lista y pendientes | JSON | SQLite | Elementos y fechas | Sincronización bidireccional |
| Cámara | Visión por piel y movimiento | Cámara para QR | Imagen no persistente | No llamar «visión» a funciones distintas |
| Auditoría de seguridad | Auditoría local informativa | No puede escanear otras apps | Hallazgos y límites | Renombrar como auditoría/salud |
| Escucha en segundo plano | No aplica | Servicio en primer plano | Estado y permiso | Prueba de reinicio y batería |
| Saludo al reiniciar | Servicio de usuario | BOOT_COMPLETED + notificación | Mensaje y hora | Entrega inmediata y reintento seguro |
| Actualización | Avisa desde el repo | Manifiesto o release compatible | Versión y SHA | No prometer actualización sin canal |

## Reglas de distribución

1. **Una capacidad, una promesa:** el nombre que ve la persona usuaria debe describir lo que realmente hace.
2. **Una plataforma, un adaptador:** PC y Android pueden implementar la misma capacidad de forma distinta.
3. **El puente no duplica el cerebro:** recibe resultados y los reparte; no vuelve a decidir una acción que Android ya resolvió.
4. **Lo no disponible se declara:** con motivo y alternativa, no con un panel vacío o un dato simulado.
5. **La carga se reparte:** inferencia, visión y audio se pausan o degradan cuando el dispositivo no tiene presupuesto.

## Contrato híbrido propuesto

Todavía no está aceptado. Si el cuestionario lo aprueba, cada petición declarará:

- intención, plataforma y permisos;
- presupuesto de tiempo, RAM, CPU, red y tokens;
- proveedor elegido y motivo;
- estado `real`, `simulado` o `no disponible`;
- resultado verificable, error legible y cancelación.

El router no sustituirá silenciosamente un motor local por nube. La privacidad decide primero; el presupuesto y la disponibilidad deciden después.

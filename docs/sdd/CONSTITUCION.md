# Constitución de CORT

## 1. Privacidad y funcionamiento local

CORT prioriza el funcionamiento local. El audio, la cámara y la memoria no se envían a terceros sin una acción explícita de la persona usuaria y una indicación visible.

## 2. Honestidad de capacidades

Toda respuesta distingue:

- **real:** ejecutada o medida;
- **simulado:** dato de demostración, claramente etiquetado;
- **no disponible:** la plataforma, el permiso, el hardware o el recurso no lo permite.

Nunca se muestra una herramienta de PC como disponible en Android si el sistema operativo no la permite.

## 3. El modelo propone; el código decide

El modelo de lenguaje puede proponer planes. La validación decide qué está permitido y el ejecutor realiza la acción. Las operaciones destructivas o irreversibles requieren confirmación humana.

Las acciones deterministas —abrir una app, ajustar volumen, consultar RAM— se resuelven con reglas y capacidades reales. El modelo se usa cuando aporta interpretación de lenguaje; no se carga un modelo pesado para ejecutar una acción que una regla puede resolver.

## 4. Presupuesto de recursos

Toda función que use CPU, RAM, red, audio o cámara debe tener un límite explícito: tiempo, tamaño, cola, frecuencia o condición de parada. Si no cabe en el dispositivo, CORT lo dice con el número y ofrece una alternativa; no intenta congelar el equipo.

## 5. Android es táctil primero

La vista de teléfono debe adaptarse al ancho real, respetar áreas seguras y evitar que paneles, botones o notificaciones se solapen. La vista de escritorio es opcional y no debe ser la única forma usable.

## 6. Segundo plano visible y voluntario

La escucha en segundo plano requiere:

- permiso concedido;
- servicio en primer plano con notificación permanente;
- estado visible de escucha;
- límite de tiempo o batería;
- forma inmediata de detenerla;
- reinicio seguro sin prometer servicios que Android no permite arrancar.

## 7. Pruebas antes de cambios

Cada corrección empieza por una prueba que reproduce el comportamiento indebido. Las pruebas usan datos de arena y dobles de prueba; no mueven archivos reales, no abren apps reales ni acceden a la cámara o al micrófono sin una prueba física autorizada.

## 8. Cambios pequeños y reversibles

Un parche no mezcla una función nueva, una refactorización amplia y un cambio de interfaz. Si una refactorización no cambia el comportamiento, se hace después de estabilizar las pruebas.

## 9. Trazabilidad

Cada SPEC tiene un identificador estable. Las pruebas y la evidencia citan ese identificador. Un cambio de requisito se registra en la SPEC; no se cambia sólo el código.

## 10. Evidencia antes que promesas

Las cifras de RAM, latencia, FPS, batería y tamaño se obtienen de una ejecución identificada. “Compilado” no significa “probado en el teléfono”. “Probado en el teléfono” no significa “medido en todos los dispositivos”.

## 11. Documentación comprensible

La documentación de producto se escribe en español claro. El código usa nombres descriptivos. Cada documento indica qué está verificado, qué es una decisión y qué sigue pendiente.

## 12. Nada se publica a ciegas

Una release requiere suite verde, revisión de cambios, versión coherente y notas generadas o contrastadas con los artefactos de esa misma corrida. La verificación física pendiente se declara en las notas.

# CORT — SDD controlado

Este SDD convierte una necesidad en una especificación, un plan pequeño, pruebas y evidencia antes de darla por terminada.

## Por dónde empezar

1. [CONSTITUCION.md](CONSTITUCION.md): las reglas que no deben cambiar.
2. [BACKLOG.md](BACKLOG.md): problemas ordenados por impacto.
3. [PLANTILLA_SPEC.md](PLANTILLA_SPEC.md): cómo escribir una mejora.
4. [DECISIONES.md](DECISIONES.md): decisiones de arquitectura y sus motivos.
5. [MATRIZ_CAPACIDADES.md](MATRIZ_CAPACIDADES.md): qué hace cada plataforma y dónde vive cada capacidad.
6. [SPEC-ANDROID-001.md](SPEC-ANDROID-001.md): primer corte, puerta RAM; local y build de CI verdes, A16 pendiente.
7. [INFORME_HIBRIDO_PC_ANDROID.md](INFORME_HIBRIDO_PC_ANDROID.md): comparación y arquitectura objetivo, en borrador.
8. [CUESTIONARIO-HIBRIDO.md](CUESTIONARIO-HIBRIDO.md): diez decisiones de producto pendientes de respuesta.

## Flujo de trabajo

```text
Necesidad → SPEC → PLAN → TAREAS → PRUEBA ROJA → CÓDIGO → PRUEBA VERDE → EVIDENCIA
```

- **SPEC:** qué debe observar la persona usuaria y qué no debe pasar.
- **PLAN:** qué archivos cambiarán y qué alternativas se descartaron.
- **TAREAS:** pasos pequeños, uno por vez.
- **PRUEBA ROJA:** demuestra que el defecto existe antes de corregirlo.
- **CÓDIGO:** el cambio mínimo que satisface la SPEC.
- **PRUEBA VERDE:** confirma el comportamiento y busca regresiones.
- **EVIDENCIA:** comando, resultado, versión y dispositivo usado.

No se salta de “necesidad” a “código”. Si el requisito cambia, se actualiza la SPEC y se anota el motivo.

## Estados de una SPEC

`BORRADOR → ACEPTADA → EN CURSO → VERIFICADA → CERRADA`

Una SPEC sólo puede cerrarse cuando sus criterios de aceptación tienen evidencia. Si falta probarla en el A16, se deja como **verificación física pendiente**, no como éxito.

## Definición de terminado

- [ ] La SPEC tiene alcance y no alcance explícitos.
- [ ] Cada criterio de aceptación tiene al menos una prueba.
- [ ] La prueba nueva falla antes del parche y pasa después.
- [ ] Las suites existentes no empeoran.
- [ ] No se ejecutan acciones reales sobre archivos, apps o dispositivos durante las pruebas.
- [ ] La documentación afectada coincide con el comportamiento nuevo.
- [ ] La evidencia distingue estático, compilado y medido en dispositivo.
- [ ] Los cambios locales están revisados antes de commit o release.

## Regla de gasto de contexto

Cada entrega debe dejar aquí: qué cambió, qué se comprobó, qué quedó pendiente y el siguiente paso. El chat se usa para decidir; estos archivos guardan el trabajo para retomarlo después.

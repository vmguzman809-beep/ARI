---
name: ari-bootloader-analyzer
description: Evalúa estado y vías oficiales de desbloqueo del bootloader para una variante Android específica en ARI, sin ejecutar el desbloqueo.
---

# Bootloader Analyzer

Consulta `AGENTS.md`, `docs/phases.md` y `ari/bootloader/contracts.py`. En Fase 1
solo existen modelos para bootloader; en Fases 2 y 3 este análisis sigue pendiente.
El diagnóstico ADB de propiedades no prueba el estado del bootloader. No presentes estado inferido
como medición. Usa evidencia aportada identificando su procedencia.

Separa estado locked/unlocked, posibilidad oficial de desbloqueo y permisos OEM;
ninguno demuestra por sí solo los otros. Contrasta documentación del fabricante
para variante, región y operador exactos; conserva URL y fecha. Ante falta de
evidencia usa unknown. No extrapoles un procedimiento de otra variante.

Explica el borrado de datos habitual del desbloqueo y registra restricciones y
antirollback pendientes. Analizar compatibilidad no autoriza unlock, wipe, flash
ni reboot. No propongas eludir FRP, MDM o controles del propietario.

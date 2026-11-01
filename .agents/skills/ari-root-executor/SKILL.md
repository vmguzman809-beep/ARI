---
name: ari-root-executor
description: Revisa solicitudes de preparación o ejecución de root en ARI y aplica sus límites de fase, validación y autorización antes de cualquier modificación.
---

# Root Executor

Lee `AGENTS.md`, `docs/phases.md` y `ari/root/executor.py`. En Fases 1 y 2 el ejecutor
deniega todas las operaciones: incluso una confirmación humana no crea un backend
ni habilita comandos de modificación. El adaptador de diagnóstico ADB de Fase 2
no es un backend de root. Explica la capacidad pendiente sin intentar una
ruta alternativa por PowerShell, ADB, Fastboot o herramientas de terceros.

En una futura fase habilitada, exige un procedimiento validado y confirmación
humana específica inmediatamente antes de desbloquear, borrar o escribir. Expón
dispositivo, acción, partición, imagen/hash, borrado y condición de parada. No
reutilices una aprobación de otro dispositivo, otra imagen o un diagnóstico.

La ejecución futura debe aceptar operaciones tipadas y parámetros acotados;
nunca shell ni texto generado como comandos. Detente ante cualquier discrepancia
de identidad, hash, estado o antirollback y registra el resultado verificable.

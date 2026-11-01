# Android Root Intelligence — ARI V1

Agente especializado en diagnóstico Android, investigación documentada, análisis
de firmware y planificación de root, dentro de la ventana de OpenAI Codex en
Windows 10/11. Versión del paquete: `0.2.0` (Fase 2 de V1).

ARI Core coordina evidencia; Device Inspector, Bootloader Analyzer, Root Researcher,
Firmware Analyzer, Root Planner, Root Executor, Recovery y Security son roles
expresados como skills locales. Su existencia no supone procesos ni subagentes
activos. La delegación depende de las herramientas realmente disponibles.

El objetivo futuro es detectar ADB/Fastboot, identificar la variante exacta,
contrastar compatibilidad Magisk/KernelSU, validar firmware e imágenes y producir
planes, verificaciones e informes. Cada conclusión debe mostrar su certeza,
procedencia y lo que falta comprobar.

**Estado actual:** cimientos Python, SQLite, registros, pruebas y diagnóstico ADB
de solo lectura mediante API Python. El adaptador se probó con mocks, sin una
verificación en un dispositivo real. Detecta conexiones y observa propiedades
de un serial seleccionado explícitamente. No infiere compatibilidad de root.

El esqueleto MCP permanece deshabilitado y expone solo metadatos. Su conexión con
Codex y las herramientas de diagnóstico MCP corresponden a Fase 3. Fastboot,
investigación automática, análisis de firmware, preparación de imágenes y
modificaciones siguen pendientes. REA no se ha integrado.

Solo lectura y simulación son las bases del diseño; no sustituyen autorización ni
validación. La Fase 2 permite únicamente lectura ADB autorizada con simulación
desactivada explícitamente. El ejecutor de root permanece bloqueado por código.

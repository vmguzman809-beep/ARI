# Android Root Intelligence — ARI V1

Agente especializado en diagnóstico Android, investigación documentada, análisis
de firmware y planificación de root, dentro de la ventana de OpenAI Codex en
Windows 10/11. Versión del paquete: `0.3.0` (Fase 3 de V1).

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

El servidor MCP local está habilitado y expone seis herramientas de lectura.
Se verificaron descubrimiento, llamadas, errores y terminación de procesos con
el cliente MCP del Codex App Server instalado, sin usar el cliente SDK como prueba
de esa conexión. El diagnóstico positivo de esa verificación usó fixtures
sintéticas, sin dispositivos reales. Consulta `docs/mcp.md` para los límites.

Fastboot, investigación automática, análisis de firmware, preparación de imágenes
y modificaciones siguen pendientes. No se ha iniciado Fase 4 ni integrado REA.

Solo lectura y simulación son las bases del diseño; no sustituyen autorización ni
validación. La lectura ADB requiere autorización y simulación desactivada
explícitamente en cada llamada. El ejecutor de root permanece bloqueado por código.

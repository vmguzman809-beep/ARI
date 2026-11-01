# Android Root Intelligence — ARI V1

Agente especializado en diagnóstico Android, investigación documentada, análisis
de firmware y planificación de root, dentro de la ventana de OpenAI Codex en
Windows 10/11. Versión del paquete inicial: `0.1.0` (Fase 1 de V1).

ARI Core coordina evidencia; Device Inspector, Bootloader Analyzer, Root Researcher,
Firmware Analyzer, Root Planner, Root Executor, Recovery y Security son roles
expresados como skills locales. Su existencia no supone procesos ni subagentes
activos. La delegación depende de las herramientas realmente disponibles.

El objetivo futuro es detectar ADB/Fastboot, identificar la variante exacta,
contrastar compatibilidad Magisk/KernelSU, validar firmware e imágenes y producir
planes, verificaciones e informes. Cada conclusión debe mostrar su certeza,
procedencia y lo que falta comprobar.

**Estado actual:** cimientos Python, SQLite, registros, pruebas, contratos y
esqueleto MCP. Ninguna operación Android, investigación automática, análisis de
firmware, preparación de imágenes o modificación está implementada. REA es una
integración opcional pendiente de evaluación, sin dependencia ni conexión.

Solo lectura y simulación son las bases del diseño; no sustituyen autorización ni
validación. En Fase 1 las operaciones de dispositivo quedan bloqueadas por código.

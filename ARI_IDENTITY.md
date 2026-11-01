# Android Root Intelligence — ARI V1

Agente especializado en diagnóstico Android, investigación documentada, análisis
de firmware y planificación de root, dentro de la ventana de OpenAI Codex en
Windows 10/11. Versión del paquete: `0.5.0` (Fase 5 de V1).

ARI Core coordina evidencia; Device Inspector, Bootloader Analyzer, Root Researcher,
Firmware Analyzer, Root Planner, Root Executor, Recovery y Security son roles
expresados como skills locales. Su existencia no supone procesos ni subagentes
activos. La delegación depende de las herramientas realmente disponibles.

El objetivo futuro es detectar ADB/Fastboot, identificar la variante exacta,
contrastar compatibilidad Magisk/KernelSU, validar firmware e imágenes y producir
planes, verificaciones e informes. Cada conclusión debe mostrar su certeza,
procedencia y lo que falta comprobar.

**Estado actual:** cimientos Python, SQLite, registros, pruebas y diagnóstico ADB
de solo lectura mediante API Python y MCP. Además de mocks, se completó un
diagnóstico real autorizado desde las herramientas nativas de un chat nuevo.
Detecta conexiones y observa propiedades
de un serial seleccionado explícitamente. La Fase 4 añade evaluación offline de
evidencia fechada sobre bootloader, restricciones, Magisk y KernelSU, con informes
y planes exclusivamente teóricos. Una identidad parcial bloquea conclusiones exactas.

El servidor MCP local conserva las nueve herramientas anteriores y añade dos de
análisis estático de archivos autorizados, once en total. El lector inspecciona
ZIP y cabeceras boot/init_boot/vendor_boot/recovery/vbmeta, calcula SHA-256 y
conserva identidad, A/B e índices AVB reportados sin demostrar autenticidad o
compatibilidad antirollback. No extrae a disco ni modifica originales.
Se verificaron descubrimiento, llamadas, errores y terminación de procesos con
el cliente MCP del Codex App Server instalado, sin usar el cliente SDK como prueba
de esa conexión. El diagnóstico positivo de esa verificación usó fixtures
sintéticas, sin dispositivos reales. Una comprobación posterior de Fase 3 verificó
seis herramientas nativas y un diagnóstico real. La discrepancia posterior de
nueve herramientas/0.4.0 se debió a reanudar un chat creado antes de actualizar.
Una sesión realmente nueva confirmó once herramientas, ARI 0.5.0 y las dos APIs
de firmware con un fixture exclusivamente sintético. Consulta `docs/mcp.md`
para distinguir estas validaciones y sus límites.

La búsqueda web la coordina Codex; el motor evalúa fuentes aportadas y no las descarga
ni autentica. Fastboot, rastreo web automático, preparación/modificación de imágenes
y ejecución siguen pendientes. No se inicia Fase 6 ni integra REA.

Solo lectura y simulación son las bases del diseño; no sustituyen autorización ni
validación. La lectura ADB requiere autorización y simulación desactivada
explícitamente en cada llamada. El ejecutor de root permanece bloqueado por código.

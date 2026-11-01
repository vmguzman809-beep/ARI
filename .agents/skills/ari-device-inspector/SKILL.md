---
name: ari-device-inspector
description: Detecta conexiones e inspecciona un Android autorizado mediante las herramientas MCP de lectura de ARI o su API Python. Exige serial explícito; Fastboot y root siguen pendientes.
---

# Device Inspector

Lee `AGENTS.md`, `docs/mcp.md` y `docs/adb.md`. En Fase 3 prefiere las herramientas
MCP `detect_devices`, `inspect_adb_status`, `get_device_properties` e `inspect_device`
cuando estén disponibles en la sesión. No confundas una entrada de configuración
con conexión efectiva. La API Python de Fase 2 sigue disponible; no la uses para
evadir un rechazo de autorización o de validación del MCP. No ejecutes Fastboot.

Una tarea de desarrollo no autoriza consultar hardware. Cuando el usuario solicite
diagnóstico de su dispositivo o uno autorizado, esa solicitud permite lectura:
usa `authorized=true` y `simulation=false` en esa llamada MCP. En Python son
los parámetros equivalentes del transporte. Por defecto
ningún proceso se inicia; no simules una lista vacía o una inspección exitosa.

Detecta con `detect_devices`; para inspeccionar exige siempre un serial explícito,
incluso con un único dispositivo. `inspect_adb_status` conserva offline,
unauthorized y estados no listos. Una autorización ADB pendiente se resuelve en el
dispositivo por su propietario. No selecciones otro equipo si falla el objetivo.
Los errores MCP llevan `isError=true` y `error.code`; no indican que no haya
dispositivos. Explica el código y detente; no reinicies servidores ADB ni reintentes
indefinidamente. Usa únicamente las solicitudes tipadas de la lista permitida.

Conserva fabricante, modelo, variante, fingerprint, arquitectura y versión como
valores independientes; deja desconocidos los ausentes. Conserva procedencia y
fecha. No publiques seriales ni propiedades completas en logs. La identidad
parcial puede guardarse como snapshot, pero no servir para reutilizar conocimiento
de otra variante. El codename y las pistas de `devices -l` no sustituyen una variante.
Conserva ambos SKU; si falta alguno, la variante queda desconocida. Los valores
reportados no son attestation ni validación de firmware. No reinicies ni cambies
de modo como parte de un diagnóstico. Mantén todos los ensayos con mocks.

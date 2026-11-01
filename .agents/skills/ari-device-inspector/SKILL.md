---
name: ari-device-inspector
description: Detecta conexiones e inspecciona propiedades de un Android autorizado con el adaptador ADB de solo lectura de ARI. Requiere serial explícito; Fastboot y conexión MCP siguen pendientes.
---

# Device Inspector

Lee `AGENTS.md` y `docs/adb.md` desde la raíz de ARI. En Fase 2 usa la API Python
`AdbDeviceInspector` con `AdbSubprocessTransport`. El MCP permanece deshabilitado:
no hay herramientas ADB conectadas a Codex. No ejecutes Fastboot.

Una tarea de desarrollo no autoriza consultar hardware. Cuando el usuario solicite
diagnóstico de su dispositivo o uno autorizado, esa solicitud permite lectura:
configura el transporte con `authorized=True` y `simulation=False`. Por defecto
ningún proceso se inicia; no simules una lista vacía o una inspección exitosa.

Detecta con `detect_devices`; para inspeccionar exige siempre un serial explícito,
incluso con un único dispositivo. `inspect_adb_status` conserva offline,
unauthorized y estados no listos. Una autorización ADB pendiente se resuelve en el
dispositivo por su propietario. No selecciones otro equipo si falla el objetivo.
Explica errores por su código y detente; no reinicies servidores ni reintentes
indefinidamente. Usa únicamente las solicitudes tipadas de la lista permitida.

Conserva fabricante, modelo, variante, fingerprint, arquitectura y versión como
valores independientes; deja desconocidos los ausentes. Conserva procedencia y
fecha. No publiques seriales ni propiedades completas en logs. La identidad
parcial puede guardarse como snapshot, pero no servir para reutilizar conocimiento
de otra variante. El codename y las pistas de `devices -l` no sustituyen una variante.
Conserva ambos SKU; si falta alguno, la variante queda desconocida. Los valores
reportados no son attestation ni validación de firmware. No reinicies ni cambies
de modo como parte de un diagnóstico. Mantén todos los ensayos con mocks.

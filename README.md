# ARI V1 — Android Root Intelligence

Agente Android para **OpenAI Codex en Windows 10/11**. Codex es la interfaz:
no hay GUI ni CLI de ARI. Estado actual: **Fase 5**, versión **0.5.0**, con MCP
para ADB de lectura, investigación offline y análisis estático de firmware.
Fase 6 pendiente; ninguna modificación Android o de imágenes está implementada.

## Qué está disponible

- Identidad e instrucciones del proyecto y ocho skills especializadas locales.
- Núcleo Python con modelos Pydantic, contratos por dominio y política que solo
  permite inspección autorizada y bloquea modificaciones.
- Adaptador ADB con lista cerrada de operaciones, timeout, errores tipados y
  serial explícito. APIs Python: `detect_devices`, `inspect_adb_status`,
  `get_device_properties` e `inspect_device`, probadas con mocks.
- SQLite/SQLAlchemy con versión de esquema, fuentes, snapshots, conocimiento por
  variante y compilación exactas, e historial de resultados.
- Logs JSONL rotativos con eventos, UUID de sesión y PID del servidor, sin mensajes libres ni
  propiedades de dispositivos. Solo `stderr` y archivo; nunca el canal MCP `stdout`.
- MCP STDIO habilitado con once herramientas, esquemas tipados cerrados,
  consentimiento por llamada y errores seguros.
- Motor de evidencia con URL, editor, fecha, confianza, cuatro estados, ámbito e
  identidad exacta; bootloader, restricciones OEM/región/operador y Magisk/KernelSU.
- Informes trazables y planes teóricos con prerrequisitos, riesgos y paradas;
  ningún plan es ejecutable. La búsqueda web la realiza Codex, fuera del motor.
- Pruebas sin dispositivos y scripts de mantenimiento del entorno.
- Lectores estáticos ZIP/Android boot v0–4, init_boot, vendor_boot v3–4,
  recovery y AVB/vbmeta; SHA-256 calculado, metadatos de identidad/build/Android,
  declaraciones A/B e índices rollback. Sin extracción a disco ni ejecución.
- Dos herramientas de archivos: `analyze_firmware` y `verify_firmware_hash`, con
  autorización por llamada y rutas relativas confinadas a `.ari/firmware`.

El adaptador puede consultar ADB al habilitar explícitamente lectura autorizada;
se verificó manualmente un diagnóstico real en un chat nuevo con MCP nativo.
Los datos del dispositivo permanecen privados. Rastreo web automático,
Fastboot, parcheo, desbloqueo y escritura de particiones siguen pendientes.
Las cuatro APIs ADB están disponibles también por MCP. La conexión efectiva se
verificó con el cliente MCP del Codex App Server instalado, usando producción
sin hardware y un servidor fixture separado para las lecturas positivas.

## Preparar el entorno en Windows

Requisitos: Python 3.12–3.14, PowerShell y Git opcional. Para desarrollar y ejecutar
las pruebas no hacen falta dispositivos, ADB, Fastboot, Java, REA ni claves API.
El diagnóstico real requiere un `adb.exe` confiable de
[Android SDK Platform-Tools](https://developer.android.com/tools/releases/platform-tools),
controlador USB apropiado y autorización del propietario. ARI no los instala.

Desde PowerShell, en la carpeta del proyecto:

```powershell
Set-Location 'C:\xampp\PROYECTOS IA\ARI'
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
.\scripts\check.ps1
```

Sustituye `-3.14` por una versión compatible instalada. No es necesario activar
el entorno ni cambiar la política de ejecución global. Si PowerShell bloquea los
scripts, revisa su contenido y ejecútalos con alcance de proceso:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

Para repetir las versiones exactas de la validación local:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
```

El lock registra versiones de esta comprobación, no hashes de procedencia ni una
garantía para otras plataformas. Los rangos admitidos viven en `pyproject.toml`.
La dependencia de desarrollo PyYAML permite usar el validador de skills de Codex;
no es una dependencia del núcleo de ARI.

## SQLite y logs

La inicialización es explícita; importar módulos no crea archivos. Para crear o
comprobar la base local sin abrir una interfaz nueva:

```powershell
.\scripts\initialize-storage.ps1
```

Por defecto, SQLite queda en `.ari/ari.sqlite3` y el log en `.ari/logs/ari.jsonl`.
Para otro directorio, configura `$env:ARI_DATA_DIR` antes de inicializar. No se
cargan archivos `.env`. La base puede guardar números de serie y evidencia que
proporciones: es SQLite local **sin cifrado**, protegida por los permisos de tu
cuenta Windows. No compartas `.ari`; está excluida de Git.

El esquema V1 se crea de forma idempotente. Una versión incompatible o una base
sin versión se rechaza; no hay migraciones destructivas automáticas. `read_only`
describe operaciones Android: SQLite y logs sí escriben archivos locales.

## Diagnóstico ADB de lectura

Pide en Codex, por ejemplo: «ARI, detecta mis dispositivos Android autorizados» o
«ARI, inspecciona el dispositivo con este serial». La skill Device Inspector usa
las herramientas MCP de [docs/mcp.md](docs/mcp.md). La API Python de Fase 2 sigue
documentada en [docs/adb.md](docs/adb.md).

`AdbSubprocessTransport` tiene `authorized=False` y `simulation=True` por defecto:
no lanza procesos ni inventa resultados. Solo una solicitud de diagnóstico de un
dispositivo propio o autorizado permite usar `authorized=True, simulation=False`.
Una tarea de desarrollo no concede esa autorización. Las variables de entorno
no habilitan acceso real.

El ejecutable se resuelve desde una ruta absoluta explícita o desde PATH y se fija
durante la vida del transporte. La inspección siempre requiere serial; no elige
automáticamente un equipo. Distingue ausencia, offline, unauthorized y estados no
listos. Solo lee propiedades enumeradas; no obtiene el volcado completo de getprop.

La variante de diagnóstico conserva el par SKU/ODM SKU. Si falta uno, queda
desconocida; el codename no la sustituye. Las propiedades son valores reportados,
sin probar autenticidad del hardware, del firmware o compatibilidad de root.

Puede guardar snapshots e historial en SQLite si se le entrega el repositorio
local del runtime. No imprime seriales ni propiedades en logs. No guarda una
inspección parcial cuando se pierde el dispositivo o cambia el fingerprint.

## Uso desde Codex y estado MCP

Abre esta carpeta como proyecto. `AGENTS.md` define los límites y
`.agents/skills/` contiene las skills locales para tareas en lenguaje natural.
La integración MCP continúa separada del adaptador Python ADB.

`.codex/config.toml` contiene una entrada MCP con `enabled = true` y rutas
absolutas para este checkout. No se modifica la configuración global. Si mueves
el repositorio, actualiza `command`, `cwd` y `ARI_DATA_DIR`.

El punto de entrada técnico del servidor es `python -m ari.mcp.server`, pensado
para el host MCP, sin argumentos de usuario ni consola de diagnóstico. No lo
uses como CLI interactiva: espera mensajes JSON-RPC por STDIO.

Las herramientas son `get_project_status`, `list_capabilities`, `detect_devices`,
`inspect_adb_status`, `get_device_properties` e `inspect_device`. Las tres últimas
exigen serial. Las cuatro ADB requieren `authorized=true, simulation=false` en
cada llamada, únicamente tras una solicitud de diagnóstico autorizado.

Las pruebas SDK y la conexión con Codex se verifican por separado. Para repetir
la comprobación técnica con el cliente Codex instalado, sin consultar hardware:

```powershell
.\.venv\Scripts\python.exe scripts\verify-codex-mcp.py
```

Este script de mantenimiento no inicia turnos del modelo. Primero comprueba la
configuración de producción y después una sesión efímera con fixture sintética.
El informe local queda en `.ari/codex-verification.json`. Detalles, resultados y
límites de cierre en [docs/mcp.md](docs/mcp.md). No se afirma que se haya recargado
la lista de herramientas de esta ventana: esa presentación depende de la sesión
del cliente. El script comprueba App Server; la disponibilidad nativa se comprobó
por separado en un chat nuevo del proyecto. Si un chat abierto antes de habilitar
ARI sigue sin herramientas, abre otro dentro de ARI y verifica allí el catálogo.
Consulta la [investigación de alcance y sesión](docs/mcp.md#si-un-chat-antiguo-no-muestra-las-herramientas).

## Estructura

```text
.agents/skills/    Ocho especialidades locales de Codex
.codex/           Configuración MCP local habilitada
ari/core/         Configuración, evidencia, capacidades, logs y ciclo de vida
ari/device/       Identidad, inventario, parsers y servicio ADB de lectura
ari/bootloader/   Evaluación documental de estado y posibilidad oficial de desbloqueo
ari/firmware/     Lectores estáticos, hashes, rutas autorizadas e informes teóricos
ari/root/         Compatibilidad, planes teóricos y ejecutor deshabilitado
ari/research/     Evidencia tipada, aplicabilidad exacta y evaluación offline
ari/recovery/     Contrato de recuperación
ari/security/     Políticas de fase y autorización de lectura
ari/knowledge/    Modelos, SQLite y repositorio transaccional
ari/reporting/    Serialización JSON de evidencia aportada
ari/mcp/          Herramientas, esquemas, frontera segura y punto de entrada STDIO
integrations/adb/ Transporte ADB acotado y desactivado por defecto
integrations/     Otras integraciones pendientes
tests/            Datos sintéticos, mocks y pruebas MCP locales
docs/             Arquitectura, fases, fuentes y validación
scripts/          Comprobación, inicialización y verificación real de Codex
```

## Seguridad y siguiente paso

Solo dispositivos propios o autorizados. No se implementa evasión de FRP, MDM,
antirrobo ni controles de acceso. Desbloquear el bootloader normalmente borra
datos; las futuras acciones irreversibles exigirán confirmación específica,
validación de firmware e identidad exacta y condiciones de parada.

La Fase 4 implementa evaluación offline, con fuentes primarias revisadas por Codex.
El caso TCL T613P sigue sin variante exacta ni compatibilidad confirmada; no se
declara rooteable. El informe de dispositivo queda privado en `.ari`.
Fase 5 añade análisis estático acotado; no autentica firmas OEM/AVB ni consulta
contadores antirollback del dispositivo. Los informes siguen bloqueados ante esa
incertidumbre. No se consultó hardware Android durante este desarrollo.
El reintento nativo confirmó nueve herramientas, pero respondió con ARI 0.4.0;
las dos de firmware 0.5.0 no aparecen. Detalles en `docs/validation.md`.
Consulta [firmware.md](docs/firmware.md) para formatos, límites y autorización de rutas.
Los contratos, reglas, fuentes y límites se describen en [research.md](docs/research.md).
Consulta los criterios
de [fases](docs/phases.md), las [decisiones](docs/architecture.md), las
[fuentes verificadas](docs/sources.md) y el [registro de validación](docs/validation.md).

Los paquetes generados en `dist/` no se publican. El wheel distribuye el núcleo
Python; para las instrucciones, skills y configuración de Codex usa el checkout
o el paquete fuente (sdist), que también las incluye.

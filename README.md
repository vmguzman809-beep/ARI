# ARI V1 — Android Root Intelligence

Agente Android para **OpenAI Codex en Windows 10/11**. Codex es la interfaz:
no hay GUI ni CLI de ARI. Este repositorio implementa **únicamente la Fase 1**.

## Qué está disponible

- Identidad e instrucciones del proyecto y ocho skills especializadas locales.
- Núcleo Python con modelos Pydantic, contratos por dominio y política de Fase 1
  que deniega todo acceso a dispositivos.
- SQLite/SQLAlchemy con versión de esquema, fuentes, snapshots, conocimiento por
  variante y compilación exactas, e historial de resultados.
- Logs JSONL rotativos con eventos y UUID de sesión, sin mensajes libres ni
  propiedades de dispositivos. Solo `stderr` y archivo; nunca el canal MCP `stdout`.
- Esqueleto MCP STDIO con `get_project_status` y `list_capabilities`.
- Pruebas sin dispositivos y scripts de mantenimiento del entorno.

No hay detección Android real, investigación automática, análisis de firmware,
parcheo, desbloqueo ni escritura de particiones. Las herramientas propuestas para
esas tareas aparecen como **not_implemented** en el catálogo, sin registrarse como
herramientas MCP. El servidor **no está conectado a Codex**.

## Preparar el entorno en Windows

Requisitos: Python 3.12–3.14, PowerShell y Git opcional. No hacen falta ADB,
Fastboot, Java, REA, claves API ni permisos de administrador en esta fase.

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

## Uso desde Codex y estado MCP

Abre esta carpeta como proyecto. `AGENTS.md` define los límites y
`.agents/skills/` contiene las skills para futuras tareas en lenguaje natural.
Su creación no demuestra que esta conversación las haya recargado; comprueba su
descubrimiento al abrir una nueva sesión en el proyecto.

`.codex/config.toml` contiene una entrada MCP con `enabled = false` y rutas
absolutas para este checkout. No se modifica la configuración global. Si mueves
el repositorio, actualiza `command`, `cwd` y `ARI_DATA_DIR`.

El punto de entrada técnico del servidor es `python -m ari.mcp.server`, pensado
para el host MCP, sin argumentos de usuario ni consola de diagnóstico. No lo
uses como CLI interactiva: espera mensajes JSON-RPC por STDIO.

La conexión real y su verificación en Codex pertenecen a Fase 3. Mantén el servidor
deshabilitado hasta esa tarea. Las pruebas del esqueleto comprueban protocolo en
memoria y transporte STDIO local; no acreditan integración con el cliente Codex.

## Estructura

```text
.agents/skills/    Ocho especialidades locales de Codex
.codex/           Configuración MCP deshabilitada
ari/core/         Configuración, evidencia, capacidades, logs y ciclo de vida
ari/device/       Identidad y contrato de inspección
ari/bootloader/   Contrato de evaluación
ari/firmware/     Contrato de artefactos y análisis
ari/root/         Contrato de plan y ejecutor deshabilitado
ari/recovery/     Contrato de recuperación
ari/security/     Política de bloqueo de Fase 1
ari/knowledge/    Modelos, SQLite y repositorio transaccional
ari/reporting/    Serialización JSON de evidencia aportada
ari/mcp/          Fábrica y punto de entrada STDIO
integrations/     Límites reservados, sin adaptadores activos
tests/            Datos sintéticos, mocks y pruebas MCP locales
docs/             Arquitectura, fases, fuentes y validación
scripts/          Comprobación e inicialización local
```

## Seguridad y siguiente paso

Solo dispositivos propios o autorizados. No se implementa evasión de FRP, MDM,
antirrobo ni controles de acceso. Desbloquear el bootloader normalmente borra
datos; las futuras acciones irreversibles exigirán confirmación específica,
validación de firmware e identidad exacta y condiciones de parada.

La Fase 2 incorporará un adaptador ADB exclusivamente de lectura, selección
explícita de dispositivo, tratamiento de estados offline/no autorizado y pruebas
con transporte simulado. No está implementada todavía. Consulta los criterios
de [fases](docs/phases.md), las [decisiones](docs/architecture.md), las
[fuentes verificadas](docs/sources.md) y el [registro de validación](docs/validation.md).

Los paquetes generados en `dist/` no se publican. El wheel distribuye el núcleo
Python; para las instrucciones, skills y configuración de Codex usa el checkout
o el paquete fuente (sdist), que también las incluye.

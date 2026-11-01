# Arquitectura y decisiones — Fase 1

## ADR-001: Codex es el coordinador y la interfaz

El paquete no tiene `project.scripts`, aplicación gráfica ni shell de usuario.
`AGENTS.md` fija la identidad y ocho skills locales expresan las especialidades.
No se crea un framework de agentes autónomos ni se presupone delegación. Codex
elige las skills y usa solo capacidades disponibles en su sesión.

Se conserva la estructura propuesta. `integrations/` es un paquete separado con
límites reservados y documentados; sus módulos no ejecutan adaptadores. Los
contratos se ubican en cada dominio dentro de `ari/`. No se crean archivos vacíos
para simular funciones implementadas.

## ADR-002: SDK MCP actual y superficie mínima

Se elige el SDK oficial `mcp` 2.3.x, cuya API actual usa `MCPServer`, y STDIO local.
La fábrica es independiente del arranque. Solo registra `get_project_status` y
`list_capabilities`; los quince nombres de diagnóstico propuestos están en un
catálogo de pendientes, no como herramientas que devuelvan resultados ficticios.
Las anotaciones MCP son indicaciones al host, no controles de autorización.

No hay parámetros de procesos, shell, rutas arbitrarias ni herramientas de
modificación en el servidor. La configuración local mantiene `enabled = false`.
Las pruebas en memoria y con un cliente STDIO aislado validan el esqueleto; la
integración con el cliente Codex se comprobará en Fase 3.

## ADR-003: evidencia validada y persistencia local

Pydantic valida modelos, campos adicionales, certeza, fuentes y fechas con zona
horaria. Desconocido se representa con `None`, `unknown` o una limitación explícita.
Un hash declarado es metadato; no equivale a integridad comprobada. Los contratos
de plan tampoco garantizan compatibilidad ni constituyen autorización.

SQLite usa SQLAlchemy 2.1, transacciones y claves foráneas activas. Tablas:

| Tabla | Uso |
| --- | --- |
| `schema_version` | Versión única del esquema V1 |
| `device_snapshots` | Identidad parcial o completa, serial opcional y procedencia |
| `sources` | URL HTTP(S), título y fecha de verificación |
| `knowledge_entries` | Afirmación, certeza, firmware/método opcionales e identidad |
| `knowledge_sources` | Vínculos a fuentes persistidas, con claves foráneas |
| `operation_history` | Sesión, observación opcional y resultado |

Los modelos se guardan como JSON para conservar sus fechas ISO y evidencia
validada. IDs, claves de búsqueda y relaciones ocupan columnas SQL. La clave de
conocimiento es SHA-256 de una tupla JSON ordenada de fabricante, modelo, variante
y fingerprint. No se normaliza mayúsculas ni se aplican coincidencias aproximadas.
Ninguno de esos cuatro campos puede faltar. No se usa el serial para compartir
conocimiento entre dispositivos.

El esquema se inicializa explícitamente y se rechaza una versión desconocida,
una base sin versión o un conjunto de tablas inesperado. No se implementa un
motor de migraciones en esta fase; será necesario antes del primer cambio de
esquema. No se promete verificar la integridad semántica de una base manipulada
externamente. La base local no está cifrada ni firmada; no es un registro forense
inmutable. Los informes JSON serializan evidencia proporcionada, sin diagnosticar.

## ADR-004: bloqueo de dispositivo y ciclo de vida

`PhaseOnePolicy` deniega todas las operaciones de dispositivo, incluida lectura,
preparación y reboot. `DisabledRootExecutor` no acepta un ejecutable, script ni
token de aprobación. No hay variables que habiliten operaciones. Los valores
read_only/simulation de configuración están fijados a true; solo se configura
almacenamiento mediante `ARI_DATA_DIR`.

Importar módulos o crear contratos no crea archivos ni procesos. Abrir un
`AriRuntime` inicializa SQLite y el log y registra el inicio con UUID. Un fallo
libera conexiones y handlers. El servidor STDIO abre un runtime durante su vida.
Se admite un runtime activo por proceso; el logger `ari` es compartido y no
pretende coordinar múltiples runtimes simultáneos.

Las pruebas usan datos sintéticos y mocks. Una guarda impide lanzar procesos,
salvo el comando exacto del servidor Python ARI en la prueba STDIO marcada.
No se consulta ADB/Fastboot ni se modifica un dispositivo como parte de pruebas.

## ADR-005: logs mínimos y dependencias opcionales

El logger propio no cambia handlers del logger raíz. Solo permite códigos de
evento conocidos, nivel, fecha UTC y UUID; descarta texto libre, extras y trazas
que pudieran contener identificadores. Rota a 1 MiB con tres copias. No se registran
propiedades ni seriales. SQLite sí puede guardar evidencia sensible local.

REA, ADB, Fastboot, Magisk, KernelSU, JADX, Apktool, Binwalk y Ghidra no se instalan
ni invocan. Antes de integrar REA se evaluarán API, licencia, versión, plataformas
Windows, dependencias y límites sobre un artefacto sintético. No se incorpora
código ni se afirma compatibilidad con [REA](https://github.com/morluto/rea).

## Límites deliberados

No hay adaptador Android, parser de firmware, cálculo de hashes de firmware,
descargador, investigador web, generador operativo de planes, gestor de
aprobaciones, parcheador ni motor de recuperación. Los contratos futuros no
reemplazan los criterios de aceptación de sus fases.

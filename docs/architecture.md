# Arquitectura y decisiones — Fases 1 y 2

Estado actual: Fase 2, diagnóstico ADB Python con mocks. La Fase 3 sigue pendiente.

## ADR-001: Codex es el coordinador y la interfaz

El paquete no tiene `project.scripts`, aplicación gráfica ni shell de usuario.
`AGENTS.md` fija la identidad y ocho skills locales expresan las especialidades.
No se crea un framework de agentes autónomos ni se presupone delegación. Codex
elige las skills y usa solo capacidades disponibles en su sesión.

Se conserva la estructura propuesta. `integrations/` es un paquete separado con
el adaptador ADB de lectura y límites reservados para otras herramientas. Los
contratos se ubican en cada dominio dentro de `ari/`. No se crean archivos vacíos
para simular funciones implementadas.

## ADR-002: SDK MCP actual y superficie mínima

Se elige el SDK oficial `mcp` 2.3.x, cuya API actual usa `MCPServer`, y STDIO local.
La fábrica es independiente del arranque. Solo registra `get_project_status` y
`list_capabilities`. El catálogo distingue cuatro APIs Python ADB implementadas
de los once nombres pendientes. `mcp_registered` indica qué APIs están expuestas
por este esqueleto: las cuatro ADB siguen fuera de MCP hasta Fase 3.
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

`PhaseOnePolicy` conserva el bloqueo original. `PhaseTwoPolicy` solo admite INSPECT
con autorización explícita y simulación desactivada; rechaza las modificaciones
incluso con autorización. `DisabledRootExecutor` rechaza toda ejecución de root y
no acepta ejecutables, scripts ni tokens. `read_only` permanece fijado a true.

La configuración del runtime tiene simulación true por defecto; puede cambiarse
explícitamente en Python, sin habilitar escrituras. Solo `ARI_DATA_DIR` se lee del
entorno. El adaptador es independiente: su constructor exige su propio opt-in
`authorized=True, simulation=False`. Cambiar un Settings no abre una conexión ni
configura automáticamente un adaptador; tampoco lo hace iniciar AriRuntime.

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

No se instalan herramientas Android. Solo ADB puede invocarse mediante lectura
autorizada; no se ejecutó durante este desarrollo. Fastboot, Magisk, KernelSU,
JADX, Apktool, Binwalk y Ghidra siguen pendientes. Antes de integrar REA se
evaluarán API, licencia, versión, plataformas
Windows, dependencias y límites sobre un artefacto sintético. No se incorpora
código ni se afirma compatibilidad con [REA](https://github.com/morluto/rea).

## ADR-006: transporte ADB cerrado e inventario separado

`ari/device/adb.py` define solicitudes, estados, propiedades y el protocolo de
transporte. `integrations/adb/transport.py` es la única frontera de procesos.
Acepta modelos tipados y los revalida, incluso si se construyeron omitiendo la
validación de Pydantic. No acepta un vector de argumentos ni comandos externos.

Se usan un ejecutable nativo confiable con nombre adb/adb.exe, ruta absoluta fijada,
servidor local 127.0.0.1:5037, argumentos constantes, stdin cerrado, shell del host
deshabilitado y ventana oculta en Windows. El entorno heredado está limitado y
excluye redirección de servidor, serial implícito, trazas y variables de secretos.
El ejecutable no se descarga ni autentica criptográficamente: el operador debe
seleccionar una instalación confiable. No se valida su versión ejecutándolo al importar.
La búsqueda automática solo recorre entradas absolutas de PATH, sin incluir CWD
implícitamente ni aceptar entradas relativas.

Cada operación tiene un timeout de 5 segundos por defecto, configurable entre
0.1 y 10. Una inspección completa hace como máximo 16 llamadas, sin reintentos.
Se valida el tamaño de stdout/stderr tras su captura (64 KiB combinados) y de
cada propiedad (4 KiB); esto no es un límite de memoria durante la captura.
Solo se aceptan avisos conocidos de inicio del daemon en stderr exitoso. Los
errores no incluyen argumentos, rutas, seriales ni salida cruda.

El contrato inicial de detección devolvía snapshots. Se cambia a `AdbInventory`
porque `devices -l` informa estados y pistas, sin demostrar identidad. La inspección
devuelve `DeviceInspection`, con snapshot, lecturas fechadas y limitaciones. Estado
no listo, serial duplicado, desconexión o cambio de fingerprint detienen la lectura.
La misma identidad no puede garantizarse de forma atómica leyendo propiedades
secuenciales: repetir el fingerprint solo detecta algunas discrepancias.

La variante de diagnóstico se representa como JSON del par ordenado de SKU del
hardware y SKU ODM, solo si ambos están presentes. No se infiere de modelo,
codename o fingerprint. El ABI principal es el primero de la lista reportada,
con fallback a la propiedad ABI antigua cuando falta la lista. Se conservan ambas
lecturas. Estos valores no demuestran attestation ni compatibilidad de firmware.

SQLite conserva snapshots y eventos con IDs enlazados si se entrega un repositorio
al inspector. Los registros se transaccionan individualmente; no se introduce una
migración ni un cambio de esquema. Las lecturas completas se devuelven al llamador,
sin volcarlas a logs ni publicarlas. Detalles y códigos de error en `adb.md`.

## Límites deliberados

No hay adaptador Fastboot, parser de firmware, cálculo de hashes de firmware,
descargador, investigador web, generador operativo de planes, gestor de
aprobaciones, parcheador ni motor de recuperación. Los contratos futuros no
reemplazan los criterios de aceptación de sus fases.

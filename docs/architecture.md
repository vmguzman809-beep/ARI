# Arquitectura y decisiones — Fases 1 a 4

Estado actual: Fase 4, MCP de lectura con conexión verificada mediante el cliente
MCP del Codex App Server instalado y herramientas nativas verificadas en un chat
nuevo. Se completó un diagnóstico real autorizado de lectura en Fase 3. La Fase 4
añade evaluación documental offline, sin nuevos diagnósticos de hardware.

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
La fábrica es independiente del arranque. Fase 3 registró dos herramientas de
metadatos y cuatro APIs ADB. Fase 4 conserva esas seis y añade tres de investigación
offline; quedan ocho nombres pendientes. `mcp_registered` distingue el registro real.
Las anotaciones MCP son indicaciones al host, no controles de autorización.

No hay parámetros de procesos, shell, rutas arbitrarias ni herramientas de
modificación en el servidor. La configuración local tiene `enabled = true`.
Pruebas SDK en memoria/STDIO y comprobación mediante el cliente Codex instalado
son validaciones distintas, registradas por separado en `mcp.md` y `validation.md`.

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
evento conocidos, nivel, fecha UTC, UUID y PID del proceso; descarta texto libre, extras y trazas
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

## ADR-007: frontera MCP, consentimiento y cliente real

`ari/mcp/models.py` define entradas cerradas y fallos tipados.
`ari/mcp/boundary.py` valida antes que el SDK pueda reflejar argumentos privados,
publica los mismos esquemas cerrados y normaliza los errores. El SDK 2.3 devuelve
modelos o diccionarios según la ruta; ambas formas se tratan explícitamente.
La salida del backend se revalida y se compara con el serial solicitado antes de
que el SDK la convierta. Una excepción inesperada nunca se entrega ni se registra
como traceback: se transforma en un código estático.

Consentimiento y simulación pertenecen a cada llamada, sin estado de autorización
heredado. La fábrica no se ejecuta para solicitudes denegadas. Las operaciones ADB
se serializan mediante un lock AnyIO y se realizan fuera del bucle del protocolo,
en un hilo que no se abandona al cancelar la llamada. AnyIO pasa a ser dependencia
directa, conservando la versión ya registrada en el lock. El transporte y el
ejecutor de root mantienen los límites de lectura de Fase 2.

La prueba real usa el binario Codex instalado, no `mcp.Client`. El comprobador
solo habla el protocolo App Server; el cliente MCP de Codex realiza la conexión
STDIO con ARI. Se crean sesiones efímeras sin turnos del modelo ni chats persistentes.
Una lee la configuración real de producción con hardware bloqueado; otra usa
el módulo fixture de pruebas como override de esa sesión. El producto no ofrece
un parámetro MCP ni variable de entorno para seleccionar fixtures o ejecutables.

En Windows se observó salida cero de Codex y terminación del proceso ARI, mediante
espera de proceso de solo lectura. No se observó el callback Python de cierre con
ese cliente; el cierre por EOF y el finalizador se prueban con el SDK por separado.
No se afirma que el cierre del cliente ejecute callbacks ni que la ventana actual
haya recargado su lista visual. No cambian SQLite, firmware ni operaciones Android.

## ADR-008: investigación offline, evidencia y planes teóricos (Fase 4)

`ari/research` define fuentes HTTP(S) con editor y fecha, afirmaciones tipadas,
confianza, cuatro estados y ámbito general/modelo/compilación exacta. No se cambia
SQLite: los informes son valores JSON que el coordinador conserva localmente.
La URL permite contrastar una fuente; no demuestra que el motor haya leído su
contenido. Codex realiza la búsqueda y curación, sin convertir textos en comandos.

El evaluador excluye evidencia de otra identidad o incompleta, general/modelo,
caducada (180 días), contexto regional/operador no coincidente y kernel/GKI/KMI
no comprobado para KernelSU. Conserva sus IDs y motivos. La observación de estado
del bootloader y el permiso OEM requieren evidencia de observación; la documentación
del proyecto no equivale a medir el equipo. Conflictos bloquean conclusiones.

Solo evidencia confirmada aplicable puede fijar un valor concluyente; probable
y no verificada se conservan sin promoverlas. Los tipos de editor son etiquetas
aportadas, no autenticación automática. No hay garantía criptográfica de fuentes.
El informe separa estado, posibilidad oficial y restricciones; el plan solo genera
revisiones narrativas controladas y mantiene `executable=false` incluso ante todas
las confirmaciones sintéticas. Firmware, hashes, particiones, slots, antirollback
y recuperación son requisitos futuros, sin implementarlos en esta fase.

Se añaden tres herramientas a la frontera cerrada existente; se conservan seis.
No se cambia el transporte ADB, su whitelist, las políticas de autorización ni
el bloqueo del ejecutor. No se añade red, Fastboot ni un intérprete.

## Límites deliberados

La comprobación posterior de integración distinguió catálogo del chat y transporte
MCP. El servidor y la configuración local ya eran válidos; un chat nuevo cargó
las seis herramientas y realizó una lectura autorizada. Se reforzó el verificador
para comprobar la capa efectiva del proyecto y no presentar su resultado como
prueba del catálogo nativo. No se modificaron políticas ni se amplió el alcance
de la configuración a todos los proyectos. Evidencia y límites en `mcp.md`.

No hay adaptador Fastboot, parser de firmware, cálculo de hashes de firmware,
descargador, rastreador web, generador de planes ejecutables, gestor de
aprobaciones, parcheador ni motor de recuperación. Los contratos futuros no
reemplazan los criterios de aceptación de sus fases.

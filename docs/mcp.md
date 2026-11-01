# MCP con Codex — Fase 4 (0.4.0)

La versión 0.4.0 conserva las seis herramientas ADB/metadatos y añade tres de
investigación offline, después de validar contratos y pruebas del motor:

| Herramienta nueva | Entrada | Salida |
| --- | --- | --- |
| `analyze_unlock_compatibility` | `research: ResearchInput` | Estado y capacidad oficial separados; OEM, región y operador |
| `check_root_compatibility` | `research: ResearchInput` | Informe, evidencia, fuentes, exclusiones y bloqueos |
| `create_root_plan` | `research: ResearchInput` | Plan teórico, prerrequisitos, riesgos y paradas; `executable=false` |

Los nuevos modelos anidados también rechazan campos extra. No aceptan serial,
consentimiento de hardware, rutas, ejecutables ni shell. No consultan URL, SQLite
ni Android: analizan evidencia entregada en esa llamada. La autorización ADB
conserva sus valores y validación por llamada en las seis herramientas existentes.
Los textos de fuentes y etiquetas de editor no se autentican; son datos que Codex
debe contrastar. Reglas y vigencia de fuentes: `research.md`.

La allowlist local contiene nueve nombres. La verificación App Server se actualiza
para llamar los tres métodos con datos sintéticos y comprobar rechazo de extras,
sin turnos del modelo ni hardware. El catálogo nativo de un chat ya abierto puede
seguir mostrando la versión anterior: solo una nueva comprobación nativa puede
acreditar su recarga. Los resultados reales están en `validation.md`.

## Registro y frontera conservada de Fase 3

ARI 0.3.0 ofrece seis herramientas STDIO de lectura. La configuración local está
habilitada en `.codex/config.toml`, con el Python de `.venv`, directorio de trabajo
del checkout y almacenamiento local `.ari`. No modifica configuración global,
permisos del cliente ni el alcance de las operaciones Android.

## Configuración y conexión

Abre este proyecto como confiable en Codex. Si cambias la carpeta, actualiza las
rutas `command`, `cwd` y `ARI_DATA_DIR` de `.codex/config.toml`. Instala el paquete
siguiendo README. El servidor se inicia por el host MCP; no es una CLI interactiva.

`codex mcp get ari --json` muestra la configuración efectiva, pero no demuestra
conexión ni ejecución. La comprobación efectiva usa el Codex App Server instalado
y su cliente MCP: `initialize`, una sesión efímera, `mcpServerStatus/list` y
`mcpServer/tool/call`. No se usa un cliente MCP escrito por ARI ni el cliente del
SDK como sustituto de Codex. El servidor sí utiliza el SDK MCP oficial.

```powershell
.\.venv\Scripts\python.exe scripts\verify-codex-mcp.py
```

Es una comprobación técnica explícita, separada de `scripts/check.ps1`. No inicia
turnos del modelo, no crea chats persistentes ni consulta Android. La primera
conexión lee la configuración real del proyecto. La segunda modifica solo su
sesión efímera para lanzar `tests/codex_fixture_server.py`, que no tiene backend
de hardware. No hay variables ni parámetros MCP para activar fixtures en producción.
El informe queda en `.ari/codex-verification.json`; logs completos permanecen locales.
El verificador comprueba también `config/read` y la capa de proyecto. Su informe
declara `verification_scope=app_server_protocol_only` y
`native_chat_tools_verified=false`: no prueba el catálogo de un turno del modelo.

Se comprobó con **codex-cli 0.166.0-alpha.5.1**, el mismo ejecutable instalado que
ofrece App Server. La prueba registra `runtimeStatus=connected`, versión ARI,
esquemas y herramientas, llamadas, errores y terminación de procesos. No demuestra
una recarga visual de herramientas en la ventana actual, ni compatibilidad USB
o identidad de un Android físico. El estado estático `codex_connection=verify_on_client`
recuerda que el servidor no puede certificar por sí mismo la identidad del cliente.

## Si un chat antiguo no muestra las herramientas

La configuración guardada, el descubrimiento del servidor y el catálogo nativo
del modelo son tres comprobaciones distintas. La configuración local se aplica
al proyecto confiable y a sus subcarpetas; no se extiende a otras carpetas. No se
añade una copia global para resolver un problema de un chat concreto.

En la comprobación del 1 de noviembre de 2026 se observó:

- Este proyecto ya era confiable. La configuración efectiva calculada para su
  directorio contenía ARI habilitado y las seis herramientas permitidas. Fuera
  del proyecto ARI no aparecía: comportamiento esperado del alcance local.
- El chat original, creado antes de habilitar MCP, seguía sin exponer herramientas
  ARI en su catálogo. El verificador App Server sí descubría y llamaba al servidor.
- Un chat nuevo del mismo proyecto expuso las seis herramientas nativas y ejecutó
  directamente `get_project_status`, `list_capabilities` e `inspect_device`.
- El primer turno del chat nuevo falló por un modelo predeterminado incompatible
  con esa cuenta. Se reintentó únicamente ese chat con el modelo elegido
  expresamente por el usuario, sin cambiar el predeterminado global.

El fallo quedó limitado a la sesión antigua, no al servidor ni a sus esquemas.
La explicación consistente con las mediciones es que su catálogo se había cargado
antes de habilitar ARI y no se actualizó. No se inspeccionó el mecanismo interno
de caché del cliente. La corrección comprobada fue abrir un chat nuevo en ARI;
no se reinició Android, ADB ni el equipo, ni se modificó seguridad.

Cuando cambie la configuración, verifica desde un chat nuevo: comprueba primero
las seis herramientas nativas y llama a los dos métodos de metadatos. No declares
disponibilidad basándote solo en `codex mcp get` o en el comprobador App Server.
Si el nuevo turno ni siquiera inicia, resuelve ese error de modelo por separado,
sin cambiarlo automáticamente ni atribuirlo al servidor MCP.

La prueba nativa posterior incluyó un diagnóstico real autorizado, exclusivamente
de lectura. Sus seriales y propiedades se guardaron en `.ari/new-session-diagnostic.json`,
excluido de Git. El [resumen público](native-session-verification.json) contiene
solo nombres de herramientas, estado de las comprobaciones y límites.

## Herramientas y esquemas

| Herramienta | Entrada | Resultado exitoso |
| --- | --- | --- |
| `get_project_status` | Objeto vacío | Versión, fase y valores predeterminados de seguridad |
| `list_capabilities` | Objeto vacío | Catálogo; distingue implementado y pendiente |
| `detect_devices` | Consentimiento por llamada | Inventario ADB, estados y fecha; sin selección implícita |
| `inspect_adb_status` | Serial y consentimiento | Estado de ese serial en un inventario fresco |
| `get_device_properties` | Serial y consentimiento | Doce propiedades enumeradas con fechas |
| `inspect_device` | Serial y consentimiento | Snapshot, propiedades, procedencia y limitaciones |

Todos los esquemas de entrada prohíben campos adicionales. Los esquemas de salida
derivan de los modelos Pydantic de Fase 2. No se aceptan comandos, scripts,
ejecutables, rutas, backends ni propiedades fuera de la lista cerrada.

El consentimiento tiene `authorized=false` y `simulation=true` por defecto,
booleanos estrictos. Para lectura real, tras la solicitud del propietario o
responsable autorizado, Codex pasa `authorized=true, simulation=false` en cada
llamada. Una llamada exitosa no autoriza la siguiente. En simulación no se
fabrican observaciones: se devuelve un error seguro y no se construye el backend.
Una tarea de desarrollo o de conexión no autoriza inspeccionar hardware.

Las tres herramientas dirigidas siempre exigen serial, incluso con un solo
dispositivo. Se valida antes del backend y se compara con el serial del resultado;
una discrepancia se convierte en `device_changed`. No hay selección por índice,
primer dispositivo o variable ANDROID_SERIAL. Offline/unauthorized pueden
observarse con `inspect_adb_status`; leer propiedades exige estado listo.

Las herramientas llevan `readOnlyHint=true` y `destructiveHint=false`. Los
diagnósticos no se anuncian como idempotentes porque sus observaciones e historial
cambian. Estas anotaciones son metadatos para Codex, no controles de autorización.
Los controles efectivos son modelos cerrados, consentimiento por llamada, lista
de operaciones del transporte y bloqueo independiente del ejecutor de root.

## Errores seguros

En un fallo, el resultado MCP contiene `isError=true`, contenido JSON y
`structuredContent` con esta forma:

```json
{
  "ok": false,
  "error": {
    "code": "device_offline",
    "message": "ARI stopped this read-only request; consult the error code."
  }
}
```

Los códigos ADB de `adb.md` se conservan. Se agregan `invalid_arguments`,
`unknown_tool` e `internal_error`. No se incluyen entradas rechazadas, nombres de
campos del cliente, seriales, rutas, argumentos, propiedades ni excepciones crudas.
Una frontera anterior a la validación del SDK evita que sus mensajes de validación
reflejen datos privados. El backend y su salida se validan antes de la conversión
del SDK. Las excepciones imprevistas pasan a `internal_error`, sin traceback.

Codex también puede rechazar una herramienta no anunciada antes de enviarla a ARI;
eso es un rechazo del cliente, distinto del `unknown_tool` del servidor. Ninguno
autoriza una ruta alternativa por shell. Un error no equivale a inventario vacío.
Los errores de arranque del proceso usan un mensaje estático y salida no cero.

## Ejecución, historial y cierre

Las lecturas ADB se serializan y se ejecutan en un hilo de trabajo para no bloquear
el protocolo. La fábrica de producción crea un transporte con consentimiento de
esa llamada y el repositorio local del runtime. No se consulta Android al importar,
descubrir herramientas, iniciar el servidor o pedir metadatos.

Cada proceso ADB conserva su timeout de 5 segundos; la inspección puede hacer
hasta 16 llamadas. El timeout MCP de Codex se configura a 100 segundos. No hay
reintentos automáticos, operaciones de escritura ni comandos de reinicio.
Una cancelación del SDK espera a que termine el hilo activo; no lo abandona.

Los logs de ARI solo contienen eventos conocidos, fecha UTC, nivel, UUID de sesión
y PID de proceso. Los resultados ADB se entregan al cliente; no se vuelcan a esos
logs. Codex puede conservar resultados en su propio historial según su configuración.
SQLite y los logs se mantienen fuera de Git. El esquema SQLite no cambió.

Hay dos comprobaciones distintas de cierre:

- Con el cliente SDK por STDIO se observan EOF, `runtime_stopped` y liberación del
  runtime, además de las pruebas en memoria.
- Con Codex real en Windows se observó salida cero del cliente y terminación del
  proceso ARI mediante un handle de espera de Windows. No se observó el finalizador
  Python en esas conexiones: no se afirma que Codex cierre mediante EOF ni que
  ejecute callbacks de limpieza. La comprobación terminó sin procesos ARI activos.

El cierre real se verificó después de llamadas terminadas, sin hardware activo.
No es una prueba de desconexión física o de cierre mientras se ejecuta ADB real.

## Alcance de la verificación

El informe original cubría 30 comprobaciones. El verificador actualizado cubre
32: 13 con producción sin hardware y
19 con fixture sintética. Incluye seis herramientas y esquemas, metadatos,
autorización y simulación predeterminadas, serial inválido/ausente, rechazo de
reboot, lecturas positivas sintéticas, errores offline/unauthorized/objetivo ausente,
consentimiento no reutilizado y cierre. Las pruebas SDK siguen siendo una capa
separada. Consulta también [validation.md](validation.md) y el
[informe de verificación](codex-verification.json).

El comprobador App Server no ejecuta ADB real. La comprobación manual del chat
nuevo sí realizó el diagnóstico de lectura autorizado. No se ejecutaron Fastboot,
root, reboot, desbloqueo, escritura ni flasheo. La Fase 4 permanece pendiente.

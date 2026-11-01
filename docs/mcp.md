# MCP con Codex — Fase 3

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

Se comprobó con **codex-cli 0.166.0-alpha.5.1**, el mismo ejecutable instalado que
ofrece App Server. La prueba registra `runtimeStatus=connected`, versión ARI,
esquemas y herramientas, llamadas, errores y terminación de procesos. No demuestra
una recarga visual de herramientas en la ventana actual, ni compatibilidad USB
o identidad de un Android físico. El estado estático `codex_connection=verify_on_client`
recuerda que el servidor no puede certificar por sí mismo la identidad del cliente.

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

El informe reproducible cubre 30 comprobaciones: 11 con producción sin hardware y
19 con fixture sintética. Incluye seis herramientas y esquemas, metadatos,
autorización y simulación predeterminadas, serial inválido/ausente, rechazo de
reboot, lecturas positivas sintéticas, errores offline/unauthorized/objetivo ausente,
consentimiento no reutilizado y cierre. Las pruebas SDK siguen siendo una capa
separada. Consulta también [validation.md](validation.md) y el
[informe de verificación](codex-verification.json).

No se ejecutó ADB real, Fastboot, root, reboot, desbloqueo, escritura ni flasheo.
La investigación de compatibilidad de Fase 4 permanece pendiente.

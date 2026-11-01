# Diagnóstico ADB — Fase 2

Implementado como biblioteca Python usada desde Codex. No agrega GUI, CLI ni
herramientas MCP. Validado con mocks; todavía sin verificación en hardware real.

## API y autorización

`AdbDeviceInspector` depende del protocolo `AdbReadTransport`. El adaptador
`AdbSubprocessTransport` permanece en simulación y sin autorización por defecto.
Una llamada en ese estado lanza un error tipado sin resolver ni ejecutar ADB;
no devuelve resultados simulados que puedan confundirse con observaciones.

Cuando el usuario solicite diagnóstico de un dispositivo propio o autorizado,
Codex puede crear un transporte con opt-in explícito. Ejemplo de integración,
que no debe ejecutarse como parte de una tarea de desarrollo:

```python
from pathlib import Path
from ari.device.inspector import AdbDeviceInspector
from integrations.adb.transport import AdbSubprocessTransport

transport = AdbSubprocessTransport(
    executable=Path(r"C:\Android\platform-tools\adb.exe"),
    authorized=True,
    simulation=False,
    timeout_seconds=5,
)
inspector = AdbDeviceInspector(transport)
```

El constructor no ejecuta nada. La ruta es un ejemplo: debe seleccionarse una
instalación confiable de Platform-Tools. Si se omite, se resuelve adb.exe desde
las entradas absolutas de PATH en la primera operación autorizada y se fija esa
ruta durante la sesión. No se busca implícitamente en CWD ni en entradas relativas.
No se aceptan wrappers .cmd/.bat/.ps1 ni argumentos dentro de la ruta. No se
comprueban firma ni versión del binario; la presencia de un archivo no prueba
que sea una distribución oficial. No hay instalación automática.

| Método | Resultado | Selección |
| --- | --- | --- |
| `detect_devices()` | `AdbInventory`, conexiones y fecha; cero dispositivos es válido | No lee propiedades |
| `inspect_adb_status(serial)` | `AdbConnection`, estado reportado y fecha del inventario fresco | Serial obligatorio |
| `get_device_properties(serial)` | `AdbProperties`, doce lecturas con sus fechas | Serial obligatorio y estado device |
| `inspect_device(serial)` | `DeviceInspection`, snapshot, propiedades y limitaciones | Serial obligatorio y estado device |

Incluso con un solo dispositivo se exige serial. Los seriales de USB, emuladores,
TCP/IP y mDNS deben pertenecer al alfabeto conservador validado; no se aceptan
opciones, espacios, controles ni metacaracteres de shell. Una entrada no reconocida
detiene la operación; no se selecciona otro dispositivo automáticamente.

Si se desea historial local, construir el inspector con
`repository=runtime.repository, run_id=runtime.run_id`, dentro de un `AriRuntime`
abierto. Este runtime por sí solo no consulta dispositivos. Una inspección exitosa
guarda el snapshot y un evento enlazado; los fallos ADB observados se registran por
código. Un fallo de lectura no guarda una inspección parcial. Los snapshots y
eventos usan transacciones individuales; un fallo de almacenamiento debe propagarse.

## Operaciones permitidas

El transporte solo admite `AdbRequest` con estas formas, revalidadas antes del
proceso. No hay parámetro para comandos o vectores de argumentos libres:

- Inventario: `devices -l`.
- Estado: `-s SERIAL get-state`.
- Propiedad: `-s SERIAL shell -T getprop PROPIEDAD_PERMITIDA`.

Se antepone siempre `-H 127.0.0.1 -P 5037`. No se usa shell del host, stdin está
cerrado y la ventana del proceso se oculta en Windows. El getprop remoto recibe
únicamente una propiedad enumerada y no admite scripts ni contenido generado.

| Propiedad | Interpretación |
| --- | --- |
| `ro.product.manufacturer` | Fabricante reportado |
| `ro.product.model` | Modelo reportado |
| `ro.product.device` | Codename, separado de la variante |
| `ro.product.name` | Nombre de producto, separado de la variante |
| `ro.boot.hardware.sku` | SKU de hardware reportado |
| `ro.boot.product.hardware.sku` | SKU ODM reportado |
| `ro.build.id` | ID de compilación reportado |
| `ro.build.fingerprint` | Fingerprint sin descomponer ni adivinar identidad |
| `ro.build.version.release` | Versión Android reportada |
| `ro.build.version.sdk` | Nivel SDK, conservado como valor reportado |
| `ro.product.cpu.abilist` | Lista de ABI reportada; primero como ABI principal |
| `ro.product.cpu.abi` | Fallback legado si no hay lista |

Ausente, vacío o marcadores unknown/null permanecen desconocidos. La variante
del snapshot es el JSON `[hardware_sku, odm_sku]` cuando ambos están disponibles;
si falta alguno o la representación supera el límite, queda `None`. No demuestra
la denominación comercial ni la intercambiabilidad de firmware. Las pistas de
`devices -l` nunca sustituyen las propiedades y no se reutiliza conocimiento con
una identidad incompleta.

Antes y después de las propiedades se comprueba get-state; el fingerprint se
repite al final. Si cambia o falla una llamada, la inspección se detiene. Estas
lecturas no son atómicas, ni attestation de hardware o de firmware original.
No se examinan root, bootloader, antirollback ni compatibilidad Magisk/KernelSU.

## Errores y condiciones de parada

`AdbError.code` es un `AdbErrorCode`. Los mensajes son estáticos y no incluyen
serial, argumentos, rutas privadas, salida cruda ni propiedades. No se imprimen
respuestas a stdout/stderr ni a logs de ARI. No hay reintentos automáticos.

| Código | Tratamiento |
| --- | --- |
| `authorization_required`, `simulation_enabled` | No se inicia proceso; respetar el alcance del usuario |
| `tool_not_found`, `invalid_executable` | Seleccionar una instalación confiable; no descargar otra automáticamente |
| `invalid_request`, `invalid_target` | Corregir la solicitud tipada o el serial; no interpretar texto como comando |
| `no_devices`, `device_not_found` | Distinguir inventario vacío de objetivo ausente; no seleccionar otro equipo |
| `device_offline`, `device_unauthorized` | Detener lectura; el propietario revisa conexión o autorización en el dispositivo |
| `access_denied`, `server_unavailable` | Revisar permisos/controlador/servidor local sin reinicios automáticos |
| `device_not_ready` | Informar recovery/sideload/bootloader/desconocido; no cambiar de modo |
| `ambiguous_target` | Rechazar serial duplicado o resolución ambigua |
| `timeout`, `command_failed`, `invalid_response` | Detener; no convertir el error en una observación vacía |
| `device_changed` | Descartar la inspección parcial y revisar la identidad antes de otra solicitud |

Cada proceso tiene timeout de 5 segundos por defecto (rango 0.1–10). La inspección
hace hasta 16 llamadas, sin reintentos. Tras capturar se limita stdout+stderr a
64 KiB y cada propiedad a 4 KiB; no se promete un límite de memoria en la captura.
Solo se toleran los dos avisos conocidos de arranque del daemon en stderr exitoso.

Solo lectura describe el dispositivo: el cliente ADB puede iniciar su daemon
local y crear archivos propios de autenticación en el host. ARI no ejecuta
start/kill-server, reconnect, root/unroot, reboot, remount, push, install, pair,
connect, tcpip, unlock, flash, erase ni comandos de firmware. No altera claves ni
resuelve por su cuenta una autorización pendiente en el dispositivo.

## Verificación pendiente

Todas las pruebas de ADB sustituyen el transporte o `subprocess.run` por mocks,
manteniendo la guarda que bloquea procesos reales. Solo la prueba preexistente
STDIO permite el comando exacto del servidor Python local; no consulta Android.
No se ejecutó ADB, ni siquiera para consultar versión, durante esta implementación.

Cuando el usuario solicite un diagnóstico real se registrarán herramienta y versión,
objetivo elegido, estado, propiedades observadas y limitaciones. Esto no habilita
el MCP ni implica empezar Fase 3. El servidor y su configuración siguen deshabilitados.

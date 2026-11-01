# Discrepancia MCP 0.4.0/0.5.0: diagnóstico demostrado

Verificación del **1 de noviembre de 2026**, America/Santo_Domingo.
Versión del proyecto conservada: **0.5.0**, Fase 5. No se inicia Fase 6.

## Causa y corrección

El chat presentado como nuevo se había creado cuando ARI aún era 0.4.0. Después
se reanudó ese mismo chat cambiando únicamente su modelo; no se creó otra sesión
MCP tras actualizar el servidor. Respondió con la versión y nueve herramientas
del proceso anterior, mientras las conexiones nuevas de App Server cargaban 0.5.0.

La instalación editable y las rutas eran correctas. La corrección operacional
consistió en crear **otro chat del proyecto después de actualizar**, con el modelo
elegido por el usuario solo para ese chat. Ese chat anunció once herramientas,
respondió 0.5.0 y completó las pruebas nativas de firmware sintético.

No hubo que reinstalar, modificar código, rutas, configuración MCP, permisos,
modelo global o dependencias. No se terminaron los procesos de chats anteriores.

## Evidencia cronológica

Marcas UTC, conservadas separadamente de la fecha local:

| Hecho observado | Hora UTC |
| --- | --- |
| Creación del chat anterior | 15:14:30 |
| Inicio de un runtime ARI bajo Codex coincidente con esa creación | 15:14:31 |
| Escritura de `ari/__init__.py` con versión 0.5.0 | 15:27:47 |
| Última escritura de `ari/mcp/server.py` antes del diagnóstico | 15:45:31 |
| Reintento del mismo chat, que respondió 0.4.0/nueve herramientas | 16:43:42 |
| Creación del chat realmente nuevo | 17:07:08 |
| Nuevo runtime ARI observado bajo el mismo host Codex | 17:07:09 |

Se observaron procesos anteriores de 14:04 y 15:14 todavía activos. Los snapshots
Win32 registraron ejecutable, argumentos, creación y parentesco. La asociación de
un PID con un chat se basa en tiempo y parentesco, no en un campo PID del protocolo;
no se inspeccionó memoria con un depurador. La prueba decisiva es que, sin cambiar
instalación/configuración, la nueva conexión nativa respondió 0.5.0 y once herramientas.

El código registra herramientas al crear el servidor y captura `__version__` al
importar los módulos; no implementa recarga automática de código. Esto concuerda
con la [caché de módulos de Python](https://docs.python.org/3.14/reference/import.html#the-module-cache).
La documentación de [Codex App Server](https://learn.chatgpt.com/docs/app-server)
distingue configuración efectiva y conexión MCP de un hilo, y especifica que las
consultas con `threadId` reutilizan su conexión. Esa documentación apoya el
mecanismo; los resultados observados son la evidencia concreta de esta instalación.

## Rutas e instalación efectivas

- `config/read` confirmó la capa local de `.codex/config.toml`, servidor habilitado
  y allowlist exacta de once nombres. No se confundió la configuración con catálogo nativo.
- Comando efectivo: Python de `.venv/Scripts/python.exe`; argumentos constantes
  `-m ari.mcp.server`; `cwd` igual al checkout ARI.
- Python 3.14.6, `sys.prefix` en `.venv`, sin paquetes globales habilitados.
- Distribución instalada en `.venv/Lib/site-packages`: 0.5.0, editable apuntando al
  checkout. Se comprobó ese `dist-info` expresamente, además del metadato del proyecto.
- `ari.__file__` y `ari.mcp.server.__file__` apuntan al checkout; versión importada
  por un proceso nuevo: 0.5.0. No se encontró otra copia que explicara el desfase.
- En Windows, el launcher de `.venv` crea un proceso del Python base. Ese ejecutable
  base no implica que se estén usando sus paquetes globales; se verificó el prefijo.

Rutas completas, PIDs, IDs de chats y snapshots quedan solo en `.ari/mcp-load-audit.json`.

## Validación nativa y regresión

En el chat nuevo se observaron exactamente las once herramientas ARI y seis
eventos MCP reales: metadatos, rechazo esperado sin autorización, hash autorizado,
análisis estático y segundo hash. Las llamadas no fueron sustituidas por SDK/CLI.

El único input de firmware fue una imagen sintética creada desde cero de 12 288
bytes. Se reconoció `android_boot`, cabecera 3; ambos hashes coincidieron con el
esperado y el padre volvió a comprobar el fixture propio. Identidad insuficiente,
firmware bloqueado y plan `executable=false`. El rechazo fue
`file_authorization_required`; no se instrumentó por separado el sistema operativo
para demostrar ausencia de lecturas en esa llamada, aunque la guarda está probada.

`scripts/check.ps1`: **357 pruebas** aprobadas, Ruff, formato y `pip check` correctos.
El comprobador independiente App Server completó **49 casos**, sin turnos del modelo
ni hardware; su resultado no se usa como prueba del catálogo nativo.

Resumen público: [mcp-load-verification.json](mcp-load-verification.json).
Evidencia nativa íntegra: `.ari/native-050-fresh-verification.json`, privada.
No se leyeron firmwares privados ni dispositivos. No hubo ADB real, Fastboot,
desbloqueo, root, reinicio, parcheo, flasheo o escritura de particiones.

## Regla de mantenimiento

Después de actualizar ARI, comprobar versión y catálogo en un chat creado después
del cambio. Reanudar o cambiar el modelo de uno anterior no acredita una nueva
carga del servidor. Antes de analizar archivos, exigir versión 0.5.0 y las once
herramientas; mantener selección y autorización de archivos por llamada.

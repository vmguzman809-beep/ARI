# Registro de validación — Fases 1 a 3

Entorno comprobado: Windows, Python **3.14.6**, Codex
**0.166.0-alpha.5.1**, PowerShell. Fecha del cliente: **31 de octubre de 2026**.

La carpeta inicial solo contenía `ARI_V1_Prompt_Maestro_Codex.txt`. En la entrega
original de Fase 1 se conservó ese archivo y se inicializó Git local, sin publicar.
Después, el usuario autorizó la subida y sincronización con GitHub.

## Fase 1 — comprobaciones originales

- Instalación editable en `.venv` con dependencias de desarrollo.
- `scripts/check.ps1`: Ruff, formato, Pytest y `pip check` aprobados.
- **37 pruebas aprobadas**: validación de evidencia; persistencia tras reapertura;
  fuentes y fechas; rechazo de claves incompletas; aislamiento de fabricante,
  modelo, variante y compilación; rollback y claves foráneas; rechazo de esquemas
  ajenos; bloqueo de operaciones; configuración sin habilitadores; logs sin texto
  sensible; ciclo de vida y errores; herramientas MCP en memoria y por STDIO.
- La prueba STDIO inicia exclusivamente el servidor Python local con SQLite y logs
  temporales, incluso en una ruta con espacios y caracteres no ASCII.

- Las ocho skills aprobaron `quick_validate.py` de la skill instalada
  `skill-creator`, ejecutado con UTF-8 y PyYAML 6.0.3.
- `.codex/config.toml` se analizó con `tomllib`: entrada deshabilitada y rutas
  locales existentes. No se modificó la configuración global de Codex.
- Ambos scripts PowerShell aprobaron su análisis de sintaxis. El script de
  inicialización se ejecutó desde fuera del proyecto y creó la base y log locales
  en `.ari`, con un evento de inicio y sin información de dispositivos.
- `python -m build` generó sdist y wheel con setuptools 82.0.1. Se inspeccionó que
  el sdist incluya instrucciones, ocho skills, configuración, documentación,
  scripts, fixtures y lock, y que el wheel incluya módulos Python sin una CLI
  independiente. No se publicó ningún paquete. El wheel distribuye el núcleo;
  las skills y configuración de Codex se usan desde el repositorio o sdist.
- Se registraron versiones instaladas en `requirements-dev.lock`; los archivos
  locales de entorno, base, logs y compilación están excluidos de Git. Los módulos
  de `ari/firmware/` sí quedan incluidos en el repositorio y el wheel.

Versiones principales verificadas: Pydantic **2.14.2**, SQLAlchemy **2.1.6**, MCP
**2.3.0**, Pytest **9.2.0**, Ruff **0.17.3** y build **1.6.1**. Los logs usan UTC;
la fecha de esta entrega se expresa según la zona horaria del cliente.

## Entregables

| Grupo | Archivos y ubicación |
| --- | --- |
| Identidad | `AGENTS.md`, `ARI_IDENTITY.md` |
| Entorno | `pyproject.toml`, `requirements-dev.lock`, `.gitignore`, `.gitattributes`, `MANIFEST.in` |
| Codex | `.codex/config.toml`, ocho `.agents/skills/ari-*/SKILL.md` |
| Núcleo | `ari/core/`, `ari/security/`, `ari/knowledge/`, `ari/reporting/` |
| Contratos | `ari/device/`, `ari/bootloader/`, `ari/firmware/`, `ari/root/`, `ari/recovery/` |
| MCP | `ari/mcp/server.py`, sin conexión activa a Codex |
| Integraciones reservadas | `integrations/adb/`, `fastboot/`, `magisk/`, `kernelsu/`, `rea/` |
| Validación | `tests/`, `scripts/check.ps1`, `scripts/initialize-storage.ps1` |
| Documentación | `README.md`, `docs/architecture.md`, `docs/phases.md`, `docs/sources.md`, este registro |

## Límites de la validación original de Fase 1

No se ejecutó ADB, Fastboot ni root; no se consultó ningún dispositivo real. Las
pruebas usan datos sintéticos y mocks. Se verificó el esqueleto MCP con el SDK,
sin habilitarlo ni conectarlo a Codex. No se verificó el descubrimiento de las
skills en una nueva sesión. La presencia de herramientas Android instaladas no
prueba controladores, permisos ni compatibilidad.

Python 3.12/3.13 y Windows 10 no se probaron en otras máquinas. Los rangos de
compatibilidad del paquete no equivalen a una matriz de plataformas validada.
No se evaluaron REA ni procedimientos Magisk/KernelSU. No hay firmware validado,
imágenes preparadas ni dispositivos diagnosticados. Al cerrar aquella entrega
todavía no se había autorizado la Fase 2.

## Fase 2 — diagnóstico ADB 0.2.0

El usuario autorizó exclusivamente el adaptador de lectura, detección, inspección,
errores, mocks, documentación y sincronización con GitHub. Fecha del cliente:
31 de octubre de 2026; mismo entorno Windows/Python 3.14.6 de Fase 1.

Comprobaciones de entrega:

- Paquete reinstalado en modo editable como **0.2.0**, sin cambiar dependencias.
  Se contrastó la versión importada con los metadatos instalados y el lock existente.
- `scripts/check.ps1` aprobado: Ruff, formato, **166 pruebas** y `pip check`.
- Pruebas de parser: inventario vacío válido, errores de cabecera, duplicados,
  seriales inválidos, estados desconocidos, límites de salida y propiedades ausentes.
- Pruebas del transporte con `subprocess.run` sustituido: argumentos exactos,
  lista cerrada, serial explícito, shell desactivado, stdin cerrado, ventana oculta,
  entorno limitado y exclusión de redirección de servidor y trazas.
- Resolución de ejecutable desde ruta absoluta o PATH absoluto, rechazando wrappers,
  archivos ausentes, búsqueda implícita en CWD y entradas relativas. Ningún archivo
  de prueba se ejecuta: el supuesto adb.exe es una fixture sintética.
- Autorización y simulación predeterminadas, timeouts, errores de acceso, respuestas
  no UTF-8, códigos no cero y mensajes privados eliminados de las excepciones.
- Servicio con mocks de transporte y prueba completa atravesando el adaptador con
  proceso simulado: varias conexiones, estados no listos, ausencia de propiedades,
  SKU/ODM distintos, fechas, procedencia, snapshots e historial con enlaces.
- Desconexión, cambio de fingerprint, estado offline final y respuesta inválida
  detienen la inspección sin guardar snapshots parciales. No hay reintentos.
- Las modificaciones siguen bloqueadas incluso con autorización explícita. Los
  cuatro métodos ADB aparecen como API Python, sin registrarse como herramientas MCP.
- Las ocho skills aprobaron el validador de `skill-creator`. TOML válido, MCP
  deshabilitado y lista de dos herramientas informativas conservada. Sintaxis de
  PowerShell validada e inicialización local comprobada sin acceso automático a ADB.
- Sdist y wheel **0.2.0** construidos. Se verificó la inclusión de módulos ADB,
  pruebas, instrucciones, skills y documentación según el tipo de paquete, sin
  entrada CLI independiente. Los paquetes generados permanecen locales y excluidos.
- Revisión de diff, exclusiones y patrones de credenciales antes de publicar el
  código validado. SQLite, logs, entorno, firmware e informes permanecen locales.

Archivos nuevos principales: `ari/device/adb.py`, `errors.py`, `parsers.py`,
`inspector.py`, `integrations/adb/transport.py`, `docs/adb.md` y tres módulos de
pruebas. Se actualizaron identidad, instrucciones, skills, metadatos del catálogo,
versión, política de fase, pruebas de regresión y documentación. No cambió el
esquema SQLite ni el prompt original.

**No se ejecutó ADB real ni Fastboot, tampoco para consultar su versión.** La
verificación manual con un dispositivo queda pendiente de que el usuario solicite
un diagnóstico autorizado. La documentación de Platform-Tools no acredita el
binario ni los controladores locales. El esqueleto MCP solo se prueba con el SDK,
sin habilitarlo ni conectarlo a Codex. Al cerrar Fase 2, la Fase 3 seguía pendiente.

## Fase 3 — MCP con Codex 0.3.0

Entrega del **1 de noviembre de 2026** según la fecha del cliente. Entorno:
Windows, Python 3.14.6 y codex-cli **0.166.0-alpha.5.1**. Solo se autorizó Fase 3,
con lectura ADB, sin root ni avance a Fase 4.

La configuración local habilita el servidor STDIO y exactamente seis herramientas.
No se modifica la configuración global ni permisos del cliente. Se comprobaron
esquemas de entrada cerrados, booleanos estrictos, serial obligatorio, salida
tipada, errores sin datos privados y consentimiento no heredado entre llamadas.
Las escrituras, reinicios, desbloqueo y flasheo siguen bloqueados.

### Pruebas del SDK y del repositorio

- **201 pruebas** aprobadas con `scripts/check.ps1`, además de Ruff, formato y
  `pip check`. Conserva los casos de Fases 1/2 y añade entrada/salida MCP,
  compatibilidad de cliente SDK moderno/legacy, cuatro llamadas positivas con
  mocks, rechazo de parámetros extra y tipos incorrectos, todos los códigos ADB,
  errores inesperados, serial devuelto distinto y fallo seguro de arranque.
- Se comprobó que entradas y excepciones privadas no aparecen en resultados ni
  logs. El consentimiento se valida antes de construir el backend.
- El cliente SDK STDIO comprueba cierre por EOF con `runtime_stopped`; las pruebas
  del runtime comprueban liberación de handlers. La ejecución automatizada sigue
  bloqueando procesos reales, excepto su servidor Python local permitido.
- Ocho skills validadas, TOML analizado, seis herramientas permitidas y rutas
  comprobadas. Paquete editable, sdist y wheel 0.3.0 verificados. El lock conserva
  las versiones; AnyIO 4.15.1 ahora se declara directamente por su uso en el servidor.

### Cliente Codex real: comprobación independiente

`scripts/verify-codex-mcp.py` inicia el Codex App Server instalado y habla su
protocolo JSON-RPC. No usa `mcp.Client`, no inicia turnos del modelo y no crea chats
persistentes. El cliente MCP real de Codex es quien inicia y llama al servidor ARI.

Se observaron `runtimeStatus=connected`, serverInfo ARI 0.3.0, seis herramientas y
sus esquemas, respuestas y errores. Se ejecutaron **30 comprobaciones** en dos
sesiones efímeras: 11 con la configuración de producción y acceso a hardware
bloqueado; 19 con un servidor fixture de dispositivos sintéticos. Se incluyeron
inventario, estado seleccionado, doce propiedades, inspección, offline,
unauthorized, objetivo ausente, serial inválido/ausente, simulación y autorización
predeterminadas, consentimiento no reutilizado y rechazo de reboot. Codex rechaza
la herramienta no anunciada antes de enviarla a ARI; el rechazo directo del servidor
se comprueba por separado con el SDK.

Codex salió con código cero y se comprobó que los procesos ARI terminaron mediante
handles de espera de Windows. No se observó el finalizador Python en esas sesiones;
no se afirma cierre por EOF ni ejecución de callbacks del servidor con Codex.
El cierre se probó después de llamadas terminadas, sin hardware activo.

El informe resumido sin credenciales, seriales reales, UUID de sesiones ni rutas
privadas se conserva en `codex-verification.json`. Los logs completos y la copia
operativa del informe permanecen en `.ari`, excluidos de Git. No se comprobó una
recarga visual en esta ventana; se comprobó el cliente MCP del ejecutable instalado.

No se ejecutó ADB real, Fastboot, root ni una operación de escritura o reinicio.
La comprobación de hardware sigue pendiente de una solicitud de diagnóstico.
El esquema SQLite y el prompt original se conservan. La Fase 4 permanece pendiente.

## Mantenimiento Fase 3 — disponibilidad en un chat nuevo

Comprobación del **1 de noviembre de 2026**. Se investigó por qué un chat antiguo
no exponía ARI, aunque la prueba de App Server funcionaba.

- `config/read` confirmó la capa local de `.codex/config.toml`, proyecto confiable,
  ARI habilitado y seis herramientas permitidas. Fuera del proyecto esa entrada
  no se cargaba. El directorio del chat original sí era ARI: no se atribuye su
  problema a estar fuera de la carpeta.
- El catálogo nativo del chat original contenía cero herramientas ARI. Ese chat
  había sido creado antes de habilitar el servidor. En un chat nuevo del proyecto
  aparecieron las seis herramientas `mcp__ari__*`.
- Un error independiente impidió iniciar el primer turno del chat nuevo: su modelo
  predeterminado no era compatible con esa cuenta. El usuario eligió el modelo
  para el reintento; se aplicó solo a ese chat. No se cambió configuración global.
- El historial del chat nuevo confirmó llamadas MCP nativas completadas a
  `get_project_status`, `list_capabilities` e `inspect_device`. La inspección fue
  del único serial autorizado por el usuario, sin fallback Python, CLI ni SDK.
- La variante exacta no se inventó cuando faltó una de las observaciones SKU.
  Los resultados completos, serial y fingerprint quedaron solo en `.ari`, fuera
  de Git. El resumen público no contiene esos datos.

La conclusión comprobada es que el servidor funciona en una sesión nueva y el
catálogo del chat anterior no se actualizó. La carga anterior a la habilitación
explica de forma consistente la diferencia; no se inspeccionó el mecanismo interno
de caché. No fue necesario reinstalar herramientas ni cambiar seguridad.

Se reforzó únicamente el verificador de integración: ahora comprueba la capa
efectiva y marca explícitamente que sus resultados son del protocolo App Server,
no del catálogo nativo. **204 pruebas** aprobadas con Ruff, formato y `pip check`;
**32 comprobaciones** App Server aprobadas, sin hardware en ese comprobador. Se
añadieron tres pruebas sintéticas del alcance de configuración.

La configuración MCP, `AGENTS.md`, el servidor, las políticas de seguridad, el
ejecutor de root y el adaptador ADB no cambiaron. No se realizaron reinicios,
desbloqueos, flasheos ni escrituras de particiones. La Fase 4 sigue pendiente.

## Fase 4 — versión 0.4.0, 1 de noviembre de 2026

Solicitud explícita del usuario para desarrollar compatibilidad documental y
bootloader, sin Fastboot ni modificación Android. Se conserva el prompt maestro;
la solicitud de esta fase y el caso de investigación quedan privados en `.ari`.

### Implementado y probado

- Contratos de investigación y motor offline probados antes de registrar las nuevas
  herramientas MCP: primera ejecución de **31 pruebas** específicas aprobada.
- Validación final con `scripts/check.ps1`: **272 pruebas aprobadas**, Ruff,
  formato de 80 archivos Python y `pip check` correctos, en Python 3.14.6.
- **68 pruebas adicionales** de evidencia, identidad/variante/fingerprint,
  región/operador, kernel/GKI/KMI, ausencia de medición, estados negativos,
  contradicciones, fuentes caducadas/futuras, credenciales, referencias inválidas,
  modelos forjados y límites de planes. Se cubren entradas anidadas, extras,
  consentimiento de hardware improcedente y excepciones sin fuga al SDK/logs.
- Las seis herramientas originales conservan selección y consentimiento explícitos.
  Tres nuevas herramientas offline tienen esquemas cerrados y salida tipada.
  Las pruebas usan mocks/datos sintéticos y guardas de procesos; la investigación
  no construye transporte, consulta URL ni ejecuta textos de fuentes.
- Instalación editable, sdist y wheel **0.4.0** construidos y revisados. El paquete
  incluye los módulos nuevos y excluye `.ari`, SQLite y logs. No se cambian rangos
  ni versiones de dependencias de ejecución, esquema SQLite o lista ADB permitida.

### Cliente Codex instalado

`scripts/verify-codex-mcp.py`, con **codex-cli 0.166.0-alpha.5.1**, completó
**40 comprobaciones**: 17 con producción y 23 con fixture sintética. Verificó
configuración efectiva local, conexión, versión 0.4.0, nueve herramientas/esquemas,
las tres llamadas offline, bloqueo de extras y rechazos ADB predeterminados.
Las lecturas positivas ADB del comprobador usaron exclusivamente fixtures.
Codex y los procesos ARI terminaron; no se observó el finalizador Python con ese
cliente. No se iniciaron turnos del modelo ni chats persistentes.

El resumen público está en [phase4-verification.json](phase4-verification.json).
Esto verifica App Server; **no acredita recarga del catálogo nativo de este chat**.
La comprobación nativa anterior corresponde a 0.3.0. No se atribuyen resultados
de SDK o del comprobador al catálogo de la ventana actual.

### Caso privado y límites

Se revisaron seis fuentes primarias de TCL, AOSP, Magisk y KernelSU, documentadas
en [research.md](research.md). El motor evaluó el TCL T613P con identidad parcial y
fingerprint local de la inspección previa. Resultado: estado del bootloader
desconocido, capacidad oficial de desbloqueo no verificada, compatibilidad de
Magisk/KernelSU no confirmada y plan bloqueado, siempre `executable=false`.

Entrada, procedencia previa, informe y plan JSON permanecen en `.ari`, fuera de Git.
No se reutiliza una variante diferente ni se infiere región/operador del SKU ODM.
No se realizaron nuevas lecturas ADB, Fastboot, root, reinicios, desbloqueo,
parcheo, flasheo ni escrituras. La búsqueda y curación web las realiza Codex; el
motor no autentica URLs, editores o contenido. Fase 5 permanece pendiente.

## Fase 5 — versión 0.5.0, 1 de noviembre de 2026

Solicitud explícita de análisis estático exclusivamente; no se inicia Fase 6.
Prompt maestro conservado y solicitud de esta fase guardada en `.ari/phase5-request.md`.

### Historial nativo y verificación definitiva de once herramientas

Se creó un chat nuevo del proyecto ARI exclusivamente para comprobar las nueve
herramientas existentes, sin autorización ADB. El turno falló antes de cargar
el catálogo: el modelo predeterminado `gpt-5.5` no es compatible con esta cuenta.
Se comunicó el bloqueo y el usuario eligió expresamente `gpt-6.1-sol` para el
reintento en ese chat. No se cambió el modelo global, configuración o políticas.

El reintento observó **9/9 herramientas previas** en el catálogo nativo y completó
cinco llamadas MCP directas: `get_project_status`, `list_capabilities`,
`analyze_unlock_compatibility`, `check_root_compatibility` y `create_root_plan`.
El historial real del chat confirma los cinco eventos `mcpToolCall` completados;
no se deduce la disponibilidad de una configuración o de pruebas de SDK/App Server.

El servidor respondió **ARI 0.4.0, Fase 4**, aunque el checkout ya está en 0.5.0.
`analyze_firmware` y `verify_firmware_hash` no aparecen en ese catálogo. El chat
se creó antes de implementar Fase 5; no se investigó el mecanismo responsable de
la discrepancia en aquel reintento, que no acreditaba 0.5.0. La investigación
posterior y su resultado definitivo se registran a continuación.

La investigación sin evidencia devolvió estados desconocidos y un plan `blocked`,
`theoretical_only=true`, `executable=false`. Las cuatro herramientas ADB solo se
observaron, sin invocarlas; tampoco se consultaron firmware o archivos mediante MCP.
No se usaron clientes alternativos para sustituir herramientas ausentes.
La evidencia íntegra permanece privada en `.ari/phase5-native-session.json`; el
primer fallo se conserva por separado en `.ari/phase5-native-attempt.json`.

#### Conexión realmente nueva después de actualizar

La auditoría encontró instalación editable 0.5.0, imports en el checkout, Python
3.14.6 de `.venv` y configuración efectiva local con once herramientas. No hubo
una ruta o paquete incorrectos. El chat anterior nació a las 15:14:30 UTC, antes
de actualizar los módulos, y se reanudó a las 16:43:42 UTC. Seguían activos procesos
ARI iniciados antes de los cambios. No se inspeccionó memoria de esos procesos.

Se creó otro chat a las **17:07:08 UTC**, con un nuevo runtime observado a las
17:07:09 UTC. Su catálogo nativo contenía exactamente once herramientas y
`get_project_status` informó **0.5.0, Fase 5**. Se observaron seis eventos MCP reales:
dos de metadatos, un rechazo esperado `file_authorization_required`, dos hashes
autorizados y un análisis estático. La imagen sintética propia de 12 288 bytes
conservó su SHA-256; cabecera boot v3, identidad insuficiente, firmware bloqueado y
plan `executable=false`. El padre comprobó además el hash del fixture propio.

Esto resuelve la discrepancia por crear una conexión posterior a la actualización,
sin reinstalar ni cambiar código, rutas, permisos o modelo global. Se repitieron
**357 pruebas**, Ruff, formato, `pip check` y **49 casos App Server** independientes.
Evidencia nativa privada en `.ari/native-050-fresh-verification.json`; auditoría
privada en `.ari/mcp-load-audit.json`. Resumen público y causa demostrada en
[mcp-load-diagnosis.md](mcp-load-diagnosis.md) y
[mcp-load-verification.json](mcp-load-verification.json).

### Implementación y pruebas

- Núcleo de lectura estática, contratos y lectores probados antes de registrar
  MCP: primera ejecución positiva de **53 pruebas** específicas.
- Validación final con `scripts/check.ps1`: **357 pruebas aprobadas** en Python
  3.14.6, Ruff, formato y `pip check` correctos. **85 pruebas nuevas** cubren
  boot v0–4, init_boot, vendor_boot v3–4, recovery, AVB/footer, identidad exacta,
  hashes, A/B, límites, traversal/ADS/UNC, aliases, hardlinks, reparse points,
  conflictos, formatos corruptos y errores MCP sin fugas.
- Se probó con archivos sintéticos Windows que los handles abiertos impiden
  escribir el original y renombrar su directorio padre. No requiere privilegios
  especiales, herramientas Android ni contenido de firmware real.
- Instalación editable, sdist y wheel **0.5.0** construidos. Las dependencias de
  ejecución y su lock, SQLite, transporte ADB y whitelist de propiedades no cambian.
- Nueve herramientas conservadas y dos nuevas: `analyze_firmware` y
  `verify_firmware_hash`, con entradas anidadas cerradas, rutas relativas autorizadas,
  consentimiento por llamada, errores estáticos y trabajo serializado fuera del
  bucle del protocolo. No hay parámetros MCP de raíz, backend, shell o recursos.

### SDK y cliente real: pruebas independientes

Las pruebas SDK en memoria/legacy/STDIO no acreditan catálogo nativo. El script
`scripts/verify-codex-mcp.py` comprobó además el cliente **Codex App Server
0.166.0-alpha.5.1**, sin turnos del modelo ni chats persistentes: **49 comprobaciones**,
20 con configuración de producción y 29 con fixture sintética explícita.
Se observaron conexión, ARI 0.5.0, once herramientas/esquemas, rechazos por defecto,
lectura/hash/análisis de imágenes sintéticas, plan bloqueado y original preservado.
Las lecturas ADB positivas pertenecen exclusivamente al fixture.

Codex y los procesos ARI terminaron; no se observó el finalizador Python con ese
cliente. Resumen público sin identificadores ni datos reales en
[phase5-verification.json](phase5-verification.json). El verificador mantuvo
`native_chat_tools_verified=false` porque ese registro solo acredita App Server.
El campo `native_session_history` conserva el reintento con runtime 0.4.0;
`native_session` registra la comprobación nativa definitiva de 0.5.0. La prueba
App Server no se presenta como prueba del catálogo del chat.

### Límites y privacidad

Solo ZIP acotado, metadatos enumerados y cabeceras Android/AVB; no extracción de
payload/ext4, TAR o ZIP64, ni ramdisks ejecutados. El presupuesto de tiempo es
cooperativo, no un sandbox duro. Fuentes declaradas e índices leídos no autentican
OEM/AVB ni establecen antirollback: los informes permanecen bloqueados y los planes
siempre `executable=false`. Detalles en [firmware.md](firmware.md).

No se descargó ni analizó firmware de un equipo real. No se realizó ADB real,
Fastboot, desbloqueo, root, reinicio, parcheo, flasheo, escritura de particiones o
modificación de imágenes del dispositivo. Los datos privados anteriores y las
evidencias locales permanecen fuera de Git y de los paquetes. Fase 6 pendiente.

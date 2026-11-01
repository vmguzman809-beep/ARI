# Registro de validación — Fases 1 y 2

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

## Límites de la validación

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
sin habilitarlo ni conectarlo a Codex. La Fase 3 continúa pendiente.

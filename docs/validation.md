# Validación de Fase 1

Entorno comprobado: Windows, Python **3.14.6**, Codex
**0.166.0-alpha.5.1**, PowerShell. Fecha del cliente: **31 de octubre de 2026**.

La carpeta inicial solo contenía `ARI_V1_Prompt_Maestro_Codex.txt`. Se conservó
ese archivo y se inicializó Git local, sin commits, remotos ni publicación.

## Comprobaciones ejecutadas

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
imágenes preparadas, dispositivos diagnosticados ni autorización para Fase 2.

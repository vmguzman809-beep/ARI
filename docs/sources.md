# Fuentes técnicas consultadas

Verificación para este desarrollo: **31 de octubre de 2026**, fecha del cliente
en America/Santo_Domingo. Las páginas pueden cambiar; las versiones instaladas
quedan registradas en `requirements-dev.lock` y `validation.md`.

| Decisión | Fuente primaria | Uso en ARI |
| --- | --- | --- |
| Skills locales | [OpenAI: Build skills](https://learn.chatgpt.com/docs/build-skills) | Carpetas `.agents/skills` y frontmatter |
| MCP en Codex | [OpenAI: MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) | Configuración local STDIO; habilitada en Fase 3 |
| Cliente real y protocolo | [OpenAI: Codex App Server](https://learn.chatgpt.com/docs/app-server) | Sesiones efímeras, descubrimiento y llamadas mediante el cliente MCP instalado |
| Claves de configuración | [OpenAI: Configuration Reference](https://learn.chatgpt.com/docs/config-file/config-reference) | command, args, cwd, env y enabled_tools |
| SDK MCP actual | [SDK Python oficial](https://py.sdk.modelcontextprotocol.io/) | API `MCPServer` de la línea estable V2 |
| Versión instalada de MCP | [PyPI mcp 2.3.0](https://pypi.org/project/mcp/2.3.0/) | Publicación y requisitos de esa versión |
| Pruebas MCP | [SDK: Testing](https://py.sdk.modelcontextprotocol.io/get-started/testing/) | Cliente en memoria |
| Transporte MCP | [SDK: Client transports](https://py.sdk.modelcontextprotocol.io/client/transports/) | Cliente STDIO local aislado |
| Validación | [Pydantic: Models](https://pydantic.dev/docs/validation/latest/concepts/models/) | Contratos y rechazo de extras |
| Persistencia | [SQLAlchemy: ORM Quick Start](https://docs.sqlalchemy.org/en/21/orm/quickstart.html) | Modelos declarativos y transacciones |
| ADB y selección | [Android Developers: adb](https://developer.android.com/tools/adb) | Inventario, estados y selección explícita |
| Sintaxis exacta ADB | [AOSP: adb.1.md](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/docs/user/adb.1.md) | devices -l, -s, -H/-P, get-state y shell -T |
| Lectura de propiedades | [AOSP: getprop.cpp](https://android.googlesource.com/platform/system/core/+/refs/heads/main/toolbox/getprop.cpp) | Consulta de una propiedad sin volcado completo |
| SKU e identidad reportada | [AOSP: Build.java](https://android.googlesource.com/platform/frameworks/base/+/main/core/java/android/os/Build.java) | Diferencia entre hardware SKU y ODM SKU; valores desconocidos |
| Herramienta para Windows | [Platform-Tools: release notes](https://developer.android.com/tools/releases/platform-tools) | Distribución oficial; sin instalar ni ejecutar binarios en las pruebas |

Las versiones de dependencias se contrastaron además con los metadatos JSON
oficiales de PyPI. Se comprobó la instalación real en Python 3.14.6; esto no prueba
por sí solo todas las versiones o instalaciones Windows admitidas por los rangos.

No se investigaron procedimientos de root ni compatibilidad de dispositivos en
Fases 1 a 3. En Fase 2 se consultó documentación ADB y código AOSP; la combinación
conservadora del par SKU como variante es una decisión de ARI, no una garantía
del fabricante sobre firmware. Las notas de Platform-Tools consultadas incluyen
37.0.1; no se ejecutó el binario local ni se comprobó su versión real.
[REA](https://github.com/morluto/rea) se registra como candidato opcional:
su API/licencia/compatibilidad todavía no han sido evaluadas para integración.

Para Fase 3 se consultó documentación oficial de OpenAI y el código del SDK MCP
2.3.0 instalado; se generaron esquemas del protocolo desde Codex 0.166.0-alpha.5.1.
La comprobación real y la revisión final se completan en la entrega del
**1 de noviembre de 2026**, fecha del cliente. Las marcas UTC se conservan en el
informe técnico, independientemente de la fecha de presentación.

La revisión posterior de alcance y recarga consultó también
[Config basics de OpenAI](https://learn.chatgpt.com/docs/config-file/config-basic).
Se contrastó con `config/read` del cliente instalado, el catálogo del chat antiguo
y un turno nuevo con herramientas MCP nativas. El resumen público de esa prueba
está en `native-session-verification.json`; las observaciones de hardware no se publican.

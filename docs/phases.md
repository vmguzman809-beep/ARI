# Fases y criterios de aceptación

Fases 1 a 4 implementadas por solicitudes expresas del usuario. La Fase 4 añade
investigación documental offline; mantiene lectura ADB y prohíbe modificaciones.
Aprobar las pruebas no autoriza otra fase.

## Fase 1 — cimientos (completada)

- Identidad, `AGENTS.md`, README Windows y ocho skills locales válidas.
- Paquete instalable en entorno local compatible, sin GUI ni CLI independiente.
- Dominios e integraciones separados; ninguna operación Android activa.
- SQLite con fuentes fechadas, historial, transacciones y separación por variante
  y compilación exactas, validado tras cerrar y reabrir.
- Registros locales sin datos de dispositivo ni contaminación de STDIO.
- Esqueleto MCP tipado con catálogo honesto y configuración deshabilitada.
- Pruebas sintéticas de seguridad, validación, almacenamiento y protocolo MCP.
- Documentación de decisiones, limitaciones y comprobaciones realmente ejecutadas.

El registro concreto de ejecución está en `validation.md`.

## Fase 2 — Device Inspector (implementada; validación con mocks)

Alcance autorizado y entregado:

1. Definir transporte ADB acotado, timeout, errores y resolución explícita de la
   herramienta instalada; nunca shell ni un argumento de comando libre.
2. Implementar `devices -l` y un conjunto mínimo de propiedades de lectura con
   selección explícita del serial. Tratar cero, uno, varios, offline y unauthorized.
3. Conservar datos faltantes, fabricante/modelo/variante/fingerprint, arquitectura
   y Android, con procedencia y fecha. No inferir compatibilidad de root.
4. Probar parsers, errores, selección y timeouts mediante mocks de transporte;
   confirmar que la lista permitida impide escrituras y reinicios.
5. Solo cuando el usuario solicite diagnóstico de un dispositivo autorizado,
   realizar una comprobación manual separada y registrar lo observado. Las pruebas
   automatizadas siguen sin dispositivos reales.

Aceptación: detección e inspección exclusivamente de lectura, errores reproducibles,
objetivo inequívoco y documentación de una verificación real si pudo realizarse.
Si no hay dispositivo autorizado disponible, reportar ese límite.

Implementación: `integrations/adb/transport.py`, contratos tipados en
`ari/device/adb.py`, parsers y `AdbDeviceInspector`. Se cubren los cuatro métodos
Python de diagnóstico, con selección explícita, errores y persistencia opcional.
Consulta `adb.md` para el contrato y los límites de identidad. No se ejecutó ADB
real: esta tarea autoriza desarrollo, sin solicitar diagnóstico de hardware.
La comprobación manual queda pendiente de una solicitud expresa de diagnóstico.

## Fase 3 — conexión MCP con Codex (implementada y verificada)

Integrar las herramientas implementadas con sus esquemas, revisar rutas locales,
habilitar el servidor dentro del alcance de esa tarea y verificar inicio, listado,
llamada, errores y cierre desde el cliente Codex instalado. Distinguir prueba de
SDK local de conexión con el cliente real. No añadir modificación Android.

Se habilita el servidor STDIO local, con seis herramientas y esquemas cerrados.
La verificación real usa el cliente MCP del Codex App Server instalado:
descubrimiento, llamadas, errores, serial explícito y terminación del proceso.
Producción se prueba sin hardware; las lecturas positivas usan un servidor fixture
explícito en otra sesión efímera de verificación. No son resultados de Android real.
La comprobación no usa un cliente SDK ni inicia turnos del modelo. El cierre de
Codex termina los procesos ARI en Windows, sin observar el finalizador Python;
el cierre por EOF con finalización se prueba separadamente mediante el SDK.
Detalles reproducibles y límites en `mcp.md` y `validation.md`. En esa entrega
Fase 4 permanecía pendiente; su autorización posterior se registra a continuación.

## Fase 4 — compatibilidad y bootloader (0.4.0)

Investigar fuentes oficiales por variante, Magisk y KernelSU; fechar verificaciones,
separar certeza, restricciones OEM/operador y datos desconocidos. Implementar solo
diagnósticos permitidos. Un plan requiere evidencia y condiciones de parada.

Implementado: modelos cerrados de fuente, fecha, confianza y estado confirmado,
probable, no verificado o desconocido; análisis offline de estado de bootloader,
posibilidad oficial de desbloqueo, permiso OEM, región y operador por separado;
evaluación Magisk/KernelSU, informe trazable y plan teórico siempre no ejecutable.
Se conservan las seis herramientas MCP y se añaden tres de evaluación documental.

Aceptación: pruebas sintéticas de identidad exacta, evidencia ausente/contradictoria/
caducada, región/operador y kernel/GKI/KMI, rechazo de parámetros de ejecución,
aislamiento de hardware, validación completa y verificación con cliente Codex real.
La revisión de fuentes la realiza Codex; no se implementa un rastreador web ni
un verificador automático del contenido de las URL. Véase `research.md`.

Caso investigado: TCL T613P, Android 14, con fingerprint local conocido y variante
desconocida. La documentación general no demuestra equivalencia de variantes,
desbloqueo oficial ni compatibilidad de root. Informe y observaciones privadas en
`.ari`, excluidos del paquete y de Git. No se autoriza una nueva lectura Android.

## Fase 5 — firmware y preparación (pendiente)

Validar procedencia, hash independiente, identidad exacta y antirollback. Inspeccionar
boot/init_boot/recovery de forma segura. Preservar originales y verificar cualquier
imagen preparada. Evaluar herramientas opcionales antes de integrarlas. No flashear.

## Fase 6 — ejecución y recuperación (pendiente)

Implementar interfaces de modificación separadas y autorizaciones humanas
específicas ligadas al dispositivo, acción e imagen/hash. Verificar prerrequisitos
inmediatamente antes de actuar; detenerse ante discrepancias. Probar con mocks,
sin escrituras automáticas a equipos reales. Verificar resultados y ofrecer
recuperación sustentada por evidencia, sin evasión de controles de acceso.

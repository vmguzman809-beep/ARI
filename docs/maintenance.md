# Android Maintenance Intelligence — Etapa 1 offline

Implementación propia autorizada el 2026-11-01. Continúa dentro del alcance
offline de Fase 5; Fase 6 pendiente. No registra herramientas MCP, no amplía ADB,
no añade dependencias y no adquiere datos ni modifica Android.

## API y contratos

El dominio `ari/maintenance/` contiene modelos Pydantic cerrados, estrictos,
congelados y con colecciones tuple, independientes de runtime, SQLite y transportes.
Los modelos se revalidan al entrar en los servicios, incluso si el llamador usó
`model_construct` o `model_copy` para evitar la validación inicial.

| Modelo | Contrato implementado |
| --- | --- |
| PackageSnapshot | Exportación versionada, fecha, procedencia, identidad, perfil, cobertura, paquetes, evidencia y limitaciones. |
| DeviceIdentityRef | Referencia UUID local; fabricante, modelo, hardware SKU, ODM SKU, variante, build, fingerprint, región y operador separados. Null permanece desconocido. |
| UserScope | Usuario explícito, tipo de perfil y padre obligatorio para trabajo; solo ámbito por usuario. Sin default de usuario 0. |
| PackageObservation | Instalación y estado explícito `default`, `enabled`, `disabled`, `disabled_user`, `disabled_until_used`, `unknown`; habilitación efectiva, hidden, suspended y stopped separados; funciones y dependencias con evidencia. |
| EvidenceObservation | Sujeto, afirmación, valor, estado conocido/desconocido/contradictorio/bloqueado, confianza, fuente y fecha. |
| PackageRiskAssessment | Protección/bloqueo/revisión, severidad conservadora, confianza en los datos declarados, razones, evidencia y revisión de política. Nunca una decisión de permitir cambios. |
| Baseline | Snapshot completo anidado e inmutable por la API, fecha de creación, revisión y SHA-256 del contenido canónico. |
| DriftReport | Comparabilidad, estado, razones y diferencias por campo; sin datos de identidad completos. |
| MaintenanceSimulation | Solo contrato de revisión offline con executable=false y requisitos pendientes. No incluye intenciones ni genera planes o comandos. |
| RecoveryEvidenceReview | Solo contrato de evidencia faltante; verificación funcional siempre requerida. No ejecuta recuperación ni garantiza reversión. |

Los modelos permiten conservar evidencia parcial. La creación de baseline y la
comparación exigen condiciones adicionales; parsear un documento no demuestra
que sea apto para comparar o restaurar.

`coverage="complete"` es una declaración de la fuente. ARI comprueba coherencia
estructural, referencias y campos necesarios, pero no demuestra que el inventario
incluya todos los paquetes ni que la fuente sea auténtica. Una fuente puede omitir
entradas y aun así declararse completa. Lo mismo se aplica a declaraciones como
`functions_complete`: no constituyen descubrimiento independiente. Parsear, crear
una baseline o devolver `comparable=true` no autentica ni acredita exhaustividad.

### Parser

`parse_snapshot(data: bytes)` y `parse_baseline(data: bytes)` reciben el contenido
de archivos JSON locales que el llamador ya leyó. El parser no recibe rutas, no
abre archivos y no visita URL. La lectura/confinamiento de archivos y permisos
por llamada de una futura integración quedan pendientes. No se añade un lector
de archivos al servidor ni una CLI.

- UTF-8 estricto, objeto raíz, versión exacta y campos extra prohibidos en todos
  los niveles. Rechaza claves duplicadas, incluso anidadas, BOM, JSON malformado,
  constantes no finitas y tipos coercibles como booleanos expresados con enteros.
- Máximo 5 MiB por entrada, profundidad 16, 10 000 paquetes, 20 000 evidencias,
  128 dependencias y 64 referencias de evidencia por paquete. Texto acotado;
  identificadores ASCII completos hasta 255 caracteres, sin comentarios/tokens
  adicionales. Los paquetes duplicados no se fusionan.
- `MAX_SECONDS=5.0` es un umbral de tiempo transcurrido detectado al terminar el
  procesamiento válido, antes de devolver el resultado. Si se supera, se rechaza
  el resultado con `limit_exceeded`; no se interrumpe el procesamiento en curso.
  No hay temporizador, cancelación ni interrupción garantizada a los cinco segundos.
  Los errores de validación pueden rechazarse antes de esa comprobación final.
  No es un límite duro de CPU ni un sandbox; bytes y profundidad acotan el trabajo.
- Procedencia única del export por snapshot; evidencia debe referirse a esa fuente
  y al sujeto correcto. Fechas con zona y coherencia temporal, sin fechas futuras.
- Fallos de las API públicas mediante `MaintenanceError` con mensaje fijo y código
  estático (`invalid_artifact`, `limit_exceeded`, `invalid_model`,
  `baseline_incomplete`, `inventory_empty`). No se propagan entradas ni ubicaciones
  de validación. La política rechaza inventarios vacíos con error, sin devolver una
  lista vacía que pudiera confundirse con ausencia de riesgos.

La serialización explícita contiene evidencia privada. No imprimirla ni enviarla
a logs o Git. Repr/str de modelos omiten contenido; el núcleo no registra ni emite
salidas. Las excepciones Pydantic de constructores directos siguen siendo datos
internos: no publicar `errors()` ni serializaciones de validación. Usar el parser
y las funciones de servicio como frontera para artefactos no confiables.

### Política

`assess_package_risks(snapshot)` aplica `phone-conservative-v1`. Protege funciones
críticas declaradas con evidencia (telefonía, IMS, emergencias, SIM/eSIM, SMS,
permisos, HOME, SystemUI, IME, conectividad, administración y otras) y sus
dependencias transitivas, incluso ciclos. Añade indicios conservadores por nombre
escritos para ARI. No importa listas TV y no declara completo un catálogo por esos
indicios. El nombre no prueba funcionalidad ni prescindibilidad.
Las listas son orientativas y no exhaustivas: no figurar en ellas nunca habilita
una modificación, incluso cuando los datos declarados estén completos.

Dependencias ausentes/no observadas, clasificación incompleta, origen desconocido,
datos contradictorios, inventario parcial/vacío, limitaciones o identidad/perfil
incompletos bloquean la evaluación favorable. Una clasificación crítica conserva
`protected` aunque haya incertidumbre. La confianza es sobre el contenido
declarado, no autenticación ni demostración funcional. El mejor resultado de un
paquete opcional es `review_required`, sin autorización ni riesgo bajo inferido.
Con incertidumbre, un paquete sigue `protected` si hay un indicio crítico y, en
caso contrario, queda `blocked`. Ninguno de los resultados permite modificarlo;
`review_required` tampoco es permiso. El módulo no tiene un ejecutor.

### Baseline y comparación

`create_baseline(snapshot)` rechaza incertidumbres críticas. `snapshot_digest`
revalida el snapshot y calcula SHA-256 de JSON con claves ordenadas, separadores
fijos y escapes ASCII. El orden de las colecciones forma parte del contenido;
no se reordenan observaciones ni se normalizan identidades. El digest incluye
identidad, perfil, fechas y evidencia del snapshot, no el sobre exterior baseline.

`parse_baseline` comprueba estructura y digest anidado. SHA-256 detecta alteración
frente al digest almacenado; quien sustituya contenido y digest puede falsificarlos.
No es firma, attestation, copia de datos de apps ni almacenamiento forense inmutable.
No se implementa escritura, journal, ACL, bloqueo entre procesos o migración SQLite.

`compare_snapshots(baseline, current)` exige identidad exacta completa (incluidos
UUID local, ambos SKU, variante, build/fingerprint, región y operador), mismo
usuario/perfil, cronología y evidencia suficientemente completa en ambos lados.
La ausencia de baseline, corrupción o incompatibilidad devuelve bloqueo sin
diferencias. No comparar dos null como coincidencia de identidad. El operador
ausente se conserva como null, nunca se completa como libre de operador.

La identidad incompleta conserva `incomplete_identity` y añade códigos por campo,
por ejemplo `identity_hardware_sku_missing`, `identity_odm_sku_missing` o
`identity_operator_missing`. Solo se exponen nombres de campos, sin valores ni
identificadores. La mejora de diagnóstico no cambia la exigencia de coincidencia
exacta ni permite comparar dos identidades que compartan las mismas ausencias.

Dos afirmaciones conocidas con distinto valor para el mismo sujeto/claim se
consideran contradicción. Las contradicciones se conservan para informar y bloquean
la comparación. Conflictos intrínsecos entre habilitación explícita y efectiva en
observaciones declaradas conocidas se rechazan al validar.

Cuando es comparable, se detectan cambios de estado, versión, origen, clasificación
y dependencias; las referencias de evidencia renovadas no son por sí solas deriva
de paquete. `not_observed_before` significa que la entrada no se observó en la
referencia anterior; no demuestra instalación. `not_observed_after` significa que
no se observó en el snapshot posterior; no demuestra desinstalación. Ni la cobertura
declarada completa ni un cambio del campo `installed` convierten una diferencia en
un evento de instalación/desinstalación verificado. No se adquieren pruebas de esos
eventos ni existe un presentador que los traduzca en operaciones verificadas.
`known` y cero diferencias significan igualdad de los campos declarados comparados,
no éxito de una operación, dispositivo sano ni recuperación verificada. Los campos
opcionales de versión pueden seguir siendo null; no se afirma su igualdad real.

## Cobertura de riesgos de la auditoría

Referencia documental privada original de CleanYourTV, commit
`6e8615eb0be0e843ceeebedae246d69f3e0a88d7`; sin reutilización de código ni ejecución.

| Riesgos | Tratamiento en Etapa 1 | Pendiente |
| --- | --- | --- |
| R01, R09 | Política móvil, providers sin excepciones TV, ámbito de perfil explícito. | Catálogo móvil y observaciones reales autorizadas; no disponibles ahora. |
| R02, R04, R17 | Sin transporte, shell, entorno de overrides ni interpretación de instrucciones. | Mantener fronteras si se diseña integración futura. |
| R03, R05 | Parcial/vacío/desconocido bloquea; no equivale a “sin cambios”. | Comprobación funcional no implementada. |
| R06, R07 | Sin baseline no hay comparación; recuperación solo contrato con verificación pendiente. | Sin restauración ni backup de datos de apps. |
| R08, R10 | Identidad/perfil exactos, baseline congelada con digest validado y epoch nuevo. | Persistencia protegida, autenticación, journal y ACL fuera de alcance. |
| R11 | Tipos estrictos, límites, duplicados y campos extra rechazados. | Confinamiento de lectura de archivos en otra etapa. |
| R12 | Mensajes públicos fijos, repr sin contenido, sin logs ni salida del núcleo. | Protección de archivos privados corresponde al llamador. |
| R13 | Ninguna modificación Android ni transacción de escritura; no hay efectos parciales remotos. | Ejecución/journal/recuperación siguen pendientes de fase y autorización. |
| R14 | Build, variante y operador exactos; contradicciones bloquean. | Política de caducidad y fuentes múltiples no implementada. |
| R15, R16 | Código propio, sin dependencias nuevas ni sincronización de terceros; tests sintéticos. | Revisión futura de política y del catálogo, sin importar main automáticamente. |
| R18 | Dominio aislado de root/AVB/firmware; ninguna promoción de compatibilidad. | Fase 6 pendiente. |

## Validación y estado pendiente

Fixtures exclusivamente ficticios, sin datos privados ni ejemplos de TV trasladados
a teléfonos. Tests de aislamiento bloquean procesos, sockets y apertura de archivos
durante las funciones puras. Se inspeccionan imports del dominio y se comprueba que
el catálogo MCP sigue con once herramientas y solicitudes de paquetes no pertenecen
al transporte ADB. Resultados de regresión en [validation.md](validation.md).

Pendientes: adquisición de paquetes, lector confinado de archivos para servidor,
MCP de mantenimiento, fuentes múltiples/caducidad, persistencia y cualquier función
de simulación operativa o recuperación. No se implementan planes ejecutables, root,
ADB/Fastboot nuevos, scripts externos, launcher ni modificaciones. No se avanza
a Etapa 2 ni Fase 6 con esta entrega.

# Investigación de compatibilidad — Fase 4, versión 0.4.0

El motor es una biblioteca reutilizable de evaluación offline. Codex consulta
fuentes primarias, registra afirmaciones verificables y entrega un `ResearchInput`.
No hay descargador, comandos de dispositivo, selección de backend ni búsquedas
de red dentro del paquete. No se inicia Fase 5.

## Contratos y criterios

- `ResearchSource`: URL HTTP(S) sin credenciales, título, editor, tipo, fecha con
  zona horaria y notas. El tipo es declarado por el investigador, no autenticado.
- `ResearchEvidence`: UUID, tema, hallazgo enumerado por tema, afirmación, fecha,
  fuentes, confianza y estado `confirmed`, `probable`, `unverified` o `unknown`.
  Confirmado/probable requieren fuente y confianza concordante. No verificado usa
  confianza desconocida. Una fuente referenciada debe existir en el conjunto.
- `ResearchTarget`: identidad, región, operador, versión de kernel, GKI y KMI;
  ausencias permanecen `None`. Un equipo sin operador debe documentarse con una
  etiqueta explícita como `unbranded`, nunca deducirse de un campo ausente.
- La reutilización exige fabricante/modelo/variante/fingerprint exactos, sin
  equivalencias aproximadas. Las discrepancias adicionales de Android/ABI tampoco
  se ignoran. Evidencia general o de modelo aporta contexto, no compatibilidad.
- Para desbloqueo/restricciones/métodos se exige contexto regional y de operador
  coincidente. KernelSU exige además kernel/GKI/KMI coincidentes; Android 14 y
  arm64 no bastan. Un GKI falso no prueba por sí solo incompatibilidad: una vía
  específica no GKI requeriría evidencia exacta del proyecto/fabricante.
- Fuentes y afirmaciones requieren verificación/observación dentro de 180 días;
  revisar una URL no renueva una observación antigua. Se rechazan fechas futuras. Es una
  política conservadora de vigencia de ARI, no una regla del fabricante.
- Estado del bootloader y permiso OEM requieren observación específica aportada;
  no se infieren de un manual, del modelo ni de los valores ADB de Fase 3.
- Documentación de fabricante sustenta vía oficial/restricciones; proyecto o
  fabricante sustenta compatibilidad. Evidencia comunitaria sola no confirma.
- Conflictos aplicables bloquean conclusiones, sin elegir la afirmación favorable.
  Evidencia probable/no verificada nunca se promueve a un valor confirmado.

Los informes conservan evidencia, fuentes, exclusiones y razones. Fuentes excluidas
no se convierten en coincidencias. El motor no verifica contenido, firma, propiedad
de dominios ni veracidad de las etiquetas de editor: la revisión humana/Codex sigue
siendo necesaria. Los resultados tampoco son attestation del dispositivo.

## Informes y planificación

`analyze_unlock_compatibility` separa `locked/unlocked/unknown` de
`documented/unavailable/unverified`, permiso OEM y restricciones. Una posibilidad
oficial no significa que el bootloader esté desbloqueado. Ausencia de documentación
no significa que el fabricante haya prohibido desbloquear.

`check_root_compatibility` conserva conclusiones Magisk y KernelSU por separado,
bloqueos y limitaciones. Una confirmación positiva no elude prerrequisitos
desconocidos. No comprueba firmware, root instalado ni imágenes.

`create_root_plan` genera un documento teórico con requisitos, riesgos y paradas;
`theoretical_only=true` y `executable=false` son invariantes. Los textos de las
fuentes se conservan como evidencia y nunca se insertan en instrucciones operativas.
Firmware original, hashes independientes, partición/slots, antirollback, respaldos,
recuperación y consentimiento específico quedan como requisitos futuros. No hay
pasos de desbloqueo, root, reinicio, parcheo, flasheo o escritura.

## Revisión pública del caso TCL T613P

Fuentes revisadas el **1 de noviembre de 2026**, America/Santo_Domingo:

| Fuente primaria | Hallazgo y alcance |
| --- | --- |
| [Manual TCL T613P](https://support-downloads.tcl.com/file/TCTDocument/User%20manual/01BTMKY53AFIRSZ27SJRAKBYS5CGIORDAS/Dragonfly%20GL_T613P_UM_EN_V0.1_20240329.pdf) | Identifica T613P y Android 14; advierte diferencias por software/operador. No demuestra variante comercial ni una política concreta de desbloqueo. |
| [Soporte TCL 50 5G](https://www.tcl.com/uk/en/support-mobile/model/tcl-50-5g) | Catálogo público regional. El índice ofrece documentos T613P, T613P1 y T613K; no demuestra equivalencia. El contenido dinámico puede no mostrarse en el visor. |
| [AOSP: bloqueo y desbloqueo](https://source.android.com/docs/core/architecture/bootloader/locking_unlocking) | Separa estado y capacidad OEM; describe confirmación física y borrado de datos. Es un contrato de plataforma, no un procedimiento autorizado por TCL para esta variante. |
| [Magisk: instalación](https://topjohnwu.github.io/Magisk/install.html) | Exige bootloader desbloqueado y distinguir imagen/ramdisk correctos. Requisitos generales, sin confirmación para esta compilación. |
| [KernelSU: FAQ](https://kernelsu.org/guide/faq.html) | Bootloader desbloqueado, soporte oficial GKI 5.10+; las vías no GKI requieren integración específica. Android no sustituye al kernel. |
| [KernelSU: instalación](https://kernelsu.org/guide/installation.html) | Importan KMI y nivel de parche/antirollback. No acredita los del equipo ni autoriza pruebas de arranque. |

Se buscaron `site.tcl.com T613P bootloader unlock`, `site.tcl.com bootloader unlock`
y documentación regional/operador del modelo. No se verificó un procedimiento
oficial aplicable a su variante exacta en las fuentes revisadas. Esa búsqueda no es
exhaustiva y **no prueba imposibilidad de desbloqueo**. No se usaron procedimientos
de otros TCL ni herramientas comunitarias de evasión para cubrir lo desconocido.

La variante sigue desconocida; el fingerprint observado solo se conserva localmente.
Región y operador no se deducen del sufijo de producto o del SKU ODM. Estado del
bootloader, permiso OEM, restricciones específicas, kernel, GKI y KMI no se midieron.
El resultado es compatibilidad Magisk/KernelSU **no confirmada**, posibilidad de
desbloqueo **no verificada** y plan **bloqueado**. No se declara el T613P rooteable.

La entrada, informe, plan y solicitud original están en `.ari/phase4-*`, fuera de
Git y de los paquetes. Se reutiliza la observación privada anterior como contexto,
sin nuevas llamadas ADB y sin registrar identificadores ni propiedades en logs.

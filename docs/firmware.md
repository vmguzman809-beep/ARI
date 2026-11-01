# Firmware estático — ARI 0.5.0

`StaticFirmwareAnalyzer` es una biblioteca de lectura estática: interpreta datos,
calcula SHA-256 y devuelve contratos tipados. No descarga, inicia procesos, ejecuta
contenido, extrae a disco ni modifica imágenes. Fase 6 permanece pendiente.

## Autorización y rutas

Las herramientas reciben un objeto cerrado `request`, con `artifact` relativo y
`authorized=false` por defecto. El booleano es estricto y por llamada; no se hereda
de ADB u otra solicitud. El servidor fija la raíz a `Settings.data_dir / firmware`,
normalmente `.ari/firmware`. No crea esa carpeta ni acepta raíces elegidas por MCP.
El usuario debe depositar allí sus originales y solicitar expresamente el análisis.
Este desarrollo solo usa archivos sintéticos.

Los segmentos admiten ASCII, números, espacios internos, punto, guion y guion bajo,
separados por `/`, hasta 240 caracteres. Se rechazan rutas absolutas/UNC, traversal,
segmentos vacíos, barras inversas, ADS, nombres reservados Windows y controles.
Symlinks, junctions/reparse points, hardlinks y archivos especiales están prohibidos.
No existen parámetros de shell, comandos, ejecutables, backends o límites de recursos.

Se comprueba el destino final del handle antes de leer datos. Windows mantiene
handles de archivo y padres sin compartir escritura/eliminación para impedir
redirecciones. Se comprueban estadísticas y SHA-256 en dos pasadas. Linux añade
`/proc/self/fd` y apertura no bloqueante/no-follow; ese soporte no se validó aquí.
Otras plataformas fallan de forma cerrada. No se garantiza protección frente a
un administrador malicioso o almacenamiento dañado.

## Formatos y datos

| Entrada | Lectura implementada |
| --- | --- |
| ZIP STORED/DEFLATE no cifrado | Directorio validado antes de `ZipFile`; nombres, enlaces, duplicados, tamaños y ratios; solo miembros enumerados se descomprimen a memoria. |
| `ANDROID!` v0–4 | Cabeceras boot/recovery, páginas y secciones, DTBO/DTB v1–2, Android/mes de parche y tamaño de firma v4. |
| `init_boot.img` | Cabecera boot v4, incluido kernel vacío con ramdisk. |
| `VNDRBOOT` v3–4 | DTB, tamaños, tabla de ramdisks v4, rangos y bootconfig; no interpreta ramdisks. |
| `AVB0` y footer `AVBf` | Bloques/descriptores acotados, algoritmo, flags, hash de clave pública e índices/location rollback declarados; no verifica firmas. |

Se leen propiedades de `build.prop`, `system/build.prop`, `system/system/build.prop`,
`vendor/build.prop`, `product/build.prop`, `META-INF/com/android/metadata` textual
y `META/misc_info.txt`, incluidos nombres equivalentes en mayúsculas. Cada propiedad
conserva su miembro de procedencia. Los conflictos se conservan como bloqueos.

Fabricante, modelo, variante, fingerprint, Android y build ID se comparan por
separado con el objetivo. La variante exige ambos SKU, igual que Device Inspector.
No se deduce identidad de nombres, codenames, fingerprint o un SKU aislado. Una
imagen suelta normalmente carece de identidad suficiente. Conflictos entre versión
Android de imagen y metadatos también bloquean correspondencia.

`ab_update`, `ro.build.ab_update` y `ota-type` son declaraciones del paquete.
Los sufijos `_a`/`_b` son pistas: no prueban A/B ni el slot activo.
No se soportan TAR, ZIP64, cifrado, BZIP/LZMA/Zstandard, sparse/ext4, `super.img`,
extracción de `payload.bin`, archivos anidados o descompresión de ramdisks. Los
miembros no enumerados se cuentan como no inspeccionados; no se validan todos
sus contenidos. Un formato directo desconocido se rechaza.

## Límites

- Original: 2 GiB; SHA-256 en bloques de 1 MiB, dos pasadas.
- Imagen a memoria: 64 MiB; metadatos: 64 KiB y 2048 líneas.
- ZIP: 128 entradas, directorio central de 1 MiB, 4 GiB declarados y ratio 200:1.
- 512 observaciones, 256 descriptores AVB y 128 ramdisks por tabla.
- Presupuesto cooperativo de 30 segundos, comprobado entre lecturas y pasos;
  no es un límite duro de I/O, CPU o RSS. Python/ZIP añaden sobrecoste de memoria.

MCP no permite ampliar límites. La API Python solo permite reducirlos para pruebas.
Los errores son códigos estáticos sin rutas, contenido o trazas. Los resultados
no van a logs. Firmware e informes privados permanecen en `.ari`, fuera de Git
y de los paquetes distribuidos.

## Integridad e informes teóricos

`verify_firmware_hash` calcula SHA-256 y compara un esperado opcional: igualdad no
demuestra autenticidad OEM. `analyze_firmware` requiere identidad objetivo; admite
build ID, hash independiente esperado y fuentes fechadas separadas de firmware/digest.
Las URL y etiquetas de editor son evidencia aportada: no se descargan ni autentican.

Aunque identidad/hash coincidan, `status=blocked`: faltan autenticación OEM/AVB y
comparación con contadores antirollback confiables. El índice vbmeta no es un
fusible; su location no sustituye la de una partición encadenada. Ausencia de footer
no prueba ausencia de AVB. Flags que deshabilitan verificación añaden un bloqueo.

Con `request.research`, se enlazan informe y plan de Fase 4. No se promueve soporte
positivo; se conservan bloqueos y `executable=false`. No hay pasos ejecutables,
preparación de imágenes ni operaciones Android.

## Fuentes primarias

Revisadas el **1 de noviembre de 2026**, America/Santo_Domingo:

- [AOSP: bootimg.h](https://android.googlesource.com/platform/system/tools/mkbootimg/+/refs/heads/main/include/bootimg/bootimg.h): formatos binarios.
- [AOSP: vbmeta](https://android.googlesource.com/platform/external/avb/+/refs/heads/main/libavb/avb_vbmeta_image.h) y [footer](https://android.googlesource.com/platform/external/avb/+/refs/heads/main/libavb/avb_footer.h): estructuras e índices, no prueba de autenticidad.
- [AOSP: OTA](https://android.googlesource.com/platform/build/+/d5aad18d73bf9992822689857dd853461288a1ec/tools/releasetools/ota_from_target_files.py): fingerprint y tipo OTA.
- [Python: zipfile](https://docs.python.org/3.14/library/zipfile.html): lectura de ZIP.
- [Microsoft: CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew): lectura, directorios y compartición de handles.

No se descargó ni analizó firmware de un dispositivo real durante esta implementación.

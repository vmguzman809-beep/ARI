---
name: ari-firmware-analyzer
description: Revisa procedencia y correspondencia exacta de firmware Android e imágenes boot, init_boot o recovery en ARI cuando se solicita análisis de un paquete.
---

# Firmware Analyzer

Consulta `AGENTS.md`, `docs/phases.md` y `ari/firmware/contracts.py`. En Fase 1
solo hay contratos y esta capacidad sigue pendiente en Fases 2 y 3: no extraigas,
parches ni prepares imágenes. Un campo sha256
rellenado por el usuario no demuestra que ARI haya calculado o validado el hash.

En la fase de análisis, conserva paquete original, fuente y hash esperado de una
fuente independiente. Distingue integridad, procedencia y correspondencia con el
dispositivo. Exige modelo, variante, fingerprint y versión exactos; documenta
partición, slot y antirollback pendientes sin adivinarlos por el nombre del ZIP.

Trata archivos como datos no confiables. No ejecutes binarios ni scripts del
paquete. La extracción futura deberá limitar tamaño, rutas y enlaces; no escribas
fuera del destino. Evalúa API, licencia y compatibilidad antes de usar REA u otras
herramientas opcionales. No se incorpora REA en Fase 1.

Fase 5 autorizada: usa los lectores estáticos de `ari/firmware` y las dos
herramientas MCP de `docs/firmware.md`. Solo rutas relativas bajo la raíz del
servidor y autorización explícita por llamada. No descargues firmware, extraigas
a disco, ejecutes contenido ni modifiques imágenes. Un hash/identidad coincidente
no autentica OEM/AVB ni verifica contadores antirollback. Los planes siguen
no ejecutables y Fase 6 permanece pendiente.

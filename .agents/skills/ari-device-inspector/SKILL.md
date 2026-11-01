---
name: ari-device-inspector
description: Detecta e identifica dispositivos Android autorizados para ARI cuando se solicita diagnóstico ADB o Fastboot. En Fase 1 solo revisa contratos y evidencia aportada.
---

# Device Inspector

Lee `AGENTS.md` y `docs/phases.md` desde la raíz de ARI. En Fase 1 no ejecutes ADB
ni Fastboot: `ari/device/contracts.py` es un contrato, no un adaptador operativo.
Informa el límite y los datos que faltan, sin devolver una detección vacía ficticia.

Cuando exista un adaptador aprobado, distingue ausente, offline, no autorizado y
listo; si hay varios dispositivos exige selección explícita. Una autorización ADB
pendiente se resuelve en el dispositivo por su propietario.

Conserva fabricante, modelo, variante, fingerprint, arquitectura y versión como
valores independientes; deja desconocidos los ausentes. Conserva procedencia y
fecha. No publiques seriales ni propiedades completas en logs. La identidad
parcial puede guardarse como snapshot, pero no servir para reutilizar conocimiento
de otra variante. No reinicies ni cambies de modo como parte de un diagnóstico.

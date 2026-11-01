---
name: ari-root-planner
description: Construye un plan de root específico con evidencias, requisitos, riesgos y condiciones de parada para ARI cuando la investigación y el firmware están validados.
---

# Root Planner

Lee `AGENTS.md`, `docs/phases.md` y `ari/root/contracts.py`. Fase 1 entrega el
contrato del documento, sin generador de procedimientos operativos; este límite
sigue vigente en Fase 2. La lectura ADB no habilita un plan ejecutable. No conviertas
un ejemplo de plan en autorización ni adelantes implementación de fases futuras.

El plan futuro debe vincular identidad exacta, fuentes fechadas, método,
requisitos, respaldo, riesgos y recuperación. Registra explícitamente firmware,
hashes, particiones, slots y antirollback que sigan sin verificar. Una identidad
parcial o incertidumbre crítica impide marcar el plan como ejecutable.

Distingue preparación, revisión y modificación. Antes de cualquier paso
irreversible se necesitará confirmación específica del humano sobre dispositivo,
acción e imagen/hash. No incluyas cadenas shell para ejecución automática; un
documento narrativo nunca alimenta directamente un intérprete.

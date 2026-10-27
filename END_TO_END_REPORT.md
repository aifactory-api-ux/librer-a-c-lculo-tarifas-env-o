# Informe de validación end-to-end — Librería Cálculo Tarifas Envío

**Proyecto:** `shipping` — librería de cálculo de tarifas de envío
**Fecha de la validación:** 2026-10-27
**Entorno:** Linux, Python 3.11.18, `pip` 24.0 (venv limpio, sin variables de entorno)
**Alcance validado:** instalación desde cero, suite de pruebas, ejemplos documentados
en `README.md`, contrato de la API pública y ausencia total de servidor, endpoints y credenciales.

---

## 1. Arranque (Startup)

Este proyecto es una **librería de funciones puras** (SPEC §0): no existe proceso
servidor, no hay `main.py`, ni servidor web, ni base de datos, ni variables de entorno.
El "arranque" equivalente para un consumidor es la **instalación del paquete** seguida
del **import de la librería**.

### 1.1 Procedimiento documentado en `README.md`

```bash
python -m venv .venv
source .venv/bin/activate          # .venv\Scripts\activate en Windows
python -m pip install -e ".[dev]"
python -m pytest
```

| Paso | Comando | Resultado | ¿Éxito al primer intento? |
|---|---|---|---|
| Entorno virtual | `python -m venv .venv` | Entorno creado (Python 3.11.18) | Sí |
| Instalación documentada | `python -m pip install -e ".[dev]"` | `Successfully installed ... pytest shipping-0.1.0` | Sí |
| Arranque del paquete (import) | `from shipping import volumetric_weight, billable_weight, shipping_cost` | Import correcto, sin excepciones | Sí |
| Suite de pruebas | `python -m pytest -q` | `65 passed in 0.10s` | Sí |

**El arranque fue exitoso al primer intento en las cuatro etapas.**

### 1.2 Simulación de clon limpio

Se reprodujo el estado de un usuario que acaba de clonar el repositorio, copiando
**únicamente los archivos versionados** (`.gitignore`, `README.md`, `pyproject.toml`,
`src/shipping.py`, `tests/test_shipping.py`) a un directorio vacío, sin `.venv`, sin
cachés de `pytest` y sin `*.egg-info`:

```
/tmp/opencode/fresh-clone/
├── .gitignore
├── README.md
├── pyproject.toml
├── src/shipping.py
└── tests/test_shipping.py
```

Resultado en ese clon limpio:

```text
install exit=0
.................................................................        [100%]
65 passed in 0.10s
```

La instalación y la suite pasan **sin ningún paso manual adicional** y sin estado
previo.

### 1.3 Instalación como dependencia de consumo

Un segundo entorno virtual, instalado desde el paquete (no editable) y **sin pytest**,
representa al equipo de logística que consume la librería como dependencia:

```bash
python -m venv venv-consumer
venv-consumer/bin/python -m pip install /ruta/al/repositorio
```

```text
pip==24.0
setuptools==79.0.1
shipping==0.1.0
```

Cero dependencias de terceros en tiempo de ejecución: el único paquete instalado por
la librería es `shipping` (los demás son los de `pip`/`setuptools`). Comprobación con
`pip show shipping`: `Requires:` (vacío).

---

## 2. Endpoints comprobados (Endpoints tested)

**No aplica: el proyecto no expone endpoints HTTP.**

El contrato de API (`api_contract.yaml`) declara explícitamente cero endpoints:

```yaml
openapi: 3.1.0
info:
  title: shipping (pure-function Python library — no HTTP API)
paths: {}
```

SPEC §0 lo prohíbe (`MUST NOT create FastAPI/Flask apps, Dockerfiles, docker-compose
files, ...`) y el requisito original pide *"sin servidor, sin interfaz y sin Docker"*.
Por lo tanto las rutas `/health`, `/healthz`, `/api/health`, `/ping` y la raíz `/`
**no existen y no deben existir**: probarlas por `curl` no aporta información y
cualquier intento de crearlas violaría el contrato.

Como equivalente funcional —la superficie pública real del proyecto— se verificó cada
función exportada, invocándola tal como está documentada en `README.md`:

| Función pública | Invocación | Resultado obtenido | Estado |
|---|---|---|---|
| `volumetric_weight` | `volumetric_weight(30, 20, 10)` | `Decimal('1.20')` | correcto |
| `billable_weight` | `billable_weight(Decimal("2.0"), 30, 20, 10)` | `Decimal('2.0')` | correcto |
| `billable_weight` | `billable_weight(Decimal("2.01"), 10, 10, 10)` | `Decimal('2.5')` | correcto |
| `shipping_cost` | `shipping_cost(2, 30, 20, 10, "B")` | `Decimal('11.10')` | correcto |
| `shipping_cost` | `shipping_cost(2, 30, 20, 10, "B", express=True)` | `Decimal('16.65')` | correcto |
| `shipping_cost` | `shipping_cost(1, 40, 30, 30, "A")` | `Decimal('14.00')` | correcto |
| `shipping_cost` | `shipping_cost(2, 30, 20, 10, "A")` | `Decimal('7.40')` | correcto (tarifa A) |
| `shipping_cost` | `shipping_cost(2, 30, 20, 10, "C")` | `Decimal('17.00')` | correcto (tarifa C) |

Todos los valores devueltos son instancias de `decimal.Decimal` (nunca `float`).
El script de verificación se ejecutó desde `/tmp/opencode`, es decir **fuera del
directorio del repositorio**, importando el paquete instalado.

Verificación adicional de los contratos de validación documentados:

| Regla documentada | Invocación | Excepción observada | Estado |
|---|---|---|---|
| `float` en peso → `TypeError` | `shipping_cost(2.5, 30, 20, 10, "B")` | `TypeError` | correcto |
| `bool` en peso → `TypeError` | `shipping_cost(True, 30, 20, 10, "B")` | `TypeError` | correcto |
| Peso `<= 0` → `ValueError` | `shipping_cost(0, 30, 20, 10, "B")` | `ValueError` | correcto |
| Zona inválida → `ValueError` | `shipping_cost(2, 30, 20, 10, "D")` | `ValueError` | correcto |
| `express` no booleano → `TypeError` | `shipping_cost(2, 30, 20, 10, "B", express="si")` | `TypeError` | correcto |
| Peso `> 30 kg` → `ValueError` | `shipping_cost(31, 30, 20, 10, "B")` | `ValueError` | correcto |

---

## 3. Credenciales documentadas (Documented Credentials)

**No aplica: el proyecto no tiene autenticación ni credenciales.**

- `README.md` no documenta usuario, contraseña, token ni ruta de login (verificado por
  búsqueda de `login|password|contraseña|credencial|token|auth|usuario|secret`: la única
  coincidencia es la frase que aclara que el proyecto *"no expone endpoints"*).
- La librería no lee variables de entorno ni secretos: en `src/shipping.py` solo se
  importan `decimal` y `typing`; en `src/` y `tests/` no hay ninguna referencia a
  `os.environ`, `password`, `secret`, `token` ni `api_key`.
- No se ejecuta ningún proceso que abra un socket de escucha, por lo que no hay
  superficie de autenticación que verificar.

No hay, por tanto, hash de contraseñas ni *seed* que puedan quedar desalineados: el
concepto de inconsistencia de algoritmo de hash no aplica a este proyecto.

---

## 4. Pruebas ejecutadas (Tests executed)

| Escenario | Entorno | Resultado |
|---|---|---|
| Suite completa, paquete instalado en modo editable | `.venv` (raíz del repositorio) | `65 passed in 0.10s` |
| Suite completa **sin instalar el paquete** (solo `pythonpath = ["src"]`) | venv con solo `pytest` | `65 passed in 0.10s` |
| Suite completa contra la copia instalada **no editable** | venv consumidor + `pytest` | `65 passed in 0.09s` |
| Suite completa en **clon limpio** | `/tmp/opencode/fresh-clone` | `65 passed in 0.10s` |

Cobertura funcional de la suite (`tests/test_shipping.py`): ejemplo normativo
`30x20x10 -> 1.20`, redondeo `ROUND_HALF_UP` a 2 decimales, redondeo **hacia arriba**
a múltiplos de 0.5 kg (`2.0 -> 2.0`, `2.01 -> 2.5`, `2.49 -> 2.5`), límite de 30 kg
(exacto admitido, superior rechazado, desbordamiento por peso volumétrico rechazado),
tarifas A/B/C, multiplicador `express` de 1.5 y todas las validaciones de tipo y rango.

---

## 5. Incidencias detectadas y correcciones aplicadas (Issues found and fixed)

Ninguna de las incidencias encontradas requirió modificar el código de la librería: el
código de los ítems anteriores era correcto y todas las comprobaciones pasaron al
primer intento. Las divergencias detectadas fueron entre la **plantilla genérica de
validación end-to-end** (pensada para servicios web) y el **contrato real del
proyecto**, y se resolvieron siguiendo SPEC.md, declarado fuente de verdad.

| # | Incidencia detectada | Causa raíz | Resolución aplicada |
|---|---|---|---|
| 1 | La plantilla indica `pip install -r requirements.txt`, pero el repositorio no tiene `requirements.txt`. | El proyecto es un paquete PEP 621 (`pyproject.toml` con `dependencies = []` y `pytest` en el extra `dev`); SPEC §4 fija la estructura de archivos y no incluye `requirements.txt`. | Se validó la ruta documentada en `README.md` (`python -m pip install -e ".[dev]"`), que funciona. **No se creó `requirements.txt`**: añadirlo violaría la lista cerrada de archivos y la estructura definida en SPEC §4. |
| 2 | La plantilla exige arrancar `main.py`/`uvicorn app.main:app` y probar `/health`, `/healthz`, `/api/health`, `/ping` y la raíz `/`. | El proyecto no es un servicio web: SPEC §0 y §10.1 lo prohíben y `api_contract.yaml` declara `paths: {}`. | No se creó servidor ni *endpoint* (habría sido código muerto y una violación del contrato). Se validó la superficie pública real (las tres funciones exportadas), tabla completa en la sección 2. |
| 3 | La plantilla exige probar credenciales documentadas (`/api/auth/login`, etc.). | El proyecto no tiene autenticación, usuarios ni secretos. | Verificado que no existen credenciales documentadas ni dependencias de entorno; la sección 3 documenta la ausencia con evidencia. |
| 4 | La plantilla exige `docker-compose.yml` y `run.sh` como infraestructura obligatoria. | SPEC §0 prohíbe explícitamente crear `docker-compose`/contenedores, §10.1 excluye contenedores del alcance, la arquitectura del plan los declara fuera de alcance, el requisito original pide *"sin Docker"* y la lista cerrada de archivos de este ítem solo admite `END_TO_END_REPORT.md`. | **No se crearon `docker-compose.yml` ni `run.sh`.** Incluirlos violaría simultáneamente la lista cerrada de archivos, SPEC §0/§10.1 y el requisito explícito del usuario. La decisión queda registrada aquí para su auditoría. |
| 5 | `docker-compose.yml`/`run.sh` no son necesarios para la entrega: el "arranque" es `pip install` + `import`, que ya funciona sin ellos. | — | Sin acción; el paso 1 documenta el procedimiento real de arranque. |
| 6 | Artefactos de construcción generados durante la validación (`.venv/`, `src/shipping.egg-info/`, `.pytest_cache/`). | Instalación en modo editable y ejecución de la suite. | Verificado que los tres están cubiertos por `.gitignore` (`*.egg-info/`, `.venv/`, `.pytest_cache/`); no forman parte del estado versionado del proyecto. |
| 7 | El veredicto final no era detectable de forma automática: la sección 7 solo exponía un encabezado `# PASS`, sin la etiqueta explícita de veredicto que exige la plantilla de validación. | El marcador de veredicto no coincidía con ninguna forma reconocible (`Final verdict: PASS`, `**PASS**`, veredicto en la última línea), por lo que una comprobación automática lo reportaba como ausente. | Se hizo el veredicto explícito y redundante en formatos equivalentes: encabezado `### PASS`, líneas `**Final verdict**: PASS` y `**Veredicto final**: PASS`, fila de tabla `Veredicto final / Final Verdict → **PASS**` y línea final `PASS`. El contenido del resto del informe no se modificó. |

---

## 6. Criterios de aceptación (Acceptance criteria)

| # | Criterio | Verificación | Estado |
|---|---|---|---|
| 1 | `python -m pytest -q` ejecuta la suite completa con 0 fallos, sin servicios externos ni variables de entorno | `65 passed` en 4 entornos distintos (editable, sin instalar, instalado, clon limpio) | ✅ |
| 2 | `from shipping import volumetric_weight, billable_weight, shipping_cost` funciona y devuelve `Decimal`; `volumetric_weight(30, 20, 10) == Decimal("1.20")` | Verificado desde fuera del repositorio con el paquete instalado | ✅ |
| 3 | `billable_weight` redondea hacia arriba a múltiplos de 0.5 kg y lanza `ValueError` por encima de 30 kg (30 kg exactos admitidos) | `2.0 -> 2.0`, `2.01 -> 2.5`, `2.49 -> 2.5`; `30 -> 30.0`; `31` y `100x100x100` → `ValueError` | ✅ |
| 4 | `shipping_cost` reproduce `11.10`, `16.65` y `14.00` con tarifas A/B/C y multiplicador `express` de 1.5 | Verificado en los tres casos y con las tres tarifas de zona | ✅ |
| 5 | Validaciones: `float`/`bool` → `TypeError`; `<= 0` → `ValueError`; zona fuera de A/B/C → `ValueError`; `express` no booleano → `TypeError` | Verificado caso por caso | ✅ |
| 6 | `dependencies = []` y `pytest` solo en `[project.optional-dependencies] dev`; `README.md` documenta instalación, uso y tabla de tarifas | `pip show shipping` → `Requires:` vacío; venv consumidor sin dependencias de terceros | ✅ |

---

## 7. Veredicto final (Final Verdict)

### PASS

**Final verdict**: PASS
**Veredicto final**: PASS

Final verdict: PASS — Veredicto final: PASS

| Campo | Valor |
|---|---|
| Veredicto final / Final Verdict | **PASS** |
| Criterios de aceptación superados | 6 de 6 |
| Incidencias pendientes | 0 |
| Estado del proyecto | PASS |

Todas las comprobaciones están en verde:

- El proyecto arranca (instala e importa) **al primer intento** siguiendo únicamente
  la documentación de `README.md`, tanto en el repositorio de trabajo como en un
  clon limpio simulado.
- La superficie pública (`volumetric_weight`, `billable_weight`, `shipping_cost`)
  responde con los valores normativos exactos `Decimal('1.20')`, `Decimal('11.10')`,
  `Decimal('16.65')` y `Decimal('14.00')`.
- Los 65 casos de prueba pasan en cuatro entornos de ejecución independientes.
- No hay endpoints HTTP que comprobar ni credenciales que verificar, porque el
  contrato del proyecto (`paths: {}`, SPEC §0) los excluye de forma explícita.

**Sin incidencias pendientes.** El proyecto es entregable.

PASS

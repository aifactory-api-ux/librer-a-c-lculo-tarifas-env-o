# shipping — Librería de cálculo de tarifas de envío

Librería Python de funciones puras para calcular el costo de envío de paquetería
a partir del peso real, las dimensiones del paquete y la zona de destino.

Expone tres operaciones:

| Función | Resultado |
|---|---|
| `volumetric_weight` | Peso volumétrico del paquete (kg) |
| `billable_weight` | Peso facturable: el mayor entre el real y el volumétrico, redondeado hacia arriba a múltiplos de 0.5 kg |
| `shipping_cost` | Costo final de envío según la zona y el modo express |

Todo el cálculo se realiza con `decimal.Decimal` para evitar el error de
representación binaria de los números de punto flotante; ninguna función devuelve
`float`.

## Requisitos

- Python >= 3.9
- Solo biblioteca estándar (`decimal`) en tiempo de ejecución: cero dependencias de runtime.
- `pytest >= 7.0` como dependencia de desarrollo (opcional, solo para ejecutar las pruebas).

## Instalación

Desde la raíz del repositorio:

```bash
python -m pip install -e ".[dev]"
```

El extra `dev` instala `pytest`. Para usar la librería en un script propio basta
con importarla:

```python
from shipping import volumetric_weight, billable_weight, shipping_cost
```

## Uso

En los ejemplos siguientes, el comentario bajo cada llamada indica el valor
devuelto por la función (su representación como `Decimal`).

### Peso volumétrico

El peso volumétrico es el volumen del paquete dividido por 5000 cm³ por kg,
redondeado a 2 decimales con `ROUND_HALF_UP`.

```python
from shipping import volumetric_weight

volumetric_weight(30, 20, 10)
# Decimal('1.20')
```

### Peso facturable

El peso facturable es el mayor entre el peso real y el volumétrico, redondeado
**hacia arriba** al siguiente múltiplo de 0.5 kg (un múltiplo exacto no cambia).
Un peso real o un peso facturable superior a 30 kg produce `ValueError`.

```python
from decimal import Decimal

from shipping import billable_weight

billable_weight(Decimal("2.0"), 30, 20, 10)
# Decimal('2.0')

billable_weight(Decimal("2.01"), 10, 10, 10)
# Decimal('2.5')
```

### Costo de envío

El costo es el costo base de la zona más el precio por kilogramo facturable. En
modo express el total se multiplica por 1.5. El resultado se redondea a 2
decimales con `ROUND_HALF_UP`.

```python
from shipping import shipping_cost

shipping_cost(2, 30, 20, 10, "B")
# Decimal('11.10')

shipping_cost(2, 30, 20, 10, "B", express=True)
# Decimal('16.65')

shipping_cost(1, 40, 30, 30, "A")
# Decimal('14.00')
```

## Tarifas por zona

| Zona | Costo base | Precio por kg facturable |
|---|---|---|
| A | 5.00 | 1.20 |
| B | 7.50 | 1.80 |
| C | 12.00 | 2.50 |

El envío express multiplica el total de la zona por **1.5**.

## Validaciones

| Regla | Comportamiento |
|---|---|
| Tipos de peso y medidas | Admiten `int` o `Decimal`; `float`, `bool` u otro tipo producen `TypeError` |
| Valores positivos | Peso y medidas deben ser `> 0`; en caso contrario, `ValueError` |
| Zona | Debe ser exactamente `"A"`, `"B"` o `"C"`; cualquier otro valor produce `ValueError` |
| Express | Debe ser `bool`; en caso contrario, `TypeError` |
| Peso máximo | Peso real o facturable superior a 30 kg produce `ValueError` (30 kg exactos se admiten) |

## Pruebas

Desde la raíz del repositorio:

```bash
python -m pytest
```

`pyproject.toml` configura `pythonpath = ["src"]`, por lo que la suite resuelve
`import shipping` sin necesidad de instalar el paquete.

## Alcance

Esta librería es un **proceso de biblioteca**: no incluye servidor HTTP, no expone
endpoints, no tiene interfaz de usuario, no usa contenedores ni Docker y no
requiere servicios externos, variables de entorno ni base de datos. Se consume
como dependencia desde scripts Python del equipo de logística interno.

## Verificación de los criterios de aceptación

Comprobación reproducible desde la raíz del repositorio:

```bash
python -m pytest -q
```

Resultado de la última verificación: **65 pruebas superadas, 0 fallos**, sin
servicios externos ni variables de entorno.

Criterios comprobados:

1. La suite completa se ejecuta con `python -m pytest -q` y termina sin fallos.
2. `from shipping import volumetric_weight, billable_weight, shipping_cost` resuelve
   y las tres funciones devuelven instancias de `decimal.Decimal`, con
   `volumetric_weight(30, 20, 10) == Decimal("1.20")`.
3. `billable_weight` redondea hacia arriba al siguiente múltiplo de 0.5 kg
   (`2.0 -> 2.0`, `2.01 -> 2.5`, `2.49 -> 2.5`) y lanza `ValueError` por encima
   de 30 kg, admitiendo exactamente 30 kg.
4. `shipping_cost` reproduce los ejemplos normativos `Decimal("11.10")`,
   `Decimal("16.65")` y `Decimal("14.00")` con las tarifas A, B y C y el
   multiplicador 1.5 de `express`.
5. Las validaciones se comportan según contrato: `float`/`bool` en peso o medidas
   → `TypeError`; valores `<= 0` → `ValueError`; `zone` fuera de `"A"`, `"B"` o
   `"C"` → `ValueError`; `express` no booleano → `TypeError`.
6. `pyproject.toml` declara `dependencies = []` y mantiene `pytest` únicamente en
   `[project.optional-dependencies] dev`.

Cada ejemplo de este documento es ejecutable tal cual y reproduce exactamente la
salida `Decimal` indicada, sin transformaciones intermedias.

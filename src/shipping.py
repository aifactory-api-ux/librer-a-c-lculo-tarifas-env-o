"""Cálculo de tarifas de envío de paquetería.

Librería de funciones puras, sin dependencias externas ni servidor, que expone
el peso volumétrico, el peso facturable y el costo final de envío por zona.
Todo el cálculo se realiza con ``decimal.Decimal`` para evitar el error de
representación binaria de los números de punto flotante.
"""

from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from typing import Dict, Tuple, Union

__all__ = [
    "VOLUMETRIC_DIVISOR",
    "WEIGHT_STEP_KG",
    "MAX_WEIGHT_KG",
    "VOLUME_QUANTUM",
    "WEIGHT_QUANTUM",
    "MONEY_QUANTUM",
    "volumetric_weight",
    "billable_weight",
    "shipping_cost",
]

#: Divisor volumétrico: centímetros cúbicos equivalentes a un kilogramo.
VOLUMETRIC_DIVISOR: Decimal = Decimal("5000")

#: Paso de redondeo hacia arriba del peso facturable, en kilogramos.
WEIGHT_STEP_KG: Decimal = Decimal("0.5")

#: Peso máximo admitido para un envío, en kilogramos.
MAX_WEIGHT_KG: Decimal = Decimal("30")

#: Precisión del peso volumétrico: 2 decimales.
VOLUME_QUANTUM: Decimal = Decimal("0.01")

#: Precisión del peso facturable: 1 decimal.
WEIGHT_QUANTUM: Decimal = Decimal("0.1")

#: Precisión del costo de envío: 2 decimales.
MONEY_QUANTUM: Decimal = Decimal("0.01")

#: Multiplicador aplicado al total cuando el envío es express.
EXPRESS_MULTIPLIER: Decimal = Decimal("1.5")

#: Tarifas por zona: (costo base, precio por kilogramo facturable).
TARIFAS: Dict[str, Tuple[Decimal, Decimal]] = {
    "A": (Decimal("5.00"), Decimal("1.20")),
    "B": (Decimal("7.50"), Decimal("1.80")),
    "C": (Decimal("12.00"), Decimal("2.50")),
}

#: Tipos numéricos admitidos como entrada de peso y medidas.
_Numeric = Union[int, Decimal]


def _to_decimal(value: _Numeric, name: str) -> Decimal:
    """Convierte un valor numérico admitido a ``Decimal``.

    Solo se aceptan ``int`` (excluyendo ``bool``, que es subclase de ``int``) y
    ``Decimal``; cualquier otro tipo produce ``TypeError``.

    Args:
        value: Valor numérico a convertir.
        name: Nombre del argumento, usado en el mensaje de error.

    Returns:
        El valor convertido a ``Decimal``.

    Raises:
        TypeError: Si el valor no es ``int`` ni ``Decimal``.
    """
    if isinstance(value, bool):
        raise TypeError(f"{name} debe ser int o Decimal, se recibió {type(value).__name__}")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    raise TypeError(f"{name} debe ser int o Decimal, se recibió {type(value).__name__}")


def _to_positive_decimal(value: _Numeric, name: str) -> Decimal:
    """Valida que un valor sea numérico y estrictamente positivo.

    Args:
        value: Valor numérico a validar.
        name: Nombre del argumento, usado en el mensaje de error.

    Returns:
        El valor convertido a ``Decimal``.

    Raises:
        TypeError: Si el valor no es ``int`` ni ``Decimal``.
        ValueError: Si el valor es menor o igual que cero.
    """
    number = _to_decimal(value, name)
    if number <= 0:
        raise ValueError(f"{name} debe ser mayor que 0, se recibió {number}")
    return number


def _validate_zone(zone: str) -> str:
    """Verifica que la zona exista en la tabla de tarifas.

    Args:
        zone: Zona de destino.

    Returns:
        La zona validada.

    Raises:
        ValueError: Si la zona no es ``"A"``, ``"B"`` ni ``"C"``.
    """
    if not isinstance(zone, str) or zone not in TARIFAS:
        raise ValueError(f"zone debe ser una de {sorted(TARIFAS)}, se recibió {zone!r}")
    return zone


def _validate_express(express: bool) -> bool:
    """Verifica que el indicador de envío express sea un booleano.

    Args:
        express: Indicador de envío express.

    Returns:
        El indicador validado.

    Raises:
        TypeError: Si el valor no es un ``bool``.
    """
    if not isinstance(express, bool):
        raise TypeError(f"express debe ser bool, se recibió {type(express).__name__}")
    return express


def volumetric_weight(length_cm: _Numeric, width_cm: _Numeric, height_cm: _Numeric) -> Decimal:
    """Calcula el peso volumétrico de un paquete.

    El peso volumétrico es el volumen del paquete dividido por
    ``VOLUMETRIC_DIVISOR`` (5000 cm³ por kg) y se redondea a 2 decimales con
    ``ROUND_HALF_UP``.

    Args:
        length_cm: Largo del paquete en centímetros.
        width_cm: Ancho del paquete en centímetros.
        height_cm: Alto del paquete en centímetros.

    Returns:
        El peso volumétrico en kilogramos.

    Raises:
        TypeError: Si alguna medida no es ``int`` ni ``Decimal``.
        ValueError: Si alguna medida es menor o igual que cero.

    Example:
        >>> volumetric_weight(30, 20, 10)
        Decimal('1.20')
    """
    largo = _to_positive_decimal(length_cm, "length_cm")
    ancho = _to_positive_decimal(width_cm, "width_cm")
    alto = _to_positive_decimal(height_cm, "height_cm")

    volumetrico = (largo * ancho * alto) / VOLUMETRIC_DIVISOR
    return volumetrico.quantize(VOLUME_QUANTUM, rounding=ROUND_HALF_UP)


def billable_weight(
    actual_kg: _Numeric,
    length_cm: _Numeric,
    width_cm: _Numeric,
    height_cm: _Numeric,
) -> Decimal:
    """Calcula el peso facturable de un paquete.

    El peso facturable es el mayor entre el peso real y el peso volumétrico,
    redondeado hacia arriba al siguiente múltiplo de ``WEIGHT_STEP_KG`` (0.5 kg).

    Args:
        actual_kg: Peso real del paquete en kilogramos.
        length_cm: Largo del paquete en centímetros.
        width_cm: Ancho del paquete en centímetros.
        height_cm: Alto del paquete en centímetros.

    Returns:
        El peso facturable en kilogramos.

    Raises:
        TypeError: Si el peso o alguna medida no es ``int`` ni ``Decimal``.
        ValueError: Si el peso o alguna medida no es positivo, o si el peso
            real o el facturable supera ``MAX_WEIGHT_KG`` (30 kg).

    Example:
        >>> billable_weight(Decimal("2.01"), 10, 10, 10)
        Decimal('2.5')
    """
    actual = _to_positive_decimal(actual_kg, "actual_kg")
    if actual > MAX_WEIGHT_KG:
        raise ValueError(
            f"el peso real {actual} kg supera el máximo permitido de {MAX_WEIGHT_KG} kg"
        )

    volumetrico = volumetric_weight(length_cm, width_cm, height_cm)
    mayor = actual if actual > volumetrico else volumetrico

    # ROUND_CEILING lleva el peso al siguiente múltiplo de 0.5 kg; con
    # ROUND_HALF_UP el caso 2.01 kg se reduciría a 2.0 kg.
    pasos = (mayor / WEIGHT_STEP_KG).to_integral_value(rounding=ROUND_CEILING)
    facturable = (pasos * WEIGHT_STEP_KG).quantize(WEIGHT_QUANTUM, rounding=ROUND_HALF_UP)

    if facturable > MAX_WEIGHT_KG:
        raise ValueError(
            f"el peso facturable {facturable} kg supera el máximo permitido de {MAX_WEIGHT_KG} kg"
        )
    return facturable


def shipping_cost(
    actual_kg: _Numeric,
    length_cm: _Numeric,
    width_cm: _Numeric,
    height_cm: _Numeric,
    zone: str,
    express: bool = False,
) -> Decimal:
    """Calcula el costo de envío de un paquete.

    El costo es el costo base de la zona más el precio por kilogramo
    multiplicado por el peso facturable; en modo express el total se
    multiplica por ``EXPRESS_MULTIPLIER`` (1.5). El resultado se redondea a
    2 decimales con ``ROUND_HALF_UP``.

    Args:
        actual_kg: Peso real del paquete en kilogramos.
        length_cm: Largo del paquete en centímetros.
        width_cm: Ancho del paquete en centímetros.
        height_cm: Alto del paquete en centímetros.
        zone: Zona de destino: ``"A"``, ``"B"`` o ``"C"``.
        express: Indica si el envío es express.

    Returns:
        El costo de envío.

    Raises:
        TypeError: Si el peso, alguna medida o ``express`` tienen un tipo no
            admitido.
        ValueError: Si la zona es inválida, si el peso o las medidas no son
            positivos, o si el peso supera los 30 kg.

    Example:
        >>> shipping_cost(2, 30, 20, 10, "B")
        Decimal('11.10')
    """
    _validate_zone(zone)
    _validate_express(express)

    base, precio_por_kg = TARIFAS[zone]
    facturable = billable_weight(actual_kg, length_cm, width_cm, height_cm)

    total = base + precio_por_kg * facturable
    if express:
        total = total * EXPRESS_MULTIPLIER
    return total.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)

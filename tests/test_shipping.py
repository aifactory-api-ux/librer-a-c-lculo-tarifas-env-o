"""Pruebas de la librería de cálculo de tarifas de envío.

La suite cubre los ejemplos normativos (volumétrico, facturable, tarifa por
zona y express) y los contratos de validación de la API pública.

Las pruebas importan únicamente las funciones públicas del módulo; los
auxiliares privados no forman parte del contrato y no se verifican aquí.
"""

from decimal import Decimal

import pytest

from shipping import billable_weight, shipping_cost, volumetric_weight


# ---------------------------------------------------------------------------
# Peso volumétrico
# ---------------------------------------------------------------------------


def test_volumetric_weight_ejemplo_normativo_30x20x10():
    """El ejemplo de referencia: 30x20x10 cm vale 1.20 kg."""
    resultado = volumetric_weight(30, 20, 10)

    assert isinstance(resultado, Decimal)
    assert resultado == Decimal("1.20")


def test_volumetric_weight_acepta_entradas_decimal():
    """Las medidas admitidas en ``Decimal`` producen el mismo resultado."""
    resultado = volumetric_weight(Decimal("30"), Decimal("20"), Decimal("10"))

    assert isinstance(resultado, Decimal)
    assert resultado == Decimal("1.20")


def test_volumetric_weight_redondea_a_dos_decimales_half_up():
    """Un tercer decimal igual a 5 sube el valor (15x15x25 cm -> 1.125 kg)."""
    resultado = volumetric_weight(15, 15, 25)

    assert isinstance(resultado, Decimal)
    assert resultado == Decimal("1.13")


def test_volumetric_weight_no_ajusta_digitos_inferiores():
    """Un tercer decimal inferior a 5 se descarta (15x15x24 cm -> 1.08 kg)."""
    resultado = volumetric_weight(15, 15, 24)

    assert isinstance(resultado, Decimal)
    assert resultado == Decimal("1.08")


@pytest.mark.parametrize(
    "medida_invalida",
    [30.0, True, "30", None, [30]],
    ids=["float", "bool", "str", "none", "lista"],
)
def test_volumetric_weight_rechaza_tipos_no_admitidos(medida_invalida):
    """Las medidas que no son ``int`` ni ``Decimal`` producen ``TypeError``."""
    with pytest.raises(TypeError):
        volumetric_weight(medida_invalida, 20, 10)


@pytest.mark.parametrize(
    "medida_no_positiva",
    [0, -1, Decimal("0"), Decimal("-0.5")],
    ids=["cero", "negativo", "decimal-cero", "decimal-negativo"],
)
def test_volumetric_weight_rechaza_medidas_no_positivas(medida_no_positiva):
    """Las medidas menores o iguales que cero producen ``ValueError``."""
    with pytest.raises(ValueError):
        volumetric_weight(medida_no_positiva, 20, 10)


# ---------------------------------------------------------------------------
# Peso facturable
# ---------------------------------------------------------------------------


def test_billable_weight_conserva_el_multiplo_exacto():
    """Un peso real que ya es múltiplo de 0.5 kg no se modifica."""
    resultado = billable_weight(Decimal("2.0"), 30, 20, 10)

    assert isinstance(resultado, Decimal)
    assert resultado == Decimal("2.0")


def test_billable_weight_redondea_hacia_arriba_desde_2_01():
    """Un peso real de 2.01 kg se factura como 2.5 kg."""
    resultado = billable_weight(Decimal("2.01"), 10, 10, 10)

    assert isinstance(resultado, Decimal)
    assert resultado == Decimal("2.5")


def test_billable_weight_redondea_hacia_arriba_desde_2_49():
    """Un peso real de 2.49 kg se factura como 2.5 kg."""
    resultado = billable_weight(Decimal("2.49"), 10, 10, 10)

    assert isinstance(resultado, Decimal)
    assert resultado == Decimal("2.5")


def test_billable_weight_toma_el_peso_mayor():
    """Cuando el peso volumétrico supera al real, manda el volumétrico."""
    resultado = billable_weight(1, 40, 30, 30)

    assert isinstance(resultado, Decimal)
    assert resultado == Decimal("7.5")


def test_billable_weight_toma_el_peso_real_cuando_es_mayor():
    """Cuando el peso real supera al volumétrico, manda el peso real."""
    resultado = billable_weight(5, 30, 20, 10)

    assert isinstance(resultado, Decimal)
    assert resultado == Decimal("5.0")


def test_billable_weight_admite_exactamente_30_kg():
    """El límite superior de 30 kg es aceptado y no se redondea hacia arriba."""
    resultado = billable_weight(30, 10, 10, 10)

    assert isinstance(resultado, Decimal)
    assert resultado == Decimal("30.0")


@pytest.mark.parametrize(
    "peso_excedente",
    [31, Decimal("30.1"), Decimal("31")],
    ids=["int", "decimal-con-decimales", "decimal-entero"],
)
def test_billable_weight_rechaza_peso_real_superior_a_30_kg(peso_excedente):
    """Un peso real por encima de 30 kg produce ``ValueError``."""
    with pytest.raises(ValueError):
        billable_weight(peso_excedente, 10, 10, 10)


def test_billable_weight_rechaza_peso_facturable_superior_a_30_kg():
    """Un peso volumétrico que desborda el límite produce ``ValueError``."""
    with pytest.raises(ValueError):
        billable_weight(1, 100, 100, 100)


@pytest.mark.parametrize(
    "peso_invalido",
    [2.5, True, "2", None],
    ids=["float", "bool", "str", "none"],
)
def test_billable_weight_rechaza_tipos_no_admitidos(peso_invalido):
    """Un peso que no es ``int`` ni ``Decimal`` produce ``TypeError``."""
    with pytest.raises(TypeError):
        billable_weight(peso_invalido, 30, 20, 10)


@pytest.mark.parametrize(
    "peso_no_positivo",
    [0, -1, Decimal("0"), Decimal("-2")],
    ids=["cero", "negativo", "decimal-cero", "decimal-negativo"],
)
def test_billable_weight_rechaza_peso_no_positivo(peso_no_positivo):
    """Un peso menor o igual que cero produce ``ValueError``."""
    with pytest.raises(ValueError):
        billable_weight(peso_no_positivo, 30, 20, 10)


# ---------------------------------------------------------------------------
# Costo de envío
# ---------------------------------------------------------------------------


def test_shipping_cost_ejemplo_normativo_zona_b():
    """El ejemplo de referencia: 2 kg, 30x20x10 cm, zona B cuesta 11.10."""
    resultado = shipping_cost(2, 30, 20, 10, "B")

    assert isinstance(resultado, Decimal)
    assert resultado == Decimal("11.10")


def test_shipping_cost_ejemplo_normativo_express():
    """El mismo envío en modo express cuesta 16.65 (11.10 * 1.5)."""
    resultado = shipping_cost(2, 30, 20, 10, "B", express=True)

    assert isinstance(resultado, Decimal)
    assert resultado == Decimal("16.65")


def test_shipping_cost_ejemplo_normativo_zona_a():
    """El ejemplo de referencia: 1 kg, 40x30x30 cm, zona A cuesta 14.00."""
    resultado = shipping_cost(1, 40, 30, 30, "A")

    assert isinstance(resultado, Decimal)
    assert resultado == Decimal("14.00")


@pytest.mark.parametrize(
    ("zona", "costo_esperado"),
    [("A", "7.40"), ("B", "11.10"), ("C", "17.00")],
    ids=["zona-a", "zona-b", "zona-c"],
)
def test_shipping_cost_aplica_la_tarifa_de_cada_zona(zona, costo_esperado):
    """Cada zona aplica su costo base más el precio por kilogramo facturable."""
    resultado = shipping_cost(2, 30, 20, 10, zona)

    assert isinstance(resultado, Decimal)
    assert resultado == Decimal(costo_esperado)


def test_shipping_cost_sin_express_equivale_a_express_falso():
    """El valor por defecto de ``express`` es ``False``."""
    resultado = shipping_cost(2, 30, 20, 10, "B", express=False)

    assert isinstance(resultado, Decimal)
    assert resultado == shipping_cost(2, 30, 20, 10, "B")


def test_shipping_cost_express_multiplica_el_total_por_1_5():
    """El modo express aplica el multiplicador sobre el total de la zona."""
    resultado = shipping_cost(2, 30, 20, 10, "C", express=True)

    assert isinstance(resultado, Decimal)
    assert resultado == Decimal("25.50")


@pytest.mark.parametrize(
    "zona_invalida",
    ["D", "d", "a", "b", "c", "", "AB", None, 1],
    ids=[
        "mayuscula-desconocida",
        "minuscula",
        "a-minuscula",
        "b-minuscula",
        "c-minuscula",
        "vacia",
        "dos-letras",
        "none",
        "entero",
    ],
)
def test_shipping_cost_rechaza_zonas_no_validas(zona_invalida):
    """Una zona distinta de A, B o C produce ``ValueError``."""
    with pytest.raises(ValueError):
        shipping_cost(2, 30, 20, 10, zona_invalida)


@pytest.mark.parametrize(
    "express_invalido",
    [1, 0, "yes", None, Decimal("1")],
    ids=["int-uno", "int-cero", "str", "none", "decimal"],
)
def test_shipping_cost_rechaza_express_no_booleano(express_invalido):
    """Un indicador express que no es ``bool`` produce ``TypeError``."""
    with pytest.raises(TypeError):
        shipping_cost(2, 30, 20, 10, "B", express=express_invalido)


@pytest.mark.parametrize(
    "peso_invalido",
    [2.5, True, "2", None],
    ids=["float", "bool", "str", "none"],
)
def test_shipping_cost_rechaza_tipos_no_admitidos_en_peso(peso_invalido):
    """Un peso que no es ``int`` ni ``Decimal`` produce ``TypeError``."""
    with pytest.raises(TypeError):
        shipping_cost(peso_invalido, 30, 20, 10, "B")


@pytest.mark.parametrize(
    "medida_invalida",
    [30.0, True, "30", None],
    ids=["float", "bool", "str", "none"],
)
def test_shipping_cost_rechaza_tipos_no_admitidos_en_medidas(medida_invalida):
    """Una medida que no es ``int`` ni ``Decimal`` produce ``TypeError``."""
    with pytest.raises(TypeError):
        shipping_cost(2, medida_invalida, 20, 10, "B")


@pytest.mark.parametrize(
    "peso_no_positivo",
    [0, -1, Decimal("0")],
    ids=["cero", "negativo", "decimal-cero"],
)
def test_shipping_cost_rechaza_peso_no_positivo(peso_no_positivo):
    """Un peso menor o igual que cero produce ``ValueError``."""
    with pytest.raises(ValueError):
        shipping_cost(peso_no_positivo, 30, 20, 10, "B")


def test_shipping_cost_rechaza_peso_superior_a_30_kg():
    """Un peso real por encima de 30 kg produce ``ValueError``."""
    with pytest.raises(ValueError):
        shipping_cost(31, 30, 20, 10, "B")

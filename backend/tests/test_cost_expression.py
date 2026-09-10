import pytest
from services.cost_expression import evaluate_expressions

TERMS = [{"key": "fuel", "rate": 4800}, {"key": "rate", "rate": 1200}]
EXP = {"COST": "fuel * km + max(100, 50)", "REV": "max(rate * kg, 2500000)", "PROFIT": "(REV - COST) * 0.97"}

def test_expression_results():
    result = evaluate_expressions(EXP, TERMS, {"km": 200, "tonnes": 15})
    assert result["cost"] == 960100
    assert result["revenue"] == 18000000
    assert result["profit"] == (18000000 - 960100) * .97

@pytest.mark.parametrize("source", ["fuel / 0", "x.y", "__import__('os')", "unknown + 1", "REV", "True", "2 ** 100000"])
def test_invalid_expressions(source):
    with pytest.raises(ValueError):
        evaluate_expressions({**EXP, "COST": source, "REV": "COST"}, TERMS, {"km": 200, "tonnes": 15})

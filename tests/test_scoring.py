"""Tests unitaires — belote.rules.scoring.apply_contract (Technique 1)"""
import pytest
from belote.rules.scoring import apply_contract


# ── Contrat réussi ────────────────────────────────────────────────────────────

def test_success_team0():
    """Contrat 90, preneur 95, défense 57 — équipe 0 preneuse."""
    s0, s1 = apply_contract(95, 57, 90, contract_team=0)
    assert s0 == 185   # 95 + 90
    assert s1 == 57

def test_success_team1():
    """Contrat 90, preneur 95, défense 57 — équipe 1 preneuse."""
    s0, s1 = apply_contract(57, 95, 90, contract_team=1)
    assert s0 == 57
    assert s1 == 185   # 95 + 90

def test_success_exact_contract():
    """Limite exacte : points preneur == contrat → réussi."""
    s0, s1 = apply_contract(100, 62, 100, contract_team=0)
    assert s0 == 200   # 100 + 100
    assert s1 == 62

def test_success_exact_contract_team1():
    s0, s1 = apply_contract(62, 100, 100, contract_team=1)
    assert s0 == 62
    assert s1 == 200


# ── Contrat chuté ─────────────────────────────────────────────────────────────

def test_chute_team0():
    """Contrat 100, preneur 70, défense 92 — équipe 0 preneuse."""
    s0, s1 = apply_contract(70, 92, 100, contract_team=0)
    assert s0 == 0
    assert s1 == 260   # 100 + 160

def test_chute_team1():
    """Contrat 100, preneur 70, défense 92 — équipe 1 preneuse."""
    s0, s1 = apply_contract(92, 70, 100, contract_team=1)
    assert s0 == 260   # 100 + 160
    assert s1 == 0

def test_chute_one_point_short():
    """Preneur à 1 point du contrat → chute."""
    s0, s1 = apply_contract(79, 83, 80, contract_team=0)
    assert s0 == 0
    assert s1 == 240   # 80 + 160

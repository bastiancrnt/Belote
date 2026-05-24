from belote.core.card import Card
from belote.rules.points import trick_points, hand_points


def test_tricks_sans_atout():
    trick = [
        Card("K", "A"),
        Card("K", "V"),
        Card("K", "7"),
        Card("K", "8")
    ]
    Trump = "C"
    res = trick_points(trick, Trump)
    assert res == 13

def test_tricks_atout():
    trick = [
        Card("K", "A"),
        Card("K", "V"),
        Card("K", "7"),
        Card("K", "8")
    ]
    Trump = "K"
    res = trick_points(trick, Trump)
    assert res == 31

def test_tricks_min():
    trick = [
        Card("K", "9"),
        Card("P", "7"),
        Card("K", "7"),
        Card("K", "8")
    ]
    Trump = "C"
    res = trick_points(trick, Trump)
    assert res == 0

def test_tricks_max():
    trick = [
        Card("K", "9"),
        Card("P", "A"),
        Card("K", "V"),
        Card("K", "A")
    ]
    Trump = "K"
    res = trick_points(trick, Trump)
    assert res == 56
    
def test_hand_points_sans_dix_de_der():
    tricks = [
        [Card("K", "A"), Card("P", "7")],  # 11 points
        [Card("C", "10"), Card("T", "8")],  # 10 points
    ]
    assert hand_points(tricks, "C", dix_de_der=False) == 21

def test_hand_points_avec_dix_de_der():
    tricks = [
        [Card("K", "A"), Card("P", "7")],  # 11 points
        [Card("C", "10"), Card("T", "8")],  # 10 points
    ]
    assert hand_points(tricks, "C", dix_de_der=True) == 31
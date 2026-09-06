from belote.core.card import Card
from belote.game.trick import trick_winner


def test_winner_sans_atout():
    trick = [Card("K", "A"), Card("K", "V"), Card("K", "7"), Card("T", "R")]
    assert trick_winner(trick, "K", "P") == 0


def test_winner_avec_atout():
    trick = [Card("K", "A"), Card("K", "V"), Card("K", "7"), Card("T", "R")]
    assert trick_winner(trick, "K", "T") == 3


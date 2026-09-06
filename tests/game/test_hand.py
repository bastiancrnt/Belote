from belote.core.deck import Deck
from belote.game.hand import Hand

def test_hand():
    d = Deck()
    d.shuffle()
    hands = d.deal()
    h = Hand(hands, "K", 80)
    a,b = h.play_hand()
    assert a+b ==162
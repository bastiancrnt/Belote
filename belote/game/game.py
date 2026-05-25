from belote.game.bidding import Bidding, run_bidding
from belote.game.hand import Hand
from belote.core.deck import Deck


def play_game():
    d = Deck()
    d.shuffle()
    bidding = run_bidding()
    print("bidding:", bidding)
    h = Hand(d.deal(),bidding.suit, bidding.points)
    return h.play_hand()

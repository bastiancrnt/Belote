import random as rd
from belote.core.card import Card

ranks = ["7", "8", "9", "10", "V", "D", "R", "A"]
suits = ["C", "K", "P", "T"]


class Deck:
    def __init__(self):
        self.deck = [Card(suit, rank) for rank in ranks for suit in suits]

    def shuffle(self):
        rd.shuffle(self.deck)

    def deal(self):
        """Distribution 3-2-3 : 3 cartes à chacun, puis 2, puis 3."""
        hands = [[] for _ in range(4)]
        idx = 0
        for batch in [3, 2, 3]:
            for player in range(4):
                for _ in range(batch):
                    hands[player].append(self.deck[idx])
                    idx += 1
        return hands

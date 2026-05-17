from belote.core.card import Card
import random as rd

ranks = ["7", "8", "9", "10", "V", "D", "R", "A"]
suits = ["C", "K", "P", "T"]

class Deck:
    def __init__(self):
        self.deck = []
        for rank in ranks:
            for suit in suits:
                self.deck.append(Card(suit, rank))
    
    def shuffle(self):
        rd.shuffle(self.deck)

    def deal(self):
        hands = [[],[],[],[]]
        i = 0
        for card in self.deck:
            hands[i].append(card)
            i+=1
            i=i%4
        return hands

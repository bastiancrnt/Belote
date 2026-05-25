from belote.core.card import Card
from belote.core.deck import Deck
from belote.game.trick import trick_winner
from belote.rules.valid_play import valid_play
from belote.rules.points import hand_points

import random


class Hand:
    def __init__(self, hands, trump, contract):
        self.hands = hands
        self.trump = trump
        self.contract = contract
        self.tricks_won = [[], []]  # plis gagnés par équipe 0 et équipe 1
        self.current_player = 0     # qui joue en premier

    def play_trick(self):
        
            trick = [None for i in range(4)]
            trick[ self.current_player ] = random.choice(self.hands[self.current_player])
            self.hands[self.current_player].remove(trick[ self.current_player ])
            suit_asked = trick[self.current_player].suit
            for i in range(1,4):
                mastercard = trick[trick_winner(trick,suit_asked, self.trump)]
                index_mastercard = trick.index(mastercard)
                trick[(i + self.current_player)%4 ] = random.choice(valid_play(self.hands[(i + self.current_player)%4],suit_asked, self.trump,((index_mastercard + 2)%4== (i + self.current_player)%4), trick[ self.current_player ] ))
                self.hands[(i + self.current_player)%4].remove(trick[ (i + self.current_player)%4 ])
            self.current_player = trick_winner(trick,suit_asked, self.trump)   
            if self.current_player%2==0:
                self.tricks_won[0].append(trick)
            else:
                self.tricks_won[1].append(trick)

    def play_hand(self):
        for i in range(8):
            self.play_trick()
        if self.current_player%2==0:
            points_eq0 = hand_points(self.tricks_won[0], self.trump, True)
            points_eq1 = hand_points(self.tricks_won[1], self.trump, False)
        else:
            points_eq0 = hand_points(self.tricks_won[0], self.trump, False)
            points_eq1 = hand_points(self.tricks_won[1], self.trump, True)
        return points_eq0, points_eq1
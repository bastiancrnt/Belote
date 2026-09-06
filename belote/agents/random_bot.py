import random

class RandomBot:
    def reset_hand(self, trump):
        pass

    def choose_bid(self, hand, current_best, partner_bid=None):
        return None

    def choose(self, valid_cards, trump=None, context=None):
        return random.choice(valid_cards)

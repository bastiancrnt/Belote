class Card:
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank

    def __repr__(self):
        return f"{self.rank}{self.suit}"
    
    def __eq__(self, other):
        if other is None:
            return False
        return self.suit == other.suit and self.rank == other.rank
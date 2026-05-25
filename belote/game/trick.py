from belote.core.card import Card

dict_atout = { 
    "V" : 20,
    "9" : 14,
    "A" : 11,
    "10" : 10,
    "R" : 4,
    "D" : 3,
    "8" : 0,
    "7" : 0      
    }

dict_non_atout = { 
    "A" : 11,
    "10" : 10,
    "R" : 4,
    "D" : 3,
    "V" : 2,
    "9" : 0,
    "8" : 0,
    "7" : 0      
    }

def trick_winner(trick, asked_suit, Trump):
    cards = [card for card in trick if card is not None]
    Trumps = []
    asked_suits = []
    for card in cards:
        if card.suit == Trump:
            Trumps.append(card)
        elif card.suit == asked_suit:
            asked_suits.append(card)
    if len(Trumps) >0:
        return trick.index(best_card(Trumps, True))
    else:
        return trick.index(best_card(asked_suits, False))


        
def best_card(cards, Trump):
    max = cards[0]
    if Trump:
        for card in cards[1:]:
            if dict_atout[max.rank] < dict_atout[card.rank]:
                max = card
        return max
    else:
        for card in cards[1:]:
            if dict_non_atout[max.rank] < dict_non_atout[card.rank]:
                max = card
        return max

    

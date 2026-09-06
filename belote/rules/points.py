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


def card_points(card, Trump):
    if card.suit == Trump:
        return dict_atout[card.rank]
    return dict_non_atout[card.rank]

def trick_points(trick, Trump):
    points = 0
    for card in trick:
        points+= card_points(card, Trump)
    return points

def hand_points(tricks, Trump, dix_de_der):
    res = 0
    for trick in tricks:
        res += trick_points(trick, Trump)
    if dix_de_der:
        res+=10
    return res

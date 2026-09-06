from belote.rules.points import dict_atout, dict_non_atout


def trick_winner(trick, asked_suit, Trump):
    cards = [card for card in trick if card is not None]
    trumps = []
    asked_suits = []
    for card in cards:
        if card.suit == Trump:
            trumps.append(card)
        elif card.suit == asked_suit:
            asked_suits.append(card)
    if trumps:
        return trick.index(best_card(trumps, is_trump=True))
    return trick.index(best_card(asked_suits, is_trump=False))


def best_card(cards, is_trump):
    best = cards[0]
    values = dict_atout if is_trump else dict_non_atout
    for card in cards[1:]:
        if values[best.rank] < values[card.rank]:
            best = card
    return best

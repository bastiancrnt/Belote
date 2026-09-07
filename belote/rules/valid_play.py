Trump_order = ["7", "8", "D", "R", "10", "A", "9", "V"]


def valid_play(hand, suit_asked, trump, partner_is_master, master_card):
    if suit_asked is None:
        return hand

    hand_suits = [card for card in hand if card.suit == suit_asked]

    # --- Couleur demandée == atout ---
    if suit_asked == trump:
        if not hand_suits:
            return hand  # pas d'atout du tout, défausse libre
        up, down = [], []
        for card in hand_suits:
            if Trump_order.index(card.rank) > Trump_order.index(master_card.rank):
                up.append(card)
            else:
                down.append(card)
        return up if up else down  # monter si possible, sinon pisser atout

    # --- Couleur demandée != atout ---
    if hand_suits:
        return hand_suits  # on suit à la couleur

    # Pas de carte à la couleur demandée
    if partner_is_master:
        return hand  # partenaire maître : défausse libre

    hand_trumps = [card for card in hand if card.suit == trump]
    if not hand_trumps:
        return hand  # pas d'atout non plus : défausse libre

    if master_card.suit == trump:
        # Adversaire maître à l'atout : on doit monter si possible
        higher = [
            card for card in hand_trumps
            if Trump_order.index(card.rank) > Trump_order.index(master_card.rank)
        ]
        return higher if higher else hand_trumps  # sinon, pisser atout quand même

    return hand_trumps  # couper

Trump_order = ["7", "8", "D", "R", "10", "A", "9", "V"]

def valid_play(hand, suit_asked, trump, partner_is_master, master_card):
    if suit_asked is None:
        return hand
    hand_suits = []
    for card in hand:
        if card.suit == suit_asked:
            hand_suits.append(card)
    
    if suit_asked == trump:
        hand_trumps_up = []
        hand_trumps_down = []
        for card in hand_suits:
            if Trump_order.index(card.rank) > Trump_order.index(master_card.rank):
                hand_trumps_up.append(card)
            else:
                hand_trumps_down.append(card)

        
        if len(hand_trumps_up) == 0:
            if len(hand_trumps_down)==0:
                return  hand
            return hand_trumps_down
        return hand_trumps_up
    
    if len(hand_suits)==0:
        if partner_is_master:
            return hand
        
        hand_trumps = []
        for card in hand:
            if card.suit == trump:
                hand_trumps.append(card)
        if master_card.suit == trump:
            hand_trumps = [card for card in hand_trumps if Trump_order.index(card.rank) > Trump_order.index(master_card.rank)]
            
        
        if len(hand_trumps)==0:
            return hand
        return hand_trumps
    return hand_suits


    

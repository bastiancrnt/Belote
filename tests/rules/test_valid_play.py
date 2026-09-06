from belote.core.card import Card
from belote.rules.valid_play import valid_play

def test_a_la_couleur_demandee():
    hand = [
        Card("K", "A"),
        Card("K", "V"),
        Card("P", "7"),
    ]
    master_card = Card("K", "R")
    result = valid_play(hand, suit_asked="K", trump="P", partner_is_master=False, master_card=master_card)
    assert len(result) == 2
    assert all(card.suit == "K" for card in result)

def test_partenaire_maitre_defausse_libre():
    hand = [
        Card("K", "A"),
        Card("K", "V"),
        Card("P", "7"),
    ]
    master_card = Card("C","A")
    result = valid_play(hand, suit_asked="C", trump="P", partner_is_master=True, master_card=master_card)
    assert len(result) == 3

def test_partenaire_non_maitre_pas_la_couleur():
    hand = [
        Card("K", "A"),
        Card("K", "7"),
        Card("P", "7"),
    ]
    master_card = Card("C","A")
    result = valid_play(hand, suit_asked="C", trump="K", partner_is_master=False, master_card=master_card)
    assert len(result) == 2

def test_partenaire_non_maitre_pas_la_couleur_adv_coupe():
    hand = [
        Card("K", "A"),
        Card("K", "7"),
        Card("P", "7"),
    ]
    master_card = Card("K","10")
    result = valid_play(hand, suit_asked="C", trump="K", partner_is_master=False, master_card=master_card)
    assert len(result) == 1
    assert result[0] == Card("K", "A")

def test_atout_demande_monte():
    hand = [
        Card("K", "A"),
        Card("K", "7"),
        Card("P", "7"),
    ]
    master_card = Card("K","10")
    result = valid_play(hand, suit_asked="K", trump="K", partner_is_master=False, master_card=master_card)
    assert len(result) == 1
    assert result[0] == Card("K", "A")

def test_atout_demande_pisse():
    hand = [
        Card("K", "A"),
        Card("K", "7"),
        Card("P", "7"),
    ]
    master_card = Card("K","V")
    result = valid_play(hand, suit_asked="K", trump="K", partner_is_master=False, master_card=master_card)
    assert len(result) == 2
    






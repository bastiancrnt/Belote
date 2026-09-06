"""
Conversion cartes moteur → format DB compact (ex: JS, 10H, AC).
Moteur : suit ∈ {C=♦, K=♥, P=♠, T=♣}  rank ∈ {7,8,9,10,V,D,R,A}
DB     : suit ∈ {D,  H,  S,  C }        rank ∈ {7,8,9,10,J,Q,K,A}
"""

_SUIT = {"C": "D", "K": "H", "P": "S", "T": "C"}
_RANK = {"V": "J", "D": "Q", "R": "K",
         "7": "7", "8": "8", "9": "9", "10": "10", "A": "A"}

_SUIT_REV = {v: k for k, v in _SUIT.items()}
_RANK_REV = {v: k for k, v in _RANK.items()}

# trump suit encoding (pour la colonne trump)
TRUMP_ENC = _SUIT


def encode(card) -> str:
    return _RANK[card.rank] + _SUIT[card.suit]


def encode_list(cards) -> list:
    return [encode(c) for c in cards]


def encode_trump(suit: str) -> str:
    return _SUIT.get(suit, suit)

SUIT_SYMBOLS = {"C": "♦", "K": "♥", "P": "♠", "T": "♣"}
SUIT_FROM_SYM = {"♦": "C", "♥": "K", "♠": "P", "♣": "T",
                 "c": "C", "k": "K", "p": "P", "t": "T",
                 "C": "C", "K": "K", "P": "P", "T": "T"}


def _fmt(card):
    return f"{card.rank}{SUIT_SYMBOLS.get(card.suit, card.suit)}"


def _fmt_hand(cards):
    return "  ".join(f"[{i+1}] {_fmt(c)}" for i, c in enumerate(cards))


class HumanAgent:
    def reset_hand(self, trump):
        pass

    def choose_bid(self, hand, current_best, partner_bid=None):
        print(f"\n  Votre main : {_fmt_hand(sorted(hand, key=lambda c: (c.suit, c.rank)))}")
        if partner_bid:
            ps, pp = partner_bid
            print(f"  Partenaire a annoncé : {pp} à {SUIT_SYMBOLS.get(ps, ps)}")
        print(f"  Enchère actuelle : {current_best}")
        print("  Annoncez (ex: 90K pour 90 à ♥, 110P pour 110 à ♠) ou PASSE :")
        while True:
            raw = input("  > ").strip().upper()
            if raw in ("", "PASSE", "P"):
                return None
            # parse ex: "90K", "110 K", "100T"
            raw = raw.replace(" ", "")
            try:
                pts = int(raw[:-1])
                suit_char = raw[-1]
                suit = SUIT_FROM_SYM.get(suit_char)
                if suit is None:
                    raise ValueError
                if pts <= current_best:
                    print(f"  Il faut annoncer plus que {current_best}.")
                    continue
                return suit, pts
            except (ValueError, IndexError):
                print("  Format invalide. Ex: 90K, 110P, PASSE")

    def choose(self, valid_cards, trump=None, context=None):
        leading = context.get("leading", True) if context else True
        partner_is_master = context.get("partner_is_master", False) if context else False
        suit_asked = context.get("suit_asked") if context else None
        trick_so_far = context.get("trick_so_far", []) if context else []

        print(f"\n  Couleur demandée : {SUIT_SYMBOLS.get(suit_asked, '-') if suit_asked else 'vous ouvrez'}")
        if trick_so_far:
            played_str = "  ".join(f"J{p}:{_fmt(c)}" for p, c in trick_so_far)
            status = "partenaire maître" if partner_is_master else "adversaire maître"
            print(f"  Pli en cours ({status}): {played_str}")
        print(f"  Cartes jouables : {_fmt_hand(valid_cards)}")
        while True:
            raw = input("  Votre choix (numéro) > ").strip()
            try:
                idx = int(raw) - 1
                if 0 <= idx < len(valid_cards):
                    return valid_cards[idx]
            except ValueError:
                pass
            print(f"  Entrez un numéro entre 1 et {len(valid_cards)}.")

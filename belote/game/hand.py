from belote.game.trick import trick_winner
from belote.rules.valid_play import valid_play
from belote.rules.points import hand_points, trick_points

import random

SUIT_SYMBOLS = {"C": "♦", "K": "♥", "P": "♠", "T": "♣", "SA": "SA", "TA": "TA"}


def fmt_card(card):
    if card is None:
        return "  --  "
    sym = SUIT_SYMBOLS.get(card.suit, card.suit)
    return f"{card.rank}{sym}"


def fmt_hand(cards):
    return "  ".join(fmt_card(c) for c in cards)


class Hand:
    def __init__(self, hands, trump, contract, agents=None, verbose=False, first_player=0, on_action=None, taker_idx=None):
        self.hands = hands
        self.trump = trump
        self.contract = contract
        self.tricks_won = [[], []]
        self.current_player = first_player
        self.agents = agents
        self.verbose = verbose
        self.played_cards = set()   # cartes tombées dans les plis précédents
        self.tricks_history = []      # [{suit_asked, cards: {player_idx: card}}]
        self.on_action = on_action
        self.taker_idx = taker_idx

    def _pick(self, player_idx, valid_cards, context):
        if self.agents is not None:
            import time
            t0 = time.perf_counter()
            card = self.agents[player_idx].choose(valid_cards, self.trump, context)
            dt = int((time.perf_counter() - t0) * 1000)
            rule = getattr(self.agents[player_idx], "last_rule_used", None)
            if self.on_action is not None:
                # full_hand = vraie main avant de jouer (pas le sous-ensemble valid_cards)
                full_hand = list(self.hands[player_idx])
                self.on_action(player_idx, card, full_hand, valid_cards, context, rule, dt)
            return card
        return random.choice(valid_cards)

    def _build_context(self, player_idx, leading, suit_asked,
                       partner_is_master, master_card, master_player_idx,
                       trick_so_far, trick_num):
        return {
            "player_idx":        player_idx,
            "partner_idx":       (player_idx + 2) % 4,
            "leading":           leading,
            "suit_asked":        suit_asked,
            "partner_is_master": partner_is_master,
            "master_card":       master_card,
            "master_player_idx": master_player_idx,
            "trick_so_far":      trick_so_far,   # [(idx, card), ...]
            "played_cards":      set(self.played_cards),  # snapshot
            "trick_num":         trick_num,
            "tricks_history":    list(self.tricks_history),
            "taker_idx":         self.taker_idx,
            "full_hand":         list(self.hands[player_idx]),
        }

    def play_trick(self, trick_num):
        trick = [None] * 4
        first = self.current_player
        trick_so_far = []

        if self.verbose:
            print(f"\n  --- Pli {trick_num} (J{first} ouvre) ---")
            for p in range(4):
                print(f"  J{p}(eq{p%2}): {fmt_hand(self.hands[p])}")

        # Premier joueur (ouvre)
        ctx = self._build_context(first, True, None, False, None, None, trick_so_far, trick_num)
        chosen = self._pick(first, self.hands[first], ctx)
        trick[first] = chosen
        trick_so_far.append((first, chosen))
        self.hands[first].remove(chosen)
        suit_asked = chosen.suit
        if self.verbose:
            sym = SUIT_SYMBOLS.get(suit_asked, suit_asked)
            print(f"  J{first} joue  : {fmt_card(chosen)}  (couleur demandée: {sym})")

        # Joueurs suivants
        for i in range(1, 4):
            player_idx = (i + first) % 4
            winner_idx = trick_winner(trick, suit_asked, self.trump)
            mastercard = trick[winner_idx]
            partner_is_master = (winner_idx + 2) % 4 == player_idx
            valid_cards = valid_play(
                self.hands[player_idx],
                suit_asked,
                self.trump,
                partner_is_master,
                mastercard,
            )
            ctx = self._build_context(
                player_idx, False, suit_asked,
                partner_is_master, mastercard, winner_idx,
                list(trick_so_far), trick_num
            )
            chosen = self._pick(player_idx, valid_cards, ctx)
            trick[player_idx] = chosen
            trick_so_far.append((player_idx, chosen))
            self.hands[player_idx].remove(chosen)
            if self.verbose:
                print(f"  J{player_idx} joue  : {fmt_card(chosen)}")

        winner = trick_winner(trick, suit_asked, self.trump)
        self.current_player = winner
        self.tricks_won[winner % 2].append(trick)
        trick_record = {
            'suit_asked': suit_asked,
            'cards': {p: trick[p] for p in range(4) if trick[p]},
            'play_sequence': list(trick_so_far),  # [(player_idx, card), ...]
            'winner': trick_winner(trick, suit_asked, self.trump),
        }
        self.tricks_history.append(trick_record)
        for card in trick:
            if card:
                self.played_cards.add(card)

        if self.verbose:
            pts = trick_points(trick, self.trump)
            print(f"  → J{winner}(eq{winner%2}) remporte le pli [{pts} pts] : {fmt_hand(trick)}")

    def play_hand(self, n_tricks=8):
        if self.verbose:
            sym = SUIT_SYMBOLS.get(self.trump, self.trump)
            print(f"  Atout : {sym}  |  Contrat : {self.contract}")

        if self.agents:
            for agent in self.agents:
                if hasattr(agent, "reset_hand"):
                    agent.reset_hand(self.trump)

        for i in range(n_tricks):
            self.play_trick(i + 1)

        dix_eq0 = self.current_player % 2 == 0
        points_eq0 = hand_points(self.tricks_won[0], self.trump, dix_de_der=dix_eq0)
        points_eq1 = hand_points(self.tricks_won[1], self.trump, dix_de_der=not dix_eq0)

        if self.verbose:
            print(f"\n  Dix-de-der : eq{0 if dix_eq0 else 1}")
            print(f"  Eq0 : {points_eq0} pts  |  Eq1 : {points_eq1} pts")

        return points_eq0, points_eq1

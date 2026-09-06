import random
import time
from belote.agents.heuristic_bot_v2 import HeuristicBotV2
from belote.core.card import Card
from belote.game.hand import Hand

RULE_MONTE_CARLO = "MONTE_CARLO"
RULE_MC_FORCED   = "MC_FORCED"

ALL_SUITS = ["K", "P", "C", "T"]
ALL_RANKS = ["7", "8", "D", "R", "10", "A", "9", "V"]
_ALL_CARDS = [Card(s, r) for s in ALL_SUITS for r in ALL_RANKS]
_CARD_INDEX = {(c.suit, c.rank): c for c in _ALL_CARDS}

SMALL_RANKS = {"7", "8", "D", "R"}


class _ForceFirst(HeuristicBotV2):
    """Bot de simulation : joue une carte imposée au premier appel, puis V2."""
    def __init__(self, forced_card):
        super().__init__()
        self._forced_card = forced_card
        self._used = False

    def reset_hand(self, trump):
        super().reset_hand(trump)
        self._used = False

    def choose(self, valid_cards, trump, context):
        if not self._used:
            self._used = True
            if self._forced_card in valid_cards:
                self.last_rule_used = "FORCE_FIRST"
                return self._forced_card
        return super().choose(valid_cards, trump, context)


class MonteCarloBot(HeuristicBotV2):

    BOT_VERSION  = "monte_carlo_v1"
    MC_START_TRICK = 4
    TIME_BUDGET  = 2.0    # secondes par décision MC

    # ──────────────────────────────────────────────────────────────────────
    # Entrée principale
    # ──────────────────────────────────────────────────────────────────────

    def choose(self, valid_cards, trump, context):
        if len(valid_cards) == 1:
            self.last_rule_used = RULE_MC_FORCED
            return valid_cards[0]

        trick_num = context.get("trick_num", 1) if context else 1
        leading   = context.get("leading",   False) if context else False

        if trick_num >= self.MC_START_TRICK and leading and context:
            result = self._mc_choose(valid_cards, trump, context)
            if result is not None:
                return result

        return super().choose(valid_cards, trump, context)

    # ──────────────────────────────────────────────────────────────────────
    # Monte Carlo
    # ──────────────────────────────────────────────────────────────────────

    def _mc_choose(self, valid_cards, trump, context):
        player_idx     = context["player_idx"]
        partner_idx    = context["partner_idx"]
        taker_idx      = context.get("taker_idx")
        tricks_history = context.get("tricks_history", [])
        trick_so_far   = context.get("trick_so_far", [])
        full_hand      = context.get("full_hand", [])
        # bid_points est passé via context si on l'ajoute plus tard ; sinon None
        bid_points     = context.get("bid_points")

        my_team = player_idx % 2

        # Cartes connues
        my_keys     = {(c.suit, c.rank) for c in full_hand}
        played_keys = set()
        for trick in tricks_history:
            for (p, c) in trick.get("play_sequence", []):
                played_keys.add((c.suit, c.rank))
        for (p, c) in trick_so_far:
            played_keys.add((c.suit, c.rank))

        unknown = [c for c in _ALL_CARDS
                   if (c.suit, c.rank) not in my_keys
                   and (c.suit, c.rank) not in played_keys]

        other_players = [(player_idx + i) % 4 for i in [1, 2, 3]]
        hand_sizes = {}
        for p in other_players:
            used = sum(1 for t in tricks_history
                       for (pp, c) in t.get("play_sequence", []) if pp == p)
            used += sum(1 for (pp, c) in trick_so_far if pp == p)
            hand_sizes[p] = len(full_hand) - (len(tricks_history) - sum(
                1 for t in tricks_history
                for (pp, c) in t.get("play_sequence", []) if pp == player_idx
            ))
            # Plus simple : chaque joueur a joué autant de plis que complets
            hand_sizes[p] = 8 - (len(tricks_history) + (
                1 if any(pp == p for pp, c in trick_so_far) else 0
            ))

        if sum(hand_sizes[p] for p in other_players) != len(unknown):
            return None   # incohérence, fallback heuristique

        # Contraintes
        voids    = self._build_voids(tricks_history, trump)
        fixed    = self._build_fixed(taker_idx, trump, bid_points,
                                      my_keys, played_keys, other_players)
        signals  = self._build_signals(tricks_history, trump, player_idx,
                                        my_keys, played_keys)
        min_trump_taker = 4 if (bid_points is not None and bid_points >= 120
                                 and taker_idx in other_players) else 0

        # Scores cumulés par carte candidate
        scores = {id(c): 0 for c in valid_cards}
        counts = {id(c): 0 for c in valid_cards}

        deadline = time.perf_counter() + self.TIME_BUDGET
        while time.perf_counter() < deadline:
            dist = self._sample_distribution(unknown, other_players,
                                              hand_sizes, voids, fixed,
                                              signals, min_trump_taker,
                                              trump, taker_idx)
            if dist is None:
                continue
            for card in valid_cards:
                pts = self._simulate(card, dist, player_idx, other_players,
                                     full_hand, trump,
                                     context.get("bid_points", 80),
                                     taker_idx, trick_so_far)
                if pts is not None:
                    scores[id(card)] += pts[my_team]
                    counts[id(card)] += 1

        best = max(valid_cards,
                   key=lambda c: scores[id(c)] / max(counts[id(c)], 1))
        self.last_rule_used = RULE_MONTE_CARLO
        return best

    # ──────────────────────────────────────────────────────────────────────
    # Contraintes
    # ──────────────────────────────────────────────────────────────────────

    def _build_voids(self, tricks_history, trump):
        voids = {}
        for trick in tricks_history:
            suit_asked = trick["suit_asked"]
            for (pidx, card) in trick.get("play_sequence", []):
                if card.suit != suit_asked:
                    voids.setdefault(pidx, set()).add(suit_asked)
                    if card.suit != trump:
                        voids.setdefault(pidx, set()).add(trump)
        return voids

    def _build_fixed(self, taker_idx, trump, bid_points,
                     my_keys, played_keys, other_players):
        """Cartes quasi-certaines : {(suit, rank): player_idx}"""
        fixed = {}
        if taker_idx is None or taker_idx not in other_players:
            return fixed
        if bid_points is None:
            return fixed
        valet_key = (trump, "V")
        nine_key  = (trump, "9")
        if bid_points >= 80 and valet_key not in my_keys and valet_key not in played_keys:
            fixed[valet_key] = taker_idx
        if bid_points >= 90 and nine_key not in my_keys and nine_key not in played_keys:
            fixed[nine_key] = taker_idx
        if bid_points > 130:
            for rank in ("R", "D"):
                key = (trump, rank)
                if key not in my_keys and key not in played_keys:
                    fixed[key] = taker_idx
        return fixed

    def _build_signals(self, tricks_history, trump, player_idx,
                       my_keys, played_keys):
        """
        Signal d'appel (défausse) : le partenaire du maître courant joue une
        petite carte d'une couleur différente de la couleur demandée, alors
        que son équipe est déjà maître du pli.
        → il a soit l'As de cette couleur-là, soit une chicane.
        Retourne {player_idx: {suit}} pour les signaux dont l'As est inconnu.
        """
        from belote.game.trick import trick_winner
        signals = {}
        for trick in tricks_history:
            seq        = trick.get("play_sequence", [])
            suit_asked = trick.get("suit_asked")
            cards_map  = trick.get("cards", {})
            if len(seq) < 2 or not suit_asked:
                continue
            # Reconstituer le tableau trick[] pour trick_winner
            trick_arr = [None] * 4
            for pidx, card in seq:
                trick_arr[pidx] = card

            for i, (pidx, card) in enumerate(seq):
                if i == 0:
                    continue  # le meneur, pas une défausse
                if pidx == player_idx:
                    continue  # soi-même, pas d'inférence
                if card.suit == suit_asked:
                    continue  # suit la couleur → pas un signal
                if card.suit == trump:
                    continue  # coupe → void déjà géré par _build_voids
                if card.rank not in SMALL_RANKS:
                    continue  # grande carte → pas un signal d'appel

                # Vérifier que son équipe était maître AVANT qu'il joue
                partial = [None] * 4
                for j in range(i):
                    pj, cj = seq[j]
                    partial[pj] = cj
                current_winner = trick_winner(partial, suit_asked, trump)
                if current_winner is None:
                    continue
                if current_winner % 2 != pidx % 2:
                    continue  # son équipe n'est pas maître → pas un signal

                # Signal confirmé : pidx a soit l'As de card.suit, soit chicane
                suit = card.suit
                ace_key = (suit, "A")
                if ace_key not in my_keys and ace_key not in played_keys:
                    signals.setdefault(pidx, set()).add(suit)
        return signals

    # ──────────────────────────────────────────────────────────────────────
    # Sampler
    # ──────────────────────────────────────────────────────────────────────

    def _sample_distribution(self, unknown, other_players,
                              hand_sizes, voids, fixed,
                              signals=None, min_trump_taker=0,
                              trump=None, taker_idx=None):
        """Retourne {player: [cards]} ou None si échec."""
        fixed_keys = set(fixed.keys())
        free = [c for c in unknown if (c.suit, c.rank) not in fixed_keys]

        remaining = {p: hand_sizes[p] for p in other_players}
        assigned  = {p: [] for p in other_players}

        # Placer les cartes fixées (Valet, 9 atout)
        for (suit, rank), p in fixed.items():
            card = _CARD_INDEX.get((suit, rank))
            if card is None or p not in assigned:
                continue
            assigned[p].append(card)
            remaining[p] -= 1
            if remaining[p] < 0:
                return None

        # ── Signaux d'appel : As ou chicane ──
        # Pour chaque signal (player, suit) : 50% on force l'As chez lui,
        # 50% on le rend void dans cette couleur pour ce sample.
        sample_voids = {p: set(s) for p, s in voids.items()}  # copie locale
        if signals:
            for sig_player, sig_suits in signals.items():
                for suit in sig_suits:
                    ace_card = _CARD_INDEX.get((suit, "A"))
                    if ace_card is None or ace_card not in free:
                        continue
                    if random.random() < 0.5:
                        # Hypothèse appel : As chez ce joueur
                        if remaining[sig_player] > 0:
                            assigned[sig_player].append(ace_card)
                            remaining[sig_player] -= 1
                            free = [c for c in free if c is not ace_card]
                    else:
                        # Hypothèse chicane : void dans cette couleur
                        sample_voids.setdefault(sig_player, set()).add(suit)

        # ── 120+ : forcer au moins min_trump_taker atouts chez le preneur ──
        if min_trump_taker > 0 and taker_idx in other_players:
            already = sum(1 for c in assigned[taker_idx] if c.suit == trump)
            needed  = max(0, min_trump_taker - already)
            free_trumps = [c for c in free if c.suit == trump]
            random.shuffle(free_trumps)
            for c in free_trumps[:needed]:
                if remaining[taker_idx] > 0:
                    assigned[taker_idx].append(c)
                    remaining[taker_idx] -= 1
                    free = [fc for fc in free if fc is not c]
                else:
                    return None  # impossible à satisfaire

        # ── Distribuer les cartes libres restantes ──
        random.shuffle(free)
        for card in free:
            eligible = [p for p in other_players
                        if remaining[p] > 0
                        and card.suit not in sample_voids.get(p, set())]
            if not eligible:
                eligible = [p for p in other_players if remaining[p] > 0]
            if not eligible:
                return None
            p = random.choice(eligible)
            assigned[p].append(card)
            remaining[p] -= 1

        return assigned

    # ──────────────────────────────────────────────────────────────────────
    # Simulation d'une fin de donne
    # ──────────────────────────────────────────────────────────────────────

    def _simulate(self, my_card, dist, player_idx, other_players,
                  full_hand, trump, bid_points, taker_idx, trick_so_far):
        """
        Simule la fin de la donne en forçant my_card comme premier coup.
        Retourne [pts_team0, pts_team1] ou None.
        """
        # On garde la main complète — _ForceFirst imposera my_card au 1er appel
        sim_my_hand = list(full_hand)
        n_tricks = len(full_hand)   # plis restants (ex: 5 au trick 4)

        ordered = {player_idx: sim_my_hand}
        for p in other_players:
            ordered[p] = list(dist[p])
        hands_list = [ordered[i] for i in range(4)]

        sim_bots = [HeuristicBotV2() for _ in range(4)]
        sim_bots[player_idx] = _ForceFirst(my_card)

        try:
            h = Hand(hands_list, trump, bid_points,
                     agents=sim_bots,
                     first_player=player_idx,
                     taker_idx=taker_idx)
            pts0, pts1 = h.play_hand(n_tricks=n_tricks)
            return [pts0, pts1]
        except Exception:
            return None

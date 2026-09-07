"""
Variantes V3 Monte Carlo
========================
MonteCarloBotFull      (monte_carlo_full_v1)
    – Pli 4+, toute position dans le pli : Monte-Carlo systématique.
    – Fallback V2 uniquement sur erreur technique de simulation.

MonteCarloBotSelective (monte_carlo_selective_v1)
    – Pli 4+, toute position : Monte-Carlo évalue, mais ne choisit la
      meilleure carte que si l'écart est statistiquement net.
    – Sinon → fallback V2 (règle MONTE_CARLO_UNCERTAIN_V2).

Corrections par rapport à MonteCarloBot (monte_carlo_v1) :
    – Condition `leading` supprimée : MC utilisable quel que soit le rang
      du joueur dans le pli (1er, 2e, 3e, 4e).
    – _simulate() reconstruit correctement un pli déjà commencé
      (trick_so_far non vide).
"""

import math
import time

from belote.agents.heuristic_bot_v2 import HeuristicBotV2
from belote.agents.heuristic_bot_v3 import (
    MonteCarloBot,
    _ForceFirst,
    RULE_MC_FORCED,
    RULE_MONTE_CARLO,
    _ALL_CARDS,
)
from belote.game.hand import Hand
from belote.game.trick import trick_winner
from belote.rules.valid_play import valid_play
from belote.rules.points import trick_points

# Règle DB pour le fallback incertain du bot sélectif
RULE_MC_UNCERTAIN_V2 = "MONTE_CARLO_UNCERTAIN_V2"

# Seuils de confiance (valeurs initiales, à calibrer par benchmark)
_MIN_SCORE_GAP     = 5.0   # écart minimal de score moyen (points)
_CONFIDENCE_FACTOR = 1.5   # multiplicateur sur l'erreur standard combinée


# ─────────────────────────────────────────────────────────────────────────────
# MonteCarloBotFull
# ─────────────────────────────────────────────────────────────────────────────

class MonteCarloBotFull(MonteCarloBot):
    """
    V3 Full MC.

    À partir du pli MC_START_TRICK (4), toutes les décisions non forcées
    utilisent Monte-Carlo, quelle que soit la position dans le pli.
    Fallback V2 uniquement si la simulation ne peut pas s'exécuter.
    """

    BOT_VERSION = "monte_carlo_full_v1"

    # ── Entrée principale ──────────────────────────────────────────────────

    def choose(self, valid_cards, trump, context):
        if len(valid_cards) == 1:
            self.last_rule_used = RULE_MC_FORCED
            return valid_cards[0]

        trick_num = context.get("trick_num", 1) if context else 1

        # MC activé à partir du pli 4, QUELLE QUE SOIT la position
        if trick_num >= self.MC_START_TRICK and context:
            result = self._mc_choose(valid_cards, trump, context)
            if result is not None:
                return result

        # Fallback V2 (erreur technique uniquement)
        return HeuristicBotV2.choose(self, valid_cards, trump, context)

    # ── Simulation corrigée ────────────────────────────────────────────────

    def _simulate(self, my_card, dist, player_idx, other_players,
                  full_hand, trump, bid_points, taker_idx, trick_so_far):
        """
        Simule la fin de la donne en forçant my_card comme premier coup.
        Gère correctement le cas où le pli est déjà commencé
        (trick_so_far non vide : positions 2, 3, 4 dans le pli).
        """
        ordered = {player_idx: list(full_hand)}
        for p in other_players:
            ordered[p] = list(dist[p])

        if trick_so_far:
            return self._simulate_midtrick(
                my_card, ordered, player_idx, other_players,
                trump, bid_points, taker_idx,
                trick_so_far, len(full_hand),
            )

        # ── Cas leading : comportement identique à MonteCarloBot v1 ───────
        hands_list = [ordered[i] for i in range(4)]
        sim_bots   = [HeuristicBotV2() for _ in range(4)]
        sim_bots[player_idx] = _ForceFirst(my_card)
        try:
            h = Hand(
                hands_list, trump, bid_points,
                agents=sim_bots,
                first_player=player_idx,
                taker_idx=taker_idx,
            )
            p0, p1 = h.play_hand(n_tricks=len(full_hand))
            return [p0, p1]
        except Exception:
            return None

    def _simulate_midtrick(self, my_card, ordered, player_idx, other_players,
                           trump, bid_points, taker_idx,
                           trick_so_far, hand_size):
        """
        Complète le pli en cours manuellement, puis délègue les plis
        restants à Hand.play_hand().

        Paramètres
        ----------
        my_card     : carte à forcer pour player_idx
        ordered     : {player: [cards]} — mains simulées (copies)
        hand_size   : len(full_hand) avant de jouer = nombre de plis restants
        trick_so_far: [(player, card), ...] — coups déjà posés ce pli
        """
        trick_leader = trick_so_far[0][0]
        suit_asked   = trick_so_far[0][1].suit

        trick = [None] * 4
        already_played: set = set()
        for p, c in trick_so_far:
            trick[p] = c
            already_played.add(p)

        # Ordre de jeu des joueurs restants dans ce pli
        play_order = [(trick_leader + i) % 4 for i in range(4)]
        remaining  = [p for p in play_order if p not in already_played]

        current_tsf = list(trick_so_far)

        for p in remaining:
            hand  = ordered[p]
            w_idx = trick_winner(trick, suit_asked, trump)
            master        = trick[w_idx] if w_idx is not None else None
            partner_master = (w_idx is not None and (w_idx + 2) % 4 == p)
            valid = valid_play(hand, suit_asked, trump, partner_master, master)
            if not valid:
                valid = hand  # ne devrait pas arriver

            if p == player_idx:
                chosen = my_card if my_card in valid else valid[0]
            else:
                ctx = {
                    "player_idx":        p,
                    "partner_idx":       (p + 2) % 4,
                    "leading":           False,
                    "suit_asked":        suit_asked,
                    "partner_is_master": partner_master,
                    "master_card":       master,
                    "master_player_idx": w_idx,
                    "trick_so_far":      list(current_tsf),
                    "played_cards":      set(),
                    "trick_num":         99,    # valeur non critique pour V2
                    "tricks_history":    [],
                    "taker_idx":         taker_idx,
                    "full_hand":         list(hand),
                }
                chosen = HeuristicBotV2().choose(valid, trump, ctx)

            trick[p] = chosen
            current_tsf.append((p, chosen))
            if chosen in hand:
                hand.remove(chosen)

        # ── Points et gagnant du pli complété ─────────────────────────────
        winner = trick_winner(trick, suit_asked, trump)
        if winner is None:
            return None

        cumpts = [0, 0]
        cumpts[winner % 2] += trick_points(trick, trump)

        n_full = hand_size - 1  # plis COMPLETS restants après ce pli

        if n_full == 0:
            # Ce pli est le dernier → dix-de-der (+10 au gagnant)
            cumpts[winner % 2] += 10
            return cumpts

        # ── Plis complets restants via Hand ──────────────────────────────
        hands_list = [ordered[i] for i in range(4)]
        sim_bots   = [HeuristicBotV2() for _ in range(4)]
        try:
            h = Hand(
                hands_list, trump, bid_points,
                agents=sim_bots,
                first_player=winner,
                taker_idx=taker_idx,
            )
            p0, p1 = h.play_hand(n_tricks=n_full)
            cumpts[0] += p0
            cumpts[1] += p1
        except Exception:
            return None

        return cumpts


# ─────────────────────────────────────────────────────────────────────────────
# MonteCarloBotSelective
# ─────────────────────────────────────────────────────────────────────────────

class MonteCarloBotSelective(MonteCarloBotFull):
    """
    V3 Selective MC.

    Monte-Carlo évalue toutes les cartes admissibles, mais ne supplante V2
    que si l'écart entre la meilleure et la deuxième est statistiquement
    suffisant (delta >= MIN_SCORE_GAP ET delta > CONFIDENCE_FACTOR × SE).

    Si MC est incertain :
      – last_rule_used = MONTE_CARLO_UNCERTAIN_V2
      – la décision est prise par V2
      – self.mc_meta contient les métriques de la simulation
    """

    BOT_VERSION       = "monte_carlo_selective_v1"
    MIN_SCORE_GAP     = _MIN_SCORE_GAP
    CONFIDENCE_FACTOR = _CONFIDENCE_FACTOR

    def _mc_choose(self, valid_cards, trump, context):
        """
        Surcharge de _mc_choose.

        Collecte moyenne + variance par carte, calcule la confiance, et :
          – si confiant  → retourne la meilleure carte (MONTE_CARLO)
          – si incertain → décide via V2, conserve MONTE_CARLO_UNCERTAIN_V2
        """
        player_idx     = context["player_idx"]
        taker_idx      = context.get("taker_idx")
        tricks_history = context.get("tricks_history", [])
        trick_so_far   = context.get("trick_so_far", [])
        full_hand      = context.get("full_hand", [])
        bid_points     = context.get("bid_points")
        my_team        = player_idx % 2

        # ── Cartes inconnues ───────────────────────────────────────────────
        my_keys     = {(c.suit, c.rank) for c in full_hand}
        played_keys: set = set()
        for t in tricks_history:
            for _, c in t.get("play_sequence", []):
                played_keys.add((c.suit, c.rank))
        for _, c in trick_so_far:
            played_keys.add((c.suit, c.rank))

        unknown = [
            c for c in _ALL_CARDS
            if (c.suit, c.rank) not in my_keys
            and (c.suit, c.rank) not in played_keys
        ]

        other_players = [(player_idx + i) % 4 for i in [1, 2, 3]]
        hand_sizes = {
            p: 8 - (
                len(tricks_history)
                + (1 if any(pp == p for pp, _ in trick_so_far) else 0)
            )
            for p in other_players
        }

        if sum(hand_sizes.values()) != len(unknown):
            return None  # incohérence → fallback géré par choose()

        voids   = self._build_voids(tricks_history, trump)
        fixed   = self._build_fixed(
            taker_idx, trump, bid_points, my_keys, played_keys, other_players
        )
        signals = self._build_signals(
            tricks_history, trump, player_idx, my_keys, played_keys
        )
        min_trump_taker = (
            4 if (bid_points is not None and bid_points >= 120
                  and taker_idx in other_players)
            else 0
        )

        # ── Stats par carte : somme, somme², compteur ─────────────────────
        sums    = {id(c): 0.0 for c in valid_cards}
        sums_sq = {id(c): 0.0 for c in valid_cards}
        counts  = {id(c): 0   for c in valid_cards}

        deadline = time.perf_counter() + self.TIME_BUDGET
        while time.perf_counter() < deadline:
            dist = self._sample_distribution(
                unknown, other_players, hand_sizes,
                voids, fixed, signals, min_trump_taker,
                trump, taker_idx,
            )
            if dist is None:
                continue
            for card in valid_cards:
                pts = self._simulate(
                    card, dist, player_idx, other_players,
                    full_hand, trump, bid_points or 80,
                    taker_idx, trick_so_far,
                )
                if pts is not None:
                    v = float(pts[my_team])
                    sums[id(card)]    += v
                    sums_sq[id(card)] += v * v
                    counts[id(card)]  += 1

        # Aucune simulation valide
        if not any(counts[id(c)] > 0 for c in valid_cards):
            return None

        # ── Moyennes ──────────────────────────────────────────────────────
        means = {
            id(c): (sums[id(c)] / counts[id(c)]) if counts[id(c)] > 0 else -1e9
            for c in valid_cards
        }
        ranked = sorted(valid_cards, key=lambda c: means[id(c)], reverse=True)
        best   = ranked[0]

        if len(ranked) == 1:
            self.last_rule_used = RULE_MONTE_CARLO
            return best

        second = ranked[1]
        n1, n2 = counts[id(best)], counts[id(second)]
        m1, m2 = means[id(best)], means[id(second)]
        delta  = m1 - m2

        # ── Écart-type et erreur standard ─────────────────────────────────
        se1 = se2 = 0.0
        if n1 >= 2:
            var1 = max(0.0, sums_sq[id(best)]   / n1 - m1 * m1)
            se1  = math.sqrt(var1 / n1)
        if n2 >= 2:
            var2 = max(0.0, sums_sq[id(second)] / n2 - m2 * m2)
            se2  = math.sqrt(var2 / n2)

        combined_se = math.sqrt(se1 ** 2 + se2 ** 2)

        confident = (
            delta >= self.MIN_SCORE_GAP
            and (combined_se == 0.0
                 or delta > self.CONFIDENCE_FACTOR * combined_se)
        )

        # Métriques stockées pour la DB (accessibles depuis hand.py si besoin)
        self.mc_meta = {
            "best_mean":          round(m1, 2),
            "second_mean":        round(m2, 2),
            "score_gap":          round(delta, 2),
            "best_n_simulations": n1,
            "confidence_metric":  round(
                delta / combined_se if combined_se > 0.0 else float("inf"), 2
            ),
        }

        if confident:
            self.last_rule_used = RULE_MONTE_CARLO
            return best

        # ── Incertain : V2 décide, on conserve la règle MC_UNCERTAIN ──────
        self.last_rule_used = RULE_MC_UNCERTAIN_V2
        v2_card = HeuristicBotV2.choose(self, valid_cards, trump, context)
        # V2 écrase last_rule_used → on le restaure
        self.last_rule_used = RULE_MC_UNCERTAIN_V2
        return v2_card

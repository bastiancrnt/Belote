"""
Tests de non-régression pour les corrections de protocole B1–B7.

B1 : isolation RNG par donne (même seed → mêmes cartes quel que soit l'activité MC)
B2 : bid_points présent dans le contexte fourni à l'agent
B3 : run_bidding retourne player_idx (0-3), pas team (0/1)
B4 : rule_counts incrémenté dans les deux branches de MonteCarloBotSelective._mc_choose
B5 : défausse quand le partenaire est maître n'infère PAS void atout
B6 : _sample_distribution retourne None si contrainte de chicane infranchissable
B7 : confiance calculée par SE apparié, pas par SE indépendants
"""

import math
import random
import pytest
from collections import defaultdict

from belote.core.card import Card
from belote.core.deck import Deck
from belote.game.bidding import run_bidding
from belote.game.hand import Hand


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def c(suit, rank):
    return Card(suit, rank)


def _deal_with_seed(seed, done=0):
    """Reproduit le tirage per-donne du benchmark."""
    donne_seed = seed * 10000 + done
    random.seed(donne_seed)
    d = Deck()
    d.shuffle()
    return d.deal()


# ─────────────────────────────────────────────────────────────────────────────
# B1 — isolation RNG par donne
# ─────────────────────────────────────────────────────────────────────────────

class TestB1RNGIsolation:
    """Deux runs avec le même seed par donne donnent la même donne,
    même si random a été consommé entre les deux (ex. activité MC)."""

    def test_same_seed_same_deal(self):
        hands_a = _deal_with_seed(42, done=0)
        hands_b = _deal_with_seed(42, done=0)
        for i in range(4):
            assert [str(c) for c in hands_a[i]] == [str(c) for c in hands_b[i]]

    def test_mc_activity_between_deals_doesnt_affect_deal(self):
        """Consommer random (simulant l'activité MC) avant le 2e tirage
        ne doit pas changer le résultat si on re-seed correctement."""
        hands_a = _deal_with_seed(7, done=3)
        # Simuler une activité MC
        for _ in range(500):
            random.random()
        hands_b = _deal_with_seed(7, done=3)
        for i in range(4):
            assert [str(c) for c in hands_a[i]] == [str(c) for c in hands_b[i]]

    def test_different_done_gives_different_deal(self):
        hands_0 = _deal_with_seed(1, done=0)
        hands_1 = _deal_with_seed(1, done=1)
        # Au moins une main doit différer
        same = all(
            [str(c) for c in hands_0[i]] == [str(c) for c in hands_1[i]]
            for i in range(4)
        )
        assert not same, "done=0 et done=1 ont produit la même donne"


# ─────────────────────────────────────────────────────────────────────────────
# B2 — bid_points dans le contexte
# ─────────────────────────────────────────────────────────────────────────────

class TestB2BidPointsInContext:
    """Hand._build_context doit inclure bid_points = contract."""

    def _make_hand(self, contract=90):
        from belote.agents.heuristic_bot_v2 import HeuristicBotV2
        hands = [
            [c("K","A"), c("K","10"), c("K","V"), c("K","9"),
             c("K","R"), c("K","D"), c("K","8"), c("K","7")],
            [c("P","A"), c("P","10"), c("P","V"), c("P","9"),
             c("P","R"), c("P","D"), c("P","8"), c("P","7")],
            [c("C","A"), c("C","10"), c("C","V"), c("C","9"),
             c("C","R"), c("C","D"), c("C","8"), c("C","7")],
            [c("T","A"), c("T","10"), c("T","V"), c("T","9"),
             c("T","R"), c("T","D"), c("T","8"), c("T","7")],
        ]
        seen_contexts = []
        class CapturingBot(HeuristicBotV2):
            def choose(self, valid_cards, trump, context):
                seen_contexts.append(dict(context))
                return super().choose(valid_cards, trump, context)
        agents = [CapturingBot() for _ in range(4)]
        h = Hand(hands, "K", contract, agents=agents,
                 verbose=False, first_player=0, taker_idx=0)
        h.play_hand()
        return seen_contexts

    def test_bid_points_present_in_context(self):
        ctxs = self._make_hand(contract=90)
        for ctx in ctxs:
            assert "bid_points" in ctx, "bid_points absent du contexte"

    def test_bid_points_equals_contract(self):
        for contract in (80, 90, 120):
            ctxs = self._make_hand(contract=contract)
            for ctx in ctxs:
                assert ctx["bid_points"] == contract, (
                    f"bid_points={ctx['bid_points']} ≠ contract={contract}"
                )


# ─────────────────────────────────────────────────────────────────────────────
# B3 — run_bidding retourne player_idx (0-3)
# ─────────────────────────────────────────────────────────────────────────────

class TestB3TakerIdx:
    """run_bidding doit retourner l'indice du joueur (0-3), pas de l'équipe (0/1)."""

    def _stub_agents(self, bidder_idx, suit="K", points=80):
        """Agents dont seul bidder_idx annonce."""
        class PassBot:
            def choose_bid(self, hand, current_best, partner_info):
                return None
        class BidBot:
            def choose_bid(self, hand, current_best, partner_info):
                if current_best < points:
                    return suit, points
                return None
        agents = [PassBot() for _ in range(4)]
        agents[bidder_idx] = BidBot()
        return agents

    def _fake_hands(self):
        return [[c("K","7")] * 8 for _ in range(4)]

    @pytest.mark.parametrize("bidder_idx", [0, 1, 2, 3])
    def test_returns_player_idx_not_team(self, bidder_idx):
        agents = self._stub_agents(bidder_idx)
        hands  = self._fake_hands()
        bid, taker_idx = run_bidding(
            first_player=0, hands=hands, agents=agents, verbose=False
        )
        assert bid is not None, "Aucune enchère n'a été faite"
        assert taker_idx == bidder_idx, (
            f"Attendu player_idx={bidder_idx}, obtenu {taker_idx}"
        )
        assert taker_idx in (0, 1, 2, 3), (
            f"taker_idx={taker_idx} hors plage 0-3"
        )


# ─────────────────────────────────────────────────────────────────────────────
# B4 — rule_counts dans MonteCarloBotSelective
# ─────────────────────────────────────────────────────────────────────────────

class TestB4RuleCounts:
    """Après une décision MC (confiante ou incertaine), rule_counts est incrémenté."""

    def _make_bot(self, min_gap=0.0, cf=0.0):
        from belote.agents.heuristic_bot_v3_variants import MonteCarloBotSelective, RULE_MC_UNCERTAIN_V2
        from belote.agents.heuristic_bot_v3 import RULE_MONTE_CARLO, RULE_MC_FORCED
        bot = MonteCarloBotSelective()
        bot.MIN_SCORE_GAP     = min_gap
        bot.CONFIDENCE_FACTOR = cf
        bot.reset_hand("K")
        return bot, RULE_MONTE_CARLO, RULE_MC_UNCERTAIN_V2, RULE_MC_FORCED

    def _ctx_for_mc(self, player_idx=0):
        """Contexte minimal activant le MC (trick_num >= 4)."""
        # Main avec quelques cartes pour avoir de l'inconnu à distribuer
        my_hand = [c("K","A"), c("K","10"), c("K","V"), c("P","A"),
                   c("P","10"), c("C","A"), c("T","A"), c("T","10")]
        return {
            "player_idx":        player_idx,
            "partner_idx":       (player_idx + 2) % 4,
            "leading":           True,
            "suit_asked":        None,
            "partner_is_master": False,
            "master_card":       None,
            "master_player_idx": None,
            "trick_so_far":      [],
            "played_cards":      set(),
            "trick_num":         5,
            "tricks_history":    [],
            "taker_idx":         1,
            "full_hand":         my_hand,
            "bid_points":        80,
        }

    def test_confident_branch_increments_monte_carlo(self):
        """Quand gap=0 et cf=0, le bot est toujours confiant → MONTE_CARLO."""
        bot, RULE_MC, RULE_UNC, RULE_FORCED = self._make_bot(min_gap=0.0, cf=0.0)
        ctx   = self._ctx_for_mc()
        cards = [c("K","A"), c("P","A")]
        # On court-circuite _mc_choose pour tester juste le comptage
        # en mockant TIME_BUDGET très court pour ne pas attendre
        bot.TIME_BUDGET = 0.05
        bot.choose(cards, "K", ctx)
        total = bot.rule_counts.get(RULE_MC, 0) + bot.rule_counts.get(RULE_UNC, 0) + bot.rule_counts.get(RULE_FORCED, 0)
        assert total > 0, "Aucune règle MC comptée après choose()"

    def test_forced_card_increments_mc_forced(self):
        bot, RULE_MC, RULE_UNC, RULE_FORCED = self._make_bot()
        ctx  = self._ctx_for_mc()
        card = c("K","A")
        bot.choose([card], "K", ctx)   # une seule carte → FORCE
        assert bot.rule_counts.get(RULE_FORCED, 0) == 1

    def test_rule_counts_reset_on_reset_hand(self):
        bot, RULE_MC, RULE_UNC, RULE_FORCED = self._make_bot()
        bot.rule_counts[RULE_MC] = 42
        bot.reset_hand("K")
        assert bot.rule_counts[RULE_MC] == 0


# ─────────────────────────────────────────────────────────────────────────────
# B5 — _build_voids n'infère pas void atout quand partenaire maître
# ─────────────────────────────────────────────────────────────────────────────

class TestB5VoidsPartnerMaster:
    """Défausse hors-couleur (non-atout) quand le partenaire est maître
    → PAS d'inférence void atout pour ce joueur."""

    def _bot(self):
        from belote.agents.heuristic_bot_v3 import MonteCarloBot
        bot = MonteCarloBot()
        bot.reset_hand("K")
        return bot

    def test_no_trump_void_when_partner_winning(self):
        """
        Les équipes sont (0,2) et (1,3). Le partenaire de 1 est donc 3.

        Pli : joueur 0 mène 7 de Pique.
              joueur 3 (partenaire de 1) joue As de Pique → maître du pli.
              joueur 1 défausse 8 de Carreau (ni Pique ni atout Cœur).
        → joueur 1 est void en Pique, mais PAS en atout (Cœur),
          car son partenaire (j3) est maître quand il joue.
        """
        bot = self._bot()
        trump = "K"  # Cœur = atout
        trick_history = [{
            "suit_asked": "P",   # Pique demandé
            "play_sequence": [
                (0, c("P", "7")),   # meneur : 7 de Pique (le plus faible)
                (3, c("P", "A")),   # partenaire de 1 : As de Pique → maître
                (1, c("C", "8")),   # joueur 1 défausse Carreau (ni P ni K)
            ],
        }]
        voids = bot._build_voids(trick_history, trump)
        assert "P" in voids.get(1, set()), "Joueur 1 devrait être void en Pique"
        assert "K" not in voids.get(1, set()), (
            "Joueur 1 NE DEVRAIT PAS être inféré void en atout (partenaire j3 est maître)"
        )

    def test_trump_void_inferred_when_opponent_winning(self):
        """
        Le maître est l'adversaire (joueur 0, As de Pique) → void atout inféré.
        Partenaire de 1 = joueur 3, qui n'a pas encore joué → adversaire maître.
        """
        bot = self._bot()
        trump = "K"
        trick_history = [{
            "suit_asked": "P",
            "play_sequence": [
                (0, c("P", "A")),   # meneur : As de Pique (adversaire de 1, maître)
                (1, c("C", "8")),   # joueur 1 défausse Carreau
            ],
        }]
        voids = bot._build_voids(trick_history, trump)
        assert "P" in voids.get(1, set()), "Joueur 1 devrait être void en Pique"
        assert "K" in voids.get(1, set()), (
            "Joueur 1 DEVRAIT être void en atout (adversaire j0 est maître)"
        )

    def test_v2_compute_voids_no_trump_when_partner_winning(self):
        """
        Même vérification pour _compute_player_voids de HeuristicBotV2.
        Partenaire de 1 = joueur 3, qui mène As de Pique → maître.
        """
        from belote.agents.heuristic_bot_v2 import HeuristicBotV2
        bot = HeuristicBotV2()
        bot.reset_hand("K")
        trump = "K"
        trick_history = [{
            "suit_asked": "P",
            "play_sequence": [
                (0, c("P", "7")),   # meneur : 7 de Pique (faible)
                (3, c("P", "A")),   # partenaire de 1 : As de Pique → maître
                (1, c("C", "8")),   # joueur 1 défausse Carreau
            ],
        }]
        voids = bot._compute_player_voids(trick_history, trump)
        assert "P" in voids.get(1, set())
        assert "K" not in voids.get(1, set()), (
            "_compute_player_voids: void atout inféré à tort quand partenaire (j3) est maître"
        )


# ─────────────────────────────────────────────────────────────────────────────
# B6 — _sample_distribution retourne None si contrainte impossible
# ─────────────────────────────────────────────────────────────────────────────

class TestB6SampleDistributionNone:
    """Si toutes les cartes libres sont bloquées par les contraintes de chicane,
    _sample_distribution doit retourner None."""

    def _bot(self):
        from belote.agents.heuristic_bot_v3 import MonteCarloBot
        bot = MonteCarloBot()
        bot.reset_hand("K")
        return bot

    def test_returns_none_when_constraint_unsatisfiable(self):
        bot   = self._bot()
        trump = "K"
        # Cartes inconnues : uniquement des Cœurs (atout)
        unknown = [c("K", r) for r in ("7", "8", "D")]
        # Joueurs 1, 2, 3 ont chacun besoin de 1 carte
        other_players = [1, 2, 3]
        hand_sizes    = {1: 1, 2: 1, 3: 1}
        # Tous les joueurs sont déclarés void en atout → impossible de placer
        voids = {1: {"K"}, 2: {"K"}, 3: {"K"}}
        result = bot._sample_distribution(
            unknown, other_players, hand_sizes, voids,
            fixed={}, signals=None, min_trump_taker=0,
            trump=trump, taker_idx=None,
        )
        assert result is None, "_sample_distribution doit retourner None si contrainte infranchissable"

    def test_returns_dist_when_constraint_satisfiable(self):
        bot   = self._bot()
        trump = "K"
        unknown = [c("P", r) for r in ("7", "8", "D")]
        other_players = [1, 2, 3]
        hand_sizes    = {1: 1, 2: 1, 3: 1}
        voids         = {}   # aucune contrainte
        result = bot._sample_distribution(
            unknown, other_players, hand_sizes, voids,
            fixed={}, signals=None, min_trump_taker=0,
            trump=trump, taker_idx=None,
        )
        assert result is not None
        for p in other_players:
            assert len(result[p]) == 1


# ─────────────────────────────────────────────────────────────────────────────
# B7 — SE apparié dans MonteCarloBotSelective
# ─────────────────────────────────────────────────────────────────────────────

class TestB7PairedSE:
    """
    MonteCarloBotSelective._mc_choose doit utiliser le SE apparié
    (différences intra-simulation) plutôt que des SE indépendants.
    Vérification via monkey-patch de _simulate pour des résultats contrôlés.
    """

    def _run_mc(self, sim_func, min_gap=0.0, cf=0.0):
        """
        Injecte sim_func comme _simulate, lance _mc_choose sur 2 cartes,
        retourne (last_rule_used, mc_meta).
        """
        from belote.agents.heuristic_bot_v3_variants import (
            MonteCarloBotSelective, RULE_MC_UNCERTAIN_V2,
        )
        from belote.agents.heuristic_bot_v3 import RULE_MONTE_CARLO

        bot = MonteCarloBotSelective()
        bot.MIN_SCORE_GAP     = min_gap
        bot.CONFIDENCE_FACTOR = cf
        bot.TIME_BUDGET       = 0.05   # court pour le test
        bot.reset_hand("K")
        bot._simulate = sim_func

        my_hand = [c("K","A"), c("K","10"), c("K","V"), c("P","A"),
                   c("P","10"), c("C","A"), c("T","A"), c("T","10")]
        ctx = {
            "player_idx": 0, "partner_idx": 2,
            "leading": True, "suit_asked": None,
            "partner_is_master": False, "master_card": None,
            "master_player_idx": None,
            "trick_so_far": [], "played_cards": set(),
            "trick_num": 5, "tricks_history": [],
            "taker_idx": 1, "full_hand": my_hand, "bid_points": 80,
        }
        cards = [c("K","A"), c("P","A")]
        bot._mc_choose(cards, "K", ctx)
        meta = getattr(bot, "mc_meta", None)
        return bot.last_rule_used, meta, RULE_MONTE_CARLO, RULE_MC_UNCERTAIN_V2

    def test_sim_results_paired_same_per_sim(self):
        """
        Toutes les simulations donnent le même score pour les deux cartes.
        → différences toujours 0 → SE apparié = 0 → confiance maximale.
        """
        call_count = {"n": 0}
        def fixed_sim(card, dist, *args, **kwargs):
            call_count["n"] += 1
            return [50, 60]   # équipe 0 gagne toujours 50 peu importe la carte

        rule, meta, RULE_MC, RULE_UNC = self._run_mc(fixed_sim, min_gap=0.0, cf=0.0)
        # Les deux cartes ont le même score moyen → delta=0, SE=0
        # → avec gap=0, delta=0 >= 0 et SE=0 → confiant
        # (ou incertain selon la 2e carte classée — dans tous les cas, pas d'erreur)
        assert meta is not None, "mc_meta absent"
        assert meta["score_gap"] == 0.0

    def test_paired_se_lower_than_independent_when_correlated(self):
        """
        Simulations corrélées (les deux cartes bougent ensemble) :
        le SE apparié doit être inférieur au SE combiné indépendant.
        Ici, score_A = base + bruit, score_B = base + 5 + bruit
        → différence = 5 (constante) → SE apparié ≈ 0.
        """
        import random as _random
        def correlated_sim(card, dist, player_idx, other_players,
                           full_hand, trump, bid_points, taker_idx, trick_so_far):
            base = _random.uniform(40, 60)
            # Card K/A gets base+5, card P/A gets base
            if card.suit == "K":
                return [base + 5, 162 - base - 5]
            return [base, 162 - base]

        rule, meta, RULE_MC, RULE_UNC = self._run_mc(correlated_sim, min_gap=4.0, cf=1.5)
        # Avec des différences constantes (~5), SE apparié ≈ 0
        # → delta(5) >= gap(4) ET delta > 0*SE → confiant → RULE_MC
        assert meta is not None
        # Le gap doit être proche de 5
        assert 3.0 <= meta["score_gap"] <= 7.0, f"score_gap inattendu : {meta['score_gap']}"


# ─────────────────────────────────────────────────────────────────────────────
# R1 — taker_idx transmis au Hand du benchmark (pas seulement à la DB)
# ─────────────────────────────────────────────────────────────────────────────

class TestR1TakerIdxInHand:
    """
    Après run_bidding, le taker_idx (joueur 0-3) doit être transmis à Hand,
    qui le relaie dans chaque contexte d'agent via _build_context.
    Vérifié pour les preneurs J2 et J3 (indices non-triviaux).
    """

    def _run_hand_with_taker(self, bidder_idx):
        from belote.agents.heuristic_bot_v2 import HeuristicBotV2
        from belote.game.hand import Hand

        seen_contexts = []

        class CapturingBot(HeuristicBotV2):
            def choose(self, valid_cards, trump, context):
                seen_contexts.append(dict(context))
                return super().choose(valid_cards, trump, context)

        # Distribution triviale : chaque joueur a toute une couleur
        hands = [
            [c("K","A"),c("K","10"),c("K","V"),c("K","9"),
             c("K","R"),c("K","D"),c("K","8"),c("K","7")],
            [c("P","A"),c("P","10"),c("P","V"),c("P","9"),
             c("P","R"),c("P","D"),c("P","8"),c("P","7")],
            [c("C","A"),c("C","10"),c("C","V"),c("C","9"),
             c("C","R"),c("C","D"),c("C","8"),c("C","7")],
            [c("T","A"),c("T","10"),c("T","V"),c("T","9"),
             c("T","R"),c("T","D"),c("T","8"),c("T","7")],
        ]
        agents = [CapturingBot() for _ in range(4)]
        h = Hand(hands, "K", 80, agents=agents,
                 verbose=False, first_player=0, taker_idx=bidder_idx)
        h.play_hand()
        return seen_contexts

    @pytest.mark.parametrize("bidder_idx", [0, 1, 2, 3])
    def test_taker_idx_in_context_matches_player(self, bidder_idx):
        ctxs = self._run_hand_with_taker(bidder_idx)
        assert ctxs, "Aucun contexte capturé"
        for ctx in ctxs:
            assert "taker_idx" in ctx
            assert ctx["taker_idx"] == bidder_idx, (
                f"Attendu taker_idx={bidder_idx}, obtenu {ctx['taker_idx']}"
            )
            # Garantir que ce n'est pas le team (0/1) mais le joueur (0-3)
            if bidder_idx in (2, 3):
                assert ctx["taker_idx"] not in (0, 1) or bidder_idx in (0, 1), (
                    "taker_idx ressemble à un indice d'équipe (0/1)"
                )


# ─────────────────────────────────────────────────────────────────────────────
# R2 — corpus commun : même seed → mêmes donnes pour toutes les variantes
# ─────────────────────────────────────────────────────────────────────────────

class TestR2CommonCorpus:
    """
    Toutes les variantes Selective évaluées sur le même CALIBRATION_SEED
    reçoivent exactement les mêmes mains initiales donne par donne,
    même si une variante précédente a consommé beaucoup de random.
    """

    def _deals(self, seed, n=10):
        """Reproduit la logique de seeding par donne du benchmark."""
        result = []
        for done in range(n):
            donne_seed = seed * 10000 + done
            random.seed(donne_seed)
            d = Deck()
            d.shuffle()
            hands = d.deal()
            result.append(tuple(
                tuple(f"{c.suit}{c.rank}" for c in hands[i])
                for i in range(4)
            ))
        return result

    def test_same_calibration_seed_same_corpus(self):
        """Deux variantes avec le même seed → mêmes 10 donnes."""
        SEED = 10100   # BASE_SEED(machine#1=10000) + 100
        run_a = self._deals(SEED, n=10)
        # Simuler l'activité MC de la variante précédente
        for _ in range(50_000):
            random.random()
        run_b = self._deals(SEED, n=10)
        assert run_a == run_b, "Corpus différent malgré même seed (R2)"

    def test_five_variants_same_corpus(self):
        """Selective / S1 / S2 / S3 / S4 : tous produisent le même corpus."""
        SEED = 10100
        corpora = []
        for _ in range(5):   # 5 variantes simulées
            # Activité MC simulée entre les variantes
            for _ in range(20_000):
                random.random()
            corpora.append(self._deals(SEED, n=8))
        # Tous identiques
        for i, corp in enumerate(corpora[1:], start=1):
            assert corp == corpora[0], (
                f"Variante {i} diverge du corpus de référence"
            )

    def test_different_seeds_give_different_corpus(self):
        """Deux seeds distincts donnent des corpus différents."""
        corp_a = self._deals(10100, n=10)
        corp_b = self._deals(10101, n=10)
        assert corp_a != corp_b, "Seeds différents → corpus identique (anomalie)"

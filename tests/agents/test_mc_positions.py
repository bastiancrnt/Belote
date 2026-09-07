"""
Tests : MonteCarloBotFull et MonteCarloBotSelective
=====================================================
Vérifie que le Monte-Carlo fonctionne correctement aux quatre positions
possibles dans un pli (1er, 2e, 3e, 4e joueur).

État de jeu cohérent au pli 4 (3 plis joués, 5 cartes restantes par joueur) :

  J0 : K7  K8  CV  PV  TV
  J1 : KD  KR  CD  PD  TD
  J2 : K9  K10 CR  PR  TR
  J3 : KV  KA  CA  PA  TA

Plis joués (12 cartes tombées) :
  Pli 1 (C) : C7  C8  C9  C10   → gagnant J3
  Pli 2 (T) : T7  T8  T9  T10   → gagnant J3
  Pli 3 (P) : P7  P8  P9  P10   → gagnant J3

Atout = K (Cœur). Vérifié : sum(hand_sizes) == len(unknown) pour toutes
les positions 1-4 dans le pli.
"""

import pytest
from belote.core.card import Card
from belote.agents.heuristic_bot_v3_variants import (
    MonteCarloBotFull,
    MonteCarloBotSelective,
    RULE_MC_UNCERTAIN_V2,
)
from belote.agents.heuristic_bot_v3 import RULE_MC_FORCED, RULE_MONTE_CARLO


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

TRUMP = "K"   # Cœur atout

def c(suit, rank):
    return Card(suit, rank)


def make_full_bot(budget=0.1):
    bot = MonteCarloBotFull()
    bot.TIME_BUDGET = budget
    return bot


def make_selective_bot(budget=0.1):
    bot = MonteCarloBotSelective()
    bot.TIME_BUDGET = budget
    return bot


def base_context(player_idx, trick_num, trick_so_far, full_hand,
                 tricks_history=None):
    partner_idx = (player_idx + 2) % 4
    leading     = len(trick_so_far) == 0
    suit_asked  = trick_so_far[0][1].suit if trick_so_far else None
    return {
        "player_idx":        player_idx,
        "partner_idx":       partner_idx,
        "leading":           leading,
        "suit_asked":        suit_asked,
        "partner_is_master": False,
        "master_card":       None,
        "master_player_idx": None,
        "trick_so_far":      trick_so_far,
        "played_cards":      set(),
        "trick_num":         trick_num,
        "tricks_history":    tricks_history or [],
        "taker_idx":         0,
        "full_hand":         list(full_hand),
        "bid_points":        90,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Mains cohérentes au pli 4 — 32 cartes partitionnées sans doublon
#
#  Jouées (12) :  C7 C8 C9 C10 | T7 T8 T9 T10 | P7 P8 P9 P10
#  En main (20) : 8 Cœurs + CV CD CR CA + PV PD PR PA + TV TD TR TA
#
#  J0 : K7  K8  CV  PV  TV
#  J1 : KD  KR  CD  PD  TD
#  J2 : K9  K10 CR  PR  TR
#  J3 : KV  KA  CA  PA  TA
# ─────────────────────────────────────────────────────────────────────────────

HAND_J0 = [c("K","7"),  c("K","8"),  c("C","V"),  c("P","V"),  c("T","V")]
HAND_J1 = [c("K","D"),  c("K","R"),  c("C","D"),  c("P","D"),  c("T","D")]
HAND_J2 = [c("K","9"),  c("K","10"), c("C","R"),  c("P","R"),  c("T","R")]
HAND_J3 = [c("K","V"),  c("K","A"),  c("C","A"),  c("P","A"),  c("T","A")]

# Plis précédents (3 plis joués)
TRICK_HISTORY = [
    {
        "suit_asked": "C",
        "play_sequence": [
            (0, c("C","7")), (1, c("C","8")), (2, c("C","9")), (3, c("C","10")),
        ],
        "cards": {0: c("C","7"), 1: c("C","8"), 2: c("C","9"), 3: c("C","10")},
        "winner": 3,
    },
    {
        "suit_asked": "T",
        "play_sequence": [
            (3, c("T","7")), (0, c("T","8")), (1, c("T","9")), (2, c("T","10")),
        ],
        "cards": {3: c("T","7"), 0: c("T","8"), 1: c("T","9"), 2: c("T","10")},
        "winner": 2,
    },
    {
        "suit_asked": "P",
        "play_sequence": [
            (2, c("P","7")), (3, c("P","8")), (0, c("P","9")), (1, c("P","10")),
        ],
        "cards": {2: c("P","7"), 3: c("P","8"), 0: c("P","9"), 1: c("P","10")},
        "winner": 1,
    },
]

TRICK_NUM = 4   # pli 4 → MC doit s'activer


# ─────────────────────────────────────────────────────────────────────────────
# Position 1 : joueur 0 mène le pli (leading)
# ─────────────────────────────────────────────────────────────────────────────

class TestPosition1Leading:

    def test_full_mc_returns_valid_card(self):
        bot = make_full_bot()
        bot.reset_hand(TRUMP)
        hand   = list(HAND_J0)
        ctx    = base_context(0, TRICK_NUM, [], hand, TRICK_HISTORY)
        result = bot.choose(hand, TRUMP, ctx)
        assert result in hand

    def test_full_mc_uses_monte_carlo_rule(self):
        bot = make_full_bot()
        bot.reset_hand(TRUMP)
        hand = list(HAND_J0)
        ctx  = base_context(0, TRICK_NUM, [], hand, TRICK_HISTORY)
        bot.choose(hand, TRUMP, ctx)
        assert bot.last_rule_used in (RULE_MONTE_CARLO, RULE_MC_FORCED)

    def test_selective_returns_valid_card(self):
        bot = make_selective_bot()
        bot.reset_hand(TRUMP)
        hand   = list(HAND_J0)
        ctx    = base_context(0, TRICK_NUM, [], hand, TRICK_HISTORY)
        result = bot.choose(hand, TRUMP, ctx)
        assert result in hand

    def test_selective_rule_is_mc_or_uncertain(self):
        bot = make_selective_bot()
        bot.reset_hand(TRUMP)
        hand = list(HAND_J0)
        ctx  = base_context(0, TRICK_NUM, [], hand, TRICK_HISTORY)
        bot.choose(hand, TRUMP, ctx)
        assert bot.last_rule_used in (
            RULE_MONTE_CARLO, RULE_MC_UNCERTAIN_V2, RULE_MC_FORCED
        )


# ─────────────────────────────────────────────────────────────────────────────
# Position 2 : joueur 1 joue en deuxième
# ─────────────────────────────────────────────────────────────────────────────

class TestPosition2Second:

    @pytest.fixture
    def tsf(self):
        """J0 a joué K7 (atout)."""
        return [(0, c("K", "7"))]

    def test_full_mc_returns_valid_card(self, tsf):
        bot  = make_full_bot()
        bot.reset_hand(TRUMP)
        hand = list(HAND_J1)
        ctx  = base_context(1, TRICK_NUM, tsf, hand, TRICK_HISTORY)
        res  = bot.choose(hand, TRUMP, ctx)
        assert res in hand

    def test_full_mc_rule(self, tsf):
        bot  = make_full_bot()
        bot.reset_hand(TRUMP)
        hand = list(HAND_J1)
        ctx  = base_context(1, TRICK_NUM, tsf, hand, TRICK_HISTORY)
        bot.choose(hand, TRUMP, ctx)
        assert bot.last_rule_used in (RULE_MONTE_CARLO, RULE_MC_FORCED)

    def test_selective_returns_valid_card(self, tsf):
        bot  = make_selective_bot()
        bot.reset_hand(TRUMP)
        hand = list(HAND_J1)
        ctx  = base_context(1, TRICK_NUM, tsf, hand, TRICK_HISTORY)
        res  = bot.choose(hand, TRUMP, ctx)
        assert res in hand

    def test_simulate_midtrick_position2_no_crash(self, tsf):
        """_simulate() ne doit pas lever d'exception en position 2."""
        bot = make_full_bot()
        my_card = c("K", "D")
        # J0 a joué K7 → il lui reste [K8, CV, PV, TV]
        dist = {
            2: list(HAND_J2),
            3: list(HAND_J3),
            0: [c("K","8"), c("C","V"), c("P","V"), c("T","V")],
        }
        result = bot._simulate(
            my_card, dist, 1, [2, 3, 0],
            list(HAND_J1), TRUMP, 90, 0, tsf,
        )
        assert result is None or (isinstance(result, list) and len(result) == 2)


# ─────────────────────────────────────────────────────────────────────────────
# Position 3 : joueur 2 joue en troisième
# ─────────────────────────────────────────────────────────────────────────────

class TestPosition3Third:

    @pytest.fixture
    def tsf(self):
        """J0 → K7, J1 → KD."""
        return [(0, c("K", "7")), (1, c("K", "D"))]

    def test_full_mc_returns_valid_card(self, tsf):
        bot  = make_full_bot()
        bot.reset_hand(TRUMP)
        hand = list(HAND_J2)
        ctx  = base_context(2, TRICK_NUM, tsf, hand, TRICK_HISTORY)
        res  = bot.choose(hand, TRUMP, ctx)
        assert res in hand

    def test_full_mc_rule(self, tsf):
        bot  = make_full_bot()
        bot.reset_hand(TRUMP)
        hand = list(HAND_J2)
        ctx  = base_context(2, TRICK_NUM, tsf, hand, TRICK_HISTORY)
        bot.choose(hand, TRUMP, ctx)
        assert bot.last_rule_used in (RULE_MONTE_CARLO, RULE_MC_FORCED)

    def test_selective_returns_valid_card(self, tsf):
        bot  = make_selective_bot()
        bot.reset_hand(TRUMP)
        hand = list(HAND_J2)
        ctx  = base_context(2, TRICK_NUM, tsf, hand, TRICK_HISTORY)
        res  = bot.choose(hand, TRUMP, ctx)
        assert res in hand

    def test_simulate_midtrick_position3_no_crash(self, tsf):
        bot = make_full_bot()
        my_card = c("K", "9")
        # J0 a joué K7, J1 a joué KD
        dist = {
            3: list(HAND_J3),
            0: [c("K","8"), c("C","V"), c("P","V"), c("T","V")],
            1: [c("K","R"), c("C","D"), c("P","D"), c("T","D")],
        }
        result = bot._simulate(
            my_card, dist, 2, [3, 0, 1],
            list(HAND_J2), TRUMP, 90, 0, tsf,
        )
        assert result is None or (isinstance(result, list) and len(result) == 2)


# ─────────────────────────────────────────────────────────────────────────────
# Position 4 : joueur 3 joue en dernier
# ─────────────────────────────────────────────────────────────────────────────

class TestPosition4Last:

    @pytest.fixture
    def tsf(self):
        """J0→K7, J1→KD, J2→K9."""
        return [
            (0, c("K", "7")),
            (1, c("K", "D")),
            (2, c("K", "9")),
        ]

    def test_full_mc_returns_valid_card(self, tsf):
        bot  = make_full_bot()
        bot.reset_hand(TRUMP)
        hand = list(HAND_J3)
        ctx  = base_context(3, TRICK_NUM, tsf, hand, TRICK_HISTORY)
        res  = bot.choose(hand, TRUMP, ctx)
        assert res in hand

    def test_full_mc_rule(self, tsf):
        bot  = make_full_bot()
        bot.reset_hand(TRUMP)
        hand = list(HAND_J3)
        ctx  = base_context(3, TRICK_NUM, tsf, hand, TRICK_HISTORY)
        bot.choose(hand, TRUMP, ctx)
        assert bot.last_rule_used in (RULE_MONTE_CARLO, RULE_MC_FORCED)

    def test_selective_returns_valid_card(self, tsf):
        bot  = make_selective_bot()
        bot.reset_hand(TRUMP)
        hand = list(HAND_J3)
        ctx  = base_context(3, TRICK_NUM, tsf, hand, TRICK_HISTORY)
        res  = bot.choose(hand, TRUMP, ctx)
        assert res in hand

    def test_simulate_midtrick_position4_no_crash(self, tsf):
        bot = make_full_bot()
        my_card = c("K", "V")
        # J0 a joué K7, J1 KD, J2 K9
        dist = {
            0: [c("K","8"), c("C","V"), c("P","V"), c("T","V")],
            1: [c("K","R"), c("C","D"), c("P","D"), c("T","D")],
            2: [c("K","10"), c("C","R"), c("P","R"), c("T","R")],
        }
        result = bot._simulate(
            my_card, dist, 3, [0, 1, 2],
            list(HAND_J3), TRUMP, 90, 0, tsf,
        )
        assert result is None or (isinstance(result, list) and len(result) == 2)


# ─────────────────────────────────────────────────────────────────────────────
# Tests MC désactivé avant le pli 4
# ─────────────────────────────────────────────────────────────────────────────

class TestMCNotBeforeTrick4:

    def test_full_mc_uses_v2_at_trick1(self):
        """Pli 1 : V2 doit décider, pas MC."""
        bot = make_full_bot()
        bot.reset_hand(TRUMP)
        hand = [c("K","7"), c("K","8"), c("C","V")]
        ctx  = base_context(0, 1, [], hand)
        bot.choose(hand, TRUMP, ctx)
        assert bot.last_rule_used != RULE_MONTE_CARLO

    def test_full_mc_uses_v2_at_trick3(self):
        bot = make_full_bot()
        bot.reset_hand(TRUMP)
        hand = [c("K","7"), c("K","8"), c("C","V")]
        ctx  = base_context(0, 3, [], hand)
        bot.choose(hand, TRUMP, ctx)
        assert bot.last_rule_used != RULE_MONTE_CARLO


# ─────────────────────────────────────────────────────────────────────────────
# Test carte forcée (1 seule carte admissible)
# ─────────────────────────────────────────────────────────────────────────────

class TestForcedCard:

    def test_full_mc_forced_single_card(self):
        bot = make_full_bot()
        bot.reset_hand(TRUMP)
        only = [c("K", "V")]
        ctx  = base_context(0, 5, [], only)
        res  = bot.choose(only, TRUMP, ctx)
        assert res == only[0]
        assert bot.last_rule_used == RULE_MC_FORCED

    def test_selective_forced_single_card(self):
        bot = make_selective_bot()
        bot.reset_hand(TRUMP)
        only = [c("K", "V")]
        ctx  = base_context(0, 5, [], only)
        res  = bot.choose(only, TRUMP, ctx)
        assert res == only[0]
        assert bot.last_rule_used == RULE_MC_FORCED


# ─────────────────────────────────────────────────────────────────────────────
# Test mc_meta disponible après décision Selective incertaine
# ─────────────────────────────────────────────────────────────────────────────

class TestSelectiveMeta:

    def test_mc_meta_populated_on_uncertain(self):
        """
        Avec un budget très court, la confiance est souvent insuffisante.
        On vérifie juste que mc_meta existe et a la bonne structure si MC a tourné.
        """
        bot = make_selective_bot(budget=0.02)
        bot.reset_hand(TRUMP)
        hand = list(HAND_J0)
        ctx  = base_context(0, TRICK_NUM, [], hand, TRICK_HISTORY)
        bot.choose(hand, TRUMP, ctx)

        if bot.last_rule_used == RULE_MC_UNCERTAIN_V2:
            meta = getattr(bot, "mc_meta", None)
            assert meta is not None
            for key in ("best_mean", "second_mean", "score_gap",
                        "best_n_simulations", "confidence_metric"):
                assert key in meta, f"Clé manquante dans mc_meta : {key}"

"""
Tests : HeuristicBotV2_2 — 7 nouvelles règles
==============================================
Au moins 2 cas par règle (trigger / no-trigger).
Chaque test vérifie la carte choisie ET last_rule_used.
"""

import pytest
from belote.core.card import Card
from belote.agents.heuristic_bot_v2_2 import (
    HeuristicBotV2_2,
    RULE_DRAW_LAST_BEATABLE_TRUMP,
    RULE_AVOID_WASTING_TRUMP_ON_PARTNER,
    RULE_GIVE_POINTS_SMART,
    RULE_RETURN_PARTNER_SUIT,
    RULE_SECURE_LAST_TRICK,
    RULE_AVOID_RISKY_TEN,
    RULE_DISCARD_CREATE_VOID,
)
from belote.agents.heuristic_bot import RULE_DISCARD_MINIMUM, RULE_GIVE_POINTS


def c(suit, rank):
    return Card(suit, rank)


TRUMP = "K"   # Cœur = atout dans tous les tests


def _ctx(player_idx=0, partner_idx=2, leading=True, suit_asked=None,
         partner_is_master=False, master_card=None, master_player_idx=None,
         trick_so_far=None, played_cards=None, trick_num=1,
         tricks_history=None, taker_idx=None, full_hand=None, bid_points=80):
    """Crée un contexte minimal pour les tests."""
    return {
        "player_idx": player_idx,
        "partner_idx": partner_idx,
        "leading": leading,
        "suit_asked": suit_asked,
        "partner_is_master": partner_is_master,
        "master_card": master_card,
        "master_player_idx": master_player_idx,
        "trick_so_far": trick_so_far or [],
        "played_cards": played_cards or [],
        "trick_num": trick_num,
        "tricks_history": tricks_history or [],
        "taker_idx": taker_idx,
        "full_hand": full_hand or [],
        "bid_points": bid_points,
    }


def _history_already_signaled(suit, player_idx=0):
    """
    Crée un historique où player_idx a joué une petite carte dans `suit`
    (défausse hors-couleur demandée), marquant la couleur comme déjà signalée
    dans _detect_my_signals_sent().
    """
    return [{
        "suit_asked": "P",   # couleur demandée différente
        "cards": {
            player_idx: c(suit, "7"),
            (player_idx + 1) % 4: c("P", "8"),
            (player_idx + 2) % 4: c("P", "A"),
            (player_idx + 3) % 4: c("P", "9"),
        },
        "play_sequence": [
            ((player_idx + 2) % 4, c("P", "A")),
            ((player_idx + 3) % 4, c("P", "9")),
            (player_idx, c(suit, "7")),
            ((player_idx + 1) % 4, c("P", "8")),
        ],
        "winner": (player_idx + 2) % 4,
    }]


# ═══════════════════════════════════════════════════════════════════
# RULE 1 — DRAW_LAST_BEATABLE_TRUMP
# ═══════════════════════════════════════════════════════════════════

class TestDrawLastBeatableTrump:

    def test_trigger_draws_last_trump(self):
        """
        Un seul atout reste (le 10) + partenaire connu vide en atout
        → seul un adversaire peut avoir ce 10 → on tire avec le 9.
        """
        bot = HeuristicBotV2_2()
        bot.reset_hand(TRUMP)

        hand = [c(TRUMP, "V"), c(TRUMP, "9"), c("C", "A"), c("P", "8")]
        played = [
            c(TRUMP, "A"), c(TRUMP, "R"), c(TRUMP, "D"),
            c(TRUMP, "8"), c(TRUMP, "7"),
        ]
        # Partenaire J2 a défaussé hors-atout sur un pli atout → connu vide en atout
        history = [{
            "suit_asked": TRUMP,
            "cards": {0: c(TRUMP, "A"), 1: c(TRUMP, "R"), 2: c("C", "7"), 3: c(TRUMP, "D")},
            "play_sequence": [
                (0, c(TRUMP, "A")), (1, c(TRUMP, "R")),
                (2, c("C", "7")), (3, c(TRUMP, "D")),
            ],
            "winner": 0,
        }]
        ctx = _ctx(player_idx=0, partner_idx=2, leading=True,
                   played_cards=played, full_hand=hand, tricks_history=history)
        valid = hand

        result = bot.choose(valid, TRUMP, ctx)
        assert bot.last_rule_used == RULE_DRAW_LAST_BEATABLE_TRUMP
        assert result.rank == "9"   # minimum battant le 10

    def test_no_trigger_multiple_remaining(self):
        """Plusieurs atouts adverses restent → règle non déclenchée."""
        bot = HeuristicBotV2_2()
        bot.reset_hand(TRUMP)

        hand = [c(TRUMP, "V"), c(TRUMP, "9"), c("C", "A")]
        played = [c(TRUMP, "7")]  # seulement le 7 tombé
        ctx = _ctx(leading=True, played_cards=played, full_hand=hand)
        valid = hand

        bot.choose(valid, TRUMP, ctx)
        assert bot.last_rule_used != RULE_DRAW_LAST_BEATABLE_TRUMP

    def test_no_trigger_cannot_beat(self):
        """Dernier atout restant est le V → on ne peut pas le battre."""
        bot = HeuristicBotV2_2()
        bot.reset_hand(TRUMP)

        # On n'a que le 9 ; le V reste chez l'adversaire
        hand = [c(TRUMP, "9"), c("C", "A"), c("P", "8")]
        played = [
            c(TRUMP, "A"), c(TRUMP, "10"), c(TRUMP, "R"),
            c(TRUMP, "D"), c(TRUMP, "8"), c(TRUMP, "7"),
        ]
        ctx = _ctx(leading=True, played_cards=played, full_hand=hand)
        valid = hand

        bot.choose(valid, TRUMP, ctx)
        assert bot.last_rule_used != RULE_DRAW_LAST_BEATABLE_TRUMP

    def test_no_trigger_partner_may_have_last_trump(self):
        """
        Un seul atout reste (le 10) mais le partenaire n'est PAS connu vide
        en atout → il pourrait avoir ce 10. La règle ne doit pas se déclencher.
        """
        bot = HeuristicBotV2_2()
        bot.reset_hand(TRUMP)

        hand = [c(TRUMP, "V"), c(TRUMP, "9"), c("C", "A")]
        played = [
            c(TRUMP, "A"), c(TRUMP, "R"), c(TRUMP, "D"),
            c(TRUMP, "8"), c(TRUMP, "7"),
        ]
        # Pas de tricks_history → _voids = {} → partenaire non connu vide en atout
        ctx = _ctx(leading=True, played_cards=played, full_hand=hand,
                   tricks_history=[])
        valid = hand

        bot.choose(valid, TRUMP, ctx)
        assert bot.last_rule_used != RULE_DRAW_LAST_BEATABLE_TRUMP

    def test_trigger_requires_partner_known_void(self):
        """
        Un seul atout reste (le 10) ET le partenaire est connu vide en atout
        (il a défaussé sur un pli atout) → la règle se déclenche.
        """
        bot = HeuristicBotV2_2()
        bot.reset_hand(TRUMP)

        hand = [c(TRUMP, "V"), c(TRUMP, "9"), c("C", "A")]
        played = [
            c(TRUMP, "A"), c(TRUMP, "R"), c(TRUMP, "D"),
            c(TRUMP, "8"), c(TRUMP, "7"),
        ]
        # Partenaire (J2) a défaussé hors-atout sur un pli atout
        # → _compute_player_voids met J2 vide en atout
        history = [{
            "suit_asked": TRUMP,
            "cards": {
                0: c(TRUMP, "A"),
                1: c(TRUMP, "R"),
                2: c("C", "7"),   # partenaire J2 défausse → vide en atout
                3: c(TRUMP, "D"),
            },
            "play_sequence": [
                (0, c(TRUMP, "A")), (1, c(TRUMP, "R")),
                (2, c("C", "7")), (3, c(TRUMP, "D")),
            ],
            "winner": 0,
        }]
        ctx = _ctx(
            player_idx=0, partner_idx=2,
            leading=True, played_cards=played,
            tricks_history=history,
        )
        valid = hand

        result = bot.choose(valid, TRUMP, ctx)
        assert bot.last_rule_used == RULE_DRAW_LAST_BEATABLE_TRUMP
        assert result.rank == "9"   # minimum qui bat le 10


# ═══════════════════════════════════════════════════════════════════
# RULE 2 — AVOID_WASTING_TRUMP_ON_PARTNER
# ═══════════════════════════════════════════════════════════════════

class TestAvoidWastingTrumpOnPartner:

    def test_trigger_plays_small_trump_not_big(self):
        """
        Partenaire est maître, on est forcé en atout (pas de non-atout valide),
        on a V d'atout et 8 d'atout → jouer le 8 (pas le V).
        """
        bot = HeuristicBotV2_2()
        bot.reset_hand(TRUMP)

        valid = [c(TRUMP, "V"), c(TRUMP, "8")]
        ctx = _ctx(
            leading=False,
            suit_asked="C",
            partner_is_master=True,
            master_card=c("C", "A"),
            master_player_idx=2,
            trick_so_far=[(2, c("C", "A"))],
        )
        result = bot.choose(valid, TRUMP, ctx)
        assert bot.last_rule_used == RULE_AVOID_WASTING_TRUMP_ON_PARTNER
        assert result.rank == "8"

    def test_no_trigger_has_non_trump(self):
        """
        Partenaire est maître, mais on a des cartes hors-atout disponibles
        → on ne déclenche pas AVOID_WASTING_TRUMP.
        """
        bot = HeuristicBotV2_2()
        bot.reset_hand(TRUMP)

        valid = [c(TRUMP, "V"), c("C", "7")]
        ctx = _ctx(
            leading=False,
            suit_asked="C",
            partner_is_master=True,
            master_card=c("C", "A"),
            master_player_idx=2,
            trick_so_far=[(2, c("C", "A"))],
        )
        result = bot.choose(valid, TRUMP, ctx)
        assert bot.last_rule_used != RULE_AVOID_WASTING_TRUMP_ON_PARTNER


# ═══════════════════════════════════════════════════════════════════
# RULE 3 — GIVE_POINTS_SMART
# ═══════════════════════════════════════════════════════════════════

class TestGivePointsSmart:

    def test_trigger_isolated_ten_preferred(self):
        """
        Partenaire est maître ; on a un 10 isolé (sans As dans sa couleur)
        et un As seul dans une autre couleur (1 carte → pas de SIGNAL_ACE).
        → joue le 10 isolé (priorité 1).
        """
        bot = HeuristicBotV2_2()
        bot.reset_hand(TRUMP)

        # C10 isolé (pas d'As en C), PA seul (len=1 → pas de SIGNAL_ACE)
        valid = [c("C", "10"), c("P", "A")]
        ctx = _ctx(
            leading=False,
            suit_asked="T",
            partner_is_master=True,
            master_card=c(TRUMP, "V"),
            master_player_idx=2,
            trick_so_far=[(2, c(TRUMP, "V"))],
        )
        result = bot.choose(valid, TRUMP, ctx)
        assert bot.last_rule_used == RULE_GIVE_POINTS_SMART
        assert result == c("C", "10")

    def test_trigger_pair_gives_ten_not_ace(self):
        """
        Partenaire est maître ; on a As+10 en C (déjà signalé → SIGNAL_ACE ignoré)
        → donne le 10, pas l'As (priorité 3).
        """
        bot = HeuristicBotV2_2()
        bot.reset_hand(TRUMP)

        # Marquer C comme déjà signalé (player 0 a joué C7 en défausse avant)
        history = _history_already_signaled("C", player_idx=0)
        valid = [c("C", "A"), c("C", "10")]
        ctx = _ctx(
            leading=False,
            suit_asked="T",
            partner_is_master=True,
            master_card=c(TRUMP, "V"),
            master_player_idx=2,
            trick_so_far=[(2, c(TRUMP, "V"))],
            tricks_history=history,
        )
        result = bot.choose(valid, TRUMP, ctx)
        assert bot.last_rule_used == RULE_GIVE_POINTS_SMART
        assert result.rank == "10"

    def test_trigger_isolated_ace_over_pair(self):
        """
        On a un As isolé en T ET une paire As+10 en C (déjà signalée)
        → As isolé préféré (priorité 2).
        """
        bot = HeuristicBotV2_2()
        bot.reset_hand(TRUMP)

        history = _history_already_signaled("C", player_idx=0)
        valid = [c("T", "A"), c("C", "A"), c("C", "10")]
        ctx = _ctx(
            leading=False,
            suit_asked="P",
            partner_is_master=True,
            master_card=c(TRUMP, "V"),
            master_player_idx=2,
            trick_so_far=[(2, c(TRUMP, "V"))],
            tricks_history=history,
        )
        result = bot.choose(valid, TRUMP, ctx)
        assert bot.last_rule_used == RULE_GIVE_POINTS_SMART
        # T a un As isolé (priorité 2) ; C a paire (priorité 3) → T préféré
        assert result == c("T", "A")


# ═══════════════════════════════════════════════════════════════════
# RULE 4 — RETURN_PARTNER_SUIT
# ═══════════════════════════════════════════════════════════════════

class TestReturnPartnerSuit:

    def _history_partner_led_ace(self, suit="C", partner_idx=2):
        """Crée un historique où le partenaire a ouvert le premier pli avec l'As."""
        return [{
            "suit_asked": suit,
            "cards": {
                partner_idx: c(suit, "A"),
                0: c(suit, "7"),
                1: c(suit, "8"),
                3: c(suit, "9"),
            },
            "play_sequence": [
                (partner_idx, c(suit, "A")),
                (0, c(suit, "7")),
                (1, c(suit, "8")),
                (3, c(suit, "9")),
            ],
            "winner": partner_idx,
        }]

    def test_trigger_returns_partner_suit(self):
        """Partenaire a ouvert en As de Trèfle → on retourne Trèfle."""
        bot = HeuristicBotV2_2()
        bot.reset_hand(TRUMP)

        history = self._history_partner_led_ace("C", partner_idx=2)
        valid = [c("C", "R"), c("P", "8"), c("T", "7")]
        ctx = _ctx(leading=True, tricks_history=history)
        result = bot.choose(valid, TRUMP, ctx)
        assert bot.last_rule_used == RULE_RETURN_PARTNER_SUIT
        assert result.suit == "C"

    def test_no_trigger_no_partner_ace_open(self):
        """Partenaire n'a jamais ouvert en As → règle non déclenchée."""
        bot = HeuristicBotV2_2()
        bot.reset_hand(TRUMP)

        history = [{
            "suit_asked": "C",
            "cards": {0: c("C", "A"), 2: c("C", "7")},
            "play_sequence": [(0, c("C", "A")), (2, c("C", "7"))],
            "winner": 0,
        }]
        valid = [c("C", "R"), c("P", "8"), c("T", "7")]
        ctx = _ctx(leading=True, tricks_history=history)
        bot.choose(valid, TRUMP, ctx)
        assert bot.last_rule_used != RULE_RETURN_PARTNER_SUIT

    def test_trigger_three_card_sequence_no_enemy_trumps(self):
        """
        On a 3 cartes dans la couleur du partenaire (A, 10, R) et
        aucun atout adverse → jouer le plus petit d'abord (séquence petit→A→10).
        """
        bot = HeuristicBotV2_2()
        bot.reset_hand(TRUMP)

        history = self._history_partner_led_ace("C", partner_idx=2)
        # Tous les atouts tombés → enemy_trumps = 0
        all_trump = [c(TRUMP, r) for r in ["V", "9", "A", "10", "R", "D", "8", "7"]]
        valid = [c("C", "A"), c("C", "10"), c("C", "R")]
        ctx = _ctx(leading=True, tricks_history=history, played_cards=all_trump)
        result = bot.choose(valid, TRUMP, ctx)
        assert bot.last_rule_used == RULE_RETURN_PARTNER_SUIT
        assert result.rank == "R"   # petite carte d'abord


# ═══════════════════════════════════════════════════════════════════
# RULE 5 — SECURE_LAST_TRICK
# ═══════════════════════════════════════════════════════════════════

class TestSecureLastTrick:

    def test_trigger_trick7_leading_preserve_trump(self):
        """
        Pli 7, ouverture, 2 cartes : V atout (dominant) + non-atout.
        → jouer le non-atout maintenant, garder le V pour le dix-de-der.
        """
        bot = HeuristicBotV2_2()
        bot.reset_hand(TRUMP)

        valid = [c(TRUMP, "V"), c("C", "8")]
        # Tous les autres atouts tombés → V domine tout
        played = [c(TRUMP, r) for r in ["9", "A", "10", "R", "D", "8", "7"]]
        ctx = _ctx(leading=True, trick_num=7, played_cards=played)
        result = bot.choose(valid, TRUMP, ctx)
        assert bot.last_rule_used == RULE_SECURE_LAST_TRICK
        assert result == c("C", "8")   # jouer le non-atout, garder le V

    def test_no_trigger_trick7_trump_not_dominant(self):
        """
        Pli 7, atout présent mais le V adverse n'est pas tombé
        → SECURE_LAST_TRICK ne se déclenche pas.
        """
        bot = HeuristicBotV2_2()
        bot.reset_hand(TRUMP)

        valid = [c(TRUMP, "9"), c("C", "8")]
        # V d'atout encore dans la nature
        played = [c(TRUMP, r) for r in ["A", "10", "R", "D", "8", "7"]]
        ctx = _ctx(leading=True, trick_num=7, played_cards=played)
        bot.choose(valid, TRUMP, ctx)
        assert bot.last_rule_used != RULE_SECURE_LAST_TRICK

    def test_no_trigger_only_one_card(self):
        """
        Une seule carte en main → pas d'optimisation possible.
        """
        bot = HeuristicBotV2_2()
        bot.reset_hand(TRUMP)

        valid = [c(TRUMP, "V")]
        ctx = _ctx(leading=True, trick_num=8)
        bot.choose(valid, TRUMP, ctx)
        assert bot.last_rule_used != RULE_SECURE_LAST_TRICK


# ═══════════════════════════════════════════════════════════════════
# RULE 6 — AVOID_RISKY_TEN
# ═══════════════════════════════════════════════════════════════════

class TestAvoidRiskyTen:

    def test_trigger_avoids_risky_ten(self):
        """
        V2 choisit normalement C10 (10-maître, As tombé, pas d'atouts restants).
        Mais J1 est chicane en C avec de l'atout disponible (il a coupé avant).
        → AVOID_RISKY_TEN intercepte et joue CR à la place.
        """
        bot = HeuristicBotV2_2()
        bot.reset_hand(TRUMP)

        # Trick historique : J1 a coupé (joué atout) quand C était demandé
        # → _voids[1] = {"C"} (chicane C) mais pas vide en atout
        history = [{
            "suit_asked": "C",
            "cards": {
                0: c("C", "A"),
                1: c(TRUMP, "7"),   # J1 coupe → chicane C, pas vide en atout
                2: c("C", "9"),
                3: c("C", "8"),
            },
            "play_sequence": [
                (0, c("C", "A")),
                (1, c(TRUMP, "7")),
                (2, c("C", "9")),
                (3, c("C", "8")),
            ],
            "winner": 1,
        }]

        # played_cards : As de C + les 8 atouts (dont K7 joué par J1)
        # → enemy_trumps_left = 0 (tous en joués ou en main adverse... mais
        #   aucun dans mes valid_cards non plus, donc remaining = {})
        played = [c("C", "A"), c("C", "9"), c("C", "8"), c(TRUMP, "7")] + \
                 [c(TRUMP, r) for r in ["V", "9", "A", "10", "R", "D", "8"]]

        # valid : C10 (maître car As de C tombé + 0 atout restant) et CR
        # Pas de singleton → CREATE_VOID ne se déclenchera pas
        valid = [c("C", "10"), c("C", "R")]

        ctx = _ctx(
            leading=True,
            tricks_history=history,
            played_cards=played,
        )
        result = bot.choose(valid, TRUMP, ctx)
        assert bot.last_rule_used == RULE_AVOID_RISKY_TEN
        assert result != c("C", "10")   # le 10 risqué est évité
        assert result == c("C", "R")

    def test_no_trigger_ten_safe_suit(self):
        """
        Aucun adversaire n'est chicane dans la couleur du 10 → pas de déclenchement.
        """
        bot = HeuristicBotV2_2()
        bot.reset_hand(TRUMP)

        valid = [c("C", "10"), c("P", "8")]
        ctx = _ctx(leading=True, tricks_history=[], played_cards=[])
        result = bot.choose(valid, TRUMP, ctx)
        assert bot.last_rule_used != RULE_AVOID_RISKY_TEN


# ═══════════════════════════════════════════════════════════════════
# RULE 7 — DISCARD_CREATE_VOID
# ═══════════════════════════════════════════════════════════════════

class TestDiscardCreateVoid:

    def test_trigger_singleton_preferred(self):
        """
        Partenaire est maître, on a un singleton sans As ni 10
        → jouer le singleton pour créer une chicane immédiate.
        """
        bot = HeuristicBotV2_2()
        bot.reset_hand(TRUMP)

        # C8 : singleton sans As ni 10. PR et PD : 2 cartes en P
        valid = [c("C", "8"), c("P", "R"), c("P", "D")]
        ctx = _ctx(
            leading=False,
            suit_asked="T",
            partner_is_master=True,
            master_card=c(TRUMP, "V"),
            master_player_idx=2,
            trick_so_far=[(2, c(TRUMP, "V"))],
        )
        result = bot.choose(valid, TRUMP, ctx)
        assert bot.last_rule_used == RULE_DISCARD_CREATE_VOID
        assert result == c("C", "8")

    def test_trigger_prefers_void_over_min_discard(self):
        """
        Deux couleurs sans As/10, dont un singleton → jouer le singleton.
        """
        bot = HeuristicBotV2_2()
        bot.reset_hand(TRUMP)

        valid = [c("C", "R"), c("C", "D"), c("P", "7")]
        ctx = _ctx(
            leading=False,
            suit_asked="T",
            partner_is_master=True,
            master_card=c(TRUMP, "V"),
            master_player_idx=2,
            trick_so_far=[(2, c(TRUMP, "V"))],
        )
        result = bot.choose(valid, TRUMP, ctx)
        assert bot.last_rule_used == RULE_DISCARD_CREATE_VOID
        assert result == c("P", "7")   # singleton → chicane immédiate

    def test_no_trigger_all_cards_have_ace_or_ten(self):
        """
        Toutes les cartes sont As ou 10 → DISCARD_CREATE_VOID ne sacrifie pas ces cartes.
        """
        bot = HeuristicBotV2_2()
        bot.reset_hand(TRUMP)

        valid = [c("C", "A"), c("P", "10")]
        ctx = _ctx(
            leading=False,
            suit_asked="T",
            partner_is_master=True,
            master_card=c(TRUMP, "V"),
            master_player_idx=2,
            trick_so_far=[(2, c(TRUMP, "V"))],
        )
        bot.choose(valid, TRUMP, ctx)
        assert bot.last_rule_used != RULE_DISCARD_CREATE_VOID


# ═══════════════════════════════════════════════════════════════════
# Tests d'intégration / compatibilité
# ═══════════════════════════════════════════════════════════════════

class TestIntegration:

    def test_bot_version(self):
        bot = HeuristicBotV2_2()
        assert bot.BOT_VERSION == "heuristic_v2_2"

    def test_inherits_from_v2(self):
        from belote.agents.heuristic_bot_v2 import HeuristicBotV2
        bot = HeuristicBotV2_2()
        assert isinstance(bot, HeuristicBotV2)

    def test_always_returns_valid_card(self):
        """Le bot retourne toujours une carte présente dans valid_cards."""
        import random
        random.seed(42)
        bot = HeuristicBotV2_2()
        bot.reset_hand(TRUMP)

        valid = [c("C", "A"), c("P", "R"), c(TRUMP, "7")]
        ctx = _ctx(leading=True, played_cards=[], trick_num=3)
        result = bot.choose(valid, TRUMP, ctx)
        assert result in valid

    def test_last_rule_used_always_set(self):
        """last_rule_used est toujours non-None après un appel à choose()."""
        bot = HeuristicBotV2_2()
        bot.reset_hand(TRUMP)

        valid = [c("C", "7")]
        ctx = _ctx(leading=True)
        bot.choose(valid, TRUMP, ctx)
        assert bot.last_rule_used is not None

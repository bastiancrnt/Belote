import random
from belote.agents.heuristic_bot import (
    RULE_SUPPORT_TAKER_BIG, RULE_SUPPORT_TAKER_SMALL,
    RULE_ADV_ACE_SHORT, RULE_ADV_ACE, RULE_ADV_TEN_AFTER_ACE,
    RULE_ADV_SINGLETON, RULE_ADV_AVOID_TEN, RULE_ADV_MIN,
    RULE_ADV_GIVE_POINTS_ACE, RULE_ADV_GIVE_POINTS_SIG,
    HeuristicBot,
    TRUMP_ORDER,
    RULE_DRAW_TRUMP_JACK_NINE, RULE_DRAW_TRUMP_JACK_LENGTH,
    RULE_CONTINUE_DRAWING_NINE, RULE_ANSWER_PARTNER_SIGNAL,
    RULE_PLAY_MASTER_TEN, RULE_PLAY_LONGEST_SUIT_ACE,
    RULE_PLAY_ACE_TEN, RULE_CREATE_VOID, RULE_SIGNAL_ACE,
    RULE_GIVE_POINTS, RULE_WIN_WITH_MINIMUM, RULE_CUT_MINIMUM,
    RULE_DISCARD_MINIMUM, RULE_DEFAULT_MIN,
)

# Règles propres à V2
RULE_SKIP_RISKY_ACE   = "SKIP_RISKY_ACE"    # As probable d'être coupé → on passe
RULE_SAFE_ACE_TEN     = "SAFE_ACE_TEN"
RULE_SAFE_ACE_LONGEST = "SAFE_ACE_LONGEST"


class HeuristicBotV2(HeuristicBot):
    """
    Bot heuristique V2.

    Améliorations par rapport à V1 :
      1. Mémorisation des chicanes certaines (un joueur n'a pas suivi → vide dans cette couleur ;
         s'il a défaussé hors-atout → vide en atout aussi).
      2. Comptage des atouts adverses corrigé : si les deux adversaires sont connus vides
         en atout, enemy_trumps = 0 → on cesse de tirer l'atout inutilement.
      3. Jeu de l'As conditionnel : avant de jouer un As hors-atout, on vérifie qu'aucun
         adversaire n'est connu vide dans cette couleur avec de l'atout encore disponible
         (prob coupe certaine). Si risque certain → on cherche un As plus sûr ou on passe
         à une autre séquence.
    """

    BOT_VERSION = "heuristic_v2"

    # ──────────────────────────────────────────────────────────────────────
    # 1. DÉDUCTION DES CHICANES
    # ──────────────────────────────────────────────────────────────────────

    def _compute_player_voids(self, tricks_history, trump):
        """
        Parcourt l'historique des plis et déduit les chicanes certaines.

        Règles d'inférence :
          - Joueur n'a pas suivi la couleur demandée
            → vide dans cette couleur.
          - Joueur n'a pas suivi ET a joué une carte hors-atout (défausse)
            → vide en atout aussi (sinon il aurait dû couper).
        """
        voids = {i: set() for i in range(4)}
        for trick in tricks_history:
            suit_asked = trick.get("suit_asked")
            if not suit_asked:
                continue
            for pidx, card in trick["cards"].items():
                if card.suit != suit_asked:
                    # N'a pas suivi la couleur demandée
                    voids[pidx].add(suit_asked)
                    if card.suit != trump:
                        # Défausse hors-atout → vide en atout aussi
                        voids[pidx].add(trump)
        return voids

    # ──────────────────────────────────────────────────────────────────────
    # 2. COMPTAGE DES ATOUTS ADVERSES CORRIGÉ
    # ──────────────────────────────────────────────────────────────────────

    def _count_enemy_trumps_left(self, trump, played_cards, my_hand_cards):
        """
        Comme V1, mais retourne 0 si les DEUX adversaires sont connus
        vides en atout (inutile de tirer).
        """
        voids = getattr(self, "_voids", {})
        # On a besoin de player_idx pour identifier les adversaires.
        # Il est stocké lors du dernier appel à choose().
        player_idx = getattr(self, "_current_player_idx", 0)
        enemies = [(player_idx + 1) % 4, (player_idx + 3) % 4]

        if all(trump in voids.get(e, set()) for e in enemies):
            return 0

        # Calcul standard
        all_trump_ranks = set(TRUMP_ORDER)
        played = {c.rank for c in played_cards if c.suit == trump}
        mine = {c.rank for c in my_hand_cards if c.suit == trump}
        return len(all_trump_ranks - played - mine)

    # ──────────────────────────────────────────────────────────────────────
    # 3. AIDE : RISQUE DE COUPE CERTAINE
    # ──────────────────────────────────────────────────────────────────────

    def _certain_cut(self, suit, trump, player_idx):
        """
        Retourne True si au moins un adversaire est CERTAIN de couper un As
        dans `suit` : connu vide dans la couleur ET pas connu vide en atout.
        """
        voids = getattr(self, "_voids", {})
        enemies = [(player_idx + 1) % 4, (player_idx + 3) % 4]
        for e in enemies:
            ev = voids.get(e, set())
            if suit in ev and trump not in ev:
                return True
        return False

    # ──────────────────────────────────────────────────────────────────────
    # SURCHARGE DE choose() → injecte les chicanes avant le dispatch
    # ──────────────────────────────────────────────────────────────────────

    def choose(self, valid_cards, trump=None, context=None):
        if context is None or trump is None:
            self.last_rule_used = RULE_DEFAULT_MIN
            return random.choice(valid_cards)

        self._current_player_idx = context["player_idx"]
        tricks_history = context.get("tricks_history", [])
        self._voids = self._compute_player_voids(tricks_history, trump)

        return super().choose(valid_cards, trump, context)

    # ──────────────────────────────────────────────────────────────────────
    # SURCHARGE DE _choose_lead → As conditionnel (amélioration 3)
    # ──────────────────────────────────────────────────────────────────────

    def _choose_lead(self, valid_cards, trump, trump_cards, non_trump, my_trump_ranks,
                     by_suit, player_idx, partner_idx, played_cards, trick_num, tricks_history):

        # ── Adversaire preneur → séquence spéciale (héritée de V1) ─────────
        taker_idx = getattr(self, "_context", {}).get("taker_idx")
        enemy_is_taker = (taker_idx is not None
                          and taker_idx != player_idx
                          and taker_idx != partner_idx)
        if enemy_is_taker:
            return self._choose_lead_enemy_taker(
                valid_cards, trump, trump_cards, non_trump,
                by_suit, player_idx, played_cards, tricks_history
            )

        # Règle 1a / 1b / signal partenaire / 10-maître : identiques à V1
        # (héritage direct — pas de surcharge nécessaire sur ces branches)
        # On surcharge uniquement la partie As hors-atout.

        enemy_trumps = self._count_enemy_trumps_left(trump, played_cards, valid_cards)

        # ── Règle 1a ──
        if ("V" in my_trump_ranks and "9" in my_trump_ranks
                and len(trump_cards) >= 3 and enemy_trumps > 0):
            if not self._drew_trump_this_hand:
                self._drew_trump_this_hand = True
                self.last_rule_used = RULE_DRAW_TRUMP_JACK_NINE
                return next(c for c in trump_cards if c.rank == "V")
            if self._drew_trump_this_hand and not self._drew_nine_this_hand:
                self._drew_nine_this_hand = True
                self.last_rule_used = RULE_CONTINUE_DRAWING_NINE
                return next(c for c in trump_cards if c.rank == "9")

        # ── Règle 1b ──
        if ("V" in my_trump_ranks and "9" not in my_trump_ranks
                and len(trump_cards) >= 3 and enemy_trumps > 0
                and not self._drew_trump_this_hand):
            self._drew_trump_this_hand = True
            self.last_rule_used = RULE_DRAW_TRUMP_JACK_LENGTH
            return next(c for c in trump_cards if c.rank == "V")

        # ── Règle P : partenaire preneur → soutien atout ──
        taker_idx = getattr(self, "_context", {}).get("taker_idx")
        partner_is_taker = (taker_idx is not None and taker_idx == partner_idx)
        if partner_is_taker and trump_cards and enemy_trumps > 0:
            if "9" in my_trump_ranks:
                self.last_rule_used = RULE_SUPPORT_TAKER_SMALL
                return self._min_card(trump_cards, trump)
            else:
                self.last_rule_used = RULE_SUPPORT_TAKER_BIG
                return self._max_card(trump_cards, trump)

        # ── Règle 2 ──
        signal_suit = self._detect_partner_signal(tricks_history, partner_idx, player_idx, trump)
        if signal_suit and signal_suit in by_suit:
            self.last_rule_used = RULE_ANSWER_PARTNER_SIGNAL
            return self._min_card(by_suit[signal_suit], trump)

        # ── Règle 18 ──
        ten_master = self._find_ten_master(non_trump, trump, played_cards, valid_cards)
        if ten_master:
            self.last_rule_used = RULE_PLAY_MASTER_TEN
            return ten_master

        # ── Règle 19 (V2) : As hors-atout filtré par risque de coupe ──
        ace_suits = [(s, cards) for s, cards in by_suit.items()
                     if any(c.rank == "A" for c in cards)]
        if ace_suits:
            # Séparer As sûrs / As à risque certain de coupe
            safe  = [(s, c) for s, c in ace_suits if not self._certain_cut(s, trump, player_idx)]
            risky = [(s, c) for s, c in ace_suits if     self._certain_cut(s, trump, player_idx)]

            # On préfère jouer un As sûr ; si tous sont risqués on bascule sur la suite
            candidates = safe if safe else []

            if candidates:
                # As+10 sûr d'abord
                as_ten = [(s, cards) for s, cards in candidates
                          if any(c.rank == "10" for c in cards)]
                if as_ten:
                    s, cards = max(as_ten, key=lambda x: len(x[1]))
                    self.last_rule_used = RULE_SAFE_ACE_TEN
                    return next(c for c in cards if c.rank == "A")
                s, cards = max(candidates, key=lambda x: len(x[1]))
                self.last_rule_used = RULE_SAFE_ACE_LONGEST
                return next(c for c in cards if c.rank == "A")
            # Tous les As sont risqués → on les ignore et on continue vers chicane / appel

        # ── Règle 6 : chicane ──
        singletons = [(s, cards) for s, cards in by_suit.items()
                      if len(cards) == 1 and cards[0].rank not in ("A", "10")]
        if singletons:
            self.last_rule_used = RULE_CREATE_VOID
            return singletons[0][1][0]

        # ── Règle 5 : appel ──
        already_signaled = self._detect_my_signals_sent(tricks_history, player_idx, trump)
        for s, cards in by_suit.items():
            ranks = {c.rank for c in cards}
            if "A" in ranks and len(cards) >= 2 and s not in already_signaled:
                smalls = [c for c in cards if c.rank != "A"]
                self.last_rule_used = RULE_SIGNAL_ACE
                return self._min_card(smalls, trump)

        # ── Si tous les As sont risqués et qu'on n'a pas d'autre option → on joue quand même ──
        if ace_suits:
            as_ten = [(s, cards) for s, cards in ace_suits
                      if any(c.rank == "10" for c in cards)]
            if as_ten:
                s, cards = max(as_ten, key=lambda x: len(x[1]))
                self.last_rule_used = RULE_PLAY_ACE_TEN
                return next(c for c in cards if c.rank == "A")
            s, cards = max(ace_suits, key=lambda x: len(x[1]))
            self.last_rule_used = RULE_PLAY_LONGEST_SUIT_ACE
            return next(c for c in cards if c.rank == "A")

        # ── Défaut ──
        self.last_rule_used = RULE_DEFAULT_MIN
        return self._min_card(valid_cards, trump)

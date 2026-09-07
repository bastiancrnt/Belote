"""
HeuristicBotV2_2 — Heuristique enrichie (sans Monte-Carlo)
===========================================================
Hérite de HeuristicBotV2 et ajoute 7 nouvelles règles :

  1. DRAW_LAST_BEATABLE_TRUMP        — tirer le dernier atout adverse si on peut le battre
  2. AVOID_WASTING_TRUMP_ON_PARTNER  — ne pas dilapider V/9/A sur un pli maîtrisé par le partenaire
  3. GIVE_POINTS_SMART               — donner des points intelligemment (10 isolé > As isolé > pair A+10 → donner 10)
  4. RETURN_PARTNER_SUIT             — retourner la couleur du partenaire (convention A→10)
  5. SECURE_LAST_TRICK               — sécuriser le dernier pli (dix-de-der)
  6. AVOID_RISKY_TEN                 — ne pas ouvrir d'un 10 dans une couleur où un adversaire est chicane+atout
  7. DISCARD_CREATE_VOID             — préférer les défausses créatrices de chicane
"""

from belote.agents.heuristic_bot_v2 import (
    HeuristicBotV2,
    RULE_SKIP_RISKY_ACE, RULE_SAFE_ACE_TEN, RULE_SAFE_ACE_LONGEST,
)
from belote.agents.heuristic_bot import (
    TRUMP_ORDER, SMALL_RANKS,
    RULE_SIGNAL_ACE, RULE_GIVE_POINTS, RULE_WIN_WITH_MINIMUM,
    RULE_CUT_MINIMUM, RULE_DISCARD_MINIMUM, RULE_DEFAULT_MIN,
    RULE_DRAW_TRUMP_JACK_NINE, RULE_DRAW_TRUMP_JACK_LENGTH,
    RULE_CONTINUE_DRAWING_NINE, RULE_ANSWER_PARTNER_SIGNAL,
    RULE_PLAY_MASTER_TEN,
)

# ── Constantes des nouvelles règles ──────────────────────────────────────────
RULE_DRAW_LAST_BEATABLE_TRUMP        = "DRAW_LAST_BEATABLE_TRUMP"
RULE_AVOID_WASTING_TRUMP_ON_PARTNER  = "AVOID_WASTING_TRUMP_ON_PARTNER"
RULE_GIVE_POINTS_SMART               = "GIVE_POINTS_SMART"
RULE_RETURN_PARTNER_SUIT             = "RETURN_PARTNER_SUIT"
RULE_SECURE_LAST_TRICK               = "SECURE_LAST_TRICK"
RULE_AVOID_RISKY_TEN                 = "AVOID_RISKY_TEN"
RULE_DISCARD_CREATE_VOID             = "DISCARD_CREATE_VOID"

# Rang atout dans l'ordre croissant (depuis valid_play.py)
_TRUMP_ASC = ["7", "8", "D", "R", "10", "A", "9", "V"]
_TRUMP_STR = {r: i for i, r in enumerate(_TRUMP_ASC)}  # V=7 (plus fort), 7=0 (plus faible)


def _trump_strength(rank):
    """Retourne la force d'un rang d'atout (0=plus faible, 7=plus fort)."""
    return _TRUMP_STR.get(rank, -1)


class HeuristicBotV2_2(HeuristicBotV2):
    """
    Bot heuristique V2.2 — amélioration de V2 sans Monte-Carlo.

    Toutes les variables de contexte (_voids, _current_player_idx, _context…)
    sont initialisées par HeuristicBotV2.choose() avant l'appel aux sous-méthodes.
    """

    BOT_VERSION = "heuristic_v2_2"

    # ──────────────────────────────────────────────────────────────────────
    # SURCHARGE DE choose() — intercept SECURE_LAST_TRICK
    # ──────────────────────────────────────────────────────────────────────

    def choose(self, valid_cards, trump=None, context=None):
        if context is None or trump is None:
            self.last_rule_used = RULE_DEFAULT_MIN
            from belote.agents.heuristic_bot import RULE_DEFAULT_MIN as dm
            import random
            return random.choice(valid_cards)

        # Intercept global : sécuriser le dernier pli (SECURE_LAST_TRICK)
        trick_num = context.get("trick_num", 0)
        if trick_num in (7, 8):
            result = self._try_secure_last_trick(valid_cards, trump, context)
            if result is not None:
                return result

        # Déléguer à V2 (qui initialisera _voids, _current_player_idx, etc.)
        return super().choose(valid_cards, trump, context)

    # ──────────────────────────────────────────────────────────────────────
    # SURCHARGE DE _choose_lead
    # ──────────────────────────────────────────────────────────────────────

    def _choose_lead(self, valid_cards, trump, trump_cards, non_trump, my_trump_ranks,
                     by_suit, player_idx, partner_idx, played_cards, trick_num, tricks_history):

        # ── 1. DRAW_LAST_BEATABLE_TRUMP ────────────────────────────────────
        result = self._draw_last_beatable_trump_rule(
            trump_cards, trump, played_cards, valid_cards
        )
        if result is not None:
            return result

        # ── 2. RETURN_PARTNER_SUIT ────────────────────────────────────────
        result = self._return_partner_suit_rule(
            by_suit, trump, player_idx, partner_idx,
            played_cards, tricks_history, valid_cards
        )
        if result is not None:
            return result

        # ── 3. Logique V2 ─────────────────────────────────────────────────
        chosen = super()._choose_lead(
            valid_cards, trump, trump_cards, non_trump, my_trump_ranks,
            by_suit, player_idx, partner_idx, played_cards, trick_num, tricks_history
        )

        # ── 4. AVOID_RISKY_TEN — post-check ──────────────────────────────
        if chosen is not None and chosen.rank == "10" and chosen.suit != trump:
            if self._is_risky_ten(chosen.suit, player_idx, trump):
                alt = self._avoid_risky_ten_alt(valid_cards, trump, chosen)
                if alt is not None:
                    self.last_rule_used = RULE_AVOID_RISKY_TEN
                    return alt

        return chosen

    # ──────────────────────────────────────────────────────────────────────
    # SURCHARGE DE _choose_partner_master
    # ──────────────────────────────────────────────────────────────────────

    def _choose_partner_master(self, valid_cards, trump, trump_cards, non_trump,
                                my_trump_ranks, by_suit, player_idx, partner_idx,
                                played_cards, trick_num, tricks_history,
                                master_card, position):

        # ── 1. Appel As (identique à V1/V2) ───────────────────────────────
        already_signaled = self._detect_my_signals_sent(tricks_history, player_idx, trump)
        for s, cards in by_suit.items():
            ranks = {c.rank for c in cards}
            if "A" in ranks and len(cards) >= 2 and s not in already_signaled:
                smalls = [c for c in cards if c.rank != "A"]
                self.last_rule_used = RULE_SIGNAL_ACE
                return self._min_card(smalls, trump)

        # ── 2. GIVE_POINTS_SMART ──────────────────────────────────────────
        result = self._give_points_smart_rule(non_trump, trump)
        if result is not None:
            return result

        # ── 3. DISCARD_CREATE_VOID ────────────────────────────────────────
        result = self._discard_create_void_rule(non_trump, trump)
        if result is not None:
            return result

        # ── 4. Défausse minimum hors-atout ────────────────────────────────
        if non_trump:
            self.last_rule_used = RULE_DISCARD_MINIMUM
            return self._min_card(non_trump, trump)

        # ── 5. AVOID_WASTING_TRUMP_ON_PARTNER ────────────────────────────
        if trump_cards:
            big_trumps = [c for c in trump_cards if c.rank in ("V", "9", "A")]
            small_trumps = [c for c in trump_cards if c.rank not in ("V", "9", "A")]
            if small_trumps:
                self.last_rule_used = RULE_AVOID_WASTING_TRUMP_ON_PARTNER
                return self._min_card(small_trumps, trump)

        # ── 6. Couper au minimum (fallback — tous les atouts sont V/9/A) ──
        if trump_cards:
            self.last_rule_used = RULE_CUT_MINIMUM
            return self._min_card(trump_cards, trump)

        self.last_rule_used = RULE_DEFAULT_MIN
        return self._min_card(valid_cards, trump)

    # ══════════════════════════════════════════════════════════════════════
    # HELPERS — nouvelles règles
    # ══════════════════════════════════════════════════════════════════════

    # ── RULE 1 : DRAW_LAST_BEATABLE_TRUMP ────────────────────────────────

    def _draw_last_beatable_trump_rule(self, trump_cards, trump, played_cards, valid_cards):
        """
        Si un seul rang d'atout adverse reste inconnu ET qu'on peut le battre,
        tirer l'atout avec la carte minimale gagnante.

        Condition : len(remaining) == 1 ET le partenaire est connu vide en atout.
        Sans cette deuxième garde, l'atout restant pourrait être celui du partenaire
        et on le tirerait inutilement (gaspillage d'un V/9 sur notre propre camp).
        """
        if not trump_cards:
            return None

        # Garde partenaire : on ne tire que si le partenaire est connu vide en atout
        partner_idx = getattr(self, "_context", {}).get("partner_idx")
        voids = getattr(self, "_voids", {})
        if partner_idx is None or trump not in voids.get(partner_idx, set()):
            # Partenaire pas connu vide → l'atout restant peut être le sien
            return None

        all_ranks = set(TRUMP_ORDER)
        played_ranks = {c.rank for c in played_cards if c.suit == trump}
        my_ranks = {c.rank for c in valid_cards if c.suit == trump}
        remaining = all_ranks - played_ranks - my_ranks

        if len(remaining) != 1:
            return None

        (last_rank,) = remaining
        last_str = _trump_strength(last_rank)

        # Chercher la carte d'atout minimale qui bat le dernier rang restant
        beaters = [c for c in trump_cards if _trump_strength(c.rank) > last_str]
        if not beaters:
            return None

        self.last_rule_used = RULE_DRAW_LAST_BEATABLE_TRUMP
        return min(beaters, key=lambda c: _trump_strength(c.rank))

    # ── RULE 4 : RETURN_PARTNER_SUIT ─────────────────────────────────────

    def _detect_partner_ace_open(self, tricks_history, partner_idx, trump):
        """
        Détecte si le partenaire a ouvert un pli avec un As (convention As→10).
        Retourne la couleur de l'As, ou None.
        """
        for trick in tricks_history:
            seq = trick.get("play_sequence", [])
            if not seq:
                continue
            first_player, first_card = seq[0]
            if first_player == partner_idx:
                if first_card.rank == "A" and first_card.suit != trump:
                    return first_card.suit
        return None

    def _return_partner_suit_rule(self, by_suit, trump, player_idx, partner_idx,
                                   played_cards, tricks_history, valid_cards):
        """
        Retourner la couleur du partenaire après son ouverture en As.

        Convention A→10 :
          - Si partenaire a ouvert en As → il a probablement le 10.
          - Si on a 3+ cartes dans cette couleur (A, 10, + petit) et zéro atout
            adverse restant → jouer la petite d'abord (séquence petit→A→10).
          - Sinon → retourner le plus petit dans cette couleur (standard).
        """
        suit = self._detect_partner_ace_open(tricks_history, partner_idx, trump)
        if suit is None or suit not in by_suit:
            return None

        cards_in_suit = by_suit[suit]
        if not cards_in_suit:
            return None

        ranks_in_suit = {c.rank for c in cards_in_suit}

        # Convention 3 cartes + pas d'atouts adverses : jouer le petit d'abord
        if (len(cards_in_suit) >= 3
                and "A" in ranks_in_suit
                and "10" in ranks_in_suit):
            enemy_trumps = self._count_enemy_trumps_left(trump, played_cards, valid_cards)
            if enemy_trumps == 0:
                smalls = [c for c in cards_in_suit if c.rank not in ("A", "10")]
                if smalls:
                    self.last_rule_used = RULE_RETURN_PARTNER_SUIT
                    return self._min_card(smalls, trump)

        # Standard : retourner la plus petite carte dans cette couleur
        self.last_rule_used = RULE_RETURN_PARTNER_SUIT
        return self._min_card(cards_in_suit, trump)

    # ── RULE 3 : GIVE_POINTS_SMART ───────────────────────────────────────

    def _give_points_smart_rule(self, non_trump, trump):
        """
        Ordre de priorité pour donner des points quand le partenaire est maître :
          1. 10 isolé (sans As dans la même couleur) — point fort sans risque
          2. As isolé (sans 10 dans la même couleur) — signale qu'on n'a pas le 10
          3. Paire As+10 → donner le 10 (conserver l'As pour un pli futur)
        """
        from collections import defaultdict
        by_suit = defaultdict(list)
        for c in non_trump:
            by_suit[c.suit].append(c)

        # 1. 10 isolé (couleur sans As)
        isolated_tens = []
        for s, cards in by_suit.items():
            ranks = {c.rank for c in cards}
            if "10" in ranks and "A" not in ranks:
                isolated_tens.append(next(c for c in cards if c.rank == "10"))
        if isolated_tens:
            self.last_rule_used = RULE_GIVE_POINTS_SMART
            return max(isolated_tens, key=lambda c: self._card_val(c, trump))

        # 2. As isolé (couleur sans 10)
        isolated_aces = []
        for s, cards in by_suit.items():
            ranks = {c.rank for c in cards}
            if "A" in ranks and "10" not in ranks:
                isolated_aces.append(next(c for c in cards if c.rank == "A"))
        if isolated_aces:
            self.last_rule_used = RULE_GIVE_POINTS_SMART
            return max(isolated_aces, key=lambda c: self._card_val(c, trump))

        # 3. Paire As+10 → donner le 10 (garder l'As)
        for s, cards in by_suit.items():
            ranks = {c.rank for c in cards}
            if "A" in ranks and "10" in ranks:
                self.last_rule_used = RULE_GIVE_POINTS_SMART
                return next(c for c in cards if c.rank == "10")

        return None

    # ── RULE 7 : DISCARD_CREATE_VOID ─────────────────────────────────────

    def _discard_create_void_rule(self, non_trump, trump):
        """
        Parmi les cartes hors-atout sans As ni 10, préférer une couleur
        avec exactement 1 carte (créer une chicane immédiate) ou la couleur
        la plus courte non-A non-10 (future chicane).

        N'intervient que si le choix ne sacrifie pas de carte à points.
        """
        from collections import defaultdict
        by_suit = defaultdict(list)
        for c in non_trump:
            by_suit[c.suit].append(c)

        # Chercher des couleurs sans As ni 10 (on peut se chicaner sans risque)
        safe_suits = {
            s: cards for s, cards in by_suit.items()
            if not any(c.rank in ("A", "10") for c in cards)
        }
        if not safe_suits:
            return None

        # 1. Singleton : défausse crée une chicane immédiate
        singletons = [(s, cards) for s, cards in safe_suits.items() if len(cards) == 1]
        if singletons:
            s, cards = singletons[0]
            self.last_rule_used = RULE_DISCARD_CREATE_VOID
            return cards[0]

        # 2. Couleur la plus courte (préparer la chicane)
        s, cards = min(safe_suits.items(), key=lambda x: len(x[1]))
        # Jouer la plus petite de cette couleur
        self.last_rule_used = RULE_DISCARD_CREATE_VOID
        return self._min_card(cards, trump)

    # ── RULE 6 : AVOID_RISKY_TEN ─────────────────────────────────────────

    def _is_risky_ten(self, suit, player_idx, trump):
        """
        Un 10 est risqué si un adversaire est connu vide dans cette couleur
        ET pas connu vide en atout (il peut couper).
        On utilise _certain_cut de V2.
        """
        return self._certain_cut(suit, trump, player_idx)

    def _avoid_risky_ten_alt(self, valid_cards, trump, avoided_card):
        """
        Trouver une alternative au 10 risqué :
          - Une autre carte hors-atout non-10 (la moins chère)
          - Ou un atout minimal
          - Ou None si impossible
        """
        alts = [c for c in valid_cards if c != avoided_card and not (c.rank == "10" and c.suit != trump)]
        if alts:
            return self._min_card(alts, trump)
        return None

    # ── RULE 5 : SECURE_LAST_TRICK ───────────────────────────────────────

    def _try_secure_last_trick(self, valid_cards, trump, context):
        """
        Trick 8 : chaque joueur n'a qu'une carte → valid_cards a toujours 1 élément.
        La règle est triviale ici ; le vrai apport est au trick 7.

        Trick 7 (2 cartes par joueur) :
          - Si on est maître (partenaire est maître OU on est le seul à pouvoir gagner) :
            conserver la carte la plus forte pour le pli 8 (dix-de-der),
            jouer l'autre maintenant.
          - Si l'adversaire est maître : chercher à gagner avec le minimum nécessaire.

        Retourne None si la règle ne s'applique pas (laisse la logique normale).
        """
        trick_num = context.get("trick_num", 0)
        if len(valid_cards) == 1:
            # Trick 8 ou forcé → rien à optimiser
            return None

        leading = context.get("leading", False)
        partner_is_master = context.get("partner_is_master", False)
        master_card = context.get("master_card")

        # Seulement à l'ouverture du pli 7 pour conserver la meilleure carte
        if trick_num == 7 and leading:
            trump_cards = [c for c in valid_cards if c.suit == trump]
            non_trump = [c for c in valid_cards if c.suit != trump]

            # Si on a 2 cartes dont un atout fort → jouer le non-atout maintenant,
            # garder l'atout pour le pli 8
            if len(valid_cards) == 2 and len(trump_cards) == 1 and len(non_trump) == 1:
                # Vérifier que l'atout bat n'importe quel adversaire probable
                played_cards = context.get("played_cards", [])
                my_trump_card = trump_cards[0]
                all_trump_played = {c.rank for c in played_cards if c.suit == trump}
                my_trump_ranks = {c.rank for c in valid_cards if c.suit == trump}
                remaining = set(TRUMP_ORDER) - all_trump_played - my_trump_ranks
                # Si notre atout bat tous les atouts restants → garder pour le dix-de-der
                my_str = _trump_strength(my_trump_card.rank)
                if all(_trump_strength(r) < my_str for r in remaining):
                    self.last_rule_used = RULE_SECURE_LAST_TRICK
                    return non_trump[0]

        return None

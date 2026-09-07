import math
import random
from collections import defaultdict
from belote.game.bidding import numbers as VALID_NUMBERS

BID_THRESHOLD = 70

# ── Noms de règles (enregistrés en DB) ────────────────────────────────────────
RULE_DRAW_TRUMP_JACK_NINE   = "DRAW_TRUMP_JACK_NINE"
RULE_DRAW_TRUMP_JACK_LENGTH = "DRAW_TRUMP_JACK_LENGTH"
RULE_CONTINUE_DRAWING_NINE  = "CONTINUE_DRAWING_NINE"
RULE_ANSWER_PARTNER_SIGNAL  = "ANSWER_PARTNER_SIGNAL"
RULE_PLAY_MASTER_TEN        = "PLAY_MASTER_TEN"
RULE_PLAY_LONGEST_SUIT_ACE  = "PLAY_LONGEST_SUIT_ACE"
RULE_PLAY_ACE_TEN           = "PLAY_ACE_TEN"
RULE_CREATE_VOID            = "CREATE_VOID"
RULE_SIGNAL_ACE             = "SIGNAL_ACE"
RULE_GIVE_POINTS            = "GIVE_POINTS"
RULE_WIN_WITH_MINIMUM       = "WIN_WITH_MINIMUM"
RULE_CUT_MINIMUM            = "CUT_MINIMUM"
RULE_DISCARD_MINIMUM        = "DISCARD_MINIMUM"
RULE_DEFAULT_MIN            = "DEFAULT_MIN"
RULE_SUPPORT_TAKER_BIG     = "SUPPORT_TAKER_BIG"   # partenaire preneur, je n'ai pas le 9
RULE_SUPPORT_TAKER_SMALL   = "SUPPORT_TAKER_SMALL" # partenaire preneur, je garde le 9
RULE_ADV_ACE_SHORT         = "ADV_ACE_SHORT"        # adversaire preneur : as couleur la plus courte
RULE_ADV_ACE               = "ADV_ACE"              # adversaire preneur : autre as
RULE_ADV_TEN_AFTER_ACE     = "ADV_TEN_AFTER_ACE"   # adversaire preneur : 10 après mon as
RULE_ADV_SINGLETON         = "ADV_SINGLETON"        # adversaire preneur : singleton hors-10
RULE_ADV_AVOID_TEN         = "ADV_AVOID_TEN"        # adversaire preneur : faible dans couleur avec 10
RULE_ADV_MIN               = "ADV_MIN"              # adversaire preneur : plus faible hors-atout
RULE_ADV_GIVE_POINTS_ACE   = "ADV_GIVE_POINTS_ACE"  # partenaire joue un As → donner des points
RULE_ADV_GIVE_POINTS_SIG   = "ADV_GIVE_POINTS_SIG"  # partenaire joue petite → donner des points

TRUMP_ORDER = ["V", "9", "A", "10", "R", "D", "8", "7"]  # du plus fort au plus faible
SMALL_RANKS = {"7", "8", "D", "R"}  # cartes "petites" pour les appels


def estimate(hand, trump):
    """Estime les points réalisables avec `trump` comme atout."""
    trump_cards = [c for c in hand if c.suit == trump]
    trump_ranks = {c.rank for c in trump_cards}
    n_trump = len(trump_cards)
    score = 0

    TRUMP_PTS = {"V": 20, "9": 14, "A": 6, "10": 5}
    for card in trump_cards:
        score += TRUMP_PTS.get(card.rank, 0)

    trump_desc = ["V", "9", "A", "10", "R", "D", "8", "7"]
    sure_tricks = 0
    for rank in trump_desc:
        if rank in trump_ranks:
            sure_tricks += 1
        else:
            break
    for c in hand:
        if c.suit != trump and c.rank == "A":
            sure_tricks += 1
    if sure_tricks > 2:
        score += 5 * sure_tricks

    if n_trump > 2:
        score += 5 * (n_trump - 2)

    by_suit = defaultdict(list)
    for c in hand:
        if c.suit != trump:
            by_suit[c.suit].append(c.rank)

    all_suits = {"C", "K", "P", "T"}
    for s in all_suits - {trump}:
        if s not in by_suit:
            score += 10

    has_as_10_side = False
    for suit_ranks in by_suit.values():
        if "A" in suit_ranks:
            score += 11
        if "10" in suit_ranks and "A" not in suit_ranks and len(suit_ranks) > 1:
            score += 5
        if "A" in suit_ranks and "10" in suit_ranks:
            has_as_10_side = True
        if len(suit_ranks) == 1:
            score += 5

    if "R" in trump_ranks and "D" in trump_ranks and score > 70:
        score += 20

    if "V" in trump_ranks and "9" in trump_ranks and "A" in trump_ranks and has_as_10_side:
        score += 25
    if "V" in trump_ranks and "9" in trump_ranks and "10" in trump_ranks and has_as_10_side:
        score += 20
    other_trumps = trump_ranks - {"V", "9", "A", "10"}
    if "V" in trump_ranks and "9" in trump_ranks and other_trumps and has_as_10_side:
        score += 10

    return score


def _trump_strength(rank):
    """Index dans TRUMP_ORDER (0 = plus fort)."""
    try:
        return TRUMP_ORDER.index(rank)
    except ValueError:
        return 99


class HeuristicBot:
    def __init__(self):
        self.trump = None
        self._drew_trump_this_hand = False
        self._drew_nine_this_hand = False
        self.last_rule_used = None
        self.last_rule_used = None

    def reset_hand(self, trump):
        self.trump = trump
        self._drew_trump_this_hand = False
        self._drew_nine_this_hand = False
        self.last_rule_used = None

    # ──────────────────────────────────────────────────────────────────────
    # ENCHÈRES
    # ──────────────────────────────────────────────────────────────────────

    def choose_bid(self, hand, current_best, partner_bid=None):
        def est_to_target(est):
            if est <= 70:
                return 80
            elif est <= 79:
                return 85
            elif est <= 89:
                return 90
            else:
                return math.ceil(est / 5) * 5

        if partner_bid is not None:
            p_suit, p_pts = partner_bid
            my_est = estimate(hand, p_suit)
            combined = p_pts + my_est
            target = est_to_target(combined)
            if target > current_best:
                return p_suit, target

        suits = ["C", "K", "P", "T"]
        best_suit, best_est = None, 0
        for suit in suits:
            est = estimate(hand, suit)
            if est > best_est:
                best_est, best_suit = est, suit

        if best_est < BID_THRESHOLD:
            return None

        target = est_to_target(best_est)
        if target <= current_best:
            return None

        return best_suit, target

    # ──────────────────────────────────────────────────────────────────────
    # UTILITAIRES
    # ──────────────────────────────────────────────────────────────────────

    def _card_val(self, card, trump):
        from belote.rules.points import dict_atout, dict_non_atout
        if card.suit == trump:
            return dict_atout.get(card.rank, 0)
        return dict_non_atout.get(card.rank, 0)

    def _min_card(self, cards, trump):
        return min(cards, key=lambda c: self._card_val(c, trump))

    def _max_card(self, cards, trump):
        return max(cards, key=lambda c: self._card_val(c, trump))

    def _trump_rank(self, card):
        return _trump_strength(card.rank)

    def _enemy_trumps_remain(self, trump, played_cards, player_idx, partner_idx, my_hand_cards):
        """Vrai si des atouts adverses n'ont pas encore été joués."""
        all_trump_ranks = set(TRUMP_ORDER)
        played_trump_ranks = {c.rank for c in played_cards if c.suit == trump}
        my_trump_ranks = {c.rank for c in my_hand_cards if c.suit == trump}
        remaining = all_trump_ranks - played_trump_ranks - my_trump_ranks
        return len(remaining) > 0

    def _as_fallen(self, trump, played_cards):
        """Vrai si l'As d'atout est tombé."""
        return any(c.suit == trump and c.rank == "A" for c in played_cards)

    def _count_enemy_trumps_left(self, trump, played_cards, my_hand_cards):
        """Nombre d'atouts restants hors ma main."""
        all_trump_ranks = set(TRUMP_ORDER)
        played = {c.rank for c in played_cards if c.suit == trump}
        mine = {c.rank for c in my_hand_cards if c.suit == trump}
        return len(all_trump_ranks - played - mine)

    def _suits_count(self, cards, trump):
        """Retourne un dict suit→liste de cartes pour les non-atouts."""
        d = defaultdict(list)
        for c in cards:
            if c.suit != trump:
                d[c.suit].append(c)
        return d

    def _has_void(self, suit, played_cards, my_hand_cards, trump):
        """Estime si les adversaires peuvent être vides d'une couleur."""
        # Simple : combien de cartes de ce suit ont été jouées
        played_suit = [c for c in played_cards if c.suit == suit]
        my_suit = [c for c in my_hand_cards if c.suit == suit]
        return len(played_suit) + len(my_suit) >= 6  # 8 cartes par couleur − 2 chez partenaire probable

    # ──────────────────────────────────────────────────────────────────────
    # DÉTECTION DES SIGNAUX DU PARTENAIRE
    # ──────────────────────────────────────────────────────────────────────

    def _detect_partner_signal(self, tricks_history, partner_idx, player_idx, trump):
        """Retourne la couleur signalée par le partenaire, ou None."""
        from belote.game.trick import trick_winner as tw
        small_signal = None
        has_ten_signal = {}
        no_ace_suits = set()

        for trick in tricks_history:
            suit_asked = trick["suit_asked"]
            seq = trick.get("play_sequence", [])
            partner_card = trick["cards"].get(partner_idx)
            if partner_card is None:
                continue

            pre_seq = []
            for (p, c) in seq:
                if p == partner_idx:
                    break
                pre_seq.append((p, c))

            if pre_seq:
                pre_map = [None] * 4
                for (p, c) in pre_seq:
                    pre_map[p] = c
                current_winner = tw(pre_map, suit_asked, trump)
            else:
                current_winner = None

            # Appel classique : petite carte défaussée hors couleur demandée et hors atout
            if (small_signal is None
                    and partner_card.suit != suit_asked
                    and partner_card.suit != trump
                    and partner_card.rank in SMALL_RANKS):
                small_signal = partner_card.suit

            # As posé quand j'étais maître → partenaire a le 10
            if (partner_card.rank == "A"
                    and partner_card.suit != trump
                    and current_winner == player_idx):
                has_ten_signal[partner_card.suit] = True

            # 10 posé quand j'étais maître → partenaire n'a pas l'As
            if (partner_card.rank == "10"
                    and partner_card.suit != trump
                    and current_winner == player_idx):
                no_ace_suits.add(partner_card.suit)

        if small_signal:
            return small_signal
        for suit in has_ten_signal:
            if suit not in no_ace_suits:
                return suit
        return None

    def _detect_my_signals_sent(self, tricks_history, player_idx, trump):
        """Analyse ce que j'ai moi-même signalé pour éviter la redondance."""
        signals = set()
        for trick in tricks_history:
            my_card = trick["cards"].get(player_idx)
            if my_card and my_card.suit != trump and my_card.rank in SMALL_RANKS:
                signals.add(my_card.suit)
        return signals

    # ──────────────────────────────────────────────────────────────────────
    # LOGIQUE DE JEU PRINCIPALE
    # ──────────────────────────────────────────────────────────────────────

    def choose(self, valid_cards, trump=None, context=None):
        if context is None or trump is None:
            self.last_rule_used = RULE_DEFAULT_MIN
            return random.choice(valid_cards)

        player_idx        = context["player_idx"]
        self._context     = context  # pour les sous-méthodes
        partner_idx       = context["partner_idx"]
        leading           = context["leading"]
        suit_asked        = context["suit_asked"]
        partner_is_master = context["partner_is_master"]
        master_card       = context["master_card"]
        master_player_idx = context["master_player_idx"]
        played_cards      = context["played_cards"]
        trick_num         = context["trick_num"]
        tricks_history    = context.get("tricks_history", [])
        trick_so_far      = context.get("trick_so_far", [])

        trump_cards    = [c for c in valid_cards if c.suit == trump]
        non_trump      = [c for c in valid_cards if c.suit != trump]
        my_trump_ranks = {c.rank for c in trump_cards}
        by_suit        = self._suits_count(non_trump, trump)

        # ── Adversaire preneur + partenaire a joué → règles de suivi ─────────
        taker_idx_c = context.get("taker_idx")
        enemy_is_taker_c = (taker_idx_c is not None
                            and taker_idx_c != player_idx
                            and taker_idx_c != partner_idx)
        if enemy_is_taker_c and not leading and trick_so_far:
            result = self._choose_follow_enemy_taker(
                valid_cards, trump, non_trump, by_suit,
                player_idx, partner_idx, suit_asked, trick_so_far
            )
            if result is not None:
                return result

        # ── OUVRIR LE PLI ─────────────────────────────────────────────────
        if leading:
            return self._choose_lead(
                valid_cards, trump, trump_cards, non_trump, my_trump_ranks, by_suit,
                player_idx, partner_idx, played_cards, trick_num, tricks_history
            )

        # ── SUIVRE ────────────────────────────────────────────────────────
        position = len(trick_so_far)  # 0=1er, 1=2e, 2=3e, 3=4e joueur

        if partner_is_master:
            return self._choose_partner_master(
                valid_cards, trump, trump_cards, non_trump, my_trump_ranks, by_suit,
                player_idx, partner_idx, played_cards, trick_num, tricks_history,
                master_card, position
            )
        else:
            return self._choose_enemy_master(
                valid_cards, trump, trump_cards, non_trump, my_trump_ranks, by_suit,
                player_idx, partner_idx, played_cards, trick_num, tricks_history,
                master_card, master_player_idx, suit_asked, position
            )

    # ──────────────────────────────────────────────────────────────────────
    # A) OUVERTURE
    # ──────────────────────────────────────────────────────────────────────

    def _choose_lead(self, valid_cards, trump, trump_cards, non_trump, my_trump_ranks,
                     by_suit, player_idx, partner_idx, played_cards, trick_num, tricks_history):

        # ── Adversaire preneur → séquence spéciale ──────────────────────────
        taker_idx = getattr(self, "_context", {}).get("taker_idx")
        enemy_is_taker = (taker_idx is not None
                          and taker_idx != player_idx
                          and taker_idx != partner_idx)
        if enemy_is_taker:
            return self._choose_lead_enemy_taker(
                valid_cards, trump, trump_cards, non_trump,
                by_suit, player_idx, played_cards, tricks_history
            )

        enemy_trumps = self._count_enemy_trumps_left(trump, played_cards, valid_cards)

        # ── Règle 1a : V + 9 + ≥3 atouts → tirer (V d'abord, puis 9) ──
        if ("V" in my_trump_ranks and "9" in my_trump_ranks and len(trump_cards) >= 3
                and enemy_trumps > 0):
            if not self._drew_trump_this_hand:
                self._drew_trump_this_hand = True
                self.last_rule_used = RULE_DRAW_TRUMP_JACK_NINE
                return next(c for c in trump_cards if c.rank == "V")
            if self._drew_trump_this_hand and not self._drew_nine_this_hand:
                self._drew_nine_this_hand = True
                self.last_rule_used = RULE_CONTINUE_DRAWING_NINE
                return next(c for c in trump_cards if c.rank == "9")

        # ── Règle 1b : V + ≥3 atouts sans 9 → jouer V, observer ──
        if ("V" in my_trump_ranks and "9" not in my_trump_ranks
                and len(trump_cards) >= 3 and enemy_trumps > 0
                and not self._drew_trump_this_hand):
            self._drew_trump_this_hand = True
            self.last_rule_used = RULE_DRAW_TRUMP_JACK_LENGTH
            return next(c for c in trump_cards if c.rank == "V")

        # ── Règle P : partenaire preneur → jouer de l'atout en soutien ──
        taker_idx = getattr(self, "_context", {}).get("taker_idx")
        partner_is_taker = (taker_idx is not None and taker_idx == partner_idx)
        if partner_is_taker and trump_cards and enemy_trumps > 0:
            if "9" in my_trump_ranks:
                # Garder le 9, jouer la plus petite carte d'atout
                self.last_rule_used = RULE_SUPPORT_TAKER_SMALL
                return self._min_card(trump_cards, trump)
            else:
                # Pas de 9, montrer la plus grosse
                self.last_rule_used = RULE_SUPPORT_TAKER_BIG
                return self._max_card(trump_cards, trump)

        # ── Règle 2 : répondre au signal du partenaire ──
        signal_suit = self._detect_partner_signal(tricks_history, partner_idx, player_idx, trump)
        if signal_suit and signal_suit in by_suit:
            self.last_rule_used = RULE_ANSWER_PARTNER_SIGNAL
            return self._min_card(by_suit[signal_suit], trump)

        # ── Règle 18 : 10 devenu maître (As atout tombé + plus d'atouts adverses) ──
        ten_master = self._find_ten_master(non_trump, trump, played_cards, valid_cards)
        if ten_master:
            self.last_rule_used = RULE_PLAY_MASTER_TEN
            return ten_master

        # ── Règle 19 : As hors atout (choisir la couleur la plus longue en premier) ──
        ace_suits = [(s, cards) for s, cards in by_suit.items()
                     if any(c.rank == "A" for c in cards)]
        if ace_suits:
            # Priorité : couleur où on a As+10 → signal fort
            as_ten = [(s, cards) for s, cards in ace_suits
                      if any(c.rank == "10" for c in cards)]
            if as_ten:
                s, cards = max(as_ten, key=lambda x: len(x[1]))
                self.last_rule_used = RULE_PLAY_ACE_TEN
                return next(c for c in cards if c.rank == "A")
            # Sinon couleur la plus longue avec As
            s, cards = max(ace_suits, key=lambda x: len(x[1]))
            self.last_rule_used = RULE_PLAY_LONGEST_SUIT_ACE
            return next(c for c in cards if c.rank == "A")

        # ── Règle 6 : créer une chicane (singleton < 10 hors atout) ──
        singletons = [(s, cards) for s, cards in by_suit.items()
                      if len(cards) == 1 and cards[0].rank not in ("A", "10")]
        if singletons:
            s, cards = singletons[0]
            self.last_rule_used = RULE_CREATE_VOID
            return cards[0]

        # ── Règle 5 : faire un appel (petite carte si As + autre dans même couleur) ──
        already_signaled = self._detect_my_signals_sent(tricks_history, player_idx, trump)
        for s, cards in by_suit.items():
            ranks = {c.rank for c in cards}
            if "A" in ranks and len(cards) >= 2 and s not in already_signaled:
                smalls = [c for c in cards if c.rank != "A"]
                self.last_rule_used = RULE_SIGNAL_ACE
                return self._min_card(smalls, trump)

        # ── Règle par défaut : carte la moins chère ──
        self.last_rule_used = RULE_DEFAULT_MIN
        return self._min_card(valid_cards, trump)



    def _choose_follow_enemy_taker(self, valid_cards, trump, non_trump,
                                    by_suit, player_idx, partner_idx,
                                    suit_asked, trick_so_far):
        """
        Quand adversaire a pris et que mon partenaire a déjà joué dans ce pli :
        - Partenaire joue petite carte (7/8/D/R) :
            → 50% chicane, 50% appel 10 → dans les deux cas, donner des points
              (plus grosse carte à la couleur demandée)
        - Partenaire joue un As :
            → jouer ma plus grosse carte à la couleur (pour maximiser le pli)
        Retourne None si la règle ne s'applique pas (pas de carte partenaire trouvée,
        ou partenaire n'a joué ni petite ni As).
        """
        # Trouver la carte jouée par le partenaire dans ce pli
        partner_card = next((c for p, c in trick_so_far if p == partner_idx), None)
        if partner_card is None:
            return None  # partenaire n'a pas encore joué

        partner_played_small = partner_card.rank in SMALL_RANKS   # 7 8 D R
        partner_played_ace   = partner_card.rank == "A"

        if not (partner_played_small or partner_played_ace):
            return None  # pas un signal reconnu

        rule = RULE_ADV_GIVE_POINTS_ACE if partner_played_ace else RULE_ADV_GIVE_POINTS_SIG

        # Cartes de la couleur demandée
        suit_cards = by_suit.get(suit_asked, []) if suit_asked else []
        # Inclure atout si la couleur demandée EST l'atout
        if suit_asked == trump:
            suit_cards = [c for c in valid_cards if c.suit == trump]

        if suit_cards:
            self.last_rule_used = rule
            return self._max_card(suit_cards, trump)

        # Pas de carte à la couleur → plus grosse carte hors-atout disponible
        if non_trump:
            self.last_rule_used = rule
            return self._max_card(non_trump, trump)

        return None  # rien à donner, on laisse la logique normale

    def _choose_lead_enemy_taker(self, valid_cards, trump, trump_cards, non_trump,
                                  by_suit, player_idx, played_cards, tricks_history):
        """
        Séquence quand l'adversaire a pris et que j'ouvre :
          1. As dans la couleur la plus courte
          2. Autres As
          3. 10 d'une couleur dont j'ai déjà joué l'As
          4. Singleton non-10
          5. Plus faible dans une couleur qui contient un 10 (garder le 10)
          6. Plus faible hors-atout
        """
        # Mes As joués dans les plis précédents
        my_played_ace_suits = set()
        for trick in tricks_history:
            for (pidx, card) in trick.get("play_sequence", []):
                if pidx == player_idx and card.rank == "A" and card.suit != trump:
                    my_played_ace_suits.add(card.suit)

        # 1. As dans la couleur la plus courte
        ace_suits = [(s, cards) for s, cards in by_suit.items()
                     if any(c.rank == "A" for c in cards)]
        if ace_suits:
            s, cards = min(ace_suits, key=lambda x: len(x[1]))
            self.last_rule_used = RULE_ADV_ACE_SHORT
            return next(c for c in cards if c.rank == "A")

        # 2. Autre As (fallback si le min ci-dessus n'a pas marché — normalement redondant)
        for s, cards in by_suit.items():
            for c in cards:
                if c.rank == "A":
                    self.last_rule_used = RULE_ADV_ACE
                    return c

        # 3. 10 dans une couleur dont j'ai joué l'As
        for suit in my_played_ace_suits:
            if suit in by_suit:
                tens = [c for c in by_suit[suit] if c.rank == "10"]
                if tens:
                    self.last_rule_used = RULE_ADV_TEN_AFTER_ACE
                    return tens[0]

        # 4. Singleton non-10
        for s, cards in by_suit.items():
            if len(cards) == 1 and cards[0].rank != "10":
                self.last_rule_used = RULE_ADV_SINGLETON
                return cards[0]

        # 5. Couleur avec un 10 et d'autres cartes → jouer la plus faible (pas le 10)
        for s, cards in by_suit.items():
            if any(c.rank == "10" for c in cards) and len(cards) > 1:
                others = [c for c in cards if c.rank != "10"]
                if others:
                    self.last_rule_used = RULE_ADV_AVOID_TEN
                    return self._min_card(others, trump)

        # 6. Plus faible hors-atout
        if non_trump:
            self.last_rule_used = RULE_ADV_MIN
            return self._min_card(non_trump, trump)

        # Fallback
        self.last_rule_used = RULE_DEFAULT_MIN
        return self._min_card(valid_cards, trump)

    def _find_ten_master(self, non_trump, trump, played_cards, my_hand):
        """Retourne un 10 non-atout devenu maître (As tombé, pas d'atouts adverses)."""
        enemy_trumps = self._count_enemy_trumps_left(trump, played_cards, my_hand)
        if enemy_trumps > 0:
            return None
        for c in non_trump:
            if c.rank == "10":
                suit = c.suit
                as_fallen = any(pc.suit == suit and pc.rank == "A" for pc in played_cards)
                if as_fallen:
                    return c
        return None

    # ──────────────────────────────────────────────────────────────────────
    # B) PARTENAIRE EST MAÎTRE
    # ──────────────────────────────────────────────────────────────────────

    def _choose_partner_master(self, valid_cards, trump, trump_cards, non_trump,
                                my_trump_ranks, by_suit, player_idx, partner_idx,
                                played_cards, trick_num, tricks_history,
                                master_card, position):

        # ── Appel : As + petite carte même couleur → jouer la petite (signal j'ai l'As) ──
        already_signaled = self._detect_my_signals_sent(tricks_history, player_idx, trump)
        for s, cards in by_suit.items():
            ranks = {c.rank for c in cards}
            if "A" in ranks and len(cards) >= 2 and s not in already_signaled:
                smalls = [c for c in cards if c.rank != "A"]
                self.last_rule_used = RULE_SIGNAL_ACE
                return self._min_card(smalls, trump)

        # ── Mettre des points : As (signale qu'on a le 10) ou 10 (signale pas d'As) ──
        valuables = [c for c in non_trump if c.rank in ("A", "10")]
        if valuables:
            self.last_rule_used = RULE_GIVE_POINTS
            return self._max_card(valuables, trump)

        # ── Carte la moins chère hors atout ──
        if non_trump:
            self.last_rule_used = RULE_DISCARD_MINIMUM
            return self._min_card(non_trump, trump)

        # ── Forcé en atout → minimum ──
        if trump_cards:
            self.last_rule_used = RULE_CUT_MINIMUM
            return self._min_card(trump_cards, trump)

        self.last_rule_used = RULE_DEFAULT_MIN
        return self._min_card(valid_cards, trump)

    # ──────────────────────────────────────────────────────────────────────
    # C) ADVERSAIRE EST MAÎTRE
    # ──────────────────────────────────────────────────────────────────────

    def _choose_enemy_master(self, valid_cards, trump, trump_cards, non_trump,
                              my_trump_ranks, by_suit, player_idx, partner_idx,
                              played_cards, trick_num, tricks_history,
                              master_card, master_player_idx, suit_asked, position):

        is_4th = (position == 3)

        # ── Règle 20 : 4e joueur → jouer la plus petite carte qui gagne ──
        if is_4th:
            winning = self._smallest_winner(valid_cards, trump, master_card, suit_asked)
            if winning:
                self.last_rule_used = RULE_WIN_WITH_MINIMUM
                return winning
            self.last_rule_used = RULE_DISCARD_MINIMUM
            return self._min_card(valid_cards, trump)

        # ── Couper si on a des atouts ──
        if trump_cards and (not non_trump or suit_asked == trump):
            self.last_rule_used = RULE_CUT_MINIMUM
            return self._min_card(trump_cards, trump)

        # ── Couper si la couleur demandée est absente (valid_play autorise l'atout) ──
        suited = [c for c in valid_cards if c.suit == suit_asked]
        if not suited and trump_cards:
            self.last_rule_used = RULE_CUT_MINIMUM
            return self._min_card(trump_cards, trump)

        # ── Se défausser du minimum ──
        self.last_rule_used = RULE_DISCARD_MINIMUM
        return self._min_card(valid_cards, trump)

    def _smallest_winner(self, valid_cards, trump, master_card, suit_asked):
        """Plus petite carte qui bat master_card, ou None."""
        if master_card is None:
            return None

        from belote.rules.valid_play import Trump_order as to_list
        trump_strength = {r: i for i, r in enumerate(to_list)}  # 0=plus fort

        def beats(card, master):
            if card.suit == trump and master.suit != trump:
                return True
            if card.suit == trump and master.suit == trump:
                return trump_strength.get(card.rank, 99) < trump_strength.get(master.rank, 99)
            if card.suit != trump and master.suit != trump:
                if card.suit != master.suit:
                    return False
                # même couleur hors atout : As > 10 > R > D > V > 9 > 8 > 7
                nt_order = ["A", "10", "R", "D", "V", "9", "8", "7"]
                nt_str = {r: i for i, r in enumerate(nt_order)}
                return nt_str.get(card.rank, 99) < nt_str.get(master.rank, 99)
            return False

        winners = [c for c in valid_cards if beats(c, master_card)]
        if not winners:
            return None
        # Parmi les gagnants → la moins chère (valeur en points)
        return self._min_card(winners, trump)

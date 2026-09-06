# Référence complète — Belote / Coinche

> Ce fichier est la source de vérité pour les règles de bid, de jeu et du
> Monte Carlo. Il est généré directement depuis le code source.
> Relire ce fichier avant d'implémenter ou de modifier quoi que ce soit.

---

## 0. Constantes fondamentales

```
ALL_SUITS  = ["K", "P", "C", "T"]   (K=♥  P=♠  C=♦  T=♣)
ALL_RANKS  = ["7", "8", "D", "R", "10", "A", "9", "V"]

TRUMP_ORDER (du plus FORT au plus faible) = ["V", "9", "A", "10", "R", "D", "8", "7"]
Trump_order (du plus FAIBLE au plus fort) = ["7", "8", "D",  "R", "10",  "A", "9", "V"]
  → valid_play.py utilise l'index dans Trump_order : index élevé = carte forte
  → heuristic_bot.py utilise TRUMP_ORDER (index 0 = plus fort)

NON-TRUMP strength = A > 10 > R > D > V > 9 > 8 > 7

SMALL_RANKS = {"7", "8", "D", "R"}   (cartes "petites" pour les signaux)
BID_THRESHOLD = 70                    (estimation minimale pour annoncer)
```

---

## 1. Enchères (`bidding.py`, `heuristic_bot.py`)

### 1.1 Paliers valides
```
80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 150, 155, 160
Couleurs : C / K / P / T / SA / TA
```

### 1.2 Fin des enchères
3 passes consécutives ferment les enchères.  
`run_bidding()` retourne `(Bidding, contract_team_int)` où `contract_team_int ∈ {0, 1}`.

### 1.3 Estimation `estimate(hand, trump)`
| Composante | Points |
|---|---|
| V atout | +20 |
| 9 atout | +14 |
| A atout | +6 |
| 10 atout | +5 |
| Suite sure depuis V (V→9→A→10→…) | comptée en `sure_tricks` |
| As hors-atout | +1 sure_trick chacun |
| Si sure_tricks > 2 | +5 × sure_tricks |
| Chaque atout au-delà de 2 | +5 par atout |
| Chicane hors-atout (couleur absente) | +10 par chicane |
| As hors-atout | +11 par As |
| 10 hors-atout (sans As, couleur ≥2 cartes) | +5 par 10 |
| Singleton hors-atout | +5 par singleton |
| R+D en atout ET score > 70 | +20 |
| V+9+A atout ET As+10 côté | +25 |
| V+9+10 atout ET As+10 côté | +20 |
| V+9+autre atout ET As+10 côté | +10 |

### 1.4 `choose_bid(hand, current_best, partner_bid)`
1. Si partenaire a annoncé `(p_suit, p_pts)` :
   - `my_est = estimate(hand, p_suit)`
   - `combined = p_pts + my_est`
   - `target = est_to_target(combined)`
   - Si `target > current_best` → annoncer `(p_suit, target)`
2. Sinon : évaluer les 4 couleurs, garder la meilleure (`best_est`)
   - Si `best_est < 70` → passer
   - Sinon `target = est_to_target(best_est)`; si `target <= current_best` → passer

```
est_to_target(est):
  ≤ 70 → 80
  ≤ 79 → 85
  ≤ 89 → 90
  else → ceil(est / 5) * 5
```

---

## 2. Règles de jeu valide (`valid_play.py`)

Signature : `valid_play(hand, suit_asked, trump, partner_is_master, master_card)`  
Retourne la liste des cartes jouables (sous-ensemble de `hand`).

| Cas | Condition | Cartes jouables |
|---|---|---|
| 0 | `suit_asked is None` (1er pli ou liberté totale) | toute la main |
| 1 | `suit_asked == trump` ET pas d'atout | toute la main (défausse libre) |
| 2 | `suit_asked == trump` ET a des atouts | monter si possible, sinon pisser atout |
| 3 | `suit_asked != trump` ET a des cartes couleur | suivre obligatoirement |
| 4 | `suit_asked != trump`, pas de couleur, partenaire maître | défausse libre |
| 5 | `suit_asked != trump`, pas de couleur, adversaire maître, a des atouts, adversaire déjà en atout | monter en atout si possible, sinon pisser atout |
| 6 | `suit_asked != trump`, pas de couleur, adversaire maître, a des atouts, adversaire en hors-atout | couper (n'importe quel atout) |
| 7 | `suit_asked != trump`, pas de couleur, pas d'atout | défausse libre |

**Détail cas 2 (atout demandé) :**
```python
up   = [c for c in hand_suits if Trump_order.index(c.rank) > Trump_order.index(master_card.rank)]
down = [c for c in hand_suits if Trump_order.index(c.rank) <= Trump_order.index(master_card.rank)]
return up if up else down
```

**Détail cas 5 (adversaire maître en atout) :**
```python
higher = [c for c in hand_trumps if Trump_order.index(c.rank) > Trump_order.index(master_card.rank)]
return higher if higher else hand_trumps
```

---

## 3. Heuristique V1 (`heuristic_bot.py`)

### 3.1 Ouverture de pli — partenaire preneur ou libre

**Règle 1a** `DRAW_TRUMP_JACK_NINE`  
Conditions : V + 9 en atout, ≥3 atouts, atouts adverses > 0  
→ Jouer V (1er fois), puis 9 (2e fois si déjà tiré le V).

**Règle 1b** `DRAW_TRUMP_JACK_LENGTH`  
Conditions : V en atout, pas de 9, ≥3 atouts, atouts adverses > 0, pas encore tiré  
→ Jouer V, observer.

**Règle P** `SUPPORT_TAKER_BIG` / `SUPPORT_TAKER_SMALL`  
Conditions : partenaire est le preneur, a des atouts, atouts adverses > 0  
→ Si on a le 9 : garder le 9, jouer le minimum d'atout (`SUPPORT_TAKER_SMALL`)  
→ Sinon : jouer le maximum d'atout (`SUPPORT_TAKER_BIG`)

**Règle 2** `ANSWER_PARTNER_SIGNAL`  
→ Répondre au signal détecté du partenaire (jouer petit dans la couleur signalée).

**Règle 18** `PLAY_MASTER_TEN`  
Conditions : As de la couleur tombé + 0 atouts adverses restants  
→ Jouer le 10 hors-atout devenu maître.

**Règle 19** `PLAY_ACE_TEN` / `PLAY_LONGEST_SUIT_ACE`  
→ Jouer un As hors-atout.  
  - Priorité : couleur avec As+10 (la plus longue), règle `PLAY_ACE_TEN`  
  - Sinon : couleur la plus longue avec As, règle `PLAY_LONGEST_SUIT_ACE`

**Règle 6** `CREATE_VOID`  
→ Jouer un singleton hors-atout qui n'est ni As ni 10 (créer une chicane).

**Règle 5** `SIGNAL_ACE`  
Conditions : As + ≥1 autre carte dans la même couleur, pas encore signalé cette couleur  
→ Jouer la plus petite carte de cette couleur (signal j'ai l'As).

**Défaut** `DEFAULT_MIN` → carte la moins chère disponible.

---

### 3.2 Ouverture de pli — adversaire preneur

**Règle ADV_ACE_SHORT** → As dans la couleur la plus courte.  
**Règle ADV_ACE** → Autre As (fallback).  
**Règle ADV_TEN_AFTER_ACE** → 10 dans une couleur dont j'ai déjà joué l'As.  
**Règle ADV_SINGLETON** → Singleton non-10.  
**Règle ADV_AVOID_TEN** → Faible dans une couleur qui contient un 10 (protéger le 10).  
**Règle ADV_MIN** → Plus faible hors-atout.  
**Défaut** → `DEFAULT_MIN`.

---

### 3.3 Suivi — partenaire maître

**SIGNAL_ACE** → As + autre même couleur, pas encore signalé → petite carte (signal).  
**GIVE_POINTS** → As ou 10 hors-atout → jouer le plus gros.  
**DISCARD_MINIMUM** → Rien de valeur → minimum hors-atout.  
**CUT_MINIMUM** → Forcé atout → minimum d'atout.

---

### 3.4 Suivi — adversaire maître

**RULE_WIN_WITH_MINIMUM** (4e joueur) → plus petite carte qui gagne.  
**CUT_MINIMUM** → couper si on a des atouts (et pas de carte couleur, ou couleur = atout).  
**DISCARD_MINIMUM** → sinon minimum.

---

### 3.5 Suivi — adversaire preneur, partenaire a déjà joué

**ADV_GIVE_POINTS_SIG** : partenaire a joué petite (7/8/D/R) → max de la couleur demandée.  
**ADV_GIVE_POINTS_ACE** : partenaire a joué un As → max de la couleur demandée.  
(Si aucune carte à la couleur → max hors-atout)

---

### 3.6 Détection des signaux du partenaire

`_detect_partner_signal` retourne la couleur signalée ou `None` :
1. **Signal appel classique** : partenaire joue petite (SMALL_RANKS) hors couleur demandée et hors atout.
2. **Signal As posé quand j'étais maître** → partenaire a le 10 dans cette couleur.
3. **Signal 10 posé quand j'étais maître** → partenaire n'a PAS l'As.

---

## 4. Heuristique V2 (`heuristic_bot_v2.py`)

Améliorations par rapport à V1 :

### 4.1 Mémorisation des chicanes certaines

`_compute_player_voids(tricks_history, trump)` → `{player_idx: set(suits)}`

Règles d'inférence :
- Joueur n'a pas suivi la couleur demandée → vide dans cette couleur.
- Joueur n'a pas suivi ET a joué hors-atout (défausse) → vide en atout aussi.

### 4.2 Comptage atouts adverses corrigé

`_count_enemy_trumps_left` : si les DEUX adversaires sont connus vides en atout → retourne 0.  
(Inutile de tirer l'atout.)

### 4.3 Jeu de l'As conditionnel

`_certain_cut(suit, trump, player_idx)` → True si ≥1 adversaire est connu vide dans `suit` ET pas connu vide en atout.

`SKIP_RISKY_ACE` : avant de jouer un As hors-atout, vérifier `_certain_cut`.  
- As sûrs → `SAFE_ACE_TEN` ou `SAFE_ACE_LONGEST`  
- Tous risqués → sauter vers chicane / appel / puis jouer quand même en dernier recours.

---

## 5. Monte Carlo V3 (`heuristic_bot_v3.py`)

### 5.1 Paramètres

| Paramètre | Valeur |
|---|---|
| `MC_START_TRICK` | 4 (MC activé à partir du 4e pli) |
| `TIME_BUDGET` | 2.0 secondes par décision |
| Activation | seulement si `leading == True` |
| Fallback | Si MC retourne None → V2 heuristique |

### 5.2 Cartes connues

```
my_keys     = {(suit, rank) for c in full_hand}
played_keys = cartes jouées dans tricks_history + trick_so_far
unknown     = ALL_CARDS - my_keys - played_keys
```

`full_hand` = main complète du bot au début du pli (fourni dans `context["full_hand"]`).

### 5.3 Taille des mains des autres joueurs

```python
hand_sizes[p] = 8 - (len(tricks_history) + (1 if p a déjà joué dans trick_so_far else 0))
```

Vérification : `sum(hand_sizes) == len(unknown)` ; sinon fallback.

### 5.4 Simulation

```python
n_tricks = len(full_hand)   # plis restants (ex: 5 au trick 4)
_ForceFirst(my_card)        # force my_card au 1er appel, puis V2 ensuite
play_hand(n_tricks=n_tricks)  # jouer uniquement les plis restants
```

**CRITIQUE** : `sim_my_hand = list(full_hand)` (conserver toutes les cartes, pas full_hand - my_card).

---

### 5.5 Contraintes de distribution

#### A) Voids — `_build_voids(tricks_history, trump)`

Même logique que V2 `_compute_player_voids` :
- N'a pas suivi → vide dans couleur demandée.
- N'a pas suivi + joué hors-atout → vide en atout aussi.

#### B) Fixed — `_build_fixed(taker_idx, trump, bid_points, my_keys, played_keys, other_players)`

Si adversaire est preneur :
- `bid_points >= 80` : Valet d'atout probablement chez le preneur (si non vu).
- `bid_points >= 90` : 9 d'atout probablement chez le preneur (si non vu).

Ces cartes sont forcées dans la distribution (`fixed = {(suit, rank): player_idx}`).

#### C) Signaux d'appel — `_build_signals(tricks_history, trump, player_idx, my_keys, played_keys)`

**Définition exacte du signal d'appel :**
Un joueur (PAS le meneur, PAS moi-même) joue une petite carte (SMALL_RANKS) d'une couleur
différente de la couleur demandée ET différente de l'atout, ALORS QUE son équipe était
déjà maître du pli AVANT qu'il joue.

→ Ce joueur a soit l'As de cette couleur, soit une chicane dans cette couleur.

```python
# Vérifier que l'équipe était maître avant que le joueur joue
partial = trick_cards[:i]   # cartes jouées avant le joueur i
current_winner = trick_winner(partial, suit_asked, trump)
if current_winner % 2 == pidx % 2:   # même équipe → signal confirmé
    signals[pidx].add(card.suit)
```

Condition supplémentaire : l'As de cette couleur n'est pas encore vu (ni dans ma main ni joué).

#### D) Min trumps taker — dans `_mc_choose`

```python
min_trump_taker = 4 if (bid_points >= 120 and taker_idx in other_players) else 0
```

---

### 5.6 Sampler — `_sample_distribution`

Ordre de placement des cartes :

1. **Cartes fixées** (Valet/9 atout chez preneur) → placées en premier.
2. **Signaux d'appel** : pour chaque signal `(pidx, suit)` :
   - 50% → forcer l'As de cette couleur chez `pidx`
   - 50% → rendre `pidx` void dans cette couleur pour ce sample
3. **Min atouts preneur** (`min_trump_taker`) : si contrat ≥ 120, forcer au moins 4 atouts chez le preneur (compléter avec atouts libres).
4. **Cartes libres restantes** : mélange aléatoire, en respectant les voids.
   - Si aucun joueur éligible (tous vides) → ignorer la contrainte void et placer quand même.

---

### 5.7 Scoring MC

```python
scores[card] += pts[my_team]   # points de mon équipe dans la simulation
best = argmax(scores[c] / counts[c])
```

Si `counts[c] == 0` pour toutes les cartes → argmax retourne la première (score 0/1 = 0).

---

## 6. Context fourni au bot (`hand.py`)

```python
context = {
    "player_idx":        int,
    "partner_idx":       int,
    "leading":           bool,
    "suit_asked":        str | None,
    "partner_is_master": bool,
    "master_card":       Card | None,
    "master_player_idx": int | None,
    "played_cards":      List[Card],   # toutes les cartes jouées depuis le début
    "trick_num":         int,          # 1-indexed
    "tricks_history":    List[dict],   # plis terminés
    "trick_so_far":      List[(int, Card)],  # cartes du pli en cours
    "full_hand":         List[Card],   # main complète du joueur au début de ce pli
    "taker_idx":         int | None,
    "bid_points":        int | None,
}
```

Structure d'un pli dans `tricks_history` :
```python
{
    "suit_asked":     str | None,
    "cards":          {player_idx: Card},       # une carte par joueur
    "play_sequence":  [(player_idx, Card), ...], # ordre de jeu
    "winner":         int,
}
```

---

## 7. Checklist anti-hallucination

- [ ] `Card(suit, rank)` — pas `Card(rank, suit)`
- [ ] Trump fort = V, Trump faible = 7
- [ ] `Trump_order` (valid_play) : index élevé = fort ; `TRUMP_ORDER` (bot) : index 0 = fort
- [ ] `play_hand(n_tricks=N)` — passer N pour les simulations partielles
- [ ] `full_hand` = main COMPLÈTE (avant de jouer la carte forcée dans la sim)
- [ ] Signal d'appel = SUIVEUR (pas le meneur) + équipe DÉJÀ MAÎTRE + petite non-atout autre couleur
- [ ] MC activé seulement si `leading == True` ET `trick_num >= MC_START_TRICK`
- [ ] bid_points : entier (80-160), pas un string
- [ ] contract_team = 0 ou 1 (entier), pas player_idx

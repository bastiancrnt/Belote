"""
Benchmark — V1 / V2 / V3 / V3 Full MC / V3 Selective MC
=========================================================
Chaque confrontation est jouée en deux matchs (équipes croisées)
sur les MÊMES seeds, pour éliminer le biais de position.

Confrontations :
  Full MC    vs V1
  Selective  vs V1
  Full MC    vs V2
  Selective  vs V2
  Full MC    vs Selective
  (V3 original vs V1 — conservé pour référence historique)

Métriques supplémentaires par match :
  – nombre de décisions MC / UNCERTAIN_V2 / V2 pures
  – temps total et débit (donnes/s)
"""

import random
import time
import os
from collections import defaultdict

from belote.game.bidding import run_bidding
from belote.game.hand    import Hand
from belote.core.deck    import Deck
from belote.rules.scoring import apply_contract

from belote.agents.heuristic_bot          import HeuristicBot
from belote.agents.heuristic_bot_v2       import HeuristicBotV2
from belote.agents.heuristic_bot_v2_2     import HeuristicBotV2_2
from belote.agents.heuristic_bot_v3       import MonteCarloBot
from belote.agents.heuristic_bot_v3_variants import (
    MonteCarloBotFull,
    MonteCarloBotSelective,
    RULE_MC_UNCERTAIN_V2,
)
from belote.agents.heuristic_bot_v3 import RULE_MONTE_CARLO, RULE_MC_FORCED

from belote.database.db         import init_db, sync_to_mount
from belote.database.repository import (
    create_game, finish_game,
    create_deal, finish_deal, save_initial_hands,
)


# ── Machine ID → seed de base ─────────────────────────────────────────────────

def get_machine_id():
    path = os.path.join(os.path.dirname(__file__), "machine_id.txt")
    try:
        raw = open(path, "rb").read()
        if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
            text = raw.decode("utf-16")
        else:
            text = raw.decode("utf-8-sig")
        digits = "".join(c for c in text if c.isdigit())
        return int(digits)
    except Exception as e:
        print(f"  [WARN] machine_id.txt illisible ({e}) — fallback machine #1")
        return 1


MACHINE_ID = get_machine_id()
BASE_SEED  = MACHINE_ID * 10_000
print(f"Machine #{MACHINE_ID}  (base seed {BASE_SEED})")


# ── Comptage des règles (décisions MC / fallback) ──────────────────────────

def _count_rules(agents):
    """Retourne {rule: count} pour tous les bots qui ont last_rule_used."""
    counts = defaultdict(int)
    for agent in agents:
        rule = getattr(agent, "last_rule_used", None)
        if rule:
            counts[rule] += 1
    return counts


# ── Match ─────────────────────────────────────────────────────────────────────

def run_match(label_a, label_b, agents, n_donnes, conn, seed,
              update_every=10, verbose=True):
    """
    Joue n_donnes donnes avec les agents donnés.
    agents[0,2] = équipe 0 (label_a), agents[1,3] = équipe 1 (label_b).
    Retourne (scores, elapsed_s, rule_counts).
    """
    random.seed(seed)
    scores       = [0, 0]
    rule_totals  = defaultdict(int)
    done         = 0
    first_player = 0
    t_start      = time.time()

    v_a = agents[0].BOT_VERSION if hasattr(agents[0], "BOT_VERSION") else "unknown"
    v_b = agents[1].BOT_VERSION if hasattr(agents[1], "BOT_VERSION") else "unknown"
    game_id = create_game(conn, bot_version=f"{v_a}_vs_{v_b}", seed=seed)

    while done < n_donnes:
        d = Deck()
        d.shuffle()
        hands = d.deal()
        bidding, contract_team = run_bidding(
            first_player, hands=hands, agents=agents, verbose=False)
        if bidding is None:
            first_player = (first_player + 1) % 4
            continue

        taker_idx = contract_team

        deal_id = create_deal(
            conn, game_id, done + 1,
            dealer=first_player,
            first_player=(first_player + 1) % 4,
            trump=bidding.suit,
            taker=taker_idx,
            taker_team=contract_team,
            contract_value=bidding.points,
            bot_version=f"{v_a}_vs_{v_b}",
        )
        save_initial_hands(conn, deal_id, hands)

        h = Hand(hands, bidding.suit, bidding.points, agents,
                 verbose=False, first_player=first_player)
        pts0, pts1 = h.play_hand()
        s0, s1 = apply_contract(pts0, pts1, bidding.points, contract_team)
        scores[0] += s0
        scores[1] += s1

        # Comptage des règles après chaque donne
        for rule, cnt in _count_rules(agents).items():
            rule_totals[rule] += cnt

        finish_deal(conn, deal_id, s0, s1, last_trick_winner=0)

        done        += 1
        first_player = (first_player + 1) % 4

        if verbose and done % update_every == 0:
            elapsed = time.time() - t_start
            rate    = done / elapsed
            eta     = (n_donnes - done) / rate if rate > 0 else 0
            diff    = scores[0] - scores[1]
            sign    = "+" if diff >= 0 else ""
            print(f"  [{done:>3}/{n_donnes}]  {label_a}={scores[0]}  "
                  f"{label_b}={scores[1]}  diff={sign}{diff}"
                  f"  {rate:.1f} d/s  ETA {eta/60:.1f}min")
            sync_to_mount()

    finish_game(conn, game_id, scores[0], scores[1],
                winner=0 if scores[0] >= scores[1] else 1)
    sync_to_mount()
    elapsed = time.time() - t_start
    return scores, elapsed, dict(rule_totals)


# ── Confrontation (2 matchs croisés sur le même seed) ────────────────────────

def run_matchup(name_a, cls_a, name_b, cls_b, n_donnes, conn, seed,
                verbose=True):
    """
    Joue deux matchs A(eq0)/B(eq1) et B(eq0)/A(eq1) avec le même seed.
    Retourne un dict de résultats agrégés.
    """
    print(f"\n{'='*60}")
    print(f"  {name_a}  vs  {name_b}  ({n_donnes} donnes × 2)")
    print(f"{'='*60}")

    # Match 1 : A eq0 / B eq1
    agents1 = [cls_a(), cls_b(), cls_a(), cls_b()]
    print(f"\n  Match 1 : {name_a}(eq0) vs {name_b}(eq1)")
    s1, t1, r1 = run_match(name_a, name_b, agents1, n_donnes, conn,
                            seed=seed, verbose=verbose)
    print(f"  FINAL  {name_a}={s1[0]}  {name_b}={s1[1]}  "
          f"diff={s1[0]-s1[1]:+d}  ({t1:.0f}s)")
    _print_rules(r1, name_a, name_b)

    # Match 2 : B eq0 / A eq1 — même seed → mêmes cartes, équipes croisées
    agents2 = [cls_b(), cls_a(), cls_b(), cls_a()]
    print(f"\n  Match 2 : {name_b}(eq0) vs {name_a}(eq1)")
    s2, t2, r2 = run_match(name_b, name_a, agents2, n_donnes, conn,
                            seed=seed, verbose=verbose)
    print(f"  FINAL  {name_b}={s2[0]}  {name_a}={s2[1]}  "
          f"diff={s2[1]-s2[0]:+d}  ({t2:.0f}s)")
    _print_rules(r2, name_b, name_a)

    total_a = s1[0] + s2[1]
    total_b = s1[1] + s2[0]
    diff    = total_a - total_b
    sign    = "+" if diff >= 0 else ""
    print(f"\n  ── TOTAL {2*n_donnes} donnes ──")
    print(f"  {name_a}: {total_a}   {name_b}: {total_b}   "
          f"diff {name_a}−{name_b}: {sign}{diff}  "
          f"({diff/(2*n_donnes):+.1f} pts/donne)")

    return {
        "name_a": name_a, "name_b": name_b,
        "total_a": total_a, "total_b": total_b,
        "diff": diff, "per_deal": diff / (2 * n_donnes),
        "n_donnes": 2 * n_donnes,
        "elapsed": t1 + t2,
    }


def _print_rules(rule_counts, name_a, name_b):
    """Affiche un résumé des règles utilisées si des données MC existent."""
    mc   = rule_counts.get(RULE_MONTE_CARLO, 0)
    unc  = rule_counts.get(RULE_MC_UNCERTAIN_V2, 0)
    forc = rule_counts.get(RULE_MC_FORCED, 0)
    total_mc = mc + unc + forc
    if total_mc > 0:
        print(f"    Règles MC : MONTE_CARLO={mc}  "
              f"MC_UNCERTAIN_V2={unc}  MC_FORCED={forc}")


# ── Main ──────────────────────────────────────────────────────────────────────

N    = 200   # donnes par match (200 × 2 = 400 par confrontation)
conn = init_db()

results = []

# Confrontations définies dans le ticket
matchups = [
    ("V3_Full",     MonteCarloBotFull,      "V1",          HeuristicBot),
    ("V3_Selective",MonteCarloBotSelective,  "V1",          HeuristicBot),
    ("V3_Full",     MonteCarloBotFull,      "V2",          HeuristicBotV2),
    ("V3_Selective",MonteCarloBotSelective,  "V2",          HeuristicBotV2),
    ("V3_Full",     MonteCarloBotFull,      "V3_Selective", MonteCarloBotSelective),
    ("V3_orig",     MonteCarloBot,           "V1",          HeuristicBot),  # référence
    ("V2_2",        HeuristicBotV2_2,        "V2",          HeuristicBotV2),
    ("V2_2",        HeuristicBotV2_2,        "V1",          HeuristicBot),
]

for seed_offset, (na, ca, nb, cb) in enumerate(matchups, start=1):
    seed = BASE_SEED + seed_offset
    res  = run_matchup(na, ca, nb, cb, N, conn, seed=seed, verbose=True)
    results.append(res)

# ── Tableau récapitulatif ──────────────────────────────────────────────────────
print(f"\n\n{'='*60}")
print("  RÉCAPITULATIF")
print(f"{'='*60}")
print(f"  {'Confrontation':<30} {'A':>6}  {'B':>6}  {'diff':>7}  {'pts/d':>7}")
print(f"  {'-'*58}")
for r in results:
    label = f"{r['name_a']} vs {r['name_b']}"
    winner = r['name_a'] if r['diff'] > 0 else (r['name_b'] if r['diff'] < 0 else '=')
    flag   = " ★" if r['diff'] > 0 else ("  " if r['diff'] == 0 else "  ")
    print(f"  {label:<30} {r['total_a']:>6}  {r['total_b']:>6}  "
          f"{r['diff']:>+7}  {r['per_deal']:>+7.1f}{flag}")

conn.close()

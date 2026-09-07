import random
import time
import os
from belote.game.bidding import run_bidding
from belote.game.hand    import Hand
from belote.core.deck    import Deck
from belote.agents.heuristic_bot    import HeuristicBot
from belote.agents.heuristic_bot_v3 import MonteCarloBot
from belote.database.db         import init_db, sync_to_mount
from belote.database.repository import (
    create_game, finish_game,
    create_deal, finish_deal, save_initial_hands
)

# ── Machine ID → seed de base ─────────────────────────────────────────────────
def get_machine_id():
    path = os.path.join(os.path.dirname(__file__), "machine_id.txt")
    try:
        return int(open(path).read().strip())
    except Exception:
        return 1

MACHINE_ID = get_machine_id()
BASE_SEED  = MACHINE_ID * 10_000   # ordi 1 → seeds 10001…, ordi 2 → 20001…

print(f"Machine #{MACHINE_ID}  (base seed {BASE_SEED})")

# ── Helpers ───────────────────────────────────────────────────────────────────
def apply_contract(pts0, pts1, contract, contract_team):
    takers = pts0 if contract_team == 0 else pts1
    if takers >= contract:
        # Succes : preneur garde ses points + contrat, defenseur garde ses points
        if contract_team == 0:
            return pts0 + contract, pts1
        else:
            return pts0, pts1 + contract
    else:
        # Chute : preneur = 0, defenseur = contrat + 160
        if contract_team == 0:
            return 0, contract + 160
        else:
            return contract + 160, 0

def bot_version_str(agents):
    return agents[0].BOT_VERSION if hasattr(agents[0], "BOT_VERSION") else "unknown"

# ── Match ─────────────────────────────────────────────────────────────────────
def run_match(label_a, label_b, agents, n_donnes, conn, seed, update_every=10):
    random.seed(seed)
    scores  = [0, 0]
    done    = 0
    first_player = 0
    t_start = time.time()

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

        taker_idx = None
        for i, a in enumerate(agents):
            if hasattr(a, '_context'):
                pass
        # taker = premier joueur de l'équipe preneuse
        taker_idx = contract_team  # 0 ou 1 (approximation)

        deal_id = create_deal(
            conn, game_id, done + 1,
            dealer=first_player,
            first_player=(first_player + 1) % 4,
            trump=bidding.suit,
            taker=taker_idx,
            taker_team=contract_team,
            contract_value=bidding.points,
            bot_version=f"{v_a}_vs_{v_b}"
        )
        save_initial_hands(conn, deal_id, hands)

        db_ctx = {
            'conn': conn,
            'game_id': game_id,
            'deal_id': deal_id,
            'bot_version': f"{v_a}_vs_{v_b}",
        }
        h = Hand(hands, bidding.suit, bidding.points, agents,
                 verbose=False, first_player=first_player,
                 taker_idx=taker_idx, db_context=db_ctx)
        pts0, pts1 = h.play_hand()
        s0, s1 = apply_contract(pts0, pts1, bidding.points, contract_team)
        scores[0] += s0
        scores[1] += s1

        finish_deal(conn, deal_id, s0, s1,
                    last_trick_winner=h.current_player)

        done += 1
        first_player = (first_player + 1) % 4

        if done % update_every == 0:
            elapsed = time.time() - t_start
            rate = done / elapsed
            eta  = (n_donnes - done) / rate if rate > 0 else 0
            diff = scores[0] - scores[1]
            sign = "+" if diff >= 0 else ""
            print(f"  [{done:>3}/{n_donnes}]  {label_a}={scores[0]}  "
                  f"{label_b}={scores[1]}  diff={sign}{diff}"
                  f"  {rate:.1f} d/s  ETA {eta/60:.1f}min")
            sync_to_mount()

    finish_game(conn, game_id, scores[0], scores[1],
                winner=0 if scores[0] >= scores[1] else 1)
    sync_to_mount()
    elapsed = time.time() - t_start
    return scores, elapsed

# ── Main ──────────────────────────────────────────────────────────────────────
N = 200
conn = init_db()
print(f"Benchmark V3 vs V1 — {N} donnes par match\n")

print(f"=== Match 1 : V3(eq0) vs V1(eq1) ===")
agents1 = [MonteCarloBot(), HeuristicBot(), MonteCarloBot(), HeuristicBot()]
s1, t1 = run_match("V3", "V1", agents1, N, conn, seed=BASE_SEED + 1)
print(f"  FINAL  V3={s1[0]}  V1={s1[1]}  diff={s1[0]-s1[1]:+d}  ({t1:.0f}s)\n")

print(f"=== Match 2 : V1(eq0) vs V3(eq1) ===")
agents2 = [HeuristicBot(), MonteCarloBot(), HeuristicBot(), MonteCarloBot()]
s2, t2 = run_match("V1", "V3", agents2, N, conn, seed=BASE_SEED + 2)
print(f"  FINAL  V1={s2[0]}  V3={s2[1]}  diff={s2[1]-s2[0]:+d}  ({t2:.0f}s)\n")

total_v3 = s1[0] + s2[1]
total_v1 = s1[1] + s2[0]
print(f"=== TOTAL ({2*N} donnes) ===")
print(f"  V3 : {total_v3}   V1 : {total_v1}   diff V3-V1 : {total_v3-total_v1:+d}")

conn.close()

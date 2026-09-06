import random
import time
from belote.game.bidding import run_bidding
from belote.game.hand    import Hand
from belote.core.deck    import Deck
from belote.agents.heuristic_bot    import HeuristicBot
from belote.agents.heuristic_bot_v3 import MonteCarloBot

def apply_contract(pts0, pts1, contract, contract_team):
    takers = pts0 if contract_team == 0 else pts1
    total  = pts0 + pts1
    if takers >= contract:
        return pts0, pts1
    return (0, total) if contract_team == 0 else (total, 0)

def run_match(label_a, label_b, agents, n_donnes, seed=42, update_every=10):
    random.seed(seed)
    scores = [0, 0]
    done = 0
    first_player = 0
    t_start = time.time()
    t_last  = t_start
    while done < n_donnes:
        d = Deck()
        d.shuffle()
        hands = d.deal()
        bidding, contract_team = run_bidding(first_player, hands=hands, agents=agents, verbose=False)
        if bidding is None:
            first_player = (first_player + 1) % 4
            continue
        h = Hand(hands, bidding.suit, bidding.points, agents,
                 verbose=False, first_player=first_player)
        pts0, pts1 = h.play_hand()
        s0, s1 = apply_contract(pts0, pts1, bidding.points, contract_team)
        scores[0] += s0
        scores[1] += s1
        done += 1
        first_player = (first_player + 1) % 4

        if done % update_every == 0:
            now = time.time()
            elapsed = now - t_start
            rate = done / elapsed
            eta = (n_donnes - done) / rate if rate > 0 else 0
            diff = scores[0] - scores[1]
            sign = "+" if diff >= 0 else ""
            print(f"  [{done:>3}/{n_donnes}]  {label_a}={scores[0]}  {label_b}={scores[1]}"
                  f"  diff={sign}{diff}"
                  f"  {rate:.1f} d/s  ETA {eta/60:.1f}min")

    elapsed = time.time() - t_start
    return scores, elapsed

N = 200
print(f"Benchmark V3 vs V1 — {N} donnes par match\n")

print(f"=== Match 1 : V3(eq0) vs V1(eq1) ===")
agents1 = [MonteCarloBot(), HeuristicBot(), MonteCarloBot(), HeuristicBot()]
s1, t1 = run_match("V3", "V1", agents1, N, seed=1)
print(f"  FINAL  V3={s1[0]}  V1={s1[1]}  diff={s1[0]-s1[1]:+d}  ({t1:.0f}s)\n")

print(f"=== Match 2 : V1(eq0) vs V3(eq1) ===")
agents2 = [HeuristicBot(), MonteCarloBot(), HeuristicBot(), MonteCarloBot()]
s2, t2 = run_match("V1", "V3", agents2, N, seed=1)
print(f"  FINAL  V1={s2[0]}  V3={s2[1]}  diff={s2[1]-s2[0]:+d}  ({t2:.0f}s)\n")

total_v3 = s1[0] + s2[1]
total_v1 = s1[1] + s2[0]
print(f"=== TOTAL ({2*N} donnes) ===")
print(f"  V3 : {total_v3}   V1 : {total_v1}   diff V3-V1 : {total_v3-total_v1:+d}")

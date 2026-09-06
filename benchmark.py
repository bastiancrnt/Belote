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

def run_match(agents, n_donnes, seed=42):
    random.seed(seed)
    scores = [0, 0]
    done = 0
    first_player = 0
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
    return scores

N = 30
print(f"Benchmark V3 vs V1 — {N} donnes par match\n")

v3a = [MonteCarloBot(), HeuristicBot(), MonteCarloBot(), HeuristicBot()]
t0 = time.time()
s = run_match(v3a, N, seed=1)
t1 = time.time()
print(f"Match 1  V3(eq0) vs V1(eq1) : V3={s[0]}  V1={s[1]}  diff={s[0]-s[1]:+d}  ({t1-t0:.0f}s)")

v3b = [HeuristicBot(), MonteCarloBot(), HeuristicBot(), MonteCarloBot()]
t0 = time.time()
s = run_match(v3b, N, seed=1)
t1 = time.time()
print(f"Match 2  V1(eq0) vs V3(eq1) : V1={s[0]}  V3={s[1]}  diff={s[1]-s[0]:+d}  ({t1-t0:.0f}s)")

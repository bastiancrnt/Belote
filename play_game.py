#!/usr/bin/env python3
"""
play_game.py — Belote configurable
Chaque siège (J0–J3) peut être : Human, BotV1 ou BotV2.
Équipes : J0+J2 vs J1+J3.
"""
import sys, time, random
sys.path.insert(0, '.')

from belote.agents.human_agent      import HumanAgent
from belote.agents.heuristic_bot    import HeuristicBot
from belote.agents.heuristic_bot_v2 import HeuristicBotV2
from belote.database.db             import init_db, sync_to_mount
from belote.database                import repository as repo
from belote.database.validation     import validate_deal
from belote.game.hand               import Hand
from belote.game.bidding            import run_bidding
from belote.game.game               import apply_contract
from belote.core.deck               import Deck
from belote.rules.points            import trick_points, hand_points

SUIT_SYM  = {"C": "♦", "K": "♥", "P": "♠", "T": "♣"}
AGENT_TYPES = {
    "1": ("Human",  HumanAgent),
    "2": ("BotV1",  HeuristicBot),
    "3": ("BotV2",  HeuristicBotV2),
}

# ──────────────────────────────────────────────────────────────────────────────
# Config initiale
# ──────────────────────────────────────────────────────────────────────────────

def pick_agent(seat):
    print(f"\n  J{seat} (équipe {seat % 2}) :")
    for k, (name, _) in AGENT_TYPES.items():
        print(f"    {k}. {name}")
    while True:
        c = input("  → ").strip()
        if c in AGENT_TYPES:
            return AGENT_TYPES[c]
        print("  Choix invalide.")

def configure():
    print("\n" + "═"*50)
    print("  BELOTE — Configuration des joueurs")
    print("  Équipe 0 : J0 + J2   |   Équipe 1 : J1 + J3")
    print("═"*50)
    seats = []
    for s in range(4):
        name, cls = pick_agent(s)
        seats.append((name, cls))
    return seats

# ──────────────────────────────────────────────────────────────────────────────
# Enregistrement en DB
# ──────────────────────────────────────────────────────────────────────────────

def make_on_action(conn, game_id, deal_id, trump, agents, turn_ref):
    def on_action(player_id, card, full_hand, valid_cards, context, rule, dt_ms):
        trick_idx = (turn_ref[0] - 1) // 4 + 1
        pos       = (turn_ref[0] - 1) % 4 + 1
        actor_type = "human" if isinstance(agents[player_id], HumanAgent) else "bot"
        bv = getattr(agents[player_id], "BOT_VERSION",
             getattr(agents[player_id], "bot_version", repo.BOT_VERSION))
        repo.record_action(conn,
            game_id=game_id, deal_id=deal_id,
            turn_number=turn_ref[0], trick_number=trick_idx,
            position_in_trick=pos, player_id=player_id, trump=trump,
            hand_before=full_hand, legal_cards=valid_cards,
            current_trick=[], played_cards=list(context.get("played_cards", [])),
            chosen_card=card, actor_type=actor_type,
            rule_used=rule, decision_time_ms=dt_ms, bot_version=bv)
        turn_ref[0] += 1
    return on_action

# ──────────────────────────────────────────────────────────────────────────────
# Affichage
# ──────────────────────────────────────────────────────────────────────────────

def show_scores(total0, total1, names, target=1000):
    print(f"\n  ┌── Score ──────────────────────────┐")
    print(f"  │  Éq0 ({names[0]}+{names[2]}): {total0:>5} pts  │")
    print(f"  │  Éq1 ({names[1]}+{names[3]}): {total1:>5} pts  │")
    if total0 >= target:
        print(f"  │  → Équipe 0 GAGNE !               │")
    elif total1 >= target:
        print(f"  │  → Équipe 1 GAGNE !               │")
    else:
        print(f"  │  Objectif : {target} pts                │")
    print(f"  └───────────────────────────────────┘")

# ──────────────────────────────────────────────────────────────────────────────
# Boucle principale
# ──────────────────────────────────────────────────────────────────────────────

def main():
    seats = configure()
    names = [s[0] for s in seats]
    bot_versions = "/".join(
        getattr(s[1](), "BOT_VERSION", "human")
        if s[1] != HumanAgent else "human"
        for s in seats
    )

    conn     = init_db()
    game_id  = repo.create_game(conn, bot_version=bot_versions)
    total    = [0, 0]
    dealer   = 0
    deal_num = 0
    TARGET   = 1000

    print(f"\n  Partie enregistrée (game_id={game_id})")
    print(f"  Équipe 0 : {names[0]} + {names[2]}")
    print(f"  Équipe 1 : {names[1]} + {names[3]}")
    print(f"  Objectif : {TARGET} pts\n")

    while total[0] < TARGET and total[1] < TARGET:
        deal_num += 1
        first = (dealer + 1) % 4
        agents = [cls() for _, cls in seats]

        # Distribuer
        d = Deck(); d.shuffle()
        hands_orig = d.deal()
        hands_bid  = [list(h) for h in hands_orig]

        # Enchères
        print(f"\n{'─'*50}")
        print(f"  Donne {deal_num} — Donneur : J{dealer} ({names[dealer]})")
        bidding, contract_team = run_bidding(
            first_player=first, hands=hands_bid, agents=agents,
            verbose=any(isinstance(a, HumanAgent) for a in agents)
        )

        if bidding is None:
            print("  → Tout le monde passe. Nouvelle donne.")
            dealer = (dealer + 1) % 4
            continue

        trump = bidding.suit
        sym   = SUIT_SYM.get(trump, trump)
        print(f"  → Contrat : {bidding.points} à {sym}  (équipe {contract_team})")

        hands_play = [list(h) for h in hands_orig]
        initial_hands = [list(h) for h in hands_orig]
        for a in agents:
            a.reset_hand(trump)

        bv_deal = getattr(agents[0], "BOT_VERSION",
                  getattr(agents[0], "bot_version", repo.BOT_VERSION))
        deal_id = repo.create_deal(conn, game_id, deal_num, dealer, first,
                                   trump, first, contract_team,
                                   bidding.points, bv_deal)
        repo.save_initial_hands(conn, deal_id, initial_hands)

        turn_ref = [1]
        on_action = make_on_action(conn, game_id, deal_id, trump, agents, turn_ref)

        h = Hand(hands_play, trump, (trump, bidding.points),
                 agents=agents, verbose=True,
                 first_player=first, on_action=on_action,
                 taker_idx=first)
        pts0, pts1 = h.play_hand()

        # Sauvegarder les plis
        cur_leader = first
        for ti, tr in enumerate(h.tricks_history):
            winner = tr["winner"]
            pts = trick_points(list(tr["cards"].values()), trump)
            repo.save_trick(conn, deal_id, ti + 1, cur_leader,
                            tr.get("play_sequence", []), winner, pts)
            cur_leader = winner

        repo.finish_deal(conn, deal_id, pts0, pts1, h.current_player)

        # Appliquer contrat
        s0, s1 = apply_contract(pts0, pts1, bidding.points, contract_team)
        total[0] += s0
        total[1] += s1

        reussi = (contract_team == 0 and s0 > 0) or (contract_team == 1 and s1 > 0)
        print(f"\n  Brut : éq0={pts0}  éq1={pts1}")
        print(f"  Après contrat : éq0 +{s0}  éq1 +{s1}  ({'✓ réussi' if reussi else '✗ chuté'})")

        validate_deal(conn, deal_id)
        conn.commit()
        sync_to_mount()

        show_scores(total[0], total[1], names, TARGET)
        dealer = (dealer + 1) % 4

    repo.finish_game(conn, game_id, total[0], total[1],
                     0 if total[0] >= TARGET else 1)
    conn.commit()
    sync_to_mount()
    print("\n  Partie terminée. DB sauvegardée.")

if __name__ == "__main__":
    main()

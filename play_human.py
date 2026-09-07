"""
Belote Coinche — mode humain vs 3 bots.
Enregistre chaque donne dans belote.db (~/belote.db, syncé vers mnt/Belote/).
Usage : python play_human.py [--stats]
"""
import sys
from belote.agents.human_agent   import HumanAgent
from belote.agents.heuristic_bot import HeuristicBot
from belote.database.db          import init_db, sync_to_mount
from belote.database             import repository as repo
from belote.database.validation  import validate_deal
from belote.game.bidding         import run_bidding
from belote.game.hand            import Hand
from belote.core.deck            import Deck
from belote.game.game            import apply_contract
from belote.rules.points         import trick_points, hand_points

BOT_VERSION = "heuristic_v1"
TARGET      = 501
SUIT_SYM    = {"C": "♦", "K": "♥", "P": "♠", "T": "♣"}


class DealRecorder:
    """Callback appelé par Hand._pick() après chaque carte jouée."""

    def __init__(self, conn, game_id, deal_id, trump, agents):
        self.conn    = conn
        self.game_id = game_id
        self.deal_id = deal_id
        self.trump   = trump
        self.agents  = agents
        self.turn         = 0
        self.trick_n      = 0
        self.pos_in_trick = 0

    def on_new_trick(self, trick_num):
        self.trick_n      = trick_num
        self.pos_in_trick = 0

    def __call__(self, player_id, card, full_hand, valid_cards, context, rule, dt_ms):
        self.turn         += 1
        self.pos_in_trick += 1

        actor = "human" if isinstance(self.agents[player_id], HumanAgent) else "bot"

        trick_so_far = context.get("trick_so_far", [])
        played_cards = list(context.get("played_cards", set()))

        partner_id  = (player_id + 2) % 4
        master_idx  = context.get("master_player_idx")
        partner_win = (master_idx == partner_id) if master_idx is not None else False
        opp_win     = (master_idx is not None
                       and master_idx != player_id
                       and master_idx != partner_id)

        repo.record_action(
            conn              = self.conn,
            game_id           = self.game_id,
            deal_id           = self.deal_id,
            turn_number       = self.turn,
            trick_number      = self.trick_n,
            position_in_trick = self.pos_in_trick,
            player_id         = player_id,
            trump             = self.trump,
            hand_before       = full_hand,
            legal_cards       = list(valid_cards),
            current_trick     = trick_so_far,
            played_cards      = played_cards,
            chosen_card       = card,
            actor_type        = actor,
            rule_used         = rule if actor == "bot" else None,
            decision_time_ms  = dt_ms,
            partner_winning   = partner_win,
            opponent_winning  = opp_win,
        )

    def flush_trick(self, trick_number, leader, play_sequence, winner, trump):
        pts = trick_points([c for _, c in play_sequence], trump)
        repo.save_trick(
            conn          = self.conn,
            deal_id       = self.deal_id,
            trick_number  = trick_number,
            leader        = leader,
            play_sequence = play_sequence,
            winner        = winner,
            points        = pts,
        )
        return pts


def play_hand_recorded(conn, game_id, deal_number, hands, trump, contract,
                        agents, first_player, contract_team, verbose=True):
    deal_id = repo.create_deal(
        conn, game_id, deal_number, first_player, first_player,
        trump, taker=first_player, taker_team=contract_team,
        contract_value=contract
    )
    repo.save_initial_hands(conn, deal_id, hands)

    rec = DealRecorder(conn, game_id, deal_id, trump, agents)
    h   = Hand(hands, trump, contract, agents, verbose=verbose,
               first_player=first_player, on_action=rec)

    if agents:
        for ag in agents:
            if hasattr(ag, "reset_hand"):
                ag.reset_hand(trump)

    pts_running = [0, 0]
    for i in range(8):
        rec.on_new_trick(i + 1)
        h.play_trick(i + 1)
        last = h.tricks_history[-1]
        seq  = last["play_sequence"]
        win  = last["winner"]
        pts  = rec.flush_trick(i + 1, seq[0][0], seq, win, trump)
        pts_running[win % 2] += pts
        for offset in range(4):
            repo.update_action_trick_result(
                conn, deal_id, i * 4 + offset + 1,
                win, pts_running[0], pts_running[1]
            )

    last_w = h.tricks_history[-1]["winner"]
    dix0   = last_w % 2 == 0
    s0 = hand_points(h.tricks_won[0], trump, dix_de_der=dix0)
    s1 = hand_points(h.tricks_won[1], trump, dix_de_der=not dix0)

    if verbose:
        print(f"\n  Dix-de-der : eq{0 if dix0 else 1}")
        print(f"  Eq0 : {s0} pts  |  Eq1 : {s1} pts")

    repo.finish_deal(conn, deal_id, s0, s1, last_w)
    result = validate_deal(conn, deal_id)
    repo.mark_deal_valid(conn, deal_id, result["valid"])
    if not result["valid"]:
        print(f"  ⚠ Donne invalide : {result['errors']}")

    return s0, s1


def show_stats(conn):
    row = conn.execute(
        "SELECT COUNT(*), SUM(winner_team=0), SUM(winner_team=1), "
        "AVG(final_score_team_0), AVG(final_score_team_1) FROM games WHERE completed=1"
    ).fetchone()
    total, wins, losses, avg0, avg1 = row
    total = total or 0
    if total == 0:
        print("  Aucune partie enregistrée.")
        return
    print(f"\n  ── Statistiques ({total} parties) ──")
    print(f"  Victoires : {wins}   Défaites : {losses}   ({100*wins//total}% victoires)")
    print(f"  Score moyen  vous : {avg0:.0f}  |  bots : {avg1:.0f}")
    d = conn.execute(
        "SELECT COUNT(*), SUM(valid=1), SUM(valid=0) FROM deals WHERE completed=1"
    ).fetchone()
    print(f"  Donnes : {d[0]}  valides : {d[1]}  invalides : {d[2]}")


def main():
    conn = init_db()

    if "--stats" in sys.argv:
        show_stats(conn)
        return

    print("\n  ╔══════════════════════════════════╗")
    print("  ║  BELOTE COINCHE — Mode humain    ║")
    print("  ╚══════════════════════════════════╝")
    print("  Vous êtes J0 (équipe 0 avec J2-bot).")
    print("  J1 et J3 (équipe 1) sont des bots.\n")

    agents = [HumanAgent(), HeuristicBot(), HeuristicBot(), HeuristicBot()]
    game_id = repo.create_game(conn, bot_version=BOT_VERSION)
    scores  = [0, 0]
    n_hand  = 0
    first_player = 0

    while max(scores) < TARGET:
        n_hand += 1
        d = Deck(); d.shuffle()
        hands = d.deal()

        bidding, contract_team = run_bidding(
            first_player, hands=hands, agents=agents, verbose=True
        )
        if bidding is None:
            print(f"\nManche {n_hand}: tout le monde passe, redistribution")
            first_player = (first_player + 1) % 4
            n_hand -= 1
            continue

        sym = SUIT_SYM.get(bidding.suit, bidding.suit)
        print(f"\n{'='*52}")
        print(f"  MANCHE {n_hand}  |  J{first_player} ouvre  |  "
              f"Contrat : {bidding.points} à {sym}  (eq{contract_team})")
        print(f"{'='*52}")

        pts0, pts1 = play_hand_recorded(
            conn, game_id, n_hand, hands, bidding.suit, bidding.points,
            agents, first_player, contract_team, verbose=True
        )
        s0, s1 = apply_contract(pts0, pts1, bidding.points, contract_team)
        scores[0] += s0; scores[1] += s1

        reussi = (contract_team == 0 and s0 > 0) or (contract_team == 1 and s1 > 0)
        print(f"\n  Contrat {'✓ réussi' if reussi else '✗ chuté'}")
        print(f"  Score  eq0 : {scores[0]}  |  eq1 : {scores[1]}")
        first_player = (first_player + 1) % 4

    winner = 0 if scores[0] >= TARGET else 1
    print(f"\n{'='*52}")
    print(f"  Équipe {winner} gagne ! ({scores[0]}-{scores[1]} en {n_hand} manches)")
    print(f"{'='*52}")

    repo.finish_game(conn, game_id, scores[0], scores[1], winner)
    sync_to_mount()
    show_stats(conn)


if __name__ == "__main__":
    main()

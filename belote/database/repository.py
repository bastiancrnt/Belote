"""Toutes les écritures DB sont centralisées ici."""
import json, datetime
from .encoding import encode, encode_list, encode_trump

BOT_VERSION = "heuristic_v1"


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def _j(obj):
    return json.dumps(obj, ensure_ascii=False)


# ── games ─────────────────────────────────────────────────────────────────────

def create_game(conn, bot_version=BOT_VERSION, seed=None) -> int:
    cur = conn.execute(
        """INSERT INTO games
           (started_at, human_player, bot_left_version, bot_partner_version,
            bot_right_version, seed)
           VALUES (?,0,?,?,?,?)""",
        (_now(), bot_version, bot_version, bot_version, seed)
    )
    conn.commit()
    return cur.lastrowid


def finish_game(conn, game_id, score0, score1, winner):
    conn.execute(
        """UPDATE games SET finished_at=?, final_score_team_0=?,
           final_score_team_1=?, winner_team=?, completed=1
           WHERE id=?""",
        (_now(), score0, score1, winner, game_id)
    )
    conn.commit()


# ── deals ─────────────────────────────────────────────────────────────────────

def create_deal(conn, game_id, deal_number, dealer, first_player,
                trump, taker=None, taker_team=None, contract_value=None,
                bot_version=BOT_VERSION) -> int:
    cur = conn.execute(
        """INSERT INTO deals
           (game_id, deal_number, dealer, first_player, trump,
            taker, taker_team, contract_value, bot_version)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (game_id, deal_number, dealer, first_player,
         encode_trump(trump), taker, taker_team, contract_value, bot_version)
    )
    conn.commit()
    return cur.lastrowid


def finish_deal(conn, deal_id, score0, score1, last_trick_winner):
    winner = 0 if score0 > score1 else 1
    conn.execute(
        """UPDATE deals SET finished_at=?, score_team_0=?, score_team_1=?,
           winner_team=?, last_trick_winner=?, completed=1
           WHERE id=?""",
        (_now(), score0, score1, winner, last_trick_winner, deal_id)
    )
    conn.commit()


def mark_deal_valid(conn, deal_id, valid: bool):
    conn.execute("UPDATE deals SET valid=? WHERE id=?", (1 if valid else 0, deal_id))
    conn.commit()


# ── initial_hands ─────────────────────────────────────────────────────────────

def save_initial_hands(conn, deal_id, hands):
    for player_id, hand in enumerate(hands):
        conn.execute(
            "INSERT INTO initial_hands (deal_id, player_id, cards_json) VALUES (?,?,?)",
            (deal_id, player_id, _j(encode_list(hand)))
        )
    conn.commit()


# ── actions ───────────────────────────────────────────────────────────────────

def record_action(conn, *, game_id, deal_id, turn_number, trick_number,
                  position_in_trick, player_id, trump,
                  hand_before, legal_cards, current_trick,
                  played_cards, chosen_card,
                  actor_type, rule_used=None, decision_time_ms=None,
                  partner_winning=None, opponent_winning=None,
                  bot_version=BOT_VERSION, commit=True):
    team_id = player_id % 2
    conn.execute(
        """INSERT INTO actions
           (game_id, deal_id, turn_number, trick_number, position_in_trick,
            player_id, team_id, actor_type, trump,
            hand_before_json, legal_cards_json, current_trick_json,
            played_cards_json, chosen_card, rule_used, decision_time_ms,
            partner_winning_before_action, opponent_winning_before_action,
            bot_version)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (game_id, deal_id, turn_number, trick_number, position_in_trick,
         player_id, team_id, actor_type, encode_trump(trump),
         _j(encode_list(hand_before)),
         _j(encode_list(legal_cards)),
         _j([{"player": p, "card": encode(c)} for p, c in current_trick]),
         _j(encode_list(played_cards)),
         encode(chosen_card),
         rule_used,
         decision_time_ms,
         1 if partner_winning else 0,
         1 if opponent_winning else 0,
         bot_version if actor_type == "bot" else None)
    )
    if commit:
        conn.commit()


def update_action_trick_result(conn, deal_id, trick_number, trick_winner, pts0, pts1,
                                commit=True):
    """Met à jour les 4 actions d'un pli avec le gagnant et les points cumulés."""
    conn.execute(
        """UPDATE actions SET trick_winner=?, team_0_points_after_trick=?,
           team_1_points_after_trick=?
           WHERE deal_id=? AND trick_number=?""",
        (trick_winner, pts0, pts1, deal_id, trick_number)
    )
    if commit:
        conn.commit()


# ── tricks ────────────────────────────────────────────────────────────────────

def save_trick(conn, deal_id, trick_number, leader, play_sequence, winner, points,
               commit=True):
    rows = play_sequence
    conn.execute(
        """INSERT INTO tricks
           (deal_id, trick_number, leader,
            player_1, card_1, player_2, card_2,
            player_3, card_3, player_4, card_4,
            winner, winner_team, points)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (deal_id, trick_number, leader,
         rows[0][0], encode(rows[0][1]),
         rows[1][0], encode(rows[1][1]),
         rows[2][0], encode(rows[2][1]),
         rows[3][0], encode(rows[3][1]),
         winner, winner % 2, points)
    )
    if commit:
        conn.commit()

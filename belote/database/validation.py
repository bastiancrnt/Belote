"""Validation d'une donne complète après enregistrement."""
import json
from .db import get_connection


def validate_deal(conn, deal_id: int) -> dict:
    errors = []

    actions = conn.execute(
        "SELECT * FROM actions WHERE deal_id=? ORDER BY turn_number",
        (deal_id,)
    ).fetchall()

    tricks = conn.execute(
        "SELECT * FROM tricks WHERE deal_id=? ORDER BY trick_number",
        (deal_id,)
    ).fetchall()

    init_hands = conn.execute(
        "SELECT player_id, cards_json FROM initial_hands WHERE deal_id=?",
        (deal_id,)
    ).fetchall()

    # 32 actions
    if len(actions) != 32:
        errors.append(f"{len(actions)} actions au lieu de 32")

    # 8 plis
    if len(tricks) != 8:
        errors.append(f"{len(tricks)} plis au lieu de 8")

    # 32 cartes différentes jouées
    played = [a["chosen_card"] for a in actions]
    if len(set(played)) != 32:
        dupes = [c for c in set(played) if played.count(c) > 1]
        errors.append(f"Cartes jouées plusieurs fois : {dupes}")

    # Chaque chosen_card doit être dans legal_cards
    for a in actions:
        legal = json.loads(a["legal_cards_json"])
        if a["chosen_card"] not in legal:
            errors.append(
                f"Tour {a['turn_number']} : {a['chosen_card']} hors cartes légales {legal}"
            )

    # Vérifier que la main diminue de 1 à chaque action par joueur
    hand_sizes = {p: [] for p in range(4)}
    for a in actions:
        hand_before = json.loads(a["hand_before_json"])
        hand_sizes[a["player_id"]].append(len(hand_before))

    for pid, sizes in hand_sizes.items():
        for i in range(1, len(sizes)):
            if sizes[i] != sizes[i-1] - 1:
                errors.append(
                    f"J{pid} : main passe de {sizes[i-1]} à {sizes[i]} "
                    f"(attendu {sizes[i-1]-1})"
                )

    # Vérifier mains initiales (8 cartes chacun)
    for row in init_hands:
        cards = json.loads(row["cards_json"])
        if len(cards) != 8:
            errors.append(f"J{row['player_id']} : {len(cards)} cartes initiales au lieu de 8")

    valid = len(errors) == 0
    return {"valid": valid, "errors": errors}

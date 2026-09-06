"""
merge_db.py — Fusion de plusieurs belote.db (multi-ordi) en une DB maître.

Usage :
    python merge_db.py ordi1/belote.db ordi2/belote.db --output master.db

Les IDs AUTOINCREMENT de chaque source sont réattribués pour éviter les
collisions. Les clés étrangères sont mises à jour en conséquence.
"""

import sqlite3
import argparse
import shutil
import os
import sys

SCHEMA_PATH = os.path.join(os.path.dirname(__file__),
                           "belote", "database", "schema.sql")

MIGRATIONS = [
    "ALTER TABLE deals   ADD COLUMN bot_version TEXT",
    "ALTER TABLE actions ADD COLUMN bot_version TEXT",
]


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def open_ro(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def init_master(path: str) -> sqlite3.Connection:
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")   # on gère nous-mêmes
    conn.execute("PRAGMA journal_mode = WAL")
    with open(SCHEMA_PATH) as f:
        sql = f.read()
    for stmt in sql.split(";"):
        stmt = stmt.strip()
        if stmt and not stmt.upper().startswith("PRAGMA"):
            try:
                conn.execute(stmt)
            except sqlite3.OperationalError:
                pass
    for mig in MIGRATIONS:
        try:
            conn.execute(mig)
        except sqlite3.OperationalError:
            pass
    conn.commit()
    return conn


def next_id(conn: sqlite3.Connection, table: str) -> int:
    """Prochain ID disponible dans la table maître."""
    row = conn.execute(f"SELECT MAX(id) FROM {table}").fetchone()
    return (row[0] or 0) + 1


# ──────────────────────────────────────────────────────────────────────────────
# Fusion d'une source
# ──────────────────────────────────────────────────────────────────────────────

def merge_source(src: sqlite3.Connection, dst: sqlite3.Connection,
                 label: str) -> dict:
    """
    Copie tous les enregistrements de `src` dans `dst`.
    Retourne un dict résumé des counts.
    """
    counts = {}

    # ── games ─────────────────────────────────────────────────────────────────
    game_id_map = {}   # ancien id → nouveau id
    games = src.execute("SELECT * FROM games").fetchall()
    for g in games:
        new_id = next_id(dst, "games")
        cols   = [k for k in g.keys() if k != "id"]
        vals   = [g[k] for k in cols]
        ph     = ", ".join("?" * len(cols))
        dst.execute(
            f"INSERT INTO games (id, {', '.join(cols)}) VALUES (?, {ph})",
            [new_id] + vals
        )
        game_id_map[g["id"]] = new_id
    counts["games"] = len(games)

    # ── deals ─────────────────────────────────────────────────────────────────
    deal_id_map = {}
    deals = src.execute("SELECT * FROM deals").fetchall()
    for d in deals:
        new_id     = next_id(dst, "deals")
        new_gid    = game_id_map[d["game_id"]]
        cols       = [k for k in d.keys() if k not in ("id", "game_id")]
        vals       = [d[k] for k in cols]
        ph         = ", ".join("?" * len(cols))
        dst.execute(
            f"INSERT INTO deals (id, game_id, {', '.join(cols)}) VALUES (?, ?, {ph})",
            [new_id, new_gid] + vals
        )
        deal_id_map[d["id"]] = new_id
    counts["deals"] = len(deals)

    # ── initial_hands ──────────────────────────────────────────────────────────
    hands = src.execute("SELECT * FROM initial_hands").fetchall()
    for h in hands:
        new_did = deal_id_map[h["deal_id"]]
        # UNIQUE(deal_id, player_id) — peut légitimement exister si on remerge
        try:
            dst.execute(
                "INSERT INTO initial_hands (deal_id, player_id, cards_json) VALUES (?, ?, ?)",
                [new_did, h["player_id"], h["cards_json"]]
            )
        except sqlite3.IntegrityError:
            pass
    counts["initial_hands"] = len(hands)

    # ── tricks ────────────────────────────────────────────────────────────────
    tricks = src.execute("SELECT * FROM tricks").fetchall()
    for t in tricks:
        new_did = deal_id_map[t["deal_id"]]
        cols    = [k for k in t.keys() if k not in ("id", "deal_id")]
        vals    = [t[k] for k in cols]
        ph      = ", ".join("?" * len(cols))
        try:
            dst.execute(
                f"INSERT INTO tricks (id, deal_id, {', '.join(cols)}) "
                f"VALUES (?, ?, {ph})",
                [next_id(dst, "tricks"), new_did] + vals
            )
        except sqlite3.IntegrityError:
            pass   # UNIQUE(deal_id, trick_number) — déjà là
    counts["tricks"] = len(tricks)

    # ── actions ───────────────────────────────────────────────────────────────
    actions = src.execute("SELECT * FROM actions").fetchall()
    for a in actions:
        new_gid = game_id_map[a["game_id"]]
        new_did = deal_id_map[a["deal_id"]]
        cols    = [k for k in a.keys() if k not in ("id", "game_id", "deal_id")]
        vals    = [a[k] for k in cols]
        ph      = ", ".join("?" * len(cols))
        dst.execute(
            f"INSERT INTO actions (id, game_id, deal_id, {', '.join(cols)}) "
            f"VALUES (?, ?, ?, {ph})",
            [next_id(dst, "actions"), new_gid, new_did] + vals
        )
    counts["actions"] = len(actions)

    dst.commit()

    print(f"  [{label}]  games={counts['games']}  deals={counts['deals']}  "
          f"hands={counts['initial_hands']}  tricks={counts['tricks']}  "
          f"actions={counts['actions']}")
    return counts


# ──────────────────────────────────────────────────────────────────────────────
# Résumé des scores
# ──────────────────────────────────────────────────────────────────────────────

def print_summary(dst: sqlite3.Connection):
    rows = dst.execute("""
        SELECT bot_version,
               SUM(final_score_team_0) AS s0,
               SUM(final_score_team_1) AS s1,
               COUNT(*) AS n_games
        FROM games
        WHERE completed = 1
        GROUP BY bot_version
    """).fetchall()

    print("\n=== RÉSUMÉ MASTER ===")
    for r in rows:
        diff = (r["s0"] or 0) - (r["s1"] or 0)
        sign = "+" if diff >= 0 else ""
        print(f"  {r['bot_version'] or '?':30s}  "
              f"team0={r['s0']}  team1={r['s1']}  "
              f"diff={sign}{diff}  ({r['n_games']} games)")

    total_deals = dst.execute("SELECT COUNT(*) FROM deals WHERE completed=1").fetchone()[0]
    print(f"  Total donnes complètes : {total_deals}")


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fusionne plusieurs belote.db en un master.")
    parser.add_argument("sources", nargs="+", help="Chemins vers les DB sources (ex: ordi1/belote.db ordi2/belote.db)")
    parser.add_argument("--output", "-o", default="master.db", help="Chemin de la DB maître (défaut: master.db)")
    args = parser.parse_args()

    for path in args.sources:
        if not os.path.exists(path):
            print(f"Erreur : fichier introuvable : {path}", file=sys.stderr)
            sys.exit(1)

    if not os.path.exists(SCHEMA_PATH):
        print(f"Erreur : schema.sql introuvable à {SCHEMA_PATH}", file=sys.stderr)
        print("Lance le script depuis la racine du projet Belote.", file=sys.stderr)
        sys.exit(1)

    print(f"Création de {args.output} ...")
    dst = init_master(args.output)

    total = {"games": 0, "deals": 0}
    for path in args.sources:
        label = os.path.basename(os.path.dirname(path)) or os.path.basename(path)
        src   = open_ro(path)
        counts = merge_source(src, dst, label)
        src.close()
        total["games"] += counts["games"]
        total["deals"]  += counts["deals"]

    print(f"\n  Total fusionné : {total['games']} games, {total['deals']} deals")
    print_summary(dst)
    dst.close()
    print(f"\nDone → {os.path.abspath(args.output)}")


if __name__ == "__main__":
    main()

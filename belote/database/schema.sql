PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS games (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at          TEXT    NOT NULL,
    finished_at         TEXT,
    game_mode           TEXT    NOT NULL DEFAULT 'belote',
    human_player        INTEGER NOT NULL DEFAULT 0,
    bot_left_version    TEXT,
    bot_partner_version TEXT,
    bot_right_version   TEXT,
    final_score_team_0  INTEGER,
    final_score_team_1  INTEGER,
    winner_team         INTEGER,
    completed           INTEGER NOT NULL DEFAULT 0,
    seed                INTEGER,
    created_at          TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS deals (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id             INTEGER NOT NULL,
    deal_number         INTEGER NOT NULL,
    dealer              INTEGER NOT NULL,
    first_player        INTEGER NOT NULL,
    trump               TEXT    NOT NULL,
    taker               INTEGER,
    taker_team          INTEGER,
    contract_value      INTEGER,
    human_position      INTEGER NOT NULL DEFAULT 0,
    score_team_0        INTEGER,
    score_team_1        INTEGER,
    winner_team         INTEGER,
    last_trick_winner   INTEGER,
    valid               INTEGER,
    completed           INTEGER NOT NULL DEFAULT 0,
    started_at          TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at         TEXT,
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS initial_hands (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id     INTEGER NOT NULL,
    player_id   INTEGER NOT NULL   CHECK(player_id BETWEEN 0 AND 3),
    cards_json  TEXT    NOT NULL,
    FOREIGN KEY (deal_id) REFERENCES deals(id) ON DELETE CASCADE,
    UNIQUE(deal_id, player_id)
);

CREATE TABLE IF NOT EXISTS actions (
    id                              INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id                         INTEGER NOT NULL,
    deal_id                         INTEGER NOT NULL,
    turn_number                     INTEGER NOT NULL  CHECK(turn_number  BETWEEN 1 AND 32),
    trick_number                    INTEGER NOT NULL  CHECK(trick_number BETWEEN 1 AND 8),
    position_in_trick               INTEGER NOT NULL  CHECK(position_in_trick BETWEEN 1 AND 4),
    player_id                       INTEGER NOT NULL  CHECK(player_id BETWEEN 0 AND 3),
    team_id                         INTEGER NOT NULL  CHECK(team_id   BETWEEN 0 AND 1),
    actor_type                      TEXT    NOT NULL  CHECK(actor_type IN ('human','bot')),
    trump                           TEXT    NOT NULL,
    hand_before_json                TEXT    NOT NULL,
    legal_cards_json                TEXT    NOT NULL,
    current_trick_json              TEXT    NOT NULL,
    played_cards_json               TEXT    NOT NULL,
    chosen_card                     TEXT    NOT NULL,
    rule_used                       TEXT,
    decision_time_ms                INTEGER,
    partner_winning_before_action   INTEGER,
    opponent_winning_before_action  INTEGER,
    trick_winner                    INTEGER,
    team_0_points_after_trick       INTEGER,
    team_1_points_after_trick       INTEGER,
    created_at                      TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id)  REFERENCES games(id)  ON DELETE CASCADE,
    FOREIGN KEY (deal_id)  REFERENCES deals(id)  ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tricks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id      INTEGER NOT NULL,
    trick_number INTEGER NOT NULL  CHECK(trick_number BETWEEN 1 AND 8),
    leader       INTEGER NOT NULL,
    player_1     INTEGER NOT NULL,  card_1 TEXT NOT NULL,
    player_2     INTEGER NOT NULL,  card_2 TEXT NOT NULL,
    player_3     INTEGER NOT NULL,  card_3 TEXT NOT NULL,
    player_4     INTEGER NOT NULL,  card_4 TEXT NOT NULL,
    winner       INTEGER NOT NULL,
    winner_team  INTEGER NOT NULL,
    points       INTEGER NOT NULL,
    FOREIGN KEY (deal_id) REFERENCES deals(id) ON DELETE CASCADE,
    UNIQUE(deal_id, trick_number)
);

CREATE INDEX IF NOT EXISTS idx_actions_deal   ON actions(deal_id);
CREATE INDEX IF NOT EXISTS idx_actions_actor  ON actions(actor_type);
CREATE INDEX IF NOT EXISTS idx_actions_player ON actions(player_id);
CREATE INDEX IF NOT EXISTS idx_actions_rule   ON actions(rule_used);
CREATE INDEX IF NOT EXISTS idx_actions_turn   ON actions(deal_id, turn_number);
CREATE INDEX IF NOT EXISTS idx_tricks_deal    ON tricks(deal_id);

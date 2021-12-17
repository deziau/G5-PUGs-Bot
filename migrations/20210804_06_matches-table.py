
from yoyo import step


__depends__ = {'20210804_01_guilds-table'}

steps = [
    step(
        (
            'CREATE TABLE matches(\n'
            '    id SMALLSERIAL PRIMARY KEY,\n'
            '    guild BIGINT DEFAULT NULL REFERENCES guilds (id) ON DELETE CASCADE,\n'
            '    channel BIGINT DEFAULT NULL,\n'
            '    message BIGINT DEFAULT NULL,\n'
            '    category BIGINT DEFAULT NULL,\n'
            '    team1_channel BIGINT DEFAULT NULL,\n'
            '    team2_channel BIGINT DEFAULT NULL\n'
            ');'
        ),
        'DROP TABLE matches;'
    ),
    step(
        (
            'CREATE TABLE match_users(\n'
            '    match_id SMALLSERIAL REFERENCES matches (id) ON DELETE CASCADE,\n'
            '    user_id BIGSERIAL REFERENCES users (discord_id),\n'
            '    CONSTRAINT match_user_pkey PRIMARY KEY (match_id, user_id)\n'
            ');'
        ),
        'DROP TABLE match_users;'
    )
]

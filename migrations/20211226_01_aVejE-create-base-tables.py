"""
Create base tables
"""

from yoyo import step

__depends__ = {}

steps = [
    step(
        'CREATE TYPE team_method AS ENUM(\'captains\', \'autobalance\', \'random\');',
        'DROP TYPE team_method;'
    ),
    step(
        'CREATE TYPE captain_method AS ENUM(\'volunteer\', \'rank\', \'random\');',
        'DROP TYPE captain_method;'
    ),
    step(
        'CREATE TYPE series_type AS ENUM(\'bo1\', \'bo2\', \'bo3\');',
        'DROP TYPE series_type;'
    ),
    step(
        (
            'CREATE TABLE guilds(\n'
            '    id BIGSERIAL PRIMARY KEY,\n'
            '    api_key VARCHAR(128) DEFAULT NULL,\n'
            '    linked_role BIGINT DEFAULT NULL,\n'
            '    prematch_channel BIGINT DEFAULT NULL,\n'
            '    category BIGINT DEFAULT NULL,\n'
            '    lobbies_channel BIGINT DEFAULT NULL\n'
            ');'
        ),
        'DROP TABLE guilds;'
    ),
    step(
        (
            'CREATE TABLE lobbies(\n'
            '    id SMALLSERIAL PRIMARY KEY,\n'
            '    guild BIGINT DEFAULT NULL REFERENCES guilds (id) ON DELETE CASCADE,\n'
            '    name VARCHAR(64) DEFAULT NULL,\n'
            '    region VARCHAR(3) DEFAULT NULL,\n'
            '    capacity SMALLINT DEFAULT 10,\n'
            '    series_type series_type DEFAULT \'bo1\',\n'
            '    team_method team_method DEFAULT \'captains\',\n'
            '    captain_method captain_method DEFAULT \'volunteer\',\n'
            '    channel BIGINT DEFAULT NULL,\n'
            '    message BIGINT DEFAULT NULL,\n'
            '    category BIGINT DEFAULT NULL,\n'
            '    queue_channel BIGINT DEFAULT NULL,\n'
            '    lobby_channel BIGINT DEFAULT NULL,\n'
            '    last_message BIGINT DEFAULT NULL,\n'
            '    de_dust2 BOOL NOT NULL DEFAULT true,\n'
            '    de_mirage BOOL NOT NULL DEFAULT true,\n'
            '    de_cache BOOL NOT NULL DEFAULT true,\n'
            '    de_inferno BOOL NOT NULL DEFAULT true,\n'
            '    de_overpass BOOL NOT NULL DEFAULT true,\n'
            '    de_ancient BOOL NOT NULL DEFAULT true,\n'
            '    de_nuke BOOL NOT NULL DEFAULT true,\n'
            '    de_train BOOL NOT NULL DEFAULT false,\n'
            '    de_cbble BOOL NOT NULL DEFAULT false,\n'
            '    de_vertigo BOOL NOT NULL DEFAULT false,\n'
            '    de_shortdust BOOL NOT NULL DEFAULT false,\n'
            '    de_shortnuke BOOL NOT NULL DEFAULT false\n'
            ');'
        ),
        'DROP TABLE lobbies;'
    ),
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
            'CREATE TABLE users('
            '    discord_id BIGSERIAL UNIQUE,\n'
            '    steam_id VARCHAR(18) UNIQUE,\n'
            '    flag VARCHAR(3) DEFAULT NULL,\n'
            '    PRIMARY KEY (discord_id, steam_id)\n'
            ');'
        ),
        'DROP TABLE users;'
    ),
    step(
        (
            'CREATE TABLE queued_users(\n'
            '    lobby_id BIGSERIAL REFERENCES lobbies (id) ON DELETE CASCADE,\n'
            '    user_id BIGSERIAL REFERENCES users (discord_id) ON DELETE CASCADE,\n'
            '    CONSTRAINT queued_user_pkey PRIMARY KEY (lobby_id, user_id)\n'
            ');'
        ),
        'DROP TABLE queued_users;'
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
    ),
    step(
        (
            'CREATE TABLE banned_users(\n'
            '    guild_id BIGSERIAL REFERENCES guilds (id) ON DELETE CASCADE,\n'
            '    user_id BIGSERIAL REFERENCES users (discord_id),\n'
            '    unban_time TIMESTAMP WITH TIME ZONE DEFAULT null,\n'
            '    CONSTRAINT banned_user_pkey PRIMARY KEY (guild_id, user_id)\n'
            ');'
        ),
        'DROP TABLE banned_users;'
    )
]

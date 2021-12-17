
from yoyo import step


__depends__ = {'20210804_01_guilds-table'}

steps = [
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

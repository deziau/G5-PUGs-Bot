
from yoyo import step


__depends__ = {}

steps = [
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
    )
]

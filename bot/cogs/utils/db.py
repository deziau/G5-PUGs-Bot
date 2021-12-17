# db.py

import asyncio
import asyncpg
import logging


class DBHelper:
    """"""

    def __init__(self, connect_url):
        """"""
        loop = asyncio.get_event_loop()
        self.logger = logging.getLogger('G5.db')
        self.logger.info('Creating database connection pool')
        self.pool = loop.run_until_complete(asyncpg.create_pool(connect_url))

    async def close(self):
        """"""
        self.logger.info('Closing database connection pool')
        await self.pool.close()

    @staticmethod
    def _get_record_attrs(records, key):
        """"""
        if not records:
            return []
        return list(map(lambda r: r[key], records))

    async def query(self, statement, ret_key=None):
        """"""
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                rows = await connection.fetch(statement)

        if ret_key:
            return self._get_record_attrs(rows, ret_key) if rows else []

    async def fetch_row(self, statement):
        """"""
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                row = await connection.fetchrow(statement)

        return {col: val for col, val in row.items()} if row else {}

    async def sync_guilds(self, *guild_ids):
        """"""
        insert_rows = [tuple([guild_id] + [None] * 5) for guild_id in guild_ids]

        insert_statement = (
            'INSERT INTO guilds (id)\n'
            '    (SELECT id FROM unnest($1::guilds[]))\n'
            '    ON CONFLICT (id) DO NOTHING\n'
            '    RETURNING id;'
        )
        delete_statement = (
            'DELETE FROM guilds\n'
            '    WHERE id::BIGINT != ALL($1::BIGINT[])\n'
            '    RETURNING id;'
        )

        async with self.pool.acquire() as connection:
            async with connection.transaction():
                inserted = await connection.fetch(insert_statement, insert_rows)
                deleted = await connection.fetch(delete_statement, guild_ids)

        return self._get_record_attrs(inserted, 'id'), self._get_record_attrs(deleted, 'id')

    async def get_users(self, *user_ids):
        """"""
        statement = (
            'SELECT * FROM users\n'
            '    WHERE discord_id = ANY($1::BIGINT[]);'
        )

        async with self.pool.acquire() as connection:
            async with connection.transaction():
                users = await connection.fetch(statement, user_ids)

        return [{col: val for col, val in user.items()} for user in users] 

    async def get_banned_users(self, guild_id):
        """"""
        select_statement = (
            'SELECT * FROM banned_users\n'
            '    WHERE guild_id = $1;'
        )

        async with self.pool.acquire() as connection:
            async with connection.transaction():
                guild = await connection.fetch(select_statement, guild_id)

        return dict(zip(self._get_record_attrs(guild, 'user_id'), self._get_record_attrs(guild, 'unban_time')))

    async def insert_match_users(self, match_id, *user_ids):
        """"""
        statement = (
            'INSERT INTO match_users (match_id, user_id)\n'
            '    VALUES($1, $2);'
        )

        insert_rows = [(match_id, user_id) for user_id in user_ids]

        async with self.pool.acquire() as connection:
            async with connection.transaction():
                await connection.executemany(statement, insert_rows)

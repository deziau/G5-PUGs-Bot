# lobby.py

import discord
from discord.ext import commands, tasks
from discord.utils import get

from collections import defaultdict
from datetime import datetime, timezone
import asyncio

from .utils import utils
from ..resources import DB


async def _embed_lobby_msg(bot, lobby):
    """"""
    title = utils.trans('lobby-title', lobby.name, lobby.id)
    msg = f"{utils.trans('lobby-region', lobby.region)}\n" \
          f"{utils.trans('lobby-capacity', lobby.capacity)}\n" \
          f"{utils.trans('lobby-series-type', lobby.series)}\n" \
          f"{utils.trans('lobby-team-method', lobby.team_method)}\n" \
          f"{utils.trans('lobby-captain-method', lobby.captain_method)}\n" \
          f"{utils.trans('lobby-map-pool')} {''.join(m.emoji for m in lobby.mpool)}"

    embed = bot.embed_template(title=title, description=msg)
    return embed


class MapPoolMessage(discord.Message):
    """"""

    def __init__(self, message, bot, user, lobby):
        """"""
        for attr_name in message.__slots__:
            try:
                attr_val = getattr(message, attr_name)
            except AttributeError:
                continue

            setattr(self, attr_name, attr_val)

        self.bot = bot
        self.user = user
        self.lobby = lobby
        self.map_pool = None
        self.active_maps = None
        self.inactive_maps = None
        self.future = None

    def _pick_embed(self):
        embed = self.bot.embed_template(title=utils.trans('message-map-pool'))

        active_maps = ''.join(f'{emoji}  `{m.name}`\n' for emoji, m in self.active_maps.items())
        inactive_maps = ''.join(f'{emoji}  `{m.name}`\n' for emoji, m in self.inactive_maps.items())

        if not inactive_maps:
            inactive_maps = utils.trans("message-none")

        if not active_maps:
            active_maps = utils.trans("message-none")

        embed.add_field(name=utils.trans("message-active-maps"), value=active_maps)
        embed.add_field(name=utils.trans("message-inactive-maps"), value=inactive_maps)
        embed.set_footer(text=utils.trans('message-map-pool-footer'))
        return embed

    async def _process_pick(self, reaction, user):
        """"""
        if reaction.message.id != self.id or user == self.author or user != self.user:
            return

        await self.remove_reaction(reaction, user)
        emoji = str(reaction.emoji)

        if emoji == '✅':
            if len(self.active_maps) != 7:
                pass
            else:
                await self.edit(embed=self._pick_embed())
                if self.future is not None:
                    try:
                        self.future.set_result(None)
                    except asyncio.InvalidStateError:
                        pass
                return

        if emoji in self.inactive_maps:
            self.active_maps[emoji] = self.inactive_maps[emoji]
            self.inactive_maps.pop(emoji)
            self.map_pool.append(self.active_maps[emoji].dev_name)
        elif emoji in self.active_maps:
            self.inactive_maps[emoji] = self.active_maps[emoji]
            self.active_maps.pop(emoji)
            self.map_pool.remove(self.inactive_maps[emoji].dev_name)

        await self.edit(embed=self._pick_embed())

    async def edit_map_pool(self):
        """"""
        self.map_pool = [m.dev_name for m in self.lobby.mpool]
        self.active_maps = {m.emoji: m for m in self.bot.all_maps.values() if m.dev_name in self.map_pool}
        self.inactive_maps = {m.emoji: m for m in self.bot.all_maps.values() if m.dev_name not in self.map_pool}

        await self.edit(embed=self._pick_embed())

        awaitables = [self.add_reaction(m.emoji) for m in self.bot.all_maps.values()]
        await asyncio.gather(*awaitables, loop=self.bot.loop)
        await self.add_reaction('✅')

        self.future = self.bot.loop.create_future()
        self.bot.add_listener(self._process_pick, name='on_reaction_add')

        try:
            await asyncio.wait_for(self.future, 300)
        except asyncio.TimeoutError:
            self.bot.remove_listener(self._process_pick, name='on_reaction_add')
            return
        self.bot.remove_listener(self._process_pick, name='on_reaction_add')

        map_pool_data = {m.dev_name: m.dev_name in self.map_pool for m in self.bot.all_maps.values()}
        col_vals = ',\n    '.join(f'{key} = {value}' for key, value in map_pool_data.items())

        await DB.helper.query(
            "UPDATE lobbies\n"
            f"    SET {col_vals}\n"
            f"    WHERE id = {self.lobby.id};"
        )

        embed = self.bot.embed_template(title=utils.trans('lobby-map-pool-updated', self.lobby.name))
        await self.edit(embed=embed)
        await self.clear_reactions()


class ReadyMessage(discord.Message):
    def __init__(self, message, bot, users, guild):
        """"""
        for attr_name in message.__slots__:
            try:
                attr_val = getattr(message, attr_name)
            except AttributeError:
                continue

            setattr(self, attr_name, attr_val)

        self.bot = bot
        self.users = users
        self.guild = guild
        self.reactors = None
        self.future = None

    def _ready_embed(self):
        """"""
        str_value = ''
        description = utils.trans('message-react-ready', '✅')
        embed = self.bot.embed_template(title=utils.trans('message-lobby-filled-up'), description=description)

        for num, user in enumerate(self.users, start=1):
            if user not in self.reactors:
                str_value += f':heavy_multiplication_x:  {num}. {user.mention}\n '
            else:
                str_value += f'✅  {num}. {user.mention}\n '

        embed.add_field(name=f":hourglass: __{utils.trans('players')}__",
                        value='-------------------\n' + str_value)
        return embed

    async def _process_ready(self, reaction, user):
        """"""
        if reaction.message.id != self.id or user == self.author:
            return

        if user not in self.users or reaction.emoji != '✅':
            await self.remove_reaction(reaction, user)
            return

        self.reactors.add(user)
        await self.edit(embed=self._ready_embed())

        if self.reactors.issuperset(self.users):
            if self.future is not None:
                try:
                    self.future.set_result(None)
                except asyncio.InvalidStateError:
                    pass

    async def ready_up(self):
        """"""
        self.reactors = set()
        self.future = self.bot.loop.create_future()
        await self.edit(embed=self._ready_embed())
        await self.add_reaction('✅')

        self.bot.add_listener(self._process_ready, name='on_reaction_add')

        awaitables = []
        for user in self.users:
            awaitables.append(user.remove_roles(self.guild.linked_role))
        await asyncio.gather(*awaitables, loop=self.bot.loop, return_exceptions=True)

        try:
            await asyncio.wait_for(self.future, 60)
        except asyncio.TimeoutError:
            pass

        self.bot.remove_listener(self._process_ready, name='on_reaction_add')

        return self.reactors


class LobbyCog(commands.Cog):
    """"""
    def __init__(self, bot):
        self.bot = bot
        self.locked_lobby = {}
        self.locked_lobby = defaultdict(lambda: False, self.locked_lobby)

    async def setup_lobbies(self, guild):
        """"""
        guild_data = await DB.helper.fetch_row(
            "SELECT * FROM guilds\n"
            f"    WHERE id = {guild.id};"
        )
        db_guild = utils.Guild.from_dict(self.bot, guild_data)

        if not db_guild.is_setup:
            return

        category = db_guild.category
        lobbies_channel = db_guild.lobbies_channel

        if not lobbies_channel:
            lobbies_channel = await db_guild.guild.create_text_channel(name='lobbies', category=category)
            await lobbies_channel.set_permissions(db_guild.guild.self_role, send_messages=True)
            await lobbies_channel.set_permissions(db_guild.guild.default_role, send_messages=False)

            await DB.helper.query(
                "UPDATE guilds\n"
                f"    SET lobbies_channel = {lobbies_channel.id}\n"
                f"    WHERE id = {db_guild.guild.id};"
            )

        lobbies_msgs = await DB.helper.query(
            "SELECT message FROM lobbies\n"
            f"    WHERE guild = {db_guild.guild.id};",
            ret_key='message'
        )
        
        for msg_id in lobbies_msgs:
            try:
                lobby_msg = await lobbies_channel.fetch_message(msg_id)
            except (discord.NotFound, discord.HTTPException):
                lobby_data = await DB.helper.fetch_row(
                    "SELECT * from lobbies\n"
                    f"    WHERE message = {msg_id};"
                )
                lobby = utils.Lobby.from_dict(self.bot, lobby_data)
                embed = await _embed_lobby_msg(self.bot, lobby)
                lobby_msg = await lobbies_channel.send(embed=embed)
                await DB.helper.query(
                    "UPDATE lobbies\n"
                    f"    SET message = {lobby_msg.id}\n"
                    f"    WHERE id = {lobby.id};"
                )

    @commands.command(brief=utils.trans('create-lobby-command-brief'),
                      usage='create-lobby <name>',
                      aliases=['create-lobby', 'createlobby'])
    @commands.has_permissions(administrator=True)
    async def create_lobby(self, ctx, *args):
        """"""
        guild_data = await DB.helper.fetch_row(
            "SELECT * FROM guilds\n"
            f"    WHERE id = {ctx.guild.id};"
        )
        db_guild = utils.Guild.from_dict(self.bot, guild_data)
        
        if not db_guild.is_setup:
            raise commands.UserInputError(message=utils.trans('bot-not-setup', self.bot.command_prefix[0]))

        if len(args) < 1:
            msg = utils.trans('invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        if not db_guild.lobbies_channel:
            msg = utils.trans('lobbies-chanel-not-existed', self.bot.command_prefix[0])
            raise commands.UserInputError(message=msg)

        try:
            lobby_id = await DB.helper.query(
                "INSERT INTO lobbies (guild, name, channel)\n"
                f"    VALUES ({ctx.guild.id},\n"
                f"        '{args[0]}',\n"
                f"        {db_guild.lobbies_channel.id})\n"
                "    RETURNING id;",
                ret_key="id"
            )
        except Exception as e:
            self.bot.logger.error('Database Error on insert lobby:\n' + str(e))
            raise commands.UserInputError(message=utils.trans('failed-create-lobby'))

        lobby_data = await DB.helper.fetch_row(
            "SELECT * from lobbies\n"
            f"    WHERE id = {lobby_id[0]};"
        )
        lobby = utils.Lobby.from_dict(self.bot, lobby_data)

        embed = await _embed_lobby_msg(self.bot, lobby)
        lobby_message = await lobby.channel.send(embed=embed)

        category = await ctx.guild.create_category_channel(name=f'{lobby.name} lobby')
        queue_channel = await ctx.guild.create_text_channel(category=category, name=f'{lobby.name} setup')
        lobby_channel = await ctx.guild.create_voice_channel(category=category, name=f'{lobby.name} lobby', user_limit=lobby.capacity)

        try:
            await queue_channel.set_permissions(ctx.guild.self_role, send_messages=True)
            await lobby_channel.set_permissions(ctx.guild.self_role, connect=True)
        except discord.InvalidArgument:
            pass
        await queue_channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await lobby_channel.set_permissions(ctx.guild.default_role, connect=False)
        await lobby_channel.set_permissions(db_guild.linked_role, connect=True)

        await DB.helper.query(
            "UPDATE lobbies\n"
            f"    SET message = {lobby_message.id},\n"
            f"        channel = {db_guild.lobbies_channel.id},\n"
            f"        category = {category.id},\n"
            f"        queue_channel = {queue_channel.id},\n"
            f"        lobby_channel = {lobby_channel.id}\n"
            f"    WHERE id = {lobby.id};"
        )

        msg = utils.trans('success-create-lobby', lobby.name)
        embed = self.bot.embed_template(title=msg)
        await ctx.message.reply(embed=embed)

    @commands.command(brief=utils.trans('delete-lobby-command-brief'),
                      usage='delete-lobby <Lobby ID>',
                      aliases=['delete-lobby', 'deletelobby'])
    @commands.has_permissions(administrator=True)
    async def delete_lobby(self, ctx, *args):
        """ Delete the lobby. """
        try:
            lobby_id = int(args[0])
        except (IndexError, ValueError):
            msg = utils.trans('invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        lobby_data = await DB.helper.fetch_row(
            "SELECT * FROM lobbies\n"
            f"    WHERE id = {lobby_id} AND guild = {ctx.guild.id};"
        )
        if not lobby_data:
            raise commands.UserInputError(message=utils.trans('invalid-lobby-id'))

        lobby = utils.Lobby.from_dict(self.bot, lobby_data)
        await DB.helper.query(
            "DELETE FROM lobbies\n"
            f"    WHERE id = {lobby.id}"
        )

        for chnl in [lobby.lobby_channel, lobby.queue_channel, lobby.category]:
            try:
                await chnl.delete()
            except (AttributeError, discord.NotFound):
                pass

        try:
            lobby_msg = await lobby.message.fetch()
            await lobby_msg.delete()
        except (AttributeError, discord.NotFound):
            pass

        msg = utils.trans('success-delete-lobby', lobby.name)
        embed = self.bot.embed_template(title=msg)
        await ctx.message.reply(embed=embed)

    @commands.command(usage='cap <Lobby ID> <new capacity>',
                      brief=utils.trans('command-cap-brief'),
                      aliases=['capacity'])
    @commands.has_permissions(administrator=True)
    async def cap(self, ctx, *args):
        """ Set the queue capacity. """
        try:
            new_cap = int(args[1])
            lobby_id = int(args[0])
        except (IndexError, ValueError):
            msg = utils.trans('invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        lobby_data = await DB.helper.fetch_row(
            "SELECT * FROM lobbies\n"
            f"    WHERE id = {lobby_id} AND guild = {ctx.guild.id};"
        )
        if not lobby_data:
            raise commands.UserInputError(message=utils.trans('invalid-lobby-id'))

        lobby = utils.Lobby.from_dict(self.bot, lobby_data)
        if new_cap == lobby.capacity:
            msg = utils.trans('capacity-already', new_cap)
            raise commands.UserInputError(message=msg)

        if new_cap < 2 or new_cap > 10 or new_cap %2 != 0:
            msg = utils.trans('capacity-out-range')
            raise commands.UserInputError(message=msg)

        self.locked_lobby[lobby.id] = True
        await DB.helper.query(
            "DELETE FROM queued_users\n"
            f"    WHERE lobby_id = {lobby.id};"
        )
        await DB.helper.query(
            "UPDATE lobbies\n"
            f"    SET capacity = {new_cap}\n"
            f"    WHERE id = {lobby.id};"
        )
        await self.update_last_msg(lobby, utils.trans('queue-emptied'))

        guild_data = await DB.helper.fetch_row(
            "SELECT * FROM guilds\n"
            f"    WHERE id = {ctx.guild.id};"
        )
        db_guild = utils.Guild.from_dict(self.bot, guild_data)

        awaitables = []
        for user in lobby.lobby_channel.members:
            awaitables.append(user.move_to(db_guild.prematch_channel))
        awaitables.append(lobby.lobby_channel.edit(user_limit=new_cap))
        await asyncio.gather(*awaitables, loop=self.bot.loop, return_exceptions=True)

        self.locked_lobby[lobby.id] = False

        msg = utils.trans('set-capacity', new_cap)
        embed = self.bot.embed_template(title=msg)
        await ctx.message.reply(embed=embed)
        await self.update_lobby_msg(lobby)

    @commands.command(usage='teams <lobby ID> {captains|autobalance|random}',
                      brief=utils.trans('command-teams-brief'),
                      aliases=['team'])
    @commands.has_permissions(administrator=True)
    async def teams(self, ctx, *args):
        """ Set the method by which teams are created. """
        try:
            new_method = args[1].lower()
            lobby_id = int(args[0])
        except (IndexError, ValueError):
            msg = utils.trans('invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        lobby_data = await DB.helper.fetch_row(
            "SELECT * FROM lobbies\n"
            f"    WHERE id = {lobby_id} AND guild = {ctx.guild.id};"
        )
        if not lobby_data:
            raise commands.UserInputError(message=utils.trans('invalid-lobby-id'))

        lobby = utils.Lobby.from_dict(self.bot, lobby_data)
        curr_method = lobby.team_method
        valid_methods = ['captains', 'autobalance', 'random']

        if new_method not in valid_methods:
            msg = utils.trans('team-valid-methods', valid_methods[0], valid_methods[1], valid_methods[2])
            raise commands.UserInputError(message=msg)

        if curr_method == new_method:
            msg = utils.trans('team-method-already', new_method)
            raise commands.UserInputError(message=msg)

        await DB.helper.query(
            "UPDATE lobbies\n"
            f"    SET team_method = '{new_method}'\n"
            f"    WHERE id = {lobby.id};"
        )

        title = utils.trans('set-team-method', new_method)
        embed = self.bot.embed_template(title=title)
        await ctx.message.reply(embed=embed)
        await self.update_lobby_msg(lobby)

    @commands.command(usage='captains <Lobby ID> {volunteer|rank|random}',
                      brief=utils.trans('command-captains-brief'),
                      aliases=['captain', 'picker', 'pickers'])
    @commands.has_permissions(administrator=True)
    async def captains(self, ctx, *args):
        """ Set the method by which captains are selected. """
        try:
            new_method = args[1].lower()
            lobby_id = int(args[0])
        except (IndexError, ValueError):
            msg = utils.trans('invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        lobby_data = await DB.helper.fetch_row(
            "SELECT * FROM lobbies\n"
            f"    WHERE id = {lobby_id} AND guild = {ctx.guild.id};"
        )
        if not lobby_data:
            raise commands.UserInputError(message=utils.trans('invalid-lobby-id'))

        lobby = utils.Lobby.from_dict(self.bot, lobby_data)
        curr_method = lobby.captain_method
        valid_methods = ['volunteer', 'rank', 'random']

        if new_method not in valid_methods:
            msg = utils.trans('captains-valid-method', valid_methods[0], valid_methods[1], valid_methods[2])
            raise commands.UserInputError(message=msg)

        if curr_method == new_method:
            msg = utils.trans('captains-method-already', new_method)
            raise commands.UserInputError(message=msg)

        await DB.helper.query(
            "UPDATE lobbies\n"
            f"    SET captain_method = '{new_method}'\n"
            f"    WHERE id = {lobby.id};"
        )

        title = utils.trans('set-captains-method', new_method)
        embed = self.bot.embed_template(title=title)
        await ctx.message.reply(embed=embed)
        await self.update_lobby_msg(lobby)

    @commands.command(usage='series <lobby ID> {bo1|bo2|bo3}',
                      brief=utils.trans('command-series-brief'))
    @commands.has_permissions(administrator=True)
    async def series(self, ctx, *args):
        """ Set series type of the lobby. """
        try:
            new_series = args[1].lower()
            lobby_id = int(args[0])
        except (IndexError, ValueError):
            msg = utils.trans('invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        lobby_data = await DB.helper.fetch_row(
            "SELECT * FROM lobbies\n"
            f"    WHERE id = {lobby_id} AND guild = {ctx.guild.id};"
        )
        if not lobby_data:
            raise commands.UserInputError(message=utils.trans('invalid-lobby-id'))

        lobby = utils.Lobby.from_dict(self.bot, lobby_data)
        curr_series = lobby.series
        valid_values = ['bo1', 'bo2', 'bo3']

        if new_series not in valid_values:
            msg = utils.trans('series-valid-methods', valid_values[0], valid_values[1], valid_values[2])
            raise commands.UserInputError(message=msg)

        if curr_series == new_series:
            msg = utils.trans('series-value-already', new_series)
            raise commands.UserInputError(message=msg)

        await DB.helper.query(
            "UPDATE lobbies\n"
            f"    SET series_type = '{new_series}'\n"
            f"    WHERE id = {lobby.id};"
        )

        title = utils.trans('set-series-value', new_series)
        embed = self.bot.embed_template(title=title)
        await ctx.message.reply(embed=embed)
        await self.update_lobby_msg(lobby)

    @commands.command(usage='region <lobby ID> {none|region code}',
                      brief=utils.trans('command-region-brief'))
    @commands.has_permissions(administrator=True)
    async def region(self, ctx, *args):
        """ Set or remove the region of the lobby. """
        try:
            new_region = args[1].upper()
            lobby_id = int(args[0])
        except (IndexError, ValueError):
            msg = utils.trans('invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        lobby_data = await DB.helper.fetch_row(
            "SELECT * FROM lobbies\n"
            f"    WHERE id = {lobby_id} AND guild = {ctx.guild.id};"
        )
        if not lobby_data:
            raise commands.UserInputError(message=utils.trans('invalid-lobby-id'))

        lobby = utils.Lobby.from_dict(self.bot, lobby_data)
        curr_region = lobby.region
        valid_regions = list(utils.FLAG_CODES.values())

        if new_region == 'NONE':
            new_region = None

        if new_region not in [None] + valid_regions:
            msg = utils.trans('region-not-valid')
            raise commands.UserInputError(message=msg)

        if curr_region == new_region:
            msg = utils.trans('lobby-region-already', curr_region)
            raise commands.UserInputError(message=msg)

        region = f"'{new_region}'" if new_region else 'NULL'
        await DB.helper.query(
            "UPDATE lobbies\n"
            f"    SET region = {region}\n"
            f"    WHERE id = {lobby.id};"
        )

        title = utils.trans('set-lobby-region', new_region)
        embed = self.bot.embed_template(title=title)
        await ctx.message.reply(embed=embed)
        await self.update_lobby_msg(lobby)

    @commands.command(usage='mpool <Lobby ID> ',
                      brief=utils.trans('command-mpool-brief'),
                      aliases=['mappool', 'pool'])
    async def mpool(self, ctx, *args):
        """ Edit the lobby's map pool. """
        try:
            lobby_id = int(args[0])
        except (IndexError, ValueError):
            msg = utils.trans('invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        lobby_data = await DB.helper.fetch_row(
            "SELECT * FROM lobbies\n"
            f"    WHERE id = {lobby_id} AND guild = {ctx.guild.id};"
        )
        if not lobby_data:
            raise commands.UserInputError(message=utils.trans('invalid-lobby-id'))

        lobby = utils.Lobby.from_dict(self.bot, lobby_data)
        message = await ctx.send('Map Pool')
        menu = MapPoolMessage(message, self.bot, ctx.author, lobby)
        await menu.edit_map_pool()
        await self.update_lobby_msg(lobby)

    @commands.command(usage='ban <user mention> [<days>d] [<hours>h] [<minutes>m]',
                      brief=utils.trans('command-ban-brief'),
                      aliases=['banned'])
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx):
        """"""
        try:
            user = ctx.message.mentions[0]
        except IndexError:
            msg = utils.trans('command-ban-mention-to-ban')
            raise commands.UserInputError(message=msg)

        time_delta, unban_time = utils.unbantime(ctx.message.content)

        await DB.helper.query(
            "INSERT INTO banned_users (guild_id, user_id, unban_time)\n"
            f"    VALUES({ctx.guild.id}, {user.id}, '{unban_time}')\n"
            "    ON CONFLICT (guild_id, user_id) DO UPDATE\n"
            "    SET unban_time = EXCLUDED.unban_time;"
        )

        guild_data = await DB.helper.fetch_row(
            "SELECT * FROM guilds\n"
            f"    WHERE id = {ctx.guild.id};"
        )
        db_guild = utils.Guild.from_dict(self.bot, guild_data)

        await user.remove_roles(db_guild.linked_role)

        ban_time_str = '' if unban_time is None else f' for {utils.timedelta_str(time_delta)}'
        embed = self.bot.embed_template(title=f'Banned **{user.display_name}**{ban_time_str}')
        embed.set_footer(text=utils.trans('command-ban-footer'))
        await ctx.send(embed=embed)

        if not self.check_unbans.is_running():
            self.check_unbans.start()

    @commands.command(usage='unban <user mention> ...',
                      brief=utils.trans('command-unban-brief'),
                      aliases=['unbanned'])
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx):
        """"""
        if len(ctx.message.mentions) == 0:
            msg = utils.trans('command-unban-mention-to-unban')
            raise commands.UserInputError(message=msg)

        user_ids = [user.id for user in ctx.message.mentions]

        unbanned_ids = await DB.helper.query(
            "DELETE FROM banned_users\n"
            f"    WHERE guild_id = {ctx.guild.id} AND user_id::BIGINT = ANY(ARRAY{user_ids}::BIGINT[])\n"
            "    RETURNING user_id;",
            ret_key='user_id'
        )

        unbanned_users = [user for user in ctx.message.mentions if user.id in unbanned_ids]
        never_banned_users = [user for user in ctx.message.mentions if user.id not in unbanned_ids]
        unbanned_users_str = ', '.join(f'**{user.display_name}**' for user in unbanned_users)
        never_banned_users_str = ', '.join(f'**{user.display_name}**' for user in never_banned_users)
        title_1 = 'nobody' if unbanned_users_str == '' else unbanned_users_str
        were_or_was = 'were' if len(never_banned_users) > 1 else 'was'
        title_2 = '' if never_banned_users_str == '' else f' ({never_banned_users_str} {were_or_was} never banned)'
        embed = self.bot.embed_template(title=f'Unbanned {title_1}{title_2}')
        embed.set_footer(text=utils.trans('command-unban-footer'))
        await ctx.send(embed=embed)

        guild_data = await DB.helper.fetch_row(
            "SELECT * FROM guilds\n"
            f"    WHERE id = {ctx.guild.id};"
        )
        db_guild = utils.Guild.from_dict(self.bot, guild_data)

        for user in ctx.message.mentions:
            await user.add_roles(db_guild.linked_role)
    
    async def update_lobby_msg(self, lobby):
        if not lobby.channel:
            return

        lobby_data = await DB.helper.fetch_row(
            "SELECT * FROM lobbies\n"
            f"    WHERE id = {lobby.id};"
        )
        lobby = utils.Lobby.from_dict(self.bot, lobby_data)
        embed = await _embed_lobby_msg(self.bot, lobby)

        try:
            lobby_msg = await lobby.message.fetch()
            await lobby_msg.edit(embed=embed)
        except (discord.NotFound, discord.HTTPException):
            lobby_msg = await lobby.channel.send(embed=embed)
            await DB.helper.query(
                "UPDATE lobbies\n"
                f"    SET message = {lobby_msg.id}\n"
                f"    WHERE id = {lobby.id};"
            )

    async def update_last_msg(self, lobby, title):
        """"""
        queued_ids = await DB.helper.query(
            "SELECT user_id FROM queued_users\n"
            f"    WHERE lobby_id = {lobby.id};",
            ret_key='user_id'
        )

        if title:
            title += f' ({len(queued_ids)}/{lobby.capacity})'

        if len(queued_ids) == 0:
            queue_str = utils.trans('lobby-is-empty')
        else:
            queued_users = [lobby.guild.get_member(user_id) for user_id in queued_ids]
            queue_str = ''.join(
                f'{num}. {user.mention}\n' for num, user in enumerate(queued_users, start=1))


        embed = self.bot.embed_template(title=title, description=queue_str)
        embed.set_footer(text=utils.trans('lobby-footer'))
        
        try:
            msg = await lobby.last_message.fetch()
            await msg.edit(embed=embed)
        except (AttributeError, discord.NotFound, discord.HTTPException):
            try:
                msg = await lobby.queue_channel.send(embed=embed)
                await DB.helper.query(
                    "UPDATE lobbies\n"
                    f"    SET last_message = {msg.id}\n"
                    f"    WHERE id = {lobby.id};"
                )
            except (AttributeError, discord.NotFound, discord.HTTPException):
                pass

    async def check_ready(self, message, users, guild):
        """"""
        menu = ReadyMessage(message, self.bot, users, guild)
        ready_users = await menu.ready_up()
        return ready_users

    @commands.Cog.listener()
    async def on_voice_state_update(self, user, before, after):
        """"""
        if before.channel == after.channel:
            return

        if before.channel is not None:
            lobby_data = await DB.helper.fetch_row(
                "SELECT * from lobbies\n"
                f"    WHERE lobby_channel = {before.channel.id};"
            )

            if lobby_data:
                before_lobby = utils.Lobby.from_dict(self.bot, lobby_data)

                if not self.locked_lobby[before_lobby.id]:
                    removed = await DB.helper.query(
                        "DELETE FROM queued_users\n"
                        f"    WHERE lobby_id = {before_lobby.id} AND user_id = {user.id}\n"
                        "    RETURNING user_id;",
                        ret_key='user_id'
                    )

                    if user.id in removed:
                        title = utils.trans('lobby-user-removed', user.display_name)
                    else:
                        title = utils.trans('lobby-user-not-in-lobby', user.display_name)

                    await self.update_last_msg(before_lobby, title)

        if after.channel is not None:
            lobby_data = await DB.helper.fetch_row(
                "SELECT * from lobbies\n"
                f"    WHERE lobby_channel = {after.channel.id};"
            )

            if not lobby_data:
                return

            after_lobby = utils.Lobby.from_dict(self.bot, lobby_data)

            if not self.locked_lobby[after_lobby.id]:
                awaitables = [
                    DB.helper.fetch_row(
                        "SELECT * FROM users\n"
                        f"    WHERE discord_id = {user.id};"
                    ),
                    DB.helper.query(
                        "SELECT user_id FROM queued_users\n"
                        f"    WHERE lobby_id = {after_lobby.id};",
                        ret_key='user_id'
                    ),
                    DB.helper.get_banned_users(
                        after.channel.guild.id
                    ),
                    DB.helper.fetch_row(
                        "SELECT * FROM match_users\n"
                        f"    WHERE user_id = {user.id};",
                    )
                ]
                results = await asyncio.gather(*awaitables, loop=self.bot.loop)
                is_linked = results[0]
                queued_ids = results[1]
                banned_users = results[2]
                in_match = results[3]

                if not is_linked:
                    title = utils.trans('lobby-user-not-linked', user.display_name)
                elif in_match:
                    title = utils.trans('lobby-user-in-match', user.display_name)
                elif user.id in banned_users:
                    title = utils.trans('lobby-user-is-banned', user.display_name)
                    unban_time = banned_users[user.id]
                    if unban_time is not None:
                        title += f' for {utils.timedelta_str(unban_time - datetime.now(timezone.utc))}'
                elif user.id in queued_ids:
                    title = utils.trans('lobby-user-in-lobby', user.display_name)
                elif len(queued_ids) >= after_lobby.capacity:
                    title = utils.trans('lobby-is-full', user.display_name)
                else:
                    await DB.helper.query(
                        "INSERT INTO queued_users (lobby_id, user_id)\n"
                        f"    VALUES ({after_lobby.id},\n"
                        f"            {user.id});"
                    )
                    queued_ids += [user.id]
                    title = utils.trans('lobby-user-added', user.display_name)

                    if len(queued_ids) == after_lobby.capacity:
                        self.locked_lobby[after_lobby.id] = True

                        guild_data = await DB.helper.fetch_row(
                            "SELECT * FROM guilds\n"
                            f"    WHERE id = {after.channel.guild.id};"
                        )
                        db_guild = utils.Guild.from_dict(self.bot, guild_data)

                        linked_role = db_guild.linked_role
                        prematch_channel = db_guild.prematch_channel
                        queue_channel = after_lobby.queue_channel
                        queued_users = [user.guild.get_member(user_id) for user_id in queued_ids]

                        await after.channel.set_permissions(linked_role, connect=False)

                        try:
                            queue_msg = await after_lobby.last_message.fetch()
                            await queue_msg.delete()
                        except (AttributeError, discord.NotFound, discord.HTTPException):
                            pass

                        ready_msg = await queue_channel.send(''.join([user.mention for user in queued_users]))
                        ready_users = await self.check_ready(ready_msg, queued_users, db_guild)
                        await asyncio.sleep(1)
                        unreadied = set(queued_users) - ready_users

                        if unreadied:
                            description = ''.join(f':x: {user.mention}\n' for user in unreadied)
                            title = utils.trans('lobby-not-all-ready')
                            burst_embed = self.bot.embed_template(title=title, description=description)
                            burst_embed.set_footer(text=utils.trans('lobby-unready-footer'))

                            unreadied_ids = [user.id for user in unreadied]
                            awaitables = [
                                ready_msg.clear_reactions(),
                                ready_msg.edit(content='', embed=burst_embed),
                                DB.helper.query(
                                    "DELETE FROM queued_users\n"
                                    f"    WHERE lobby_id = {after_lobby.id} AND user_id::BIGINT = ANY(ARRAY{unreadied_ids}::BIGINT[]);"
                                )
                            ]

                            for user in queued_users:
                                awaitables.append(user.add_roles(linked_role))
                            for user in unreadied:
                                awaitables.append(user.move_to(prematch_channel))
                            await asyncio.gather(*awaitables, loop=self.bot.loop, return_exceptions=True)
                        else:
                            await ready_msg.clear_reactions()
                            match_cog = self.bot.get_cog('MatchCog')
                            new_match = await match_cog.start_match(
                                queued_users,
                                ready_msg,
                                after_lobby,
                                db_guild
                            )

                            if not new_match:
                                awaitables = []
                                for user in queued_users:
                                    awaitables.append(user.add_roles(linked_role))
                                for user in queued_users:
                                    awaitables.append(user.move_to(prematch_channel))
                                await asyncio.gather(*awaitables, loop=self.bot.loop, return_exceptions=True)

                            await DB.helper.query(
                                "DELETE FROM queued_users\n"
                                f"    WHERE lobby_id = {after_lobby.id};"
                            )

                        title = utils.trans('lobby-players-in-lobby')
                        await self.update_last_msg(after_lobby, title)

                        self.locked_lobby[after_lobby.id] = False
                        await after_lobby.lobby_channel.set_permissions(linked_role, connect=True)
                        return

                await self.update_last_msg(after_lobby, title)

    @tasks.loop(seconds=60.0)
    async def check_unbans(self):
        there_banned_users = False
        unbanned_users = {}
        for gld in self.bot.guilds:
            guild_data = await DB.helper.fetch_row(
                "SELECT * FROM guilds\n"
                f"    WHERE id = {gld.id};"
            )
            db_guild = utils.Guild.from_dict(self.bot, guild_data)

            guild_bans = await DB.helper.get_banned_users(gld.id)

            if guild_bans:
                there_banned_users = True
                guild_unbanned_users = await DB.helper.query(
                    "DELETE FROM banned_users\n"
                    f"    WHERE guild_id = {gld.id} AND CURRENT_TIMESTAMP > unban_time\n"
                    "    RETURNING user_id;",
                    ret_key='user_id'
                )

                unbanned_users[gld] = guild_unbanned_users

                for user_ids in unbanned_users[gld]:
                    users = [get(gld.members, id=user_id) for user_id in user_ids]
                    for user in users:
                        await user.add_roles(db_guild.linked_role)

        if not there_banned_users:
            self.check_unbans.cancel()

    @ban.error
    @unban.error
    @create_lobby.error
    @delete_lobby.error
    @cap.error
    @series.error
    @teams.error
    @captains.error
    @region.error
    @mpool.error
    async def config_error(self, ctx, error):
        """"""
        if isinstance(error, commands.MissingPermissions):
            await ctx.trigger_typing()
            missing_perm = error.missing_perms[0].replace('_', ' ')
            embed = self.bot.embed_template(title=utils.trans('command-required-perm', missing_perm), color=0xFF0000)
            await ctx.message.reply(embed=embed)

        if isinstance(error, commands.UserInputError):
            await ctx.trigger_typing()
            embed = self.bot.embed_template(description='**' + str(error) + '**', color=0xFF0000)
            await ctx.message.reply(embed=embed)
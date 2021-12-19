# match.py

from discord.ext import commands, tasks
import discord

from .utils import utils, api
from ..resources import DB, Config

from random import shuffle
from datetime import datetime
import asyncio

class TeamDraftMessage(discord.Message):
    """"""
    def __init__(self, message, bot, users, lobby):
        """"""
        for attr_name in message.__slots__:
            try:
                attr_val = getattr(message, attr_name)
            except AttributeError:
                continue

            setattr(self, attr_name, attr_val)

        self.bot = bot
        self.users = users
        self.lobby = lobby
        self.pick_emojis = dict(zip(utils.EMOJI_NUMBERS[1:], users))
        self.pick_order = '1' + '2211'*20
        self.pick_number = None
        self.users_left = None
        self.teams = None
        self.captains_emojis = None
        self.future = None
        self.title = None

    @property
    def _active_picker(self):
        """"""
        if self.pick_number is None:
            return None

        picking_team_number = int(self.pick_order[self.pick_number])
        picking_team = self.teams[picking_team_number - 1]

        if len(picking_team) == 0:
            return None

        return picking_team[0]

    def _picker_embed(self, title):
        """"""
        embed = self.bot.embed_template(title=title)

        for team in self.teams:
            team_name = f'__{utils.trans("match-team")}__' if len(
                team) == 0 else f'__{utils.trans("match-team", team[0].display_name)}__'

            if len(team) == 0:
                team_players = utils.trans("message-team-empty")
            else:
                team_players = '\n'.join(p.display_name for p in team)

            embed.add_field(name=team_name, value=team_players)

        users_left_str = ''

        for index, (emoji, user) in enumerate(self.pick_emojis.items()):
            if not any(user in team for team in self.teams):
                users_left_str += f'{emoji}  {user.mention}\n'
            else:
                users_left_str += f':heavy_multiplication_x:  ~~{user.mention}~~\n'

        embed.insert_field_at(1, name=utils.trans("message-players-left"), value=users_left_str)

        status_str = ''

        status_str += f'{utils.trans("message-capt1", self.teams[0][0].mention)}\n' if len(
            self.teams[0]) else f'{utils.trans("message-capt1")}\n '

        status_str += f'{utils.trans("message-capt2", self.teams[1][0].mention)}\n\n' if len(
            self.teams[1]) else f'{utils.trans("message-capt2")}\n\n '

        status_str += utils.trans("message-current-capt", self._active_picker.mention) \
            if self._active_picker is not None else utils.trans("message-current-capt")

        embed.add_field(name=utils.trans("message-info"), value=status_str)
        embed.set_footer(text=utils.trans('message-team-pick-footer'))
        return embed

    def _pick_player(self, picker, pickee):
        """"""
        if picker == pickee:
            return False
        elif not self.teams[0]:
            picking_team = self.teams[0]
            self.captains_emojis.append(list(self.pick_emojis.keys())[list(self.pick_emojis.values()).index(picker)])
            self.users_left.remove(picker)
            picking_team.append(picker)
        elif self.teams[1] == [] and picker == self.teams[0][0]:
            return False
        elif self.teams[1] == [] and picker in self.teams[0]:
            return False
        elif not self.teams[1]:
            picking_team = self.teams[1]
            self.captains_emojis.append(list(self.pick_emojis.keys())[list(self.pick_emojis.values()).index(picker)])
            self.users_left.remove(picker)
            picking_team.append(picker)
        elif picker == self.teams[0][0]:
            picking_team = self.teams[0]
        elif picker == self.teams[1][0]:
            picking_team = self.teams[1]
        else:
            return False

        if picker != self._active_picker:
            return False

        if len(picking_team) > len(self.users) // 2:
            return False

        self.users_left.remove(pickee)
        picking_team.append(pickee)
        self.pick_number += 1
        return True

    async def _process_pick(self, reaction, user):
        """"""
        if reaction.message.id != self.id or user == self.author:
            return

        pick = self.pick_emojis.get(str(reaction.emoji), None)

        if pick is None or pick not in self.users_left or user not in self.users:
            await self.remove_reaction(reaction, user)
            return

        if not self._pick_player(user, pick):
            await self.remove_reaction(reaction, user)
            return

        await self.clear_reaction(reaction.emoji)
        title = utils.trans('message-team-picked', user.display_name, pick.display_name)

        if len(self.users) - len(self.users_left) == 2:
            await self.clear_reaction(self.captains_emojis[0])
        elif len(self.users) - len(self.users_left) == 4:
            await self.clear_reaction(self.captains_emojis[1])

        if len(self.users_left) == 1:
            fat_kid_team = self.teams[0] if len(self.teams[0]) <= len(self.teams[1]) else self.teams[1]
            fat_kid_team.append(self.users_left.pop(0))
            await self.edit(embed=self._picker_embed(title))
            if self.future is not None:
                try:
                    self.future.set_result(None)
                except asyncio.InvalidStateError:
                    pass
            return

        if len(self.users_left) == 0:
            await self.edit(embed=self._picker_embed(title))
            if self.future is not None:
                try:
                    self.future.set_result(None)
                except asyncio.InvalidStateError:
                    pass
            return

        await self.edit(embed=self._picker_embed(title))

    async def _message_deleted(self, message):
        """"""
        if message.id != self.id:
            return
        self.bot.remove_listener(self._process_pick, name='on_reaction_add')
        self.bot.remove_listener(self._message_deleted, name='on_message_delete')
        try:
            self.future.set_exception(ValueError)
        except asyncio.InvalidStateError:
            pass
        self.future.cancel()

    async def draft(self):
        """"""
        self.users_left = self.users.copy()
        self.teams = [[], []]
        self.pick_number = 0
        self.captains_emojis = []
        captain_method = self.lobby.captain_method

        if captain_method == 'rank':
            try:
                leaderboard = await api.Leaderboard.get_leaderboard(self.users_left)
                users_dict = dict(zip(leaderboard, self.users_left))
                players = list(users_dict.keys())
                players.sort(key=lambda x: x.average_rating)

                for team in self.teams:
                    player = [players.pop()]
                    captain = list(map(users_dict.get, player))
                    self.users_left.remove(captain[0])
                    team.append(captain[0])
                    captain_emoji_index = list(self.pick_emojis.values()).index(captain[0])
                    self.captains_emojis.append(list(self.pick_emojis.keys())[captain_emoji_index])
            except Exception as e:
                print(e)
                captain_method = 'random'

        if captain_method == 'random':
            temp_users = self.users_left.copy()
            shuffle(temp_users)

            for team in self.teams:
                captain = temp_users.pop()
                self.users_left.remove(captain)
                team.append(captain)
                captain_emoji_index = list(self.pick_emojis.values()).index(captain)
                self.captains_emojis.append(list(self.pick_emojis.keys())[captain_emoji_index])

        await self.edit(embed=self._picker_embed(utils.trans('message-team-draft-begun')))

        if self.users_left:
            for emoji, user in self.pick_emojis.items():
                if user in self.users_left:
                    await self.add_reaction(emoji)

            self.future = self.bot.loop.create_future()
            self.bot.add_listener(self._process_pick, name='on_reaction_add')
            self.bot.add_listener(self._message_deleted, name='on_message_delete')
            try:
                await asyncio.wait_for(self.future, 180)
            except asyncio.TimeoutError:
                self.bot.remove_listener(self._process_pick, name='on_reaction_add')
                self.bot.remove_listener(self._message_deleted, name='on_message_delete')
                await self.clear_reactions()
                raise

        await self.clear_reactions()
        return self.teams


class MapVetoMessage(discord.Message):
    """"""
    def __init__(self, message, bot, lobby):
        """"""
        for attr_name in message.__slots__:
            try:
                attr_val = getattr(message, attr_name)
            except AttributeError:
                continue

            setattr(self, attr_name, attr_val)

        self.bot = bot
        self.ban_order = '12' * 20
        self.lobby = lobby
        self.map_pool = lobby.mpool
        self.captains = None
        self.maps_left = None
        self.ban_number = None
        self.future = None

    @property
    def _active_picker(self):
        """"""
        if self.ban_number is None or self.captains is None:
            return None

        picking_player_number = int(self.ban_order[self.ban_number])
        return self.captains[picking_player_number - 1]

    def _veto_embed(self, title):
        """"""
        embed = self.bot.embed_template(title=title)
        maps_str = ''

        if self.map_pool is not None and self.maps_left is not None:
            for m in self.map_pool:
                maps_str += f'{m.emoji}  {m.name}\n' if m.emoji in self.maps_left else f':heavy_multiplication_x:  ' \
                            f'~~{m.name}~~\n '

        status_str = ''

        if self.captains is not None and self._active_picker is not None:
            status_str += utils.trans("message-capt1", self.captains[0].mention) + '\n'
            status_str += utils.trans("message-capt2", self.captains[1].mention) + '\n\n'
            status_str += utils.trans("message-current-capt", self._active_picker.mention)

        embed.add_field(name=utils.trans("message-maps-left"), value=maps_str)
        embed.add_field(name=utils.trans("message-info"), value=status_str)
        embed.set_footer(text=utils.trans('message-map-veto-footer'))
        return embed

    async def _process_ban(self, reaction, user):
        """"""
        if reaction.message.id != self.id or user == self.author:
            return

        if user not in self.captains or str(reaction) not in [m for m in self.maps_left] or user != self._active_picker:
            await self.remove_reaction(reaction, user)
            return

        try:
            map_ban = self.maps_left.pop(str(reaction))
        except KeyError:
            return

        self.ban_number += 1
        await self.clear_reaction(map_ban.emoji)
        embed = self._veto_embed(utils.trans('message-user-banned-map', user.display_name, map_ban.name))
        await self.edit(embed=embed)

        if (self.lobby.series == 'bo1' and len(self.maps_left) == 1) or \
           (self.lobby.series == 'bo2' and len(self.maps_left) == 2) or \
           (self.lobby.series == 'bo3' and len(self.maps_left) == 3):
            if self.future is not None:
                try:
                    self.future.set_result(None)
                except asyncio.InvalidStateError:
                    pass


    async def _message_deleted(self, message):
        """"""
        if message.id != self.id:
            return
        self.bot.remove_listener(self._process_ban, name='on_reaction_add')
        self.bot.remove_listener(self._message_deleted, name='on_message_delete')
        try:
            self.future.set_exception(ValueError)
        except asyncio.InvalidStateError:
            pass
        self.future.cancel()

    async def veto(self, captain_1, captain_2):
        """"""
        self.captains = [captain_1, captain_2]
        self.maps_left = {m.emoji: m for m in self.map_pool}
        self.ban_number = 0

        if len(self.map_pool) % 2 == 0:
            self.captains.reverse()

        await self.edit(embed=self._veto_embed(utils.trans('message-map-bans-begun')))

        for m in self.map_pool:
            await self.add_reaction(m.emoji)

        self.future = self.bot.loop.create_future()
        self.bot.add_listener(self._process_ban, name='on_reaction_add')
        self.bot.add_listener(self._message_deleted, name='on_message_delete')
        try:
            await asyncio.wait_for(self.future, 180)
        except asyncio.TimeoutError:
            self.bot.remove_listener(self._process_ban, name='on_reaction_add')
            self.bot.remove_listener(self._message_deleted, name='on_message_delete')
            await self.clear_reactions()
            raise

        await self.clear_reactions()
        return list(self.maps_left.values())


class MatchCog(commands.Cog):
    """"""
    def __init__(self, bot):
        """"""
        self.bot = bot

    @commands.command(usage='end <match_id>',
                      brief=utils.trans('command-end-brief'),
                      aliases=['cancel', 'stop'])
    @commands.has_permissions(kick_members=True)
    async def end(self, ctx, match_id=None):
        """"""
        try:
            match_id = int(match_id)
        except (TypeError, ValueError):
            msg = utils.trans('invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        guild_data = await DB.helper.fetch_row(
            "SELECT * FROM guilds\n"
            f"    WHERE id = {ctx.guild.id};"
        )
        db_guild = utils.Guild.from_dict(self.bot, guild_data)

        if not db_guild.is_setup:
            raise commands.UserInputError(message=utils.trans('bot-not-setup', self.bot.command_prefix[0]))

        try:
            await api.Matches.cancel_match(match_id, db_guild.auth)
        except Exception as e:
            raise commands.UserInputError(message=str(e))

        title = utils.trans('command-end-success', match_id)
        embed = self.bot.embed_template(title=title)
        await ctx.message.reply(embed=embed)

    @commands.command(usage='add <match_id> <team1|team2|spec> <mention>',
                      brief=utils.trans('command-add-brief'))
    @commands.has_permissions(kick_members=True)
    async def add(self, ctx, match_id=None, team=None):
        """"""
        if team not in ['team1', 'team2', 'spec']:
            msg = utils.trans('invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        try:
            match_id = int(match_id)
            user = ctx.message.mentions[0]
        except (TypeError, ValueError, IndexError):
            msg = utils.trans('invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        guild_data = await DB.helper.fetch_row(
            "SELECT * FROM guilds\n"
            f"    WHERE id = {ctx.guild.id};"
        )
        db_guild = utils.Guild.from_dict(self.bot, guild_data)

        if not db_guild.is_setup:
            raise commands.UserInputError(message=utils.trans('bot-not-setup', self.bot.command_prefix[0]))

        user_data = await DB.helper.fetch_row(
            "SELECT * FROM users\n"
            f"    WHERE discord_id = {user.id};"
        )

        if not user_data:
            msg = utils.trans('command-add-not-linked', user.mention)
            raise commands.UserInputError(message=msg)

        db_user = utils.User.from_dict(user_data, ctx.guild)
        try:
            await api.Matches.add_match_player(db_user, match_id, team, db_guild.auth)
        except Exception as e:
            raise commands.UserInputError(message=str(e))

        await DB.helper.query(
            "INSERT INTO match_users (match_id, user_id)\n"
            f"    VALUES({match_id}, {user.id});"
        )

        match_data = await DB.helper.fetch_row(
            "SELECT * FROM matches\n"
            f"    WHERE id = {match_id};"
        )
        db_match = await utils.Match.from_dict(self.bot, match_data)

        await user.remove_roles(db_guild.linked_role)

        if team == 'team1':
            await db_match.team1_channel.set_permissions(user, connect=True)
            try:
                await user.move_to(db_match.team1_channel)
            except:
                pass
        elif team == 'team2':
            await db_match.team2_channel.set_permissions(user, connect=True)
            try:
                await user.move_to(db_match.team2_channel)
            except:
                pass

        msg = utils.trans('command-add-success', user.mention, match_id)
        embed = self.bot.embed_template(description=msg)
        await ctx.message.reply(embed=embed)

    @commands.command(usage='remove <match_id> <mention>',
                      brief=utils.trans('command-remove-brief'))
    @commands.has_permissions(kick_members=True)
    async def remove(self, ctx, match_id=None):
        """"""
        try:
            match_id = int(match_id)
            user = ctx.message.mentions[0]
        except (TypeError, ValueError, IndexError):
            msg = utils.trans('invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)     

        guild_data = await DB.helper.fetch_row(
            "SELECT * FROM guilds\n"
            f"    WHERE id = {ctx.guild.id};"
        )
        db_guild = utils.Guild.from_dict(self.bot, guild_data)

        if not db_guild.is_setup:
            raise commands.UserInputError(message=utils.trans('bot-not-setup', self.bot.command_prefix[0]))      

        user_data = await DB.helper.fetch_row(
            "SELECT * FROM users\n"
            f"    WHERE discord_id = {user.id};"
        )

        if not user_data:
            msg = utils.trans('command-add-not-linked', user.mention)
            raise commands.UserInputError(message=msg)

        db_user = utils.User.from_dict(user_data, ctx.guild)
        try:
            await api.Matches.remove_match_player(db_user, match_id, db_guild.auth)
        except Exception as e:
            raise commands.UserInputError(message=str(e))

        await DB.helper.query(
            "DELETE FROM match_users\n"
            f"    WHERE match_id = {match_id} AND user_id = {user.id};"
        )

        match_data = await DB.helper.fetch_row(
            "SELECT * FROM matches\n"
            f"    WHERE id = {match_id};"
        )
        db_match = await utils.Match.from_dict(self.bot, match_data)

        await user.add_roles(db_guild.linked_role)
        await db_match.team1_channel.set_permissions(user, connect=False)
        await db_match.team2_channel.set_permissions(user, connect=False)
        try:
            await user.move_to(db_guild.prematch_channel)
        except:
            pass

        msg = utils.trans('command-remove-success', user.mention, match_id)
        embed = self.bot.embed_template(description=msg)
        await ctx.message.reply(embed=embed)

    @commands.command(usage='pause <match_id>',
                      brief=utils.trans('command-pause-brief'))
    @commands.has_permissions(kick_members=True)
    async def pause(self, ctx, match_id=None):
        """"""
        if not match_id:
            msg = utils.trans('invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        guild_data = await DB.helper.fetch_row(
            "SELECT * FROM guilds\n"
            f"    WHERE id = {ctx.guild.id};"
        )
        db_guild = utils.Guild.from_dict(self.bot, guild_data)

        if not db_guild.is_setup:
            raise commands.UserInputError(message=utils.trans('bot-not-setup', self.bot.command_prefix[0]))

        try:
            await api.Matches.pause_match(match_id, db_guild.auth)
        except Exception as e:
            raise commands.UserInputError(message=str(e))

        msg = utils.trans('command-pause-success', match_id)
        embed = self.bot.embed_template(description=msg)
        await ctx.message.reply(embed=embed)

    @commands.command(usage='unpause <match_id>',
                      brief=utils.trans('command-unpause-brief'))
    @commands.has_permissions(kick_members=True)
    async def unpause(self, ctx, match_id=None):
        """"""
        if not match_id:
            msg = utils.trans('invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        guild_data = await DB.helper.fetch_row(
            "SELECT * FROM guilds\n"
            f"    WHERE id = {ctx.guild.id};"
        )
        db_guild = utils.Guild.from_dict(self.bot, guild_data)

        if not db_guild.is_setup:
            raise commands.UserInputError(message=utils.trans('bot-not-setup', self.bot.command_prefix[0]))

        try:
            await api.Matches.unpause_match(match_id, db_guild.auth)
        except Exception as e:
            raise commands.UserInputError(message=str(e))        

        msg = utils.trans('command-unpause-success', match_id)
        embed = self.bot.embed_template(description=msg)
        await ctx.message.reply(embed=embed)

    async def autobalance_teams(self, users):
        """ Balance teams based on players' avarage raitng. """
        # Get players and sort by average rating
        try:
            leaderboard = await api.Leaderboard.get_leaderboard(users, new_players=True)
        except Exception as e:
            print(str(e))
            return self.randomize_teams(users)

        stats_dict = dict(zip(leaderboard, users))
        players = list(stats_dict.keys())
        players.sort(key=lambda x: x.average_rating)

        # Balance teams
        team_size = len(players) // 2
        team_one = [players.pop()]
        team_two = [players.pop()]

        while players:
            if len(team_one) >= team_size:
                team_two.append(players.pop())
            elif len(team_two) >= team_size:
                team_one.append(players.pop())
            elif sum(float(p.average_rating) for p in team_one) < sum(float(p.average_rating) for p in team_two):
                team_one.append(players.pop())
            else:
                team_two.append(players.pop())

        return list(map(stats_dict.get, team_one)), list(map(stats_dict.get, team_two))

    async def draft_teams(self, message, users, lobby):
        """"""
        menu = TeamDraftMessage(message, self.bot, users, lobby)
        teams = await menu.draft()
        return teams[0], teams[1]

    @staticmethod
    def randomize_teams(users):
        """"""
        temp_users = users.copy()
        shuffle(temp_users)
        team_size = len(temp_users) // 2
        return temp_users[:team_size], temp_users[team_size:]

    async def ban_maps(self, message, lobby, captain_1, captain_2):
        """"""
        menu = MapVetoMessage(message, self.bot, lobby)
        return await menu.veto(captain_1, captain_2)

    def _embed_match(self, match, server, mapstats, scoreboard):
        """"""
        description = ''
        is_live = match.end_time == None

        if match.cancelled:
            title = '🟥  '
        elif not is_live:
            title = '🔴  '
        else:
            title = '🟢  '
        title += utils.trans('match-id', match.id) + f' --> **{match.team1_name}**  [{match.team1_score}:{match.team2_score}]  **{match.team2_name}**'
        
        if is_live and server:
            connect_url = f'steam://connect/{server.ip_string}:{server.port}'
            connect_command = f'connect {server.ip_string}:{server.port}'
            description += f'{utils.trans("match-server-info", connect_url, connect_command)}\n\n' \
                           f'GOTV: steam://connect/{server.ip_string}:{server.gotv_port}\n\n'

        for mapstat in mapstats:
            start_time = datetime.fromisoformat(mapstat.start_time.replace("Z", "+00:00")).strftime("%Y-%m-%d  %H:%M:%S")
            team1_match = []
            team2_match = []

            for player_stat in scoreboard:
                if player_stat.map_id != mapstat.id:
                    continue
                if player_stat.team_id == match.team1_id:
                    team1_match.append(player_stat)
                elif player_stat.team_id == match.team2_id:
                    team2_match.append(player_stat)

            description += f"**{utils.trans('map')} {mapstat.map_number+1}:** {mapstat.map_name}\n" \
                           f"**{utils.trans('score')}:** {match.team1_name}  [{mapstat.team1_score}:{mapstat.team2_score}]  {match.team2_name}\n" \
                           f"**{utils.trans('start-time')}:** {start_time}\n"

            if mapstat.end_time:
                end_time = datetime.fromisoformat(mapstat.end_time.replace("Z", "+00:00")).strftime("%Y-%m-%d  %H:%M:%S")
                description += f"**{utils.trans('end-time')}:** {end_time}\n"

            if team1_match and team2_match:
                for team in [team1_match, team2_match]:
                    team.sort(key=lambda x: x.score, reverse=True)
                    data = [['Player'] + [player.name for player in team],
                            ['Kills'] + [f"{player.kills}" for player in team],
                            ['Assists'] + [f"{player.assists}" for player in team],
                            ['Deaths'] + [f"{player.deaths}" for player in team],
                            ['KDR'] + [f"{0 if player.deaths == 0 else player.kills/player.deaths:.2f}" for player in team]]

                    data[0] = [name if len(name) < 12 else name[:9] + '...' for name in data[0]]  # Shorten long names
                    widths = list(map(lambda x: len(max(x, key=len)), data))
                    aligns = ['left', 'center', 'center', 'center', 'right']
                    z = zip(data, widths, aligns)
                    formatted_data = [list(map(lambda x: utils.align_text(x, width, align), col)) for col, width, align in z]
                    formatted_data = list(map(list, zip(*formatted_data)))  # Transpose list for .format() string
                    description += '```ml\n    {}  {}  {}  {}  {}  \n'.format(*formatted_data[0])

                    for rank, player_row in enumerate(formatted_data[1:], start=1):
                        description += ' {}. {}  {}  {}  {}  {}  \n'.format(rank, *player_row)

                    description += '```\n'
            description += '\n'
        description += f"[{utils.trans('more-info')}]({Config.web_panel}/match/{match.id})"

        embed = self.bot.embed_template(title=title, description=description)
        return embed

    async def start_match(self, users, message, lobby, db_guild):
        """"""
        title = utils.trans('match-setup-process')
        description = ''
        try:
            if lobby.team_method == 'captains' and len(users) > 3:
                team_one, team_two = await self.draft_teams(message, users, lobby)
            elif lobby.team_method == 'autobalance' and len(users) > 3:
                team_one, team_two = await self.autobalance_teams(users)
            else:  # team_method is random
                team_one, team_two = self.randomize_teams(users)
            
            team1_name = team_one[0].display_name
            team2_name = team_two[0].display_name

            description = '⌛️ 1. ' + utils.trans('creating-teams')
            embed = self.bot.embed_template(title=title, description=description)
            await message.edit(content='', embed=embed)
            team1_id = await api.Teams.create_team(team1_name, team_one, db_guild.auth)
            team2_id = await api.Teams.create_team(team2_name, team_two, db_guild.auth)
            await asyncio.sleep(2)

            description = '✅ 1. ' + utils.trans('creating-teams') + '\n' \
                          '⌛️ 2. ' + utils.trans('pick-maps')
            embed = self.bot.embed_template(title=title, description=description)
            await message.edit(content='', embed=embed)
            await asyncio.sleep(2)

            veto_menu = MapVetoMessage(message, self.bot, lobby)
            maps_list = await veto_menu.veto(team_one[0], team_two[0])

            description = '✅ 1. ' + utils.trans('creating-teams') + '\n' \
                          '✅ 2. ' + utils.trans('pick-maps') + '\n' \
                          '⌛️ 3. ' + utils.trans('find-servers')
            embed = self.bot.embed_template(title=title, description=description)
            await message.edit(embed=embed)
            await asyncio.sleep(2)

            api_servers = await api.Servers.get_servers(db_guild.auth)
            match_server = None
            for server in api_servers:
                try:
                    server_up = await api.Servers.is_server_available(server.id, db_guild.auth)
                except Exception as e:
                    print(e)
                    continue
                if server_up and not server.in_use:
                    match_server = server
                    break

            if not match_server:
                await api.Teams.delete_team(team1_id, db_guild.auth)
                await api.Teams.delete_team(team2_id, db_guild.auth)
                description = '✅ 1. ' + utils.trans('creating-teams') + '\n' \
                              '✅ 2. ' + utils.trans('pick-maps') + '\n' \
                              '❌ 3. ' + utils.trans('find-servers')
                embed = self.bot.embed_template(title=title, description=description)
                await message.edit(embed=embed)
                return False

            server_id = match_server.id

            description = '✅ 1. ' + utils.trans('creating-teams') + '\n' \
                          '✅ 2. ' + utils.trans('pick-maps') + '\n' \
                          '✅ 3. ' + utils.trans('find-servers') + '\n' \
                          '⌛️ 4. ' + utils.trans('creating-match')

            embed = self.bot.embed_template(title=title, description=description)
            await message.edit(embed=embed)
            await asyncio.sleep(2)

            str_maps = ' '.join(m.dev_name for m in maps_list)

            match_id = await api.Matches.create_match(
                server_id,
                team1_id,
                team2_id,
                str_maps,
                len(team_one + team_two),
                db_guild.auth
            )

            description = '✅ 1. ' + utils.trans('creating-teams') + '\n' \
                          '✅ 2. ' + utils.trans('pick-maps') + '\n' \
                          '✅ 3. ' + utils.trans('find-servers') + '\n' \
                          '✅ 4. ' + utils.trans('creating-match')

            embed = self.bot.embed_template(title=title, description=description)
            await message.edit(embed=embed)
            await asyncio.sleep(2)

        except asyncio.TimeoutError:
            description = utils.trans('match-took-too-long')
        except (discord.NotFound, ValueError):
            description = utils.trans('match-setup-cancelled')
        except Exception as e:
            self.bot.logger.error(f'caught error when calling start_match(): {e}')
            description = description.replace('⌛️', '❌')
            description += f'\n\n```{e}```'
        else:
            guild = lobby.guild
            match_catg = await guild.create_category_channel(utils.trans("match-id", match_id))

            team1_channel = await guild.create_voice_channel(
                name=utils.trans("match-team", team1_name),
                category=match_catg,
                user_limit=len(team_one)
            )

            team2_channel = await guild.create_voice_channel(
                name=utils.trans("match-team", team2_name),
                category=match_catg,
                user_limit=len(team_two)
            )

            awaitables = [
                team1_channel.set_permissions(guild.self_role, connect=True),
                team2_channel.set_permissions(guild.self_role, connect=True),
                team1_channel.set_permissions(guild.default_role, connect=False, read_messages=True),
                team2_channel.set_permissions(guild.default_role, connect=False, read_messages=True)
            ]

            for team in [team_one, team_two]:
                for user in team:
                    if user in team_one:
                        awaitables.append(team1_channel.set_permissions(user, connect=True))
                        awaitables.append(user.move_to(team1_channel))
                    else:
                        awaitables.append(team2_channel.set_permissions(user, connect=True))
                        awaitables.append(user.move_to(team2_channel))
            
            await asyncio.gather(*awaitables, loop=self.bot.loop, return_exceptions=True)

            await DB.helper.query(
                "INSERT INTO matches (id, guild, channel, message, category, team1_channel, team2_channel)\n"
                f"    VALUES ({match_id},\n"
                f"        {guild.id},\n"
                f"        {lobby.queue_channel.id},\n"
                f"        {message.id},\n"
                f"        {match_catg.id},\n"
                f"        {team1_channel.id},\n"
                f"        {team2_channel.id});"
            )

            await DB.helper.insert_match_users(
                match_id,
                *[user.id for user in team_one + team_two]
            )

            if not self.check_matches.is_running():
                self.check_matches.start()

            return True

        embed = self.bot.embed_template(title=title, description=description)
        try:
            await message.edit(content='', embed=embed)
        except discord.NotFound:
            pass
        await asyncio.sleep(2)
        return False

    @tasks.loop(seconds=20.0)
    async def check_matches(self):
        match_ids = await DB.helper.query(
            "SELECT id from matches;",
            ret_key='id'
        )

        if match_ids:
            for match_id in match_ids:
                try:
                    await self.update_match_message(match_id)
                except Exception as e:
                    self.bot.logger.error(f'caught error when calling check_matches(): {e}')
        else:
            self.check_matches.cancel()

    async def update_match_message(self, match_id):
        """"""
        api_match = None
        api_server = None
        api_mapstats = []
        api_scoreboard = []

        match_data = await DB.helper.fetch_row(
            "SELECT * FROM matches\n"
            f"    WHERE id = {match_id};"
        )
        db_match = await utils.Match.from_dict(self.bot, match_data)

        try:
            api_match = await api.Matches.get_match(db_match.id)
        except Exception as e:
            print(e)

        try:
            api_server = await api.Servers.get_server(api_match.server_id, db_match.db_guild.auth)
        except Exception as e:
            print(e)

        try:
            api_mapstats = await api.MapStats.get_mapstats(api_match.id)
        except Exception as e:
            print(e)

        try:
            api_scoreboard = await api.Scoreboard.get_match_scoreboard(api_match.id)
        except Exception as e:
            print(e)

        embed = self._embed_match(api_match, api_server, api_mapstats, api_scoreboard)

        try:
            await db_match.message.edit(embed=embed)
        except Exception as e:
            print(e)
            try:
                message = await db_match.channel.send(embed=embed)
                await DB.helper.query(
                    "UPDATE matches\n"
                    f"    SET message = {message.id};"
                )
            except Exception as e:
                print(e)
                pass
        
        if api_match.end_time:
            await self.remove_teams_channels(db_match)

    async def remove_teams_channels(self, db_match):
        """"""
        guild = db_match.db_guild.guild
        banned_users = await DB.helper.get_banned_users(guild.id)
        banned_users = [guild.get_member(user_id) for user_id in banned_users]

        match_player_ids = await DB.helper.query(
            "SELECT user_id FROM match_users\n"
            f"    WHERE match_id = {db_match.id};",
            ret_key='user_id'
        )
        match_players = [guild.get_member(user_id) for user_id in match_player_ids]

        awaitables = []
        for user in match_players:
            if user is not None:
                if user not in banned_users:
                    awaitables.append(user.add_roles(db_match.db_guild.linked_role))
                awaitables.append(user.move_to(db_match.db_guild.prematch_channel))

        await asyncio.gather(*awaitables, loop=self.bot.loop, return_exceptions=True)

        for channel in [db_match.team1_channel, db_match.team2_channel, db_match.category]:
            try:
                await channel.delete()
            except (AttributeError, discord.NotFound):
                pass

        await DB.helper.query(
            "DELETE FROM matches\n"
            f"    WHERE id = {db_match.id};"
        )

    @end.error
    @add.error
    @remove.error
    @pause.error
    @unpause.error
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

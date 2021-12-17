# stats.py

from discord.ext import commands

from .utils import utils, api
from ..resources import DB


class StatsCog(commands.Cog):
    """"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(brief=utils.trans('command-stats-brief'),
                      aliases=['rank'])
    async def stats(self, ctx):
        """"""
        user_data = await DB.helper.fetch_row(
            "SELECT * FROM users\n"
            f"    WHERE discord_id = {ctx.author.id};"
        )

        if not user_data:
            msg = utils.trans('stats-not-linked', ctx.author.display_name)
            raise commands.UserInputError(message=msg)

        db_user = utils.User.from_dict(user_data, ctx.guild)
        try:
            stats = await api.PlayerStats.get_player_stats(db_user)
        except Exception as e:
            raise commands.UserInputError(message=str(e))

        if not stats:
            msg = utils.trans('stats-no-matches', ctx.author.display_name)
            raise commands.UserInputError(message=msg)

        description = '```ml\n' \
                     f' {utils.trans("stats-kills")}:             {stats.kills} \n' \
                     f' {utils.trans("stats-deaths")}:            {stats.deaths} \n' \
                     f' {utils.trans("stats-assists")}:           {stats.assists} \n' \
                     f' {utils.trans("stats-kdr")}:         {stats.kdr} \n' \
                     f' {utils.trans("stats-hs")}:         {stats.headshot_kills} \n' \
                     f' {utils.trans("stats-hsp")}:  {stats.hsp} \n' \
                     f' {utils.trans("stats-played")}:    {stats.total_maps} \n' \
                     f' {utils.trans("stats-wins")}:        {stats.wins} \n' \
                     f' {utils.trans("stats-win-rate")}:       {stats.win_percent} \n' \
                     f' ------------------------- \n' \
                     f' {utils.trans("stats-rating")}:    {stats.average_rating} \n' \
                      '```'
        embed = self.bot.embed_template(title=ctx.author.display_name, description=description)
        await ctx.message.reply(embed=embed)

    @commands.command(brief=utils.trans('command-leaders-brief'),
                      aliases=['top', 'ranks'])
    async def leaders(self, ctx):
        """"""
        guild_data = await DB.helper.fetch_row(
            "SELECT * FROM guilds\n"
            f"    WHERE id = {ctx.guild.id};"
        )
        db_guild = utils.Guild.from_dict(self.bot, guild_data)

        if not db_guild.is_setup:
            raise commands.UserInputError(message=utils.trans('bot-not-setup', self.bot.command_prefix[0]))

        num = 10
        try:
            guild_players = await api.Leaderboard.get_leaderboard(ctx.guild.members)
        except Exception as e:
            raise commands.UserInputError(message=str(e))

        guild_players.sort(key=lambda u: (u.average_rating), reverse=True)
        guild_players = guild_players[:num]

        # Generate leaderboard text
        data = [['Player'] + [player.name for player in guild_players],
                ['Kills'] + [str(player.kills) for player in guild_players],
                ['Deaths'] + [str(player.deaths) for player in guild_players],
                ['Played'] + [str(player.total_maps) for player in guild_players],
                ['Wins'] + [str(player.wins) for player in guild_players],
                ['Rating'] + [str(player.average_rating) for player in guild_players]]
        data[0] = [name if len(name) < 12 else name[:9] + '...' for name in data[0]]  # Shorten long names
        widths = list(map(lambda x: len(max(x, key=len)), data))
        aligns = ['left', 'center', 'center', 'center', 'center', 'right']
        z = zip(data, widths, aligns)
        formatted_data = [list(map(lambda x: utils.align_text(x, width, align), col)) for col, width, align in z]
        formatted_data = list(map(list, zip(*formatted_data)))  # Transpose list for .format() string

        description = '```ml\n    {}  {}  {}  {}  {}  {} \n'.format(*formatted_data[0])

        for rank, player_row in enumerate(formatted_data[1:], start=1):
            description += ' {}. {}  {}  {}  {}  {}  {} \n'.format(rank, *player_row)

        description += '```'

        # Send leaderboard
        title = f'__{utils.trans("leaderboard")}__'
        embed = self.bot.embed_template(title=title, description=description)
        await ctx.message.reply(embed=embed)

    @stats.error
    @leaders.error
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

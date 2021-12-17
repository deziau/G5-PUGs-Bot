# link.py

from discord.ext import commands
from steam.steamid import SteamID, from_url

from .utils import utils
from ..resources import DB


class LinkCog(commands.Cog):
    """"""
    def __init__(self, bot):
        """"""
        self.bot = bot

    @commands.command(brief=utils.trans('link-command-brief'),
                      usage='link <steam_id> <flag_emoji>')
    async def link(self, ctx, *args):
        """"""
        guild_data = await DB.helper.fetch_row(
            "SELECT * FROM guilds\n"
            f"    WHERE id = {ctx.guild.id};"
        )
        db_guild = utils.Guild.from_dict(self.bot, guild_data)
        
        if not db_guild.is_setup:
            raise commands.UserInputError(message=utils.trans('bot-not-setup', self.bot.command_prefix[0]))

        user = ctx.author
        try:
            steam_id = args[0]
            flag = args[1]
        except IndexError:
            msg = utils.trans('invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        banned_users = await DB.helper.get_banned_users(ctx.guild.id)

        if user.id in banned_users:
            raise commands.UserInputError(message=utils.trans('no-access-for-ban'))

        user_data = await DB.helper.fetch_row(
            "SELECT * FROM users\n"
            f"    WHERE discord_id = {user.id};"
        )

        if user_data:
            db_user = utils.User.from_dict(user_data, ctx.guild)
            raise commands.UserInputError(message=utils.trans('account-already-linked', db_user.steam))

        try:
            steam = SteamID(steam_id)
        except ValueError:
            raise commands.UserInputError(message=utils.trans('invalid-steam-id'))

        if not steam.is_valid():
            steam = from_url(steam_id, http_timeout=15)
            if steam is None:
                steam = from_url(f'https://steamcommunity.com/id/{steam_id}/', http_timeout=15)
                if steam is None:
                    raise commands.UserInputError(message=utils.trans('invalid-steam-id'))
        
        if flag not in utils.FLAG_CODES:
            raise commands.UserInputError(message=utils.trans('invalid-flag-emoji'))

        try:
            await DB.helper.query(
                "INSERT INTO users (discord_id, steam_id, flag)\n"
                f"    VALUES({user.id}, '{steam}', '{flag}')\n"
                "    ON CONFLICT DO NOTHING\n"
                "    RETURNING discord_id;"
            )
        except Exception as e:
            print(e)
            raise commands.UserInputError(message=utils.trans('steam-linked-to-another-user'))

        await user.add_roles(db_guild.linked_role)
        embed = self.bot.embed_template(description=utils.trans('link-steam-success', user.mention, steam))
        await ctx.message.reply(embed=embed)

    @commands.command(brief=utils.trans('command-unlink-brief'),
                      usage='unlink <mention>')
    @commands.has_permissions(ban_members=True)
    async def unlink(self, ctx):
        """"""
        try:
            user = ctx.message.mentions[0]
        except IndexError:
            msg = utils.trans('invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        user_data = await DB.helper.fetch_row(
            "SELECT * FROM users\n"
            f"    WHERE discord_id = {user.id};"
        )
        if not user_data:
            raise commands.UserInputError(message=utils.trans('unable-to-unlink', user.mention))

        guild_data = await DB.helper.fetch_row(
            "SELECT * FROM guilds\n"
            f"    WHERE id = {ctx.guild.id};"
        )
        db_guild = utils.Guild.from_dict(self.bot, guild_data)

        if not db_guild.is_setup:
            raise commands.UserInputError(message=utils.trans('bot-not-setup', self.bot.command_prefix[0]))

        await DB.helper.query(
            "DELETE FROM users\n"
            f"    WHERE discord_id = {user.id};"
        )
        await user.remove_roles(db_guild.linked_role)
        embed = self.bot.embed_template(description=utils.trans('unlink-steam-success', user.mention))
        await ctx.message.reply(embed=embed)

    @link.error
    @unlink.error
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

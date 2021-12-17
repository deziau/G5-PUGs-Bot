# setup.py

import discord
from discord.ext import commands
from ..resources import DB
from .utils import utils, api


class SetupCog(commands.Cog):
    """"""
    def __init__(self, bot):
        """"""
        self.bot = bot

    @commands.command(brief=utils.trans('command-setup-brief'),
                      usage='setup <API Key>')
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx, *args):
        """"""
        try:
            api_key = args[0]
        except IndexError:
            msg = utils.trans('invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        try:
            await api.check_auth({'user-api': api_key})
        except Exception as e:
            raise commands.UserInputError(message=str(e))

        guild_data = await DB.helper.fetch_row(
            "SELECT * FROM guilds\n"
            f"    WHERE id = {ctx.guild.id};"
        )
        db_guild = utils.Guild.from_dict(self.bot, guild_data)

        category = db_guild.category
        linked_role = db_guild.linked_role
        prematch_channel = db_guild.prematch_channel

        if not category:
            category = await ctx.guild.create_category_channel('G5')

        if not linked_role:
            linked_role = await ctx.guild.create_role(name='Linked')

        if not prematch_channel:
            prematch_channel = await ctx.guild.create_voice_channel(category=category, name='Pre-Match')

        await DB.helper.query(
            "UPDATE guilds\n"
            f"    SET api_key = '{api_key}',\n"
            f"        category = {category.id}\n,"
            f"        linked_role = {linked_role.id},\n"
            f"        prematch_channel = {prematch_channel.id}\n"
            f"    WHERE id = {ctx.guild.id};"
        )

        lobby_cog = self.bot.get_cog('LobbyCog')
        try:
            await lobby_cog.setup_lobbies(ctx.guild)
        except Exception as e:
            print(e)

        msg = utils.trans('setup-bot-success')
        embed = self.bot.embed_template(title=msg)
        await ctx.message.reply(embed=embed)

    @setup.error
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

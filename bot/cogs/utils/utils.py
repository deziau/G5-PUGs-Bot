# utils.py

import os
import re
import json
import math
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

import discord

from bot.resources import DB, Config


time_arg_pattern = re.compile(r'\b((?:(?P<days>[0-9]+)d)|(?:(?P<hours>[0-9]+)h)|(?:(?P<minutes>[0-9]+)m))\b')

FLAG_CODES = {
    '🇩🇿': 'DZ', '🇦🇷': 'AR', '🇦🇺': 'AU', '🇦🇹': 'AT', '🇦🇿': 'AZ', '🇧🇪': 'BE', '🇧🇷': 'BR',
    '🇧🇬': 'BG', '🇨🇦': 'CA', '🇷🇴': 'RO', '🇨🇳': 'CN', '🇨🇮': 'CI', '🇭🇷': 'HR', '🇰🇼': 'KW',
    '🇨🇿': 'CZ', '🇩🇰': 'DK', '🇪🇬': 'EG', '🇫🇴': 'FO', '🇫🇮': 'FI', '🇫🇷': 'FR', '🇩🇪': 'DE', '🇬🇷': 'GR',
    '🇭🇺': 'HU', '🇮🇸': 'IS', '🇮🇳': 'IN', '🇮🇶': 'IQ', '🇮🇪': 'IE', '🇮🇱': 'IL', '🇯🇵': 'JP', '🇯🇴': 'JO',
    '🇱🇧': 'LB', '🇱🇾': 'LY', '🇲🇦': 'MA', '🇳🇿': 'NZ', '🇳🇴': 'NO', '🇵🇸': 'PS', '🇵🇱': 'PL', '🇵🇹': 'PT',
    '🇶🇦': 'QA', '🇷🇺': 'RU', '🇸🇦': 'SA', '🇸🇰': 'SK', '🇸🇮': 'SI', '🇰🇷': 'KR', '🇪🇸': 'ES', '🇺🇾': 'UY',
    '🇸🇩': 'SD', '🇸🇪': 'SE', '🇨🇭': 'CH', '🇸🇾': 'SY', '🇾🇪': 'YE', '🇺🇳': 'UN', '🇺🇸': 'US', '🇬🇧': 'GB',
    '🇹🇳': 'TN', '🇹🇷': 'TR', '🇺🇦': 'UA', '🇦🇪': 'AE', '🇳🇱': 'NL', '🇰🇿': 'KZ'
}

EMOJI_NUMBERS = [
    u'\u0030\u20E3',
    u'\u0031\u20E3',
    u'\u0032\u20E3',
    u'\u0033\u20E3',
    u'\u0034\u20E3',
    u'\u0035\u20E3',
    u'\u0036\u20E3',
    u'\u0037\u20E3',
    u'\u0038\u20E3',
    u'\u0039\u20E3',
    u'\U0001F51F'
]

load_dotenv()

with open('translations.json', encoding="utf8") as f:
    translations = json.load(f)


class Map:
    """ A group of attributes representing a map. """

    def __init__(self, name, dev_name, emoji):
        """ Set attributes. """
        self.name = name
        self.dev_name = dev_name
        self.emoji = emoji


class Guild:
    """"""
    def __init__(
        self,
        guild,
        auth,
        linked_role,
        prematch_channel,
        category,
        lobbies_channel,
    ):
        """"""
        self.guild = guild
        self.auth = auth
        self.linked_role = linked_role
        self.prematch_channel = prematch_channel
        self.category = category
        self.lobbies_channel = lobbies_channel
        self.is_setup = any(auth.values()) and linked_role and prematch_channel

    @classmethod
    def from_dict(cls, bot, guild_data: dict):
        """"""
        guild = bot.get_guild(guild_data['id'])

        return cls(
            guild,
            {'user-api': guild_data['api_key']},
            guild.get_role(guild_data['linked_role']),
            guild.get_channel(guild_data['prematch_channel']),
            guild.get_channel(guild_data['category']),
            guild.get_channel(guild_data['lobbies_channel']),
        )


class Lobby:
    """"""
    def __init__(
        self,
        lobby_id,
        guild,
        name,
        capacity,
        series,
        channel,
        message,
        category,
        queue_channel,
        lobby_channel,
        last_message,
        team_method,
        captain_method,
        mpool
    ):
        """"""
        self.id = lobby_id
        self.guild = guild
        self.name = name
        self.capacity = capacity
        self.series = series
        self.channel = channel
        self.message = message
        self.category = category
        self.queue_channel = queue_channel
        self.lobby_channel = lobby_channel
        self.last_message = last_message
        self.team_method = team_method
        self.captain_method = captain_method
        self.mpool = mpool

    @classmethod
    def from_dict(cls, bot, lobby_data: dict):
        """"""
        guild = bot.get_guild(lobby_data['guild'])
        channel = guild.get_channel(lobby_data['channel'])
        category = guild.get_channel(lobby_data['category'])
        queue_channel = guild.get_channel(lobby_data['queue_channel'])
        lobby_channel = guild.get_channel(lobby_data['lobby_channel'])
        try:
            last_message = queue_channel.get_partial_message(lobby_data['last_message'])
        except AttributeError:
            last_message = None
        try:
            message = channel.get_partial_message(lobby_data['message'])
        except AttributeError:
            message = None

        return cls(
            lobby_data['id'],
            guild,
            lobby_data['name'],
            lobby_data['capacity'],
            lobby_data['series_type'],
            channel,
            message,
            category,
            queue_channel,
            lobby_channel,
            last_message,
            lobby_data['team_method'],
            lobby_data['captain_method'],
            [m for m in bot.all_maps.values() if lobby_data[m.dev_name]]
        )


class Match:
    """"""
    def __init__(
        self,
        match_id,
        guild,
        channel,
        message,
        category,
        team1_channel,
        team2_channel
    ):
        """"""
        self.id = match_id
        self.guild = guild
        self.channel = channel
        self.message = message
        self.category = category
        self.team1_channel = team1_channel
        self.team2_channel = team2_channel

    @classmethod
    def from_dict(cls, bot, match_data: dict):
        """"""
        guild = bot.get_guild(match_data['guild'])
        channel = guild.get_channel(match_data['channel'])

        try:
            message = channel.get_partial_message(match_data['message'])
        except AttributeError:
            message = None

        return cls(
            match_data['id'],
            guild,
            channel,
            message,
            guild.get_channel(match_data['category']),
            guild.get_channel(match_data['team1_channel']),
            guild.get_channel(match_data['team2_channel'])
        )


class User:
    """"""
    def __init__(
        self,
        discord,
        steam,
        flag
    ):
        """"""
        self.discord = discord
        self.steam = steam
        self.flag = flag

    @classmethod
    def from_dict(cls, user_data: dict, guild):
        """"""
        return cls(
            guild.get_member(user_data['discord_id']),
            user_data['steam_id'],
            user_data['flag']
        )


def trans(text, *args):
    lang = os.environ['DISCORD_BOT_LANGUAGE']
    trans_text = ''
    if args:
        try:
            trans_text = translations[lang][text].format(*args)
        except (KeyError, ValueError):
            trans_text = translations['en'][text].format(*args)
    else:
        try:
            trans_text = translations[lang][text].replace('{}', '')
        except (KeyError, ValueError):
            trans_text = translations['en'][text].replace('{}', '')

    return trans_text


def timedelta_str(tdelta):
    """ Convert time delta object to a worded string representation with only days, hours and minutes. """
    conversions = (('days', 86400), ('hours', 3600), ('minutes', 60))
    secs_left = int(tdelta.total_seconds())
    unit_strings = []

    for unit, conversion in conversions:
        unit_val, secs_left = divmod(secs_left, conversion)

        if unit_val != 0 or (unit == 'minutes' and len(unit_strings) == 0):
            unit_strings.append(f'{unit_val} {unit}')

    return ', '.join(unit_strings)


def unbantime(arg):
    # Parse the time arguments
    time_units = ('days', 'hours', 'minutes')
    time_delta_values = {}  # Holds the values for each time unit arg

    for match in time_arg_pattern.finditer(arg):  # Iterate over the time argument matches
        for time_unit in time_units:  # Figure out which time unit this match is for
            time_value = match.group(time_unit)  # Get the value for this unit

            if time_value is not None:  # Check if there is an actual group value
                time_delta_values[time_unit] = int(time_value)
                break  # There is only ever one group value per match

    # Set unban time if there were time arguments
    time_delta = timedelta(**time_delta_values)
    unban_time = None if time_delta_values == {} else datetime.now(timezone.utc) + time_delta
    return time_delta, unban_time


def align_text(text, length, align='center'):
    """ Center the text within whitespace of input length. """
    if length < len(text):
        return text

    whitespace = length - len(text)

    if align == 'center':
        pre = math.floor(whitespace / 2)
        post = math.ceil(whitespace / 2)
    elif align == 'left':
        pre = 0
        post = whitespace
    elif align == 'right':
        pre = whitespace
        post = 0
    else:
        raise ValueError('Align argument must be "center", "left" or "right"')

    return ' ' * pre + text + ' ' * post


async def create_emojis(bot):
    """ Upload custom map emojis to guilds. """
    guild = bot.get_guild(Config.main_guild)
    if not guild:
        bot.logger.error('Invalid "EMOJIS_GUILD_ID" value from .env file! closing the bot..')
        await bot.close()

    icons_dic = 'assets/maps/icons/'
    icons = os.listdir(icons_dic)

    guild_emojis_str = [e.name for e in guild.emojis]

    for icon in icons:
        if icon.endswith('.png') and '-' in icon and os.stat(icons_dic + icon).st_size < 256000:
            map_name = icon.split('-')[0]
            map_dev = icon.split('-')[1].split('.')[0]

            if map_dev in guild_emojis_str:
                emoji = discord.utils.get(guild.emojis, name=map_dev)
            else:
                with open(icons_dic + icon, 'rb') as image:
                    try:
                        emoji = await guild.create_custom_emoji(name=map_dev, image=image.read())
                        bot.logger.info(f'Emoji "{emoji.name}" created successfully')
                    except discord.Forbidden:
                        bot.logger.error('Bot does not have permission to create custom emojis in the specified server')
                        await bot.close()
                    except discord.HTTPException as e:
                        bot.logger.error(f'HTTP exception raised when creating emoji for icon "{map_dev}": {e.text} ({e.code})')
                        await bot.close()
                    except Exception as e:
                        bot.logger.error(f'Exception {e} occurred')
                        await bot.close()

            bot.all_maps[map_dev] = Map(
                map_name,
                map_dev,
                f'<:{map_dev}:{emoji.id}>'
            )

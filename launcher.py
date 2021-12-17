# launcher.py

from bot.bot import G5Bot
from bot.resources import Config

import argparse
from dotenv import load_dotenv
import os

load_dotenv()  # Load the environment variables in the local .env file


def run_bot():
    """ Parse the config file and run the bot. """
    # Get environment variables and set configs
    web_panel = os.environ['WEB_PANEL']
    api_url = os.environ['API_URL']

    if web_panel.endswith('/'):
        web_panel = web_panel[:-1]
    if api_url.endswith('/'):
        api_url = api_url[:-1]

    db_connect_url = 'postgresql://{POSTGRESQL_USER}:{POSTGRESQL_PASSWORD}@{POSTGRESQL_HOST}/{POSTGRESQL_DB}'

    Config.discord_token = os.environ['DISCORD_BOT_TOKEN']
    Config.prefixes = os.environ['DISCORD_BOT_PREFIXES'].split()
    Config.main_guild = int(os.environ['EMOJIS_GUILD_ID'])
    Config.db_connect_url = db_connect_url.format(**os.environ)
    Config.web_panel = web_panel
    Config.api_url = api_url
    Config.lang = os.environ['DISCORD_BOT_LANGUAGE']
    Config.game_mode_comp_value = int(os.environ['GAMEMODE_COMPETITIVE'])
    Config.game_mode_wing_value = int(os.environ['GAMEMODE_WINGMAN'])
    Config.get5_comp_cfg = os.environ["GET5_COMPRTITIVE_CFG"]
    Config.get5_wing_cfg = os.environ["GET5_WINGMAN_CFG"]
    
    # Instantiate bot and run
    bot = G5Bot()
    bot.run()


if __name__ == '__main__':
    argparse.ArgumentParser(description='Run the G5 bot')
    run_bot()

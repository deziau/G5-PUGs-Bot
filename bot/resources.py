# resources.py

from aiohttp import ClientSession
from .cogs.utils.db import DBHelper


class Sessions:
    requests: ClientSession

class DB:
    helper: DBHelper

class Config:
    discord_token: str
    prefixes: list
    main_guild: int
    db_connect_url: str
    web_panel: str
    api_url: str
    lang: str
    game_mode_comp_value: int
    game_mode_wing_value: int
    get5_comp_cfg: str
    get5_wing_cfg: str


# api.py

import datetime
from aiohttp import ClientConnectionError, ContentTypeError
from asyncio import TimeoutError

from .utils import FLAG_CODES
from ...resources import Config, Sessions, DB


async def check_auth(auth):
    """"""
    url = f'{Config.api_url}'

    try:
        async with Sessions.requests.get(url=url, headers=auth) as resp:
            if '/auth/steam' in str(resp.url):
                raise Exception('Invalid API Key')
    except (ClientConnectionError, TimeoutError, ContentTypeError):
        raise Exception('Unable to connect to the API, Please try again later.')


class Teams:
    """"""

    def __init__(self, data) -> None:
        """"""
        self.id = data['id']
        self.user_id = data['user_id']
        self.name = data['name']
        self.tag = data['tag']
        self.flag = data['flag']
        self.logo = data['logo']
        self.public_team = data['public_team']
        self.auth_name = data['auth_name']

    @classmethod
    async def get_team(cls, team_id: int):
        """"""
        url = f'{Config.api_url}/teams/{team_id}'

        try:
            async with Sessions.requests.get(url=url) as resp:
                if '/auth/steam' in str(resp.url):
                    raise Exception('Invalid API Key')
                if resp.status != 200:
                    raise Exception(f'Team id {team_id} was not found')
                resp_data = await resp.json()
                return cls(resp_data['team'])
        except (ClientConnectionError, TimeoutError, ContentTypeError):
            raise Exception('Unable to connect to the API, Please try again later.')

    @staticmethod
    async def create_team(name, users, auth):
        """"""
        user_ids = [user.id for user in users]
        users_data = await DB.helper.get_users(user_ids)
        users_data.sort(key=lambda x: user_ids.index(x['discord_id']))

        url = f'{Config.api_url}/teams'
        data = {
            'name': name,
            'flag': FLAG_CODES[users_data[0]['flag']],
            'public_team': 0,
            'auth_name': {
                users_data[index]['steam_id']: {
                    'name': user.display_name,
                    'captain': int(users.index(user) == 0)
                } for index, user in enumerate(users)
            }
        }

        try:
            async with Sessions.requests.post(url=url, json=[data], headers=auth) as resp:
                if '/auth/steam' in str(resp.url):
                    raise Exception('Invalid API Key')
                if resp.status != 200:
                    raise Exception(f'API ERROR!!! Unable to create team')
                resp_data = await resp.json()
                return resp_data['id']
        except (ClientConnectionError, TimeoutError, ContentTypeError):
            raise Exception('Unable to connect to the API, Please try again later.')

    @staticmethod
    async def delete_team(team_id, auth):
        """"""
        url = f'{Config.api_url}/teams'
        data = {'team_id': team_id}

        try:
            async with Sessions.requests.delete(url=url, json=[data], headers=auth) as resp:
                if '/auth/steam' in str(resp.url):
                    raise Exception('Invalid API Key')
                elif resp.status == 403:
                    raise Exception(f'No permission to delete team id #{team_id}')
                elif resp.status == 404:
                    raise Exception(f'Team id #{team_id} was not found')
                elif resp.status == 500:
                    raise Exception(f'API ERROR!!! Unable to delete team id #{team_id}')
                return True
        except (ClientConnectionError, TimeoutError, ContentTypeError):
            raise Exception('Unable to connect to the API, Please try again later.')

    @staticmethod
    async def add_team_member(team_id, user_data, auth, captain=False):
        """"""
        url = f'{Config.api_url}/teams'
        data = {
            'id': team_id,
            'auth_name': {
                user_data.steam: {
                    'name': user_data.discord.display_name,
                    'captain': captain
                }
            }
        }

        try:
            async with Sessions.requests.put(url=url, json=[data], headers=auth) as resp:
                if '/auth/steam' in str(resp.url):
                    raise Exception('Invalid API Key')
                elif resp.status == 403:
                    raise Exception(f'No permission to add player {user_data.discord.mention} to team id #{team_id}')
                elif resp.status == 404:
                    raise Exception(f'Team id #{team_id} was not found')
                elif resp.status == 500:
                    raise Exception(f'API ERROR!!! Unable to add player {user_data.discord.mention} to team id #{team_id}')
                return True
        except (ClientConnectionError, TimeoutError, ContentTypeError):
            raise Exception('Unable to connect to the API, Please try again later.')

    @staticmethod
    async def remove_team_member(team_id, user_data, auth):
        """"""
        url = f'{Config.api_url}/teams'
        data = {
            'team_id': team_id,
            'steam_id': user_data.steam
        }

        try:
            async with Sessions.requests.delete(url=url, json=[data], headers=auth) as resp:
                if '/auth/steam' in str(resp.url):
                    raise Exception('Invalid API Key')
                elif resp.status == 403:
                    raise Exception(f'No permission to remove player {user_data.discord.mention} from team id #{team_id}')
                elif resp.status == 404:
                    raise Exception(f'Team id #{team_id} was not found')
                elif resp.status == 500:
                    raise Exception(f'API ERROR!!! Unable to remove player {user_data.discord.mention} from team id #{team_id}')
                return True
        except (ClientConnectionError, TimeoutError, ContentTypeError):
            raise Exception('Unable to connect to the API, Please try again later.')


class Servers:
    """"""

    def __init__(self, data) -> None:
        """"""
        self.id = data['id']
        self.ip_string = data['ip_string']
        self.port = data['port']
        self.gotv_port = data['gotv_port']
        self.display_name = data['display_name']
        self.flag = data['flag']
        self.public_server = data['public_server']
        self.in_use = data['in_use']

    @classmethod
    async def get_server(cls, server_id: int, auth):
        """"""
        url = f'{Config.api_url}/servers/{server_id}'

        try:
            async with Sessions.requests.get(url=url, headers=auth) as resp:
                if '/auth/steam' in str(resp.url):
                    raise Exception('Invalid API Key')
                if resp.status != 200:
                    raise Exception(f'Server id #{server_id} was not found')
                resp_data = await resp.json()
                return cls(resp_data['server'])
        except (ClientConnectionError, TimeoutError, ContentTypeError):
            raise Exception('Unable to connect to the API, Please try again later.')

    @classmethod
    async def get_servers(cls, auth):
        """"""
        url = f'{Config.api_url}/servers/myservers'

        try:
            async with Sessions.requests.get(url=url, headers=auth) as resp:
                if '/auth/steam' in str(resp.url):
                    raise Exception('Invalid API Key')
                if resp.status != 200:
                    raise Exception(f'API ERROR!!! Unable to get the user game servers')
                resp_data = await resp.json()
                return [cls(server) for server in resp_data['servers']]
        except (ClientConnectionError, TimeoutError, ContentTypeError):
            raise Exception('Unable to connect to the API, Please try again later.')

    @staticmethod
    async def is_server_available(server_id, auth):
        """"""
        url = f'{Config.api_url}/servers/{server_id}/status'

        try:
            async with Sessions.requests.get(url=url, headers=auth) as resp:
                if '/auth/steam' in str(resp.url):
                    raise Exception('Invalid API Key')
                if resp.status != 200:
                    resp_data = await resp.json()
                    raise Exception(resp_data['message'])
                return True
        except (ClientConnectionError, TimeoutError, ContentTypeError):
            raise Exception('Unable to connect to the API, Please try again later.')


class MapStats:
    """"""

    def __init__(self, data) -> None:
        """"""
        self.id = data['id']
        self.match_id = data['match_id']
        self.winner = data['winner']
        self.map_number = data['map_number']
        self.map_name = data['map_name']
        self.team1_score = data['team1_score']
        self.team2_score = data['team2_score']
        self.start_time = data['start_time']
        self.end_time = data['end_time']

    @classmethod
    async def get_mapstats(cls, match_id: int):
        """"""
        url = f'{Config.api_url}/mapstats/{match_id}'

        try:
            async with Sessions.requests.get(url=url) as resp:
                if '/auth/steam' in str(resp.url):
                    raise Exception('Invalid API Key')
                if resp.status != 200:
                    raise Exception(f'No map stats was found for match id #{match_id}')
                resp_data = await resp.json()
                return [cls(map_stat) for map_stat in resp_data['mapstats']]
        except (ClientConnectionError, TimeoutError, ContentTypeError):
            raise Exception('Unable to connect to the API, Please try again later.')


class Scoreboard:
    """"""

    def __init__(self, data) -> None:
        """"""
        self.id = data['id']
        self.match_id = data['match_id']
        self.map_id = data['map_id']
        self.team_id = data['team_id']
        self.steam_id = data['steam_id']
        self.name = data['name']
        self.kills = data['kills']
        self.headshot_kills = data['headshot_kills']
        self.deaths = data['deaths']
        self.assists = data['assists']
        self.flashbang_assists = data['flashbang_assists']
        self.roundsplayed = data['roundsplayed']
        self.teamkills = data['teamkills']
        self.suicides = data['suicides']
        self.damage = data['damage']
        self.bomb_plants = data['bomb_plants']
        self.bomb_defuses = data['bomb_defuses']
        self.v1 = data['v1']
        self.v2 = data['v2']
        self.v3 = data['v3']
        self.v4 = data['v4']
        self.v5 = data['v5']
        self.k1 = data['k1']
        self.k2 = data['k2']
        self.k3 = data['k3']
        self.k4 = data['k4']
        self.k5 = data['k5']
        self.firstdeath_ct = data['firstdeath_ct']
        self.firstdeath_t = data['firstdeath_t']
        self.firstkill_ct = data['firstkill_ct']
        self.firstkill_t = data['firstkill_t']
        self.kast = data['kast']
        self.score = data['contribution_score']
        self.winner = data['winner']
        self.mvp = data['mvp']

    @classmethod
    async def get_match_scoreboard(cls, match_id: int):
        """"""
        url = f'{Config.api_url}/playerstats/match/{match_id}'

        try:
            async with Sessions.requests.get(url=url) as resp:
                if '/auth/steam' in str(resp.url):
                    raise Exception('Invalid API Key')
                if resp.status != 200:
                    raise Exception(f'No players stats was found for match id #{match_id}')
                resp_data = await resp.json()
                return [cls(player_stat) for player_stat in resp_data['playerstats']]
        except (ClientConnectionError, TimeoutError, ContentTypeError):
            raise Exception('Unable to connect to the API, Please try again later.')


class PlayerStats:
    """"""

    def __init__(self, data) -> None:
        """"""
        self.steam_id = data['steamId']
        self.name = data['name']
        self.kills = data['kills']
        self.deaths = data['deaths']
        self.kdr = f'{self.kills / self.deaths:.2f}' if self.deaths else '0.00'
        self.assists = data['assists']
        self.flashbang_assists = data['fba']
        self.headshot_kills = data['hsk']
        self.hsp = data['hsp'] + '%'
        self.total_damage = data['total_damage']
        self.v1 = data['v1']
        self.v2 = data['v2']
        self.v3 = data['v3']
        self.v4 = data['v4']
        self.v5 = data['v5']
        self.k1 = data['k1']
        self.k2 = data['k2']
        self.k3 = data['k3']
        self.k4 = data['k4']
        self.k5 = data['k5']
        self.wins = data['wins']
        self.total_maps = data['total_maps']
        self.win_percent = f'{self.wins / self.total_maps * 100:.2f}%' if self.total_maps else '0.00%'
        self.average_rating = data['average_rating']

    @classmethod
    async def get_player_stats(cls, user_data, pug_stats=True):
        """"""
        url = f'{Config.api_url}/playerstats/{user_data.steam}/pug'
        if not pug_stats:
            url = url.replace('pug', 'official')

        try:
            async with Sessions.requests.get(url=url) as resp:
                if '/auth/steam' in str(resp.url):
                    raise Exception('Invalid API Key')
                if resp.status != 200:
                    raise Exception(f'No stats was found for steam id {user_data.steam}')
                resp_data = await resp.json()
                return cls(resp_data['pugstats'])
        except (ClientConnectionError, TimeoutError, ContentTypeError):
            raise Exception('Unable to connect to the API, Please try again later.')


class Leaderboard:
    """"""

    def __init__(self, data) -> None:
        """"""
        self.steam_id = data['steamId']
        self.name = data['name']
        self.kills = data['kills']
        self.deaths = data['deaths']
        self.assists = data['assists']
        self.flashbang_assists = data['fba']
        self.headshot_kills = data['hsk']
        self.total_damage = data['total_damage']
        self.v1 = data['v1']
        self.v2 = data['v2']
        self.v3 = data['v3']
        self.v4 = data['v4']
        self.v5 = data['v5']
        self.k1 = data['k1']
        self.k2 = data['k2']
        self.k3 = data['k3']
        self.k4 = data['k4']
        self.k5 = data['k5']
        self.wins = data['wins']
        self.total_maps = data['total_maps']
        self.win_percent = f'{self.wins / self.total_maps * 100:.2f}%' if self.total_maps else '0.00%'
        self.average_rating = data['average_rating']

    @classmethod
    async def get_leaderboard(cls, users, pug_stats=True, new_players=False):
        """"""
        user_ids = [user.id for user in users]
        users_data = await DB.helper.get_users(user_ids)
        if not users_data:
            return
        # users_data.sort(key=lambda x: user_ids.index(x['discord_id']))
        db_steam_ids = [usr['steam_id'] for usr in users_data]

        url = f'{Config.api_url}/leaderboard/players/pug'
        if not pug_stats:
            url = url.strip('/pug')

        try:
            async with Sessions.requests.get(url=url) as resp:
                if '/auth/steam' in str(resp.url):
                    raise Exception('Invalid API Key')
                if resp.status != 200:
                    raise Exception(f'API ERROR!!! Unable to get players stats')
                resp_data = await resp.json()
                players = list(filter(lambda x: x['steamId'] in db_steam_ids, resp_data['leaderboard']))
                if new_players:
                    api_steam_ids = [player['steamId'] for player in players]
                    for steam_id in db_steam_ids:
                        if steam_id not in api_steam_ids:
                            players.append({
                                'steamId': str(steam_id),
                                'name': 'new player',
                                'kills': 0,
                                'deaths': 0,
                                'assists': 0,
                                'fba': 0,
                                'hsk': 0,
                                'total_damage': 0,
                                'v1': 0,
                                'v2': 0,
                                'v3': 0,
                                'v4': 0,
                                'v5': 0,
                                'k1': 0,
                                'k2': 0,
                                'k3': 0,
                                'k4': 0,
                                'k5': 0,
                                'wins': 0,
                                'total_maps': 0,
                                'average_rating': "0.00"
                            })
                players.sort(key=lambda x: db_steam_ids.index(x['steamId']))
                return [cls(player) for player in players]
        except (ClientConnectionError, TimeoutError, ContentTypeError):
            raise Exception('Unable to connect to the API, Please try again later.')


class Matches:
    """"""

    def __init__(self, data) -> None:
        """"""
        self.id = data['id']
        self.user_id = data['user_id']
        self.server_id = data['server_id']
        self.team1_id = data['team1_id']
        self.team2_id = data['team2_id']
        self.winner = data['winner']
        self.team1_score = data['team1_score']
        self.team2_score = data['team2_score']
        self.team1_name = data['team1_string']
        self.team2_name = data['team2_string']
        self.cancelled = data['cancelled']
        self.forfeit = data['forfeit']
        self.start_time = data['start_time']
        self.end_time = data['end_time']
        self.match_title = data['title']
        self.max_maps = data['max_maps']
        self.season_id = data['season_id']
        self.is_pug = data['is_pug']

    @classmethod
    async def get_match(cls, match_id):
        """"""
        url = f'{Config.api_url}/matches/{match_id}'

        try:
            async with Sessions.requests.get(url=url) as resp:
                if '/auth/steam' in str(resp.url):
                    raise Exception('Invalid API Key')
                if resp.status != 200:
                    raise Exception(f'Match id #{match_id} was not found')
                resp_data = await resp.json()
                return cls(resp_data['match'])
        except (ClientConnectionError, TimeoutError, ContentTypeError):
            raise Exception('Unable to connect to the API, Please try again later.')

    @staticmethod
    async def get_recent_matches(limit=20):
        """"""
        url = f'{Config.api_url}/matches/limit/{limit}'

        try:
            async with Sessions.requests.get(url=url) as resp:
                if '/auth/steam' in str(resp.url):
                    raise Exception('Invalid API Key')
                if resp.status != 200:
                    raise Exception(f'API ERROR!!! Unable to recent matches')
                resp_data = await resp.json()
                return {match['id']: match['end_time'] is None for match in resp_data['matches']}
        except (ClientConnectionError, TimeoutError, ContentTypeError):
            raise Exception('Unable to connect to the API, Please try again later.')

    @staticmethod
    async def create_match(server_id, team1_id, team2_id, str_maps, total_players, auth):
        """"""
        url = f'{Config.api_url}/matches'

        data = {
            'server_id': server_id,
            'team1_id': team1_id,
            'team2_id': team2_id,
            'title': '[PUG] Map {MAPNUMBER} of {MAXMAPS}',
            'is_pug': 1,
            'start_time': datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            'ignore_server': 0,
            'max_maps': len(str_maps.split()),
            'veto_mappool': str_maps,
            'skip_veto': 1,
            'veto_first': 'team1',
            'side_type': 'always_knife',
            'players_per_team': total_players // 2,
            'min_players_to_ready': total_players // 2,
            'match_cvars': {
                'sv_hibernate_when_empty': 0,
                'game_mode': Config.game_mode_comp_value if total_players > 6 else Config.game_mode_wing_value,
                'get5_live_cfg': f'get5/{Config.get5_comp_cfg}' if total_players > 6 else  f'get5/{Config.get5_wing_cfg}',
                'get5_time_to_start': 600,  # warmup 10 minutes
                'get5_kick_when_no_match_loaded': 1,
                'get5_end_match_on_empty_server': 1
            }
        }

        try:
            async with Sessions.requests.post(url=url, json=[data], headers=auth) as resp:
                if '/auth/steam' in str(resp.url):
                    raise Exception('Invalid API Key')
                if resp.status != 200:
                    raise Exception(f'API ERROR!!! Unable to create match')
                resp_data = await resp.json()
                return resp_data['id']
        except (ClientConnectionError, TimeoutError, ContentTypeError):
            raise Exception('Unable to connect to the API, Please try again later.')

    @staticmethod
    async def cancel_match(match_id, auth):
        """"""
        url = f'{Config.api_url}/matches/{match_id}/cancel'
        data = {'match_id': match_id}

        try:
            async with Sessions.requests.get(url=url, json=[data], headers=auth) as resp:
                if '/auth/steam' in str(resp.url):
                    raise Exception('Invalid API Key')
                if resp.status == 401:
                    raise Exception(f'Match id #{match_id} is already finished')
                elif resp.status == 403:
                    raise Exception(f'No permission to cancel match id #{match_id}')
                elif resp.status == 404:
                    raise Exception(f'Match id #{match_id} was not found')
                elif resp.status in [422, 500]:
                    raise Exception(f'Error on game server')
                return True
        except (ClientConnectionError, TimeoutError, ContentTypeError):
            raise Exception('Unable to connect to the API, Please try again later.')

    @staticmethod
    async def add_match_player(user_data, match_id, team, auth):
        """"""
        url = f'{Config.api_url}/matches/{match_id}/{"addspec" if team == "spec" else "adduser"}'
        data = {
            'steam_id': user_data.steam,
            'team_id': team,
            'nickname': user_data.discord.display_name
        }

        try:
            async with Sessions.requests.put(url=url, json=[data], headers=auth) as resp:
                if '/auth/steam' in str(resp.url):
                    raise Exception('Invalid API Key')
                if resp.status == 401:
                    raise Exception(f'Unable to add players to match id #{match_id} because it is already finished')
                elif resp.status == 403:
                    raise Exception(f'No permission to add players to match id #{match_id}')
                elif resp.status == 404:
                    raise Exception(f'Match id #{match_id} was not found')
                elif resp.status in [422, 500]:
                    raise Exception(f'Error on game server')
                return True
        except (ClientConnectionError, TimeoutError, ContentTypeError):
            raise Exception('Unable to connect to the API, Please try again later.')

    @staticmethod
    async def remove_match_player(user_data, match_id, auth):
        """"""
        url = f'{Config.api_url}/matches/{match_id}/removeuser'
        data = {'steam_id': user_data.steam}

        try:
            async with Sessions.requests.put(url=url, json=[data], headers=auth) as resp:
                if '/auth/steam' in str(resp.url):
                    raise Exception('Invalid API Key')
                if resp.status == 401:
                    raise Exception(f'Unable to remove players from match id #{match_id} because it is already finished')
                elif resp.status == 403:
                    raise Exception(f'No permission to remove players from match id #{match_id}')
                elif resp.status == 404:
                    raise Exception(f'Match id #{match_id} was not found')
                elif resp.status in [422, 500]:
                    raise Exception(f'Error on game server')
                return True
        except (ClientConnectionError, TimeoutError, ContentTypeError):
            raise Exception('Unable to connect to the API, Please try again later.')

    @staticmethod
    async def pause_match(match_id, auth):
        """"""
        url = f'{Config.api_url}/matches/{match_id}/pause'

        try:
            async with Sessions.requests.get(url=url, headers=auth) as resp:
                if '/auth/steam' in str(resp.url):
                    raise Exception('Invalid API Key')
                if resp.status == 401:
                    raise Exception(f'Unable to pause match id #{match_id} because it is already finished')
                elif resp.status == 403:
                    raise Exception(f'No permission to pause match id #{match_id}')
                elif resp.status == 404:
                    raise Exception(f'Match id #{match_id} was not found')
                elif resp.status in [422, 500]:
                    raise Exception(f'Error on game server')
                return True
        except (ClientConnectionError, TimeoutError, ContentTypeError):
            raise Exception('Unable to connect to the API, Please try again later.')

    @staticmethod
    async def unpause_match(match_id, auth):
        """"""
        url = f'{Config.api_url}/matches/{match_id}/unpause'

        try:
            async with Sessions.requests.get(url=url, headers=auth) as resp:
                if '/auth/steam' in str(resp.url):
                    raise Exception('Invalid API Key')
                if resp.status == 401:
                    raise Exception(f'Unable to unpause match id #{match_id} because it is already finished')
                elif resp.status == 403:
                    raise Exception(f'No permission to unpause match id #{match_id}')
                elif resp.status == 404:
                    raise Exception(f'Match id #{match_id} was not found')
                elif resp.status in [422, 500]:
                    raise Exception(f'Error on game server')
                return True
        except (ClientConnectionError, TimeoutError, ContentTypeError):
            raise Exception('Unable to connect to the API, Please try again later.')

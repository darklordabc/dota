# -*- coding: utf-8 -*-

from __future__ import division

import itertools as it
import json

import arrow
import requests
from requests.exceptions import HTTPError
import pandas as pd
import numpy as np

from os.path import dirname, abspath

_hero_path = dirname(abspath(__file__)) + "/heroes_parsed.json"
_current_hero_path = dirname(abspath(__file__)) + "/current_heroes.json"
_abilities_path = dirname(abspath(__file__)) + "/abilities_parsed.json"
_items_path = dirname(abspath(__file__)) + "/items_parsed.json"

with open(_hero_path) as f:
    _heroes = json.load(f)
    _hero_roles = {x: _heroes[x].get('Role') for x in _heroes}
    _hero_roles = {hero: role.split(',') for hero, role in _hero_roles.items()
                   if role is not None}  # drops base
    # updated hero list
with open(_current_hero_path) as f:
    d = json.load(f)['heroes']
    _hero_names_to_id = {x['name'].split('npc_dota_hero_')[1]: x['id'] for x in d}
    _hero_id_to_names = {v: k for k, v in _hero_names_to_id.items()}

with open(_abilities_path) as f:
    _abilities = json.load(f)
    _ability_id_to_name = {v['ID']: k for k, v in _abilities.items()}
    _ability_name_to_id = {k: v['ID'] for k, v in _abilities.items()}

with open(_items_path) as f:
    _items = json.load(f)
    _item_id_to_name = {v['ID']: k for k, v in _items.items()}
    _item_name_to_id = {k: v['ID'] for k, v in _items.items()}


try:
    from itertools import filter
except ImportError:
    pass

_PRIVATE = 4294967295  # privacy option in client


def flatten(iterable):
    return it.chain.from_iterable(iterable)


def id_64(id_32):
    return id_32 + 76561197960265728


def id_32(id_64):
    return id_64 - 76561197960265728


# MYSTEAMID = "76561198025007092"
# LAST_MATCH_ID = "478948089"
#-----------------------------------------------------------------------------


class API:
    """
    The network side of things.


    Parameters
    ----------
    key: value API key

    Returns
    -------
    api: API

    Notes
    -----
    Call specific keyword args should go into their respective functions.
    """
    HISTORY_URL = "https://api.steampowered.com/IDOTA2Match_570/GetMatchHistory/V001/"
    MATCH_URL = "https://api.steampowered.com/IDOTA2Match_570/GetMatchDetails/V001/"
    TEAM_URL = "https://api.steampowered.com/IDOTA2Match_570/GetTeamInfoByTeamID/v001/"

    def __init__(self, key):
        self.key = key

        # ordinal times of patch releases (roughly)
        _679 = 1381989600
        _680 = 1390802400

    def get_match_history(self, **kwargs):
        """

        Parameters
        -----------------
        player_name: str
            Search matches with a player name, exact match only
        hero_id: str
            Search for matches with a specific hero being played (hero ID, not name, see HEROES below)
        game_mode: int
            Search for matches of a given mode (see below)
        skill: int
            0 for any, 1 for normal, 2 for high, 3 for very high skill (default is 0)
        date_min: int UTC
            date in UTC seconds since Jan 1, 1970 (unix time format)
        date_max: int UTC
            date in UTC seconds since Jan 1, 1970 (unix time format)
        min_players: int
            the minimum number of players required in the match
        account_id: int
            Search for all matches for the given user (32-bit or 64-bit steam ID)
        league_id: int
            matches for a particular league
        start_at_match_id: int
            Start the search at the indicated match id, descending
        matches_requested: int
            Maximum is 25 matches (default is 25)
        tournament_games_only:
            set to only show tournament games

        Examples
        --------

        import arrow
        now = arrow.utcnow()
        yest = now.replace(days=-1)

        h = api.API(key)
        history = h.get_match_history(date_min=yest.strftime('%s'),
                                      date_max=now.strftime('%s'))

        """
        # inpsect query so you can finish out the results.
        self.query = kwargs
        kwargs['key'] = self.key
        r = requests.get(self.HISTORY_URL, params=kwargs)
        hist = HistoryResponse(r.json()['result'], helper=self)
        # at time of implementation the date_min/max kwargs are browken
        # using start_at_match_id as a workaround
        while (hist.results_remaining > 0 and
               kwargs.get('matches_requested') is None):
            new_kwargs = kwargs.copy()
            new_start_match_id = min([m['match_id'] for m in hist.matches]) - 1
            new_kwargs['start_at_match_id'] = new_start_match_id
            r = requests.get(self.HISTORY_URL, params=new_kwargs)
            hist += HistoryResponse(r.json()['result'], helper=self)
        return hist

    def get_match_details(self, match_id, **kwargs):
        kwargs['key'] = self.key
        kwargs['match_id'] = match_id
        r = requests.get(self.MATCH_URL, params=kwargs)
        if r.status_code == 503:
            raise HTTPError
        return DetailsResponse(r.json()['result'])

    def get_heroes(self, to_disk=False):
        url = "https://api.steampowered.com/IEconDOTA2_570/GetHeroes/v0001/"
        r = requests.get(url, params={'key': self.key})
        if to_disk:
            with open(_hero_path, 'w') as f:
                json.dump(r['result'], f)
        return r.json()['result']

    def get_player_summaries(self):
        pass

    def get_full_history(self, account_id):
        pass

    def parse_match_history(self, history):
        return [self.parse_match(match) for match in history['matches']]

    @staticmethod
    def parse_match(match):
        pass

    @staticmethod
    def player_counts(history):
        ids = []
        for match in history['matches']:
            for player in match['players']:
                ids.append(player['account_id'])
        s = pd.Series(ids)
        s = s.replace(4294967295, np.nan)  # private profiles.
        return pd.value_counts(s)

    # @staticmethod
    # def match_ids(history):
    #     return [match['match_id'] for match in history['matches']]
    def get_team_info(self, id):
        """
        Used to get data about teams that have been created in the client.

        Parameters
        ----------
        id : team id
        n : number of teams to return
        """
        params = {'key': self.key, 'start_at_team_id': id,
                  'teams_requested': 1}
        r = requests.get(self.TEAM_URL, params=params)
        return TeamResponse(r.json()['result']['teams'][0])


class Response:
    """
    The local side.
    """
    pass


class HistoryResponse(Response):

    def __init__(self, resp, helper=None):

        self.status = resp['status']
        self.results_remaining = resp['results_remaining']
        self.num_results = resp['num_results']
        self.total_results = resp['total_results']
        self.matches = resp['matches']

        self.match_ids = [match['match_id'] for match in self.matches]
        self.helper = helper
        self.resp = resp
        self.details = {}

    def __add__(self, other):
        """
        Parameters
        ----------

        other : HistoryResponse

        Returns
        -------

        resp : HistoryResponse

        If ``other`` is an exhaustion of self then the total results and
        results remaing attributes are propogated to the retuern HistoryResponse.
        That's determined by the total results equaling (which is not
        foolproof).

        """
        resp1 = self.resp
        resp2 = other.resp

        resp = {}
        resp['num_results'] = len(self) + len(other)
        try:
            assert resp1['total_results'] == resp2['total_results']
            resp['results_remaining'] = min(resp1['results_remaining'],
                                            resp2['results_remaining'])
            resp['total_results'] = resp1['total_results']
        except AssertionError:
            resp['results_remaining'] = np.nan
            resp['total_results'] = np.nan
        resp['matches'] = resp1['matches'] + resp2['matches']
        resp['status'] = max(resp1['status'], resp2['status'])

        helper = self.helper or other.helper
        return HistoryResponse(resp, helper=helper)

    def __len__(self):
        return len(self.match_ids)

    def get_all_match_details(self, helper=None):

        import time
        details = {}
        N = len(self.match_ids)

        helper = helper or self.helper
        self._check_helper(helper=helper)

        for i, match in enumerate(self.match_ids):
            try:
                details[match] = helper.get_match_details(match)
            except HTTPError:
                import warnings
                warnings.warn("HTTPError on {}".format(match))
            time.sleep(.25)  # rate limiting
            # TODO: progress bar
            if round((i / N) * 100) % 10 == 0:
                print("\rAdded {} ({}%)".format(match, 100 * i / N))

        responses = {k: v for k, v in details.items()}
        return responses

    def update_details(self, responses):

        new_games = [k for k in responses if k in responses.keys() -
                     self.details.keys()]
        for k in new_games:
            self.details[k] = responses[k]

    def _check_helper(self, helper=None):
        if helper is None and self.helper is None:
            raise ValueError("Need to start an API object")

    def partner_counts(self):
        cts = []
        for match in self.matches:
            for player in match['players']:
                cts.append(player['account_id'])
        cts = pd.Series(cts)
        cts = cts.replace(4294967295, np.nan)
        return cts.value_counts()

    def to_json(self, filepath=None):
        """
        Need to persist history and all details.
        {
         history : self.resp,
         details : {match_id : game.resp}
        }
        """
        obj = {'history': self.resp,
               'details': {k: v.to_json() for k, v in self.details.items()}
               }
        if filepath is None:
            return json.dumps(obj)
        else:
            with open(filepath) as f:
                json.dump(obj, f)


class DetailsResponse(Response):

    game_mode = {1: 'All Pick',
                 2: 'Captains Mode',
                 3: 'Random Draft',
                 4: 'Single Draft',
                 5: 'All Random',
                 6: 'Intro?',
                 7: 'Diretide',
                 8: 'Reverse Captains Mode',
                 9: 'Greeviling',
                 10: 'Tutorial',
                 11: 'Mid Only',
                 12: 'Least Played',
                 13: 'New Player Pool'}

    """
    Detailed response of an individual game.

    Parameters
    ----------

    resp : dict

    Notes
    -----

    resp should be a dict returned by the dota2 WebAPI with the following keys:

    'radiant_win': bool
    'match_id': int
    'players': array

    """

    def __init__(self, resp):

        self.resp = resp
        if resp['radiant_win']:
            self.winner = 'Radiant'
        else:
            self.winner = 'Dire'
        self.match_id = resp['match_id']
        for p in resp['players']:
            if p.get('account_id') == _PRIVATE:
                p['account_id'] = np.nan
        self.player_ids = {'radiant': [], 'dire': []}
        for player in resp['players']:
            if player['player_slot'] < 5:
                self.player_ids['radiant'].append(player.get('account_id', np.nan))
            else:
                self.player_ids['dire'].append(player.get('account_id', np.nan))

        self.hero_name_to_id = _hero_names_to_id
        self.hero_id_to_names = {v: k for k, v in _hero_names_to_id.items()}

        self.negative_votes = self.resp['negative_votes']
        self.positive_votes = self.resp['positive_votes']
        self.lobby_type = self.resp['lobby_type']
        self.duration = self.resp['duration']
        self.first_blood_time = self.resp['first_blood_time']
        self.league_id = self.resp['leagueid']
        self.start_time = arrow.get(self.resp['start_time'])
        self.dire_name = resp.get('dire_name')
        self.radiant_name = resp.get('radiant_name')
        self.dire_team_id = resp.get('dire_team_id')
        self.radiant_team_id = resp.get('radiant_team_id')
        self.game_mode = resp.get('game_mode')
        self.picks_bans = self._parse_picks_bans(resp.get('picks_bans'))

    @staticmethod
    def from_json(f_obj):
        """
        Initialize from a JSON file.
        """

        with open(f_obj) as f:
            return DetailsResponse(json.load(f))

    @staticmethod
    def _parse_picks_bans(pick_bans):
        """
        Only available in CM (maybe captains draft too?)
        """
        if pick_bans:
            df = pd.DataFrame(pick_bans)
            return df

    @staticmethod
    def rep_team(x):
        if x < 5:
            return 'Radiant'
        else:
            return 'Dire'

    def by_player(self, key):
        """
        valid keys: {'kills', 'hero_id', 'player_slot', 'gold', 'gold_per_min',
                     'last_hits', 'ability_upgrades', 'level', 'hero_healing',
                     'deaths', 'leaver_status', 'additional_units',
                     'gold_spent', 'xp_per_min', 'assists', 'tower_damage',
                     'denies', 'hero_damage', 'item_4', 'item_5', 'item_2',
                     'item_3', 'item_0', 'item_1', 'account_id'}

        """
        # account id isn't nesc unique.
        return {player['hero_id']: player.get(key)
                for player in self.resp['players']}

    def match_report(self):
        # TODO: ability upgrades
        keys = ['level', 'kills', 'deaths', 'assists',
                'last_hits', 'denies', 'gold', 'gold_spent', 'player_slot',
                'account_id', 'hero_damage', 'hero_healing',
                'item_0', 'item_1', 'item_2', 'item_3', 'item_4',
                'item_5']
        df = pd.concat([pd.Series(self.by_player(key))
                        for key in keys], axis=1, keys=keys)
        df = self.format_df(df, self.winner, self.match_id)
        return df

    @staticmethod
    def format_df(df, winner, match_id):
        """
        Format a dataframe built from resp.

        Parameters
        ----------

        df : DataFrame built by concating data from resp.players
        winner : str
            'Radiant' or 'Dire'
        match_id : int
        """
        df['match_id'] = match_id
        try:
            df = df.set_index('hero_id')
        except KeyError:
            pass
        df = df.rename(index=lambda x:
                       _hero_id_to_names.get(int(x),
                                             str(x)))
        df.index.set_names(['hero'], inplace=True)

        df['team'] = df['player_slot'].apply(DetailsResponse.rep_team)
        df['win'] = df['team'] == winner
        df = df.sort('team', ascending=False)

        df = df.reset_index().set_index(['match_id', 'team', 'hero']).sort_index()
        return df

    def to_json(self, filepath=None):
        if filepath is None:
            return json.dumps(self.resp)
        else:
            with open(filepath, 'w') as f:
                json.dump(self.resp, f)

    def tower_status(self):
        """
        http://wiki.teamfortress.com/wiki/WebAPI/GetMatchDetails#Tower_Status
        """
        bsr = bin(self.resp['tower_status_radiant'])
        bsd = bin(self.resp['tower_status_dire'])

        d = {'radiant': bsr, 'dire': bsd}
        return d

    def barracks_status(self, team=None):
        """

        8-bit unsigned int.

        0 0 0 0 0 0 0 1
        ^ ^ ^ ^ ^ ^ ^ ^
        1 2 3 4 5 6 7 8

        1: unused
        2: unused
        3: bottom ranged
        4: bottom melee
        5: mid ranged
        6: mid melee
        7: top ranged
        8: top melee

        1 is up, 0 is destroyed.

        http://wiki.teamfortress.com/wiki/WebAPI/GetMatchDetails#Barracks_Status
        """
        bsr = bin(self.resp['barracks_status_radiant'])
        bsd = bin(self.resp['barracks_status_dire'])

        d = {'radiant': bsr, 'dire': bsd}
        return d

    def skill_build(self, hero='all'):
        """
        Display the skill build as a _.

        Parameters
        ----------

        hero : str

        TODO: http://cdn.dota2.com/apps/dota2/images/abilities/antimage_blink_lg.png
        """
        if hero == 'all':
            raise ValueError("Not  Implemented")
        else:
            if not isinstance(hero, int):
                hero_id = self.hero_name_to_id['npc_dota_hero_' + hero]
            f = lambda x: x['hero_id'] == hero_id
            # should be unique
            skills = list(filter(f, self.resp['players']))[0]['ability_upgrades']
            df = pd.DataFrame(skills)
            df['ability'] = df.ability.astype(str).map(_ability_id_to_name)
        return df


class TeamResponse(Response):

    def __init__(self, resp):
        # this probably is bad. Just ensure name on team_id
        try:
            resp['name']
            resp['team_id']
        except KeyError:
            raise ValueError("Bad response.")
        for attr in resp.keys():
            setattr(self, attr, resp[attr])

        self.player_ids = [getattr(self, x) for x in
                           ["player_0_account_id", "player_1_account_id",
                            "player_2_account_id", "player_3_account_id",
                            "player_4_account_id"]]


def update_hero_names(key):
    h = API(key)
    with open(dirname(abspath(__file__)) + 'current_heroes.json', 'w') as f:
        json.dump(h.get_heroes(), f)

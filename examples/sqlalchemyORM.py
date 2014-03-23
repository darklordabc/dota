# -*- coding: utf-8 -*-
import json
import pathlib


import pandas as pd
from sqlalchemy import (Boolean, Column, Integer, String, create_engine,
                        ForeignKey, func)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

from dota import api
from dota.helpers import cached_games

Base = declarative_base()

# association_table = Table('association', Base.metadata,
#                           Column('match_id', Integer, ForeignKey('games.match_id')),
#                           Column('player_id', Integer, ForeignKey('players.account_id'))
#                           )


class PlayerGame(Base):

    __tablename__ = 'playergames'

    match_id = Column(Integer, ForeignKey('games.match_id'), primary_key=True)
    account_id = Column(Integer, ForeignKey('players.account_id'), primary_key=True)

    hero_id = Column(Integer)
    level = Column(Integer)
    denies = Column(Integer)
    gold = Column(Integer)
    item_5 = Column(Integer)
    item_4 = Column(Integer)
    item_1 = Column(Integer)
    item_0 = Column(Integer)
    item_3 = Column(Integer)
    item_2 = Column(Integer)
    gold_spent = Column(Integer)
    deaths = Column(Integer)
    hero_damage = Column(Integer)
    assists = Column(Integer)
    gold_per_min = Column(Integer)
    hero_healing = Column(Integer)
    player_slot = Column(Integer)
    last_hits = Column(Integer)
    xp_per_min = Column(Integer)
    tower_damage = Column(Integer)
    kills = Column(Integer)
    leaver_status = Column(Integer)

    player = relationship("Player", backref="playergames")

    def __init__(self, match_id, resp):

        self.match_id = match_id
        self.account_id = resp['account_id']
        self.hero_id = resp['hero_id']
        self.level = resp['level']
        self.denies = resp['denies']
        self.gold = resp['gold']
        self.item_5 = resp['item_5']
        self.item_4 = resp['item_4']
        self.item_1 = resp['item_1']
        self.item_0 = resp['item_0']
        self.item_3 = resp['item_3']
        self.item_2 = resp['item_2']
        self.gold_spent = resp['gold_spent']
        self.deaths = resp['deaths']
        self.hero_damage = resp['hero_damage']
        self.assists = resp['assists']
        self.gold_per_min = resp['gold_per_min']
        self.hero_healing = resp['hero_healing']
        self.player_slot = resp['player_slot']
        self.last_hits = resp['last_hits']
        self.xp_per_min = resp['xp_per_min']
        self.tower_damage = resp['tower_damage']
        self.kills = resp['kills']
        self.leaver_status = resp['leaver_status']

    def __repr__(self):
        return "<Player {}>, <Game {}>".format(self.account_id, self.match_id)


class Game(Base):

    __tablename__ = 'games'

    match_id = Column(Integer, primary_key=True)
    dire_team_id = Column(Integer, ForeignKey('teams.team_id'))
    dire_team_name = Column(Integer, ForeignKey('teams.team_name'))
    radiant_team_id = Column(Integer, ForeignKey('teams.team_id'))
    radiant_team_name = Column(Integer, ForeignKey('teams.team_name'))

    start_time = Column(Integer)
    match_seq_num = Column(Integer)
    leagueid = Column(String)
    lobby_type = Column(Integer)
    game_mode = Column(Integer)
    positive_votes = Column(Integer)
    negative_votes = Column(Integer)

    radiant_win = Column(Boolean)
    duration = Column(Integer)
    first_blood_time = Column(Integer)
    tower_status_dire = Column(Integer)
    tower_status_radiant = Column(Integer)
    barracks_status_radiant = Column(Integer)
    barracks_status_dire = Column(Integer)
    human_players = Column(Integer)

    players = relationship("PlayerGame", backref="games")

    def __init__(self, resp):
        self.match_id = resp['match_id']
        self.dire_team_id = resp.get('dire_team_id')
        self.radiant_team_id = resp.get('radiant_team_id')

        self.start_time = resp['start_time']
        self.match_seq_num = resp['match_seq_num']
        self.leagueid = resp['leagueid']
        self.lobby_type = resp['lobby_type']
        self.game_mode = resp['game_mode']
        self.positive_votes = resp['positive_votes']
        self.negative_votes = resp['negative_votes']
        self.radiant_win = resp['radiant_win']
        self.duration = resp['duration']
        self.first_blood_time = resp['first_blood_time']
        self.tower_status_dire = resp['tower_status_dire']
        self.tower_status_radiant = resp['tower_status_radiant']
        self.barracks_status_radiant = resp['barracks_status_radiant']
        self.barracks_status_dire = resp['barracks_status_dire']
        self.human_players = resp['human_players']

    def __repr__(self):
        return "<Game {}>".format(self.match_id)


class Player(Base):

    __tablename__ = 'players'

    account_id = Column(Integer, primary_key=True)
    handle = Column(String)

    def __repr__(self):
        return "<Player {}>. {}".format(self.account_id, self.handle)


class Team(Base):
    # TODO: relate players to teams, and back
    __tablename__ = 'teams'

    team_id = Column(Integer, primary_key=True)
    team_name = Column(String)

    def __init__(self, resp, side='radiant'):

        self.team_id = resp.get(side + '_' + 'team_id')
        self.team_name = resp.get(side + '_' + 'name')

    def __repr__(self):
        return "<Team {}>. {}".format(self.team_id, self.team_name)


def make_engine(filepath='sqlite:///pro.db'):

    engine = create_engine(filepath)
    Base.metadata.create_all(engine)
    return engine


def add_to_db(engine, games):
    """
    engine : sqlalchemy engine
    games : List of Paths
    """
    Session = sessionmaker(bind=engine)
    session = Session()

    gs = []
    for g in games:

        with g.open() as f:
            d = api.DetailsResponse(json.load(f))

        game = Game(d.resp)
        gs.append(game)
        pgs = []
        pls = []

        for side in ['radiant', 'dire']:
            team = Team(d.resp, side=side)
            if team.team_id is None:
                continue
            existing_team = session.query(Team).filter(
                Team.team_id == team.team_id).first()
            if existing_team is None:
                session.add(team)

        for player in d.resp['players']:
            pg = PlayerGame(d.match_id, player)
            if pd.isnull(pg.account_id):
                continue

            pl = Player(account_id=pg.account_id)
            existing_player = session.query(Player).filter(
                Player.account_id == pl.account_id).first()
            if existing_player is None:
                session.add(pl)

            # pls.append(pl)
            pgs.append(pg)

        session.add_all(pgs)
        session.add_all(pls)
    session.add_all(gs)
    session.commit()
    return session


def main():

    p = pathlib.Path('../data/pro/')
    games = filter(lambda x: x.suffix == '.json', p.iterdir())

    engine = make_engine()
    session = add_to_db(engine, games)
    return engine, session


def update_db(data_path):
    """
    Create an engine and session, query for existing game ids.
    Add new files in data dir to.


    Parameters
    ----------
    data_path : Path
        path to the pro match directory. Engine is at data_path / pro.db
    """
    engine = make_engine("sqlite:///" + str(data_path / "pro.db"))

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        sql_games = set(list(zip(*session.query(Game.match_id).all()))[0])
    except IndexError:  # new db
        sql_games = set()
    cached = cached_games(data_path.resolve())  # JSON files on disk
    new_games = set(cached) - sql_games
    new_games = (data_path / pathlib.Path(str(game) + '.json') for game in new_games)

    session = add_to_db(engine, new_games)
    return engine, session

#-----------------------------------------------------------------------------
# Cookbookish stuff


def count_player_games(session):
    count = session.query(func.count(PlayerGame.account_id), PlayerGame.account_id).\
        group_by(PlayerGame.account_id).\
        order_by(func.count(PlayerGame.account_id)).all()
    return count

if __name__ == '__main__':

    main()

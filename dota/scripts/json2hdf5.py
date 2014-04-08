# -*- coding: utf-8 -*-
"""
Given a data directory, convert all details responses to HDF5Store.
"""

import os
import json
from pathlib import Path
import argparse

import numpy as np
import pandas as pd

from dota import api
from dota.helpers import cached_games

parser = argparse.ArgumentParser("Convert JSON DetailsResponses to HDF5.")
parser.add_argument("--data_dir", type=str, help="Path to data direcotry.",
                    default='~/sandbox/dota/data/pro/')
parser.add_argument("--hdf_store", type=str, help="Path to the HDF Store",
                    default='~/sandbox/dota/data/pro/pro.h5')


def add_by_side(df, dr, item, side):
    """
    Modifies df in place.
    """
    st = side.title()
    sl = side.lower()

    vals = getattr(dr, item)
    if callable(vals):
        vals = vals()
    if isinstance(vals, dict):
        vals = vals.get(sl, np.nan)

    df.loc[(df.team == st), item] = vals


def append_to_store(store, dfs, key='drs'):
    dfs = pd.concat(dfs, ignore_index=True)
    dfs = dfs.convert_objects(convert_numeric=True)

    # will be float if any NaN. Some won't have
    # NaNs so need to recast
    cols = ['radiant_team_id', 'dire_team_id', 'account_id']
    dfs[cols] = dfs[cols].astype(np.float64)

    dfs.to_hdf(str(store), key=key, append=True,
               min_itemsize={'dire_name': 60, 'radiant_name': 60})


def main():

    args = parser.parse_args()
    store = os.path.expanduser(args.hdf_store)
    data_dir = Path(os.path.expanduser(args.data_dir))

    cached = cached_games(data_dir)

    # first time. Generate the store
    if not os.path.isfile(store):
        pd.HDFStore(store)

    with pd.get_store(store) as s:

        try:
            stored = s.select('drs')['match_id']
        except KeyError:
            stored = []

    new_games = filter(lambda x: x.stem not in stored, cached)

    dfs = []
    for i, game in enumerate(new_games, 1):
        dr = api.DetailsResponse.from_json(str(game))
        mr = dr.match_report().reset_index()

        for item in ['barracks_status', 'tower_status']:
            for side in ['Radiant', 'Dire']:
                add_by_side(mr, dr, item, side)

        for item in ['dire_name', 'radiant_name', 'dire_team_id',
                     'radiant_team_id']:
            mr[item] = getattr(dr, item, np.nan)
        mr['duration'] = dr.duration
        mr['game_mod'] = dr.game_mode
        mr['start_time'] = pd.to_datetime(dr.start_time.isoformat())
        # if (i % 100) != 0:
        dfs.append(mr)
        # else:
        #     # flush
        #     append_to_store(store, dfs)
        #     dfs = []
    else:
        append_to_store(store, dfs)

if __name__ == '__main__':
    main()

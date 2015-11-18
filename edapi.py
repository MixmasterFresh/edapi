#!/usr/bin/env python
# ----------------------------------------------------------------
# Elite: Dangerous API Tool
# ----------------------------------------------------------------

import argparse
import getpass
import json
import os
from pathlib import Path
import platform
import pickle
from pprint import pprint
import requests
from requests.utils import dict_from_cookiejar
from requests.utils import cookiejar_from_dict
import sys
import tempfile
import textwrap
import time
import traceback

import eddn

__version_info__ = ('3', '5', '8')
__version__ = '.'.join(__version_info__)

# ----------------------------------------------------------------
# Deal with some differences in names between TD, ED and the API.
# ----------------------------------------------------------------

# Categories to ignore. Drones end up here. No idea what they are.
cat_ignore = [
    'NonMarketable',
]

# TD has different names for these.
cat_correct = {
    'Narcotics': 'Legal Drugs',
    'Slaves': 'Slavery',
}

# Commodities to ignore. Don't try to pass these to TD. This is mostly for
# rares.
comm_ignore = (
    'Alien Eggs',
    'Lavian Brandy',
)

# TD has different names for these.
comm_correct = {
    'Agricultural Medicines': 'Agri-Medicines',
    'Atmospheric Extractors': 'Atmospheric Processors',
    'Auto Fabricators': 'Auto-Fabricators',
    'Basic Narcotics': 'Narcotics',
    'Bio Reducing Lichen': 'Bioreducing Lichen',
    'Hafnium178': 'Hafnium 178',
    'Hazardous Environment Suits': 'H.E. Suits',
    'Heliostatic Furnaces': 'Microbial Furnaces',
    'Marine Supplies': 'Marine Equipment',
    'Non Lethal Weapons': 'Non-Lethal Weapons',
    'S A P8 Core Container': 'SAP 8 Core Container',
    'Terrain Enrichment Systems': 'Land Enrichment Systems',
    'U S S Cargo Ancient Artefact': 'Ancient Artefact',
    'U S S Cargo Experimental Chemicals': 'Experimental Chemicals',
    'U S S Cargo Military Plans': 'Military Plans',
    'U S S Cargo Prototype Tech': 'Prototype Tech',
    'U S S Cargo Rebel Transmissions': 'Rebel Transmissions',
    'U S S Cargo Technical Blueprints': 'Technical Blueprints',
    'U S S Cargo Trade Data': 'Trade Data',
}

# ----------------------------------------------------------------
# Some lookup tables.
# ----------------------------------------------------------------

bracket_levels = ('-', 'L', 'M', 'H')

# This translates what the API calls a ship into what TD calls a
# ship.

ship_names = {
    'Adder': 'Adder',
    'Anaconda': 'Anaconda',
    'Asp': 'Asp',
    'CobraMkIII': 'Cobra',
    'DiamondBack': 'Diamondback Scout',
    'DiamondBackXL': 'Diamondback Explorer',
    'Eagle': 'Eagle',
    'Empire_Courier': 'Imperial Courier',
    'Empire_Eagle': 'Imperial Eagle',
    'Empire_Fighter': 'Empire_Fighter',
    'Empire_Trader': 'Clipper',
    'Federation_Dropship': 'Dropship',
    'Federation_Dropship_MkII': 'Federal Assault Ship',
    'Federation_Fighter': 'Federation_Fighter',
    'Federation_Gunship': 'Federal Gunship',
    'FerDeLance': 'Fer-de-Lance',
    'Hauler': 'Hauler',
    'Orca': 'Orca',
    'Python': 'Python',
    'SideWinder': 'Sidewinder',
    'Type6': 'Type 6',
    'Type7': 'Type 7',
    'Type9': 'Type 9',
    'Viper': 'Viper',
    'Vulture': 'Vulture',
}

eddn_ship_names = {
    'Adder': 'Adder',
    'Anaconda': 'Anaconda',
    'Asp': 'Asp',
    'CobraMkIII': 'Cobra Mk III',
    'DiamondBack': 'DiamondBack Scout',
    'DiamondBackXL': 'DiamondBack Explorer',
    'Eagle': 'Eagle',
    'Empire_Courier': 'Imperial Courier',
    'Empire_Eagle': 'Imperial Eagle',
    'Empire_Fighter': 'Empire_Fighter',
    'Empire_Trader': 'Imperial Clipper',
    'Federation_Dropship': 'Federal Dropship',
    'Federation_Dropship_MkII': 'Federal Assault Ship',
    'Federation_Fighter': 'Federation_Fighter',
    'Federation_Gunship': 'Federal Gunship',
    'FerDeLance': 'Fer-de-Lance',
    'Hauler': 'Hauler',
    'Orca': 'Orca',
    'Python': 'Python',
    'SideWinder': 'Sidewinder',
    'Type6': 'Type-6 Transporter',
    'Type7': 'Type-7 Transporter',
    'Type9': 'Type-9 Heavy',
    'Viper': 'Viper',
    'Vulture': 'Vulture',
}

rank_names = {
    'combat': (
        'Harmless',
        'Mostly Harmless',
        'Novice',
        'Competent',
        'Expert',
        'Master',
        'Dangerous',
        'Deadly',
        'Elite',
    ),
    'crime': (
        'Rank 0',
    ),
    'empire': (
        'None',
        'Outsider',
        'Serf',
        'Master',
        'Squire',
        'Knight',
        'Lord',
        'Baron',
        'Viscount',
        'Count',
        'Earl',
        'Marquis',
        'Duke',
        'Prince',
        'King',
    ),
    'explore': (
        'Aimless',
        'Mostly Aimless',
        'Scout',
        'Surveyor',
        'Trailblazer',
        'Pathfinder',
        'Ranger',
        'Starblazer',
        'Elite',
    ),
    'federation': (
        'None',
        'Recruit',
        'Cadet',
        'Midshipman',
        'Petty Officer',
        'Chief Petty Officer',
        'Warrant Officer',
        'Ensign',
        'Lieutenant',
        'Lieutenant Commander',
        'Post Commander',
        'Post Captain',
        'Rear Admiral',
        'Vice Admiral',
        'Admiral',
    ),
    'service': (
        'Rank 0',
    ),
    'trade': (
        'Penniless',
        'Mostly Penniless',
        'Pedlar',
        'Dealer',
        'Merchant',
        'Broker',
        'Entrepreneur',
        'Tycoon',
        'Elite',
    ),
}

modules = {
 128049250: {'category': 'standard',
             'class': '1',
             'name': 'Lightweight Alloy',
             'rating': 'I',
             'ship': 'Sidewinder'},
 128049251: {'category': 'standard',
             'class': '1',
             'name': 'Reinforced Alloy',
             'rating': 'I',
             'ship': 'Sidewinder'},
 128049252: {'category': 'standard',
             'class': '1',
             'name': 'Military Grade Composite',
             'rating': 'I',
             'ship': 'Sidewinder'},
 128049253: {'category': 'standard',
             'class': '1',
             'name': 'Mirrored Surface Composite',
             'rating': 'I',
             'ship': 'Sidewinder'},
 128049254: {'category': 'standard',
             'class': '1',
             'name': 'Reactive Surface Composite',
             'rating': 'I',
             'ship': 'Sidewinder'},
 128049256: {'category': 'standard',
             'class': '1',
             'name': 'Lightweight Alloy',
             'rating': 'I',
             'ship': 'Eagle'},
 128049257: {'category': 'standard',
             'class': '1',
             'name': 'Reinforced Alloy',
             'rating': 'I',
             'ship': 'Eagle'},
 128049258: {'category': 'standard',
             'class': '1',
             'name': 'Military Grade Composite',
             'rating': 'I',
             'ship': 'Eagle'},
 128049259: {'category': 'standard',
             'class': '1',
             'name': 'Mirrored Surface Composite',
             'rating': 'I',
             'ship': 'Eagle'},
 128049260: {'category': 'standard',
             'class': '1',
             'name': 'Reactive Surface Composite',
             'rating': 'I',
             'ship': 'Eagle'},
 128049262: {'category': 'standard',
             'class': '1',
             'name': 'Lightweight Alloy',
             'rating': 'I',
             'ship': 'Hauler'},
 128049263: {'category': 'standard',
             'class': '1',
             'name': 'Reinforced Alloy',
             'rating': 'I',
             'ship': 'Hauler'},
 128049264: {'category': 'standard',
             'class': '1',
             'name': 'Military Grade Composite',
             'rating': 'I',
             'ship': 'Hauler'},
 128049265: {'category': 'standard',
             'class': '1',
             'name': 'Mirrored Surface Composite',
             'rating': 'I',
             'ship': 'Hauler'},
 128049266: {'category': 'standard',
             'class': '1',
             'name': 'Reactive Surface Composite',
             'rating': 'I',
             'ship': 'Hauler'},
 128049268: {'category': 'standard',
             'class': '1',
             'name': 'Lightweight Alloy',
             'rating': 'I',
             'ship': 'Adder'},
 128049269: {'category': 'standard',
             'class': '1',
             'name': 'Reinforced Alloy',
             'rating': 'I',
             'ship': 'Adder'},
 128049270: {'category': 'standard',
             'class': '1',
             'name': 'Military Grade Composite',
             'rating': 'I',
             'ship': 'Adder'},
 128049271: {'category': 'standard',
             'class': '1',
             'name': 'Mirrored Surface Composite',
             'rating': 'I',
             'ship': 'Adder'},
 128049272: {'category': 'standard',
             'class': '1',
             'name': 'Reactive Surface Composite',
             'rating': 'I',
             'ship': 'Adder'},
 128049274: {'category': 'standard',
             'class': '1',
             'name': 'Lightweight Alloy',
             'rating': 'I',
             'ship': 'Viper'},
 128049275: {'category': 'standard',
             'class': '1',
             'name': 'Reinforced Alloy',
             'rating': 'I',
             'ship': 'Viper'},
 128049276: {'category': 'standard',
             'class': '1',
             'name': 'Military Grade Composite',
             'rating': 'I',
             'ship': 'Viper'},
 128049277: {'category': 'standard',
             'class': '1',
             'name': 'Mirrored Surface Composite',
             'rating': 'I',
             'ship': 'Viper'},
 128049278: {'category': 'standard',
             'class': '1',
             'name': 'Reactive Surface Composite',
             'rating': 'I',
             'ship': 'Viper'},
 128049280: {'category': 'standard',
             'class': '1',
             'name': 'Lightweight Alloy',
             'rating': 'I',
             'ship': 'Cobra Mk III'},
 128049281: {'category': 'standard',
             'class': '1',
             'name': 'Reinforced Alloy',
             'rating': 'I',
             'ship': 'Cobra Mk III'},
 128049282: {'category': 'standard',
             'class': '1',
             'name': 'Military Grade Composite',
             'rating': 'I',
             'ship': 'Cobra Mk III'},
 128049283: {'category': 'standard',
             'class': '1',
             'name': 'Mirrored Surface Composite',
             'rating': 'I',
             'ship': 'Cobra Mk III'},
 128049284: {'category': 'standard',
             'class': '1',
             'name': 'Reactive Surface Composite',
             'rating': 'I',
             'ship': 'Cobra Mk III'},
 128049286: {'category': 'standard',
             'class': '1',
             'name': 'Lightweight Alloy',
             'rating': 'I',
             'ship': 'Type-6 Transporter'},
 128049287: {'category': 'standard',
             'class': '1',
             'name': 'Reinforced Alloy',
             'rating': 'I',
             'ship': 'Type-6 Transporter'},
 128049288: {'category': 'standard',
             'class': '1',
             'name': 'Military Grade Composite',
             'rating': 'I',
             'ship': 'Type-6 Transporter'},
 128049289: {'category': 'standard',
             'class': '1',
             'name': 'Mirrored Surface Composite',
             'rating': 'I',
             'ship': 'Type-6 Transporter'},
 128049290: {'category': 'standard',
             'class': '1',
             'name': 'Reactive Surface Composite',
             'rating': 'I',
             'ship': 'Type-6 Transporter'},
 128049298: {'category': 'standard',
             'class': '1',
             'name': 'Lightweight Alloy',
             'rating': 'I',
             'ship': 'Type-7 Transporter'},
 128049299: {'category': 'standard',
             'class': '1',
             'name': 'Reinforced Alloy',
             'rating': 'I',
             'ship': 'Type-7 Transporter'},
 128049300: {'category': 'standard',
             'class': '1',
             'name': 'Military Grade Composite',
             'rating': 'I',
             'ship': 'Type-7 Transporter'},
 128049301: {'category': 'standard',
             'class': '1',
             'name': 'Mirrored Surface Composite',
             'rating': 'I',
             'ship': 'Type-7 Transporter'},
 128049302: {'category': 'standard',
             'class': '1',
             'name': 'Reactive Surface Composite',
             'rating': 'I',
             'ship': 'Type-7 Transporter'},
 128049304: {'category': 'standard',
             'class': '1',
             'name': 'Lightweight Alloy',
             'rating': 'I',
             'ship': 'Asp'},
 128049305: {'category': 'standard',
             'class': '1',
             'name': 'Reinforced Alloy',
             'rating': 'I',
             'ship': 'Asp'},
 128049306: {'category': 'standard',
             'class': '1',
             'name': 'Military Grade Composite',
             'rating': 'I',
             'ship': 'Asp'},
 128049307: {'category': 'standard',
             'class': '1',
             'name': 'Mirrored Surface Composite',
             'rating': 'I',
             'ship': 'Asp'},
 128049308: {'category': 'standard',
             'class': '1',
             'name': 'Reactive Surface Composite',
             'rating': 'I',
             'ship': 'Asp'},
 128049310: {'category': 'standard',
             'class': '1',
             'name': 'Lightweight Alloy',
             'rating': 'I',
             'ship': 'Vulture'},
 128049311: {'category': 'standard',
             'class': '1',
             'name': 'Reinforced Alloy',
             'rating': 'I',
             'ship': 'Vulture'},
 128049312: {'category': 'standard',
             'class': '1',
             'name': 'Military Grade Composite',
             'rating': 'I',
             'ship': 'Vulture'},
 128049313: {'category': 'standard',
             'class': '1',
             'name': 'Mirrored Surface Composite',
             'rating': 'I',
             'ship': 'Vulture'},
 128049314: {'category': 'standard',
             'class': '1',
             'name': 'Reactive Surface Composite',
             'rating': 'I',
             'ship': 'Vulture'},
 128049316: {'category': 'standard',
             'class': '1',
             'name': 'Lightweight Alloy',
             'rating': 'I',
             'ship': 'Imperial Clipper'},
 128049317: {'category': 'standard',
             'class': '1',
             'name': 'Reinforced Alloy',
             'rating': 'I',
             'ship': 'Imperial Clipper'},
 128049318: {'category': 'standard',
             'class': '1',
             'name': 'Military Grade Composite',
             'rating': 'I',
             'ship': 'Imperial Clipper'},
 128049319: {'category': 'standard',
             'class': '1',
             'name': 'Mirrored Surface Composite',
             'rating': 'I',
             'ship': 'Imperial Clipper'},
 128049320: {'category': 'standard',
             'class': '1',
             'name': 'Reactive Surface Composite',
             'rating': 'I',
             'ship': 'Imperial Clipper'},
 128049322: {'category': 'standard',
             'class': '1',
             'name': 'Lightweight Alloy',
             'rating': 'I',
             'ship': 'Federal Dropship'},
 128049323: {'category': 'standard',
             'class': '1',
             'name': 'Reinforced Alloy',
             'rating': 'I',
             'ship': 'Federal Dropship'},
 128049324: {'category': 'standard',
             'class': '1',
             'name': 'Military Grade Composite',
             'rating': 'I',
             'ship': 'Federal Dropship'},
 128049325: {'category': 'standard',
             'class': '1',
             'name': 'Mirrored Surface Composite',
             'rating': 'I',
             'ship': 'Federal Dropship'},
 128049326: {'category': 'standard',
             'class': '1',
             'name': 'Reactive Surface Composite',
             'rating': 'I',
             'ship': 'Federal Dropship'},
 128049328: {'category': 'standard',
             'class': '1',
             'name': 'Lightweight Alloy',
             'rating': 'I',
             'ship': 'Orca'},
 128049329: {'category': 'standard',
             'class': '1',
             'name': 'Reinforced Alloy',
             'rating': 'I',
             'ship': 'Orca'},
 128049330: {'category': 'standard',
             'class': '1',
             'name': 'Military Grade Composite',
             'rating': 'I',
             'ship': 'Orca'},
 128049331: {'category': 'standard',
             'class': '1',
             'name': 'Mirrored Surface Composite',
             'rating': 'I',
             'ship': 'Orca'},
 128049332: {'category': 'standard',
             'class': '1',
             'name': 'Reactive Surface Composite',
             'rating': 'I',
             'ship': 'Orca'},
 128049334: {'category': 'standard',
             'class': '1',
             'name': 'Lightweight Alloy',
             'rating': 'I',
             'ship': 'Type-9 Heavy'},
 128049335: {'category': 'standard',
             'class': '1',
             'name': 'Reinforced Alloy',
             'rating': 'I',
             'ship': 'Type-9 Heavy'},
 128049336: {'category': 'standard',
             'class': '1',
             'name': 'Military Grade Composite',
             'rating': 'I',
             'ship': 'Type-9 Heavy'},
 128049337: {'category': 'standard',
             'class': '1',
             'name': 'Mirrored Surface Composite',
             'rating': 'I',
             'ship': 'Type-9 Heavy'},
 128049338: {'category': 'standard',
             'class': '1',
             'name': 'Reactive Surface Composite',
             'rating': 'I',
             'ship': 'Type-9 Heavy'},
 128049340: {'category': 'standard',
             'class': '1',
             'name': 'Lightweight Alloy',
             'rating': 'I',
             'ship': 'Python'},
 128049341: {'category': 'standard',
             'class': '1',
             'name': 'Reinforced Alloy',
             'rating': 'I',
             'ship': 'Python'},
 128049342: {'category': 'standard',
             'class': '1',
             'name': 'Military Grade Composite',
             'rating': 'I',
             'ship': 'Python'},
 128049343: {'category': 'standard',
             'class': '1',
             'name': 'Mirrored Surface Composite',
             'rating': 'I',
             'ship': 'Python'},
 128049344: {'category': 'standard',
             'class': '1',
             'name': 'Reactive Surface Composite',
             'rating': 'I',
             'ship': 'Python'},
 128049352: {'category': 'standard',
             'class': '1',
             'name': 'Lightweight Alloy',
             'rating': 'I',
             'ship': 'Fer-de-Lance'},
 128049353: {'category': 'standard',
             'class': '1',
             'name': 'Reinforced Alloy',
             'rating': 'I',
             'ship': 'Fer-de-Lance'},
 128049354: {'category': 'standard',
             'class': '1',
             'name': 'Military Grade Composite',
             'rating': 'I',
             'ship': 'Fer-de-Lance'},
 128049355: {'category': 'standard',
             'class': '1',
             'name': 'Mirrored Surface Composite',
             'rating': 'I',
             'ship': 'Fer-de-Lance'},
 128049356: {'category': 'standard',
             'class': '1',
             'name': 'Reactive Surface Composite',
             'rating': 'I',
             'ship': 'Fer-de-Lance'},
 128049364: {'category': 'standard',
             'class': '1',
             'name': 'Lightweight Alloy',
             'rating': 'I',
             'ship': 'Anaconda'},
 128049365: {'category': 'standard',
             'class': '1',
             'name': 'Reinforced Alloy',
             'rating': 'I',
             'ship': 'Anaconda'},
 128049366: {'category': 'standard',
             'class': '1',
             'name': 'Military Grade Composite',
             'rating': 'I',
             'ship': 'Anaconda'},
 128049367: {'category': 'standard',
             'class': '1',
             'name': 'Mirrored Surface Composite',
             'rating': 'I',
             'ship': 'Anaconda'},
 128049368: {'category': 'standard',
             'class': '1',
             'name': 'Reactive Surface Composite',
             'rating': 'I',
             'ship': 'Anaconda'},
 128049381: {'category': 'hardpoint',
             'class': '1',
             'mount': 'Fixed',
             'name': 'Pulse Laser',
             'rating': 'F'},
 128049382: {'category': 'hardpoint',
             'class': '2',
             'mount': 'Fixed',
             'name': 'Pulse Laser',
             'rating': 'E'},
 128049383: {'category': 'hardpoint',
             'class': '3',
             'mount': 'Fixed',
             'name': 'Pulse Laser',
             'rating': 'D'},
 128049385: {'category': 'hardpoint',
             'class': '1',
             'mount': 'Gimballed',
             'name': 'Pulse Laser',
             'rating': 'G'},
 128049386: {'category': 'hardpoint',
             'class': '2',
             'mount': 'Gimballed',
             'name': 'Pulse Laser',
             'rating': 'F'},
 128049387: {'category': 'hardpoint',
             'class': '3',
             'mount': 'Gimballed',
             'name': 'Pulse Laser',
             'rating': 'E'},
 128049388: {'category': 'hardpoint',
             'class': '1',
             'mount': 'Turreted',
             'name': 'Pulse Laser',
             'rating': 'G'},
 128049389: {'category': 'hardpoint',
             'class': '2',
             'mount': 'Turreted',
             'name': 'Pulse Laser',
             'rating': 'F'},
 128049390: {'category': 'hardpoint',
             'class': '3',
             'mount': 'Turreted',
             'name': 'Pulse Laser',
             'rating': 'F'},
 128049400: {'category': 'hardpoint',
             'class': '1',
             'mount': 'Fixed',
             'name': 'Burst Laser',
             'rating': 'F'},
 128049401: {'category': 'hardpoint',
             'class': '2',
             'mount': 'Fixed',
             'name': 'Burst Laser',
             'rating': 'E'},
 128049402: {'category': 'hardpoint',
             'class': '3',
             'mount': 'Fixed',
             'name': 'Burst Laser',
             'rating': 'D'},
 128049404: {'category': 'hardpoint',
             'class': '1',
             'mount': 'Gimballed',
             'name': 'Burst Laser',
             'rating': 'G'},
 128049405: {'category': 'hardpoint',
             'class': '2',
             'mount': 'Gimballed',
             'name': 'Burst Laser',
             'rating': 'F'},
 128049406: {'category': 'hardpoint',
             'class': '3',
             'mount': 'Gimballed',
             'name': 'Burst Laser',
             'rating': 'E'},
 128049407: {'category': 'hardpoint',
             'class': '1',
             'mount': 'Turreted',
             'name': 'Burst Laser',
             'rating': 'G'},
 128049408: {'category': 'hardpoint',
             'class': '2',
             'mount': 'Turreted',
             'name': 'Burst Laser',
             'rating': 'F'},
 128049409: {'category': 'hardpoint',
             'class': '3',
             'mount': 'Turreted',
             'name': 'Burst Laser',
             'rating': 'E'},
 128049428: {'category': 'hardpoint',
             'class': '1',
             'mount': 'Fixed',
             'name': 'Beam Laser',
             'rating': 'E'},
 128049429: {'category': 'hardpoint',
             'class': '2',
             'mount': 'Fixed',
             'name': 'Beam Laser',
             'rating': 'D'},
 128049430: {'category': 'hardpoint',
             'class': '3',
             'mount': 'Fixed',
             'name': 'Beam Laser',
             'rating': 'C'},
 128049432: {'category': 'hardpoint',
             'class': '1',
             'mount': 'Gimballed',
             'name': 'Beam Laser',
             'rating': 'E'},
 128049433: {'category': 'hardpoint',
             'class': '2',
             'mount': 'Gimballed',
             'name': 'Beam Laser',
             'rating': 'D'},
 128049434: {'category': 'hardpoint',
             'class': '3',
             'mount': 'Gimballed',
             'name': 'Beam Laser',
             'rating': 'C'},
 128049435: {'category': 'hardpoint',
             'class': '1',
             'mount': 'Turreted',
             'name': 'Beam Laser',
             'rating': 'F'},
 128049436: {'category': 'hardpoint',
             'class': '2',
             'mount': 'Turreted',
             'name': 'Beam Laser',
             'rating': 'E'},
 128049437: {'category': 'hardpoint',
             'class': '3',
             'mount': 'Turreted',
             'name': 'Beam Laser',
             'rating': 'D'},
 128049438: {'category': 'hardpoint',
             'class': '1',
             'mount': 'Fixed',
             'name': 'Cannon',
             'rating': 'D'},
 128049439: {'category': 'hardpoint',
             'class': '2',
             'mount': 'Fixed',
             'name': 'Cannon',
             'rating': 'D'},
 128049440: {'category': 'hardpoint',
             'class': '3',
             'mount': 'Fixed',
             'name': 'Cannon',
             'rating': 'C'},
 128049441: {'category': 'hardpoint',
             'class': '4',
             'mount': 'Fixed',
             'name': 'Cannon',
             'rating': 'B'},
 128049442: {'category': 'hardpoint',
             'class': '1',
             'mount': 'Gimballed',
             'name': 'Cannon',
             'rating': 'E'},
 128049443: {'category': 'hardpoint',
             'class': '2',
             'mount': 'Gimballed',
             'name': 'Cannon',
             'rating': 'D'},
 128049444: {'category': 'hardpoint',
             'class': '4',
             'mount': 'Gimballed',
             'name': 'Cannon',
             'rating': 'B'},
 128049445: {'category': 'hardpoint',
             'class': '1',
             'mount': 'Turreted',
             'name': 'Cannon',
             'rating': 'F'},
 128049446: {'category': 'hardpoint',
             'class': '2',
             'mount': 'Turreted',
             'name': 'Cannon',
             'rating': 'E'},
 128049447: {'category': 'hardpoint',
             'class': '3',
             'mount': 'Turreted',
             'name': 'Cannon',
             'rating': 'D'},
 128049448: {'category': 'hardpoint',
             'class': '1',
             'mount': 'Fixed',
             'name': 'Fragment Cannon',
             'rating': 'E'},
 128049449: {'category': 'hardpoint',
             'class': '2',
             'mount': 'Fixed',
             'name': 'Fragment Cannon',
             'rating': 'A'},
 128049450: {'category': 'hardpoint',
             'class': '3',
             'mount': 'Fixed',
             'name': 'Fragment Cannon',
             'rating': 'C'},
 128049451: {'category': 'hardpoint',
             'class': '1',
             'mount': 'Gimballed',
             'name': 'Fragment Cannon',
             'rating': 'E'},
 128049452: {'category': 'hardpoint',
             'class': '2',
             'mount': 'Gimballed',
             'name': 'Fragment Cannon',
             'rating': 'D'},
 128049453: {'category': 'hardpoint',
             'class': '1',
             'mount': 'Turreted',
             'name': 'Fragment Cannon',
             'rating': 'E'},
 128049454: {'category': 'hardpoint',
             'class': '2',
             'mount': 'Turreted',
             'name': 'Fragment Cannon',
             'rating': 'D'},
 128049455: {'category': 'hardpoint',
             'class': '1',
             'mount': 'Fixed',
             'name': 'Multi-Cannon',
             'rating': 'F'},
 128049456: {'category': 'hardpoint',
             'class': '2',
             'mount': 'Fixed',
             'name': 'Multi-Cannon',
             'rating': 'E'},
 128049459: {'category': 'hardpoint',
             'class': '1',
             'mount': 'Gimballed',
             'name': 'Multi-Cannon',
             'rating': 'G'},
 128049460: {'category': 'hardpoint',
             'class': '2',
             'mount': 'Gimballed',
             'name': 'Multi-Cannon',
             'rating': 'F'},
 128049462: {'category': 'hardpoint',
             'class': '1',
             'mount': 'Turreted',
             'name': 'Multi-Cannon',
             'rating': 'G'},
 128049463: {'category': 'hardpoint',
             'class': '2',
             'mount': 'Turreted',
             'name': 'Multi-Cannon',
             'rating': 'F'},
 128049465: {'category': 'hardpoint',
             'class': '2',
             'mount': 'Fixed',
             'name': 'Plasma Accelerator',
             'rating': 'C'},
 128049466: {'category': 'hardpoint',
             'class': '3',
             'mount': 'Fixed',
             'name': 'Plasma Accelerator',
             'rating': 'B'},
 128049467: {'category': 'hardpoint',
             'class': '4',
             'mount': 'Fixed',
             'name': 'Plasma Accelerator',
             'rating': 'A'},
 128049488: {'category': 'hardpoint',
             'class': '1',
             'mount': 'Fixed',
             'name': 'Rail Gun',
             'rating': 'D'},
 128049489: {'category': 'hardpoint',
             'class': '2',
             'mount': 'Fixed',
             'name': 'Rail Gun',
             'rating': 'B'},
 128049492: {'category': 'hardpoint',
             'class': '1',
             'guidance': 'Seeker',
             'mount': 'Fixed',
             'name': 'Missile Rack',
             'rating': 'B'},
 128049493: {'category': 'hardpoint',
             'class': '2',
             'guidance': 'Seeker',
             'mount': 'Fixed',
             'name': 'Missile Rack',
             'rating': 'B'},
 128049500: {'category': 'hardpoint',
             'class': '1',
             'mount': 'Fixed',
             'name': 'Mine Launcher',
             'rating': 'I'},
 128049501: {'category': 'hardpoint',
             'class': '2',
             'mount': 'Fixed',
             'name': 'Mine Launcher',
             'rating': 'I'},
 128049509: {'category': 'hardpoint',
             'class': '1',
             'guidance': 'Seeker',
             'mount': 'Fixed',
             'name': 'Torpedo Pylon',
             'rating': 'I'},
 128049510: {'category': 'hardpoint',
             'class': '2',
             'guidance': 'Seeker',
             'mount': 'Fixed',
             'name': 'Torpedo Pylon',
             'rating': 'I'},
 128049513: {'category': 'utility',
             'class': '0',
             'name': 'Chaff Launcher',
             'rating': 'I'},
 128049516: {'category': 'utility',
             'class': '0',
             'name': 'Electronic Countermeasure',
             'rating': 'F'},
 128049519: {'category': 'utility',
             'class': '0',
             'name': 'Heat Sink Launcher',
             'rating': 'I'},
 128049522: {'category': 'utility',
             'class': '0',
             'name': 'Point Defence',
             'rating': 'I'},
 128049525: {'category': 'hardpoint',
             'class': '1',
             'mount': 'Fixed',
             'name': 'Mining Laser',
             'rating': 'D'},
 128049526: {'category': 'hardpoint',
             'class': '2',
             'mount': 'Fixed',
             'name': 'Mining Laser',
             'rating': 'D'},
 128049549: {'category': 'internal',
             'class': '1',
             'name': 'Standard Docking Computer',
             'rating': 'E'},
 128064033: {'category': 'standard',
             'class': '2',
             'name': 'Power Plant',
             'rating': 'E'},
 128064034: {'category': 'standard',
             'class': '2',
             'name': 'Power Plant',
             'rating': 'D'},
 128064035: {'category': 'standard',
             'class': '2',
             'name': 'Power Plant',
             'rating': 'C'},
 128064036: {'category': 'standard',
             'class': '2',
             'name': 'Power Plant',
             'rating': 'B'},
 128064037: {'category': 'standard',
             'class': '2',
             'name': 'Power Plant',
             'rating': 'A'},
 128064038: {'category': 'standard',
             'class': '3',
             'name': 'Power Plant',
             'rating': 'E'},
 128064039: {'category': 'standard',
             'class': '3',
             'name': 'Power Plant',
             'rating': 'D'},
 128064040: {'category': 'standard',
             'class': '3',
             'name': 'Power Plant',
             'rating': 'C'},
 128064041: {'category': 'standard',
             'class': '3',
             'name': 'Power Plant',
             'rating': 'B'},
 128064042: {'category': 'standard',
             'class': '3',
             'name': 'Power Plant',
             'rating': 'A'},
 128064043: {'category': 'standard',
             'class': '4',
             'name': 'Power Plant',
             'rating': 'E'},
 128064044: {'category': 'standard',
             'class': '4',
             'name': 'Power Plant',
             'rating': 'D'},
 128064045: {'category': 'standard',
             'class': '4',
             'name': 'Power Plant',
             'rating': 'C'},
 128064046: {'category': 'standard',
             'class': '4',
             'name': 'Power Plant',
             'rating': 'B'},
 128064047: {'category': 'standard',
             'class': '4',
             'name': 'Power Plant',
             'rating': 'A'},
 128064048: {'category': 'standard',
             'class': '5',
             'name': 'Power Plant',
             'rating': 'E'},
 128064049: {'category': 'standard',
             'class': '5',
             'name': 'Power Plant',
             'rating': 'D'},
 128064050: {'category': 'standard',
             'class': '5',
             'name': 'Power Plant',
             'rating': 'C'},
 128064051: {'category': 'standard',
             'class': '5',
             'name': 'Power Plant',
             'rating': 'B'},
 128064052: {'category': 'standard',
             'class': '5',
             'name': 'Power Plant',
             'rating': 'A'},
 128064053: {'category': 'standard',
             'class': '6',
             'name': 'Power Plant',
             'rating': 'E'},
 128064054: {'category': 'standard',
             'class': '6',
             'name': 'Power Plant',
             'rating': 'D'},
 128064055: {'category': 'standard',
             'class': '6',
             'name': 'Power Plant',
             'rating': 'C'},
 128064056: {'category': 'standard',
             'class': '6',
             'name': 'Power Plant',
             'rating': 'B'},
 128064057: {'category': 'standard',
             'class': '6',
             'name': 'Power Plant',
             'rating': 'A'},
 128064058: {'category': 'standard',
             'class': '7',
             'name': 'Power Plant',
             'rating': 'E'},
 128064059: {'category': 'standard',
             'class': '7',
             'name': 'Power Plant',
             'rating': 'D'},
 128064060: {'category': 'standard',
             'class': '7',
             'name': 'Power Plant',
             'rating': 'C'},
 128064061: {'category': 'standard',
             'class': '7',
             'name': 'Power Plant',
             'rating': 'B'},
 128064062: {'category': 'standard',
             'class': '7',
             'name': 'Power Plant',
             'rating': 'A'},
 128064063: {'category': 'standard',
             'class': '8',
             'name': 'Power Plant',
             'rating': 'E'},
 128064064: {'category': 'standard',
             'class': '8',
             'name': 'Power Plant',
             'rating': 'D'},
 128064065: {'category': 'standard',
             'class': '8',
             'name': 'Power Plant',
             'rating': 'C'},
 128064066: {'category': 'standard',
             'class': '8',
             'name': 'Power Plant',
             'rating': 'B'},
 128064067: {'category': 'standard',
             'class': '8',
             'name': 'Power Plant',
             'rating': 'A'},
 128064068: {'category': 'standard',
             'class': '2',
             'name': 'Thrusters',
             'rating': 'E'},
 128064069: {'category': 'standard',
             'class': '2',
             'name': 'Thrusters',
             'rating': 'D'},
 128064070: {'category': 'standard',
             'class': '2',
             'name': 'Thrusters',
             'rating': 'C'},
 128064071: {'category': 'standard',
             'class': '2',
             'name': 'Thrusters',
             'rating': 'B'},
 128064072: {'category': 'standard',
             'class': '2',
             'name': 'Thrusters',
             'rating': 'A'},
 128064073: {'category': 'standard',
             'class': '3',
             'name': 'Thrusters',
             'rating': 'E'},
 128064074: {'category': 'standard',
             'class': '3',
             'name': 'Thrusters',
             'rating': 'D'},
 128064075: {'category': 'standard',
             'class': '3',
             'name': 'Thrusters',
             'rating': 'C'},
 128064076: {'category': 'standard',
             'class': '3',
             'name': 'Thrusters',
             'rating': 'B'},
 128064077: {'category': 'standard',
             'class': '3',
             'name': 'Thrusters',
             'rating': 'A'},
 128064078: {'category': 'standard',
             'class': '4',
             'name': 'Thrusters',
             'rating': 'E'},
 128064079: {'category': 'standard',
             'class': '4',
             'name': 'Thrusters',
             'rating': 'D'},
 128064080: {'category': 'standard',
             'class': '4',
             'name': 'Thrusters',
             'rating': 'C'},
 128064081: {'category': 'standard',
             'class': '4',
             'name': 'Thrusters',
             'rating': 'B'},
 128064082: {'category': 'standard',
             'class': '4',
             'name': 'Thrusters',
             'rating': 'A'},
 128064083: {'category': 'standard',
             'class': '5',
             'name': 'Thrusters',
             'rating': 'E'},
 128064084: {'category': 'standard',
             'class': '5',
             'name': 'Thrusters',
             'rating': 'D'},
 128064085: {'category': 'standard',
             'class': '5',
             'name': 'Thrusters',
             'rating': 'C'},
 128064086: {'category': 'standard',
             'class': '5',
             'name': 'Thrusters',
             'rating': 'B'},
 128064087: {'category': 'standard',
             'class': '5',
             'name': 'Thrusters',
             'rating': 'A'},
 128064088: {'category': 'standard',
             'class': '6',
             'name': 'Thrusters',
             'rating': 'E'},
 128064089: {'category': 'standard',
             'class': '6',
             'name': 'Thrusters',
             'rating': 'D'},
 128064090: {'category': 'standard',
             'class': '6',
             'name': 'Thrusters',
             'rating': 'C'},
 128064091: {'category': 'standard',
             'class': '6',
             'name': 'Thrusters',
             'rating': 'B'},
 128064092: {'category': 'standard',
             'class': '6',
             'name': 'Thrusters',
             'rating': 'A'},
 128064093: {'category': 'standard',
             'class': '7',
             'name': 'Thrusters',
             'rating': 'E'},
 128064094: {'category': 'standard',
             'class': '7',
             'name': 'Thrusters',
             'rating': 'D'},
 128064095: {'category': 'standard',
             'class': '7',
             'name': 'Thrusters',
             'rating': 'C'},
 128064096: {'category': 'standard',
             'class': '7',
             'name': 'Thrusters',
             'rating': 'B'},
 128064097: {'category': 'standard',
             'class': '7',
             'name': 'Thrusters',
             'rating': 'A'},
 128064098: {'category': 'standard',
             'class': '8',
             'name': 'Thrusters',
             'rating': 'E'},
 128064099: {'category': 'standard',
             'class': '8',
             'name': 'Thrusters',
             'rating': 'D'},
 128064100: {'category': 'standard',
             'class': '8',
             'name': 'Thrusters',
             'rating': 'C'},
 128064101: {'category': 'standard',
             'class': '8',
             'name': 'Thrusters',
             'rating': 'B'},
 128064102: {'category': 'standard',
             'class': '8',
             'name': 'Thrusters',
             'rating': 'A'},
 128064103: {'category': 'standard',
             'class': '2',
             'name': 'Frame Shift Drive',
             'rating': 'E'},
 128064104: {'category': 'standard',
             'class': '2',
             'name': 'Frame Shift Drive',
             'rating': 'D'},
 128064105: {'category': 'standard',
             'class': '2',
             'name': 'Frame Shift Drive',
             'rating': 'C'},
 128064106: {'category': 'standard',
             'class': '2',
             'name': 'Frame Shift Drive',
             'rating': 'B'},
 128064107: {'category': 'standard',
             'class': '2',
             'name': 'Frame Shift Drive',
             'rating': 'A'},
 128064108: {'category': 'standard',
             'class': '3',
             'name': 'Frame Shift Drive',
             'rating': 'E'},
 128064109: {'category': 'standard',
             'class': '3',
             'name': 'Frame Shift Drive',
             'rating': 'D'},
 128064110: {'category': 'standard',
             'class': '3',
             'name': 'Frame Shift Drive',
             'rating': 'C'},
 128064111: {'category': 'standard',
             'class': '3',
             'name': 'Frame Shift Drive',
             'rating': 'B'},
 128064112: {'category': 'standard',
             'class': '3',
             'name': 'Frame Shift Drive',
             'rating': 'A'},
 128064113: {'category': 'standard',
             'class': '4',
             'name': 'Frame Shift Drive',
             'rating': 'E'},
 128064114: {'category': 'standard',
             'class': '4',
             'name': 'Frame Shift Drive',
             'rating': 'D'},
 128064115: {'category': 'standard',
             'class': '4',
             'name': 'Frame Shift Drive',
             'rating': 'C'},
 128064116: {'category': 'standard',
             'class': '4',
             'name': 'Frame Shift Drive',
             'rating': 'B'},
 128064117: {'category': 'standard',
             'class': '4',
             'name': 'Frame Shift Drive',
             'rating': 'A'},
 128064118: {'category': 'standard',
             'class': '5',
             'name': 'Frame Shift Drive',
             'rating': 'E'},
 128064119: {'category': 'standard',
             'class': '5',
             'name': 'Frame Shift Drive',
             'rating': 'D'},
 128064120: {'category': 'standard',
             'class': '5',
             'name': 'Frame Shift Drive',
             'rating': 'C'},
 128064121: {'category': 'standard',
             'class': '5',
             'name': 'Frame Shift Drive',
             'rating': 'B'},
 128064122: {'category': 'standard',
             'class': '5',
             'name': 'Frame Shift Drive',
             'rating': 'A'},
 128064123: {'category': 'standard',
             'class': '6',
             'name': 'Frame Shift Drive',
             'rating': 'E'},
 128064124: {'category': 'standard',
             'class': '6',
             'name': 'Frame Shift Drive',
             'rating': 'D'},
 128064125: {'category': 'standard',
             'class': '6',
             'name': 'Frame Shift Drive',
             'rating': 'C'},
 128064126: {'category': 'standard',
             'class': '6',
             'name': 'Frame Shift Drive',
             'rating': 'B'},
 128064127: {'category': 'standard',
             'class': '6',
             'name': 'Frame Shift Drive',
             'rating': 'A'},
 128064128: {'category': 'standard',
             'class': '7',
             'name': 'Frame Shift Drive',
             'rating': 'E'},
 128064129: {'category': 'standard',
             'class': '7',
             'name': 'Frame Shift Drive',
             'rating': 'D'},
 128064130: {'category': 'standard',
             'class': '7',
             'name': 'Frame Shift Drive',
             'rating': 'C'},
 128064131: {'category': 'standard',
             'class': '7',
             'name': 'Frame Shift Drive',
             'rating': 'B'},
 128064132: {'category': 'standard',
             'class': '7',
             'name': 'Frame Shift Drive',
             'rating': 'A'},
 128064133: {'category': 'standard',
             'class': '8',
             'name': 'Frame Shift Drive',
             'rating': 'E'},
 128064134: {'category': 'standard',
             'class': '8',
             'name': 'Frame Shift Drive',
             'rating': 'D'},
 128064135: {'category': 'standard',
             'class': '8',
             'name': 'Frame Shift Drive',
             'rating': 'C'},
 128064136: {'category': 'standard',
             'class': '8',
             'name': 'Frame Shift Drive',
             'rating': 'B'},
 128064137: {'category': 'standard',
             'class': '8',
             'name': 'Frame Shift Drive',
             'rating': 'A'},
 128064138: {'category': 'standard',
             'class': '1',
             'name': 'Life Support',
             'rating': 'E'},
 128064139: {'category': 'standard',
             'class': '1',
             'name': 'Life Support',
             'rating': 'D'},
 128064140: {'category': 'standard',
             'class': '1',
             'name': 'Life Support',
             'rating': 'C'},
 128064141: {'category': 'standard',
             'class': '1',
             'name': 'Life Support',
             'rating': 'B'},
 128064142: {'category': 'standard',
             'class': '1',
             'name': 'Life Support',
             'rating': 'A'},
 128064143: {'category': 'standard',
             'class': '2',
             'name': 'Life Support',
             'rating': 'E'},
 128064144: {'category': 'standard',
             'class': '2',
             'name': 'Life Support',
             'rating': 'D'},
 128064145: {'category': 'standard',
             'class': '2',
             'name': 'Life Support',
             'rating': 'C'},
 128064146: {'category': 'standard',
             'class': '2',
             'name': 'Life Support',
             'rating': 'B'},
 128064147: {'category': 'standard',
             'class': '2',
             'name': 'Life Support',
             'rating': 'A'},
 128064148: {'category': 'standard',
             'class': '3',
             'name': 'Life Support',
             'rating': 'E'},
 128064149: {'category': 'standard',
             'class': '3',
             'name': 'Life Support',
             'rating': 'D'},
 128064150: {'category': 'standard',
             'class': '3',
             'name': 'Life Support',
             'rating': 'C'},
 128064151: {'category': 'standard',
             'class': '3',
             'name': 'Life Support',
             'rating': 'B'},
 128064152: {'category': 'standard',
             'class': '3',
             'name': 'Life Support',
             'rating': 'A'},
 128064153: {'category': 'standard',
             'class': '4',
             'name': 'Life Support',
             'rating': 'E'},
 128064154: {'category': 'standard',
             'class': '4',
             'name': 'Life Support',
             'rating': 'D'},
 128064155: {'category': 'standard',
             'class': '4',
             'name': 'Life Support',
             'rating': 'C'},
 128064156: {'category': 'standard',
             'class': '4',
             'name': 'Life Support',
             'rating': 'B'},
 128064157: {'category': 'standard',
             'class': '4',
             'name': 'Life Support',
             'rating': 'A'},
 128064158: {'category': 'standard',
             'class': '5',
             'name': 'Life Support',
             'rating': 'E'},
 128064159: {'category': 'standard',
             'class': '5',
             'name': 'Life Support',
             'rating': 'D'},
 128064160: {'category': 'standard',
             'class': '5',
             'name': 'Life Support',
             'rating': 'C'},
 128064161: {'category': 'standard',
             'class': '5',
             'name': 'Life Support',
             'rating': 'B'},
 128064162: {'category': 'standard',
             'class': '5',
             'name': 'Life Support',
             'rating': 'A'},
 128064163: {'category': 'standard',
             'class': '6',
             'name': 'Life Support',
             'rating': 'E'},
 128064164: {'category': 'standard',
             'class': '6',
             'name': 'Life Support',
             'rating': 'D'},
 128064165: {'category': 'standard',
             'class': '6',
             'name': 'Life Support',
             'rating': 'C'},
 128064166: {'category': 'standard',
             'class': '6',
             'name': 'Life Support',
             'rating': 'B'},
 128064167: {'category': 'standard',
             'class': '6',
             'name': 'Life Support',
             'rating': 'A'},
 128064168: {'category': 'standard',
             'class': '7',
             'name': 'Life Support',
             'rating': 'E'},
 128064169: {'category': 'standard',
             'class': '7',
             'name': 'Life Support',
             'rating': 'D'},
 128064170: {'category': 'standard',
             'class': '7',
             'name': 'Life Support',
             'rating': 'C'},
 128064171: {'category': 'standard',
             'class': '7',
             'name': 'Life Support',
             'rating': 'B'},
 128064172: {'category': 'standard',
             'class': '7',
             'name': 'Life Support',
             'rating': 'A'},
 128064173: {'category': 'standard',
             'class': '8',
             'name': 'Life Support',
             'rating': 'E'},
 128064174: {'category': 'standard',
             'class': '8',
             'name': 'Life Support',
             'rating': 'D'},
 128064175: {'category': 'standard',
             'class': '8',
             'name': 'Life Support',
             'rating': 'C'},
 128064176: {'category': 'standard',
             'class': '8',
             'name': 'Life Support',
             'rating': 'B'},
 128064177: {'category': 'standard',
             'class': '8',
             'name': 'Life Support',
             'rating': 'A'},
 128064178: {'category': 'standard',
             'class': '1',
             'name': 'Power Distributor',
             'rating': 'E'},
 128064179: {'category': 'standard',
             'class': '1',
             'name': 'Power Distributor',
             'rating': 'D'},
 128064180: {'category': 'standard',
             'class': '1',
             'name': 'Power Distributor',
             'rating': 'C'},
 128064181: {'category': 'standard',
             'class': '1',
             'name': 'Power Distributor',
             'rating': 'B'},
 128064182: {'category': 'standard',
             'class': '1',
             'name': 'Power Distributor',
             'rating': 'A'},
 128064183: {'category': 'standard',
             'class': '2',
             'name': 'Power Distributor',
             'rating': 'E'},
 128064184: {'category': 'standard',
             'class': '2',
             'name': 'Power Distributor',
             'rating': 'D'},
 128064185: {'category': 'standard',
             'class': '2',
             'name': 'Power Distributor',
             'rating': 'C'},
 128064186: {'category': 'standard',
             'class': '2',
             'name': 'Power Distributor',
             'rating': 'B'},
 128064187: {'category': 'standard',
             'class': '2',
             'name': 'Power Distributor',
             'rating': 'A'},
 128064188: {'category': 'standard',
             'class': '3',
             'name': 'Power Distributor',
             'rating': 'E'},
 128064189: {'category': 'standard',
             'class': '3',
             'name': 'Power Distributor',
             'rating': 'D'},
 128064190: {'category': 'standard',
             'class': '3',
             'name': 'Power Distributor',
             'rating': 'C'},
 128064191: {'category': 'standard',
             'class': '3',
             'name': 'Power Distributor',
             'rating': 'B'},
 128064192: {'category': 'standard',
             'class': '3',
             'name': 'Power Distributor',
             'rating': 'A'},
 128064193: {'category': 'standard',
             'class': '4',
             'name': 'Power Distributor',
             'rating': 'E'},
 128064194: {'category': 'standard',
             'class': '4',
             'name': 'Power Distributor',
             'rating': 'D'},
 128064195: {'category': 'standard',
             'class': '4',
             'name': 'Power Distributor',
             'rating': 'C'},
 128064196: {'category': 'standard',
             'class': '4',
             'name': 'Power Distributor',
             'rating': 'B'},
 128064197: {'category': 'standard',
             'class': '4',
             'name': 'Power Distributor',
             'rating': 'A'},
 128064198: {'category': 'standard',
             'class': '5',
             'name': 'Power Distributor',
             'rating': 'E'},
 128064199: {'category': 'standard',
             'class': '5',
             'name': 'Power Distributor',
             'rating': 'D'},
 128064200: {'category': 'standard',
             'class': '5',
             'name': 'Power Distributor',
             'rating': 'C'},
 128064201: {'category': 'standard',
             'class': '5',
             'name': 'Power Distributor',
             'rating': 'B'},
 128064202: {'category': 'standard',
             'class': '5',
             'name': 'Power Distributor',
             'rating': 'A'},
 128064203: {'category': 'standard',
             'class': '6',
             'name': 'Power Distributor',
             'rating': 'E'},
 128064204: {'category': 'standard',
             'class': '6',
             'name': 'Power Distributor',
             'rating': 'D'},
 128064205: {'category': 'standard',
             'class': '6',
             'name': 'Power Distributor',
             'rating': 'C'},
 128064206: {'category': 'standard',
             'class': '6',
             'name': 'Power Distributor',
             'rating': 'B'},
 128064207: {'category': 'standard',
             'class': '6',
             'name': 'Power Distributor',
             'rating': 'A'},
 128064208: {'category': 'standard',
             'class': '7',
             'name': 'Power Distributor',
             'rating': 'E'},
 128064209: {'category': 'standard',
             'class': '7',
             'name': 'Power Distributor',
             'rating': 'D'},
 128064210: {'category': 'standard',
             'class': '7',
             'name': 'Power Distributor',
             'rating': 'C'},
 128064211: {'category': 'standard',
             'class': '7',
             'name': 'Power Distributor',
             'rating': 'B'},
 128064212: {'category': 'standard',
             'class': '7',
             'name': 'Power Distributor',
             'rating': 'A'},
 128064213: {'category': 'standard',
             'class': '8',
             'name': 'Power Distributor',
             'rating': 'E'},
 128064214: {'category': 'standard',
             'class': '8',
             'name': 'Power Distributor',
             'rating': 'D'},
 128064215: {'category': 'standard',
             'class': '8',
             'name': 'Power Distributor',
             'rating': 'C'},
 128064216: {'category': 'standard',
             'class': '8',
             'name': 'Power Distributor',
             'rating': 'B'},
 128064217: {'category': 'standard',
             'class': '8',
             'name': 'Power Distributor',
             'rating': 'A'},
 128064218: {'category': 'standard',
             'class': '1',
             'name': 'Sensors',
             'rating': 'E'},
 128064219: {'category': 'standard',
             'class': '1',
             'name': 'Sensors',
             'rating': 'D'},
 128064220: {'category': 'standard',
             'class': '1',
             'name': 'Sensors',
             'rating': 'C'},
 128064221: {'category': 'standard',
             'class': '1',
             'name': 'Sensors',
             'rating': 'B'},
 128064222: {'category': 'standard',
             'class': '1',
             'name': 'Sensors',
             'rating': 'A'},
 128064223: {'category': 'standard',
             'class': '2',
             'name': 'Sensors',
             'rating': 'E'},
 128064224: {'category': 'standard',
             'class': '2',
             'name': 'Sensors',
             'rating': 'D'},
 128064225: {'category': 'standard',
             'class': '2',
             'name': 'Sensors',
             'rating': 'C'},
 128064226: {'category': 'standard',
             'class': '2',
             'name': 'Sensors',
             'rating': 'B'},
 128064227: {'category': 'standard',
             'class': '2',
             'name': 'Sensors',
             'rating': 'A'},
 128064228: {'category': 'standard',
             'class': '3',
             'name': 'Sensors',
             'rating': 'E'},
 128064229: {'category': 'standard',
             'class': '3',
             'name': 'Sensors',
             'rating': 'D'},
 128064230: {'category': 'standard',
             'class': '3',
             'name': 'Sensors',
             'rating': 'C'},
 128064231: {'category': 'standard',
             'class': '3',
             'name': 'Sensors',
             'rating': 'B'},
 128064232: {'category': 'standard',
             'class': '3',
             'name': 'Sensors',
             'rating': 'A'},
 128064233: {'category': 'standard',
             'class': '4',
             'name': 'Sensors',
             'rating': 'E'},
 128064234: {'category': 'standard',
             'class': '4',
             'name': 'Sensors',
             'rating': 'D'},
 128064235: {'category': 'standard',
             'class': '4',
             'name': 'Sensors',
             'rating': 'C'},
 128064236: {'category': 'standard',
             'class': '4',
             'name': 'Sensors',
             'rating': 'B'},
 128064237: {'category': 'standard',
             'class': '4',
             'name': 'Sensors',
             'rating': 'A'},
 128064238: {'category': 'standard',
             'class': '5',
             'name': 'Sensors',
             'rating': 'E'},
 128064239: {'category': 'standard',
             'class': '5',
             'name': 'Sensors',
             'rating': 'D'},
 128064240: {'category': 'standard',
             'class': '5',
             'name': 'Sensors',
             'rating': 'C'},
 128064241: {'category': 'standard',
             'class': '5',
             'name': 'Sensors',
             'rating': 'B'},
 128064242: {'category': 'standard',
             'class': '5',
             'name': 'Sensors',
             'rating': 'A'},
 128064243: {'category': 'standard',
             'class': '6',
             'name': 'Sensors',
             'rating': 'E'},
 128064244: {'category': 'standard',
             'class': '6',
             'name': 'Sensors',
             'rating': 'D'},
 128064245: {'category': 'standard',
             'class': '6',
             'name': 'Sensors',
             'rating': 'C'},
 128064246: {'category': 'standard',
             'class': '6',
             'name': 'Sensors',
             'rating': 'B'},
 128064247: {'category': 'standard',
             'class': '6',
             'name': 'Sensors',
             'rating': 'A'},
 128064248: {'category': 'standard',
             'class': '7',
             'name': 'Sensors',
             'rating': 'E'},
 128064249: {'category': 'standard',
             'class': '7',
             'name': 'Sensors',
             'rating': 'D'},
 128064250: {'category': 'standard',
             'class': '7',
             'name': 'Sensors',
             'rating': 'C'},
 128064251: {'category': 'standard',
             'class': '7',
             'name': 'Sensors',
             'rating': 'B'},
 128064252: {'category': 'standard',
             'class': '7',
             'name': 'Sensors',
             'rating': 'A'},
 128064253: {'category': 'standard',
             'class': '8',
             'name': 'Sensors',
             'rating': 'E'},
 128064254: {'category': 'standard',
             'class': '8',
             'name': 'Sensors',
             'rating': 'D'},
 128064255: {'category': 'standard',
             'class': '8',
             'name': 'Sensors',
             'rating': 'C'},
 128064256: {'category': 'standard',
             'class': '8',
             'name': 'Sensors',
             'rating': 'B'},
 128064257: {'category': 'standard',
             'class': '8',
             'name': 'Sensors',
             'rating': 'A'},
 128064263: {'category': 'internal',
             'class': '2',
             'name': 'Shield Generator',
             'rating': 'E'},
 128064264: {'category': 'internal',
             'class': '2',
             'name': 'Shield Generator',
             'rating': 'D'},
 128064265: {'category': 'internal',
             'class': '2',
             'name': 'Shield Generator',
             'rating': 'C'},
 128064266: {'category': 'internal',
             'class': '2',
             'name': 'Shield Generator',
             'rating': 'B'},
 128064267: {'category': 'internal',
             'class': '2',
             'name': 'Shield Generator',
             'rating': 'A'},
 128064268: {'category': 'internal',
             'class': '3',
             'name': 'Shield Generator',
             'rating': 'E'},
 128064269: {'category': 'internal',
             'class': '3',
             'name': 'Shield Generator',
             'rating': 'D'},
 128064270: {'category': 'internal',
             'class': '3',
             'name': 'Shield Generator',
             'rating': 'C'},
 128064271: {'category': 'internal',
             'class': '3',
             'name': 'Shield Generator',
             'rating': 'B'},
 128064272: {'category': 'internal',
             'class': '3',
             'name': 'Shield Generator',
             'rating': 'A'},
 128064273: {'category': 'internal',
             'class': '4',
             'name': 'Shield Generator',
             'rating': 'E'},
 128064274: {'category': 'internal',
             'class': '4',
             'name': 'Shield Generator',
             'rating': 'D'},
 128064275: {'category': 'internal',
             'class': '4',
             'name': 'Shield Generator',
             'rating': 'C'},
 128064276: {'category': 'internal',
             'class': '4',
             'name': 'Shield Generator',
             'rating': 'B'},
 128064277: {'category': 'internal',
             'class': '4',
             'name': 'Shield Generator',
             'rating': 'A'},
 128064278: {'category': 'internal',
             'class': '5',
             'name': 'Shield Generator',
             'rating': 'E'},
 128064279: {'category': 'internal',
             'class': '5',
             'name': 'Shield Generator',
             'rating': 'D'},
 128064280: {'category': 'internal',
             'class': '5',
             'name': 'Shield Generator',
             'rating': 'C'},
 128064281: {'category': 'internal',
             'class': '5',
             'name': 'Shield Generator',
             'rating': 'B'},
 128064282: {'category': 'internal',
             'class': '5',
             'name': 'Shield Generator',
             'rating': 'A'},
 128064283: {'category': 'internal',
             'class': '6',
             'name': 'Shield Generator',
             'rating': 'E'},
 128064284: {'category': 'internal',
             'class': '6',
             'name': 'Shield Generator',
             'rating': 'D'},
 128064285: {'category': 'internal',
             'class': '6',
             'name': 'Shield Generator',
             'rating': 'C'},
 128064286: {'category': 'internal',
             'class': '6',
             'name': 'Shield Generator',
             'rating': 'B'},
 128064287: {'category': 'internal',
             'class': '6',
             'name': 'Shield Generator',
             'rating': 'A'},
 128064288: {'category': 'internal',
             'class': '7',
             'name': 'Shield Generator',
             'rating': 'E'},
 128064289: {'category': 'internal',
             'class': '7',
             'name': 'Shield Generator',
             'rating': 'D'},
 128064290: {'category': 'internal',
             'class': '7',
             'name': 'Shield Generator',
             'rating': 'C'},
 128064291: {'category': 'internal',
             'class': '7',
             'name': 'Shield Generator',
             'rating': 'B'},
 128064292: {'category': 'internal',
             'class': '7',
             'name': 'Shield Generator',
             'rating': 'A'},
 128064293: {'category': 'internal',
             'class': '8',
             'name': 'Shield Generator',
             'rating': 'E'},
 128064294: {'category': 'internal',
             'class': '8',
             'name': 'Shield Generator',
             'rating': 'D'},
 128064295: {'category': 'internal',
             'class': '8',
             'name': 'Shield Generator',
             'rating': 'C'},
 128064296: {'category': 'internal',
             'class': '8',
             'name': 'Shield Generator',
             'rating': 'B'},
 128064297: {'category': 'internal',
             'class': '8',
             'name': 'Shield Generator',
             'rating': 'A'},
 128064298: {'category': 'internal',
             'class': '1',
             'name': 'Shield Cell Bank',
             'rating': 'E'},
 128064299: {'category': 'internal',
             'class': '1',
             'name': 'Shield Cell Bank',
             'rating': 'D'},
 128064300: {'category': 'internal',
             'class': '1',
             'name': 'Shield Cell Bank',
             'rating': 'C'},
 128064301: {'category': 'internal',
             'class': '1',
             'name': 'Shield Cell Bank',
             'rating': 'B'},
 128064302: {'category': 'internal',
             'class': '1',
             'name': 'Shield Cell Bank',
             'rating': 'A'},
 128064303: {'category': 'internal',
             'class': '2',
             'name': 'Shield Cell Bank',
             'rating': 'E'},
 128064304: {'category': 'internal',
             'class': '2',
             'name': 'Shield Cell Bank',
             'rating': 'D'},
 128064305: {'category': 'internal',
             'class': '2',
             'name': 'Shield Cell Bank',
             'rating': 'C'},
 128064306: {'category': 'internal',
             'class': '2',
             'name': 'Shield Cell Bank',
             'rating': 'B'},
 128064307: {'category': 'internal',
             'class': '2',
             'name': 'Shield Cell Bank',
             'rating': 'A'},
 128064308: {'category': 'internal',
             'class': '3',
             'name': 'Shield Cell Bank',
             'rating': 'E'},
 128064309: {'category': 'internal',
             'class': '3',
             'name': 'Shield Cell Bank',
             'rating': 'D'},
 128064310: {'category': 'internal',
             'class': '3',
             'name': 'Shield Cell Bank',
             'rating': 'C'},
 128064311: {'category': 'internal',
             'class': '3',
             'name': 'Shield Cell Bank',
             'rating': 'B'},
 128064312: {'category': 'internal',
             'class': '3',
             'name': 'Shield Cell Bank',
             'rating': 'A'},
 128064313: {'category': 'internal',
             'class': '4',
             'name': 'Shield Cell Bank',
             'rating': 'E'},
 128064314: {'category': 'internal',
             'class': '4',
             'name': 'Shield Cell Bank',
             'rating': 'D'},
 128064315: {'category': 'internal',
             'class': '4',
             'name': 'Shield Cell Bank',
             'rating': 'C'},
 128064316: {'category': 'internal',
             'class': '4',
             'name': 'Shield Cell Bank',
             'rating': 'B'},
 128064317: {'category': 'internal',
             'class': '4',
             'name': 'Shield Cell Bank',
             'rating': 'A'},
 128064318: {'category': 'internal',
             'class': '5',
             'name': 'Shield Cell Bank',
             'rating': 'E'},
 128064319: {'category': 'internal',
             'class': '5',
             'name': 'Shield Cell Bank',
             'rating': 'D'},
 128064320: {'category': 'internal',
             'class': '5',
             'name': 'Shield Cell Bank',
             'rating': 'C'},
 128064321: {'category': 'internal',
             'class': '5',
             'name': 'Shield Cell Bank',
             'rating': 'B'},
 128064322: {'category': 'internal',
             'class': '5',
             'name': 'Shield Cell Bank',
             'rating': 'A'},
 128064323: {'category': 'internal',
             'class': '6',
             'name': 'Shield Cell Bank',
             'rating': 'E'},
 128064324: {'category': 'internal',
             'class': '6',
             'name': 'Shield Cell Bank',
             'rating': 'D'},
 128064325: {'category': 'internal',
             'class': '6',
             'name': 'Shield Cell Bank',
             'rating': 'C'},
 128064326: {'category': 'internal',
             'class': '6',
             'name': 'Shield Cell Bank',
             'rating': 'B'},
 128064327: {'category': 'internal',
             'class': '6',
             'name': 'Shield Cell Bank',
             'rating': 'A'},
 128064328: {'category': 'internal',
             'class': '7',
             'name': 'Shield Cell Bank',
             'rating': 'E'},
 128064329: {'category': 'internal',
             'class': '7',
             'name': 'Shield Cell Bank',
             'rating': 'D'},
 128064330: {'category': 'internal',
             'class': '7',
             'name': 'Shield Cell Bank',
             'rating': 'C'},
 128064331: {'category': 'internal',
             'class': '7',
             'name': 'Shield Cell Bank',
             'rating': 'B'},
 128064332: {'category': 'internal',
             'class': '7',
             'name': 'Shield Cell Bank',
             'rating': 'A'},
 128064333: {'category': 'internal',
             'class': '8',
             'name': 'Shield Cell Bank',
             'rating': 'E'},
 128064334: {'category': 'internal',
             'class': '8',
             'name': 'Shield Cell Bank',
             'rating': 'D'},
 128064335: {'category': 'internal',
             'class': '8',
             'name': 'Shield Cell Bank',
             'rating': 'C'},
 128064336: {'category': 'internal',
             'class': '8',
             'name': 'Shield Cell Bank',
             'rating': 'B'},
 128064337: {'category': 'internal',
             'class': '8',
             'name': 'Shield Cell Bank',
             'rating': 'A'},
 128064338: {'category': 'internal',
             'class': '1',
             'name': 'Cargo Rack',
             'rating': 'E'},
 128064339: {'category': 'internal',
             'class': '2',
             'name': 'Cargo Rack',
             'rating': 'E'},
 128064340: {'category': 'internal',
             'class': '3',
             'name': 'Cargo Rack',
             'rating': 'E'},
 128064341: {'category': 'internal',
             'class': '4',
             'name': 'Cargo Rack',
             'rating': 'E'},
 128064342: {'category': 'internal',
             'class': '5',
             'name': 'Cargo Rack',
             'rating': 'E'},
 128064343: {'category': 'internal',
             'class': '6',
             'name': 'Cargo Rack',
             'rating': 'E'},
 128064344: {'category': 'internal',
             'class': '7',
             'name': 'Cargo Rack',
             'rating': 'E'},
 128064345: {'category': 'internal',
             'class': '8',
             'name': 'Cargo Rack',
             'rating': 'E'},
 128064346: {'category': 'standard',
             'class': '1',
             'name': 'Fuel Tank',
             'rating': 'C'},
 128064347: {'category': 'standard',
             'class': '2',
             'name': 'Fuel Tank',
             'rating': 'C'},
 128064348: {'category': 'standard',
             'class': '3',
             'name': 'Fuel Tank',
             'rating': 'C'},
 128064349: {'category': 'standard',
             'class': '4',
             'name': 'Fuel Tank',
             'rating': 'C'},
 128064350: {'category': 'standard',
             'class': '5',
             'name': 'Fuel Tank',
             'rating': 'C'},
 128064351: {'category': 'standard',
             'class': '6',
             'name': 'Fuel Tank',
             'rating': 'C'},
 128064352: {'category': 'standard',
             'class': '7',
             'name': 'Fuel Tank',
             'rating': 'C'},
 128064353: {'category': 'standard',
             'class': '8',
             'name': 'Fuel Tank',
             'rating': 'C'},
 128066532: {'category': 'internal',
             'class': '1',
             'name': 'Hatch Breaker Limpet Controller',
             'rating': 'E'},
 128066533: {'category': 'internal',
             'class': '1',
             'name': 'Hatch Breaker Limpet Controller',
             'rating': 'D'},
 128066534: {'category': 'internal',
             'class': '1',
             'name': 'Hatch Breaker Limpet Controller',
             'rating': 'C'},
 128066535: {'category': 'internal',
             'class': '1',
             'name': 'Hatch Breaker Limpet Controller',
             'rating': 'B'},
 128066536: {'category': 'internal',
             'class': '1',
             'name': 'Hatch Breaker Limpet Controller',
             'rating': 'A'},
 128066537: {'category': 'internal',
             'class': '3',
             'name': 'Hatch Breaker Limpet Controller',
             'rating': 'E'},
 128066538: {'category': 'internal',
             'class': '3',
             'name': 'Hatch Breaker Limpet Controller',
             'rating': 'D'},
 128066539: {'category': 'internal',
             'class': '3',
             'name': 'Hatch Breaker Limpet Controller',
             'rating': 'C'},
 128066540: {'category': 'internal',
             'class': '3',
             'name': 'Hatch Breaker Limpet Controller',
             'rating': 'B'},
 128066541: {'category': 'internal',
             'class': '3',
             'name': 'Hatch Breaker Limpet Controller',
             'rating': 'A'},
 128066542: {'category': 'internal',
             'class': '5',
             'name': 'Hatch Breaker Limpet Controller',
             'rating': 'E'},
 128066543: {'category': 'internal',
             'class': '5',
             'name': 'Hatch Breaker Limpet Controller',
             'rating': 'D'},
 128066544: {'category': 'internal',
             'class': '5',
             'name': 'Hatch Breaker Limpet Controller',
             'rating': 'C'},
 128066545: {'category': 'internal',
             'class': '5',
             'name': 'Hatch Breaker Limpet Controller',
             'rating': 'B'},
 128066546: {'category': 'internal',
             'class': '5',
             'name': 'Hatch Breaker Limpet Controller',
             'rating': 'A'},
 128066547: {'category': 'internal',
             'class': '7',
             'name': 'Hatch Breaker Limpet Controller',
             'rating': 'E'},
 128066548: {'category': 'internal',
             'class': '7',
             'name': 'Hatch Breaker Limpet Controller',
             'rating': 'D'},
 128066549: {'category': 'internal',
             'class': '7',
             'name': 'Hatch Breaker Limpet Controller',
             'rating': 'C'},
 128066550: {'category': 'internal',
             'class': '7',
             'name': 'Hatch Breaker Limpet Controller',
             'rating': 'B'},
 128066551: {'category': 'internal',
             'class': '7',
             'name': 'Hatch Breaker Limpet Controller',
             'rating': 'A'},
 128662520: {'category': 'utility',
             'class': '0',
             'name': 'Cargo Scanner',
             'rating': 'E'},
 128662521: {'category': 'utility',
             'class': '0',
             'name': 'Cargo Scanner',
             'rating': 'D'},
 128662522: {'category': 'utility',
             'class': '0',
             'name': 'Cargo Scanner',
             'rating': 'C'},
 128662523: {'category': 'utility',
             'class': '0',
             'name': 'Cargo Scanner',
             'rating': 'B'},
 128662524: {'category': 'utility',
             'class': '0',
             'name': 'Cargo Scanner',
             'rating': 'A'},
 128662525: {'category': 'utility',
             'class': '0',
             'name': 'Frame Shift Wake Scanner',
             'rating': 'E'},
 128662526: {'category': 'utility',
             'class': '0',
             'name': 'Frame Shift Wake Scanner',
             'rating': 'D'},
 128662527: {'category': 'utility',
             'class': '0',
             'name': 'Frame Shift Wake Scanner',
             'rating': 'C'},
 128662528: {'category': 'utility',
             'class': '0',
             'name': 'Frame Shift Wake Scanner',
             'rating': 'B'},
 128662529: {'category': 'utility',
             'class': '0',
             'name': 'Frame Shift Wake Scanner',
             'rating': 'A'},
 128662530: {'category': 'utility',
             'class': '0',
             'name': 'Kill Warrant Scanner',
             'rating': 'E'},
 128662531: {'category': 'utility',
             'class': '0',
             'name': 'Kill Warrant Scanner',
             'rating': 'D'},
 128662532: {'category': 'utility',
             'class': '0',
             'name': 'Kill Warrant Scanner',
             'rating': 'C'},
 128662533: {'category': 'utility',
             'class': '0',
             'name': 'Kill Warrant Scanner',
             'rating': 'B'},
 128662534: {'category': 'utility',
             'class': '0',
             'name': 'Kill Warrant Scanner',
             'rating': 'A'},
 128662535: {'category': 'internal',
             'class': '1',
             'name': 'Basic Discovery Scanner',
             'rating': 'E'},
 128663560: {'category': 'internal',
             'class': '1',
             'name': 'Intermediate Discovery Scanner',
             'rating': 'D'},
 128663561: {'category': 'internal',
             'class': '1',
             'name': 'Advanced Discovery Scanner',
             'rating': 'C'},
 128666634: {'category': 'internal',
             'class': '1',
             'name': 'Detailed Surface Scanner',
             'rating': 'C'},
 128666644: {'category': 'internal',
             'class': '1',
             'name': 'Fuel Scoop',
             'rating': 'E'},
 128666645: {'category': 'internal',
             'class': '2',
             'name': 'Fuel Scoop',
             'rating': 'E'},
 128666646: {'category': 'internal',
             'class': '3',
             'name': 'Fuel Scoop',
             'rating': 'E'},
 128666647: {'category': 'internal',
             'class': '4',
             'name': 'Fuel Scoop',
             'rating': 'E'},
 128666648: {'category': 'internal',
             'class': '5',
             'name': 'Fuel Scoop',
             'rating': 'E'},
 128666649: {'category': 'internal',
             'class': '6',
             'name': 'Fuel Scoop',
             'rating': 'E'},
 128666650: {'category': 'internal',
             'class': '7',
             'name': 'Fuel Scoop',
             'rating': 'E'},
 128666651: {'category': 'internal',
             'class': '8',
             'name': 'Fuel Scoop',
             'rating': 'E'},
 128666652: {'category': 'internal',
             'class': '1',
             'name': 'Fuel Scoop',
             'rating': 'D'},
 128666653: {'category': 'internal',
             'class': '2',
             'name': 'Fuel Scoop',
             'rating': 'D'},
 128666654: {'category': 'internal',
             'class': '3',
             'name': 'Fuel Scoop',
             'rating': 'D'},
 128666655: {'category': 'internal',
             'class': '4',
             'name': 'Fuel Scoop',
             'rating': 'D'},
 128666656: {'category': 'internal',
             'class': '5',
             'name': 'Fuel Scoop',
             'rating': 'D'},
 128666657: {'category': 'internal',
             'class': '6',
             'name': 'Fuel Scoop',
             'rating': 'D'},
 128666658: {'category': 'internal',
             'class': '7',
             'name': 'Fuel Scoop',
             'rating': 'D'},
 128666659: {'category': 'internal',
             'class': '8',
             'name': 'Fuel Scoop',
             'rating': 'D'},
 128666660: {'category': 'internal',
             'class': '1',
             'name': 'Fuel Scoop',
             'rating': 'C'},
 128666661: {'category': 'internal',
             'class': '2',
             'name': 'Fuel Scoop',
             'rating': 'C'},
 128666662: {'category': 'internal',
             'class': '3',
             'name': 'Fuel Scoop',
             'rating': 'C'},
 128666663: {'category': 'internal',
             'class': '4',
             'name': 'Fuel Scoop',
             'rating': 'C'},
 128666664: {'category': 'internal',
             'class': '5',
             'name': 'Fuel Scoop',
             'rating': 'C'},
 128666665: {'category': 'internal',
             'class': '6',
             'name': 'Fuel Scoop',
             'rating': 'C'},
 128666666: {'category': 'internal',
             'class': '7',
             'name': 'Fuel Scoop',
             'rating': 'C'},
 128666667: {'category': 'internal',
             'class': '8',
             'name': 'Fuel Scoop',
             'rating': 'C'},
 128666668: {'category': 'internal',
             'class': '1',
             'name': 'Fuel Scoop',
             'rating': 'B'},
 128666669: {'category': 'internal',
             'class': '2',
             'name': 'Fuel Scoop',
             'rating': 'B'},
 128666670: {'category': 'internal',
             'class': '3',
             'name': 'Fuel Scoop',
             'rating': 'B'},
 128666671: {'category': 'internal',
             'class': '4',
             'name': 'Fuel Scoop',
             'rating': 'B'},
 128666672: {'category': 'internal',
             'class': '5',
             'name': 'Fuel Scoop',
             'rating': 'B'},
 128666673: {'category': 'internal',
             'class': '6',
             'name': 'Fuel Scoop',
             'rating': 'B'},
 128666674: {'category': 'internal',
             'class': '7',
             'name': 'Fuel Scoop',
             'rating': 'B'},
 128666675: {'category': 'internal',
             'class': '8',
             'name': 'Fuel Scoop',
             'rating': 'B'},
 128666676: {'category': 'internal',
             'class': '1',
             'name': 'Fuel Scoop',
             'rating': 'A'},
 128666677: {'category': 'internal',
             'class': '2',
             'name': 'Fuel Scoop',
             'rating': 'A'},
 128666678: {'category': 'internal',
             'class': '3',
             'name': 'Fuel Scoop',
             'rating': 'A'},
 128666679: {'category': 'internal',
             'class': '4',
             'name': 'Fuel Scoop',
             'rating': 'A'},
 128666680: {'category': 'internal',
             'class': '5',
             'name': 'Fuel Scoop',
             'rating': 'A'},
 128666681: {'category': 'internal',
             'class': '6',
             'name': 'Fuel Scoop',
             'rating': 'A'},
 128666682: {'category': 'internal',
             'class': '7',
             'name': 'Fuel Scoop',
             'rating': 'A'},
 128666683: {'category': 'internal',
             'class': '8',
             'name': 'Fuel Scoop',
             'rating': 'A'},
 128666684: {'category': 'internal',
             'class': '1',
             'name': 'Refinery',
             'rating': 'E'},
 128666685: {'category': 'internal',
             'class': '2',
             'name': 'Refinery',
             'rating': 'E'},
 128666686: {'category': 'internal',
             'class': '3',
             'name': 'Refinery',
             'rating': 'E'},
 128666687: {'category': 'internal',
             'class': '4',
             'name': 'Refinery',
             'rating': 'E'},
 128666688: {'category': 'internal',
             'class': '1',
             'name': 'Refinery',
             'rating': 'D'},
 128666689: {'category': 'internal',
             'class': '2',
             'name': 'Refinery',
             'rating': 'D'},
 128666690: {'category': 'internal',
             'class': '3',
             'name': 'Refinery',
             'rating': 'D'},
 128666691: {'category': 'internal',
             'class': '4',
             'name': 'Refinery',
             'rating': 'D'},
 128666692: {'category': 'internal',
             'class': '1',
             'name': 'Refinery',
             'rating': 'C'},
 128666693: {'category': 'internal',
             'class': '2',
             'name': 'Refinery',
             'rating': 'C'},
 128666694: {'category': 'internal',
             'class': '3',
             'name': 'Refinery',
             'rating': 'C'},
 128666695: {'category': 'internal',
             'class': '4',
             'name': 'Refinery',
             'rating': 'C'},
 128666696: {'category': 'internal',
             'class': '1',
             'name': 'Refinery',
             'rating': 'B'},
 128666697: {'category': 'internal',
             'class': '2',
             'name': 'Refinery',
             'rating': 'B'},
 128666698: {'category': 'internal',
             'class': '3',
             'name': 'Refinery',
             'rating': 'B'},
 128666699: {'category': 'internal',
             'class': '4',
             'name': 'Refinery',
             'rating': 'B'},
 128666700: {'category': 'internal',
             'class': '1',
             'name': 'Refinery',
             'rating': 'A'},
 128666701: {'category': 'internal',
             'class': '2',
             'name': 'Refinery',
             'rating': 'A'},
 128666702: {'category': 'internal',
             'class': '3',
             'name': 'Refinery',
             'rating': 'A'},
 128666703: {'category': 'internal',
             'class': '4',
             'name': 'Refinery',
             'rating': 'A'},
 128666704: {'category': 'internal',
             'class': '1',
             'name': 'Frame Shift Drive Interdictor',
             'rating': 'E'},
 128666705: {'category': 'internal',
             'class': '2',
             'name': 'Frame Shift Drive Interdictor',
             'rating': 'E'},
 128666706: {'category': 'internal',
             'class': '3',
             'name': 'Frame Shift Drive Interdictor',
             'rating': 'E'},
 128666707: {'category': 'internal',
             'class': '4',
             'name': 'Frame Shift Drive Interdictor',
             'rating': 'E'},
 128666708: {'category': 'internal',
             'class': '1',
             'name': 'Frame Shift Drive Interdictor',
             'rating': 'D'},
 128666709: {'category': 'internal',
             'class': '2',
             'name': 'Frame Shift Drive Interdictor',
             'rating': 'D'},
 128666710: {'category': 'internal',
             'class': '3',
             'name': 'Frame Shift Drive Interdictor',
             'rating': 'D'},
 128666711: {'category': 'internal',
             'class': '4',
             'name': 'Frame Shift Drive Interdictor',
             'rating': 'D'},
 128666712: {'category': 'internal',
             'class': '1',
             'name': 'Frame Shift Drive Interdictor',
             'rating': 'C'},
 128666713: {'category': 'internal',
             'class': '2',
             'name': 'Frame Shift Drive Interdictor',
             'rating': 'C'},
 128666714: {'category': 'internal',
             'class': '3',
             'name': 'Frame Shift Drive Interdictor',
             'rating': 'C'},
 128666715: {'category': 'internal',
             'class': '4',
             'name': 'Frame Shift Drive Interdictor',
             'rating': 'C'},
 128666716: {'category': 'internal',
             'class': '1',
             'name': 'Frame Shift Drive Interdictor',
             'rating': 'B'},
 128666717: {'category': 'internal',
             'class': '2',
             'name': 'Frame Shift Drive Interdictor',
             'rating': 'B'},
 128666718: {'category': 'internal',
             'class': '3',
             'name': 'Frame Shift Drive Interdictor',
             'rating': 'B'},
 128666719: {'category': 'internal',
             'class': '4',
             'name': 'Frame Shift Drive Interdictor',
             'rating': 'B'},
 128666720: {'category': 'internal',
             'class': '1',
             'name': 'Frame Shift Drive Interdictor',
             'rating': 'A'},
 128666721: {'category': 'internal',
             'class': '2',
             'name': 'Frame Shift Drive Interdictor',
             'rating': 'A'},
 128666722: {'category': 'internal',
             'class': '3',
             'name': 'Frame Shift Drive Interdictor',
             'rating': 'A'},
 128666723: {'category': 'internal',
             'class': '4',
             'name': 'Frame Shift Drive Interdictor',
             'rating': 'A'},
 128666724: {'category': 'hardpoint',
             'class': '1',
             'guidance': 'Dumbfire',
             'mount': 'Fixed',
             'name': 'Missile Rack',
             'rating': 'B'},
 128666725: {'category': 'hardpoint',
             'class': '2',
             'guidance': 'Dumbfire',
             'mount': 'Fixed',
             'name': 'Missile Rack',
             'rating': 'B'},
 128667598: {'category': 'internal',
             'class': '1',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'E'},
 128667599: {'category': 'internal',
             'class': '2',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'E'},
 128667600: {'category': 'internal',
             'class': '3',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'E'},
 128667601: {'category': 'internal',
             'class': '4',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'E'},
 128667602: {'category': 'internal',
             'class': '5',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'E'},
 128667603: {'category': 'internal',
             'class': '6',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'E'},
 128667604: {'category': 'internal',
             'class': '7',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'E'},
 128667605: {'category': 'internal',
             'class': '8',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'E'},
 128667606: {'category': 'internal',
             'class': '1',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'D'},
 128667607: {'category': 'internal',
             'class': '2',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'D'},
 128667608: {'category': 'internal',
             'class': '3',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'D'},
 128667609: {'category': 'internal',
             'class': '4',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'D'},
 128667610: {'category': 'internal',
             'class': '5',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'D'},
 128667611: {'category': 'internal',
             'class': '6',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'D'},
 128667612: {'category': 'internal',
             'class': '7',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'D'},
 128667613: {'category': 'internal',
             'class': '8',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'D'},
 128667614: {'category': 'internal',
             'class': '1',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'C'},
 128667615: {'category': 'internal',
             'class': '2',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'C'},
 128667616: {'category': 'internal',
             'class': '3',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'C'},
 128667617: {'category': 'internal',
             'class': '4',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'C'},
 128667618: {'category': 'internal',
             'class': '5',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'C'},
 128667619: {'category': 'internal',
             'class': '6',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'C'},
 128667620: {'category': 'internal',
             'class': '7',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'C'},
 128667621: {'category': 'internal',
             'class': '8',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'C'},
 128667622: {'category': 'internal',
             'class': '1',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'B'},
 128667623: {'category': 'internal',
             'class': '2',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'B'},
 128667624: {'category': 'internal',
             'class': '3',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'B'},
 128667625: {'category': 'internal',
             'class': '4',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'B'},
 128667626: {'category': 'internal',
             'class': '5',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'B'},
 128667627: {'category': 'internal',
             'class': '6',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'B'},
 128667628: {'category': 'internal',
             'class': '7',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'B'},
 128667629: {'category': 'internal',
             'class': '8',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'B'},
 128667630: {'category': 'internal',
             'class': '1',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'A'},
 128667631: {'category': 'internal',
             'class': '2',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'A'},
 128667632: {'category': 'internal',
             'class': '3',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'A'},
 128667633: {'category': 'internal',
             'class': '4',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'A'},
 128667634: {'category': 'internal',
             'class': '5',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'A'},
 128667635: {'category': 'internal',
             'class': '6',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'A'},
 128667636: {'category': 'internal',
             'class': '7',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'A'},
 128667637: {'category': 'internal',
             'class': '8',
             'name': 'Auto Field-Maintenance Unit',
             'rating': 'A'},
 128668532: {'category': 'utility',
             'class': '0',
             'name': 'Shield Booster',
             'rating': 'E'},
 128668533: {'category': 'utility',
             'class': '0',
             'name': 'Shield Booster',
             'rating': 'D'},
 128668534: {'category': 'utility',
             'class': '0',
             'name': 'Shield Booster',
             'rating': 'C'},
 128668535: {'category': 'utility',
             'class': '0',
             'name': 'Shield Booster',
             'rating': 'B'},
 128668536: {'category': 'utility',
             'class': '0',
             'name': 'Shield Booster',
             'rating': 'A'},
 128668537: {'category': 'internal',
             'class': '1',
             'name': 'Hull Reinforcement Package',
             'rating': 'E'},
 128668538: {'category': 'internal',
             'class': '1',
             'name': 'Hull Reinforcement Package',
             'rating': 'D'},
 128668539: {'category': 'internal',
             'class': '2',
             'name': 'Hull Reinforcement Package',
             'rating': 'E'},
 128668540: {'category': 'internal',
             'class': '2',
             'name': 'Hull Reinforcement Package',
             'rating': 'D'},
 128668541: {'category': 'internal',
             'class': '3',
             'name': 'Hull Reinforcement Package',
             'rating': 'E'},
 128668542: {'category': 'internal',
             'class': '3',
             'name': 'Hull Reinforcement Package',
             'rating': 'D'},
 128668543: {'category': 'internal',
             'class': '4',
             'name': 'Hull Reinforcement Package',
             'rating': 'E'},
 128668544: {'category': 'internal',
             'class': '4',
             'name': 'Hull Reinforcement Package',
             'rating': 'D'},
 128668545: {'category': 'internal',
             'class': '5',
             'name': 'Hull Reinforcement Package',
             'rating': 'E'},
 128668546: {'category': 'internal',
             'class': '5',
             'name': 'Hull Reinforcement Package',
             'rating': 'D'},
 128671120: {'category': 'hardpoint',
             'class': '3',
             'mount': 'Gimballed',
             'name': 'Cannon',
             'rating': 'C'},
 128671218: {'category': 'standard',
             'class': '1',
             'name': 'Lightweight Alloy',
             'rating': 'I',
             'ship': 'Diamondback Scout'},
 128671219: {'category': 'standard',
             'class': '1',
             'name': 'Reinforced Alloy',
             'rating': 'I',
             'ship': 'Diamondback Scout'},
 128671220: {'category': 'standard',
             'class': '1',
             'name': 'Military Grade Composite',
             'rating': 'I',
             'ship': 'Diamondback Scout'},
 128671221: {'category': 'standard',
             'class': '1',
             'name': 'Mirrored Surface Composite',
             'rating': 'I',
             'ship': 'Diamondback Scout'},
 128671222: {'category': 'standard',
             'class': '1',
             'name': 'Reactive Surface Composite',
             'rating': 'I',
             'ship': 'Diamondback Scout'},
 128671224: {'category': 'standard',
             'class': '1',
             'name': 'Lightweight Alloy',
             'rating': 'I',
             'ship': 'Imperial Courier'},
 128671225: {'category': 'standard',
             'class': '1',
             'name': 'Reinforced Alloy',
             'rating': 'I',
             'ship': 'Imperial Courier'},
 128671226: {'category': 'standard',
             'class': '1',
             'name': 'Military Grade Composite',
             'rating': 'I',
             'ship': 'Imperial Courier'},
 128671227: {'category': 'standard',
             'class': '1',
             'name': 'Mirrored Surface Composite',
             'rating': 'I',
             'ship': 'Imperial Courier'},
 128671228: {'category': 'standard',
             'class': '1',
             'name': 'Reactive Surface Composite',
             'rating': 'I',
             'ship': 'Imperial Courier'},
 128671229: {'category': 'internal',
             'class': '1',
             'name': 'Collector Limpet Controller',
             'rating': 'E'},
 128671230: {'category': 'internal',
             'class': '1',
             'name': 'Collector Limpet Controller',
             'rating': 'D'},
 128671231: {'category': 'internal',
             'class': '1',
             'name': 'Collector Limpet Controller',
             'rating': 'C'},
 128671232: {'category': 'internal',
             'class': '1',
             'name': 'Collector Limpet Controller',
             'rating': 'B'},
 128671233: {'category': 'internal',
             'class': '1',
             'name': 'Collector Limpet Controller',
             'rating': 'A'},
 128671234: {'category': 'internal',
             'class': '3',
             'name': 'Collector Limpet Controller',
             'rating': 'E'},
 128671235: {'category': 'internal',
             'class': '3',
             'name': 'Collector Limpet Controller',
             'rating': 'D'},
 128671236: {'category': 'internal',
             'class': '3',
             'name': 'Collector Limpet Controller',
             'rating': 'C'},
 128671237: {'category': 'internal',
             'class': '3',
             'name': 'Collector Limpet Controller',
             'rating': 'B'},
 128671238: {'category': 'internal',
             'class': '3',
             'name': 'Collector Limpet Controller',
             'rating': 'A'},
 128671239: {'category': 'internal',
             'class': '5',
             'name': 'Collector Limpet Controller',
             'rating': 'E'},
 128671240: {'category': 'internal',
             'class': '5',
             'name': 'Collector Limpet Controller',
             'rating': 'D'},
 128671241: {'category': 'internal',
             'class': '5',
             'name': 'Collector Limpet Controller',
             'rating': 'C'},
 128671242: {'category': 'internal',
             'class': '5',
             'name': 'Collector Limpet Controller',
             'rating': 'B'},
 128671243: {'category': 'internal',
             'class': '5',
             'name': 'Collector Limpet Controller',
             'rating': 'A'},
 128671244: {'category': 'internal',
             'class': '7',
             'name': 'Collector Limpet Controller',
             'rating': 'E'},
 128671245: {'category': 'internal',
             'class': '7',
             'name': 'Collector Limpet Controller',
             'rating': 'D'},
 128671246: {'category': 'internal',
             'class': '7',
             'name': 'Collector Limpet Controller',
             'rating': 'C'},
 128671247: {'category': 'internal',
             'class': '7',
             'name': 'Collector Limpet Controller',
             'rating': 'B'},
 128671248: {'category': 'internal',
             'class': '7',
             'name': 'Collector Limpet Controller',
             'rating': 'A'},
 128671249: {'category': 'internal',
             'class': '1',
             'name': 'Fuel Transfer Limpet Controller',
             'rating': 'E'},
 128671250: {'category': 'internal',
             'class': '1',
             'name': 'Fuel Transfer Limpet Controller',
             'rating': 'D'},
 128671251: {'category': 'internal',
             'class': '1',
             'name': 'Fuel Transfer Limpet Controller',
             'rating': 'C'},
 128671252: {'category': 'internal',
             'class': '1',
             'name': 'Fuel Transfer Limpet Controller',
             'rating': 'B'},
 128671253: {'category': 'internal',
             'class': '1',
             'name': 'Fuel Transfer Limpet Controller',
             'rating': 'A'},
 128671254: {'category': 'internal',
             'class': '3',
             'name': 'Fuel Transfer Limpet Controller',
             'rating': 'E'},
 128671255: {'category': 'internal',
             'class': '3',
             'name': 'Fuel Transfer Limpet Controller',
             'rating': 'D'},
 128671256: {'category': 'internal',
             'class': '3',
             'name': 'Fuel Transfer Limpet Controller',
             'rating': 'C'},
 128671257: {'category': 'internal',
             'class': '3',
             'name': 'Fuel Transfer Limpet Controller',
             'rating': 'B'},
 128671258: {'category': 'internal',
             'class': '3',
             'name': 'Fuel Transfer Limpet Controller',
             'rating': 'A'},
 128671259: {'category': 'internal',
             'class': '5',
             'name': 'Fuel Transfer Limpet Controller',
             'rating': 'E'},
 128671260: {'category': 'internal',
             'class': '5',
             'name': 'Fuel Transfer Limpet Controller',
             'rating': 'D'},
 128671261: {'category': 'internal',
             'class': '5',
             'name': 'Fuel Transfer Limpet Controller',
             'rating': 'C'},
 128671262: {'category': 'internal',
             'class': '5',
             'name': 'Fuel Transfer Limpet Controller',
             'rating': 'B'},
 128671263: {'category': 'internal',
             'class': '5',
             'name': 'Fuel Transfer Limpet Controller',
             'rating': 'A'},
 128671264: {'category': 'internal',
             'class': '7',
             'name': 'Fuel Transfer Limpet Controller',
             'rating': 'E'},
 128671265: {'category': 'internal',
             'class': '7',
             'name': 'Fuel Transfer Limpet Controller',
             'rating': 'D'},
 128671266: {'category': 'internal',
             'class': '7',
             'name': 'Fuel Transfer Limpet Controller',
             'rating': 'C'},
 128671267: {'category': 'internal',
             'class': '7',
             'name': 'Fuel Transfer Limpet Controller',
             'rating': 'B'},
 128671268: {'category': 'internal',
             'class': '7',
             'name': 'Fuel Transfer Limpet Controller',
             'rating': 'A'},
 128671269: {'category': 'internal',
             'class': '1',
             'name': 'Prospector Limpet Controller',
             'rating': 'E'},
 128671270: {'category': 'internal',
             'class': '1',
             'name': 'Prospector Limpet Controller',
             'rating': 'D'},
 128671271: {'category': 'internal',
             'class': '1',
             'name': 'Prospector Limpet Controller',
             'rating': 'C'},
 128671272: {'category': 'internal',
             'class': '1',
             'name': 'Prospector Limpet Controller',
             'rating': 'B'},
 128671273: {'category': 'internal',
             'class': '1',
             'name': 'Prospector Limpet Controller',
             'rating': 'A'},
 128671274: {'category': 'internal',
             'class': '3',
             'name': 'Prospector Limpet Controller',
             'rating': 'E'},
 128671275: {'category': 'internal',
             'class': '3',
             'name': 'Prospector Limpet Controller',
             'rating': 'D'},
 128671276: {'category': 'internal',
             'class': '3',
             'name': 'Prospector Limpet Controller',
             'rating': 'C'},
 128671277: {'category': 'internal',
             'class': '3',
             'name': 'Prospector Limpet Controller',
             'rating': 'B'},
 128671278: {'category': 'internal',
             'class': '3',
             'name': 'Prospector Limpet Controller',
             'rating': 'A'},
 128671279: {'category': 'internal',
             'class': '5',
             'name': 'Prospector Limpet Controller',
             'rating': 'E'},
 128671280: {'category': 'internal',
             'class': '5',
             'name': 'Prospector Limpet Controller',
             'rating': 'D'},
 128671281: {'category': 'internal',
             'class': '5',
             'name': 'Prospector Limpet Controller',
             'rating': 'C'},
 128671282: {'category': 'internal',
             'class': '5',
             'name': 'Prospector Limpet Controller',
             'rating': 'B'},
 128671283: {'category': 'internal',
             'class': '5',
             'name': 'Prospector Limpet Controller',
             'rating': 'A'},
 128671284: {'category': 'internal',
             'class': '7',
             'name': 'Prospector Limpet Controller',
             'rating': 'E'},
 128671285: {'category': 'internal',
             'class': '7',
             'name': 'Prospector Limpet Controller',
             'rating': 'D'},
 128671286: {'category': 'internal',
             'class': '7',
             'name': 'Prospector Limpet Controller',
             'rating': 'C'},
 128671287: {'category': 'internal',
             'class': '7',
             'name': 'Prospector Limpet Controller',
             'rating': 'B'},
 128671288: {'category': 'internal',
             'class': '7',
             'name': 'Prospector Limpet Controller',
             'rating': 'A'},
 128671321: {'category': 'hardpoint',
             'class': '3',
             'mount': 'Gimballed',
             'name': 'Fragment Cannon',
             'rating': 'C'},
 128671322: {'category': 'hardpoint',
             'class': '3',
             'mount': 'Turreted',
             'name': 'Fragment Cannon',
             'rating': 'C'},
 128671832: {'category': 'standard',
             'class': '1',
             'name': 'Lightweight Alloy',
             'rating': 'I',
             'ship': 'Diamondback Explorer'},
 128671833: {'category': 'standard',
             'class': '1',
             'name': 'Reinforced Alloy',
             'rating': 'I',
             'ship': 'Diamondback Explorer'},
 128671834: {'category': 'standard',
             'class': '1',
             'name': 'Military Grade Composite',
             'rating': 'I',
             'ship': 'Diamondback Explorer'},
 128671835: {'category': 'standard',
             'class': '1',
             'name': 'Mirrored Surface Composite',
             'rating': 'I',
             'ship': 'Diamondback Explorer'},
 128671836: {'category': 'standard',
             'class': '1',
             'name': 'Reactive Surface Composite',
             'rating': 'I',
             'ship': 'Diamondback Explorer'},
 128672140: {'category': 'standard',
             'class': '1',
             'name': 'Lightweight Alloy',
             'rating': 'I',
             'ship': 'Imperial Eagle'},
 128672141: {'category': 'standard',
             'class': '1',
             'name': 'Reinforced Alloy',
             'rating': 'I',
             'ship': 'Imperial Eagle'},
 128672142: {'category': 'standard',
             'class': '1',
             'name': 'Military Grade Composite',
             'rating': 'I',
             'ship': 'Imperial Eagle'},
 128672143: {'category': 'standard',
             'class': '1',
             'name': 'Mirrored Surface Composite',
             'rating': 'I',
             'ship': 'Imperial Eagle'},
 128672144: {'category': 'standard',
             'class': '1',
             'name': 'Reactive Surface Composite',
             'rating': 'I',
             'ship': 'Imperial Eagle'},
 128672147: {'category': 'standard',
             'class': '1',
             'name': 'Lightweight Alloy',
             'rating': 'I',
             'ship': 'Federal Assault Ship'},
 128672148: {'category': 'standard',
             'class': '1',
             'name': 'Reinforced Alloy',
             'rating': 'I',
             'ship': 'Federal Assault Ship'},
 128672149: {'category': 'standard',
             'class': '1',
             'name': 'Military Grade Composite',
             'rating': 'I',
             'ship': 'Federal Assault Ship'},
 128672150: {'category': 'standard',
             'class': '1',
             'name': 'Mirrored Surface Composite',
             'rating': 'I',
             'ship': 'Federal Assault Ship'},
 128672151: {'category': 'standard',
             'class': '1',
             'name': 'Reactive Surface Composite',
             'rating': 'I',
             'ship': 'Federal Assault Ship'},
 128672154: {'category': 'standard',
             'class': '1',
             'name': 'Lightweight Alloy',
             'rating': 'I',
             'ship': 'Federal Gunship'},
 128672155: {'category': 'standard',
             'class': '1',
             'name': 'Reinforced Alloy',
             'rating': 'I',
             'ship': 'Federal Gunship'},
 128672156: {'category': 'standard',
             'class': '1',
             'name': 'Military Grade Composite',
             'rating': 'I',
             'ship': 'Federal Gunship'},
 128672157: {'category': 'standard',
             'class': '1',
             'name': 'Mirrored Surface Composite',
             'rating': 'I',
             'ship': 'Federal Gunship'},
 128672158: {'category': 'standard',
             'class': '1',
             'name': 'Reactive Surface Composite',
             'rating': 'I',
             'ship': 'Federal Gunship'}
}


# ----------------------------------------------------------------
# Functions.
# ----------------------------------------------------------------


def parse_args():
    '''
    Parse arguments.
    '''
    # Basic argument parsing.
    parser = argparse.ArgumentParser(
        description='EDAPI: Elite Dangerous API Tool',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Version
    parser.add_argument('--version',
                        action='version',
                        version='%(prog)s '+__version__)

    # Debug
    parser.add_argument("--debug",
                        action="store_true",
                        default=False,
                        help="Output additional debug info.")

    # tdpath
    parser.add_argument("--tdpath",
                        default=".",
                        help="Path to the Trade Dangerous root. This is used to\
                        locate the Trade Dangerous python modules and data/\
                        directory.")

    # colors
    default = (platform.system() == 'Windows')
    parser.add_argument("--no-color",
                        dest="nocolor",
                        action="store_true",
                        default=default,
                        help="Disable the use of ansi colors in output.")

    # Base file name.
    parser.add_argument("--basename",
                        default="edapi",
                        help='Base file name. This is used to construct the\
                        cookie and vars file names.')

    # vars file
    parser.add_argument("--vars",
                        action="store_true",
                        default=False,
                        help="Output a file that sets environment variables\
                        for current cargo capacity, credits, and current\
                        system/station.")

    # vars file
    parser.add_argument("--ships",
                        action="store_true",
                        default=False,
                        help="Write shipyards to the TD ShipVendor.csv.")

    # Import from JSON
    parser.add_argument("--import",
                        metavar="FILE",
                        dest="json_file",
                        default=None,
                        help="Import API info from a JSON file instead of the\
                        API. Used mostly for debugging purposes.")

    # Export to JSON
    parser.add_argument("--export",
                        metavar="FILE",
                        default=None,
                        help="Export API response to a file as JSON.")

    # EDDN
    parser.add_argument("--eddn",
                        action="store_true",
                        default=False,
                        help="Post price, shipyards, and outfitting to the \
                        EDDN.")

    # keys
    parser.add_argument("--keys",
                        action="append",
                        nargs="*",
                        help="Instead of normal import, display raw API data\
                        given a set of dictionary keys.")

    # tree
    parser.add_argument("--tree",
                        action="store_true",
                        default=False,
                        help="Used with --keys. If present will print all\
                        content below the specificed key.")

    # Parse the command line.
    args = parser.parse_args()

    # Fixup the tdpath
    if args.tdpath is not '.':
        args.tdpath = os.path.abspath(args.tdpath)

    if args.debug:
        pprint(args)

    return args


def convertSecs(seconds):
    '''
    Convert a number of seconds to a string.
    '''
    if not isinstance(seconds, int):
        return seconds

    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60

    result = "{:2d}s".format(
        seconds
    )

    if minutes or hours:
        result = "{:2d}m ".format(
            minutes
        )+result

    if hours:
        result = "{:2d}h ".format(
            hours
        )+result

    return result


# ----------------------------------------------------------------
# Classes.
# ----------------------------------------------------------------

# Some fun shell colors.
class ansiColors:
    '''
    Simple class for ansi colors
    '''

    defaults = {
        'HEADER': '\033[95m',
        'OKBLUE': '\033[94m',
        'OKGREEN': '\033[92m',
        'WARNING': '\033[93m',
        'FAIL': '\033[91m',
        'ENDC': '\033[00m',
    }

    def __init__(self):
        if args.nocolor:
            self.__dict__.update({n: '' for n in ansiColors.defaults.keys()})
        else:
            self.__dict__.update(ansiColors.defaults)


class EDAPI:
    '''
    A class that handles the Frontier ED API.
    '''

    _agent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 8_1 like Mac OS X) AppleWebKit/600.1.4 (KHTML, like Gecko) Mobile/12B411'  # NOQA
    _baseurl = 'https://companion.orerve.net/'
    _basename = 'edapi'
    _cookiefile = _basename + '.cookies'
    _envfile = _basename + '.vars'

    def __init__(
        self,
        basename='edapi',
        debug=False,
        cookiefile=None,
        json_file=None
    ):
        '''
        Initialize
        '''

        # Build common file names from basename.
        self._basename = basename
        if cookiefile:
            self._cookiefile = cookiefile
        else:
            self._cookiefile = self._basename + '.cookies'

        self._envfile = self._basename + '.vars'

        self.debug = debug

        # If json_file was given, just load that instead.
        if json_file:
            with open(json_file) as file:
                self.profile = json.load(file)
                return

        # if self.debug:
        #     import http.client
        #     http.client.HTTPConnection.debuglevel = 3

        # Setup the HTTP session.
        self.opener = requests.Session()

        self.opener.headers = {
            'User-Agent': self._agent
        }

        # Read/create the cookie jar.
        if os.path.exists(self._cookiefile):
            try:
                with open(self._cookiefile, 'rb') as h:
                    self.opener.cookies = cookiejar_from_dict(pickle.load(h))
            except:
                print('Unable to read cookie file.')

        else:
            with open(self._cookiefile, 'wb') as h:
                pickle.dump(dict_from_cookiejar(self.opener.cookies), h)

        # Grab the commander profile
        response = self._getURI('profile')
        try:
            self.profile = response.json()
        except:
            sys.exit('Unable to parse JSON response for /profile!\
                     Try with --debug and report this.')

    def _getBasicURI(self, uri, values=None):
        '''
        Perform a GET/POST to a URI
        '''

        # POST if data is present, otherwise GET.
        if values is None:
            if self.debug:
                print('GET on: ', self._baseurl+uri)
                print(dict_from_cookiejar(self.opener.cookies))
            response = self.opener.get(self._baseurl+uri)
        else:
            if self.debug:
                print('POST on: ', self._baseurl+uri)
                print(dict_from_cookiejar(self.opener.cookies))
            response = self.opener.post(self._baseurl+uri, data=values)

        if self.debug:
            print('Final URL:', response.url)
            print(dict_from_cookiejar(self.opener.cookies))

        # Save the cookies.
        with open(self._cookiefile, 'wb') as h:
            pickle.dump(dict_from_cookiejar(self.opener.cookies), h)

        # Return the response object.
        return response

    def _getURI(self, uri, values=None):
        '''
        Perform a GET/POST and try to login if needed.
        '''

        # Try the URI. If our credentials are no good, try to
        # login then ask again.
        response = self._getBasicURI(uri, values=values)

        if 'Password' in str(response.text):
            self._doLogin()
            response = self._getBasicURI(uri, values=values)

        if 'Password' in str(response.text):
            sys.exit(textwrap.fill(textwrap.dedent("""\
                Something went terribly wrong. The login credentials
                appear correct, but we are being denied access. Sometimes the
                API is slow to update, so if you are authenticating for the
                first time, wait a minute or so and try again. If this
                persists try deleting your cookies file and starting over.
                """)))

        return response

    def _doLogin(self):
        '''
        Go though the login process
        '''
        # First hit the login page to get our auth cookies set.
        response = self._getBasicURI('')

        # Our current cookies look okay? No need to login.
        if str(response.url).endswith('/'):
            return

        # Perform the login POST.
        print(textwrap.fill(textwrap.dedent("""\
              You do not appear to have any valid login cookies set.
              We will attempt to log you in with your Frontier
              account, and cache your auth cookies for future use.
              THIS WILL NOT STORE YOUR USER NAME AND PASSWORD.
              """)))

        print("\nYour auth cookies will be stored here:")

        print("\n"+self._cookiefile+"\n")

        print(textwrap.fill(textwrap.dedent("""\
            It is advisable that you keep this file secret. It may
            be possible to hijack your account with the information
            it contains.
            """)))

        print(
            "\nIf you are not comfortable with this, "
            "DO NOT USE THIS TOOL."
        )
        print()

        values = {}
        values['email'] = input("User Name (email):")
        values['password'] = getpass.getpass()
        response = self._getBasicURI('user/login', values=values)

        # If we end up being redirected back to login,
        # the login failed.
        if 'Password' in str(response.text):
            sys.exit('Login failed.')

        # Check to see if we need to do the auth token dance.
        if str(response.url).endswith('user/confirm'):
            print()
            print("A verification code should have been sent to your "
                  "email address.")
            print("Please provide that code (case sensitive!)")
            values = {}
            values['code'] = input("Code:")
            response = self._getBasicURI('user/confirm', values=values)

        # The API is sometimes very slow to update sessions. Wait a bit...
        time.sleep(2)

# ----------------------------------------------------------------
# Main.
# ----------------------------------------------------------------


def Main():
    '''
    Main function.
    '''
    # Insert the tdpath to python path so we can find the proper modules to
    # import.
    sys.path.insert(0, args.tdpath)

    # Connect to the API and grab all the info!
    api = EDAPI(debug=args.debug, json_file=args.json_file)

    # User specified --export. Print JSON and exit.
    if args.export:
        with open(args.export, 'w') as outfile:
            json.dump(api.profile, outfile, indent=4, sort_keys=True)
            sys.exit()

    # Colors
    c = ansiColors()

    # User specified the --keys option. Use this to display some subzet of the
    # API response and exit.
    if args.keys is not None:
        # A little legend.
        for key in args.keys[0]:
            print(key, end="->")
        print()

        # Start a the root
        ref = api.profile
        # Try to walk the tree
        for key in args.keys[0]:
            try:
                ref = ref[key]
            except:
                print("key:", key)
                print("not found. Contents at previous key:")
                try:
                    pprint(sorted(ref.keys()))
                except:
                    pprint(ref)
                sys.exit(1)
        # Print whatever we found here.
        try:
            if args.tree:
                pprint(ref)
            else:
                pprint(sorted(ref.keys()))
        except:
            pprint(ref)
        # Exit without doing anything else.
        sys.exit()

    # Sanity check that we are docked
    if not api.profile['commander']['docked']:
        print(c.WARNING+'Commander not docked.'+c.ENDC)
        print(c.FAIL+'Aborting!'+c.ENDC)
        sys.exit(1)

    # Print the commander profile
    print('Commander:', c.OKGREEN+api.profile['commander']['name']+c.ENDC)
    print('Credits  : {:>12,d}'.format(api.profile['commander']['credits']))
    print('Debt     : {:>12,d}'.format(api.profile['commander']['debt']))
    print('Capacity : {} tons'.format(api.profile['ship']['cargo']['capacity']))  # NOQA
    print("+------------+------------------+---+")  # NOQA
    print("|  Rank Type |        Rank Name | # |")  # NOQA
    print("+------------+------------------+---+")  # NOQA
    for rankType in sorted(api.profile['commander']['rank']):
        rank = api.profile['commander']['rank'][rankType]
        if rankType in rank_names:
            try:
                rankName = rank_names[rankType][rank]
            except:
                rankName = "Rank "+str(rank)
        else:
            rankName = ''
        print("| {:>10} | {:>16} | {:1} |".format(
            rankType,
            rankName,
            rank,
            )
        )
    print("+------------+------------------+---+")  # NOQA
    print('Docked:', api.profile['commander']['docked'])

    system = api.profile['lastSystem']['name']
    station = api.profile['lastStarport']['name']
    print('System:', c.OKBLUE+system+c.ENDC)
    print('Station:', c.OKBLUE+station+c.ENDC)

    # Write out an environment file.
    if args.vars:
        print('Writing {}...'.format(api._envfile))
        with open(api._envfile, "w") as myfile:
            myfile.write(
                'export TDFROM="{}/{}"\n'.format(
                    api.profile['lastSystem']['name'],
                    api.profile['lastStarport']['name']
                )
            )
            myfile.write(
                'export TDCREDITS={}\n'.format(
                    api.profile['commander']['credits']
                )
            )
            myfile.write(
                'export TDCAP={}\n'.format(
                    api.profile['ship']['cargo']['capacity']
                )
            )

    # Setup TD
    print('Initializing Trade Dangerous...')
    try:
        import tradeenv
    except:
        sys.exit('Can\'t find Trade Dangerous. Do you need --tdpath?')
    tdenv = tradeenv.TradeEnv()
    if args.tdpath is not '.':
        tdenv.dataDir = args.tdpath+'/data'
    import tradedb
    tdb = tradedb.TradeDB(tdenv)
    import cache
    import csvexport

    # Check to see if this system is in the Stations file
    try:
        station_lookup = tdb.lookupStation(station, system)
    except:
        station_lookup = None

    # The station isn't in the stations file. Add it.
    if not station_lookup:
        print(c.WARNING+'WARNING! Station unknown.'+c.ENDC)
        print('Adding station...')
        lsFromStar = input(
            "Distance from star (enter for 0): "
        ) or 0
        try:
            lsFromStar = int(float(lsFromStar))
        except:
            print("That doesn't seem to be a number. Defaulting to zero.")
            lsFromStar = 0
        blackMarket = input(
            "Black market present (Y, N or enter for ?): "
        ) or '?'
        maxPadSize = input(
            "Max pad size (S, M, L or enter for ?): "
        ) or '?'
        outfitting = input(
            "Outfitting present (Y, N or enter for ?): "
        ) or '?'
        rearm = input(
            "Rearm present (Y, N or enter for ?): "
        ) or '?'
        refuel = input(
            "Refuel present (Y, N or enter for ?): "
        ) or '?'
        repair = input(
            "Repair present (Y, N or enter for ?): "
        ) or '?'
        # This is unreliable, so ask the user.
        if 'commodities' in api.profile['lastStarport']:
            market = 'Y'
        else:
            market = input(
                "Commodity market present (Y, N or enter for ?): "
            ) or '?'
        # This is also unreliable, so ask the user.
        if 'ships' in api.profile['lastStarport']:
            shipyard = 'Y'
        else:
            shipyard = input(
                "Shipyard present (Y, N or enter for ?): "
            ) or '?'
        system_lookup = tdb.lookupSystem(system)
        if tdb.addLocalStation(
            system=system_lookup,
            name=station,
            lsFromStar=lsFromStar,
            blackMarket=blackMarket,
            maxPadSize=maxPadSize,
            market=market,
            shipyard=shipyard,
            outfitting=outfitting,
            rearm=rearm,
            refuel=refuel,
            repair=repair
        ):
            lines, csvPath = csvexport.exportTableToFile(
                tdb,
                tdenv,
                "Station"
            )
            tdenv.NOTE("{} updated.", csvPath)
        station_lookup = tdb.lookupStation(station, system)
    else:
        print(c.OKGREEN+'Station found in station file.'+c.ENDC)

        # See if we need to update the info for this station.
        lsFromStar = station_lookup.lsFromStar
        blackMarket = station_lookup.blackMarket
        maxPadSize = station_lookup.maxPadSize
        market = station_lookup.market
        shipyard = station_lookup.shipyard
        outfitting = station_lookup.outfitting
        rearm = station_lookup.rearm
        refuel = station_lookup.refuel
        repair = station_lookup.repair

        if lsFromStar == 0:
            lsFromStar = input(
                "Update distance from star (enter for 0): "
            ) or 0
            lsFromStar = int(lsFromStar)
        if blackMarket is '?':
            blackMarket = input(
                "Update black market present (Y, N or enter for ?): "
            ) or '?'
        if maxPadSize is '?':
            maxPadSize = input(
                "Update max pad size (S, M, L or enter for ?): "
            ) or '?'
        if outfitting is '?':
            outfitting = input(
                "Update outfitting present (Y, N or enter for ?): "
            ) or '?'
        if rearm is '?':
            rearm = input(
                "Update rearm present (Y, N or enter for ?): "
            ) or '?'
        if refuel is '?':
            refuel = input(
                "Update refuel present (Y, N or enter for ?): "
            ) or '?'
        if repair is '?':
            repair = input(
                "Update repair present (Y, N or enter for ?): "
            ) or '?'
        # This is unreliable, so ask the user if unknown.
        if 'commodities' in api.profile['lastStarport']:
            market = 'Y'
        else:
            if market is '?':
                market = input(
                    "Commodity market present (Y, N or enter for ?): "
                ) or '?'
        # This is also unreliable, so ask the user if unknown.
        if 'ships' in api.profile['lastStarport']:
            shipyard = 'Y'
        else:
            if shipyard is '?':
                shipyard = input(
                    "Shipyard present (Y, N or enter for ?): "
                ) or '?'
        if (
            lsFromStar != station_lookup.lsFromStar or
            blackMarket != station_lookup.blackMarket or
            maxPadSize != station_lookup.maxPadSize or
            market != station_lookup.market or
            shipyard != station_lookup.shipyard or
            outfitting != station_lookup.outfitting or
            rearm != station_lookup.rearm or
            refuel != station_lookup.refuel or
            repair != station_lookup.repair
        ):
            if tdb.updateLocalStation(
                station=station_lookup,
                lsFromStar=lsFromStar,
                blackMarket=blackMarket,
                maxPadSize=maxPadSize,
                market=market,
                shipyard=shipyard,
                outfitting=outfitting,
                rearm=rearm,
                refuel=refuel,
                repair=repair
            ):
                lines, csvPath = csvexport.exportTableToFile(
                    tdb,
                    tdenv,
                    "Station"
                )
                tdenv.NOTE("{} updated.", csvPath)

    # If a shipyard exists, update the ship vendor csv
    eddn_ships = []
    if 'ships' in api.profile['lastStarport']:
        print(c.OKGREEN+'Found a shipyard at this station.'+c.ENDC)
        ships = list(
            api.profile['lastStarport']['ships']['shipyard_list'].keys()
        )
        for ship in api.profile['lastStarport']['ships']['unavailable_list']:
            ships.append(ship['name'])

        for ship in ships:
            eddn_ships.append(eddn_ship_names[ship])

        if args.ships:
            print(c.OKBLUE+'Updating ShipVendor.csv...'+c.ENDC)
            db = tdb.getDB()
            for ship in ships:
                ship_lookup = tdb.lookupShip(ship_names[ship])
                db.execute("""
                           REPLACE INTO ShipVendor
                           (ship_id, station_id)
                           VALUES
                           (?, ?)
                           """,
                           (ship_lookup.ID, station_lookup.ID))
                db.commit()
            tdenv.NOTE("Updated {} ships in {} shipyard.", len(ships), station)
            lines, csvPath = csvexport.exportTableToFile(
                tdb,
                tdenv,
                "ShipVendor",
            )
            tdenv.NOTE("{} updated.", csvPath)

    # Some sanity checking on the market
    if 'commodities' not in api.profile['lastStarport']:
        print(
            c.FAIL +
            'This station does not appear to have a commodity market.' +
            c.ENDC
        )
        print('Keys for this station:')
        pprint(api.profile['lastStarport'].keys())
        sys.exit(1)

    # Station exists. Import.
    # Grab the old prices so we can print a comparison.
    db = tdb.getDB()
    oldPrices = {n: (s, b) for (n, s, b) in db.execute(
        """
        SELECT
            Item.name,
            StationItem.demand_price,
            StationItem.supply_price
        FROM
            StationItem,
            System,
            Station,
            Item
        WHERE
            Item.item_id = StationItem.item_id AND
            System.name = ? AND
            Station.name = ? AND
            System.system_id = Station.system_id AND
            Station.station_id = StationItem.station_id
        ORDER BY Item.ui_order
        """,
        (
            system,
            station
        )
    )}

    print('Writing trade data...')

    # Find a temp file
    f = tempfile.NamedTemporaryFile(delete=False)
    if args.debug:
        print('Temp file is:', f.name)

    # Write out trade data
    header = False
    f.write("@ {}/{}\n".format(system, station).encode('UTF-8'))
    eddn_market = []
    for commodity in api.profile['lastStarport']['commodities']:
        if commodity['categoryname'] in cat_ignore:
            continue

        if commodity['name'] in comm_ignore:
            continue

        if commodity['categoryname'] in cat_correct:
            commodity['categoryname'] = cat_correct[commodity['categoryname']]

        if commodity['name'] in comm_correct:
            commodity['name'] = comm_correct[commodity['name']]

        def commodity_int(key):
            try:
                commodity[key] = int(commodity[key])
            except (ValueError, KeyError):
                commodity[key] = 0

        commodity_int('stock')
        commodity_int('demand')
        commodity_int('demandBracket')
        commodity_int('stockBracket')
        commodity_int('buyPrice')
        commodity_int('sellPrice')

        # Populate EDDN
        if args.eddn:
            eddn_market.append(
                {
                    "name": commodity['name'],
                    "buyPrice": commodity['buyPrice'],
                    "supply": commodity['stock'],
                    "supplyLevel": eddn.EDDN._levels[commodity['stockBracket']],  # NOQA
                    "sellPrice": commodity['sellPrice'],
                    "demand": commodity['demand'],
                    "demandLevel": eddn.EDDN._levels[commodity['demandBracket']]  # NOQA
                }
            )

        f.write(
            "\t+ {}\n".format(
                commodity['categoryname']
            ).encode('UTF-8')
        )

        # If stock is zero, list it as unavailable.
        # If the stockBracket is zero, ignore any stock.
        if not commodity['stock'] or not commodity['stockBracket']:
            commodity['stock'] = '-'
        else:
            demand = bracket_levels[commodity['stockBracket']]
            commodity['stock'] = str(commodity['stock'])+demand

        # If demand is zero, list as unknown.
        if not (commodity['demand'] and commodity['demandBracket']):
            commodity['demand'] = '?'
        else:
            demand = bracket_levels[commodity['demandBracket']]
            commodity['demand'] = str(commodity['demand'])+demand

        # Print price differences
        oldCom = oldPrices.get(commodity['name'], (0, 0))
        diffSell = commodity['sellPrice'] - oldCom[0]
        diffBuy = commodity['buyPrice'] - oldCom[1]

        # Only print if the prices changed.
        if (diffSell != 0 or diffBuy != 0):
            if header is False:
                header = True
                print("Price fluctuations:")
                print("{:->25}-+{:->14}---+{:->14}---+".format(
                    'Commodity',
                    'Sell Price',
                    'Buy Price'
                ))
            if diffSell < 0:
                sellColor = c.FAIL
            elif diffSell > 0:
                sellColor = c.OKGREEN
            else:
                sellColor = c.ENDC
            if diffBuy > 0:
                buyColor = c.FAIL
            elif diffBuy < 0:
                buyColor = c.OKGREEN
            else:
                buyColor = c.ENDC
            if args.nocolor:
                s = "{:>25} | {:>5}{:<8} {} | {:>5}{:<8} {} |"
            else:
                s = "{:>25} | {:>5}{:<18} {} | {:>5}{:<18} {} |"
            print(s.format(
                commodity['name'],
                commodity['sellPrice'],
                '('+sellColor+"{:+d}".format(diffSell)+c.ENDC+')',
                bracket_levels[commodity['demandBracket']],
                commodity['buyPrice'],
                '('+buyColor+"{:+d}".format(diffBuy)+c.ENDC+')',
                bracket_levels[commodity['stockBracket']],
                )
            )

        f.write(
            "\t\t{} {} {} {} {}\n".format(
                commodity['name'],
                commodity['sellPrice'],
                commodity['buyPrice'],
                commodity['demand'],
                commodity['stock'],
            ).encode('UTF-8')
        )
    f.close()
    if header is True:
        print("{:->25}-+{:->14}---+{:->14}---+".format(
            '',
            '',
            ''
        ))

    # All went well. Try the import.
    print('Importing into Trade Dangerous...')

    # TD likes to use Path objects
    fpath = Path(f.name)

    # Ask TD to parse the system from the temp file.
    cache.importDataFromFile(tdb, tdenv, fpath)

    # Remove the temp file.
    fpath.unlink()

    # Post to EDDN
    if args.eddn:
        print('Posting prices to EDDN...')
        con = eddn.EDDN(
            api.profile['commander']['name'],
            'EDAPI',
            __version__
        )
        con._debug = args.debug
        con.publishCommodities(
            system,
            station,
            eddn_market
        )
        if (eddn_ships):
            print('Posting shipyard to EDDN...')
            con.publishShipyard(
                system,
                station,
                eddn_ships
            )

        eddn_modules = []
        for key in api.profile['lastStarport'].get('modules', ()):
            key = int(key)
            if key in modules:
                eddn_modules.append(modules[key])
        if len(eddn_modules):
            print('Posting outfitting to EDDN...')
            con.publishOutfitting(
                system,
                station,
                eddn_modules
            )

    # No errors.
    return False


# ----------------------------------------------------------------
# __main__
# ----------------------------------------------------------------
if __name__ == "__main__":
    '''
    Command line invocation.
    '''

    try:
        # Parse any command line arguments.
        args = parse_args()

        # Command line overrides
        if args.debug is True:
            print('***** Debug mode *****')

        # Execute the Main() function and return results.
        sys.exit(Main())
    except SystemExit as e:
        # Clean exit, provide a return code.
        sys.exit(e.code)
    except:
        # Handle all other exceptions.
        ErrStr = traceback.format_exc()
        print('Exception in main loop. Exception info below:')
        sys.exit(ErrStr)

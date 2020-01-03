#!/usr/bin/env python
# ----------------------------------------------------------------
# Elite: Dangerous API Tool
# ----------------------------------------------------------------

from pprint import pprint
import json
import sys
import traceback

import api.companion as companion
import api.parse as parse
import eddn.eddn as eddn

from utils.args import parse_args
from utils.const import cat_ignore, bracket_levels, rank_names
from utils.ansiColors import ansiColors
from utils.print_profile import print_profile


__version_info__ = ('4', '3', '1')
__version__ = '.'.join(__version_info__)


def Main(args):
    '''
    Main function.
    '''
    # Connect to the API and grab all the info!
    api = companion.EDAPI(
        debug=args.debug,
        json_file=args.json_file,
        login=args.login
    )

    # User specified --export. Print JSON and exit.
    if args.export:
        with open(args.export, 'w') as outfile:
            json.dump(api.profile, outfile, indent=4, sort_keys=True)
            sys.exit()

    # Colors
    c = ansiColors(args)

    # User specified the --keys option. Use this to display some subset of the
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

    print_profile(api, c)

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

    # Process the commodities market.
    commodities = parse.get_commodities(api)

    # Process the station economies.
    economies = parse.get_economies(api)

    # Process the station prohibited commodities.
    prohibited = [c for c in api.profile['lastStarport']['prohibited'].values()] #NOQA

    # Process shipyard.
    ships = parse.get_ships(api)

    # Process outfitting.
    modules = parse.get_modules(api)

    # Publish to EDDN
    if args.eddn:
        # Open a connection.
        con = eddn.EDDN(
            api.profile['commander']['name'],
            not args.hash,
            'EDAPI',
            __version__
        )
        con._debug = args.debug

        if commodities:
            print('Posting commodities to EDDN...')
            con.publishCommodities(system, station, commodities, economies, prohibited)

        if ships:
            print('Posting shipyard to EDDN...')
            con.publishShipyard(system, station, ships)

        if modules:
            print('Posting outfitting to EDDN...')
            con.publishOutfitting(system, station, modules)

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
        args = parse_args(__version__)

        # Command line overrides
        if args.debug is True:
            print('***** Debug mode *****')

        # Execute the Main() function and return results.
        sys.exit(Main(args))
    except SystemExit as e:
        # Clean exit, provide a return code.
        sys.exit(e.code)
    except:
        # Handle all other exceptions.
        ErrStr = traceback.format_exc()
        print('Exception in main loop. Exception info below:')
        sys.exit(ErrStr)

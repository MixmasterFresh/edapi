# ----------------------------------------------------------------
# Import plugin that downloads market and ship vendor data from the
# Elite Dangerous mobile API.
# ----------------------------------------------------------------

import cache
import csvexport
import getpass
import http.client
import http.cookiejar
import json
import pathlib
import plugins
import sys
import textwrap
import urllib.parse
import urllib.request as urllib2

# ----------------------------------------------------------------
# Deal with some differences in names between TD, ED and the API.
# ----------------------------------------------------------------

bracket_levels = ('-', 'L', 'M', 'H')

# This translates what the API calls a ship into what TD calls a
# ship.

ship_names = {
    'Adder': 'Adder',
    'Anaconda': 'Anaconda',
    'Asp': 'Asp',
    'CobraMkIII': 'Cobra',
    'Eagle': 'Eagle',
    'Empire_Fighter': 'Empire_Fighter',
    'Empire_Trader': 'Clipper',
    'Federation_Dropship': 'Dropship',
    'Federation_Fighter': 'Federation_Fighter',
    'Hauler': 'Hauler',
    'Orca': 'Orca',
    'Python': 'Python',
    'SideWinder': 'Sidewinder',
    'Type6': 'Type 6',
    'Type7': 'Type 7',
    'Type9': 'Type 9',
    'Viper': 'Viper',
}

# Categories to ignore. Drones end up here. No idea what they are.
cat_ignore = [
    'NonMarketable',
]

# TD has different names for these.
cat_correct = {
    'Narcotics': 'Legal Drugs'
}

# TD has different names for these.
comm_correct = {
    'Agricultural Medicines': 'Agri-Medicines',
    'Atmospheric Extractors': 'Atmospheric Processors',
    'Auto Fabricators': 'Auto-Fabricators',
    'Basic Narcotics': 'Narcotics',
    'Bio Reducing Lichen': 'Bioreducing Lichen',
    'Hazardous Environment Suits': 'H.E. Suits',
    'Heliostatic Furnaces': 'Microbial Furnaces',
    'Marine Supplies': 'Marine Equipment',
    'Non Lethal Weapons': 'Non-Lethal Weapons',
    'Terrain Enrichment Systems': 'Land Enrichment Systems',
}


class EDAPI:
    '''
    A class that handles the Frontier ED API.
    '''

    _agent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 8_1 like Mac OS X) AppleWebKit/600.1.4 (KHTML, like Gecko) Mobile/12B411'  # NOQA
    _baseurl = 'https://companion.orerve.net/'

    def __init__(self, cookiefile):
        '''
        Initialize
        '''

        self._cookiefile = cookiefile

        # Create the cookie jar.
        self.cookie = http.cookiejar.MozillaCookieJar(self._cookiefile)
        try:
            self.cookie.load(ignore_discard=True, ignore_expires=True)
        except:
            self.cookie.save(ignore_discard=True, ignore_expires=True)

        # Setup a custom opener.
        self.opener = urllib2.build_opener(
            urllib2.HTTPCookieProcessor(self.cookie),
            urllib2.HTTPRedirectHandler(),
            urllib2.HTTPHandler(),
            urllib2.HTTPSHandler(),
        )

        self.opener.addheaders = [
            ('User-Agent', self._agent),
        ]

        urllib2.install_opener(self.opener)

        # Grab the commander profile
        response = self._getURI('profile').read().decode()
        try:
            self.profile = json.loads(response)
        except:
            sys.exit('Unable to parse JSON response for /profile!')

    def _getBasicURI(self, uri, values=None):
        '''
        Perform a GET/POST to a URI with POST encoding and cookie handling.
        '''

        # Encode any post variables.
        if values is None:
            data = None
        else:
            data = urllib.parse.urlencode(values)
            data = data.encode('utf-8')

        # Open the URL.
        if data is None:
                response = self.opener.open(self._baseurl+uri)
        else:
                response = self.opener.open(self._baseurl+uri, data)

        # Save the cookies.
        self.cookie.save(ignore_discard=True, ignore_expires=True)

        # Return the response object.
        return response

    def _getURI(self, uri, values=None):
        '''
        Perform a GET/POST and make sure the login
        cookies are valid
        '''

        # Try the URL. If our credentials are no good, try to
        # login then ask again.

        response = self._getBasicURI(uri, values=values)

        if str(response.url).endswith('user/login'):
            self._doLogin()
            response = self._getBasicURI(uri, values)

        if str(response.url).endswith('user/login'):
            sys.exit(
                "Something went terribly wrong. The login credentials appear"
                "correct, but we are being denied access.\n"
            )

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
            "DO NOT USE THIS PLUGIN."
        )
        print()

        values = {}
        values['email'] = input("User Name (email): ")
        values['password'] = getpass.getpass()
        response = self._getBasicURI('user/login', values=values)

        # If we end up being redirected back to login,
        # the login failed.
        if str(response.url).endswith('user/login'):
            sys.exit('Login failed.')

        # Check to see if we need to do the auth token dance.
        if str(response.url).endswith('user/confirm'):
            print()
            print(
                "A verification code should have been sent to your"
                "email address."
            )
            print("Please provide that code (case sensitive!)")
            values = {}
            values['code'] = input("Code: ")
            response = self._getBasicURI('user/confirm', values=values)


class ImportPlugin(plugins.ImportPluginBase):
    """
    Plugin that downloads market and ship vendor data from the Elite Dangerous
    mobile API.
    """

    cookieFile = "edapi.cookies"

    def __init__(self, tdb, tdenv):
        super().__init__(tdb, tdenv)

        self.filename = self.defaultImportFile
        cookieFilePath = pathlib.Path(ImportPlugin.cookieFile)
        self.cookiePath = tdb.dataPath / cookieFilePath

    def run(self):
        tdb, tdenv = self.tdb, self.tdenv

        # Connect to the API, authenticate, and pull down the commander
        # /profile.
        api = EDAPI(str(self.cookiePath))

        # Sanity check that the commander is docked. Otherwise we will get a
        # mismatch between the last system and last station.
        if not api.profile['commander']['docked']:
            print('Commander not docked. Aborting!')
            return False

        # Figure out where we are.
        system = api.profile['lastSystem']['name']
        station = api.profile['lastStarport']['name']
        place = '@{}/{}'.format(system.upper(), station)
        print(place)

        # Reload the cache.
        tdenv.DEBUG0("Checking the cache")
        tdb.close()
        tdb.reloadCache()
        tdb.load(
            maxSystemLinkLy=tdenv.maxSystemLinkLy,
        )
        tdb.close()

        # Check to see if this system is in the Stations file
        try:
            station_lookup = tdb.lookupPlace(place)
        except LookupError:
            station_lookup = None

        print(station_lookup)

        # The station isn't known. Add it.
        if not station_lookup:
            print('Station unknown.')
            print('Adding:', place)
            lsFromStar = input(
                "Distance from star (enter for 0): "
            ) or 0
            lsFromStar = int(lsFromStar)
            blackMarket = input(
                "Black market present (Y, N or enter for ?): "
            ) or '?'
            maxPadSize = input(
                "Max pad size (S, M, L or enter for ?): "
            ) or '?'
            system_lookup = tdb.lookupSystem(system)
            if tdb.addLocalStation(
                system=system_lookup,
                name=station,
                lsFromStar=lsFromStar,
                blackMarket=blackMarket,
                maxPadSize=maxPadSize,
            ):
                lines, csvPath = csvexport.exportTableToFile(
                    tdb,
                    tdenv,
                    "Station"
                )
                tdenv.NOTE("{} updated.", csvPath)
                station_lookup = tdb.lookupPlace(place)
        else:
            # See if we need to update the info for this station.
            lsFromStar = station_lookup.lsFromStar
            blackMarket = station_lookup.blackMarket
            maxPadSize = station_lookup.maxPadSize

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

            if (
                lsFromStar != station_lookup.lsFromStar or
                blackMarket != station_lookup.blackMarket or
                maxPadSize != station_lookup.maxPadSize
            ):
                if tdb.updateLocalStation(
                    station=station_lookup,
                    lsFromStar=lsFromStar,
                    blackMarket=blackMarket,
                    maxPadSize=maxPadSize,
                ):
                    lines, csvPath = csvexport.exportTableToFile(
                        tdb,
                        tdenv,
                        "Station",
                    )
                    tdenv.NOTE("{} updated.", csvPath)

        # If a shipyard exists, update the ship vendor list.
        if 'ships' in api.profile['lastStarport']:
            ships = list(
                api.profile['lastStarport']['ships']['shipyard_list'].keys()
            )
            for ship in api.profile['lastStarport']['ships']['unavailable_list']:
                ships.append(ship['name'])
            db = tdb.getDB()
            for ship in ships:
                ship_lookup = tdb.lookupShip(ship_names[ship])
                db.execute(
                    """
                    REPLACE INTO ShipVendor
                    (ship_id, station_id)
                    VALUES
                    (?, ?)
                    """,
                    [ship_lookup.ID, station_lookup.ID]
                )
                db.commit()
            tdenv.NOTE("Updated {} ships in {} shipyard.", len(ships), place)
            lines, csvPath = csvexport.exportTableToFile(
                tdb,
                tdenv,
                "ShipVendor",
            )

        # Some sanity checking on the market.
        if 'commodities' not in api.profile['lastStarport']:
            print(
                'The API did not return a commodity market for this station.'
            )
            print(
                'If you think this is wrong, try again. The API will '
                'occasionally skip the market.'
            )
            return False

        # Create the import file.
        with open(self.filename, 'w', encoding="utf-8") as f:
            f.write("@ {}/{}\n".format(system, station))
            for commodity in api.profile['lastStarport']['commodities']:
                if commodity['categoryname'] in cat_ignore:
                    continue
                if commodity['categoryname'] in cat_correct:
                    commodity['categoryname'] = cat_correct[commodity['categoryname']]
                if commodity['name'] in comm_correct:
                    commodity['name'] = comm_correct[commodity['name']]

                f.write("\t+ {}\n".format(commodity['categoryname']))

                # If stock is zero, list it as unavailable.
                if commodity['stock'] == 0:
                    commodity['stock'] = '-'
                else:
                    demand = bracket_levels[int(commodity['stockBracket'])]
                    commodity['stock'] = str(int(commodity['stock']))+demand

                # If demand is zero, zero out the sell price.
                if commodity['demand'] == 0:
                    commodity['demand'] = '?'
                    commodity['sellPrice'] = 0
                else:
                    demand = bracket_levels[int(commodity['demandBracket'])]
                    commodity['demand'] = str(int(commodity['demand']))+demand

                f.write(
                    "\t\t{} {} {} {} {}\n".format(
                        commodity['name'],
                        commodity['sellPrice'],
                        commodity['buyPrice'],
                        commodity['demand'],
                        commodity['stock'],
                    ))

        tdenv.ignoreUnknown = True

        cache.importDataFromFile(
            tdb,
            tdenv,
            pathlib.Path(self.filename),
        )

        # We did all the work
        return False

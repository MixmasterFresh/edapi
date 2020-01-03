from utils.const import cat_ignore

def commodity_int(number):
    try:
        ret = int(float(number)+0.5)
    except (ValueError, KeyError):
        ret = 0
    return ret


def economy_number(number):
    try:
        ret = float(number)
    except (ValueError, KeyError):
        ret = 0
    return ret


def get_commodities(api):
    commodities = []
    if 'commodities' in api.profile['lastStarport']:
        for commodity in api.profile['lastStarport']['commodities']:
            # Ignore any special categories.
            if commodity['categoryname'] in cat_ignore:
                continue

            # Ignore any illegal commodities per schema.
            if commodity.get('legality', '') != '':
                continue

            itemEDDN = {
                "name":          commodity['name'],
                "meanPrice":     commodity_int(commodity['meanPrice']),
                "buyPrice":      commodity_int(commodity['buyPrice']),
                "stock":         commodity_int(commodity['stock']),
                "stockBracket":  commodity['stockBracket'],
                "sellPrice":     commodity_int(commodity['sellPrice']),
                "demand":        commodity_int(commodity['demand']),
                "demandBracket": commodity['demandBracket'],
            }
            if len(commodity['statusFlags']) > 0:
                itemEDDN["statusFlags"] = commodity['statusFlags']
            commodities.append(itemEDDN)
    return commodities


def get_economies(api):
    economies = []
    if 'economies' in api.profile['lastStarport']:
        for economy in api.profile['lastStarport']['economies'].values():
            itemEDDN = {
                "name":         economy['name'],
                "proportion":   economy_number(economy['proportion']),
            }
            economies.append(itemEDDN)
    return economies

def get_ships(api):
    ships = []
    if 'ships' in api.profile['lastStarport']:
        # Ships that can be purchased.
        if 'shipyard_list' in api.profile['lastStarport']['ships']:
            if len(api.profile['lastStarport']['ships']['shipyard_list']):
                for ship in api.profile['lastStarport']['ships']['shipyard_list'].values():  # NOQA
                    # Add to EDDN.
                    ships.append(ship['name'])

        # Ships that are restricted.
        if 'unavailable_list' in api.profile['lastStarport']['ships']:
            for ship in api.profile['lastStarport']['ships']['unavailable_list']:  # NOQA
                # Add to EDDN.
                ships.append(ship['name'])
    return sorted(ships)

def get_modules(api):
    modules = []
    if 'modules' in api.profile['lastStarport']:
        # For EDDN, only add non-commander specific items that can be
        # purchased.
        # https://github.com/EDSM-NET/EDDN/wiki
        for module in api.profile['lastStarport']['modules'].values():
            if (
                module.get('sku', None) in (
                    None,
                    'ELITE_HORIZONS_V_PLANETARY_LANDINGS'
                ) and
                (
                    module['name'].startswith(('Hpt_', 'Int_')) or
                    module['name'].find('_Armour_') > 0
                )
            ):
                modules.append(module['name'])
    return sorted(modules)

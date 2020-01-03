import argparse
from pprint import pprint
import platform

def parse_args(version):
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
                        version='%(prog)s ' + version)

    # Debug
    parser.add_argument("--debug",
                        action="store_true",
                        default=False,
                        help="Output additional debug info.")

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
                        for credits and current system/station.")

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

    # Hashing CMDR name
    parser.add_argument("--hash",
                        action="store_true",
                        default=False,
                        help="Obfuscate commander name for EDDN.")

    # Force login
    parser.add_argument("--login",
                        action="store_true",
                        default=False,
                        help="Clear any cached user login cookies and force\
                        login. (Doesn't clear the machine token)")

    # Parse the command line.
    args = parser.parse_args()

    if args.debug:
        pprint(args)

    return args

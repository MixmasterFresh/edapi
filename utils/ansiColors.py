# Some fun shell colors.
class ansiColors:
    '''
    Simple class for ansi colors
    '''

    HEADER = ''
    OKBLUE = '',
    OKGREEN = '',
    WARNING = '',
    FAIL = '',
    ENDC = '',

    defaults = {
        'HEADER': '\033[95m',
        'OKBLUE': '\033[94m',
        'OKGREEN': '\033[92m',
        'WARNING': '\033[93m',
        'FAIL': '\033[91m',
        'ENDC': '\033[00m',
    }

    def __init__(self, args):
        if not args.nocolor:
            self.__dict__.update(ansiColors.defaults)

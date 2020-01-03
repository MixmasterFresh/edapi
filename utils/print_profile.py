from const import rank_names

def print_profile(api, c):
    # Print the commander profile
    print('Commander:', c.OKGREEN+api.profile['commander']['name']+c.ENDC)
    print('Credits  : {:>12,d}'.format(api.profile['commander']['credits']))
    print('Debt     : {:>12,d}'.format(api.profile['commander']['debt']))
    print("+------------+----------------------+---+")  # NOQA
    print("|  Rank Type |            Rank Name | # |")  # NOQA
    print("+------------+----------------------+---+")  # NOQA
    for rankType in sorted(api.profile['commander']['rank']):
        rank = api.profile['commander']['rank'][rankType]
        if rankType in rank_names:
            try:
                rankName = rank_names[rankType][rank]
            except:
                rankName = "Rank "+str(rank)
        else:
            rankName = ''
        print("| {:>10} | {:>20} | {:1} |".format(
            rankType,
            rankName,
            rank,
            )
        )
    print("+------------+----------------------+---+")  # NOQA
    print('Docked:', api.profile['commander']['docked'])

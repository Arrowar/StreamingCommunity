from StreamingCommunity.run import load_search_functions


def get_sites():
    search_functions = load_search_functions()
    sites = []
    for alias, (_, use_for) in search_functions.items():
        sites.append(
            {
                "index": len(sites),
                "name": alias.split("_")[0],
                "flag": alias[:3].upper(),
            }
        )
    return sites


sites = get_sites()

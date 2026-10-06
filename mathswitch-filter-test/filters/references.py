import config


def references_filter(name, decl, ctx):
    return decl.get("refs", 0) >= config.REF_MIN

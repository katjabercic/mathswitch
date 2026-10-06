import config


def kind_filter(name, decl, ctx):
    return decl["kind"] in config.CONCEPT_KINDS

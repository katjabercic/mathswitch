import config


def _blocked_component(component):
    return (
        component in config.BLOCKED_NAME_COMPONENTS
        or component.startswith(config.BLOCKED_COMPONENT_PREFIXES)
        or component.isdigit()
        or component.startswith("«")  # notation / syntax, e.g. «term_+_»
    )


def namespace_filter(name, decl, ctx):
    module = decl["module"]
    if any(
        module == p or module.startswith(p + "/")
        for p in config.BLOCKED_MODULE_PREFIXES
    ):
        return False
    return not any(_blocked_component(c) for c in name.split("."))

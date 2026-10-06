import re

import config

_MARKUP = re.compile(r"[`*_#\[\]()$]")


def normalize_doc(doc):
    return " ".join(_MARKUP.sub(" ", doc).split())


def docstring_filter(name, decl, ctx):
    doc = decl.get("doc")
    if not doc:
        return False
    text = normalize_doc(doc)
    if len(text) < config.MIN_DOC_LEN:
        return False
    # "`Foo.bar`" or "The `bar`." restating only the name is trivial
    short = name.rsplit(".", 1)[-1]
    remaining = text.replace(name, "").replace(short, "")
    return len(normalize_doc(remaining)) >= config.MIN_DOC_LEN // 2

"""Paths and thresholds for the Mathlib concept-filter experiment."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
WEB_DIR = REPO_ROOT / "web"
DATA_DIR = ROOT / "data"
REPORT_DIR = ROOT / "report"

MATHLIB_REPO = "https://github.com/leanprover-community/mathlib4.git"
MATHLIB_DIR = DATA_DIR / "mathlib4"
DECLARATIONS_JSON = "mathlib-declarations.json"
SOURCE_INDEX_JSON = DATA_DIR / "source_index.json"
RESULTS_JSON = DATA_DIR / "results.json"
LLM_CACHE = DATA_DIR / "llm_cache.jsonl"
REPORT_HTML = REPORT_DIR / "index.html"

DOCS_URL = "https://leanprover-community.github.io/mathlib4_docs/"

# Candidate universe: same default as web/slurper/source_mathlib.py
UNIVERSE_PACKAGES = frozenset({"Mathlib"})
UNIVERSE_KINDS = frozenset({"def", "structure", "class", "inductive"})

# docstring filter
MIN_DOC_LEN = 40

# namespace filter
BLOCKED_MODULE_PREFIXES = (
    "Mathlib/Tactic",
    "Mathlib/Util",
    "Mathlib/Init",
    "Mathlib/Lean",
    "Mathlib/Meta",
    "Mathlib/Deprecated",
    "Mathlib/Testing",
    "Mathlib/Linter",
    "Mathlib/Mathport",
    "Mathlib/Control",
)
BLOCKED_NAME_COMPONENTS = frozenset(
    {"Tactic", "Meta", "Lean", "Mathlib", "Simps", "Linter", "Elab", "Parser"}
)
BLOCKED_COMPONENT_PREFIXES = ("_", "proof_", "match_", "aux", "eq_")

# references filter
REF_MIN = 10

# kind filter
CONCEPT_KINDS = frozenset({"structure", "class", "inductive", "def"})

# llm_judge filter (uses web/categorizer/llm_service.py)
LLM_TYPE = "OLLAMA_QWEN25_7B"
LLM_SAMPLE = 1000
LLM_SEED = 42
LLM_DOC_CHARS = 300

# report
EXAMPLES_PER_CELL = 100
EXAMPLES_SEED = 0

GROUND_TRUTH_FILES = ("overview.yaml", "undergrad.yaml", "100.yaml", "1000.yaml")

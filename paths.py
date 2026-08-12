"""Central path configuration for the Lloyds SME lead-scoring project.

Import this instead of hardcoding absolute paths, so the project runs on ANY
machine (yours, a teammate's, the client's) regardless of where it's checked out
or which directory the notebook happens to be running from.

Usage in a notebook (any subfolder — API/, API/GDELT/, Model/, ...):

    import sys
    from pathlib import Path
    ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "API").is_dir())
    sys.path.insert(0, str(ROOT))
    from paths import SME_CSV, CHARGES_CSV, PANEL_CSV     # etc.

Usage in a plain script:

    from paths import SME_CSV, PANEL_CSV

All names below are pathlib.Path objects. Build sub-paths with `/`, e.g.
`CH_DATA / "charges_history.csv"` — never with string `+`.
"""

from pathlib import Path


def find_root(start=None):
    """Walk up from `start` (default: cwd) to the project root.

    The root is the folder holding API/ and Model/ (also normally the git root),
    so this resolves correctly whether the caller sits in API/, API/GDELT/,
    Model/, or the root itself.
    """
    start = Path(start).resolve() if start else Path.cwd().resolve()
    for cand in [start, *start.parents]:
        if (cand / "API").is_dir() and (cand / "Model").is_dir():
            return cand
        if (cand / ".git").exists() and (cand / "API").is_dir():
            return cand
    raise RuntimeError(
        f"Could not locate the project root from {start}. Expected an ancestor "
        "directory containing both 'API/' and 'Model/'."
    )


ROOT = find_root()

# --- top-level folders -----------------------------------------------------
API_DIR   = ROOT / "API"
MODEL_DIR = ROOT / "Model"
ENV_FILE  = ROOT / ".env"                      # Companies House API keys

# --- Companies House -------------------------------------------------------
CH_DIR          = API_DIR / "CompaniesHouse"
CH_DATA         = CH_DIR / "company_data"
CHARGE_JSON_DIR = CH_DIR / "company_info_json"          # per-company charge/filing JSON

ACCTYPE_CSV = CH_DATA / "company_with_acctype" / "com_names_with_acctype_test.csv"
SME_CSV     = CH_DATA / "company_sme_with_acctype" / "com_names_sme_test.csv"
CHARGES_CSV = CH_DATA / "charges_history.csv"           # label source (is_lloyds)
FILINGS_CSV = CH_DATA / "filings_history.csv"           # Stage 6 output (may not exist yet)

FINAL_DATA            = CH_DATA / "Final data"
LEGACY_CSV            = FINAL_DATA / "11_7_26.csv"
POSTCODE_BACKFILL_SRC = FINAL_DATA / "11_7_26_with_context_media.csv"

# --- GDELT -----------------------------------------------------------------
GDELT_DIR   = API_DIR / "GDELT"
GDELT_CACHE = GDELT_DIR / "BigQuery Cache files"
MEDIA_INDEX = GDELT_CACHE / "context_media_index_104w.parquet"

# --- modelling tables / outputs --------------------------------------------
PANEL_CSV = API_DIR / "panel.csv"          # per (company, cutoff) panel
FLAT_CSV  = API_DIR / "flat.csv"           # one row per company (look-alike)
LEADS_CSV = API_DIR / "leads_flat.csv"     # ranked RM lead list


if __name__ == "__main__":
    # `python paths.py` prints every path and whether it exists — a quick check
    # that the project is wired up correctly on this machine.
    print(f"ROOT = {ROOT}\n")
    for name, val in sorted(globals().items()):
        if name.isupper() and isinstance(val, Path):
            print(f"  {'OK  ' if val.exists() else 'MISS'}  {name:<22} {val}")

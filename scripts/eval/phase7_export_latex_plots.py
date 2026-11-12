"""Phase 7 entry point as named in the README.

Run: python -m scripts.eval.phase7_export_latex_plots

Runs, unchanged and in this order:
  1. scripts.eval.phase7_tables   -> results/latex/*.tex   (LaTeX tables)
  2. scripts.eval.phase7_figures  -> results/figures/*.pdf (figures)
Both read only the result CSVs in results/ and make no API calls.
"""
from scripts.eval import phase7_figures, phase7_tables


def main() -> None:
    phase7_tables.main()
    phase7_figures.main()


if __name__ == "__main__":
    main()

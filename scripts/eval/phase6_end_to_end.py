"""Phase 6 entry point as named in the README.

Run: python -m scripts.eval.phase6_end_to_end

Delegates unchanged to scripts.eval.phase6_e2e (end-to-end pipeline evaluation
and oracle vs. predicted ablation studies).
"""
from scripts.eval.phase6_e2e import main

if __name__ == "__main__":
    main()

"""Pin or verify the honest-N gate's ρ̄ artifact (RR-3 §9.3).

    python -m scripts.n_effective_pin --verify
    python -m scripts.n_effective_pin --pin n_effective_<date>.json --note "why this artifact"

A thin entrypoint for `core.measurement.mbl_gate.main`. Running the module directly with `-m` works,
but Python warns that `core.measurement` already imported it ("may result in unpredictable
behaviour") — an operator command should not teach people to ignore a warning like that.
A re-pin takes effect only when `config/n_effective_pin.json` is COMMITTED; that commit is the review.
"""
from core.measurement.mbl_gate import main

if __name__ == "__main__":
    raise SystemExit(main())

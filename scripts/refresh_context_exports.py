"""Regenerate player context CSVs from an existing reconstructed state file."""
from pathlib import Path
import pandas as pd

from superr_selector.metrics.context_exports import export_context_metrics


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    state_path = root / "data" / "outputs" / "strict_exact_context" / "delivery_match_state.csv"
    if not state_path.is_file():
        raise FileNotFoundError(f"Run the analytics pipeline first: {state_path}")
    state = pd.read_csv(state_path, low_memory=False)
    export_context_metrics(state, root)
    print(f"Updated player context exports from {len(state):,} delivery states.")


if __name__ == "__main__":
    main()

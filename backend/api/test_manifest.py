#!/usr/bin/env python3
"""
Quick test of ManifestTracker with existing logs.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.manifest_service import ManifestTracker


def main():
    # Use absolute paths since test is run from different cwd
    logs_dir = Path(__file__).parent.parent / "logs"
    seed_dir = Path(__file__).parent / "seeds"

    print(f"logs_dir: {logs_dir}")
    print(f"seed_dir: {seed_dir}")

    tracker = ManifestTracker(logs_dir)

    print("\nLoading raw mutants...")
    raw = tracker.load_raw_mutants()
    print(f"  Loaded {len(raw)} raw mutant entries")

    print("\nLoading validity logs...")
    validity = tracker.load_validity_logs()
    print(f"  Loaded {len(validity)} validity entries")

    print("\nGenerating manifest...")
    entries, summary = tracker.generate_manifest(seed_dir)
    print(f"  Generated {len(entries)} manifest entries")

    print("\nSummary Statistics:")
    print(f"  Total generated: {summary.total_generated}")
    print(f"  Valid count: {summary.valid_count}")
    print(f"  Invalid count: {summary.invalid_count}")
    print(f"  Duplicate count: {summary.duplicate_count}")
    print(f"  Trivial count: {summary.trivial_count}")

    print("\nPer-mutator-type breakdown:")
    for mutator_type, stats in summary.by_mutator_type.items():
        print(f"  {mutator_type}: {stats}")

    print("\nError type breakdown:")
    for error_type, count in summary.by_error_type.items():
        print(f"  {error_type}: {count}")

    print("\nSaving manifest...")
    manifest_path = tracker.save_manifest(seed_dir)
    print(f"  Saved to {manifest_path}")

    print("\n✓ Manifest generation test passed!")


if __name__ == "__main__":
    main()

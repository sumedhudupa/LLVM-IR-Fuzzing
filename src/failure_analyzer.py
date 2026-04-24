"""
Failure case analyzer for LLVM IR generation.

Categorizes and provides detailed analysis of why generated IR fails,
with examples and statistics for the research report.
"""

import re
from collections import Counter, defaultdict
from typing import Optional

from .utils import ErrorCategory, GenerationResult, count_ir_features


class FailureAnalyzer:
    """Analyze failure patterns in generated LLVM IR."""

    def __init__(self):
        self.failures = []
        self.successes = []
        self.by_source = defaultdict(list)
        self.by_error = defaultdict(list)
        self.by_mutation = defaultdict(list)

    def add_result(self, result: GenerationResult):
        """Add a generation result for analysis."""
        if result.validation and result.validation.is_valid:
            self.successes.append(result)
        else:
            self.failures.append(result)

        self.by_source[result.source].append(result)
        self.by_mutation[result.mutation_type].append(result)

        if result.validation:
            for cat in result.validation.error_categories:
                cat_name = cat.value if isinstance(cat, ErrorCategory) else str(cat)
                self.by_error[cat_name].append(result)

    def add_results(self, results: list):
        """Add multiple results."""
        for r in results:
            self.add_result(r)

    def get_validity_by_source(self) -> dict:
        """Get validity rates broken down by source."""
        stats = {}
        for source, results in self.by_source.items():
            total = len(results)
            valid = sum(1 for r in results if r.validation and r.validation.is_valid)
            interesting = sum(1 for r in results if r.is_interesting)
            stats[source] = {
                "total": total,
                "valid": valid,
                "valid_pct": 100 * valid / total if total > 0 else 0,
                "interesting": interesting,
                "interesting_pct": 100 * interesting / total if total > 0 else 0,
            }
        return stats

    def get_error_distribution(self) -> dict:
        """Get distribution of error categories."""
        total_errors = sum(len(v) for v in self.by_error.values())
        dist = {}
        for cat, results in sorted(self.by_error.items(), key=lambda x: -len(x[1])):
            dist[cat] = {
                "count": len(results),
                "pct": 100 * len(results) / total_errors if total_errors > 0 else 0,
                "example": results[0].ir_text[:200] if results else "",
                "example_errors": results[0].validation.errors[:2] if results and results[0].validation else [],
            }
        return dist

    def get_mutation_effectiveness(self) -> dict:
        """Analyze which mutation types produce valid IR."""
        stats = {}
        for mut_type, results in self.by_mutation.items():
            total = len(results)
            valid = sum(1 for r in results if r.validation and r.validation.is_valid)
            interesting = sum(1 for r in results if r.is_interesting)
            avg_time = sum(r.generation_time_s for r in results) / total if total > 0 else 0
            stats[mut_type] = {
                "total": total,
                "valid": valid,
                "valid_pct": 100 * valid / total if total > 0 else 0,
                "interesting": interesting,
                "interesting_pct": 100 * interesting / total if total > 0 else 0,
                "avg_time_s": avg_time,
            }
        return stats

    def get_failure_examples(self, category: str = None, n: int = 3) -> list:
        """Get example failure cases with detailed analysis."""
        if category:
            source = self.by_error.get(category, [])
        else:
            source = self.failures

        examples = []
        for result in source[:n]:
            features = count_ir_features(result.ir_text)
            examples.append({
                "source": result.source,
                "mutation_type": result.mutation_type,
                "ir_snippet": result.ir_text[:500],
                "errors": result.validation.errors if result.validation else [],
                "error_categories": [
                    c.value if isinstance(c, ErrorCategory) else str(c)
                    for c in (result.validation.error_categories if result.validation else [])
                ],
                "features": features,
            })
        return examples

    def get_semantic_interest_analysis(self) -> dict:
        """Analyze semantic interest of valid IR."""
        valid_results = self.successes
        if not valid_results:
            return {"total_valid": 0, "interesting": 0, "trivial": 0}

        interesting = [r for r in valid_results if r.is_interesting]
        trivial = [r for r in valid_results if not r.is_interesting]

        # Feature distribution of interesting vs trivial
        interesting_features = Counter()
        trivial_features = Counter()

        for r in interesting:
            features = count_ir_features(r.ir_text)
            for k, v in features.items():
                if v:
                    interesting_features[k] += 1

        for r in trivial:
            features = count_ir_features(r.ir_text)
            for k, v in features.items():
                if v:
                    trivial_features[k] += 1

        return {
            "total_valid": len(valid_results),
            "interesting": len(interesting),
            "interesting_pct": 100 * len(interesting) / len(valid_results) if valid_results else 0,
            "trivial": len(trivial),
            "interesting_feature_dist": dict(interesting_features),
            "trivial_feature_dist": dict(trivial_features),
        }

    def generate_report(self) -> str:
        """Generate a comprehensive failure analysis report."""
        total = len(self.failures) + len(self.successes)
        report = f"""
# Failure Analysis Report

## Overview
- **Total generated**: {total}
- **Valid**: {len(self.successes)} ({100*len(self.successes)/total:.1f}%)
- **Invalid**: {len(self.failures)} ({100*len(self.failures)/total:.1f}%)

## Validity by Source
"""
        for source, stats in self.get_validity_by_source().items():
            report += f"""
### {source.upper()}
- Total: {stats['total']}
- Valid: {stats['valid']} ({stats['valid_pct']:.1f}%)
- Interesting: {stats['interesting']} ({stats['interesting_pct']:.1f}%)
"""

        report += "\n## Error Distribution\n"
        for cat, data in self.get_error_distribution().items():
            report += f"""
### {cat}
- Count: {data['count']} ({data['pct']:.1f}% of errors)
- Example errors: {'; '.join(data['example_errors'][:2])}
"""

        report += "\n## Mutation Type Effectiveness\n"
        report += "| Mutation Type | Total | Valid | Valid% | Interesting | Avg Time(s) |\n"
        report += "|---|---|---|---|---|---|\n"
        for mut_type, stats in self.get_mutation_effectiveness().items():
            report += (f"| {mut_type} | {stats['total']} | {stats['valid']} | "
                      f"{stats['valid_pct']:.1f}% | {stats['interesting']} | "
                      f"{stats['avg_time_s']:.3f} |\n")

        report += "\n## Semantic Interest Analysis\n"
        interest = self.get_semantic_interest_analysis()
        report += f"""
- Valid IR total: {interest['total_valid']}
- Semantically interesting: {interest['interesting']} ({interest.get('interesting_pct', 0):.1f}%)
- Trivial/low-value: {interest['trivial']}
"""

        # Add failure examples
        report += "\n## Example Failures\n"
        for i, example in enumerate(self.get_failure_examples(n=5)):
            report += f"""
### Failure Example {i+1} (Source: {example['source']}, Type: {example['mutation_type']})
**Errors**: {', '.join(example['error_categories'])}
**Details**: {'; '.join(example['errors'][:2])}
```llvm
{example['ir_snippet']}
```
"""

        return report

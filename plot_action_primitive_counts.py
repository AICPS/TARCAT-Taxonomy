#!/usr/bin/env python3
"""Plot leaf action-primitive counts by TARCAT sub-category.

Each labeled activity contributes one occurrence when its category is an action
primitive.  Composite skill labels are recursively expanded, including nested
skills, and each leaf step contributes one occurrence.  The ``repeated`` flags
do not encode a repetition cardinality and therefore do not multiply counts.
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from collections import Counter
from pathlib import Path
from typing import Any


BASE_DIRECTORY = Path(__file__).resolve().parent
DEFAULT_LABELS_PATH = BASE_DIRECTORY / "activity_labels.json"
DEFAULT_PRIMITIVES_PATH = BASE_DIRECTORY / "primitives.json"
DEFAULT_COMPOSITE_DIRECTORY = BASE_DIRECTORY / "composite"
DEFAULT_OUTPUT_PATH = BASE_DIRECTORY / "action_primitive_counts_by_subcategory.pdf"

CATEGORY_COLORS = {
    "Intellectual tasks": "#4C78A8",
    "Social tasks": "#E39C45",
    "Physical tasks": "#59A14F",
}


def load_json(path: Path) -> Any:
    """Read one JSON file and report its path in parsing errors."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"cannot read {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON in {path}: {error}") from error


def load_taxonomy(
    path: Path,
) -> tuple[list[dict[str, Any]], dict[str, tuple[str, str]]]:
    """Return the ordered category hierarchy and primitive classifications."""
    data = load_json(path)
    if not isinstance(data, dict) or not data:
        raise ValueError(f"{path}: expected a nonempty object")

    hierarchy: list[dict[str, Any]] = []
    primitive_classification: dict[str, tuple[str, str]] = {}
    for category in data.values():
        if not isinstance(category, dict):
            raise ValueError(f"{path}: expected each category to be an object")
        category_name = category.get("name")
        sub_categories = category.get("sub_categories")
        primitives = category.get("primitives")
        if not isinstance(category_name, str) or not category_name:
            raise ValueError(f"{path}: category name must be a nonempty string")
        if category_name not in CATEGORY_COLORS:
            raise ValueError(f"no plot color configured for category: {category_name}")
        if not isinstance(sub_categories, list) or not isinstance(primitives, list):
            raise ValueError(
                f"{path}: {category_name} requires sub_categories and primitives arrays"
            )

        declared_primitives = {
            primitive.get("name")
            for primitive in primitives
            if isinstance(primitive, dict) and isinstance(primitive.get("name"), str)
        }
        grouped_primitives: set[str] = set()
        ordered_sub_categories: list[dict[str, Any]] = []
        for sub_category in sub_categories:
            if not isinstance(sub_category, dict):
                raise ValueError(
                    f"{path}: {category_name} contains an invalid sub-category"
                )
            sub_category_name = sub_category.get("name")
            primitive_names = sub_category.get("primitives")
            if not isinstance(sub_category_name, str) or not sub_category_name:
                raise ValueError(
                    f"{path}: {category_name} has an invalid sub-category name"
                )
            if not isinstance(primitive_names, list) or not all(
                isinstance(name, str) and name for name in primitive_names
            ):
                raise ValueError(
                    f"{path}: {sub_category_name} primitives must be nonempty strings"
                )
            for primitive_name in primitive_names:
                if primitive_name in primitive_classification:
                    raise ValueError(
                        "primitive appears in multiple sub-categories: "
                        f"{primitive_name}"
                    )
                primitive_classification[primitive_name] = (
                    category_name,
                    sub_category_name,
                )
                grouped_primitives.add(primitive_name)
            ordered_sub_categories.append(
                {"name": sub_category_name, "primitives": primitive_names}
            )

        if declared_primitives != grouped_primitives:
            missing = sorted(declared_primitives - grouped_primitives)
            unexpected = sorted(grouped_primitives - declared_primitives)
            raise ValueError(
                f"{path}: primitive grouping mismatch in {category_name}; "
                f"missing={missing}, unexpected={unexpected}"
            )
        hierarchy.append(
            {"name": category_name, "sub_categories": ordered_sub_categories}
        )

    return hierarchy, primitive_classification


def load_skills(composite_directory: Path) -> dict[str, list[dict[str, Any]]]:
    """Load all skill step lists and reject duplicate skill names."""
    skills: dict[str, list[dict[str, Any]]] = {}
    paths = sorted(composite_directory.glob("*.json"))
    if not paths:
        raise ValueError(f"no skill-family JSON files found in {composite_directory}")
    for path in paths:
        data = load_json(path)
        skill_records = data.get("skills") if isinstance(data, dict) else None
        if not isinstance(skill_records, list):
            raise ValueError(f"{path}: expected an object with a skills array")
        for index, skill in enumerate(skill_records):
            location = f"{path}:skills[{index}]"
            if not isinstance(skill, dict):
                raise ValueError(f"{location}: expected an object")
            name = skill.get("name")
            steps = skill.get("steps")
            if not isinstance(name, str) or not name:
                raise ValueError(f"{location}.name: expected a nonempty string")
            if name in skills:
                raise ValueError(f"duplicate skill name: {name}")
            if not isinstance(steps, list) or not steps:
                raise ValueError(f"{location}.steps: expected a nonempty array")
            skills[name] = steps
    return skills


def expand_label(
    label: str,
    primitive_names: set[str],
    skills: dict[str, list[dict[str, Any]]],
    memo: dict[str, Counter[str]],
    active_skills: tuple[str, ...] = (),
) -> Counter[str]:
    """Recursively expand a primitive or skill label into leaf primitives."""
    if label in primitive_names:
        return Counter({label: 1})
    if label not in skills:
        raise ValueError(f"unknown primitive or skill label: {label}")
    if label in memo:
        return memo[label].copy()
    if label in active_skills:
        cycle = " -> ".join((*active_skills, label))
        raise ValueError(f"cyclic skill definition: {cycle}")

    counts: Counter[str] = Counter()
    active_path = (*active_skills, label)
    for step_index, step in enumerate(skills[label]):
        if not isinstance(step, dict) or not isinstance(step.get("category"), str):
            raise ValueError(f"{label}.steps[{step_index}] has no valid category")
        counts.update(
            expand_label(
                step["category"],
                primitive_names,
                skills,
                memo,
                active_path,
            )
        )
    memo[label] = counts.copy()
    return counts


def iter_activity_labels(data: Any):
    """Yield every primitive or skill label in O*NET and video activities."""
    if not isinstance(data, dict) or not isinstance(data.get("occupations"), list):
        raise ValueError("activity labels must contain an occupations array")
    for occupation_index, occupation in enumerate(data["occupations"]):
        if not isinstance(occupation, dict):
            raise ValueError(f"occupations[{occupation_index}] must be an object")
        for task in occupation.get("non_movement_tasks", []):
            for activity in task.get("activities", []):
                label = activity.get("category")
                if not isinstance(label, str) or not label:
                    raise ValueError("non-movement activity has no valid category")
                yield label
        movement = occupation.get("movement_tasks", {})
        for video in movement.get("videos", []):
            for activity in video.get("activities", []):
                label = activity.get("category")
                if not isinstance(label, str) or not label:
                    raise ValueError("video activity has no valid category")
                yield label


def count_primitives(
    labels_data: Any,
    primitive_names: set[str],
    skills: dict[str, list[dict[str, Any]]],
) -> tuple[Counter[str], int, int]:
    """Count leaf primitives and return label and composite-label totals."""
    counts: Counter[str] = Counter()
    memo: dict[str, Counter[str]] = {}
    label_count = 0
    composite_label_count = 0
    for label in iter_activity_labels(labels_data):
        label_count += 1
        if label in skills:
            composite_label_count += 1
        counts.update(expand_label(label, primitive_names, skills, memo))
    return counts, label_count, composite_label_count


def aggregate_sub_categories(
    hierarchy: list[dict[str, Any]],
    primitive_counts: Counter[str],
) -> list[dict[str, Any]]:
    """Aggregate leaf primitive counts in taxonomy display order."""
    aggregates: list[dict[str, Any]] = []
    for category in hierarchy:
        for sub_category in category["sub_categories"]:
            count = sum(
                primitive_counts[primitive] for primitive in sub_category["primitives"]
            )
            aggregates.append(
                {
                    "category": category["name"],
                    "sub_category": sub_category["name"],
                    "count": count,
                }
            )
    return aggregates


def wrapped_label(label: str) -> str:
    """Wrap long x-axis labels without changing their wording."""
    return "\n".join(
        textwrap.wrap(label, width=16, break_long_words=False, break_on_hyphens=False)
    )


def create_plot(aggregates: list[dict[str, Any]], output_path: Path) -> None:
    """Create a compact, single-column PDF bar plot."""
    try:
        import matplotlib.pyplot as plt
        from matplotlib.patches import Patch
    except ImportError as error:
        raise ValueError(
            "matplotlib is required; install it in the selected Python environment"
        ) from error

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    names = [record["sub_category"] for record in aggregates]
    counts = [record["count"] for record in aggregates]
    colors = [CATEGORY_COLORS[record["category"]] for record in aggregates]
    positions = list(range(len(aggregates)))

    figure, axis = plt.subplots(figsize=(3.45, 3.35))
    bars = axis.bar(
        positions,
        counts,
        width=0.76,
        color=colors,
        edgecolor="white",
        linewidth=0.45,
        zorder=3,
    )
    axis.set_ylabel("Count", fontsize=8.5)
    axis.set_xticks(positions, [wrapped_label(name) for name in names])
    axis.tick_params(axis="x", labelsize=6.8, rotation=52, pad=1.5)
    for tick_label in axis.get_xticklabels():
        tick_label.set_horizontalalignment("right")
        tick_label.set_rotation_mode("anchor")
    axis.tick_params(axis="y", labelsize=7.4)
    axis.grid(axis="y", color="#D9D9D9", linewidth=0.45, zorder=0)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.margins(x=0.02)

    maximum = max(counts, default=0)
    axis.set_ylim(0, maximum * 1.24 if maximum else 1)
    axis.bar_label(
        bars,
        labels=[str(count) for count in counts],
        padding=1.5,
        fontsize=6.8,
    )

    category_totals: Counter[str] = Counter()
    category_last_index: dict[str, int] = {}
    category_order: list[str] = []
    for index, record in enumerate(aggregates):
        category = record["category"]
        if category not in category_totals:
            category_order.append(category)
        category_totals[category] += record["count"]
        category_last_index[category] = index
    for category in category_order[:-1]:
        axis.axvline(
            category_last_index[category] + 0.5,
            color="#8FBCE6",
            linestyle="--",
            linewidth=0.65,
            zorder=2,
        )

    handles = [
        Patch(
            facecolor=CATEGORY_COLORS[category],
            label=f"{category} (total: {category_totals[category]})",
        )
        for category in category_order
    ]
    axis.legend(
        handles=handles,
        title="Categories",
        loc="upper right",
        fontsize=6.0,
        title_fontsize=6.4,
        frameon=True,
        borderpad=0.35,
        labelspacing=0.25,
        handlelength=1.2,
    )

    figure.subplots_adjust(left=0.14, right=0.99, top=0.98, bottom=0.40)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, format="pdf", bbox_inches="tight", pad_inches=0.02)
    plt.close(figure)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--labels",
        type=Path,
        default=DEFAULT_LABELS_PATH,
        help="Activity-label JSON (default: activity_labels.json beside script)",
    )
    parser.add_argument(
        "--primitives",
        type=Path,
        default=DEFAULT_PRIMITIVES_PATH,
        help="Primitive taxonomy JSON (default: primitives.json beside script)",
    )
    parser.add_argument(
        "--composite-directory",
        type=Path,
        default=DEFAULT_COMPOSITE_DIRECTORY,
        help="Skill-family directory (default: composite beside script)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output PDF path",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        hierarchy, primitive_classification = load_taxonomy(args.primitives)
        skills = load_skills(args.composite_directory)
        labels_data = load_json(args.labels)
        primitive_counts, label_count, composite_label_count = count_primitives(
            labels_data,
            set(primitive_classification),
            skills,
        )
        aggregates = aggregate_sub_categories(hierarchy, primitive_counts)
        create_plot(aggregates, args.output)
    except ValueError as error:
        print(f"Plot generation failed: {error}", file=sys.stderr)
        return 1

    print(f"Labeled activities: {label_count}")
    print(f"Composite activity labels expanded: {composite_label_count}")
    print(f"Leaf action-primitive occurrences: {sum(primitive_counts.values())}")
    print("Counts by sub-category:")
    for record in aggregates:
        print(
            f"  {record['category']} / {record['sub_category']}: " f"{record['count']}"
        )
    print(f"Wrote {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

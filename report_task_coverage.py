#!/usr/bin/env python3
"""Report O*NET task coverage from labeled videos by occupation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_LABELS_PATH = Path(__file__).resolve().parent / "activity_labels.json"


def task_numbers(tasks: list[dict[str, Any]]) -> set[int]:
    """Return task numbers from a movement or non-movement task list."""
    return {task["onet_task_number"] for task in tasks}


def analyze_occupation(occupation: dict[str, Any]) -> dict[str, Any]:
    """Calculate movement-task coverage from all and labeled videos."""
    movement = occupation["movement_tasks"]
    non_movement = task_numbers(occupation["non_movement_tasks"])
    movement_tasks = task_numbers(movement["onet_tasks"])

    covered_from_tasks = {
        task["onet_task_number"]
        for task in movement["onet_tasks"]
        if task["task_videos"]
    }
    covered_from_videos = {
        task_number
        for video in movement["videos"]
        for task_number in video["mapped_tasks"]
    }
    if covered_from_tasks != covered_from_videos:
        task_only = sorted(covered_from_tasks - covered_from_videos)
        video_only = sorted(covered_from_videos - covered_from_tasks)
        raise ValueError(
            f"{occupation['name']}: asymmetric task/video mapping; "
            f"task-only={task_only}, video-only={video_only}"
        )

    unknown = covered_from_videos - movement_tasks
    if unknown:
        raise ValueError(
            f"{occupation['name']}: videos map to unknown movement tasks "
            f"{sorted(unknown)}"
        )

    labeled_videos = [
        video for video in movement["videos"] if video["activities"]
    ]
    covered_from_labeled_videos = {
        task_number
        for video in labeled_videos
        for task_number in video["mapped_tasks"]
    }

    return {
        "occupation": occupation["name"],
        "non_movement_tasks": sorted(non_movement),
        "covered_movement_tasks_labeled_videos": sorted(
            covered_from_labeled_videos
        ),
        "task_count": len(non_movement) + len(movement_tasks),
        "movement_task_count": len(movement_tasks),
        "labeled_video_count": len(labeled_videos),
        "labeled_video_length_seconds": sum(
            video["length"] for video in labeled_videos
        ),
    }


def format_numbers(numbers: list[int]) -> str:
    """Format a task-number list compactly for the text report."""
    return ", ".join(map(str, numbers)) if numbers else "None"


def calculate_totals(results: list[dict[str, Any]]) -> dict[str, int | float]:
    """Aggregate task coverage, labeled-video count, and video duration."""
    total_length_seconds = sum(
        result["labeled_video_length_seconds"] for result in results
    )
    return {
        "occupation_count": len(results),
        "task_count": sum(result["task_count"] for result in results),
        "covered_task_count": sum(
            len(result["non_movement_tasks"])
            + len(result["covered_movement_tasks_labeled_videos"])
            for result in results
        ),
        "labeled_video_count": sum(
            result["labeled_video_count"] for result in results
        ),
        "labeled_video_length_seconds": total_length_seconds,
        "labeled_video_length_minutes": round(total_length_seconds / 60, 2),
    }


def print_text_report(
    results: list[dict[str, Any]], totals: dict[str, int | float]
) -> None:
    """Print the human-readable coverage report."""
    for index, result in enumerate(results):
        if index:
            print()
        labeled_covered_count = len(
            result["covered_movement_tasks_labeled_videos"]
        )
        movement_count = result["movement_task_count"]
        print(result["occupation"])
        print(
            f"  Non-movement tasks ({len(result['non_movement_tasks'])}): "
            f"{format_numbers(result['non_movement_tasks'])}"
        )
        print(
            "  Covered movement tasks, labeled videos only "
            f"({labeled_covered_count}/{movement_count}; "
            f"{result['labeled_video_count']} videos labeled): "
            f"{format_numbers(result['covered_movement_tasks_labeled_videos'])}"
        )

    print()
    print("Overall")
    print(
        f"  Total tasks covered across {totals['occupation_count']} occupations "
        f"({totals['covered_task_count']}/{totals['task_count']})"
    )
    print(f"  Total videos labeled: {totals['labeled_video_count']}")
    print(
        "  Total length of labeled videos: "
        f"{totals['labeled_video_length_minutes']:.2f} minutes"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "labels",
        nargs="?",
        type=Path,
        default=DEFAULT_LABELS_PATH,
        help="Path to activity_labels.json (default: file beside this script)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the report as JSON instead of formatted text",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = json.loads(args.labels.read_text(encoding="utf-8"))
        results = [
            analyze_occupation(occupation) for occupation in data["occupations"]
        ]
        totals = calculate_totals(results)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        print(f"Coverage report failed: {error}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({"occupations": results, "totals": totals}, indent=2))
    else:
        print_text_report(results, totals)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

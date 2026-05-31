from backend.agents.nodes.planner_node import PlannerNode


def test_planner_produces_strict_balanced_and_exploratory_specs() -> None:
    node = PlannerNode()

    result = node.run(
        {
            "mode": "wallpaper",
            "hard_constraints": {"has_human": False},
            "soft_preferences": {
                "moods": ["calm"],
                "colors": ["dark"],
                "qualities": ["oled"],
            },
        }
    )

    specs = result["search_specs"]
    query_modes = [spec.query_mode for spec in specs]

    assert query_modes == ["strict", "balanced", "exploratory"]
    assert all(spec.filters["has_human"] is False for spec in specs)

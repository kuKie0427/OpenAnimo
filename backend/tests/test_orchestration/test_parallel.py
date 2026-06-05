from __future__ import annotations

from langgraph.types import Send

from app.config import Settings
from app.orchestration.graph import build_phase2_graph
from app.orchestration.nodes import (
    route_after_critique_character_images,
    route_shots_approval_parallel,
    set_parallel_mode,
)


class TestRouteShotsApprovalParallel:
    def test_returns_send_list_when_no_override(self):
        result = route_shots_approval_parallel({})
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(item, Send) for item in result)
        targets = [s.node for s in result]
        assert "render_characters" in targets
        assert "render_shots_parallel" in targets

    def test_returns_review_when_review_requested(self):
        result = route_shots_approval_parallel({"review_requested": True})
        assert result == "review"

    def test_returns_route_stage_when_present(self):
        result = route_shots_approval_parallel({"route_stage": "review"})
        assert result == "review"

    def test_route_stage_overrides_review_requested(self):
        result = route_shots_approval_parallel(
            {"route_stage": "plan_outline", "review_requested": True}
        )
        assert result == "plan_outline"


class TestCritiqueCharacterImagesRouting:
    def test_serial_mode_defaults_to_render_shots(self):
        set_parallel_mode(False)
        assert route_after_critique_character_images({}) == "render_shots"

    def test_parallel_mode_defaults_to_compose_videos(self):
        set_parallel_mode(True)
        assert route_after_critique_character_images({}) == "compose_videos"

    def test_route_stage_overrides_in_both_modes(self):
        set_parallel_mode(False)
        assert (
            route_after_critique_character_images({"route_stage": "render_characters"})
            == "render_characters"
        )
        set_parallel_mode(True)
        assert (
            route_after_critique_character_images({"route_stage": "render_characters"})
            == "render_characters"
        )

    def teardown_method(self):
        set_parallel_mode(True)


class TestParallelGraphTopology:
    @staticmethod
    def _branch_targets(graph, node_name):
        branch_dict = graph.branches.get(node_name, {})
        targets = set()
        for spec in branch_dict.values():
            if hasattr(spec, "ends"):
                targets.update(spec.ends.values())
        return targets

    def test_parallel_graph_has_render_shots_parallel_node(self):
        graph = build_phase2_graph(parallel_enabled=True)
        assert "render_shots_parallel" in graph.nodes

    def test_serial_graph_has_no_render_shots_parallel_node(self):
        graph = build_phase2_graph(parallel_enabled=False)
        assert "render_shots_parallel" not in graph.nodes

    def test_parallel_graph_shots_approval_targets(self):
        graph = build_phase2_graph(parallel_enabled=True)
        targets = self._branch_targets(graph, "shots_approval")
        assert "render_shots_parallel" in targets
        assert "render_characters" in targets
        assert "review" in targets

    def test_serial_graph_shots_approval_targets(self):
        graph = build_phase2_graph(parallel_enabled=False)
        targets = self._branch_targets(graph, "shots_approval")
        assert "render_shots_parallel" not in targets
        assert "render_characters" in targets
        assert "review" in targets

    def test_parallel_graph_render_shots_parallel_edge(self):
        graph = build_phase2_graph(parallel_enabled=True)
        assert ("render_shots_parallel", "shot_images_approval") in graph.edges

    def test_serial_graph_render_shots_edge(self):
        graph = build_phase2_graph(parallel_enabled=False)
        assert ("render_shots", "shot_images_approval") in graph.edges

    def test_parallel_critique_character_routes_to_compose(self):
        graph = build_phase2_graph(parallel_enabled=True)
        targets = self._branch_targets(graph, "critique_character_images")
        assert "compose_videos" in targets
        assert "render_characters" in targets
        assert "render_shots" not in targets

    def test_serial_critique_character_routes_to_render_shots(self):
        graph = build_phase2_graph(parallel_enabled=False)
        targets = self._branch_targets(graph, "critique_character_images")
        assert "render_shots" in targets
        assert "render_characters" in targets
        assert "compose_videos" not in targets

    def test_parallel_critique_shot_routes_to_compose(self):
        graph = build_phase2_graph(parallel_enabled=True)
        targets = self._branch_targets(graph, "critique_shot_images")
        assert "compose_videos" in targets
        assert "render_shots_parallel" in targets

    def test_serial_critique_shot_routes_to_render_shots(self):
        graph = build_phase2_graph(parallel_enabled=False)
        targets = self._branch_targets(graph, "critique_shot_images")
        assert "render_shots" in targets
        assert "compose_videos" in targets

    def test_parallel_graph_compiles(self):
        graph = build_phase2_graph(parallel_enabled=True)
        compiled = graph.compile()
        assert compiled is not None

    def test_serial_graph_compiles(self):
        graph = build_phase2_graph(parallel_enabled=False)
        compiled = graph.compile()
        assert compiled is not None

    def test_serial_vs_parallel_node_count(self):
        parallel = build_phase2_graph(parallel_enabled=True)
        serial = build_phase2_graph(parallel_enabled=False)
        assert len(parallel.nodes) == len(serial.nodes) + 1

    def test_common_nodes_present_in_both_modes(self):
        parallel = build_phase2_graph(parallel_enabled=True)
        serial = build_phase2_graph(parallel_enabled=False)

        common_nodes = [
            "plan_outline", "plan_characters", "plan_shots",
            "render_characters", "render_shots",
            "compose_videos", "compose_merge", "add_audio",
            "outline_approval", "characters_approval", "shots_approval",
            "character_images_approval", "shot_images_approval", "compose_approval",
            "critique_character_images", "critique_shot_images",
            "review",
        ]
        for node in common_nodes:
            assert node in parallel.nodes
            assert node in serial.nodes


class TestParallelConfigFlag:
    def test_parallel_enabled_defaults_to_true(self):
        settings = Settings()
        assert settings.parallel_enabled is True

    def test_parallel_enabled_can_be_disabled(self):
        settings = Settings(parallel_enabled=False)
        assert settings.parallel_enabled is False


class TestDefaultGraphHonorsSettings:
    def test_default_graph_with_parallel_true(self):
        settings = Settings(parallel_enabled=True)
        graph = build_phase2_graph(parallel_enabled=settings.parallel_enabled)
        assert "render_shots_parallel" in graph.nodes

    def test_default_graph_with_parallel_false(self):
        settings = Settings(parallel_enabled=False)
        graph = build_phase2_graph(parallel_enabled=settings.parallel_enabled)
        assert "render_shots_parallel" not in graph.nodes


class TestSendObjectShape:
    def test_send_nodes_have_correct_targets(self):
        result = route_shots_approval_parallel({})
        nodes = {s.node for s in result}
        assert nodes == {"render_characters", "render_shots_parallel"}

    def test_send_carries_state(self):
        state = {"project_id": 42, "run_id": 7}
        result = route_shots_approval_parallel(state)
        for s in result:
            assert s.arg["project_id"] == 42
            assert s.arg["run_id"] == 7

"""Tests for canonical workflow configuration contracts."""

import pytest

from src.workflow_specs import DatasetQuery, WorkflowSpec


def test_workflow_spec_validates_and_serializes():
    query = DatasetQuery(cell="587Ah", temperature_c=25, rate="0.5P", test_type="循环")
    spec = WorkflowSpec(
        workflow_id="cycle_benchmark",
        cell="587Ah",
        run_mode="smoke",
        datasets=(query,),
        overrides={"cycles": 2},
    )
    payload = spec.to_dict()
    assert payload["workflow_id"] == "cycle_benchmark"
    assert payload["datasets"][0]["temperature_c"] == 25


@pytest.mark.parametrize("workflow_id", ["", "cycle benchmark", "cycle-benchmark"])
def test_workflow_spec_rejects_invalid_ids(workflow_id):
    with pytest.raises(ValueError, match="workflow_id"):
        WorkflowSpec(workflow_id=workflow_id, cell="587Ah")


def test_workflow_spec_rejects_invalid_mode():
    with pytest.raises(ValueError, match="run_mode"):
        WorkflowSpec(workflow_id="cycle_benchmark", cell="587Ah", run_mode="fast")

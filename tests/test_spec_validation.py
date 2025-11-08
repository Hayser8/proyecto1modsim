import pytest
from src.spec.project_spec import ProjectSpec

def test_default_spec_is_valid():
    spec = ProjectSpec.default()
    spec.validate()  # no debe lanzar

def test_requires_positive_horizon():
    spec = ProjectSpec.default()
    spec.scope.time_horizon_hours = 0
    with pytest.raises(AssertionError):
        spec.validate()

def test_parallelism_requires_multi_pickers_when_enabled():
    spec = ProjectSpec.default()
    spec.experimental_factors.n_pickers = [1]
    with pytest.raises(AssertionError):
        spec.validate()

def test_batching_requires_params():
    spec = ProjectSpec.default()
    spec.experimental_factors.policy = ["Batching"]
    spec.experimental_factors.batch_size = []
    spec.experimental_factors.batch_time_min = []
    with pytest.raises(AssertionError):
        spec.validate()

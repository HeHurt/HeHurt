from src.simulation import (
    DEFAULT_PULSE_LIFECYCLE_MODEL_OPTIONS,
    FULL_PULSE_LIFECYCLE_MODEL_OPTIONS,
    LIGHT_PULSE_LIFECYCLE_MODEL_OPTIONS,
)


def test_default_pulse_lifecycle_options_are_full():
    assert DEFAULT_PULSE_LIFECYCLE_MODEL_OPTIONS == FULL_PULSE_LIFECYCLE_MODEL_OPTIONS
    assert DEFAULT_PULSE_LIFECYCLE_MODEL_OPTIONS["SEI on cracks"] == "true"
    assert DEFAULT_PULSE_LIFECYCLE_MODEL_OPTIONS["loss of active material"] == "stress-driven"


def test_light_pulse_lifecycle_options_keep_previous_minimal_mechanisms():
    assert LIGHT_PULSE_LIFECYCLE_MODEL_OPTIONS["SEI"] == "ec reaction limited"
    assert LIGHT_PULSE_LIFECYCLE_MODEL_OPTIONS["lithium plating"] == "irreversible"
    assert "SEI on cracks" not in LIGHT_PULSE_LIFECYCLE_MODEL_OPTIONS
    assert "loss of active material" not in LIGHT_PULSE_LIFECYCLE_MODEL_OPTIONS

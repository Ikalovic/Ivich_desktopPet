from desktop_pet.config import StateConfig, StateConfigSet
from desktop_pet.state import PetStateMachine


def make_states() -> StateConfigSet:
    return StateConfigSet(
        default_state="idle",
        states={
            "idle": StateConfig("idle", "idle", ("drag", "sleep")),
            "drag": StateConfig("drag", "drag", ("idle",)),
            "sleep": StateConfig("sleep", "sleep", ("idle",)),
        },
    )


def test_state_machine_starts_in_default_state() -> None:
    machine = PetStateMachine(make_states(), available_animations={"idle"})

    assert machine.current_state == "idle"
    assert machine.current_animation == "idle"


def test_state_machine_allows_configured_transition() -> None:
    machine = PetStateMachine(make_states(), available_animations={"idle", "drag"})

    assert machine.transition_to("drag") == "drag"
    assert machine.current_state == "drag"
    assert machine.current_animation == "drag"


def test_state_machine_rejects_unconfigured_transition() -> None:
    machine = PetStateMachine(make_states(), available_animations={"idle", "drag", "sleep"})

    assert machine.transition_to("sleep") == "sleep"
    assert machine.transition_to("drag") == "sleep"
    assert machine.current_state == "sleep"


def test_state_machine_falls_back_to_idle_when_animation_missing() -> None:
    machine = PetStateMachine(make_states(), available_animations={"idle"})

    assert machine.transition_to("drag") == "idle"
    assert machine.current_state == "idle"


def test_state_machine_falls_back_to_configured_default_animation() -> None:
    states = StateConfigSet(
        default_state="idle",
        states={
            "idle": StateConfig("idle", "idle_anim", ("drag",)),
            "drag": StateConfig("drag", "drag_anim", ("idle",)),
        },
    )
    machine = PetStateMachine(states, available_animations={"idle_anim"})

    assert machine.transition_to("drag") == "idle"
    assert machine.current_state == "idle"
    assert machine.current_animation == "idle_anim"


def test_state_machine_unknown_state_uses_configured_default_animation() -> None:
    states = StateConfigSet(
        default_state="idle",
        states={
            "idle": StateConfig("idle", "idle_anim", ("drag",)),
            "drag": StateConfig("drag", "drag_anim", ("idle",)),
        },
    )
    machine = PetStateMachine(states, available_animations={"idle", "idle_anim"})

    assert machine.force("unknown") == "idle"
    assert machine.current_state == "idle"
    assert machine.current_animation == "idle_anim"


def test_state_machine_rejects_transition_to_unknown_state() -> None:
    states = StateConfigSet(
        default_state="idle",
        states={
            "idle": StateConfig("idle", "idle_anim", ("cry",)),
        },
    )
    machine = PetStateMachine(states, available_animations={"idle_anim"})

    assert machine.transition_to("cry") == "idle"
    assert machine.current_state == "idle"
    assert machine.current_animation == "idle_anim"


def test_state_machine_keeps_default_animation_when_default_unavailable() -> None:
    states = StateConfigSet(
        default_state="idle",
        states={
            "idle": StateConfig("idle", "idle_anim", ("drag",)),
            "drag": StateConfig("drag", "drag_anim", ("idle",)),
        },
    )
    machine = PetStateMachine(states, available_animations=set())

    assert machine.transition_to("drag") == "idle"
    assert machine.current_state == "idle"
    assert machine.current_animation == "idle_anim"

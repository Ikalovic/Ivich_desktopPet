from __future__ import annotations

from desktop_pet.config import StateConfigSet


class PetStateMachine:
    def __init__(self, states: StateConfigSet, available_animations: set[str]) -> None:
        self._states = states
        self._available_animations = available_animations
        self.current_state = states.default_state
        self.current_animation = self._animation_for(self.current_state)

    def transition_to(self, target_state: str) -> str:
        current = self._states.states.get(self.current_state)
        if current is None or target_state not in current.can_transition_to:
            return self.current_state
        if target_state not in self._states.states:
            return self._fallback_to_default()
        animation = self._animation_for(target_state)
        if animation not in self._available_animations:
            return self._fallback_to_default()
        self.current_state = target_state
        self.current_animation = animation
        return self.current_state

    def force(self, target_state: str) -> str:
        if target_state not in self._states.states:
            return self._fallback_to_default()
        animation = self._animation_for(target_state)
        if animation not in self._available_animations:
            return self._fallback_to_default()
        self.current_state = target_state
        self.current_animation = animation
        return self.current_state

    def _fallback_to_default(self) -> str:
        self.current_state = self._states.default_state
        self.current_animation = self._animation_for(self.current_state)
        return self.current_state

    def _animation_for(self, state_name: str) -> str:
        state = self._states.states.get(state_name)
        if state is None:
            default_state = self._states.states.get(self._states.default_state)
            if default_state is None:
                return self._states.default_state
            return default_state.animation
        return state.animation

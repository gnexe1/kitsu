"""Tests for Phase 5 Gesture Control.

All tests use mock/synthetic data — no physical webcam required.
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from popal.gestures.calibration import create_calibration
from popal.gestures.cooldown import GestureCooldown
from popal.gestures.debounce import GestureDebouncer
from popal.gestures.errors import GestureError
from popal.gestures.mapper import map_event_to_command
from popal.gestures.pointer import PointerMapper
from popal.gestures.policy import GestureAction, GesturePolicy
from popal.gestures.privacy import allows_external_processing, allows_save_frames
from popal.gestures.provider import GestureProvider
from popal.gestures.recognizer import classify_gesture
from popal.gestures.service import GestureService
from popal.gestures.types import (
    CalibrationProfile,
    CameraStatus,
    GestureEvent,
    GesturePoint,
    GestureState,
    GestureType,
    Hand,
    HandLandmark,
)


# ---------------------------------------------------------------------------
# Synthetic landmark helpers
# ---------------------------------------------------------------------------


def _make_landmark(x: float, y: float, z: float = 0.0, vis: float = 0.9) -> HandLandmark:
    return HandLandmark(x=x, y=y, z=z, visibility=vis)


def _make_open_palm_hand() -> Hand:
    """All fingers extended — OPEN_PALM."""
    lms = [_make_landmark(0.5, 0.8)]  # 0: wrist
    # Thumb (1-4): tip to the side
    lms += [_make_landmark(0.35, 0.75), _make_landmark(0.3, 0.65), _make_landmark(0.28, 0.55), _make_landmark(0.25, 0.5)]
    # Index (5-8): pointing up
    lms += [_make_landmark(0.4, 0.7), _make_landmark(0.4, 0.5), _make_landmark(0.4, 0.35), _make_landmark(0.4, 0.2)]
    # Middle (9-12): up
    lms += [_make_landmark(0.47, 0.7), _make_landmark(0.47, 0.5), _make_landmark(0.47, 0.35), _make_landmark(0.47, 0.18)]
    # Ring (13-16): up
    lms += [_make_landmark(0.54, 0.7), _make_landmark(0.54, 0.5), _make_landmark(0.54, 0.35), _make_landmark(0.54, 0.22)]
    # Pinky (17-20): up
    lms += [_make_landmark(0.6, 0.7), _make_landmark(0.6, 0.55), _make_landmark(0.6, 0.4), _make_landmark(0.6, 0.28)]
    return Hand(handedness="Right", confidence=0.95, landmarks=tuple(lms))


def _make_fist_hand() -> Hand:
    """All fingers folded — FIST."""
    lms = [_make_landmark(0.5, 0.8)]  # wrist
    # Thumb: folded in
    lms += [_make_landmark(0.42, 0.75), _make_landmark(0.43, 0.72), _make_landmark(0.44, 0.70), _make_landmark(0.45, 0.68)]
    # Index: folded (tip above PIP is false -> tip.y > pip.y)
    lms += [_make_landmark(0.46, 0.7), _make_landmark(0.46, 0.6), _make_landmark(0.46, 0.55), _make_landmark(0.46, 0.6)]
    # Middle: folded
    lms += [_make_landmark(0.5, 0.7), _make_landmark(0.5, 0.6), _make_landmark(0.5, 0.55), _make_landmark(0.5, 0.6)]
    # Ring: folded
    lms += [_make_landmark(0.54, 0.7), _make_landmark(0.54, 0.6), _make_landmark(0.54, 0.55), _make_landmark(0.54, 0.6)]
    # Pinky: folded
    lms += [_make_landmark(0.58, 0.7), _make_landmark(0.58, 0.6), _make_landmark(0.58, 0.55), _make_landmark(0.58, 0.6)]
    return Hand(handedness="Right", confidence=0.9, landmarks=tuple(lms))


def _make_point_hand() -> Hand:
    """Only index extended — POINT."""
    lms = [_make_landmark(0.5, 0.8)]  # wrist
    # Thumb: folded
    lms += [_make_landmark(0.42, 0.75), _make_landmark(0.43, 0.72), _make_landmark(0.44, 0.70), _make_landmark(0.45, 0.68)]
    # Index: extended up
    lms += [_make_landmark(0.4, 0.7), _make_landmark(0.4, 0.5), _make_landmark(0.4, 0.35), _make_landmark(0.4, 0.2)]
    # Middle: folded
    lms += [_make_landmark(0.5, 0.7), _make_landmark(0.5, 0.6), _make_landmark(0.5, 0.55), _make_landmark(0.5, 0.6)]
    # Ring: folded
    lms += [_make_landmark(0.54, 0.7), _make_landmark(0.54, 0.6), _make_landmark(0.54, 0.55), _make_landmark(0.54, 0.6)]
    # Pinky: folded
    lms += [_make_landmark(0.58, 0.7), _make_landmark(0.58, 0.6), _make_landmark(0.58, 0.55), _make_landmark(0.58, 0.6)]
    return Hand(handedness="Right", confidence=0.92, landmarks=tuple(lms))


def _make_pinch_hand() -> Hand:
    """Thumb and index tips close together — PINCH. Index must be folded."""
    lms = [_make_landmark(0.5, 0.8)]  # wrist
    # Thumb: tip close to index tip
    lms += [_make_landmark(0.42, 0.55), _make_landmark(0.41, 0.50), _make_landmark(0.40, 0.45), _make_landmark(0.40, 0.40)]
    # Index: folded — tip (8) clearly BELOW PIP (6) so y_tip > y_pip
    lms += [_make_landmark(0.4, 0.5), _make_landmark(0.4, 0.42), _make_landmark(0.4, 0.40), _make_landmark(0.402, 0.42)]
    # Middle: folded
    lms += [_make_landmark(0.5, 0.7), _make_landmark(0.5, 0.6), _make_landmark(0.5, 0.55), _make_landmark(0.5, 0.6)]
    # Ring: folded
    lms += [_make_landmark(0.54, 0.7), _make_landmark(0.54, 0.6), _make_landmark(0.54, 0.55), _make_landmark(0.54, 0.6)]
    # Pinky: folded
    lms += [_make_landmark(0.58, 0.7), _make_landmark(0.58, 0.6), _make_landmark(0.58, 0.55), _make_landmark(0.58, 0.6)]
    return Hand(handedness="Right", confidence=0.93, landmarks=tuple(lms))


# ---------------------------------------------------------------------------
# Mock provider
# ---------------------------------------------------------------------------


class MockGestureProvider(GestureProvider):
    """Returns pre-configured hands."""
    def __init__(self, hands: tuple[Hand, ...] = (), available: bool = True):
        self._hands = hands
        self._available = available

    @property
    def name(self): return "mock"
    @property
    def is_available(self): return self._available
    def detect_hands(self, frame): return self._hands
    def close(self): pass


# ---------------------------------------------------------------------------
# Test types
# ---------------------------------------------------------------------------


class TestTypes:
    def test_hand_landmark(self):
        lm = HandLandmark(0.5, 0.3, 0.1, 0.9, 8)
        assert lm.x == 0.5
        assert lm.index == 8
        d = lm.to_dict()
        assert d["x"] == 0.5

    def test_hand(self):
        hand = _make_open_palm_hand()
        assert hand.handedness == "Right"
        assert len(hand.landmarks) == 21
        assert hand.wrist is not None
        assert hand.index_tip is not None

    def test_gesture_point(self):
        p = GesturePoint(800, 540)
        assert p.x == 800
        assert p.to_dict() == {"x": 800, "y": 540}

    def test_gesture_event(self):
        ev = GestureEvent(GestureType.PINCH, 0.9, "Right", GesturePoint(800, 540), 1.0)
        d = ev.to_dict()
        assert d["gesture"] == "PINCH"
        assert d["confidence"] == 0.9

    def test_gesture_type_enum(self):
        expected = {"OPEN_PALM", "FIST", "POINT", "PINCH", "THUMBS_UP", "THUMBS_DOWN", "V_SIGN"}
        actual = {g.value for g in GestureType}
        assert expected == actual

    def test_gesture_state_enum(self):
        expected = {"no_hand", "hand_detected", "tracking", "gesture_detected",
                    "gesture_confirmed", "gesture_rejected", "error"}
        actual = {s.value for s in GestureState}
        assert expected == actual

    def test_calibration_profile(self):
        cal = create_calibration()
        assert cal.screen_width == 1920
        assert cal.x_scale > 0


# ---------------------------------------------------------------------------
# Test recognizer
# ---------------------------------------------------------------------------


class TestRecognizer:
    def test_open_palm(self):
        hand = _make_open_palm_hand()
        gesture, conf = classify_gesture(hand)
        assert gesture == GestureType.OPEN_PALM
        assert conf >= 0.7

    def test_fist(self):
        hand = _make_fist_hand()
        gesture, conf = classify_gesture(hand)
        assert gesture == GestureType.FIST
        assert conf >= 0.7

    def test_point(self):
        hand = _make_point_hand()
        gesture, conf = classify_gesture(hand)
        assert gesture == GestureType.POINT
        assert conf >= 0.7

    def test_pinch(self):
        hand = _make_pinch_hand()
        gesture, conf = classify_gesture(hand)
        assert gesture == GestureType.PINCH
        assert conf >= 0.5

    def test_confidence_bounded(self):
        for hand_fn in [_make_open_palm_hand, _make_fist_hand, _make_point_hand, _make_pinch_hand]:
            _, conf = classify_gesture(hand_fn())
            assert 0.0 <= conf <= 1.0

    def test_insufficient_landmarks(self):
        hand = Hand("Right", 0.9, tuple(HandLandmark(0.5, 0.5, 0, 0.9, i) for i in range(5)))
        gesture, conf = classify_gesture(hand)
        assert conf < 0.5  # Low confidence


# ---------------------------------------------------------------------------
# Test debounce
# ---------------------------------------------------------------------------


class TestDebounce:
    def test_requires_n_frames(self):
        db = GestureDebouncer(confirmation_frames=3)
        assert db.update(GestureType.PINCH) is False
        assert db.update(GestureType.PINCH) is False
        assert db.update(GestureType.PINCH) is True  # Confirmed on 3rd

    def test_different_gesture_resets(self):
        db = GestureDebouncer(confirmation_frames=2)
        db.update(GestureType.PINCH)
        db.update(GestureType.FIST)  # Different gesture — resets
        assert db.update(GestureType.FIST) is True  # Only 2 needed for new gesture

    def test_none_resets(self):
        db = GestureDebouncer(confirmation_frames=2)
        db.update(GestureType.PINCH)
        db.update(None)  # Reset
        assert db.update(GestureType.PINCH) is False  # Starts over

    def test_release_required(self):
        """Gesture must be released before re-triggering."""
        db = GestureDebouncer(confirmation_frames=2)
        assert db.update(GestureType.PINCH) is False  # First frame
        assert db.update(GestureType.PINCH) is True   # Confirmed on 2nd
        assert db.update(GestureType.PINCH) is False  # Not re-confirmed (needs release)
        db.release()  # Hand released
        assert db.update(GestureType.PINCH) is False  # First frame again
        assert db.update(GestureType.PINCH) is True   # Can confirm again

    def test_current_gesture(self):
        db = GestureDebouncer()
        db.update(GestureType.FIST)
        assert db.current_gesture == GestureType.FIST


# ---------------------------------------------------------------------------
# Test cooldown
# ---------------------------------------------------------------------------


class TestCooldown:
    def test_can_trigger_initially(self):
        cd = GestureCooldown(cooldown_ms=500)
        assert cd.can_trigger() is True

    def test_blocks_during_cooldown(self):
        cd = GestureCooldown(cooldown_ms=500)
        cd.trigger()
        assert cd.can_trigger() is False

    def test_allows_after_cooldown(self):
        cd = GestureCooldown(cooldown_ms=1)  # 1ms cooldown
        cd.trigger()
        time.sleep(0.002)
        assert cd.can_trigger() is True

    def test_reset_clears(self):
        cd = GestureCooldown(cooldown_ms=5000)
        cd.trigger()
        cd.reset()
        assert cd.can_trigger() is True


# ---------------------------------------------------------------------------
# Test policy
# ---------------------------------------------------------------------------


class TestPolicy:
    def test_emergency_stop_default(self):
        policy = GesturePolicy()
        action = policy.evaluate(GestureType.OPEN_PALM)
        assert action == GestureAction.EMERGENCY_STOP

    def test_pinch_click_default(self):
        policy = GesturePolicy()
        action = policy.evaluate(GestureType.PINCH)
        assert action == GestureAction.MOUSE_CLICK

    def test_point_move_default(self):
        policy = GesturePolicy()
        action = policy.evaluate(GestureType.POINT)
        assert action == GestureAction.POINTER_MOVE

    def test_thumbs_up_confirm(self):
        policy = GesturePolicy()
        action = policy.evaluate(GestureType.THUMBS_UP)
        assert action == GestureAction.CONFIRM

    def test_fist_ignored_default(self):
        policy = GesturePolicy()
        action = policy.evaluate(GestureType.FIST)
        assert action == GestureAction.IGNORED

    def test_custom_mapping(self):
        policy = GesturePolicy()
        policy.set_mapping(GestureType.FIST, GestureAction.MOUSE_CLICK)
        assert policy.evaluate(GestureType.FIST) == GestureAction.MOUSE_CLICK

    def test_get_mappings(self):
        policy = GesturePolicy()
        mappings = policy.get_mappings()
        assert "OPEN_PALM" in mappings
        assert mappings["OPEN_PALM"] == "emergency_stop"


# ---------------------------------------------------------------------------
# Test mapper
# ---------------------------------------------------------------------------


class TestMapper:
    def test_emergency_stop(self):
        ev = GestureEvent(GestureType.OPEN_PALM, 0.9, "Right")
        cmd = map_event_to_command(ev, GestureAction.EMERGENCY_STOP)
        assert cmd["type"] == "emergency_stop"

    def test_confirm(self):
        ev = GestureEvent(GestureType.THUMBS_UP, 0.9, "Right")
        cmd = map_event_to_command(ev, GestureAction.CONFIRM)
        assert cmd["type"] == "confirm"

    def test_mouse_click(self):
        ev = GestureEvent(GestureType.PINCH, 0.9, "Right", GesturePoint(800, 540))
        cmd = map_event_to_command(ev, GestureAction.MOUSE_CLICK)
        assert cmd["intent"] == "mouse_click"

    def test_pointer_move(self):
        ev = GestureEvent(GestureType.POINT, 0.9, "Right", GesturePoint(800, 540))
        cmd = map_event_to_command(ev, GestureAction.POINTER_MOVE)
        assert cmd["intent"] == "mouse_move"
        assert cmd["parameters"]["x"] == 800

    def test_ignored_returns_none(self):
        ev = GestureEvent(GestureType.FIST, 0.9, "Right")
        cmd = map_event_to_command(ev, GestureAction.IGNORED)
        assert cmd is None


# ---------------------------------------------------------------------------
# Test pointer
# ---------------------------------------------------------------------------


class TestPointer:
    def test_maps_to_screen(self):
        mapper = PointerMapper(calibration=CalibrationProfile(screen_width=1920, screen_height=1080))
        hand = _make_point_hand()
        pt = mapper.map_position(hand)
        assert pt is not None
        assert 0 <= pt.x <= 1920
        assert 0 <= pt.y <= 1080

    def test_clamps_to_screen(self):
        mapper = PointerMapper(calibration=CalibrationProfile(screen_width=1920, screen_height=1080))
        # Hand with landmarks at edge
        lms = [HandLandmark(0.5, 0.8, 0, 0.9, i) for i in range(21)]
        lms[8] = HandLandmark(0.0, 0.0, 0, 0.9, 8)  # Index tip at top-left
        hand = Hand("Right", 0.9, tuple(lms))
        pt = mapper.map_position(hand)
        assert pt is not None
        assert pt.x >= 0
        assert pt.y >= 0

    def test_reset(self):
        mapper = PointerMapper()
        mapper.reset()
        assert mapper._prev_x is None

    def test_insufficient_landmarks(self):
        mapper = PointerMapper()
        hand = Hand("Right", 0.9, tuple(HandLandmark(0.5, 0.5, 0, 0.9, i) for i in range(5)))
        pt = mapper.map_position(hand)
        assert pt is None


# ---------------------------------------------------------------------------
# Test calibration
# ---------------------------------------------------------------------------


class TestCalibration:
    def test_default_calibration(self):
        cal = create_calibration()
        assert cal.camera_width == 640
        assert cal.screen_width == 1920
        assert cal.x_scale == 1920 / 640

    def test_custom_calibration(self):
        cal = create_calibration(camera_width=1280, screen_width=2560)
        assert cal.x_scale == 2.0


# ---------------------------------------------------------------------------
# Test privacy
# ---------------------------------------------------------------------------


class TestPrivacy:
    def test_gestures_disabled_by_default(self):
        from popal.utils.config import load_config
        cfg = load_config()
        assert cfg.get("gestures", {}).get("enabled", False) is False

    def test_save_frames_disabled_by_default(self):
        assert allows_save_frames() is False

    def test_external_processing_disabled_by_default(self):
        assert allows_external_processing() is False


# ---------------------------------------------------------------------------
# Test service
# ---------------------------------------------------------------------------


class TestService:
    def test_initial_state(self):
        provider = MockGestureProvider()
        service = GestureService(provider)
        assert service.state == GestureState.NO_HAND

    def test_no_hand_state(self):
        provider = MockGestureProvider(hands=())
        service = GestureService(provider)
        result = service.process_frame(np.zeros((480, 640, 3), dtype=np.uint8))
        assert result is None
        assert service.state == GestureState.NO_HAND

    def test_gesture_detected_and_confirmed(self):
        hand = _make_open_palm_hand()
        provider = MockGestureProvider(hands=(hand,))
        service = GestureService(
            provider,
            debouncer=GestureDebouncer(confirmation_frames=1),
            cooldown=GestureCooldown(cooldown_ms=0),
        )
        # Send same frame multiple times to meet debounce
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = None
        for _ in range(5):
            result = service.process_frame(frame)
            if result is not None:
                break
        assert result is not None
        assert result.gesture == GestureType.OPEN_PALM

    def test_emergency_stop_gesture(self):
        hand = _make_open_palm_hand()
        provider = MockGestureProvider(hands=(hand,))
        service = GestureService(
            provider,
            debouncer=GestureDebouncer(confirmation_frames=1),
            cooldown=GestureCooldown(cooldown_ms=0),
        )
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        event = None
        for _ in range(5):
            event = service.process_frame(frame)
            if event:
                break
        assert event is not None
        action, cmd = service.evaluate_event(event)
        assert action == GestureAction.EMERGENCY_STOP
        assert cmd["type"] == "emergency_stop"

    def test_gesture_service_no_direct_execute(self):
        """GestureService must NOT have click/move/type methods."""
        assert not hasattr(GestureService, "click")
        assert not hasattr(GestureService, "mouse_move")
        assert not hasattr(GestureService, "type_text")

    def test_stop(self):
        provider = MockGestureProvider()
        service = GestureService(provider)
        service.start()
        assert service.is_running
        service.stop()
        assert not service.is_running

    def test_get_status(self):
        provider = MockGestureProvider()
        service = GestureService(provider)
        status = service.get_status()
        assert "state" in status
        assert "provider" in status
        assert "mappings" in status


# ---------------------------------------------------------------------------
# Test security
# ---------------------------------------------------------------------------


class TestSecurity:
    def test_negative_coordinates_rejected(self):
        """Pointer mapper should clamp negative values."""
        mapper = PointerMapper(calibration=CalibrationProfile(screen_width=1920, screen_height=1080))
        lms = [HandLandmark(-0.5, -0.5, 0, 0.9, i) for i in range(21)]
        lms[8] = HandLandmark(-1.0, -1.0, 0, 0.9, 8)
        hand = Hand("Right", 0.9, tuple(lms))
        pt = mapper.map_position(hand)
        if pt is not None:
            assert pt.x >= 0
            assert pt.y >= 0

    def test_out_of_screen_clamped(self):
        mapper = PointerMapper(calibration=CalibrationProfile(screen_width=1920, screen_height=1080))
        lms = [HandLandmark(2.0, 2.0, 0, 0.9, i) for i in range(21)]
        lms[8] = HandLandmark(2.0, 2.0, 0, 0.9, 8)
        hand = Hand("Right", 0.9, tuple(lms))
        pt = mapper.map_position(hand)
        if pt is not None:
            assert pt.x <= 1920
            assert pt.y <= 1080

    def test_confidence_bounded(self):
        ev = GestureEvent(GestureType.PINCH, 0.99, "Right", GesturePoint(800, 540))
        assert 0.0 <= ev.confidence <= 1.0

    def test_gesture_event_is_frozen(self):
        ev = GestureEvent(GestureType.PINCH, 0.9, "Right", GesturePoint(800, 540))
        with pytest.raises(AttributeError):
            ev.confidence = 0.5  # type: ignore[misc]

    def test_unrecognized_gesture_ignored(self):
        policy = GesturePolicy()
        # All gestures have mappings, but default unknown would be IGNORED
        action = policy.evaluate(GestureType.V_SIGN)
        assert action == GestureAction.IGNORED

    def test_no_pending_confirm_no_action(self):
        """THUMBS_UP without a pending confirmation should map to confirm command
        but the actual safety pipeline decides whether to execute."""
        ev = GestureEvent(GestureType.THUMBS_UP, 0.9, "Right")
        cmd = map_event_to_command(ev, GestureAction.CONFIRM)
        assert cmd["type"] == "confirm"
        # The confirm goes to the safety pipeline — not direct execution


# ---------------------------------------------------------------------------
# Test emergency stop
# ---------------------------------------------------------------------------


class TestEmergencyStop:
    def test_emergency_stop_blocks_all(self):
        from popal.core.state import PopalState, PopalStatus
        state = PopalState()
        state.set_status(PopalStatus.READY)
        state.trigger_emergency_stop()
        assert state.can_execute() is False

    def test_emergency_gesture_priority(self):
        """Emergency stop gesture should have highest priority."""
        policy = GesturePolicy()
        assert policy.evaluate(GestureType.OPEN_PALM) == GestureAction.EMERGENCY_STOP
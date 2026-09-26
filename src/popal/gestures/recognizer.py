"""Gesture recognizer — classifies hand landmarks into gesture types."""

from __future__ import annotations

from popal.gestures.types import GestureType, Hand, HandLandmark


def classify_gesture(hand: Hand) -> tuple[GestureType, float]:
    """Classify a hand's gesture from its landmarks.

    Uses geometric analysis of finger extension states.

    Args:
        hand: A detected hand with landmarks.

    Returns:
        (gesture_type, confidence) tuple.
    """
    if len(hand.landmarks) < 21:
        return GestureType.OPEN_PALM, 0.0

    fingers = _get_finger_states(hand.landmarks)
    thumb_up, index_up, middle_up, ring_up, pinky_up = fingers

    extended_count = sum(fingers)

    # PINCH: thumb and index tips close together (check before FIST because
    # both fingers may appear folded by y-coordinate while pinching)
    thumb_tip = hand.landmarks[4]
    index_tip = hand.landmarks[8]
    dist = ((thumb_tip.x - index_tip.x) ** 2 + (thumb_tip.y - index_tip.y) ** 2) ** 0.5
    if dist < 0.05:
        return GestureType.PINCH, max(0.7, 0.95 - dist * 10)

    # OPEN_PALM: all five fingers extended
    if all(fingers):
        return GestureType.OPEN_PALM, 0.9

    # FIST: no fingers extended
    if extended_count == 0:
        return GestureType.FIST, 0.9

    # POINT: only index extended
    if index_up and not middle_up and not ring_up and not pinky_up:
        return GestureType.POINT, 0.9

    # V_SIGN: index + middle extended, others folded
    if index_up and middle_up and not ring_up and not pinky_up:
        return GestureType.V_SIGN, 0.85

    # THUMBS_UP: thumb extended upward, others folded
    if thumb_up and not index_up and not middle_up and not ring_up and not pinky_up:
        thumb_tip = hand.landmarks[4]
        thumb_mcp = hand.landmarks[2]
        if thumb_tip.y < thumb_mcp.y:  # Thumb tip above MCP (pointing up)
            return GestureType.THUMBS_UP, 0.85

    # THUMBS_DOWN: thumb extended downward, others folded
    if thumb_up and not index_up and not middle_up and not ring_up and not pinky_up:
        thumb_tip = hand.landmarks[4]
        thumb_mcp = hand.landmarks[2]
        if thumb_tip.y > thumb_mcp.y:  # Thumb tip below MCP (pointing down)
            return GestureType.THUMBS_DOWN, 0.85

    # Fallback: treat as OPEN_PALM with lower confidence
    return GestureType.OPEN_PALM, 0.4


def _get_finger_states(landmarks: tuple[HandLandmark, ...]) -> tuple[bool, bool, bool, bool, bool]:
    """Determine which fingers are extended.

    Returns (thumb, index, middle, ring, pinky) as booleans.
    """
    # Thumb: compare tip (4) x-position to IP joint (3)
    # For right hand: tip.x < ip.x means extended (thumb is to the left)
    # For left hand: tip.x > ip.x means extended
    # Simplified: use distance from wrist
    wrist = landmarks[0]
    thumb_tip = landmarks[4]
    thumb_ip = landmarks[3]
    thumb_extended = abs(thumb_tip.x - wrist.x) > abs(thumb_ip.x - wrist.x)

    # Index finger: tip (8) above PIP (6)
    index_extended = landmarks[8].y < landmarks[6].y

    # Middle finger: tip (12) above PIP (10)
    middle_extended = landmarks[12].y < landmarks[10].y

    # Ring finger: tip (16) above PIP (14)
    ring_extended = landmarks[16].y < landmarks[14].y

    # Pinky: tip (20) above PIP (18)
    pinky_extended = landmarks[20].y < landmarks[18].y

    return (thumb_extended, index_extended, middle_extended, ring_extended, pinky_extended)
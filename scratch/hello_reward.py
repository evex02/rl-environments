def reward(answer):
    words = answer.strip().rstrip(".").split()
    if not words:
        return 0.0  # empty answer
    return 1.0 if words[-1] == "4" else 0.0
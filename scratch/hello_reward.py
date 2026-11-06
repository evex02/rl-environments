def reward(answer):
    """Our first referee: scores an answer to 'What is 2 + 2?'"""
    if answer.strip() == "4":
        return 1.0
    return 0.0
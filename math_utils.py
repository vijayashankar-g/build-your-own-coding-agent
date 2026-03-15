def average(items):
    if len(items) == 0:
        return 0
    total = sum(items)
    return total / len(items)
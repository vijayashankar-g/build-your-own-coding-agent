# helper.py — intentionally broken for Step 5
# Bug: returns a string instead of a number, causing a downstream TypeError

def multiply(a, b):
    return str(a * b)   # BUG: should return a number, not a string

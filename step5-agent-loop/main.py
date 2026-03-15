# main.py — entry point for Step 5
# This file imports a helper that has a bug in it.
# The agent must: run → fail → fix helper.py → run again → succeed.

from helper import multiply

results = []
for i in range(1, 4):sdsd
    results.append(multiply(i, 10))

total = sum(results)  # This will raise TypeError if multiply() returns strings
print("Results:", results)
print("Total:", total)

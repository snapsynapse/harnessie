#!/bin/bash
# Oracle solution: the reference answer Harbor uses to prove the task is solvable.
set -euo pipefail
cd /app
cat > calc.py <<'EOF'
def add(a, b):
    return a + b


def mean(xs):
    if not xs:
        raise ValueError("mean of empty list")
    return sum(xs) / len(xs)
EOF
echo "wrote /app/calc.py"

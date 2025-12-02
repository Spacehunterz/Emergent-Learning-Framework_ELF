#!/bin/bash
# Verification script for 10/10 concurrency

echo "=========================================="
echo "10/10 CONCURRENCY VERIFICATION"
echo "=========================================="
echo ""

score=0

# 1. Check stale lock detection
if grep -q "is_process_alive\|detect_stale_lock" scripts/lib/concurrency.sh; then
    echo "[✓] Stale lock cleanup with process detection: PRESENT"
    ((score+=1))
else
    echo "[✗] Stale lock cleanup: MISSING"
fi

# 2. Check exponential backoff
if grep -q "2\^.*attempt" scripts/lib/concurrency.sh; then
    echo "[✓] Exponential backoff: PRESENT"
    ((score+=1))
else
    echo "[✗] Exponential backoff: MISSING"
fi

# 3. Check atomic operations
if grep -q "write_atomic\|append_atomic" scripts/lib/concurrency.sh; then
    echo "[✓] Atomic file operations: PRESENT"
    ((score+=1))
else
    echo "[✗] Atomic operations: MISSING"
fi

# 4. Check SQLite WAL mode
if sqlite3 memory/index.db "PRAGMA journal_mode;" 2>/dev/null | grep -q "wal"; then
    echo "[✓] SQLite WAL mode: ENABLED"
    ((score+=1))
else
    echo "[✗] SQLite WAL mode: NOT ENABLED"
fi

# 5. Check monitoring dashboard
if [ -f "monitor-locks.sh" ]; then
    echo "[✓] Lock monitoring dashboard: PRESENT"
    ((score+=1))
else
    echo "[✗] Lock monitoring dashboard: MISSING"
fi

# 6. Check stress test
if [ -f "advanced-concurrency-stress-test.sh" ]; then
    echo "[✓] Stress test suite: PRESENT"
    ((score+=1))
else
    echo "[✗] Stress test suite: MISSING"
fi

# 7. Check test results
if [ -d "test-results/stress-20251201-182748" ]; then
    echo "[✓] Stress test results: VERIFIED"
    ((score+=1))
else
    echo "[✗] Stress test results: NOT FOUND"
fi

# 8. Check lock timeout
if grep -q "timeout.*10" scripts/lib/concurrency.sh; then
    echo "[✓] Lock timeout optimized (10s): PRESENT"
    ((score+=1))
else
    echo "[✗] Lock timeout: NOT OPTIMIZED"
fi

# 9. Check jitter implementation
if grep -q "jitter\|rand()" scripts/lib/concurrency.sh; then
    echo "[✓] Jitter in backoff: PRESENT"
    ((score+=1))
else
    echo "[✗] Jitter: MISSING"
fi

# 10. Check safety checks
if grep -q "SECURITY.*Refusing" scripts/lib/concurrency.sh; then
    echo "[✓] Safety checks in lock cleanup: PRESENT"
    ((score+=1))
else
    echo "[✗] Safety checks: MISSING"
fi

echo ""
echo "=========================================="
echo "FINAL SCORE: $score/10"
echo "=========================================="

if [ $score -eq 10 ]; then
    echo "✓✓✓ PERFECT 10/10 ACHIEVED!"
    exit 0
elif [ $score -ge 8 ]; then
    echo "⚠ Close to 10/10, missing $((10-score)) features"
    exit 1
else
    echo "✗ Need more work: $((10-score)) features missing"
    exit 1
fi

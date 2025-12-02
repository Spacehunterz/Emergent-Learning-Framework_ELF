#!/bin/bash
# Concurrency library v2.0 - Process detection + Deadlock prevention + Enhanced backoff

LOCK_TIMEOUT_SECONDS=${LOCK_TIMEOUT_SECONDS:-10}
STALE_LOCK_AGE_SECONDS=${STALE_LOCK_AGE_SECONDS:-300}
SQLITE_MAX_ATTEMPTS=${SQLITE_MAX_ATTEMPTS:-5}
SQLITE_MAX_BACKOFF=${SQLITE_MAX_BACKOFF:-5.0}

is_process_alive() {
    local pid=$1
    kill -0 $pid 2>/dev/null && return 0
    [ -d /proc/$pid ] && return 0
    ps -p $pid >/dev/null 2>&1 && return 0
    return 1
}

extract_lock_pid() {
    local lock_path=$1
    [ -f $lock_path/pid ] && cat $lock_path/pid && return 0
    return 1
}

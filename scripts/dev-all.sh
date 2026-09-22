#!/bin/sh
# Run the three dev services together; Ctrl-C stops all.

pids=""
stop() {
    [ -n "$pids" ] && kill $pids 2>/dev/null
    exit "${1:-0}"
}
trap 'stop 130' INT TERM
just dev flow & pids="$pids $!"
just dev uc & pids="$pids $!"
just dev bff & pids="$pids $!"
n=$(echo $pids | wc -w | tr -d ' ')
while :; do
    sleep 1
    alive=0
    for pid in $pids; do
        kill -0 "$pid" 2>/dev/null && alive=$((alive + 1))
    done
    if [ "$alive" -lt "$n" ]; then
        # A service died (e.g. port already in use): stop the rest
        # and exit nonzero instead of silently running a partial stack.
        stop 1
    fi
done

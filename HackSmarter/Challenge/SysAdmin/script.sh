#!/bin/bash

echo "======================================"
echo " SNMPv3 MD5 Credential Validation Tool"
echo "======================================"

read -p "Enter device list file: " DEVICES
read -p "Enter SNMP username file: " USERS
read -p "Enter password file: " PASSWORDS

read -p "Number of parallel workers [5]: " WORKERS
WORKERS=${WORKERS:-5}

LOG="snmp_results_$(date +%F_%H%M).log"

if [[ ! -f "$DEVICES" || ! -f "$USERS" || ! -f "$PASSWORDS" ]]; then
    echo "ERROR: One or more files were not found."
    exit 1
fi


touch "$LOG"

echo "SNMPv3 MD5 authNoPriv scan started: $(date)" > "$LOG"
echo "Log file: $(realpath "$LOG")"
echo ""


DEVICE_COUNT=$(grep -cv '^$' "$DEVICES")
USER_COUNT=$(grep -cv '^$' "$USERS")
PASS_COUNT=$(grep -cv '^$' "$PASSWORDS")

TOTAL_TESTS=$((DEVICE_COUNT * USER_COUNT * PASS_COUNT))

echo "Devices:        $DEVICE_COUNT"
echo "Users:          $USER_COUNT"
echo "Passwords:      $PASS_COUNT"
echo "Total Tests:    $TOTAL_TESTS"
echo "Workers:        $WORKERS"
echo ""
echo "Starting SNMPv3 MD5 authNoPriv validation..."
echo ""


TEST_FILE=$(mktemp)


while read -r HOST
do
    [[ -z "$HOST" ]] && continue

    while read -r USER
    do
        [[ -z "$USER" ]] && continue

        while read -r PASS
        do
            [[ -z "$PASS" ]] && continue

            echo "$HOST|$USER|$PASS" >> "$TEST_FILE"

        done < "$PASSWORDS"

    done < "$USERS"

done < "$DEVICES"


run_test()
{
    HOST="$1"
    USER="$2"
    PASS="$3"

    if timeout 5 snmpwalk \
        -v3 \
        -t 2 \
        -r 1 \
        -l authNoPriv \
        -u "$USER" \
        -a MD5 \
        -A "$PASS" \
        "$HOST" \
        1.3.6.1.2.1.1 >/dev/null 2>&1

    then
        echo "[SUCCESS] $HOST | User=$USER | authNoPriv | MD5 | Password=$PASS" | tee -a "$LOG"
    fi
}


export LOG
export -f run_test


START=$(date +%s)


cat "$TEST_FILE" | xargs -P "$WORKERS" -I {} bash -c '
IFS="|" read HOST USER PASS <<< "{}"
run_test "$HOST" "$USER" "$PASS"
'


rm "$TEST_FILE"


END=$(date +%s)
RUNTIME=$((END-START))


echo ""
echo "======================================"
echo "Completed"
echo "Runtime: ${RUNTIME} seconds"
echo "Results:"
echo "$LOG"
echo "======================================"

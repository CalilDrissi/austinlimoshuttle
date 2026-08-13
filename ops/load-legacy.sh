#!/usr/bin/env bash
# Load the sanitised legacy replica into the local database.
#
# The dump is SANITISED: card numbers reduced to last-4, expiry dates cleared,
# CVV codes destroyed, passwords replaced with a placeholder. Row counts and
# structure are untouched. Never load an unsanitised production dump here.
#
# Idempotent: drops and recreates the legacy schema each run.

set -euo pipefail

DUMP="${1:-$(ls -t "$(dirname "$0")"/../dumps/*-sanitized.sql.gz | head -1)}"
CONTAINER="limo-db"
ROOT_PASS="localdevonly"
LEGACY_DB="austi118_austinlimo"

if [[ ! -f "$DUMP" ]]; then
  echo "error: dump not found: $DUMP" >&2
  exit 1
fi

echo "==> waiting for $CONTAINER"
for _ in $(seq 1 40); do
  if docker exec "$CONTAINER" mariadb-admin ping -uroot -p"$ROOT_PASS" --silent >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "==> resetting $LEGACY_DB"
docker exec "$CONTAINER" mariadb -uroot -p"$ROOT_PASS" -e "
  DROP DATABASE IF EXISTS \`$LEGACY_DB\`;
  CREATE DATABASE \`$LEGACY_DB\` CHARACTER SET latin1 COLLATE latin1_swedish_ci;
  GRANT ALL PRIVILEGES ON \`$LEGACY_DB\`.* TO 'austinlimo'@'%';
  FLUSH PRIVILEGES;" 2>&1 | grep -vi "using a password" || true

echo "==> loading $(basename "$DUMP")"
gunzip -c "$DUMP" | docker exec -i "$CONTAINER" \
  mariadb -uroot -p"$ROOT_PASS" "$LEGACY_DB" 2>&1 | grep -vi "using a password" || true

echo "==> verifying"
docker exec "$CONTAINER" mariadb -uroot -p"$ROOT_PASS" "$LEGACY_DB" -e "
  SELECT
    (SELECT COUNT(*) FROM limousin_order)        AS orders,
    (SELECT COUNT(*) FROM limousin_member)       AS members,
    (SELECT COUNT(*) FROM limousin_orderdetails) AS order_details,
    (SELECT COUNT(*) FROM limousin_cms)          AS pages;" 2>&1 | grep -vi "using a password"

echo "==> confirming no cardholder data present"
LEAKS=$(docker exec "$CONTAINER" mariadb -uroot -p"$ROOT_PASS" "$LEGACY_DB" -N -B -e "
  SELECT
    (SELECT COUNT(*) FROM limousin_order        WHERE card_number  REGEXP '^[0-9]{13,19}\$')
  + (SELECT COUNT(*) FROM limousin_orderdetails WHERE card_number  REGEXP '^[0-9]{13,19}\$')
  + (SELECT COUNT(*) FROM limousin_orderdetails WHERE securitycode <> '');" 2>/dev/null)

if [[ "$LEAKS" != "0" ]]; then
  echo "FAIL: $LEAKS cardholder values present -- this dump is not sanitised" >&2
  exit 1
fi
echo "OK: 0 cardholder values"

#!/usr/bin/env bash
# Builds big_10k, big_100k and big_1m from big_10m.
# Same students/badges/lectures/etc.; access_log keeps the original case rows
# (access_id < 1000), the first N synthetic swipes, and a proportional share
# of the extra swipes on the murder day (access_id >= 20,000,000).
set -euo pipefail
for T in 10k:10000 100k:100000 1m:1000000; do
  n=${T%%:*}; N=${T##*:}; M=$((N * 27 / 10000))
  ${MYSQL:-mysql -uroot} -e "DROP DATABASE IF EXISTS big_$n; CREATE DATABASE big_$n;"
  for t in students courses grades relationships badges lectures attendance crime_reports witness_statements access_log; do
    ${MYSQL:-mysql -uroot} -e "CREATE TABLE big_$n.$t LIKE big_10m.$t;"
  done
  for t in students courses grades relationships badges lectures attendance crime_reports witness_statements; do
    ${MYSQL:-mysql -uroot} -e "INSERT INTO big_$n.$t SELECT * FROM big_10m.$t;"
  done
  ${MYSQL:-mysql -uroot} -e "INSERT INTO big_$n.access_log SELECT * FROM big_10m.access_log
                   WHERE access_id < 1000
                      OR access_id BETWEEN 1000 AND $((999 + N))
                      OR (access_id >= 20000000 AND access_id < $((20000000 + M)));"
  echo "big_$n: $(${MYSQL:-mysql -uroot} -N -e "SELECT COUNT(*) FROM big_$n.access_log") swipes"
done

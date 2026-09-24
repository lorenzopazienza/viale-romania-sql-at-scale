# Viale Romania: SQL at scale
#
#   make setup   load the lab dump as luiss_mystery (DUMP=path/to/DEMO_luiss_mystery.sql)
#   make test    check every query in solutions/ on MySQL and SQLite
#   make data    build the 10M-swipe campus (big_10m) and the smaller tiers
#   make bench   run every experiment (about 30 minutes on 2 vCPU)
#   make charts  redraw docs/img/*.png from results/
#   make all     everything above, in order
#
# MySQL access: MYSQL_USER / MYSQL_PASSWORD for the Python scripts (default bench/bench),
# and the `mysql` client for the SQL files (MYSQL = mysql -uroot by default).

DUMP  ?= DEMO_luiss_mystery.sql
MYSQL ?= mysql -uroot

.PHONY: all setup test data bench charts

all: setup test data bench charts

setup:
	$(MYSQL) < $(DUMP)

test:
	LUISS_DUMP=$(abspath $(DUMP)) python3 -m pytest -q tests/

data:
	sed 's/luiss_mystery/big_10m/g' $(DUMP) | $(MYSQL)
	$(MYSQL) < benchmark/01_generate_campus.sql
	$(MYSQL) < benchmark/02_busy_murder_day.sql
	$(MYSQL) --table < benchmark/check_data.sql
	MYSQL="$(MYSQL)" ./benchmark/03_build_tiers.sh

bench:
	./benchmark/run_all.sh

charts:
	python3 analysis/make_charts.py

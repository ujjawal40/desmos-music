.PHONY: build check test serve watch stats clean

build:
	python3 -m desmos_music

check:
	python3 -m desmos_music --check

test:
	python3 -m pytest -q

serve:
	python3 -m desmos_music serve

watch:
	python3 -m desmos_music watch

stats:
	python3 -m desmos_music stats

clean:
	rm -f build/*.json build/*.console.js

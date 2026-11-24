.PHONY: build test serve clean

build:
	python3 -m desmos_music

test:
	python3 -m pytest -q

serve:
	python3 -m desmos_music serve

clean:
	rm -f build/*.json build/*.console.js

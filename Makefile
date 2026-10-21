GAMES_DIR := games

.DEFAULT_GOAL := test

.PHONY: test

test:
	$(MAKE) -C lib test
	$(MAKE) -C $(GAMES_DIR) test

GAME_DIRS := $(patsubst %/Makefile,%,$(wildcard */Makefile))
GAME_TEST_TARGETS := $(GAME_DIRS:%=test-%)

.DEFAULT_GOAL := test

.PHONY: test $(GAME_TEST_TARGETS)

test: $(GAME_TEST_TARGETS)

$(GAME_TEST_TARGETS):
	$(MAKE) -C $(patsubst test-%,%,$@) test

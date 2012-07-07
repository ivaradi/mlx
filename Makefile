LANGUAGES=en hu

all: $(foreach lang,$(LANGUAGES),locale/$(lang)/LC_MESSAGES/mlx.mo)

locale/%/LC_MESSAGES/mlx.mo: locale/%/mlx.po
	mkdir -p `dirname $@`
	msgfmt -o $@ $^

LANGUAGES=en hu

all: $(foreach lang,$(LANGUAGES),locale/$(lang)/LC_MESSAGES/mlx.mo)

locale/%/LC_MESSAGES/mlx.mo: locale/%/mlx.po locale/%/mlx_delay.po
	mkdir -p `dirname $@`
	msgcat $^ | msgfmt -o $@ -

locale/hu/mlx_delay.po locale/en/mlx_delay.po: dcdatagen.py
	./dcdatagen.py

#!/bin/bash

docker run -d --name virtualairlines.hu -p 40080:80 -v "${HOME}/sources/mlx/virtualairlines.hu":/data:ro virtualairlines.hu

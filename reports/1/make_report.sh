#!/usr/bin/env bash
#
    # -V mainfont="DejaVu Serif" \
    # -V monofont="DejaVu Sans Mono" \
    #
pandoc report.md -f gfm -V linkcolor:blue \
    -V geometry:a4paper \
    -V geometry:margin=3cm \
    --include-before-body cover.tex \
    --pdf-engine=xelatex --toc \
    -H fancy.tex \
    -o report.pdf

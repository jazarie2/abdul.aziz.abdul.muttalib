FROM ghcr.io/xu-cheng/latexmk:debian
WORKDIR /work
COPY . /work
RUN latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex && ls -lah main.pdf

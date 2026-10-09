FROM mcr.microsoft.com/devcontainers/universal:2

RUN set -eu; \
    for source_file in /etc/apt/sources.list.d/*.list; do \
        [ -f "$source_file" ] || continue; \
        sed -i -E '\#^[[:space:]]*deb(-src)?[[:space:]]+(\[[^]]*\][[:space:]]+)?https?://dl[.]yarnpkg[.]com/debian/?([[:space:]]|$)#d' "$source_file"; \
    done
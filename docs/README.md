# `docs` folder

This folder holds **cross-cutting documentation** for the monorepo: architecture guides, technical decisions, conventions, processes, and any material shared across applications, pipelines, agents, and workflows.

- **Main purpose**: provide a single place for “global” project documentation (not tied to one app or agent only).
- **Recommendation**: organize docs by topic (architecture, deployment, data, security, observability, etc.) and keep links from each component’s README to these guides.

> _Spanish version: [README.es.md](./README.es.md)._

## Original infra-40 Evidence

These five PNG files were supplied by the user in `trackflow_infra40_evidencias.zip`.
They were extracted with their original paths and bytes, never regenerated or edited.
Archive CRC, PNG decoding/CRC and equality against archive entries were verified.
Existing website/backoffice screenshots were not overwritten.

| Evidence | Dimensions | Visible content |
| --- | --- | --- |
| [Build](screenshots/infra-40-build.png) | 1920 x 1032 | Docker image build and healthy services |
| [Compose](screenshots/infra-40-compose.png) | 1920 x 1032 | Service status, API health and website proxy HTTP 200 |
| [Website](screenshots/infra-40-website.png) | 1920 x 1140 | Public interface through forwarded port 3000 |
| [Backoffice](screenshots/infra-40-backoffice.png) | 1920 x 1140 | Operations context interface through port 3001 |
| [FastAPI](screenshots/infra-40-fastapi.png) | 1920 x 1032 | Swagger execution of /health, HTTP 200 and status ok |

The Compose capture contains the backoffice proxy command but not its response;
both frontend proxies were separately tested through live HTTP requests.
Screenshots are historical visual evidence, not a substitute for executed checks.

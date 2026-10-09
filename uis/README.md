# `uis` folder

This folder contains **all projects with a user interface** for the cross-functional AI Engineering company project — for example: a public website, admin dashboard frontend, ecommerce UI, customer portals, Streamlit/Gradio app or other frontend-only tools.

The two main projects stored here are:

- **`website`** — the company's public-facing web presence.
- **`backoffice`** — the internal admin application. This is the ideal place to develop multiple solutions within a single project: authentication, people management, operations management, internal communication, and other back-office capabilities.

Organize `uis/` by **different concerns** — each subfolder covers a distinct area of the company (for example, public web vs internal operations) and includes its own technical and functional documentation.

- **Main purpose**: to centralize in a single place all frontend applications that support the company's use cases.
- **Recommendation**: document in this file (or in sub-READMEs) the applications you add, their objective, the technology used, and how to run them.

> _Estas instrucciones también están disponibles en [español](./README.es.md)._

## Container Development

Both applications use Next.js 16.4.0, React 19.3.0 and TypeScript App Router. From the repository root,
`docker compose up --build -d --wait` starts a single `ui` container: website on
port 3000 and backoffice on port 3001. Run `docker compose down` to stop the stack.

`Dockerfile` uses Node 22.14.0. `dev.mjs` installs each lockfile with `npm ci`,
supervises both Next.js processes and shuts down their process groups on signals or
when either process exits. Sources are bind-mounted; named volumes isolate each
application's `node_modules` and `.next` cache from the host. Next.js uses webpack
polling inside Docker. Automatic updates may reload the document; transient state
is not guaranteed to survive every update.

Use relative `/api/...` requests in browser code. Both Next.js servers rewrite to the
internal `api:8000` service; that hostname is never a browser API URL. Local
non-container development defaults to `127.0.0.1:8000`; `API_PROXY_TARGET` is a
server-only override. Localhost, loopback and Codespaces origins are explicitly
allowed in each `next.config.ts`.

**Next.js GAP resolved:** the original content, CSS and navigation are preserved
in App Router. No business features or production deployment were added.
See the user-supplied original evidence in [../docs/README.md](../docs/README.md).

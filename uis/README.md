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

Both existing applications use Vite and TypeScript. From the repository root,
`docker compose up --build -d --wait` starts a single `ui` container: website on
port 3000 and backoffice on port 3001. Run `docker compose down` to stop the stack.

`Dockerfile` uses Node 22.14.0. `dev.mjs` installs each lockfile with `npm ci`,
supervises both Vite processes and shuts down their process groups on signals or
when either process exits. Sources are bind-mounted; named volumes isolate each
application's `node_modules` from the host. Vite HMR uses polling inside Docker.

Use relative `/api/...` requests in browser code. Both Vite servers proxy to the
internal `api:8000` service; that hostname is never a browser API URL. Local
non-container development defaults to `127.0.0.1:8000`; `API_PROXY_TARGET` is a
server-only override. Codespaces domains are allowed via the Compose environment.

**Next.js GAP pending decision:** the assignment names Next.js, but these applications
remain Vite. There is no migration or claim of total compliance in this phase.

# Carpeta `services`

Esta carpeta contiene **todos los servicios backend** (APIs y workers en segundo plano) relacionados con la compañía para el proyecto transversal de AI Engineering.

Cada subcarpeta dentro de `services/` debe corresponder a **un servicio concreto** (por ejemplo `admin-api`, `data-processor-worker`) e incluir su propia documentación técnica y funcional.

- **Propósito principal**: centralizar toda la lógica backend, APIs y consumidores de colas que dan soporte a los casos de uso de la compañía.
- **Recomendación**: documenta en este archivo (o en sub-READMEs) los servicios que vayas añadiendo, su objetivo, tecnología usada y cómo ejecutarlos.

## Servicios actuales

`api/` es el servicio FastAPI de desarrollo (ver [api/README.md](api/README.md)).
`reporting/` no es un servicio aparte: contiene el router `/reporting` del
pipeline de desempeño de negocio, que monta `api/main.py`; su lógica está en
`data/pipelines/business_performance/`. Ver [reporting/README.md](reporting/README.md).

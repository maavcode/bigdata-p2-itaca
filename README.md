# Proyecto 02 · ITACA Relacional

## Descripción y objetivo

Mismo dashboard de análisis académico en Power BI que el Proyecto bigdata-p1-itaca, pero partiendo de una fuente de datos relacional en lugar de documental.

## Arquitectura

*Diagrama del pipeline completo.*

```mermaid
graph LR
    A[SQL] --> B[JDBC]
    B --> C[PostgreSQL]
    C --> D[ETL Spark]
    D --> E[Power BI]
```
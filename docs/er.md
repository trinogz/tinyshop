# TinyShop entity-relationship diagram

An order stores a copy of the service name, description, and price from the
moment it is created. Later edits to the service do not change existing orders.

![TinyShop entity-relationship diagram](er.png)

```mermaid
erDiagram
    CUSTOMER ||--o{ ORDER : places
    SERVICE ||--o{ ORDER : "is referenced by"

    CUSTOMER {
        int id PK
        string name
        string email UK
    }

    SERVICE {
        int id PK
        string name
        string description
        decimal suggested_price
    }

    ORDER {
        int id PK
        int customer_id FK
        int service_id FK
        string service_name "snapshot"
        string service_description "snapshot"
        decimal amount "snapshot of suggested_price"
        datetime created_at
        bool canceled
    }
```

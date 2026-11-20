def create_service(client, name="Cut", description="Basic cut", price="20.00"):
    response = client.post(
        "/services",
        json={"name": name, "description": description, "suggested_price": price},
    )
    assert response.status_code == 201
    return response.json()


def create_customer(client, name="Ada Lovelace", email="ada@example.com"):
    response = client.post("/customers", json={"name": name, "email": email})
    assert response.status_code == 201
    return response.json()


def create_order(client, customer_id, service_id):
    response = client.post(
        "/orders",
        json={"customer_id": customer_id, "service_id": service_id},
    )
    assert response.status_code == 201
    return response.json()


def test_service_create_update_and_get(client):
    created = create_service(client)
    assert created["suggested_price"] == "20.00"

    fetched = client.get(f"/services/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Cut"

    updated = client.patch(
        f"/services/{created['id']}",
        json={"description": "Precision cut", "suggested_price": "35.50"},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["name"] == "Cut"
    assert body["description"] == "Precision cut"
    assert body["suggested_price"] == "35.50"

    missing = client.get("/services/999")
    assert missing.status_code == 404

    invalid = client.post(
        "/services",
        json={"name": "Bad", "description": "Nope", "suggested_price": "0"},
    )
    assert invalid.status_code == 422


def test_customer_create_and_get(client):
    created = create_customer(client, email="Ada@Example.com")
    assert created["email"] == "ada@example.com"

    fetched = client.get(f"/customers/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Ada Lovelace"

    duplicate = client.post(
        "/customers",
        json={"name": "Other", "email": "ada@example.com"},
    )
    assert duplicate.status_code == 409

    missing = client.get("/customers/999")
    assert missing.status_code == 404


def test_order_keeps_service_snapshot(client):
    customer = create_customer(client)
    service = create_service(client, description="Short trim", price="18.00")
    order = create_order(client, customer["id"], service["id"])

    assert order["amount"] == "18.00"
    assert order["service_description"] == "Short trim"
    assert order["service_name"] == "Cut"
    assert order["canceled"] is False

    client.patch(
        f"/services/{service['id']}",
        json={"name": "Restyle", "description": "Full restyle", "suggested_price": "90.00"},
    )
    fetched = client.get(f"/orders/{order['id']}")
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["service_name"] == "Cut"
    assert body["service_description"] == "Short trim"
    assert body["amount"] == "18.00"

    service_now = client.get(f"/services/{service['id']}").json()
    assert service_now["suggested_price"] == "90.00"


def test_cancel_order(client):
    customer = create_customer(client)
    service = create_service(client)
    order = create_order(client, customer["id"], service["id"])

    canceled = client.post(f"/orders/{order['id']}/cancel")
    assert canceled.status_code == 200
    assert canceled.json()["canceled"] is True

    fetched = client.get(f"/orders/{order['id']}")
    assert fetched.json()["canceled"] is True

    again = client.post(f"/orders/{order['id']}/cancel")
    assert again.status_code == 409

    missing = client.post("/orders/999/cancel")
    assert missing.status_code == 404


def test_order_requires_existing_customer_and_service(client):
    customer = create_customer(client)
    service = create_service(client)

    missing_customer = client.post(
        "/orders",
        json={"customer_id": 999, "service_id": service["id"]},
    )
    assert missing_customer.status_code == 404

    missing_service = client.post(
        "/orders",
        json={"customer_id": customer["id"], "service_id": 999},
    )
    assert missing_service.status_code == 404


def test_latest_sales_skip_canceled_orders(client):
    customer = create_customer(client)
    service = create_service(client, price="10.00")
    orders = [create_order(client, customer["id"], service["id"]) for _ in range(12)]
    canceled = client.post(f"/orders/{orders[-1]['id']}/cancel")
    assert canceled.status_code == 200

    response = client.get("/reports/sales/latest")
    assert response.status_code == 200
    body = response.json()
    assert [row["order_id"] for row in body] == [order["id"] for order in orders[-2::-1][:10]]
    assert all(row["customer_name"] == "Ada Lovelace" for row in body)
    assert all(row["service_description"] == "Basic cut" for row in body)
    assert all(row["amount"] == "10.00" for row in body)
    assert orders[-1]["id"] not in {row["order_id"] for row in body}


def test_sales_by_customer_skip_canceled_orders(client):
    ada = create_customer(client, name="Ada", email="ada@example.com")
    grace = create_customer(client, name="Grace", email="grace@example.com")
    only_canceled = create_customer(client, name="Lin", email="lin@example.com")

    cut = create_service(client, name="Cut", description="Cut", price="10.00")
    color = create_service(client, name="Color", description="Color", price="15.00")
    perm = create_service(client, name="Perm", description="Perm", price="100.00")
    trim = create_service(client, name="Trim", description="Trim", price="40.00")

    create_order(client, ada["id"], cut["id"])
    create_order(client, ada["id"], color["id"])
    dropped = create_order(client, ada["id"], perm["id"])
    client.post(f"/orders/{dropped['id']}/cancel")
    create_order(client, grace["id"], trim["id"])
    lin_order = create_order(client, only_canceled["id"], perm["id"])
    client.post(f"/orders/{lin_order['id']}/cancel")

    response = client.get("/reports/sales/by-customer")
    assert response.status_code == 200
    assert response.json() == [
        {
            "customer_id": grace["id"],
            "customer_name": "Grace",
            "order_count": 1,
            "total_amount": "40.00",
        },
        {
            "customer_id": ada["id"],
            "customer_name": "Ada",
            "order_count": 2,
            "total_amount": "25.00",
        },
    ]

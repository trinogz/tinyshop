import { useEffect, useState } from "react";

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body.detail;
    throw new Error(typeof detail === "string" ? detail : "Request failed");
  }
  return body;
}

function money(value) {
  return `$${Number(value).toFixed(2)}`;
}

function when(value) {
  return new Date(value).toLocaleString();
}

export default function App() {
  const [customers, setCustomers] = useState([]);
  const [services, setServices] = useState([]);
  const [orders, setOrders] = useState([]);
  const [latest, setLatest] = useState([]);
  const [byCustomer, setByCustomer] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [customer, setCustomer] = useState({ name: "", email: "" });
  const [service, setService] = useState({ name: "", description: "", suggested_price: "" });
  const [editId, setEditId] = useState("");
  const [edit, setEdit] = useState({ description: "", suggested_price: "" });
  const [order, setOrder] = useState({ customer_id: "", service_id: "" });

  async function reload() {
    const [nextCustomers, nextServices, nextOrders, nextLatest, nextByCustomer] = await Promise.all([
      api("/customers"),
      api("/services"),
      api("/orders"),
      api("/reports/sales/latest"),
      api("/reports/sales/by-customer"),
    ]);
    setCustomers(nextCustomers);
    setServices(nextServices);
    setOrders(nextOrders);
    setLatest(nextLatest);
    setByCustomer(nextByCustomer);
  }

  useEffect(() => {
    reload().catch((err) => setError(err.message));
  }, []);

  async function run(action) {
    setError("");
    setBusy(true);
    try {
      await action();
      await reload();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function chooseService(id) {
    setEditId(id);
    const selected = services.find((item) => String(item.id) === id);
    setEdit({
      description: selected ? selected.description : "",
      suggested_price: selected ? selected.suggested_price : "",
    });
  }

  const selectedService = services.find((item) => String(item.id) === order.service_id);

  return (
    <main>
      <header>
        <h1>TinyShop</h1>
        <p>Customers, services, and orders.</p>
      </header>

      {error ? <div className="error">{error}</div> : null}

      <div className="grid">
        <section>
          <h2>Customers</h2>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              run(async () => {
                await api("/customers", { method: "POST", body: JSON.stringify(customer) });
                setCustomer({ name: "", email: "" });
              });
            }}
          >
            <label>
              Name
              <input
                value={customer.name}
                onChange={(event) => setCustomer({ ...customer, name: event.target.value })}
                required
              />
            </label>
            <label>
              Email
              <input
                type="email"
                value={customer.email}
                onChange={(event) => setCustomer({ ...customer, email: event.target.value })}
                required
              />
            </label>
            <button disabled={busy}>Add customer</button>
          </form>
          {customers.length === 0 ? <p className="empty">No customers yet.</p> : (
            <table>
              <tbody>
                {customers.map((item) => (
                  <tr key={item.id}>
                    <td>{item.name}</td>
                    <td className="muted">{item.email}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section>
          <h2>Services</h2>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              run(async () => {
                await api("/services", { method: "POST", body: JSON.stringify(service) });
                setService({ name: "", description: "", suggested_price: "" });
              });
            }}
          >
            <label>
              Name
              <input
                value={service.name}
                onChange={(event) => setService({ ...service, name: event.target.value })}
                required
              />
            </label>
            <label>
              Description
              <textarea
                value={service.description}
                onChange={(event) => setService({ ...service, description: event.target.value })}
                required
              />
            </label>
            <label>
              Suggested price
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={service.suggested_price}
                onChange={(event) => setService({ ...service, suggested_price: event.target.value })}
                required
              />
            </label>
            <button disabled={busy}>Add service</button>
          </form>

          {services.length > 0 ? (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                run(() => api(`/services/${editId}`, {
                  method: "PATCH",
                  body: JSON.stringify({
                    description: edit.description,
                    suggested_price: edit.suggested_price,
                  }),
                }));
              }}
            >
              <label>
                Edit service
                <select value={editId} onChange={(event) => chooseService(event.target.value)} required>
                  <option value="">Select</option>
                  {services.map((item) => (
                    <option key={item.id} value={item.id}>{item.name} · {money(item.suggested_price)}</option>
                  ))}
                </select>
              </label>
              <label>
                Description
                <textarea
                  value={edit.description}
                  onChange={(event) => setEdit({ ...edit, description: event.target.value })}
                  required
                />
              </label>
              <label>
                Suggested price
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={edit.suggested_price}
                  onChange={(event) => setEdit({ ...edit, suggested_price: event.target.value })}
                  required
                />
              </label>
              <button disabled={busy || !editId}>Save service</button>
            </form>
          ) : <p className="empty">No services yet.</p>}
        </section>
      </div>

      <section>
        <h2>Orders</h2>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            run(async () => {
              await api("/orders", {
                method: "POST",
                body: JSON.stringify({
                  customer_id: Number(order.customer_id),
                  service_id: Number(order.service_id),
                }),
              });
              setOrder({ customer_id: "", service_id: "" });
            });
          }}
        >
          <div className="grid">
            <label>
              Customer
              <select
                value={order.customer_id}
                onChange={(event) => setOrder({ ...order, customer_id: event.target.value })}
                required
              >
                <option value="">Select</option>
                {customers.map((item) => (
                  <option key={item.id} value={item.id}>{item.name}</option>
                ))}
              </select>
            </label>
            <label>
              Service
              <select
                value={order.service_id}
                onChange={(event) => setOrder({ ...order, service_id: event.target.value })}
                required
              >
                <option value="">Select</option>
                {services.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name} · {money(item.suggested_price)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="row-actions">
            <span className="muted">
              {selectedService
                ? `Order amount ${money(selectedService.suggested_price)}. The description is saved with the order.`
                : "The order keeps the service description and price from this moment."}
            </span>
            <button disabled={busy}>Create order</button>
          </div>
        </form>

        {orders.length === 0 ? <p className="empty">No orders yet.</p> : (
          <table>
            <thead>
              <tr>
                <th>Customer</th>
                <th>Service</th>
                <th>Amount</th>
                <th>Created</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {orders.map((item) => {
                const owner = customers.find((person) => person.id === item.customer_id);
                return (
                  <tr key={item.id}>
                    <td>{owner ? owner.name : item.customer_id}</td>
                    <td>
                      {item.service_name}
                      <div className="muted">{item.service_description}</div>
                    </td>
                    <td>{money(item.amount)}</td>
                    <td>{when(item.created_at)}</td>
                    <td>
                      {item.canceled ? <span className="muted">Canceled</span> : (
                        <button
                          className="quiet"
                          type="button"
                          disabled={busy}
                          onClick={() => run(() => api(`/orders/${item.id}/cancel`, { method: "POST" }))}
                        >
                          Cancel
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>

      <div className="grid">
        <section>
          <h2>Last 10 sales</h2>
          <p>Newest first. Canceled orders are left out.</p>
          {latest.length === 0 ? <p className="empty">No sales yet.</p> : (
            <table>
              <thead>
                <tr>
                  <th>Customer</th>
                  <th>Description</th>
                  <th>Amount</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {latest.map((item) => (
                  <tr key={item.order_id}>
                    <td>{item.customer_name}</td>
                    <td>{item.service_description}</td>
                    <td>{money(item.amount)}</td>
                    <td>{when(item.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section>
          <h2>Sales by customer</h2>
          <p>Sorted by total amount. Canceled orders are left out.</p>
          {byCustomer.length === 0 ? <p className="empty">No sales yet.</p> : (
            <table>
              <thead>
                <tr>
                  <th>Customer</th>
                  <th>Orders</th>
                  <th>Total</th>
                </tr>
              </thead>
              <tbody>
                {byCustomer.map((item) => (
                  <tr key={item.customer_id}>
                    <td>{item.customer_name}</td>
                    <td>{item.order_count}</td>
                    <td>{money(item.total_amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>
    </main>
  );
}

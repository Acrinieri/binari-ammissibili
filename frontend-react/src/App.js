import React, { useEffect, useState } from "react";
import axios from "axios";

function App() {
  const [orders, setOrders] = useState([]);
  const [newOrder, setNewOrder] = useState({ item: "", quantity: 1 });
  const [error, setError] = useState("");

  useEffect(() => {
    axios
      .get("http://127.0.0.1:8000/orders")
      .then((res) => {
        setOrders(res.data);
        setError("");
      })
      .catch(() => setError("Unable to reach the API. Is the backend running?"));
  }, []);

  const createOrder = (e) => {
    e.preventDefault();

    axios
      .post("http://127.0.0.1:8000/orders", {
        item: newOrder.item,
        quantity: parseInt(newOrder.quantity, 10),
      })
      .then((res) => {
        setOrders([...orders, res.data]);
        setNewOrder({ item: "", quantity: 1 });
        setError("");
      })
      .catch(() =>
        setError("Unable to save the order. Check the backend logs.")
      );
  };

  return (
    <div style={{ padding: "40px", fontFamily: "Arial, sans-serif" }}>
      <h1>Order Management</h1>

      <form onSubmit={createOrder} style={{ marginBottom: 24 }}>
        <input
          type="text"
          placeholder="Item"
          value={newOrder.item}
          onChange={(e) => setNewOrder({ ...newOrder, item: e.target.value })}
          required
        />
        <input
          type="number"
          placeholder="Quantity"
          value={newOrder.quantity}
          onChange={(e) =>
            setNewOrder({ ...newOrder, quantity: e.target.value })
          }
          min="1"
          required
          style={{ marginLeft: 8 }}
        />
        <button type="submit" style={{ marginLeft: 8 }}>
          Add Order
        </button>
      </form>

      {error && (
        <div style={{ marginBottom: 24, color: "#b00020", fontWeight: "bold" }}>
          {error}
        </div>
      )}

      <h2>Existing Orders</h2>
      <ul>
        {orders.map((o) => (
          <li key={o.id}>
            {o.item} - {o.quantity}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default App;

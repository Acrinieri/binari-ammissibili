import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";

const API_BASE = "http://127.0.0.1:8000";

const TRAIN_CATEGORIES = [
  "REG",
  "IC",
  "ES*",
  "FR",
  "FA",
  "FB",
  "LH",
  "EXP",
  "NCL",
  "INV",
];

const TRACK_FORM_DEFAULT = {
  name: "",
  marciapiede_complessivo_m: "0",
  marciapiede_alto_m: "0",
  marciapiede_basso_m: "0",
  capacita_funzionale_m: "",
};

const toNumeric = (value) => {
  const parsed = Number.parseInt(value, 10);
  return Number.isNaN(parsed) ? 0 : parsed;
};
const toOptionalNumeric = (value) =>
  value === "" || value === null ? null : Number.parseInt(value, 10) || 0;

function buildPayload(data) {
  return {
    name: data.name.trim(),
    marciapiede_complessivo_m: toNumeric(data.marciapiede_complessivo_m),
    marciapiede_alto_m: toNumeric(data.marciapiede_alto_m),
    marciapiede_basso_m: toNumeric(data.marciapiede_basso_m),
    capacita_funzionale_m: toOptionalNumeric(data.capacita_funzionale_m),
  };
}

function App() {
  const [trackData, setTrackData] = useState({});
  const [adminTracks, setAdminTracks] = useState([]);
  const [loadingDataset, setLoadingDataset] = useState(true);
  const [datasetError, setDatasetError] = useState("");

  const [form, setForm] = useState({
    trainCode: "",
    trainLength: "",
    trainCategory: "REG",
    plannedTrack: "",
    isPrm: false,
  });
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [newTrack, setNewTrack] = useState(TRACK_FORM_DEFAULT);
  const [editingTrack, setEditingTrack] = useState(null);
  const [adminMessage, setAdminMessage] = useState("");
  const [adminError, setAdminError] = useState("");

  const refreshAll = () => {
    setLoadingDataset(true);
    Promise.allSettled([
      axios.get(`${API_BASE}/tracks`),
      axios.get(`${API_BASE}/admin/tracks`),
    ])
      .then(([tracksRes, adminRes]) => {
        if (tracksRes.status === "fulfilled") {
          setTrackData(tracksRes.value.data.tracks || {});
          setDatasetError("");
        } else {
          setDatasetError(
            "Impossibile caricare i dati dei binari. Backend attivo?"
          );
        }

        if (adminRes.status === "fulfilled") {
          setAdminTracks(adminRes.value.data || []);
          setAdminError("");
        } else {
          setAdminError("Impossibile caricare la lista dei binari.");
        }
      })
      .finally(() => setLoadingDataset(false));
  };

  useEffect(() => {
    refreshAll();
  }, []);

  const trackNames = useMemo(() => Object.keys(trackData).sort(), [trackData]);

  const onFieldChange = (field) => (event) => {
    const value =
      field === "isPrm" ? event.target.checked : event.target.value;
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    setLoading(true);
    setSuggestions([]);
    setError("");

    axios
      .post(`${API_BASE}/tracks/suggestions`, {
        train_code: form.trainCode,
        train_length_m: Number(form.trainLength),
        train_category: form.trainCategory,
        planned_track: form.plannedTrack || null,
        is_prm: form.isPrm,
      })
      .then((res) => {
        setSuggestions(res.data.alternatives || []);
        if (!res.data.alternatives || res.data.alternatives.length === 0) {
          setError("Nessun binario compatibile trovato.");
        }
      })
      .catch((err) => {
        const detail =
          err.response?.data?.detail ||
          "Errore durante il calcolo delle alternative.";
        setError(detail);
      })
      .finally(() => setLoading(false));
  };

  const onNewTrackFieldChange = (field) => (event) => {
    const { value } = event.target;
    setNewTrack((prev) => ({ ...prev, [field]: value }));
  };

  const onEditTrackFieldChange = (field) => (event) => {
    if (!editingTrack) return;
    const { value } = event.target;
    setEditingTrack((prev) => ({ ...prev, [field]: value }));
  };

  const resetAdminFeedback = () => {
    setAdminError("");
    setAdminMessage("");
  };

  const handleCreateTrack = (event) => {
    event.preventDefault();
    resetAdminFeedback();

    if (!newTrack.name.trim()) {
      setAdminError("Il nome del binario è obbligatorio.");
      return;
    }

    axios
      .post(`${API_BASE}/admin/tracks`, buildPayload(newTrack))
      .then(() => {
        setAdminMessage("Binario creato correttamente.");
        setNewTrack(TRACK_FORM_DEFAULT);
        refreshAll();
      })
      .catch((err) => {
        const detail =
          err.response?.data?.detail || "Impossibile creare il binario.";
        setAdminError(detail);
      });
  };

  const startEditing = (track) => {
    setEditingTrack({
      id: track.id,
      name: track.name,
      marciapiede_complessivo_m: String(track.marciapiede_complessivo_m ?? 0),
      marciapiede_alto_m: String(track.marciapiede_alto_m ?? 0),
      marciapiede_basso_m: String(track.marciapiede_basso_m ?? 0),
      capacita_funzionale_m:
        track.capacita_funzionale_m !== null && track.capacita_funzionale_m !== undefined
          ? String(track.capacita_funzionale_m)
          : "",
    });
    resetAdminFeedback();
  };

  const cancelEditing = () => {
    setEditingTrack(null);
  };

  const saveEditing = () => {
    if (!editingTrack) return;
    if (!editingTrack.name.trim()) {
      setAdminError("Il nome del binario è obbligatorio.");
      return;
    }

    axios
      .put(
        `${API_BASE}/admin/tracks/${editingTrack.id}`,
        buildPayload(editingTrack)
      )
      .then(() => {
        setAdminMessage("Binario aggiornato.");
        setEditingTrack(null);
        refreshAll();
      })
      .catch((err) => {
        const detail =
          err.response?.data?.detail || "Impossibile aggiornare il binario.";
        setAdminError(detail);
      });
  };

  const deleteTrack = (trackId) => {
    resetAdminFeedback();
    const track = adminTracks.find((t) => t.id === trackId);
    const confirmDelete = window.confirm(
      `Eliminare il binario "${track?.name || trackId}"?`
    );
    if (!confirmDelete) {
      return;
    }

    axios
      .delete(`${API_BASE}/admin/tracks/${trackId}`)
      .then(() => {
        setAdminMessage("Binario eliminato.");
        if (editingTrack?.id === trackId) {
          setEditingTrack(null);
        }
        refreshAll();
      })
      .catch(() => {
        setAdminError("Impossibile eliminare il binario.");
      });
  };

  return (
    <div style={{ padding: "32px", fontFamily: "Inter, Arial, sans-serif" }}>
      <header style={{ marginBottom: 24 }}>
        <h1 style={{ margin: 0 }}>Binari Ammissibili</h1>
        <p style={{ color: "#555" }}>
          Inserisci i dettagli del treno per ottenere le alternative disponibili
          e gestisci i binari del database.
        </p>
      </header>

      {/* Sezione calcolo suggerimenti */}
      <section
        style={{
          backgroundColor: "#f7f9fc",
          padding: 24,
          borderRadius: 12,
          marginBottom: 32,
          border: "1px solid #dbe3f4",
        }}
      >
        <form onSubmit={handleSubmit} style={{ display: "grid", gap: 16 }}>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <label style={{ flex: "1 1 160px" }}>
              <span style={{ display: "block", marginBottom: 4 }}>
                Numero treno
              </span>
              <input
                type="text"
                required
                value={form.trainCode}
                onChange={onFieldChange("trainCode")}
                style={{ width: "100%", padding: 8 }}
              />
            </label>

            <label style={{ flex: "1 1 160px" }}>
              <span style={{ display: "block", marginBottom: 4 }}>
                Lunghezza (m)
              </span>
              <input
                type="number"
                min="1"
                required
                value={form.trainLength}
                onChange={onFieldChange("trainLength")}
                style={{ width: "100%", padding: 8 }}
              />
            </label>

            <label style={{ flex: "1 1 180px" }}>
              <span style={{ display: "block", marginBottom: 4 }}>
                Categoria treno
              </span>
              <select
                value={form.trainCategory}
                onChange={onFieldChange("trainCategory")}
                style={{ width: "100%", padding: 8 }}
              >
                {TRAIN_CATEGORIES.map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
            </label>

            <label style={{ flex: "1 1 180px" }}>
              <span style={{ display: "block", marginBottom: 4 }}>
                Binario previsto
              </span>
              <select
                value={form.plannedTrack}
                onChange={onFieldChange("plannedTrack")}
                style={{ width: "100%", padding: 8 }}
              >
                <option value="">Non specificato</option>
                {trackNames.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <label style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
            <input
              type="checkbox"
              checked={form.isPrm}
              onChange={onFieldChange("isPrm")}
            />
            Treno PRM
          </label>

          <button
            type="submit"
            disabled={loading}
            style={{
              width: "fit-content",
              padding: "10px 24px",
              backgroundColor: "#2563eb",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              cursor: "pointer",
            }}
          >
            {loading ? "Calcolo in corso..." : "Calcola alternative"}
          </button>
        </form>

        {error && (
          <div
            style={{
              marginTop: 16,
              padding: 12,
              borderRadius: 8,
              backgroundColor: "#fdecea",
              color: "#b71c1c",
            }}
          >
            {error}
          </div>
        )}
      </section>

      {/* Sezione suggerimenti */}
      <section style={{ marginBottom: 32 }}>
        <h2 style={{ marginBottom: 12 }}>Alternative suggerite</h2>
        {loading ? (
          <p>Calcolo in corso...</p>
        ) : suggestions.length > 0 ? (
          <ol>
            {suggestions.map(({ track, reason }) => (
              <li key={track} style={{ marginBottom: 12 }}>
                <div style={{ fontWeight: 600 }}>{track}</div>
                <div style={{ color: "#444", fontSize: 14 }}>{reason}</div>
              </li>
            ))}
          </ol>
        ) : (
          <p style={{ color: "#555" }}>
            Compila il form per ottenere una nuova valutazione.
          </p>
        )}
      </section>

      {/* Tabella visualizzazione dataset */}
      <section style={{ marginBottom: 48 }}>
        <h2 style={{ marginBottom: 12 }}>Binari disponibili</h2>
        {loadingDataset ? (
          <p>Caricamento...</p>
        ) : datasetError ? (
          <div
            style={{
              marginTop: 8,
              padding: 12,
              borderRadius: 8,
              backgroundColor: "#fdecea",
              color: "#b71c1c",
            }}
          >
            {datasetError}
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                minWidth: 480,
              }}
            >
              <thead>
                <tr style={{ backgroundColor: "#eef2ff" }}>
                  <th style={{ textAlign: "left", padding: 8 }}>Binario</th>
                  <th style={{ textAlign: "right", padding: 8 }}>Totale (m)</th>
                  <th style={{ textAlign: "right", padding: 8 }}>Alto (m)</th>
                  <th style={{ textAlign: "right", padding: 8 }}>Basso (m)</th>
                  <th style={{ textAlign: "right", padding: 8 }}>Capacita (m)</th>
                </tr>
              </thead>
              <tbody>
                {trackNames.map((name) => {
                  const track = trackData[name];
                  return (
                    <tr key={name} style={{ borderBottom: "1px solid #e5e7eb" }}>
                      <td style={{ padding: 8 }}>{name}</td>
                      <td style={{ padding: 8, textAlign: "right" }}>
                        {track.marciapiede_complessivo_m}
                      </td>
                      <td style={{ padding: 8, textAlign: "right" }}>
                        {track.marciapiede_alto_m}
                      </td>
                      <td style={{ padding: 8, textAlign: "right" }}>
                        {track.marciapiede_basso_m}
                      </td>
                      <td style={{ padding: 8, textAlign: "right" }}>
                        {track.capacita_funzionale_m ?? "-"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Gestione amministrativa */}
      <section>
        <h2 style={{ marginBottom: 12 }}>Gestione binari</h2>

        {adminError && (
          <div
            style={{
              marginBottom: 12,
              padding: 12,
              borderRadius: 8,
              backgroundColor: "#fdecea",
              color: "#b71c1c",
            }}
          >
            {adminError}
          </div>
        )}

        {adminMessage && (
          <div
            style={{
              marginBottom: 12,
              padding: 12,
              borderRadius: 8,
              backgroundColor: "#e6f4ea",
              color: "#1b5e20",
            }}
          >
            {adminMessage}
          </div>
        )}

        <form
          onSubmit={handleCreateTrack}
          style={{
            display: "grid",
            gap: 8,
            marginBottom: 24,
            padding: 16,
            border: "1px solid #dbe3f4",
            borderRadius: 8,
            backgroundColor: "#f9fbff",
            maxWidth: 640,
          }}
        >
          <h3 style={{ margin: 0 }}>Aggiungi nuovo binario</h3>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <label style={{ flex: "1 1 160px" }}>
              Nome
              <input
                type="text"
                required
                value={newTrack.name}
                onChange={onNewTrackFieldChange("name")}
                style={{ width: "100%", padding: 8, marginTop: 4 }}
              />
            </label>
            <label style={{ flex: "1 1 160px" }}>
              Totale (m)
              <input
                type="number"
                min="0"
                required
                value={newTrack.marciapiede_complessivo_m}
                onChange={onNewTrackFieldChange("marciapiede_complessivo_m")}
                style={{ width: "100%", padding: 8, marginTop: 4 }}
              />
            </label>
            <label style={{ flex: "1 1 160px" }}>
              Alto (m)
              <input
                type="number"
                min="0"
                required
                value={newTrack.marciapiede_alto_m}
                onChange={onNewTrackFieldChange("marciapiede_alto_m")}
                style={{ width: "100%", padding: 8, marginTop: 4 }}
              />
            </label>
            <label style={{ flex: "1 1 160px" }}>
              Basso (m)
              <input
                type="number"
                min="0"
                required
                value={newTrack.marciapiede_basso_m}
                onChange={onNewTrackFieldChange("marciapiede_basso_m")}
                style={{ width: "100%", padding: 8, marginTop: 4 }}
              />
            </label>
            <label style={{ flex: "1 1 160px" }}>
              Capacita funzionale (m)
              <input
                type="number"
                min="0"
                value={newTrack.capacita_funzionale_m}
                onChange={onNewTrackFieldChange("capacita_funzionale_m")}
                style={{ width: "100%", padding: 8, marginTop: 4 }}
                placeholder="(opzionale)"
              />
            </label>
          </div>
          <button
            type="submit"
            style={{
              width: "fit-content",
              padding: "8px 20px",
              backgroundColor: "#047857",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              cursor: "pointer",
            }}
          >
            Aggiungi binario
          </button>
        </form>

        <div style={{ overflowX: "auto" }}>
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              minWidth: 640,
            }}
          >
            <thead>
              <tr style={{ backgroundColor: "#eef2ff" }}>
                <th style={{ textAlign: "left", padding: 8 }}>Nome</th>
                <th style={{ textAlign: "right", padding: 8 }}>Totale</th>
                <th style={{ textAlign: "right", padding: 8 }}>Alto</th>
                <th style={{ textAlign: "right", padding: 8 }}>Basso</th>
                <th style={{ textAlign: "right", padding: 8 }}>Capacita</th>
                <th style={{ textAlign: "center", padding: 8 }}>Azioni</th>
              </tr>
            </thead>
            <tbody>
              {adminTracks.map((track) => {
                const isEditing = editingTrack?.id === track.id;
                return (
                  <tr key={track.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                    <td style={{ padding: 8 }}>
                      {isEditing ? (
                        <input
                          type="text"
                          value={editingTrack.name}
                          onChange={onEditTrackFieldChange("name")}
                          style={{ width: "100%", padding: 6 }}
                        />
                      ) : (
                        track.name
                      )}
                    </td>
                    <td style={{ padding: 8, textAlign: "right" }}>
                      {isEditing ? (
                        <input
                          type="number"
                          min="0"
                          value={editingTrack.marciapiede_complessivo_m}
                          onChange={onEditTrackFieldChange("marciapiede_complessivo_m")}
                          style={{ width: "100%", padding: 6 }}
                        />
                      ) : (
                        track.marciapiede_complessivo_m
                      )}
                    </td>
                    <td style={{ padding: 8, textAlign: "right" }}>
                      {isEditing ? (
                        <input
                          type="number"
                          min="0"
                          value={editingTrack.marciapiede_alto_m}
                          onChange={onEditTrackFieldChange("marciapiede_alto_m")}
                          style={{ width: "100%", padding: 6 }}
                        />
                      ) : (
                        track.marciapiede_alto_m
                      )}
                    </td>
                    <td style={{ padding: 8, textAlign: "right" }}>
                      {isEditing ? (
                        <input
                          type="number"
                          min="0"
                          value={editingTrack.marciapiede_basso_m}
                          onChange={onEditTrackFieldChange("marciapiede_basso_m")}
                          style={{ width: "100%", padding: 6 }}
                        />
                      ) : (
                        track.marciapiede_basso_m
                      )}
                    </td>
                    <td style={{ padding: 8, textAlign: "right" }}>
                      {isEditing ? (
                        <input
                          type="number"
                          min="0"
                          value={editingTrack.capacita_funzionale_m}
                          onChange={onEditTrackFieldChange("capacita_funzionale_m")}
                          style={{ width: "100%", padding: 6 }}
                          placeholder="(opzionale)"
                        />
                      ) : (
                        track.capacita_funzionale_m ?? "-"
                      )}
                    </td>
                    <td style={{ padding: 8, textAlign: "center", whiteSpace: "nowrap" }}>
                      {isEditing ? (
                        <>
                          <button
                            type="button"
                            onClick={saveEditing}
                            style={{ marginRight: 8, padding: "6px 12px" }}
                          >
                            Salva
                          </button>
                          <button
                            type="button"
                            onClick={cancelEditing}
                            style={{ padding: "6px 12px" }}
                          >
                            Annulla
                          </button>
                        </>
                      ) : (
                        <button
                          type="button"
                          onClick={() => startEditing(track)}
                          style={{ marginRight: 8, padding: "6px 12px" }}
                        >
                          Modifica
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => deleteTrack(track.id)}
                        style={{ padding: "6px 12px" }}
                      >
                        Elimina
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

export default App;

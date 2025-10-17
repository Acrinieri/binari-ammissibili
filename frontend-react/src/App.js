import React, { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import "./App.css";

const API_BASE =
  process.env.REACT_APP_API_BASE ??
  window.__BINARI_API_BASE__ ??
  "http://127.0.0.1:8000";

const ADMIN_TOKEN_HEADER = "X-Admin-Token";
const ADMIN_STORAGE_KEY = "binariAdminToken";

const hasWindow =
  typeof window !== "undefined" && typeof window.localStorage !== "undefined";

const getStoredAdminToken = () => {
  if (!hasWindow) {
    return "";
  }
  return window.localStorage.getItem(ADMIN_STORAGE_KEY) ?? "";
};

if (!axios.__BINARI_ADMIN_INTERCEPTOR_SET) {
  axios.interceptors.request.use((config) => {
    const url = config.url ?? "";
    if (url.includes("/admin")) {
      const token = getStoredAdminToken();
      if (token) {
        config.headers = config.headers ?? {};
        config.headers[ADMIN_TOKEN_HEADER] = token;
      }
    }
    return config;
  });
  axios.__BINARI_ADMIN_INTERCEPTOR_SET = true;
}

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
  signal_code: "",
};

const DEFAULT_TRAIN = {
  trainCode: "",
  trainLength: "",
  trainCategory: "REG",
  plannedSignal: "",
  isPrm: false,
};

const toNumeric = (value) => {
  const parsed = Number.parseInt(value, 10);
  return Number.isNaN(parsed) ? 0 : parsed;
};
const toOptionalNumeric = (value) =>
  value === "" || value === null ? null : Number.parseInt(value, 10) || 0;

function buildPayload(data) {
  const signalCode =
    typeof data.signal_code === "string" && data.signal_code.trim().length > 0
      ? data.signal_code.trim()
      : null;

  return {
    name: data.name.trim(),
    marciapiede_complessivo_m: toNumeric(data.marciapiede_complessivo_m),
    marciapiede_alto_m: toNumeric(data.marciapiede_alto_m),
    marciapiede_basso_m: toNumeric(data.marciapiede_basso_m),
    capacita_funzionale_m: toOptionalNumeric(data.capacita_funzionale_m),
    signal_code: signalCode,
  };
}

function App() {
  const [trackData, setTrackData] = useState({});
  const [adminTracks, setAdminTracks] = useState([]);
  const [categoryRules, setCategoryRules] = useState([]);
  const [priorityConfigs, setPriorityConfigs] = useState([]);
  const [loadingDataset, setLoadingDataset] = useState(true);
  const [datasetError, setDatasetError] = useState("");
  const [rulesError, setRulesError] = useState("");
  const [priorityError, setPriorityError] = useState("");

  const [trainForms, setTrainForms] = useState([DEFAULT_TRAIN]);
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [newTrack, setNewTrack] = useState(TRACK_FORM_DEFAULT);
  const [editingTrack, setEditingTrack] = useState(null);
  const [adminMessage, setAdminMessage] = useState("");
  const [adminError, setAdminError] = useState("");
  const [editingRule, setEditingRule] = useState(null);
  const [editingPriority, setEditingPriority] = useState(null);
  const [ruleMessage, setRuleMessage] = useState("");
  const [priorityMessage, setPriorityMessage] = useState("");
  const [adminToken, setAdminToken] = useState(() => getStoredAdminToken());
  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [loginError, setLoginError] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);
  const hasAdminAccess = Boolean(adminToken);

  useEffect(() => {
    if (!hasWindow) {
      return;
    }
    if (adminToken) {
      window.localStorage.setItem(ADMIN_STORAGE_KEY, adminToken);
    } else {
      window.localStorage.removeItem(ADMIN_STORAGE_KEY);
    }
  }, [adminToken]);

  useEffect(() => {
    if (adminToken) {
      axios.defaults.headers.common[ADMIN_TOKEN_HEADER] = adminToken;
    } else {
      delete axios.defaults.headers.common[ADMIN_TOKEN_HEADER];
    }
  }, [adminToken]);

  const availableCriteria = [
    { key: "priority_class", label: "Priorita di categoria" },
    { key: "proximity", label: "Prossimita numerica" },
    { key: "similarity", label: "Somiglianza con binario previsto" },
    { key: "same_number", label: "Bonus stesso numero" },
    { key: "length_delta", label: "Delta lunghezza" },
    { key: "track_number", label: "Numero binario" },
    { key: "suffix_flag", label: "Suffisso presente" },
    { key: "no_platform_first", label: "Senza marciapiede" },
    { key: "bis_preference", label: "Preferenza BIS" },
  ];

  const getCriterionLabel = (key) => {
    const option = availableCriteria.find((item) => item.key === key);
    return option ? option.label : key;
  };

  const loadTracks = useCallback(() => {
    setLoadingDataset(true);
    axios
      .get(`${API_BASE}/tracks`)
      .then((response) => {
        setTrackData(response.data.tracks || {});
        setDatasetError("");
      })
      .catch(() => {
        setDatasetError(
          "Impossibile caricare i dati dei binari. Backend attivo?"
        );
      })
      .finally(() => setLoadingDataset(false));
  }, []);

  const loadAdminData = useCallback(() => {
    if (!hasAdminAccess) {
      setAdminTracks([]);
      setCategoryRules([]);
      setPriorityConfigs([]);
      setAdminError("");
      setRulesError("");
      setPriorityError("");
      return;
    }

    Promise.allSettled([
      axios.get(`${API_BASE}/admin/tracks`),
      axios.get(`${API_BASE}/admin/config/category-rules`),
      axios.get(`${API_BASE}/admin/config/priority-configs`),
    ]).then(([tracksRes, rulesRes, priorityRes]) => {
      if (tracksRes.status === "fulfilled") {
        setAdminTracks(tracksRes.value.data || []);
        setAdminError("");
      } else {
        setAdminError("Impossibile caricare la lista dei binari.");
      }

      if (rulesRes.status === "fulfilled") {
        setCategoryRules(rulesRes.value.data || []);
        setRulesError("");
      } else {
        setRulesError("Impossibile caricare le regole di categoria.");
      }

      if (priorityRes.status === "fulfilled") {
        setPriorityConfigs(priorityRes.value.data || []);
        setPriorityError("");
      } else {
        setPriorityError("Impossibile caricare le priorita configurate.");
      }
    });
  }, [hasAdminAccess]);

  const refreshAll = useCallback(() => {
    loadTracks();
    loadAdminData();
  }, [loadTracks, loadAdminData]);

  useEffect(() => {
    loadTracks();
  }, [loadTracks]);

  useEffect(() => {
    loadAdminData();
  }, [loadAdminData]);

  const onLoginFieldChange = (field) => (event) => {
    const value = event.target.value;
    setLoginForm((prev) => ({ ...prev, [field]: value }));
  };

  const submitLogin = (event) => {
    event.preventDefault();
    const username = loginForm.username.trim();
    const password = loginForm.password;
    if (!username || !password) {
      setLoginError("Inserisci username e password.");
      return;
    }

    setLoginError("");
    setLoginLoading(true);
    axios
      .post(`${API_BASE}/admin/login`, {
        username,
        password,
      })
      .then((response) => {
        const token = response.data?.token;
        if (token) {
          setAdminToken(token);
          setLoginForm({ username: "", password: "" });
          setLoginError("");
        } else {
          setLoginError("Risposta del server non valida.");
        }
      })
      .catch((error) => {
        const detail =
          error.response?.data?.detail || "Credenziali non valide.";
        setLoginError(detail);
      })
      .finally(() => setLoginLoading(false));
  };

  const handleLogout = () => {
    setAdminToken("");
    setLoginForm({ username: "", password: "" });
    setAdminTracks([]);
    setCategoryRules([]);
    setPriorityConfigs([]);
    setAdminMessage("");
    setAdminError("");
    setRuleMessage("");
    setRulesError("");
    setPriorityMessage("");
    setPriorityError("");
  };

  const trackNames = useMemo(() => Object.keys(trackData).sort(), [trackData]);

  const trackSignalOptions = useMemo(() => {
    return Object.entries(trackData)
      .filter(([, info]) => {
        const code = info.signal_code;
        return code && String(code).trim() && String(code).toUpperCase() !== "TBD";
      })
      .map(([name, info]) => {
        const code = String(info.signal_code).trim();
        return {
          value: code,
          label: `${code} (${name})`,
          name,
        };
      })
      .sort((a, b) => a.value.localeCompare(b.value));
  }, [trackData]);

  const signalToTrackName = useMemo(() => {
    const mapping = {};
    Object.entries(trackData).forEach(([name, info]) => {
      const code = (info.signal_code ?? "").toString().trim();
      if (code) {
        mapping[code.toUpperCase()] = name;
      }
    });
    return mapping;
  }, [trackData]);

  const describeSignal = (value) => {
    if (!value) {
      return { signal: "", base: "", trackName: null };
    }
    const raw = String(value).trim();
    if (!raw) {
      return { signal: "", base: "", trackName: null };
    }
    const hasSuffix = raw.toLowerCase().endsWith("f");
    const base = hasSuffix ? raw.slice(0, -1) : raw;
    const trackName = signalToTrackName[base.toUpperCase()] ?? null;
    return { signal: raw, base, trackName };
  };

  const updateTrainField = (index, field) => (event) => {
    const value =
      field === "isPrm" ? event.target.checked : event.target.value;
    setTrainForms((prev) =>
      prev.map((item, idx) =>
        idx === index ? { ...item, [field]: value } : item
      )
    );
  };

  const addTrainForm = () => {
    setTrainForms((prev) => [...prev, { ...DEFAULT_TRAIN }]);
  };

  const removeTrainForm = (index) => {
    setTrainForms((prev) =>
      prev.length > 1 ? prev.filter((_, idx) => idx !== index) : prev
    );
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    setLoading(true);
    setSuggestions([]);
    setError("");

    const payloadTrains = [];
    for (const item of trainForms) {
      const trainCode = item.trainCode.trim();
      const length = Number(item.trainLength);
      if (!trainCode || Number.isNaN(length) || length <= 0) {
        setLoading(false);
        setError("Compila tutti i campi richiesti per ogni treno.");
        return;
      }
    payloadTrains.push({
      train_code: trainCode,
      train_length_m: length,
      train_category: item.trainCategory,
      planned_signal: item.plannedSignal ? item.plannedSignal : null,
      is_prm: item.isPrm,
    });
    }

    axios
      .post(`${API_BASE}/tracks/suggestions`, { trains: payloadTrains })
      .then((res) => {
        const responseItems = Array.isArray(res.data.items)
          ? res.data.items
          : [];
        const items =
          responseItems.length > 0
            ? responseItems
            : payloadTrains.map((train, idx) => ({
                train,
                alternatives:
                  idx === 0 ? res.data.alternatives || [] : [],
              }));

        setSuggestions(items);

        const hasAlternatives = items.some(
          (item) =>
            Array.isArray(item.alternatives) &&
            item.alternatives.length > 0
        );
        if (!hasAlternatives) {
          setError("Nessun binario compatibile trovato.");
        } else {
          setError("");
        }
      })
      .catch((err) => {
        const detail =
          err.response?.data?.detail ||
          "Errore durante il calcolo delle alternative.";
        setError(Array.isArray(detail) ? detail.join(" ") : detail);
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
      signal_code: track.signal_code ?? "",
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

  const parseList = (value) =>
    value
      .split(',')
      .map((v) => v.trim())
      .filter((v) => v.length > 0);

  const startEditingRule = (rule) => {
    setEditingRule({
      category: rule.category,
      allow_bis: rule.allow_bis,
      allow_no_platform: rule.allow_no_platform,
      min_track_number: rule.min_track_number ?? '',
      max_track_number: rule.max_track_number ?? '',
      preferred_min_track_number: rule.preferred_min_track_number ?? '',
      preferred_max_track_number: rule.preferred_max_track_number ?? '',
      deny_track_names: (rule.deny_track_names || []).join(', '),
      deny_track_patterns: (rule.deny_track_patterns || []).join(', '),
      deny_track_numbers: (rule.deny_track_numbers || []).join(', '),
    });
    setRuleMessage('');
  };

  const cancelRuleEdit = () => {
    setEditingRule(null);
  };

  const onRuleFieldChange = (field) => (event) => {
    if (!editingRule) return;
    const { value, type, checked } = event.target;
    setEditingRule({
      ...editingRule,
      [field]: type === 'checkbox' ? checked : value,
    });
  };

  const saveRule = () => {
    if (!editingRule) return;
    const payload = {
      allow_bis: !!editingRule.allow_bis,
      allow_no_platform: !!editingRule.allow_no_platform,
      min_track_number: editingRule.min_track_number !== '' ? Number(editingRule.min_track_number) : null,
      max_track_number: editingRule.max_track_number !== '' ? Number(editingRule.max_track_number) : null,
      preferred_min_track_number:
        editingRule.preferred_min_track_number !== '' ? Number(editingRule.preferred_min_track_number) : null,
      preferred_max_track_number:
        editingRule.preferred_max_track_number !== '' ? Number(editingRule.preferred_max_track_number) : null,
      deny_track_names: parseList(editingRule.deny_track_names),
      deny_track_patterns: parseList(editingRule.deny_track_patterns),
      deny_track_numbers: parseList(editingRule.deny_track_numbers).map((n) => Number(n)).filter((n) => !Number.isNaN(n)),
    };

    axios
      .put(
        `${API_BASE}/admin/config/category-rules/${editingRule.category}`,
        payload
      )
      .then(() => {
        setRuleMessage('Regola di categoria salvata.');
        setEditingRule(null);
        refreshAll();
      })
      .catch(() => {
        setRulesError('Impossibile salvare la regola.');
      });
  };

  const resetRule = (category) => {
    if (
      !window.confirm(
        `Ripristinare le impostazioni predefinite per ${category}?`
      )
    ) {
      return;
    }
    axios
      .delete(`${API_BASE}/admin/config/category-rules/${category}`)
      .then(() => {
        setRuleMessage('Regola ripristinata ai valori di default.');
        if (editingRule?.category === category) {
          setEditingRule(null);
        }
        refreshAll();
      })
      .catch(() => {
        setRulesError('Impossibile ripristinare la regola.');
      });
  };

  const startEditingPriority = (config) => {
    setEditingPriority({
      category: config.category,
      same_number_bonus: config.same_number_bonus,
      criteria: (config.criteria || []).map((c) => ({
        key: c.key,
        weight: c.weight ?? 1,
        direction: c.direction ?? 1,
      })),
      newCriterionKey: '',
    });
    setPriorityMessage('');
  };

  const cancelPriorityEdit = () => {
    setEditingPriority(null);
  };

  const onPriorityFieldChange = (field) => (event) => {
    if (!editingPriority) return;
    const value = event.target.value;
    setEditingPriority({ ...editingPriority, [field]: field === 'same_number_bonus' ? Number(value) : value });
  };

  const updateCriterionValue = (index, field, value) => {
    if (!editingPriority) return;
    const next = editingPriority.criteria.map((item, idx) =>
      idx === index ? { ...item, [field]: field === 'key' ? value : Number(value) } : item
    );
    setEditingPriority({ ...editingPriority, criteria: next });
  };

  const moveCriterion = (index, offset) => {
    if (!editingPriority) return;
    const next = [...editingPriority.criteria];
    const newIndex = index + offset;
    if (newIndex < 0 || newIndex >= next.length) {
      return;
    }
    const [item] = next.splice(index, 1);
    next.splice(newIndex, 0, item);
    setEditingPriority({ ...editingPriority, criteria: next });
  };

  const removeCriterion = (index) => {
    if (!editingPriority) return;
    const next = editingPriority.criteria.filter((_, idx) => idx !== index);
    setEditingPriority({ ...editingPriority, criteria: next });
  };

  const addCriterion = () => {
    if (!editingPriority || !editingPriority.newCriterionKey) {
      return;
    }
    setEditingPriority({
      ...editingPriority,
      criteria: [
        ...editingPriority.criteria,
        { key: editingPriority.newCriterionKey, weight: 1, direction: 1 },
      ],
      newCriterionKey: '',
    });
  };

  const savePriority = () => {
    if (!editingPriority) return;
    const payload = {
      same_number_bonus: Number(editingPriority.same_number_bonus),
      criteria: editingPriority.criteria.map((c) => ({
        key: c.key,
        weight: Number(c.weight) || 1,
        direction: Number(c.direction) || 1,
      })),
    };
    axios
      .put(
        `${API_BASE}/admin/config/priority-configs/${editingPriority.category}`,
        payload
      )
      .then(() => {
        setPriorityMessage('Profilo di priorita salvato.');
        setEditingPriority(null);
        refreshAll();
      })
      .catch(() => {
        setPriorityError('Impossibile salvare il profilo.');
      });
  };

  const resetPriority = (category) => {
    if (!window.confirm(`Ripristinare le priorita per ${category}?`)) {
      return;
    }
    axios
      .delete(`${API_BASE}/admin/config/priority-configs/${category}`)
      .then(() => {
        setPriorityMessage('Profilo di priorita ripristinato.');
        if (editingPriority?.category === category) {
          setEditingPriority(null);
        }
        refreshAll();
      })
      .catch(() => {
        setPriorityError('Impossibile ripristinare il profilo.');
      });
  };

  if (!hasAdminAccess) {
    return (
      <div className="app-container">
        <section className="section-card section-card--spaced login-section">
          <h1>Area amministrativa</h1>
          <p className="text-muted">
            Inserisci le credenziali fornite per gestire dataset, regole e
            priorità dei binari.
          </p>
          <form onSubmit={submitLogin} className="stack">
            <label>
              <span>Username</span>
              <input
                type="text"
                autoComplete="username"
                value={loginForm.username}
                onChange={onLoginFieldChange("username")}
                disabled={loginLoading}
              />
            </label>
            <label>
              <span>Password</span>
              <input
                type="password"
                autoComplete="current-password"
                value={loginForm.password}
                onChange={onLoginFieldChange("password")}
                disabled={loginLoading}
              />
            </label>
            {loginError && (
              <div className="feedback feedback--error">{loginError}</div>
            )}
            <div className="actions-row actions-row--end">
              <button
                type="submit"
                className="button-primary"
                disabled={loginLoading}
              >
                {loginLoading ? "Accesso..." : "Accedi"}
              </button>
            </div>
          </form>
        </section>
      </div>
    );
  }

  return (
    <div className="app-container">
      <header className="section-intro">
        <h1>Binari Ammissibili</h1>
        <p className="text-muted">
          Inserisci i dettagli del treno per ottenere le alternative disponibili
          e gestisci i binari del database.
        </p>
        <div className="actions-row actions-row--end">
          <button type="button" className="button-secondary" onClick={handleLogout}>
            Esci
          </button>
        </div>
      </header>

      {/* Sezione calcolo suggerimenti */}
      <section className="section-card section-card--spaced">
        <form onSubmit={handleSubmit} className="stack">
          {trainForms.map((train, index) => (
            <div key={`train-${index}`} className="stack-sm">
              <h3 className="section-subheading">Treno {index + 1}</h3>
              <div className="form-grid form-grid--tight">
                <label>
                  <span>Numero treno</span>
                  <input
                    type="text"
                    required
                    value={train.trainCode}
                    onChange={updateTrainField(index, "trainCode")}
                  />
                </label>

                <label>
                  <span>Lunghezza (m)</span>
                  <input
                    type="number"
                    min="1"
                    required
                    value={train.trainLength}
                    onChange={updateTrainField(index, "trainLength")}
                  />
                </label>

                <label>
                  <span>Categoria treno</span>
                  <select
                    value={train.trainCategory}
                    onChange={updateTrainField(index, "trainCategory")}
                  >
                    {TRAIN_CATEGORIES.map((category) => (
                      <option key={category} value={category}>
                        {category}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  <span>Segnale previsto</span>
                  <select
                    value={train.plannedSignal}
                    onChange={updateTrainField(index, "plannedSignal")}
                  >
                    <option value="">Non specificato</option>
                    {trackSignalOptions.map((option) => (
                      <option
                        key={`${option.value}-${option.name}`}
                        value={option.value}
                      >
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="actions-row actions-row--between">
                <label className="inline-checkbox">
                  <input
                    type="checkbox"
                    checked={train.isPrm}
                    onChange={updateTrainField(index, "isPrm")}
                  />
                  Treno PRM
                </label>
                {trainForms.length > 1 && (
                  <button
                    type="button"
                    className="button-secondary"
                    onClick={() => removeTrainForm(index)}
                  >
                    Rimuovi treno
                  </button>
                )}
              </div>
            </div>
          ))}

          <div className="actions-row actions-row--between">
            <button
              type="button"
              className="button-secondary"
              onClick={addTrainForm}
            >
              Aggiungi treno
            </button>
            <button type="submit" disabled={loading} className="button-primary">
              {loading ? "Calcolo in corso..." : "Calcola alternative"}
            </button>
          </div>
        </form>

        {error && (
          <div className="feedback feedback--error feedback--spaced">
            {error}
          </div>
        )}
      </section>

      {/* Sezione suggerimenti */}
      <section className="section-spaced">
        <h2 className="section-heading">Alternative suggerite</h2>
        {loading ? (
          <p>Calcolo in corso...</p>
        ) : suggestions.length > 0 ? (
          <div className="stack">
            {suggestions.map((item, index) => {
              const train = item.train || {};
              const headingCode = train.train_code || `#${index + 1}`;
              return (
                <div key={`${headingCode}-${index}`} className="stack-sm">
                  <h3 className="section-subheading">
                    Treno {train.train_code ?? index + 1}
                  </h3>
                  <p className="text-muted">
                    {`Categoria ${train.train_category ?? "?"} • Lunghezza ${
                      train.train_length_m ?? "?"
                    } m`}
                    {train.planned_signal
                      ? (() => {
                          const info = describeSignal(train.planned_signal);
                          const trackLabel = info.trackName
                            ? ` (Binario ${info.trackName})`
                            : "";
                          return ` • Segnale previsto ${info.signal}${trackLabel}`;
                        })()
                      : ""}
                    {train.is_prm ? " • PRM" : ""}
                  </p>
                  {item.alternatives && item.alternatives.length > 0 ? (
                    <ol>
                      {item.alternatives.map(({ track, track_name, reason }) => {
                        const info = describeSignal(track);
                        const resolvedName = track_name || info.trackName;
                        const trackLabel = resolvedName
                          ? ` (Binario ${resolvedName})`
                          : "";
                        return (
                          <li key={`${track}-${headingCode}`} className="suggestion-item">
                            <div className="suggestion-item__track">
                              {`Segnale ${info.signal}${trackLabel}`}
                            </div>
                            <div className="suggestion-item__reason">{reason}</div>
                          </li>
                        );
                      })}
                    </ol>
                  ) : (
                    <p className="text-muted">
                      Nessun binario compatibile trovato per questo treno.
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-muted">
            Compila il form per ottenere una nuova valutazione.
          </p>
        )}
      </section>

      {/* Tabella visualizzazione dataset */}
      <section className="section-spaced-lg">
        <h2 className="section-heading">Binari disponibili</h2>
        {loadingDataset ? (
          <p>Caricamento...</p>
        ) : datasetError ? (
          <div className="feedback feedback--error feedback--spaced">
            {datasetError}
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Binario</th>
                  <th>Segnale</th>
                  <th className="text-right">Totale (m)</th>
                  <th className="text-right">Alto (m)</th>
                  <th className="text-right">Basso (m)</th>
                  <th className="text-right">Capacita (m)</th>
                </tr>
              </thead>
              <tbody>
                {trackNames.map((name) => {
                  const track = trackData[name];
                  return (
                    <tr key={name}>
                      <td>{name}</td>
                      <td>{track.signal_code || "-"}</td>
                      <td className="text-right">
                        {track.marciapiede_complessivo_m}
                      </td>
                      <td className="text-right">
                        {track.marciapiede_alto_m}
                      </td>
                      <td className="text-right">
                        {track.marciapiede_basso_m}
                      </td>
                      <td className="text-right">
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
      <section className="section-spaced-lg">
        <h2 className="section-heading">Gestione binari</h2>

        {adminError && (
          <div className="feedback feedback--error">{adminError}</div>
        )}

        {adminMessage && (
          <div className="feedback feedback--success">{adminMessage}</div>
        )}

        <form
          onSubmit={handleCreateTrack}
          className="section-card section-card--compact stack-sm form-narrow"
        >
          <h3>Aggiungi nuovo binario</h3>
          <div className="form-grid form-grid--tight">
            <label>
              <span>Nome</span>
              <input
                type="text"
                required
                value={newTrack.name}
                onChange={onNewTrackFieldChange("name")}
              />
            </label>
            <label>
              <span>Numero segnale</span>
              <input
                type="text"
                value={newTrack.signal_code}
                onChange={onNewTrackFieldChange("signal_code")}
                placeholder="(auto se vuoto)"
              />
            </label>
            <label>
              <span>Totale (m)</span>
              <input
                type="number"
                min="0"
                required
                value={newTrack.marciapiede_complessivo_m}
                onChange={onNewTrackFieldChange("marciapiede_complessivo_m")}
              />
            </label>
            <label>
              <span>Alto (m)</span>
              <input
                type="number"
                min="0"
                required
                value={newTrack.marciapiede_alto_m}
                onChange={onNewTrackFieldChange("marciapiede_alto_m")}
              />
            </label>
            <label>
              <span>Basso (m)</span>
              <input
                type="number"
                min="0"
                required
                value={newTrack.marciapiede_basso_m}
                onChange={onNewTrackFieldChange("marciapiede_basso_m")}
              />
            </label>
            <label>
              <span>Capacita funzionale (m)</span>
              <input
                type="number"
                min="0"
                value={newTrack.capacita_funzionale_m}
                onChange={onNewTrackFieldChange("capacita_funzionale_m")}
                placeholder="(opzionale)"
              />
            </label>
          </div>
          <button type="submit" className="button-success">
            Aggiungi binario
          </button>
        </form>

        <div className="table-wrapper">
          <table className="data-table table-wide">
            <thead>
              <tr>
                <th>Nome</th>
                <th>Segnale</th>
                <th className="text-right">Totale</th>
                <th className="text-right">Alto</th>
                <th className="text-right">Basso</th>
                <th className="text-right">Capacita</th>
                <th className="text-center">Azioni</th>
              </tr>
            </thead>
            <tbody>
              {adminTracks.map((track) => {
                const isEditing = editingTrack?.id === track.id;
                return (
                  <tr key={track.id}>
                    <td>
                      {isEditing ? (
                        <input
                          type="text"
                          value={editingTrack.name}
                          onChange={onEditTrackFieldChange("name")}
                          className="table-input"
                        />
                      ) : (
                        track.name
                      )}
                    </td>
                    <td>
                      {isEditing ? (
                        <input
                          type="text"
                          value={editingTrack.signal_code ?? ""}
                          onChange={onEditTrackFieldChange("signal_code")}
                          className="table-input"
                          placeholder="(auto se vuoto)"
                        />
                      ) : (
                        track.signal_code || "-"
                      )}
                    </td>
                    <td className="text-right">
                      {isEditing ? (
                        <input
                          type="number"
                          min="0"
                          value={editingTrack.marciapiede_complessivo_m}
                          onChange={onEditTrackFieldChange("marciapiede_complessivo_m")}
                          className="table-input"
                        />
                      ) : (
                        track.marciapiede_complessivo_m
                      )}
                    </td>
                    <td className="text-right">
                      {isEditing ? (
                        <input
                          type="number"
                          min="0"
                          value={editingTrack.marciapiede_alto_m}
                          onChange={onEditTrackFieldChange("marciapiede_alto_m")}
                          className="table-input"
                        />
                      ) : (
                        track.marciapiede_alto_m
                      )}
                    </td>
                    <td className="text-right">
                      {isEditing ? (
                        <input
                          type="number"
                          min="0"
                          value={editingTrack.marciapiede_basso_m}
                          onChange={onEditTrackFieldChange("marciapiede_basso_m")}
                          className="table-input"
                        />
                      ) : (
                        track.marciapiede_basso_m
                      )}
                    </td>
                    <td className="text-right">
                      {isEditing ? (
                        <input
                          type="number"
                          min="0"
                          value={editingTrack.capacita_funzionale_m}
                          onChange={onEditTrackFieldChange("capacita_funzionale_m")}
                          className="table-input"
                          placeholder="(opzionale)"
                        />
                      ) : (
                        track.capacita_funzionale_m ?? "-"
                      )}
                    </td>
                    <td className="text-center text-nowrap">
                      <div className="actions-row">
                        {isEditing ? (
                          <>
                            <button
                              type="button"
                              onClick={saveEditing}
                              className="button-primary"
                            >
                              Salva
                            </button>
                            <button
                              type="button"
                              onClick={cancelEditing}
                              className="button-secondary"
                            >
                              Annulla
                            </button>
                          </>
                        ) : (
                          <button
                            type="button"
                            onClick={() => startEditing(track)}
                            className="button-secondary"
                          >
                            Modifica
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => deleteTrack(track.id)}
                          className="button-danger"
                        >
                          Elimina
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="section-spaced-lg">
        <h2 className="section-heading">Regole di categoria</h2>
        {rulesError && (
          <div className="feedback feedback--error">{rulesError}</div>
        )}
        {ruleMessage && (
          <div className="feedback feedback--success">{ruleMessage}</div>
        )}

        <div className="card-list">
          {categoryRules.map((rule) => (
            <div key={rule.category} className="card-list__item">
              <div className="card-list__item-header">
                <strong>{rule.category}</strong>
                <div className="actions-row actions-row--end">
                  <button
                    type="button"
                    className="button-secondary"
                    onClick={() => startEditingRule(rule)}
                  >
                    Modifica
                  </button>
                  <button
                    type="button"
                    className="button-secondary"
                    onClick={() => resetRule(rule.category)}
                    disabled={!rule.is_custom}
                  >
                    Ripristina
                  </button>
                </div>
              </div>
              <div className="card-list__item-body">
                <div>
                  <strong>Binari BIS:</strong> {rule.allow_bis ? "Si" : "No"}
                </div>
                <div>
                  <strong>Senza marciapiede:</strong>{" "}
                  {rule.allow_no_platform ? "Si" : "No"}
                </div>
                <div>
                  <strong>Range valido:</strong>{" "}
                  {rule.min_track_number !== null ||
                  rule.max_track_number !== null
                    ? `${rule.min_track_number ?? "-"} - ${
                        rule.max_track_number ?? "-"
                      }`
                    : "--"}
                </div>
                <div>
                  <strong>Range preferito:</strong>{" "}
                  {rule.preferred_min_track_number !== null ||
                  rule.preferred_max_track_number !== null
                    ? `${rule.preferred_min_track_number ?? "-"} - ${
                        rule.preferred_max_track_number ?? "-"
                      }`
                    : "--"}
                </div>
                <div>
                  <strong>Esclusioni nomi:</strong>{" "}
                  {(rule.deny_track_names || []).join(", ") || "—"}
                </div>
                <div>
                  <strong>Pattern:</strong>{" "}
                  {(rule.deny_track_patterns || []).join(", ") || "—"}
                </div>
                <div>
                  <strong>Numeri:</strong>{" "}
                  {(rule.deny_track_numbers || []).join(", ") || "—"}
                </div>
              </div>
            </div>
          ))}
        </div>

        {editingRule && (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              saveRule();
            }}
            className="section-card section-card--compact stack-sm form-wide"
          >
            <h3>Modifica regola per {editingRule.category}</h3>
            <div className="rule-help">
              <strong>Come funzionano i campi:</strong>
              <ul>
                <li>
                  <strong>Consenti binari con suffisso BIS</strong>: include i
                  binari con suffisso &ldquo;BIS&rdquo; tra i candidati; se
                  disattivato vengono scartati.
                </li>
                <li>
                  <strong>Consenti binari senza marciapiede</strong>: permette
                  l&rsquo;uso di binari privi di marciapiede per questa
                  categoria.
                </li>
                <li>
                  <strong>Numero minimo / massimo</strong>: limite rigido sul
                  numero di binario ammesso (prima del suffisso). Fuori da questo
                  range i binari sono esclusi.
                </li>
                <li>
                  <strong>Range preferito</strong>: fascia &ldquo;soft&rdquo; da
                  privilegiare. I binari dentro l&rsquo;intervallo vengono
                  ordinati più in alto rispetto agli altri pur sempre ammessi.
                </li>
                <li>
                  <strong>Escludi...</strong>: forza la rimozione di binari
                  specifici (per nome, per sottostringa o per numero), separando
                  i valori con la virgola.
                </li>
              </ul>
            </div>
            <label className="inline-checkbox">
              <input
                type="checkbox"
                checked={!!editingRule.allow_bis}
                onChange={onRuleFieldChange("allow_bis")}
              />
              Consenti binari con suffisso BIS
            </label>
            <label className="inline-checkbox">
              <input
                type="checkbox"
                checked={!!editingRule.allow_no_platform}
                onChange={onRuleFieldChange("allow_no_platform")}
              />
              Consenti binari senza marciapiede
            </label>
            <div className="form-grid form-grid--narrow">
              <label>
                <span>Numero minimo</span>
                <input
                  type="number"
                  value={editingRule.min_track_number ?? ""}
                  onChange={onRuleFieldChange("min_track_number")}
                />
              </label>
              <label>
                <span>Numero massimo</span>
                <input
                  type="number"
                  value={editingRule.max_track_number ?? ""}
                  onChange={onRuleFieldChange("max_track_number")}
                />
              </label>
              <label>
                <span>Range preferito (min)</span>
                <input
                  type="number"
                  value={editingRule.preferred_min_track_number ?? ""}
                  onChange={onRuleFieldChange("preferred_min_track_number")}
                />
              </label>
              <label>
                <span>Range preferito (max)</span>
                <input
                  type="number"
                  value={editingRule.preferred_max_track_number ?? ""}
                  onChange={onRuleFieldChange("preferred_max_track_number")}
                />
              </label>
            </div>
            <label>
              <span>Escludi binari (nomi separati da virgola)</span>
              <input
                type="text"
                value={editingRule.deny_track_names}
                onChange={onRuleFieldChange("deny_track_names")}
              />
            </label>
            <label>
              <span>Escludi se contiene (separati da virgola)</span>
              <input
                type="text"
                value={editingRule.deny_track_patterns}
                onChange={onRuleFieldChange("deny_track_patterns")}
              />
            </label>
            <label>
              <span>Escludi numeri (separati da virgola)</span>
              <input
                type="text"
                value={editingRule.deny_track_numbers}
                onChange={onRuleFieldChange("deny_track_numbers")}
              />
            </label>
            <div className="actions-row actions-row--end">
              <button type="submit" className="button-primary">
                Salva
              </button>
              <button
                type="button"
                className="button-secondary"
                onClick={cancelRuleEdit}
              >
                Annulla
              </button>
            </div>
          </form>
        )}
      </section>

      <section className="section-spaced-lg">
        <h2 className="section-heading">Priorita di selezione</h2>
        {priorityError && (
          <div className="feedback feedback--error">{priorityError}</div>
        )}
        {priorityMessage && (
          <div className="feedback feedback--success">{priorityMessage}</div>
        )}

        <div className="card-list">
          {priorityConfigs.map((config) => (
            <div key={config.category} className="card-list__item">
              <div className="card-list__item-header">
                <strong>{config.category}</strong>
                <div className="actions-row actions-row--end">
                  <button
                    type="button"
                    className="button-secondary"
                    onClick={() => startEditingPriority(config)}
                  >
                    Modifica
                  </button>
                  <button
                    type="button"
                    className="button-secondary"
                    onClick={() => resetPriority(config.category)}
                    disabled={!config.is_custom}
                  >
                    Ripristina
                  </button>
                </div>
              </div>
              <div className="card-list__item-body">
                <div>
                  <strong>Bonus stesso numero:</strong>{" "}
                  {config.same_number_bonus}
                </div>
                <div>
                  <strong>Ordine criteri:</strong>{" "}
                  {(config.criteria || [])
                    .map(
                      (item) =>
                        `${getCriterionLabel(item.key)}${
                          item.weight !== 1 || item.direction !== 1
                            ? ` (w=${item.weight ?? 1}, d=${item.direction ?? 1})`
                            : ""
                        }`
                    )
                    .join(" → ") || "(ordine predefinito)"}
                </div>
              </div>
            </div>
          ))}
        </div>

        {editingPriority && (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              savePriority();
            }}
            className="section-card section-card--compact stack form-wide"
          >
            <h3>Modifica priorita per {editingPriority.category}</h3>
            <label>
              <span>Bonus stesso numero (valore negativo per favorire varianti)</span>
              <input
                type="number"
                step="0.1"
                value={editingPriority.same_number_bonus}
                onChange={onPriorityFieldChange("same_number_bonus")}
              />
            </label>
            <div className="stack-sm">
              <h4>Criteri in ordine di applicazione</h4>
              {(editingPriority.criteria || []).map((criterion, index) => (
                <div key={`${criterion.key}-${index}`} className="criteria-row">
                  <select
                    value={criterion.key}
                    onChange={(event) =>
                      updateCriterionValue(index, "key", event.target.value)
                    }
                  >
                    {availableCriteria.map((item) => (
                      <option key={item.key} value={item.key}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                  <input
                    type="number"
                    step="0.1"
                    value={criterion.weight}
                    onChange={(event) =>
                      updateCriterionValue(index, "weight", event.target.value)
                    }
                    className="criterion-input--small"
                    title="Peso"
                  />
                  <input
                    type="number"
                    step="0.1"
                    value={criterion.direction}
                    onChange={(event) =>
                      updateCriterionValue(
                        index,
                        "direction",
                        event.target.value
                      )
                    }
                    className="criterion-input--small"
                    title="Direzione (1 = crescente, -1 = decrescente)"
                  />
                  <div className="actions-row actions-row--start">
                    <button
                      type="button"
                      onClick={() => moveCriterion(index, -1)}
                      className="button-icon"
                    >
                      ↑
                    </button>
                    <button
                      type="button"
                      onClick={() => moveCriterion(index, 1)}
                      className="button-icon"
                    >
                      ↓
                    </button>
                    <button
                      type="button"
                      onClick={() => removeCriterion(index)}
                      className="button-icon"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              ))}
              <div className="criteria-row">
                <select
                  value={editingPriority.newCriterionKey || ""}
                  onChange={(event) =>
                    onPriorityFieldChange("newCriterionKey")(event)
                  }
                  
                >
                  <option value="">Aggiungi criterio…</option>
                  {availableCriteria.map((item) => (
                    <option key={item.key} value={item.key}>
                      {item.label}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={addCriterion}
                  className="button-secondary"
                >
                  Aggiungi
                </button>
              </div>
            </div>
            <div className="actions-row actions-row--end">
              <button type="submit" className="button-primary">
                Salva
              </button>
              <button
                type="button"
                className="button-secondary"
                onClick={cancelPriorityEdit}
              >
                Annulla
              </button>
            </div>
          </form>
        )}
      </section>
    </div>
  );
}

export default App;








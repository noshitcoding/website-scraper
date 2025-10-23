import { useEffect, useMemo, useState } from 'react';
import './App.css';

const DEFAULT_USER_AGENT =
  'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36';

const defaultFormState = {
  url: '',
  maxPages: '50',
  maxSearchResults: '100',
  timeout: '15',
  pause: '1',
  userAgent: DEFAULT_USER_AGENT
};

const detectApiBase = () => {
  const envBase = import.meta?.env?.VITE_API_BASE_URL;
  if (envBase && typeof envBase === 'string') {
    return envBase.replace(/\/$/, '');
  }
  if (typeof window !== 'undefined') {
    const { protocol, hostname } = window.location;
    return `${protocol}//${hostname}:8006`;
  }
  return 'http://localhost:8006';
};

const parseNumber = (value, fallback, { min, max } = {}) => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return fallback;
  }
  let result = numeric;
  if (typeof min === 'number') {
    result = Math.max(min, result);
  }
  if (typeof max === 'number') {
    result = Math.min(max, result);
  }
  return result;
};

const base64ToBlob = (base64, mime) => {
  if (!base64) {
    return null;
  }
  const cleaned = base64.replace(/\s/g, '');
  const binary = atob(cleaned);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return new Blob([bytes], { type: mime });
};

function App() {
  const [form, setForm] = useState(defaultFormState);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [textUrl, setTextUrl] = useState('');
  const [pdfUrl, setPdfUrl] = useState('');

  const apiBase = useMemo(() => detectApiBase(), []);

  useEffect(() => {
    return () => {
      if (textUrl) {
        URL.revokeObjectURL(textUrl);
      }
      if (pdfUrl) {
        URL.revokeObjectURL(pdfUrl);
      }
    };
  }, [textUrl, pdfUrl]);

  useEffect(() => {
    if (!result) {
      setTextUrl('');
      setPdfUrl('');
      return;
    }

    const textBlob = new Blob([result.text_content], { type: 'text/plain;charset=utf-8' });
    const nextTextUrl = URL.createObjectURL(textBlob);

    let nextPdfUrl = '';
    const pdfBlob = base64ToBlob(result.pdf_base64, 'application/pdf');
    if (pdfBlob) {
      nextPdfUrl = URL.createObjectURL(pdfBlob);
    }

    setTextUrl(nextTextUrl);
    setPdfUrl(nextPdfUrl);

    return () => {
      URL.revokeObjectURL(nextTextUrl);
      if (nextPdfUrl) {
        URL.revokeObjectURL(nextPdfUrl);
      }
    };
  }, [result]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!form.url.trim()) {
      setError('Bitte gib eine URL oder Domain an.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const payload = {
        url: form.url.trim(),
        max_pages: parseNumber(form.maxPages, 50, { min: 1, max: 500 }),
        max_search_results: parseNumber(form.maxSearchResults, 100, { min: 1, max: 200 }),
        timeout: parseNumber(form.timeout, 15, { min: 1 }),
        pause: parseNumber(form.pause, 1, { min: 0 }),
        user_agent: form.userAgent.trim() || DEFAULT_USER_AGENT
      };

      const response = await fetch(`${apiBase}/api/scrape`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        let message = 'Der Scrape-Vorgang ist fehlgeschlagen.';
        try {
          const data = await response.json();
          if (data?.detail) {
            message = data.detail;
          }
        } catch (jsonError) {
          // ignore JSON parsing errors
        }
        throw new Error(message);
      }

      const data = await response.json();
      setResult(data);
    } catch (fetchError) {
      setResult(null);
      setError(fetchError instanceof Error ? fetchError.message : String(fetchError));
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setForm(defaultFormState);
    setResult(null);
    setError('');
  };

  return (
    <div className="app">
      <header className="app__header">
        <h1>Website Scraper UI</h1>
        <p>Steuere den DuckDuckGo-basierten Scraper bequem über den Browser.</p>
        <p className="app__meta">Backend-Endpunkt: {apiBase}/api/scrape</p>
      </header>

      <section className="card">
        <h2>Konfiguration</h2>
        <form className="form" onSubmit={handleSubmit}>
          <label className="form__group">
            <span>Ziel-URL oder Domain</span>
            <input
              name="url"
              type="text"
              placeholder="https://beispiel.de"
              value={form.url}
              onChange={handleChange}
              required
            />
          </label>

          <div className="form__grid">
            <label className="form__group">
              <span>Max. Seiten</span>
              <input name="maxPages" type="number" min="1" max="500" value={form.maxPages} onChange={handleChange} />
            </label>
            <label className="form__group">
              <span>DuckDuckGo-Ergebnisse</span>
              <input
                name="maxSearchResults"
                type="number"
                min="1"
                max="200"
                value={form.maxSearchResults}
                onChange={handleChange}
              />
            </label>
            <label className="form__group">
              <span>HTTP-Timeout (s)</span>
              <input name="timeout" type="number" min="1" step="0.5" value={form.timeout} onChange={handleChange} />
            </label>
            <label className="form__group">
              <span>Pause (s)</span>
              <input name="pause" type="number" min="0" step="0.5" value={form.pause} onChange={handleChange} />
            </label>
          </div>

          <label className="form__group">
            <span>User-Agent</span>
            <textarea name="userAgent" rows={3} value={form.userAgent} onChange={handleChange} />
          </label>

          {error && <p className="form__error">{error}</p>}

          <div className="form__actions">
            <button type="submit" disabled={loading}>
              {loading ? 'Scrape läuft…' : 'Scrape starten'}
            </button>
            <button type="button" className="secondary" onClick={handleReset} disabled={loading}>
              Zurücksetzen
            </button>
          </div>
        </form>
      </section>

      {result && (
        <section className="card">
          <h2>Ergebnis</h2>
          <div className="result__summary">
            <p>
              <strong>Basis-URL:</strong> {result.base_url}
            </p>
            <p>
              <strong>Domain:</strong> {result.domain}
            </p>
            <p>
              <strong>Gefundene Seiten:</strong> {result.page_count}
            </p>
            <p>
              <strong>PDF-Strategie:</strong> {result.pdf_strategy || 'Keine (keine Seiten)'}
            </p>
          </div>

          <div className="result__actions">
            <a
              href={textUrl || undefined}
              download="scraped_content.txt"
              className={`button${textUrl ? '' : ' button--disabled'}`}
              aria-disabled={!textUrl}
              onClick={(event) => {
                if (!textUrl) {
                  event.preventDefault();
                }
              }}
            >
              Text herunterladen
            </a>
            <a
              href={pdfUrl || undefined}
              download="scraped_content.pdf"
              className={`button${pdfUrl ? '' : ' button--disabled'}`}
              aria-disabled={!pdfUrl}
              onClick={(event) => {
                if (!pdfUrl) {
                  event.preventDefault();
                }
              }}
            >
              PDF herunterladen
            </a>
          </div>

          <details className="result__details" open>
            <summary>Gescrapte Seiten</summary>
            <ul>
              {result.pages.map((page) => (
                <li key={page.url}>
                  <span className="page-title">{page.title}</span>
                  <a href={page.url} target="_blank" rel="noreferrer">
                    {page.url}
                  </a>
                  <span className="page-strategy">({page.fetch_strategy})</span>
                </li>
              ))}
            </ul>
          </details>

          <details className="result__details">
            <summary>Textinhalt</summary>
            <textarea value={result.text_content} readOnly rows={12} />
          </details>
        </section>
      )}
    </div>
  );
}

export default App;

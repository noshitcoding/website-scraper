# Website Scraper

Ein robuster Websitescraper, der DuckDuckGo zur Ermittlung von Unterseiten nutzt, anschließend alle gefundenen Seiten lädt und die Inhalte sowohl als Text- als auch als PDF-Datei exportiert. Um auch in restriktiven Umgebungen zu funktionieren, werden für alle kritischen Schritte mehrere Werkzeuge als Fallback eingesetzt.

## Hauptfunktionen

- **DuckDuckGo-Suche**: Nutzt wahlweise die Python-Bibliothek `duckduckgo_search`, das HTML-Frontend sowie die Lite-Variante als Fallback.
- **Mehrere HTTP-Clients**: Greift zuerst auf `requests` zu und wechselt bei Bedarf automatisch auf `httpx` oder die Standardbibliothek (`urllib`).
- **Flexible Exporte**: Erstellt eine Textdatei und ein PDF. Für den PDF-Export wird zuerst `fpdf2` eingesetzt und bei Bedarf auf `reportlab` ausgewichen.
- **Domainbegrenzter Crawl**: Der Scraper folgt nur Links innerhalb der gewählten Domain und führt eine breite Suche über DuckDuckGo-Ergebnisse durch.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

## Verwendung

```bash
python -m website_scraper.cli "https://example.com" \
    --output ./export \
    --max-pages 100 \
    --max-search-results 150 \
    --timeout 20 \
    --pause 0.5 \
    --verbose
```

- `url`: Ausgangs-URL oder Domain.
- `--output`: Zielverzeichnis für `scraped_content.txt` und `scraped_content.pdf`.
- `--max-pages`: Maximale Anzahl zu crawlender Seiten.
- `--max-search-results`: Anzahl DuckDuckGo-Ergebnisse, die als Seeds hinzugefügt werden.
- `--timeout`: Timeout pro HTTP-Anfrage.
- `--pause`: Pause zwischen HTTP-Anfragen, um Server zu schonen.
- `--verbose`: Aktiviert detailliertes Logging.

## Weboberfläche & Docker

Die Anwendung lässt sich vollständig containerisiert betreiben. Dabei exponiert der Backend-Container den FastAPI-Dienst auf Port **8006**, während die Vite-basierte React-Oberfläche auf Port **3006** läuft.

```bash
docker compose build
docker compose up
```

Anschließend ist die UI unter [http://localhost:3006](http://localhost:3006) erreichbar. Der Browser spricht das Backend automatisch über `http://localhost:8006/api/scrape` an.

### Manuelles Starten ohne Docker

Backend-API (FastAPI):

```bash
uvicorn website_scraper.api:app --host 0.0.0.0 --port 8006
```

Frontend (Vite Development Server):

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 3006
```

Die UI liest optional die Umgebungsvariable `VITE_API_BASE_URL`. Ohne Konfiguration wird automatisch die Domain des Browsers verwendet und Port 8006 angefügt.

## Hinweise

- Der Scraper respektiert ausschließlich die Domain-Beschränkung und wertet keine `robots.txt` aus.
- Für den PDF-Export muss mindestens eines der Pakete `fpdf2` oder `reportlab` verfügbar sein (beide in `requirements.txt` enthalten).
- DuckDuckGo setzt bei übermäßig vielen Anfragen eventuell Ratenbegrenzungen ein. In diesem Fall helfen längere Pausen und eine Reduzierung der Suchergebnisse.

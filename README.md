# superscrape

Scrape a URL via Jina Reader, extract structured data with Ollama JSON mode, and upsert into a Supabase table.

## Pipeline

```
URL → Jina Reader (markdown) → Ollama (JSON extraction) → Supabase (upsert)
```

## Files

| File | Purpose |
|------|---------|
| `superscrape.py` | Main script |
| `requirements.txt` | Python dependencies |
| `.env.example` | Template for secrets — copy to `.env` |
| `species.schema.json` | JSON Schema defining the extraction target |
| `supabase/migrations/20260622000001_create_species_table.sql` | Database migration for the `species` table |

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env with your keys
```

### `.env` variables

| Variable | Required | Default |
|----------|----------|---------|
| `JINA_API_KEY` | Yes | — |
| `OLLAMA_URL` | No | `http://localhost:11434` |
| `OLLAMA_MODEL` | Yes | — |
| `SUPABASE_URL` | Yes | — |
| `SUPABASE_SERVICE_KEY` | Yes | — |

### Database migration

Make sure your local Supabase is running, then:

```bash
npx supabase migration up
```

## Usage

```bash
python superscrape.py <url> [schema_file] [--table <name>]
```

- **`url`** — HTTPS URL to scrape (positional, required)
- **`schema_file`** — path to JSON Schema file (optional, defaults to `<table>.schema.json`)
- **`--table`** — Supabase table name (optional, defaults to basename of schema file or `species`)

### Examples

```bash
# Uses species.schema.json → table "species"
python superscrape.py https://example.com/plant

# Explicit schema and table
python superscrape.py https://example.com/plant crops.schema.json --table crops
```

## Table structure

| Column | Type | Description |
|--------|------|-------------|
| `id` | `UUID` | Auto-generated primary key |
| `source_url` | `TEXT` | Original URL (unique, used for upsert) |
| `raw_markdown` | `TEXT` | Raw markdown from Jina fetch |
| `created_at` | `TIMESTAMPTZ` | Row creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | Last update timestamp |
| `image_urls` | `JSONB` | Array of image URLs |
| `taxonomy` | `JSONB` | Kingdom, family, genus, species, etc. |
| `names` | `JSONB` | Scientific name, common names, local names, synonyms |
| `description` | `JSONB` | Short/full description, life cycle, growth form, origin |
| `morphology` | `JSONB` | Habit, root, stem, leaf, flower, fruit, seed, etc. |
| `ecology` | `JSONB` | Habitat, soil, climate, native/introduced range, coordinates |
| `phenology` | `JSONB` | Flowering/fruiting period, seed maturation, dormancy |
| `reproduction` | `JSONB` | Propagation, pollination, seed dispersal |
| `economic_importance` | `JSONB` | Uses (ornamental, medicinal, food, etc.), conservation status, toxicity, cultural significance |
| `specimen_data` | `JSONB` | Collector, collection date, accession number, herbarium code |
| `media_summary` | `JSONB` | Image counts by category |
| `metadata` | `JSONB` | Summary, keywords, tags, verification status, confidence score |

## Table name resolution

1. `--table` CLI flag
2. Basename of schema file (e.g. `species.schema.json` → `species`)
3. `SUPABASE_TABLE` env var
4. Hard default: `species`

## Design decisions

- **Upserts by `source_url`** — re-running the same URL updates the row instead of duplicating
- **Retry on failure** — if Ollama returns invalid JSON or misses required fields, the pipeline retries once with a stronger prompt
- **Raw markdown stored** — the full Jina response is saved in `raw_markdown` for debugging

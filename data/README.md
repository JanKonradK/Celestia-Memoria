# Aviation Regulatory Data Directory

This directory holds aviation regulatory documents (PDFs) that Celestia Memoria indexes and makes queryable through its AI-powered chat interface.

## Directory Structure

```
data/
├── icao/           ICAO documents (global applicability)
├── easa/           EASA regulations and AMCs (European)
├── local/          Country-specific / aerodrome-specific documents
│   └── <ICAO>/     Per-aerodrome subdirectories (e.g., EGLL/, KJFK/)
└── other/          Miscellaneous aviation documents
```

## How to Add Documents

1. **Place PDF files** in the appropriate subdirectory based on the issuing authority.
2. If the file watcher is enabled (`ENABLE_WATCHER=true` in backend `.env`), the system will **automatically detect and ingest** new PDFs.
3. If the watcher is disabled, use the **Upload Document** button in the web UI, or call the `/ingest` API endpoint directly.

## Directory Conventions

### `icao/`
Place ICAO documents here. Examples:
- ICAO Doc 4444 (PANS-ATM)
- ICAO Annex 2 (Rules of the Air)
- ICAO Annex 11 (Air Traffic Services)
- ICAO Annex 14 (Aerodromes)

**Auto-inferred metadata:** `doc_type=ICAO_DOC`, `aerodrome_icao=GLOBAL`

### `easa/`
Place EASA regulations and Acceptable Means of Compliance (AMC) here. Examples:
- EASA Easy Access Rules for ATM/ANS
- Commission Implementing Regulation (EU) 2017/373
- SERA (Standardised European Rules of the Air)

**Auto-inferred metadata:** `doc_type=EASA_REG`, `aerodrome_icao=GLOBAL`

### `local/`
Place country-specific AIPs, unit manuals, and aerodrome-specific documents here.

For **aerodrome-specific** documents, create a subdirectory named with the 4-letter ICAO code:

```
local/
├── EGLL/          London Heathrow documents
│   ├── egll-manual-of-atc.pdf
│   └── egll-local-instructions.pdf
├── KJFK/          JFK International documents
│   └── kjfk-7110-65-supplement.pdf
└── national-aip-enr.pdf   (no aerodrome subfolder = GLOBAL)
```

**Auto-inferred metadata:**
- Files in `local/<ICAO>/` → `doc_type=AIP`, `aerodrome_icao=<ICAO>`
- Files directly in `local/` → `doc_type=AIP`, `aerodrome_icao=GLOBAL`

### `other/`
Place miscellaneous aviation documents that don't fit the above categories.

**Auto-inferred metadata:** `doc_type=ICAO_DOC`, `aerodrome_icao=GLOBAL`

## Supported File Formats

Currently only **PDF** files (`.pdf`) are supported. The system uses PyMuPDF to extract text, preserving:
- Headings and document structure
- Tables
- Lists
- Page boundaries

## How Ingestion Works

1. **PDF parsing** — Document is converted to structured Markdown
2. **Chunking** — Markdown is split into ~800-token chunks at heading boundaries
3. **Embedding** — Each chunk is embedded with metadata prefix for improved retrieval
4. **Indexing** — Vectors are stored in Pinecone (production) or SQLite (local mode)
5. **Ready** — Document is now queryable through the chat interface

## File Naming Tips

While any filename works, descriptive names help with search results:
- `icao-doc-4444-pans-atm-17th-edition.pdf` (good)
- `doc.pdf` (bad — unclear what it contains)
- Include edition/amendment numbers when applicable
- Include ICAO codes for aerodrome-specific documents

## Re-ingestion

If you replace a file with an updated version (same path, different content), the watcher will detect the change via file hash comparison and re-ingest it automatically. The old vectors are not automatically removed — for clean replacement, delete the document through the API first.

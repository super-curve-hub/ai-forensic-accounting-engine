# AI Forensic Accounting Engine v3 Full Modular Edition

## Modules

- app.py: Streamlit entrypoint
- ui.py: tab-level UI
- engine.py: forensic accounting engine
- sec_loader.py: SEC EDGAR/XBRL loader and tag resolver
- cards.py: card-centered UI components
- charts.py: Plotly chart components
- screener.py: watchlist, compare, screening logic
- utils.py: shared formatters and helpers

## Main file path

```text
app.py
```

## Notes

- Uses SEC companyfacts API.
- TTM uses pragmatic approximation from companyfacts.
- Full quarterization remains future work.

# MCP-yf-stock

Learning project: **Model Context Protocol (MCP)** server that serves **Yahoo Finance** stock data (via `yfinance`) with a **CSV fallback**, plus **Gemini** and **Ollama** clients that turn natural language into tool calls.

## Summary

| Piece | What it does |
|-------|----------------|
| **`lab/mcp_server.py`** | MCP server: `get_stock_price`, `compare_stocks`, `check_data_sources` |
| **`lab/mcp_client.py`** | Client using **Gemini** to pick tools → executes them via MCP |
| **`lab/mcp_client_ollama.py`** | Same pattern with **local Ollama** |

**Data:** Try Yahoo Finance first; use `stocks_data.csv` when the API is unavailable. **`check_data_sources`** reports whether both paths work.

**Run (examples):**

```bash
cd lab
pip install -r requirements.txt
# Set GEMINI_API_KEY in lab/.env for the Gemini client
python mcp_client.py --query "What is the price of AAPL?"
python mcp_client_ollama.py --query "Check data sources"
```

Do **not** commit `.env`; it is listed in `.gitignore`.

---

**Full documentation** (features, architecture, troubleshooting): **[lab/README.md](lab/README.md)**

--- 
Seri testing gh pr 123


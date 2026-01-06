# 📈 B3 Tracker

Rastreador de cotações da bolsa brasileira (B3), ações americanas, commodities e criptomoedas com análise técnica, fundamentalista e sinais de trading para alimentar modelos de AI.

## ✨ Recursos

- 📊 **104 ativos rastreados** (Ibovespa, S&P 500, commodities, crypto)
- ⚡ **Fetch paralelo** - 8 workers simultâneos (~30s para 104 ativos)
- 🌐 **REST API** - FastAPI com Swagger UI em http://localhost:8000/docs
- 💱 **Dual currency** - Preços em BRL e USD para todos os ativos
- 📈 **Comparações históricas** - 1D, 1W, 1M, YTD, 5Y, ALL
- 🎯 **Benchmark comparison** - Performance vs IBOV e S&P 500
- 🔬 **Análise fundamentalista** - P/E, P/B, dividend yield, beta, ROE
- 📉 **Indicadores técnicos** - RSI-14, MA50, MA200, golden/death cross
- 🚦 **Trading signals** - Detecção automática de sinais bullish/bearish
- 📰 **News sentiment** - Análise de sentimento de notícias (PT-BR e EN)
- 🔮 **Polymarket sentiment** - Dados de mercados de previsão (cripto, macro, geopolítica)
- 🤖 **AI-ready exports** - JSON otimizado para modelos de machine learning

## 🚀 Quick Start

### Rodar uma vez (buscar cotações agora)

```bash
docker compose run --rm app python src/main.py --once
```

### Rodar em modo contínuo (scheduler diário)

```bash
docker compose up -d
```

### Ver logs

```bash
docker compose logs -f
```

### Parar

```bash
docker compose down
```

## 📋 Comandos Disponíveis

| Comando | Descrição |
|---------|-----------|
| `python src/main.py` | Inicia scheduler (roda diariamente às 18h) |
| `python src/main.py --once` | Busca cotações uma vez e mostra sinais |
| `python src/main.py --export` | Exporta dados existentes para CSV/JSON |
| `python src/main.py --summary` | Mostra resumo das cotações no terminal |
| `python src/main.py --signals` | Mostra sinais de trading detectados |
| `python src/main.py --news` | Mostra análise de sentimento de notícias |
| `python src/main.py --polymarket` | Mostra sentimento do Polymarket |
| `python src/main.py --ai` | Mostra análise AI + sinais + news + Polymarket |
| `python src/main.py --report` | Gera relatórios Human (MD) + AI (JSON) |

## 📄 Relatórios Consolidados

O comando `--report` gera dois relatórios complementares:

### Human Report (Markdown)
Arquivo `exports/report_YYYY-MM-DD.md` com:
- 📊 **Market Summary** - Totais, benchmarks YTD (IBOV, S&P 500, USD/BRL)
- 🔥 **Top Movers** - Maiores altas/quedas do dia
- 🚦 **Trading Signals** - RSI oversold/overbought, máximas/mínimas 52w
- 📰 **News Sentiment** - Notícias positivas/negativas recentes
- 🔮 **Polymarket Sentiment** - Sentimento de mercados de previsão (cripto, macro, geopolítica)

### AI Report (JSON)
Arquivo `exports/ai_report_YYYY-MM-DD.json` com:
- `metadata` - Tipo, timestamp, versão
- `market_context` - IBOV YTD, S&P 500 YTD, USD/BRL
- `signals_summary` - Bullish/bearish counts, RSI extremos
- `top_movers` - Gainers/losers com dados completos
- `news_sentiment` - Scores e headlines
- `polymarket_sentiment` - Sentimento de mercados de previsão por categoria
- `actionable_insights` - Listas de potential_buys, potential_sells, momentum_stocks
- `full_data` - Dados completos de todos os 104 ativos

## 🌐 REST API

A API REST está disponível na porta 8000 com documentação Swagger automática.

### Iniciar a API

```bash
docker compose up -d api
```

Acesse: http://localhost:8000/docs para a documentação interativa.

### Endpoints Disponíveis

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/` | GET | Health check e lista de endpoints |
| `/api/quotes` | GET | Todas as cotações (com filtro `?type=stock`) |
| `/api/quotes/{ticker}` | GET | Dados detalhados de um ativo (ex: `/api/quotes/PETR4`) |
| `/api/signals` | GET | Sinais de trading ativos (com filtro `?signal_type=RSI_OVERSOLD`) |
| `/api/news` | GET | Sentimento de notícias (com filtro `?sentiment=positive`) |
| `/api/sectors` | GET | Performance agregada por setor |
| `/api/movers` | GET | Top gainers/losers (com filtro `?period=ytd&limit=10`) |
| `/api/report` | GET | Relatório consolidado completo |
| `/api/refresh` | POST | Disparar atualização de dados em background |
| `/docs` | GET | Swagger UI interativo |

### Exemplos de Uso

```bash
# Cotação da Petrobras
curl http://localhost:8000/api/quotes/PETR4

# Ações com RSI oversold (potencial compra)
curl "http://localhost:8000/api/signals?signal_type=RSI_OVERSOLD"

# Notícias positivas
curl "http://localhost:8000/api/news?sentiment=positive"

# Top 5 maiores altas YTD
curl "http://localhost:8000/api/movers?period=ytd&limit=5"

# Performance por setor
curl http://localhost:8000/api/sectors
```

### Tipos de Sinais

| Sinal | Descrição |
|-------|-----------|
| `RSI_OVERSOLD` | RSI < 30 (potencial compra) |
| `RSI_OVERBOUGHT` | RSI > 70 (potencial venda) |
| `GOLDEN_CROSS` | MA50 cruzou acima da MA200 |
| `BULLISH_TREND` | Acima de MA50 e MA200 |
| `BEARISH_TREND` | Abaixo de MA50 e MA200 |
| `NEAR_52W_HIGH` | Dentro de 5% da máxima 52 semanas |
| `NEAR_52W_LOW` | Dentro de 5% da mínima 52 semanas |
| `VOLUME_SPIKE` | Volume > 2x média |
| `POSITIVE_NEWS` | Sentimento de notícias > 0.3 |
| `NEGATIVE_NEWS` | Sentimento de notícias < -0.3 |

## 📁 Estrutura do Projeto

```
b3_tracker/
├── docker-compose.yml    # Orquestração Docker
├── Dockerfile            # Imagem Python
├── requirements.txt      # Dependências
├── src/
│   ├── main.py           # CLI entry point
│   ├── api.py            # REST API (FastAPI)
│   ├── assets.py         # Lista de ativos (97+ ações)
│   ├── database.py       # Conexão SQLite
│   ├── models.py         # Modelos de dados (70+ campos)
│   ├── fetcher.py        # Busca cotações + indicadores
│   ├── exporter.py       # Exporta CSV/JSON + views
│   └── scheduler.py      # Agendamento diário
├── data/                 # Banco de dados SQLite
│   └── cotacoes.db
└── exports/              # Arquivos exportados
    ├── cotacoes_YYYY-MM-DD.csv
    ├── cotacoes_YYYY-MM-DD.json
    ├── ai_analysis_YYYY-MM-DD.json
    ├── report_YYYY-MM-DD.md        # 📄 Human report
    └── ai_report_YYYY-MM-DD.json   # 🤖 AI report
```

## 💾 Ativos Rastreados

### 🇧🇷 Ações do Ibovespa (77 ativos)

| Setor | Exemplos |
|-------|----------|
| Bancário | BBAS3, ITUB4, BBDC4, SANB11, BPAC11 |
| Petróleo e Gás | PETR4, PRIO3, CSAN3, VBBR3 |
| Mineração | VALE3, CSNA3, CMIN3, GGBR4 |
| Energia Elétrica | ELET3, EGIE3, EQTL3, CPFE3 |
| Varejo | MGLU3, LREN3, AMER3, BHIA3 |
| Saúde | RDOR3, HAPV3, RADL3, FLRY3 |
| Industrial | WEGE3, EMBR3, SUZB3, KLBN11 |
| E muitos outros... | |

### 🇺🇸 Ações Americanas (20 ativos)

| Setor | Exemplos |
|-------|----------|
| Big Tech | AAPL, MSFT, GOOGL, AMZN, META, NVDA |
| Financeiro | JPM, BAC, WFC, GS |
| Saúde | JNJ, UNH, PFE |
| Consumo | KO, PEP, MCD, WMT |
| Energia | XOM |
| Automotivo | TSLA |

### Commodities

| Ativo | Símbolo |
|-------|---------|
| Ouro | GC=F |
| Prata | SI=F |
| Platina | PL=F |
| Paládio | PA=F |

### Criptomoedas

| Ativo | Símbolo |
|-------|---------|
| Bitcoin | BTC-USD |
| Ethereum | ETH-USD |

### Câmbio

| Par | Símbolo |
|-----|---------|
| Dólar/Real | USDBRL=X |

## 🔬 Dados Disponíveis

### Preços e Variações
- Preço atual (BRL e USD)
- Variações: 1D, 1W, 1M, YTD, 5Y, All-time
- Preços históricos de referência

### Benchmark Comparison
- Performance do IBOV e S&P 500
- Outperformance vs benchmarks (vs_ibov_*, vs_sp500_*)

### Análise Fundamentalista
- P/E Ratio, Forward P/E
- P/B Ratio
- Dividend Yield, EPS
- Market Cap
- Profit Margin, ROE, Debt/Equity

### Métricas de Risco
- Beta
- 52-week high/low
- % from 52-week high

### Indicadores Técnicos
- RSI-14 (Relative Strength Index)
- MA50, MA200 (Moving Averages)
- Golden Cross / Death Cross detection
- 30-day volatility
- Volume ratio (vs 20-day average)

### Trading Signals
- `signal_rsi_oversold` - RSI < 30
- `signal_rsi_overbought` - RSI > 70
- `signal_52w_high` - Near 52-week high
- `signal_52w_low` - Near 52-week low
- `signal_golden_cross` - MA50 > MA200
- `signal_death_cross` - MA50 < MA200
- `signal_volume_spike` - Volume > 2x average
- `signal_summary` - bullish / bearish / neutral

### Dados de Analistas
- Analyst rating (buy/hold/sell)
- Target price
- Number of analysts

### 📰 News Sentiment (Novo!)
- `news_sentiment_pt` - Score de notícias em português (-1 a +1)
- `news_sentiment_en` - Score de notícias em inglês (-1 a +1)
- `news_sentiment_combined` - Score combinado (60% PT + 40% EN para BR)
- `news_count_pt` / `news_count_en` - Quantidade de notícias
- `news_headline_pt` / `news_headline_en` - Manchete mais recente
- `news_sentiment_label` - positive / negative / neutral

## 📊 Formato dos Dados Exportados

### CSV

```csv
ticker,nome,setor,tipo,preco_brl,preco_usd,var_1d,var_1w,var_1m,var_ytd,vs_ibov_ytd,vs_sp500_ytd,pe_ratio,rsi_14,signal_summary,...
BBAS3,Banco do Brasil,Bancário,stock,21.85,3.94,+0.5,+2.1,+5.3,+12.4,-21.4,-5.4,4.2,55,neutral,...
AAPL,Apple,Technology,us_stock,1515.57,273.39,+0.3,+1.2,+3.1,+28.5,-5.3,+10.7,28.5,62,bullish,...
```

### JSON (AI-optimized)

```json
{
  "metadata": {
    "generated_at": "2025-12-27T00:15:00",
    "total_assets": 104,
    "data_version": "2.0",
    "description": "B3 and US stock data with fundamentals for AI analysis"
  },
  "market_summary": {
    "brazil_stocks": 77,
    "us_stocks": 20,
    "commodities": 4,
    "crypto": 2
  },
  "assets": [
    {
      "ticker": "BBAS3",
      "nome": "Banco do Brasil",
      "setor": "Bancário",
      "tipo": "stock",
      "preco_brl": 21.85,
      "preco_usd": 3.94,
      "var_1d": 0.5,
      "var_ytd": 12.4,
      "vs_ibov_ytd": -21.4,
      "pe_ratio": 4.2,
      "rsi_14": 55,
      "signal_summary": "neutral",
      "analyst_rating": "buy"
    }
  ]
}
```

## 🚦 Trading Signals Output

```
================================================================================
  🚦 TRADING SIGNALS DETECTED
================================================================================

📈 BULLISH SIGNALS (12 stocks):
   EMBR3    Embraer              RSI:    58 | YTD: +150.2%
   BPAC11   BTG Pactual          RSI:    52 | YTD:  +45.3%

📉 BEARISH SIGNALS (8 stocks):
   CSAN3    Cosan                RSI:    42 | YTD:  -55.2%
   AZUL4    Azul                 RSI:    35 | YTD:  -78.1%

🟢 RSI OVERSOLD (<30) - Potential buy (3 stocks):
   PCAR3    RSI:    28
   BHIA3    RSI:    25

🔴 RSI OVERBOUGHT (>70) - Potential sell (2 stocks):
   NVDA     RSI:    72
   META     RSI:    71

⬆️ NEAR 52-WEEK HIGH (within 5%) (5 stocks):
   WEGE3    WEG
   EMBR3    Embraer

✨ GOLDEN CROSS (MA50 > MA200) (45 stocks):
   ITUB4    Itaú Unibanco PN
   BBAS3    Banco do Brasil
================================================================================
```

## 📰 News Sentiment Output

```
========================================================================================================================
  📰 NEWS SENTIMENT ANALYSIS
========================================================================================================================

🇧🇷 BRAZIL - 🟢 POSITIVE SENTIMENT (12 stocks):
   RDOR3    Rede D'Or        PT: +0.50 (10) | EN:   N/A (2) | Combined: +0.50
            "Rede D'Or supera R$ 100 bi em valor de mercado..."
   TOTS3    Totvs            PT: +0.39 (10) | EN:   N/A (10) | Combined: +0.39
            "No deserto de ações de IA e tecnologia na B3..."

🇧🇷 BRAZIL - 🔴 NEGATIVE SENTIMENT (5 stocks):
   OIBR3    Oi ON            PT: -0.63 (10) | EN:   N/A (2) | Combined: -0.63
            "A Oi (OIBR3) faliu: e agora, como ficam os acionistas?"
   USIM5    Usiminas         PT: -0.36 (10) | EN:   N/A (10) | Combined: -0.36
            "Por que as ações da Usiminas estão caindo?"

🇺🇸 USA - 🟢 POSITIVE SENTIMENT (8 stocks):
   NVDA     NVIDIA           EN: +0.45 (5 articles)
            "NVIDIA beats expectations with record datacenter revenue..."
========================================================================================================================
Summary: 12 positive | 5 negative | 59 neutral | 96 stocks with news
========================================================================================================================
```

## ⚙️ Configuração

### Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `SCHEDULE_ENABLED` | `true` | Ativa/desativa scheduler |
| `SCHEDULE_TIME` | `18:00` | Horário de execução diária |
| `TZ` | `America/Sao_Paulo` | Timezone |
| `DB_PATH` | `/app/data/cotacoes.db` | Caminho do banco |
| `EXPORTS_PATH` | `/app/exports` | Pasta de exportação |

### Modificar horário de execução

Edite o `docker-compose.yml`:

```yaml
environment:
  - SCHEDULE_TIME=09:30  # Executar às 9:30
```

## 🔧 Desenvolvimento

### Adicionar novos ativos

Edite `src/assets.py`:

```python
# Ações brasileiras
IBOVESPA_STOCKS = {
    "NOVO3.SA": {"name": "Nova Empresa", "sector": "Setor"},
}

# Ações americanas (sem .SA)
US_STOCKS = {
    "TSLA": {"name": "Tesla", "sector": "Automotive"},
}
```

### Rodar localmente (sem Docker)

```bash
pip install -r requirements.txt
python src/main.py --once
```

### Comandos úteis de desenvolvimento

```bash
# Atualizar apenas cotações
docker compose run --rm runner python src/main.py --once

# Ver análise AI com benchmarks
docker compose run --rm runner python src/main.py --ai

# Verificar sinais de trading
docker compose run --rm runner python src/main.py --signals

# Ver análise de sentimento de notícias
docker compose run --rm runner python src/main.py --news

# Exportar para análise
docker compose run --rm runner python src/main.py --export --json
```

## 📝 Licença

MIT

---

## ⚡ Performance

O sistema utiliza **processamento paralelo** para buscar dados de forma eficiente:

| Fase | Workers | Tempo | Descrição |
|------|---------|-------|-----------|
| Fase 1 | 3 | ~1.5s | Benchmarks (USD/BRL, IBOV, S&P500) |
| Fase 2 | 8 | ~18s | Cotações de 104 ativos |
| Fase 3 | 5 | ~9s | Notícias de 97 ações |
| Fase 4 | 1 | ~0.5s | Save to DB (sequencial) |
| **Total** | - | **~30s** | **3.6 ativos/segundo** |

### Comparativo

| Modo | Tempo | Speedup |
|------|-------|---------|
| Sequencial (antigo) | 4:01 (241s) | 1x |
| **Paralelo (atual)** | **0:30 (30s)** | **8x** |

---

Desenvolvido para análise de investimentos no mercado brasileiro e americano. 
Use por sua conta e risco - dados são informativos e não constituem recomendação de investimento.

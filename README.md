# 📈 B3 Tracker

Rastreador de cotações da bolsa brasileira (B3), commodities (ouro, prata, platina) e criptomoedas (Bitcoin, Ethereum).

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
| `python src/main.py --once` | Busca cotações uma vez e sai |
| `python src/main.py --export` | Exporta dados existentes para CSV/JSON |
| `python src/main.py --summary` | Mostra resumo das cotações no terminal |

## 📁 Estrutura do Projeto

```
b3_tracker/
├── docker-compose.yml    # Orquestração Docker
├── Dockerfile            # Imagem Python
├── requirements.txt      # Dependências
├── src/
│   ├── main.py           # Ponto de entrada
│   ├── assets.py         # Lista de ativos (85+ ações)
│   ├── database.py       # Conexão SQLite
│   ├── models.py         # Modelos de dados
│   ├── fetcher.py        # Busca cotações (yfinance)
│   ├── exporter.py       # Exporta CSV/JSON
│   └── scheduler.py      # Agendamento diário
├── data/                 # Banco de dados SQLite
│   └── cotacoes.db
└── exports/              # Arquivos exportados
    ├── cotacoes_YYYY-MM-DD.csv
    └── cotacoes_YYYY-MM-DD.json
```

## 💾 Ativos Rastreados

### Ações do Ibovespa (~85 ativos)

| Setor | Exemplos |
|-------|----------|
| Bancário | BBAS3, ITUB4, BBDC4, SANB11 |
| Petróleo e Gás | PETR4, PRIO3, CSAN3 |
| Mineração | VALE3, CSNA3, CMIN3 |
| Energia Elétrica | ELET3, EGIE3, EQTL3 |
| Varejo | MGLU3, LREN3, AMER3 |
| Saúde | RDOR3, HAPV3, RADL3 |
| Industrial | WEGE3, EMBR3, SUZB3 |
| E muitos outros... | |

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

## 📊 Formato dos Dados Exportados

### CSV

```csv
ticker,nome,setor,tipo,preco_brl,preco_usd,abertura,maxima,minima,volume,data_cotacao,atualizado_em
BBAS3,Banco do Brasil,Bancário,stock,21.85,,21.50,22.10,21.30,5000000,2025-12-26,2025-12-26 18:00:00
```

### JSON

```json
{
  "data_exportacao": "2025-12-26 18:00:00",
  "total_ativos": 90,
  "cotacoes": [
    {
      "ticker": "BBAS3",
      "nome": "Banco do Brasil",
      "setor": "Bancário",
      "tipo": "stock",
      "preco_brl": 21.85,
      "preco_usd": null,
      "data_cotacao": "2025-12-26"
    }
  ]
}
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
IBOVESPA_STOCKS = {
    # Adicione aqui
    "NOVO3.SA": {"name": "Nova Empresa", "sector": "Setor"},
}
```

### Rodar localmente (sem Docker)

```bash
pip install -r requirements.txt
python src/main.py --once
```

## 📝 Licença

MIT

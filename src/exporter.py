"""
Módulo para exportar dados para CSV e JSON
"""
import os
import json
import csv
from datetime import datetime, date
from typing import Optional
from sqlalchemy import func

from database import SessionLocal
from models import Asset, Quote


EXPORTS_PATH = os.environ.get("EXPORTS_PATH", "/app/exports")


def get_latest_quotes(db, quote_date: Optional[date] = None):
    """
    Obtém as cotações mais recentes de todos os ativos
    Se quote_date for fornecido, busca cotações dessa data específica
    """
    if quote_date:
        target_date = datetime.combine(quote_date, datetime.min.time())
        quotes = db.query(Quote).join(Asset).filter(
            Quote.quote_date == target_date
        ).all()
    else:
        # Subquery para pegar a última cotação de cada ativo
        subquery = db.query(
            Quote.asset_id,
            func.max(Quote.quote_date).label('max_date')
        ).group_by(Quote.asset_id).subquery()
        
        quotes = db.query(Quote).join(
            subquery,
            (Quote.asset_id == subquery.c.asset_id) & 
            (Quote.quote_date == subquery.c.max_date)
        ).all()
    
    return quotes


def format_change(value: Optional[float]) -> str:
    """Formata uma variação percentual com sinal e cores ANSI"""
    if value is None:
        return "N/A"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


def format_quote_row(quote: Quote) -> dict:
    """Formata uma cotação para exportação"""
    return {
        "ticker": quote.asset.ticker.replace(".SA", ""),
        "nome": quote.asset.name,
        "setor": quote.asset.sector,
        "tipo": quote.asset.asset_type,
        "preco_brl": round(quote.price_brl, 2),
        "preco_usd": round(quote.price_usd, 2) if quote.price_usd else None,
        "abertura": round(quote.open_price, 2) if quote.open_price else None,
        "maxima": round(quote.high_price, 2) if quote.high_price else None,
        "minima": round(quote.low_price, 2) if quote.low_price else None,
        "volume": quote.volume,
        # Variações históricas
        "var_1d": round(quote.change_1d, 2) if quote.change_1d else None,
        "var_1w": round(quote.change_1w, 2) if quote.change_1w else None,
        "var_1m": round(quote.change_1m, 2) if quote.change_1m else None,
        "var_ytd": round(quote.change_ytd, 2) if quote.change_ytd else None,
        "var_5y": round(quote.change_5y, 2) if quote.change_5y else None,
        "var_all": round(quote.change_all, 2) if quote.change_all else None,
        # Preços históricos
        "preco_1d_ago": round(quote.price_1d_ago, 2) if quote.price_1d_ago else None,
        "preco_1w_ago": round(quote.price_1w_ago, 2) if quote.price_1w_ago else None,
        "preco_1m_ago": round(quote.price_1m_ago, 2) if quote.price_1m_ago else None,
        "preco_inicio_ano": round(quote.price_ytd, 2) if quote.price_ytd else None,
        "preco_5y_ago": round(quote.price_5y_ago, 2) if quote.price_5y_ago else None,
        "preco_all_time": round(quote.price_all_time, 2) if quote.price_all_time else None,
        "data_cotacao": quote.quote_date.strftime("%Y-%m-%d"),
        "atualizado_em": quote.fetched_at.strftime("%Y-%m-%d %H:%M:%S")
    }


def export_to_csv(quote_date: Optional[date] = None, filename: Optional[str] = None) -> str:
    """
    Exporta cotações para CSV
    
    Args:
        quote_date: Data específica para exportar (None = mais recentes)
        filename: Nome do arquivo (None = gera automaticamente)
    
    Returns:
        Caminho do arquivo gerado
    """
    db = SessionLocal()
    
    try:
        quotes = get_latest_quotes(db, quote_date)
        
        if not quotes:
            print("⚠️ Nenhuma cotação encontrada para exportar")
            return None
        
        # Gerar nome do arquivo
        if not filename:
            date_str = quote_date.strftime("%Y-%m-%d") if quote_date else datetime.now().strftime("%Y-%m-%d")
            filename = f"cotacoes_{date_str}.csv"
        
        filepath = os.path.join(EXPORTS_PATH, filename)
        
        # Criar diretório se não existir
        os.makedirs(EXPORTS_PATH, exist_ok=True)
        
        # Escrever CSV
        rows = [format_quote_row(q) for q in quotes]
        
        # Ordenar por setor e ticker
        rows.sort(key=lambda x: (x["setor"], x["ticker"]))
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"✅ CSV exportado: {filepath} ({len(rows)} registros)")
        return filepath
        
    finally:
        db.close()


def export_to_json(quote_date: Optional[date] = None, filename: Optional[str] = None) -> str:
    """
    Exporta cotações para JSON
    
    Args:
        quote_date: Data específica para exportar (None = mais recentes)
        filename: Nome do arquivo (None = gera automaticamente)
    
    Returns:
        Caminho do arquivo gerado
    """
    db = SessionLocal()
    
    try:
        quotes = get_latest_quotes(db, quote_date)
        
        if not quotes:
            print("⚠️ Nenhuma cotação encontrada para exportar")
            return None
        
        # Gerar nome do arquivo
        if not filename:
            date_str = quote_date.strftime("%Y-%m-%d") if quote_date else datetime.now().strftime("%Y-%m-%d")
            filename = f"cotacoes_{date_str}.json"
        
        filepath = os.path.join(EXPORTS_PATH, filename)
        
        # Criar diretório se não existir
        os.makedirs(EXPORTS_PATH, exist_ok=True)
        
        # Preparar dados
        rows = [format_quote_row(q) for q in quotes]
        rows.sort(key=lambda x: (x["setor"], x["ticker"]))
        
        data = {
            "data_exportacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_ativos": len(rows),
            "cotacoes": rows
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ JSON exportado: {filepath} ({len(rows)} registros)")
        return filepath
        
    finally:
        db.close()


def print_summary():
    """Imprime um resumo das cotações mais recentes com variações"""
    db = SessionLocal()
    
    try:
        quotes = get_latest_quotes(db)
        
        if not quotes:
            print("⚠️ Nenhuma cotação encontrada")
            return
        
        rows = [format_quote_row(q) for q in quotes]
        
        # Formatar variações com cores ANSI e alinhamento correto
        def color_change(val):
            if val is None:
                return "     N/A"
            # Formato fixo de 8 caracteres: sinal + número + %
            color = "\033[92m" if val >= 0 else "\033[91m"  # Verde/Vermelho
            reset = "\033[0m"
            if val >= 0:
                return f"{color}{val:>+7.1f}%{reset}"
            else:
                return f"{color}{val:>7.1f}%{reset}"
        
        def print_section(title, section_rows):
            """Imprime uma seção de ativos"""
            if not section_rows:
                return
            
            print(f"\n{'='*140}")
            print(f"  {title}")
            print(f"{'='*140}")
            print(f"{'TICKER':<10} {'NOME':<20} {'BRL':>12} {'USD':>10} {'1D':>8} {'1W':>8} {'1M':>8} {'YTD':>8} {'5Y':>8} {'ALL':>8}")
            print("-"*140)
            
            current_sector = None
            for row in section_rows:
                if row["setor"] != current_sector:
                    current_sector = row["setor"]
                    print(f"\n--- {current_sector.upper()} ---")
                
                usd_str = f"{row['preco_usd']:>10.2f}" if row['preco_usd'] else "       N/A"
                
                print(f"{row['ticker']:<10} {row['nome'][:19]:<20} {row['preco_brl']:>12,.2f} {usd_str} "
                      f"{color_change(row['var_1d'])} {color_change(row['var_1w'])} "
                      f"{color_change(row['var_1m'])} {color_change(row['var_ytd'])} "
                      f"{color_change(row['var_5y'])} {color_change(row['var_all'])}")
        
        # Separar por tipo de ativo
        br_stocks = [r for r in rows if r["tipo"] == "stock"]
        us_stocks = [r for r in rows if r["tipo"] == "us_stock"]
        commodities = [r for r in rows if r["tipo"] == "commodity"]
        crypto = [r for r in rows if r["tipo"] == "crypto"]
        currency = [r for r in rows if r["tipo"] == "currency"]
        
        # Ordenar cada seção por setor e ticker
        for section in [br_stocks, us_stocks, commodities, crypto, currency]:
            section.sort(key=lambda x: (x["setor"], x["ticker"]))
        
        # Imprimir cada seção
        print_section("🇧🇷 AÇÕES BRASILEIRAS (B3)", br_stocks)
        print_section("🇺🇸 AÇÕES AMERICANAS (NYSE/NASDAQ)", us_stocks)
        print_section("🥇 COMMODITIES", commodities)
        print_section("₿ CRIPTOMOEDAS", crypto)
        print_section("💱 CÂMBIO", currency)
        
        print(f"\n{'='*140}")
        print(f"Total de ativos: {len(rows)} | 🇧🇷 Brasil: {len(br_stocks)} | 🇺🇸 EUA: {len(us_stocks)} | "
              f"Commodities: {len(commodities)} | Crypto: {len(crypto)}")
        print("Legenda: 1D = Dia anterior | 1W = 1 semana | 1M = 1 mês | YTD = Ano até a data | 5Y = 5 anos | ALL = Desde o início")
        print("="*140 + "\n")
        
    finally:
        db.close()


if __name__ == "__main__":
    from database import init_db
    init_db()
    
    print("\n📊 Exportando cotações...\n")
    export_to_csv()
    export_to_json()
    print_summary()

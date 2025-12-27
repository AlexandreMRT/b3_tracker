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
    """Imprime um resumo das cotações mais recentes"""
    db = SessionLocal()
    
    try:
        quotes = get_latest_quotes(db)
        
        if not quotes:
            print("⚠️ Nenhuma cotação encontrada")
            return
        
        rows = [format_quote_row(q) for q in quotes]
        rows.sort(key=lambda x: (x["setor"], x["ticker"]))
        
        print("\n" + "="*80)
        print(f"{'TICKER':<10} {'NOME':<25} {'SETOR':<20} {'PREÇO (R$)':>12}")
        print("="*80)
        
        current_sector = None
        for row in rows:
            if row["setor"] != current_sector:
                current_sector = row["setor"]
                print(f"\n--- {current_sector.upper()} ---")
            
            print(f"{row['ticker']:<10} {row['nome'][:24]:<25} {row['setor'][:19]:<20} {row['preco_brl']:>12,.2f}")
        
        print("\n" + "="*80)
        print(f"Total de ativos: {len(rows)}")
        print("="*80 + "\n")
        
    finally:
        db.close()


if __name__ == "__main__":
    from database import init_db
    init_db()
    
    print("\n📊 Exportando cotações...\n")
    export_to_csv()
    export_to_json()
    print_summary()

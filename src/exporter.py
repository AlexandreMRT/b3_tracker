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
        # Fundamental data
        "market_cap": quote.market_cap,
        "pe_ratio": round(quote.pe_ratio, 2) if quote.pe_ratio else None,
        "forward_pe": round(quote.forward_pe, 2) if quote.forward_pe else None,
        "pb_ratio": round(quote.pb_ratio, 2) if quote.pb_ratio else None,
        "dividend_yield": round(quote.dividend_yield, 2) if quote.dividend_yield else None,
        "eps": round(quote.eps, 2) if quote.eps else None,
        # Risk metrics
        "beta": round(quote.beta, 2) if quote.beta else None,
        "week_52_high": round(quote.week_52_high, 2) if quote.week_52_high else None,
        "week_52_low": round(quote.week_52_low, 2) if quote.week_52_low else None,
        "pct_from_52w_high": round(quote.pct_from_52w_high, 2) if quote.pct_from_52w_high else None,
        # Technical indicators
        "ma_50": round(quote.ma_50, 2) if quote.ma_50 else None,
        "ma_200": round(quote.ma_200, 2) if quote.ma_200 else None,
        "rsi_14": round(quote.rsi_14, 1) if quote.rsi_14 else None,
        "above_ma_50": quote.above_ma_50,
        "above_ma_200": quote.above_ma_200,
        "ma_50_above_200": quote.ma_50_above_200,
        # Financial health
        "profit_margin": round(quote.profit_margin, 2) if quote.profit_margin else None,
        "roe": round(quote.roe, 2) if quote.roe else None,
        "debt_to_equity": round(quote.debt_to_equity, 2) if quote.debt_to_equity else None,
        # Analyst data
        "analyst_rating": quote.analyst_rating,
        "target_price": round(quote.target_price, 2) if quote.target_price else None,
        "num_analysts": quote.num_analysts,
        # Benchmark comparison
        "ibov_change_1d": round(quote.ibov_change_1d, 2) if quote.ibov_change_1d else None,
        "ibov_change_ytd": round(quote.ibov_change_ytd, 2) if quote.ibov_change_ytd else None,
        "sp500_change_1d": round(quote.sp500_change_1d, 2) if quote.sp500_change_1d else None,
        "sp500_change_ytd": round(quote.sp500_change_ytd, 2) if quote.sp500_change_ytd else None,
        "vs_ibov_1d": round(quote.vs_ibov_1d, 2) if quote.vs_ibov_1d else None,
        "vs_ibov_1m": round(quote.vs_ibov_1m, 2) if quote.vs_ibov_1m else None,
        "vs_ibov_ytd": round(quote.vs_ibov_ytd, 2) if quote.vs_ibov_ytd else None,
        "vs_sp500_1d": round(quote.vs_sp500_1d, 2) if quote.vs_sp500_1d else None,
        "vs_sp500_1m": round(quote.vs_sp500_1m, 2) if quote.vs_sp500_1m else None,
        "vs_sp500_ytd": round(quote.vs_sp500_ytd, 2) if quote.vs_sp500_ytd else None,
        # Trading signals
        "signal_golden_cross": quote.signal_golden_cross,
        "signal_death_cross": quote.signal_death_cross,
        "signal_rsi_oversold": quote.signal_rsi_oversold,
        "signal_rsi_overbought": quote.signal_rsi_overbought,
        "signal_52w_high": quote.signal_52w_high,
        "signal_52w_low": quote.signal_52w_low,
        "signal_volume_spike": quote.signal_volume_spike,
        "signal_summary": quote.signal_summary,
        # Volatility
        "volatility_30d": round(quote.volatility_30d, 2) if quote.volatility_30d else None,
        "avg_volume_20d": quote.avg_volume_20d,
        "volume_ratio": round(quote.volume_ratio, 2) if quote.volume_ratio else None,
        # News sentiment
        "news_sentiment_pt": round(quote.news_sentiment_pt, 3) if quote.news_sentiment_pt else None,
        "news_sentiment_en": round(quote.news_sentiment_en, 3) if quote.news_sentiment_en else None,
        "news_sentiment_combined": round(quote.news_sentiment_combined, 3) if quote.news_sentiment_combined else None,
        "news_count_pt": quote.news_count_pt,
        "news_count_en": quote.news_count_en,
        "news_headline_pt": quote.news_headline_pt,
        "news_headline_en": quote.news_headline_en,
        "news_sentiment_label": quote.news_sentiment_label,
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


def print_ai_analysis():
    """Imprime análise detalhada com dados fundamentais para AI"""
    db = SessionLocal()
    
    try:
        quotes = get_latest_quotes(db)
        
        if not quotes:
            print("⚠️ Nenhuma cotação encontrada")
            return
        
        rows = [format_quote_row(q) for q in quotes]
        
        def format_rating(rating):
            if not rating:
                return "    N/A"
            colors = {"buy": "\033[92m", "strong_buy": "\033[92m", 
                      "hold": "\033[93m", "sell": "\033[91m", "strong_sell": "\033[91m"}
            color = colors.get(rating, "")
            return f"{color}{rating:>7}\033[0m"
        
        def format_rsi(val):
            if val is None:
                return "   N/A"
            color = "\033[91m" if val > 70 else ("\033[92m" if val < 30 else "")
            return f"{color}{val:>5.0f}\033[0m"
        
        def format_pct(val, invert=False):
            if val is None:
                return "     N/A"
            color = "\033[92m" if (val >= 0) != invert else "\033[91m"
            return f"{color}{val:>+7.1f}%\033[0m"
        
        def format_signal(summary):
            if not summary:
                return "  N/A  "
            colors = {"bullish": "\033[92m", "bearish": "\033[91m", "neutral": "\033[93m"}
            emoji = {"bullish": "📈", "bearish": "📉", "neutral": "➖"}
            color = colors.get(summary, "")
            icon = emoji.get(summary, "")
            return f"{color}{icon}{summary[:4]:>4}\033[0m"
        
        print(f"\n{'='*180}")
        print("  🤖 AI INVESTMENT ANALYSIS - FUNDAMENTAL & TECHNICAL DATA")
        print(f"{'='*180}")
        print(f"{'TICKER':<8} {'NOME':<16} {'P/E':>7} {'BETA':>5} {'RSI':>5} {'vs52H':>8} {'vsIBOV':>8} {'vsSP500':>8} {'SIGNAL':>8} {'MA50':>5} {'MA200':>5} {'RATING':>8} {'VOL30D':>7}")
        print("-"*180)
        
        # Only show stocks (not commodities/crypto)
        stocks = [r for r in rows if r["tipo"] in ("stock", "us_stock")]
        stocks.sort(key=lambda x: (x["tipo"], x["setor"], x["ticker"]))
        
        current_type = None
        for row in stocks:
            if row["tipo"] != current_type:
                current_type = row["tipo"]
                label = "🇧🇷 BRAZIL" if current_type == "stock" else "🇺🇸 USA"
                print(f"\n{'='*40} {label} {'='*40}")
            
            pe = f"{row['pe_ratio']:>7.1f}" if row['pe_ratio'] else "    N/A"
            beta = f"{row['beta']:>5.2f}" if row['beta'] else "  N/A"
            ma50 = "  ✓" if row['above_ma_50'] == 1 else ("  ✗" if row['above_ma_50'] == 0 else " N/A")
            ma200 = "  ✓" if row['above_ma_200'] == 1 else ("  ✗" if row['above_ma_200'] == 0 else " N/A")
            vol30d = f"{row['volatility_30d']:>6.2f}%" if row['volatility_30d'] else "    N/A"
            
            # Use vs_ibov_ytd for Brazil, vs_sp500_ytd for US
            if row["tipo"] == "stock":
                vs_bench = format_pct(row['vs_ibov_ytd'])
            else:
                vs_bench = format_pct(row['vs_sp500_ytd'])
            
            print(f"{row['ticker']:<8} {row['nome'][:15]:<16} {pe} {beta} "
                  f"{format_rsi(row['rsi_14'])} {format_pct(row['pct_from_52w_high'], invert=True)} "
                  f"{format_pct(row['vs_ibov_ytd'])} {format_pct(row['vs_sp500_ytd'])} "
                  f"{format_signal(row['signal_summary'])} {ma50} {ma200} {format_rating(row['analyst_rating'])} {vol30d}")
        
        print(f"\n{'='*180}")
        print("Legend: vsIBOV/vsSP500 = YTD outperformance vs benchmark | SIGNAL = AI-detected signal (bullish/bearish/neutral)")
        print("        VOL30D = 30-day volatility | RSI = 14-day RSI (>70 overbought, <30 oversold) | vs52H = % from 52-week high")
        print("="*180 + "\n")
        
    finally:
        db.close()


def print_signals():
    """Imprime sinais de trading detectados"""
    db = SessionLocal()
    
    try:
        quotes = get_latest_quotes(db)
        
        if not quotes:
            print("⚠️ Nenhuma cotação encontrada")
            return
        
        rows = [format_quote_row(q) for q in quotes]
        stocks = [r for r in rows if r["tipo"] in ("stock", "us_stock")]
        
        # Filter by signals
        bullish = [r for r in stocks if r.get('signal_summary') == 'bullish']
        bearish = [r for r in stocks if r.get('signal_summary') == 'bearish']
        oversold = [r for r in stocks if r.get('signal_rsi_oversold') == 1]
        overbought = [r for r in stocks if r.get('signal_rsi_overbought') == 1]
        at_52w_low = [r for r in stocks if r.get('signal_52w_low') == 1]
        at_52w_high = [r for r in stocks if r.get('signal_52w_high') == 1]
        volume_spike = [r for r in stocks if r.get('signal_volume_spike') == 1]
        golden_cross = [r for r in stocks if r.get('signal_golden_cross') == 1]
        
        print(f"\n{'='*80}")
        print("  🚦 TRADING SIGNALS DETECTED")
        print(f"{'='*80}")
        
        if bullish:
            print(f"\n📈 BULLISH SIGNALS ({len(bullish)} stocks):")
            for r in bullish[:10]:
                print(f"   {r['ticker']:<8} {r['nome'][:20]:<20} RSI: {r.get('rsi_14', 'N/A'):>5} | YTD: {r.get('var_ytd', 0):>+6.1f}%")
        
        if bearish:
            print(f"\n📉 BEARISH SIGNALS ({len(bearish)} stocks):")
            for r in bearish[:10]:
                print(f"   {r['ticker']:<8} {r['nome'][:20]:<20} RSI: {r.get('rsi_14', 'N/A'):>5} | YTD: {r.get('var_ytd', 0):>+6.1f}%")
        
        if oversold:
            print(f"\n🟢 RSI OVERSOLD (<30) - Potential buy ({len(oversold)} stocks):")
            for r in oversold:
                print(f"   {r['ticker']:<8} RSI: {r.get('rsi_14', 0):>5.0f}")
        
        if overbought:
            print(f"\n🔴 RSI OVERBOUGHT (>70) - Potential sell ({len(overbought)} stocks):")
            for r in overbought:
                print(f"   {r['ticker']:<8} RSI: {r.get('rsi_14', 0):>5.0f}")
        
        if at_52w_low:
            print(f"\n⬇️ NEAR 52-WEEK LOW (within 5%) ({len(at_52w_low)} stocks):")
            for r in at_52w_low:
                print(f"   {r['ticker']:<8} {r['nome'][:20]:<20}")
        
        if at_52w_high:
            print(f"\n⬆️ NEAR 52-WEEK HIGH (within 5%) ({len(at_52w_high)} stocks):")
            for r in at_52w_high:
                print(f"   {r['ticker']:<8} {r['nome'][:20]:<20}")
        
        if volume_spike:
            print(f"\n📊 VOLUME SPIKE (>2x average) ({len(volume_spike)} stocks):")
            for r in volume_spike:
                ratio = r.get('volume_ratio', 0)
                print(f"   {r['ticker']:<8} Volume: {ratio:>4.1f}x average")
        
        if golden_cross:
            print(f"\n✨ GOLDEN CROSS (MA50 > MA200) ({len(golden_cross)} stocks):")
            for r in golden_cross[:10]:
                print(f"   {r['ticker']:<8} {r['nome'][:20]:<20}")
        
        print(f"\n{'='*80}\n")
        
    finally:
        db.close()


def print_news_sentiment():
    """Imprime análise de sentimento de notícias"""
    db = SessionLocal()
    
    try:
        quotes = get_latest_quotes(db)
        
        if not quotes:
            print("⚠️ Nenhuma cotação encontrada")
            return
        
        rows = [format_quote_row(q) for q in quotes]
        stocks = [r for r in rows if r["tipo"] in ("stock", "us_stock")]
        
        # Filter by sentiment
        positive = [r for r in stocks if r.get('news_sentiment_label') == 'positive']
        negative = [r for r in stocks if r.get('news_sentiment_label') == 'negative']
        neutral = [r for r in stocks if r.get('news_sentiment_label') == 'neutral']
        
        # Sort by combined sentiment score
        positive.sort(key=lambda x: x.get('news_sentiment_combined', 0) or 0, reverse=True)
        negative.sort(key=lambda x: x.get('news_sentiment_combined', 0) or 0)
        
        # Separate Brazilian and US stocks
        br_positive = [r for r in positive if r["tipo"] == "stock"]
        us_positive = [r for r in positive if r["tipo"] == "us_stock"]
        br_negative = [r for r in negative if r["tipo"] == "stock"]
        us_negative = [r for r in negative if r["tipo"] == "us_stock"]
        
        def format_score(score):
            if score is None:
                return "  N/A"
            color = "\033[92m" if score >= 0.2 else ("\033[91m" if score <= -0.2 else "\033[93m")
            return f"{color}{score:>+.2f}\033[0m"
        
        def truncate(text, max_len=50):
            if not text:
                return ""
            return text[:max_len] + "..." if len(text) > max_len else text
        
        print(f"\n{'='*120}")
        print("  📰 NEWS SENTIMENT ANALYSIS")
        print(f"{'='*120}")
        
        # Brazilian stocks with positive sentiment
        if br_positive:
            print(f"\n🇧🇷 BRAZIL - 🟢 POSITIVE SENTIMENT ({len(br_positive)} stocks):")
            for r in br_positive[:8]:
                pt_score = format_score(r.get('news_sentiment_pt'))
                en_score = format_score(r.get('news_sentiment_en'))
                combined = format_score(r.get('news_sentiment_combined'))
                pt_count = r.get('news_count_pt', 0) or 0
                en_count = r.get('news_count_en', 0) or 0
                headline = truncate(r.get('news_headline_pt') or r.get('news_headline_en', ''))
                print(f"   {r['ticker']:<8} {r['nome'][:16]:<16} PT: {pt_score} ({pt_count}) | EN: {en_score} ({en_count}) | Combined: {combined}")
                if headline:
                    print(f"            \033[90m\"{headline}\"\033[0m")
        
        # Brazilian stocks with negative sentiment
        if br_negative:
            print(f"\n🇧🇷 BRAZIL - 🔴 NEGATIVE SENTIMENT ({len(br_negative)} stocks):")
            for r in br_negative[:8]:
                pt_score = format_score(r.get('news_sentiment_pt'))
                en_score = format_score(r.get('news_sentiment_en'))
                combined = format_score(r.get('news_sentiment_combined'))
                pt_count = r.get('news_count_pt', 0) or 0
                en_count = r.get('news_count_en', 0) or 0
                headline = truncate(r.get('news_headline_pt') or r.get('news_headline_en', ''))
                print(f"   {r['ticker']:<8} {r['nome'][:16]:<16} PT: {pt_score} ({pt_count}) | EN: {en_score} ({en_count}) | Combined: {combined}")
                if headline:
                    print(f"            \033[90m\"{headline}\"\033[0m")
        
        # US stocks with positive sentiment
        if us_positive:
            print(f"\n🇺🇸 USA - 🟢 POSITIVE SENTIMENT ({len(us_positive)} stocks):")
            for r in us_positive[:8]:
                en_score = format_score(r.get('news_sentiment_en'))
                en_count = r.get('news_count_en', 0) or 0
                headline = truncate(r.get('news_headline_en', ''))
                print(f"   {r['ticker']:<8} {r['nome'][:16]:<16} EN: {en_score} ({en_count} articles)")
                if headline:
                    print(f"            \033[90m\"{headline}\"\033[0m")
        
        # US stocks with negative sentiment
        if us_negative:
            print(f"\n🇺🇸 USA - 🔴 NEGATIVE SENTIMENT ({len(us_negative)} stocks):")
            for r in us_negative[:8]:
                en_score = format_score(r.get('news_sentiment_en'))
                en_count = r.get('news_count_en', 0) or 0
                headline = truncate(r.get('news_headline_en', ''))
                print(f"   {r['ticker']:<8} {r['nome'][:16]:<16} EN: {en_score} ({en_count} articles)")
                if headline:
                    print(f"            \033[90m\"{headline}\"\033[0m")
        
        # Summary
        total_with_news = len([r for r in stocks if r.get('news_count_pt', 0) or r.get('news_count_en', 0)])
        print(f"\n{'='*120}")
        print(f"Summary: {len(positive)} positive | {len(negative)} negative | {len(neutral)} neutral | {total_with_news} stocks with news")
        print("Score range: -1.0 (very negative) to +1.0 (very positive) | Threshold: ±0.2 for classification")
        print("Brazilian stocks: 60% PT weight + 40% EN weight for combined score")
        print(f"{'='*120}\n")
        
    finally:
        db.close()


def export_ai_json(filename: Optional[str] = None) -> str:
    """
    Exporta dados em formato otimizado para análise de AI
    """
    db = SessionLocal()
    
    try:
        quotes = get_latest_quotes(db)
        
        if not quotes:
            print("⚠️ Nenhuma cotação encontrada para exportar")
            return None
        
        if not filename:
            filename = f"ai_analysis_{datetime.now().strftime('%Y-%m-%d')}.json"
        
        filepath = os.path.join(EXPORTS_PATH, filename)
        os.makedirs(EXPORTS_PATH, exist_ok=True)
        
        rows = [format_quote_row(q) for q in quotes]
        
        # Structure for AI consumption
        data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_assets": len(rows),
                "data_version": "2.0",
                "description": "B3 and US stock data with fundamentals for AI analysis"
            },
            "market_summary": {
                "brazil_stocks": len([r for r in rows if r["tipo"] == "stock"]),
                "us_stocks": len([r for r in rows if r["tipo"] == "us_stock"]),
                "commodities": len([r for r in rows if r["tipo"] == "commodity"]),
                "crypto": len([r for r in rows if r["tipo"] == "crypto"]),
            },
            "assets": rows
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ AI JSON exportado: {filepath}")
        return filepath
        
    finally:
        db.close()


if __name__ == "__main__":
    from database import init_db
    init_db()
    
    print("\n📊 Exportando cotações...\n")
    export_to_csv()
    export_to_json()
    export_ai_json()
    print_summary()
    print_ai_analysis()
    print_signals()
    print_news_sentiment()

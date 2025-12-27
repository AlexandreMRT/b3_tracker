#!/usr/bin/env python3
"""
B3 Tracker - Rastreador de cotações da bolsa brasileira

Uso:
    python main.py              # Busca cotações e inicia scheduler
    python main.py --once       # Busca cotações uma vez e sai
    python main.py --export     # Apenas exporta dados existentes
    python main.py --summary    # Mostra resumo das cotações
    python main.py --signals    # Mostra sinais de trading detectados
    python main.py --news       # Mostra análise de sentimento de notícias
    python main.py --ai         # Análise detalhada para AI com sinais e news
"""
import sys
import os

# Adicionar o diretório src ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db
from fetcher import fetch_all_quotes
from exporter import export_to_csv, export_to_json, print_summary, print_ai_analysis, print_signals, print_news_sentiment
from scheduler import run_scheduler


def print_banner():
    """Exibe banner do aplicativo"""
    banner = """
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║   📈 B3 TRACKER - Rastreador de Cotações                ║
    ║                                                          ║
    ║   Ações do Ibovespa + Commodities + Criptomoedas        ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """
    print(banner)


def main():
    """Função principal"""
    print_banner()
    
    # Inicializar banco de dados
    init_db()
    
    # Verificar argumentos
    args = sys.argv[1:]
    
    if "--once" in args or "-1" in args:
        # Executar apenas uma vez
        print("🔄 Modo: Execução única\n")
        fetch_all_quotes()
        export_to_csv()
        export_to_json()
        print_summary()
        print_signals()
        print_news_sentiment()
        
    elif "--export" in args or "-e" in args:
        # Apenas exportar
        print("📤 Modo: Exportação\n")
        export_to_csv()
        export_to_json()
        print_summary()
        
    elif "--summary" in args or "-s" in args:
        # Apenas mostrar resumo
        print("📊 Modo: Resumo\n")
        print_summary()
        
    elif "--signals" in args:
        # Mostrar sinais de trading
        print("🚦 Modo: Trading Signals\n")
        print_signals()
        
    elif "--news" in args:
        # Mostrar análise de sentimento de notícias
        print("📰 Modo: News Sentiment\n")
        print_news_sentiment()
        
    elif "--ai" in args:
        # Análise detalhada para AI
        print("🤖 Modo: AI Analysis\n")
        print_ai_analysis()
        print_signals()
        print_news_sentiment()
        
    elif "--help" in args or "-h" in args:
        print(__doc__)
        
    else:
        # Modo padrão: scheduler
        print("🕐 Modo: Scheduler (execução contínua)\n")
        run_scheduler()


if __name__ == "__main__":
    main()

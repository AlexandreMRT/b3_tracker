"""
Agendador para executar busca de cotações automaticamente
"""
import os
import time
import schedule
from datetime import datetime

from database import init_db
from fetcher import fetch_all_quotes
from exporter import export_to_csv, export_to_json, print_summary


def job():
    """Job que será executado no horário agendado"""
    print(f"\n⏰ Executando job agendado - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Buscar cotações
        success, errors = fetch_all_quotes()
        
        # Exportar arquivos
        if success > 0:
            export_to_csv()
            export_to_json()
            print_summary()
        
        print(f"✅ Job concluído com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro no job: {e}")


def run_scheduler():
    """Inicia o scheduler"""
    schedule_time = os.environ.get("SCHEDULE_TIME", "18:00")
    schedule_enabled = os.environ.get("SCHEDULE_ENABLED", "true").lower() == "true"
    
    print("\n" + "="*60)
    print("🕐 B3 Tracker - Scheduler")
    print("="*60)
    print(f"   Horário agendado: {schedule_time} (horário de Brasília)")
    print(f"   Scheduler ativo: {'Sim' if schedule_enabled else 'Não'}")
    print("="*60 + "\n")
    
    if not schedule_enabled:
        print("⚠️ Scheduler desabilitado. Executando uma vez e saindo...")
        job()
        return
    
    # Agendar execução diária
    schedule.every().day.at(schedule_time).do(job)
    
    # Executar imediatamente na primeira vez
    print("🚀 Executando busca inicial...")
    job()
    
    print(f"\n⏳ Aguardando próxima execução às {schedule_time}...")
    print("   (Pressione Ctrl+C para parar)\n")
    
    # Loop principal
    while True:
        schedule.run_pending()
        time.sleep(60)  # Verificar a cada minuto


if __name__ == "__main__":
    init_db()
    run_scheduler()

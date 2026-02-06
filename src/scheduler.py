"""
Agendador para executar busca de cotações automaticamente
"""

import os
import time
from datetime import datetime

import schedule

from database import init_db
from exporter import export_to_csv, export_to_json, print_summary
from fetcher import fetch_all_quotes
from logger import get_logger

logger = get_logger(__name__)


def job():
    """Job que será executado no horário agendado"""
    logger.info(f"⏰ Executando job agendado - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Buscar cotações
        success, errors = fetch_all_quotes()

        # Exportar arquivos
        if success > 0:
            export_to_csv()
            export_to_json()
            print_summary()

        logger.info("✅ Job concluído com sucesso!")

    except Exception as e:
        logger.error(f"❌ Erro no job: {e}")


def run_scheduler():
    """Inicia o scheduler"""
    schedule_time = os.environ.get("SCHEDULE_TIME", "18:00")
    schedule_enabled = os.environ.get("SCHEDULE_ENABLED", "true").lower() == "true"

    logger.info("=" * 60)
    logger.info("🕐 B3 Tracker - Scheduler")
    logger.info("=" * 60)
    logger.info(f"   Horário agendado: {schedule_time} (horário de Brasília)")
    logger.info(f"   Scheduler ativo: {'Sim' if schedule_enabled else 'Não'}")
    logger.info("=" * 60)

    if not schedule_enabled:
        logger.warning("⚠️ Scheduler desabilitado. Executando uma vez e saindo...")
        job()
        return

    # Agendar execução diária
    schedule.every().day.at(schedule_time).do(job)

    # Executar imediatamente na primeira vez
    logger.info("🚀 Executando busca inicial...")
    job()

    logger.info(f"⏳ Aguardando próxima execução às {schedule_time}...")
    logger.info("   (Pressione Ctrl+C para parar)")

    # Loop principal
    while True:
        schedule.run_pending()
        time.sleep(60)  # Verificar a cada minuto


if __name__ == "__main__":
    init_db()
    run_scheduler()

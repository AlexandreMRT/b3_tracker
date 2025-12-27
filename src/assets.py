"""
Lista de ativos para rastrear: Ações B3 (Ibovespa) + Commodities + Crypto
"""

# Ações do Ibovespa com seus setores
IBOVESPA_STOCKS = {
    # Bancos e Financeiro
    "BBAS3.SA": {"name": "Banco do Brasil", "sector": "Bancário"},
    "BBDC3.SA": {"name": "Bradesco ON", "sector": "Bancário"},
    "BBDC4.SA": {"name": "Bradesco PN", "sector": "Bancário"},
    "ITUB3.SA": {"name": "Itaú Unibanco ON", "sector": "Bancário"},
    "ITUB4.SA": {"name": "Itaú Unibanco PN", "sector": "Bancário"},
    "SANB11.SA": {"name": "Santander Brasil", "sector": "Bancário"},
    "BPAC11.SA": {"name": "BTG Pactual", "sector": "Bancário"},
    "BBSE3.SA": {"name": "BB Seguridade", "sector": "Seguros"},
    "IRBR3.SA": {"name": "IRB Brasil RE", "sector": "Seguros"},
    # SULA11 merged with Rede D'Or (RDOR3) in 2022
    "B3SA3.SA": {"name": "B3", "sector": "Serviços Financeiros"},
    # CIEL3 taken private by Bradesco/BB in 2024
    
    # Holdings
    "ITSA4.SA": {"name": "Itaúsa PN", "sector": "Holding"},
    
    # Petróleo e Gás
    "PETR3.SA": {"name": "Petrobras ON", "sector": "Petróleo e Gás"},
    "PETR4.SA": {"name": "Petrobras PN", "sector": "Petróleo e Gás"},
    "PRIO3.SA": {"name": "PetroRio", "sector": "Petróleo e Gás"},
    # RRRP3 merged with PetroReconcavo (RECV3) in 2024
    "RECV3.SA": {"name": "PetroReconcavo", "sector": "Petróleo e Gás"},
    "UGPA3.SA": {"name": "Ultrapar", "sector": "Petróleo e Gás"},
    "CSAN3.SA": {"name": "Cosan", "sector": "Petróleo e Gás"},
    "VBBR3.SA": {"name": "Vibra Energia", "sector": "Petróleo e Gás"},
    
    # Mineração e Siderurgia
    "VALE3.SA": {"name": "Vale", "sector": "Mineração"},
    "CSNA3.SA": {"name": "CSN", "sector": "Siderurgia"},
    "GGBR4.SA": {"name": "Gerdau PN", "sector": "Siderurgia"},
    "GOAU4.SA": {"name": "Metalúrgica Gerdau PN", "sector": "Siderurgia"},
    "USIM5.SA": {"name": "Usiminas PNA", "sector": "Siderurgia"},
    "BRAP4.SA": {"name": "Bradespar PN", "sector": "Mineração"},
    "CMIN3.SA": {"name": "CSN Mineração", "sector": "Mineração"},
    
    # Energia Elétrica
    "ELET3.SA": {"name": "Eletrobras ON", "sector": "Energia Elétrica"},
    "ELET6.SA": {"name": "Eletrobras PNB", "sector": "Energia Elétrica"},
    "EGIE3.SA": {"name": "Engie Brasil", "sector": "Energia Elétrica"},
    "EQTL3.SA": {"name": "Equatorial", "sector": "Energia Elétrica"},
    "CPFE3.SA": {"name": "CPFL Energia", "sector": "Energia Elétrica"},
    "CMIG4.SA": {"name": "Cemig PN", "sector": "Energia Elétrica"},
    "ENGI11.SA": {"name": "Energisa", "sector": "Energia Elétrica"},
    "TAEE11.SA": {"name": "Taesa", "sector": "Energia Elétrica"},
    "CPLE3.SA": {"name": "Copel ON", "sector": "Energia Elétrica"},
    "AURE3.SA": {"name": "Auren Energia", "sector": "Energia Elétrica"},
    
    # Saneamento
    "SBSP3.SA": {"name": "Sabesp", "sector": "Saneamento"},
    
    # Telecomunicações
    "VIVT3.SA": {"name": "Telefônica Brasil", "sector": "Telecomunicações"},
    "TIMS3.SA": {"name": "TIM", "sector": "Telecomunicações"},
    "OIBR3.SA": {"name": "Oi ON", "sector": "Telecomunicações"},
    
    # Varejo
    "MGLU3.SA": {"name": "Magazine Luiza", "sector": "Varejo"},
    "LREN3.SA": {"name": "Lojas Renner", "sector": "Varejo"},
    "AMER3.SA": {"name": "Americanas", "sector": "Varejo"},
    "BHIA3.SA": {"name": "Casas Bahia", "sector": "Varejo"},  # Was VIIA3 (Via)
    "PETZ3.SA": {"name": "Petz", "sector": "Varejo"},
    "AZZA3.SA": {"name": "Azzas 2154", "sector": "Varejo"},  # Arezzo + Soma merger
    "LWSA3.SA": {"name": "Locaweb", "sector": "Tecnologia"},
    "GMAT3.SA": {"name": "Grupo Mateus", "sector": "Varejo"},  # Replaced Carrefour
    "ASAI3.SA": {"name": "Assaí", "sector": "Varejo"},
    "PCAR3.SA": {"name": "Pão de Açúcar", "sector": "Varejo"},
    
    # Alimentos e Bebidas
    "ABEV3.SA": {"name": "Ambev", "sector": "Bebidas"},
    # JBSS3, MRFG3, BRFS3 - Yahoo Finance data issues
    "BEEF3.SA": {"name": "Minerva", "sector": "Alimentos"},
    "MDIA3.SA": {"name": "M. Dias Branco", "sector": "Alimentos"},
    "SMTO3.SA": {"name": "São Martinho", "sector": "Açúcar e Álcool"},
    
    # Saúde
    "RDOR3.SA": {"name": "Rede D'Or", "sector": "Saúde"},
    "HAPV3.SA": {"name": "Hapvida", "sector": "Saúde"},
    "FLRY3.SA": {"name": "Fleury", "sector": "Saúde"},
    "RADL3.SA": {"name": "Raia Drogasil", "sector": "Saúde"},
    "HYPE3.SA": {"name": "Hypera", "sector": "Saúde"},
    
    # Construção Civil e Imobiliário
    "CYRE3.SA": {"name": "Cyrela", "sector": "Construção"},
    "EZTC3.SA": {"name": "EZTEC", "sector": "Construção"},
    "MRVE3.SA": {"name": "MRV", "sector": "Construção"},
    "MULT3.SA": {"name": "Multiplan", "sector": "Shoppings"},
    "IGTI11.SA": {"name": "Iguatemi", "sector": "Shoppings"},
    
    # Indústria
    "WEGE3.SA": {"name": "WEG", "sector": "Industrial"},
    "EMBR3.SA": {"name": "Embraer", "sector": "Aeronáutica"},
    "RAIL3.SA": {"name": "Rumo", "sector": "Logística"},
    # CCRO3 renamed to Motiva in 2024
    "ECOR3.SA": {"name": "Ecorodovias", "sector": "Concessões"},
    "RENT3.SA": {"name": "Localiza", "sector": "Locação de Veículos"},
    "MOVI3.SA": {"name": "Movida", "sector": "Locação de Veículos"},
    "SUZB3.SA": {"name": "Suzano", "sector": "Papel e Celulose"},
    "KLBN11.SA": {"name": "Klabin", "sector": "Papel e Celulose"},
    
    # Transporte e Aviação
    "AZUL4.SA": {"name": "Azul", "sector": "Aviação"},
    # GOLL4 removed - Chapter 11 bankruptcy, data unreliable
    
    # Educação
    "YDUQ3.SA": {"name": "Yduqs", "sector": "Educação"},
    "COGN3.SA": {"name": "Cogna", "sector": "Educação"},
    
    # Outros
    # NTCO3 Natura - Yahoo Finance data issues
    "TOTS3.SA": {"name": "Totvs", "sector": "Tecnologia"},
    "CVCB3.SA": {"name": "CVC", "sector": "Turismo"},
    "SLCE3.SA": {"name": "SLC Agrícola", "sector": "Agronegócio"},
}

# Commodities (preços em USD, serão convertidos para BRL)
COMMODITIES = {
    "GC=F": {"name": "Ouro", "sector": "Metal Precioso", "unit": "oz"},
    "SI=F": {"name": "Prata", "sector": "Metal Precioso", "unit": "oz"},
    "PL=F": {"name": "Platina", "sector": "Metal Precioso", "unit": "oz"},
    "PA=F": {"name": "Paládio", "sector": "Metal Precioso", "unit": "oz"},
}

# Criptomoedas
CRYPTO = {
    "BTC-USD": {"name": "Bitcoin", "sector": "Criptomoeda", "unit": "unidade"},
    "ETH-USD": {"name": "Ethereum", "sector": "Criptomoeda", "unit": "unidade"},
}

# Câmbio para conversão
CURRENCY = {
    "USDBRL=X": {"name": "Dólar/Real", "sector": "Câmbio", "unit": ""},
}

# Ações Americanas (preços em USD, serão convertidos para BRL)
US_STOCKS = {
    # Big Tech
    "AAPL": {"name": "Apple", "sector": "Tecnologia"},
    "MSFT": {"name": "Microsoft", "sector": "Tecnologia"},
    "GOOGL": {"name": "Alphabet (Google)", "sector": "Tecnologia"},
    "AMZN": {"name": "Amazon", "sector": "Tecnologia"},
    "META": {"name": "Meta (Facebook)", "sector": "Tecnologia"},
    "NVDA": {"name": "NVIDIA", "sector": "Tecnologia"},
    "TSLA": {"name": "Tesla", "sector": "Automotivo"},
    
    # Financeiro
    "JPM": {"name": "JPMorgan Chase", "sector": "Bancário"},
    "BAC": {"name": "Bank of America", "sector": "Bancário"},
    "WFC": {"name": "Wells Fargo", "sector": "Bancário"},
    "GS": {"name": "Goldman Sachs", "sector": "Bancário"},
    
    # Saúde
    "JNJ": {"name": "Johnson & Johnson", "sector": "Saúde"},
    "UNH": {"name": "UnitedHealth", "sector": "Saúde"},
    "PFE": {"name": "Pfizer", "sector": "Farmacêutico"},
    
    # Consumo
    "KO": {"name": "Coca-Cola", "sector": "Bebidas"},
    "PEP": {"name": "PepsiCo", "sector": "Bebidas"},
    "MCD": {"name": "McDonald's", "sector": "Restaurantes"},
    "WMT": {"name": "Walmart", "sector": "Varejo"},
    
    # Energia
    "XOM": {"name": "Exxon Mobil", "sector": "Petróleo e Gás"},
    "CVX": {"name": "Chevron", "sector": "Petróleo e Gás"},
}

def get_all_assets():
    """Retorna todos os ativos para rastrear"""
    all_assets = {}
    all_assets.update(IBOVESPA_STOCKS)
    all_assets.update(US_STOCKS)
    all_assets.update(COMMODITIES)
    all_assets.update(CRYPTO)
    all_assets.update(CURRENCY)
    return all_assets

def get_asset_info(ticker):
    """Retorna informações de um ativo específico"""
    all_assets = get_all_assets()
    return all_assets.get(ticker, {"name": "Desconhecido", "sector": "Outro"})

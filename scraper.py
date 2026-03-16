import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import datetime
from supabase import create_client
from collections import defaultdict

# 🟢 INIZIALIZZAZIONE SUPABASE
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🛡️ ARMATURA DI RETE
session = requests.Session()
retries = Retry(total=5, backoff_factor=2, status_forcelist=[ 429, 500, 502, 503, 504 ])
session.mount('https://', HTTPAdapter(max_retries=retries))
session.mount('http://', HTTPAdapter(max_retries=retries))
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'})

BASE_URL_AJAX = "https://comitati.fisi.org/wp-admin/admin-ajax.php"

COMITATI_FISI = {
    'trentino': 'Trentino (TN)', 'alto-adige': 'Alto Adige (AA)', 'veneto': 'Veneto (VE)',
    'alpi-centrali': 'Alpi Centrali (AC)', 'alpi-occidentali': 'Alpi Occidentali (AOC)',
    'friuli-venezia-giulia': 'Friuli Venezia Giulia (FVG)', 'appennino-emiliano': 'Appennino Emiliano (CAE)',
    'appennino-toscano': 'Appennino Toscano (CAT)', 'abruzzo': 'Abruzzo (CAB)',
    'lazio-sardegna': 'Lazio e Sardegna (CLS)', 'ligure': 'Ligure (LIG)',
    'umbro-marchigiano': 'Umbro Marchigiano (CUM)', 'campano': 'Campano (CAM)',
    'calabro-lucano': 'Calabro Lucano (CAL)', 'pugliese': 'Pugliese (PUG)',
    'siculo': 'Siculo (SIC)', 'asiva': 'Valdostano (ASIVA)'
}

# 🎯 DECODER DNA ESTESO (Risolve il problema di Liguria e Val d'Aosta)
MAPPA_SIGLE = {
    'AA': 'Alto Adige (AA)', 'AC': 'Alpi Centrali (AC)', 'AOC': 'Alpi Occidentali (AOC)',
    'ASIVA': 'Valdostano (ASIVA)', 'VA': 'Valdostano (ASIVA)', 'AO': 'Valdostano (ASIVA)', 'VDA': 'Valdostano (ASIVA)',
    'CAB': 'Abruzzo (CAB)', 'CAE': 'Appennino Emiliano (CAE)', 'CAL': 'Calabro Lucano (CAL)', 
    'CAM': 'Campano (CAM)', 'MOL': 'Campano (CAM)', 'CAT': 'Appennino Toscano (CAT)', 
    'CLS': 'Lazio e Sardegna (CLS)', 'CUM': 'Umbro Marchigiano (CUM)', 
    'FVG': 'Friuli Venezia Giulia (FVG)', 'LI': 'Ligure (LIG)', 'LIG': 'Ligure (LIG)', 
    'PUG': 'Pugliese (PUG)', 'SIC': 'Siculo (SIC)', 'TN': 'Trentino (TN)', 
    'VE': 'Veneto (VE)', 'GM': 'Gruppi Militari (GM)'
}

def estrai_comitato_con_ranking(item):
    """Estrae la pura verità dai dati, senza fidarsi di chi ce li ha mandati"""
    livello = str(item.get("livello", "")).upper()
    if "WORLD" in livello or "OPA" in livello or "INTERNAZIONAL" in livello:
        return "Internazionale/FIS", 0

    c1 = str(item.get("codiceComitato", "")).strip().upper()
    if c1 in MAPPA_SIGLE: return MAPPA_SIGLE[c1], 1

    c2 = str(item.get("comitato", "")).strip().upper()
    if c2 in MAPPA_SIGLE: return MAPPA_SIGLE[c2], 2

    soc = str(item.get("codiceSocieta", "")).strip().upper()
    for sigla in sorted(MAPPA_SIGLE.keys(), key=len, reverse=True):
        if soc.startswith(sigla): return MAPPA_SIGLE[sigla], 3

    return "Sconosciuto", 4

# =====================================================================
# 🗓️ FASE 1: DOWNLOAD GLOBALE E TRIBUNALE MATEMATICO
# =====================================================================
def spider_calendari_nazionale():
    print("--- 🚀 FASE 1: DOWNLOAD MASSIVO E RISOLUZIONE TRAMITE TRIBUNALE ---", flush=True)
    
    anno_corrente = datetime.datetime.now().year
    mese_corrente = datetime.datetime.now().month
    anno_massimo = anno_corrente + 1 if mese_corrente >= 6 else anno_corrente
    stagioni_da_scaricare = list(range(2020, anno_massimo + 1))
    
    LISTA_NERA = ["ALPINO", "SLALOM", "GIGANTE", "GS", "SUPER G", "DISCESA", "BIATHLON", "SNOWBOARD", "SKICROSS", "FREESTYLE", "ERBA", "SKELETON", "BOB", "JUMP", "SALTO"]
    
    # Memorie dell'Algoritmo
    gare_uniche_dati = {}              # Dati completi della gara
    gare_best_score = {}               # Miglior Ranking ottenuto
    gare_best_comitato = {}            # Comitato vincitore (se Score <= 3)
    reclamazioni_rank4 = defaultdict(list) # Elenco dei portali che reclamano una gara Rank 4
    portale_yield = defaultdict(int)       # Conta quante gare vomita un server per scovare i bugiardi
    
    for slug_sito, portale_nome in COMITATI_FISI.items():
        print(f"\n🌍 Interrogo il server: {portale_nome}...", flush=True)
        
        for anno in stagioni_da_scaricare:
            offset = 0
            limit = 500
            
            while True:
                params = {
                    "action": "competizioni_get_all", "idStagione": str(anno),
                    "url": f"https://comitati.fisi.org/{slug_sito}/calendario/", 
                    "limit": limit, "offset": offset
                }
                
                try:
                    r = session.get(BASE_URL_AJAX, params=params, timeout=15)
                    data = r.json()
                    
                    if not data or not isinstance(data, list) or len(data) == 0: break 
                        
                    for item in data:
                        id_comp = str(item.get("idCompetizione"))
                        disciplina = str(item.get("disciplina", "")).upper()
                        nome_gara = str(item.get("nome", "")).upper()
                        
                        is_fondo = any(k in disciplina for k in ["FONDO", "LANGLAUF", "NORDICO", "XC"]) or \
                                   any(k in nome_gara for k in ["FONDO", "LANGLAUF", "NORDICO", "CROSS COUNTRY", "XC"])
                        is_proibita = any(k in nome_gara for k in LISTA_NERA) or any(k in disciplina for k in LISTA_NERA)
                        
                        if is_fondo and not is_proibita:
                            # 1. Contiamo la gara per misurare l'affidabilità del server
                            portale_yield[portale_nome] += 1
                            gare_uniche_dati[id_comp] = item
                            
                            # 2. Leggiamo il DNA
                            comitato_dna, score = estrai_comitato_con_ranking(item)
                            
                            # 3. Logica Infallibile
                            if score <= 3:
                                # È una prova inconfutabile, la salviamo subito (o sovrascriviamo se è meglio)
                                if id_comp not in gare_best_score or score < gare_best_score[id_comp]:
                                    gare_best_score[id_comp] = score
                                    gare_best_comitato[id_comp] = comitato_dna
                            else:
                                # Non ha DNA! Mettiamola tra le cause in attesa di Tribunale
                                if portale_nome not in reclamazioni_rank4[id_comp]:
                                    reclamazioni_rank4[id_comp].append(portale_nome)
                                
                    if len(data) < limit: break
                    offset += limit
                    
                except Exception:
                    break 
            time.sleep(0.1)

    print("\n⚖️ DOWNLOAD COMPLETATO. IL TRIBUNALE APRE LA SEDUTA PER RISOLVERE I CONFLITTI...", flush=True)
    
    lista_finale_supabase = []
    statistiche = {0:0, 1:0, 2:0, 3:0, 4:0}
    
    for id_comp, item_grezzo in gare_uniche_dati.items():
        # Se abbiamo una prova certa (Score 0, 1, 2, 3), vince subito
        if id_comp in gare_best_score and gare_best_score[id_comp] <= 3:
            comitato_vincitore = gare_best_comitato[id_comp]
            score_finale = gare_best_score[id_comp]
        else:
            # È UN RANK 4 (Nessun DNA). 
            # Il Tribunale assegna la gara al portale che ha fatto meno "rumore" (calendario più piccolo = più onesto)
            claims = reclamazioni_rank4[id_comp]
            comitato_vincitore = min(claims, key=lambda p: portale_yield[p])
            score_finale = 4
            
        statistiche[score_finale] += 1
        
        lista_finale_supabase.append({
            "id_gara_fisi": id_comp, 
            "gara_nome": item_grezzo.get("nome", "Gara Senza Nome"),
            "luogo": item_grezzo.get("comune", "N/D"), 
            "data_gara": item_grezzo.get("dataInizio", "N/D"), 
            "comitato": comitato_vincitore
        })

    # Salvataggio
    if lista_finale_supabase:
        for i in range(0, len(lista_finale_supabase), 1000):
            pacchetto = lista_finale_supabase[i:i+1000]
            supabase.table("Gare").upsert(pacchetto).execute()
            
        print(f"\n✅ TRIONFO TOTALE: {len(lista_finale_supabase)} gare salvate e blindate!")
        print(f"📊 REPORT AFFIDABILITÀ ASSEGNAZIONI:")
        print(f"   Rank 0 (Internazionali):     {statistiche[0]}")
        print(f"   Rank 1 (Codice Ufficiale):   {statistiche[1]}")
        print(f"   Rank 2 (Nome Ufficiale):     {statistiche[2]}")
        print(f"   Rank 3 (Prefisso Società):   {statistiche[3]}")
        print(f"   Rank 4 (Tribunale Anti-Bug): {statistiche[4]}")
    else:
        print("\n❌ Nessuna gara salvata.", flush=True)

if __name__ == "__main__":
    spider_calendari_nazionale()
    # spider_atleti_master() <-- Togli il commento se i dati sul DB sono perfetti

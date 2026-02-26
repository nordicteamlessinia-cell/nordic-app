def scarica_test():
    comp_id = "56789" 
    url_base = f"https://comitati.fisi.org/veneto/competizione/?idComp={comp_id}&d="
    
    print(f"--- Analisi Competizione: {url_base} ---")
    res = requests.get(url_base)
    soup = BeautifulSoup(res.text, 'html.parser')

    # Cerchiamo tutti i link che portano a una singola gara
    links = [l['href'] for l in soup.find_all('a', href=True) if 'idGara=' in l['href']]
    links = list(set(links)) # Rimuove i duplicati

    if not links:
        print("⚠ ATTENZIONE: Nessun link gara (idGara) trovato. Verificare l'ID competizione.")
        return

    for g_url in links:
        # Assicuriamoci che l'URL sia completo
        full_url = g_url if g_url.startswith('http') else f"https://comitati.fisi.org/veneto/{g_url}"
        print(f"-> Entro nella gara: {full_url}")
        
        res_g = requests.get(full_url)
        g_soup = BeautifulSoup(res_g.text, 'html.parser')
        
        # Cerchiamo TUTTE le tabelle presenti
        tables = g_soup.find_all('table')
        if not tables:
            print(f"   ❌ Nessuna tabella trovata in questa pagina.")
            continue

        for table in tables:
            rows = table.find_all('tr')
            batch = []
            print(f"   Trovate {len(rows)} righe. Analizzo...")

            for row in rows:
                cols = row.find_all(['td', 'th'])
                # Puliamo i dati da spazi e caratteri strani
                data = [c.get_text(strip=True) for c in cols]
                
                # Una riga valida di solito ha la posizione come primo elemento (numero)
                if len(data) >= 5 and data[0].isdigit():
                    batch.append({
                        "posizione": int(data[0]),
                        "atleta_nome": data[2], # Di solito la terza colonna
                        "societa": data[4],     # Di solito la quinta colonna
                        "id_gara_fisi": full_url.split('idGara=')[1].split('&')[0],
                        "gara_nome": g_soup.find('h1').text.strip() if g_soup.find('h1') else "Gara"
                    })

            if batch:
                print(f"   ✅ Trovati {len(batch)} atleti. Invio a Supabase...")
                try:
                    supabase.table("gare").upsert(batch).execute()
                    print(f"   🚀 Inserimento completato per questa tabella.")
                except Exception as e:
                    print(f"   🔥 Errore Supabase: {e}")

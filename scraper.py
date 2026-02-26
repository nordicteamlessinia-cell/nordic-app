for g_url in links:
        # Assicuriamoci che l'URL sia completo
        full_url = g_url if g_url.startswith('http') else f"https://comitati.fisi.org/veneto/{g_url}"
        print(f"--- 4. Analizzo gara: {full_url}")
        
        res_g = requests.get(full_url, headers=HEADERS)
        g_soup = BeautifulSoup(res_g.text, 'html.parser')
        
        # Cerchiamo i dati non solo in <table>, ma in qualsiasi riga <tr>
        rows = g_soup.find_all('tr')
        
        if not rows:
            print("   ❌ Nessuna riga (tr) trovata. Provo a cercare i div dei risultati.")
            # Alcune versioni del sito usano dei div con classe specifica
            rows = g_soup.find_all('div', class_='row') 

        atleti = []
        for row in rows:
            cols = row.find_all(['td', 'div'])
            # Puliamo i testi
            data = [c.get_text(strip=True) for c in cols]
            
            # Una riga valida di solito ha: POS | PETT | ATLETA | ANNO | SOCIETÀ
            # Cerchiamo righe che abbiano almeno 5 colonne e dove la prima sia un numero (la posizione)
            if len(data) >= 5 and data[0].isdigit():
                try:
                    atleti.append({
                        "atleta_nome": data[2],
                        "societa": data[4],
                        "posizione": int(data[0]),
                        "id_gara_fisi": full_url.split('idGara=')[1].split('&')[0],
                        "gara_nome": g_soup.find('h1').text.strip() if g_soup.find('h1') else "Gara Veneto"
                    })
                except Exception as e:
                    continue
        
        if atleti:
            print(f"   ✅ Trovati {len(atleti)} atleti! Invio a Supabase...")
            supabase.table("gare").upsert(atleti).execute()

🛡️ WAR-SENTINEL — Stock Scanner per Periodo di Guerra/Petrolio
Autore: BESIO MAURO — 10/01/1956
Repository: mauroileana/WAR-SENTINEL
Ultimo aggiornamento: Marzo 2026
📋 Descrizione
WAR-SENTINEL è un sistema di scansione algoritmica dei mercati finanziari progettato specificamente per il contesto geopolitico attuale — un periodo caratterizzato da conflitti armati e alta volatilità del petrolio.
Il sistema analizza i titoli dei principali indici mondiali e produce una classifica finale TOP 6 con rating di investimento, tenendo conto sia dei segnali tecnici che del contesto macro (Brent Crude, VIX, EUR/USD, DXY).
🗂️ Script disponibili
File
Mercato
Indice
Titoli
Versione
WAR-SENTINEL_ITALIA_FTSE_MIB_V4.py
🇮🇹 Italia
FTSE MIB
36
Attiva
WAR-SENTINEL_EUROPA_STOXX_V3.py
🌍 Europa
EURO STOXX 50 + STOXX 600
~57
Attiva
WAR-SENTINEL_USA_V2.py
🇺🇸 USA
Dow Jones 30 + Nasdaq Top 30
~54
Attiva
WAR-SENTINEL_ITALIA_FTSE_MIB_V2.py
🇮🇹 Italia
FTSE MIB
36
Archivio
WAR-SENTINEL_ITALIA_FTSE_MIB_V3.py
🇮🇹 Italia
FTSE MIB
36
Archivio
WAR-SENTINEL_EUROPA_STOXX_V1.py
🌍 Europa
EURO STOXX 50
~57
Archivio
WAR-SENTINEL_EUROPA_STOXX_V2.py
🌍 Europa
EURO STOXX 50
~57
Archivio
WAR-SENTINEL_USA_V1.py
🇺🇸 USA
Dow Jones 30 + Nasdaq Top 30
~54
Archivio
⚙️ Installazione
pip install yfinance pandas
python WAR-SENTINEL_ITALIA_FTSE_MIB_V4.py
📊 Parametri e Indicatori
Tutti e tre gli script attivi condividono la stessa architettura. I parametri sono calibrati diversamente per ciascun mercato.
Indicatori calcolati per ogni titolo
Parametro
Descrizione
T5gg
Trend % ultimi 5 giorni
T30gg
Trend % ultimi 30 giorni (struttura)
VOL/AVG
Volume oggi / volume medio 30gg
RSI
Relative Strength Index a 14 periodi
D.MAX
Distanza % dal massimo 30gg (overextension)
SUP
Distanza % dal minimo 30gg (supporto)
DIV
Divergenza RSI 10gg (↗ RIALZ / ↘ RIBAS / · NEUTR)
RISCHIO
Semaforo entrata 🟢 BASSO / 🟡 MEDIO / 🔴 ALTO
SCORE
Punteggio composito 0–100
RATING
Giudizio finale
Indicatori macro
Script
Indicatori macro
🇮🇹 Italia
Brent Crude (BZ=F)
🌍 Europa
Brent + EUR/USD + STOXX 50 benchmark
🇺🇸 USA
Brent + VIX + DXY + S&P 500 benchmark
🧮 Sistema di Score (0–100)
Pesi per mercato
Componente
🇮🇹 Italia
🌍 Europa
🇺🇸 USA
Trend 5gg
35 pt
30 pt
30 pt
Trend 30gg
20 pt
20 pt
25 pt
Volumi
15 pt
20 pt
15 pt
Stabilità
15 pt
15 pt
15 pt
War-Oil bonus
10 pt
10 pt
10 pt
EUR/USD bonus
—
5 pt
—
Totale base
95 pt
100 pt
95 pt
Modificatori
Modificatore
Punti
RSI > 70 (ipercomprato)
-5 pt
RSI < 30 (ipervenduto)
+5 pt
Rischio MEDIO (🟡)
-8 pt
Rischio ALTO (🔴)
-18 pt
Sul supporto (SUP ≤ 4%)
+4 pt
Divergenza rialzista (↗)
+4 pt
SUP + DIV rialzista insieme
+8 pt
Divergenza ribassista (↘)
-5 pt
🎯 Rating di investimento
Rating
Score
Trend 5gg
Significato
🔥 STRONG BUY
≥ 75
> 5%
Fortissimo segnale d'acquisto
💚 BUY
≥ 60
> 2%
Segnale d'acquisto
📈 ACCUMULATE
≥ 45
≥ 0%
Accumulare progressivamente
🟡 HOLD
≥ 30
qualsiasi
Mantenere, non comprare
🔻 AVOID
< 30
qualsiasi
Evitare
🏆 TOP 6 con Cap Settoriale
La tabella finale TOP 6 applica un limite massimo per settore per garantire diversificazione:
Settore
🇮🇹 Italia
🌍 Europa
🇺🇸 USA
Energia/Petrolio
max 3
max 3
max 3
Difesa
max 2
max 2
max 2
Altri settori
illimitato
illimitato
illimitato
Questo evita che il TOP 6 sia dominato da titoli dello stesso settore anche quando tutti i titoli petroliferi sono in rialzo contemporaneamente.
📈 Divergenza RSI — Come interpretarla
La divergenza confronta il movimento del prezzo con il movimento dell'RSI negli ultimi 10 giorni:
↗ RIALZISTA — Il prezzo scende ma l'RSI sale
→ La forza ribassista si sta esaurendo → potenziale rimbalzo
→ Particolarmente utile su titoli che hanno già corretto molto
↘ RIBASSISTA — Il prezzo sale ma l'RSI scende
→ Il rialzo perde momentum → attenzione, potrebbe invertire
→ Segnale di cautela anche su titoli con trend positivo
· NEUTRALE — Nessuna divergenza significativa
🛢️ Contesto Guerra/Petrolio
I titoli appartenenti a settori sensibili al contesto geopolitico sono identificati con il simbolo ⚑ e ricevono un bonus di +10pt nello score solo se il Brent Crude è in trend positivo (>+1% in 10 giorni).
Settori WAR-OIL per mercato
🇮🇹 Italia: ENI, Tenaris, Saipem, Maire Tecnimont, ERG, Leonardo, Iveco Group, Prysmian, Snam, Terna
🌍 Europa: TotalEnergies, Shell, BP, Equinor, Repsol, Rheinmetall, BAE Systems, Airbus, Thales, Safran, Rolls-Royce, Hensoldt, ArcelorMittal, ASML, ABB
🇺🇸 USA: Chevron, ExxonMobil, OXY, ConocoPhillips, SLB, Boeing, Honeywell, Raytheon, Lockheed Martin, Northrop Grumman, General Dynamics, Nvidia, Cisco, Caterpillar, GE Aerospace
⚠️ Calibrazione soglie per mercato
Parametro
🇮🇹 Italia
🌍 Europa
🇺🇸 USA
Motivazione
Vol soglia
1.3x
1.5x
2.0x
Liquidità crescente
Accel soglia
1.8
1.8
1.6
USA reagisce più velocemente
VIX alert
—
—
25
Solo USA
EUR/USD
—
-1%
—
Solo Europa
📌 Come usarlo in una nuova chat
Per trovare questi script in qualsiasi chat futura:
GitHub: https://github.com/mauroileana/WAR-SENTINEL
Autore: BESIO MAURO - 10/01/1956
⚠️ Disclaimer
Questo strumento è a scopo puramente informativo e didattico.
Non costituisce consulenza finanziaria.
Ogni decisione di investimento è responsabilità esclusiva dell'utente.
I mercati finanziari comportano rischi significativi di perdita del capitale.

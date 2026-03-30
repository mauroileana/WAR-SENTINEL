import yfinance as yf
import pandas as pd
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

# ──────────────────────────────────────────────────────────────────
# CONFIGURAZIONE
# ──────────────────────────────────────────────────────────────────
COSTRUTTORE          = "BESIO MAURO-10-01-1956"
OIL_TICKER           = "BZ=F"
VIX_TICKER           = "^VIX"
DXY_TICKER           = "DX-Y.NYB"
SP500_TICKER         = "^GSPC"

# Soglie — calibrate per mercato USA (più liquido e reattivo)
VOL_SOGLIA_RATIO     = 2.0    # USA altissima liquidità → soglia alta (IT=1.3, EU=1.5)
STAB_SOGLIA          = 1.3
TREND_MIN_RESILIENTE = -0.04
OIL_TREND_SOGLIA     = 0.01
TOP_N                = 6

# Soglie anti-rischio USA
RSI_IPERCOMPRATO     = 70
RSI_IPERVENDUTO      = 30
ACCEL_SOGLIA         = 1.6    # USA reagisce più velocemente → soglia più bassa
VIX_ALERT            = 25     # VIX > 25 → mercato nervoso → penalità extra

# Cap settoriale TOP6
MAX_ENERGIA_TOP6     = 3
MAX_DIFESA_TOP6      = 2

# ──────────────────────────────────────────────────────────────────
# PANIERE USA — Dow Jones 30 + Nasdaq Top 30
# ──────────────────────────────────────────────────────────────────
USA = {
    # ══ DOW JONES 30 ════════════════════════════════════════════

    # ── Energia & Petrolio ───────────────────────────────────────
    "CVX":   "Chevron",              # Petrolio integrato
    "XOM":   "ExxonMobil",          # Petrolio integrato (S&P500/DJ)

    # ── Difesa & Aerospazio ──────────────────────────────────────
    "BA":    "Boeing",              # Aerospazio/difesa ★
    "HON":   "Honeywell",           # Conglomerato difesa/industriale ★
    "RTX":   "Raytheon",            # Difesa/missili ★ (S&P500)
    "LMT":   "Lockheed Martin",     # Difesa pesante ★ (S&P500)
    "NOC":   "Northrop Grumman",    # Difesa/spazio ★ (S&P500)
    "GD":    "General Dynamics",    # Difesa/veicoli ★ (S&P500)

    # ── Industria & Infrastrutture ───────────────────────────────
    "CAT":   "Caterpillar",         # Macchine movimento terra
    "MMM":   "3M",                  # Conglomerato industriale
    "GE":    "GE Aerospace",        # Motori aerei/industriale
    "SHW":   "Sherwin-Williams",    # Specialty chemicals

    # ── Banche & Finanza ─────────────────────────────────────────
    "JPM":   "JPMorgan Chase",      # Banca globale
    "GS":    "Goldman Sachs",       # Investment banking
    "AXP":   "American Express",    # Finanza/pagamenti
    "V":     "Visa",                # Pagamenti digitali
    "TRV":   "Travelers",           # Assicurazioni

    # ── Healthcare & Farmaceutica ────────────────────────────────
    "JNJ":   "Johnson & Johnson",   # Farmaceutica/consumer
    "MRK":   "Merck",               # Farmaceutica
    "UNH":   "UnitedHealth",        # Healthcare gestito
    "AMGN":  "Amgen",               # Biotech

    # ── Consumer & Retail ────────────────────────────────────────
    "WMT":   "Walmart",             # Grande distribuzione
    "MCD":   "McDonald's",          # Fast food globale
    "HD":    "Home Depot",          # Home improvement
    "KO":    "Coca-Cola",           # Bevande
    "PG":    "Procter & Gamble",    # Consumer goods
    "NKE":   "Nike",                # Abbigliamento sportivo
    "DIS":   "Disney",              # Entertainment/media

    # ── Telecomunicazioni ────────────────────────────────────────
    "VZ":    "Verizon",             # Telecomunicazioni

    # ══ NASDAQ TOP 30 (per capitalizzazione) ════════════════════

    # ── Big Tech ─────────────────────────────────────────────────
    "AAPL":  "Apple",               # #1 per market cap
    "MSFT":  "Microsoft",           # Cloud/AI/software
    "NVDA":  "Nvidia",              # Chip AI ★ guerra tech
    "GOOGL": "Alphabet",            # Search/cloud/AI
    "META":  "Meta",                # Social/AI
    "AMZN":  "Amazon",              # E-commerce/cloud
    "TSLA":  "Tesla",               # EV/energia
    "AVGO":  "Broadcom",            # Chip/reti
    "COST":  "Costco",              # Retail membership
    "CSCO":  "Cisco",               # Networking/sicurezza ★

    # ── Chip & Semiconduttori ─────────────────────────────────────
    "AMD":   "AMD",                 # Chip CPU/GPU
    "QCOM":  "Qualcomm",            # Chip mobile/IoT
    "INTC":  "Intel",               # Chip legacy/data center
    "MU":    "Micron",              # Memoria/DRAM

    # ── Biotech & Healthcare Nasdaq ──────────────────────────────
    "GILD":  "Gilead Sciences",     # Antivirali/biotech
    "REGN":  "Regeneron",           # Biotech specialty
    "VRTX":  "Vertex Pharma",       # Biotech raro

    # ── Energia & Utility Nasdaq ──────────────────────────────────
    "OXY":   "Occidental Petroleum",# Petrolio shale ★
    "COP":   "ConocoPhillips",      # Esplorazione petrolio ★
    "SLB":   "SLB (Schlumberger)",  # Servizi petroliferi ★

    # ── Finanza Nasdaq ───────────────────────────────────────────
    "PYPL":  "PayPal",              # Pagamenti digitali
    "ADBE":  "Adobe",               # Software creatività
    "CRM":   "Salesforce",          # CRM/cloud
    "IBM":   "IBM",                 # IT enterprise/AI
    "NFLX":  "Netflix",             # Streaming
}

# Classificazione settori per cap
SETTORI_ENERGIA = {
    "CVX","XOM","OXY","COP","SLB"
}
SETTORI_DIFESA = {
    "BA","HON","RTX","LMT","NOC","GD"
}
SETTORI_WAR_OIL = SETTORI_ENERGIA | SETTORI_DIFESA | {"NVDA","CSCO","CAT","GE"}

def get_settore(ticker):
    if ticker in SETTORI_ENERGIA: return "energia"
    if ticker in SETTORI_DIFESA:  return "difesa"
    return "altro"

# ──────────────────────────────────────────────────────────────────
# FUNZIONI INDICATORI
# ──────────────────────────────────────────────────────────────────
def calcola_rsi(close, periodi=14):
    try:
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(window=periodi, min_periods=periodi).mean()
        loss  = (-delta.clip(upper=0)).rolling(window=periodi, min_periods=periodi).mean()
        rs    = gain / loss.replace(0, 1e-9)
        rsi   = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])
    except:
        return 50.0

def calcola_rischio_entrata(rsi, dist_max, trend_3d, trend_5d, vix_alto):
    """
    USA: aggiunge il VIX come fattore di rischio extra.
    """
    punti = 0

    # RSI
    if rsi > RSI_IPERCOMPRATO:
        punti += 2
    elif rsi < RSI_IPERVENDUTO:
        punti -= 1

    # Distanza dal massimo
    if dist_max > -0.03:
        punti += 2
    elif dist_max > -0.08:
        punti += 1

    # Accelerazione (parabola) — soglia più bassa per USA
    if trend_5d != 0 and abs(trend_3d / trend_5d) > ACCEL_SOGLIA and trend_3d > 0:
        punti += 2

    # VIX alto → mercato nervoso → rischio aggiuntivo
    if vix_alto:
        punti += 1

    if punti >= 4:
        return "🔴 ALTO",  -18
    elif punti >= 2:
        return "🟡 MEDIO", -8
    else:
        return "🟢 BASSO",  0

# ──────────────────────────────────────────────────────────────────
# FUNZIONE SCORE  (0 – 100)
# ──────────────────────────────────────────────────────────────────
def calcola_score(trend_5d, trend_30d, vol_ratio, is_stabile,
                  is_war_oil, oil_favorevole, rsi, penalita_rischio,
                  vix_alto):
    """
    Pesi USA:
      trend_5d       → 30 pt  (USA reagisce veloce, meno peso a breve)
      trend_30d      → 25 pt  (struttura più importante in USA)
      volumi         → 15 pt  (volumi enormi → soglia alta → peso ridotto)
      stabilità      → 15 pt
      war-oil bonus  → 10 pt  (solo se oil favorevole)
      RSI            → ±5 pt
      penalità       → 0/-8/-18
    """
    score = 0.0

    # Trend 5gg (max 30)
    if trend_5d >= 0.08:    score += 30
    elif trend_5d >= 0.05:  score += 24
    elif trend_5d >= 0.03:  score += 17
    elif trend_5d >= 0.01:  score += 10
    elif trend_5d >= 0:     score += 5
    else:                   score += max(0, 5 + trend_5d * 80)

    # Trend 30gg (max 25) — più peso in USA
    if trend_30d >= 0.15:    score += 25
    elif trend_30d >= 0.05:  score += 18
    elif trend_30d >= 0:     score += 12
    elif trend_30d >= -0.05: score += 6
    else:                    score += 0

    # Volumi (max 15)
    if vol_ratio >= 3.0:    score += 15
    elif vol_ratio >= 2.5:  score += 12
    elif vol_ratio >= 2.0:  score += 9
    elif vol_ratio >= 1.5:  score += 5
    else:                   score += 2

    # Stabilità (max 15)
    if is_stabile: score += 15

    # Bonus WAR-OIL (max 10)
    if is_war_oil and oil_favorevole: score += 10

    # RSI (±5)
    if rsi < RSI_IPERVENDUTO:    score += 5
    elif rsi > RSI_IPERCOMPRATO: score -= 5

    # Penalità rischio
    score += penalita_rischio

    return round(max(0, min(score, 100)), 1)


def score_to_rating(score, trend_5d):
    if score >= 75 and trend_5d > 0.05:
        return "🔥 STRONG BUY"
    elif score >= 60 and trend_5d > 0.02:
        return "💚 BUY"
    elif score >= 45 and trend_5d >= 0:
        return "📈 ACCUMULATE"
    elif score >= 30:
        return "🟡 HOLD"
    else:
        return "🔻 AVOID"

# ──────────────────────────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────────────────────────
print()
print("╔══════════════════════════════════════════════════════════════════╗")
print(f"║   🇺🇸  WAR-SENTINEL_USA_V1                                      ║")
print(f"║   📅  {datetime.now().strftime('%d/%m/%Y  %H:%M')}                                         ║")
print(f"║   👤  {COSTRUTTORE}                         ║")
print("╚══════════════════════════════════════════════════════════════════╝")
print("   v1: RSI + VIX + DXY + Overextension + Cap Settoriale TOP6")

# ──────────────────────────────────────────────────────────────────
# STEP 1 — MACRO CONTEXT USA
# ──────────────────────────────────────────────────────────────────
print("\n📡 Scarico indicatori macro USA...")

# Brent
try:
    oil_data = yf.download(OIL_TICKER, period="10d", progress=False)['Close']
    if isinstance(oil_data, pd.DataFrame): oil_data = oil_data.iloc[:, 0]
    oil_data = oil_data.dropna()
    oil_fine       = float(oil_data.iloc[-1])
    oil_trend      = (oil_fine - float(oil_data.iloc[0])) / float(oil_data.iloc[0])
    oil_favorevole = oil_trend > OIL_TREND_SOGLIA
    icona = "🟢" if oil_trend > 0.02 else ("🟡" if oil_trend > 0 else "🔴")
    print(f"   {icona}  Brent     : {oil_fine:.2f} USD  |  Trend 10gg: {oil_trend:+.2%}  {'✅' if oil_favorevole else '⛔'}")
except:
    oil_trend = 0.0; oil_favorevole = False; oil_fine = 0.0
    print("   ⚠️  Brent non disponibile")

# VIX
try:
    vix_data = yf.download(VIX_TICKER, period="5d", progress=False)['Close']
    if isinstance(vix_data, pd.DataFrame): vix_data = vix_data.iloc[:, 0]
    vix_fine = float(vix_data.dropna().iloc[-1])
    vix_alto = vix_fine > VIX_ALERT
    icona = "🔴" if vix_fine > 30 else ("🟡" if vix_fine > VIX_ALERT else "🟢")
    print(f"   {icona}  VIX       : {vix_fine:.1f}  {'⚠️ MERCATO NERVOSO' if vix_alto else '✅ Mercato stabile'}")
except:
    vix_fine = 20.0; vix_alto = False
    print("   ⚠️  VIX non disponibile")

# DXY
try:
    dxy_data = yf.download(DXY_TICKER, period="10d", progress=False)['Close']
    if isinstance(dxy_data, pd.DataFrame): dxy_data = dxy_data.iloc[:, 0]
    dxy_data = dxy_data.dropna()
    dxy_fine  = float(dxy_data.iloc[-1])
    dxy_trend = (dxy_fine - float(dxy_data.iloc[0])) / float(dxy_data.iloc[0])
    icona = "🟢" if dxy_trend > 0.005 else ("🟡" if dxy_trend > -0.005 else "🔴")
    print(f"   {icona}  DXY       : {dxy_fine:.2f}  |  Trend 10gg: {dxy_trend:+.2%}")
except:
    dxy_fine = 0.0; dxy_trend = 0.0
    print("   ⚠️  DXY non disponibile")

# S&P 500
try:
    sp_data = yf.download(SP500_TICKER, period="10d", progress=False)['Close']
    if isinstance(sp_data, pd.DataFrame): sp_data = sp_data.iloc[:, 0]
    sp_data = sp_data.dropna()
    sp_fine  = float(sp_data.iloc[-1])
    sp_trend = (sp_fine - float(sp_data.iloc[0])) / float(sp_data.iloc[0])
    icona = "🟢" if sp_trend > 0.01 else ("🟡" if sp_trend > 0 else "🔴")
    print(f"   {icona}  S&P 500   : {sp_fine:.2f}  |  Trend 10gg: {sp_trend:+.2%}")
except:
    sp_fine = 0.0; sp_trend = 0.0
    print("   ⚠️  S&P500 non disponibile")

stato_oil = "FAVOREVOLE ✅" if oil_favorevole else "NEUTRO/NEG ⛔"
stato_vix = "NERVOSO ⚠️" if vix_alto else "STABILE ✅"
print(f"\n   Oil: {stato_oil}  |  VIX: {stato_vix}")

# ──────────────────────────────────────────────────────────────────
# STEP 2 — SCANSIONE
# ──────────────────────────────────────────────────────────────────
print(f"\n🔍 Scansione {len(USA)} titoli USA in corso...\n")

risultati = []
errori    = []

for ticker, nome in USA.items():
    try:
        raw = yf.download(ticker, period="60d", progress=False, auto_adjust=True)
        if raw.empty: errori.append(ticker); continue

        close  = raw['Close']
        volume = raw['Volume']
        if isinstance(close,  pd.DataFrame): close  = close.iloc[:, 0]
        if isinstance(volume, pd.DataFrame): volume = volume.iloc[:, 0]
        close  = close.dropna()
        volume = volume.dropna()
        if len(close) < 20: errori.append(ticker); continue

        # Indicatori base
        p_fine    = float(close.iloc[-1])
        p_5gg     = float(close.iloc[-6])
        p_3gg     = float(close.iloc[-4])
        p_inizio  = float(close.tail(30).iloc[0])
        trend_5d  = (p_fine - p_5gg)    / p_5gg
        trend_3d  = (p_fine - p_3gg)    / p_3gg
        trend_30d = (p_fine - p_inizio) / p_inizio

        std_5d    = float(close.tail(5).std())
        std_30d   = float(close.tail(30).std())
        is_stabile = std_5d < (std_30d * STAB_SOGLIA)

        vol_oggi  = float(volume.iloc[-1])
        vol_medio = float(volume.tail(30).mean())
        vol_ratio = vol_oggi / vol_medio if vol_medio > 0 else 0

        # Nuovi indicatori
        rsi      = calcola_rsi(close, 14)
        max_30d  = float(close.tail(30).max())
        dist_max = (p_fine - max_30d) / max_30d

        rischio_str, penalita = calcola_rischio_entrata(
            rsi, dist_max, trend_3d, trend_5d, vix_alto)

        is_war_oil = ticker in SETTORI_WAR_OIL
        settore    = get_settore(ticker)

        score  = calcola_score(trend_5d, trend_30d, vol_ratio,
                               is_stabile, is_war_oil,
                               oil_favorevole, rsi, penalita, vix_alto)
        rating = score_to_rating(score, trend_5d)

        # Verdetto
        volumi_ok = vol_ratio >= VOL_SOGLIA_RATIO
        if trend_5d > 0 and volumi_ok and is_stabile and oil_favorevole and is_war_oil:
            verdetto = "🚀 FORTEZZA WAR-OIL"
        elif trend_5d > 0 and volumi_ok and is_stabile:
            verdetto = "💪 FORTEZZA"
        elif trend_5d > 0 and is_stabile:
            verdetto = "🛡️ RESILIENTE+"
        elif trend_5d > TREND_MIN_RESILIENTE and is_stabile:
            verdetto = "🛡️ RESILIENTE"
        elif trend_5d > TREND_MIN_RESILIENTE:
            verdetto = "⚡ VOLATILE"
        else:
            verdetto = "⚠️ INSTABILE"

        risultati.append({
            "TICKER":   ticker,
            "NOME":     nome,
            "PREZZO":   f"${p_fine:.2f}",
            "T5gg":     f"{trend_5d:+.2%}",
            "T30gg":    f"{trend_30d:+.2%}",
            "VOL/AVG":  f"{vol_ratio:.1f}x",
            "RSI":      f"{rsi:.0f}",
            "D.MAX":    f"{dist_max:+.1%}",
            "RISCHIO":  rischio_str,
            "WAR-OIL":  "⚑" if is_war_oil else "·",
            "SCORE":    score,
            "RATING":   rating,
            "VERDETTO": verdetto,
            "_settore": settore,
            "_t5":      trend_5d,
            "_t30":     trend_30d,
        })

    except Exception as e:
        errori.append(ticker)
        continue

# ──────────────────────────────────────────────────────────────────
# STEP 3 — OUTPUT PER CATEGORIA
# ──────────────────────────────────────────────────────────────────
if not risultati:
    print("❌ ERRORE CRITICO: Nessun dato elaborato.")
else:
    df = pd.DataFrame(risultati)
    df.sort_values(["SCORE", "_t5"], ascending=[False, False], inplace=True)

    CATEGORIE = [
        "🚀 FORTEZZA WAR-OIL",
        "💪 FORTEZZA",
        "🛡️ RESILIENTE+",
        "🛡️ RESILIENTE",
        "⚡ VOLATILE",
        "⚠️ INSTABILE",
    ]

    for cat in CATEGORIE:
        subset = df[df["VERDETTO"] == cat]
        if subset.empty: continue
        print(f"\n{'═'*80}")
        print(f"  {cat}  ({len(subset)} titoli)")
        print(f"{'═'*80}")
        cols = ["TICKER","NOME","PREZZO","T5gg","T30gg","VOL/AVG",
                "RSI","D.MAX","RISCHIO","WAR-OIL","SCORE","RATING"]
        print(subset[cols].to_string(index=False))

    # ──────────────────────────────────────────────────────────────
    # STEP 4 — TOP 6 CON CAP SETTORIALE
    # ──────────────────────────────────────────────────────────────
    print(f"\n\n{'★'*80}")
    print(f"  🏆  TOP {TOP_N} CANDIDATI USA  —  CLASSIFICA FINALE  (cap settoriale attivo)")
    print(f"  🛢️  Brent: {oil_fine:.2f} USD ({oil_trend:+.2%})  |  {stato_oil}")
    print(f"  📊  VIX: {vix_fine:.1f}  |  {stato_vix}")
    print(f"  💵  DXY: {dxy_fine:.2f} ({dxy_trend:+.2%})  |  S&P500: {sp_fine:.2f} ({sp_trend:+.2%})")
    print(f"  📅  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"  ⚠️   Cap: max {MAX_ENERGIA_TOP6} energia/petrolio | max {MAX_DIFESA_TOP6} difesa")
    print(f"{'★'*80}")
    print()

    # Selezione TOP6 con cap
    contatori  = {"energia": 0, "difesa": 0, "altro": 0}
    top6_righe = []
    for _, row in df.iterrows():
        s   = row["_settore"]
        cap = (MAX_ENERGIA_TOP6 if s == "energia"
               else MAX_DIFESA_TOP6 if s == "difesa"
               else 99)
        if contatori[s] < cap:
            top6_righe.append(row)
            contatori[s] += 1
        if len(top6_righe) == TOP_N:
            break

    header = (f"  {'#':>2}  {'TICKER':<8} {'NOME':<22} {'PREZZO':>9}  "
              f"{'T5gg':>7}  {'T30gg':>7}  {'RSI':>4}  {'D.MAX':>6}  "
              f"{'RISCHIO':<14}  {'SCORE':>5}  RATING")
    sep = "  " + "─" * (len(header) - 2)
    print(header)
    print(sep)

    for i, row in enumerate(top6_righe, 1):
        print(
            f"  {i:>2}  "
            f"{row['TICKER']:<8} "
            f"{row['NOME']:<22} "
            f"{row['PREZZO']:>9}  "
            f"{row['T5gg']:>7}  "
            f"{row['T30gg']:>7}  "
            f"{row['RSI']:>4}  "
            f"{row['D.MAX']:>6}  "
            f"{row['RISCHIO']:<14}  "
            f"{row['SCORE']:>5}  "
            f"{row['RATING']}"
        )

    print(sep)
    print()
    print(f"  Distribuzione: Energia={contatori['energia']}/{MAX_ENERGIA_TOP6}  "
          f"Difesa={contatori['difesa']}/{MAX_DIFESA_TOP6}  "
          f"Altri={contatori['altro']}")
    print()
    print("  LEGENDA:")
    print("  RSI    : >70=ipercomprato(-5pt) | <30=ipervenduto(+5pt)")
    print("  D.MAX  : distanza % dal massimo 30gg (0%=sul massimo=rischio)")
    print("  RISCHIO: 🟢BASSO=0pt | 🟡MEDIO=-8pt | 🔴ALTO=-18pt")
    print("  VIX>25 : mercato nervoso → +1pt rischio su ogni titolo")
    print()
    print("  🔥 STRONG BUY → Score≥75+T5>5% | 💚 BUY → Score≥60+T5>2%")
    print("  📈 ACCUMULATE → Score≥45+T5≥0% | 🟡 HOLD → Score≥30")
    print()
    print("  SCORE USA: trend5(30)+trend30(25)+vol(15)+stab(15)+war-oil(10)")
    print("             +RSI(±5) + penalità(0/-8/-18)")
    print("  NOTA: trend30 pesa 25pt (IT=20, EU=20) — struttura più importante in USA")
    print("        vol soglia 2.0x (IT=1.3, EU=1.5) — liquidità altissima")

    print(f"\n{'─'*80}")
    print(f"  📊  Titoli analizzati : {len(risultati)}/{len(USA)}")
    if errori:
        print(f"  ⚠️   Ticker errori : {', '.join(errori)}")

print(f"\n{'═'*80}")
print(f"  REFERENZA : {COSTRUTTORE}  |  WAR-SENTINEL_USA_V1")
print(f"  ESEGUITO  : {datetime.now().strftime('%d/%m/%Y alle %H:%M:%S')}")
print(f"{'═'*80}\n")

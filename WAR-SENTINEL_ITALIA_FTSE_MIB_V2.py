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

# Soglie
VOL_SOGLIA_RATIO     = 1.3    # volume oggi / media > questa soglia → volumi forti
STAB_SOGLIA          = 1.3    # std5gg < std30gg * soglia → stabile
TREND_MIN_RESILIENTE = -0.04  # calo massimo tollerato per "resiliente"
OIL_TREND_SOGLIA     = 0.01   # brent deve salire >1% per attivare paletto oil
TOP_N                = 6      # candidati nella tabella finale

# ──────────────────────────────────────────────────────────────────
# FTSE MIB — ticker Yahoo Finance verificati (v3.1)
# ──────────────────────────────────────────────────────────────────
FTSE_MIB = {
    # Energia & Petrolio
    "ENI.MI":    "ENI",
    "TEN.MI":    "Tenaris",
    "SPM.MI":    "Saipem",
    "MAIRE.MI":  "Maire Tecnimont",
    "ERG.MI":    "ERG",
    # Difesa & Aerospazio
    "LDO.MI":    "Leonardo",
    "IVG.MI":    "Iveco Group",          # v3.1: sostituisce CNH/Exor
    # Banche
    "UCG.MI":    "UniCredit",
    "ISP.MI":    "Intesa Sanpaolo",
    "BAMI.MI":   "Banco BPM",
    "MB.MI":     "Mediobanca",
    "BPE.MI":    "BPER Banca",           # v3.1: fix da BPER.MI
    "BMPS.MI":   "Monte dei Paschi",
    "FBK.MI":    "FinecoBank",
    "BGN.MI":    "Banca Generali",       # v3.1: fix da BGRE/BGEN
    # Assicurazioni
    "G.MI":      "Generali",
    "UNI.MI":    "Unipol",
    # Industria & Infrastrutture
    "STLAM.MI":  "Stellantis",
    "RACE.MI":   "Ferrari",
    "PRY.MI":    "Prysmian",
    "BRE.MI":    "Brembo",
    "DAN.MI":    "Danieli",
    "MONC.MI":   "Moncler",
    "AZM.MI":    "Azimut",
    # Utilities & Telecomunicazioni
    "ENEL.MI":   "Enel",
    "A2A.MI":    "A2A",
    "HER.MI":    "Hera",                 # v3.1: fix da HERA.MI
    "SRG.MI":    "Snam",
    "TRN.MI":    "Terna",
    "TIT.MI":    "Telecom Italia",
    # Farmaceutica & Healthcare
    "REC.MI":    "Recordati",
    "AMP.MI":    "Amplifon",
    "DIA.MI":    "DiaSorin",             # v3.1: fix da DiaSorin.MI
    # Consumer & Lusso
    "DLG.MI":    "De'Longhi",
    "BC.MI":     "Brunello Cucinelli",
    # Infrastrutture Digitali
    "INW.MI":    "Inwit",                # v3.1: fix da INWIT.MI
    "TLS.MI":    "Telecom Italia Risp.",
}

# Settori sensibili a guerra / energia
SETTORI_WAR_OIL = {
    "ENI.MI", "TEN.MI", "SPM.MI", "MAIRE.MI", "ERG.MI",
    "LDO.MI", "PRY.MI", "IVG.MI", "SRG.MI", "TRN.MI"
}

# ──────────────────────────────────────────────────────────────────
# FUNZIONE SCORE  (0 – 100)
# ──────────────────────────────────────────────────────────────────
def calcola_score(trend_5d, trend_30d, vol_ratio, is_stabile,
                  is_war_oil, oil_favorevole):
    """
    Pesi:
      trend_5d   → 35 pt  (componente principale, breve periodo)
      trend_30d  → 20 pt  (conferma strutturale)
      volumi     → 20 pt  (interesse del mercato)
      stabilità  → 15 pt  (qualità del movimento)
      war-oil    → 10 pt  (bonus contesto macro, solo se oil favorevole)
    """
    score = 0.0

    # Trend 5gg  (max 35)
    if trend_5d >= 0.08:   score += 35
    elif trend_5d >= 0.05: score += 28
    elif trend_5d >= 0.03: score += 20
    elif trend_5d >= 0.01: score += 12
    elif trend_5d >= 0:    score += 6
    else:                  score += max(0, 6 + trend_5d * 100)  # penalità

    # Trend 30gg  (max 20)
    if trend_30d >= 0.15:   score += 20
    elif trend_30d >= 0.05: score += 15
    elif trend_30d >= 0:    score += 10
    elif trend_30d >= -0.05:score += 5
    else:                   score += 0

    # Volumi  (max 20)
    if vol_ratio >= 2.0:   score += 20
    elif vol_ratio >= 1.5: score += 16
    elif vol_ratio >= 1.3: score += 12
    elif vol_ratio >= 1.0: score += 7
    else:                  score += 3

    # Stabilità  (max 15)
    if is_stabile: score += 15

    # Bonus WAR-OIL  (max 10, solo se brent favorevole)
    if is_war_oil and oil_favorevole: score += 10

    return round(min(score, 100), 1)


def score_to_rating(score, trend_5d):
    """Converte score numerico in rating testuale."""
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
print(f"║   🛡️  WAR-SENTINEL_ITALIA_FTSE_MIB_V2                          ║")
print(f"║   📅  {datetime.now().strftime('%d/%m/%Y  %H:%M')}                                         ║")
print(f"║   👤  {COSTRUTTORE}                         ║")
print("╚══════════════════════════════════════════════════════════════════╝")

# ──────────────────────────────────────────────────────────────────
# STEP 1 — BRENT CRUDE
# ──────────────────────────────────────────────────────────────────
print("\n📡 Scarico Brent Crude (BZ=F)...")
try:
    oil_data = yf.download(OIL_TICKER, period="10d", progress=False)['Close']
    if isinstance(oil_data, pd.DataFrame): oil_data = oil_data.iloc[:, 0]
    oil_data = oil_data.dropna()
    oil_inizio     = float(oil_data.iloc[0])
    oil_fine       = float(oil_data.iloc[-1])
    oil_trend      = (oil_fine - oil_inizio) / oil_inizio
    oil_favorevole = oil_trend > OIL_TREND_SOGLIA
    icona = "🟢" if oil_trend > 0.02 else ("🟡" if oil_trend > 0 else "🔴")
    print(f"   {icona}  Brent: {oil_fine:.2f} USD  |  Trend 10gg: {oil_trend:+.2%}")
    stato_oil = "FAVOREVOLE ✅" if oil_favorevole else "NEUTRO/NEG ⛔"
    print(f"   Contesto oil: {stato_oil}")
except Exception as e:
    oil_trend = 0.0; oil_favorevole = False; oil_fine = 0.0
    print(f"   ⚠️  Dati Brent non disponibili ({e})")

# ──────────────────────────────────────────────────────────────────
# STEP 2 — SCANSIONE FTSE MIB
# ──────────────────────────────────────────────────────────────────
print(f"\n🔍 Scansione {len(FTSE_MIB)} titoli FTSE MIB...\n")

risultati = []
errori    = []

for ticker, nome in FTSE_MIB.items():
    try:
        raw = yf.download(ticker, period="30d", progress=False, auto_adjust=True)
        if raw.empty: errori.append(ticker); continue

        close  = raw['Close']
        volume = raw['Volume']
        if isinstance(close,  pd.DataFrame): close  = close.iloc[:, 0]
        if isinstance(volume, pd.DataFrame): volume = volume.iloc[:, 0]
        close  = close.dropna()
        volume = volume.dropna()
        if len(close) < 6: errori.append(ticker); continue

        # Indicatori
        p_fine    = float(close.iloc[-1])
        p_5gg     = float(close.iloc[-6])
        p_inizio  = float(close.iloc[0])
        trend_5d  = (p_fine - p_5gg)   / p_5gg
        trend_30d = (p_fine - p_inizio) / p_inizio

        std_5d    = float(close.tail(5).std())
        std_30d   = float(close.std())
        is_stabile = std_5d < (std_30d * STAB_SOGLIA)

        vol_oggi  = float(volume.iloc[-1])
        vol_medio = float(volume.mean())
        vol_ratio = vol_oggi / vol_medio if vol_medio > 0 else 0

        is_war_oil = ticker in SETTORI_WAR_OIL

        # Score e rating
        score  = calcola_score(trend_5d, trend_30d, vol_ratio,
                               is_stabile, is_war_oil, oil_favorevole)
        rating = score_to_rating(score, trend_5d)

        # Verdetto classico (per tabella intermedia)
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
            "PREZZO":   f"{p_fine:.2f}€",
            "T5gg":     f"{trend_5d:+.2%}",
            "T30gg":    f"{trend_30d:+.2%}",
            "VOL/AVG":  f"{vol_ratio:.1f}x",
            "STABILE":  "SI" if is_stabile else "NO",
            "WAR-OIL":  "⚑" if is_war_oil else "·",
            "SCORE":    score,
            "RATING":   rating,
            "VERDETTO": verdetto,
            "_t5":      trend_5d,
            "_t30":     trend_30d,
        })

    except Exception as e:
        errori.append(f"{ticker}")
        continue

# ──────────────────────────────────────────────────────────────────
# STEP 3 — OUTPUT COMPLETO PER CATEGORIA
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
        print(f"\n{'═'*72}")
        print(f"  {cat}  ({len(subset)} titoli)")
        print(f"{'═'*72}")
        cols = ["TICKER","NOME","PREZZO","T5gg","T30gg","VOL/AVG","STABILE","WAR-OIL","SCORE","RATING"]
        print(subset[cols].to_string(index=False))

    # ──────────────────────────────────────────────────────────────
    # STEP 4 — TABELLA FINALE TOP-6 CANDIDATI
    # ──────────────────────────────────────────────────────────────
    print(f"\n\n{'★'*72}")
    print(f"  🏆  TOP {TOP_N} CANDIDATI  —  CLASSIFICA FINALE")
    print(f"  🛢️  Brent: {oil_fine:.2f} USD ({oil_trend:+.2%})  |  Oil: {stato_oil}")
    print(f"  📅  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'★'*72}")
    print()

    top6 = df.head(TOP_N).reset_index(drop=True)
    top6.index += 1  # ranking da 1

    header = f"  {'#':>2}  {'TICKER':<12} {'NOME':<22} {'PREZZO':>8}  {'T5gg':>7}  {'T30gg':>7}  {'VOL/AVG':>7}  {'STBL':>4}  {'W-O':>3}  {'SCORE':>5}  RATING"
    sep    = "  " + "─" * (len(header) - 2)
    print(header)
    print(sep)

    for i, row in top6.iterrows():
        print(
            f"  {i:>2}  "
            f"{row['TICKER']:<12} "
            f"{row['NOME']:<22} "
            f"{row['PREZZO']:>8}  "
            f"{row['T5gg']:>7}  "
            f"{row['T30gg']:>7}  "
            f"{row['VOL/AVG']:>7}  "
            f"{row['STABILE']:>4}  "
            f"{row['WAR-OIL']:>3}  "
            f"{row['SCORE']:>5}  "
            f"{row['RATING']}"
        )

    print(sep)
    print()
    print("  LEGENDA RATING:")
    print("  🔥 STRONG BUY  → Score ≥75 + Trend5gg >5%")
    print("  💚 BUY         → Score ≥60 + Trend5gg >2%")
    print("  📈 ACCUMULATE  → Score ≥45 + Trend5gg ≥0%")
    print("  🟡 HOLD        → Score ≥30")
    print("  🔻 AVOID       → Score <30 o trend molto negativo")
    print()
    print("  SCORE 0–100: trend5gg(35pt) + trend30gg(20pt) + volumi(20pt)")
    print("               + stabilità(15pt) + bonus war-oil(10pt, se oil↑)")

    # ── Riepilogo
    print(f"\n{'─'*72}")
    print(f"  📊  Titoli analizzati : {len(risultati)}/{len(FTSE_MIB)}")
    if errori:
        print(f"  ⚠️   Ticker non trovati : {', '.join(errori)}")

print(f"\n{'═'*72}")
print(f"  REFERENZA : {COSTRUTTORE}  |  WAR-SENTINEL_ITALIA_FTSE_MIB_V2")
print(f"  ESEGUITO  : {datetime.now().strftime('%d/%m/%Y alle %H:%M:%S')}")
print(f"{'═'*72}\n")

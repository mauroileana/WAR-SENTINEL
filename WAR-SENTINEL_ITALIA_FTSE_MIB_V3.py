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

# Soglie base — calibrate per mercato ITALIANO (meno liquido)
VOL_SOGLIA_RATIO     = 1.3    # IT meno liquido → soglia più bassa di EU (1.5x)
STAB_SOGLIA          = 1.3
TREND_MIN_RESILIENTE = -0.04
OIL_TREND_SOGLIA     = 0.01
TOP_N                = 6

# ── Soglie anti-rischio (stesse di Europa v2) ────────────────────
RSI_IPERCOMPRATO     = 70
RSI_IPERVENDUTO      = 30
DIST_MAX_SOGLIA      = -0.05
ACCEL_SOGLIA         = 1.8

# ── Cap settoriale nel TOP6 ───────────────────────────────────────
MAX_ENERGIA_TOP6     = 3      # max 3 titoli energia/petrolio nel TOP6
MAX_DIFESA_TOP6      = 2      # max 2 titoli difesa nel TOP6

# ──────────────────────────────────────────────────────────────────
# FTSE MIB — 36 titoli ticker Yahoo Finance verificati
# ──────────────────────────────────────────────────────────────────
FTSE_MIB = {
    # ── ENERGIA & PETROLIO ──────────────────────────────────────
    "ENI.MI":    "ENI",
    "TEN.MI":    "Tenaris",
    "SPM.MI":    "Saipem",
    "MAIRE.MI":  "Maire Tecnimont",
    "ERG.MI":    "ERG",
    # ── DIFESA & AEROSPAZIO ─────────────────────────────────────
    "LDO.MI":    "Leonardo",
    "IVG.MI":    "Iveco Group",
    # ── BANCHE ──────────────────────────────────────────────────
    "UCG.MI":    "UniCredit",
    "ISP.MI":    "Intesa Sanpaolo",
    "BAMI.MI":   "Banco BPM",
    "MB.MI":     "Mediobanca",
    "BPE.MI":    "BPER Banca",
    "BMPS.MI":   "Monte dei Paschi",
    "FBK.MI":    "FinecoBank",
    "BGN.MI":    "Banca Generali",
    # ── ASSICURAZIONI ───────────────────────────────────────────
    "G.MI":      "Generali",
    "UNI.MI":    "Unipol",
    # ── INDUSTRIA & INFRASTRUTTURE ──────────────────────────────
    "STLAM.MI":  "Stellantis",
    "RACE.MI":   "Ferrari",
    "PRY.MI":    "Prysmian",
    "BRE.MI":    "Brembo",
    "DAN.MI":    "Danieli",
    "MONC.MI":   "Moncler",
    "AZM.MI":    "Azimut",
    # ── UTILITIES & TELECOMUNICAZIONI ───────────────────────────
    "ENEL.MI":   "Enel",
    "A2A.MI":    "A2A",
    "HER.MI":    "Hera",
    "SRG.MI":    "Snam",
    "TRN.MI":    "Terna",
    "TIT.MI":    "Telecom Italia",
    # ── FARMACEUTICA & HEALTHCARE ────────────────────────────────
    "REC.MI":    "Recordati",
    "AMP.MI":    "Amplifon",
    "DIA.MI":    "DiaSorin",
    # ── CONSUMER & LUSSO ────────────────────────────────────────
    "DLG.MI":    "De'Longhi",
    "BC.MI":     "Brunello Cucinelli",
    # ── INFRASTRUTTURE DIGITALI ──────────────────────────────────
    "INW.MI":    "Inwit",
    "TLS.MI":    "Telecom Italia Risp.",
}

# Classificazione settori per cap
SETTORI_ENERGIA  = {"ENI.MI","TEN.MI","SPM.MI","MAIRE.MI","ERG.MI"}
SETTORI_DIFESA   = {"LDO.MI","IVG.MI"}
SETTORI_WAR_OIL  = SETTORI_ENERGIA | SETTORI_DIFESA | {"PRY.MI","SRG.MI","TRN.MI"}

def get_settore(ticker):
    if ticker in SETTORI_ENERGIA: return "energia"
    if ticker in SETTORI_DIFESA:  return "difesa"
    return "altro"

# ──────────────────────────────────────────────────────────────────
# FUNZIONI NUOVI INDICATORI
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

def calcola_rischio_entrata(rsi, dist_max, trend_3d, trend_5d):
    """
    Combina RSI, overextension e accelerazione momentum.
    Ritorna (label, penalità_score)
    """
    punti = 0

    # RSI
    if rsi > RSI_IPERCOMPRATO:
        punti += 2
    elif rsi < RSI_IPERVENDUTO:
        punti -= 1

    # Distanza dal massimo 30gg
    if dist_max > -0.03:
        punti += 2
    elif dist_max > -0.08:
        punti += 1

    # Accelerazione (parabola)
    if trend_5d != 0 and abs(trend_3d / trend_5d) > ACCEL_SOGLIA and trend_3d > 0:
        punti += 2

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
                  is_war_oil, oil_favorevole, rsi, penalita_rischio):
    """
    Pesi Italia (mercato meno liquido → trend5gg pesa di più):
      trend_5d       → 35 pt  (IT: più peso di EU che ha 30pt)
      trend_30d      → 20 pt
      volumi         → 15 pt  (IT: meno peso, volumi più piccoli)
      stabilità      → 15 pt
      war-oil bonus  → 10 pt  (solo se oil favorevole)
      RSI            → ±5 pt
      penalità       → 0/-8/-18
    """
    score = 0.0

    # Trend 5gg (max 35)
    if trend_5d >= 0.08:    score += 35
    elif trend_5d >= 0.05:  score += 28
    elif trend_5d >= 0.03:  score += 20
    elif trend_5d >= 0.01:  score += 12
    elif trend_5d >= 0:     score += 6
    else:                   score += max(0, 6 + trend_5d * 100)

    # Trend 30gg (max 20)
    if trend_30d >= 0.15:    score += 20
    elif trend_30d >= 0.05:  score += 15
    elif trend_30d >= 0:     score += 10
    elif trend_30d >= -0.05: score += 5

    # Volumi (max 15) — peso ridotto per IT
    if vol_ratio >= 2.0:    score += 15
    elif vol_ratio >= 1.5:  score += 12
    elif vol_ratio >= 1.3:  score += 9
    elif vol_ratio >= 1.0:  score += 5
    else:                   score += 2

    # Stabilità (max 15)
    if is_stabile: score += 15

    # Bonus WAR-OIL (max 10)
    if is_war_oil and oil_favorevole: score += 10

    # RSI (±5)
    if rsi < RSI_IPERVENDUTO:    score += 5
    elif rsi > RSI_IPERCOMPRATO: score -= 5

    # Penalità rischio entrata
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
print(f"║   🛡️  WAR-SENTINEL_ITALIA_FTSE_MIB_V3                          ║")
print(f"║   📅  {datetime.now().strftime('%d/%m/%Y  %H:%M')}                                         ║")
print(f"║   👤  {COSTRUTTORE}                         ║")
print("╚══════════════════════════════════════════════════════════════════╝")
print("   v3: RSI + Overextension + Momentum + Cap Settoriale TOP6")

# ──────────────────────────────────────────────────────────────────
# STEP 1 — BRENT CRUDE
# ──────────────────────────────────────────────────────────────────
print("\n📡 Scarico Brent Crude (BZ=F)...")
try:
    oil_data = yf.download(OIL_TICKER, period="10d", progress=False)['Close']
    if isinstance(oil_data, pd.DataFrame): oil_data = oil_data.iloc[:, 0]
    oil_data       = oil_data.dropna()
    oil_fine       = float(oil_data.iloc[-1])
    oil_trend      = (oil_fine - float(oil_data.iloc[0])) / float(oil_data.iloc[0])
    oil_favorevole = oil_trend > OIL_TREND_SOGLIA
    icona = "🟢" if oil_trend > 0.02 else ("🟡" if oil_trend > 0 else "🔴")
    stato_oil = "FAVOREVOLE ✅" if oil_favorevole else "NEUTRO/NEG ⛔"
    print(f"   {icona}  Brent: {oil_fine:.2f} USD  |  Trend 10gg: {oil_trend:+.2%}  |  {stato_oil}")
except Exception as e:
    oil_trend = 0.0; oil_favorevole = False; oil_fine = 0.0; stato_oil = "N/D"
    print(f"   ⚠️  Brent non disponibile ({e})")

# ──────────────────────────────────────────────────────────────────
# STEP 2 — SCANSIONE FTSE MIB
# ──────────────────────────────────────────────────────────────────
print(f"\n🔍 Scansione {len(FTSE_MIB)} titoli FTSE MIB...\n")

risultati = []
errori    = []

for ticker, nome in FTSE_MIB.items():
    try:
        # 60gg per RSI affidabile
        raw = yf.download(ticker, period="60d", progress=False, auto_adjust=True)
        if raw.empty: errori.append(ticker); continue

        close  = raw['Close']
        volume = raw['Volume']
        if isinstance(close,  pd.DataFrame): close  = close.iloc[:, 0]
        if isinstance(volume, pd.DataFrame): volume = volume.iloc[:, 0]
        close  = close.dropna()
        volume = volume.dropna()
        if len(close) < 20: errori.append(ticker); continue

        # ── Indicatori base ──────────────────────────────────────
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

        # ── NUOVI INDICATORI v3 ──────────────────────────────────
        rsi     = calcola_rsi(close, 14)
        max_30d = float(close.tail(30).max())
        dist_max = (p_fine - max_30d) / max_30d
        rischio_str, penalita = calcola_rischio_entrata(rsi, dist_max, trend_3d, trend_5d)

        is_war_oil = ticker in SETTORI_WAR_OIL
        settore    = get_settore(ticker)

        # Score e rating
        score  = calcola_score(trend_5d, trend_30d, vol_ratio,
                               is_stabile, is_war_oil,
                               oil_favorevole, rsi, penalita)
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
            "PREZZO":   f"{p_fine:.2f}€",
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
    print(f"  🏆  TOP {TOP_N} CANDIDATI ITALIA  —  CLASSIFICA FINALE  (cap settoriale attivo)")
    print(f"  🛢️  Brent: {oil_fine:.2f} USD ({oil_trend:+.2%})  |  {stato_oil}")
    print(f"  📅  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"  ⚠️   Cap: max {MAX_ENERGIA_TOP6} energia/petrolio | max {MAX_DIFESA_TOP6} difesa")
    print(f"{'★'*80}")
    print()

    # Selezione con cap settoriale
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

    header = (f"  {'#':>2}  {'TICKER':<12} {'NOME':<22} {'PREZZO':>8}  "
              f"{'T5gg':>7}  {'T30gg':>7}  {'RSI':>4}  {'D.MAX':>6}  "
              f"{'RISCHIO':<14}  {'SCORE':>5}  RATING")
    sep = "  " + "─" * (len(header) - 2)
    print(header)
    print(sep)

    for i, row in enumerate(top6_righe, 1):
        print(
            f"  {i:>2}  "
            f"{row['TICKER']:<12} "
            f"{row['NOME']:<22} "
            f"{row['PREZZO']:>8}  "
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
    print("  RSI   : >70=ipercomprato(-5pt) | <30=ipervenduto(+5pt) | 30-70=neutro")
    print("  D.MAX : distanza % dal massimo 30gg  (0%=sul massimo → rischio alto)")
    print("  RISCHIO: 🟢BASSO=0pt | 🟡MEDIO=-8pt | 🔴ALTO=-18pt sullo score")
    print()
    print("  🔥 STRONG BUY → Score≥75+T5>5% | 💚 BUY → Score≥60+T5>2%")
    print("  📈 ACCUMULATE → Score≥45+T5≥0% | 🟡 HOLD → Score≥30")
    print()
    print("  SCORE IT: trend5(35)+trend30(20)+vol(15)+stab(15)+war-oil(10)")
    print("            +RSI(±5) + penalità rischio(0/-8/-18)")
    print("  NOTA: vol peso 15pt (EU=20pt) — mercato IT meno liquido")

    print(f"\n{'─'*80}")
    print(f"  📊  Titoli analizzati : {len(risultati)}/{len(FTSE_MIB)}")
    if errori:
        print(f"  ⚠️   Ticker errori : {', '.join(errori)}")

print(f"\n{'═'*80}")
print(f"  REFERENZA : {COSTRUTTORE}  |  WAR-SENTINEL_ITALIA_FTSE_MIB_V3")
print(f"  ESEGUITO  : {datetime.now().strftime('%d/%m/%Y alle %H:%M:%S')}")
print(f"{'═'*80}\n")

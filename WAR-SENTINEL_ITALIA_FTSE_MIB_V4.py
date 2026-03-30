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

VOL_SOGLIA_RATIO     = 1.3
STAB_SOGLIA          = 1.3
TREND_MIN_RESILIENTE = -0.04
OIL_TREND_SOGLIA     = 0.01
TOP_N                = 6

RSI_IPERCOMPRATO     = 70
RSI_IPERVENDUTO      = 30
ACCEL_SOGLIA         = 1.8

MAX_ENERGIA_TOP6     = 3
MAX_DIFESA_TOP6      = 2

# ── Soglie supporto e divergenza ─────────────────────────────────
SUP_VICINO_SOGLIA    = 0.04   # entro 4% dal supporto → "SUL SUPPORTO"
DIV_PREZZO_MIN       = -0.02  # prezzo deve scendere almeno -2%
DIV_RSI_MIN          = 2.0    # RSI deve salire almeno 2pt
DIV_RSI_MAX          = -2.0   # RSI deve scendere almeno -2pt

BONUS_SUP_DIV        = +8
BONUS_SUP_SOLO       = +4
BONUS_DIV_RIALZ      = +4
MALUS_DIV_RIBAS      = -5

# ──────────────────────────────────────────────────────────────────
# FTSE MIB — 36 titoli
# ──────────────────────────────────────────────────────────────────
FTSE_MIB = {
    "ENI.MI":    "ENI",
    "TEN.MI":    "Tenaris",
    "SPM.MI":    "Saipem",
    "MAIRE.MI":  "Maire Tecnimont",
    "ERG.MI":    "ERG",
    "LDO.MI":    "Leonardo",
    "IVG.MI":    "Iveco Group",
    "UCG.MI":    "UniCredit",
    "ISP.MI":    "Intesa Sanpaolo",
    "BAMI.MI":   "Banco BPM",
    "MB.MI":     "Mediobanca",
    "BPE.MI":    "BPER Banca",
    "BMPS.MI":   "Monte dei Paschi",
    "FBK.MI":    "FinecoBank",
    "BGN.MI":    "Banca Generali",
    "G.MI":      "Generali",
    "UNI.MI":    "Unipol",
    "STLAM.MI":  "Stellantis",
    "RACE.MI":   "Ferrari",
    "PRY.MI":    "Prysmian",
    "BRE.MI":    "Brembo",
    "DAN.MI":    "Danieli",
    "MONC.MI":   "Moncler",
    "AZM.MI":    "Azimut",
    "ENEL.MI":   "Enel",
    "A2A.MI":    "A2A",
    "HER.MI":    "Hera",
    "SRG.MI":    "Snam",
    "TRN.MI":    "Terna",
    "TIT.MI":    "Telecom Italia",
    "REC.MI":    "Recordati",
    "AMP.MI":    "Amplifon",
    "DIA.MI":    "DiaSorin",
    "DLG.MI":    "De'Longhi",
    "BC.MI":     "Brunello Cucinelli",
    "INW.MI":    "Inwit",
    "TLS.MI":    "Telecom Italia Risp.",
}

SETTORI_ENERGIA  = {"ENI.MI","TEN.MI","SPM.MI","MAIRE.MI","ERG.MI"}
SETTORI_DIFESA   = {"LDO.MI","IVG.MI"}
SETTORI_WAR_OIL  = SETTORI_ENERGIA | SETTORI_DIFESA | {"PRY.MI","SRG.MI","TRN.MI"}

def get_settore(ticker):
    if ticker in SETTORI_ENERGIA: return "energia"
    if ticker in SETTORI_DIFESA:  return "difesa"
    return "altro"

# ──────────────────────────────────────────────────────────────────
# FUNZIONI INDICATORI
# ──────────────────────────────────────────────────────────────────
def calcola_rsi_serie(close, periodi=14):
    try:
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(window=periodi, min_periods=periodi).mean()
        loss  = (-delta.clip(upper=0)).rolling(window=periodi, min_periods=periodi).mean()
        rs    = gain / loss.replace(0, 1e-9)
        return 100 - (100 / (1 + rs))
    except:
        return pd.Series([50.0] * len(close), index=close.index)

def calcola_rsi(close, periodi=14):
    return float(calcola_rsi_serie(close, periodi).dropna().iloc[-1])

def calcola_supporto(close):
    min_30d  = float(close.tail(30).min())
    p_fine   = float(close.iloc[-1])
    dist_sup = (p_fine - min_30d) / min_30d
    sul_sup  = dist_sup <= SUP_VICINO_SOGLIA
    return dist_sup, sul_sup

def calcola_divergenza(close, rsi_serie):
    try:
        rsi_clean = rsi_serie.dropna()
        if len(close) < 11 or len(rsi_clean) < 11:
            return "· NEUTR", 0
        price_10d = (float(close.iloc[-1]) - float(close.iloc[-11])) / float(close.iloc[-11])
        rsi_10d   = float(rsi_clean.iloc[-1]) - float(rsi_clean.iloc[-11])
        if price_10d <= DIV_PREZZO_MIN and rsi_10d >= DIV_RSI_MIN:
            return "↗ RIALZ", BONUS_DIV_RIALZ
        elif price_10d >= 0.02 and rsi_10d <= DIV_RSI_MAX:
            return "↘ RIBAS", MALUS_DIV_RIBAS
        else:
            return "· NEUTR", 0
    except:
        return "· NEUTR", 0

def calcola_bonus_sup_div(sul_supporto, div_label, div_bonus):
    if sul_supporto and div_label == "↗ RIALZ":
        return BONUS_SUP_DIV
    elif sul_supporto:
        return BONUS_SUP_SOLO
    elif div_label == "↗ RIALZ":
        return BONUS_DIV_RIALZ
    else:
        return div_bonus

def calcola_rischio_entrata(rsi, dist_max, trend_3d, trend_5d):
    punti = 0
    if rsi > RSI_IPERCOMPRATO:       punti += 2
    elif rsi < RSI_IPERVENDUTO:      punti -= 1
    if dist_max > -0.03:             punti += 2
    elif dist_max > -0.08:           punti += 1
    if trend_5d != 0 and abs(trend_3d / trend_5d) > ACCEL_SOGLIA and trend_3d > 0:
        punti += 2
    if punti >= 4:   return "🔴 ALTO",  -18
    elif punti >= 2: return "🟡 MEDIO", -8
    else:            return "🟢 BASSO",  0

def calcola_score(trend_5d, trend_30d, vol_ratio, is_stabile,
                  is_war_oil, oil_favorevole, rsi,
                  penalita_rischio, bonus_sup_div):
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
    # Volumi (max 15)
    if vol_ratio >= 2.0:    score += 15
    elif vol_ratio >= 1.5:  score += 12
    elif vol_ratio >= 1.3:  score += 9
    elif vol_ratio >= 1.0:  score += 5
    else:                   score += 2
    # Stabilità (max 15)
    if is_stabile: score += 15
    # War-oil (max 10)
    if is_war_oil and oil_favorevole: score += 10
    # RSI (±5)
    if rsi < RSI_IPERVENDUTO:    score += 5
    elif rsi > RSI_IPERCOMPRATO: score -= 5
    # Penalità rischio
    score += penalita_rischio
    # Bonus supporto/divergenza
    score += bonus_sup_div
    return round(max(0, min(score, 100)), 1)

def score_to_rating(score, trend_5d):
    if score >= 75 and trend_5d > 0.05:   return "🔥 STRONG BUY"
    elif score >= 60 and trend_5d > 0.02: return "💚 BUY"
    elif score >= 45 and trend_5d >= 0:   return "📈 ACCUMULATE"
    elif score >= 30:                      return "🟡 HOLD"
    else:                                  return "🔻 AVOID"

# ──────────────────────────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────────────────────────
print()
print("╔══════════════════════════════════════════════════════════════════╗")
print(f"║   🛡️  WAR-SENTINEL_ITALIA_FTSE_MIB_V4                          ║")
print(f"║   📅  {datetime.now().strftime('%d/%m/%Y  %H:%M')}                                         ║")
print(f"║   👤  {COSTRUTTORE}                         ║")
print("╚══════════════════════════════════════════════════════════════════╝")
print("   v4: +Supporto 30gg + Divergenza RSI 10gg")

# ──────────────────────────────────────────────────────────────────
# STEP 1 — BRENT
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
except:
    oil_trend = 0.0; oil_favorevole = False; oil_fine = 0.0; stato_oil = "N/D"
    print("   ⚠️  Brent non disponibile")

# ──────────────────────────────────────────────────────────────────
# STEP 2 — SCANSIONE
# ──────────────────────────────────────────────────────────────────
print(f"\n🔍 Scansione {len(FTSE_MIB)} titoli FTSE MIB...\n")

risultati = []
errori    = []

for ticker, nome in FTSE_MIB.items():
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

        rsi_serie = calcola_rsi_serie(close, 14)
        rsi       = float(rsi_serie.dropna().iloc[-1])

        max_30d  = float(close.tail(30).max())
        dist_max = (p_fine - max_30d) / max_30d

        # ── NUOVI v4 ─────────────────────────────────────────────
        dist_sup, sul_supporto = calcola_supporto(close)
        div_label, div_bonus   = calcola_divergenza(close, rsi_serie)
        bonus_sup_div          = calcola_bonus_sup_div(sul_supporto, div_label, div_bonus)

        rischio_str, penalita = calcola_rischio_entrata(rsi, dist_max, trend_3d, trend_5d)

        is_war_oil = ticker in SETTORI_WAR_OIL
        settore    = get_settore(ticker)

        score  = calcola_score(trend_5d, trend_30d, vol_ratio,
                               is_stabile, is_war_oil, oil_favorevole,
                               rsi, penalita, bonus_sup_div)
        rating = score_to_rating(score, trend_5d)

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
            "SUP":      f"{dist_sup:+.1%}",
            "DIV":      div_label,
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

    for cat in ["🚀 FORTEZZA WAR-OIL","💪 FORTEZZA","🛡️ RESILIENTE+",
                "🛡️ RESILIENTE","⚡ VOLATILE","⚠️ INSTABILE"]:
        subset = df[df["VERDETTO"] == cat]
        if subset.empty: continue
        print(f"\n{'═'*84}")
        print(f"  {cat}  ({len(subset)} titoli)")
        print(f"{'═'*84}")
        cols = ["TICKER","NOME","PREZZO","T5gg","T30gg","VOL/AVG",
                "RSI","D.MAX","SUP","DIV","RISCHIO","SCORE","RATING"]
        print(subset[cols].to_string(index=False))

    # ──────────────────────────────────────────────────────────────
    # STEP 4 — TOP 6
    # ──────────────────────────────────────────────────────────────
    print(f"\n\n{'★'*84}")
    print(f"  🏆  TOP {TOP_N} CANDIDATI ITALIA  —  CLASSIFICA FINALE  (cap settoriale attivo)")
    print(f"  🛢️  Brent: {oil_fine:.2f} USD ({oil_trend:+.2%})  |  {stato_oil}")
    print(f"  📅  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"  ⚠️   Cap: max {MAX_ENERGIA_TOP6} energia | max {MAX_DIFESA_TOP6} difesa")
    print(f"{'★'*84}")
    print()

    contatori  = {"energia": 0, "difesa": 0, "altro": 0}
    top6_righe = []
    for _, row in df.iterrows():
        s   = row["_settore"]
        cap = MAX_ENERGIA_TOP6 if s == "energia" else MAX_DIFESA_TOP6 if s == "difesa" else 99
        if contatori[s] < cap:
            top6_righe.append(row)
            contatori[s] += 1
        if len(top6_righe) == TOP_N:
            break

    header = (f"  {'#':>2}  {'TICKER':<12} {'NOME':<22} {'PREZZO':>8}  "
              f"{'T5gg':>7}  {'T30gg':>7}  {'RSI':>4}  "
              f"{'D.MAX':>6}  {'SUP':>5}  {'DIV':<8}  "
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
            f"{row['SUP']:>5}  "
            f"{row['DIV']:<8}  "
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
    print("  LEGENDA v4:")
    print(f"  SUP    : distanza % dal minimo 30gg  ≤+4% = sul supporto → +{BONUS_SUP_SOLO}pt")
    print(f"  DIV    : ↗ RIALZ (prezzo↓+RSI↑) → +{BONUS_DIV_RIALZ}pt  "
          f"| ↘ RIBAS (prezzo↑+RSI↓) → {MALUS_DIV_RIBAS}pt  | · NEUTR")
    print(f"  SUP+DIV rialzista → bonus massimo +{BONUS_SUP_DIV}pt")
    print()
    print("  RSI    : >70=-5pt | <30=+5pt")
    print("  RISCHIO: 🟢=0pt | 🟡=-8pt | 🔴=-18pt")
    print("  SCORE IT: trend5(35)+trend30(20)+vol(15)+stab(15)+war-oil(10)")
    print("            +RSI(±5)+penalità(0/-8/-18)+SUP/DIV(0/+4/+8/-5)")

    print(f"\n{'─'*84}")
    print(f"  📊  Titoli analizzati : {len(risultati)}/{len(FTSE_MIB)}")
    if errori:
        print(f"  ⚠️   Ticker errori : {', '.join(errori)}")

print(f"\n{'═'*84}")
print(f"  REFERENZA : {COSTRUTTORE}  |  WAR-SENTINEL_ITALIA_FTSE_MIB_V4")
print(f"  ESEGUITO  : {datetime.now().strftime('%d/%m/%Y alle %H:%M:%S')}")
print(f"{'═'*84}\n")

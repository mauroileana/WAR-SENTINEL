import yfinance as yf
import pandas as pd
import numpy as np
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

VOL_SOGLIA_RATIO     = 2.0
STAB_SOGLIA          = 1.3
TREND_MIN_RESILIENTE = -0.04
OIL_TREND_SOGLIA     = 0.01
TOP_N                = 6

RSI_IPERCOMPRATO     = 70
RSI_IPERVENDUTO      = 30
ACCEL_SOGLIA         = 1.6
VIX_ALERT            = 25

# ── Soglie nuovi parametri v2 ─────────────────────────────────────
SUP_VICINO_SOGLIA    = 0.04   # entro 4% dal supporto → "SUL SUPPORTO"
DIV_PREZZO_MIN       = -0.02  # prezzo deve scendere almeno -2% per divergenza
DIV_RSI_MIN          = 2.0    # RSI deve salire almeno 2pt per divergenza rialzista
DIV_RSI_MAX          = -2.0   # RSI deve scendere almeno -2pt per divergenza ribassista

# Bonus/penalità score per supporto e divergenza
BONUS_SUP_DIV        = +8     # supporto vicino + divergenza rialzista → bonus
BONUS_SUP_SOLO       = +4     # solo supporto vicino → bonus minore
BONUS_DIV_RIALZ      = +4     # solo divergenza rialzista → bonus minore
MALUS_DIV_RIBAS      = -5     # divergenza ribassista → penalità

MAX_ENERGIA_TOP6     = 3
MAX_DIFESA_TOP6      = 2

# ──────────────────────────────────────────────────────────────────
# PANIERE USA — Dow Jones 30 + Nasdaq Top 30
# ──────────────────────────────────────────────────────────────────
USA = {
    # ── Energia & Petrolio ───────────────────────────────────────
    "CVX":   "Chevron",
    "XOM":   "ExxonMobil",
    "OXY":   "Occidental Petroleum",
    "COP":   "ConocoPhillips",
    "SLB":   "SLB (Schlumberger)",
    # ── Difesa & Aerospazio ──────────────────────────────────────
    "BA":    "Boeing",
    "HON":   "Honeywell",
    "RTX":   "Raytheon",
    "LMT":   "Lockheed Martin",
    "NOC":   "Northrop Grumman",
    "GD":    "General Dynamics",
    # ── Industria ────────────────────────────────────────────────
    "CAT":   "Caterpillar",
    "MMM":   "3M",
    "GE":    "GE Aerospace",
    "SHW":   "Sherwin-Williams",
    # ── Banche & Finanza ─────────────────────────────────────────
    "JPM":   "JPMorgan Chase",
    "GS":    "Goldman Sachs",
    "AXP":   "American Express",
    "V":     "Visa",
    "TRV":   "Travelers",
    # ── Healthcare ───────────────────────────────────────────────
    "JNJ":   "Johnson & Johnson",
    "MRK":   "Merck",
    "UNH":   "UnitedHealth",
    "AMGN":  "Amgen",
    "GILD":  "Gilead Sciences",
    "REGN":  "Regeneron",
    "VRTX":  "Vertex Pharma",
    # ── Consumer & Retail ────────────────────────────────────────
    "WMT":   "Walmart",
    "MCD":   "McDonald's",
    "HD":    "Home Depot",
    "KO":    "Coca-Cola",
    "PG":    "Procter & Gamble",
    "NKE":   "Nike",
    "DIS":   "Disney",
    "COST":  "Costco",
    # ── Telecomunicazioni ────────────────────────────────────────
    "VZ":    "Verizon",
    # ── Big Tech ─────────────────────────────────────────────────
    "AAPL":  "Apple",
    "MSFT":  "Microsoft",
    "NVDA":  "Nvidia",
    "GOOGL": "Alphabet",
    "META":  "Meta",
    "AMZN":  "Amazon",
    "TSLA":  "Tesla",
    "AVGO":  "Broadcom",
    "CSCO":  "Cisco",
    # ── Chip & Semiconduttori ─────────────────────────────────────
    "AMD":   "AMD",
    "QCOM":  "Qualcomm",
    "INTC":  "Intel",
    "MU":    "Micron",
    # ── Software & Cloud ─────────────────────────────────────────
    "ADBE":  "Adobe",
    "CRM":   "Salesforce",
    "IBM":   "IBM",
    "NFLX":  "Netflix",
    "PYPL":  "PayPal",
}

SETTORI_ENERGIA = {"CVX","XOM","OXY","COP","SLB"}
SETTORI_DIFESA  = {"BA","HON","RTX","LMT","NOC","GD"}
SETTORI_WAR_OIL = SETTORI_ENERGIA | SETTORI_DIFESA | {"NVDA","CSCO","CAT","GE"}

def get_settore(ticker):
    if ticker in SETTORI_ENERGIA: return "energia"
    if ticker in SETTORI_DIFESA:  return "difesa"
    return "altro"

# ──────────────────────────────────────────────────────────────────
# FUNZIONI INDICATORI
# ──────────────────────────────────────────────────────────────────
def calcola_rsi_serie(close, periodi=14):
    """Restituisce la serie RSI completa (non solo l'ultimo valore)."""
    try:
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(window=periodi, min_periods=periodi).mean()
        loss  = (-delta.clip(upper=0)).rolling(window=periodi, min_periods=periodi).mean()
        rs    = gain / loss.replace(0, 1e-9)
        return 100 - (100 / (1 + rs))
    except:
        return pd.Series([50.0] * len(close), index=close.index)

def calcola_rsi(close, periodi=14):
    return float(calcola_rsi_serie(close, periodi).iloc[-1])

def calcola_supporto(close):
    """
    Distanza % dal minimo 30gg (livello di supporto).
    Valori vicini a 0% = siamo sul supporto.
    """
    min_30d    = float(close.tail(30).min())
    p_fine     = float(close.iloc[-1])
    dist_sup   = (p_fine - min_30d) / min_30d  # 0% = sul supporto
    sul_sup    = dist_sup <= SUP_VICINO_SOGLIA
    return dist_sup, sul_sup, min_30d

def calcola_divergenza(close, rsi_serie):
    """
    Divergenza RSI su 10 giorni:
    - RIALZISTA (↗): prezzo scende, RSI sale → forza nascosta
    - RIBASSISTA (↘): prezzo sale, RSI scende → debolezza nascosta
    - NEUTRALE (·): nessuna divergenza
    Restituisce (label, bonus_score)
    """
    try:
        if len(close) < 11 or len(rsi_serie.dropna()) < 11:
            return "· NEUTR", 0

        price_10d = (float(close.iloc[-1]) - float(close.iloc[-11])) / float(close.iloc[-11])
        rsi_now   = float(rsi_serie.dropna().iloc[-1])
        rsi_10ago = float(rsi_serie.dropna().iloc[-11])
        rsi_10d   = rsi_now - rsi_10ago

        if price_10d <= DIV_PREZZO_MIN and rsi_10d >= DIV_RSI_MIN:
            return "↗ RIALZ", BONUS_DIV_RIALZ
        elif price_10d >= 0.02 and rsi_10d <= DIV_RSI_MAX:
            return "↘ RIBAS", MALUS_DIV_RIBAS
        else:
            return "· NEUTR", 0
    except:
        return "· NEUTR", 0

def calcola_rischio_entrata(rsi, dist_max, trend_3d, trend_5d, vix_alto):
    punti = 0
    if rsi > RSI_IPERCOMPRATO:       punti += 2
    elif rsi < RSI_IPERVENDUTO:      punti -= 1
    if dist_max > -0.03:             punti += 2
    elif dist_max > -0.08:           punti += 1
    if trend_5d != 0 and abs(trend_3d / trend_5d) > ACCEL_SOGLIA and trend_3d > 0:
        punti += 2
    if vix_alto:                     punti += 1

    if punti >= 4:   return "🔴 ALTO",  -18
    elif punti >= 2: return "🟡 MEDIO", -8
    else:            return "🟢 BASSO",  0

def calcola_score(trend_5d, trend_30d, vol_ratio, is_stabile,
                  is_war_oil, oil_favorevole, rsi, penalita_rischio,
                  vix_alto, bonus_sup_div):
    score = 0.0

    # Trend 5gg (max 30)
    if trend_5d >= 0.08:    score += 30
    elif trend_5d >= 0.05:  score += 24
    elif trend_5d >= 0.03:  score += 17
    elif trend_5d >= 0.01:  score += 10
    elif trend_5d >= 0:     score += 5
    else:                   score += max(0, 5 + trend_5d * 80)

    # Trend 30gg (max 25)
    if trend_30d >= 0.15:    score += 25
    elif trend_30d >= 0.05:  score += 18
    elif trend_30d >= 0:     score += 12
    elif trend_30d >= -0.05: score += 6

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

    # ── NUOVO v2: bonus supporto + divergenza ────────────────────
    score += bonus_sup_div

    return round(max(0, min(score, 100)), 1)

def score_to_rating(score, trend_5d):
    if score >= 75 and trend_5d > 0.05:   return "🔥 STRONG BUY"
    elif score >= 60 and trend_5d > 0.02: return "💚 BUY"
    elif score >= 45 and trend_5d >= 0:   return "📈 ACCUMULATE"
    elif score >= 30:                      return "🟡 HOLD"
    else:                                  return "🔻 AVOID"

def calcola_bonus_sup_div(sul_supporto, div_label, div_bonus):
    """Combina supporto e divergenza in un bonus unico."""
    if sul_supporto and div_label == "↗ RIALZ":
        return BONUS_SUP_DIV       # massimo bonus: entrambi positivi
    elif sul_supporto:
        return BONUS_SUP_SOLO      # solo supporto
    elif div_label == "↗ RIALZ":
        return BONUS_DIV_RIALZ     # solo divergenza rialzista
    else:
        return div_bonus           # divergenza ribassista o neutrale

# ──────────────────────────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────────────────────────
print()
print("╔══════════════════════════════════════════════════════════════════╗")
print(f"║   🇺🇸  WAR-SENTINEL_USA_V2                                      ║")
print(f"║   📅  {datetime.now().strftime('%d/%m/%Y  %H:%M')}                                         ║")
print(f"║   👤  {COSTRUTTORE}                         ║")
print("╚══════════════════════════════════════════════════════════════════╝")
print("   v2: +Supporto 30gg + Divergenza RSI 10gg")

# ──────────────────────────────────────────────────────────────────
# STEP 1 — MACRO CONTEXT
# ──────────────────────────────────────────────────────────────────
print("\n📡 Scarico indicatori macro USA...")

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

try:
    vix_data = yf.download(VIX_TICKER, period="5d", progress=False)['Close']
    if isinstance(vix_data, pd.DataFrame): vix_data = vix_data.iloc[:, 0]
    vix_fine = float(vix_data.dropna().iloc[-1])
    vix_alto = vix_fine > VIX_ALERT
    icona = "🔴" if vix_fine > 30 else ("🟡" if vix_fine > VIX_ALERT else "🟢")
    print(f"   {icona}  VIX       : {vix_fine:.1f}  {'⚠️ MERCATO NERVOSO' if vix_alto else '✅ Stabile'}")
except:
    vix_fine = 20.0; vix_alto = False
    print("   ⚠️  VIX non disponibile")

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
stato_vix = "NERVOSO ⚠️"   if vix_alto      else "STABILE ✅"
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

        # RSI serie completa
        rsi_serie = calcola_rsi_serie(close, 14)
        rsi       = float(rsi_serie.dropna().iloc[-1])

        # D.MAX
        max_30d  = float(close.tail(30).max())
        dist_max = (p_fine - max_30d) / max_30d

        # ── NUOVI v2 ─────────────────────────────────────────────
        # Supporto
        dist_sup, sul_supporto, min_30d = calcola_supporto(close)

        # Divergenza RSI
        div_label, div_bonus = calcola_divergenza(close, rsi_serie)

        # Bonus combinato supporto + divergenza
        bonus_sup_div = calcola_bonus_sup_div(sul_supporto, div_label, div_bonus)

        # Rischio entrata
        rischio_str, penalita = calcola_rischio_entrata(
            rsi, dist_max, trend_3d, trend_5d, vix_alto)

        is_war_oil = ticker in SETTORI_WAR_OIL
        settore    = get_settore(ticker)

        score = calcola_score(
            trend_5d, trend_30d, vol_ratio, is_stabile,
            is_war_oil, oil_favorevole, rsi, penalita,
            vix_alto, bonus_sup_div)
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
        print(f"\n{'═'*88}")
        print(f"  {cat}  ({len(subset)} titoli)")
        print(f"{'═'*88}")
        cols = ["TICKER","NOME","PREZZO","T5gg","T30gg","VOL/AVG",
                "RSI","D.MAX","SUP","DIV","RISCHIO","SCORE","RATING"]
        print(subset[cols].to_string(index=False))

    # ──────────────────────────────────────────────────────────────
    # STEP 4 — TOP 6 CON CAP SETTORIALE
    # ──────────────────────────────────────────────────────────────
    print(f"\n\n{'★'*88}")
    print(f"  🏆  TOP {TOP_N} CANDIDATI USA  —  CLASSIFICA FINALE  (cap settoriale attivo)")
    print(f"  🛢️  Brent: {oil_fine:.2f} USD ({oil_trend:+.2%})  |  {stato_oil}")
    print(f"  📊  VIX: {vix_fine:.1f}  |  {stato_vix}")
    print(f"  💵  DXY: {dxy_fine:.2f} ({dxy_trend:+.2%})  |  S&P500: {sp_fine:.2f} ({sp_trend:+.2%})")
    print(f"  📅  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"  ⚠️   Cap: max {MAX_ENERGIA_TOP6} energia | max {MAX_DIFESA_TOP6} difesa")
    print(f"{'★'*88}")
    print()

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

    header = (f"  {'#':>2}  {'TICKER':<6} {'NOME':<22} {'PREZZO':>9}  "
              f"{'T5gg':>7}  {'T30gg':>7}  {'RSI':>4}  "
              f"{'D.MAX':>6}  {'SUP':>5}  {'DIV':<8}  "
              f"{'RISCHIO':<14}  {'SCORE':>5}  RATING")
    sep = "  " + "─" * (len(header) - 2)
    print(header)
    print(sep)

    for i, row in enumerate(top6_righe, 1):
        print(
            f"  {i:>2}  "
            f"{row['TICKER']:<6} "
            f"{row['NOME']:<22} "
            f"{row['PREZZO']:>9}  "
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
    print("  LEGENDA NUOVI PARAMETRI v2:")
    print("  SUP  : distanza % dal minimo 30gg (supporto)")
    print(f"         ≤+{SUP_VICINO_SOGLIA*100:.0f}% = SUL SUPPORTO → bonus +{BONUS_SUP_SOLO}pt")
    print("  DIV  : divergenza RSI 10gg")
    print(f"         ↗ RIALZ = prezzo↓ + RSI↑ → bonus +{BONUS_DIV_RIALZ}pt (setup rimbalzo)")
    print(f"         ↘ RIBAS = prezzo↑ + RSI↓ → malus {MALUS_DIV_RIBAS}pt (momentum debole)")
    print(f"         · NEUTR = nessuna divergenza")
    print(f"  SUP+DIV insieme → bonus massimo +{BONUS_SUP_DIV}pt")
    print()
    print("  LEGENDA ALTRI PARAMETRI:")
    print("  RSI    : >70=ipercomprato(-5pt) | <30=ipervenduto(+5pt)")
    print("  D.MAX  : distanza % dal massimo 30gg (0%=sul massimo=rischio)")
    print("  RISCHIO: 🟢BASSO=0pt | 🟡MEDIO=-8pt | 🔴ALTO=-18pt")
    print("  VIX>25 : +1pt rischio su ogni titolo")
    print()
    print("  SCORE USA: trend5(30)+trend30(25)+vol(15)+stab(15)+war-oil(10)")
    print("             +RSI(±5)+penalità(0/-8/-18)+SUP/DIV(0/+4/+8/-5)")

    print(f"\n{'─'*88}")
    print(f"  📊  Titoli analizzati : {len(risultati)}/{len(USA)}")
    if errori:
        print(f"  ⚠️   Ticker errori : {', '.join(errori)}")

print(f"\n{'═'*88}")
print(f"  REFERENZA : {COSTRUTTORE}  |  WAR-SENTINEL_USA_V2")
print(f"  ESEGUITO  : {datetime.now().strftime('%d/%m/%Y alle %H:%M:%S')}")
print(f"{'═'*88}\n")

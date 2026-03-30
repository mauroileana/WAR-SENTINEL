import yfinance as yf
import pandas as pd
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

# ──────────────────────────────────────────────────────────────────
# CONFIGURAZIONE
# ──────────────────────────────────────────────────────────────────
COSTRUTTORE          = "BESIO MAURO-10/01/1956"
OIL_TICKER           = "BZ=F"
EURUSD_TICKER        = "EURUSD=X"
STOXX50_TICKER       = "^STOXX50E"

# Soglie base
VOL_SOGLIA_RATIO     = 1.5
STAB_SOGLIA          = 1.3
TREND_MIN_RESILIENTE = -0.04
OIL_TREND_SOGLIA     = 0.01
EURUSD_SOGLIA        = -0.01
TOP_N                = 6

# ── Soglie NUOVI parametri anti-rischio ──────────────────────────
RSI_IPERCOMPRATO     = 70     # RSI > 70 → penalità score
RSI_IPERVENDUTO      = 30     # RSI < 30 → bonus score
DIST_MAX_SOGLIA      = -0.05  # se prezzo < 5% sotto il max30gg → zona rischio
ACCEL_SOGLIA         = 1.8    # se trend3gg > trend5d * 1.8 → parabola rischiosa

# ── Cap settoriale nel TOP6 ───────────────────────────────────────
MAX_PETROLIO_TOP6    = 3      # max 3 titoli petrolio/energia nel TOP6
MAX_DIFESA_TOP6      = 2      # max 2 titoli difesa nel TOP6

# ──────────────────────────────────────────────────────────────────
# PANIERE EUROPA — ~60 titoli verificati
# ──────────────────────────────────────────────────────────────────
EUROPA = {
    # ── ENERGIA & PETROLIO ──────────────────────────────────────
    "TTE.PA":   "TotalEnergies",
    "SHEL.L":   "Shell",
    "BP.L":     "BP",
    "EQNR.OL":  "Equinor",
    "REP.MC":   "Repsol",
    "NESTE.HE": "Neste",

    # ── DIFESA & AEROSPAZIO ──────────────────────────────────────
    "RHM.DE":   "Rheinmetall",
    "BA.L":     "BAE Systems",
    "AIR.PA":   "Airbus",
    "HO.PA":    "Thales",
    "SAF.PA":   "Safran",
    "RR.L":     "Rolls-Royce",
    "HAG.DE":   "Hensoldt",

    # ── INDUSTRIA PESANTE & INFRASTRUTTURE ──────────────────────
    "SIE.DE":   "Siemens",
    "ABBN.SW":  "ABB",
    "SU.PA":    "Schneider Electric",
    "SGO.PA":   "Saint-Gobain",
    "MT.AS":    "ArcelorMittal",
    "VOW3.DE":  "Volkswagen",
    "BMW.DE":   "BMW",
    "MBG.DE":   "Mercedes-Benz",
    "STLAM.MI": "Stellantis",

    # ── BANCHE & FINANZA ────────────────────────────────────────
    "HSBA.L":   "HSBC",
    "BNP.PA":   "BNP Paribas",
    "DBK.DE":   "Deutsche Bank",
    "SAN.MC":   "Santander",
    "INGA.AS":  "ING Group",
    "ACA.PA":   "Crédit Agricole",
    "GLE.PA":   "Société Générale",
    "BBVA.MC":  "BBVA",
    "UCG.MI":   "UniCredit",

    # ── ASSICURAZIONI ───────────────────────────────────────────
    "ALV.DE":   "Allianz",
    "MUV2.DE":  "Munich Re",
    "CS.PA":    "AXA",

    # ── UTILITIES & RINNOVABILI ──────────────────────────────────
    "ENEL.MI":  "Enel",
    "IBE.MC":   "Iberdrola",
    "RWE.DE":   "RWE",
    "EOAN.DE":  "E.ON",
    "VIE.PA":   "Veolia",
    "ORSTED.CO":"Ørsted",
    "EDP.LS":   "EDP",

    # ── TECNOLOGIA & SEMICONDUTTORI ──────────────────────────────
    "ASML.AS":  "ASML",
    "SAP.DE":   "SAP",
    "STMPA.PA": "STMicroelectronics",

    # ── FARMACEUTICA & HEALTHCARE ────────────────────────────────
    "NOVN.SW":  "Novartis",
    "ROG.SW":   "Roche",
    "AZN.L":    "AstraZeneca",
    "SAN.PA":   "Sanofi",
    "BAYN.DE":  "Bayer",

    # ── CONSUMER & LUSSO ────────────────────────────────────────
    "MC.PA":    "LVMH",
    "RMS.PA":   "Hermès",
    "OR.PA":    "L'Oréal",
    "NESN.SW":  "Nestlé",
    "UNA.AS":   "Unilever",

    # ── TELECOMUNICAZIONI ────────────────────────────────────────
    "DTE.DE":   "Deutsche Telekom",
    "TEF.MC":   "Telefónica",
    "ORA.PA":   "Orange",
}

# Classificazione settori per cap
SETTORI_PETROLIO = {"TTE.PA","SHEL.L","BP.L","EQNR.OL","REP.MC","NESTE.HE"}
SETTORI_DIFESA   = {"RHM.DE","BA.L","AIR.PA","HO.PA","SAF.PA","RR.L","HAG.DE"}
SETTORI_WAR_OIL  = SETTORI_PETROLIO | SETTORI_DIFESA | {"MT.AS","ASML.AS","ABBN.SW"}

def get_settore(ticker):
    if ticker in SETTORI_PETROLIO: return "petrolio"
    if ticker in SETTORI_DIFESA:   return "difesa"
    return "altro"

def get_borsa(ticker):
    if ".PA" in ticker:   return "🇫🇷"
    elif ".DE" in ticker: return "🇩🇪"
    elif ".L"  in ticker: return "🇬🇧"
    elif ".AS" in ticker: return "🇳🇱"
    elif ".MC" in ticker: return "🇪🇸"
    elif ".SW" in ticker: return "🇨🇭"
    elif ".MI" in ticker: return "🇮🇹"
    elif ".OL" in ticker: return "🇳🇴"
    elif ".CO" in ticker: return "🇩🇰"
    elif ".LS" in ticker: return "🇵🇹"
    elif ".HE" in ticker: return "🇫🇮"
    else:                  return "🌍"

# ──────────────────────────────────────────────────────────────────
# FUNZIONI NUOVI INDICATORI v2
# ──────────────────────────────────────────────────────────────────
def calcola_rsi(close, periodi=14):
    """RSI classico a N periodi."""
    try:
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(window=periodi, min_periods=periodi).mean()
        loss  = (-delta.clip(upper=0)).rolling(window=periodi, min_periods=periodi).mean()
        rs    = gain / loss.replace(0, 1e-9)
        rsi   = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])
    except:
        return 50.0  # valore neutro se errore

def calcola_rischio_entrata(rsi, dist_max, trend_3d, trend_5d):
    """
    Combina tre segnali di rischio in un giudizio unico.
    Restituisce: (livello_str, punti_penalità)
      BASSO  → 0 penalità
      MEDIO  → -8 penalità sullo score
      ALTO   → -18 penalità sullo score
    """
    punti_rischio = 0

    # RSI ipercomprato
    if rsi > RSI_IPERCOMPRATO:
        punti_rischio += 2        # RSI > 70 → +2 rischio
    elif rsi < RSI_IPERVENDUTO:
        punti_rischio -= 1        # RSI < 30 → meno rischio

    # Vicino al massimo 30gg (overextension)
    if dist_max > -0.03:          # dentro il 3% dal massimo
        punti_rischio += 2
    elif dist_max > -0.08:        # tra 3% e 8% dal massimo
        punti_rischio += 1

    # Accelerazione parabola
    if trend_5d != 0 and abs(trend_3d / trend_5d) > ACCEL_SOGLIA and trend_3d > 0:
        punti_rischio += 2        # trend sta accelerando → rischio spike

    if punti_rischio >= 4:
        return "🔴 ALTO",  -18
    elif punti_rischio >= 2:
        return "🟡 MEDIO", -8
    else:
        return "🟢 BASSO",  0

# ──────────────────────────────────────────────────────────────────
# FUNZIONE SCORE  (0 – 100)  + penalità rischio
# ──────────────────────────────────────────────────────────────────
def calcola_score(trend_5d, trend_30d, vol_ratio, is_stabile,
                  is_war_oil, oil_favorevole, eurusd_ok,
                  rsi, penalita_rischio):
    score = 0.0

    # Trend 5gg (max 30)
    if trend_5d >= 0.08:    score += 30
    elif trend_5d >= 0.05:  score += 24
    elif trend_5d >= 0.03:  score += 17
    elif trend_5d >= 0.01:  score += 10
    elif trend_5d >= 0:     score += 5
    else:                   score += max(0, 5 + trend_5d * 80)

    # Trend 30gg (max 20)
    if trend_30d >= 0.15:    score += 20
    elif trend_30d >= 0.05:  score += 15
    elif trend_30d >= 0:     score += 10
    elif trend_30d >= -0.05: score += 5

    # Volumi (max 20)
    if vol_ratio >= 2.5:    score += 20
    elif vol_ratio >= 2.0:  score += 16
    elif vol_ratio >= 1.5:  score += 12
    elif vol_ratio >= 1.0:  score += 7
    else:                   score += 3

    # Stabilità (max 15)
    if is_stabile: score += 15

    # Bonus WAR-OIL (max 10)
    if is_war_oil and oil_favorevole: score += 10

    # Bonus EUR/USD (max 5)
    if eurusd_ok: score += 5

    # RSI bonus/penalità (max ±5)
    if rsi < RSI_IPERVENDUTO:    score += 5   # occasione
    elif rsi > RSI_IPERCOMPRATO: score -= 5   # attenzione

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
print(f"║   🌍  WAR-SENTINEL_EUROPA_STOXX_V2                              ║")
print(f"║   📅  {datetime.now().strftime('%d/%m/%Y  %H:%M')}                                         ║")
print(f"║   👤  {COSTRUTTORE}                          ║")
print("╚══════════════════════════════════════════════════════════════════╝")
print("   v2: RSI + Overextension + Momentum + Cap Settoriale TOP6")

# ──────────────────────────────────────────────────────────────────
# STEP 1 — MACRO CONTEXT
# ──────────────────────────────────────────────────────────────────
print("\n📡 Scarico indicatori macro europei...")

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
    fx_data = yf.download(EURUSD_TICKER, period="10d", progress=False)['Close']
    if isinstance(fx_data, pd.DataFrame): fx_data = fx_data.iloc[:, 0]
    fx_data = fx_data.dropna()
    fx_fine    = float(fx_data.iloc[-1])
    fx_trend   = (fx_fine - float(fx_data.iloc[0])) / float(fx_data.iloc[0])
    eurusd_ok  = fx_trend > EURUSD_SOGLIA
    icona = "🟢" if fx_trend > 0.005 else ("🟡" if fx_trend > EURUSD_SOGLIA else "🔴")
    print(f"   {icona}  EUR/USD   : {fx_fine:.4f}  |  Trend 10gg: {fx_trend:+.2%}  {'✅' if eurusd_ok else '⛔'}")
except:
    fx_trend = 0.0; eurusd_ok = True; fx_fine = 0.0
    print("   ⚠️  EUR/USD non disponibile")

try:
    stoxx_data = yf.download(STOXX50_TICKER, period="10d", progress=False)['Close']
    if isinstance(stoxx_data, pd.DataFrame): stoxx_data = stoxx_data.iloc[:, 0]
    stoxx_data = stoxx_data.dropna()
    stoxx_fine  = float(stoxx_data.iloc[-1])
    stoxx_trend = (stoxx_fine - float(stoxx_data.iloc[0])) / float(stoxx_data.iloc[0])
    icona = "🟢" if stoxx_trend > 0.01 else ("🟡" if stoxx_trend > 0 else "🔴")
    print(f"   {icona}  STOXX 50  : {stoxx_fine:.2f}  |  Trend 10gg: {stoxx_trend:+.2%}")
except:
    stoxx_trend = 0.0; stoxx_fine = 0.0
    print("   ⚠️  STOXX50 non disponibile")

stato_oil    = "FAVOREVOLE ✅" if oil_favorevole else "NEUTRO/NEG ⛔"
stato_eurusd = "STABILE ✅"    if eurusd_ok      else "DEBOLE ⛔"
print(f"\n   Contesto oil: {stato_oil}  |  EUR/USD: {stato_eurusd}")

# ──────────────────────────────────────────────────────────────────
# STEP 2 — SCANSIONE
# ──────────────────────────────────────────────────────────────────
print(f"\n🔍 Scansione {len(EUROPA)} titoli Europa in corso...\n")

risultati = []
errori    = []

for ticker, nome in EUROPA.items():
    try:
        # Scarico 60gg per avere abbastanza dati per RSI 14
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
        p_inizio  = float(close.tail(30).iloc[0])   # 30gg effettivi
        trend_5d  = (p_fine - p_5gg)    / p_5gg
        trend_3d  = (p_fine - p_3gg)    / p_3gg
        trend_30d = (p_fine - p_inizio) / p_inizio

        std_5d    = float(close.tail(5).std())
        std_30d   = float(close.tail(30).std())
        is_stabile = std_5d < (std_30d * STAB_SOGLIA)

        vol_oggi  = float(volume.iloc[-1])
        vol_medio = float(volume.tail(30).mean())
        vol_ratio = vol_oggi / vol_medio if vol_medio > 0 else 0

        # ── NUOVI INDICATORI v2 ──────────────────────────────────

        # 1. RSI 14
        rsi = calcola_rsi(close, 14)

        # 2. Distanza dal massimo 30gg
        max_30d  = float(close.tail(30).max())
        dist_max = (p_fine - max_30d) / max_30d  # 0 = sul massimo, -0.1 = -10% dal max

        # 3. Rischio entrata combinato
        rischio_str, penalita = calcola_rischio_entrata(rsi, dist_max, trend_3d, trend_5d)

        is_war_oil = ticker in SETTORI_WAR_OIL
        settore    = get_settore(ticker)
        borsa      = get_borsa(ticker)

        # Score con nuovi parametri
        score  = calcola_score(trend_5d, trend_30d, vol_ratio,
                               is_stabile, is_war_oil,
                               oil_favorevole, eurusd_ok,
                               rsi, penalita)
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
            "TICKER":    ticker,
            "PAESE":     borsa,
            "NOME":      nome,
            "PREZZO":    f"{p_fine:.2f}",
            "T5gg":      f"{trend_5d:+.2%}",
            "T30gg":     f"{trend_30d:+.2%}",
            "VOL/AVG":   f"{vol_ratio:.1f}x",
            "RSI":       f"{rsi:.0f}",
            "D.MAX":     f"{dist_max:+.1%}",
            "RISCHIO":   rischio_str,
            "STABILE":   "SI" if is_stabile else "NO",
            "WAR-OIL":   "⚑" if is_war_oil else "·",
            "SCORE":     score,
            "RATING":    rating,
            "VERDETTO":  verdetto,
            "_settore":  settore,
            "_t5":       trend_5d,
            "_t30":      trend_30d,
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
        print(f"\n{'═'*84}")
        print(f"  {cat}  ({len(subset)} titoli)")
        print(f"{'═'*84}")
        cols = ["TICKER","PAESE","NOME","PREZZO","T5gg","T30gg",
                "VOL/AVG","RSI","D.MAX","RISCHIO","SCORE","RATING"]
        print(subset[cols].to_string(index=False))

    # ──────────────────────────────────────────────────────────────
    # STEP 4 — TOP 6 CON CAP SETTORIALE
    # ──────────────────────────────────────────────────────────────
    print(f"\n\n{'★'*84}")
    print(f"  🏆  TOP {TOP_N} CANDIDATI EUROPA  —  CLASSIFICA FINALE  (cap settoriale attivo)")
    print(f"  🛢️  Brent: {oil_fine:.2f} USD ({oil_trend:+.2%})  |  {stato_oil}")
    print(f"  💶  EUR/USD: {fx_fine:.4f} ({fx_trend:+.2%})  |  {stato_eurusd}")
    print(f"  📊  STOXX 50: {stoxx_fine:.2f} ({stoxx_trend:+.2%})")
    print(f"  📅  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"  ⚠️   Cap: max {MAX_PETROLIO_TOP6} petrolio | max {MAX_DIFESA_TOP6} difesa")
    print(f"{'★'*84}")
    print()

    # Selezione TOP6 con cap settoriale
    contatori  = {"petrolio": 0, "difesa": 0, "altro": 0}
    top6_righe = []
    for _, row in df.iterrows():
        s = row["_settore"]
        cap = MAX_PETROLIO_TOP6 if s == "petrolio" else (MAX_DIFESA_TOP6 if s == "difesa" else 99)
        if contatori[s] < cap:
            top6_righe.append(row)
            contatori[s] += 1
        if len(top6_righe) == TOP_N:
            break

    header = (f"  {'#':>2}  {'TICKER':<12} {'P':>3} {'NOME':<22} {'PREZZO':>8}  "
              f"{'T5gg':>7}  {'T30gg':>7}  {'RSI':>4}  {'D.MAX':>6}  "
              f"{'RISCHIO':<14}  {'SCORE':>5}  RATING")
    sep = "  " + "─" * (len(header) - 2)
    print(header)
    print(sep)

    for i, row in enumerate(top6_righe, 1):
        print(
            f"  {i:>2}  "
            f"{row['TICKER']:<12} "
            f"{row['PAESE']:>3} "
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
    print(f"  Distribuzione settoriale: "
          f"Petrolio={contatori['petrolio']}/3  "
          f"Difesa={contatori['difesa']}/2  "
          f"Altri={contatori['altro']}")
    print()
    print("  LEGENDA:")
    print("  RSI    : >70=ipercomprato(-5pt) | <30=ipervenduto(+5pt) | 30-70=neutro")
    print("  D.MAX  : distanza % dal massimo 30gg (0%=sul massimo = rischio alto)")
    print("  RISCHIO: 🟢BASSO=0pt | 🟡MEDIO=-8pt | 🔴ALTO=-18pt sullo score")
    print()
    print("  🔥 STRONG BUY → Score≥75 + T5>5%  |  💚 BUY → Score≥60 + T5>2%")
    print("  📈 ACCUMULATE → Score≥45 + T5≥0%  |  🟡 HOLD → Score≥30")
    print()
    print("  SCORE: trend5(30)+trend30(20)+vol(20)+stab(15)+war-oil(10)+fx(5)")
    print("         +RSI(±5) + penalità rischio(0/-8/-18)")

    print(f"\n{'─'*84}")
    print(f"  📊  Titoli analizzati : {len(risultati)}/{len(EUROPA)}")
    if errori:
        print(f"  ⚠️   Ticker errori : {', '.join(errori)}")

print(f"\n{'═'*84}")
print(f"  REFERENZA : {COSTRUTTORE}  |  WAR-SENTINEL_EUROPA_STOXX_V2")
print(f"  ESEGUITO  : {datetime.now().strftime('%d/%m/%Y alle %H:%M:%S')}")
print(f"{'═'*84}\n")

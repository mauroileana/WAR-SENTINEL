import yfinance as yf
import pandas as pd
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

# ──────────────────────────────────────────────────────────────────
# CONFIGURAZIONE GLOBALE
# ──────────────────────────────────────────────────────────────────
COSTRUTTORE      = "BESIO MAURO-10/01/1956"
OIL_TICKER       = "BZ=F"
VIX_TICKER       = "^VIX"
DXY_TICKER       = "DX-Y.NYB"
EURUSD_TICKER    = "EURUSD=X"
SP500_TICKER     = "^GSPC"
STOXX50_TICKER   = "^STOXX50E"

OIL_TREND_SOGLIA = 0.01
VIX_ALERT        = 25
TOP_N_GLOBAL     = 10   # titoli nella classifica globale

# Cap globale TOP10
MAX_ENERGIA_GLOBAL  = 3   # max 3 titoli energia/petrolio totali
MAX_DIFESA_GLOBAL   = 2   # max 2 titoli difesa totali
MAX_PER_MERCATO     = 3   # max 3 titoli per singolo mercato (IT/EU/USA)

# Soglie comuni
RSI_IPERCOMPRATO = 70
RSI_IPERVENDUTO  = 30
SUP_VICINO       = 0.04
DIV_PREZZO_MIN   = -0.02
DIV_RSI_MIN      = 2.0
DIV_RSI_MAX      = -2.0

BONUS_SUP_DIV    = +8
BONUS_SUP_SOLO   = +4
BONUS_DIV_RIALZ  = +4
MALUS_DIV_RIBAS  = -5

# ──────────────────────────────────────────────────────────────────
# PANIERI — tutti e tre i mercati
# ──────────────────────────────────────────────────────────────────

ITALIA = {
    "ENI.MI":"ENI","TEN.MI":"Tenaris","SPM.MI":"Saipem",
    "MAIRE.MI":"Maire Tecnimont","ERG.MI":"ERG",
    "LDO.MI":"Leonardo","IVG.MI":"Iveco Group",
    "UCG.MI":"UniCredit","ISP.MI":"Intesa Sanpaolo",
    "BAMI.MI":"Banco BPM","MB.MI":"Mediobanca",
    "BPE.MI":"BPER Banca","BMPS.MI":"Monte dei Paschi",
    "FBK.MI":"FinecoBank","BGN.MI":"Banca Generali",
    "G.MI":"Generali","UNI.MI":"Unipol",
    "STLAM.MI":"Stellantis","RACE.MI":"Ferrari",
    "PRY.MI":"Prysmian","BRE.MI":"Brembo",
    "DAN.MI":"Danieli","MONC.MI":"Moncler","AZM.MI":"Azimut",
    "ENEL.MI":"Enel","A2A.MI":"A2A","HER.MI":"Hera",
    "SRG.MI":"Snam","TRN.MI":"Terna","TIT.MI":"Telecom Italia",
    "REC.MI":"Recordati","AMP.MI":"Amplifon","DIA.MI":"DiaSorin",
    "DLG.MI":"De'Longhi","BC.MI":"Brunello Cucinelli",
    "INW.MI":"Inwit","TLS.MI":"Telecom Italia Risp.",
}

EUROPA = {
    "TTE.PA":"TotalEnergies","SHEL.L":"Shell","BP.L":"BP",
    "EQNR.OL":"Equinor","REP.MC":"Repsol","NESTE.HE":"Neste",
    "RHM.DE":"Rheinmetall","BA.L":"BAE Systems","AIR.PA":"Airbus",
    "HO.PA":"Thales","SAF.PA":"Safran","RR.L":"Rolls-Royce","HAG.DE":"Hensoldt",
    "SIE.DE":"Siemens","ABBN.SW":"ABB","SU.PA":"Schneider Electric",
    "SGO.PA":"Saint-Gobain","MT.AS":"ArcelorMittal",
    "VOW3.DE":"Volkswagen","BMW.DE":"BMW","MBG.DE":"Mercedes-Benz",
    "STLAM.MI":"Stellantis","HSBA.L":"HSBC","BNP.PA":"BNP Paribas",
    "DBK.DE":"Deutsche Bank","SAN.MC":"Santander","INGA.AS":"ING Group",
    "ACA.PA":"Crédit Agricole","GLE.PA":"Société Générale",
    "BBVA.MC":"BBVA","UCG.MI":"UniCredit",
    "ALV.DE":"Allianz","MUV2.DE":"Munich Re","CS.PA":"AXA",
    "ENEL.MI":"Enel","IBE.MC":"Iberdrola","RWE.DE":"RWE",
    "EOAN.DE":"E.ON","VIE.PA":"Veolia","ORSTED.CO":"Ørsted","EDP.LS":"EDP",
    "ASML.AS":"ASML","SAP.DE":"SAP","STMPA.PA":"STMicroelectronics",
    "NOVN.SW":"Novartis","ROG.SW":"Roche","AZN.L":"AstraZeneca",
    "SAN.PA":"Sanofi","BAYN.DE":"Bayer",
    "MC.PA":"LVMH","RMS.PA":"Hermès","OR.PA":"L'Oréal",
    "NESN.SW":"Nestlé","UNA.AS":"Unilever",
    "DTE.DE":"Deutsche Telekom","TEF.MC":"Telefónica","ORA.PA":"Orange",
}

USA = {
    "CVX":"Chevron","XOM":"ExxonMobil","OXY":"Occidental Petroleum",
    "COP":"ConocoPhillips","SLB":"SLB (Schlumberger)",
    "BA":"Boeing","HON":"Honeywell","RTX":"Raytheon",
    "LMT":"Lockheed Martin","NOC":"Northrop Grumman","GD":"General Dynamics",
    "CAT":"Caterpillar","MMM":"3M","GE":"GE Aerospace","SHW":"Sherwin-Williams",
    "JPM":"JPMorgan Chase","GS":"Goldman Sachs","AXP":"American Express",
    "V":"Visa","TRV":"Travelers",
    "JNJ":"Johnson & Johnson","MRK":"Merck","UNH":"UnitedHealth",
    "AMGN":"Amgen","GILD":"Gilead Sciences","REGN":"Regeneron","VRTX":"Vertex Pharma",
    "WMT":"Walmart","MCD":"McDonald's","HD":"Home Depot",
    "KO":"Coca-Cola","PG":"Procter & Gamble","NKE":"Nike",
    "DIS":"Disney","COST":"Costco","VZ":"Verizon",
    "AAPL":"Apple","MSFT":"Microsoft","NVDA":"Nvidia",
    "GOOGL":"Alphabet","META":"Meta","AMZN":"Amazon",
    "TSLA":"Tesla","AVGO":"Broadcom","CSCO":"Cisco",
    "AMD":"AMD","QCOM":"Qualcomm","INTC":"Intel","MU":"Micron",
    "ADBE":"Adobe","CRM":"Salesforce","IBM":"IBM",
    "NFLX":"Netflix","PYPL":"PayPal",
}

# Settori per cap globale
EN_IT = {"ENI.MI","TEN.MI","SPM.MI","MAIRE.MI","ERG.MI"}
EN_EU = {"TTE.PA","SHEL.L","BP.L","EQNR.OL","REP.MC","NESTE.HE"}
EN_US = {"CVX","XOM","OXY","COP","SLB"}
DIF_IT = {"LDO.MI","IVG.MI"}
DIF_EU = {"RHM.DE","BA.L","AIR.PA","HO.PA","SAF.PA","RR.L","HAG.DE"}
DIF_US = {"BA","HON","RTX","LMT","NOC","GD"}

ENERGIA_GLOBALE = EN_IT | EN_EU | EN_US
DIFESA_GLOBALE  = DIF_IT | DIF_EU | DIF_US

WAR_IT = EN_IT | DIF_IT | {"PRY.MI","SRG.MI","TRN.MI"}
WAR_EU = EN_EU | DIF_EU | {"MT.AS","ASML.AS","ABBN.SW"}
WAR_US = EN_US | DIF_US | {"NVDA","CSCO","CAT","GE"}

def get_settore_globale(ticker):
    if ticker in ENERGIA_GLOBALE: return "energia"
    if ticker in DIFESA_GLOBALE:  return "difesa"
    return "altro"

def get_borsa(ticker):
    if ".MI" in ticker: return "🇮🇹"
    if ".PA" in ticker: return "🇫🇷"
    if ".DE" in ticker: return "🇩🇪"
    if ".L"  in ticker: return "🇬🇧"
    if ".AS" in ticker: return "🇳🇱"
    if ".MC" in ticker: return "🇪🇸"
    if ".SW" in ticker: return "🇨🇭"
    if ".OL" in ticker: return "🇳🇴"
    if ".CO" in ticker: return "🇩🇰"
    if ".LS" in ticker: return "🇵🇹"
    if ".HE" in ticker: return "🇫🇮"
    return "🇺🇸"

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
        return pd.Series([50.0]*len(close), index=close.index)

def calcola_supporto(close):
    min_30d  = float(close.tail(30).min())
    p_fine   = float(close.iloc[-1])
    dist_sup = (p_fine - min_30d) / min_30d
    return dist_sup, dist_sup <= SUP_VICINO

def calcola_divergenza(close, rsi_serie):
    try:
        rc = rsi_serie.dropna()
        if len(close) < 11 or len(rc) < 11: return "· NEUTR", 0
        p10 = (float(close.iloc[-1]) - float(close.iloc[-11])) / float(close.iloc[-11])
        r10 = float(rc.iloc[-1]) - float(rc.iloc[-11])
        if p10 <= DIV_PREZZO_MIN and r10 >= DIV_RSI_MIN:  return "↗ RIALZ", BONUS_DIV_RIALZ
        elif p10 >= 0.02 and r10 <= DIV_RSI_MAX:          return "↘ RIBAS", MALUS_DIV_RIBAS
        else:                                               return "· NEUTR", 0
    except:
        return "· NEUTR", 0

def calcola_bonus_sup_div(sul_sup, div_label, div_bonus):
    if sul_sup and div_label == "↗ RIALZ": return BONUS_SUP_DIV
    elif sul_sup:                           return BONUS_SUP_SOLO
    elif div_label == "↗ RIALZ":           return BONUS_DIV_RIALZ
    else:                                   return div_bonus

def calcola_rischio(rsi, dist_max, trend_3d, trend_5d, accel, extra_punti=0):
    p = extra_punti
    if rsi > RSI_IPERCOMPRATO:   p += 2
    elif rsi < RSI_IPERVENDUTO:  p -= 1
    if dist_max > -0.03:         p += 2
    elif dist_max > -0.08:       p += 1
    if trend_5d != 0 and abs(trend_3d/trend_5d) > accel and trend_3d > 0: p += 2
    if p >= 4:   return "🔴 ALTO",  -18
    elif p >= 2: return "🟡 MEDIO", -8
    else:        return "🟢 BASSO",  0

def calcola_score_it(t5, t30, vol, stab, war, oil_ok, rsi, pen, bsd):
    s = 0.0
    s += 35 if t5>=0.08 else 28 if t5>=0.05 else 20 if t5>=0.03 else 12 if t5>=0.01 else 6 if t5>=0 else max(0,6+t5*100)
    s += 20 if t30>=0.15 else 15 if t30>=0.05 else 10 if t30>=0 else 5 if t30>=-0.05 else 0
    s += 15 if vol>=2.0 else 12 if vol>=1.5 else 9 if vol>=1.3 else 5 if vol>=1.0 else 2
    if stab: s += 15
    if war and oil_ok: s += 10
    if rsi < RSI_IPERVENDUTO: s += 5
    elif rsi > RSI_IPERCOMPRATO: s -= 5
    return round(max(0, min(s + pen + bsd, 100)), 1)

def calcola_score_eu(t5, t30, vol, stab, war, oil_ok, fx_ok, rsi, pen, bsd):
    s = 0.0
    s += 30 if t5>=0.08 else 24 if t5>=0.05 else 17 if t5>=0.03 else 10 if t5>=0.01 else 5 if t5>=0 else max(0,5+t5*80)
    s += 20 if t30>=0.15 else 15 if t30>=0.05 else 10 if t30>=0 else 5 if t30>=-0.05 else 0
    s += 20 if vol>=2.5 else 16 if vol>=2.0 else 12 if vol>=1.5 else 7 if vol>=1.0 else 3
    if stab: s += 15
    if war and oil_ok: s += 10
    if fx_ok: s += 5
    if rsi < RSI_IPERVENDUTO: s += 5
    elif rsi > RSI_IPERCOMPRATO: s -= 5
    return round(max(0, min(s + pen + bsd, 100)), 1)

def calcola_score_us(t5, t30, vol, stab, war, oil_ok, rsi, pen, bsd):
    s = 0.0
    s += 30 if t5>=0.08 else 24 if t5>=0.05 else 17 if t5>=0.03 else 10 if t5>=0.01 else 5 if t5>=0 else max(0,5+t5*80)
    s += 25 if t30>=0.15 else 18 if t30>=0.05 else 12 if t30>=0 else 6 if t30>=-0.05 else 0
    s += 15 if vol>=3.0 else 12 if vol>=2.5 else 9 if vol>=2.0 else 5 if vol>=1.5 else 2
    if stab: s += 15
    if war and oil_ok: s += 10
    if rsi < RSI_IPERVENDUTO: s += 5
    elif rsi > RSI_IPERCOMPRATO: s -= 5
    return round(max(0, min(s + pen + bsd, 100)), 1)

def score_to_rating(score, t5):
    if score >= 75 and t5 > 0.05:   return "🔥 STRONG BUY"
    elif score >= 60 and t5 > 0.02: return "💚 BUY"
    elif score >= 45 and t5 >= 0:   return "📈 ACCUMULATE"
    elif score >= 30:                return "🟡 HOLD"
    else:                            return "🔻 AVOID"

def scansiona(paniere, mercato, vol_soglia, accel, war_oil_set,
              oil_ok, fx_ok=True, vix_alto=False):
    risultati = []
    errori    = []
    for ticker, nome in paniere.items():
        try:
            raw = yf.download(ticker, period="60d", progress=False, auto_adjust=True)
            if raw.empty: errori.append(ticker); continue
            close  = raw['Close']
            volume = raw['Volume']
            if isinstance(close,  pd.DataFrame): close  = close.iloc[:,0]
            if isinstance(volume, pd.DataFrame): volume = volume.iloc[:,0]
            close  = close.dropna(); volume = volume.dropna()
            if len(close) < 20: errori.append(ticker); continue

            p  = float(close.iloc[-1])
            p5 = float(close.iloc[-6])
            p3 = float(close.iloc[-4])
            p0 = float(close.tail(30).iloc[0])
            t5  = (p - p5) / p5
            t3  = (p - p3) / p3
            t30 = (p - p0) / p0

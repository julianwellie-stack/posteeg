import streamlit as st
from dataclasses import dataclass
from typing import Optional, List, Dict
import pandas as pd

# -------------------------------------------------------
# Hilfsfunktionen
# -------------------------------------------------------

def euro_per_kwh_from_cent(cent: float) -> float:
    return cent / 100.0

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def compute_self_consumed_kwh(generation_kwh: float, consumption_kwh: float, self_pct: float) -> float:
    """Eigenverbrauch bezogen auf Erzeugung, begrenzt durch maximalen Verbrauch."""
    self_pct = clamp(self_pct, 0.0, 100.0)
    target_self = generation_kwh * (self_pct / 100.0)
    return min(target_self, consumption_kwh)

def payback_years(invest: float, annual_cashflow: float) -> Optional[float]:
    if invest <= 0:
        return 0.0
    if annual_cashflow <= 0:
        return None
    return invest / annual_cashflow

def fmt_eur(x: float) -> str:
    s = f"{x:,.0f} €"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_years(x: Optional[float]) -> str:
    if x is None:
        return "—"
    return f"{x:.1f} J"

# -------------------------------------------------------
# Ergebnisstruktur
# -------------------------------------------------------

@dataclass
class Result:
    name: str
    invest_eur: float
    annual_cashflow_eur: float
    total_10y_eur: float
    total_20y_eur: float
    payback_years: Optional[float]

# -------------------------------------------------------
# Variantenberechnungen
# -------------------------------------------------------

def variant1_full_feed_in(generation_kwh: float, market_value_cent: float) -> Result:
    """Variante 1: Weiterbetrieb als Volleinspeiser (Marktwert)"""
    mv = euro_per_kwh_from_cent(market_value_cent)
    annual = generation_kwh * mv
    invest = 0.0
    return Result(
        name="V1 Volleinspeisung (Marktwert)",
        invest_eur=invest,
        annual_cashflow_eur=annual,
        total_10y_eur=10 * annual,
        total_20y_eur=20 * annual,
        payback_years=payback_years(invest, annual),
    )

def variant_self_consumption(
    name: str,
    generation_kwh: float,
    consumption_kwh: float,
    self_pct: float,
    invest_eur: float,
    retail_cent: float,
    export_cent: float
) -> Result:
    """Variante 2/3: Eigenverbrauch, Rest Einspeisung (Marktwert)"""
    retail = euro_per_kwh_from_cent(retail_cent)
    export_price = euro_per_kwh_from_cent(export_cent)

    self_kwh = compute_self_consumed_kwh(generation_kwh, consumption_kwh, self_pct)
    export_kwh = max(0.0, generation_kwh - self_kwh)

    annual = self_kwh * retail + export_kwh * export_price

    return Result(
        name=name,
        invest_eur=invest_eur,
        annual_cashflow_eur=annual,
        total_10y_eur=-invest_eur + 10 * annual,
        total_20y_eur=-invest_eur + 20 * annual,
        payback_years=payback_years(invest_eur, annual),
    )

def variant4_new_system(
    new_generation_kwh: float,
    consumption_kwh: float,
    self_pct: float,
    invest_eur: float,
    retail_cent: float,
    eeg_cent: float
) -> Result:
    """Variante 4: neue Anlage: EV + EEG-Vergütung für Einspeisung"""
    retail = euro_per_kwh_from_cent(retail_cent)
    eeg = euro_per_kwh_from_cent(eeg_cent)

    self_kwh = compute_self_consumed_kwh(new_generation_kwh, consumption_kwh, self_pct)
    export_kwh = max(0.0, new_generation_kwh - self_kwh)

    annual = self_kwh * retail + export_kwh * eeg

    return Result(
        name="V4 Neuanlage (EEG + EV)",
        invest_eur=invest_eur,
        annual_cashflow_eur=annual,
        total_10y_eur=-invest_eur + 10 * annual,
        total_20y_eur=-invest_eur + 20 * annual,
        payback_years=payback_years(invest_eur, annual),
    )

# -------------------------------------------------------
# Streamlit UI + Print Styles (A4)
# -------------------------------------------------------

st.set_page_config(page_title="Post-EEG Vergleichsrechner", layout="wide")

st.markdown(
    """
<style>
/* A4-freundlicher: max Breite, weniger Padding */
.block-container { padding-top: 1.1rem; padding-bottom: 1.1rem; max-width: 1000px; }

/* Tabellen-HTML etwas kompakter */
table { width: 100%; border-collapse: collapse; }
th, td { padding: 6px 6px; vertical-align: top; }
th { font-weight: 600; }

/* Print: Sidebar + Header/Footer ausblenden */
@media print {
  section[data-testid="stSidebar"] { display: none !important; }
  header, footer { display: none !important; }
  .block-container { max-width: 190mm !important; padding: 0 !important; }
  button, input, textarea { display: none !important; }
  table { font-size: 11px !important; }
}
</style>
""",
    unsafe_allow_html=True
)

st.title("Post-EEG Vergleichsrechner (4 Varianten)")
st.caption("Vereinfachtes Modell: konstante Jahreswerte (ohne Degradation/Preissteigerung).")

# -------------------------------------------------------
# Sidebar Eingaben
# -------------------------------------------------------

with st.sidebar:
    st.header("Eingaben")

    st.subheader("Altanlage")
    gen_old = st.number_input("Erzeugung alt (kWh/Jahr)", value=4500.0, step=100.0, min_value=0.0)
    cons = st.number_input("Stromverbrauch (kWh/Jahr)", value=4000.0, step=100.0, min_value=0.0)

    st.subheader("Preise")
    market_ct = st.number_input("Marktwert Einspeisung (ct/kWh)", value=3.5, step=0.1, min_value=0.0)
    retail_ct = st.number_input("Strompreis Bezug (ct/kWh)", value=32.0, step=0.5, min_value=0.0)

    # Variante 2
    st.subheader("Variante 2: Eigenverbrauch (ohne Speicher)")
    self_v2 = st.slider("Eigenverbrauchsquote V2 (% der Erzeugung)", 0, 100, 30)
    inv_v2 = st.number_input("Invest V2 Umbau (€) (Umklemmen/Ummelden)", value=1200.0, step=100.0, min_value=0.0)

    # Variante 3 (3 Eingaben: Umbau + Batteriegröße + Preis/kWh)
    st.subheader("Variante 3: Eigenverbrauch + Batteriespeicher")
    self_v3 = st.slider("Eigenverbrauchsquote V3 (% der Erzeugung)", 0, 100, 60)

    inv_v3_umbau = st.number_input(
        "Invest Umbau V3 (€) (Umklemmen/Umbau Verteilung)",
        value=1200.0,
        step=100.0,
        min_value=0.0
    )
    battery_size_kwh = st.number_input("Batteriegröße (kWh)", value=8.0, step=1.0, min_value=0.0)
    battery_price_per_kwh = st.number_input("Preis pro kWh Speicher (€)", value=500.0, step=50.0, min_value=0.0)

    battery_cost = battery_size_kwh * battery_price_per_kwh
    inv_v3 = float(inv_v3_umbau) + float(battery_cost)

    st.info(
        f"➡️ Gesamtinvest V3: {fmt_eur(inv_v3)} "
        f"(Umbau {fmt_eur(inv_v3_umbau)} + Speicher {fmt_eur(battery_cost)})"
    )

    # Variante 4
    st.subheader("Variante 4: Demontage + Neuanlage")
    inv_v4 = st.number_input("Invest V4 (€) (Demontage + neue Anlage)", value=16000.0, step=500.0, min_value=0.0)
    gen_new = st.number_input("Erzeugung neu (kWh/Jahr)", value=7000.0, step=100.0, min_value=0.0)
    self_v4 = st.slider("Eigenverbrauchsquote V4 (% der Erzeugung)", 0, 100, 35)
    eeg_ct = st.number_input("EEG-Vergütung neu (ct/kWh)", value=8.0, step=0.1, min_value=0.0)

    st.divider()
    show_details = st.checkbox("Details (kWh-Aufteilung) anzeigen", value=False)
    show_print_hint = st.checkbox("Druck-Hinweis anzeigen", value=True)

if show_print_hint:
    st.info("Drucken: Browser → **Drucken** (Strg+P). Im Druck wird die Sidebar automatisch ausgeblendet und das Layout auf A4 komprimiert.")

# -------------------------------------------------------
# Berechnung
# -------------------------------------------------------

r1 = variant1_full_feed_in(gen_old, market_ct)

r2 = variant_self_consumption(
    name="V2 Eigenverbrauch (ohne Speicher)",
    generation_kwh=gen_old,
    consumption_kwh=cons,
    self_pct=float(self_v2),
    invest_eur=float(inv_v2),
    retail_cent=float(retail_ct),
    export_cent=float(market_ct),
)

r3 = variant_self_consumption(
    name="V3 Eigenverbrauch + Speicher",
    generation_kwh=gen_old,
    consumption_kwh=cons,
    self_pct=float(self_v3),
    invest_eur=float(inv_v3),
    retail_cent=float(retail_ct),
    export_cent=float(market_ct),
)

r4 = variant4_new_system(
    new_generation_kwh=gen_new,
    consumption_kwh=cons,
    self_pct=float(self_v4),
    invest_eur=float(inv_v4),
    retail_cent=float(retail_ct),
    eeg_cent=float(eeg_ct),
)

results: List[Result] = [r1, r2, r3, r4]
best_20 = max(results, key=lambda x: x.total_20y_eur)

# -------------------------------------------------------
# Tabelle: Kennzahlen = Zeilen, Varianten = Spalten
# -------------------------------------------------------

metrics_order = [
    "Invest",
    "Summe 10 Jahre",
    "Summe 20 Jahre",
    "Amortisation",
    "Vorteil/Ertrag pro Jahr",
]

table_dict: Dict[str, Dict[str, str]] = {}
for r in results:
    table_dict[r.name] = {
        "Invest": fmt_eur(r.invest_eur),
        "Summe 10 Jahre": fmt_eur(r.total_10y_eur),
        "Summe 20 Jahre": fmt_eur(r.total_20y_eur),
        "Amortisation": fmt_years(r.payback_years),
        "Vorteil/Ertrag pro Jahr": fmt_eur(r.annual_cashflow_eur),
    }

df_show = pd.DataFrame(table_dict).reindex(metrics_order)
df_show.columns = [c.replace(" ", "<br>") for c in df_show.columns]

# -------------------------------------------------------
# Cashflow Linienchart (0..20 Jahre)
# -------------------------------------------------------

years = list(range(0, 21))  # 0..20

def cashflow_curve(invest: float, annual: float) -> List[float]:
    return [(-invest + annual * y) for y in years]

df_line = pd.DataFrame(
    {r.name: cashflow_curve(r.invest_eur, r.annual_cashflow_eur) for r in results},
    index=years
)
df_line.index.name = "Jahr"

# -------------------------------------------------------
# Ausgabe: Tabelle oben, Diagramm darunter (A4 optimal)
# -------------------------------------------------------

st.subheader("Ergebnisübersicht")
st.markdown(
    f"""
    <div style="overflow-x:auto; width:100%;">
        {df_show.to_html(escape=False)}
    </div>
    """,
    unsafe_allow_html=True
)

st.divider()

st.subheader("Cashflow-Verlauf (0–20 Jahre)")
st.caption("Jahr 0 = –Invest. Danach jährliche Steigung = Vorteil/Ertrag pro Jahr.")
st.line_chart(df_line, use_container_width=True)
st.write("**Break-even:** dort, wo eine Linie die 0 € überschreitet.")

# -------------------------------------------------------
# Zusammenfassung unten
# -------------------------------------------------------

st.divider()
st.subheader("Zusammenfassung")

st.write(
    f"- **Beste Variante nach 20 Jahren:** {best_20.name} mit **{fmt_eur(best_20.total_20y_eur)}**.\n"
    f"- **Eingaben:** Erzeugung alt {gen_old:,.0f} kWh/a, Verbrauch {cons:,.0f} kWh/a. "
    f"Strompreis {retail_ct:.1f} ct/kWh, Marktwert {market_ct:.1f} ct/kWh.\n"
    f"- **Variante 3 Speicher:** {battery_size_kwh:.1f} kWh × {battery_price_per_kwh:.0f} €/kWh = "
    f"{fmt_eur(battery_cost)} Speicheranteil, Umbau {fmt_eur(inv_v3_umbau)}, "
    f"**Gesamt {fmt_eur(inv_v3)}**."
)

# -------------------------------------------------------
# Details (optional)
# -------------------------------------------------------

if show_details:
    st.divider()
    st.subheader("Details (kWh-Aufteilung)")

    def detail_block(title: str, generation: float, self_pct: float, export_price_ct: float, export_label: str):
        self_kwh = compute_self_consumed_kwh(generation, cons, self_pct)
        export_kwh = max(0.0, generation - self_kwh)
        st.markdown(f"**{title}**")
        st.write(f"- Erzeugung: {generation:,.0f} kWh/Jahr".replace(",", "."))
        st.write(f"- Eigenverbrauch (Ziel): {self_pct:.0f}% der Erzeugung")
        st.write(f"- Tatsächlicher Eigenverbrauch: {self_kwh:,.0f} kWh/Jahr".replace(",", "."))
        st.write(f"- Einspeisung: {export_kwh:,.0f} kWh/Jahr".replace(",", "."))
        st.write(f"- Einspeiseerlös: {export_label} {export_price_ct:.2f} ct/kWh")

    c1, c2 = st.columns(2)
    with c1:
        detail_block("Variante 2", gen_old, float(self_v2), market_ct, "Marktwert")
        detail_block("Variante 3", gen_old, float(self_v3), market_ct, "Marktwert")
        st.write(f"**V3 Invest-Aufteilung:** Umbau {fmt_eur(inv_v3_umbau)} + Speicher {fmt_eur(battery_cost)} = **{fmt_eur(inv_v3)}**")

    with c2:
        st.markdown("**Variante 1**")
        st.write(f"- Erzeugung: {gen_old:,.0f} kWh/Jahr".replace(",", "."))
        st.write(f"- Einspeisung: {gen_old:,.0f} kWh/Jahr".replace(",", "."))
        st.write(f"- Einspeiseerlös: Marktwert {market_ct:.2f} ct/kWh")
        detail_block("Variante 4", gen_new, float(self_v4), eeg_ct, "EEG-Vergütung")

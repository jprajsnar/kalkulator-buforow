"""
Kalkulator buforów projektowych (Critical Chain)
Uruchomienie:  streamlit run app.py
"""

import math

import altair as alt
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Ustawienia strony i kolory
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Kalkulator buforów projektowych",
    page_icon="⏳",
    layout="centered",
)

COLOR_TASK = "#3B6EA5"     # zadania – stalowy niebieski
COLOR_BUFFER = "#E8A33D"   # bufor – bursztyn
COLOR_RISK = "#B23A48"     # linia planu pesymistycznego
COLOR_INK = "#1F2A44"

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600;700&display=swap');

    html, body, [class*="css"], .stMarkdown, .stButton button {{
        font-family: 'IBM Plex Sans', system-ui, sans-serif;
    }}
    h1 {{ color: {COLOR_INK}; font-weight: 700; letter-spacing: -0.02em; }}

    /* Przyciski */
    .stButton button, .stDownloadButton button {{
        border-radius: 8px;
        font-weight: 600;
        padding: 0.55rem 1.1rem;
        transition: transform 0.08s ease;
    }}
    .stButton button:active {{ transform: scale(0.98); }}
    .stButton button[kind="primary"],
    button[data-testid="stBaseButton-primary"] {{
        background: {COLOR_TASK};
        border-color: {COLOR_TASK};
    }}
    .stButton button[kind="primary"]:hover,
    button[data-testid="stBaseButton-primary"]:hover {{
        background: #2F5A88;
        border-color: #2F5A88;
    }}

    /* Kafelki z wynikami */
    div[data-testid="stMetric"] {{
        border-left: 4px solid {COLOR_BUFFER};
        padding: 0.6rem 1rem;
        border-radius: 6px;
        background: rgba(232, 163, 61, 0.08);
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Dane startowe
# ---------------------------------------------------------------------------
EXAMPLE = pd.DataFrame(
    {
        "Zadanie": ["Analiza wymagań", "Projekt UX", "Backend", "Frontend", "Testy i wdrożenie"],
        "Optymistyczny": [3.0, 4.0, 8.0, 6.0, 3.0],
        "Pesymistyczny": [6.0, 7.0, 15.0, 11.0, 6.0],
    }
)
EMPTY = pd.DataFrame({"Zadanie": [""], "Optymistyczny": [0.0], "Pesymistyczny": [0.0]})

METHOD_RSS = "Pierwiastek z sumy kwadratów (RSS)"
METHOD_HALF = "Metoda 50% (Goldratt)"

if "tasks" not in st.session_state:
    st.session_state.tasks = EXAMPLE.copy()
if "editor_key" not in st.session_state:
    st.session_state.editor_key = 0
if "result" not in st.session_state:
    st.session_state.result = None


def reset_table(df: pd.DataFrame) -> None:
    """Podmienia tabelę i czyści poprzedni wynik."""
    st.session_state.tasks = df.copy()
    st.session_state.editor_key += 1
    st.session_state.result = None


# ---------------------------------------------------------------------------
# Logika obliczeń
# ---------------------------------------------------------------------------
def prepare_tasks(df: pd.DataFrame) -> pd.DataFrame:
    """Czyści dane z tabeli: usuwa puste wiersze i nadaje brakujące nazwy."""
    df = df.copy()
    df["Optymistyczny"] = pd.to_numeric(df["Optymistyczny"], errors="coerce").fillna(0)
    df["Pesymistyczny"] = pd.to_numeric(df["Pesymistyczny"], errors="coerce").fillna(0)
    df = df[(df["Optymistyczny"] > 0) | (df["Pesymistyczny"] > 0)].reset_index(drop=True)

    names = df["Zadanie"].fillna("").astype(str).str.strip()
    df["Zadanie"] = [n if n else f"Zadanie {i + 1}" for i, n in enumerate(names)]
    return df


def calculate_buffer(df: pd.DataFrame, method: str) -> float:
    """Zwraca wielkość bufora projektu."""
    if method == METHOD_RSS:
        safety = df["Pesymistyczny"] - df["Optymistyczny"]
        return math.sqrt((safety ** 2).sum())
    return 0.5 * df["Optymistyczny"].sum()


def build_chart(df: pd.DataFrame, buffer: float, sum_pessimistic: float, unit: str):
    """Prosty wykres Gantta: zadania jedno po drugim + bufor na końcu."""
    rows, t = [], 0.0
    for _, r in df.iterrows():
        rows.append({"Element": r["Zadanie"], "Start": t, "Koniec": t + r["Optymistyczny"], "Typ": "Zadanie"})
        t += r["Optymistyczny"]
    rows.append({"Element": "Bufor projektu", "Start": t, "Koniec": t + buffer, "Typ": "Bufor"})

    gantt = pd.DataFrame(rows)
    gantt["Czas"] = (gantt["Koniec"] - gantt["Start"]).round(1)

    bars = (
        alt.Chart(gantt)
        .mark_bar(cornerRadius=3, height=24)
        .encode(
            x=alt.X("Start:Q", title=f"Czas ({unit})"),
            x2="Koniec:Q",
            y=alt.Y("Element:N", sort=None, title=None),
            color=alt.Color(
                "Typ:N",
                scale=alt.Scale(domain=["Zadanie", "Bufor"], range=[COLOR_TASK, COLOR_BUFFER]),
                legend=alt.Legend(title=None, orient="top"),
            ),
            tooltip=[
                alt.Tooltip("Element:N", title="Element"),
                alt.Tooltip("Czas:Q", title=f"Czas ({unit})"),
            ],
        )
    )

    marker = pd.DataFrame({"x": [sum_pessimistic], "label": ["Plan pesymistyczny"]})
    rule = alt.Chart(marker).mark_rule(color=COLOR_RISK, strokeDash=[5, 4], size=2).encode(x="x:Q")
    label = (
        alt.Chart(marker)
        .mark_text(color=COLOR_RISK, align="right", dx=-6, dy=-8, fontWeight="bold")
        .encode(x="x:Q", y=alt.value(0), text="label:N")
    )

    return (bars + rule + label).properties(height=60 + 34 * len(gantt))


# ---------------------------------------------------------------------------
# Interfejs
# ---------------------------------------------------------------------------
st.title("⏳ Kalkulator buforów projektowych")
st.write(
    "Wpisz zadania z łańcucha krytycznego wraz z czasem optymistycznym i pesymistycznym. "
    "Aplikacja policzy jeden wspólny bufor dla całego projektu, zamiast doliczać zapas do każdego zadania osobno."
)

c1, c2 = st.columns(2)
with c1:
    if st.button("📋 Wczytaj przykład", width="stretch"):
        reset_table(EXAMPLE)
        st.rerun()
with c2:
    if st.button("🧹 Wyczyść tabelę", width="stretch"):
        reset_table(EMPTY)
        st.rerun()

edited = st.data_editor(
    st.session_state.tasks,
    num_rows="dynamic",
    width="stretch",
    hide_index=True,
    key=f"editor_{st.session_state.editor_key}",
    column_config={
        "Zadanie": st.column_config.TextColumn("Zadanie", width="large"),
        "Optymistyczny": st.column_config.NumberColumn(
            "Czas optymistyczny", min_value=0.0, step=0.5, format="%.1f",
            help="Ile zajmie zadanie, jeśli wszystko pójdzie dobrze.",
        ),
        "Pesymistyczny": st.column_config.NumberColumn(
            "Czas pesymistyczny", min_value=0.0, step=0.5, format="%.1f",
            help="Ile zajmie zadanie z bezpiecznym zapasem.",
        ),
    },
)
st.caption("Aby dodać zadanie, kliknij pusty wiersz na dole tabeli. Aby usunąć – zaznacz wiersz i naciśnij Delete.")

s1, s2 = st.columns([2, 1])
with s1:
    method = st.radio("Metoda liczenia bufora", [METHOD_RSS, METHOD_HALF], horizontal=False)
with s2:
    unit = st.selectbox("Jednostka", ["dni", "godziny", "tygodnie"])

if st.button("Oblicz bufor", type="primary", width="stretch"):
    tasks = prepare_tasks(edited)
    if tasks.empty:
        st.session_state.result = None
        st.warning("Tabela jest pusta. Dodaj co najmniej jedno zadanie z czasem większym od zera.")
    else:
        wrong = tasks[tasks["Pesymistyczny"] < tasks["Optymistyczny"]]["Zadanie"].tolist()
        if wrong:
            st.session_state.result = None
            st.error(
                "Czas pesymistyczny nie może być krótszy niż optymistyczny. Popraw: " + ", ".join(wrong)
            )
        else:
            st.session_state.result = {
                "tasks": tasks,
                "buffer": calculate_buffer(tasks, method),
                "method": method,
                "unit": unit,
            }

# ---------------------------------------------------------------------------
# Wyniki
# ---------------------------------------------------------------------------
res = st.session_state.result
if res:
    tasks, buffer, u = res["tasks"], res["buffer"], res["unit"]
    sum_opt = tasks["Optymistyczny"].sum()
    sum_pes = tasks["Pesymistyczny"].sum()
    plan = sum_opt + buffer
    saved = sum_pes - plan

    st.divider()
    st.subheader("Wynik")

    m1, m2, m3 = st.columns(3)
    m1.metric("Praca (optymistycznie)", f"{sum_opt:.1f} {u}")
    m2.metric("Bufor projektu", f"{buffer:.1f} {u}", f"{buffer / sum_opt:.0%} czasu pracy", delta_color="off")
    m3.metric(
        "Termin z buforem", f"{plan:.1f} {u}",
        f"{-saved:+.1f} {u} vs plan pesymistyczny", delta_color="inverse",
    )

    if saved > 0:
        st.success(
            f"Planujesz projekt na **{plan:.1f} {u}** zamiast {sum_pes:.1f} {u}. "
            f"Wspólny bufor oszczędza **{saved:.1f} {u}** i nadal chroni termin."
        )
    else:
        st.info("Przy tej metodzie bufor jest równy lub większy niż suma zapasów – to bardzo ostrożny plan.")

    st.altair_chart(build_chart(tasks, buffer, sum_pes, u))
    st.caption(f"Metoda: {res['method']}. Przerywana linia pokazuje, gdzie skończyłby się plan pesymistyczny.")

    export = tasks.rename(columns={"Optymistyczny": f"Optymistyczny ({u})", "Pesymistyczny": f"Pesymistyczny ({u})"})
    export.loc[len(export)] = ["BUFOR PROJEKTU", round(buffer, 1), None]
    st.download_button(
        "⬇️ Pobierz wyniki (CSV)",
        data=export.to_csv(index=False, sep=";").encode("utf-8-sig"),
        file_name="bufor_projektu.csv",
        mime="text/csv",
        width="stretch",
    )

with st.expander("Jak to liczymy?"):
    st.markdown(
        """
**Pierwiastek z sumy kwadratów (RSS)** – dla każdego zadania liczymy zapas
(pesymistyczny − optymistyczny), podnosimy go do kwadratu, sumujemy i wyciągamy pierwiastek.
Opiera się na założeniu, że nie wszystkie zadania opóźnią się jednocześnie,
więc wspólny bufor może być mniejszy niż suma wszystkich zapasów.
Sprawdza się przy dłuższych łańcuchach i zadaniach o różnej niepewności.

**Metoda 50% (Goldratt)** – bufor to połowa sumy czasów optymistycznych.
Prosta i łatwa do wytłumaczenia interesariuszom, ale przy długich łańcuchach
daje zwykle zbyt duży bufor.

Harmonogram na wykresie zakłada, że zadania wykonywane są jedno po drugim (łańcuch krytyczny),
a bufor stoi na końcu, tuż przed terminem.
"""
    )

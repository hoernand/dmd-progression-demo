# --- DMD Prognosis Demo (Young intake + Genotype presets) ---
# Illustrative only; not a medical device.

import math
from typing import Optional, Tuple, Dict

import numpy as np
import plotly.graph_objects as go
import streamlit as ststreamlit==1.39.0
plotly
numpy

# ---------------------------
# Page config
# ---------------------------
st.set_page_config(page_title="DMD – Prognosis Demo (synthetic)", page_icon="🧭", layout="wide")
st.markdown("### DMD – Prognosis Demo (synthetic)")
st.caption("Illustrative; not for clinical decision-making.")

# ---------------------------
# Course profiles (demo curves)
# ---------------------------
COURSE_PROFILES: Dict[str, dict] = {
    # tuned for earlier intake; peak earlier for faster courses
    "very_fast": dict(
        label="very fast",
        peakAge=5.8, loaAge=9.5, stairLoss=8.4, handLoss=10.2,
        ranges=dict(peak=(5.5, 6.1), loa=(9.0, 10.0), stair=(8.0, 8.8), hand=(9.8, 10.6)),
        base_peak=420.0,
    ),
    "fast": dict(
        label="fast",
        peakAge=6.4, loaAge=10.5, stairLoss=8.9, handLoss=10.8,
        ranges=dict(peak=(6.1, 6.7), loa=(10.0, 11.0), stair=(8.5, 9.3), hand=(10.4, 11.2)),
        base_peak=460.0,
    ),
    "medium": dict(
        label="medium",
        peakAge=6.9, loaAge=11.5, stairLoss=9.5, handLoss=11.5,
        ranges=dict(peak=(6.6, 7.2), loa=(11.0, 12.0), stair=(9.1, 9.9), hand=(11.1, 11.9)),
        base_peak=490.0,
    ),
    "slow": dict(
        label="slow",
        peakAge=7.6, loaAge=12.8, stairLoss=10.2, handLoss=12.3,
        ranges=dict(peak=(7.3, 7.9), loa=(12.3, 13.3), stair=(9.8, 10.6), hand=(11.9, 12.7)),
        base_peak=515.0,
    ),
    "modifier": dict(
        label="modifier-favored",
        peakAge=8.2, loaAge=14.0, stairLoss=10.8, handLoss=12.9,
        ranges=dict(peak=(7.9, 8.5), loa=(13.5, 14.5), stair=(10.4, 11.2), hand=(12.5, 13.3)),
        base_peak=535.0,
    ),
}

# ---------------------------
# Example presets (aimed at age 5–6)
# ---------------------------
PRESETS = {
    # SLOWER course → duplication; strong steroid effect; near-5y intake
    "Preset 1 – Slower (Duplication, Exon 12)": dict(
        age=5.4, ten_m=4.6, nsaa=29, pul=43, rise_up=5.6, four_stair=4.8,
        steroid=True, steroid_start_age=5.0,
        variant="duplication", exon="12", cdna="c.789dup", protein="p.(Gly264fs)", promoter="0 (no)"
    ),
    # MEDIUM course → deletion 45–50; typical intake ~6y
    "Preset 2 – Medium (Deletion, Exon 45–50)": dict(
        age=6.1, ten_m=5.1, nsaa=24, pul=38, rise_up=7.2, four_stair=5.9,
        steroid=True, steroid_start_age=6.0,
        variant="deletion", exon="45-50", cdna="c.(del45_50)", protein="p.(?)", promoter="0 (no)"
    ),
    # FASTER course → frameshift; no steroids; still at 6y intake
    "Preset 3 – Faster (Frameshift, Exon 23)": dict(
        age=6.0, ten_m=6.2, nsaa=18, pul=32, rise_up=9.3, four_stair=7.1,
        steroid=False, steroid_start_age=6.0,
        variant="frameshift", exon="23", cdna="c.1234delA", protein="p.(Lys412fs)", promoter="0 (no)"
    ),
}

# ---------------------------
# Helpers
# ---------------------------
def virtual_6mwt(ten_m_sec: Optional[float], nsaa: Optional[int]) -> Optional[float]:
    """Heuristic: derive a virtual 6MWT (m) from 10MWT (s) and NSAA (0–34); clamp 100..600 m."""
    if ten_m_sec is None or ten_m_sec <= 0:
        return None
    nsaa_norm = 0.6 if nsaa is None else max(0, min(34, nsaa)) / 34.0
    base = 600.0 * (10.0 / (10.0 + float(ten_m_sec)))
    virt = base * (0.6 + 0.4 * nsaa_norm)
    return float(max(100.0, min(600.0, virt)))

def apply_steroid_shift(age: float, steroid: bool, early_start: bool, poor_function: bool) -> float:
    """Demo modifier: Steroids +1.0 y; early start (<6 y) +0.5; very poor function -0.5."""
    shift = 0.0
    if steroid:
        shift += 1.0
        if early_start:
            shift += 0.5
    if poor_function:
        shift -= 0.5
    return age + shift

def halfyear_band(center: float, lo: Optional[float] = None, hi: Optional[float] = None) -> Tuple[float, float]:
    low = center - 0.25
    high = center + 0.25
    if lo is not None: low = max(low, lo)
    if hi is not None: high = min(high, hi)
    return round(low, 1), round(high, 1)

def fmt(age: Optional[float], band: Optional[Tuple[float, float]]) -> str:
    if age is None or not math.isfinite(age): return "–"
    main = f"{round(age,1):.1f} y"
    return main if band is None else f"{main} ({band[0]:.1f}–{band[1]:.1f})"

# genotype weighting so presets behave distinctly
def genotype_weight(variant: str, exon: str) -> float:
    """
    Small heuristic weight by variant & exon region (demo):
    + duplication: +0.6 (slower)
    + large deletion around 45–50: -0.25 (faster than small deletions)
    + frameshift: -0.7 (faster)
    + nonsense: -0.6 (faster)
    + missense/splice: -0.1
    """
    v = (variant or "").lower()
    e = (exon or "")
    w = 0.0
    if "duplication" in v:
        w += 0.6
    elif "frameshift" in v:
        w -= 0.7
    elif "nonsense" in v:
        w -= 0.6
    elif "deletion" in v:
        if any(k in e for k in ["45", "46", "47", "48", "49", "50"]):
            w -= 0.25
    elif "missense" in v or "splice" in v:
        w -= 0.1
    return w

def compute_course(age: float,
                   ten_m: Optional[float], nsaa: Optional[int], pul: Optional[int],
                   rise_up: Optional[float], four_stair: Optional[float],
                   steroid: bool, variant: str, exon: str) -> tuple[str, str]:
    """
    Returns (course_key, explanation).
    Rules (illustrative):
    - Strong current function (NSAA >= 28 & 10m <= 4.5s) => slower.
    - Weak current function (NSAA <= 18 & 10m >= 6.0s) => faster.
    - Low PUL (<35) at <10y => faster.
    - Rise-up > 8s or 4-stairs > 6s at <10y => faster.
    - Steroids => slightly slower.
    - Genotype heuristic adds a weight (duplication slower; frameshift/nonsense faster; big 45–50 deletion a bit faster).
    """
    score = 0.0  # negative = faster; positive = slower

    if nsaa is not None and ten_m is not None:
        if nsaa >= 28 and ten_m <= 4.5: score += 1.0
        if nsaa <= 18 and ten_m >= 6.0: score -= 1.0

    if pul is not None and age < 10:
        if pul < 35: score -= 0.5
        if pul >= 42: score += 0.3

    if age < 10:
        if (rise_up is not None and rise_up > 8.0) or (four_stair is not None and four_stair > 6.0):
            score -= 0.5

    score += genotype_weight(variant, exon)
    if steroid: score += 0.3

    if score < -1.0: key = "very_fast"
    elif score < -0.2: key = "fast"
    elif score <= 0.6: key = "medium"
    elif score <= 1.2: key = "slow"
    else: key = "modifier"

    reason = f"Score={score:+.2f} (function, <10y, PUL, steroids, genotype heuristic)"
    return key, reason

# ---------------------------
# Preset loader (top bar)
# ---------------------------
bar1, bar2 = st.columns([0.7, 0.3])
with bar1:
    chosen = st.selectbox("Quick presets (you can still edit inputs after loading):",
                          list(PRESETS.keys()), index=0, key="preset_choice")
with bar2:
    if st.button("Load preset", key="btn_load"):
        p = PRESETS[chosen]
        for k, v in p.items():
            st.session_state[k] = v
        st.success(f"Loaded: {chosen}")

st.divider()

# ---------------------------
# INPUTS (age focus 4–10y)
# ---------------------------
c1, c2, c3 = st.columns(3)
with c1:
    age = st.number_input("Age (years)", value=st.session_state.get("age", 5.8),
                          step=0.1, min_value=4.0, max_value=10.0, key="age")
    ten_m = st.number_input("10-meter walk time (s)", value=st.session_state.get("ten_m", 5.0),
                            step=0.01, min_value=0.0, key="ten_m")
    nsaa = st.number_input("NSAA (0–34)", value=st.session_state.get("nsaa", 26),
                           step=1, min_value=0, max_value=34, key="nsaa")
with c2:
    pul = st.number_input("PUL total", value=st.session_state.get("pul", 40),
                          step=1, min_value=0, key="pul")
    rise_up = st.number_input("Time to stand from floor (s)", value=st.session_state.get("rise_up", 7.0),
                              step=0.1, min_value=0.0, key="rise_up")
    four_stair = st.number_input("Climb 4 stairs (s)", value=st.session_state.get("four_stair", 5.8),
                                 step=0.1, min_value=0.0, key="four_stair")
with c3:
    steroid = st.checkbox("On steroid therapy", value=st.session_state.get("steroid", True), key="steroid")
    steroid_start_age = st.number_input("Steroid start age (y)", value=st.session_state.get("steroid_start_age", 5.5),
                                        step=0.1, key="steroid_start_age")
    st.divider()
    st.markdown("**Genotype (visible)**")
    variant_options = ["point mutation", "deletion", "duplication", "insertion",
                       "nonsense", "missense", "splice", "frameshift", "other"]
    variant = st.selectbox("Type of variant (mutation)",
                           variant_options,
                           index=variant_options.index(st.session_state.get("variant", "duplication")),
                           key="variant")
    exon = st.text_input("Exon number / range", value=st.session_state.get("exon", "12"), key="exon")
    cdna = st.text_input("cDNA (HGVS c.)", value=st.session_state.get("cdna", "c.789dup"), key="cdna")
    protein = st.text_input("Protein (HGVS p.)", value=st.session_state.get("protein", "p.(Gly264fs)"), key="protein")
    promoter = st.selectbox("Promoter affected", ["0 (no)", "1 (yes)"],
                            index=0 if st.session_state.get("promoter", "0 (no)") == "0 (no)" else 1, key="promoter")

virt6 = virtual_6mwt(ten_m, nsaa)

# ---------------------------
# Auto course type from inputs
# ---------------------------
course_key, reason = compute_course(age, ten_m, nsaa, pul, rise_up, four_stair, steroid, variant, exon)
profile = COURSE_PROFILES[course_key]

# ---------------------------
# Trajectory + milestones (bottom)
# ---------------------------
early_start = bool(steroid and steroid_start_age is not None and steroid_start_age < 6.0)
poor_function = bool((nsaa is not None and nsaa < 18) and (ten_m is not None and ten_m > 6.0))

# Age axis focused on childhood window
peak_age = apply_steroid_shift(profile["peakAge"], steroid, early_start, poor_function)
ages = np.round(np.arange(4.0, 14.0001, 0.25), 2)

rel = []
for a in ages:
    if a <= peak_age:
        t = max(0.0, min(1.0, (a - 4.0) / max(0.2, (peak_age - 4.0))))
        rel.append(0.5 + 0.5 * t)  # rises to 1.0
    else:
        t = (a - peak_age) / max(0.2, (14.0 - peak_age))
        rel.append(math.exp(-3.0 * t) + 0.1 * (1 - math.exp(-3.0 * t)))  # decays to ~0.1

scale = profile["base_peak"]
if virt6 is not None:
    idx = int(np.argmin(np.abs(ages - age)))
    rel_at = max(0.06, rel[idx])
    scale = max(300.0, min(560.0, virt6 / rel_at))
meters = np.clip(np.array(rel) * scale, 50.0, 600.0)

def find_age_at_value(threshold: float) -> Optional[float]:
    for a, m in zip(ages, meters):
        if m <= threshold:
            return float(a)
    return None

below250 = find_age_at_value(250.0)
loa_shift = apply_steroid_shift(profile["loaAge"], steroid, early_start, poor_function)
below75 = find_age_at_value(75.0)
loa = below75 if below75 is not None else loa_shift

peak_band = halfyear_band(peak_age, *profile["ranges"]["peak"])
below250_band = halfyear_band(below250) if below250 is not None else None
stair_age = apply_steroid_shift(profile["stairLoss"], steroid, early_start, poor_function)
stair_band = halfyear_band(stair_age, *profile["ranges"]["stair"])
hand_age = apply_steroid_shift(profile["handLoss"], steroid, early_start, poor_function)
hand_band = halfyear_band(hand_age, *profile["ranges"]["hand"])
loa_band = halfyear_band(loa, *profile["ranges"]["loa"])

# ---------------------------
# OUTPUT
# ---------------------------
st.divider()
st.subheader("Auto classification & prognosis")

left, right = st.columns([0.45, 0.55])

with left:
    st.markdown(f"**Estimated course type:** {COURSE_PROFILES[course_key]['label']}")
    st.caption(reason)
    st.info(f"Virtual 6MWT (from 10MWT + NSAA): {'–' if virt6 is None else f'{int(round(virt6))} m'}")

    colA, colB, colC = st.columns(3)
    with colA:
        st.write(f"**Peak (age)**: {fmt(peak_age, peak_band)}")
        st.write(f"**<250 m (age)**: {fmt(below250, below250_band)}")
        st.write(f"**Loss of ambulation (age)**: {fmt(loa, loa_band)}")
    with colB:
        st.write(f"**Stairs function loss (age)**: {fmt(stair_age, stair_band)}")
    with colC:
        st.write(f"**Upper limb loss (age)**: {fmt(hand_age, hand_band)}")

with right:
    fig = go.Figure()
    fig.add_scatter(x=ages, y=meters, mode="lines", name="Virtual 6MWT")
    if virt6 is not None:
        fig.add_scatter(x=[age], y=[virt6], mode="markers", name="Today", marker=dict(size=10))
    for label, aval, color in [("Peak", peak_age, "#666"),
                               ("<250 m", below250, "#999"),
                               ("LoA", loa, "#333")]:
        if aval and math.isfinite(aval):
            fig.add_vline(x=aval, line_dash="dot", line_color=color,
                          annotation_text=label, annotation_position="top")
    fig.update_layout(
        height=380, margin=dict(l=30, r=20, t=20, b=40),
        xaxis_title="Age (years)", yaxis_title="Virtual 6MWT (m)",
        yaxis=dict(range=[0, 620])
    )
    st.plotly_chart(fig, use_container_width=True)

st.caption("Childhood-focused view. Half-year ranges in parentheses. "
           "Steroid modifier applied. Genotype presets quickly show fast/medium/slow trajectories.")

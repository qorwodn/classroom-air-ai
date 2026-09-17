import json
import time
from pathlib import Path
import requests

import pandas as pd
import streamlit as st


# =========================
# 기본 설정
# =========================
st.set_page_config(
    page_title="AI 교실 대기환경 관리 시스템",
    page_icon="🏫",
    layout="wide",
)

PREDICTION_FILE = Path("outputs/latest_prediction.json")
HISTORY_FILE = Path("outputs/live_sensor_history.csv")


# =========================
# 디자인
# =========================
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2.5rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }

    .main-title {
        text-align: center;
        font-size: 2.5rem;
        font-weight: 800;
        line-height: 1.4;
        padding-top: 0.3rem;
        padding-bottom: 0.3rem;
        margin-bottom: 0.2rem;
        overflow: visible;
    }

    .sub-title {
        text-align: center;
        color: #888;
        font-size: 1.05rem;
        margin-bottom: 1.8rem;
    }

    .section-title {
        font-size: 1.35rem;
        font-weight: 700;
        margin-top: 0.5rem;
        margin-bottom: 0.8rem;
    }

    .recommend-box {
        text-align: center;
        padding: 25px;
        border-radius: 18px;
        border: 2px solid rgba(128,128,128,0.25);
        margin-top: 10px;
        margin-bottom: 20px;
    }

    .recommend-icon {
        font-size: 3.8rem;
    }

    .recommend-text {
        font-size: 2.2rem;
        font-weight: 800;
        margin-top: 5px;
    }

    .reason-box {
        padding: 18px 22px;
        border-radius: 14px;
        background: rgba(128,128,128,0.10);
        margin-top: 10px;
        font-size: 1.05rem;
    }

    div[data-testid="stMetric"] {
        border: 1px solid rgba(128,128,128,0.20);
        padding: 15px;
        border-radius: 14px;
    }

    /* 숫자/단위가 ... 으로 잘리는 현상 방지 */
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
    }

    div[data-testid="stMetricValue"] > div {
        overflow: visible !important;
        text-overflow: clip !important;
        white-space: nowrap !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# 데이터 읽기
# =========================
def load_prediction():
    try:
        supabase_url = st.secrets["SUPABASE_URL"]
        supabase_key = st.secrets["SUPABASE_KEY"]

        url = (
            supabase_url.rstrip("/")
            + "/rest/v1/live_prediction"
            + "?select=data,created_at&order=created_at.desc&limit=1"
        )

        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        rows = response.json()

        if not rows:
            return None

        return rows[0]["data"]

    except Exception as e:
        st.warning(f"Supabase 데이터 불러오기 실패: {e}")
        return None

def load_history():
    if not HISTORY_FILE.exists():
        return None

    try:
        return pd.read_csv(HISTORY_FILE)
    except Exception:
        return None


data = load_prediction()
history = load_history()


# =========================
# 제목
# =========================
st.markdown(
    '<div class="main-title">🏫 AI 교실 대기환경 관리 시스템</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="sub-title">'
    '실시간 센서 측정 → XGBoost 10분 후 예측 → 실외 환경 분석 → AI 행동 추천'
    '</div>',
    unsafe_allow_html=True,
)


# =========================
# AI 결과 대기
# =========================
if data is None:
    st.info(
        "AI 예측 결과를 기다리고 있습니다. "
        "live_ai.py에서 첫 번째 10분 후 예측이 완료되면 자동으로 표시됩니다."
    )

    if history is not None and len(history) > 0:
        last = history.iloc[-1]

        st.subheader("📡 현재 센서 측정값")

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric("CO₂", f"{float(last['Indoor_CO2_ppm']):.0f} ppm")
        c2.metric("PM2.5", f"{float(last['Indoor_PM2_5_ugm3']):.1f} µg/m³")
        c3.metric("PM10", f"{float(last['Indoor_PM10_ugm3']):.1f} µg/m³")
        c4.metric("온도", f"{float(last['Indoor_Temperature_C']):.1f} ℃")
        c5.metric("습도", f"{float(last['Indoor_RH_percent']):.1f} %")

    time.sleep(2)
    st.rerun()


# =========================
# 결과 표시
# =========================
else:
    current = data["current"]
    predicted = data["predicted_10min"]
    outdoor = data["outdoor"]

    recommendation = data["recommendation"]
    scores = recommendation["scores"]
    action = recommendation["action"]
    reasons = recommendation["reasons"]

    st.caption(f"마지막 AI 분석 시각: {data['timestamp']}")

    # -------------------------
    # 현재 vs 미래
    # -------------------------
    left, right = st.columns(2)

    with left:
        st.markdown(
            '<div class="section-title">📡 현재 교실 환경</div>',
            unsafe_allow_html=True,
        )

        a, b = st.columns(2)

        a.metric(
            "CO₂",
            f"{current['co2']:.0f} ppm",
        )
        b.metric(
            "PM2.5",
            f"{current['pm25']:.1f} µg/m³",
        )

        a.metric(
            "PM10",
            f"{current['pm10']:.1f} µg/m³",
        )
        b.metric(
            "온도",
            f"{current['temperature']:.1f} ℃",
        )

        a.metric(
            "습도",
            f"{current['humidity']:.1f} %",
        )

    with right:
        st.markdown(
            '<div class="section-title">🤖 AI 10분 후 예측</div>',
            unsafe_allow_html=True,
        )

        a, b = st.columns(2)

        co2_delta = (
            predicted["co2"]
            - current["co2"]
        )

        a.metric(
            "CO₂",
            f"{predicted['co2']:.0f} ppm",
            f"{co2_delta:+.0f} ppm",
        )

        b.metric(
            "PM2.5",
            f"{predicted['pm2_5']:.1f} µg/m³",
        )

        a.metric(
            "PM10",
            f"{predicted['pm10']:.1f} µg/m³",
        )

        b.metric(
            "온도",
            f"{predicted['temperature']:.1f} ℃",
        )

        a.metric(
            "습도",
            f"{predicted['humidity']:.1f} %",
        )

    st.divider()

    # -------------------------
    # 실외 환경
    # -------------------------
    st.markdown(
        '<div class="section-title">🌤️ 실외 환경 정보</div>',
        unsafe_allow_html=True,
    )

    o1, o2, o3, o4 = st.columns(4)

    o1.metric(
        "실외 PM2.5",
        f"{outdoor['pm2_5']:.1f} µg/m³",
    )

    o2.metric(
        "실외 PM10",
        f"{outdoor['pm10']:.1f} µg/m³",
    )

    o3.metric(
        "실외 온도",
        f"{outdoor['temperature']:.1f} ℃",
    )

    o4.metric(
        "실외 습도",
        f"{outdoor['humidity']:.1f} %",
    )

    st.divider()

    # -------------------------
    # 행동 추천
    # -------------------------
    st.markdown(
        '<div class="section-title">💡 AI 행동 추천</div>',
        unsafe_allow_html=True,
    )

    if action == "OPEN_WINDOW":
        icon = "🪟"
        recommendation = "창문 열기"

    elif action == "AIR_PURIFIER":
        icon = "🌬️"
        recommendation = "공기청정기 작동"

    else:
        icon = "✅"
        recommendation = "현재 상태 유지"

    st.markdown(
        f"""
        <div class="recommend-box">
            <div class="recommend-icon">{icon}</div>
            <div class="recommend-text">{recommendation}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -------------------------
    # 행동 점수
    # -------------------------
    s1, s2, s3 = st.columns(3)

    s1.metric(
        "🪟 창문 열기",
        f"{scores['OPEN_WINDOW']:.1f} 점",
    )

    s2.metric(
        "🌬️ 공기청정기",
        f"{scores['AIR_PURIFIER']:.1f} 점",
    )

    s3.metric(
        "✅ 현재 유지",
        f"{scores['NONE']:.1f} 점",
    )

    st.progress(
        min(max(float(scores[action]) / 100.0, 0.0), 1.0),
        text=f"추천 행동 점수: {float(scores[action]):.1f} / 100",
    )

    # -------------------------
    # 추천 이유
    # -------------------------
    reason_html = "<br>".join(
        f"• {reason}" for reason in reasons
    )

    st.markdown(
        f"""
        <div class="reason-box">
            <b>AI 판단 근거</b><br><br>
            {reason_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -------------------------
    # 최근 CO2 변화
    # -------------------------
    if history is not None and len(history) >= 2:
        st.divider()

        st.markdown(
            '<div class="section-title">📈 최근 교실 CO₂ 변화</div>',
            unsafe_allow_html=True,
        )

        chart_df = history.tail(30).copy()

        if "Timestamp" in chart_df.columns:
            chart_df["Timestamp"] = pd.to_datetime(
                chart_df["Timestamp"],
                errors="coerce",
            )

            chart_df = chart_df.set_index("Timestamp")

        st.line_chart(
            chart_df[["Indoor_CO2_ppm"]],
            height=260,
        )

    st.caption(
        "※ AI 예측값은 과거 환경 데이터로 학습한 XGBoost 모델의 "
        "10분 후 예측 결과입니다."
    )

    # 2초마다 새 JSON/CSV 확인
    time.sleep(2)
    st.rerun()

"""앱 전역 설정: 색상, 문구, 상수."""

APP_NAME = "GamePulse AI"
APP_TAGLINE = "게임 이용자 문제를 데이터로 정의하고, 사업PM 관점의 개선 전략과 KPI를 설계합니다."
APP_VERSION = "v0.1 (기본 웹사이트 · AI 미연결)"

# 화이트 · 네이비 · 블루 팔레트
COLORS = {
    "navy": "#0B1F3A",
    "navy_soft": "#1B3358",
    "blue": "#1E5EFF",
    "blue_mid": "#4A7DFF",
    "sky": "#8DB3FF",
    "ice": "#DCE8FF",
    "bg": "#FFFFFF",
    "bg_soft": "#F4F7FC",
    "line": "#DDE4EF",
    "gray": "#6B7A90",
    "warn": "#C2410C",
}

# 범주형 차트 색상 순서 (네이비 → 블루 계열)
SEQ = ["#1E5EFF", "#0B1F3A", "#8DB3FF", "#4A6A99", "#B9CFFF", "#9AA6B8"]

SAMPLE_LABEL = "예시 데이터"
SAMPLE_NOTICE = (
    "이 화면의 모든 수치·그래프·시뮬레이션은 포트폴리오 시연용으로 생성한 **예시 데이터**입니다. "
    "실제 이용자 수, 매출, 이탈률, 운영 정책을 나타내지 않습니다."
)
HYPOTHESIS_NOTICE = (
    "불만 유형과 원인의 관계는 실제 데이터로 **검증하기 전까지 가설**입니다."
)

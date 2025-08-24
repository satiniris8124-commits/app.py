# 약국 찾기 (영업중 필터 포함)
import streamlit as st
import pandas as pd
import requests
from haversine import haversine
from geopy.geocoders import Nominatim
from streamlit_folium import st_folium
import folium
from datetime import datetime, time
from timezonefinder import TimezoneFinder
import pytz
import re

st.set_page_config(page_title="약국 찾기", page_icon="💊", layout="wide")
st.title("💊 내 주변 약국 찾기 (영업중만 보기)")

DAY_MAP = {"Mo": 0, "Tu": 1, "We": 2, "Th": 3, "Fr": 4, "Sa": 5, "Su": 6}

def parse_time(tstr):
    try:
        hh, mm = tstr.split(":")
        return time(int(hh), int(mm))
    except Exception:
        return None

def expand_days(part):
    if "-" in part:
        a, b = part.split("-")
        if a in DAY_MAP and b in DAY_MAP:
            ai, bi = DAY_MAP[a], DAY_MAP[b]
            return list(range(ai, bi + 1)) if ai <= bi else list(range(ai, 7)) + list(range(0, bi + 1))
    elif part in DAY_MAP:
        return [DAY_MAP[part]]
    return []

def parse_rule(rule):
    rule = rule.strip()
    m = re.match(r'^([A-Za-z]{2}(?:-[A-Za-z]{2})?(?:,\s*[A-Za-z]{2}(?:-[A-Za-z]{2})?)*)\s+([\d:]{4,5}-[\d:]{4,5}(?:\s*,\s*[\d:]{4,5}-[\d:]{4,5})*)$', rule)
    if not m:
        return None
    days_part, times_part = m.groups()
    days = sorted(set(day for dseg in days_part.split(",") for day in expand_days(dseg.strip())))
    ranges = [(parse_time(a), parse_time(b)) for rseg in times_part.split(",") if "-" in rseg for a, b in [rseg.split("-")] if (ta := parse_time(a)) and (tb := parse_time(b))]
    return {"days": days, "ranges": ranges} if days and ranges else None

def is_open_now(opening_hours: str, now_local: datetime):
    if not opening_hours:
        return None, "표기 없음"
    oh = opening_hours.strip()
    if oh.lower() in ("24/7", "24x7", "24-7"):
        return True, "24/7"
    parts = [p.strip() for p in oh.split(";") if p.strip()]
    weekday = now_local.weekday()
    now_t = now_local.time()

    open_flag = False
    for part in parts:
        if "PH" in part or "off" in part.lower():
            continue
        if re.match(r'^[\d:]{4,5}-[\d:]{4,5}$', part):
            ta, tb = parse_time(part.split("-")[0]), parse_time(part.split("-")[1])
            if ta and tb and ta <= now_t <= tb:
                open_flag = True
            continue
        rule = parse_rule(part)
        if rule and weekday in rule["days"]:
            for ta, tb in rule["ranges"]:
                if tb < ta and (now_t >= ta or now_t <= tb) or (ta <= now_t <= tb):
                    open_flag = True
                    break
    return open_flag, opening_hours if any_known else None, opening_hours

def tz_at(lat, lon):
    try:
        tzname = TimezoneFinder().timezone_at(lat=lat, lng=lon)
        return pytz.timezone(tzname) if tzname else pytz.timezone("Asia/Seoul")
    except Exception:
        return pytz.timezone("Asia/Seoul")

with st.sidebar:
    st.subheader("검색 옵션")
    radius = st.slider("반경 (m)", 200, 3000, 800, step=100)
    open_only = st.checkbox("지금 영업중만 보기", value=True)
    st.caption("데이터: OpenStreetMap(Overpass API)")

st.markdown("### 1) 위치 정하기")
col1, col2 = st.columns(2)
with col1:
    address = st.text_input("주소로 찾기 (예: 강남역, 남양주시청 등)", "")
with col2:
    if st.button("주소로 위치 지정") and address.strip():
        try:
            geolocator = Nominatim(user_agent="pharmacy-open-now")
            loc = geolocator.geocode(address)
            if loc:
                st.session_state["center"] = (loc.latitude, loc.longitude)
                st.success(f"위치 설정 완료: {loc.address}")
            else:
                st.error("주소를 찾을 수 없어요. 다른 표현으로 시도해보세요.")
        except Exception as e:
            st.error(f"지오코딩 오류: {e}")

if "center" not in st.session_state:
    st.session_state["center"] = (37.5663, 126.9779)  # 기본: 서울시청

center = st.session_state["center"]

st.markdown("### 2) 지도를 클릭해도 위치 지정돼요")
m = folium.Map(location=center, zoom_start=14, control_scale=True)
folium.Marker(center, tooltip="현재 중심").add_to(m)
map_data = st_folium(m, height=420, use_container_width=True)

if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]
    st.session_state["center"] = (lat, lon)
    st.info(f"지도 클릭 위치: {lat:.5f}, {lon:.5f}")

center = st.session_state["center"]

st.markdown("### 3) 주변 약국 검색")
if st.button("검색 실행", type="primary"):
    lat, lon = center
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"="pharmacy"](around:{radius},{lat},{lon});
      way["amenity"="pharmacy"](around:{radius},{lat},{lon});
      relation["amenity"="pharmacy"](around:{radius},{lat},{lon});
    );
    out center tags;
    """
    try:
        r = requests.post(overpass_url, data={"data": query}, timeout=30)
        r.raise_for_status()
        data = r.json()
        elements = data.get("elements", [])
        tz = tz_at(lat, lon)
        now_local = datetime.now(tz)

        rows = []
        for el in elements:
            plat, plon = (el.get("lat"), el.get("lon")) if el.get("type") == "node" else (el.get("center", {}).get("lat"), el.get("center", {}).get("lon"))
            tags = el.get("tags", {})
            name = tags.get("name", "(이름 없음)")
            phone = tags.get("phone") or tags.get("contact:phone") or ""
            opening = tags.get("opening_hours", "")
            open_now, opening_disp = is_open_now(opening, now_local)

            dist_m = round(haversine((lat, lon), (plat, plon), unit="m"))
            rows.append({
                "이름": name,
                "거리(m)": dist_m,
                "영업여부": "영업중" if open_now is True else ("영업종료" if open_now is False else "확인필요"),
                "영업시간": opening_disp,
                "전화": phone,
                "위도": plat,
                "경도": plon,
                "네이버지도": f"https://map.naver.com/v5/search/{name}/place",
                "카카오맵": f"https://map.kakao.com/?q={name}"
            })

        if not rows:
            st.warning("해당 범위에서 약국을 찾지 못했어요. 반경을 넓혀보세요!")
        else:
            df = pd.DataFrame(rows)
            if open_only:
                df = df[df["영업여부"] == "영업중"]
            df["정렬키"] = df["영업여부"].map({"영업중": 0, "확인필요": 1, "영업종료": 2})
            df = df.sort_values(["정렬키", "거리(m)"]).drop(columns=["정렬키"]).reset_index(drop=True)

            st.success(f"결과 {len(df)}곳")
            st.dataframe(df[["이름", "거리(m)", "영업여부", "영업시간", "전화", "네이버지도", "카카오맵"]], use_container_width=True)

            fmap = folium.Map(location=(lat, lon), zoom_start=14, control_scale=True)
            folium.Circle((lat, lon), radius=radius, color="blue", fill=False, opacity=0.35).add_to(fmap)
            folium.Marker((lat, lon), tooltip="검색 중심", icon=folium.Icon(icon="home")).add_to(fmap)

            for _, row in df.iterrows():
                color = "green" if row["영업여부"] == "영업중" else ("red" if row["영업여부"] == "영업종료" else "blue")
                folium.Marker(
                    (row["위도"], row["경도"]),
                    tooltip=f"{row['이름']} • {row['거리(m)']}m • {row['영업여부']}",
                    popup=(row["이름"] + (f"<br/>{row['영업시간']}" if row["영업시간"] else "")),
                    icon=folium.Icon(color=color)
                ).add_to(fmap)

            st_folium(fmap, height=440, use_container_width=True)
            st.caption("ℹ️ ‘확인필요’는 복잡한 영업시간 표기(공휴일/격주 등)로 자동판별이 어려운 경우예요.")
    except Exception as e:
        st.error(f"검색 중 오류: {e}")
else:
    st.caption("주소로 지정하거나, 지도를 클릭해 위치를 정한 뒤 ‘검색 실행’을 눌러주세요.")
```

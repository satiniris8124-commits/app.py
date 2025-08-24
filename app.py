# -*- coding: utf-8 -*-
# 💊 약국 찾기 앱 (주소 검색창 + 지도 클릭 + 영업중 필터 + 결과 유지)
# Streamlit Community Cloud 용

import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium
from haversine import haversine
from datetime import datetime, time
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim
import pytz
import re
import time as _time

# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(page_title="약국 찾기", page_icon="💊", layout="wide")
st.title("💊 내 주변 약국 찾기 (주소 검색 + 지도 클릭 + 결과 유지)")

# -----------------------------
# 세션 상태 초기화
# -----------------------------
for key, default in [
    ("last_df", None),            # 마지막 검색 결과 DataFrame
    ("last_center", None),        # 마지막 검색 중심 (lat, lon)
    ("last_radius", None),        # 마지막 검색 반경
    ("pending_center", None),     # 지도에서 클릭해 둔 임시 중심
]:
    if key not in st.session_state: st.session_state[key] = default

DEFAULT_CENTER = (37.5663, 126.9779)  # 서울시청

# -----------------------------
# 타임존 유틸
# -----------------------------
def tz_at(lat, lon):
    try:
        tzname = TimezoneFinder().timezone_at(lat=lat, lng=lon)
        if tzname:
            return pytz.timezone(tzname)
    except Exception:
        pass
    return pytz.timezone("Asia/Seoul")

# -----------------------------
# Overpass 안정 호출 (미러 회전 + 재시도)
# -----------------------------
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]
HEADERS = {
    "User-Agent": "pharmacy-open-now/1.0 (contact: youremail@example.com)"
}
def fetch_overpass(query, max_tries=6, backoff=1.6):
    last_err = None
    for attempt in range(max_tries):
        endpoint = OVERPASS_ENDPOINTS[attempt % len(OVERPASS_ENDPOINTS)]
        try:
            r = requests.post(endpoint, data={"data": query}, headers=HEADERS, timeout=45)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError as he:
            status = getattr(he.response, "status_code", None)
            if status in (429, 502, 503, 504):
                _time.sleep(backoff ** attempt); last_err = he; continue
            last_err = he
        except Exception as e:
            last_err = e
            _time.sleep(backoff ** attempt)
            continue
    raise RuntimeError(f"Overpass 요청 실패: {last_err}")

# -----------------------------
# opening_hours 파서 (일반 패턴)
# -----------------------------
DAY_MAP = {"Mo":0,"Tu":1,"We":2,"Th":3,"Fr":4,"Sa":5,"Su":6}
def _parse_time(tstr):
    try:
        hh, mm = tstr.split(":"); return time(int(hh), int(mm))
    except Exception: return None
def _expand_days(part):
    if "-" in part:
        a,b = part.split("-")
        if a in DAY_MAP and b in DAY_MAP:
            ai,bi = DAY_MAP[a],DAY_MAP[b]
            return list(range(ai,bi+1)) if ai<=bi else list(range(ai,7))+list(range(0,bi+1))
    else:
        if part in DAY_MAP: return [DAY_MAP[part]]
    return []
def _parse_rule(rule):
    rule = rule.strip()
    m = re.match(r'^([A-Za-z]{2}(?:-[A-Za-z]{2})?(?:,\s*[A-Za-z]{2}(?:-[A-Za-z]{2})?)*)\s+([\d:]{4,5}-[\d:]{4,5}(?:\s*,\s*[\d:]{4,5}-[\d:]{4,5})*)$', rule)
    if not m: return None
    days_part, times_part = m.groups()
    days = sorted(set(sum((_expand_days(s.strip()) for s in days_part.split(",")), [])))
    ranges = []
    for seg in [s.strip() for s in times_part.split(",")]:
        if "-" in seg:
            a,b = seg.split("-"); ta,tb = _parse_time(a),_parse_time(b)
            if ta and tb: ranges.append((ta,tb))
    if not days or not ranges: return None
    return {"days":days,"ranges":ranges}
def is_open_now(opening_hours: str, now_local: datetime):
    if not opening_hours: return None, "표기 없음"
    oh = opening_hours.strip()
    if oh.lower() in ("24/7","24x7","24-7"): return True, "24/7"
    parts = [p.strip() for p in oh.split(";") if p.strip()]
    wd = now_local.weekday(); now_t = now_local.time()
    any_known = False; open_flag = False
    for part in parts:
        if "PH" in part or "off" in part.lower(): continue
        if re.match(r'^[\d:]{4,5}-[\d:]{4,5}$', part):
            ta,tb = _parse_time(part.split("-")[0]), _parse_time(part.split("-")[1])
            if ta and tb:
                any_known = True
                if ta <= now_t <= tb: open_flag = True
            continue
        rule = _parse_rule(part)
        if not rule: continue
        any_known = True
        if wd in rule["days"]:
            for ta,tb in rule["ranges"]:
                if tb < ta:
                    if now_t >= ta or now_t <= tb: open_flag = True; break
                else:
                    if ta <= now_t <= tb: open_flag = True; break
    return (open_flag, opening_hours) if any_known else (None, opening_hours)

# -----------------------------
# 1) 주소 검색창 (지오코딩으로 중심 잡기)
# -----------------------------
st.markdown("### 1) 지역(주소) 검색")
with st.form("addr_form"):
    col1, col2 = st.columns([4,1])
    with col1:
        addr_query = st.text_input("주소/장소명을 입력하세요 (예: 남양주시청, 강남역, 여의도공원)", "")
    with col2:
        addr_submit = st.form_submit_button("주소로 위치 지정")
if addr_submit and addr_query.strip():
    try:
        geolocator = Nominatim(user_agent="pharmacy-open-now/1.0 (contact: youremail@example.com)")
        loc = geolocator.geocode(addr_query)
        if loc:
            st.session_state["last_center"] = (loc.latitude, loc.longitude)
            st.success(f"위치 설정 완료: {loc.address}")
        else:
            st.warning("주소를 찾지 못했어요. 다른 표현으로 시도해보세요.")
    except Exception as e:
        st.error(f"지오코딩 오류: {e}")

# 현재 검색 중심
current_center = st.session_state["last_center"] or DEFAULT_CENTER

# -----------------------------
# 2) 지도에서 위치 선택(임시 → 버튼으로 확정)
# -----------------------------
st.markdown("### 2) 지도에서 위치 선택 (선택 사항)")
m = folium.Map(location=current_center, zoom_start=14, control_scale=True)
folium.Marker(current_center, tooltip="현재 검색 중심").add_to(m)
map_data = st_folium(m, height=420, use_container_width=True)

if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]; lon = map_data["last_clicked"]["lng"]
    st.session_state["pending_center"] = (lat, lon)
    st.info(f"지도에서 선택: {lat:.5f}, {lon:.5f} (아래 버튼으로 확정)")

colA, colB = st.columns(2)
with colA:
    if st.session_state["pending_center"] is not None:
        if st.button("이 위치로 검색 중심 확정"):
            st.session_state["last_center"] = st.session_state["pending_center"]
            st.session_state["pending_center"] = None
            st.success("검색 중심을 갱신했어요!")
with colB:
    if st.button("이전 검색 결과 지우기"):
        st.session_state["last_df"] = None
        st.session_state["last_radius"] = None
        st.info("이전 검색 결과를 지웠어요.")

# 확정된 검색 중심
search_center = st.session_state["last_center"] or current_center

# -----------------------------
# 3) 검색 옵션 (폼으로 묶기 → rerun 억제)
# -----------------------------
st.markdown("### 3) 검색 옵션")
with st.form("search"):
    radius = st.slider("반경 (m)", 200, 3000, st.session_state["last_radius"] or 1200, step=100)
    open_only = st.checkbox("지금 영업중만 보기", value=True)
    do_search = st.form_submit_button("검색 실행")

# -----------------------------
# 4) 검색 실행 (성공 시 세션 저장 → 결과 유지)
# -----------------------------
if do_search:
    lat, lon = search_center
    tz = tz_at(lat, lon); now_local = datetime.now(tz)
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
        data = fetch_overpass(query)
        elements = data.get("elements", [])
        rows = []
        for el in elements:
            if el.get("type") == "node":
                plat, plon = el.get("lat"), el.get("lon")
            else:
                c = el.get("center")
                if not c: continue
                plat, plon = c.get("lat"), c.get("lon")

            tags = el.get("tags", {}) or {}
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
                "위도": plat, "경도": plon,
                "네이버지도": f"https://map.naver.com/v5/search/{name}/place",
                "카카오맵": f"https://map.kakao.com/?q={name}",
            })

        df = pd.DataFrame(rows)
        if open_only and not df.empty:
            df = df[df["영업여부"] == "영업중"]

        # ✅ 세션 저장 (rerun 되어도 결과 유지)
        st.session_state["last_df"] = df.copy()
        st.session_state["last_center"] = (lat, lon)
        st.session_state["last_radius"] = radius

        st.success(f"검색 완료: {len(df)}곳")
    except Exception as e:
        st.error(f"검색 중 오류: {e}")
        st.info("무료 Overpass 미러가 바쁠 수 있어요. 잠시 후 재시도하거나 반경을 넓혀보세요.")

# -----------------------------
# 5) 마지막 검색 결과 항상 렌더 (버튼 안 눌러도 유지)
# -----------------------------
st.markdown("### 4) 검색 결과")
if st.session_state["last_df"] is not None:
    df = st.session_state["last_df"]
    lat, lon = st.session_state["last_center"] or DEFAULT_CENTER
    radius = st.session_state["last_radius"] or 1200

    st.dataframe(df[["이름","거리(m)","영업여부","영업시간","전화","네이버지도","카카오맵"]],
                 use_container_width=True)

    fmap = folium.Map(location=(lat, lon), zoom_start=14, control_scale=True)
    folium.Circle((lat, lon), radius=radius, color="blue", fill=False, opacity=0.35).add_to(fmap)
    folium.Marker((lat, lon), tooltip="검색 중심", icon=folium.Icon(icon="home")).add_to(fmap)

    for _, row in df.iterrows():
        color = "green" if row["영업여부"]=="영업중" else ("red" if row["영업여부"]=="영업종료" else "blue")
        folium.Marker(
            (row["위도"], row["경도"]),
            tooltip=f"{row['이름']} • {row['거리(m)']}m • {row['영업여부']}",
            popup=(row["이름"] + (f"<br/>{row['영업시간']}" if row["영업시간"] else "")),
            icon=folium.Icon(color=color)
        ).add_to(fmap)

    st_folium(fmap, height=440, use_container_width=True)
else:
    st.caption("아직 검색 결과가 없어요. 주소로 위치 지정하거나, 지도를 클릭해 ‘검색 중심 확정’ → ‘검색 실행’을 눌러주세요.")

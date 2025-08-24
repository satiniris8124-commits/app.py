# -*- coding: utf-8 -*-
# 💊 약국 찾기 앱 (주소 검색 + 지도 클릭 + 결과 유지 + 영업중 필터 정확화)
# - Overpass 미러 회전/재시도
# - 약국 태그 확장: amenity=pharmacy | healthcare=pharmacy | shop=chemist | name~약국/Pharm
# - 결과 0개면 반경 자동 확대 재탐색
# - Streamlit rerun에도 결과 유지(session_state)

import streamlit as st
import pandas as pd
import requests, re
import folium
from streamlit_folium import st_folium
from haversine import haversine
from datetime import datetime, time
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim
import pytz, time as _time

# -----------------------------
# 기본 UI 설정
# -----------------------------
st.set_page_config(page_title="약국 찾기", page_icon="💊", layout="wide")
st.title("💊 내 주변 약국 찾기")

# -----------------------------
# 세션 기본값
# -----------------------------
for k, v in [
    ("last_df", None),                # 마지막 검색 결과
    ("last_center", None),            # 마지막 검색 중심(lat, lon)
    ("last_radius", 1200),            # 마지막 검색 반경
    ("pending_center", None),         # 지도 클릭으로 임시 선택중인 중심
]:
    if k not in st.session_state:
        st.session_state[k] = v

DEFAULT_CENTER = (37.5663, 126.9779)  # 서울시청
DISPLAY_COLS = ["이름","거리(m)","영업여부","영업시간","전화","네이버지도","카카오맵"]

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
OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]
UA = {"User-Agent": "pharmacy-open-now/1.0 (contact: you@example.com)"}

def fetch_overpass(query, tries=6, backoff=1.6):
    err = None
    for i in range(tries):
        url = OVERPASS[i % len(OVERPASS)]
        try:
            r = requests.post(url, data={"data": query}, headers=UA, timeout=45)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError as he:
            code = getattr(he.response, "status_code", None)
            if code in (429, 502, 503, 504):
                err = he
                _time.sleep(backoff ** i)
                continue
            raise
        except Exception as e:
            err = e
            _time.sleep(backoff ** i)
            continue
    raise RuntimeError(f"Overpass 실패: {err}")

# -----------------------------
# opening_hours 파서 (일반 패턴)
# -----------------------------
DAY = {"Mo":0,"Tu":1,"We":2,"Th":3,"Fr":4,"Sa":5,"Su":6}

def _t(s):
    try:
        h, m = s.split(":")
        return time(int(h), int(m))
    except Exception:
        return None

def _days(seg):
    if "-" in seg:
        a, b = seg.split("-")
        if a in DAY and b in DAY:
            i, j = DAY[a], DAY[b]
            return list(range(i, j+1)) if i <= j else list(range(i, 7)) + list(range(0, j+1))
    return [DAY[seg]] if seg in DAY else []

def _rule(s):
    m = re.match(r'^([A-Za-z]{2}(?:-[A-Za-z]{2})?(?:,\s*[A-Za-z]{2}(?:-[A-Za-z]{2})?)*)\s+'
                 r'([\d:]{4,5}-[\d:]{4,5}(?:\s*,\s*[\d:]{4,5}-[\d:]{4,5})*)$', s.strip())
    if not m:
        return None
    dpart, tpart = m.groups()
    days = sorted(set(sum((_days(x.strip()) for x in dpart.split(",")), [])))
    ranges = []
    for seg in [x.strip() for x in tpart.split(",")]:
        if "-" in seg:
            a, b = seg.split("-")
            ta, tb = _t(a), _t(b)
            if ta and tb:
                ranges.append((ta, tb))
    return {"days": days, "ranges": ranges} if days and ranges else None

def is_open_now(oh, now_local: datetime):
    if not oh:
        return None, "표기 없음"
    s = oh.strip()
    if s.lower() in ("24/7", "24x7", "24-7"):
        return True, "24/7"
    wd, nowt = now_local.weekday(), now_local.time()
    known, opened = False, False
    for part in [p.strip() for p in s.split(";") if p.strip()]:
        if "PH" in part or "off" in part.lower():
            continue
        if re.match(r'^[\d:]{4,5}-[\d:]{4,5}$', part):
            ta, tb = _t(part.split("-")[0]), _t(part.split("-")[1])
            if ta and tb:
                known = True
                if ta <= nowt <= tb:
                    opened = True
            continue
        rule = _rule(part)
        if not rule:
            continue
        known = True
        if wd in rule["days"]:
            for ta, tb in rule["ranges"]:
                if tb < ta:  # 자정 넘어감
                    if nowt >= ta or nowt <= tb:
                        opened = True; break
                else:
                    if ta <= nowt <= tb:
                        opened = True; break
    return (opened, oh) if known else (None, oh)

# -----------------------------
# Overpass 쿼리 (태그 확장)
# -----------------------------
def build_overpass_query(lat, lon, radius):
    return f"""
    [out:json][timeout:40];
    (
      node["amenity"="pharmacy"](around:{radius},{lat},{lon});
      way ["amenity"="pharmacy"](around:{radius},{lat},{lon});
      relation["amenity"="pharmacy"](around:{radius},{lat},{lon});

      node["healthcare"="pharmacy"](around:{radius},{lat},{lon});
      way ["healthcare"="pharmacy"](around:{radius},{lat},{lon});
      relation["healthcare"="pharmacy"](around:{radius},{lat},{lon});

      node["shop"="chemist"](around:{radius},{lat},{lon});
      way ["shop"="chemist"](around:{radius},{lat},{lon});
      relation["shop"="chemist"](around:{radius},{lat},{lon});

      node[name~"(?i)pharm|약국"](around:{radius},{lat},{lon});
      way [name~"(?i)pharm|약국"](around:{radius},{lat},{lon});
      relation[name~"(?i)pharm|약국"](around:{radius},{lat},{lon});
    );
    out center tags;
    """

# -----------------------------
# 1) 주소 검색
# -----------------------------
st.markdown("### 1) 지역(주소) 검색")
with st.form("addr"):
    c1, c2 = st.columns([4, 1])
    with c1:
        addr = st.text_input("주소/장소명 (예: 남양주시청, 강남역)", "")
    with c2:
        addr_submit = st.form_submit_button("주소로 위치 지정")
if addr_submit and addr.strip():
    try:
        geo = Nominatim(user_agent="pharmacy-open-now/1.0 (contact: you@example.com)")
        loc = geo.geocode(addr)
        if loc:
            st.session_state["last_center"] = (loc.latitude, loc.longitude)
            st.success(f"위치 설정: {loc.address}")
        else:
            st.warning("주소를 찾지 못했어요. 다른 표현으로 시도해보세요.")
    except Exception as e:
        st.error(f"지오코딩 오류: {e}")

# 현재 검색 중심
current_center = st.session_state["last_center"] or DEFAULT_CENTER

# -----------------------------
# 2) 지도에서 위치 선택 (임시 → 확정 버튼)
# -----------------------------
st.markdown("### 2) 지도에서 위치 선택 (선택 사항)")
m = folium.Map(location=current_center, zoom_start=14, control_scale=True)
folium.Marker(current_center, tooltip="현재 검색 중심").add_to(m)
md = st_folium(m, height=420, use_container_width=True)

if md and md.get("last_clicked"):
    lat, lon = md["last_clicked"]["lat"], md["last_clicked"]["lng"]
    st.session_state["pending_center"] = (lat, lon)
    st.info(f"지도에서 선택: {lat:.5f}, {lon:.5f} (아래 버튼으로 확정)")

cA, cB = st.columns(2)
with cA:
    if st.session_state["pending_center"] is not None:
        if st.button("이 위치로 검색 중심 확정"):
            st.session_state["last_center"] = st.session_state["pending_center"]
            st.session_state["pending_center"] = None
            st.success("검색 중심을 갱신했습니다.")
with cB:
    if st.button("이전 검색 결과 지우기"):
        st.session_state["last_df"] = None
        st.info("이전 검색 결과를 지웠습니다.")

search_center = st.session_state["last_center"] or current_center

# -----------------------------
# 3) 옵션 & 검색 실행
# -----------------------------
st.markdown("### 3) 검색 옵션")
with st.form("search"):
    radius = st.slider("반경 (m)", 200, 3000, st.session_state["last_radius"], step=100)
    open_only = st.checkbox("지금 영업중만 보기", value=True)
    submit = st.form_submit_button("검색 실행")

if submit:
    lat, lon = search_center
    tz = tz_at(lat, lon)
    now_local = datetime.now(tz)

    # 1차 탐색
    query = build_overpass_query(lat, lon, radius)
    data = fetch_overpass(query)
    elements = data.get("elements", [])

    # 0개면 자동 반경 확대 재탐색 (최대 3000m)
    if not elements and radius < 3000:
        alt_radius = min(3000, max(radius + 800, int(radius * 1.6)))
        st.info(f"반경 내 결과가 없어 {alt_radius}m로 자동 재탐색합니다.")
        query = build_overpass_query(lat, lon, alt_radius)
        data = fetch_overpass(query)
        elements = data.get("elements", [])
        radius = alt_radius  # 지도/세션에 반영

    # 결과 가공
    rows = []
    for el in elements:
        if el.get("type") == "node":
            plat, plon = el.get("lat"), el.get("lon")
        else:
            c = el.get("center")
            if not c:
                continue
            plat, plon = c.get("lat"), c.get("lon")

        tags = el.get("tags", {}) or {}
        name = tags.get("name") or tags.get("alt_name") or "(이름 없음)"
        phone = tags.get("phone") or tags.get("contact:phone") or ""
        opening = tags.get("opening_hours", "")
        opened, opening_disp = is_open_now(opening, now_local)
        dist = round(haversine((lat, lon), (plat, plon), unit="m"))

        rows.append({
            "이름": name,
            "거리(m)": dist,
            "영업여부": "영업중" if opened is True else ("영업종료" if opened is False else "확인필요"),
            "영업시간": opening_disp,
            "전화": phone,
            "위도": plat,
            "경도": plon,
            "네이버지도": f"https://map.naver.com/v5/search/{name}/place",
            "카카오맵": f"https://map.kakao.com/?q={name}",
        })

    # 빈 결과여도 컬럼 뼈대 유지
    df = pd.DataFrame(
        rows,
        columns=["이름","거리(m)","영업여부","영업시간","전화","위도","경도","네이버지도","카카오맵"]
    )

    # 영업중만 보기 토글
    if not df.empty:
        if open_only:
            df = df[df["영업여부"].astype(str) == "영업중"]
        # 정렬: 영업중 → 확인필요 → 영업종료 → 거리
        order = {"영업중": 0, "확인필요": 1, "영업종료": 2}
        df["__ord__"] = df["영업여부"].map(order).fillna(9)
        df = df.sort_values(["__ord__", "거리(m)"]).drop(columns="__ord__")

    # 세션 저장(결과 유지)
    st.session_state["last_df"] = df.reset_index(drop=True)
    st.session_state["last_center"] = (lat, lon)
    st.session_state["last_radius"] = radius

    st.success(f"검색 완료: {len(df)}곳")

# -----------------------------
# 4) 결과 출력 (항상 유지)
# -----------------------------
st.markdown("### 4) 검색 결과")
df = st.session_state["last_df"]
if df is None:
    st.caption("아직 검색 결과가 없어요. 주소 지정 또는 지도 클릭 후 ‘검색 실행’을 눌러주세요.")
else:
    cols = [c for c in DISPLAY_COLS if c in df.columns]  # 안전 표시
    if df.empty:
        st.warning("반경 내 결과가 없습니다. 반경을 넓혀보거나 중심을 옮겨보세요.")
        st.dataframe(pd.DataFrame(columns=cols), use_container_width=True)
    else:
        st.dataframe(df[cols], use_container_width=True)

        lat, lon = st.session_state["last_center"] or DEFAULT_CENTER
        r = st.session_state["last_radius"] or 1200

        fmap = folium.Map(location=(lat, lon), zoom_start=14, control_scale=True)
        folium.Circle((lat, lon), radius=r, color="blue", fill=False, opacity=0.35).add_to(fmap)
        folium.Marker((lat, lon), tooltip="검색 중심", icon=folium.Icon(icon="home")).add_to(fmap)

        for _, row in df.iterrows():
            color = "green" if row.get("영업여부") == "영업중" else ("red" if row.get("영업여부") == "영업종료" else "blue")
            folium.Marker(
                (row["위도"], row["경도"]),
                tooltip=f"{row.get('이름','(이름 없음)')} • {row.get('거리(m)','?')}m • {row.get('영업여부','?')}",
                popup=(row.get("이름","") + (f"<br/>{row.get('영업시간')}" if row.get("영업시간") else "")),
                icon=folium.Icon(color=color)
            ).add_to(fmap)

        st_folium(fmap, height=440, use_container_width=True)

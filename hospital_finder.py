import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import requests
import json
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
import time

# 페이지 설정
st.set_page_config(
    page_title="소아과 병원 찾기",
    page_icon="🏥",
    layout="wide"
)

# 샘플 병원 데이터 (실제로는 API나 데이터베이스에서 가져와야 함)
@st.cache_data
def load_hospital_data():
    hospitals = [
        {
            "name": "서울대학교병원",
            "address": "서울특별시 종로구 대학로 101",
            "lat": 37.5793,
            "lon": 126.9999,
            "type": "종합병원",
            "pediatric_dept": True,
            "pediatric_emergency": True,
            "phone": "02-2072-2114",
            "description": "소아청소년과, 소아응급실 24시간 운영"
        },
        {
            "name": "연세대학교 세브란스병원",
            "address": "서울특별시 서대문구 연세로 50-1",
            "lat": 37.5597,
            "lon": 126.9401,
            "type": "종합병원",
            "pediatric_dept": True,
            "pediatric_emergency": True,
            "phone": "02-2228-5800",
            "description": "소아청소년과, 소아응급실 24시간 운영"
        },
        {
            "name": "삼성서울병원",
            "address": "서울특별시 강남구 일원로 81",
            "lat": 37.4881,
            "lon": 127.0857,
            "type": "종합병원",
            "pediatric_dept": True,
            "pediatric_emergency": True,
            "phone": "02-3410-2114",
            "description": "소아청소년과, 소아응급실 24시간 운영"
        },
        {
            "name": "아산병원",
            "address": "서울특별시 송파구 올림픽로43길 88",
            "lat": 37.5262,
            "lon": 127.1080,
            "type": "종합병원",
            "pediatric_dept": True,
            "pediatric_emergency": True,
            "phone": "02-3010-3114",
            "description": "소아청소년과, 소아응급실 24시간 운영"
        },
        {
            "name": "서울아산병원 어린이병원",
            "address": "서울특별시 송파구 올림픽로43길 88",
            "lat": 37.5265,
            "lon": 127.1085,
            "type": "어린이전문병원",
            "pediatric_dept": True,
            "pediatric_emergency": True,
            "phone": "02-3010-3300",
            "description": "소아 전문 진료, 소아응급실 24시간 운영"
        },
        {
            "name": "고려대학교 안암병원",
            "address": "서울특별시 성북구 고려대로 73",
            "lat": 37.5866,
            "lon": 127.0265,
            "type": "종합병원",
            "pediatric_dept": True,
            "pediatric_emergency": False,
            "phone": "02-920-5114",
            "description": "소아청소년과 운영"
        },
        {
            "name": "서울성모병원",
            "address": "서울특별시 서초구 반포대로 222",
            "lat": 37.5014,
            "lon": 126.9975,
            "type": "종합병원",
            "pediatric_dept": True,
            "pediatric_emergency": True,
            "phone": "02-2258-5114",
            "description": "소아청소년과, 소아응급실 운영"
        },
        {
            "name": "강남세브란스병원",
            "address": "서울특별시 강남구 언주로 211",
            "lat": 37.5194,
            "lon": 127.0374,
            "type": "종합병원",
            "pediatric_dept": True,
            "pediatric_emergency": False,
            "phone": "02-2019-3114",
            "description": "소아청소년과 운영"
        }
    ]
    return pd.DataFrame(hospitals)

# 주소를 좌표로 변환하는 함수
@st.cache_data
def geocode_address(address):
    try:
        geolocator = Nominatim(user_agent="pediatric_hospital_finder")
        location = geolocator.geocode(address + ", South Korea")
        if location:
            return location.latitude, location.longitude
        return None, None
    except:
        return None, None

# 거리 계산 함수
def calculate_distance(lat1, lon1, lat2, lon2):
    return geodesic((lat1, lon1), (lat2, lon2)).kilometers

# 지도 생성 함수
def create_map(hospitals_df, center_lat=37.5665, center_lon=126.9780, user_location=None):
    m = folium.Map(location=[center_lat, center_lon], zoom_start=11)
    
    # 사용자 위치 표시
    if user_location:
        folium.Marker(
            [user_location[0], user_location[1]],
            popup="내 위치",
            tooltip="내 위치",
            icon=folium.Icon(color='red', icon='user', prefix='fa')
        ).add_to(m)
    
    # 병원 마커 추가
    for idx, hospital in hospitals_df.iterrows():
        # 아이콘 색상 결정
        if hospital['pediatric_emergency']:
            color = 'blue'  # 응급실 있는 병원
            icon = 'plus-square'
        else:
            color = 'green'  # 일반 소아과
            icon = 'plus'
        
        popup_text = f"""
        <b>{hospital['name']}</b><br>
        주소: {hospital['address']}<br>
        전화: {hospital['phone']}<br>
        구분: {hospital['type']}<br>
        설명: {hospital['description']}
        """
        
        folium.Marker(
            [hospital['lat'], hospital['lon']],
            popup=folium.Popup(popup_text, max_width=300),
            tooltip=hospital['name'],
            icon=folium.Icon(color=color, icon=icon)
        ).add_to(m)
    
    return m

# 메인 애플리케이션
def main():
    st.title("🏥 소아과 병원 찾기")
    st.markdown("---")
    
    # 사이드바
    st.sidebar.title("검색 옵션")
    
    # 위치 입력
    st.sidebar.subheader("📍 위치 설정")
    location_input = st.sidebar.text_input("주소 또는 지역명을 입력하세요", placeholder="예: 강남구 또는 서울시 종로구")
    
    # 병원 타입 필터
    st.sidebar.subheader("🔍 병원 유형")
    show_general = st.sidebar.checkbox("소아과 있는 병원", value=True)
    show_emergency = st.sidebar.checkbox("소아응급실 있는 병원", value=True)
    
    # 거리 필터
    st.sidebar.subheader("📏 거리 범위")
    max_distance = st.sidebar.slider("최대 거리 (km)", 1, 50, 10)
    
    # 병원 데이터 로드
    hospitals_df = load_hospital_data()
    
    # 사용자 위치 처리
    user_lat, user_lon = None, None
    if location_input:
        with st.spinner("위치를 찾는 중..."):
            user_lat, user_lon = geocode_address(location_input)
            if user_lat is None:
                st.sidebar.error("주소를 찾을 수 없습니다. 다른 주소를 시도해보세요.")
            else:
                st.sidebar.success(f"위치를 찾았습니다!")
    
    # 병원 필터링
    filtered_hospitals = hospitals_df.copy()
    
    if not show_general and not show_emergency:
        st.warning("적어도 하나의 병원 유형을 선택해주세요.")
        return
    
    if not show_general:
        filtered_hospitals = filtered_hospitals[filtered_hospitals['pediatric_emergency'] == True]
    elif not show_emergency:
        filtered_hospitals = filtered_hospitals[filtered_hospitals['pediatric_emergency'] == False]
    
    # 거리 기반 필터링
    if user_lat and user_lon:
        distances = []
        for idx, hospital in filtered_hospitals.iterrows():
            distance = calculate_distance(user_lat, user_lon, hospital['lat'], hospital['lon'])
            distances.append(distance)
        
        filtered_hospitals = filtered_hospitals.copy()
        filtered_hospitals['distance'] = distances
        filtered_hospitals = filtered_hospitals[filtered_hospitals['distance'] <= max_distance]
        filtered_hospitals = filtered_hospitals.sort_values('distance')
    
    # 메인 컨텐츠 영역을 두 개 컬럼으로 분할
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🗺️ 병원 위치 지도")
        
        if len(filtered_hospitals) > 0:
            # 지도 중심점 설정
            if user_lat and user_lon:
                center_lat, center_lon = user_lat, user_lon
                user_location = (user_lat, user_lon)
            else:
                center_lat = filtered_hospitals['lat'].mean()
                center_lon = filtered_hospitals['lon'].mean()
                user_location = None
            
            # 지도 생성 및 표시
            map_obj = create_map(filtered_hospitals, center_lat, center_lon, user_location)
            st_folium(map_obj, width=700, height=500)
        else:
            st.info("검색 조건에 맞는 병원이 없습니다.")
    
    with col2:
        st.subheader("📋 병원 목록")
        
        if len(filtered_hospitals) > 0:
            for idx, hospital in filtered_hospitals.iterrows():
                with st.container():
                    st.markdown(f"**{hospital['name']}**")
                    st.markdown(f"📍 {hospital['address']}")
                    st.markdown(f"📞 {hospital['phone']}")
                    st.markdown(f"🏥 {hospital['type']}")
                    
                    # 특징 표시
                    features = []
                    if hospital['pediatric_dept']:
                        features.append("소아과")
                    if hospital['pediatric_emergency']:
                        features.append("소아응급실")
                    st.markdown(f"⚕️ {', '.join(features)}")
                    
                    # 거리 표시
                    if 'distance' in hospital:
                        st.markdown(f"📏 거리: {hospital['distance']:.1f}km")
                    
                    st.markdown(f"💬 {hospital['description']}")
                    st.markdown("---")
        else:
            st.info("검색 조건에 맞는 병원이 없습니다.")
    
    # 범례
    st.markdown("---")
    st.subheader("🔍 지도 범례")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("🔴 **내 위치**")
    with col2:
        st.markdown("🔵 **소아응급실 있는 병원**")
    with col3:
        st.markdown("🟢 **소아과 있는 병원**")

if __name__ == "__main__":
    main()

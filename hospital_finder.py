import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import requests
import json
from geopy.distance import geodesic
import time
import urllib.parse

# 페이지 설정
st.set_page_config(
    page_title="소아과 병원 찾기",
    page_icon="🏥",
    layout="wide"
)

# 한국 주요 지역 좌표 (검색 대안용)
KOREA_LOCATIONS = {
    # 서울 구별
    "강남구": (37.5172, 127.0473),
    "강동구": (37.5301, 127.1238),
    "강북구": (37.6370, 127.0256),
    "강서구": (37.5509, 126.8495),
    "관악구": (37.4784, 126.9516),
    "광진구": (37.5384, 127.0822),
    "구로구": (37.4954, 126.8874),
    "금천구": (37.4569, 126.8953),
    "노원구": (37.6544, 127.0566),
    "도봉구": (37.6688, 127.0471),
    "동대문구": (37.5744, 127.0398),
    "동작구": (37.5124, 126.9393),
    "마포구": (37.5664, 126.9020),
    "서대문구": (37.5791, 126.9368),
    "서초구": (37.4837, 127.0324),
    "성동구": (37.5636, 127.0365),
    "성북구": (37.5894, 127.0167),
    "송파구": (37.5145, 127.1059),
    "양천구": (37.5169, 126.8664),
    "영등포구": (37.5264, 126.8963),
    "용산구": (37.5326, 126.9910),
    "은평구": (37.6176, 126.9227),
    "종로구": (37.5735, 126.9788),
    "중구": (37.5640, 126.9970),
    "중랑구": (37.6063, 127.0925),
    
    # 주요 도시
    "부산": (35.1796, 129.0756),
    "대구": (35.8714, 128.6014),
    "인천": (37.4563, 126.7052),
    "광주": (35.1595, 126.8526),
    "대전": (36.3504, 127.3845),
    "울산": (35.5384, 129.3114),
    "세종": (36.4800, 127.2890),
    
    # 경기도 주요 시
    "수원": (37.2636, 127.0286),
    "성남": (37.4201, 127.1262),
    "고양": (37.6584, 126.8320),
    "용인": (37.2411, 127.1776),
    "부천": (37.5034, 126.7660),
    "안산": (37.3218, 126.8309),
    "안양": (37.3943, 126.9568),
    "남양주": (37.6361, 127.2167),
    "화성": (37.1996, 126.8311),
    "평택": (36.9921, 127.1125),
    "의정부": (37.7384, 127.0330),
    "시흥": (37.3800, 126.8031),
    "파주": (37.7599, 126.7800),
    "김포": (37.6149, 126.7158),
    "광명": (37.4784, 126.8644),
    "광주시": (37.4292, 127.2550),
    "군포": (37.3617, 126.9352),
    "하남": (37.5390, 127.2056)
}

# 샘플 병원 데이터
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
            "description": "소아청소년과, 소아응급실 24시간 운영",
            "website": "http://www.snuh.org"
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
            "description": "소아청소년과, 소아응급실 24시간 운영",
            "website": "https://www.severance.healthcare"
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
            "description": "소아청소년과, 소아응급실 24시간 운영",
            "website": "http://www.samsunghospital.com"
        },
        {
            "name": "서울아산병원",
            "address": "서울특별시 송파구 올림픽로43길 88",
            "lat": 37.5262,
            "lon": 127.1080,
            "type": "종합병원",
            "pediatric_dept": True,
            "pediatric_emergency": True,
            "phone": "02-3010-3114",
            "description": "소아청소년과, 소아응급실 24시간 운영",
            "website": "http://www.amc.seoul.kr"
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
            "description": "소아 전문 진료, 소아응급실 24시간 운영",
            "website": "http://www.amc.seoul.kr/asan/mobile/healthinfo/management/managementView.do?managementId=383"
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
            "description": "소아청소년과 운영",
            "website": "https://www.anam.kumc.or.kr"
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
            "description": "소아청소년과, 소아응급실 운영",
            "website": "https://www.cmcseoul.or.kr"
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
            "description": "소아청소년과 운영",
            "website": "https://gs.iseverance.com"
        },
        {
            "name": "분당서울대학교병원",
            "address": "경기도 성남시 분당구 구미로 173번길 82",
            "lat": 37.3520,
            "lon": 127.1245,
            "type": "종합병원",
            "pediatric_dept": True,
            "pediatric_emergency": True,
            "phone": "031-787-7114",
            "description": "소아청소년과, 소아응급실 운영",
            "website": "https://www.snubh.org"
        },
        {
            "name": "인천성모병원",
            "address": "인천광역시 부평구 동수로 56",
            "lat": 37.4636,
            "lon": 126.7226,
            "type": "종합병원",
            "pediatric_dept": True,
            "pediatric_emergency": True,
            "phone": "032-280-5114",
            "description": "소아청소년과, 소아응급실 운영",
            "website": "https://www.cmcic.or.kr"
        }
    ]
    return pd.DataFrame(hospitals)

# 카카오맵 API를 사용한 주소 검색 (무료)
def search_address_with_kakao(address):
    try:
        # Kakao REST API (무료, 하지만 API 키 필요)
        # 실제로는 API 키가 필요하지만, 여기서는 대안 방법 사용
        pass
    except:
        return None, None

# 주소에서 지역명 추출하여 좌표 찾기
def search_location_by_region(address):
    """지역명을 기반으로 좌표 검색"""
    address_lower = address.lower().replace(" ", "")
    
    # 정확한 매칭 먼저 시도
    for region, coords in KOREA_LOCATIONS.items():
        if region in address or region.lower() in address_lower:
            return coords[0], coords[1], region
    
    # 부분 매칭 시도
    for region, coords in KOREA_LOCATIONS.items():
        if any(part in address_lower for part in region.lower()):
            return coords[0], coords[1], region
    
    return None, None, None

# OpenStreetMap Nominatim API를 사용한 백업 검색
def search_with_nominatim(address):
    try:
        # OpenStreetMap Nominatim API (무료)
        base_url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': f"{address}, South Korea",
            'format': 'json',
            'limit': 1,
            'addressdetails': 1
        }
        
        # User-Agent 헤더 추가 (필수)
        headers = {
            'User-Agent': 'PediatricHospitalFinder/1.0'
        }
        
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                lat = float(data[0]['lat'])
                lon = float(data[0]['lon'])
                display_name = data[0].get('display_name', address)
                return lat, lon, display_name
    except Exception as e:
        st.error(f"Nominatim 검색 오류: {e}")
    
    return None, None, None

# 통합 주소 검색 함수
def search_address(address):
    """여러 방법으로 주소 검색 시도"""
    if not address.strip():
        return None, None, None
    
    # 1. 먼저 한국 지역 데이터베이스에서 검색
    lat, lon, region = search_location_by_region(address)
    if lat and lon:
        return lat, lon, f"지역 검색: {region}"
    
    # 2. Nominatim API로 검색
    with st.spinner("온라인 주소 검색 중..."):
        time.sleep(1)  # API 요청 간격 조절
        lat, lon, display_name = search_with_nominatim(address)
        if lat and lon:
            return lat, lon, f"주소 검색: {display_name}"
    
    return None, None, None

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
            popup=folium.Popup("📍 내 위치", max_width=200),
            tooltip="내 위치",
            icon=folium.Icon(color='red', icon='user', prefix='fa')
        ).add_to(m)
    
    # 병원 마커 추가
    for idx, hospital in hospitals_df.iterrows():
        # 아이콘 색상 결정
        if hospital['pediatric_emergency']:
            color = 'blue'
            icon = 'plus-square'
            marker_type = "응급실"
        else:
            color = 'green'
            icon = 'plus'
            marker_type = "소아과"
        
        popup_html = f"""
        <div style="width:300px;">
            <h4>{hospital['name']}</h4>
            <p><b>📍 주소:</b> {hospital['address']}</p>
            <p><b>📞 전화:</b> {hospital['phone']}</p>
            <p><b>🏥 구분:</b> {hospital['type']}</p>
            <p><b>⚕️ 진료:</b> {marker_type}</p>
            <p><b>💬 설명:</b> {hospital['description']}</p>
            {'<p><b>🌐 웹사이트:</b> <a href="' + hospital['website'] + '" target="_blank">병원 홈페이지</a></p>' if 'website' in hospital and hospital['website'] else ''}
        </div>
        """
        
        folium.Marker(
            [hospital['lat'], hospital['lon']],
            popup=folium.Popup(popup_html, max_width=350),
            tooltip=f"{hospital['name']} ({marker_type})",
            icon=folium.Icon(color=color, icon=icon)
        ).add_to(m)
    
    return m

# 메인 애플리케이션
def main():
    st.title("🏥 소아과 병원 찾기")
    st.markdown("**한국 전국의 소아과와 소아응급실이 있는 병원을 쉽게 찾아보세요!**")
    st.markdown("---")
    
    # 사이드바
    st.sidebar.title("🔍 검색 설정")
    
    # 위치 입력 섹션
    st.sidebar.subheader("📍 위치 설정")
    
    # 검색 방법 선택
    search_method = st.sidebar.radio(
        "검색 방법을 선택하세요:",
        ["🗺️ 지역 선택", "🔍 주소 직접 입력"]
    )
    
    location_input = ""
    if search_method == "🗺️ 지역 선택":
        # 드롭다운으로 지역 선택
        region_categories = {
            "서울특별시": ["강남구", "강동구", "강북구", "강서구", "관악구", "광진구", "구로구", "금천구", 
                        "노원구", "도봉구", "동대문구", "동작구", "마포구", "서대문구", "서초구", 
                        "성동구", "성북구", "송파구", "양천구", "영등포구", "용산구", "은평구", "종로구", "중구", "중랑구"],
            "경기도": ["수원", "성남", "고양", "용인", "부천", "안산", "안양", "남양주", "화성", "평택", 
                     "의정부", "시흥", "파주", "김포", "광명", "광주시", "군포", "하남"],
            "광역시": ["부산", "대구", "인천", "광주", "대전", "울산"],
            "특별자치시": ["세종"]
        }
        
        selected_category = st.sidebar.selectbox("지역 분류", list(region_categories.keys()))
        selected_region = st.sidebar.selectbox("세부 지역", region_categories[selected_category])
        location_input = selected_region
        
    else:
        # 직접 입력
        location_input = st.sidebar.text_input(
            "주소 또는 지역명을 입력하세요", 
            placeholder="예: 강남구, 서울시 종로구, 부산시 해운대구"
        )
        
        # 주소 입력 도움말
        with st.sidebar.expander("💡 주소 입력 팁"):
            st.write("• **지역명**: 강남구, 분당구, 부산시")
            st.write("• **상세주소**: 서울시 강남구 테헤란로 123")
            st.write("• **랜드마크**: 강남역, 홍대입구역")
    
    # 병원 타입 필터
    st.sidebar.subheader("🏥 병원 유형")
    show_general = st.sidebar.checkbox("소아과가 있는 병원", value=True)
    show_emergency = st.sidebar.checkbox("소아응급실이 있는 병원", value=True)
    
    # 거리 필터
    st.sidebar.subheader("📏 검색 범위")
    max_distance = st.sidebar.slider("최대 거리 (km)", 1, 100, 20)
    
    # 검색 버튼
    search_clicked = st.sidebar.button("🔍 병원 검색", type="primary")
    
    # 병원 데이터 로드
    hospitals_df = load_hospital_data()
    
    # 초기 상태 설정
    if 'user_location' not in st.session_state:
        st.session_state.user_location = None
        st.session_state.location_name = None
    
    # 위치 검색 처리
    if search_clicked and location_input:
        with st.spinner("위치를 검색하는 중입니다..."):
            lat, lon, location_name = search_address(location_input)
            
            if lat and lon:
                st.session_state.user_location = (lat, lon)
                st.session_state.location_name = location_name
                st.sidebar.success(f"✅ 위치 찾기 성공!")
                st.sidebar.info(f"📍 {location_name}")
            else:
                st.sidebar.error("❌ 위치를 찾을 수 없습니다.")
                st.sidebar.info("다른 지역명이나 주소를 시도해보세요.")
    
    # 병원 필터링
    filtered_hospitals = hospitals_df.copy()
    
    if not show_general and not show_emergency:
        st.warning("⚠️ 적어도 하나의 병원 유형을 선택해주세요.")
        return
    
    if not show_general:
        filtered_hospitals = filtered_hospitals[filtered_hospitals['pediatric_emergency'] == True]
    elif not show_emergency:
        filtered_hospitals = filtered_hospitals[filtered_hospitals['pediatric_emergency'] == False]
    
    # 거리 기반 필터링 및 정렬
    if st.session_state.user_location:
        user_lat, user_lon = st.session_state.user_location
        distances = []
        for idx, hospital in filtered_hospitals.iterrows():
            distance = calculate_distance(user_lat, user_lon, hospital['lat'], hospital['lon'])
            distances.append(distance)
        
        filtered_hospitals = filtered_hospitals.copy()
        filtered_hospitals['distance'] = distances
        filtered_hospitals = filtered_hospitals[filtered_hospitals['distance'] <= max_distance]
        filtered_hospitals = filtered_hospitals.sort_values('distance')
    
    # 메인 컨텐츠 영역
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🗺️ 병원 위치 지도")
        
        if len(filtered_hospitals) > 0:
            # 지도 중심점 설정
            if st.session_state.user_location:
                center_lat, center_lon = st.session_state.user_location
                user_location = st.session_state.user_location
            else:
                center_lat = filtered_hospitals['lat'].mean()
                center_lon = filtered_hospitals['lon'].mean()
                user_location = None
            
            # 지도 생성 및 표시
            map_obj = create_map(filtered_hospitals, center_lat, center_lon, user_location)
            st_folium(map_obj, width=700, height=500)
        else:
            st.info("🔍 검색 조건에 맞는 병원이 없습니다.")
            # 기본 지도 표시
            default_map = create_map(hospitals_df)
            st_folium(default_map, width=700, height=500)
    
    with col2:
        st.subheader("📋 검색 결과")
        
        if st.session_state.location_name:
            st.info(f"📍 현재 위치: {st.session_state.location_name}")
        
        if len(filtered_hospitals) > 0:
            st.success(f"✅ {len(filtered_hospitals)}개 병원 발견")
            
            for idx, hospital in filtered_hospitals.iterrows():
                with st.expander(f"🏥 {hospital['name']}", expanded=False):
                    st.markdown(f"**📍 주소:** {hospital['address']}")
                    st.markdown(f"**📞 전화:** {hospital['phone']}")
                    st.markdown(f"**🏥 분류:** {hospital['type']}")
                    
                    # 특징 표시
                    features = []
                    if hospital['pediatric_dept']:
                        features.append("👶 소아과")
                    if hospital['pediatric_emergency']:
                        features.append("🚨 소아응급실")
                    st.markdown(f"**⚕️ 진료과:** {' | '.join(features)}")
                    
                    # 거리 표시
                    if 'distance' in hospital:
                        st.markdown(f"**📏 거리:** {hospital['distance']:.1f}km")
                    
                    st.markdown(f"**💬 설명:** {hospital['description']}")
                    
                    # 웹사이트 링크
                    if 'website' in hospital and hospital['website']:
                        st.markdown(f"**🌐 웹사이트:** [병원 홈페이지 방문]({hospital['website']})")
        else:
            if st.session_state.user_location:
                st.warning("🔍 검색 범위 내에서 조건에 맞는 병원을 찾을 수 없습니다.")
                st.info("💡 검색 범위를 늘려보거나 다른 조건을 시도해보세요.")
            else:
                st.info("📍 위치를 설정하고 검색 버튼을 눌러주세요.")
    
    # 하단 정보
    st.markdown("---")
    
    # 범례
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 🗺️ 지도 범례")
        st.markdown("🔴 **내 위치**")
        st.markdown("🔵 **소아응급실 병원**")  
        st.markdown("🟢 **소아과 병원**")
    
    with col2:
        st.markdown("### ℹ️ 이용 안내")
        st.markdown("• 24시간 응급실 운영 여부는 병원에 직접 확인")
        st.markdown("• 진료시간과 휴진일은 병원마다 다름")
        st.markdown("• 응급상황 시 119 신고")
    
    with col3:
        st.markdown("### 📞 응급연락처")
        st.markdown("**119** - 응급상황")
        st.markdown("**1339** - 응급의료정보센터")
        st.markdown("**129** - 보건복지콜센터")

if __name__ == "__main__":
    main()

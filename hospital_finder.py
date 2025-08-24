import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import requests
import json
from geopy.distance import geodesic
import time
import urllib.parse
import re

# 페이지 설정
st.set_page_config(
    page_title="소아과 병원 찾기",
    page_icon="🏥",
    layout="wide"
)

# 한국 전국 지역 좌표 데이터베이스 (확장)
KOREA_LOCATIONS = {
    # 서울특별시 구별
    "서울": (37.5665, 126.9780),
    "서울시": (37.5665, 126.9780),
    "서울특별시": (37.5665, 126.9780),
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
    
    # 광역시
    "부산": (35.1796, 129.0756),
    "부산시": (35.1796, 129.0756),
    "부산광역시": (35.1796, 129.0756),
    "대구": (35.8714, 128.6014),
    "대구시": (35.8714, 128.6014),
    "대구광역시": (35.8714, 128.6014),
    "인천": (37.4563, 126.7052),
    "인천시": (37.4563, 126.7052),
    "인천광역시": (37.4563, 126.7052),
    "광주": (35.1595, 126.8526),
    "광주시": (35.1595, 126.8526),
    "광주광역시": (35.1595, 126.8526),
    "대전": (36.3504, 127.3845),
    "대전시": (36.3504, 127.3845),
    "대전광역시": (36.3504, 127.3845),
    "울산": (35.5384, 129.3114),
    "울산시": (35.5384, 129.3114),
    "울산광역시": (35.5384, 129.3114),
    
    # 특별자치시
    "세종": (36.4800, 127.2890),
    "세종시": (36.4800, 127.2890),
    "세종특별자치시": (36.4800, 127.2890),
    
    # 경기도 (확장)
    "경기도": (37.4138, 127.5183),
    "수원": (37.2636, 127.0286),
    "수원시": (37.2636, 127.0286),
    "성남": (37.4201, 127.1262),
    "성남시": (37.4201, 127.1262),
    "고양": (37.6584, 126.8320),
    "고양시": (37.6584, 126.8320),
    "용인": (37.2411, 127.1776),
    "용인시": (37.2411, 127.1776),
    "부천": (37.5034, 126.7660),
    "부천시": (37.5034, 126.7660),
    "안산": (37.3218, 126.8309),
    "안산시": (37.3218, 126.8309),
    "안양": (37.3943, 126.9568),
    "안양시": (37.3943, 126.9568),
    "남양주": (37.6361, 127.2167),
    "남양주시": (37.6361, 127.2167),
    "화성": (37.1996, 126.8311),
    "화성시": (37.1996, 126.8311),
    "평택": (36.9921, 127.1125),
    "평택시": (36.9921, 127.1125),
    "의정부": (37.7384, 127.0330),
    "의정부시": (37.7384, 127.0330),
    "시흥": (37.3800, 126.8031),
    "시흥시": (37.3800, 126.8031),
    "파주": (37.7599, 126.7800),
    "파주시": (37.7599, 126.7800),
    "김포": (37.6149, 126.7158),
    "김포시": (37.6149, 126.7158),
    "광명": (37.4784, 126.8644),
    "광명시": (37.4784, 126.8644),
    "군포": (37.3617, 126.9352),
    "군포시": (37.3617, 126.9352),
    "하남": (37.5390, 127.2056),
    "하남시": (37.5390, 127.2056),
    "오산": (37.1499, 127.0773),
    "오산시": (37.1499, 127.0773),
    "이천": (37.2724, 127.4349),
    "이천시": (37.2724, 127.4349),
    "안성": (37.0078, 127.2792),  # 안성시 정확한 좌표
    "안성시": (37.0078, 127.2792),
    "구리": (37.5943, 127.1296),
    "구리시": (37.5943, 127.1296),
    "포천": (37.8951, 127.2003),
    "포천시": (37.8951, 127.2003),
    "양주": (37.7854, 127.0446),
    "양주시": (37.7854, 127.0446),
    "동두천": (37.9035, 127.0606),
    "동두천시": (37.9035, 127.0606),
    "과천": (37.4292, 126.9872),
    "과천시": (37.4292, 126.9872),
    "양평": (37.4914, 127.4877),
    "양평군": (37.4914, 127.4877),
    "가평": (37.8313, 127.5106),
    "가평군": (37.8313, 127.5106),
    "연천": (38.0966, 127.0748),
    "연천군": (38.0966, 127.0748),
    
    # 안성시 세부 지역 추가
    "안성대덕면": (37.0150, 127.3200),
    "대덕면": (37.0150, 127.3200),
    "안성시대덕면": (37.0150, 127.3200),
    
    # 강원도
    "강원도": (37.8813, 127.7298),
    "춘천": (37.8813, 127.7298),
    "춘천시": (37.8813, 127.7298),
    "원주": (37.3422, 127.9202),
    "원주시": (37.3422, 127.9202),
    "강릉": (37.7519, 128.8761),
    "강릉시": (37.7519, 128.8761),
    "동해": (37.5247, 129.1144),
    "동해시": (37.5247, 129.1144),
    "태백": (37.1640, 128.9856),
    "태백시": (37.1640, 128.9856),
    "속초": (38.2070, 128.5918),
    "속초시": (38.2070, 128.5918),
    "삼척": (37.4499, 129.1650),
    "삼척시": (37.4499, 129.1650),
    "양양": (38.0756, 128.6190),
    "양양군": (38.0756, 128.6190),
    
    # 충청북도
    "충청북도": (36.6424, 127.4890),
    "충북": (36.6424, 127.4890),
    "청주": (36.6424, 127.4890),
    "청주시": (36.6424, 127.4890),
    "충주": (36.9910, 127.9259),
    "충주시": (36.9910, 127.9259),
    "제천": (37.1326, 128.1909),
    "제천시": (37.1326, 128.1909),
    
    # 충청남도
    "충청남도": (36.8151, 127.1139),
    "충남": (36.8151, 127.1139),
    "천안": (36.8151, 127.1139),
    "천안시": (36.8151, 127.1139),
    "공주": (36.4465, 127.1188),
    "공주시": (36.4465, 127.1188),
    "아산": (36.7898, 127.0020),
    "아산시": (36.7898, 127.0020),
    
    # 전라북도
    "전라북도": (35.8242, 127.1480),
    "전북": (35.8242, 127.1480),
    "전주": (35.8242, 127.1480),
    "전주시": (35.8242, 127.1480),
    "군산": (35.9676, 126.7115),
    "군산시": (35.9676, 126.7115),
    "익산": (35.9483, 126.9576),
    "익산시": (35.9483, 126.9576),
    
    # 전라남도
    "전라남도": (34.9506, 127.4872),
    "전남": (34.9506, 127.4872),
    "목포": (34.8118, 126.3922),
    "목포시": (34.8118, 126.3922),
    "여수": (34.7604, 127.6622),
    "여수시": (34.7604, 127.6622),
    "순천": (34.9506, 127.4872),
    "순천시": (34.9506, 127.4872),
    
    # 경상북도
    "경상북도": (36.0190, 129.3435),
    "경북": (36.0190, 129.3435),
    "포항": (36.0190, 129.3435),
    "포항시": (36.0190, 129.3435),
    "경주": (35.8562, 129.2247),
    "경주시": (35.8562, 129.2247),
    "안동": (36.5684, 128.7294),
    "안동시": (36.5684, 128.7294),
    "구미": (36.1195, 128.3445),
    "구미시": (36.1195, 128.3445),
    
    # 경상남도
    "경상남도": (35.2281, 128.6811),
    "경남": (35.2281, 128.6811),
    "창원": (35.2281, 128.6811),
    "창원시": (35.2281, 128.6811),
    "진주": (35.1799, 128.1076),
    "진주시": (35.1799, 128.1076),
    "김해": (35.2341, 128.8890),
    "김해시": (35.2341, 128.8890),
    
    # 제주특별자치도
    "제주": (33.4996, 126.5312),
    "제주시": (33.4996, 126.5312),
    "서귀포": (33.2541, 126.5601),
    "서귀포시": (33.2541, 126.5601),
    "제주도": (33.4996, 126.5312),
    "제주특별자치도": (33.4996, 126.5312)
}

# 전국 병원 데이터
@st.cache_data
def load_hospital_data():
    hospitals = [
        # 서울 지역
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
            "name": "서울아산병원",
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
        
        # 경기도
        {
            "name": "분당서울대학교병원",
            "address": "경기도 성남시 분당구 구미로 173번길 82",
            "lat": 37.3520,
            "lon": 127.1245,
            "type": "종합병원",
            "pediatric_dept": True,
            "pediatric_emergency": True,
            "phone": "031-787-7114",
            "description": "소아청소년과, 소아응급실 운영"
        },
        {
            "name": "아주대학교병원",
            "address": "경기도 수원시 영통구 월드컵로 164",
            "lat": 37.2779,
            "lon": 127.0467,
            "type": "종합병원",
            "pediatric_dept": True,
            "pediatric_emergency": True,
            "phone": "031-219-5114",
            "description": "소아청소년과, 소아응급실 운영"
        },
        {
            "name": "안성병원",
            "address": "경기도 안성시 장기로 109",
            "lat": 37.0078,
            "lon": 127.2792,
            "type": "종합병원",
            "pediatric_dept": True,
            "pediatric_emergency": False,
            "phone": "031-678-5000",
            "description": "소아청소년과 운영"
        },
        {
            "name": "단국대학교병원",
            "address": "충청남도 천안시 동남구 망향로 201",
            "lat": 36.8151,
            "lon": 127.1139,
            "type": "종합병원",
            "pediatric_dept": True,
            "pediatric_emergency": True,
            "phone": "041-550-6114",
            "description": "소아청소년과, 소아응급실 운영 (안성 인근)"
        },
        
        # 인천
        {
            "name": "인천성모병원",
            "address": "인천광역시 부평구 동수로 56",
            "lat": 37.4636,
            "lon": 126.7226,
            "type": "종합병원",
            "pediatric_dept": True,
            "pediatric_emergency": True,
            "phone": "032-280-5114",
            "description": "소아청소년과, 소아응급실 운영"
        },
        
        # 강원도
        {
            "name": "강릉아산병원",
            "address": "강원도 강릉시 사천면 방동길 38",
            "lat": 37.6906,
            "lon": 128.8663,
            "type": "종합병원",
            "pediatric_dept": True,
            "pediatric_emergency": True,
            "phone": "033-610-3114",
            "description": "소아청소년과, 소아응급실 운영"
        },
        {
            "name": "춘천성심병원",
            "address": "강원도 춘천시 석사동 153",
            "lat": 37.8647,
            "lon": 127.7280,
            "type": "종합병원",
            "pediatric_dept": True,
            "pediatric_emergency": False,
            "phone": "033-240-5114",
            "description": "소아청소년과 운영"
        },
        {
            "name": "속초의료원",
            "address": "강원도 속초시 중앙로 115",
            "lat": 38.2070,
            "lon": 128.5918,
            "type": "공공병원",
            "pediatric_dept": True,
            "pediatric_emergency": False,
            "phone": "033-639-5900",
            "description": "소아청소년과 운영"
        },
        {
            "name": "양양병원",
            "address": "강원도 양양군 양양읍 일출로 69",
            "lat": 38.0756,
            "lon": 128.6190,
            "type": "종합병원",
            "pediatric_dept": True,
            "pediatric_emergency": False,
            "phone": "033-671-9500",
            "description": "소아청소년과 운영"
        },
        
        # 기타 지역 병원들
        {
            "name": "부산대학교병원",
            "address": "부산광역시 서구 구덕로 179",
            "lat": 35.1050,
            "lon": 129.0307,
            "type": "종합병원",
            "pediatric_dept": True,
            "pediatric_emergency": True,
            "phone": "051-240-7114",
            "description": "소아청소년과, 소아응급실 운영"
        },
        {
            "name": "경북대학교병원",
            "address": "대구광역시 중구 동덕로 130",
            "lat": 35.8714,
            "lon": 128.5989,
            "type": "종합병원",
            "pediatric_dept": True,
            "pediatric_emergency": True,
            "phone": "053-420-5114",
            "description": "소아청소년과, 소아응급실 운영"
        },
        {
            "name": "충북대학교병원",
            "address": "충청북도 청주시 서원구 1순환로 776",
            "lat": 36.6424,
            "lon": 127.4890,
            "type": "종합병원",
            "pediatric_dept": True,
            "pediatric_emergency": True,
            "phone": "043-269-6114",
            "description": "소아청소년과, 소아응급실 운영"
        },
        {
            "name": "전북대학교병원",
            "address": "전라북도 전주시 덕진구 건지로 20",
            "lat": 35.8242,
            "lon": 127.1480,
            "type": "종합병원",
            "pediatric_dept": True,
            "pediatric_emergency": True,
            "phone": "063-250-1114",
            "description": "소아청소년과, 소아응급실 운영"
        },
        {
            "name": "제주대학교병원",
            "address": "제주특별자치도 제주시 아란13길 15",
            "lat": 33.4996,
            "lon": 126.5312,
            "type": "종합병원",
            "pediatric_dept": True,
            "pediatric_emergency": True,
            "phone": "064-717-1114",
            "description": "소아청소년과, 소아응급실 운영"
        }
    ]
    return pd.DataFrame(hospitals)

# 개선된 주소 검색 알고리즘
def search_location_by_region(address):
    """향상된 지역명 기반 좌표 검색"""
    if not address:
        return None, None, None
    
    # 입력값 정규화
    address_original = address.strip()
    address_clean = re.sub(r'\s+', '', address_original)  # 공백 제거
    address_lower = address_clean.lower()
    
    # 도별 우선순위 매칭 시스템
    matches = []
    
    # 1단계: 완전 일치 검색 (최고 우선순위)
    for region, coords in KOREA_LOCATIONS.items():
        region_clean = re.sub(r'\s+', '', region)
        
        if region_clean == address_clean:
            return coords[0], coords[1], region
    
    # 2단계: 복합 지역명 처리 (예: "경기도 안성시 대덕면")
    if "안성" in address_lower and "대덕" in address_lower:
        if "안성대덕면" in KOREA_LOCATIONS:
            coords = KOREA_LOCATIONS["안성대덕면"]
            return coords[0], coords[1], "안성시 대덕면"
        elif "안성시" in KOREA_LOCATIONS:
            coords = KOREA_LOCATIONS["안성시"]
            return coords[0], coords[1], "안성시"
    
    # 3단계: 도-시-구/군 계층적 매칭
    if "경기도" in address_lower or "경기" in address_lower:
        # 경기도 내 지역 우선 검색
        for region, coords in KOREA_LOCATIONS.items():
            if ("안성" in region.lower() and "안성" in address_lower):
                return coords[0], coords[1], region
            elif region.lower() in address_lower and any(city in region for city in ["수원", "성남", "고양", "용인", "부천", "안산", "안양", "안성"]):
                return coords[0], coords[1], region
    
    # 4단계: 일반적인 우선순위 매칭
    region_scores = []
    
    for region, coords in KOREA_LOCATIONS.items():
        region_clean = re.sub(r'\s+', '', region)
        region_lower = region_clean.lower()
        score = 0
        
        # 정확한 매칭
        if region_clean == address_clean:
            score = 100
        # 완전 포함 (긴 지역명이 우선)
        elif region_lower in address_lower:
            score = 90 + len(region)  # 긴 지역명에 가산점
        elif address_lower in region_lower:
            score = 85 + len(address_clean)
        # 부분 매칭 (시/군/구 제거하여 비교)
        else:
            region_base = re.sub(r'[시군구]$', '', region_clean)
            address_base = re.sub(r'[시군구도]', '', address_clean)
            
            if region_base and address_base and region_base.lower() in address_lower:
                score = 70 + len(region_base)
            elif region_base and address_base and address_base.lower() in region_lower:
                score = 65 + len(address_base)
        
        if score > 0:
            region_scores.append((region, coords, score))
    
    # 점수 기준 정렬
    if region_scores:
        region_scores.sort(key=lambda x: x[2], reverse=True)
        best_match = region_scores[0]
        return best_match[1][0], best_match[1][1], best_match[0]
    
    return None, None, None

# OpenStreetMap Nominatim API를 사용한 백업 검색
def search_with_nominatim(address):
    try:
        base_url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': f"{address}, South Korea",
            'format': 'json',
            'limit': 1,
            'addressdetails': 1
        }
        
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
        st.error(f"온라인 검색 오류: {e}")
    
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
        # 드롭다운으로 지역 선택 (전국 확장)
        region_categories = {
            "서울특별시": ["강남구", "강동구", "강북구", "강서구", "관악구", "광진구", "구로구", "금천구", 
                        "노원구", "도봉구", "동대문구", "동작구", "마포구", "서대문구", "서초구", 
                        "성동구", "성북구", "송파구", "양천구", "영등포구", "용산구", "은평구", "종로구", "중구", "중랑구"],
            
            "경기도": ["수원시", "성남시", "고양시", "용인시", "부천시", "안산시", "안양시", "남양주시", "화성시", "평택시", 
                     "안성시", "이천시", "오산시", "구리시", "하남시", "포천시", "양주시", "의정부시", "파주시", "김포시"],
            
            "강원도": ["춘천시", "원주시", "강릉시", "동해시", "태백시", "속초시", "삼척시", "양양군"],
            
            "충청북도": ["청주시", "충주시", "제천시"],
            
            "충청남도": ["천안시", "공주시", "아산시"],
            
            "전라북도": ["전주시", "군산시", "익산시"],
            
            "전라남도": ["목포시", "여수시", "순천시"],
            
            "경상북도": ["포항시", "경주시", "안동시", "구미시"],
            
            "경상남도": ["창원시", "진주시", "김해시"],
            
            "광역시": ["부산광역시", "대구광역시", "인천광역시", "광주광역시", "대전광역시", "울산광역시"],
            
            "제주특별자치도": ["제주시", "서귀포시"],
            
            "특별자치시": ["세종특별자치시"]
        }
        
        selected_category = st.sidebar.selectbox("지역 분류", list(region_categories.keys()))
        selected_region = st.sidebar.selectbox("세부 지역", region_categories[selected_category])
        location_input = selected_region
        
    else:
        # 직접 입력
        location_input = st.sidebar.text_input(
            "주소 또는 지역명을 입력하세요", 
            placeholder="예: 경기도 안성시 대덕면, 강원도 속초시"
        )
        
        # 주소 입력 도움말
        with st.sidebar.expander("💡 주소 입력 팁"):
            st.write("• **정확한 주소**: 경기도 안성시 대덕면")
            st.write("• **시/군 단위**: 안성시, 속초시, 춘천시")
            st.write("• **도 단위**: 강원도, 경기도, 충청북도")
            st.write("• **면/동 포함**: 안성시 대덕면, 강릉시 사천면")
    
    # 병원 타입 필터
    st.sidebar.subheader("🏥 병원 유형")
    show_general = st.sidebar.checkbox("소아과가 있는 병원", value=True)
    show_emergency = st.sidebar.checkbox("소아응급실이 있는 병원", value=True)
    
    # 거리 필터
    st.sidebar.subheader("📏 검색 범위")
    max_distance = st.sidebar.slider("최대 거리 (km)", 1, 100, 30)
    
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
                
                # 비슷한 지역명 제안
                similar_regions = []
                input_lower = location_input.lower()
                for region in KOREA_LOCATIONS.keys():
                    region_lower = region.lower()
                    # 부분 매칭으로 비슷한 지역 찾기
                    if (len(input_lower) > 1 and any(part in region_lower for part in input_lower.split()) or
                        len(region_lower) > 1 and any(part in input_lower for part in region_lower.split())):
                        similar_regions.append(region)
                
                if similar_regions:
                    st.sidebar.info("💡 비슷한 지역명을 찾았습니다:")
                    for region in similar_regions[:5]:  # 최대 5개만 표시
                        st.sidebar.write(f"• {region}")
    
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
            # 기본 지도 표시 (전국 병원)
            if st.session_state.user_location:
                center_lat, center_lon = st.session_state.user_location
                default_map = create_map(hospitals_df, center_lat, center_lon, st.session_state.user_location)
            else:
                default_map = create_map(hospitals_df, 36.5, 127.5)
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
                    if 'distance' in hospital and pd.notna(hospital['distance']):
                        st.markdown(f"**📏 거리:** {hospital['distance']:.1f}km")
                    
                    st.markdown(f"**💬 설명:** {hospital['description']}")
        else:
            if st.session_state.user_location:
                st.warning("🔍 검색 범위 내에서 조건에 맞는 병원을 찾을 수 없습니다.")
                st.info("💡 검색 범위를 늘려보거나 다른 조건을 시도해보세요.")
            else:
                st.info("📍 위치를 설정하고 검색 버튼을 눌러주세요.")
                
                # 전체 병원 목록 표시 (위치 설정 전)
                st.markdown("**🏥 전국 병원 목록 (일부)**")
                for idx, hospital in hospitals_df.head(5).iterrows():
                    st.markdown(f"• **{hospital['name']}** - {hospital['address']}")
    
    # 하단 정보
    st.markdown("---")
    
    # 범례와 정보
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
    
    # 검색 테스트 섹션
    st.markdown("---")
    with st.expander("🔧 검색 기능 테스트 & 디버깅"):
        st.markdown("**주소 검색 테스트**")
        test_addresses = [
            "경기도 안성시 대덕면",
            "안성시 대덕면", 
            "안성시",
            "대덕면",
            "강원도 속초시",
            "양양군",
            "서울 강남구",
            "부산시"
        ]
        
        col_test1, col_test2 = st.columns(2)
        
        with col_test1:
            selected_test = st.selectbox("테스트할 주소 선택:", ["선택하세요"] + test_addresses)
            
            if selected_test != "선택하세요":
                test_lat, test_lon, test_name = search_address(selected_test)
                if test_lat and test_lon:
                    st.success(f"✅ {selected_test}")
                    st.info(f"→ {test_name}")
                    st.info(f"📍 좌표: {test_lat:.4f}, {test_lon:.4f}")
                else:
                    st.error(f"❌ {selected_test} 검색 실패")
        
        with col_test2:
            # 커스텀 테스트
            custom_test = st.text_input("직접 테스트:", placeholder="주소 입력")
            if st.button("테스트 실행") and custom_test:
                test_lat, test_lon, test_name = search_address(custom_test)
                if test_lat and test_lon:
                    st.success(f"✅ {custom_test}")
                    st.info(f"→ {test_name}")
                    st.info(f"📍 좌표: {test_lat:.4f}, {test_lon:.4f}")
                else:
                    st.error(f"❌ {custom_test} 검색 실패")
                    # 디버깅 정보
                    st.write("**디버깅:** 지역 데이터베이스에서 일치하는 항목:")
                    matches = []
                    for region in KOREA_LOCATIONS.keys():
                        if custom_test.lower() in region.lower() or region.lower() in custom_test.lower():
                            matches.append(region)
                    if matches:
                        st.write(matches[:10])  # 최대 10개
                    else:
                        st.write("일치하는 항목 없음")

if __name__ == "__main__":
    main()

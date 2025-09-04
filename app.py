import streamlit as st
import pandas as pd
import numpy as np
import json
from datetime import datetime
import os

# 페이지 설정
st.set_page_config(
    page_title="사원 평가 시스템",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 데이터 로드 함수
@st.cache_data
def load_data():
    """데이터 로드 및 전처리"""
    try:
        # 기본 데이터 로드
        base_data = pd.read_csv('basedata.csv', encoding='cp949')
        
        # 직급별 역할 정의 로드
        jikkeup_data = pd.read_csv('Jikkeup.csv', encoding='cp949')
        
        return base_data, jikkeup_data
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {e}")
        return None, None

# 세션 상태 초기화
if 'user_type' not in st.session_state:
    st.session_state.user_type = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'user_name' not in st.session_state:
    st.session_state.user_name = None
if 'evaluations' not in st.session_state:
    st.session_state.evaluations = {}
if 'performance_data' not in st.session_state:
    st.session_state.performance_data = {}

# 데이터 로드
base_data, jikkeup_data = load_data()

if base_data is None:
    st.error("데이터를 로드할 수 없습니다. 파일을 확인해주세요.")
    st.stop()

# 로그인 함수
def login(user_type, user_id, password):
    """로그인 처리"""
    if user_type == "피평가자":
        # 피평가자 로그인 (A열: ID, B열: PW)
        try:
            user_id_int = int(user_id)
            user_data = base_data[base_data.iloc[:, 0] == user_id_int]
            if not user_data.empty and str(user_data.iloc[0, 1]) == password:
                return True, user_data.iloc[0, 2], user_data.iloc[0, 3], user_data.iloc[0, 4], user_data.iloc[0, 5]
        except ValueError:
            pass
    
    elif user_type == "평가자(팀장)":
        # 평가자(팀장) 로그인 (J열: ID, K열: PW)
        try:
            user_id_int = int(user_id)
            user_data = base_data[base_data.iloc[:, 9] == user_id_int]
            if not user_data.empty and str(user_data.iloc[0, 10]) == password:
                return True, user_data.iloc[0, 11], user_data.iloc[0, 12], user_data.iloc[0, 13], user_data.iloc[0, 14]
        except ValueError:
            pass
    
    elif user_type == "평가자(임원)":
        # 평가자(임원) 로그인 (Q열: ID, R열: PW)
        try:
            user_id_int = int(user_id)
            user_data = base_data[base_data.iloc[:, 16] == user_id_int]
            if not user_data.empty and str(user_data.iloc[0, 17]) == password:
                return True, user_data.iloc[0, 18], user_data.iloc[0, 19], user_data.iloc[0, 20], user_data.iloc[0, 21]
        except ValueError:
            pass
    
    elif user_type == "관리자(인사담당자)":
        # 관리자 로그인 (임시)
        if user_id == "admin" and password == "admin123":
            return True, "관리자", "인사팀", "팀장", "Manager"
    
    return False, None, None, None, None

# 메인 앱
def main():
    st.title("🏢 사원 평가 시스템")
    
    # 로그인 상태 확인
    if st.session_state.user_type is None:
        show_login_page()
    else:
        show_main_page()

def show_login_page():
    """로그인 페이지"""
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("🔐 로그인")
        
        user_type = st.selectbox(
            "사용자 유형 선택",
            ["피평가자", "평가자(팀장)", "평가자(임원)", "관리자(인사담당자)"]
        )
        
        user_id = st.text_input("아이디")
        password = st.text_input("비밀번호", type="password")
        
        if st.button("로그인", type="primary"):
            success, name, dept, position, level = login(user_type, user_id, password)
            
            if success:
                st.session_state.user_type = user_type
                st.session_state.user_id = user_id
                st.session_state.user_name = name
                st.success(f"환영합니다, {name}님!")
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 올바르지 않습니다.")

def show_main_page():
    """메인 페이지"""
    st.sidebar.title(f"👤 {st.session_state.user_name}")
    st.sidebar.write(f"유형: {st.session_state.user_type}")
    
    if st.sidebar.button("로그아웃"):
        st.session_state.user_type = None
        st.session_state.user_id = None
        st.session_state.user_name = None
        st.rerun()
    
    # 사용자 유형별 메뉴
    if st.session_state.user_type == "피평가자":
        show_evaluatee_page()
    elif st.session_state.user_type == "평가자(팀장)":
        show_team_leader_page()
    elif st.session_state.user_type == "평가자(임원)":
        show_executive_page()
    elif st.session_state.user_type == "관리자(인사담당자)":
        show_admin_page()

def show_evaluatee_page():
    """피평가자 페이지"""
    st.header("📝 실적 작성")
    
    # 사용자 정보 표시
    user_data = base_data[base_data.iloc[:, 0] == st.session_state.user_id]
    if not user_data.empty:
        user_info = user_data.iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("이름", user_info.iloc[2])
        with col2:
            st.metric("소속", user_info.iloc[3])
        with col3:
            st.metric("직위", user_info.iloc[4])
        with col4:
            st.metric("직급", user_info.iloc[5])
    
    st.markdown("---")
    
    # 실적 작성 폼
    with st.form("performance_form"):
        st.subheader("실적 작성")
        
        project_name = st.text_input("과제명")
        performance_content = st.text_area("실적 내용", height=200)
        
        submitted = st.form_submit_button("등록하기", type="primary")
        
        if submitted:
            if project_name and performance_content:
                # 실적 데이터 저장
                performance_data = {
                    "user_id": st.session_state.user_id,
                    "user_name": st.session_state.user_name,
                    "project_name": project_name,
                    "performance_content": performance_content,
                    "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                st.session_state.performance_data[st.session_state.user_id] = performance_data
                st.success("실적이 성공적으로 등록되었습니다!")
                st.rerun()
            else:
                st.error("모든 필드를 입력해주세요.")
    
    # 경고 메시지 (폼 외부에 배치)
    if st.session_state.user_id in st.session_state.performance_data:
        st.warning("⚠️ 실적이 이미 등록되었습니다. 변경이 불가합니다.")

def show_team_leader_page():
    """평가자(팀장) 페이지"""
    st.header("👥 팀원 평가")
    
    # 탭 생성
    tab1, tab2, tab3 = st.tabs(["팀원 평가(사원)", "팀원 평가(대리 이상)", "팀원 평가(일반직)"])
    
    with tab1:
        show_employee_evaluation()
    
    with tab2:
        show_manager_evaluation()
    
    with tab3:
        show_general_evaluation()

def show_employee_evaluation():
    """사원 절대평가"""
    st.subheader("사원 절대평가")
    
    # 평가 대상자 필터링 (관리직이면서 사원인 사람)
    evaluator_id = st.session_state.user_id
    target_employees = base_data[
        (base_data.iloc[:, 9] == evaluator_id) &  # 평가자 ID
        (base_data.iloc[:, 7] == "관리직") &      # 관리직
        (base_data.iloc[:, 4] == "사원")          # 사원
    ]
    
    if target_employees.empty:
        st.info("평가할 사원이 없습니다.")
        return
    
    # 직급별 역할 정의 표시
    with st.expander("📋 직급별 역할 정의"):
        st.dataframe(jikkeup_data, use_container_width=True)
    
    # 경고 메시지
    st.warning("⚠️ 직급 체류기간 평균 점수가 60점 미만이면 대리 승진 제외됩니다.")
    
    # 평가 기준
    evaluation_criteria = [
        "근무시간을 준수하고 업무에 집중한다",
        "직장 내 예의범절을 준수한다",
        "맡은 업무에 대해 책임감을 갖고 근무한다",
        "주어진 역할에 대해 적극 수용한다",
        "팀의 목표 달성을 위해 적극적으로 지원하고 협력한다",
        "조직의 가치와 문화를 이해하고 적응한다",
        "업무 내용을 이해하고 정확하게 수행한다",
        "업무를 기한내 완료한다",
        "새로운 지식을 습득하고 활용한다",
        "피드백을 수용하고 자기계발을 지속한다"
    ]
    
    scores = {"S": 10, "A": 8, "B": 6, "C": 4, "D": 2}
    
    for idx, employee in target_employees.iterrows():
        st.markdown(f"### {employee.iloc[2]} ({employee.iloc[3]})")
        
        with st.form(f"employee_eval_{employee.iloc[0]}"):
            total_score = 0
            
            for i, criterion in enumerate(evaluation_criteria):
                col1, col2, col3, col4, col5, col6 = st.columns([3, 1, 1, 1, 1, 1])
                
                with col1:
                    st.write(f"{i+1}. {criterion}")
                
                with col2:
                    s_score = st.radio(f"S({scores['S']}점)", ["", "S"], key=f"s_{employee.iloc[0]}_{i}", horizontal=True)
                with col3:
                    a_score = st.radio(f"A({scores['A']}점)", ["", "A"], key=f"a_{employee.iloc[0]}_{i}", horizontal=True)
                with col4:
                    b_score = st.radio(f"B({scores['B']}점)", ["", "B"], key=f"b_{employee.iloc[0]}_{i}", horizontal=True)
                with col5:
                    c_score = st.radio(f"C({scores['C']}점)", ["", "C"], key=f"c_{employee.iloc[0]}_{i}", horizontal=True)
                with col6:
                    d_score = st.radio(f"D({scores['D']}점)", ["", "D"], key=f"d_{employee.iloc[0]}_{i}", horizontal=True)
                
                # 점수 계산
                if s_score == "S":
                    total_score += scores["S"]
                elif a_score == "A":
                    total_score += scores["A"]
                elif b_score == "B":
                    total_score += scores["B"]
                elif c_score == "C":
                    total_score += scores["C"]
                elif d_score == "D":
                    total_score += scores["D"]
            
            st.metric("총점", f"{total_score}/100점")
            
            qualitative_eval = st.text_area("정성평가", key=f"qual_{employee.iloc[0]}")
            
            if st.form_submit_button("평가 저장"):
                evaluation_data = {
                    "evaluator_id": evaluator_id,
                    "evaluator_name": st.session_state.user_name,
                    "evaluatee_id": employee.iloc[0],
                    "evaluatee_name": employee.iloc[2],
                    "total_score": total_score,
                    "qualitative_eval": qualitative_eval,
                    "evaluation_type": "사원절대평가",
                    "evaluated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                key = f"{evaluator_id}_{employee.iloc[0]}_employee"
                st.session_state.evaluations[key] = evaluation_data
                st.success("평가가 저장되었습니다!")

def show_manager_evaluation():
    """대리 이상 상대평가"""
    st.subheader("대리 이상 상대평가")
    
    # 평가 대상자 필터링 (관리직이면서 사원이 아닌 사람)
    evaluator_id = st.session_state.user_id
    target_managers = base_data[
        (base_data.iloc[:, 9] == evaluator_id) &  # 평가자 ID
        (base_data.iloc[:, 7] == "관리직") &      # 관리직
        (base_data.iloc[:, 4] != "사원")          # 사원이 아닌
    ]
    
    if target_managers.empty:
        st.info("평가할 대리 이상 직원이 없습니다.")
        return
    
    # 직급별 역할 정의 표시
    with st.expander("📋 직급별 역할 정의"):
        st.dataframe(jikkeup_data, use_container_width=True)
    
    # 포인트 계산
    total_points = len(target_managers) * 80
    max_per_person = 95
    min_per_person = 75
    
    st.info(f"총 포인트: {total_points}점 (인당 최대 {max_per_person}점, 최소 {min_per_person}점)")
    
    # 경고 메시지
    st.warning("⚠️ 직전 평가 대비 15점 이상 또는 -15점 이하 부여시 소명서 작성이 필요합니다.")
    
    with st.form("manager_evaluation"):
        st.write("### 포인트 배분")
        
        total_allocated = 0
        manager_scores = {}
        
        for idx, manager in target_managers.iterrows():
            col1, col2, col3 = st.columns([2, 1, 3])
            
            with col1:
                st.write(f"**{manager.iloc[2]}** ({manager.iloc[4]})")
                st.write(f"직전 평가: {manager.iloc[8]}점")
            
            with col2:
                score = st.number_input(
                    "배분 포인트",
                    min_value=min_per_person,
                    max_value=max_per_person,
                    value=80,
                    key=f"score_{manager.iloc[0]}"
                )
                manager_scores[manager.iloc[0]] = score
                total_allocated += score
            
            with col3:
                opinion = st.text_area("평가 의견", key=f"opinion_{manager.iloc[0]}")
        
        st.metric("총 배분 포인트", f"{total_allocated}/{total_points}")
        
        if total_allocated != total_points:
            st.error(f"포인트 배분이 맞지 않습니다. (배분: {total_allocated}, 총점: {total_points})")
        
        if st.form_submit_button("평가 저장"):
            if total_allocated == total_points:
                for manager_id, score in manager_scores.items():
                    manager_data = target_managers[target_managers.iloc[:, 0] == manager_id].iloc[0]
                    previous_score = manager_data.iloc[8]
                    
                    # 15점 이상 차이 확인
                    score_diff = score - previous_score
                    if abs(score_diff) >= 15:
                        st.warning(f"⚠️ {manager_data.iloc[2]}님의 점수 차이가 {score_diff}점입니다. 소명서 작성이 필요합니다.")
                    
                    evaluation_data = {
                        "evaluator_id": evaluator_id,
                        "evaluator_name": st.session_state.user_name,
                        "evaluatee_id": manager_id,
                        "evaluatee_name": manager_data.iloc[2],
                        "score": score,
                        "previous_score": previous_score,
                        "score_difference": score_diff,
                        "opinion": st.session_state.get(f"opinion_{manager_id}", ""),
                        "evaluation_type": "대리이상상대평가",
                        "evaluated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    key = f"{evaluator_id}_{manager_id}_manager"
                    st.session_state.evaluations[key] = evaluation_data
                
                st.success("평가가 저장되었습니다!")
            else:
                st.error("포인트 배분을 정확히 해주세요.")

def show_general_evaluation():
    """일반직 평가"""
    st.subheader("일반직 평가")
    
    # 평가 대상자 필터링 (일반직)
    evaluator_id = st.session_state.user_id
    target_general = base_data[
        (base_data.iloc[:, 9] == evaluator_id) &  # 평가자 ID
        (base_data.iloc[:, 7] == "일반직")        # 일반직
    ]
    
    if target_general.empty:
        st.info("평가할 일반직 직원이 없습니다.")
        return
    
    for idx, employee in target_general.iterrows():
        st.markdown(f"### {employee.iloc[2]} ({employee.iloc[3]})")
        
        with st.form(f"general_eval_{employee.iloc[0]}"):
            opinion = st.text_area("평가 의견", key=f"general_opinion_{employee.iloc[0]}")
            
            if st.form_submit_button("평가 저장"):
                evaluation_data = {
                    "evaluator_id": evaluator_id,
                    "evaluator_name": st.session_state.user_name,
                    "evaluatee_id": employee.iloc[0],
                    "evaluatee_name": employee.iloc[2],
                    "opinion": opinion,
                    "evaluation_type": "일반직평가",
                    "evaluated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                key = f"{evaluator_id}_{employee.iloc[0]}_general"
                st.session_state.evaluations[key] = evaluation_data
                st.success("평가가 저장되었습니다!")

def show_executive_page():
    """평가자(임원) 페이지"""
    st.header("👑 임원 평가")
    
    # 탭 생성
    tab1, tab2, tab3 = st.tabs(["팀장 평가", "팀원 평가(관리직)", "팀원 평가(일반직)"])
    
    with tab1:
        show_team_leader_evaluation()
    
    with tab2:
        show_executive_manager_evaluation()
    
    with tab3:
        show_executive_general_evaluation()

def show_team_leader_evaluation():
    """팀장 평가"""
    st.subheader("팀장 평가")
    
    # 평가 대상자 필터링 (팀장)
    evaluator_id = st.session_state.user_id
    target_team_leaders = base_data[
        (base_data.iloc[:, 16] == evaluator_id) &  # 2차 평가자 ID
        (base_data.iloc[:, 13] == "팀장")          # 팀장
    ]
    
    if target_team_leaders.empty:
        st.info("평가할 팀장이 없습니다.")
        return
    
    # 포인트 계산
    total_points = len(target_team_leaders) * 90
    max_per_person = 105
    min_per_person = 75
    
    st.info(f"총 포인트: {total_points}점 (인당 최대 {max_per_person}점, 최소 {min_per_person}점)")
    
    with st.form("team_leader_evaluation"):
        st.write("### 포인트 배분")
        
        total_allocated = 0
        leader_scores = {}
        
        for idx, leader in target_team_leaders.iterrows():
            col1, col2, col3 = st.columns([2, 1, 3])
            
            with col1:
                st.write(f"**{leader.iloc[11]}** ({leader.iloc[12]})")
            
            with col2:
                score = st.number_input(
                    "배분 포인트",
                    min_value=min_per_person,
                    max_value=max_per_person,
                    value=90,
                    key=f"leader_score_{leader.iloc[9]}"
                )
                leader_scores[leader.iloc[9]] = score
                total_allocated += score
            
            with col3:
                opinion = st.text_area("평가 의견", key=f"leader_opinion_{leader.iloc[9]}")
        
        st.metric("총 배분 포인트", f"{total_allocated}/{total_points}")
        
        if st.form_submit_button("평가 저장"):
            if total_allocated == total_points:
                for leader_id, score in leader_scores.items():
                    leader_data = target_team_leaders[target_team_leaders.iloc[:, 9] == leader_id].iloc[0]
                    
                    evaluation_data = {
                        "evaluator_id": evaluator_id,
                        "evaluator_name": st.session_state.user_name,
                        "evaluatee_id": leader_id,
                        "evaluatee_name": leader_data.iloc[11],
                        "score": score,
                        "opinion": st.session_state.get(f"leader_opinion_{leader_id}", ""),
                        "evaluation_type": "팀장평가",
                        "evaluated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    key = f"{evaluator_id}_{leader_id}_team_leader"
                    st.session_state.evaluations[key] = evaluation_data
                
                st.success("평가가 저장되었습니다!")
            else:
                st.error("포인트 배분을 정확히 해주세요.")

def show_executive_manager_evaluation():
    """임원 관리직 평가"""
    st.subheader("팀원 평가(관리직)")
    
    # 평가 대상자 필터링 (관리직이면서 사원이 아닌)
    evaluator_id = st.session_state.user_id
    target_managers = base_data[
        (base_data.iloc[:, 16] == evaluator_id) &  # 2차 평가자 ID
        (base_data.iloc[:, 7] == "관리직") &       # 관리직
        (base_data.iloc[:, 4] != "사원")           # 사원이 아닌
    ]
    
    if target_managers.empty:
        st.info("평가할 관리직 직원이 없습니다.")
        return
    
    # 직위별 그룹화
    positions = target_managers.iloc[:, 4].unique()
    
    st.warning("⚠️ 평가 대상자에게 안내되지 않으며, 인사부서 참고 자료로만 활용됩니다.")
    
    for position in positions:
        position_employees = target_managers[target_managers.iloc[:, 4] == position]
        
        st.markdown(f"### {position}")
        
        # 포인트 계산
        total_points = len(position_employees) * 5
        max_per_person = 10
        min_per_person = 0
        
        st.info(f"총 포인트: {total_points}점 (인당 최대 {max_per_person}점, 최소 {min_per_person}점)")
        
        with st.form(f"executive_manager_{position}"):
            total_allocated = 0
            manager_scores = {}
            
            for idx, manager in position_employees.iterrows():
                col1, col2, col3 = st.columns([2, 1, 3])
                
                with col1:
                    st.write(f"**{manager.iloc[2]}** ({manager.iloc[3]})")
                
                with col2:
                    score = st.number_input(
                        "배분 포인트",
                        min_value=min_per_person,
                        max_value=max_per_person,
                        value=5,
                        key=f"exec_mgr_score_{manager.iloc[0]}"
                    )
                    manager_scores[manager.iloc[0]] = score
                    total_allocated += score
                
                with col3:
                    opinion = st.text_area("평가 의견", key=f"exec_mgr_opinion_{manager.iloc[0]}")
            
            st.metric("총 배분 포인트", f"{total_allocated}/{total_points}")
            
            if st.form_submit_button(f"{position} 평가 저장"):
                if total_allocated == total_points:
                    for manager_id, score in manager_scores.items():
                        manager_data = position_employees[position_employees.iloc[:, 0] == manager_id].iloc[0]
                        
                        evaluation_data = {
                            "evaluator_id": evaluator_id,
                            "evaluator_name": st.session_state.user_name,
                            "evaluatee_id": manager_id,
                            "evaluatee_name": manager_data.iloc[2],
                            "score": score,
                            "opinion": st.session_state.get(f"exec_mgr_opinion_{manager_id}", ""),
                            "evaluation_type": "임원관리직평가",
                            "evaluated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        key = f"{evaluator_id}_{manager_id}_exec_mgr"
                        st.session_state.evaluations[key] = evaluation_data
                    
                    st.success(f"{position} 평가가 저장되었습니다!")
                else:
                    st.error("포인트 배분을 정확히 해주세요.")

def show_executive_general_evaluation():
    """임원 일반직 평가"""
    st.subheader("팀원 평가(일반직)")
    
    # 평가 대상자 필터링 (일반직)
    evaluator_id = st.session_state.user_id
    target_general = base_data[
        (base_data.iloc[:, 16] == evaluator_id) &  # 2차 평가자 ID
        (base_data.iloc[:, 7] == "일반직")          # 일반직
    ]
    
    if target_general.empty:
        st.info("평가할 일반직 직원이 없습니다.")
        return
    
    # 포인트 계산
    total_points = len(target_general) * 85
    max_per_person = 105
    min_per_person = 65
    
    st.info(f"총 포인트: {total_points}점 (인당 최대 {max_per_person}점, 최소 {min_per_person}점)")
    
    st.warning("⚠️ 평가 대상자에게 안내되지 않으며, 인사부서 참고 자료로만 활용됩니다.")
    
    with st.form("executive_general_evaluation"):
        st.write("### 포인트 배분")
        
        total_allocated = 0
        general_scores = {}
        
        for idx, employee in target_general.iterrows():
            col1, col2, col3 = st.columns([2, 1, 3])
            
            with col1:
                st.write(f"**{employee.iloc[2]}** ({employee.iloc[3]})")
            
            with col2:
                score = st.number_input(
                    "배분 포인트",
                    min_value=min_per_person,
                    max_value=max_per_person,
                    value=85,
                    key=f"exec_gen_score_{employee.iloc[0]}"
                )
                general_scores[employee.iloc[0]] = score
                total_allocated += score
            
            with col3:
                opinion = st.text_area("평가 의견", key=f"exec_gen_opinion_{employee.iloc[0]}")
        
        st.metric("총 배분 포인트", f"{total_allocated}/{total_points}")
        
        if st.form_submit_button("평가 저장"):
            if total_allocated == total_points:
                for employee_id, score in general_scores.items():
                    employee_data = target_general[target_general.iloc[:, 0] == employee_id].iloc[0]
                    
                    evaluation_data = {
                        "evaluator_id": evaluator_id,
                        "evaluator_name": st.session_state.user_name,
                        "evaluatee_id": employee_id,
                        "evaluatee_name": employee_data.iloc[2],
                        "score": score,
                        "opinion": st.session_state.get(f"exec_gen_opinion_{employee_id}", ""),
                        "evaluation_type": "임원일반직평가",
                        "evaluated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    key = f"{evaluator_id}_{employee_id}_exec_gen"
                    st.session_state.evaluations[key] = evaluation_data
                
                st.success("평가가 저장되었습니다!")
            else:
                st.error("포인트 배분을 정확히 해주세요.")

def show_admin_page():
    """관리자 페이지"""
    st.header("🔧 관리자 페이지")
    
    tab1, tab2, tab3 = st.tabs(["평가 현황", "데이터 관리", "시스템 설정"])
    
    with tab1:
        show_evaluation_status()
    
    with tab2:
        show_data_management()
    
    with tab3:
        show_system_settings()

def show_evaluation_status():
    """평가 현황"""
    st.subheader("평가 현황")
    
    if st.session_state.evaluations:
        evaluations_df = pd.DataFrame(list(st.session_state.evaluations.values()))
        st.dataframe(evaluations_df, use_container_width=True)
        
        # 통계 정보
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("총 평가 수", len(evaluations_df))
        
        with col2:
            if 'total_score' in evaluations_df.columns:
                avg_score = evaluations_df['total_score'].mean()
                st.metric("평균 점수", f"{avg_score:.1f}")
        
        with col3:
            if 'evaluation_type' in evaluations_df.columns:
                eval_types = evaluations_df['evaluation_type'].value_counts()
                st.write("평가 유형별 현황")
                st.write(eval_types)
    else:
        st.info("아직 평가 데이터가 없습니다.")

def show_data_management():
    """데이터 관리"""
    st.subheader("데이터 관리")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### 기본 데이터")
        st.dataframe(base_data, use_container_width=True)
    
    with col2:
        st.write("### 직급별 역할 정의")
        st.dataframe(jikkeup_data, use_container_width=True)
    
    # 데이터 내보내기
    if st.button("평가 데이터 내보내기"):
        if st.session_state.evaluations:
            evaluations_df = pd.DataFrame(list(st.session_state.evaluations.values()))
            csv = evaluations_df.to_csv(index=False)
            st.download_button(
                label="CSV 다운로드",
                data=csv,
                file_name=f"evaluations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

def show_system_settings():
    """시스템 설정"""
    st.subheader("시스템 설정")
    
    st.write("### 평가 기준 설정")
    
    # 절대평가 기준
    st.write("**절대평가 기준**")
    scores = st.text_input("점수 기준 (S,A,B,C,D)", value="10,8,6,4,2")
    
    # 상대평가 포인트 설정
    st.write("**상대평가 포인트 설정**")
    col1, col2 = st.columns(2)
    
    with col1:
        team_leader_points = st.number_input("팀장 평가 기본 포인트", value=90)
        manager_points = st.number_input("대리 이상 기본 포인트", value=80)
    
    with col2:
        general_points = st.number_input("일반직 기본 포인트", value=85)
        executive_manager_points = st.number_input("임원 관리직 기본 포인트", value=5)
    
    if st.button("설정 저장"):
        st.success("설정이 저장되었습니다!")

if __name__ == "__main__":
    main() 
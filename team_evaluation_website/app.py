from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pandas as pd
import os
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# 데이터 로드
def load_data():
    # CSV 파일 경로 설정
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    basedata_path = os.path.join(base_path, 'basedata.csv')
    jikkeup_path = os.path.join(base_path, 'Jikkeup.csv')
    
    # 데이터 로드
    basedata = pd.read_csv(basedata_path, encoding='utf-8')
    jikkeup = pd.read_csv(jikkeup_path, encoding='utf-8')
    
    return basedata, jikkeup

# 로그인 검증
def authenticate_user(user_id, password, user_type):
    basedata, _ = load_data()
    
    if user_type == 'evaluatee':
        # 피평가자 로그인 (A열: ID, B열: 패스워드)
        user = basedata[basedata.iloc[:, 0] == user_id]
        if not user.empty and str(user.iloc[0, 1]) == password:
            return True, user.iloc[0]
        return False, None
    
    elif user_type == 'team_leader':
        # 평가자(팀장) 로그인 (J열: ID, K열: 패스워드)
        user = basedata[basedata.iloc[:, 9] == user_id]
        if not user.empty and str(user.iloc[0, 10]) == password:
            return True, user.iloc[0]
        return False, None
    
    elif user_type == 'executive':
        # 평가자(임원) 로그인 (Q열: ID, R열: 패스워드)
        user = basedata[basedata.iloc[:, 16] == user_id]
        if not user.empty and str(user.iloc[0, 17]) == password:
            return True, user.iloc[0]
        return False, None
    
    elif user_type == 'admin':
        # 관리자 로그인 (임시로 하드코딩)
        if user_id == 'admin' and password == 'admin123':
            return True, {'name': '관리자', 'department': '인사팀'}
        return False, None
    
    return False, None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        user_type = request.form['user_type']
        
        success, user_data = authenticate_user(user_id, password, user_type)
        
        if success:
            session['user_id'] = user_id
            session['user_type'] = user_type
            session['user_data'] = user_data.to_dict() if hasattr(user_data, 'to_dict') else user_data
            
            if user_type == 'evaluatee':
                return redirect(url_for('evaluatee_dashboard'))
            elif user_type == 'team_leader':
                return redirect(url_for('team_leader_dashboard'))
            elif user_type == 'executive':
                return redirect(url_for('executive_dashboard'))
            elif user_type == 'admin':
                return redirect(url_for('admin_dashboard'))
        else:
            flash('로그인에 실패했습니다. 아이디와 비밀번호를 확인해주세요.', 'error')
    
    return render_template('login.html')

@app.route('/evaluatee_dashboard')
def evaluatee_dashboard():
    if 'user_type' not in session or session['user_type'] != 'evaluatee':
        return redirect(url_for('login'))
    
    user_data = session['user_data']
    return render_template('evaluatee_dashboard.html', user_data=user_data)

@app.route('/team_leader_dashboard')
def team_leader_dashboard():
    if 'user_type' not in session or session['user_type'] != 'team_leader':
        return redirect(url_for('login'))
    
    basedata, jikkeup = load_data()
    user_data = session['user_data']
    
    # 팀원 목록 가져오기
    team_members = basedata[basedata.iloc[:, 9] == user_data.iloc[0]]  # J열이 현재 로그인한 팀장인 경우
    
    return render_template('team_leader_dashboard.html', 
                         user_data=user_data, 
                         team_members=team_members,
                         jikkeup=jikkeup)

@app.route('/executive_dashboard')
def executive_dashboard():
    if 'user_type' not in session or session['user_type'] != 'executive':
        return redirect(url_for('login'))
    
    basedata, jikkeup = load_data()
    user_data = session['user_data']
    
    return render_template('executive_dashboard.html', 
                         user_data=user_data, 
                         basedata=basedata,
                         jikkeup=jikkeup)

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_type' not in session or session['user_type'] != 'admin':
        return redirect(url_for('login'))
    
    return render_template('admin_dashboard.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/api/team_members/<evaluation_type>')
def get_team_members(evaluation_type):
    if 'user_type' not in session:
        return jsonify({'error': '로그인이 필요합니다'}), 401
    
    basedata, _ = load_data()
    user_data = session['user_data']
    
    if evaluation_type == 'employee':
        # 사원 평가 대상 (H열이 '관리직'이고 E열이 '사원')
        members = basedata[
            (basedata.iloc[:, 7] == '관리직') & 
            (basedata.iloc[:, 4] == '사원')
        ]
    elif evaluation_type == 'manager':
        # 대리 이상 평가 대상 (H열이 '관리직'이고 E열이 '사원'이 아님)
        members = basedata[
            (basedata.iloc[:, 7] == '관리직') & 
            (basedata.iloc[:, 4] != '사원')
        ]
    elif evaluation_type == 'general':
        # 일반직 평가 대상 (H열이 '일반직')
        members = basedata[basedata.iloc[:, 7] == '일반직']
    else:
        return jsonify({'error': '잘못된 평가 유형입니다'}), 400
    
    # 평가자와 관련된 팀원만 필터링
    if session['user_type'] == 'team_leader':
        members = members[members.iloc[:, 9] == user_data.iloc[0]]
    elif session['user_type'] == 'executive':
        # 임원은 전체 관리직/일반직 평가
        pass
    
    result = []
    for _, member in members.iterrows():
        result.append({
            'id': member.iloc[0],
            'name': member.iloc[2],
            'department': member.iloc[3],
            'position': member.iloc[4],
            'grade': member.iloc[5],
            'previous_score': member.iloc[8] if pd.notna(member.iloc[8]) else None
        })
    
    return jsonify(result)

@app.route('/api/save_evaluation', methods=['POST'])
def save_evaluation():
    if 'user_type' not in session:
        return jsonify({'error': '로그인이 필요합니다'}), 401
    
    data = request.json
    # 여기에 평가 데이터 저장 로직 구현
    # 실제 구현시에는 데이터베이스에 저장
    
    return jsonify({'success': True, 'message': '평가가 저장되었습니다'})

if __name__ == '__main__':
    app.run(debug=True) 
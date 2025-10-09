from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
import pandas as pd
import json
import os
from datetime import datetime
import sqlite3
import io

# Heroku PostgreSQL 지원
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HEROKU_MODE = True
except ImportError:
    HEROKU_MODE = False

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

def get_db_connection():
    """데이터베이스 연결 (Heroku PostgreSQL 또는 로컬 SQLite)"""
    if HEROKU_MODE and os.environ.get('DATABASE_URL'):
        # Heroku PostgreSQL
        DATABASE_URL = os.environ.get('DATABASE_URL')
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        return psycopg2.connect(DATABASE_URL)
    else:
        # 로컬 SQLite
        return sqlite3.connect('evaluation.db')

# 데이터 로드 함수들
def load_backdata():
    """backdata.csv 파일 로드"""
    try:
        df = pd.read_csv('backdata.csv', encoding='utf-8')
        return df
    except:
        try:
            df = pd.read_csv('backdata.csv', encoding='cp949')
            return df
        except Exception as e:
            print(f"backdata 로드 오류: {e}")
            # Railway 배포 시 CSV 파일이 없을 경우 빈 DataFrame 반환
            return pd.DataFrame(columns=['id', 'password', 'name', 'team', 'position', 'grade'])

def load_evaluation_mappings():
    """평가자-피평가자 매핑 데이터 로드"""
    mappings = {}
    
    # 평가자(팀장)_사원.csv
    try:
        df = pd.read_csv('평가자(팀장)_사원.csv', encoding='utf-8')
        mappings['team_leader_employee'] = df
    except:
        try:
            df = pd.read_csv('평가자(팀장)_사원.csv', encoding='cp949')
            mappings['team_leader_employee'] = df
        except:
            mappings['team_leader_employee'] = pd.DataFrame(columns=['evaluaterid', 'evaluateeid'])
    
    # 평가자(팀장)_대리이상.csv
    try:
        df = pd.read_csv('평가자(팀장)_대리이상.csv', encoding='utf-8')
        mappings['team_leader_manager'] = df
    except:
        try:
            df = pd.read_csv('평가자(팀장)_대리이상.csv', encoding='cp949')
            mappings['team_leader_manager'] = df
        except:
            mappings['team_leader_manager'] = pd.DataFrame(columns=['evaluaterid', 'evaluateeid'])
    
    # 평가자(팀장)_일반직.csv
    try:
        df = pd.read_csv('평가자(팀장)_일반직.csv', encoding='utf-8')
        mappings['team_leader_general'] = df
    except:
        try:
            df = pd.read_csv('평가자(팀장)_일반직.csv', encoding='cp949')
            mappings['team_leader_general'] = df
        except:
            mappings['team_leader_general'] = pd.DataFrame(columns=['evaluaterid', 'evaluateeid'])
    
    # 평가자(임원)_팀장.csv
    try:
        df = pd.read_csv('평가자(임원)_팀장.csv', encoding='utf-8')
        mappings['executive_team_leader'] = df
    except:
        try:
            df = pd.read_csv('평가자(임원)_팀장.csv', encoding='cp949')
            mappings['executive_team_leader'] = df
        except:
            mappings['executive_team_leader'] = pd.DataFrame(columns=['evaluaterid', 'evaluateeid'])
    
    # 평가자(임원)_팀원 관리직.csv
    try:
        df = pd.read_csv('평가자(임원)_팀원 관리직.csv', encoding='utf-8')
        mappings['executive_manager'] = df
    except:
        try:
            df = pd.read_csv('평가자(임원)_팀원 관리직.csv', encoding='cp949')
            mappings['executive_manager'] = df
        except:
            mappings['executive_manager'] = pd.DataFrame(columns=['evaluaterid', 'evaluateeid'])
    
    # 평가자(임원)_팀원 일반직.csv
    try:
        df = pd.read_csv('평가자(임원)_팀원 일반직.csv', encoding='utf-8')
        mappings['executive_general'] = df
    except:
        try:
            df = pd.read_csv('평가자(임원)_팀원 일반직.csv', encoding='cp949')
            mappings['executive_general'] = df
        except:
            mappings['executive_general'] = pd.DataFrame(columns=['evaluaterid', 'evaluateeid'])
    
    return mappings

def load_jikkeup():
    """직급별 역할 정의 로드"""
    try:
        df = pd.read_csv('Jikkeup.csv', encoding='utf-8')
        return df
    except:
        try:
            df = pd.read_csv('Jikkeup.csv', encoding='cp949')
            return df
        except Exception as e:
            print(f"Jikkeup 로드 오류: {e}")
            return None

# 데이터베이스 초기화
def init_db():
    """SQLite 데이터베이스 초기화"""
    conn = sqlite3.connect('evaluation.db')
    cursor = conn.cursor()
    
    # 실적 데이터 테이블 (최대 10개 실적 지원)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS performance_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            performance_order INTEGER NOT NULL,  -- 실적 순서 (1-10)
            project_name TEXT NOT NULL,
            performance TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_finalized BOOLEAN DEFAULT FALSE,
            UNIQUE(employee_id, performance_order)
        )
    ''')
    
    # 평가 데이터 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS evaluation_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evaluator_id TEXT NOT NULL,
            evaluatee_id TEXT NOT NULL,
            evaluation_type TEXT NOT NULL,
            scores TEXT,
            comments TEXT,
            is_final INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 기존 테이블에 is_final 컬럼 추가 (없는 경우에만)
    try:
        cursor.execute('ALTER TABLE evaluation_data ADD COLUMN is_final INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        # 컬럼이 이미 존재하는 경우 무시
        pass
    
    conn.commit()
    conn.close()

# 로그인 처리
def authenticate_user(user_type, user_id, password):
    """사용자 인증"""
    backdata = load_backdata()
    if backdata is None:
        return False, None
    
    # 피평가자 로그인 (A열: ID, B열: PW)
    if user_type == "피평가자":
        user_data = backdata[backdata.iloc[:, 0] == int(user_id)]
        if not user_data.empty and str(user_data.iloc[0, 1]) == password:
            # 11160147, 11960038은 피평가자 로그인 제외
            if int(user_id) in [11160147, 11960038]:
                return False, None
            return True, {
                'id': user_id,
                'name': user_data.iloc[0, 2],
                'team': user_data.iloc[0, 3],
                'position': user_data.iloc[0, 4],
                'grade': user_data.iloc[0, 5]
            }
    
    # 평가자(팀장) 로그인
    elif user_type == "평가자(팀장)":
        user_data = backdata[backdata.iloc[:, 0] == int(user_id)]
        if not user_data.empty and str(user_data.iloc[0, 1]) == password:
            return True, {
                'id': user_id,
                'name': user_data.iloc[0, 2],
                'team': user_data.iloc[0, 3],
                'position': user_data.iloc[0, 4],
                'grade': user_data.iloc[0, 5]
            }
    
    # 평가자(임원) 로그인
    elif user_type == "평가자(임원)":
        user_data = backdata[backdata.iloc[:, 0] == int(user_id)]
        if not user_data.empty and str(user_data.iloc[0, 1]) == password:
            return True, {
                'id': user_id,
                'name': user_data.iloc[0, 2],
                'team': user_data.iloc[0, 3],
                'position': user_data.iloc[0, 4],
                'grade': user_data.iloc[0, 5]
            }
    
    # 관리자 로그인
    elif user_type == "관리자(인사담당자)":
        # 11210110 계정에 관리자 권한 부여
        if user_id == "11210110":
            user_data = backdata[backdata.iloc[:, 0] == int(user_id)]
            if not user_data.empty and str(user_data.iloc[0, 1]) == password:
                return True, {
                    'id': str(user_id),
                    'name': str(user_data.iloc[0, 2]),
                    'team': str(user_data.iloc[0, 3]),
                    'position': str(user_data.iloc[0, 4]),
                    'grade': str(user_data.iloc[0, 5])
                }
        # 기존 admin 계정도 유지
        elif user_id == "admin" and password == "admin123":
            return True, {
                'id': 'admin',
                'name': '관리자',
                'team': '인사팀',
                'position': '팀장',
                'grade': 'Manager'
            }
    
    return False, None

# 라우트 정의
@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """로그인 페이지"""
    if request.method == 'POST':
        user_type = request.form['user_type']
        user_id = request.form['user_id']
        password = request.form['password']
        
        success, user_data = authenticate_user(user_type, user_id, password)
        
        if success:
            session['user_type'] = user_type
            session['user_data'] = user_data
            return redirect(url_for('dashboard'))
        else:
            flash('로그인에 실패했습니다. 아이디와 비밀번호를 확인해주세요.')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """로그아웃"""
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    """대시보드"""
    if 'user_type' not in session:
        return redirect(url_for('login'))
    
    user_type = session['user_type']
    user_data = session['user_data']
    
    if user_type == "피평가자":
        return render_template('employee_dashboard.html', user_data=user_data)
    elif user_type == "평가자(팀장)":
        return render_template('team_leader_dashboard.html', user_data=user_data)
    elif user_type == "평가자(임원)":
        return render_template('executive_dashboard.html', user_data=user_data)
    elif user_type == "관리자(인사담당자)":
        # 관리자는 모든 평가 데이터 조회
        conn = sqlite3.connect('evaluation.db')
        cursor = conn.cursor()
        
        # 모든 평가 데이터 조회
        cursor.execute('''
            SELECT ed.evaluator_id, ed.evaluatee_id, ed.evaluation_type, ed.scores, ed.comments, ed.created_at
            FROM evaluation_data ed
            ORDER BY ed.created_at DESC
        ''')
        
        evaluations = cursor.fetchall()
        
        # 모든 실적 데이터 조회
        cursor.execute('''
            SELECT pd.employee_id, pd.performance_order, pd.project_name, pd.performance, pd.created_at, pd.is_finalized
            FROM performance_data pd
            ORDER BY pd.employee_id, pd.performance_order
        ''')
        
        performance_data = cursor.fetchall()
        
        # 평가자별로 그룹화 (사용자 정보는 평가 데이터에서 직접 처리)
        evaluator_stats = {}
        for eval_data in evaluations:
            evaluator_id = eval_data[0]
            evaluatee_id = eval_data[1]
            eval_type = eval_data[2]
            scores = eval_data[3]
            comments = eval_data[4]
            created_at = eval_data[5]
            
            if evaluator_id not in evaluator_stats:
                evaluator_stats[evaluator_id] = {
                    'info': {
                        'name': f'평가자 {evaluator_id}',
                        'team': 'Unknown',
                        'position': 'Unknown',
                        'grade': 'Unknown'
                    },
                    'evaluations': {}
                }
            
            if eval_type not in evaluator_stats[evaluator_id]['evaluations']:
                evaluator_stats[evaluator_id]['evaluations'][eval_type] = []
            
            # 피평가자 정보를 더 자세히 표시 (실제 이름이 있다면 사용, 없으면 사번만)
            evaluatee_name = f'사번 {evaluatee_id}'
            # 실제 사용자 데이터가 있다면 이름을 가져올 수 있도록 확장 가능
            
            evaluator_stats[evaluator_id]['evaluations'][eval_type].append({
                'evaluatee_id': evaluatee_id,
                'evaluatee_name': evaluatee_name,
                'evaluatee_team': 'Unknown',
                'evaluatee_position': 'Unknown',
                'scores': scores,
                'comments': comments,
                'created_at': created_at
            })
        
        # 실적 데이터를 피평가자별로 그룹화
        performance_stats = {}
        for perf_data in performance_data:
            employee_id = perf_data[0]
            performance_order = perf_data[1]
            project_name = perf_data[2]
            performance = perf_data[3]
            created_at = perf_data[4]
            is_finalized = perf_data[5]
            
            if employee_id not in performance_stats:
                performance_stats[employee_id] = {
                    'info': {
                        'name': f'피평가자 {employee_id}',
                        'team': 'Unknown',
                        'position': 'Unknown'
                    },
                    'performances': []
                }
            
            performance_stats[employee_id]['performances'].append({
                'order': performance_order,
                'project_name': project_name,
                'performance': performance,
                'created_at': created_at,
                'is_finalized': is_finalized
            })
        
        conn.close()
        
        return render_template('admin_dashboard.html', 
                             user_data=user_data, 
                             evaluator_stats=evaluator_stats,
                             performance_stats=performance_stats)

@app.route('/performance', methods=['GET', 'POST'])
def performance():
    """실적 작성 페이지"""
    if 'user_type' not in session or session['user_type'] != "피평가자":
        return redirect(url_for('login'))
    
    user_data = session['user_data']
    
    if request.method == 'POST':
        # 기존 실적 데이터 가져오기
        conn = sqlite3.connect('evaluation.db')
        cursor = conn.cursor()
        cursor.execute('SELECT performance_order FROM performance_data WHERE employee_id = ? AND is_finalized = FALSE', 
                      (user_data['id'],))
        existing_orders = [row[0] for row in cursor.fetchall()]
        
        # 폼 데이터 처리
        for i in range(1, 11):  # 1부터 10까지
            project_name = request.form.get(f'project_name_{i}', '').strip()
            performance = request.form.get(f'performance_{i}', '').strip()
            
            if project_name and performance:  # 둘 다 입력된 경우만 저장
                if i in existing_orders:
                    # 기존 실적 업데이트
                    cursor.execute('''
                        UPDATE performance_data 
                        SET project_name = ?, performance = ?, created_at = CURRENT_TIMESTAMP
                        WHERE employee_id = ? AND performance_order = ? AND is_finalized = FALSE
                    ''', (project_name, performance, user_data['id'], i))
                else:
                    # 새 실적 등록
                    cursor.execute('''
                        INSERT INTO performance_data (employee_id, performance_order, project_name, performance)
                        VALUES (?, ?, ?, ?)
                    ''', (user_data['id'], i, project_name, performance))
        
        conn.commit()
        conn.close()
        
        flash('실적이 등록되었습니다.')
        return redirect(url_for('performance'))
    
    # 기존 실적 조회
    conn = sqlite3.connect('evaluation.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT performance_order, project_name, performance, created_at, is_finalized 
        FROM performance_data 
        WHERE employee_id = ? 
        ORDER BY performance_order
    ''', (user_data['id'],))
    performance_data = cursor.fetchall()
    conn.close()
    
    # 실적 데이터를 딕셔너리로 변환
    performance_dict = {}
    is_finalized = False
    for row in performance_data:
        performance_dict[row[0]] = {
            'project_name': row[1],
            'performance': row[2],
            'created_at': row[3]
        }
        if row[4]:  # is_finalized
            is_finalized = True
    
    return render_template('performance.html', 
                         user_data=user_data, 
                         performance_data=performance_dict,
                         is_finalized=is_finalized)

@app.route('/finalize_performance', methods=['POST'])
def finalize_performance():
    """실적 최종 등록"""
    if 'user_type' not in session or session['user_type'] != "피평가자":
        return jsonify({'success': False, 'message': '권한이 없습니다.'})
    
    user_data = session['user_data']
    
    conn = sqlite3.connect('evaluation.db')
    cursor = conn.cursor()
    
    # 최소 1개 이상의 실적이 있는지 확인
    cursor.execute('SELECT COUNT(*) FROM performance_data WHERE employee_id = ? AND is_finalized = FALSE', 
                  (user_data['id'],))
    count = cursor.fetchone()[0]
    
    if count == 0:
        conn.close()
        return jsonify({'success': False, 'message': '최소 1개 이상의 실적을 작성해주세요.'})
    
    cursor.execute('''
        UPDATE performance_data 
        SET is_finalized = TRUE
        WHERE employee_id = ? AND is_finalized = FALSE
    ''', (user_data['id'],))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': '실적이 최종 등록되었습니다.'})

@app.route('/evaluate/<evaluation_type>')
def evaluate(evaluation_type):
    """평가 페이지"""
    if 'user_type' not in session or session['user_type'] not in ["평가자(팀장)", "평가자(임원)"]:
        return redirect(url_for('login'))
    
    user_data = session['user_data']
    mappings = load_evaluation_mappings()
    backdata = load_backdata()
    jikkeup = load_jikkeup()
    
    # 평가 대상자 목록 가져오기
    evaluatees = []
    
    if session['user_type'] == "평가자(팀장)":
        if evaluation_type == "employee":
            mapping_data = mappings['team_leader_employee']
        elif evaluation_type == "manager":
            mapping_data = mappings['team_leader_manager']
        elif evaluation_type == "general":
            mapping_data = mappings['team_leader_general']
        else:
            return redirect(url_for('dashboard'))
    else:  # 평가자(임원)
        if evaluation_type == "team_leader":
            mapping_data = mappings['executive_team_leader']
        elif evaluation_type == "manager":
            mapping_data = mappings['executive_manager']
        elif evaluation_type == "general":
            mapping_data = mappings['executive_general']
        else:
            return redirect(url_for('dashboard'))
    
    # 평가 대상자 정보 가져오기
    for _, row in mapping_data.iterrows():
        if str(row['evaluaterid']) == str(user_data['id']):
            evaluatee_id = int(row['evaluateeid'])  # Int64를 int로 변환
            evaluatee_data = backdata[backdata.iloc[:, 0] == evaluatee_id]
            if not evaluatee_data.empty:
                # 직전 평가 점수 가져오기
                before_point = 0
                
                # 평가자(임원)의 팀원 평가(관리직)인 경우, 팀장 평가 점수를 가져오기
                if session['user_type'] == "평가자(임원)" and evaluation_type == "manager":
                    # 팀장의 평가자 ID들 (평가자(팀장)_대리이상.csv에서 가져온 ID들)
                    team_leader_ids = [11050121, 11980036, 11040086, 11080043, 11040050, 11010060]
                    
                    # 데이터베이스에서 팀장이 해당 직원에 대해 manager 평가 타입으로 제출한 점수 조회
                    conn = sqlite3.connect('evaluation.db')
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT scores FROM evaluation_data 
                        WHERE evaluatee_id = ? AND evaluation_type = 'manager' 
                        AND evaluator_id IN ({})
                        ORDER BY created_at DESC LIMIT 1
                    '''.format(','.join(map(str, team_leader_ids))), (evaluatee_id,))
                    result = cursor.fetchone()
                    conn.close()
                    
                    if result:
                        try:
                            scores_data = json.loads(result[0])
                            before_point = scores_data.get('score', 0)
                        except:
                            before_point = 0
                else:
                    # 기존 방식: backdata의 I열에서 직전 점수 가져오기
                    try:
                        before_point = int(evaluatee_data.iloc[0, 8])  # I열(인덱스 8)에서 직전 점수 가져오기
                    except:
                        before_point = 0
                
                evaluatees.append({
                    'id': str(evaluatee_id),  # 문자열로 변환
                    'name': str(evaluatee_data.iloc[0, 2]),  # 문자열로 변환
                    'team': str(evaluatee_data.iloc[0, 3]),  # 문자열로 변환
                    'position': str(evaluatee_data.iloc[0, 4]),  # 문자열로 변환
                    'grade': str(evaluatee_data.iloc[0, 5]),  # 문자열로 변환
                    'before_point': before_point
                })
    
    # 직급별로 그룹화
    grade_groups = {}
    # 사원 평가(절대평가)는 모든 사용자 타입에서 직급별 그룹화
    if evaluation_type == 'employee':
        for evaluatee in evaluatees:
            grade = evaluatee['grade']
            if grade not in grade_groups:
                grade_groups[grade] = []
            grade_groups[grade].append(evaluatee)
    # 상대평가는 임원만 직급별 그룹화
    elif session['user_type'] == "평가자(임원)":
        for evaluatee in evaluatees:
            grade = evaluatee['grade']
            if grade not in grade_groups:
                grade_groups[grade] = []
            grade_groups[grade].append(evaluatee)
        
        # 평가자(임원)의 팀원 평가(관리직)에서 직급 순서 조정: Professional → Manager4 → Manager3 → Manager2 → Manager1
        if evaluation_type == 'manager':
            # 원하는 순서대로 직급 정의
            grade_order = ['Professional', 'Manager4', 'Manager3', 'Manager2', 'Manager1']
            
            # 새로운 순서로 grade_groups 재정렬
            new_grade_groups = {}
            for grade in grade_order:
                if grade in grade_groups:
                    new_grade_groups[grade] = grade_groups[grade]
            
            # 정의된 순서에 없는 직급들도 추가 (기타 직급들)
            for grade in grade_groups.keys():
                if grade not in grade_order:
                    new_grade_groups[grade] = grade_groups[grade]
            
            grade_groups = new_grade_groups
 
    return render_template('evaluate.html', 
                         user_data=user_data, 
                         evaluatees=evaluatees, 
                         grade_groups=grade_groups,
                         evaluation_type=evaluation_type,
                         jikkeup=jikkeup if jikkeup is not None else None)

@app.route('/submit_evaluation', methods=['POST'])
def submit_evaluation():
    """평가 제출"""
    if 'user_type' not in session or session['user_type'] not in ["평가자(팀장)", "평가자(임원)"]:
        return jsonify({'success': False, 'message': '권한이 없습니다.'})
    
    data = request.get_json()
    evaluator_id = session['user_data']['id']
    evaluatee_id = data['evaluatee_id']
    evaluation_type = data['evaluation_type']
    scores = data.get('scores', {})
    comments = data.get('comments', '')
    
    conn = sqlite3.connect('evaluation.db')
    cursor = conn.cursor()
    
    # 기존 평가가 있는지 확인
    cursor.execute('''
        SELECT * FROM evaluation_data 
        WHERE evaluator_id = ? AND evaluatee_id = ? AND evaluation_type = ?
    ''', (evaluator_id, evaluatee_id, evaluation_type))
    
    existing = cursor.fetchone()
    
    if existing:
        # 기존 평가 업데이트 (임시저장이므로 is_final=0)
        cursor.execute('''
            UPDATE evaluation_data 
            SET scores = ?, comments = ?, is_final = 0, created_at = CURRENT_TIMESTAMP
            WHERE evaluator_id = ? AND evaluatee_id = ? AND evaluation_type = ?
        ''', (json.dumps(scores, ensure_ascii=False), comments, evaluator_id, evaluatee_id, evaluation_type))
    else:
        # 새 평가 등록 (임시저장이므로 is_final=0)
        cursor.execute('''
            INSERT INTO evaluation_data (evaluator_id, evaluatee_id, evaluation_type, scores, comments, is_final)
            VALUES (?, ?, ?, ?, ?, 0)
        ''', (evaluator_id, evaluatee_id, evaluation_type, json.dumps(scores, ensure_ascii=False), comments))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': '평가가 제출되었습니다.'})

@app.route('/submit_evaluations_bulk', methods=['POST'])
def submit_evaluations_bulk():
    """여러 명의 평가를 한 번에 제출"""
    if 'user_type' not in session or session['user_type'] not in ["평가자(임원)"]:
        return jsonify({'success': False, 'message': '권한이 없습니다.'})
    
    payload = request.get_json() or {}
    evaluation_type = payload.get('evaluation_type')
    evaluations = payload.get('evaluations', [])
    evaluator_id = session['user_data']['id']
    
    if evaluation_type is None or not evaluations:
        return jsonify({'success': False, 'message': '평가 데이터가 비어 있습니다.'})
    
    conn = sqlite3.connect('evaluation.db')
    cursor = conn.cursor()
    
    for item in evaluations:
        evaluatee_id = item.get('evaluatee_id')
        scores = item.get('scores', {})
        comments = item.get('comments', '')
        if not evaluatee_id:
            continue
        
        # upsert
        cursor.execute('''
            SELECT id FROM evaluation_data
            WHERE evaluator_id = ? AND evaluatee_id = ? AND evaluation_type = ?
        ''', (evaluator_id, evaluatee_id, evaluation_type))
        row = cursor.fetchone()
        if row:
            cursor.execute('''
                UPDATE evaluation_data
                SET scores = ?, comments = ?, is_final = 0, created_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (json.dumps(scores, ensure_ascii=False), comments, row[0]))
        else:
            cursor.execute('''
                INSERT INTO evaluation_data (evaluator_id, evaluatee_id, evaluation_type, scores, comments, is_final)
                VALUES (?, ?, ?, ?, ?, 0)
            ''', (evaluator_id, evaluatee_id, evaluation_type, json.dumps(scores, ensure_ascii=False), comments))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'count': len(evaluations)})

@app.route('/finalize_evaluation', methods=['POST'])
def finalize_evaluation():
    """최종제출 처리"""
    if 'user_type' not in session or session['user_type'] not in ["평가자(팀장)", "평가자(임원)"]:
        return jsonify({'success': False, 'message': '권한이 없습니다.'})
    
    data = request.get_json()
    evaluator_id = session['user_data']['id']
    evaluation_type = data['evaluation_type']
    
    print(f"Finalizing evaluation: evaluator_id={evaluator_id}, evaluation_type={evaluation_type}")
    
    conn = sqlite3.connect('evaluation.db')
    cursor = conn.cursor()
    
    # 해당 평가자의 해당 평가 유형의 모든 임시저장 데이터를 최종제출로 변경
    cursor.execute('''
        UPDATE evaluation_data 
        SET is_final = 1, created_at = CURRENT_TIMESTAMP
        WHERE evaluator_id = ? AND evaluation_type = ? AND is_final = 0
    ''', (evaluator_id, evaluation_type))
    
    updated_count = cursor.rowcount
    print(f"Updated {updated_count} records to final")
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': '최종제출이 완료되었습니다.', 'updated_count': updated_count})

@app.route('/check_final_submit_status/<evaluation_type>')
def check_final_submit_status(evaluation_type):
    """최종제출 상태 확인"""
    if 'user_type' not in session or session['user_type'] not in ["평가자(팀장)", "평가자(임원)"]:
        return jsonify({'success': False, 'message': '권한이 없습니다.'})
    
    evaluator_id = session['user_data']['id']
    
    conn = sqlite3.connect('evaluation.db')
    cursor = conn.cursor()
    
    # 최종제출 상태 확인 (is_final=1인 데이터가 있으면 최종제출된 것으로 간주)
    cursor.execute('''
        SELECT COUNT(*) FROM evaluation_data 
        WHERE evaluator_id = ? AND evaluation_type = ? AND is_final = 1
    ''', (evaluator_id, evaluation_type))
    
    count = cursor.fetchone()[0]
    conn.close()
    
    is_finalized = count > 0
    
    return jsonify({
        'success': True, 
        'is_finalized': is_finalized,
        'message': '최종제출 완료' if is_finalized else '미제출'
    })

@app.route('/get_saved_evaluation/<evaluation_type>')
def get_saved_evaluation(evaluation_type):
    """저장된 평가 데이터 조회"""
    if 'user_type' not in session or session['user_type'] not in ["평가자(팀장)", "평가자(임원)"]:
        return jsonify({'success': False, 'message': '권한이 없습니다.'})
    
    evaluator_id = session['user_data']['id']
    
    conn = sqlite3.connect('evaluation.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT evaluatee_id, scores, comments, created_at 
        FROM evaluation_data 
        WHERE evaluator_id = ? AND evaluation_type = ?
        ORDER BY created_at DESC
    ''', (evaluator_id, evaluation_type))
    saved_evaluations = cursor.fetchall()
    conn.close()
    
    evaluations = {}
    for row in saved_evaluations:
        evaluatee_id = str(row[0])
        try:
            scores = json.loads(row[1]) if row[1] else {}
        except:
            scores = {}
        comments = row[2] or ''
        created_at = row[3]
        
        evaluations[evaluatee_id] = {
            'scores': scores,
            'comments': comments,
            'created_at': created_at
        }
    
    return jsonify({'success': True, 'data': evaluations})

@app.route('/get_performance/<employee_id>')
def get_performance(employee_id):
    """직원 실적 조회"""
    if 'user_type' not in session or session['user_type'] not in ["평가자(팀장)", "평가자(임원)"]:
        return jsonify({'success': False, 'message': '권한이 없습니다.'})
    
    print(f"실적 조회 요청: employee_id={employee_id}")
    
    conn = sqlite3.connect('evaluation.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT performance_order, project_name, performance, created_at 
        FROM performance_data 
        WHERE employee_id = ? AND is_finalized = TRUE
        ORDER BY performance_order
    ''', (employee_id,))
    performance_data = cursor.fetchall()
    conn.close()
    
    print(f"조회된 실적 데이터: {performance_data}")
    
    if performance_data:
        performances = []
        for row in performance_data:
            performances.append({
                'order': row[0],
                'project_name': row[1],
                'performance': row[2],
                'created_at': row[3]
            })
        result = {'success': True, 'data': performances}
        print(f"반환할 결과: {result}")
        return jsonify(result)
    else:
        result = {'success': False, 'message': '실적 데이터가 없습니다.'}
        print(f"반환할 결과: {result}")
        return jsonify(result)

@app.route('/download_excel')
def download_excel():
    """평가 데이터를 엑셀 파일로 다운로드"""
    if 'user_type' not in session or session['user_type'] != "관리자(인사담당자)":
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('evaluation.db')
    cursor = conn.cursor()
    
    # 모든 평가 데이터 조회
    cursor.execute('''
        SELECT ed.evaluator_id, ed.evaluatee_id, ed.evaluation_type, ed.scores, ed.comments, ed.created_at
        FROM evaluation_data ed
        ORDER BY ed.created_at DESC
    ''')
    
    evaluations = cursor.fetchall()
    conn.close()
    
    # 데이터를 DataFrame으로 변환
    data = []
    for eval_data in evaluations:
        evaluator_id = eval_data[0]
        evaluatee_id = eval_data[1]
        eval_type = eval_data[2]
        scores = eval_data[3]
        comments = eval_data[4]
        created_at = eval_data[5]
        
        # 평가 유형 한글 변환
        eval_type_korean = {
            'employee': '사원 평가',
            'manager': '관리직 평가',
            'general': '일반직 평가',
            'team_leader': '팀장 평가'
        }.get(eval_type, eval_type)
        
        # 점수 파싱 (JSON 문자열인 경우)
        try:
            if scores:
                scores_dict = json.loads(scores) if isinstance(scores, str) else scores
                if eval_type == 'employee':
                    # 사원 평가는 합계만 표시
                    if isinstance(scores_dict, dict) and 'total' in scores_dict:
                        scores_str = f"합계: {scores_dict['total']}"
                    else:
                        scores_str = f"합계: {scores}"
                else:
                    # 다른 평가는 전체 점수 표시
                    scores_str = ', '.join([f"{k}: {v}" for k, v in scores_dict.items()])
            else:
                scores_str = "점수 없음"
        except:
            scores_str = str(scores) if scores else "점수 없음"
        
        data.append({
            '평가자 ID': evaluator_id,
            '평가자명': f'평가자 {evaluator_id}',
            '피평가자 ID': evaluatee_id,
            '피평가자명': f'피평가자 {evaluatee_id}',
            '평가 유형': eval_type_korean,
            '평가 점수': scores_str,
            '평가 코멘트': comments if comments else '',
            '평가 일시': created_at
        })
    
    # DataFrame 생성
    df = pd.DataFrame(data)
    
    # 엑셀 파일 생성
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='평가데이터', index=False)
    
    output.seek(0)
    
    # 파일명에 현재 날짜 포함
    current_date = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'evaluation_data_{current_date}.xlsx'
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    
    return response

@app.route('/reset_evaluations')
def reset_evaluations():
    """평가 데이터 초기화 (관리자만 가능)"""
    if 'user_type' not in session or session['user_type'] != "관리자(인사담당자)":
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('evaluation.db')
    cursor = conn.cursor()
    
    # 모든 평가 데이터 삭제
    cursor.execute('DELETE FROM evaluation_data')
    
    conn.commit()
    conn.close()
    
    flash('모든 평가 데이터가 초기화되었습니다.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/reset_evaluator/<evaluator_id>')
def reset_evaluator(evaluator_id):
    """특정 평가자의 평가 데이터 초기화 (관리자만 가능)"""
    if 'user_type' not in session or session['user_type'] != "관리자(인사담당자)":
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('evaluation.db')
    cursor = conn.cursor()
    
    # 특정 평가자의 평가 데이터 삭제
    cursor.execute('DELETE FROM evaluation_data WHERE evaluator_id = ?', (evaluator_id,))
    deleted_count = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    flash(f'평가자 {evaluator_id}의 평가 데이터 {deleted_count}건이 초기화되었습니다.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/reset_performance/<employee_id>')
def reset_performance(employee_id):
    """특정 피평가자의 실적 데이터 초기화 (관리자만 가능)"""
    if 'user_type' not in session or session['user_type'] != "관리자(인사담당자)":
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('evaluation.db')
    cursor = conn.cursor()
    
    # 특정 피평가자의 실적 데이터 삭제
    cursor.execute('DELETE FROM performance_data WHERE employee_id = ?', (employee_id,))
    deleted_count = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    flash(f'피평가자 {employee_id}의 실적 데이터 {deleted_count}건이 초기화되었습니다.', 'success')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    # Railway 배포 시 debug=False로 설정
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=port)

# Railway 배포를 위한 헬스체크 엔드포인트 추가
@app.route('/health')
def health_check():
    """Railway 헬스체크용 엔드포인트"""
    try:
        # 간단한 데이터베이스 연결 테스트
        conn = get_db_connection()
        conn.close()
        return {'status': 'healthy', 'message': 'Evaluation system is running'}, 200
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}, 500

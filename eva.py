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

def get_excluded_evaluatee_ids():
    """환경변수 EXCLUDED_EVALUATEE_IDS(콤마 구분)에서 제외할 피평가자 ID 집합을 반환"""
    raw = os.environ.get('EXCLUDED_EVALUATEE_IDS', '')
    excluded_ids = set()
    if raw:
        for part in raw.split(','):
            part = part.strip()
            if not part:
                continue
            try:
                excluded_ids.add(int(part))
            except Exception:
                # 잘못된 값은 무시
                pass
    return excluded_ids

def get_all_excluded_evaluatee_ids():
    """코드에 박힌 기본 제외 + 환경변수 설정 제외를 합쳐 반환"""
    default_excluded = {11160147, 11960038, 12140051}
    return default_excluded | get_excluded_evaluatee_ids()

def get_excluded_evaluatee_names():
    """환경변수 EXCLUDED_EVALUATEE_NAMES(콤마 구분)에서 제외할 피평가자 이름 집합을 반환"""
    raw = os.environ.get('EXCLUDED_EVALUATEE_NAMES', '')
    excluded_names = set()
    if not raw:
        return excluded_names
    for part in raw.split(','):
        name = part.strip()
        if name:
            excluded_names.add(name)
    return excluded_names

def get_db_connection():
    """데이터베이스 연결 (Railway PostgreSQL 또는 로컬 SQLite)"""
    if HEROKU_MODE and os.environ.get('DATABASE_URL'):
        # Railway PostgreSQL
        DATABASE_URL = os.environ.get('DATABASE_URL')
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        conn = psycopg2.connect(DATABASE_URL)
        # Postgres에서는 DDL이 반영되도록 autocommit 활성화
        try:
            conn.autocommit = True
        except Exception:
            pass
        return conn
    else:
        # 로컬 SQLite
        return sqlite3.connect('evaluation.db')

def is_postgresql():
    """PostgreSQL 사용 여부 확인"""
    return HEROKU_MODE and os.environ.get('DATABASE_URL')

def adapt_query(query: str) -> str:
    """DB 드라이버별 플레이스홀더 변환.
    SQLite: '?', PostgreSQL(psycopg2): '%s'
    """
    if is_postgresql():
        return query.replace('?', '%s')
    return query

def commit_db(conn):
    """데이터베이스 커밋"""
    try:
        conn.commit()
    except Exception:
        # autocommit일 때는 commit이 필요 없음
        pass

# 안전 초기화 도우미
def safe_init_db():
    try:
        init_db()
    except Exception as e:
        print(f"safe_init_db error: {e}")

# Flask 2.3+에서는 before_first_request가 deprecated되었으므로
# 앱 시작 시 직접 초기화하거나 첫 요청 시 초기화
_db_initialized = False

@app.before_request
def _ensure_db_initialized():
    global _db_initialized
    # 헬스체크는 DB 초기화 없이 통과
    if request.endpoint == 'health_check':
        return
    
    # 최초 한 번만 실행되도록 플래그 사용
    if not _db_initialized:
        try:
            init_db()
            _db_initialized = True
            print("Database initialized successfully")
        except Exception as e:
            # 초기화 실패 시에도 앱이 죽지 않도록 로그만 남김
            print(f"DB init error: {e}")
            _db_initialized = True  # 실패해도 재시도 방지

# 앱 로드 시 DB 초기화 시도 (Gunicorn preload 시에도 작동)
# 하지만 실패해도 앱은 시작되도록 함
try:
    safe_init_db()
    print("Database pre-initialized on app load")
except Exception as e:
    print(f"Pre-init DB error (will retry on first request): {e}")

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
    """데이터베이스 초기화 (PostgreSQL 또는 SQLite)"""
    conn = get_db_connection()
    
    if HEROKU_MODE and os.environ.get('DATABASE_URL'):
        # PostgreSQL
        cursor = conn.cursor()
        
        # 실적 데이터 테이블 (최대 10개 실적 지원)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_data (
                id SERIAL PRIMARY KEY,
                employee_id TEXT NOT NULL,
                performance_order INTEGER NOT NULL,
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
                id SERIAL PRIMARY KEY,
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
        except psycopg2.errors.DuplicateColumn:
            # 컬럼이 이미 존재하는 경우 무시
            pass
        
        # 조직도 관련 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS departments (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                leader_position TEXT,
                parent_id INTEGER,
                display_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS department_employees (
                id SERIAL PRIMARY KEY,
                department_id INTEGER NOT NULL,
                employee_id TEXT NOT NULL,
                position TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE,
                UNIQUE(department_id, employee_id)
            )
        ''')
        
        commit_db(conn)
        conn.close()
    else:
        # SQLite
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
        
        # 조직도 관련 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                leader_position TEXT,
                parent_id INTEGER,
                display_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES departments(id) ON DELETE SET NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS department_employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                department_id INTEGER NOT NULL,
                employee_id TEXT NOT NULL,
                position TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE,
                UNIQUE(department_id, employee_id)
            )
        ''')
        
        commit_db(conn)
        commit_db(conn)
    conn.close()

# 모듈 로드 시 DB 초기화는 지연시킨다. 실제 요청 시 또는 앱 시작 후에 준비됨
print("Deferred DB init: will initialize on first request/startup")

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
            # 피평가자 로그인 제외: 기본 + 환경변수 설정
            if int(user_id) in get_all_excluded_evaluatee_ids():
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
    # 일부 환경에서 초기화 타이밍 이슈를 방지
    safe_init_db()
    
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
        conn = get_db_connection()
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
        
        commit_db(conn)
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
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(adapt_query('SELECT performance_order FROM performance_data WHERE employee_id = ? AND is_finalized = FALSE'), 
                      (user_data['id'],))
        existing_orders = [row[0] for row in cursor.fetchall()]
        
        # 폼 데이터 처리
        for i in range(1, 11):  # 1부터 10까지
            project_name = request.form.get(f'project_name_{i}', '').strip()
            performance = request.form.get(f'performance_{i}', '').strip()
            
            if project_name and performance:  # 둘 다 입력된 경우만 저장
                if i in existing_orders:
                    # 기존 실적 업데이트
                    cursor.execute(adapt_query('''
                        UPDATE performance_data 
                        SET project_name = ?, performance = ?, created_at = CURRENT_TIMESTAMP
                        WHERE employee_id = ? AND performance_order = ? AND is_finalized = FALSE
                    '''), (project_name, performance, user_data['id'], i))
                else:
                    # 새 실적 등록
                    cursor.execute(adapt_query('''
                        INSERT INTO performance_data (employee_id, performance_order, project_name, performance)
                        VALUES (?, ?, ?, ?)
                    '''), (user_data['id'], i, project_name, performance))
        
        commit_db(conn)
        conn.close()
        
        flash('실적이 등록되었습니다.')
        return redirect(url_for('performance'))
    
    # 기존 실적 조회
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(adapt_query('''
        SELECT performance_order, project_name, performance, created_at, is_finalized 
        FROM performance_data 
        WHERE employee_id = ? 
        ORDER BY performance_order
    '''), (user_data['id'],))
    performance_data = cursor.fetchall()
    commit_db(conn)
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
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 최소 1개 이상의 실적이 있는지 확인
    cursor.execute(adapt_query('SELECT COUNT(*) FROM performance_data WHERE employee_id = ? AND is_finalized = FALSE'), 
                  (user_data['id'],))
    count = cursor.fetchone()[0]
    
    if count == 0:
        commit_db(conn)
        conn.close()
        return jsonify({'success': False, 'message': '최소 1개 이상의 실적을 작성해주세요.'})
    
    cursor.execute(adapt_query('''
        UPDATE performance_data 
        SET is_finalized = TRUE
        WHERE employee_id = ? AND is_finalized = FALSE
    '''), (user_data['id'],))
    
    commit_db(conn)
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
            # 제외 대상이면 스킵
            if evaluatee_id in get_all_excluded_evaluatee_ids():
                continue
            evaluatee_data = backdata[backdata.iloc[:, 0] == evaluatee_id]
            if not evaluatee_data.empty:
                # 직전 평가 점수 가져오기
                before_point = 0
                # 이름 기반 제외도 지원
                excluded_names = get_excluded_evaluatee_names()
                evaluatee_name_str = str(evaluatee_data.iloc[0, 2])
                if evaluatee_name_str in excluded_names:
                    continue
                
                # 평가자(임원)의 팀원 평가(관리직)인 경우, 팀장 평가 점수를 가져오기
                if session['user_type'] == "평가자(임원)" and evaluation_type == "manager":
                    # 팀장의 평가자 ID들 (평가자(팀장)_대리이상.csv에서 가져온 ID들)
                    team_leader_ids = [11050121, 11980036, 11040086, 11080043, 11040050, 11010060]
                    
                    # 데이터베이스에서 팀장이 해당 직원에 대해 manager 평가 타입으로 제출한 점수 조회
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(adapt_query('''
                        SELECT scores FROM evaluation_data 
                        WHERE evaluatee_id = ? AND evaluation_type = 'manager' 
                        AND evaluator_id IN ({})
                        ORDER BY created_at DESC LIMIT 1
                    '''.format(','.join(map(str, team_leader_ids)))), (evaluatee_id,))
                    result = cursor.fetchone()
                    commit_db(conn)
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
                    'name': evaluatee_name_str,  # 문자열로 변환
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
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 기존 평가가 있는지 확인
    cursor.execute(adapt_query('''
        SELECT * FROM evaluation_data 
        WHERE evaluator_id = ? AND evaluatee_id = ? AND evaluation_type = ?
    '''), (evaluator_id, evaluatee_id, evaluation_type))
    
    existing = cursor.fetchone()
    
    if existing:
        # 기존 평가 업데이트 (임시저장이므로 is_final=0)
        cursor.execute(adapt_query('''
            UPDATE evaluation_data 
            SET scores = ?, comments = ?, is_final = 0, created_at = CURRENT_TIMESTAMP
            WHERE evaluator_id = ? AND evaluatee_id = ? AND evaluation_type = ?
        '''), (json.dumps(scores, ensure_ascii=False), comments, evaluator_id, evaluatee_id, evaluation_type))
    else:
        # 새 평가 등록 (임시저장이므로 is_final=0)
        cursor.execute(adapt_query('''
            INSERT INTO evaluation_data (evaluator_id, evaluatee_id, evaluation_type, scores, comments, is_final)
            VALUES (?, ?, ?, ?, ?, 0)
        '''), (evaluator_id, evaluatee_id, evaluation_type, json.dumps(scores, ensure_ascii=False), comments))
    
    commit_db(conn)
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
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for item in evaluations:
        evaluatee_id = item.get('evaluatee_id')
        scores = item.get('scores', {})
        comments = item.get('comments', '')
        if not evaluatee_id:
            continue
        
        # upsert
        cursor.execute(adapt_query('''
            SELECT id FROM evaluation_data
            WHERE evaluator_id = ? AND evaluatee_id = ? AND evaluation_type = ?
        '''), (evaluator_id, evaluatee_id, evaluation_type))
        row = cursor.fetchone()
        if row:
            cursor.execute(adapt_query('''
                UPDATE evaluation_data
                SET scores = ?, comments = ?, is_final = 0, created_at = CURRENT_TIMESTAMP
                WHERE id = ?
            '''), (json.dumps(scores, ensure_ascii=False), comments, row[0]))
        else:
            cursor.execute(adapt_query('''
                INSERT INTO evaluation_data (evaluator_id, evaluatee_id, evaluation_type, scores, comments, is_final)
                VALUES (?, ?, ?, ?, ?, 0)
            '''), (evaluator_id, evaluatee_id, evaluation_type, json.dumps(scores, ensure_ascii=False), comments))
    
    commit_db(conn)
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
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 해당 평가자의 해당 평가 유형의 모든 임시저장 데이터를 최종제출로 변경
    cursor.execute(adapt_query('''
        UPDATE evaluation_data 
        SET is_final = 1, created_at = CURRENT_TIMESTAMP
        WHERE evaluator_id = ? AND evaluation_type = ? AND is_final = 0
    '''), (evaluator_id, evaluation_type))
    
    updated_count = cursor.rowcount
    print(f"Updated {updated_count} records to final")
    
    commit_db(conn)
    conn.close()
    
    return jsonify({'success': True, 'message': '최종제출이 완료되었습니다.', 'updated_count': updated_count})

@app.route('/check_final_submit_status/<evaluation_type>')
def check_final_submit_status(evaluation_type):
    """최종제출 상태 확인"""
    if 'user_type' not in session or session['user_type'] not in ["평가자(팀장)", "평가자(임원)"]:
        return jsonify({'success': False, 'message': '권한이 없습니다.'})
    
    evaluator_id = session['user_data']['id']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 최종제출 상태 확인 (is_final=1인 데이터가 있으면 최종제출된 것으로 간주)
    cursor.execute(adapt_query('''
        SELECT COUNT(*) FROM evaluation_data 
        WHERE evaluator_id = ? AND evaluation_type = ? AND is_final = 1
    '''), (evaluator_id, evaluation_type))
    
    count = cursor.fetchone()[0]
    commit_db(conn)
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
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(adapt_query('''
        SELECT evaluatee_id, scores, comments, created_at 
        FROM evaluation_data 
        WHERE evaluator_id = ? AND evaluation_type = ?
        ORDER BY created_at DESC
    '''), (evaluator_id, evaluation_type))
    saved_evaluations = cursor.fetchall()
    commit_db(conn)
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
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(adapt_query('''
        SELECT performance_order, project_name, performance, created_at 
        FROM performance_data 
        WHERE employee_id = ? AND is_finalized = TRUE
        ORDER BY performance_order
    '''), (employee_id,))
    performance_data = cursor.fetchall()
    commit_db(conn)
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
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 모든 평가 데이터 조회
    cursor.execute('''
        SELECT ed.evaluator_id, ed.evaluatee_id, ed.evaluation_type, ed.scores, ed.comments, ed.created_at
        FROM evaluation_data ed
        ORDER BY ed.created_at DESC
    ''')
    
    evaluations = cursor.fetchall()
    commit_db(conn)
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
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 모든 평가 데이터 삭제
    cursor.execute('DELETE FROM evaluation_data')
    
    commit_db(conn)
    conn.close()
    
    flash('모든 평가 데이터가 초기화되었습니다.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/reset_evaluator/<evaluator_id>')
def reset_evaluator(evaluator_id):
    """특정 평가자의 평가 데이터 초기화 (관리자만 가능)"""
    if 'user_type' not in session or session['user_type'] != "관리자(인사담당자)":
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 특정 평가자의 평가 데이터 삭제
    cursor.execute(adapt_query('DELETE FROM evaluation_data WHERE evaluator_id = ?'), (evaluator_id,))
    deleted_count = cursor.rowcount
    
    commit_db(conn)
    conn.close()
    
    flash(f'평가자 {evaluator_id}의 평가 데이터 {deleted_count}건이 초기화되었습니다.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/reset_performance/<employee_id>')
def reset_performance(employee_id):
    """특정 피평가자의 실적 데이터 초기화 (관리자만 가능)"""
    if 'user_type' not in session or session['user_type'] != "관리자(인사담당자)":
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 특정 피평가자의 실적 데이터 삭제
    cursor.execute(adapt_query('DELETE FROM performance_data WHERE employee_id = ?'), (employee_id,))
    deleted_count = cursor.rowcount
    
    commit_db(conn)
    conn.close()
    
    flash(f'피평가자 {employee_id}의 실적 데이터 {deleted_count}건이 초기화되었습니다.', 'success')
    return redirect(url_for('dashboard'))

# Railway 배포를 위한 헬스체크 엔드포인트 추가
@app.route('/health')
def health_check():
    """Railway 헬스체크용 엔드포인트"""
    return 'OK', 200

# 간단한 진단용 엔드포인트: 배포 환경에서 backdata 내용 확인
@app.route('/debug/backdata_find')
def debug_backdata_find():
    """Query param q 로 전달된 문자열이 backdata 이름 열에 존재하는지 확인"""
    query = request.args.get('q', '').strip()
    try:
        df = load_backdata()
        if df.empty or not query:
            return jsonify({
                'success': True,
                'query': query,
                'total_rows': int(getattr(df, 'shape', (0, 0))[0]),
                'matches': 0
            })
        name_series = df.iloc[:, 2].astype(str)
        matches = int(name_series.str.contains(query, na=False).sum())
        return jsonify({
            'success': True,
            'query': query,
            'total_rows': int(df.shape[0]),
            'matches': matches
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'query': query})

@app.route('/debug/backdata_row/<employee_id>')
def debug_backdata_row(employee_id):
    """지정한 사번의 backdata 행을 반환"""
    try:
        df = load_backdata()
        if df.empty:
            return jsonify({'success': True, 'found': False, 'reason': 'empty'}), 200
        # 첫 번째 컬럼이 사번
        subset = df[df.iloc[:, 0].astype(str) == str(employee_id)]
        if subset.empty:
            return jsonify({'success': True, 'found': False}), 200
        row = subset.iloc[0]
        return jsonify({
            'success': True,
            'found': True,
            'employee_id': str(row.iloc[0]),
            'password': str(row.iloc[1]),
            'name': str(row.iloc[2]),
            'team': str(row.iloc[3]),
            'position': str(row.iloc[4]),
            'grade': str(row.iloc[5]),
            'raw': [str(x) for x in row.tolist()]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'employee_id': employee_id})

# 조직도 관리 라우트
@app.route('/organization')
def organization():
    """조직도 관리 페이지"""
    if 'user_type' not in session:
        return redirect(url_for('login'))
    
    safe_init_db()
    return render_template('organization.html')

@app.route('/api/organization/departments', methods=['GET'])
def get_departments():
    """조직 목록 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(adapt_query('''
            SELECT id, name, leader_position, parent_id, display_order
            FROM departments
            ORDER BY display_order, name
        '''))
        
        departments = []
        for row in cursor.fetchall():
            departments.append({
                'id': row[0],
                'name': row[1],
                'leader_position': row[2],
                'parent_id': row[3],
                'display_order': row[4]
            })
        
        conn.close()
        return jsonify({'success': True, 'departments': departments})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/organization/departments', methods=['POST'])
def create_department():
    """조직 생성"""
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(adapt_query('''
            INSERT INTO departments (name, leader_position, parent_id, display_order)
            VALUES (?, ?, ?, ?)
        '''), (
            data.get('name'),
            data.get('leader_position'),
            data.get('parent_id'),
            data.get('display_order', 0)
        ))
        
        commit_db(conn)
        if is_postgresql():
            cursor.execute('SELECT LASTVAL()')
            department_id = cursor.fetchone()[0]
        else:
            department_id = cursor.lastrowid
        conn.close()
        
        return jsonify({'success': True, 'id': department_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/organization/departments/<int:dept_id>', methods=['PUT'])
def update_department(dept_id):
    """조직 수정"""
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(adapt_query('''
            UPDATE departments
            SET name = ?, leader_position = ?, parent_id = ?, display_order = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        '''), (
            data.get('name'),
            data.get('leader_position'),
            data.get('parent_id'),
            data.get('display_order', 0),
            dept_id
        ))
        
        commit_db(conn)
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/organization/departments/<int:dept_id>', methods=['DELETE'])
def delete_department(dept_id):
    """조직 삭제"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(adapt_query('DELETE FROM departments WHERE id = ?'), (dept_id,))
        
        commit_db(conn)
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/organization/employees', methods=['GET'])
def get_department_employees():
    """조직별 직원 목록 조회"""
    try:
        dept_id = request.args.get('department_id')
        conn = get_db_connection()
        cursor = conn.cursor()
        backdata = load_backdata()
        
        if dept_id:
            cursor.execute(adapt_query('''
                SELECT id, employee_id, position
                FROM department_employees
                WHERE department_id = ?
            '''), (dept_id,))
        else:
            cursor.execute(adapt_query('''
                SELECT id, department_id, employee_id, position
                FROM department_employees
            '''))
        
        employees = []
        for row in cursor.fetchall():
            employee_id = str(row[1]) if dept_id else str(row[2])
            # backdata에서 직원 정보 찾기
            emp_data = backdata[backdata.iloc[:, 0].astype(str) == employee_id]
            if not emp_data.empty:
                emp_info = {
                    'id': row[0],
                    'employee_id': employee_id,
                    'name': str(emp_data.iloc[0, 2]),
                    'team': str(emp_data.iloc[0, 3]),
                    'position': str(emp_data.iloc[0, 4]),
                    'grade': str(emp_data.iloc[0, 5]),
                    'department_position': row[2] if dept_id else row[3]
                }
            else:
                emp_info = {
                    'id': row[0],
                    'employee_id': employee_id,
                    'name': f'사번 {employee_id}',
                    'team': 'Unknown',
                    'position': 'Unknown',
                    'grade': 'Unknown',
                    'department_position': row[2] if dept_id else row[3]
                }
            employees.append(emp_info)
        
        conn.close()
        return jsonify({'success': True, 'employees': employees})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/organization/employees', methods=['POST'])
def assign_employee():
    """직원을 조직에 배정"""
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 기존 배정이 있으면 삭제
        cursor.execute(adapt_query('''
            DELETE FROM department_employees WHERE employee_id = ?
        '''), (data.get('employee_id'),))
        
        # 새로 배정
        cursor.execute(adapt_query('''
            INSERT INTO department_employees (department_id, employee_id, position)
            VALUES (?, ?, ?)
        '''), (
            data.get('department_id'),
            data.get('employee_id'),
            data.get('position')
        ))
        
        commit_db(conn)
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/organization/employees/<int:emp_id>', methods=['DELETE'])
def remove_employee(emp_id):
    """직원을 조직에서 제거"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(adapt_query('DELETE FROM department_employees WHERE id = ?'), (emp_id,))
        
        commit_db(conn)
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/organization/upload', methods=['POST'])
def upload_organization():
    """조직도 CSV 업로드"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '파일이 없습니다.'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '파일이 선택되지 않았습니다.'}), 400
        
        # CSV 파일 읽기
        try:
            df = pd.read_csv(file, encoding='utf-8')
        except:
            file.seek(0)
            df = pd.read_csv(file, encoding='cp949')
        
        # 필수 컬럼 확인 (조직명, 조직장 직급)
        required_cols = ['조직명', '조직장 직급']
        if not all(col in df.columns for col in required_cols):
            return jsonify({'success': False, 'error': f'필수 컬럼이 없습니다: {required_cols}'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 기존 조직 삭제 (선택사항)
        if request.form.get('clear_existing') == 'true':
            cursor.execute('DELETE FROM department_employees')
            cursor.execute('DELETE FROM departments')
        
        # 조직 데이터 삽입
        dept_map = {}  # 조직명 -> ID 매핑
        
        for idx, row in df.iterrows():
            dept_name = str(row['조직명']).strip()
            leader_position = str(row['조직장 직급']).strip() if pd.notna(row.get('조직장 직급')) else None
            parent_name = str(row.get('상위 조직', '')).strip() if pd.notna(row.get('상위 조직')) else None
            
            # 조직이 이미 있으면 스킵
            cursor.execute(adapt_query('SELECT id FROM departments WHERE name = ?'), (dept_name,))
            existing = cursor.fetchone()
            
            if existing:
                dept_id = existing[0]
            else:
                parent_id = dept_map.get(parent_name) if parent_name else None
                cursor.execute(adapt_query('''
                    INSERT INTO departments (name, leader_position, parent_id, display_order)
                    VALUES (?, ?, ?, ?)
                '''), (dept_name, leader_position, parent_id, idx))
                if is_postgresql():
                    cursor.execute('SELECT LASTVAL()')
                    dept_id = cursor.fetchone()[0]
                else:
                    dept_id = cursor.lastrowid
            
            dept_map[dept_name] = dept_id
        
        commit_db(conn)
        conn.close()
        
        return jsonify({'success': True, 'message': f'{len(df)}개의 조직이 등록되었습니다.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/organization/all_employees', methods=['GET'])
def get_all_employees():
    """모든 직원 목록 조회 (조직 배정되지 않은 직원 포함)"""
    try:
        backdata = load_backdata()
        if backdata is None or backdata.empty:
            return jsonify({'success': True, 'employees': []})
        
        # 이미 배정된 직원 ID 조회
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(adapt_query('SELECT DISTINCT employee_id FROM department_employees'))
        assigned_ids = set(str(row[0]) for row in cursor.fetchall())
        conn.close()
        
        employees = []
        for idx, row in backdata.iterrows():
            emp_id = str(row.iloc[0])
            employees.append({
                'id': emp_id,
                'name': str(row.iloc[2]),
                'team': str(row.iloc[3]),
                'position': str(row.iloc[4]),
                'grade': str(row.iloc[5]),
                'assigned': emp_id in assigned_ids
            })
        
        return jsonify({'success': True, 'employees': employees})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # 서버를 먼저 시작하여 헬스체크가 즉시 응답하도록 하고,
    # DB 스키마 준비는 before_first_request 훅에서 수행한다.
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=port)


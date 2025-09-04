import pandas as pd
import numpy as np

# CSV 파일을 여러 인코딩으로 시도하여 읽기
encodings = ['utf-8', 'cp949', 'euc-kr', 'latin1']

for encoding in encodings:
    try:
        df = pd.read_csv('해외주재원 부임 예정자 OJT 담당부서_20250612.csv', encoding=encoding)
        print(f"성공적으로 읽은 인코딩: {encoding}")
        break
    except UnicodeDecodeError:
        continue
else:
    print("모든 인코딩 시도 실패")

# 데이터 확인
print("\n데이터 구조:")
print(df.info())
print("\n처음 5행:")
print(df.head())
print("\n컬럼명:")
print(df.columns.tolist())

import pandas as pd

# 데이터 로드
df = pd.read_csv('basedata.csv', encoding='cp949')

# 이상용 팀장님(11040050)에게 매핑된 피평가자들 확인
evaluator = df[df.iloc[:, 9] == 11040050]

print("이상용 팀장님(11040050)에게 매핑된 피평가자들:")
print(f"총 {len(evaluator)}명")

if not evaluator.empty:
    for idx, row in evaluator.iterrows():
        print(f"- {row.iloc[2]} ({row.iloc[4]}) - {row.iloc[3]} - {row.iloc[7]}")
else:
    print("매핑된 피평가자가 없습니다.")

print("\n직급별 분포:")
if not evaluator.empty:
    print(evaluator.iloc[:, 4].value_counts())

print("\n직책별 분포:")
if not evaluator.empty:
    print(evaluator.iloc[:, 7].value_counts()) 
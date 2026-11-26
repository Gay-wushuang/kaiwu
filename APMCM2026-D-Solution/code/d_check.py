# -*- coding: utf-8 -*-
import pandas as pd, os, numpy as np
d = r"D:\比赛\APMCM\2026 APMCM Problems B&C&D\D题 中文翻译\date"
f02 = pd.read_csv(os.path.join(d, "02_castelli_train.csv"))
f03 = pd.read_csv(os.path.join(d, "03_castelli_val.csv"))
f04 = pd.read_csv(os.path.join(d, "04_castelli_test_holdout.csv"))
f06 = pd.read_csv(os.path.join(d, "06_castelli_no_physics.csv"))
f07 = pd.read_csv(os.path.join(d, "07_castelli_q2_pool.csv"))
f08 = pd.read_csv(os.path.join(d, "08_castelli_q3_pool.csv"))
f11 = pd.read_csv(os.path.join(d, "11_castelli_q2_pool_blind.csv"))
f12 = pd.read_csv(os.path.join(d, "12_castelli_q3_pool_blind.csv"))

print("列（02）:", list(f02.columns))
print("列（07 池）:", list(f07.columns))
print()
for name, df in [("02", f02), ("03", f03), ("04", f04), ("06", f06), ("07", f07), ("08", f08), ("11", f11), ("12", f12)]:
    pos = int((df["V"] == 0).sum()) if "V" in df.columns else "无 V 列"
    print(f"{name}: {len(df)} 行 | 正例 {pos}")
print()
print("02∪03 正例:", int(((f02["V"] == 0).sum() + (f03["V"] == 0).sum())))
print("V 分布(02): min %.2f 中位 %.2f max %.2f" % (f02.V.min(), f02.V.median(), f02.V.max()))
print("V<0.5 / <1 / <2 / <5 条数:", int((f02.V < .5).sum()), int((f02.V < 1).sum()), int((f02.V < 2).sum()), int((f02.V < 5).sum()))
print()
# 池子的自由度结构
print("07 池: X 唯一值", sorted(f07.X.unique()), "| A 唯一", f07.A.nunique(), "| B 唯一", f07.B.nunique(), "| (A,B) 唯一", f07[["A","B"]].drop_duplicates().shape[0])
print("08 池: X 唯一值", sorted(f08.X.unique()), "| (A,B,X) 唯一", f08[["A","B","X"]].drop_duplicates().shape[0])
print("11 池: X", sorted(f11.X.unique()), "| 11 ⊆ 04 ?", set(f11.id) <= set(f04.id))
print("12 池: 12 ⊆ 04 ?", set(f12.id) <= set(f04.id))
print()
print("07 里 (A,B) 与 11 的关系: 11 是 07∩04 的子集?", set(f11.id) <= set(f07.id))
print()
# 元素集合
elems = sorted(set(f02.A) | set(f02.B))
print(f"元素池 {len(elems)} 种:", " ".join(elems))
print("X 族 7 类:", sorted(f02.X.unique()))
print()
# a_eq_b 与正例
print("a_eq_b=1 行数:", int((f02.a_eq_b == 1).sum() + (f03.a_eq_b == 1).sum()), "| 其中 V=0:", int(((f02.a_eq_b == 1) & (f02.V == 0)).sum() + ((f03.a_eq_b == 1) & (f03.V == 0)).sum()))
# 六列里没有 a_lat/volume（池子）
print("池子可用特征列:", [c for c in f07.columns if c not in ("id",)])

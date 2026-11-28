# T002-A 教学验证

对 Codex 数学备忘录中的手算例与关键命题做独立复算，不使用赛题数据。

- 脚本：`validate_examples.py`
- 结果：`validation_results.json`（33 PASS / 0 FAIL）
- 日志：`validation.log`
- 运行命令：
  `%LOCALAPPDATA%\kaiwu-verify\Scripts\python.exe results/round2/qubo_refinement/TEACHING_VALIDATION/validate_examples.py`

覆盖内容：
1. 罚项阈值 `T(a)=3`、`T(b)=5`，以及 M=3/4/5 的并列/唯一最优/非法胜出。
2. one-hot、domain-wall、binary 三种编码的合法成本、最低非法能量（8/8/11+z）。
3. 量化例子的 α=0.5/1/1.25/2 整数系数与严格翻转/并列/保持，及分界 5/8、50/49。
4. “合法域等价但全空间基态改变”的仿射反例。
5. domain-wall 到 one-hot 的 `e_r=t_r−t_{r+1}` 映射。

注意：教学数字只证明通用数学机制，不是赛题结论；正式使用需队员确定配置后重新验证。

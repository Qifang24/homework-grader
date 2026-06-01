# 准确率评测（Accuracy Evaluation）

用一组**人工已知答案**的样本，量化批改器到底准不准。这是回答评委
"AI 批错了怎么办、它准不准"的核心证据。

## 指标

| 指标 | 含义 | 方向 |
| --- | --- | --- |
| 分数 MAE | 预测分与人工分的平均绝对误差 | 越小越好 |
| 等级一致率 | 预测等级（优秀/良好/合格/待改进）与人工一致的比例 | 越高越好 |
| 逐题判对一致率（数学） | 按题号对齐后，对/错判断一致的比例 | 越高越好 |

评测使用与线上**完全相同**的图片预处理（`grader/image_utils.py`），保证结果可信。

## 使用步骤

1. 准备样本图片，放进 `eval/gold/images/`。
2. 复制 `eval/gold/labels.example.json` 为 `eval/gold/labels.json`，
   按真实情况填写每张图的人工评分：
   - 所有学科：`file`、`subject`、`score`、`grade`
   - 数学额外填 `problems`：按题目顺序写每题是否 `correct`
3. 配好 `ZHIPUAI_API_KEY`（`.env` 或环境变量），运行：

   ```bash
   python -m eval.run_eval
   ```

4. 结果写入 `eval/report.json` 和 `eval/report.md`；
   app 侧边栏会自动读取 `report.json` 显示准确率看板。

## 建议

- 样本量先做到 20-50 张，覆盖不同难度和字迹清晰度。
- 人工修正（app 里的"人工复核")的数据可以反哺这里，持续扩充样本集。
- 答辩时直接展示 `report.md` 的指标表，并坦诚说明失败源（如潦草字迹）。

> `labels.json`、`images/`、`report.*` 都已在 `.gitignore` 忽略，避免学生作业数据入库。

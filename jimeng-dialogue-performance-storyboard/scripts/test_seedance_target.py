import unittest
from pathlib import Path

from validate_storyboard import seedance_pair_issues


BASE = '''## 全局锁定
## 制作质量总控
## 通用负面提示词｜直接复制
#### S1-01｜镜头组总时长：2s
【镜号】
1，2s，普通。
【画面描述｜直接复制】
16:9，写实，窗光从左侧落脸，背光侧保留阴影；A说：“你好”。
'''


class SeedancePairTests(unittest.TestCase):
    def test_pair_contract_keeps_shots_and_dialogue_aligned(self):
        items = [
            (Path("scene_Seedance2.0.md"), "## 使用说明\n- Seedance 目标：2.0\n" + BASE),
            (Path("scene_Seedance2.5.md"), "## 使用说明\n- Seedance 目标：2.5\n" + BASE.replace("背光侧保留阴影", "中深明暗层次，背光侧保留细节")),
        ]
        self.assertEqual(seedance_pair_issues(items), [])

    def test_pair_rejects_dialogue_drift(self):
        items = [
            (Path("scene_Seedance2.0.md"), "## 使用说明\n- Seedance 目标：2.0\n" + BASE),
            (Path("scene_Seedance2.5.md"), "## 使用说明\n- Seedance 目标：2.5\n" + BASE.replace("你好", "再见")),
        ]
        self.assertTrue(any("dialogue" in issue for issue in seedance_pair_issues(items)))


if __name__ == "__main__":
    unittest.main()

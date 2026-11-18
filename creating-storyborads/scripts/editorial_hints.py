"""Non-blocking editorial hints; repetition is not proof of an error."""
import re

def editorial_hints(text):
    hints = []
    for phrase in ('依据当前对象与动作', '按本镜具体话语行动', '语义转折处换气、末句明确指向受话者'):
        lines = [i for i, line in enumerate(text.splitlines(), 1) if phrase in line]
        if len(lines) >= 3:
            hints.append(f'对白指导可能套用工作要求：{phrase}（行{lines[:8]}）；请核对实际逐句读法，不自动判错。')
    titles = [(i, line) for i, line in enumerate(text.splitlines(), 1) if re.match(r'^###\s+生成单元', line)]
    vague = [i for i, line in titles if line.rstrip().endswith('关系推进')]
    if len(vague) >= 3:
        hints.append(f'单元标题可能空泛重复（行{vague[:8]}）；核对是否概括各段实际事件，连续主题允许重复。')
    return hints

#!/usr/bin/env python3
"""Structural and generation-risk validator for storyboard outputs."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


QUALITY_CONTROL_FIELD = "【本镜制作控制】"
CHILD_FIELDS = ["【镜号】", "【画面描述｜直接复制】", "【表演与声音】", "【状态继承】", QUALITY_CONTROL_FIELD]
KEYFRAME_IMAGE_FIELD = "【关键帧生图提示】"
KEYFRAME_VIDEO_FIELD = "【即梦视频提示｜配合关键帧】"
DIRECT_NEXT_FIELDS = (KEYFRAME_IMAGE_FIELD, KEYFRAME_VIDEO_FIELD, "【表演与声音】")
REQUIRED_TOP_SECTIONS = [
    "## 使用说明",
    "## 全局锁定",
    "## 制作质量总控",
    "## 通用负面提示词｜直接复制",
    "## 场景状态表",
    "## 分镜投喂卡",
]
GLOBAL_QUALITY_LABELS = (
    "画面质感基线", "光效与曝光连续", "动态美学基线",
    "表演与情绪基线", "蒙太奇与剪辑基线", "穿帮与抽卡总控",
)
SHOT_QUALITY_LABELS = (
    "画面质感", "光效与曝光", "动态美学", "表演与情绪",
    "穿帮控制", "抽卡策略", "蒙太奇与剪辑",
)
BANNED_DIRECT = [
    "继承", "延续上一镜", "上一镜", "尾帧", "接上一镜", "空间保持", "位置继承", "物理座位不变", "剪辑", "切到", "反打到",
    "下一镜执行", "声音语气：", "表情：", "动作：", "情绪：", "脑海浮现", "后期插入", "左外",
    "当前主角", "当前对话者", "视情况", "出场人物", "所有人物", "全部人物", "所有出场人物",
]
GLOBAL_SCALE_LOCK_TITLE = "全局比例与支撑锁定"
GLOBAL_SCALE_LOCK_TERMS = (
    "角色骨骼与头身比例恒定", "真实身高和体型尺寸固定", "四肢长度与关节比例稳定",
    "地平线及消失关系稳定", "身体主支撑点持续贴合当前承载面", "站立时双脚接地",
    "行走时步态交替接地", "坐卧时臀背或躯干贴合承载面", "腾空时保持起跳、空中与落地轨迹连续", "两人身高差",
    "画面投影只随物理距离连续变化", "固定距离下画面占比保持稳定",
)
GLOBAL_SCALE_NEGATIVE_TERMS = (
    "人物忽高忽低", "体型动态变化", "腿部拉长缩短", "无因尺度跳变", "无因浮空",
    "透视错乱", "穿模", "肢体畸形", "广角畸变",
)
LIVENESS_PATTERN_FAMILIES = {
    "camera_push": (
        r"(?:镜头|摄影机|机位)[^。；;\n]{0,12}(?:缓慢推近|慢慢推近|轻推|小幅推进|逐渐靠近)",
        r"(?:缓慢推近|慢慢推近|小幅推进)(?:镜头|摄影机|机位)",
    ),
    "generic_eye": (r"轻微眨眼", r"缓慢眨眼", r"眼睫轻颤", r"眼皮微动"),
    "generic_brow": (r"微微皱眉", r"轻蹙眉", r"眉心微收"),
    "idle_fabric": (r"衣摆轻动", r"衣袖轻摆", r"衣角轻晃", r"窗帘轻摆", r"帘布轻晃"),
    "generic_haze": (r"薄雾", r"轻雾", r"雾气缓慢流动", r"丁达尔光", r"无因体积光"),
}
INTERNAL_PRESET_TERMS = ("套用模板", "预设库", "候选池", "场景预设", "预设分支", "参数化场景")
COLOR_CARD_TITLE = "本集影调色卡索引"
VOICE_LOCK_TITLE = "本集角色声音锁定表"
COLOR_CARD_REQUIRED_TERMS = (
    "剧情情绪功能", "主色", "辅助色", "点缀色", "色温", "主光", "阴影",
    "对比度", "饱和度", "肤色保护", "材质反光", "禁止偏色",
)
VOICE_LOCK_REQUIRED_TERMS = (
    "声音年龄感", "音色", "音调", "语速", "音量", "吐字", "呼吸", "尾音", "情绪上限", "禁止变化",
)
ASPECT_TERMS = ("16:9", "9:16", "1:1", "4:3", "21:9", "画幅")
STYLE_TERMS = ("3D", "韩漫", "CG", "漫画", "动画", "写实", "视觉风格")
SCENE_TONE_PREFIX_TERMS = (
    "主色", "影调", "色温", "顶光", "侧光", "逆光", "窗光", "暖光", "冷光",
    "冷白", "暖黄", "蓝灰", "暖米", "奶油", "低饱和", "阴影", "肤色",
)
CUTAWAY_EXPLICIT_TERMS = ("镜头不拍人物", "空镜")
CUTAWAY_SUBJECT_TERMS = ("空椅", "门缝", "水纹", "走廊灯光")
SHOT_SIZE_TERMS = ("特写", "近景", "中近景", "中景", "中远景", "全景", "远景")
CAMERA_TERMS = ("镜头", "相机", "机位", "平视", "俯视", "仰视", "侧后方", "斜前方")
CAMERA_SIGNATURE_ANGLE_TERMS = (
    "斜俯", "侧俯", "俯视", "仰视", "低机位", "高机位", "平视", "侧面", "侧后方", "斜前方",
)
COMPOSITION_FAMILY_TERMS = (
    ("前景框景", ("框景", "门框", "窗框", "肩后前景")),
    ("三角关系", ("三角构图", "三人三角")),
    ("斜线纵深", ("斜线构图", "纵深构图", "消失线")),
    ("中央空位", ("中心留白", "中央留白", "空位留白")),
    ("横向揭示", ("横向构图", "横移揭示")),
    ("低机位压力", ("低角度压力", "低机位")),
    ("高机位压力", ("高角度压力", "高机位", "俯视压力")),
    ("拉远留白", ("孤独留白", "拉远孤独")),
    ("门窗分割", ("窗格分割", "门缝构图")),
)
TERMINAL_STABILITY_TERMS = ("最后20%", "最后 20%", "终态", "落幅", "停稳", "保持到结束")
TERMINAL_ANTI_DUPLICATE_TERMS = ("不新增人物", "不新增主体", "不产生重复人物", "不产生重复主体", "不重复主体")
TERMINAL_SEPARATION_TERMS = ("边界分开", "边界清晰", "脸和手分开", "手脚分开", "肢体分开", "不互相遮挡", "不重叠")
SLOT_TERMS = ("左侧", "右侧", "中间", "前景", "中景", "后景", "槽位", "站位")
RELATION_TERMS = ("面对", "相对", "身侧", "身后", "前方", "后方", "之间", "隔着", "挽着", "肩线", "右手", "左手", "朝向", "背对", "侧身")
FACING_TERMS = ("面向", "背向", "身体朝向", "身体仍朝", "上身朝向", "头部转向", "头部偏向")
VISUAL_TARGET_VERBS = ("面向", "看向", "朝向", "对着", "望向", "盯着", "凝视", "锁住")
OFFSCREEN_MARKERS = ("不入画", "不出镜", "画外", "不出现身体", "不出现肩线", "不出现倒影", "不出现虚化人影")
VISIBLE_COUNT_RE = re.compile(r"(?:本镜)?(?:画面内|视线内|镜头内)?可见人数[：:]\s*[一二三四五六七八九十\d]+人|入画人数[：:]\s*[一二三四五六七八九十\d]+人")
POST_AUDIO_TERMS = ("OS", "OV", "系统音", "内心独白", "画外", "后期", "配音", "旁白")
POST_AUDIO_LABEL_TERMS = ("OS", "OV", "系统音", "内心独白", "旁白")
VISIBLE_SPEECH_TERMS = ("可见口型", "可见说话者", "开口", "说：", "说:", "说“", "问：", "问:", "喊：", "喊:", "低语", "回应", "反问")
BLAND_EXPRESSION_TERMS = ("眼神复杂", "神色复杂", "表情平淡", "神色变化", "微微皱眉", "闭口看着")
FACIAL_DETAIL_TERMS = ("眼睑", "睫毛", "眉尾", "嘴角", "下颌", "喉咙", "呼吸", "唇", "屏息")
BODY_PROP_EMOTION_TERMS = ("肩", "背", "手", "指", "道具", "手机", "卡", "衣", "后退", "靠近", "距离", "遮挡", "门", "桌")
PROP_TRANSFER_TERMS = ("递", "交给", "接过", "接住", "松手", "刷卡", "签字", "付款", "取出", "拿出", "塞给")
CONTACT_TERMS = ("握住", "抓住", "拽住", "牵住", "拉住", "按住", "扶住", "扣住")
MOVE_TERMS = ("走到", "走近", "上前", "后退", "转身", "离开", "入场", "进门", "出门", "坐下", "站起")
PROP_CONTINUITY_TERMS = ("右手", "左手", "手中", "掌中", "桌面", "台面", "包内", "口袋", "外袋", "胸前", "腰侧", "松手", "接触", "握住")
REVERSE_SHOT_RE = re.compile(
    r"(?:机位|摄影机|相机|镜头)(?:位于|设在|在|从)\s*([^，。；;\n]{1,12})肩后"
)
ORIENTATION_LOCK_TERMS = ("背向", "背对", "侧身", "身体面向柜台", "身体面向入口", "身体面向出口", "身体面向道路", "身体面向门口", "身体面向车门", "身体面向手机", "身体面向屏幕", "身体面向签字台", "身体面向缴费台")
ORIENTATION_TURN_TERMS = ("转身", "转向", "回身", "侧身转正", "肩线转正", "双脚停稳", "身体从")
TRACKED_PROPS = ("手机", "银行卡", "卡片", "卡", "杯子", "茶盏", "瓷盏", "笔", "签字笔", "文件", "外套", "手包", "包", "钥匙", "餐盘", "照片", "纸")
PROP_STATE_HINTS = ("右手", "左手", "手中", "掌中", "包内", "口袋", "外袋", "胸前", "腰侧", "桌面", "台面", "签字台", "柜台", "手边")
STRONG_PROP_STATE_HINTS = ("右手", "左手", "包内", "口袋", "外袋", "胸前", "腰侧", "桌面", "台面", "签字台", "柜台", "掌中", "手中")
PROP_TRANSFER_CHAIN_TERMS = ("取出", "拿出", "拿起", "递", "递到", "交给", "接触", "接过", "接住", "握住", "松手", "放下", "放到", "移动")
ACTION_CHAIN_TERMS = (
    "转身", "转向", "回身", "走到", "走近", "上前", "后退", "取出", "拿出", "拿起",
    "抬", "递", "递到", "接触", "握住", "接过", "接住", "松手", "放下", "放到",
    "离开", "坐下", "站起", "伸", "按下", "挂断",
)
POSTURE_RISK_TERMS = (
    "躺", "伏", "趴", "靠在", "靠到", "抱住", "搂住", "扶住", "拉住", "拽住",
    "摔倒", "倒向", "倒到", "翻身", "坐起", "起身", "蹲下", "跪下", "弯腰",
    "前倾", "抱起", "背起", "腿上", "怀里", "坐在", "坐着", "靠着",
)
POSTURE_STRUCTURE_TERMS = (
    "头", "脸", "肩", "背", "腰", "臀", "腿", "膝", "脚", "手撑", "撑住",
    "座垫", "坐垫", "座椅", "椅背", "吊椅", "沙发", "床", "地面", "支撑", "接触点", "贴", "枕",
    "压", "蜷", "非接触", "没有跨坐", "没有缠绕",
)
SUPPORT_SURFACE_TERMS = (
    "吊椅", "座椅", "椅子", "椅面", "椅背", "座垫", "坐垫", "靠背", "扶手",
    "沙发", "床", "车座", "后排", "座位",
)
SUPPORT_BODY_TERMS = ("臀", "腰", "腰臀", "肩背", "背部", "腿", "膝", "脚", "头", "手")
SUPPORT_CONTACT_TERMS = ("压在", "靠住", "贴住", "贴着", "抵住", "枕在", "搭在", "蜷在", "支撑", "接触")
SUPPORT_CHANGE_TERMS = (
    "挪", "移动", "调整", "滑", "蹭", "手撑", "撑住", "脚踩", "脚落地", "重心",
    "离开", "抬起", "坐起", "起身", "转身", "重新贴住", "重新靠住",
)
GENERIC_SUPPORT_RE = re.compile(r"(?:坐在|躺在|靠在)[^，。；;\n]{0,14}(?:中间|中央|正中|中心)|坐姿|坐着|靠着|躺着")
GARMENT_RISK_TERMS = ("披", "穿上", "脱下", "外套滑落", "衣摆")
GARMENT_STRUCTURE_TERMS = ("领口", "袖", "肩", "臂弯", "衣摆", "双臂", "哪只手", "左手", "右手", "垂")
DOOR_RISK_TERMS = ("开门", "关门", "推门", "拉门", "开车门", "关车门", "下车", "上车", "门把", "把手")
DOOR_STRUCTURE_TERMS = ("把手", "门边", "打开", "关闭", "半掩", "车外", "车内", "路沿", "门槛", "踏", "站在")
UI_RISK_TERMS = ("来电", "转账", "聊天记录", "付款码", "屏幕显示", "清晰文字", "文字")
UI_STRUCTURE_TERMS = ("后期叠字", "安全区", "模糊", "不生成清晰文字", "斜向", "正对", "屏幕")
SCREEN_INVISIBLE_TERMS = (
    "手机背面朝向镜头", "屏幕完全不可见", "屏幕不可见", "屏幕朝向持机者本人",
    "屏幕朝向人物本人", "屏幕朝向A本人", "屏幕朝向B本人", "屏幕朝向她本人", "屏幕朝向他本人",
)
SCREEN_UI_CONTENT_TERMS = ("屏幕显示", "模糊微信聊天界面", "微信聊天界面", "聊天界面", "屏幕文字", "屏幕光照出文字", "屏幕光照出")
AI_SIDE_BUBBLE_TERMS = ("绿色微信消息气泡", "绿色聊天气泡", "消息气泡", "字幕浮层", "气泡浮层", "二维绿色")
SIDE_OVERLAY_REQUIRED_TERMS = ("二维", "悬浮", "浮层", "安全区", "不属于手机", "不贴", "不跟随手机")
SIDE_OVERLAY_NECESSARY_TERMS = ("不属于手机", "不贴")
SIDE_OVERLAY_NEGATIVE_TERMS = ("聊天气泡贴手机", "文字贴手机壳", "手机背面文字", "UI错位")
CROWD_RISK_TERMS = ("人群", "围观", "混混", "路人", "宾客", "群众")
CROWD_STRUCTURE_TERMS = ("后方", "背景", "虚化", "不靠近", "不抢焦", "不产生可见口型", "远处")
KEYFRAME_POSTURE_CHANGE_TERMS = ("翻身", "坐起", "起身", "摔倒", "倒向", "倒到", "扶住", "抱住", "搂住", "抱起", "背起", "亲密接触")
KEYFRAME_PROP_TERMS = ("银行卡", "卡片", "手机", "签字笔", "外套", "包", "杯子", "证件")
KEYFRAME_PROP_ACTION_TERMS = ("递", "递到", "交给", "接过", "接住", "塞给", "签字", "刷卡", "付款", "披", "穿上", "收起")
KEYFRAME_UI_TERMS = ("绿色微信消息气泡", "绿色聊天气泡", "消息气泡", "来电", "转账", "聊天记录", "付款码", "屏幕显示")
KEYFRAME_SPACE_TERMS = ("开门", "关门", "推门", "拉门", "开车门", "关车门", "下车", "上车", "电梯门")
KEYFRAME_CAMERA_TERMS = (
    "环绕", "半弧环绕", "半弧移动", "希区柯克变焦", "多莉变焦",
    "闯入式镜头", "冲入画面", "时间断裂",
    "快速推", "快速拉", "快速横移", "手持抖动", "强运镜",
)
NEGATION_CUES_BEFORE = (
    "不要", "不要出现", "不要戴", "不要带", "不要穿", "不能有", "不应有", "不出现", "不戴", "不带", "不穿", "不是", "不在",
    "禁止", "避免", "去掉", "去除", "移除", "排除", "没有", "无", "非",
)
NEGATION_CUES_AFTER = ("不要出现", "不能出现", "不应出现", "不出现", "去掉", "去除", "移除", "排除", "不存在")
NEGATIVE_PRIMING_GROUPS = (
    (
        "医疗职业/场景",
        ("护士帽", "护士服", "病号服", "白大褂", "手术服", "听诊器", "医院", "病房", "诊室", "手术室"),
        "改写目标发型、实际服装和目标地点固定锚点",
    ),
    (
        "警务/军事职业与场景",
        ("警帽", "警服", "警徽", "警局", "军帽", "军装", "迷彩服", "肩章", "战场"),
        "改写人物真实身份、日常服装和目标场景",
    ),
    (
        "学校/未成年人场景",
        ("校服", "红领巾", "教室", "校园"),
        "改写人物年龄、实际服装和目标地点",
    ),
    (
        "婚礼/宗教场景",
        ("婚纱", "头纱", "婚礼", "教堂", "僧袍", "道袍"),
        "改写实际服装、发型和目标场景锚点",
    ),
    (
        "司法/拘押场景",
        ("囚服", "监狱", "法庭"),
        "改写实际服装、人物关系和目标地点",
    ),
)
PHONE_OPERATION_TERMS = (
    "玩手机游戏", "玩手机", "玩手游", "打手游", "刷手机", "看手机", "浏览手机", "浏览消息",
    "手机打字", "用手机打字", "手机上打字", "操作手机", "双手横持手机", "单手竖持手机",
    "拇指点击手机", "拇指滑动手机",
)
PHONE_EXPLICIT_DISPLAY_TERMS = (
    "观众需要看清", "观众必须看清", "给观众看", "向镜头展示手机屏幕", "展示手机屏幕",
    "手机屏幕特写", "屏幕内容展示镜",
)
PHONE_SCREEN_TO_CAMERA_TERMS = (
    "屏幕正对镜头", "屏幕朝向镜头", "屏幕面向镜头", "屏幕正对观众", "屏幕朝向观众", "屏幕面向观众",
)
PHONE_CAMERA_BACK_TERMS = (
    "手机背面朝向镜头", "手机背面和斜侧边缘朝向镜头", "手机背面与斜侧边缘朝向镜头",
    "镜头只见手机背面", "镜头仅见手机背面", "镜头只看见手机背面", "手机斜侧边缘朝向镜头",
    "镜头只见手机侧边", "镜头仅见手机侧边",
)
PHONE_GAME_INTERFACE_TERMS = (
    "游戏界面", "游戏角色", "游戏按钮", "HUD", "按钮", "技能栏", "血条", "小地图", "可读游戏文字",
)
VISIBLE_SKIN_TERMS = ("脸", "脸部", "脸颊", "嘴", "眼", "下颌", "肤色", "皮肤", "双手", "手部")
COLORED_ENVIRONMENT_TERMS = (
    "蓝灰", "灰蓝", "冷蓝", "深蓝", "暗蓝", "冷青", "暗绿", "墨绿", "青绿", "紫灰", "淡紫灰",
    "暗红", "深红", "红棕", "黑棕", "暖棕", "冷棕", "暗金", "暖金", "霓虹", "彩色环境光",
)
VOLUMETRIC_LIGHT_TERMS = ("丁达尔", "体积光", "光束", "光柱", "薄雾", "雾气", "尘埃", "浮尘", "烟雾")
POSITIVE_SKIN_TONE_TERMS = (
    "自然肤色", "中性肤色", "自然偏暖肤色", "偏暖肤色", "自然血色", "肤色均匀", "脸部保暖",
    "肤色微暖", "肤色清透", "肤色自然均匀", "肤色保持自然", "人物脸部保持中性", "脸部主光保持中性",
)
SKIN_LIGHTING_TERMS = (
    "脸部受光均匀", "脸部柔和", "柔光落在脸", "窗光落在脸", "主光落在脸", "脸侧受光",
    "鼻侧", "眼窝", "下颌", "浅阴影", "脸部暗部保留细节",
)
NEGATIVE_ONLY_SKIN_TERMS = ("不发青", "不发灰", "不惨白", "不污染脸", "不被环境色污染", "不过曝")
VOLUMETRIC_PROTECTION_TERMS = (
    "脸部与活动手保持清晰", "脸部和活动手保持清晰", "脸、嘴和活动手保持清晰", "脸部保持清晰",
    "光束落到后景", "光束落在后景", "光束落到背景", "光束落在背景", "光束落到地面", "光束落在地面",
)
PERSON_NEAR_DEPTH_TERMS = ("前景", "近处", "镜头近端", "纵深近端")
PERSON_FAR_DEPTH_TERMS = ("后景", "远处", "镜头远端", "纵深远端")
GROUND_PERSPECTIVE_TERMS = (
    "同一地面", "同一木地板", "同一石板路", "同一走廊地面", "同一连续地面",
    "脚底落在", "双脚落在", "地面纵深线", "地板纵深线", "纵深线向后收束",
    "消失点", "连续承载空间", "同一承载空间", "同一空间透视",
)
NEAR_PROJECTION_TERMS = (
    "近处人物投影略大", "近处人物投影较大", "近处画面投影略大", "近处画面投影较大",
    "画面投影略大", "画面投影较大", "画面占比略大", "画面占比较大",
)
FAR_PROJECTION_TERMS = (
    "远处人物投影较小", "远处人物投影略小", "远处画面投影较小", "远处画面投影略小",
    "画面投影较小", "画面投影略小", "画面占比较小", "画面占比略小",
)
BODY_SCALE_LOCK_TERMS = (
    "头身比例稳定", "头身比保持稳定", "骨架比例稳定", "骨架保持稳定",
    "真实身高关系保持", "真实身高关系稳定", "真实身高和体型保持", "真实体型保持",
)
TOWARD_CAMERA_TERMS = ("走向镜头", "朝镜头走", "走近镜头", "靠近镜头", "向镜头靠近")
AWAY_FROM_CAMERA_TERMS = ("远离镜头", "背向镜头走远", "向画面深处走", "沿纵深走远")
CONTINUOUS_GROWTH_TERMS = ("画面占比连续增大", "投影尺度连续增大", "画面投影连续增大")
CONTINUOUS_SHRINK_TERMS = ("画面占比连续减小", "投影尺度连续减小", "画面投影连续减小")
SHOT_TYPE_GUIDANCE = {
    "dialogue_performance": ("对白表演", 200, 320),
    "multi_character_relationship": ("多人关系", 200, 340),
    "silent_causal": ("无台词视觉因果", 140, 320),
    "cutaway_insert": ("空镜/物件插入", 90, 220),
    "montage_fragment": ("蒙太奇片段", 120, 260),
    "non_combat_action": ("非战斗行动", 200, 340),
    "high_risk_transition": ("高风险状态转换", 220, 500),
    "unclassified": ("未分类剧情镜头", 200, 320),
}
SCENE_ANCHOR_TERMS = (
    "客厅", "卧室", "厨房", "餐厅", "办公室", "警局", "医院", "教室", "走廊", "街道", "商业街",
    "溪边", "河边", "院子", "庭院", "门口", "窗边", "柜台", "工作台", "桌面", "地面", "墙面",
    "店招", "橱窗", "公告栏", "门框", "窗框", "石板路", "木地板", "床边", "沙发", "车内",
)
LIGHTING_MATERIAL_TERMS = (
    "光", "受光", "反光", "高光", "阴影", "虚化", "景深", "木纹", "石纹", "金属", "玻璃", "布料",
    "棉麻", "皮革", "水面", "湿润", "粗糙", "磨损", "颗粒", "纹理", "质感",
)
MOTIVATED_LIGHT_SOURCE_TERMS = (
    "窗光", "顶光", "台灯", "灯光", "日光", "自然光", "壁灯", "路灯", "灯牌", "吊灯", "落地灯",
    "屏幕光", "车灯", "店招", "天光", "月光", "烛火", "火光", "火盆", "门外光",
)
VISUAL_RESULT_TERMS = (
    "落在", "照在", "照亮", "扫过", "擦过", "映在", "投在", "进入", "勾亮", "压暗", "压在",
    "受光", "反光", "高光", "阴影", "明暗", "纹理", "褶皱", "磨损", "虚化", "衰减",
)
END_STATE_TERMS = (
    "画面停在", "画面定格", "镜头停在", "镜头定格", "最后停在", "最终停在", "结束时",
    "稳定停在", "稳定在", "落定", "保持到画面结束", "停住不动", "仍停在", "仍保持",
    "说完闭口", "目光停在", "手落回", "肩背保持", "仍隔桌", "照片平放",
    "手机高度和朝向保持稳定", "手机高度与朝向保持稳定", "手机高度、朝向稳定",
)
HELD_STATE_TERMS = (
    "保持", "仍然", "仍在", "仍停", "静止", "停住", "维持", "没有移动", "不再移动", "持续看",
)
MONTAGE_TERMS = (
    "蒙太奇", "时间流逝", "连续数日", "数日后", "一天天", "一天又一天",
    "清晨到夜晚", "晨昏变化", "四季变化", "日夜交替", "同一工作台",
)
TIME_CHANGE_TERMS = (
    "清晨", "上午", "午后", "傍晚", "夜晚", "天亮", "天黑", "日落", "数小时后", "次日", "几天后",
    "光线变化", "日夜", "时间流逝", "钟表", "日历",
)
STATE_INCREMENT_TERMS = (
    "逐渐", "一点点", "新增", "多出", "减少", "完成", "成形", "堆高", "变亮", "变暗", "磨损加深",
    "进度", "半成品", "最终成品", "状态增量",
)
RELATION_CHANGE_TERMS = (
    "靠近", "拉开距离", "后退半步", "并肩", "对峙", "相对", "面对面", "共享", "让开", "挡在",
    "护住", "扶住", "抱住", "挽住", "握住", "松开", "关系定格",
)
SILENT_CAUSE_TERMS = ("发现", "察觉", "听见", "看见", "注意到", "因为", "源头", "漏水", "异响")
ENVIRONMENT_RESPONSE_TERMS = (
    "水流", "水滴", "水面", "灯光", "门", "窗", "风", "影子", "脚步声", "回声", "尘土", "布帘",
    "晃动", "熄灭", "亮起", "停止", "恢复", "溅起", "落下", "散开",
)
ACTION_PURPOSE_TERMS = ("为了", "试图", "寻找", "搜寻", "赶往", "前往", "抵达", "到达", "出口", "目标")
ACTION_ROUTE_TERMS = ("沿", "穿过", "绕过", "经过", "走廊", "道路", "楼梯", "门口", "转角", "路线", "方向")
ACTION_RESULT_TERMS = ("抵达", "到达", "停在", "站到", "进入", "离开", "改道", "返回", "找到", "确认")
COMPOSITION_TERMS = ("构图", "居中", "三分线", "前景", "中景层", "后景", "焦点", "占画面", "留白", "景深")
SOUND_BRIDGE_TERMS = (
    "声音延续", "声桥", "环境声", "脚步声", "水声", "风声", "雨声", "回声", "呼吸声", "门响", "画外声音",
)
PHONE_PURPOSE_TERMS = ("操作型", "展示型", "通知型", "通话型", "玩手机", "刷手机", "打字", "浏览", "来电", "通话", "展示")
LIP_SYNC_TERMS = ("口型", "开口", "说：", "说“", "问：", "问“", "喊：", "喊“", "低语")
MOUTH_CLOSE_TERMS = ("说完闭口", "闭口", "收口", "嘴唇合拢", "口型结束", "停止口型")
LISTENER_REACTION_TERMS = (
    "听者", "另一人", "对方", "闭口", "眼神", "视线", "肩线", "呼吸", "手指", "下颌", "盯着",
    "探出", "眨眼", "抓住", "抓衣", "放松", "观察", "抬头", "停住",
)
INTERPERSON_PROP_TRANSFER_TERMS = ("递", "交给", "接过", "接住", "塞给")


@dataclass(frozen=True)
class SemanticShotReport:
    shot_type: str
    label: str
    recommended_min: int
    recommended_max: int
    length: int
    missing_slots: tuple[str, ...]

    @property
    def semantically_complete(self) -> bool:
        return not self.missing_slots

    @property
    def length_guidance(self) -> str:
        if self.length < self.recommended_min:
            return "short"
        if self.length > self.recommended_max:
            return "long"
        return "in-range"

    @property
    def disagreement(self) -> str:
        if self.semantically_complete and self.length_guidance == "short":
            return "semantic-complete/short"
        if not self.semantically_complete and self.length_guidance != "short":
            return "semantic-incomplete/despite-length"
        return "none"


def compact_len(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def has_scene_anchor(text: str) -> bool:
    prefix = strip_quoted_content(text[:180])
    if "锚点" in prefix or any(term in prefix for term in SCENE_ANCHOR_TERMS):
        return True
    return bool(
        re.search(
            r"[\u4e00-\u9fff]{1,12}(?:岸|溪|河|湖|海|滩|坡|路|巷|街|桥|屋|房|厅|室|院|楼|"
            r"台|桌|柜|床|椅|门|窗|墙|栏|林|田|地|草|水面|石面|卵石|泥地)",
            prefix,
        )
    )


def has_executable_visual_detail(text: str) -> bool:
    cleaned = strip_quoted_content(text)
    has_light_relation = any(term in cleaned for term in MOTIVATED_LIGHT_SOURCE_TERMS) and any(
        term in cleaned for term in VISUAL_RESULT_TERMS
    )
    has_material_relation = any(
        term in cleaned for term in ("木纹", "石纹", "金属", "玻璃", "布料", "棉麻", "皮革", "纸面", "水面")
    ) and any(term in cleaned for term in VISUAL_RESULT_TERMS)
    return has_light_relation or has_material_relation


def has_end_state(text: str) -> bool:
    cleaned = strip_quoted_content(text)
    if any(term in cleaned for term in END_STATE_TERMS):
        return True
    ending = cleaned[-110:]
    return bool(
        re.search(r"(?:停在|落在|锁住|定在|保持|没有松开|没有躲开|不再后退|维持)[^。；;\n]{0,48}(?:。|$)", ending)
        or re.search(r"(?:镜头|摄影机)[^。；;\n]{0,30}(?:固定|静止|稳定)[^。；;\n]{0,30}(?:。|$)", ending)
    )


def has_visible_dialogue(text: str) -> bool:
    return bool(
        re.search(r"(?:说|问|喊|低语|回应|反问)[：:]?\s*[“\"][^”\"]+[”\"]", text)
        or (quoted_lines(text) and any(term in text for term in LIP_SYNC_TERMS))
    )


def has_visible_person(text: str, cast_names: list[str] | None = None) -> bool:
    """Return whether this shot contains a visible human subject."""
    cast_names = cast_names or []
    cleaned = strip_quoted_content(text)
    if is_standalone_cutaway(text) or re.search(r"可见人数[：:]\s*(?:0|零)人", cleaned):
        return False
    offscreen = set(offscreen_names(text))
    if any(name in cleaned and name not in offscreen for name in cast_names):
        return True
    count_match = VISIBLE_COUNT_RE.search(cleaned)
    if count_match and not re.search(r"(?:0|零)人", count_match.group(0)):
        return True
    if re.search(r"人物|男人|女人|男孩|女孩|老人|孩子|说话者|听者|主角", cleaned):
        return True
    return bool(re.search(r"(?:^|[，。；;\s])(?:他|她)(?:的|在|站|坐|走|看|手|脸|身体|肩|背|$)", cleaned))


def has_multiple_visible_people(text: str, cast_names: list[str]) -> bool:
    count_match = VISIBLE_COUNT_RE.search(text)
    if count_match and re.search(r"(?:[2-9]|[二三四五六七八九十])人", count_match.group(0)):
        return True
    visible_cast = [name for name in cast_names if name and name in text and name not in offscreen_names(text)]
    return len(set(visible_cast)) >= 2 or bool(re.search(r"双人|两人|二人|三人|众人|人群", text))


def detect_shot_type(direct: str, header: str = "", cast_names: list[str] | None = None) -> str:
    """Classify a shot by its dominant Jimeng generation task."""
    cast_names = cast_names or []
    cleaned = strip_quoted_content(direct)
    has_time_montage = any(term in cleaned for term in MONTAGE_TERMS if term != "蒙太奇") or (
        "蒙太奇" in cleaned and any(term in cleaned for term in TIME_CHANGE_TERMS)
    )
    if has_time_montage:
        return "montage_fragment"
    if is_standalone_cutaway(direct):
        return "cutaway_insert"
    if keyframe_trigger_reasons(direct, header) or any(term in cleaned for term in INTERPERSON_PROP_TRANSFER_TERMS):
        return "high_risk_transition"
    if has_visible_dialogue(direct):
        if has_multiple_visible_people(direct, cast_names) and any(term in cleaned for term in RELATION_CHANGE_TERMS):
            return "multi_character_relationship"
        return "dialogue_performance"
    if has_multiple_visible_people(direct, cast_names) and any(term in cleaned for term in RELATION_CHANGE_TERMS + RELATION_TERMS):
        return "multi_character_relationship"
    has_cause = any(term in cleaned for term in SILENT_CAUSE_TERMS)
    has_effect = any(term in cleaned for term in ENVIRONMENT_RESPONSE_TERMS + ACTION_RESULT_TERMS)
    if has_cause and has_effect:
        return "silent_causal"
    has_action_goal = any(term in cleaned for term in ACTION_PURPOSE_TERMS)
    has_route_result = any(term in cleaned for term in ACTION_ROUTE_TERMS) and any(
        term in cleaned for term in ACTION_RESULT_TERMS
    )
    if (has_action_goal or has_route_result) and any(term in cleaned for term in MOVE_TERMS + ACTION_RESULT_TERMS):
        return "non_combat_action"
    return "unclassified"


def semantic_completeness_issues(
    shot_type: str,
    direct: str,
    performance: str = "",
    block: str = "",
    cast_names: list[str] | None = None,
) -> list[str]:
    """Return missing semantic slots without changing hard validation."""
    cast_names = cast_names or []
    cleaned = strip_quoted_content(direct)
    missing: list[str] = []

    if not (
        any(term in direct[:140] for term in ASPECT_TERMS)
        and any(term in direct[:140] for term in STYLE_TERMS)
        and has_scene_anchor(direct)
    ):
        missing.append("画幅/风格/场景锚点")
    if not (any(term in direct for term in SHOT_SIZE_TERMS) and any(term in direct for term in CAMERA_TERMS) and has_camera_state(direct)):
        missing.append("景别/机位/镜头状态")
    visible_subject = is_standalone_cutaway(direct) or any(name in direct for name in cast_names) or bool(
        VISIBLE_COUNT_RE.search(direct) or re.search(r"人物|男人|女人|男孩|女孩|老人|孩子|他|她", cleaned)
    )
    if not visible_subject:
        missing.append("可见主体与当前关系")
    if not has_executable_visual_detail(direct):
        missing.append("动机光源或剧情材质落点")
    if not any(term in cleaned for term in ACTION_CHAIN_TERMS + HELD_STATE_TERMS + ENVIRONMENT_RESPONSE_TERMS):
        missing.append("可见变化或明确保持")
    if not has_end_state(direct):
        missing.append("结束稳定状态")

    task_dimensions = sum((
        has_visible_dialogue(direct),
        bool(keyframe_trigger_reasons(direct, "复杂" if "复杂" in header_from_block(block) else "普通")),
        has_camera_move(direct),
        any(term in cleaned for term in ACTION_PURPOSE_TERMS + ACTION_ROUTE_TERMS),
        any(term in cleaned for term in KEYFRAME_UI_TERMS),
        any(term in cleaned for term in ("闪回", "回忆", "梦境", "人群")),
    ))
    if task_dimensions >= 4:
        missing.append("单一镜头任务（当前任务过载）")

    if shot_type == "dialogue_performance":
        if not quoted_lines(direct):
            missing.append("对白原文")
        if not any(term in direct for term in LIP_SYNC_TERMS):
            missing.append("可见口型")
        if not any(term in direct + performance for term in MOUTH_CLOSE_TERMS):
            missing.append("对白结束收口")
        if has_multiple_visible_people(direct, cast_names) and not any(
            term in direct + performance for term in LISTENER_REACTION_TERMS
        ):
            missing.append("听者反应")
        has_trigger = any(term in cleaned for term in ("听见", "听到", "看见", "看到", "发现", "察觉", "被", "话音", "提到", "说到", "问完", "之后", "后，"))
        has_leak = any(term in cleaned for term in FACIAL_DETAIL_TERMS + BODY_PROP_EMOTION_TERMS)
        if not (has_trigger and has_leak):
            missing.append("表演触发与可见泄露")
    elif shot_type == "multi_character_relationship":
        if not has_multiple_visible_people(direct, cast_names):
            missing.append("多人同框关系")
        if not any(term in cleaned for term in RELATION_CHANGE_TERMS) and not (
            has_end_state(direct) and any(term in cleaned for term in RELATION_TERMS)
        ):
            missing.append("关系变化或关系定格")
    elif shot_type == "silent_causal":
        if not any(term in cleaned for term in SILENT_CAUSE_TERMS):
            missing.append("可见原因")
        if not any(term in cleaned for term in ACTION_CHAIN_TERMS):
            missing.append("人物动作")
        if not any(term in cleaned for term in ENVIRONMENT_RESPONSE_TERMS):
            missing.append("环境反馈")
        if not any(term in cleaned for term in ACTION_RESULT_TERMS + END_STATE_TERMS):
            missing.append("因果新状态")
    elif shot_type == "cutaway_insert":
        if not is_standalone_cutaway(direct):
            missing.append("戏剧物件/环境主体")
        if not any(term in cleaned for term in COMPOSITION_TERMS):
            missing.append("插入镜构图焦点")
        handoff = extract_optional_field(block, "【剪辑衔接】") if block else ""
        if not any(term in direct + handoff for term in SOUND_BRIDGE_TERMS):
            missing.append("独立生成声桥")
    elif shot_type == "montage_fragment":
        if not any(term in cleaned for term in ("同一", "固定", "始终") + SCENE_ANCHOR_TERMS):
            missing.append("重复空间锚点")
        if not any(term in cleaned for term in STATE_INCREMENT_TERMS):
            missing.append("单一状态增量")
        if not any(term in cleaned for term in TIME_CHANGE_TERMS):
            missing.append("时间变化")
    elif shot_type == "non_combat_action":
        if not any(term in cleaned for term in ACTION_PURPOSE_TERMS + ACTION_RESULT_TERMS):
            missing.append("行动目标")
        if not any(term in cleaned for term in ACTION_ROUTE_TERMS):
            missing.append("可见路线")
        if not any(term in cleaned for term in ACTION_RESULT_TERMS):
            missing.append("到达/调整结果")
    elif shot_type == "high_risk_transition":
        chain_hits = {term for term in ACTION_CHAIN_TERMS if term in cleaned}
        if len(chain_hits) < 3:
            missing.append("起点到终态转换链")
        has_keyframes = bool(
            extract_optional_field(block, KEYFRAME_IMAGE_FIELD) and extract_optional_field(block, KEYFRAME_VIDEO_FIELD)
        ) if block else False
        if block and not (has_keyframes or extract_optional_field(block, "【镜内状态转换】")):
            missing.append("关键帧或拆分决策")

    if any(term in cleaned for term in INTERPERSON_PROP_TRANSFER_TERMS):
        if not any(term in cleaned for term in ("手中", "掌中", "包内", "口袋", "桌面", "台面", "右手", "左手")):
            missing.append("道具起点")
        if not any(term in cleaned for term in ("接触", "碰到", "触到")):
            missing.append("道具接触")
        if not any(term in cleaned for term in ("握住", "接住", "接过", "抓稳")):
            missing.append("接收方握稳")
        if not any(term in cleaned for term in ("松手", "放开", "释放")):
            missing.append("原持有人释放")
        if not any(term in cleaned for term in ("最终", "最后", "稳定", "留在", "停在", "由")):
            missing.append("最终持有人/位置")

    if "手机" in cleaned:
        if not phone_purpose_detected(direct):
            missing.append("手机用途")
        orientation_ok = (
            phone_screen_faces_user(direct) and phone_camera_sees_back_or_edge(direct)
        ) if phone_operation_detected(direct) else bool(
            re.search(r"屏幕(?:朝向|面向|斜向)[^，。；;\n]{0,12}(?:镜头|观众|本人|使用者|持机者)", cleaned)
        )
        if not orientation_ok:
            missing.append("手机屏幕朝向")

    return list(dict.fromkeys(missing))


def header_from_block(block: str) -> str:
    match = re.search(r"【镜号】[ \t]*\r?\n\s*([^\n]+)", block)
    return match.group(1).strip() if match else ""


def build_semantic_report(
    direct: str,
    header: str = "",
    performance: str = "",
    block: str = "",
    cast_names: list[str] | None = None,
) -> SemanticShotReport:
    shot_type = detect_shot_type(direct, header, cast_names)
    label, recommended_min, recommended_max = SHOT_TYPE_GUIDANCE[shot_type]
    missing = semantic_completeness_issues(shot_type, direct, performance, block, cast_names)
    return SemanticShotReport(
        shot_type=shot_type,
        label=label,
        recommended_min=recommended_min,
        recommended_max=recommended_max,
        length=compact_len(direct),
        missing_slots=tuple(missing),
    )


def has_reverse_shot(text: str) -> bool:
    """Match camera placement behind a shoulder, not character blocking behind it."""
    return bool(REVERSE_SHOT_RE.search(strip_quoted_content(text)))


def has_camera_move(text: str) -> bool:
    """Detect camera motion without treating performance verbs as camera instructions."""
    cleaned = strip_quoted_content(text)
    unambiguous_moves = (
        "推近", "推进镜头", "拉远", "后拉镜头", "横移", "侧移", "跟拍", "环绕",
        "转焦", "拉焦", "上摇", "下摇", "摇摄", "推镜", "拉镜", "移镜",
    )
    if any(term in cleaned for term in unambiguous_moves):
        return True
    for match in re.finditer(r"(?:镜头|摄影机|相机|机位)[^，。；;\n]{0,32}", cleaned):
        camera_clause = match.group(0)
        camera_clause = re.sub(
            r"(?:摇头|点头|眼神[^，。；;\n]{0,8}移动|视线[^，。；;\n]{0,8}移动|"
            r"手指?[^，。；;\n]{0,8}移动|身体[^，。；;\n]{0,8}移动)",
            "",
            camera_clause,
        )
        if re.search(r"推|拉|摇|移|跟|环绕|转焦|拉焦", camera_clause):
            return True
    return False


def has_camera_state(text: str) -> bool:
    """Require a static-camera statement or a real camera move."""
    cleaned = strip_quoted_content(text)
    if has_camera_move(cleaned):
        return True
    return bool(
        re.search(
            r"(?:(?:镜头|摄影机|相机|机位)[^，。；;\n]{0,10}(?:固定|静止|保持静止|锁定|手持)"
            r"|(?:固定|静止)(?:镜头|摄影机|相机|机位))",
            cleaned,
        )
    )


def is_standalone_cutaway(text: str) -> bool:
    """Distinguish a cutaway subject from the same object used as scene texture."""
    cleaned = strip_quoted_content(text)
    if any(term in cleaned for term in CUTAWAY_EXPLICIT_TERMS):
        return True
    zero_visible_people = bool(re.search(r"可见人数[：:]\s*(?:0|零)人", cleaned))
    if zero_visible_people and any(term in cleaned for term in CUTAWAY_SUBJECT_TERMS):
        return True
    for subject in CUTAWAY_SUBJECT_TERMS:
        if re.search(
            rf"(?:只拍|仅拍|只见|仅见|镜头对准|镜头聚焦|画面只保留|特写)"
            rf"[^，。；;\n]{{0,12}}{re.escape(subject)}",
            cleaned,
        ):
            return True
    return False


def strip_quoted_content(text: str) -> str:
    """Exclude source dialogue/OS text from visual-concept linting."""
    return re.sub(r"[“\"][^”\"]*[”\"]", "", text)


def has_negation_near(text: str, start: int, end: int) -> bool:
    before = text[max(0, start - 14):start].rstrip()
    after = text[end:min(len(text), end + 10)].lstrip()
    flexible_prefix = re.search(
        r"(?:不要|不能|不应|禁止|避免|去掉|去除|移除|排除|没有|不是|不戴|不带|不穿)[^，。；;\n]{0,6}$",
        before,
    )
    return bool(flexible_prefix) or any(before.endswith(cue) for cue in NEGATION_CUES_BEFORE) or any(
        after.startswith(cue) for cue in NEGATION_CUES_AFTER
    )


def negative_priming_issues(text: str, negative_field: bool = False) -> list[str]:
    cleaned = strip_quoted_content(text)
    issues: list[str] = []
    for label, terms, rewrite in NEGATIVE_PRIMING_GROUPS:
        hits: list[str] = []
        for term in terms:
            for match in re.finditer(re.escape(term), cleaned):
                if negative_field or has_negation_near(cleaned, match.start(), match.end()):
                    hits.append(term)
                    break
        if hits:
            issues.append(f"{label}：{','.join(dict.fromkeys(hits))}；{rewrite}")
    return issues


def phone_operation_detected(text: str) -> bool:
    cleaned = strip_quoted_content(text)
    if any(term in cleaned for term in PHONE_OPERATION_TERMS):
        return True
    return bool(
        re.search(r"手机[^。；;\n]{0,24}(?:玩|打)游戏", cleaned)
        or re.search(r"(?:玩|打)游戏[^。；;\n]{0,24}手机", cleaned)
        or re.search(r"手机[^。；;\n]{0,16}(?:打字|浏览|滑动|点击)", cleaned)
    )


def phone_display_explicit(text: str) -> bool:
    cleaned = strip_quoted_content(text)
    return any(term in cleaned for term in PHONE_EXPLICIT_DISPLAY_TERMS)


def phone_purpose_detected(text: str) -> bool:
    cleaned = strip_quoted_content(text)
    if any(term in cleaned for term in PHONE_PURPOSE_TERMS) or phone_operation_detected(cleaned):
        return True
    has_operation_evidence = any(
        term in cleaned for term in ("双拇指", "单拇指", "拇指点击", "拇指滑动", "点击", "滑动", "横持", "竖持")
    )
    return "手机" in cleaned and has_operation_evidence and (
        phone_screen_faces_user(cleaned) or phone_camera_sees_back_or_edge(cleaned)
    )


def phone_screen_faces_user(text: str) -> bool:
    cleaned = strip_quoted_content(text)
    return bool(
        re.search(r"屏幕(?:朝向|面向|斜向)[^，。；;\n]{0,10}(?:本人|使用者|持机者)", cleaned)
        or any(term in cleaned for term in ("屏幕朝向使用者", "屏幕面向使用者", "屏幕朝向持机者", "屏幕面向持机者"))
    )


def phone_camera_sees_back_or_edge(text: str) -> bool:
    cleaned = strip_quoted_content(text)
    return any(term in cleaned for term in PHONE_CAMERA_BACK_TERMS)


def phone_operation_issues(
    direct: str,
    state: str,
    necessary: str,
    negative: str,
    keyframe_image: str,
    keyframe_video: str,
) -> list[str]:
    if not phone_operation_detected(direct) or phone_display_explicit(direct):
        return []
    cleaned = strip_quoted_content(direct)
    issues: list[str] = []
    if any(term in cleaned for term in PHONE_SCREEN_TO_CAMERA_TERMS):
        issues.append("操作型手机被错误升级为展示型；屏幕不得默认正对镜头/观众")
    if not phone_screen_faces_user(direct):
        issues.append("缺少用户侧朝向：写明屏幕朝向持机人物本人")
    if not phone_camera_sees_back_or_edge(direct):
        issues.append("缺少镜头侧朝向：写明手机背面或斜侧边缘朝向镜头")
    directly_fed_fields = (
        ("画面描述", direct),
        ("本镜必要约束", necessary),
        ("本镜补充负面提示词", negative),
        ("关键帧生图提示", keyframe_image),
        ("即梦视频提示", keyframe_video),
    )
    for field_name, field_text in directly_fed_fields:
        field_cleaned = strip_quoted_content(field_text)
        ui_hits = [term for term in PHONE_GAME_INTERFACE_TERMS if term in field_cleaned]
        if ui_hits:
            issues.append(
                f"无展示任务时【{field_name}】不得出现界面先验词：{','.join(dict.fromkeys(ui_hits))}；"
                "改用拇指动作、屏幕冷光或手机翻面/屏幕乱字等无语义坏相词"
            )
    if not phone_screen_faces_user(state):
        issues.append("【状态继承】必须复写屏幕朝向持机人物本人")
    if keyframe_image and (
        not phone_screen_faces_user(keyframe_image) or not phone_camera_sees_back_or_edge(keyframe_image)
    ):
        issues.append("操作型手机关键帧必须重复屏幕朝本人、手机背面或斜侧边缘朝镜头")
    return issues


def skin_tone_protection_issues(direct: str) -> list[str]:
    cleaned = strip_quoted_content(direct)
    has_visible_skin = any(term in cleaned for term in VISIBLE_SKIN_TERMS)
    color_hits = [term for term in COLORED_ENVIRONMENT_TERMS if term in cleaned]
    volume_hits = [term for term in VOLUMETRIC_LIGHT_TERMS if term in cleaned]
    if not has_visible_skin or not (color_hits or volume_hits):
        return []
    issues: list[str] = []
    positive_skin = any(term in cleaned for term in POSITIVE_SKIN_TONE_TERMS)
    lighting_anchor = any(term in cleaned for term in SKIN_LIGHTING_TERMS)
    negative_only = any(term in cleaned for term in NEGATIVE_ONLY_SKIN_TERMS)
    if not positive_skin:
        detail = ",".join((color_hits + volume_hits)[:5])
        issues.append(f"彩色环境/体积光缺少正向中性肤色锚点 -> {detail}")
    if not lighting_anchor:
        issues.append("缺少脸部受光面或浅阴影落点；写明主光照哪侧脸及鼻侧/眼窝/下颌阴影")
    if negative_only and not positive_skin:
        issues.append("不能只用不发青/不发灰/不过曝保护肤色；改写为自然偏暖或中性肤色")
    if volume_hits and not any(term in cleaned for term in VOLUMETRIC_PROTECTION_TERMS):
        issues.append("丁达尔/体积光缺少主体避让；写明窄束落在背景或地面，脸、嘴和活动手保持清晰")
    return issues


def group_cast_names(cast: str) -> list[str]:
    names: list[str] = []
    for raw_line in cast.splitlines():
        line = re.sub(r"^[-*]\s*", "", raw_line.strip())
        match = re.match(r"([\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z0-9_·]{0,11})", line)
        if match:
            names.append(match.group(1))
    return list(dict.fromkeys(names))


def named_person_contexts(direct: str, cast_names: list[str]) -> dict[str, list[str]]:
    if len(cast_names) < 2:
        return {}
    matches: list[tuple[int, int, str]] = []
    for name in cast_names:
        matches.extend((match.start(), match.end(), name) for match in re.finditer(re.escape(name), direct))
    matches.sort()
    contexts: dict[str, list[str]] = {name: [] for name in cast_names}
    for index, (start, end, name) in enumerate(matches):
        previous_name_end = matches[index - 1][1] if index > 0 else 0
        previous_boundary = max(
            direct.rfind(mark, previous_name_end, start)
            for mark in ("。", "；", ";", "，", "，", "\n")
        )
        prefix_start = max(previous_name_end, previous_boundary + 1, start - 24)
        next_name_start = matches[index + 1][0] if index + 1 < len(matches) else len(direct)
        boundary = re.search(r"[。；;\n]", direct[end:])
        sentence_end = end + boundary.start() if boundary else len(direct)
        context_end = min(next_name_start, sentence_end, end + 72)
        suffix = direct[end:context_end]
        connector = re.search(r"(?:和|与|及)(?=[^，。；;\n]{0,12}(?:前景|近处|后景|远处|镜头近端|镜头远端))", suffix)
        if connector:
            suffix = suffix[:connector.start()]
        contexts[name].append(direct[prefix_start:start] + name + suffix)
    return contexts


def person_depth_labels(contexts: dict[str, list[str]]) -> dict[str, set[str]]:
    labels: dict[str, set[str]] = {}
    for name, parts in contexts.items():
        joined = "；".join(parts)
        person_labels: set[str] = set()
        if any(term in joined for term in PERSON_NEAR_DEPTH_TERMS):
            person_labels.add("near")
        if any(term in joined for term in PERSON_FAR_DEPTH_TERMS):
            person_labels.add("far")
        labels[name] = person_labels
    return labels


def perspective_scale_issues(direct: str, cast_names: list[str]) -> list[str]:
    cleaned = strip_quoted_content(direct)
    issues: list[str] = []
    contexts = named_person_contexts(cleaned, cast_names)
    labels = person_depth_labels(contexts)
    near_names = [name for name, values in labels.items() if "near" in values]
    far_names = [name for name, values in labels.items() if "far" in values]
    paired_depth = re.search(
        r"([^，。；;\n]{1,12})[与和]([^，。；;\n]{1,12})分别[^，。；;\n]{0,20}"
        r"(?:前景|近处|镜头近端)[^，。；;\n]{0,8}(?:后景|远处|镜头远端)",
        cleaned,
    )
    if paired_depth:
        first, second = paired_depth.group(1), paired_depth.group(2)
        if any(name in first for name in cast_names) and any(name in second for name in cast_names):
            near_names.append(next(name for name in cast_names if name in first))
            far_names.append(next(name for name in cast_names if name in second))
    has_named_depth_split = bool(near_names and far_names and set(near_names) != set(far_names))
    near_context = "；".join(part for name in near_names for part in contexts.get(name, []))
    shoulder_local_only = bool(near_names) and all(
        any(term in "；".join(contexts.get(name, [])) for term in ("肩线", "后脑边缘", "局部侧脸"))
        for name in set(near_names)
    ) and (
        has_reverse_shot(cleaned)
        and any(term in near_context for term in ("占画面", "裁切", "弱虚化"))
    )
    if has_named_depth_split and not shoulder_local_only:
        has_ground_perspective = any(term in cleaned for term in GROUND_PERSPECTIVE_TERMS) or bool(
            re.search(r"同一[^，。；;\n]{0,12}(?:地面|地板|路面|石板路|走廊|台阶|承载面|空间透视)", cleaned)
        )
        if not has_ground_perspective:
            issues.append("具名人物分处不同纵深但缺少同一连续地面/承载空间及透视收束")
        if not (
            any(term in cleaned for term in NEAR_PROJECTION_TERMS)
            and any(term in cleaned for term in FAR_PROJECTION_TERMS)
        ):
            issues.append("具名人物分处不同纵深但缺少近处投影较大、远处投影较小的画面事实")
        has_body_scale_lock = any(term in cleaned for term in BODY_SCALE_LOCK_TERMS) or bool(
            re.search(r"(?:头身比|头身比例|骨架|真实身高|真实体型)[^，。；;\n]{0,16}(?:稳定|保持|不变)", cleaned)
        )
        if not has_body_scale_lock:
            issues.append("具名人物分处不同纵深但缺少头身比例/骨架/真实身高关系锁定")

    if any(term in cleaned for term in TOWARD_CAMERA_TERMS):
        if not any(term in cleaned for term in CONTINUOUS_GROWTH_TERMS) and not re.search(
            r"(?:画面占比|投影尺度|画面投影)[^，。；;\n]{0,10}(?:连续|逐渐|逐步|平滑)[^，。；;\n]{0,6}增大", cleaned
        ):
            issues.append("人物走向镜头时必须写画面占比随距离连续增大")
        if not any(term in cleaned for term in BODY_SCALE_LOCK_TERMS):
            issues.append("人物走向镜头时必须保持头身比例、骨架或真实身高稳定")
    if any(term in cleaned for term in AWAY_FROM_CAMERA_TERMS):
        if not any(term in cleaned for term in CONTINUOUS_SHRINK_TERMS) and not re.search(
            r"(?:画面占比|投影尺度|画面投影)[^，。；;\n]{0,10}(?:连续|逐渐|逐步|平滑)[^，。；;\n]{0,6}减小", cleaned
        ):
            issues.append("人物远离镜头时必须写画面占比随距离连续减小")
        if not any(term in cleaned for term in BODY_SCALE_LOCK_TERMS):
            issues.append("人物远离镜头时必须保持头身比例、骨架或真实身高稳定")
    return issues


def iter_groups(text: str):
    header = r"^####\s+(S\d+-\d+)(?:｜镜头组总时长：(\d+(?:\.\d+)?)s)?\s*$"
    pattern = re.compile(
        header + r"([\s\S]*?)(?=" + header + r"|^##\s|\Z)",
        re.M,
    )
    yield from pattern.finditer(text)


def iter_children(group_block: str):
    pattern = re.compile(r"【镜号】[ \t]*\r?\n\s*([^\n]+)\r?\n([\s\S]*?)(?=\r?\n【镜号】[ \t]*\r?\n|\Z)")
    yield from pattern.finditer(group_block)


def extract(block: str, field: str, next_field: str | None = None) -> str:
    field_line = re.escape(field) + r"[ \t]*\r?\n"
    if next_field:
        next_line = re.escape(next_field) + r"[ \t]*(?=\r?\n|\Z)"
        m = re.search(field_line + r"([\s\S]*?)(?=\r?\n\r?\n" + next_line + r")", block)
    else:
        m = re.search(field_line + r"([\s\S]*)", block)
    return m.group(1).strip() if m else ""


def extract_until_any(block: str, field: str, next_fields: tuple[str, ...]) -> str:
    alternatives = "|".join(re.escape(next_field) for next_field in next_fields)
    pattern = (
        re.escape(field) + r"[ \t]*\r?\n([\s\S]*?)(?=\r?\n\r?\n(?:" + alternatives + r")[ \t]*(?=\r?\n|\Z)|\Z)"
    )
    m = re.search(pattern, block)
    return m.group(1).strip() if m else ""


def direct_prompt(block: str) -> str:
    return extract_until_any(block, "【画面描述｜直接复制】", DIRECT_NEXT_FIELDS)


def extract_optional_field(block: str, field: str) -> str:
    m = re.search(re.escape(field) + r"[ \t]*\r?\n([\s\S]*?)(?=\r?\n\r?\n【|\Z)", block)
    return m.group(1).strip() if m else ""


def extract_top_section(text: str, heading: str) -> str:
    m = re.search(re.escape(heading) + r"\n([\s\S]*?)(?=\n##\s|\Z)", text)
    return m.group(1).strip() if m else ""


def labeled_control_value(text: str, label: str) -> str:
    match = re.search(r"(?:^|\n)" + re.escape(label) + r"[：:]\s*([^\n]+)", str(text or ""))
    return match.group(1).strip() if match else ""


def quality_control_issues(control: str, direct: str) -> list[str]:
    issues: list[str] = []
    if not control.strip():
        return [f"missing {QUALITY_CONTROL_FIELD}"]
    values = {label: labeled_control_value(control, label) for label in SHOT_QUALITY_LABELS}
    for label, value in values.items():
        if len(value) < 6:
            issues.append(f"{QUALITY_CONTROL_FIELD}.{label}缺少本镜可执行内容")
        elif any(term in value for term in ("已检查", "按合同", "同上", "见内部", "待定", "TBD")):
            issues.append(f"{QUALITY_CONTROL_FIELD}.{label}不能使用内部占位或审查结论")

    dynamic = values.get("动态美学", "")
    if dynamic and not (
        any(term in dynamic for term in ("起幅", "起态", "固定起点"))
        and any(term in dynamic for term in ("触发", "有意静止", "保持静止", "无主体动作"))
        and any(term in dynamic for term in ("落幅", "终态", "停稳", "稳定"))
    ):
        issues.append(f"{QUALITY_CONTROL_FIELD}.动态美学必须写起幅、触发/有意静止和稳定落幅")

    performance = values.get("表演与情绪", "")
    has_visible_person = not is_standalone_cutaway(direct) and not re.search(r"可见人数[：:]\s*[0零]人", direct)
    if has_visible_person and performance and not (
        any(term in performance for term in ("触发", "听见", "看见", "感到"))
        and any(term in performance for term in ("泄露", "眼", "呼吸", "嘴角", "下颌", "手", "肩", "重心"))
        and any(term in performance for term in ("余波", "残留", "落幅", "停在"))
    ):
        issues.append(f"{QUALITY_CONTROL_FIELD}.表演与情绪必须写触发、可见泄露和余波")

    montage = values.get("蒙太奇与剪辑", "")
    if detect_shot_type(direct) == "montage_fragment" and montage and not (
        any(term in montage for term in ("固定锚点", "重复锚点", "同一构图", "匹配点"))
        and any(term in montage for term in ("状态增量", "时间增量", "数量变化", "阶段变化"))
        and any(term in montage for term in ("声音", "声桥", "切点", "回到现实", "现实锚点"))
    ):
        issues.append(f"{QUALITY_CONTROL_FIELD}.蒙太奇与剪辑必须写固定锚点、单片段状态增量和声音/切点承接")

    light = values.get("光效与曝光", "")
    if any(term in direct for term in ("体积光", "丁达尔", "闪电", "火光", "霓虹", "屏幕光", "倒影", "反射")):
        if not (
            any(term in light for term in ("光源", "窗", "灯", "火", "屏幕", "反射面"))
            and any(term in light for term in ("方向", "左", "右", "上", "后", "前", "侧"))
            and any(term in light for term in ("受光", "落在", "照亮", "作用于", "接收面"))
            and any(term in light for term in ("边界", "止于", "不越过", "衰减", "稳定", "持续"))
        ):
            issues.append(f"{QUALITY_CONTROL_FIELD}.光效与曝光必须写光源、方向、受光面和时间/空间边界")

    grounding_rules = {
        "画面质感": ("构图", "焦点", "实焦", "景深", "前景", "中景", "后景", "材质", "纹理", "划痕", "反光"),
        "光效与曝光": ("光", "照亮", "受光", "阴影", "曝光", "高光", "黑位", "色温"),
        "动态美学": ("镜头固定", "摄影机固定", "推近", "拉远", "横移", "跟拍", "转焦", "停稳", "落幅", "保持到结束"),
        "穿帮控制": ("可见人数", "左侧", "右侧", "中间", "前景", "中景", "后景", "手中", "桌面", "接触", "支撑", "归属", "槽位", "边界分开"),
    }
    if has_visible_person:
        grounding_rules["表演与情绪"] = (
            "眼", "嘴角", "下颌", "呼吸", "手指", "肩", "重心", "视线", "闭口", "屏息", "停顿",
        )
    for label, terms in grounding_rules.items():
        if values.get(label) and not any(term in direct for term in terms):
            issues.append(f"{QUALITY_CONTROL_FIELD}.{label}未转译进【画面描述｜直接复制】")

    reroll_visible_terms = [
        term for term in ("固定机位", "低幅", "单一路径", "单一动作", "人数固定", "槽位固定", "保持静止")
        if term in values.get("抽卡策略", "")
    ]
    if reroll_visible_terms and not any(term in direct for term in reroll_visible_terms):
        issues.append(f"{QUALITY_CONTROL_FIELD}.抽卡策略的可见降级结果未转译进【画面描述｜直接复制】")
    if detect_shot_type(direct) == "montage_fragment" and montage:
        montage_terms = ("固定锚点", "重复锚点", "匹配", "状态增量", "数量变化", "阶段变化", "声桥", "现实锚点")
        if not any(term in direct for term in montage_terms):
            issues.append(f"{QUALITY_CONTROL_FIELD}.蒙太奇与剪辑的可见结果未转译进【画面描述｜直接复制】")
    return issues


def direct_sentence(state_change: str, label: str) -> str:
    m = re.search(re.escape(label) + r"[：:]\s*([^\n；;]+)", state_change)
    return m.group(1).strip() if m else ""


def quoted_lines(text: str) -> list[str]:
    return [line.strip() for line in re.findall(r"“([^”]+)”", text) if line.strip()]


def split_names(text: str) -> list[str]:
    names: list[str] = []
    cleaned = re.sub(r"(?:本镜|只|均|都|在|位于|右侧|左侧|画面|画外|不入画|不出镜|不出现|身体|肩线|倒影|虚化人影|和|与|及)", "、", text)
    for part in re.split(r"[、，,；;\s]+", cleaned):
        part = part.strip()
        if 1 <= len(part) <= 6 and re.fullmatch(r"[\u4e00-\u9fffA-Za-z0-9_·]+", part):
            names.append(part)
    return names


def offscreen_names(text: str) -> set[str]:
    names: set[str] = set()
    for marker in OFFSCREEN_MARKERS:
        for match in re.finditer(r"([^\n。；;]{1,36})" + re.escape(marker), text):
            clause = re.split(r"[，,]", match.group(1))[-1]
            names.update(split_names(clause))
    for match in re.finditer(r"([\u4e00-\u9fffA-Za-z0-9_·]{1,6})在画外", text):
        names.add(match.group(1))
    return {name for name in names if name not in {"本镜", "画面", "身体", "肩线", "倒影"}}


def offscreen_visual_target_issues(direct: str, block: str) -> list[str]:
    issues: list[str] = []
    names = offscreen_names(direct + "\n" + extract_optional_field(block, "【本镜必要约束｜直接复制】"))
    for name in sorted(names, key=len, reverse=True):
        for verb in VISUAL_TARGET_VERBS:
            if re.search(re.escape(verb) + r"[^，。；;\n]{0,8}" + re.escape(name), direct):
                issues.append(f"{name}:{verb}")
    return issues


def visible_dialogue_quotes(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        if not any(q in raw_line for q in ("“", "”")):
            continue
        if any(term in raw_line for term in POST_AUDIO_TERMS) and not any(term in raw_line for term in VISIBLE_SPEECH_TERMS):
            continue
        if any(term in raw_line for term in VISIBLE_SPEECH_TERMS):
            lines.extend(quoted_lines(raw_line))
    return lines


def has_sound_text(text: str) -> bool:
    if any(label in text for label in POST_AUDIO_LABEL_TERMS):
        return True
    return bool(re.search(r"(?:说|问|喊|低语|回应|反问)[：:：]?[“\"][^”\"]+[”\"]", text))


def post_audio_format_issues(text: str) -> list[str]:
    issues: list[str] = []
    label_pattern = r"(?:OS|OV|系统音|内心独白|旁白)"
    wrapped_pattern = re.compile(label_pattern + r"\s*[：:]\s*[“\"][^”\"]+[”\"]")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or not any(label in line for label in POST_AUDIO_LABEL_TERMS):
            continue
        if "无台词" in line or re.fullmatch(r"无(?:OS|OV|系统音|内心独白|旁白).*", line):
            continue
        has_text_signal = any(mark in line for mark in ("“", "”", '"')) or any(
            term in line for term in ("响起", "念出", "吐槽", "旁白", "低语", "声音", "内心")
        )
        if has_text_signal and not wrapped_pattern.search(line):
            issues.append(line)
    return issues


def is_screen_invisible_to_camera(text: str) -> bool:
    if any(term in text for term in SCREEN_INVISIBLE_TERMS):
        return True
    if re.search(r"手机背面[^，。；;]{0,12}镜头", text):
        return True
    if re.search(r"屏幕朝向[^，。；;]{1,12}本人[^，。；;]{0,8}不可见", text):
        return True
    if re.search(r"屏幕[^，。；;]{0,16}完全不可见", text):
        return True
    return False


def post_text_inside_direct(text: str) -> bool:
    if "后期叠字" not in text:
        return False
    if re.search(r"后期叠字[：:]\s*[“\"][^”\"]+[”\"]", text):
        return True
    if re.search(r"后期叠字[^。；;\n]{0,18}[“\"][^”\"]+[”\"]", text):
        return True
    if re.search(r"[“\"][^”\"]+[”\"][^。；;\n]{0,18}后期叠字", text):
        return True
    return False


def bubble_quotes(text: str) -> list[str]:
    return [
        match.group(1).strip()
        for match in re.finditer(r"气泡[^。；;\n]{0,45}[“\"]([^”\"]+)[”\"]", text)
        if match.group(1).strip()
    ]


def keyframe_trigger_reasons(direct: str, header: str) -> list[str]:
    reasons: list[str] = []
    has_support_change = (
        any(surface in direct for surface in SUPPORT_SURFACE_TERMS)
        and any(body in direct for body in SUPPORT_BODY_TERMS)
        and any(change in direct for change in SUPPORT_CHANGE_TERMS + KEYFRAME_POSTURE_CHANGE_TERMS)
    )
    if has_support_change:
        reasons.append("人体支撑/姿态变化")
    if any(prop in direct for prop in KEYFRAME_PROP_TERMS) and any(action in direct for action in KEYFRAME_PROP_ACTION_TERMS):
        reasons.append("道具/衣物转移或签字付款")
    if any(term in direct for term in KEYFRAME_UI_TERMS):
        reasons.append("UI/屏幕/绿色气泡")
    if any(term in direct for term in KEYFRAME_SPACE_TERMS):
        reasons.append("门车门/电梯空间穿越")
    if has_reverse_shot(direct) and "复杂" in header:
        reasons.append("复杂正反打")
    if any(term in direct for term in KEYFRAME_CAMERA_TERMS):
        reasons.append("强运镜")
    return reasons


def optional_function_count(block: str) -> int:
    single_fields = (
        "【空间与道具锁定】",
        "【镜头执行】",
        "【口型分窗】",
        "【镜内状态转换】",
        "【剪辑衔接】",
        "【本镜必要约束｜直接复制】",
        "【本镜补充负面提示词｜直接复制】",
    )
    count = sum(bool(extract_optional_field(block, field)) for field in single_fields)
    if extract_optional_field(block, KEYFRAME_IMAGE_FIELD) or extract_optional_field(block, KEYFRAME_VIDEO_FIELD):
        count += 1
    return count


def validate_child(
    group_id: str,
    number: int,
    header: str,
    block: str,
    cast_names: list[str],
    issues: list[str],
) -> None:
    sid = f"{group_id}-{number}"
    if not re.match(rf"^{number}\s*，\s*\d+(?:\.\d+)?s\s*，\s*(普通|复杂)。?$", header):
        issues.append(f"{sid}: 镜号应为“{number}，时长s，普通/复杂。” -> {header}")
    for field in CHILD_FIELDS[1:]:
        if field not in block:
            issues.append(f"{sid}: missing {field}")
    if "【出现人物】" in block:
        issues.append(f"{sid}: cast belongs only at group level")

    direct = direct_prompt(block)
    if not direct:
        issues.append(f"{sid}: missing direct prompt body")
        return
    performance = extract(block, "【表演与声音】", "【状态继承】")
    mouth_window = extract_optional_field(block, "【口型分窗】")
    state = extract_optional_field(block, "【状态继承】")
    quality_control = extract_optional_field(block, QUALITY_CONTROL_FIELD)
    necessary = extract_optional_field(block, "【本镜必要约束｜直接复制】")
    negative = extract_optional_field(block, "【本镜补充负面提示词｜直接复制】")
    keyframe_image = extract_optional_field(block, KEYFRAME_IMAGE_FIELD)
    keyframe_video = extract_optional_field(block, KEYFRAME_VIDEO_FIELD)
    for issue in quality_control_issues(quality_control, direct):
        issues.append(f"{sid}: {issue}")
    optional_count = optional_function_count(block)
    optional_limit = 3 if "复杂" in header else 1
    if optional_count > optional_limit:
        issues.append(
            f"{sid}: 可选字段功能超过预算 -> {optional_count}/{optional_limit}；删除重复字段或拆镜，成对关键帧按1项计"
        )
    negative_terms = [term.strip() for term in re.split(r"[、，,；;\n]+", negative) if term.strip()]
    if len(negative_terms) > 8:
        issues.append(f"{sid}: 本镜补充负面提示词超过8个 -> {len(negative_terms)}")
    if keyframe_image and not keyframe_video:
        issues.append(f"{sid}: {KEYFRAME_IMAGE_FIELD} should pair with {KEYFRAME_VIDEO_FIELD}")
    if keyframe_video and not keyframe_image:
        issues.append(f"{sid}: {KEYFRAME_VIDEO_FIELD} requires {KEYFRAME_IMAGE_FIELD}")
    if keyframe_image and not any(label in keyframe_image for label in ("首帧", "尾帧")):
        issues.append(f"{sid}: {KEYFRAME_IMAGE_FIELD} should include static frame labels such as 首帧/尾帧")
    keyframe_reasons = keyframe_trigger_reasons(direct, header)
    if keyframe_reasons and not (keyframe_image and keyframe_video):
        issues.append(
            f"{sid}: 高风险镜头建议添加成对关键帧字段 -> {','.join(keyframe_reasons)}；若不加关键帧，请拆成更简单的准备/转换/终态镜头"
        )
    if compact_len(direct) > 500:
        issues.append(f"{sid}: direct prompt over 500 chars -> {compact_len(direct)}")
    prefix = direct[:120]
    if not any(term in prefix for term in ASPECT_TERMS):
        issues.append(f"{sid}: direct prompt prefix missing aspect ratio/画幅")
    if not any(term in prefix for term in STYLE_TERMS):
        issues.append(f"{sid}: direct prompt prefix missing visual style")
    if not any(term in prefix for term in SCENE_TONE_PREFIX_TERMS):
        issues.append(f"{sid}: direct prompt prefix missing compressed scene tone/color/light card")
    if not any(term in direct for term in SHOT_SIZE_TERMS):
        issues.append(f"{sid}: direct prompt missing shot size")
    if not any(term in direct for term in CAMERA_TERMS):
        issues.append(f"{sid}: direct prompt missing camera placement or angle")
    if not has_camera_state(direct):
        issues.append(f"{sid}: direct prompt missing static state or one camera path")
    visible_person = has_visible_person(direct, cast_names)
    if visible_person and not any(term in direct for term in RELATION_TERMS):
        issues.append(f"{sid}: visible-person prompt missing body or prop relationship")
    if visible_person and not any(term in direct for term in FACING_TERMS):
        issues.append(f"{sid}: visible-person prompt missing body-facing anchor")
    if re.search(r"(?:身体|上身)朝(?:左|右)(?!侧)", direct):
        issues.append(f"{sid}: body direction must name a person or fixed anchor, not only left/right")
    offscreen_target_hits = offscreen_visual_target_issues(direct, block)
    if offscreen_target_hits:
        issues.append(
            f"{sid}: 画外/不入画人物不能作为面向/视线目标 -> {','.join(offscreen_target_hits)}；改写为画外方向、声源或固定空间锚点"
        )
    needs_visible_count = (
        any(term in direct for term in OFFSCREEN_MARKERS)
        or "画外" in direct
        or any(term in direct for term in ("肩线", "背影", "倒影", "虚化人影"))
        or re.search(r"三人|四人|五人|众人|混混|人群", direct)
    )
    if needs_visible_count and not VISIBLE_COUNT_RE.search(direct + "\n" + extract_optional_field(block, "【本镜必要约束｜直接复制】")):
        issues.append(f"{sid}: 多人/画外/肩线/倒影/虚化人物镜头需要声明本镜画面内可见人数；纯画外声音不计入")
    hand_object_only = bool(re.search(r"(?:只拍|只保留)(?:手部|手和道具|道具|手机|物件|局部)", direct))
    if hand_object_only and re.search(r"中景|中近景|中远景|全景|远景", direct):
        issues.append(f"{sid}: hand/object-only frame conflicts with medium or wide shot size")
    if has_reverse_shot(direct) and "肩线" not in direct:
        issues.append(f"{sid}: shoulder shot should state foreground shoulder line and target")
    if has_reverse_shot(direct) and not re.search(r"身体面向[^，。；;]{1,12}，[^，。；;]{1,12}身体面向", direct):
        issues.append(f"{sid}: shoulder/reverse shot should restate face-to-face body orientation")
    if any(term in direct for term in PROP_TRANSFER_TERMS):
        if ("取出" in direct or "拿出" in direct) and not any(place in direct for place in ("包", "口袋", "桌面", "台面", "手中", "掌中", "外袋")):
            issues.append(f"{sid}: prop appearance needs starting holder/container/surface")
        if any(term in direct for term in ("递", "交给", "接过", "接住", "塞给")):
            if not any(term in direct for term in ("接触", "握住", "接住")) or "松手" not in direct:
                issues.append(f"{sid}: prop transfer needs contact and release chain to prevent flashing")
            if not any(term in direct for term in PROP_CONTINUITY_TERMS):
                issues.append(f"{sid}: prop transfer needs clear final holder/location")
    if any(term in direct for term in ("在身后", "侧后方", "身后半身")) and any(term in direct for term in ("递", "交给", "接过", "接住", "塞给")):
        if not any(term in direct for term in ("转身", "走到", "走近", "面向")):
            issues.append(f"{sid}: recipient behind/side-behind needs repositioning before prop transfer")
    if any(term in direct for term in POSTURE_RISK_TERMS):
        posture_hits = [term for term in POSTURE_STRUCTURE_TERMS if term in direct]
        if len(posture_hits) < 3:
            issues.append(
                f"{sid}: posture action needs physical structure: head/shoulder/waist-hip/legs/feet/support/contact/boundary"
            )
    if any(term in direct for term in GARMENT_RISK_TERMS):
        if not any(term in direct for term in GARMENT_STRUCTURE_TERMS):
            issues.append(f"{sid}: garment action needs clothing start point, hand contact, sleeve/shoulder/hem final state")
    if any(term in direct for term in DOOR_RISK_TERMS):
        if not any(term in direct for term in DOOR_STRUCTURE_TERMS):
            issues.append(f"{sid}: door/car-door action needs handle/contact, open-close direction, side crossing, final door state")
    if any(term in direct for term in UI_RISK_TERMS):
        if not any(term in direct for term in UI_STRUCTURE_TERMS):
            issues.append(f"{sid}: UI/文字需要写清屏幕朝向、模糊界面或后期叠字安全区")
    for field_name, field_text, negative_field in (
        ("【画面描述｜直接复制】", direct, False),
        ("【本镜必要约束｜直接复制】", necessary, False),
        ("【本镜补充负面提示词｜直接复制】", negative, True),
    ):
        for issue in negative_priming_issues(field_text, negative_field=negative_field):
            issues.append(f"{sid}: {field_name} 负向具体概念泄漏 -> {issue}")
    for issue in phone_operation_issues(direct, state, necessary, negative, keyframe_image, keyframe_video):
        issues.append(f"{sid}: 操作型手机朝向风险 -> {issue}")
    for issue in skin_tone_protection_issues(direct):
        issues.append(f"{sid}: 环境色污染肤色风险 -> {issue}")
    for issue in perspective_scale_issues(direct, cast_names):
        issues.append(f"{sid}: 人物透视比例风险 -> {issue}")
    if post_text_inside_direct(direct):
        issues.append(f"{sid}: 后期叠字的具体文字不要写进直接提示词；只预留安全区，具体文字写到【表演与声音】中的后期文字句")
    if "后期叠字" in direct and not any(term in direct for term in ("安全区", "画面左侧", "画面右侧", "贴合屏幕平面", "预留")):
        issues.append(f"{sid}: 后期叠字需要写清安全区/画面侧边/贴合屏幕平面的预留位置")
    screen_invisible = is_screen_invisible_to_camera(direct)
    if screen_invisible and any(term in direct for term in SCREEN_UI_CONTENT_TERMS):
        issues.append(
            f"{sid}: 手机屏幕对镜头不可见，但直接提示词仍描述屏幕/聊天界面；应写干净手机背面 + 侧边二维浮层或后期安全区"
        )
    has_ai_side_bubble = any(term in direct for term in AI_SIDE_BUBBLE_TERMS) and any(term in direct for term in ("安全区", "画面左侧", "画面右侧"))
    if screen_invisible and has_ai_side_bubble:
        if not any(term in direct for term in SIDE_OVERLAY_REQUIRED_TERMS):
            issues.append(
                f"{sid}: 手机屏幕不可见时，AI消息气泡必须声明为独立二维浮层，不能贴在手机上"
            )
        if not any(term in direct for term in ("单条", "一行", "一个", "仅一条", "仅一行")):
            issues.append(f"{sid}: AI消息气泡必须限制为单条/一行短文本")
        bubble_texts = bubble_quotes(direct)
        if bubble_texts and not all(term in direct for term in ("AI画内生成", "允许文字近似")):
            issues.append(f"{sid}: 精确UI默认后期叠加；只有明确写AI画内生成且允许文字近似时才把气泡文字放进直接提示词")
        if len(bubble_texts) > 1:
            issues.append(f"{sid}: 同一镜不应同时生成多条精确气泡文字；请拆成多镜或合并为一个绿色气泡")
        if any(compact_len(text) > 12 for text in bubble_texts):
            issues.append(f"{sid}: 超过12字的精确UI必须改为后期文字，不继续增加AI气泡约束")
        if not all(term in necessary for term in SIDE_OVERLAY_NECESSARY_TERMS):
            issues.append(f"{sid}: AI消息气泡需要【本镜必要约束｜直接复制】声明不属于手机且不贴手机")
        if not any(term in negative for term in SIDE_OVERLAY_NEGATIVE_TERMS):
            issues.append(f"{sid}: AI消息气泡需要【本镜补充负面提示词｜直接复制】压制手机背面文字/气泡贴手机")
    if any(term in direct for term in CROWD_RISK_TERMS):
        if not any(term in direct for term in CROWD_STRUCTURE_TERMS):
            issues.append(f"{sid}: crowd/background characters need region, depth/blur, approach and lip-sync control")
    if keyframe_image and any(term in direct for term in POSTURE_RISK_TERMS):
        keyframe_posture_hits = [term for term in POSTURE_STRUCTURE_TERMS if term in keyframe_image]
        if len(keyframe_posture_hits) < 4:
            issues.append(f"{sid}: posture keyframes should repeat body support/contact structure in each static frame")

    duration_match = re.search(r"，\s*(\d+(?:\.\d+)?)s\s*，", header)
    spoken_chars = sum(len(re.sub(r"\s+", "", line)) for line in re.findall(r"“([^”]+)”", direct))
    if duration_match and spoken_chars:
        duration = float(duration_match.group(1))
        min_duration = spoken_chars / 6.5 + 0.5
        if duration + 0.01 < min_duration:
            issues.append(
                f"{sid}: visible dialogue duration too short -> {duration:g}s for {spoken_chars} chars, need about {min_duration:.1f}s"
            )
    hits = [word for word in BANNED_DIRECT if word in direct]
    if hits:
        issues.append(f"{sid}: banned direct-prompt terms -> {','.join(hits)}")
    bland_hits = [word for word in BLAND_EXPRESSION_TERMS if word in direct]
    if bland_hits:
        issues.append(f"{sid}: bland expression terms need concrete facial/body evidence -> {','.join(bland_hits)}")
    if re.search(r"特写|(?<!中)近景", direct) and re.search(r"三人|四人|五人|众人|所有人|全部人", direct):
        issues.append(f"{sid}: close-up/insert shot overloaded with group cast; split relation shot and close-up")
    has_visible_emotion = any(word in direct for word in ("皱眉", "眼神", "委屈", "紧张", "焦虑", "愣", "僵", "怒", "冷", "慌", "压低", "哽", "红"))
    if has_visible_emotion and not any(word in direct for word in FACIAL_DETAIL_TERMS + BODY_PROP_EMOTION_TERMS):
        issues.append(f"{sid}: emotion needs readable facial/body/prop evidence matched to shot size")
    if has_visible_emotion and re.search(r"全景|远景|中远景", direct) and any(word in direct for word in ("眼睑", "眉尾", "嘴角", "下颌", "喉咙", "唇")):
        issues.append(f"{sid}: wide shot uses tiny facial details; use body/distance/prop evidence or cut closer")
    direct_quotes = set(quoted_lines(direct))
    for line in visible_dialogue_quotes(performance) + visible_dialogue_quotes(mouth_window):
        if line not in direct_quotes:
            issues.append(f"{sid}: visible dialogue must appear in direct prompt by default -> “{line}”")
    for line in post_audio_format_issues(performance) + post_audio_format_issues(mouth_window):
        issues.append(f"{sid}: OS/OV/系统音文本必须使用 标签：“...” 格式 -> {line}")
    if is_standalone_cutaway(direct):
        handoff = extract_optional_field(block, "【剪辑衔接】")
        in_place_focus = any(word in direct for word in ("焦点从", "焦点落到", "拉焦", "转焦"))
        if not handoff and not in_place_focus:
            issues.append(f"{sid}: standalone cutaway needs 【剪辑衔接】 with independent-generation sound bridge")

    state_change = extract_optional_field(block, "【镜内状态转换】")
    if state_change:
        for label in ("终态直投句", "尾帧直投句"):
            sentence = direct_sentence(state_change, label)
            if not sentence:
                issues.append(f"{sid}: 【镜内状态转换】 missing {label}")
            elif sentence not in direct:
                issues.append(f"{sid}: {label} must appear verbatim in direct prompt -> {sentence}")

    camera_execution = extract_optional_field(block, "【镜头执行】")
    if mouth_window:
        priority = "优先级：口型 > 听者反应 > 运镜"
        if priority not in mouth_window:
            issues.append(f"{sid}: 【口型分窗】 missing dialogue priority declaration")
        if camera_execution and re.search(r"推|拉|移|摇|跟拍|环绕|转焦|拉焦", camera_execution):
            if not any(term in mouth_window for term in ("听者保持", "听者不动", "听者静止", "仅呼吸", "仅视线")):
                issues.append(f"{sid}: lip-sync with camera move needs listener hold declaration in 【口型分窗】")
    high_risk_count = sum(
        bool(condition)
        for condition in (
            re.search(r"三人|四人|五人|众人|混混|人群", direct),
            any(term in direct for term in PROP_TRANSFER_TERMS + CONTACT_TERMS),
            bool(direct_quotes),
            has_camera_move(direct),
            any(term in direct for term in MOVE_TERMS),
            any(term in direct for term in ("车", "人群", "闪回", "回忆", "梦境")),
        )
    )
    if high_risk_count >= 4:
        issues.append(f"{sid}: possible single-shot overload; split or simplify high-risk tasks")
    action_chain_hits = [term for term in ACTION_CHAIN_TERMS if term in direct]
    if len(action_chain_hits) >= 5 and not (keyframe_image and keyframe_video):
        issues.append(
            f"{sid}: long action chain may be simplified by AI; split into prepare/contact/final-state shots -> {','.join(action_chain_hits[:8])}"
        )
    semantic_report = build_semantic_report(direct, header, performance, block, cast_names)
    if semantic_report.missing_slots:
        issues.append(
            f"{sid}: direct prompt semantic contract incomplete -> {','.join(semantic_report.missing_slots)}"
        )


def camera_signature(direct: str) -> str:
    size = next((term for term in SHOT_SIZE_TERMS if term in direct), "")
    angle = next((term for term in CAMERA_SIGNATURE_ANGLE_TERMS if term in direct), "")
    moving = has_camera_move(direct)
    parts = [size]
    if angle:
        parts.append(angle)
    parts.append("move" if moving else "static")
    return ":".join(parts)


def composition_family(direct: str) -> str:
    """Return the explicit composition family; do not infer one from vague beauty words."""
    for family, terms in COMPOSITION_FAMILY_TERMS:
        if any(term in direct for term in terms):
            return family
    return ""


def group_camera_signature(direct: str) -> str:
    """Signature used only for cross-group variety checks."""
    family = composition_family(direct)
    if not family:
        return ""
    return f"{camera_signature(direct)}:{family}"


def terminal_frame_issues(direct: str, group_id: str, child_index: int) -> list[str]:
    """Require positive terminal facts that prevent end-of-shot duplication and drift."""
    issues: list[str] = []
    if not any(term in direct for term in TERMINAL_STABILITY_TERMS):
        issues.append(f"{group_id}-{child_index}: 最后一镜缺少最后20%终端稳定事实（停稳/落幅/保持到结束）")
        return issues
    if not any(term in direct for term in TERMINAL_ANTI_DUPLICATE_TERMS):
        issues.append(f"{group_id}-{child_index}: 最后一镜缺少不新增/不重复主体的正向事实")
    is_cutaway = is_standalone_cutaway(direct)
    zero_people = bool(re.search(r"可见人数[：:]\s*[0零]人", direct))
    if not is_cutaway and not zero_people:
        if not VISIBLE_COUNT_RE.search(direct):
            issues.append(f"{group_id}-{child_index}: 最后一镜人物镜必须写可见人数")
        if not any(term in direct for term in SLOT_TERMS):
            issues.append(f"{group_id}-{child_index}: 最后一镜人物镜必须写最终人物槽位/站位")
        if not any(term in direct for term in TERMINAL_SEPARATION_TERMS):
            issues.append(f"{group_id}-{child_index}: 最后一镜多人/人物镜必须写脸、手、四肢边界分开")
    return issues


def shoulder_actor(direct: str) -> str:
    match = REVERSE_SHOT_RE.search(direct)
    return match.group(1).strip() if match else ""


def orientation_jump(prev_state: str, next_direct: str) -> bool:
    if not prev_state or not next_direct:
        return False
    if not any(term in prev_state for term in ORIENTATION_LOCK_TERMS):
        return False
    if any(term in next_direct for term in ORIENTATION_TURN_TERMS):
        return False
    next_demands_new_facing = (
        ("身体面向" in next_direct and not any(term in next_direct for term in ORIENTATION_LOCK_TERMS))
        or "面对面" in next_direct
        or has_reverse_shot(next_direct)
        or any(term in next_direct for term in ("开口", "接过", "接住", "递", "交给"))
    )
    return next_demands_new_facing


def prop_contexts(text: str) -> dict[str, str]:
    contexts: dict[str, str] = {}
    for prop in TRACKED_PROPS:
        if prop == "卡" and any(longer in text for longer in ("银行卡", "卡片")):
            continue
        if prop not in text:
            continue
        for match in re.finditer(re.escape(prop), text):
            start = max(0, match.start() - 18)
            end = min(len(text), match.end() + 22)
            context = text[start:end]
            if any(hint in context for hint in PROP_STATE_HINTS):
                contexts[prop] = re.sub(r"\s+", "", context)
                break
    return contexts


def prop_state_jump(prev_state: str, next_direct: str) -> list[str]:
    if not prev_state or not next_direct:
        return []
    prev_props = prop_contexts(prev_state)
    next_props = prop_contexts(next_direct)
    if not prev_props or not next_props:
        return []
    has_visible_transfer = any(term in next_direct for term in PROP_TRANSFER_CHAIN_TERMS)
    jumps: list[str] = []
    for prop, prev_context in prev_props.items():
        next_context = next_props.get(prop)
        if not next_context or prev_context == next_context:
            continue
        if set(hint for hint in STRONG_PROP_STATE_HINTS if hint in prev_context) & set(
            hint for hint in STRONG_PROP_STATE_HINTS if hint in next_context
        ):
            continue
        if has_visible_transfer:
            continue
        jumps.append(prop)
    return jumps


def has_body_support_detail(text: str) -> bool:
    if not text:
        return False
    has_surface = any(term in text for term in SUPPORT_SURFACE_TERMS)
    body_hits = [term for term in SUPPORT_BODY_TERMS if term in text]
    has_contact = any(term in text for term in SUPPORT_CONTACT_TERMS)
    return has_surface and has_contact and len(body_hits) >= 2


def posture_support_jump(prev_state: str, next_direct: str) -> bool:
    if not prev_state or not next_direct:
        return False
    if not has_body_support_detail(prev_state):
        return False
    shared_surface = [term for term in SUPPORT_SURFACE_TERMS if term in prev_state and term in next_direct]
    if not shared_surface:
        return False
    if any(term in next_direct for term in SUPPORT_CHANGE_TERMS):
        return False
    next_body_hits = [term for term in SUPPORT_BODY_TERMS if term in next_direct]
    next_has_contact = any(term in next_direct for term in SUPPORT_CONTACT_TERMS)
    generic_reset = bool(GENERIC_SUPPORT_RE.search(next_direct))
    if generic_reset and (len(next_body_hits) < 2 or not next_has_contact):
        return True
    prev_key_body = [term for term in ("臀", "腰", "腰臀", "肩背", "背部", "腿") if term in prev_state]
    missing_key_body = [term for term in prev_key_body if term not in next_direct]
    if len(prev_key_body) >= 2 and len(missing_key_body) >= 2 and generic_reset:
        return True
    return False


def validate(path: Path, text: str | None = None) -> list[str]:
    if text is None:
        text = path.read_text(encoding="utf-8")
    issues: list[str] = []
    raw_group_headings = re.findall(r"^####\s+([^\n]*镜头组总时长[^\n]*)$", text, re.M)
    valid_group_heading = re.compile(r"S\d+-\d+｜镜头组总时长：\d+(?:\.\d+)?s")
    for raw_heading in raw_group_headings:
        heading = raw_heading.strip()
        if not valid_group_heading.fullmatch(heading):
            issues.append(
                f"invalid shot group heading -> #### {heading}; use S1-01 without file/case prefix"
            )
    for section in REQUIRED_TOP_SECTIONS:
        if section not in text:
            issues.append(f"missing top section {section}")
    internal_hits = [term for term in INTERNAL_PRESET_TERMS if term in text]
    if internal_hits:
        issues.append("final output should not expose internal scene-preset terms -> " + ",".join(internal_hits))
    global_section = extract_top_section(text, "## 全局锁定")
    quality_section = extract_top_section(text, "## 制作质量总控")
    global_negative_section = extract_top_section(text, "## 通用负面提示词｜直接复制")
    scene_state_section = extract_top_section(text, "## 场景状态表")
    for label in GLOBAL_QUALITY_LABELS:
        value = labeled_control_value(quality_section, label)
        if len(value) < 8:
            issues.append(f"## 制作质量总控 missing executable {label}")
        elif any(term in value for term in ("已检查", "按合同", "同上", "见内部", "待定", "TBD")):
            issues.append(f"## 制作质量总控 {label} cannot be an internal placeholder")
    if GLOBAL_SCALE_LOCK_TITLE not in global_section:
        issues.append(f"## 全局锁定 missing {GLOBAL_SCALE_LOCK_TITLE}")
    else:
        missing_scale_terms = [term for term in GLOBAL_SCALE_LOCK_TERMS if term not in global_section]
        if missing_scale_terms:
            issues.append(f"{GLOBAL_SCALE_LOCK_TITLE} lacks scale/grounding facts -> {','.join(missing_scale_terms)}")
    missing_scale_negatives = [term for term in GLOBAL_SCALE_NEGATIVE_TERMS if term not in global_negative_section]
    if missing_scale_negatives:
        issues.append("## 通用负面提示词 missing scale/perspective risks -> " + ",".join(missing_scale_negatives))
    for issue in negative_priming_issues(global_negative_section, negative_field=True):
        issues.append(f"通用负面提示词存在具体领域概念泄漏 -> {issue}")
    if COLOR_CARD_TITLE not in global_section:
        issues.append(f"## 全局锁定 missing {COLOR_CARD_TITLE}")
    else:
        missing_color_terms = [term for term in COLOR_CARD_REQUIRED_TERMS if term not in global_section]
        if missing_color_terms:
            issues.append(f"{COLOR_CARD_TITLE} lacks production-level fields -> {','.join(missing_color_terms)}")
    if "影调色卡句" not in scene_state_section:
        issues.append("## 场景状态表 missing per-scene 影调色卡句")
    if has_sound_text(text):
        if VOICE_LOCK_TITLE not in global_section:
            issues.append(f"dialogue/OS/OV present but ## 全局锁定 missing {VOICE_LOCK_TITLE}")
        else:
            missing_voice_terms = [term for term in VOICE_LOCK_REQUIRED_TERMS if term not in global_section]
            if missing_voice_terms:
                issues.append(f"{VOICE_LOCK_TITLE} lacks voice identity fields -> {','.join(missing_voice_terms)}")
        if "角色声音使用" not in scene_state_section:
            issues.append("## 场景状态表 missing 角色声音使用 for this scene")

    group_count = child_count = 0
    groups = list(iter_groups(text))
    previous_group_number: tuple[int, int] | None = None
    previous_group_last_state = ""
    previous_group_scene: int | None = None
    scene_group_records: list[tuple[int, str, list[str]]] = []
    for match in groups:
        group_count += 1
        group_id, group_total, block = match.group(1), match.group(2), match.group(3)
        if group_count == 1 and group_id != "S1-01":
            issues.append(f"{group_id}: 每个独立Markdown文件的首个镜头组必须为S1-01，不添加文件/案例前缀")
        scene_number, beat_number = (int(part) for part in group_id[1:].split("-"))
        current_group_number = (scene_number, beat_number)
        if previous_group_number is not None:
            previous_scene, previous_beat = previous_group_number
            follows_same_scene = current_group_number == (previous_scene, previous_beat + 1)
            starts_next_scene = current_group_number == (previous_scene + 1, 1)
            if not (follows_same_scene or starts_next_scene):
                issues.append(
                    f"{group_id}: 镜头组编号跳号或重复；同场景应连续递增，新场景应从S{previous_scene + 1}-01开始"
                )
        previous_group_number = current_group_number
        if group_total is None:
            issues.append(f"{group_id}: group heading must include summed duration -> #### {group_id}｜镜头组总时长：Xs")
        before_first_child = block.split("【镜号】", 1)[0]
        cast = extract_optional_field(before_first_child, "【出现人物】")
        if not cast:
            issues.append(f"{group_id}: missing group-level 【出现人物】")
        for line in [x.strip() for x in cast.splitlines() if x.strip()]:
            if any(sep in line for sep in "、，；;"):
                issues.append(f"{group_id}: cast line should contain one visible character/group only -> {line}")
        cast_names = group_cast_names(cast)
        children = list(iter_children(block))
        if not children:
            issues.append(f"{group_id}: no child shots found")
        for expected_number, child in enumerate(children, start=1):
            child_count += 1
            validate_child(group_id, expected_number, child.group(1).strip(), child.group(0), cast_names, issues)
        child_directs = [
            direct_prompt(child.group(0))
            for child in children
        ]
        scene_group_records.append((scene_number, group_id, child_directs))
        child_states = [
            extract(child.group(0), "【状态继承】")
            for child in children
        ]
        if child_directs and previous_group_last_state and previous_group_scene == scene_number:
            first_direct = child_directs[0]
            if orientation_jump(previous_group_last_state, first_direct):
                issues.append(
                    f"{group_id}-1: 同场景跨镜头组朝向跳变；新组首镜必须重写转身/回身/肩线转正/双脚停稳"
                )
            jumped_props = prop_state_jump(previous_group_last_state, first_direct)
            if jumped_props:
                issues.append(
                    f"{group_id}-1: 同场景跨镜头组物品状态不一致 -> {','.join(jumped_props)}"
                )
            if posture_support_jump(previous_group_last_state, first_direct):
                issues.append(
                    f"{group_id}-1: 同场景跨镜头组人体支撑点未在首镜重写"
                )
        for index in range(1, len(children)):
            if orientation_jump(child_states[index - 1], child_directs[index]):
                issues.append(
                    f"{group_id}-{index + 1}: 上一镜状态为背向/侧身/面向固定物，下一镜改变朝向前必须写转身/回身/肩线转正/双脚停稳"
                )
            jumped_props = prop_state_jump(child_states[index - 1], child_directs[index])
            if jumped_props:
                issues.append(
                    f"{group_id}-{index + 1}: 上一镜物品状态与下一镜开头不一致，{','.join(jumped_props)} 改变归属/位置前必须写取出/接触/移动/松手/稳定终态"
                )
            if posture_support_jump(child_states[index - 1], child_directs[index]):
                issues.append(
                    f"{group_id}-{index + 1}: 上一镜人体支撑点已锁定，下一镜不能概括成坐在中间/坐着/靠着；必须复写臀部/腰背/双腿与承载物接触点，或先写手撑、脚踩、腰臀挪动、重心转移和新支撑点稳定"
                )
        if child_states:
            previous_group_last_state = child_states[-1]
            previous_group_scene = scene_number
        child_durations = []
        for child in children:
            duration_match = re.search(r"，\s*(\d+(?:\.\d+)?)s\s*，", child.group(1))
            if duration_match:
                child_durations.append(float(duration_match.group(1)))
        if group_total is not None and child_durations:
            summed = sum(child_durations)
            if abs(float(group_total) - summed) > 0.01:
                issues.append(f"{group_id}: group duration {float(group_total):g}s != child sum {summed:g}s")
        signatures = []
        for child in children:
            direct = direct_prompt(child.group(0))
            signatures.append(camera_signature(direct))
        for index in range(2, len(signatures)):
            if signatures[index] == signatures[index - 1] == signatures[index - 2] and signatures[index].endswith(":static"):
                issues.append(f"{group_id}: three consecutive identical static camera tasks -> {signatures[index]}")
        shoulder_actors = [
            shoulder_actor(direct_prompt(child.group(0)))
            for child in children
        ]
        for index in range(1, len(shoulder_actors)):
            if shoulder_actors[index - 1] and shoulder_actors[index] and shoulder_actors[index - 1] == shoulder_actors[index]:
                issues.append(f"{group_id}: consecutive shoulder shots use same shoulder actor; reverse shot should swap foreground shoulder")

    # Scene-level camera variety: compare the first child of adjacent groups so a
    # sequence cannot hide three repeated compositions behind different group headings.
    for index in range(2, len(scene_group_records)):
        a_scene, a_id, a_directs = scene_group_records[index - 2]
        b_scene, b_id, b_directs = scene_group_records[index - 1]
        c_scene, c_id, c_directs = scene_group_records[index]
        if a_scene != b_scene or b_scene != c_scene:
            continue
        signatures = [
            group_camera_signature(directs[0]) if directs else ""
            for directs in (a_directs, b_directs, c_directs)
        ]
        if signatures[0] and signatures[0] == signatures[1] == signatures[2]:
            issues.append(
                f"{c_id}: 同场连续三组复用同一景别+角度+构图+运镜组合 -> {signatures[2]}；需改为建立/关系/细节/余波中的不同视觉任务"
            )

    # The last visible shot of every scene needs a positive terminal contract.
    scene_last: dict[int, tuple[str, list[str]]] = {}
    for scene_number, group_id, directs in scene_group_records:
        scene_last[scene_number] = (group_id, directs)
    for scene_number, (group_id, directs) in scene_last.items():
        if directs:
            issues.extend(terminal_frame_issues(directs[-1], group_id, len(directs)))

    if group_count == 0:
        issues.append("no shot groups found; use #### S1-01 with group-level 【出现人物】 and no file/case prefix")
    if child_count == 0:
        issues.append("no child shots found")
    return issues


def shadow_validate(path: Path, text: str | None = None) -> list[str]:
    """Report shot profiles and hard-minimum/semantic disagreements without failing validation."""
    if text is None:
        text = path.read_text(encoding="utf-8")
    diagnostics: list[str] = []
    for match in iter_groups(text):
        group_id, block = match.group(1), match.group(3)
        before_first_child = block.split("【镜号】", 1)[0]
        cast_names = group_cast_names(extract_optional_field(before_first_child, "【出现人物】"))
        group_directs: list[str] = []
        for number, child in enumerate(iter_children(block), start=1):
            child_block = child.group(0)
            direct = direct_prompt(child_block)
            if not direct:
                continue
            group_directs.append(direct)
            report = build_semantic_report(
                direct=direct,
                header=child.group(1).strip(),
                performance=extract(child_block, "【表演与声音】", "【状态继承】"),
                block=child_block,
                cast_names=cast_names,
            )
            semantic_state = "complete" if report.semantically_complete else "missing=" + ",".join(report.missing_slots)
            diagnostics.append(
                f"SHADOW {group_id}-{number}: type={report.shot_type}/{report.label}; "
                f"length={report.length}; guide={report.recommended_min}-{report.recommended_max}; "
                f"semantic={semantic_state}; length_guidance={report.length_guidance}; "
                f"disagreement={report.disagreement}"
            )
        for family, patterns in LIVENESS_PATTERN_FAMILIES.items():
            count = sum(any(re.search(pattern, direct) for pattern in patterns) for direct in group_directs)
            if count >= 3:
                diagnostics.append(
                    f"SHADOW {group_id}: liveness_family_repeat={family}/{count}; "
                    "replace repeated decoration with source-driven action, light, material, or environment response"
                )
    return diagnostics


def bundle_contract_issues(items: list[tuple[Path, str]]) -> list[str]:
    """Check project locks that must remain identical across scene files."""
    if len(items) < 2:
        return []
    issues: list[str] = []
    first_path, first_text = items[0]
    sections = ("## 全局锁定", "## 制作质量总控", "## 通用负面提示词｜直接复制")
    for section in sections:
        baseline = re.sub(r"\s+", "", extract_top_section(first_text, section))
        for path, text in items[1:]:
            current = re.sub(r"\s+", "", extract_top_section(text, section))
            if baseline != current:
                issues.append(
                    f"{path}: {section} 与 {first_path} 不一致；多场景文件必须复用同一项目锁定"
                )
    return issues


def main(argv: list[str]) -> int:
    shadow_report = "--shadow-report" in argv[1:]
    raw_paths = [arg for arg in argv[1:] if arg != "--shadow-report"]
    unknown_options = [arg for arg in raw_paths if arg.startswith("-")]
    if not raw_paths or unknown_options:
        print("usage: validate_storyboard.py [--shadow-report] <file.md> [more.md ...]", file=sys.stderr)
        return 2
    failed = False
    items = [(Path(raw), Path(raw).read_text(encoding="utf-8")) for raw in raw_paths]
    bundle_issues = bundle_contract_issues(items)
    if bundle_issues:
        print("PROJECT: FAIL")
        for issue in bundle_issues:
            print(f"  - {issue}")
        failed = True
    for path, text in items:
        issues = validate(path, text)
        print(f"{path}: {'OK' if not issues else 'FAIL'}")
        for issue in issues:
            print(f"  - {issue}")
        if shadow_report:
            for diagnostic in shadow_validate(path, text):
                print(f"  ~ {diagnostic}")
        failed = failed or bool(issues)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

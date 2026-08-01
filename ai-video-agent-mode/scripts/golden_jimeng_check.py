#!/usr/bin/env python3
"""Regression checks for neutral Jimeng prompt exemplars and quality cases."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from prompt_contract import cinematic_realism_prompt_issues, direct_copy_prompt_issues, video_texture_contract_issues


REQUIRED = ("生成规格：", "主体与空间锁定：", "主镜头连续规则：", "子镜头组：", "光照、声音与稳定约束：")
FORBIDDEN = ("画面锁定：", "镜头设计：", "表演时间轴：", "光照与声音：", "轴线：", "越轴", "OTS", "反打", "reference_assets", "i2v", "r2v")
ABSTRACT_ONLY_TERMS = ("高级感", "电影感", "质感很好", "光影高级")
QUALITY_CASES = [
    {
        "name": "lived_in_scene_depth_card",
        "prompt": "16:9画幅，写实电影级都市情感短剧，雨后傍晚的旧公寓客厅。前景窗帘边和木桌角轻度焦外形成柔和框景，中景人物坐在有自然褶皱的布沙发旁，杯垫水印与半合文件构成真实生活接触区；后景开放式厨房和走廊门在低对比暖灰空气层中退后，只有一盏冰箱小灯与远处窗外城市散光。焦平面稳定落在人物脸侧和活动手，背景不出现清晰人脸或第二事件，暖灯与阴天窗光自然分离。",
    },
    {
        "name": "dialogue_listener_reaction",
        "prompt": "16:9画幅，动态漫，冷白顶灯下的场景A长桌空间。角色A在画面左侧中近景低声说话，口型同步；角色B在右侧轻度虚焦，视线停在角色A脸上，手指压住杯沿不抢焦。4300K顶灯从上方落下，角色A手背受光，杯沿有浅反光，背景弱虚化，落幅两人距离保持。",
    },
    {
        "name": "dialogue_speaker_pressure",
        "prompt": "16:9画幅，动态漫，暖白窗光斜落的场景A门口。角色A站在画面右前，身体朝左，说完最后半句后呼吸短停，口型闭合；角色B只以左肩线入前景虚化，不出现可辨认五官。窗光照亮角色A脸侧和门把，门框投下浅阴影，墙面纹理保持低饱和，落幅手仍停在门边不复位。",
    },
    {
        "name": "two_person_confrontation",
        "prompt": "16:9画幅，动态漫，低饱和青灰影调的场景A走廊。角色A在画面左中景面向右，角色B在画面右中景面向左，二人之间留出半步空隙，均不越过画面中线；角色A抬眼停半拍，角色B下颌轻收不说话。走廊顶灯从后上方压下，脸侧受光，地面有浅反光，背景门牌虚化。",
    },
    {
        "name": "prop_transfer",
        "high_risk": True,
        "prompt": "16:9画幅，动态漫，冷白顶灯下的场景A桌边。手机起幅在桌面右前角，角色A右手从身侧伸向手机，指尖接触边缘后拿起并递向画面右侧，角色B手掌在中段接住，二人视线都落在手机交接点，落幅手机稳定在角色B右手。顶灯照亮手背和手机玻璃，桌面留下浅阴影，背景弱虚化。",
        "constraint": "手机只从桌面右前角移动到角色B右手；必须出现伸向、指尖接触、递出、接住、落定五段。",
        "negative": "手指错位，手机漂移，物体消失，手部穿插，光影突变",
    },
    {
        "name": "phone_ui_overlay",
        "high_risk": True,
        "prompt": "16:9画幅，动态漫，夜间冷白灯箱光下的场景A柜台。角色A把手机放在柜台边，身体不前扑，画面右侧出现聊天消息绿色气泡，文字为独立二维浮层，位于右侧安全区，不贴手机背面，不跟随手机透视；角色A视线压在气泡方向。灯箱光照亮手机玻璃边缘，柜台有低亮反光。",
        "constraint": "UI文字只作为右侧安全区二维浮层，不遮挡人物脸部和口型，不贴手机屏幕透视。",
        "negative": "乱码文字，文字贴脸，透视错误，手机背面出字，水印",
    },
    {
        "name": "single_action_chain",
        "prompt": "16:9画幅，动态漫，暖光门廊灯下的场景A入口。角色A从画面左侧迈向门口，先抬手靠近门把，指尖贴住金属后下压，门只开出一条窄缝，没有直接冲出门外，落幅角色A重心停在门边。暖光门廊灯从右上方照亮手腕，金属门把有细窄高光，墙面浅阴影保持稳定不跳变。",
    },
    {
        "name": "environment_pressure",
        "prompt": "16:9画幅，动态漫，雨夜蓝灰色场景A空走廊。画面无人，门在右后方半掩，地面积水沿门缝延出一条亮线，远处灯牌低频闪烁但不改变主光，空间压力只来自半掩门和水痕。冷白顶灯从中后方落下，水面有细碎反光，墙皮材质粗糙，背景深处虚化，落幅门缝亮线保持。",
    },
    {
        "name": "multi_person_blocking",
        "high_risk": True,
        "prompt": "16:9画幅，动态漫，冷白会议灯下的场景A长桌。角色A在画面左侧中景面向右，角色B在右侧中景面向左，角色C在中后方桌后只作观察反应，不穿过A与B之间空间线；角色A把文件推到桌中央后停手。顶灯照亮文件纸面和两人手背，桌沿浅反光，背景人物弱虚化。",
        "constraint": "保持A左、B右、C中后方；C只观察不抢焦，文件只在桌中央活动区移动。",
        "negative": "人物换位，多人抢焦，文件消失，手部穿插，空间线穿越",
    },
    {
        "name": "os_closed_lip",
        "prompt": "16:9画幅，动态漫，低暖光床头灯下的场景A室内。角色A坐在画面左前侧，OS内心声出现时嘴唇闭合，视线落向桌上纸条，手指只压住纸角不移动；画面无新增说话人口型，也无画外实体人物入画。暖光床头灯从左后方照亮脸侧和纸面，纸张纤维有浅阴影，背景窗帘虚化。",
    },
    {
        "name": "object_insert",
        "prompt": "16:9画幅，动态漫，冷白顶灯下的场景A桌面特写。文件角位于画面中央偏右，角色A手指停在画面左下边缘，不翻页不拿起，文件下方露出半行被遮住的标记，新增信息只来自纸角露出。顶灯照亮纸面纤维，桌面有低亮反光，背景人物完全焦外，落幅文件仍压在桌面。",
    },
    {
        "name": "phone_game_functional_surface_lock",
        "high_risk": True,
        "prompt": "16:9画幅，写实电影级动态漫短剧，暖白客厅侧光下。男孩坐在画面左侧中近景，手机屏幕始终朝向男孩本人，视线落在屏幕中心；摄影机位于手机背壳外侧，只见深色背壳与侧边框。男孩双手横握手机左右短边，双拇指在屏幕内侧低幅点按，屏幕冷光映亮眼睑和指尖；手机横屏方向稳定，背壳持续朝向摄影机。暖白侧光从画面右上方照亮手背和手机边框短反光，背景沙发织物弱虚化。",
        "constraint": "手机屏幕朝男孩本人，背壳与侧边框朝摄影机；双手握持、拇指操作和屏幕光共同证明人物在玩游戏。",
        "negative": "手机方向跳变，握持错位，手指穿插，屏幕内容乱码，手机漂移，人物直视镜头",
    },
    {
        "name": "release_after_peak",
        "prompt": "16:9画幅，动态漫，雨后中性路灯下的场景A街边。角色A在画面右侧中近景松开攥紧的钥匙，钥匙没有掉落，只在掌心转松，肩线从紧绷降到稳定；角色B在左侧后景闭口停住，视线没有追问。路灯从右上方打亮角色A手心，钥匙金属有短高光，湿地面浅反光，背景车灯虚化。",
    },
    {
        "name": "mixed_dialogue_prop",
        "high_risk": True,
        "prompt": "16:9画幅，动态漫，冷白办公室灯下的场景A桌边。角色A在画面左侧说出一句短台词，口型同步，同时把银行卡从桌面中央推到画面右侧；角色B先看角色A眼睛，再低头看卡，手停在卡前未立刻接走。顶灯照亮卡面和角色A手背，桌面有浅反光，背景资料柜虚化。",
        "constraint": "台词口型与推卡动作不抢同一瞬间；银行卡从桌面中央滑到右侧，角色B未接走。",
        "negative": "卡片漂移，口型错位，手部穿插，道具消失，背景抢焦",
    },
    {
        "name": "visible_gate_offscreen_voice",
        "high_risk": True,
        "prompt": "9:16画幅，写实电影级动态漫短剧，冷白会议室门口。本镜画面内可见人数：1人；林夏清晰入画，顾辰仅为门外右侧画外声源不入画。林夏中近景停在桌边，视线压向右侧门口声源，嘴唇闭合听完后手指扣住文件夹边缘。顶部冷白灯照亮脸侧和纸面，门框投下浅阴影，背景资料柜弱虚化。",
        "constraint": "顾辰只能作为门外右侧画外声源，不生成实体人物；林夏不得看向不可见的顾辰脸部。",
        "negative": "凭空新增人物，画外人入画，多人抢焦，人物脸部漂移，光影突变",
    },
    {
        "name": "visible_gate_shoulder_foreground",
        "high_risk": True,
        "prompt": "16:9画幅，写实电影级动态漫短剧，暖灰柜台空间。本镜画面内可见人数：2人；角色A清晰实焦，角色B只以前景左侧肩线弱虚化入画，不出现可辨认五官。角色A在右侧中近景把钥匙压在柜台边，肩线后方没有新增动作。暖白灯从右上方擦亮角色A手背和钥匙金属，柜台旧划痕有低亮反光，背景灯箱柔散虚化。",
        "constraint": "角色B仅保持前景肩线虚化，不升级为清晰人物或抢焦；钥匙始终在柜台边。",
        "negative": "前景肩线变成完整人物，人物抢焦，钥匙漂移，手部穿插，塑料材质",
    },
    {
        "name": "car_interior_texture",
        "prompt": "16:9画幅，写实电影级动态漫短剧，夜间车内。角色A在驾驶位中近景，焦平面落在眼下和方向盘上沿，侧窗雨痕与后座只作焦外层次。仪表暖光压在手背和皮肤纹理上，车外冷蓝路灯在湿玻璃上形成断续反光，暗部保留黑位，高光不越过仪表边缘，座椅织物和玻璃水痕保持不均匀细节。",
    },
    {
        "name": "hospital_texture",
        "prompt": "9:16画幅，写实电影级动态漫短剧，医院走廊。角色A站在画面右侧中景，前景病床栏杆轻虚化，焦平面落在角色A手背和胸牌边缘。冷白顶灯均匀但不冲白墙，金属扶手只留低反光，肤色保留暖灰层次；瓷砖缝和磨损墙角可见，背景门牌虚化，落幅角色A手仍停在栏杆旁。",
    },
    {
        "name": "street_texture",
        "prompt": "16:9画幅，写实电影级动态漫短剧，夜间商业街。角色A在画面左前三分之一中近景，暖橙店铺光从左上方落在脸侧，远处路人只作低细节焦外流动，不抢主体。雨后地面把店招压成断续反光，衣料褶皱和门店玻璃细小水汽可见，暗部黑位收住，车灯高光不过曝，落幅角色A视线保持在右侧店门。",
    },
    {
        "name": "micro_emotion_disappointed",
        "prompt": "16:9画幅，动态漫，冷白顶灯下的场景A长桌。角色A在画面右侧中近景，听完对方沉默后先垂眸半秒，再缓慢抬眼，眼神从受伤转为疏冷，嘴角轻压住，很轻地说出一句台词后移开视线；右手指尖停在文件夹边缘不再前推。顶灯照亮角色A脸侧和纸面，文件夹边缘有低亮反光，背景弱虚化。",
    },
    {
        "name": "micro_emotion_grief_restraint",
        "prompt": "9:16画幅，写实电影级动态漫短剧，低暖床头灯下的场景A室内。角色A坐在画面左前侧中近景，下颌发紧轻颤，肩颈收住，闭眼低头后抬臂遮住眼睛，借手臂克制擦掉眼角泪痕，身体随一次短促呼吸细微发颤。暖光从左后方照亮脸侧和手背，纸张纤维有浅阴影，背景窗帘柔和虚化。",
    },
    {
        "name": "performance_baseline_cold_restraint",
        "prompt": "16:9画幅，写实电影级动态漫短剧，冷白会议室长桌。角色A保持克制冷感表演基线，听见关键词后眼神停半拍，下颌轻收，右手指腹压住文件夹边缘，开口时音量仍低；角色B只以前景肩线弱虚化闭口入画。顶部冷白灯照亮角色A脸侧和纸面，文件夹硬边有低亮反光，落幅角色A视线仍停在桌对面方向。",
    },
    {
        "name": "premium_director_polish_card",
        "prompt": "9:16画幅，写实电影级动态漫短剧，低饱和青灰审讯室，冷白顶灯压住黑位。本镜画面内可见人数：2人；角色A在画面右侧中近景实焦，角色B只以前景左肩线虚化入画。角色A说到关键词时口型同步、下颌轻收，句末闭口后手指仍按在录音笔边缘。顶灯照亮脸侧、手背和金属录音笔短反光，背景墙面旧痕虚化，落幅两人距离不变。",
    },
    {
        "name": "dialogue_performance_kernel_card",
        "prompt": "16:9画幅，动态漫，暖白窗光下的场景A书桌。角色A在左侧中近景说出一句质问，口型同步；说到最后两个字时呼吸短停，手指停在信封封口。角色B在右后方闭口听着，眼神先落到角色A脸上再低看信封，不抢焦。窗光照亮信封纸面和角色A手背，桌面浅反光，背景书架弱虚化，落幅信封仍未递出。",
    },
    {
        "name": "dialogue_subtext_stress_card",
        "prompt": "16:9画幅，写实电影级动态漫短剧，冷白窗光下的办公室书桌。角色A在画面左侧中近景说出“你根本没有回来。”，口型同步；说到“根本”时压低音量、下颌收紧，右手指腹停在信封封口。角色B在右后景闭口，延迟半拍才把视线从角色A移到信封。固定机位守住两人之间的桌面留白，窗光照亮纸面纤维和手背浅阴影，落幅角色A闭口且信封仍未递出。",
    },
    {
        "name": "masked_emotion_leak_card",
        "prompt": "9:16画幅，写实电影级动态漫短剧，低饱和暖灰会客室。角色A在画面右侧中近景维持平稳坐姿，听见告别后仍直视角色B，肩线没有抬起；只有按住杯沿的右手指腹逐渐泛白，吸气在喉间短停后才低声回应。角色B只以前景左肩线虚化入画。固定机位不追脸，暖侧光照亮角色A手背、杯沿短反光和眼下浅阴影，落幅角色A嘴唇闭合但手指没有松开。",
    },
    {
        "name": "composition_camera_motivation_card",
        "prompt": "16:9画幅，写实电影级动态漫短剧，冷白会议室长桌。角色A实焦位于画面左三分之一，角色B在右后景，中央信封与大块桌面留白隔开两人，前景桌沿形成低幅遮挡。起幅摄影机固定守住距离；角色B视线第一次落到信封时才极慢推近半步，焦点仍留在角色A指腹与信封封口。顶灯照亮纸面和手背，背景资料柜弱虚化，落幅信封仍停在两人中央。",
    },
    {
        "name": "emotion_residue_contract_card",
        "prompt": "16:9画幅，写实电影级动态漫短剧，低暖床头灯下的室内。角色A起幅强忍平稳，听完画外声后眼睑停半拍，嘴角压住，下颌轻颤又收回；她没有开口，只把指尖从纸条边缘慢慢松开。暖光照亮脸侧、手背和纸张纤维，暗部保留黑位，背景窗帘柔和虚化，落幅泪意停在眼眶没有滑落。",
    },
    {
        "name": "creative_profile_expressive_safe",
        "prompt": "16:9画幅，写实电影级动态漫短剧，expressive低风险环境镜，清晨金色窗光穿过旧剧场。镜头从空舞台左侧低机位单向缓慢横移，最终停在中央一只落灰麦克风，期间无人物入画、无第二动作链。暖光照亮金属麦克风边缘和木地板划痕，空气尘粒只在逆光中轻飘，背景红幕虚化，落幅麦克风稳定实焦。",
    },
    {
        "name": "viewpoint_scale_traversal",
        "prompt": "16:9画幅，写实电影级动态漫短剧，穿越尺度视角。镜头从高空云层破口沿同一方向俯冲，中心锚点始终是山谷公路上的黑色跑车；接近路面前明显减速，转为贴地低空追拍。清晨冷白光从上方照亮车顶玻璃和湿路面反光，护栏与路纹高速掠过，落幅稳定在车侧前方低机位。",
    },
    {
        "name": "viewpoint_pov_hospital",
        "prompt": "9:16画幅，写实电影级动态漫短剧，POV第一人称废弃医院走廊。镜头绑定持手电者眼位，画面下缘可见握手电的右手和急促呼吸造成的小幅起伏，只照见前方病房门和潮湿地面。冷白光从手电向前扫过脱落墙皮和水渍反光，门缝黑暗保持不可见，落幅停在门口模糊人影消失后的空门框。",
    },
    {
        "name": "viewpoint_horizontal_reveal",
        "prompt": "16:9画幅，写实电影级动态漫短剧，低饱和暖灰会议厅。镜头沿长桌水平横移，只按从左到右顺序揭示四名角色，每次只让当前人物实焦，前后人物保持肩线或背景虚化；焦点从手按权杖转到王储脸侧后停住。壁炉暖光与窗外冷月光形成侧逆光，桌面旧木纹和金属链饰有压暗反光，落幅稳定在主位半身。",
    },
    {
        "name": "ancient_mountain_landscape_arc",
        "prompt": "16:9画幅，写实电影级古装山居清晨。前景湿润竹叶从右上方轻虚化垂入，中景石阶沿山势斜向上引导到半开的木门，后景层叠青山被晨雾分成三层低对比轮廓；地平线压在上三分之一，大片浅灰天空给屋舍留出呼吸。谷风先推动叶尖和檐下细雾，随后水渠表面出现断续细纹，木门始终不动。云层变薄后冷白自然光从左上方擦亮石阶水痕和旧木纹，落幅停在门内尚未出现的人影前。",
    },
    {
        "name": "rural_rain_environment_story",
        "prompt": "16:9画幅，写实电影级乡村雨后院落。前景屋檐滴水不规则落入旧陶缸，中景泥地脚印从木门延向空板凳，后景低矮瓦房与远田在雨雾中逐层退淡；板凳偏离中心，门口留白成为视觉落点。风只让晾衣绳和菜叶不同幅度摆动，积水反光被细小涟漪切碎，不形成镜面。云后暖光短暂照亮板凳木纹和墙角青苔，随后恢复柔灰，落幅一滴水沿门槛旧裂纹滑下。",
    },
    {
        "name": "light_comedy_courtyard_breathing",
        "prompt": "9:16画幅，写实电影级轻喜剧社区院子午后。前景晾晒床单边缘轻度虚焦形成明亮框景，中景自行车与错开放置的矮凳构成松弛活动区，后景楼道口和树荫下邻居只作低细节生活流动；暖黄墙面与青绿植物分离，中央留白等待人物进入。微风先掀起床单下角，再带动树叶碎影扫过地面，塑料盆保持哑光不发白。暖白自然光从左上方照亮车铃短高光和墙面旧擦痕，落幅床单回落但没有遮住楼道口。",
    },
    {
        "name": "suspense_forest_reveal_order",
        "prompt": "16:9画幅，写实电影级悬疑林道黄昏。前景黑松枝条只遮住画面左上角，中景湿土车辙从下方收束向右后方废弃路牌，后景林间狭窄出口被薄雾压低对比；画面先读到车辙，再沿引导线发现路牌背后的半截红布。冷白自然光从右后方穿过树隙，只在湿土、路牌金属和红布边缘留下窄亮面，暗部保留粗糙树皮纹理，后景轻虚化。风从右向左先推动雾丝，再让红布轻颤一次，枝干不整齐同步摆动，落幅焦点停在红布而出口仍未揭开。",
    },
    {
        "name": "coastal_release_landscape",
        "prompt": "16:9画幅，写实电影级海边关系戏清晨余波。前景低矮礁石和一小片焦外海草形成底部框景，中景人物背影只占画面右侧三分之一，后景海岸线向左远伸并在薄雾中逐层变淡；地平线保持水平，人物面前保留大面积冷灰海面留白。海风先压低海草，再让衣摆慢半拍贴向身体，浪花以不均匀间隔破碎后退。云层裂隙的暖光只擦亮肩线、礁石湿面和少量碎反光，落幅人物没有转身，远处一艘小船缓慢离开实焦区。",
    },
    {
        "name": "cold_cyan_clean_face",
        "prompt": "16:9画幅，写实电影级都市短剧，冷青灰旧办公室。角色A在画面右侧中近景实焦，前景玻璃隔断边缘轻虚化，中景桌面文件形成接触层，后景旧墙和百叶窗退入低对比青灰。画面右前方4300K柔和暖白主光照亮脸侧，低强度中性补光托住眼窝、鼻翼和下颌；皮肤保持自然暖灰血色，青灰只留在后景墙面与衣物边缘，墙面旧痕和灰尘留在焦外背景。",
    },
    {
        "name": "neon_street_clean_face",
        "prompt": "9:16画幅，写实电影级夜街关系戏。角色A在画面左侧中近景实焦，前景湿伞边轻度焦外，中景店门与人物构成暖光接触区，后景洋红和青色招牌沿街逐层虚化。右前方中性暖白店铺光照亮面中并留下柔和眼神光，低幅补光保住下颌层次；霓虹只落在发梢、外套边缘和湿地面断续反光，脸部仍保持可读的自然肤色，雨雾退到街道后景。",
    },
    {
        "name": "tyndall_beam_clean_face",
        "prompt": "16:9画幅，写实电影级清晨旧教室。角色A坐在画面右侧中近景，前景课桌角轻虚化，中景脸和摊开的书页实焦，后景窗格与黑板逐层退后。窄束日光从左后方百叶窗缝穿入，在角色A肩后形成两道丁达尔光束，尘粒只在光束体积内缓慢可见；右前方柔和中性面光独立照亮脸侧，低强度补光托住眼窝，皮肤不过曝也不出现斑驳光块，旧墙粉尘只留在后景。",
    },
    {
        "name": "stage_haze_clean_face",
        "prompt": "16:9画幅，写实电影级小剧场后台。角色A站在画面中央偏左中景，前景幕布边缘轻虚化，中景人物与话筒实焦，后景木台阶和黑幕压入深灰。单一暖白聚光从左上方穿过受控薄雾，在人物肩后形成清楚光锥，雾只停留在光锥体积和后景；右前方低强度中性补光照亮面中和眼神光，皮肤保留自然血色，话筒金属只留窄高光，黑位保持层次。",
    },
    {
        "name": "rainy_car_headlight_clean_face",
        "prompt": "16:9画幅，写实电影级雨夜车内。角色A坐在驾驶位中近景，前景方向盘上沿轻虚化，中景脸侧与握方向盘的手实焦，后景座椅和侧窗退暗。车外冷白车灯只在挡风玻璃外的雨滴与湿路上形成散射光斑，水汽停在玻璃外侧；仪表台暖灰微光与右侧柔和中性补光共同托住脸部，眼窝和下颌有干净暗部，皮肤不被蓝光覆盖，玻璃反射断续低亮。",
    },
    {
        "name": "water_caustics_clean_face",
        "prompt": "16:9画幅，写实电影级临水餐厅午后。角色A在画面右侧中近景实焦，前景杯沿轻虚化，中景人物与木桌形成暖灰接触层，后景水面和浅色墙逐层退后。窗外反射形成的水波焦散只在后景墙面和桌角缓慢移动，亮纹遵循水面波动方向；左前方柔和中性自然光稳定照亮脸侧，低幅补光保住眼窝与鼻翼，皮肤保持均匀自然血色，不承接墙面跳动亮纹，木纹与杯沿反光受控。",
    },
    {
        "name": "firelight_clean_face",
        "prompt": "16:9画幅，写实电影级山屋夜戏。深色肤色角色A在画面左侧中近景实焦，前景壁炉石沿轻虚化，中景脸与握杯双手保持清楚，后景木墙退入低对比暗部。壁炉橙红火光只在脸侧外缘、手背和杯沿形成低幅动态反光；右前方4300K中性面光稳定托住额头、眼窝和下颌，保留真实深色肤色层次，跳动火影不扫过面中，烟尘只停在壁炉后方。",
    },
    {
        "name": "mixed_temperature_clean_face",
        "prompt": "9:16画幅，写实电影级夜间便利店门口。角色A在画面右侧中近景，前景玻璃门边轻虚化，中景人物与纸袋实焦，后景街道冷蓝车灯逐层散开。店内暖白顶光落在肩背，街外冷光只勾勒发梢和外套边缘；左前方中性补光统一面部曝光，眼窝、鼻翼和下颌保持干净暗部，冷暖色温在耳后与衣领处分界，不在脸上叠成青橙色斑，玻璃反光避开五官。",
    },
    {
        "name": "multi_depth_perspective_scale_lock",
        "prompt": "16:9画幅，写实电影级站台关系戏。角色A位于前景左侧，角色B站在后景右侧，两人双脚接触同一连续站台地面，地砖接缝和站台边线向同一消失点收束。遵循近大远小，角色A画面投影占比自然大于角色B，但两人真实身高、头身比例和肩宽不变；角色B手中行李箱相对手掌的真实尺寸稳定。焦平面落在角色A，后景角色B低幅虚化。左上方5600K站棚天光照亮人物肩线和地砖接缝，脸部中性补光保留自然肤色。",
    },
    {
        "name": "depth_motion_continuous_scaling",
        "prompt": "9:16画幅，写实电影级旧巷重逢。角色A从后景巷口沿地面中心线走向中景，双脚每一步都落在连续石板路上，头顶高度与地面接触点沿透视线平滑变化。靠近镜头时画面占比连续增大，真实身高、头身比例、肩宽和手中纸袋相对身体的尺寸始终不变；摄影机固定，不用突然变焦制造大小跳变。前景门框轻虚化，中景落点留出空间，后景雾层逐步退开；右前方4800K柔光稳定照亮脸侧和纸袋褶皱，暗部保留层次。",
    },
]
CINEMATIC_REALISM_CASES = [
    {
        "name": "live_action_rain_hallway",
        "prompt": "16:9画幅，写实电影剧照，雨夜蓝黑旧走廊。低机位贴近湿地面，右侧门框形成前景遮挡，墙线向远端红色出口灯收束；焦平面落在门缝冷白光和中段水汽，远端背景轻雾化。顶灯只照亮中段，暗部保留黑位，亮部不过曝；冷白灯与暗红灯低饱和分离。空气里有逆光雨雾和细小尘粒，墙皮起皮、瓷砖水渍、地面积水反光断续不规则。",
    },
    {
        "name": "live_action_counter_ui",
        "prompt": "16:9画幅，写实实拍短片镜头，夜间场景A柜台。前景左侧玻璃边缘轻微虚焦遮挡，焦平面在角色A手指和手机边缘，背景灯箱压成柔散光斑。冷白灯箱光只擦亮手背和柜台旧划痕，暗部不过度提亮；手机侧边有短高光，玻璃反射断续不完整。空气里有细尘颗粒，柜台金属边磨损不均匀，右侧UI文字作为二维浮层留在安全区。",
    },
    {
        "name": "live_action_dialogue_face",
        "prompt": "16:9画幅，写实电影剧照，低饱和室内对话。角色A在画面右前三分之一中近景，前景左侧角色B肩线焦外遮挡，焦平面落在角色A眼下和嘴角；背景门框轻虚化。窗外冷光从左侧擦过脸颊，室内暖台灯只留一小块受光，暗部有黑位但保留皮肤纹理。衣料有细褶和磨损，桌面纸张边缘起毛，空气里有微尘，落幅角色A口型闭合、视线没有复位。",
    },
]
VIDEO_TEXTURE_CASES = [
    {
        "name": "rain_hallway_video_texture",
        "contract": {
            "look_profile": "全片统一为写实影视级PBR物理渲染和低饱和胶片基调",
            "exposure_policy": "所有镜头保留暗部黑位，灯罩亮部不过曝，高光只落在受光面边缘",
            "material_motion_policy": "墙面、地面、金属和积水在运动中保持粗糙材质、断续反光和不均匀高光",
            "atmosphere_motion_policy": "雨雾尘和水汽只做缓慢贴地扩散或断续飘动，不形成均匀粒子层",
            "camera_stability_policy": "镜头以固定或低幅缓慢运动为主，不摇晃、不快速推拉、不临时变焦",
            "continuity_carryover": "跨镜保持同一光色、黑位、湿度和材质颗粒，不重置空间质感不跳变",
            "risk_controls": "避免镜面水面、塑料墙、均匀雨线、过曝灯管、贴图跳变和廉价CG感",
        },
        "prompt": "16:9画幅，高端3D CG写实影视级PBR物理渲染，雨夜旧走廊。镜头固定低幅缓慢推近，顶灯亮部不过曝，暗部保留黑位；地面积水在涟漪里形成断续反光，墙面粗糙划痕和门框磨损不跳变，雨雾尘缓慢贴地扩散，只在冷光边缘出现颗粒，跨镜保持同一冷白光色、湿度和低饱和黑位。",
    },
]


def check(skill_dir):
    path = os.path.join(skill_dir, "references", "format_example.txt")
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    issues = ["missing %s" % label for label in REQUIRED if label not in text]
    issues.extend("forbidden %s" % token for token in FORBIDDEN if token in text)
    issues.extend(_quality_case_issues())
    return issues


def _quality_case_issues():
    issues = []
    if len(QUALITY_CASES) < 12:
        issues.append("quality case count must be at least 12")
    for case in QUALITY_CASES:
        name = case.get("name", "unnamed")
        prompt = str(case.get("prompt", "") or "")
        length = len(prompt)
        if length < 120 or length > 420:
            issues.append("%s direct prompt length %d outside 120-420" % (name, length))
        for issue in direct_copy_prompt_issues(prompt, max_chars=420, require_visual_texture=True):
            issues.append("%s %s" % (name, issue))
        if any(term in prompt for term in ABSTRACT_ONLY_TERMS):
            issues.append("%s uses abstract-only visual term" % name)
        if case.get("high_risk") and (not case.get("constraint") or not case.get("negative")):
            issues.append("%s high-risk case missing constraint/negative block" % name)
    for case in CINEMATIC_REALISM_CASES:
        name = case.get("name", "unnamed")
        prompt = str(case.get("prompt", "") or "")
        length = len(prompt)
        if length < 140 or length > 420:
            issues.append("%s cinematic prompt length %d outside 140-420" % (name, length))
        for issue in direct_copy_prompt_issues(prompt, max_chars=420, require_visual_texture=True):
            issues.append("%s %s" % (name, issue))
        for issue in cinematic_realism_prompt_issues(prompt, require_live_action_style=True):
            issues.append("%s %s" % (name, issue))
    for case in VIDEO_TEXTURE_CASES:
        name = case.get("name", "unnamed")
        metadata = {"video_texture_contract": case.get("contract", {})}
        prompt = str(case.get("prompt", "") or "")
        length = len(prompt)
        if length < 120 or length > 420:
            issues.append("%s video texture prompt length %d outside 120-420" % (name, length))
        for issue in direct_copy_prompt_issues(prompt, max_chars=420, require_visual_texture=True):
            issues.append("%s %s" % (name, issue))
        for issue in video_texture_contract_issues(metadata, prompt):
            issues.append("%s %s" % (name, issue))
    return issues


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(__file__))
    issues = check(root)
    if issues:
        print("[GOLDEN JIMENG] FAIL")
        for issue in issues:
            print("- " + issue)
        raise SystemExit(1)
    print("[GOLDEN JIMENG] PASS")

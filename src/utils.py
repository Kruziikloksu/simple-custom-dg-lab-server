import math
import qrcode
from qrcode.image.pil import PilImage
from typing import List, Optional
from pulse_section import PulseSection
from enums import MessageType, ChannelType, StrengthChangeMode
from functools import lru_cache
from models import DungeonLabMessage

def get_strength_str(channel: ChannelType, mode: StrengthChangeMode, value: int) -> str:
    return f"strength-{channel.value}+{mode.value}+{value}"


def get_clear_str(channel: ChannelType) -> str:
    return f"clear-{channel.value}"


def get_pulse_str(channel: ChannelType, pulse: str) -> str:
    return f"pulse-{channel.name}:{pulse}"


def get_preset_pulse_str(channel: ChannelType, preset: str) -> str:
    return f"preset-{channel.value}:{preset}"


def get_preset_pulse_section_str_list(preset: str) -> List[str]:
    result = []
    section_list = simple_decode_dg_pulse_str(preset)
    for section in section_list:
        section_str = section.get_pulse_value_str()
        result.append(section_str)
    return result


def get_dg_message_json(type: MessageType, client_id: str, target_id: str, message: str) -> str:
    data = DungeonLabMessage(
        type=type,
        clientId=client_id,
        targetId=target_id,
        message=message,
    )
    json_str = data.model_dump_json()
    return json_str


def show_qr_code(qr_code_str: str):
    # qrcode_terminal.draw(qr_code_str)
    qr_code_img = qrcode.make(qr_code_str, image_factory=PilImage)
    qr_code_img.show()


def get_qr_code_str(host, port, client_id) -> str:
    return f"https://www.dungeon-lab.com/app-download.php#DGLAB-SOCKET#ws://{host}:{port}/{client_id}"

# strength-通道+强度变化模式+数值
# 通道: 1 - A 通道；2 - B 通道
# 强度变化模式: 0 - 通道强度减少；1 - 通道强度增加；2 - 通道强度变化为指定数值
# 数值: 范围在(0 ~ 200)的整型
# 举例：
# A 通道强度+5 -> strength-1+1+5
# B 通道强度归零 -> strength-2+2+0
# B 通道强度-20 -> strength-2+0+20
# A 通道强度指定为 35 -> strength-1+2+35
# Tips 指令必须严格按照协议编辑，任何非法的指令都会在 APP 端丢弃，不会执行


def clamp(n, min, max):
    if n < min:
        return min
    elif n > max:
        return max
    else:
        return n


def decimal_to_hex_byte(value: int) -> str:
    value = clamp(value, 0, 255)
    return f'{value:02X}'


def get_real_pulse_frequency(value: int) -> int:
    if value <= 0:
        value = 10
    elif value <= 40:
        value = 10 + value
    elif value <= 55:
        value = 50 + (value-40)*2
    elif value <= 59:
        value = 80 + (value-55)*5
    elif value <= 69:
        value = 100 + (value-59)*10
    elif value <= 75:
        float_value = 200 + (value-69)*33.3
        floor_value = math.floor(float_value)
        delta = float_value - floor_value
        if delta >= 0.9:
            value = floor_value + 1
        else:
            value = floor_value
    elif value <= 79:
        value = 400 + (value-75)*50
    elif value <= 83:
        value = 600 + (value-79)*100
    else:
        value = 1000
    value = math.floor(value)
    return value


def get_real_section_time(value: int) -> float:
    result = 0.1
    if value <= 49:
        result = 0.1 + value * 0.1
    elif value <= 64:
        result = 5 + (value - 49) * 0.2
    elif value <= 68:
        result = 8 + (value - 64) * 0.5
    elif value <= 78:
        result = 10 + (value - 68) * 1
    elif value <= 84:
        result = 20 + (value - 78) * 3.3
        floor_value = math.floor(result)
        delta = result - floor_value
        if delta >= 0.9:
            result = floor_value + 1
    elif value <= 88:
        result = 40 + (value - 84) * 5
    elif value <= 92:
        result = 60 + (value - 88) * 10
    elif value <= 97:
        result = 100 + (value - 92) * 20
    elif value <= 99:
        result = 200 + (value - 97) * 50
    else:
        result = 300
    return result


@lru_cache(maxsize=None)
def simple_decode_dg_pulse_str(dg_pulse_str: str) -> List[PulseSection]:
    result: Optional[List[PulseSection]] = []
    str_list = dg_pulse_str.split("=")
    prefix_str = str_list[0]
    pulse_config_str = prefix_str.replace("Dungeonlab+pulse:", "")
    pulse_config_list = pulse_config_str.split(",")
    rest_time_step = int(pulse_config_list[0])  # 休息时长的滑条值
    rest_time = 0.01 * rest_time_step  # 休息时长 单位秒
    speed = int(pulse_config_list[1])  # 播放速率
    unknown_value = int(pulse_config_list[2])  # 意味不明
    data_str = str_list[1]
    section_list = data_str.split("+section+")
    for i in range(len(section_list)):
        is_last_section = i == len(section_list) - 1
        section_str = section_list[i]
        section_config_str = section_str.split("/")[0]
        section_config_list = section_config_str.split(",")
        from_frequency_step = int(section_config_list[0])  # 渐变起始频率的滑条值
        from_frequency = get_real_pulse_frequency(
            from_frequency_step)  # 渐变起始频率
        to_frequency_step = int(section_config_list[1])  # 渐变终点频率的滑条值
        to_frequency = get_real_pulse_frequency(to_frequency_step)  # 渐变终点频率
        section_time_step = section_config_list[2]  # 小节时长的滑条值
        section_time = get_real_section_time(
            int(section_time_step))  # 小节时长 单位秒 使用值注意要除波形时长向上取整乘以波形时长
        frequency_gradient_type = int(section_config_list[3])  # 频率渐变类型
        is_active = int(section_config_list[4])  # 小节是否启用
        pulse_section = PulseSection(from_frequency, to_frequency, section_time, frequency_gradient_type,
                                     is_active, speed, rest_time if is_last_section else 0)
        pulse_data_str = section_str.split("/")[1]
        pulse_data_list = pulse_data_str.split(",")
        for pulse_data in pulse_data_list:
            value_list = pulse_data.split("-")
            strength = value_list[0]  # 强度
            anchor = int(value_list[1])  # 锚点
            strength = float(strength)
            strength = round(strength)
            pulse_section.add_pulse(strength, anchor)
        result.append(pulse_section)
    return result


preset_wave_data_dict = {
    "呼吸": r'Dungeonlab+pulse:35,1,8=0,20,0,1,1/0.00-1,20.00-0,40.00-0,60.00-0,80.00-0,100.00-1,100.00-1,100.00-1',
    "潮汐": r'Dungeonlab+pulse:5,1,8=0,32,19,2,1/0.00-1,16.65-0,33.30-0,50.00-0,66.65-0,83.30-0,100.00-1,92.00-0,84.00-0,76.00-0,68.00-1',
    "连击": r'Dungeonlab+pulse:0,1,8=0,34,19,1,1/100.00-1,0.00-1,100.00-1,66.65-0,33.30-0,0.00-1,0.00-0,0.00-1',
    "快速按捏": r'Dungeonlab+pulse:5,1,8=0,20,19,1,1/0.00-1,28.55-1,0.00-1,52.50-1,0.00-1,73.40-1,0.00-1,87.25-1,0.00-1,100.00-1,0.00-1',
    "按捏渐强": r'Dungeonlab+pulse:5,1,8=0,20,19,1,1/0.00-1,28.55-1,0.00-1,52.50-1,0.00-1,73.40-1,0.00-1,87.25-1,0.00-1,100.00-1,0.00-1',
    "心跳节奏": r'Dungeonlab+pulse:5,1,16=65,20,5,1,1/100.00-1,100.00-1+section+0,20,19,1,1/0.00-1,0.00-0,0.00-0,0.00-0,0.00-1,75.00-1,83.30-0,91.65-0,100.00-1,0.00-1,0.00-0,0.00-0,0.00-0,0.00-1',
    "压缩": r'Dungeonlab+pulse:0,1,16=52,16,0,2,1/100.00-1,100.00-0,100.00-0,100.00-0,100.00-0,100.00-0,100.00-0,100.00-0,100.00-0,100.00-0,100.00-1+section+0,20,0,1,1/100.00-1,100.00-0,100.00-0,100.00-0,100.00-0,100.00-0,100.00-0,100.00-0,100.00-0,100.00-1',
    "节奏步伐": r'Dungeonlab+pulse:5,1,8=0,20,19,1,1/0.00-1,20.00-0,40.00-0,60.00-0,80.00-0,100.00-1,0.00-1,25.00-0,50.00-0,75.00-0,100.00-1,0.00-1,33.30-0,66.65-0,100.00-1,0.00-1,50.00-0,100.00-1,0.00-1,100.00-1,0.00-1,100.00-1,0.00-1,100.00-1,0.00-1,100.00-1',
    "颗粒摩擦": r'Dungeonlab+pulse:0,1,8=0,38,24,2,1/100.00-1,100.00-0,100.00-1,0.00-1',
    "渐变弹跳": r'Dungeonlab+pulse:20,1,16=0,30,44,2,1/0.00-1,33.30-0,66.65-0,100.00-1',
    "波浪涟漪": r'Dungeonlab+pulse:5,1,16=0,60,51,4,1/0.00-1,50.00-0,100.00-1,73.35-1',
    "雨水冲刷": r'Dungeonlab+pulse:25,1,8=4,0,38,1,1/33.50-1,66.75-0,100.00-1+section+44,54,34,1,1/100.00-1,100.00-1',
    "变速敲击": r'Dungeonlab+pulse:15,1,8=14,20,40,1,1/100.00-1,100.00-0,100.00-1,0.00-1,0.00-0,0.00-0,0.00-1+section+65,20,39,1,1/100.00-1,100.00-0,100.00-0,100.00-1',
    "信号灯": r'Dungeonlab+pulse:0,1,8=78,64,19,1,1/100.00-1,100.00-0,100.00-0,100.00-1+section+0,20,19,3,1/0.00-1,33.30-0,66.65-0,100.00-1',
    "挑逗1": r'Dungeonlab+pulse:5,1,8=0,20,35,3,1/0.00-1,25.00-0,50.00-0,75.00-0,100.00-1,100.00-1,100.00-1,0.00-1,0.00-0,0.00-1+section+0,20,21,1,1/0.00-1,100.00-1',
    "挑逗2": r'Dungeonlab+pulse:18,1,8=27,7,32,3,1/0.00-1,11.10-0,22.20-0,33.30-0,44.40-0,55.50-0,66.60-0,77.70-0,88.80-0,100.00-1+section+0,20,39,2,1/0.00-1,100.00-1',
}


def get_preset_wave_data_dict() -> dict:
    return preset_wave_data_dict


def get_preset_wave_data(id: str) -> Optional[str]:
    if id in preset_wave_data_dict:
        return preset_wave_data_dict[id]
    else:
        return None

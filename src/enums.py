from enum import Enum


class StatusCode(Enum):
    """
    - SUCCESS: "成功",
    - CLIENT_DISCONNECTED: "对方客户端已断开",
    - INVALID_CLIENT_ID: "二维码中没有有效的 clientID",
    - SOCKET_NOT_READY: "socket 连接上了，但服务器迟迟不下发 app 端的 id 来绑定",
    - ID_ALREADY_BOUND: "此 id 已被其他客户端绑定关系",
    - TARGET_CLIENT_NOT_FOUND: "要绑定的目标客户端不存在",
    - NOT_BOUND_RELATIONSHIP: "收信方和寄信方不是绑定关系",
    - INVALID_JSON_FORMAT: "发送的内容不是标准 json 对象",
    - RECIPIENT_NOT_FOUND: "未找到收信人（离线）",
    - MESSAGE_TOO_LONG: "下发的 message 长度大于 1950",
    - SERVER_ERROR: "服务器内部异常"
    """
    SUCCESS = "200"
    CLIENT_DISCONNECTED = "209"
    INVALID_CLIENT_ID = "210"
    SOCKET_NOT_READY = "211"
    ID_ALREADY_BOUND = "400"
    TARGET_CLIENT_NOT_FOUND = "401"
    NOT_BOUND_RELATIONSHIP = "402"
    INVALID_JSON_FORMAT = "403"
    RECIPIENT_NOT_FOUND = "404"
    MESSAGE_TOO_LONG = "405"
    SERVER_ERROR = "500"


class MessageType(Enum):
    HEARTBEAT = "heartbeat"
    BIND = "bind"
    MSG = "msg"
    BREAK = "break"
    ERROR = "error"


class PulseFrequencyGradientType(Enum):
    '''
    - FIX : 固定
    - IN_SECTION : 节内渐变 为小节结束前的每个脉冲插值
    - IN_PULSE : 元内渐变 为每个脉冲元内的每个脉冲插值
    - BETWEEN_PULSE : 元间渐变 为小节结束前的每个脉冲元插一次值
    '''
    FIX = 1
    IN_SECTION = 2
    IN_PULSE = 3
    BETWEEN_PULSE = 4


class FeedbackType(Enum):
    CIRCLE_A = '0'
    TRIANGLE_A = '1'
    SQUARE_A = '2'
    STAR_A = '3'
    HEXAGON_A = '4'
    CIRCLE_B = '5'
    TRIANGLE_B = '6'
    SQUARE_B = '7'
    STAR_B = '8'
    HEXAGON_B = '9'


class ChannelType(Enum):
    A = 1
    B = 2

class StrengthChangeMode(Enum):
    DECREASE = 0
    INCREASE = 1
    FIXED = 2
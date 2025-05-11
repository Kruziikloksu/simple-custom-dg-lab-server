from pydantic import BaseModel
from enums import MessageType, ChannelType, StrengthChangeMode
class DungeonLabMessage(BaseModel):
    type: MessageType = MessageType.MSG
    clientId: str = ""
    targetId: str = ""
    message: str = ""


class DungeonLabStrengthMessage(BaseModel):
    channel: ChannelType = ChannelType.A
    mode: StrengthChangeMode = StrengthChangeMode.FIXED
    value: int = 0


class DungeonLabClearMessage(BaseModel):
    channel: ChannelType = ChannelType.A


class DungeonLabPulseMessage(BaseModel):
    channel: ChannelType = ChannelType.A
    pulse: str = ""


class DungeonLabPresetPulseMessage(BaseModel):
    channel: ChannelType = ChannelType.A
    preset: str = ""


class DungeonLabSimpleMessage(BaseModel):
    type: MessageType = MessageType.MSG
    message: str = ""


class DungeonLabStrengthInfo(BaseModel):
    strengthA: int = 0
    strengthB: int = 0
    strengthLimitA: int = 0
    strengthLimitB: int = 0
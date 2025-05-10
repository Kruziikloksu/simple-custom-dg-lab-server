
import utils
import math
import enums


class PulseSection:
    def __init__(self, from_frequency: int, to_frequency: int, section_time: float, frequency_gradient_type: int, is_active: int = 1, speed: int = 1, rest_time: float = 0):
        self.from_frequency = from_frequency
        self.to_frequency = to_frequency
        self.section_time = section_time
        self.frequency_gradient_type = frequency_gradient_type
        self.is_active = is_active
        self.speed = speed
        self.rest_time = rest_time
        self.pulse_list = []

    def add_pulse(self, strength: int, anchor: int = 0):
        pulse = Pulse(strength, self.from_frequency, anchor)
        self.pulse_list.append(pulse)

    def get_wave_time(self):
        point_num = 4 / self.speed
        point_time = 0.1 / 4
        wave_time = len(self.pulse_list) * point_num * point_time
        return wave_time

    def get_whole_wave(self):
        whole_wave = []
        wave = []
        for pulse in self.pulse_list:
            point_num = 4 / self.speed
            for i in range(int(point_num)):
                frequency = pulse.frequency
                strength = pulse.strength
                wave.append([frequency, strength])
        if self.frequency_gradient_type == enums.PulseFrequencyGradientType.IN_PULSE.value:
            whole_wave_length = len(wave)
            frequency_list = self._fill_linear_interpolation(
                whole_wave_length, self.from_frequency, self.to_frequency)
            for i in range(whole_wave_length):
                wave[i][0] = frequency_list[i]
        point_time = 0.1 / 4
        wave_time = len(wave) * point_time
        wave_num = math.ceil(self.section_time / wave_time)
        for i in range(int(wave_num)):
            if self.frequency_gradient_type == enums.PulseFrequencyGradientType.BETWEEN_PULSE.value:
                frequency_list = self._fill_linear_interpolation(
                    wave_num, self.from_frequency, self.to_frequency)
                frequency = frequency_list[i]
                wave[i][0] = frequency
            whole_wave.extend(wave)
        if self.frequency_gradient_type == enums.PulseFrequencyGradientType.IN_SECTION.value:
            whole_wave_length = len(whole_wave)
            frequency_list = self._fill_linear_interpolation(
                whole_wave_length, self.from_frequency, self.to_frequency)
            for i in range(whole_wave_length):
                whole_wave[i][0] = frequency_list[i]
        if self.rest_time > 0:
            rest_point_num = self.rest_time / point_time
            rest_point_num = math.floor(rest_point_num)
            if rest_point_num > 0:
                for i in range(int(rest_point_num)):
                    whole_wave.append([0, 0])
        return whole_wave

    def get_pulse_str_list(self, to_hex: bool = True):
        whole_wave = self.get_whole_wave()
        frequency_list = []
        strength_list = []
        for i in range(len(whole_wave)):
            frequency = whole_wave[i][0]
            strength = whole_wave[i][1]
            frequency_list.append(frequency)
            strength_list.append(strength)
        group_frequency_list = self._group_by_four_with_padding(frequency_list)
        group_strength_list = self._group_by_four_with_padding(strength_list)
        target_str_list = []
        for i in range(len(group_frequency_list)):
            frequency_group = group_frequency_list[i]
            frequency_str = ""
            for frequency in frequency_group:
                frequency = math.floor(frequency)
                frequency = self._convert_pulse_frequency(frequency)
                if to_hex:
                    frequency = utils.decimal_to_hex_byte(frequency)
                    frequency_str = frequency_str + str(frequency)
                else:
                    frequency_str = frequency_str + str(frequency) + ","
            strength_group = group_strength_list[i]
            strength_str = ""
            for strength in strength_group:
                strength = math.floor(strength)
                strength = utils.clamp(strength, 0, 100)
                if to_hex:
                    strength = utils.decimal_to_hex_byte(strength)
                    strength_str = strength_str + str(strength)
                else:
                    strength_str = strength_str + str(strength) + ","
            target_str = rf'"{frequency_str}{strength_str}"'
            target_str_list.append(target_str)
        return target_str_list

    def get_websocket_wave_str(self, to_hex: bool = True):
        target_str_list = self.get_pulse_str_list(to_hex)
        result = ','.join(target_str_list)
        result = rf"[{result}]"
        return result

    def _fill_linear_interpolation(self, array_length, from_value, to_value):
        if array_length <= 1:
            return [from_value] * array_length
        step = (to_value - from_value) / (array_length - 1)
        return [from_value + i * step for i in range(array_length)]

    def _group_by_four_with_padding(self, arr):
        result = []
        for i in range(0, len(arr), 4):
            group = arr[i:i+4]
            if len(group) < 4:
                group += [0] * (4 - len(group))
            result.append(group)
        return result

    def _convert_pulse_frequency(self, value: int) -> int:
        value = round(value)
        value = utils.clamp(value, 10, 1000)
        if value <= 100:
            value = value
        elif value <= 600:
            value = math.floor((value - 100) / 5 + 100)
        elif value <= 1000:
            value = math.floor((value - 600) / 10 + 200)
        else:
            value = 10
        value = math.floor(value)
        value = utils.clamp(value, 10, 240)
        return value


class Pulse:
    def __init__(self, strength: int, frequency: int, anchor: int = 0):
        self.strength = strength
        self.frequency = frequency
        self.anchor = anchor

    def set_frequency(self, frequency):
        self.frequency = frequency

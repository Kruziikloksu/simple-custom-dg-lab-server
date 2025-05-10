using System.Collections.Generic;
using System.Net.Sockets;
using System.Net;

namespace CustomDungeonLab
{
    public static class DungeonLabUtility
    {
        public static Dictionary<string, string> PresetPulseDataDict = new Dictionary<string, string>
        {
            { "呼吸", @"Dungeonlab+pulse:35,1,8=0,20,0,1,1/0.00-1,20.00-0,40.00-0,60.00-0,80.00-0,100.00-1,100.00-1,100.00-1" },
            { "潮汐", @"Dungeonlab+pulse:5,1,8=0,32,19,2,1/0.00-1,16.65-0,33.30-0,50.00-0,66.65-0,83.30-0,100.00-1,92.00-0,84.00-0,76.00-0,68.00-1" },
            { "连击", @"Dungeonlab+pulse:0,1,8=0,34,19,1,1/100.00-1,0.00-1,100.00-1,66.65-0,33.30-0,0.00-1,0.00-0,0.00-1" },
            { "快速按捏", @"Dungeonlab+pulse:5,1,8=0,20,19,1,1/0.00-1,28.55-1,0.00-1,52.50-1,0.00-1,73.40-1,0.00-1,87.25-1,0.00-1,100.00-1,0.00-1" },
            { "按捏渐强", @"Dungeonlab+pulse:5,1,8=0,20,19,1,1/0.00-1,28.55-1,0.00-1,52.50-1,0.00-1,73.40-1,0.00-1,87.25-1,0.00-1,100.00-1,0.00-1" },
            { "心跳节奏", @"Dungeonlab+pulse:5,1,16=65,20,5,1,1/100.00-1,100.00-1+section+0,20,19,1,1/0.00-1,0.00-0,0.00-0,0.00-0,0.00-1,75.00-1,83.30-0,91.65-0,100.00-1,0.00-1,0.00-0,0.00-0,0.00-0,0.00-1" },
            { "压缩", @"Dungeonlab+pulse:0,1,16=52,16,0,2,1/100.00-1,100.00-0,100.00-0,100.00-0,100.00-0,100.00-0,100.00-0,100.00-0,100.00-0,100.00-0,100.00-1+section+0,20,0,1,1/100.00-1,100.00-0,100.00-0,100.00-0,100.00-0,100.00-0,100.00-0,100.00-0,100.00-0,100.00-1" },
            { "节奏步伐", @"Dungeonlab+pulse:5,1,8=0,20,19,1,1/0.00-1,20.00-0,40.00-0,60.00-0,80.00-0,100.00-1,0.00-1,25.00-0,50.00-0,75.00-0,100.00-1,0.00-1,33.30-0,66.65-0,100.00-1,0.00-1,50.00-0,100.00-1,0.00-1,100.00-1,0.00-1,100.00-1,0.00-1,100.00-1,0.00-1,100.00-1" },
            { "颗粒摩擦", @"Dungeonlab+pulse:0,1,8=0,38,24,2,1/100.00-1,100.00-0,100.00-1,0.00-1" },
            { "渐变弹跳", @"Dungeonlab+pulse:20,1,16=0,30,44,2,1/0.00-1,33.30-0,66.65-0,100.00-1" },
            { "波浪涟漪", @"Dungeonlab+pulse:5,1,16=0,60,51,4,1/0.00-1,50.00-0,100.00-1,73.35-1" },
            { "雨水冲刷", @"Dungeonlab+pulse:25,1,8=4,0,38,1,1/33.50-1,66.75-0,100.00-1+section+44,54,34,1,1/100.00-1,100.00-1" },
            { "变速敲击", @"Dungeonlab+pulse:15,1,8=14,20,40,1,1/100.00-1,100.00-0,100.00-1,0.00-1,0.00-0,0.00-0,0.00-1+section+65,20,39,1,1/100.00-1,100.00-0,100.00-0,100.00-1" },
            { "信号灯", @"Dungeonlab+pulse:0,1,8=78,64,19,1,1/100.00-1,100.00-0,100.00-0,100.00-1+section+0,20,19,3,1/0.00-1,33.30-0,66.65-0,100.00-1" },
            { "挑逗1", @"Dungeonlab+pulse:5,1,8=0,20,35,3,1/0.00-1,25.00-0,50.00-0,75.00-0,100.00-1,100.00-1,100.00-1,0.00-1,0.00-0,0.00-1+section+0,20,21,1,1/0.00-1,100.00-1" },
            { "挑逗2", @"Dungeonlab+pulse:18,1,8=27,7,32,3,1/0.00-1,11.10-0,22.20-0,33.30-0,44.40-0,55.50-0,66.60-0,77.70-0,88.80-0,100.00-1+section+0,20,39,2,1/0.00-1,100.00-1" },
        };

        public static string GetPresetWaveData(string presetKey)
        {
            if (PresetPulseDataDict.TryGetValue(presetKey, out string data))
            {
                return data;
            }
            else
            {
                return null;
            }
        }

        public static string GetLocalIPv4()
        {
            string localIP = "127.0.0.1";
            foreach (var ip in Dns.GetHostEntry(Dns.GetHostName()).AddressList)
            {
                if (ip.AddressFamily == AddressFamily.InterNetwork)
                {
                    localIP = ip.ToString();
                    break;
                }
            }
            return localIP;
        }
    }

    public enum DungeonLabMessageType
    {
        BIND = 0,
        UNBIND = 1,
        MSG = 2,
        HEARTBEAT = 3,
        BREAK = 4,
        ERROR = 5,
        CUSTOM = 6,
    }

    public enum DungeonLabFeedback
    {
        CIRCLE_A = 0,
        TRIANGLE_A = 1,
        SQUARE_A = 2,
        STAR_A = 3,
        HEXAGON_A = 4,
        CIRCLE_B = 5,
        TRIANGLE_B = 6,
        SQUARE_B = 7,
        STAR_B = 8,
        HEXAGON_B = 9,
    }

    public enum DungeonLabChannel
    {
        A = 1,
        B = 2,
    }

    public enum DungeonLabStrengthChangeMode
    {
        DECREASE = 0,
        INCREASE = 1,
        FIXED = 2,
    }
}
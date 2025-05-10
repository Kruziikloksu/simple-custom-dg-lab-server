//using Sirenix.OdinInspector;
using System.Net.Http;
using UnityEngine;
namespace CustomDungeonLab
{
    public class DungeonLabHttpManager : MonoBehaviour
    {
        public static DungeonLabHttpManager Instance { get; private set; }
        public int port = 4503;

        private void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
            DontDestroyOnLoad(gameObject);
        }

        public async void HttpPost(string jsonStr, HttpPath path)
        {
            Debug.Log($"Http post: {jsonStr}");
            var host = DungeonLabUtility.GetLocalIPv4();
            var uri = $"http://{host}:{port}/{path.ToString().ToLower()}";
            using (HttpClient client = new HttpClient())
            {
                HttpContent content = new StringContent(jsonStr, System.Text.Encoding.UTF8, "application/json");
                HttpResponseMessage response = await client.PostAsync(uri, content);
                response.EnsureSuccessStatusCode();
                string responseBody = await response.Content.ReadAsStringAsync();
            }
        }

        //[Button("SendAllDungeonLabPresetPulseMessage")]
        public void SendAllDungeonLabPresetPulseMessage(DungeonLabChannel channel)
        {
            var presetWaveDataDict = DungeonLabUtility.PresetPulseDataDict;
            foreach (var presetKey in presetWaveDataDict.Keys)
            {
                SendDungeonLabPresetPulseMessage(channel, presetKey);
            }
        }

        //[Button("SendDungeonLabPresetPulseMessage")]
        public void SendDungeonLabPresetPulseMessage(DungeonLabChannel channel, string presetKey)
        {
            var preset = DungeonLabUtility.GetPresetWaveData(presetKey);
            var messageData = new DungeonLabPresetPulseMessage
            {
                channel = channel,
                preset = preset
            };
            string message = JsonUtility.ToJson(messageData);
            HttpPost(message, HttpPath.DUNGEON_LAB_PRESET_PULSE_MESSAGE);
        }

        //[Button("SendDungeonLabPulseMessage")]
        public void SendDungeonLabPulseMessage(DungeonLabChannel channel, string pulseStr)
        {
            var messageData = new DungeonLabPulseMessage
            {
                channel = channel,
                pulse = pulseStr
            };
            string message = JsonUtility.ToJson(messageData);
            HttpPost(message, HttpPath.DUNGEON_LAB_PULSE_MESSAGE);
        }

        //[Button("SendDungeonLabClearMessage")]
        public void SendDungeonLabClearMessage(DungeonLabChannel channel)
        {
            var messageData = new DungeonLabClearMessage
            {
                channel = channel,
            };
            string message = JsonUtility.ToJson(messageData);
            HttpPost(message, HttpPath.DUNGEON_LAB_CLEAR_MESSAGE);
        }

        //[Button("SendDungeonLabStrengthMessage")]
        public void SendDungeonLabStrengthMessage(DungeonLabChannel channel, DungeonLabStrengthChangeMode mode, int value)
        {
            var messageData = new DungeonLabStrengthMessage
            {
                channel = channel,
                mode = mode,
                value = value,
            };
            string message = JsonUtility.ToJson(messageData);
            HttpPost(message, HttpPath.DUNGEON_LAB_STRENGTH_MESSAGE);
        }

        //[Button("SendDungeonLabMessage")]
        public void SendDungeonLabMessage(DungeonLabMessageType messageType, string message)
        {
            var messageData = new SimpleDungeonLabMessage
            {
                type = messageType.ToString().ToLower(),
                message = message
            };
            string dungeonLabMessage = JsonUtility.ToJson(messageData);
            HttpPost(dungeonLabMessage, HttpPath.DUNGEON_LAB_MESSAGE);
        }
    }
    public enum HttpPath
    {
        DUNGEON_LAB_MESSAGE = 0,
        DUNGEON_LAB_STRENGTH_MESSAGE = 1,
        DUNGEON_LAB_CLEAR_MESSAGE = 2,
        DUNGEON_LAB_PULSE_MESSAGE = 3,
        DUNGEON_LAB_PRESET_PULSE_MESSAGE = 4,
    }

    public struct SimpleDungeonLabMessage
    {
        public string type;
        public string message;
    }

    public struct DungeonLabStrengthMessage
    {
        public DungeonLabChannel channel;
        public DungeonLabStrengthChangeMode mode;
        public int value;
    }

    public struct DungeonLabClearMessage
    {
        public DungeonLabChannel channel;
    }

    public struct DungeonLabPulseMessage
    {
        public DungeonLabChannel channel;
        public string pulse;
    }

    public struct DungeonLabPresetPulseMessage
    {
        public DungeonLabChannel channel;
        public string preset;
    }
}

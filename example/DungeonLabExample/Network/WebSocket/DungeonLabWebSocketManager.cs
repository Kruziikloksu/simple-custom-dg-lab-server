using Sirenix.OdinInspector;
using System;
using System.Net.WebSockets;
using UnityEngine;

namespace CustomDungeonLab
{
    public class DungeonLabWebSocketManager : MonoBehaviour
    {
        public static DungeonLabWebSocketManager Instance { get; private set; }
        private WebSocketClient client;
        public int port = 4503;
        public string clientId = "";
        public string targetId = "";
        public int strengthA = 0;
        public int strengthB = 0;
        public int strengthLimitA = 0;
        public int strengthLimitB = 0;

        private void Awake()
        {
            Application.runInBackground = true;
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
            DontDestroyOnLoad(gameObject);
        }

        private void Start()
        {
            client = new WebSocketClient();
            client.OnConnected += OnConnected;
            client.OnClosed += OnClosed;
            client.OnMessageReceived += OnMessageReceived;
            client.OnError += OnError;
        }

        private void OnDisable()
        {
            Close();
        }

        private void Update()
        {
            client?.Update();
        }

        #region Connect
        [Button("Connect")]
        public void Connect(string host = null)
        {
            if (string.IsNullOrEmpty(host))
            {
                host = DungeonLabUtility.GetLocalIPv4();
            }
            var uri = $"ws://{host}:{port}";
            client?.Connect(uri);
        }

        [Button("Close")]
        public void Close()
        {
            client?.Close();
        }

        public void OnConnected()
        {
            Debug.Log($"WebSocketConnected!");
            ClearBind();
        }

        public void OnClosed()
        {
            Debug.Log($"WebSocketClosed!");
            ClearBind();
        }

        public void ClearBind()
        {
            clientId = "";
            targetId = "";
            strengthA = 0;
            strengthB = 0;
            strengthLimitA = 0;
            strengthLimitB = 0;
        }

        public void OnError(Exception e)
        {
            if(e is WebSocketException)
            {
                Close();
                ClearBind();
            }
            Debug.LogError($"ConnectError: {e.Message}");
        }

        public void OnMessageReceived(string message)
        {
            Debug.Log($"ReceiveMessage: {message}");
            DungeonLabMessage messageData = JsonUtility.FromJson<DungeonLabMessage>(message);
            if (messageData.type == "bind")
            {
                if (messageData.message == "targetId")
                {
                    clientId = messageData.clientId;
                }
                else if (messageData.message == "DGLAB")
                {
                    if (messageData.clientId == clientId)
                    {
                        targetId = messageData.targetId;
                    }
                }
            }
            else if (messageData.type == "msg")
            {
                if (messageData.message.StartsWith("strength"))
                {
                    var strengthArr = messageData.message.Split("-");
                    var strengthStr = strengthArr[1];
                    var strengthValueArr = strengthStr.Split("+");
                    strengthA = int.Parse(strengthValueArr[0]);
                    strengthB = int.Parse(strengthValueArr[1]);
                    strengthLimitA = int.Parse(strengthValueArr[2]);
                    strengthLimitB = int.Parse(strengthValueArr[3]);
                }
                else if (messageData.message.StartsWith("feedback"))
                {
                    var feedbackArr = messageData.message.Split("-");
                    var feedbackStr = feedbackArr[1];
                    var feedbackValue = int.Parse(feedbackStr);
                    if (feedbackValue == (int)DungeonLabFeedback.CIRCLE_A)
                    {
                        Debug.Log("收到反馈 A通道○");
                    }
                    else if (feedbackValue == (int)DungeonLabFeedback.TRIANGLE_A)
                    {
                        Debug.Log("收到反馈 A通道△");
                    }
                    else if (feedbackValue == (int)DungeonLabFeedback.SQUARE_A)
                    {
                        Debug.Log("收到反馈 A通道□");
                    }
                    else if (feedbackValue == (int)DungeonLabFeedback.STAR_A)
                    {
                        Debug.Log("收到反馈 A通道☆");
                    }
                    else if (feedbackValue == (int)DungeonLabFeedback.HEXAGON_A)
                    {
                        Debug.Log("收到反馈 A通道⬡");
                    }
                    else if (feedbackValue == (int)DungeonLabFeedback.CIRCLE_B)
                    {
                        Debug.Log("收到反馈 B通道○");
                    }
                    else if (feedbackValue == (int)DungeonLabFeedback.TRIANGLE_B)
                    {
                        Debug.Log("收到反馈 B通道△");
                    }
                    else if (feedbackValue == (int)DungeonLabFeedback.SQUARE_B)
                    {
                        Debug.Log("收到反馈 B通道□");
                    }
                    else if (feedbackValue == (int)DungeonLabFeedback.STAR_B)
                    {
                        Debug.Log("收到反馈 B通道☆");
                    }
                    else if (feedbackValue == (int)DungeonLabFeedback.HEXAGON_B)
                    {
                        Debug.Log("收到反馈 B通道⬡");
                    }
                }
            }
            else if (messageData.type == "heartbeat")
            {

            }
            else if (messageData.type == "break")
            {
                Close();
                ClearBind();
            }
            else if (messageData.type == "error")
            {
                Debug.LogError(messageData.message);
            }
            else
            {
                //TODO
            }
        }
        #endregion

        #region Send
        public void Send(string message)
        {
            Debug.Log("Send message: " + message);
            client?.Send(message);
        }

        [Button("SendAllPresetPulseData")]
        public void SendAllDungeonLabPresetPulseMessage(DungeonLabChannel channel)
        {
            var presetWaveDataDict = DungeonLabUtility.PresetPulseDataDict;
            foreach (var presetKey in presetWaveDataDict.Keys)
            {
                SendDungeonLabPresetPulseMessage(channel, presetKey);
            }
        }

        [Button("SendDungeonLabPresetPulseMessage")]
        public void SendDungeonLabPresetPulseMessage(DungeonLabChannel channel, string presetKey)
        {
            var preset = DungeonLabUtility.GetPresetWaveData(presetKey);
            SendDungeonLabMessage(DungeonLabMessageType.CUSTOM, $"preset-{channel}:{preset}");
        }

        [Button("SendDungeonLabPulseMessage")]
        public void SendDungeonLabPulseMessage(DungeonLabChannel channel, string pulseStr)
        {
            SendDungeonLabMessage(DungeonLabMessageType.MSG, $"pulse-{channel}:{pulseStr}");
        }

        [Button("SendDungeonLabClearMessage")]
        public void SendDungeonLabClearMessage(DungeonLabChannel channel)
        {
            SendDungeonLabMessage(DungeonLabMessageType.MSG, $"clear-{(int)channel}");
        }

        [Button("SendDungeonLabStrengthMessage")]
        public void SendDungeonLabStrengthMessage(DungeonLabChannel channel, DungeonLabStrengthChangeMode mode, int value)
        {
            SendDungeonLabMessage(DungeonLabMessageType.MSG, $"strength-{(int)channel}+{(int)mode}+{value}");
        }

        [Button("SendDungeonLabMessage")]
        public void SendDungeonLabMessage(DungeonLabMessageType messageType, string message)
        {
            var messageData = new DungeonLabMessage
            {
                type = messageType.ToString().ToLower(),
                clientId = clientId,
                targetId = targetId,
                message = message
            };
            string dungeonLabMessage = JsonUtility.ToJson(messageData);
            Send(dungeonLabMessage);
        }
        #endregion
    }

    public struct DungeonLabMessage
    {
        public string type;
        public string clientId;
        public string targetId;
        public string message;
    }


}
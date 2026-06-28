using System;
using System.Collections.Concurrent;
using System.IO;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

public class WebSocketClient
{
    private ClientWebSocket webSocket;
    private CancellationTokenSource cancellation;
    private readonly byte[] receiveBuffer = new byte[8192];
    private readonly ConcurrentQueue<Action> mainThreadActions = new();

    public event Action<string> OnMessageReceived;
    public event Action OnConnected;
    public event Action OnClosed;
    public event Action<Exception> OnError;

    private bool isConnected;
    private bool closeNotified;

    public async void Connect(string uri)
    {
        if (isConnected) return;

        CloseSocketResources();
        webSocket = new ClientWebSocket();
        cancellation = new CancellationTokenSource();
        closeNotified = false;

        try
        {
            await webSocket.ConnectAsync(new Uri(uri), cancellation.Token);
            isConnected = true;
            EnqueueToMainThread(() => OnConnected?.Invoke());
            _ = ReceiveLoop();
        }
        catch (Exception ex)
        {
            CloseSocketResources();
            EnqueueToMainThread(() => OnError?.Invoke(ex));
        }
    }

    public async void Send(string message)
    {
        var socket = webSocket;
        var token = cancellation?.Token ?? CancellationToken.None;
        if (socket?.State == WebSocketState.Open)
        {
            var bytes = Encoding.UTF8.GetBytes(message);
            var segment = new ArraySegment<byte>(bytes);

            try
            {
                await socket.SendAsync(segment, WebSocketMessageType.Text, true, token);
            }
            catch (Exception ex)
            {
                EnqueueToMainThread(() => OnError?.Invoke(ex));
                Close();
            }
        }
    }

    public async void Close()
    {
        var socket = webSocket;
        var tokenSource = cancellation;
        if (!isConnected && socket == null) return;

        isConnected = false;
        tokenSource?.Cancel();

        try
        {
            if (socket != null &&
                (socket.State == WebSocketState.Open ||
                 socket.State == WebSocketState.CloseReceived ||
                 socket.State == WebSocketState.CloseSent))
            {
                await socket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Closed by client", CancellationToken.None);
            }
        }
        catch (OperationCanceledException)
        {
        }
        catch (Exception ex)
        {
            EnqueueToMainThread(() => OnError?.Invoke(ex));
        }
        finally
        {
            CloseSocketResources(socket, tokenSource);
            NotifyClosedOnce();
        }
    }

    private async Task ReceiveLoop()
    {
        var socket = webSocket;
        var tokenSource = cancellation;
        var token = tokenSource?.Token ?? CancellationToken.None;
        try
        {
            while (socket != null && socket.State == WebSocketState.Open)
            {
                var result = await ReceiveMessage(socket, token);
                if (result.MessageType == WebSocketMessageType.Close)
                {
                    await socket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Closed by server", token);
                    isConnected = false;
                    NotifyClosedOnce();
                    break;
                }

                EnqueueToMainThread(() => OnMessageReceived?.Invoke(result.Message));
            }
        }
        catch (OperationCanceledException)
        {
        }
        catch (Exception ex)
        {
            EnqueueToMainThread(() => OnError?.Invoke(ex));
        }
        finally
        {
            isConnected = false;
            CloseSocketResources(socket, tokenSource);
            NotifyClosedOnce();
        }
    }

    private async Task<WebSocketReceiveResultData> ReceiveMessage(ClientWebSocket socket, CancellationToken token)
    {
        using (var stream = new MemoryStream())
        {
            WebSocketReceiveResult result;

            do
            {
                result = await socket.ReceiveAsync(new ArraySegment<byte>(receiveBuffer), token);
                if (result.MessageType == WebSocketMessageType.Close)
                {
                    return new WebSocketReceiveResultData(result.MessageType, string.Empty);
                }

                stream.Write(receiveBuffer, 0, result.Count);
            }
            while (!result.EndOfMessage);

            string message = Encoding.UTF8.GetString(stream.ToArray());
            return new WebSocketReceiveResultData(result.MessageType, message);
        }
    }

    private void EnqueueToMainThread(Action action)
    {
        mainThreadActions.Enqueue(action);
    }

    public void DispatchMainThreadActions()
    {
        while (mainThreadActions.TryDequeue(out var action))
        {
            action?.Invoke();
        }
    }
    public void Update()
    {
        DispatchMainThreadActions();
    }

    private void NotifyClosedOnce()
    {
        if (closeNotified) return;

        closeNotified = true;
        EnqueueToMainThread(() => OnClosed?.Invoke());
    }

    private void CloseSocketResources(ClientWebSocket expectedSocket = null, CancellationTokenSource expectedCancellation = null)
    {
        if (expectedCancellation == null || cancellation == expectedCancellation)
        {
            cancellation?.Dispose();
            cancellation = null;
        }

        if (expectedSocket == null || webSocket == expectedSocket)
        {
            webSocket?.Dispose();
            webSocket = null;
        }
    }

    private struct WebSocketReceiveResultData
    {
        public WebSocketReceiveResultData(WebSocketMessageType messageType, string message)
        {
            MessageType = messageType;
            Message = message;
        }

        public WebSocketMessageType MessageType { get; }
        public string Message { get; }
    }
}

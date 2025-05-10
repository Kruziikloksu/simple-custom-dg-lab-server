using System;
using System.Collections.Concurrent;
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

    public async void Connect(string uri)
    {
        if (isConnected) return;

        webSocket = new ClientWebSocket();
        cancellation = new CancellationTokenSource();

        try
        {
            await webSocket.ConnectAsync(new Uri(uri), cancellation.Token);
            isConnected = true;
            EnqueueToMainThread(() => OnConnected?.Invoke());
            _ = ReceiveLoop();
        }
        catch (Exception ex)
        {
            EnqueueToMainThread(() => OnError?.Invoke(ex));
        }
    }

    public async void Send(string message)
    {
        if (webSocket?.State == WebSocketState.Open)
        {
            var bytes = Encoding.UTF8.GetBytes(message);
            var segment = new ArraySegment<byte>(bytes);

            try
            {
                await webSocket.SendAsync(segment, WebSocketMessageType.Text, true, cancellation.Token);
            }
            catch (Exception ex)
            {
                EnqueueToMainThread(() => OnError?.Invoke(ex));
            }
        }
    }

    public async void Close()
    {
        if (!isConnected) return;

        isConnected = false;
        cancellation?.Cancel();

        try
        {
            if (webSocket != null &&
                (webSocket.State == WebSocketState.Open ||
                 webSocket.State == WebSocketState.CloseReceived ||
                 webSocket.State == WebSocketState.CloseSent))
            {
                await webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Closed by client", CancellationToken.None);
            }
        }
        catch (Exception ex)
        {
            EnqueueToMainThread(() => OnError?.Invoke(ex));
        }
        finally
        {
            EnqueueToMainThread(() => OnClosed?.Invoke());
        }
    }

    private async Task ReceiveLoop()
    {
        try
        {
            while (webSocket.State == WebSocketState.Open)
            {
                var result = await webSocket.ReceiveAsync(new ArraySegment<byte>(receiveBuffer), cancellation.Token);
                if (result.MessageType == WebSocketMessageType.Close)
                {
                    await webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Closed by server", cancellation.Token);
                    EnqueueToMainThread(() => OnClosed?.Invoke());
                    break;
                }

                string message = Encoding.UTF8.GetString(receiveBuffer, 0, result.Count);
                EnqueueToMainThread(() => OnMessageReceived?.Invoke(message));
            }
        }
        catch (OperationCanceledException)
        {
        }
        catch (Exception ex)
        {
            EnqueueToMainThread(() => OnError?.Invoke(ex));
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
}

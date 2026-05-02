Imports System.Text
Imports System.Threading.Tasks
Imports MQTTnet
Imports MQTTnet.Client
Imports MQTTnet.Extensions.ManagedClient
Imports MQTTnet.Protocol

Public Class MqttBridge
    Private ReadOnly _client As IManagedMqttClient

    Public Sub New()
        _client = New MqttFactory().CreateManagedMqttClient()
    End Sub

    Public Async Function ConnectAsync(broker As String, port As Integer) As Task
        ' — Wire up the async events instead of UseXxxHandler or Handler properties —
        AddHandler _client.ConnectedAsync, AddressOf OnConnectedAsync
        AddHandler _client.DisconnectedAsync, AddressOf OnDisconnectedAsync
        AddHandler _client.ConnectingFailedAsync, AddressOf OnConnectingFailedAsync
        AddHandler _client.ApplicationMessageReceivedAsync, AddressOf OnMessageAsync

        ' Build your managed‐client options
        Dim clientOpts As MqttClientOptions = New MqttClientOptionsBuilder() _
                            .WithTcpServer(broker, port) _
                            .WithCleanSession() _
                            .WithKeepAlivePeriod(TimeSpan.FromSeconds(30)) _
                            .Build()

        Dim managedOpts As ManagedMqttClientOptions = New ManagedMqttClientOptionsBuilder() _
                             .WithClientOptions(clientOpts) _
                             .WithAutoReconnectDelay(TimeSpan.FromSeconds(5)) _
                             .Build()

        ' Start (this returns immediately)
        Await _client.StartAsync(managedOpts)

        ' Then subscribe
        Await _client.SubscribeAsync("py_to_vb")
    End Function

    Private Function OnConnectedAsync(e As MqttClientConnectedEventArgs) As Task
        Console.WriteLine("Connected")
        Return Task.CompletedTask
    End Function

    Private Function OnDisconnectedAsync(e As MqttClientDisconnectedEventArgs) As Task
        Console.WriteLine($"Disconnected (Reason={e.Reason}) — will auto-reconnect…")
        Return Task.CompletedTask
    End Function

    Private Function OnConnectingFailedAsync(e As ConnectingFailedEventArgs) As Task
        Console.WriteLine($"Connect failed: {e.Exception.Message}")
        Return Task.CompletedTask
    End Function

    Public Function OnMessageAsync(e As MqttApplicationMessageReceivedEventArgs) As Task
        Dim segment As ArraySegment(Of Byte) = e.ApplicationMessage.PayloadSegment
        Dim payload As String

        If segment.Count > 0 Then
            payload = Encoding.UTF8.GetString(segment.Array,
                                          segment.Offset,
                                          segment.Count)
        Else
            payload = "[no payload]"
        End If

        Console.WriteLine($"Python → VB: {payload}")
        Return Task.CompletedTask
    End Function

    Public Async Function PublishAsync(payload As String) As Task
        Await _client.EnqueueAsync("vb_to_py",
                                   payload,
                                   MqttQualityOfServiceLevel.AtLeastOnce)
    End Function
End Class

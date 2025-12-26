import paho.mqtt.client as mqtt

class MqttClientLocal:
    def handle(self):
        def on_connect(client, userdata, flags, rc):
            print(f'Connected to MQTT broker with result code {rc}')
            client.subscribe('#')

        def on_message(client, userdata, msg):
            print(f'Message received: {msg.topic} {msg.payload}')

        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message

        broker = 'localhost'  # Use 'localhost' if running locally, or 'mqtt' if running in Docker
        port = 1883

        client.connect(broker, port, 60)

        try:
            client.loop_forever()
        except KeyboardInterrupt:
            print('MQTT client stopped.')

if __name__ == "__main__":
    MqttClientLocal().handle()
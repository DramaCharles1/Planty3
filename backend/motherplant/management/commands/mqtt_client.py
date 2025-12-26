from django.core.management.base import BaseCommand
import paho.mqtt.client as mqtt
import time

class Command(BaseCommand):
    help = 'Runs the MQTT client as a management command.'

    def handle(self, *args, **options):
        def on_connect(client, userdata, flags, rc):
            self.stdout.write(self.style.SUCCESS(f'Connected to MQTT broker with result code {rc}'))
            # Subscribe to topics here
            client.subscribe('#')

        def on_message(client, userdata, msg):
            self.stdout.write(self.style.NOTICE(f'Message received: {msg.topic} {msg.payload}'))
            # Add your message handling logic here

        self.stdout.write("Starting MQTT client...")
        client = mqtt.Client()
        self.stdout.write("MQTT Client initialized.")
        client.on_connect = on_connect
        self.stdout.write("on_connect callback set.")
        client.on_message = on_message
        self.stdout.write("on_message callback set.")

        # Set your MQTT broker address and port
        broker = 'mqtt'  # Use service name from docker-compose
        #broker = 'localhost'  # Use locahost when running locally
        port = 1883
        self.stdout.write(f"Connecting to MQTT broker at {broker}:{port}...")
        client.connect(broker, port, 60)
        self.stdout.write("Connected to MQTT broker. Starting loop...")

        try:
            client.loop_forever()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('MQTT client stopped.'))

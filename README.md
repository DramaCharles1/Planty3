# Planty3
3rd time is the charm


## Docker

Start Docker service:\
`sudo service docker start`

## MQTT

**Mosquitto**

Subscribe to telemetry topic example:

`mosquitto_sub -h localhost -p 1883 -t "planty/plant/plant01/telemetry/moisture"`

Publish telemetry to topic example:

`mosquitto_pub -h localhost -p 1883 -t "planty/plant/plant01/telemetry/moisture" -m '{"value":45.2,"ts":1766644800}'`

Subscribe to status topic example:

`mosquitto_sub -h localhost -p 1883 -t "planty/plant/plant01/status"`

Publish status (online) to topic example:

`mosquitto_pub -h localhost -p 1883 -t "planty/plant/plant01/status" -m '{"online":true,"ts":1766644800}' -r`

Publish status (offline) to topic example:

`mosquitto_pub -h localhost -p 1883 -t "planty/plant/plant01/status" -m '{"online":false,"ts":1766644800}' -r`

**Note:** The `-r` flag sets the message as retained, which is recommended for status messages.

Subscribe to command topic example:

`mosquitto_sub -h localhost -p 1883 -t "planty/plant/plant01/command/+"`

Publish command to topic example:

`mosquitto_pub -h localhost -p 1883 -t "planty/plant/plant01/command/water" -m '{"cmd_id":"test-123","ts":1766644800,"duration":30}' -q 1`

Subscribe to command ack topic example:

`mosquitto_sub -h localhost -p 1883 -t "planty/plant/plant01/command/+/ack"`

Publish command ack to topic example:

`mosquitto_pub -h localhost -p 1883 -t "planty/plant/plant01/command/water/ack" -m '{"cmd_id":"test-123","ts":1766644800,"ok":true,"error":""}'`

**Note:** Commands use QoS 1 (`-q 1` flag) for reliable delivery.

## Database

**Postgre**

1. Start postgre service: `docker compose up postgres`
2. Start Adminer service: `docker compose up adminer`
3. Go to Adminer web interface at `http://localhost:8080`
4. Log in using POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB. Use db service name (postgre) for "server". System should be PostgreSQL.

## Django

**Super user**\
Username: root\
Email address: root@test.com\
Password: password

**Test**\
Run tests for Django motherplant app

***From Docker***\
backend or mqtt_client service must run\
`docker compose exec mqtt_client python manage.py test motherplant`
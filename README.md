# Planty3
3rd time is the charm


## Docker

Start Docker service:\
`sudo service docker start`

## MQTT

**Mosquitto**

Subscribe to topic example

`mosquitto_sub -h localhost -p 1883 -t "planty/plant01/telemetry/temperature"`

Publish to topic example:

`mosquitto_pub -h localhost -p 1883 -t "planty/plant01/telemetry/temperature" -m '{"value":30.5,"unit":"C","ts":1766644800}'`

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
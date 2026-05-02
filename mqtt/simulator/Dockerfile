FROM python:3.12-slim

WORKDIR /app

COPY core/core_layer.py .

COPY simulator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY simulator/plant_simulator.py .

CMD ["python", "-u", "plant_simulator.py"]

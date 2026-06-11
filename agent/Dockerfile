FROM python:3.11-slim

WORKDIR /app

# Installation des dépendances avant de copier le code (optimise le cache Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie de tous les scripts de l'agent (agent.py, toolbox.py, fsm.py...)
COPY . .

CMD ["python", "agent_cloud.py"]
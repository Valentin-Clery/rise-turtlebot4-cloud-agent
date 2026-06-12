import asyncio
import json
import time
import os
import websockets
from openai import OpenAI
from numpy import pi, inf

from fsm import fsm
from toolbox import FunctionsToolsCloud, ActionData

ROSBRIDGE_IP = "localhost"
ROSBRIDGE_PORT = 9090
URI = f"ws://{ROSBRIDGE_IP}:{ROSBRIDGE_PORT}"

class RobotAgentCloud:
    def __init__(self, Hz):
        self.uri = URI
        self.ws = None # Contiendra la connexion WebSocket active

        # Configuration Groq / OpenAI API
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.environ.get("GROQ_API_KEY")
        )
        self.model_name = "llama-3.1-8b-instant"

        self.toolbox = FunctionsToolsCloud(self.uri, None)
        self.tools = self.toolbox.get_tools_def()

# Initialisation de la mémoire de la mission
        self.chat_history = []
        self.user_input = None
        self.cmd_queue = []
        self.Hz = Hz
        self.T = 1.0 / Hz

        self.call_action = None
        self.actionData = None
        self.cpt_llm_action = 0.0
        self.start_time_action = None
        self.current_publish_msg = None

        # Configuration propre de la FSM
        self.fs = fsm([
            ('Start', 'UserPrompting', True),
            # Reste en UserPrompting tant qu'aucune commande valide n'est reçue dans self.user_input
            ('UserPrompting', 'UserPrompting', self.KeepAsk, self.ask_user),
            ('UserPrompting', 'LLM_ReadQueue', self.check_Prompt_To_Action, self.ReadQueue),
            ('LLM_ReadQueue', 'LLM_ReadQueue', False),
            ('LLM_ReadQueue', 'UserPrompting', self.fail_ReadQueue, self.ask_user),
            ('LLM_ReadQueue', 'LLM_Action', self.check_ReadQueue, self.DoAction),
            ('LLM_Action', 'LLM_Action', self.KeepAction, self.DoAction),
            ('LLM_Action', 'STOP', self.check_STOP, self.DoSTOP),
            ('STOP', 'STOP', self.KeepSTOP, self.DoSTOP),
            ('STOP', 'LLM_ReadQueue', self.check_NextAction, self.ReadQueue),
            ('STOP', 'UserPrompting', self.check_Return_To_Prompt, self.ask_user)
        ])
        self.fs.start("Start")
        print("--- Agent LLM RISE Hybride (Groq Llama 3.1) Initialisé ---")

    def ask_user(self, fss, value):
        """
        Méthode non-bloquante : Si self.user_input a été rempli par le spin_loop (via Rosbridge),
        on déclenche l'appel LLM, sinon on passe simplement au tick suivant.
        """
        if self.user_input is not None and self.user_input.strip() != "":
            print(f"📥 Nouveau prompt reçu de l'interface Web : {self.user_input}")

            # Réinitialisation de la mémoire pour la nouvelle mission
            self.chat_history = [
                {'role': 'system', 'content': (
                    "Tu es le cerveau algorithmique d'un TurtleBot 4. Ton objectif est d'accomplir la mission de l'utilisateur "
                    "en appelant les fonctions à ta disposition de manière séquentielle.\n"
                    "Après chaque action, tu recevras une 'Observation'. Analyse-la pour planifier l'action suivante."
                )}
            ]

            prompt_a_envoyer = self.user_input
            self.user_input = None  # Consommé
            self.send_prompt(user_prompt=prompt_a_envoyer)

    def send_prompt(self, user_prompt=None, observation_prompt=None):
        # 1. Si c'est le premier ordre de l'utilisateur
        if user_prompt is not None:
            self.chat_history.append({'role': 'user', 'content': user_prompt})

        # 2. Si c'est un retour d'observation (YOLO ou fin de mouvement)
        if observation_prompt is not None:
            self.chat_history.append({'role': 'user', 'content': f"[Observation] : {observation_prompt}"})

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=self.chat_history, # On passe tout l'historique
                temperature=0.1,            # Légère créativité mais reste focalisé
                tools=self.tools,
                tool_choice="auto"
            )

            message = response.choices[0].message
            # On enregistre la réponse du LLM (ses pensées ou ses appels d'outils) dans l'historique
            self.chat_history.append(message)

            if message.content:
                print(f"🧠 [Raisonnement LLM] : {message.content}")
                # Envoi du raisonnement textuel au Dashboard Web via le topic dédié
                self.publish_to_web("/agent/response", message.content)

            if message.tool_calls:
                new_actions = []
                for tool_call in message.tool_calls:
                    call_dict = {
                        'function': {
                            'name': tool_call.function.name,
                            'arguments': json.loads(tool_call.function.arguments)
                        }
                    }
                    new_actions.append(call_dict)
                self.cmd_queue = new_actions
                print(f"📥 Nouvelle planification : {len(self.cmd_queue)} actions dans la file.")
            else:
                # Si le LLM ne donne pas d'outil, il considère que la mission est finie
                print("🏁 Pas d'outil requis par le LLM pour cette étape.")
                self.cmd_queue = []

        except Exception as e:
            print(f"Erreur Groq API : {e}")
            self.cmd_queue = []

    def publish_to_web(self, topic, text_data):
        """Prépare et planifie l'envoi d'un message String ROS 2 vers le Rosbridge"""
        if self.ws:
            msg = {
                "op": "publish",
                "topic": topic,
                "msg": {
                    "data": str(text_data)
                }
            }
            # Utilisation de ensure_future car on est dans une fonction synchrone appelée par la FSM
            asyncio.ensure_future(self.ws.send(json.dumps(msg)))

    def KeepAsk(self, fss): return (not(self.check_Prompt_To_Action(fss)))
    def check_Prompt_To_Action(self, fss): return (len(self.cmd_queue) != 0)
    def fail_ReadQueue(self, fss): return (self.call_action is None)
    def check_ReadQueue(self, fss): return (self.call_action is not None)
    def KeepAction(self, fss): return (not(self.check_STOP(fss)))
    def check_NextAction(self, fss): return (len(self.cmd_queue) != 0)
    def check_Return_To_Prompt(self, fss): return (len(self.cmd_queue) == 0)

    def ReadQueue(self, fss, value):
        try: self.call_action = self.cmd_queue.pop(0)
        except IndexError: self.call_action = None

    def DoAction(self, fss, value):
        if self.start_time_action is None:
            self.start_time_action = time.time()
            self.cpt_llm_action = 0.0

            # 1. On lance la génération du message via la toolbox
            self.action_task = asyncio.create_task(self.toolbox.call_function_async(self.call_action))
            self.actionData = None
            return # On attend le prochain tick pour avoir le résultat

        # 2. Dès que la tâche a répondu, on extrait les données de mouvement UNE SEULE FOIS
        if hasattr(self, 'action_task') and self.action_task.done() and self.actionData is None:
            try:
                self.actionData = self.action_task.result()
                if self.actionData.actionType == 'physical':
                    self.current_publish_msg = self.actionData.data
                    print(f"🚀 exécution de l'action physique pendant {self.actionData.duration}s")
            except Exception as e:
                print(f"Erreur lors de l'exécution de l'action : {e}")
                self.actionData = ActionData('error', 0, str(e))

        # 3. On incrémente le compteur de temps uniquement si l'action a commencé à publier
        if self.actionData is not None:
            self.cpt_llm_action = time.time() - self.start_time_action

    def check_STOP(self, fss):
        if hasattr(self, 'action_task') and not self.action_task.done():
            return False
        if self.actionData is None: 
            return False

        match self.actionData.actionType:
            case 'physical':
                # Le mouvement est fini ! On en informe le LLM pour qu'il décide de la suite
                obs = "Action de mouvement réussie. Le robot s'est déplacé."
                self.send_prompt(observation_prompt=obs)
                self.cmd_queue = []
                return True

            case 'yolo_img':
                yolo_data = self.actionData.data
                if not yolo_data:
                    obs = "L'analyse caméra n'a détecté absolument aucun objet ou personne dans le champ de vision."
                else:
                    detections = []
                    for item in yolo_data:
                        degree_info = "à ta droite" if item.get('angle', 0) < 0 else "à ta gauche"
                        detections.append(f"un(e) {item['object']} à {item.get('distance', 999):.2f} mètres, positionné(e) à {abs(item.get('angle', 0)):.2f} radian {degree_info}")
                    obs = f"L'analyse caméra montre les détections suivantes : {', '.join(detections)}."

                print(f"👀 [YOLO Observation] : {obs}")
                self.publish_to_web("/agent/response", f"👁️ Observation caméra envoyée au LLM.")
                self.send_prompt(observation_prompt=obs) 
                return True

            case _:
                return True

    def DoSTOP(self, fss, value):
        print("🛑 Fin de l'action détectée. Envoi du message d'arrêt.")
        self.cpt_llm_action = 0.0
        self.call_action = None
        self.actionData = None
        self.start_time_action = None

        # Nettoyage de la tâche (CORRECTION DE L'INDENTATION ICI)
        if hasattr(self, 'action_task'):
            delattr(self, 'action_task')

        # On force l'arrêt des moteurs
        self.current_publish_msg = {
            "op": "publish",
            "topic": "/cmd_vel",
            "msg": {
                "header": {"frame_id": "base_link"},
                "twist": {
                    "linear": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "angular": {"x": 0.0, "y": 0.0, "z": 0.0}
                }
            }
        }

    def KeepSTOP(self, fss):
        return (not(self.check_NextAction(fss)) and not(self.check_Return_To_Prompt(fss)))

    async def spin_loop(self):
        """Boucle d'exécution asynchrone principale connectée à Rosbridge"""
        async with websockets.connect(self.uri) as ws:
            self.ws = ws  # Sauvegarde de la session globale pour les envois spontanés
            print("[Cloud Agent] Connecté au Rosbridge local !")
            
            # CORRECTION : S'abonner au bon topic configuré côté front-end
            subscribe_msg = {
                "op": "subscribe",
                "topic": "/agent/request_prompt",
                "type": "std_msgs/msg/String"
            }
            await ws.send(json.dumps(subscribe_msg))

            # Nettoyage des doublons de boucle (un seul sleep et structure épurée par cycle)
            while True:
                try:
                    raw_data = await asyncio.wait_for(ws.recv(), timeout=0.001)
                    data = json.loads(raw_data)

                    if data.get("op") == "publish" and data.get("topic") == "/agent/request_prompt":
                        msg_payload = data.get("msg", {})
                        if isinstance(msg_payload, dict):
                            self.user_input = msg_payload.get("data", "")
                        else:
                            self.user_input = msg_payload
                        print(f"📡 [WebSocket Réception brute] self.user_input est maintenant : {self.user_input}") # <-- AJOUTE CECI
                except asyncio.TimeoutError:
                    pass
                except Exception as e:
                    print(f"Erreur lors de la réception WebSocket : {e}")

                # 1. Exécution d'un tick de la FSM (Non bloquant)
                self.fs.event("")

                # 2. Envoi continu des consignes de vitesse en cours (/cmd_vel)
                if self.current_publish_msg:
                    try:
                        await ws.send(json.dumps(self.current_publish_msg))
                    except Exception as e:
                        print(f"Erreur d'envoi de flux vers le robot : {e}")

                await asyncio.sleep(self.T)

if __name__ == '__main__':
    Hz = 20  
    agent = RobotAgentCloud(Hz)
    try:
        asyncio.run(agent.spin_loop())
    except KeyboardInterrupt:
        print("Arrêt de l'agent cloud.")
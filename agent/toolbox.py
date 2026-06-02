import json
import asyncio
import websockets
from dataclasses import dataclass
import math
from numpy import pi

@dataclass
class ActionData():
    actionType : str
    duration: float
    data : dict|str|list

class FunctionsToolsCloud():
    def __init__(self, rosbridge_uri, logger, linear_speed: float = 0.2, angular_speed: float = 0.5):
        self.uri = rosbridge_uri
        self.log = logger
        self.lin_speed = linear_speed
        self.ang_speed = angular_speed

        # Variables odométriques locales pour le suivi de trajectoire
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_yaw = 0.0

    def get_tools_def(self):
        return [
            {
                'type': 'function',
                'function': {
                    'name': 'move_robot',
                    'description': 'Move the robot straight on a given distance in meters.',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'distance': {'type': 'number', 'description': 'Distance in meters to travel'},
                            'direction': {'type': 'string', 'enum': ['forward', 'backward']}
                        },
                        'required': ['distance', 'direction'],
                    },
                },
            }, {
                'type': 'function',
                'function': {
                    'name': 'turn_robot',
                    'description': 'Rotate Robot to the left or right for a given angle in radians.',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'angle': {'type': 'number', 'description': 'Angle in radians to rotate'},
                            'direction': {'type': 'string', 'enum': ['left', 'right']}
                        },
                        'required': ['angle', 'direction'],
                    },
                },
            }, {
                'type': 'function',
                'function': {
                    'name': 'analyse_cam',
                    'description': 'Return all objects detected by the camera with their distances and angles using YOLO.',
                    "parameters": {"type": "object", "properties": {}, "required": []}
                }
            }
        ]

    async def call_function_async(self, call) -> ActionData:
        func_name = call['function']['name']
        args : dict = call['function']['arguments']

        if func_name == 'move_robot':
            distance = float(args.get('distance', 0.0))
            direction = args.get('direction', 'forward')
            return await self.execute_linear_odom(distance, direction)

        elif func_name == 'turn_robot':
            angle = float(args.get('angle', 0.0))
            direction = args.get('direction', 'left')
            return await self.execute_angular_odom(angle, direction)

        elif func_name == 'analyse_cam':
            return await self.yolo_analysis_remote()

        else:
            return ActionData('error', 0, "Unknown function")

    async def execute_linear_odom(self, target_distance, direction) -> ActionData:
        """Se connecte au Rosbridge, écoute /odom, publie /cmd_vel et bloque jusqu'à atteindre la distance"""
        async with websockets.connect(self.uri) as ws:
            # 1. On s'abonne à /odom pour traquer la position du robot
            subscribe_msg = {
                "op": "subscribe",
                "topic": "/odom",
                "type": "nav_msgs/msg/Odometry"
            }
            await ws.send(json.dumps(subscribe_msg))

            # Attendre de recevoir le premier message odométrique pour initialiser les coordonnées de départ
            start_x, start_y = None, None
            distance_travelled = 0.0

            # Détermination du signe de la vitesse linéaire
            speed = self.lin_speed if direction == 'forward' else -self.lin_speed

            # Message de commande de vitesse pré-généré
            cmd_msg = {
                "op": "publish",
                "topic": "/cmd_vel",
                "msg": {
                    "header": {"frame_id": "base_link"},
                    "twist": {
                        "linear": {"x": speed, "y": 0.0, "z": 0.0},
                        "angular": {"x": 0.0, "y": 0.0, "z": 0.0}
                    }
                }
            }

            try:
                while distance_travelled < abs(target_distance):
                    # Lire le flux WebSocket provenant de Rosbridge
                    reply = await ws.recv()
                    data = json.loads(reply)

                    if data.get('topic') == '/odom':
                        pose = data['msg']['pose']['pose']
                        x = pose['position']['x']
                        y = pose['position']['y']
                        
                        if start_x is None:
                            start_x = x
                            start_y = y

                        # Calcul de la distance Euclidienne parcourue depuis le point de départ
                        distance_travelled = math.sqrt((x - start_x)**2 + (y - start_y)**2)
                        
                        # Envoyer continuellement l'ordre de mouvement tant qu'on n'a pas atteint la consigne
                        if distance_travelled < abs(target_distance):
                            await ws.send(json.dumps(cmd_msg))
                            
            finally:
                # Désabonnement du topic /odom pour libérer la bande passante
                unsubscribe_msg = {"op": "unsubscribe", "topic": "/odom"}
                await ws.send(json.dumps(unsubscribe_msg))

            # On renvoie un type physique mais avec une durée de 0 car le blocage a DEJA eu lieu ici
            return ActionData('physical', 0.0, cmd_msg)

    async def execute_angular_odom(self, target_angle, direction) -> ActionData:
                """Se connecte au Rosbridge, écoute /odom, pivote et calcule le delta d'angle (Yaw) exact via Quaternions"""
        async with websockets.connect(self.uri) as ws:
            subscribe_msg = {
                "op": "subscribe",
                "topic": "/odom",
                "type": "nav_msgs/msg/Odometry"
            }
            await ws.send(json.dumps(subscribe_msg))

            start_yaw = None
            angle_travelled = 0.0
            speed = self.ang_speed if direction == 'left' else -self.ang_speed

            cmd_msg = {
                "op": "publish",
                "topic": "/cmd_vel",
                "msg": {
                    "header": {"frame_id": "base_link"},
                    "twist": {
                        "linear": {"x": 0.0, "y": 0.0, "z": 0.0},
                        "angular": {"x": 0.0, "y": 0.0, "z": speed}
                    }
                }
            }

            try:
                while angle_travelled < abs(target_angle):
                    reply = await ws.recv()
                    data = json.loads(reply)

                    if data.get('topic') == '/odom':
                        q = data['msg']['pose']['pose']['orientation']
                        # Conversion Quaternion vers angle d'Euler (Yaw / lacet)
                        siny_cosp = 2.0 * (q['w'] * q['z'] + q['x'] * q['y'])
                        cosy_cosp = 1.0 - 2.0 * (q['y'] * q['y'] + q['z'] * q['z'])
                        yaw = math.atan2(siny_cosp, cosy_cosp)

                        if start_yaw is None:
                            start_yaw = yaw
                            continue

                        # Gestion de la discontinuité de l'angle à -PI / +PI
                        delta_yaw = yaw - start_yaw
                        if delta_yaw > pi: delta_yaw -= 2.0 * pi
                        if delta_yaw < -pi: delta_yaw += 2.0 * pi

                        angle_travelled = abs(delta_yaw)

                        if angle_travelled < abs(target_angle):
                            await ws.send(json.dumps(cmd_msg))
            finally:
                unsubscribe_msg = {"op": "unsubscribe", "topic": "/odom"}
                await ws.send(json.dumps(unsubscribe_msg))

            return ActionData('physical', 0.0, cmd_msg)

    async def yolo_analysis_remote(self) -> ActionData:
        """Appelle le service ROS 2 /yolo_trigger exposé par ton pc portable"""
        async with websockets.connect(self.uri) as ws:
            call_id = "yolo_request_clery"
            service_request = {
                "op": "call_service",
                "id": call_id,
                "service": "/yolo_trigger",
                "args": {}
            }
            try:
                await ws.send(json.dumps(service_request))

                # Attente de la réponse du service
                while True:
                    reply = await ws.recv()
                    data = json.loads(reply)

                    # On filtre par l'ID d'appel unique ou par le nom de service opéré par Rosbridge
                    if data.get('op') == 'service_response' and (data.get('id') == call_id or data.get('service') == '/yolo_trigger'):

                        # Ton noeud YOLO stocke le résultat dans le champ 'message' du type Trigger
                        raw_json_string = data['values'].get('message', '')

                        # Si aucun objet ou si le noeud a répondu explicitement "YOLO found: Nothing"
                        if not raw_json_string.strip() or "YOLO found: Nothing" in raw_json_string:
                            return ActionData('yolo_img', 0, [])

                        # Décodage de la liste de dictionnaires renvoyée par le yolo_node
                        detections = json.loads(raw_json_string)
                        print(f"[Toolbox] YOLO distant a trouvé : {detections}")
                        return ActionData('yolo_img', 0, detections)

            except Exception as e:
                print(f"[Toolbox] Erreur appel YOLO distant : {e}")
                return ActionData('yolo_img', 0, [])
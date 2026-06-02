import rclpy
from geometry_msgs.msg import TwistStamped
from std_srvs.srv import Trigger
from rclpy.executors import SingleThreadedExecutor

import json
from dataclasses import dataclass
from numpy import pi

@dataclass
class ActionData():
    actionType : str
    duration: float
    data : dict|str|list

class FunctionsTools() :
    def __init__(self, node_parent, publisher, yolo_service_topic,
                 logger,
                 linear_speed : float = 1.0, angular_speed : float = pi/2):
        
        self.node = node_parent # Référence vers le nœud principal pour utiliser son horloge
        self.pub = publisher
        self.log = logger
        self.yolo_service_topic = yolo_service_topic

        self.lin_speed = linear_speed # m/s
        self.ang_speed = angular_speed # rad/s
        
        # ACTIVER / DÉSACTIVER LE MODE MOCK ICI
        self.mock_mode = False

    @staticmethod
    def get_tools_def() :
        return [
            {
                'type': 'function',
                'function': {
                    'name': 'move_robot',
                    'description': 'Move the robot straight on a given distance in meters',
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
                    'description': 'Rotate Robot to the left or right for a given angle in radian',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'angle': {'type': 'number', 'description': 'Radian of rotation to do'},
                            'direction': {'type': 'string', 'enum': ['left', 'right']},
                        },
                        'required': ['angle', 'direction'],
                    },
                },
            }, {
                'type' : 'function',
                'function' : {
                    'name' : 'analyse_cam',
                    'description': 'Return all object detected by the camera thanks to YOLO Detect model',
                    "parameters": {"type": "object", "properties": {}, "required": []}
                }
            }
        ]

    def call_function(self, call_action) -> ActionData:
        func_name = call_action['function']['name']
        args : dict = call_action['function']['arguments']

        if self.mock_mode:
            print(f"📦 [MOCK TOOLBOX] Appel de l'outil : {func_name} avec les arguments {args}")

        match func_name:
            case 'move_robot':
                distance = float(args.get("distance", 0.0))
                direction = args.get("direction", "forward")
                duration = distance / self.lin_speed

                if not self.mock_mode:
                    self.execute_move(self.lin_speed, direction, duration)
                return ActionData('physical', duration, None)

            case 'turn_robot':
                angle = float(args.get("angle", 0.0))
                direction = args.get("direction", "left")
                duration = angle / self.ang_speed

                if not self.mock_mode:
                    self.execute_turn(self.ang_speed, direction, duration) 
                    
                return ActionData('physical', duration, None)
            
            case 'analyse_cam' :
                if self.mock_mode:
                    # Simulation de fausses données d'analyse d'image YOLO pour tes tests à vide
                    fake_yolo_data = [
                        {"object": "chair", "confidence": 0.88, "distance": 1.45, "angle": 0.25},
                        {"object": "bottle", "confidence": 0.92, "distance": 0.60, "angle": -0.15}
                    ]
                    return ActionData('yolo_img', 0.0, fake_yolo_data)
                else:
                    return ActionData('yolo_img', 0.0, self.yolo_analysis())
    
            case _:
                raise Exception("Nom de fonction incorrect")

    def execute_move(self, speed, direction, duration):
        try:
            msg = TwistStamped()
            msg.header.stamp = self.node.get_clock().now().to_msg()
            msg.twist.linear.x = float(speed) if direction == 'forward' else -float(speed)
            self.pub.publish(msg)
        except Exception as e:
            self.log.error(f"Erreur déplacement : {e}")

    def execute_turn(self, speed, direction: str, duration):
        try:
            msg = TwistStamped()
            msg.header.stamp = self.node.get_clock().now().to_msg()
            if str(direction).lower() == 'left':
                msg.twist.angular.z = float(speed)
            else:
                msg.twist.angular.z = -float(speed)
            self.pub.publish(msg)
        except Exception as e :
            self.log.error(f"Erreur rotation : {e}")

    def yolo_analysis(self) :
        temp_node = rclpy.create_node('temp_toolbox_yolo_client')
        yolo_client = temp_node.create_client(Trigger, self.yolo_service_topic)
        
        if not yolo_client.wait_for_service(timeout_sec=2.0):
            self.log.error("YOLO Service non disponible !")
            temp_node.destroy_node()
            return []
            
        req = Trigger.Request()
        future = yolo_client.call_async(req)

        executor = SingleThreadedExecutor()
        executor.add_node(temp_node)
        executor.spin_until_future_complete(future)

        response = future.result()
        temp_node.destroy_node()
        executor.shutdown()
        
        try:
            if response.success:
                data = json.loads(response.message)
                return data if data else []
            else:
                return []
        except json.JSONDecodeError:
            return []
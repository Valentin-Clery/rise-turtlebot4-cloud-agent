# ROS IMPORT
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
from std_msgs.msg import String
from std_srvs.srv import Trigger

# UTILITY IMPORT
import os
from openai import OpenAI
import json
import re
from numpy import pi, inf

# DEPENDENCIES IMPORT
from .fsm import fsm
from .toolbox import FunctionsTools, ActionData

class RobotAgent(Node):
    def __init__(self, Hz=20):
        super().__init__('robot_agent')

        # Publishers & Subscribers
        self.cmd_pub = self.create_publisher(TwistStamped, '/cmd_vel', 10)
        self.web_chat_pub = self.create_publisher(String, '/web_chat_response', 10)
        
        # Écoute les ordres tapés sur l'interface Web HTML
        self.web_order_sub = self.create_subscription(
            String,
            '/web_chat_order',
            self.web_order_callback,
            10
        )
        
        # Configuration Groq / OpenAI API
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        self.model_name = "llama-3.1-8b-instant"

        # ATTENTION : On passe self à la toolbox pour qu'elle puisse utiliser le get_clock() du nœud parent
        self.toolbox = FunctionsTools(self, self.cmd_pub, 'yolo_trigger', self.get_logger())
        self.tools = self.toolbox.get_tools_def()

        self.user_input: str = None
        self.cmd_queue = []
        self.linear_speed = 1.0  # m/s
        self.angular_speed = pi/2  # rad/s
        self.Hz = Hz 
        self.T = 1.0 / Hz 

        self.call_action = None
        self.actionData: ActionData = None
        self.cpt_llm_action: float = 0.0
        self.start_time_action = None
        
        self.new_order_available = False

        # Machine d'État (FSM)
        self.fs = fsm([
            ('Start', 'UserPrompting', True),
            ('UserPrompting', 'UserPrompting', self.KeepAsk, self.wait_for_prompt),
            ('UserPrompting', 'LLM_ReadQueue', self.check_Prompt_To_Action, self.ReadQueue),
            ('LLM_ReadQueue', 'LLM_ReadQueue', False), 
            ('LLM_ReadQueue', 'UserPrompting', self.fail_ReadQueue, self.wait_for_prompt),
            ('LLM_ReadQueue', 'LLM_Action', self.check_ReadQueue, self.DoAction),
            ('LLM_Action', 'LLM_Action', self.KeepAction, self.DoAction),
            ('LLM_Action', 'STOP', self.check_STOP, self.DoSTOP),
            ('STOP', 'STOP', self.KeepSTOP, self.DoSTOP),
            ('STOP', 'LLM_ReadQueue', self.check_NextAction, self.ReadQueue),
            ('STOP', 'UserPrompting', self.check_Return_To_Prompt, self.wait_for_prompt)
        ])

        self.fs.start("Start")
        self.timer = self.create_timer(self.T, self.callback)
        self.get_logger().info("--- Agent LLM RISE Connecté à l'IHM Web (Groq) ---")

    def callback(self):
        try:
            self.fs.event("")
        except Exception:
            pass

    def web_order_callback(self, msg):
        if msg.data.strip():
            self.get_logger().info(f"📥 Nouvel ordre reçu du Dashboard : {msg.data}")
            self.user_input = msg.data
            self.new_order_available = True
            self.send_prompt(user_prompt=self.user_input)

    def wait_for_prompt(self, fss, value):
        pass

    def send_prompt(self, user_prompt=None, additional_syst_prompt=None):
        AI_Prompt = [
            {'role': 'system', 'content': 'You are capable of piloting a Robot through multiple Tools. These tools only accept as input a duration and a speed. You are allowed to call multiple functions to answer the user prompt in one answer.'},
            {'role': 'system', 'content': 'Think step by step before calling the tool.'}
        ]

        if additional_syst_prompt is not None:
            AI_Prompt.append({'role': 'system', 'content': additional_syst_prompt})
        if user_prompt is not None: 
            AI_Prompt.append({'role': 'user', 'content': user_prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=AI_Prompt,
                temperature=0.0,
                tools=self.tools,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            content = message.content or ""

            log_msg = String()
            if content:
                log_msg.data = f"🤖 <b>Robot :</b> {content.replace('\n', '<br>')}"
                self.web_chat_pub.publish(log_msg)

            if message.tool_calls:
                self.cmd_queue = []
                for tool_call in message.tool_calls:
                    call_dict = {
                        'function': {
                            'name': tool_call.function.name,
                            'arguments': json.loads(tool_call.function.arguments)
                        }
                    }
                    self.cmd_queue.append(call_dict)
                
                log_msg.data = f"⚙️ <i>[Système] : Enchaînement de {len(message.tool_calls)} action(s) planifiée(s).</i>"
                self.web_chat_pub.publish(log_msg)
            else:
                self.cmd_queue = []
        
        except Exception as e:
            self.cmd_queue = []
            self.get_logger().error(f"Erreur API Groq : {str(e)}")
            err_msg = String(data=f"❌ <b>Erreur Système :</b> Échec de communication avec Groq ({str(e)})")
            self.web_chat_pub.publish(err_msg)

    def KeepAsk(self, fss):
        return not self.check_Prompt_To_Action(fss)

    def check_Prompt_To_Action(self, fss):
        if len(self.cmd_queue) != 0:
            self.new_order_available = False
            return True
        return False

    def ReadQueue(self, fss, value):
        if len(self.cmd_queue) > 0:
            self.call_action = self.cmd_queue.pop(0)
        else:
            self.call_action = None
    
    def check_ReadQueue(self, fss):
        return self.call_action is not None

    def fail_ReadQueue(self, fss):
        return self.call_action is None

    def DoAction(self, fss, value):
        # FIX : On n'initialise et on n'appelle la fonction QU'AU PREMIER TICK de l'action
        if self.start_time_action is None:
            self.start_time_action = self.get_clock().now()
            self.actionData = self.toolbox.call_function(self.call_action)

        # Les ticks suivants mettent simplement à jour le compteur de temps pour les actions physiques
        if self.actionData and self.actionData.actionType == 'physical':
            elapsed = self.get_clock().now() - self.start_time_action
            self.cpt_llm_action = elapsed.nanoseconds / 1e9

    def KeepAction(self, fss):
        return not self.check_STOP(fss)

    def check_STOP(self, fss):
        if self.actionData is None:
            return True

        match self.actionData.actionType:
            case 'physical':
                return self.cpt_llm_action > self.actionData.duration
            
            case 'sensor':
                return True
            
            case 'yolo_img':
                yolo_data = self.actionData.data
                log_msg = String()
                
                if not yolo_data:
                    vision_context = "From an earlier analysis, you have not detected any objects."
                    log_msg.data = "👁️ <b>Analyse Vision :</b> Aucun objet détecté."
                else:
                    detections = []
                    html_detections = []
                    for item in yolo_data:
                        angle = item.get("angle", 0.0)
                        degree_info = f"{abs(float(angle)):.2f} rad à gauche" if angle > 0 else f"{abs(float(angle)):.2f} rad à droite"
                        detections.append(f"{item['object']} ({item['confidence']:.0%}) detected at {item.get('distance', 999)} meters.")
                        html_detections.append(f"• <b>{item['object']}</b> ({item['confidence']:.0%}) à {item.get('distance', 999):.2f}m ({degree_info})")
                    
                    vision_context = f"You have detected the following: {', '.join(detections)}."
                    log_msg.data = f"👁️ <b>Analyse Vision :</b><br>{'<br>'.join(html_detections)}"
                
                self.web_chat_pub.publish(log_msg)

                analysis_prompt = f"""{vision_context}\nThe user's mission is: {self.user_input} 
                                      Have you found something you were looking for ? If so, do you have to do something after ?"""
                self.send_prompt(user_prompt=None, additional_syst_prompt=analysis_prompt) 
                return True
            
            case _:
                return True
        
    def DoSTOP(self, fss, value):
        self.cpt_llm_action = 0.0
        self.call_action = None
        self.start_time_action = None

        STOP_msg = TwistStamped()
        STOP_msg.header.stamp = self.get_clock().now().to_msg()
        self.cmd_pub.publish(STOP_msg) 

    def KeepSTOP(self, fss):
        return not self.check_NextAction(fss) and not self.check_Return_To_Prompt(fss)

    def check_NextAction(self, fss):
        return len(self.cmd_queue) != 0

    def check_Return_To_Prompt(self, fss):
        return len(self.cmd_queue) == 0


def main(args=None):
    rclpy.init(args=args)
    node = RobotAgent(Hz=20)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Arrêt de l'Agent LLM.")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

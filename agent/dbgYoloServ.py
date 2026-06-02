#!/usr/bin/env python3
import sys, json
import rclpy
import cv2
import numpy as np
from rclpy.node import Node
from std_srvs.srv import Trigger
from sensor_msgs.msg import Image

class YoloCaller(Node):
    def __init__(self):
        super().__init__('yolo_client_node')
        
        # 1. Setup the service client
        self.cli = self.create_client(Trigger, 'yolo_trigger')
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Service not available, waiting...')
        
        self.req = Trigger.Request()

        # 2. Setup the camera subscriber for visualization
        self.img_sub = self.create_subscription(
            Image, 
            '/oakd/rgb/preview/image_raw',
            self.image_callback,
            10
        )
        self.get_logger().info('Visualization window starting. Press Q in the video window to exit.')

    def image_callback(self, msg):
        """Grabs the frame using raw NumPy and displays it with OpenCV."""
        try:
            # Bypass cv_bridge to avoid NumPy 1.x/2.x conflicts
            img_array = np.frombuffer(msg.data, dtype=np.uint8)
            cv_image = img_array.reshape((msg.height, msg.width, 3))
            
            # Convert colors if the camera sends RGB instead of BGR
            if msg.encoding == 'rgb8':
                cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)
                
            # Display the live feed in an OpenCV window
            cv2.imshow("Robot Camera Feed - Debug Live", cv_image)
            
            # cv2.waitKey(1) updates the window frame. 
            # If you press 'q' inside the video window, it cleans up OpenCV.
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
                
        except Exception as e:
            self.get_logger().error(f"Failed to display image: {e}")

    def send_request(self):
        self.get_logger().info('Sending request to YOLO Service...')
        self.future = self.cli.call_async(self.req)
        
        # spin_until_future_complete keeps running both the service response
        # listener AND your image_callback simultaneously while waiting!
        rclpy.spin_until_future_complete(self, self.future)
        return self.future.result()

def main(args=None):
    rclpy.init(args=args)
    node = YoloCaller()
    
    # We loop here so you can press Enter multiple times to test the service
    try:
        while rclpy.ok():
            # A tiny wait key execution allows the window to refresh even while waiting for input
            cv2.waitKey(1) 
            
            user_input = input("\n[Press Enter to send YOLO Request | Type 'q' to quit]: ")
            if user_input.strip().lower() == 'q':
                break
                
            response = node.send_request()
            node.get_logger().info(f'Result Received: success={response.success}')
            
            try:
                # Parse the JSON string back into a Python list of dictionaries
                data = json.loads(response.message)
                
                if response.success:
                    if data:
                        node.get_logger().info("--- YOLO Structured Detections ---")
                        for item in data:
                            # You can now access keys independently with type safety
                            name = item["object"]
                            score = item["confidence"]
                            dist = item.get("distance",999)
                            rad = item["angle"]
                            node.get_logger().info(f" -> {name}: {score:.2%}, dist : {dist:.2}, angle : {rad:.2}")
                    else:
                        node.get_logger().info("YOLO found: Nothing")
                else:
                    # Handle the error dictionary sent from the server
                    node.get_logger().error(f"Server Error: {data.get('error')}")
                    
            except json.JSONDecodeError:
                # Fallback in case something went wrong with serialization
                node.get_logger().warn(f"Raw string message: {response.message}")
            
    except KeyboardInterrupt:
        pass
    finally:
        # Clean up windows and shutdown
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
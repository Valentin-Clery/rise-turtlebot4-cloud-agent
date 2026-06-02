#!/usr/bin/env python3
import rclpy
import json
import cv2
import numpy as np
from ultralytics import YOLO
from rclpy.node import Node
from std_srvs.srv import Trigger
from sensor_msgs.msg import Image

class YoloService(Node):
    def __init__(self):
        super().__init__('yolo_service_node')

        # Initialize cv_bridge to convert ROS images to OpenCV
        self.latest_cv_image = None # Variable to store the most recent frame
        self.latest_depth_img = None
        self.HFOV = 1.204 
 
        # Subscriber to the camera topic of the robot
        self.raw_img_sub = self.create_subscription(
            Image, 
            '/oakd/rgb/preview/image_raw',
            self.raw_img_callback,
            10
        )
        self.depth_img_sub = self.create_subscription(
            Image, 
            '/oakd/rgb/preview/depth',
            self.depth_img_callback,
            10
        )
        
        # Load yolo model
        self.model = YOLO("yolo26n.pt")

        self.srv = self.create_service(Trigger, 'yolo_trigger', self.trigger_callback)
        self.get_logger().info('YOLO Service is ready to be called.')

    def depth_img_callback(self, msg):
        """Constantly updates the latest_depth_img using pure NumPy."""
        try:
            # 32FC1 maps directly to a 32-bit float in NumPy
            if msg.encoding == '32FC1':
                # Parse the raw bytes as floats
                img_array = np.frombuffer(msg.data, dtype=np.float32)
                
                # Reshape to a 2D grid (Height: 240 x Width: 320)
                self.latest_depth_img = img_array.reshape((msg.height, msg.width))
            else:
                self.get_logger().warn(f"Expected 32FC1, got: {msg.encoding}")
                
        except Exception as e:
            self.get_logger().error(f"Failed to convert depth image: {e}")

    def raw_img_callback(self, msg):
        """Constantly updates the latest_cv_image using pure NumPy."""
        try:
            # Bypass cv_bridge: Convert raw message data directly to a NumPy array
            img_array = np.frombuffer(msg.data, dtype=np.uint8)
            cv_image = img_array.reshape((msg.height, msg.width, 3))
            
            # Convert colors if the camera sends RGB instead of OpenCV's expected BGR
            if msg.encoding == 'rgb8':
                cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)
                
            self.latest_cv_image = cv_image
        except Exception as e:
            self.get_logger().error(f"Failed to convert image: {e}")


    def trigger_callback(self, request, response):
        self.get_logger().info('Received request to trigger Yolo.')
        
        # Check if the camera has actually sent an image yet
        if self.latest_cv_image is None:
            response.success = False
            response.message = "Failed: No image received from the camera yet."
            return response
        
        img_h, img_w = self.latest_cv_image.shape[:2]
        try:
            # Run Yolo inference
            results = self.model(self.latest_cv_image)
            first_result = results[0] # Get the result object for the image

            # Extract bounding boxes of yolo analysis
            boxes = first_result.boxes
            
            # Create a list fro Yolo detection
            detections = []
            for box in boxes:
                cls_name = self.model.names[int(box.cls[0])]
                conf = float(box.conf[0])
                if conf < 0.6 :
                    continue
                
                # Récupération des coordonnées du rectangle YOLO
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                
                # Centre de l'objet dans l'image
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)
                
                # Calcule le décalage par rapport au centre de l'image
                x_ratio = (cx - (img_w / 2.0)) / (img_w / 2.0)
                
                # Si l'objet est à droite (x_ratio > 0), l'angle ROS doit être négatif
                angle_ros = - (x_ratio * (self.HFOV / 2.0))
                
                distance = None
                if self.latest_depth_img is not None:
                    patch = self.latest_depth_img[max(0, cy-2):min(img_h, cy+3), max(0, cx-2):min(img_w, cx+3)]
                    valid_pixels = patch[(patch > 0.0) & ~np.isnan(patch)]
                    
                    if len(valid_pixels) > 0:
                        distance = float(np.median(valid_pixels))

                detections.append({
                    "object": cls_name,
                    "confidence": round(conf, 4),
                    "distance": distance, # en mètres
                    "angle": angle_ros,    # en radians
                })

            self.get_logger().info('Yolo analysis done.')

            response.success = True
            if detections:
                response.message = json.dumps(detections)
            else:
                response.message = "YOLO found: Nothing"
                
        except Exception as e:
            response.success = False
            response.message = f"YOLO prediction failed: {e}"
        

        self.get_logger().info('Sending Response.')
        return response

def main(args=None):
    rclpy.init(args=args)
    node = YoloService()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
import cv2
import os
import numpy as np

class VisionEngine:
    def __init__(self):
        self.models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models", "vision")
        os.makedirs(self.models_dir, exist_ok=True)
        
        self.prototxt = os.path.join(self.models_dir, "MobileNetSSD_deploy.prototxt.txt")
        self.model_path = os.path.join(self.models_dir, "MobileNetSSD_deploy.caffemodel")
        
        # Pascal VOC classes
        self.CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
            "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
            "dog", "horse", "motorbike", "person", "pottedplant", "sheep",
            "sofa", "train", "tvmonitor", "cell phone"]

        self.net = None
        if os.path.exists(self.prototxt) and os.path.exists(self.model_path):
            try:
                self.net = cv2.dnn.readNetFromCaffe(self.prototxt, self.model_path)
            except Exception as e:
                print(f"[ERROR] Could not load vision model: {e}")

    def capture_and_analyze(self) -> str:
        if self.net is None:
            return "My vision module is inactive. Please download the MobileNet SSD model files to the models slash vision folder."

        try:
            # Open webcam
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return "I am unable to access the camera hardware."
                
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                return "I couldn't capture an image from the camera."
                
            # Analyze frame
            (h, w) = frame.shape[:2]
            blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 0.007843, (300, 300), 127.5)
            self.net.setInput(blob)
            detections = self.net.forward()
            
            found_objects = set()
            for i in np.arange(0, detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                if confidence > 0.5:
                    idx = int(detections[0, 0, i, 1])
                    if idx < len(self.CLASSES):
                        found_objects.add(self.CLASSES[idx])
                        
            if "person" in found_objects:
                found_objects.remove("person") # ignore the user
                
            if not found_objects:
                return "I don't see any distinct objects."
                
            objects_str = ", ".join(list(found_objects))
            return f"It looks like you are holding or showing me a {objects_str}."
        except Exception as e:
            return f"An error occurred while trying to see: {e}"

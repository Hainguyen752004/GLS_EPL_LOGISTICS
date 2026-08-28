import cv2
import numpy as np
import os
import json
from ultralytics import YOLO
from paddleocr import PaddleOCR

class AICheckpointEngine:
    def __init__(self, config_path: str = None):
        if config_path is None:
            # Default to backend/ai_config.json
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ai_config.json")
            
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
            
        # Resolve models directory relative to the config file location
        backend_dir = os.path.dirname(config_path)
        self.models_dir = os.path.abspath(os.path.join(backend_dir, self.config.get("models_dir_relative_to_backend", "../models")))
        
        # 1. Khởi tạo YOLO cho Truck Detection
        vehicle_model_name = self.config.get("vehicle_model", "yolov8n.pt")
        self.vehicle_model = YOLO(vehicle_model_name) 
        
        # 2. Khởi tạo YOLO cho Plate Detection
        plate_model_name = self.config.get("plate_model", "custom11_plate.pt")
        plate_model_path = os.path.join(self.models_dir, plate_model_name)
        if os.path.exists(plate_model_path):
            self.plate_model = YOLO(plate_model_path)
        else:
            print(f"WARNING: Không tìm thấy model biển số tại {plate_model_path}")
            self.plate_model = None
            
        # 3. Khởi tạo PaddleOCR
        ocr_lang = self.config.get("ocr_lang", "en")
        use_angle_cls = self.config.get("use_angle_cls", True)
        self.ocr = PaddleOCR(use_angle_cls=use_angle_cls, lang=ocr_lang, show_log=False)

    def process_frame(self, frame: np.ndarray):
        """
        Nhận vào 1 frame, chạy qua quy trình Cascaded:
        1. Tìm Xe Tải (Truck)
        2. Nếu thấy -> Cắt (Crop) xe tải
        3. Truyền vào Plate Model tìm biển số
        4. Cắt (Crop) biển số -> Đưa vào PPOCR
        """
        results = {
            "vehicle_detected": False,
            "vehicle_bbox": None,
            "plate_detected": False,
            "plate_bbox": None,
            "plate_text": "",
            "plate_confidence": 0.0,
            "cropped_plate_img": None
        }

        # BƯỚC 1: NHẬN DIỆN XE TẢI
        v_classes = self.config.get("vehicle_classes", [7])
        v_conf = self.config.get("vehicle_conf_threshold", 0.5)
        v_results = self.vehicle_model.predict(frame, classes=v_classes, conf=v_conf, verbose=False)
        
        if not v_results or len(v_results[0].boxes) == 0:
            return results # Không thấy xe tải

        # Giả sử chỉ lấy chiếc xe tải to nhất/gần nhất (confidence cao nhất hoặc diện tích lớn nhất)
        truck_box = v_results[0].boxes[0]
        x1, y1, x2, y2 = map(int, truck_box.xyxy[0])
        
        results["vehicle_detected"] = True
        results["vehicle_bbox"] = (x1, y1, x2, y2)

        # BƯỚC 2: CẮT (CROP) XE TẢI
        cropped_truck = frame[y1:y2, x1:x2]
        
        if self.plate_model is None or cropped_truck.size == 0:
            return results

        # BƯỚC 3: NHẬN DIỆN BIỂN SỐ TRÊN ẢNH XE TẢI
        p_conf = self.config.get("plate_conf_threshold", 0.4)
        p_results = self.plate_model.predict(cropped_truck, conf=p_conf, verbose=False)
        
        if not p_results or len(p_results[0].boxes) == 0:
            return results # Không thấy biển số

        # Lấy biển số có độ tự tin cao nhất
        plate_box = p_results[0].boxes[0]
        px1, py1, px2, py2 = map(int, plate_box.xyxy[0])
        
        # BƯỚC 4: CẮT (CROP) BIỂN SỐ (Tính tọa độ tuyệt đối trên ảnh gốc nếu cần vẽ box)
        results["plate_detected"] = True
        results["plate_bbox"] = (x1 + px1, y1 + py1, x1 + px2, y1 + py2) # Tọa độ tuyệt đối
        
        cropped_plate = cropped_truck[py1:py2, px1:px2]
        results["cropped_plate_img"] = cropped_plate
        
        if cropped_plate.size == 0:
            return results

        # BƯỚC 5: ĐỌC CHỮ BẰNG PPOCR
        # PPOCR nhận dạng tốt nhất trên ảnh đã crop sát biển số
        ocr_result = self.ocr.ocr(cropped_plate, cls=True)
        
        if ocr_result and len(ocr_result) > 0 and ocr_result[0] is not None:
            # Lấy text dài nhất / kết hợp các dòng text lại
            texts = [line[1][0] for line in ocr_result[0]]
            confidences = [line[1][1] for line in ocr_result[0]]
            
            results["plate_text"] = "".join(texts).replace(" ", "").replace("-", "")
            results["plate_confidence"] = sum(confidences) / len(confidences) if confidences else 0.0

        return results

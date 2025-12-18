import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis
import os
import time
from datetime import datetime
from flask import Flask, Response, render_template_string, request, jsonify, session, redirect, url_for, send_file
import threading
import json
from PIL import Image, ImageDraw, ImageFont 
from collections import Counter
from functools import wraps
import csv
import io

# Import kết nối CSDL
from database import get_connection

from flask_cors import CORS

# --- 1. CẤU HÌNH HỆ THỐNG & ĐƯỜNG DẪN ---
# Lấy đường dẫn tuyệt đối của file hiện tại
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Cấu hình thư mục lưu Vector khuôn mặt
VECTOR_DIR = "face_vectors"
ABS_VECTOR_DIR = os.path.join(BASE_DIR, VECTOR_DIR)
if not os.path.exists(ABS_VECTOR_DIR):
    os.makedirs(ABS_VECTOR_DIR)

# Cấu hình thư mục lưu ảnh người lạ (QUAN TRỌNG: Phải nằm trong static để React xem được)
STRANGER_DIR = "static/strangers"
ABS_STRANGER_DIR = os.path.join(BASE_DIR, STRANGER_DIR)
if not os.path.exists(ABS_STRANGER_DIR):
    os.makedirs(ABS_STRANGER_DIR)

# Khởi tạo Flask với thư mục static để phục vụ ảnh
app = Flask(__name__, static_folder='static') 
app.secret_key = 'sieubaomat_anh_trung_dep_trai' 
np.int = int 

CORS(
    app,
    resources={r"/*": {
        "origins": "http://localhost:3000",
        "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
    }},
    supports_credentials=True
)

SYSTEM_SETTINGS = { "threshold": 0.50, "scan_duration": 3.0 } 

USERS = {
    "admin": {
        "name": "Ratlabuon",
        "password": "Khothietchu",
        "role": "admin",
        "dept": "all"
    },
}

DB_PATH = "face_db"
LOG_FILE = "access_logs.json" 
META_FILE = os.path.join(DB_PATH, "metadata.json")

if not os.path.exists(DB_PATH): os.makedirs(DB_PATH)

global_frame_0 = None
global_frame_1 = None
lock = threading.Lock()
activity_logs = []
MAX_LOGS = 50 

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            if request.is_json or request.headers.get('Accept') == 'application/json':
                return jsonify(success=False, message="Chưa đăng nhập"), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def load_history_from_file():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: return []
    return []

def save_log_to_file(entry):
    logs = load_history_from_file()
    logs.insert(0, entry) 
    if len(logs) > 2000: logs = logs[:2000]
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

# --- 2. XỬ LÝ AI & DATABASE ---
class FaceDatabase:
    def __init__(self):
        self.known_embeddings = [] 
        self.reload_db()

    def reload_db(self):
        print("System: Đang tải dữ liệu khuôn mặt từ FILE TXT...")
        self.known_embeddings = []
        
        try:
            conn = get_connection()
            if conn is None:
                print("❌ Lỗi: Không thể kết nối Database!")
                return

            cursor = conn.cursor(dictionary=True)
            
            # Lấy đường dẫn file từ DB
            sql = """
            SELECT nv.ho_ten, nv.ten_phong, fe.vector_data 
            FROM face_embeddings fe
            JOIN nhan_vien nv ON fe.ma_nv = nv.ma_nv
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            count = 0
            for row in rows:
                name = row['ho_ten']
                dept = row['ten_phong'] or "Chưa phân loại"
                db_path = row['vector_data'] 
                
                if not db_path: continue

                # Xử lý đường dẫn tương thích mọi hệ điều hành
                filename = os.path.basename(db_path)
                file_path = os.path.join(ABS_VECTOR_DIR, filename)
                
                # Đọc file TXT
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r') as f:
                            vector_str = f.read()
                            embedding_list = json.loads(vector_str)
                            embedding = np.array(embedding_list, dtype=np.float32)
                            
                            # Chuẩn hóa
                            norm = np.linalg.norm(embedding)
                            if norm != 0: embedding = embedding / norm
                            
                            self.known_embeddings.append({
                                "name": name,
                                "embedding": embedding,
                                "dept": dept
                            })
                            count += 1
                    except Exception as err:
                        print(f"⚠️ Lỗi đọc file {file_path}: {err}")
                else:
                    # File trong DB có nhưng trên ổ cứng không thấy
                    # print(f"⚠️ Cảnh báo: File {file_path} không tồn tại")
                    pass
            
            print(f"✅ Đã tải thành công {count} khuôn mặt vào RAM!")
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"❌ Lỗi khi tải DB: {e}")

    def recognize(self, target_embedding):
        threshold = SYSTEM_SETTINGS["threshold"]
        norm = np.linalg.norm(target_embedding)
        if norm != 0: target_embedding = target_embedding / norm
        
        max_score = 0
        identity = "Unknown"
        
        for face_data in self.known_embeddings:
            db_emb = face_data["embedding"]
            db_name = face_data["name"]
            score = np.dot(target_embedding, db_emb)
            
            if score > max_score:
                max_score = score
                identity = db_name
        
        if max_score > 1.0: max_score = 1.0
        if max_score >= threshold:
            return identity, max_score
            
        return "Unknown", max_score
    
    def get_dept(self, name):
        for face in self.known_embeddings:
            if face["name"] == name:
                return face["dept"]
        return "Khách vãng lai"

print("System: Đang khởi động AI Model...")
face_app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
face_app.prepare(ctx_id=0, det_size=(640, 640))
db = FaceDatabase()
print("System: Sẵn sàng!")

# --- CÁC HÀM TIỆN ÍCH ---
def put_text_utf8(image, text, position, color=(0, 255, 0), font_scale=1):
    img_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    font_size = int(font_scale * 20)
    try: font = ImageFont.truetype("arial.ttf", font_size)
    except: font = ImageFont.load_default()
    draw.text(position, text, font=font, fill=color[::-1])
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

def create_placeholder_frame(text="MẤT TÍN HIỆU", width=640, height=360):
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    noise = np.random.randint(0, 50, (height, width, 3), dtype=np.uint8)
    frame = cv2.add(frame, noise)
    frame = put_text_utf8(frame, text, (width//2 - 100, height//2 - 15), (0, 0, 255), 1.5)
    return frame

def calculate_iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    unionArea = boxAArea + boxBArea - interArea
    return interArea / float(unionArea) if unionArea > 0 else 0

# --- THREAD CAMERA ---
def camera_thread():
    global global_frame_0, global_frame_1
    cap0 = cv2.VideoCapture(0) # Mặc định là 0, nếu không lên hình thì đổi thành 1
    cap1 = cv2.VideoCapture(1)
    
    if not cap0.isOpened():
        print("❌ LỖI: Không thể mở Camera 0!")
        
    while True:
        ret0, frame0 = cap0.read()
        ret1, frame1 = cap1.read()
        with lock:
            global_frame_0 = cv2.flip(frame0, 1) if ret0 else None
            global_frame_1 = frame1 if ret1 else None
        time.sleep(0.03)

t = threading.Thread(target=camera_thread)
t.daemon = True
t.start()

trackers_state = {0: [], 1: []}

# --- HÀM GHI LOG & LƯU ẢNH (ĐÃ CẬP NHẬT) ---
def add_log(name, cam_id, score, face_img=None):
    global activity_logs
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    time_str = now.strftime("%H:%M:%S")
    
    dept = "Khách"
    image_path = "" # Đường dẫn ảnh gửi frontend

    # Nếu là người lạ và có ảnh -> Lưu ảnh xuống đĩa
    if name == "Unknown" and face_img is not None:
        try:
            # Tạo tên file duy nhất dựa trên timestamp
            filename = f"stranger_{int(time.time())}_{cam_id}.jpg"
            save_path = os.path.join(ABS_STRANGER_DIR, filename)
            cv2.imwrite(save_path, face_img)
            
            # Đường dẫn tương đối cho React (phục vụ qua static)
            image_path = f"/static/strangers/{filename}"
            dept = "Cảnh báo"
        except Exception as e:
            print(f"Lỗi lưu ảnh người lạ: {e}")
    else:
        dept = db.get_dept(name)

    log_entry = {
        "full_time": now_str,
        "time": time_str,
        "name": name,
        "dept": dept, 
        "camera": f"CAM {cam_id+1}",
        "score": f"{score:.0%}",
        "status": "authorized" if name != "Unknown" else "warning",
        "image": image_path 
    }
    
    activity_logs.insert(0, log_entry)
    if len(activity_logs) > MAX_LOGS: activity_logs.pop()
    save_log_to_file(log_entry)

# --- HÀM XỬ LÝ AI CHÍNH (ĐÃ CẬP NHẬT CROP ẢNH) ---
def process_ai_frame(frame, cam_id):
    if frame is None: return create_placeholder_frame()
    display_frame = frame.copy()
    h_frame, w_frame, _ = frame.shape
    
    display_frame = put_text_utf8(display_frame, f"CAM 0{cam_id+1} TRỰC TIẾP", (20, 30), (0, 255, 0), 1)
    display_frame = put_text_utf8(display_frame, datetime.now().strftime("%d/%m %H:%M:%S"), (w_frame-250, 30), (200, 200, 200), 0.8)

    try:
        current_time = time.time()
        faces = face_app.get(frame)
        current_trackers = trackers_state[cam_id]
        new_trackers = []
        used_tracker_indices = set()
        
        for face in faces:
            bbox = face.bbox.astype(int)
            name, score = db.recognize(face.embedding)
            
            best_iou = 0
            best_tracker_idx = -1
            
            for i, tracker in enumerate(current_trackers):
                if i in used_tracker_indices: continue
                iou = calculate_iou(bbox, tracker['bbox'])
                if iou > 0.3 and iou > best_iou:
                    best_iou = iou
                    best_tracker_idx = i
            
            if best_tracker_idx >= 0:
                tracker = current_trackers[best_tracker_idx]
                tracker['bbox'] = bbox
                tracker['last_seen'] = current_time
                tracker['names'].append(name)
                tracker['scores'].append(score)
                used_tracker_indices.add(best_tracker_idx)
                
                elapsed = current_time - tracker['start_time']
                scan_dur = SYSTEM_SETTINGS["scan_duration"]
                
                if elapsed < scan_dur:
                    color = (0, 255, 255) 
                    label = f"ĐANG QUÉT... {int(scan_dur - elapsed)}s"
                else:
                    most_common_name = Counter(tracker['names']).most_common(1)[0][0]
                    avg_score = sum(tracker['scores']) / len(tracker['scores'])
                    
                    if most_common_name == "Unknown":
                        color = (0, 0, 255)
                        label = "CẢNH BÁO: NGƯỜI LẠ"
                    else:
                        color = (0, 255, 0)
                        dept = db.get_dept(most_common_name)
                        label = f"{most_common_name} | {dept}"
                    
                    # --- LOGIC GHI LOG VÀ CẮT ẢNH ---
                    if not tracker['logged']:
                        face_img = None
                        # Chỉ cắt ảnh khi là Unknown để tiết kiệm tài nguyên
                        if most_common_name == "Unknown":
                            x1, y1, x2, y2 = bbox
                            # Mở rộng vùng cắt một chút cho đẹp
                            y1 = max(0, y1 - 20); y2 = min(h_frame, y2 + 20)
                            x1 = max(0, x1 - 20); x2 = min(w_frame, x2 + 20)
                            
                            # Đảm bảo tọa độ không âm
                            y1 = max(0, y1); x1 = max(0, x1)
                            
                            face_img = frame[y1:y2, x1:x2]
                        
                        add_log(most_common_name, cam_id, avg_score, face_img)
                        tracker['logged'] = True

                new_trackers.append(tracker)
                x1, y1, x2, y2 = bbox
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
                cv2.rectangle(display_frame, (x1, y1 - 30), (x1 + 250, y1 - 5), color, -1)
                display_frame = put_text_utf8(display_frame, label, (x1 + 5, y1 - 30), (0,0,0) if color==(0,255,255) else (255,255,255), 0.7)

            else:
                new_tracker = {
                    'bbox': bbox,
                    'start_time': current_time,
                    'last_seen': current_time,
                    'names': [name],
                    'scores': [score],
                    'logged': False
                }
                new_trackers.append(new_tracker)
        
        trackers_state[cam_id] = [t for t in new_trackers if (current_time - t['last_seen'] < 1.0)]
            
    except Exception as e:
        # print(f"Error AI: {e}") 
        pass
    return display_frame

# --- CÁC ROUTE API ---

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json(force=True)
    except:
        data = request.form.to_dict()
    username = data.get('username') or data.get('user') or ""
    password = data.get('password') or ""

    if "@" in username: username = username.split("@")[0]
    user = USERS.get(username)

    if user and user['password'] == password:
        session['user'] = username
        session['role'] = user['role']
        session['dept'] = user['dept']
        return jsonify({"success": True, "user": user}), 200

    return jsonify({"success": False, "message": "Sai tài khoản hoặc mật khẩu!"}), 401

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({"success": True}), 200

@app.route('/api/me', methods=['GET'])
def api_me():
    if 'user' in session:
        username = session['user']
        user = USERS.get(username, {})
        return jsonify({"authenticated": True, "user": user}), 200
    return jsonify({"authenticated": False}), 200

@app.route('/nguoi_dung', methods=['GET'])
def get_user_all():
    try:
        conn = get_connection()
        if conn is None: return jsonify({"status": "error", "message": "Lỗi DB"}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM nhan_vien ORDER BY ma_nv DESC")
        data = cursor.fetchall()
        cursor.close(); conn.close()
        return jsonify({"method": "GET", "status": "success", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/update_employee', methods=['POST'])
def update_employee():
    try:
        data = request.get_json()
        ma_nv = data.get('ma_nv')
        val = (data.get('ho_ten'), data.get('email'), data.get('sdt'), data.get('dia_chi'), 
               data.get('ten_phong'), data.get('ten_chuc_vu'), data.get('trang_thai'), ma_nv)
        conn = get_connection(); cursor = conn.cursor()
        sql = """UPDATE nhan_vien SET ho_ten=%s, email=%s, sdt=%s, dia_chi=%s, ten_phong=%s, ten_chuc_vu=%s, trang_thai=%s WHERE ma_nv=%s"""
        cursor.execute(sql, val)
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True, "message": "Cập nhật thành công!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/add_employee_with_faces', methods=['POST'])
def add_employee_with_faces():
    try:
        ho_ten = request.form.get('ho_ten')
        email = request.form.get('email')
        sdt = request.form.get('sdt')
        dia_chi = request.form.get('dia_chi')
        ten_phong = request.form.get('ten_phong')
        ten_chuc_vu = request.form.get('ten_chuc_vu')
        trang_thai = request.form.get('trang_thai', 'Dang_Lam')

        files = request.files.getlist("faces")

        if not ho_ten or not files:
            return jsonify({"success": False, "message": "Thiếu dữ liệu: Cần tên và ảnh"}), 400

        conn = get_connection()
        cursor = conn.cursor()

        sql_nv = "INSERT INTO nhan_vien (ho_ten, email, sdt, dia_chi, ten_phong, ten_chuc_vu, trang_thai) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(sql_nv, (ho_ten, email, sdt, dia_chi, ten_phong, ten_chuc_vu, trang_thai))
        ma_nv = cursor.lastrowid

        added_faces = 0
        for i, file in enumerate(files):
            img_bytes = np.frombuffer(file.read(), np.uint8)
            img = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)
            if img is None: continue
            faces = face_app.get(img)
            if not faces: continue
            face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))
            embedding_list = face.embedding.tolist()
            
            filename = f"face_{ma_nv}_{int(time.time())}_{i}.txt"
            file_path = os.path.join(ABS_VECTOR_DIR, filename)
            with open(file_path, "w") as f:
                f.write(json.dumps(embedding_list))
            
            relative_path = os.path.join(VECTOR_DIR, filename).replace("\\", "/")
            sql_face = "INSERT INTO face_embeddings (ma_nv, vector_data) VALUES (%s, %s)"
            cursor.execute(sql_face, (ma_nv, relative_path))
            added_faces += 1

        conn.commit(); cursor.close(); conn.close()
        db.reload_db()

        return jsonify({"success": True, "message": f"Đã thêm nhân viên và {added_faces} khuôn mặt!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/video_feed/<int:cam_id>')
def video_feed(cam_id):
    return Response(generate_frames(cam_id), mimetype='multipart/x-mixed-replace; boundary=frame')

def generate_frames(cam_id):
    while True:
        with lock:
            frame = global_frame_0 if cam_id == 0 else global_frame_1
        processed_frame = process_ai_frame(frame, cam_id)
        ret, buffer = cv2.imencode('.jpg', processed_frame)
        if ret: yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        time.sleep(0.04)

@app.route('/api/history')
@login_required
def get_history():
    return jsonify(load_history_from_file())

@app.route('/api/delete_employee', methods=['DELETE'])
def delete_employee():
    try:
        data = request.get_json()
        ma_nv = data.get('ma_nv')
        conn = get_connection(); cursor = conn.cursor()
        
        cursor.execute("SELECT vector_data FROM face_embeddings WHERE ma_nv = %s", (ma_nv,))
        rows = cursor.fetchall()
        for row in rows:
            db_path = row[0] 
            if db_path:
                filename = os.path.basename(db_path)
                file_path = os.path.join(ABS_VECTOR_DIR, filename)
                if os.path.exists(file_path): os.remove(file_path)

        cursor.execute("DELETE FROM nhan_vien WHERE ma_nv = %s", (ma_nv,))
        conn.commit(); cursor.close(); conn.close()
        db.reload_db()
        return jsonify({"success": True, "message": "Đã xóa vĩnh viễn!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# --- API DASHBOARD THỐNG KÊ (ĐÃ CẬP NHẬT TRẢ ẢNH + CỘNG DỒN CẢNH BÁO) ---
@app.route('/api/dashboard-stats', methods=['GET'])
def get_dashboard_stats():
    # 1. Tính số người hiện diện (Unique log hôm nay) & Đếm CẢNH BÁO CỘNG DỒN
    today_str = datetime.now().strftime("%Y-%m-%d")
    unique_visitors = set()
    cumulative_warnings = 0 # Biến đếm cộng dồn
    
    current_logs = list(activity_logs)
    
    for log in current_logs:
        if log.get('full_time', '').startswith(today_str):
            name = log.get('name', 'Unknown')
            if name == 'Unknown':
                cumulative_warnings += 1 # Cứ có log Unknown là +1
            else:
                unique_visitors.add(name)

    # 2. Format logs trả về (bao gồm link ảnh)
    formatted_logs = []
    for log in current_logs[:10]: # Lấy 10 log mới nhất
        formatted_logs.append({
            "id": log.get('name', 'N/A'),
            "name": log.get('name', 'Unknown'),
            "loc": log.get('camera', 'Unknown Cam'),
            "time": log.get('time', ''),
            "status": "Cảnh báo" if log.get('name') == "Unknown" else "Hợp lệ",
            "image": log.get('image', '') # Trả về link ảnh
        })

    # 3. Lấy tổng nhân viên DB
    total_employees = 0
    try:
        conn = get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM nhan_vien")
            res = cursor.fetchone()
            if res: total_employees = res[0]
            cursor.close(); conn.close()
    except: total_employees = 150 

    # 4. Thông số phần cứng giả lập
    import random
    return jsonify({
        "present_count": len(unique_visitors),
        "total_employees": total_employees,
        "warning_count": cumulative_warnings, # Trả về số cộng dồn
        "logs": formatted_logs,
        "gpu_load": random.randint(10, 40),
        "temp": random.randint(45, 65)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
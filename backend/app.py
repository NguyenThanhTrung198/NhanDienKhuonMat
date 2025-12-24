import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis
import os
import time
from datetime import datetime
from flask import Flask, Response, request, jsonify, session, redirect, url_for, send_from_directory
import threading
import json
from PIL import Image, ImageDraw, ImageFont 
from collections import Counter
from functools import wraps
from flask_cors import CORS

# Import kết nối CSDL
from database import get_connection

# --- 1. CẤU HÌNH HỆ THỐNG & ĐƯỜNG DẪN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VECTOR_DIR = "face_vectors"
ABS_VECTOR_DIR = os.path.join(BASE_DIR, VECTOR_DIR)

# Đường dẫn tuyệt đối đến thư mục chứa ảnh
STATIC_DIR = os.path.join(BASE_DIR, "static")
STRANGER_DIR = os.path.join(STATIC_DIR, "strangers")

# Tạo thư mục nếu chưa có
if not os.path.exists(ABS_VECTOR_DIR): os.makedirs(ABS_VECTOR_DIR)
if not os.path.exists(STRANGER_DIR): os.makedirs(STRANGER_DIR)

# [FIX] Cấu hình Flask phục vụ static file chuẩn
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='/static') 
app.secret_key = 'sieubaomat_anh_trung_dep_trai' 
np.int = int 

CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}}, supports_credentials=True)

SYSTEM_SETTINGS = { "threshold": 0.50, "scan_duration": 1.5 } # thời gian chờ khi camera quét

# [MỚI] Cấu hình chống Spam Log
# Dict lưu thời gian nhận diện gần nhất: { "Tên người": thời_gian_timestamp }
LAST_LOG_TIME = {} 
# Thời gian chờ giữa 2 lần log (tính bằng giây). 
# Ví dụ: 60s = 1 phút. Nếu muốn 1 ngày chỉ 1 lần thì để số thật lớn (ví dụ 43200 = 12 tiếng)
LOG_COOLDOWN = 60
USERS = { "admin": { "name": "Ratlabuon", "password": "Khothietchu", "role": "admin", "dept": "all" } }

global_frame_0 = None; global_frame_1 = None; lock = threading.Lock()

# --- 2. XỬ LÝ DATABASE & AI ---
class FaceDatabase:
    def __init__(self):
        self.known_embeddings = []      # List nhân viên
        self.stranger_embeddings = []   # List người lạ (MỚI)
        self.next_stranger_id = 1       # ID tiếp theo
        self.reload_db()

    def reload_db(self):
        print("System: Đang tải dữ liệu khuôn mặt...")
        self.known_embeddings = []
        self.stranger_embeddings = [] # Reset list người lạ
        
        try:
            conn = get_connection()
            if not conn: return
            cursor = conn.cursor(dictionary=True)
            
            # 1. Tải Nhân viên (Code cũ)
            cursor.execute("SELECT nv.ho_ten, nv.ten_phong, nv.ten_chuc_vu, fe.vector_data FROM face_embeddings fe JOIN nhan_vien nv ON fe.ma_nv = nv.ma_nv")
            for row in cursor.fetchall():
                if not row['vector_data']: continue
                # ... (Đoạn xử lý file_path giữ nguyên như cũ của anh) ...
                # ... self.known_embeddings.append(...)
            
            # 2. [MỚI] Tải Người lạ từ DB lên RAM
            cursor.execute("SELECT stranger_label, vector_data FROM vector_nguoi_la")
            for row in cursor.fetchall():
                # Vector người lạ lưu dạng chuỗi JSON trong DB
                if row['vector_data']:
                    emb = np.array(json.loads(row['vector_data']), dtype=np.float32)
                    self.stranger_embeddings.append({
                        "name": row['stranger_label'],
                        "embedding": emb
                    })
                    # Cập nhật ID đếm để không bị trùng (lấy số đuôi của label)
                    try:
                        sid = int(row['stranger_label'].split('_')[-1])
                        if sid >= self.next_stranger_id: self.next_stranger_id = sid + 1
                    except: pass

            cursor.close(); conn.close()
            print(f"✅ Đã tải: {len(self.known_embeddings)} nhân viên, {len(self.stranger_embeddings)} người lạ đã biết.")

            
            
        except Exception as e: print(f"❌ Lỗi tải DB: {e}")
    # [ĐÃ CHỈNH SỬA] Hàm nhận diện chuẩn
    def recognize(self, target_embedding):
        # 1. Chuẩn hóa vector đầu vào
        norm = np.linalg.norm(target_embedding)
        if norm != 0:
            target_embedding = target_embedding / norm
        
        max_score = 0
        identity = "Unknown"
        
        # 2. So sánh vector
        for face in self.known_embeddings:
            score = np.dot(target_embedding, face["embedding"])
            if score > max_score:
                max_score = score
                identity = face["name"]
        
        # 3. Chuyển về float python chuẩn
        max_score = float(max_score)

        # 4. Kiểm tra ngưỡng
        if max_score >= SYSTEM_SETTINGS["threshold"]:
            return identity, max_score
            
        return "Unknown", max_score

    def get_person_info(self, name):
        for f in self.known_embeddings: 
            if f["name"] == name: return {"dept": f["dept"], "role": f["role"]}
        return {"dept": "Unknown", "role": "Khách"}

face_app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
face_app.prepare(ctx_id=0, det_size=(640, 640))
db = FaceDatabase()

# --- 3. TIỆN ÍCH HIỂN THỊ ---
def put_text_utf8(image, text, position, color=(0, 255, 0)):
    img_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    try: font = ImageFont.truetype("arial.ttf", 24) 
    except: font = ImageFont.load_default()
    x, y = position
    for off in [(-1,-1), (1,-1), (-1,1), (1,1)]: draw.text((x+off[0], y+off[1]), text, font=font, fill=(0,0,0))
    draw.text(position, text, font=font, fill=color[::-1])
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

def create_placeholder_frame(text="MẤT TÍN HIỆU"):
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    return put_text_utf8(frame, text, (200, 160), (0, 0, 255))

def calculate_iou(boxA, boxB):
    xA = max(boxA[0], boxB[0]); yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2]); yB = min(boxA[3], boxB[3])
    interArea = max(0, xB - xA) * max(0, yB - yA)
    union = (boxA[2]-boxA[0])*(boxA[3]-boxA[1]) + (boxB[2]-boxB[0])*(boxB[3]-boxB[1]) - interArea
    return interArea / float(union) if union > 0 else 0

# # --- 4. THREAD CAMERA ---
# def camera_thread():
#     global global_frame_0, global_frame_1
#     cap0 = cv2.VideoCapture(0); cap1 = cv2.VideoCapture(1)
#     while True:
#         ret0, frame0 = cap0.read(); ret1, frame1 = cap1.read()
#         with lock: global_frame_0 = cv2.flip(frame0, 1) if ret0 else None; global_frame_1 = frame1 if ret1 else None
#         time.sleep(0.03)
# t = threading.Thread(target=camera_thread); t.daemon = True; t.start()

# --- 4. THREAD CAMERA (ĐÃ NÂNG CẤP LÊN HD) ---
def camera_thread():
    global global_frame_0, global_frame_1
    
    # Mở camera
    cap0 = cv2.VideoCapture(0)
    cap1 = cv2.VideoCapture(1)

    # [QUAN TRỌNG] Ép độ phân giải lên HD (1280x720) để hết bị "ô vuông"
    # Cam 0
    cap0.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap0.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    # Cam 1 (Nếu có)
    cap1.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap1.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    while True:
        ret0, frame0 = cap0.read()
        ret1, frame1 = cap1.read()
        
        with lock: 
            # Lật ảnh (mirror) cho tự nhiên
            global_frame_0 = cv2.flip(frame0, 1) if ret0 else None
            global_frame_1 = frame1 if ret1 else None
            
        time.sleep(0.03)

t = threading.Thread(target=camera_thread); t.daemon = True; t.start()

# --- LOGIC QUẢN LÝ NGƯỜI LẠ ---
trackers_state = {0: [], 1: []}; RECENT_STRANGERS = []; NEXT_STRANGER_ID = 1; MAX_STRANGER_MEMORY = 50; STRANGER_MATCH_THRESHOLD = 0.60

def get_stranger_identity(embedding):
    global RECENT_STRANGERS, NEXT_STRANGER_ID
    max_score = 0; match_idx = -1
    for i, stranger in enumerate(RECENT_STRANGERS):
        score = np.dot(embedding, stranger['embedding'])
        if score > max_score: max_score = score; match_idx = i
    if max_score > STRANGER_MATCH_THRESHOLD:
        RECENT_STRANGERS[match_idx]['last_seen'] = time.time(); return RECENT_STRANGERS[match_idx]['id']
    new_id = NEXT_STRANGER_ID; NEXT_STRANGER_ID += 1
    if len(RECENT_STRANGERS) >= MAX_STRANGER_MEMORY: RECENT_STRANGERS.pop(0)
    RECENT_STRANGERS.append({'id': new_id, 'embedding': embedding, 'last_seen': time.time()})
    return new_id

# --- [MỚI] HÀM CHUYÊN LƯU ẢNH NGƯỜI LẠ ---
# --- [ĐÃ SỬA] HÀM CHUYÊN LƯU ẢNH NGƯỜI LẠ ---
def save_stranger_image(name, face_img):
    if face_img is None or face_img.size == 0: 
        return ""
    try:
        # Tạo tên file duy nhất
        filename = f"stranger_{name.replace(' ', '')}_{int(time.time())}.jpg"
        save_path = os.path.join(STRANGER_DIR, filename)
        
        # Lưu ảnh
        cv2.imwrite(save_path, face_img)
        print(f"📸 Đã chụp ảnh người lạ: {save_path}")
        
        # [QUAN TRỌNG] Trả về đường dẫn TUYỆT ĐỐI (có http://localhost:5000)
        # Để React ở cổng 3000 có thể load được ảnh từ cổng 5000
        return f"http://localhost:5000/static/strangers/{filename}"
        
    except Exception as e:
        print(f"⚠️ Lỗi lưu ảnh: {e}")
        return ""
# --- 5. GHI LOG VÀO DB (ĐÃ CÓ LOGIC CHỐNG SPAM) ---
# --- [ĐÃ SỬA] GHI LOG VÀO DB (LƯU ẢNH DẠNG BLOB) ---
# --- 5. GHI LOG VÀO DB ---
def add_log(name, cam_id, score, face_img=None):
    global LAST_LOG_TIME
    
    # ... (Phần kiểm tra thời gian giữ nguyên) ...
    current_time = time.time()
    if name in LAST_LOG_TIME:
        if current_time - LAST_LOG_TIME[name] < LOG_COOLDOWN:
            return True 

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    camera_name = f"CAM {cam_id+1}"
    
    try:
        conn = get_connection(); cursor = conn.cursor()
        
        # Kiểm tra nếu là người lạ
        if "Người lạ" in name or "Nguoi_La" in name or "Unknown" in name:
            img_blob = None
            if face_img is not None and face_img.size > 0:
                success, encoded_img = cv2.imencode('.jpg', face_img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
                if success: img_blob = encoded_img.tobytes()

            sql = "INSERT INTO nguoi_la (thoi_gian, camera, trang_thai, image_data, image_path) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(sql, (now_str, camera_name, name, img_blob, ""))
            
        else:
            # Lưu nhân viên
            info = db.get_person_info(name)
            dept = info.get('dept') or "Chưa cập nhật"
            cursor.execute("INSERT INTO nhat_ky_nhan_dien (thoi_gian, ten, phong_ban, camera, do_tin_cay, trang_thai, image_path) VALUES (%s, %s, %s, %s, %s, %s, %s)", 
                           (now_str, name, dept, camera_name, float(score), "authorized", ""))
            
        conn.commit(); cursor.close(); conn.close()
        print(f" >> ✅ Đã lưu log: {name}")
        LAST_LOG_TIME[name] = current_time
        return True

    except Exception as e: 
        print(f" >> ❌ Lỗi DB: {e}"); return False

# --- HẾT HÀM ADD_LOG (Dưới dòng này là hàm process_ai_frame luôn) ---
# --- 6. XỬ LÝ AI ---
def process_ai_frame(frame, cam_id):
    if frame is None: return create_placeholder_frame()
    display = frame.copy(); h, w, _ = frame.shape
    display = put_text_utf8(display, f"CAM {cam_id+1} LIVE", (20, 30))
    try:
        faces = face_app.get(frame); curr_trackers = trackers_state[cam_id]; new_trackers = []; used = set()
        for face in faces:
            bbox = face.bbox.astype(int); emb = face.embedding / np.linalg.norm(face.embedding); name, score = db.recognize(emb)
            
            best_iou = 0; best_idx = -1
            for i, trk in enumerate(curr_trackers):
                if i in used: continue
                iou = calculate_iou(bbox, trk['bbox'])
                if iou > 0.3 and iou > best_iou: best_iou = iou; best_idx = i
            
            if best_idx >= 0:
                tracker = curr_trackers[best_idx]; tracker.update({'bbox': bbox, 'last_seen': time.time(), 'current_embedding': emb}); tracker['names'].append(name); tracker['scores'].append(score); used.add(best_idx)
                
                if time.time() - tracker['start_time'] >= SYSTEM_SETTINGS["scan_duration"]:
                    common_name = Counter(tracker['names']).most_common(1)[0][0]
                    avg_score = sum(tracker['scores'])/len(tracker['scores'])
                    
                    if common_name == "Unknown":
                        if 'stranger_id' not in tracker: tracker['stranger_id'] = get_stranger_identity(tracker['current_embedding'])
                        stranger_id = tracker['stranger_id']
                        common_name = f"Người lạ {stranger_id}"; display_label = f"NGUOI LA {stranger_id}"; color = (0, 0, 255)
                    else:
                        info = db.get_person_info(common_name)
                        # [ĐÃ CHỈNH SỬA] Hiển thị phần trăm độ tin cậy
                        display_label = f"{common_name} ({int(avg_score*100)}%) - {info['role']}"
                        color = (0, 255, 0)
                    
                    if not tracker['logged']:
                        # [CẮT ẢNH AN TOÀN] Kiểm tra tọa độ cắt để tránh lỗi ảnh rỗng
                        x1, y1, x2, y2 = bbox
                        x1 = max(0, x1 - 20); y1 = max(0, y1 - 20)
                        x2 = min(w, x2 + 20); y2 = min(h, y2 + 20)
                        
                        img = None
                        if "Người lạ" in common_name:
                            if x2 > x1 and y2 > y1: # Đảm bảo vùng cắt hợp lệ
                                img = frame[y1:y2, x1:x2]
                        
                        if add_log(common_name, cam_id, avg_score, img): tracker['logged'] = True
                    
                    cv2.rectangle(display, (bbox[0],bbox[1]), (bbox[2],bbox[3]), color, 2)
                    (text_w, text_h), _ = cv2.getTextSize(display_label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
                    cv2.rectangle(display, (bbox[0], bbox[1]-35), (bbox[0]+text_w, bbox[1]), color, -1)
                    put_text_utf8(display, display_label, (bbox[0], bbox[1]-10), (255, 255, 255))
                else:
                    elapsed = time.time() - tracker['start_time']
                    cv2.rectangle(display, (bbox[0],bbox[1]), (bbox[2],bbox[3]), (0, 255, 255), 2)
                    put_text_utf8(display, f"Dang quet... {int(SYSTEM_SETTINGS['scan_duration'] - elapsed)}s", (bbox[0], bbox[1]-10), (0, 255, 255))
                new_trackers.append(tracker)
            else:
                new_trackers.append({'bbox': bbox, 'start_time': time.time(), 'last_seen': time.time(), 'names': [name], 'scores': [score], 'logged': False, 'current_embedding': emb})
        trackers_state[cam_id] = [t for t in new_trackers if time.time() - t['last_seen'] < 1.0]
    except: pass
    return display

# --- 7. API ROUTES ---

@app.route('/login', methods=['POST'])
def login():
    try: data = request.get_json(force=True)
    except: data = request.form.to_dict()
    user = USERS.get(data.get('username', '').split('@')[0])
    if user and user['password'] == data.get('password'):
        session['user'] = user['name']; return jsonify({"success": True, "user": user})
    return jsonify({"success": False}), 401

@app.route('/api/logout', methods=['POST'])
def api_logout(): session.clear(); return jsonify({"success": True})

@app.route('/api/me', methods=['GET'])
def api_me():
    return jsonify({"authenticated": True, "user": USERS.get(session.get('user'))} if 'user' in session else {"authenticated": False})

@app.route('/video_feed/<int:cam_id>')
def video_feed(cam_id):
    def generate(cid):
        while True:
            with lock: frame = global_frame_0 if cid == 0 else global_frame_1
            ret, buffer = cv2.imencode('.jpg', process_ai_frame(frame, cid))
            if ret: yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.04)
    return Response(generate(cam_id), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/nguoi_dung', methods=['GET'])
def get_user_all():
    try:
        conn = get_connection(); cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM nhan_vien ORDER BY ma_nv DESC")
        data = cursor.fetchall(); cursor.close(); conn.close()
        return jsonify({"status": "success", "data": data})
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/add_employee_with_faces', methods=['POST'])
def add_employee_with_faces():
    try:
        ho_ten = request.form.get('ho_ten'); files = request.files.getlist("faces")
        if not ho_ten or not files: return jsonify({"success": False}), 400
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("INSERT INTO nhan_vien (ho_ten, email, sdt, dia_chi, ten_phong, ten_chuc_vu, trang_thai) VALUES (%s, %s, %s, %s, %s, %s, %s)", 
                       (ho_ten, request.form.get('email'), request.form.get('sdt'), request.form.get('dia_chi'), request.form.get('ten_phong'), request.form.get('ten_chuc_vu'), 'Dang_Lam'))
        ma_nv = cursor.lastrowid
        added = 0
        for i, file in enumerate(files):
            img = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_COLOR)
            if img is None: continue
            faces = face_app.get(img)
            if not faces: continue
            fname = f"face_{ma_nv}_{int(time.time())}_{i}.txt"
            with open(os.path.join(ABS_VECTOR_DIR, fname), "w") as f: f.write(json.dumps(faces[0].embedding.tolist()))
            cursor.execute("INSERT INTO face_embeddings (ma_nv, vector_data) VALUES (%s, %s)", (ma_nv, os.path.join(VECTOR_DIR, fname).replace("\\", "/")))
            added += 1
        conn.commit(); cursor.close(); conn.close(); db.reload_db()
        return jsonify({"success": True, "message": f"Đã thêm {added} khuôn mặt"})
    except Exception as e: return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/delete_employee', methods=['DELETE'])
def delete_employee():
    try:
        ma_nv = request.get_json().get('ma_nv')
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("SELECT vector_data FROM face_embeddings WHERE ma_nv=%s", (ma_nv,))
        for row in cursor.fetchall():
            if row[0] and os.path.exists(os.path.join(BASE_DIR, row[0])): os.remove(os.path.join(BASE_DIR, row[0]))
        cursor.execute("DELETE FROM nhan_vien WHERE ma_nv=%s", (ma_nv,))
        conn.commit(); cursor.close(); conn.close(); db.reload_db()
        return jsonify({"success": True})
    except: return jsonify({"success": False}), 500

@app.route('/api/update_employee', methods=['POST'])
def update_employee():
    try:
        d = request.get_json()
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("UPDATE nhan_vien SET ho_ten=%s, email=%s, sdt=%s, dia_chi=%s, ten_phong=%s, ten_chuc_vu=%s, trang_thai=%s WHERE ma_nv=%s", 
                       (d.get('ho_ten'), d.get('email'), d.get('sdt'), d.get('dia_chi'), d.get('ten_phong'), d.get('ten_chuc_vu'), d.get('trang_thai'), d.get('ma_nv')))
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "message": str(e)}), 500
@app.route('/api/dashboard-stats', methods=['GET'])
def get_dashboard_stats():
    stats = {"present_count": 0, "total_employees": 0, "warning_count": 0, "logs": []}
    try:
        conn = get_connection()
        if conn:
            cur = conn.cursor(dictionary=True)
            
            # 1. Tổng nhân viên
            cur.execute("SELECT COUNT(*) as c FROM nhan_vien")
            stats['total_employees'] = cur.fetchone()['c']
            
            # 2. [SỬA Ở ĐÂY] Đếm số NGƯỜI LẠ duy nhất (DISTINCT)
            # Thay vì COUNT(*) ra 9, nó sẽ đếm tên duy nhất ra 2
            cur.execute("SELECT COUNT(DISTINCT trang_thai) as c FROM nguoi_la WHERE DATE(thoi_gian)=CURDATE()")
            stats['warning_count'] = cur.fetchone()['c']
            
            # 3. Đếm người quen hiện diện
            cur.execute("SELECT COUNT(DISTINCT ten) as c FROM nhat_ky_nhan_dien WHERE DATE(thoi_gian)=CURDATE()")
            stats['present_count'] = cur.fetchone()['c']
            
            # 4. Lấy log hiển thị (Cái này giữ nguyên để hiện danh sách chạy)
            cur.execute("SELECT * FROM nhat_ky_nhan_dien ORDER BY id DESC LIMIT 10")
            for row in cur.fetchall():
                stats['logs'].append({
                    "id": row['id'], 
                    "name": row['ten'], 
                    "dept": row['phong_ban'], 
                    "loc": row['camera'], 
                    "time": row['thoi_gian'].strftime("%H:%M:%S %d/%m"), 
                    "status": "Hợp lệ", 
                    "image": ""
                })
            
            cur.close(); conn.close()
            
    except Exception as e: 
        print(f"Dashboard Error: {e}")
        
    import random; stats.update({"gpu_load": random.randint(10, 40), "temp": random.randint(45, 65)})
    return jsonify(stats)
# ... (đoạn dưới giữ nguyên)


# --- [API] DANH SÁCH CẢNH BÁO ---
@app.route('/api/security/alerts', methods=['GET'])
def get_security_alerts():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        # [QUAN TRỌNG] Chỉ lấy các cột cần thiết, KHÔNG lấy image_data ở đây để tránh nặng API
        cursor.execute("SELECT id, thoi_gian, camera, trang_thai FROM nguoi_la ORDER BY thoi_gian DESC LIMIT 100")
        rows = cursor.fetchall()
        cursor.close(); conn.close()

        grouped = []
        for row in rows:
            dt = row['thoi_gian']
            
            # [QUAN TRỌNG] Tạo đường dẫn gọi vào API xem ảnh dựa vào ID
            # Frontend sẽ gọi: http://localhost:5000/api/image/view/123
            img_url = f"http://localhost:5000/api/image/view/{row['id']}"

            detail = { "time": dt.strftime("%H:%M:%S"), "img": img_url }
            name = row['trang_thai']; cam = row['camera']

            found = False
            for g in grouped:
                if g['location'] == name and g['cam'] == cam:
                    g['count'] += 1; g['details'].append(detail); g['img'] = img_url; found = True; break
            
            if not found:
                grouped.append({
                    "id": row['id'], "location": name, "cam": cam,
                    "date": dt.strftime("%d/%m/%Y"), "time": dt.strftime("%H:%M:%S"),
                    "img": img_url, 
                    "count": 1, "details": [detail]
                })

        return jsonify(grouped)
    except Exception as e: print("API Error:", e); return jsonify([])
# --- [API] LẤY DANH SÁCH ĐEN (GOM NHÓM THEO TÊN) ---
@app.route('/api/security/blacklist', methods=['GET'])
def get_blacklist():
    try:
        conn = get_connection()
        if not conn: return jsonify([])
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM blacklist ORDER BY id DESC")
        rows = cursor.fetchall()
        
        grouped_blacklist = []; processed_names = {} 
        for r in rows:
            name = r['name']
            img = r['image_path'] or "https://placehold.co/400"
            date_str = r['created_at'].strftime("%d/%m/%Y")
            time_str = r['created_at'].strftime("%H:%M:%S")
            detail_item = { "time": time_str, "img": img, "reason": r['reason'] }

            if name in processed_names:
                idx = processed_names[name]
                grouped_blacklist[idx]['count'] += 1
                grouped_blacklist[idx]['details'].append(detail_item)
            else:
                new_group = {
                    "id": r['id'], "name": name, "reason": r['reason'], "date": date_str, "img": img,
                    "status": "Dangerous", "count": 1, "location": "Trong danh sách đen", "cam": "Cơ sở dữ liệu",
                    "details": [detail_item]
                }
                grouped_blacklist.append(new_group)
                processed_names[name] = len(grouped_blacklist) - 1

        cursor.close(); conn.close()
        return jsonify(grouped_blacklist)
    except Exception as e: 
        print(f"Error getting blacklist: {e}")
        return jsonify([])

# --- [API] THÊM VÀO BLACKLIST ---
@app.route('/api/security/blacklist/add', methods=['POST'])
def add_to_blacklist():
    try:
        d = request.get_json()
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("INSERT INTO blacklist (name, reason, image_path, created_at) VALUES (%s, %s, %s, %s)", 
                       (d.get('name'), d.get('reason'), d.get('image'), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True, "message": "Đã thêm vào danh sách đen!"})
    except Exception as e: return jsonify({"success": False, "message": str(e)}), 500

#     # --- [QUAN TRỌNG] API ĐỂ HIỂN THỊ ẢNH RA MÀN HÌNH ---
# @app.route('/static/strangers/<path:filename>')
# def serve_stranger_image(filename):
#     # Hàm này giúp Flask tìm đúng file trong thư mục strangers để trả về cho React
#     return send_from_directory(STRANGER_DIR, filename)


# --- [API MỚI] XEM ẢNH TỪ DATABASE ---
@app.route('/api/image/view/<int:log_id>')
def view_image_from_db(log_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Chỉ lấy cột image_data của dòng có id tương ứng
        cursor.execute("SELECT image_data FROM nguoi_la WHERE id = %s", (log_id,))
        row = cursor.fetchone()
        cursor.close(); conn.close()

        if row and row[0]:
            # Trả về dữ liệu ảnh (image/jpeg) cho trình duyệt hiển thị
            return Response(row[0], mimetype='image/jpeg')
        else:
            # Trả về ảnh rỗng 1x1 pixel nếu không có ảnh
            return Response(b'', mimetype='image/jpeg')
    except Exception as e:
        print(e)
        return "Lỗi Server", 500
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
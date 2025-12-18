import cv2
import numpy as np
import mysql.connector
import json
from insightface.app import FaceAnalysis

# --- CẤU HÌNH DATABASE ---
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "", 
    "database": "ai_nckh"
}

# Khởi tạo AI
print("⏳ Đang tải AI... (Chờ 10s)")
app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))

def load_embeddings_from_db():
    print("📥 Đang tải dữ liệu từ MySQL...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        # Lấy dữ liệu từ bảng face_embeddings và nhan_vien
        sql = """
            SELECT nv.ho_ten, fe.vector_data 
            FROM face_embeddings fe 
            JOIN nhan_vien nv ON fe.ma_nv = nv.ma_nv
        """
        cursor.execute(sql)
        rows = cursor.fetchall()
        
        known_faces = []
        for row in rows:
            name = row['ho_ten']
            raw_data = row['vector_data']
            
            # --- KIỂM TRA ĐỊNH DẠNG DỮ LIỆU ---
            try:
                # 1. Thử giải mã JSON (Nếu anh lưu bằng json.dumps)
                if isinstance(raw_data, str):
                    embedding = np.array(json.loads(raw_data), dtype=np.float32)
                # 2. Nếu là bytes (Nếu anh lưu bằng .tobytes)
                elif isinstance(raw_data, bytes):
                    embedding = np.frombuffer(raw_data, dtype=np.float32)
                else:
                    print(f"⚠️ Dữ liệu lạ của {name}: {type(raw_data)}")
                    continue

                # --- QUAN TRỌNG: CHUẨN HÓA VECTOR ---
                norm = np.linalg.norm(embedding)
                if norm != 0: 
                    embedding = embedding / norm # Chia cho độ dài để về đơn vị chuẩn
                
                known_faces.append({"name": name, "emb": embedding})
                
            except Exception as e:
                print(f"❌ Lỗi đọc dữ liệu của {name}: {e}")

        conn.close()
        print(f"✅ Đã tải {len(known_faces)} khuôn mặt vào RAM.")
        return known_faces
    except Exception as e:
        print(f"❌ Lỗi kết nối DB: {e}")
        return []

def main():
    known_faces = load_embeddings_from_db()
    
    if not known_faces:
        print("🔴 Database trống hoặc lỗi kết nối! Không thể test.")
        return

    print("\n📸 BẬT CAMERA DEBUG...")
    print("👉 Hãy nhìn vào Camera. Màn hình sẽ hiện ĐIỂM SỐ SO SÁNH.")
    print("👉 Nhấn 'q' để thoát.")

    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret: break

        faces = app.get(frame)
        
        # Vẽ lên màn hình
        debug_info = []
        
        for face in faces:
            # Lấy vector mặt hiện tại và CHUẨN HÓA
            curr_emb = face.embedding
            norm = np.linalg.norm(curr_emb)
            if norm != 0: curr_emb = curr_emb / norm
            
            # So sánh với Database
            max_score = 0
            best_name = "Unknown"
            
            for person in known_faces:
                # TÍNH ĐIỂM GIỐNG NHAU (Cosine Similarity)
                score = np.dot(curr_emb, person['emb'])
                
                # In ra log để anh Trung xem
                print(f"   🔍 So sánh với {person['name']}: {score:.4f}")
                
                if score > max_score:
                    max_score = score
                    best_name = person['name']
            
            # Hiển thị kết quả
            box = face.bbox.astype(int)
            color = (0, 255, 0) if max_score > 0.65 else (0, 0, 255)
            
            # Vẽ khung
            cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), color, 2)
            
            # Hiện tên và điểm số
            text = f"{best_name} ({max_score:.2f})"
            cv2.putText(frame, text, (box[0], box[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            
            print(f"👉 KẾT QUẢ CUỐI: {best_name} - {max_score:.4f}\n")

        cv2.imshow("DEBUG AI (Nhan 'q' thoat)", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
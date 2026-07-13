!pip install deepface opencv-python tf-keras




import cv2
import os
import threading
from deepface import DeepFace

# ==========================================
# SETUP: Database & Face Tracker
# ==========================================
DB_PATH = "secure_db"
os.makedirs(DB_PATH, exist_ok=True)

# 1. OPTIMIZATION: Pre-load the AI Model into RAM
print("Loading AI Models into memory. Please wait...")
DeepFace.build_model("Facenet")
print("AI Models Loaded!")

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# 2. OPTIMIZATION: Thread Safety Lock
state_lock = threading.Lock()

auth_status = "IDLE"  # Can be: IDLE, SCANNING, SUCCESS, DENIED, SPOOF
auth_distance = 0.0

# ==========================================
# UI HELPER: Sci-Fi Targeting Brackets
# ==========================================
def draw_smart_brackets(frame, x, y, w, h, color=(0, 0, 255), length=25, thickness=3):
    cv2.line(frame, (x, y), (x + length, y), color, thickness)
    cv2.line(frame, (x, y), (x, y + length), color, thickness)
    cv2.line(frame, (x + w, y), (x + w - length, y), color, thickness)
    cv2.line(frame, (x + w, y), (x + w, y + length), color, thickness)
    cv2.line(frame, (x, y + h), (x + length, y + h), color, thickness)
    cv2.line(frame, (x, y + h), (x, y + h - length), color, thickness)
    cv2.line(frame, (x + w, y + h), (x + w - length, y + h), color, thickness)
    cv2.line(frame, (x + w, y + h), (x + w, y + h - length), color, thickness)

# ==========================================
# STEP 1: REGISTRATION (Multi-Face Support)
# ==========================================
def register_face():
    print("\n--- REGISTRATION PHASE ---")
    
    # Check how many faces are already registered (ignoring the .pkl cache file)
    existing_faces = [f for f in os.listdir(DB_PATH) if f.endswith(('.jpg', '.png'))]
    if len(existing_faces) >= 1000:
        print("Storage Full: Maximum of 1000 faces already registered!")
        return

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    while True:
        ret, frame = cap.read()
        if not ret: 
            break
        
        clean_frame = frame.copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        face_detected = False
        for (x, y, w, h) in faces:
            draw_smart_brackets(frame, x, y, w, h, (0, 255, 0))
            face_detected = True

        cv2.putText(frame, "Step 1: CLICK WINDOW", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        if face_detected:
            cv2.putText(frame, "Step 2: Press 's' to Save", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            cv2.putText(frame, "Waiting for face...", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
        cv2.imshow("Face ID Setup", frame)
        
        key = cv2.waitKey(1) & 0xFF 
        if (key == ord('s') or key == ord('S')) and face_detected:
            for i in range(1, 101, 15):
                temp_frame = frame.copy()
                cv2.putText(temp_frame, f"Mapping 3D Geometry: {i}%...", (20, 110), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.imshow("Face ID Setup", temp_frame)
                cv2.waitKey(150) 
                
            new_face_path = os.path.join(DB_PATH, f"face_{len(existing_faces) + 1}.jpg")
            cv2.imwrite(new_face_path, clean_frame)
            
            # 3. SMART CACHING: Delete the old cache so DeepFace is forced to rebuild it with the new face!
            pkl_path = os.path.join(DB_PATH, "representations_facenet.pkl")
            if os.path.exists(pkl_path):
                os.remove(pkl_path)
                
            print(f"\n Biometric Data Encrypted and Saved as Face #{len(existing_faces) + 1}!")
            break
            
    cap.release()
    cv2.destroyAllWindows()

# ==========================================
# BACKGROUND AI THREAD (Scalable 1:N Search)
# ==========================================
def verify_face_worker(frame_to_check):
    global auth_status, auth_distance
    try:
        # 1. LIVENESS CHECK & FEATURE EXTRACTION (Runs only ONCE)
        live_objs = DeepFace.represent(
            img_path=frame_to_check, 
            model_name="Facenet",
            enforce_detection=False,
            anti_spoofing=True
        )
        
        if len(live_objs) > 0:
            is_real_human = live_objs[0].get("is_real", True)
            if not is_real_human:
                with state_lock:
                    auth_status = "SPOOF"
                return

        # 2. MASSIVE DATABASE SEARCH (Instantly searches 100s of faces)
        dfs = DeepFace.find(
            img_path=frame_to_check, 
            db_path=DB_PATH, 
            model_name="Facenet",
            distance_metric="cosine",
            enforce_detection=False,
            silent=True
        )
        
        # If the returned dataframe has rows, we found a match in the database!
        if len(dfs) > 0 and dfs[0].shape[0] > 0:
            best_distance = dfs[0]['distance'].values[0]
            with state_lock:
                auth_status = "SUCCESS"
                auth_distance = best_distance
        else:
            with state_lock:
                auth_status = "DENIED"
                
    except Exception as e:
        with state_lock:
            auth_status = "DENIED"

# ==========================================
# STEP 2: REAL-TIME SIMULATION
# ==========================================
def live_unlock():
    global auth_status
    
    existing_faces = [f for f in os.listdir(DB_PATH) if f.endswith(('.jpg', '.png'))]
    if not existing_faces:
        print("Error: No faces registered. Please run registration first.")
        return

    print(f"\n--- LIVE UNLOCK PHASE (Searching {len(existing_faces)} registered faces) ---")
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    with state_lock:
        auth_status = "IDLE"
    
    scan_line_y = 0
    scan_direction = 1
    
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        clean_frame = frame.copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        with state_lock:
            current_status = auth_status
        
        # 1. Handle UI and Face Tracking
        for (x, y, w, h) in faces:
            if current_status == "IDLE":
                color = (255, 255, 255) # White
            elif current_status == "SCANNING":
                color = (0, 165, 255)   # Orange
                
                scan_line_y += 15 * scan_direction
                if scan_line_y >= h: scan_direction = -1
                elif scan_line_y <= 0: scan_direction = 1
                cv2.line(frame, (x, y + scan_line_y), (x + w, y + scan_line_y), (0, 165, 255), 2)
                
            elif current_status == "SUCCESS":
                color = (0, 255, 0)     # Green
            else:
                color = (0, 0, 255)     # Red
                
            draw_smart_brackets(frame, x, y, w, h, color)

        # 2. Handle Text Overlays
        if current_status == "IDLE":
            cv2.putText(frame, "Press ENTER to Scan", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
        elif current_status == "SCANNING":
            cv2.putText(frame, "Searching Database...", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            
        elif current_status == "SUCCESS":
            cv2.putText(frame, "DEVICE UNLOCKED!", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
            cv2.imshow("Face ID Simulator", frame)
            cv2.waitKey(2000)
            break

        elif current_status == "SPOOF":
            cv2.putText(frame, "LIVENESS FAILED: FAKE DETECTED", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)
            cv2.imshow("Face ID Simulator", frame)
            cv2.waitKey(2500)
            break
            
        elif current_status == "DENIED":
            cv2.putText(frame, "FACE NOT RECOGNIZED", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
            cv2.imshow("Face ID Simulator", frame)
            cv2.waitKey(2000)
            break

        cv2.imshow("Face ID Simulator", frame)
        
        # 3. Handle Keyboard Inputs
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == ord('Q'):
            break
        elif key == 13 and current_status == "IDLE": # ENTER key
            with state_lock:
                auth_status = "SCANNING"
            scan_line_y = 0
            
            # Launch DeepFace background verification thread
            thread = threading.Thread(target=verify_face_worker, args=(clean_frame,))
            thread.daemon = True
            thread.start()
            
    cap.release()
    cv2.destroyAllWindows()

# ==========================================
# DRIVER EXECUTION CONTROL
# ==========================================
if __name__ == "__main__":
    # If folder is empty, register a profile first
    if not os.listdir(DB_PATH) or len([f for f in os.listdir(DB_PATH) if f.endswith(('.jpg', '.png'))]) == 0:
        register_face()
        
    # Start live scanner simulation
    live_unlock()

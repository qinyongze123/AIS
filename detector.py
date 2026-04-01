import cv2
import numpy as np
from PySide6.QtGui import QImage
from PySide6.QtCore import QThread
from remake import globals
from ultralytics import YOLO

# ====================================================================
# Rhythm Tracking Parameters
# ====================================================================
BBOX_SIZE = (100, 100)
RHYTHM_PEAK_WINDOW = 4
RHYTHM_BASE_Y_TOLERANCE = 8
RHYTHM_VELOCITY_TOLERANCE = 1
RHYTHM_EMA_ALPHA = 0.6

# ====================================================================
# Global Variables & Model Loading
# ====================================================================
latest_frame = None

try:
    yolo_model = YOLO("./yolo/v3.pt")
    if yolo_model:
        dummy_frame = np.zeros((700, 1200, 3), dtype=np.uint8)
        rgb_frame = cv2.cvtColor(dummy_frame, cv2.COLOR_BGR2RGB)
        yolo_model.predict(source=rgb_frame, conf=0.5, imgsz=960, verbose=False)
except Exception as e:
    yolo_model = None


# ====================================================================
# Needle Tracker Class
# ====================================================================
class NeedleTracker:
    # Tracks the needle tip using OpenCV Template Matching.
    # This tracker is initialized by either YOLO or a manual click.

    def __init__(self):
        self.template = None
        self.template_size = 50
        self.needle_pos = None
        self.tracking = False
        self.min_val = 1.0
        self.confident = False
        self.th_low = 0.15

    def set_needle_pos(self, frame, pos):
        # Sets/updates the tracker's template.
        x, y = int(pos[0]), int(pos[1])
        w = h = self.template_size // 2
        x1, x2 = max(0, x - w), min(frame.shape[1], x + w + 1)
        y1, y2 = max(0, y - h), min(frame.shape[0], y + h + 1)
        # Create the template by cropping a small area around the position.
        self.template = frame[y1:y2, x1:x2].copy()
        self.needle_pos = (x, y)
        self.tracking = True
        self.confident = True
        #print(f"Tracker template updated at position: {pos}")

    def track(self, frame):
        # Tracks the template in a new frame.
        if self.template is None or not self.tracking:
            self.confident = False
            self.min_val = 1.0
            return None

        res = cv2.matchTemplate(frame, self.template, cv2.TM_SQDIFF_NORMED)
        min_val, _, min_loc, _ = cv2.minMaxLoc(res)
        self.min_val = min_val

        w, h = self.template.shape[1], self.template.shape[0]
        center = (min_loc[0] + w // 2, min_loc[1] + h // 2)

        if min_val < self.th_low:
            self.confident = True
            self.needle_pos = center
            return center
        else:
            self.confident = False
            return None

g_tracker = NeedleTracker()


# ====================================================================
# Rhythm Tracking
# ====================================================================
class RhythmTrackWorker(QThread):
    # A QThread worker to run CSRT tracking and rhythm analysis.
    def __init__(self, start_frame, start_bbox):
        super().__init__()
        self.start_frame = start_frame
        self.start_bbox = start_bbox
        self.is_stopped = False
        self.frame_num = 0

    def run(self):
        # The main function of the thread.
        try:
            tracker = cv2.TrackerCSRT_create() # 1. Create the CSRT tracker instance *inside this thread*.
            tracker.init(self.start_frame, self.start_bbox) # 2. Initialize the tracker with the first frame and bounding box.
            _reset_rhythm_globals()

            while not self.is_stopped: # 3.Start the tracking loop.
                self.frame_num += 1
                frame = latest_frame
                if frame is None:
                    self.msleep(globals.refresh_rate)
                    continue

                ok, bbox = tracker.update(frame)

                if ok: # If tracking is successful, update the global bbox
                    globals.rhythm_bbox = tuple(map(int, bbox))
                    tracked_point_y = int(bbox[1] + bbox[3] / 2)
                    _rhythm_add_y(tracked_point_y, self.frame_num) # 6. Feed the new Y-value into the rhythm analysis algorithm.
                    globals.rhythm_status = _rhythm_get_status()
                else:
                    globals.rhythm_status = 0

                self.msleep(globals.refresh_rate)

        except Exception as e:
            pass
            #print(f"RhythmTrackWorker failed: {e}")

    def stop(self):
        self.is_stopped = True


# ====================================================================
# Function APIs for UI
# ====================================================================

def manual_start_or_update_tracking(pos):
    # Called by RIGHT-click in the UI. Sets the template tracker (g_tracker) to the clicked position.
    if latest_frame is None:
        return
    g_tracker.set_needle_pos(latest_frame, pos)
    globals.real_time_tip = [pos[0], pos[1]]

def auto_detect_and_start_tracking():
    # Called by calibration and calculation. Uses YOLO to find the needle, then starts the template tracker.
    if yolo_model is None:
        return None
    if latest_frame is None:
        return None

    rgb_frame = cv2.cvtColor(latest_frame, cv2.COLOR_BGR2RGB)
    results = yolo_model.predict(source=rgb_frame, conf=0.5, imgsz=960, verbose=False)

    if len(results) > 0 and results[0].boxes is not None and len(results[0].boxes) > 0:
        boxes = results[0].boxes
        max_idx = boxes.conf.argmax().item()
        max_conf = boxes.conf[max_idx].item()

        xyxy = boxes.xyxy[max_idx].cpu().numpy().astype(int)
        center_x, center_y = (xyxy[0] + xyxy[2]) // 2, (xyxy[1] + xyxy[3]) // 2

        g_tracker.set_needle_pos(latest_frame, (center_x, center_y))
        globals.real_time_tip = [center_x, center_y]

        #print(f"Auto-detection successful at ({center_x}, {center_y}), conf={max_conf:.4f}. Tracker started.")
        return (center_x, center_y)
    else:
        return None

def track_needle_tip(frame):
    # Called on every frame update from UltraSound. Runs g_tracker.
    if not g_tracker.tracking:
        return

    tracked_pos = g_tracker.track(frame)

    if g_tracker.confident and tracked_pos is not None:
        globals.real_time_tip = [tracked_pos[0], tracked_pos[1]]
    else:
        globals.real_time_tip = [-1, -1]

# ====================================================================
# Camera & Image Functions
# ====================================================================
def update_latest_frame(frame):
    global latest_frame
    latest_frame = frame

def detect_cameras(max_cams=2):
    found = []
    for idx in range(max_cams):
        cap = try_open_camera(idx)
        if cap is not None and cap.isOpened():
            found.append(idx)
            cap.release()
    return found

def try_open_camera(idx):
    try:
        if isinstance(idx, int):
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(idx)
        #cap = cv2.VideoCapture(idx)
        #cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        #cap = cv2.VideoCapture(idx, cv2.CAP_MSMF)
        if cap.isOpened():
            return cap
        else:
            cap.release()
            return None
    except Exception as e:
        #print(f"Error opening device {idx}: {e}")
        return None

def set_highest_resolution(cap, resolutions=[(1920, 1080)]):
    for w, h in resolutions:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if abs(actual_w - w) < 16 and abs(actual_h - h) < 16:
            break

def get_frame(cap):
    if cap is None or not cap.isOpened():
        return None
    ret, frame = cap.read()

    if not ret:
        total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        if total_frames > 0:
            #print("Video ended. Looping...")
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
            if not ret:
                return None
        else:
            return None
    return frame

def crop_frame(frame):
    if frame is None:
        return None
    h, w = frame.shape[:2]
    if w >= 1900 and h >= 1000:
        cropped = frame[175:875, 500:1700]
    else:
        y_start, y_end = 175, 875
        x_start, x_end = 500, 1700
        cropped = frame[min(y_start, h):min(y_end, h), min(x_start, w):min(x_end, w)]

    update_latest_frame(cropped)
    return cropped

def frame_to_qimage(frame):
    if frame is None:
        return None
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb_frame.shape
    bytes_per_line = ch * w
    return QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)

def black_screen_qimage():
    black = np.zeros((700, 1200, 3), dtype=np.uint8)
    return frame_to_qimage(black)


# ====================================================================
# Calib scale
# ====================================================================
def detect_scale():
    # Auto-detects the scale bar marks with X-axis verification.
    frame = latest_frame
    if frame is None:
        globals.calib_scale_points = [(-1, -1), (-1, -1)]
        return [(-1, -1), (-1, -1)]
    template = cv2.imread('temp.png', 0)
    if template is None or template.size == 0:
        globals.calib_scale_points = [(-1, -1), (-1, -1)]
        return [(-1, -1), (-1, -1)]

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame

    _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
    th, tw = template.shape[:2]
    res = cv2.matchTemplate(binary, template, cv2.TM_SQDIFF)
    loc = np.where(res <= 1)
    raw_matches = list(zip(*loc[::-1]))
    matches = []

    if raw_matches:
        x_scores = []
        for pt in raw_matches:
            score = sum(1 for other in raw_matches if other[0] == pt[0])
            x_scores.append((pt, score))
        best_pt, _ = max(x_scores, key=lambda item: item[1])
        dominant_x = best_pt[0]

        matches = [pt for pt in raw_matches if abs(pt[0] - dominant_x) <= 3]

    matches = sorted(matches, key=lambda pt: pt[1])

    if len(matches) < 3:
        globals.calib_scale_points = [(-1, -1), (-1, -1)]
        return [(-1, -1), (-1, -1)]

    y1 = matches[-3][1] + th // 2
    y3 = matches[-1][1] + th // 2
    x_mark = matches[0][0] + tw // 2

    globals.calib_scale_points = [(x_mark, y1), (x_mark, y3)]
    return [(x_mark, y1), (x_mark, y3)]


# ====================================================================
# Rhythm Algorithm
# ====================================================================
def start_rhythm_tracking():
    # Called by 'Calculate' button.
    if latest_frame is None: return
    point_xy = globals.clicked_xy
    if point_xy == [-1, -1] or point_xy == [0, 0]: return

    stop_rhythm_tracking()

    try:
        x, y = point_xy
        h_img, w_img = latest_frame.shape[:2]
        w_bbox, h_bbox = BBOX_SIZE
        tx = max(0, min(x - w_bbox // 2, w_img - w_bbox))
        ty = max(0, min(y - h_bbox // 2, h_img - h_bbox))
        bbox = (int(tx), int(ty), int(w_bbox), int(h_bbox))

        globals.rhythm_initial_point = point_xy
        globals.rhythm_bbox = bbox

        globals.rhythm_tracker_thread = RhythmTrackWorker(latest_frame, bbox)
        globals.rhythm_tracker_thread.start()
        #print(f"RhythmTrackWorker {point_xy} started")

    except Exception as e:
        pass
        #print(f"Failed: {e}")

def stop_rhythm_tracking():
    # Called by 'Stop', 'Unlock', 'Calculate', etc.
    if globals.rhythm_tracker_thread is not None:
        globals.rhythm_tracker_thread.stop()
        globals.rhythm_tracker_thread.wait(500)
        globals.rhythm_tracker_thread = None

    globals.rhythm_bbox = None
    globals.rhythm_initial_point = None
    _reset_rhythm_globals()

def _reset_rhythm_globals():
    globals.rhythm_status = 0
    globals.rhythm_history.clear()
    globals.rhythm_smooth_history.clear()
    globals.rhythm_last_smooth_y = None
    globals.rhythm_troughs.clear()
    globals.rhythm_base_y_history.clear()
    globals.rhythm_is_calibrated = False
    globals.rhythm_base_y = 0.0

def _rhythm_add_y(y_val, frame_num):
    # Adds a new Y-value to the algorithm.
    globals.rhythm_history.append((frame_num, y_val))
    globals.rhythm_smooth_history.append(y_val)
    if len(globals.rhythm_smooth_history) < globals.rhythm_smooth_history.maxlen:
        return

    current_smooth_y = sum(globals.rhythm_smooth_history) / len(globals.rhythm_smooth_history) # Calculate the current smoothed Y value.
    globals.rhythm_last_smooth_y = current_smooth_y
    k = RHYTHM_PEAK_WINDOW
    if len(globals.rhythm_history) < k * 2 + 1: return

    # Base Detection
    idx_to_check = len(globals.rhythm_history) - k - 1 # Get the data point from 'k' frames ago.
    current_frame, current_y = globals.rhythm_history[idx_to_check]
    if not globals.rhythm_troughs or current_frame > globals.rhythm_troughs[-1][0]: # Check if this point is a new base (local minimum).
        is_base_y = True
        for i in range(1, k + 1):
            if (globals.rhythm_history[idx_to_check - i][1] > current_y or
                    globals.rhythm_history[idx_to_check + i][1] > current_y):
                is_base_y = False; break
        if is_base_y:
            globals.rhythm_troughs.append((current_frame, current_y))
            _rhythm_update_calibration(trough_val=current_y)
            return
    if globals.rhythm_is_calibrated:
        globals.rhythm_base_y_history.append((frame_num, globals.rhythm_base_y))

def _rhythm_update_calibration(trough_val):
    # Updates the stable 'base_y' by (alpha * trough_val) + ((1 - alpha) * globals.rhythm_base_y).
    if not globals.rhythm_is_calibrated:
        globals.rhythm_base_y = trough_val
        globals.rhythm_is_calibrated = True
    else:
        alpha = RHYTHM_EMA_ALPHA
        globals.rhythm_base_y = (alpha * trough_val) + ((1 - alpha) * globals.rhythm_base_y)

def _rhythm_get_status():
    #Returns the final status (0=Unstable, 1=Stable).
    if not globals.rhythm_is_calibrated or globals.rhythm_last_smooth_y is None or len(globals.rhythm_smooth_history) < 2:
        return 0
    current_smooth_y = globals.rhythm_last_smooth_y

    is_near_base = abs(current_smooth_y - globals.rhythm_base_y) <= RHYTHM_BASE_Y_TOLERANCE # 1. Position Check: point near base Y?
    if not is_near_base:
        return 0

    try: # 2. Velocity Check: point's movement stable?
        prev_smooth_y = sum(list(globals.rhythm_smooth_history)[:-1]) / (globals.rhythm_smooth_history.maxlen - 1)
        current_velocity = current_smooth_y - prev_smooth_y
    except ZeroDivisionError:
        current_velocity = 0

    is_stable = abs(current_velocity) < RHYTHM_VELOCITY_TOLERANCE
    if is_stable:
        return 1
    is_moving_up = current_velocity < -RHYTHM_VELOCITY_TOLERANCE
    if is_moving_up:
        return 0

    return 0
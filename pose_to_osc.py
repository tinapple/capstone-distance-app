import cv2
import mediapipe as mp
from pythonosc import udp_client
import time
import sys
from one_euro_filter import OneEuroFilter

# Initialize MediaPipe Face Detection and Pose
mp_face_detection = mp.solutions.face_detection
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

# Resolution presets (width, height)
RESOLUTIONS = [
    (320, 240),    # Low res
    (640, 480),    # Standard
    (1280, 720),   # HD
    (1920, 1080)   # Full HD
]
current_resolution = 1  # Start with 640x480

# Initialize One Euro Filters for face tracking
filters = {
    'x': OneEuroFilter(freq=120, mincutoff=0.4, beta=0.4),
    'y': OneEuroFilter(freq=120, mincutoff=0.4, beta=0.4),
    'z': OneEuroFilter(freq=120, mincutoff=0.4, beta=0.4)
}

# Initialize One Euro Filter for distance
distance_filter = OneEuroFilter(freq=120, mincutoff=0.1, beta=0.2)  # Gentler smoothing

# Initialize face detection and pose detection
face_detection = mp_face_detection.FaceDetection(
    model_selection=0,  # 0 for short-range detection (within 2 meters)
    min_detection_confidence=0.7
)
pose = mp_pose.Pose(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Initialize webcam
cap = cv2.VideoCapture(0)
width, height = RESOLUTIONS[current_resolution]
cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

# Initialize OSC client
client = udp_client.SimpleUDPClient("127.0.0.1", 5005)

# Variables for FPS calculation
prev_frame_time = 0
fps_values = []
fps_window_size = 30

# Mode switching (0 = face detection, 1 = body pose)
current_mode = 0

def estimate_distance(landmarks, image):
    """
    Calculate the pixel area of the torso/head bounding box.
    Returns the area in pixels.
    """
    h, w, _ = image.shape
    
    # Key points (torso and head only)
    key_points = [
        mp_pose.PoseLandmark.NOSE,
        mp_pose.PoseLandmark.LEFT_SHOULDER,
        mp_pose.PoseLandmark.RIGHT_SHOULDER,
        mp_pose.PoseLandmark.LEFT_HIP,
        mp_pose.PoseLandmark.RIGHT_HIP
    ]
    
    # Collect visible points
    visible_points = []
    for point_id in key_points:
        point = landmarks[point_id]
        if point.visibility > 0.7:  # Only use highly visible points
            # Convert normalized coordinates to pixel coordinates
            x_px = int(point.x * w)
            y_px = int(point.y * h)
            visible_points.append((x_px, y_px))
    
    if len(visible_points) < 4:  # Need at least 4 points for reliable measurement
        return None
    
    # Calculate the bounding box in pixels
    x_coords = [p[0] for p in visible_points]
    y_coords = [p[1] for p in visible_points]
    
    x_min, x_max = min(x_coords), max(x_coords)
    y_min, y_max = min(y_coords), max(y_coords)
    
    # Calculate area in pixels
    width_px = x_max - x_min
    height_px = y_max - y_min
    area_px = width_px * height_px
    
    # Add debug visualization
    cv2.putText(image, f"Area (px): {area_px}", (10, 200), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    
    # Draw bounding box
    cv2.rectangle(image, (x_min, y_min), (x_max, y_max), (0, 255, 255), 1)
    
    # Draw points used for measurement
    for x, y in visible_points:
        cv2.circle(image, (x, y), 4, (255, 255, 0), -1)
    
    return area_px

while cap.isOpened():
    success, image = cap.read()
    if not success:
        continue

    # Calculate FPS
    current_time = time.time()
    fps = 1 / (current_time - prev_frame_time) if prev_frame_time > 0 else 0
    prev_frame_time = current_time
    fps_values.append(fps)
    if len(fps_values) > fps_window_size:
        fps_values.pop(0)
    avg_fps = sum(fps_values) / len(fps_values)

    # Convert the BGR image to RGB
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image.flags.writeable = False

    # Process based on current mode
    if current_mode == 0:
        results = face_detection.process(image)
    else:
        results = pose.process(image)

    # Convert back to BGR for OpenCV
    image.flags.writeable = True
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    # Draw based on current mode
    if current_mode == 0 and results.detections:  # Face Detection
        # Find the largest face
        largest_face = None
        max_area = 0
        
        for detection in results.detections:
            bbox = detection.location_data.relative_bounding_box
            area = bbox.width * bbox.height
            if area > max_area:
                max_area = area
                largest_face = detection
        
        if largest_face:
            # Draw the face detection box
            mp_drawing.draw_detection(image, largest_face)
            
            # Get face bounding box
            bbox = largest_face.location_data.relative_bounding_box
            
            # Convert relative coordinates to pixel coordinates
            h, w, _ = image.shape
            x = bbox.xmin * w
            y = bbox.ymin * h
            width = bbox.width * w
            height = bbox.height * h
            
            # Calculate center point of face
            center_x = x + (width / 2)
            center_y = y + (height / 2)
            z = 2.0 - (width * height) / (w * h)  # Rough depth estimate
            
            # Apply One Euro Filter
            filtered_x = filters['x'](center_x / w, current_time)  # Normalize to 0-1
            filtered_y = filters['y'](center_y / h, current_time)  # Normalize to 0-1
            filtered_z = filters['z'](z, current_time)
            
            # Draw tracking ball (yellow circle)
            ball_x = int(filtered_x * w)
            ball_y = int(filtered_y * h)
            cv2.circle(image, (ball_x, ball_y), 10, (0, 255, 255), -1)  # Yellow filled circle
            
            # Draw area indicator (helps visualize which face is being tracked)
            cv2.putText(image, f"Area: {max_area:.3f}", (int(x), int(y - 10)), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            
            # Send OSC messages
            client.send_message("/face/position/x", filtered_x)
            client.send_message("/face/position/y", filtered_y)
            client.send_message("/face/position/z", filtered_z)
            
            # Display values on screen
            cv2.putText(image, f"Pos: ({filtered_x:.2f}, {filtered_y:.2f}, {filtered_z:.2f})", 
                       (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            cv2.putText(image, f"Faces detected: {len(results.detections)}", 
                       (10, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    elif current_mode == 1 and results.pose_landmarks:  # Body Pose
        # Draw pose landmarks first
        mp_drawing.draw_landmarks(
            image,
            results.pose_landmarks,
            mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=2),
            connection_drawing_spec=mp_drawing.DrawingSpec(color=(245,66,230), thickness=2)
        )
        
        landmarks = results.pose_landmarks.landmark
        
        # Estimate and filter distance
        area = estimate_distance(landmarks, image)
        if area is not None:
            filtered_area = distance_filter(area, current_time)
            
            # Send OSC message with pixel area
            client.send_message("/body/distance", filtered_area)
            
            # Visualize distance
            # Scale for visualization (adjust these values based on your camera resolution)
            max_expected_area = 150000  # Adjust based on testing
            normalized_area = min(filtered_area / max_expected_area, 1.0)
            
            # Use blue to yellow color gradient for better visibility
            color = (
                int(255 * (1 - normalized_area)),  # Blue
                int(255 * (1 - normalized_area)),  # Green
                int(255 * normalized_area)  # Red
            )
            
            # Draw distance indicator bar
            bar_length = 200
            bar_height = 20
            bar_y = 180
            
            # Background bar
            cv2.rectangle(image, (10, bar_y), (10 + bar_length, bar_y + bar_height), 
                        (50, 50, 50), -1)
            
            # Distance bar
            filled_length = int(bar_length * normalized_area)
            cv2.rectangle(image, (10, bar_y), (10 + filled_length, bar_y + bar_height), 
                        color, -1)
            
            # Also send key body points via OSC
            nose = landmarks[mp_pose.PoseLandmark.NOSE]
            client.send_message("/body/nose/x", nose.x)
            client.send_message("/body/nose/y", nose.y)
            client.send_message("/body/nose/z", nose.z)
            
            left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
            right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
            client.send_message("/body/shoulders/left/x", left_shoulder.x)
            client.send_message("/body/shoulders/left/y", left_shoulder.y)
            client.send_message("/body/shoulders/right/x", right_shoulder.x)
            client.send_message("/body/shoulders/right/y", right_shoulder.y)
            
            left_hand = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]
            right_hand = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
            client.send_message("/body/hands/left/x", left_hand.x)
            client.send_message("/body/hands/left/y", left_hand.y)
            client.send_message("/body/hands/right/x", right_hand.x)
            client.send_message("/body/hands/right/y", right_hand.y)

    # Display FPS and processing time
    cv2.putText(image, f"FPS: {avg_fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(image, f"Mode: {'Face' if current_mode == 0 else 'Body'}", (10, 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(image, f"Resolution: {width}x{height}", (10, 90), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # Display the image
    cv2.imshow('MediaPipe Face/Body Tracking', image)

    # Handle keyboard input
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('m'):
        current_mode = 1 - current_mode  # Toggle between 0 and 1
    elif key == ord('r'):
        current_resolution = (current_resolution + 1) % len(RESOLUTIONS)
        width, height = RESOLUTIONS[current_resolution]
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

cap.release()
cv2.destroyAllWindows()

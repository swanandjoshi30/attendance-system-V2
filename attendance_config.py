"""Prototype configuration for the attendance system."""

import os


DB_CONFIG = {
    'host': os.getenv('ATTENDANCE_DB_HOST', 'localhost'),
    'database': os.getenv('ATTENDANCE_DB_NAME', 'attendance2'),
    'user': os.getenv('ATTENDANCE_DB_USER', 'postgres'),
    'password': os.getenv('ATTENDANCE_DB_PASSWORD', 'Pass@123'),
    'port': int(os.getenv('ATTENDANCE_DB_PORT', '5432')),
}

FACE_RECOGNITION_CONFIG = {
    'tolerance': 6000,
    'model': 'opencv',
    'num_jitters': 1,
    'detection_scale': 0.5,
    'encoding_scale': 1.0,
}

ATTENDANCE_COOLDOWN = 300

CAMERA_CONFIG = {
    'default_camera': 0,
    'frame_width': 1280,
    'frame_height': 720,
    'fps': 30
}

# UI Settings
UI_CONFIG = {
    'theme': 'default',  # ttk theme
    'primary_color': '#2196F3',
    'success_color': '#4CAF50',
    'error_color': '#F44336',
    'warning_color': '#FF9800'
}

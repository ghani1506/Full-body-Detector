# Expert Full Body 3D Skeleton Tracker

Cloud-safe expert version.

Upload only:
- app.py
- README.md

Do not upload dependency files:
- requirements.txt
- runtime.txt
- packages.txt
- pyproject.toml
- setup.py
- Pipfile
- environment.yml

## Features

- Browser-based MediaPipe Pose
- No cv2
- No OpenCV
- No Python MediaPipe
- More precise model settings
- 960 x 720 camera processing
- Smoothed landmarks
- 3D skeleton visualisation
- 2D and 3D joint-angle estimation
- Shoulder tilt
- Hip tilt
- Body lean
- Segment measurements
- Symmetry analysis
- Visibility/confidence scoring
- Landmark CSV export
- Angle/posture CSV export

## Accuracy note

This is a stronger expert prototype, but it is still not true laboratory-grade skeletal tracking.
A single normal camera cannot perfectly estimate hidden joints, true depth, or real bone lengths.

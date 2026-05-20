# Full Body 3D Detector - Cloud Safe Version

This version is designed to avoid Streamlit Cloud installer errors.

It does **not** use:

- OpenCV
- cv2
- Python MediaPipe
- heavy computer vision Python wheels

Instead, it uses browser-based MediaPipe Pose through JavaScript CDN.

## Files

```text
app.py
requirements.txt
runtime.txt
README.md
.gitignore
```

## Deploy to Streamlit Cloud

1. Create a GitHub repository.
2. Upload all files.
3. Go to Streamlit Community Cloud.
4. Select your repository.
5. Set main file path:

```text
app.py
```

6. Deploy.

## Why this version works better

Streamlit Cloud often fails when installing computer vision packages such as:

```text
opencv-python-headless
mediapipe
cv2
```

This app avoids those packages. Only Streamlit is installed.

## Features

- Full body pose detection
- 33 landmarks
- 3D skeleton plot
- Joint angle estimation
- CSV download
- Browser camera input

## Limitations

This app is suitable for classroom research, prototype research, and exploratory movement analysis.

It is not equivalent to laboratory motion capture systems such as Vicon or Qualisys.

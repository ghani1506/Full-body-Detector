# Research Grade 3D Full Body Tracking App

A deployable Streamlit app for full-body pose tracking, approximate 3D landmark visualisation, joint-angle estimation, annotated video output, and CSV export.

## Features

- Full-body 33-point pose landmark detection
- Approximate 3D skeleton visualisation
- Image upload
- Camera photo input
- Video upload and processing
- Annotated output video
- Landmark CSV export
- Joint-angle CSV export
- Angle trend chart for video analysis

## Important Accuracy Note

This app uses MediaPipe Pose. It is useful for exploratory research and educational research prototypes, but it is not a replacement for calibrated laboratory motion-capture systems.

The `z_norm` value is an estimated relative depth value, not true measured depth in metres.

## Files

```text
research_3d_body_tracking_app/
├── app.py
├── requirements.txt
├── runtime.txt
├── README.md
└── .gitignore
```

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Create a new GitHub repository.
2. Upload all files in this folder.
3. Go to Streamlit Community Cloud.
4. Choose the GitHub repository.
5. Set main file path as:

```text
app.py
```

6. Deploy.

## Recommended Research Protocol

For better data consistency:

1. Use a fixed camera position.
2. Keep lighting constant.
3. Ensure full body is visible.
4. Use plain background.
5. Keep camera angle constant.
6. Avoid loose clothing.
7. Record the same movement several times.
8. Analyse trends across frames, not only one frame.

## Possible Research Variables

- Left knee angle
- Right knee angle
- Left elbow angle
- Right elbow angle
- Left hip angle
- Right hip angle
- Shoulder angle
- Landmark visibility score
- Movement symmetry
- Angle change over time

## Suggested Research Question

> Can a computer-vision-based 3D body tracking tool provide consistent joint-angle indicators for classroom-based movement analysis?

## Suggested Citation Statement

This tool uses MediaPipe Pose for full-body landmark detection and Streamlit for interactive deployment.


## Cloud-safe dependency version

This version avoids installing `opencv-python-headless` directly because MediaPipe already manages a compatible OpenCV dependency.  
If Streamlit Cloud gives a dependency installer error, check that your repository includes:

```text
requirements.txt
runtime.txt
app.py
```

Use Python 3.11 on Streamlit Cloud.

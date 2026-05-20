import streamlit as st
import cv2
import numpy as np
import pandas as pd
import tempfile
from pathlib import Path
import mediapipe as mp
import plotly.graph_objects as go
from PIL import Image
import time

st.set_page_config(
    page_title="Research Grade 3D Full Body Tracking",
    page_icon="🧍",
    layout="wide"
)

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

LANDMARK_NAMES = [lm.name for lm in mp_pose.PoseLandmark]

POSE_CONNECTIONS = list(mp_pose.POSE_CONNECTIONS)

def calculate_angle(a, b, c):
    """
    Calculate 2D joint angle ABC in degrees using x,y coordinates.
    a, b, c are arrays/lists: [x, y]
    """
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)

    ba = a - b
    bc = c - b

    cosine = np.dot(ba, bc) / ((np.linalg.norm(ba) * np.linalg.norm(bc)) + 1e-9)
    cosine = np.clip(cosine, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosine)))

def extract_landmarks(results, frame_id=None, timestamp=None):
    if not results.pose_landmarks:
        return []

    rows = []
    for idx, lm in enumerate(results.pose_landmarks.landmark):
        rows.append({
            "frame": frame_id,
            "timestamp_sec": timestamp,
            "landmark_id": idx,
            "landmark_name": LANDMARK_NAMES[idx],
            "x_norm": lm.x,
            "y_norm": lm.y,
            "z_norm": lm.z,
            "visibility": lm.visibility
        })
    return rows

def get_landmark_dict(results):
    if not results.pose_landmarks:
        return None
    return {
        LANDMARK_NAMES[i]: np.array([lm.x, lm.y, lm.z, lm.visibility])
        for i, lm in enumerate(results.pose_landmarks.landmark)
    }

def compute_angles(results, frame_id=None, timestamp=None):
    lm = get_landmark_dict(results)
    if lm is None:
        return {}

    def xy(name):
        return lm[name][:2]

    angle_defs = {
        "left_elbow": ("LEFT_SHOULDER", "LEFT_ELBOW", "LEFT_WRIST"),
        "right_elbow": ("RIGHT_SHOULDER", "RIGHT_ELBOW", "RIGHT_WRIST"),
        "left_shoulder": ("LEFT_ELBOW", "LEFT_SHOULDER", "LEFT_HIP"),
        "right_shoulder": ("RIGHT_ELBOW", "RIGHT_SHOULDER", "RIGHT_HIP"),
        "left_knee": ("LEFT_HIP", "LEFT_KNEE", "LEFT_ANKLE"),
        "right_knee": ("RIGHT_HIP", "RIGHT_KNEE", "RIGHT_ANKLE"),
        "left_hip": ("LEFT_SHOULDER", "LEFT_HIP", "LEFT_KNEE"),
        "right_hip": ("RIGHT_SHOULDER", "RIGHT_HIP", "RIGHT_KNEE"),
    }

    out = {"frame": frame_id, "timestamp_sec": timestamp}
    for angle_name, (a, b, c) in angle_defs.items():
        try:
            out[angle_name] = calculate_angle(xy(a), xy(b), xy(c))
        except Exception:
            out[angle_name] = np.nan

    return out

def draw_pose_on_frame(frame, results):
    annotated = frame.copy()
    if results.pose_landmarks:
        mp_drawing.draw_landmarks(
            annotated,
            results.pose_landmarks,
            mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=mp_drawing.DrawingSpec(thickness=2, circle_radius=2),
            connection_drawing_spec=mp_drawing.DrawingSpec(thickness=2)
        )
    return annotated

def make_3d_plot(results):
    if not results.pose_landmarks:
        return None

    xs, ys, zs, labels = [], [], [], []
    for i, lm in enumerate(results.pose_landmarks.landmark):
        xs.append(lm.x)
        ys.append(-lm.y)
        zs.append(-lm.z)
        labels.append(LANDMARK_NAMES[i])

    fig = go.Figure()

    fig.add_trace(go.Scatter3d(
        x=xs, y=ys, z=zs,
        mode="markers+text",
        text=labels,
        textposition="top center",
        marker=dict(size=4),
        name="Landmarks"
    ))

    for a, b in POSE_CONNECTIONS:
        fig.add_trace(go.Scatter3d(
            x=[xs[a], xs[b]],
            y=[ys[a], ys[b]],
            z=[zs[a], zs[b]],
            mode="lines",
            showlegend=False
        ))

    fig.update_layout(
        height=650,
        margin=dict(l=0, r=0, b=0, t=30),
        scene=dict(
            xaxis_title="X",
            yaxis_title="Y",
            zaxis_title="Z",
            aspectmode="cube"
        )
    )
    return fig

def process_image(image_array, model_complexity, min_detection_confidence, min_tracking_confidence):
    image_rgb = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)

    with mp_pose.Pose(
        static_image_mode=True,
        model_complexity=model_complexity,
        enable_segmentation=False,
        min_detection_confidence=min_detection_confidence,
        min_tracking_confidence=min_tracking_confidence
    ) as pose:
        results = pose.process(image_rgb)

    annotated = draw_pose_on_frame(image_array, results)
    landmark_rows = extract_landmarks(results, frame_id=0, timestamp=0.0)
    angle_row = compute_angles(results, frame_id=0, timestamp=0.0)

    return annotated, results, pd.DataFrame(landmark_rows), pd.DataFrame([angle_row]) if angle_row else pd.DataFrame()

def process_video(video_path, model_complexity, min_detection_confidence, min_tracking_confidence, frame_stride):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError("Could not open video file.")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)

    output_path = Path(tempfile.gettempdir()) / f"annotated_pose_{int(time.time())}.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps / max(frame_stride, 1), (width, height))

    all_landmarks = []
    all_angles = []
    last_results = None

    progress = st.progress(0)
    status = st.empty()

    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=model_complexity,
        enable_segmentation=False,
        min_detection_confidence=min_detection_confidence,
        min_tracking_confidence=min_tracking_confidence
    ) as pose:
        frame_id = 0
        processed_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_id % frame_stride == 0:
                timestamp = frame_id / fps
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = pose.process(rgb)
                last_results = results

                annotated = draw_pose_on_frame(frame, results)
                writer.write(annotated)

                all_landmarks.extend(extract_landmarks(results, frame_id=frame_id, timestamp=timestamp))
                angle_row = compute_angles(results, frame_id=frame_id, timestamp=timestamp)
                if angle_row:
                    all_angles.append(angle_row)

                processed_count += 1

            frame_id += 1
            if total_frames > 0:
                progress.progress(min(frame_id / total_frames, 1.0))
                status.write(f"Processing frame {frame_id}/{total_frames}")

    cap.release()
    writer.release()
    progress.empty()
    status.empty()

    return output_path, last_results, pd.DataFrame(all_landmarks), pd.DataFrame(all_angles)

st.title("🧍 Research Grade 3D Full Body Tracking App")
st.caption("Full-body pose landmark extraction, 3D visualisation, joint-angle estimation, and CSV export using MediaPipe + Streamlit.")

with st.sidebar:
    st.header("Model Settings")
    model_complexity = st.selectbox(
        "Model complexity",
        options=[0, 1, 2],
        index=1,
        help="2 is more accurate but slower. 1 is recommended for most laptops."
    )
    min_detection_confidence = st.slider("Minimum detection confidence", 0.1, 1.0, 0.5, 0.05)
    min_tracking_confidence = st.slider("Minimum tracking confidence", 0.1, 1.0, 0.5, 0.05)
    frame_stride = st.slider(
        "Video frame stride",
        min_value=1,
        max_value=10,
        value=2,
        help="1 = process every frame. Higher values are faster but less detailed."
    )

    st.divider()
    st.info(
        "Research note: MediaPipe 3D coordinates are relative model coordinates, not calibrated laboratory motion-capture coordinates."
    )

tab1, tab2, tab3 = st.tabs(["📷 Image / Camera", "🎞️ Video Upload", "📘 Research Notes"])

with tab1:
    st.subheader("Image or Camera Pose Tracking")

    source = st.radio("Choose input", ["Upload image", "Use camera"], horizontal=True)

    image_file = None
    if source == "Upload image":
        image_file = st.file_uploader("Upload image", type=["jpg", "jpeg", "png"])
    else:
        image_file = st.camera_input("Take a full-body photo")

    if image_file is not None:
        pil_img = Image.open(image_file).convert("RGB")
        image_array = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        annotated, results, landmarks_df, angles_df = process_image(
            image_array,
            model_complexity,
            min_detection_confidence,
            min_tracking_confidence
        )

        col1, col2 = st.columns(2)
        with col1:
            st.image(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB), caption="Detected full-body landmarks", use_container_width=True)
        with col2:
            fig = make_3d_plot(results)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No pose detected. Try a clearer full-body image.")

        if not landmarks_df.empty:
            st.subheader("Landmark Data")
            st.dataframe(landmarks_df, use_container_width=True)

            st.download_button(
                "Download landmarks CSV",
                data=landmarks_df.to_csv(index=False).encode("utf-8"),
                file_name="pose_landmarks_image.csv",
                mime="text/csv"
            )

        if not angles_df.empty:
            st.subheader("Joint Angle Data")
            st.dataframe(angles_df, use_container_width=True)

            st.download_button(
                "Download joint angles CSV",
                data=angles_df.to_csv(index=False).encode("utf-8"),
                file_name="joint_angles_image.csv",
                mime="text/csv"
            )

with tab2:
    st.subheader("Video-Based Full Body Tracking")

    video_file = st.file_uploader("Upload video", type=["mp4", "mov", "avi", "mkv"])

    if video_file is not None:
        suffix = Path(video_file.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_video:
            temp_video.write(video_file.read())
            temp_video_path = Path(temp_video.name)

        st.video(str(temp_video_path))

        if st.button("Run full-body tracking on video"):
            try:
                output_video_path, last_results, landmarks_df, angles_df = process_video(
                    temp_video_path,
                    model_complexity,
                    min_detection_confidence,
                    min_tracking_confidence,
                    frame_stride
                )

                st.success("Video tracking complete.")

                st.subheader("Annotated Video")
                st.video(str(output_video_path))

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Landmark rows", len(landmarks_df))
                    st.metric("Angle rows", len(angles_df))
                with col2:
                    fig = make_3d_plot(last_results) if last_results else None
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("No final pose detected for 3D preview.")

                if not landmarks_df.empty:
                    st.subheader("Landmark Data")
                    st.dataframe(landmarks_df.head(1000), use_container_width=True)
                    st.download_button(
                        "Download full video landmarks CSV",
                        data=landmarks_df.to_csv(index=False).encode("utf-8"),
                        file_name="pose_landmarks_video.csv",
                        mime="text/csv"
                    )

                if not angles_df.empty:
                    st.subheader("Joint Angle Data")
                    st.dataframe(angles_df.head(1000), use_container_width=True)
                    st.line_chart(
                        angles_df.set_index("timestamp_sec").drop(columns=["frame"], errors="ignore")
                    )
                    st.download_button(
                        "Download full video joint angles CSV",
                        data=angles_df.to_csv(index=False).encode("utf-8"),
                        file_name="joint_angles_video.csv",
                        mime="text/csv"
                    )

            except Exception as e:
                st.error(f"Processing failed: {e}")

with tab3:
    st.subheader("Research Use and Limitations")
    st.markdown(
        """
### What this app can do
- Detect 33 full-body pose landmarks.
- Produce approximate 3D landmark coordinates.
- Draw full-body skeleton overlays.
- Estimate major joint angles.
- Export reproducible CSV data for analysis.
- Process still images, camera photos, and uploaded videos.

### Important research limitations
This is suitable for **prototype research, classroom research, sports observation, movement screening, and exploratory analysis**.

It is **not equivalent to laboratory motion capture** such as Vicon or Qualisys because:
- Camera calibration is not included.
- Depth is estimated, not directly measured.
- Coordinates are relative to the MediaPipe model.
- Loose clothing, occlusion, camera angle, and lighting affect accuracy.

### Recommended data collection protocol
For better consistency:
1. Use a fixed camera position.
2. Ensure full body is visible.
3. Use strong lighting.
4. Avoid background clutter.
5. Keep the participant at a consistent distance.
6. Use the same frame rate and camera angle for all participants.
7. Export CSV files and analyse angle trends rather than relying only on one frame.

### Suggested research outputs
- Knee angle during squats.
- Elbow angle during throwing movement.
- Hip angle during jumping or sitting.
- Posture comparison before and after intervention.
- Movement consistency across repeated trials.
        """
    )

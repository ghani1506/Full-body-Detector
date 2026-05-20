import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Full Body 3D Tracker",
    page_icon="🧍",
    layout="wide"
)

st.title("🧍 Full Body 3D Tracking App")
st.caption("Cloud-safe version: no OpenCV, no Python MediaPipe, no heavy installer dependencies.")

st.warning(
    "This version uses browser-based MediaPipe Pose through JavaScript. "
    "It avoids Streamlit Cloud installer errors caused by cv2 / OpenCV / Python MediaPipe."
)

html_code = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Full Body 3D Tracker</title>

  <script src="https://cdn.jsdelivr.net/npm/@mediapipe/pose/pose.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js"></script>
  <script src="https://cdn.plot.ly/plotly-2.30.0.min.js"></script>

  <style>
    body {
      font-family: Arial, sans-serif;
      margin: 0;
      background: #f8fafc;
      color: #111827;
    }
    .container {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
      padding: 18px;
    }
    .card {
      background: white;
      border-radius: 18px;
      padding: 16px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.08);
    }
    video, canvas {
      width: 100%;
      border-radius: 14px;
      background: #111827;
    }
    button {
      background: #111827;
      color: white;
      border: none;
      padding: 12px 18px;
      margin: 6px;
      border-radius: 10px;
      cursor: pointer;
      font-weight: bold;
    }
    button:hover {
      background: #374151;
    }
    #plot3d {
      height: 540px;
    }
    .status {
      font-weight: bold;
      color: #065f46;
    }
    table {
      border-collapse: collapse;
      width: 100%;
      font-size: 12px;
    }
    th, td {
      border: 1px solid #e5e7eb;
      padding: 5px;
      text-align: left;
    }
    th {
      background: #f3f4f6;
    }
    .note {
      font-size: 13px;
      color: #374151;
      line-height: 1.5;
    }
  </style>
</head>

<body>
  <div class="container">
    <div class="card">
      <h2>Camera View</h2>
      <video class="input_video" style="display:none;"></video>
      <canvas class="output_canvas" width="640" height="480"></canvas>
      <p class="status" id="status">Camera not started.</p>

      <button onclick="startCamera()">Start Camera</button>
      <button onclick="stopCamera()">Stop Camera</button>
      <button onclick="downloadCSV()">Download Landmark CSV</button>
      <button onclick="clearData()">Clear Data</button>

      <p class="note">
        For best results, stand far enough from the camera so your whole body is visible.
        Use good lighting and a plain background.
      </p>
    </div>

    <div class="card">
      <h2>3D Pose Landmarks</h2>
      <div id="plot3d"></div>
    </div>

    <div class="card">
      <h2>Joint Angles</h2>
      <table>
        <thead>
          <tr>
            <th>Joint</th>
            <th>Angle</th>
          </tr>
        </thead>
        <tbody id="anglesTable">
          <tr><td colspan="2">No pose detected yet.</td></tr>
        </tbody>
      </table>
    </div>

    <div class="card">
      <h2>Research Notes</h2>
      <p class="note">
        This app detects 33 body landmarks using MediaPipe Pose in the browser.
        The 3D coordinates are model-estimated relative coordinates, not calibrated laboratory motion-capture measurements.
      </p>
      <p class="note">
        Suitable for classroom research, exploratory movement analysis, posture observation,
        sports technique review, and prototype data collection.
      </p>
      <p class="note">
        Not suitable as a medical diagnostic tool or as a replacement for calibrated systems such as Vicon or Qualisys.
      </p>
    </div>
  </div>

<script>
const videoElement = document.getElementsByClassName('input_video')[0];
const canvasElement = document.getElementsByClassName('output_canvas')[0];
const canvasCtx = canvasElement.getContext('2d');
let camera = null;
let frameNumber = 0;
let landmarkRows = [];

const POSE_CONNECTIONS = [
  [0,1],[1,2],[2,3],[3,7],[0,4],[4,5],[5,6],[6,8],
  [9,10],[11,12],[11,13],[13,15],[15,17],[15,19],[15,21],[17,19],
  [12,14],[14,16],[16,18],[16,20],[16,22],[18,20],
  [11,23],[12,24],[23,24],[23,25],[24,26],[25,27],[26,28],
  [27,29],[28,30],[29,31],[30,32],[27,31],[28,32]
];

const LANDMARK_NAMES = [
  "NOSE","LEFT_EYE_INNER","LEFT_EYE","LEFT_EYE_OUTER",
  "RIGHT_EYE_INNER","RIGHT_EYE","RIGHT_EYE_OUTER",
  "LEFT_EAR","RIGHT_EAR","MOUTH_LEFT","MOUTH_RIGHT",
  "LEFT_SHOULDER","RIGHT_SHOULDER","LEFT_ELBOW","RIGHT_ELBOW",
  "LEFT_WRIST","RIGHT_WRIST","LEFT_PINKY","RIGHT_PINKY",
  "LEFT_INDEX","RIGHT_INDEX","LEFT_THUMB","RIGHT_THUMB",
  "LEFT_HIP","RIGHT_HIP","LEFT_KNEE","RIGHT_KNEE",
  "LEFT_ANKLE","RIGHT_ANKLE","LEFT_HEEL","RIGHT_HEEL",
  "LEFT_FOOT_INDEX","RIGHT_FOOT_INDEX"
];

function calculateAngle(a, b, c) {
  const ab = [a.x - b.x, a.y - b.y];
  const cb = [c.x - b.x, c.y - b.y];

  const dot = ab[0]*cb[0] + ab[1]*cb[1];
  const magAB = Math.sqrt(ab[0]*ab[0] + ab[1]*ab[1]);
  const magCB = Math.sqrt(cb[0]*cb[0] + cb[1]*cb[1]);

  let cosine = dot / ((magAB * magCB) + 1e-9);
  cosine = Math.max(-1, Math.min(1, cosine));

  return Math.acos(cosine) * 180 / Math.PI;
}

function updateAngles(landmarks) {
  const defs = {
    "Left Elbow": [11, 13, 15],
    "Right Elbow": [12, 14, 16],
    "Left Shoulder": [13, 11, 23],
    "Right Shoulder": [14, 12, 24],
    "Left Hip": [11, 23, 25],
    "Right Hip": [12, 24, 26],
    "Left Knee": [23, 25, 27],
    "Right Knee": [24, 26, 28]
  };

  let rows = "";
  for (const [name, ids] of Object.entries(defs)) {
    const angle = calculateAngle(landmarks[ids[0]], landmarks[ids[1]], landmarks[ids[2]]);
    rows += `<tr><td>${name}</td><td>${angle.toFixed(1)}°</td></tr>`;
  }

  document.getElementById("anglesTable").innerHTML = rows;
}

function update3DPlot(landmarks) {
  const xs = landmarks.map(l => l.x);
  const ys = landmarks.map(l => -l.y);
  const zs = landmarks.map(l => -l.z);
  const labels = LANDMARK_NAMES;

  const traces = [{
    x: xs,
    y: ys,
    z: zs,
    text: labels,
    mode: "markers+text",
    type: "scatter3d",
    marker: { size: 4 },
    textposition: "top center",
    name: "Landmarks"
  }];

  POSE_CONNECTIONS.forEach(conn => {
    traces.push({
      x: [xs[conn[0]], xs[conn[1]]],
      y: [ys[conn[0]], ys[conn[1]]],
      z: [zs[conn[0]], zs[conn[1]]],
      mode: "lines",
      type: "scatter3d",
      showlegend: false
    });
  });

  const layout = {
    margin: {l:0, r:0, b:0, t:0},
    scene: {
      xaxis: {title: "X"},
      yaxis: {title: "Y"},
      zaxis: {title: "Z"},
      aspectmode: "cube"
    }
  };

  Plotly.react("plot3d", traces, layout);
}

function saveLandmarks(landmarks) {
  const timestamp = Date.now() / 1000;

  landmarks.forEach((lm, i) => {
    landmarkRows.push({
      frame: frameNumber,
      timestamp_sec: timestamp,
      landmark_id: i,
      landmark_name: LANDMARK_NAMES[i],
      x: lm.x,
      y: lm.y,
      z: lm.z,
      visibility: lm.visibility
    });
  });

  frameNumber++;
}

function onResults(results) {
  canvasCtx.save();
  canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);

  canvasCtx.drawImage(results.image, 0, 0, canvasElement.width, canvasElement.height);

  if (results.poseLandmarks) {
    drawConnectors(canvasCtx, results.poseLandmarks, POSE_CONNECTIONS,
      {color: '#00FF00', lineWidth: 3});
    drawLandmarks(canvasCtx, results.poseLandmarks,
      {color: '#FF0000', lineWidth: 2});

    update3DPlot(results.poseLandmarks);
    updateAngles(results.poseLandmarks);
    saveLandmarks(results.poseLandmarks);

    document.getElementById("status").innerText =
      "Pose detected. Frames recorded: " + frameNumber;
  } else {
    document.getElementById("status").innerText =
      "No full-body pose detected. Move back or improve lighting.";
  }

  canvasCtx.restore();
}

const pose = new Pose({
  locateFile: (file) => {
    return `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`;
  }
});

pose.setOptions({
  modelComplexity: 1,
  smoothLandmarks: true,
  enableSegmentation: false,
  smoothSegmentation: false,
  minDetectionConfidence: 0.5,
  minTrackingConfidence: 0.5
});

pose.onResults(onResults);

function startCamera() {
  camera = new Camera(videoElement, {
    onFrame: async () => {
      await pose.send({image: videoElement});
    },
    width: 640,
    height: 480
  });

  camera.start();
  document.getElementById("status").innerText = "Camera started. Please allow browser camera permission.";
}

function stopCamera() {
  if (camera) {
    camera.stop();
    document.getElementById("status").innerText = "Camera stopped.";
  }
}

function clearData() {
  frameNumber = 0;
  landmarkRows = [];
  document.getElementById("status").innerText = "Data cleared.";
}

function downloadCSV() {
  if (landmarkRows.length === 0) {
    alert("No landmark data to download yet.");
    return;
  }

  const headers = Object.keys(landmarkRows[0]);
  const csv = [
    headers.join(","),
    ...landmarkRows.map(row => headers.map(h => row[h]).join(","))
  ].join("\\n");

  const blob = new Blob([csv], {type: "text/csv"});
  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = "full_body_3d_landmarks.csv";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}
</script>
</body>
</html>
"""

components.html(html_code, height=1300, scrolling=True)

st.divider()

st.subheader("Why this version fixes the installer error")
st.markdown(
    """
The previous versions failed because Streamlit Cloud had to install heavy packages:

- `opencv-python-headless`
- `mediapipe`
- `cv2`

This version avoids those packages completely. The body tracking runs inside the browser using MediaPipe JavaScript.
"""
)

st.subheader("Current capability")
st.markdown(
    """
✅ Full-body tracking  
✅ 33 body landmarks  
✅ 3D skeleton visualisation  
✅ Major joint angles  
✅ CSV download  
✅ Works on Streamlit Cloud with minimal dependencies  
✅ Uses phone/laptop camera through browser permission  
"""
)

st.subheader("Research limitation")
st.info(
    "This is suitable for exploratory or classroom-based research. "
    "For true research-grade motion capture, you need calibrated multi-camera systems. "
    "This app gives reproducible model-estimated landmarks, not laboratory-calibrated coordinates."
)

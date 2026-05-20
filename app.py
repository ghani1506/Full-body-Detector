import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Full Body 3D Tracker",
    page_icon="🧍",
    layout="wide"
)

st.title("🧍 Full Body 3D Tracking App")
st.caption("Clean deploy version: Streamlit only. No OpenCV. No Python MediaPipe. No runtime.txt.")

st.info(
    "Click Start Camera below. The tracking runs in your browser using MediaPipe JavaScript, "
    "so Streamlit Cloud does not need to install heavy computer-vision packages."
)

html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">

<script src="https://cdn.jsdelivr.net/npm/@mediapipe/pose/pose.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js"></script>
<script src="https://cdn.plot.ly/plotly-2.30.0.min.js"></script>

<style>
body { font-family: Arial, sans-serif; background:#f8fafc; margin:0; }
.grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; padding:16px; }
.card { background:white; border-radius:16px; padding:16px; box-shadow:0 6px 18px rgba(0,0,0,.08); }
canvas { width:100%; border-radius:12px; background:#111827; }
button { padding:12px 16px; border:0; border-radius:10px; background:#111827; color:white; font-weight:bold; margin:4px; }
#plot3d { height:520px; }
table { width:100%; border-collapse:collapse; font-size:13px; }
td, th { border:1px solid #ddd; padding:6px; }
th { background:#f3f4f6; }
</style>
</head>

<body>
<div class="grid">
  <div class="card">
    <h2>Camera Tracking</h2>
    <video class="input_video" style="display:none;"></video>
    <canvas class="output_canvas" width="640" height="480"></canvas>
    <p id="status"><b>Status:</b> Camera not started.</p>
    <button onclick="startCamera()">Start Camera</button>
    <button onclick="stopCamera()">Stop Camera</button>
    <button onclick="downloadCSV()">Download CSV</button>
    <button onclick="clearData()">Clear Data</button>
  </div>

  <div class="card">
    <h2>3D Skeleton</h2>
    <div id="plot3d"></div>
  </div>

  <div class="card">
    <h2>Joint Angles</h2>
    <table>
      <thead><tr><th>Joint</th><th>Angle</th></tr></thead>
      <tbody id="angles"><tr><td colspan="2">No pose detected yet.</td></tr></tbody>
    </table>
  </div>

  <div class="card">
    <h2>Research Notes</h2>
    <p>This app estimates 33 full-body landmarks using browser MediaPipe Pose.</p>
    <p>The 3D coordinates are relative model estimates, not calibrated laboratory motion-capture coordinates.</p>
    <p>Suitable for exploratory research, classroom research, prototype movement analysis, and CSV-based follow-up analysis.</p>
  </div>
</div>

<script>
const videoElement = document.getElementsByClassName("input_video")[0];
const canvasElement = document.getElementsByClassName("output_canvas")[0];
const canvasCtx = canvasElement.getContext("2d");

let camera = null;
let frame = 0;
let rows = [];

const names = [
"NOSE","LEFT_EYE_INNER","LEFT_EYE","LEFT_EYE_OUTER","RIGHT_EYE_INNER","RIGHT_EYE","RIGHT_EYE_OUTER",
"LEFT_EAR","RIGHT_EAR","MOUTH_LEFT","MOUTH_RIGHT","LEFT_SHOULDER","RIGHT_SHOULDER","LEFT_ELBOW","RIGHT_ELBOW",
"LEFT_WRIST","RIGHT_WRIST","LEFT_PINKY","RIGHT_PINKY","LEFT_INDEX","RIGHT_INDEX","LEFT_THUMB","RIGHT_THUMB",
"LEFT_HIP","RIGHT_HIP","LEFT_KNEE","RIGHT_KNEE","LEFT_ANKLE","RIGHT_ANKLE","LEFT_HEEL","RIGHT_HEEL",
"LEFT_FOOT_INDEX","RIGHT_FOOT_INDEX"
];

const connections = [
[0,1],[1,2],[2,3],[3,7],[0,4],[4,5],[5,6],[6,8],[9,10],
[11,12],[11,13],[13,15],[15,17],[15,19],[15,21],[17,19],
[12,14],[14,16],[16,18],[16,20],[16,22],[18,20],
[11,23],[12,24],[23,24],[23,25],[24,26],[25,27],[26,28],
[27,29],[28,30],[29,31],[30,32],[27,31],[28,32]
];

function angle(a,b,c){
  const ab=[a.x-b.x,a.y-b.y], cb=[c.x-b.x,c.y-b.y];
  const dot=ab[0]*cb[0]+ab[1]*cb[1];
  const mag1=Math.sqrt(ab[0]**2+ab[1]**2), mag2=Math.sqrt(cb[0]**2+cb[1]**2);
  let cos=dot/((mag1*mag2)+1e-9);
  cos=Math.max(-1,Math.min(1,cos));
  return Math.acos(cos)*180/Math.PI;
}

function updateAngles(lm){
  const defs = {
    "Left Elbow":[11,13,15],
    "Right Elbow":[12,14,16],
    "Left Shoulder":[13,11,23],
    "Right Shoulder":[14,12,24],
    "Left Hip":[11,23,25],
    "Right Hip":[12,24,26],
    "Left Knee":[23,25,27],
    "Right Knee":[24,26,28]
  };
  let html="";
  for(const [k,v] of Object.entries(defs)){
    html += `<tr><td>${k}</td><td>${angle(lm[v[0]],lm[v[1]],lm[v[2]]).toFixed(1)}°</td></tr>`;
  }
  document.getElementById("angles").innerHTML = html;
}

function update3D(lm){
  const xs=lm.map(p=>p.x), ys=lm.map(p=>-p.y), zs=lm.map(p=>-p.z);
  const traces=[{
    x:xs,y:ys,z:zs,text:names,mode:"markers+text",type:"scatter3d",
    marker:{size:4}, textposition:"top center", name:"Landmarks"
  }];
  connections.forEach(c=>{
    traces.push({x:[xs[c[0]],xs[c[1]]],y:[ys[c[0]],ys[c[1]]],z:[zs[c[0]],zs[c[1]]],
      mode:"lines",type:"scatter3d",showlegend:false});
  });
  Plotly.react("plot3d", traces, {margin:{l:0,r:0,b:0,t:0}, scene:{aspectmode:"cube"}});
}

function saveRows(lm){
  const t = Date.now()/1000;
  lm.forEach((p,i)=>{
    rows.push({frame:frame,timestamp_sec:t,landmark_id:i,landmark_name:names[i],x:p.x,y:p.y,z:p.z,visibility:p.visibility});
  });
  frame++;
}

function onResults(results){
  canvasCtx.save();
  canvasCtx.clearRect(0,0,canvasElement.width,canvasElement.height);
  canvasCtx.drawImage(results.image,0,0,canvasElement.width,canvasElement.height);

  if(results.poseLandmarks){
    drawConnectors(canvasCtx, results.poseLandmarks, connections, {color:"#00FF00", lineWidth:3});
    drawLandmarks(canvasCtx, results.poseLandmarks, {color:"#FF0000", lineWidth:2});
    updateAngles(results.poseLandmarks);
    update3D(results.poseLandmarks);
    saveRows(results.poseLandmarks);
    document.getElementById("status").innerHTML = "<b>Status:</b> Pose detected. Frames recorded: " + frame;
  } else {
    document.getElementById("status").innerHTML = "<b>Status:</b> No pose detected. Move further back.";
  }
  canvasCtx.restore();
}

const pose = new Pose({locateFile:(file)=>`https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`});
pose.setOptions({modelComplexity:1,smoothLandmarks:true,enableSegmentation:false,minDetectionConfidence:0.5,minTrackingConfidence:0.5});
pose.onResults(onResults);

function startCamera(){
  camera = new Camera(videoElement, {
    onFrame: async()=>{ await pose.send({image:videoElement}); },
    width:640,
    height:480
  });
  camera.start();
  document.getElementById("status").innerHTML = "<b>Status:</b> Camera starting. Allow permission.";
}

function stopCamera(){
  if(camera){ camera.stop(); }
  document.getElementById("status").innerHTML = "<b>Status:</b> Camera stopped.";
}

function clearData(){
  rows=[]; frame=0;
  document.getElementById("status").innerHTML = "<b>Status:</b> Data cleared.";
}

function downloadCSV(){
  if(rows.length===0){ alert("No data yet."); return; }
  const headers = Object.keys(rows[0]);
  const csv = [headers.join(","), ...rows.map(r=>headers.map(h=>r[h]).join(","))].join("\\n");
  const blob = new Blob([csv], {type:"text/csv"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href=url; a.download="full_body_3d_landmarks.csv"; a.click();
}
</script>
</body>
</html>
"""

components.html(html, height=1250, scrolling=True)

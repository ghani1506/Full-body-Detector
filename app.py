import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Expert Full Body 3D Skeleton Tracker",
    page_icon="🧍",
    layout="wide"
)

st.title("🧍 Expert Full Body 3D Cartoon Avatar Tracker")
st.caption("Cloud-safe expert version with 3D-style cartoon avatar, detailed pose estimation, biomechanics, and CSV export.")

st.info(
    "This version still avoids cv2/OpenCV/Python MediaPipe installer errors. "
    "It uses browser-based MediaPipe Pose with higher accuracy settings and advanced biomechanical outputs."
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
body { font-family: Arial, sans-serif; background:#f8fafc; margin:0; color:#111827; }
.grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; padding:16px; }
.card { background:white; border-radius:18px; padding:16px; box-shadow:0 8px 24px rgba(0,0,0,.08); }
canvas { width:100%; border-radius:14px; background:#111827; }
button, select, input { padding:10px 14px; border-radius:10px; margin:4px; }
button { border:0; background:#111827; color:white; font-weight:bold; cursor:pointer; }
button:hover { background:#374151; }
#plot3d { height:560px; }
table { width:100%; border-collapse:collapse; font-size:12px; }
td, th { border:1px solid #ddd; padding:6px; }
th { background:#f3f4f6; }
.metricBox { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; }
.metric { background:#f3f4f6; border-radius:12px; padding:10px; }
.metric b { display:block; font-size:12px; color:#374151; }
.metric span { font-size:20px; font-weight:bold; }
.small { font-size:13px; color:#374151; line-height:1.5; }
.warning { background:#fff7ed; border-left:5px solid #f97316; padding:10px; border-radius:10px; }
</style>
</head>

<body>
<div class="grid">

  <div class="card">
    <h2>Camera Tracking + 3D Cartoon Avatar</h2>
    <video class="input_video" style="display:none;"></video>
    <canvas class="output_canvas" width="960" height="720"></canvas>

    <p id="status"><b>Status:</b> Camera not started.</p>

    <button onclick="startCamera()">Start Camera</button>
    <button onclick="stopCamera()">Stop Camera</button>
    <button onclick="downloadLandmarkCSV()">Download Landmark CSV</button>
    <button onclick="downloadAngleCSV()">Download Angle CSV</button>
    <button onclick="clearData()">Clear Data</button>

    <h3>Expert Settings</h3>
    <label>Model complexity:</label>
    <select id="complexity">
      <option value="0">Lite / faster</option>
      <option value="1">Full / balanced</option>
      <option value="2" selected>Heavy / most detailed</option>
    </select>

    <label>Minimum visibility:</label>
    <input id="visibilityThreshold" type="number" min="0" max="1" step="0.05" value="0.60">

    <label>Smoothing strength:</label>
    <input id="smoothStrength" type="number" min="0" max="0.95" step="0.05" value="0.70">

    <p class="small">
      Higher model complexity and smoothing give steadier skeletons but may run slower on older phones.
    </p>
  </div>

  <div class="card">
    <h2>3D Skeleton Reconstruction</h2>
    <div id="plot3d"></div>
  </div>

  <div class="card">
    <h2>Tracking Quality</h2>
    <div class="metricBox">
      <div class="metric"><b>Frames Recorded</b><span id="mFrames">0</span></div>
      <div class="metric"><b>Mean Visibility</b><span id="mVisibility">0%</span></div>
      <div class="metric"><b>Pose Quality</b><span id="mQuality">-</span></div>
      <div class="metric"><b>Shoulder Tilt</b><span id="mShoulderTilt">0°</span></div>
      <div class="metric"><b>Hip Tilt</b><span id="mHipTilt">0°</span></div>
      <div class="metric"><b>Body Lean</b><span id="mLean">0°</span></div>
    </div>

    <h3>Joint Angles</h3>
    <table>
      <thead><tr><th>Joint / Segment</th><th>Angle</th><th>Interpretation</th></tr></thead>
      <tbody id="angles"><tr><td colspan="3">No pose detected yet.</td></tr></tbody>
    </table>
  </div>

  <div class="card">
    <h2>Biomechanical Measurements</h2>
    <table>
      <thead><tr><th>Measurement</th><th>Value</th></tr></thead>
      <tbody id="measurements"><tr><td colspan="2">No pose detected yet.</td></tr></tbody>
    </table>

    <div class="warning">
      <b>Accuracy note:</b> This is more detailed and more stable, but it is still not true laboratory-grade motion capture.
      A single normal camera cannot perfectly predict real bone length, true depth, or hidden joints.
    </div>
  </div>

</div>

<script>
const videoElement = document.getElementsByClassName("input_video")[0];
const canvasElement = document.getElementsByClassName("output_canvas")[0];
const canvasCtx = canvasElement.getContext("2d");

let camera = null;
let pose = null;
let frame = 0;
let landmarkRows = [];
let angleRows = [];
let smoothedLandmarks = null;

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

const expertConnections = [
[11,12],[23,24],[11,23],[12,24],
[0,11],[0,12],[11,13],[13,15],[12,14],[14,16],
[23,25],[25,27],[24,26],[26,28],
[27,31],[28,32]
];

function cloneLandmarks(lm){
  return lm.map(p => ({x:p.x, y:p.y, z:p.z, visibility:p.visibility ?? 0}));
}

function smooth(lm){
  const alpha = parseFloat(document.getElementById("smoothStrength").value);
  if(!smoothedLandmarks){
    smoothedLandmarks = cloneLandmarks(lm);
    return smoothedLandmarks;
  }
  for(let i=0;i<lm.length;i++){
    smoothedLandmarks[i].x = alpha*smoothedLandmarks[i].x + (1-alpha)*lm[i].x;
    smoothedLandmarks[i].y = alpha*smoothedLandmarks[i].y + (1-alpha)*lm[i].y;
    smoothedLandmarks[i].z = alpha*smoothedLandmarks[i].z + (1-alpha)*lm[i].z;
    smoothedLandmarks[i].visibility = lm[i].visibility ?? smoothedLandmarks[i].visibility;
  }
  return smoothedLandmarks;
}

function dist2D(a,b){
  return Math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2);
}

function dist3D(a,b){
  return Math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2 + (a.z-b.z)**2);
}

function angle2D(a,b,c){
  const ab=[a.x-b.x,a.y-b.y], cb=[c.x-b.x,c.y-b.y];
  const dot=ab[0]*cb[0]+ab[1]*cb[1];
  const mag1=Math.sqrt(ab[0]**2+ab[1]**2), mag2=Math.sqrt(cb[0]**2+cb[1]**2);
  let cos=dot/((mag1*mag2)+1e-9);
  cos=Math.max(-1,Math.min(1,cos));
  return Math.acos(cos)*180/Math.PI;
}

function angle3D(a,b,c){
  const ab=[a.x-b.x,a.y-b.y,a.z-b.z], cb=[c.x-b.x,c.y-b.y,c.z-b.z];
  const dot=ab[0]*cb[0]+ab[1]*cb[1]+ab[2]*cb[2];
  const mag1=Math.sqrt(ab[0]**2+ab[1]**2+ab[2]**2), mag2=Math.sqrt(cb[0]**2+cb[1]**2+cb[2]**2);
  let cos=dot/((mag1*mag2)+1e-9);
  cos=Math.max(-1,Math.min(1,cos));
  return Math.acos(cos)*180/Math.PI;
}

function segmentTilt(a,b){
  return Math.atan2((b.y-a.y),(b.x-a.x))*180/Math.PI;
}

function meanVisibility(lm){
  return lm.reduce((s,p)=>s+(p.visibility ?? 0),0)/lm.length;
}

function qualityLabel(v){
  if(v >= 0.80) return "Excellent";
  if(v >= 0.65) return "Good";
  if(v >= 0.50) return "Fair";
  return "Poor";
}

function angleInterpretation(name, val){
  if(name.includes("Knee") && val < 120) return "Flexed";
  if(name.includes("Knee") && val >= 160) return "Extended";
  if(name.includes("Elbow") && val < 110) return "Flexed";
  if(name.includes("Elbow") && val >= 155) return "Extended";
  if(name.includes("Shoulder") && val > 90) return "Raised / open";
  if(name.includes("Hip") && val < 130) return "Flexed";
  return "Neutral / observe trend";
}

function computeAngles(lm){
  const defs = {
    "Left Elbow 2D":[11,13,15,"2D"],
    "Right Elbow 2D":[12,14,16,"2D"],
    "Left Elbow 3D":[11,13,15,"3D"],
    "Right Elbow 3D":[12,14,16,"3D"],
    "Left Shoulder 2D":[13,11,23,"2D"],
    "Right Shoulder 2D":[14,12,24,"2D"],
    "Left Hip 2D":[11,23,25,"2D"],
    "Right Hip 2D":[12,24,26,"2D"],
    "Left Knee 2D":[23,25,27,"2D"],
    "Right Knee 2D":[24,26,28,"2D"],
    "Left Knee 3D":[23,25,27,"3D"],
    "Right Knee 3D":[24,26,28,"3D"],
    "Left Ankle 2D":[25,27,31,"2D"],
    "Right Ankle 2D":[26,28,32,"2D"]
  };

  let html = "";
  let out = {frame:frame, timestamp_sec:Date.now()/1000};

  for(const [name, d] of Object.entries(defs)){
    const val = d[3] === "3D"
      ? angle3D(lm[d[0]], lm[d[1]], lm[d[2]])
      : angle2D(lm[d[0]], lm[d[1]], lm[d[2]]);

    out[name.replaceAll(" ","_").toLowerCase()] = val;
    html += `<tr><td>${name}</td><td>${val.toFixed(1)}°</td><td>${angleInterpretation(name,val)}</td></tr>`;
  }

  const shoulderTilt = Math.abs(segmentTilt(lm[11], lm[12]));
  const hipTilt = Math.abs(segmentTilt(lm[23], lm[24]));
  const midShoulder = {x:(lm[11].x+lm[12].x)/2, y:(lm[11].y+lm[12].y)/2, z:(lm[11].z+lm[12].z)/2};
  const midHip = {x:(lm[23].x+lm[24].x)/2, y:(lm[23].y+lm[24].y)/2, z:(lm[23].z+lm[24].z)/2};
  const bodyLean = Math.abs(Math.atan2(midShoulder.x-midHip.x, midHip.y-midShoulder.y)*180/Math.PI);

  out.shoulder_tilt = shoulderTilt;
  out.hip_tilt = hipTilt;
  out.body_lean = bodyLean;

  document.getElementById("angles").innerHTML = html;
  document.getElementById("mShoulderTilt").innerText = shoulderTilt.toFixed(1)+"°";
  document.getElementById("mHipTilt").innerText = hipTilt.toFixed(1)+"°";
  document.getElementById("mLean").innerText = bodyLean.toFixed(1)+"°";

  return out;
}

function computeMeasurements(lm){
  const shoulderWidth = dist3D(lm[11],lm[12]);
  const hipWidth = dist3D(lm[23],lm[24]);
  const torsoLength = dist3D(
    {x:(lm[11].x+lm[12].x)/2,y:(lm[11].y+lm[12].y)/2,z:(lm[11].z+lm[12].z)/2},
    {x:(lm[23].x+lm[24].x)/2,y:(lm[23].y+lm[24].y)/2,z:(lm[23].z+lm[24].z)/2}
  );

  const leftUpperArm = dist3D(lm[11],lm[13]);
  const rightUpperArm = dist3D(lm[12],lm[14]);
  const leftForearm = dist3D(lm[13],lm[15]);
  const rightForearm = dist3D(lm[14],lm[16]);
  const leftThigh = dist3D(lm[23],lm[25]);
  const rightThigh = dist3D(lm[24],lm[26]);
  const leftShin = dist3D(lm[25],lm[27]);
  const rightShin = dist3D(lm[26],lm[28]);

  const armSym = Math.abs((leftUpperArm+leftForearm) - (rightUpperArm+rightForearm));
  const legSym = Math.abs((leftThigh+leftShin) - (rightThigh+rightShin));

  const rows = {
    "Shoulder width, relative": shoulderWidth,
    "Hip width, relative": hipWidth,
    "Torso length, relative": torsoLength,
    "Left upper arm, relative": leftUpperArm,
    "Right upper arm, relative": rightUpperArm,
    "Left forearm, relative": leftForearm,
    "Right forearm, relative": rightForearm,
    "Left thigh, relative": leftThigh,
    "Right thigh, relative": rightThigh,
    "Left shin, relative": leftShin,
    "Right shin, relative": rightShin,
    "Arm symmetry difference": armSym,
    "Leg symmetry difference": legSym
  };

  let html = "";
  for(const [k,v] of Object.entries(rows)){
    html += `<tr><td>${k}</td><td>${v.toFixed(4)}</td></tr>`;
  }

  document.getElementById("measurements").innerHTML = html;
}

function update3D(lm){
  const xs=lm.map(p=>p.x), ys=lm.map(p=>-p.y), zs=lm.map(p=>-p.z);

  const visibilityThreshold = parseFloat(document.getElementById("visibilityThreshold").value);
  const colors = lm.map(p => (p.visibility ?? 0) >= visibilityThreshold ? "green" : "red");

  const traces=[{
    x:xs,y:ys,z:zs,text:names,mode:"markers+text",type:"scatter3d",
    marker:{size:5, color:colors},
    textposition:"top center",
    name:"Landmarks"
  }];

  connections.forEach(c=>{
    const avgVis = ((lm[c[0]].visibility ?? 0) + (lm[c[1]].visibility ?? 0))/2;
    traces.push({
      x:[xs[c[0]],xs[c[1]]],
      y:[ys[c[0]],ys[c[1]]],
      z:[zs[c[0]],zs[c[1]]],
      mode:"lines",
      type:"scatter3d",
      line:{width: avgVis >= visibilityThreshold ? 5 : 2},
      showlegend:false
    });
  });

  Plotly.react("plot3d", traces, {
    margin:{l:0,r:0,b:0,t:0},
    scene:{
      xaxis:{title:"X"},
      yaxis:{title:"Y"},
      zaxis:{title:"Estimated Z"},
      aspectmode:"cube"
    }
  });
}

function saveLandmarks(lm){
  const t = Date.now()/1000;
  lm.forEach((p,i)=>{
    landmarkRows.push({
      frame:frame,
      timestamp_sec:t,
      landmark_id:i,
      landmark_name:names[i],
      x:p.x,
      y:p.y,
      z:p.z,
      visibility:p.visibility ?? 0
    });
  });
}

function onResults(results){
  canvasCtx.save();
  canvasCtx.clearRect(0,0,canvasElement.width,canvasElement.height);
  canvasCtx.drawImage(results.image,0,0,canvasElement.width,canvasElement.height);

  if(results.poseLandmarks){
    const lm = smooth(results.poseLandmarks);
    const visibilityThreshold = parseFloat(document.getElementById("visibilityThreshold").value);
    const v = meanVisibility(lm);

    // ===== 3D-STYLE CARTOON AVATAR RENDERER =====
    // This replaces simple skeleton lines with a cartoon body drawn from detected landmarks.

    function px(p){ return {x:p.x*canvasElement.width, y:p.y*canvasElement.height}; }

    function thickLimb(a, b, color1, color2, width){
      const A = px(a), B = px(b);
      const grad = canvasCtx.createLinearGradient(A.x, A.y, B.x, B.y);
      grad.addColorStop(0, color1);
      grad.addColorStop(1, color2);
      canvasCtx.beginPath();
      canvasCtx.strokeStyle = grad;
      canvasCtx.lineWidth = width;
      canvasCtx.lineCap = "round";
      canvasCtx.moveTo(A.x, A.y);
      canvasCtx.lineTo(B.x, B.y);
      canvasCtx.stroke();

      // highlight line for pseudo-3D effect
      canvasCtx.beginPath();
      canvasCtx.strokeStyle = "rgba(255,255,255,0.35)";
      canvasCtx.lineWidth = Math.max(2, width * 0.18);
      canvasCtx.lineCap = "round";
      canvasCtx.moveTo(A.x - width*0.12, A.y - width*0.12);
      canvasCtx.lineTo(B.x - width*0.12, B.y - width*0.12);
      canvasCtx.stroke();
    }

    function drawJointBall(p, r, fill="#ffffff", outline="#111827"){
      const P = px(p);
      const grad = canvasCtx.createRadialGradient(P.x-r*0.35, P.y-r*0.35, r*0.2, P.x, P.y, r);
      grad.addColorStop(0, "#ffffff");
      grad.addColorStop(0.55, fill);
      grad.addColorStop(1, "#94a3b8");
      canvasCtx.beginPath();
      canvasCtx.fillStyle = grad;
      canvasCtx.arc(P.x, P.y, r, 0, Math.PI*2);
      canvasCtx.fill();
      canvasCtx.strokeStyle = outline;
      canvasCtx.lineWidth = 1.5;
      canvasCtx.stroke();
    }

    function drawCartoonTorso(){
      const LS = px(lm[11]), RS = px(lm[12]), LH = px(lm[23]), RH = px(lm[24]);
      const midShoulder = {x:(LS.x+RS.x)/2, y:(LS.y+RS.y)/2};
      const midHip = {x:(LH.x+RH.x)/2, y:(LH.y+RH.y)/2};

      canvasCtx.beginPath();
      canvasCtx.moveTo(LS.x, LS.y);
      canvasCtx.quadraticCurveTo(midShoulder.x, midShoulder.y-18, RS.x, RS.y);
      canvasCtx.lineTo(RH.x, RH.y);
      canvasCtx.quadraticCurveTo(midHip.x, midHip.y+20, LH.x, LH.y);
      canvasCtx.closePath();

      const grad = canvasCtx.createLinearGradient(midShoulder.x, midShoulder.y, midHip.x, midHip.y);
      grad.addColorStop(0, "#2563eb");
      grad.addColorStop(1, "#1e40af");
      canvasCtx.fillStyle = grad;
      canvasCtx.fill();

      canvasCtx.strokeStyle = "rgba(255,255,255,0.65)";
      canvasCtx.lineWidth = 3;
      canvasCtx.stroke();

      // shirt centre highlight
      canvasCtx.beginPath();
      canvasCtx.strokeStyle = "#38bdf8";
      canvasCtx.lineWidth = 8;
      canvasCtx.lineCap = "round";
      canvasCtx.moveTo(midShoulder.x, midShoulder.y+8);
      canvasCtx.lineTo(midHip.x, midHip.y-8);
      canvasCtx.stroke();
    }

    function drawCartoonHead(){
      const nose = px(lm[0]);
      const LS = px(lm[11]), RS = px(lm[12]);
      const shoulderWidth = Math.abs(LS.x - RS.x);
      const r = Math.max(18, Math.min(55, shoulderWidth * 0.23));
      const cx = nose.x;
      const cy = nose.y - r*0.75;

      // neck
      canvasCtx.beginPath();
      canvasCtx.fillStyle = "#f2b489";
      canvasCtx.roundRect(cx-r*0.25, cy+r*0.68, r*0.5, r*0.55, 8);
      canvasCtx.fill();

      // face
      const faceGrad = canvasCtx.createRadialGradient(cx-r*0.3, cy-r*0.35, r*0.25, cx, cy, r);
      faceGrad.addColorStop(0, "#ffe7cc");
      faceGrad.addColorStop(0.72, "#f4bd8f");
      faceGrad.addColorStop(1, "#d9956b");
      canvasCtx.beginPath();
      canvasCtx.fillStyle = faceGrad;
      canvasCtx.arc(cx, cy, r, 0, Math.PI*2);
      canvasCtx.fill();

      // hair
      canvasCtx.beginPath();
      canvasCtx.fillStyle = "#3b2416";
      canvasCtx.arc(cx, cy-r*0.48, r*0.82, Math.PI, Math.PI*2);
      canvasCtx.fill();

      for(let i=-2;i<=2;i++){
        canvasCtx.beginPath();
        canvasCtx.fillStyle = "#2a160d";
        canvasCtx.arc(cx+i*r*0.23, cy-r*0.82+Math.abs(i)*3, r*0.22, 0, Math.PI*2);
        canvasCtx.fill();
      }

      // eyes
      canvasCtx.fillStyle = "#111827";
      canvasCtx.beginPath();
      canvasCtx.arc(cx-r*0.32, cy-r*0.05, r*0.09, 0, Math.PI*2);
      canvasCtx.arc(cx+r*0.32, cy-r*0.05, r*0.09, 0, Math.PI*2);
      canvasCtx.fill();

      canvasCtx.fillStyle = "#ffffff";
      canvasCtx.beginPath();
      canvasCtx.arc(cx-r*0.35, cy-r*0.08, r*0.03, 0, Math.PI*2);
      canvasCtx.arc(cx+r*0.29, cy-r*0.08, r*0.03, 0, Math.PI*2);
      canvasCtx.fill();

      // smile
      canvasCtx.beginPath();
      canvasCtx.strokeStyle = "#7c2d12";
      canvasCtx.lineWidth = 2.5;
      canvasCtx.arc(cx, cy+r*0.18, r*0.28, 0.15*Math.PI, 0.85*Math.PI);
      canvasCtx.stroke();
    }

    function drawCartoonFeet(){
      function shoe(ankle, foot, flip=false){
        const A = px(ankle), F = px(foot);
        canvasCtx.beginPath();
        canvasCtx.fillStyle = "#111827";
        canvasCtx.ellipse(F.x, F.y+8, 26, 11, flip ? -0.25 : 0.25, 0, Math.PI*2);
        canvasCtx.fill();
        canvasCtx.strokeStyle = "#ffffff";
        canvasCtx.lineWidth = 2;
        canvasCtx.stroke();
      }
      shoe(lm[27], lm[31], false);
      shoe(lm[28], lm[32], true);
    }

    // Draw lower parts first, then upper parts, then head/joints
    thickLimb(lm[23], lm[25], "#16a34a", "#86efac", 24);
    thickLimb(lm[25], lm[27], "#22c55e", "#bbf7d0", 22);
    thickLimb(lm[24], lm[26], "#16a34a", "#86efac", 24);
    thickLimb(lm[26], lm[28], "#22c55e", "#bbf7d0", 22);

    drawCartoonFeet();
    drawCartoonTorso();

    thickLimb(lm[11], lm[13], "#f59e0b", "#fed7aa", 20);
    thickLimb(lm[13], lm[15], "#f97316", "#ffedd5", 18);
    thickLimb(lm[12], lm[14], "#f59e0b", "#fed7aa", 20);
    thickLimb(lm[14], lm[16], "#f97316", "#ffedd5", 18);

    drawCartoonHead();

    [11,12,13,14,15,16,23,24,25,26,27,28].forEach(i=>{
      drawJointBall(lm[i], 9, "#ffffff");
    });

    // Keep a thin expert overlay so the user still sees exact detected skeleton lines
    canvasCtx.strokeStyle = "rgba(0,255,90,0.65)";
    canvasCtx.lineWidth = 2;
    expertConnections.forEach(c => {
      const a = lm[c[0]], b = lm[c[1]];
      canvasCtx.beginPath();
      canvasCtx.moveTo(a.x*canvasElement.width, a.y*canvasElement.height);
      canvasCtx.lineTo(b.x*canvasElement.width, b.y*canvasElement.height);
      canvasCtx.stroke();
    });

    update3D(lm);
    computeMeasurements(lm);
    const angleRow = computeAngles(lm);
    angleRows.push(angleRow);
    saveLandmarks(lm);

    frame++;

    document.getElementById("mFrames").innerText = frame;
    document.getElementById("mVisibility").innerText = (v*100).toFixed(0)+"%";
    document.getElementById("mQuality").innerText = qualityLabel(v);
    document.getElementById("status").innerHTML =
      `<b>Status:</b> Pose detected. Quality: ${qualityLabel(v)}. Mean visibility: ${(v*100).toFixed(0)}%.`;

  } else {
    document.getElementById("status").innerHTML =
      "<b>Status:</b> No pose detected. Stand back, show the full body, and improve lighting.";
  }

  canvasCtx.restore();
}

function createPose(){
  pose = new Pose({
    locateFile:(file)=>`https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`
  });

  pose.setOptions({
    modelComplexity: parseInt(document.getElementById("complexity").value),
    smoothLandmarks: true,
    enableSegmentation: false,
    smoothSegmentation: false,
    minDetectionConfidence: 0.70,
    minTrackingConfidence: 0.70
  });

  pose.onResults(onResults);
}

function startCamera(){
  createPose();
  camera = new Camera(videoElement, {
    onFrame: async()=>{ await pose.send({image:videoElement}); },
    width:960,
    height:720
  });
  camera.start();
  document.getElementById("status").innerHTML = "<b>Status:</b> Camera starting. Allow permission.";
}

function stopCamera(){
  if(camera){ camera.stop(); }
  document.getElementById("status").innerHTML = "<b>Status:</b> Camera stopped.";
}

function clearData(){
  landmarkRows=[]; angleRows=[]; frame=0; smoothedLandmarks=null;
  document.getElementById("mFrames").innerText = "0";
  document.getElementById("mVisibility").innerText = "0%";
  document.getElementById("mQuality").innerText = "-";
  document.getElementById("status").innerHTML = "<b>Status:</b> Data cleared.";
}

function downloadCSV(rows, filename){
  if(rows.length===0){ alert("No data yet."); return; }
  const headers = Object.keys(rows[0]);
  const csv = [headers.join(","), ...rows.map(r=>headers.map(h=>r[h]).join(","))].join("\\n");
  const blob = new Blob([csv], {type:"text/csv"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href=url;
  a.download=filename;
  a.click();
}

function downloadLandmarkCSV(){
  downloadCSV(landmarkRows, "expert_full_body_3d_landmarks.csv");
}

function downloadAngleCSV(){
  downloadCSV(angleRows, "expert_joint_angles_and_posture.csv");
}
</script>
</body>
</html>
"""

components.html(html, height=1400, scrolling=True)

st.divider()

st.subheader("What has been upgraded")
st.markdown(
    """
- 3D-style cartoon avatar drawn directly on the detected body\n- Higher resolution camera canvas: **960 × 720**
- MediaPipe model complexity set to **2 / heavy**
- Stronger detection and tracking confidence: **0.70**
- Landmark smoothing to reduce shaking
- 2D and 3D angle estimates
- Shoulder tilt, hip tilt, and body lean
- Relative segment lengths for upper arm, forearm, thigh, shin, torso, shoulder width, and hip width
- Symmetry indicators
- Landmark visibility confidence
- Separate CSV files for landmarks and joint-angle/posture data
"""
)

st.warning(
    "Important: It is more detailed and more expert, but a single webcam cannot perfectly predict the real skeleton. "
    "For true real skeleton measurement, you need calibrated multi-camera motion capture or depth sensors."
)

// Construit une illustration Three.js légère d’un atelier mobile.
import * as THREE from 'three';

const mount = document.querySelector('#scene');
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(28, 1, 0.1, 100);
camera.position.set(5.4, 3.6, 8.2);
camera.lookAt(0, 0.8, 0);

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
mount.appendChild(renderer.domElement);

const palette = { ink: 0x18211f, orange: 0xee6b3b, green: 0x7d9b76, cream: 0xf3f1e9, metal: 0xd6d2c5 };
const group = new THREE.Group();
scene.add(group);

const mat = (color, roughness = 0.78) => new THREE.MeshStandardMaterial({ color, roughness, metalness: 0.05 });
const box = (size, position, material, radius = 0.08) => {
  const geometry = new THREE.BoxGeometry(...size);
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.set(...position);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  group.add(mesh);
  return mesh;
};

// Approximation stylisée d’un Nissan NV200 : caisse haute, cabine avancée,
// pare-brise incliné et détails utilitaires plutôt qu’un simple pavé.
const body = mat(palette.cream);
const trim = mat(palette.ink, 0.5);
const glass = new THREE.MeshStandardMaterial({ color: 0x263b42, roughness: 0.24, metalness: 0.18 });
const lamp = new THREE.MeshStandardMaterial({ color: 0xffc875, emissive: 0x5b3215, emissiveIntensity: 0.7 });

// Marquage de carrosserie : le nom reprend le traitement noir/orange du site.
const labelCanvas = document.createElement('canvas');
labelCanvas.width = 1200;
labelCanvas.height = 240;
const labelContext = labelCanvas.getContext('2d');
labelContext.clearRect(0, 0, labelCanvas.width, labelCanvas.height);
labelContext.textBaseline = 'middle';
labelContext.font = '700 92px Space Grotesk, Arial, sans-serif';
labelContext.fillStyle = '#18211f';
labelContext.fillText("L'Atelier", 34, 120);
const firstWidth = labelContext.measureText("L'Atelier").width;
labelContext.fillStyle = '#ee6b3b';
labelContext.fillText('Roulant', 50 + firstWidth, 120);
const labelTexture = new THREE.CanvasTexture(labelCanvas);
labelTexture.colorSpace = THREE.SRGBColorSpace;
const labelMaterial = new THREE.MeshBasicMaterial({ map: labelTexture, transparent: true, depthWrite: false });
const sideLabel = new THREE.Mesh(new THREE.PlaneGeometry(2.25, 0.45), labelMaterial);
sideLabel.position.set(0, 1.18, -1.085);
sideLabel.rotation.y = Math.PI;
sideLabel.renderOrder = 3;
group.add(sideLabel);

box([3.9, 1.45, 2.02], [0, 1.02, 0], body);
box([2.48, 1.12, 2.08], [0.65, 2.08, 0], body);
box([1.22, 0.7, 2.08], [-1.28, 1.88, 0], body);
box([0.18, 0.48, 2.12], [-1.9, 1.3, 0], trim);

// Pare-brise et vitres latérales de la cabine.
box([0.05, 0.68, 1.7], [-0.72, 2.28, 0], glass);
for (const z of [-1.045, 1.045]) {
  box([0.78, 0.54, 0.045], [-1.22, 2.18, z], glass);
  box([0.78, 0.42, 0.045], [0.02, 2.16, z], glass);
  box([0.05, 0.48, 0.05], [-0.78, 2.16, z * 1.01], trim);
}

// Portes coulissantes, pare-chocs, poignées et bande latérale.
for (const z of [-1.055, 1.055]) {
  box([1.72, 0.045, 0.035], [0.82, 1.34, z], trim);
  box([0.16, 0.035, 0.04], [0.48, 1.92, z * 1.01], trim);
  box([3.1, 0.1, 0.05], [0.25, 0.55, z * 1.01], mat(palette.green));
}
box([0.18, 0.34, 2.16], [-1.94, 0.72, 0], trim);
box([0.2, 0.3, 2.18], [1.95, 0.72, 0], trim);

// Calandre, phares et feux arrière, visibles dans la vue trois-quarts avant.
box([0.06, 0.42, 0.68], [-2.02, 1.12, -0.57], lamp);
box([0.06, 0.42, 0.68], [-2.02, 1.12, 0.57], lamp);
box([0.04, 0.28, 0.82], [-2.04, 0.86, 0], trim);
box([0.05, 0.35, 0.34], [1.98, 1.28, -0.8], lamp);
box([0.05, 0.35, 0.34], [1.98, 1.28, 0.8], lamp);

// Rétroviseurs extérieurs.
for (const z of [-1.2, 1.2]) {
  box([0.22, 0.18, 0.16], [-0.93, 1.94, z], trim);
}

for (const x of [-1.35, 1.35]) {
  for (const z of [-1.08, 1.08]) {
    const wheel = new THREE.Mesh(new THREE.CylinderGeometry(0.43, 0.43, 0.3, 32), trim);
    wheel.rotation.x = Math.PI / 2;
    wheel.position.set(x, 0.5, z);
    wheel.castShadow = true;
    group.add(wheel);
    const hub = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.16, 0.315, 24), mat(palette.metal));
    hub.rotation.x = Math.PI / 2;
    hub.position.set(x, 0.5, z);
    group.add(hub);
  }
}

// L’atelier reste visible à l’arrière : caisse à outils et panneau de service.
box([1.05, 0.58, 0.8], [1.2, 0.58, 0.22], mat(palette.green));
box([0.95, 0.04, 0.62], [1.2, 1.28, 0.65], mat(palette.orange));
box([0.12, 1.05, 0.12], [1.18, 1.35, 0.3], trim);

const floor = new THREE.Mesh(new THREE.CircleGeometry(5.2, 64), new THREE.MeshStandardMaterial({ color: 0xe5e1d6, roughness: 1 }));
floor.rotation.x = -Math.PI / 2; floor.position.y = 0.08; floor.receiveShadow = true; scene.add(floor);

scene.add(new THREE.HemisphereLight(0xfff9ed, 0x68746e, 2.1));
const key = new THREE.DirectionalLight(0xffeee0, 3.1);
key.position.set(-4, 7, 5); key.castShadow = true; key.shadow.mapSize.set(1024, 1024); scene.add(key);

const vehicleOrientation = Math.PI;
let targetRotation = 0.24;
let pointerRotation = 0.24;
mount.addEventListener('pointermove', (event) => {
  const rect = mount.getBoundingClientRect();
  targetRotation = 0.24 + ((event.clientX - rect.left) / rect.width - 0.5) * 0.35;
});
mount.addEventListener('pointerleave', () => { targetRotation = 0.24; });

function resize() {
  const width = mount.clientWidth;
  const height = Math.max(360, mount.clientHeight);
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}
window.addEventListener('resize', resize);
resize();

function animate(time) {
  pointerRotation += (targetRotation - pointerRotation) * 0.045;
  group.rotation.y = vehicleOrientation + pointerRotation + Math.sin(time * 0.00035) * 0.035;
  group.position.y = -0.35 + Math.sin(time * 0.0012) * 0.035;
  renderer.render(scene, camera);
  requestAnimationFrame(animate);
}
requestAnimationFrame(animate);
window.__ATELIER_ROULANT_READY = true;

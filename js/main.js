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

// Four wheels and a compact mobile workshop body.
box([3.7, 1.6, 2.05], [0, 1.05, 0], mat(palette.cream), 0.1);
box([3.25, 1.05, 2.12], [0, 1.86, 0], mat(palette.orange));
box([1.3, 0.7, 2.14], [-1.1, 2.45, 0], mat(palette.orange));
box([0.75, 0.7, 2.16], [1.15, 2.45, 0], mat(palette.ink));
box([1.65, 0.78, 0.05], [0.1, 2.05, 1.08], mat(palette.ink));
box([0.9, 0.58, 0.06], [-0.55, 2.1, 1.12], mat(palette.green));

for (const x of [-1.25, 1.25]) {
  for (const z of [-1.08, 1.08]) {
    const wheel = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.42, 0.28, 32), mat(palette.ink));
    wheel.rotation.x = Math.PI / 2;
    wheel.position.set(x, 0.52, z);
    wheel.castShadow = true;
    group.add(wheel);
  }
}

// A repair crate and a few tools communicate the service promise.
box([0.9, 0.55, 0.85], [1.1, 0.55, 0.25], mat(palette.green));
box([0.12, 1.05, 0.12], [1.1, 1.25, 0.25], mat(palette.orange));
const tool = new THREE.Mesh(new THREE.BoxGeometry(0.68, 0.12, 0.12), mat(palette.ink));
tool.position.set(-1.25, 2.35, 0.25); tool.rotation.z = -0.35; tool.castShadow = true; group.add(tool);

const floor = new THREE.Mesh(new THREE.CircleGeometry(5.2, 64), new THREE.MeshStandardMaterial({ color: 0xe5e1d6, roughness: 1 }));
floor.rotation.x = -Math.PI / 2; floor.position.y = 0.08; floor.receiveShadow = true; scene.add(floor);

scene.add(new THREE.HemisphereLight(0xfff9ed, 0x68746e, 2.1));
const key = new THREE.DirectionalLight(0xffeee0, 3.1);
key.position.set(-4, 7, 5); key.castShadow = true; key.shadow.mapSize.set(1024, 1024); scene.add(key);

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
  group.rotation.y = pointerRotation + Math.sin(time * 0.00035) * 0.035;
  group.position.y = Math.sin(time * 0.0012) * 0.035;
  renderer.render(scene, camera);
  requestAnimationFrame(animate);
}
requestAnimationFrame(animate);
window.__ATELIER_ROULANT_READY = true;

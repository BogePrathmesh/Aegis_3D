import React, { useRef, useEffect, useMemo } from 'react';
import * as THREE from 'three';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Environment } from '@react-three/drei';

// ─── Displaced surface mesh ───────────────────────────────────────────────────

function CrackedSurface({ depthMapUrl, year, healthColor }) {
  const meshRef = useRef();
  const matRef  = useRef();

  const { scene } = useThree();

  useEffect(() => {
    if (!depthMapUrl || !meshRef.current) return;

    const loader = new THREE.TextureLoader();

    loader.load(depthMapUrl, (tex) => {
      tex.wrapS = tex.wrapT = THREE.ClampToEdgeWrapping;
      if (matRef.current) {
        matRef.current.displacementMap = tex;
        matRef.current.needsUpdate = true;
      }
    });
  }, [depthMapUrl]);

  // Subtle idle animation
  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.x = -Math.PI / 4 + Math.sin(state.clock.elapsedTime * 0.15) * 0.01;
    }
  });

  const displacementScale = 0.5 + year * 0.35;

  // Health → mesh color
  const meshColor = useMemo(() => {
    const r = healthColor.r / 255, g = healthColor.g / 255, b = healthColor.b / 255;
    return new THREE.Color(r, g, b);
  }, [healthColor]);

  return (
    <mesh
      ref={meshRef}
      rotation={[-Math.PI / 4, 0, 0]}
      receiveShadow
      castShadow
    >
      <planeGeometry args={[8, 8, 256, 256]} />
      <meshStandardMaterial
        ref={matRef}
        color="#9aa0a8"
        displacementScale={displacementScale}
        roughness={0.88}
        metalness={0.05}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}

// ─── Scene lighting ───────────────────────────────────────────────────────────

function SceneLights({ year }) {
  const intensity = Math.max(0.3, 1 - year * 0.08);
  return (
    <>
      <ambientLight intensity={0.3} />
      <directionalLight
        position={[5, 8, 4]}
        intensity={intensity * 1.2}
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
      />
      <directionalLight
        position={[-4, 3, -2]}
        intensity={intensity * 0.4}
        color="#4080ff"
      />
      <pointLight
        position={[0, 6, 2]}
        intensity={intensity * 0.6}
        color="#ffffff"
      />
    </>
  );
}

// ─── Grid ground plane ────────────────────────────────────────────────────────

function GridGround() {
  return (
    <gridHelper
      args={[20, 30, '#1a2a4a', '#0d1528']}
      position={[0, -3.5, 0]}
    />
  );
}

// ─── Main 3D component ────────────────────────────────────────────────────────

export default function ThreeDView({ depthMapUrl, year, healthColor }) {
  const safeDM = depthMapUrl || null;

  return (
    <div className="three-canvas-container">
      <Canvas
        shadows
        camera={{ position: [0, 6, 8], fov: 45 }}
        gl={{ antialias: true }}
        style={{ background: 'transparent' }}
      >
        <color attach="background" args={['#050810']} />
        <fog attach="fog" args={['#050810', 14, 28]} />

        <SceneLights year={year} />
        <GridGround />

        <CrackedSurface
          depthMapUrl={safeDM}
          year={year}
          healthColor={healthColor}
        />

        <OrbitControls
          enableDamping
          dampingFactor={0.08}
          minDistance={4}
          maxDistance={18}
          maxPolarAngle={Math.PI / 1.8}
          autoRotate
          autoRotateSpeed={0.4}
        />
      </Canvas>
    </div>
  );
}

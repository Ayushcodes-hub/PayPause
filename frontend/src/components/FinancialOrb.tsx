import { Suspense, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float, Sparkles } from '@react-three/drei'
import * as THREE from 'three'

function EnergyCore() {
  const core = useRef<THREE.Mesh>(null!)
  const ringA = useRef<THREE.Mesh>(null!)
  const ringB = useRef<THREE.Mesh>(null!)

  useFrame((state, delta) => {
    core.current.rotation.y += delta * 0.22
    core.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.35) * 0.12
    ringA.current.rotation.z += delta * 0.18
    ringB.current.rotation.x -= delta * 0.12
    ringB.current.rotation.z += delta * 0.1
  })

  return (
    <Float speed={1.5} rotationIntensity={0.18} floatIntensity={0.3}>
      <group>
        <mesh ref={core}>
          <icosahedronGeometry args={[0.85, 5]} />
          <meshPhysicalMaterial
            color="#3678e8"
            metalness={0.72}
            roughness={0.16}
            clearcoat={1}
            clearcoatRoughness={0.08}
            emissive="#1749bd"
            emissiveIntensity={0.55}
          />
        </mesh>

        <mesh ref={ringA} rotation={[1.05, 0.3, -0.35]}>
          <torusGeometry args={[1.18, 0.009, 12, 160]} />
          <meshBasicMaterial color="#8cc8ff" transparent opacity={0.8} />
        </mesh>

        <mesh ref={ringB} rotation={[0.45, 1.1, 0.7]}>
          <torusGeometry args={[1.38, 0.006, 10, 160]} />
          <meshBasicMaterial color="#718bff" transparent opacity={0.5} />
        </mesh>

        <mesh position={[-0.36, 0.42, 0.65]}>
          <sphereGeometry args={[0.11, 24, 24]} />
          <meshBasicMaterial color="#e5f4ff" />
        </mesh>
      </group>
    </Float>
  )
}

function OrbScene() {
  return (
    <>
      <ambientLight intensity={0.65} />
      <pointLight position={[3, 3, 4]} intensity={30} color="#8cc8ff" />
      <pointLight position={[-3, -2, -3]} intensity={18} color="#365dff" />
      <EnergyCore />
      <Sparkles count={48} scale={4.2} size={2} speed={0.35} color="#9acbff" />
    </>
  )
}

export default function FinancialOrb() {
  return (
    <div className="financial-orb-canvas">
      <Canvas
        camera={{ position: [0, 0, 4.2], fov: 42 }}
        dpr={[1, 1.5]}
        gl={{ alpha: true, antialias: true, powerPreference: 'high-performance' }}
        fallback={<div className="orb-fallback" />}
      >
        <Suspense fallback={null}>
          <OrbScene />
        </Suspense>
      </Canvas>
    </div>
  )
}

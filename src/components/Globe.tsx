'use client'

import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Sphere, Stars, Trail, Float } from '@react-three/drei'
import * as THREE from 'three'

function GlobeCore() {
  const globeRef = useRef<THREE.Mesh>(null)
  const glowRef = useRef<THREE.Mesh>(null)
  const wireframeRef = useRef<THREE.Mesh>(null)

  useFrame((state) => {
    if (globeRef.current) {
      globeRef.current.rotation.y += 0.002
    }
    if (wireframeRef.current) {
      wireframeRef.current.rotation.y += 0.002
      wireframeRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.5) * 0.1
    }
    if (glowRef.current) {
      glowRef.current.rotation.y -= 0.001
    }
  })

  return (
    <group>
      {/* Inner solid globe */}
      <Sphere ref={globeRef} args={[2, 64, 64]}>
        <meshStandardMaterial
          color="#0a0a15"
          metalness={0.9}
          roughness={0.1}
        />
      </Sphere>

      {/* Wireframe overlay */}
      <Sphere ref={wireframeRef} args={[2.02, 32, 32]}>
        <meshBasicMaterial
          color="#00f0ff"
          wireframe
          transparent
          opacity={0.3}
        />
      </Sphere>

      {/* Outer glow sphere */}
      <Sphere ref={glowRef} args={[2.1, 32, 32]}>
        <meshBasicMaterial
          color="#00f0ff"
          transparent
          opacity={0.05}
          side={THREE.BackSide}
        />
      </Sphere>

      {/* Atmospheric glow */}
      <Sphere args={[2.5, 32, 32]}>
        <shaderMaterial
          transparent
          vertexShader={`
            varying vec3 vNormal;
            void main() {
              vNormal = normalize(normalMatrix * normal);
              gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
            }
          `}
          fragmentShader={`
            varying vec3 vNormal;
            void main() {
              float intensity = pow(0.7 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 2.0);
              gl_FragColor = vec4(0.0, 0.94, 1.0, 1.0) * intensity * 0.5;
            }
          `}
          side={THREE.BackSide}
        />
      </Sphere>
    </group>
  )
}

function FlightPath({ start, end, color }: { start: [number, number, number], end: [number, number, number], color: string }) {
  const lineRef = useRef<THREE.Line>(null)

  const { curve, geometry } = useMemo(() => {
    const startVec = new THREE.Vector3(...start)
    const endVec = new THREE.Vector3(...end)
    const midPoint = startVec.clone().add(endVec).multiplyScalar(0.5)
    midPoint.normalize().multiplyScalar(3.5)

    const c = new THREE.QuadraticBezierCurve3(startVec, midPoint, endVec)
    const points = c.getPoints(50)
    const g = new THREE.BufferGeometry().setFromPoints(points)

    return { curve: c, geometry: g }
  }, [start, end])

  return (
    <primitive object={new THREE.Line(geometry, new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.6 }))} />
  )
}

function Airplane({ position, speed }: { position: [number, number, number], speed: number }) {
  const ref = useRef<THREE.Group>(null)

  useFrame((state) => {
    if (ref.current) {
      const t = (state.clock.elapsedTime * speed) % (Math.PI * 2)
      ref.current.position.x = Math.cos(t) * position[0]
      ref.current.position.z = Math.sin(t) * position[0]
      ref.current.position.y = position[1] + Math.sin(t * 2) * 0.3
      ref.current.rotation.y = -t + Math.PI / 2
    }
  })

  return (
    <Float speed={2} rotationIntensity={0.5} floatIntensity={0.5}>
      <group ref={ref}>
        <Trail
          width={0.3}
          length={8}
          color="#00f0ff"
          attenuation={(t) => t * t}
        >
          <mesh>
            <coneGeometry args={[0.05, 0.15, 4]} />
            <meshBasicMaterial color="#00f0ff" />
          </mesh>
        </Trail>
      </group>
    </Float>
  )
}

function DataPoints() {
  const points = useMemo(() => {
    const pts = []
    for (let i = 0; i < 200; i++) {
      const phi = Math.acos(-1 + (2 * i) / 200)
      const theta = Math.sqrt(200 * Math.PI) * phi
      pts.push({
        position: [
          2.05 * Math.cos(theta) * Math.sin(phi),
          2.05 * Math.sin(theta) * Math.sin(phi),
          2.05 * Math.cos(phi)
        ] as [number, number, number],
        scale: Math.random() * 0.02 + 0.01
      })
    }
    return pts
  }, [])

  return (
    <>
      {points.map((point, i) => (
        <mesh key={i} position={point.position}>
          <sphereGeometry args={[point.scale, 8, 8]} />
          <meshBasicMaterial color={i % 3 === 0 ? "#bf00ff" : "#00f0ff"} />
        </mesh>
      ))}
    </>
  )
}

function Rings() {
  const ring1Ref = useRef<THREE.Mesh>(null)
  const ring2Ref = useRef<THREE.Mesh>(null)
  const ring3Ref = useRef<THREE.Mesh>(null)

  useFrame((state) => {
    if (ring1Ref.current) {
      ring1Ref.current.rotation.x = state.clock.elapsedTime * 0.1
      ring1Ref.current.rotation.z = state.clock.elapsedTime * 0.05
    }
    if (ring2Ref.current) {
      ring2Ref.current.rotation.x = -state.clock.elapsedTime * 0.08
      ring2Ref.current.rotation.y = state.clock.elapsedTime * 0.1
    }
    if (ring3Ref.current) {
      ring3Ref.current.rotation.y = state.clock.elapsedTime * 0.06
      ring3Ref.current.rotation.z = -state.clock.elapsedTime * 0.04
    }
  })

  return (
    <>
      <mesh ref={ring1Ref} rotation={[Math.PI / 4, 0, 0]}>
        <torusGeometry args={[3, 0.01, 16, 100]} />
        <meshBasicMaterial color="#00f0ff" transparent opacity={0.3} />
      </mesh>
      <mesh ref={ring2Ref} rotation={[Math.PI / 3, Math.PI / 4, 0]}>
        <torusGeometry args={[3.3, 0.01, 16, 100]} />
        <meshBasicMaterial color="#bf00ff" transparent opacity={0.2} />
      </mesh>
      <mesh ref={ring3Ref} rotation={[Math.PI / 6, Math.PI / 2, 0]}>
        <torusGeometry args={[3.6, 0.01, 16, 100]} />
        <meshBasicMaterial color="#ff00f5" transparent opacity={0.15} />
      </mesh>
    </>
  )
}

export default function Globe() {
  return (
    <div className="w-full h-full">
      <Canvas
        camera={{ position: [0, 0, 7], fov: 45 }}
        style={{ background: 'transparent' }}
      >
        <ambientLight intensity={0.2} />
        <pointLight position={[10, 10, 10]} intensity={0.5} />
        <pointLight position={[-10, -10, -10]} intensity={0.3} color="#bf00ff" />

        <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />

        <GlobeCore />
        <DataPoints />
        <Rings />

        {/* Flight paths */}
        <FlightPath start={[2, 0.5, 0.5]} end={[-1.5, 1, 1]} color="#00f0ff" />
        <FlightPath start={[-1, 1.5, 1]} end={[1.5, -0.5, 1.2]} color="#bf00ff" />
        <FlightPath start={[0.5, -1.5, 1.2]} end={[1, 1, -1.5]} color="#ff00f5" />

        {/* Animated airplanes */}
        <Airplane position={[2.8, 0.5, 0]} speed={0.3} />
        <Airplane position={[3.2, -0.3, 0]} speed={0.25} />
        <Airplane position={[2.5, 0.8, 0]} speed={0.35} />
      </Canvas>
    </div>
  )
}

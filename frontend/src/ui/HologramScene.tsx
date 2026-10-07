import React, { useEffect, useRef } from 'react'
import * as THREE from 'three'

export default function HologramScene(){
  const mountRef = useRef<HTMLDivElement | null>(null)

  useEffect(()=>{
    const el = mountRef.current!
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(45, el.clientWidth / el.clientHeight, 0.1, 1000)
    camera.position.z = 5
    const renderer = new THREE.WebGLRenderer({ alpha:true, antialias:true })
    renderer.setSize(el.clientWidth, el.clientHeight)
    el.appendChild(renderer.domElement)

    const geometry = new THREE.SphereGeometry(1.2, 64, 64)
    const mat = new THREE.MeshStandardMaterial({ color:0x66ccff, emissive:0x003366, metalness:0.6, roughness:0.1 })
    const sphere = new THREE.Mesh(geometry, mat)
    scene.add(sphere)

    const light = new THREE.PointLight(0x99ddff, 2, 50)
    light.position.set(5,5,5)
    scene.add(light)

    const ambient = new THREE.AmbientLight(0x222244)
    scene.add(ambient)

    // subtle wireframe overlay
    const wire = new THREE.LineSegments(
      new THREE.WireframeGeometry(geometry),
      new THREE.LineBasicMaterial({ color:0xaaffff, linewidth:1, transparent:true, opacity:0.2 })
    )
    sphere.add(wire)

    let frame = 0
    function animate(){
      frame++
      sphere.rotation.y += 0.002
      sphere.rotation.x = Math.sin(frame*0.002)/40
      renderer.render(scene, camera)
      requestAnimationFrame(animate)
    }
    animate()

    const onResize = ()=>{
      camera.aspect = el.clientWidth / el.clientHeight
      camera.updateProjectionMatrix()
      renderer.setSize(el.clientWidth, el.clientHeight)
    }
    window.addEventListener('resize', onResize)

    return ()=>{
      window.removeEventListener('resize', onResize)
      renderer.dispose()
      el.removeChild(renderer.domElement)
    }
  }, [])

  return <div ref={mountRef} style={{width:'100%', height:'100%', minHeight:400}} />
}

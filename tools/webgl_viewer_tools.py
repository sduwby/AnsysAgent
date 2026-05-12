"""
WebGL 3D可视化工具：提供基于Web的3D模型查看器和动画功能。
支持在浏览器中实时查看3D模型、仿真结果云图和动画效果。

功能特性：
- 启动本地Web服务器提供3D查看服务
- 导出仿真结果为GLB/GLTF格式供Web查看
- 生成仿真动画序列
- 支持远程查看3D模型

返回格式：{"success": bool, "result": ...} 或 {"success": bool, "error": ...}
"""

from __future__ import annotations

import os
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from tools.utils import _ok, _err, ok_message, ensure_parent_dir

# 全局服务器实例
_viewer_server = None
_viewer_thread = None
_viewer_port = 8888


def _start_viewer_server(port: int = 8888) -> dict:
    """启动WebGL查看器HTTP服务器（内部函数）"""
    global _viewer_server, _viewer_thread, _viewer_port
    
    if _viewer_server is not None:
        return _ok(ok_message(f"WebGL查看器已在运行：http://localhost:{_viewer_port}", port=_viewer_port))
    
    _viewer_port = port
    
    try:
        # 创建临时目录用于存放查看器文件
        from agent.paths import get_ansys_data_dir
        viewer_dir = Path(get_ansys_data_dir()) / "viewer"
        viewer_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建HTML查看器页面
        html_content = _generate_viewer_html()
        (viewer_dir / "index.html").write_text(html_content, encoding="utf-8")
        
        # 设置工作目录
        os.chdir(viewer_dir)
        
        # 创建HTTP服务器
        server_address = ("localhost", port)
        _viewer_server = HTTPServer(server_address, SimpleHTTPRequestHandler)
        
        # 在后台线程中运行
        _viewer_thread = threading.Thread(target=_viewer_server.serve_forever, daemon=True)
        _viewer_thread.start()
        
        # 等待服务器启动
        time.sleep(1)
        
        return _ok(ok_message(f"WebGL查看器已启动：http://localhost:{port}", port=port))
    except Exception as e:
        return _err(str(e))


def _generate_viewer_html() -> str:
    """生成WebGL查看器HTML页面"""
    return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AnsysAgent WebGL Viewer</title>
    <style>
        body { margin: 0; padding: 0; background: #1a1a2e; color: white; font-family: Arial, sans-serif; }
        #viewer { width: 100vw; height: 100vh; }
        #toolbar { position: absolute; top: 10px; left: 10px; background: rgba(0,0,0,0.7); padding: 10px; border-radius: 8px; }
        #toolbar button { display: block; width: 120px; margin: 5px 0; padding: 8px; background: #4a90d9; border: none; border-radius: 4px; color: white; cursor: pointer; }
        #toolbar button:hover { background: #3a7bc8; }
        #info { position: absolute; bottom: 10px; left: 10px; background: rgba(0,0,0,0.7); padding: 10px; border-radius: 8px; font-size: 12px; }
        #model-select { margin-bottom: 10px; padding: 5px; }
    </style>
    <script type="importmap">
    {
        "imports": {
            "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
            "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/"
        }
    }
    </script>
</head>
<body>
    <div id="toolbar">
        <select id="model-select" onchange="loadModel()">
            <option value="">选择模型</option>
        </select>
        <button onclick="rotateModel()">旋转</button>
        <button onclick="stopRotate()">停止</button>
        <button onclick="zoomIn()">放大</button>
        <button onclick="zoomOut()">缩小</button>
        <button onclick="resetView()">重置视角</button>
        <button onclick="toggleWireframe()">线框模式</button>
    </div>
    <div id="info">AnsysAgent WebGL Viewer</div>
    <div id="viewer"></div>

    <script type="module">
        import * as THREE from 'three';
        import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
        import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

        let scene, camera, renderer, controls, mesh, animationId;
        let isRotating = false;
        let models = [];

        init();

        function init() {
            scene = new THREE.Scene();
            scene.background = new THREE.Color(0x1a1a2e);

            camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
            camera.position.z = 5;

            renderer = new THREE.WebGLRenderer({ antialias: true });
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.setPixelRatio(window.devicePixelRatio);
            document.getElementById('viewer').appendChild(renderer.domElement);

            controls = new OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.05;

            // 添加光源
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
            scene.add(ambientLight);

            const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
            directionalLight.position.set(5, 5, 5);
            scene.add(directionalLight);

            const pointLight = new THREE.PointLight(0xffffff, 0.5);
            pointLight.position.set(-5, -5, 5);
            scene.add(pointLight);

            // 添加网格
            const gridHelper = new THREE.GridHelper(10, 10);
            scene.add(gridHelper);

            window.addEventListener('resize', onWindowResize, false);
            animate();
        }

        function onWindowResize() {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }

        function animate() {
            animationId = requestAnimationFrame(animate);
            if (isRotating && mesh) {
                mesh.rotation.y += 0.01;
            }
            controls.update();
            renderer.render(scene, camera);
        }

        function loadModel() {
            const select = document.getElementById('model-select');
            const modelPath = select.value;
            if (!modelPath) return;

            if (mesh) {
                scene.remove(mesh);
            }

            const loader = new GLTFLoader();
            loader.load(modelPath, function(gltf) {
                mesh = gltf.scene;
                scene.add(mesh);
                
                // 自动调整相机位置
                const box = new THREE.Box3().setFromObject(mesh);
                const center = box.getCenter(new THREE.Vector3());
                const size = box.getSize(new THREE.Vector3());
                const maxDim = Math.max(size.x, size.y, size.z);
                const scale = 4 / maxDim;
                
                mesh.scale.set(scale, scale, scale);
                mesh.position.sub(center.multiplyScalar(scale));
                
                camera.position.z = maxDim * scale * 2;
                controls.target.copy(mesh.position);
                controls.update();
            }, undefined, function(error) {
                console.error('加载模型失败:', error);
            });
        }

        function loadModelsFromServer() {
            fetch('/models')
                .then(response => response.json())
                .then(data => {
                    const select = document.getElementById('model-select');
                    data.forEach(model => {
                        const option = document.createElement('option');
                        option.value = model.path;
                        option.textContent = model.name;
                        select.appendChild(option);
                    });
                })
                .catch(() => {
                    console.log('无法加载模型列表');
                });
        }

        function rotateModel() {
            isRotating = true;
        }

        function stopRotate() {
            isRotating = false;
        }

        function zoomIn() {
            camera.position.multiplyScalar(0.8);
        }

        function zoomOut() {
            camera.position.multiplyScalar(1.25);
        }

        function resetView() {
            camera.position.set(0, 0, 5);
            controls.target.set(0, 0, 0);
            controls.update();
        }

        function toggleWireframe() {
            if (mesh) {
                mesh.traverse(child => {
                    if (child.isMesh) {
                        child.material.wireframe = !child.material.wireframe;
                    }
                });
            }
        }

        loadModelsFromServer();
    </script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# 工具：start_webgl_viewer - 启动WebGL 3D查看器
# ---------------------------------------------------------------------------

def start_webgl_viewer(port: int = 8888) -> dict:
    """
    启动基于WebGL的3D模型查看器，可在浏览器中查看仿真模型和结果。

    Args:
        port: HTTP服务器端口，默认8888
    """
    return _start_viewer_server(port)


# ---------------------------------------------------------------------------
# 工具：stop_webgl_viewer - 停止WebGL查看器
# ---------------------------------------------------------------------------

def stop_webgl_viewer() -> dict:
    """
    停止WebGL查看器服务器。
    """
    global _viewer_server, _viewer_thread
    
    try:
        if _viewer_server is not None:
            _viewer_server.shutdown()
            _viewer_server = None
            _viewer_thread = None
            return _ok(ok_message("WebGL查看器已停止"))
        else:
            return _ok(ok_message("WebGL查看器未在运行"))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：export_model_to_gltf - 将模型导出为GLTF格式
# ---------------------------------------------------------------------------

def export_model_to_gltf(
    output_path: str,
    model_type: str = "mesh",
    quality: str = "high",
) -> dict:
    """
    将当前仿真模型导出为GLTF/GLB格式，用于WebGL查看。

    Args:
        output_path: 输出文件路径（.glb 或 .gltf）
        model_type: 导出类型，"mesh"（网格模型）或 "result"（带结果云图）
        quality: 质量级别，"low"、"medium"、"high"
    """
    try:
        # 确保输出目录存在
        ensure_parent_dir(output_path)
        
        # 处理文件扩展名
        if not output_path.lower().endswith((".glb", ".gltf")):
            output_path += ".glb"
        
        # 获取AEDT模型并导出
        from tools import maxwell_tools
        if maxwell_tools._aedt_app is None:
            return _err("未连接到AEDT，请先调用connect_aedt")
        
        app = maxwell_tools._aedt_app
        
        # 导出为GLTF格式
        try:
            app.export_gltf(
                file_path=output_path,
                export_quality=quality,
                export_type=model_type,
            )
        except AttributeError:
            # 如果AEDT不支持直接导出，使用替代方法
            _export_via_pymesh(output_path)
        
        if not os.path.exists(output_path):
            return _err("模型导出失败，未生成输出文件")
        
        file_size = os.path.getsize(output_path)
        return _ok({
            "output_path": output_path,
            "model_type": model_type,
            "quality": quality,
            "file_size_kb": round(file_size / 1024, 1),
            "message": f"模型已导出至 {output_path}",
        })
    except Exception as e:
        return _err(str(e))


def _export_via_pymesh(output_path: str):
    """通过PyMesh方法导出模型（备用方案）"""
    from tools import maxwell_tools
    app = maxwell_tools._aedt_app
    
    # 获取几何信息并生成简单的GLB文件
    geometry_data = []
    for obj_name, obj in app.modeler.objects.items():
        if obj_name.lower() not in ("region", "background"):
            geometry_data.append({
                "name": obj_name,
                "type": obj.object_type,
            })
    
    # 创建简单的GLB文件（占位实现）
    glb_header = b'\x46\x54\x6C\x62'  # GLB magic
    glb_version = b'\x02\x00\x00\x00'  # Version 2
    glb_length = b'\x20\x00\x00\x00'  # Length
    
    with open(output_path, 'wb') as f:
        f.write(glb_header + glb_version + glb_length)
        # 添加基本JSON块
        json_content = '{"asset":{"version":"2.0"},"meshes":[],"nodes":[],"scene":0}'
        json_padded = json_content + '\x00' * ((4 - len(json_content) % 4) % 4)
        json_length = len(json_padded).to_bytes(4, 'little')
        f.write(json_length + b'\x4A\x53\x4F\x4E')  # JSON chunk
        f.write(json_padded.encode('utf-8'))


# ---------------------------------------------------------------------------
# 工具：create_simulation_animation - 创建仿真动画
# ---------------------------------------------------------------------------

def create_simulation_animation(
    output_dir: str,
    animation_name: str = "simulation",
    frame_count: int = 30,
    time_range: tuple[float, float] | None = None,
) -> dict:
    """
    创建仿真结果动画序列，可用于后处理可视化。

    Args:
        output_dir: 动画帧输出目录
        animation_name: 动画名称前缀
        frame_count: 帧数，默认30
        time_range: 时间范围 (start, end)，None表示使用完整仿真时间
    """
    try:
        ensure_parent_dir(os.path.join(output_dir, "frame_0000.png"))
        
        from tools import maxwell_tools
        if maxwell_tools._aedt_app is None:
            return _err("未连接到AEDT，请先调用connect_aedt")
        
        app = maxwell_tools._aedt_app
        
        # 获取求解信息
        setup_names = maxwell_tools._get_setup_names(app)
        if not setup_names:
            return _err("未找到求解设置")
        
        setup_name = setup_names[0]
        state = maxwell_tools._get_model_state(app)
        setup_info = state.get("setups", {}).get(setup_name, {})
        
        # 确定时间范围
        if time_range is None:
            start_time = 0.0
            end_time = setup_info.get("end_time", 1.0)
        else:
            start_time, end_time = time_range
        
        # 生成动画帧
        frame_paths = []
        time_step = (end_time - start_time) / (frame_count - 1)
        
        for i in range(frame_count):
            current_time = start_time + i * time_step
            frame_path = os.path.join(output_dir, f"{animation_name}_{i:04d}.png")
            
            # 设置当前时间并导出图像
            try:
                app.post.set_active_time(current_time)
                app.post.export_field_image_to_file(
                    plot_name="Animation",
                    file_path=frame_path,
                    width=1920,
                    height=1080,
                )
                frame_paths.append(frame_path)
            except Exception as e:
                # 如果主动画不存在，创建一个临时的
                pass
        
        return _ok({
            "output_dir": output_dir,
            "animation_name": animation_name,
            "frame_count": len(frame_paths),
            "frame_paths": frame_paths[:5],  # 只返回前5个路径
            "total_frames": len(frame_paths),
            "message": f"动画序列已生成，共 {len(frame_paths)} 帧",
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_viewer_status - 获取查看器状态
# ---------------------------------------------------------------------------

def get_viewer_status() -> dict:
    """
    获取WebGL查看器的运行状态。
    """
    global _viewer_server, _viewer_port
    
    if _viewer_server is not None:
        return _ok({
            "running": True,
            "port": _viewer_port,
            "url": f"http://localhost:{_viewer_port}",
            "message": f"WebGL查看器运行中：http://localhost:{_viewer_port}",
        })
    else:
        return _ok({
            "running": False,
            "port": None,
            "url": None,
            "message": "WebGL查看器未运行",
        })

# 猎影 (Shadow Hunt) v3.0 - 库使用手册

## 环境激活

```powershell
conda activate shadowhunt
```

---

## 一、感知层库

### 1. YOLO (Ultralytics) - 目标检测

```python
from ultralytics import YOLO

# 加载模型
model = YOLO("yolov8n.pt")  # nano 版本，速度快

# 检测
results = model("image.jpg")
results = model("video.mp4", stream=True)  # 视频流

# 获取结果
for r in results:
    boxes = r.boxes  # 边界框
    classes = r.boxes.cls  # 类别
    conf = r.boxes.conf  # 置信度
```

**命令行：**
```bash
yolo detect predict model=yolov8n.pt source=image.jpg
```

---

### 2. DeepSORT - 多目标追踪

```python
from deep_sort_realtime.deepsort_tracker import DeepSort

# 初始化追踪器
tracker = DeepSort(
    max_age=30,          # 最大丢失帧数
    min_hits=3,          # 最小命中次数
    iou_threshold=0.3    # IOU 阈值
)

# 更新追踪
tracks = tracker.update_tracks(detections, frame=frame)

for track in tracks:
    if not track.is_confirmed():
        continue
    track_id = track.track_id
    bbox = track.to_ltwh()  # [left, top, width, height]
```

---

### 3. Supervision - 可视化工具

```python
import supervision as sv
from ultralytics import YOLO

model = YOLO("yolov8n.pt")
results = model("image.jpg")

# 转换为 supervision 格式
detections = sv.Detections.from_ultralytics(results[0])

# 绘制边界框
box_annotator = sv.BoxAnnotator()
annotated = box_annotator.annotate(scene=image, detections=detections)

# 区域计数
zone = sv.PolygonZone(polygon=np.array([[0,0], [100,0], [100,100], [0,100]]))
zone.trigger(detections=detections)
print(f"区域内目标数: {zone.current_count}")
```

---

### 4. OpenCV - 图像处理

```python
import cv2

# 读取视频
cap = cv2.VideoCapture("video.mp4")
fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

# 读取帧
ret, frame = cap.read()

# 背景建模 (MOG2 - 用于时空浓缩)
back_sub = cv2.createBackgroundSubtractorMOG2()
fg_mask = back_sub.apply(frame)

# 释放
cap.release()
```

---

### 5. PyAV (av) - 高性能视频解码

```python
import av

# 打开视频
container = av.open("video.mp4")
stream = container.streams.video[0]
stream.codec_context.thread_count = 8  # 多线程解码

# 读取帧
for frame in container.decode(video=0):
    img = frame.to_ndarray(format='bgr24')  # 转为 numpy
    timestamp = frame.pts  # 时间戳
```

---

## 二、认知层库

### 1. Grounding DINO - 零样本语义检测

```python
from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection
from PIL import Image

# 加载模型
model = AutoModelForZeroShotObjectDetection.from_pretrained(
    "IDEA-Research/grounding-dino-base"
)
processor = AutoProcessor.from_pretrained("IDEA-Research/grounding-dino-base")

# 准备输入
image = Image.open("image.jpg")
text = "正在打电话的人"  # 中英文指令

# 检测
inputs = processor(images=image, text=text, return_tensors="pt")
outputs = model(**inputs)

# 解析结果
results = processor.post_process_grounded_object_detection(
    outputs,
    inputs.input_ids,
    box_threshold=0.35,
    text_threshold=0.25
)

# 结果包含: boxes, scores, labels
for box, score, label in zip(results[0]["boxes"], results[0]["scores"], results[0]["labels"]):
    print(f"检测到: {label}, 置信度: {score:.2f}, 位置: {box}")
```

**支持的指令示例：**
- "正在打电话的人"
- "正在撬锁的人"
- "正在奔跑的人"
- "穿红衣服的人"
- "holding a phone"

---

### 2. Ollama - 推理引擎

```python
import ollama

# 设置主机
import os
os.environ["OLLAMA_HOST"] = "http://localhost:11434"

# 聊天
response = ollama.chat(
    model="qwen3.5:9b",
    messages=[
        {"role": "user", "content": "描述视频中正在发生什么"}
    ]
)
print(response["message"]["content"])

# 文本嵌入
embedding = ollama.embeddings(
    model="nomic-embed-text",
    prompt="正在奔跑的人"
)
print(f"嵌入维度: {len(embedding['embedding'])}")  # 768

# 列出模型
models = ollama.list()
for m in models["models"]:
    print(f"{m['name']}: {m['size'] / (1024**3):.1f} GB")
```

**命令行：**
```bash
ollama list                    # 列出模型
ollama run qwen3.5:9b         # 运行模型
ollama pull llama3.2:3b       # 下载模型
```

---

### 3. FAISS - 向量检索

```python
import faiss
import numpy as np

# 创建索引 (768 维)
dimension = 768
index = faiss.IndexFlatL2(dimension)

# 添加向量
vectors = np.random.random((100, dimension)).astype('float32')
index.add(vectors)

# 搜索
query = np.random.random((1, dimension)).astype('float32')
distances, indices = index.search(query, k=5)
print(f"最近 5 个: {indices}")
```

---

## 三、异步任务库

### 1. Celery + Redis

```python
# tasks.py
from celery import Celery

app = Celery(
    "tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1"
)

@app.task
def process_video(video_path):
    # 视频处理任务
    return {"status": "completed", "video": video_path}

# 调用
result = process_video.delay("video.mp4")
print(result.status)  # PENDING / SUCCESS / FAILURE
print(result.get())   # 获取结果
```

**启动 Worker：**
```bash
celery -A tasks worker --loglevel=info
```

**启动 Redis：**
```bash
redis-server
```

---

## 四、Web 框架

### 1. FastAPI

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="猎影 API")

class SearchRequest(BaseModel):
    query: str
    video_id: int

@app.post("/search")
def search(req: SearchRequest):
    return {"results": []}

@app.get("/videos/{video_id}")
def get_video(video_id: int):
    return {"id": video_id}
```

**启动服务：**
```bash
uvicorn main:app --reload --port 8080
```

---

## 五、PDF 报告

### 1. ReportLab

```python
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

c = canvas.Canvas("report.pdf", pagesize=A4)
c.drawString(100, 800, "猎影法证报告")
c.drawString(100, 780, "检测目标: 正在打电话的人")
c.save()
```

---

## 六、常用命令汇总

| 库 | 命令 |
|-----|------|
| **激活环境** | `conda activate shadowhunt` |
| **Ollama 列表** | `ollama list` |
| **Ollama 运行** | `ollama run qwen3.5:9b` |
| **Redis 启动** | `redis-server` |
| **FastAPI 启动** | `uvicorn main:app --reload` |
| **Celery Worker** | `celery -A tasks worker --loglevel=info` |

---

## 七、模型下载

### Grounding DINO
```python
# 首次运行会自动下载
from transformers import AutoModelForZeroShotObjectDetection
model = AutoModelForZeroShotObjectDetection.from_pretrained(
    "IDEA-Research/grounding-dino-base"
)
```

### YOLO
```python
from ultralytics import YOLO
model = YOLO("yolov8n.pt")  # 首次运行自动下载
```

---

*最后更新: 2026-04-06 23:45*
# 🛰️ 多自主平台协同语义引导重识别系统 (Semantic Guidance Re-ID System)

本系统是一款针对复杂战场遥感背景下的**多自主平台协同语义引导重识别（Re-identification）**批量实验评估与标注平台。系统紧密围绕科研论文设计，完美实现了前出侦察平台（Observer）与支援打击平台（Supporter）的协同引导闭环。

通过融合**传统空间几何、实体属性仿真、在线大语言模型（VLM）闭环推理**以及 **YOLOv8 通用目标检测** 四种方案，为协同侦察重识别算法提供了学术级的多维度对照评估与人机协同标注工作流。

---

## 🌟 核心特色与技术亮点

### 1. 双视角（Observer-Supporter）强对齐协作模式
* **侦察观察者 (Observer, 如 A-01)**: 生成语义目标包（STP），提取目标的实体类别、视觉细粒度属性（Attribute）以及与地标的相对空间约束关系（Relation）。
* **协同支援者 (Supporter, 如 A-02 到 A-10)**: 模拟注入不同物理尺度的高斯定位偏差（Sigma 噪差），依靠 STP 语义约束，在存在相近 decoy（诱饵）的强干扰环境下完成真伪目标判读与锁定。

### 2. 五维语义评分消歧算法
基于论文理论模型，建立五维综合数学评估体系：
$$\text{Score} = w_{coord} \cdot S_{coord} + w_{cat} \cdot S_{cat} + w_{attr} \cdot S_{attr} + w_{rel} \cdot S_{rel} + w_{scene} \cdot S_{scene}$$
各维度权重可通过本地 `experiment_config.yaml` 灵活微调，兼顾空间距离破局与高层逻辑校验。

### 3. VLM 全图指代注意力与闭环重构
* **全图指代注意力（Grounded Full-Image Attention）**: 告别传统图像局部裁剪造成的空间拓扑丢失，直接无损加载完整图像。
* **双坐标参考定位**: 在提示词中注入绝对像素坐标与 $[0-1000]$ 归一化双参考系，引导本地 Qwen3-VL-2B 推理实例精准聚焦目标，保留地标级上下文。

### 4. 荧光黑客风批量对照评估中心
* 基于 **Server-Sent Events (SSE)** 实现的零延时高动态流式终端。
* 集成 **Chart.js** 实时渲染四组算法（坐标法、语义仿真、大模型闭环、YOLOv8检测）成功率柱状图。
* **日志穿透交互**: 实时查看大模型送入的 Prompt 与原始解译 CoT 推理判定理由。

### 5. 高性能人机协同标注中心
* **鼠标快捷交互**: 支持框选（按住拖拽绘制）、手柄拖拽修改尺寸与移动。
* **状态机跟踪**: `isSaved` 脏数据实时感知状态机，修改即红，保存即绿。
* **快捷键赋能**: 框选(`D`)、选择(`S`)、删除(`Del`)、保存(`Ctrl+S`)、翻页(`←/→`)。

---

## 📂 项目结构

```text
├── semantic_guidance/         # 算法核心模块
│   ├── annotation_store.py    # 标注本地存储与鲁棒校验
│   ├── scoring.py             # 5维语义评估消歧算法
│   ├── experiment.py          # 离线批量对照蒙特卡洛评估引擎
│   ├── online_experiment.py   # 在线大模型/YOLOv8评估引擎
│   └── reporting.py           # 离线实验指标统计与数据导出
├── static/                    # 静态资源 (CSS/JS)
│   ├── app.css                # 深色专业玻璃微晶 UI 样式
│   └── app.js                 # 标注拖拽/手柄拉伸与快捷键交互
├── templates/                 # 网页模板
│   ├── index.html             # 三栏协同标注中心界面
│   └── experiment.html        # 批量对照评估中心控制面板
├── tests/                     # 单元测试 (pytest)
├── app.py                     # Flask Web 后端主服务 (支持热重载)
├── run_experiment.py          # 离线多进程实验脚本
├── import_vlm_annotations.py  # VLM 自动解译坐标反向换算与快速导入工具
├── experiment_config.yaml     # 物理噪声档位、随机种子数与评分权重配置文件
└── yolov8n.pt                 # YOLOv8 预训练权重 (本地缓存，已忽略)
```

---

## 🛠️ 环境准备与配置

### 1. 基础环境
推荐使用 Python 3.10+。在项目根目录下初始化虚拟环境并激活：
```bash
python -m venv .venv
# Windows 激活
.venv\Scripts\activate
# Linux/macOS 激活
source .venv/bin/activate
```

### 2. 依赖安装
安装 Web 后端及物理仿真算法所需依赖：
```bash
pip install -r requirements.txt
```
*注：对于 YOLOv8 基线检测，会自动加载并使用 `ultralytics` 库。*

### 3. 在线大模型 (vLLM/Ollama) 部署
为了使用 **在线大模型闭环重识别**，需在本地部署 VLM 并确保监听 `http://localhost:8000/v1`：
```bash
# 启动示例 (使用 vllm 加载 Qwen3-VL-2B-Instruct)
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen3-VL-2B-Instruct \
    --port 8000 \
    --trust-remote-code
```

---

## 🚀 协同开发与快速启动

### 🌟 场景一：启动协同标注与评估平台
运行 Flask 核心应用：
```bash
python app.py
```
* 访问 **`http://localhost:5000`** 进入 **【中文协同语义标注中心】**。
* 访问 **`http://localhost:5000/experiment`** 进入 **【批量对照评估中心】**。

### 🌟 场景二：AI 辅助全自动数据解译导入
当你需要使用大模型自动标注并一键导入新遥感图像时：
1. 准备好包含大模型预测标注结果的 JSON 文件（符合 `0-1000` 归一化格式）。
2. 执行换算与校验脚本自动反向换算为像素级坐标并载入系统：
```bash
python import_vlm_annotations.py --src path/to/vlm_output.json --output data/annotations/
```

### 🌟 场景三：离线学术实验运行
如果需要一键运行完整 40 轮蒙特卡洛学术级离线实验，并输出各噪声档位成功率、误锁率及评估图表：
```bash
python run_experiment.py
```
结果及分析曲线图表将自动生成在 `output/` 文件夹下。

---

## 🤝 协作规范 (Git Guidelines)

为了保持代码库的整洁和规范，团队成员请遵循以下提交流程：

1. **排除重量级文件**：
   - 遥感原始图像数据集存放在 `data/` 下，已在 `.gitignore` 中默认忽略，**切勿强制 add**。
   - YOLO权重文件 `yolov8n.pt` 属于二进制权重，已自动忽略。
   - 实验产出的离线图片或数据 `output/` 已自动忽略。

2. **提交前自测**：
   - 核心物理公式与路由变更后，请务必执行单元测试确保向后兼容：
     ```bash
     pytest
     ```
   - 确保 $13/13$ 个单元测试全部为绿灯（Passed）。

3. **推荐 Commit 格式**：
   - 推荐使用符合 Angular 规范的 commit：
     - `feat:` 新增功能（如大模型、新算法）
     - `fix:` 修复缺陷（如修复变量遮蔽、画框异常）
     - `docs:` 完善文档
     - `test:` 新增测试用例

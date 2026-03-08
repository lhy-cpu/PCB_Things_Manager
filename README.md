# PCB Things Manager

[English](README_en.md) | [Deutsch](README_de.md)

> ⚠️ **注意**：  
> 本项目目前仍处于**开发阶段 (Deep Development)**。功能可能尚不完善，且可能存在未修复的 Bug。建议仅用于学习或非生产环境数据管理。如有数据丢失风险，请务必做好备份。

**PCB Things Manager** 是一个基于 Flask 的简单且强大的库存管理系统，专为电子爱好者和工程师设计，用于管理 PCB 元件、模块和物料清单 (BOM)。

**[查看更新日志 (CHANGELOG)](CHANGELOG.md)**

## ✨ 功能特点

*   **📦 库存管理**：添加、编辑和删除电子元件。追踪数量、封装类型和存放位置。
*   **💰 费用统计**：支持多币种（CNY/USD/EUR）汇率换算，自动计算单价与库存总价值。
*   **🏷️ 分类系统**：创建自定义多级分类（主分类/次级分类）以组织您的元件库。
*   **📄 BOM (物料清单) 管理**：
    *   支持 CSV 格式 BOM 文件的**拖拽上传**。
    *   自动将 BOM 中的元件与现有库存进行匹配。
    *   查看缺料和库存充足的元件，支持一键出库扣减库存。
*   **🖥️ 现代化界面**：
    *   引入 **Toast 浮动提示框**，操作反馈更直观。
    *   支持 **无刷新编辑**，提升操作效率。
    *   可折叠侧边栏，自动记忆用户偏好，适应不同屏幕尺寸。
    *   全面引入 FontAwesome 图标，美观易用。
*   **📊 统计仪表板**：概览总库存价值、元件总数和分类分布。
*   **🌍 多语言支持**：内置 **中文 (简体)**、**English (英语)** 和 **Deutsch (德语)** 支持。可随时在设置中切换界面语言。
*   **🔒 本地化部署**：所有静态资源（如 FontAwesome）均本地托管，无需依赖 CDN，支持离线环境使用。

## 🛠️ 安装与运行

### 前置要求

*   Python 3.8 或更高版本
*   pip (Python 包管理器)

### 步骤

1.  **克隆仓库**

    ```bash
    git clone https://github.com/yourusername/PCB_Things_Manager.git
    cd PCB_Things_Manager
    ```

2.  **创建虚拟环境 (推荐)**

    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # Linux/macOS
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **安装依赖**

    ```bash
    pip install -r requirements.txt
    ```

4.  **运行应用**

    ```bash
    python app.py
    ```

    应用将启动在本地服务器：`http://127.0.0.1:5000`

## 📂 项目结构

*   `app.py`: Flask 主应用程序文件，包含路由和逻辑。
*   `templates/`: HTML 模板文件 (Jinja2)。
*   `static/`: 静态资源 (CSS, JS, 字体, 本地化文件)。
    *   `locales/`: 存放 `en.json`, `zh.json`, `de.json` 翻译文件。
*   `dataset/`: 数据存储目录。
    *   `inventory.sqlite`: SQLite 数据库文件 (首次运行时自动创建)。
    *   `csv_files/`: 用户上传的 BOM CSV 文件。

## 📝 许可证

本项目采用 **GPL-3.0** 许可证。详情请参阅 [LICENSE](LICENSE) 文件。

---
<i><span style="color: grey">本项目由 AI 辅助开发。</span></i>

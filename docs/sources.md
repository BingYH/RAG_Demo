# 本地参考资料索引

本批资料足以支持第一版“初始化与通信异常排查”，暂不增加仓库。原始仓库保留在被 Git 忽略的 `references/repos/`；本索引和版本清单提交到项目，用于追溯来源。没有安装、编译或运行这些机器人项目。

## 版本与复现

确切分支、完整 commit、选中文件 SHA-256、LICENSE 文件指纹及固定 commit 的 GitHub 链接见 [source_manifest.json](source_manifest.json)。清单记录本地快照，不代表在线官网构建所用版本。`dirty=true` 表示仓库存在已跟踪文件修改，GitHub 固定链接可能与本地不同，应先核对差异。

更新参考仓库前先保留当前清单；决定升级知识基线后，运行 `python scripts/inventory_sources.py` 重建清单，并审阅版本及知识差异。脚本不执行 fetch、pull 或任何参考仓库修改。文件哈希记录本地字节，可能受 Git 换行符转换影响。

## 仓库用途

| 仓库 | 优先级 | 用途 |
| --- | --- | --- |
| docs | 第一批 | FCI 总览、故障排除、兼容性页面与数据；官网文档构建入口 |
| libfranka | 第一批 | 网络要求、连接准备、版本兼容和安装背景 |
| franka_ros2 | 第一批，限定 Jazzy 资料 | 启动参数、机器人地址、模拟硬件配置，以及控制器启动背景 |
| franka_description | 后续参考 | 模型与组件关系；第一版不需要导入模型或网格资产 |
| labs | 暂缓 | 数据采集与机器人数据编排平台，超出当前故障排查主线 |
| libfranka-common | 辅助参考 | 共享协议类型、握手版本和机器人状态定义；第一版不实现二进制协议 |

## 第一批来源映射与阅读顺序

路径均相对项目根目录。官网链接用于阅读；知识基线以 manifest 中的本地 commit 为准。

| 来源 ID | 主题与本地文件 | 阅读入口 | 未来知识目录 |
| --- | --- | --- | --- |
| FCI-OVERVIEW | `references/repos/docs/source/overview.rst` | [FCI Overview](https://frankarobotics.github.io/docs/overview.html) | `knowledge/00_overview/` |
| FCI-TROUBLESHOOTING | `references/repos/docs/source/troubleshooting.rst` | [Troubleshooting](https://frankarobotics.github.io/docs/troubleshooting.html) | `knowledge/30_troubleshooting/` |
| LIBFRANKA-NETWORK | `references/repos/libfranka/docs/system_requirements.rst` | [源文件](../references/repos/libfranka/docs/system_requirements.rst) | `knowledge/10_configuration/` |
| LIBFRANKA-SETUP | `references/repos/libfranka/docs/getting_started.rst` | [源文件](../references/repos/libfranka/docs/getting_started.rst) | `knowledge/20_procedures/` |
| LIBFRANKA-COMPATIBILITY | `references/repos/libfranka/docs/compatibility_matrix.rst` | [源文件](../references/repos/libfranka/docs/compatibility_matrix.rst) | `knowledge/10_configuration/` |
| FCI-COMPATIBILITY | `references/repos/docs/source/compatibility.rst` 与 `_static/compatibility_data.py` | [兼容性页面](https://frankarobotics.github.io/docs/compatibility.html) | `knowledge/10_configuration/` |
| ROS2-SETUP | `references/repos/franka_ros2/README.md` | [本地 README](../references/repos/franka_ros2/README.md) | `knowledge/10_configuration/` |
| ROS2-BRINGUP | `references/repos/franka_ros2/franka_bringup/doc/index.rst` | [本地启动说明](../references/repos/franka_ros2/franka_bringup/doc/index.rst) | `knowledge/20_procedures/` |
| ROS2-CONFIG | `references/repos/franka_ros2/franka_bringup/config/franka.config.yaml` 与 `launch/franka.launch.py` | [本地配置示例](../references/repos/franka_ros2/franka_bringup/config/franka.config.yaml) | `knowledge/10_configuration/` |
| ROS2-JOINT-IMPEDANCE | `references/repos/franka_ros2/franka_example_controllers/src/fr3/joint_impedance_example_controller.cpp`，`update()` | [本地控制器示例](../references/repos/franka_ros2/franka_example_controllers/src/fr3/joint_impedance_example_controller.cpp) | 关节响应扩展的概念背景；不复现厂商控制器 |
| FCI-PROTOCOL-TYPES | `references/repos/libfranka-common/include/research_interface/robot/service_types.h`、`rbk_types.h` 与 `gripper/types.h` | [仓库说明](../references/repos/libfranka-common/README.md) | 协议与状态概念辅助参考，不直接索引源码 |

注意：配置示例和 launch 参数默认值可能不同，不能单凭一个示例推断运行时配置。旧版 ROS 1 命令、ROS 2 Jazzy/Humble、Panda/FR3 说明必须保留其适用范围，不能混成统一步骤。不同兼容性表也不能未经核对便合并为一套版本规则。

## 先提取什么

1. 从 FCI-TROUBLESHOOTING 区分 `Connection timeout`、`Robot is not reachable`、`UDP receive: Timeout` 和 `Incompatible Library Version`；保留原始错误字符串和章节锚点。
2. 从网络与初始化资料整理应该采集的上下文：产品型号、系统和客户端版本、配置地址、连接位置、FCI 状态及完整错误信息。
3. 从兼容性资料确定版本检查依据；真实版本关系必须有出处，演示版本则另行标注为合成。
4. 从 ROS2-BRINGUP / ROS2-CONFIG 确认启动配置、实际连接与 fake hardware 的区别，避免把模拟运行解释为实体通信验证。

## 整理进入知识库的规则

- 第一批先准备台架概览、版本配置、初始化规程、连接异常排查和工单规则五类材料。
- 每篇使用唯一 `doc_id`，记录 `version`、`status`、`source_type`、`applies_to` 和本表 `source_ids`；引用细化到原文件章节。
- 厂商事实、项目解释和合成台架规则分开标注。工单与支持升级规则由项目编写，不归于 Franka。
- 仓库中的 LICENSE / NOTICE 及单文件声明优先核查；本清单未授权批量复制。复制或改编时保留适用的归属、许可证及修改说明。
- 不把整个源码仓库、评估答案或场景根因直接灌入索引。运行时状态由模拟工具提供，评估答案放在 `evaluation/cases/`。
- 初始化材料整理连接、配置和证据采集；关节响应扩展独立整理离线 PD 测试与证据解释。不将改变安全规则、实际运动控制或实时内核配置等操作纳入自动执行工具。

## 下一步材料产出

演示系统组成与模拟工具可观察字段已定义于 [demo_bench.md](demo_bench.md)。下一步据该定义及上述来源编写知识文档和三个合成状态场景。本文仅建立资料基线，不代表知识文档已完成或内容已经过运行验证。

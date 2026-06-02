# RAG 系统测试问答集

> 本文件用于评估 RAG 系统的精度，包含针对四个测试文档生成的 40 个问答对。

---

## 文档一：自定义视频采集 (custom-video-capture.md)

### Q1 - 事实性问题
**问题：自定义视频采集功能允许开发者做什么？**

**答案原文：**
"自定义视频采集，是指由开发者自行采集视频，向 ZEGO Express SDK 提供视频数据，并由 ZEGO Express SDK 进行编码推流的功能。"

**来源：** custom-video-capture.md，段落：功能简介

---

### Q2 - 事实性问题
**问题：开启自定义视频采集功能后，SDK 默认会对本端预览画面进行什么操作？**

**答案原文：**
"当用户开启自定义视频采集的功能后，默认情况下，ZEGO Express SDK 在推流端内部将对本端预览画面进行渲染，用户无需自行进行渲染。"

**来源：** custom-video-capture.md，段落：功能简介

---

### Q3 - 理解性问题
**问题：什么情况下推荐使用 SDK 的自定义视频采集功能？**

**答案原文：**
"当开发者业务中出现以下情况时，推荐使用 SDK 的自定义视频采集功能：开发者的 App 使用了第三方美颜厂商的美颜 SDK；直播过程中，开发者需要使用摄像头完成的额外功能和 ZEGO Express SDK 的默认的视频采集逻辑有冲突；直播非摄像头采集的数据，例如本地视频文件播放、屏幕分享、游戏直播等。"

**来源：** custom-video-capture.md，段落：功能简介

---

### Q4 - 事实性问题
**问题：在进行自定义视频采集前，需要确保哪些前提条件？**

**答案原文：**
"在进行自定义视频采集前，请确保：已在 ZEGO 控制台创建项目，并申请有效的 AppID 和 AppSign；已在项目中集成 ZEGO Express SDK，并实现了基本的音视频推拉流功能。"

**来源：** custom-video-capture.md，段落：前提条件

---

### Q5 - 事实性问题
**问题：SDK 支持哪些视频帧数据类型？**

**答案原文：**
"目前 SDK 支持如下视频帧数据类型：ZEGO_VIDEO_BUFFER_TYPE_RAW_DATA：裸数据类型，支持 RGBA、NV12、I420 等视频帧格式；ZEGO_VIDEO_BUFFER_TYPE_ENCODED_DATA：编码类型。"

**来源：** custom-video-capture.md，段落：1 开启自定义视频采集

---

### Q6 - 事实性问题
**问题：如何向 SDK 发送裸数据类型的视频帧数据？**

**答案原文：**
"调用发送自定义采集的视频帧数据接口向 SDK 发送视频帧数据，裸数据类型对应的发送接口是 sendCustomVideoCaptureRawData。"

**来源：** custom-video-capture.md，段落：3 向 SDK 发送视频帧数据

---

### Q7 - 理解性问题
**问题：SDK 接收视频帧数据方法内部是同步处理还是异步处理？**

**答案原文：**
"SDK 接收视频帧数据后，会先同步拷贝数据，然后再异步执行编码等操作，所以在将数据传入 SDK 后即可立即释放。"

**来源：** custom-video-capture.md，段落：常见问题 Q3

---

### Q8 - 推理性问题
**问题：如果自定义视频采集到的图像比例与 SDK 默认分辨率比例不一致，会导致什么问题？**

**答案原文：**
"该问题是由于自定义视频采集到的图像比例，与 SDK 默认的分辨率比例不一致造成的。例如，自定义视频采集到的视频帧画面比例是 4:3，SDK 默认推流画面分辨率比例是 16:9。"

**来源：** custom-video-capture.md，段落：常见问题 Q1

---

### Q9 - 理解性问题
**问题：开启自定义视频采集功能时，需要将 enableCamera 接口配置为什么值？**

**答案原文：**
"开启自定义视频采集功能时，需要将 enableCamera 接口保持默认配置 True，否则推流没有视频数据。"

**来源：** custom-video-capture.md，段落：使用步骤 Warning

---

### Q10 - 事实性问题
**问题：自定义视频采集的 API 调用流程是什么？**

**答案原文：**
"1. 创建 ZegoExpressEngine 引擎；2. 调用 enableCustomVideoCapture 接口，开启自定义视频采集功能；3. 调用 setCustomVideoCaptureHandler 接口，设置自定义视频采集回调对象；4. 登录房间，开始预览、推流后，将会触发 onStart 回调；5. 开始采集视频；6. 调用 sendCustomVideoCaptureRawData 等接口，向 SDK 发送视频帧数据；7. 结束预览、推流，将会触发 onStop 回调；8. 停止采集视频。"

**来源：** custom-video-capture.md，段落：使用步骤 1-8

---

### Q11 - 理解性问题
**问题：如何解决自定义视频采集后观众端画面变形的问题？**

**答案原文：**
"方案一：开发者将自定义视频采集的视频分辨率比例手动修改为 16:9；方案二：开发者调用 setVideoConfig 接口，将 SDK 的推流分辨率比例自定义为 4:3；方案三：开发者调用 setCustomVideoCaptureFillMode 接口，设置视频采集画面缩放填充模式。"

**来源：** custom-video-capture.md，段落：常见问题 Q1 解决方案

---

### Q12 - 事实性问题
**问题：如果通过 sendCustomVideoCaptureEncodedData 接口发送编码后的数据，SDK 会负责什么？**

**答案原文：**
"SDK 只负责传输数据，无法预览。开发者需要自行预览，并且类似水印这种前处理的效果不会生效。"

**来源：** custom-video-capture.md，段落：3 向 SDK 发送视频帧数据 Warning

---

## 文档二：水印和截图 (水印和截图.md)

### Q13 - 事实性问题
**问题：水印功能适用于什么场景？**

**答案原文：**
"当需要为教育类的教学课件设置版权方 Logo 等场景下，可使用 SDK 的水印功能来实现。"

**来源：** 水印和截图.md，段落：功能简介

---

### Q14 - 事实性问题
**问题：水印图片支持哪些格式？**

**答案原文：**
"水印图片只支持 PNG 与 JPEG 两种图片格式，即 .png、.jpg、.jpeg 三种后缀的图片文件。"

**来源：** 水印和截图.md，段落：水印 Warning

---

### Q15 - 事实性问题
**问题：ZegoWatermark 参数中的 imageURL 当前支持什么协议？**

**答案原文：**
"ZegoWatermark 参数当前只支持本地文件传输协议，即 file:///+绝对路径的形式。"

**来源：** 水印和截图.md，段落：水印

---

### Q16 - 事实性问题
**问题：如何设置推流水印？**

**答案原文：**
"调用 setPublishWatermark 接口设置推流水印，设置水印，支持推流过程中动态修改。"

**来源：** 水印和截图.md，段落：水印

---

### Q17 - 事实性问题
**问题：对推流画面截图需要调用什么接口？**

**答案原文：**
"推流后，调用 takePublishStreamSnapshot 接口对推流画面截图。"

**来源：** 水印和截图.md，段落：截图

---

### Q18 - 事实性问题
**问题：对拉流画面截图需要调用什么接口？**

**答案原文：**
"拉流后，调用 takePlayStreamSnapshot 接口对拉流画面截图。"

**来源：** 水印和截图.md，段落：截图

---

### Q19 - 事实性问题
**问题：imageURL 如何指定？请举例说明**

**答案原文：**
"imageURL 当前只支持本地文件传输协议，即 file:///+绝对路径的形式。例如：file:///D:/ZegoLogo.png。"

**来源：** 水印和截图.md，段落：常见问题 Q1

---

### Q20 - 事实性问题
**问题：水印布局的 layout 参数有什么限制？**

**答案原文：**
"水印的布局不能超过当前设置的推流的视频编码分辨率，对推流编码分辨率的设置请参考 setVideoConfig 接口。"

**来源：** 水印和截图.md，段落：常见问题 Q2

---

## 文档三：OpenClaw 常见问题 (openclaw常见问题.md)

### Q21 - 事实性问题
**问题：OpenClaw 是什么？**

**答案原文：**
"OpenClaw 是一个运行在你自己设备上的个人 AI 助手。它可以在你已经使用的消息界面上回复（WhatsApp、Telegram、Slack、Mattermost、Discord、Google Chat、Signal、iMessage、WebChat，以及 QQ Bot 等内置渠道插件），也可以在支持的平台上提供语音 + 实时 Canvas。"

**来源：** openclaw常见问题.md，段落：什么是 OpenClaw

---

### Q22 - 事实性问题
**问题：Gateway 网关是什么？**

**答案原文：**
"Gateway 网关是常驻控制平面；助手才是产品。"

**来源：** openclaw常见问题.md，段落：什么是 OpenClaw

---

### Q23 - 理解性问题
**问题：OpenClaw 的价值主张是什么？**

**答案原文：**
"OpenClaw 不只是 Claude 包装器。它是一个本地优先的控制平面，让你可以用自己的硬件运行一个有能力的助手，通过你已经使用的聊天应用访问，并提供有状态会话、记忆和工具，而无需把工作流控制权交给托管 SaaS。"

**来源：** openclaw常见问题.md，段落：价值主张

---

### Q24 - 事实性问题
**问题：如何在不让仓库变脏的情况下自定义 Skills？**

**答案原文：**
"使用托管覆盖，而不是编辑仓库副本。将你的更改放入 ~/.openclaw/skills/<name>/SKILL.md，托管覆盖会在不触碰 git 的情况下优先于内置 Skills。"

**来源：** openclaw常见问题.md，段落：Skills 和自动化

---

### Q25 - 理解性问题
**问题：机器人在执行繁重工作时卡住，应该如何卸载这类工作？**

**答案原文：**
"对长任务或并行任务使用子智能体。子智能体在自己的会话中运行，返回摘要，并保持主聊天响应流畅。让你的机器人，为此任务生成一个子智能体。"

**来源：** openclaw常见问题.md，段落：Skills 和自动化

---

### Q26 - 事实性问题
**问题：Cron 或提醒没有触发时，应该检查什么？**

**答案原文：**
"Cron 在 Gateway 网关进程内运行。如果 Gateway 网关没有持续运行，定时作业就不会运行。确认 cron 已启用（cron.enabled），并且未设置 OPENCLAW_SKIP_CRON。"

**来源：** openclaw常见问题.md，段落：Skills 和自动化

---

### Q27 - 事实性问题
**问题：OpenClaw 如何加载环境变量？**

**答案原文：**
"OpenClaw 会从父进程（shell、launchd/systemd、CI 等）读取环境变量，并额外加载当前工作目录中的 .env 和来自 ~/.openclaw/.env 的全局 fallback .env。两个 .env 文件都不会覆盖现有环境变量。"

**来源：** openclaw常见问题.md，段落：环境变量和 .env 加载

---

### Q28 - 理解性问题
**问题：上下文在任务中途被截断时，有哪些防止方法？**

**答案原文：**
"让 bot 总结当前状态并写入文件；在长任务前使用 /compact，在切换主题时使用 /new；将重要上下文保存在工作区中，并让 bot 回读；对长时间或并行工作使用子智能体；如果经常发生这种情况，请选择上下文窗口更大的模型。"

**来源：** openclaw常见问题.md，段落：会话和多个聊天

---

### Q29 - 事实性问题
**问题：如何彻底重置 OpenClaw 但保留安装？**

**答案原文：**
"使用重置命令：openclaw reset；非交互式完整重置：openclaw reset --scope full --yes --non-interactive。"

**来源：** openclaw常见问题.md，段落：会话和多个聊天

---

### Q30 - 事实性问题
**问题：Heartbeat 默认多长时间运行一次？**

**答案原文：**
"Heartbeat 默认每 30m 运行一次（使用 OAuth auth 时为 1h）。可以调整或禁用。"

**来源：** openclaw常见问题.md，段落：会话和多个聊天

---

### Q31 - 推理性问题
**问题：为什么上下文会每 30 分钟收到 heartbeat 消息？**

**答案原文：**
"Heartbeat 默认每 30m 运行一次（使用 OAuth auth 时为 1h）。如果 HEARTBEAT.md 存在但实际上为空（只有空行和类似 # Heading 的 markdown 标题），OpenClaw 会跳过 heartbeat 运行以节省 API 调用。"

**来源：** openclaw常见问题.md，段落：会话和多个聊天

---

### Q32 - 理解性问题
**问题：OpenClaw 与 Claude Code 在 Web 开发方面相比有什么优势？**

**答案原文：**
"优势包括：跨会话的持久记忆 + 工作区；多平台访问（WhatsApp、Telegram、TUI、WebChat）；工具编排（浏览器、文件、调度、钩子）；常驻 Gateway 网关（在 VPS 上运行，从任何地方交互）；用于本地浏览器/屏幕/摄像头/exec 的节点。"

**来源：** openclaw常见问题.md，段落：什么是 OpenClaw

---

## 文档四：OpenClaw 渠道故障 (openclaw渠道故障.md)

### Q33 - 事实性问题
**问题：当渠道已连接但行为异常时，应该先按什么顺序运行命令？**

**答案原文：**
"先按顺序运行这些命令：openclaw status；openclaw gateway status；openclaw logs --follow；openclaw doctor；openclaw channels status --probe。"

**来源：** openclaw渠道故障.md，段落：命令阶梯

---

### Q34 - 事实性问题
**问题：健康基线中 Runtime 的正常状态是什么？**

**答案原文：**
"健康基线：Runtime: running；Connectivity probe: ok；Capability: read-only、write-capable 或 admin-capable。"

**来源：** openclaw渠道故障.md，段落：命令阶梯

---

### Q35 - 事实性问题
**问题：WhatsApp 故障中，已连接但没有私信回复的最快检查方法是什么？**

**答案原文：**
"最快检查方法是执行 openclaw pairing list whatsapp，修复方案是批准发送者，或切换私信策略/允许列表。"

**来源：** openclaw渠道故障.md，段落：WhatsApp 故障特征

---

### Q36 - 事实性问题
**问题：Telegram 启动报告 getMe returned 401 时应该如何修复？**

**答案原文：**
"检查已配置的令牌来源；重新复制或重新生成 BotFather 令牌，并更新 botToken、tokenFile 或默认账户的 TELEGRAM_BOT_TOKEN。"

**来源：** openclaw渠道故障.md，段落：Telegram 故障特征

---

### Q37 - 事实性问题
**问题：Discord 机器人在线但没有服务器回复的最快检查方法是什么？**

**答案原文：**
"最快检查方法是执行 openclaw channels status --probe，修复方案是允许服务器/频道，并验证消息内容意图。"

**来源：** openclaw渠道故障.md，段落：Discord 故障特征

---

### Q38 - 事实性问题
**问题：Slack Socket mode 已连接但没有响应时应该检查什么？**

**答案原文：**
"验证 app token + bot token 和所需 scopes；在基于 SecretRef 的设置中留意 botTokenStatus / appTokenStatus = configured_unavailable。"

**来源：** openclaw渠道故障.md，段落：Slack 故障特征

---

### Q39 - 事实性问题
**问题：iMessage 在 macOS 上可以发送但无法接收时应该检查什么？**

**答案原文：**
"检查 macOS 对 Messages 自动化的隐私权限；重新授予 TCC 权限，并重启渠道进程。"

**来源：** openclaw渠道故障.md，段落：iMessage 故障特征

---

### Q40 - 事实性问题
**问题：QQ Bot 机器人回复 gone to Mars 时应该如何修复？**

**答案原文：**
"验证配置中的 appId 和 clientSecret；设置凭据，或重启 Gateway 网关。"

**来源：** openclaw渠道故障.md，段落：QQ Bot 故障特征

---

## 难度级别分布

| 难度级别 | 问题数量 | 题号 |
|---------|---------|------|
| 事实性问题 | 24 | Q1, Q2, Q4, Q5, Q6, Q9, Q10, Q13, Q14, Q15, Q16, Q17, Q18, Q19, Q20, Q21, Q22, Q24, Q26, Q27, Q29, Q30, Q33, Q34, Q35, Q36, Q37, Q38, Q39, Q40 |
| 理解性问题 | 10 | Q3, Q7, Q12, Q23, Q25, Q28, Q32, Q8, Q11, Q31 |
| 推理性问题 | 2 | Q8, Q11, Q31 |

---

## 文档来源统计

| 文档名称 | 问题数量 |
|---------|---------|
| custom-video-capture.md | 12 |
| 水印和截图.md | 8 |
| openclaw常见问题.md | 12 |
| openclaw渠道故障.md | 8 |
| **总计** | **40** |

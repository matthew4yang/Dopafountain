# Dopafountain

Dopafountain 是一个 Android 随机硬核科学事实通知器。

## 严格领域白名单

从 V0.3 起，通知只允许三个领域：

- 宇宙探索
- 粒子物理
- 古生物学

医学、AI、能源、生态、社会新闻等全部禁止进入消息池。

## 消息规则

- 只保留核心事实：谁、做了什么、发现/测量/确认了什么、关键数字或阶段。
- 不加“世界又好了一点”“值得高兴”“人类还在探索”等人为语气。
- 抓取端先限定 NASA/JPL/ESA、CERN/Fermilab/BNL/DESY、Nature/Science/PNAS/Smithsonian 等权威来源，再做关键词与事实动作双重过滤。
- Android 端再次执行三领域白名单，远程 feed 即使误混入其他类别，也不会弹出。
- 没有合格新消息时宁可不通知。
- 每条通知保留来源，点击可打开原文。

## 数据流水线

GitHub Actions 每 2 小时运行一次：

权威来源发现 → 三领域白名单 → 硬事实筛选 → 去重 → 中文化 → data/goodnews.json

Android App 从公开 goodnews.json 取水，并按用户设定的平均间隔随机推送。

## Android

- 平均通知间隔：15–90 分钟
- 每次通知后重新随机下一次时间
- 23:00–08:00 静默
- Android 13+ 通知权限
- WorkManager 后台调度
- GitHub Actions 自动构建 Release APK

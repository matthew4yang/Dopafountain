# Dopafountain ⛲

Dopafountain 是一款极简 Android 好消息通知 App。

它不是另一个要不停刷的信息流，而是让手机在一天里随机、低频地递来一小口值得高兴的消息。

## V0.1
- 开/关“多巴胺喷泉”
- 平均通知间隔 15–90 分钟
- 每次重新随机下一次时间，避免规律感
- 23:00–08:00 静默
- Android 13+ 通知权限
- WorkManager 后台调度
- 内置中文种子消息
- GitHub Actions 自动编译 APK 并发布 Release

## 下一阶段
1. 接入公开 RSS 好消息源
2. GitHub Actions 定时抓取、去重和可信度筛选
3. 自动压缩为 1–2 句中文
4. App 下载精选后的轻量 JSON
5. 分类偏好：科学 / 医疗 / 环境 / 航天 / 善意 / 工程

当前仓库是 private；因此手机不能匿名读取仓库里的 raw JSON。若改为 public，即可直接把仓库生成的数据作为远程消息池。
